import ctypes

"""
Visa types used by NI C API DLLs.
"""

ViStatus = ctypes.c_long
ViRsrc = ctypes.c_char_p
ViString = ctypes.c_char_p
ViConstString = ViString
ViSession = ctypes.c_ulong
ViBoolean = ctypes.c_ushort
ViAttr = ctypes.c_long
ViReal64 = ctypes.c_double

VI_NULL = 0
