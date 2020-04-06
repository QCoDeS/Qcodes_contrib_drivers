import logging
from typing import Optional, Dict, Callable, Union
from functools import partial
from platform import architecture
import os
import sys
import ctypes

from qcodes import Instrument, InstrumentChannel, Parameter
from qcodes.utils.validators import Numbers

logger = logging.getLogger(__name__)


class Vaunix_LDA(Instrument):
    r"""
    This is the QCoDeS driver for Vaunix LDA digital attenuators.
    Requires that the DLL that comes with the instrument,
    `` VNX_atten64.dll``  and/or `` VNX_atten.dll``, is found at ``dll_path``,
    for 64-bit Windows and 32-bit Windows, respectively.
    If the instrument has more than one physical channel,
    ``InstrumentChannel``  objects are created for each one.
    If the instrument has only one physical channel, no channels are created
    and the parameters will be assigned to this instrument instead.
    The sweep profiles available in the API are not implemented.

    Tested with with 64-bit system and
    - LDA-133
    - LDA-802Q

    Args:
        name: Qcodes name for this instrument
        serial_number: Serial number of the instrument, used to identify it.
        dll_path: Look for the LDA DLL's in this directory.
            By default, the directory this file is in.
        channel_names: Optionally assign these names to the channels.
        test_mode: If true, communicates with the API but not with the device.
            For testing purposes.
    """

    def __init__(self, name: str,
                 serial_number: int,
                 dll_path: Optional[str] = None,
                 channel_names: Optional[Dict[int, str]] = None,
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
            raise ValueError(f"LDA with serial number {self.serial_number}"
                             f" was not found in the system. Found: {devices}")

        self.dll.fnLDA_InitDevice(self.reference)

        num_channels = self.dll.fnLDA_GetNumChannels(self.reference)
        if num_channels == 1:
            # don't add Channel objects, add parameters directly instead
            self.add_parameter("attenuation",
                               parameter_class=LdaAttenuation,
                               )
            wf_vals = LdaWorkingFrequency.get_validator(self)
            if wf_vals:
                self.add_parameter("working_frequency",
                                   parameter_class=LdaWorkingFrequency,
                                   vals=wf_vals,
                                   )
        else:
            for i in range(1, num_channels + 1):
                name = channel_names.get(i, f"ch{i}")
                ch = LdaChannel(parent=self, channel_number=i, name=name)
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

    def close(self) -> None:
        self.dll.fnLDA_CloseDevice(self.reference)
        super().close()

    def save_settings(self) -> None:
        """ Save current settings to memory.
        Settings are automatically loaded during power on.
        """
        self.dll.fnLDA_SaveSettings(self.reference)


class LdaChannel(InstrumentChannel):
    """ Channel corresponding to one input-output pair of the LDA
        digital attenuator. """
    def __init__(self, parent: Vaunix_LDA,
                 channel_number: int,
                 name: str):
        super().__init__(parent=parent, name=name)
        self.channel_number = channel_number
        self.add_parameter("attenuation",
                           parameter_class=LdaAttenuation,
                           )
        wf_vals = LdaWorkingFrequency.get_validator(parent)
        if wf_vals:
            self.add_parameter("working_frequency",
                               parameter_class=LdaWorkingFrequency,
                               vals=wf_vals,
                               )


class LdaParameter(Parameter):
    scaling = 1

    def __init__(self, name: str,
                 instrument: Union[Vaunix_LDA, LdaChannel],
                 dll_get_function: Callable, dll_set_function: Callable,
                 **kwargs):
        """ Parameter associated with one channel of the LDA.
            Args:
                name: parameter name
                instrument: parent instrument, either LDA or LDA channel
                dll_get_function: DLL function that gets the value
                dll_get_function: DLL function that sets the value
        """
        super().__init__(name, instrument, **kwargs)
        self.dll = instrument.root_instrument.dll
        self.reference = instrument.root_instrument.reference
        self.dll_get_function = partial(dll_get_function, self.reference)
        self.dll_set_function = partial(dll_set_function, self.reference)

    def _switch_channel(self) -> None:
        """ Switch to this channel. """
        if hasattr(self.instrument, "channel_number"):
            self.dll.fnLDA_SetChannel(self.reference,
                                      self.instrument.channel_number)

    def get_raw(self) -> float:
        """ Switch to this channel and return current value. """
        self._switch_channel()
        value = self.dll_get_function()
        if value < 0:
            raise RuntimeError(f'{self.dll_get_function.__name__} returned'
                               f' error {value}')
        return value * self.scaling

    def set_raw(self, value: float) -> None:
        """ Switch to this channel and set to ``value`` . """
        self._switch_channel()
        value = round(value / self.scaling)
        error_msg = self.dll_set_function(value)
        if error_msg != 0:
            raise RuntimeError(f'{self.dll_get_function.__name__} returned'
                               f' error {error_msg}')


class LdaAttenuation(LdaParameter):
    """ Attenuation of one channel in the LDA. """
    scaling = 0.05  # integers returned by the API correspond to 0.05 dB

    def __init__(self, name: str,
                 instrument: Union[Vaunix_LDA, LdaChannel],
                 **kwargs):
        dll = instrument.root_instrument.dll
        super().__init__(name, instrument,
                         dll_get_function=dll.fnLDA_GetAttenuationHR,
                         dll_set_function=dll.fnLDA_SetAttenuationHR,
                         vals=Numbers(0, 63),  # replace below
                         unit="dB",
                         label="Attenuation",
                         **kwargs,
                         )

        self._switch_channel()
        min_att = dll.fnLDA_GetMinAttenuationHR(self.reference) * self.scaling
        max_att = dll.fnLDA_GetMaxAttenuationHR(self.reference) * self.scaling
        self.vals = Numbers(min_att, max_att)


class LdaWorkingFrequency(LdaParameter):
    """ Working frequency of one channel of the LDA.
    Not supported on all models.
    """
    scaling = 100_000  # integers returned by the API correspond to 100kHz

    def __init__(self, name: str,
                 instrument: Union[Vaunix_LDA, LdaChannel],
                 **kwargs):
        """Attenuation of one channel in the LDA.
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
        """ Returns validator for working frequency, if ``root_instrument``
         supports it. Else returns None.
        """
        max_freq = root_instrument.dll.fnLDA_GetMaxWorkingFrequency(
                    root_instrument.reference) * cls.scaling
        min_freq = root_instrument.dll.fnLDA_GetMinWorkingFrequency(
                    root_instrument.reference) * cls.scaling
        # if feature is not supported, these values will be equal
        ret = None
        try:
            ret = Numbers(min_freq, max_freq)
        except TypeError:
            pass
        return ret


# shorthand
LDA = Vaunix_LDA
