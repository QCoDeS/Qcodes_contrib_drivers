import time
from typing import Any

import numpy as np
from qcodes import validators as vals
from qcodes import VisaInstrument
from qcodes.parameters import Parameter, create_on_off_val_mapping
from qcodes.validators import Enum, Numbers


class KeySight_E5080B(VisaInstrument):
    """
    Qcodes driver for the Keysight E5080B Vector Network Analyzer
    """
    time.sleep(5)  # Required sleep to ensure the instruments can start being queried

    def __init__(self, name: str, address: str, **kwargs: Any) -> None:
        super().__init__(name, address, terminator="\n", **kwargs)

        # Setting frequency range
        min_freq = 100e3
        max_freq = 53e9

        # Sets the start frequency of the analyzer.
        self.start_freq: Parameter = self.add_parameter(
            "start_freq",
            label="Start Frequency",
            get_cmd="SENS:FREQ:STAR?",
            get_parser=float,
            set_cmd="SENS:FREQ:STAR {}",
            unit="Hz",
            vals=Numbers(min_value=min_freq, max_value=max_freq),
        )
        """Parameter start_freq"""

        # Sets the stop frequency of the analyzer.
        self.stop_freq: Parameter = self.add_parameter(
            "stop_freq",
            label="Stop Frequency",
            get_cmd="SENS:FREQ:STOP?",
            get_parser=float,
            set_cmd="SENS:FREQ:STOP {}",
            unit="Hz",
            vals=Numbers(min_value=min_freq, max_value=max_freq),
        )
        """Parameter stop_freq"""

        # Sets the center frequency of the analyzer.
        self.center_freq: Parameter = self.add_parameter(
            "center_freq",
            label="Center Frequency",
            get_cmd="SENS:FREQ:CENT?",
            get_parser=float,
            set_cmd="SENS:FREQ:CENT {}",
            unit="Hz",
            vals=Numbers(min_value=min_freq, max_value=max_freq),
        )
        """Parameter center_freq"""

        # Sets the frequency span of the analyzer.
        self.span: Parameter = self.add_parameter(
            "span",
            label="Frequency Span",
            get_cmd="SENS:FREQ:SPAN?",
            get_parser=float,
            set_cmd="SENS:FREQ:SPAN {}",
            unit="Hz",
        )
        """Parameter span"""

        # Sets the Continuous Wave (or Fixed) frequency. Must also send SENS:SWEEP:TYPE CW to put the analyzer into CW sweep mode.
        self.cw: Parameter = self.add_parameter(
            "cw",
            label="CW Frequency",
            get_cmd="SENS:FREQ:CW?",
            get_parser=float,
            set_cmd="SENS:FREQ:CW {}",
            unit="Hz",
        )
        """Parameter Continuous wave"""

        # Sets the number of data points for the measurement.
        self.points: Parameter = self.add_parameter(
            "points",
            label="Points",
            get_cmd="SENS:SWE:POIN?",
            get_parser=int,
            set_cmd="SENS:SWE:POIN {}",
            unit="",
            vals=Numbers(min_value=1, max_value=100003),
        )
        """Parameter points"""

        # Sets the RF power output level.
        self.source_power: Parameter = self.add_parameter(
            "source_power",
            label="source_power",
            unit="dBm",
            get_cmd="SOUR:POW?",
            set_cmd="SOUR:POW {}",
            get_parser=float,
            vals=Numbers(min_value=-100, max_value=20),
        )
        """Parameter source_power"""

        # Sets the bandwidth of the digital IF filter to be used in the measurement.
        self.if_bandwidth: Parameter = self.add_parameter(
            "if_bandwidth",
            label="if_bandwidth",
            unit="Hz",
            get_cmd="SENS:BWID?",
            set_cmd="SENS:BWID {}",
            get_parser=float,
            vals=Numbers(min_value=1, max_value=15e6),
        )
        """Parameter if_bandwidth"""

        # Sets the type of analyzer sweep mode. First set sweep type, then set sweep parameters such as frequency or power settings. Default is LIN
        self.sweep_type: Parameter = self.add_parameter(
            "sweep_type",
            label="Type",
            get_cmd="SENS:SWE:TYPE?",
            set_cmd="SENS:SWE:TYPE {}",
            vals=Enum("LIN", "LOG", "POW", "CW", "SEGM"),
        )
        """Parameter sweep_type"""

        # Sets the number of trigger signals the specified channel will ACCEPT. Default is CONT.
        self.sweep_mode: Parameter = self.add_parameter(
            "sweep_mode",
            label="Type",
            get_cmd="SENS:SWE:MODE?",
            set_cmd="SENS:SWE:MODE {}",
            vals=Enum("HOLD", "CONT", "GRO", "SING"),
        )
        """Parameter sweep_mode"""

        # Sets the trigger count (groups) for the specified channel. Set trigger mode to group after setting this count.
        # Default is 1. 1 is the same as SING trigger
        self.sweep_group_count: Parameter = self.add_parameter(
            "sweep_group_count",
            label="sweep_group_count",
            get_cmd="SENS:SWE:GRO:COUN?",
            set_cmd="SENS:SWE:GRO:COUN {}",
            get_parser=int,
            vals=Numbers(min_value=1, max_value=2e6),
        )
        """Parameter sweep_group_count"""

        # Sets the source of the sweep trigger signal. Default is IMMediate.
        self.trigger_source: Parameter = self.add_parameter(
            "trigger_source",
            label="Trigger Source",
            get_cmd="TRIG:SOUR?",
            set_cmd="TRIG:SOUR {}",
            vals=Enum("EXT", "IMM", "MAN"),
        )
        """Trigger Source"""

        # Specifies the type of EXTERNAL trigger input detection used to listen for signals on the Meas Trig IN connectors. Default is LEV.
        self.trigger_type: Parameter = self.add_parameter(
            "trigger_type",
            label="Trigger Type",
            get_cmd="TRIG:TYPE?",
            set_cmd="TRIG:TYPE {}",
            vals=Enum("EDGE", "LEV"),
        )
        """Trigger Type"""

        # Specifies the polarity expected by the external trigger input circuitry. Also specify TRIG:TYPE (Level |Edge).
        self.trigger_slope: Parameter = self.add_parameter(
            "trigger_slope",
            label="Trigger Slope",
            get_cmd="TRIG:SLOP?",
            set_cmd="TRIG:SLOP {}",
            vals=Enum("POS", "NEG"),
        )
        """Trigger Slope"""

        # Determines what happens to an EDGE trigger signal if it occurs before the VNA is ready to be triggered. (LEVEL trigger signals are always ignored.)
        self.accept_trigger_before_armed: Parameter = self.add_parameter(
            "accept_trigger_before_armed",
            label="Accept Trigger Before Armed",
            get_cmd="CONT:SIGN:TRIG:ATBA?",
            set_cmd="CONT:SIGN:TRIG:ATBA {}",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Accept Trigger Before Armed"""

        # Sets the time the analyzer takes to complete one sweep.
        self.sweep_time: Parameter = self.add_parameter(
            "sweep_time",
            label="sweep_time",
            unit="s",
            get_parser=float,
            get_cmd="SENS:SWE:TIME?",
            set_cmd="SENS:SWE:TIME {}",
        )
        """Parameter sweep_time"""

        # Turns the automatic sweep time function ON or OFF.
        self.sweep_time_auto: Parameter = self.add_parameter(
            "sweep_time_auto",
            label="sweep_time_auto",
            get_parser=float,
            get_cmd="SENS:SWE:TIME:AUTO?",
            set_cmd="SENS:SWE:TIME:AUTO {}",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Parameter sweep_time_auto"""

        # Set/get a measurement parameter for the specified measurement.
        self.scattering_parameter: Parameter = self.add_parameter(
            "scattering_parameter",
            label="scattering_parameter",
            get_cmd="CALC:MEAS:PAR?",
            set_cmd="CALC:MEAS:PAR {}",
            vals=vals.Enum("S11", "S12", "S21", "S22"),
        )
        """Parameter scattering_parameter"""

        # Turns trace averaging ON or OFF. Default OFF
        self.averages_enabled: Parameter = self.add_parameter(
            "averages_enabled",
            label="Averages Enabled",
            get_cmd="SENS:AVER?",
            set_cmd="SENS:AVER {}",
            val_mapping=create_on_off_val_mapping(on_val="1", off_val="0"),
        )
        """Parameter averages_enabled"""

        # Sets the number of measurements to combine for an average. Must also set SENS:AVER[:STATe] ON
        self.averages_count: Parameter = self.add_parameter(
            "averages_count",
            label="Averages Count",
            get_cmd="SENS:AVER:COUN?",
            get_parser=int,
            set_cmd="SENS:AVER:COUN {:d}",
            vals=Numbers(min_value=1, max_value=65536),
        )
        """Parameter averages count"""

        # Sets the type of averaging to perform: Point or Sweep (default is sweep).
        self.averages_mode: Parameter = self.add_parameter(
            "averages_mode",
            label="Averages Mode",
            get_cmd="SENS:AVER:MODE?",
            set_cmd="SENS:AVER:MODE {}",
            vals=Enum("POIN", "SWE"),
        )
        """Parameter averages mode"""

        # Sets the data format for transferring measurement data and frequency data. Default is ASCii,0.
        self.format_data: Parameter = self.add_parameter(
            "format_data",
            label="Format Data",
            get_cmd="FORM:DATA?",
            set_cmd="FORM:DATA {}",
            vals=Enum("REAL,32", "REAL,64", "ASCii,0"),
        )
        """Parameter averages mode"""

        # Turns RF power from the source ON or OFF.
        self.rf_on: Parameter = self.add_parameter(
            "rf_on",
            label="RF ON",
            get_cmd="OUTP?",
            set_cmd="OUTP {}",
            val_mapping=create_on_off_val_mapping(on_val="1", off_val="0"),
        )
        """Parameter RF Power Source"""

        # Set the byte order used for GPIB data transfer.
        # Some computers read data from the analyzer in the reverse order. This command is only implemented if FORMAT:DATA is set to :REAL.
        # Default is NORM
        self.format_border: Parameter = self.add_parameter(
            "format_border",
            label="Format Border",
            get_cmd="FORM:BORD?",
            set_cmd="FORM:BORD {}",
            vals=Enum("NORM", "SWAP"),
        )
        """Parameter Format Border"""

        # Status Operation
        # Summarizes conditions in the Averaging and Operation:Define:User<1|2|3> event registers.
        self.operation_status: Parameter = self.add_parameter(
            "operation_status",
            label="Operation Status",
            get_cmd="STAT:OPER:COND?",
            get_parser=int,
        )
        """Status Operation"""

        # Clear averages
        # Clears and restarts averaging of the measurement data. Does NOT apply to point averaging.
        self.add_function("clear_averages", call_cmd="SENS:AVER:CLE")

        # Clear Status
        # Clears the instrument status byte by emptying the error queue and clearing all event registers. Also cancels any preceding *OPC command or query.
        self.add_function("cls", call_cmd="*CLS")

        # Operation complete command
        # Generates the OPC message in the standard event status register when all pending overlapped operations have been completed (for example, a sweep, or a Default).
        self.add_function("opc", call_cmd="*OPC")

        # System Reset
        # Deletes all traces, measurements, and windows.
        self.add_function("system_reset", call_cmd="SYST:PRES")

    def get_data(self):
        """Retrieve the complex measurement data"""
        return self.visa_handle.query_binary_values("CALC:MEAS:DATA:SDAT?")

    def get_frequencies(self):
        """return freqpoints"""
        self.format_data("REAL,64")  # recommended to avoid frequency rounding errors
        return np.array(self.visa_handle.query_binary_values("CALC:MEAS:X?"))
