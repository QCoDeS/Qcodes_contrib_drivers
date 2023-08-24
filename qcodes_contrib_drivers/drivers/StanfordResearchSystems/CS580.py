# -*- coding: utf-8 -*-
"""QCoDeS-Driver for Stanford Research Systems CS580 current source:
https://www.thinksrs.com/products/cs580.html

Authors:
    Julien Barrier, <julien@julienbarrier.eu>
"""

import logging
from typing import Optional, Any, Dict

from qcodes.instrument import VisaInstrument
from qcodes.parameters import Parameter, create_on_off_val_mapping
from qcodes import validators as vals

log = logging.getLogger(__name__)


class CS580(VisaInstrument):
    """
    Class to represent an SRS CS580 current source

    status: beta-version

    Args:
        name (str): name for the instrument
        address (str): Visa resource name to connect
        terminator (str): Visa terminator
    """

    _gains = {
        1e-9: 0, 10e-9: 1, 100e-9: 2,
        1e-6: 3, 10e-6: 4, 100e-6: 5,
        1e-3: 6, 10e-3: 7, 50e-3: 8
    }

    _n_to_gains = {g: k for k, g in _gains.items()}

    _overload_status = {
        0: 'None',
        1: 'Compliance limit reached',
        2: 'Analog input overload',
        3: 'Compliance limit reached and analog input overload'
    }

    def __init__(
            self,
            name: str,
            address: str,
            terminator: str = '\r\n',
            **kwargs: Any) -> None:
        super().__init__(name, address=address, terminator=terminator,
                         **kwargs)

        self.gain = Parameter(
            'gain',
            label='Gain',
            unit='A/V',
            get_cmd='GAIN?',
            set_cmd='GAIN {:d}',
            get_parser=self._parse_get_gain,
            set_parser=self._parse_set_gain,
            instrument=self
        )

        self.input = Parameter(
            'input',
            label='Analog input',
            get_cmd='INPT?',
            set_cmd='INPT{:d}',
            vals=vals.Ints(0, 1),
            instrument=self
        )

        self.speed = Parameter(
            'speed',
            label='Speed',
            get_cmd='RESP?',
            set_cmd='RESP{:d}',
            val_mapping={
                'fast': 0,
                'slow': 1},
            vals=vals.Ints(0, 1),
            instrument=self
        )

        self.shield = Parameter(
            'shield',
            label='Inner shield',
            get_cmd='SHLD?',
            set_cmd='SHLD{:d}',
            val_mapping={
                'guard': 0,
                'return': 1},
            vals=vals.Ints(0, 1),
            instrument=self
        )

        self.isolation = Parameter(
            'isolation',
            label='Isolation',
            get_cmd='ISOL?',
            set_cmd='ISOL{:d}',
            val_mapping={
                'ground': 0,
                'float': 1},
            vals=vals.Ints(0, 1),
            instrument=self
        )

        self.output = Parameter(
            'output',
            label='Output',
            get_cmd='SOUT?',
            set_cmd='SOUT{:d}',
            val_mapping=create_on_off_val_mapping(on_val='1', off_val='0'),
            vals=vals.Ints(0, 1),
            instrument=self
        )

        self.current = Parameter(
            'current',
            label='DC current',
            unit='A',
            get_cmd='CURR?',
            set_cmd='CURR{:e}',
            vals=vals.Numbers(-100e-3, 100e-3),
            instrument=self
        )

        self.voltage = Parameter(
            name='voltage',
            label='Compliance voltage',
            unit='V',
            get_cmd='VOLT?',
            set_cmd='VOLT{:f}',
            vals=vals.Numbers(min_value=0.0, max_value=50.0),
            instrument=self
        )

        self.alarm = Parameter(
            name='alarm',
            label='Audible alarms',
            get_cmd='ALRM?',
            set_cmd='ALRM{:d}',
            val_mapping=create_on_off_val_mapping(on_val='1', off_val='0'),
            vals=vals.Ints(0, 1),
            instrument=self
        )

        self.connect_message()

    def get_idn(self) -> Dict[str, Optional[str]]:
        """ Return the Instrument Identifier Message """
        idstr = self.ask('*IDN?')
        idparts = [p.strip() for p in idstr.split(',', 4)][1:]
        return dict(zip(('vendor', 'model, serial', 'firmware'), idparts))

    def get_overload(self) -> str:
        """ Reads the current avlue of the signal overload status."""
        self.log.info('Get overload status')
        ovd_status = self.ask('OVLD?')
        try:
            return self._overload_status[int(ovd_status)]
        except ValueError:
            if isinstance(ovd_status, str):
                return ovd_status
            else:
                raise ValueError

    def reset(self) -> None:
        """Reset the CS580 to its default configuration"""
        self.log.info('Reset CS580 to its default configuration.')
        self.write('*RST')
        return None

    def _parse_get_gain(self, s: int) -> float:
        return self._n_to_gains[int(s)]

    def _parse_set_gain(self, s: float) -> int:
        return self._gains[s]
