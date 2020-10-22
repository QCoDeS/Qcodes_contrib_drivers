"""ANC350v3Lib is a Python wrapper for the C++ library of the Attocube ANC350 driver (version 3)

It depends on anc350v3.dll (and libusb0.dll) which are provided by Attocube on the installation
disc. You can find the dll files for 32-bit and 64-bit in folder ANC350_Library.
Please the dlls into the working directory or specify the path when instantiating the ANC350v3Lib.

Author:
    Lukas Lankes, Forschungszentrum Jülich GmbH / ZEA-2, l.lankes@fz-juelich.de
"""

import ctypes
import ctypes.util
from ctypes import c_int8, c_int32, c_uint32, c_double, c_void_p, byref
from ctypes import create_string_buffer as c_string
import locale
from typing import Any, Optional, Tuple, Union
import sys

from .interface import ANC350LibError, ANC350LibDeviceType, ANC350LibExternalTriggerMode, \
    ANC350LibTriggerPolarity, ANC350LibActuatorType

__all__ = ["ANC350v3Lib", "ANC350v3LibError", "ANC350LibError", "ANC350LibDeviceType",
           "ANC350LibExternalTriggerMode", "ANC350LibTriggerPolarity", "ANC350LibActuatorType"]


class ANC350v3LibError(ANC350LibError):
    """Exception class for errors occurring in ``ANC350v3Lib`` and ``ANC350v4Lib``

    Attributes:
        message: Error message
        code: Error code from dll (or None)
    """

    def __init__(self, message: Optional[str] = None, code: Optional[int] = None):
        """Create instance of ``ANC350v3LibError``

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
            7: "Device locked",
            8: "Unknown error",
            9: "Invalid device number",
            10: "Invalid axis number",
            11: "Parameter out of range",
            12: "Function not available",
            13: "Can't open or parse file"
        }
        return messages[code] if code in messages else None


class ANC350v3Lib:
    """A wrapper class for version 3 of the ANC350 driver anc350v3.dll

    This class adapts all functions of anc350v3.dll and forwards its calls to the dll.
    """
    DEFAULT_PATH_TO_DLL = r"anc350v3.dll"

    def __init__(self, path_to_dll: Optional[str] = None):
        """Creates an instance of the anc350v3.dll-wrapper

        Args:
            path_to_dll: Path to anc350v3.dll or None, if it's stored in the working directory
        """
        if not path_to_dll:
            path_to_dll = self.DEFAULT_PATH_TO_DLL

        try:
            if sys.platform != 'win32':
                self._dll: Any = None
                self._encoding: Any = None
                raise OSError("\"anc350v3.dll\" is only compatible with Microsoft Windows")

            self._path_to_dll = ctypes.util.find_library(path_to_dll or self.DEFAULT_PATH_TO_DLL)
            if self._path_to_dll is None:
                raise FileNotFoundError("Could not find " + path_to_dll)

            self._dll = ctypes.windll.LoadLibrary(self._path_to_dll)

            # String encoding
            self._encoding = locale.getpreferredencoding(False)
        except Exception as exc:
            raise ANC350v3LibError("Error loading " + path_to_dll) from exc

    def discover(self, search_usb: bool = True, search_tcp: bool = True) -> int:
        """Discover Devices

        The function searches for connected ANC350RES devices on USB and LAN and initializes
        internal data structures per device. Devices that arwe in use by another application or PC
        are not found. The function must be called before connecting to a device and must not be
        called as long as any devices are connected.

        The number of devices found is returned. In subsequent functions, devices are identified by
        a sequence number that must be less than the number returned.

        Args:
            search_usb: True (default) to search for USB devices; False otherwise
            search_tcp: True (default) to search for TCP/IP devices; False otherwise

        Returns:
            Number of devices found

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        interfaces = (0x1 if search_usb else 0x0) | (0x2 if search_tcp else 0x0)
        c_interfaces = c_int32(interfaces)
        c_dev_count = c_uint32()

        try:
            return_code = self._dll.ANC_discover(c_interfaces, byref(c_dev_count))
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_discover") from exc
        ANC350v3LibError.check_error(return_code, "ANC_discover")

        return c_dev_count.value

    def get_device_info(self, dev_no: int = 0) -> Tuple[ANC350LibDeviceType, int, str, str, bool]:
        """Device Information

        Returns available information about a device. The function can not be called before
        ``discover`` but the devices don't have to be connected with ``connect``. All Pointers to
        output parameters may be zero to ignore the respective value.

        Args:
            dev_no: Sequence number of the device. Must be smaller than the return value from the
                    last ``ANC_discover`` call (default: 0).

        Returns:
            A tuple containing the device's information:
                0. dev_type: Type of the ANC350 device
                1. id: Programmed hardware ID of the device
                2. serial: The device's serial number
                3. address: The device's interface address if applicable. Returns the IP address in
                         dotted-decimal notation or the string "USB", respectively
                4. connected: True, if the device is already connected

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_dev_no = c_uint32(dev_no)
        c_dev_type = c_int32()
        c_id = c_int8()
        c_serial = c_string(16)
        c_address = c_string(16)
        c_connected = c_int32()

        try:
            return_code = self._dll.ANC_getDeviceInfo(c_dev_no, byref(c_dev_type), byref(c_id),
                                                      byref(c_serial), byref(c_address),
                                                      byref(c_connected))
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_getDeviceInfo") from exc
        ANC350v3LibError.check_error(return_code, "ANC_getDeviceInfo")

        return ANC350LibDeviceType(c_dev_type.value), c_id.value,\
               c_serial.value.decode(self._encoding), c_address.value.decode(self._encoding),\
               bool(c_connected.value)

    def connect(self, dev_no: int = 0) -> c_void_p:
        """Connect Device

        Initializes and connects the selected device.
        This has to be done before any access to control variables or measured data.

        Args:
            dev_no: Sequence number of the device. Must be smaller than the return value from the
                    last ``discover`` call (default: 0).

        Returns:
            device: Handle to the opened device; or None on error

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_dev_no = c_uint32(dev_no)
        c_dev_handle = c_void_p()

        try:
            return_code = self._dll.ANC_connect(c_dev_no, byref(c_dev_handle))
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_connect") from exc
        ANC350v3LibError.check_error(return_code, "ANC_connect")

        if not c_dev_handle:
            raise ANC350v3LibError("Received invalid handle from ANC_connect")

        return c_dev_handle

    def disconnect(self, dev_handle: c_void_p) -> None:
        """Disconnect Device

        Closes the connection to the device. The device handle becomes invalid.

        Args:
            dev_handle: Handle of the device to close

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        try:
            return_code = self._dll.ANC_disconnect(dev_handle)
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_disconnect") from exc
        ANC350v3LibError.check_error(return_code, "ANC_disconnect")

    def get_device_config(self, dev_handle: c_void_p) -> Tuple[bool, bool, bool, bool]:
        """Read Device Configuration

        Reads static device configuration data

        Args:
            dev_handle: Handle of the device to access

        Returns:
            A tuple containing which features of the device are enabled:
                0. sync: Ethernet enabled (True) or disabled (False)
                1. lockin: Low power loss measurement enabled (True) or disabled (False)
                2. duty: Duty cycle enabled (True) or disabled (False)
                3. app: Control by iOS app enabled (True) or disabled (False)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_features = c_uint32()

        try:
            return_code = self._dll.ANC_getDeviceConfig(dev_handle, byref(c_features))
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_getDeviceConfig") from exc
        ANC350v3LibError.check_error(return_code, "ANC_getDeviceConfig")

        features = c_features.value
        feat_sync = bool(0x1 & features)
        feat_lockin = bool(0x2 & features)
        feat_duty = bool(0x4 & features)
        feat_app = bool(0x8 & features)

        return feat_sync, feat_lockin, feat_duty, feat_app

    def get_axis_status(self, dev_handle: c_void_p, axis_no: int) \
            -> Tuple[bool, bool, bool, bool, bool, bool, bool]:
        """Read Axis Status

        Reads status information about an axis of the device.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)

        Returns:
            A tuple containing the axis status:
                0. connected: True, if the axis is connected to a sensor.
                1. enabled: True, if the axis voltage output is enabled.
                2. moving: True, if the axis is moving.
                3. target: True, if the target is reached in automatic positioning.
                4. eot_fwd: True, if end of travel detected in forward direction.
                5. eot_bwd: True, if end of travel detected in backward direction.
                6. error: True, if the axis' sensor is in error state.

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_connected = c_int32()
        c_enabled = c_int32()
        c_moving = c_int32()
        c_target = c_int32()
        c_eot_fwd = c_int32()
        c_eot_bwd = c_int32()
        c_error = c_int32()

        try:
            return_code = self._dll.ANC_getAxisStatus(dev_handle, c_axis_no,
                                                      byref(c_connected), byref(c_enabled),
                                                      byref(c_moving), byref(c_target),
                                                      byref(c_eot_fwd), byref(c_eot_bwd),
                                                      byref(c_error))
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_getAxisStatus") from exc
        ANC350v3LibError.check_error(return_code, "ANC_getAxisStatus")

        return bool(c_connected.value), bool(c_enabled.value), bool(c_moving.value), \
               bool(c_target.value), bool(c_eot_fwd.value), bool(c_eot_bwd.value), \
               bool(c_error.value)

    def set_axis_output(self, dev_handle: c_void_p, axis_no: int, enable: bool,
                        auto_disable: bool) -> None:
        """Enable Axis Output

        Enables or disables the voltage output of an axis.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)
            enable: True, to enable the voltage output. False, to disable it.
            auto_disable: True, if the voltage output is to be deactivated automatically when end of
                          travel is detected.

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_enable = c_int32(int(enable))
        c_auto_disable = c_int32(int(auto_disable))

        try:
            return_code = self._dll.ANC_setAxisOutput(dev_handle, c_axis_no, c_enable,
                                                      c_auto_disable)
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_setAxisOutput") from exc
        ANC350v3LibError.check_error(return_code, "ANC_setAxisOutput")

    def set_amplitude(self, dev_handle: c_void_p, axis_no: int, amplitude: float) -> None:
        """Set Amplitude

        Sets the amplitude parameter for an axis

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)
            amplitude: Amplitude in Volts [V] (internal resolution is 1mV)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_amplitude = c_double(amplitude)

        try:
            return_code = self._dll.ANC_setAmplitude(dev_handle, c_axis_no, c_amplitude)
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_setAmplitude") from exc
        ANC350v3LibError.check_error(return_code, "ANC_setAmplitude")

    def set_frequency(self, dev_handle: c_void_p, axis_no: int, frequency: float) -> None:
        """Set Frequency

        Sets the frequency parameter for an axis

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)
            frequency: Frequency in Hertz [Hz], internal resolution is 1 Hz (although DLL accepts
                       double-values)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_frequency = c_double(frequency)

        try:
            return_code = self._dll.ANC_setFrequency(dev_handle, c_axis_no, c_frequency)
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_setFrequency") from exc
        ANC350v3LibError.check_error(return_code, "ANC_setFrequency")

    def set_dc_voltage(self, dev_handle: c_void_p, axis_no: int, voltage: float) -> None:
        """Set DC Output Voltage

        Sets the DC level on the voltage output when no sawtooth based motion and no feedback loop
        is active.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)
            voltage: DC output voltage in Volts [V], internal resolution is 1 mV

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_voltage = c_double(voltage)

        try:
            return_code = self._dll.ANC_setDcVoltage(dev_handle, c_axis_no, c_voltage)
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_setDcVoltage") from exc
        ANC350v3LibError.check_error(return_code, "ANC_setDcVoltage")

    def get_amplitude(self, dev_handle: c_void_p, axis_no: int) -> float:
        """Read Back Amplitude

        Reads back the amplitude parameter of an axis.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)

        Returns:
            Amplitude in Volts [V]

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_amplitude = c_double()

        try:
            return_code = self._dll.ANC_getAmplitude(dev_handle, c_axis_no, byref(c_amplitude))
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_getAmplitude") from exc
        ANC350v3LibError.check_error(return_code, "ANC_getAmplitude")

        return c_amplitude.value

    def get_frequency(self, dev_handle: c_void_p, axis_no: int) -> float:
        """Read back Frequency

        Reads back the frequency parameter of an axis.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)

        Returns:
            Frequency in Hertz [Hz]

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_frequency = c_double()

        try:
            return_code = self._dll.ANC_getFrequency(dev_handle, c_axis_no, byref(c_frequency))
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_getFrequency") from exc
        ANC350v3LibError.check_error(return_code, "ANC_getFrequency")

        return c_frequency.value

    def start_single_step(self, dev_handle: c_void_p, axis_no: int, backward: bool) -> None:
        """Single Step

        Triggers a single step in desired direction.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)
            backward: Step direction forward (False) or backward (True)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_backward = c_int32(int(backward))

        try:
            return_code = self._dll.ANC_startSingleStep(dev_handle, c_axis_no, c_backward)
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_startSingleStep") from exc
        ANC350v3LibError.check_error(return_code, "ANC_startSingleStep")

    def start_continuous_move(self, dev_handle: c_void_p, axis_no: int, start: bool,
                              backward: bool) -> None:
        """Continuous Motion

        Starts or stops continous motion in forward or backward direction.
        Other kinds of motion are stopped.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)
            start: Starts (True) or stops (False) the motion
            backward: Step direction forward (False) or backward (True)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_start = c_int32(int(start))
        c_backward = c_int32(int(backward))

        try:
            return_code = self._dll.ANC_startContinousMove(dev_handle, c_axis_no, c_start,
                                                           c_backward)
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_startContinousMove") from exc
        ANC350v3LibError.check_error(return_code, "ANC_startContinousMove")

    def start_auto_move(self, dev_handle: c_void_p, axis_no: int, enable: bool,
                        relative: bool) -> None:
        """Set Automatic Motion

        Switches automatic moving (i.e. following the target position) on or off

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)
            enable: Enables (True) or disables (False) automatic motion
            relative: If the target position is to be interpreted absolute (False) or relative to
                      the current position (True)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_enable = c_int32(int(enable))
        c_relative = c_int32(int(relative))

        try:
            return_code = self._dll.ANC_startAutoMove(dev_handle, c_axis_no, c_enable,
                                                      c_relative)
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_startAutoMove") from exc
        ANC350v3LibError.check_error(return_code, "ANC_startAutoMove")

    def set_target_position(self, dev_handle: c_void_p, axis_no: int, target: float) -> None:
        """Set Target Position

        Sets the target position for automatic motion, see ``start_auto_move``.
        For linear type actuators the position unit is m, for goniometers and rotators it is degree.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)
            target: Target position in meters [m] or degrees [°]. Internal resolution is 1 nm or
                    1 µ°.

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_target = c_double(target)

        try:
            return_code = self._dll.ANC_setTargetPosition(dev_handle, c_axis_no, c_target)
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_setTargetPosition") from exc
        ANC350v3LibError.check_error(return_code, "ANC_setTargetPosition")

    def set_target_range(self, dev_handle: c_void_p, axis_no: int, target_range: float) -> None:
        """Set Target Range

        Defines the range around the target position where the target is considered to be reached.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)
            target_range: Target range in meters [m] or degrees [°]. Internal resolution is 1 nm or
                          1 µ°.

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_target_range = c_double(target_range)

        try:
            return_code = self._dll.ANC_setTargetRange(dev_handle, c_axis_no, c_target_range)
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_setTargetRange") from exc
        ANC350v3LibError.check_error(return_code, "ANC_setTargetRange")

    def get_position(self, dev_handle: c_void_p, axis_no: int) -> float:
        """Read Current Position

        Retrieves the current actuator position.
        For linear type actuators the position unit is m; for goniometers and rotators it is degree.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)

        Returns:
            Current position in meters [m] or degrees [°]

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_position = c_double()

        try:
            return_code = self._dll.ANC_getPosition(dev_handle, c_axis_no, byref(c_position))
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_getPosition") from exc
        ANC350v3LibError.check_error(return_code, "ANC_getPosition")

        return c_position.value

    def get_firmware_version(self, dev_handle: c_void_p) -> int:
        """Firmware version

        Retrieves the version of currently loaded firmware.

        Args:
            dev_handle: Handle of the device to access

        Returns:
            Version number

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_version = c_int32()

        try:
            return_code = self._dll.ANC_getFirmwareVersion(dev_handle, byref(c_version))
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_getFirmwareVersion") from exc
        ANC350v3LibError.check_error(return_code, "ANC_getFirmwareVersion")

        return c_version.value

    def configure_ext_trigger(self, dev_handle: c_void_p, axis_no: int,
                              mode: Union[ANC350LibExternalTriggerMode, int]) -> None:
        """Configure Trigger Input

        Enables the input trigger for steps.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)
            mode: Disable (0), quadrature (1) or trigger(2) for external triggering

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_mode = c_uint32(int(mode))

        try:
            return_code = self._dll.ANC_configureExtTrigger(dev_handle, c_axis_no, c_mode)
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_configureExtTrigger") from exc
        ANC350v3LibError.check_error(return_code, "ANC_configureExtTrigger")

    def configure_a_quad_b_in(self, dev_handle: c_void_p, axis_no: int, enable: bool,
                              resolution: float) -> None:
        """Configure A-Quad-B Input

        Enables and configures the A-Quad-B (quadrature) input for the target position.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)
            enable: Enable (True) or disable (False) A-Quad-B input
            resolution: A-Quad-B step width in meters [m]. Internal resolution is 1 nm.

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_enable = c_int32(enable)
        c_resolution = c_double(resolution)

        try:
            return_code = self._dll.ANC_configureAQuadBIn(dev_handle, c_axis_no, c_enable,
                                                          c_resolution)
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_configureAQuadBIn") from exc
        ANC350v3LibError.check_error(return_code, "ANC_configureAQuadBIn")

    def configure_a_quad_b_out(self, dev_handle: c_void_p, axis_no: int, enable: bool,
                               resolution: float, clock: float) -> None:
        """Configure A-Quad-B Output

        Enables and configures the A-Quad-B (quadrature) output of the current position.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)
            enable: Enable (True) or disable (False) A-Quad-B output
            resolution: A-Quad-B step width in meters [m]. Internal resolution is 1 nm.
            clock: Clock of the A-Quad-B output in seconds [s]. Allowed range is 40ns ... 1.3ms;
                   internal resolution is 20ns.

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_enable = c_int32(enable)
        c_resolution = c_double(resolution)
        c_clock = c_double(clock)

        try:
            return_code = self._dll.ANC_configureAQuadBOut(dev_handle, c_axis_no, c_enable,
                                                           c_resolution, c_clock)
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_configureAQuadBOut") from exc
        ANC350v3LibError.check_error(return_code, "ANC_configureAQuadBOut")

    def configure_rng_trigger_pol(self, dev_handle: c_void_p, axis_no: int,
                                  polarity: Union[ANC350LibTriggerPolarity, int]) -> None:
        """Configure Polarity of Range Trigger

        Configure lower position for range trigger.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)
            polarity: Polarity of trigger signal when position is between lower and upper Low(0) and
                      High(1)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_polarity = c_int32(int(polarity))

        try:
            return_code = self._dll.ANC_configureRngTriggerPol(dev_handle, c_axis_no,
                                                               c_polarity)
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_configureRngTriggerPol") from exc
        ANC350v3LibError.check_error(return_code, "ANC_configureRngTriggerPol")

    def configure_rng_trigger(self, dev_handle: c_void_p, axis_no: int, lower: int,
                              upper: int) -> None:
        """Configure Range Trigger

        Configure lower position for range trigger.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)
            lower: Lower position for range trigger in nanometers [nm]
            upper: Upper position for range trigger in nanometers [nm]

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_lower = c_uint32(lower)
        c_upper = c_uint32(upper)

        try:
            return_code = self._dll.ANC_configureRngTrigger(dev_handle, c_axis_no, c_lower,
                                                            c_upper)
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_configureRngTrigger") from exc
        ANC350v3LibError.check_error(return_code, "ANC_configureRngTrigger")

    def configure_rng_trigger_eps(self, dev_handle: c_void_p, axis_no: int, epsilon: int) -> None:
        """Configure Epsilon of Range Trigger

        Configure hysteresis for range trigger.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)
            epsilon: Hysteresis in nanometers per millidegree [nm/m°]

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_epsilon = c_uint32(epsilon)

        try:
            return_code = self._dll.ANC_configureRngTriggerEps(dev_handle, c_axis_no,
                                                               c_epsilon)
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_configureRngTriggerEps") from exc
        ANC350v3LibError.check_error(return_code, "ANC_configureRngTriggerEps")

    def configure_nsl_trigger(self, dev_handle: c_void_p, enable: bool) -> None:
        """Configure NSL Trigger

        Enables NSL input as trigger source.

        Args:
            dev_handle: Handle of the device to access
            enable: Disable (False) or enable (True)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_enable = c_int32(int(enable))

        try:
            return_code = self._dll.ANC_configureNslTrigger(dev_handle, c_enable)
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_configureNslTrigger") from exc
        ANC350v3LibError.check_error(return_code, "ANC_configureNslTrigger")

    def configure_nsl_trigger_axis(self, dev_handle: c_void_p, axis_no: int) -> None:
        """Configure NSL Trigger Axis

        Selects axis for NSL trigger.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)

        try:
            return_code = self._dll.ANC_configureNslTriggerAxis(dev_handle, c_axis_no)
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_configureNslTriggerAxis") from exc
        ANC350v3LibError.check_error(return_code, "ANC_configureNslTriggerAxis")

    def select_actuator(self, dev_handle: c_void_p, axis_no: int, actuator: int) -> None:
        """Select Actuator

        Selects the actuator to be used for the axis from actuator presets.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)
            actuator: Actuator selection (0..255)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_actuator = c_uint32(actuator)

        try:
            return_code = self._dll.ANC_selectActuator(dev_handle, c_axis_no, c_actuator)
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_selectActuator") from exc
        ANC350v3LibError.check_error(return_code, "ANC_selectActuator")

    def get_actuator_name(self, dev_handle: c_void_p, axis_no: int) -> str:
        """Get Actuator Name

        Get the name of the currently selected actuator

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)

        Returns:
            Name of the actuator

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_name = c_string(20)

        try:
            return_code = self._dll.ANC_getActuatorName(dev_handle, c_axis_no, byref(c_name))
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_getActuatorName") from exc
        ANC350v3LibError.check_error(return_code, "ANC_getActuatorName")

        return c_name.value.decode(self._encoding)

    def get_actuator_type(self, dev_handle: c_void_p, axis_no: int) -> ANC350LibActuatorType:
        """Get Actuator Type

        Get the type of the currently selected actuator

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)

        Returns:
            Type of the actuator

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_type = c_int32()

        try:
            return_code = self._dll.ANC_getActuatorType(dev_handle, c_axis_no, byref(c_type))
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_getActuatorType") from exc
        ANC350v3LibError.check_error(return_code, "ANC_getActuatorType")

        return ANC350LibActuatorType(c_type.value)

    def measure_capacitance(self, dev_handle: c_void_p, axis_no: int) -> float:
        """Measure Motor Capacitance

        Performs a measurement of the capacitance of the piezo motor and returns the result. If no
        motor is connected, the result will be 0.
        The function doesn't return before the measurement is complete; this will take a few seconds
        of time.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)

        Returns:
            Capacitance in Farad [F]

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_cap = c_double()

        try:
            return_code = self._dll.ANC_measureCapacitance(dev_handle, c_axis_no, byref(c_cap))
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_measureCapacitance") from exc
        ANC350v3LibError.check_error(return_code, "ANC_measureCapacitance")

        return c_cap.value

    def save_params(self, dev_handle: c_void_p) -> None:
        """Save Parameters

        Saves parameters to persistent flash memory in the device. They will be present as defaults
        after the next power-on.
        The following parameters are affected:
        * amplitude (see ``set_amplitude``)
        * frequency (see ``set_frequency``)
        * target range (see ``set_target_range``)
        * target ground (see ``set_target_ground``)
        * actuator selection (see ``select_actuator``)
        * trigger and quadrature settings

        Args:
            dev_handle: Handle of the device to access

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        try:
            return_code = self._dll.ANC_saveParams(dev_handle)
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_saveParams") from exc
        ANC350v3LibError.check_error(return_code, "ANC_saveParams")

    def reset_position(self, dev_handle: c_void_p, axis_no: int) -> None:
        """Reset Position

        Sets the current (relative) position of an axis to Zero.
        Only applicable for NUM and FPS devices.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)

        try:
            return_code = self._dll.ANC_resetPosition(dev_handle, c_axis_no)
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_resetPosition") from exc
        ANC350v3LibError.check_error(return_code, "ANC_resetPosition")

    def move_reference(self, dev_handle: c_void_p, axis_no: int) -> None:
        """Reset Reference

        Starts an approach to the reference position. A running motion command is aborted; automatic
        moving (see ``start_auto_move``) is switched on. Requires a valid reference position.
        Only applicable for NUM devices.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)

        try:
            return_code = self._dll.ANC_moveReference(dev_handle, c_axis_no)
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_moveReference") from exc
        ANC350v3LibError.check_error(return_code, "ANC_moveReference")

    def get_ref_position(self, dev_handle: c_void_p, axis_no: int) -> Tuple[float, bool]:
        """Read Reference Position

        Retrieves the current reference position.
        For linear type actuators the position unit is meter [m]; for goniometers and rotators it is
        degree [°].
        Only applicable for NUM devices.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)

        Returns:
            Tuple containing the reference position:
                0. position: Current reference position in meters [m] or degrees [°].
                1. valid: True, if the reference position is valid.

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_position = c_double()
        c_valid = c_int32()

        try:
            return_code = self._dll.ANC_getRefPosition(dev_handle, c_axis_no,
                                                       byref(c_position), byref(c_valid))
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_getRefPosition") from exc
        ANC350v3LibError.check_error(return_code, "ANC_getRefPosition")

        # TODO: Could we only return position if valid is True and return None, if valid is False?
        # Then, one return value would be enough
        return c_position.value, bool(c_valid.value)

    def configure_duty_cycle(self, dev_handle: c_void_p, axis_no: int, period: float,
                             off_time: float) -> None:
        """Configure Duty Cycle Parameters

        Enables and configures the sensor's duty cycle for all axes.
        Requires the duty cycle feature to be installed.
        Only applicable for NUM devices.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)
            period: Duty cycle period in seconds [s]
            off_time: Duty cycle off time in seconds [s]

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_period = c_double(period)
        c_off_time = c_double(off_time)

        try:
            return_code = self._dll.ANC_configureDutyCycle(dev_handle, c_axis_no, c_period,
                                                           c_off_time)
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_configureDutyCycle") from exc
        ANC350v3LibError.check_error(return_code, "ANC_configureDutyCycle")

    def enable_sensor(self, dev_handle: c_void_p, enable: bool) -> None:
        """Switch Sensor Power

        Switches the sensor power for all axes on or off.
        Only applicable for NUM devices.

        Args:
            dev_handle: Handle of the device to access
            enable: Enable (True) or disable (False) the sensor

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_enable = c_int32(int(enable))

        try:
            return_code = self._dll.ANC_enableSensor(dev_handle, c_enable)
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_enableSensor") from exc
        ANC350v3LibError.check_error(return_code, "ANC_enableSensor")

    def enable_ref_auto_update(self, dev_handle: c_void_p, axis_no: int, enable: bool) -> None:
        """Enable Reference Auto Update

        Enables or disables the reference auto update for an axis. When enabled, every time the
        reference marking is hit, the reference position will be updated. When disabled, the
        reference marking will be considered only the first time, later hits will be ignored.
        Only applicable for NUM devices.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)
            enable: Enable (True) or disable (False) the feature

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_enable = c_int32(int(enable))

        try:
            return_code = self._dll.ANC_enableRefAutoUpdate(dev_handle, c_axis_no, c_enable)
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_enableRefAutoUpdate") from exc
        ANC350v3LibError.check_error(return_code, "ANC_enableRefAutoUpdate")

    def enable_ref_auto_reset(self, dev_handle: c_void_p, axis_no: int, enable: bool) -> None:
        """Enable Position Auto Reset

        Enables or disables the position auto reset for an axis. When enabled, every time the
        reference marking is hit, the position will be set to zero. When disabled, the reference
        marking will be ignored.
        Only applicable for NUM devices.

        Args:
            dev_handle: Handle of the device to access
            axis_no: Axis number (0..2)
            enable: Enable (True) or disable (False) the feature

        Raises:
            ANC350LibError is raised, if the function call fails
        """
        c_axis_no = c_uint32(axis_no)
        c_enable = c_int32(int(enable))

        try:
            return_code = self._dll.ANC_enableRefAutoReset(dev_handle, c_axis_no, c_enable)
        except Exception as exc:
            raise ANC350v3LibError("Unexpected error in ANC_enableRefAutoReset") from exc
        ANC350v3LibError.check_error(return_code, "ANC_enableRefAutoReset")

    # TODO: Function is part of DLL, but not documented
    # def enable_trace(self, dev_handle: c_void_p, ...):
    #     try:
    #         return_code = self._dll.ANC_enableTrace(dev_handle, ...)
    #     except Exception as exc:
    #         raise ANC350LibError("Unexpected error in ANC_enableTrace") from exc
    #     ANC350LibError.check_error(return_code, "ANC_enableTrace")
