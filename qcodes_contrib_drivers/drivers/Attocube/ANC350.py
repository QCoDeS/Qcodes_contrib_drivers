from typing import Tuple, Dict, Any

from qcodes import Instrument
from qcodes.instrument.channel import InstrumentChannel, ChannelList
from qcodes.utils.validators import Numbers

from qcodes_contrib_drivers.drivers.Attocube.ANC350Lib import v3, ANC350LibDeviceType


class Anc350Axis(InstrumentChannel):
    """
    Representation of an axis of the ANC350

    The Attocube ANC350 has 3 axis, one for every direction.

    Args:
        parent: the Instrument that the channel is attached to
        name: the name of the axis itself
        axis: the index of the axis (1..3)

    Attributes:
        position: Get the current postion on a single axis
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

        if parent._version == 3 or parent._version == 4:
            # Postion
            self._get_position = self._get_position_v3
            self._set_position = self._set_position_v3
            # Frequency
            self._get_frequency = self._get_frequency_v3
            self._set_frequency = self._set_frequency_v3
            # Amplitude
            self._get_amplitude = self._get_amplitude_v3
            self._set_amplitude = self._set_amplitude_v3
            # Status
            self._get_status = self._get_status_v3
            self._set_status = False
            # Voltage
            self._set_voltage = self._set_voltage_v3
            self._get_voltage = False
            # Target_position
            self._set_target_position = self._set_target_position_v3
            self._get_target_position = False
            # Target_range
            self._set_target_range = self._set_target_range_v3
            self._get_target_range = False
            # Actutaor
            self._set_actuator = self._set_actuator_v3
            self._get_actuator = False
            # Actuator_name
            self._set_actuator_name = self._set_actuator_name_v3
            self._get_actuator_name = False
            # Capacitance
            self._set_capacitance = False
            self._get_capacitance = self._get_capacitance_v3

            if parent._version == 4:
                # Voltage
                self._get_voltage = self._get_dc_voltage_v4

        elif parent._version == 2:
            # TODO: add support for version 2
            raise NotImplementedError
        else:
            # TODO: Throw a fitting Exception
            pass

        self.add_parameter("position",
                           label="Position",
                           get_cmd=self._get_position,
                           set_cmd=self._set_position,
                           )

        self.add_parameter("frequency",
                           label="Frequency",
                           get_cmd=self._get_frequency,
                           set_cmd=self._set_frequency,
                           unit="Hz")

        self.add_parameter("amplitude",
                           label="Amplitude",
                           get_cmd=self._get_amplitude,
                           set_cmd=self._set_amplitude,
                           vals=Numbers(0, 70),
                           unit="V")

        self.add_parameter("status",
                           label="",
                           get_cmd=self._get_status,
                           set_cmd=self._set_status,
                           )

        self.add_parameter("voltage",
                           label="",
                           get_cmd=self._get_voltage,
                           set_cmd=self._set_voltage,
                           vals=Numbers(0, 70),
                           unit="V",
                           )

        # TODO: possible to add two differtent units? -> linear actuatorsm, goniometers and rotators degree.
        self.add_parameter("target_postion",
                           label="",
                           get_cmd=False,
                           set_cmd=self._set_target_position,
                           )

        # TODO: possible to add two differtent units? -> linear actuatorsm, goniometers and rotators degree.
        self.add_parameter("target_range",
                           label="",
                           get_cmd=self._get_target_range,
                           set_cmd=self._set_target_range,
                           )

        self.add_parameter("actuator",
                           label="",
                           get_cmd=False,
                           set_cmd=self,
                           vals=Numbers(0, 255),
                           )

        self.add_parameter("actuator_name",
                           label="",
                           get_cmd=self._get_actuator_name,
                           set_cmd=self._set_actuator_name)

        # TODO: parameter actuator type?

        self.add_parameter("capacitance",
                           label="",
                           get_cmd=self._get_capacitance,
                           set_cmd=False,
                           unit="F")

    # Version 3
    # ---------
    def set_output_v3(self, enable: bool, auto_disable: bool) -> None:
        """
        Enables or disables the voltage output of an axis.

        Args:
            enable: True, to enable the voltage output. False, to disable it.
            auto_disable: True, if the voltage output is to be deactivated automatically when end of
                          travel is detected.
        """
        self._parent.lib.set_axis_output(dev_handle=self._parent.device_handle, axis_no=self._axis, enable=enable,
                                         auto_disable=auto_disable)

    def start_single_step_v3(self, backward) -> None:
        """
        Triggers a single step in desired direction.

        Args:
            backward: Step direction forward (False) or backward (True)
        """
        self._parent.lib.start_single_step(dev_handle=self._parent.device_handle, axis_no=self._axis, backward=backward)

    def start_continuous_move_v3(self, start, backward) -> None:
        """
        Starts or stops continous motion in forward or backward direction.
        Other kinds of motion are stopped.

        Args:
            start: Starts (True) or stops (False) the motion
            backward: Step direction forward (False) or backward (True)
        """
        self._parent.lib.start_continuous_move(dev_handle=self._parent.device_handle, axis_no=self._axis, start=start,
                                               backward=backward)

    def start_auto_move_v3(self, enable, relative) -> None:
        """
        Switches automatic moving (i.e. following the target position) on or off

        Args:
            enable: Enables (True) or disables (False) automatic motion
            relative: If the target position is to be interpreted absolute (False) or relative to
                      the current position (True)
        """
        self._parent.lib.start_auto_move(dev_handle=self._parent.device_handle, axis_no=self._axis, enable=enable,
                                         relative=relative)

    def _get_position_v3(self) -> float:
        """
        Get the current position of this axis


        Returns:
            Current position in meters [m] (linear type actuators) or degrees [°] (goniometers and rotators)
        """
        return self._parent.lib.get_position(dev_handle=self._parent.device_handle, axis_no=self._axis)

    def _set_position_v3(self, poisition: float) -> None:
        # TODO: is it needed to change the target range to a default?
        # TODO: better block the setter and calls while moving
        self._set_target_position_v3(poisition)
        self.start_auto_move_v3(True, False)

    def _get_frequency_v3(self) -> float:
        """
        Returns the frequency parameter of this axis.

        Returns:
            Frequency in Hertz [Hz]
        """
        return self._parent.lib.get_frequency(dev_handle=self._parent.device_handle, axis_no=self._axis)

    def _set_frequency_v3(self, frequency: float) -> None:
        """
        Sets the frequency parameter for this axis

        Args:
            frequency: Frequency in Hertz [Hz], internal resolution is 1 Hz
        """
        self._parent.lib.set_frequency(dev_handle=self._parent.device_handle, axis_no=self._axis, frequency=frequency)

    def _get_amplitude_v3(self) -> float:
        """
        Returns the amplitude parameter of this axis.

        Returns:
            Amplitude in Volts [V]
        """
        return self._parent.lib.get_amplitude(dev_handle=self._parent.device_handle, axis_no=self._axis)

    def _set_amplitude_v3(self, amplitude: float) -> None:
        """
        Sets the amplitude parameter for an axis

        Args:
            amplitude: Amplitude in Volts [V] (internal resolution is 1mV)
        """
        self._parent.lib.set_amplitude(dev_handle=self._parent.device_handle, axis_no=self._axis, amplitude=amplitude)

    def _get_status_v3(self) -> Dict[str, bool]:
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
        names = ("connected", "enabled", "moving", "target", "eot_fwd", "eot_bwf", "error")
        status_list = self._parent.lib.get_axis_status(dev_handle=self._parent.device_handle, axis_no=self._axis)
        status_dict = {}

        for name, status in zip(names, status_list):
            status_dict[name] = status

        return status_dict

    def _set_voltage_v3(self, voltage: float) -> None:
        """
        Sets the DC level on the voltage output when no sawtooth based motion and no feedback loop
        is active.

        Args:
            voltage: DC output voltage in Volts [V], internal resolution is 1 mV
        """
        self._parent.lib.set_dc_voltage(dev_handle=self._parent.device_handle, axis_no=self._axis, voltage=voltage)

    def _set_target_position_v3(self, target: float) -> None:
        """
        Sets the target position for automatic motion, see ``start_auto_move``.
        For linear type actuators the position unit is m, for goniometers and rotators it is degree.

        Args:
            target: Target position in meters [m] or degrees [°]. Internal resolution is 1 nm or
                    1 µ°.
        """
        self._parent.lib.set_target_position(dev_handle=self._parent.device_handle, axis_no=self._axis, target=target)

    def _set_target_range_v3(self, target_range: float) -> None:
        """
        Sets the range around the target position where the target is considered to be reached.
        For linear type actuators the position unit is m, for goniometers and rotators it is degree.

        Args:
             target_range: Target range in meters [m] or degrees [°]. Internal resolution is 1 nm or
                          1 µ°.
        """
        self._parent.lib.set_target_range(dev_handle=self._parent.device_handle, axis_no=self._axis,
                                          target=target_range)

    # TODO: add missing explaining for the actuator
    def _set_actuator_v3(self, actuator: int) -> None:
        self._parent.lib.select_actuator(dev_handle=self._parent.device_handle, axis_no=self._axis, actuator=actuator)

    def _get_actuator_name_v3(self) -> str:
        """
        Returns the name of the currently selected actuator

        Returns:
            Name of the actuator
        """
        return self._parent.lib.get_actuator_name(dev_handle=self._parent.device_handle, axis_no=self._axis)

    def _get_capacitance_v3(self) -> float:
        return self._parent.lib.measure_capacitance(dev_handle=self._parent.device_handle, axis_no=self._axis)

    # Version 4
    # ---------
    def _get_dc_voltage_v4(self) -> float:
        """
        Reads back the current DC level.

        Returns:
            DC output voltage in Volts [V]
        """
        return self._parent.lib.get_dc_voltage(dev_handle=self._parent.device_handle, axis_no=self._axis)


class ANC350(Instrument):
    """
    Qcodes driver for the ANC350

    Args:
        name: the name of the instrument itself
        inst_num: Sequence number of the device to connect to
        search_usb: True (default) to search for USB devices; False otherwise
        search_tcp: True (default) to search for TCP/IP devices; False otherwise
        library: library that fits to the version of the device and provides the appropriate dll wrappers

    Attributes:
        device_info: Returns available information about a device as a tuple.
    """

    def __init__(self, library, name: str, version: int = 3, inst_num: int = 0, search_usb: bool = True,
                 search_tcp: bool = True):
        super().__init__(name)

        self.lib = library

        self._dev_no = inst_num
        self._version = version

        if self.lib.discover(search_usb=search_usb, search_tcp=search_tcp) < inst_num:
            raise RuntimeError("No matching device found for this number")
        else:
            self.device_handle = self.lib.connect(inst_num)

        # TODO: is this snapshotable or should it be?
        axischannels = ChannelList(self, "Anc350Axis", Anc350Axis)
        for nr, axis in enumerate(['x', 'y', 'z'], 1):
            axis_name = "{}-axis".format(axis)
            axischannel = Anc350Axis(parent=self, name=axis_name, axis=nr)
            axischannels.append(axischannel)
            self.add_submodule(name, axischannel)
        axischannels.lock()
        self.add_submodule("axis_channles", axischannels)

        self.add_parameter("device_info",
                           label="",
                           get_cmd=self._get_device_info,
                           set_cmd=False)

    def save_params(self) -> None:
        """
        Saves parameters to persistent flash memory in the device. They will be present as defaults after the next power-on.
        """
        self.lib.save_params(dev_handle=self.device_handle)

    def disconnect(self) -> None:
        """
        Closes the connection to the device. The device handle becomes invalid.
        """
        self.lib.disconnect(dev_handle=self.device_handle)
        del self.device_handle

    def _get_device_info(self) -> Tuple[ANC350LibDeviceType, int, str, str, bool]:
        return self.lib.get_device_info(self._dev_no)
