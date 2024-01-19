"""Qcodes driver for Andor iDus 4xx cameras.

Tested with a Andor iDus 416. A typical workflow would look something
like this::
    ccd = AndorIDus4xx('ccd')
    ccd.acquisition_mode('kinetics')
    ccd.read_mode('random track')
    ccd.preamp_gain(1.)
    ccd.number_accumulations(2)
    ccd.number_kinetics(10)
    ccd.random_track_settings((2, [20, 30, 40, 40]))
    # The following time parameters are computed to a closest valid
    # value by the SDK. Setting all to zero would hence result in the
    # shortest possible acquisition time. These values should be set
    # last since they depend on other settings.
    ccd.exposure_time(0)
    ccd.accumulation_cycle_time(0)
    ccd.kinetic_cycle_time(0)
    # Acquire data
    data = ccd.ccd_data()
    data.shape  # (10, 2, 2000)
    # The shape of the ccd_data parameter is automatically adjusted to
    # the acquisition and read modes
    ccd.acquisition_mode('single scan')
    ccd.read_mode('full vertical binning')
    data = ccd.ccd_data()
    data.shape  # (2000,)

TODO (thangleiter, 23/11/11):
    - Live monitor using 'run till abort' mode and async event queue
    - Triggering
    - Handle shutter modes
    - It might be smarter not to use :meth:`AndorIDus4xx.wait_for_acquisition`
      in :class:`CCDData` since it will lock the dll away forever if there are
      incorrect acquisition settings or it's waiting for a trigger that never
      comes. This might lead to a reboot of the computer being required.

"""
import itertools
import operator
import textwrap
import time
from collections import abc
from functools import partial, wraps
from typing import Any, Callable, Dict, Literal, Optional, Sequence, Tuple, TypeVar

import numpy as np
import numpy.typing as npt
from qcodes import validators
from qcodes.instrument import Instrument
from qcodes.parameters import (ParameterBase, ParamRawDataType, DelegateParameter,
                               ManualParameter, MultiParameter, Parameter, ParameterWithSetpoints)
from qcodes.parameters.cache import _Cache, _CacheProtocol
from qcodes.utils.helpers import create_on_off_val_mapping
from tqdm import tqdm

from . import post_processing
from .private.andor_sdk import SDKError, atmcd64d

_T = TypeVar('_T')


@wraps(textwrap.dedent)
def dedent(text: str | None) -> str | None:
    """Wrap textwrap.dedent for mypy for use with __doc__ attributes."""
    return textwrap.dedent(text) if text is not None else None


class _HeterogeneousSequence(validators.Validator[Sequence[Any]]):
    """A validator for heterogeneous sequences."""

    def __init__(
            self,
            elt_validators: Sequence[validators.Validator[Any]] = (validators.Anything(),)
    ) -> None:
        self._elt_validators = elt_validators
        self._valid_values = ([vval for vval in itertools.chain(*(
            elt_validator._valid_values for elt_validator in self._elt_validators
        ))],)

    def validate(self, value: Sequence[Any], context: str = "") -> None:
        if not isinstance(value, Sequence):
            raise TypeError(f"{value!r} is not a sequence; {context}")
        if len(value) != self.length:
            raise ValueError(
                f"{value!r} has not length {self.length} but {len(value)}"
            )
        for elt, validator in zip(value, self._elt_validators):
            if not isinstance(validator, validators.Anything):
                validator.validate(elt)

    @property
    def elt_validators(self) -> Sequence[validators.Validator[Any]]:
        return self._elt_validators

    @property
    def length(self) -> int:
        return len(self.elt_validators)


class _PostProcessingCallable(validators.Validator[Callable[[npt.NDArray[np.int32]],
                              npt.NDArray[np.int32]]]):
    """A validator for post-processing functions."""

    def __init__(self) -> None:
        self._valid_values = (lambda x: x,)

    def __repr__(self) -> str:
        return '<Callable[[npt.NDArray[np.int32]], npt.NDArray[np.int32]>'

    def validate(self, value: abc.Callable[..., Any], context: str = "") -> None:
        if not callable(value) and isinstance(value, post_processing.PostProcessingFunction):
            raise TypeError(f"{value!r} is not a post-processing function; {context}")


class DetectorPixels(MultiParameter):
    """Stores the detector size in pixels."""

    def get_raw(self) -> Tuple[int, int]:
        if self.instrument is None:
            raise RuntimeError("No instrument attached to Parameter.")

        return self.instrument.atmcd64d.get_detector()


class PixelSize(MultiParameter):
    """Stores the pixel size in microns."""

    def get_raw(self) -> Tuple[float, float]:
        if self.instrument is None:
            raise RuntimeError("No instrument attached to Parameter.")

        return self.instrument.atmcd64d.get_pixel_size()


class DetectorSize(MultiParameter):
    """Stores the detector size in microns."""

    def get_raw(self) -> Tuple[float, float]:
        if self.instrument is None:
            raise RuntimeError("No instrument attached to Parameter.")

        px_x, px_y = self.instrument.atmcd64d.get_detector()
        size_x, size_y = self.instrument.atmcd64d.get_pizel_size()
        return px_x * size_x, px_y * size_y


class AcquiredPixels(MultiParameter):
    """Returns the shape of a single frame for the current settings."""

    def get_raw(self) -> Tuple[int, int]:
        if self.instrument is None:
            raise RuntimeError("No instrument attached to Parameter.")

        width, height = self.instrument.detector_pixels.get_latest()
        read_mode = self.instrument.read_mode.get_latest()
        if read_mode == 'image':
            hbin, vbin, hstart, hend, vstart, vend = self.instrument.image_settings.get()
            width = (hend - hstart + 1) // hbin
            height = (vend - vstart + 1) // vbin
        elif read_mode == 'multi track':
            height, *_ = self.instrument.multi_track_settings.get()
        elif read_mode == 'random track':
            height, _ = self.instrument.random_track_settings.get()
        elif read_mode in ('single track', 'full vertical binning'):
            height = 1

        return width, height


class SingleTrackSettings(MultiParameter):
    """Represents the settings for single-track acquisition."""

    def get_raw(self) -> Optional[Tuple[int, int]]:
        if self.instrument is None:
            raise RuntimeError("No instrument attached to Parameter.")

        return self.cache.get(False)

    def set_raw(self, val: Tuple[int, int]):
        if self.instrument is None:
            raise RuntimeError("No instrument attached to Parameter.")

        self.instrument.atmcd64d.set_single_track(*val)


class MultiTrackSettings(MultiParameter):
    """
    Represents the settings for multi-track acquisition.

    When setting, a sequence of *three* numbers (number, height, and
    offset).

    When getting, a tuple of *five* numbers (number, height, offset,
    bottom, gap) is returned. The last two are calculated by the dll
    function and are thus only available when getting.
    """
    # Bottom and gap are computed by the dll
    _bottom: Optional[int] = None
    _gap: Optional[int] = None

    def get_raw(self) -> Optional[Tuple[int, int, int, int, int]]:
        if self.instrument is None:
            raise RuntimeError("No instrument attached to Parameter.")

        val = self.cache.get(False)
        return tuple(val) + (self._bottom, self._gap) if val is not None else None

    def set_raw(self, val: Tuple[int, int, int]):
        if self.instrument is None:
            raise RuntimeError("No instrument attached to Parameter.")

        self._bottom, self._gap = self.instrument.atmcd64d.set_multi_track(*val)


class RandomTrackSettings(MultiParameter):
    """Represents the settings for random-track acquisition."""

    def get_raw(self) -> Optional[Tuple[int, ...]]:
        if self.instrument is None:
            raise RuntimeError("No instrument attached to Parameter.")

        return self.cache.get(False)

    def set_raw(self, val: Tuple[int, Sequence[int]]):
        if self.instrument is None:
            raise RuntimeError("No instrument attached to Parameter.")

        self.instrument.atmcd64d.set_random_tracks(*val)


class ImageSettings(MultiParameter):
    """Represents the settings for image acquisition."""

    def get_raw(self) -> Optional[Tuple[int, int, int, int, int, int]]:
        if self.instrument is None:
            raise RuntimeError("No instrument attached to Parameter.")

        return self.cache.get(False)

    def set_raw(self, val: Tuple[int, int, int, int, int, int]):
        if self.instrument is None:
            raise RuntimeError("No instrument attached to Parameter.")

        self.instrument.atmcd64d.set_image(*val)


class FastKineticsSettings(MultiParameter):
    """Represents fast kinetics settings."""

    def get_raw(self) -> Optional[Tuple[int, int, float, int, int, int, int]]:
        if self.instrument is None:
            raise RuntimeError("No instrument attached to Parameter.")

        return self.cache.get(False)

    def set_raw(self, val: Tuple[int, int, float, int, int, int, int]):
        if self.instrument is None:
            raise RuntimeError("No instrument attached to Parameter.")

        self.instrument.atmcd64d.set_fast_kinetics(*val)
        # Set the number of frames so that CCDData knows the correct
        # shape of the data.
        self.instrument.number_kinetics.set(val[1])
        # The exposure time always seems to be 0 in fast kinetics mode
        # self.instrument.exposure_time.set(val[2])
        self.instrument.read_mode.set(self.instrument.read_mode.inverse_val_mapping[val[3]])


class ParameterWithSetSideEffect(Parameter):
    """A :class:`Parameter` allowing for side effects on set events.

    Parameters
    ----------
    set_side_effect :
        A callable that is run before every set event. Receives the
        parameter instance and the set value as arguments.
    """

    def __init__(self, name: str, set_side_effect: Callable[[Parameter, Any], None],
                 **kwargs: Any) -> None:
        if not callable(set_cmd := kwargs.pop('set_cmd', False)):
            raise ValueError('ParameterWithSetSideEffect requires a set_cmd')

        def set_raw(value: ParamRawDataType) -> None:
            # Parameter does not allow overriding set_raw method
            set_side_effect(self, value)
            set_cmd(value)

        super().__init__(name, set_cmd=set_raw, **kwargs)


class PixelAxis(Parameter):
    """
    A parameter that enumerates the pixels along an axis.

    If you have a calibration of horizontal pixels to, for example in a
    spectrograph, wavelength at hand, set this parameter's get_parser
    and unit.
    """

    def __init__(self, name: str, dimension: Literal[0, 1], instrument: 'AndorIDus4xx',
                 **kwargs: Any) -> None:
        self.dimension = dimension
        super().__init__(name, instrument, **kwargs)

    def get_raw(self) -> npt.NDArray[np.int_]:
        if self.instrument is None:
            raise RuntimeError("No instrument attached to Parameter.")

        return np.arange(1, self.instrument.acquired_pixels.get()[self.dimension] + 1)


class TimeAxis(Parameter):
    """
    A parameter that holds the start of each exposure window.

    If the acquisition mode is a kinetic series, the size corresponds
    to number_kinetics(), otherwise it's always 1.
    """

    def get_raw(self) -> npt.NDArray[np.float64]:
        if self.instrument is None:
            raise RuntimeError("No instrument attached to Parameter.")

        n_pts = self.instrument.acquired_frames.get()
        dt = self.instrument.kinetic_cycle_time.get()
        return np.arange(0, dt * n_pts, dt)


class PersistentDelegateParameter(DelegateParameter):
    """A delegate parameter with an independent cache."""

    def __init__(self, name: str, source: Parameter | None, *args: Any, **kwargs: Any):
        super().__init__(name, source, *args, **kwargs)
        self.cache: _CacheProtocol = _Cache(self, max_val_age=kwargs.get('max_val_age', None))


class CCDData(ParameterWithSetpoints):
    """
    Parameter class for data taken with an Andor CCD.

    The data is saved in an integer array with dynamic shape depending
    on the acquisition and readout modes.

     - If the acquisition mode is a kinetic series, the first axis is a
       :class:`TimeAxis` with size the number of frames, otherwise it is
       empty.
     - The last axes correspond to the image dimensions, which may be 1d
       or 2d depending on the readout mode. If 2d, the y-axis (vertical
       dimension) is stored first.

    Note:

        In 2d mode, the last two axes are switched around compared to
        the rest of this driver.

    """
    _delegates: set['CCDDataDelegateParameter'] = set()

    def get_raw(self) -> npt.NDArray[np.int32]:
        if self.instrument is None:
            raise RuntimeError("No instrument attached to Parameter.")

        shape = tuple(setpoints.get().size for setpoints in self.setpoints)
        # Can use get_latest here since acquisition_mode and read_mode set parses
        # already take care of invalidating caches if things changed.
        number_frames = self.instrument.acquired_frames.get_latest()
        number_accumulations = self.instrument.acquired_accumulations.get_latest()
        number_pixels = np.prod(self.instrument.acquired_pixels.get_latest())

        # In fast kinetics mode, an acquisition event only occurs once per series,
        # not number_frames times like in regular kinetic series mode.
        if self.instrument.acquisition_mode.get_latest() != 'fast kinetics':
            number_acquisitions = number_frames
        else:
            number_acquisitions = 1

        # We decide here which method we use to fetch data from the SDK. The CCD
        # has a circular buffer, so we should fetch data during acquisition if
        # the desired result is larger.
        fetch_lazy = number_frames < self.instrument.atmcd64d.get_size_of_circular_buffer()

        # TODO (thangleiter): for fast kinetics, one might want to fetch a number of images
        #                     every few acquisitions.
        if fetch_lazy:
            data_buffer = np.empty(number_frames * number_pixels, dtype=np.int32)
        else:
            data_buffer = np.empty((number_frames, number_pixels), dtype=np.int32)

        if not self.instrument.status().startswith('DRV_ACQUIRING'):
            self.instrument.log.debug('Starting acquisition.')
            self.instrument.atmcd64d.start_acquisition()

        try:
            for frame in range(number_acquisitions):
                self.instrument.log.debug(f'Acquiring frame {frame}/{number_frames}.')

                for accumulation in range(number_accumulations):
                    self.instrument.log.debug('Acquiring accumulation '
                                              f'{accumulation}/{number_accumulations}.')
                    # TODO (thangleiter): If using an external trigger and it does not arrive for
                    #                     whatever reason, the interpreter will live here forever.
                    self.instrument.atmcd64d.wait_for_acquisition()

                if not fetch_lazy:
                    # TODO (thangleiter): For unforeseen reasons, this might fetch old data. Better
                    #                     to clear internal buffer before acquisition start?
                    self.instrument.log.debug(f'Fetching frame {frame}/{number_frames}.')
                    self.instrument.atmcd64d.get_oldest_image_by_reference(data_buffer[frame])

            if fetch_lazy:
                self.instrument.log.debug('Fetching all frames.')
                self.instrument.atmcd64d.get_acquired_data_by_reference(data_buffer.reshape(-1))
        except KeyboardInterrupt:
            self.instrument.log.debug('Aborted acquisition.')
            try:
                self.instrument.atmcd64d.abort_acquisition()
            except SDKError:
                pass

        self.instrument.log.debug('Finished acquisition.')
        return data_buffer.reshape(shape)

    def register_delegate(self, delegate: 'CCDDataDelegateParameter'):
        self._delegates.add(delegate)

    @property
    def setpoints(self) -> Sequence[ParameterBase]:
        # Only here for mypy: https://github.com/python/mypy/issues/5936
        return super().setpoints

    @setpoints.setter
    def setpoints(self, setpoints: Sequence[ParameterBase]) -> None:
        # https://github.com/python/mypy/issues/5936#issuecomment-1429175144
        ParameterWithSetpoints.setpoints.fset(self, setpoints)  # type: ignore[attr-defined]
        for delegate in self._delegates:
            delegate.setpoints = setpoints

    @property
    def vals(self) -> validators.Validator | None:
        # Only here for mypy: https://github.com/python/mypy/issues/5936
        return super().vals

    @vals.setter
    def vals(self, vals: validators.Validator | None) -> None:
        # https://github.com/python/mypy/issues/5936#issuecomment-1429175144
        ParameterWithSetpoints.vals.fset(self, vals)  # type: ignore[attr-defined]
        for delegate in self._delegates:
            delegate.vals = vals


class CCDDataDelegateParameter(DelegateParameter, ParameterWithSetpoints):
    """A DelegateParameter that can be used as a ParameterWithSetpoints."""

    def __init__(self, name: str, source: CCDData, **kwargs: Any):
        kwargs.setdefault('vals', getattr(source, 'vals'))
        kwargs.setdefault('setpoints', getattr(source, 'setpoints'))
        kwargs.setdefault('snapshot_get', getattr(source, '_snapshot_get'))
        kwargs.setdefault('snapshot_value', getattr(source, '_snapshot_value'))
        super().__init__(name, source, **kwargs)
        self._register_with_source(source)

    def _register_with_source(self, source):
        while not isinstance(source, CCDData):
            try:
                source = source.source
            except AttributeError:
                raise ValueError('Expected source to be CCData or delegate thereof.')
        source.register_delegate(self)


class AndorIDus4xx(Instrument):
    """
    Instrument driver for the Andor iDus 4xx family CCDs.

    Args:
        name: Instrument name.
        dll_path: Path to the atmcd64.dll file. If not set, a default path is used.
        camera_id: ID for the desired CCD.
        min_temperature: The minimum temperature of operation for the CCD. Defaults to the value
                         the model supports. Note that that might apply for water cooling only.

    Attributes:
        serial_number: Serial number of the CCD.
        head_model: Head model of the CCD.
        firmware_version: Firmware version of the CCD.
        firmware_build: Firmware build of the CCD.
        acquisition_mode_capabilities: Available acquisition modes.
        read_mode_capabilities: Available read modes.
        trigger_mode_capabilities: Available trigger modes.
        pixel_mode_capabilities: Bit-depth and color mode.
        feature_capabilities: Available camera and SDK features.

    """
    # For iDus models, there are only a single channel and amplifier each AFAIK
    _CHANNEL: int = 0
    _AMPLIFIER: int = 0

    # TODO (SvenBo90): implement further acquisition modes
    # TODO (SvenBo90): implement further trigger modes
    # TODO (SvenBo90): handle shutter closing and opening timings
    # TODO (thangleiter): implement further real-time filter modes

    def __init__(self, name: str, dll_path: Optional[str] = None, camera_id: int = 0,
                 min_temperature: Optional[int] = None, **kwargs):
        super().__init__(name, **kwargs)

        # link to dll
        self.atmcd64d = atmcd64d(dll_path=dll_path)

        # initialization
        self.atmcd64d.initialize(' ')
        self.atmcd64d.set_current_camera(self.atmcd64d.get_camera_handle(camera_id))

        # get camera information
        self.serial_number = self.atmcd64d.get_camera_serial_number()
        self.head_model = self.atmcd64d.get_head_model()
        self.firmware_version = self.atmcd64d.get_hardware_version()[4]
        self.firmware_build = self.atmcd64d.get_hardware_version()[5]
        self.acquisition_mode_capabilities = self.atmcd64d.get_capabilities()[0]
        self.read_mode_capabilities = self.atmcd64d.get_capabilities()[1]
        self.trigger_mode_capabilities = self.atmcd64d.get_capabilities()[2]
        self.pixel_mode_capabilities = self.atmcd64d.get_capabilities()[4]
        self.feature_capabilities = self.atmcd64d.get_capabilities()[5]

        # add the instrument parameters
        self.add_parameter('accumulation_cycle_time',
                           get_cmd=self.atmcd64d.get_acquisition_timings,
                           set_cmd=self.atmcd64d.set_accumulation_cycle_time,
                           get_parser=lambda ans: float(ans[1]),
                           max_val_age=0,
                           unit='s',
                           label='accumulation cycle time',
                           docstring=dedent(self.atmcd64d.set_accumulation_cycle_time.__doc__))

        self.add_parameter('cooler',
                           get_cmd=self.atmcd64d.is_cooler_on,
                           set_cmd=self._set_cooler,
                           val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
                           label='cooler',
                           docstring=dedent(self.atmcd64d.cooler_on.__doc__))

        self.add_parameter('cooler_mode',
                           set_cmd=self.atmcd64d.set_cooler_mode,
                           val_mapping={'maintain': 1, 'return': 0},
                           label='Cooler mode',
                           initial_value='return',
                           docstring=dedent("""
                           Determines whether the cooler is switched off when the camera is
                           shut down.

                           'maintain' means it is maintained on shutdown, 'return' means the
                           camera returns to ambient temperature. Defaults to 'return'.
                           """))

        self.add_parameter('cosmic_ray_filter_mode',
                           get_cmd=self.atmcd64d.get_filter_mode,
                           set_cmd=self.atmcd64d.set_filter_mode,
                           val_mapping=create_on_off_val_mapping(on_val=2, off_val=0),
                           label='Cosmic ray filter mode',
                           docstring=dedent(self.atmcd64d.set_filter_mode.__doc__))

        self.add_parameter('data_averaging_filter_mode',
                           get_cmd=self.atmcd64d.filter_get_data_averaging_mode,
                           set_cmd=self.atmcd64d.filter_set_data_averaging_mode,
                           val_mapping={'No Averaging Filter': 0,
                                        'Recursive Averaging Filter': 5,
                                        'Frame Averaging Filter': 6},
                           label='Data averaging filter mode',
                           docstring=dedent(self.atmcd64d.filter_set_data_averaging_mode.__doc__))

        self.add_parameter('data_averaging_filter_factor',
                           get_cmd=self.atmcd64d.filter_get_averaging_factor,
                           set_cmd=self.atmcd64d.filter_set_averaging_factor,
                           vals=validators.Ints(1),
                           label='Data averaging filter factor',
                           docstring=dedent(self.atmcd64d.filter_set_averaging_factor.__doc__))

        self.add_parameter('data_averaging_filter_frame_count',
                           get_cmd=self.atmcd64d.filter_get_averaging_frame_count,
                           set_cmd=self.atmcd64d.filter_set_averaging_frame_count,
                           vals=validators.Ints(1),
                           label='Data averaging filter frame count',
                           docstring=dedent(self.atmcd64d.filter_set_averaging_frame_count.__doc__))

        self.add_parameter('detector_size',
                           parameter_class=DetectorPixels,
                           names=('horizontal', 'vertical'),
                           shapes=((), ()),
                           units=('μm', 'μm'),
                           labels=('Horizontal chip size', 'Vertical chip size'),
                           docstring=DetectorPixels.__doc__,
                           snapshot_value=True)

        self.add_parameter('exposure_time',
                           get_cmd=self.atmcd64d.get_acquisition_timings,
                           set_cmd=self.atmcd64d.set_exposure_time,
                           get_parser=lambda ans: float(ans[0]),
                           max_val_age=0,
                           unit='s',
                           label='exposure time',
                           docstring=dedent(self.atmcd64d.set_exposure_time.__doc__))

        self.add_parameter('fast_kinetics_settings',
                           parameter_class=FastKineticsSettings,
                           names=('exposed_rows', 'series_length', 'time', 'mode', 'hbin',
                                  'vbin', 'offset'),
                           shapes=((), (), (), (), (), (), ()),
                           units=('px', 'px', 's', '', 'px', 'px', 'px'),
                           vals=_HeterogeneousSequence([validators.Ints(1), validators.Ints(1),
                                                        validators.Numbers(0),
                                                        validators.Enum(0, 4), validators.Ints(1),
                                                        validators.Ints(1), validators.Ints(0)]),
                           docstring=dedent(self.atmcd64d.set_fast_kinetics.__doc__),
                           snapshot_value=True)

        self.add_parameter('fast_external_trigger',
                           set_cmd=self.atmcd64d.set_fast_ext_trigger,
                           val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
                           label='Fast external trigger mode',
                           docstring=dedent(self.atmcd64d.set_fast_ext_trigger.__doc__))

        self.add_parameter('fastest_recommended_vertical_shift_speed',
                           get_cmd=self.atmcd64d.get_fastest_recommended_vs_speed,
                           get_parser=operator.itemgetter(1),
                           unit='μs/px',
                           docstring=dedent(
                               self.atmcd64d.get_fastest_recommended_vs_speed.__doc__
                           ))

        speeds = [round(self.atmcd64d.get_hs_speed(self._CHANNEL, self._AMPLIFIER, index), 3)
                  for index
                  in range(self.atmcd64d.get_number_hs_speeds(self._CHANNEL, self._AMPLIFIER))]
        self.add_parameter('horizontal_shift_speed',
                           label='Horizontal shift speed',
                           set_cmd=partial(self.atmcd64d.set_hs_speed, self._AMPLIFIER),
                           val_mapping={speed: index
                                        for index, speed in enumerate(speeds)} | {'Unset': -1},
                           initial_cache_value='Unset',
                           unit='MHz',
                           docstring=dedent(self.atmcd64d.set_hs_speed.__doc__))

        self.add_parameter('keep_clean_time',
                           get_cmd=self.atmcd64d.get_keep_clean_time,
                           unit='s',
                           label='Keep clean cycle duration',
                           docstring=dedent(self.atmcd64d.get_keep_clean_time.__doc__))

        self.add_parameter('kinetic_cycle_time',
                           get_cmd=self.atmcd64d.get_acquisition_timings,
                           set_cmd=self.atmcd64d.set_kinetic_cycle_time,
                           get_parser=lambda ans: float(ans[2]),
                           max_val_age=0,
                           unit='s',
                           label='Kinetic cycle time',
                           docstring=dedent(self.atmcd64d.set_kinetic_cycle_time.__doc__))

        self.add_parameter('multi_track_settings',
                           parameter_class=MultiTrackSettings,
                           names=('number', 'height', 'offset', 'bottom', 'gap'),
                           shapes=((), (), (), (), ()),
                           units=('px', 'px', 'px', 'px', 'px'),
                           vals=_HeterogeneousSequence([validators.Ints(1), validators.Ints(1),
                                                        validators.Ints(0)]),
                           docstring=dedent(self.atmcd64d.set_multi_track.__doc__),
                           snapshot_value=True)

        self.add_parameter('number_accumulations',
                           set_cmd=self.atmcd64d.set_number_accumulations,
                           initial_value=1,
                           label='number accumulations',
                           docstring=dedent(self.atmcd64d.set_number_accumulations.__doc__))

        self.add_parameter('number_kinetics',
                           set_cmd=self.atmcd64d.set_number_kinetics,
                           initial_value=1,
                           label='number of frames',
                           docstring=dedent(self.atmcd64d.set_number_kinetics.__doc__))

        self.add_parameter('detector_pixels',
                           parameter_class=DetectorPixels,
                           names=('horizontal', 'vertical'),
                           shapes=((), ()),
                           units=('px', 'px'),
                           labels=('Horizontal number of pixels', 'Vertical number of pixels'),
                           docstring=DetectorPixels.__doc__,
                           snapshot_value=True)

        self.add_parameter('pixel_size',
                           parameter_class=PixelSize,
                           names=('horizontal', 'vertical'),
                           shapes=((), ()),
                           units=('μm', 'μm'),
                           labels=('Horizontal pixel size', 'Vertical pixel size'),
                           docstring=PixelSize.__doc__,
                           snapshot_value=True)

        # Real-time photon counting
        self.add_parameter('photon_counting',
                           set_cmd=self.atmcd64d.set_photon_counting,
                           val_mapping=create_on_off_val_mapping(),
                           label='Photon counting enabled',
                           initial_cache_value=False,
                           docstring=dedent(self.atmcd64d.set_photon_counting.__doc__))

        no_of_divisions = self.atmcd64d.get_number_photon_counting_divisions()
        self.add_parameter('photon_counting_divisions',
                           set_cmd=partial(self.atmcd64d.set_photon_counting_divisions,
                                           no_of_divisions),
                           vals=validators.Sequence(validators.Ints(1, 65535),
                                                    length=no_of_divisions + 1,
                                                    require_sorted=True),
                           label='Photon counting divisions',
                           docstring=dedent(self.atmcd64d.set_photon_counting_divisions.__doc__))

        self.add_parameter('photon_counting_threshold',
                           set_cmd=self.atmcd64d.set_photon_counting_threshold,
                           vals=validators.Sequence(validators.Ints(1, 65535), length=2,
                                                    require_sorted=True),
                           label='Photon counting threshold',
                           docstring=dedent(self.atmcd64d.set_photon_counting_threshold.__doc__))

        self.add_parameter('post_processing_function',
                           label='Post processing function',
                           parameter_class=ManualParameter,
                           initial_value=post_processing.Identity(),
                           vals=_PostProcessingCallable(),
                           set_parser=self._parse_post_processing_function,
                           docstring="A callable with signature f(data) -> processed_data that is "
                                     "used as the ccd_data parameter get_parser.")

        gains = [round(self.atmcd64d.get_preamp_gain(index), 3)
                 for index in range(self.atmcd64d.get_number_preamp_gains())]
        self.add_parameter('preamp_gain',
                           label='Pre-Amplifier gain',
                           set_cmd=self.atmcd64d.set_preamp_gain,
                           val_mapping={gain: index
                                        for index, gain in enumerate(gains)} | {'Unset': -1},
                           initial_cache_value='Unset',
                           docstring=dedent(self.atmcd64d.set_preamp_gain.__doc__))

        self.add_parameter('random_track_settings',
                           parameter_class=RandomTrackSettings,
                           names=('number_tracks', 'areas'),
                           shapes=((), ()),
                           units=('', 'px'),
                           vals=_HeterogeneousSequence([validators.Ints(1),
                                                        validators.Sequence(validators.Ints(1))]),
                           docstring=dedent(self.atmcd64d.set_random_tracks.__doc__),
                           snapshot_value=True)

        self.add_parameter('readout_time',
                           get_cmd=self.atmcd64d.get_readout_time,
                           label='Readout time',
                           docstring=dedent(self.atmcd64d.get_readout_time.__doc__))

        temperature_range = self.atmcd64d.get_temperature_range()
        self.add_parameter('set_temperature',
                           set_cmd=self.atmcd64d.set_temperature,
                           vals=validators.Ints(min_value=min_temperature or temperature_range[0],
                                                max_value=temperature_range[1]),
                           unit=u"\u00b0" + 'C',
                           label='set temperature',
                           docstring=dedent(self.atmcd64d.set_temperature.__doc__))

        self.add_parameter('shutter_mode',
                           set_cmd=self._set_shutter_mode,
                           val_mapping={'fully auto': 0,
                                        'permanently open': 1,
                                        'permanently closed': 2},
                           label='shutter mode',
                           initial_value='fully auto',
                           docstring=dedent(self.atmcd64d.set_shutter.__doc__))

        self.add_parameter('single_track_settings',
                           parameter_class=SingleTrackSettings,
                           names=('centre', 'height'),
                           shapes=((), ()),
                           units=('px', 'px'),
                           vals=validators.Sequence(validators.Ints(1), length=2),
                           docstring=dedent(self.atmcd64d.set_single_track.__doc__),
                           snapshot_value=True)

        # Real-time spurious noise filter
        self.add_parameter('spurious_noise_filter_mode',
                           get_cmd=self.atmcd64d.filter_get_mode,
                           set_cmd=self.atmcd64d.filter_set_mode,
                           val_mapping={'No Filter': 0,
                                        'Median Filter': 1,
                                        'Level Above Filter': 2,
                                        'Interquartile Range Filter': 3,
                                        'Noise Threshold Filter': 4},
                           label='Spurious noise filter mode',
                           docstring=dedent(self.atmcd64d.filter_set_mode.__doc__))

        self.add_parameter('spurious_noise_filter_threshold',
                           get_cmd=self.atmcd64d.filter_get_threshold,
                           set_cmd=self.atmcd64d.filter_set_threshold,
                           vals=validators.Ints(0, 65535),
                           label='Spurious noise threshold',
                           docstring=dedent(self.atmcd64d.filter_set_threshold.__doc__))

        self.add_parameter('status',
                           label='Camera Status',
                           get_cmd=self.atmcd64d.get_status,
                           get_parser=self._parse_status,
                           docstring=dedent(self.atmcd64d.get_status.__doc__))

        self.add_parameter('temperature',
                           get_cmd=self.atmcd64d.get_temperature,
                           unit=u"\u00b0" + 'C',
                           label='temperature',
                           docstring=dedent(self.atmcd64d.get_temperature.__doc__))

        self.add_parameter('trigger_mode',
                           set_cmd=self.atmcd64d.set_trigger_mode,
                           val_mapping={'internal': 0,
                                        'external': 1,
                                        'external start': 6,
                                        'external exposure': 7,
                                        'software trigger': 10},
                           initial_value='internal',
                           docstring=dedent(self.atmcd64d.set_trigger_mode.__doc__))

        speeds = [self.atmcd64d.get_vs_speed(index)
                  for index in range(self.atmcd64d.get_number_vs_speeds())]
        self.add_parameter('vertical_shift_speed',
                           label='Vertical shift speed',
                           set_cmd=self.atmcd64d.set_vs_speed,
                           val_mapping={speed: index
                                        for index, speed in enumerate(speeds)} | {'Unset': -1},
                           initial_cache_value='Unset',
                           unit='μs/px',
                           docstring=dedent(self.atmcd64d.set_vs_speed.__doc__))

        # Parameters that depend on other parameters and therefore cannot be sorted alphabetically
        self.add_parameter('image_settings',
                           parameter_class=ImageSettings,
                           names=('hbin', 'vbin', 'hstart', 'hend', 'vstart', 'vend'),
                           shapes=((), (), (), (), (), ()),
                           units=('px', 'px', 'px', 'px', 'px', 'px'),
                           vals=_HeterogeneousSequence([
                               validators.Ints(1, self.detector_pixels.get_latest()[0]),
                               validators.Ints(1, self.detector_pixels.get_latest()[1]),
                               validators.Ints(1, self.detector_pixels.get_latest()[0] - 1),
                               validators.Ints(2, self.detector_pixels.get_latest()[0]),
                               validators.Ints(1, self.detector_pixels.get_latest()[1] - 1),
                               validators.Ints(2, self.detector_pixels.get_latest()[1])
                           ]),
                           docstring=dedent(self.atmcd64d.set_image.__doc__),
                           snapshot_value=True)

        self.add_parameter('acquired_accumulations',
                           get_cmd=self._get_acquired_accumulations,
                           # Always infer from acquisition mode, never use cache
                           max_val_age=0,
                           docstring='Number of accumulations per frame.')

        self.add_parameter('acquired_frames',
                           get_cmd=self._get_acquired_frames,
                           # Always infer from acquisition mode, never use cache
                           max_val_age=0,
                           docstring='Number of frames that will be acquired.')

        self.add_parameter('acquired_pixels',
                           parameter_class=AcquiredPixels,
                           names=('horizontal', 'vertical'),
                           shapes=((), ()),
                           units=('px', 'px'),
                           docstring=AcquiredPixels.__doc__,
                           snapshot_value=True)

        self.add_parameter('time_axis',
                           parameter_class=TimeAxis,
                           vals=validators.Arrays(shape=(self.acquired_frames.get_latest,)),
                           unit='s',
                           label='Time axis (frames)',
                           docstring=TimeAxis.__doc__)

        self.add_parameter('horizontal_axis',
                           parameter_class=PixelAxis,
                           dimension=0,
                           vals=validators.Arrays(shape=(self._acquired_horizontal_pixels,)),
                           unit='px',
                           label='Horizontal axis',
                           docstring=PixelAxis.__doc__)

        self.add_parameter('vertical_axis',
                           parameter_class=PixelAxis,
                           dimension=1,
                           vals=validators.Arrays(shape=(self._acquired_vertical_pixels,)),
                           unit='px',
                           label='Vertical axis',
                           docstring=PixelAxis.__doc__)

        self.add_parameter('ccd_data',
                           setpoints=(self.time_axis, self.vertical_axis, self.horizontal_axis,),
                           parameter_class=CCDData,
                           get_parser=self._parse_ccd_data,
                           vals=validators.Arrays(shape=(
                               self.acquired_frames.get_latest,
                               self._acquired_vertical_pixels,
                               self._acquired_horizontal_pixels
                           )),
                           unit='cts',
                           label='CCD Data',
                           docstring=CCDData.__doc__)

        self.add_parameter('ccd_data_bg_corrected',
                           parameter_class=CCDDataDelegateParameter,
                           source=self.ccd_data,
                           get_parser=self._subtract_background,
                           label='CCD Data (bg corrected)',
                           unit='cts',
                           docstring="CCD data with a background image previously taken "
                                     "subtracted.")

        self.add_parameter('ccd_data_per_second',
                           parameter_class=CCDDataDelegateParameter,
                           source=self.ccd_data,
                           get_parser=lambda val: val / self.exposure_time.get_latest(),
                           label='CCD Data per second',
                           unit='cps',
                           docstring="CCD data (counts) divided by the exposure time.")

        self.add_parameter('ccd_data_bg_corrected_per_second',
                           parameter_class=CCDDataDelegateParameter,
                           source=self.ccd_data_bg_corrected,
                           get_parser=lambda val: val / self.exposure_time.get_latest(),
                           label='CCD Data (bg corrected) per second',
                           unit='cps',
                           docstring="CCD data with a background image previously taken "
                                     "subtracted and divided by the exposure time.")

        self.add_parameter('background',
                           parameter_class=PersistentDelegateParameter,
                           source=self.ccd_data,
                           get_parser=self._parse_background,
                           docstring=dedent("""
                           Takes a background image for the current acquisition settings.

                           Note that data conversions set in post_processing_function are
                           still run.
                           """))

        self.add_parameter('acquisition_mode',
                           parameter_class=ParameterWithSetSideEffect,
                           set_cmd=self.atmcd64d.set_acquisition_mode,
                           set_side_effect=self._process_acquisition_mode,
                           val_mapping={'single scan': 1,
                                        'accumulate': 2,
                                        'kinetics': 3,
                                        'fast kinetics': 4,
                                        'run till abort': 5},
                           initial_value='single scan',
                           label='acquisition mode',
                           docstring=dedent(self.atmcd64d.set_acquisition_mode.__doc__))

        self.add_parameter('read_mode',
                           parameter_class=ParameterWithSetSideEffect,
                           set_cmd=self.atmcd64d.set_read_mode,
                           set_side_effect=self._process_read_mode,
                           val_mapping={'full vertical binning': 0,
                                        'multi track': 1,
                                        'random track': 2,
                                        'single track': 3,
                                        'image': 4},
                           initial_value='full vertical binning',
                           label='read mode',
                           docstring=dedent(self.atmcd64d.set_read_mode.__doc__))

        self.connect_message()

    # get methods
    def _get_acquired_accumulations(self) -> int:
        # Fast kinetics does not seem to support accumulations
        if self.acquisition_mode.get_latest() in {'single scan', 'fast kinetics'}:
            return 1
        return self.number_accumulations.get_latest()

    def _get_acquired_frames(self) -> int:
        if 'kinetics' in self.acquisition_mode.get_latest():
            return self.number_kinetics.get_latest()
        return 1

    def get_idn(self) -> Dict[str, Optional[str]]:
        return {'vendor': 'Andor', 'model': self.head_model,
                'serial': str(self.serial_number),
                'firmware': f'{self.firmware_version}.{self.firmware_build}'}

    # set methods
    def _set_cooler(self, cooler_on: int) -> None:
        if cooler_on == 1:
            self.atmcd64d.cooler_on()
        elif cooler_on == 0:
            self.atmcd64d.cooler_off()

    def _set_shutter_mode(self, shutter_mode: int) -> None:
        self.atmcd64d.set_shutter(1, shutter_mode, 30, 30)

    # further methods
    def _acquired_horizontal_pixels(self) -> int:
        return self.acquired_pixels.get_latest()[0]

    def _acquired_vertical_pixels(self) -> int:
        return self.acquired_pixels.get_latest()[1]

    def _freeze_acquisition_settings(self) -> dict[str, Any]:
        acquisition_settings = {'acquisition_mode': self.acquisition_mode.get_latest(),
                                'acquisition_timings': self.atmcd64d.get_acquisition_timings(),
                                'read_mode': self.read_mode.get_latest()}

        settings = getattr(self, self.read_mode.get_latest().replace(' ', '_') + '_settings', None)
        if settings is not None:
            acquisition_settings['read_mode_settings'] = settings.get_latest()
        return acquisition_settings

    def _process_acquisition_mode(self, param: Parameter, param_val: str):
        # Invalidate relevant caches
        self.acquired_frames.cache.invalidate()
        self.acquired_accumulations.cache.invalidate()

        # Update self.ccd_data with correct dimensions
        setpoints: tuple[PixelAxis] | tuple[PixelAxis, PixelAxis]
        shape: tuple[Callable[[], int]] | tuple[Callable[[], int], Callable[[], int]]
        if self.vertical_axis in self.ccd_data.setpoints:
            setpoints = (self.vertical_axis, self.horizontal_axis)
            shape = (self._acquired_vertical_pixels, self._acquired_horizontal_pixels)
        else:
            setpoints = (self.horizontal_axis,)
            shape = (self._acquired_horizontal_pixels,)

        if self._has_time_dimension(param_val):
            self.ccd_data.setpoints = (self.time_axis,) + setpoints
            self.ccd_data.vals = validators.Arrays(
                shape=(self.acquired_frames.get_latest,) + shape
            )
        else:
            self.ccd_data.setpoints = setpoints
            self.ccd_data.vals = validators.Arrays(shape=shape)

    def _process_read_mode(self, param: Parameter, param_val: str):
        # Invalidate relevant caches
        self.acquired_pixels.cache.invalidate()

        # Update self.ccd_data with correct dimensions
        setpoints: tuple[TimeAxis] | tuple[()]
        shape: tuple[Callable[[], int]] | tuple[()]
        if self.time_axis in self.ccd_data.setpoints:
            setpoints = (self.time_axis,)
            shape = (self.acquired_frames.get_latest,)
        else:
            setpoints = ()
            shape = ()

        if self._has_vertical_dimension(param_val):
            self.ccd_data.setpoints = setpoints + (self.vertical_axis, self.horizontal_axis)
            self.ccd_data.vals = validators.Arrays(
                shape=shape + (self._acquired_vertical_pixels, self._acquired_horizontal_pixels)
            )
        else:
            self.ccd_data.setpoints = setpoints + (self.horizontal_axis,)
            self.ccd_data.vals = validators.Arrays(
                shape=shape + (self._acquired_horizontal_pixels,)
            )

    @staticmethod
    def _has_vertical_dimension(read_mode) -> bool:
        return read_mode in (1, 2, 4)

    @staticmethod
    def _has_time_dimension(acquisition_mode) -> bool:
        return acquisition_mode not in (1, 2)

    def _parse_background(self, data: npt.NDArray) -> npt.NDArray:
        """Stores current acquisition settings as parameter metadata."""
        self.background.load_metadata(self._freeze_acquisition_settings())
        return data

    def _parse_ccd_data(self, val: npt.NDArray) -> npt.NDArray:
        # Make sure post_processing_function always gets a 3d array but return
        # the shape that CCDData returns.
        shp = list(val.shape)
        if not self._has_time_dimension(self.acquisition_mode.get_latest()):
            shp.insert(0, 1)
        if not self._has_vertical_dimension(self.read_mode.get_latest()):
            shp.insert(1, 1)
        return self.post_processing_function()(val.reshape(shp)).reshape(val.shape)

    def _parse_post_processing_function(self, val: _T) -> _T:
        # Make sure the post-processing function knows the dll
        if not hasattr(val, 'atmcd64d') or val.atmcd64d is None:
            setattr(val, 'atmcd64d', self.atmcd64d)
        return val

    def _parse_status(self, code: int) -> str:
        status = {
            'DRV_IDLE': 'IDLE waiting on instructions.',
            'DRV_TEMPCYCLE': 'Executing temperature cycle.',
            'DRV_ACQUIRING': 'Acquisition in progress.',
            'DRV_ACCUM_TIME_NOT_MET': 'Unable to meet Accumulate cycle time.',
            'DRV_KINETIC_TIME_NOT_MET': 'Unable to meet Kinetic cycle time.',
            'DRV_ERROR_ACK': 'Unable to communicate with card.',
            'DRV_ACQ_BUFFER': 'Computer unable to read the data via the ISA '
                              'slot at the required rate.',
            'DRV_ACQ_DOWNFIFO_FULL': 'Computer unable to read data fast '
                                     'enough to stop camera memory going full.',
            'DRV_SPOOLERROR': 'Overflow of the spool buffer.'
        }
        status_code = self.atmcd64d.error_codes[code]
        return f'{status_code}: {status[status_code]}'

    def _subtract_background(self, data: npt.NDArray) -> npt.NDArray:
        if (background := self.background.cache.get(False)) is None:
            raise RuntimeError("No background acquired. Perform a get on the 'background' "
                               "parameter")

        current_settings = self._freeze_acquisition_settings()
        background_settings = {key: self.background.metadata.get(key, None)
                               for key in current_settings}
        if not self.background_is_valid:
            raise RuntimeError('Background was acquired for different settings; cannot subtract '
                               'it. Consider taking a new background or changing the settings. '
                               f'Previous settings were: {background_settings}')
        return data - background

    @property
    def background_is_valid(self) -> bool:
        current_settings = self._freeze_acquisition_settings()
        background_settings = {key: self.background.metadata.get(key, None)
                               for key in current_settings}
        return background_settings == current_settings

    def close(self) -> None:
        self.atmcd64d.shut_down()
        super().close()

    def abort_acquisition(self) -> None:
        self.atmcd64d.abort_acquisition()

    def prepare_acquisition(self) -> None:
        self.atmcd64d.prepare_acquisition()

    def start_acquisition(self) -> None:
        """Start the acquisition. Exposed for 'run till abort'
        acquisition mode and external triggering."""
        self.atmcd64d.start_acquisition()

    def arm(self) -> None:
        """TODO: Placeholder."""
        self.log.debug('Arming: clear buffer, prepare and starting acquisition.')
        self.clear_circular_buffer()
        self.prepare_acquisition()
        self.start_acquisition()

    def clear_circular_buffer(self) -> None:
        self.atmcd64d.free_internal_memory()

    def cool_down(self, setpoint: int | None = None,
                  target: Literal['stabilized', 'reached'] = 'reached',
                  show_progress: bool = True) -> None:
        """Turn the cooler on and wait for the temperature to stabilize.

        Args:
            setpoint: The target temperature. Required if
                *set_temperature* is not initialized.
            target: Finish if temperature is reached or reached and stabilized.
            show_progress: Show a progressbar. The default is True.

        """
        if setpoint is None and (setpoint := self.set_temperature.get()) is None:
            raise ValueError('Please set the set_temperature first or specify setpoint.')

        targets: tuple[str, str] | tuple[str]
        if target.lower() == 'reached':
            targets = ('DRV_TEMP_NOT_STABILIZED', 'DRV_TEMP_STABILIZED')
        elif target.lower() == 'stabilized':
            targets = ('DRV_TEMP_STABILIZED',)
        else:
            raise ValueError('target should be one of reached or stabilized.')

        self.set_temperature(setpoint)
        self.cooler.set('on')

        # bar does not show for negative totals, but ok
        with tqdm(
                initial=(initial := self.temperature.get()),
                total=(setpoint - initial),
                desc=f'{self.name} cooling down from {initial}{self.temperature.unit} '
                     f'to {setpoint}{self.temperature.unit}. Delta',
                unit=self.temperature.unit,
                disable=not show_progress
        ) as pbar:
            while (status := self.atmcd64d.get_cooling_status()[0]) not in targets:
                # For lack of a better method:
                # https://github.com/tqdm/tqdm/issues/1264
                pbar.postfix = f'status={status}'
                pbar.n = self.temperature.get() - initial
                pbar.refresh()
                time.sleep(1)
            pbar.postfix = status
            pbar.n = pbar.total
            pbar.refresh()

    def warm_up(self, target: int = 15, show_progress: bool = True) -> None:
        """Turn the cooler off and wait for the temperature to reach target.

        Parameters
        ----------
        target : int, optional
            The target temperature. Defaults to 15C.
        show_progress : bool, optional
            Show a progressbar. The default is True.

        """
        self.cooler.set('off')

        # bar does not show for negative totals, but ok
        with tqdm(
                initial=(initial := self.temperature.get()),
                total=target - initial,
                desc=f'{self.name} warming up from {initial}{self.temperature.unit} '
                     f'to {target}{self.temperature.unit}. Delta',
                unit=self.temperature.unit,
                disable=not show_progress
        ) as pbar:
            while (temp := self.temperature.get()) != target:
                # For lack of a better method:
                # https://github.com/tqdm/tqdm/issues/1264
                pbar.n = temp - target
                pbar.refresh()
                time.sleep(1)
            pbar.n = pbar.total
            pbar.refresh()
