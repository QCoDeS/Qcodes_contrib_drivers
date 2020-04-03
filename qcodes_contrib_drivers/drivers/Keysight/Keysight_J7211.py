from qcodes.instrument.visa import VisaInstrument
from qcodes.utils.validators import Ints
from typing import Optional


class Keysight_J7211(VisaInstrument):
    r"""
    Qcodes driver for the Keysight J7211 Attenuation Control Unit.
    Tested with J7211B.

    Args:
        name: Instrument name
        address: Address or alias of instrument
        attenuation: Optional attenuation level to set on startup
    """

    def __init__(self, name: str, address: str,
                 attenuation: Optional[int] = None, **kwargs):
        super().__init__(name=name, address=address, terminator='\r', **kwargs)

        self.add_parameter('attenuation', unit='dB',
                           set_cmd='ATT {:03.0f}',
                           get_cmd='ATT?',
                           get_parser=int)

        self.connect_message()

        model = self.IDN()['model']

        if model in ["J7211A", "J7211B"]:
            self.attenuation.vals = Ints(0, 120)
        elif model in ["J7211C"]:
            self.attenuation.vals = Ints(0, 100)
        else:
            raise RuntimeError("Model {} is not supported.".format(model))

        if attenuation is not None:
            self.attenuation(attenuation)
