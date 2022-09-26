from qcodes import VisaInstrument
from qcodes.instrument.channel import InstrumentChannel
from qcodes.utils.validators import Numbers, Enum
from qcodes.utils.helpers import create_on_off_val_mapping
import pyvisa as visa

class Yokogawa7651(VisaInstrument):
    """
    QCoDeS driver for Yokogawa 7651 current source.
    """
    def __init__(self, name: str, address: str, **kwargs):
        """
        Args:
            name: Name to use internally in QCoDeS
            address: VISA ressource address
        """
        super().__init__(name, address, **kwargs)

        self.add_parameter(name='output',
                           set_cmd='O{}E',
                           val_mapping={'on': 1,
                                        'off': 0})
        
        self.add_parameter(name='mode',
                           set_cmd='F{}E',
                           val_mapping={'C.V.': 1,
                                        'C.C.': 5})

        self.add_parameter(name='range',
                           set_cmd=self._set_range)

        self.add_parameter(name='value',
                           set_cmd=self._set_value)

    def _set_range(self, range: str):
        """Function to set range based on output mode.

        Parameters
        ----------
        range : str
            Desired output range
        """
        allowed_range = {'C.V.': {'10mV': 'R2',
                                  '100mV': 'R3',
                                  '1V': 'R4',
                                  '10V': 'R5',
                                  '30V': 'R6'},
                         'C.C.': {'1mA': 'R4',
                                  '10mA': 'R5',
                                  '100mA': 'R6'}}

        try:
            range_str = allowed_range[self.mode()][range]
        except:
            raise ValueError('Specified range is not supported or in wrong unit.')

        self.write(range_str+'E')

    def _set_value(self, value: float):
        """Function to set output value.

        Parameters
        ----------
        value : float
            Desired output value, in the unit of mV (or mA)
        """
        value_str = f'{abs(value)/1000:.10f}'

        if value < 0:
            polarity_str = '-'
        else:
            polarity_str = '+'

        self.write('S'+polarity_str+value_str+'E')
        
