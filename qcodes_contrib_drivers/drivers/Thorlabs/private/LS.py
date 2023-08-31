# -*- coding: utf-8 -*-
"""QCoDes- Base driver for Thorlab instruments using the LS commands

Authors:
    iago-rst https://github.com/iago-rst, 2023
    Julien Barrier <julien@julienbarrier.eu>, 2023
"""
import ctypes
import logging
from time import sleep
from typing import Optional

from qcodes.parameters import Parameter
from qcodes import validators as vals

from .kinesis import _Thorlabs_Kinesis

log = logging.getLogger(__name__)

class _Thorlabs_LS(_Thorlabs_Kinesis):
    """Instrument driver for Thorlabs instruments using the CC commands

    Args:
        name: Instrument name.
        serial_number: Serial number of the device.
        dll_path: Path to the kinesis dll for the instrument to use.
        dll_dir: Directory in which the kinesis dll are stored.
        simulation: Enables the simulation manager. Defaults to False.
        polling: Polling rate in ms. Defaults to 200.
        home: Sets the device to home state. Defaults to False.
    """
    _CONDITIONS = ['homed', 'moved', 'stopped', 'limit_updated']
    def __init__(self,
                 name: str,
                 serial_number: str,
                 dll_path: str,
                 dll_dir: Optional[str],
                 simulation: bool = False,
                 polling: int = 200,
                 home: bool = False,
                 **kwargs):
        self._dll_path = dll_path
        super().__init__(name, serial_number,
                         self._dll_path, dll_dir, simulation,
                         **kwargs)

        if self._dll.TLI_BuildDeviceList() == 0:
            self._open_laser()
            self._start_polling(polling)

        self._info = self._get_hardware_info()
        self.model = self._info[0].decode('utf-8')
        self.version = self._info[4]

        self._load_settings()
        self._set_limits_approach(1)

        sleep(3)

        self._clear_message_queue()

        if home:
            if not self._can_home():
                self.homed = False
                raise RuntimeError('Device `{}` is not homeable')
            else:
                self.go_home()
        else:
            self.homed = False


        self.output_enabled = Parameter(
            'output_enabled',
            label='Output enabled',
            get_cmd=self._get_output_enabled,
            set_cmd=self._set_output_enabled,
            vals=vals.Bool(),
            docstring='turn laser output off/on. Note that laser key switch must be turned on to turn output on.',
            instrument=self
        )

        self.power = Parameter(
            'power',
            label='Power output',
            unit='W',
            get_cmd=self._get_power,
            set_cmd=self._set_power,
            vals=vals.Numbers(0, .007),
            instrument=self
        )

        self.connect_message()

    def identify(self) -> None:
        """Sends a command to the device to make it identify itself"""
        self._dll.LS_Identify(self._serial_number)

    def get_idn(self) -> dict:
        """Get device identifier"""
        idparts = ['Thorlabs', self.model, self.version, self.serial_number]
        return dict(zip(('vendor', 'model', 'serial', 'firmware'), idparts))

    def _get_status_bits(self) -> int:
        status = self._dll.LS_GetStatusBits(self._serial_number)
        if status == 0x40000000:
            raise ValueError()
        else:
            return int(status)

    def _get_output_enabled(self) -> bool:
        return bool(self._get_status_bits() & 1)

    def _set_output_enabled(self, value: bool) -> None:
        if value:
            self.enable_output()
        else:
            self.disable_output()

    def enable_output(self) -> None:
        ret = self._dll.LS_EnableOutput(self._serial_number)
        self._check_error(ret)

    def disable_output(self) -> None:
        ret = self._dll.LS_DisableOutput(self._serial_number)
        self._check_error(ret)

    def _get_power(self) -> float:
        max_num = 32767
        max_power = .007
        num = self._dll.LS_GetPowerReading(self._serial_number)
        return num/max_num * max_power

    def _set_power(self, power: float) -> None:
        max_num = 32767
        max_power = .007
        percent = power / max_power
        ret = self._dll.LS_SetPower(self._serial_number, int(percent*max_num))
        self._check_error(ret)

    def close(self):
        if self._simulation:
            self.disable_simulation()
        if hasattr(self, '_serial_number'):
            self._stop_polling()
            self._dll.LS_Close(self._serial_number)

    def _get_hardware_info(self) -> list:
        """Gets the hardware information from the device

        Returns:
            list: [model number, hardware type number, number of channels,
                notes describing the device, firmware version, hardware version,
                hardware modification state]
        """
        model = ctypes.create_string_buffer(8)
        model_size = ctypes.c_ulong(8)
        type_num = ctypes.c_ushort()
        channel_num = ctypes.c_ushort()
        notes = ctypes.create_string_buffer(48)
        notes_size = ctypes.c_ulong(48)
        firmware_version = ctypes.c_ulong()
        hardware_version = ctypes.c_ushort()
        modification_state = ctypes.c_ushort()

        ret = self._dll.LS_GetHardwareInfo(
            self._serial_number,
            ctypes.byref(model), model_size,
            ctypes.byref(type_num), ctypes.byref(channel_num),
            ctypes.byref(notes), notes_size, ctypes.byref(firmware_version),
            ctypes.byref(hardware_version), ctypes.byref(modification_state)
        )

        self._check_error(ret)
        return [model.value, type_num.value, channel_num.value,
                notes.value, firmware_version.value, hardware_version.value,
                modification_state.value]

    def _load_settings(self):
        """Update device with stored settings"""
        self._dll.LS_LoadSettings(self._serial_number)
        return None

    def _open_laser(self) -> None:
        ret = self._dll.LS_Open(self._serial_number)
        self._check_error(ret)

    def _close_laser(self) -> None:
        ret = self._dll.LS_Close(self._serial_number)
        self._check_error(ret)

    def _start_polling(self, polling: int):
        pol = ctypes.c_int(polling)
        ret = self._dll.LS_StartPolling(self._serial_number, ctypes.byref(pol))
        self._check_error(ret)
        return None

    def _stop_polling(self):
        self._dll.LS_StopPolling(self._serial_number)

    def _clear_message_queue(self) -> None:
        self._dll.LS_ClearMessageQueue(self._serial_number)
        return None
