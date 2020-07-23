from typing import Tuple, Dict, Any

from qcodes import Instrument, Parameter
from qcodes.instrument.channel import InstrumentChannel, ChannelList
from qcodes.instrument.parameter import ParamRawDataType
from qcodes.utils.validators import Numbers
import qcodes.utils.validators as vals

from qcodes_contrib_drivers.drivers.Attocube.ANC350Lib import ANC350LibActuatorType, ANC350v3Lib, ANC350v4Lib


class ANC350OutputParameter(Parameter):
    def __init__(self, axis: "Anc350Axis" = None, **kwargs):
        super().__init__(**kwargs)
        if axis is not None:
            if isinstance(axis, Anc350Axis):
                self._axis = axis
            else:
                raise TypeError("Given Type is not fitting")

    def set_raw(self, value: ParamRawDataType, auto_disable: bool = True) -> None:
        self._axis._set_output(value, auto_disable)


class Anc350Axis(InstrumentChannel):
    """
    Representation of an axis of the ANC350

    The Attocube ANC350 has 3 axis, one for every direction.

    Args:
        parent: the Instrument that the channel is attached to
        name: the name of the axis itself
        axis: the index of the axis (0..2)

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

        if isinstance(self.parent.lib, ANC350v3Lib):
            self._axis = axis

            self.add_parameter("position",
                               label="Position",
                               get_cmd=self._get_position,
                               set_cmd=False,
                               unit="mm or °"
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
                               label="Status",
                               get_cmd=self._get_status,
                               set_cmd=False)

            self.add_parameter("target_position",
                               label="Target Position",
                               get_cmd=None,
                               set_cmd=self._set_target_position,
                               unit="mm or °")

            self.add_parameter("target_range",
                               label="Target Range",
                               get_cmd=None,
                               set_cmd=self._set_target_range,
                               unit="mm or °")

            self.add_parameter("actuator",
                               label="Actuator",
                               get_cmd=None,
                               set_cmd=self._set_actuator,
                               vals=Numbers(0, 255))

            self.add_parameter("actuator_type",
                               label="Actuator Type",
                               get_cmd=self._get_actuator_type,
                               set_cmd=False)

            self.add_parameter("actuator_name",
                               label="Actuator Name",
                               get_cmd=self._get_actuator_name,
                               set_cmd=False)

            self.add_parameter("capacitance",
                               label="Capacitance",
                               get_cmd=self._get_capacitance,
                               set_cmd=False,
                               unit="nF")

            if isinstance(self.parent.lib, ANC350v4Lib):
                voltage_get = self._get_voltage
            else:
                voltage_get = False

            self.add_parameter("voltage",
                               label="Voltage",
                               get_cmd=voltage_get,
                               set_cmd=self._set_voltage,
                               vals=Numbers(0, 70),
                               unit="V")

            self.add_parameter("output",
                               label="Output",
                               parameter_class=ANC350OutputParameter,
                               axis=self,
                               val_mapping={True: True, False: False, "On": True, "Off": False, "on": True,
                                            "off": False},
                               get_cmd=None)

        else:
            raise NotImplementedError("Only version 3 and 4 are currently supported")

    # Version 3
    # ---------
    def _set_output(self, enable: bool, auto_disable: bool = True) -> None:
        """
        Enables or disables the voltage output of an axis.

        Args:
            enable (bool): True, to enable the voltage output. False, to disable it.
            auto_disable (bool): True, if the voltage output is to be deactivated automatically when end of
                          travel is detected.
        """
        self._parent.lib.set_axis_output(dev_handle=self._parent.device_handle, axis_no=self._axis, enable=enable,
                                         auto_disable=auto_disable)

    _direction_dic = {
        "foreward": False,
        "backward": True,
        +1: False,
        -1: True,
        True: True,
        False: False
    }

    def single_step(self, backward: bool) -> None:
        """
        Triggers a single step in desired direction.

        Args:
            backward: Step direction forward (False) or backward (True)
        """
        self._parent.lib.start_single_step(dev_handle=self._parent.device_handle, axis_no=self._axis,
                                           backward=self._direction_dic[backward])

    def start_continuous_move(self, backward):
        """
        Starts continuous motion in forward or backward direction.
        Other kinds of motion are stopped.

        Args:
            backward: Step direction forward (False) or backward (True)
        """
        self._parent.lib.start_continuous_move(dev_handle=self._parent.device_handle, axis_no=self._axis, start=True,
                                               backward=self._direction_dic[backward])

    def stop_continuous_move(self, backward: bool):
        """
        Stops continuous motion in forward or backward direction.

        Args:
            backward: Step direction forward (False) or backward (True)
        """
        self._parent.lib.start_continuous_move(dev_handle=self._parent.device_handle, axis_no=self._axis, start=False,
                                               backward=self._direction_dic[backward])

    _relativ_dic = {
        "absolute": True,
        "relative": False,
        True: True,
        False: False
    }

    def enable_auto_move(self, relative=False) -> None:
        """
        Enables automatic moving

        Args:
            relative: If the target position is to be interpreted absolute (False) or relative to the current position (True)
        """
        self._parent.lib.start_auto_move(dev_handle=self._parent.device_handle, axis_no=self._axis, enable=True,
                                         relative=self._relativ_dic[relative])

    def disable_auto_move(self, relative: bool = False) -> None:
        """
        Disables automatic moving

        Args:
            relative (bool): If the target position is to be interpreted absolute (False) or relative to the current position (True)
        """
        self._parent.lib.start_auto_move(dev_handle=self._parent.device_handle, axis_no=self._axis, enable=False,
                                         relative=relative)

    def _get_position(self) -> float:
        """
        Get the current position of this axis

        Returns:
            Current position in millimeters [mm] (linear type actuators) or degrees [°] (goniometers and rotators)
        """
        if self.position.unit == "mm":
            # Conversion from meters to millimeters because the wrapper works with meters
            return self._parent.lib.get_position(dev_handle=self._parent.device_handle, axis_no=self._axis) * 10E2
        else:
            # Degrees don't need to be converted for the wrapper
            return self._parent.lib.get_position(dev_handle=self._parent.device_handle, axis_no=self._axis)

    def _set_position(self, position: float) -> None:
        """
        The axis moves to the given position with the target range that is set before.
        Args:
            position (float): The position the axis moves to
        """
        if self.position.unit == "mm":
            # Conversion from meters to millimeters because the wrapper works with meters
            self._set_target_position(position / 10E2)
        else:
            # Degrees don't need to be converted for the wrapper
            self._set_target_position(position)
        self.start_auto_move(True, True)

    def _get_frequency(self) -> float:
        """
        Returns the frequency parameter of this axis.

        Returns:
            Frequency in Hertz [Hz], internal resolution is 1 Hz
        """
        return self._parent.lib.get_frequency(dev_handle=self._parent.device_handle, axis_no=self._axis)

    def _set_frequency(self, frequency: float) -> None:
        """
        Sets the frequency parameter for this axis

        Args:
            frequency (float): Frequency in Hertz [Hz], internal resolution is 1 Hz
        """
        self._parent.lib.set_frequency(dev_handle=self._parent.device_handle, axis_no=self._axis, frequency=frequency)

    def _get_amplitude(self) -> float:
        """
        Returns the amplitude parameter of this axis.

        Returns:
            Amplitude in Volts [V]
        """
        return self._parent.lib.get_amplitude(dev_handle=self._parent.device_handle, axis_no=self._axis)

    def _set_amplitude(self, amplitude: float) -> None:
        """
        Sets the amplitude parameter for an axis

        Args:
            amplitude (float): Amplitude in Volts [V] (internal resolution is 1mV)
        """
        self._parent.lib.set_amplitude(dev_handle=self._parent.device_handle, axis_no=self._axis, amplitude=amplitude)

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
        names = ("connected", "enabled", "moving", "target", "eot_fwd", "eot_bwf", "error")
        status_list = self._parent.lib.get_axis_status(dev_handle=self._parent.device_handle, axis_no=self._axis)
        status_dict = {}

        for name, status in zip(names, status_list):
            status_dict[name] = status

        return status_dict

    def _set_voltage(self, voltage: float) -> None:
        """
        Sets the DC level on the voltage output when no sawtooth based motion and no feedback loop
        is active.

        Args:
            voltage: DC output voltage in Volts [V], internal resolution is 1 mV
        """
        self._parent.lib.set_dc_voltage(dev_handle=self._parent.device_handle, axis_no=self._axis, voltage=voltage)

    def _set_target_position(self, target: float) -> None:
        """
        Sets the target position for automatic motion.
        For linear type actuators the position unit is mm, for goniometers and rotators it is degree.

        Args:
            target (float): Target position in meters [mm] or degrees [°]. Internal resolution is 1 nm or
                    1 µ°.
        """
        if self.position.unit == "mm":
            self._parent.lib.set_target_position(dev_handle=self._parent.device_handle, axis_no=self._axis,
                                                 target=target / 10E2)
        else:
            self._parent.lib.set_target_position(dev_handle=self._parent.device_handle, axis_no=self._axis,
                                                 target=target)

    def _set_target_range(self, target_range: float) -> None:
        """
        Sets the range around the target position where the target is considered to be reached.
        For linear type actuators the position unit is mm, for goniometers and rotators it is degree.

        Args:
             target_range (float): Target range in millimeters [mm] or degrees [°]. Internal resolution is 1 nm or
                          1 µ°.
        """
        if self.position.unit == "mm":
            self._parent.lib.set_target_range(dev_handle=self._parent.device_handle, axis_no=self._axis,
                                              target=target_range / 10E2)
        else:
            self._parent.lib.set_target_range(dev_handle=self._parent.device_handle, axis_no=self._axis,
                                              target=target_range)

    def _set_actuator(self, actuator: int) -> None:
        """
        Selects the actuator to be used for the axis from actuator presets. And changes the unit of the position
        parameters if necessary.

        Args:
            actuator (int): Actuator selection (0..255)
        """
        old_actuator_type = self._get_actuator_type()
        self._parent.lib.select_actuator(dev_handle=self._parent.device_handle, axis_no=self._axis, actuator=actuator)
        current_actuator_type = self._get_actuator_type()
        if current_actuator_type != old_actuator_type:
            if current_actuator_type == ANC350LibActuatorType(0):
                self._change_position_unit("mm")
            elif (old_actuator_type is ANC350LibActuatorType(1)) or (old_actuator_type is ANC350LibActuatorType(2)):
                self._change_position_unit("°")

    def _change_position_unit(self, unit: str):
        if str in ["mm", "°"]:
            self.position.unit = unit
            self.target_position = unit
            self.target_range = unit
        else:
            raise ValueError("Unit is invalid - " + unit)

    def _get_actuator_type(self) -> ANC350LibActuatorType:
        """
        Get the type of the currently selected actuator

        Returns:
            Type of the actuator
        """
        return self._parent.lib.get_actuator_type(dev_handle=self._parent.device_handle, axis_no=self._axis)

    def _get_actuator_name(self) -> str:
        """
        Returns the name of the currently selected actuator

        Returns:
            Name of the actuator
        """
        return self._parent.lib.get_actuator_name(dev_handle=self._parent.device_handle, axis_no=self._axis)

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
        #10E9 as factor for the conversion from F to nF
        return self._parent.lib.measure_capacitance(dev_handle=self._parent.device_handle, axis_no=self._axis) * 10E9

    # Version 4
    # ---------
    def _get_voltage(self) -> float:
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

    def __init__(self, library, name: str, inst_num: int = 0, search_usb: bool = True,
                 search_tcp: bool = True):
        super().__init__(name)

        self._lib = library

        self._dev_no = inst_num

        if self._lib.discover(search_usb=search_usb, search_tcp=search_tcp) < inst_num:
            raise RuntimeError("No matching device found for this number")
        else:
            self._device_handle = self._lib.connect(inst_num)

        axischannels = ChannelList(self, "Anc350Axis", Anc350Axis)
        for nr, axis in enumerate(['x', 'y', 'z'], 0):
            axis_name = "{}_axis".format(axis)
            axischannel = Anc350Axis(parent=self, name=axis_name, axis=nr)
            axischannels.append(axischannel)
            self.add_submodule(axis_name, axischannel)
        axischannels.lock()
        self.add_submodule("axis_channels", axischannels)

    def save_params(self) -> None:
        """
        Saves parameters to persistent flash memory in the device. They will be present as defaults after the next power-on.
        """
        self._lib.save_params(dev_handle=self._device_handle)

    def disconnect(self) -> None:
        """
        Closes the connection to the device. The device handle becomes invalid.
        """
        self._lib.disconnect(dev_handle=self._device_handle)
        self._device_handle = None

    def get_idn(self):
        """
        Returns a dictionary with information About the device

        Returns:
            A dictionary containing vendor, model, serial number and firmware version
        """
        device_info = self._lib.get_device_info(self._dev_no)
        version_no = 3
        if isinstance(self.parent._lib, ANC350v4Lib):
            version_no = 4

        return {"vendor": "Attocube", 'model': 'ANC350',
                'serial': device_info[2], 'firmware': version_no}
