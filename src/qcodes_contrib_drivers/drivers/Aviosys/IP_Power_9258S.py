from qcodes import Instrument, InstrumentChannel, ChannelList
from qcodes.utils.validators import Enum
from qcodes.utils.helpers import create_on_off_val_mapping
import urllib.request


class PowerChannel(InstrumentChannel):
    """
    Channel class for a socket on the Aviosys IP Power 9258S.

    Args:
        parent: Parent instrument.
        name: Channel name.
        channel: Alphabetic channel id.
    """

    CHANNEL_IDS = {'A': 1, 'B': 2, 'C': 3, 'D': 4}
    CHANNEL_NAMES = Enum(*CHANNEL_IDS.keys())

    def __init__(self, parent: Instrument, name: str, channel: str):

        super().__init__(parent, name)

        # validate the channel id
        PowerChannel.CHANNEL_NAMES.validate(channel)
        self._id_name = channel
        self._id_number = PowerChannel.CHANNEL_IDS[channel]

        # add parameters
        self.add_parameter('power_enabled',
                           get_cmd=self._get_power_enabled,
                           set_cmd=self._set_power_enabled,
                           get_parser=int,
                           val_mapping=create_on_off_val_mapping(on_val="1", off_val="0"),
                           label='Power {}'.format(self._id_name))

    # get methods
    def _get_power_enabled(self):
        request = urllib.request.Request(self.parent.address+'/set.cmd?cmd=getpower')
        response = urllib.request.urlopen(request)
        request_read = response.read()
        return request_read.decode("utf-8")[4 + self._id_number * 6]

    # set methods
    def _set_power_enabled(self, power):
        request = urllib.request.Request(f"{self.parent.address}/set.cmd?cmd=setpower+p6{self._id_number}={power}")
        urllib.request.urlopen(request)


class Aviosys_IP_Power_9258S(Instrument):
    """
    Instrument driver for the Aviosys IP Power 9258S. The IP Power 9258S is a network power controller. The device
    controls up to four power channels, that can be turned on and off. With this instrument also non-smart instruments
    can be controlled remotely.

    Args:
        name: Instrument name.
        address: http address.
        login_name: http login name.
        login_password: http login password.

    Attributes:
        address: http address.
    """

    def __init__(self, name: str, address: str, login_name: str, login_password: str, **kwargs):

        super().__init__(name, **kwargs)

        # save access settings
        self.address = address

        # set up http connection
        password_manager = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        password_manager.add_password(None, self.address, login_name, login_password)
        handler = urllib.request.HTTPBasicAuthHandler(password_manager)
        opener = urllib.request.build_opener(handler)
        urllib.request.install_opener(opener)

        # add channels
        channels = ChannelList(self, "PowerChannels", PowerChannel, snapshotable=False)
        for id_name in PowerChannel.CHANNEL_IDS.keys():
            channel = PowerChannel(self, 'Chan{}'.format(id_name), id_name)
            channels.append(channel)
            self.add_submodule(id_name, channel)
        channels.lock()
        self.add_submodule("channels", channels)

        # print connect message
        self.connect_message()

    # get functions
    def get_idn(self):
        return {'vendor': 'Aviosys', 'model': 'IP Power 9258S'}
