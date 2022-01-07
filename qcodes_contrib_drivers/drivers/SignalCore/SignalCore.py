import ctypes
import os
import sys
from typing import Dict, Optional
from qcodes import Instrument
from qcodes.utils.validators import Enum


MAXDEVICES = 50
MAXDESCRIPTORSIZE = 9
COMMINTERFACE = ctypes.c_uint8(1)

class ManDate(ctypes.Structure):
    _fields_ = [('year', ctypes.c_uint8),
                ('month', ctypes.c_uint8),
                ('day', ctypes.c_uint8),
                ('hour', ctypes.c_uint8)]


class DeviceInfoT(ctypes.Structure):
    _fields_ = [('product_serial_number', ctypes.c_uint32),
                ('hardware_revision', ctypes.c_float),
                ('firmware_revision', ctypes.c_float),
                ('device_interfaces', ctypes.c_uint8),
                ('man_date', ManDate)]
device_info_t = DeviceInfoT()


class ListModeT(ctypes.Structure):
    _fields_ = [('sweep_mode', ctypes.c_uint8),
                ('sweep_dir', ctypes.c_uint8),
                ('tri_waveform', ctypes.c_uint8),
                ('hw_trigger', ctypes.c_uint8),
                ('step_on_hw_trig', ctypes.c_uint8),
                ('return_to_start', ctypes.c_uint8),
                ('trig_out_enable', ctypes.c_uint8),
                ('trig_out_on_cycle', ctypes.c_uint8)]


class PLLStatusT(ctypes.Structure):
    _fields_ = [('sum_pll_ld', ctypes.c_uint8),
                ('crs_pll_ld', ctypes.c_uint8),
                ('fine_pll_ld', ctypes.c_uint8),
                ('crs_ref_pll_ld', ctypes.c_uint8),
                ('crs_aux_pll_ld', ctypes.c_uint8),
                ('ref_100_pll_ld', ctypes.c_uint8),
                ('ref_10_pll_ld', ctypes.c_uint8)]


class OperateStatusT(ctypes.Structure):
    _fields_ = [('rf1_lock_mode', ctypes.c_uint8),
                ('rf1_loop_gain', ctypes.c_uint8),
                ('device_access', ctypes.c_uint8),
                ('device_standby', ctypes.c_uint8),
                ('auto_pwr_disable', ctypes.c_uint8),
                ('output_enable', ctypes.c_uint8),
                ('ext_ref_lock_enable', ctypes.c_uint8),
                ('ext_ref_detect', ctypes.c_uint8),
                ('ref_out_select', ctypes.c_uint8),
                ('list_mode_running', ctypes.c_uint8),
                ('rf_mode', ctypes.c_uint8),
                ('over_temp', ctypes.c_uint8),
                ('harmonic_ss', ctypes.c_uint8),
                ('pci_clk_enable', ctypes.c_uint8)]


class DeviceStatusT(ctypes.Structure):
    _fields_ = [('list_mode_t', ListModeT),
                ('operate_status_t', OperateStatusT),
                ('pll_status_t', PLLStatusT)]
device_status_t = DeviceStatusT()


class HWTriggerT(ctypes.Structure):
    _fields_ = [('edge', ctypes.c_uint8),
                ('pxi_enable', ctypes.c_uint8),
                ('pxi_line', ctypes.c_uint8)]
hw_trigger_t = HWTriggerT()


class DeviceRFParamsT(ctypes.Structure):
    _fields_ = [('frequency', ctypes.c_double),
                ('sweep_start_freq', ctypes.c_double),
                ('sweep_stop_freq', ctypes.c_double),
                ('sweep_step_freq', ctypes.c_double),
                ('sweep_dwell_time', ctypes.c_uint32),
                ('sweep_cycles', ctypes.c_uint32),
                ('buffer_points', ctypes.c_uint32),
                ('rf_phase_offset', ctypes.c_float),
                ('power_level', ctypes.c_float),
                ('atten_value', ctypes.c_float),
                ('level_dac_value', ctypes.c_uint16)]
device_rf_params_t = DeviceRFParamsT()


error_dict = {'0':'SCI_SUCCESS',
              '0':'SCI_ERROR_NONE',
              '-1':'SCI_ERROR_INVALID_DEVICE_HANDLE',
              '-2':'SCI_ERROR_NO_DEVICE',
              '-3':'SCI_ERROR_INVALID_DEVICE',
              '-4':'SCI_ERROR_MEM_UNALLOCATE',
              '-5':'SCI_ERROR_MEM_EXCEEDED',
              '-6':'SCI_ERROR_INVALID_REG',
              '-7':'SCI_ERROR_INVALID_ARGUMENT',
              '-8':'SCI_ERROR_COMM_FAIL',
              '-9':'SCI_ERROR_OUT_OF_RANGE',
              '-10':'SCI_ERROR_PLL_LOCK',
              '-11':'SCI_ERROR_TIMED_OUT',
              '-12':'SCI_ERROR_COMM_INIT',
              '-13':'SCI_ERROR_TIMED_OUT_READ',
              '-14':'SCI_ERROR_INVALID_INTERFACE'}



class SC5521A(Instrument):
    __doc__ = 'QCoDeS python driver for the Signal Core SC5521A.'

    def __init__(self, name: str,
                       dll_path: str='SignalCore\\SC5520A\\api\\c\\scipci\\x64\\sc5520a_uhfs.dll',
                       **kwargs):
        """
        QCoDeS driver for the Signal Core SC5521A.
        This driver has been tested when only one SignalCore is connected to the
        computer.

        Args:
        name (str): Name of the instrument.
        dll_path (str): Path towards the instrument DLL.
        """

        (super().__init__)(name, **kwargs)

        self._devices_number = ctypes.c_uint()
        self._pxi10Enable = 0
        self._lock_external = 0
        self._clock_frequency = 10
        buffers = [ctypes.create_string_buffer(MAXDESCRIPTORSIZE + 1) for bid in range(MAXDEVICES)]
        self.buffer_pointer_array = (ctypes.c_char_p * MAXDEVICES)()
        for device in range(MAXDEVICES):
            self.buffer_pointer_array[device] = ctypes.cast(buffers[device], ctypes.c_char_p)

        self._buffer_pointer_array_p = ctypes.cast(self.buffer_pointer_array, ctypes.POINTER(ctypes.c_char_p))

        # Adapt the path to the computer language
        if sys.platform == 'win32':
            dll_path = os.path.join(os.environ['PROGRAMFILES'], dll_path)
            self._dll = ctypes.WinDLL(dll_path)
        else:
            raise EnvironmentError(f"{self.__class__.__name__} is supported only on Windows platform")

        found = self._dll.sc5520a_uhfsSearchDevices(COMMINTERFACE, self._buffer_pointer_array_p, ctypes.byref(self._devices_number))
        if found:
            raise RuntimeError('Failed to find any device')
        self._open()

        self.add_parameter(name='temperature',
                           docstring='Return the microwave source internal temperature.',
                           label='Device temperature',
                           unit='celsius',
                           get_cmd=self._get_temperature)

        self.add_parameter(name='status',
                           docstring='.',
                           vals=Enum('on', 'off'),
                           set_cmd=self._set_status,
                           get_cmd=self._get_status)

        self.add_parameter(name='power',
                           docstring='.',
                           label='Power',
                           unit='dbm',
                           set_cmd=self._set_power,
                           get_cmd=self._get_power)

        self.add_parameter(name='frequency',
                           docstring='.',
                           label='Frequency',
                           unit='Hz',
                           set_cmd=self._set_frequency,
                           get_cmd=self._get_frequency)

        self.add_parameter(name='rf_mode',
                           docstring='.',
                           vals=Enum('single_tone', 'sweep'),
                           initial_value='single_tone',
                           set_cmd=self._set_rf_mode,
                           get_cmd=self._get_rf_mode)

        self.add_parameter(name='clock_frequency',
                           docstring='Select the internal clock frequency, 10 or 100MHz.',
                           unit='MHz',
                           vals=Enum(10, 100),
                           initial_value=100,
                           set_cmd=self._set_clock_frequency,
                           get_cmd=self._get_clock_frequency)

        self.add_parameter(name='clock_reference',
                           docstring='Select the clock reference, internal or external.',
                           vals=Enum('internal', 'external'),
                           initial_value='internal',
                           set_cmd=self._set_clock_reference,
                           get_cmd=self._get_clock_reference)
        self.connect_message()

    def _open(self) -> None:
        self._handle = ctypes.wintypes.HANDLE()
        self._dll.sc5520a_uhfsOpenDevice(COMMINTERFACE, self.buffer_pointer_array[0], ctypes.c_uint8(1), ctypes.byref(self._handle))

    def _close(self) -> None:
        self._dll.sc5520a_uhfsCloseDevice(self._handle)

    def _error_handler(self, msg: int) -> None:
        """Display error when setting the device fail.

        Args:
            msg (int): error key, see error_dict dict.

        Raises:
            BaseException
        """

        if msg!=0:
            raise BaseException("Couldn't set the devise due to {}.".format(error_dict[str(msg)]))
        else:
            pass

    def _get_temperature(self) -> float:
        temperature = ctypes.c_float()
        self._dll.sc5520a_uhfsFetchTemperature(self._handle, ctypes.byref(temperature))
        return temperature.value

    def _set_status(self, status: str) -> None:
        if status.lower() == 'on':
            status_ = 1
        else:
            status_ = 0
        msg = self._dll.sc5520a_uhfsSetOutputEnable(self._handle, ctypes.c_int(status_))
        self._error_handler(msg)

    def _get_status(self) -> str:
        self._dll.sc5520a_uhfsFetchDeviceStatus(self._handle, ctypes.byref(device_status_t))
        if device_status_t.operate_status_t.output_enable:
            return 'on'
        else:
            return 'off'

    def _set_power(self, power: float) -> None:
        msg = self._dll.sc5520a_uhfsSetPowerLevel(self._handle, ctypes.c_float(power))
        self._error_handler(msg)

    def _get_power(self) -> float:
        self._dll.sc5520a_uhfsFetchRfParameters(self._handle, ctypes.byref(device_rf_params_t))
        return device_rf_params_t.power_level

    def _set_frequency(self, frequency: float) -> None:
        msg = self._dll.sc5520a_uhfsSetFrequency(self._handle, ctypes.c_double(frequency))
        self._error_handler(msg)

    def _get_frequency(self) -> float:
        device_rf_params_t = DeviceRFParamsT()
        self._dll.sc5520a_uhfsFetchRfParameters(self._handle, ctypes.byref(device_rf_params_t))
        return float(device_rf_params_t.frequency)

    def _set_clock_frequency(self, clock_frequency: float) -> None:
        if clock_frequency == 10:
            self._select_high = 0
        else:
            self._select_high = 1
        msg = self._dll.sc5520a_uhfsSetReferenceMode(self._handle, ctypes.c_int(self._pxi10Enable), ctypes.c_int(self._select_high), ctypes.c_int(self._lock_external))
        self._error_handler(msg)

    def _get_clock_frequency(self) -> float:
        self._dll.sc5520a_uhfsFetchDeviceStatus(self._handle, ctypes.byref(device_status_t))
        ref_out_select = device_status_t.operate_status_t.ref_out_select
        if ref_out_select == 1:
            return 100
        return 10

    def _set_clock_reference(self, clock_reference: str) -> None:
        if clock_reference.lower() == 'internal':
            self._lock_external = 0
        else:
            self._lock_external = 1
        msg = self._dll.sc5520a_uhfsSetReferenceMode(self._handle, ctypes.c_int(self._pxi10Enable), ctypes.c_int(self._select_high), ctypes.c_int(self._lock_external))
        self._error_handler(msg)

    def _get_clock_reference(self) -> str:
        self._dll.sc5520a_uhfsFetchDeviceStatus(self._handle, ctypes.byref(device_status_t))
        ext_ref_detect = device_status_t.operate_status_t.ext_ref_detect
        if ext_ref_detect == 1:
            return 'external'
        return 'internal'

    def _set_rf_mode(self, rf_mode: str) -> None:
        if rf_mode.lower() == 'single_tone':
            self.rf_mode_ = 0
        else:
            self.rf_mode_ = 1
        msg = self._dll.sc5520a_uhfsSetRfMode(self._handle, ctypes.c_int(self.rf_mode_))
        self._error_handler(msg)

    def _get_rf_mode(self) -> str:
        self._dll.sc5520a_uhfsFetchDeviceStatus(self._handle, ctypes.byref(device_status_t))
        rf_mode = device_status_t.operate_status_t.rf_mode
        if rf_mode == 0:
            return 'single_tone'
        return 'sweep'

    def get_idn(self) -> Dict[str, Optional[str]]:
        self._dll.sc5520a_uhfsFetchDeviceInfo(self._handle, ctypes.byref(device_info_t))

        return {'vendor':'SignalCore',
                'model':'SC5521A',
                'serial':device_info_t.product_serial_number,
                'firmware':device_info_t.firmware_revision,
                'hardware':device_info_t.hardware_revision,
                'manufacture_date':'20{}-{}-{} at {}h'.format(device_info_t.man_date.year, device_info_t.man_date.month, device_info_t.man_date.day, device_info_t.man_date.hour)}
