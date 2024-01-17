"""Interface to the Andor dll post-processing functions.

Functions are implemented as classes so that parameters are persistent
when snapshotted.
"""
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
@dataclasses.dataclass
class PostProcessingFunction(Protocol):
    """Protocol specifying a valid, stateful post-processing function."""

    def __call__(self, input_image: npt.NDArray[np.int32]) -> npt.NDArray[np.int32]:
        pass

    def _JSONEncoder(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class Identity(PostProcessingFunction):
    """Returns a copy of the input image."""

    def __call__(self, input_image: npt.NDArray[np.int32]) -> npt.NDArray[np.int32]:
        return np.copy(input_image)


@dataclasses.dataclass
class NoiseFilter(PostProcessingFunction):
    """
    This function will apply a filter to the input image and return the
    processed image in the output buffer.

    The filter applied is chosen by the user by setting Mode to a
    permitted value.

    Parameters
    ----------
    int Baseline:
        The baseline associated with the image.
    int Mode:
        The mode to use to process the data. Valid options are:

        = ==============================
        1 Use Median Filter
        2 Use Level Above Filter
        3 Use Interquartile Range Filter
        4 Use Noise Threshold Filter
        = ==============================

    float Threshold:
        This is the Threshold multiplier for the Median, Interquartile
        and Noise Threshold filters. For the Level Above filter this is
        Threshold count above the baseline.

    """
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
class PhotonCounting(PostProcessingFunction):
    """
    This function will convert the input image data to photons and
    return the processed image in the output buffer.

    Parameters
    ----------
    float * Threshold:
        The Thresholds used to define a photon.

    """
    atmcd64d: atmcd64d = dataclasses.field(repr=False)
    thresholds: Sequence[float]

    def __call__(self, input_image: npt.NDArray[np.int32]) -> npt.NDArray[np.int32]:
        num_frames, height, width = input_image.shape
        output_image = self.atmcd64d.post_process_photon_counting(input_image.reshape(-1),
                                                                  num_frames, num_frames,
                                                                  self.thresholds, height, width)
        return output_image.reshape(input_image.shape)


@dataclasses.dataclass
class CountConvert(PostProcessingFunction):
    # TODO (thangleiter): untested because unavailable.
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
