# -*- coding: UTF-8 -*-
# Tongyu Zhao <ty.zhao.work@gmail.com> summer 2022
import ctypes
import logging
from typing import Optional, Any
from functools import partial
from ctypes import byref

from typing_extensions import Literal
from qcodes import Instrument

from .dll_wrapper import AttributeWrapper, NamedArgType, NIHSDIODLLWrapper
from .visa_types import (
    ViBoolean, ViConstString, ViInt32, ViString, ViSession, ViAttr, ViReal64, VI_NULL, ViUInt32
)

def c_str(s: str) -> bytes: return bytes(s, "ascii")

# attribute ID's used for querying attributes
NIHSDIO_ATTR_DYNAMIC_CHANNELS             = AttributeWrapper(ViAttr(1150002), ViString)
NIHSDIO_ATTR_STATIC_CHANNELS              = AttributeWrapper(ViAttr(1150003), ViString)
NIHSDIO_ATTR_SERIAL_NUMBER                = AttributeWrapper(ViAttr(1150096), ViString)

NIHSDIO_ATTR_REF_CLOCK_SOURCE             = AttributeWrapper(ViAttr(1150011), ViString)
NIHSDIO_ATTR_REF_CLOCK_RATE               = AttributeWrapper(ViAttr(1150012), ViReal64)
NIHSDIO_ATTR_REF_CLOCK_IMPEDANCE          = AttributeWrapper(ViAttr(1150058), ViReal64)

NIHSDIO_ATTR_SAMPLE_CLOCK_SOURCE          = AttributeWrapper(ViAttr(1150013), ViString)
NIHSDIO_ATTR_SAMPLE_CLOCK_RATE            = AttributeWrapper(ViAttr(1150014), ViReal64)
NIHSDIO_ATTR_SAMPLE_CLOCK_IMPEDANCE       = AttributeWrapper(ViAttr(1150060), ViReal64)

NIHSDIO_ATTR_REPEAT_MODE                  = AttributeWrapper(ViAttr(1150026), ViInt32)
NIHSDIO_ATTR_REPEAT_COUNT                 = AttributeWrapper(ViAttr(1150071), ViInt32)

NIHSDIO_ATTR_DATA_POSITION                = AttributeWrapper(ViAttr(1150056), ViInt32)
NIHSDIO_ATTR_DATA_WIDTH                   = AttributeWrapper(ViAttr(1150108), ViInt32)

logger = logging.getLogger(__name__)

REF_CLK_SRC_MAP = {
    "None": "None",
    "clk_in": "ClkIn",
    "pxi_clk": "PXI_CLK",
    "rtsi7": "RTSI7",
    "pxie_dstara": "PXIe_DStarA"
}

SAMPLE_CLK_SRC_MAP = {
    "on_board_clock": "OnBoardClock",
    "clk_in": "ClkIn",
    "pxi_star": "PXI_STAR",
    "strobe": "STROBE"
}

LOGIC_FAMILY = {
    "1.2V": 81,
    "1.5V": 80,
    "1.8V": 8,
    "2.5V": 7,
    "3.3V": 6,
    "5.0V": 5
}

SIGNAL = {
    "sample_clock": 52,
    "reference_clock": 51,
    "start_trigger": 53,
    "reference_trigger": 54,
    "data_active_event": 55,
    "ready_for_start_event": 56,
    "ready_for_advance_event": 66,
    "end_of_record_event": 68,
    "pause_trigger": 57,
    "script_trigger": 58,
    "marker_event": 59,
    "onboard_reference_clock": 60,
    "advance_trigger": 61,
    "stop_trigger": 82
}

OUTPUT_TERMINAL = [
    "PFI0", "PFI1", "PFI2", "PFI3", # PFI connectors
    "PXI_Trig0", "PXI_Trig1", "PXI_Trig2", "PXI_Trig3", # the PXI trigger backplane
    "PXI_Trig4", "PXI_Trig5", "PXI_Trig6", # the PXI trigger backplane
    "PXI_Trig7", "RTSI0", "RTSI1", "RTSI2", # the RTSI trigger bus
    "RTSI3", "RTSI4", "RTSI5", "RTSI6", # the RTSI trigger bus
    "RTSI7", # designated for the Onboard Reference Clock
    "ClkOut", # CLK OUT connector on the front panel
    "DDC_ClkOut", # DDC CLK OUT terminal in the DDC connector
    "", VI_NULL # the signal is not exported
]

DATA_POSITION = {
    'sample_clock_rising_edge': 18,
    'sample_clock_falling_edge': 19,
    'delay_from_sample_clock_rising_edge': 20
}

DATA_LAYOUT = {
    'group_by_sample': 71,
    'group_by_channel': 72
}

class NationalInstruments_HSDIO(Instrument):
    r"""
    This is the QCoDeS driver for National Instruments HSDIO
    devices based on the NI-HSDIO driver. As of NI-HSDIO version 21.5, the
    supported devices are
    PXI/PCI-6541, PXI/PCI-6542, PXIe-6544, PXIe-6545,
    PXIe-6547, PXIe-6548, PXI/PCI-6551, PXI/PCI-6552,
    PXIe-6555, PXIe-6556, PXI/PCI-6561, PXI/PCI-6562

    Documentation for the NI-HSDIO C API can be found by default in the
    folder C:\Users\Public\Documents\National Instruments\NI-HSDIO\Documentation

    Only very basic functionality is implemented.

    Tested with

    - PCI-6541
    - PXI-6542

    Args:
        name: Name for this instrument
        resource: Identifier for this instrument in NI MAX.
        dll_path: path to the NI-HSDIO library DLL. If not provided, use the
            default location,
            ``C:\Program Files\IVI Foundation\IVI\bin\NiHSDIO_64.dll``.
        id_query: whether to perform an ID query on initialization
        reset_device: whether to reset the device on initialization
    """

    # default DLL location
    dll_path = r"C:\Program Files\IVI Foundation\IVI\bin\niHSDIO_64.dll"
    # C:\Program Files (x86)\IVI Foundation\IVI\bin\niHSDIO.dll for 32-bit

    def __init__(self, name: str, resource: str,
                 dll_path: Optional[str] = None,
                 session_type: str = 'Generation',
                 id_query: bool = False,
                 reset_device: bool = False,
                 **kwargs):

        super().__init__(name, **kwargs)

        assert session_type in ['Generation', 'Acquisition'], 'NIHSDIO session must be either Generation or Acquisition'

        self._session_type = session_type

        self.resource = resource

        self.wrapper = NIHSDIODLLWrapper(dll_path=dll_path or self.dll_path, session_type=self._session_type)

        self._handle = self.init(id_query=id_query,
                                 reset_device=reset_device)

        # Wrap DLL calls
        self.wrapper.Initiate = self.wrapper.wrap_dll_function_checked(  # type: ignore[attr-defined]
                name_in_library="Initiate",
                argtypes=[NamedArgType("vi", ViSession)]
                )

        self.wrapper.Abort = self.wrapper.wrap_dll_function_checked(  # type: ignore[attr-defined]
                name_in_library="Abort",
                argtypes=[NamedArgType("vi", ViSession)])
        
        self.wrapper.AssignDynamicChannels = self.wrapper.wrap_dll_function_checked(  # type: ignore[attr-defined]
                name_in_library="AssignDynamicChannels",
                argtypes=[NamedArgType("vi", ViSession),
                          NamedArgType("channelList", ViConstString)])

        self.wrapper.AssignStaticChannels = self.wrapper.wrap_dll_function_checked(  # type: ignore[attr-defined]
                name_in_library="AssignStaticChannels",
                argtypes=[NamedArgType("vi", ViSession),
                          NamedArgType("channelList", ViConstString)])

        self.wrapper.WaitUntilDone = self.wrapper.wrap_dll_function_checked(  # type: ignore[attr-defined]
                name_in_library="WaitUntilDone",
                argtypes=[NamedArgType("vi", ViSession),
                          NamedArgType("maxTimeMilliseconds", ViInt32)])

        self.wrapper.ExportSignal = self.wrapper.wrap_dll_function_checked(  # type: ignore[attr-defined]
                name_in_library="ExportSignal",
                argtypes=[NamedArgType("vi", ViSession),
                          NamedArgType("signal", ViInt32),
                          NamedArgType("signalIdentifier", ViConstString),
                          NamedArgType("outputTerminal", ViConstString)])

        self.wrapper.DataPosition = self.wrapper.wrap_dll_function_checked(  # type: ignore[attr-defined]
                name_in_library="ConfigureDataPosition",
                argtypes=[NamedArgType("vi", ViSession),
                          NamedArgType("channelList", ViConstString),
                          NamedArgType("position", ViInt32)])

        # wrap the ConfigureVoltage function family
        volt_chan = ['Data', 'Trigger', 'Event']
        for chan in volt_chan:
            setattr(self.wrapper, f'Configure{chan}VoltageLogicFamily',
                    self.wrapper.wrap_dll_function_checked(  # type: ignore[attr-defined]
                        name_in_library=f'Configure{chan}VoltageLogicFamily',
                        argtypes=[NamedArgType("vi", ViSession),
                                  NamedArgType("channelList", ViConstString),
                                  NamedArgType("logicFamily", ViInt32)]))

            setattr(self.wrapper, f'Configure{chan}VoltageCustomLevels',
                    self.wrapper.wrap_dll_function_checked(  # type: ignore[attr-defined]
                        name_in_library=f'Configure{chan}VoltageCustomLevels',
                        argtypes=[NamedArgType("vi", ViSession),
                                  NamedArgType("channelList", ViConstString),
                                  NamedArgType("lowLevel", ViReal64),
                                  NamedArgType("highLevel", ViReal64)]))

        # wrap the WriteNamedWaveform function family
        numeric_format = ['U32', 'U16', 'U8']
        for format in numeric_format:
            setattr(self.wrapper, f'WriteNamedWaveform{format}',
                    self.wrapper.wrap_dll_function_checked(  # type: ignore[attr-defined]
                        name_in_library=f'WriteNamedWaveform{format}',
                        argtypes=[NamedArgType("vi", ViSession),
                                  NamedArgType("waveformName", ViConstString),
                                  NamedArgType("samplesToWrite", ViInt32),]))

        self.wrapper.WriteNamedWaveformFromFileHWS = self.wrapper.wrap_dll_function_checked(  # type: ignore[attr-defined]
                name_in_library="WriteNamedWaveformFromFileHWS",
                argtypes=[NamedArgType("vi", ViSession),
                          NamedArgType("waveformName", ViConstString),
                          NamedArgType("filePath", ViConstString),
                          NamedArgType("useRateFromWaveform", ViBoolean),])

        self.wrapper.WriteNamedWaveformWDT = self.wrapper.wrap_dll_function_checked(  # type: ignore[attr-defined]
                name_in_library="WriteNamedWaveformWDT",
                argtypes=[NamedArgType("vi", ViSession),
                          NamedArgType("waveformName", ViConstString),
                          NamedArgType("samplesToWrite", ViInt32),
                          NamedArgType("dataLayout", ViInt32),])

        self.add_parameter(name='dynamic_channels',
                           label='Dynamic Channels',
                           get_cmd=partial(self.get_attribute,
                                           NIHSDIO_ATTR_DYNAMIC_CHANNELS),
                           set_cmd=self._assign_dynamic_channels
                          )

        self.add_parameter(name='static_channels',
                           label='Static Channels',
                           get_cmd=partial(self.get_attribute,
                                           NIHSDIO_ATTR_STATIC_CHANNELS),
                           set_cmd=self._assign_static_channels
                          )

        self.add_parameter(name="ref_clock_source",
                           label="Reference clock source",
                           docstring="Specify the reference clock source for "
                           "the device. See the ``vals`` attribute for valid "
                           "values.",
                           get_cmd=partial(self.get_attribute,
                                           NIHSDIO_ATTR_REF_CLOCK_SOURCE),
                           set_cmd=partial(self.set_attribute,
                                           NIHSDIO_ATTR_REF_CLOCK_SOURCE),
                           val_mapping=REF_CLK_SRC_MAP,
                           )

        self.add_parameter(name="ref_clock_rate",
                           label="Reference clock rate",
                           docstring="Specify the reference clock rate for "
                           "the device. See the ``vals`` attribute for valid "
                           "values.",
                           unit='Hz',
                           get_cmd=partial(self.get_attribute,
                                           NIHSDIO_ATTR_REF_CLOCK_RATE),
                           set_cmd=partial(self.set_attribute,
                                           NIHSDIO_ATTR_REF_CLOCK_RATE),
                           )

        self.add_parameter(name="sample_clock_source",
                           label="Sample clock source",
                           docstring="Specify the sample clock source for "
                           "the device. See the ``vals`` attribute for valid "
                           "values.",
                           get_cmd=partial(self.get_attribute,
                                           NIHSDIO_ATTR_SAMPLE_CLOCK_SOURCE),
                           set_cmd=partial(self.set_attribute,
                                           NIHSDIO_ATTR_SAMPLE_CLOCK_SOURCE),
                           val_mapping=SAMPLE_CLK_SRC_MAP,
                           )

        self.add_parameter(name="sample_clock_rate",
                           label="Reference clock rate",
                           docstring="Specify the sample clock rate for "
                           "the device. See the ``vals`` attribute for valid "
                           "values.",
                           unit='Hz',
                           get_cmd=partial(self.get_attribute,
                                           NIHSDIO_ATTR_SAMPLE_CLOCK_RATE),
                           set_cmd=partial(self.set_attribute,
                                           NIHSDIO_ATTR_SAMPLE_CLOCK_RATE),
                           )

        self.add_parameter(name="repeat_mode",
                           label="Repeat mode",
                           get_cmd=partial(self.get_attribute,
                                           NIHSDIO_ATTR_REPEAT_MODE),
                           set_cmd=partial(self.set_attribute,
                                           NIHSDIO_ATTR_REPEAT_MODE),
                           val_mapping={'finite': 16,
                                        'continuous': 17},
                           )

        self.add_parameter(name="repeat_count",
                           label="Repeat count",
                           get_cmd=partial(self.get_attribute,
                                           NIHSDIO_ATTR_REPEAT_COUNT),
                           set_cmd=partial(self.set_attribute,
                                           NIHSDIO_ATTR_REPEAT_COUNT),
                           )

        self.connect_message()

    def initiate(self):
        """
        Initiate generation/acquisition. This causes the NI-HSDIO device to leave
        the Configuration state.
        """
        self.wrapper.Initiate(self._handle)

    def abort(self):
        """
        Stop generation/acquisition and return to the Configuration state.
        """
        self.wrapper.Abort(self._handle)

    def reset_device(self):
        """
        Reset the device to its Initial state and reload its FPGA.
        """
        self.wrapper.reset_device(self._handle)

    def init(self, id_query: bool = False,
            reset_device: bool = False) -> ViSession:
        """
        Call the wrapped init function from the library

        Args:
            id_query: whether to perform an ID query
            reset_device: whether to reset the device

        Returns:
            the ViSession handle of the initialized device
        """
        return self.wrapper.init(self.resource, id_query=id_query,
                                 reset_device=reset_device)

    def configure_export_signal(self, signal: str, output_terminal: str, signal_identifier: str=''):
        """
        Call the wrapped ExportSignal function from the library

        Args:
            signal (str): Signal (clock, trigger, or event) to export.
            outputTerminal (str): Output terminal where the signal is exported.
            signalIdentifier (str, optional): Describes the signal being exported.
                                              Defaults to ''.
        """
        assert signal in SIGNAL.keys(), "Unsupported output signal."
        assert output_terminal in OUTPUT_TERMINAL, "Unsupported output terminal."

        self.wrapper.ExportSignal(self._handle, ViInt32(SIGNAL[signal]),
                                  c_str(signal_identifier),c_str(output_terminal))

    def configure_voltage(self, channel: Literal['Data', 'Trigger', 'Event'],
                          type: Literal['LogicFamily', 'CustomLevels'],
                          channel_list: str='', logic_family: str='5.0V',
                          low_level: float=0, high_level: float=5):
        """
        Call the wrapped ConfigureVoltage function family from the library

        Args:
            channel ({'Data', 'Trigger', 'Event'}): Channel to configure.
            type ({'LogicFamily', 'CustomLevels'}): Configuration type.
            channel_list (str, optional): Digital channels to configure. Defaults to ''.
            logic_family (str, optional): The logic family for the data voltage levels. Defaults to '5.0V'.
            low_level (float, optional): Voltage that identifies low level. Only required when type is 'CustomLevels'. Defaults to 0.
            high_level (float, optional): Voltage that identifies low level. Only required when type is 'CustomLevels'. Defaults to 5.
        """

        if type == 'LogicFamily':
            func = getattr(self.wrapper, f'Configure{channel}VoltageLogicFamily')
            func(self._handle, ViConstString(c_str(channel_list)), ViInt32(LOGIC_FAMILY[logic_family]))
        else:
            func = getattr(self.wrapper, f'Configure{channel}VoltageCustomLevels')
            func(self._handle, ViConstString(c_str(channel_list)), ViReal64(low_level), ViReal64(high_level))

    def write_named_waveform_WDT(self, name: str, num_of_channels: int, waveform: list, data_layout='group_by_channel'):
        """
        Call the wrapped WriteNamedWaveformWDT function from the library

        Args:
            name (str): The name to associate with the allocated waveform memory.
            num_of_channels (int): Number of output channels.
            waveform (list): The digital waveform data. The list has a shape of (number of channels)*(number of samples)
            data_layout ({'group_by_channel', 'group_by_sample'}): The layout of the waveform contained in waveform.
        """
        if data_layout not in DATA_LAYOUT.keys():
            raise ValueError("data_layout must be either 'group_by_sample' or 'group_by_channel'!")
        
        waveform_length = len(waveform)
        waveform_length_per_channel = int(waveform_length/num_of_channels)

        # expand the waveform list by inserting 0's in front of actual values
        # expanded_waveform = [0]*(waveform_length*num_of_channels)
        # for i in range(waveform_length):
        #     expanded_waveform[int(num_of_channels*(i+1)-1)] = waveform[i]

        # waveform = (ctypes.c_uint8*(waveform_length*num_of_channels))(*expanded_waveform)
        waveform = (ctypes.c_uint8*(waveform_length))(*waveform)

        self.wrapper.WriteNamedWaveformWDT(self._handle,
                                           ViConstString(c_str(name)),
                                           ViInt32(waveform_length_per_channel),
                                           ViInt32(DATA_LAYOUT[data_layout]),
                                           byref(waveform))

    def configure_data_position(self, position: str, channel_list: str=''):
        assert position in DATA_POSITION.keys(), 'Unsupported data position'

        self.wrapper.DataPosition(self._handle, ViConstString(c_str(channel_list)),
                                  ViInt32(DATA_POSITION[position]))

    def wait_until_done(self, max_time_milliseconds: int = 10000):
        self.wrapper.WaitUntilDone(self._handle, ViInt32(max_time_milliseconds))

    def _assign_dynamic_channels(self, channelList: str):
        self.wrapper.AssignDynamicChannels(self._handle, c_str(channelList))

    def _assign_static_channels(self, channelList: str):
        self.wrapper.AssignStaticChannels(self._handle, c_str(channelList))

    def reset(self):
        self.wrapper.reset(self._handle)

    def get_attribute(self, attr: AttributeWrapper) -> Any:
        return self.wrapper.get_attribute(self._handle, attr)

    def set_attribute(self, attr: AttributeWrapper, set_value: Any):
        self.wrapper.set_attribute(self._handle, attr, set_value)

    def close(self):
        if getattr(self, "_handle", None):
            self.wrapper.close(self._handle)
        super().close()

    @property
    def session_type(self):
        return self._session_type

    @property
    def clock_configurations(self):
        return {'Reference clock source': self.get_attribute(NIHSDIO_ATTR_REF_CLOCK_SOURCE),
                'Reference clock rate': self.get_attribute(NIHSDIO_ATTR_REF_CLOCK_RATE),
                'Reference clock impedance': self.get_attribute(NIHSDIO_ATTR_REF_CLOCK_IMPEDANCE),
                'Sample clock source': self.get_attribute(NIHSDIO_ATTR_SAMPLE_CLOCK_SOURCE),
                'Sample clock rate': self.get_attribute(NIHSDIO_ATTR_SAMPLE_CLOCK_RATE),
                'Sample clock impedance': self.get_attribute(NIHSDIO_ATTR_SAMPLE_CLOCK_IMPEDANCE)}

    @property
    def serial(self) -> str:
        return self.get_attribute(NIHSDIO_ATTR_SERIAL_NUMBER)

    @property
    def data_width(self):
        return self.get_attribute(NIHSDIO_ATTR_DATA_WIDTH)

    def get_idn(self):
        return {
                "vendor": 'National Instruments',
                "model": 'HSDIO',
                "serial": self.serial
        }

# shorthand alias for the above
NI_HSDIO = NationalInstruments_HSDIO
