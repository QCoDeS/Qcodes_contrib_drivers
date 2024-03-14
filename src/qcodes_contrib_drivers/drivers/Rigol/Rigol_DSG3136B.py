"""Driver for Rigol DSG3136B microwave signal generator

Written by Edward Laird (http://wp.lancs.ac.uk/laird-group/) based on another Rigol driver by Matthew Green.

Examples:

    ***Setting up and testing instrument control***

    On Edward's PC, it seems to be necessary to run UltraSigma (Rigol's proprietary interface program), then unplug and replug USB, then run the Python commands below. After that you can shut down UltraSigma and Python will run happily.

        $ from qcodes.instrument_drivers.rigol.Rigol_DSG3136B import RigolDSG3136B
        $ sg_1 = RigolDSG3136B('r_3136B_1', 'USB0::0x1AB1::0x099C::DSG3E244600050::INSTR')
        $ sg_1.identify()      # Should return the name of the instrument
        $ sg_1.output('1')     # Turn output on
        $ sg_1.frequency(1e9)  # Set the instrument frequency
        $ sg_1.level(-20.57)   # Set the instrument power level

    If you have set up QCoDes with dummy instruments (following
    https://microsoft.github.io/Qcodes/examples/15_minutes_to_QCoDeS.html )  and have set up doND (following
    https://microsoft.github.io/Qcodes/examples/DataSet/Using_doNd_functions_in_comparison_to_Measurement_context_manager_for_performing_measurements.html ) then you should also be able to execute:
        $ station.add_component(sg_1)
        $ do1d(sg_1.level, -50, -20, 11, 0, dmm.v1, dmm.v2, show_progress=True, do_plot=True)


    ***Using sweep mode***

    Sweep mode is a faster way of stepping through a series of data points than setting frequency or power at every step.
    To sweep from 1 GHz to 2 GHz in 11 steps then do:
        $ sg_1.sweep('FREQ')
        $ sg_1.sweep_type('STEP')
        $ sg_1.sweep_direction('FWD')
        $ sg_1.sweep_shape('RAMP')
        $ sg_1.sweep_frequency_start(1e9)
        $ sg_1.sweep_frequency_stop(2e9)
        $ sg_1.sweep_points(11)
        $ sg_1.sweep_mode('SING')
        $ sg_1.sweep_trigger('AUTO')
        $ sg_1.point_trigger('BUS')
    and then
        $ sg_1.sweep_execute()
    to begin the sweep, and
        $ sg_1.trigger()
    to step to each next point. To jump back to the beginning of the sweep, execute
        $ sg_1.sweep_reset()
    To go back from sweep to continuous output, execute
        $ sg_1.sweep('OFF')
"""

import logging
from qcodes import validators as vals
from qcodes.instrument import VisaInstrument

log = logging.getLogger(__name__)

class RigolDSG3136B(VisaInstrument):
    """
    QCoDeS driver for the Rigol DSG3136B signal generator.
    See end of file for example instantiation code and middle of the file for information about sweeping.
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
