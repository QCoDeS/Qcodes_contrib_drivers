from typing import Any, Dict, Optional

from qcodes import VisaInstrument
from qcodes.utils.validators import Numbers, Enum

class N5183M(VisaInstrument):
    """
    This is the qcodes driver for Keysight/Agilent N5183M.
    """

    def __init__(self, name: str, address: str, min_power: int = -144, max_power: int = 19, **kwargs: Any):
        super().__init__(name, address, terminator='\n', **kwargs)

        # Query the instrument for installed options
        self._options = self.ask('*OPT?').split(',')

        if '1E1' in self._options: # Mechanical attenuator option
            min_power = -130

        if '1EA' in self._options: # High power output option
            max_power = 30

        freq_dict = {'501':1e9, '503':3e9, '506':6e9, '513': 13e9, '520':20e9, '532': 31.8e9, '540': 40e9}

        for opt in self._options:
            if opt in freq_dict.keys():
                max_freq = freq_dict[opt]
                break
        
        if ('UNU' in self._options) or ('UNW' in self._options):
            self.add_parameter('pulse_mod',
                               label='Pulse Modulation',
                               get_cmd='PULM:STAT?',
                               set_cmd='PULM:STAT {}',
                               val_mapping={'on': 1, 'off': 0})

        self.add_parameter('power',
                           label='Power',
                           get_cmd='SOUR:POW?',
                           get_parser=float,
                           set_cmd='SOUR:POW {:.2f}',
                           unit='dBm',
                           vals=Numbers(min_value=min_power,max_value=max_power))

        self.add_parameter('frequency',
                           label='Frequency',
                           get_cmd='SOUR:FREQ?',
                           get_parser=float,
                           set_cmd='SOUR:FREQ {:.2f}',
                           unit='Hz',
                           vals=Numbers(min_value=100e3,max_value=max_freq))

        self.add_parameter('phase_offset',
                           label='Phase Offset',
                           get_cmd='SOUR:PHAS?',
                           get_parser=float,
                           set_cmd='SOUR:PHAS {:.2f}',
                           unit='rad'
                           )

        self.add_parameter('output_modulation',
                           get_cmd=':OUTP:MOD?',
                           set_cmd='OUTP:STAT OFF;:OUTP:MOD {}',
                           val_mapping={'on': 1, 'off': 0})
        
        self.add_parameter('ref_source',
                           get_cmd=self._get_ref_source,
                           set_cmd=self._set_ref_source,
                           vals=Enum("EXT", "INT", "AUTO"))

        self.add_parameter('rf_output',
                           get_cmd='OUTP:STAT?',
                           set_cmd='OUTP:STAT {}',
                           val_mapping={'on': 1, 'off': 0})

        self.connect_message()

    def _get_ref_source(self):
        isauto = self.ask(":ROSC:SOUR:AUTO?")

        if isauto == "1":
            return "AUTO"
        else:
            return self.ask(":ROSC:SOUR?")
        
    def _set_ref_source(self, source:str):
        if source == "AUTO":
            self.write(":ROSC:SOUR:AUTO ON;")
        else:
            self.write(f":ROSC:SOUR {source};")

    def get_idn(self) -> Dict[str, Optional[str]]:
        IDN_str = self.ask_raw('*IDN?')
        vendor, model, serial, firmware = map(str.strip, IDN_str.split(','))
        IDN: Dict[str, Optional[str]] = {
            'vendor': vendor, 'model': model,
            'serial': serial, 'firmware': firmware}
        return IDN

