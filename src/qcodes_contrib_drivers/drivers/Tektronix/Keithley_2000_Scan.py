from functools import partial
from typing import TYPE_CHECKING

from qcodes.instrument import InstrumentChannel

if TYPE_CHECKING:
    from .Keithley_6500 import Keithley_6500


class Keithley_2000_Scan_Channel(InstrumentChannel):
    """
    This is the qcodes driver for a channel of the 2000-SCAN scanner card.
    """
    def __init__(self, dmm: "Keithley_6500", channel: int, **kwargs) -> None:
        """
        Initialize instance of scanner card Keithley 2000-SCAN
        Args:
            dmm: Instance of digital multimeter Keithley6500 containing the scanner card
            channel: Channel number
            **kwargs: Keyword arguments to pass to __init__ function of InstrumentChannel class
        """
        super().__init__(dmm, f"ch{channel}", **kwargs)
        self.channel = channel
        self.dmm = dmm

        self.add_parameter('resistance',
                           unit='Ohm',
                           label=f'Resistance CH{self.channel}',
                           get_parser=float,
                           get_cmd=partial(self._measure, 'RES'))

        self.add_parameter('resistance_4w',
                           unit='Ohm',
                           label=f'Resistance (4-wire) CH{self.channel}',
                           get_parser=float,
                           get_cmd=partial(self._measure, 'FRES'))

        self.add_parameter('voltage_dc',
                           unit='V',
                           label=f'DC Voltage CH{self.channel}',
                           get_parser=float,
                           get_cmd=partial(self._measure, 'VOLT'))

        self.add_parameter('current_dc',
                           unit='A',
                           label=f'DC current CH{self.channel}',
                           get_parser=float,
                           get_cmd=partial(self._measure, 'CURR'))

    def _measure(self, quantity: str) -> str:
        """
        Measure given quantity at rear terminal of the instrument. Only perform measurement if rear terminal is
        active. Send SCPI command to measure and read out given quantity.
        Args:
            quantity: Quantity to be measured

        Returns: Measurement result

        """
        if self.dmm.active_terminal.get() == 'REAR':
            self.write(f"SENS:FUNC '{quantity}', (@{self.channel:d})")
            self.write(f"ROUT:CLOS (@{self.channel:d})")
            return self.ask("READ?")
        else:
            raise RuntimeError("Front terminal is active instead of rear terminal.")
