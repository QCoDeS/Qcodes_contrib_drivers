"""ANC350v2Lib is a Python wrapper for the C++ library of the Attocube ANC350 driver (version 2)

It depends on hvpositionerv2.dll (and libusb0.dll) which are provided by Attocube on the
installation disc. You can find the dll files for 32-bit and 64-bit in folder ANC350_Library.
Please the dlls into the working directory or specify the path when instantiating the ANC350v2Lib.

Author:
    Lukas Lankes, Forschungszentrum Jülich GmbH / ZEA-2, l.lankes@fz-juelich.de
"""

import ctypes
import ctypes.util
from ctypes import c_bool, c_int32, byref
from ctypes import create_string_buffer as c_string
import locale
from typing import Iterable, Optional, Union, Tuple

from .interface import ANC350LibError, ANC350LibTriggerPolarity, ANC350LibAmplitudeControlMode, \
    ANC350LibSignalEdge, ANC350LibTriggerInputMode, ANC350LibTriggerOutputMode

__all__ = ["ANC350v2Lib", "ANC350v2LibError", "ANC350LibError", "ANC350LibTriggerPolarity",
           "ANC350LibAmplitudeControlMode", "ANC350LibSignalEdge", "ANC350LibTriggerInputMode",
           "ANC350LibTriggerOutputMode"]


class ANC350v2LibError(ANC350LibError):
    """Exception class for errors occurring in ``ANC350v2Lib``

    Attributes:
        message: Error message
        code: Error code from dll (or None)
    """
    WARNING_CODES = [4]

    def __init__(self, message: Optional[str] = None, code: Optional[int] = None):
        """Create instance of ``ANC350v2LibError``

        Args:
            message: Error message
            code: Error code from dll
        """
        super().__init__(message, code)

    @classmethod
    def _get_message_for_code(cls, code: int) -> Optional[str]:
        """Override this function to convert return codes into error messages

        Args:
            code: Occurred error code

        Returns:
            Corresponding error message for code
        """
        messages = {
            -1: "Unspecified error",
            0: "Success",
            1: "Communication timeout",
            2: "Not connected",
            3: "Driver error",
            4: "Boot ignored",
            5: "File not found",
            6: "Invalid parameter",
            7: "Device locked",
            8: "Unspecified parameter"
        }
        return messages[code] if code in messages else None


class ANC350v2Lib:
    """A wrapper class for version 2 of the ANC350 driver hvpositionerv2.dll

    This class adapts all functions of hvpositionerv2.dll and forwards its calls to the dll.
    """
    DEFAULT_PATH_TO_DLL = r"hvpositionerv2.dll"

    def __init__(self, path_to_dll: Optional[str] = None):
        """Creates an instance of the hvpositionerv2.dll-wrapper

        Args:
            path_to_dll: Path to hvpositionerv2.dll or None, if it's stored in the working directory
        """
        try:
            self._path_to_dll = ctypes.util.find_library(path_to_dll or self.DEFAULT_PATH_TO_DLL)
            if self._path_to_dll is None:
                raise FileNotFoundError("Could not find " + self.DEFAULT_PATH_TO_DLL)

            self._dll = ctypes.windll.LoadLibrary(self._path_to_dll)

            # String encoding
            self._encoding = locale.getpreferredencoding(False)
        except Exception as exc:
            raise ANC350v2LibError("Error loading " + self.DEFAULT_PATH_TO_DLL) from exc

    def check(self) -> Iterable[Tuple[int, int, bool]]:
        """Determines connected positioners and their respective hardware ids

        Returns:
            List of tuples containing the positioner's device number, its hardware id and a flag
            indicating whether the hardware is currently locked.

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        class Info(ctypes.Structure):
            _fields_ = [("id", c_int32),
                        ("locked", c_bool)]

        c_info = ctypes.POINTER(Info)()
        devices = []

        try:
            dev_count = self._dll.PositionerCheck(byref(c_info))

            if dev_count > 0 and c_info:
                for i in range(dev_count):
                    info: Tuple[int, int, bool] = (i, c_info[i].id.value, c_info[i].locked.value)
                    devices.append(info)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerCheck") from exc

        return devices

    def connect(self, dev_no: int = 0) -> Optional[c_int32]:
        """Establishes a connections to the selected device

        Args:
            dev_no: Number of the device to connect.

        Returns:
            Handle for subsequently accesses to the device.

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_dev_no = c_int32(dev_no)
        c_dev_handle = c_int32()

        try:
            return_code = self._dll.PositionerConnect(c_dev_no, byref(c_dev_handle))
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerConnect") from exc
        ANC350v2LibError.check_error(return_code, "PositionerConnect")

        return c_dev_handle if c_dev_handle else None

    def close(self, dev_handle: c_int32) -> None:
        """Closes the connection to a certain device

        Args:
            dev_handle: Handle of device to close

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        try:
            return_code = self._dll.PositionerClose(dev_handle)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerClose") from exc
        ANC350v2LibError.check_error(return_code, "PositionerClose")

    def set_hardware_id(self, dev_handle: c_int32, hardware_id: int) -> None:
        """Sets the hardware id for the device

        The hardware id serves as a differentiator in case of multiple simultaneous connected
        devices.

        Args:
            dev_handle: Handle of addressed device
            hardware_id: Hardware id

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_hardware_id = c_int32(hardware_id)

        try:
            return_code = self._dll.PositionerSetHardwareId(dev_handle, c_hardware_id)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerSetHardwareId") from exc
        ANC350v2LibError.check_error(return_code, "PositionerSetHardwareId")

    def get_status(self, dev_handle: c_int32, axis_no: int) -> Tuple[bool, bool, bool, bool]:
        """Determies the status of the selected axis

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)

        Returns:
            Status of the axis as tuple of bools:
                0. moving: True, if the axis is moving
                1. stop_detected: True, if a hump was detected
                2. sensor_error: True, if the seonsor has an error
                3. sensor_not_connected: True, if the sensor is not connected

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_status = c_int32()

        try:
            return_code = self._dll.PositionerGetStatus(dev_handle, c_axis_no, byref(c_status))
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerGetStatus") from exc
        ANC350v2LibError.check_error(return_code, "PositionerGetStatus")

        status = c_status.value
        status_moving = bool(0x1 & status)
        status_stop_detected = bool(0x2 & status)
        status_sensor_error = bool(0x4 & status)
        status_sensor_disconnected = bool(0x8 & status)

        return status_moving, status_stop_detected, status_sensor_error, status_sensor_disconnected

    def set_output(self, dev_handle: c_int32, axis_no: int, enable: bool) -> None:
        """Activates / deactivates the output relais of the addressed axis.

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)
            enable: True, to activate the output relais; False, to deactivate it.

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_enable = c_bool(enable)

        try:
            return_code = self._dll.PositionerSetOutput(dev_handle, c_axis_no, c_enable)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerSetOutput") from exc
        ANC350v2LibError.check_error(return_code, "PositionerSetOutput")

    def set_static_amplitude(self, dev_handle: c_int32, amplitude: int) -> None:
        """Sets the output voltage for resistive sensors

        Args:
            dev_handle: Handle of addressed device
            amplitude: Amplitude in millivolts [mV]

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_amplitude = c_int32(amplitude)

        try:
            return_code = self._dll.PositionerStaticAmplitude(dev_handle, c_amplitude)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerStaticAmplitude") from exc
        ANC350v2LibError.check_error(return_code, "PositionerStaticAmplitude")

    def enable_dc_input(self, dev_handle: c_int32, axis_no: int, enable: bool = True) -> None:
        """Activates / deactivates the DC input of the addressed axis

        Only applicable for scanner and dither axes.

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)
            enable: Status of input (True: activated, False: deactivated)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_enable = c_bool(enable)

        try:
            return_code = self._dll.PositionerDcInEnable(dev_handle, c_axis_no, c_enable)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerDcInEnable") from exc
        ANC350v2LibError.check_error(return_code, "PositionerDcInEnable")

    def is_dc_input_enabled(self, dev_handle: c_int32, axis_no: int) -> bool:
        """Determines the status of DC input of the addressed axis

        Only applicable for scanner and dither axes.

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)

        Returns:
            Status of input (True: activated, False: deactivated)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_enabled = c_bool()

        try:
            return_code = self._dll.PositionerGetDcInEnable(dev_handle, c_axis_no, byref(c_enabled))
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerGetDcInEnable") from exc
        ANC350v2LibError.check_error(return_code, "PositionerGetDcInEnable")

        return c_enabled.value

    def enable_ac_input(self, dev_handle: c_int32, axis_no: int, enable: bool = True) -> None:
        """Activates / deactivates the AC input of the addressed axis

        Only applicable for dither axis.

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)
            enable: Status of input (True: activated, False: deactivated)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_enable = c_bool(enable)

        try:
            return_code = self._dll.PositionerAcInEnable(dev_handle, c_axis_no, c_enable)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerAcInEnable") from exc
        ANC350v2LibError.check_error(return_code, "PositionerAcInEnable")

    def is_ac_input_enabled(self, dev_handle: c_int32, axis_no: int) -> bool:
        """Determines the status of AC input of the addressed axis

        Only applicable for dither axis.

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)

        Returns:
            Status of input (True: activated, False: deactivated)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_enabled = c_bool()

        try:
            return_code = self._dll.PositionerGetAcInEnable(dev_handle, c_axis_no, byref(c_enabled))
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerGetAcInEnable") from exc
        ANC350v2LibError.check_error(return_code, "PositionerGetAcInEnable")

        return c_enabled.value

    def enable_internal_signal(self, dev_handle: c_int32, axis_no: int, enable: bool) -> None:
        """Activates / Deactivates the internal signal generation of the addressed axis

        Only applicable for scanner and dither axes.

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)
            enable: Status of internal signal (True: activated, False: deactivated)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_enable = c_bool(enable)

        try:
            return_code = self._dll.PositionerIntEnable(dev_handle, c_axis_no, c_enable)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerIntEnable") from exc
        ANC350v2LibError.check_error(return_code, "PositionerIntEnable")

    def is_internal_signal_enabled(self, dev_handle: c_int32, axis_no: int) -> bool:
        """Determines the status of internal signal generation of the addressed axis

        Only applicable for scanner and dither axes.

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)

        Returns:
            Status of input (True: activated, False: deactivated)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_enabled = c_bool()

        try:
            return_code = self._dll.PositionerGetIntEnable(dev_handle, c_axis_no, byref(c_enabled))
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerGetIntEnable") from exc
        ANC350v2LibError.check_error(return_code, "PositionerGetIntEnable")

        return c_enabled.value

    def enable_bandwidth_limit(self, dev_handle: c_int32, axis_no: int,
                               enable: bool = True) -> None:
        """Activates / Deactivates the band width limiter of the addressed axis

        Only applicable for scanner axes.

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)
            enable: Status of bandwidth limiter (True: activated, False: deactivated)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_enable = c_bool(enable)

        try:
            return_code = self._dll.PositionerBandwidthLimitEnable(dev_handle, c_axis_no, c_enable)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerBandwidthLimitEnable") from exc
        ANC350v2LibError.check_error(return_code, "PositionerBandwidthLimitEnable")

    def is_bandwidth_limit_enabled(self, dev_handle: c_int32, axis_no: int) -> bool:
        """Determines the status of the band width limiter of the addressed axis

        Only applicable for scanner axes.

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)

        Returns:
            Status of bandwidth limiter (True: activated, False: deactivated)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_enabled = c_bool()

        try:
            return_code = self._dll.PositionerGetBandwidthLimitEnable(dev_handle, c_axis_no,
                                                                      byref(c_enabled))
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerGetBandwidthLimitEnable") from exc
        ANC350v2LibError.check_error(return_code, "PositionerGetBandwidthLimitEnable")

        return c_enabled.value

    def measure_capacity(self, dev_handle: c_int32, axis_no: int) -> Optional[int]:
        """Determines the capacity of the piezo of the addressed axis by measurement

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)

        Returns:
            Measured capacity in picofarad [pF] or None, in case of an error

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_capacity = c_int32()

        try:
            return_code = self._dll.PositionerCapMeasure(dev_handle, c_axis_no, byref(c_capacity))
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerCapMeasure") from exc
        ANC350v2LibError.check_error(return_code, "PositionerCapMeasure")

        return c_capacity.value if c_capacity.value >= 0 else None

    def enable_sensor_power_group_a(self, dev_handle: c_int32, enable: bool = True) -> None:
        """Switches power of sensor group A.

        Sensor group A contains either the sensors of axis 1..3 or 1..2 dependent on hardware of
        controller.

        Args:
            dev_handle: Handle of addressed device
            enable: Switch (True: on, False: off)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_enable = c_bool(enable)

        try:
            return_code = self._dll.PositionerSensorPowerGroupA(dev_handle, c_enable)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerSensorPowerGroupA") from exc
        ANC350v2LibError.check_error(return_code, "PositionerSensorPowerGroupA")

    def enable_sensor_power_group_b(self, dev_handle: c_int32, enable: bool = True) -> None:
        """Switches power of sensor group B.

        Sensor group B contains either the sensors of axis 4..6 or 3 dependent on hardware of
        controller.

        Args:
            dev_handle: Handle of addressed device
            enable: Switch (True: on, False: off)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_enable = c_bool(enable)

        try:
            return_code = self._dll.PositionerSensorPowerGroupB(dev_handle, c_enable)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerSensorPowerGroupB") from exc
        ANC350v2LibError.check_error(return_code, "PositionerSensorPowerGroupB")

    def enable_duty_cycle(self, dev_handle: c_int32, enable: bool = True) -> None:
        """Controls duty cycle mode

        Args:
            dev_handle: Handle of addressed device
            enable: Switch (True: on, False: off)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_enable = c_int32(enable)

        try:
            return_code = self._dll.PositionerDutyCycleEnable(dev_handle, c_enable)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerDutyCycleEnable") from exc
        ANC350v2LibError.check_error(return_code, "PositionerDutyCycleEnable")

    def set_duty_cycle_period(self, dev_handle: c_int32, period: int) -> None:
        """Sets the duty cycle period

        Args:
            dev_handle: Handle of addressed device
            period: Period in milliseconds [ms]

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_period = c_int32(period)

        try:
            return_code = self._dll.PositionerDutyCyclePeriod(dev_handle, c_period)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerDutyCyclePeriod") from exc
        ANC350v2LibError.check_error(return_code, "PositionerDutyCyclePeriod")

    def set_duty_cycle_off_time(self, dev_handle: c_int32, off_time: int) -> None:
        """Sets the duty cycle period

        Args:
            dev_handle: Handle of addressed device
            off_time: Period in milliseconds [ms]

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_off_time = c_int32(off_time)

        try:
            return_code = self._dll.PositionerDutyCycleOffTime(dev_handle, c_off_time)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerDutyCycleOffTime") from exc
        ANC350v2LibError.check_error(return_code, "PositionerDutyCycleOffTime")

    def get_position(self, dev_handle: c_int32, axis_no: int) -> int:
        """Determines the actual position of the addressed axis

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)

        Returns:
            Position in unit of actor multiplied by 1000

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_position = c_int32()

        try:
            return_code = self._dll.PositionerGetPosition(dev_handle, c_axis_no, byref(c_position))
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerGetPosition") from exc
        ANC350v2LibError.check_error(return_code, "PositionerGetPosition")

        return c_position.value

    def get_rotation_count(self, dev_handle: c_int32, axis_no: int) -> int:
        """Determines the actual number of rotations in case of a rotary actor

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)

        Returns:
            Number of rotations

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_rotations = c_int32()

        try:
            return_code = self._dll.foo(dev_handle, c_axis_no, byref(c_rotations))
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerGetRotCount") from exc
        ANC350v2LibError.check_error(return_code, "PositionerGetRotCount")

        return c_rotations.value

    def get_reference(self, dev_handle: c_int32, axis_no: int) -> Tuple[int, bool]:
        """Determines the distance of reference mark to the origin

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)

        Returns:
            Tuple containing the reference position:
                0. position: Reference position in unit of actor
                1. valid: True, if reference position is valid.

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_position = c_int32()
        c_valid = c_bool()

        try:
            return_code = self._dll.PositionerGetReference(dev_handle, c_axis_no, byref(c_position),
                                                           byref(c_valid))
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerGetReference") from exc
        ANC350v2LibError.check_error(return_code, "PositionerGetReference")

        # TODO: Could we only return position if valid is True and return None, if valid is False?
        # Then, one return value would be enough
        return c_position.value, c_valid.value

    def get_reference_rotation_count(self, dev_handle: c_int32, axis_no: int) -> int:
        """Determines the actual number of rotations for the reference position in case of a rotary
        actor

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)

        Returns:
            Number of rotations

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_count = c_int32()

        try:
            return_code = self._dll.PositionerGetReferenceRotCount(dev_handle, c_axis_no,
                                                                   byref(c_count))
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerGetReferenceRotCount") from exc
        ANC350v2LibError.check_error(return_code, "PositionerGetReferenceRotCount")

        return c_count.value

    def reset_position(self, dev_handle: c_int32, axis_no: int) -> None:
        """Sets the origin to the actual position

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)

        try:
            return_code = self._dll.PositionerResetPosition(dev_handle, c_axis_no)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerResetPosition") from exc
        ANC350v2LibError.check_error(return_code, "PositionerResetPosition")

    def move_absolute(self, dev_handle: c_int32, axis_no: int, position: int,
                      rotation_count: int = 0) -> None:
        """Starts approach to absolute target position

        Previous movement will be stopped.

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)
            position: Target position in unit of actor multiplied by 1000
            rotation_count: Number of rotations in case of rotary actor and deactivated single
                            circle mode

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_position = c_int32(position)
        c_rotation_count = c_int32(rotation_count)

        try:
            return_code = self._dll.PositionerMoveAbsolute(dev_handle, c_axis_no, c_position,
                                                           c_rotation_count)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerMoveAbsolute") from exc
        ANC350v2LibError.check_error(return_code, "PositionerMoveAbsolute")

    def update_absolute(self, dev_handle: c_int32, axis_no: int, position: int) -> None:
        """Updates target position for a running approach

        This function has a lower performance impact on a running approach asv ``move_absolute``.

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)
            position: Target position in unit of actor multiplied by 1000

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_position = c_int32(position)

        try:
            return_code = self._dll.PositionerUpdateAbsolute(dev_handle, c_axis_no, c_position)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerUpdateAbsolute") from exc
        ANC350v2LibError.check_error(return_code, "PositionerUpdateAbsolute")

    def move_relative(self, dev_handle: c_int32, axis_no: int, distance: int,
                      rotation_count: int = 0) -> None:
        """Starts approach to relative target position

        Previous movement will be stopped.

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)
            distance: Relative position in unit of actor multiplied by 1000
            rotation_count: Number of rotations in case of rotary actor and deactivated single
                            circle mode

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_distance = c_int32(distance)
        c_rotation_count = c_int32(rotation_count)

        try:
            return_code = self._dll.PositionerMoveRelative(dev_handle, c_axis_no, c_distance,
                                                           c_rotation_count)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerMoveRelative") from exc
        ANC350v2LibError.check_error(return_code, "PositionerMoveRelative")

    def move_reference(self, dev_handle: c_int32, axis_no: int) -> None:
        """Starts approach to reference position

        Previous movement will be stopped.

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)

        try:
            return_code = self._dll.PositionerMoveReference(dev_handle, c_axis_no)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerMoveReference") from exc
        ANC350v2LibError.check_error(return_code, "PositionerMoveReference")

    def stop_approach(self, dev_handle: c_int32, axis_no: int) -> None:
        """Stops approaching target, relative or reference position of selected axis

        DC level of affected axis after stopping depends on setting by ``set_target_ground``.

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)

        try:
            return_code = self._dll.PositionerStopApproach(dev_handle, c_axis_no)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerStopApproach") from exc
        ANC350v2LibError.check_error(return_code, "PositionerStopApproach")

    def enable_stop_detection(self, dev_handle: c_int32, axis_no: int, enable: bool = True) -> None:
        """Switches Stop Detection

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)
            enable: Switch (True=on, False=off)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_enable = c_bool(enable)

        try:
            return_code = self._dll.PositionerStopDetection(dev_handle, c_axis_no, c_enable)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerStopDetection") from exc
        ANC350v2LibError.check_error(return_code, "PositionerStopDetection")

    def enable_stop_detection_sticky(self, dev_handle: c_int32, axis_no: int,
                                     enable: bool = True) -> None:
        """When enabled, an active stop detection status remains active until cleared manually by
        PositionerClearStopDetection.

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)
            enable: Switch (True: on, False: off)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_enable = c_bool(enable)

        try:
            return_code = self._dll.PositionerSetStopDetectionSticky(dev_handle, c_axis_no,
                                                                     c_enable)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerSetStopDetectionSticky") from exc
        ANC350v2LibError.check_error(return_code, "PositionerSetStopDetectionSticky")

    def clear_stop_detection(self, dev_handle: c_int32, axis_no: int) -> None:
        """When PositionerSetStopDetectionAuto (?) is disabled, this clears the stop detection
         status

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)

        try:
            return_code = self._dll.PositionerClearStopDetection(dev_handle, c_axis_no)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerClearStopDetection") from exc
        ANC350v2LibError.check_error(return_code, "PositionerClearStopDetection")

    def single_circle_mode(self, dev_handle: c_int32, axis_no: int, enable: bool) -> None:
        """Switches single circle mode

        In case of activated single circle mode the number of rotations are ignored and the shortest
        way to target position is used. Only relevant for rotary actors.

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)
            enable: Switch (True=on, False=off)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_enable = c_bool(enable)

        try:
            return_code = self._dll.PositionerSingleCircleMode(dev_handle, c_axis_no, c_enable)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerSingleCircleMode") from exc
        ANC350v2LibError.check_error(return_code, "PositionerSingleCircleMode")

    def enable_target_ground(self, dev_handle: c_int32, axis_no: int, enable: bool = True) -> None:
        """When enabled, the actor voltage is set to zero after closed loop positioning finished

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)
            enable: Switch (True: on, False: off)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_enable = c_bool(enable)

        try:
            return_code = self._dll.PositionerSetTargetGround(dev_handle, c_axis_no, c_enable)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerSetTargetGround") from exc
        ANC350v2LibError.check_error(return_code, "PositionerSetTargetGround")

    def set_target_position(self, dev_handle: c_int32, axis_no: int, position: int,
                            rotation_count: int) -> None:
        """When enabled, the actor voltage is set to zero after closed loop positioning finished

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)
            position: Target position in unit of actor multiplied by 1000
            rotation_count: Number of rotations in case of rotary actor and deactivated single
                            circle mode

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_position = c_int32(position)
        c_rotation_count = c_int32(rotation_count)

        try:
            return_code = self._dll.PositionerSetTargetPos(dev_handle, c_axis_no, c_position,
                                                           c_rotation_count)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerSetTargetPos") from exc
        ANC350v2LibError.check_error(return_code, "PositionerSetTargetPos")

    def move_absolute_sync(self, dev_handle: c_int32, bitmask_of_axes: int) -> None:
        """Starts the synchronous approach to absolute target positions for selected axes

        Previous movement will be stopped. The target positions for each axis is defined by
        ``set_target_position``.

        Args:
            dev_handle: Handle of addressed device
            bitmask_of_axes: Bitmask of axes to start (TODO: Solve this with Enum, IntFlags or List)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axes = c_int32(bitmask_of_axes)

        try:
            return_code = self._dll.PositionerMoveAbsoluteSync(dev_handle, c_axes)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerMoveAbsoluteSync") from exc
        ANC350v2LibError.check_error(return_code, "PositionerMoveAbsoluteSync")

    def set_amplitude_control_mode(self, dev_handle: c_int32, axis_no: int,
                                   mode: Union[ANC350LibAmplitudeControlMode, int]) -> None:
        """Selects type of amplitude control

        The amplitude is controlled by the positioner to hold the value constant determined by the
        selected type of amplitude control.

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)
            mode: Type of amplitude control: speed (0), amplitude (1) or step size (2)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_mode = c_int32(int(mode))

        try:
            return_code = self._dll.PositionerAmplitudeControl(dev_handle, c_axis_no, c_mode)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerAmplitudeControl") from exc
        ANC350v2LibError.check_error(return_code, "PositionerAmplitudeControl")

    def set_amplitude(self, dev_handle: c_int32, axis_no: int, amplitude: int) -> None:
        """Sets the amplitude setpoint

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)
            amplitude: Amplitude in millivolts [mV]

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_amplitude = c_int32(amplitude)

        try:
            return_code = self._dll.PositionerAmplitude(dev_handle, c_axis_no, c_amplitude)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerAmplitude") from exc
        ANC350v2LibError.check_error(return_code, "PositionerAmplitude")

    def get_amplitude(self, dev_handle: c_int32, axis_no: int) -> int:
        """Determines the actual amplitude

        In case of standstill of the actor this is the amplitude setpoint. In case of movement the
        amplitude set by amplitude control is determined.

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)

        Returns:
            Amplitude in millivolts [mV]

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_amplitude = c_int32()

        try:
            return_code = self._dll.PositionerGetAmplitude(dev_handle, c_axis_no,
                                                           byref(c_amplitude))
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerGetAmplitude") from exc
        ANC350v2LibError.check_error(return_code, "PositionerGetAmplitude")

        return c_amplitude.value

    def get_speed(self, dev_handle: c_int32, axis_no: int) -> int:
        """Determines the actual speed

        In case of standstill of the actor this is the calculated speed resulting from amplitude
        setpoint, frequency and motor parameters. In case of movement this is the measured speed.

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)

        Returns:
            Speed in unit of actor per second multiplied by 1000

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_speed = c_int32()

        try:
            return_code = self._dll.PositionerGetSpeed(dev_handle, c_axis_no, byref(c_speed))
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerGetSpeed") from exc
        ANC350v2LibError.check_error(return_code, "PositionerGetSpeed")

        return c_speed.value

    def get_step_width(self, dev_handle: c_int32, axis_no: int) -> int:
        """Determines the step width.

        In case of standstill of the motor this is the calculated step width resulting from
        amplitude setpoint, frequency and motor parameters. In case of movement this is the measured
        step width.

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)

        Returns:
            Step width in unit of actor multiplied by 1000

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_step_width = c_int32()

        try:
            return_code = self._dll.PositionerGetStepwidth(dev_handle, c_axis_no,
                                                           byref(c_step_width))
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerGetStepwidth") from exc
        ANC350v2LibError.check_error(return_code, "PositionerGetStepwidth")

        return c_step_width.value

    def move_single_step(self, dev_handle: c_int32, axis_no: int, backward: bool) -> None:
        """Starts a one step positioning

        Previous movement will be stopped.

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)
            backward: Direction for positioning (False: forward, True: backward)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_direction = c_int32(int(backward))

        try:
            return_code = self._dll.PositionerMoveSingleStep(dev_handle, c_axis_no, c_direction)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerMoveSingleStep") from exc
        ANC350v2LibError.check_error(return_code, "PositionerMoveSingleStep")

    def move_continuously(self, dev_handle: c_int32, axis_no: int, backward: bool) -> None:
        """Starts continuously positioning with set parameters for amplitude and speed and amplitude
        control respectively.

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)
            backward: Direction for positioning (False: forward, True: backward)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_direction = c_int32(int(backward))

        try:
            return_code = self._dll.PositionerMoveContinuous(dev_handle, c_axis_no, c_direction)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerMoveContinuous") from exc
        ANC350v2LibError.check_error(return_code, "PositionerMoveContinuous")

    def stop_moving(self, dev_handle: c_int32, axis_no: int) -> None:
        """Stops any positioning.

        DC level of affected axis is zero after stopping

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)

        try:
            return_code = self._dll.PositionerStopMoving(dev_handle, c_axis_no)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerStopMoving") from exc
        ANC350v2LibError.check_error(return_code, "PositionerStopMoving")

    def set_external_step_forward_input(self, dev_handle: c_int32, axis_no: int,
                                        trigger_input: int) -> None:
        """Configures external step trigger input for selected axis

        A trigger on this input results in a forward single step.

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)
            trigger_input: Trigger input (0: disabled, 1..6 input trigger)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_input = c_int32(trigger_input)

        try:
            return_code = self._dll.PositionerExternalStepFwdInput(dev_handle, c_axis_no, c_input)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerExternalStepFwdInput") from exc
        ANC350v2LibError.check_error(return_code, "PositionerExternalStepFwdInput")

    def set_external_step_backward_input(self, dev_handle: c_int32, axis_no: int,
                                         trigger_input: int) -> None:
        """Configures external step trigger input for selected axis

        A trigger on this input results in a backward single step.

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)
            trigger_input: Trigger input (0: disabled, 1..6 input trigger)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_input = c_int32(trigger_input)

        try:
            return_code = self._dll.PositionerExternalStepBkwInput(dev_handle, c_axis_no, c_input)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerExternalStepBkwInput") from exc
        ANC350v2LibError.check_error(return_code, "PositionerExternalStepBkwInput")

    def set_external_step_input_edge(self, dev_handle: c_int32, axis_no: int,
                                     edge: Union[ANC350LibSignalEdge, int]) -> None:
        """Configures edge sensitivity of external step trigger input for selected axis

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)
            edge: Edge of trigger (0: raising, 1: falling)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_edge = c_int32(int(edge))

        try:
            return_code = self._dll.PositionerExternalStepInputEdge(dev_handle, c_axis_no, c_edge)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerExternalStepInputEdge") from exc
        ANC350v2LibError.check_error(return_code, "PositionerExternalStepInputEdge")

    def set_external_step_count(self, dev_handle: c_int32, axis_no: int, step_count: int) -> None:
        """Configures the number of successive steps caused by external trigger, or manual step
        request

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)
            step_count: Number of steps (1..65535)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_step_count = c_int32(step_count)

        try:
            return_code = self._dll.PositionerStepCount(dev_handle, c_axis_no, c_step_count)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerStepCount") from exc
        ANC350v2LibError.check_error(return_code, "PositionerStepCount")

    def set_frequency(self, dev_handle: c_int32, axis_no: int, frequency: int) -> None:
        """Sets the frequency

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)
            frequency: Frequency in Hertz [Hz]

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_frequency = c_int32(frequency)

        try:
            return_code = self._dll.PositionerFrequency(dev_handle, c_axis_no, c_frequency)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerFrequency") from exc
        ANC350v2LibError.check_error(return_code, "PositionerFrequency")

    def get_frequency(self, dev_handle: c_int32, axis_no: int) -> int:
        """Determines the frequency

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)

        Returns:
            Frequency in Hertz [Hz]

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_frequency = c_int32()

        try:
            return_code = self._dll.PositionerGetFrequency(dev_handle, c_axis_no,
                                                           byref(c_frequency))
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerGetFrequency") from exc
        ANC350v2LibError.check_error(return_code, "PositionerGetFrequency")

        return c_frequency.value

    def set_dc_level(self, dev_handle: c_int32, axis_no: int, dc_level: int) -> None:
        """Sets the DC level

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)
            dc_level: DC level in millivolts [mV]

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_dc_level = c_int32(dc_level)

        try:
            return_code = self._dll.PositionerDCLevel(dev_handle, c_axis_no, c_dc_level)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerDCLevel") from exc
        ANC350v2LibError.check_error(return_code, "PositionerDCLevel")

    def get_dc_level(self, dev_handle: c_int32, axis_no: int) -> int:
        """Determines the status actual DC Level

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)

        Returns:
            DC level in millivolts [mV]

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_dc_level = c_int32()

        try:
            return_code = self._dll.PositionerGetDcLevel(dev_handle, c_axis_no, byref(c_dc_level))
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerGetDcLevel") from exc
        ANC350v2LibError.check_error(return_code, "PositionerGetDcLevel")

        return c_dc_level.value

    def set_input_trigger_mode(self, dev_handle: c_int32,
                               mode: Union[ANC350LibTriggerInputMode, int]) -> None:
        """Selects the mode of the input trigger signals

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)
            mode: Mode of trigger pins (see ``ANC350LibTriggerInputMode``)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_mode = c_int32(int(mode))

        try:
            return_code = self._dll.PositionerTriggerModeIn(dev_handle, c_mode)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerTriggerModeIn") from exc
        ANC350v2LibError.check_error(return_code, "PositionerTriggerModeIn")

    def set_output_trigger_mode(self, dev_handle: c_int32,
                                mode: Union[ANC350LibTriggerOutputMode, int]) -> None:
        """Selects the mode of the output trigger signals

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)
            mode: Mode of trigger pins (see ``ANC350LibTriggerOutputMode``)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_mode = c_int32(int(mode))

        try:
            return_code = self._dll.PositionerTriggerModeOut(dev_handle, c_mode)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerTriggerModeOut") from exc
        ANC350v2LibError.check_error(return_code, "PositionerTriggerModeOut")

    def set_trigger(self, dev_handle: c_int32, trigger_no: int, low_level: int,
                    high_level: int) -> None:
        """Sets the trigger thresholds for external trigger.

        Args:
            dev_handle: Handle of addressed device
            trigger_no: Number of addressed Trigger (0..5)
            low_level: Lower trigger threshold in unit of actor multiplied by 1000
            high_level: Upper trigger threshold in unit of actor multiplied by 1000

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_trigger_no = c_int32(trigger_no)
        c_low_level = c_int32(low_level)
        c_high_level = c_int32(high_level)

        try:
            return_code = self._dll.PositionerTrigger(dev_handle, c_trigger_no, c_low_level,
                                                      c_high_level)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerTrigger") from exc
        ANC350v2LibError.check_error(return_code, "PositionerTrigger")

    def set_trigger_axis(self, dev_handle: c_int32, trigger_no: int, axis_no: int) -> None:
        """Selects the corresponding axis for the addressed trigger

        Args:
            dev_handle: Handle of addressed device
            trigger_no: Number of addressed Trigger (0..5)
            axis_no: Number of addressed axis (0..2)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_trigger_no = c_int32(trigger_no)
        c_axis_no = c_int32(axis_no)

        try:
            return_code = self._dll.PositionerTriggerAxis(dev_handle, c_trigger_no, c_axis_no)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerTriggerAxis") from exc
        ANC350v2LibError.check_error(return_code, "PositionerTriggerAxis")

    def set_trigger_polarity(self, dev_handle: c_int32, trigger_no: int,
                             polarity: Union[ANC350LibTriggerPolarity, int]) -> None:
        """Sets the polarity of the external trigger

        Args:
            dev_handle: Handle of addressed device
            trigger_no: Number of addressed Trigger (0..5)
            polarity: Polarity (0: low active, 1: high active)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_trigger_no = c_int32(trigger_no)
        c_polarity = c_int32(int(polarity))

        try:
            return_code = self._dll.PositionerTriggerPolarity(dev_handle, c_trigger_no, c_polarity)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerTriggerPolarity") from exc
        ANC350v2LibError.check_error(return_code, "PositionerTriggerPolarity")

    def set_trigger_epsilon(self, dev_handle: c_int32, trigger_no: int, epsilon: int) -> None:
        """Sets the hysteresis of the external trigger

        Args:
            dev_handle: Handle of addressed device
            trigger_no: Number of addressed Trigger (0..5)
            epsilon: Hysteresis in unit of actor multiplied by 1000

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_trigger_no = c_int32(trigger_no)
        c_epsilon = c_int32(epsilon)

        try:
            return_code = self._dll.PositionerTriggerEpsilon(dev_handle, c_trigger_no, c_epsilon)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerTriggerEpsilon") from exc
        ANC350v2LibError.check_error(return_code, "PositionerTriggerEpsilon")

    def set_quadratur_axis(self, dev_handle: c_int32, quadratur_no: int, axis_no: int) -> None:
        """Selects the axis for use with this trigger in/out pair

        Args:
            dev_handle: Handle of addressed device
            quadratur_no: Number of addressed quadrature unit (0..2)
            axis_no: Selected axis (0..2)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_quadratur_no = c_int32(quadratur_no)
        c_axis_no = c_int32(axis_no)

        try:
            return_code = self._dll.PositionerQuadratureAxis(dev_handle, c_quadratur_no, c_axis_no)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerQuadratureAxis") from exc
        ANC350v2LibError.check_error(return_code, "PositionerQuadratureAxis")

    def set_quadratur_input_period(self, dev_handle: c_int32, quadratur_no: int,
                                   period: int) -> None:
        """Selects the stepsize the controller executes when detecting a step on its input AB-signal

        Args:
            dev_handle: Handle of addressed device
            quadratur_no: Number of addressed quadrature unit (0..2)
            period: stepsize in unit of actor multiplied by 1000

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_quadratur_no = c_int32(quadratur_no)
        c_period = c_int32(period)

        try:
            return_code = self._dll.PositionerQuadratureInputPeriod(dev_handle, c_quadratur_no,
                                                                    c_period)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerQuadratureInputPeriod") from exc
        ANC350v2LibError.check_error(return_code, "PositionerQuadratureInputPeriod")

    def set_quadratur_output_period(self, dev_handle: c_int32, quadratur_no: int,
                                    period: int) -> None:
        """Selects the position difference which causes a step on the output AB-signal

        Args:
            dev_handle: Handle of addressed device
            quadratur_no: Number of addressed quadrature unit (0..2)
            period: stepsize in unit of actor multiplied by 1000

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_quadratur_no = c_int32(quadratur_no)
        c_period = c_int32(period)

        try:
            return_code = self._dll.PositionerQuadratureOutputPeriod(dev_handle, c_quadratur_no,
                                                                     c_period)
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerQuadratureOutputPeriod") from exc
        ANC350v2LibError.check_error(return_code, "PositionerQuadratureOutputPeriod")

    def load_params(self, dev_handle: c_int32, axis_no: int, file_name: str) -> None:
        """Loads a parameter file for actor configuration

        Args:
            dev_handle: Handle of addressed device
            axis_no: Number of addressed axis (0..2)
            file_name: Path to parameter file

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_int32(axis_no)
        c_file_name = c_string(file_name.encode(self._encoding))

        try:
            return_code = self._dll.PositionerLoad(dev_handle, c_axis_no, byref(c_file_name))
        except Exception as exc:
            raise ANC350v2LibError("Unexpected error in PositionerLoad") from exc
        ANC350v2LibError.check_error(return_code, "PositionerLoad")
