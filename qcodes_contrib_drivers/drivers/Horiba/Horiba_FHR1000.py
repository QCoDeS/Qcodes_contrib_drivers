from __future__ import annotations

import abc
import ctypes
import os
import pathlib
from typing import Mapping, Any, Sequence
from typing_extensions import Literal

from qcodes import InstrumentChannel, ChannelList
from qcodes.instrument import Instrument, InstrumentBase
from ._private.fhr_client import FHRClient


class SpeError(Exception):
    """Error raised by the dll."""


class Dispatcher:
    """Implements the interface to the motors."""
    _ERROR_CODES = {0: 'NoErr',
                    1: 'errInvalidDispatcherName',
                    2: 'errInvalidFunctionName',
                    3: 'errInvalidParameter',
                    4: 'errConnectionError',
                    5: 'errConnectionTimeout',
                    6: 'errWrongResult',
                    7: 'errAbort',
                    0xFFFFFFFF: 'errForce32bit'}

    def __init__(self, cli, handle):
        self.cli = cli
        self.handle = handle

    def error_check(self, code: int):
        if code != 0:
            raise SpeError(self._ERROR_CODES.get(code))


class PortChannel(Dispatcher, InstrumentChannel):
    """Manages instrument communication."""

    def __init__(self, parent: InstrumentBase, name: str, cli, handle,
                 port: int):
        Dispatcher.__init__(self, cli, handle)
        InstrumentChannel.__init__(self, parent, name)
        self.port = ctypes.c_int(port)

    def open(self):
        """Open serial port."""
        code, _ = self.cli.SpeCommand(self.handle, 'Port', 'Open', self.port)
        self.error_check(code)

    def close(self):
        """Close serial port."""
        code, _ = self.cli.SpeCommand(self.handle, 'Port', 'Close', None)
        self.error_check(code)

    def is_open(self) -> bool:
        """Check if the port is open."""
        par = ctypes.c_int()
        code, value = self.cli.SpeCommand(self.handle, 'Port', 'IsOpen', par)
        self.error_check(code)
        return bool(value)

    def set_baud_rate(self, baud_rate: int = 115200):
        """Set port baud rate for opened pot. Should be the default."""
        rate = ctypes.c_int(baud_rate)
        code, _ = self.cli.SpeCommand(self.handle, 'Port', 'SetBaudRate', rate)
        self.error_check(code)

    def set_timeout(self, timeout: int = 90000):
        """Set timeout in milliseconds."""
        timeout = ctypes.c_int(timeout)
        code, _ = self.cli.SpeCommand(self.handle, 'Port', 'SetTimeout',
                                      timeout)
        self.error_check(code)


class MotorChannel(Dispatcher, InstrumentChannel, metaclass=abc.ABCMeta):
    """ABC for the various motors of the device."""

    def __init__(self, parent: InstrumentBase, name: str, cli, handle,
                 motor: int):
        Dispatcher.__init__(self, cli, handle)
        InstrumentChannel.__init__(self, parent, name)
        self.motor = motor
        self.step: int | None = None

    @classmethod
    @property
    def type(cls) -> str:
        try:
            return cls.__name__.removesuffix('Channel')
        except AttributeError:
            # Python 3.8
            return cls.__name__[:-7]

    @property
    @abc.abstractmethod
    def unit(self) -> str:
        pass

    def set_id(self, i: int):
        """Set motor ID.

        This is the `Addr` address in LabSpec6."""
        i = ctypes.c_int(i)
        code, _ = self.cli.SpeCommand(self.handle, f'{self.type}{self.motor}',
                                      'SetID', i)
        self.error_check(code)

    def get_id(self) -> int:
        """Get motor ID."""
        i = ctypes.c_int()
        code, value = self.cli.SpeCommand(self.handle,
                                          f'{self.type}{self.motor}', 'GetID',
                                          i)
        self.error_check(code)
        return value

    def stop(self):
        """Stop motor."""
        code, _ = self.cli.SpeCommand(self.handle, f'{self.type}{self.motor}',
                                      'Stop', None)
        self.error_check(code)

    def set_position(self, pos: int):
        """Set motor position. It return final motor position after
        movement.

        For grating motor the position unit depends on 'Step' value in
        SpeSetup structure. If 'Step' = 1 the motor position is raw
        motor steps. Otherwise it is the position in picometers.

        For slit motors the position in motor steps is the 'Position'
        value multiplied by 'Step' value from SpeSetup.

        For DC motors, the position is binary.
        """
        pos = ctypes.c_int(pos)
        code, _ = self.cli.SpeCommand(self.handle, f'{self.type}{self.motor}',
                                      'SetPosition', pos)
        self.error_check(code)


class DCChannel(MotorChannel):
    """Handles DC motors (with binary positions)."""

    def __init__(self, parent: InstrumentBase, name: str, cli, handle, motor: int):
        MotorChannel.__init__(self, parent, name, cli, handle, motor)

        self.add_parameter('position',
                           label=f'DC Motor {self.motor} position',
                           set_cmd=self.set_position,
                           unit=self.unit)

    @property
    def unit(self) -> str:
        return ''


class SlitChannel(MotorChannel):
    """Handles the linear slit motors of the device."""

    def __init__(self, parent: InstrumentBase, name: str, cli, handle, motor: int):
        # Cannot use super() since parent also defines the position parameter
        MotorChannel.__init__(self, parent, name, cli, handle, motor)

        self.add_parameter('position',
                           label=f'Slit {self.motor} position',
                           get_cmd=self.get_position,
                           set_cmd=self.set_position,
                           unit=self.unit)

    @property
    def unit(self) -> str:
        return 'pm'

    def init(self, offset: int):
        """Initialize motor with offset position (optical zero order
        position in motor steps)."""
        offset = ctypes.c_int(offset)
        code, _ = self.cli.SpeCommand(self.handle, f'{self.type}{self.motor}',
                                      'Init', offset)
        self.error_check(code)

    def set_setup(self,
                  min_speed: int = 50,
                  max_speed: int = 600,
                  ramp: int = 650,
                  backlash: int = 500,
                  step: int = 2,
                  revers: bool = False):
        """Write motor setup data.

        Parameters
        ----------
        min_speed : int
            Minimal speed
        max_speed : int
            Maximal speed
        ramp : int
            Acceleration
        backlash : int
            Backlash (~+-500..2000)
        step : int
            Operation mode:
                - 1: position in motor steps
                - 0, 2, 3 ...: position in picometers
        revers : bool
            Rotation direction:
                - 0: direct
                - 1: inverse
        """
        code, _ = self.cli.SpeCommandSetup(
            self.handle, f'{self.type}{self.motor}',
            fields=(min_speed, max_speed, ramp, backlash, step, revers)
        )
        self.error_check(code)
        self.step = step
        self.position.unit = self.unit

    def get_position(self) -> int:
        """Get current position. The result depends on 'Step' value
        similar to "SetPosition" parameter value."""
        if self.step is None:
            raise RuntimeError('Please initialize the slit using set_setup()')

        pos = ctypes.c_int()
        code, value = self.cli.SpeCommand(self.handle,
                                          f'{self.type}{self.motor}',
                                          'GetPosition', pos)
        self.error_check(code)
        return value * self.step


class GratingChannel(SlitChannel):
    """Handles the grating rotation motors of the device."""

    def __init__(self, parent: InstrumentBase, name: str, cli, handle, motor: int):
        # Cannot use super() since parents also define the position parameter
        MotorChannel.__init__(self, parent, name, cli, handle, motor)

        self.add_parameter('position',
                           label=f'Grating {self.motor} position',
                           get_cmd=self.get_position,
                           set_cmd=self.set_position,
                           unit=self.unit)
        self.add_parameter('shift',
                           label='Zero order shift',
                           set_cmd=self.set_shift,
                           unit=self.unit)

    @property
    def unit(self) -> str:
        if self.step == 1:
            return 'motor steps'
        elif self.step is None:
            return ''
        else:
            return 'pm'

    def set_ini_params(self,
                       phase: Literal[1, 2, 3],
                       min_speed: int = 50,
                       max_speed: int = 600,
                       ramp: int = 600):
        """Motor initialization parameters.

        Parameters
        ----------
        phase : {1, 2, 3}
            Initialization phase.
        min_speed : int
            Minimal speed
        max_speed : int
            Maximal speed
        ramp : int
            Acceleration
        """
        code, _ = self.cli.SpeCommandIniParams(
            self.handle, f'{self.type}{self.motor}',
            fields=(phase, min_speed, max_speed, ramp)
        )
        self.error_check(code)

    def set_shift(self, shift: int):
        """Set zero order shift (not available now)."""
        raise NotImplementedError


class HoribaFHR1000(Instrument):

    def __init__(self,
                 name: str,
                 port: int,
                 dll_dir: str | os.PathLike | pathlib.Path,
                 gratings_addr: Sequence[int],
                 slits_addr: Sequence[int],
                 dcs_addr: Sequence[int],
                 metadata: Mapping[Any, Any] | None = None,
                 label: str | None = None):

        self.cli = FHRClient(dll_dir=dll_dir)
        self.handle: int = self.cli.CreateSpe()

        super().__init__(name, metadata, label)

        dcs = ChannelList(self, 'dcs', DCChannel)
        slits = ChannelList(self, 'slits', SlitChannel)
        gratings = ChannelList(self, 'gratings', GratingChannel)

        for i, addr in enumerate(dcs_addr, start=1):
            dcs.append(DCChannel(self, f'DC_{i}', self.cli, self.handle, i))
            dcs[-1].set_id(addr)
        for i, addr in enumerate(slits_addr, start=1):
            slits.append(SlitChannel(self, f'slit_{i}', self.cli, self.handle,
                                     i))
            slits[-1].set_id(addr)
        for i, addr in enumerate(gratings_addr, start=1):
            gratings.append(GratingChannel(self, f'grating_{i}', self.cli,
                                           self.handle, i))
            gratings[-1].set_id(addr)

        self.add_submodule('port', PortChannel(self, 'port', self.cli,
                                               self.handle, port))
        self.add_submodule('dcs', dcs.to_channel_tuple())
        self.add_submodule('slits', slits.to_channel_tuple())
        self.add_submodule('gratings', gratings.to_channel_tuple())

        self.connect()

    def connect(self):
        if not self.port.is_open():
            self.port.open()
        self.port.set_baud_rate(115200)

    def disconnect(self):
        if self.port.is_open():
            self.port.close()

    def close(self) -> None:
        self.disconnect()
        self.cli.DeleteSpe(self.handle)
        super().close()
