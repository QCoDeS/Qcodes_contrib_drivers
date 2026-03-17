from collections import namedtuple
import logging
from typing import TYPE_CHECKING

from qcodes.validators import Bool

if TYPE_CHECKING:
    from typing_extensions import (
        Unpack,
    )

from qcodes.instrument import (
    VisaInstrument,
    VisaInstrumentKWArgs,
)

OUT="out"
IN="in"

log = logging.getLogger(__name__)


class PicoPST(VisaInstrument):
    """
    QCoDeS instrument driver for the Pico SCPI USBTMC LabTool (PST)
    ===============================================================

    Documentation pending.
    """

    default_terminator = "\n"

    # Table of digital inputs/outputs parameters
    DigitalIO = namedtuple("DigitalIO","dir, scpi_num, gp, pico_pin")
    _digital_ios = [
        DigitalIO(OUT, 0, 22, 29),
        DigitalIO(OUT, 1, 14, 19),
        DigitalIO(OUT, 2, 15, 20),
        DigitalIO(IN, 0, 20, 29),
        DigitalIO(IN, 1, 21, 27),
        DigitalIO(IN, 2, 27, 32),
    ]

    @staticmethod
    def _int_as_bool(*args, **kwargs) -> bool:
        return bool(int(*args, **kwargs))

    def __init__(
        self, name: str, address: str, **kwargs: "Unpack[VisaInstrumentKWArgs]"
    ):
        super().__init__(name, address, **kwargs)

        # Add digital IOs as parameters
        for io in self._digital_ios:
            parameter = self.add_parameter(
                f"{io.dir}put_gp{io.gp}",
                # Digital states are unitless
                unit="",
                set_cmd=f"DIGI:{io.dir.upper()}P{io.scpi_num} {{:d}}",
                get_cmd=f"DIGI:{io.dir.upper()}P{io.scpi_num}?",
                vals=Bool(),
                get_parser=self._int_as_bool,
                docstring=f"Turns GP{io.gp} (Pico pin {io.pico_pin}) on or off" if io.dir == IN else "Indicates whether GP20 (Pico pin 26) is on or off"
            )
            parameter.__doc__= f"Digital {io.dir.upper()}put GP{io.gp} (Pico pin {io.pico_pin})"
            setattr(self, f"output_{io.gp}", parameter)

        # Inputs must be enabled before they are used
        self.inputs_enabled = self.add_parameter(
            "inputs_enabled",
            unit="",
            set_cmd="STAT:OPER:DIGI:INP:ENAB {:d}",
            get_cmd="STAT:OPER:DIGI:INP:ENAB?",
            vals=Bool(),
            get_parser=self._int_as_bool,
            docstring="Enables or disables the use of inputs"
        )
        """Inputs Enabled"""

        # Other functions exist but are not implemented here.

        self.connect_message()
