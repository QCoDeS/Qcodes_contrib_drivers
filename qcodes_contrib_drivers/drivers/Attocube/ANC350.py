from typing import Any, Callable, Dict, Optional, Union

import qcodes.utils.validators as vals
from qcodes.instrument.base import Instrument
from qcodes.instrument.channel import InstrumentChannel, ChannelList

from .ANC350Lib import ANC350LibActuatorType, ANC350v3Lib, ANC350v4Lib


class Anc350Axis(InstrumentChannel):
    """
    Representation of an axis of the ANC350

    The Attocube ANC350 has 3 axis, one for every direction.

    Args:
        parent: the Instrument that the channel is attached to
        name: the name of the axis itself
        axis: the index of the axis (0..2)

    Attributes:
        position: Get the current position on a single axis
        frequency: Set the frequency of the output signal. Depending on positioner type and usage of other axes one can
            adjust the frequency from 1Hz up to 5kHz (only on one axis at one time is a frequency above 2kHz allowed)
        amplitude: Value for the drive voltage of the piezo drive. Bychanging this value, the step size of the
            positioner can be varied. Value for the drive voltage of the piezo drive. Bychanging this value, the step
            size of the positioner can be varied.
        status:
        voltage: Sets the DC level on the voltage output when no sawtooth based motion and no feedback loop
            is active.
        target_position: Sets the target position for automatic motion (start_auto_move). For linear type actuators the
            position unit is m, for goniometers and rotators it is degree.
        target_range: Defines the range around the target position where the target is considered to be reached.
        actuator: Selects the actuator to be used for the axis from actuator presets.
        actuator_name: Get the name of the currently selected actuator
        capacitance: Performs a measurement of the capacitance of the piezo motor and returns the result. If no
            motor is connected, the result will be 0.
            The function doesn't return before the measurement is complete; this will take a few seconds of time.
    """

    def __init__(self, parent: "ANC350", name: str, axis: int):
        super().__init__(parent, name)

        self._axis = axis

        self.add_parameter("position",
                           label="Position",
                           get_cmd=self._get_position,
                           unit="mm or m°")

        self.add_parameter("frequency",
                           label="Frequency",
                           get_cmd=self._get_frequency,
                           set_cmd=self._set_frequency,
                           vals=vals.Ints(1, 5000),
                           unit="Hz")

        self.add_parameter("amplitude",
                           label="Amplitude",
                           get_cmd=self._get_amplitude,
                           set_cmd=self._set_amplitude,
                           vals=vals.Numbers(0, 70),
                           unit="V")

        self.add_parameter("status",
                           label="Status",
                           get_cmd=self._get_status)

        self.add_parameter("target_position",
                           label="Target Position",
                           get_cmd=None,
                           set_cmd=self._set_target_position,
                           vals=vals.Numbers(),
                           unit="mm or m°")

        self.add_parameter("target_range",
                           label="Target Range",
                           get_cmd=None,
                           set_cmd=self._set_target_range,
                           vals=vals.Numbers(),
                           unit="mm or m°")

        self.add_parameter("actuator",
                           label="Actuator",
                           get_cmd=None,
                           set_cmd=self._set_actuator,
                           vals=vals.Ints(0, 255))

        self.add_parameter("actuator_type",
                           label="Actuator Type",
                           get_cmd=self._get_actuator_type)

        self.add_parameter("actuator_name",
                           label="Actuator Name",
                           get_cmd=self._get_actuator_name)

        self.add_parameter("capacitance",
                           label="Capacitance",
                           get_cmd=self._get_capacitance,
                           unit="nF")

        if self._parent._version_no >= 4:
            voltage_get: Optional[Callable] = self._get_voltage
        else:
            voltage_get = None

        self.add_parameter("voltage",
                           label="Voltage",
                           get_cmd=voltage_get,
                           set_cmd=self._set_voltage,
                           vals=vals.Numbers(0, 70),
                           unit="V")  # Internal resolution: mV (0.001)

        self.add_parameter("output",
                           label="Output",
                           val_mapping={False: 0,
                                        True: 1,
                                        "off": 0,
                                        "on": 1,
                                        "auto": 2},
                           get_cmd=self._get_output,
                           set_cmd=self._set_output)

        # Set actual unit (either mm or m°) to positional parameters
        self._update_position_unit()

    # Version 3
    # ---------
    def single_step(self, backward: Optional[Union[bool, str, int]] = None) -> None:
        """
        Triggers a single step in desired direction.

        Args:
            backward: Step direction forward (False) or backward (True). Beside True/False, you can
                      set the direction to "forward"/"backward" or +1/-1 (default: forward or False)
        """
        backward = self._map_direction_parameter(backward)

        self._parent._lib.start_single_step(self._parent._device_handle, self._axis, backward)

    def multiple_steps(self, steps: int) -> None:
        """
        Performs multiple steps. The direction depends on the sign (+: forward, -: backward)

        Args:
            steps: Number of steps to move. The sign indicates the moving direction (+: forward,
                   -: backward)
        """
        backward = (steps < 0)
        
        for i in range(abs(steps)):
            self.single_step(backward)

    def start_continuous_move(self, backward: Optional[Union[bool, str, int]] = None) -> None:
        """
        Starts continuous motion in forward or backward direction.
        Other kinds of motion are stopped.

        Args:
            backward: Step direction forward (False) or backward (True). Beside True/False, you can
                      set the direction to "forward"/"backward" or +1/-1 (default: forward or False)
        """
        backward = self._map_direction_parameter(backward)

        self._parent._lib.start_continuous_move(self._parent._device_handle, self._axis, True,
                                                backward)

    def stop_continuous_move(self) -> None:
        """Stops continuous motion in forward or backward direction."""
        self._parent._lib.start_continuous_move(self._parent._device_handle, self._axis, False,
                                                False)

    _direction_mapping: Dict[Any, bool] = {
        "forward": False,
        "backward": True,
        +1: False,
        -1: True
    }

    @classmethod
    def _map_direction_parameter(cls, backward: Optional[Union[bool, str, int]]) -> bool:
        if backward is None:
            return False
        if backward in [False, True]:
            return bool(backward)

        if backward in cls._direction_mapping:
            return cls._direction_mapping[backward]

        raise ValueError(f"Unexpected value for argument `backward`. Allowed values are: "
                         f"{[None, False, True, *cls._direction_mapping.keys()]}")

    _relative_mapping: Dict[Any, bool] = {
        "absolute": True,
        "relative": False
    }

    def enable_auto_move(self, relative: Optional[Union[bool, str]] = None) -> None:
        """
        Enables automatic moving

        Args:
            relative: If the target position is to be interpreted absolute (False) or relative to
                      the current position (True).
        """
        relative = self._map_relative_parameter(relative)

        self._parent._lib.start_auto_move(self._parent._device_handle, self._axis, True, relative)

    def disable_auto_move(self) -> None:
        """Disables automatic moving"""
        self._parent._lib.start_auto_move(self._parent._device_handle, self._axis, False, False)

    @classmethod
    def _map_relative_parameter(cls, relative: Optional[Union[bool, str]]) -> bool:
        if relative is None:
            return False
        if relative in [False, True]:
            return bool(relative)

        if relative in cls._relative_mapping:
            return cls._relative_mapping[relative]
        
        allowed_values = ", ".join(cls._relative_mapping.keys())
        raise ValueError(f"Unexpected value for argument `relative`. Allowed values are: None, "
                         f"False, True, {allowed_values}")

    def _get_position(self) -> float:
        """
        Get the current position of this axis

        Returns:
            Current position in millimeters [mm] (linear type actuators) or millidegrees [m°]
            (goniometers and rotators)
        """
        # Conversion from meters (degrees) to millimeters (millidegrees) because the wrapper works
        # with meters (degrees)
        return self._parent._lib.get_position(self._parent._device_handle, self._axis) * 1e3

    def _set_position(self, position: float) -> None:
        """(EXPERIMENTAL FUNCTION)
        The axis moves to the given position with the target range that is set before.

        Args:
            position: The position the axis moves to
        """
        self._set_target_position(position)
        self._set_output(2)  # 2 = "auto"

    def _get_frequency(self) -> float:
        """
        Returns the frequency parameter of this axis.

        Returns:
            Frequency in Hertz [Hz], internal resolution is 1 Hz
        """
        return self._parent._lib.get_frequency(self._parent._device_handle, self._axis)

    def _set_frequency(self, frequency: float) -> None:
        """
        Sets the frequency parameter for this axis

        Args:
            frequency (float): Frequency in Hertz [Hz], internal resolution is 1 Hz
        """
        frequency = int(round(frequency))

        self._parent._lib.set_frequency(self._parent._device_handle, self._axis, frequency)

    def _get_amplitude(self) -> float:
        """
        Returns the amplitude parameter of this axis.

        Returns:
            Amplitude in Volts [V]
        """
        return self._parent._lib.get_amplitude(self._parent._device_handle, self._axis)

    def _set_amplitude(self, amplitude: float) -> None:
        """
        Sets the amplitude parameter for an axis

        Args:
            amplitude: Amplitude in Volts [V] (internal resolution is 1mV)
        """
        self._parent._lib.set_amplitude(self._parent._device_handle, self._axis, amplitude)

    def _get_status(self) -> Dict[str, bool]:
        """
        Reads status information about an axis

        Returns:
            A Dictionary containing the information about an axis:
                connected: True, if the axis is connected to a sensor.
                enabled: True, if the axis voltage output is enabled.
                moving: True, if the axis is moving.
                target: True, if the target is reached in automatic positioning.
                eot_fwd: True, if end of travel detected in forward direction.
                eot_bwd: True, if end of travel detected in backward direction.
                error: True, if the axis' sensor is in error state.
        """
        keys = ("connected", "enabled", "moving", "target", "eot_fwd", "eot_bwf", "error")
        status = self._parent._lib.get_axis_status(self._parent._device_handle, self._axis)

        return dict(zip(keys, status))

    def _set_voltage(self, voltage: float) -> None:
        """
        Sets the DC level on the voltage output when no sawtooth based motion and no feedback loop
        is active.

        Args:
            voltage: DC output voltage in Volts [V], internal resolution is 1 mV
        """
        self._parent._lib.set_dc_voltage(self._parent._device_handle, self._axis, voltage)

    def _set_target_position(self, target: float) -> None:
        """
        Sets the target position for automatic motion.
        For linear type actuators the position unit is mm, for goniometers and rotators it is m°.

        Args:
            target: Target position in millimeters [mm] or millidegrees [m°]. Internal resolution is
                    1 nm or 1 µ°.
        """
        # Conversion from meters (degrees) to millimeters (millidegrees) because the wrapper works
        # with meters (degrees)
        self._parent._lib.set_target_position(self._parent._device_handle, self._axis,
                                              target * 1e-3)

    def _set_target_range(self, target_range: float) -> None:
        """
        Sets the range around the target position where the target is considered to be reached.
        For linear type actuators the position unit is mm, for goniometers and rotators it is m°.

        Args:
             target_range: Target range in millimeters [mm] or millidegrees [m°]. Internal
                           resolution is 1 nm or 1 µ°.
        """
        # Conversion from meters (degrees) to millimeters (millidegrees) because the wrapper works
        # with meters (degrees)
        self._parent._lib.set_target_range(self._parent._device_handle, self._axis,
                                           target_range * 1e-3)

    def _set_actuator(self, actuator: int) -> None:
        """
        Selects the actuator to be used for the axis from actuator presets. And changes the unit of the position
        parameters if necessary.

        Args:
            actuator: Actuator selection (0..255)
        """
        old_actuator_type = self._get_actuator_type()
        self._parent._lib.select_actuator(self._parent._device_handle, self._axis, actuator)

        self._update_position_unit(old_actuator_type)

    def _update_position_unit(self, old_actuator_type: Optional[ANC350LibActuatorType] = None) \
            -> None:
        """Checks the current actuator type and sets the corresponding unit for position-parameters.

        Args:
            old_actuator_type: Actuator type before changing it. This parameter is used to determine,
                               if the actuator type has changed. If not, there is no need to update
                               the unit. This parameter is optional. If it is None, the unit is
                               always updated.
        """
        actuator_type = self._get_actuator_type()

        if actuator_type != old_actuator_type:
            if actuator_type == ANC350LibActuatorType.Linear:
                unit = "mm"
            else:
                unit = "m°"

            self.position.unit = unit
            self.target_position.unit = unit
            self.target_range.unit = unit

    def _get_actuator_type(self) -> ANC350LibActuatorType:
        """
        Get the type of the currently selected actuator

        Returns:
            Type of the actuator
        """
        return self._parent._lib.get_actuator_type(self._parent._device_handle, self._axis)

    def _get_actuator_name(self) -> str:
        """
        Returns the name of the currently selected actuator

        Returns:
            Name of the actuator
        """
        return self._parent._lib.get_actuator_name(self._parent._device_handle, self._axis)

    def _get_capacitance(self) -> float:
        """
        Returns the motor capacitance
        Performs a measurement of the capacitance of the piezo motor and returns the result. If no
        motor is connected, the result will be 0.
        The function doesn't return before the measurement is complete; this will take a few seconds
        of time.

        Returns:
            Capacitance in Farad [nF]
        """
        # 1e9 as factor for the conversion from F to nF
        return self._parent._lib.measure_capacitance(self._parent._device_handle, self._axis) * 1e9

    def _set_output(self, enable: int) -> None:
        """
        Enables or disables the voltage output of this axis.

        Args:
            enable: Enable/disable voltage output:
                    - 0: disable
                    - 1: enable
                    - 2: enable until end of travel is detected
        """
        auto_off = False

        if enable == 0:
            enable = False
        elif enable == 1 or enable == 2:
            if enable == 2:  # enable, but automatically disable when end of travel is detected
                auto_off = True
            enable = True
        else:
            raise ValueError("enable")

        self._parent._lib.set_axis_output(self._parent._device_handle, self._axis, enable, auto_off)

    def _get_output(self) -> int:
        """Reads the voltage output status.

        Returns:
            1, if the axis voltage output is enabled. 0, if it is disabled.
        """
        return 1 if self._get_status()["enabled"] else 0

    # Version 4
    # ---------
    def _get_voltage(self) -> float:
        """
        Reads back the current DC level (only supported by library with version 4)

        Returns:
            DC output voltage in Volts [V]
        """
        return self._parent._lib.get_dc_voltage(self._parent._device_handle, self._axis)


class ANC350(Instrument):
    """
    Qcodes driver for the ANC350

    Args:
        name: the name of the instrument itself
        library: library that fits to the version of the device and provides the appropriate dll
                 wrappers
        inst_no: Sequence number of the device to connect to (default: 0, the first device found)
    """

    def __init__(self, name: str, library: ANC350v3Lib, inst_no: int = 0):
        super().__init__(name)

        if isinstance(library, ANC350v4Lib):
            self._version_no = 4
        elif isinstance(library, ANC350v3Lib):
            self._version_no = 3
        else:
            raise NotImplementedError("Only version 3 and 4 of ANC350's driver-DLL are currently "
                                      "supported")

        self._lib = library
        self._device_no = inst_no
        self._device_handle = self._lib.connect(inst_no)

        axischannels = ChannelList(self, "Anc350Axis", Anc350Axis)
        for nr, axis in enumerate(['x', 'y', 'z']):
            axis_name = f"{axis}_axis"
            axischannel = Anc350Axis(parent=self, name=axis_name, axis=nr)
            axischannels.append(axischannel)
            self.add_submodule(axis_name, axischannel)
        axischannels.lock()
        self.add_submodule("axis_channels", axischannels)

    def close(self) -> None:
        """
        Closes the connection to the device. The device handle becomes invalid.
        """
        self._lib.disconnect(self._device_handle)
        super().close()

    def save_params(self) -> None:
        """
        Saves parameters to persistent flash memory in the device. They will be present as defaults
        after the next power-on.
        """
        self._lib.save_params(self._device_handle)

    def get_idn(self) -> Dict[str, Optional[str]]:
        """
        Returns a dictionary with information about the device

        Returns:
            A dictionary containing vendor, model, serial number and firmware version
        """
        serial = self._lib.get_device_info(self._device_no)[2]

        return {"vendor": "Attocube", "model": "ANC350",
                "serial": serial, "firmware": str(self._version_no)}
