"""Shared scalar and trace readout helpers for Zurich lock-in amplifiers.

This has been tested with MFLI and UHF-LI. See `docs/examples/ZurichInstruments_lockins.ipynb` for an example notebook.

Written by Edward Laird (http://wp.lancs.ac.uk/laird-group/)."""

from collections.abc import Callable, Mapping, Sequence
from functools import partial
import math
from numbers import Integral
import sys
import threading
import time
from typing import Any, cast, overload

import numpy as np
from qcodes.instrument import Instrument
from qcodes.parameters import MultiParameter, Parameter, ParamRawDataType
from qcodes.validators import ComplexNumbers, Enum, Numbers

from ._trace import TraceParameter


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
    """Selected dataset quantities derived from the same demodulator sample.

    Calling without arguments reads the values. Calling with component names,
    e.g. ``readout("r", "theta")`` or ``readout(parameters=("r", "theta"))``,
    returns a MultiParameter to register before measuring. Selection performs
    no acquisition and leaves the original parameter unchanged.
    """

    _components = ("x", "y", "r", "theta")

    def __init__(
        self,
        name: str,
        *,
        reader: "_DemodulatorReadout",
        components: tuple[str, ...] = _components,
        source: "_ReadoutParameter | None" = None,
        **kwargs: Any,
    ):
        self._reader = reader
        self._indices = tuple(self._components.index(item) for item in components)
        self._source = self if source is None else source
        self._selected_readouts: dict[tuple[str, ...], _ReadoutParameter] = {}
        kwargs.setdefault("docstring", self.__class__.__doc__)
        super().__init__(
            name,
            names=tuple(f"readout_{item}" for item in components),
            labels=tuple(("X", "Y", "R", "Theta")[i] for i in self._indices),
            shapes=((),) * len(components),
            setpoints=((),) * len(components),
            units=tuple(
                (source.units if source is not None else ("", "", "", "deg"))[i]
                for i in self._indices
            ),
            snapshot_get=False,
            snapshot_value=False,
            **kwargs,
        )

    @overload
    def __call__(self) -> tuple[float, ...]: ...

    @overload
    def __call__(self, component: str, *components: str) -> "_ReadoutParameter": ...

    @overload
    def __call__(self, *, parameters: Sequence[str]) -> "_ReadoutParameter": ...

    @overload
    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...

    def __call__(
        self, *components: Any, parameters: Sequence[str] | None = None, **kwargs: Any
    ) -> Any:
        if kwargs:
            raise TypeError(f"Unexpected readout arguments: {', '.join(kwargs)}")
        if not components and parameters is None:
            return self.get()
        if parameters is not None:
            if components:
                raise TypeError("Use positional components or parameters, not both")
            if isinstance(parameters, str) or not isinstance(parameters, Sequence):
                raise TypeError("parameters must be a sequence of component names")
            components = tuple(parameters)
        if not components or any(item not in self._components for item in components):
            raise ValueError("Select at least one component from x, y, r, theta")
        if len(set(components)) != len(components):
            raise ValueError("Readout components must be unique")
        source = self._source
        if components == self._components:
            return source
        with self._reader.instrument._readout_lock:
            if components not in source._selected_readouts:
                source._selected_readouts[components] = _ReadoutParameter(
                    f"{source.name}_{'_'.join(components)}",
                    reader=self._reader,
                    components=components,
                    source=source,
                    instrument=source.instrument,
                    bind_to_instrument=False,
                    metadata=source.metadata.copy(),
                )
            return source._selected_readouts[components]

    def get_raw(self) -> tuple[float, ...]:
        values = self._reader.read()
        return tuple(values[i] for i in self._indices)


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
        combined_parameters = [combined, *combined._selected_readouts.values()]
        for parameter in combined_parameters:
            parameter.units = tuple(units[i] for i in parameter._indices)
            parameter.cache.invalidate()
        for parameter in [*self.parameters, *combined_parameters]:
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
    serial: str
    clockbase: Parameter

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
        for reference_index, reference in enumerate(self.extrefs):
            if not bool(reference.enable()):
                continue
            demodselect = getattr(reference, "demodselect", None)
            if demodselect is None:
                # Do not guess which demodulator firmware uses for recovery.
                raise RuntimeError(
                    f"Cannot verify external-reference recovery for {self._lockin_model}: "
                    f"extrefs[{reference_index}].demodselect is unavailable while "
                    "the external reference is enabled"
                )
            if int(demodselect()) == index:
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

    def configure_trace(
        self,
        *,
        duration: float | None = None,
        grid_mode: int | None = None,
        sweep_parameter: Parameter | None = None,
        start: float | None = None,
        stop: float | None = None,
        points: int = 201,
        demod: int = 0,
        parameters: Sequence[str] = ("x", "y"),
        name: str | None = None,
        timeout: float = 60.0,
        spacing: str | None = None,
        settling_time: float | None = None,
        averaging_time: float | None = None,
    ) -> TraceParameter:
        """Prepare a trace parameter for ``do0d`` or an outer ``do1d`` sweep.

        Supply ``duration`` in seconds for an interpolated time trace, or use
        ``grid_mode=4`` without duration for exact samples. Supply
        ``sweep_parameter`` with ``start`` and ``stop`` for a parameter sweep.
        Each subsequent read
        acquires one fresh trace, including all selected components and their
        actual time/grid setpoints. This method reads configuration but neither
        changes instrument settings nor starts an acquisition.

        Args:
            duration: Time-trace duration, including the final sample interval.
                The nominal time grid is ``arange(points) * duration / points``.
                After acquisition, setpoints use LabOne's reported grid spacing.
                Continuous streaming must be enabled with rate >= points/duration.
                Required for grid modes 1 and 2; must be omitted for mode 4.
            grid_mode: Time-trace sampling: 1 (nearest neighbour), 2 (linear,
                default), or 4 (exact, without interpolation). In mode 4, points
                and the actual demodulator streaming rate determine duration;
                the nominal time grid is ``arange(points) / rate``. Reconfigure
                the trace after changing that rate. Omit for parameter sweeps.
            sweep_parameter: Readable/writable native Zurich node on this device,
                e.g. ``oscs[0].freq``. The node must support LabOne sweeping;
                convenience aliases and parameters on other instruments cannot
                be used. Its original value is restored after every acquisition,
                including failure. Sweeps are sequential and ascending.
            start: Sweep start in the native parameter's units.
            stop: Sweep stop (greater than start), in the same units.
            points: Number of points per trace; an integer >= 2.
            demod: Measurement demodulator, indexed from zero.
            parameters: Nonempty selection of x, y, r, theta in return order.
                R and Theta are calculated from aligned X/Y, including for
                sweeps (polar conversion of averaged X/Y, not averaged R/Theta).
                Theta is in degrees; other units follow ``configure_readout``.
            name: Parameter name on the demodulator. If omitted, use time_trace
                or sweep_trace with a numerical suffix for subsequent calls.
                Explicit names must be unused. Binding includes configuration
                metadata in station snapshots without acquiring trace data.
            timeout: Seconds to wait for completion (transport timeouts separate).
            spacing: Sweep-only: 'linear' (default) or 'log'. Log requires start > 0.
            settling_time: Sweep-only: minimum settling time per point in seconds
                (default 0). LabOne also waits for filter settling to 0.001
                inaccuracy, taking whichever settling requirement is longer.
            averaging_time: Sweep-only: minimum averaging duration per point in
                seconds (default 0). At least 10 filter time constants and 10
                samples are also required. Existing filter bandwidth is retained.

        Time traces acquire streamed demodulator X/Y using the selected grid
        mode; they are not raw scope waveforms. Sweeps change the selected
        setting during acquisition. Keep trace configuration/units fixed within
        a dataset; call this method again before a new dataset to change them.
        Advanced triggering and sweep modes remain available via the vendor API.

        Examples:
            >>> trace = lockin.configure_trace(duration=0.5, points=201)
            >>> do0d(trace, do_plot=True)
            >>> trace = lockin.configure_trace(points=1000, grid_mode=4)
            >>> x, y = trace()
            >>> trace = lockin.configure_trace(
            ...     sweep_parameter=lockin.oscs[0].freq, start=1e3, stop=100e3,
            ...     parameters=("r", "theta"),
            ... )
            >>> do0d(trace, do_plot=True)
        """
        with self._readout_lock:
            return TraceParameter(
                self, duration=duration, grid_mode=grid_mode,
                sweep_parameter=sweep_parameter,
                start=start, stop=stop, points=points, demod=demod,
                parameters=parameters, name=name, timeout=timeout, spacing=spacing,
                settling_time=settling_time, averaging_time=averaging_time,
            )
