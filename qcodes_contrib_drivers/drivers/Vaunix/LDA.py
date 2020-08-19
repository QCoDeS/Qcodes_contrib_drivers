r"""
This is the QCoDeS driver for Vaunix LDA digital attenuators. It requires the
DLL that comes with the instrument, ``VNX_atten64.dll`` and/or
``VNX_atten.dll``, for 64-bit Windows and 32-bit Windows, respectively. If the
instrument has more than one physical channel, ``InstrumentChannel`` s are
created for each one. If the instrument has only one physical channel, no
channels are created and the parameters will be assigned to this instrument
instead. The sweep profiles available in the API are not implemented.

Tested with 64-bit system and

- LDA-133
- LDA-802Q

"""

import logging
from typing import Optional, Dict, Callable, Union, cast
from functools import partial
from platform import architecture
import os
import sys
import ctypes
import time

from qcodes import Instrument, InstrumentChannel, Parameter
from qcodes.utils.validators import Numbers

logger = logging.getLogger(__name__)

class Vaunix_LDA(Instrument):
    dll_path = None

    def __init__(self, name: str,
                 serial_number: int,
                 dll_path: Optional[str] = None,
                 channel_names: Optional[Dict[int, str]] = None,
                 test_mode: bool = False,
                 **kwargs):
        r"""
        QCoDeS Instrument for Vaunix LDA digital attenuators.

        Args:
            name: Qcodes name for this instrument
            serial_number: Serial number of the instrument, used to identify
                it.
            dll_path: Look for the LDA DLLs in this directory. Sets the dll
                path as class attribute that is used for future instances for
                which ``dll_path`` is not given.
            channel_names: Optionally assign these names to the channels.
            test_mode: If True, simulates communication with an LDA-102
                (serial:55102). Does not communicate with physical devices. For
                testing purposes.
        """
        begin_time = time.time()

        self.serial_number = serial_number
        self.reference = None

        if channel_names is None:
            channel_names = {}

        self.dll = self._get_dll(dll_path)
        self.dll.fnLDA_SetTestMode(test_mode)  # Test API without communication

        # Find all Vaunix devices, init the one with matching serial number.
        num_devices = self.dll.fnLDA_GetNumDevices()
        device_IDs = ctypes.c_int * num_devices
        device_refs = device_IDs()
        self.dll.fnLDA_GetDevInfo(device_refs)
        devices = {self.dll.fnLDA_GetSerialNumber(ref): ref
                   for ref in device_refs}
        self.reference = devices.get(self.serial_number, "not found")
        if self.reference == "not found":
            raise ValueError(f"LDA with serial number {self.serial_number}"
                             f" was not found in the system. Found: {devices}")

        self.dll.fnLDA_InitDevice(self.reference)

        # call superclass init only after DLL has been successfully loaded
        super().__init__(name=name, **kwargs)

        num_channels = self.dll.fnLDA_GetNumChannels(self.reference)
        if num_channels == 1:
            # don't add Channel objects, add parameters directly instead
            _add_lda_parameters(self)
        else:
            for i in range(1, num_channels + 1):
                name = channel_names.get(i, f"ch{i}")
                ch = LdaChannel(parent=self, channel_number=i, name=name)
                self.add_submodule(name, ch)

        self.connect_message(begin_time=begin_time)

    def _get_dll(self, dll_path: Optional[str] = None) -> ctypes.CDLL:
        r"""
        Load correct DLL from ``dll_path`` based on bitness of the operating
        system.

        Args:
            dll_path: path to the directory that contains the Vaunix LDA DLL.
                By default, use class attribute ``Vaunix_LDA.dll_path``.
        """
        path = dll_path or Vaunix_LDA.dll_path
        if path is None:
            raise ValueError("DLL path for Vaunix LDA was not provided. "
                             "Either set ``Vaunix_LDA.dll_path`` or provide "
                             "it as an argument to the constructor.")

        if sys.platform != "win32":
            raise OSError(f"LDA is not supported on {sys.platform}.")
        bitness = architecture()[0]
        if "64bit" in bitness:
            full_path = os.path.join(path, "VNX_atten64")
        elif "32bit" in bitness:
            full_path = os.path.join(path, "VNX_atten")
        else:
            raise OSError(f"Unknown bitness of system: {bitness}")

        try:
            dll = ctypes.cdll.LoadLibrary(full_path)
        except OSError as e:
            # typeshead seems to be unaware that winerror is an attribute
            # under windows
            winerror = getattr(e, "winerror", None)
            if winerror is not None and winerror == 126:
                # 'the specified module could not be found'
                raise OSError(f"Could not find DLL at '{full_path}'")
            else:
                raise

        return dll

    def get_idn(self) -> Dict[str, Optional[str]]:

        buf = ctypes.create_string_buffer(300)
        self.dll.fnLDA_GetModelNameA(self.reference, buf)
        model = str(buf.value.decode())

        return {"vendor": "Vaunix",
                "model": model,
                "serial":  self.dll.fnLDA_GetSerialNumber(self.reference),
                "firmware": self.dll.fnLDA_GetDLLVersion(),
                }

    def close(self) -> None:
        if hasattr(self, "dll"):
            self.dll.fnLDA_CloseDevice(self.reference)
        super().close()

    def save_settings(self) -> None:
        """
        Save current settings to memory. Settings are automatically loaded
        during power on.
        """
        self.dll.fnLDA_SaveSettings(self.reference)


class LdaChannel(InstrumentChannel):
    """
    Channel corresponding to one input-output pair of the LDA digital
    attenuator.
    """
    def __init__(self, parent: Vaunix_LDA,
                 channel_number: int,
                 name: str):
        super().__init__(parent=parent, name=name)
        self.channel_number = channel_number
        _add_lda_parameters(self)


def _add_lda_parameters(inst: Union[Vaunix_LDA, LdaChannel]) -> None:
    """
    Helper function for adding parameters to either LDA root instrument,
    or channels inside it.
    Args:
        inst: the instrument or channel to add the parameters to.
    """
    root_instrument = cast(Vaunix_LDA, inst.root_instrument)
    inst.add_parameter("attenuation",
                       parameter_class=LdaAttenuation,
                       set_parser=float,
                       )
    wf_vals = LdaWorkingFrequency.get_validator(root_instrument)
    if wf_vals:
        inst.add_parameter("working_frequency",
                           parameter_class=LdaWorkingFrequency,
                           vals=wf_vals,
                           )


class LdaParameter(Parameter):
    scaling = 1.0  # Scaling from integers from API to physical quantities

    def __init__(self, name: str,
                 instrument: Union[Vaunix_LDA, LdaChannel],
                 dll_get_function: Callable, dll_set_function: Callable,
                 **kwargs):
        """
        Parameter associated with one channel of the LDA.

        Args:
            name: parameter name
            instrument: parent instrument, either LDA or LDA channel
            dll_get_function: DLL function that gets the value
            dll_get_function: DLL function that sets the value
        """
        super().__init__(name, instrument, **kwargs)
        self._reference = instrument.root_instrument.reference
        self._dll_get_function = partial(dll_get_function, self._reference)
        self._dll_set_function = partial(dll_set_function, self._reference)

    def _switch_channel(self) -> None:
        """
        Switch to this channel.
        """
        if hasattr(self.instrument, "channel_number"):
            instr = cast(Instrument, self.instrument)
            instr.root_instrument.dll.fnLDA_SetChannel(self._reference,
                                                       instr.channel_number)

    def get_raw(self) -> float:
        """
        Switch to this channel and return current value.
        """
        self._switch_channel()
        value = self._dll_get_function()
        if value < 0:
            raise RuntimeError(f'{self._dll_get_function.func.__name__} '
                               f'returned error {value}')
        return value * self.scaling

    def set_raw(self, value: float) -> None:
        """
        Switch to this channel and set to ``value`` .
        """
        self._switch_channel()
        value = round(value / self.scaling)
        error_msg = self._dll_set_function(value)
        if error_msg != 0:
            raise RuntimeError(f'{self._dll_set_function.func.__name__} '
                               f'returned error {error_msg}')


class LdaAttenuation(LdaParameter):
    """
    Attenuation of one channel in the LDA.
    """
    scaling = 0.05  # integers returned by the API correspond to 0.05 dB

    def __init__(self, name: str,
                 instrument: Union[Vaunix_LDA, LdaChannel],
                 **kwargs):
        dll = instrument.root_instrument.dll

        ref = instrument.root_instrument.reference
        min_att = dll.fnLDA_GetMinAttenuationHR(ref) * self.scaling
        max_att = dll.fnLDA_GetMaxAttenuationHR(ref) * self.scaling
        vals = Numbers(min_att, max_att)

        super().__init__(name, instrument,
                         dll_get_function=dll.fnLDA_GetAttenuationHR,
                         dll_set_function=dll.fnLDA_SetAttenuationHR,
                         vals=vals,
                         unit="dB",
                         label="Attenuation",
                         **kwargs,
                         )


class LdaWorkingFrequency(LdaParameter):
    """
    Working frequency of one channel of the LDA. Not supported on all models.
    """
    scaling = 100_000  # integers returned by the API correspond to 100kHz

    def __init__(self, name: str,
                 instrument: Union[Vaunix_LDA, LdaChannel],
                 **kwargs):
        """
        Attenuation of one channel in the LDA.

        Args:
            name: parameter name
            instrument: parent instrument, either LDA or LDA channel
        """
        dll = instrument.root_instrument.dll
        super().__init__(name, instrument,
                         dll_get_function=dll.fnLDA_GetWorkingFrequency,
                         dll_set_function=dll.fnLDA_SetWorkingFrequency,
                         unit="Hz",
                         label="Working frequency",
                         docstring="Frequency at which the "
                                   "attenuation is most accurate.",
                         **kwargs
                         )

    @classmethod
    def get_validator(cls, root_instrument: Vaunix_LDA) -> Optional[Numbers]:
        """
        Returns validator for working frequency, if ``root_instrument``
        supports it. Else returns None.
        """
        max_freq = root_instrument.dll.fnLDA_GetMaxWorkingFrequency(
                    root_instrument.reference) * cls.scaling
        min_freq = root_instrument.dll.fnLDA_GetMinWorkingFrequency(
                    root_instrument.reference) * cls.scaling
        # if feature is not supported, these values will be equal
        if max_freq > min_freq:
            return Numbers(min_freq, max_freq)
        else:
            return None


# shorthand
LDA = Vaunix_LDA
