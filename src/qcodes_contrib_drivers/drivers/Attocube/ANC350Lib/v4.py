"""ANC350v4Lib is a Python wrapper for the C++ library of the Attocube ANC350 driver (version 4)

It depends on anc350v4.dll (and libusb0.dll) which are provided by Attocube on the installation
disc. You can find the dll files for 32-bit and 64-bit in folder ANC350_Library.
Please the dlls into the working directory or specify the path when instantiating the ANC350v4Lib.

Author:
    Lukas Lankes, Forschungszentrum Jülich GmbH / ZEA-2, l.lankes@fz-juelich.de
"""

from ctypes import c_int32, c_uint32, c_double, c_void_p, byref
from ctypes import create_string_buffer as c_string
from typing import Optional

from .interface import ANC350LibError, ANC350LibDeviceType, ANC350LibExternalTriggerMode, \
    ANC350LibTriggerPolarity, ANC350LibActuatorType
from .v3 import ANC350v3Lib, ANC350v3LibError

__all__ = ["ANC350v4Lib", "ANC350v3LibError", "ANC350LibError", "ANC350LibDeviceType",
           "ANC350LibExternalTriggerMode", "ANC350LibTriggerPolarity", "ANC350LibActuatorType"]


class ANC350v4Lib(ANC350v3Lib):
    """A wrapper class for version 4 of the ANC350 driver anc350v4.dll

    This class adapts all functions of anc350v4.dll and forwards its calls to the dll.
    ANC350v4Lib is backwards compatible to ANC350v3Lib; version 4 only has some more functions.
    """
    DEFAULT_PATH_TO_DLL = r"anc350v4.dll"

    def __init__(self, path_to_dll: Optional[str] = None):
        """Creates an instance of the anc350v4.dll-wrapper

        Args:
            path_to_dll: Path to anc350v4.dll or None, if it's stored in the working directory
        """
        super().__init__(path_to_dll)

    def register_external_ip(self, hostname: str) -> bool:
        """Register IP Device in external Network

        ``discover`` is able to find devices connected via TCP/IP in the same network segment, but
        it can't "look through" routers. To connect devices in external networks, reachable by
        routing, the IP addresses of those devices have to be registered prior to calling
        ``discover``. The function registers one device and can be called several times.

        The function will return True, if the name resolution succeeds (False otherwise); it doesn't
        test if the device is reachable. Registered and reachable devices will be found by
        ``discover``.

        Args:
            hostname: Hostname or IP Address in dotted decimal notation of the device to register.

        Returns:
            True, if the name resolution succeeds. This doesn't guarantee that the device is
            reachable. False, if the hostname couldn't be resolved.

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_hostname = c_string(hostname.encode(self._encoding))

        try:
            return_code = self._dll.ANC_registerExternalIp(byref(c_hostname))
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_registerExternalIp") from exc

        # This function returns 0 (ANC_Ok) if the hostname was added successfully (otherwise it
        # returns 9 (ANC_NoDevice)). So, don't raise an exception if this is the case.
        if return_code == 9:
            return False
        else:
            ANC350v3LibError.check_error(return_code, "ANC_registerExternalIp")
            # If no other error was raised, registering the hostname was successful
            return True

    def get_dc_voltage(self, dev_handle: c_void_p, axis_no: int) -> float:
        """Read back DC Output Voltage

        Reads back the current DC level. It may be the level that has been set by ``set_dc_voltag``
        or the value currently adjusted by the feedback controller.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)

        Returns:
            DC output voltage in Volts [V]

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_voltage = c_double()

        try:
            return_code = self._dll.ANC_getDcVoltage(dev_handle, c_axis_no, byref(c_voltage))
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_getDcVoltage") from exc
        ANC350v3LibError.check_error(return_code, "ANC_getDcVoltage")

        return c_voltage.value

    def set_target_ground(self, dev_handle: c_void_p, axis_no: int, target_ground: bool) -> None:
        """Set Target Ground Flag

        Sets or clears the Target Ground Flag. It determines the action performed in automatic
        positioning mode when the target position is reached.
        If set, the DC output is set to 0V and the position control feedback loop is stopped.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)
            target_ground: Target Ground Flag

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_target_ground = c_int32(target_ground)

        try:
            return_code = self._dll.ANC_setTargetGround(dev_handle, c_axis_no, c_target_ground)
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_setTargetGround") from exc
        ANC350v3LibError.check_error(return_code, "ANC_setTargetGround")

    def get_lut_name(self, dev_handle: c_void_p, axis_no: int) -> str:
        """Get LUT Name

        Get the name of the currently selected sensor look-up table.
        The function is only available in RES devices.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)

        Returns:
            Name of the look-up table.

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_name = c_string(20)

        try:
            return_code = self._dll.ANC_getLutName(dev_handle, c_axis_no, byref(c_name))
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_getLutName") from exc
        ANC350v3LibError.check_error(return_code, "ANC_getLutName")

        return c_name.value.decode(self._encoding)

    def load_lut_file(self, dev_handle: c_void_p, axis_no: int, file_name: str) -> None:
        """Load Lookup Table

        Loads a sensor lookup table from a file into the device.
        The function is only available in RES devices.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)
            file_name: Name of the LUT file to read, optionally with path.

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_file_name = c_string(file_name.encode(self._encoding))

        try:
            return_code = self._dll.ANC_loadLutFile(dev_handle, c_axis_no, byref(c_file_name))
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_loadLutFile") from exc
        ANC350v3LibError.check_error(return_code, "ANC_loadLutFile")

    # TODO: This function is part of the DLL but not documented. Not sure about signature, yet
    # def enable_trace(self, dev_handle: c_void_p, ...):
    #     try:
    #         return_code = self._anc350v4.ANC_enableTrace(dev_handle, ...)
    #     except Exception as exc:
    #         raise ANC350LibError("Unexpected error in ANC_enableTrace") from exc
    #     ANC350LibError.check_error(return_code, "ANC_enableTrace")
