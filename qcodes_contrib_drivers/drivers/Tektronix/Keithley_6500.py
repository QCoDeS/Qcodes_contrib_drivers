from qcodes.instrument.visa import VisaInstrument
from qcodes.instrument import InstrumentChannel
from qcodes.utils.validators import Numbers
from functools import partial
from .Keithley_2000_Scan import Keithley_2000_Scan_Channel


class Keithley_Sense(InstrumentChannel):
    """
    This is the class for a measurement channel, i.e. the quantity to be measured (e.g. resistance, voltage).
    """
    def __init__(self, parent: VisaInstrument, name: str, channel: str) -> None:
        """

        Args:
            parent: VisaInstrument instance of the Keithley Digital Multimeter
            name: Channel name (e.g. 'CH1')
            channel: Name of the quantity to measure (e.g. 'VOLT' for DC voltage measurement)
        """
        valid_channels = ['VOLT', 'CURR', 'RES', 'FRES']
        if channel.upper() not in valid_channels:
            raise ValueError(f"Channel must be one of the following: {', '.join(valid_channels)}")
        super().__init__(parent, name)

        self.add_parameter('measure',
                           unit=partial(self._get_unit, channel),
                           label=partial(self._get_label, channel),
                           get_parser=float,
                           get_cmd=partial(self.parent._measure, channel),
                           docstring="Measure value of chosen quantity (Current/Voltage/Resistance)."
                           )

        self.add_parameter('nplc',
                           label='NPLC',
                           get_parser=float,
                           get_cmd=f"SENS:{channel}:NPLC?",
                           set_cmd=f"SENS:{channel}:NPLC {{:.4f}}",
                           vals=Numbers(0.0005, 12),
                           docstring="Integration rate (Number of Power Line Cycles)"
                           )

    @staticmethod
    def _get_unit(quantity: str) -> str:
        """

        Args:
            quantity: Quantity to be measured

        Returns: Corresponding unit string

        """
        channel_units = {'VOLT': 'V', 'CURR': 'A', 'RES': 'Ohm', 'FRES': 'Ohm'}
        return channel_units[quantity]

    @staticmethod
    def _get_label(quantity: str) -> str:
        """

        Args:
            quantity: Quantity to be measured

        Returns: Corresponding parameter label

        """
        channel_labels = {'VOLT': 'Measured voltage.',
                          'CURR': 'Measured current.',
                          'RES': 'Measured resistance',
                          'FRES': 'Measured resistance (4w)'}
        return channel_labels[quantity]


class Keithley_6500(VisaInstrument):
    """
    This is the qcodes driver for a Keithley DMM6500 digital multimeter.
    """
    def __init__(self, name: str,
                 address: str,
                 terminator="\n",
                 **kwargs):
        """
        Initialize instance of digital multimeter Keithley6500. Check if scanner card is inserted.
        Args:
            name: Name of instrument
            address: Address of instrument
            terminator: Termination character for SCPI commands
            **kwargs: Keyword arguments to pass to __init__ function of VisaInstrument class
        """
        super().__init__(name, address, terminator=terminator, **kwargs)
        for quantity in ['VOLT', 'CURR', 'RES', 'FRES']:
            channel = Keithley_Sense(self, quantity.lower(), quantity)
            self.add_submodule(quantity.lower(), channel)

        self.add_parameter('active_terminal',
                           label='active terminal',
                           get_cmd="ROUTe:TERMinals?",
                           docstring="Active terminal of instrument. Can only be switched via knob on front panel.")

        self.add_parameter('resistance',
                           unit='Ohm',
                           label='Measured resistance',
                           get_parser=float,
                           get_cmd=partial(self._measure, 'RES'),
                           )

        self.add_parameter('resistance_4w',
                           unit='Ohm',
                           label='Measured resistance',
                           get_parser=float,
                           get_cmd=partial(self._measure, 'FRES')
                           )

        self.add_parameter('voltage_dc',
                           unit='V',
                           label='Measured DC voltage',
                           get_parser=float,
                           get_cmd=partial(self._measure, 'VOLT')
                           )

        self.add_parameter('current_dc',
                           unit='A',
                           label='Measured DC current',
                           get_parser=float,
                           get_cmd=partial(self._measure, 'CURR')
                           )

        self.connect_message()

        # check if scanner card is connected
        # If no scanner card is connected, the query below returns "Empty Slot".
        # For the Scanner Card 2000-SCAN used for development of this driver the output was
        # "2000,10-Chan Mux,0.0.0a,00000000".
        scan_idn_msg = self.ask(":SYSTem:CARD1:IDN?")
        if scan_idn_msg != "Empty Slot":
            msg_parts = scan_idn_msg.split(",")
            print(f"Scanner card {msg_parts[0]}-SCAN detected.")
            for ch_number in range(1, 11):
                scan_channel = Keithley_2000_Scan_Channel(self, ch_number)
                self.add_submodule(f"ch{ch_number:d}", scan_channel)

    # only measure if front terminal is active
    def _measure(self, quantity: str) -> str:
        """
        Measure given quantity at front terminal of the instrument. Only perform measurement if front terminal is
        active. Send SCPI command to measure and read out given quantity.
        Args:
            quantity: Quantity to be measured

        Returns: Measurement result

        """
        if self.active_terminal.get() == 'FRON':
            return self.ask(f"MEAS:{quantity}?")
        else:
            raise RuntimeError("Rear terminal is active instead of front terminal.")
