from typing import Any, Dict, Optional

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
                           get_cmd='OL1',
                           get_parser=float,
                           set_cmd='XL1 {:.2f} DM;',
                           unit='dBm')

        self.add_parameter('frequency',
                           label='Frequency',
                           get_cmd='OF1',
                           get_parser=self.frequency_parser,
                           set_cmd='F1; {:.10f} Hz',
                           unit='Hz')

        self.add_parameter('rf_output',
                           get_cmd=None,
                           initial_value='off',
                           set_cmd='RF{};',
                           val_mapping={'on': 1, 'off': 0})

    def frequency_parser(self, input: str):
        return float(input.strip('\r'))*1e6

    def initialize(self):
        self.write_raw('RST;')

    def get_idn(self) -> Dict[str, Optional[str]]:
        IDN_str = self.ask_raw('OIDN')
        vendor = 'Anritsu'
        model, serial = map(str.strip, IDN_str.split(' '))
        IDN: Dict[str, Optional[str]] = {
            'vendor': vendor, 'model': model,
            'serial': serial, 'firmware': None}
        return IDN
