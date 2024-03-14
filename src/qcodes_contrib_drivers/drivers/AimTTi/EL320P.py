from typing import List, Dict, Union, Optional, Sequence, Any, Tuple
import numpy as np
import time

from qcodes.instrument.visa import VisaInstrument
import qcodes.utils.validators as vals

class EL320P(VisaInstrument):
    """Qcodes driver for AIM & Thurlby Thandar EL320P power supply (BlueFors 4K warmup heater).
    """
    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, terminator='\r\n', **kwargs)
        self.visa_handle.baud_rate = 9600
        self.add_parameter(
            name='voltage_set',
            label='Voltage setting',
            unit='V',
            get_cmd='V?',
            get_parser=self._get_parser,
            set_cmd='V {}',
            vals=vals.Numbers(0,30),
            docstring='Voltage setting'
            )
        self.add_parameter(
            name='voltage_out',
            label='Actual output voltage',
            unit='V',
            get_cmd='VO?',
            get_parser=self._get_parser,
            docstring='Actual output voltage'
            )
        self.add_parameter(
            name='current_set',
            label='Current setting',
            unit='A',
            get_cmd='I?',
            get_parser=self._get_parser,
            set_cmd='I {}',
            vals=vals.Numbers(0.01,2),
            docstring='Current setting'
            )
        self.add_parameter(
            name='current_out',
            label='Actual output current',
            unit='A',
            get_cmd='IO?',
            get_parser=self._get_parser,
            docstring='Actual output current'
            )
        self.add_parameter(
            name='mode',
            label='Mode',
            get_cmd='M?',
            get_parser=str,
            docstring='Device mode: constant current or constant voltage'
            )
        self.add_parameter(
            name='output',
            label='Output status',
            get_cmd='OUT?',
            get_parser=self._output_parser,
            set_cmd='{}',
            vals=vals.Enum('ON', 'OFF')
            )
        self.add_parameter(
            name='error',
            label='Error message',
            get_cmd='ERR?',
            get_parser=self._error_parser,
            val_mapping={'OK': 0, 'Command not recognized': 1, 'Value outside of instrument limits': 2},
            vals=vals.Enum(0,1,2)
            )
        self.connect_message()

    def _get_parser(self, response):
        return float(response[2:])

    def _output_parser(self, response):
        return response[4:]

    def _error_parser(self, response):
        return int(response[-1])
