from qcodes.instrument import Instrument, ChannelList, InstrumentChannel
from qcodes.validators import Numbers,Bool,Enum
from qcodes_contrib_drivers.drivers.QphoX.CryoSwitchController.CryoSwitchController import Cryoswitch
import os
from typing import Optional

class CryoSwitchChannel(InstrumentChannel):
    """
    CryoSwitchChannel class is used to define the channels for the CryoSwitchControllerDriver.
    It is a subclass of the InstrumentChannel class from qcodes.

    Attributes:
        parent (Instrument): The parent instrument to which the channel is attached.
        name (str): The name of the channel.
        channel (str): The channel identifier.
        active_contact (Parameter): The active contact for the channel.
            It can be a number between 0 and 6.
    """

    def __init__(self, parent: Instrument, name: str, channel: str):
        """
        Initializes a new instance of the CryoSwitchChannel class.

        Args:
            parent (Instrument): The parent instrument to which the channel is attached.
            name (str): The name of the channel.
            channel (str): The channel identifier.
        """
        super().__init__(parent, name)

        self.add_parameter(
            'active_contact',
            get_cmd=self._get_active_contact,
            vals=Numbers(0, 6),
            docstring="Number of the active channel, based on the json file tracking the changes. "
                "Value 0 indicates no contact is connected."
        )

        self._channel = channel
        self._active_contact = 0

    def connect(self, contact: int):
        """
        Applies a current pulse to make a specified contact.

        Args:
            contact (int): The contact to be connected.

        Returns:
            np.ndarray: The current waveform after the connection.
        """
        trace = self.parent.connect(self._channel, contact)
        self._active_contact = contact
        self.active_contact()
        return trace

    def disconnect(self, contact: int):
        """
        Applies a current pulse to disconnect a specified contact.

        Args:
            contact (int): The contact to be disconnected.

        Returns:
            np.ndarray: The current waveform after the disconnection.
        """
        trace = self.parent.disconnect(self._channel, contact)
        self._active_contact = 0
        self.active_contact()
        return trace

    def disconnect_all(self):
        """
        Applies a disconnecting pulse to all contacts.

        Returns:
            np.ndarray: The current waveform after all contacts are disconnected.
        """
        trace = self.parent.disconnect_all(self._channel)
        self._active_contact = 0
        self.active_contact()
        return trace

    def smart_connect(self, contact: int):
        """
        Connects a contact to the channel smartly, i.e., disconnects the previously connected
        contacts and connects the specified switch contact based on the tracking history.

        Args:
            contact (int): The contact to be connected.

        Returns:
            np.ndarray: The current waveform after the smart connection.
        """
        trace = self.parent.smart_connect(self._channel, contact)
        self._active_contact = contact
        self.active_contact()
        return trace

    def _get_active_contact(self):
        """
        Gets the active contact for the channel.

        Returns:
            int: The active contact for the channel.
        """
        return self._active_contact

class CryoSwitchControllerDriver(Instrument):
    """
    CryoSwitchControllerDriver class is used to control the Cryoswitch.
    It is a subclass of the Instrument class from qcodes.

    Attributes:
        name (str): The name of the instrument.
        output_voltage (Parameter): The output voltage of the controller.
            It can be a number between 0 and 25 (V).
        pulse_duration (Parameter): The pulse duration of the controller.
            It can be a number between 0 and 1000 (ms).
        OCP_value (Parameter): The overcurrent protection trigger value of the controller.
            It can be a number between 0 and 1000 (mA).
        chopping (Parameter): The chopping function status of the controller.
            It can be a boolean value.
        switch_model (Parameter): The switch model used by the controller.
            It can be either 'R583423141' or 'R573423600'.
            Equvalently, one may set the model using 'RT' (room temperature) for R573423600, and 'CRYO' instead of 'R583423141'.
            The two switch types require different connectivity between the D-Sub on the controller box and the switch.
        power_status (Parameter): The power status of the controller.
            It can be either 0 (disabled) or 1 (enabled).
    """

    def __init__(self, name: str, **kwargs):
        """
        Initializes a new instance of the CryoSwitchControllerDriver class.

        Args:
            name (str): The name of the instrument.
        """
        super().__init__(name, **kwargs)

        self._controller = Cryoswitch()
        self._switch_model: Optional[str] = None

        self.add_parameter(
            'output_voltage',
            set_cmd=self._controller.set_output_voltage,
            vals=Numbers(5, 28),
            docstring="Magnitude of the voltage pulse used to control the switch"
        )

        self.add_parameter(
            'pulse_duration',
            set_cmd=self._controller.set_pulse_duration_ms,
            vals=Numbers(1, 100),
            docstring="Duration of the voltage pulse used to control the switch in ms"
        )

        self.add_parameter(
            'OCP_value',
            set_cmd=self._controller.set_OCP_mA,
            vals=Numbers(1, 150),
            docstring="OVercurrent protection level in mA"
        )

        self.add_parameter(
            'chopping',
            set_cmd=self._enable_disable_chopping,
            vals=Bool()
        )

        self.add_parameter(
            'switch_model',
            set_cmd=self._select_switch_model,
            get_cmd=self._get_switch_model,
            vals=Enum('R583423141', 'R573423600', 'CRYO', 'RT'),
            docstring="Selection between the configurations for control of room-temperature "
                    "and cryogenic version of the switch. Permitted values: 'R583423141', 'R573423600', 'CRYO', 'RT'"
        )

        self.add_parameter(
            'power_status',
            get_cmd=self._controller.get_power_status,
            vals=Enum(0, 1),
            docstring="On (1) or Off (0) status of the switch controller."
        )

        self.add_function('start', call_cmd=self._controller.start)
        self.add_function('enable_OCP', call_cmd=self._controller.enable_OCP)
        self.add_function('reset_OCP', call_cmd=self._controller.reset_OCP)

        channels = ChannelList(self, "Channels", CryoSwitchChannel, snapshotable=False)
        for ch in ['A', 'B', 'C', 'D']:
            channel = CryoSwitchChannel(self, f"{ch}", ch)
            channels.append(channel)
        channels.lock()
        self.add_submodule("channels", channels)

    def _select_switch_model(self, switch_type: Optional[str] = None):
        if switch_type in ['R583423141', 'CRYO']:
            self._controller.select_switch_model('R583423141')
            self._switch_model = 'R583423141'
            print('Note that R583423141 and R573423600 models require different connection to the switch box.')
        elif switch_type in ['R573423600', 'RT']:
            self._controller.select_switch_model('R573423600')
            self._switch_model = 'R573423600'
            print('Note that R583423141 and R573423600 models require different connection to the switch box.')
        else:
            print('Selected switch type does not exist.')

    def _get_switch_model(self):
        return self._switch_model

    def get_switches_state(self, port: Optional[str] = None):
        """
        Read and return the state of the contacts as recorded in the states.json

        Args:
            port (str|None): A port which states are to be returned. None will return
                the state of all contacts. (default None)

        Returns:
            dict: dictionary listing a state of every contact.
        """
        return self._controller.get_switches_state(port)

    def disconnect_all(self, port: str):
        """
        Applies a disconnecting current pulse to all contacts of the
        specified port

        Args:
            port (str): A letter A-D indicating the port to be controlled.
        """
        self._controller.disconnect_all(port)

    def smart_connect(self, port: str, contact: int):
        """
        Disconnects from all the connected contacts for a specified channel
        and connects only to the indicated one.

        Args:
            port (str): A letter A-D indicating the port to be controlled.
            contact (int): Number of the contact that is to be connected
        """
        return self._controller.smart_connect(port, contact)

    def _enable_disable_chopping(self, enable: bool):
        """
        Enables or disables the chopping function of the controller.

        Args:
            enable (bool): True to enable the chopping function, False to disable it.
        """
        if enable:
            self._controller.enable_chopping()
        else:
            self._controller.disable_chopping()

    def connect(self, port: str, contact: int):
        """
        Applies a current pulse to connect a specific contact of
        a switch at a selected port.

        Args:
            port (str): The port to which the contact is connected.
            contact (int): The contact to be connected.

        Returns:
            trace: The current waveform after the connection.
        """
        return self._controller.connect(port, contact)

    def disconnect(self, port: str, contact: int):
        """
        Applies a current pulse to disconnect a specific contact of
        a switch at a selected port.

        Args:
            port (str): The port from which the contact is disconnected.
            contact (int): The contact to be disconnected.

        Returns:
            trace: The current waveform after the disconnection.
        """
        return self._controller.disconnect(port, contact)

    def get_idn(self):
        """
        A dummy getidn function for the instrument initialization
        in QCoDeS to work.
        """
        pass

    def close(self):
        """
        Disconnect from the switch controller.
        """
        self._controller.labphox.disconnect()
        super().close()
