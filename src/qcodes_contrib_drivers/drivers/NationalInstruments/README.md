# Drivers for National Insturments devices

NI device drivers work mainly by wrapping DLLs. For some DLLs, there exist
official Python bindings (e.g.
[nimi-python](https://github.com/ni/nimi-python),
[nidaqmx-python](https://github.com/ni/nidaqmx-python),
[nifpga-python](https://github.com/ni/nifpga-python), etc.). For those that do
not have official bindings, you can use the `NIDLLInstrment` class to wrap DLL
functions relatively easily, see below.

## Manually wrapping DLL drivers

Based on observing the C API of the NI-RFSG and NI-Sync drivers, it seems that
the NI DLL drivers have some common features. All DLL C functions are of the
form `ni<drivername>_<functionname>`. For example, for RFSG, functions are of
the form `niRFSG_Initiate`, `niRFSG_Abort` etc. Furthermore, some functions
exist for all drivers with the same signature: e.g. `ni<drivername>_init`,
`ni<drivername>_reset`, `ni<drivername>_close`, and, importantly,
`ni<drivername>_error_message`.

The `NIDLLWrapper` class keeps track of wrapped library functions for a given
driver, and provides the handy `wrap_dll_function_checked` function to wrap
additional functions. `wrap_dll_function_checked` wraps a given function so
that if the DLL function results in an error, the corresponding
`ni<drivername>_error_message` gets automatically called and converted to a
Python exception or warning. Additionally, the `NIDLLWrapper` class already
wraps common functions such as `ni<drivername>_init` and
`ni<drivername>_close`.

Creating a Qcodes `Instrument` that wraps an NI DLL driver amounts to
subclassing `NIDLLInstrment`, wrapping the DLL functions needed for the
required functionality with `wrap_dll_function_checked`, and adding the
corresponding parameters with `add_parameter` as usual. A subclass of the
`NIDLLInstrment` should provide the "prefix", i.e. `ni<drivername>` used for
the library DLL functions, for example for RFSG, the prefix is `niRFSG`.

A `NIDLLInstrment` subclass should have entirely pythonic methods that take and
return Python types, and shouldn't have to deal with `ctypes` directly
(although NI visa types such as `ViInt32` are needed for wrapping the library
functions). On the other hand, `NIDLLWrapper` is a lower-level class that has
nothing to do with `qcodes.Instrument`, and doesn't hold a reference to a
device session. Instead, the session should be provided as a parameter when
calling a library function.
