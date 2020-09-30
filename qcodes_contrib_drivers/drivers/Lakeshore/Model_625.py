import logging
import time


from qcodes import VisaInstrument
from qcodes.utils.validators import  Numbers, Enum

log = logging.getLogger(__name__)

class Lakeshore625(VisaInstrument):
    """
    Driver for the Lakeshore 625 magnet power supply.

    This class uses T/A and A/s as units.

    Args:
        name (str): a name for the instrument
        address (str): VISA address of the device
        current_ramp_limit: A current ramp limit, in units of A/s
    """

    def __init__(self, name, coil_constant,  field_ramp_rate, address=None,
                 reset=False, terminator='', **kwargs):

        super().__init__(name, address, terminator=terminator, **kwargs)
    
        # Add reset function
        self.add_function('reset', call_cmd='*RST')
        if reset:
            self.reset()

        # Add solenoid parameters    
        self.add_parameter('coil_constant_unit',
                           set_cmd=self._set_coil_constant_unit,
                           get_cmd=self._get_coil_constant_unit,
                           get_parser=float,
                           val_mapping={'T/A': 0,
                                        'kG/A': 1})
    
        self.add_parameter('coil_constant',
                           unit = self.coil_constant_unit,
                           get_cmd=self._get_coil_constant,
                           set_cmd=self._update_coil_constant,
                           vals=Numbers(0.001, 999.99999))  # what are good numbers here?

        self.add_parameter('current_limit',
                           unit="A",
                           set_cmd=lambda x: self._set_curent_limit(x),
                           get_cmd=self._get_current_limit,
                           get_parser=float,
                           vals=Numbers(0, 60.1))
                
        self.add_parameter('field_ramp_rate',
                           unit = 'T/min',
                           get_cmd=self._get_field_ramp_rate,
                           set_cmd=self._set_field_ramp_rate)
        
        self.add_parameter('voltage_limit',
                           unit="V",
                           set_cmd=lambda x: self._set_voltage_limit(x),
                           get_cmd=self._get_voltage_limit,
                           get_parser=float,
                           vals=Numbers(0, 5))  # what are good numbers here?
        
        self.add_parameter('current_rate_limit',
                           unit="A/s",
                           set_cmd=lambda x: self._set_current_rate_limit(x),
                           get_cmd=self._get_current_rate_limit,
                           get_parser=float,
                           vals=Numbers(0, 99.999))  # what are good numbers here?

 


        # Add current solenoid parameters
        # Note that field is validated in set_field
        self.add_parameter('field',
                           unit = 'T',
                           full_name = self.name + '_' + 'field',
                           set_cmd=self.set_field,
                           get_cmd='RDGF?',
                           get_parser=float)
        
        self.add_parameter('voltage',
                           unit = 'V',
                           set_cmd="SETV {}",
                           get_cmd='RDGV?',
                           get_parser=float,
                           vals=Numbers(-5, 5))
        
        self.add_parameter('current',
                           unit = 'A',
                           set_cmd="SETI {}",
                           get_cmd='RDGI?',
                           get_parser=float,
                           vals=Numbers(-60, 60))
        
        self.add_parameter('current_ramp_rate',
                           unit = 'A/s',
                           set_cmd="RATE {}",
                           get_cmd='RATE?',
                           get_parser=float)
        
        self.add_parameter('ramp_segments',
                           set_cmd="RSEG {}",
                           get_cmd='RSEG?',
                           get_parser=float,
                           val_mapping={'disabled': 0,
                                        'enabled': 1})
        
        self.add_parameter('persistent_switch_heater',
                           set_cmd=lambda x: self._set_persistent_switch_heater_status(x),
                           get_cmd=self._get_persistent_switch_heater_status,
                           get_parser=float,
                           val_mapping={'disabled': 0,
                                        'enabled': 1})
    
        self.add_parameter('quench_detection',
                           set_cmd=lambda x: self._set_quench_detection_status(x),
                           get_cmd=self._get_quench_detection_status,
                           get_parser=float,
                           val_mapping={'disabled': 0,
                                        'enabled': 1})
    
        self.add_parameter('quench_current_step_limit',
                           unit = 'A/s',
                           set_cmd=lambda x: self._set_quench_current_step_limit(x),
                           get_cmd=self._get_quench_current_step_limit,
                           get_parser=float,
                           vals=Numbers(0.01, 10))
        
        self.add_parameter('ramping_state',
                           get_cmd=self._get_ramping_state,
                           vals=Enum('ramping', 'not ramping'))
        
        self.add_parameter('operational_error_status',
                           get_cmd=self._get_operational_errors,
                           get_parser=str)
        
        self.add_parameter('oer_quench',
                           get_cmd=self._get_oer_quench_bit,
                           get_parser=int,
                           val_mapping={'no quench detected': 0,
                                        'quench detected': 1})
   
        # Add clear function
        self.add_function('clear', call_cmd='*CLS')
        
        # disable persistent switch heater by default
        self.persistent_switch_heater('disabled')
        
        # disable ramp segments by default
        self.ramp_segments('disabled')
        
        # set coil constant unit to T/A by default
        self.coil_constant_unit('T/A')

        # assign init parameters
        self.coil_constant(coil_constant)
        self.field_ramp_rate(field_ramp_rate)

        self.connect_message()




    def _sleep(self, t):
        """
        Sleep for a number of seconds t. If we are or using
        the PyVISA 'sim' backend, omit this
        """

        simmode = getattr(self, 'visabackend', False) == 'sim'

        if simmode:
            return
        else:
            time.sleep(t)
            
    # get functions returning several values
    def _get_limit(self):
        """
        Gets the limits of the supply
        """
        raw_string = self.ask('LIMIT?')
        current_limit, voltage_limit, current_rate_limit = raw_string.split(',')
        return float(current_limit), float(voltage_limit), float(current_rate_limit)
    
    def _get_persistent_switch_heater_setup(self):
        """
        Gets the persistant switch heater setup
        """
        raw_string = self.ask('PSHS?')
        status, psh_current, psh_delay = raw_string.split(',')
        return float(status), float(psh_current), float(psh_delay)
    
    def _get_quench_detection_setup(self):
        """
        Gets the quench detections setup, returns 'status' and 'current step limit'
        """
        raw_string = self.ask('QNCH?')
        status, current_step_limit = raw_string.split(',')
        return float(status), float(current_step_limit)

    def _get_field_setup(self):
        """
        Gets the field setup, returns 'coil constant unit' and 'coil constant'
        """
        raw_string = self.ask('FLDS?')
        unit, coil_constant = raw_string.split(',')
        return str(unit), float(coil_constant)    
    
    
    # get functions for parameters
    def _get_current_limit(self):
        """
        Gets the current limit of the coil
        """
        current_limit, voltage_limit, current_rate_limit = self._get_limit()
        return current_limit
    
    def _get_voltage_limit(self):
        """
        Gets the current limit of the coil
        """
        current_limit, voltage_limit, current_rate_limit = self._get_limit()
        return voltage_limit

    def _get_current_rate_limit(self):
        """
        Gets the current limit of the coil
        """
        current_limit, voltage_limit, current_rate_limit = self._get_limit()
        return current_rate_limit
    
    def _get_persistent_switch_heater_status(self):
        """
        Sets the status of the persistant switch heater
        """
        status, psh_current, psh_delay = self._get_persistent_switch_heater_setup()
        return status
    
    def _get_quench_detection_status(self):
        """
        Gets the quench detections status
        """
        status, current_step_limit = self._get_quench_detection_setup()
        return float(status)
    
    def _get_quench_current_step_limit(self):
        """
        Gets the quench detections status
        """
        status, current_step_limit = self._get_quench_detection_setup()
        return float(current_step_limit)
    
    def _get_coil_constant(self):
        """
        Gets the coil_constant
        """
        coil_constant_unit, coil_constant = self._get_field_setup()
        return float(coil_constant)
    
    def _get_coil_constant_unit(self):
        """
        Gets the coil_constant
        """
        coil_constant_unit, coil_constant = self._get_field_setup()
        return str(coil_constant_unit)
    
    def _get_field_ramp_rate(self):
        """
        Gets the field ramp rate
        """
        coil_constant_unit, coil_constant = self._get_field_setup() # in T/A by default
        current_ramp_rate = self.current_ramp_rate()    # in A/s
        field_ramp_rate = current_ramp_rate * coil_constant * 60 # in T/min
        return float(field_ramp_rate)
    
    def _get_ramping_state(self):
        """
        Gets the ramping state of the power supply (corresponds to blue LED on panel)
        Is inferred from the status bit register
        """
        operation_condition_register = self.ask('OPST?')
        bin_OPST = bin(int(operation_condition_register))[2:]
        if len(bin_OPST)<2:
            rampbit = 1
        else:
            # read second bit, 0 = ramping, 1 = not ramping
            rampbit = int(bin_OPST[-2])
        if rampbit == 1:
            return 'not ramping'
        else:
            return 'ramping'
            
    def _get_operational_errors(self):
        """
        Reads the Error status register to infer the operational errors
        """
        error_status_register = self.ask('ERST?')
        # three bytes are read at the same time, the middle one is the operational error status
        operational_error_registor = error_status_register.split(',')[1]
        
        #prepend zeros to bit-string such that it always has length 9
        oer_bit = bin(int(operational_error_registor))[2:].zfill(9)
        return(oer_bit)
        
    def _get_oer_quench_bit(self):
        """
        Returns the oer quench bit
        """
        return self._get_operational_errors()[3]
    
    
    # set functions for parameters
    def _set_curent_limit(self, current_limit_setpoint):
        """
        Sets the current limit of the coil
        """
        current_limit, voltage_limit, current_rate_limit = self._get_limit()
        self.write_raw('LIMIT {}, {}, {}'.format(current_limit_setpoint, voltage_limit, current_rate_limit))

    def _set_voltage_limit(self, voltage_limit_setpoint):
        """
        Sets the current limit of the coil
        """
        current_limit, voltage_limit, current_rate_limit = self._get_limit()
        self.write_raw('LIMIT {}, {}, {}'.format(current_limit, voltage_limit_setpoint, current_rate_limit))
        
    def _set_current_rate_limit(self, current_rate_limit_setpoint):
        """
        Sets the current limit of the coil
        """
        current_limit, voltage_limit, current_rate_limit = self._get_limit()
        self.write_raw('LIMIT {}, {}, {}'.format(current_limit, voltage_limit, current_rate_limit_setpoint))
        
    def _set_persistent_switch_heater_status(self, status_setpoint):
        """
        Sets the status of the persistant switch heater
        """
        status, psh_current, psh_delay = self._get_persistent_switch_heater_setup()
        self.write_raw('PSHS {}, {}, {}'.format(status_setpoint, psh_current, psh_delay))
        
    def _set_quench_detection_status(self, status_setpoint):
        """
        Sets the quench detections status
        """
        status, current_step_limit = self._get_quench_detection_setup()
        self.write_raw('QNCH {}, {}'.format(status_setpoint, current_step_limit))
        
    def _set_quench_current_step_limit(self, current_step_limit_setpoint):
        """
        Sets the quench detections status
        """
        status, current_step_limit = self._get_quench_detection_setup()
        self.write_raw('QNCH {}, {}'.format(status, current_step_limit_setpoint))
        
    def _set_coil_constant(self, coil_constant_setpoint):
        """
        Sets the coil_constant
        """
        coil_constant_unit, coil_constant = self._get_field_setup()
        self.write_raw('FLDS {}, {}'.format(coil_constant_unit, coil_constant_setpoint))
    
    def _set_coil_constant_unit(self, coil_constant_unit_setpoint):
        """
        Sets the coil_constant
        """
        coil_constant_unit, coil_constant = self._get_field_setup()
        self.write_raw('FLDS {}, {}'.format(coil_constant_unit_setpoint, coil_constant))
        
    def _update_coil_constant(self, coil_constant_setpoint):
        """
        Updates the coil_constant and with it all linked parameters
        """
        # read field_ramp_rate before chaning coil constant
        field_ramp_rate = self.field_ramp_rate()
        # set the coil constant
        self._set_coil_constant(coil_constant_setpoint)
        # update the current ramp rate, leaving the field ramp rate unchanged
        current_ramp_rate_setpoint = field_ramp_rate / coil_constant_setpoint / 60   # current_ramp_rate is in A/s
        self.current_ramp_rate(current_ramp_rate_setpoint)

    def _set_field_ramp_rate(self, field_ramp_rate_setpoint):
        """
        Sets the field ramp rate in units of T/min by setting the corresponding current_ramp_rate
        """
        coil_constant_unit, coil_constant = self._get_field_setup() # in T/A by default
        current_ramp_rate_setpoint = field_ramp_rate_setpoint / coil_constant / 60   # current_ramp_rate is in A/s
        self.current_ramp_rate(current_ramp_rate_setpoint)




    def set_field(self, value, block=True):
        """
        Ramp to a certain field

        Args:
            block (bool): Whether to wait unit the field has finished setting
            perform_safety_check (bool): Whether to set the field via a parent
                driver (if present), which might perform additional safety
                checks.
        """

        self.write('SETF {}'.format(value))
        # Check if we want to block
        if not block:
            return

        # Otherwise, wait until no longer ramping
        self.log.debug(f'Starting blocking ramp of {self.name} to {value}')
        self._sleep(0.5)    # wait for a short time for the power supply to fall into the ramping state
        while self.ramping_state() == 'ramping':
            self._sleep(0.3)
        self._sleep(2.0)
        self.log.debug(f'Finished blocking ramp')
        return
