from time import sleep, time
import numpy as np
import pyvisa
import logging
import ctypes  # only for DLL-based instrument
import qcodes as qc
from typing import Any, Callable, TypeVar, Union
from qcodes.utils.validators import Bool, Enum, Ints, MultiType, Numbers

from qcodes.instrument import (
    Instrument,
    VisaInstrument,
    ManualParameter,
    MultiParameter,
    InstrumentChannel,
    InstrumentModule,
)
from qcodes.utils import validators as vals

from qcodes.instrument.parameter import Parameter

class mercury(VisaInstrument):
    """
    QCoDeS driver for the dual channel sourcemeter PI Mercury Motor controller
    """

    def __init__(self, name: str, address: str, **kwargs: Any):       
        # supplying the terminator means you don't need to remove it from every response
        super().__init__(name, address, terminator='\n', **kwargs)

    # The following parameters include all those described in section 2.5 of the manual
    # and are sufficient to drive the instrument at a basic level.
    # System related commands or more complicated commands for arbitrary waveforms are not implemented here.
 
    # Driver parameter to ask identity:
        
        self.add_parameter("identity",
                            label="Identity",
                            get_cmd="*IDN?"
                            )

    # Driver parameter to ask register status:
        
        self.add_parameter("status_register",
                            label="Status Register",
                            get_cmd="#4"
                            )
                            
    # Driver parameter to ask if there is any error:
        
        self.add_parameter("error",
                            label="Error",
                            get_cmd="ERR?"
                            )                    
    # Get queries the motion of the axes
        
        self.add_parameter("motion_status",
                            label="Motion Status",
                            get_cmd="#5"
                            )
    # Stop all axes abruptly
        
        self.add_parameter("stop_axes",
                            label="Stop Axes",
                            set_cmd="#24"
                            )
    # Query if Macro is Running
        
        self.add_parameter("query_macro",
                            label="Query Macro",
                            get_cmd="#8"
                            )
    # Get list of available commands
        self.add_parameter("help",
                            label="Get Help",
                            get_cmd="HLP?"
                            )
    # Get current syntax version
        self.add_parameter("syntax_version",
                            label="Get Syntax Version",
                            get_cmd="CSV?"
                            )
    # Request Conroller Ready Status
        self.add_parameter("controller_status",
                            label="Controller ready status",
                            get_cmd="#7"
                            )
    # Get versions of firmware and drivers
        self.add_parameter("get_version",
                            label="Versions of firmware and drivers",
                            get_cmd="VER?"
                            )
    # Halt Motion Smoothly
        self.add_parameter("halt_smoothly",
                            label="Halt motion smoothly",
                            set_cmd="HLT[]"
                            )
    # Go to home position
        self.add_parameter("go_home",
                            label="Go to home position",
                            set_cmd="GOH[]"
                            )
    # Get list of current axis identifiers
    
        self.add_parameter("get_axis",
                            label="List of current axis",
                            get_cmd="SAI?"
                            )
    # Fast referenc move to reference switch 
    
        self.add_parameter("moveto_reference",
                            label="A reference move",
                            set_cmd="FRF[]"
                            )
    # Get servo mode 
    
        self.add_parameter("get_servo",
                            label="get servo mode",
                            get_cmd="SVO?"
                            )
    # Set servo mode 
    
        self.add_parameter("set_servo",
                            label="get servo mode",
                            get_cmd="SVO {}",
                            vals=vals.Numbers(min_value=100,max_value=105),
                            get_parser=float
                            )                         
    # Driver parameter to reset the instrument:
        
        # self.add_parameter("reset",
                            # label="Reset",
                            # set_cmd="*RST"
                            # )
           
    # # Driver parameter to set the output of channel A on or off:
        
        # self._outputAchan_map = {'ON': 'ON', 'OFF':'OFF'}
        
        # self.add_parameter("output_A",
                           # label="OutputAChannel",
                           # get_cmd=self._output_Achan_getter,
                           # set_cmd=":OUTP1 {}",
                           # val_mapping=self._outputAchan_map,
                           # )

    # # Driver parameter to set the output of channel B on or off:
    
        # self._outputBchan_map = {'ON': 'ON', 'OFF':'OFF'}
        
        # self.add_parameter("output_B",
                           # label="OutputBChannel",
                           # get_cmd=self._output_Bchan_getter,
                           # set_cmd=":OUTP2 {}",
                           # val_mapping=self._outputBchan_map,
                           # )
    
    # # Driver parameter to set the output mode (current or voltage):
        
        # self._outputmode_map = {'CURR': 'CURR', 'VOLT':'VOLT'}
        
        # self.add_parameter("output_mode",
                           # label="OutputMode",
                           # get_cmd=":OUTP:FUNC:MODE?",
                           # set_cmd=":OUTP:FUNC:MODE {}",
                           # val_mapping=self._outputmode_map,
                           # )
                           
    # # Driver parameter to set the source waiting time ON or OFF (0s):
    
        # self._waittime_map = {'ON': 'ON', 'OFF':'OFF'}
        
        # self.add_parameter("waittime_status",
                           # label="WaitTimeStatus",
                           # get_cmd=self._waittime_getter,
                           # set_cmd=":SOUR:WAIT {}",
                           # val_mapping=self._waittime_map,
                           # )
                           
    # # Driver parameter to set the source waiting time:
    
        # self.add_parameter("waittime",
                            # label="WaitTime",
                            # unit="s",
                            # get_cmd="SOUR:WAIT:OFFS?",
                            # set_cmd="SOUR:WAIT:OFFS {}",
                            # vals=vals.Numbers(min_value=1e-3,max_value=10),
                            # get_parser=float
                            # )
                           
    # # THE BELOW SECTIONS ARE DEDICATED TO VOLTAGE SOURCING AND SENSING
    
    # # Driver parameter to set the enable or disable the auto range:
        
        # self._autorange_map = {'ON': 'ON', 'OFF':'OFF'}
        
        # self.add_parameter("autorange",
                           # label="AutoRange",
                           # get_cmd=self._autorange_getter,
                           # set_cmd=":SOUR:VOLT:RANG:AUTO {}",
                           # val_mapping=self._autorange_map,
                           # )
                           
    # # Driver parameter to set a voltage range to channel A:
        
        # self.add_parameter("voltage_range_A",
                            # label="VoltageRangeA",
                            # unit="V",
                            # get_cmd="SOUR1:VOLT:RANG?",
                            # set_cmd="SOUR1:VOLT:RANG {}",
                            # vals=vals.Numbers(min_value=2e-1,max_value=2e2),
                            # get_parser=float
                            # )
                            
    # # Driver parameter to set a voltage range to channel B:
        
        # self.add_parameter("voltage_range_B",
                            # label="VoltageRangeB",
                            # unit="V",
                            # get_cmd="SOUR2:VOLT:RANG?",
                            # set_cmd="SOUR2:VOLT:RANG {}",
                            # vals=vals.Numbers(min_value=2e-1,max_value=2e2),
                            # get_parser=float
                            # )
                            
    # # Driver parameter to set a voltage immediately to channel A:
        
        # self.add_parameter("voltage_source_A",
                            # label="VoltageA",
                            # unit="V",
                            # get_cmd="SOUR1:VOLT?",
                            # set_cmd="SOUR1:VOLT {}",
                            # vals=vals.Numbers(min_value=-2e2,max_value=2e2),
                            # get_parser=float
                            # )
                            
    # # Driver parameter to set a voltage immediately to channel B:
        
        # self.add_parameter("voltage_source_B",
                            # label="VoltageB",
                            # unit="V",
                            # get_cmd="SOUR2:VOLT?",
                            # set_cmd="SOUR2:VOLT {}",
                            # vals=vals.Numbers(min_value=-2e2,max_value=2e2),
                            # get_parser=float
                            # )
    
    # # Driver parameter to set a voltage limit to channel A (requires auto range ON):
    
        # self.add_parameter("voltage_limit_A",
                            # label="VoltageLimitA",
                            # unit="V",
                            # get_cmd="SENS1:VOLT:RANG:AUTO:LLIM?",
                            # set_cmd="SENS1:VOLT:RANG:AUTO:LLIM {}",
                            # vals=vals.Numbers(min_value=2e-1,max_value=2e2),
                            # get_parser=float
                            # )
                            
    # # Driver parameter to set a voltage limit to channel B (requires auto range ON):
    
        # self.add_parameter("voltage_limit_B",
                            # label="VoltageLimitB",
                            # unit="V",
                            # get_cmd="SENS2:VOLT:RANG:AUTO:LLIM?",
                            # set_cmd="SENS2:VOLT:RANG:AUTO:LLIM {}",
                            # vals=vals.Numbers(min_value=2e-1,max_value=2e2),
                            # get_parser=float
                            # )
                            
    # # Driver parameter to set a voltage compliance to channel A:
    
        # self.add_parameter("voltage_compliance_A",
                            # label="VoltageComplianceA",
                            # unit="V",
                            # get_cmd="SENS1:VOLT:PROT?",
                            # set_cmd="SENS1:VOLT:PROT {}",
                            # vals=vals.Numbers(min_value=1e-6,max_value=2e0),
                            # get_parser=float
                            # )
                            
    # # Driver parameter to set a voltage compliance to channel B:
    
        # self.add_parameter("voltage_compliance_B",
                            # label="VoltageComplianceB",
                            # unit="V",
                            # get_cmd="SENS2:VOLT:PROT?",
                            # set_cmd="SENS2:VOLT:PROT {}",
                            # vals=vals.Numbers(min_value=1e-6,max_value=2e0),
                            # get_parser=float
                            # )
                            
    # # THE BELOW SECTIONS ARE DEDICATED TO VOLTAGE SOURCING AND SENSING
    
    # # Driver parameter to set a current range to channel A:
        
        # self.add_parameter("current_range_A",
                            # label="CurrentRangeA",
                            # unit="A",
                            # get_cmd="SOUR1:CURR:RANG?",
                            # set_cmd="SOUR1:CURR:RANG {}",
                            # vals=vals.Numbers(min_value=1e-9,max_value=3e0),
                            # get_parser=float
                            # )
                            
    # # Driver parameter to set a current range to channel B:
        
        # self.add_parameter("current_range_B",
                            # label="CurrentRangeB",
                            # unit="A",
                            # get_cmd="SOUR2:CURR:RANG?",
                            # set_cmd="SOUR2:CURR:RANG {}",
                            # vals=vals.Numbers(min_value=1e-9,max_value=3e0),
                            # get_parser=float
                            # )
                            
    # # Driver parameter to set a current immediately to channel A:
        
        # self.add_parameter("current_source_A",
                            # label="CurrentA",
                            # unit="A",
                            # get_cmd="SOUR1:CURR?",
                            # set_cmd="SOUR1:CURR {}",
                            # vals=vals.Numbers(min_value=-3e0,max_value=3e0),
                            # get_parser=float
                            # )
                            
    # # Driver parameter to set a current immediately to channel B:
        
        # self.add_parameter("current_source_B",
                            # label="CurrentB",
                            # unit="A",
                            # get_cmd="SOUR2:CURR?",
                            # set_cmd="SOUR2:CURR {}",
                            # vals=vals.Numbers(min_value=-3e1,max_value=3e0),
                            # get_parser=float
                            # )

    # # Driver parameter to set a current limit to the A channel (requires auto range ON):
    
        # self.add_parameter("current_limit_A",
                            # label="CurrentLimitA",
                            # unit="A",
                            # get_cmd="SENS1:CURR:RANG:AUTO:LLIM?",
                            # set_cmd="SENS1:CURR:RANG:AUTO:LLIM {}",
                            # vals=vals.Numbers(min_value=1e-6,max_value=2e0),
                            # get_parser=float
                            # )
                            
    # # Driver parameter to set a current limit to the A channel (requires auto range ON):
    
        # self.add_parameter("current_limit_B",
                            # label="CurrentLimitB",
                            # unit="A",
                            # get_cmd="SENS2:CURR:RANG:AUTO:LLIM?",
                            # set_cmd="SENS2:CURR:RANG:AUTO:LLIM {}",
                            # vals=vals.Numbers(min_value=1e-6,max_value=2e0),
                            # get_parser=float
                            # )

    # # Driver parameter to set a current compliance to the A channel:
    
        # self.add_parameter("current_compliance_A",
                            # label="CurrentComplianceA",
                            # unit="A",
                            # get_cmd="SENS1:CURR:PROT?",
                            # set_cmd="SENS1:CURR:PROT {}",
                            # vals=vals.Numbers(min_value=1e-8,max_value=1),
                            # get_parser=float
                            # )
                            
    # # Driver parameter to set a current compliance to the A channel:
    
        # self.add_parameter("current_compliance_B",
                            # label="CurrentComplianceB",
                            # unit="A",
                            # get_cmd="SENS2:CURR:PROT?",
                            # set_cmd="SENS2:CURR:PROT {}",
                            # vals=vals.Numbers(min_value=1e-8,max_value=1),
                            # get_parser=float
                            # )
    
    # # Driver parameter to measure current on the A channel:
    
        # self.add_parameter("current_measure_A",
                            # label="CurrentA",
                            # unit="A",
                            # get_cmd="MEAS:CURR? (@1)",
                            # get_parser=float
                            # )

    # # Driver parameter to measure current on the B channel:
    
        # self.add_parameter("current_measure_B",
                            # label="CurrentB",
                            # unit="A",
                            # get_cmd="MEAS:CURR? (@2)",
                            # get_parser=float
                            # )  

    # # Driver parameter to measure voltage on the A channel:
    
        # self.add_parameter("voltage_measure_A",
                            # label="VoltageA",
                            # unit="V",
                            # get_cmd="MEAS:VOLT? (@1)",
                            # get_parser=float
                            # )

    # # Driver parameter to measure voltage on the B channel:
    
        # self.add_parameter("voltage_measure_B",
                            # label="VoltageB",
                            # unit="V",
                            # get_cmd="MEAS:VOLT? (@2)",
                            # get_parser=float
                            # )    
                           
    # def _autorange_getter(self) -> str:
        # """
        # get_cmd for the auto range
        # """
        # resp = self.ask("SOUR:VOLT:RANG:AUTO?")
        # if resp =='1':
            # autorange='ON'
        # elif resp=='0':
            # autorange='OFF'

        # return autorange
        
    # def _waittime_getter(self) -> str:
        # """
        # get_cmd for the auto range
        # """
        # resp = self.ask("SOUR:WAIT?")
        # if resp =='1':
            # waittime_status='ON'
        # elif resp=='0':
            # waittime_status='OFF'

        # return waittime_status
    
    # def _output_Achan_getter(self) -> str:
        # """
        # get_cmd for the A output channel
        # """
        # resp = self.ask("OUTP1?")
        # if resp =='1':
            # outputAchan='ON'
        # elif resp=='0':
            # outputAchan='OFF'

        # return outputAchan
        
    # def _output_Bchan_getter(self) -> str:
        # """
        # get_cmd for the B output channel
        # """
        # resp = self.ask("OUTP2?")
        # if resp =='1':
            # outputBchan='ON'
        # elif resp=='0':
            # outputBchan='OFF'

        # return outputBchan