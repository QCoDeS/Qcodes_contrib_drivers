from typing import Optional
from .RFSG import NI_RFSG
from qcodes.utils.validators import Numbers


class NationalInstruments_PXIe_5654(NI_RFSG):
    r"""
    Device-specific driver for the PXIe-5654 signal generator. See the NI_RFSG
    class for further details.

    Args:
        name: Name for this instrument
        resource: Identifier for this instrument in NI MAX.
        dll_path: path to the NI-RFSG library DLL. If not provided, use the
            default location,
            ``C:\Program Files\IVI Foundation\IVI\bin\NiRFSG_64.dll``.
        id_query: whether to perform an ID query on initialization
        reset_device: whether to reset the device on initialization
    """
    def __init__(self, name: str, resource: str,
                 dll_path: Optional[str] = None,
                 id_query: bool = False,
                 reset_device: bool = False,
                 **kwargs):

        super().__init__(name=name, resource=resource, dll_path=dll_path,
                         id_query=id_query, reset_device=reset_device,
                         **kwargs)

        # device-specific parameter limits
        self.frequency.vals = Numbers(250e3, 20e9)
        self.power_level.vals = Numbers(-7, 15)

        # check for amplitude extender and update power limits accordingly
        model = self.IDN()["model"]
        if "PXIe-5696" in model:
            self.power_level.vals = Numbers(-110, 24)


NI_PXIe_5654 = NationalInstruments_PXIe_5654
