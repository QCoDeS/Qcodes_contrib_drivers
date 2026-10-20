"""Driver for the Keithley 2280S precision DC power supplies.

Command reference: Keithley 077085503, March 2019, sections 3 and 7.
https://download.tek.com/manual/077085503_2280_Ref_Mar_20191.pdf
"""

from __future__ import annotations

import csv
import re
from contextlib import contextmanager
from functools import partial
from typing import TYPE_CHECKING

import numpy as np
from qcodes.instrument import InstrumentChannel, VisaInstrument, VisaInstrumentKWArgs
from qcodes.parameters import MultiParameter, Parameter, create_on_off_val_mapping
from qcodes.validators import Enum, Ints, MultiType, Numbers, Strings

if TYPE_CHECKING:
    from collections.abc import Iterator

    import numpy.typing as npt
    from typing_extensions import Unpack


_ON_OFF = create_on_off_val_mapping(on_val=1, off_val=0)
_PRESETS = Enum("MIN", "MAX", "DEF")
_DATA_ELEMENTS = ("READ", "SOUR", "UNIT", "MODE", "DATE", "TIME", "TST", "REL", "RST")
_STATISTICS = ("MIN", "MAX", "MEAN", "PKPK", "SDEV", "NONE")
_STAT_ELEMENTS = ("READ", "UNIT", "TST", "RNUM")
_NUMBER = re.compile(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?)(?:[AVs]|RNDG#)?")


def _unquote(response: str) -> str:
    return response.strip().strip('"').strip("'")


def _parse_data(response: str) -> tuple[float | str, ...]:
    """Parse numeric fields with optional units, preserving dates and modes."""
    fields = next(csv.reader([response.strip()]))
    result: list[float | str] = []
    for field in fields:
        field = field.strip()
        match = _NUMBER.fullmatch(field)
        result.append(float(match[1]) if match else field)
    return tuple(result)


def _validate_elements(value: str, allowed: tuple[str, ...]) -> str:
    """Validate a comma-separated list of SCPI short names."""
    parts = [part.strip().upper() for part in value.split(",")]
    if not 1 <= len(parts) <= len(allowed) or any(p not in allowed for p in parts):
        raise ValueError(f"Expected a comma-separated selection from {allowed}")
    if "NONE" in parts and len(parts) != 1:
        raise ValueError("NONE cannot be combined with other statistics")
    return ",".join(parts)


class _ConcurrentMeasurement(MultiParameter):
    """Acquire current and voltage together, with separate dataset columns."""

    def __init__(self, name: str, instrument: Keithley2280SSense, **kwargs) -> None:
        super().__init__(
            name,
            instrument=instrument,
            names=("current", "voltage"),
            labels=("Measured current", "Measured voltage"),
            units=("A", "V"),
            shapes=((), ()),
            setpoints=((), ()),
            snapshot_get=False,
            **kwargs,
        )
        self._sense = instrument

    def get_raw(self) -> tuple[float, float]:
        current, voltage = self._sense.supply._measure("CONC")
        return current, voltage


class Keithley2280SSense(InstrumentChannel):
    """Measurement settings for voltage, current, or concurrent measurements.

    Concurrent range and relative offset apply to current. The instrument has
    only one voltage range. ``digits`` affects the display only; ``resolution``
    also changes NPLC, autozero, filtering, and source delay.

    On the concurrent channel, ``current`` and ``voltage`` each acquire both
    quantities and return only the named value, keeping both on the display.
    Reading them separately triggers two acquisitions. Use ``measure`` to
    obtain both values from one acquisition.
    """

    def __init__(self, parent: Keithley2280S, name: str, function: str) -> None:
        super().__init__(parent, name)
        self.supply = parent
        self._function = function
        prefix = f":SENS:{function}"
        voltage = function == "VOLT"
        unit = "V" if voltage else "A"
        maximum = parent.max_voltage if voltage else parent.max_current

        self.nplc: Parameter = self.add_parameter(
            "nplc",
            label=f"{name.capitalize()} integration time",
            get_cmd=f"{prefix}:NPLC?",
            set_cmd=self._set_nplc,
            get_parser=float,
            vals=MultiType(Numbers(0.002, 15), _PRESETS),
            docstring="Integration in PLC; maximum 12 at 50 Hz, 15 at 60 Hz.",
        )
        self.digits: Parameter = self.add_parameter(
            "digits",
            get_cmd=f"{prefix}:DIG?",
            set_cmd=f"{prefix}:DIG {{}}",
            get_parser=int,
            vals=MultiType(Enum(4, 5, 6), _PRESETS),
        )
        self.resolution: Parameter = self.add_parameter(
            "resolution",
            get_cmd=False,
            set_cmd=f"{prefix}:RES {{}}",
            vals=Enum(4, 5, 6),
            docstring="Select the 4.5, 5.5, or 6.5 digit measurement preset.",
        )
        self.range: Parameter = self.add_parameter(
            "range",
            unit=unit,
            get_cmd=f"{prefix}:RANG?",
            set_cmd=f"{prefix}:RANG {{}}",
            get_parser=float,
            vals=(
                Enum(parent.max_voltage)
                if voltage
                else MultiType(Numbers(0, 10), _PRESETS)
            ),
            docstring="A fixed current range disables autoranging; values round up.",
        )
        if not voltage:
            self.autorange: Parameter = self.add_parameter(
                "autorange",
                get_cmd=f"{prefix}:RANG:AUTO?",
                set_cmd=f"{prefix}:RANG:AUTO {{}}",
                val_mapping=_ON_OFF,
            )
        self.filter_enabled: Parameter = self.add_parameter(
            "filter_enabled",
            get_cmd=f"{prefix}:AVER:STAT?",
            set_cmd=f"{prefix}:AVER:STAT {{}}",
            val_mapping=_ON_OFF,
        )
        self.filter_count: Parameter = self.add_parameter(
            "filter_count",
            get_cmd=f"{prefix}:AVER:COUN?",
            set_cmd=f"{prefix}:AVER:COUN {{}}",
            get_parser=int,
            vals=MultiType(Ints(2, 100), _PRESETS),
        )
        self.filter_window: Parameter = self.add_parameter(
            "filter_window",
            unit="%",
            get_cmd=f"{prefix}:AVER:WIND?",
            set_cmd=f"{prefix}:AVER:WIND {{}}",
            get_parser=float,
            vals=MultiType(Numbers(0.01, 100), _PRESETS),
            docstring="Rounds up to 0.01, 0.1, 1, 10, or 100 percent.",
        )
        self.filter_type: Parameter = self.add_parameter(
            "filter_type",
            get_cmd=f"{prefix}:AVER:TCON?",
            set_cmd=f"{prefix}:AVER:TCON {{}}",
            val_mapping={"moving": "MOV"},
        )
        self.relative: Parameter = self.add_parameter(
            "relative",
            unit=unit,
            get_cmd=f"{prefix}:REF?",
            set_cmd=f"{prefix}:REF {{}}",
            get_parser=float,
            vals=Numbers(-maximum, maximum),
        )
        self.relative_enabled: Parameter = self.add_parameter(
            "relative_enabled",
            get_cmd=f"{prefix}:REF:STAT?",
            set_cmd=f"{prefix}:REF:STAT {{}}",
            val_mapping=_ON_OFF,
        )
        if function == "CONC":
            self.add_parameter("measure", parameter_class=_ConcurrentMeasurement)
            self.current: Parameter = self.add_parameter(
                "current",
                label="Measured current",
                unit="A",
                get_cmd=lambda: parent._measure("CONC")[0],
                set_cmd=False,
                snapshot_get=False,
                docstring="Acquire current and voltage together; return current only.",
            )
            self.voltage: Parameter = self.add_parameter(
                "voltage",
                label="Measured voltage",
                unit="V",
                get_cmd=lambda: parent._measure("CONC")[1],
                set_cmd=False,
                snapshot_get=False,
                docstring="Acquire current and voltage together; return voltage only.",
            )
        else:
            self.add_parameter(
                "measure",
                label=f"Measured {name}",
                unit=unit,
                get_cmd=lambda: parent._measure(function)[0],
                set_cmd=False,
                snapshot_get=False,
            )

    def _set_nplc(self, value: float | str) -> None:
        if not isinstance(value, str):
            maximum = 12 if self.supply.line_frequency() == 50 else 15
            Numbers(0.002, maximum).validate(value)
        self.write(f":SENS:{self._function}:NPLC {value}")

    def acquire_relative(self) -> None:
        """Take a reading of this function and store its relative offset.

        A fresh reading is needed after changing function on firmware 01.07b.
        The output must be on; relative subtraction is enabled separately.
        """
        self.supply._measure(self._function)
        self.write(f":SENS:{self._function}:REF:ACQ")


class Keithley2280SCalculate(InstrumentChannel):
    """Statistics over the instrument's reading buffer.

    ``data`` returns a flat tuple in the instrument's response order, with
    timestamps preserved as strings. UNIT adds suffixes, not separate fields.
    Metadata is available only when all selected statistics are MIN and/or MAX.
    Use ``statistics()`` for an unambiguous dictionary of numeric results.
    """

    def __init__(self, parent: Keithley2280S, name: str) -> None:
        super().__init__(parent, name)
        self.format: Parameter = self.add_parameter(
            "format",
            get_cmd=":CALC2:FORM?",
            set_cmd=partial(self._set_format, ":CALC2:FORM", _STATISTICS, False),
            get_parser=_unquote,
            vals=Strings(),
        )
        self.data_format: Parameter = self.add_parameter(
            "data_format",
            get_cmd=":CALC2:FORM:ELEM?",
            set_cmd=partial(self._set_format, ":CALC2:FORM:ELEM", _STAT_ELEMENTS, True),
            get_parser=_unquote,
            vals=Strings(),
        )
        self.function: Parameter = self.add_parameter(
            "function",
            get_cmd=":CALC2:FUNC?",
            set_cmd=":CALC2:FUNC {}",
            get_parser=_unquote,
            vals=Enum("CURR", "VOLT"),
        )
        self.enabled: Parameter = self.add_parameter(
            "enabled",
            get_cmd=":CALC2:STAT?",
            set_cmd=":CALC2:STAT {}",
            val_mapping=_ON_OFF,
        )
        self.data: Parameter = self.add_parameter(
            "data",
            get_cmd=":CALC2:IMM?",
            get_parser=_parse_data,
            set_cmd=False,
            snapshot_get=False,
        )

    def _set_format(
        self, command: str, allowed: tuple[str, ...], quoted: bool, value: str
    ) -> None:
        value = _validate_elements(value, allowed)
        self.write(f'{command} "{value}"' if quoted else f"{command} {value}")

    def statistics(self) -> dict[str, float]:
        """Calculate all five statistics, restoring formats and enabled state.

        Query each statistic separately because firmware versions differ in the
        order of PKPK and SDEV in a combined response.
        """
        old_format = self.format()
        old_elements = self.data_format()
        old_enabled = self.enabled()
        try:
            self.enabled(True)
            self.data_format("READ")
            result = {}
            for statistic in _STATISTICS[:-1]:
                self.format(statistic)
                result[statistic.lower()] = float(self.data()[0])
            return result
        finally:
            self.format(old_format)
            self.data_format(old_elements)
            self.enabled(old_enabled)


class Keithley2280SBuffer(InstrumentChannel):
    """The 2280S's single reading buffer (2 to 2500 readings)."""

    def __init__(self, parent: Keithley2280S, name: str) -> None:
        super().__init__(parent, name)
        self.supply = parent
        self.size: Parameter = self.add_parameter(
            "size",
            get_cmd=":TRAC:POIN?",
            set_cmd=":TRAC:POIN {}",
            get_parser=int,
            vals=Ints(2, 2500),
        )
        self.number_of_readings: Parameter = self.add_parameter(
            "number_of_readings", get_cmd=":TRAC:POIN:ACT?", get_parser=int
        )
        self.feed: Parameter = self.add_parameter(
            "feed",
            get_cmd=":TRAC:FEED?",
            set_cmd=":TRAC:FEED {}",
            vals=Enum("SENS", "CALC"),
        )
        self.feed_control: Parameter = self.add_parameter(
            "feed_control",
            get_cmd=":TRAC:FEED:CONT?",
            set_cmd=":TRAC:FEED:CONT {}",
            vals=Enum("NEV", "NEXT", "ALW"),
        )
        self.autoclear: Parameter = self.add_parameter(
            "autoclear",
            get_cmd=":TRAC:CLE:AUTO?",
            set_cmd=":TRAC:CLE:AUTO {}",
            val_mapping=_ON_OFF,
        )

    def clear_buffer(self) -> None:
        """Stop acquisition and clear readings; continuous initiation is disabled."""
        self.supply.continuous(False)
        self.supply.abort()
        self.write(":TRAC:CLE")

    def get_data(
        self, start: int = 1, end: int | None = None, elements: str = "READ,SOUR,REL"
    ) -> tuple[float | str, ...]:
        """Read an inclusive range of buffer indices as a flat tuple.

        For concurrent data with the default elements, each record contains
        current (A), voltage (V), and relative time (s), in that order.
        The instrument controls element order, regardless of the supplied order.
        """
        elements = _validate_elements(elements, _DATA_ELEMENTS)
        Ints(1, 2500).validate(start)
        if end is None:
            end = self.number_of_readings()
            if end == 0 and start == 1:
                return ()
        Ints(start, 2500).validate(end)
        return _parse_data(self.ask(f':TRAC:DATA:SEL? {start},{end},"{elements}"'))


class Keithley2280S(VisaInstrument):
    """Keithley 2280S-32-6 and 2280S-60-3 DC power supplies.

    ``source_voltage`` and ``source_current`` are numeric setpoints suitable
    for do1d/do2d. The current setpoint is the current limit in CV operation;
    the load determines whether the supply operates in CV or CC mode.

    Measurement parameters are ``voltage.measure``, ``current.measure``, and
    the two-output MultiParameter ``concurrent.measure``. They select their
    measurement function, temporarily select a numeric response format, and
    restore the previous format. The output must already be on.

    ``concurrent.current`` and ``concurrent.voltage`` each acquire both
    quantities but return a single scalar, for recording only one quantity
    while displaying both. Use ``concurrent.measure`` for a paired reading.

    Construction does not reset the instrument unless ``reset=True``.
    Source limits are selected from ``*IDN?``, and NPLC is checked against the
    instrument's line frequency. The hardware enforces ``voltage_limit`` too.
    """

    default_terminator = "\n"

    def __init__(
        self,
        name: str,
        address: str,
        reset: bool = False,
        **kwargs: Unpack[VisaInstrumentKWArgs],
    ) -> None:
        super().__init__(name, address, **kwargs)
        model = self.get_idn()["model"]
        limits = {"2280S-32-6": (32.0, 6.1), "2280S-60-3": (60.0, 3.3)}
        if model not in limits:
            self.close()
            raise ValueError(f"Unsupported Keithley model: {model!r}")
        self.max_voltage, self.max_current = limits[model]

        self.source_voltage: Parameter = self.add_parameter(
            "source_voltage",
            label="Source voltage",
            unit="V",
            get_cmd=":SOUR:VOLT?",
            set_cmd=self._set_voltage,
            get_parser=float,
            vals=Numbers(0, self.max_voltage),
        )
        self.source_current: Parameter = self.add_parameter(
            "source_current",
            label="Current limit",
            unit="A",
            get_cmd=":SOUR:CURR?",
            set_cmd=":SOUR:CURR {}",
            get_parser=float,
            vals=Numbers(0, self.max_current),
        )
        self.voltage_limit: Parameter = self.add_parameter(
            "voltage_limit",
            unit="V",
            get_cmd=":SOUR:VOLT:LIM?",
            set_cmd=":SOUR:VOLT:LIM {}",
            get_parser=float,
            vals=Numbers(0, self.max_voltage),
            docstring="Maximum voltage setpoint; lowering it can lower the output.",
        )
        self.output: Parameter = self.add_parameter(
            "output",
            get_cmd=":OUTP?",
            set_cmd=":OUTP {}",
            val_mapping={"off": 0, "on": 1, "disabled": 2},
            docstring=(
                "off, on, or disabled. Disabled also prevents front-panel enabling. "
                "Measurements require on."
            ),
        )
        self.voltage_protection: Parameter = self.add_parameter(
            "voltage_protection",
            unit="V",
            get_cmd=":SOUR:VOLT:PROT?",
            set_cmd=":SOUR:VOLT:PROT {}",
            get_parser=float,
            vals=Numbers(0.5, self.max_voltage + 1),
        )
        self.current_protection: Parameter = self.add_parameter(
            "current_protection",
            unit="A",
            get_cmd=":SOUR:CURR:PROT?",
            set_cmd=":SOUR:CURR:PROT {}",
            get_parser=float,
            vals=Numbers(0.1, self.max_current),
        )
        self.protection_tripped: Parameter = self.add_parameter(
            "protection_tripped", get_cmd=":OUTP:PROT:TRIP?", get_parser=_unquote
        )
        self.source_delay: Parameter = self.add_parameter(
            "source_delay",
            unit="s",
            get_cmd=":SOUR:DEL?",
            set_cmd=":SOUR:DEL {}",
            get_parser=float,
            vals=Numbers(0, 99),
        )
        self.source_delay_enabled: Parameter = self.add_parameter(
            "source_delay_enabled",
            get_cmd=":SOUR:DEL:STAT?",
            set_cmd=":SOUR:DEL:STAT {}",
            val_mapping=_ON_OFF,
        )
        self.function: Parameter = self.add_parameter(
            "function",
            get_cmd=":SENS:FUNC?",
            set_cmd=':SENS:FUNC "{}"',
            get_parser=lambda value: _unquote(value).split(":")[0],
            vals=Enum("VOLT", "CURR", "CONC"),
        )
        self.line_frequency: Parameter = self.add_parameter(
            "line_frequency", unit="Hz", get_cmd=":SYST:LFR?", get_parser=float
        )
        self.autozero: Parameter = self.add_parameter(
            "autozero",
            get_cmd=":SYST:AZER?",
            set_cmd=":SYST:AZER {}",
            val_mapping=_ON_OFF,
        )
        self.arm_count: Parameter = self.add_parameter(
            "arm_count",
            get_cmd=":ARM:COUN?",
            set_cmd=":ARM:COUN {}",
            get_parser=int,
            vals=MultiType(Ints(1, 2500), _PRESETS),
        )
        self.arm_source: Parameter = self.add_parameter(
            "arm_source",
            get_cmd=":ARM:SOUR?",
            set_cmd=":ARM:SOUR {}",
            vals=Enum("IMM", "EXT", "MAN", "BUS"),
        )
        self.trigger_count: Parameter = self.add_parameter(
            "trigger_count",
            get_cmd=":TRIG:COUN?",
            set_cmd=":TRIG:COUN {}",
            get_parser=int,
            vals=MultiType(Ints(1, 2500), _PRESETS),
        )
        self.trigger_source: Parameter = self.add_parameter(
            "trigger_source",
            get_cmd=":TRIG:SOUR?",
            set_cmd=":TRIG:SOUR {}",
            vals=Enum("IMM", "EXT", "MAN"),
        )
        self.sample_count: Parameter = self.add_parameter(
            "sample_count",
            get_cmd=":TRIG:SAMP:COUN?",
            set_cmd=":TRIG:SAMP:COUN {}",
            get_parser=int,
            vals=MultiType(Ints(1, 2500), _PRESETS),
        )
        self.continuous: Parameter = self.add_parameter(
            "continuous",
            get_cmd=":INIT:CONT?",
            set_cmd=":INIT:CONT {}",
            val_mapping=_ON_OFF,
        )
        self.data_format: Parameter = self.add_parameter(
            "data_format",
            get_cmd=":FORM:ELEM?",
            set_cmd=self._set_data_format,
            get_parser=_unquote,
            vals=Strings(),
        )
        self.brightness: Parameter = self.add_parameter(
            "brightness",
            unit="%",
            get_cmd=":DISP:BRIG?",
            set_cmd=":DISP:BRIG {}",
            get_parser=int,
            vals=MultiType(Ints(5, 100), _PRESETS),
        )
        self.screen: Parameter = self.add_parameter(
            "screen",
            get_cmd=False,
            set_cmd=":DISP:SCRE {}",
            vals=Enum("HOME", "GRAP", "DAT"),
        )
        self.display_text: Parameter = self.add_parameter(
            "display_text",
            get_cmd=False,
            set_cmd=self._set_display_text,
            vals=Strings(max_length=24),
        )
        self.gpib_address: Parameter = self.add_parameter(
            "gpib_address",
            get_cmd=":SYST:GPIB:ADDR?",
            set_cmd=":SYST:GPIB:ADDR {}",
            get_parser=int,
            vals=Ints(1, 30),
        )
        self.opc: Parameter = self.add_parameter(
            "opc",
            get_cmd="*OPC?",
            get_parser=lambda value: bool(int(value)),
            snapshot_get=False,
        )
        self.error: Parameter = self.add_parameter(
            "error", get_cmd=self.get_error, snapshot_get=False
        )
        self.voltage = Keithley2280SSense(self, "voltage", "VOLT")
        self.current = Keithley2280SSense(self, "current", "CURR")
        self.concurrent = Keithley2280SSense(self, "concurrent", "CONC")
        self.calculate = Keithley2280SCalculate(self, "calculate")
        self.buffer = Keithley2280SBuffer(self, "buffer")
        for channel in (
            self.voltage,
            self.current,
            self.concurrent,
            self.calculate,
            self.buffer,
        ):
            self.add_submodule(channel.short_name, channel)
        if reset:
            self.reset()
        self.connect_message()

    def _set_voltage(self, value: float) -> None:
        Numbers(0, self.voltage_limit()).validate(value)
        self.write(f":SOUR:VOLT {value}")

    def _set_data_format(self, value: str) -> None:
        value = _validate_elements(value, _DATA_ELEMENTS)
        self.write(f':FORM:ELEM "{value}"')

    def _set_display_text(self, value: str) -> None:
        if any(char in value for char in '\r\n"'):
            raise ValueError("Display text cannot contain quotes or line breaks")
        self.write(f':DISP:USER:TEXT "{value}"')

    @contextmanager
    def _temporary_format(self, elements: str) -> Iterator[None]:
        previous = self.data_format()
        try:
            if previous != elements:
                self.data_format(elements)
            yield
        finally:
            if previous != elements:
                self.data_format(previous)

    def _measure(self, function: str) -> tuple[float, ...]:
        if self.output() != "on":
            raise RuntimeError("Enable the output before making a measurement")
        # In concurrent mode READ is current, and SOUR is measured voltage.
        elements = "READ,SOUR" if function == "CONC" else "READ"
        with self._temporary_format(elements):
            values = _parse_data(self.ask(f":MEAS:{function}?"))
        expected = 2 if function == "CONC" else 1
        if len(values) != expected or not all(isinstance(v, float) for v in values):
            raise ValueError(f"Unexpected {function} measurement response: {values!r}")
        return tuple(float(value) for value in values)

    def read(self) -> tuple[float | str, ...]:
        """Trigger acquisition and return the first reading in ``data_format``.

        Honors the configured trigger model; external/manual triggers can block
        until the VISA timeout. For a simple single reading use a measure parameter.
        """
        return _parse_data(self.ask(":READ?"))

    def fetch(self) -> tuple[float | str, ...]:
        """Fetch the latest reading without triggering, in ``data_format``."""
        return _parse_data(self.ask(":FETC?"))

    def acquire(self, count: int) -> npt.NDArray[np.float64]:
        """Acquire a finite concurrent trace, returning columns current, voltage, time.

        Units are A, V, s. This clears the buffer and configures immediate,
        noncontinuous triggering, raw sense data, and ``count`` readings.
        The output must already be on. Increase ``timeout`` for long acquisitions.
        Measurement settings (NPLC, range, and filtering) are retained.
        """
        Ints(2, 2500).validate(count)
        if self.output() != "on":
            raise RuntimeError("Enable the output before acquiring a trace")
        self.buffer.clear_buffer()
        self.function("CONC")
        self.buffer.size(count)
        self.buffer.feed("SENS")
        self.buffer.feed_control("NEXT")
        self.arm_source("IMM")
        self.arm_count(1)
        self.trigger_source("IMM")
        self.trigger_count(count)
        self.sample_count(1)
        try:
            self.initiate()
            self.opc()
            values = self.buffer.get_data(1, count)
            data = np.asarray(values, dtype=float)
            if data.size != count * 3:
                raise ValueError(f"Expected {count} current/voltage/time records")
            return data.reshape(count, 3)
        finally:
            self.abort()

    def get_error(self) -> tuple[int, str]:
        """Pop the oldest error; code zero means the queue is empty."""
        code, message = next(
            csv.reader([self.ask(":SYST:ERR?")], skipinitialspace=True)
        )
        return int(code), message

    def reset(self) -> None:
        """Restore instrument defaults, including turning the output off."""
        self.write("*RST")
        self.invalidate_cache()

    def clear(self) -> None:
        """Clear status registers and the error queue (SCPI ``*CLS``)."""
        self.write("*CLS")

    def trigger(self) -> None:
        """Send a bus trigger; select BUS as the arm source first."""
        self.write("*TRG")

    def force_trigger(self) -> None:
        """Bypass the current arm or trigger event detector."""
        self.write(":FORC:TRIG")

    def wait(self) -> None:
        """Queue ``*WAI``; use ``opc()`` to wait on the Python side."""
        self.write("*WAI")

    def abort(self) -> None:
        """Abort the trigger model; continuous initiation can restart it."""
        self.write(":ABOR")

    def initiate(self) -> None:
        """Start the configured trigger model."""
        self.write(":INIT")

    def clear_text(self) -> None:
        """Clear the custom display message."""
        self.write(":DISP:CLE")

    def clear_error(self) -> None:
        """Clear the error queue."""
        self.write(":SYST:ERR:CLE")

    def clear_protection(self) -> None:
        """Clear a latched output protection fault."""
        self.write(":OUTP:PROT:CLE")

    def local(self) -> None:
        """Return control to the front panel."""
        self.write(":SYST:LOC")

    def opc_set(self) -> None:
        """Set the operation-complete event bit when pending operations finish."""
        self.write("*OPC")

    def self_test(self) -> bool:
        """Run the instrument self-test; True means it passed."""
        return int(self.ask("*TST?")) == 0
