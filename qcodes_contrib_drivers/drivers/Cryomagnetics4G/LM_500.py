# This Python file uses the following encoding: utf-8

"""
Created on 11-2020
@author: Nath !
Updated by Elyjah <elyjah.kiyooka@cea.fr>, June 2022

"""

import time
from qcodes import VisaInstrument, validators as vals
from qcodes.utils.delaykeyboardinterrupt import DelayedKeyboardInterrupt

class LM_500(VisaInstrument):
    """
    This is the qcodes driver for the LM_500 Helium lvl monitor.
    """

    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, terminator='\n', **kwargs)

        idn = self.IDN.get()
        self.model = idn['model']
        print ('The LM_500 level meter units have been set to cm.')


        self.add_parameter(name='measure',
                            label = 'Measure Helium level',
                            get_cmd = 'MEAS? 1',
                            get_parser = str,
                            docstring="Measure the helium level in the units defined by the user.")

        self.add_parameter(name='measure_float',
                            label = 'Measure Helium level as float',
                            get_cmd = self._get_float,
                            get_parser = float,
                            vals = vals.Numbers(),
                            docstring="Measure the helium level in the units defined by the user as a float without the units printed.")

        self.add_parameter(name='units',
                            label = 'Set unit',
                            get_cmd = 'UNITS?',
                            get_parser = str,
                            set_cmd = 'UNITS {}',
                            set_parser = str,
                            vals=vals.Enum('cm','in','percent','%'),
                            initial_value = 'cm',
                            docstring="Get and set the units for measurement.")

    def _get_float(self)->float:
        """Parce the output of measure to strip the units off, and outputs just the value as a float.
        """
        output = self.visa_handle.query('MEAS? 1')
        units = self.visa_handle.query('UNITS?')
        return float(output.replace(units,''))

