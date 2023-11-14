from qcodes.utils.validators import Numbers, Enum
from qcodes import VisaInstrument
from qcodes.parameters import create_on_off_val_mapping
from typing import Any


class Valon5015(VisaInstrument):
    def __init__(self, name: str, address: str, **kwargs: Any):
        super().__init__(name, address, terminator='\n', **kwargs)

        self.add_parameter(name='status',
                           label='Status',
                           get_cmd='STAT?')
        
        self.add_parameter(name='id',
                           label='ID',
                           get_cmd='ID?',
                           set_cmd='ID{}',
                           set_parser=lambda n: str(int(n)))

        self.add_parameter(name='frequency',
                           label='Frequency',
                           unit='Hz',
                           get_cmd='F?',
                           set_cmd='F{}Hz',
                           get_parser=int,
                           set_parser=lambda freq: str(int(freq)),
                           vals=Numbers(10e6, 15e9))
        
        self.add_parameter(name='offset',
                           label='Offset',
                           unit='Hz',
                           get_cmd='OFF?',
                           set_cmd='OFF{}Hz',
                           get_parser=int,
                           set_parser=lambda freq: str(int(freq)),
                           vals=Numbers(-4295e3, 4295e3))
        
        self.add_parameter(name='power',
                           label='Power',
                           unit='dBm',
                           get_cmd='PWR?',
                           set_cmd='PWR{}',
                           get_parser=float)
        
        self.add_parameter(name='low_power_mode_enabled',
                           label='Low Power Mode Enabled',
                           get_cmd='PDN?',
                           set_cmd='PDN{}',
                           get_parser=str.lower,
                           set_parser=str.upper,
                           val_mapping=create_on_off_val_mapping(on_val=True, off_val=False))
        
        self.add_parameter(name='buffer amplifiers_enabled',
                           label='Buffer Amplifiers Enabled',
                           get_cmd='OEN?',
                           set_cmd='OEN{}',
                           get_parser=str.lower,
                           set_parser=str.upper,
                           val_mapping=create_on_off_val_mapping(on_val=True, off_val=False))
        
        self.add_parameter(name='modulation_db',
                           label='Modulation_dB',
                           unit='dB',
                           get_cmd='AMD?',
                           set_cmd='AMD{}',
                           get_parser=float,
                           vals=Numbers(0.0))
        
        self.add_parameter(name='modulation_frequency',
                           label='Modulation_Frequency',
                           unit='Hz',
                           get_cmd='AMF?',
                           set_cmd='AMF{}',
                           get_parser=int,
                           set_parser=lambda freq: str(int(freq)),
                           vals=Numbers(1, 2e3))
