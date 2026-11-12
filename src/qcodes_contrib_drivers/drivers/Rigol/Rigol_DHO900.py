"""QCoDeS driver for the Rigol DHO900 series oscilloscopes.

Models: DHO914, DHO914S, DHO924, DHO924S (four analog channels; the "S" models have
a built-in 25 MHz function generator). The DHO800 series shares the programming
guide; the driver connects to it as well, but has only been run on a DHO914S.

Programming reference: RIGOL DHO800/DHO900 Programming Guide (August 2023).
Tested on a DHO914S, firmware 00.01.04, over USBTMC (NI-VISA).

Where the instrument deviates from the guide, the driver follows the instrument:

- ``*OPC?`` returns 0 while an acquisition is in progress instead of waiting, so the
  end of a single acquisition is detected by polling ``:TRIGger:STATus?`` for STOP
  (:meth:`RigolDHO900.digitize`).
- Out-of-range values are clipped without an error (a vertical scale of 1000 V/div
  becomes 100 V/div, a generator frequency of 30 MHz becomes 25 MHz). The driver
  refuses them against the limits of the guide or, where they differ, of the
  instrument, which depend on other settings (probe ratio, vertical scale, waveform
  function), and reads back the settings whose limits depend on the instrument state
  (memory depth, horizontal offset, zoom, pulse widths, delay calibration,
  measurement thresholds): a value the instrument changed raises ``ValueError``
  naming the value it set.
- Setting the generator above 10 MHz lowers an amplitude above 5 V to 5 V without an
  error; the driver refuses such a frequency.
- A query the instrument rejects receives no response at all, so the client waits
  for the full VISA timeout. The driver avoids such queries (the DVM reading while
  the DVM is off, the long form ``:SOURce:MOD:AM:INTernal:FREQuency?``).
- A device clear (USBTMC) after such a query leaves the USB interface unable to
  respond (VI_ERROR_INP_PROT_VIOL, then timeouts); repeated, the instrument drops
  off the bus until it is power-cycled, while its display keeps working. The
  driver therefore connects without a device clear (``device_clear=False``).
- The modulation type is ignored without an error while the modulation is off, and
  the modulation settings (depth, deviation, modulating frequency and waveform)
  unless the modulation is on and of their type; the driver refuses a change
  otherwise. The modulating waveforms are accepted only as SIN, SQU, TRI, UPRAMP,
  DNRAMP and NOISE (the guide's SINusoid, UPR, NOIS etc. are rejected, -222), and
  a query returns these words, not the guide's UPR, DNR and NOIS.
- The counter statistics (``:COUNter:TOTalize:ENABle``) are rejected (-200) while
  the counter is off.
- The measurement thresholds (``:MEASure:SETup:MAX`` etc.) misread a number in
  exponent form; the driver sends plain numbers. Duty cycles, overshoot and
  preshoot are ratios, not percent.
- ``:WAVeform:FORMat ASCii`` occasionally omits the comma between two values of a
  long record; waveforms are therefore read in WORD format only.
- Reading the memory (``:WAVeform:MODE RAW``) while the acquisition runs returns an
  empty block without an error; the driver refuses the read instead.
- ``:SOURce:FUNCtion:SQUare:DUYT``, as spelled in the guide, is a command error; the
  driver uses ``:SOURce:FUNCtion:SQUare:DUTY``. Its range is 1 % to 99 %.
- ``:CHANnel<n>:POSition`` ("bias voltage") adds its value to the waveform data and
  to the measurements; it is not a display position (:attr:`RigolDHO900Channel.bias`).
- Measurements that cannot be made return 9.9E37; the driver returns NaN. An item
  is computed only after the query that adds it, within about 0.35 s, which
  :meth:`RigolDHO900.measure` waits for.
- ``:MEASure:ITEM?`` of a channel that is off turns the channel on; the driver
  returns NaN for it without a query. On a stopped acquisition, the instrument
  computes only some of the items added (:meth:`RigolDHO900.measure`).
- The frequency counter counts only while the acquisition runs (reading 0 while
  stopped); the DVM measures in either state.
- A channel that is off ignores changes of its scale and offset (other settings are
  taken); the driver refuses them. Its waveform preamble reports 0 points.
- The delay calibration (``:CHANnel<n>:TCALibrate``) is rejected at time bases slower
  than 10 us/div, also for the unchanged value, which the driver does not write.
- The vertical offset limits change at 58 mV/div, 250 mV/div and 2.55 V/div (at a
  probe ratio of 1), not at the guide's 65 mV, 260 mV and 2.65 V/div.
- The preamble's point count is that between ``:WAVeform:STARt`` and ``:STOP``,
  not the record length; in the normal mode, and in the maximum mode while
  running, a start or stop beyond 1000 is rejected (-200) rather than clipped.
- Binary blocks read with the termination character on (a read ends at each 0x0A
  byte of the data) intermittently stalled for a whole VISA timeout; the driver
  reads them with it off (:meth:`RigolDHO900.query_block`).
"""

from __future__ import annotations

import logging
import math
import time
from typing import TYPE_CHECKING, Any

import numpy as np
import numpy.typing as npt
from qcodes.instrument import (
    ChannelList,
    InstrumentBaseKWArgs,
    InstrumentChannel,
    InstrumentModule,
    VisaInstrument,
    VisaInstrumentKWArgs,
)
from qcodes.parameters import (
    Parameter,
    ParameterWithSetpoints,
    create_on_off_val_mapping,
)
from qcodes.validators import Arrays, Enum, Ints, MultiType, Numbers, Strings

if TYPE_CHECKING:
    from typing import Unpack

log = logging.getLogger(__name__)

_ON_OFF = create_on_off_val_mapping(on_val="1", off_val="0")

#: a response at or above this value is no reading (the instrument sends 9.9E37)
_INVALID = 9e37

#: relative tolerance of a read-back; the instrument keeps 7 significant digits
_READBACK_RTOL = 1e-5

#: probe ratios the instrument accepts
PROBE_RATIOS = (
    0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50,
    100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000,
)  # fmt: skip

#: memory depths (points) the instrument accepts besides "auto"
MEMORY_DEPTHS = (1e3, 1e4, 1e5, 1e6, 1e7, 2.5e7, 5e7)

#: the measurement items of :MEASure:ITEM? by the names of RigolDHO900.measure
MEASUREMENT_ITEMS = {
    "vmax": "VMAX",
    "vmin": "VMIN",
    "vpp": "VPP",
    "vtop": "VTOP",
    "vbase": "VBASe",
    "vamp": "VAMP",
    "vavg": "VAVG",
    "vrms": "VRMS",
    "ac_rms": "ACRMs",
    "period_vrms": "PVRMs",
    "overshoot": "OVERshoot",
    "preshoot": "PREShoot",
    "area": "MARea",
    "period_area": "MPARea",
    "period": "PERiod",
    "frequency": "FREQuency",
    "rise_time": "RTIMe",
    "fall_time": "FTIMe",
    "positive_width": "PWIDth",
    "negative_width": "NWIDth",
    "positive_duty": "PDUTy",
    "negative_duty": "NDUTy",
    "tvmax": "TVMAX",
    "tvmin": "TVMIN",
    "positive_slew_rate": "PSLewrate",
    "negative_slew_rate": "NSLewrate",
    "vupper": "VUPPer",
    "vmid": "VMID",
    "vlower": "VLOWer",
    "variance": "VARiance",
    "positive_pulses": "PPULses",
    "negative_pulses": "NPULses",
    "rising_edges": "PEDGes",
    "falling_edges": "NEDGes",
    "delay_rr": "RRDelay",
    "delay_rf": "RFDelay",
    "delay_fr": "FRDelay",
    "delay_ff": "FFDelay",
    "phase_rr": "RRPHase",
    "phase_rf": "RFPHase",
    "phase_fr": "FRPHase",
    "phase_ff": "FFPHase",
}

#: the items that take two sources
TWO_SOURCE_ITEMS = frozenset(
    name for name in MEASUREMENT_ITEMS if name.startswith(("delay_", "phase_"))
)

#: the results of :MEASure:STATistic:ITEM? by the keys of measure_statistics
STATISTICS = {
    "current": "CURRent",
    "average": "AVERages",
    "minimum": "MINimum",
    "maximum": "MAXimum",
    "deviation": "DEViation",
    "count": "CNT",
}

#: the measurements a channel has as parameters: (item, label, unit)
CHANNEL_MEASUREMENTS = (
    ("vmax", "Maximum", "V"),
    ("vmin", "Minimum", "V"),
    ("vpp", "Peak-to-peak", "V"),
    ("vamp", "Amplitude", "V"),
    ("vavg", "Mean", "V"),
    ("vrms", "RMS", "V"),
    ("ac_rms", "AC RMS", "V"),
    ("frequency", "Frequency", "Hz"),
    ("period", "Period", "s"),
    ("rise_time", "Rise time", "s"),
    ("fall_time", "Fall time", "s"),
    ("positive_duty", "Positive duty cycle", ""),  # a ratio, 0 to 1
)

#: highest frequency of each generator function (Hz); DC and noise have none
AWG_MAX_FREQUENCY = {"sine": 25e6, "square": 15e6, "ramp": 150e3, "arb": 10e6}
#: lowest generator frequency (Hz)
AWG_MIN_FREQUENCY = 2e-3
#: generator amplitude limits (Vpp, high impedance): up to 10 MHz, above
AWG_MAX_AMPLITUDE = ((10e6, 10.0), (math.inf, 5.0))
AWG_MIN_AMPLITUDE = 2e-3


def _float_or_nan(response: str) -> float:
    """A numeric response as float; the invalid marker 9.9E37 as NaN."""
    value = float(response)
    return math.nan if abs(value) >= _INVALID else value


def offset_limit(scale: float, probe_ratio: float) -> float:
    """The vertical offset (and bias) limit in V for a vertical scale in V/div at a
    probe ratio. Measured on a DHO914S (firmware 00.01.04) at a probe ratio of 1,
    and scaling with the ratio: +-0.5 V below 500 uV/div, +-1 V up to 58 mV/div,
    +-8 V up to 250 mV/div, +-20 V below 2.55 V/div, +-100 V from 2.55 V/div. The
    guide's table has the same limits with the band edges at 65 mV, 260 mV and
    2.65 V/div."""
    s = scale / probe_ratio
    eps = 1e-9
    if s < 500e-6 * (1 - eps):
        limit = 0.5
    elif s <= 58e-3 * (1 + eps):
        limit = 1.0
    elif s <= 250e-3 * (1 + eps):
        limit = 8.0
    elif s < 2.55 * (1 - eps):
        limit = 20.0
    else:
        limit = 100.0
    return limit * probe_ratio


def awg_max_amplitude(frequency: float) -> float:
    """The highest generator amplitude (Vpp) at a frequency."""
    for corner, amplitude in AWG_MAX_AMPLITUDE:
        if frequency <= corner:
            return amplitude
    return AWG_MAX_AMPLITUDE[-1][1]


class RigolDHO900Channel(InstrumentChannel["RigolDHO900"]):
    """An analog input channel: vertical settings, waveform and measurements."""

    def __init__(
        self,
        parent: RigolDHO900,
        name: str,
        channel: int,
        **kwargs: Unpack[InstrumentBaseKWArgs],
    ) -> None:
        super().__init__(parent, name, **kwargs)
        self.channel = channel
        prefix = f":CHANnel{channel}"
        self._prefix = prefix

        # the settings are declared in the order in which they can be set back: the
        # probe ratio rescales scale and offset, and the instrument ignores scale and
        # offset while the channel is off, so enabled comes last

        self.probe_ratio: Parameter = self.add_parameter(
            "probe_ratio",
            label="Probe ratio",
            get_cmd=f"{prefix}:PROBe?",
            set_cmd=f"{prefix}:PROBe {{:g}}",
            get_parser=float,
            vals=Enum(*PROBE_RATIOS),
        )
        """Probe attenuation ratio. Scale, offset, bias and levels are in volts at
        the probe tip; setting the ratio rescales them."""

        self.units: Parameter = self.add_parameter(
            "units",
            label="Units",
            get_cmd=f"{prefix}:UNITs?",
            set_cmd=f"{prefix}:UNITs {{}}",
            val_mapping={
                "volt": "VOLT",
                "ampere": "AMP",
                "watt": "WATT",
                "unknown": "UNKN",
            },
        )
        """The amplitude unit shown on the display. The driver's parameters keep
        their units (V)."""

        self.coupling: Parameter = self.add_parameter(
            "coupling",
            label="Coupling",
            get_cmd=f"{prefix}:COUPling?",
            set_cmd=f"{prefix}:COUPling {{}}",
            val_mapping={"dc": "DC", "ac": "AC", "gnd": "GND"},
        )
        """Input coupling."""

        self.bandwidth_limit: Parameter = self.add_parameter(
            "bandwidth_limit",
            label="20 MHz bandwidth limit",
            get_cmd=f"{prefix}:BWLimit?",
            set_cmd=f"{prefix}:BWLimit {{}}",
            val_mapping={False: "OFF", True: "20M"},
        )
        """Whether the 20 MHz bandwidth limit is on."""

        self.invert: Parameter = self.add_parameter(
            "invert",
            label="Invert",
            get_cmd=f"{prefix}:INVert?",
            set_cmd=f"{prefix}:INVert {{}}",
            val_mapping=_ON_OFF,
        )
        """Whether the waveform is inverted (also in the waveform data)."""

        self.vernier: Parameter = self.add_parameter(
            "vernier",
            label="Fine scale adjustment",
            get_cmd=f"{prefix}:VERNier?",
            set_cmd=f"{prefix}:VERNier {{}}",
            val_mapping=_ON_OFF,
        )
        """Whether the front-panel knob adjusts the vertical scale in fine steps. The
        scale parameter accepts any value in range either way."""

        self.scale: Parameter = self.add_parameter(
            "scale",
            label="Vertical scale",
            unit="V/div",
            get_cmd=f"{prefix}:SCALe?",
            set_cmd=self._set_scale,
            get_parser=float,
            vals=Numbers(200e-6 * min(PROBE_RATIOS), 10 * max(PROBE_RATIOS)),
        )
        """Vertical scale: 200 uV/div to 10 V/div times the probe ratio."""

        self.offset: Parameter = self.add_parameter(
            "offset",
            label="Vertical offset",
            unit="V",
            get_cmd=f"{prefix}:OFFSet?",
            set_cmd=self._set_offset,
            get_parser=float,
            vals=Numbers(),
        )
        """Vertical offset: shifts the waveform on the display; the voltage at the
        screen center is -offset. Its range depends on the scale and probe ratio."""

        self.bias: Parameter = self.add_parameter(
            "bias",
            label="Bias voltage",
            unit="V",
            get_cmd=f"{prefix}:POSition?",
            set_cmd=self._set_bias,
            get_parser=float,
            vals=Numbers(),
        )
        """Bias voltage (:CHANnel<n>:POSition): added to the waveform data and to the
        measurements, unlike offset. Same range as offset."""

        self.delay_calibration: Parameter = self.add_parameter(
            "delay_calibration",
            label="Delay calibration",
            unit="s",
            get_cmd=f"{prefix}:TCALibrate?",
            set_cmd=self._set_delay_calibration,
            get_parser=float,
            vals=Numbers(-100e-9, 100e-9),
        )
        """Channel delay calibration (deskew), -100 ns to 100 ns. The instrument
        accepts a change only at fast time bases (it rejected every value at
        200 us/div and accepted them at 1 us/div, up to 10 us/div); a change it
        rejects raises, and the unchanged value is not written (it would be rejected
        too)."""

        self.label_text: Parameter = self.add_parameter(
            "label_text",
            label="Label",
            get_cmd=f"{prefix}:LABel:CONTent?",
            set_cmd=f"{prefix}:LABel:CONTent {{}}",
            vals=Strings(min_length=1),
        )
        """The channel's label on the display."""

        self.label_visible: Parameter = self.add_parameter(
            "label_visible",
            label="Show label",
            get_cmd=f"{prefix}:LABel:SHOW?",
            set_cmd=f"{prefix}:LABel:SHOW {{}}",
            val_mapping=_ON_OFF,
        )
        """Whether the label is shown on the display."""

        self.enabled: Parameter = self.add_parameter(
            "enabled",
            label=f"Channel {channel} on",
            get_cmd=f"{prefix}:DISPlay?",
            set_cmd=f"{prefix}:DISPlay {{}}",
            val_mapping=_ON_OFF,
        )
        """Whether the channel is on. While it is off, the instrument ignores changes
        of scale and offset, and its trace and measurements are not available."""

        self.trace: ParameterWithSetpoints = self.add_parameter(
            "trace",
            label=f"Channel {channel}",
            unit="V",
            get_cmd=self._get_trace,
            setpoints=(parent.waveform.time_axis,),
            vals=Arrays(shape=(parent.waveform.points,)),
            parameter_class=ParameterWithSetpoints,
            snapshot_value=False,
        )
        """The channel's waveform in V, as selected by waveform.mode: the display
        (normal), or the memory of a stopped acquisition (raw)."""

        for item, label, unit in CHANNEL_MEASUREMENTS:
            self.add_parameter(
                item,
                label=label,
                unit=unit,
                get_cmd=self._measurement_getter(item),
                snapshot_get=False,
                docstring=f"Measurement {MEASUREMENT_ITEMS[item]} of the channel; NaN "
                "when it cannot be measured.",
            )

    @property
    def source_name(self) -> str:
        """The channel as a source in SCPI commands."""
        return f"CHANnel{self.channel}"

    def _measurement_getter(self, item: str) -> Any:
        def get() -> float:
            return self.root_instrument.measure(item, f"ch{self.channel}")

        return get

    def is_on(self) -> bool:
        """Whether the channel is on (queried)."""
        return self.ask(f"{self._prefix}:DISPlay?").strip() == "1"

    def _require_on_unless_unchanged(self, node: str, value: float, what: str) -> bool:
        """For a channel that is off, which ignores scale and offset changes: True if
        value is the current one (nothing to write), else ValueError. False for a
        channel that is on."""
        if self.is_on():
            return False
        current = float(self.ask(f"{self._prefix}:{node}?"))
        if math.isclose(current, value, rel_tol=_READBACK_RTOL, abs_tol=1e-12):
            return True
        raise ValueError(
            f"{self.full_name}: the {what} of a channel that is off cannot be changed "
            "(the instrument ignores it); turn the channel on first"
        )

    def _set_scale(self, value: float) -> None:
        ratio = float(self.ask(f"{self._prefix}:PROBe?"))
        low, high = 200e-6 * ratio, 10.0 * ratio
        if not low * (1 - 1e-9) <= value <= high * (1 + 1e-9):
            raise ValueError(
                f"{self.full_name}: {value} V/div is outside {low:g} to {high:g} V/div "
                f"at probe ratio {ratio:g}"
            )
        if self._require_on_unless_unchanged("SCALe", value, "scale"):
            return
        self.write(f"{self._prefix}:SCALe {value:.6e}")

    def _check_offset_range(self, value: float, what: str) -> None:
        ratio = float(self.ask(f"{self._prefix}:PROBe?"))
        scale = float(self.ask(f"{self._prefix}:SCALe?"))
        limit = offset_limit(scale, ratio)
        if abs(value) > limit * (1 + 1e-9):
            raise ValueError(
                f"{self.full_name}: {what} {value} V is outside +-{limit:g} V at "
                f"{scale:g} V/div and probe ratio {ratio:g}"
            )

    def _set_offset(self, value: float) -> None:
        self._check_offset_range(value, "offset")
        if self._require_on_unless_unchanged("OFFSet", value, "offset"):
            return
        self.write(f"{self._prefix}:OFFSet {value:.6e}")

    def _set_delay_calibration(self, value: float) -> None:
        current = float(self.ask(f"{self._prefix}:TCALibrate?"))
        if math.isclose(current, value, rel_tol=_READBACK_RTOL, abs_tol=1e-15):
            return
        self.root_instrument._write_checked(
            f"{self._prefix}:TCALibrate", value, self.delay_calibration
        )

    def _set_bias(self, value: float) -> None:
        self._check_offset_range(value, "bias")
        self.write(f"{self._prefix}:POSition {value:.6e}")

    def _get_trace(self) -> npt.NDArray[np.float64]:
        if not self.is_on():
            raise RuntimeError(f"{self.full_name}: the channel is off; it has no trace")
        return self.root_instrument.waveform.read(self.source_name)


class RigolDHO900Waveform(InstrumentModule["RigolDHO900"]):
    """Waveform readout: the mode and the time axis of the channels' traces."""

    #: points read per :WAVeform:DATA? from the memory
    chunk_points = 250_000

    def __init__(
        self, parent: RigolDHO900, name: str, **kwargs: Unpack[InstrumentBaseKWArgs]
    ) -> None:
        super().__init__(parent, name, **kwargs)

        self.mode: Parameter = self.add_parameter(
            "mode",
            label="Waveform read mode",
            get_cmd=":WAVeform:MODE?",
            set_cmd=":WAVeform:MODE {}",
            val_mapping={"normal": "NORM", "maximum": "MAX", "raw": "RAW"},
        )
        """What a trace reads: normal, the 1000 points on the display; raw, the
        memory (memory depth points), only while stopped; maximum, the display while
        running and the memory while stopped."""

        self.points: Parameter = self.add_parameter(
            "points",
            label="Waveform points",
            get_cmd=self._get_points,
            snapshot_get=False,
        )
        """The number of points a trace has in the current mode and state."""

        self.time_axis: Parameter = self.add_parameter(
            "time_axis",
            label="Time",
            unit="s",
            get_cmd=self._get_time_axis,
            vals=Arrays(shape=(self.points,)),
            snapshot_value=False,
        )
        """The time of each trace point relative to the trigger."""

    def preamble(self, source: str = "CHANnel1") -> dict[str, float]:
        """The waveform preamble of a source (as in :WAVeform:SOURce) in the current
        mode, for the whole record: format, type, points, count, x and y increment,
        origin and reference.

        Selects the whole record first (:WAVeform:STARt 1, :WAVeform:STOP at its
        end): the points the preamble reports are those between start and stop, not
        the record length."""
        self.write(f":WAVeform:SOURce {source}")
        self.write(":WAVeform:FORMat WORD")
        mode = self.ask(":WAVeform:MODE?").strip()
        running = mode == "MAX" and self.ask(":TRIGger:STATus?").strip() != "STOP"
        if mode == "NORM" or running:
            # the display; a stop point beyond 1000 is rejected (-200)
            last = 1000
        else:
            # the instrument clips the stop point to the end of the record
            last = round(float(self.ask(":ACQuire:MDEPth?")))
        self.write(":WAVeform:STARt 1")
        self.write(f":WAVeform:STOP {last}")
        fields = self.ask(":WAVeform:PREamble?").split(",")
        if len(fields) != 10:
            raise RuntimeError(f"{self.full_name}: unexpected preamble {fields!r}")
        keys = (
            "format", "type", "points", "count", "xincrement", "xorigin",
            "xreference", "yincrement", "yorigin", "yreference",
        )  # fmt: skip
        return {key: float(value) for key, value in zip(keys, fields, strict=True)}

    def _source_for_axis(self) -> str:
        # the preamble of a channel that is off has 0 points; all channels that are
        # on share the time axis
        for channel in self.root_instrument.channels:
            if channel.is_on():
                return channel.source_name
        return "CHANnel1"

    def _get_points(self) -> int:
        return int(self.preamble(self._source_for_axis())["points"])

    def _get_time_axis(self) -> npt.NDArray[np.float64]:
        pre = self.preamble(self._source_for_axis())
        n = int(pre["points"])
        times = pre["xorigin"] + (np.arange(n) - pre["xreference"]) * pre["xincrement"]
        return np.asarray(times, dtype=np.float64)

    def _needs_stop(self, pre: dict[str, float]) -> bool:
        # type 2: raw; type 1 (maximum) reads the memory only while stopped
        return int(pre["type"]) == 2

    def read(self, source: str) -> npt.NDArray[np.float64]:
        """Read the waveform of a source (:WAVeform:SOURce syntax) in V."""
        pre = self.preamble(source)
        if self._needs_stop(pre) and self.ask(":TRIGger:STATus?").strip() != "STOP":
            raise RuntimeError(
                f"{self.full_name}: the memory (raw mode) can only be read while the "
                "acquisition is stopped: call stop() or digitize() first"
            )
        n = int(pre["points"])
        raw = np.empty(n, dtype=np.uint16)
        chunk = self.chunk_points
        for first in range(0, n, chunk):
            last = min(first + chunk, n)
            # stop first, then start: preamble() left start 1, so start <= stop
            # holds at every step
            self.write(f":WAVeform:STOP {last}")
            self.write(f":WAVeform:STARt {first + 1}")
            block = self.root_instrument.query_block(":WAVeform:DATA?", "H")
            if len(block) != last - first:
                raise RuntimeError(
                    f"{self.full_name}: {len(block)} points received for points "
                    f"{first + 1} to {last} of {source}"
                )
            raw[first:last] = block
        volts = (raw - pre["yorigin"] - pre["yreference"]) * pre["yincrement"]
        return np.asarray(volts, dtype=np.float64)


class RigolDHO900Timebase(InstrumentModule["RigolDHO900"]):
    """The horizontal system."""

    def __init__(
        self, parent: RigolDHO900, name: str, **kwargs: Unpack[InstrumentBaseKWArgs]
    ) -> None:
        super().__init__(parent, name, **kwargs)

        self.mode: Parameter = self.add_parameter(
            "mode",
            label="Time base mode",
            get_cmd=":TIMebase:MODE?",
            set_cmd=":TIMebase:MODE {}",
            val_mapping={"main": "MAIN", "roll": "ROLL"},
        )
        """YT (main) or roll mode."""

        self.scale: Parameter = self.add_parameter(
            "scale",
            label="Horizontal scale",
            unit="s/div",
            get_cmd=":TIMebase:MAIN:SCALe?",
            set_cmd=self._set_scale,
            get_parser=float,
            vals=Numbers(1e-9, 1000),
        )
        """Horizontal scale; the screen is 10 divisions wide. The fastest scale
        depends on the model's bandwidth (2 ns/div on the DHO914S), the slowest is
        500 s/div."""

        self.offset: Parameter = self.add_parameter(
            "offset",
            label="Horizontal offset",
            unit="s",
            get_cmd=":TIMebase:MAIN:OFFSet?",
            set_cmd=lambda value: parent._write_checked(
                ":TIMebase:MAIN:OFFSet", value, self.offset
            ),
            get_parser=float,
            vals=Numbers(),
        )
        """Time of the screen center relative to the trigger. Its range depends on
        the scale and the run state; a value the instrument changes raises."""

        self.reference: Parameter = self.add_parameter(
            "reference",
            label="Horizontal reference",
            get_cmd=":TIMebase:HREFerence:MODE?",
            set_cmd=":TIMebase:HREFerence:MODE {}",
            val_mapping={
                "center": "CENT",
                "left": "LB",
                "right": "RB",
                "trigger": "TRIG",
                "user": "USER",
            },
        )
        """The point the waveform expands or compresses about when the scale
        changes."""

        self.reference_position: Parameter = self.add_parameter(
            "reference_position",
            label="User reference position",
            get_cmd=":TIMebase:HREFerence:POSition?",
            set_cmd=":TIMebase:HREFerence:POSition {}",
            get_parser=int,
            vals=Ints(-500, 500),
        )
        """The user-defined horizontal reference position, -500 to 500."""

        self.vernier: Parameter = self.add_parameter(
            "vernier",
            label="Fine horizontal adjustment",
            get_cmd=":TIMebase:VERNier?",
            set_cmd=":TIMebase:VERNier {}",
            val_mapping=_ON_OFF,
        )
        """Whether the front-panel knob adjusts the horizontal scale in fine steps."""

        self.auto_roll: Parameter = self.add_parameter(
            "auto_roll",
            label="Automatic roll mode",
            get_cmd=":TIMebase:ROLL?",
            set_cmd=":TIMebase:ROLL {}",
            val_mapping=_ON_OFF,
        )
        """Whether the roll mode starts by itself at 50 ms/div and slower."""

        self.delay_enabled: Parameter = self.add_parameter(
            "delay_enabled",
            label="Zoom (delayed sweep)",
            get_cmd=":TIMebase:DELay:ENABle?",
            set_cmd=":TIMebase:DELay:ENABle {}",
            val_mapping=_ON_OFF,
        )
        """Whether the zoomed (delayed) time base is shown."""

        self.delay_scale: Parameter = self.add_parameter(
            "delay_scale",
            label="Zoom scale",
            unit="s/div",
            get_cmd=":TIMebase:DELay:SCALe?",
            set_cmd=lambda value: parent._write_checked(
                ":TIMebase:DELay:SCALe", value, self.delay_scale
            ),
            get_parser=float,
            vals=Numbers(0, 1000),
        )
        """Scale of the zoomed time base, at most the main scale, in 1-2-5 steps."""

        self.delay_offset: Parameter = self.add_parameter(
            "delay_offset",
            label="Zoom offset",
            unit="s",
            get_cmd=":TIMebase:DELay:OFFSet?",
            set_cmd=lambda value: parent._write_checked(
                ":TIMebase:DELay:OFFSet", value, self.delay_offset
            ),
            get_parser=float,
            vals=Numbers(),
        )
        """Offset of the zoomed time base; the zoomed window lies within the main
        one."""

    def _set_scale(self, value: float) -> None:
        self.root_instrument._write_checked(":TIMebase:MAIN:SCALe", value, self.scale)


class RigolDHO900Acquisition(InstrumentModule["RigolDHO900"]):
    """Acquisition mode, averaging, memory depth and sample rate."""

    def __init__(
        self, parent: RigolDHO900, name: str, **kwargs: Unpack[InstrumentBaseKWArgs]
    ) -> None:
        super().__init__(parent, name, **kwargs)

        self.type: Parameter = self.add_parameter(
            "type",
            label="Acquisition mode",
            get_cmd=":ACQuire:TYPE?",
            set_cmd=":ACQuire:TYPE {}",
            val_mapping={
                "normal": "NORM",
                "peak": "PEAK",
                "average": "AVER",
                "ultra": "ULTR",
            },
        )
        """normal, peak detection, average or UltraAcquire (segmented)."""

        self.averages: Parameter = self.add_parameter(
            "averages",
            label="Averages",
            get_cmd=":ACQuire:AVERages?",
            set_cmd=":ACQuire:AVERages {}",
            get_parser=int,
            vals=Enum(*(2**n for n in range(1, 17))),
        )
        """Number of averages in the average mode: a power of 2 from 2 to 65536."""

        self.memory_depth: Parameter = self.add_parameter(
            "memory_depth",
            label="Memory depth",
            unit="pts",
            get_cmd=":ACQuire:MDEPth?",
            set_cmd=self._set_memory_depth,
            get_parser=float,
            vals=MultiType(Enum("auto"), Enum(*MEMORY_DEPTHS)),
        )
        """Points per acquisition: "auto" or 1e3, 1e4, 1e5, 1e6, 1e7, 2.5e7, 5e7. The
        largest depth depends on the number of channels on (DHO900: 50M for one,
        25M for two, 10M for three or four). A read returns the depth in use, also
        in auto. A depth the instrument does not accept raises."""

        self.sample_rate: Parameter = self.add_parameter(
            "sample_rate",
            label="Sample rate",
            unit="Sa/s",
            get_cmd=":ACQuire:SRATe?",
            get_parser=float,
        )
        """The current sample rate."""

    def _set_memory_depth(self, value: str | float) -> None:
        if value == "auto":
            self.write(":ACQuire:MDEPth AUTO")
            return
        self.root_instrument._write_checked(
            ":ACQuire:MDEPth", float(value), self.memory_depth, fmt="{:.0f}"
        )


class RigolDHO900Trigger(InstrumentModule["RigolDHO900"]):
    """Trigger: sweep, status and the edge and pulse trigger settings."""

    def __init__(
        self, parent: RigolDHO900, name: str, **kwargs: Unpack[InstrumentBaseKWArgs]
    ) -> None:
        super().__init__(parent, name, **kwargs)
        sources = parent._source_mapping()

        self.type: Parameter = self.add_parameter(
            "type",
            label="Trigger type",
            get_cmd=":TRIGger:MODE?",
            set_cmd=":TRIGger:MODE {}",
            val_mapping={
                "edge": "EDGE",
                "pulse": "PULS",
                "slope": "SLOP",
                "video": "VID",
                "pattern": "PATT",
                "duration": "DUR",
                "timeout": "TIM",
                "runt": "RUNT",
                "window": "WIND",
                "delay": "DEL",
                "setup_hold": "SET",
                "nth_edge": "NEDG",
                "rs232": "RS232",
                "iic": "IIC",
                "spi": "SPI",
                "can": "CAN",
                "lin": "LIN",
            },
        )
        """The trigger type. The driver has the settings of the edge and pulse
        triggers."""

        self.sweep: Parameter = self.add_parameter(
            "sweep",
            label="Trigger sweep",
            get_cmd=":TRIGger:SWEep?",
            set_cmd=":TRIGger:SWEep {}",
            val_mapping={"auto": "AUTO", "normal": "NORM", "single": "SING"},
        )
        """auto: acquires without a trigger as well; normal: only on a trigger;
        single: one acquisition on the next trigger, then stop."""

        self.status: Parameter = self.add_parameter(
            "status",
            label="Trigger status",
            get_cmd=":TRIGger:STATus?",
            val_mapping={
                "triggered": "TD",
                "wait": "WAIT",
                "run": "RUN",
                "auto": "AUTO",
                "stop": "STOP",
            },
            snapshot_get=False,
        )
        """triggered, wait (armed), run, auto (acquiring without a trigger) or
        stop."""

        self.coupling: Parameter = self.add_parameter(
            "coupling",
            label="Trigger coupling",
            get_cmd=":TRIGger:COUPling?",
            set_cmd=":TRIGger:COUPling {}",
            val_mapping={
                "dc": "DC",
                "ac": "AC",
                "lf_reject": "LFR",
                "hf_reject": "HFR",
            },
        )
        """Coupling of the edge trigger on an analog channel."""

        self.holdoff: Parameter = self.add_parameter(
            "holdoff",
            label="Trigger holdoff",
            unit="s",
            get_cmd=":TRIGger:HOLDoff?",
            set_cmd=":TRIGger:HOLDoff {:.6e}",
            get_parser=float,
            vals=Numbers(8e-9, 10),
        )
        """Time after a trigger during which the trigger is not rearmed."""

        self.noise_reject: Parameter = self.add_parameter(
            "noise_reject",
            label="Noise rejection",
            get_cmd=":TRIGger:NREJect?",
            set_cmd=":TRIGger:NREJect {}",
            val_mapping=_ON_OFF,
        )
        """Whether noise rejection is on."""

        self.edge_source: Parameter = self.add_parameter(
            "edge_source",
            label="Edge trigger source",
            get_cmd=":TRIGger:EDGE:SOURce?",
            set_cmd=":TRIGger:EDGE:SOURce {}",
            val_mapping=sources,
        )
        """Source of the edge trigger."""

        self.edge_slope: Parameter = self.add_parameter(
            "edge_slope",
            label="Edge trigger slope",
            get_cmd=":TRIGger:EDGE:SLOPe?",
            set_cmd=":TRIGger:EDGE:SLOPe {}",
            val_mapping={"rising": "POS", "falling": "NEG", "either": "RFAL"},
        )
        """The edge the edge trigger fires on."""

        self.edge_level: Parameter = self.add_parameter(
            "edge_level",
            label="Edge trigger level",
            unit="V",
            get_cmd=":TRIGger:EDGE:LEVel?",
            set_cmd=lambda value: self._set_level(
                "EDGE", self.edge_source, value, self.edge_level
            ),
            get_parser=float,
            vals=Numbers(),
        )
        """Edge trigger level, within +-4.5 divisions of the screen center of the
        source channel."""

        self.pulse_source: Parameter = self.add_parameter(
            "pulse_source",
            label="Pulse trigger source",
            get_cmd=":TRIGger:PULSe:SOURce?",
            set_cmd=":TRIGger:PULSe:SOURce {}",
            val_mapping=sources,
        )
        """Source of the pulse trigger."""

        self.pulse_polarity: Parameter = self.add_parameter(
            "pulse_polarity",
            label="Pulse polarity",
            get_cmd=":TRIGger:PULSe:POLarity?",
            set_cmd=":TRIGger:PULSe:POLarity {}",
            val_mapping={"positive": "POS", "negative": "NEG"},
        )
        """Polarity of the pulses the pulse trigger qualifies."""

        self.pulse_when: Parameter = self.add_parameter(
            "pulse_when",
            label="Pulse condition",
            get_cmd=":TRIGger:PULSe:WHEN?",
            set_cmd=":TRIGger:PULSe:WHEN {}",
            val_mapping={"greater": "GRE", "less": "LESS", "between": "GLES"},
        )
        """Trigger on pulses wider than pulse_lower_width (greater), narrower than
        pulse_upper_width (less), or between the two."""

        self.pulse_upper_width: Parameter = self.add_parameter(
            "pulse_upper_width",
            label="Pulse upper width",
            unit="s",
            get_cmd=":TRIGger:PULSe:UWIDth?",
            set_cmd=lambda value: parent._write_checked(
                ":TRIGger:PULSe:UWIDth", value, self.pulse_upper_width
            ),
            get_parser=float,
            vals=Numbers(1e-9, 10),
        )
        """Upper pulse width limit (less, between)."""

        self.pulse_lower_width: Parameter = self.add_parameter(
            "pulse_lower_width",
            label="Pulse lower width",
            unit="s",
            get_cmd=":TRIGger:PULSe:LWIDth?",
            set_cmd=lambda value: parent._write_checked(
                ":TRIGger:PULSe:LWIDth", value, self.pulse_lower_width
            ),
            get_parser=float,
            vals=Numbers(1e-9, 10),
        )
        """Lower pulse width limit (greater, between)."""

        self.pulse_level: Parameter = self.add_parameter(
            "pulse_level",
            label="Pulse trigger level",
            unit="V",
            get_cmd=":TRIGger:PULSe:LEVel?",
            set_cmd=lambda value: self._set_level(
                "PULSe", self.pulse_source, value, self.pulse_level
            ),
            get_parser=float,
            vals=Numbers(),
        )
        """Pulse trigger level, within +-4.5 divisions of the screen center of the
        source channel."""

    def _set_level(
        self, node: str, source: Parameter, value: float, param: Parameter
    ) -> None:
        channel = self.root_instrument._channel_of(source.get())
        if channel is not None:
            scale = float(channel.ask(f"{channel._prefix}:SCALe?"))
            offset = float(channel.ask(f"{channel._prefix}:OFFSet?"))
            low, high = -4.5 * scale - offset, 4.5 * scale - offset
            tol = 1e-6 * scale
            if not low - tol <= value <= high + tol:
                raise ValueError(
                    f"{param.full_name}: {value} V is outside {low:g} to {high:g} V "
                    f"({channel.short_name} at {scale:g} V/div, offset {offset:g} V)"
                )
        self.write(f":TRIGger:{node}:LEVel {value:.6e}")


class RigolDHO900AWG(InstrumentModule["RigolDHO900"]):
    """The built-in function generator of the DHO914S and DHO924S (GI output).

    Amplitudes and offsets are those into a high impedance load: on a DHO914S an
    amplitude of 2 V gave 1.99 Vpp at a 1 MOhm input. Arbitrary waveforms cannot be
    loaded through SCPI."""

    FUNCTIONS = {
        "sine": "SIN",
        "square": "SQU",
        "ramp": "RAMP",
        "dc": "DC",
        "noise": "NOIS",
        "arb": "ARB",
    }
    #: the keywords as the instrument accepts and returns them: the long forms
    #: SINusoid, SQUare and TRIangle and the short forms UPR, DNR and NOIS of the
    #: guide are rejected (-222), and a query returns UPRAMP, DNRAMP and NOISE
    MODULATION_FUNCTIONS = {
        "sine": "SIN",
        "square": "SQU",
        "triangle": "TRI",
        "up_ramp": "UPRAMP",
        "down_ramp": "DNRAMP",
        "noise": "NOISE",
    }

    def __init__(
        self, parent: RigolDHO900, name: str, **kwargs: Unpack[InstrumentBaseKWArgs]
    ) -> None:
        super().__init__(parent, name, **kwargs)

        self.output: Parameter = self.add_parameter(
            "output",
            label="Generator output",
            get_cmd=":SOURce:OUTPut:STATe?",
            set_cmd=":SOURce:OUTPut:STATe {}",
            val_mapping=_ON_OFF,
        )
        """Whether the generator output is on."""

        self.function: Parameter = self.add_parameter(
            "function",
            label="Waveform",
            get_cmd=":SOURce:FUNCtion?",
            set_cmd=self._set_function,
            val_mapping=self.FUNCTIONS,
        )
        """The waveform. A function whose frequency limit is below the current
        frequency is refused: lower the frequency first."""

        self.frequency: Parameter = self.add_parameter(
            "frequency",
            label="Frequency",
            unit="Hz",
            get_cmd=":SOURce:FREQuency?",
            set_cmd=self._set_frequency,
            get_parser=float,
            vals=Numbers(AWG_MIN_FREQUENCY, max(AWG_MAX_FREQUENCY.values())),
        )
        """Frequency: 2 mHz to 25 MHz (sine), 15 MHz (square), 150 kHz (ramp) or
        10 MHz (arb). Above 10 MHz the amplitude is limited to 5 V: a frequency
        above 10 MHz at a higher amplitude is refused, since the instrument would
        lower the amplitude."""

        self.amplitude: Parameter = self.add_parameter(
            "amplitude",
            label="Amplitude",
            unit="Vpp",
            get_cmd=":SOURce:VOLTage:AMPLitude?",
            set_cmd=self._set_amplitude,
            get_parser=float,
            vals=Numbers(AWG_MIN_AMPLITUDE, AWG_MAX_AMPLITUDE[0][1]),
        )
        """Peak-to-peak amplitude into a high impedance: 2 mV to 10 V up to 10 MHz,
        to 5 V above, and at most twice the margin the offset leaves."""

        self.offset: Parameter = self.add_parameter(
            "offset",
            label="Offset",
            unit="V",
            get_cmd=":SOURce:VOLTage:OFFSet?",
            set_cmd=self._set_offset,
            get_parser=float,
            vals=Numbers(-5, 5),
        )
        """DC offset: within +-(maximum amplitude - amplitude) / 2."""

        self.phase: Parameter = self.add_parameter(
            "phase",
            label="Start phase",
            unit="deg",
            get_cmd=":SOURce:PHASe?",
            set_cmd=":SOURce:PHASe {:.6e}",
            get_parser=float,
            vals=Numbers(0, 360),
        )
        """Start phase of the waveform."""

        self.ramp_symmetry: Parameter = self.add_parameter(
            "ramp_symmetry",
            label="Ramp symmetry",
            unit="%",
            get_cmd=":SOURce:FUNCtion:RAMP:SYMMetry?",
            set_cmd=":SOURce:FUNCtion:RAMP:SYMMetry {:.6e}",
            get_parser=float,
            vals=Numbers(0, 100),
        )
        """Share of the period the ramp rises."""

        self.square_duty_cycle: Parameter = self.add_parameter(
            "square_duty_cycle",
            label="Square duty cycle",
            unit="%",
            get_cmd=":SOURce:FUNCtion:SQUare:DUTY?",
            set_cmd=":SOURce:FUNCtion:SQUare:DUTY {:.6e}",
            get_parser=float,
            vals=Numbers(1, 99),
        )
        """Share of the period the square wave is high, 1 % to 99 % (the guide's
        0 to 100 % is clipped by the instrument)."""

        # The modulation settings are taken only while the modulation is on and of
        # their type; otherwise the instrument ignores them without an error. The
        # type comes first and the on/off state last, so that a settings restore can
        # set them in declaration order.

        self.modulation_type: Parameter = self.add_parameter(
            "modulation_type",
            label="Modulation type",
            get_cmd=":SOURce:MOD:TYPe?",
            set_cmd=self._set_modulation_type,
            val_mapping={"am": "AM", "fm": "FM", "pm": "PM"},
        )
        """Amplitude, frequency or phase modulation by an internal waveform. Can be
        changed only while the modulation is on (the instrument ignores it
        otherwise)."""

        self.am_depth: Parameter = self.add_parameter(
            "am_depth",
            label="AM depth",
            unit="%",
            get_cmd=":SOURce:MOD:AM:DEPTh?",
            set_cmd=self._modulation_setter("AM", ":SOURce:MOD:AM:DEPTh", "am_depth"),
            get_parser=float,
            vals=Numbers(0, 120),
        )
        """Amplitude modulation depth. Can be changed only while the modulation is
        on with type am."""

        self.fm_deviation: Parameter = self.add_parameter(
            "fm_deviation",
            label="FM deviation",
            unit="Hz",
            get_cmd=":SOURce:MOD:FM:DEViation?",
            set_cmd=self._modulation_setter(
                "FM", ":SOURce:MOD:FM:DEViation", "fm_deviation"
            ),
            get_parser=float,
            vals=Numbers(2e-3, 25e6),
        )
        """Peak frequency deviation, up to the carrier frequency. Can be changed only
        while the modulation is on with type fm."""

        self.pm_deviation: Parameter = self.add_parameter(
            "pm_deviation",
            label="PM deviation",
            unit="deg",
            get_cmd=":SOURce:MOD:PM:DEViation?",
            set_cmd=self._modulation_setter(
                "PM", ":SOURce:MOD:PM:DEViation", "pm_deviation"
            ),
            get_parser=float,
            vals=Numbers(0, 360),
        )
        """Peak phase deviation. Can be changed only while the modulation is on with
        type pm."""

        for kind in ("am", "fm", "pm"):
            upper = kind.upper()
            # the long form :SOURce:MOD:AM:INTernal:FREQuency? is a command error (no
            # response); within INTernal only FREQ is accepted
            self.add_parameter(
                f"{kind}_frequency",
                label=f"{upper} frequency",
                unit="Hz",
                get_cmd=f":SOURce:MOD:{upper}:INTernal:FREQ?",
                set_cmd=self._modulation_setter(
                    upper, f":SOURce:MOD:{upper}:INTernal:FREQ", f"{kind}_frequency"
                ),
                get_parser=float,
                vals=Numbers(2e-3, 1e6),
                docstring=f"Frequency of the {upper} modulating waveform. Can be "
                f"changed only while the modulation is on with type {kind}.",
            )
            self.add_parameter(
                f"{kind}_function",
                label=f"{upper} waveform",
                get_cmd=f":SOURce:MOD:{upper}:INTernal:FUNCtion?",
                set_cmd=self._modulation_setter(
                    upper, f":SOURce:MOD:{upper}:INTernal:FUNCtion", f"{kind}_function"
                ),
                val_mapping=self.MODULATION_FUNCTIONS,
                docstring=f"The {upper} modulating waveform. Can be changed only "
                f"while the modulation is on with type {kind}.",
            )

        self.modulation: Parameter = self.add_parameter(
            "modulation",
            label="Modulation",
            get_cmd=":SOURce:MOD:STATe?",
            set_cmd=":SOURce:MOD:STATe {}",
            val_mapping=_ON_OFF,
        )
        """Whether the output is modulated."""

    def _set_modulation_type(self, keyword: str) -> None:
        if self.ask(":SOURce:MOD:STATe?").strip() != "1":
            if self.ask(":SOURce:MOD:TYPe?").strip() == keyword:
                return
            raise ValueError(
                f"{self.modulation_type.full_name}: can be changed only while the "
                "modulation is on (the instrument ignores it otherwise)"
            )
        self.write(f":SOURce:MOD:TYPe {keyword}")

    def _modulation_setter(self, kind: str, header: str, name: str) -> Any:
        """The set function of a modulation setting of kind (AM, FM, PM): written
        while the modulation is on with that type; otherwise an unchanged value is
        accepted and a change refused."""

        def set_value(value: float | str) -> None:
            text = value if isinstance(value, str) else f"{value:.6e}"
            on = self.ask(":SOURce:MOD:STATe?").strip() == "1"
            if on and self.ask(":SOURce:MOD:TYPe?").strip() == kind:
                self.write(f"{header} {text}")
                return
            current = self.ask(f"{header}?").strip()
            if isinstance(value, str):
                unchanged = current == value
            else:
                unchanged = math.isclose(float(current), value, rel_tol=_READBACK_RTOL)
            if not unchanged:
                raise ValueError(
                    f"{self.parameters[name].full_name}: can be changed only while the "
                    f"modulation is on with type {kind.lower()} (the instrument "
                    "ignores it otherwise)"
                )

        return set_value

    def _function_now(self) -> str:
        response = self.ask(":SOURce:FUNCtion?").strip()
        for name, keyword in self.FUNCTIONS.items():
            if keyword == response:
                return name
        raise RuntimeError(f"{self.full_name}: unexpected function {response!r}")

    def _set_function(self, keyword: str) -> None:
        name = next(n for n, k in self.FUNCTIONS.items() if k == keyword)
        limit = AWG_MAX_FREQUENCY.get(name)
        if limit is not None:
            frequency = float(self.ask(":SOURce:FREQuency?"))
            if frequency > limit * (1 + 1e-9):
                raise ValueError(
                    f"{self.function.full_name}: {name} is limited to {limit:g} Hz; "
                    f"the frequency is {frequency:g} Hz: lower it first"
                )
        self.write(f":SOURce:FUNCtion {keyword}")

    def _set_frequency(self, value: float) -> None:
        name = self._function_now()
        limit = AWG_MAX_FREQUENCY.get(name)
        if limit is None:
            raise ValueError(f"{self.frequency.full_name}: {name} has no frequency")
        if value > limit * (1 + 1e-9):
            raise ValueError(
                f"{self.frequency.full_name}: {value:g} Hz is above {limit:g} Hz, the "
                f"limit of {name}"
            )
        amplitude = float(self.ask(":SOURce:VOLTage:AMPLitude?"))
        if amplitude > awg_max_amplitude(value) * (1 + 1e-9):
            raise ValueError(
                f"{self.frequency.full_name}: at {value:g} Hz the amplitude is "
                f"limited to {awg_max_amplitude(value):g} V; the amplitude is "
                f"{amplitude:g} V: lower it first"
            )
        self.write(f":SOURce:FREQuency {value:.7e}")

    def _set_amplitude(self, value: float) -> None:
        frequency = float(self.ask(":SOURce:FREQuency?"))
        offset = float(self.ask(":SOURce:VOLTage:OFFSet?"))
        maximum = awg_max_amplitude(frequency)
        limit = maximum - 2 * abs(offset)
        if value > limit * (1 + 1e-9):
            raise ValueError(
                f"{self.amplitude.full_name}: {value:g} V is above {limit:g} V, the "
                f"limit at {frequency:g} Hz with an offset of {offset:g} V"
            )
        self.write(f":SOURce:VOLTage:AMPLitude {value:.6e}")

    def _set_offset(self, value: float) -> None:
        frequency = float(self.ask(":SOURce:FREQuency?"))
        amplitude = float(self.ask(":SOURce:VOLTage:AMPLitude?"))
        limit = (awg_max_amplitude(frequency) - amplitude) / 2
        if abs(value) > limit * (1 + 1e-9) + 1e-12:
            raise ValueError(
                f"{self.offset.full_name}: {value:g} V is outside +-{limit:g} V, the "
                f"limit with an amplitude of {amplitude:g} V at {frequency:g} Hz"
            )
        self.write(f":SOURce:VOLTage:OFFSet {value:.6e}")


class RigolDHO900Counter(InstrumentModule["RigolDHO900"]):
    """The hardware frequency counter."""

    def __init__(
        self, parent: RigolDHO900, name: str, **kwargs: Unpack[InstrumentBaseKWArgs]
    ) -> None:
        super().__init__(parent, name, **kwargs)

        # enabled comes last: statistics can be changed only while the counter is
        # on, so a settings restore sets it first

        self.source: Parameter = self.add_parameter(
            "source",
            label="Counter source",
            get_cmd=":COUNter:SOURce?",
            set_cmd=":COUNter:SOURce {}",
            val_mapping=parent._source_mapping(),
        )
        """The counted channel."""

        self.mode: Parameter = self.add_parameter(
            "mode",
            label="Counter mode",
            get_cmd=":COUNter:MODE?",
            set_cmd=":COUNter:MODE {}",
            val_mapping={"frequency": "FREQ", "period": "PER", "totalize": "TOT"},
        )
        """frequency, period, or totalize (edge count)."""

        self.digits: Parameter = self.add_parameter(
            "digits",
            label="Counter digits",
            get_cmd=":COUNter:NDIGits?",
            set_cmd=":COUNter:NDIGits {}",
            get_parser=int,
            vals=Ints(3, 6),
        )
        """Resolution in digits (frequency and period)."""

        self.statistics: Parameter = self.add_parameter(
            "statistics",
            label="Counter statistics",
            get_cmd=":COUNter:TOTalize:ENABle?",
            set_cmd=self._set_statistics,
            val_mapping=_ON_OFF,
        )
        """Whether the counter's statistics are on (:COUNter:TOTalize:ENABle;
        frequency and period). Can be changed only while the counter is on (the
        instrument rejects it otherwise)."""

        self.enabled: Parameter = self.add_parameter(
            "enabled",
            label="Counter on",
            get_cmd=":COUNter:ENABle?",
            set_cmd=":COUNter:ENABle {}",
            val_mapping=_ON_OFF,
        )
        """Whether the counter is on."""

        self.value: Parameter = self.add_parameter(
            "value",
            label="Counter reading",
            get_cmd=":COUNter:CURRent?",
            get_parser=_float_or_nan,
            snapshot_get=False,
        )
        """The reading in Hz, s or counts, depending on mode; NaN while the counter
        is off. Right after it is turned on, or after a change of mode or digits,
        the reading is 0 or NaN until the first gate time has passed."""

    def _set_statistics(self, keyword: str) -> None:
        if self.ask(":COUNter:ENABle?").strip() != "1":
            if self.ask(":COUNter:TOTalize:ENABle?").strip() == keyword:
                return
            raise ValueError(
                f"{self.statistics.full_name}: can be changed only while the counter "
                "is on"
            )
        self.write(f":COUNter:TOTalize:ENABle {keyword}")

    def clear_total(self) -> None:
        """Restart the edge count of the totalize mode."""
        self.write(":COUNter:TOTalize:CLEar")


class RigolDHO900DVM(InstrumentModule["RigolDHO900"]):
    """The digital voltmeter (4 digits, independent of the acquisition)."""

    def __init__(
        self, parent: RigolDHO900, name: str, **kwargs: Unpack[InstrumentBaseKWArgs]
    ) -> None:
        super().__init__(parent, name, **kwargs)

        self.enabled: Parameter = self.add_parameter(
            "enabled",
            label="DVM on",
            get_cmd=":DVM:ENABle?",
            set_cmd=":DVM:ENABle {}",
            val_mapping=_ON_OFF,
        )
        """Whether the voltmeter is on."""

        self.source: Parameter = self.add_parameter(
            "source",
            label="DVM source",
            get_cmd=":DVM:SOURce?",
            set_cmd=":DVM:SOURce {}",
            val_mapping={
                f"ch{n}": f"CHAN{n}" for n in range(1, parent.n_channels + 1)
            },
        )
        """The measured channel."""

        self.mode: Parameter = self.add_parameter(
            "mode",
            label="DVM mode",
            get_cmd=":DVM:MODE?",
            set_cmd=":DVM:MODE {}",
            val_mapping={"ac_rms": "ACRM", "dc": "DC", "dc_rms": "DCRM"},
        )
        """ac_rms: RMS without the DC component; dc: mean; dc_rms: RMS."""

        self.value: Parameter = self.add_parameter(
            "value",
            label="DVM reading",
            unit="V",
            get_cmd=self._get_value,
            snapshot_get=False,
        )
        """The reading; NaN while the voltmeter is off. After it is turned on, the
        voltmeter reads 0 for 1.5 s to 3 s, then once a value near 0, then the
        reading."""

    def _get_value(self) -> float:
        # with the voltmeter off, :DVM:CURRent? receives no response (VISA timeout)
        if self.ask(":DVM:ENABle?").strip() != "1":
            return math.nan
        return _float_or_nan(self.ask(":DVM:CURRent?"))


class RigolDHO900Measurement(InstrumentModule["RigolDHO900"]):
    """Settings of the automatic measurements."""

    def __init__(
        self, parent: RigolDHO900, name: str, **kwargs: Unpack[InstrumentBaseKWArgs]
    ) -> None:
        super().__init__(parent, name, **kwargs)

        self.threshold_type: Parameter = self.add_parameter(
            "threshold_type",
            label="Threshold type",
            get_cmd=":MEASure:THReshold:TYPE?",
            set_cmd=":MEASure:THReshold:TYPE {}",
            val_mapping={"percent": "PERC", "absolute": "ABS"},
        )
        """Whether the thresholds are in % of the amplitude or in V."""

        for level, keyword in (("upper", "MAX"), ("middle", "MID"), ("lower", "MIN")):
            name = f"threshold_{level}"
            self.add_parameter(
                name,
                label=f"Threshold {level}",
                get_cmd=f":MEASure:SETup:{keyword}?",
                # integers in the guide; an exponent form (9.5e+01) is misread
                set_cmd=self._threshold_setter(f":MEASure:SETup:{keyword}", name),
                get_parser=float,
                vals=Numbers(-1e3, 1e3),
                docstring=f"The {level} threshold of the time measurements, in % or "
                "V (threshold_type). lower < middle < upper: a value that breaks the "
                "order is not taken by the instrument and raises.",
            )

        self.amplitude_method: Parameter = self.add_parameter(
            "amplitude_method",
            label="Amplitude method",
            get_cmd=":MEASure:AMP:TYPE?",
            set_cmd=":MEASure:AMP:TYPE {}",
            val_mapping={"auto": "AUTO", "manual": "MAN"},
        )
        """How the top and base levels are found."""

        self.area: Parameter = self.add_parameter(
            "area",
            label="Measurement range",
            get_cmd=":MEASure:AREA?",
            set_cmd=":MEASure:AREA {}",
            val_mapping={"main": "MAIN", "zoom": "ZOOM"},
        )
        """Measure over the main or the zoomed time base (zoom requires
        timebase.delay_enabled)."""

        self.statistics_count: Parameter = self.add_parameter(
            "statistics_count",
            label="Statistics count",
            get_cmd=":MEASure:STATistic:COUNt?",
            set_cmd=":MEASure:STATistic:COUNt {}",
            get_parser=int,
            vals=Ints(2, 100_000),
        )
        """Number of measurements the statistics cover."""

        self.statistics_display: Parameter = self.add_parameter(
            "statistics_display",
            label="Show statistics",
            get_cmd=":MEASure:STATistic:DISPlay?",
            set_cmd=":MEASure:STATistic:DISPlay {}",
            val_mapping=_ON_OFF,
        )
        """Whether the statistics are shown on the display."""

    def _threshold_setter(self, header: str, name: str) -> Any:
        def set_value(value: float) -> None:
            self.root_instrument._write_checked(
                header, value, self.parameters[name], fmt="{:g}"
            )

        return set_value

    def clear(self) -> None:
        """Remove all measurement items from the display."""
        self.write(":MEASure:CLEar")

    def reset_statistics(self) -> None:
        """Clear the statistics and start them again."""
        self.write(":MEASure:STATistic:RESet")


class RigolDHO900(VisaInstrument):
    """QCoDeS driver for the Rigol DHO900 (and DHO800) series oscilloscopes.

    Args:
        name: Name of the instrument.
        address: VISA address, e.g. ``USB0::0x1AB1::0x044C::<serial>::INSTR``.
        **kwargs: Passed on to VisaInstrument.

    The driver writes nothing at connect. A trace sets the waveform source, format
    and the start and stop points before it reads.
    """

    default_terminator = "\n"
    default_timeout = 5.0

    def __init__(
        self,
        name: str,
        address: str,
        **kwargs: Unpack[VisaInstrumentKWArgs],
    ) -> None:
        # A device clear after a query that received no response leaves the
        # instrument's USB interface unable to respond; repeated, the instrument
        # drops off the bus until it is power-cycled. Hence no clear at connect.
        kwargs.setdefault("device_clear", False)
        super().__init__(name, address, **kwargs)

        model = str(self.get_idn().get("model") or "")
        if not model.upper().startswith(("DHO9", "DHO8")):
            log.warning("%s: model %r is not a DHO800 or DHO900", name, model)
        self.model = model
        self.n_channels = int(self.ask(":SYSTem:RAMount?"))
        modules = self.ask(":SYSTem:MODules?").split(",")
        self.has_logic_analyzer = modules[0].strip() == "1"
        self.has_awg = self.ask(":SYSTem:DGSTatus?").strip() == "1"

        self.waveform: RigolDHO900Waveform = self.add_submodule(
            "waveform", RigolDHO900Waveform(self, "waveform")
        )
        """Waveform readout."""

        channels = ChannelList(self, "channels", RigolDHO900Channel)
        for n in range(1, self.n_channels + 1):
            channel = RigolDHO900Channel(self, f"ch{n}", n)
            channels.append(channel)
            self.add_submodule(f"ch{n}", channel)
        self.channels = self.add_submodule("channels", channels.to_channel_tuple())
        """The analog channels, also as ch1, ch2, ..."""

        self.timebase: RigolDHO900Timebase = self.add_submodule(
            "timebase", RigolDHO900Timebase(self, "timebase")
        )
        """The horizontal system."""

        self.acquisition: RigolDHO900Acquisition = self.add_submodule(
            "acquisition", RigolDHO900Acquisition(self, "acquisition")
        )
        """Acquisition settings."""

        self.trigger: RigolDHO900Trigger = self.add_submodule(
            "trigger", RigolDHO900Trigger(self, "trigger")
        )
        """Trigger settings and status."""

        self.measurement: RigolDHO900Measurement = self.add_submodule(
            "measurement", RigolDHO900Measurement(self, "measurement")
        )
        """Measurement settings."""

        self.counter: RigolDHO900Counter = self.add_submodule(
            "counter", RigolDHO900Counter(self, "counter")
        )
        """The frequency counter."""

        self.dvm: RigolDHO900DVM = self.add_submodule(
            "dvm", RigolDHO900DVM(self, "dvm")
        )
        """The digital voltmeter."""

        self.awg: RigolDHO900AWG | None = None
        """The function generator; None on models without one."""
        if self.has_awg:
            self.awg = self.add_submodule("awg", RigolDHO900AWG(self, "awg"))

        self.connect_message()

    # --- helpers

    def _source_mapping(self) -> dict[str, str]:
        mapping = {f"ch{n}": f"CHAN{n}" for n in range(1, self.n_channels + 1)}
        if self.has_logic_analyzer:
            mapping.update({f"d{n}": f"D{n}" for n in range(16)})
        return mapping

    def _channel_of(self, source: str) -> RigolDHO900Channel | None:
        if source.startswith("ch"):
            return self.submodules[source]  # type: ignore[return-value]
        return None

    def _source_keyword(self, source: str) -> str:
        if source.startswith("ch") and source[2:].isdigit():
            n = int(source[2:])
            if 1 <= n <= self.n_channels:
                return f"CHANnel{n}"
        if source.startswith("math") and source[4:] in ("1", "2", "3", "4"):
            return f"MATH{source[4:]}"
        if self.has_logic_analyzer and source.startswith("d") and source[1:].isdigit():
            if 0 <= int(source[1:]) <= 15:
                return f"D{source[1:]}"
        raise ValueError(f"{self.name}: unknown source {source!r}")

    def _write_checked(
        self, header: str, value: float, param: Parameter, fmt: str = "{:.6e}"
    ) -> None:
        """Write a value and read it back; raise if the instrument set another one
        (it clips out-of-range values without an error)."""
        self.write(f"{header} {fmt.format(value)}")
        actual = float(self.ask(f"{header}?"))
        if not math.isclose(actual, value, rel_tol=_READBACK_RTOL, abs_tol=1e-15):
            raise ValueError(
                f"{param.full_name}: {value:g} was not accepted; the instrument set "
                f"{actual:g}"
            )

    def query_block(self, command: str, datatype: str) -> npt.NDArray[Any]:
        """Query a definite-length binary block (#N...) and return its values.

        Read with the termination character off, to the USBTMC end of message:
        with it on, a read ends at each 0x0A byte of the data, and full-memory reads
        then intermittently stalled for the whole VISA timeout."""
        visa = self.visa_handle
        with visa.read_termination_context(None):
            values = visa.query_binary_values(
                command,
                datatype=datatype,  # type: ignore[arg-type]
                is_big_endian=False,
                # np.array itself: pyvisa then decodes with np.frombuffer
                container=np.array,  # type: ignore[arg-type]
                chunk_size=1 << 20,
            )
        return np.asarray(values)

    # --- acquisition control

    def run(self) -> None:
        """Start acquiring continuously."""
        self.write(":RUN")

    def stop(self) -> None:
        """Stop acquiring; the memory keeps the last acquisition."""
        self.write(":STOP")

    def single(self) -> None:
        """Arm a single acquisition (trigger sweep single); returns immediately."""
        self.write(":SINGle")

    def force_trigger(self) -> None:
        """Generate a trigger (normal and single sweep)."""
        self.write(":TFORce")

    def clear_display(self) -> None:
        """Clear the waveforms on the display."""
        self.write(":CLEar")

    def autoset(self) -> None:
        """Adjust scales, time base and trigger to the input signals (front-panel
        AUTO). Changes most settings."""
        self.write(":AUToset")

    def digitize(self, timeout: float = 10.0, poll_interval: float = 0.02) -> None:
        """Acquire one waveform and wait until the acquisition has stopped, so that
        the channels' traces and the measurements come from the same acquisition.

        Raises TimeoutError if no trigger arrives within timeout seconds; the
        instrument then remains armed (force_trigger() completes it).
        """
        self.write(":SINGle")
        start = time.monotonic()
        armed = False
        while True:
            status = self.ask(":TRIGger:STATus?").strip()
            elapsed = time.monotonic() - start
            if status != "STOP":
                armed = True
            elif armed or elapsed > 0.2:
                # STOP before the instrument reported the arming: a single whose
                # trigger came within one poll, or (after 0.2 s) one that completed
                # before the first poll
                return
            if elapsed > timeout:
                raise TimeoutError(
                    f"{self.name}: no trigger within {timeout} s (status {status})"
                )
            time.sleep(poll_interval)

    # --- measurements

    def _measurement_sources(self, item: str, source: str, source2: str | None) -> str:
        if item not in MEASUREMENT_ITEMS:
            raise ValueError(
                f"{self.name}: unknown measurement {item!r}; one of "
                f"{', '.join(MEASUREMENT_ITEMS)}"
            )
        sources = self._source_keyword(source)
        if item in TWO_SOURCE_ITEMS:
            if source2 is None:
                raise ValueError(f"{self.name}: {item} requires a second source")
            sources += "," + self._source_keyword(source2)
        return f"{MEASUREMENT_ITEMS[item]},{sources}"

    def _sources_off(self, *sources: str | None) -> bool:
        """Whether one of the channel sources is off (a measurement query would turn
        it on)."""
        for source in sources:
            if source is not None:
                channel = self._channel_of(source)
                if channel is not None and not channel.is_on():
                    return True
        return False

    #: seconds measure() queries again while a measurement is invalid: an item
    #: queried for the first time, or right after an acquisition, was computed within
    #: 0.05 s to 0.35 s
    measurement_wait = 0.5

    def measure(
        self,
        item: str,
        source: str = "ch1",
        source2: str | None = None,
        wait: float | None = None,
    ) -> float:
        """One automatic measurement: item (a key of MEASUREMENT_ITEMS, e.g. "vpp",
        "frequency", "phase_rr") of source ("ch1", ..., "math1", ...; delays and
        phases also of source2). NaN when it cannot be measured, and for a channel
        that is off (which the instrument would turn on to measure it).

        The instrument adds the item to the measurements on the display and computes
        it afterwards: while the result is invalid, it is queried again for up to
        wait seconds (default measurement_wait). On a stopped acquisition the
        instrument computes only some of the items added (about 14 added one at a
        time, none of many added in quick succession); an item still invalid there
        is queried once more after the display's items are removed
        (:MEASure:CLEar)."""
        query = self._measurement_sources(item, source, source2)
        if self._sources_off(source, source2):
            return math.nan
        wait = self.measurement_wait if wait is None else wait
        value = self._query_measurement(query, wait)
        if math.isnan(value) and wait > 0:
            if self.ask(":TRIGger:STATus?").strip() == "STOP":
                self.write(":MEASure:CLEar")
                value = self._query_measurement(query, wait)
        return value

    def _query_measurement(self, query: str, wait: float) -> float:
        deadline = time.monotonic() + wait
        while True:
            value = _float_or_nan(self.ask(f":MEASure:ITEM? {query}"))
            if not math.isnan(value) or time.monotonic() >= deadline:
                return value
            time.sleep(0.05)

    def measure_statistics(
        self, item: str, source: str = "ch1", source2: str | None = None
    ) -> dict[str, float]:
        """The statistics of a measurement (current, average, minimum, maximum,
        deviation, count), switching its statistics on first. NaN where there is no
        value yet, and for a channel that is off."""
        query = self._measurement_sources(item, source, source2)
        if self._sources_off(source, source2):
            return {key: math.nan for key in STATISTICS}
        self.write(f":MEASure:STATistic:ITEM {query}")
        return {
            key: _float_or_nan(self.ask(f":MEASure:STATistic:ITEM? {keyword},{query}"))
            for key, keyword in STATISTICS.items()
        }

    # --- instrument

    def screenshot(self, image_format: str = "png") -> bytes:
        """The display as an image file (png, bmp or jpg)."""
        fmt = image_format.upper()
        if fmt not in ("PNG", "BMP", "JPG"):
            raise ValueError(
                f"{self.name}: image format {image_format!r}: png, bmp or jpg"
            )
        return bytes(self.query_block(f":DISPlay:DATA? {fmt}", "B"))

    def save_setup(self) -> bytes:
        """The instrument setup as a binary block (:SYSTem:SETup?), for load_setup."""
        return bytes(self.query_block(":SYSTem:SETup?", "B"))

    def load_setup(self, setup: bytes) -> None:
        """Load a setup read by save_setup."""
        self.visa_handle.write_binary_values(
            ":SYSTem:SETup ", list(setup), datatype="B"
        )

    def reset(self) -> None:
        """Restore the factory default settings (*RST)."""
        self.write("*RST")
