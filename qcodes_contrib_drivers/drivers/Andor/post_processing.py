"""Interface to the Andor dll post-processing functions.

Functions are implemented as classes so that parameters are persistent
when snapshotted.
"""
import dataclasses
import enum
from typing import Any, Protocol, runtime_checkable

import numpy as np
import numpy.typing as npt

from .private import andor_sdk


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
    """Protocol specifying a valid, stateful post-processing function.

    Note that the input image should always be a 3d array (num_frames,
    num_ypx, num_xpx).
    """

    def __call__(self, input_image: npt.NDArray[np.int32]) -> npt.NDArray[np.int32]:
        pass

    def _JSONEncoder(self) -> dict[str, Any]:
        asdict = dataclasses.asdict(self)
        asdict.pop('atmcd64d', None)
        return asdict


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
    baseline: int
    mode: NoiseFilterMode
    threshold: float
    atmcd64d: andor_sdk.atmcd64d | None = dataclasses.field(default=None, repr=False)

    def __call__(self, input_image: npt.NDArray[np.int32]) -> npt.NDArray[np.int32]:
        if self.atmcd64d is None:
            raise RuntimeError('Provide an atmcd64d instance to use this function')
        _, height, width = input_image.shape
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
        The Thresholds used to define a photon (min and max)

    """
    thresholds: tuple[int, int]
    atmcd64d: andor_sdk.atmcd64d | None = dataclasses.field(default=None, repr=False)

    def __call__(self, input_image: npt.NDArray[np.int32]) -> npt.NDArray[np.int32]:
        if self.atmcd64d is None:
            raise RuntimeError('Provide an atmcd64d instance to use this function')
        num_images, height, width = input_image.shape
        # ??? Unclear from documentation what difference num_frames makes.
        num_frames = num_images
        output_image = self.atmcd64d.post_process_photon_counting(input_image.reshape(-1),
                                                                  num_images, num_frames,
                                                                  self.thresholds, height, width)
        return output_image.reshape(input_image.shape)


@dataclasses.dataclass
class CountConvert(PostProcessingFunction):
    # TODO (thangleiter): untested because unavailable.
    baseline: int
    mode: CountConversionMode
    em_gain: int
    quantum_efficiency: float
    sensitivity: float = 0.0
    atmcd64d: andor_sdk.atmcd64d | None = dataclasses.field(default=None, repr=False)

    def __call__(self, input_image: npt.NDArray[np.int32]) -> npt.NDArray[np.int32]:
        if self.atmcd64d is None:
            raise RuntimeError('Provide an atmcd64d instance to use this function')
        num_frames, height, width = input_image.shape
        output_image = self.atmcd64d.post_process_count_convert(input_image.reshape(-1),
                                                                num_frames, self.baseline,
                                                                self.mode.value, self.em_gain,
                                                                self.quantum_efficiency,
                                                                self.sensitivity, height, width)
        return output_image.reshape(input_image.shape)
