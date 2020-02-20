import logging
from typing import Optional, List, Any, Dict
from functools import partial
from platform import architecture
import os
import ctypes

from qcodes import Instrument, InstrumentChannel
from qcodes.utils.validators import Numbers

logger = logging.getLogger(__name__)

# path to dll file
dll_path = os.path.dirname(os.path.abspath(__file__))
       
bitness = architecture()[0]
if "64bit" in bitness:
    dll_path = os.path.join(dll_path, "VNX_atten64")
elif "32bit" in bitness:
    dll_path = os.path.join(dll_path, "VNX_atten")
else:
    raise SystemError("Unkown bitness of system:", bitness)
DLL = ctypes.cdll.LoadLibrary(dll_path)

DLL.fnLDA_SetTestMode(False)  # Test API without communication

ATT_UNIT = 0.05  # integers returned by the API correspond to 0.05 dB
FREQ_UNIT = 100_000  # integers returned by the API correspond to 100kHz


class LDA(Instrument):
    r"""
    This is the QCoDeS driver for Vaunix LDA digital attenuators.
    Assumes a 64-it Windows system and that `VNX_atten64.dll` and/or `VNX_atten.dll`
    is located in the same folder.
    If the instrument has more than one physical channel, `InstrumentChannel` objects
    are created for each one. If there is only one physical channel, no channels are created
    and the parameters will be assigned to this instrument instead.
    The sweep profiles available in the API are not implemented.

    Tested with with 64-bit system and
    - LDA-133
    - LDA-802Q

    Args:
        name: Qcodes name for this instrument
        serial_number: Serial number of the instrument, used to identify it.
        channel_names: Optionally assign these names to the channels.
    """

    def __init__(self, name: str,
                 serial_number: int,
                 channel_names: Optional[List[str]] = [],
                 **kwargs):

        super().__init__(name=name, **kwargs)
        self.serial_number = serial_number
        self.reference = None

        # Find all Vaunix devices, init the one with matching serial number.
        num_devices = DLL.fnLDA_GetNumDevices()
        device_IDs = ctypes.c_int * num_devices
        device_refs = device_IDs()
        DLL.fnLDA_GetDevInfo(device_refs)

        devices = {DLL.fnLDA_GetSerialNumber(ref): ref for ref in device_refs}
        if self.serial_number in devices:
            self.reference = devices[self.serial_number]
        else:
            raise ValueError(f"LDA with serial number {self.serial_number} was not found"
                             f" in the system. Found: {devices}")

        DLL.fnLDA_InitDevice(self.reference)    

        num_channels = DLL.fnLDA_GetNumChannels(self.reference)
        if num_channels == 1:
            # don't add Channel objects, add attenuation parameter directly instead
            max_att = DLL.fnLDA_GetMaxAttenuationHR(self.reference) * ATT_UNIT
            min_att = DLL.fnLDA_GetMinAttenuationHR(self.reference) * ATT_UNIT
            
            min_freq = DLL.fnLDA_SetWorkingFrequency(self.reference, int(6.5e9/ FREQ_UNIT))
            max_freq = DLL.fnLDA_GetWorkingFrequency(self.reference) * FREQ_UNIT
            self.add_parameter("attenuation",
                               unit="dB",
                               get_cmd=self.get_attenuation,
                               set_cmd=self.set_attenuation,
                               vals=Numbers(min_att, max_att)
                               )
                               
            max_freq = DLL.fnLDA_GetMaxWorkingFrequency(self.reference) * FREQ_UNIT
            min_freq = DLL.fnLDA_GetMinWorkingFrequency(self.reference) * FREQ_UNIT
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

    def get_idn(self) -> Dict[str, Optional[str]]:

        model = ctypes.create_string_buffer(300)
        DLL.fnLDA_GetModelNameA(self.reference, model)
        model = model.value.decode()
        
        return {"vendor": "Vaunix",
                "model": model,
                "serial":  DLL.fnLDA_GetSerialNumber(self.reference),
                "firmware": DLL.fnLDA_GetDLLVersion(),
                }

    def close(self):
        DLL.fnLDA_CloseDevice(self.reference)
        super().close()

    def get_attenuation(self) -> float:
        """ Return attenuation of currently selected channel. """
        value = DLL.fnLDA_GetAttenuationHR(self.reference)
        if value < 0:
            raise RuntimeError('GetAttenuationHR returned error', value)

        atten_db = value * ATT_UNIT
        return atten_db

    def set_attenuation(self, value: float):
        """ Set attenuation of currently selected channel to `value`. """
        attenuation = round(value / ATT_UNIT)
        error_msg = DLL.fnLDA_SetAttenuationHR(self.reference, int(attenuation))
        if error_msg != 0:
            raise RuntimeError('SetAttenuationHR returned error', error_msg)

    def set_working_frequency(self, value: float):
        """ Set working frequency of currently selected channel to `value`. """
        frequency_100khz = int(value / FREQ_UNIT)
        error_msg = DLL.fnLDA_SetWorkingFrequency(self.reference, frequency_100khz)
        if error_msg != 0:
            raise RuntimeError('fSetWorkingFrequency returned error', error_msg)

    def get_working_frequency(self) -> float:
        """ Get working frequency of currently selected channel to `value`. """
        return DLL.fnLDA_GetWorkingFrequency(self.reference) * FREQ_UNIT

    def switch_channel(self, number: int):
        """ Change to which channel get and set commands refer to."""
        _ = DLL.fnLDA_SetChannel(self.reference, number)
        
    def save_settings(self):
        """ Save current settings to memory. Settings are automatically loaded during power on."""
        DLL.fnLDA_SaveSettings(self.reference)


class LDAChannel(InstrumentChannel):
    """ Attenuation channel for the LDA digital attenuator. """

    def __init__(self, parent: str, channel_number: int, name: Optional[str] = None):
        name = name or f"ch{channel_number}"
        super().__init__(parent=parent, name=name)
        self.channel_number = channel_number

        max_att = DLL.fnLDA_GetMaxAttenuationHR(self.parent.reference) * ATT_UNIT
        min_att = DLL.fnLDA_GetMinAttenuationHR(self.parent.reference) * ATT_UNIT

        self.add_parameter("attenuation",
                           unit="dB",
                           get_cmd=partial(self._switch_and_call, self.parent.get_attenuation),
                           set_cmd=partial(self._switch_and_call, self.parent.set_attenuation),
                           vals=Numbers(min_att, max_att)
                           )

        max_freq = DLL.fnLDA_GetMaxWorkingFrequency(self.parent.reference) * FREQ_UNIT
        min_freq = DLL.fnLDA_GetMinWorkingFrequency(self.parent.reference) * FREQ_UNIT

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

    def _switch_and_call(self, func, *args) -> Any:
        """ Change active channel on the parent instrument, so that `func` call is applied on
        the this channel. """
        self.parent.switch_channel(self.channel_number)
        return func(*args)
