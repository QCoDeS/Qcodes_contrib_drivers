import ctypes
from typing import List, Optional, Tuple, Union
import enum


class ThorlabsHWType(enum.Enum):
    PRM1Z8 = 31
    MFF10x = 48
    K10CR1 = 50


class ThorlabsException(Exception):
    pass


class Thorlabs_APT:
    """
    Wrapper class for the APT.dll Thorlabs APT Server library.
    The class has been tested for a Thorlabs MFF10x mirror flipper, a Thorlabs PRM1Z8 Polarizer
    Wheel and a Thorlabs K10CR1 rotator.

    Args:
        dll_path: Path to the APT.dll file. If not set, a default path is used.
        verbose: Flag for the verbose behaviour. If true, successful events are printed.
        event_dialog: Flag for the event dialog. If true, event dialog pops up for information.

    Attributes:
        verbose: Flag for the verbose behaviour.
        dll: WinDLL object for APT.dll.
    """

    # default dll installation path
    _dll_path = 'C:\\Program Files\\Thorlabs\\APT\\APT Server\\APT.dll'

    # success and error codes
    _success_code = 0

    def __init__(self, dll_path: Optional[str] = None, verbose: bool = False, event_dialog: bool = False):

        # save attributes
        self.verbose = verbose

        # connect to the DLL
        self.dll = ctypes.CDLL(dll_path or self._dll_path)

        # initialize APT server
        self.apt_init()
        self.enable_event_dlg(event_dialog)

    def error_check(self, code: int, function_name: str = "") -> None:
        """Analyzes a functions return code to check, if the function call to APT.dll was
        successful. If an error occurred, this function throws an ThorlabsException.

        Args:
            code: The called function's return code
            function_name: Name of the called function

        Throws:
            ThorlabsException: Thrown, if the return code indicates that an error has occurred.
        """
        if code == self._success_code:
            if self.verbose:
                print("APT: [{}]: {}".format(function_name, "OK - no error"))
        else:
            raise ThorlabsException("APT: [{}]: Unknown code: {}".format(function_name, code))

    def apt_clean_up(self) -> None:
        """Cleans up the resources of APT.dll"""
        code = self.dll.APTCleanUp()
        self.error_check(code, 'APTCleanUp')

    def apt_init(self) -> None:
        """Initialization of APT.dll"""
        code = self.dll.APTInit()
        self.error_check(code, 'APTInit')

    def list_available_devices(self, hw_type: Union[int, ThorlabsHWType] = None) \
            -> List[Tuple[int, int, int]]:
        """Lists all available Thorlabs devices, that can connect to the APT server.

        Args:
            hw_type: If this parameter is passed, the function only searches for a certain device
                     model. Otherwise (if the parameter is None), it searches for all Thorlabs
                     devices.

        Returns:
            A list of tuples. Each list-element is a tuple of 3 ints, containing the device's
            hardware type, device id and serial number: [(hw type id, device id, serial), ...]
        """
        devices = []
        count = ctypes.c_long()

        if hw_type is not None:
            # Only search for devices of the passed hardware type (model)
            if isinstance(hw_type, ThorlabsHWType):
                hw_type_range = [hw_type.value]
            else:
                hw_type_range = [int(hw_type)]
        else:
            # Search for all models
            hw_type_range = list(range(100))

        for hw_type_id in hw_type_range:
            # Get number of devices of the specific hardware type
            if self.dll.GetNumHWUnitsEx(hw_type_id, ctypes.byref(count)) == 0 and count.value > 0:
                # Is there any device of the specified hardware type
                serial_number = ctypes.c_long()
                # Get the serial numbers of all devices of that hardware type
                for ii in range(count.value):
                    if self.dll.GetHWSerialNumEx(hw_type_id, ii, ctypes.byref(serial_number)) == 0:
                        devices.append((hw_type_id, ii, serial_number.value))

        return devices

    def enable_event_dlg(self, enable: bool) -> None:
        """Activates/deactivates the event dialog, which appears when an error occurs.

        Args:
            enable: True, to enable the event dialog. False, to disable it.
        """
        c_enable = ctypes.c_bool(enable)
        code = self.dll.EnableEventDlg(c_enable)

        self.error_check(code, 'EnableEventDlg')

    def get_hw_info(self, serial_number: int) -> Tuple[str, str, str]:
        """Returns the device's information.

        Args:
            serial_number: The device's serial number for which this function is called.

        Returns:
            device model name, firmware version, hardware notes.
        """
        c_serial_number = ctypes.c_long(serial_number)
        c_sz_model = ctypes.create_string_buffer(64)
        c_sz_sw_ver = ctypes.create_string_buffer(64)
        c_sz_hw_notes = ctypes.create_string_buffer(64)

        code = self.dll.GetHWInfo(c_serial_number,
                                  c_sz_model, 64,
                                  c_sz_sw_ver, 64,
                                  c_sz_hw_notes, 64)
        self.error_check(code, 'GetHWInfo')

        return c_sz_model.value.decode('utf-8'), \
               c_sz_sw_ver.value.decode("utf-8"), \
               c_sz_hw_notes.value.decode("utf-8")

    def get_hw_serial_num_ex(self, hw_type: Union[int, ThorlabsHWType], index: int) -> int:
        """Returns the a device's serial number by passing the model's hardware type and the
        device id.

        Args:
            hw_type: Hardware type (model code) to search for.
            index: Device id

        Returns:
            The device's serial number
        """
        if isinstance(hw_type, ThorlabsHWType):
            hw_type_id = hw_type.value
        else:
            hw_type_id = int(hw_type)

        c_hw_type = ctypes.c_long(hw_type_id)
        c_index = ctypes.c_long(index)
        c_serial_number = ctypes.c_long()

        code = self.dll.GetHWSerialNumEx(c_hw_type, c_index, ctypes.byref(c_serial_number))
        self.error_check(code, 'GetHWSerialNumEx')

        return c_serial_number.value

    def init_hw_device(self, serial_number: int) -> None:
        """Initializes the device

        Args:
            serial_number: The device's serial number for which this function is called.
        """
        c_serial_number = ctypes.c_long(serial_number)
        code = self.dll.InitHWDevice(c_serial_number)
        self.error_check(code, 'InitHWDevice')

    def mot_get_position(self, serial_number: int) -> float:
        """Returns the current motor position

        Args:
            serial_number: The device's serial number for which this function is called.

        Returns:
            Motor position in degrees (0 to 360)
        """
        c_serial_number = ctypes.c_long(serial_number)
        c_position = ctypes.c_float()
        code = self.dll.MOT_GetPosition(c_serial_number, ctypes.byref(c_position))
        self.error_check(code, 'MOT_GetPosition')
        return c_position.value

    def mot_get_status_bits(self, serial_number: int) -> int:
        """Returns the motor's status bits

        Args:
            serial_number: The device's serial number for which this function is called.

        Returns:
            Status bits of the motor
        """
        c_serial_number = ctypes.c_long(serial_number)
        c_status_bits = ctypes.c_long()
        code = self.dll.MOT_GetStatusBits(c_serial_number, ctypes.byref(c_status_bits))
        self.error_check(code, 'MOT_GetStatusBits')
        return c_status_bits.value

    def mot_move_absolute_ex(self,
                             serial_number: int, absolute_position: float, wait: bool) -> None:
        """Moves the motor to an absolute position

        Args:
            serial_number: The device's serial number for which this function is called.
            position: The position to move the motor to in degrees (0 to 360)
            wait: True, to block until the motor reaches the target position. False, to do this
                  asynchronously.
        """
        c_serial_number = ctypes.c_long(serial_number)
        c_absolute_position = ctypes.c_float(absolute_position)
        c_wait = ctypes.c_bool(wait)

        code = self.dll.MOT_MoveAbsoluteEx(c_serial_number, c_absolute_position, c_wait)
        self.error_check(code, 'MOT_MoveAbsoluteEx')

    def mot_move_jog(self, serial_number: int, direction: int, wait: bool) -> None:
        """Returns the motor's status bits

        Args:
            serial_number: The device's serial number for which this function is called.
            direction: Forward (1) or reverse (2)
            wait: True, to block until the motor reaches the target position. False, to do this
                  asynchronously.
        """
        c_serial_number = ctypes.c_long(serial_number)
        c_direction = ctypes.c_long(direction)
        c_wait = ctypes.c_bool(wait)

        code = self.dll.MOT_MoveJog(c_serial_number, c_direction, c_wait)
        self.error_check(code, 'MOT_MoveJog')

    def mot_stop_profiled(self, serial_number: int) -> None:
        """Stops the motor.

        Args:
            serial_number: The device's serial number for which this function is called.
        """
        c_serial_number = ctypes.c_long(serial_number)

        code = self.dll.MOT_StopProfiled(c_serial_number)
        self.error_check(code, 'MOT_StopProfiled')

    def mot_get_velocity_parameters(self, serial_number: int) -> Tuple[float, float, float]:
        """Returns the motor's velocity parameters

        Args:
            serial_number: The device's serial number for which this function is called.

        Returns:
            minimum velocity (deg/s), acceleration (deg/s/s), maximum velocity (deg/s)
        """
        c_serial_number = ctypes.c_long(serial_number)
        c_min_vel = ctypes.c_float()
        c_accn = ctypes.c_float()
        c_max_vel = ctypes.c_float()

        code = self.dll.MOT_GetVelParams(c_serial_number,
                                         ctypes.byref(c_min_vel),
                                         ctypes.byref(c_accn),
                                         ctypes.byref(c_max_vel))
        self.error_check(code, 'MOT_SetVelParams')

        return c_min_vel.value, c_accn.value, c_max_vel.value

    def mot_set_velocity_parameters(self, serial_number: int, min_vel: float, accn: float,
                                    max_vel: float) -> None:
        """Sets the motor's velocity parameters

        Args:
            serial_number: The device's serial number for which this function is called.
            min_vel: Minimum veloctiy (starting velocity) in deg/s
            accn: Acceleration in deg/s/s
            max_vel: Maximum velocity (target velocity) in deg/s
        """
        c_serial_number = ctypes.c_long(serial_number)
        c_min_vel = ctypes.c_float(min_vel)
        c_accn = ctypes.c_float(accn)
        c_max_vel = ctypes.c_float(max_vel)

        code = self.dll.MOT_SetVelParams(c_serial_number, c_min_vel, c_accn, c_max_vel)
        self.error_check(code, 'MOT_SetVelParams')

    def mot_move_velocity(self, serial_number: int, direction: int) -> None:
        """Lets the motor rotate continuously in the specified direction.

        Args:
            serial_number: The device's serial number for which this function is called.
            direction: Forward (1) or reverse (2)
        """
        c_serial_number = ctypes.c_long(serial_number)
        c_direction = ctypes.c_long(direction)

        code = self.dll.MOT_MoveVelocity(c_serial_number, c_direction)
        self.error_check(code, 'MOT_MoveVelocity')

    def enable_hw_channel(self, serial_number: int) -> None:
        """Enables the hardware channel (often the motor)

        Args:
            serial_number: The device's serial number for which this function is called.
        """
        c_serial_number = ctypes.c_long(serial_number)

        code = self.dll.MOT_EnableHWChannel(c_serial_number)
        self.error_check(code, 'MOT_EnableHWChannel')

    def disable_hw_channel(self, serial_number: int) -> None:
        """Disables the hardware channel (often the motor)

        Args:
            serial_number: The device's serial number for which this function is called.
        """
        c_serial_number = ctypes.c_long(serial_number)

        code = self.dll.MOT_DisableHWChannel(c_serial_number)
        self.error_check(code, 'MOT_DisableHWChannel')

    def mot_move_home(self, serial_number: int, wait: bool) -> None:
        """Moves the motor to zero and recalibrates it

        Args:
            serial_number: The device's serial number for which this function is called.
            wait: True, to block until the motor reaches the target position. False, to do this
                  asynchronously.
        """
        c_serial_number = ctypes.c_long(serial_number)
        c_wait = ctypes.c_bool(wait)

        code = self.dll.MOT_MoveHome(c_serial_number, c_wait)
        self.error_check(code, 'MOT_MoveHome')

    def mot_get_home_parameters(self, serial_number: int) -> Tuple[int, int, float, float]:
        """Returns the motor's parameters for moving home

        Args:
            serial_number: The device's serial number for which this function is called.

        Returns:
            direction, home limit switch, velocity (deg/s), zero offset (deg)
        """
        c_serial_number = ctypes.c_long(serial_number)
        c_direction = ctypes.c_long()
        c_lim_switch = ctypes.c_long()
        c_velocity = ctypes.c_float()
        c_zero_offset = ctypes.c_float()

        code = self.dll.MOT_GetHomeParams(c_serial_number,
                                          ctypes.byref(c_direction), ctypes.byref(c_lim_switch),
                                          ctypes.byref(c_velocity), ctypes.byref(c_zero_offset))
        self.error_check(code, 'MOT_GetHomeParams')

        return c_direction.value, c_lim_switch.value, c_velocity.value, c_zero_offset.value

    def mot_set_home_parameters(self, serial_number: int, direction: int, lim_switch: int,
                                velocity: float, zero_offset: float) -> None:
        """Sets the motor's parameters for moving home

        Args:
            serial_number: The device's serial number for which this function is called.
            direction: Moving direction (1 for forward, 2 for reverse)
            lim_switch: Home limit switch (1 for reverse, 4 for forward)
            velocity: Moving velocity in degrees/s
            zero_offset: Offset of zero position in degrees

        Returns:
            minimum velocity (deg/s), acceleration (deg/s/s), maximum velocity (deg/s)
        """
        c_serial_number = ctypes.c_long(serial_number)
        c_direction = ctypes.c_long(direction)
        c_lim_switch = ctypes.c_long(lim_switch)
        c_velocity = ctypes.c_float(velocity)
        c_zero_offset = ctypes.c_float(zero_offset)

        code = self.dll.MOT_SetHomeParams(c_serial_number,
                                          c_direction, c_lim_switch, c_velocity, c_zero_offset)
        self.error_check(code, 'MOT_SetHomeParams')
