"""Driver for Yokogawa AQ637x Optical Spectrum Analyzers.

Provides instrument-level driver, trace/channel abstraction and data retrieval helpers.
"""

import logging
from typing import TYPE_CHECKING, cast

import numpy as np
from qcodes.instrument import (
    ChannelTuple,
    Instrument,
    InstrumentBaseKWArgs,
    InstrumentChannel,
    VisaInstrument,
    VisaInstrumentKWArgs,
)
from qcodes.parameters import (
    Parameter,
    ParameterWithSetpoints,
    create_on_off_val_mapping,
    ParamRawDataType,
)
from qcodes.validators import Arrays, Enum, Ints, Strings

if TYPE_CHECKING:
    from typing_extensions import Unpack
    from qcodes.parameters import ParameterKWArgs
    from pyvisa.util import BINARY_DATATYPES

log = logging.getLogger(__name__)


class YokogawaData(Parameter):
    """Parameter reading a binary trace block from the instrument.

    Supports REAL64 and REAL32 formats and returns a NumPy array. Used for the
    wavelength (setpoint) axis; the level data that carries this axis as its
    setpoints is read by :class:`YokogawaDataWithSetpoints`.
    """

    # Map the instrument data format to the pyvisa/struct datatype code.
    _DATATYPES: "dict[str, BINARY_DATATYPES]" = {'REAL64': 'd', 'REAL32': 'f'}

    def __init__(
        self,
        name: str,
        *,
        data_format: str = 'REAL64',
        **kwargs: "Unpack[ParameterKWArgs]",
    ) -> None:
        get_cmd = kwargs.pop("get_cmd", None)
        super().__init__(name, **kwargs)

        if data_format not in self._DATATYPES:
            raise ValueError(f"Unsupported format {data_format!r}; expected 'REAL64' or 'REAL32'")
        if not isinstance(get_cmd, str):
            raise ValueError("YokogawaData requires a get_cmd query string")

        self.data_format = data_format
        self._get_cmd = get_cmd

    def get_raw(self) -> ParamRawDataType:
        """Retrieve raw binary data for this parameter and return as numpy.ndarray.

        Sets the instrument data format, then queries and parses the IEEE-488.2
        definite-length binary block via pyvisa's ``query_binary_values``. The
        AQ637x transmits low-order bytes first, i.e. little-endian
        (``is_big_endian=False``).
        """
        instrument = cast("YokogawaAQ637x", self.root_instrument)

        # Set data format
        instrument.format_data(self.data_format)

        # Query and parse the binary block
        return instrument.visa_handle.query_binary_values(
            self._get_cmd,
            datatype=self._DATATYPES[self.data_format],
            is_big_endian=False,
            container=np.ndarray,
        )


class YokogawaDataWithSetpoints(YokogawaData, ParameterWithSetpoints):
    """Trace level (y) data that carries its wavelength axis as setpoints.

    Reads the same IEEE-488.2 binary block as :class:`YokogawaData` but, being a
    :class:`~qcodes.parameters.ParameterWithSetpoints`, it declares its wavelength
    setpoint axis and an :class:`~qcodes.validators.Arrays` shape, so the data
    integrates with the QCoDeS measurement/dataset system (the associated
    wavelength axis is recorded automatically).
    """


class YokogawaAQ637xChannel(InstrumentChannel):
    """Channel representing a single trace on the Yokogawa OSA.

    Exposes trace-specific parameters (state, attribute, trace_axis, data, etc.)
    and convenience commands for trace operations (activate, delete, set modes).
    """

    def __init__(
            self,
            parent: Instrument,
            name: str,
            trace: str,
            **kwargs: "Unpack[InstrumentBaseKWArgs]",
    ) -> None:
        super().__init__(parent, name, **kwargs)
        self.trace = trace

        self.state: Parameter = self.add_parameter(
            "state",
            set_cmd=f":TRACe:STATe:{trace} {{}}",
            get_cmd=f":TRACe:STATe:{trace}?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        "Sets/queries the display status of the specified trace"

        self.attribute: Parameter = self.add_parameter(
            "attribute",
            set_cmd=f":TRACe:ATTRibute:{trace} {{}}",
            get_cmd=f":TRACe:ATTRibute:{trace}?",
            val_mapping={
                "WRITE": 0,
                "FIX": 1,
                "MAX_HOLD": 2,
                "MIN_HOLD": 3,
                "ROLLING_AVERAGE": 4,
                "CALCULATE": 5
            },
        )
        """Trace Attribute"""

        self.roll_avg: Parameter = self.add_parameter(
            "roll_avg",
            set_cmd=f":TRACe:ATTRibute:RAVG:{trace} {{}}",
            get_cmd=f":TRACe:ATTRibute:RAVG:{trace}?",
            vals=Ints(2, 100),
            get_parser=int,
        )
        """ROLL AVG averaging count for the specified trace"""

        self.data_sample_number: Parameter = self.add_parameter(
            "data_sample_number",
            get_cmd=f":TRACe:DATA:SNUMber? {trace}",
            get_parser=int,
        )
        """Number of sampled data points for this trace."""

        self.trace_axis: YokogawaData = self.add_parameter(
            "trace_axis",
            get_cmd=f":TRACe:DATA:X? {trace}",
            parameter_class=YokogawaData,
            unit="m",
            label=f"{trace} axis",
            vals=Arrays(shape=(self._sample_count,)),
            snapshot_value=False,
        )
        """X-axis data for this trace, the setpoints for `data`.

        The unit follows `unit_x`: wavelength (m, the default and the declared
        unit here), frequency (Hz) or wavenumber (1/m) on the AQ6375/AQ6375B.
        """

        self.data: YokogawaDataWithSetpoints = self.add_parameter(
            "data",
            get_cmd=f":TRACe:DATA:Y? {trace}",
            parameter_class=YokogawaDataWithSetpoints,
            unit="dBm",
            label=f"{trace} level",
            setpoints=(self.trace_axis,),
            vals=Arrays(shape=(self._sample_count,)),
            snapshot_value=False,
        )
        """Level data for this trace, with `trace_axis` as its setpoint axis."""

    def _sample_count(self) -> int:
        """Current number of sampled points, used as the trace-data array shape."""
        return int(self.data_sample_number())

    def active(self) -> None:
        """Set trace in ACTIVE mode"""
        self.write(f":TRACe:ACTive {self.trace}")

    def delete(self) -> None:
        """Delete the data of this trace."""
        self.write(f":TRACe:DELete {self.trace}")

    def write_mode(self) -> None:
        """Set trace in WRITE mode"""
        self.write(f":TRACe:ATTRibute:{self.trace} WRITe")

    def fix(self) -> None:
        """Set trace in FIX mode"""
        self.write(f":TRACe:ATTRibute:{self.trace} FIX")

    def max_hold(self) -> None:
        """Set trace in MAX HOLD mode"""
        self.write(f":TRACe:ATTRibute:{self.trace} MAX")

    def min_hold(self) -> None:
        """Set trace in MIN HOLD mode"""
        self.write(f":TRACe:ATTRibute:{self.trace} MIN")


class YokogawaAQ637xAutoMarker(InstrumentChannel):
    """One of the four advanced (auto) markers ``AMARker1``–``AMARker4``.

    Exposes marker state/position/readout and the integral and power-density (noise)
    marker functions, plus peak/bottom search actions.
    """

    def __init__(
            self,
            parent: Instrument,
            name: str,
            index: int,
            **kwargs: "Unpack[InstrumentBaseKWArgs]",
    ) -> None:
        super().__init__(parent, name, **kwargs)
        self._index = index
        base = f":CALCulate:AMARker{index}"

        self.state: Parameter = self.add_parameter(
            "state",
            set_cmd=f"{base}:STATe {{}}",
            get_cmd=f"{base}:STATe?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Enable or disable this auto marker (on/off)"""

        self.trace: Parameter = self.add_parameter(
            "trace",
            set_cmd=f"{base}:TRACe {{}}",
            get_cmd=f"{base}:TRACe?",
            vals=Enum("TRA", "TRB", "TRC", "TRD", "TRE", "TRF", "TRG"),
        )
        """Trace this marker is attached to (TRA–TRG)"""

        self.x: Parameter = self.add_parameter(
            "x",
            set_cmd=f"{base}:X {{}}",
            get_cmd=f"{base}:X?",
            get_parser=float,
        )
        """Marker X position (wavelength or frequency, per `marker_unit`)"""

        self.y: Parameter = self.add_parameter(
            "y",
            get_cmd=f"{base}:Y?",
            get_parser=float,
        )
        """Marker Y value (level readout)"""

        self.integral_state: Parameter = self.add_parameter(
            "integral_state",
            set_cmd=f"{base}:FUNCtion:INTegral:STATe {{}}",
            get_cmd=f"{base}:FUNCtion:INTegral:STATe?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Enable or disable the integral marker function (on/off)"""

        self.integral_range: Parameter = self.add_parameter(
            "integral_range",
            set_cmd=f"{base}:FUNCtion:INTegral:IRANge {{}}",
            get_cmd=f"{base}:FUNCtion:INTegral:IRANge?",
            get_parser=float,
            unit="Hz",
        )
        """Integration frequency range for the integral marker function (Hz)"""

        self.integral_result: Parameter = self.add_parameter(
            "integral_result",
            get_cmd=f"{base}:FUNCtion:INTegral:RESult?",
            get_parser=float,
        )
        """Result of the integral marker function"""

        self.pdensity_state: Parameter = self.add_parameter(
            "pdensity_state",
            set_cmd=f"{base}:FUNCtion:PDENsity:STATe {{}}",
            get_cmd=f"{base}:FUNCtion:PDENsity:STATe?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Enable or disable the power-density/noise marker function (on/off)"""

        self.pdensity_bandwidth: Parameter = self.add_parameter(
            "pdensity_bandwidth",
            set_cmd=f"{base}:FUNCtion:PDENsity:BWIDth {{}}M",
            get_cmd=f"{base}:FUNCtion:PDENsity:BWIDth?",
            get_parser=float,
            unit="m",
        )
        """Normalization bandwidth for the power-density marker function (m)"""

        self.pdensity_result: Parameter = self.add_parameter(
            "pdensity_result",
            get_cmd=f"{base}:FUNCtion:PDENsity:RESult?",
            get_parser=float,
        )
        """Result of the power-density/noise marker function"""

    def off(self) -> None:
        """Turn this auto marker off."""
        self.write(f":CALCulate:AMARker{self._index}:AOFF")

    def function_preset(self) -> None:
        """Reset this marker's analysis function to its default."""
        self.write(f":CALCulate:AMARker{self._index}:FUNCtion:PRESet")

    def maximum(self) -> None:
        """Move the marker to the peak (maximum) level."""
        self.write(f":CALCulate:AMARker{self._index}:MAXimum")

    def maximum_left(self) -> None:
        """Move the marker to the next peak to the left."""
        self.write(f":CALCulate:AMARker{self._index}:MAXimum:LEFT")

    def maximum_next(self) -> None:
        """Move the marker to the next-highest peak."""
        self.write(f":CALCulate:AMARker{self._index}:MAXimum:NEXT")

    def maximum_right(self) -> None:
        """Move the marker to the next peak to the right."""
        self.write(f":CALCulate:AMARker{self._index}:MAXimum:RIGHt")

    def minimum(self) -> None:
        """Move the marker to the bottom (minimum) level."""
        self.write(f":CALCulate:AMARker{self._index}:MINimum")

    def minimum_left(self) -> None:
        """Move the marker to the next bottom to the left."""
        self.write(f":CALCulate:AMARker{self._index}:MINimum:LEFT")

    def minimum_next(self) -> None:
        """Move the marker to the next-lowest bottom."""
        self.write(f":CALCulate:AMARker{self._index}:MINimum:NEXT")

    def minimum_right(self) -> None:
        """Move the marker to the next bottom to the right."""
        self.write(f":CALCulate:AMARker{self._index}:MINimum:RIGHt")


class YokogawaAQ637x(VisaInstrument):
    """
    Driver for the Yokogawa AQ6370C/AQ6370D/AQ6373/AQ6373B/AQ6375/AQ6375B Optical Spectrum Analyzer.
    """

    default_terminator = "\n"

    MODELS = [
        "AQ6370C",
        "AQ6370D",
        "AQ6373",
        "AQ6373B",
        "AQ6375",
        "AQ6375B",
    ]
    """List of support Optical Spectrum Analyzer"""

    def __init__(
            self,
            name: str,
            address: str,
            **kwargs: "Unpack[VisaInstrumentKWArgs]",
    ):
        super().__init__(name, address, **kwargs)

        self.model = self.get_idn()["model"]
        if self.model is None:
            raise KeyError("Could not determine model")
        if self.model not in self.MODELS:
            raise KeyError(f"Model code {self.model} is not recognized")

        # Create channels (called traces for OSA) and register each as a submodule
        # so they appear in ``instrument.submodules`` and in the snapshot. The
        # explicit attributes preserve autocompletion / static typing.
        self.TRA = self.add_submodule("TRA", YokogawaAQ637xChannel(self, "TRA", "TRA"))
        self.TRB = self.add_submodule("TRB", YokogawaAQ637xChannel(self, "TRB", "TRB"))
        self.TRC = self.add_submodule("TRC", YokogawaAQ637xChannel(self, "TRC", "TRC"))
        self.TRD = self.add_submodule("TRD", YokogawaAQ637xChannel(self, "TRD", "TRD"))
        self.TRE = self.add_submodule("TRE", YokogawaAQ637xChannel(self, "TRE", "TRE"))
        self.TRF = self.add_submodule("TRF", YokogawaAQ637xChannel(self, "TRF", "TRF"))
        self.TRG = self.add_submodule("TRG", YokogawaAQ637xChannel(self, "TRG", "TRG"))
        # Immutable view for iteration; ``snapshotable=False`` so the traces are
        # not snapshotted twice (once here, once via their own submodules).
        self.traces = ChannelTuple(
            self,
            "traces",
            YokogawaAQ637xChannel,
            (self.TRA, self.TRB, self.TRC, self.TRD, self.TRE, self.TRF, self.TRG),
            snapshotable=False,
        )
        """Instrument traces (aka channels)"""
        self.add_submodule("traces", self.traces)

        # Advanced (auto) markers AMARker1..AMARker4
        self.amarker1 = self.add_submodule("amarker1", YokogawaAQ637xAutoMarker(self, "amarker1", 1))
        self.amarker2 = self.add_submodule("amarker2", YokogawaAQ637xAutoMarker(self, "amarker2", 2))
        self.amarker3 = self.add_submodule("amarker3", YokogawaAQ637xAutoMarker(self, "amarker3", 3))
        self.amarker4 = self.add_submodule("amarker4", YokogawaAQ637xAutoMarker(self, "amarker4", 4))
        self.amarkers = ChannelTuple(
            self,
            "amarkers",
            YokogawaAQ637xAutoMarker,
            (self.amarker1, self.amarker2, self.amarker3, self.amarker4),
            snapshotable=False,
        )
        """Advanced/auto markers (AMARker1–AMARker4)"""
        self.add_submodule("amarkers", self.amarkers)


        # Common Commands (IEEE 488.2)

        self.event_status_enable: Parameter = self.add_parameter(
            "event_status_enable",
            set_cmd="*ESE {}",
            get_cmd="*ESE?",
            vals=Ints(0, 255),
            get_parser=int,
        )
        """Standard event status enable register (0–255)"""

        self.event_status_register: Parameter = self.add_parameter(
            "event_status_register",
            get_cmd="*ESR?",
            get_parser=int,
        )
        """Standard event status register (read and clear)"""

        self.operation_complete: Parameter = self.add_parameter(
            "operation_complete",
            set_cmd="*OPC",
            get_cmd="*OPC?",
            get_parser=int,
        )
        """Operation complete flag (sets/queries OPC bit in ESR)"""

        self.service_request_enable: Parameter = self.add_parameter(
            "service_request_enable",
            set_cmd="*SRE {}",
            get_cmd="*SRE?",
            vals=Ints(0, 255),
            get_parser=int,
        )
        """Service request enable register (0–255)"""

        self.status_byte: Parameter = self.add_parameter(
            "status_byte",
            get_cmd="*STB?",
            get_parser=int,
        )
        """Status byte register (read-only)"""

        self.self_test: Parameter = self.add_parameter(
            "self_test",
            get_cmd=self._get_self_test,
            snapshot_value=False,  # Exclude from snapshot as it takes time to execute
        )
        """Run instrument self-test and return status code"""

        # APPLication:DLOGging Sub System Commands

        self.dlog_elapsed_time: Parameter = self.add_parameter(
            "dlog_elapsed_time",
            get_cmd=":APPLication:DLOGging:ETIMe?",
            get_parser=int,
            unit="s",
        )
        """Elapsed data-logging time (s)"""

        self.dlog_interval: Parameter = self.add_parameter(
            "dlog_interval",
            set_cmd=":APPLication:DLOGging:LPARameter:INTerval {}",
            get_cmd=":APPLication:DLOGging:LPARameter:INTerval?",
            vals=Ints(),
            get_parser=int,
        )
        """Data-logging sampling interval"""

        self.dlog_item: Parameter = self.add_parameter(
            "dlog_item",
            set_cmd=":APPLication:DLOGging:LPARameter:ITEM {}",
            get_cmd=":APPLication:DLOGging:LPARameter:ITEM?",
            vals=Ints(0, 3),
            get_parser=int,
        )
        """Data-logging item selection"""

        self.dlog_lmode: Parameter = self.add_parameter(
            "dlog_lmode",
            set_cmd=":APPLication:DLOGging:LPARameter:LMODe {}",
            get_cmd=":APPLication:DLOGging:LPARameter:LMODe?",
            vals=Ints(1, 2),
            get_parser=int,
        )
        """Data-logging mode"""

        self.dlog_memory: Parameter = self.add_parameter(
            "dlog_memory",
            set_cmd=":APPLication:DLOGging:LPARameter:MEMory {}",
            get_cmd=":APPLication:DLOGging:LPARameter:MEMory?",
            val_mapping={
                "INTERNAL": "INT",
                "EXTERNAL": "EXT",
            },
        )
        """Data-logging storage location (internal or external)"""

        self.dlog_mthresh: Parameter = self.add_parameter(
            "dlog_mthresh",
            set_cmd=":APPLication:DLOGging:LPARameter:MTHResh {}",
            get_cmd=":APPLication:DLOGging:LPARameter:MTHResh?",
            get_parser=float,
        )
        """Data-logging measurement threshold"""

        self.dlog_pdetect_athresh: Parameter = self.add_parameter(
            "dlog_pdetect_athresh",
            set_cmd=":APPLication:DLOGging:LPARameter:PDETect:ATHResh {}",
            get_cmd=":APPLication:DLOGging:LPARameter:PDETect:ATHResh?",
            get_parser=float,
        )
        """Peak-detection absolute threshold"""

        self.dlog_pdetect_rthresh: Parameter = self.add_parameter(
            "dlog_pdetect_rthresh",
            set_cmd=":APPLication:DLOGging:LPARameter:PDETect:RTHResh {}",
            get_cmd=":APPLication:DLOGging:LPARameter:PDETect:RTHResh?",
            get_parser=float,
        )
        """Peak-detection relative threshold"""

        self.dlog_pdetect_ttype: Parameter = self.add_parameter(
            "dlog_pdetect_ttype",
            set_cmd=":APPLication:DLOGging:LPARameter:PDETect:TTYPe {}",
            get_cmd=":APPLication:DLOGging:LPARameter:PDETect:TTYPe?",
            val_mapping={
                "ABSOLUTE": "ABS",
                "RELATIVE": "REL",
            },
        )
        """Peak-detection threshold type (absolute or relative)"""

        self.dlog_tduration: Parameter = self.add_parameter(
            "dlog_tduration",
            set_cmd=":APPLication:DLOGging:LPARameter:TDURation {}",
            get_cmd=":APPLication:DLOGging:LPARameter:TDURation?",
            vals=Ints(),
            get_parser=int,
        )
        """Data-logging total duration"""

        self.dlog_tlogging: Parameter = self.add_parameter(
            "dlog_tlogging",
            set_cmd=":APPLication:DLOGging:LPARameter:TLOGging {}",
            get_cmd=":APPLication:DLOGging:LPARameter:TLOGging?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Time-based logging (on/off)"""

        self.dlog_state: Parameter = self.add_parameter(
            "dlog_state",
            set_cmd=":APPLication:DLOGging:STATe {}",
            get_cmd=":APPLication:DLOGging:STATe?",
            val_mapping={
                "STOP": 0,
                "START": 1,
            },
        )
        """Data-logging run state (start/stop)"""

        # CALCulate Sub System Commands — Line markers

        self.line_marker_srange: Parameter = self.add_parameter(
            "line_marker_srange",
            set_cmd=":CALCulate:LMARker:SRANge {}",
            get_cmd=":CALCulate:LMARker:SRANge?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Limit the analysis range to line markers L1–L2 (on/off)"""

        # CALCulate Sub System Commands — Manual markers

        self.marker_auto: Parameter = self.add_parameter(
            "marker_auto",
            set_cmd=":CALCulate:MARKer:AUTO {}",
            get_cmd=":CALCulate:MARKer:AUTO?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Automatic marker placement (on/off)"""

        self.marker_function_format: Parameter = self.add_parameter(
            "marker_function_format",
            set_cmd=":CALCulate:MARKer:FUNCtion:FORMat {}",
            get_cmd=":CALCulate:MARKer:FUNCtion:FORMat?",
            val_mapping={
                "OFFSET": 0,
                "SPACING": 1,
            },
        )
        """Marker readout format (offset or spacing)"""

        self.marker_function_update: Parameter = self.add_parameter(
            "marker_function_update",
            set_cmd=":CALCulate:MARKer:FUNCtion:UPDate {}",
            get_cmd=":CALCulate:MARKer:FUNCtion:UPDate?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Continuous marker-function value update (on/off)"""

        self.marker_maximum_scenter_auto: Parameter = self.add_parameter(
            "marker_maximum_scenter_auto",
            set_cmd=":CALCulate:MARKer:MAXimum:SCENter:AUTO {}",
            get_cmd=":CALCulate:MARKer:MAXimum:SCENter:AUTO?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Automatic 'peak to center' after each sweep (on/off)"""

        self.marker_maximum_srlevel_auto: Parameter = self.add_parameter(
            "marker_maximum_srlevel_auto",
            set_cmd=":CALCulate:MARKer:MAXimum:SRLevel:AUTO {}",
            get_cmd=":CALCulate:MARKer:MAXimum:SRLevel:AUTO?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Automatic 'peak to reference level' after each sweep (on/off)"""

        self.marker_msearch: Parameter = self.add_parameter(
            "marker_msearch",
            set_cmd=":CALCulate:MARKer:MSEarch {}",
            get_cmd=":CALCulate:MARKer:MSEarch?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Multi-peak/bottom marker search mode (on/off)"""

        self.marker_msearch_sort: Parameter = self.add_parameter(
            "marker_msearch_sort",
            set_cmd=":CALCulate:MARKer:MSEarch:SORT {}",
            get_cmd=":CALCulate:MARKer:MSEarch:SORT?",
            val_mapping={
                "WAVELENGTH": 0,
                "LEVEL": 1,
            },
        )
        """Sort order for multi-marker search (by wavelength or level)"""

        self.marker_msearch_threshold: Parameter = self.add_parameter(
            "marker_msearch_threshold",
            set_cmd=":CALCulate:MARKer:MSEarch:THResh {}",
            get_cmd=":CALCulate:MARKer:MSEarch:THResh?",
            get_parser=float,
            unit="dB",
        )
        """Threshold for multi-marker search (dB)"""

        self.marker_unit: Parameter = self.add_parameter(
            "marker_unit",
            set_cmd=":CALCulate:MARKer:UNIT {}",
            get_cmd=":CALCulate:MARKer:UNIT?",
            val_mapping=self._x_unit_val_mapping(),
        )
        """Marker X-axis unit (wavelength or frequency; wavenumber on AQ6375/AQ6375B)"""

        # CALibration Sub System Commands

        self.calibration_bandwidth_wavelength: Parameter = self.add_parameter(
            "calibration_bandwidth_wavelength",
            get_cmd=":CALibration:BANDwidth:WAVelength?",
            get_parser=float,
            unit="m",
        )
        """Wavelength at which the resolution-bandwidth calibration was performed (m)"""

        self.calibration_wavelength_external_source: Parameter = self.add_parameter(
            "calibration_wavelength_external_source",
            set_cmd=":CALibration:WAVelength:EXTernal:SOURce {}",
            get_cmd=":CALibration:WAVelength:EXTernal:SOURce?",
            val_mapping={
                "LASER": 0,
                "GASCELL": 1,
                "EMISSION": 2,
            },
        )
        """External wavelength-calibration reference source (laser, gas cell or emission line)"""

        self.calibration_wavelength_external_wavelength: Parameter = self.add_parameter(
            "calibration_wavelength_external_wavelength",
            set_cmd=":CALibration:WAVelength:EXTernal:WAVelength {}M",
            get_cmd=":CALibration:WAVelength:EXTernal:WAVelength?",
            get_parser=float,
            unit="m",
        )
        """Reference wavelength used for external wavelength calibration (m)"""

        self.calibration_zero_auto: Parameter = self.add_parameter(
            "calibration_zero_auto",
            set_cmd=":CALibration:ZERO:AUTO {}",
            get_cmd=":CALibration:ZERO:AUTO?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Enable or disable automatic zeroing of the monitor (on/off). See also `zero_once()`"""

        self.calibration_zero_interval: Parameter = self.add_parameter(
            "calibration_zero_interval",
            set_cmd=":CALibration:ZERO:INTerval {}",
            get_cmd=":CALibration:ZERO:INTerval?",
            vals=Ints(),
            get_parser=int,
        )
        """Interval between automatic zeroing operations"""

        self.calibration_zero_status: Parameter = self.add_parameter(
            "calibration_zero_status",
            get_cmd=":CALibration:ZERO:STATus?",
            get_parser=int,
        )
        """Status of the most recent zeroing operation"""

        # DISPlay Sub System Commands

        self.display_color: Parameter = self.add_parameter(
            "display_color",
            set_cmd=":DISPlay:COLor {}",
            get_cmd=":DISPlay:COLor?",
            vals=Ints(0, 5),
            get_parser=int,
        )
        """Screen color mode (0 = B/W, 1–5 = color modes)"""

        self.display_enabled: Parameter = self.add_parameter(
            "display_enabled",
            set_cmd=":DISPlay {}",
            get_cmd=":DISPlay?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Enable or disable the display (on/off)"""

        self.display_overview_position: Parameter = self.add_parameter(
            "display_overview_position",
            set_cmd=":DISPlay:OVIew:POSition {}",
            get_cmd=":DISPlay:OVIew:POSition?",
            val_mapping={
                "OFF": 0,
                "LEFT": 1,
                "RIGHT": 2,
            },
        )
        """Overview display position (off, left, right) (position)"""

        self.display_overview_size: Parameter = self.add_parameter(
            "display_overview_size",
            set_cmd=":DISPlay:OVIew:SIZE {}",
            get_cmd=":DISPlay:OVIew:SIZE?",
            val_mapping={
                "LARGE": 0,
                "SMALL": 1,
            },
        )
        """Overview display size (large or small) (size)"""

        self.display_split: Parameter = self.add_parameter(
            "display_split",
            set_cmd=":DISPlay:SPLit {}",
            get_cmd=":DISPlay:SPLit?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Enable or disable split screen display (on/off)"""

        self.display_split_hold_lower: Parameter = self.add_parameter(
            "display_split_hold_lower",
            set_cmd=":DISPlay:SPLit:HOLD:LOWer {}",
            get_cmd=":DISPlay:SPLit:HOLD:LOWer?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Hold the lower trace in split-screen mode (on/off)"""

        self.display_split_hold_upper: Parameter = self.add_parameter(
            "display_split_hold_upper",
            set_cmd=":DISPlay:SPLit:HOLD:UPPer {}",
            get_cmd=":DISPlay:SPLit:HOLD:UPPer?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Hold the upper trace in split-screen mode (on/off)"""

        self.display_text_data: Parameter = self.add_parameter(
            "display_text_data",
            set_cmd=':DISPlay:TEXT:DATA "{}"',
            get_cmd=":DISPlay:TEXT:DATA?",
            vals=Strings(max_length=56),
        )
        """Display text label (max 56 characters)"""

        self.display_trace_x_center: Parameter = self.add_parameter(
            "display_trace_x_center",
            set_cmd=":DISPlay:TRACe:X:SCALe:CENTer {}M",
            get_cmd=":DISPlay:TRACe:X:SCALe:CENTer?",
            get_parser=float,
            unit="m",
        )
        """Center value of the display X-axis (m)"""

        self.display_trace_x_span: Parameter = self.add_parameter(
            "display_trace_x_span",
            set_cmd=":DISPlay:TRACe:X:SCALe:SPAN {}M",
            get_cmd=":DISPlay:TRACe:X:SCALe:SPAN?",
            get_parser=float,
            unit="m",
        )
        """Span of the display X-axis (m)"""

        self.display_trace_x_srange: Parameter = self.add_parameter(
            "display_trace_x_srange",
            set_cmd=":DISPlay:TRACe:X:SCALe:SRANge {}",
            get_cmd=":DISPlay:TRACe:X:SCALe:SRANge?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Limit analytical range to the display X-axis scale (on/off)"""

        self.display_trace_x_start: Parameter = self.add_parameter(
            "display_trace_x_start",
            set_cmd=":DISPlay:TRACe:X:SCALe:STARt {}M",
            get_cmd=":DISPlay:TRACe:X:SCALe:STARt?",
            get_parser=float,
            unit="m",
        )
        """Start value of the display X-axis (m)"""

        self.display_trace_x_stop: Parameter = self.add_parameter(
            "display_trace_x_stop",
            set_cmd=":DISPlay:TRACe:X:SCALe:STOP {}M",
            get_cmd=":DISPlay:TRACe:X:SCALe:STOP?",
            get_parser=float,
            unit="m",
        )
        """Stop value of the display X-axis (m)"""

        self.display_trace_y_nmask: Parameter = self.add_parameter(
            "display_trace_y_nmask",
            set_cmd=":DISPlay:TRACe:Y:NMASk {}",
            get_cmd=":DISPlay:TRACe:Y:NMASk?",
            get_parser=float,
            unit="dB",
        )
        """Y-axis display mask threshold (-999 disables masking) (dB)"""

        self.display_trace_y_nmask_type: Parameter = self.add_parameter(
            "display_trace_y_nmask_type",
            set_cmd=":DISPlay:TRACe:Y:NMASk:TYPE {}",
            get_cmd=":DISPlay:TRACe:Y:NMASk:TYPE?",
            val_mapping={
                "VERTICAL": 0,
                "HORIZONTAL": 1,
            },
        )
        """Y-axis mask display type (vertical or horizontal) (type)"""

        self.display_trace_y_dnumber: Parameter = self.add_parameter(
            "display_trace_y_dnumber",
            set_cmd=":DISPlay:TRACe:Y:SCALe:DNUMber {}",
            get_cmd=":DISPlay:TRACe:Y:SCALe:DNUMber?",
            vals=Enum(8, 10, 12),
            get_parser=int,
        )
        """Number of Y-axis display divisions (8, 10, or 12) (divisions)"""

        self.display_trace_y1_blevel: Parameter = self.add_parameter(
            "display_trace_y1_blevel",
            set_cmd=":DISPlay:TRACe:Y1:SCALe:BLEVel {}",
            get_cmd=":DISPlay:TRACe:Y1:SCALe:BLEVel?",
            get_parser=float,
            unit="W",
        )
        """Y1-axis base level for linear scale (W)"""

        self.display_trace_y1_pdivision: Parameter = self.add_parameter(
            "display_trace_y1_pdivision",
            set_cmd=":DISPlay:TRACe:Y1:SCALe:PDIVision {}",
            get_cmd=":DISPlay:TRACe:Y1:SCALe:PDIVision?",
            get_parser=float,
            unit="dB",
        )
        """Y1-axis level scale per division (dB)"""

        self.display_trace_y1_rlevel: Parameter = self.add_parameter(
            "display_trace_y1_rlevel",
            set_cmd=":DISPlay:TRACe:Y1:SCALe:RLEVel {}DBM",
            get_cmd=":DISPlay:TRACe:Y1:SCALe:RLEVel?",
            get_parser=float,
            unit="dBm",
        )
        """Y1-axis reference level (dBm)"""

        self.display_trace_y1_rposition: Parameter = self.add_parameter(
            "display_trace_y1_rposition",
            set_cmd=":DISPlay:TRACe:Y1:SCALe:RPOSition {}",
            get_cmd=":DISPlay:TRACe:Y1:SCALe:RPOSition?",
            vals=Ints(0, 12),
            get_parser=int,
            unit="DIV",
        )
        """Y1-axis reference level position (DIV)"""

        self.display_trace_y1_spacing: Parameter = self.add_parameter(
            "display_trace_y1_spacing",
            set_cmd=":DISPlay:TRACe:Y1:SCALe:SPACing {}",
            get_cmd=":DISPlay:TRACe:Y1:SCALe:SPACing?",
            val_mapping={
                "LOG": 0,
                "LINEAR": 1,
            },
        )
        """Y1-axis scale spacing (logarithmic or linear) (type)"""

        self.display_trace_y1_unit: Parameter = self.add_parameter(
            "display_trace_y1_unit",
            set_cmd=":DISPlay:TRACe:Y1:SCALe:UNIT {}",
            get_cmd=":DISPlay:TRACe:Y1:SCALe:UNIT?",
            val_mapping={
                "DBM": 0,
                "W": 1,
                "DBM_PER_NM": 2,
                "W_PER_NM": 3,
            },
        )
        """Y1-axis unit (dBm, W, dBm/nm, or W/nm) (unit)"""

        self.display_trace_y2_auto: Parameter = self.add_parameter(
            "display_trace_y2_auto",
            set_cmd=":DISPlay:TRACe:Y2:SCALe:AUTO {}",
            get_cmd=":DISPlay:TRACe:Y2:SCALe:AUTO?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Enable or disable automatic scaling of the Y2-axis (on/off)"""

        self.display_trace_y2_length: Parameter = self.add_parameter(
            "display_trace_y2_length",
            set_cmd=":DISPlay:TRACe:Y2:SCALe:LENGth {}KM",
            get_cmd=":DISPlay:TRACe:Y2:SCALe:LENGth?",
            get_parser=float,
            unit='km',
        )
        """Optical fiber length for Y2-axis when unit is dB/km (km)"""

        self.display_trace_y2_olevel: Parameter = self.add_parameter(
            "display_trace_y2_olevel",
            set_cmd=":DISPlay:TRACe:Y2:SCALe:OLEVel {}DB",
            get_cmd=":DISPlay:TRACe:Y2:SCALe:OLEVel?",
            get_parser=float,
            unit="dB",
        )
        """Y2-axis offset level (dB or dB/km, unit depends on subscale)"""

        self.display_trace_y2_pdivision: Parameter = self.add_parameter(
            "display_trace_y2_pdivision",
            set_cmd=":DISPlay:TRACe:Y2:SCALe:PDIVision {}DB",
            get_cmd=":DISPlay:TRACe:Y2:SCALe:PDIVision?",
            get_parser=float,
            unit="dB",
        )
        """Y2-axis scale per division (unit depends on subscale)"""

        self.display_trace_y2_rposition: Parameter = self.add_parameter(
            "display_trace_y2_rposition",
            set_cmd=":DISPlay:TRACe:Y2:SCALe:RPOSition {}",
            get_cmd=":DISPlay:TRACe:Y2:SCALe:RPOSition?",
            vals=Ints(0, 12),
            get_parser=int,
            unit="DIV",
        )
        """Y2-axis reference level position (DIV)"""

        self.display_trace_y2_sminimum: Parameter = self.add_parameter(
            "display_trace_y2_sminimum",
            set_cmd=":DISPlay:TRACe:Y2:SCALe:SMINimum {}%",
            get_cmd=":DISPlay:TRACe:Y2:SCALe:SMINimum?",
            get_parser=float,
            unit="%",
        )
        """Y2-axis scale minimum value (linear or % mode)"""

        self.display_trace_y2_unit: Parameter = self.add_parameter(
            "display_trace_y2_unit",
            set_cmd=":DISPlay:TRACe:Y2:SCALe:UNIT {}",
            get_cmd=":DISPlay:TRACe:Y2:SCALe:UNIT?",
            val_mapping={
                "DB": 0,
                "LINEAR": 1,
                "DB_PER_KM": 2,
                "PERCENT": 3,
            },
        )
        """Y2-axis unit (dB, linear, dB/km, or %) (unit)"""

        # FORMat Sub System Commands

        self.format_data: Parameter = self.add_parameter(
            "format_data",
            set_cmd=":FORMat:DATA {}",
            get_cmd=":FORMat:DATA?",
            val_mapping={
                "ASCII": "ASCII",
                "REAL64": "REAL,64",
                "REAL32": "REAL,32",
            },
        )
        """Data transfer format (ASCII, REAL 64-bit, or REAL 32-bit) (format)"""

        # INITiate Sub System Command

        self.sweep_mode: Parameter = self.add_parameter(
            "sweep_mode",
            set_cmd=":INITiate:SMODe {}",
            get_cmd=":INITiate:SMODe?",
            val_mapping={
                "SINGLE": 1,
                "REPEAT": 2,
                "AUTO": 3,
                "SEGMENT": 4
            }
        )
        """Sets/queries the sweep mode (mode)"""

        # SENSe Sub System Commands

        self.sense_average_count: Parameter = self.add_parameter(
            "sense_average_count",
            set_cmd=":SENSe:AVERage:COUNt {}",
            get_cmd=":SENSe:AVERage:COUNt?",
            vals=Ints(),
            get_parser=int,
        )
        """Number of averages per measured point"""

        self.sense_bandwidth_resolution: Parameter = self.add_parameter(
            "sense_bandwidth_resolution",
            set_cmd=":SENSe:BANDwidth:RESolution {}M",
            get_cmd=":SENSe:BANDwidth:RESolution?",
            get_parser=float,
            unit="m",
        )
        """Measurement resolution (bandwidth)"""

        self.sense_chopper: Parameter = self.add_parameter(
            "sense_chopper",
            set_cmd=":SENSe:CHOPper {}",
            get_cmd=":SENSe:CHOPper?",
            val_mapping={
                "OFF": 0,
                "SWITCH": 2,
            },
        )
        """Chopper mode (off or switch) (mode)"""

        self.sense_correction_level_shift: Parameter = self.add_parameter(
            "sense_correction_level_shift",
            set_cmd=":SENSe:CORRection:LEVel:SHIFt {}",
            get_cmd=":SENSe:CORRection:LEVel:SHIFt?",
            get_parser=float,
            unit="dB",
        )
        """Level correction offset (dB)"""

        self.sense_correction_rvelocity_medium: Parameter = self.add_parameter(
            "sense_correction_rvelocity_medium",
            set_cmd=":SENSe:CORRection:RVELocity:MEDium {}",
            get_cmd=":SENSe:CORRection:RVELocity:MEDium?",
            val_mapping={
                "AIR": 0,
                "VACUUM": 1,
            },
        )
        """Wavelength reference medium (air or vacuum) (medium)"""

        self.sense_correction_wavelength_shift: Parameter = self.add_parameter(
            "sense_correction_wavelength_shift",
            set_cmd=":SENSe:CORRection:WAVelength:SHIFt {}",
            get_cmd=":SENSe:CORRection:WAVelength:SHIFt?",
            get_parser=float,
            unit="m",
        )
        """Wavelength correction offset (m)"""

        self.sense_sensitivity: Parameter = self.add_parameter(
            "sense_sensitivity",
            set_cmd=":SENSe:SENSe {}",
            get_cmd=":SENSe:SENSe?",
            val_mapping={
                "NORMAL_HOLD": 0,
                "NORMAL_AUTO": 1,
                "MID": 2,
                "HIGH1": 3,
                "HIGH2": 4,
                "HIGH3": 5,
                "NORMAL": 6,
            },
        )
        """Measurement sensitivity setting (setting)"""

        self.sense_setting_correction: Parameter = self.add_parameter(
            "sense_setting_correction",
            set_cmd=":SENSe:SETTing:CORRection {}",
            get_cmd=":SENSe:SETTing:CORRection?",
            val_mapping={
                "OFF": 0,
                "ON_MODE1": 1,
                "ON_MODE2": 2,
            },
        )
        """Resolution correction function setting (mode)"""

        self.sense_setting_fconnector: Parameter = self.add_parameter(
            "sense_setting_fconnector",
            set_cmd=":SENSe:SETTing:FCONnector {}",
            get_cmd=":SENSe:SETTing:FCONnector?",
            val_mapping={
                "NORMAL": 0,
                "ANGLED": 1,
            },
        )
        """Fiber connector mode (normal or angled) (mode)"""

        if self.model in ("AQ6373", "AQ6373B"):
            self.sense_setting_fiber: Parameter = self.add_parameter(
                "sense_setting_fiber",
                set_cmd=":SENSe:SETTing:FIBer {}",
                get_cmd=":SENSe:SETTing:FIBer?",
                val_mapping={
                    "SMALL": 0,
                    "LARGE": 1,
                },
            )
            """Fiber core size mode (small or large) (mode)"""

        self.sense_setting_smoothing: Parameter = self.add_parameter(
            "sense_setting_smoothing",
            set_cmd=":SENSe:SETTing:SMOothing {}",
            get_cmd=":SENSe:SETTing:SMOothing?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Enable or disable smoothing (on/off)"""

        self.sense_sweep_points: Parameter = self.add_parameter(
            "sense_sweep_points",
            set_cmd=":SENSe:SWEep:POINts {}",
            get_cmd=":SENSe:SWEep:POINts?",
            vals=Ints(),
            get_parser=int,
        )
        """Number of samples measured per sweep (points)"""

        self.sense_sweep_points_auto: Parameter = self.add_parameter(
            "sense_sweep_points_auto",
            set_cmd=":SENSe:SWEep:POINts:AUTO {}",
            get_cmd=":SENSe:SWEep:POINts:AUTO?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Automatically set the number of sweep points (on/off)"""

        self.sense_sweep_segment_points: Parameter = self.add_parameter(
            "sense_sweep_segment_points",
            set_cmd=":SENSe:SWEep:SEGMent:POINts {}",
            get_cmd=":SENSe:SWEep:SEGMent:POINts?",
            vals=Ints(1, 2 ** 31 - 1),
            get_parser=int,
        )
        """Number of sampling points per segment sweep (points)"""

        self.sense_sweep_speed: Parameter = self.add_parameter(
            "sense_sweep_speed",
            set_cmd=":SENSe:SWEep:SPEed {}",
            get_cmd=":SENSe:SWEep:SPEed?",
            val_mapping={
                "1X": 0,
                "2X": 1,
            },
        )
        """Sweep speed (1x = standard, 2x = fast) (ratio)"""

        self.sense_sweep_step: Parameter = self.add_parameter(
            "sense_sweep_step",
            set_cmd=":SENSe:SWEep:STEP {}M",
            get_cmd=":SENSe:SWEep:STEP?",
            get_parser=float,
            unit="m",
        )
        """Sampling interval for sweep measurements (m)"""

        self.sense_sweep_time_0nm: Parameter = self.add_parameter(
            "sense_sweep_time_0nm",
            set_cmd=":SENSe:SWEep:TIME:0NM {}",
            get_cmd=":SENSe:SWEep:TIME:0NM?",
            vals=Ints(0, 2 ** 31 - 1),
            get_parser=int,
            unit="s",
        )
        """Measurement time for 0-nm sweep mode (s)"""

        self.sense_sweep_time_interval: Parameter = self.add_parameter(
            "sense_sweep_time_interval",
            set_cmd=":SENSe:SWEep:TIME:INTerval {}",
            get_cmd=":SENSe:SWEep:TIME:INTerval?",
            vals=Ints(0, 2 ** 31 - 1),
            get_parser=int,
            unit="s",
        )
        """Time between consecutive sweeps (s)"""

        if self.model not in ("AQ6370D", "AQ6373B", "AQ6375B"):
            self.sense_sweep_tlssync: Parameter = self.add_parameter(
                "sense_sweep_tlssync",
                set_cmd=":SENSe:SWEep:TLSSync {}",
                get_cmd=":SENSe:SWEep:TLSSync?",
                val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
            )
            """Enable or disable synchronous TLS sweep (on/off)"""

        self.sense_wavelength_center: Parameter = self.add_parameter(
            "sense_wavelength_center",
            set_cmd=":SENSe:WAVelength:CENTer {}M",
            get_cmd=":SENSe:WAVelength:CENTer?",
            get_parser=float,
            unit="m",
        )
        """Measurement center wavelength (m)"""

        self.sense_wavelength_span: Parameter = self.add_parameter(
            "sense_wavelength_span",
            set_cmd=":SENSe:WAVelength:SPAN {}M",
            get_cmd=":SENSe:WAVelength:SPAN?",
            get_parser=float,
            unit="m",
        )
        """Measurement wavelength span (m)"""

        self.sense_wavelength_srange: Parameter = self.add_parameter(
            "sense_wavelength_srange",
            set_cmd=":SENSe:WAVelength:SRANge {}",
            get_cmd=":SENSe:WAVelength:SRANge?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Limit wavelength sweep range to marker L1–L2 spacing (on/off)"""

        self.sense_wavelength_start: Parameter = self.add_parameter(
            "sense_wavelength_start",
            set_cmd=":SENSe:WAVelength:STARt {}M",
            get_cmd=":SENSe:WAVelength:STARt?",
            get_parser=float,
            unit="m",
        )
        """Measurement start wavelength (m)"""

        self.sense_wavelength_stop: Parameter = self.add_parameter(
            "sense_wavelength_stop",
            set_cmd=":SENSe:WAVelength:STOP {}M",
            get_cmd=":SENSe:WAVelength:STOP?",
            get_parser=float,
            unit="m",
        )
        """Measurement stop wavelength (m)"""

        # STATus Sub System Commands

        self.status_operation_condition: Parameter = self.add_parameter(
            "status_operation_condition",
            get_cmd=":STATus:OPERation:CONDition?",
            get_parser=int,
        )
        """Operation status condition register"""

        self.status_operation_enable: Parameter = self.add_parameter(
            "status_operation_enable",
            set_cmd=":STATus:OPERation:ENABle {}",
            get_cmd=":STATus:OPERation:ENABle?",
            vals=Ints(0, 65535),
            get_parser=int,
        )
        """Operation status enable register"""

        self.status_operation_event: Parameter = self.add_parameter(
            "status_operation_event",
            get_cmd=":STATus:OPERation:EVENt?",
            get_parser=int,
        )
        """Operation status event register (read and clear)"""

        self.status_questionable_condition: Parameter = self.add_parameter(
            "status_questionable_condition",
            get_cmd=":STATus:QUEStionable:CONDition?",
            get_parser=int,
        )
        """Questionable status condition register"""

        self.status_questionable_enable: Parameter = self.add_parameter(
            "status_questionable_enable",
            set_cmd=":STATus:QUEStionable:ENABle {}",
            get_cmd=":STATus:QUEStionable:ENABle?",
            vals=Ints(0, 65535),
            get_parser=int,
        )
        """Questionable status enable register"""

        self.status_questionable_event: Parameter = self.add_parameter(
            "status_questionable_event",
            get_cmd=":STATus:QUEStionable:EVENt?",
            get_parser=int,
        )
        """Questionable status event register (read and clear)"""

        # SYSTem Sub System Commands

        self.system_buzzer_click: Parameter = self.add_parameter(
            "system_buzzer_click",
            set_cmd=":SYSTem:BUZZer:CLIC {}",
            get_cmd=":SYSTem:BUZZer:CLIC?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Key-click buzzer (on/off)"""

        self.system_buzzer_warning: Parameter = self.add_parameter(
            "system_buzzer_warning",
            set_cmd=":SYSTem:BUZZer:WARNing {}",
            get_cmd=":SYSTem:BUZZer:WARNing?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Warning buzzer (on/off)"""

        self.system_communicate_gpib2_address: Parameter = self.add_parameter(
            "system_communicate_gpib2_address",
            set_cmd=":SYSTem:COMMunicate:GP-IB2:ADDRess {}",
            get_cmd=":SYSTem:COMMunicate:GP-IB2:ADDRess?",
            vals=Ints(0, 30),
            get_parser=int,
        )
        """GP-IB2 (device) address"""

        self.system_communicate_gpib2_scontroller: Parameter = self.add_parameter(
            "system_communicate_gpib2_scontroller",
            set_cmd=":SYSTem:COMMunicate:GP-IB2:SCONtroller {}",
            get_cmd=":SYSTem:COMMunicate:GP-IB2:SCONtroller?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """GP-IB2 system-controller mode (on/off)"""

        self.system_communicate_gpib2_tls_address: Parameter = self.add_parameter(
            "system_communicate_gpib2_tls_address",
            set_cmd=":SYSTem:COMMunicate:GP-IB2:TLS:ADDRess {}",
            get_cmd=":SYSTem:COMMunicate:GP-IB2:TLS:ADDRess?",
            vals=Ints(0, 30),
            get_parser=int,
        )
        """GP-IB2 address of the tunable laser source used for synchronized sweeps"""

        self.system_communicate_lockout: Parameter = self.add_parameter(
            "system_communicate_lockout",
            set_cmd=":SYSTem:COMMunicate:LOCKout {}",
            get_cmd=":SYSTem:COMMunicate:LOCKout?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Remote lockout of the front panel (on/off)"""

        self.system_communicate_rmonitor: Parameter = self.add_parameter(
            "system_communicate_rmonitor",
            set_cmd=":SYSTem:COMMunicate:RMONitor {}",
            get_cmd=":SYSTem:COMMunicate:RMONitor?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Remote-monitor (network) mode (on/off)"""

        self.system_date: Parameter = self.add_parameter(
            "system_date",
            set_cmd=":SYSTem:DATE {}",
            get_cmd=":SYSTem:DATE?",
        )
        """System date as ``yyyy,mm,dd``"""

        self.system_display_transparent: Parameter = self.add_parameter(
            "system_display_transparent",
            set_cmd=":SYSTem:DISPlay:TRANsparent {}",
            get_cmd=":SYSTem:DISPlay:TRANsparent?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Transparent dialog windows (on/off)"""

        self.system_display_uncal: Parameter = self.add_parameter(
            "system_display_uncal",
            set_cmd=":SYSTem:DISPlay:UNCal {}",
            get_cmd=":SYSTem:DISPlay:UNCal?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Display of the 'UNCAL' warning (on/off)"""

        self.system_error: Parameter = self.add_parameter(
            "system_error",
            get_cmd=":SYSTem:ERRor?",
            snapshot_value=False,
        )
        """Oldest entry in the instrument error queue (code and message)"""

        self.system_fspeed: Parameter = self.add_parameter(
            "system_fspeed",
            get_cmd=":SYSTem:FSPeed?",
        )
        """Sampling/measurement front-end speed grade"""

        self.system_grid: Parameter = self.add_parameter(
            "system_grid",
            set_cmd=":SYSTem:GRID {}",
            get_cmd=":SYSTem:GRID?",
            val_mapping={
                "12.5GHZ": 0,
                "25GHZ": 1,
                "50GHZ": 2,
                "100GHZ": 3,
                "200GHZ": 4,
                "CUSTOM": 5,
            },
        )
        """WDM ITU grid spacing"""

        self.system_grid_custom_spacing: Parameter = self.add_parameter(
            "system_grid_custom_spacing",
            set_cmd=":SYSTem:GRID:CUSTom:SPACing {}GHZ",
            get_cmd=":SYSTem:GRID:CUSTom:SPACing?",
            get_parser=float,
            unit="GHz",
        )
        """Custom WDM grid spacing (GHz)"""

        self.system_grid_custom_start: Parameter = self.add_parameter(
            "system_grid_custom_start",
            set_cmd=":SYSTem:GRID:CUSTom:STARt {}M",
            get_cmd=":SYSTem:GRID:CUSTom:STARt?",
            get_parser=float,
            unit="m",
        )
        """Custom WDM grid start wavelength (m)"""

        self.system_grid_custom_stop: Parameter = self.add_parameter(
            "system_grid_custom_stop",
            set_cmd=":SYSTem:GRID:CUSTom:STOP {}M",
            get_cmd=":SYSTem:GRID:CUSTom:STOP?",
            get_parser=float,
            unit="m",
        )
        """Custom WDM grid stop wavelength (m)"""

        self.system_grid_reference: Parameter = self.add_parameter(
            "system_grid_reference",
            set_cmd=":SYSTem:GRID:REFerence {}M",
            get_cmd=":SYSTem:GRID:REFerence?",
            get_parser=float,
            unit="m",
        )
        """WDM grid reference wavelength (m)"""

        self.system_time: Parameter = self.add_parameter(
            "system_time",
            set_cmd=":SYSTem:TIME {}",
            get_cmd=":SYSTem:TIME?",
        )
        """System time as ``hh,mm,ss``"""

        self.system_version: Parameter = self.add_parameter(
            "system_version",
            get_cmd=":SYSTem:VERSion?",
        )
        """Instrument firmware version"""

        # TRACe Sub System Commands — Template / GO-NOGO

        self.template_gonogo: Parameter = self.add_parameter(
            "template_gonogo",
            set_cmd=":TRACe:TEMPlate:GONogo {}",
            get_cmd=":TRACe:TEMPlate:GONogo?",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Template GO/NO-GO judgement (on/off)"""

        self.template_level_shift: Parameter = self.add_parameter(
            "template_level_shift",
            set_cmd=":TRACe:TEMPlate:LEVel:SHIFt {}",
            get_cmd=":TRACe:TEMPlate:LEVel:SHIFt?",
            get_parser=float,
            unit="dB",
        )
        """Template level shift (dB)"""

        self.template_result: Parameter = self.add_parameter(
            "template_result",
            get_cmd=":TRACe:TEMPlate:RESult?",
        )
        """Template GO/NO-GO judgement result"""

        self.template_ttype: Parameter = self.add_parameter(
            "template_ttype",
            set_cmd=":TRACe:TEMPlate:TTYPe {}",
            get_cmd=":TRACe:TEMPlate:TTYPe?",
            val_mapping={
                "UPPER": 0,
                "LOWER": 1,
                "UPPER_AND_LOWER": 2,
            },
        )
        """Template limit type (upper, lower, or both)"""

        self.template_wavelength_shift: Parameter = self.add_parameter(
            "template_wavelength_shift",
            set_cmd=":TRACe:TEMPlate:WAVelength:SHIFt {}M",
            get_cmd=":TRACe:TEMPlate:WAVelength:SHIFt?",
            get_parser=float,
            unit="m",
        )
        """Template wavelength shift (m)"""

        # TRIGger Sub System Commands

        self.trigger_delay: Parameter = self.add_parameter(
            "trigger_delay",
            set_cmd=":TRIGger:DELay {}",
            get_cmd=":TRIGger:DELay?",
            get_parser=float,
            unit="s",
        )
        """Delay between the trigger event and the start of the sweep (s)"""

        self.trigger_gate_time: Parameter = self.add_parameter(
            "trigger_gate_time",
            set_cmd=":TRIGger:GATE:TIMe {}",
            get_cmd=":TRIGger:GATE:TIMe?",
            get_parser=float,
            unit="s",
        )
        """Gate open time in gated-sweep mode (s)"""

        self.trigger_gate_logic: Parameter = self.add_parameter(
            "trigger_gate_logic",
            set_cmd=":TRIGger:GATE:LOGic {}",
            get_cmd=":TRIGger:GATE:LOGic?",
            val_mapping={
                "POSITIVE": 0,
                "NEGATIVE": 1,
            },
        )
        """Gate signal logic polarity (positive or negative)"""

        self.trigger_gate_slope: Parameter = self.add_parameter(
            "trigger_gate_slope",
            set_cmd=":TRIGger:GATE:SLOPe {}",
            get_cmd=":TRIGger:GATE:SLOPe?",
            val_mapping={
                "RISE": 0,
                "FALL": 1,
            },
        )
        """Gate trigger edge (rising or falling)"""

        self.trigger_gate_state: Parameter = self.add_parameter(
            "trigger_gate_state",
            set_cmd=":TRIGger:GATE:STATe {}",
            get_cmd=":TRIGger:GATE:STATe?",
            val_mapping={
                "OFF": 0,
                "ON": 1,
                "PEAK_HOLD": 2,
            },
        )
        """Gated-sweep mode (off, on, or peak-hold)"""

        self.trigger_input: Parameter = self.add_parameter(
            "trigger_input",
            set_cmd=":TRIGger:INPut {}",
            get_cmd=":TRIGger:INPut?",
            val_mapping={
                "EXTERNAL_TRIGGER": 0,
                "SAMPLE_TRIGGER": 1,
                "SWEEP_ENABLE": 2,
            },
        )
        """External input mode (external trigger, sampling trigger or sweep enable)"""

        self.trigger_output: Parameter = self.add_parameter(
            "trigger_output",
            set_cmd=":TRIGger:OUTPut {}",
            get_cmd=":TRIGger:OUTPut?",
            val_mapping={
                "OFF": 0,
                "SWEEP_STATUS": 1,
            },
        )
        """Trigger output mode (off or sweep-status)"""

        self.trigger_phold_htime: Parameter = self.add_parameter(
            "trigger_phold_htime",
            set_cmd=":TRIGger:PHOLd:HTIMe {}",
            get_cmd=":TRIGger:PHOLd:HTIMe?",
            get_parser=float,
            unit="s",
        )
        """Peak-hold time in peak-hold gate mode (s)"""

        # UNIT Sub System Commands

        self.unit_power_digit: Parameter = self.add_parameter(
            "unit_power_digit",
            set_cmd=":UNIT:POWer:DIGit {}",
            get_cmd=":UNIT:POWer:DIGit?",
            vals=Ints(1, 3),
            get_parser=int,
        )
        """Number of significant digits for power readouts (1–3)"""

        self.unit_x: Parameter = self.add_parameter(
            "unit_x",
            set_cmd=":UNIT:X {}",
            get_cmd=":UNIT:X?",
            val_mapping=self._x_unit_val_mapping(),
        )
        """X-axis unit (wavelength or frequency; wavenumber on AQ6375/AQ6375B)"""


    # Internal helpers

    def _get_self_test(self) -> int:
        """Query ``*TST?`` with a temporarily extended VISA timeout.

        The instrument self-test runs for several seconds, well beyond the
        default VISA timeout; querying it with the default timeout raises
        ``VI_ERROR_TMO`` and can leave the session in a bad state.
        """
        old_timeout = self.visa_handle.timeout
        self.visa_handle.timeout = 120000  # ms
        try:
            return int(self.ask("*TST?"))
        finally:
            self.visa_handle.timeout = old_timeout

    def _x_unit_val_mapping(self) -> "dict[str, int]":
        """val_mapping for the X-axis unit; wavenumber only on AQ6375/AQ6375B."""
        mapping = {"WAVELENGTH": 0, "FREQUENCY": 1}
        if self.model in ("AQ6375", "AQ6375B"):
            mapping["WNUMBER"] = 2
        return mapping

    # Common Commands (IEEE 488.2)

    def clear_status(self) -> None:
        """Clear all event status registers and queues except the output queue"""
        self.write("*CLS")

    def reset(self) -> None:
        """Reset the instrument to its default state"""
        self.write("*RST")

    def trigger(self) -> None:
        """Force a single trigger sweep regardless of trigger mode"""
        self.write("*TRG")

    def wait(self) -> None:
        """Wait until all previously issued commands have completed"""
        self.write("*WAI")

    # ABORt Sub System Command

    def stop(self) -> None:
        """Stops operations such as measurements and calibration"""
        self.write(":ABORt")

    # CALCulate Sub System Commands — Line marker actions

    def line_marker_all_off(self) -> None:
        """Turn off all line markers (`:CALCulate:LMARker:AOFF`)."""
        self.write(":CALCulate:LMARker:AOFF")

    def line_marker_sspan(self) -> None:
        """Set the sweep span to the L1–L2 line-marker spacing."""
        self.write(":CALCulate:LMARker:SSPan")

    def line_marker_szspan(self) -> None:
        """Set the zoom span to the L1–L2 line-marker spacing."""
        self.write(":CALCulate:LMARker:SZSPan")

    def line_marker_set_x(self, marker: int, value: float) -> None:
        """Set wavelength/frequency line marker ``marker`` (1 or 2)."""
        self.write(f":CALCulate:LMARker:X {marker},{value}")

    def line_marker_set_y(self, marker: int, value: float) -> None:
        """Set level line marker ``marker`` (3 or 4)."""
        self.write(f":CALCulate:LMARker:Y {marker},{value}")

    # CALCulate Sub System Commands — Manual marker actions

    def clear_all_markers(self) -> None:
        """Turn off all manual markers (`:CALCulate:MARKer:AOFF`)."""
        self.write(":CALCulate:MARKer:AOFF")

    def marker_maximum(self) -> None:
        """Move the active marker to the peak level."""
        self.write(":CALCulate:MARKer:MAXimum")

    def marker_maximum_left(self) -> None:
        """Move the active marker to the next peak to the left."""
        self.write(":CALCulate:MARKer:MAXimum:LEFT")

    def marker_maximum_next(self) -> None:
        """Move the active marker to the next-highest peak."""
        self.write(":CALCulate:MARKer:MAXimum:NEXT")

    def marker_maximum_right(self) -> None:
        """Move the active marker to the next peak to the right."""
        self.write(":CALCulate:MARKer:MAXimum:RIGHt")

    def marker_maximum_scenter(self) -> None:
        """Set the peak wavelength to the measurement center ('peak to center')."""
        self.write(":CALCulate:MARKer:MAXimum:SCENter")

    def marker_maximum_srlevel(self) -> None:
        """Set the peak level to the reference level ('peak to reference level')."""
        self.write(":CALCulate:MARKer:MAXimum:SRLevel")

    def marker_maximum_szcenter(self) -> None:
        """Set the peak wavelength to the display center in zoom span."""
        self.write(":CALCulate:MARKer:MAXimum:SZCenter")

    def marker_minimum(self) -> None:
        """Move the active marker to the bottom level."""
        self.write(":CALCulate:MARKer:MINimum")

    def marker_minimum_left(self) -> None:
        """Move the active marker to the next bottom to the left."""
        self.write(":CALCulate:MARKer:MINimum:LEFT")

    def marker_minimum_next(self) -> None:
        """Move the active marker to the next-lowest bottom."""
        self.write(":CALCulate:MARKer:MINimum:NEXT")

    def marker_minimum_right(self) -> None:
        """Move the active marker to the next bottom to the right."""
        self.write(":CALCulate:MARKer:MINimum:RIGHt")

    def marker_scenter(self) -> None:
        """Set the active marker wavelength to the measurement center."""
        self.write(":CALCulate:MARKer:SCENter")

    def marker_srlevel(self) -> None:
        """Set the active marker level to the reference level."""
        self.write(":CALCulate:MARKer:SRLevel")

    def marker_set_state(self, marker: int, state: bool) -> None:
        """Enable or disable moving marker ``marker``."""
        self.write(f":CALCulate:MARKer:STATe {marker},{1 if state else 0}")

    def marker_szcenter(self) -> None:
        """Set the active marker wavelength to the display center in zoom span."""
        self.write(":CALCulate:MARKer:SZCenter")

    def marker_set_x(self, marker: int, value: float) -> None:
        """Set the X position (wavelength/frequency) of marker ``marker``."""
        self.write(f":CALCulate:MARKer:X {marker},{value}")

    def marker_get_x(self, marker: int) -> float:
        """Query the X position of marker ``marker``."""
        return float(self.ask(f":CALCulate:MARKer:X? {marker}"))

    def marker_get_y(self, marker: int) -> float:
        """Query the Y value (level) of marker ``marker``."""
        return float(self.ask(f":CALCulate:MARKer:Y? {marker}"))

    # CALibration Sub System Commands

    def align(self) -> None:
        """Perform the standard (internal) optical alignment adjustment."""
        self.write(":CALibration:ALIGn")

    def align_external(self) -> None:
        """Perform optical alignment using an external light source."""
        self.write(":CALibration:ALIGn:EXTernal")

    def align_internal(self) -> None:
        """Perform optical alignment using the internal reference source."""
        self.write(":CALibration:ALIGn:INTernal")

    def calibrate_bandwidth(self) -> None:
        """Execute the resolution-bandwidth calibration."""
        self.write(":CALibration:BANDwidth")

    def calibrate_bandwidth_initialize(self) -> None:
        """Reset the resolution-bandwidth calibration to its factory state."""
        self.write(":CALibration:BANDwidth:INITialize")

    def calibration_power_offset_table(self, index: int, offset: float) -> None:
        """Set an entry in the power-offset calibration table.

        Args:
            index: Table entry index.
            offset: Level offset in dB.
        """
        self.write(f":CALibration:POWer:OFFSet:TABLe {index},{offset}")

    def calibrate_wavelength_external(self) -> None:
        """Execute wavelength calibration using the external reference source."""
        self.write(":CALibration:WAVelength:EXTernal")

    def calibrate_wavelength_internal(self) -> None:
        """Execute wavelength calibration using the internal reference."""
        self.write(":CALibration:WAVelength:INTernal")

    def calibration_wavelength_offset_table(self, index: int, offset: float) -> None:
        """Set an entry in the wavelength-offset calibration table.

        Args:
            index: Table entry index.
            offset: Wavelength offset value.
        """
        self.write(f":CALibration:WAVelength:OFFSet:TABLe {index},{offset}")

    def zero_once(self) -> None:
        """Perform a single monitor-zeroing operation now (`:CALibration:ZERO ONCE`)."""
        self.write(":CALibration:ZERO ONCE")

    # DISPlay Sub System Commands

    def display_position(self, trace: str, position: str) -> None:
        """Place ``trace`` in the upper (``UP``) or lower (``LOW``) split window."""
        self.write(f":DISPlay:POSition {trace},{position}")

    def display_text_clear(self) -> None:
        """Clear all display text labels"""
        self.write(":DISPlay:TEXT:CLEar")

    def display_trace_x_initialize(self) -> None:
        """Initialize the display X-axis scale parameters"""
        self.write(":DISPlay:TRACe:X:SCALe:INITialize")

    def display_trace_x_smscale(self) -> None:
        """Sets parameters of the current display scale to the measurement scale"""
        self.write(":DISPLAY:TRACE:X:SMSCALE")

    # INITiate Sub System Command

    def immediate(self) -> None:
        """Makes a sweep"""
        self.write(":INITIATE")

    def auto(self) -> None:
        """Equivalent to the OSA front-panel `AUTO` button: set sweep mode to AUTO and trigger an immediate sweep."""
        self.sweep_mode("AUTO")
        self.immediate()

    def repeat(self) -> None:
        """Equivalent to the OSA front-panel `REPEAT` button: set sweep mode to REPEAT and trigger continuous sweeps."""
        self.sweep_mode("REPEAT")
        self.immediate()

    def single(self) -> None:
        """Equivalent to the OSA front-panel `SINGLE` button: set sweep mode to SINGLE and perform one sweep."""
        self.sweep_mode("SINGLE")
        self.immediate()

    # MEMory Sub System Commands

    def memory_clear(self, index: int) -> None:
        """Clear the internal trace-memory entry at ``index``."""
        self.write(f":MEMory:CLEar {index}")

    def memory_empty(self, index: int) -> int:
        """Return whether the internal trace-memory entry at ``index`` is empty."""
        return int(self.ask(f":MEMory:EMPty? {index}"))

    def memory_load(self, index: int, trace: str) -> None:
        """Load internal memory ``index`` into ``trace`` (TRA–TRG)."""
        self.write(f":MEMory:LOAD {index},{trace}")

    def memory_store(self, index: int, trace: str) -> None:
        """Store ``trace`` (TRA–TRG) into internal memory ``index``."""
        self.write(f":MEMory:STORe {index},{trace}")

    # MMEMory Sub System Commands

    @staticmethod
    def _medium(medium: "str | None") -> str:
        """Build the optional ``,INTernal|EXTernal`` medium suffix."""
        return f",{medium}" if medium is not None else ""

    def mmemory_auto_name(self, mode: str) -> None:
        """Set the automatic file-naming scheme (``NUMBer`` or ``DATE``)."""
        self.write(f":MMEMory:ANAMe {mode}")

    def mmemory_catalog(self, medium: "str | None" = None) -> str:
        """Return the file catalog of the current (or given) storage medium."""
        arg = f" {medium}" if medium is not None else ""
        return self.ask(f":MMEMory:CATalog?{arg}")

    def mmemory_change_directory(self, name: str) -> None:
        """Change the current working directory."""
        self.write(f':MMEMory:CDIRectory "{name}"')

    def mmemory_change_drive(self, drive: str) -> None:
        """Select the current drive (``INTernal`` or ``EXTernal``)."""
        self.write(f":MMEMory:CDRive {drive}")

    def mmemory_copy(
            self,
            source: str,
            destination: str,
            source_medium: "str | None" = None,
            destination_medium: "str | None" = None,
    ) -> None:
        """Copy a file between locations/media."""
        self.write(
            f':MMEMory:COPY "{source}"{self._medium(source_medium)},'
            f'"{destination}"{self._medium(destination_medium)}'
        )

    def mmemory_data(self, filename: str, medium: "str | None" = None) -> str:
        """Return the raw contents of ``filename``."""
        return self.ask(f':MMEMory:DATA? "{filename}"{self._medium(medium)}')

    def mmemory_delete(self, filename: str, medium: "str | None" = None) -> None:
        """Delete ``filename`` from the given medium."""
        self.write(f':MMEMory:DELete "{filename}"{self._medium(medium)}')

    def mmemory_make_directory(self, name: str, medium: "str | None" = None) -> None:
        """Create a directory on the given medium."""
        self.write(f':MMEMory:MDIRectory "{name}"{self._medium(medium)}')

    def mmemory_remove(self) -> None:
        """Safely unmount the external storage medium."""
        self.write(":MMEMory:REMove")

    def mmemory_rename(self, new_name: str, old_name: str, medium: "str | None" = None) -> None:
        """Rename ``old_name`` to ``new_name`` on the given medium."""
        self.write(f':MMEMory:REName "{new_name}","{old_name}"{self._medium(medium)}')

    def mmemory_load_all_trace(self, filename: str, medium: "str | None" = None) -> None:
        """Load an all-trace (.CSV/.BIN) file."""
        self.write(f':MMEMory:LOAD:ATRace "{filename}"{self._medium(medium)}')

    def mmemory_load_data_logging(self, filename: str, medium: "str | None" = None) -> None:
        """Load a data-logging file."""
        self.write(f':MMEMory:LOAD:DLOGing "{filename}"{self._medium(medium)}')

    def mmemory_load_memory(self, index: int, filename: str, medium: "str | None" = None) -> None:
        """Load ``filename`` into internal memory ``index``."""
        self.write(f':MMEMory:LOAD:MEMory {index},"{filename}"{self._medium(medium)}')

    def mmemory_load_program(self, index: int, filename: str, medium: "str | None" = None) -> None:
        """Load a program file into program slot ``index``."""
        self.write(f':MMEMory:LOAD:PROGram {index},"{filename}"{self._medium(medium)}')

    def mmemory_load_setting(self, filename: str, medium: "str | None" = None) -> None:
        """Load an instrument-settings file."""
        self.write(f':MMEMory:LOAD:SETTing "{filename}"{self._medium(medium)}')

    def mmemory_load_template(self, template: str, filename: str, medium: "str | None" = None) -> None:
        """Load a template file into the given template."""
        self.write(f':MMEMory:LOAD:TEMPlate {template},"{filename}"{self._medium(medium)}')

    def mmemory_load_trace(self, trace: str, filename: str, medium: "str | None" = None) -> None:
        """Load ``filename`` into ``trace`` (TRA–TRG)."""
        self.write(f':MMEMory:LOAD:TRACe {trace},"{filename}"{self._medium(medium)}')

    def mmemory_store_analysis_result(self, filename: str, medium: "str | None" = None) -> None:
        """Store the analysis-result table to a file."""
        self.write(f':MMEMory:STORe:ARESult "{filename}"{self._medium(medium)}')

    def mmemory_store_all_trace(self, filename: str, medium: "str | None" = None) -> None:
        """Store all traces to a file."""
        self.write(f':MMEMory:STORe:ATRace "{filename}"{self._medium(medium)}')

    def mmemory_store_data(self, filename: str, medium: "str | None" = None) -> None:
        """Store measurement data to a file (format set by `mmemory_store_data_type`)."""
        self.write(f':MMEMory:STORe:DATA "{filename}"{self._medium(medium)}')

    def mmemory_store_data_item(self, item: str, state: bool) -> None:
        """Enable/disable an item in stored data (DATE/LABel/DATA/CONDition/TRACe)."""
        self.write(f":MMEMory:STORe:DATA:ITEM {item},{1 if state else 0}")

    def mmemory_store_data_mode(self, mode: str) -> None:
        """Set the data-store mode (``ADD`` or ``OVER``)."""
        self.write(f":MMEMory:STORe:DATA:MODE {mode}")

    def mmemory_store_data_type(self, data_type: str) -> None:
        """Set the data-store file type (``CSV`` or ``DT``)."""
        self.write(f":MMEMory:STORe:DATA:TYPE {data_type}")

    def mmemory_store_data_logging(self, filename: str, medium: "str | None" = None) -> None:
        """Store the data-logging result to a file."""
        self.write(f':MMEMory:STORe:DLOGging "{filename}"{self._medium(medium)}')

    def mmemory_store_data_logging_csave(self, state: bool) -> None:
        """Enable/disable continuous saving during data logging."""
        self.write(f":MMEMory:STORe:DLOGging:CSAVe {1 if state else 0}")

    def mmemory_store_data_logging_tsave(self, state: bool) -> None:
        """Enable/disable time-stamp saving during data logging."""
        self.write(f":MMEMory:STORe:DLOGging:TSAVe {1 if state else 0}")

    def mmemory_store_graphics(
            self, color: str, image_format: str, filename: str, medium: "str | None" = None
    ) -> None:
        """Store a screenshot (color: ``B&W``/``COLor``/``PCOLor``; format: ``BMP``/``TIFF``)."""
        self.write(
            f':MMEMory:STORe:GRAPhics {color},{image_format},"{filename}"{self._medium(medium)}'
        )

    def mmemory_store_memory(
            self, index: int, data_format: str, filename: str, medium: "str | None" = None
    ) -> None:
        """Store internal memory ``index`` to a file (format ``BI`` or ``CSV``)."""
        self.write(
            f':MMEMory:STORe:MEMory {index},{data_format},"{filename}"{self._medium(medium)}'
        )

    def mmemory_store_program(self, index: int, filename: str, medium: "str | None" = None) -> None:
        """Store program slot ``index`` to a file."""
        self.write(f':MMEMory:STORe:PROGram {index},"{filename}"{self._medium(medium)}')

    def mmemory_store_setting(self, filename: str, medium: "str | None" = None) -> None:
        """Store the current instrument settings to a file."""
        self.write(f':MMEMory:STORe:SETTing "{filename}"{self._medium(medium)}')

    def mmemory_store_template(self, template: str, filename: str, medium: "str | None" = None) -> None:
        """Store the given template to a file."""
        self.write(f':MMEMory:STORe:TEMPlate {template},"{filename}"{self._medium(medium)}')

    def mmemory_store_trace(
            self, trace: str, data_format: str, filename: str, medium: "str | None" = None
    ) -> None:
        """Store ``trace`` (TRA–TRG) to a file (format ``BIN`` or ``CSV``)."""
        self.write(
            f':MMEMory:STORe:TRACe {trace},{data_format},"{filename}"{self._medium(medium)}'
        )

    # PROGram Sub System Command

    def program_execute(self, index: int) -> None:
        """Execute the stored program at ``index``."""
        self.write(f":PROGram:EXECute {index}")

    # STATus Sub System Commands

    def status_operation_preset(self) -> None:
        """Preset the operation status enable/transition registers."""
        self.write(":STATus:OPERation:PRESet")

    # SYSTem Sub System Commands

    def system_grid_custom_clear_all(self) -> None:
        """Clear all custom WDM grid entries."""
        self.write(":SYSTem:GRID:CUSTom:CLEar:ALL")

    def system_grid_custom_delete(self, grid_number: int) -> None:
        """Delete a custom WDM grid entry by number."""
        self.write(f":SYSTem:GRID:CUSTom:DELete {grid_number}")

    def system_grid_custom_insert(self, value: float) -> None:
        """Insert a wavelength into the custom WDM grid (m)."""
        self.write(f":SYSTem:GRID:CUSTom:INSert {value}M")

    def system_information(self, kind: int = 0) -> str:
        """Return system information (``kind`` 0 or 1)."""
        return self.ask(f":SYSTem:INFormation? {kind}")

    def system_operator_lock(self, state: bool, password: str) -> None:
        """Enable/disable the operator lock using ``password``."""
        self.write(f':SYSTem:OLOCK {1 if state else 0},"{password}"')

    def system_preset(self) -> None:
        """Reset the instrument to its preset (initialized) state."""
        self.write(":SYSTem:PRESet")

    # TRACe Sub System Commands

    def trace_copy(self, source: str, destination: str) -> None:
        """Copy trace ``source`` to ``destination`` (TRA–TRG)."""
        self.write(f":TRACe:COPY {source},{destination}")

    def delete_all_traces(self) -> None:
        """Delete the data of all traces."""
        self.write(":TRACe:DELete:ALL")

    def trace_power_density(self, trace: str, bandwidth: float) -> str:
        """Query the power spectral density of ``trace`` normalized to ``bandwidth`` (m)."""
        return self.ask(f":TRACe:PDENsity? {trace},{bandwidth}")

    def template_data(self, template: str, wavelength: float, level: float) -> None:
        """Append a (wavelength, level) point to ``template``."""
        self.write(f":TRACe:TEMPlate:DATA {template},{wavelength},{level}")

    def template_all_delete(self, template: str) -> None:
        """Delete all points of ``template``."""
        self.write(f":TRACe:TEMPlate:ADELete {template}")

    def template_edit_type(self, template: str, edit_type: str) -> None:
        """Set the edit type of ``template`` (``NONE``, ``A`` or ``B``)."""
        self.write(f":TRACe:TEMPlate:ETYPe {template},{edit_type}")

    def template_mode(self, template: str, mode: str) -> None:
        """Set the level mode of ``template`` (``ABSolute`` or ``RELative``)."""
        self.write(f":TRACe:TEMPlate:MODE {template},{mode}")

    def template_display(self, template: str, state: bool) -> None:
        """Show or hide ``template`` on screen."""
        self.write(f":TRACe:TEMPlate:DISPlay {template},{1 if state else 0}")
