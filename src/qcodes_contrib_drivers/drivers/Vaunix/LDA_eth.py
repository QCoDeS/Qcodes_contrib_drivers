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

MAX_MODELNAME = 32
MAX_SWVERSION = 7
MAX_NETBUFF   = 16
FREQ_UNIT     = 1e5
ATT_UNIT      = 0.05

logger = logging.getLogger(__name__)

class Vaunix_LDA_Eth(Instrument):
    dll_path = None

    def __init__(self, name: str,
                 ip_address: str,
                 dll_path: Optional[str] = None,
                 num_channels: int = 1,
                 channel_names: Optional[Dict[int, str]] = None,
                 test_mode: bool = False,
                 **kwargs):
        
        begin_time = time.time()
        self.ip_address = ip_address
        self.ip_buffer = ctypes.create_string_buffer(ip_address.encode())

        if channel_names is None:
            channel_names = {}

        self.dll = self._get_dll(dll_path)
        self.dll.fnLDA_SetTestMode(test_mode)  # Test API without communication
        
        self.dll.fnLDA_InitDevice(self.ip_buffer)

        # call superclass init only after DLL has been successfully loaded
        super().__init__(name=name, **kwargs)

        if num_channels == 1: # Ethernet dll does not have method to get the number of channel
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
        path = dll_path or Vaunix_LDA_Eth.dll_path
        if path is None:
            raise ValueError("DLL path for Vaunix LDA was not provided. "
                             "Either set ``Vaunix_LDA.dll_path`` or provide "
                             "it as an argument to the constructor.")

        if sys.platform != "win32":
            raise OSError(f"LDA is not supported on {sys.platform}.")
        bitness = architecture()[0]
        if "64bit" in bitness:
            full_path = os.path.join(path, "VNX_Eth_Attn64")
        elif "32bit" in bitness:
            full_path = os.path.join(path, "VNX_Eth_Attn")
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

        buf = (ctypes.c_char*MAX_MODELNAME)()
        self.dll.fnLDA_GetModelName(self.ip_buffer, buf)
        model = str(buf.value.decode())

        serialno = (ctypes.c_int*1)()
        self.dll.fnLDA_GetSerialNumber(self.ip_buffer, serialno)
        
        swv_buf = (ctypes.c_char*MAX_SWVERSION)()
        self.dll.fnLDA_GetSoftwareVersion(self.ip_buffer, swv_buf)
        swversion = str(swv_buf.value.decode())


        return {"vendor": "Vaunix",
                "model": model,
                "serial":  serialno[0],
                "firmware": swversion,
                }
    
    def close(self) -> None:
        if hasattr(self, "dll"):
            self.dll.fnLDA_CloseDevice(self.ip_buffer)
        super().close()

class LdaChannel(InstrumentChannel):
    """
    Channel corresponding to one input-output pair of the LDA digital
    attenuator.
    """
    def __init__(self, parent: Vaunix_LDA_Eth,
                 channel_number: int,
                 name: str):
        super().__init__(parent=parent, name=name)
        self.channel_number = channel_number
        _add_lda_parameters(self)


def _add_lda_parameters(inst: Union[Vaunix_LDA_Eth, LdaChannel]) -> None:
    """
    Helper function for adding parameters to either LDA root instrument,
    or channels inside it.
    Args:
        inst: the instrument or channel to add the parameters to.
    """
    root_instrument = cast(Vaunix_LDA_Eth, inst.root_instrument)
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
                 instrument: Union[Vaunix_LDA_Eth, LdaChannel],
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
        self._ip_buffer = instrument.root_instrument.ip_buffer
        self._dll_get_function = partial(dll_get_function, self._ip_buffer)
        self._dll_set_function = partial(dll_set_function, self._ip_buffer)

    def _switch_channel(self) -> None:
        """
        Switch to this channel.
        """
        if hasattr(self.instrument, "channel_number"):
            instr = cast(Instrument, self.instrument)
            instr.root_instrument.dll.fnLDA_SetChannel(self._ip_buffer,
                                                       ctypes.c_int(instr.channel_number))

    def get_raw(self) -> float:
        """
        Switch to this channel and return current value.
        """
        self._switch_channel()
        val_buf = (ctypes.c_int*1)()
        value = self._dll_get_function(val_buf)
        if value < 0:
            raise RuntimeError(f'{self._dll_get_function.func.__name__} '
                               f'returned error {value}')
        return val_buf[0] * self.scaling

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
                 instrument: Union[Vaunix_LDA_Eth, LdaChannel],
                 **kwargs):
        dll = instrument.root_instrument.dll

        ref = instrument.root_instrument.ip_buffer
        min_att = (ctypes.c_int*1)()
        dll.fnLDA_GetMinAttenuation(ref,min_att)
        max_att = (ctypes.c_int*1)()
        dll.fnLDA_GetMaxAttenuation(ref,max_att)
        vals = Numbers(min_att[0]*self.scaling, max_att[0]*self.scaling)

        label = "Attenuation"
        if isinstance(instrument, LdaChannel):
            # prefix label to make channels more easily distinguishable in plots
            label = f"{instrument.short_name} {label}"

        super().__init__(name, instrument,
                         dll_get_function=dll.fnLDA_GetAttenuation,
                         dll_set_function=dll.fnLDA_SetAttenuation,
                         vals=vals,
                         unit="dB",
                         label=label,
                         **kwargs,
                         )


class LdaWorkingFrequency(LdaParameter):
    """
    Working frequency of one channel of the LDA. Not supported on all models.
    """
    scaling = 100_000  # integers returned by the API correspond to 100kHz

    def __init__(self, name: str,
                 instrument: Union[Vaunix_LDA_Eth, LdaChannel],
                 **kwargs):
        """
        Attenuation of one channel in the LDA.

        Args:
            name: parameter name
            instrument: parent instrument, either LDA or LDA channel
        """
        dll = instrument.root_instrument.dll

        label = "Working frequency"
        if isinstance(instrument, LdaChannel):
            # prefix label to make channels more easily distinguishable in plots
            label = f"{instrument.short_name} {label}"

        super().__init__(name, instrument,
                         dll_get_function=dll.fnLDA_GetWorkingFrequency,
                         dll_set_function=dll.fnLDA_SetWorkingFrequency,
                         unit="Hz",
                         label=label,
                         docstring="Frequency at which the "
                                   "attenuation is most accurate.",
                         **kwargs
                         )

    @classmethod
    def get_validator(cls, root_instrument: Vaunix_LDA_Eth) -> Optional[Numbers]:
        """
        Returns validator for working frequency, if ``root_instrument``
        supports it. Else returns None.
        """
        max_freq = (ctypes.c_int*1)()
        root_instrument.dll.fnLDA_GetMaxWorkingFrequency(root_instrument.ip_buffer, max_freq)
        min_freq = (ctypes.c_int*1)()
        root_instrument.dll.fnLDA_GetMinWorkingFrequency(root_instrument.ip_buffer, min_freq)
        # if feature is not supported, these values will be equal
        if max_freq[0] > min_freq[0]:
            return Numbers(min_freq[0]*cls.scaling, max_freq[0]*cls.scaling)
        else:
            return None