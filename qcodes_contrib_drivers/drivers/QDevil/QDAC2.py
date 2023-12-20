import numpy as np
import itertools
import uuid
from time import sleep as sleep_s
from qcodes.instrument.channel import InstrumentChannel, ChannelList
from qcodes.instrument.visa import VisaInstrument
from pyvisa.errors import VisaIOError
from qcodes.utils import validators
from typing import NewType, Tuple, Sequence, List, Dict, Optional
from packaging.version import Version, parse
import abc

# Version 1.8.0
#
# Guiding principles for this driver for QDevil QDAC-II
# -----------------------------------------------------
#
# 1. Each command should be self-contained, so
#
#        qdac.ch02.dc_constant_V(0.1)
#
#    should make sure that channel 2 is in the right mode for outputting
#    a constant voltage.
#
# 2. Numeric values should be in ISO units and/or their unit should be an
#    explicitly part of the function name, like above.  If the numeric is
#    a unit-less number, then prefixed by n_ like
#
#        qdac.n_channels()
#
# 3. Allocation of resources should be automated as much as possible, preferably
#    by python context managers that automatically clean up on exit.  Such
#    context managers have a name with a '_Context' suffix.
#
# 4. Any generator should by default be set to start on the BUS trigger
#    (*TRG) so that it is possible to synchronise several generators without
#    further setup; which also eliminates the need for special cases for the
#    BUS trigger.


#
# Future improvements
# -------------------
#
# - Detect and handle mixing of internal and external triggers (_trigger).
#


pseudo_trigger_voltage = 5


error_ambiguous_wave = 'Only one of frequency_Hz or period_s can be ' \
                       'specified for a wave form'


def ints_to_comma_separated_list(array: Sequence[int]) -> str:
    return ','.join([str(x) for x in array])


def floats_to_comma_separated_list(array: Sequence[float]) -> str:
    rounded = [format(x, 'g') for x in array]
    return ','.join(rounded)


def comma_sequence_to_list(sequence: str) -> Sequence[str]:
    if not sequence:
        return []
    return [x.strip() for x in sequence.split(',')]


def comma_sequence_to_list_of_floats(sequence: str) -> Sequence[float]:
    if not sequence:
        return []
    return [float(x.strip()) for x in sequence.split(',')]


def diff_matrix(initial: Sequence[float],
                measurements: Sequence[Sequence[float]]) -> np.ndarray:
    """Subtract an array of measurements by an initial measurement
    """
    matrix = np.asarray(measurements)
    return matrix - np.asarray(list(itertools.repeat(initial, matrix.shape[1])))


def split_version_string_into_components(version: str) -> List[str]:
    return version.split('-')


"""External input trigger

There are four 3V3 non-isolated triggers on the back (1, 2, 3, 4).
"""
ExternalInput = NewType('ExternalInput', int)


class QDac2Trigger_Context:
    """Internal Triggers with automatic deallocation

    This context manager wraps an already-allocated internal trigger number so
    that the trigger can be automatically reclaimed when the context exits.
    """

    def __init__(self, parent: 'QDac2', value: int):
        self._parent = parent
        self._value = value

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._parent.free_trigger(self)
        # Propagate exceptions
        return False

    @property
    def value(self) -> int:
        """internal SCPI trigger number"""
        return self._value


def _trigger_context_to_value(trigger: QDac2Trigger_Context) -> int:
    return trigger.value


class QDac2ExternalTrigger(InstrumentChannel):
    """External output trigger

    There are three 5V isolated triggers on the front (1, 2, 3) and two
    non-isolated 3V3 on the back (4, 5).
    """

    def __init__(self, parent: 'QDac2', name: str, external: int):
        super().__init__(parent, name)
        self.add_function(
            name='source_from_bus',
            call_cmd=f'outp:trig{external}:sour bus'
        )
        self.add_parameter(
            name='source_from_input',
            # Route external input to external output
            set_cmd='outp:trig{0}:sour ext{1}'.format(external, '{}'),
            get_parser=int
        )
        self.add_parameter(
            name='source_from_trigger',
            # Route internal trigger to external output
            set_parser=_trigger_context_to_value,
            set_cmd='outp:trig{0}:sour int{1}'.format(external, '{}'),
            get_parser=int
        )
        self.add_parameter(
            name='width_s',
            label='width',
            unit='s',
            set_cmd='outp:trig{0}:widt {1}'.format(external, '{}'),
            get_cmd=f'outp:trig{external}:widt?',
            get_parser=float
        )
        self.add_parameter(
            name='polarity',
            label='polarity',
            set_cmd='outp:trig{0}:pol {1}'.format(external, '{}'),
            get_cmd=f'outp:trig{external}:pol?',
            get_parser=str,
            vals=validators.Enum('inv', 'norm')
        )
        self.add_parameter(
            name='delay_s',
            label='delay',
            unit='s',
            set_cmd='outp:trig{0}:del {1}'.format(external, '{}'),
            get_cmd=f'outp:trig{external}:del?',
            get_parser=float
        )
        self.add_function(
            name='signal',
            call_cmd=f'outp:trig{external}:sign'
        )


class _Channel_Context(metaclass=abc.ABCMeta):

    def __init__(self, channel: 'QDac2Channel'):
        self._channel = channel

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Propagate exceptions
        return False

    def allocate_trigger(self) -> QDac2Trigger_Context:
        """Allocate internal trigger

        Returns:
            QDac2Trigger_Context: Context that wraps the trigger
        """
        return self._channel._parent.allocate_trigger()

    @abc.abstractmethod
    def start_on(self, trigger: QDac2Trigger_Context) -> None:
        pass

    @abc.abstractmethod
    def start_once_on(self, trigger: QDac2Trigger_Context) -> None:
        pass

    @abc.abstractmethod
    def start_on_external(self, trigger: ExternalInput) -> None:
        pass

    @abc.abstractmethod
    def start_once_on_external(self, trigger: ExternalInput) -> None:
        pass

    @abc.abstractmethod
    def abort(self) -> None:
        pass

    def _write_channel(self, cmd: str) -> None:
        self._channel.write_channel(cmd)

    def _write_channel_floats(self, cmd: str, values: Sequence[float]) -> None:
        self._channel.write_channel_floats(cmd, values)

    def _ask_channel(self, cmd: str) -> str:
        return self._channel.ask_channel(cmd)

    def _channel_message(self, template: str) -> None:
        return self._channel._channel_message(template)


class _Dc_Context(_Channel_Context):

    def __init__(self, channel: 'QDac2Channel'):
        super().__init__(channel)
        self._write_channel('sour{0}:dc:trig:sour hold')
        self._trigger: Optional[QDac2Trigger_Context] = None
        self._marker_start: Optional[QDac2Trigger_Context] = None
        self._marker_end: Optional[QDac2Trigger_Context] = None
        self._marker_step_start: Optional[QDac2Trigger_Context] = None
        self._marker_step_end: Optional[QDac2Trigger_Context] = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.abort()
        if self._trigger:
            self._channel._parent.free_trigger(self._trigger)
        if self._marker_start:
            self._channel._parent.free_trigger(self._marker_start)
            self._write_channel(f'sour{"{0}"}:dc:mark:star 0')
        if self._marker_end:
            self._channel._parent.free_trigger(self._marker_end)
            self._write_channel(f'sour{"{0}"}:dc:mark:end 0')
        if self._marker_step_start:
            self._channel._parent.free_trigger(self._marker_step_start)
            self._write_channel(f'sour{"{0}"}:dc:mark:sst 0')
        if self._marker_step_end:
            self._channel._parent.free_trigger(self._marker_step_end)
            self._write_channel(f'sour{"{0}"}:dc:mark:send 0')
        # Always disable any triggering
        self._write_channel(f'sour{"{0}"}:dc:trig:sour imm')
        # Propagate exceptions
        return False

    def start_on(self, trigger: QDac2Trigger_Context) -> None:
        """Attach internal trigger to DC generator

        Args:
            trigger (QDac2Trigger_Context): trigger that will start DC
        """
        self._trigger = trigger
        internal = _trigger_context_to_value(trigger)
        self._write_channel(f'sour{"{0}"}:dc:trig:sour int{internal}')
        self._make_ready_to_start()

    def start_once_on(self, trigger: QDac2Trigger_Context) -> None:
        """Attach internal one-shot trigger to DC generator

        Args:
            trigger (QDac2Trigger_Context): trigger that will start DC
        """
        self._trigger = trigger
        internal = _trigger_context_to_value(trigger)
        self._write_channel(f'sour{"{0}"}:dc:trig:sour int{internal}')
        self._make_ready_to_start_once()

    def start_on_external(self, trigger: ExternalInput) -> None:
        """Attach external trigger to DC generator

        Args:
            trigger (ExternalInput): trigger that will start DC generator
        """
        self._trigger = None
        self._write_channel(f'sour{"{0}"}:dc:trig:sour ext{trigger}')
        self._make_ready_to_start()

    def start_once_on_external(self, trigger: ExternalInput) -> None:
        """Attach external one-shot trigger to DC generator

        Args:
            trigger (ExternalInput): trigger that will start DC generator
        """
        self._trigger = None
        self._write_channel(f'sour{"{0}"}:dc:trig:sour ext{trigger}')
        self._make_ready_to_start_once()

    def abort(self) -> None:
        """Abort any DC running generator on the channel
        """
        self._write_channel('sour{0}:dc:abor')

    def end_marker(self) -> QDac2Trigger_Context:
        """Internal trigger that will mark the end of the DC generator

        A new internal trigger is allocated if necessary.

        Returns:
            QDac2Trigger_Context: trigger that will mark the end
        """
        if not self._marker_end:
            self._marker_end = self.allocate_trigger()
        self._write_channel(f'sour{"{0}"}:dc:mark:end {self._marker_end.value}')
        return self._marker_end

    def start_marker(self) -> QDac2Trigger_Context:
        """Internal trigger that will mark the beginning of the DC generator

        A new internal trigger is allocated if necessary.

        Returns:
            QDac2Trigger_Context: trigger that will mark the beginning
        """
        if not self._marker_start:
            self._marker_start = self.allocate_trigger()
        self._write_channel(f'sour{"{0}"}:dc:mark:star {self._marker_start.value}')
        return self._marker_start

    def step_end_marker(self) -> QDac2Trigger_Context:
        """Internal trigger that will mark the end of each step

        A new internal trigger is allocated if necessary.

        Returns:
            QDac2Trigger_Context: trigger that will mark the end of each step
        """
        if not self._marker_step_end:
            self._marker_step_end = self.allocate_trigger()
        self._write_channel(f'sour{"{0}"}:dc:mark:send {self._marker_step_end.value}')
        return self._marker_step_end

    def step_start_marker(self) -> QDac2Trigger_Context:
        """Internal trigger that will mark the beginning of each step

        A new internal trigger is allocated if necessary.

        Returns:
            QDac2Trigger_Context: trigger that will mark the end of each step
        """
        if not self._marker_step_start:
            self._marker_step_start = self.allocate_trigger()
        self._write_channel(f'sour{"{0}"}:dc:mark:sst {self._marker_step_start.value}')
        return self._marker_step_start

    def _set_delay(self, delay_s: float) -> None:
        self._write_channel(f'sour{"{0}"}:dc:del {delay_s}')

    def _set_triggering(self) -> None:
        self._write_channel('sour{0}:dc:trig:sour bus')
        self._make_ready_to_start()

    def _start(self, description: str) -> None:
        if self._trigger:
            self._make_ready_to_start()
            return self._write_channel(f'tint {self._trigger.value}')
        self._switch_to_immediate_trigger()
        self._write_channel('sour{0}:dc:init')

    def _make_ready_to_start(self) -> None:
        self._write_channel('sour{0}:dc:init:cont on')

    def _make_ready_to_start_once(self) -> None:
        self._write_channel('sour{0}:dc:init:cont off')

    def _switch_to_immediate_trigger(self) -> None:
        self._write_channel('sour{0}:dc:init:cont off')
        self._write_channel('sour{0}:dc:trig:sour imm')


class Sweep_Context(_Dc_Context):

    def __init__(self, channel: 'QDac2Channel', start_V: float, stop_V: float,
                 points: int, repetitions: int, dwell_s: float, delay_s: float,
                 backwards: bool, stepped: bool):
        self._repetitions = repetitions
        super().__init__(channel)
        channel.write_channel('sour{0}:volt:mode swe')
        self._set_voltages(start_V, stop_V)
        channel.write_channel(f'sour{"{0}"}:swe:poin {points}')
        self._set_trigger_mode(stepped)
        channel.write_channel(f'sour{"{0}"}:swe:dwel {dwell_s}')
        super()._set_delay(delay_s)
        self._set_direction(backwards)
        self._set_repetitions()
        self._set_triggering()

    def _set_voltages(self, start_V: float, stop_V: float):
        self._write_channel(f'sour{"{0}"}:swe:star {start_V}')
        self._write_channel(f'sour{"{0}"}:swe:stop {stop_V}')

    def _set_trigger_mode(self, stepped: bool) -> None:
        if stepped:
            return self._write_channel('sour{0}:swe:gen step')
        self._write_channel('sour{0}:swe:gen auto')

    def _set_direction(self, backwards: bool) -> None:
        if backwards:
            return self._write_channel('sour{0}:swe:dir down')
        self._write_channel('sour{0}:swe:dir up')

    def _set_repetitions(self) -> None:
        self._write_channel(f'sour{"{0}"}:swe:coun {self._repetitions}')

    def _perpetual(self) -> bool:
        return self._repetitions < 0

    def start(self) -> None:
        """Start the DC sweep
        """
        self._start('DC sweep')

    def points(self) -> int:
        """
        Returns:
            int: Number of steps in the DC sweep
        """
        return int(self._ask_channel('sour{0}:swe:poin?'))

    def cycles_remaining(self) -> int:
        """
        Returns:
            int: Number of cycles remaining in the DC sweep
        """
        return int(self._ask_channel('sour{0}:swe:ncl?'))

    def time_s(self) -> float:
        """
        Returns:
            float: Seconds that it will take to do the sweep
        """
        return float(self._ask_channel('sour{0}:swe:time?'))

    def start_V(self) -> float:
        """
        Returns:
            float: Starting voltage
        """
        return float(self._ask_channel('sour{0}:swe:star?'))

    def stop_V(self) -> float:
        """
        Returns:
            float: Ending voltage
        """
        return float(self._ask_channel('sour{0}:swe:stop?'))

    def values_V(self) -> Sequence[float]:
        """
        Returns:
            Sequence[float]: List of voltages
        """
        return list(np.linspace(self.start_V(), self.stop_V(), self.points()))


class List_Context(_Dc_Context):

    def __init__(self, channel: 'QDac2Channel', voltages: Sequence[float],
                 repetitions: int, dwell_s: float, delay_s: float,
                 backwards: bool, stepped: bool):
        super().__init__(channel)
        self._repetitions = repetitions
        self._write_channel('sour{0}:volt:mode list')
        self._set_voltages(voltages)
        self._set_trigger_mode(stepped)
        self._write_channel(f'sour{"{0}"}:list:dwel {dwell_s}')
        super()._set_delay(delay_s)
        self._set_direction(backwards)
        self._set_repetitions()
        self._set_triggering()

    def _set_voltages(self, voltages: Sequence[float]) -> None:
        self._write_channel_floats('sour{0}:list:volt ', voltages)

    def _set_trigger_mode(self, stepped: bool) -> None:
        if stepped:
            return self._write_channel('sour{0}:list:tmod step')
        self._write_channel('sour{0}:list:tmod auto')

    def _set_direction(self, backwards: bool) -> None:
        if backwards:
            return self._write_channel('sour{0}:list:dir down')
        self._write_channel('sour{0}:list:dir up')

    def _set_repetitions(self) -> None:
        self._write_channel(f'sour{"{0}"}:list:coun {self._repetitions}')

    def _perpetual(self) -> bool:
        return self._repetitions < 0

    def start(self) -> None:
        """Start the DC list generator
        """
        self._start('DC list')

    def append(self, voltages: Sequence[float]) -> None:
        """Append voltages to the existing list

        Arguments:
            voltages (Sequence[float]): Sequence of voltages
        """
        self._write_channel_floats('sour{0}:list:volt:app ', voltages)
        self._make_ready_to_start()

    def points(self) -> int:
        """
        Returns:
            int: Number of steps in the DC list
        """
        return int(self._ask_channel('sour{0}:list:poin?'))

    def cycles_remaining(self) -> int:
        """
        Returns:
            int: Number of cycles remaining in the DC list
        """
        return int(self._ask_channel('sour{0}:list:ncl?'))

    def values_V(self) -> Sequence[float]:
        """
        Returns:
            Sequence[float]: List of voltages
        """
        # return comma_sequence_to_list_of_floats(
        #     self._ask_channel('sour{0}:list:volt?'))
        return comma_sequence_to_list_of_floats(
            self._ask_channel('sour{0}:list:volt?'))


class _Waveform_Context(_Channel_Context):

    def __init__(self, channel: 'QDac2Channel'):
        super().__init__(channel)
        self._trigger: Optional[QDac2Trigger_Context] = None
        self._marker_start: Optional[QDac2Trigger_Context] = None
        self._marker_end: Optional[QDac2Trigger_Context] = None
        self._marker_period_start: Optional[QDac2Trigger_Context] = None
        self._marker_period_end: Optional[QDac2Trigger_Context] = None

    def __enter__(self):
        return self

    def _cleanup(self, wave_kind: str) -> None:
        if self._trigger:
            self._channel._parent.free_trigger(self._trigger)
        if self._marker_start:
            self._channel._parent.free_trigger(self._marker_start)
            self._write_channel(f'sour{"{0}"}:{wave_kind}:mark:star 0')
        if self._marker_end:
            self._channel._parent.free_trigger(self._marker_end)
            self._write_channel(f'sour{"{0}"}:{wave_kind}:mark:end 0')
        if self._marker_period_start:
            self._channel._parent.free_trigger(self._marker_period_start)
            self._write_channel(f'sour{"{0}"}:{wave_kind}:mark:pstart 0')
        if self._marker_period_end:
            self._channel._parent.free_trigger(self._marker_period_end)
            self._write_channel(f'sour{"{0}"}:{wave_kind}:mark:pend 0')
        # Always disable any triggering
        self._write_channel(f'sour{"{0}"}:{wave_kind}:trig:sour imm')

    def _start(self, wave_kind: str, description: str) -> None:
        if self._trigger:
            self._make_ready_to_start(wave_kind)
            return self._write_channel(f'tint {self._trigger.value}')
        self._switch_to_immediate_trigger(wave_kind)
        self._write_channel(f'sour{"{0}"}:{wave_kind}:init')

    def _start_on(self, trigger: QDac2Trigger_Context, wave_kind: str) -> None:
        self._trigger = trigger
        internal = _trigger_context_to_value(trigger)
        self._write_channel(f'sour{"{0}"}:{wave_kind}:trig:sour int{internal}')
        self._make_ready_to_start(wave_kind)

    def _start_once_on(self, trigger: QDac2Trigger_Context, wave_kind: str) -> None:
        self._trigger = trigger
        internal = _trigger_context_to_value(trigger)
        self._write_channel(f'sour{"{0}"}:{wave_kind}:trig:sour int{internal}')
        self._make_ready_to_start_once(wave_kind)

    def _start_on_external(self, trigger: ExternalInput, wave_kind: str) -> None:
        self._trigger = None
        self._write_channel(f'sour{"{0}"}:{wave_kind}:trig:sour ext{trigger}')
        self._make_ready_to_start(wave_kind)

    def _start_once_on_external(self, trigger: ExternalInput, wave_kind: str) -> None:
        self._trigger = None
        self._write_channel(f'sour{"{0}"}:{wave_kind}:trig:sour ext{trigger}')
        self._make_ready_to_start_once(wave_kind)

    def _end_marker(self, wave_kind: str) -> QDac2Trigger_Context:
        if not self._marker_end:
            self._marker_end = self.allocate_trigger()
        self._write_channel(f'sour{"{0}"}:{wave_kind}:mark:end {self._marker_end.value}')
        return self._marker_end

    def _start_marker(self, wave_kind: str) -> QDac2Trigger_Context:
        if not self._marker_start:
            self._marker_start = self.allocate_trigger()
        self._write_channel(f'sour{"{0}"}:{wave_kind}:mark:star {self._marker_start.value}')
        return self._marker_start

    def _period_end_marker(self, wave_kind: str) -> QDac2Trigger_Context:
        if not self._marker_period_end:
            self._marker_period_end = self.allocate_trigger()
        self._write_channel(f'sour{"{0}"}:{wave_kind}:mark:pend {self._marker_period_end.value}')
        return self._marker_period_end

    def _period_start_marker(self, wave_kind: str) -> QDac2Trigger_Context:
        if not self._marker_period_start:
            self._marker_period_start = self.allocate_trigger()
        self._write_channel(f'sour{"{0}"}:{wave_kind}:mark:pstart {self._marker_period_start.value}')
        return self._marker_period_start

    def _make_ready_to_start(self, wave_kind: str) -> None:
        self._write_channel(f'sour{"{0}"}:{wave_kind}:init:cont on')

    def _make_ready_to_start_once(self, wave_kind: str) -> None:
        self._write_channel(f'sour{"{0}"}:{wave_kind}:init:cont off')

    def _switch_to_immediate_trigger(self, wave_kind: str):
        self._write_channel(f'sour{"{0}"}:{wave_kind}:init:cont off')
        self._write_channel(f'sour{"{0}"}:{wave_kind}:trig:sour imm')

    def _set_delay(self, wave_kind: str, delay_s) -> None:
        self._write_channel(f'sour{"{0}"}:{wave_kind}:del {delay_s}')

    def _set_slew(self, wave_kind: str, slew_V_s: Optional[float]) -> None:
        if slew_V_s:
            # Bug, see https://trello.com/c/SeeUrRNY
            self._write_channel(f'sour{"{0}"}:{wave_kind}:slew {slew_V_s}')
        else:
            self._write_channel(f'sour{"{0}"}:{wave_kind}:slew inf')


class Square_Context(_Waveform_Context):

    def __init__(self, channel: 'QDac2Channel', frequency_Hz: Optional[float],
                 repetitions: int, period_s: Optional[float],
                 duty_cycle_percent: float, kind: str, inverted: bool,
                 span_V: float, offset_V: float, delay_s: float,
                 slew_V_s: Optional[float]):
        super().__init__(channel)
        self._repetitions = repetitions
        self._write_channel('sour{0}:squ:trig:sour hold')
        self._set_frequency(frequency_Hz, period_s)
        self._write_channel(f'sour{"{0}"}:squ:dcyc {duty_cycle_percent}')
        self._set_type(kind)
        self._set_polarity(inverted)
        self._write_channel(f'sour{"{0}"}:squ:span {span_V}')
        self._write_channel(f'sour{"{0}"}:squ:offs {offset_V}')
        self._set_slew('squ', slew_V_s)
        super()._set_delay('squ', delay_s)
        self._write_channel(f'sour{"{0}"}:squ:coun {repetitions}')
        self._set_triggering()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.abort()
        super()._cleanup('squ')
        # Propagate exceptions
        return False

    def start(self) -> None:
        """Start the square wave generator
        """
        self._start('squ', 'square wave')

    def abort(self) -> None:
        """Abort any running square wave generator
        """
        self._write_channel('sour{0}:squ:abor')

    def cycles_remaining(self) -> int:
        """
        Returns:
            int: Number of cycles remaining in the square wave
        """
        return int(self._ask_channel('sour{0}:squ:ncl?'))

    def _set_frequency(self, frequency_Hz: Optional[float],
                       period_s: Optional[float]) -> None:
        if frequency_Hz:
            return self._write_channel(f'sour{"{0}"}:squ:freq {frequency_Hz}')
        if period_s:
            self._write_channel(f'sour{"{0}"}:squ:per {period_s}')

    def _set_type(self, kind: str) -> None:
        if kind == 'positive':
            self._write_channel('sour{0}:squ:typ pos')
        elif kind == 'negative':
            self._write_channel('sour{0}:squ:typ neg')
        else:
            self._write_channel('sour{0}:squ:typ symm')

    def _set_polarity(self, inverted: bool) -> None:
        if inverted:
            self._write_channel('sour{0}:squ:pol inv')
        else:
            self._write_channel('sour{0}:squ:pol norm')

    def _set_triggering(self) -> None:
        self._write_channel('sour{0}:squ:trig:sour bus')
        self._make_ready_to_start('squ')

    def end_marker(self) -> QDac2Trigger_Context:
        """Internal trigger that will mark the end of the square wave

        A new internal trigger is allocated if necessary.

        Returns:
            QDac2Trigger_Context: trigger that will mark the end
        """
        return super()._end_marker('squ')

    def start_marker(self) -> QDac2Trigger_Context:
        """Internal trigger that will mark the beginning of the square wave

        A new internal trigger is allocated if necessary.

        Returns:
            QDac2Trigger_Context: trigger that will mark the beginning
        """
        return super()._start_marker('squ')

    def period_end_marker(self) -> QDac2Trigger_Context:
        """Internal trigger that will mark the end of each period

        A new internal trigger is allocated if necessary.

        Returns:
            QDac2Trigger_Context: trigger that will mark the end of each period
        """
        return super()._period_end_marker('squ')

    def period_start_marker(self) -> QDac2Trigger_Context:
        """Internal trigger that will mark the beginning of each period

        A new internal trigger is allocated if necessary.

        Returns:
            QDac2Trigger_Context: trigger that will mark the beginning of each period
        """
        return super()._period_start_marker('squ')

    def start_on(self, trigger: QDac2Trigger_Context) -> None:
        """Attach internal trigger to start the square wave generator

        Args:
            trigger (QDac2Trigger_Context): trigger that will start square wave
        """
        return super()._start_on(trigger, 'squ')

    def start_once_on(self, trigger: QDac2Trigger_Context) -> None:
        """Attach internal one-shot trigger to start the square wave generator

        Args:
            trigger (QDac2Trigger_Context): trigger that will start square wave
        """
        return super()._start_once_on(trigger, 'squ')

    def start_on_external(self, trigger: ExternalInput) -> None:
        """Attach external trigger to start the square wave generator

        Args:
            trigger (ExternalInput): external trigger that will start square wave
        """
        return super()._start_on_external(trigger, 'squ')

    def start_once_on_external(self, trigger: ExternalInput) -> None:
        """Attach external one-shot trigger to start the square wave generator

        Args:
            trigger (ExternalInput): external trigger that will start square wave
        """
        return super()._start_once_on_external(trigger, 'squ')


class Sine_Context(_Waveform_Context):

    def __init__(self, channel: 'QDac2Channel', frequency_Hz: Optional[float],
                 repetitions: int, period_s: Optional[float], inverted: bool,
                 span_V: float, offset_V: float, delay_s: float,
                 slew_V_s: Optional[float]):
        super().__init__(channel)
        self._repetitions = repetitions
        self._write_channel('sour{0}:sine:trig:sour hold')
        self._set_frequency(frequency_Hz, period_s)
        self._set_polarity(inverted)
        self._write_channel(f'sour{"{0}"}:sine:span {span_V}')
        self._write_channel(f'sour{"{0}"}:sine:offs {offset_V}')
        self._set_slew('sine', slew_V_s)
        super()._set_delay('sine', delay_s)
        self._write_channel(f'sour{"{0}"}:sine:coun {repetitions}')
        self._set_triggering()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.abort()
        super()._cleanup('sine')
        # Propagate exceptions
        return False

    def start(self) -> None:
        """Start the sine wave generator
        """
        self._start('sine', 'sine wave')

    def abort(self) -> None:
        """Abort any running sine wave generator
        """
        self._write_channel('sour{0}:sine:abor')

    def cycles_remaining(self) -> int:
        """
        Returns:
            int: Number of cycles remaining in the sine wave
        """
        return int(self._ask_channel('sour{0}:sine:ncl?'))

    def _set_frequency(self, frequency_Hz: Optional[float],
                       period_s: Optional[float]) -> None:
        if frequency_Hz:
            return self._write_channel(f'sour{"{0}"}:sine:freq {frequency_Hz}')
        if period_s:
            self._write_channel(f'sour{"{0}"}:sine:per {period_s}')

    def _set_polarity(self, inverted: bool) -> None:
        if inverted:
            self._write_channel('sour{0}:sine:pol inv')
        else:
            self._write_channel('sour{0}:sine:pol norm')

    def _set_triggering(self) -> None:
        self._write_channel('sour{0}:sine:trig:sour bus')
        self._make_ready_to_start('sine')

    def end_marker(self) -> QDac2Trigger_Context:
        """Internal trigger that will mark the end of the sine wave

        A new internal trigger is allocated if necessary.

        Returns:
            QDac2Trigger_Context: trigger that will mark the end
        """
        return super()._end_marker('sine')

    def start_marker(self) -> QDac2Trigger_Context:
        """Internal trigger that will mark the beginning of the sine wave

        A new internal trigger is allocated if necessary.

        Returns:
            QDac2Trigger_Context: trigger that will mark the beginning
        """
        return super()._start_marker('sine')

    def period_end_marker(self) -> QDac2Trigger_Context:
        """Internal trigger that will mark the end of each period

        A new internal trigger is allocated if necessary.

        Returns:
            QDac2Trigger_Context: trigger that will mark the end of each period
        """
        return super()._period_end_marker('sine')

    def period_start_marker(self) -> QDac2Trigger_Context:
        """Internal trigger that will mark the beginning of each period

        A new internal trigger is allocated if necessary.

        Returns:
            QDac2Trigger_Context: trigger that will mark the beginning of each period
        """
        return super()._period_start_marker('sine')

    def start_on(self, trigger: QDac2Trigger_Context) -> None:
        """Attach internal trigger to start the sine wave generator

        Args:
            trigger (QDac2Trigger_Context): trigger that will start sine wave
        """
        return super()._start_on(trigger, 'sine')

    def start_once_on(self, trigger: QDac2Trigger_Context) -> None:
        """Attach internal one-shot trigger to start the sine wave generator

        Args:
            trigger (QDac2Trigger_Context): trigger that will start sine wave
        """
        return super()._start_once_on(trigger, 'sin')

    def start_on_external(self, trigger: ExternalInput) -> None:
        """Attach external trigger to start the sine wave generator

        Args:
            trigger (ExternalInput): external trigger that will start sine wave
        """
        return super()._start_on_external(trigger, 'sine')

    def start_once_on_external(self, trigger: ExternalInput) -> None:
        """Attach external one-shot trigger to start the sine wave generator

        Args:
            trigger (ExternalInput): external trigger that will start sine wave
        """
        return super()._start_once_on_external(trigger, 'sin')


class Triangle_Context(_Waveform_Context):

    def __init__(self, channel: 'QDac2Channel', frequency_Hz: Optional[float],
                 repetitions: int, period_s: Optional[float],
                 duty_cycle_percent: float, inverted: bool, span_V: float,
                 offset_V: float, delay_s: float, slew_V_s: Optional[float]):
        super().__init__(channel)
        self._repetitions = repetitions
        self._write_channel('sour{0}:tri:trig:sour hold')
        self._set_frequency(frequency_Hz, period_s)
        self._write_channel(f'sour{"{0}"}:tri:dcyc {duty_cycle_percent}')
        self._set_polarity(inverted)
        self._write_channel(f'sour{"{0}"}:tri:span {span_V}')
        self._write_channel(f'sour{"{0}"}:tri:offs {offset_V}')
        self._set_slew('tri', slew_V_s)
        super()._set_delay('tri', delay_s)
        self._write_channel(f'sour{"{0}"}:tri:coun {repetitions}')
        self._set_triggering()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.abort()
        super()._cleanup('tri')
        # Propagate exceptions
        return False

    def start(self) -> None:
        """Start the triangle wave generator
        """
        self._start('tri', 'triangle wave')

    def abort(self) -> None:
        """Abort any running triangle wave generator
        """
        self._write_channel('sour{0}:tri:abor')

    def cycles_remaining(self) -> int:
        """
        Returns:
            int: Number of cycles remaining in the triangle wave
        """
        return int(self._ask_channel('sour{0}:tri:ncl?'))

    def _set_frequency(self, frequency_Hz: Optional[float],
                       period_s: Optional[float]) -> None:
        if frequency_Hz:
            return self._write_channel(f'sour{"{0}"}:tri:freq {frequency_Hz}')
        if period_s:
            self._write_channel(f'sour{"{0}"}:tri:per {period_s}')

    def _set_type(self, kind: bool) -> None:
        if kind == 'positive':
            self._write_channel('sour{0}:tri:typ pos')
        elif kind == 'negative':
            self._write_channel('sour{0}:tri:typ neg')
        else:
            self._write_channel('sour{0}:tri:typ symm')

    def _set_polarity(self, inverted: bool) -> None:
        if inverted:
            self._write_channel('sour{0}:tri:pol inv')
        else:
            self._write_channel('sour{0}:tri:pol norm')

    def _set_triggering(self) -> None:
        self._write_channel('sour{0}:tri:trig:sour bus')
        self._make_ready_to_start('tri')

    def end_marker(self) -> QDac2Trigger_Context:
        """Internal trigger that will mark the end of the triangle wave

        A new internal trigger is allocated if necessary.

        Returns:
            QDac2Trigger_Context: trigger that will mark the end
        """
        return super()._end_marker('tri')

    def start_marker(self) -> QDac2Trigger_Context:
        """Internal trigger that will mark the beginning of the triangle wave

        A new internal trigger is allocated if necessary.

        Returns:
            QDac2Trigger_Context: trigger that will mark the beginning
        """
        return super()._start_marker('tri')

    def period_end_marker(self) -> QDac2Trigger_Context:
        """Internal trigger that will mark the end of each period

        A new internal trigger is allocated if necessary.

        Returns:
            QDac2Trigger_Context: trigger that will mark the end of each period
        """
        return super()._period_end_marker('tri')

    def period_start_marker(self) -> QDac2Trigger_Context:
        """Internal trigger that will mark the beginning of each period

        A new internal trigger is allocated if necessary.

        Returns:
            QDac2Trigger_Context: trigger that will mark the beginning of each period
        """
        return super()._period_start_marker('tri')

    def start_on(self, trigger: QDac2Trigger_Context) -> None:
        """Attach internal trigger to start the triangle wave generator

        Args:
            trigger (QDac2Trigger_Context): trigger that will start triangle
        """
        return super()._start_on(trigger, 'tri')

    def start_once_on(self, trigger: QDac2Trigger_Context) -> None:
        """Attach internal one-shot trigger to start the triangle wave generator

        Args:
            trigger (QDac2Trigger_Context): trigger that will start triangle wave
        """
        return super()._start_once_on(trigger, 'tri')

    def start_on_external(self, trigger: ExternalInput) -> None:
        """Attach external trigger to start the triangle wave generator

        Args:
            trigger (ExternalInput): external trigger that will start triangle
        """
        return super()._start_on_external(trigger, 'tri')

    def start_once_on_external(self, trigger: ExternalInput) -> None:
        """Attach external one-shot trigger to start the triangle wave generator

        Args:
            trigger (ExternalInput): external trigger that will start triangle wave
        """
        return super()._start_once_on_external(trigger, 'tri')


class Awg_Context(_Waveform_Context):

    def __init__(self, channel: 'QDac2Channel', trace_name: str,
                 repetitions: int, scale: float, offset_V: float,
                 slew_V_s: Optional[float]):
        super().__init__(channel)
        self._repetitions = repetitions
        self._write_channel('sour{0}:awg:trig:sour hold')
        self._write_channel(f'sour{"{0}"}:awg:def "{trace_name}"')
        self._write_channel(f'sour{"{0}"}:awg:scal {scale}')
        self._write_channel(f'sour{"{0}"}:awg:offs {offset_V}')
        self._set_slew('awg', slew_V_s)
        self._write_channel(f'sour{"{0}"}:awg:coun {repetitions}')
        self._set_triggering()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.abort()
        super()._cleanup('awg')
        # Propagate exceptions
        return False

    def start(self) -> None:
        """Start the AWG
        """
        self._start('awg', 'AWG')

    def abort(self) -> None:
        """Abort any running AWG
        """
        self._write_channel('sour{0}:awg:abor')

    def cycles_remaining(self) -> int:
        """
        Returns:
            int: Number of cycles remaining in the AWG
        """
        return int(self._ask_channel('sour{0}:awg:ncl?'))

    def _set_triggering(self) -> None:
        self._write_channel('sour{0}:awg:trig:sour bus')
        self._make_ready_to_start('awg')

    def end_marker(self) -> QDac2Trigger_Context:
        """Internal trigger that will mark the end of the AWG

        A new internal trigger is allocated if necessary.

        Returns:
            QDac2Trigger_Context: trigger that will mark the end
        """
        return super()._end_marker('awg')

    def start_marker(self) -> QDac2Trigger_Context:
        """Internal trigger that will mark the beginning of the AWG

        A new internal trigger is allocated if necessary.

        Returns:
            QDac2Trigger_Context: trigger that will mark the beginning
        """
        return super()._start_marker('awg')

    def period_end_marker(self) -> QDac2Trigger_Context:
        """Internal trigger that will mark the end of each period

        A new internal trigger is allocated if necessary.

        Returns:
            QDac2Trigger_Context: trigger that will mark the end of each period
        """
        return super()._period_end_marker('awg')

    def period_start_marker(self) -> QDac2Trigger_Context:
        """Internal trigger that will mark the beginning of each period

        A new internal trigger is allocated if necessary.

        Returns:
            QDac2Trigger_Context: trigger that will mark the beginning of each period
        """
        return super()._period_start_marker('awg')

    def start_on(self, trigger: QDac2Trigger_Context) -> None:
        """Attach internal trigger to start the AWG

        Args:
            trigger (QDac2Trigger_Context): trigger that will start AWG
        """
        return super()._start_on(trigger, 'awg')

    def start_once_on(self, trigger: QDac2Trigger_Context) -> None:
        """Attach internal one-shot trigger to start the AWG

        Args:
            trigger (QDac2Trigger_Context): trigger that will start AWG
        """
        return super()._start_once_on(trigger, 'awg')

    def start_on_external(self, trigger: ExternalInput) -> None:
        """Attach external trigger to start the AWG

        Args:
            trigger (ExternalInput): external trigger that will start AWG
        """
        return super()._start_on_external(trigger, 'awg')

    def start_once_on_external(self, trigger: ExternalInput) -> None:
        """Attach external one-shot trigger to start the AWG

        Args:
            trigger (ExternalInput): external trigger that will start AWG
        """
        return super()._start_once_on_external(trigger, 'awg')


class Measurement_Context(_Channel_Context):

    def __init__(self, channel: 'QDac2Channel', delay_s: float,
                 repetitions: int, current_range: str,
                 aperture_s: Optional[float], nplc: Optional[int]):
        super().__init__(channel)
        self._trigger: Optional[QDac2Trigger_Context] = None
        self._write_channel(f'sens{"{0}"}:del {delay_s}')
        self._write_channel(f'sens{"{0}"}:rang {current_range}')
        self._set_aperture(aperture_s, nplc)
        self._write_channel(f'sens{"{0}"}:coun {repetitions}')
        self._set_triggering()

    def start(self) -> None:
        """Start a current measurement
        """
        if self._trigger:
            return self._write_channel(f'tint {self._trigger.value}')
        self._switch_to_immediate_trigger()
        self._write_channel('sens{0}:init')

    def _switch_to_immediate_trigger(self) -> None:
        self._write_channel('sens{0}:init:cont off')
        self._write_channel('sens{0}:trig:sour imm')

    def start_on(self, trigger: QDac2Trigger_Context) -> None:
        """Attach internal trigger to start the current measurement

        Args:
            trigger (QDac2Trigger_Context): trigger that will start measurement
        """
        self._trigger = trigger
        internal = _trigger_context_to_value(trigger)
        self._write_channel(f'sens{"{0}"}:trig:sour int{internal}')
        self._write_channel(f'sens{"{0}"}:init:cont on')

    def start_once_on(self, trigger: QDac2Trigger_Context) -> None:
        """Attach internal once-shot trigger to start the current measurement

        Args:
            trigger (QDac2Trigger_Context): trigger that will start measurement
        """
        self._trigger = trigger
        internal = _trigger_context_to_value(trigger)
        self._write_channel(f'sens{"{0}"}:trig:sour int{internal}')
        self._write_channel(f'sens{"{0}"}:init:cont off')

    def start_on_external(self, trigger: ExternalInput) -> None:
        """Attach external trigger to start the current measurement

        Args:
            trigger (ExternalInput): trigger that will start measurement
        """
        self._write_channel(f'sens{"{0}"}:trig:sour ext{trigger}')
        self._write_channel(f'sens{"{0}"}:init:cont on')

    def start_once_on_external(self, trigger: ExternalInput) -> None:
        """Attach external one-shot trigger to start the current measurement

        Args:
            trigger (ExternalInput): trigger that will start measurement
        """
        self._write_channel(f'sens{"{0}"}:trig:sour ext{trigger}')
        self._write_channel(f'sens{"{0}"}:init:cont off')

    def abort(self) -> None:
        """Abort current measurement
        """
        self._write_channel('sens{0}:abor')

    def n_cycles_remaining(self) -> int:
        """
        Returns:
            int: Number of measurements remaining
        """
        return int(self._ask_channel('sens{0}:ncl?'))

    def n_available(self) -> int:
        """
        Returns:
            int: Number of measurements available
        """
        return int(self._ask_channel('sens{0}:data:poin?'))

    def available_A(self) -> Sequence[float]:
        """Retrieve current measurements

        The available measurements will be removed from measurement queue.

        Returns:
            Sequence[float]: list of available current measurements
        """
        # Bug circumvention
        if self.n_available() == 0:
            return list()
        return comma_sequence_to_list_of_floats(
            self._ask_channel('sens{0}:data:rem?'))

    def peek_A(self) -> float:
        """Peek at the first available current measurement

        Returns:
            float: current in Amperes
        """
        return float(self._ask_channel('sens{0}:data:last?'))

    def _set_aperture(self, aperture_s: Optional[float], nplc: Optional[int]
                      ) -> None:
        if aperture_s:
            return self._write_channel(f'sens{"{0}"}:aper {aperture_s}')
        self._write_channel(f'sens{"{0}"}:nplc {nplc}')

    def _set_triggering(self) -> None:
        self._write_channel('sens{0}:trig:sour bus')
        self._write_channel('sens{0}:init')


class QDac2Channel(InstrumentChannel):

    def __init__(self, parent: 'QDac2', name: str, channum: int):
        super().__init__(parent, name)
        self._channum = channum
        self.add_parameter(
            name='measurement_range',
            label='range',
            set_cmd='sens{1}:rang {0}'.format('{}', channum),
            get_cmd=f'sens{channum}:rang?',
            vals=validators.Enum('low', 'high')
        )
        self.add_parameter(
            name='measurement_aperture_s',
            label='aperture',
            unit='s',
            set_cmd='sens{1}:aper {0}'.format('{}', channum),
            get_cmd=f'sens{channum}:aper?',
            get_parser=float
        )
        self.add_parameter(
            name='measurement_nplc',
            label='PLC',
            set_cmd='sens{1}:nplc {0}'.format('{}', channum),
            get_cmd=f'sens{channum}:nplc?',
            get_parser=int
        )
        self.add_parameter(
            name='measurement_delay_s',
            label=f'delay',
            unit='s',
            set_cmd='sens{1}:del {0}'.format('{}', channum),
            get_cmd=f'sens{channum}:del?',
            get_parser=float
        )
        self.add_function(
            name='measurement_abort',
            call_cmd=f'sens{channum}:abor'
        )
        self.add_parameter(
            name='measurement_count',
            label='count',
            set_cmd='sens{1}:coun {0}'.format('{}', channum),
            get_cmd=f'sens{channum}:coun?',
            get_parser=int
        )
        self.add_parameter(
            name='n_masurements_remaining',
            label='remaning',
            get_cmd=f'sens{channum}:ncl?',
            get_parser=int
        )
        self.add_parameter(
            name='current_last_A',
            label='last',
            unit='A',
            get_cmd=f'sens{channum}:data:last?',
            get_parser=float
        )
        self.add_parameter(
            name='n_measurements_available',
            label='available',
            get_cmd=f'sens{channum}:data:poin?',
            get_parser=int
        )
        self.add_parameter(
            name='current_start_on',
            # Channel {channum} current measurement on internal trigger
            set_parser=_trigger_context_to_value,
            set_cmd='sens{1}:trig:sour int{0}'.format('{}', channum),
        )
        self.add_parameter(
            name='measurement_start_on_external',
            # Channel {channum} current measurement on external input
            set_cmd='sens{1}:trig:sour ext{0}'.format('{}', channum),
        )
        self.add_parameter(
            name='output_range',
            label='range',
            set_cmd='sour{1}:rang {0}'.format('{}', channum),
            get_cmd=f'sour{channum}:rang?',
            vals=validators.Enum('low', 'high')
        )
        self.add_parameter(
            name='output_low_range_minimum_V',
            label='low range min',
            unit='V',
            get_cmd=f'sour{channum}:rang:low:min?',
            get_parser=float
        )
        self.add_parameter(
            name='output_low_range_maximum_V',
            label='low voltage max',
            unit='V',
            get_cmd=f'sour{channum}:rang:low:max?',
            get_parser=float
        )
        self.add_parameter(
            name='output_high_range_minimum_V',
            label='high voltage min',
            unit='V',
            get_cmd=f'sour{channum}:rang:high:min?',
            get_parser=float
        )
        self.add_parameter(
            name='output_high_range_maximum_V',
            label='high voltage max',
            unit='V',
            get_cmd=f'sour{channum}:rang:high:max?',
            get_parser=float
        )
        self.add_parameter(
            name='output_filter',
            label=f'low-pass cut-off',
            unit='Hz',
            set_cmd='sour{1}:filt {0}'.format('{}', channum),
            get_cmd=f'sour{channum}:filt?',
            get_parser=str,
            vals=validators.Enum('dc', 'med', 'high')
        )
        self.add_parameter(
            name='dc_constant_V',
            label=f'ch{channum}',
            unit='V',
            set_cmd=self._set_fixed_voltage_immediately,
            get_cmd=f'sour{channum}:volt?',
            get_parser=float,
            vals=validators.Numbers(-10.0, 10.0)
        )
        self.add_parameter(
            name='dc_last_V',
            label=f'ch{channum}',
            unit='V',
            get_cmd=f'sour{channum}:volt:last?',
            get_parser=float
        )
        self.add_parameter(
            name='dc_next_V',
            label=f'ch{channum}',
            unit='V',
            set_cmd='sour{1}:volt:trig {0}'.format('{}', channum),
            get_cmd=f'sour{channum}:volt:trig?',
            get_parser=float
        )
        self.add_parameter(
            name='dc_slew_rate_V_per_s',
            label=f'ch{channum}',
            unit='V/s',
            set_cmd='sour{1}:volt:slew {0}'.format('{}', channum),
            get_cmd=f'sour{channum}:volt:slew?',
            get_parser=float
        )
        self.add_parameter(
            name='read_current_A',
            # Perform immediate current measurement on channel
            label=f'ch{channum}',
            unit='A',
            get_cmd=f'read{channum}?',
            get_parser=comma_sequence_to_list_of_floats
        )
        self.add_parameter(
            name='fetch_current_A',
            # Retrieve all available current measurements on channel
            label=f'ch{channum}',
            unit='A',
            get_cmd=f'fetc{channum}?',
            get_parser=comma_sequence_to_list_of_floats
        )
        self.add_parameter(
            name='dc_mode',
            label=f'DC mode',
            set_cmd='sour{1}:volt:mode {0}'.format('{}', channum),
            get_cmd=f'sour{channum}:volt:mode?',
            vals=validators.Enum('fixed', 'list', 'sweep')
        )
        self.add_function(
            name='dc_initiate',
            call_cmd=f'sour{channum}:dc:init'
        )
        self.add_function(
            name='dc_abort',
            call_cmd=f'sour{channum}:dc:abor'
        )
        self.add_function(
            name='abort',
            call_cmd=f'sour{channum}:all:abor'
        )

    @property
    def number(self) -> int:
        """Channel number"""
        return self._channum

    def clear_measurements(self) -> Sequence[float]:
        """Retrieve current measurements

        The available measurements will be removed from measurement queue.

        Returns:
            Sequence[float]: list of available current measurements
        """
        # Bug circumvention
        if int(self.ask_channel('sens{0}:data:poin?')) == 0:
            return list()
        return comma_sequence_to_list_of_floats(
            self.ask_channel('sens{0}:data:rem?'))

    def measurement(self, delay_s: float = 0.0, repetitions: int = 1,
                    current_range: str = 'high',
                    aperture_s: Optional[float] = None,
                    nplc: Optional[int] = None
                    ) -> Measurement_Context:
        """Set up a sequence of current measurements

        Args:
            delay_s (float, optional): Seconds to delay the actual measurement after trigger (default 0)
            repetitions (int, optional): Number of consecutive measurements (default 1)
            current_range (str, optional): high (10mA, default) or low (200nA)
            nplc (None, optional): Integration time in power-line cycles (default 1)
            aperture_s (None, optional): Seconds of integration time instead of NPLC

        Returns:
            Measurement_Context: context manager

        Raises:
            ValueError: configuration error
        """
        if aperture_s and nplc:
            raise ValueError('Only one of nplc or aperture_s can be '
                             'specified for a current measurement')
        if not aperture_s and not nplc:
            nplc = 1
        return Measurement_Context(self, delay_s, repetitions, current_range,
                                   aperture_s, nplc)

    def output_mode(self, range: str = 'high', filter: str = 'high') -> None:
        """Set the output voltage

        Args:
            range (str, optional): Low or high (default) current range
            filter (str, optional): DC (10Hz), medium (10kHz) or high (300kHz, default) voltage filter
        """
        self.output_range(range)
        self.output_filter(filter)

    def dc_list(self, voltages: Sequence[float], repetitions: int = 1,
                dwell_s: float = 1e-03, delay_s: float = 0,
                backwards: bool = False, stepped: bool = False
                ) -> List_Context:
        """Set up a DC-list generator

        Args:
            voltages (Sequence[float]): Voltages in list
            repetitions (int, optional): Number of repetitions of the list (default 1)
            dwell_s (float, optional): Seconds between each voltage (default 1ms)
            delay_s (float, optional): Seconds of delay after receiving a trigger (default 0)
            backwards (bool, optional): Use list in reverse (default is forward)
            stepped (bool, optional): True means that each step needs to be triggered (default False)

        Returns:
            List_Context: context manager
        """
        return List_Context(self, voltages, repetitions, dwell_s, delay_s,
                            backwards, stepped)

    def dc_sweep(self, start_V: float, stop_V: float, points: int,
                 repetitions: int = 1, dwell_s: float = 1e-03,
                 delay_s: float = 0, backwards=False, stepped=True
                 ) -> Sweep_Context:
        """Set up a DC sweep

        Args:
            start_V (float): Start voltage
            stop_V (float): Send voltage
            points (int): Number of steps
            repetitions (int, optional): Number of repetition (default 1)
            dwell_s (float, optional): Seconds between each voltage (default 1ms)
            delay_s (float, optional): Seconds of delay after receiving a trigger (default 0)
            backwards (bool, optional): Sweep in reverse (default is forward)
            stepped (bool, optional): True means that each step needs to be triggered (default False)

        Returns:
            Sweep_Context: context manager
        """
        return Sweep_Context(self, start_V, stop_V, points, repetitions,
                             dwell_s, delay_s, backwards, stepped)

    def square_wave(self, frequency_Hz: Optional[float] = None,
                    period_s: Optional[float] = None, repetitions: int = -1,
                    duty_cycle_percent: float = 50.0, kind: str = 'symmetric',
                    inverted: bool = False, span_V: float = 0.2,
                    offset_V: float = 0.0, delay_s: float = 0,
                    slew_V_s: Optional[float] = None
                    ) -> Square_Context:
        """Set up a square-wave generator

        Args:
            frequency_Hz (float, optional): Frequency
            period_s (float, optional): Period length (instead of frequency)
            repetitions (int, optional): Number of repetition (default infinite)
            duty_cycle_percent (float, optional): Percentage on-time (default 50%)
            kind (str, optional): Positive, negative or symmetric (default) around the offset
            inverted (bool, optional): True means flipped (default False)
            span_V (float, optional): Voltage span (default 200mV)
            offset_V (float, optional): Offset (default 0V)
            delay_s (float, optional): Seconds of delay after receiving a trigger (default 0)
            slew_V_s (float, optional): Max slew rate in V/s (default None)

        Returns:
            Square_Context: context manager

        Raises:
            ValueError: configuration error
        """
        if frequency_Hz and period_s:
            raise ValueError(error_ambiguous_wave)
        if not frequency_Hz and not period_s:
            frequency_Hz = 1000
        return Square_Context(self, frequency_Hz, repetitions, period_s,
                              duty_cycle_percent, kind, inverted, span_V,
                              offset_V, delay_s, slew_V_s)

    def sine_wave(self, frequency_Hz: Optional[float] = None,
                  period_s: Optional[float] = None, repetitions: int = -1,
                  inverted: bool = False, span_V: float = 0.2,
                  offset_V: float = 0.0, delay_s: float = 0,
                  slew_V_s: Optional[float] = None
                  ) -> Sine_Context:
        """Set up a sine-wave generator

        Args:
            frequency_Hz (float, optional): Frequency
            period_s (float, optional): Period length (instead of frequency)
            repetitions (int, optional): Number of repetition (default infinite)
            inverted (bool, optional): True means flipped (default False)
            span_V (float, optional): Voltage span (default 200mV)
            offset_V (float, optional): Offset (default 0V)
            delay_s (float, optional): Seconds of delay after receiving a trigger (default 0)
            slew_V_s (None, optional): Max slew rate in V/s (default None)

        Returns:
            Sine_Context: context manager

        Raises:
            ValueError: configuration error
        """
        if frequency_Hz and period_s:
            raise ValueError(error_ambiguous_wave)
        if not frequency_Hz and not period_s:
            frequency_Hz = 1000
        return Sine_Context(self, frequency_Hz, repetitions, period_s,
                            inverted, span_V, offset_V, delay_s, slew_V_s)

    def triangle_wave(self, frequency_Hz: Optional[float] = None,
                      period_s: Optional[float] = None, repetitions: int = -1,
                      duty_cycle_percent: float = 50.0, inverted: bool = False,
                      span_V: float = 0.2, offset_V: float = 0.0,
                      delay_s: float = 0, slew_V_s: Optional[float] = None
                      ) -> Triangle_Context:
        """Set up a triangle-wave generator

        Args:
            frequency_Hz (float, optional): Frequency
            period_s (float, optional): Period length (instead of frequency)
            repetitions (int, optional): Number of repetition (default infinite)
            duty_cycle_percent (float, optional): Percentage on-time (default 50%)
            inverted (bool, optional): True means flipped (default False)
            span_V (float, optional): Voltage span (default 200mV)
            offset_V (float, optional): Offset (default 0V)
            delay_s (float, optional): Seconds of delay after receiving a trigger (default 0)
            slew_V_s (float, optional): Max slew rate in V/s (default None)

        Returns:
            Triangle_Context: context manager

        Raises:
            ValueError: configuration error
        """
        if frequency_Hz and period_s:
            raise ValueError(error_ambiguous_wave)
        if not frequency_Hz and not period_s:
            frequency_Hz = 1000
        return Triangle_Context(self, frequency_Hz, repetitions, period_s,
                                duty_cycle_percent, inverted, span_V,
                                offset_V, delay_s, slew_V_s)

    def arbitrary_wave(self, trace_name: str, repetitions: int = 1,
                       scale: float = 1.0, offset_V: float = 0.0,
                       slew_V_s: Optional[float] = None
                       ) -> Awg_Context:
        """Set up an arbitrary-wave generator

        Args:
            trace_name (str): Use data from this named trace
            repetitions (int, optional): Number of repetition (default 1)
            scale (float, optional): Scaling factor of voltages (default 1)
            offset_V (float, optional): Offset (default 0V)
            slew_V_s (None, optional): Max slew rate in V/s (default None)

        Returns:
            Awg_Context: context manager
        """
        return Awg_Context(self, trace_name, repetitions, scale, offset_V,
                           slew_V_s)

    def _set_fixed_voltage_immediately(self, v) -> None:
        self.write(f'sour{self._channum}:volt:mode fix')
        self.write(f'sour{self._channum}:volt {v}')

    def ask_channel(self, cmd: str) -> str:
        """Inject channel number into SCPI query

        Arguments:
            cmd (str): Must contain a '{0}' placeholder for the channel number

        Returns:
            str: SCPI answer
        """
        return self.ask(self._channel_message(cmd))

    def write_channel(self, cmd: str) -> None:
        """Inject channel number into SCPI command

        Arguments:
            cmd (str): Must contain a '{0}' placeholder for the channel number
        """
        self.write(self._channel_message(cmd))

    def write_channel_floats(self, cmd: str, values: Sequence[float]) -> None:
        """Inject channel number and a list of values into SCPI command

        The values are appended to the end of the command.

        Arguments:
            cmd (str): Must contain a '{0}' placeholder for channel number
            values (Sequence[float]): Sequence of numbers
        """
        self._parent.write_floats(self._channel_message(cmd), values)

    def write(self, cmd: str) -> None:
        """Send a SCPI command

        Args:
            cmd (str): SCPI command
        """
        self._parent.write(cmd)

    def _channel_message(self, template: str):
        return template.format(self._channum)


class Trace_Context:

    def __init__(self, parent, name: str, size: int):
        self._parent = parent
        self._size = size
        self._name = name
        self._parent.write(f'trac:def "{name}",{size}')

    def __len__(self):
        return self.size

    @property
    def size(self) -> int:
        """Number of values in trace"""
        return self._size

    @property
    def name(self) -> str:
        """Name of trace"""
        return self._name

    def waveform(self, values: Sequence[float]) -> None:
        """Fill values into trace

        Args:
            values (Sequence[float]): Sequence of values

        Raises:
            ValueError: size mismatch
        """
        if len(values) != self.size:
            raise ValueError(f'trace length {len(values)} does not match '
                             f'allocated length {self.size}')
        self._parent.write_floats(f'trac:data "{self.name}",', values)


class Virtual_Sweep_Context:

    def __init__(self, arrangement: 'Arrangement_Context', sweep: np.ndarray,
                 start_trigger: Optional[str], step_time_s: float,
                 step_trigger: Optional[str], repetitions: Optional[int]):
        self._arrangement = arrangement
        self._sweep = sweep
        self._step_trigger = step_trigger
        self._step_time_s = step_time_s
        self._repetitions = repetitions
        self._allocate_triggers(start_trigger)
        self._qdac_ready = False

    def __enter__(self):
        self._ensure_qdac_setup()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Let Arrangement take care of freeing triggers
        return False

    def actual_values_V(self, contact: str) -> np.ndarray:
        """The corrected values that would actually be sent to the contact

        Args:
            contact (str): Name of contact

        Returns:
            np.ndarray: Corrected voltages
        """
        index = self._arrangement._contact_index(contact)
        return self._sweep[:, index]

    def start(self) -> None:
        """Start the 2D sweep
        """
        self._ensure_qdac_setup()
        trigger = self._arrangement.get_trigger_by_name(self._start_trigger_name)
        self._arrangement._qdac.trigger(trigger)

    def _allocate_triggers(self, start_sweep: Optional[str]) -> None:
        if not start_sweep:
            # Use a random, unique name
            start_sweep = uuid.uuid4().hex
        self._arrangement._allocate_internal_triggers([start_sweep])
        self._start_trigger_name = start_sweep

    def _ensure_qdac_setup(self) -> None:
        if self._qdac_ready:
            return self._make_ready_to_start()
        self._route_inner_trigger()
        self._send_lists_to_qdac()
        self._qdac_ready = True

    def _route_inner_trigger(self) -> None:
        if not self._step_trigger:
            return
        trigger = self._arrangement.get_trigger_by_name(self._step_trigger)
        # All channels change in sync, so just use the first channel to make the
        # external trigger.
        channel = self._get_channel(0)
        channel.write_channel(f'sour{"{0}"}:dc:mark:sst '
                              f'{_trigger_context_to_value(trigger)}')

    def _get_channel(self, contact_index: int) -> 'QDac2Channel':
        channel_number = self._arrangement._channels[contact_index]
        qdac = self._arrangement._qdac
        return qdac.channel(channel_number)

    def _send_lists_to_qdac(self) -> None:
        for contact_index in range(self._arrangement.shape):
            self._send_list_to_qdac(contact_index, self._sweep[:, contact_index])

    def _send_list_to_qdac(self, contact_index, voltages):
        channel = self._get_channel(contact_index)
        dc_list = channel.dc_list(voltages=voltages, dwell_s=self._step_time_s,
                                  repetitions=self._repetitions)
        trigger = self._arrangement.get_trigger_by_name(self._start_trigger_name)
        dc_list.start_on(trigger)

    def _make_ready_to_start(self):  # Bug circumvention
        for contact_index in range(self._arrangement.shape):
            channel = self._get_channel(contact_index)
            channel.write_channel('sour{0}:dc:init')


class Arrangement_Context:
    def __init__(self, qdac: 'QDac2', contacts: Dict[str, int],
                 output_triggers: Optional[Dict[str, int]],
                 internal_triggers: Optional[Sequence[str]],
                 outer_trigger_channel: Optional[int]):
        self._qdac = qdac
        self._fix_contact_order(contacts)
        self._allocate_triggers(internal_triggers, output_triggers)
        self._outer_trigger_channel = outer_trigger_channel
        self._correction = np.identity(self.shape)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._free_triggers()
        return False

    @property
    def shape(self) -> int:
        """Number of contacts in the arrangement"""
        return len(self._contacts)

    @property
    def correction_matrix(self) -> np.ndarray:
        """Correction matrix"""
        return self._correction

    @property
    def contact_names(self) -> Sequence[str]:
        """
        Returns:
            Sequence[str]: Contact names in the same order as channel_numbers
        """
        return self._contact_names

    def _allocate_internal_triggers(self,
                                    internal_triggers: Optional[Sequence[str]]
                                    ) -> None:
        if not internal_triggers:
            return
        for name in internal_triggers:
            self._internal_triggers[name] = self._qdac.allocate_trigger()

    def initiate_correction(self, contact: str, factors: Sequence[float]) -> None:
        """Override how much a particular contact influences the other contacts

        Args:
            contact (str): Name of contact
            factors (Sequence[float]): factors between -1.0 and 1.0
        """
        index = self._contact_index(contact)
        self._correction[index] = factors

    def set_virtual_voltage(self, contact: str, voltage: float) -> None:
        """Set virtual voltage on specific contact

        The actual voltage that the contact will receive depends on the
        correction matrix.

        Args:
            contact (str): Name of contact
            voltage (float): Voltage corresponding to no correction
        """
        try:
            index = self._contact_index(contact)
        except KeyError:
            raise ValueError(f'No contact named "{contact}"')
        self._effectuate_virtual_voltage(index, voltage)

    def set_virtual_voltages(self, contacts_to_voltages: Dict[str, float]) -> None:
        """Set virtual voltages on specific contacts in one go

        The actual voltage that each contact will receive depends on the
        correction matrix.

        Args:
            contact_to_voltages (Dict[str,float]): contact to voltage map
        """
        for contact, voltage in contacts_to_voltages.items():
            try:
                index = self._contact_index(contact)
            except KeyError:
                raise ValueError(f'No contact named "{contact}"')
            self._virtual_voltages[index] = voltage
        self._effectuate_virtual_voltages()

    def _effectuate_virtual_voltage(self, index: int, voltage: float) -> None:
        self._virtual_voltages[index] = voltage
        self._effectuate_virtual_voltages()

    def _effectuate_virtual_voltages(self) -> None:
        for index, channel_number in enumerate(self._channels):
            actual_V = self.actual_voltages()[index]
            self._qdac.channel(channel_number).dc_constant_V(actual_V)

    def add_correction(self, contact: str, factors: Sequence[float]) -> None:
        """Update how much a particular contact influences the other contacts

        This is mostly useful in arrangements where each contact has significant
        effect only on nearby contacts, and thus can be added incrementally.

        The factors are extended by the identity matrix and multiplied to the
        correction matrix.

        Args:
            contact (str): Name of contact
            factors (Sequence[float]): factors usually between -1.0 and 1.0
        """
        index = self._contact_index(contact)
        multiplier = np.identity(self.shape)
        multiplier[index] = factors
        self._correction = np.matmul(multiplier, self._correction)

    def _fix_contact_order(self, contacts: Dict[str, int]) -> None:
        self._contact_names = list()
        self._contacts = dict()
        self._channels = list()
        index = 0
        for contact, channel in contacts.items():
            self._contact_names.append(contact)
            self._contacts[contact] = index
            index += 1
            self._channels.append(channel)
        self._virtual_voltages = np.zeros(self.shape)

    @property
    def channel_numbers(self) -> Sequence[int]:
        """
        Returns:
            Sequence[int]: Channels numbers in the same order as contact_names
        """
        return self._channels

    def channel(self, name: str) -> QDac2Channel:
        return self._qdac.channel(self._channels[self._contacts[name]])

    def virtual_voltage(self, contact: str) -> float:
        """
        Args:
            contact (str): Name of contact

        Returns:
            float: Voltage before correction
        """
        index = self._contact_index(contact)
        return self._virtual_voltages[index]

    def actual_voltages(self) -> Sequence[float]:
        """
        Returns:
            Sequence[float]: Corrected voltages for all contacts
        """
        vs = np.matmul(self._correction, self._virtual_voltages)
        if self._qdac._round_off:
            vs = np.round(vs, self._qdac._round_off)
        return list(vs)

    def get_trigger_by_name(self, name: str) -> QDac2Trigger_Context:
        """
        Args:
            name (str): Name of trigger

        Returns:
            QDac2Trigger_Context: Trigger context manager
        """
        try:
            return self._internal_triggers[name]
        except KeyError:
            print(f'Internal triggers: {list(self._internal_triggers.keys())}')
            raise

    def _all_channels_as_suffix(self) -> str:
        channels_str = ints_to_comma_separated_list(self.channel_numbers)
        return f'(@{channels_str})'

    def currents_A(self, nplc: int = 1, current_range: str = "low") -> Sequence[float]:
        """Measure currents on all contacts

        Args:
            nplc (int, optional): Number of powerline cycles to average over
            current_range (str, optional): Current range (default low)
        """
        channels_suffix = self._all_channels_as_suffix()
        self._qdac.write(f'sens:rang {current_range},{channels_suffix}')
        # Wait for relays to finish switching by doing a query
        self._qdac.ask(f'*stb?')
        self._qdac.write(f'sens:nplc {nplc},{channels_suffix}')
        # Wait for the current sensors to stabilize and then read
        slowest_line_freq_Hz = 50
        sleep_s((nplc + 1) / slowest_line_freq_Hz)
        currents = self._qdac.ask(f'read? {channels_suffix}')
        return comma_sequence_to_list_of_floats(currents)

    def virtual_sweep(self, contact: str, voltages: Sequence[float],
                      start_sweep_trigger: Optional[str] = None,
                      step_time_s: float = 1e-5,
                      step_trigger: Optional[str] = None,
                      repetitions: int = 1) -> Virtual_Sweep_Context:
        """Sweep a contact to create a 1D sweep

        Args:
            contact (str): Name of sweeping contact
            voltages (Sequence[float]): Virtual sweep voltages
            outer_contact (str): Name of slow-changing (outer) contact
            start_sweep_trigger (None, optional): Trigger that starts sweep
            step_time_s (float, optional): Delay between voltage changes
            step_trigger (None, optional): Trigger that marks each step
            repetitions (int, Optional): Number of back-and-forth sweeps, or -1 for infinite

        Returns:
            Virtual_Sweep_Context: context manager
        """
        sweep = self._calculate_1d_values(contact, voltages)
        return Virtual_Sweep_Context(self, sweep, start_sweep_trigger,
                                     step_time_s, step_trigger, repetitions)

    def _calculate_1d_values(self, contact: str, voltages: Sequence[float]
                             ) -> np.ndarray:
        original_voltage = self.virtual_voltage(contact)
        index = self._contact_index(contact)
        sweep = list()
        for v in voltages:
            self._virtual_voltages[index] = v
            sweep.append(self.actual_voltages())
        self._virtual_voltages[index] = original_voltage
        return np.array(sweep)

    def virtual_sweep2d(self, inner_contact: str, inner_voltages: Sequence[float],
                        outer_contact: str, outer_voltages: Sequence[float],
                        start_sweep_trigger: Optional[str] = None,
                        inner_step_time_s: float = 1e-5,
                        inner_step_trigger: Optional[str] = None,
                        outer_step_trigger: Optional[str] = None,
                        repetitions: int = 1) -> Virtual_Sweep_Context:
        """Sweep two contacts to create a 2D sweep

        Args:
            inner_contact (str): Name of fast-changing (inner) contact
            inner_voltages (Sequence[float]): Inner contact virtual voltages
            outer_contact (str): Name of slow-changing (outer) contact
            outer_voltages (Sequence[float]): Outer contact virtual voltages
            start_sweep_trigger (None, optional): Trigger that starts sweep
            inner_step_time_s (float, optional): Delay between voltage changes
            inner_step_trigger (None, optional): Trigger that marks each step
            outer_step_trigger (None, optional): Name of trigger that marks outer step
            repetitions (int, Optional): Number of back-and-forth sweeps, or -1 for infinite

        Returns:
            Virtual_Sweep_Context: context manager
        """
        if not start_sweep_trigger:
            # Use a random, unique name
            start_sweep_trigger = uuid.uuid4().hex
        sweep = self._calculate_2d_values(inner_contact, inner_voltages,
                                          outer_contact, outer_voltages)
        ctx = Virtual_Sweep_Context(self, sweep, start_sweep_trigger,
                                    inner_step_time_s, inner_step_trigger,
                                    repetitions)
        if outer_step_trigger:
            self._setup_outer_trigger(outer_step_trigger, start_sweep_trigger,
                                      len(inner_voltages)*inner_step_time_s,
                                      len(outer_voltages))
        return ctx

    def _setup_outer_trigger(self, outer_step_trigger: str,
                             start_sweep_trigger: str,
                             period_s: float, outer_cycles: int) -> None:
        if not self._outer_trigger_channel:
            raise ValueError("Arrangement needs an outer_trigger_channel when"
                             " using outer_step_trigger")
            return
        helper_ch = self._qdac.channel(self._outer_trigger_channel)
        helper_ctx = helper_ch.sine_wave(
            period_s=period_s, repetitions=outer_cycles, span_V=0)
        helper_ctx.start_on(self.get_trigger_by_name(start_sweep_trigger))
        trigger = self.get_trigger_by_name(outer_step_trigger)
        helper_ctx._marker_period_start = trigger
        helper_ctx.period_start_marker()
        self._outer_trigger_context = helper_ctx

    def _calculate_2d_values(self, inner_contact: str,
                             inner_voltages: Sequence[float],
                             outer_contact: str,
                             outer_voltages: Sequence[float]) -> np.ndarray:
        original_fast_voltage = self.virtual_voltage(inner_contact)
        original_slow_voltage = self.virtual_voltage(outer_contact)
        outer_index = self._contact_index(outer_contact)
        inner_index = self._contact_index(inner_contact)
        sweep = list()
        for slow_V in outer_voltages:
            self._virtual_voltages[outer_index] = slow_V
            for fast_V in inner_voltages:
                self._virtual_voltages[inner_index] = fast_V
                sweep.append(self.actual_voltages())
        self._virtual_voltages[inner_index] = original_fast_voltage
        self._virtual_voltages[outer_index] = original_slow_voltage
        return np.array(sweep)

    def virtual_detune(self, contacts: Sequence[str], start_V: Sequence[float],
                       end_V: Sequence[float], steps: int,
                       start_trigger: Optional[str] = None,
                       step_time_s: float = 1e-5,
                       step_trigger: Optional[str] = None,
                       repetitions: int = 1) -> Virtual_Sweep_Context:
        """Sweep any number of contacts linearly from one set of values to another set of values

        Args:
            contacts (Sequence[str]): contacts involved in sweep
            start_V (Sequence[float]): First-extreme values
            end_V (Sequence[float]): Second-extreme values
            steps (int): Number of steps between extremes
            start_trigger (None, optional): Trigger that starts sweep
            step_time_s (float, Optional): Seconds between each step
            step_trigger (None, optional): Trigger that marks each step
            repetitions (int, Optional): Number of back-and-forth sweeps, or -1 for infinite
        """
        self._check_same_lengths(contacts, start_V, end_V)
        sweep = self._calculate_detune_values(contacts, start_V, end_V, steps)
        return Virtual_Sweep_Context(self, sweep, start_trigger, step_time_s,
                                     step_trigger, repetitions)

    @staticmethod
    def _check_same_lengths(contacts, start_V, end_V) -> None:
        n_contacts = len(contacts)
        if n_contacts != len(start_V):
            raise ValueError(f'There must be exactly one voltage per contact: {start_V}')
        if n_contacts != len(end_V):
            raise ValueError(f'There must be exactly one voltage per contact: {end_V}')

    def _calculate_detune_values(self, contacts: Sequence[str], start_V: Sequence[float],
                                 end_V: Sequence[float], steps: int):
        original_voltages = [self.virtual_voltage(contact) for contact in contacts]
        indices = [self._contact_index(contact) for contact in contacts]
        sweep = list()
        forward_V = [forward_and_back(start_V[i], end_V[i], steps) for i in range(len(contacts))]
        for voltages in zip(*forward_V):
            for index, voltage in zip(indices, voltages):
                self._virtual_voltages[index] = voltage
            sweep.append(self.actual_voltages())
        for index, voltage in zip(indices, original_voltages):
            self._virtual_voltages[index] = voltage
        return np.array(sweep)

    def leakage(self, modulation_V: float, nplc: int = 2) -> np.ndarray:
        """Run a simple leakage test between the contacts

        Each contact is changed in turn and the resulting change in current from
        steady-state is recorded.  The resulting resistance matrix is calculated
        as modulation_voltage divided by current_change.

        Args:
            modulation_V (float): Virtual voltage added to each contact
            nplc (int, Optional): Powerline cycles to wait for each measurement

        Returns:
            ndarray: contact-to-contact resistance in Ohms
        """
        steady_state_A, currents_matrix = self._leakage_currents(modulation_V, nplc, 'low')
        with np.errstate(divide='ignore'):
            return np.abs(modulation_V / diff_matrix(steady_state_A, currents_matrix))

    def _leakage_currents(self, modulation_V: float, nplc: int,
                          current_range: str
                          ) -> Tuple[Sequence[float], Sequence[Sequence[float]]]:
        steady_state_A = self.currents_A(nplc, 'low')
        currents_matrix = list()
        for index, channel_nr in enumerate(self.channel_numbers):
            original_V = self._virtual_voltages[index]
            self._effectuate_virtual_voltage(index, original_V + modulation_V)
            currents = self.currents_A(nplc, current_range)
            self._effectuate_virtual_voltage(index, original_V)
            currents_matrix.append(currents)
        return steady_state_A, currents_matrix

    def _contact_index(self, contact: str) -> int:
        return self._contacts[contact]

    def _allocate_triggers(self, internal_triggers: Optional[Sequence[str]],
                           output_triggers: Optional[Dict[str, int]]
                           ) -> None:
        self._internal_triggers: Dict[str, QDac2Trigger_Context] = dict()
        self._allocate_internal_triggers(internal_triggers)
        self._allocate_external_triggers(output_triggers)

    def _allocate_external_triggers(self, output_triggers:
                                    Optional[Dict[str, int]]
                                    ) -> None:
        self._external_triggers = dict()
        if not output_triggers:
            return
        for name, port in output_triggers.items():
            self._external_triggers[name] = port
            trigger = self._qdac.allocate_trigger()
            self._qdac.connect_external_trigger(port, trigger)
            self._internal_triggers[name] = trigger

    def _free_triggers(self) -> None:
        for trigger in self._internal_triggers.values():
            self._qdac.free_trigger(trigger)


def forward_and_back(start: float, end: float, steps: int):
    forward = np.linspace(start, end, steps)
    backward = np.flip(forward)[1:][:-1]
    back_and_forth = itertools.chain(forward, backward)
    return back_and_forth


class QDac2(VisaInstrument):

    def __init__(self, name: str, address: str, **kwargs) -> None:
        """Connect to a QDAC-II

        Args:
            name (str): Name for instrument
            address (str): Visa identification string
            **kwargs: additional argument to the Visa driver
        """
        self._check_instrument_name(name)
        super().__init__(name, address, terminator='\n', **kwargs)
        self._set_up_serial()
        self._set_up_debug_settings()
        self._set_up_channels()
        self._set_up_external_triggers()
        self._set_up_internal_triggers()
        self._set_up_simple_functions()
        self.connect_message()
        self._check_for_wrong_model()
        self._check_for_incompatiable_firmware()
        self._set_up_manual_triggers()

    def n_channels(self) -> int:
        """
        Returns:
            int: Number of channels
        """
        return len(self.submodules['channels'])

    def channel(self, ch: int) -> QDac2Channel:
        """
        Args:
            ch (int): Channel number

        Returns:
            QDac2Channel: Visa representation of the channel
        """
        return getattr(self, f'ch{ch:02}')

    @staticmethod
    def n_triggers() -> int:
        """
        Returns:
            int: Number of internal triggers
        """
        return 14

    @staticmethod
    def n_external_inputs() -> int:
        """
        Returns:
            int: Number of external input triggers
        """
        return 4

    def n_external_outputs(self) -> int:
        """
        Returns:
            int: Number of external output triggers
        """
        return len(self.submodules['external_triggers'])

    def allocate_trigger(self) -> QDac2Trigger_Context:
        """Allocate an internal trigger

        Does not have any effect on the instrument, only the driver.

        Returns:
            QDac2Trigger_Context: Context manager

        Raises:
            ValueError: no free triggers
        """
        try:
            number = self._internal_triggers.pop()
        except KeyError:
            raise ValueError('no free internal triggers')
        return QDac2Trigger_Context(self, number)

    def free_trigger(self, trigger: QDac2Trigger_Context) -> None:
        """Free an internal trigger

        Does not have any effect on the instrument, only the driver.

        Args:
            trigger (QDac2Trigger_Context): trigger to free
        """
        internal = _trigger_context_to_value(trigger)
        self._internal_triggers.add(internal)

    def free_all_triggers(self) -> None:
        """Free all an internal triggers

        Does not have any effect on the instrument, only the driver.
        """
        self._set_up_internal_triggers()

    def connect_external_trigger(self, port: int, trigger: QDac2Trigger_Context,
                                 width_s: float = 1e-6
                                 ) -> None:
        """Route internal trigger to external trigger

        Args:
            port (int): External output trigger number
            trigger (QDac2Trigger_Context): Internal trigger
            width_s (float, optional): Output trigger width in seconds (default 1ms)
        """
        internal = _trigger_context_to_value(trigger)
        self.write(f'outp:trig{port}:sour int{internal}')
        self.write(f'outp:trig{port}:widt {width_s}')

    def reset(self) -> None:
        self.write('*rst')
        sleep_s(5)

    def errors(self) -> str:
        """Retrieve and clear all previous errors

        Returns:
            str: Comma separated list of errors or '0, "No error"'
        """
        return self.ask('syst:err:all?')

    def error(self) -> str:
        """Retrieve next error

        Returns:
            str: The next error or '0, "No error"'
        """
        return self.ask('syst:err?')

    def n_errors(self) -> int:
        """Peek at number of previous errors

        Returns:
            int: Number of errors
        """
        return int(self.ask('syst:err:coun?'))

    def start_all(self) -> None:
        """Trigger the global SCPI bus (``*TRG``)

        All generators, that have not been explicitly set to trigger on an
        internal or external trigger, will be started.
        """
        self.write('*trg')

    def remove_traces(self) -> None:
        """Delete all trace definitions from the instrument

        This means that all AWGs loose their data.
        """
        self.write('trac:rem:all')

    def traces(self) -> Sequence[str]:
        """List all defined traces

        Returns:
            Sequence[str]: trace names
        """
        return comma_sequence_to_list(self.ask('trac:cat?'))

    def allocate_trace(self, name: str, size: int) -> Trace_Context:
        """Reserve memory for a new trace

        Args:
            name (str): Name of new trace
            size (int): Number of voltage values in the trace

        Returns:
            Trace_Context: context manager
        """
        return Trace_Context(self, name, size)

    def mac(self) -> str:
        """
        Returns:
            str: Media Access Control (MAC) address of the instrument
        """
        mac = self.ask('syst:comm:lan:mac?')
        return f'{mac[1:3]}-{mac[3:5]}-{mac[5:7]}-{mac[7:9]}-{mac[9:11]}' \
               f'-{mac[11:13]}'

    def arrange(self, contacts: Dict[str, int],
                output_triggers: Optional[Dict[str, int]] = None,
                internal_triggers: Optional[Sequence[str]] = None,
                outer_trigger_channel: Optional[int] = None
                ) -> Arrangement_Context:
        """An arrangement of contacts and triggers for virtual gates

        Each contact corresponds to a particular output channel.  Each
        output_trigger corresponds to a particular external output trigger.
        Each internal_trigger will be allocated from the pool of internal
        triggers, and can later be used for synchronisation.  After
        initialisation of the arrangement, contacts and triggers can only be
        referred to by name.

        The voltages that will appear on each contact depends not only on the
        specified virtual voltage, but also on a correction matrix.  Initially,
        the contacts are assumed to not influence each other, which means that
        the correction matrix is the identity matrix, ie. the row for
        each contact has a value of [0, ..., 0, 1, 0, ..., 0].

        Args:
            contacts (Dict[str, int]): Name/channel pairs
            output_triggers (Sequence[Tuple[str,int]], optional): Name/number pairs of output triggers
            internal_triggers (Sequence[str], optional): List of names of internal triggers to allocate
            outer_trigger_channel (int, optional): Additional channel if outer trigger is needed

        Returns:
            Arrangement_Context: context manager
        """
        return Arrangement_Context(self, contacts, output_triggers,
                                   internal_triggers, outer_trigger_channel)

    # -----------------------------------------------------------------------
    # Instrument-wide functions
    # -----------------------------------------------------------------------

    # -----------------------------------------------------------------------
    # Debugging and testing

    def start_recording_scpi(self) -> None:
        """Record all SCPI commands sent to the instrument

        Any previous recordings are removed.  To inspect the SCPI commands sent
        to the instrument, call get_recorded_scpi_commands().
        """
        self._scpi_sent: List[str] = list()
        self._record_commands = True

    def get_recorded_scpi_commands(self) -> List[str]:
        """
        Returns:
            Sequence[str]: SCPI commands sent to the instrument
        """
        commands = self._scpi_sent
        self._scpi_sent = list()
        return commands

    def clear(self) -> None:
        """Reset the VISA message queue of the instrument
        """
        self.visa_handle.clear()

    def clear_read_queue(self) -> Sequence[str]:
        """Flush the VISA message queue of the instrument

        Takes at least _message_flush_timeout_ms to carry out.

        Returns:
            Sequence[str]: Messages lingering in queue
        """
        lingering = list()
        original_timeout = self.visa_handle.timeout
        self.visa_handle.timeout = self._message_flush_timeout_ms
        while True:
            try:
                message = self.visa_handle.read()
            except VisaIOError:
                break
            else:
                lingering.append(message)
        self.visa_handle.timeout = original_timeout
        return lingering

    # -----------------------------------------------------------------------
    # Override communication methods to make it possible to record the
    # communication with the instrument.

    def write(self, cmd: str) -> None:
        """Send SCPI command to instrument

        Args:
            cmd (str): SCPI command
        """
        if self._record_commands:
            self._scpi_sent.append(cmd)
        super().write(cmd)

    def ask(self, cmd: str) -> str:
        """Send SCPI query to instrument

        Args:
            cmd (str): SCPI query

        Returns:
            str: SCPI answer
        """
        if self._record_commands:
            self._scpi_sent.append(cmd)
        answer = super().ask(cmd)
        return answer

    def write_floats(self, cmd: str, values: Sequence[float]) -> None:
        """Append a list of values to a SCPI command

        By default, the values are IEEE binary encoded.

        Remember to include separating space in command if needed.
        """
        if self._no_binary_values:
            compiled = f'{cmd}{floats_to_comma_separated_list(values)}'
            if self._record_commands:
                self._scpi_sent.append(compiled)
            return super().write(compiled)
        if self._record_commands:
            self._scpi_sent.append(f'{cmd}{floats_to_comma_separated_list(values)}')
        self.visa_handle.write_binary_values(cmd, values)

    # -----------------------------------------------------------------------

    def _set_up_debug_settings(self) -> None:
        self._record_commands = False
        self._scpi_sent = list()
        self._message_flush_timeout_ms = 1
        self._round_off = None
        self._no_binary_values = False

    def _set_up_serial(self) -> None:
        # No harm in setting the speed even if the connection is not serial.
        self.visa_handle.baud_rate = 921600  # type: ignore

    def _check_for_wrong_model(self) -> None:
        model = self.IDN()['model']
        if model != 'QDAC-II':
            raise ValueError(f'Unknown model {model}. Are you using the right'
                             ' driver for your instrument?')

    def _check_for_incompatiable_firmware(self) -> None:
        # Only compare the firmware, not the FPGA version
        firmware = split_version_string_into_components(self.IDN()['firmware'])[1]
        least_compatible_fw = '0.17.5'
        if parse(firmware) < parse(least_compatible_fw):
            raise ValueError(f'Incompatible firmware {firmware}. You need at '
                             f'least {least_compatible_fw}')

    def _set_up_channels(self) -> None:
        channels = ChannelList(self, 'Channels', QDac2Channel,
                               snapshotable=False)
        for i in range(1, 24 + 1):
            name = f'ch{i:02}'
            channel = QDac2Channel(self, name, i)
            self.add_submodule(name, channel)
            channels.append(channel)
        channels.lock()
        self.add_submodule('channels', channels)

    def _set_up_external_triggers(self) -> None:
        triggers = ChannelList(self, 'Channels', QDac2ExternalTrigger,
                               snapshotable=False)
        for i in range(1, 5 + 1):
            name = f'ext{i}'
            trigger = QDac2ExternalTrigger(self, name, i)
            self.add_submodule(name, trigger)
            triggers.append(trigger)
        triggers.lock()
        self.add_submodule('external_triggers', triggers)

    def _set_up_internal_triggers(self) -> None:
        # A set of the available internal triggers
        self._internal_triggers = set(range(1, self.n_triggers() + 1))

    def _set_up_manual_triggers(self) -> None:
        self.add_parameter(
            name='trigger',
            # Manually trigger event
            set_parser=_trigger_context_to_value,
            set_cmd='tint {}',
        )

    def _set_up_simple_functions(self) -> None:
        self.add_function('abort', call_cmd='abor')

    def _check_instrument_name(self, name: str) -> None:
        if name.isidentifier():
            return
        raise ValueError(
            f'Instrument name "{name}" is incompatible with QCoDeS parameter '
            'generation (no spaces, punctuation, prepended numbers, etc)')
