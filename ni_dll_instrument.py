"""
This module contains a small class that mixes features that are common to all
libraries in the NIDLLWrapper class with qcodes.Instrument.
"""

from functools import partial
from qcodes import Instrument
from .dll_wrapper import NIDLLWrapper, AttributeWrapper


class NIDLLInstrument(Instrument):
    """
    Common base class for QCoDeS instrument that holds a refence to an NI
    driver DLL wrapper object, as well as an instrument handle (ViSession). It
    handles calling the DLL methods and has some common methods implemented,
    such as init, close and get_attribute.

    Args:
        name: Name for this instrument
        resource_name: Identifier for this instrument in NI MAX.
        dll_path: path to the library DLL.
        lib_prefix: the prefix of the function names in the library (see
            NIDLLWrapper)
        id_query: whether to perform an ID query on initialization
        reset_device: whether to reset the device on initialization
    """

    def __init__(self, name: str, resource_name: str, dll_path: str,
                 lib_prefix: str, id_query: bool = False,
                 reset_device: bool = False, **kwargs):

        super().__init__(name, **kwargs)

        self.resource_name = resource_name

        self.wrapper = NIDLLWrapper(dll_path=dll_path, lib_prefix=lib_prefix)

        self._handle = self.wrapper.init(self.resource_name,
                                         id_query=id_query,
                                         reset_device=reset_device)

    def reset(self):
        self.wrapper.reset(self._handle)

    def get_attribute(self, attr: AttributeWrapper):
        return self.wrapper.get_attribute(self._handle, attr)

    def close(self):
        if getattr(self, "_handle", None):
            self.wrapper.close(self._handle)
        super().close()
