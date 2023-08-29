# -*- coding: utf-8 -*-
"""QCoDes-Driver for Thorlab PM100D Handheld Optical Power and Energy Meter Console
https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=3341&pn=PM100D

Authors:
    Julien Barrier, <julien@julienbarrier.eu>
"""

import logging
import time
from typing import Optional, Any

from qcodes.instrument import VisaInstrument
from qcodes.parameters import Parameter, create_on_off_val_mapping
import qcodes.validators as vals

log = logging.getLogger(__name__)


class Thorlab_PM100D(VisaInstrument):
    """
    Class to represent a Thorlab PM100D optical powermeter
    
    status: beta-version
    
    Args:
        name (str): name for the instrument
        address (str): Visa Resource name to connect
        terminator (str): Visa terminator
        timeout (float, optional). Visa timeout. default to 20s
    """
    def __init__(self,
                 name: str,
                 address: Optional[str] = None,
                 terminator='\n',
                 timeout: float = 20,
                 **kwargs: Any):
        super().__init__(name, address, terminator=terminator, **kwargs)
        self._timeout = timeout
        self._timeout_pwr = 120

        self.averaging = Parameter(
            'averaging',
            label='Averaging rate',
            get_cmd='AVER?',
            set_cmd='AVER',
            val_mapping=create_on_off_val_mapping(on_val='1', off_val='0'),
            vals=vals.Ints(0, 1),
            instrument=self
        )

        self.wavelength = Parameter(
            'wavelength',
            label='Detected wavelength',
            unit='m',
            get_cmd=self._get_wavelength,
            set_cmd=self._set_wavelength,
            vals=vals.Numbers(185e-9, 25e-6),
            instrument=self
        )

        self.power = Parameter(
            "power",
            label='Measured power',
            unit="W",
            get_cmd=self._get_power,
            vals=vals.Numbers(),
            instrument=self
        )

        self.write('STAT:OPER:PTR 512')
        self.write('STAT:OPER:NTR 0')
        self.ask('STAT:OPER?')
        self._check_error()
        self.averaging(300)
        self._set_conf_power()

        self.connect_message()

    def _check_error(self) -> None:
        err = self.ask('SYST:ERR?')
        if err[:2] != '+0':
            raise RuntimeError(f'PM100D call failed with error: {err}')

    def _set_wavelength(self, value: float) -> None:
        value_in_nm = value*1e9
        self.write(f'SENS:CORR:WAV {value_in_nm}')

    def _get_wavelength(self) -> float:
        value_in_nm = self.ask('SENS:CORR:WAV?')
        return float(value_in_nm)/1e9

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
        oper = self.ask('STAT:OPER?')
        start = time.process_time()
        time_spent = 0.
        while oper != str(512) and time_spent < self._timeout_pwr:
            oper = self.ask('STAT:OPER?')
            time_spent = time.process_time()-start
        power = self.ask('FETC?')
        self._check_error()
        return float(power)