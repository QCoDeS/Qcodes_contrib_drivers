from qcodes import VisaInstrument, validators as vals
from qcodes import InstrumentChannel, ChannelList
from functools import partial


class RohdeSchwarzHMPChannel(InstrumentChannel):
    def __init__(self, parent, name, channel):
        super().__init__(parent, name)
        self.channel = channel
        self.max_current = self.get_max_current()

        self._scpi_commands = {"set_voltage": "SOURce:VOLTage:LEVel:IMMediate:AMPLitude",
                               "set_current": "SOURce:CURRent:LEVel:IMMediate:AMPLitude",
                               "state": "OUTPut:STATe",
                               "voltage": "MEASure:SCALar:VOLTage:DC",
                               "current": "MEASure:SCALar:CURRent:DC"
                               }

        self.add_parameter("set_voltage",
                           label='Target voltage output',
                           set_cmd=partial(self.send_cmd, "set_voltage"),
                           get_cmd=partial(self.send_cmd, "set_voltage", None),
                           get_parser=float,
                           unit='V',
                           vals=vals.Numbers(0, 32.050)
                           )
        self.add_parameter("set_current",
                           label='Target current output',
                           set_cmd=partial(self.send_cmd, "set_current"),
                           get_cmd=partial(self.send_cmd, "set_current", None),
                           get_parser=float,
                           unit='A',
                           vals=vals.Numbers(0.5e-3, self.max_current)
                           )
        self.add_parameter('state',
                           label='Output enabled',
                           set_cmd=partial(self.send_cmd, "state"),
                           get_cmd=partial(self.send_cmd, "state", None),
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF')
                           )
        self.add_parameter("voltage",
                           label='Measured voltage',
                           get_cmd=partial(self.send_cmd, "voltage", None),
                           get_parser=float,
                           unit='V',
                           )
        self.add_parameter("current",
                           label='Measured current',
                           get_cmd=partial(self.send_cmd, "current", None),
                           get_parser=float,
                           unit='A',
                           )
        self.add_parameter("power",
                           label='Measured power',
                           get_cmd=self._get_power,
                           get_parser=float,
                           unit='W',
                           )

    def get_max_current(self):
        if self.parent.model_no > 4000:
            return 10
        elif self.parent.model_no == 2020 and self.channel == 1:
            return 10
        return 5

    def send_cmd(self, param, value):
        self.write(f"INSTrument:NSELect {self.channel:d}")
        if value is None:
            return self.ask(f"{self._scpi_commands[param]}?")
        else:
            return self.write(f"{self._scpi_commands[param]} {value}")

    def _get_power(self):
        curr = float(self.send_cmd("current", None))
        volt = float(self.send_cmd("voltage", None))
        return curr * volt


class _RohdeSchwarzHMP(VisaInstrument):
    """
    This is the general HMP Power Supply driver class that implements shared parameters and functionality
    among all similar power supplies from Rohde & Schwarz.

    This driver was written to be inherited from by a specific driver (e.g. HMP4040).
    """

    def __init__(self, name, address, model_no, **kwargs):
        super().__init__(name, address, terminator="\n", **kwargs)
        self.model_no = model_no

        self.add_parameter('state',
                           label='Output enabled',
                           set_cmd='OUTPut:GENeral {}',
                           get_cmd='OUTPut:GENeral?',
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF')
                           )
        # number of channels can be calculated from model number
        num_channels = (self.model_no % 100) // 10
        # channel-specific parameters
        channels = ChannelList(self, "SupplyChannel", RohdeSchwarzHMPChannel, snapshotable=False)
        for ch_num in range(1, num_channels + 1):
            ch_name = "ch{}".format(ch_num)
            channel = RohdeSchwarzHMPChannel(self, ch_name, ch_num)
            channels.append(channel)
            self.add_submodule(ch_name, channel)
        channels.lock()
        self.add_submodule("channels", channels)

        self.connect_message()
