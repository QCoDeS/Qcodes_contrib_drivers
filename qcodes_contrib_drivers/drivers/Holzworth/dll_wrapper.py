import ctypes
from typing import NamedTuple, List, Any

# 256 bytes should be enough, according to the documentation
STRING_BUFFER_SIZE = 257


def c_str(s: str) -> bytes: return bytes(s, "ascii")


class NamedArgType(NamedTuple):
    """
    Struct for associating a name with an argument type for DLL function
    signatures.
    """
    name: str
    argtype: Any

class HOLZWORTHDLLWrapper(object):
    """
    """

    def __init__(self, dll_path: str):
        self._dll = ctypes.cdll.LoadLibrary(dll_path)

        self.usb_comm_write = self.wrap_dll_function(
                name_in_library="usbCommWrite",
                argtypes=[
                    NamedArgType("serialnum", ctypes.c_char_p),
                    NamedArgType("pBuf", ctypes.c_char_p)
                    ]
                )

    def wrap_dll_function(self, name_in_library: str,
                          argtypes: List[NamedArgType],
                          restype: Any=ctypes.c_char_p,
                          ) -> Any:
        """
        """

        func = getattr(self._dll, name_in_library)
        func.restype = restype
        func.argtypes = [a.argtype for a in argtypes]
        func.argnames = [a.name for a in argtypes]  # just in case

        return func

    def write_command(self, serial_number: str, command: str):
        """
        """

        rtn = self.usb_comm_write(c_str(serial_number), c_str(command))
        return rtn.decode("utf_8")
