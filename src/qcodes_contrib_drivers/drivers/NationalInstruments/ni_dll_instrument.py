"""
This module contains a small class that mixes features that are common to all
libraries in the ``NIDLLWrapper`` class with ``qcodes.Instrument``.
"""

from functools import partial
from typing import Any
from qcodes import Instrument
from .dll_wrapper import NIDLLWrapper, AttributeWrapper
from .visa_types import ViSession


class NIDLLInstrument(Instrument):
    """
    Common base class for QCoDeS instruments based on NI DLL drivers, when an
    official NI Python driver (such as ``nidaqmx`` or ``nifpga``) is not
    available. It holds a refence to an NI DLL wrapper object, as well as an
    instrument handle (``ViSession``). It handles calling the DLL methods and
    has some common methods implemented, such as ``init``, ``close`` and
    ``get_attribute``.

    Args:
        name: Name for this instrument
        resource: Identifier for this instrument in NI MAX.
        dll_path: path to the library DLL.
        lib_prefix: the prefix of the function names in the library (see
            ``NIDLLWrapper``)
        id_query: whether to perform an ID query on initialization
        reset_device: whether to reset the device on initialization
    """

    def __init__(self, name: str, resource: str, dll_path: str,
                 lib_prefix: str, id_query: bool = False,
                 reset_device: bool = False, **kwargs):

        super().__init__(name, **kwargs)

        self.resource = resource

        self.wrapper = NIDLLWrapper(dll_path=dll_path, lib_prefix=lib_prefix)

        self._handle = self.init(id_query=id_query,
                                 reset_device=reset_device)

    def init(self, id_query: bool = False,
             reset_device: bool = False) -> ViSession:
        """
        Call the wrapped init function from the library

        Args:
            id_query: whether to perform an ID query
            reset_device: whether to reset the device

        Returns:
            the ViSession handle of the initialized device
        """
        return self.wrapper.init(self.resource, id_query=id_query,
                                 reset_device=reset_device)

    def reset(self):
        self.wrapper.reset(self._handle)

    def get_attribute(self, attr: AttributeWrapper) -> Any:
        return self.wrapper.get_attribute(self._handle, attr)

    def set_attribute(self, attr: AttributeWrapper, set_value: Any):
        self.wrapper.set_attribute(self._handle, attr, set_value)

    def close(self):
        if getattr(self, "_handle", None):
            self.wrapper.close(self._handle)
        super().close()
