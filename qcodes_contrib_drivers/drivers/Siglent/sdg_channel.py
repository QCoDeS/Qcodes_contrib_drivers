from collections import ChainMap
from enum import Enum
from functools import partial
from itertools import takewhile
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
)

from qcodes.instrument import InstrumentBase
from qcodes.parameters import Group, GroupParameter, Parameter
from qcodes.validators.validators import Enum as EnumVals
from qcodes.validators.validators import Ints, MultiTypeOr, Numbers

from .sdx import SiglentChannel, SiglentSDx


_T = TypeVar("_T")
_U = TypeVar("_U")


def _identity(x: _T) -> _T:
    return x


def _group_by_two(list_: Iterable[_T]) -> Iterator[Tuple[_T, _T]]:
    return zip(*2 * (iter(list_),))


def _iter_str_split(string: str, *, sep: str, start: int = 0) -> Iterator[str]:
    if slen := len(sep):
        last: int = start
        while (next := string.find(sep, last)) != -1:
            yield string[last:next]
            last = next + slen
        yield string[last:]
    else:
        yield from iter(string)


def _find_first_by_key(
    search_key: str,
    items: Iterator[Tuple[str, str]],
    *,
    transform_found: Callable[[str], Any] = _identity,
    not_found=None,
) -> Any:
    for k, value in items:
        if k == search_key:
            return transform_found(value)
    else:
        return not_found


def _none_to_empty_str(value):
    return "" if value is None else value


if False:

    def _collect_by_keys(
        search_keys: Tuple[str, ...],
        items: Iterator[Tuple[str, str]],
        *,
        defaults: dict[str, str],
    ) -> Iterator[Tuple[str, str]]:
        missing = set(defaults.keys())

        for key, value in items:
            if key in search_keys:
                missing.remove(key)
                yield (key, value)

        for key in missing:
            yield key, defaults[key]

    def _remap_keys(
        items: Iterator[Tuple[_T, _U]], *, using: Dict[_T, _T]
    ) -> Iterator[Tuple[_T, _U]]:
        for key, value in items:
            yield using.get(key, key), value

    def _if_not_empty(
        *, then: Callable[[str], Any], else_default: Any = None
    ) -> Callable[[Optional[str]], Any]:
        def result_func(response: Optional[str]) -> Any:
            if response is None or response == "":
                return else_default
            else:
                return then(response)

        return result_func

    def _float_to_str(value: float):
        result = f"{value:g}"
        return result


def _strip_unit(suffix: str, *, then: Callable[[str], Any]) -> Callable[[str], Any]:
    return lambda value: then(value.removesuffix(suffix))


def _merge_dicts(*dicts: dict) -> dict:
    dest = dict()
    for src in dicts:
        for k, v in src.items():
            dest[k] = v
    return dest


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

        self._add_modulate_wave_parameters(
            extra_params=kwargs.pop("extra_mdwv_params", set())
        )

        self._add_sweep_wave_parameters(
            extra_params=kwargs.pop("extra_swwv_params", set())
        )

        self._add_burst_wave_parameters(
            extra_params=kwargs.pop("extra_btwv_params", set())
        )

    # ---------------------------------------------------------------

    def _add_output_parameters(self, *, extra_params: Set[str]):

        ch_command = self._ch_num_prefix + "OUTP"
        set_cmd_ = ch_command + " "
        get_cmd = ch_command + "?"

        result_prefix_len = len(ch_command) + 1

        self.add_parameter(
            "raw_outp",
            label="raw OUTPut command",
            set_cmd=set_cmd_ + "{}",
            get_cmd=get_cmd,
            get_parser=lambda string: string[result_prefix_len:],
        )

        def extract_outp_field(name: Optional[str]) -> Callable[[str], Any]:
            def result_func(response: str):
                response_items = _iter_str_split(
                    response, start=result_prefix_len, sep=","
                )
                first = next(response_items)
                if name is None:
                    return first
                else:
                    return _find_first_by_key(
                        name,
                        _group_by_two(response_items),
                    )

            return result_func

        self.add_parameter(
            "enabled",
            label="Enabled",
            val_mapping={True: "ON", False: "OFF"},
            set_cmd=set_cmd_ + "{}",
            get_cmd=get_cmd,
            get_parser=extract_outp_field(None),
        )

        self.add_parameter(
            "load",
            label="Output load",
            unit="\N{OHM SIGN}",
            vals=MultiTypeOr(Numbers(50, 1e5), EnumVals("HZ")),
            set_cmd=set_cmd_ + "LOAD,{}",
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
                set_cmd=set_cmd_ + "POWERON_STATE,{}",
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
            set_cmd=set_cmd_ + "PLRT,{}",
            get_cmd=get_cmd,
            get_parser=extract_outp_field("PLRT"),
        )

    # ---------------------------------------------------------------

    def _add_basic_wave_parameters(self, *, extra_params: Set[str]):

        ch_command = self._ch_num_prefix + "BSWV"
        set_cmd_ = ch_command + " "
        get_cmd = ch_command + "?"

        result_prefix_len = len(ch_command) + 1

        self.add_parameter(
            "raw_basic_wave",
            label="raw BaSic WaVe command",
            set_cmd=set_cmd_ + "{}",
            get_cmd=get_cmd,
            get_parser=lambda string: string[result_prefix_len:],
        )

        def extract_bswv_field(
            name: str, *, then: Callable[[str], Any] = _identity, else_default=None
        ) -> Callable[[str], Any]:
            def result_func(response: str):
                return _find_first_by_key(
                    name,
                    _group_by_two(
                        _iter_str_split(response, start=result_prefix_len, sep=",")
                    ),
                    transform_found=then,
                    not_found=else_default,
                )

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
            set_cmd=set_cmd_ + "WVTP,{}",
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
            set_cmd=set_cmd_ + "FRQ,{}",
        )

        self.add_parameter(
            "period",
            label="Basic Wave Period",
            vals=Numbers(1 / freq_ranges[1], 1 / freq_ranges[0]),
            unit="s",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("PERI", then=_strip_unit("S", then=float)),
            set_cmd=set_cmd_ + "PERI,{}",
        )

        self.add_parameter(
            "amplitude",
            label="Basic Wave Amplitude (Peak-to-Peak)",
            vals=Numbers(amp_range_vpp[0], amp_range_vpp[1]),
            unit="V",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("AMP", then=_strip_unit("V", then=float)),
            set_cmd=set_cmd_ + "AMP,{}",
        )

        self.add_parameter(
            "amplitude_rms",
            label="Basic Wave Amplitude (RMS)",
            vals=Numbers(amp_range_vrms[0], amp_range_vrms[1]),
            unit="V",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("AMPRMS", then=_strip_unit("V", then=float)),
            set_cmd=set_cmd_ + "AMPRMS,{}",
        )

        # doesn't seem to work
        self.add_parameter(
            "amplitude_dbm",
            label="Basic Wave Amplitude (dBm)",
            vals=Numbers(),
            unit="dBm",
            # get_cmd=get_cmd,
            # get_parser=extract_bswv_field("AMPDBM", then=strip_unit("dBm", then=float)),
            set_cmd=set_cmd_ + "AMPDBM,{}",
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
                set_cmd=set_cmd_ + "MAX_OUTPUT_AMP,{}",
            )

        self.add_parameter(
            "offset",
            label="Offset",
            vals=Numbers(range_offset[0], range_offset[1]),
            unit="V",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("OFST", then=_strip_unit("V", then=float)),
            set_cmd=set_cmd_ + "OFST,{}",
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
            set_cmd=set_cmd_ + "COM_OFST,{}",
        )

        self.add_parameter(
            "ramp_symmetry",
            label="Ramp Symmetry",
            vals=Numbers(0.0, 100.0),
            unit="%",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("SYM", then=_strip_unit("%", then=float)),
            set_cmd=set_cmd_ + "SYM,{}",
        )

        self.add_parameter(
            "duty_cycle",
            label="Duty cycle (Square/Pulse)",
            vals=Numbers(0.0, 100.0),
            unit="%",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("DUTY", then=_strip_unit("%", then=float)),
            set_cmd=set_cmd_ + "DUTY,{}",
        )

        self.add_parameter(
            "phase",
            label="Phase",
            vals=Numbers(0.0, 360.0),
            unit="\N{DEGREE SIGN}",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("PHSE", then=float),
            set_cmd=set_cmd_ + "PHSE,{}",
        )

        self.add_parameter(
            "noise_std_dev",
            label="Standard deviation (Noise)",
            vals=Numbers(),
            unit="V",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("STDEV", then=_strip_unit("V", then=float)),
            set_cmd=set_cmd_ + "STDEV,{}",
        )

        self.add_parameter(
            "noise_mean",
            label="Mean (Noise)",
            vals=Numbers(),
            unit="V",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("MEAN", then=_strip_unit("V", then=float)),
            set_cmd=set_cmd_ + "MEAN,{}",
        )

        self.add_parameter(
            "pulse_width",
            label="Pulse width",
            vals=Numbers(min_value=0.0),
            unit="s",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("WIDTH", then=float),
            set_cmd=set_cmd_ + "WIDTH,{}",
        )

        self.add_parameter(
            "rise_time",
            label="Rise time (Pulse)",
            vals=Numbers(min_value=0.0),
            unit="s",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("RISE", then=_strip_unit("S", then=float)),
            set_cmd=set_cmd_ + "RISE,{}",
        )

        self.add_parameter(
            "fall_time",
            label="Rise time (Pulse)",
            vals=Numbers(min_value=0.0),
            unit="s",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("FALL", then=_strip_unit("S", then=float)),
            set_cmd=set_cmd_ + "FALL,{}",
        )

        self.add_parameter(
            "delay",
            label="Waveform delay",
            vals=Numbers(min_value=0.0),
            unit="s",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("DLY", then=_strip_unit("S", then=float)),
            set_cmd=set_cmd_ + "DLY,{}",
        )

        self.add_parameter(
            "high_level",
            label="High Level",
            vals=Numbers(range_offset[0], range_offset[1]),
            unit="V",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("HLEV", then=_strip_unit("V", then=float)),
            set_cmd=set_cmd_ + "HLEV,{}",
        )

        self.add_parameter(
            "low_level",
            label="Low Level",
            vals=Numbers(range_offset[0], range_offset[1]),
            unit="V",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("LLEV", then=_strip_unit("V", then=float)),
            set_cmd=set_cmd_ + "LLEV,{}",
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
            set_cmd=set_cmd_ + "BANDSTATE,{}",
        )

        self.add_parameter(
            "noise_bandwidth",
            label="Noise bandwidth",
            get_cmd=get_cmd,
            vals=Numbers(min_value=0),
            get_parser=extract_bswv_field(
                "BANDWIDTH", then=_strip_unit("HZ", then=float)
            ),
            set_cmd=set_cmd_ + "BANDWIDTH,{}",
            unit="Hz",
        )

        self.add_parameter(
            "prbs_length",
            label="PRBS length is 2^value - 1",
            vals=Ints(3, 32),
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("LENGTH", then=int),
            set_cmd=set_cmd_ + "LENGTH,{}",
        )

        self.add_parameter(
            "prbs_edge_time",
            label="PRBS rise/fall time",
            vals=Numbers(min_value=0),
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("EDGE", then=_strip_unit("S", then=float)),
            set_cmd=set_cmd_ + "EDGE,{}",
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
            set_cmd=set_cmd_ + "FORMAT,{}",
        )

        self.add_parameter(
            "prbs_differential_mode",
            label="PRBS differential mode",
            val_mapping={
                False: "OFF",
                True: "ON",
            },
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("DIFFSTATE", else_default="OFF"),
            set_cmd=set_cmd_ + "DIFFSTATE,{}",
        )

        self.add_parameter(
            "prbs_bit_rate",
            label="PRBS bit rate",
            vals=Numbers(min_value=0),
            get_cmd=get_cmd,
            get_parser=extract_bswv_field(
                "BITRATE", then=_strip_unit("bps", then=float)
            ),
            set_cmd=set_cmd_ + "BITRATE,{}",
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
            set_cmd=set_cmd_ + "LOGICLEVEL,{}",
            get_parser=extract_bswv_field("LOGICLEVEL"),
        )

    # ---------------------------------------------------------------

    def _add_modulate_wave_parameters(self, *, extra_params: Set[str]):

        ch_command = self._ch_num_prefix + "MDWV"
        set_cmd_ = ch_command + " "
        get_cmd = ch_command + "?"

        result_prefix_len = len(ch_command) + 1

        self.add_parameter(
            "raw_modulate_wave",
            label="raw MoDulate WaVe command",
            set_cmd=set_cmd_ + "{}",
            get_cmd=get_cmd,
            get_parser=lambda string: string[result_prefix_len:],
        )

        def extract_mdwv_field(
            name: str, *, then: Callable[[str], Any] = _identity, else_default=None
        ) -> Callable[[str], Any]:
            def result_func(response: str):
                response_items = _iter_str_split(
                    response, start=result_prefix_len, sep=","
                )

                try:
                    # STATE ON/OFF
                    state_key, state_value = next(response_items), next(response_items)
                except StopIteration:
                    return else_default

                if name == state_key:
                    return then(state_value)

                param_group, param_name = name.split(",")

                # <AM|FM|PM|PWM... etc> / <CARR>
                for group in response_items:
                    if group == param_group:
                        break
                else:
                    return else_default

                return _find_first_by_key(
                    param_name,
                    _group_by_two(response_items),
                    transform_found=then,
                    not_found=else_default,
                )

            return result_func

        SRC_INT_EXT_VALS = {
            None: "",
            "internal": "INT",
            "external": "EXT",
        }

        SRC_VALS = _merge_dicts(
            SRC_INT_EXT_VALS,
            {
                "channel1": "CH1",
                "channel2": "CH2",
            },
        )

        MDSP_VALS = {
            None: "",
            "sine": "SINE",
            "square": "SQUARE",
            "triangle": "TRIANGLE",
            "upramp": "UPRAMP",
            "downramp": "DNRAMP",
            "noise": "NOISE",
            "arb": "ARB",
        }

        CARR_WVTP_VALS = {
            None: "",
            "sine": "SINE",
            "square": "SQUARE",
            "ramp": "RAMP",
            "arb": "ARB",
            "pulse": "PULSE",
        }

        ranges: Mapping[str, Tuple[float, float]] = self._parent._ranges

        freq_ranges = ranges["frequency"]
        amp_range_vpp = ranges["vpp"]
        amp_range_vrms = ranges["vrms"]
        range_offset = ranges["offset"]

        # STATE

        self.add_parameter(
            "modulate_wave",
            label="Modulate wave",
            val_mapping={
                False: "OFF",
                True: "ON",
            },
            set_cmd=set_cmd_ + "STATE,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field("STATE"),
        )

        # AM

        self.add_parameter(
            "mod_am_src",
            label="AM signal source",
            val_mapping=SRC_VALS,
            set_cmd=set_cmd_ + "AM,SRC,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field("AM,SRC", else_default=""),
        )

        self.add_parameter(
            "mod_am_shape",
            label="AM signal modulation shape",
            val_mapping=MDSP_VALS,
            set_cmd=set_cmd_ + "AM,MDSP,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field("AM,MDSP", else_default=""),
        )

        self.add_parameter(
            "mod_am_frequency",
            label="AM signal modulation frequency",
            unit="Hz",
            vals=Numbers(min_value=0),
            set_cmd=set_cmd_ + "AM,FRQ,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field("AM,FRQ", then=_strip_unit("HZ", then=float)),
        )

        self.add_parameter(
            "mod_am_depth",
            label="AM signal modulation depth",
            vals=Numbers(0, 120),
            set_cmd=set_cmd_ + "AM,DEPTH,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field("AM,DEPTH", then=float),
        )

        # DSBAM

        self.add_parameter(
            "mod_dsb_am_src",
            label="DSB-AM signal source",
            val_mapping=SRC_INT_EXT_VALS,
            set_cmd=set_cmd_ + "DSBAM,SRC,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field("DSBAM,SRC", else_default=""),
        )

        self.add_parameter(
            "mod_dsb_am_shape",
            label="DSB-AM signal modulation shape",
            val_mapping=MDSP_VALS,
            set_cmd=set_cmd_ + "DSBAM,MDSP,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field("DSBAM,MDSP", else_default=""),
        )

        self.add_parameter(
            "mod_dsb_am_frequency",
            label="DSB-AM signal modulation frequency",
            unit="Hz",
            vals=Numbers(min_value=0),
            set_cmd=set_cmd_ + "DSBAM,FRQ,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field(
                "DSBAM,FRQ", then=_strip_unit("HZ", then=float)
            ),
        )

        if "DSBSC" in extra_params:
            self.add_parameter(
                "mod_dsb_sc_src",
                label="DSB-SC signal source",
                val_mapping=SRC_VALS,
                set_cmd=set_cmd_ + "DSBSC,SRC,{}",
                get_cmd=get_cmd,
                get_parser=extract_mdwv_field("DSBSC,SRC", else_default=""),
            )
            self.add_parameter(
                "mod_dsb_sc_shape",
                label="DSB-SC signal modulation shape",
                val_mapping=MDSP_VALS,
                set_cmd=set_cmd_ + "DSBSC,MDSP,{}",
                get_cmd=get_cmd,
                get_parser=extract_mdwv_field("DSBSC,MDSP", else_default=""),
            )
            self.add_parameter(
                "mod_dsb_sc_frequency",
                label="DSB-SC signal modulation frequency",
                unit="Hz",
                vals=Numbers(min_value=0),
                set_cmd=set_cmd_ + "DSBSC,FRQ,{}",
                get_cmd=get_cmd,
                get_parser=extract_mdwv_field(
                    "DSBSC,FRQ", then=_strip_unit("HZ", then=float)
                ),
            )

        # FM

        self.add_parameter(
            "mod_fm_src",
            label="FM signal source",
            val_mapping=SRC_VALS,
            set_cmd=set_cmd_ + "FM,SRC,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field("FM,SRC", else_default=""),
        )

        self.add_parameter(
            "mod_fm_shape",
            label="FM signal modulation shape",
            val_mapping=MDSP_VALS,
            set_cmd=set_cmd_ + "FM,MDSP,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field("FM,MDSP", else_default=""),
        )

        self.add_parameter(
            "mod_fm_frequency",
            label="FM signal modulation frequency",
            unit="Hz",
            vals=Numbers(min_value=0),
            set_cmd=set_cmd_ + "FM,FRQ,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field("FM,FRQ", then=_strip_unit("HZ", then=float)),
        )

        self.add_parameter(
            "mod_fm_deviation",
            label="FM signal frequency deviation",
            unit="Hz",
            vals=Numbers(min_value=0),
            set_cmd=set_cmd_ + "FM,DEVI,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field(
                "FM,DEVI", then=_strip_unit("HZ", then=float)
            ),
        )

        # PM

        self.add_parameter(
            "mod_pm_src",
            label="PM signal source",
            val_mapping=SRC_VALS,
            set_cmd=set_cmd_ + "PM,SRC,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field("PM,SRC", else_default=""),
        )

        self.add_parameter(
            "mod_pm_shape",
            label="PM signal modulation shape",
            val_mapping=MDSP_VALS,
            set_cmd=set_cmd_ + "PM,MDSP,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field("PM,MDSP", else_default=""),
        )

        self.add_parameter(
            "mod_pm_frequency",
            label="PM frequency",
            unit="Hz",
            vals=Numbers(min_value=0),
            set_cmd=set_cmd_ + "PM,FRQ,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field("PM,FRQ", then=_strip_unit("HZ", then=float)),
        )

        self.add_parameter(
            "mod_pm_deviation",
            label="PM phase deviation",
            unit="\N{DEGREE SIGN}",
            vals=Numbers(0.0, 360.0),
            set_cmd=set_cmd_ + "PM,DEPTH,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field("PM,DEPTH", then=float),
        )

        # PWM

        self.add_parameter(
            "mod_pwm_src",
            label="PWM signal source",
            val_mapping=SRC_VALS,
            set_cmd=set_cmd_ + "PWM,SRC,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field("PWM,SRC", else_default=""),
        )

        self.add_parameter(
            "mod_pwm_frequency",
            label="PWM signal modulation frequency",
            unit="Hz",
            vals=Numbers(min_value=0),
            set_cmd=set_cmd_ + "PWM,FRQ,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field(
                "PWM,FRQ", then=_strip_unit("HZ", then=float)
            ),
        )

        self.add_parameter(
            "mod_pwm_width_deviation",
            label="PWM width deviation",
            unit="s",
            vals=Numbers(min_value=0),
            set_cmd=set_cmd_ + "PWM,DEVI,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field(
                "PWM,DEVI", then=_strip_unit("S", then=float)
            ),
        )

        self.add_parameter(
            "mod_pwm_duty_cycle_deviation",
            label="PWM duty cycle deviation",
            unit="%",
            vals=Numbers(min_value=0),
            set_cmd=set_cmd_ + "PWM,DDEVI,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field("PWM,DDEVI", then=float),
        )

        self.add_parameter(
            "mod_pwm_shape",
            label="PWM signal modulation shape",
            val_mapping=MDSP_VALS,
            set_cmd=set_cmd_ + "PWM,MDSP,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field("PWM,MDSP", else_default=""),
        )

        # ASK

        self.add_parameter(
            "mod_ask_src",
            label="ASK signal source",
            val_mapping=SRC_INT_EXT_VALS,
            set_cmd=set_cmd_ + "ASK,SRC,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field("ASK,SRC", else_default=""),
        )

        self.add_parameter(
            "mod_ask_key_frequency",
            label="ASK key frequency",
            unit="Hz",
            vals=Numbers(min_value=0),
            set_cmd=set_cmd_ + "ASK,KFRQ,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field(
                "ASK,KFRQ", then=_strip_unit("HZ", then=float)
            ),
        )

        # FSK

        self.add_parameter(
            "mod_fsk_src",
            label="FSK signal source",
            val_mapping=SRC_INT_EXT_VALS,
            set_cmd=set_cmd_ + "FSK,SRC,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field("FSK,SRC", else_default=""),
        )

        self.add_parameter(
            "mod_fsk_key_frequency",
            label="FSK key frequency",
            unit="Hz",
            vals=Numbers(min_value=0),
            set_cmd=set_cmd_ + "FSK,KFRQ,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field(
                "FSK,KFRQ", then=_strip_unit("HZ", then=float)
            ),
        )

        self.add_parameter(
            "mod_fsk_hop_frequency",
            label="FSK hop frequency",
            unit="Hz",
            vals=Numbers(min_value=0),
            set_cmd=set_cmd_ + "FSK,HFRQ,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field(
                "FSK,HFRQ", then=_strip_unit("HZ", then=float)
            ),
        )

        # PSK

        self.add_parameter(
            "mod_psk_src",
            label="PSK signal source",
            val_mapping=SRC_INT_EXT_VALS,
            set_cmd=set_cmd_ + "PSK,SRC,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field("PSK,SRC", else_default=""),
        )

        self.add_parameter(
            "mod_psk_key_frequency",
            label="PSK key frequency",
            unit="Hz",
            vals=Numbers(min_value=0),
            set_cmd=set_cmd_ + "ASK,KFRQ,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field(
                "PSK,KFRQ", then=_strip_unit("HZ", then=float)
            ),
        )

        # CARR

        self.add_parameter(
            "mod_carrier_wave_type",
            label="Modulation carrier waveform type",
            val_mapping=CARR_WVTP_VALS,
            set_cmd=set_cmd_ + "CARR,WVTP,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field("CARR,WVTP", else_default=""),
        )

        self.add_parameter(
            "mod_carrier_frequency",
            label="Carrier frequency",
            unit="Hz",
            vals=Numbers(freq_ranges[0], freq_ranges[1]),
            set_cmd=set_cmd_ + "CARR,FRQ,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field(
                "CARR,FRQ", then=_strip_unit("HZ", then=float)
            ),
        )

        self.add_parameter(
            "mod_carrier_phase",
            label="Carrier phase",
            unit="\N{DEGREE SIGN}",
            vals=Numbers(0.0, 360.0),
            set_cmd=set_cmd_ + "CARR,PHSE,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field("CARR,PHSE", then=float),
        )

        self.add_parameter(
            "mod_carrier_amplitude",
            label="Carrier amplitude (Peak-to-peak)",
            vals=Numbers(amp_range_vpp[0], amp_range_vpp[1]),
            unit="V",
            set_cmd=set_cmd_ + "CARR,AMP,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field(
                "CARR,AMP", then=_strip_unit("V", then=float)
            ),
        )

        self.add_parameter(
            "mod_carrier_amplitude_rms",
            label="Carrier amplitude (RMS)",
            vals=Numbers(amp_range_vrms[0], amp_range_vrms[1]),
            unit="V",
            set_cmd=set_cmd_ + "CARR,AMPRMS,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field(
                "CARR,AMPRMS", then=_strip_unit("V", then=float)
            ),
        )

        self.add_parameter(
            "mod_carrier_offset",
            label="Carrier offset",
            vals=Numbers(range_offset[0], range_offset[1]),
            unit="V",
            set_cmd=set_cmd_ + "CARR,OFST,{}",
            get_parser=extract_mdwv_field(
                "CARR,OFST", then=_strip_unit("V", then=float)
            ),
            get_cmd=get_cmd,
        )

        self.add_parameter(
            "mod_carrier_ramp_symmetry",
            label="Carrier symmetry (Ramp)",
            vals=Numbers(0.0, 100.0),
            unit="%",
            set_cmd=set_cmd_ + "CARR,SYM,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field(
                "CARR,SYM", then=_strip_unit("%", then=float)
            ),
        )

        self.add_parameter(
            "mod_carrier_duty_cycle",
            label="Carrier duty cycle (Square/Pulse)",
            vals=Numbers(0.0, 100.0),
            unit="%",
            set_cmd=set_cmd_ + "CARR,DUTY,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field(
                "CARR,DUTY", then=_strip_unit("%", then=float)
            ),
        )

        if "CARR,RISE" in extra_params:
            self.add_parameter(
                "mod_carrier_rise_time",
                label="Carrier rise time (Pulse)",
                vals=Numbers(min_value=0.0),
                unit="s",
                set_cmd=set_cmd_ + "CARR,RISE,{}",
                get_cmd=get_cmd,
                get_parser=extract_mdwv_field(
                    "CARR,RISE", then=_strip_unit("S", then=float)
                ),
            )

        if "CARR,FALL" in extra_params:
            self.add_parameter(
                "mod_carrier_fall_time",
                label="Carrier rise time (Pulse)",
                vals=Numbers(min_value=0.0),
                unit="s",
                get_cmd=get_cmd,
                get_parser=extract_mdwv_field(
                    "CARR,FALL", then=_strip_unit("S", then=float)
                ),
                set_cmd=set_cmd_ + "CARR,FALL,{}",
            )

        if "CARR,DLY" in extra_params:
            self.add_parameter(
                "mod_carrier_delay",
                label="Carrier waveform delay (Pulse)",
                vals=Numbers(min_value=0.0),
                unit="s",
                get_cmd=get_cmd,
                set_cmd=set_cmd_ + "CARR,DLY,{}",
                get_parser=extract_mdwv_field(
                    "CARR,DLY", then=_strip_unit("S", then=float)
                ),
            )

    # ---------------------------------------------------------------

    def _add_sweep_wave_parameters(self, *, extra_params: Set[str]):

        ch_command = self._ch_num_prefix + "SWWV"
        set_cmd_ = ch_command + " "
        get_cmd = ch_command + "?"

        result_prefix_len = len(ch_command) + 1

        ranges: Mapping[str, Tuple[float, float]] = self._parent._ranges

        self.add_parameter(
            "raw_sweep_wave",
            label="raw SWeep WaVe command",
            set_cmd=set_cmd_ + "{}",
            get_cmd=get_cmd,
            get_parser=lambda string: string[result_prefix_len:],
        )

        def extract_swwv_field(
            name: str, *, then: Callable[[str], Any] = _identity, else_default=None
        ) -> Callable[[str], Any]:

            if not name.startswith("CARR,"):

                def result_func(response: str):
                    items = takewhile(
                        lambda str: str != "CARR",
                        _iter_str_split(response, start=result_prefix_len, sep=","),
                    )
                    return _find_first_by_key(
                        name,
                        _group_by_two(items),
                        transform_found=then,
                        not_found=else_default,
                    )

            else:
                name = name[5:]

                def result_func(response: str):
                    items = _iter_str_split(response, start=result_prefix_len, sep=",")

                    for item in items:
                        if item == "CARR":
                            break
                    else:
                        return else_default

                    return _find_first_by_key(
                        name,
                        _group_by_two(items),
                        transform_found=then,
                        not_found=else_default,
                    )

            return result_func

        if False:

            def extract_swwv_non_carr_fields(
                field_names: Tuple[str, ...],
                *,
                field_defaults: Dict[str, Any],
                remap_field_to_param: Dict[str, str],
            ) -> Callable[[str], Dict[str, Any]]:
                def result_func(response: str):
                    non_carr_items = _group_by_two(
                        takewhile(
                            lambda str: str != "CARR",
                            _iter_str_split(response, start=result_prefix_len, sep=","),
                        )
                    )
                    items = _collect_by_keys(
                        field_names, non_carr_items, defaults=field_defaults
                    )

                    return dict(_remap_keys(items, using=remap_field_to_param))

                return result_func

        freq_ranges = ranges["frequency"]
        amp_range_vpp = ranges["vpp"]
        amp_range_vrms = ranges["vrms"]
        range_offset = ranges["offset"]

        # STATE

        self.add_parameter(
            "sweep_wave",
            label="Sweep wave",
            val_mapping={
                False: "OFF",
                True: "ON",
            },
            set_cmd=set_cmd_ + "STATE,{}",
            get_cmd=get_cmd,
            get_parser=extract_swwv_field("STATE"),
        )

        # TIME
        self.add_parameter(
            "sweep_time",
            label="Sweep time",
            unit="s",
            vals=Numbers(
                0,
            ),
            set_cmd=set_cmd_ + "TIME,{}",
            get_cmd=get_cmd,
            get_parser=extract_swwv_field("TIME", then=_strip_unit("S", then=float)),
        )

        if "STARTTIME" in extra_params or True:
            self.add_parameter(
                "sweep_start_hold_time",
                label="Sweep start hold time",
                unit="s",
                vals=Numbers(0, 300),
                set_cmd=set_cmd_ + "STARTTIME,{}",
                get_cmd=get_cmd,
                get_parser=extract_swwv_field(
                    "STARTTIME", then=_strip_unit("S", then=float)
                ),
            )

        if "ENDTIME" in extra_params or True:
            self.add_parameter(
                "sweep_end_hold_time",
                label="Sweep end hold time",
                unit="s",
                vals=Numbers(0, 300),
                set_cmd=set_cmd_ + "ENDTIME,{}",
                get_cmd=get_cmd,
                get_parser=extract_swwv_field(
                    "ENDTIME", then=_strip_unit("S", then=float)
                ),
            )

        if "BACKTIME" in extra_params or True:
            self.add_parameter(
                "sweep_back_time",
                label="Sweep back time",
                unit="s",
                vals=Numbers(0, 300),
                set_cmd=set_cmd_ + "BACKTIME,{}",
                get_cmd=get_cmd,
                get_parser=extract_swwv_field(
                    "BACKTIME", then=_strip_unit("S", then=float)
                ),
            )

        # START, STOP

        # the instrument does not allow setting the start value if it's above the stop value
        def _set_sweep_start_frequency_raw_(self: SiglentSDGChannel, value: float):
            stop_frequency_param: Parameter = self.sweep_stop_frequency
            stop_freq = stop_frequency_param.cache.get()
            if stop_freq is not None and stop_freq < value:
                stop_frequency_param.cache.invalidate()
                self.write_raw(set_cmd_ + f"STOP,{value:g}")
            self.write_raw(set_cmd_ + f"START,{value:g}")

        # the instrument does not allow setting the stop value if it's below the start value
        def _set_sweep_stop_frequency_raw_(self: SiglentSDGChannel, value: float):
            start_frequency_param: Parameter = self.sweep_start_frequency
            start_freq = start_frequency_param.cache.get()
            if start_freq is not None and start_freq > value:
                start_frequency_param.cache.invalidate()
                self.write_raw(set_cmd_ + f"START,{value:g}")
            self.write_raw(set_cmd_ + f"STOP,{value:g}")

        self.add_parameter(
            "sweep_start_frequency",
            label="Sweep start frequency",
            vals=Numbers(freq_ranges[0], freq_ranges[1]),
            unit="Hz",
            set_cmd=partial(_set_sweep_start_frequency_raw_, self),
            get_cmd=get_cmd,
            get_parser=extract_swwv_field("START", then=_strip_unit("HZ", then=float)),
        )

        self.add_parameter(
            "sweep_stop_frequency",
            label="Sweep stop frequency",
            vals=Numbers(freq_ranges[0], freq_ranges[1]),
            unit="Hz",
            set_cmd=partial(_set_sweep_stop_frequency_raw_, self),
            get_cmd=get_cmd,
            get_parser=extract_swwv_field("STOP", then=_strip_unit("HZ", then=float)),
        )

        if "CENTER" in extra_params or True:
            self.add_parameter(
                "sweep_center_frequency",
                label="Sweep center frequency",
                vals=Numbers(freq_ranges[0], freq_ranges[1]),
                unit="Hz",
                set_cmd=set_cmd_ + "CENTER,{}",
                get_cmd=get_cmd,
                get_parser=extract_swwv_field(
                    "CENTER", then=_strip_unit("HZ", then=float)
                ),
            )

        if "SPAN" in extra_params or True:
            self.add_parameter(
                "sweep_frequency_span",
                label="Sweep frequency span",
                vals=Numbers(0, abs(freq_ranges[1] - freq_ranges[0])),
                unit="Hz",
                set_cmd=set_cmd_ + "SPAN,{}",
                get_cmd=get_cmd,
                get_parser=extract_swwv_field(
                    "SPAN", then=_strip_unit("HZ", then=float)
                ),
            )

        # SWMD

        self.add_parameter(
            "sweep_mode",
            label="Sweep mode",
            val_mapping={
                None: "",
                "linear": "LINE",
                "logarithmic": "LOG",
                "step": "STEP",
            },
            set_cmd=set_cmd_ + "SWMD,{}",
            get_cmd=get_cmd,
            get_parser=extract_swwv_field("SWMD", else_default=""),
        )

        # DIR

        self.add_parameter(
            "sweep_direction",
            label="Sweep direction",
            val_mapping={
                None: "",
                "up": "UP",
                "down": "DOWN",
                "up-down": "UP_DOWN",
            },
            get_cmd=get_cmd,
            get_parser=extract_swwv_field("DIR", else_default=""),
            set_cmd=set_cmd_ + "DIR,{}",
        )

        # SYM

        self.add_parameter(
            "sweep_symmetry",
            label="Sweep (up-down) symmetry",
            vals=Numbers(0.0, 100.0),
            unit="%",
            get_cmd=get_cmd,
            get_parser=extract_swwv_field("SYM", then=_strip_unit("%", then=float)),
            set_cmd=set_cmd_ + "SYM,{}",
        )

        # TRSR

        self.add_parameter(
            "sweep_trigger_source",
            label="Sweep trigger source",
            val_mapping={
                None: "",
                "external": "EXT",
                "internal": "INT",
                "manual": "MAN",
            },
            get_cmd=get_cmd,
            get_parser=extract_swwv_field("TRSR", else_default=""),
            set_cmd=set_cmd_ + "TRSR,{}",
        )

        # MTRIG

        self.add_function(
            "sweep_trigger",
            call_cmd=set_cmd_ + "MTRIG",
        )

        if "TRMD" in extra_params:
            self.add_parameter(
                "sweep_trigger_output",
                label="(Sweep) state of trigger output",
                val_mapping={
                    None: "",
                    True: "ON",
                    False: "OFF",
                },
                get_cmd=get_cmd,
                get_parser=extract_swwv_field("TRMD", else_default=""),
                set_cmd=set_cmd_ + "TRMD,{}",
            )

        if "EDGE" in extra_params:

            self.add_parameter(
                "sweep_trigger_edge",
                label="Sweep trigger edge",
                val_mapping={
                    None: "",
                    "rise": "RISE",
                    "fall": "FALL",
                },
                get_cmd=get_cmd,
                get_parser=extract_swwv_field("EDGE", else_default=""),
                set_cmd=set_cmd_ + "EDGE,{}",
            )

        # CARR

        CARR_WVTP_VALS = {
            None: "",
            "sine": "SINE",
            "square": "SQUARE",
            "ramp": "RAMP",
            "arb": "ARB",
        }

        # CARR

        self.add_parameter(
            "sweep_carrier_wave_type",
            label="Modulation carrier waveform type",
            val_mapping=CARR_WVTP_VALS,
            set_cmd=set_cmd_ + "CARR,WVTP,{}",
            get_cmd=get_cmd,
            get_parser=extract_swwv_field("CARR,WVTP", else_default=""),
        )

        self.add_parameter(
            "sweep_carrier_frequency",
            label="Sweep carrier frequency",
            unit="Hz",
            vals=Numbers(freq_ranges[0], freq_ranges[1]),
            set_cmd=set_cmd_ + "CARR,FRQ,{}",
            get_cmd=get_cmd,
            get_parser=extract_swwv_field(
                "CARR,FRQ", then=_strip_unit("HZ", then=float)
            ),
        )

        self.add_parameter(
            "sweep_carrier_phase",
            label="Sweep carrier phase",
            unit="\N{DEGREE SIGN}",
            vals=Numbers(0.0, 360.0),
            set_cmd=set_cmd_ + "CARR,PHSE,{}",
            get_cmd=get_cmd,
            get_parser=extract_swwv_field("CARR,PHSE", then=float),
        )

        self.add_parameter(
            "sweep_carrier_amplitude",
            label="Sweep carrier amplitude (Peak-to-peak)",
            vals=Numbers(amp_range_vpp[0], amp_range_vpp[1]),
            unit="V",
            set_cmd=set_cmd_ + "CARR,AMP,{}",
            get_cmd=get_cmd,
            get_parser=extract_swwv_field(
                "CARR,AMP", then=_strip_unit("V", then=float)
            ),
        )

        self.add_parameter(
            "sweep_carrier_amplitude_rms",
            label="Sweep carrier amplitude (RMS)",
            vals=Numbers(amp_range_vrms[0], amp_range_vrms[1]),
            unit="V",
            set_cmd=set_cmd_ + "CARR,AMPRMS,{}",
            get_cmd=get_cmd,
            get_parser=extract_swwv_field(
                "CARR,AMPRMS", then=_strip_unit("V", then=float)
            ),
        )

        self.add_parameter(
            "sweep_carrier_offset",
            label="Sweep carrier offset",
            vals=Numbers(range_offset[0], range_offset[1]),
            unit="V",
            set_cmd=set_cmd_ + "CARR,OFST,{}",
            get_parser=extract_swwv_field(
                "CARR,OFST", then=_strip_unit("V", then=float)
            ),
            get_cmd=get_cmd,
        )

        self.add_parameter(
            "sweep_carrier_ramp_symmetry",
            label="Sweep carrier symmetry (Ramp)",
            vals=Numbers(0.0, 100.0),
            unit="%",
            set_cmd=set_cmd_ + "CARR,SYM,{}",
            get_cmd=get_cmd,
            get_parser=extract_swwv_field(
                "CARR,SYM", then=_strip_unit("%", then=float)
            ),
        )

        self.add_parameter(
            "sweep_carrier_duty_cycle",
            label="Sweep carrier duty cycle (Square)",
            vals=Numbers(0.0, 100.0),
            unit="%",
            set_cmd=set_cmd_ + "CARR,DUTY,{}",
            get_cmd=get_cmd,
            get_parser=extract_swwv_field(
                "CARR,DUTY", then=_strip_unit("%", then=float)
            ),
        )

        self.add_parameter(
            "sweep_mark",
            label="Sweep Mark (on/off)",
            val_mapping={
                None: "",
                False: "OFF",
                True: "ON",
            },
            set_cmd=set_cmd_ + "MARK_STATE,{}",
            get_cmd=get_cmd,
            get_parser=extract_swwv_field("MARK_STATE", else_default=""),
        )

        self.add_parameter(
            "sweep_mark_frequency",
            label="Sweep mark frequency",
            unit="Hz",
            vals=Numbers(freq_ranges[0], freq_ranges[1]),
            set_cmd=set_cmd_ + "MARK_FREQ,{}",
            get_cmd=get_cmd,
            get_parser=extract_swwv_field(
                "MARK_FREQ", then=_strip_unit("HZ", then=float)
            ),
        )

    # ---------------------------------------------------------------

    def _add_burst_wave_parameters(self, *, extra_params: Set[str]):

        ch_command = self._ch_num_prefix + "BTWV"
        set_cmd_ = ch_command + " "
        get_cmd = ch_command + "?"

        result_prefix_len = len(ch_command) + 1

        ranges: Mapping[str, Tuple[float, float]] = self._parent._ranges

        self.add_parameter(
            "raw_burst_wave",
            label="raw BursT WaVe command",
            set_cmd=set_cmd_ + "{}",
            get_cmd=get_cmd,
            get_parser=lambda string: string[result_prefix_len:],
        )

        def extract_btwv_field(
            name: str, *, then: Callable[[str], Any] = _identity, else_default=None
        ) -> Callable[[str], Any]:

            if not name.startswith("CARR,"):

                def result_func(response: str):
                    items = takewhile(
                        lambda str: str != "CARR",
                        _iter_str_split(response, start=result_prefix_len, sep=","),
                    )
                    return _find_first_by_key(
                        name,
                        _group_by_two(items),
                        transform_found=then,
                        not_found=else_default,
                    )

            else:
                name = name[5:]

                def result_func(response: str):
                    items = _iter_str_split(response, start=result_prefix_len, sep=",")
                    for item in items:
                        if item == "CARR":
                            break
                    else:
                        return else_default
                    return _find_first_by_key(
                        name,
                        _group_by_two(items),
                        transform_found=then,
                        not_found=else_default,
                    )

            return result_func

        freq_ranges = ranges["frequency"]
        amp_range_vpp = ranges["vpp"]
        amp_range_vrms = ranges["vrms"]
        range_offset = ranges["offset"]

        burst_period_range = ranges["burst_period"]
        burst_phase_range = ranges.get("burst_phase", (0.0, 360.0))
        burst_ncycle_range = ranges["burst_ncycles"]

        burst_trigger_delay_range = ranges["burst_trigger_delay"]

        # STATE

        self.add_parameter(
            "burst_wave",
            label="Burst wave",
            val_mapping={
                False: "OFF",
                True: "ON",
            },
            set_cmd=set_cmd_ + "STATE,{}",
            get_cmd=get_cmd,
            get_parser=extract_btwv_field("STATE"),
        )

        # PRD

        self.add_parameter(
            "burst_period",
            label="Burst period",
            unit="s",
            vals=Numbers(burst_period_range[0], burst_period_range[1]),
            set_cmd=set_cmd_ + "PRD,{}",
            get_cmd=get_cmd,
            get_parser=extract_btwv_field("PRD", then=_strip_unit("S", then=float)),
        )

        # STPS

        self.add_parameter(
            "burst_start_phase",
            label="Burst start phase",
            unit="\N{DEGREE SIGN}",
            vals=Numbers(burst_phase_range[0], burst_phase_range[1]),
            set_cmd=set_cmd_ + "STPS,{}",
            get_cmd=get_cmd,
            get_parser=extract_btwv_field("STPS", then=float),
        )

        # GATE_NCYC

        self.add_parameter(
            "burst_mode",
            label="Burst mode",
            val_mapping={
                None: "",
                "gate": "GATE",
                "ncyc": "NCYC",
            },
            set_cmd=set_cmd_ + "GATE_NCYC,{}",
            get_cmd=get_cmd,
            get_parser=extract_btwv_field("GATE_NCYC", else_default=""),
        )

        # TRSR

        self.add_parameter(
            "burst_trigger_source",
            label="Burst trigger source",
            val_mapping={
                None: "",
                "external": "EXT",
                "internal": "INT",
                "manual": "MAN",
            },
            get_cmd=get_cmd,
            get_parser=extract_btwv_field("TRSR", else_default=""),
            set_cmd=set_cmd_ + "TRSR,{}",
        )

        # MTRIG

        self.add_function(
            "burst_trigger",
            call_cmd=set_cmd_ + "MTRIG",
        )

        self.add_parameter(
            "burst_trigger_delay",
            label="Burst trigger delay",
            unit="s",
            vals=Numbers(burst_trigger_delay_range[0], burst_trigger_delay_range[1]),
            set_cmd=set_cmd_ + "DLAY,{}",
            get_cmd=get_cmd,
            get_parser=extract_btwv_field("DLAY", then=_strip_unit("S", then=float)),
        )

        self.add_parameter(
            "burst_gate_polarity",
            label="Burst gate polarity",
            val_mapping={
                None: "",
                "negative": "NEG",
                "positive": "POS",
            },
            set_cmd=set_cmd_ + "PLRT,{}",
            get_cmd=get_cmd,
            get_parser=extract_btwv_field("PLRT", else_default=""),
        )

        if "TRMD" in extra_params:
            self.add_parameter(
                "burst_trigger_output_mode",
                label="(Burst) trigger output mode",
                val_mapping={
                    None: "",
                    "rise": "RISE",
                    "fall": "FALL",
                    "off": "OFF",
                },
                get_cmd=get_cmd,
                get_parser=extract_btwv_field("TRMD", else_default=""),
                set_cmd=set_cmd_ + "TRMD,{}",
            )

        if "EDGE" in extra_params:

            self.add_parameter(
                "burst_trigger_edge",
                label="Burst trigger edge",
                val_mapping={
                    None: "",
                    "rise": "RISE",
                    "fall": "FALL",
                },
                get_cmd=get_cmd,
                get_parser=extract_btwv_field("EDGE", else_default=""),
                set_cmd=set_cmd_ + "EDGE,{}",
            )

        # TIME

        self.add_parameter(
            "burst_ncycles",
            label="Burst cycles",
            vals=MultiTypeOr(
                Ints(burst_ncycle_range[0], burst_ncycle_range[1]),
                EnumVals("INF", None),
            ),
            set_parser=_none_to_empty_str,
            set_cmd=set_cmd_ + "TIME,{}",
            get_cmd=get_cmd,
            get_parser=extract_btwv_field("TIME", then=int, else_default=None),
        )

        if "COUNTER" in extra_params:
            self.add_parameter(
                "burst_counter",
                label="Burst counter",
                vals=Ints(min_value=1),
                set_parser=_none_to_empty_str,
                set_cmd=set_cmd_ + "COUNTER,{}",
                get_cmd=get_cmd,
                get_parser=extract_btwv_field("COUNTER", then=int, else_default=None),
            )

        # CARR

        CARR_WVTP_VALS = {
            None: "",
            "sine": "SINE",
            "square": "SQUARE",
            "ramp": "RAMP",
            "arb": "ARB",
            "pulse": "PULSE",
            "noise": "NOISE",
        }

        self.add_parameter(
            "burst_carrier_wave_type",
            label="Burst carrier waveform type",
            val_mapping=CARR_WVTP_VALS,
            set_cmd=set_cmd_ + "CARR,WVTP,{}",
            get_cmd=get_cmd,
            get_parser=extract_btwv_field("CARR,WVTP", else_default=""),
        )

        self.add_parameter(
            "burst_carrier_frequency",
            label="Burst carrier frequency",
            unit="Hz",
            vals=Numbers(freq_ranges[0], freq_ranges[1]),
            set_cmd=set_cmd_ + "CARR,FRQ,{}",
            get_cmd=get_cmd,
            get_parser=extract_btwv_field(
                "CARR,FRQ", then=_strip_unit("HZ", then=float)
            ),
        )

        self.add_parameter(
            "burst_carrier_phase",
            label="Carrier phase",
            unit="\N{DEGREE SIGN}",
            vals=Numbers(0.0, 360.0),
            set_cmd=set_cmd_ + "CARR,PHSE,{}",
            get_cmd=get_cmd,
            get_parser=extract_btwv_field("CARR,PHSE", then=float),
        )

        self.add_parameter(
            "burst_carrier_amplitude",
            label="Carrier amplitude (Peak-to-peak)",
            vals=Numbers(amp_range_vpp[0], amp_range_vpp[1]),
            unit="V",
            set_cmd=set_cmd_ + "CARR,AMP,{}",
            get_cmd=get_cmd,
            get_parser=extract_btwv_field(
                "CARR,AMP", then=_strip_unit("V", then=float)
            ),
        )

        self.add_parameter(
            "burst_carrier_amplitude_rms",
            label="Carrier amplitude (RMS)",
            vals=Numbers(amp_range_vrms[0], amp_range_vrms[1]),
            unit="V",
            set_cmd=set_cmd_ + "CARR,AMPRMS,{}",
            get_cmd=get_cmd,
            get_parser=extract_btwv_field(
                "CARR,AMPRMS", then=_strip_unit("V", then=float)
            ),
        )

        self.add_parameter(
            "burst_carrier_offset",
            label="Carrier offset",
            vals=Numbers(range_offset[0], range_offset[1]),
            unit="V",
            set_cmd=set_cmd_ + "CARR,OFST,{}",
            get_parser=extract_btwv_field(
                "CARR,OFST", then=_strip_unit("V", then=float)
            ),
            get_cmd=get_cmd,
        )

        self.add_parameter(
            "burst_carrier_ramp_symmetry",
            label="Carrier symmetry (Ramp)",
            vals=Numbers(0.0, 100.0),
            unit="%",
            set_cmd=set_cmd_ + "CARR,SYM,{}",
            get_cmd=get_cmd,
            get_parser=extract_btwv_field(
                "CARR,SYM", then=_strip_unit("%", then=float)
            ),
        )

        self.add_parameter(
            "burst_carrier_duty_cycle",
            label="Carrier duty cycle (Square/Pulse)",
            vals=Numbers(0.0, 100.0),
            unit="%",
            set_cmd=set_cmd_ + "CARR,DUTY,{}",
            get_cmd=get_cmd,
            get_parser=extract_btwv_field(
                "CARR,DUTY", then=_strip_unit("%", then=float)
            ),
        )

        if "CARR,RISE" in extra_params:
            self.add_parameter(
                "burst_carrier_rise_time",
                label="Carrier rise time (Pulse)",
                vals=Numbers(min_value=0.0),
                unit="s",
                set_cmd=set_cmd_ + "CARR,RISE,{}",
                get_cmd=get_cmd,
                get_parser=extract_btwv_field(
                    "CARR,RISE", then=_strip_unit("S", then=float)
                ),
            )

        if "CARR,FALL" in extra_params:
            self.add_parameter(
                "burst_carrier_fall_time",
                label="Carrier rise time (Pulse)",
                vals=Numbers(min_value=0.0),
                unit="s",
                get_cmd=get_cmd,
                get_parser=extract_btwv_field(
                    "CARR,FALL", then=_strip_unit("S", then=float)
                ),
                set_cmd=set_cmd_ + "CARR,FALL,{}",
            )

        if "CARR,DLY" in extra_params:
            self.add_parameter(
                "burst_carrier_delay",
                label="Carrier waveform delay (Pulse)",
                vals=Numbers(min_value=0.0),
                unit="s",
                get_cmd=get_cmd,
                set_cmd=set_cmd_ + "CARR,DLY,{}",
                get_parser=extract_btwv_field(
                    "CARR,DLY", then=_strip_unit("S", then=float)
                ),
            )

        self.add_parameter(
            "burst_carrier_noise_std_dev",
            label="Burst Carrier Standard deviation (Noise)",
            vals=Numbers(),
            unit="V",
            get_cmd=get_cmd,
            get_parser=extract_btwv_field(
                "CARR,STDEV", then=_strip_unit("V", then=float)
            ),
            set_cmd=set_cmd_ + "CARR,STDEV,{}",
        )

        self.add_parameter(
            "burst_carrier_noise_mean",
            label="Burst carrier mean (Noise)",
            vals=Numbers(),
            unit="V",
            get_cmd=get_cmd,
            get_parser=extract_btwv_field(
                "CARR,MEAN", then=_strip_unit("V", then=float)
            ),
            set_cmd=set_cmd_ + "CARR,MEAN,{}",
        )

    # ---------------------------------------------------------------
