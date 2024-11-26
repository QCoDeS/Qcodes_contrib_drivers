"""Driver for Rigol DSG3136B microwave signal generator

Written by Edward Laird (http://wp.lancs.ac.uk/laird-group/) based on another Rigol driver by Matthew Green.

A documentation notebook is in the docs/examples/ directory.
"""

import logging
from qcodes import validators as vals
from qcodes.instrument import VisaInstrument

log = logging.getLogger(__name__)

class RigolDSG3136B(VisaInstrument):
    """
    QCoDeS driver for the Rigol DSG3136B signal generator.
    """

    def __init__(self, name, address, **kwargs):
        '''
        Args:
            name (str): The name of the instrument used internally by QCoDes. Must be unique.
            address (str): The VISA resource name.
        '''
        super().__init__(name, address, terminator="\n", **kwargs)

        self.add_parameter('identify',
            label='Indentify',
            get_cmd='*IDN?',
            get_parser=str.rstrip
            )
        """Send identification code"""
        
        self.add_parameter('output',
            label='Output state',
            set_cmd=':OUTPut:STATe {}',
            get_cmd=':OUTPut:STATe?',
            val_mapping={
                   'OFF': 0,
                   'ON': 1,
               },
            #get_parser=str.rstrip,
            vals=vals.Enum('OFF', 'ON')
            )
        """Turns on or off the RF output, e.g. sg_1.output('0') or sg_1.output('OFF')"""
        
        self.add_parameter(name='frequency',
            label='Frequency',
            unit='Hz',
            get_cmd='FREQ?',
            set_cmd='FREQ {:.2f}',
            get_parser=float,
            vals=vals.Numbers(9e3, 13.6e9)
            )
        """Control the output frequency"""
        
        self.add_parameter(name='level',
            label='Level',
            unit='dBm',
            get_cmd='LEV?',
            set_cmd='LEV {:.2f}',
            get_parser=float,
            vals=vals.Numbers(-130, 27)
            )
        """Control the output power level"""
                      
        self.add_parameter('sweep_direction',
            label='Sweep direction',
            set_cmd=':SOURce:SWEep:DIRection {}',
            get_cmd=':SOURce:SWEep:DIRection?',
            get_parser=str.rstrip,
            vals=vals.Enum('FWD', 'REV')
            )
        """Control the sweep direction"""

        self.add_parameter('sweep_list_points',
            label='Sweep list points',
            get_cmd=':SOURce:SWEep:LIST:CPOint?',
            get_parser=int
            )
        """Control the number of sweep points"""

        self.add_parameter('sweep_mode',
            label='Sweep mode',
            set_cmd=':SOURce:SWEep:MODE {}',
            get_cmd=':SOURce:SWEep:MODE?',
            get_parser=str.rstrip,
            vals=vals.Enum('SING', 'CONT')
            )
        """Control the sweep mode"""

        self.add_parameter('sweep_trigger',
            label='Sweep trigger',
            set_cmd=':SOURce:SWEep:SWEep:TRIGger:TYPE {}',
            get_cmd=':SOURce:SWEep:SWEep:TRIGger:TYPE?',
            get_parser=str.rstrip,
            vals=vals.Enum('AUTO', 'KEY', 'BUS', 'EXT')
            )
        """Control the trigger mode of the sweep period (i.e. the trigger required to restart the sweep)"""
        
        self.add_parameter('point_trigger',
            label='Point trigger',
            set_cmd=':SOURce:SWEep:POINt:TRIGger:TYPE {}',
            get_cmd=':SOURce:SWEep:POINt:TRIGger:TYPE?',
            get_parser=str.rstrip,
            vals=vals.Enum('AUTO', 'KEY', 'BUS', 'EXT')
            )
        """Control the point trigger mode of the sweep (i.e. the trigger required to move to the next point)"""

        self.add_parameter('sweep',
            label='Sweep state',
            set_cmd=':SOURce:SWEep:STATe {}',
            get_cmd=':SOURce:SWEep:STATe?',
            get_parser=str.rstrip,
            vals=vals.Enum('OFF', 'FREQ', 'LEV', 'LEV,FREQ')
            )

        self.add_parameter('sweep_dwell',
            label='Sweep point dwell time',
            set_cmd=':SOURce:SWEep:STEP:DWELl {}',
            get_cmd=':SOURce:SWEep:STEP:DWELl?',
            get_parser=float,
            vals=vals.Numbers(2e-3,100),
            unit='s'
            )

        self.add_parameter('sweep_dwell_step',
            label='Sweep point dwell time step',
            set_cmd=':SOURce:SWEep:STEP:DWELl:STEP {}',
            get_cmd=':SOURce:SWEep:STEP:DWELl:STEP?',
            get_parser=float,
            vals=vals.Numbers(10e-3,10),
            unit='s'
            )

        self.add_parameter('sweep_points',
            label='Number of sweep points',
            set_cmd=':SOURce:SWEep:STEP:POINts {}',
            get_cmd=':SOURce:SWEep:STEP:POINts?',
            get_parser=float,
            vals=vals.Ints(2,65535)
            )

        self.add_parameter('sweep_points_step',
            label='Number of sweep points step',
            set_cmd=':SOURce:SWEep:STEP:POINts:STEP {}',
            get_cmd=':SOURce:SWEep:STEP:POINts:STEP?',
            get_parser=float,
            vals=vals.Ints(1,10000)
            )

        self.add_parameter('sweep_shape',
            label='Sweep shape',
            set_cmd=':SOURce:SWEep:STEP:SHAPe {}',
            get_cmd=':SOURce:SWEep:STEP:SHAPe?',
            get_parser=str.rstrip,
            vals=vals.Enum('RAMP', 'TRI')
            )

        self.add_parameter('sweep_spacing',
            label='Sweep spacing',
            set_cmd=':SOURce:SWEep:TYPE {}',
            get_cmd=':SOURce:SWEep:TYPE?',
            get_parser=str.rstrip,
            vals=vals.Enum('LIN', 'LOG')
            )

        self.add_parameter('sweep_frequency_start',
            label='Sweep start frequency',
            set_cmd=':SOURce:SWEep:STEP:STARt:FREQuency {}',
            get_cmd=':SOURce:SWEep:STEP:STARt:FREQuency?',
            get_parser=float,
            vals=vals.Numbers(9e3,3.6e9),
            unit='Hz'
            )
        
        self.add_parameter('sweep_frequency_stop',
            label='Sweep start frequency',
            set_cmd=':SOURce:SWEep:STEP:STOP:FREQuency {}',
            get_cmd=':SOURce:SWEep:STEP:STOP:FREQuency?',
            get_parser=float,
            vals=vals.Numbers(9e3,3.6e9),
            unit='Hz'
            )

        self.add_parameter('sweep_frequency_start_step',
            label='Sweep start frequency step',
            set_cmd=':SOURce:SWEep:STEP:STARt:FREQuency:STEP {}',
            get_cmd=':SOURce:SWEep:STEP:STARt:FREQuency:STEP?',
            get_parser=float,
            vals=vals.Numbers(10e-3,1e9),
            unit='Hz'
            )

        self.add_parameter('sweep_level_start',
            label='Sweep start level',
            set_cmd=':SOURce:SWEep:STEP:STARt:LEVel {}',
            get_cmd=':SOURce:SWEep:STEP:STARt:LEVel?',
            get_parser=float,
            vals=vals.Numbers(),
            unit='dBm'
            )

        self.add_parameter('sweep_amplitude_start',
            label='Sweep start amplitude',
            set_cmd=self.sweep_level_start,
            get_cmd=self.sweep_level_start,
            docstring='Wrapper for sweep level start'
            )

        self.add_parameter('sweep_level_start_step',
            label='Sweep start level step',
            set_cmd=':SOURce:SWEep:STEP:STARt:LEVel:STEP {}',
            get_cmd=':SOURce:SWEep:STEP:STARt:LEVel:STEP?',
            get_parser=float,
            vals=vals.Numbers(),
            unit='dBm'
            )

        self.add_parameter('sweep_amplitude_start_step',
            label='Sweep start amplitude step',
            set_cmd=self.sweep_level_start_step,
            get_cmd=self.sweep_level_start_step,
            docstring='Wrapper for sweep level start step'
            )

        self.add_parameter('sweep_frequency_stop_step',
            label='Sweep stop frequency step',
            set_cmd=':SOURce:SWEep:STEP:STOP:FREQuency:STEP {}',
            get_cmd=':SOURce:SWEep:STEP:STOP:FREQuency:STEP?',
            get_parser=float,
            vals=vals.Numbers(9e3,3.6e9),
            unit='Hz'
            )

        self.add_parameter('sweep_level_stop',
            label='Sweep stop level',
            set_cmd=':SOURce:SWEep:STEP:STOP:LEVel {}',
            get_cmd=':SOURce:SWEep:STEP:STOP:LEVel?',
            get_parser=float,
            vals=vals.Numbers(),
            unit='dBm'
            )

        self.add_parameter('sweep_level_stop_step',
            label='Sweep stop level step',
            set_cmd=':SOURce:SWEep:STEP:STOP:LEVel:STEP {}',
            get_cmd=':SOURce:SWEep:STEP:STOP:LEVel:STEP?',
            get_parser=float,
            vals=vals.Numbers(),
            unit='dBm'
            )

        self.add_parameter('sweep_type',
            label='Sweep type',
            set_cmd=':SOURce:SWEep:TYPE {}',
            get_cmd=':SOURce:SWEep:TYPE?',
            get_parser=str.rstrip,
            vals=vals.Enum('LIST','STEP')
            )
        
        # As recommended by QCoDeS, it's a good idea to call connect_message at the end of your constructor.
        self.connect_message()
        
    def trigger(self) -> None:
        """
        Generates a trigger event. This is equivalent to pressing the Force Trigger button on front panel.
        """
        self.write('*TRG')
        
    def sweep_reset(self) -> None:
        """
        Resets a sweep to the beginning of its range.
        """
        self.write(':SOURce:SWEep:RESet:ALL')
        
    def sweep_execute(self) -> None:
        """
        Executes a sweep
        """
        self.write(':SOURce:SWEep:EXECute')
        
    


