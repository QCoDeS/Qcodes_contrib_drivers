from functools import partial

from qcodes.instrument import InstrumentChannel


class Keithley_2000_Scan_Channel(InstrumentChannel):
    def __init__(self, dmm, channel: int, **kwargs):
        super().__init__(dmm, f"ch{channel}", **kwargs)
        self.channel = channel
        self.dmm = dmm

        self.add_parameter('resistance',
                           unit='Ohm',
                           label=f'Resistance CH{self.channel}',
                           get_parser=float,
                           get_cmd=partial(self.measure, 'RES'))

        self.add_parameter('resistance_4w',
                           unit='Ohm',
                           label=f'Resistance (4-wire) CH{self.channel}',
                           get_parser=float,
                           get_cmd=partial(self.measure, 'FRES'))

        self.add_parameter('voltage_dc',
                           unit='V',
                           label=f'DC Voltage CH{self.channel}',
                           get_parser=float,
                           get_cmd=partial(self.measure, 'VOLT'))

        self.add_parameter('current_dc',
                           unit='A',
                           label=f'DC current CH{self.channel}',
                           get_parser=float,
                           get_cmd=partial(self.measure, 'CURR'))

    def measure(self, measurement_func: str) -> str:
        if self.dmm.active_terminal.get() == 'REAR':
            self.write(f"SENS:FUNC '{measurement_func}', (@{self.channel:d})")
            self.write(f"ROUT:CLOS (@{self.channel:d})")
            return self.ask("READ?")
        else:
            print("WARNING: Front terminal is active instead of rear terminal.")
            return "nan"
