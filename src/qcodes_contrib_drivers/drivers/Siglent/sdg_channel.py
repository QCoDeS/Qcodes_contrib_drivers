import functools
from functools import partial
from typing import Dict, Mapping, Optional, Set, Tuple, Union

from qcodes.parameters import Parameter
from qcodes.parameters import create_on_off_val_mapping as _create_on_off_val_mapping
from qcodes.validators.validators import Enum as EnumVals
from qcodes.validators.validators import Ints, MultiTypeOr, Numbers

from . import _sdg_response_fields as _fields
from .sdx import SiglentChannel, SiglentSDx

_substr_from = _fields.substr_from
_strip_unit = _fields.strip_unit
_merge_dicts = _fields.merge_dicts
_none_to_empty_str = _fields.none_to_empty_str

_on_off_val_mapping = _create_on_off_val_mapping(on_val="ON", off_val="OFF")


def _add_none_to_empty_val_mapping(*val_mappings: Dict) -> Dict:
    return _merge_dicts(*val_mappings, {None: ""})


class SiglentSDGChannel(SiglentChannel):
    def __init__(self, parent: SiglentSDx, name: str, channel_number: int, **kwargs):
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

        self._add_parameter_copy_function(
            channel_number=channel_number, n_channels=kwargs.get("n_channels", 2)
        )

        self._add_arbitrary_wave_parameters()

        self._add_sync_parameters(n_channels=kwargs.get("n_channels", 2))

        self._add_invert_parameter()

    # ---------------------------------------------------------------

    def _add_output_parameters(self, *, extra_params: Set[str]):
        ch_command = self._ch_num_prefix + "OUTP"
        set_cmd_ = ch_command + " "
        get_cmd = ch_command + "?"

        result_prefix_len = len(ch_command) + 1

        self.add_parameter(
            "_raw_outp",
            label="raw OUTPut command",
            set_cmd=set_cmd_ + "{}",
            get_cmd=get_cmd,
            get_parser=_substr_from(result_prefix_len),
        )

        extract_outp_field = functools.partial(
            _fields.extract_standalone_first_field_or_regular_field, result_prefix_len
        )

        self.add_parameter(
            "enabled",
            label="Enabled",
            val_mapping=_on_off_val_mapping,
            set_cmd=set_cmd_ + "{}",
            get_cmd=get_cmd,
            get_parser=extract_outp_field(None),
        )

        def _convert_load_value(value: str) -> Union[float, str]:
            if value == "HZ":
                return value
            try:
                return int(value)
            except ValueError:
                pass
            return value

        self.add_parameter(
            "load",
            label="Output load",
            unit="\N{OHM SIGN}",
            vals=MultiTypeOr(Ints(50, 100_000), EnumVals("HZ")),
            set_cmd=set_cmd_ + "LOAD,{}",
            get_cmd=get_cmd,
            get_parser=extract_outp_field("LOAD", then=_convert_load_value),
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
            "_raw_basic_wave",
            label="raw BaSic WaVe command",
            set_cmd=set_cmd_ + "{}",
            get_cmd=get_cmd,
            get_parser=_substr_from(result_prefix_len),
        )

        extract_bswv_field = functools.partial(
            _fields.extract_regular_field, result_prefix_len
        )

        _none_to_empty = _add_none_to_empty_val_mapping

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
            # get_parser=extract_bswv_field("AMPDBM", then=strip_unit("dBm", then=float)),  # noqa: E501
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
            val_mapping=_none_to_empty(_on_off_val_mapping),
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
            val_mapping=_on_off_val_mapping,
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
            val_mapping=_none_to_empty(
                {
                    "ttl": "TTL_CMOS",
                    "lvttl": "LVTTL_LVCMOS",
                    "cmos": "TTL_CMOS",
                    "lvcmos": "LVTTL_LVCMOS",
                    "ecl": "ECL",
                    "lvpecl": "LVPECL",
                    "lvds": "LVDS",
                    # "custom": "CUSTOM",
                }
            ),
            set_cmd=set_cmd_ + "LOGICLEVEL,{}",
            get_cmd=get_cmd,
            get_parser=extract_bswv_field("LOGICLEVEL", else_default=""),
        )

    # ---------------------------------------------------------------

    def _add_modulate_wave_parameters(self, *, extra_params: Set[str]):
        ch_command = self._ch_num_prefix + "MDWV"
        set_cmd_ = ch_command + " "
        get_cmd = ch_command + "?"

        result_prefix_len = len(ch_command) + 1

        self.add_parameter(
            "_raw_modulate_wave",
            label="raw MoDulate WaVe command",
            set_cmd=set_cmd_ + "{}",
            get_cmd=get_cmd,
            get_parser=_substr_from(result_prefix_len),
        )

        extract_mdwv_field = functools.partial(
            _fields.extract_first_state_field_or_any_group_prefixed_field,
            result_prefix_len,
        )

        _none_to_empty = _add_none_to_empty_val_mapping

        SRC_INT_EXT_VALS = _none_to_empty(
            {
                "internal": "INT",
                "external": "EXT",
            }
        )

        SRC_VALS = _merge_dicts(
            SRC_INT_EXT_VALS,
            {
                "channel1": "CH1",
                "channel2": "CH2",
            },
        )

        MDSP_VALS = _none_to_empty(
            {
                "sine": "SINE",
                "square": "SQUARE",
                "triangle": "TRIANGLE",
                "upramp": "UPRAMP",
                "downramp": "DNRAMP",
                "noise": "NOISE",
                "arb": "ARB",
            }
        )

        CARR_WVTP_VALS = _none_to_empty(
            {
                "sine": "SINE",
                "square": "SQUARE",
                "ramp": "RAMP",
                "arb": "ARB",
                "pulse": "PULSE",
            }
        )

        ranges: Mapping[str, Tuple[float, float]] = self._parent._ranges

        freq_ranges = ranges["frequency"]
        amp_range_vpp = ranges["vpp"]
        amp_range_vrms = ranges["vrms"]
        range_offset = ranges["offset"]

        # STATE

        self.add_parameter(
            "modulate_wave",
            label="Modulate wave",
            val_mapping=_on_off_val_mapping,
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
            label="Modulation carrier frequency",
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
            label="Modulation carrier phase",
            unit="\N{DEGREE SIGN}",
            vals=Numbers(0.0, 360.0),
            set_cmd=set_cmd_ + "CARR,PHSE,{}",
            get_cmd=get_cmd,
            get_parser=extract_mdwv_field("CARR,PHSE", then=float),
        )

        self.add_parameter(
            "mod_carrier_amplitude",
            label="Modulation carrier amplitude (Peak-to-peak)",
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
            label="Modulation carrier amplitude (RMS)",
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
            label="Modulation carrier offset",
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
            label="Modulation carrier symmetry (Ramp)",
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
            label="Modulation carrier duty cycle (Square/Pulse)",
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
                label="Modulation carrier rise time (Pulse)",
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
                label="Modulation carrier rise time (Pulse)",
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
                label="Modulation carrier carrier waveform delay (Pulse)",
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
            "_raw_sweep_wave",
            label="raw SWeep WaVe command",
            set_cmd=set_cmd_ + "{}",
            get_cmd=get_cmd,
            get_parser=_substr_from(result_prefix_len),
        )

        extract_swwv_field = functools.partial(
            _fields.extract_regular_field_before_group_or_group_prefixed_field,
            "CARR",
            result_prefix_len,
        )

        freq_ranges = ranges["frequency"]
        amp_range_vpp = ranges["vpp"]
        amp_range_vrms = ranges["vrms"]
        range_offset = ranges["offset"]

        _none_to_empty = _add_none_to_empty_val_mapping

        # STATE

        self.add_parameter(
            "sweep_wave",
            label="Sweep wave",
            val_mapping=_on_off_val_mapping,
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

        # the instrument does not allow setting the start value if it's above the stop value  # noqa: E501
        def _set_sweep_start_frequency_raw_(self: SiglentSDGChannel, value: float):
            stop_frequency_param: Parameter = self.sweep_stop_frequency
            stop_freq = stop_frequency_param.cache.get()
            if stop_freq is not None and stop_freq < value:
                stop_frequency_param.cache.invalidate()
                self.write_raw(set_cmd_ + f"STOP,{value:g}")
            self.write_raw(set_cmd_ + f"START,{value:g}")

        # the instrument does not allow setting the stop value if it's below the start value  # noqa: E501
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
            val_mapping=_none_to_empty(
                {
                    "linear": "LINE",
                    "logarithmic": "LOG",
                    "step": "STEP",
                }
            ),
            set_cmd=set_cmd_ + "SWMD,{}",
            get_cmd=get_cmd,
            get_parser=extract_swwv_field("SWMD", else_default=""),
        )

        # DIR

        self.add_parameter(
            "sweep_direction",
            label="Sweep direction",
            val_mapping=_none_to_empty(
                {
                    "up": "UP",
                    "down": "DOWN",
                    "up-down": "UP_DOWN",
                }
            ),
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
            val_mapping=_none_to_empty(
                {
                    "external": "EXT",
                    "internal": "INT",
                    "manual": "MAN",
                }
            ),
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
                val_mapping=_none_to_empty(_on_off_val_mapping),
                get_cmd=get_cmd,
                get_parser=extract_swwv_field("TRMD", else_default=""),
                set_cmd=set_cmd_ + "TRMD,{}",
            )

        if "EDGE" in extra_params:
            self.add_parameter(
                "sweep_trigger_edge",
                label="Sweep trigger edge",
                val_mapping=_none_to_empty(
                    {
                        "rise": "RISE",
                        "fall": "FALL",
                    }
                ),
                get_cmd=get_cmd,
                get_parser=extract_swwv_field("EDGE", else_default=""),
                set_cmd=set_cmd_ + "EDGE,{}",
            )

        # CARR

        CARR_WVTP_VALS = _none_to_empty(
            {
                "sine": "SINE",
                "square": "SQUARE",
                "ramp": "RAMP",
                "arb": "ARB",
            }
        )

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
            val_mapping=_none_to_empty(_on_off_val_mapping),
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
        _none_to_empty = _add_none_to_empty_val_mapping

        ch_command = self._ch_num_prefix + "BTWV"
        set_cmd_ = ch_command + " "
        get_cmd = ch_command + "?"

        result_prefix_len = len(ch_command) + 1

        extract_btwv_field = functools.partial(
            _fields.extract_regular_field_before_group_or_group_prefixed_field,
            "CARR",
            result_prefix_len,
        )

        ranges: Mapping[str, Tuple[int, int]] = self._parent._ranges

        self.add_parameter(
            "_raw_burst_wave",
            label="raw BursT WaVe command",
            set_cmd=set_cmd_ + "{}",
            get_cmd=get_cmd,
            get_parser=_substr_from(result_prefix_len),
        )

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
            val_mapping=_on_off_val_mapping,
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
            val_mapping=_none_to_empty(
                {
                    "gate": "GATE",
                    "ncyc": "NCYC",
                }
            ),
            set_cmd=set_cmd_ + "GATE_NCYC,{}",
            get_cmd=get_cmd,
            get_parser=extract_btwv_field("GATE_NCYC", else_default=""),
        )

        # TRSR

        self.add_parameter(
            "burst_trigger_source",
            label="Burst trigger source",
            val_mapping=_none_to_empty(
                {
                    "external": "EXT",
                    "internal": "INT",
                    "manual": "MAN",
                }
            ),
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
            val_mapping=_none_to_empty(
                {
                    "negative": "NEG",
                    "positive": "POS",
                }
            ),
            set_cmd=set_cmd_ + "PLRT,{}",
            get_cmd=get_cmd,
            get_parser=extract_btwv_field("PLRT", else_default=""),
        )

        if "TRMD" in extra_params:
            self.add_parameter(
                "burst_trigger_output_mode",
                label="(Burst) trigger output mode",
                val_mapping=_none_to_empty(
                    {
                        "rise": "RISE",
                        "fall": "FALL",
                        "off": "OFF",
                    }
                ),
                get_cmd=get_cmd,
                get_parser=extract_btwv_field("TRMD", else_default=""),
                set_cmd=set_cmd_ + "TRMD,{}",
            )

        if "EDGE" in extra_params:
            self.add_parameter(
                "burst_trigger_edge",
                label="Burst trigger edge",
                val_mapping=_none_to_empty(
                    {
                        "rise": "RISE",
                        "fall": "FALL",
                    }
                ),
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

        CARR_WVTP_VALS = _none_to_empty(
            {
                "sine": "SINE",
                "square": "SQUARE",
                "ramp": "RAMP",
                "arb": "ARB",
                "pulse": "PULSE",
                "noise": "NOISE",
            }
        )

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
            label="Burst carrier phase",
            unit="\N{DEGREE SIGN}",
            vals=Numbers(0.0, 360.0),
            set_cmd=set_cmd_ + "CARR,PHSE,{}",
            get_cmd=get_cmd,
            get_parser=extract_btwv_field("CARR,PHSE", then=float),
        )

        self.add_parameter(
            "burst_carrier_amplitude",
            label="Burst carrier amplitude (Peak-to-peak)",
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
            label="Burst carrier amplitude (RMS)",
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
            label="Burst carrier offset",
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
            label="Burst carrier symmetry (Ramp)",
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
            label="Burst carrier duty cycle (Square/Pulse)",
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
                label="Burst carrier rise time (Pulse)",
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
                label="Burst carrier rise time (Pulse)",
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
                label="Burst carrier waveform delay (Pulse)",
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
            label="Burst carrier standard deviation (Noise)",
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

    def _add_parameter_copy_function(
        self, *, channel_number: Optional[int], n_channels: Optional[int]
    ):
        if channel_number is None or n_channels is None or n_channels < 2:
            return

        other_channel_numbers = [
            ch for ch in range(1, 1 + n_channels) if ch != channel_number
        ]

        self.add_function(
            "copy_parameters_from_channel",
            call_cmd="PACP " + f"C{channel_number}" + ",C{:d}",
            args=[EnumVals(*other_channel_numbers)],
            docstring="""
                Copy parameters from other channel.

                Args:
                    channel: 
                        1-based index of source channel.
                        Must be different than current channel.
            """,
        )

    # ---------------------------------------------------------------

    def _add_arbitrary_wave_parameters(self):
        ch_command = self._ch_num_prefix + "ARWV"
        set_cmd_ = ch_command + " "
        get_cmd = ch_command + "?"

        result_prefix_len = len(ch_command) + 1

        ranges = self.parent._ranges

        arwv_ranges = ranges["arwv_index"]

        self.add_parameter(
            "_raw_arbitrary_wave",
            label="raw ARbitrary WaVe command",
            set_cmd=set_cmd_ + "{}",
            get_cmd=get_cmd,
            get_parser=_substr_from(result_prefix_len),
        )

        extract_arwv_field = functools.partial(
            _fields.extract_regular_field, result_prefix_len
        )

        self.add_parameter(
            "arbitrary_wave_index",
            label="Arbitrary wave index",
            set_cmd=set_cmd_ + "INDEX,{}",
            get_cmd=get_cmd,
            vals=Ints(arwv_ranges[0], arwv_ranges[1]),
            get_parser=extract_arwv_field("INDEX", then=int),
        )

        self.add_parameter(
            "arbitrary_wave_name",
            label="Arbitrary wave name",
            set_cmd=set_cmd_ + "NAME,{}",
            get_cmd=get_cmd,
            get_parser=extract_arwv_field("NAME"),
        )

    def _add_sync_parameters(self, *, n_channels):
        if n_channels < 2:
            return

        ch_command = self._ch_num_prefix + "SYNC"
        set_cmd_ = ch_command + " "
        get_cmd = ch_command + "?"

        result_prefix_len = len(ch_command) + 1

        # ranges = self.parent._ranges

        self.add_parameter(
            "_raw_sync",
            label="raw SYNC command",
            set_cmd=set_cmd_ + "{}",
            get_cmd=get_cmd,
            get_parser=_substr_from(result_prefix_len),
        )

        extract_sync_field = functools.partial(
            _fields.extract_standalone_first_field_or_regular_field, result_prefix_len
        )

        self.add_parameter(
            "sync_enabled",
            label="Sync enabled",
            set_cmd=set_cmd_ + " {}",
            get_cmd=get_cmd,
            val_mapping=_on_off_val_mapping,
            get_parser=extract_sync_field(None),
        )

        self.add_parameter(
            "sync_type",
            label="Sync type",
            set_cmd=set_cmd_ + "TYPE,{}",
            get_cmd=get_cmd,
            val_mapping={
                "channel1": "CH1",
                "channel2": "CH2",
                "mod-channel1": "MOD_CH1",
                "mod-channel2": "MOD_CH2",
            },
            get_parser=extract_sync_field("TYPE"),
        )

    def _add_invert_parameter(self):
        ch_command = self._ch_num_prefix + "INVT"
        set_cmd_ = ch_command + " "
        get_cmd = ch_command + "?"

        result_prefix_len = len(ch_command) + 1

        # ranges = self.parent._ranges

        self.add_parameter(
            "inverted",
            label="Inverted polarity",
            val_mapping=_on_off_val_mapping,
            set_cmd=set_cmd_ + "{}",
            get_cmd=get_cmd,
            get_parser=_substr_from(result_prefix_len),
        )
