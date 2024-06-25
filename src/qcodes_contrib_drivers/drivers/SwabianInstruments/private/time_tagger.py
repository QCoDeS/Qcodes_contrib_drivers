from __future__ import annotations

import abc
import inspect
import os
import sys
import textwrap
import warnings
from collections.abc import Callable, Sequence, Collection
from pathlib import Path
from typing import Any, TypeVar

import numpy as np
import numpy.typing as npt
from qcodes.instrument import InstrumentBase, InstrumentChannel, InstrumentModule
from qcodes.parameters import ParamRawDataType, Parameter, ParameterBase
from qcodes.validators import validators as vals

try:
    sys.path.append(str(Path(os.environ['TIMETAGGER_INSTALL_PATH'], 'driver', 'python')))
    import TimeTagger as tt
except (KeyError, ImportError):
    tt = None

_F = TypeVar('_F', bound=Callable[..., Any])


def _snake_to_camel(name: str) -> str:
    humps = name.split('_')
    return humps[0] + ''.join(hump.title() for hump in humps[1:])


def refer_to_api_doc(api_obj: str) -> Callable[[_F], _F]:
    """Decorator factory to link a method to its TT API documentation."""

    def decorator(func: _F) -> _F:
        api_name = '.'.join([api_obj, _snake_to_camel(func.__name__)])
        func.__doc__ = textwrap.dedent(
            f"""Forwards API method :meth:`TimeTagger:{api_name}`. See
            documentation there."""
        )
        return func

    return decorator


def cached_api_object(__func: Callable[..., Any] | None = None,
                      *, required_parameters: Collection[str] | None = None):
    """A custom descriptor for a cached API object with exception
    handling, invalidation capability, and initialization checks."""

    class CachedProperty:

        def __init__(self, func: Callable[..., Any]):
            self.func = func
            self.required_parameters = [] if required_parameters is None else required_parameters
            self.cache_name = f"__{func.__qualname__}_cached"

        def __get__(self, instance, owner=None):
            if instance is None:
                return self

            # Assert the required parameters have been initialized by checking
            # that they pass the validator
            not_initialized = set()
            for param_name in self.required_parameters:
                param: ParameterBase = getattr(instance, param_name)
                try:
                    param.vals.validate(param.cache.get())
                except AttributeError:
                    # No validator, cannot do anything
                    warnings.warn("All required parameters should have a validator.",
                                  RuntimeWarning, stacklevel=2)
                except Exception:
                    not_initialized.add(param_name)
            if any(not_initialized):
                raise RuntimeError('The following parameters need to be initialized first: '
                                   + ', '.join(not_initialized))

            if hasattr(instance, self.cache_name):
                value = getattr(instance, self.cache_name)
            else:
                value = self.func(instance)
                setattr(instance, self.cache_name, value)
            return value

        def __set__(self, instance, value):
            raise AttributeError('api property cannot be set directly.')

        def __delete__(self, instance):
            if hasattr(instance, self.cache_name):
                delattr(instance, self.cache_name)

    if __func is not None:
        cached_property = CachedProperty(__func)
        cached_property.__doc__ = __func.__doc__
        return cached_property
    else:
        return CachedProperty


class TypeValidator(vals.Validator[type]):
    """A validator for specific types."""

    def __init__(self, cls: type):
        self._valid_values = (cls,)
        self.is_numeric = False

    def validate(self, value: type, context: str = "") -> None:
        if not isinstance(value, self.valid_values):
            raise TypeError(f'{value!r} is not of type {self.valid_values[0]}; {context}')


class ArrayLikeValidator(vals.Arrays):
    """A validator for array_like objects.

    Note that validation might be expensive since conversion to ndarray
    takes place each time.
    """

    def __repr__(self) -> str:
        return super().__repr__().replace('Arrays', 'ArrayLike')

    def validate(self, value: npt.ArrayLike, context: str = "") -> None:
        try:
            array = np.array(value)
        except ValueError as err:
            raise ValueError(f'{value!r} is invalid: cannot convert to array; {context}') from err
        super().validate(array, context)


class ParameterWithSetSideEffect(Parameter):
    """A :class:`Parameter` allowing for side effects on set events.

    Parameters
    ----------
    set_side_effect :
        A callable that is run on every set event. Receives the set
        value as sole argument.
    execute_before :
        Run the side effect before or after setting the parameter.
    """

    def __init__(self, name: str, set_side_effect: Callable[[Any], None],
                 set_cmd: Callable[[ParamRawDataType], Any] | None = None,
                 execute_before: bool = False, **kwargs: Any) -> None:
        if set_cmd is False:
            raise ValueError('ParameterWithSetSideEffect needs to be settable')

        # Parameter does not allow overriding set_raw method
        def set_raw(value: ParamRawDataType) -> ParamRawDataType:
            if execute_before:
                set_side_effect(value)
            if set_cmd is not None:
                set_cmd(value)
            if not execute_before:
                set_side_effect(value)
            return value

        super().__init__(name, set_cmd=set_raw, **kwargs)


class MeasurementControlMixin(metaclass=abc.ABCMeta):
    """Mixin class forwarding common methods from the TimeTagger API."""

    @property
    @abc.abstractmethod
    def api(self):
        pass

    @refer_to_api_doc('IteratorBase')
    def clear(self):
        return self.api.clear()

    @refer_to_api_doc('IteratorBase')
    def start(self):
        return self.api.start()

    @refer_to_api_doc('IteratorBase')
    def start_for(self, duration: int, clear: bool = True):
        return self.api.startFor(duration, clear)

    @refer_to_api_doc('IteratorBase')
    def stop(self):
        return self.api.stop()

    @refer_to_api_doc('IteratorBase')
    def is_running(self) -> bool:
        return self.api.isRunning()

    @refer_to_api_doc('IteratorBase')
    def wait_until_finished(self, timeout: int = -1):
        return self.api.waitUntilFinished(timeout)


class TimeTaggerInstrumentBase(InstrumentBase, metaclass=abc.ABCMeta):
    """Base class for TimeTagger instruments and channels.

    Overrides :meth:`snapshot_base` to add the API configuration.
    """

    @property
    @abc.abstractmethod
    def api(self):
        pass

    def snapshot_base(self, update: bool | None = False,
                      params_to_skip_update: Sequence[str] | None = None) -> dict[Any, Any]:
        key = f'{self.__class__.__qualname__} API configuration'
        try:
            config = {key: self.get_configuration()}
        except RuntimeError:
            # API not initialized
            config = {}
        except Exception as err:
            self.log.error(f'Could not load {key}', exc_info=err)
            config = {}
        return config | super().snapshot_base(update, params_to_skip_update)

    @refer_to_api_doc('TimeTaggerBase')
    def get_configuration(self) -> dict[str, Any]:
        # TODO: The TimeTaggerBase call includes descriptions of measurements associated with it,
        #  so recursing into its submodules (measurements) will duplicate information. Include?
        return self.api.getConfiguration()


class TimeTaggerModule(InstrumentChannel, metaclass=abc.ABCMeta):
    """An InstrumentChannel implementing TimeTagger Measurements and
    Virtual Channels."""
    __implementations: set[type[TimeTaggerModule]] = set()

    def __init__(self, parent: InstrumentBase, name: str,
                 api_tagger: tt.TimeTaggerBase | None = None, **kwargs: Any):
        """Initialize a TimeTaggerModule.

        Parameters
        ----------
        parent :
            The parent instrument.
        name :
            The channel name.
        api_tagger :
            The TimeTagger API object of the device to use. Can be a
            virtual time tagger gotten from
            :meth:`TimeTaggerSynchronizedMeasurements.get_tagger`.
        """

        super().__init__(parent, name, **kwargs)
        self._api_tagger = self.parent.api if api_tagger is None else api_tagger

    def __init_subclass__(cls):
        if not (
                cls.__qualname__.endswith('Measurement')
                or cls.__qualname__.endswith('VirtualChannel')
        ):
            raise RuntimeError('TimeTaggerModule should only be used as base class for '
                               '*Measurement or *VirtualChannel subclasses.')
        if not inspect.isabstract(cls):
            for impl in filter(lambda impl: impl.__qualname__ == cls.__qualname__,
                               list(TimeTaggerModule.__implementations)):
                # Handle %autoreload (reloaded class will not have the same hash and hence
                # lead to a duplicate entry)
                TimeTaggerModule.__implementations.remove(impl)
            TimeTaggerModule.__implementations.add(cls)

    @property
    @abc.abstractmethod
    def api(self):
        """The :class:`TimeTagger:TimeTagger.Measurement` API object
        underlying this module."""
        pass

    @property
    def api_tagger(self) -> tt.TimeTaggerBase:
        """The :class:`TimeTagger:TimeTagger.TimeTaggerBase` API object
        underlying this module."""
        return self._api_tagger

    @classmethod
    def implementations(cls: type[TimeTaggerModule]) -> frozenset[type[TimeTaggerModule]]:
        """All registered implementations of this class."""
        return frozenset(cls.__implementations)

    def _invalidate_api(self, *_):
        try:
            del self.api
        except AttributeError:
            # API not initialized or not cached_property
            pass


class TimeTaggerMeasurement(MeasurementControlMixin, TimeTaggerInstrumentBase, TimeTaggerModule,
                            metaclass=abc.ABCMeta):
    """Instrument channel representing a TimeTagger API Measurement."""

    def __init__(self, parent: InstrumentBase, name: str,
                 api_tagger: tt.TimeTaggerBase | None = None, **kwargs: Any):
        super().__init__(parent, name, api_tagger, **kwargs)

        self.capture_duration = Parameter(
            'capture_duration',
            instrument=self,
            label='Capture duration',
            unit='ps',
            get_cmd=lambda: self.api.getCaptureDuration(),
            set_cmd=False,
            max_val_age=0.0
        )

    @refer_to_api_doc('IteratorBase')
    def get_capture_duration(self) -> int:
        return self.api.getCaptureDuration()


class TimeTaggerVirtualChannel(TimeTaggerInstrumentBase, TimeTaggerModule, metaclass=abc.ABCMeta):
    """Instrument channel representing a TimeTagger API Virtual Channel."""

    # The API docs aren't clear on which VirtualChannel classes provide which getChannel(s) method
    @refer_to_api_doc('VirtualChannel')
    def get_channel(self) -> int:
        try:
            return self.api.getChannel()
        except AttributeError as err:
            raise AttributeError(f"The {self.__class__.__qualname__} API doesn't provide a "
                                 f"getChannel() method. Try {self.__class__.__qualname__}."
                                 "get_channels().") from err

    @refer_to_api_doc('VirtualChannel')
    def get_channels(self) -> list[int]:
        try:
            return self.api.getChannels()
        except AttributeError as err:
            raise AttributeError(f"The {self.__class__.__qualname__} API doesn't provide a "
                                 f"getChannels() method. Try {self.__class__.__qualname__}."
                                 "get_channel().") from err


class TimeTaggerSynchronizedMeasurements(MeasurementControlMixin, InstrumentModule):
    """Instrument module representing a TimeTagger API
    :class:`TimeTagger:SynchronizedMeasurements` object."""

    def __init__(self, parent: InstrumentBase, name: str, **kwargs: Any) -> None:
        super().__init__(parent, name, **kwargs)
        self._api = tt.SynchronizedMeasurements(parent.api)
        self._api_tagger = self.api.getTagger()

    @property
    def api(self) -> tt.SynchronizedMeasurements:
        return self._api

    @property
    def api_tagger(self) -> tt.TimeTaggerBase:
        """A proxy TimeTagger API object for synchronized measurements."""
        return self._api_tagger

    @refer_to_api_doc('SynchronizedMeasurements')
    def register_measurement(self, measurement: TimeTaggerMeasurement):
        return self.api.registerMeasurement(measurement.api)

    @refer_to_api_doc('SynchronizedMeasurements')
    def unregister_measurement(self, measurement: TimeTaggerMeasurement):
        return self.api.unregisterMeasurement(measurement.api)
