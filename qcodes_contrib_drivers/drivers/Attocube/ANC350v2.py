from typing import Tuple, Dict, Any

from qcodes import Instrument, Parameter
from qcodes.instrument.channel import InstrumentChannel, ChannelList
from qcodes.instrument.parameter import ParamRawDataType
from qcodes.utils.validators import Numbers
import qcodes.utils.validators as vals

from qcodes_contrib_drivers.drivers.Attocube.ANC350Lib import ANC350v2Lib


class Anc350Axis(InstrumentChannel):
    def __init__(self, parent: "ANC350", name: str, axis: int):
        super().__init__(parent, name)

        if isinstance(self.parent.lib, ANC350v2Lib):
            self._axis = axis

            self.add_parameter("position",
                               label="Position",
                               get_cmd=,
                               set_cmd=,
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

            #TODO: to implement
            self.add_parameter("status",
                               label="Status",
                               get_cmd=,
                               set_cmd=)


            self.add_parameter("target_position",
                               label="Target Position",
                               get_cmd=,
                               set_cmd=,
                               unit="mm or °")

            self.add_parameter("target_range",
                               label="Target Range",
                               get_cmd=None,
                               set_cmd=,
                               unit="mm or °")

            self.add_parameter("actuator",
                               label="Actuator",
                               get_cmd=,
                               set_cmd=,
                               vals=Numbers(0, 255))

            self.add_parameter("capacitance",
                               label="Capacitance",
                               get_cmd=self._get_capacitance,
                               set_cmd=False,
                               unit="nF")

            self.add_parameter("voltage",
                               label="Voltage",
                               get_cmd=,
                               set_cmd=,
                               vals=Numbers(0, 70),
                               unit="V")

            self.add_parameter("output",
                               val_mapping={True: True, False: False, "On": True, "Off": False, "on": True,
                                            "off": False},
                               get_cmd=)

        else:
            raise NotImplementedError("Driver for devices with version 2")


    def _get_frequency(self) -> float:
        """
        Returns the frequency parameter of this axis.

        Returns:
            Frequency in Hertz [Hz], , internal resolution is 1 Hz
        """
        return self._parent._lib.get_frequency(dev_handle=self._parent._device_handle, axis_no=self._axis)

    def _set_frequency(self, frequency: float) -> None:
        self.self._parent._lib.set_frequency(dev_handle=self._parent._device_handle, axis_no=self._axis,
                                             frequency=int(round(frequency)))

    def _get_amplitude(self) -> float:
        """
        Returns the amplitude parameter of this axis.

        In case of standstill of the actor this is the amplitude setpoint. In case of movement the
        amplitude set by amplitude control is determined.

        Returns:
            Amplitude in Volts [V]
        """
        # /1E3 for conversion from mV to V
        return self._parent._lib.get_amplitude(dev_handle=self._parent._device_handle, axis_no=self._axis) / 1E3

    def _set_amplitude(self, amplitude: float) -> None:
        """
        Sets the amplitude setpoint

        Args:
            amplitude (float): Amplitude in Volts [V] (internal resolution is 1mV)
        """
        self._parent._lib.set_amplitude(dev_handle=self._parent._device_handle, axis_no=self._axis,
                                        amplitude=(amplitude * 1E3))

        #TODO: implement missing methods for the parameters

    def _get_capacitance(self) -> float:
        """
        Returns the motor capacitance
        Performs a measurement of the capacitance of the piezo motor and returns the result

        Returns:
            Measured capacity in picofarad [nF] or None, in case of an error
        """
        #1E3 as factor for the conversion from F to nF because the library v2 returns pF
        return self._parent._lib.measure_capacity(dev_handle=self._parent._deivce_handle, axis_no= self._axis) /1E3


class ANC350(Instrument):
    def __init__(self, library: ANC350v2Lib, name: str, inst_num: int = 0):
        super().__init__(name)

        self._lib = library

        #TODO: How to check if the inst_num is viable?
        self._device_handle = self._lib.connect(inst_num)

        axischannels = ChannelList(self, "Anc350Axis", Anc350Axis)
        for nr, axis in enumerate(['x', 'y', 'z'], 0):
            axis_name = "{}_axis".format(axis)
            axischannel = Anc350Axis(parent=self, name=axis_name, axis=nr)
            axischannels.append(axischannel)
            self.add_submodule(axis_name, axischannel)
        axischannels.lock()
        self.add_submodule("axis_channels", axischannels)

    def disconnect(self) -> None:
        """
        Closes the connection to the device.
        """
        self._lib.close(dev_handle=self._device_handle)
        self._device_handle = None

    def get_idn(self):
        """
        Returns a dictionary with information About the device

        Returns:
            A dictionary containing vendor, model, serial number and firmware version
        """

        # TODO: How to get the serial number?
        return {"vendor": "Attocube", 'model': 'ANC350',
                'serial': serial_no, 'firmware': "2"}
