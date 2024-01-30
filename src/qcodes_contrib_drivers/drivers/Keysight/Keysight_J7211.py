from qcodes.instrument.visa import VisaInstrument
from qcodes.utils.validators import Ints
from typing import Optional


class Keysight_J7211(VisaInstrument):
    r"""
    Qcodes driver for the Keysight J7211 Attenuation Control Unit.
    Tested with J7211B.

    Args:
        name: Instrument name
        address: Address or VISA alias of instrument
        attenuation: Optional attenuation level (in dB) to set on startup
        terminator: Termination character in VISA communication.
    """

    def __init__(self, name: str, address: str,
                 attenuation: Optional[int] = None,
                 terminator="\r", **kwargs):
        super().__init__(name=name, address=address,
                         terminator=terminator, **kwargs)

        model = self.IDN()['model']
        if model in ["J7211A", "J7211B"]:
            vals = Ints(0, 120)
        elif model in ["J7211C"]:
            vals = Ints(0, 100)
        else:
            raise RuntimeError(f"Model {model} is not supported.")

        self.add_parameter('attenuation', unit='dB',
                           set_cmd='ATT {:03.0f}',
                           get_cmd='ATT?',
                           get_parser=int,
                           vals=vals,
                           initial_value=attenuation)

        self.connect_message()
