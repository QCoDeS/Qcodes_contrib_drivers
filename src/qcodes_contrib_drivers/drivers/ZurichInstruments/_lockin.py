"""Shared, non-configuring readout helpers for Zurich lock-in amplifiers."""

from collections.abc import Callable, Mapping, Sequence
from functools import partial
import math
from numbers import Integral
import sys
import threading
import time
from typing import Any, cast

import numpy as np
from qcodes.instrument import Instrument
from qcodes.parameters import MultiParameter, Parameter, ParamRawDataType
from qcodes.validators import ComplexNumbers, Enum, Numbers


def _sample_field(sample: Mapping[str, Any], field: str) -> Any:
    """Extract a scalar or a single-element vector without truncating data."""
    try:
        value = np.asarray(sample[field])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Demodulator sample has no valid {field!r} field") from exc
    if value.size != 1 or value.ndim > 1:
        raise ValueError(f"Expected one {field!r} value in demodulator sample")
    return value.item()


def _sample_xy(sample: Mapping[str, Any]) -> tuple[float, float]:
    try:
        x = float(_sample_field(sample, "x"))
        y = float(_sample_field(sample, "y"))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Invalid X/Y values in demodulator sample") from exc
    if not (math.isfinite(x) and math.isfinite(y)):
        raise ValueError("Non-finite X/Y values in demodulator sample")
    return x, y


def _sample_timestamp(sample: Mapping[str, Any]) -> int:
    value = _sample_field(sample, "timestamp")
    # Do not convert through float: device timestamps can exceed 2**53.
    if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
        raise ValueError("Demodulator sample has no valid positive integer timestamp")
    return int(value)


class ComplexSampleParameter(Parameter):
    """Return the latest sample as X + 1j*Y, without waiting for another sample.

    ``dict_parameter`` retains the constructor interface of the original MFLI
    helper. An instrument may supply ``check_readable`` to reject channels that
    cannot currently provide measurement data.
    """

    def __init__(
        self,
        *args: Any,
        dict_parameter: Parameter | None = None,
        check_readable: Callable[[], None] | None = None,
        read_lock: Any = None,
        **kwargs: Any,
    ):
        if dict_parameter is None:
            raise TypeError("ComplexSampleParameter requires a dict_parameter")
        self._dict_parameter = dict_parameter
        self._check_readable = check_readable
        self._read_lock = read_lock if read_lock is not None else threading.RLock()
        super().__init__(*args, **kwargs)

    def get_raw(self) -> ParamRawDataType:
        with self._read_lock:
            if self._check_readable is not None:
                self._check_readable()
            x, y = _sample_xy(self._dict_parameter.get())
            return complex(x, y)


class _ReadoutParameter(MultiParameter):
    """Four dataset quantities derived from the same demodulator sample."""

    def __init__(self, name: str, *, reader: "_DemodulatorReadout", **kwargs: Any):
        self._reader = reader
        super().__init__(
            name,
            names=("readout_x", "readout_y", "readout_r", "readout_theta"),
            labels=("X", "Y", "R", "Theta"),
            shapes=((), (), (), ()),
            setpoints=((), (), (), ()),
            units=("", "", "", "deg"),
            snapshot_get=False,
            snapshot_value=False,
            **kwargs,
        )

    def get_raw(self) -> tuple[float, float, float, float]:
        return self._reader.read()


class _DemodulatorReadout:
    def __init__(self, instrument: "LockinMixin", index: int):
        self.instrument = instrument
        self.index = index
        self.channel = instrument.demods[index]
        self.configuration: tuple[int, float | None] | None = None
        self.parameters: list[Parameter] = []
        self.unit_configured = False

    def _configuration(self) -> tuple[tuple[int, float | None], str | None]:
        source = int(self.channel.adcselect())
        inputs = self.instrument.sigins
        unit: str | None = None
        scaling: float | None = None
        if source == 0:
            unit, scaling = "V", float(inputs[0].scaling())
        elif source == 1:
            if self.instrument._lockin_model == "MFLI":
                unit, scaling = "A", float(self.instrument.currins[0].scaling())
            else:
                unit, scaling = "V", float(inputs[1].scaling())
        elif source in (8, 9):
            unit = "V"  # Physical auxiliary inputs.
        elif source == 174 and self.instrument._lockin_model == "MFLI":
            unit = ""  # The constant, dimensionless demodulator input.
        # Internal, trigger and oscillator-phase sources require explicit units.
        # A non-unit scaling factor may represent a transducer calibration.
        if scaling is not None and scaling != 1.0:
            unit = None
        return (source, scaling), unit

    def configure(self, unit: str | None = None, *, initial: bool = False) -> None:
        configuration, inferred_unit = self._configuration()
        if unit is not None and not isinstance(unit, str):
            raise TypeError("Readout unit must be a string or None")
        chosen_unit = inferred_unit if unit is None else unit
        if chosen_unit is None and not initial:
            raise ValueError("Cannot infer readout units; specify unit explicitly")
        self.configuration = configuration
        self.unit_configured = chosen_unit is not None
        units = (chosen_unit or "",) * 3 + ("deg",)
        for parameter, parameter_unit in zip(self.parameters, units):
            parameter.unit = parameter_unit
            parameter.cache.invalidate()
        combined = self.channel.readout
        combined.units = units
        combined.cache.invalidate()
        for parameter in [*self.parameters, combined]:
            parameter.metadata.update(
                signal_source=configuration[0],
                input_scaling=configuration[1],
                unit_configured=self.unit_configured,
            )

    def _check_configuration(self) -> None:
        current, _ = self._configuration()
        if not self.unit_configured or current != self.configuration:
            raise RuntimeError(
                f"Demodulator {self.index} readout units need configuration. "
                f"Call configure_readout(demod={self.index}, unit=...) before "
                "registering a new measurement; input source or scaling may have changed."
            )

    def component(self, index: int) -> float:
        return self.read()[index]

    def read(self) -> tuple[float, float, float, float]:
        with self.instrument._readout_lock:
            self.instrument._check_demodulator(self.index)
            self._check_configuration()
            timeout = float(self.instrument.acquisition_timeout())
            deadline = time.monotonic() + timeout
            baseline = self.channel.sample()
            _sample_xy(baseline)
            timestamp = _sample_timestamp(baseline)
            while time.monotonic() < deadline:
                sample = self.channel.sample()
                x, y = _sample_xy(sample)
                next_timestamp = _sample_timestamp(sample)
                if next_timestamp < timestamp:
                    raise RuntimeError(
                        "Demodulator timestamp moved backwards; reconnect"
                    )
                if time.monotonic() >= deadline:
                    break
                if next_timestamp > timestamp:
                    self.instrument._check_demodulator(self.index)
                    self._check_configuration()
                    return x, y, math.hypot(x, y), math.degrees(math.atan2(y, x))
                time.sleep(min(0.01, max(0.0, deadline - time.monotonic())))
            self.instrument._check_demodulator(self.index)
            raise TimeoutError(
                f"Demodulator {self.index} supplied no newer sample within {timeout:g} s; "
                "check the streaming rate and trigger, or increase acquisition_timeout"
            )


class LockinMixin:
    """Add readouts to existing vendor channels without changing their nodes.

    Concrete classes initialize the vendor driver first, then call
    ``_initialize_lockin``. The vendor remains responsible for connections,
    device settings, modules, and instrument lifecycle.
    """

    _lockin_model: str
    _measurement_demodulators: tuple[int, ...]
    _output_mixers: tuple[int, ...]
    # These members are provided by the vendor driver after its initialization.
    demods: Sequence[Any]
    sigins: Sequence[Any]
    currins: Sequence[Any]
    sigouts: Sequence[Any]
    extrefs: Sequence[Any]
    session: Any
    device_type: str
    acquisition_timeout: Parameter

    def _initialize_lockin(self) -> None:
        instrument = cast(Instrument, self)
        if self.device_type != self._lockin_model:
            raise ValueError(
                f"Expected {self._lockin_model}, connected to {self.device_type}"
            )
        # The two drivers normally share a vendor session. Serialize our reads
        # and metadata updates even when dond uses separate instrument threads.
        if not hasattr(self.session, "_qcodes_contrib_lockin_lock"):
            self.session._qcodes_contrib_lockin_lock = threading.RLock()
        self._readout_lock = self.session._qcodes_contrib_lockin_lock
        options = str(getattr(self, "device_options")()).upper()
        self._lockin_options = set(options.replace(",", " ").split())
        instrument.add_parameter(
            "acquisition_timeout",
            label="Readout timeout",
            unit="s",
            get_cmd=None,
            set_cmd=None,
            initial_value=5.0,
            vals=Numbers(1e-9, sys.float_info.max),
            docstring="Timeout waiting for a newer sample; transport timeouts are separate.",
        )
        self._readouts: dict[int, _DemodulatorReadout] = {}
        for index, demod in enumerate(self.demods):
            demod.add_parameter(
                "complex_sample",
                parameter_class=ComplexSampleParameter,
                dict_parameter=demod.sample,
                check_readable=partial(self._check_demodulator, index),
                read_lock=self._readout_lock,
                label="Vrms",  # Preserve the original MFLI metadata.
                vals=ComplexNumbers(),
                snapshot_get=False,
                snapshot_value=False,
            )
            if index not in self._measurement_demodulators:
                continue
            reader = _DemodulatorReadout(self, index)
            self._readouts[index] = reader
            for component, name in enumerate(("x", "y", "r", "theta")):
                demod.add_parameter(
                    name,
                    label=name.upper() if name != "theta" else "Theta",
                    get_cmd=partial(reader.component, component),
                    set_cmd=False,
                    vals=Numbers(),
                    snapshot_get=False,
                    snapshot_value=False,
                    docstring="Read one newer demodulator sample. Use readout for coherent X/Y/R/Theta.",
                )
                reader.parameters.append(demod.parameters[name])
            demod.add_parameter(
                "readout", parameter_class=_ReadoutParameter, reader=reader
            )
            reader.configure(initial=True)

        # With frequency-expansion options there may be several mixer signals.
        # Keep all inherited controls, but do not choose a convenience alias.
        expansion = (
            {"MD", "MF-MD"} if self._lockin_model == "MFLI" else {"MF", "UHF-MF"}
        )
        if not self._lockin_options.intersection(expansion):
            for output, mixer in zip(self.sigouts, self._output_mixers):
                amplitude = output.amplitudes[mixer].value
                enabled = output.enables[mixer].value
                output.add_parameter(
                    "amplitude",
                    label="Output peak amplitude",
                    unit="V",
                    get_cmd=amplitude.get,
                    set_cmd=amplitude.set,
                    vals=Numbers(),
                    docstring="Peak voltage at the configured load; independent of output on/off.",
                )
                output.add_parameter(
                    "amplitude_enabled",
                    label="Oscillator contribution enabled",
                    get_cmd=enabled.get,
                    set_cmd=enabled.set,
                    vals=Enum(0, 1),
                    docstring="Enable this oscillator contribution, separately from output on/off.",
                )

    def _check_demodulator(self, index: int) -> None:
        if (
            self._lockin_model == "MFLI"
            and index == 1
            and not self._lockin_options.intersection({"MD", "MF-MD"})
        ):
            raise RuntimeError(
                "MFLI demodulator 1 is reference-only and cannot supply measurements"
            )
        for reference in self.extrefs:
            if bool(reference.enable()) and int(reference.demodselect()) == index:
                raise RuntimeError(
                    f"Demodulator {index} is being used for external-reference recovery"
                )
        if not bool(self.demods[index].enable()):
            raise RuntimeError(
                f"Demodulator {index} streaming is disabled; configure its enable and rate before reading"
            )

    def configure_readout(self, demod: int = 0, *, unit: str | None = None) -> None:
        """Refresh readout metadata before registering a new measurement.

        No device setting or sample value is changed. If ``unit`` is omitted,
        infer V/A for an unscaled signal input, V for an auxiliary input, or an
        empty unit for the MFLI constant input. Other sources and scaled inputs
        require an explicit unit (``""`` is allowed for dimensionless results).
        Changing source/scaling during a run raises an error on the next read;
        reconfigure metadata and start a new measurement after such a change.
        The legacy ``complex_sample`` keeps its historical metadata.
        """
        if (
            isinstance(demod, bool)
            or not isinstance(demod, Integral)
            or demod not in self._readouts
        ):
            raise ValueError(f"No scalar readout is available for demodulator {demod}")
        with self._readout_lock:
            self._readouts[demod].configure(unit)
