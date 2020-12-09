from qcodes import VisaInstrument
from qcodes import Instrument
from qcodes.instrument.channel import InstrumentChannel


class E36313AChannel(InstrumentChannel):
    """

    """
    def __init__(self, parent: Instrument, name: str, chan: int) -> None:
        """
        Args:
            parent: The instrument to which the channel is
            attached.
            name: The name of the channel
            chan: The number of the channel in question (1-3)
        """
        # Sanity Check inputs
        if name not in ['ch1', 'ch2', 'ch3']:
            raise ValueError("Invalid Channel: {}, expected 'ch1' or 'ch2' or 'ch3'"
                             .format(name))
        if chan not in [1, 2, 3]:
            raise ValueError("Invalid Channel: {}, expected '1' or '2' or '3'"
                             .format(chan))

        super().__init__(parent, name)

        self.add_parameter('source_voltage',
                           label="Channel {} Voltage".format(chan),
                           get_cmd='VOLT? (@{:d})'.format(chan),
                           get_parser=float,
                           set_cmd='VOLT {{:.8G}},(@{:d})'.format(chan),
                           unit='V')

        self.add_parameter('source_current',
                           label="Channel {} Current".format(chan),
                           get_cmd='CURR? (@{:d})'.format(chan),
                           get_parser=float,
                           set_cmd='CURR {{:.8G}},(@{:d})'.format(chan),
                           unit='A')

        self.add_parameter('voltage',
                           get_cmd='MEAS:VOLT? (@{:d})'.format(chan),
                           get_parser=float,
                           label='Channel {} Voltage'.format(chan),
                           unit='V')

        self.add_parameter('current',
                           get_cmd='MEAS:CURR? (@{:d})'.format(chan),
                           get_parser=float,
                           label='Channel {} Current'.format(chan),
                           unit='A')

        self.add_parameter('enable',
                           get_cmd='OUTP? (@{:d})'.format(chan),
                           set_cmd='OUTP {{:d}},(@{:d})'.format(chan),
                           val_mapping={'on':  1, 'off': 0})

        self.channel = chan


class E36313A(VisaInstrument):
    """
    This is the qcodes driver for the Keysight E36313A programmable DC power supply
    """
    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, terminator='\n', **kwargs)

        # The E36313A supports two channels
        for ch_num in [1, 2, 3]:
            ch_name = "ch{:d}".format(ch_num)
            channel = E36313AChannel(self, ch_name, ch_num)
            self.add_submodule(ch_name, channel)

        self.connect_message()

    def get_idn(self):
        IDN = self.ask_raw('*IDN?')
        vendor, model, serial, firmware = map(str.strip, IDN.split(','))
        IDN = {'vendor': vendor, 'model': model,
               'serial': serial, 'firmware': firmware}
        return IDN
