# This Python file uses the following encoding: utf-8

"""
Created by Elyjah <elyjah.kiyooka@cea.fr>, June 2022

"""

from qcodes import VisaInstrument, validators as vals
from qcodes.utils.delaykeyboardinterrupt import DelayedKeyboardInterrupt
from qcodes.utils.validators import ComplexNumbers, Enum, Numbers, Ints

class GS200(VisaInstrument):
    """
    This is the qcodes driver for the Yokogawa GS200 DC voltage / current source
    Model GS200. Highest current output is 200mA !
    """
    def __init__(self, name: str, address: str, **kwargs):
        super().__init__(name, address, terminator='', device_clear = True, **kwargs)

        idn = self.IDN.get()
        self.model = idn['model']

        self.add_parameter(name='output_state',
                            label='Output state',
                            get_cmd=':OUTPut:STATe?',
                            get_parser=str,
                            set_cmd=':OUTPut:STATe {}',
                            set_parse=str,
                            val_mapping = {'OFF':  0,
                                            'ON': 1},
                            docstring="Turn the output on or off.")

        self.add_parameter(name='source',
                            label='Source',
                            get_cmd=':SOURce:FUNCtion?',
                            get_parser=str,
                            set_cmd=':SOURce:FUNCtion {}',
                            set_parser=str,
                            vals = Enum('Curr', 'Volt'),
                            docstring="Select which source you want current or voltage")

        self.add_parameter(name='output_curr',
                            label='output_curr',
                            get_cmd=':SOURce:LEVel?',
                            get_parser=str,
                            set_cmd=':SOURce:LEVel {}',
                            set_parser=float,
                            vals = Numbers(min_value = -200e-3, max_value = 200e-3),
                            unit = 'A',
                            docstring="Choose the value of the current. Will only source once you change the output_state to 'ON'.  "
                            "Only relevant if the 'source' is in current mode.")

        self.add_parameter(name='range_volt',
                            label='range_volt',
                            get_cmd=':SOURce:RANGe?',
                            get_parser=str,
                            set_cmd=':SOURce:RANGe {}',
                            get_parser=int,
                            vals = Enum(1,10,30),
                            unit = 'V',
                            docstring="Choose the range for the voltage output. Only relevant if sourcing voltage.")

        self.add_parameter(name='range_curr',
                            label='range_curr',
                            get_cmd=':SOURce:RANGe?',
                            get_parser=str,
                            set_cmd=':SOURce:RANGe {}',
                            get_parser=float,
                            vals = Enum(1e-3,10e-3,100e-3,200e-3),
                            unit = 'A',
                            docstring="Choose the range for the current output. Only relevant if sourcing current.")

        self.add_parameter(name='compliance_volt',
                            label='compliance_volt',
                            get_cmd=':SOURce:PROtection:VOLTage?',
                            get_parser=str,
                            set_cmd=':SOURce:Protection:VOLTage {}',
                            get_parser=int,
                            vals = Numbers(min_value = 1, max_value = 30),
                            unit = 'V',
                            docstring="Get and set the compliance voltage. Only relevant if sourcing current.")

        self.add_parameter(name='compliance_curr',
                            label='compliance_curr',
                            get_cmd=':SOURce:PROtection:CURRent?',
                            get_parser=str,
                            set_cmd=':SOURce:Protection:CURRent {}',
                            get_parser=float,
                            vals = Numbers(min_value = 1e-3, max_value = 200e-3),
                            unit = 'A',
                            docstring="Get and set the compliance current. Only relevant if sourcing voltage.")

