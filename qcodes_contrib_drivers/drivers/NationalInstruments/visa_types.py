import ctypes

"""
Visa types used by NI C API DLLs.
"""

ViChar = ctypes.c_char
ViStatus = ctypes.c_long
ViRsrc = ctypes.c_char_p
ViInt32 = ctypes.c_int32
ViString = ctypes.c_char_p
ViConstString = ViString
ViSession = ctypes.c_ulong
ViBoolean = ctypes.c_ushort
ViAttr = ctypes.c_long
ViReal64 = ctypes.c_double

VI_NULL = 0
