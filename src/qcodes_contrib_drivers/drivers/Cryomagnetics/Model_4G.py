# This Python file uses the following encoding: utf-8

"""
Created on Mon Feb 5 09:44:08 2018
@author: Rami EZZOUCH
Updated by Elyjah <elyjah.kiyooka@cea.fr>, June 2022

"""

import time
from qcodes import VisaInstrument, validators as vals
from qcodes.utils.helpers import create_on_off_val_mapping

class Model_4G(VisaInstrument):
    """
    This is the qcodes driver for the cryomagnetics
    Model 4G superconducting magnet power supply.
    """

    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, terminator='\n', **kwargs)

        idn = self.IDN.get()
        self.model = idn['model']
        self.visa_handle.write('UNITS G')
        print ('The cyromag magnet power supply units have been set to KGauss.')

        self.add_parameter(name='units',
                            label='units',
                            get_cmd='UNITS?',
                            get_parser=str,
                            set_cmd='UNITS {}',
                            set_parser=str,
                            vals=vals.Enum('A', 'G'),
                            docstring=("Get and set the units the magnet uses to output values. "
                                       "Please keep units in G or else some parameters may not work properly. "))

        self.add_parameter(name='B',
                            label='Set field in one command',
                            get_cmd='IOUT?',
                            get_parser=lambda val: float(val[:-2]),
                            set_cmd=self._set_mag,
                            set_parser=float,
                            vals=vals.Numbers(-86, 86),
                            unit='kG',
                            docstring=("Set and get the current magnet supply output. "
                            "Queries the current field and subtracts the setpoint field every 100 ms "
                            "and only accepts reaching the setpoint when difference is less than 5 mT or 50 G. "
                            "Will only work if units are set to G. "))

        self.add_parameter(name='B_go',
                            label='Set field in one command',
                            get_cmd='IOUT?',
                            get_parser=lambda val: float(val[:-2]),
                            set_cmd=self._set_mag_go,
                            set_parser=float,
                            vals=vals.Numbers(-86, 86),
                            unit='kG',
                            docstring=("Set and get the current magnet supply output. "
                            "Queries the current field and subtracts the setpoint field every 100 ms "
                            "and only accepts reaching the setpoint when difference is less than 5 mT or 50 G. "
                            "Will only work if units are set to G. "))

        self.add_parameter(name='field',
                            label='Field from current in coils',
                            get_cmd='IMAG?',
                            get_parser=lambda val: float(val[:-2]),
                            unit='kG',
                            docstring=("Get the current in the magnet solenoid  "
                            "and converts to field using coil constant. "
                            "Only different from field_supply if magnet persistent heater is off. "
                            "Value in coils is assumed from last value when heater was on."))

        self.add_parameter(name='field_supply',
                            label='Field from current supply output',
                            get_cmd='IOUT?',
                            get_parser=lambda val: float(val[:-2]),
                            unit='kG',
                            docstring=("Get the magnet supply output current "
                            "and converts to field using coil constant."))

        self.add_parameter(name='sweep',
                            label='Sweep field',
                            get_cmd='SWEEP?',
                            get_parser=str,
                            set_cmd='SWEEP {} SLOW',
                            set_parser=str,
                            vals=vals.Enum('UP', 'Up', 'up', 'DOWN', 'Down', 'down', 'Pause', 'PAUSE', 'pause', 'ZERO', 'Zero', 'zero'),
                            unit='Amps/Sec',
                            docstring=("Tells the magnet to start sweeping to its upper limit, lower limit, or to zero. "
                            "Can also be used to pause the magnet while sweeping."))

        self.add_parameter(name='hilim',
                            label='Upper field',
                            get_cmd='ULIM?',
                            get_parser= lambda val: float(val[:-2]),
                            set_cmd='ULIM {}',
                            set_parser=float,
                            vals=vals.Numbers(-86, 86),
                            unit='kG',
                            docstring=("Get and set the desired higher field range. "))

        self.add_parameter(name='lolim',
                            label='Lower field',
                            get_cmd='LLIM?',
                            get_parser= lambda val: float(val[:-2]),
                            set_cmd='LLIM {}',
                            set_parser=float,
                            vals=vals.Numbers(-86, 86),
                            unit='kG',
                            docstring=("Get and set the desired lower field range."))

        self.add_parameter(name='rate_0',
                            label='1st sweep rate',
                            get_cmd='RATE? 0',
                            get_parser=float,
                            set_cmd='RATE 0 {}',
                            set_parser=float,
                            vals = vals.Numbers(0, 0.01),
                            unit='Amps/Sec',
                            docstring=("Get and set the sweep rate for the first range between 0 and 25 A."))

        self.add_parameter(name='rate_1',
                            label='2nd sweep rate',
                            get_cmd='RATE? 1',
                            get_parser=float,
                            set_cmd='RATE 1 {}',
                            set_parser=float,
                            vals = vals.Numbers(0, 0.01),
                            unit='Amps/Sec',
                            docstring=("Get and set the sweep rate for the second range between 25 and 45 A."))

        self.add_parameter(name='rate_2',
                            label='3rd sweep rate',
                            get_cmd='RATE? 2',
                            get_parser=float,
                            set_cmd='RATE 2 {}',
                            set_parser=float,
                            vals = vals.Numbers(0, 0.01),
                            unit='Amps/Sec',
                            docstring=("Get and set the sweep rate for the third range between 45 and 65 A."))

        self.add_parameter(name='rate_3',
                            label='4th sweep rate',
                            get_cmd='RATE? 3',
                            get_parser=float,
                            set_cmd='RATE 3 {}',
                            set_parser=float,
                            vals = vals.Numbers(0, 0.01),
                            unit='Amps/Sec',
                            docstring=("Get and set the sweep rate for the fourth range between 65 and 85 A."))

        self.add_parameter(name='rate_4',
                            label='5th sweep rate',
                            get_cmd='RATE? 4',
                            get_parser=float,
                            set_cmd='RATE 4 {}',
                            set_parser=float,
                            vals = vals.Numbers(0, 0.01),
                            unit='Amps/Sec',
                            docstring=("Get and set the sweep rate for the fifth range between 85 and 95 A."))

        self.add_parameter(name='persistance_heater',
                            label='Persistance heater',
                            get_cmd='PSHTR?',
                            set_cmd=self._set_persistance_heater,
                            val_mapping=create_on_off_val_mapping(on_val='1', off_val='0'),
                            docstring=("Turn on or off the persistance heater."))

    def _set_mag(self,set_pnt):
        """Function to control the movement of the magnet parameter B. Asks current field value and compares to setpoint.
        If the setpoint is higher it sweeps up, and if the setpoint is lower it sweeps down. If the value is
        different by more than 5 mT or 50 G, the while loop will not exit. The while loop sleeps 50 ms before checking again.
        """
        unit = self.visa_handle.query('UNITS?')
        if unit != 'G':
            RuntimeError('Units must be in Gauss / kG ! ')

        mag_now = float(self.visa_handle.query('IOUT?')[:-2])
        if set_pnt > mag_now:
            self.visa_handle.write('ULIM %s' % set_pnt)
            self.visa_handle.write('SWEEP UP SLOW')

            while abs(set_pnt - mag_now) >= 0.05:
                time.sleep(.05)
                mag_now = float(self.visa_handle.query('IOUT?')[:-2])

        if set_pnt < mag_now:
            self.visa_handle.write('LLIM %s' % set_pnt)
            self.visa_handle.write('SWEEP DOWN SLOW')

            while abs(set_pnt - mag_now) >= 0.05:
                time.sleep(.05)
                mag_now = float(self.visa_handle.query('IOUT?')[:-2])

    def _set_mag_go(self,set_pnt):
        """Function to check if the magnet has reached its desired value (to within 5 mT or 50 G) in the magnet parameter B_go.
        To be used when the field is swept independentally (with a different function) and only for comparing current magnet value to desired one.
        While loop checks every 50 ms for comparison of the two values.
        """
        unit = self.visa_handle.query('UNITS?')
        if unit != 'G':
            RuntimeError('Units must be in Gauss / kG ! ')

        while abs(set_pnt -  float(self.visa_handle.query('IOUT?')[:-2])) >= 0.05:
            time.sleep(.05)

    def _set_persistance_heater(self, val):
        if val == '0':
            self.write_raw('PSHTR OFF')
        else:
            self.write_raw('PSHTR ON')