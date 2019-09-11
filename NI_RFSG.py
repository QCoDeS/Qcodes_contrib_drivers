import logging
from typing import Optional, List, Any
from functools import partial
from .visa_types import ViChar, ViString, ViAttr, ViSession, ViReal64
from .dll_wrapper import NIDLLWrapper, AttributeWrapper, NamedArgType

# constants used for querying attributes
NIRFSG_ATTR_FREQUENCY   = AttributeWrapper(ViAttr(1250001), ViReal64)
NIRFSG_ATTR_POWER_LEVEL = AttributeWrapper(ViAttr(1250002), ViReal64)

from qcodes.instrument.base import Instrument

logger = logging.getLogger(__name__)


class NationalInstruments_RFSG(Instrument):
    r"""
    This is the qcodes driver for National Instruments RF signal generator
    devices based on the NI-RFSG driver. As of NI-RFSG version 18.1, the
    supported devices are 
    PXI-5610,  PXI-5650,  PXI-5651,  PXI-5652,  PXI-5670,  PXI-5671, PXIe-5611,
    PXIe-5644, PXIe-5645, PXIe-5646, PXIe-5650, PXIe-5651, PXIe-5652,
    PXIe-5653, PXIe-5654, PXIe-5672, PXIe-5673, PXIe-5673E, PXIe-5820,
    PXIe-5840.

    Documentation for the NI-RFSG C API can be found by default in the 
    folder C:\Users\Public\Documents\National Instruments\NI-RFSG\Documentation.

    Only very basic functionality is implemented.

    Tested with 

    - PXIe-5654

    Args:
        name: Name for this instrument
        resource_name: Identifier for this instrument in NI MAX.
        dll_path: path to the NI-RFSG library DLL.
        id_query: whether to perform an ID query on initialization
        reset_device: whether to reset the device on initialization
    """

    # default DLL location
    dll_path = r"C:\Program Files\IVI Foundation\IVI\bin\NiRFSG_64.dll"
    # C:\Program Files (x86)\IVI Foundation\IVI\bin\NiRFSG.dll for 32-bit systems

    def __init__(self, name: str, resource_name: str,
                 dll_path: Optional[str] = None, 
                 id_query: bool = False, 
                 reset_device: bool = False,
                 **kwargs):
        super().__init__(name, **kwargs)

        dll_path = dll_path or self.dll_path
        self.resource_name = resource_name

        # _w is shorthand for wrapper
        self._w = NIDLLWrapper(dll_path = dll_path, lib_prefix = "niRFSG")

        self._handle = self._w.init(self.resource_name,
                                    id_query=id_query, 
                                    reset_device=reset_device)

        self._w.wrap_dll_function_checked(name_in_library = "Initiate",
                                          argtypes = [
                                              NamedArgType("vi", ViSession),
                                          ], apply_handle = self._handle)

        self._w.wrap_dll_function_checked(name_in_library = "Abort",
                                          argtypes = [
                                              NamedArgType("vi", ViSession),
                                          ], apply_handle = self._handle)

        self._w.wrap_dll_function_checked(name_in_library = "ConfigureRF",
                                          argtypes = [
                                              NamedArgType("vi", ViSession),
                                              NamedArgType("frequency",  ViReal64),
                                              NamedArgType("powerLevel", ViReal64),
                                          ], apply_handle =  self._handle)

        self.add_parameter("frequency", 
                           unit="Hz",
                           get_cmd=partial(self.get_attribute, 
                                           NIRFSG_ATTR_FREQUENCY),
                           set_cmd=self.set_frequency,
                           )

        self.add_parameter(name="power_level",
                           unit="dBm",
                           label="power level",
                           get_cmd=partial(self.get_attribute,
                                           NIRFSG_ATTR_POWER_LEVEL),
                           set_cmd=self.set_power_level,
                           )
                                           


    # TODO: move commmon functions (init, close, get_attribute) to separate NIDLLInstrument class, so no need for _handle everywhere
    def close(self):
        if getattr(self, "_handle", None):
            self._w.close(self._handle)
        super().close()

    def get_attribute(self, attr: AttributeWrapper):
        return self._w.get_attribute(self._handle, attr)

    def initiate(self):
        """
        Initiate signal generation. This causes the NI-RFSG device to leave
        the Configuration state.
        """
        self._w.Initiate()

    def abort(self):
        """
        Stop signal generation and return to the Configuration state.
        """
        self._w.Abort()

    def ConfigureRF(self, frequency: float, power_level: float, initiate: bool):
        """
        NI-RFSG devices can only set both the frequency and power level 
        simultatneously.

        NOTE: PXI-5670/5671 and PXIe-5672 devices must be in the Configuration
        state before calling this function (by calling niRFSG_Abort), that is 
        not implemented here.

        Args:
            frequency:
            power_level: power level in dBm
            initiate: if True, call self.initiate after configuring, which
                starts RF output
        """
        self._w.ConfigureRF(ViReal64(frequency), ViReal64(power_level))
        if initiate:
            self.initiate()

    def set_frequency(self, frequency: float, initiate: bool = False):
        power_level = self._w.get_attribute(self._handle, NIRFSG_ATTR_POWER_LEVEL)
        self.ConfigureRF(frequency, power_level, initiate)

    def set_power_level(self, power_level: float, initiate: bool = False):
        frequency = self._w.get_attribute(self._handle, NIRFSG_ATTR_FREQUENCY)
        self.ConfigureRF(frequency, power_level, initiate)

    #def ask(self, cmd: str) -> str:
    #    #TODO (IDN)
    #    pass

# class NationalInstruments_RFSG

# shorthand alias for the above
NI_RFSG = NationalInstruments_RFSG
