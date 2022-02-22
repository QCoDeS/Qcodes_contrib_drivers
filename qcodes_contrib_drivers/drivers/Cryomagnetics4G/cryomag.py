# This Python file uses the following encoding: utf-8

"""
Created on Mon Feb 5 09:44:08 2018
@author: Rami EZZOUCH
Updated by Elyjah <elyjah.kiyooka@cea.fr>, Jan 2022

"""

import time
from qcodes import VisaInstrument, validators as vals
from qcodes.utils.delaykeyboardinterrupt import DelayedKeyboardInterrupt

class Cryomag(VisaInstrument):
    """
    This is the qcodes driver for the cryomagnetics
    Model 4G superconducting magnet power supply.
    """

    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, terminator='\n', **kwargs)

        idn = self.IDN.get()
        self.model = idn['model']
        self.visa_handle.write('UNITS G')
        print ('The units have been set to KGauss')

        self.add_parameter(name='RST',
                           label='RST',
                           set_cmd='*RST',
                           set_parser=str)

        self.add_parameter(name='getI',
                           label='Magnetic Field',
                           get_cmd='IOUT?',
                           get_parser=lambda val: float(val[:-2]),
                           unit='kG')

        self.add_parameter(name='getImag',
                           label='getImag',
                           get_cmd='IMAG?',
                           get_parser=lambda val: float(val[:-2]),
                           unit='kG')

        self.add_parameter(name='goto',
                           label='goto',
                           set_cmd='SWEEP {} SLOW',
                           get_cmd='SWEEP?',
                           get_parser=str,
                           set_parser=str,
                           vals=vals.Enum('UP', 'Up', 'up', 'DOWN', 'Down', 'down', 'Pause', 'PAUSE', 'pause', 'ZERO', 'Zero', 'zero'),
                           unit='Amps/Sec')

        self.add_parameter(name='STOP',
                           label='STOP',
                           set_cmd='SWEEP PAUSE')

        self.add_parameter(name='setRate0',
                           label='setRate0',
                           set_cmd='RATE 0 {}',
                           set_parser=float,
                           vals = vals.Numbers(0, 0.01),
                           unit='Amps/Sec')

        self.add_parameter(name='setRate1',
                           label='setRate1',
                           set_cmd='RATE 1 {}',
                           set_parser=float,
                           vals = vals.Numbers(0, 0.01),
                           unit='Amps/Sec')

        self.add_parameter(name='getRate0',
                           label='getRate0',
                           get_cmd='RATE? 0',
                           get_parser=float,
                           unit='Amps/Sec')

        self.add_parameter(name='getRate1',
                           label='getRate1',
                           get_cmd='RATE? 1',
                           get_parser=float,
                           unit='Amps/Sec')

        self.add_parameter(name='heater',
                           label='heater',
                           get_cmd='PSHTR?',
                           set_cmd='PSHTR {}',
                           get_parser=str,
                           set_parser=str,
                           vals=vals.Enum('On', 'Off', 'ON', 'OFF', 'on', 'off'),
                           unit='None')

        self.add_parameter(name='units',
                           label='units',
                           get_cmd='UNITS?',
                           set_cmd='UNITS {}',
                           get_parser=str,
                           set_parser=str,
                           vals=vals.Enum('A', 'G'),
                           unit='None')

        self.add_parameter(name='hilim',
                           label='hilim',
                           get_cmd='ULIM?',
                           set_cmd='ULIM {}',
                           get_parser= lambda val: float(val[:-2]),
                           set_parser=float,
                           vals=vals.Numbers(-86, 86),
                           unit='kG')

        self.add_parameter(name='lolim',
                           label='lolim',
                           get_cmd='LLIM?',
                           set_cmd='LLIM {}',
                           get_parser= lambda val: float(val[:-2]),
                           set_parser=float,
                           vals=vals.Numbers(-86, 86),
                           unit='kG')

        self.add_parameter(name='B',
                           label='Set field in one command',
                           get_cmd='IOUT?',
                           get_parser=lambda val: float(val[:-2]),
                           set_cmd=self._set_mag,
                           set_parser=float,
                           vals=vals.Numbers(-86, 86),
                           unit='kG')

    def _set_mag(self,set_pnt):
        unit = self.visa_handle.query('UNITS?')
        if unit != 'G':
            RuntimeError('Units must be in Gauss')

        mag_now = float(self.visa_handle.query('IOUT?')[:-2])
        if set_pnt > mag_now:
            self.visa_handle.write('ULIM %s' % set_pnt)
            self.visa_handle.write('SWEEP UP SLOW')

            while abs(set_pnt - mag_now) >= 0.05:
                time.sleep(.1)
                mag_now = float(self.visa_handle.query('IOUT?')[:-2])

        if set_pnt < mag_now:
            self.visa_handle.write('LLIM %s' % set_pnt)
            self.visa_handle.write('SWEEP DOWN SLOW')

            while abs(set_pnt - mag_now) >= 0.05:
                time.sleep(.1)
                mag_now = float(self.visa_handle.query('IOUT?')[:-2])
