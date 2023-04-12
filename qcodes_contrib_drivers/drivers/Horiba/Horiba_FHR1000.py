from __future__ import annotations

import abc
import ctypes
import os
import pathlib
import sys
from typing import Mapping, Any, Sequence

from typing_extensions import Literal

from qcodes.instrument import (Instrument, InstrumentBase, InstrumentChannel,
                               ChannelList)
from qcodes.validators import validators
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
                 motor: int, metadata: Mapping[Any, Any] | None = None,
                 label: str | None = None):
        Dispatcher.__init__(self, cli, handle)
        InstrumentChannel.__init__(self, parent, name, metadata=metadata,
                                   label=label)
        self.motor = motor

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

    def stop(self, raise_exception: bool = False):
        """Stop motor.

        Parameters
        ----------
        raise_exception : bool, default: False
            Raise an 'errAbort' exception upon successful stop.
        """
        code, _ = self.cli.SpeCommand(self.handle, f'{self.type}{self.motor}',
                                      'Stop', None)
        try:
            self.error_check(code)
        except SpeError as se:
            if raise_exception or str(se) != 'errAbort':
                raise

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


class PrecisionMotorChannel(MotorChannel, metaclass=abc.ABCMeta):
    """ABC for the precision motors of the device."""

    def __init__(self, parent: InstrumentBase, name: str, cli, handle,
                 motor: int, metadata: Mapping[Any, Any] | None = None,
                 label: str | None = None):
        super().__init__(parent, name, cli, handle, motor, metadata, label)

        self._step: int | None = None
        self._offset: int | None = None

    @property
    def step(self) -> int:
        if self._step is None:
            raise RuntimeError('Please set up the motor using set_setup()')
        return self._step

    @step.setter
    def step(self, val: int):
        self._step = val

    @property
    def offset(self) -> int:
        if self._offset is None:
            raise RuntimeError(f'Please set {type(self).__name__}.offset or '
                               'initialize the motor using init().')
        return self._offset

    @offset.setter
    def offset(self, val: int):
        self._offset = val

    def init(self, offset: int):
        """Initialize motor with offset position (optical zero order
        position in motor steps)."""
        offset = ctypes.c_int(offset)
        code, _ = self.cli.SpeCommand(self.handle, f'{self.type}{self.motor}',
                                      'Init', offset)
        self.error_check(code)
        self.offset = offset

    def set_setup(self,
                  min_speed: int = 50,
                  max_speed: int = 600,
                  ramp: int = 650,
                  backlash: int = 500,
                  step: int = 2,
                  reverse: bool = False):
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
        reverse : bool
            Rotation direction:
                - 0: direct
                - 1: inverse
        """
        code, _ = self.cli.SpeCommandSetup(
            self.handle, f'{self.type}{self.motor}',
            fields=(min_speed, max_speed, ramp, backlash, step, reverse)
        )
        self.error_check(code)
        self.step = step
        self.position.unit = self.unit

    def get_position(self) -> int:
        """Get current position. The result depends on 'Step' value
        similar to "SetPosition" parameter value."""
        pos = ctypes.c_int()
        code, value = self.cli.SpeCommand(self.handle,
                                          f'{self.type}{self.motor}',
                                          'GetPosition', pos)
        self.error_check(code)
        return value

    def get_position_relative(self) -> int:
        return self.get_position() - self.offset

    def set_position_relative(self, pos: int):
        self.set_position(pos + self.offset)


class DCChannel(MotorChannel):
    """Handles DC motors (with binary positions)."""

    def __init__(self, parent: InstrumentBase, name: str, cli, handle,
                 motor: int,
                 val_mapping: Mapping[str, Literal[0, 1]] | None = None,
                 metadata: Mapping[Any, Any] | None = None,
                 label: str | None = None):
        label = label or f'DC {motor}'
        MotorChannel.__init__(self, parent, name, cli, handle, motor, metadata,
                              label)

        self.add_parameter('position',
                           label=f'{label} position',
                           get_cmd=False,
                           set_cmd=self.set_position,
                           val_mapping=val_mapping,
                           unit=self.unit)

    @property
    def unit(self) -> str:
        return ''


class SlitChannel(PrecisionMotorChannel):
    """Handles the linear slit motors of the device."""

    def __init__(self, parent: InstrumentBase, name: str, cli, handle,
                 motor: int, min_value: int = -sys.maxsize - 1,
                 max_value: int = sys.maxsize,
                 metadata: Mapping[Any, Any] | None = None,
                 label: str | None = None):
        label = label or f'Slit {motor}'
        super().__init__(parent, name, cli, handle, motor, metadata, label)

        vals = validators.Numbers(min_value, max_value)
        self.add_parameter('position',
                           label=f'{label} position',
                           get_cmd=self.get_position,
                           set_cmd=self.set_position,
                           set_parser=int,
                           vals=vals,
                           unit=self.unit)
        self.add_parameter('width',
                           label=f'{label} width',
                           get_cmd=self.get_position_relative,
                           set_cmd=self.set_position_relative,
                           set_parser=int,
                           unit=self.unit)

    @property
    def unit(self) -> str:
        return 'pm'

    def get_position(self) -> int:
        return super().get_position() * self.step

    get_position.__doc__ = PrecisionMotorChannel.get_position.__doc__


class GratingChannel(PrecisionMotorChannel):
    """Handles the grating rotation motors of the device."""

    def __init__(self, parent: InstrumentBase, name: str, cli, handle,
                 motor: int, min_value: int = -sys.maxsize - 1,
                 max_value: int = sys.maxsize,
                 metadata: Mapping[Any, Any] | None = None,
                 label: str | None = None):
        label = label or f'Grating {motor}'
        # Cannot use super() since parent also defines the position parameter
        super().__init__(parent, name, cli, handle, motor, metadata, label)

        vals = validators.Numbers(min_value, max_value)
        self.add_parameter('position',
                           label=f'{label} position',
                           get_cmd=self.get_position,
                           set_cmd=self.set_position,
                           set_parser=int,
                           vals=vals,
                           unit=self.unit)
        self.add_parameter('position_deviation',
                           label=f'{label} position deviation from zero order',
                           get_cmd=self.get_position_relative,
                           set_cmd=self.set_position_relative,
                           set_parser=int,
                           unit=self.unit)
        self.add_parameter('shift',
                           label='Zero order shift',
                           get_cmd=False,
                           set_cmd=self.set_shift,
                           set_parser=int,
                           unit=self.unit)

    @property
    def unit(self) -> str:
        try:
            if self.step == 1:
                return 'motor steps'
            else:
                return 'pm'
        except RuntimeError:
            # Not initialized yet
            return ''

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
                 grating_addrs: Sequence[int],
                 slit_addrs: Sequence[int],
                 dc_addrs: Sequence[int],
                 grating_kwargs: Sequence[Mapping[str, Any]] | None = None,
                 slit_kwargs: Sequence[Mapping[str, Any]] | None = None,
                 dc_kwargs: Sequence[Mapping[str, Any]] | None = None,
                 metadata: Mapping[Any, Any] | None = None,
                 label: str | None = None):

        self.cli = FHRClient(dll_dir=dll_dir)
        self.handle: int = self.cli.CreateSpe()

        super().__init__(name, metadata, label)

        dcs = ChannelList(self, 'dcs', DCChannel)
        slits = ChannelList(self, 'slits', SlitChannel)
        gratings = ChannelList(self, 'gratings', GratingChannel)

        dc_kwargs = dc_kwargs or [{}] * len(dc_addrs)
        slit_kwargs = slit_kwargs or [{}] * len(slit_addrs)
        grating_kwargs = grating_kwargs or [{}] * len(grating_addrs)

        for i, (addr, kw) in enumerate(zip(dc_addrs, dc_kwargs), start=1):
            dcs.append(DCChannel(self, f'DC_{i}', self.cli, self.handle, i,
                                 **kw))
            dcs[-1].set_id(addr)
        for i, (addr, kw) in enumerate(zip(slit_addrs, slit_kwargs), start=1):
            slits.append(SlitChannel(self, f'slit_{i}', self.cli, self.handle,
                                     i, **kw))
            slits[-1].set_id(addr)
        for i, (addr, kw) in enumerate(zip(grating_addrs, grating_kwargs),
                                       start=1):
            gratings.append(GratingChannel(self, f'grating_{i}', self.cli,
                                           self.handle, i, **kw))
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
