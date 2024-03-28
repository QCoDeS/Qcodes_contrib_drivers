from collections import ChainMap
from qcodes.instrument.channel import InstrumentChannel
from qcodes.instrument.instrument_base import InstrumentBase
from qcodes.instrument.visa import VisaInstrument

from struct import unpack as struct_unpack


class SiglentChannel(InstrumentChannel):
    def __init__(self, parent: InstrumentBase, name: str, channel_number: int):
        self._channel_number = channel_number
        super().__init__(parent, name)

    @property
    def channel_number(self):
        return self._channel_number


class SiglentSDx(VisaInstrument):
    def __init__(self, *args, **kwargs):
        kwargs = ChainMap(kwargs, {"terminator": "\n"})
        super().__init__(*args, **kwargs)
        self.visa_handle.response_delay = 0.25
        self.connect_message()

    def reset(self):
        self.write("*RST")

    def screen_dump_bmp(self, file_name):
        """
        Save screen dump to `file_name`
        .bmp extension automatically appended
        """
        data_bytes = self.scdp_bmp_bytes()

        with open(file_name + ".bmp", "wb") as f:
            f.write(data_bytes)

    def scdp_bmp_bytes(self) -> bytes:
        """
        Return SCreen DumP BitMaP as bytes.
        """
        BMP_HEADER_SIZE = 0x14
        LEN_TERMCHAR = 1
        visa_handle = self.visa_handle
        visa_handle.write_raw(b"SCDP")

        header_bytes = visa_handle.read_bytes(
            count=BMP_HEADER_SIZE, break_on_termchar=False
        )
        (bmp_file_size,) = struct_unpack("<i", header_bytes[2:6])
        data_bytes = visa_handle.read_bytes(
            count=(bmp_file_size - BMP_HEADER_SIZE + LEN_TERMCHAR),
            break_on_termchar=False,
        )
        return header_bytes + data_bytes[:-LEN_TERMCHAR]
