# -*- coding: utf-8 -*-
"""QCoDeS-Driver for Montana Instruments Cryostation.
Tested on a cryostation s50
https://www.montanainstruments.com/products/s50

Authors:
    Julien Barrier, <julien@julienbarrier.eu>
"""

import logging
import time
from typing import Optional, Any, Dict

from qcodes import Parameter, IPInstrument
from qcodes import validators as vals
from qcodes.utils.helpers import create_on_off_val_mapping


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

        #self._heater_range_auto = False
        #self._heater_range_temp = [0.03, 0.1, 0.3, 1, 12, 40]
        #self._heater_range_curr = [0.316, 1, 3.16, 10, 31.6, 100]
        #self._control_channel = 5
        #self._max_field = 14

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
        self.write(self._parse_command('SCD'))
        
    def standby(self) -> None:
        self.write(self._parse_command('SSB'))
        
    def stop_automation(self) -> None:
        self.write(self._parse_command('STP'))
        
    def start_warmup(self) -> None:
        self.write(self._parse_command('SWU'))
        
    def set_temp_and_wait(self, setpoint) -> None:
        self.temp_setpoint.set(setpoint)
        time.sleep(10)
        while self.temp_stability.get() > 0.2:
            time.sleep(10)
        return self.temp_setpoint.get()
        
    def wait_stability(self, time=10) -> None:
        stability = self.temp_stability.get()
        while stability > 0.02 or stability < 0:
            time.sleep(time)
            stability = self.temp_stability.get()

        
    def _set_temp(self, temp):
        self.ask_raw(self._parse_command('STSP{}'.format(temp)))
        
    def _parse_command(self, command):
        try:
            str(command)
        except:
            raise ValueError('command to Montana cannot be converted to string')
        return '{:02d}'.format(len(command)) + command
        
    def _parse_temp(self, msg: str) -> float:
        temp = msg[2:]
        try:
            return float(temp)
        except:
            raise ValueError('output from Montana cannot be converted to float')