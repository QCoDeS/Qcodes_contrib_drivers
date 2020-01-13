from qcodes import VisaInstrument, InstrumentChannel, ChannelList
from qcodes.utils.validators import Enum


class SensorChannel(InstrumentChannel):
    """
    Channel class for the Lakeshore 331.

    Args:
        parent: The parent Lakeshore 331.
        name: The channel name.
        channel: The channel ID.

    Attributes:
        channel: The channel ID.
    """

    _channel_values = Enum('A', 'B')

    def __init__(self, parent: "Model_331", name: str, channel: str):
        super().__init__(parent, name)

        # validate the channel value
        self._channel_values.validate(channel)
        self.channel = channel

        # add parameters
        self.add_parameter('temperature',
                           get_cmd='KRDG? {}'.format(self.channel),
                           get_parser=float,
                           label='temperature {}'.format(self.channel),
                           unit='K')

        self.add_parameter('sensor_raw',
                           get_cmd='SRDG? {}'.format(self.channel),
                           get_parser=float,
                           label='sensor raw {}'.format(self.channel),
                           unit=u"\u03A9")  # TODO: this will vary based on sensor type

        self.add_parameter('sensor_status',
                           get_cmd='RDGST? {}'.format(self.channel),
                           val_mapping={
                               'ok': 0,
                               'invalid reading': 1,
                               'temp underrange': 16,
                               'temp overrange': 32,
                               'sensor units zero': 64,
                               'temp overrange, sensor units zero': 96,
                               'Sensor Units Overrange': 128,
                               'temp underrange, sensor units overrange': 144},
                           label='sensor status {}'.format(self.channel))


class Model_331(VisaInstrument):
    """
    Instrument class for the Lakeshore 331.

    Args:
        name: The channel name.
        address: The GPIB address.
    """

    _loop = 1

    def __init__(self, name: str, address: str, **kwargs):
        super().__init__(name, address, terminator="\r\n", **kwargs)

        # add channels
        channels = ChannelList(self, "TempSensors", SensorChannel, snapshotable=False)
        for channel_id in ('A', 'B'):
            channel = SensorChannel(self, 'Chan{}'.format(channel_id), channel_id)
            channels.append(channel)
            self.add_submodule(channel_id, channel)
        channels.lock()
        self.add_submodule("channels", channels)

        # add parameters
        self.add_parameter('heater_output',
                           get_cmd='HTR?',
                           get_parser=float,
                           label='heater output',
                           unit='%')

        self.add_parameter('heater_range',
                           get_cmd='RANGE?',
                           get_parser=int,
                           set_cmd='RANGE {}',
                           val_mapping={
                               'off': 0,
                               '0.5W': 1,
                               '5W': 2,
                               '50W': 3},
                           label='heater range')

        self.add_parameter('input',
                           get_cmd='CSET? %i' % self._loop,
                           set_cmd='CSET ' + str(self._loop) + ',{},1,1,1',
                           get_parser=lambda ans: ans[0],
                           label='input')

        self.add_parameter('setpoint',
                           get_cmd='SETP? '+str(self._loop),
                           set_cmd='SETP ' + str(self._loop) + ', {}',
                           get_parser=float,
                           label='setpoint',
                           unit='K')

        # print connect message
        self.connect_message()
