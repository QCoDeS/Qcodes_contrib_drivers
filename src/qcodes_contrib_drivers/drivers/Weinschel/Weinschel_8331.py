from typing import TYPE_CHECKING

from qcodes.validators import Enum
from qcodes.instrument import VisaInstrument, VisaInstrumentKWArgs
from qcodes.parameters import Parameter


if TYPE_CHECKING:
    from typing_extensions import Unpack

class Weinschel8331(VisaInstrument):
    """
    QCodes driver for Weinschel 8331 stepped attenuator.

    Weinschel is formerly known as Aeroflex/Weinschel

    Very similar to the Weinschel 8320 driver that comes built in with QCodes,
    but supports multiple channels. We don't know of a way to programmatically
    query the number of channels, so it must be provided as a parameter to the
    constructor. The attenuation parameters for each channel are called
    attenuation1, attenuation2, and so on.

    The default port for a socket connection is 10001.
    """

    default_terminator = "\r"

    def __init__(
        self,
        name: str,
        address: str,
        num_channels: int,
        **kwargs: "Unpack[VisaInstrumentKWArgs]",
    ):
        super().__init__(name=name, address=address, **kwargs)
        for n in range(1, num_channels + 1):
            setattr(
                self,
                f"attenuation{n}",
                Parameter(
                    f"attenuation{n}",
                    unit="dB",
                    set_cmd=f"ATTN {n} " + "{0:0=2d}",
                    get_cmd=f"ATTN? {n}",
                    vals=Enum(*range(0, 62 + 1, 2)),
                    instrument=self,
                    get_parser=int,
                    label=f"Channel {n} attenuation",
                    docstring=f"Control the attenuation of channel {n}",
                )
            )

        self.connect_message()
