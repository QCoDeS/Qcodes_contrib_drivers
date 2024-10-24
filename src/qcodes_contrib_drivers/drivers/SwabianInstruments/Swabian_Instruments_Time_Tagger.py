"""QCoDeS driver for the Swabian Instruments Time Tagger series.

Since the `Swabian Instruments Python driver`_ is already excellent,
this driver is mostly concerned with wrapping its object-oriented API
into QCoDeS Instruments and Parameters. It is organized as follows:

 * The actual device driver is :class:`TimeTagger`, which wraps the API
   :class:`TimeTagger:TimeTagger` object.

 * Measurements and Virtual Channels are implemented as
   :class:`~qcodes:qcodes.instrument.channel.InstrumentChannel` s, which
   should dynamically be added and removed from the :class:`TimeTagger`
   instrument's corresponding
   :class:`~qcodes:qcodes.instrument.channel.ChannelList` as needed.
   These channels own
   :class:`~qcodes:qcodes.parameters.parameter.Parameter` s
   which may be required to be initialized to instantiate the API object
   of the TimeTagger library that actually controls the measurement.

 * If properly initialized, each QCoDeS instrument or channel has a
   cached :meth:`api` property that gives access to the TimeTagger API
   object. The cache is automatically invalidated if a Paramaeter is
   changed that was used to instantiate the object (e.g., the binwidth).

 * :class:`~.private.time_tagger.TimeTaggerVirtualChannel` and
   :class:`~.private.time_tagger.TimeTaggerMeasurement` inherit from the
   abstract :class:`~.private.time_tagger.TimeTaggerModule`, and
   subclasses are automatically registered. This is used to generate
   convenience methods in the :class:`TimeTagger` instrument to add a
   new measurement or virtual channel to its corresponding channel list.

 * Measurements inherit common functionality from
   :class:`TimeTagger:IteratorBase` (formatted in snake_case).

 * The :class:`TimeTagger` instrument has a submodule
   :attr:`~TimeTagger.synchronized_measurements` that wraps the API
   :class:`TimeTagger:SynchronizedMeasurements` and allows for syncing
   multiple measurements using the same tagger.

 * Parameters in this driver are named according to their API
   counterparts. See the API documentation for their explanations.

**Implementing new Measurement or VirtualChannel classes**

As corresponding channel lists are automatically added to the main
instrument driver, to implement new measurements or virtual channels
from the TimeTagger API one simply needs to inherit from
:class:`~.private.time_tagger.TimeTaggerMeasurement` or
:class:`~.private.time_tagger.TimeTaggerVirtualChannel`, respectively.
The subclasses should have a :meth:`api` method decorated with
:func:`~.private.time_tagger.cached_api_object`, which takes care
of asserting all required parameters are initialized as well as
invalidating the object if parameters changed. For the former, required
parameters should be passed as argument to the decorator. For the
latter, required parameters should be instances of
:class:`~.private.time_tagger.ParameterWithSetSideEffect`, with the side
effect argument `set_side_effect=self._invalidate_api`. Note that, if
parameter classes other than
:class:`~qcodes:qcodes.parameters.parameter.Parameter` are required, one
could dynamically modify them to include set side effects. For now and
for legibility, only this class is provided.

.. _Swabian Instruments Python driver: https://www.swabianinstruments.com/static/documentation/TimeTagger/index.html

"""
from __future__ import annotations

import re
import textwrap
from typing import Dict, Any, TypeVar

import numpy as np
from qcodes.instrument import Instrument, InstrumentBase, ChannelList
from qcodes.parameters import (Parameter, ParameterWithSetpoints, DelegateParameter,
                               ParamRawDataType)
from qcodes.validators import validators as vals

from .private.time_tagger import (tt, TypeValidator, ParameterWithSetSideEffect,
                                  TimeTaggerMeasurement, TimeTaggerSynchronizedMeasurements,
                                  TimeTaggerInstrumentBase, TimeTaggerVirtualChannel,
                                  cached_api_object, ArrayLikeValidator, TimeTaggerModule,
                                  refer_to_api_doc)

_T = TypeVar('_T', bound=ParamRawDataType)
_TimeTaggerModuleT = TypeVar('_TimeTaggerModuleT', bound=type[TimeTaggerModule])


class CombinerVirtualChannel(TimeTaggerVirtualChannel):
    """Virtual channel combining physical ones."""

    def __init__(self, parent: InstrumentBase, name: str,
                 api_tagger: tt.TimeTaggerBase | None = None, **kwargs: Any):
        super().__init__(parent, name, api_tagger, **kwargs)

        self.channels = ParameterWithSetSideEffect(
            'channels',
            set_side_effect=self._invalidate_api,
            instrument=self,
            label='Channels',
            vals=vals.Sequence(vals.Ints())
        )

    @cached_api_object(required_parameters={'channels'})  # type: ignore[misc]
    def api(self) -> tt.Combiner:
        return tt.Combiner(self.api_tagger, self.channels.get())


class CoincidenceVirtualChannel(TimeTaggerVirtualChannel):
    """Virtual channel clicking on coincidence of physical clicks."""

    def __init__(self, parent: InstrumentBase, name: str,
                 api_tagger: tt.TimeTaggerBase | None = None, **kwargs: Any):
        super().__init__(parent, name, api_tagger, **kwargs)

        self.channels = ParameterWithSetSideEffect(
            'channels',
            set_side_effect=self._invalidate_api,
            instrument=self,
            label='Channels',
            vals=vals.Sequence(vals.Ints())
        )

        self.coincidence_window = ParameterWithSetSideEffect(
            'coincidence_window',
            set_side_effect=self._invalidate_api,
            instrument=self,
            label='Coincidence window',
            unit='ps',
            initial_value=1000,
            vals=vals.PermissiveInts(),
            set_parser=int
        )

        self.timestamp = ParameterWithSetSideEffect(
            'timestamp',
            set_side_effect=self._invalidate_api,
            instrument=self,
            label='Timestamp',
            initial_value=tt.CoincidenceTimestamp.Last,
            vals=vals.Enum(*tt.CoincidenceTimestamp)
        )

    @cached_api_object(required_parameters={'channels'})  # type: ignore[misc]
    def api(self) -> tt.Coincidence:
        return tt.Coincidence(self.api_tagger, self.channels.get())


class CorrelationMeasurement(TimeTaggerMeasurement):
    """Measurement of the time-delay between clicks on channels."""

    def __init__(self, parent: InstrumentBase, name: str,
                 api_tagger: tt.TimeTaggerBase | None = None, **kwargs: Any):
        super().__init__(parent, name, api_tagger, **kwargs)

        self.channels = ParameterWithSetSideEffect(
            'channels',
            set_side_effect=self._invalidate_api,
            instrument=self,
            label='Channels',
            vals=vals.MultiType(vals.Sequence(vals.Ints(), length=1),
                                vals.Sequence(vals.Ints(), length=2))
        )

        self.binwidth = ParameterWithSetSideEffect(
            'binwidth',
            set_side_effect=self._invalidate_api,
            instrument=self,
            label='Binwidth',
            unit='ps',
            initial_value=1000,
            vals=vals.Numbers(),
            set_parser=int
        )

        self.n_bins = ParameterWithSetSideEffect(
            'n_bins',
            set_side_effect=self._invalidate_api,
            instrument=self,
            label='Number of bins',
            initial_value=1000,
            vals=vals.Numbers(),
            set_parser=int
        )

        self.time_bins = Parameter(
            'time_bins',
            instrument=self,
            label='Time bins',
            unit='ps',
            get_cmd=lambda: self.api.getIndex(),
            vals=vals.Arrays(shape=(self.n_bins.get_latest,), valid_types=(np.int64,))
        )

        self.data = ParameterWithSetpoints(
            'data',
            get_cmd=lambda: self.api.getData(),
            vals=vals.Arrays(shape=(self.n_bins.get_latest,), valid_types=(np.int32,)),
            setpoints=(self.time_bins,),
            instrument=self,
            label='Data',
            unit='cts',
            max_val_age=0.0
        )

        self.data_normalized = ParameterWithSetpoints(
            'data_normalized',
            get_cmd=lambda: self.api.getDataNormalized(),
            vals=vals.Arrays(shape=(self.n_bins.get_latest,), valid_types=(np.float64,)),
            setpoints=(self.time_bins,),
            instrument=self,
            label='Normalized data',
            max_val_age=0.0
        )

    @cached_api_object(required_parameters={'channels', 'binwidth', 'n_bins'})  # type: ignore[misc]
    def api(self) -> tt.Correlation:
        return tt.Correlation(self.api_tagger,
                              *self.channels.get(),
                              binwidth=self.binwidth.get(),
                              n_bins=self.n_bins.get())


class CountRateMeasurement(TimeTaggerMeasurement):
    """Measurement of the click rate on channels."""

    def __init__(self, parent: InstrumentBase, name: str,
                 api_tagger: tt.TimeTaggerBase | None = None, **kwargs: Any):
        super().__init__(parent, name, api_tagger, **kwargs)

        def number_of_channels():
            return len(self.channels.get_latest())

        self.channels = ParameterWithSetSideEffect(
            'channels',
            set_side_effect=self._invalidate_api,
            instrument=self,
            label='Channels',
            vals=vals.Sequence(vals.Ints())
        )

        # See CounterMeasurement for explanation
        self.__channels_proxy = DelegateParameter(
            f'__{self.full_name}_channels_proxy',
            source=self.channels,
            vals=ArrayLikeValidator(shape=(number_of_channels,), valid_types=(int,)),
            bind_to_instrument=False
        )

        self.data = ParameterWithSetpoints(
            'data',
            get_cmd=lambda: self.api.getData(),
            vals=vals.Arrays(shape=(number_of_channels,), valid_types=(np.float64,)),
            setpoints=(self.__channels_proxy,),
            instrument=self,
            label='Data',
            unit='Hz',
            max_val_age=0.0
        )

        self.counts_total = ParameterWithSetpoints(
            'counts_total',
            get_cmd=lambda: self.api.getCountsTotal(),
            vals=vals.Arrays(shape=(number_of_channels,), valid_types=(np.int32,)),
            setpoints=(self.__channels_proxy,),
            instrument=self,
            label='Total counts',
            max_val_age=0.0
        )

    @cached_api_object(required_parameters={'channels'})
    def api(self):
        return tt.Countrate(self.api_tagger, self.channels.get())


class CounterMeasurement(TimeTaggerMeasurement):
    """Measurement of the clicks on channels."""

    def __init__(self, parent: InstrumentBase, name: str,
                 api_tagger: tt.TimeTaggerBase | None = None, **kwargs: Any):
        super().__init__(parent, name, api_tagger, **kwargs)

        def number_of_channels():
            return len(self.channels.get_latest())

        self.channels = ParameterWithSetSideEffect(
            'channels',
            set_side_effect=self._invalidate_api,
            instrument=self,
            label='Channels',
            vals=vals.Sequence(vals.Ints())
        )

        # channels are setpoints for data parameters, but have a variable length and can therefore
        # not be validated using an Arrays validator with the shape parameter as is required by
        # ParameterWithSetpoints. Hence, we create a private dummy DelegateParameter to solve
        # the chicken-egg problem of validating on the length of the channels parameter.
        self.__channels_proxy = DelegateParameter(
            # DANGER: needs unique name
            f'__{self.full_name}_channels_proxy',
            source=self.channels,
            vals=ArrayLikeValidator(shape=(number_of_channels,),
                                    # tt.CHANNEL_UNUSED is a constant that evaluates to an integer
                                    valid_types=(int, type(tt.CHANNEL_UNUSED))),
            bind_to_instrument=False
        )

        self.binwidth = ParameterWithSetSideEffect(
            'binwidth',
            set_side_effect=self._invalidate_api,
            instrument=self,
            label='Binwidth',
            unit='ps',
            initial_value=10 ** 9,
            vals=vals.Numbers(),
            set_parser=int
        )

        self.n_values = ParameterWithSetSideEffect(
            'n_values',
            set_side_effect=self._invalidate_api,
            instrument=self,
            label='Number of bins',
            initial_value=1,
            vals=vals.Numbers(),
            set_parser=int
        )

        self.data_total_counts = Parameter(
            'data_total_counts',
            instrument=self,
            label='Total number of events',
            get_cmd=lambda: self.api.getDataTotalCounts(),
            set_cmd=False,
            max_val_age=0.0,
            vals=vals.Arrays(shape=(number_of_channels,), valid_types=(np.uint64,))
        )

        self.time_bins = Parameter(
            'time_bins',
            instrument=self,
            label='Time bins',
            unit='ps',
            get_cmd=lambda: self.api.getIndex(),
            vals=vals.Arrays(shape=(self.n_values.get_latest,), valid_types=(np.int64,))
        )

        self.rolling = Parameter(
            'rolling',
            instrument=self,
            label='Rolling buffer',
            set_cmd=None,
            initial_value=True,
            vals=vals.Bool()
        )

        self.data = ParameterWithSetpoints(
            'data',
            get_cmd=lambda: self.api.getData(self.rolling()),
            vals=vals.Arrays(shape=(number_of_channels, self.n_values.get_latest),
                             valid_types=(np.int32,)),
            setpoints=(self.__channels_proxy, self.time_bins),
            instrument=self,
            label='Data',
            unit='cts',
            max_val_age=0.0
        )

        self.data_normalized = ParameterWithSetpoints(
            'data_normalized',
            get_cmd=lambda: self.api.getDataNormalized(self.rolling()),
            vals=vals.Arrays(shape=(number_of_channels, self.n_values.get_latest),
                             valid_types=(np.float64,)),
            setpoints=(self.__channels_proxy, self.time_bins,),
            instrument=self,
            label='Normalized data',
            unit='Hz',
            max_val_age=0.0
        )

    @cached_api_object(required_parameters={'channels', 'binwidth', 'n_values'})  # type: ignore[misc]
    def api(self) -> tt.Counter:
        return tt.Counter(self.api_tagger,
                          self.channels.get(),
                          binwidth=self.binwidth.get(),
                          n_values=self.n_values.get())


class HistogramLogBinsMeasurement(TimeTaggerMeasurement):
    """Log-spaced measurement of the time-delay between clicks on channels."""

    def __init__(self, parent: InstrumentBase, name: str,
                 api_tagger: tt.TimeTaggerBase | None = None, **kwargs: Any):
        super().__init__(parent, name, api_tagger, **kwargs)

        self.click_channel = ParameterWithSetSideEffect(
            'click_channel',
            set_side_effect=self._invalidate_api,
            instrument=self,
            label='Click channel',
            vals=vals.Ints()
        )

        self.start_channel = ParameterWithSetSideEffect(
            'start_channel',
            set_side_effect=self._invalidate_api,
            instrument=self,
            label='Start channel',
            vals=vals.Ints()
        )

        self.exp_start = ParameterWithSetSideEffect(
            'exp_start',
            set_side_effect=self._invalidate_api,
            instrument=self,
            label='Start exponent',
            vals=vals.Numbers(),
            set_parser=float
        )

        self.exp_stop = ParameterWithSetSideEffect(
            'exp_stop',
            set_side_effect=self._invalidate_api,
            instrument=self,
            label='Stop exponent',
            vals=vals.Numbers(),
            set_parser=float
        )

        self.n_bins = ParameterWithSetSideEffect(
            'n_bins',
            set_side_effect=self._invalidate_api,
            instrument=self,
            label='Number of bins',
            vals=vals.Numbers(),
        )

        self.click_gate = ParameterWithSetSideEffect(
            'click_gate',
            set_side_effect=self._invalidate_api,
            instrument=self,
            label='Evaluation gate for click channel',
            vals=vals.MultiType(vals.Enum(None), TypeValidator(tt.ChannelGate))
        )

        self.start_gate = ParameterWithSetSideEffect(
            'start_gate',
            set_side_effect=self._invalidate_api,
            instrument=self,
            label='Evaluation gate for start channel',
            vals=vals.MultiType(vals.Enum(None), TypeValidator(tt.ChannelGate))
        )

        def n_bins():
            return self.n_bins.get_latest()

        def n_bin_edges():
            return n_bins() - 1

        self.time_bin_edges = Parameter(
            'time_bin_edges',
            instrument=self,
            label='Time bin edges',
            unit='ps',
            get_cmd=lambda: self.api.getBinEdges(),
            vals=vals.Arrays(shape=(n_bin_edges,), valid_types=(np.int64,))
        )

        self.time_bins = DelegateParameter(
            'time_bins',
            source=self.time_bin_edges,
            label='Time bins',
            get_parser=lambda val: val[:-1] + np.diff(val) // 2,
            vals=vals.Arrays(shape=(n_bins,), valid_types=(np.int64,)),
            bind_to_instrument=True
        )

        self.counts = ParameterWithSetpoints(
            'counts',
            get_cmd=lambda: self.api.getDataObject().getCounts(),
            vals=vals.Arrays(shape=(n_bins,), valid_types=(np.uint64,)),
            setpoints=(self.time_bins,),
            instrument=self,
            label='Counts',
            unit='cts',
            max_val_age=0.0
        )

        self.g2 = ParameterWithSetpoints(
            'g2',
            get_cmd=lambda: self.api.getDataObject().getG2(),
            vals=vals.Arrays(shape=(n_bins,), valid_types=(np.float64,)),
            setpoints=(self.time_bins,),
            instrument=self,
            label=r'$g^{(2)}(\tau)$',
            max_val_age=0.0
        )

    @cached_api_object(required_parameters={
        'click_channel', 'start_channel', 'exp_start', 'exp_stop', 'n_bins'
    })  # type: ignore[misc]
    def api(self) -> tt.HistogramLogBins:
        return tt.HistogramLogBins(self.api_tagger, self.click_channel.get(),
                                   self.start_channel.get(), self.exp_start.get(),
                                   self.exp_stop.get(), self.n_bins.get(),
                                   click_gate=self.click_gate.get(),
                                   start_gate=self.start_gate.get())


class TimeTagger(TimeTaggerInstrumentBase, Instrument):
    """QCoDeS driver for Time Tagger devices."""

    def __init__(self, name: str, serial: str = '', **kwargs):
        """Initialize a TimeTagger instrument.

        Parameters
        ----------
        name :
            The instrument name
        serial :
            The device's serial number. If left empty, the first
            available device is connected to.

        """
        if tt is None:
            raise ImportError('This driver requires the TimeTagger python module. Download it at '
                              'https://www.swabianinstruments.com/time-tagger/downloads/')

        super().__init__(name, **kwargs)
        self._api = tt.createTimeTagger(serial)

        self.add_submodule('synchronized_measurements',
                           TimeTaggerSynchronizedMeasurements(self, 'synchronized_measurements'))

        for cls in TimeTaggerModule.implementations():
            self._add_channel_list(cls)

        self.connect_message()

    @property
    def api(self) -> tt.TimeTaggerBase:
        return self._api

    def remove_all_measurements(self):
        """Remove all entries of TimeTaggerMeasurement instances from
        channel lists."""
        for cls in filter(lambda x: issubclass(x, TimeTaggerMeasurement),
                          TimeTaggerModule.implementations()):
            lst = getattr(self, _parse_time_tagger_module(cls)[1])
            for i in range(len(lst)):
                lst.pop()

    def remove_all_virtual_channels(self):
        """Remove all entries of TimeTaggerVirtualChannel instances from
        channel lists."""
        for cls in filter(lambda x: issubclass(x, TimeTaggerVirtualChannel),
                          TimeTaggerModule.implementations()):
            lst = getattr(self, _parse_time_tagger_module(cls)[1])
            for i in range(len(lst)):
                lst.pop()

    @refer_to_api_doc('TimeTagger')
    def set_trigger_level(self, channel: int, level: float):
        return self.api.setTriggerLevel(channel, level)

    @refer_to_api_doc('TimeTagger')
    def get_trigger_level(self, channel: int) -> float:
        return self.api.getTriggerLevel(channel)

    @refer_to_api_doc('TimeTaggerBase')
    def set_input_delay(self, channel: int, delay: int):
        return self.api.setInputDelay(channel, delay)

    @refer_to_api_doc('TimeTaggerBase')
    def get_input_delay(self, channel: int) -> int:
        return self.api.getInputDelay(channel)

    @refer_to_api_doc('TimeTagger')
    def set_test_signal(self, channels: list[int], state: bool):
        return self.api.setTestSignal(channels, state)

    @refer_to_api_doc('TimeTagger')
    def get_test_signal(self, channel: int) -> bool:
        return self.api.getTestSignal(channel)

    def close(self) -> None:
        try:
            tt.freeTimeTagger(self.api)
        except AttributeError:
            # API not initialized
            pass
        super().close()

    def get_idn(self) -> Dict[str, str | None]:
        return {'vendor': 'Swabian Instruments',
                'model': self.api.getModel(),
                'serial': self.api.getSerial(),
                'firmware': self.api.getFirmwareVersion()}

    def _add_channel_list(self, cls: _TimeTaggerModuleT):
        """Automatically generates add_{xxx}_{yyy} methods for all
        registered implementations of TimeTaggerModule."""

        def fun(name: str | None = None,
                api_tagger: tt.TimeTaggerBase | None = None, label: str | None = None,
                **kwargs: Any) -> TimeTaggerModule:
            if name is None:
                name = f'{functionality}_{len(channellist) + 1}'
            if label is None:
                label = name.replace('_', ' ').capitalize()

            channel = cls(self, name, api_tagger, label=label, **kwargs)
            channellist.append(channel)
            return channel

        functionality, listname, type_snake = _parse_time_tagger_module(cls)
        channellist = ChannelList(parent=self, name=listname, chan_type=cls)
        self.add_submodule(listname, channellist)

        fun.__doc__ = textwrap.dedent(
            f"""Add a new :class:`{cls.__qualname__}` to the
            :class:`ChannelList` :attr:`{listname}`.

            Parameters
            ----------
            name :
                A name for the {type_snake.replace('_', ' ')} type.
                Defaults to ``{functionality}_[number]``.
            api_tagger :
                The :mod:`TimeTagger` tagger object to use. Defaults to the
                physical one, but can also be the proxy returned by
                :meth:`TimeTagger.SynchronizedMeasurements.getTagger`
            **kwargs :
                Passed along to the :class:`InstrumentChannel` constructor.

            Returns
            -------
            {functionality}_{type_snake} :
                The newly added {cls.__qualname__} object.
            """
        )
        fun.__name__ = f"add_{listname.rstrip('s')}"
        setattr(self, fun.__name__, fun)


def _parse_time_tagger_module(cls: _TimeTaggerModuleT) -> tuple[str, str, str]:
    if issubclass(cls, TimeTaggerMeasurement):
        type_camel = 'Measurement'
    elif issubclass(cls, TimeTaggerVirtualChannel):
        type_camel = 'VirtualChannel'
    else:
        raise ValueError(f'{cls} not a subclass of TimeTaggerMeasurement or '
                         'TimeTaggerVirtualChannel.')

    functionality = _camel_to_snake(cls.__qualname__[:-len(type_camel)])
    type_snake = _camel_to_snake(type_camel)
    listname = f'{functionality}_{type_snake}s'
    return functionality, listname, type_snake


def _camel_to_snake(name: str) -> str:
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
