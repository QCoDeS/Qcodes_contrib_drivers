from collections import ChainMap
from .sdx import SiglentSDx, SiglentChannel, InstrumentBase

from qcodes.parameters import Group, GroupParameter

from qcodes.instrument.channel import ChannelList

from qcodes.validators.validators import MultiTypeOr, Numbers, Ints, Enum as EnumVals

from enum import Enum

from typing import (
    Any,
    Optional,
    Callable,
    List,
    Mapping,
    Set,
    Tuple,
    Iterable,
    Iterator,
)


from itertools import zip_longest


def _group_by_two(list_: Iterable, *, fillvalue=None) -> Iterator[Tuple[Any, Any]]:
    return zip_longest(*2 * [iter(list_)], fillvalue=fillvalue)


def _identity(x):
    return x


def _strip_unit(unit: str, *, then: Callable[[str], Any]) -> Callable[[str], Any]:
    len_unit = len(unit)

    def result_func(value: str):
        if value.endswith(unit):
            value = value[:-len_unit]
        return then(value)

    return result_func


class SiglentSDGChannel(SiglentChannel):
    def __init__(
        self, parent: InstrumentBase, name: str, channel_number: int, **kwargs
    ):
        super().__init__(parent, name, channel_number)
        self._ch_num_prefix = (
            f"C{channel_number}:" if channel_number is not None else ""
        )

        self._add_output_parameters(extra_params=kwargs.pop("extra_outp_params", set()))

        self._add_basic_wave_parameters(
            extra_params=kwargs.pop("extra_bswv_params", set())
        )

    def _add_output_parameters(self, *, extra_params: Set[str]):

        ch_num_prefix = self._ch_num_prefix
        cmd_prefix = ch_num_prefix + "OUTP"
        cmd_prefix_len = len(cmd_prefix)
        get_cmd = ch_num_prefix + "OUTP?"

        def extract_outp_field(
            name: Optional[str],
            *,
            then: Callable[[str], Any] = _identity,
            else_default=None,
        ) -> Callable[[str], Any]:
            def result_func(response: str):
                response = response[cmd_prefix_len + 1 :]
                (enabled, *keys_values) = response.split(",")
                if name is None:
                    return enabled
                for key, value in _group_by_two(keys_values):
                    if key == name:
                        return then(value)
                else:
                    return else_default

            return result_func

        self.add_parameter(
            "enabled",
            label="Enabled",
            val_mapping={True: "ON", False: "OFF"},
            set_cmd=cmd_prefix + " {}",
            get_cmd=get_cmd,
            get_parser=extract_outp_field(None),
        )

        self.add_parameter(
            "load",
            label="Output load",
            unit="Ω",
            vals=MultiTypeOr(Numbers(50, 1e5), EnumVals("HZ")),
            set_cmd=cmd_prefix + " LOAD,{}",
            get_cmd=get_cmd,
            get_parser=extract_outp_field("LOAD"),
        )

        if "POWERON_STATE" in extra_params:
            self.add_parameter(
                "poweron_state",
                label="Power-on state",
                val_mapping={
                    False: 0,
                    True: 1,
                },
                set_cmd=cmd_prefix + " POWERON_STATE,{}",
                get_cmd=get_cmd,
                get_parser=extract_outp_field("POWERON_STATE"),
            )

        self.add_parameter(
            "polarity",
            label="Polarity",
            val_mapping={
                "normal": "NOR",
                "inverted": "INVT",
            },
            set_cmd=cmd_prefix + " PLRT,{}",
            get_cmd=get_cmd,
            get_parser=extract_outp_field("PLRT"),
        )

    def _add_basic_wave_parameters(self, *, extra_params: Set[str]):
        ch_num_prefix = self._ch_num_prefix
        cmd_prefix = ch_num_prefix + "BSWV"
        cmd_prefix_len = len(cmd_prefix)
        get_cmd = ch_num_prefix + "BSWV?"

        def extract_bswv_field(
            name: str, *, then: Callable[[str], Any] = _identity, else_default=None
        ) -> Callable[[str], Any]:
            def result_func(response: str):
                response = response[cmd_prefix_len + 1 :]
                values = response.split(",")
                for key, value in zip(*2 * [iter(values)]):
                    if key == name:
                        return then(value)
                else:
                    return else_default

            return result_func

        self.add_parameter(
            "wave_type",
            label="Basic Wave type",
            val_mapping={
                "sine": "SINE",
                "square": "SQUARE",
                "ramp": "RAMP",
                "pulse": "PULSE",
                "noise": "NOISE",
                "arb": "ARB",
                "dc": "DC",
                "prbs": "PRBS",
                "iq": "IQ",
            },
            set_cmd=cmd_prefix + " WVTP,{}",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("WVTP"),
        )

        ranges: Mapping[str, Tuple[float, float]] = self._parent._ranges

        freq_ranges = ranges["frequency"]
        amp_range_vpp = ranges["vpp"]
        amp_range_vrms = ranges["vrms"]
        range_offset = ranges["offset"]

        self.add_parameter(
            "frequency",
            label="Basic Wave Frequency",
            vals=Numbers(freq_ranges[0], freq_ranges[1]),
            unit="Hz",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("FRQ", then=_strip_unit("HZ", then=float)),
            set_cmd=cmd_prefix + " FRQ,{}",
        )

        self.add_parameter(
            "period",
            label="Basic Wave Period",
            vals=Numbers(1 / freq_ranges[1], 1 / freq_ranges[0]),
            unit="s",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("PERI", then=_strip_unit("S", then=float)),
            set_cmd=cmd_prefix + " PERI,{}",
        )

        self.add_parameter(
            "amplitude",
            label="Basic Wave Amplitude (Peak-to-Peak)",
            vals=Numbers(amp_range_vpp[0], amp_range_vpp[1]),
            unit="V",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("AMP", then=_strip_unit("V", then=float)),
            set_cmd=cmd_prefix + " AMP,{}",
        )

        self.add_parameter(
            "amplitude_rms",
            label="Basic Wave Amplitude (RMS)",
            vals=Numbers(amp_range_vrms[0], amp_range_vrms[1]),
            unit="V",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("AMPRMS", then=_strip_unit("V", then=float)),
            set_cmd=cmd_prefix + " AMPRMS,{}",
        )

        # doesn't seem to work
        self.add_parameter(
            "amplitude_dbm",
            label="Basic Wave Amplitude (dBm)",
            vals=Numbers(),
            unit="dBm",
            # get_cmd=get_cmd,
            # get_parser=extract_bswv_field("AMPDBM", then=strip_unit("dBm", then=float)),
            set_cmd=cmd_prefix + " AMPDBM,{}",
        )

        if "MAX_OUTPUT_AMP" in extra_params:
            self.add_parameter(
                "max_output_amp",
                label="Max output amplitude",
                vals=Numbers(min_value=0),
                unit="V",
                get_cmd=get_cmd,
                get_parser=extract_bswv_field(
                    "MAX_OUTPUT_AMP", then=_strip_unit("V", then=float)
                ),
                set_cmd=cmd_prefix + " MAX_OUTPUT_AMP,{}",
            )

        self.add_parameter(
            "offset",
            label="Offset",
            vals=Numbers(range_offset[0], range_offset[1]),
            unit="V",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("OFST", then=_strip_unit("V", then=float)),
            set_cmd=cmd_prefix + " OFST,{}",
        )

        self.add_parameter(
            "common_offset",
            label="Common Offset (Differential output)",
            vals=Numbers(-1, 1),
            unit="V",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field(
                "COM_OFST", then=_strip_unit("V", then=float)
            ),
            set_cmd=cmd_prefix + " COM_OFST,{}",
        )

        self.add_parameter(
            "ramp_symmetry",
            label="Ramp Symmetry",
            vals=Numbers(0.0, 100.0),
            unit="%",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("SYM", then=_strip_unit("%", then=float)),
            set_cmd=cmd_prefix + " SYM,{}",
        )

        self.add_parameter(
            "duty_cycle",
            label="Duty cycle (Square/Pulse)",
            vals=Numbers(0.0, 100.0),
            unit="%",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("DUTY", then=_strip_unit("%", then=float)),
            set_cmd=cmd_prefix + " DUTY,{}",
        )

        self.add_parameter(
            "phase",
            label="Phase",
            vals=Numbers(0.0, 360.0),
            unit="deg",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("PHSE", then=float),
            set_cmd=cmd_prefix + " PHSE,{}",
        )

        self.add_parameter(
            "noise_std_dev",
            label="Standard deviation (Noise)",
            vals=Numbers(),
            unit="V",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("STDEV", then=_strip_unit("V", then=float)),
            set_cmd=cmd_prefix + " STDEV,{}",
        )

        self.add_parameter(
            "noise_mean",
            label="Mean (Noise)",
            vals=Numbers(),
            unit="V",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("MEAN", then=_strip_unit("V", then=float)),
            set_cmd=cmd_prefix + " MEAN,{}",
        )

        self.add_parameter(
            "pulse_width",
            label="Pulse width",
            vals=Numbers(min_value=0.0),
            unit="s",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("WIDTH", then=float),
            set_cmd=cmd_prefix + " WIDTH,{}",
        )

        self.add_parameter(
            "rise_time",
            label="Rise time (Pulse)",
            vals=Numbers(min_value=0.0),
            unit="s",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("RISE", then=_strip_unit("S", then=float)),
            set_cmd=cmd_prefix + " RISE,{}",
        )

        self.add_parameter(
            "fall_time",
            label="Rise time (Pulse)",
            vals=Numbers(min_value=0.0),
            unit="s",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("FALL", then=_strip_unit("S", then=float)),
            set_cmd=cmd_prefix + " FALL,{}",
        )

        self.add_parameter(
            "delay",
            label="Waveform delay",
            vals=Numbers(min_value=0.0),
            unit="s",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("DLY", then=_strip_unit("S", then=float)),
            set_cmd=cmd_prefix + " DLY,{}",
        )

        self.add_parameter(
            "high_level",
            label="High Level",
            vals=Numbers(range_offset[0], range_offset[1]),
            unit="V",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("HLEV", then=_strip_unit("V", then=float)),
            set_cmd=cmd_prefix + " HLEV,{}",
        )

        self.add_parameter(
            "low_level",
            label="Low Level",
            vals=Numbers(range_offset[0], range_offset[1]),
            unit="V",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("LLEV", then=_strip_unit("V", then=float)),
            set_cmd=cmd_prefix + " LLEV,{}",
        )

        self.add_parameter(
            "noise_bandwidth_enabled",
            label="Noise bandwidth enabled",
            val_mapping={
                False: "OFF",
                True: "ON",
                None: "",
            },
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("BANDSTATE", else_default=""),
            set_cmd=cmd_prefix + " BANDSTATE,{}",
        )

        self.add_parameter(
            "noise_bandwidth",
            label="Noise bandwidth",
            get_cmd=get_cmd,
            vals=Numbers(min_value=0),
            get_parser=extract_bswv_field(
                "BANDWIDTH", then=_strip_unit("HZ", then=float)
            ),
            set_cmd=cmd_prefix + " BANDWIDTH,{}",
            unit="Hz",
        )

        self.add_parameter(
            "prbs_length",
            label="PRBS length is 2^value - 1",
            vals=Ints(3, 32),
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("LENGTH", then=int),
            set_cmd=cmd_prefix + " LENGTH,{}",
        )

        self.add_parameter(
            "prbs_edge_time",
            label="PRBS rise/fall time",
            vals=Numbers(min_value=0),
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("EDGE", then=_strip_unit("S", then=float)),
            set_cmd=cmd_prefix + " EDGE,{}",
            unit="s",
        )

        self.add_parameter(
            "differential_mode",
            label="Channel differential output",
            val_mapping={
                False: "SINGLE",
                True: "DIFFERENTIAL",
            },
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("FORMAT", else_default="SINGLE"),
            set_cmd=cmd_prefix + " FORMAT,{}",
        )

        self.add_parameter(
            "prbs_differential_mode",
            label="PRBS differential mode",
            val_mapping={
                False: "OFF",
                True: "ON",
            },
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("DIFFSTATE"),
            set_cmd=cmd_prefix + " DIFFSTATE,{}",
        )

        self.add_parameter(
            "prbs_bit_rate",
            label="PRBS bit rate",
            vals=Numbers(min_value=0),
            get_cmd=get_cmd,
            get_parser=extract_bswv_field(
                "BITRATE", then=_strip_unit("bps", then=float)
            ),
            set_cmd=cmd_prefix + " BITRATE,{}",
            unit="bps",
        )

        self.add_parameter(
            "prbs_logic_level",
            label="PRBS Logic level",
            val_mapping={
                "ttl": "TTL_CMOS",
                "lvttl": "LVTTL_LVCMOS",
                "cmos": "TTL_CMOS",
                "lvcmos": "LVTTL_LVCMOS",
                "ecl": "ECL",
                "lvpecl": "LVPECL",
                "lvds": "LVDS",
                # "custom": "CUSTOM",
            },
            set_cmd=cmd_prefix + " LOGICLEVEL,{}",
            get_parser=extract_bswv_field("LOGICLEVEL"),
        )


class SiglentSDGx(SiglentSDx):
    def __init__(self, *args, **kwargs):
        n_channels = kwargs.pop("n_channels", None)
        channel_type = kwargs.pop("channel_type", SiglentSDGChannel)
        channel_kwargs = {}
        for ch_param in ("extra_outp_params", "extra_bswv_params"):
            if ch_param in kwargs:
                channel_kwargs[ch_param] = kwargs.pop(ch_param)

        self._ranges = kwargs.pop("ranges", {})

        super().__init__(*args, **kwargs)

        channels = ChannelList(self, "channel", SiglentSDGChannel, snapshotable=False)

        for channel_number in range(1, n_channels + 1):
            name = f"channel{channel_number}"
            channel = channel_type(self, name, channel_number, **channel_kwargs)
            self.add_submodule(name, channel)
            channels.append(channel)

        self.add_submodule("channel", channels)


class Siglent_SDG_60xx(SiglentSDGx):
    def __init__(self, *args, **kwargs):
        default_params = {
            "n_channels": 2,
            "extra_outp_params": {"POWERON_STATE"},
            "extra_bswv_params": {"MAX_OUTPUT_AMP"},
        }
        kwargs = ChainMap(kwargs, default_params)
        super().__init__(*args, **kwargs)


class Siglent_SDG_20xx(SiglentSDGx):
    def __init__(self, *args, **kwargs):
        default_params = {
            "n_channels": 2,
            "extra_bswv_params": {"MAX_OUTPUT_AMP"},
        }
        kwargs = ChainMap(kwargs, default_params)
        super().__init__(*args, **kwargs)


class Siglent_SDG_6022X(Siglent_SDG_60xx):
    def __init__(self, *args, **kwargs):
        ranges = {
            "frequency": (1e-3, 200e6),
            "vpp": (2e-3, 20.0),
            "vrms": (2e-3, 10.0),
            "offset": (-10, 10),
        }

        kwargs = ChainMap(kwargs, {"ranges": ranges})
        super().__init__(*args, **kwargs)


class Siglent_SDG_2042X(Siglent_SDG_20xx):
    def __init__(self, *args, **kwargs):
        ranges = {
            "frequency": (1e-3, 40e6),
            "vpp": (2e-3, 20.0),
            "vrms": (2e-3, 10.0),
            "offset": (-10, 10),
        }

        kwargs = ChainMap(kwargs, {"ranges": ranges})
        super().__init__(*args, **kwargs)
