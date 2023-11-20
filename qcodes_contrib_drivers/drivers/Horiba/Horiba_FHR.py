from __future__ import annotations

import abc
import configparser
import ctypes
import os
import pathlib
import sys
from typing import Mapping, Any, Dict

from qcodes import validators
from qcodes.instrument import (Instrument, InstrumentBase, InstrumentChannel,
                               ChannelList)
from typing_extensions import Literal

from qcodes_contrib_drivers.drivers.Horiba.private.fhr_client import FHRClient


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
        self.config: dict[str, str]

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
        code, _ = self.cli.SpeCommand(self.handle, 'Port', 'Close')
        self.error_check(code)

    def is_open(self) -> bool:
        """Check if the port is open."""
        code, value = self.cli.SpeCommand(self.handle, 'Port', 'IsOpen',
                                          ctypes.c_int())
        self.error_check(code)
        return bool(value)

    def set_baud_rate(self, baud_rate: int = 115200):
        """Set port baud rate for opened pot. Should be the default."""
        code, _ = self.cli.SpeCommand(self.handle, 'Port', 'SetBaudRate',
                                      ctypes.c_int(baud_rate))
        self.error_check(code)

    def set_timeout(self, timeout: int = 90000):
        """Set timeout in milliseconds."""
        code, _ = self.cli.SpeCommand(self.handle, 'Port', 'SetTimeout',
                                      ctypes.c_int(timeout))
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
    def type(cls) -> str:
        return cls.__name__.removesuffix('Channel')

    def set_id(self, i: int):
        """Set motor ID.

        This is the `Addr` address in LabSpec6."""
        code, _ = self.cli.SpeCommand(self.handle,
                                      f'{self.type()}{self.motor}', 'SetID',
                                      ctypes.c_int(i))
        self.error_check(code)

    def get_id(self) -> int:
        """Get motor ID."""
        code, value = self.cli.SpeCommand(self.handle,
                                          f'{self.type()}{self.motor}',
                                          'GetID', ctypes.c_int())
        self.error_check(code)
        return value

    def stop(self, raise_exception: bool = False):
        """Stop motor.

        Parameters
        ----------
        raise_exception : bool, default: False
            Raise an 'errAbort' exception upon successful stop.
        """
        code, _ = self.cli.SpeCommand(self.handle,
                                      f'{self.type()}{self.motor}', 'Stop')
        try:
            self.error_check(code)
        except SpeError as se:
            if raise_exception or str(se) != 'errAbort':
                raise

    def _set_position(self, pos: int):
        """Set motor position. It return final motor position after
        movement.

        For grating motor the position unit depends on 'Step' value in
        SpeSetup structure. If 'Step' = 1 the motor position is raw
        motor steps. Otherwise it is the position in picometers.

        For slit motors the position in motor steps is the 'Position'
        value multiplied by 'Step' value from SpeSetup.

        For DC motors, the position is binary.
        """
        code, _ = self.cli.SpeCommand(self.handle,
                                      f'{self.type()}{self.motor}',
                                      'SetPosition', ctypes.c_int(pos))
        self.error_check(code)


class PrecisionMotorChannel(MotorChannel, metaclass=abc.ABCMeta):
    """ABC for the precision motors of the device."""

    def __init__(self, parent: InstrumentBase, name: str, cli, handle,
                 motor: int, min_value: int = 0, max_value: int = sys.maxsize,
                 offset: int = 0, metadata: Mapping[Any, Any] | None = None,
                 label: str | None = None):
        super().__init__(parent, name, cli, handle, motor, metadata, label)

        self._step: int = 1
        self._offset: int = offset

        self.add_parameter('position',
                           label=f'{label} position',
                           get_cmd=self._get_position,
                           set_cmd=self._set_position,
                           set_parser=int,
                           vals=validators.Numbers(min_value, max_value),
                           unit=self.unit)

    @property
    @abc.abstractmethod
    def unit(self) -> str:
        pass

    def init(self):
        """Initialize motor with offset position (optical zero order
        position in motor steps)."""
        code, _ = self.cli.SpeCommand(self.handle,
                                      f'{self.type()}{self.motor}', 'Init',
                                      ctypes.c_int(self._offset))
        self.error_check(code)

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
            self.handle, f'{self.type()}{self.motor}',
            fields=(min_speed, max_speed, ramp, backlash, step, reverse)
        )
        self.error_check(code)
        self._step = step
        self.position.unit = self.unit

    def _get_position(self) -> int:
        """Get current position. The result depends on 'Step' value
        similar to "SetPosition" parameter value."""
        code, value = self.cli.SpeCommand(self.handle,
                                          f'{self.type()}{self.motor}',
                                          'GetPosition', ctypes.c_int())
        self.error_check(code)
        return value


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
                           set_parser=int,
                           set_cmd=self._set_position,
                           val_mapping=val_mapping)


class SlitChannel(PrecisionMotorChannel):
    """Handles the linear slit motors of the device."""

    def __init__(self, parent: InstrumentBase, name: str, cli, handle,
                 motor: int, min_value: int = 0, max_value: int = sys.maxsize,
                 offset: int = 0, metadata: Mapping[Any, Any] | None = None,
                 label: str | None = None):
        label = label or f'Slit {motor}'
        super().__init__(parent, name, cli, handle, motor, min_value + offset,
                         max_value + offset, offset, metadata, label)

        self._offset = offset
        self.add_parameter('width',
                           label=f'{label} width',
                           get_cmd=self._get_width,
                           set_cmd=self._set_width,
                           set_parser=int,
                           unit=self.unit,
                           vals=validators.Numbers(min_value, max_value),
                           docstring="Actual slit opening width")

    @property
    def unit(self) -> str:
        # From the manual:
        #   For slit motors the position in motor steps is the
        #   'Position' value multiplied by 'Step' value from SpeSetup.
        # What I take from this is that it always returns microns.
        return 'μm'

    def _get_width(self) -> int:
        return self.position() - self._offset

    def _set_width(self, width: int):
        return self.position(width + self._offset)


class GratingChannel(PrecisionMotorChannel):
    """Handles the grating rotation motors of the device."""

    def __init__(self, parent: InstrumentBase, name: str, cli, handle,
                 motor: int, min_value: int = 0, max_value: int = sys.maxsize,
                 offset: int = 0, metadata: Mapping[Any, Any] | None = None,
                 label: str | None = None):
        label = label or f'Grating {motor}'
        # Cannot use super() since parent also defines the position parameter
        super().__init__(parent, name, cli, handle, motor, min_value,
                         max_value, offset, metadata, label)

        self.add_parameter('shift',
                           label='Zero order shift',
                           get_cmd=False,
                           set_cmd=self._set_shift,
                           set_parser=int,
                           unit=self.unit)

    @property
    def unit(self) -> str:
        return 'motor steps' if self._step == 1 else 'pm'

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
            self.handle, f'{self.type()}{self.motor}',
            fields=(phase, min_speed, max_speed, ramp)
        )
        self.error_check(code)

    def _set_shift(self, shift: int):
        """Set zero order shift."""
        code, _ = self.cli.SpeCommand(self.handle,
                                      f'{self.type()}{self.motor}',
                                      'SetShift', ctypes.c_int(shift))
        self.error_check(code)


class HoribaFHR(Instrument):
    """Horiba FHR driver for a 32-bit dll.

    This driver uses ``msl.loadlib`` to communicate with the 32-bit dll
    through a 32-bit server from a 64-bit client.

    Args:
        dll_dir (path_like):
            Directory to search for SpeControl.dll
        config_file (path_like):
            Configuration file (see below)
        dc_val_mappings (dict):
            val_mappings for the DC motors (mirrors). Should be a dict
            of mappings with integer keys corresponding to the mirror
            id. For example, for an instrument with only one mirror
            "Mirror2", ``{2: {'front': 0, 'side': 1}}``.

    Notes:
        The configuration file should be an ``ini``-like file with
        sections

         - ``[Firmware]``
         - ``[Port]``
         - ``[Spectrometer]``
         - ``[Grating1]`` etc.
         - ``[Slit1]`` etc.
         - ``[Mirror1]`` etc.

    Examples:
        See ``docs/examples`` for an example notebook.

    """

    def __init__(
            self, name: str,
            dll_dir: str | os.PathLike | pathlib.Path,
            config_file: str | os.PathLike | pathlib.Path,
            dc_val_mappings: Dict[int, Dict[str, Literal[0, 1]] | None] = {},
            metadata: Mapping[Any, Any] | None = None,
            label: str | None = None
    ):

        self.cli = FHRClient(dll_dir)
        self.handle: int = self.cli.CreateSpe()
        self.config = configparser.ConfigParser(comment_prefixes=('==',))
        self.config.read(config_file)

        additional_metadata = {
            'Focal length': self.config['Spectrometer'].getint('Focal'),
            'Coefficient of angle': self.config['Spectrometer'].getfloat(
                'CoefficientOfAngle'
            ),
            'Number of gratings': self.config['Spectrometer'].getint(
                'GratingNumber'
            ),
            'Number of slits': self.config['Spectrometer'].getint(
                'SlitNumber'
            )
        }

        super().__init__(name, additional_metadata | dict(metadata or {}), label)

        gratings = ChannelList(self, 'gratings', GratingChannel)
        slits = ChannelList(self, 'slits', SlitChannel)
        mirrors = ChannelList(self, 'mirrors', DCChannel)

        for name, section in self.config.items():
            if name == 'Port':
                # This relies on Port being the first section because otherwise
                # communication with the device will fail.
                port = PortChannel(self, 'port', self.cli, self.handle,
                                   section.getint('ComPort'))
                port.open()
                port.set_baud_rate(section.getint('Baudrate'))
                port.set_timeout(section.getint('Timeout'))
                port.config = dict(section)
            elif name.startswith('Grating'):
                # Grating1, Grating2, etc
                grating = GratingChannel(
                    self,
                    # Cannot use section['Name'] b/c of invalid identifier
                    # chars.
                    f"grating_{section['Value']}",
                    self.cli,
                    self.handle,
                    motor=int(name[-1]),
                    # TODO: this assumes MotorStepUnit to be != 1
                    min_value=section.getint('MinNm')*1000,  # pm
                    max_value=section.getint('MaxNm')*1000,
                    offset=section.getint('Offset'),  # motor steps
                    metadata={'Coefficient of linearity': section.getfloat(
                        'CoefficientOfLinearity'
                    )}
                )
                grating.set_id(section.getint('AddrAxe'))
                grating.set_setup(
                    # For whatever reason these parameters are in the
                    # Spectrometer section...
                    min_speed=self.config['Spectrometer'].getint('SpeedMin'),
                    max_speed=self.config['Spectrometer'].getint('SpeedMax'),
                    ramp=self.config['Spectrometer'].getint('Acceleration'),
                    backlash=self.config['Spectrometer'].getint('Backlash'),
                    step=self.config['Spectrometer'].getint('MotorStepUnit'),
                    reverse=self.config['Spectrometer'].getboolean('Reverse')
                )
                # Hardcoded since it is not present in my ini file.
                # Taken from 'SDK FHR Express -additional informations-.pdf'
                grating.set_ini_params(phase=1, min_speed=2000,
                                       max_speed=100000, ramp=400)
                grating.set_ini_params(phase=2, min_speed=2000,
                                       max_speed=100000, ramp=400)
                grating.set_ini_params(phase=3, min_speed=2000,
                                       max_speed=10000, ramp=400)
                grating.shift(section.getint('Shift'))
                grating.config = dict(section)
                gratings.append(grating)
            elif name.startswith('Slit'):
                # Slit1, Slit2, etc
                slit = SlitChannel(
                    self,
                    section['Name'].lower().replace(' ', '_'),
                    self.cli,
                    self.handle,
                    motor=int(name[-1]),
                    # min_value and max_value are used for the slit width,
                    # not absolute position.
                    min_value=section.getint('Minum'),
                    max_value=section.getint('Maxum'),
                    offset=section.getint('Offset'),
                    metadata={'Coefficient of linearity': section.getfloat(
                        'CoefficientOfLinearity'
                    )}
                )
                slit.set_id(section.getint('AddrAxe'))
                slit.set_setup(min_speed=section.getint('SpeedMin'),
                               max_speed=section.getint('SpeedMax'),
                               ramp=section.getint('Acceleration'),
                               backlash=section.getint('Backlash'),
                               step=section.getint('MotorStepUnit'),
                               reverse=section.getboolean('Reverse'))
                slit.config = dict(section)
                slits.append(slit)
            elif name.startswith('Mirror'):
                # Mirror1, Mirror2, etc
                mirror = DCChannel(
                    self,
                    section['Name'].lower().replace(' ', '_'),
                    self.cli,
                    self.handle,
                    motor=int(name[-1]),
                    val_mapping=dc_val_mappings.get(int(name[-1])),
                    metadata={'Delay (ms)': section.getint('Delayms'),
                              'Duty cycle (%)': section.getint('DutyCycle%')}
                )
                mirror.set_id(section.getint('AddrAxe'))
                mirror.config = dict(section)
                mirrors.append(mirror)

        self.add_submodule('port', port)
        self.add_submodule('mirrors', mirrors.to_channel_tuple())
        self.add_submodule('slits', slits.to_channel_tuple())
        self.add_submodule('gratings', gratings.to_channel_tuple())

        self.connect_message()

    def get_idn(self) -> Dict[str, str | None]:
        return {'serial': self.config['Firmware']['SerialNumber'],
                'firmware': self.config['Firmware']['VersionNumber'],
                'model': f"FHR{self.config['Spectrometer']['Focal']}",
                'vendor': 'Horiba'}

    def disconnect(self):
        if self.port.is_open():
            self.port.close()

    def close(self) -> None:
        self.disconnect()
        self.cli.DeleteSpe(self.handle)
        super().close()
