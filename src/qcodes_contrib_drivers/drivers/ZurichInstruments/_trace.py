"""QCoDeS array readout for a single LabOne acquisition.

Written by Edward Laird (http://wp.lancs.ac.uk/laird-group/).
"""

from collections.abc import Sequence
from contextlib import ExitStack
import math
from typing import TYPE_CHECKING, Any

import numpy as np
from qcodes.parameters import MultiParameter, Parameter

if TYPE_CHECKING:
    from ._lockin import LockinMixin


def _finite(value: float, name: str, *, minimum: float | None = None) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


class TraceParameter(MultiParameter):
    """One fresh time trace or parameter sweep per read.

    Create through ``lockin.configure_trace``. All selected components share
    one acquisition; R and Theta are derived from its X/Y arrays (Theta in
    degrees). ``axis`` returns the latest acquired setpoints, or the nominal
    grid before the first acquisition. Interpolated time traces use LabOne's
    reported grid spacing; exact traces use device timestamps. Configure a new
    parameter to change trace length, selection, or units before starting a
    new dataset.
    """

    def __init__(
        self,
        device: "LockinMixin",
        *,
        duration: float | None,
        grid_mode: int | None,
        sweep_parameter: Parameter | None,
        start: float | None,
        stop: float | None,
        points: int,
        demod: int,
        parameters: Sequence[str],
        name: str | None,
        timeout: float,
        spacing: str | None,
        settling_time: float | None,
        averaging_time: float | None,
    ) -> None:
        if (
            isinstance(points, bool)
            or not isinstance(points, (int, np.integer))
            or points < 2
        ):
            raise ValueError("points must be an integer >= 2")
        if isinstance(parameters, str) or not isinstance(parameters, Sequence):
            raise TypeError("parameters must be a sequence of x, y, r, theta")
        components = tuple(parameters)
        if not components or any(
            p not in ("x", "y", "r", "theta") for p in components
        ):
            raise ValueError("Select at least one component from x, y, r, theta")
        if len(set(components)) != len(components):
            raise ValueError("Trace components must be unique")
        if (
            isinstance(demod, bool)
            or not isinstance(demod, (int, np.integer))
            or demod not in device._readouts
        ):
            raise ValueError(f"No trace readout is available for demodulator {demod}")
        self._device = device
        self._reader = device._readouts[demod]
        self._demod = device.demods[demod]
        self._demod_index = int(demod)
        self._points = int(points)
        self._components = components
        self._timeout = _finite(timeout, "timeout", minimum=0)
        if self._timeout == 0:
            raise ValueError("timeout must be positive")
        self._sweep_parameter = sweep_parameter
        self._duration = duration
        self._exact_rate: float | None = None
        settings: dict[str, Any] = dict(
            points=self._points, demodulator=int(demod),
            components=components, timeout_s=self._timeout,
        )
        if sweep_parameter is None:
            if grid_mode is not None and (
                isinstance(grid_mode, bool)
                or not isinstance(grid_mode, (int, np.integer))
                or grid_mode not in (1, 2, 4)
            ):
                raise ValueError("grid_mode must be 1 (nearest), 2 (linear), or 4 (exact)")
            self._grid_mode = 2 if grid_mode is None else int(grid_mode)
            if any(
                v is not None
                for v in (start, stop, spacing, settling_time, averaging_time)
            ):
                raise ValueError(
                    "start, stop, spacing, settling_time and averaging_time "
                    "require sweep_parameter"
                )
            if self._grid_mode == 4:
                if duration is not None:
                    raise ValueError("Omit duration when grid_mode=4; points and rate determine duration")
                self._exact_rate = _finite(self._demod.rate(), "streaming rate", minimum=0)
                if self._exact_rate == 0:
                    raise ValueError("Exact sampling requires a positive streaming rate")
                axis = np.arange(self._points) / self._exact_rate
                duration_s = self._points / self._exact_rate
                settings["sampling_rate_sps"] = self._exact_rate
            else:
                if duration is None:
                    raise ValueError("Supply duration for grid modes 1 and 2, or use grid_mode=4")
                self._duration = _finite(duration, "duration", minimum=0)
                if self._duration == 0:
                    raise ValueError("duration must be positive")
                duration_s = self._duration
                axis = np.arange(self._points) * self._duration / self._points
            axis_suffix, axis_label, axis_unit = "time", "Time from trace start", "s"
            settings.update(
                acquisition="time", duration_s=duration_s,
                grid_mode={1: "nearest", 2: "linear", 4: "exact"}[self._grid_mode],
            )
        else:
            if grid_mode is not None:
                raise ValueError("grid_mode is only supported for time traces")
            if duration is not None or start is None or stop is None:
                raise ValueError("A sweep requires start and stop, without duration")
            node = getattr(sweep_parameter, "zi_node", None)
            if (
                not isinstance(sweep_parameter, Parameter)
                or sweep_parameter.root_instrument is not device
                or not sweep_parameter.settable or not sweep_parameter.gettable
                or not isinstance(node, str)
                or not node.lower().startswith(f"/{device.serial.lower()}/")
            ):
                raise ValueError(
                    "sweep_parameter must be a readable, writable native node "
                    "on this instrument"
                )
            if sweep_parameter.scale is not None or sweep_parameter.offset is not None:
                raise ValueError(
                    "sweep_parameter must use native node units without scale or offset"
                )
            self._start = _finite(start, "start")
            self._stop = _finite(stop, "stop")
            if self._start >= self._stop:
                raise ValueError("start must be less than stop")
            sweep_parameter.validate(self._start)
            sweep_parameter.validate(self._stop)
            self._spacing = "linear" if spacing is None else spacing
            if self._spacing not in ("linear", "log"):
                raise ValueError("spacing must be 'linear' or 'log'")
            if self._spacing == "log" and self._start <= 0:
                raise ValueError("Logarithmic sweeps require positive start and stop")
            self._settling_time = _finite(
                0.0 if settling_time is None else settling_time,
                "settling_time", minimum=0,
            )
            self._averaging_time = _finite(
                0.0 if averaging_time is None else averaging_time,
                "averaging_time", minimum=0,
            )
            grid = np.geomspace if self._spacing == "log" else np.linspace
            axis = grid(self._start, self._stop, self._points)
            axis_suffix = sweep_parameter.name
            axis_label, axis_unit = sweep_parameter.label, sweep_parameter.unit
            settings.update(
                acquisition="sweep", sweep_node=node,
                sweep_parameter=sweep_parameter.full_name,
                start=self._start, stop=self._stop, spacing=self._spacing,
                bandwidth_control="manual", settling_time_s=self._settling_time,
                settling_inaccuracy=0.001, averaging_time_s=self._averaging_time,
                averaging_tc=10, averaging_samples=10, restore_sweep_parameter=True,
            )

        self._reader._check_configuration()
        self._configuration = self._reader.configuration
        self._readout_units = tuple(self._demod.readout.units)
        self._check_setup()
        if name is None:
            base = "time_trace" if sweep_parameter is None else "sweep_trace"
            name = base
            suffix = 2
            while name in self._demod.parameters:
                name = f"{base}_{suffix}"
                suffix += 1
        elif name in self._demod.parameters:
            raise ValueError(f"Demodulator already has a parameter named {name!r}")
        indices = tuple(("x", "y", "r", "theta").index(c) for c in components)
        self._axis = axis
        super().__init__(
            name, instrument=self._demod,
            names=tuple(f"{name}_{c}" for c in components),
            labels=tuple("Theta" if c == "theta" else c.upper() for c in components),
            units=tuple(self._readout_units[i] for i in indices),
            shapes=((self._points,),) * len(components),
            setpoints=((axis,),) * len(components),
            setpoint_names=((f"{name}_{axis_suffix}",),) * len(components),
            setpoint_labels=((axis_label,),) * len(components),
            setpoint_units=((axis_unit,),) * len(components),
            snapshot_get=False, snapshot_value=False,
        )
        self.metadata.update(self._demod.readout.metadata)
        self.metadata.update(settings)
        self.metadata["polar_convention"] = "r=abs(x+iy), theta=arg(x+iy) in degrees"

    @property
    def axis(self) -> np.ndarray:
        """A copy of the latest axis, in the units specified by setpoint_units."""
        return self._axis.copy()

    def _check_setup(self) -> None:
        self._device._check_demodulator(self._demod_index)
        self._reader._check_configuration()
        if (
            self._reader.configuration != self._configuration
            or tuple(self._demod.readout.units) != self._readout_units
        ):
            raise RuntimeError(
                "Readout configuration changed; configure a new trace before measuring"
            )
        if self._demod.trigger() != 0:
            raise RuntimeError(
                "Enable continuous demodulator streaming before acquiring a trace"
            )
        if self._exact_rate is not None and self._demod.rate() != self._exact_rate:
            raise RuntimeError("Streaming rate changed; configure a new trace for exact sampling")
        if (
            self._duration is not None
            and self._points / self._duration > self._demod.rate()
        ):
            raise ValueError("Increase demodulator streaming rate or reduce points/duration")

    def get_raw(self) -> tuple[np.ndarray, ...]:
        with self._device._readout_lock:
            self._check_setup()
            if self._sweep_parameter is None:
                axis, x, y = self._acquire_time()
            else:
                axis, x, y = self._acquire_sweep()
            self._check_setup()
            values = dict(
                x=x, y=y, r=np.hypot(x, y), theta=np.degrees(np.arctan2(y, x))
            )
            # DataSaver expands MultiParameter setpoints after get_raw returns.
            # Never substitute the nominal grid for an acquired axis.
            self._axis = axis.copy()
            self.setpoints = ((self._axis,),) * len(self._components)
            return tuple(values[c] for c in self._components)

    @staticmethod
    def _cleanup(stack: ExitStack, module: Any) -> None:
        # ExitStack attempts every cleanup even if an earlier callback raises.
        stack.callback(module.close)
        stack.callback(module.raw_module.clear)
        stack.callback(module.unsubscribe, "*")
        stack.callback(module.finish)

    def _acquire_time(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        paths = [
            f"/{self._device.serial.lower()}/demods/{self._demod_index}/sample.{c}"
            for c in ("x", "y")
        ]
        with ExitStack() as stack:
            module = self._device.session.modules.create_daq_module()
            self._cleanup(stack, module)
            module.device(self._device)
            module.type(0)
            module.grid.mode(self._grid_mode)
            module.grid.rows(1)
            module.count(1)
            module.endless(0)
            if self._duration is not None:
                module.duration(self._duration)
            module.grid.cols(self._points)
            for path in paths:
                module.subscribe(path)
            module.execute()
            module.wait_done(timeout=self._timeout, sleep_time=0.05)
            data = module.read(raw=True)
        try:
            if any(len(data[path]) != 1 for path in paths):
                raise ValueError("Expected one burst per component")
            bursts = [data[path][0] for path in paths]
            values = [np.asarray(b["value"], dtype=float) for b in bursts]
            stamps = [np.asarray(b["timestamp"]) for b in bursts]
            if any(a.shape != (1, self._points) for a in values + stamps):
                raise ValueError("Unexpected trace shape")
            if not all(np.isfinite(a).all() for a in values):
                raise ValueError("Non-finite trace values")
            if not all(np.issubdtype(a.dtype, np.integer) for a in stamps):
                raise ValueError("Expected integer device timestamps")
            if not np.array_equal(stamps[0], stamps[1]):
                raise ValueError("X/Y timestamps do not match")
            ticks = stamps[0][0]
            if ticks[0] < 0 or np.any(ticks[1:] <= ticks[:-1]):
                raise ValueError("Trace timestamps do not increase")
            if self._grid_mode == 4:
                clockbase = float(self._device.clockbase())
                if not math.isfinite(clockbase) or clockbase <= 0:
                    raise ValueError("Invalid device clockbase")
                # Subtract before converting: timestamps may exceed 2**53.
                axis = (ticks - ticks[0]) / clockbase
            else:
                # Resampled values lie on the grid reported by LabOne. The
                # returned timestamps need not have this uniform spacing.
                steps = [
                    float(np.asarray(b["header"]["gridcoldelta"]).item())
                    for b in bursts
                ]
                if not all(math.isfinite(step) and step > 0 for step in steps):
                    raise ValueError("Invalid time-grid spacing")
                if steps[0] != steps[1]:
                    raise ValueError("X/Y time-grid spacing does not match")
                axis = np.arange(self._points) * steps[0]
            return axis, values[0][0].copy(), values[1][0].copy()
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise RuntimeError(f"Invalid or incomplete time trace: {exc}") from exc

    def _acquire_sweep(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        parameter = self._sweep_parameter
        assert parameter is not None
        path = f"/{self._device.serial.lower()}/demods/{self._demod_index}/sample"
        with ExitStack() as stack:
            original = parameter()
            module = self._device.session.modules.create_sweeper_module()
            stack.callback(parameter.set, original)
            self._cleanup(stack, module)
            module.device(self._device)
            module.gridnode(parameter)
            module.start(self._start)
            module.stop(self._stop)
            module.samplecount(self._points)
            module.xmapping(1 if self._spacing == "log" else 0)
            module.scan(0)
            module.loopcount(1)
            module.endless(0)
            # Use the user's filter settings. A positive bandwidth is required
            # by LabOne even though its value is ignored in manual mode.
            module.bandwidth(1.0)
            module.bandwidthcontrol(0)
            module.settling.time(self._settling_time)
            module.settling.inaccuracy(0.001)
            module.averaging.tc(10)
            module.averaging.sample(10)
            module.averaging.time(self._averaging_time)
            module.subscribe(path)
            module.execute()
            module.wait_done(timeout=self._timeout, sleep_time=0.05)
            data = module.read()
        try:
            if len(data[path]) != 1 or len(data[path][0]) != 1:
                raise ValueError("Expected one complete sweep")
            sample = data[path][0][0]
            # 'frequency' is the demodulator frequency, which need not be the
            # swept quantity (or the oscillator frequency for harmonics != 1).
            arrays = tuple(
                np.asarray(sample[c], dtype=float) for c in ("grid", "x", "y")
            )
            if any(
                a.shape != (self._points,) or not np.isfinite(a).all() for a in arrays
            ):
                raise ValueError("Unexpected sweep shape or non-finite values")
            if np.any(np.diff(arrays[0]) <= 0):
                raise ValueError("Sweep grid does not increase")
            return arrays[0].copy(), arrays[1].copy(), arrays[2].copy()
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise RuntimeError(f"Invalid or incomplete sweep trace: {exc}") from exc
