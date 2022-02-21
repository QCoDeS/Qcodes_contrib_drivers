# This Python file uses the following encoding: utf-8

"""
Created on 11-2020
@author: Nath !
Updated by Elyjah <elyjah.kiyooka@cea.fr>, Jan 2022

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
        self.visa_handle.write('UNITS cm')
        print ('The units have been set to cm.')

        self.add_parameter(name='measure_helvl',
                           label = 'Measure Helium level',
                           get_cmd = 'MEAS? 1',
                           get_parser = str,
                           set_cmd = 'MEAS 1',
                           vals=vals.Enum('Meas', 'MEASURE', 'meas', 'mesure', 'Mesure', 'Do', 'do'),
                           )
