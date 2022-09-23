from typing import Any

from qcodes import VisaInstrument

class Anritsu68B(VisaInstrument):
    """
    This is the qcodes driver for Anritsu/Wiltron 68B series signal generators.
    Only the very basic functions are implemented.
    """

    def __init__(self, name: str, address: str, **kwargs: Any):
        super().__init__(name, address, terminator='\n', **kwargs)

        self.add_parameter('power',
                           label='Power',
                           set_cmd='XL1 {:.2f} DM;',
                           unit='dBm')

        self.add_parameter('frequency',
                           label='Frequency',
                           set_cmd='F1; {:.10f} Hz',
                           unit='Hz')

        self.add_parameter('rf_output',
                           set_cmd='RF{};',
                           val_mapping={'on': 1, 'off': 0})

    def initialize(self):
        self.write_raw('RST;')
