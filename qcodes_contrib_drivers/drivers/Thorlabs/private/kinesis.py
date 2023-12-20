# -*- coding: utf-8 -*-
"""QCoDeS base drivers for Thorlabs Kinesis instruments

Authors:
    Julien Barrier, <julien@julienbarrier.eu>
"""
import os
import sys
import ctypes
from typing import Any, Optional

from qcodes.instrument import Instrument
from . import GeneralErrors, MotorErrors, ConnexionErrors

class _Thorlabs_Kinesis(Instrument):
    """A base class for Thorlabs kinesis instruments

    Args:
        name: Instrument name.
        serial_number: Serial number of the device.
        dll_path: Path to the kinesis dll for the instrument to use.
        dll_dir: Directory in which the kinesis dll are stored.
        simulation: Enables the simulation manager. Defaults to False.
    """
    def __init__(self,
                 name: str,
                 serial_number: str,
                 dll_path: str,
                 dll_dir: Optional[str] = None,
                 simulation: bool = False,
                 **kwargs):
        super().__init__(name, **kwargs)
        self.serial_number = serial_number
        self._serial_number = ctypes.c_char_p(self.serial_number.encode('ascii'))
        self._dll_path = dll_path
        self._dll_dir: Optional[str] = dll_dir if dll_dir else r'C:\Program Files\Thorlabs\Kinesis'
        if sys.platform != 'win32':
            self._dll: Any = None
            raise OSError('Thorlabs Kinesis only works on Windows')
        else:
            os.add_dll_directory(self._dll_dir)
            self._dll = ctypes.cdll.LoadLibrary(self._dll_path)

        self._simulation = simulation
        if self._simulation:
            self.enable_simulation()

        self._device_info = dict(zip(
            ['type_ID', 'description', 'PID', 'is_known_type', 'motor_type',
             'is_piezo', 'is_laser', 'is_custom', 'is_rack', 'max_channels'],
            self._get_device_info()))
        self._type_ID = self._device_info['type_ID']
        self._description = self._device_info['description']
        self._PID = self._device_info['PID']
        self._is_known_type = self._device_info['is_known_type']
        self._motor_type = self._device_info['motor_type']
        self._is_piezo = self._device_info['is_piezo']
        self._is_laser = self._device_info['is_laser']
        self._is_custom = self._device_info['is_custom']
        self._is_rack = self._device_info['is_rack']
        self._max_channels = self._device_info['max_channels']

    def _get_device_info(self) -> list:
        """Get the device information from the USB port

        Returns:
            list: [type id, description, PID, is known type, motor type,
            is piezo, is laser, is custom type, is rack, max channels]
        """
        type_id = ctypes.c_ulong()
        description = ctypes.c_char()
        pid = ctypes.c_ulong()
        is_known_type = ctypes.c_bool()
        motor_type = ctypes.c_int()
        is_piezo_device = ctypes.c_bool()
        is_laser = ctypes.c_bool()
        is_custom_type = ctypes.c_bool()
        is_rack = ctypes.c_bool()
        max_channels = ctypes.c_bool()

        ret = self._dll.TLI_GetDeviceInfo(
            ctypes.byref(self._serial_number),
            ctypes.byref(type_id),
            ctypes.byref(description),
            ctypes.byref(pid),
            ctypes.byref(is_known_type),
            ctypes.byref(motor_type),
            ctypes.byref(is_piezo_device),
            ctypes.byref(is_laser),
            ctypes.byref(is_custom_type),
            ctypes.byref(is_rack),
            ctypes.byref(max_channels)
        )
        self._check_error(ret)
        return [type_id.value, description.value, pid.value,
                is_known_type.value, motor_type.value, is_piezo_device.value,
                is_laser.value, is_custom_type.value, is_rack.value,
                max_channels.value]

    def _check_error(self, status: int) -> None:
        if status != 0:
            if status in ConnexionErrors:
                raise ConnectionError(f'{ConnexionErrors[status]} ({status})')
            elif status in GeneralErrors:
                raise OSError(f'{GeneralErrors[status]} ({status})')
            elif status in MotorErrors:
                raise RuntimeError(f'{MotorErrors[status]} ({status})')
            else:
                raise ValueError(f'Unknown error code ({status})')
        else:
            pass
        return None

    def enable_simulation(self) -> None:
        """Initialise a connection to the simulation manager, which must already be running"""
        self._dll.TLI_InitializeSimulations()

    def disable_simulation(self) -> None:
        """Uninitialize a connection to the simulation manager, which must be running"""
        self._dll.TLI_UninitializeSimulations()
