from qcodes.instrument.visa import VisaInstrument
from qcodes.instrument import InstrumentChannel
from qcodes.utils.validators import Numbers
from functools import partial


class Keithley_Sense(InstrumentChannel):
    def __init__(self, parent: VisaInstrument, name: str, channel: str) -> None:
        valid_channels = ['VOLT', 'CURR', 'RES', 'FRES']
        if channel.upper() not in valid_channels:
            raise ValueError(f"Channel must be one of the following: {', '.join(valid_channels)}")
        super().__init__(parent, name)

        self.add_parameter('measure',
                           unit=partial(self._get_unit, channel),
                           label=partial(self._get_label, channel),
                           get_parser=float,
                           get_cmd=f":MEAS:{channel}?",
                           docstring="Measure value of chosen quantity (Current/Voltage/Resistance)."
                           )

        self.add_parameter('nlpc',
                           label='NLPC',
                           get_parser=float,
                           get_cmd=f"SENS:{channel}:NPLC?",
                           set_cmd=f"SENS:{channel}:NPLC {{:.4f}}",
                           vals=Numbers(0.0005, 12)
                           )

    @staticmethod
    def _get_unit(channel: str) -> str:
        channel_units = {'VOLT': 'V', 'CURR': 'A', 'RES': 'Ohm', 'FRES': 'Ohm'}
        return channel_units[channel]

    @staticmethod
    def _get_label(channel: str) -> str:
        channel_labels = {'VOLT': 'Measured voltage.',
                          'CURR': 'Measured current.',
                          'RES': 'Measured resistance',
                          'FRES': 'Measured resistance (4w)'}
        return channel_labels[channel]


class Keithley_6500(VisaInstrument):

    def __init__(self, name: str,
                 address: str,
                 terminator="\n",
                 **kwargs):
        super().__init__(name, address, terminator=terminator, **kwargs)

        for sense in ['VOLT', 'CURR', 'RES', 'FRES']:
            channel = Keithley_Sense(self, sense.lower(), sense)
            self.add_submodule(sense.lower(), channel)

        self.connect_message()
