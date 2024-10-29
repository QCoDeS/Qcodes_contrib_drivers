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
        self.add_parameter("stop_axes2",
                            label="Stops all axes",
                            get_cmd="STP"
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
    
        self.add_parameter("reference",
                            label="Reference",
                            get_cmd = self._reference_getter,
                            set_cmd = "FRF {}",
                            )
    # Fast reference move to negative limit
    
        self.add_parameter("negative",
                            label="Negative Reference",                            
                            set_cmd = "FNL 1",
                            )
    # Inidicate limit switches
        
        self.add_parameter("limit",
                            label="Limit",                            
                            get_cmd = "LIM? 1",
                            )
    
    # Fast reference move to positive limit
    
        self.add_parameter("positive",
                            label="Positive Reference",                            
                            set_cmd = "FPL 1",
                            )
                            
    # Servo mode 

        self._servomode_map = {'ON': '1 1', 'OFF':'1 0'}
        
        self.add_parameter("servo",
                            label="Servo Mode",
                            get_cmd=self._servo_getter,
                            set_cmd="SVO {}",
                            val_mapping=self._servomode_map
                            )
    # Target mode
        self.add_parameter("get_target",
                            label="get on target mode",
                            get_cmd="ONT?",
                            )  
    # Set absolute target position                                    
        self.add_parameter("position",
                            label="Position",
                            unit="mm",
                            get_cmd="MOV?",
                            set_cmd="MOV 1 {:.1f}",
                            vals=vals.Numbers(min_value=1e-3,max_value=1e1),
                            get_parser=str,
                            )
    # Set relative target position
        self.add_parameter("relative",
                            label="Relative Position",
                            unit="mm",                         
                            set_cmd="MVR 1 {:.1f}",
                            vals=vals.Numbers(min_value=1e-3,max_value=1e1),
                            get_parser=str,
                            )
    # Get commanded closed-loop velocity
        self.add_parameter("cl_velocity",
                            label="Velocity",
                            unit="mm/s",                         
                            get_cmd="TCV? 1",
                            )
    # Set closed-loop velocity
        self.add_parameter("velocity",
                            label="Velocity",
                            unit="mm/s",                         
                            get_cmd="VEL? 1",
                            set_cmd = "VEL 1 {}",
                            vals = vals.Numbers(min_value=0, max_value=3),
                            get_parser = float,
                            )
        
 
    def _servo_getter(self) -> str:
        """
        get_cmd for the servo
        """
        resp = self.ask("SVO?")
        if resp =='1=1':
            servo_status='1 1'
        elif resp=='1=0':
            servo_status='1 0'

        return servo_status
    
    def _reference_getter(self) -> str:
        """
        get_cmd for reference
        """
        resp = self.ask("FRF?")
        if resp == '1=1':
            reference_status = '1 1'
        elif resp == '1=0':
            reference_status = '1 0'
        
        return reference_status