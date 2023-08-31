# -*- coding: utf-8 -*-
"""QCoDes-Driver for Thorlab PM100D Handheld Optical Power and Energy Meter Console
https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=3341&pn=PM100D

Authors:
    Julien Barrier, <julien@julienbarrier.eu>
"""

import logging
from time import sleep
from typing import Any

from qcodes.instrument import VisaInstrument
from qcodes.parameters import Parameter, create_on_off_val_mapping
import qcodes.validators as vals

log = logging.getLogger(__name__)


class Thorlab_PM100D(VisaInstrument):
    """
    Class to represent a Thorlab PM100D optical powermeter
    
    status: beta-version
    
    Args:
        name: name for the instrument
        address: Visa Resource name to connect
        terminator: Visa terminator
        timeout. Visa timeout.
    """
    def __init__(self,
                 name: str,
                 address: str,
                 terminator: str = '\n',
                 timeout: float = 20,
                 **kwargs: Any):
        super().__init__(name, address, terminator=terminator,
                         timeout=timeout, **kwargs)

        self.averaging = Parameter(
            'averaging',
            label='Averaging rate',
            get_cmd='AVER?',
            set_cmd='AVER',
            vals=vals.Numbers(),
            instrument=self
        )

        self.wavelength = Parameter(
            'wavelength',
            label='Detected wavelength',
            unit='m',
            get_cmd='SENS:CORR:WAV?',
            set_cmd='SENS:CORR:WAV {}',
            scale=1e9,
            vals=vals.Numbers(185e-9, 25e-6),
            instrument=self
        )

        self.power = Parameter(
            'power',
            label='Measured power',
            unit='W',
            get_cmd=self._get_power,
            vals=vals.Numbers(),
            instrument=self
        )

        self.attenuation = Parameter(
            'attenuation',
            label='Attenuation',
            unit='dB',
            get_cmd='CORR?',
            get_parser=float,
            set_cmd='CORR {}',
            set_parser=float,
            vals=vals.Numbers(-60, 60),
            instrument=self
        )

        self.power_range = Parameter(
            'power_range',
            label='Power range',
            unit='W',
            get_cmd='SENS:POW:RANG:UPP?',
            set_cmd='SENS:POW:RANG:UPP {}',
            get_parser=float,
            set_parser=float,
            vals=vals.Numbers(),
            instrument=self
        )

        self.auto_range = Parameter(
            'auto_range',
            label='Auto range power',
            get_cmd='SENS:POW:RANG:AUTO?',
            set_cmd='SENS:POW:RANG:AUTO {}',
            val_mapping=create_on_off_val_mapping(on_val='1', off_val='0'),
            vals=vals.Ints(0, 1),
            instrument=self
        )

        self.frequency = Parameter(
            'frequency',
            unit='Hz',
            get_cmd='MEAS:FREQ?',
            get_parser=float,
            vals=vals.Numbers(),
            instrument=self
        )

        self.current = Parameter(
            'current',
            label='Current',
            unit='A',
            get_cmd='MEAS:CURR?',
            get_parser=float,
            vals=vals.Numbers(),
            instrument=self
        )

        self.current_range = Parameter(
            'current_range',
            label='Current range',
            unit='A',
            get_cmd='SENS:CURR:RANG:UPP?',
            get_parser=float,
            vals=vals.Numbers(),
            instrument=self
        )

        self.zero_value = Parameter(
            'zero_value',
            unit='W',
            get_cmd='CORR:COLL:ZERO:MAGN?',
            get_parser=float,
            vals=vals.Numbers(),
            instrument=self
        )

        self.beam_diameter = Parameter(
            'beam_diameter',
            label='Beam diameter',
            unit='m',
            get_cmd='CORR:BEAM?',
            set_cmd='CORR:BEAM {}',
            scale=1e3,
            vals=vals.Numbers(),
            instrument=self
        )

        self._set_transition_filter(512, 0)
        self.averaging(300)
        self._set_conf_power()

        self.connect_message()

    def _check_error(self) -> None:
        err = self.ask('SYST:ERR?')
        if err[:2] != '+0':
            raise RuntimeError(f'PM100D call failed with error: {err}')

    def _set_conf_power(self) -> None:
        """Set configuration to power mode
        """
        self.write('CONF:POW')  # set config to power mode
        self.ask('ABOR;:STAT:OPER?')
        self.write('INIT')
        return None

    def _get_power(self) -> float:
        """Get the power
        """
        self._set_conf_power()
        self.write('MEAS:POW')
        sleep(.2)
        power = self.ask('FETC?')
        return float(power)

    def _set_transition_filter(self, positive: int, negative: int) -> None:
        """Apply filters
        """
        self.write(f'STAT:OPER:PTR {positive}')
        sleep(.2)
        self.write(f'STAT:OPER:NTR {negative}')
        sleep(5)
        self.ask('STAT:OPER?')  # clear register
        sleep(.2)
