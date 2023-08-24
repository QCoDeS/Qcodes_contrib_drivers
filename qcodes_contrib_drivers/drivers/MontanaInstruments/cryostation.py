# -*- coding: utf-8 -*-
"""QCoDeS-Driver for Montana Instruments Cryostation.
Tested on a cryostation s50
https://www.montanainstruments.com/products/s50

Authors:
    Julien Barrier, <julien@julienbarrier.eu>
"""

import logging
from time import sleep
from typing import Optional, Any, Dict

from qcodes.instrument import IPInstrument
from qcodes.parameters import Parameter
from qcodes import validators as vals

log = logging.getLogger(__name__)


class MontanaInstruments_Cryostation(IPInstrument):
    """
    Class to represent a Montana Instruments Cryostation.
    
    status: beta-version
    
    Args:
        name (str): name for the instrument
        address (str): IP address for the resource to connect
        port (int): Port to connect IP
        timeout (float, optional). Visa timeout. Defaults to 20s.
    """

    def __init__(
            self,
            name: str,
            address: Optional[str] = None,
            port: Optional[int] = None,
            timeout: float = 20,
            **kwargs: Any) -> None:
        super().__init__(name, address=address, port=port,
                         terminator='', timeout=timeout, **kwargs)
        self._address = address
        self._port = port

        self.temp_setpoint = Parameter(
            name='temp_setpoint',
            unit='K',
            label='Temperature setpoint',
            get_cmd=self._parse_command('GTSP'),
            set_cmd=self._set_temp,
            get_parser=self._parse_temp,
            vals=vals.Numbers(min_value=2, max_value=295),
            instrument=self
        )

        self.temp_sample = Parameter(
            name='temp_sample',
            unit='K',
            label='Temperature sample',
            get_cmd=self._parse_command('GST'),
            get_parser=self._parse_temp,
            vals=vals.Numbers(),
            instrument=self
        )

        self.temp_platform = Parameter(
            name='temp_platform',
            unit='K',
            label='Temperature platform',
            get_cmd=self._parse_command('GPT'),
            get_parser=self._parse_temp,
            vals=vals.Numbers(),
            instrument=self
        )

        self.temp_stage1 = Parameter(
            name='temp_stage1',
            unit='K',
            label='Temperature Stage 1',
            get_cmd=self._parse_command('GS1T'),
            get_parser=self._parse_temp,
            vals=vals.Numbers(),
            instrument=self
        )

        self.temp_stage2 = Parameter(
            name='temp_stage2',
            unit='K',
            label='Temperature Stage 2',
            get_cmd=self._parse_command('GS2T'),
            get_parser=self._parse_temp,
            vals=vals.Numbers(),
            instrument=self
        )

        self.power_heater_platform = Parameter(
            name='power_heater_platform',
            unit='W',
            label='Platform heater power',
            get_cmd=self._parse_command('GPHP'),
            get_parser=self._parse_temp,
            vals=vals.Numbers(),
            instrument=self
        )

        self.power_heater_stage1 = Parameter(
            name='power_heater_stage1',
            unit='W',
            label='Stage 1 heater power',
            get_cmd=self._parse_command('GS1HP'),
            get_parser=self._parse_temp,
            vals=vals.Numbers(),
            instrument=self
        )

        self.temp_stability = Parameter(
            name='temp_stability',
            unit='K',
            label='temperature stability sample stage',
            get_cmd=self._parse_command('GSS'),
            get_parser=self._parse_temp,
            vals=vals.Numbers(),
            instrument=self
        )

        self.connect_message()

    def get_idn(self) -> Dict[str, Optional[str]]:
        """ Return the Instrument Identifier Message """
        idstr = self.ask(self._parse_command('*IDN?'))
        idparts = [p.strip() for p in idstr.split(':', 4)][1:]
        return dict(zip(idstr, idparts))

    def start_cooldown(self) -> None:
        self.log.info('Start cooldown.')
        self.write(self._parse_command('SCD'))

    def standby(self) -> None:
        self.log.info('Standby.')
        self.write(self._parse_command('SSB'))

    def stop_automation(self) -> None:
        self.log.info('Stop automation.')
        self.write(self._parse_command('STP'))

    def start_warmup(self) -> None:
        self.log.info('Start warmup.')
        self.write(self._parse_command('SWU'))

    def set_temp_and_wait(self, setpoint: float) -> None:
        self.log.info('Set temperature and wait until it is stable.')
        self.temp_setpoint.set(setpoint)
        sleep(10)
        while self.temp_stability.get() > 0.2:
            sleep(10)
        return self.temp_setpoint.get()

    def wait_stability(self, time: float = 10) -> None:
        self.log.info('Wait until the temperature is stable')
        stability = self.temp_stability.get()
        while stability > 0.02 or stability < 0:
            sleep(time)
            stability = self.temp_stability.get()

    def _set_temp(self, setpoint: float):
        self.ask_raw(self._parse_command(f'STSP{setpoint}'))

    def _parse_command(self, command):
        try:
            str(command)
        except Exception as error:
            raise ValueError('command to Montana cannot be converted to string') from error
        return f'{len(command):02d}' + command

    def _parse_temp(self, msg: str) -> float:
        temp = msg[2:]
        try:
            return float(temp)
        except Exception as error:
            raise ValueError('output from Montana cannot be converted to float') from error
        