"""
This module has some convenience classes and functions for wrapping NI C API
calls. Modeled after the DLL calls in the NIMI-python library, see e.g.
https://github.com/ni/nimi-python/blob/master/generated/nitclk/nitclk/_library.py
"""

import ctypes
from ctypes import POINTER
from typing import NamedTuple, Optional, List, Any, Callable
import warnings
from dataclasses import dataclass
from .visa_types import (
    ViChar, ViStatus, ViRsrc, ViInt32, ViString, ViSession, ViBoolean, ViAttr,
    ViChar, ViReal64, VI_NULL
)

# 256 bytes should be enough, according to the documentation
STRING_BUFFER_SIZE = 257


def c_str(s: str) -> bytes: return bytes(s, "ascii")


@dataclass
class AttributeWrapper(object):
    """
    Struct to associate a data type to a numeric constant (i.e. attribute)
    defined in a NI DLL library. ``dtype`` should be one of the types defined
    in the ``visa_types`` module. Here, ``value`` means the same as the
    attributeID in the DLL documentation.
    """
    value: ViAttr
    dtype: Any


class NamedArgType(NamedTuple):
    """
    Struct for associating a name with an argument type for DLL function
    signatures.
    """
    name: str
    argtype: Any


class NIDLLWrapper(object):
    """
    This class provides convenience functions for wrapping and checking a DLL
    function call, as well as some premade pythonic wrapper functinos for
    common library functions such as libName_error_message, libName_init/close
    and libName_GetAttribute (e.g. niRFSG_init or niSync_init). Other functions
    should be wrapped by a library-specific class by calling
    ``wrap_dll_function_checked``. See the NI_RFSG driver for a concrete
    example.

    Args:
        dll_path: path to the DLL file containing the library
        lib_prefix: All function names in the library start with this. For
            example, for NI-RFSG, where function names are of the form
            niRFSG_FunctionName, ``lib_prefix`` should be 'niRFSG'.
    """

    def __init__(self, dll_path: str, lib_prefix: str):
        self._dll = ctypes.cdll.LoadLibrary(dll_path)
        self._lib_prefix = lib_prefix

        self._dtype_map = {
                ViBoolean: "ViBoolean",
                ViInt32: "ViInt32",
                ViReal64: "ViReal64",
                ViString: "ViString"
        }

        # wrap standard functions that are the same in all libraries

        # note: self.error_messsage is a convenience wrapper around this, with
        # a different signature
        self._error_message = self.wrap_dll_function(
                name_in_library="error_message",
                argtypes=[
                    NamedArgType("vi", ViSession),
                    NamedArgType("errorCode", ViStatus),
                    NamedArgType("errorMessage", POINTER(ViChar)),
                    ]
                )

        # this is wrapped in self.init with a different signature
        self._init = self.wrap_dll_function_checked(
                name_in_library="init",
                argtypes=[
                    NamedArgType("resourceName", ViRsrc),
                    NamedArgType("idQuery", ViBoolean),
                    NamedArgType("resetDevice", ViBoolean),
                    ]
                )

        # no special name is needed, the signature is the same
        self.reset = self.wrap_dll_function_checked(
                name_in_library="reset",
                argtypes=[NamedArgType("vi", ViSession)]
                )

        self.close = self.wrap_dll_function_checked(
                name_in_library="close",
                argtypes=[NamedArgType("vi", ViSession)]
                )

        # wrap GetAttribute<DataType> functions (see get_attribute method)
        for dtype, dtype_name in self._dtype_map.items():

            # argtypes for the GetAttribute<DataType> functions
            getter_argtypes = [
                    NamedArgType("vi", ViSession),
                    NamedArgType("channelName", ViString),
                    NamedArgType("attributeID", ViAttr),
                    NamedArgType("attributeValue", POINTER(dtype))
            ]

            # the argtypes for the corresponding SetAttribute<DataType>
            # functions. note that the signature for SetAttributeViString is
            # the same as for the other types even though GetAttributeViString
            # has a unique signature
            setter_argtypes = getter_argtypes.copy()

            if dtype == ViString:
                # replace last argument
                getter_argtypes.pop()
                getter_argtypes.append(NamedArgType("bufferSize", ViInt32))
                # ViString is already a pointer, so no POINTER() here
                getter_argtypes.append(NamedArgType("attributeValue", dtype))

            getter_name = f"GetAttribute{dtype_name}"
            getter_func = self.wrap_dll_function_checked(
                    getter_name,
                    argtypes=getter_argtypes)
            setattr(self, getter_name, getter_func)

            setter_argtypes[-1] = NamedArgType("attributeValue", dtype)

            setter_name = f"SetAttribute{dtype_name}"
            setter_func = self.wrap_dll_function_checked(
                    setter_name,
                    argtypes=setter_argtypes)
            setattr(self, setter_name, setter_func)

    def wrap_dll_function(self, name_in_library: str,
                          argtypes: List[NamedArgType],
                          restype: Any = ViStatus,
                          ) -> Any:
        """
        Convenience method for wrapping a function in a NI C API.

        Args:
            name_in_library: The name of the function in the library (e.g.
                "niRFSG_init", or without the prefix, just "init")
            argtypes: list of ``NamedArgType`` tuples containing the names and
                types of the arguments of the function to be wrapped.
            restype: The return type of the library function (most likely
                ``ViStatus``).
        """

        if not name_in_library.startswith(self._lib_prefix):
            name_in_library = f"{self._lib_prefix}_{name_in_library}"

        # TODO( mgunyho ): thread lock? (see nimi-python link at top of file)
        func = getattr(self._dll, name_in_library)
        func.restype = restype
        func.argtypes = [a.argtype for a in argtypes]
        func.argnames = [a.name for a in argtypes]  # just in case

        return func

    def _check_error(self, error_code: int):
        """
        If the error code is nonzero, convert it to a string using
        ``self.error_message`` and raise an exception or issue a warning as
        appropriate. ``self.error_message`` must be initialized with
        ``wrap_dll_function`` before this method can be used.
        """
        if error_code != 0:
            msg = self.error_message(error_code=ViStatus(error_code))
            if error_code < 0:
                # negative error codes are errors
                raise RuntimeError(f"({error_code}) {msg}")
            else:
                warnings.warn(f"({error_code}) {msg}", RuntimeWarning,
                              stacklevel=3)


    def wrap_dll_function_checked(self, name_in_library: str,
                                  argtypes: List[NamedArgType]) -> Callable:
        """
        Same as ``wrap_dll_function``, but check the return value and convert
        it to a Python exception or warning if it is nonzero using
        ``self._check_error``. The arguments are the same as for
        ``wrap_dll_function``, except that ``restype`` is always ``ViStatus``.
        """

        func = self.wrap_dll_function(
                name_in_library=name_in_library,
                argtypes=argtypes,
                restype=ViStatus,
                )

        # see https://docs.python.org/3/library/ctypes.html#return-types
        func.restype = self._check_error

        return func

    def init(self, resource: str, id_query: bool = True,
             reset_device: bool = False) -> ViSession:
        """
        Convenience wrapper around libName_init (e.g. niRFSG_init). Returns the
        ViSession handle of the initialized session. The wrapped version of the
        actual DLL function is registered as self._init, see __init__. Note
        that this class is not responsible for storing the handle, it should
        be managed by the function or class that calls the functions wrapped by
        this class.

        Args:
            resource: the resource name of the device to initialize, as given
                by NI MAX.
            id_query: whether to perform an ID query on initialization
            reset_device: whether to reset the device during initialization
        Returns:
            the ViSession handle of the initialized device
        """
        session = ViSession()
        self._init(ViRsrc(c_str(resource)), id_query, reset_device,
                   ctypes.byref(session))
        return session

    def get_attribute(self, session: ViSession, attr: AttributeWrapper) -> Any:
        """
        Get an attribute with data type "DataType" by calling the appropriate
        "libName_GetAttribute<DataType>" function (for example
        niRFSG_GetAttributeViReal64 when ``lib_prefix`` is "niRFSG" and
        ``attr.dtype`` is ``ViReal64``).

        NOTE: channels are not implemented.
        """
        dtype = attr.dtype
        if dtype not in self._dtype_map:
            raise ValueError(f"get_attribute() not implemented for {dtype}")

        dtype_name = self._dtype_map[dtype]
        func = getattr(self, f"GetAttribute{dtype_name}")

        if dtype == ViString:
            res = ctypes.create_string_buffer(STRING_BUFFER_SIZE)
            func(session, b"", attr.value, STRING_BUFFER_SIZE, res)
            ret: Any = res.value.decode()
        else:
            res = dtype()
            func(session, b"", attr.value, ctypes.byref(res))
            ret = res.value

        return ret

    def set_attribute(self, session: ViSession, attr: AttributeWrapper,
                      set_value: Any) -> Any:
        """
        Set an attribute with data type "DataType" by calling the appropriate
        "libName_SetAttribute<DataType>" function (for example
        niRFSG_SetAttributeViReal64 when ``lib_prefix`` is "niRFSG" and
        ``attr.dtype`` is ``ViReal64``).

        NOTE: channels are not implemented.
        """
        dtype = attr.dtype
        if dtype not in self._dtype_map:
            raise ValueError(f"set_attribute() not implemented for {dtype}")

        dtype_name = self._dtype_map[dtype]
        func = getattr(self, f"SetAttribute{dtype_name}")

        if dtype == ViString:
            res = ctypes.create_string_buffer(STRING_BUFFER_SIZE)
            func(session, b"", attr.value, c_str(set_value), res)
            ret = res.value.decode()
        else:
            res = dtype()
            func(session, b"", attr.value, set_value)

    def error_message(self, session: Optional[ViSession] = None,
                      error_code: ViStatus = ViStatus(0)) -> str:
        """
        Convenience wrapper around libName_error_message (which is wrapped as
        self._error_message).
        """
        buf = ctypes.create_string_buffer(STRING_BUFFER_SIZE)
        self._error_message(session or VI_NULL, error_code, buf)
        return buf.value.decode()
