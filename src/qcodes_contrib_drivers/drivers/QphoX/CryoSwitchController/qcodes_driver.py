from qcodes import Instrument, ChannelList, InstrumentChannel
from qcodes.utils.validators import Numbers,Bool,Enum
from qcodes_contrib_drivers.drivers.QphoX.CryoSwitchController.CryoSwitchController import Cryoswitch

class CryoSwitchChannel(InstrumentChannel):
    def __init__(self, parent: Instrument, name: str, channel: str):
        super().__init__(parent, name)

        self.add_parameter(
            'active_contact',
            get_cmd=self._get_active_contact,
            vals=Numbers(0, 6)
        )

        self._channel = channel
        self._active_contact = 0

    def connect(self, contact: int):
        trace = self.parent.connect(self._channel, contact)
        self._active_contact = contact
        self.active_contact()
        return trace

    def disconnect(self, contact: int):
        trace = self.parent.disconnect(self._channel, contact)
        self._active_contact = 0
        self.active_contact()
        return trace

    def disconnect_all(self):
        trace = self.parent.disconnect_all(self._channel)
        self._active_contact = 0
        self.active_contact()
        return trace

    def smart_connect(self, contact: int):
        trace = self.parent.smart_connect(self._channel, contact)
        self._active_contact = contact
        self.active_contact()
        return trace

    def _get_active_contact(self):
        return self._active_contact

class CryoSwitchControllerDriver(Instrument):
    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)

        self._controller = Cryoswitch()

        self.add_parameter(
            'output_voltage',
            set_cmd=self._controller.set_output_voltage,
            vals=Numbers(0, 10)
        )

        self.add_parameter(
            'pulse_duration',
            set_cmd=self._controller.set_pulse_duration_ms,
            vals=Numbers(0, 1000)
        )

        self.add_parameter(
            'OCP_value',
            set_cmd=self._controller.set_OCP_mA,
            vals=Numbers(0, 1000)
        )

        self.add_parameter(
            'chopping',
            set_cmd=self._enable_disable_chopping,
            vals=Bool()
        )

        self.add_parameter(
            'switch_model',
            set_cmd=self._controller.select_switch_model,
            vals=Enum('R583423141', 'R573423600')
        )

        self.add_parameter(
            'power_status',
            get_cmd=self._controller.get_power_status,
            vals=Enum(0, 1)
        )

        def get_switches_state(self, port: str = None):
            return self._controller.get_switches_state(port)

        def disconnect_all(self, port: str):
            self._controller.disconnect_all(port)

        def smart_connect(self, port: str, contact: int):
            return self._controller.smart_connect(port, contact)
        
        self.add_function('start', call_cmd=self._controller.start)
        self.add_function('enable_OCP', call_cmd=self._controller.enable_OCP)
        self.add_function('reset_OCP', call_cmd=self._controller.reset_OCP)

        channels = ChannelList(self, "Channels", CryoSwitchChannel, snapshotable=False)
        for ch in ['A', 'B', 'C', 'D']:
            channel = CryoSwitchChannel(self, f"channel_{ch}", ch)
            channels.append(channel)
        channels.lock()
        self.add_submodule("channels", channels)

    def _enable_disable_chopping(self, enable: bool):
        if enable:
            self._controller.enable_chopping()
        else:
            self._controller.disable_chopping()

    def connect(self, port: str, contact: int):
        return self._controller.connect(port, contact)

    def disconnect(self, port: str, contact: int):
        return self._controller.disconnect(port, contact)

    def get_idn(self):
        pass
