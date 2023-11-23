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
    # shortest possible acquisition time.
    ccd.exposure_time(0)
    ccd.accumulation_cycle_time(0)
    ccd.kinetic_cycle_time(0)
    # Acquire data
    data = ccd.ccd_data()
    data.shape  # (10, 2, 2000)

Note:
    :meth:`atmcd64d.GetImages` and related are still untested.

"""
import itertools
import operator
import textwrap
from collections import abc
from functools import partial
from typing import Any, Callable, Dict, Literal, Optional, Sequence, Set, Tuple, Union

import numpy as np
import numpy.typing as npt
from qcodes import Instrument, MultiParameter, Parameter, ParameterWithSetpoints
from qcodes import validators as vals
from qcodes.utils.helpers import create_on_off_val_mapping

from . import post_processing
from .private.andor_sdk import SDKError, atmcd64d


class _HeterogeneousSequence(vals.Validator[Sequence[Any]]):
    """A validator for heterogeneous sequences."""

    def __init__(self, elt_validators: Sequence[vals.Validator[Any]] = (vals.Anything(),)) -> None:
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
            if not isinstance(validator, vals.Anything):
                validator.validate(elt)

    @property
    def elt_validators(self) -> Sequence[vals.Validator[Any]]:
        return self._elt_validators

    @property
    def length(self) -> int:
        return len(self.elt_validators)


class _PostProcessingCallable(vals.Validator[Callable[[npt.NDArray[np.int32]], npt.NDArray[np.int32]]]):
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
    """Represents the settings for multi-track acquisition."""
    _bottom: Optional[int] = None
    _gap: Optional[int] = None

    def get_raw(self) -> Optional[Tuple[int, int, int, int, int]]:
        if self.instrument is None:
            raise RuntimeError("No instrument attached to Parameter.")

        val = self.cache.get(False)
        return tuple(val) + (self._bottom, self._gap) if val is not None else None  # type: ignore[return-value]

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


class PixelAxis(Parameter):
    """A parameter that enumerates the pixels along an axis.

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
    """A parameter that holds the start of each exposure window.

    If the acquisition mode is a kinetic series, the size corresponds
    to number_kinetics(), otherwise it's always 1.
    """

    def get_raw(self) -> npt.NDArray[np.float64]:
        if self.instrument is None:
            raise RuntimeError("No instrument attached to Parameter.")

        n_pts = self.instrument.acquired_frames.get()
        dt = self.instrument.kinetic_cycle_time.get()
        return np.arange(0, dt * n_pts, dt)


class CCDData(ParameterWithSetpoints):
    """Parameter class for data taken with an Andor CCD.

    The data is saved in an integer array with shape (number of frames,
    number of y pixels, number of x pixels). Depending on the read mode,
    the first two dimensions may be singletons.

    Note:
        The last two axes are switched around compared to the rest of
        this driver.

    """

    def get_raw(self) -> npt.NDArray[np.int32]:
        if self.instrument is None:
            raise RuntimeError("No instrument attached to Parameter.")

        shape = tuple(setpoints.get().size for setpoints in self.setpoints)
        # Can use get_latest here since acquisition_mode and read_mode set parsres
        # already take care of invalidating caches if things changed.
        number_frames = self.instrument.acquired_frames.get_latest()
        number_accumulations = self.instrument.acquired_accumulations.get_latest()
        number_pixels = np.prod(self.instrument.acquired_pixels.get_latest())

        # We decide here which method we use to fetch data from the SDK. The CCD
        # has a circular buffer, so we should fetch data during acquisition if
        # the desired result is larger.
        fetch_lazy = self.instrument.atmcd64d.get_size_of_circular_buffer() < number_frames

        # TODO (thangleiter): for fast kinetics, one might want to fetch a number of images
        #                     every few acquisitions.
        if fetch_lazy:
            data_buffer = np.empty(number_frames * number_pixels, dtype=np.int32)
        else:
            data_buffer = np.empty((number_frames, number_pixels), dtype=np.int32)

        self.instrument.log.debug('Starting acquisition.')
        self.instrument.atmcd64d.start_acquisition()

        try:
            for frame in range(number_frames):
                self.instrument.log.debug(f'Acquiring frame {frame}/{number_frames}.')

                for accumulation in range(number_accumulations):
                    self.instrument.log.debug('Acquiring accumulation '
                                              f'{accumulation}/{number_accumulations}.')
                    self.instrument.atmcd64d.wait_for_acquisition()

                if not fetch_lazy:
                    # TODO (thangleiter): For unforeseen reasons, this might fetch old data. Better
                    #                     to clear internal buffer before acquisitoin start?
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

        # add the instrument parameters
        self.add_parameter('accumulation_cycle_time',
                           get_cmd=self.atmcd64d.get_acquisition_timings,
                           set_cmd=self.atmcd64d.set_accumulation_cycle_time,
                           get_parser=lambda ans: float(ans[1]),
                           max_val_age=0,
                           unit='s',
                           label='accumulation cycle time')

        self.add_parameter('detector_size',
                           parameter_class=DetectorPixels,
                           names=('horizontal', 'vertical'),
                           shapes=((), ()),
                           units=('μm', 'μm'),
                           labels=('Horizontal chip size', 'Vertical chip size'),
                           snapshot_value=True)

        self.add_parameter('cooler',
                           get_cmd=self.atmcd64d.is_cooler_on,
                           set_cmd=self._set_cooler,
                           val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
                           label='cooler')

        self.add_parameter('cooler_mode',
                           set_cmd=self.atmcd64d.set_cooler_mode,
                           val_mapping={'maintain': 1, 'return': 0},
                           label='Cooler mode',
                           initial_value='return',
                           docstring=textwrap.dedent(
                               """Determines whether the cooler is switched off when the camera is
                               shut down.

                               'maintain' means it is maintained on shutdown, 'return' means the
                               camera returns to ambient temperature. Defaults to 'return'.
                               """
                           ))

        self.add_parameter('exposure_time',
                           get_cmd=self.atmcd64d.get_acquisition_timings,
                           set_cmd=self.atmcd64d.set_exposure_time,
                           get_parser=lambda ans: float(ans[0]),
                           max_val_age=0,
                           unit='s',
                           label='exposure time')

        self.add_parameter('fastest_recommended_vertical_shift_speed',
                           get_cmd=self.atmcd64d.get_fastest_recommended_vertical_shift_speed,
                           get_parser=operator.itemgetter(1),
                           docstring='Fastest recommended vertical shift speed for curent '
                                     'vertical clock voltage',
                           unit='μs/px')

        self.add_parameter('filter_mode',
                           get_cmd=self.atmcd64d.get_filter_mode,
                           set_cmd=self.atmcd64d.set_filter_mode,
                           val_mapping=create_on_off_val_mapping(on_val=2, off_val=0),
                           label='filter mode')

        speeds = [round(self.atmcd64d.get_hs_speed(self._CHANNEL, self._AMPLIFIER, index), 3)
                  for index
                  in range(self.atmcd64d.get_number_hs_speeds(self._CHANNEL, self._AMPLIFIER))]
        self.add_parameter('horizontal_shift_speed',
                           label='Horizontal shift speed',
                           set_cmd=partial(self.atmcd64d.set_hs_speed, self._AMPLIFIER),
                           val_mapping={speed: index
                                        for index, speed in enumerate(speeds)} | {'Unset': -1},
                           initial_cache_value='Unset',
                           unit='MHz')

        self.add_parameter('keep_clean_time',
                           get_cmd=self.atmcd64d.get_keep_clean_time,
                           unit='s',
                           label='Keep clean cycle duration')

        self.add_parameter('kinetic_cycle_time',
                           get_cmd=self.atmcd64d.get_acquisition_timings,
                           set_cmd=self.atmcd64d.set_kinetic_cycle_time,
                           get_parser=lambda ans: float(ans[2]),
                           max_val_age=0,
                           unit='s',
                           label='Kinetic cycle time')

        self.add_parameter('multi_track_settings',
                           parameter_class=MultiTrackSettings,
                           names=('number', 'height', 'offset', 'bottom', 'gap'),
                           shapes=((), (), (), (), ()),
                           units=('px', 'px', 'px', 'px', 'px'),
                           vals=_HeterogeneousSequence([vals.Ints(1), vals.Ints(1), vals.Ints(0)]),
                           docstring=textwrap.dedent(
                               """Multi-track settings.

                               When setting, a sequence of *three* numbers (number, height, and
                               offset); refer to the SDK documentation for explanation.

                               When getting, a tuple of *five* numbers (number, height, offset,
                               bottom, gap) is return. The last two are calculated by the dll
                               function and are thus only available when getting.
                               """
                           ),
                           snapshot_value=True)

        self.add_parameter('number_accumulations',
                           set_cmd=self.atmcd64d.set_number_accumulations,
                           label='number accumulations')

        self.add_parameter('number_kinetics',
                           set_cmd=self.atmcd64d.set_number_kinetics,
                           label='number of scans during a single acquisition sequence')

        self.add_parameter('detector_pixels',
                           parameter_class=DetectorPixels,
                           names=('horizontal', 'vertical'),
                           shapes=((), ()),
                           units=('px', 'px'),
                           labels=('Horizontal number of pixels', 'Vertical number of pixels'),
                           snapshot_value=True)

        self.add_parameter('pixel_size',
                           parameter_class=PixelSize,
                           names=('horizontal', 'vertical'),
                           shapes=((), ()),
                           units=('μm', 'μm'),
                           labels=('Horizontal pixel size', 'Vertical pixel size'),
                           snapshot_value=True)

        self.add_parameter('post_processing_function',
                           label='Post processing function',
                           set_cmd=self._set_post_processing_function,
                           initial_value=None,
                           vals=vals.MultiType(_PostProcessingCallable(), vals.Enum(None)))

        gains = [round(self.atmcd64d.get_preamp_gain(index), 3)
                 for index in range(self.atmcd64d.get_number_preamp_gains())]
        self.add_parameter('preamp_gain',
                           label='Pre-Amplifier gain',
                           set_cmd=self.atmcd64d.set_preamp_gain,
                           val_mapping={gain: index
                                        for index, gain in enumerate(gains)} | {'Unset': -1},
                           initial_cache_value='Unset')

        self.add_parameter('random_track_settings',
                           parameter_class=RandomTrackSettings,
                           names=('number_tracks', 'areas'),
                           shapes=((), ()),
                           units=('', 'px'),
                           vals=_HeterogeneousSequence([
                               vals.Ints(1),
                               vals.Sequence(vals.Ints(1))
                           ]),
                           snapshot_value=True)

        temperature_range = self.atmcd64d.get_temperature_range()
        self.add_parameter('set_temperature',
                           set_cmd=self.atmcd64d.set_temperature,
                           vals=vals.Ints(min_value=min_temperature or temperature_range[0],
                                          max_value=temperature_range[1]),
                           unit=u"\u00b0" + 'C',
                           label='set temperature')

        self.add_parameter('shutter_mode',
                           set_cmd=self._set_shutter_mode,
                           val_mapping={'fully auto': 0,
                                        'permanently open': 1,
                                        'permanently closed': 2},
                           label='shutter mode',
                           initial_value='fully auto')

        self.add_parameter('single_track_settings',
                           parameter_class=SingleTrackSettings,
                           names=('centre', 'height'),
                           shapes=((), ()),
                           units=('px', 'px'),
                           vals=vals.Sequence(vals.Ints(1), length=2),
                           snapshot_value=True)

        self.add_parameter('status',
                           label='Camera Status',
                           get_cmd=self.atmcd64d.get_status,
                           get_parser=self._parse_status)

        self.add_parameter('temperature',
                           get_cmd=self.atmcd64d.get_temperature,
                           unit=u"\u00b0" + 'C',
                           label='temperature')

        self.add_parameter('trigger_mode',
                           set_cmd=self.atmcd64d.set_trigger_mode,
                           val_mapping={'internal': 0},
                           initial_value='internal')

        speeds = [self.atmcd64d.get_vs_speed(index)
                  for index in range(self.atmcd64d.get_number_vs_speeds())]
        self.add_parameter('vertical_shift_speed',
                           label='Vertical shift speed',
                           set_cmd=self.atmcd64d.set_vs_speed,
                           val_mapping={speed: index
                                        for index, speed in enumerate(speeds)} | {'Unset': -1},
                           initial_cache_value='Unset',
                           unit='μs/px')

        # Parameters that depend on other parameters and therefore cannot be sorted alphabetically
        self.add_parameter('image_settings',
                           parameter_class=ImageSettings,
                           names=('hbin', 'vbin', 'hstart', 'hend', 'vstart', 'vend'),
                           shapes=((), (), (), (), (), ()),
                           units=('px', 'px', 'px', 'px', 'px', 'px'),
                           vals=_HeterogeneousSequence([
                               vals.Ints(1, self.detector_pixels.get_latest()[0]),
                               vals.Ints(1, self.detector_pixels.get_latest()[1]),
                               vals.Ints(1, self.detector_pixels.get_latest()[0] - 1),
                               vals.Ints(2, self.detector_pixels.get_latest()[0]),
                               vals.Ints(1, self.detector_pixels.get_latest()[1] - 1),
                               vals.Ints(2, self.detector_pixels.get_latest()[1])
                           ]),
                           docstring="For iDus, it is recommended that you set horizontal binning "
                                     "to 1.",
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
                           snapshot_value=True)

        self.add_parameter('time_axis',
                           parameter_class=TimeAxis,
                           vals=vals.Arrays(shape=(self.acquired_frames.get_latest,)),
                           unit='s',
                           label='Time axis (frames)')

        self.add_parameter('horizontal_axis',
                           parameter_class=PixelAxis,
                           dimension=0,
                           vals=vals.Arrays(shape=(self._acquired_horizontal_pixels,)),
                           unit='px',
                           label='Horizontal axis')

        self.add_parameter('vertical_axis',
                           parameter_class=PixelAxis,
                           dimension=1,
                           vals=vals.Arrays(shape=(self._acquired_vertical_pixels,)),
                           unit='px',
                           label='Vertical axis')

        self.add_parameter('ccd_data',
                           setpoints=(self.time_axis, self.vertical_axis, self.horizontal_axis,),
                           parameter_class=CCDData,
                           vals=vals.Arrays(shape=(
                               self.acquired_frames.get_latest,
                               self._acquired_vertical_pixels,
                               self._acquired_horizontal_pixels
                           )),
                           unit='cts',
                           label='CCD Data')

        self.add_parameter('acquisition_mode',
                           set_cmd=self.atmcd64d.set_acquisition_mode,
                           set_parser=self._parse_acquisition_mode,
                           val_mapping={'single scan': 1,
                                        'accumulate': 2,
                                        'kinetics': 3,
                                        'run till abort': 5},
                           initial_value='single scan',
                           label='acquisition mode')

        self.add_parameter('read_mode',
                           set_cmd=self.atmcd64d.set_read_mode,
                           set_parser=self._parse_read_mode,
                           val_mapping={'full vertical binning': 0,
                                        'multi track': 1,
                                        'random track': 2,
                                        'single track': 3,
                                        'image': 4},
                           initial_value='full vertical binning',
                           label='read mode')

        self.connect_message()

    # get methods
    def _get_acquired_accumulations(self) -> int:
        if self.acquisition_mode.get_latest() == 'single scan':
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

    def _set_post_processing_function(self, val) -> None:
        self.ccd_data.get_parser = val

    def _set_shutter_mode(self, shutter_mode: int) -> None:
        self.atmcd64d.set_shutter(1, shutter_mode, 30, 30)

    # further methods
    def _acquired_horizontal_pixels(self) -> int:
        return self.acquired_pixels.get_latest()[0]

    def _acquired_vertical_pixels(self) -> int:
        return self.acquired_pixels.get_latest()[1]

    def _parse_acquisition_mode(self, val) -> None:
        # Invalidate relevant caches
        self.acquired_frames.cache.invalidate()
        self.acquired_accumulations.cache.invalidate()

        # Update self.ccd_data with correct dimensions
        if self.vertical_axis in self.ccd_data.setpoints:
            setpoints = (self.vertical_axis, self.horizontal_axis)
            shape = (self._acquired_vertical_pixels, self._acquired_horizontal_pixels)
        else:
            setpoints = (self.horizontal_axis,)
            shape = (self._acquired_horizontal_pixels,)

        if self._has_time_dimension(val):
            self.ccd_data.setpoints = (self.time_axis,) + setpoints
            self.ccd_data.vals = vals.Arrays(shape=(self.acquired_frames.get_latest,) + shape)
        else:
            self.ccd_data.setpoints = setpoints
            self.ccd_data.vals = vals.Arrays(shape=shape)

        return val

    def _parse_read_mode(self, val) -> None:
        # Invalidate relevant caches
        self.acquired_pixels.cache.invalidate()

        # Update self.ccd_data with correct dimensions
        if self.time_axis in self.ccd_data.setpoints:
            setpoints = (self.time_axis,)
            shape = (self.acquired_frames.get_latest,)
        else:
            setpoints = tuple()
            shape = tuple()

        if self._has_vertical_dimension(val):
            self.ccd_data.setpoints = setpoints + (self.vertical_axis, self.horizontal_axis)
            self.ccd_data.vals = vals.Arrays(shape=shape + (self._acquired_vertical_pixels,
                                                            self._acquired_horizontal_pixels))
        else:
            self.ccd_data.setpoints = setpoints + (self.horizontal_axis,)
            self.ccd_data.vals = vals.Arrays(shape=shape + (self._acquired_horizontal_pixels,))

        return val

    @staticmethod
    def _has_vertical_dimension(read_mode) -> bool:
        return read_mode in (1, 2, 4)

    @staticmethod
    def _has_time_dimension(acquisition_mode) -> bool:
        return acquisition_mode not in (1, 2)

    def _parse_status(self, code: int) -> str:
        status = {
            'DRV_IDLE': 'IDLE waiting on instructions.',
            'DRV_TEMPCYCLE': 'Executing temperature cycle.',
            'DRV_ACQUIRING': ' Acquisition in progress.',
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

    def close(self) -> None:
        self.atmcd64d.shut_down()
        super().close()

    def abort_acquisition(self) -> None:
        self.atmcd64d.abort_acquisition()

    def prepare_acquisition(self) -> None:
        self.atmcd64d.prepare_acquisition()

    def start_acquisition(self) -> None:
        """Start the acquisition. Exposed to be used with 'run till
        abort' mode."""
        self.atmcd64d.start_acquisition()

    def arm(self) -> None:
        """TODO: Placeholder."""
        self.clear_circular_buffer()
        self.prepare_acquisition()

    def clear_circular_buffer(self) -> None:
        self.atmcd64d.free_internal_memory()
