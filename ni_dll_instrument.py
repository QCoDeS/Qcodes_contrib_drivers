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

    # for convenience
    #def wrap_dll_function(self, *args, **kwargs):
    #    return self.wrapper.wrap_dll_function(*args, **kwargs)

    #def wrap_dll_function_checked(self, *args, **kwargs):
    #    return self.wrapper.wrap_dll_function_checked(*args, **kwargs)

    # attempt at directly getting attributes from DLL, conflicts with qcodes
    # should probably be done with DelegateAttributes
    #def __getattr__(self, name):
    #    """
    #    If the attribute is not a QCoDeS parameter, try to call function that
    #    from the DLL wrapper class, and automatically prepend self._handle to
    #    argument list.
    #    """
    #    try:
    #        return super().__getattr__(name)

    #    except AttributeError:
    #        print(name)
    #        print(self.wrapper._wrapped_functions)
    #        #try:
    #        #    attr = getattr(self.wrapper, name)
    #        #    print(attr)
    #        #    if (name in self.wrapper._wrapped_functions and
    #        #        attr.):
    #        #        attr = partial(attr, self._handle)
    #        #    return attr
    #        try:
    #            if name in self.wrapper._wrapped_functions:
    #                attr = getattr(self.wrapper, name)

    #                # automatically apply handle if applicable
    #                if (attr.argnames[0] == "vi" and
    #                    attr.argtypes[0] == ViSession):

    #                    attr = partial(attr, self._handle)

    #                return attr

    #            else:
    #                raise AttributeError

    #        except AttributeError as e:
    #            raise AttributeError((f"'{self.__class__.__name__}' or its"
    #                                  f" wrapped library has no attribute"
    #                                  f" '{name}'"))

    def get_attribute(self, attr: AttributeWrapper):
        return self.wrapper.get_attribute(self._handle, attr)

    def close(self):
        if getattr(self, "_handle", None):
            self.wrapper.close(self._handle)
        super().close()
