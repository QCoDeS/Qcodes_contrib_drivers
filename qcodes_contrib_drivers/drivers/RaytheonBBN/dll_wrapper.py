import warnings
import numpy as np
import numpy.ctypeslib as npct
from ctypes import cdll
from typing import NamedTuple, Any, List, Optional
from ctypes import create_string_buffer, c_uint64, c_uint8, c_int, c_int16, c_char_p, POINTER, c_uint, c_char, c_float, c_uint32, byref, c_double
from dataclasses import dataclass

APS2_STATUS = c_int

def c_str(s: str) -> bytes: return bytes(s, "ascii")

status_dict = {
    0: "APS2_OK",
    -1: "APS2_UNKNOWN_ERROR",
    -2: "APS2_NO_DEVICE_FOUND",
    -3: "APS2_UNCONNECTED",
    -4: "APS2_RESET_TIMEOUT",
    -5: "APS2_FILELOG_ERROR",
    -6: "APS2_SEQFILE_FAIL",
    -7: "APS2_PLL_LOST_LOCK",
    -8: "APS2_MMCM_LOST_LOCK",
    -9: "APS2_UNKNOWN_RUN_MODE",
    -10: "APS2_FAILED_TO_CONNECT",
    -11: "APS2_INVALID_DAC",
    -12: "APS2_NO_SUCH_BITFILE",
    -13: "APS2_MAC_ADDR_VALIDATION_FAILURE",
    -14: "APS2_IP_ADDR_VALIDATION_FAILURE",
    -15: "APS2_DHCP_VALIDATION_FAILURE",
    -16: "APS2_RECEIVE_TIMEOUT",
    -17: "APS2_SOCKET_FAILURE",
    -18: "APS2_INVALID_IP_ADDR",
    -19: "APS2_COMMS_ERROR",
    -20: "APS2_UNALIGNED_MEMORY_ACCESS",
    -21: "APS2_ERPOM_ERASE_FAILURE",
    -22: "APS2_BITFILE_VALIDATION_FAILURE",
    -23: "APS2_BAD_PLL_VALUE",
}

reset_dict = {
    0: "RECONFIG_EPROM_USER",
    1: "RECONFIG_EPROM_BASE",
    2: "RESET_TCP"
}

class NamedArgType(NamedTuple):
    """
    Struct for associating a name with an argument type for DLL function
    signatures.
    """
    name: str
    argtype: Any

@dataclass
class AttributeWrapper(object):
    """
    Struct to associate a data type to a numeric constant.
    """
    name: str
    dtype: Any

class APS2DLLWrapper(object):
    def __init__(self, dll_path: str) -> None:
        self._dll = cdll.LoadLibrary(dll_path)

        self._dtype_map = {
                c_float: "c_float",
                c_int: "c_int",
                c_uint: "c_uint",
                c_double: "c_double"
        }

        self._error_message = self.wrap_dll_function(
                name_in_library="get_error_msg",
                argtypes=[NamedArgType("statusCode", APS2_STATUS)]
                )

        self._get_device_IPs = self.wrap_dll_function_checked(
            name_in_library="get_device_IPs",
            argtypes=[NamedArgType("deviceIP", POINTER(c_char_p))]
        )

        self._get_num_devices = self.wrap_dll_function_checked(
            name_in_library="get_numDevices",
            argtypes=[NamedArgType("numDevices", POINTER(c_uint))]
        )

        self._get_firmware_version = self.wrap_dll_function_checked(
            name_in_library="get_firmware_version",
            argtypes=[NamedArgType("deviceIP", c_char),
                      NamedArgType("version", c_uint32),
                      NamedArgType("git_sha1", c_uint32),
                      NamedArgType("build_timestamp", c_uint32),
                      NamedArgType("version_string", c_char)]
        )

        self._connect_APS = self.wrap_dll_function_checked(
            name_in_library="connect_APS",
            argtypes=[NamedArgType("deviceIP", c_char_p)]
        )

        self._disconnect_APS = self.wrap_dll_function_checked(
            name_in_library="disconnect_APS",
            argtypes=[NamedArgType("deviceIP", c_char_p)]
        )

        self._reset = self.wrap_dll_function_checked(
            name_in_library="reset",
            argtypes=[NamedArgType("deviceIP", c_char_p),
                      NamedArgType("resetMode", c_int)]
        )

        self._init = self.wrap_dll_function_checked(
            name_in_library="init_APS",
            argtypes=[NamedArgType("deviceIP", c_char_p),
                      NamedArgType("force", c_int)]
        )

        self._set_mixer_correction_matrix = self.wrap_dll_function_checked(
            name_in_library="set_mixer_correction_matrix",
            argtypes=[NamedArgType("deviceIP", c_char_p),
                      NamedArgType("matrix",npct.ndpointer(dtype=np.float32,
                                                           ndim=2,
                                                           flags='C_CONTIGUOUS'))]
        )

        self._get_mixer_correction_matrix = self.wrap_dll_function_checked(
            name_in_library="get_mixer_correction_matrix",
            argtypes=[NamedArgType("deviceIP", c_char_p),
                      NamedArgType("matrix", npct.ndpointer(dtype=np.float32,
                                                            ndim=2,
                                                            flags='C_CONTIGUOUS'))]
        )

        self._trigger = self.wrap_dll_function_checked(
            name_in_library="trigger",
            argtypes=[NamedArgType("deviceIP", c_char_p)]
        )

        self._set_waveform_float = self.wrap_dll_function_checked(
            name_in_library="set_waveform_float",
            argtypes=[NamedArgType("deviceIP", c_char_p),
                      NamedArgType("channel", c_int),
                      NamedArgType("data", POINTER(c_float)),
                      NamedArgType("numPts", c_int)]
        )

        self._set_waveform_int = self.wrap_dll_function_checked(
            name_in_library="set_waveform_int",
            argtypes=[NamedArgType("deviceIP", c_char_p),
                      NamedArgType("channel", c_int),
                      NamedArgType("data", POINTER(c_int16)),
                      NamedArgType("numPts", c_int)]
        )

        self._set_markers = self.wrap_dll_function_checked(
            name_in_library="set_markers",
            argtypes=[NamedArgType("deviceIP", c_char_p),
                      NamedArgType("channel", c_int),
                      NamedArgType("data", POINTER(c_uint8)),
                      NamedArgType("numPts", c_int)]
        )

        self._write_sequence = self.wrap_dll_function_checked(
            name_in_library="write_sequence",
            argtypes=[NamedArgType("deviceIP", c_char_p),
                      NamedArgType("data", POINTER(c_uint64)),
                      NamedArgType("numWords", c_uint32)]
        )

        self._set_run_mode = self.wrap_dll_function_checked(
            name_in_library="set_run_mode",
            argtypes=[NamedArgType("deviceIP", c_char_p),
                      NamedArgType("mode", c_int)]
        )

        self._load_sequence_file = self.wrap_dll_function_checked(
            name_in_library="load_sequence_file",
            argtypes=[NamedArgType("deviceIP", c_char_p),
                      NamedArgType("seqFile", c_char_p)]
        )

        self._clear_channel_data = self.wrap_dll_function_checked(
            name_in_library="clear_channel_data",
            argtypes=[NamedArgType("deviceIP", c_char_p)]
        )

        self._run = self.wrap_dll_function_checked(
            name_in_library="run",
            argtypes=[NamedArgType("deviceIP", c_char_p)]
        )

        self._stop = self.wrap_dll_function_checked(
            name_in_library="stop",
            argtypes=[NamedArgType("deviceIP", c_char_p)]
        )

    def wrap_dll_function(self, name_in_library: str,
                          argtypes: List[NamedArgType],
                          restype: Any = APS2_STATUS,
                          ) -> Any:
        """
        Convenience method for wrapping a function in libaps2 API.

        Args:
            name_in_library: The name of the function in the library
            argtypes: list of ``NamedArgType`` tuples containing the names and
                types of the arguments of the function to be wrapped.
            restype: The return type of the library function.
        """

        func = getattr(self._dll, name_in_library)
        func.restype = restype
        func.argtypes = [a.argtype for a in argtypes]
        func.argnames = [a.name for a in argtypes]

        return func

    def error_message(self, error_code: APS2_STATUS = APS2_STATUS(0)) -> str:
        """
        Convenience wrapper around get_error_message (which is wrapped as
        self._error_message).
        """
        code = self._error_message(error_code)
        return status_dict[code]

    def _check_error(self, error_code: int):
        """
        If the error code is nonzero, convert it to a string using
        ``self.error_message`` and raise an exception or issue a warning as
        appropriate. ``self.error_message`` must be initialized with
        ``wrap_dll_function`` before this method can be used.
        """
        if error_code != 0:
            msg = self.error_message(error_code=APS2_STATUS(error_code))
            if error_code < 0:
                # negative error codes are errors
                raise RuntimeError(f"({status_dict[error_code]}) {msg}")
            else:
                warnings.warn(f"({status_dict[error_code]}) {msg}", RuntimeWarning,
                              stacklevel=3)

    def wrap_dll_function_checked(self, name_in_library: str,
                                  argtypes: List[NamedArgType]):
        """
        Same as ``wrap_dll_function``, but check the return value and convert
        it to a Python exception or warning if it is nonzero using
        ``self._check_error``. The arguments are the same as for
        ``wrap_dll_function``.
        """

        func = self.wrap_dll_function(
                name_in_library=name_in_library,
                argtypes=argtypes,
                restype=c_int,
                )

        # see https://docs.python.org/3/library/ctypes.html#return-types
        func.restype = self._check_error

        return func

    def get_attribute(self, address: str, attr: AttributeWrapper, channel: Optional[int]=None) -> Any:
        """
        Get an attribute with data type "DataType"
        """
        dtype = attr.dtype

        func = self.wrap_dll_function_checked(
            name_in_library=f"get_{attr.name}",
            argtypes=[NamedArgType("deviceIP", c_char_p),]
        )

        if dtype == c_char_p:
            res = create_string_buffer(64)
            if channel is None:
                func(c_str(address), byref(res))
            else:
                func(c_str(address), c_int(channel), byref(res))
            ret = res.value.decode()
        else:
            res = dtype()
            if channel is None:
                func(c_str(address), byref(res))
            else:
                func(c_str(address), c_int(channel), byref(res))
            ret = res.value

        return ret

    def set_attribute(self, address: str, attr: AttributeWrapper, set_value: Any, channel: Optional[int]=None) -> Any:
        """
        Set an attribute with data type "DataType"
        """
        dtype = attr.dtype

        func = getattr(self._dll, f"set_{attr.name}")

        if dtype == c_char_p:
            if channel is None:
                func(c_str(address), c_str(set_value))
            else:
                func(c_str(address), c_int(channel), c_str(set_value))
        else:
            if channel is None:
                func(c_str(address), dtype(set_value))
            else:
                func(c_str(address), c_int(channel), dtype(set_value))
