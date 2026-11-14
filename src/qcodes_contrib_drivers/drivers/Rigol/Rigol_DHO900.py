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
- The channels share the ADC, interleaved, but the preamble gives them the same
  time axis: with four channels on, CH1 lagged CH2 by 0.8 ns (one sample period
  at 1.25 GSa/s) more than with two. :meth:`RigolDHO900FrequencyResponse.
  calibrate_through` measures and corrects the difference between two channels.
- At some vertical scales between the steps of the 1-2-5 sequence (0.301, 0.341,
  0.461, 0.505 V/div with a 10:1 probe) the gain differs from the preamble's
  conversion by up to 0.11 dB; the autoscale of frequency_response uses the steps.
- A ``:SINGle`` while the acquisition runs occasionally stops it without an
  acquisition (an empty memory); :meth:`RigolDHO900.digitize` stops it first.
- ``:RUN`` takes effect 0.1 s to 0.4 s after it and occasionally not at all; a
  pending ``:RUN`` turns a following ``:SINGle`` into continuous acquisition.
  :meth:`RigolDHO900.run` returns once the acquisition runs and sends ``:RUN``
  again otherwise.
- Out-of-range values are clipped without an error (a vertical scale of 1000 V/div
  becomes 100 V/div, a generator frequency of 30 MHz becomes 25 MHz). The driver
  refuses them against the limits of the guide or, where they differ, of the
  instrument, which depend on other settings (vertical scale, waveform function),
  and reads back the settings whose limits depend on the instrument state (vertical
  offset and bias, memory depth, horizontal scale and offset, zoom, pulse widths,
  the Bode plot's frequencies): a value the instrument clipped stays set, is logged
  as a warning and is the value cached. Delay calibration and measurement
  thresholds, whose out-of-range values the instrument ignores rather than clips,
  raise ``ValueError`` naming the value that remains.
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
- The Bode plot (:BODeplot) has no command that reads its results.
  ``:BODeplot:ENABle 0`` turns the generator output off, also when the plot is off
  already; the driver does not write it then. The sources read as CHAN1 (the guide:
  CHANnel1); the same channel as input and output is rejected (-222), and writing
  a source turns that channel on, even unchanged (the driver writes only a
  change). A sweep
  leaves the input and output channels AC-coupled. Start, stop, points and
  amplitude out of range are clipped without an error (:class:`RigolDHO900Bode`).

Besides the instrument's Bode plot (``bode``), the driver measures gain and phase
from the waveforms (``frequency_response``, after https://github.com/wjakob/rigol):
a least-squares sine fit at the generator frequency to the input and output traces
of one acquisition, with the vertical scales adjusted to each signal. On a DHO914S
its floor with an open output channel was -75 dB to -119 dB, against -51 dB to
-65 dB of the instrument's own plot (both 2 Vpp, 100 Hz to 25 MHz).
"""

from __future__ import annotations

import math
import time
from functools import wraps
from typing import TYPE_CHECKING, Any, ClassVar

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
    MultiParameter,
    Parameter,
    ParameterWithSetpoints,
    create_on_off_val_mapping,
)
from qcodes.validators import Arrays, Bool, Enum, Ints, MultiType, Numbers, Strings

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from typing import Unpack


_ON_OFF = create_on_off_val_mapping(on_val="1", off_val="0")


class EmptyReadError(RuntimeError):
    """The instrument returned an empty block for a memory read.

    The acquisition was not stopped, or a single acquisition did not take place."""

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


class _ReadBackParameter(Parameter):
    """A parameter whose value the instrument clips without an error.

    Its setter writes and reads back (RigolDHO900._write_checked) and leaves
    a value the instrument changed in read_back; the cache then contains that value,
    where QCoDeS would cache the requested one."""

    read_back: float | None = None

    def _wrap_set(self, set_function: Callable[..., None]) -> Callable[..., None]:
        set_and_cache = super()._wrap_set(set_function)

        @wraps(set_and_cache)
        def set_and_read_back(value: Any, **kwargs: Any) -> None:
            self.read_back = None
            set_and_cache(value, **kwargs)
            if self.read_back is not None:
                self.cache._update_with(value=self.read_back, raw_value=self.read_back)

        return set_and_read_back


def awg_max_amplitude(frequency: float) -> float:
    """The highest generator amplitude at a frequency.

    Args:
        frequency: Generator frequency in Hz.

    Returns:
        The highest peak-to-peak amplitude in V into a high impedance.
    """
    for corner, amplitude in AWG_MAX_AMPLITUDE:
        if frequency <= corner:
            return amplitude
    return AWG_MAX_AMPLITUDE[-1][1]


#: a sample this many divisions from the screen center or farther is clipped: the
#: ADC range ends at +-4.369 div (DHO914S)
CLIP_DIVISIONS = 4.3


def log_frequencies(
    start: float, stop: float, points_per_decade: int
) -> npt.NDArray[np.float64]:
    """Logarithmically spaced frequencies from start to stop.

    The frequencies are start * 10**(k / n) for n points per decade, and stop. The
    instrument's Bode plot uses the same grid (1 kHz, 1.259 kHz, 1.585 kHz, ... at
    10 points per decade).

    Args:
        start: First frequency in Hz.
        stop: Last frequency in Hz.
        points_per_decade: Number of points per decade.

    Returns:
        The frequencies in Hz, start and stop included.

    Raises:
        ValueError: If start is not below stop.
    """
    if not 0 < start < stop:
        raise ValueError(
            f"frequencies: start {start:g} Hz must be below stop {stop:g} Hz"
        )
    steps = math.floor(points_per_decade * math.log10(stop / start) + 1e-9)
    freqs = start * 10.0 ** (np.arange(steps + 1) / points_per_decade)
    if freqs[-1] < stop * (1 - 1e-9):
        freqs = np.append(freqs, stop)
    return np.asarray(freqs, dtype=np.float64)


def memory_channels(enabled: Sequence[int]) -> tuple[int, ...]:
    """The channels whose samples the memory contains, in its order.

    Firmware 00.01.04, DHO914S: CH1 alone with one channel on, CH1 and the other
    channel with CH1 among two, CH1 and CH2 with two others, CH1 to CHn with n of
    three or four. A memory read of the k-th channel that is on returns the k-th of
    these; the memory of a channel that is on is its own only where the two agree.

    Args:
        enabled: Numbers of the channels that are on.

    Returns:
        Numbers of the channels recorded into the memory, in its order.
    """
    on = tuple(sorted(enabled))
    if len(on) == 1:
        return (1,)
    if len(on) == 2:
        return on if on[0] == 1 else (1, 2)
    return tuple(range(1, len(on) + 1))


def readable_channels(enabled: Sequence[int], n_channels: int = 4) -> tuple[int, ...]:
    """The channels to turn on for a memory read.

    The fewest channels, those that are on included, whose memory is their own
    (memory_channels).

    Args:
        enabled: Numbers of the channels that are on.
        n_channels: Number of analog channels of the instrument.

    Returns:
        Numbers of the channels to have on.
    """
    on = set(enabled)
    for extra in ((), (1,), (1, 2), (1, 2, 3), tuple(range(1, n_channels + 1))):
        candidate = tuple(sorted(on | set(extra)))
        if memory_channels(candidate) == candidate:
            return candidate
    return tuple(range(1, n_channels + 1))


def linear_frequencies(
    start: float, stop: float, points: int
) -> npt.NDArray[np.float64]:
    """Equally spaced frequencies from start to stop.

    Args:
        start: First frequency in Hz.
        stop: Last frequency in Hz.
        points: Number of frequencies.

    Returns:
        The frequencies in Hz, start and stop included.

    Raises:
        ValueError: If start is not below stop.
    """
    if not 0 < start < stop:
        raise ValueError(
            f"frequencies: start {start:g} Hz must be below stop {stop:g} Hz"
        )
    return np.linspace(start, stop, points, dtype=np.float64)


def fit_sine(
    t: npt.ArrayLike, y: npt.ArrayLike, frequency: float
) -> tuple[float, float, float]:
    """Least-squares fit of y = A sin(2 pi f t + phase) + c at a known frequency f.

    The fit rejects noise and harmonics that a peak or zero-crossing measurement
    picks up, and needs no whole number of periods.

    Args:
        t: Sample times in s.
        y: Sample values.
        frequency: The known frequency f in Hz.

    Returns:
        The amplitude A, the phase in rad and the offset c.
    """
    t = np.asarray(t, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    w = 2 * np.pi * frequency
    design = np.column_stack([np.sin(w * t), np.cos(w * t), np.ones_like(t)])
    (b, a, c), *_ = np.linalg.lstsq(design, y, rcond=None)
    return float(np.hypot(a, b)), float(np.arctan2(a, b)), float(c)


def scale_125(value: float) -> float:
    """The smallest value of the 1-2-5 sequence (1, 2, 5, 10, ...) at or above value.

    Args:
        value: A positive number.

    Returns:
        The value of the sequence.
    """
    exponent = math.floor(math.log10(value))
    for mantissa in (1, 2, 5, 10):
        candidate = mantissa * 10.0**exponent
        if candidate >= value * (1 - 1e-9):
            return candidate
    return 10.0 ** (exponent + 1)


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
            parameter_class=_ReadBackParameter,
            label="Vertical offset",
            unit="V",
            get_cmd=f"{prefix}:OFFSet?",
            set_cmd=self._set_offset,
            get_parser=float,
            vals=Numbers(),
        )
        """Vertical offset: shifts the waveform on the display; the voltage at the
        screen center is -offset. Its range depends on the scale and probe ratio; the
        instrument clips a value outside it, which is logged as a warning, and the
        clipped value is the one cached."""

        self.bias: Parameter = self.add_parameter(
            "bias",
            parameter_class=_ReadBackParameter,
            label="Bias voltage",
            unit="V",
            get_cmd=f"{prefix}:POSition?",
            set_cmd=self._set_bias,
            get_parser=float,
            vals=Numbers(),
        )
        """Bias voltage (:CHANnel<n>:POSition): added to the waveform data and to the
        measurements, unlike offset. Same range and clipping as offset."""

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
            set_cmd=self._set_enabled,
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

    def _set_enabled(self, value: str) -> None:
        self.write(f"{self._prefix}:DISPlay {value}")
        # the instrument reconfigures the acquisition; digitize() allows for it
        self.parent._channels_changed = time.monotonic()

    def _require_on_unless_unchanged(self, node: str, value: float, what: str) -> bool:
        """Whether a change of a channel that is off can be skipped.

        A channel that is off ignores scale and offset changes: True if value is the
        current one (nothing to write), else ValueError. False for a channel that is
        on."""
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

    def _write_in_range(self, node: str, value: float, param: Parameter) -> None:
        """Write offset or bias and read it back.

        The instrument clips a value outside
        the range of the scale and probe ratio without an error, and that range is
        not predictable from the scale alone (it differs between channels and with
        the bandwidth limit): a clipped value stays set, is logged as a warning and
        is the value cached (_ReadBackParameter)."""
        header = f"{self._prefix}:{node}"
        self.write(f"{header} {value:.6e}")
        actual = float(self.ask(f"{header}?"))
        if math.isclose(actual, value, rel_tol=_READBACK_RTOL, abs_tol=1e-12):
            return
        param.read_back = actual  # type: ignore[attr-defined]
        scale = float(self.ask(f"{self._prefix}:SCALe?"))
        ratio = float(self.ask(f"{self._prefix}:PROBe?"))
        self.log.warning(
            "%s %g V is outside the range at %g V/div and probe ratio %g; the "
            "instrument set %g V",
            param.name, value, scale, ratio, actual,
        )

    def _set_offset(self, value: float) -> None:
        if self._require_on_unless_unchanged("OFFSet", value, "offset"):
            return
        self._write_in_range("OFFSet", value, self.offset)

    def _set_delay_calibration(self, value: float) -> None:
        current = float(self.ask(f"{self._prefix}:TCALibrate?"))
        if math.isclose(current, value, rel_tol=_READBACK_RTOL, abs_tol=1e-15):
            return
        self.root_instrument._write_or_raise(
            f"{self._prefix}:TCALibrate", value, self.delay_calibration
        )

    def _set_bias(self, value: float) -> None:
        self._write_in_range("POSition", value, self.bias)

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
        """The waveform preamble of a source in the current mode, for the whole record.

        Selects the whole record first (:WAVeform:STARt 1, :WAVeform:STOP at its
        end): the points the preamble reports are those between start and stop, not
        the record length.

        Args:
            source: Waveform source as in :WAVeform:SOURce, e.g. "CHANnel1".

        Returns:
            By key: format, type, points, count, xincrement, xorigin, xreference,
            yincrement, yorigin and yreference.

        Raises:
            RuntimeError: If the preamble does not have ten fields.
        """
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
        return self._ask_preamble()

    def _ask_preamble(self) -> dict[str, float]:
        fields = self.ask(":WAVeform:PREamble?").split(",")
        if len(fields) != 10:
            raise RuntimeError(f"{self.full_name}: unexpected preamble {fields!r}")
        keys = (
            "format", "type", "points", "count", "xincrement", "xorigin",
            "xreference", "yincrement", "yorigin", "yreference",
        )  # fmt: skip
        return {key: float(value) for key, value in zip(keys, fields, strict=True)}

    def _axis_preamble(self) -> dict[str, float]:
        # the preamble of a channel that is off has 0 points, and so has that of a
        # channel turned on after the acquisition stopped (normal mode); all channels
        # with samples share the time axis
        pre = None
        for channel in self.root_instrument.channels:
            if channel.is_on():
                pre = self.preamble(channel.source_name)
                if pre["points"] > 0:
                    return pre
        return pre if pre is not None else self.preamble("CHANnel1")

    def _get_points(self) -> int:
        return int(self._axis_preamble()["points"])

    def _get_time_axis(self) -> npt.NDArray[np.float64]:
        pre = self._axis_preamble()
        n = int(pre["points"])
        times = pre["xorigin"] + (np.arange(n) - pre["xreference"]) * pre["xincrement"]
        return np.asarray(times, dtype=np.float64)

    def _needs_stop(self, pre: dict[str, float]) -> bool:
        # type 2: raw; type 1 (maximum) reads the memory only while stopped
        return int(pre["type"]) == 2

    def _check_memory(self, source: str) -> None:
        """Refuse a memory read of a channel whose memory is not its own.

        The instrument records other channels than those that are on for some sets of
        channels (memory_channels), and a memory read follows the channels on now, not
        those of the acquisition."""
        root = self.root_instrument
        if not source.upper().startswith("CHAN"):
            return
        on = tuple(n for n, ch in enumerate(root.channels, 1) if ch.is_on())
        if memory_channels(on) != on:
            names = ", ".join(f"CH{n}" for n in on)
            turn_on = ", ".join(
                f"CH{n}" for n in readable_channels(on, root.n_channels) if n not in on
            )
            raise RuntimeError(
                f"{self.full_name}: with {names} on, the instrument records "
                f"{', '.join(f'CH{n}' for n in memory_channels(on))} into the memory, "
                f"not the channels that are on: turn on {turn_on} and acquire again, "
                "or read the display (mode normal)"
            )
        acquired = root._acquired_channels
        if acquired is not None and acquired != on:
            raise RuntimeError(
                f"{self.full_name}: channels were turned on or off after the "
                "acquisition, which moves the memory of the others: acquire again"
            )

    def read(self, source: str) -> npt.NDArray[np.float64]:
        """Read the waveform of a source.

        Args:
            source: Waveform source as in :WAVeform:SOURce, e.g. "CHANnel1".

        Returns:
            The samples in V.

        Raises:
            RuntimeError: As read_with_preamble().
        """
        return self.read_with_preamble(source)[0]

    def read_with_preamble(
        self, source: str
    ) -> tuple[npt.NDArray[np.float64], dict[str, float]]:
        """Read the waveform of a source, with the preamble of the read.

        Args:
            source: Waveform source as in :WAVeform:SOURce, e.g. "CHANnel1".

        Returns:
            The samples in V, and the preamble of the read (see preamble()) for
            their time axis.

        Raises:
            RuntimeError: If the memory (raw mode) is read while the acquisition
                runs; if the memory of the source is not its own for the channels
                on (memory_channels), or channels were turned on or off since the
                acquisition; if the source has no samples; if a block has another
                number of points than requested.
        """
        pre = self.preamble(source)
        stopped = self.ask(":TRIGger:STATus?").strip() == "STOP"
        if self._needs_stop(pre) and not stopped:
            raise RuntimeError(
                f"{self.full_name}: the memory (raw mode) can only be read while the "
                "acquisition is stopped: call stop() or digitize() first"
            )
        # raw, or maximum while stopped: the memory
        if stopped and self.ask(":WAVeform:MODE?").strip() in ("RAW", "MAX"):
            self._check_memory(source)
        return self._read_points(source, pre), pre

    def _read_memory(
        self, source: str, points: int
    ) -> tuple[npt.NDArray[np.float64], dict[str, float]]:
        """read_with_preamble() of a stopped raw acquisition, without its checks.

        Reads points points without the queries of the mode, the trigger status and
        the channels on: for a caller that has established them for a series of
        acquisitions (frequency_response). One query for the preamble instead of
        about ten."""
        self.write(f":WAVeform:SOURce {source}")
        self.write(":WAVeform:FORMat WORD")
        self.write(":WAVeform:STARt 1")
        self.write(f":WAVeform:STOP {points}")
        pre = self._ask_preamble()
        return self._read_points(source, pre), pre

    def _read_points(
        self, source: str, pre: dict[str, float]
    ) -> npt.NDArray[np.float64]:
        n = int(pre["points"])
        if n == 0:
            raise RuntimeError(
                f"{self.full_name}: {source} has no samples in the stopped acquisition "
                "(the channel was turned on after it): acquire again"
            )
        raw = np.empty(n, dtype=np.uint16)
        chunk = self.chunk_points
        for first in range(0, n, chunk):
            last = min(first + chunk, n)
            # stop first, then start: preamble() left start 1, so start <= stop
            # holds at every step
            self.write(f":WAVeform:STOP {last}")
            self.write(f":WAVeform:STARt {first + 1}")
            block = self.root_instrument.query_block(":WAVeform:DATA?", "H")
            if len(block) == 0:
                raise EmptyReadError(
                    f"{self.full_name}: 0 points received for points {first + 1} "
                    f"to {last} of {source}"
                )
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
            parameter_class=_ReadBackParameter,
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
            parameter_class=_ReadBackParameter,
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
        the scale and the run state; a value the instrument clips is logged as a
        warning and cached as clipped."""

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
            parameter_class=_ReadBackParameter,
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
            parameter_class=_ReadBackParameter,
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
            parameter_class=_ReadBackParameter,
            label="Memory depth",
            unit="pts",
            get_cmd=":ACQuire:MDEPth?",
            set_cmd=self._set_memory_depth,
            get_parser=float,
            vals=MultiType(Enum("auto"), Enum(*MEMORY_DEPTHS)),
        )
        """Points per acquisition: "auto" or 1e3, 1e4, 1e5, 1e6, 1e7, 2.5e7, 5e7. The
        largest depth depends on the number of channels on (DHO900: 50M for one,
        25M for two, 10M for three or four); the trigger source counts as a channel
        on, also while it is off. A read returns the depth in use, also
        in auto. A depth the instrument does not accept is replaced by the one it
        sets, which is logged as a warning and cached."""

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
            parameter_class=_ReadBackParameter,
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
            parameter_class=_ReadBackParameter,
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

    FUNCTIONS: ClassVar[dict[str, str]] = {
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
    MODULATION_FUNCTIONS: ClassVar[dict[str, str]] = {
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
        """The set function of a modulation setting of kind (AM, FM, PM).

        The value is written while the modulation is on with that type; otherwise an
        unchanged value is accepted and a change refused."""

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


class RigolDHO900Bode(InstrumentModule["RigolDHO900"]):
    """The instrument's own Bode plot (:BODeplot, DHO914S and DHO924S).

    It sweeps the generator and draws gain and phase on the display.

    The programming guide has no command that reads the results; they are available
    only on the display (screenshot()). frequency_response measures gain and phase
    from the waveforms instead and returns them.

    While it runs, the instrument sets the input and output channels to AC coupling
    and leaves them so, and changes their vertical scales, the time base and the
    memory depth; the generator output is on during the sweep and off at its end.
    Input and output must be different channels (the instrument rejects the same
    channel, -222), and writing a source turns that channel on, also an unchanged
    source while the plot is off (the driver writes only a change). Out-of-range
    values are clipped without an error (a start frequency above the stop becomes
    stop - 10 Hz, a stop below the start becomes start + 10 Hz, an amplitude of 6 V
    becomes 1.705 V); the driver refuses values outside the guide's ranges, and a
    start or stop frequency the instrument clips against the other is logged as a
    warning and cached as clipped."""

    def __init__(
        self, parent: RigolDHO900, name: str, **kwargs: Unpack[InstrumentBaseKWArgs]
    ) -> None:
        super().__init__(parent, name, **kwargs)
        # the instrument returns CHAN1 (the guide: CHANnel1) and accepts both forms
        sources = {f"ch{n}": f"CHAN{n}" for n in range(1, parent.n_channels + 1)}

        self.enabled: Parameter = self.add_parameter(
            "enabled",
            label="Bode plot shown",
            get_cmd=":BODeplot:ENABle?",
            set_cmd=self._set_enabled,
            val_mapping=_ON_OFF,
        )
        """Whether the Bode plot window is shown. Turning it off turns the generator
        output off; the driver therefore writes nothing when it is off already."""

        self.sweep_type: Parameter = self.add_parameter(
            "sweep_type",
            label="Bode sweep type",
            get_cmd=":BODeplot:SWEeptype?",
            set_cmd=":BODeplot:SWEeptype {}",
            val_mapping={"log": "LOG", "linear": "LINE"},
        )
        """Logarithmic or linear frequency steps."""

        self.input_source: Parameter = self.add_parameter(
            "input_source",
            label="Bode input",
            get_cmd=":BODeplot:REF:IN?",
            set_cmd=self._source_setter(":BODeplot:REF:IN", ":BODeplot:REF:OUT?"),
            val_mapping=sources,
        )
        """The channel at the input of the device under test; not the output
        channel. A change turns the channel on."""

        self.output_source: Parameter = self.add_parameter(
            "output_source",
            label="Bode output",
            get_cmd=":BODeplot:REF:OUT?",
            set_cmd=self._source_setter(":BODeplot:REF:OUT", ":BODeplot:REF:IN?"),
            val_mapping=sources,
        )
        """The channel at the output of the device under test; not the input
        channel. A change turns the channel on."""

        self.start_frequency: Parameter = self.add_parameter(
            "start_frequency",
            parameter_class=_ReadBackParameter,
            label="Bode start frequency",
            unit="Hz",
            get_cmd=":BODeplot:STARt?",
            set_cmd=lambda value: parent._write_checked(
                ":BODeplot:STARt", value, self.start_frequency
            ),
            get_parser=float,
            vals=Numbers(10, 24.99e6),
        )
        """Start frequency, 10 Hz to 24.99 MHz, below the stop frequency."""

        self.stop_frequency: Parameter = self.add_parameter(
            "stop_frequency",
            parameter_class=_ReadBackParameter,
            label="Bode stop frequency",
            unit="Hz",
            get_cmd=":BODeplot:STOP?",
            set_cmd=lambda value: parent._write_checked(
                ":BODeplot:STOP", value, self.stop_frequency
            ),
            get_parser=float,
            vals=Numbers(100, 25e6),
        )
        """Stop frequency, 100 Hz to 25 MHz, above the start frequency."""

        self.points_per_decade: Parameter = self.add_parameter(
            "points_per_decade",
            label="Bode points per decade",
            get_cmd=":BODeplot:POINts?",
            set_cmd=":BODeplot:POINts {}",
            get_parser=int,
            vals=Ints(10, 300),
        )
        """Frequency points per decade (logarithmic sweep)."""

        self.amplitude: Parameter = self.add_parameter(
            "amplitude",
            label="Bode amplitude",
            unit="Vpp",
            get_cmd=":BODeplot:VOLTage? ALL",
            set_cmd=":BODeplot:VOLTage ALL,{:.6e}",
            get_parser=float,
            vals=Numbers(20e-3, 5.0),
        )
        """Generator amplitude of the whole sweep, 20 mV to 5 V peak-to-peak. The
        amplitudes of the frequency ranges (:BODeplot:VOLTage <range>,<amp>) are
        separate settings that this one does not change."""

        self.running: Parameter = self.add_parameter(
            "running",
            label="Bode sweep in progress",
            get_cmd=":BODeplot:RUNStop?",
            val_mapping=_ON_OFF,
        )
        """Whether a sweep is in progress; start() and stop() change it."""

    def _set_enabled(self, value: str) -> None:
        # :BODeplot:ENABle 0 turns the generator output off, also when the Bode plot
        # is off already
        if value == "0" and self.ask(":BODeplot:ENABle?").strip() == "0":
            return
        self.write(f":BODeplot:ENABle {value}")

    def _source_setter(self, header: str, other_query: str) -> Any:
        # writing a source turns that channel on, also the unchanged source
        def set_source(keyword: str) -> None:
            if self.ask(f"{header}?").strip() == keyword:
                return
            if self.ask(other_query).strip() == keyword:
                raise ValueError(
                    f"{self.full_name}: input and output must be different channels "
                    "(the instrument rejects the same channel)"
                )
            self.write(f"{header} {keyword}")

        return set_source

    def start(self) -> None:
        """Show the Bode plot and start a sweep; returns immediately."""
        self.write(":BODeplot:ENABle 1")
        self.write(":BODeplot:RUNStop 1")

    def stop(self) -> None:
        """Stop the sweep in progress."""
        self.write(":BODeplot:RUNStop 0")

    def sweep(self, timeout: float = 3600.0, poll_interval: float = 0.5) -> float:
        """Run one sweep and return when it has ended.

        The results are shown on the display only.

        Args:
            timeout: Longest duration of the sweep in s.
            poll_interval: Interval in s between the queries of the sweep's state.

        Returns:
            The duration of the sweep in s.

        Raises:
            TimeoutError: If the sweep has not ended within timeout; the sweep is
                then stopped.
        """
        self.start()
        begin = time.monotonic()
        while True:
            time.sleep(poll_interval)
            elapsed = time.monotonic() - begin
            if self.ask(":BODeplot:RUNStop?").strip() == "0":
                return elapsed
            if elapsed > timeout:
                self.stop()
                raise TimeoutError(
                    f"{self.full_name}: sweep not ended within {timeout} s"
                )


class RigolDHO900ResponseParameter(MultiParameter):
    """Gain (dB) and phase (deg) against frequency from one frequency_response sweep.

    The frequencies are those of its settings."""

    def __init__(
        self, name: str, instrument: RigolDHO900FrequencyResponse, **kwargs: Any
    ) -> None:
        super().__init__(
            name,
            names=("gain", "phase"),
            shapes=((1,), (1,)),
            instrument=instrument,
            labels=("Gain", "Phase"),
            units=("dB", "deg"),
            setpoints=None,
            setpoint_names=(("frequency",), ("frequency",)),
            setpoint_labels=(("Frequency",), ("Frequency",)),
            setpoint_units=(("Hz",), ("Hz",)),
            snapshot_get=False,
            snapshot_value=False,
            docstring="Gain (dB) and phase (deg) of a sweep of frequency_response.",
            **kwargs,
        )
        self._module = instrument

    # shapes and setpoints follow the frequency settings: a measurement registers
    # them before the sweep

    @property  # type: ignore[override]
    def shapes(self) -> tuple[tuple[int, ...], ...]:
        """The shapes of gain and phase, from the frequencies of the settings."""
        n = len(self._module.frequencies())
        return ((n,), (n,))

    @shapes.setter
    def shapes(self, value: Any) -> None:
        pass

    @property
    def setpoints(self) -> tuple[tuple[tuple[float, ...]], ...]:
        """The frequencies of the settings, the setpoints of gain and phase."""
        freqs = tuple(float(f) for f in self._module.frequencies())
        return ((freqs,), (freqs,))

    @setpoints.setter
    def setpoints(self, value: Any) -> None:
        pass

    def get_raw(self) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
        """Run a sweep and return its gain and phase."""
        result = self._module.sweep()
        return result["gain"], result["phase"]


class RigolDHO900FrequencyResponse(InstrumentModule["RigolDHO900"]):
    """Gain and phase of a device under test from the generator and two channels.

    Measured with the generator (DHO914S, DHO924S) and the waveforms of two
    channels, the method of https://github.com/wjakob/rigol (BSD-3-Clause).

    At each frequency the generator outputs a sine; one single acquisition records
    the input and output channels over at least ``cycles`` periods, and a sine at
    the generator's frequency is fitted to each trace by least squares (fit_sine).
    Gain and phase are the ratio of the fitted amplitudes and the difference of the
    fitted phases. With autoscale, the vertical scales are adjusted between
    acquisitions, in steps of the 1-2-5 sequence, so that the peak of each signal
    lies at 1.6 to 4 of the 4 divisions above the center line without
    clipping, which keeps the 12-bit resolution over a wide range of gains.

    The settings of this module are kept by the driver, not by the instrument;
    they do not change the instrument's own Bode plot (bode)."""

    #: acquisitions per frequency at most, while autoscale adjusts the scales
    max_acquisitions = 6
    #: the range of the signal peak, in divisions, that autoscale accepts without a
    #: change of a scale of the 1-2-5 sequence; a new scale is the step of that
    #: sequence that places the peak at or below the upper end (1.6 to 4 div)
    accepted_divisions = (1.5, 4.0)

    def __init__(
        self, parent: RigolDHO900, name: str, **kwargs: Unpack[InstrumentBaseKWArgs]
    ) -> None:
        super().__init__(parent, name, **kwargs)
        channels = [f"ch{n}" for n in range(1, parent.n_channels + 1)]

        self.input_source: Parameter = self.add_parameter(
            "input_source",
            label="Input",
            initial_value="ch1",
            set_cmd=None,
            vals=Enum("awg", *channels),
        )
        """The channel at the input of the device under test, or "awg": the set
        generator amplitude is the input then, and the phase is NaN."""

        self.output_source: Parameter = self.add_parameter(
            "output_source",
            label="Output",
            initial_value="ch2",
            set_cmd=None,
            vals=Enum(*channels),
        )
        """The channel at the output of the device under test."""

        self.sweep_type: Parameter = self.add_parameter(
            "sweep_type",
            label="Sweep type",
            initial_value="log",
            set_cmd=None,
            vals=Enum("log", "linear"),
        )
        """Logarithmic frequency steps (points_per_decade) or linear steps
        (points)."""

        self.start_frequency: Parameter = self.add_parameter(
            "start_frequency",
            label="Start frequency",
            unit="Hz",
            initial_value=1e3,
            set_cmd=None,
            vals=Numbers(0.1, 25e6),
        )
        """First frequency of the sweep."""

        self.stop_frequency: Parameter = self.add_parameter(
            "stop_frequency",
            label="Stop frequency",
            unit="Hz",
            initial_value=1e6,
            set_cmd=None,
            vals=Numbers(0.1, 25e6),
        )
        """Last frequency of the sweep."""

        self.points_per_decade: Parameter = self.add_parameter(
            "points_per_decade",
            label="Points per decade",
            initial_value=10,
            set_cmd=None,
            vals=Ints(1, 1000),
        )
        """Frequency points per decade of a logarithmic sweep (log_frequencies)."""

        self.points: Parameter = self.add_parameter(
            "points",
            label="Points",
            initial_value=50,
            set_cmd=None,
            vals=Ints(2, 10000),
        )
        """Number of equally spaced frequency points of a linear sweep, start and
        stop included."""

        self.frequencies: Parameter = self.add_parameter(
            "frequencies",
            label="Frequency",
            unit="Hz",
            get_cmd=self._get_frequencies,
            snapshot_value=False,
        )
        """The frequencies of the sweep, from sweep type, start, stop and points per
        decade (logarithmic) or points (linear)."""

        self.amplitude: Parameter = self.add_parameter(
            "amplitude",
            label="Generator amplitude",
            unit="Vpp",
            initial_value=1.0,
            set_cmd=None,
            vals=Numbers(AWG_MIN_AMPLITUDE, AWG_MAX_AMPLITUDE[0][1]),
        )
        """Peak-to-peak amplitude of the generator's sine into a high impedance; at
        most 5 V for a sweep above 10 MHz."""

        self.cycles: Parameter = self.add_parameter(
            "cycles",
            label="Periods per acquisition",
            initial_value=10,
            set_cmd=None,
            vals=Ints(1, 10000),
        )
        """Periods on the screen at least: the time base is the 1-2-5 step at or
        above cycles / frequency / 10 div. The record can extend beyond the screen
        at fast time bases."""

        self.memory_depth: Parameter = self.add_parameter(
            "memory_depth",
            label="Memory depth",
            unit="pts",
            initial_value=1e4,
            set_cmd=None,
            vals=Enum(*MEMORY_DEPTHS[:4]),
        )
        """Memory depth of the acquisitions, 1e3 to 1e6 points."""

        self.settling_time: Parameter = self.add_parameter(
            "settling_time",
            label="Settling time",
            unit="s",
            initial_value=0.0,
            set_cmd=None,
            vals=Numbers(0, 3600),
        )
        """Delay between a frequency change and the acquisition, for a device under
        test with long time constants."""

        self.autoscale: Parameter = self.add_parameter(
            "autoscale",
            label="Adjust vertical scales",
            initial_value=True,
            set_cmd=None,
            vals=Bool(),
        )
        """Whether the vertical scales are adjusted to each signal (see the class
        docstring); otherwise they stay as set."""

        self.through_correction: Parameter = self.add_parameter(
            "through_correction",
            label="Apply the through calibration",
            initial_value=True,
            set_cmd=None,
            vals=Bool(),
        )
        """Whether sweep() corrects gain and phase by the through calibration
        (calibrate_through()), while one exists."""

        self.through_calibrated: Parameter = self.add_parameter(
            "through_calibrated",
            label="Through calibration available",
            get_cmd=lambda: self.through_calibration is not None,
        )
        """Whether a through calibration exists (through_calibration)."""

        self.response: RigolDHO900ResponseParameter = self.add_parameter(
            "response", parameter_class=RigolDHO900ResponseParameter
        )
        """Gain (dB) and phase (deg) from one sweep, for the QCoDeS dataset."""

        self.last_sweep: dict[str, npt.NDArray[np.float64]] | None = None
        """The result of the most recent sweep() (see there)."""

        self.through_calibration: dict[str, Any] | None = None
        """The reference of calibrate_through(), or None: arrays by key frequency
        (Hz), gain (dB) and phase (deg), and the input_source and output_source it
        was measured with. Can be saved and set again for a later session with the
        same probes and channels."""

    def _get_frequencies(self) -> npt.NDArray[np.float64]:
        start, stop = self.start_frequency(), self.stop_frequency()
        if self.sweep_type() == "log":
            return log_frequencies(start, stop, self.points_per_decade())
        return linear_frequencies(start, stop, self.points())

    def sweep(
        self, frequencies: npt.ArrayLike | None = None
    ) -> dict[str, npt.NDArray[np.float64]]:
        """Measure gain and phase at the frequencies of the settings or at given ones.

        Changes the instrument settings: generator (sine, amplitude, no offset or
        modulation, frequency; the output is on during the sweep and back in its
        previous state afterwards), the two channels (on, offset 0, scales with
        autoscale), time base (main mode, no auto roll, offset 0), memory depth,
        edge trigger on the input channel (on the output channel with "awg"
        as input) at 0 V, rising, and the waveform mode (raw). Coupling,
        bandwidth limit and probe ratio stay as set. Turns on CH1 (and CH2, CH3)
        where the instrument records the measured channels into the memory only
        with them (memory_channels).

        With a through calibration (calibrate_through()) and through_correction
        on, gain and phase are corrected by the reference: the gain in dB and the
        phase are its differences from the reference, interpolated between the
        reference's frequencies (the gain over log f, the phase linearly over f,
        exact for a delay).

        Args:
            frequencies: Frequencies in Hz; by default those of the settings
                (frequencies).

        Returns:
            Arrays by key, also kept as last_sweep: frequency (the generator's, Hz),
            gain (dB), phase (deg, unwrapped over the sweep; NaN with "awg" as
            input), raw_gain and raw_phase (without the through correction; equal
            to gain and phase without it), input_amplitude and output_amplitude (V,
            peak), input_scale and output_scale (V/div of the acquisition used).

        Raises:
            RuntimeError: If the instrument has no generator.
            ValueError: If input and output are the same channel, there are no
                frequencies, a frequency lies outside the generator's range, or
                the amplitude exceeds the generator's limit at the highest
                frequency; with the through correction, if the calibration was
                measured with other channels or a frequency lies outside its
                range.
            TimeoutError: If an acquisition does not end, also after a forced
                trigger.
        """
        return self._sweep(frequencies, correct=self.through_correction())

    def calibrate_through(
        self, frequencies: npt.ArrayLike | None = None
    ) -> dict[str, Any]:
        """Measure the reference of the through correction.

        Connect the input and output channel to the same node (the generator's
        output, or the input of the device under test) before. The sweep then
        measures the difference between the two channels and their probes: delay
        (channel skew, and the interleaving of the instrument's ADC between the
        channels, 0.8 ns between CH1 and CH2 with four channels on), gain and the
        frequency response of the probes. Later sweeps with the same input and
        output source are corrected by it while through_correction is on. A
        reference that deviates by more than 3 dB or 45 deg is logged as a
        warning: the channels are then probably not on the same node.

        Args:
            frequencies: Frequencies in Hz; by default those of the settings
                (frequencies). Later sweeps must lie within their range.

        Returns:
            The reference, also kept as through_calibration.

        Raises:
            RuntimeError: As sweep().
            ValueError: As sweep().
            TimeoutError: As sweep().
        """
        result = self._sweep(frequencies, correct=False)
        reference: dict[str, Any] = {
            "frequency": result["frequency"].copy(),
            "gain": result["gain"].copy(),
            "phase": result["phase"].copy(),
            "input_source": self.input_source(),
            "output_source": self.output_source(),
        }
        worst_gain = float(np.nanmax(np.abs(reference["gain"])))
        phases = reference["phase"][np.isfinite(reference["phase"])]
        worst_phase = float(np.max(np.abs(phases))) if phases.size else 0.0
        if worst_gain > 3.0 or worst_phase > 45.0:
            self.log.warning(
                "through calibration deviates by up to %.1f dB and %.0f deg: the "
                "input and output channel are probably not on the same node",
                worst_gain, worst_phase,
            )  # fmt: skip
        self.through_calibration = reference
        return reference

    def clear_through_calibration(self) -> None:
        """Discard the through calibration; later sweeps are uncorrected."""
        self.through_calibration = None

    def _through_reference(
        self, freqs: npt.NDArray[np.float64]
    ) -> dict[str, Any] | None:
        """The through calibration for a sweep at freqs; None without one.

        Checked against the sources and the frequency range of the sweep."""
        reference = self.through_calibration
        if reference is None:
            return None
        sources = (reference["input_source"], reference["output_source"])
        if sources != (self.input_source(), self.output_source()):
            raise ValueError(
                f"{self.full_name}: the through calibration was measured with input "
                f"{sources[0]} and output {sources[1]}: calibrate again, or turn "
                "through_correction off"
            )
        ref_f = np.asarray(reference["frequency"], dtype=np.float64)
        low, high = float(np.min(ref_f)), float(np.max(ref_f))
        # the generator's frequencies differ from the requested ones by up to 1e-6
        if freqs.min() < low * (1 - 1e-6) or freqs.max() > high * (1 + 1e-6):
            raise ValueError(
                f"{self.full_name}: the through calibration covers {low:g} Hz to "
                f"{high:g} Hz, the sweep {freqs.min():g} Hz to {freqs.max():g} Hz"
            )
        return reference

    @staticmethod
    def _correct(
        reference: dict[str, Any],
        frequency: npt.NDArray[np.float64],
        gain: npt.NDArray[np.float64],
        wrapped: npt.NDArray[np.float64],
    ) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
        """Gain (dB) and wrapped phase (rad) corrected by a through reference."""
        order = np.argsort(reference["frequency"])
        ref_f = np.asarray(reference["frequency"], dtype=np.float64)[order]
        ref_gain = np.asarray(reference["gain"], dtype=np.float64)[order]
        ref_phase = np.radians(np.asarray(reference["phase"], dtype=np.float64)[order])
        f = np.clip(frequency, ref_f[0], ref_f[-1])
        gain = gain - np.interp(np.log10(f), np.log10(ref_f), ref_gain)
        if np.all(np.isfinite(ref_phase)):
            wrapped = np.remainder(
                wrapped - np.interp(f, ref_f, ref_phase) + np.pi, 2 * np.pi
            ) - np.pi
        return gain, wrapped

    def _sweep(
        self, frequencies: npt.ArrayLike | None, correct: bool
    ) -> dict[str, npt.NDArray[np.float64]]:
        root = self.root_instrument
        awg = root.awg
        if awg is None:
            raise RuntimeError(f"{self.full_name}: the instrument has no generator")
        input_source = self.input_source()
        output_source = self.output_source()
        if input_source == output_source:
            raise ValueError(f"{self.full_name}: input and output are the same channel")
        if frequencies is None:
            freqs = self.frequencies()
        else:
            freqs = np.atleast_1d(np.asarray(frequencies, dtype=np.float64))
        if freqs.size == 0:
            raise ValueError(f"{self.full_name}: no frequencies")
        if freqs.min() < AWG_MIN_FREQUENCY or freqs.max() > AWG_MAX_FREQUENCY["sine"]:
            raise ValueError(
                f"{self.full_name}: frequencies must lie within "
                f"{AWG_MIN_FREQUENCY:g} Hz to {AWG_MAX_FREQUENCY['sine']:g} Hz"
            )
        amplitude = self.amplitude()
        if amplitude > awg_max_amplitude(float(freqs.max())) * (1 + 1e-9):
            raise ValueError(
                f"{self.full_name}: amplitude {amplitude:g} V is above "
                f"{awg_max_amplitude(float(freqs.max())):g} V, the limit at "
                f"{freqs.max():g} Hz"
            )
        reference = self._through_reference(freqs) if correct else None
        channels: dict[str, RigolDHO900Channel] = {}
        for source in (input_source, output_source):
            if source != "awg":
                channels[source] = root.submodules[source]  # type: ignore[assignment]
        trigger_source = input_source if input_source != "awg" else output_source

        output_was_on = awg.output()
        self._prepare(awg, amplitude, float(freqs[0]), channels, trigger_source)
        scales = {source: ch.scale() for source, ch in channels.items()}
        # constant during the sweep: queried once, not at every acquisition
        ratios = {source: float(ch.probe_ratio()) for source, ch in channels.items()}
        depth = round(float(root.ask(":ACQuire:MDEPth?")))
        channels_on = root._channels_on()
        peaks: dict[str, list[float]] = {source: [] for source in channels}
        n = freqs.size
        result = {
            key: np.full(n, np.nan)
            for key in (
                "frequency", "gain", "phase", "input_amplitude", "output_amplitude",
                "input_scale", "output_scale",
            )
        }  # fmt: skip
        wrapped = np.full(n, np.nan)
        try:
            for i, frequency in enumerate(freqs):
                if self.autoscale():
                    self._predict_scales(channels, scales, ratios, peaks)
                fit = self._measure_point(
                    awg, float(frequency), channels, scales, ratios, depth, channels_on
                )
                for source in channels:
                    peaks[source].append(fit["peaks"][source])
                actual = fit["frequency"]
                result["frequency"][i] = actual
                out_amp, out_phase = fit[output_source]
                if input_source == "awg":
                    in_amp, in_phase = amplitude / 2, math.nan
                else:
                    in_amp, in_phase = fit[input_source]
                    result["input_scale"][i] = fit["scales"][input_source]
                result["output_scale"][i] = fit["scales"][output_source]
                result["input_amplitude"][i] = in_amp
                result["output_amplitude"][i] = out_amp
                if in_amp > 0 and out_amp > 0:
                    result["gain"][i] = 20 * math.log10(out_amp / in_amp)
                wrapped[i] = math.remainder(out_phase - in_phase, 2 * math.pi)
                self.log.debug(
                    "%g Hz, gain %.3f dB, phase %.2f deg",
                    actual, result["gain"][i],
                    math.degrees(wrapped[i]),
                )  # fmt: skip
        finally:
            if not output_was_on:
                awg.output(False)
        result["raw_gain"] = result["gain"].copy()
        if input_source != "awg":
            result["raw_phase"] = np.degrees(np.unwrap(wrapped))
        else:
            result["raw_phase"] = result["phase"].copy()
        if reference is not None:
            result["gain"], wrapped = self._correct(
                reference, result["frequency"], result["gain"], wrapped
            )
        if input_source != "awg":
            result["phase"] = np.degrees(np.unwrap(wrapped))
        self.last_sweep = result
        return result

    def _prepare(
        self,
        awg: RigolDHO900AWG,
        amplitude: float,
        first_frequency: float,
        channels: dict[str, RigolDHO900Channel],
        trigger_source: str,
    ) -> None:
        root = self.root_instrument
        awg.modulation(False)
        awg.offset(0.0)
        # amplitude and frequency limit each other: go through 1 kHz
        if awg.function() in ("dc", "noise"):
            awg.function("sine")
        awg.frequency(1e3)
        awg.function("sine")
        awg.amplitude(amplitude)
        awg.frequency(first_frequency)
        awg.output(True)
        for channel in channels.values():
            channel.enabled(True)
            channel.offset(0.0)
        # the memory of the measured channels is their own only for some sets of
        # channels on (memory_channels): turn on the others it requires
        on = root._channels_on()
        for n in readable_channels(on, root.n_channels):
            if n not in on:
                root.channels[n - 1].enabled(True)
        root.timebase.mode("main")
        root.timebase.auto_roll(False)
        root.timebase.delay_enabled(False)
        root.run()
        root.timebase.offset(0.0)
        root.acquisition.memory_depth(self.memory_depth())
        trigger = root.trigger
        trigger.type("edge")
        trigger.edge_source(trigger_source)
        trigger.edge_slope("rising")
        trigger.edge_level(0.0)
        root.waveform.mode("raw")

    def _measure_point(
        self,
        awg: RigolDHO900AWG,
        frequency: float,
        channels: dict[str, RigolDHO900Channel],
        scales: dict[str, float],
        ratios: dict[str, float],
        depth: int,
        channels_on: tuple[int, ...],
    ) -> dict[str, Any]:
        """Acquire at one frequency, adjusting the scales (autoscale).

        Returns the generator frequency, (amplitude, phase) of each channel and, by
        keys "peaks" and "scales", the peak of each trace (V) and the scale it was
        acquired at (V/div). A trace still clipped after the last acquisition is
        logged as a warning."""
        root = self.root_instrument
        # sweep() has checked frequency and amplitude against the generator's limits
        self.write(f":SOURce:FREQuency {frequency:.7e}")
        actual = float(self.ask(":SOURce:FREQuency?"))
        awg.frequency.cache.set(actual)
        timebase = scale_125(self.cycles() / actual / 10)
        timebase = min(max(timebase, 2e-9), 500.0)
        self._set_timebase(timebase)
        if self.settling_time() > 0:
            time.sleep(self.settling_time())
        fits: dict[str, Any] = {"frequency": actual, "peaks": {}, "scales": {}}
        for _ in range(self.max_acquisitions):
            self._acquire(2.0 + 30 * timebase, channels_on)
            changed = False
            try:
                reads = {
                    source: root.waveform._read_memory(channel.source_name, depth)
                    for source, channel in channels.items()
                }
            except EmptyReadError as error:
                self.log.warning("%s; acquiring again", error)
                continue
            for source, channel in channels.items():
                volts, pre = reads[source]
                t = pre["xorigin"] + (np.arange(volts.size) - pre["xreference"]) * pre[
                    "xincrement"
                ]
                amp, phase, offset = fit_sine(t, volts, actual)
                fits[source] = (amp, phase)
                fits["peaks"][source] = float(np.max(np.abs(volts)))
                # the scale of this acquisition: autoscale may change it below
                fits["scales"][source] = scales[source]
                if self.autoscale():
                    new = self._new_scale(
                        ratios[source], volts, amp, offset, scales[source]
                    )
                    if new != scales[source]:
                        channel.scale(new)
                        scales[source] = float(channel.scale())
                        changed = True
            if not changed:
                break
        if any(source not in fits for source in channels):
            raise EmptyReadError(
                f"{self.full_name}: no acquisition with samples at {actual:g} Hz in "
                f"{self.max_acquisitions} attempts"
            )
        for source, scale in fits["scales"].items():
            if fits["peaks"][source] >= CLIP_DIVISIONS * scale:
                self.log.warning(
                    "%g Hz: %s clipped at %g V/div in the last acquisition; gain "
                    "and phase of this point are unreliable",
                    actual, source, scale,
                )  # fmt: skip
        return fits

    def _set_timebase(self, scale: float) -> None:
        """Set the time base, while stopped where the instrument accepts the value.

        :RUN takes 0.1 s to 0.4 s. A stopped acquisition holds a time base far
        below that of its record (10 ms/div to 0.5 us/div gives 20 us/div): the
        acquisition is then started and the value set again."""
        root = self.root_instrument
        root.write(f":TIMebase:MAIN:SCALe {scale:.6e}")
        actual = float(root.ask(":TIMebase:MAIN:SCALe?"))
        if math.isclose(actual, scale, rel_tol=_READBACK_RTOL):
            root.timebase.scale.cache.set(actual)
        else:
            root.run()
            root.timebase.scale(scale)

    def _predict_scales(
        self,
        channels: dict[str, RigolDHO900Channel],
        scales: dict[str, float],
        ratios: dict[str, float],
        peaks: dict[str, list[float]],
    ) -> None:
        """Set each scale for the peak extrapolated from the last two points.

        A gain that changes along the sweep then does not cost a second
        acquisition."""
        for source, channel in channels.items():
            history = peaks[source]
            if len(history) < 2 or min(history[-2:]) <= 0:
                continue
            trend = min(max(history[-1] / history[-2], 0.5), 2.0)
            new = self._scale_for_peak(
                ratios[source], history[-1] * trend, scales[source]
            )
            if new != scales[source]:
                channel.scale(new)
                scales[source] = float(channel.scale())

    def _new_scale(
        self,
        ratio: float,
        volts: npt.NDArray[np.float64],
        amplitude: float,
        offset: float,
        scale: float,
    ) -> float:
        peak = float(np.max(np.abs(volts)))
        if peak >= CLIP_DIVISIONS * scale:
            return min(scale_125(scale * 5), 10.0 * ratio)
        # the peak of the trace, not that of the fitted sine: near a notch of the
        # response, harmonics and noise exceed the fundamental, and a scale for the
        # fundamental clips the trace
        return self._scale_for_peak(ratio, max(peak, amplitude + abs(offset)), scale)

    def _scale_for_peak(self, ratio: float, peak: float, scale: float) -> float:
        """The scale for a signal peak (V), a step of the 1-2-5 sequence.

        Unchanged while the scale is such a step and the peak lies within
        accepted_divisions, else the smallest step that holds the peak within the
        upper end. Only the steps: at scales between them the instrument's gain
        differed from the preamble's conversion by up to 0.11 dB (0.301, 0.341,
        0.461, 0.505 V/div; DHO914S, 10:1 probe), at the steps by 0.02 dB at most,
        so that a through calibration and a later sweep share the scale's gain."""
        low, high = 200e-6 * ratio, 10.0 * ratio
        if peak <= 0:
            return min(max(scale_125(low), low), high)
        lower, upper = self.accepted_divisions
        divisions = peak / scale
        on_grid = math.isclose(scale, scale_125(scale), rel_tol=1e-6)
        if on_grid and (
            lower <= divisions <= upper
            or (divisions < lower and scale <= low * (1 + 1e-9))
        ):
            return scale
        return min(max(scale_125(peak / upper), low), high)

    def _acquire(self, timeout: float, channels_on: tuple[int, ...]) -> None:
        """One single acquisition.

        A forced trigger if none arrives (a signal below the trigger's
        sensitivity)."""
        root = self.root_instrument
        try:
            root._digitize(timeout, 0.02, channels_on)
        except TimeoutError:
            root.force_trigger()
            deadline = time.monotonic() + timeout
            while self.ask(":TRIGger:STATus?").strip() != "STOP":
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.02)


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
            self.root_instrument._write_or_raise(
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

    The driver writes nothing at connect. A trace sets the waveform source, format
    and the start and stop points before it reads.

    Args:
        name: Name of the instrument.
        address: VISA address, e.g. ``USB0::0x1AB1::0x044C::<serial>::INSTR``.
        **kwargs: Passed on to VisaInstrument.

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
            self.log.warning("model %r is not a DHO800 or DHO900", model)
        self.model = model
        self.n_channels = int(self.ask(":SYSTem:RAMount?"))
        modules = self.ask(":SYSTem:MODules?").split(",")
        self.has_logic_analyzer = modules[0].strip() == "1"
        self.has_awg = self.ask(":SYSTem:DGSTatus?").strip() == "1"
        # the channels on at the last acquisition the driver started or stopped; None
        # while running or before (waveform reads check it, _check_memory)
        self._acquired_channels: tuple[int, ...] | None = None
        # when the driver last turned a channel on or off (time.monotonic())
        self._channels_changed = -math.inf

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
        self.bode: RigolDHO900Bode | None = None
        """The instrument's own Bode plot; None on models without a generator."""
        self.frequency_response: RigolDHO900FrequencyResponse | None = None
        """Gain and phase measured from the waveforms; None on models without a
        generator."""
        if self.has_awg:
            self.awg = self.add_submodule("awg", RigolDHO900AWG(self, "awg"))
            self.bode = self.add_submodule("bode", RigolDHO900Bode(self, "bode"))
            self.frequency_response = self.add_submodule(
                "frequency_response",
                RigolDHO900FrequencyResponse(self, "frequency_response"),
            )

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
        if (
            self.has_logic_analyzer
            and source.startswith("d")
            and source[1:].isdigit()
            and 0 <= int(source[1:]) <= 15
        ):
            return f"D{source[1:]}"
        raise ValueError(f"{self.name}: unknown source {source!r}")

    def _write_checked(
        self, header: str, value: float, param: Parameter, fmt: str = "{:.6e}"
    ) -> None:
        """Write a value and read it back.

        The instrument clips an out-of-range value
        without an error: a value it changed stays set, is logged as a warning and is
        the value cached (param is a _ReadBackParameter)."""
        self.write(f"{header} {fmt.format(value)}")
        actual = float(self.ask(f"{header}?"))
        if math.isclose(actual, value, rel_tol=_READBACK_RTOL, abs_tol=1e-15):
            return
        param.read_back = actual  # type: ignore[attr-defined]
        unit = f" {param.unit}" if param.unit else ""
        param.instrument.log.warning(  # type: ignore[union-attr]
            "%s %g%s is outside the instrument's range; the instrument set %g%s",
            param.name, value, unit, actual, unit,
        )

    def _write_or_raise(
        self, header: str, value: float, param: Parameter, fmt: str = "{:.6e}"
    ) -> None:
        """Write a value and read it back; raise if the instrument did not take it.

        For settings whose value the instrument ignores rather than clips (delay
        calibration at slow time bases, thresholds out of order): the setting then
        remains at its previous value."""
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
        then intermittently stalled for the whole VISA timeout.

        Args:
            command: The query.
            datatype: Struct format character of the values, e.g. "H".

        Returns:
            The values of the block.
        """
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

    def _channels_on(self) -> tuple[int, ...]:
        return tuple(n for n, ch in enumerate(self.channels, 1) if ch.is_on())

    #: s after a channel was turned on or off before digitize() arms an acquisition
    channel_settling = 1.0

    #: s after :SINGle within which a STOP without a preceding arming is taken as the
    #: instrument not yet armed, not as an acquisition that completed before the first
    #: poll: after a reconfiguration (run, time base, memory depth) the status read
    #: STOP for up to 0.44 s before the instrument armed
    arming_time = 1.0

    #: s after :RUN within which the trigger status must leave STOP before run()
    #: sends :RUN again; 0 turns the check off
    run_confirm_time = 1.0

    def run(self) -> None:
        """Start acquiring continuously; returns once the acquisition runs.

        The instrument applies :RUN 0.1 s to 0.4 s after it, and occasionally not at
        all. A :RUN still pending when a :SINGle arrives turns the single acquisition
        into a continuous one. run() therefore polls the trigger status until it
        leaves STOP, sends :RUN again after run_confirm_time, and raises TimeoutError
        after three attempts."""
        self._acquired_channels = None
        for _ in range(3):
            self.write(":RUN")
            if self.run_confirm_time <= 0:
                return
            start = time.monotonic()
            while time.monotonic() - start < self.run_confirm_time:
                if self.ask(":TRIGger:STATus?").strip() != "STOP":
                    return
                time.sleep(0.02)
        raise TimeoutError(f"{self.name}: the acquisition did not start after :RUN")

    def stop(self) -> None:
        """Stop acquiring; returns once the acquisition has stopped.

        The memory keeps the last acquisition.

        Raises:
            TimeoutError: If the trigger status has not read STOP within
                run_confirm_time after the second :STOP.
        """
        self._stop_confirmed()
        self._acquired_channels = self._channels_on()

    def _stop_confirmed(self) -> None:
        for _ in range(2):
            self.write(":STOP")
            if self.run_confirm_time <= 0:
                return
            start = time.monotonic()
            while time.monotonic() - start < self.run_confirm_time:
                if self.ask(":TRIGger:STATus?").strip() == "STOP":
                    return
                time.sleep(0.02)
        raise TimeoutError(f"{self.name}: the acquisition did not stop after :STOP")

    def single(self) -> None:
        """Arm a single acquisition (trigger sweep single); returns immediately."""
        self.write(":SINGle")
        self._acquired_channels = self._channels_on()

    def force_trigger(self) -> None:
        """Generate a trigger (normal and single sweep)."""
        self.write(":TFORce")

    def clear_display(self) -> None:
        """Clear the waveforms on the display."""
        self.write(":CLEar")

    def autoset(self) -> None:
        """Adjust scales, time base and trigger to the input signals (AUTO key).

        Changes most settings."""
        self.write(":AUToset")

    def digitize(self, timeout: float = 10.0, poll_interval: float = 0.02) -> None:
        """Acquire one waveform and wait until the acquisition has stopped.

        The channels' traces and the measurements then come from the same
        acquisition.

        Args:
            timeout: Longest wait for the trigger in s.
            poll_interval: Interval in s between the queries of the trigger status.

        Raises:
            TimeoutError: If no trigger arrives within timeout; the instrument then
                remains armed (force_trigger() completes it).
        """
        self._digitize(timeout, poll_interval, self._channels_on())

    def _digitize(
        self, timeout: float, poll_interval: float, channels_on: tuple[int, ...]
    ) -> None:
        """digitize() with the channels on already known (frequency_response)."""
        # after a channel was turned on or off, the trigger status does not follow
        # :SINGle for about 0.3 s (STOP before the arming, WAIT before a STOP)
        settling = self._channels_changed + self.channel_settling - time.monotonic()
        if settling > 0:
            time.sleep(settling)
        # a :SINGle while the acquisition runs occasionally stopped it without a
        # single acquisition (status STOP, trigger sweep AUTO, an empty memory;
        # 2026-11-14), and the running acquisition's WAIT or TD reads as an arming:
        # stop it first
        if self.ask(":TRIGger:STATus?").strip() != "STOP":
            self._stop_confirmed()
        # the first poll right after :SINGle: the instrument reports WAIT for about
        # 0.1 s even for a short record, so the arming is seen and the arming_time
        # fallback is rarely needed
        self.write(":SINGle")
        self._acquired_channels = channels_on
        start = time.monotonic()
        armed = False
        resent = False
        while True:
            status = self.ask(":TRIGger:STATus?").strip()
            elapsed = time.monotonic() - start
            if status != "STOP":
                armed = True
            elif armed or elapsed > self.arming_time:
                # STOP after the instrument reported the arming, or (after
                # arming_time) a single that completed before the first poll; before
                # that, STOP can also precede the arming
                return
            if elapsed > timeout:
                if not resent and self.ask(":TRIGger:SWEep?").strip() != "SING":
                    # the instrument acquires continuously: a :RUN applied after
                    # the :SINGle overrode it
                    self.log.warning(
                        "the acquisition ran continuously after :SINGle; "
                        "sending :SINGle again"
                    )
                    resent = True
                    self.write(":SINGle")
                    start = time.monotonic()
                    armed = False
                    continue
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
        """Whether one of the channel sources is off.

        A measurement query would turn it on."""
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
        """One automatic measurement.

        The instrument adds the item to the measurements on the display and computes
        it afterwards: while the result is invalid, it is queried again for up to
        wait seconds. On a stopped acquisition the instrument computes only some of
        the items added (about 14 added one at a time, none of many added in quick
        succession); an item still invalid there is queried once more after the
        display's items are removed (:MEASure:CLEar).

        Args:
            item: A key of MEASUREMENT_ITEMS, e.g. "vpp", "frequency", "phase_rr".
            source: "ch1", ..., "math1", ...
            source2: The second source of delays and phases.
            wait: Longest wait in s for a valid result; by default
                measurement_wait.

        Returns:
            The result; NaN when it cannot be measured, and for a channel that is
            off (which the instrument would turn on to measure it).

        Raises:
            ValueError: If the item or a source is unknown, or a delay or phase
                has no second source.
        """
        query = self._measurement_sources(item, source, source2)
        if self._sources_off(source, source2):
            return math.nan
        wait = self.measurement_wait if wait is None else wait
        value = self._query_measurement(query, wait)
        if (
            math.isnan(value)
            and wait > 0
            and self.ask(":TRIGger:STATus?").strip() == "STOP"
        ):
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
        """The statistics of a measurement, switching its statistics on first.

        Args:
            item: A key of MEASUREMENT_ITEMS.
            source: "ch1", ..., "math1", ...
            source2: The second source of delays and phases.

        Returns:
            By key: current, average, minimum, maximum, deviation and count. NaN
            where there is no value yet, and for a channel that is off.

        Raises:
            ValueError: As measure().
        """
        query = self._measurement_sources(item, source, source2)
        if self._sources_off(source, source2):
            return dict.fromkeys(STATISTICS, math.nan)
        self.write(f":MEASure:STATistic:ITEM {query}")
        return {
            key: _float_or_nan(self.ask(f":MEASure:STATistic:ITEM? {keyword},{query}"))
            for key, keyword in STATISTICS.items()
        }

    # --- instrument

    def screenshot(self, image_format: str = "png") -> bytes:
        """The display as an image file.

        Args:
            image_format: "png", "bmp" or "jpg".

        Returns:
            The content of the image file.

        Raises:
            ValueError: If the format is not one of these.
        """
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
        """Load a setup read by save_setup.

        Args:
            setup: The binary block that save_setup() returned.
        """
        self.visa_handle.write_binary_values(
            ":SYSTem:SETup ", list(setup), datatype="B"
        )

    def reset(self) -> None:
        """Restore the factory default settings (*RST)."""
        self.write("*RST")
