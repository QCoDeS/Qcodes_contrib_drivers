from __future__ import annotations

import time
from functools import wraps
from typing import Any, Callable, TypeVar

from qcodes import Parameter, VisaInstrument
from qcodes.parameters import Group, GroupParameter, create_on_off_val_mapping

_SOC = '.'
"""Start Of Command."""
_SOR = '#'
"""Start Of Response."""
_COMMAND_TIMEOUT = 3
"""The required timeout between commands."""
_WATCHDOG_TIMEOUT = 5
"""The timeout after which another serial watchdog command needs to be
sent to establish communication."""
_ERROR_CODES = {'\x30': 'No Error',
                '\x31': 'Checksum Error',
                '\x32': 'Bad Command',
                '\x33': 'Out of Bound Qualifier'}
_MODE_STATUS = {'\x30': 'Auto Start',
                '\x31': 'Stand By',
                '\x32': 'Chiller Run',
                '\x33': 'Safety Default'}
_ALARM_STATUS = {'\x30': 'No Alarms',
                 '\x31': 'Alarm'}
_CHILLER_STATUS = {'\x30': 'OFF',
                   '\x31': 'ON'}
_DRYER_STATUS = {'\x30': 'OFF',
                 '\x31': 'ON'}

_T = TypeVar('_T')


def _ascii_checksum(s: str) -> str:
    return f"{sum(s.encode('ascii')) & 0xFF:X}"


def _encode_cmd(fun: Callable[[Any, Any], _T]) -> Callable[[Any, Any], _T]:
    """Encodes a command into valid format by appending the checksum."""

    @wraps(fun)
    def wrapped(self, cmd: str) -> _T:
        cmd = cmd.upper()
        if not cmd.startswith(_SOC):
            cmd = _SOC + cmd
        return fun(self, cmd + _ascii_checksum(cmd))

    return wrapped


def _command_timeout(fun: Callable[[Any, Any], _T]) -> Callable[[Any, Any], _T]:
    """Waits for the timeout before another command can be sent."""

    @wraps(fun)
    def wrapped(self, cmd: str) -> _T:
        target = self._command_timestamp + _COMMAND_TIMEOUT
        while (now := time.time()) < target:
            time.sleep(0.1)
        self._command_timestamp = now
        return fun(self, cmd)

    return wrapped


def _watchdog_timeout(fun: Callable[[Any, Any], _T]) -> Callable[[Any, Any], _T]:
    """Ensures communication is established using watchdog signal."""

    @wraps(fun)
    def wrapped(self, cmd: str) -> _T:
        elapsed_time = time.time() - self._command_timestamp
        if not cmd.startswith('.U') and elapsed_time > _WATCHDOG_TIMEOUT:
            self._watchdog()
        return fun(self, cmd)

    return wrapped


class ThermotekT255p(VisaInstrument):
    """Driver for the Thermotek T255p laser chiller."""

    def __init__(self, name: str, address: str, timeout: float = 3,
                 device_clear: bool = True, visalib: str | None = None,
                 pyvisa_sim_file: str | None = None, **kwargs: Any):
        super().__init__(name, address, timeout, terminator='\r',
                         device_clear=device_clear, visalib=visalib,
                         pyvisa_sim_file=pyvisa_sim_file, **kwargs)

        self._command_timestamp: float = 0

        self.enabled = Parameter(
            'enabled',
            label='Chiller running',
            set_cmd='G{}',
            get_cmd=lambda: self._watchdog()[2],
            val_mapping=create_on_off_val_mapping('1', '0'),
            instrument=self
        )
        """Mode Select (0: Stand By, 1: Run Mode)."""
        self.temperature_setpoint = GroupParameter(
            'temperature_setpoint',
            label='Set point Temperature',
            unit='°C',
            # Drop first byte (command echo in this case). Need to check for
            # type since for some reason group parameters pass the set value
            # through the get_parser...
            get_parser=lambda v: int(v[1:] if isinstance(v, str) else v) / 10,
            set_parser=lambda v: int(v * 10),
            instrument=self
        )
        self.max_power_setpoint = GroupParameter(
            'max_power_setpoint',
            label='Max Power Setting',
            unit='W',
            get_parser=float,
            instrument=self
        )
        self.setpoints = Group(
            [self.temperature_setpoint, self.max_power_setpoint],
            set_cmd='M{temperature_setpoint:+d}',
            get_cmd='H0'
        )
        self.manifold_temperature = Parameter(
            'manifold_temperature',
            label='Manifold temperature',
            unit='°C',
            get_cmd='I',
            get_parser=lambda v: int(v) / 100,
            instrument=self
        )
        self.temperature_sense_mode = Parameter(
            'temperature_sense_mode',
            label='External Temp Sense Mode',
            get_cmd=False,
            set_cmd='O{}',
            val_mapping={'Internal': '0', 'External': '1'},
            instrument=self
        )

        self.connect_message()

    @_encode_cmd
    @_watchdog_timeout
    @_command_timeout
    def write(self, cmd: str) -> None:
        super().write(cmd)
        # Flush read buffer since otherwise the write response will be returned
        # the next time ask() is called
        self.visa_handle.read()

    @_encode_cmd
    @_watchdog_timeout
    @_command_timeout
    def ask(self, cmd: str) -> str:
        # A command has the following structure:
        # 1B    soc
        # 1B    command code
        # nB    n optional qualifier bytes (values passed to the device)
        # 2B    checksum
        # The response has the following structure:
        # 1B    sor
        # 1B    command echo
        # 1B    comm error status
        # mB    m optional response bytes
        # 2B    checksum
        response = super().ask(cmd)
        if not response.startswith(_SOR + cmd[1]):
            self.log.error(f'Communication failed. Response was {response}')
            raise RuntimeError('Communication failed. Try again.')
        if response[-2:] != _ascii_checksum(response[:-2]):
            self.log.error(f'Checksum does not match. Response was {response}')
            raise RuntimeError('Checksum does not match.')
        if (status := _ERROR_CODES.get(response[2])) != 'No Error':
            self.log.error(f'Error code {status}. Response was {response}')
            raise RuntimeError(status)
        return response[3:-2]

    def get_idn(self) -> dict[str, str | None]:
        return {'vendor': 'Thermotek',
                'model': 'T255p',
                'serial': None,
                'firmware': None}

    def _watchdog(self) -> str:
        return self.ask('U')

    def status(self) -> dict[str, str]:
        response = self._watchdog()
        return {'Mode Status': _MODE_STATUS[response[0]],
                'Alarm Status': _ALARM_STATUS[response[1]],
                'Chiller Status': _CHILLER_STATUS[response[2]],
                'Dryer Status': _DRYER_STATUS[response[3]]}

    def alarm_state(self) -> dict[str, bool]:
        flags = self.ask('J')
        alarms = ['Float Switch', 'Hi Alarm', 'Lo Alarm', 'Sensor Alarm',
                  'EEPROM Fail', 'Watch dog']
        return {alarm: bool(int(flag)) for alarm, flag in zip(alarms, flags)}
