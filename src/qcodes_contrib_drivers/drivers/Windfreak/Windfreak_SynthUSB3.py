"""Driver for Windfreak SynthUSB3 signal generator

Written by Edward Laird (http://wp.lancs.ac.uk/laird-group/).

A documentation notebook is in the docs/examples/ directory.
"""

from typing import TYPE_CHECKING

from qcodes import validators as vals
from qcodes.instrument import VisaInstrument, VisaInstrumentKWArgs
from qcodes.parameters import Parameter

if TYPE_CHECKING:
    from typing_extensions import Unpack

class WindfreakSynthUSB3(VisaInstrument):
    """
    QCodes driver for the Windfreak SynthUSB3 signal generator.

    """

    default_terminator = ""

    def __init__(
        self, name: str, address: str, **kwargs: "Unpack[VisaInstrumentKWArgs]"
    ):
        super().__init__(name, address, **kwargs)

        self.add_parameter('identify',
            label='Identify',
            get_cmd='+-',
            get_parser=str.rstrip
            )
        """Send model and serial number."""

        self.add_parameter('output',
            label='Output state',
            set_cmd='E{}',
            get_cmd='E?',
            val_mapping={
                   'OFF': 0,
                   'ON': 1,
               },
            vals=vals.Enum('OFF', 'ON')
            )
        """Turn the output on or off. Be careful using this command; communication sometimes hangs up if you set parameters with the output off, or set the ouptut on twice in a row."""

        self.frequency = Parameter(
            "frequency",
            unit="MHz",
            set_cmd="f{:.7f}",
            get_cmd="f?",
            instrument=self,
            get_parser=float,
        )
        """Control the carrier frequency"""

        self.level = Parameter(
            "level",
            unit="dBm",
            set_cmd="W{:.2f}",
            get_cmd="W?",
            instrument=self,
            get_parser=float,
        )
        """Control the carrier level"""

#        self.connect_message(idn_param="+")   #I can't make this work, don't know why.
