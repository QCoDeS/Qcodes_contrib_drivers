import logging
from typing import Optional, List, Any, Dict, Callable
from functools import partial
from platform import architecture
import os
import sys
import ctypes

from qcodes import Instrument, InstrumentChannel
from qcodes.utils.validators import Numbers

logger = logging.getLogger(__name__)

ATT_UNIT = 0.05  # integers returned by the API correspond to 0.05 dB
FREQ_UNIT = 100_000  # integers returned by the API correspond to 100kHz


class Vaunix_LDA(Instrument):
    r"""
    This is the QCoDeS driver for Vaunix LDA digital attenuators.
    Requires that the DLL that comes with the instrument, `` VNX_atten64.dll``  and/or `` VNX_atten.dll``,
    is found at ``dll_path``, for 64-bit Windows and 32-bit Windows, respectively.
    If the instrument has more than one physical channel, `` InstrumentChannel``  objects
    are created for each one. If the instrument has only one physical channel, no channels are created
    and the parameters will be assigned to this instrument instead.
    The sweep profiles available in the API are not implemented.

    Tested with with 64-bit system and
    - LDA-133
    - LDA-802Q

    Args:
        name: Qcodes name for this instrument
        serial_number: Serial number of the instrument, used to identify it.
        dll_path: Look for the LDA DLL's in this directory. By default, the directory this file is in.
        channel_names: Optionally assign these names to the channels.
        test_mode: If true, communicates with the API but not with the device. For testing purposes.
    """

    def __init__(self, name: str,
                 serial_number: int,
                 dll_path: Optional[str] = None,
                 channel_names: Optional[List[str]] = None,
                 test_mode: Optional[bool] = False,
                 **kwargs):

        super().__init__(name=name, **kwargs)
        self.serial_number = serial_number
        self.reference = None

        if channel_names is None:
            channel_names = []

        self.dll = None
        self._load_dll(dll_path)
        self.dll.fnLDA_SetTestMode(test_mode)  # Test API without communication

        # Find all Vaunix devices, init the one with matching serial number.
        num_devices = self.dll.fnLDA_GetNumDevices()
        device_IDs = ctypes.c_int * num_devices
        device_refs = device_IDs()
        self.dll.fnLDA_GetDevInfo(device_refs)
        devices = {self.dll.fnLDA_GetSerialNumber(ref): ref for ref in device_refs}
        self.reference = devices.get(self.serial_number, "not found")
        if self.reference == "not found":
            raise ValueError(f"LDA with serial number {self.serial_number} was not found"
                             f" in the system. Found: {devices}")

        self.dll.fnLDA_InitDevice(self.reference)

        num_channels = self.dll.fnLDA_GetNumChannels(self.reference)
        if num_channels == 1:
            # don't add Channel objects, add attenuation parameter directly instead
            max_att = self.dll.fnLDA_GetMaxAttenuationHR(self.reference) * ATT_UNIT
            min_att = self.dll.fnLDA_GetMinAttenuationHR(self.reference) * ATT_UNIT

            self.add_parameter("attenuation",
                               unit="dB",
                               get_cmd=self.get_attenuation,
                               set_cmd=self.set_attenuation,
                               vals=Numbers(min_att, max_att)
                               )

            max_freq = self.dll.fnLDA_GetMaxWorkingFrequency(self.reference) * FREQ_UNIT
            min_freq = self.dll.fnLDA_GetMinWorkingFrequency(self.reference) * FREQ_UNIT
            if max_freq > min_freq:
                self.add_parameter("working_frequency",
                                   unit="Hz",
                                   vals=Numbers(min_freq, max_freq),
                                   get_cmd=self.get_working_frequency,
                                   set_cmd=self.set_working_frequency,
                                   docstring="Frequency at which the attenuation is most accurate.",
                                   )

        else:
            for i in range(1, num_channels + 1):
                name = channel_names[i-1] if len(channel_names) >= i else f"ch{i}"
                ch = LDAChannel(parent=self, channel_number=i, name=name)
                self.add_submodule(name, ch)

        self.connect_message()

    def _load_dll(self, dll_path: str = None) -> None:
        r""" Load correct DLL from ``dll_path`` based on bitness of the operating system.
        Args:
            dll_path: path to the directory that contains the Vaunix LDA DLL.
            By default, same as the directory of this file.
        """
        if dll_path is None:
            dll_path = os.path.dirname(os.path.abspath(__file__))

        if sys.platform != "win32":
            raise OSError(f"LDA is not supported on {sys.platform}.")

        bitness = architecture()[0]
        if "64bit" in bitness:
            dll_path = os.path.join(dll_path, "VNX_atten64")
        elif "32bit" in bitness:
            dll_path = os.path.join(dll_path, "VNX_atten")
        else:
            raise OSError("Unknown bitness of system:", bitness)
        self.dll = ctypes.cdll.LoadLibrary(dll_path)

    def get_idn(self) -> Dict[str, Optional[str]]:

        model = ctypes.create_string_buffer(300)
        self.dll.fnLDA_GetModelNameA(self.reference, model)
        model = str(model.value.decode())

        return {"vendor": "Vaunix",
                "model": model,
                "serial":  self.dll.fnLDA_GetSerialNumber(self.reference),
                "firmware": self.dll.fnLDA_GetDLLVersion(),
                }

    def close(self):
        self.dll.fnLDA_CloseDevice(self.reference)
        super().close()

    def get_attenuation(self) -> float:
        """ Return attenuation of currently selected channel. """
        value = self.dll.fnLDA_GetAttenuationHR(self.reference)
        if value < 0:
            raise RuntimeError('GetAttenuationHR returned error', value)

        atten_db = value * ATT_UNIT
        return atten_db

    def set_attenuation(self, value: float):
        """ Set attenuation of currently selected channel to `` value`` . """
        attenuation = round(value / ATT_UNIT)
        error_msg = self.dll.fnLDA_SetAttenuationHR(self.reference, int(attenuation))
        if error_msg != 0:
            raise RuntimeError('SetAttenuationHR returned error', error_msg)

    def set_working_frequency(self, value: float):
        """ Set working frequency of currently selected channel to `` value`` . """
        frequency_100khz = int(value / FREQ_UNIT)
        error_msg = self.dll.fnLDA_SetWorkingFrequency(self.reference, frequency_100khz)
        if error_msg != 0:
            raise RuntimeError('fSetWorkingFrequency returned error', error_msg)

    def get_working_frequency(self) -> float:
        """ Get working frequency of currently selected channel to `` value`` . """
        return self.dll.fnLDA_GetWorkingFrequency(self.reference) * FREQ_UNIT

    def switch_channel(self, number: int):
        """ Change to which channel get and set commands refer to."""
        _ = self.dll.fnLDA_SetChannel(self.reference, number)

    def save_settings(self):
        """ Save current settings to memory. Settings are automatically loaded during power on."""
        self.dll.fnLDA_SaveSettings(self.reference)


class LDAChannel(InstrumentChannel):
    """ Attenuation channel for the LDA digital attenuator. """

    def __init__(self, parent: Instrument, channel_number: int, name: Optional[str] = None):
        name = name or f"ch{channel_number}"
        super().__init__(parent=parent, name=name)
        self.channel_number = channel_number

        max_att = self.parent.dll.fnLDA_GetMaxAttenuationHR(self.parent.reference) * ATT_UNIT
        min_att = self.parent.dll.fnLDA_GetMinAttenuationHR(self.parent.reference) * ATT_UNIT

        self.add_parameter("attenuation",
                           unit="dB",
                           get_cmd=partial(self._switch_and_call, self.parent.get_attenuation),
                           set_cmd=partial(self._switch_and_call, self.parent.set_attenuation),
                           vals=Numbers(min_att, max_att)
                           )

        max_freq = self.parent.dll.fnLDA_GetMaxWorkingFrequency(self.parent.reference) * FREQ_UNIT
        min_freq = self.parent.dll.fnLDA_GetMinWorkingFrequency(self.parent.reference) * FREQ_UNIT

        if max_freq > min_freq:
            self.add_parameter("working_frequency",
                               unit="Hz",
                               vals=Numbers(min_freq, max_freq),
                               get_cmd=partial(self._switch_and_call,
                                               self.parent.get_working_frequency),
                               set_cmd=partial(self._switch_and_call,
                                               self.parent.set_working_frequency),
                               docstring="Frequency at which the attenuation is most accurate.",
                               )

    def _switch_and_call(self, func: Callable, *args) -> Any:
        """ Change active channel on the parent instrument, so that ``func``  call is applied on
        this channel. """
        self.parent.switch_channel(self.channel_number)
        return func(*args)

# shorthand
LDA = Vaunix_LDA