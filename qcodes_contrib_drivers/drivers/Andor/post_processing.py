import dataclasses
import enum
from typing import Protocol, Sequence, runtime_checkable

import numpy as np
import numpy.typing as npt

from .private.andor_sdk import atmcd64d


class NoiseFilterMode(enum.IntEnum):
    median = 1
    level_above = 2
    interquartile_range = 3
    noise_threshold = 4


class CountConversionMode(enum.IntEnum):
    electrons = 1
    photons = 2


@runtime_checkable
class PostProcessingFunction(Protocol):

    def __call__(self, input_image: npt.NDArray[np.int32]) -> npt.NDArray[np.int32]:
        pass


@dataclasses.dataclass
class NoiseFilter:
    atmcd64d: atmcd64d = dataclasses.field(repr=False)
    baseline: int
    mode: NoiseFilterMode
    threshold: float

    def __call__(self, input_image: npt.NDArray[np.int32]) -> npt.NDArray[np.int32]:
        height, width = input_image.shape[-2:]
        output_image = self.atmcd64d.post_process_noise_filter(input_image.reshape(-1),
                                                               self.baseline, self.mode.value,
                                                               self.threshold, height, width)
        return output_image.reshape(input_image.shape)


@dataclasses.dataclass
class PhotonCounting:
    atmcd64d: atmcd64d = dataclasses.field(repr=False)
    thresholds: Sequence[float]

    def __call__(self, input_image: npt.NDArray[np.int32]) -> npt.NDArray[np.int32]:
        num_frames, height, width = input_image.shape
        output_image = self.atmcd64d.post_process_photon_counting(input_image.reshape(-1),
                                                                  num_frames, num_frames,
                                                                  self.thresholds, height, width)
        return output_image.reshape(input_image.shape)


@dataclasses.dataclass
class CountConvert:
    atmcd64d: atmcd64d = dataclasses.field(repr=False)
    baseline: int
    mode: CountConversionMode
    em_gain: int
    quantum_efficiency: float
    sensitivity: float = 0.0

    def __call__(self, input_image: npt.NDArray[np.int32]) -> npt.NDArray[np.int32]:
        num_frames, height, width = input_image.shape
        output_image = self.atmcd64d.post_process_count_convert(input_image.reshape(-1),
                                                                num_frames, self.baseline,
                                                                self.mode.value, self.em_gain,
                                                                self.quantum_efficiency,
                                                                self.sensitivity, height, width)
        return output_image.reshape(input_image.shape)
