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

        self.channels = self.add_parameter(
            'channels',
            ParameterWithSetSideEffect,
            set_side_effect=self._invalidate_api,
            label='Channels',
            vals=vals.Sequence(vals.Ints())
        )
        """List of channels to be combined into a single virtual channel."""

    @cached_api_object(required_parameters={'channels'})  # type: ignore[misc]
    def api(self) -> tt.Combiner:
        return tt.Combiner(self.api_tagger, self.channels.get())


class CoincidenceVirtualChannel(TimeTaggerVirtualChannel):
    """Virtual channel clicking on coincidence of physical clicks."""

    def __init__(self, parent: InstrumentBase, name: str,
                 api_tagger: tt.TimeTaggerBase | None = None, **kwargs: Any):
        super().__init__(parent, name, api_tagger, **kwargs)

        self.channels = self.add_parameter(
            'channels',
            ParameterWithSetSideEffect,
            set_side_effect=self._invalidate_api,
            label='Channels',
            vals=vals.Sequence(vals.Ints())
        )
        """List of channels on which coincidence will be detected in the 
        virtual channel."""

        self.coincidence_window = self.add_parameter(
            'coincidence_window',
            ParameterWithSetSideEffect,
            set_side_effect=self._invalidate_api,
            label='Coincidence window',
            unit='ps',
            initial_value=1000,
            vals=vals.PermissiveInts(),
            set_parser=int
        )
        """Maximum time between all events for a coincidence."""

        self.timestamp = self.add_parameter(
            'timestamp',
            ParameterWithSetSideEffect,
            set_side_effect=self._invalidate_api,
            label='Timestamp',
            initial_value=tt.CoincidenceTimestamp.Last,
            vals=vals.Enum(*tt.CoincidenceTimestamp)
        )
        """Type of timestamp for virtual channel."""

    @cached_api_object(required_parameters={'channels'})  # type: ignore[misc]
    def api(self) -> tt.Coincidence:
        return tt.Coincidence(self.api_tagger, self.channels.get())


class CorrelationMeasurement(TimeTaggerMeasurement):
    """Measurement of the time-delay between clicks on channels."""

    def __init__(self, parent: InstrumentBase, name: str,
                 api_tagger: tt.TimeTaggerBase | None = None, **kwargs: Any):
        super().__init__(parent, name, api_tagger, **kwargs)

        self.channels = self.add_parameter(
            'channels',
            ParameterWithSetSideEffect,
            set_side_effect=self._invalidate_api,
            label='Channels',
            vals=vals.MultiType(vals.Sequence(vals.Ints(), length=1),
                                vals.Sequence(vals.Ints(), length=2))
        )
        """Channel on which (stop) clicks are received and channel on which 
        reference clicks (start) are received (when left empty or set to 
        :class:`TimeTagger:CHANNEL_UNUSED` -> an auto-correlation measurement 
        is performed, which is the same as setting channel_1 = channel_2)."""

        self.binwidth = self.add_parameter(
            'binwidth',
            ParameterWithSetSideEffect,
            set_side_effect=self._invalidate_api,
            label='Binwidth',
            unit='ps',
            initial_value=1000,
            vals=vals.Numbers(),
            set_parser=int
        )
        """Bin width in ps."""

        self.n_bins = self.add_parameter(
            'n_bins',
            ParameterWithSetSideEffect,
            set_side_effect=self._invalidate_api,
            label='Number of bins',
            initial_value=1000,
            vals=vals.Numbers(),
            set_parser=int
        )
        """The number of bins in the resulting histogram."""

        self.time_bins = self.add_parameter(
            'time_bins',
            Parameter,
            label='Time bins',
            unit='ps',
            get_cmd=lambda: self.api.getIndex(),
            vals=vals.Arrays(shape=(self.n_bins.get_latest,), valid_types=(np.int64,))
        )
        """A vector of size n_bins containing the time bins in ps."""

        self.data = self.add_parameter(
            'data',
            ParameterWithSetpoints,
            get_cmd=lambda: self.api.getData(),
            vals=vals.Arrays(shape=(self.n_bins.get_latest,), valid_types=(np.int32,)),
            setpoints=(self.time_bins,),
            label='Data',
            unit='cts',
            max_val_age=0.0
        )
        """A one-dimensional array of size n_bins containing the histogram."""

        self.data_normalized = self.add_parameter(
            'data_normalized',
            ParameterWithSetpoints,
            get_cmd=lambda: self.api.getDataNormalized(),
            vals=vals.Arrays(shape=(self.n_bins.get_latest,), valid_types=(np.float64,)),
            setpoints=(self.time_bins,),
            label='Normalized data',
            max_val_age=0.0
        )
        """Data normalized by the binwidth and the average count rate."""

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

        self.channels = self.add_parameter(
            'channels',
            ParameterWithSetSideEffect,
            set_side_effect=self._invalidate_api,
            label='Channels',
            vals=vals.Sequence(vals.Ints())
        )
        """Channels for which the average count rate is measured."""

        # See CounterMeasurement for explanation
        # Not using add_parameter (GH #6715)
        self.__channels_proxy = DelegateParameter(
            f'__{self.full_name}_channels_proxy',
            source=self.channels,
            vals=ArrayLikeValidator(shape=(number_of_channels,), valid_types=(int,)),
            bind_to_instrument=False
        )

        self.data = self.add_parameter(
            'data',
            ParameterWithSetpoints,
            get_cmd=lambda: self.api.getData(),
            vals=vals.Arrays(shape=(number_of_channels,), valid_types=(np.float64,)),
            setpoints=(self.__channels_proxy,),
            label='Data',
            unit='Hz',
            max_val_age=0.0
        )
        """Average count rate in counts per second."""

        self.counts_total = self.add_parameter(
            'counts_total',
            ParameterWithSetpoints,
            get_cmd=lambda: self.api.getCountsTotal(),
            vals=vals.Arrays(shape=(number_of_channels,), valid_types=(np.int32,)),
            setpoints=(self.__channels_proxy,),
            label='Total counts',
            max_val_age=0.0
        )
        """The total number of events since the instantiation of this object."""

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

        self.channels = self.add_parameter(
            'channels',
            ParameterWithSetSideEffect,
            set_side_effect=self._invalidate_api,
            label='Channels',
            vals=vals.Sequence(vals.Ints())
        )
        """Channels used for counting tags."""

        # channels are setpoints for data parameters, but have a variable length and can therefore
        # not be validated using an Arrays validator with the shape parameter as is required by
        # ParameterWithSetpoints. Hence, we create a private dummy DelegateParameter to solve
        # the chicken-egg problem of validating on the length of the channels parameter.
        # Not using add_parameter (GH #6715)
        self.__channels_proxy = DelegateParameter(
            # DANGER: needs unique name
            f'__{self.full_name}_channels_proxy',
            source=self.channels,
            vals=ArrayLikeValidator(shape=(number_of_channels,),
                                    # tt.CHANNEL_UNUSED is a constant that evaluates to an integer
                                    valid_types=(int, type(tt.CHANNEL_UNUSED))),
            bind_to_instrument=False
        )

        self.binwidth = self.add_parameter(
            'binwidth',
            ParameterWithSetSideEffect,
            set_side_effect=self._invalidate_api,
            label='Binwidth',
            unit='ps',
            initial_value=10 ** 9,
            vals=vals.Numbers(),
            set_parser=int
        )
        """Bin width in ps."""

        self.n_values = self.add_parameter(
            'n_values',
            ParameterWithSetSideEffect,
            set_side_effect=self._invalidate_api,
            label='Number of bins',
            initial_value=1,
            vals=vals.Numbers(),
            set_parser=int
        )
        """Number of bins."""

        self.data_total_counts = self.add_parameter(
            'data_total_counts',
            Parameter,
            label='Total number of events',
            get_cmd=lambda: self.api.getDataTotalCounts(),
            set_cmd=False,
            max_val_age=0.0,
            vals=vals.Arrays(shape=(number_of_channels,), valid_types=(np.uint64,))
        )
        """Number of events per channel.
        
        Returns total number of events per channel since the last call to 
        :meth:`clear`, including the currently integrating bin. This method 
        works correctly even when the USB transfer rate or backend processing 
        capabilities are exceeded.
        """

        self.time_bins = self.add_parameter(
            'time_bins',
            Parameter,
            label='Time bins',
            unit='ps',
            get_cmd=lambda: self.api.getIndex(),
            vals=vals.Arrays(shape=(self.n_values.get_latest,), valid_types=(np.int64,))
        )
        """Returns the relative time of the bins in ps. 
        
        The first entry of the returned vector is always 0.
        """

        self.rolling = self.add_parameter(
            'rolling',
            Parameter,
            label='Rolling buffer',
            set_cmd=None,
            initial_value=True,
            vals=vals.Bool()
        )
        """Controls how the counter array is filled."""

        self.data = self.add_parameter(
            'data',
            ParameterWithSetpoints,
            get_cmd=lambda: self.api.getData(self.rolling()),
            vals=vals.Arrays(shape=(number_of_channels, self.n_values.get_latest),
                             valid_types=(np.int32,)),
            setpoints=(self.__channels_proxy, self.time_bins),
            label='Data',
            unit='cts',
            max_val_age=0.0
        )
        """An array of size ‘number of channels’ by n_values containing the 
        counts in each fully integrated bin."""

        self.data_normalized = self.add_parameter(
            'data_normalized',
            ParameterWithSetpoints,
            get_cmd=lambda: self.api.getDataNormalized(self.rolling()),
            vals=vals.Arrays(shape=(number_of_channels, self.n_values.get_latest),
                             valid_types=(np.float64,)),
            setpoints=(self.__channels_proxy, self.time_bins,),
            label='Normalized data',
            unit='Hz',
            max_val_age=0.0
        )
        """Does the same as :attr:`data` but returns the count rate in Hz as a 
        float. 
        
        Not integrated bins and bins in overflow mode are marked as NaN."""

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

        self.click_channel = self.add_parameter(
            'click_channel',
            ParameterWithSetSideEffect,
            set_side_effect=self._invalidate_api,
            label='Click channel',
            vals=vals.Ints()
        )
        """Channel on which clicks are received."""

        self.start_channel = self.add_parameter(
            'start_channel',
            ParameterWithSetSideEffect,
            set_side_effect=self._invalidate_api,
            label='Start channel',
            vals=vals.Ints()
        )
        """Channel on which start clicks are received."""

        self.exp_start = self.add_parameter(
            'exp_start',
            ParameterWithSetSideEffect,
            set_side_effect=self._invalidate_api,
            label='Start exponent',
            vals=vals.Numbers(),
            set_parser=float
        )
        """Exponent ``10^exp_start`` in seconds where the very first bin begins."""

        self.exp_stop = self.add_parameter(
            'exp_stop',
            ParameterWithSetSideEffect,
            set_side_effect=self._invalidate_api,
            label='Stop exponent',
            vals=vals.Numbers(),
            set_parser=float
        )
        """Exponent ``10^exp_stop`` in seconds where the very last bin ends."""

        self.n_bins = self.add_parameter(
            'n_bins',
            ParameterWithSetSideEffect,
            set_side_effect=self._invalidate_api,
            label='Number of bins',
            vals=vals.Numbers(),
        )
        """The number of bins in the histogram."""

        self.click_gate = self.add_parameter(
            'click_gate',
            ParameterWithSetSideEffect,
            set_side_effect=self._invalidate_api,
            label='Evaluation gate for click channel',
            vals=vals.MultiType(vals.Enum(None), TypeValidator(tt.ChannelGate))
        )
        """Optional evaluation gate for the :attr:`click_channel`."""

        self.start_gate = self.add_parameter(
            'start_gate',
            ParameterWithSetSideEffect,
            set_side_effect=self._invalidate_api,
            label='Evaluation gate for start channel',
            vals=vals.MultiType(vals.Enum(None), TypeValidator(tt.ChannelGate))
        )
        """Optional evaluation gate for the :attr:`start_channel`."""

        def n_bins():
            return self.n_bins.get_latest()

        def n_bin_edges():
            return n_bins() - 1

        self.time_bin_edges = self.add_parameter(
            'time_bin_edges',
            Parameter,
            label='Time bin edges',
            unit='ps',
            get_cmd=lambda: self.api.getBinEdges(),
            vals=vals.Arrays(shape=(n_bin_edges,), valid_types=(np.int64,))
        )
        """A vector of size `n_bins+1` containing the bin edges in picoseconds."""

        self.time_bins = self.add_parameter(
            'time_bins',
            DelegateParameter,
            source=self.time_bin_edges,
            label='Time bins',
            get_parser=lambda val: val[:-1] + np.diff(val) // 2,
            vals=vals.Arrays(shape=(n_bins,), valid_types=(np.int64,)),
            bind_to_instrument=True
        )
        """A vector of size `n_bins` containing the bin centers in picoseconds."""

        self.counts = self.add_parameter(
            'counts',
            ParameterWithSetpoints,
            get_cmd=lambda: self.api.getDataObject().getCounts(),
            vals=vals.Arrays(shape=(n_bins,), valid_types=(np.uint64,)),
            setpoints=(self.time_bins,),
            label='Counts',
            unit='cts',
            max_val_age=0.0
        )
        """A one-dimensional array of size `n_bins` containing the histogram."""

        self.g2 = self.add_parameter(
            'g2',
            ParameterWithSetpoints,
            get_cmd=lambda: self.api.getDataObject().getG2(),
            vals=vals.Arrays(shape=(n_bins,), valid_types=(np.float64,)),
            setpoints=(self.time_bins,),
            label=r'$g^{(2)}(\tau)$',
            max_val_age=0.0
        )
        """The counts normalized by the binwidth of each bin and the average 
        count rate."""

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
