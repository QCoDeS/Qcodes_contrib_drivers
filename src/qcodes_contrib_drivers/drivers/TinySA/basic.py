"""Interface for the tinySA Basic spectrum analyser.

Provides a Python driver for the tinySA Basic spectrum analyser.

Documentation:

- tinySA: https://www.tinysa.org/wiki/
- Unofficial Python API: https://github.com/LC-Linkous/tinySA_python

See `docs/examples/` for example notebooks.

Written by Edward Laird (http://wp.lancs.ac.uk/laird-group/).
"""

from __future__ import annotations

import re
import time
from typing import Any, Protocol, Sequence, cast

import numpy as np
from qcodes.instrument import Instrument
from qcodes.parameters import Parameter, ParameterWithSetpoints
from qcodes.validators import Arrays, Enum, Numbers


class SerialHandle(Protocol):
    """Protocol for the subset of pyserial's Serial API used by this driver."""

    def close(self) -> None: ...

    def reset_input_buffer(self) -> None: ...

    def reset_output_buffer(self) -> None: ...

    def write(self, data: bytes) -> int: ...

    def flush(self) -> None: ...

    def read(self, size: int = 1) -> bytes: ...


class ListPortsModule(Protocol):
    """Protocol for the list_ports module used for USB autodetection."""

    def comports(self) -> Sequence[Any]: ...


serial: Any | None = None
list_ports: ListPortsModule | None = None


def _ensure_pyserial() -> None:
    """Import pyserial lazily so the module can load without it installed."""
    global serial, list_ports
    if serial is not None and list_ports is not None:
        return
    try:
        import serial as _serial
        from serial.tools import list_ports as _list_ports
    except ImportError as exc:
        raise ImportError(
            "TinySABasic requires the optional dependency 'pyserial'. "
            "Install it in the active environment to use this driver."
        ) from exc
    serial = _serial
    list_ports = _list_ports


VID = 0x0483  # Vendor ID
PID = 0x5740  # Product ID


class TinySASerialBackend:
    """
    Minimal serial backend for tinySA.

    The command semantics follow the documented tinySA_python API:
    - `mode {low|high} {input|output}`
    - `scan {start} {stop} [npts] [outmask]`
    - `output on|off`
    """

    PROMPT = b"ch>"

    def __init__(
        self,
        port: str | None = None,
        *,
        timeout: float = 5.0,
        vid: int = VID,
        pid: int = PID,
    ) -> None:
        self._port = port or self.autodetect_port(vid=vid, pid=pid)
        self._timeout = timeout
        self._serial: SerialHandle | None = None

    @property
    def port(self) -> str:
        return self._port

    @staticmethod
    def autodetect_port(*, vid: int = VID, pid: int = PID) -> str:
        _ensure_pyserial()
        assert list_ports is not None
        for device in list_ports.comports():
            if device.vid == vid and device.pid == pid:
                return device.device
        raise OSError("tinySA device not found")

    def connect(self) -> None:
        _ensure_pyserial()
        if self._serial is None:
            assert serial is not None
            self._serial = cast(
                SerialHandle,
                serial.Serial(self._port, timeout=self._timeout),
            )
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()

    def disconnect(self) -> None:
        if self._serial is not None:
            self._serial.close()
            self._serial = None

    def _serial_handle(self) -> SerialHandle:
        self.connect()
        assert self._serial is not None
        return self._serial

    def _write_command(self, command: str) -> None:
        handle = self._serial_handle()
        handle.reset_input_buffer()
        handle.reset_output_buffer()
        handle.write((command + "\r").encode("ascii"))
        handle.flush()

    def _read_until_prompt(self) -> bytes:
        handle = self._serial_handle()
        buffer = bytearray()
        deadline = time.monotonic() + self._timeout
        while True:
            chunk = handle.read(1)
            if chunk:
                buffer.extend(chunk)
                if buffer.endswith(self.PROMPT):
                    return bytes(buffer)
                deadline = time.monotonic() + self._timeout
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError("Timed out waiting for tinySA prompt")

    @staticmethod
    def _strip_prompt(payload: bytes) -> bytes:
        cleaned = payload.replace(b"\r", b"")
        if cleaned.endswith(TinySASerialBackend.PROMPT):
            cleaned = cleaned[: -len(TinySASerialBackend.PROMPT)]
        return cleaned.strip(b"\n")

    def command_bytes(self, command: str) -> bytes:
        self._write_command(command)
        cleaned = self._strip_prompt(self._read_until_prompt())
        lines = cleaned.splitlines()
        if lines and lines[0].strip() == command.encode("ascii"):
            cleaned = b"\n".join(lines[1:])
        return cleaned.strip(b"\n")

    def command_text(self, command: str) -> str:
        return (
            self.command_bytes(command)
            .decode(
                "utf-8",
                errors="replace",
            )
            .strip()
        )

    def version(self) -> str:
        return self.command_text("version")

    def set_mode(self, rf_path: str, io_mode: str) -> None:
        self.command_bytes(f"mode {rf_path} {io_mode}")

    def set_output(self, enabled: bool) -> None:
        self.command_bytes(f"output {'on' if enabled else 'off'}")

    def set_level(self, value: float) -> None:
        self.command_bytes(f"level {value:g}")

    def set_frequency(self, value: float) -> None:
        self.command_bytes(f"freq {int(round(value))}")

    def set_rbw(self, value: str | int) -> None:
        """
        Set RBW using the driver-facing unit convention.

        The QCoDeS layer uses Hz, but the tinySA command expects kHz, so
        numeric values are converted here before being sent to the instrument.
        """
        if isinstance(value, str):
            text = value.strip().lower()
            if text != "auto":
                raise ValueError("rbw string value must be 'auto'")
            self.command_bytes("rbw auto")
            return
        self.command_bytes(f"rbw {int(round(value / 1000))}")

    def get_rbw(self) -> str | int:
        """
        Read RBW from the instrument and return it in Hz.

        The tinySA reports numeric RBW values in kHz. This method normalises
        the response to the driver-facing Hz convention.
        """
        response = self.command_text("rbw").lower()
        marked_match = re.search(r"\[\s*(auto|[-+]?\d*\.?\d+)\s*\]", response)
        if marked_match is not None:
            token = marked_match.group(1)
        else:
            tokens = re.findall(r"auto|[-+]?\d*\.?\d+", response)
            if len(tokens) != 1:
                raise ValueError(f"Could not parse rbw response: {response!r}")
            token = tokens[0]
        if token == "auto":
            return "auto"
        return int(round(float(token) * 1000))

    def set_sweep_start(self, value: float) -> None:
        self.command_bytes(f"sweep start {int(round(value))}")

    def set_sweep_stop(self, value: float) -> None:
        self.command_bytes(f"sweep stop {int(round(value))}")

    def pause(self) -> None:
        self.command_bytes("pause")

    def resume(self) -> None:
        self.command_bytes("resume")

    @staticmethod
    def _coerce_trace_length(
        values: Sequence[float],
        expected_npts: int,
    ) -> np.ndarray:
        """Coerce a trace to the expected number of points by padding or truncating."""
        array = np.asarray(values, dtype=float)
        if array.size == expected_npts:
            return array
        if array.size > expected_npts:
            return array[:expected_npts]
        if array.size == 0:
            return np.full(expected_npts, np.nan, dtype=float)
        padding = np.full(expected_npts - array.size, array[-1], dtype=float)
        return np.concatenate((array, padding))

    @staticmethod
    def _parse_scan_column(payload: bytes, expected_npts: int) -> np.ndarray:
        # tinySA occasionally returns a malformed token `-:.0`; tinySA_python
        # replaces it with `-10.0` before parsing.
        fixed = payload.replace(b"-:.0", b"-10.0")
        return TinySASerialBackend._parse_numeric_column(
            fixed,
            expected_npts,
        )

    @staticmethod
    def _parse_numeric_column(
        payload: bytes,
        expected_npts: int,
    ) -> np.ndarray:
        values: list[float] = []
        for raw_line in payload.replace(b"\r", b"").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            for token in line.split():
                try:
                    values.append(float(token))
                    break
                except ValueError:
                    continue
        return TinySASerialBackend._coerce_trace_length(
            values,
            expected_npts,
        )

    def scan(
        self,
        start: float,
        stop: float,
        npts: int,
        *,
        outmask: int = 2,
    ) -> np.ndarray:
        """Run a sweep and return the first numeric column of the response."""
        command = (
            f"scan {int(round(start))} {int(round(stop))} {int(npts)} {int(outmask)}"
        )
        payload = self.command_bytes(command)
        try:
            return self._parse_scan_column(payload, expected_npts=npts)
        finally:
            self.resume()


class TinySABasic(Instrument):
    """
    QCoDeS driver for the tinySA Basic spectrum analyser.

    This driver communicates with the instrument over its serial command
    interface via `pyserial`. It provides QCoDeS parameters for sweep
    configuration, output configuration, and trace acquisition.

    Reading `measurement_trace` triggers a fresh sweep and returns the trace
    data with `frequency` as the corresponding setpoints.
    """

    ALLOWED_SWEEP_NPTS = (51, 101, 145, 290)
    ALLOWED_RBW_HZ = ("auto", 3000, 10000, 30000, 100000, 300000, 600000)
    MODE_VALUES = {
        "low_input": ("low", "input"),
        "high_input": ("high", "input"),
        "low_output": ("low", "output"),
        "high_output": ("high", "output"),
    }

    def __init__(
        self,
        name: str,
        port: str | None = None,
        *,
        timeout: float = 5.0,
        start: float = 1e6,
        stop: float = 300e6,
        npts: int = 290,
        **kwargs,
    ) -> None:
        # Import the optional serial dependency only when the driver is used.
        _ensure_pyserial()
        self._backend = TinySASerialBackend(port=port, timeout=timeout)
        self._backend.connect()

        self._start_hz = float(start)
        self._stop_hz = float(stop)
        self._npts = int(npts)
        self._mode_state = "unknown"
        self._rf_output_state = "unknown"
        self._rbw_state: str | int = "auto"
        self._level_dbm = 0.0
        self._output_frequency_hz = 1e6

        self._frequency_cache: np.ndarray | None = None
        self._measurement_trace_cache: np.ndarray | None = None

        super().__init__(name, **kwargs)

        self.mode: Parameter = self.add_parameter(
            "mode",
            label="tinySA Mode",
            get_cmd=self._get_mode,
            set_cmd=self._set_mode,
            vals=Enum(*self.MODE_VALUES),
        )
        """Which port to use and whether it's an input or output mode."""

        self.rf_output: Parameter = self.add_parameter(
            "rf_output",
            label="RF Output",
            get_cmd=self._get_rf_output,
            set_cmd=self._set_rf_output,
            vals=Enum("on", "off", "unknown"),
        )
        """ Whether the RF output is enabled. Only meaningful in output modes, but can be read in any mode. """

        self.rbw: Parameter = self.add_parameter(
            "rbw",
            label="Resolution Bandwidth",
            unit="Hz",
            get_cmd=self._get_rbw,
            set_cmd=self._set_rbw,
            vals=Enum(*self.ALLOWED_RBW_HZ),
        )
        """Resolution Bandwidth."""

        self.level: Parameter = self.add_parameter(
            "level",
            label="Output Level",
            unit="dBm",
            get_cmd=self._get_level,
            set_cmd=self._set_level,
            vals=Numbers(),
        )
        """RF output level."""

        self.output_frequency: Parameter = self.add_parameter(
            "output_frequency",
            label="Output Frequency",
            unit="Hz",
            get_cmd=self._get_output_frequency,
            set_cmd=self._set_output_frequency,
            vals=Numbers(min_value=0),
        )
        """RF output frequency."""

        self.start: Parameter = self.add_parameter(
            "start",
            label="Start Frequency",
            unit="Hz",
            get_cmd=self._get_start,
            set_cmd=self._set_start,
            vals=Numbers(min_value=0),
        )
        """Start frequency for the sweep."""

        self.stop: Parameter = self.add_parameter(
            "stop",
            label="Stop Frequency",
            unit="Hz",
            get_cmd=self._get_stop,
            set_cmd=self._set_stop,
            vals=Numbers(min_value=0),
        )
        """Stop frequency for the sweep."""

        self.npts: Parameter = self.add_parameter(
            "npts",
            label="Sweep Points",
            get_cmd=self._get_npts,
            set_cmd=self._set_npts,
            vals=Enum(*self.ALLOWED_SWEEP_NPTS),
        )
        """Number of points for the sweep."""

        self.frequency: Parameter = self.add_parameter(
            "frequency",
            label="Frequency",
            unit="Hz",
            get_cmd=self._get_frequency_axis,
            set_cmd=False,
            vals=Arrays(shape=(self._point_count,)),
        )
        """Parameter frequency, which serves as the setpoints for measurement_trace."""

        self.measurement_trace: ParameterWithSetpoints = self.add_parameter(
            "measurement_trace",
            label="Measurement Trace",
            unit="dBm",
            get_cmd=self._get_measurement_trace,
            set_cmd=False,
            parameter_class=ParameterWithSetpoints,
            setpoints=(self.frequency,),
            vals=Arrays(shape=(self._point_count,)),
        )
        """The measurement trace acquired from the instrument. Reading this parameter triggers a new sweep, and the frequency parameter is updated as the corresponding setpoints."""

        self.connect_message()

    def _point_count(self) -> int:
        return int(self._npts)

    def _invalidate_trace_cache(self) -> None:
        self._frequency_cache = None
        self._measurement_trace_cache = None

    @staticmethod
    def _normalise_mode(value: str) -> str:
        text = value.strip().lower().replace("-", "_").replace(" ", "_")
        if text not in TinySABasic.MODE_VALUES:
            valid = ", ".join(sorted(TinySABasic.MODE_VALUES))
            raise ValueError(
                f"Unsupported tinySA mode {value!r}. Valid modes: {valid}",
            )
        return text

    def _mode_is_output(self) -> bool:
        return self._mode_state.endswith("_output")

    def _require_input_mode(self, operation: str) -> None:
        if self._mode_is_output():
            raise RuntimeError(
                f"{operation} requires an input mode. "
                "Set sa.mode('low_input') or sa.mode('high_input') first."
            )

    def _set_mode(self, value: str) -> None:
        mode = self._normalise_mode(value)
        rf_path, io_mode = self.MODE_VALUES[mode]
        self._backend.set_mode(rf_path, io_mode)
        self._mode_state = mode
        self._invalidate_trace_cache()

    def _get_mode(self) -> str:
        return self._mode_state

    def _set_rf_output(self, value: str) -> None:
        state = value.strip().lower()
        if state not in {"on", "off"}:
            raise ValueError("rf_output must be 'on' or 'off'")
        self._backend.set_output(state == "on")
        self._rf_output_state = state

    def _get_rf_output(self) -> str:
        return self._rf_output_state

    def _set_rbw(self, value: str | int) -> None:
        rbw: str | int
        if isinstance(value, str):
            rbw = value.strip().lower()
        else:
            rbw = int(value)
        if rbw not in self.ALLOWED_RBW_HZ:
            raise ValueError(
                "tinySA supports only these RBW values: "
                f"{', '.join(str(v) for v in self.ALLOWED_RBW_HZ)}. "
                f"Requested: {rbw}."
            )
        self._backend.set_rbw(rbw)
        self._rbw_state = rbw
        self._invalidate_trace_cache()

    def _get_rbw(self) -> str | int:
        try:
            self._rbw_state = self._backend.get_rbw()
        except ValueError:
            pass
        return self._rbw_state

    def _set_level(self, value: float) -> None:
        self._backend.set_level(float(value))
        self._level_dbm = float(value)

    def _get_level(self) -> float:
        return self._level_dbm

    def _set_output_frequency(self, value: float) -> None:
        self._backend.set_frequency(float(value))
        self._output_frequency_hz = float(value)

    def _get_output_frequency(self) -> float:
        return self._output_frequency_hz

    def _set_start(self, value: float) -> None:
        start_hz = float(value)
        self._start_hz = start_hz
        self._invalidate_trace_cache()

    def _get_start(self) -> float:
        return self._start_hz

    def _set_stop(self, value: float) -> None:
        stop_hz = float(value)
        self._stop_hz = stop_hz
        self._invalidate_trace_cache()

    def _get_stop(self) -> float:
        return self._stop_hz

    def _set_npts(self, value: int) -> None:
        npts = int(value)
        if npts not in self.ALLOWED_SWEEP_NPTS:
            raise ValueError(
                "tinySA supports only these sweep point counts: "
                f"{', '.join(str(p) for p in self.ALLOWED_SWEEP_NPTS)}. "
                f"Requested: {npts}."
            )
        self._npts = npts
        self._invalidate_trace_cache()

    def _get_npts(self) -> int:
        return self._npts

    def _validate_sweep_range(self) -> None:
        if self._start_hz >= self._stop_hz:
            raise ValueError(
                "Invalid sweep range: "
                f"start={self._start_hz:g} Hz, stop={self._stop_hz:g} Hz. "
                "Set start lower than stop before acquiring data."
            )

    def _make_frequency_axis(self) -> np.ndarray:
        self._validate_sweep_range()
        return np.linspace(
            self._start_hz,
            self._stop_hz,
            num=self._npts,
            dtype=float,
        )

    def _get_frequency_axis(self) -> np.ndarray:
        if self._frequency_cache is None or self._frequency_cache.size != self._npts:
            self._frequency_cache = self._make_frequency_axis()
        return self._frequency_cache.copy()

    def _update_parameter_caches(self) -> None:
        if self._frequency_cache is not None:
            self.frequency.cache.set(self._frequency_cache.copy())
        if self._measurement_trace_cache is not None:
            self.measurement_trace.cache.set(
                self._measurement_trace_cache.copy(),
            )

    def refresh_sweep(self) -> np.ndarray:
        """
        Acquire a fresh trace and update the parameter caches.

        The caches are kept only so QCoDeS can snapshot the trace and matching
        frequency setpoints consistently after the acquisition.
        """
        self._require_input_mode("refresh_sweep")
        self._frequency_cache = self._make_frequency_axis()
        self._measurement_trace_cache = self._backend.scan(
            self._start_hz,
            self._stop_hz,
            self._npts,
            outmask=2,
        )
        self._update_parameter_caches()
        return self._measurement_trace_cache.copy()

    def _get_measurement_trace(self) -> np.ndarray:
        """Return a newly acquired trace on every call."""
        return self.refresh_sweep()

    def ask_raw(self, command: str) -> str:
        return self._backend.command_text(command)

    def write_raw(self, command: str) -> None:
        self._backend.command_bytes(command)

    def get_idn(self) -> dict[str, str | None]:
        firmware = self.ask_raw("version").splitlines()[0]
        return {
            "vendor": "tinySA",
            "model": "tinySA",
            "serial": None,
            "firmware": firmware,
        }

    def close(self) -> None:
        try:
            self._backend.disconnect()
        finally:
            super().close()
