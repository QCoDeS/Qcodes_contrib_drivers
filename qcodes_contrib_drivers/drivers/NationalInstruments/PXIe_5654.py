from .RFSG import NI_RFSG
from qcodes.utils.validators import Numbers

class NationalInstruments_PXIe_5654(NI_RFSG):
    """
    Device-specific driver for the PXIe-5654 signal generator.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # device-specific parameter limits
        self.frequency.vals = Numbers(250e3, 20e9)
        self.power_level.vals = Numbers(-7, 15)

        # check for amplitude extender and update power limits accordingly
        model = self.IDN()["model"]
        if "PXIe-5696" in model:
            self.power_level.vals = Numbers(-110, 24)


NI_PXIe_5654 = NationalInstruments_PXIe_5654
