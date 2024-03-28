from .sdx import SiglentSDx

from enum import Enum
from attr import dataclass

import re
import numpy as np
import numpy.typing as npt

from typing import Callable, Tuple


class TriggerMode(Enum):
    AUTO = "AUTO"
    NORMAL = "NORM"
    SINGLE = "SINGLE"
    STOP = "STOP"

    def __str__(self):
        return self.value


@dataclass
class WaveformSetup:
    """
    Waveform download setup

    spacing
        SP: 0 or 1 = every point, n = every n-th

    num_points:
        NP: 0 = default, all

    start_idx
        FP: 0 is default
    """

    spacing: int = 1
    num_points: int = 0
    start_idx: int = 0


# Not a proper QCoDeS instrument
# TODO: Add channels, add parameters, add parameter axes
class Siglent_SDS_120NxE(SiglentSDx):
    """
    Siglent SDS 1202/1204xE
    """

    def get_time_base(
        self,
        channel: int = 1,
        *,
        _RE=re.compile(r"^TDIV[ ]*([0-9eE+\-.,]+)[ ]*[sS]$"),
    ) -> int:
        response = self.ask("TDIV?")
        groups = _RE.match(response)
        assert groups is not None
        value = float(groups[1].replace(",", "."))
        return int(value)

    def get_num_samples(
        self,
        channel: int = 1,
        *,
        _RE=re.compile(r"^SANU[ ]*([0-9eE+\-.,]+)[ ]*([kK]?)[ ]*pts$"),
    ) -> int:
        response = self.ask(f"SANU? C{channel:d}")
        groups = _RE.match(response)
        assert groups is not None
        value = float(groups[1].replace(",", "."))
        if groups[2]:
            value *= 1000
        return int(value)

    def get_sample_rate(
        self,
        *,
        _RE=re.compile(r"^SARA[ ]*([0-9eE+\-.,]+)[ ]*([kKMG]?)[ ]*[sS]a[ ]*/[ ]*s$"),
    ) -> int:
        response = self.ask("SARA?")
        groups = _RE.match(response)
        assert groups is not None
        value = float(groups[1].replace(",", "."))
        multiplier = {
            "k": 1e3,
            "K": 1e3,
            "M": 1e6,
            "G": 1e9,
        }
        value *= multiplier.get(groups[2], 1.0)
        return int(value)

    def get_vdiv(
        self,
        channel: int = 1,
        *,
        _RE=re.compile(r"^C[0-9]+:VDIV[ ]*([0-9eE+\-.,]+)[ ]*V$"),
    ) -> float:
        response = self.ask(f"C{channel:d}:VDIV?")
        groups = _RE.match(response)
        assert groups is not None
        value = float(groups[1].replace(",", "."))
        return value

    def get_ofst(
        self,
        channel: int = 1,
        *,
        _RE=re.compile(r"^C[0-9]+:OFST[ ]*([0-9eE+\-.,]+)[ ]*V$"),
    ) -> float:
        response = self.ask(f"C{channel:d}:OFST?")
        groups = _RE.match(response)
        assert groups is not None
        value = float(groups[1].replace(",", "."))
        return value

    def get_raw_analog_waveform_data(self, channel: int = 1) -> npt.NDArray:
        return self.visa_handle.query_binary_values(
            f"C{channel:d}:WF? DAT2",
            "b",
            header_fmt="ieee",
            container=np.array,  # type: ignore
        )

    def get_math_vdiv(
        self,
        *,
        _RE=re.compile(r"^MTVD[ ]*([0-9eE+\-.,]+)[ ]*V$"),
    ) -> float:
        response = self.ask("MTVD?")
        groups = _RE.match(response)
        assert groups is not None
        value = float(groups[1].replace(",", "."))
        return value

    def get_raw_math_waveform_data(self) -> npt.NDArray:
        self.write("MATH:WF? DAT2")
        len_prefix = len("MATH:WF ALL,")
        response_header = self.visa_handle.read_bytes(count=len_prefix)  # noqa: F841
        return self.visa_handle.read_binary_values(
            "b",
            header_fmt="ieee",
            container=np.array,  # type: ignore
        )

    def get_raw_digital_waveform_data(self, channel: int = 0) -> npt.NDArray:
        "Returns digital data. Each bit will be"
        self.write(f"D{channel:d}:WF? DAT2")
        len_prefix = len(f"D{channel:d}:WF ALL,")
        response_part1 = self.visa_handle.read_bytes(count=len_prefix)  # noqa: F841
        return self.visa_handle.read_binary_values(
            "B",
            header_fmt="ieee",
            container=np.array,  # type: ignore
        )

    def get_channel_waveform_data(self, channel: int) -> npt.NDArray:
        Vdiv = self.get_vdiv(channel)
        Vofs = self.get_ofst(channel)
        return Vdiv * self.get_raw_analog_waveform_data(channel) / 25 + Vofs

    def _get_waveform_axis(
        self,
        sample_rate: float,
        wfsu: WaveformSetup,
        get_num_samples: Callable[[], int],
    ) -> npt.NDArray:
        num_points = wfsu.num_points if wfsu.num_points != 0 else get_num_samples()
        spacing = wfsu.spacing if wfsu.spacing != 0 else 1
        start_idx = wfsu.start_idx

        return (np.arange(num_points) * spacing + start_idx) / sample_rate

    def get_channel_waveform(self, channel: int) -> Tuple[npt.NDArray, npt.NDArray]:
        sample_rate = self.get_sample_rate()
        wfsu = self.get_waveform_setup()
        data = self.get_channel_waveform_data(channel)
        axis = self._get_waveform_axis(
            sample_rate, wfsu, get_num_samples=lambda: len(data)
        )
        return (axis, data)

    def get_math_waveform(self) -> npt.NDArray:
        MtDiv = self.get_math_vdiv()
        return MtDiv * self.get_raw_math_waveform_data() / 25

    # don't use this. fft data can't be downloaded
    def set_to_fft(self, channel: int):
        self.write(f"DEFINE EQN,'FFTC{channel:d}'")

    def get_trig_mode(self) -> TriggerMode:
        response = self.ask("TRIG_MODE?")
        tail = len("TRMD ")
        return TriggerMode(response[tail:])

    def set_trig_mode(self, mode: TriggerMode):
        self.write(f"TRIG_MODE {mode.value}")

    def get_waveform_setup(
        self,
        *,
        _RE=re.compile(
            "WFSU [ ]*SP[ ]*,[ ]*([0-9]+),[ ]*NP[ ]*,[ ]*([0-9]+),[ ]*FP[ ]*,[ ]*([0-9]+)",  # noqa: E501
            re.IGNORECASE,
        ),
    ) -> WaveformSetup:  # (SP, NP, FP)
        response = self.ask("WFSU?")
        groups = _RE.match(response)
        assert groups is not None
        return WaveformSetup(
            spacing=int(groups[1]), num_points=int(groups[2]), start_idx=int(groups[3])
        )

    def set_waveform_setup(self, wfsu: WaveformSetup):
        self.write(f"WFSU SP,{wfsu.spacing},NP,{wfsu.num_points},FP,{wfsu.start_idx}")
