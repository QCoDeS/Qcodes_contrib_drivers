import numpy as np
from .dll_wrapper import APS2DLLWrapper, AttributeWrapper
from qcodes import Instrument, InstrumentChannel
from qcodes.instrument import InstrumentModule
from qcodes.validators import Enum, Strings
from qcodes.parameters import ManualParameter
from ctypes import c_uint32, c_uint64, c_uint8, c_int16, c_int, c_float, c_double, c_uint, c_char_p, addressof, create_string_buffer
from functools import partial
from typing import Optional, Dict, Literal

def c_str(s: str) -> bytes: return bytes(s, "ascii")

# gettable attributes
UPTIME = AttributeWrapper("uptime", c_double)
FPGA_TEMPERATURE = AttributeWrapper("fpga_temperature", c_float)
RUNSTATE = AttributeWrapper("runState", c_int)
DHCP_ENABLE = AttributeWrapper("dhcp_enable", c_int)
IP_ADDRESS = AttributeWrapper("ip_addr", c_char_p)
SAMPLERATE = AttributeWrapper("sampleRate", c_uint)
TRIGGER_SOURCE = AttributeWrapper("trigger_source", c_int)
TRIGGER_INTERVAL = AttributeWrapper("trigger_interval", c_double)
WAVEFORM_FREQUENCY = AttributeWrapper("waveform_frequency", c_float)
MIXER_AMPLITUDE_IMBALANCE = AttributeWrapper("mixer_amplitude_imbalance", c_float)
MIXER_PHASE_SKEW = AttributeWrapper("mixer_phase_skew", c_float)

# gettable channel attributes
CHANNEL_OFFSET = AttributeWrapper("channel_offset", c_float)
CHANNEL_SCALE = AttributeWrapper("channel_scale", c_float)
CHANNEL_ENABLED = AttributeWrapper("channel_enabled", c_int)
CHANNEL_DELAY = AttributeWrapper("channel_delay", c_uint)

class APS2Rack(Instrument):
    def __init__(self, name: str,
                 dll_path: str,
                 **kwargs) -> None:

        super().__init__(name, **kwargs)

        self._wrapper = APS2DLLWrapper(dll_path=dll_path)

        for idx in list(self.enumerate().keys())[1:]:
            module = APS2Slice(self, f"APS2_{idx}", self.enumerate()[idx])
            self.add_submodule(f"APS2_{idx}", module)

    def get_num_devices(self):
        num = c_uint()
        self._wrapper._get_num_devices(num)
        return int(num.value)

    def get_device_IPs(self):
        num_devices = self.get_num_devices()
        if num_devices > 0:
            results = (c_char_p * num_devices)(addressof(create_string_buffer(16)))
            self._wrapper._get_device_IPs(results)

            return [r.decode('ascii') for r in results]
        else:
            return None

    def enumerate(self):
        device_IPs = self.get_device_IPs()
        if device_IPs:
            n = len(device_IPs)
        else:
            n = 0

        APS2_list = {}
        for i in range(n):
            APS2_list[i] = device_IPs[i]
        return APS2_list

    def get_idn(self):
        IDN: Dict[str, Optional[str]] = {
            'vendor': 'Raytheon BBN', 'model': 'APS2 Rack',
            'serial': None, 'firmware': None}
        return IDN

class APS2Channel(InstrumentChannel):
    def __init__(self, parent: InstrumentModule,
                 name: str,
                 channel: int,
                 **kwargs) -> None:
        super().__init__(parent, name, **kwargs)

        self._wrapper = self._parent._wrapper
        self.channel = channel

        self.add_parameter(name="channel_offset",
                           get_cmd=partial(self._get_attribute,
                                           CHANNEL_OFFSET),
                           set_cmd=partial(self._set_attribute,
                                           CHANNEL_OFFSET))

        self.add_parameter(name="channel_scale",
                           get_cmd=partial(self._get_attribute,
                                           CHANNEL_SCALE),
                           set_cmd=partial(self._set_attribute,
                                           CHANNEL_SCALE))

        self.add_parameter(name="channel_enabled",
                           get_cmd=partial(self._get_attribute,
                                           CHANNEL_ENABLED),
                           set_cmd=partial(self._set_attribute,
                                           CHANNEL_ENABLED))

        self.add_parameter(name="channel_delay",
                           get_cmd=partial(self._get_attribute,
                                           CHANNEL_DELAY),
                           set_cmd=partial(self._set_attribute,
                                           CHANNEL_DELAY))

    def set_waveform_float(self, data: list[float]):
        num_points = len(data)
        converted_data = (c_float * num_points)(*data)
        self._wrapper._set_waveform_float(c_str(self._parent.address),
                                          c_int(self.channel),
                                          converted_data,
                                          c_int(num_points))

    def set_waveform_int(self, data: list[int]):
        num_points = len(data)
        converted_data = (c_int16 * num_points)(*data)
        self._wrapper._set_waveform_int(c_str(self._parent.address),
                                        c_int(self.channel),
                                        converted_data,
                                        c_int(num_points))

    def set_markers(self, data: list[int]):
        num_points = len(data)
        converted_data = (c_uint8 * num_points)(*data)
        self._wrapper._set_markers(c_str(self._parent.address),
                                   c_int(self.channel),
                                   converted_data,
                                   c_int(num_points))

    def _get_attribute(self, attr: AttributeWrapper):
        return self._wrapper.get_attribute(self._parent.address,
                                           attr,
                                           channel=self.channel)

    def _set_attribute(self, attr: AttributeWrapper, set_val):
        return self._wrapper.set_attribute(self._parent.address,
                                           attr,
                                           set_val,
                                           channel=self.channel)

class APS2Slice(InstrumentModule):
    def __init__(self, parent: Instrument,
                 name: str,
                 address: str,
                 **kwargs):

        super().__init__(parent, name, **kwargs)

        self._wrapper = self._parent._wrapper
        self.address = address
        self.sequence_file = None

        for chan in [0, 1]:
            channel = APS2Channel(self, f"Channel_{chan}", channel=chan)
            self.add_submodule(f"Channel_{chan}", channel)

        self.add_parameter(name="up_time",
                           get_cmd=partial(self._get_attribute,
                                           UPTIME),
                           set_cmd=False)

        self.add_parameter(name="ip_address",
                           get_cmd=partial(self._get_attribute,
                                           IP_ADDRESS),
                           set_cmd=partial(self._set_attribute,
                                           IP_ADDRESS))

        self.add_parameter(name="DHCP_enable",
                           get_cmd=partial(self._get_attribute,
                                           DHCP_ENABLE),
                           set_cmd=partial(self._set_attribute,
                                           DHCP_ENABLE),
                           val_mapping={"disabled": 0,
                                        "enabled": 1})

        self.add_parameter(name="fpga_temperature",
                           get_cmd=partial(self._get_attribute,
                                           FPGA_TEMPERATURE),
                           set_cmd=False)

        self.add_parameter(name="sample_rate",
                           unit="MHz",
                           get_cmd=partial(self._get_attribute,
                                           SAMPLERATE),
                           set_cmd=partial(self._set_attribute,
                                           SAMPLERATE),
                           vals=Enum(200, 300, 600, 1200))

        self.add_parameter(name="mixer_amplitude_imbalance",
                           get_cmd=partial(self._get_attribute,
                                           MIXER_AMPLITUDE_IMBALANCE),
                           set_cmd=partial(self._set_attribute,
                                           MIXER_AMPLITUDE_IMBALANCE))

        self.add_parameter(name="mixer_phase_skew",
                           get_cmd=partial(self._get_attribute,
                                           MIXER_PHASE_SKEW),
                           set_cmd=partial(self._set_attribute,
                                           MIXER_PHASE_SKEW))

        self.add_parameter(name="trigger_source",
                           get_cmd=partial(self._get_attribute,
                                           TRIGGER_SOURCE),
                           set_cmd=partial(self._set_attribute,
                                           TRIGGER_SOURCE),
                           val_mapping={"external": 0,
                                        "internal": 1,
                                        "software": 2,
                                        "system": 3})

        self.add_parameter(name="trigger_interval",
                           get_cmd=partial(self._get_attribute,
                                           TRIGGER_INTERVAL),
                           set_cmd=partial(self._set_attribute,
                                           TRIGGER_INTERVAL))

        self.add_parameter(name="waveform_frequency",
                           get_cmd=partial(self._get_attribute,
                                           WAVEFORM_FREQUENCY),
                           set_cmd=partial(self._set_attribute,
                                           WAVEFORM_FREQUENCY))

        self.add_parameter(name="sequence_file_location",
                           parameter_class=ManualParameter,
                           vals=Strings(),
                           initial_value="")

        self.add_parameter(name="run_state",
                           get_cmd=partial(self._get_attribute,
                                           RUNSTATE),
                           set_cmd=False,
                           val_mapping={"stopped": 0,
                                        "playing": 1})
        
        # self.add_parameter(name="sequence_file_location",
        #                    parameter_class=ManualParameter,
        #                    vals=Strings(),
        #                    initial_value="")

    def write_sequence(self, data: list[int]):
        num_words = len(data)
        converted_data = (c_uint64 * num_words)(*data)
        self._wrapper._write_sequence(c_str(self.address),
                                      converted_data,
                                      c_uint32(num_words))

    def set_run_mode(self, mode: Literal["run_sequence", "trig_waveform", "cw_waveform"]):
        mode_dict = {"run_sequence": 0, "trig_waveform": 1, "cw_waveform": 2}
        self._wrapper._set_run_mode(c_str(self.address),
                                    c_int(mode_dict[mode]))

    def load_sequence_file(self):
        self._wrapper._load_sequence_file(c_str(self.address),
                                          c_str(self.sequence_file_location()))
        # self.sequence_file = sequence_file

    def clear_channel_data(self):
        self._wrapper._clear_channel_data(c_str(self.address))

    def reset(self, reset_mode: int=0):
        if reset_mode in [0, 1, 2]:
            self._wrapper._reset(c_str(self.address), c_int(reset_mode))
        else:
            raise ValueError("reset_mode should be among 0 ('RECONFIG_EPROM_USER'), 1 ('RECONFIG_EPROM_BASE') or 2 ('RESET_TCP')")

        return None

    def initialize(self, force: bool=False):
        self._wrapper._init(c_str(self.address), c_int(force))

        return None

    def trigger(self):
        self._wrapper._trigger(c_str(self.address))

        return None

    def connect(self):
        self._wrapper._connect_APS(c_str(self.address))

        return None

    def disconnect(self):
        self._wrapper._diconnect_APS(c_str(self.address))

        return None

    def run(self):
        self._wrapper._run(c_str(self.address))

        return None

    def stop(self):
        self._wrapper._stop(c_str(self.address))

        return None

    def get_mixer_correction_matrix(self):
        matrix = np.zeros((2, 2), dtype=np.float32)
        self._wrapper._get_mixer_correction_matrix(c_str(self.address),
                                                  matrix)

        return matrix

    def set_mixer_correction_matrix(self, matrix: np.ndarray(shape=(2, 2), dtype=np.float32)):
        self._wrapper._set_mixer_correction_matrix(c_str(self.address),
                                                  matrix)

        return None

    def _get_attribute(self, attr: AttributeWrapper):
        return self._wrapper.get_attribute(self.address, attr)

    def _set_attribute(self, attr: AttributeWrapper, set_val):
        return self._wrapper.set_attribute(self.address, attr, set_val)
