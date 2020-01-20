from qcodes import Instrument
import ctypes
import numpy as np
import os
import time


class DeviceInformation(ctypes.Structure):
    _fields_ = [
        ("Manufacturer", ctypes.c_char * 5),
        ("ManufacturerId", ctypes.c_char * 3),
        ("ProductDescription", ctypes.c_char * 9),
        ("Major", ctypes.c_uint),
        ("Minor", ctypes.c_uint),
        ("Release", ctypes.c_uint),
    ]


class GetPosition(ctypes.Structure):
    _fields_ = [
        ("Position", ctypes.c_int),
        ("uPosition", ctypes.c_int),
        ("EncPosition", ctypes.c_longlong),
    ]


class Status(ctypes.Structure):
    _fields_ = [
        ("MoveSts", ctypes.c_uint),
        ("MvCmdSts", ctypes.c_uint),
        ("PWRSts", ctypes.c_uint),
        ("EncSts", ctypes.c_uint),
        ("WindSts", ctypes.c_uint),
        ("CurPosition", ctypes.c_int),
        ("uCurPosition", ctypes.c_int),
        ("EncPosition", ctypes.c_longlong),
        ("CurSpeed", ctypes.c_int),
        ("uCurSpeed", ctypes.c_int),
        ("Ipwr", ctypes.c_int),
        ("Upwr", ctypes.c_int),
        ("Iusb", ctypes.c_int),
        ("Uusb", ctypes.c_int),
        ("CurT", ctypes.c_int),
        ("Flags", ctypes.c_uint),
        ("GPIOFlags", ctypes.c_uint),
        ("CmdBufFreeSpace", ctypes.c_uint),
    ]


class libximc:
    # TODO: use error check, implement wait for stop function from dll

    # default dll path
    _dll_path = 'C:\\Program Files\\XILab\\libximc.dll'

    # success and error codes
    _success_codes = {0: 'Ok'}
    _error_codes = {-1: 'Error', -2: 'NotImplemented', -3: 'ValueError', -4: 'NoDevice'}

    def __init__(self, dll_path=None, verbose=False):
        # save attributes
        self.verbose = verbose

        # connect to the dll
        current_path = os.getcwd()
        try:
            os.chdir(os.path.dirname(self._dll_path))
            self.dll = ctypes.windll.LoadLibrary(dll_path or self._dll_path)
        finally:
            os.chdir(current_path)

        # set resource type
        self.dll.enumerate_devices.restype = ctypes.POINTER(DeviceInformation)

    def error_check(self, code, function_name=''):
        if code in self._success_codes.keys():
            if self.verbose:
                print("libximc: [%s]: %s" % (function_name, self._success_codes[code]))
        elif code in self._error_codes.keys():
            print("libximc: [%s]: %s" % (function_name, self._error_codes[code]))
            raise Exception(self._error_codes[code])
        else:
            print("libximc: [%s]: Unknown code: %s" % (function_name, code))
            raise Exception()

    def command_move(self, device_id, position, u_position):
        self.dll.command_move(device_id, position, u_position)

    def enumerate_devices(self, probe_flags):
        enumeration = self.dll.enumerate_devices(probe_flags, b"")
        return enumeration

    def get_device_name(self, device_enumeration, device_index):
        device_name = self.dll.get_device_name(device_enumeration, device_index)
        return device_name

    def get_position(self, device_id, get_position):
        self.dll.get_position(device_id, get_position)

    def get_status(self, device_id, status):
        self.dll.get_status(device_id, status)

    def open_device(self, device_name):
        device_id = self.dll.open_device(device_name)
        return device_id


class Standa_10MWA168(Instrument):

    def __init__(self, name, serial_number, dll_path=None, **kwargs):
        super().__init__(name, **kwargs)

        # link to dll
        self.libximc = libximc(dll_path=dll_path)

        # instrument constants
        self.filter_wheel_1 = [-1, 0, 1, -1, 1, 2, -1, 1, 2, 3, 3, 3, 1, 2, 4, 4, 1, 2, 5, 5, 4, 1, 2, 6, 6, 6, 2, 5, 6, 6, 6]
        self.filter_wheel_2 = [-1, 0, -1, 1, 1, 1, 2, 2, 2, -1, 1, 2, 3, 3, -1, 2, 4, 4, -1, 1, 3, 5, 5, -1, 1, 2, 6, 4, 4, 5, 6]
        self.offset_wheel_1 = 0.
        self.offset_wheel_2 = 62.
        self.revolution = 200.
        self.distance = self.revolution / 8.

        # initialization
        self.serial_number = serial_number
        device_enumeration = self.libximc.enumerate_devices(0)
        enumeration_name = self.libximc.get_device_name(device_enumeration, 0)
        self.device_id = self.libximc.open_device(enumeration_name)

        # Time to wait (in seconds) between setting up wheel 1 and 2
        self.set_transmittance_sleep_time = 10.0

        # add parameters
        self.add_parameter('transmittance',
                           set_cmd=self._set_transmittance,
                           label='Transmittance',
                           val_mapping={
                               1: 0, 0: 1, 9.0e-1: 2, 8.0e-1: 3, 7.2e-1: 4, 4.0e-1: 5, 3.0e-1: 6, 2.7e-1: 7,
                               1.5e-1: 8, 1.0e-1: 9, 8.0e-2: 10, 3.0e-2: 11, 2.7e-2: 12, 1.5e-2: 13, 1.0e-2: 14,
                               3.0e-3: 15, 2.7e-3: 16, 1.5e-3: 17, 1.0e-3: 18, 8.0e-4: 19, 3.0e-4: 20, 2.7e-4: 21,
                               1.5e-4: 22, 1.0e-4: 23, 8.0e-5: 24, 3.0e-5: 25, 1.5e-5: 26, 3.0e-6: 27, 3.0e-7: 28,
                               3.0e-8: 29, 3.0e-9: 30})

        self.add_parameter('position',
                           set_cmd=self._set_position,
                           get_cmd=self._get_position,
                           get_parser=float,
                           label='Position')

        self.add_parameter('status',
                           get_cmd=self._get_status,
                           get_parser=int,
                           label='status')

        self.connect_message()

    # get methods
    def _get_position(self):
        position = GetPosition()
        self.libximc.get_position(self.device_id, ctypes.byref(position))
        return position.Position

    def _get_status(self):
        status = Status()
        self.libximc.get_status(self.device_id, ctypes.byref(status))
        return status.MoveSts

    # set methods
    def _set_position(self, position):
        self.libximc.command_move(self.device_id, int(position), 0)

    def _set_transmittance(self, transmittance_id):
        # get filter to set
        filter_wheel_1 = self.filter_wheel_1[transmittance_id]
        filter_wheel_2 = self.filter_wheel_2[transmittance_id]

        # get current position
        current_position = self.position.get()

        # determine new positions
        position_wheel_2 = self.offset_wheel_2 + self.distance * filter_wheel_2 + \
                           np.ceil(current_position / self.revolution + 2) * self.revolution
        position_wheel_1 = self.offset_wheel_1 + self.distance * filter_wheel_1 + \
                           np.ceil(current_position / self.revolution + 2) * self.revolution

        if position_wheel_1 > position_wheel_2:
            print('new', position_wheel_1, position_wheel_2)
            position_wheel_1 -= self.revolution

        # set position of the second wheel
        self.position.set(np.floor(position_wheel_2))
        time.sleep(self.sleep_time / 10.0)  # default: 1 s
        for i in range(100):
            if self.status.get() == 0:
                break

        # wait another time
        time.sleep(self.sleep_time)  # default: 10 s

        # set position of the first wheel
        self.position.set(np.floor(position_wheel_1))
        time.sleep(self.sleep_time / 10.0)  # default: 1 s
        for i in range(100):
            if self.status.get() == 0:
                break

        time.sleep(self.sleep_time / 100.0)  # default: 0.1 s
