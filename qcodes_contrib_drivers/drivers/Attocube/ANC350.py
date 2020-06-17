from qcodes import Instrument
from qcodes.instrument.channel import InstrumentChannel, ChannelList
from qcodes.utils.validators import Numbers

from qcodes_contrib_drivers.drivers.Attocube.ANC350Lib import v3


# TODO: Bei Docstrings einfach teilweise die Kommentare uebernehmen
class Anc350Axis(InstrumentChannel):

    def __init__(self, parent: "ANC350", name: str, axis: int):
        super().__init__(parent, name)

        self._axis = axis
        self._parent = parent

        self.add_parameter("position",
                           label="Position",
                           get_cmd=self._get_position,
                           set_cmd=False,
                           docstring="""
                           
                           """)

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
                           set_cmd=False,
                           docstring="""
                           Reads status information about an axis of the device. And returns them in a array.
                           """)

        self.add_parameter("output",
                           label="",
                           # output True, false oder 0,1???
                           get_cmd=False,
                           set_cmd=parent.lib.set_axis_output(dev_handle=parent.device_handle),
                           vals=,  # True und False / 0 und 1
                           docstring="""
                           
                           """)

        self.add_parameter("voltage",
                           label="",
                           get_cmd=False,
                           set_cmd=self._set_voltage,
                           unit="V",
                           docstring="""
                           Sets the DC level on the voltage output when no sawtooth based motion and no feedback loop
                           is active.
                           """)

        self.add_parameter("target_postion",
                           label="",
                           get_cmd=False,
                           set_cmd=self._set_target_position,
                           docstring="""
                           
                           """)

        # TODO: Unit Angabe - Meter oder Grad oder gibt man bei unit beides an?
        self.add_parameter("target_range",
                           label="",
                           get_cmd=False,
                           set_cmd=self._set_target_range,
                           docstring="""
                           
                           """)

        # Kann man actuator und actuator name kombinieren auch wenn sie nicht den selben Datentypen zurückgeben
        self.add_parameter("actuator",
                           label="",
                           get_cmd=False,
                           set_cmd=self,
                           vals=Numbers(0, 255),
                           docstring="""
                           
                           """)

        self.add_parameter("actuator_name",
                           label="",
                           get_cmd=self._get_actuator_name,
                           set_cmd=False,
                           docstring="""
                           
                           """)

        self.add_parameter("capacitance",
                           label="",
                           get_cmd=self._get_capacitance,
                           set_cmd=False,
                           unit="F",
                           docstring="""

                            """)

    # TODO: umsetztbar als Parameter?
    def start_single_step(self, backward):
        self._parent.lib.start_single_step(dev_handle=self._parent.device_handle, axis_no=self._axis, backward=backward)

    def start_continuous_move(self, start, backward):
        self._parent.lib.start_continuous_move(dev_handle=self._parent.device_handle, axis_no=self._axis, start=start,
                                               backward=backward)

    def start_auto_move(self, enable, relative):
        self._parent.lib.start_auto_move(dev_handle=self._parent.device_handle, axis_no=self._axis, enable=enable,
                                         relative=relative)

    def _get_position(self):
        return self._parent.lib.set_target_postion(dev_handle=self._parent.device_handle, axis_no=self._axis)

    def _get_frequency(self):
        return self._parent.lib.get_frequency(dev_handle=self._parent.device_handle, axis_no=self._axis)

    def _set_frequency(self, frequency):
        self._parent.lib.set_frequency(dev_handle=self._parent.device_handle, axis_no=self._axis, frequency=frequency)

    def _get_amplitude(self):
        return self._parent.lib.get_amplitude(dev_handle=self._parent.device_handle, axis_no=self._axis)

    def _set_amplitude(self, amplitude):
        self._parent.lib.get_amplitude(dev_handle=self._parent.device_handle, axis_no=self._axis, amplitude=amplitude)

    def _get_status(self):
        names = ("connected","enabled","moving","target","eot_fwd","eot_bwf", "error")
        status_list = self._parent.lib.get_axis_status(dev_handle=self._parent.device_handle, axis_no=self._axis)
        status_dict = {}

        for name, status in zip(names,status_list):
            status_dict[name] = status

        return status_dict

    # wie macht man das mit zwei unbekannten? in zwei parameter aufteilen? Und Problem mit True/ False
    def _set_axis_output(self, enable):
        self._parent.lib.get_axis_status(dev_handle=self._parent.device_handle, axis_no=self._axis, enable=enable)

    def _set_voltage(self, voltage):
        self._parent.lib.set_dc_voltage(dev_handle=self._parent.device_handle, axis_no=self._axis, voltage=voltage)

    def _set_target_position(self, target):
        self._parent.lib.set_target_postion(dev_handle=self._parent.device_handle, axis_no=self._axis, target=target)

    def _set_target_range(self, target_range):
        self._parent.lib.set_target_range(dev_handle=self._parent.device_handle, axis_no=self._axis,
                                          target=target_range)

    def _set_actuator(self, actuator):
        self._parent.lib.select_actuator(dev_handle=self._parent.device_handle, axis_no=self._axis, actuator=actuator)

    def _get_actuator_name(self):
        return self._parent.lib.get_actuator_name(dev_handle=self._parent.device_handle, axis_no=self._axis)

    def _get_capacitance(self):
        return self._parent.lib.measure_capacitance(dev_handle=self._parent.device_handle, axis_no=self._axis)


class ANC350(Instrument):
    def __init__(self, name: str, num: int = 0, search_usb: bool = True, search_tcp: bool = True):
        super().__init__(name)  # Fehlende Parameter?

        lib = v3.ANC350v3Lib()

        self._dev_no = num

        if lib.discover(search_usb=search_usb, search_tcp=search_tcp) < num:
            raise RuntimeError("No matching device found for this number")
        else:
            self.device_handle = lib.connect(num)

        # Kofiguration

        # snapshotable?
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
                           set_cmd=False,
                           docstring="""
                           
                           """)

    def save_params(self):
        self.lib.save_params(dev_handle=self.device_handle)

    def disconnect(self):
        self.lib.disconnect(dev_handle=self.device_handle)
        del self.device_handle

    def _get_device_info(self):
        return self.lib.get_device_info(self._dev_no)
