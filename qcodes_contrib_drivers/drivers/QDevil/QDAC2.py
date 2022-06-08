import numpy as np
import uuid
from qcodes.instrument.channel import InstrumentChannel, ChannelList
from qcodes.instrument.visa import VisaInstrument
from pyvisa.errors import VisaIOError
from qcodes.utils import validators
from typing import Any, NewType, Sequence, List, Dict, Tuple, Optional
from packaging.version import parse

# Version 0.13.0
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
#    explicitly part of the function name, like above, or, if unit-less number,
#    then prefixed by n_ like
#
#        qdac.n_channels()
#
# 3. Allocation of resources should be automated as much as possible, preferably
#    by python context managers that automatically clean up on exit.  Such
#    context managers have a name with a '_Context' suffix.
#
# 4. Any generator should by default be set to start on the bus trigger
#    (*TRG) so that it is possible to synchronise several generators without
#    further setup; which also eliminates the need for special cases for the
#    bus trigger.


#
# Future improvements
# -------------------
#
# - Detect and handle mixing of internal and external triggers (_trigger).
#

error_ambiguous_wave = 'Only one of frequency_Hz or period_s can be ' \
                       'specified for a wave form'


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
        """Get the internal SCPI trigger number

        Returns:
            int: internal trigger number
        """
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


def floats_to_comma_separated_list(array: Sequence[float]):
    rounded = [format(x, 'g') for x in array]
    return ','.join(rounded)


def array_to_comma_separated_list(array: str):
    return ','.join(map(str, array))


def comma_sequence_to_list(sequence: str):
    if not sequence:
        return []
    return [x.strip() for x in sequence.split(',')]


def comma_sequence_to_list_of_floats(sequence: str):
    if not sequence:
        return []
    return [float(x.strip()) for x in sequence.split(',')]


class _Channel_Context():

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

    def start_on(self, trigger: QDac2Trigger_Context) -> None:
        """Attach internal trigger to DC generator

        Args:
            trigger (QDac2Trigger_Context): trigger that will start DC
        """
        self._trigger = trigger
        internal = _trigger_context_to_value(trigger)
        self._write_channel(f'sour{"{0}"}:dc:trig:sour int{internal}')
        self._make_ready_to_start()

    def start_on_external(self, trigger: ExternalInput) -> None:
        """Attach external trigger to DC generator

        Args:
            trigger (ExternalInput): trigger that will start DC generator
        """
        self._trigger = None
        self._write_channel(f'sour{"{0}"}:dc:trig:sour ext{trigger}')
        self._make_ready_to_start()

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
        self._write_channel('sour{0}:dc:init')

    def _switch_to_immediate_trigger(self) -> None:
        self._write_channel('sour{0}:dc:init:cont off')
        self._write_channel('sour{0}:dc:trig:sour imm')


class Sweep_Context(_Dc_Context):

    def __init__(self, channel: 'QDac2Channel', start_V: float, stop_V: float,
                 points: int, repetitions: int, dwell_s: float, backwards: bool,
                 stepped: bool):
        self._repetitions = repetitions
        super().__init__(channel)
        channel.write_channel('sour{0}:volt:mode swe')
        self._set_voltages(start_V, stop_V)
        channel.write_channel(f'sour{"{0}"}:swe:poin {points}')
        self._set_trigger_mode(stepped)
        channel.write_channel(f'sour{"{0}"}:swe:dwel {dwell_s}')
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
                 repetitions: int, dwell_s: float, backwards: bool,
                 stepped: bool):
        super().__init__(channel)
        self._repetitions = repetitions
        self._write_channel('sour{0}:volt:mode list')
        self._set_voltages(voltages)
        self._set_trigger_mode(stepped)
        self._write_channel(f'sour{"{0}"}:list:dwel {dwell_s}')
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

    def _start_on_external(self, trigger: ExternalInput, wave_kind: str) -> None:
        self._trigger = None
        self._write_channel(f'sour{"{0}"}:{wave_kind}:trig:sour ext{trigger}')
        self._make_ready_to_start(wave_kind)

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
        self._write_channel(f'sour{"{0}"}:{wave_kind}:mark:psta {self._marker_period_start.value}')
        return self._marker_period_start

    def _make_ready_to_start(self, wave_kind: str) -> None:
        self._write_channel(f'sour{"{0}"}:{wave_kind}:init:cont on')
        self._write_channel(f'sour{"{0}"}:{wave_kind}:init')

    def _switch_to_immediate_trigger(self, wave_kind: str):
        self._write_channel(f'sour{"{0}"}:{wave_kind}:init:cont off')
        self._write_channel(f'sour{"{0}"}:{wave_kind}:trig:sour imm')

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
                 span_V: float, offset_V: float, slew_V_s: Optional[float]):
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
        self._write_channel(f'sour{"{0}"}:squ:coun {repetitions}')
        self._set_triggering()

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

    def start_on_external(self, trigger: ExternalInput) -> None:
        """Attach external trigger to start the square wave generator

        Args:
            trigger (ExternalInput): external trigger that will start square wave
        """
        return super()._start_on_external(trigger, 'squ')


class Sine_Context(_Waveform_Context):

    def __init__(self, channel: 'QDac2Channel', frequency_Hz: Optional[float],
                 repetitions: int, period_s: Optional[float], inverted: bool,
                 span_V: float, offset_V: float, slew_V_s: Optional[float]):
        super().__init__(channel)
        self._repetitions = repetitions
        self._write_channel('sour{0}:sin:trig:sour hold')
        self._set_frequency(frequency_Hz, period_s)
        self._set_polarity(inverted)
        self._write_channel(f'sour{"{0}"}:sin:span {span_V}')
        self._write_channel(f'sour{"{0}"}:sin:offs {offset_V}')
        self._set_slew('sin', slew_V_s)
        self._write_channel(f'sour{"{0}"}:sin:coun {repetitions}')
        self._set_triggering()

    def start(self) -> None:
        """Start the sine wave generator
        """
        self._start('sin', 'sine wave')

    def abort(self) -> None:
        """Abort any running sine wave generator
        """
        self._write_channel('sour{0}:sin:abor')

    def cycles_remaining(self) -> int:
        """
        Returns:
            int: Number of cycles remaining in the sine wave
        """
        return int(self._ask_channel('sour{0}:sin:ncl?'))

    def _set_frequency(self, frequency_Hz: Optional[float],
                       period_s: Optional[float]) -> None:
        if frequency_Hz:
            return self._write_channel(f'sour{"{0}"}:sin:freq {frequency_Hz}')
        if period_s:
            self._write_channel(f'sour{"{0}"}:sin:per {period_s}')

    def _set_polarity(self, inverted: bool) -> None:
        if inverted:
            self._write_channel('sour{0}:sin:pol inv')
        else:
            self._write_channel('sour{0}:sin:pol norm')

    def _set_triggering(self) -> None:
        self._write_channel('sour{0}:sin:trig:sour bus')
        self._make_ready_to_start('sin')

    def end_marker(self) -> QDac2Trigger_Context:
        """Internal trigger that will mark the end of the sine wave

        A new internal trigger is allocated if necessary.

        Returns:
            QDac2Trigger_Context: trigger that will mark the end
        """
        return super()._end_marker('sin')

    def start_marker(self) -> QDac2Trigger_Context:
        """Internal trigger that will mark the beginning of the sine wave

        A new internal trigger is allocated if necessary.

        Returns:
            QDac2Trigger_Context: trigger that will mark the beginning
        """
        return super()._start_marker('sin')

    def period_end_marker(self) -> QDac2Trigger_Context:
        """Internal trigger that will mark the end of each period

        A new internal trigger is allocated if necessary.

        Returns:
            QDac2Trigger_Context: trigger that will mark the end of each period
        """
        return super()._period_end_marker('sin')

    def period_start_marker(self) -> QDac2Trigger_Context:
        """Internal trigger that will mark the beginning of each period

        A new internal trigger is allocated if necessary.

        Returns:
            QDac2Trigger_Context: trigger that will mark the beginning of each period
        """
        return super()._period_start_marker('sin')

    def start_on(self, trigger: QDac2Trigger_Context) -> None:
        """Attach internal trigger to start the sine wave generator

        Args:
            trigger (QDac2Trigger_Context): trigger that will start sine wave
        """
        return super()._start_on(trigger, 'sin')

    def start_on_external(self, trigger: ExternalInput) -> None:
        """Attach external trigger to start the sine wave generator

        Args:
            trigger (ExternalInput): external trigger that will start sine wave
        """
        return super()._start_on_external(trigger, 'sin')


class Triangle_Context(_Waveform_Context):

    def __init__(self, channel: 'QDac2Channel', frequency_Hz: Optional[float],
                 repetitions: int, period_s: Optional[float],
                 duty_cycle_percent: float, inverted: bool, span_V: float,
                 offset_V: float, slew_V_s: Optional[float]):
        super().__init__(channel)
        self._repetitions = repetitions
        self._write_channel('sour{0}:tri:trig:sour hold')
        self._set_frequency(frequency_Hz, period_s)
        self._write_channel(f'sour{"{0}"}:tri:dcyc {duty_cycle_percent}')
        self._set_polarity(inverted)
        self._write_channel(f'sour{"{0}"}:tri:span {span_V}')
        self._write_channel(f'sour{"{0}"}:tri:offs {offset_V}')
        self._set_slew('tri', slew_V_s)
        self._write_channel(f'sour{"{0}"}:tri:coun {repetitions}')
        self._set_triggering()

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

    def start_on_external(self, trigger: ExternalInput) -> None:
        """Attach external trigger to start the triangle wave generator

        Args:
            trigger (ExternalInput): external trigger that will start triangle
        """
        return super()._start_on_external(trigger, 'tri')


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

    def start_on_external(self, trigger: ExternalInput) -> None:
        """Attach external trigger to start the AWG

        Args:
            trigger (ExternalInput): external trigger that will start AWG
        """
        return super()._start_on_external(trigger, 'awg')


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
        self._write_channel(f'sens{"{0}"}:init')

    def start_on_external(self, trigger: ExternalInput) -> None:
        """Attach external trigger to start the current measurement

        Args:
            trigger (ExternalInput): trigger that will start measurement
        """
        self._write_channel(f'sens{"{0}"}:trig:sour ext{trigger}')
        self._write_channel(f'sens{"{0}"}:init:cont on')
        self._write_channel(f'sens{"{0}"}:init')

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
            return []
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

    def clear_measurements(self) -> Sequence[float]:
        """Retrieve current measurements

        The available measurements will be removed from measurement queue.

        Returns:
            Sequence[float]: list of available current measurements
        """
        # Bug circumvention
        if int(self.ask_channel('sens{0}:data:poin?')) == 0:
            return []
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
                dwell_s: float = 1e-03, backwards: bool = False,
                stepped: bool = False
                ) -> List_Context:
        """Set up a DC-list generator

        Args:
            voltages (Sequence[float]): Voltages in list
            repetitions (int, optional): Number of repetitions of the list (default 1)
            dwell_s (float, optional): Seconds between each voltage (default 1ms)
            backwards (bool, optional): Use list in reverse (default is forward)
            stepped (bool, optional): True means that each step needs to be triggered (default False)

        Returns:
            List_Context: context manager
        """
        return List_Context(self, voltages, repetitions, dwell_s, backwards,
                            stepped)

    def dc_sweep(self, start_V: float, stop_V: float, points: int,
                 repetitions=1, dwell_s=1e-03, backwards=False, stepped=True
                 ) -> Sweep_Context:
        """Set up a DC sweep

        Args:
            start_V (float): Start voltage
            stop_V (float): Send voltage
            points (int): Number of steps
            repetitions (int, optional): Number of repetition (default 1)
            dwell_s (float, optional): Seconds between each voltage (default 1ms)
            backwards (bool, optional): Sweep in reverse (default is forward)
            stepped (bool, optional): True means that each step needs to be triggered (default False)

        Returns:
            Sweep_Context: context manager
        """
        return Sweep_Context(self, start_V, stop_V, points, repetitions,
                             dwell_s, backwards, stepped)

    def square_wave(self, frequency_Hz: Optional[float] = None,
                    period_s: Optional[float] = None, repetitions: int = -1,
                    duty_cycle_percent: float = 50.0, kind: str = 'symmetric',
                    inverted: bool = False, span_V: float = 0.2,
                    offset_V: float = 0.0, slew_V_s: Optional[float] = None
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
                              offset_V, slew_V_s)

    def sine_wave(self, frequency_Hz: Optional[float] = None,
                  period_s: Optional[float] = None, repetitions: int = -1,
                  inverted: bool = False, span_V: float = 0.2,
                  offset_V: float = 0.0, slew_V_s: Optional[float] = None
                  ) -> Sine_Context:
        """Set up a sine-wave generator

        Args:
            frequency_Hz (float, optional): Frequency
            period_s (float, optional): Period length (instead of frequency)
            repetitions (int, optional): Number of repetition (default infinite)
            inverted (bool, optional): True means flipped (default False)
            span_V (float, optional): Voltage span (default 200mV)
            offset_V (float, optional): Offset (default 0V)
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
                            inverted, span_V, offset_V, slew_V_s)

    def triangle_wave(self, frequency_Hz: Optional[float] = None,
                      period_s: Optional[float] = None, repetitions: int = -1,
                      duty_cycle_percent: float = 50.0, inverted: bool = False,
                      span_V: float = 0.2, offset_V: float = 0.0,
                      slew_V_s: Optional[float] = None
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
                                offset_V, slew_V_s)

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
        """
        Returns:
            int: Number of values in trace
        """
        return self._size

    @property
    def name(self) -> str:
        """Returns:
            str: Name of trace
        """
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


class Sweep_2D_Context:

    def __init__(self, arrangement: 'Arrangement_Context', sweep: np.ndarray,
                 start_sweep_trigger: Optional[str], inner_step_time_s: float,
                 inner_step_trigger: Optional[str]):
        self._arrangement = arrangement
        self._sweep = sweep
        self._inner_step_trigger = inner_step_trigger
        self._inner_step_time_s = inner_step_time_s
        self._allocate_triggers(start_sweep_trigger)
        self._qdac_ready = False

    def __enter__(self):
        self._ensure_qdac_setup()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Let Arrangement take care of freeing triggers
        return False

    def actual_values_V(self, gate: str) -> np.ndarray:
        """The corrected values that would actually be sent to the gate

        Args:
            gate (str): Name of gate

        Returns:
            np.ndarray: Corrected voltages
        """
        index = self._arrangement._gate_index(gate)
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
        if not self._inner_step_trigger:
            return
        trigger = self._arrangement.get_trigger_by_name(self._inner_step_trigger)
        # All channels change in sync, so just use the first channel to make the
        # external trigger.
        channel = self._get_channel(0)
        channel.write_channel(f'sour{"{0}"}:dc:mark:sst '
                              f'{_trigger_context_to_value(trigger)}')

    def _get_channel(self, gate_index: int) -> 'QDac2Channel':
        channel_number = self._arrangement._channels[gate_index]
        qdac = self._arrangement._qdac
        return qdac.channel(channel_number)

    def _send_lists_to_qdac(self) -> None:
        for gate_index in range(self._arrangement.shape):
            self._send_list_to_qdac(gate_index, self._sweep[:, gate_index])

    def _send_list_to_qdac(self, gate_index, voltages):
        channel = self._get_channel(gate_index)
        dc_list = channel.dc_list(voltages=voltages, dwell_s=self._inner_step_time_s)
        trigger = self._arrangement.get_trigger_by_name(self._start_trigger_name)
        dc_list.start_on(trigger)

    def _make_ready_to_start(self):  # Bug circumvention
        for gate_index in range(self._arrangement.shape):
            channel = self._get_channel(gate_index)
            channel.write_channel('sour{0}:dc:init')


class Arrangement_Context:
    def __init__(self, qdac: 'QDac2', gates: Dict[str, int],
                 output_triggers: Optional[Dict[str, int]],
                 internal_triggers: Optional[Sequence[str]]):
        self._qdac = qdac
        self._fix_gate_order(gates)
        self._allocate_triggers(internal_triggers, output_triggers)
        self._correction = np.identity(self.shape)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._free_triggers()
        return False

    @property
    def shape(self) -> int:
        """
        Returns:
            int: Number of gates in the arrangement
        """
        return len(self._gates)

    @property
    def correction_matrix(self) -> np.ndarray:
        """
        Returns:
            np.ndarray: Correction matrix
        """
        return self._correction

    def _allocate_internal_triggers(self,
                                    internal_triggers: Optional[Sequence[str]]
                                    ) -> None:
        if not internal_triggers:
            return
        for name in internal_triggers:
            self._internal_triggers[name] = self._qdac.allocate_trigger()

    def initiate_correction(self, gate: str, factors: Sequence[float]):
        """Override how much a particular gate influences the other gates

        Args:
            gate (str): Name of gate
            factors (Sequence[float]): factors between -1.0 and 1.0
        """
        index = self._gate_index(gate)
        self._correction[index] = factors

    def set_virtual_voltage(self, gate: str, voltage: float) -> None:
        index = self._gate_index(gate)
        self._virtual_voltages[index] = voltage

    def add_correction(self, gate: str, factors: Sequence[float]) -> None:
        """Update how much a particular gate influences the other gates

        This is mostly useful in arrangements where each gate has significant
        effect only on nearby gates, and thus can be added incrementally.

        The factors are extended by the identity matrix and multiplied to the
        correction matrix.

        Args:
            gate (str): Name of gate
            factors (Sequence[float]): factors usually between -1.0 and 1.0
        """
        index = self._gate_index(gate)
        multiplier = np.identity(self.shape)
        multiplier[index] = factors
        self._correction = np.matmul(multiplier, self._correction)

    def _fix_gate_order(self, gates: Dict[str, int]) -> None:
        self._gates = {}
        self._channels = []
        index = 0
        for gate, channel in gates.items():
            self._gates[gate] = index
            index += 1
            self._channels.append(channel)
        self._virtual_voltages = np.zeros(self.shape)

    def virtual_voltage(self, gate: str) -> float:
        """
        Args:
            gate (str): Name of gate

        Returns:
            float: Virtual voltage on the gate
        """
        index = self._gate_index(gate)
        return self._virtual_voltages[index]

    def actual_voltages(self) -> Sequence[float]:
        """
        Returns:
            Sequence[float]: Corrected voltages for all gates
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

    def virtual_sweep2d(self, inner_gate: str, inner_voltages: Sequence[float],
                        outer_gate: str, outer_voltages: Sequence[float],
                        start_sweep_trigger: Optional[str] = None,
                        inner_step_time_s: float = 1e-5,
                        inner_step_trigger: Optional[str] = None
                        ) -> Sweep_2D_Context:
        """Sweep two gates to create a 2D sweep

        Args:
            inner_gate (str): Name of fast-changing (inner) gate
            inner_voltages (Sequence[float]): Inner gate voltages
            outer_gate (str): Name of slow-changing (outer) gate
            outer_voltages (Sequence[float]): Outer gate voltages
            start_sweep_trigger (None, optional): Trigger that starts sweep
            inner_step_time_s (float, optional): Delay between voltage changes
            inner_step_trigger (None, optional): Trigger that marks each step

        Returns:
            Sweep_2D_Context: context manager
        """
        sweep = self._calculate_sweep_values(inner_gate, inner_voltages,
                                             outer_gate, outer_voltages)
        return Sweep_2D_Context(self, sweep, start_sweep_trigger,
                                inner_step_time_s, inner_step_trigger)

    def _calculate_sweep_values(self, inner_gate: str,
                                inner_voltages: Sequence[float],
                                outer_gate: str,
                                outer_voltages: Sequence[float]) -> np.ndarray:
        original_fast_voltage = self.virtual_voltage(inner_gate)
        original_slow_voltage = self.virtual_voltage(outer_gate)
        sweep = []
        for slow_V in outer_voltages:
            self.set_virtual_voltage(outer_gate, slow_V)
            for fast_V in inner_voltages:
                self.set_virtual_voltage(inner_gate, fast_V)
                sweep.append(self.actual_voltages())
        self.set_virtual_voltage(inner_gate, original_fast_voltage)
        self.set_virtual_voltage(outer_gate, original_slow_voltage)
        return np.array(sweep)

    def _gate_index(self, gate: str) -> int:
        return self._gates[gate]

    def _allocate_triggers(self, internal_triggers: Optional[Sequence[str]],
                           output_triggers: Optional[Dict[str, int]]
                           ) -> None:
        self._internal_triggers: Dict[str, QDac2Trigger_Context] = {}
        self._allocate_internal_triggers(internal_triggers)
        self._allocate_external_triggers(output_triggers)

    def _allocate_external_triggers(self, output_triggers:
                                    Optional[Dict[str, int]]
                                    ) -> None:
        self._external_triggers = {}
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
        return 16

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

    def arrange(self, gates: Dict[str, int],
                output_triggers: Optional[Dict[str, int]] = None,
                internal_triggers: Optional[Sequence[str]] = None
                ) -> Arrangement_Context:
        """An arrangement of gates and triggers for virtual 2D sweeps

        Each gate corresponds to a particular output channel and each trigger
        corresponds to a particular external or internal trigger.  After
        initialisation of the arrangement, gates and triggers can only be
        referred to by name.

        The voltages that will appear on each gate depends not only on the
        specified virtual voltage, but also on a correction matrix.

        Initially, the gates are assumed to not influence each other, which
        means that the correction matrix is the identity matrix, ie. the row for
        each gate has a value of [0, ..., 0, 1, 0, ..., 0].

        Args:
            gates (Gates): Name/channel pairs
            output_triggers (Optional[Sequence[Tuple[str,int]]], optional): Name/number pairs of output triggers
            internal_triggers (Optional[Sequence[str]], optional): List of names of internal triggers to allocate

        Returns:
            Arrangement_Context: Description
        """
        return Arrangement_Context(self, gates, output_triggers,
                                   internal_triggers)

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
        self._scpi_sent: List[str] = []
        self._record_commands = True

    def get_recorded_scpi_commands(self) -> List[str]:
        """
        Returns:
            Sequence[str]: SCPI commands sent to the instrument
        """
        commands = self._scpi_sent
        self._scpi_sent = []
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
        lingering = []
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
        self._scpi_sent = []
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
        least_compatible_fw = '3-0.9.16'
        firmware = self.IDN()['firmware']
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
            trigger = QDac2ExternalTrigger(self, str(QDac2ExternalTrigger), i)
            self.add_submodule(name, trigger)
            triggers.append(trigger)
        triggers.lock()
        self.add_submodule('external_triggers', triggers)

    def _set_up_internal_triggers(self) -> None:
        # A set of the available 16 internal triggers
        self._internal_triggers = set(range(1, self.n_triggers() + 1))

    def _set_up_manual_triggers(self) -> None:
        self.add_parameter(
            name='trigger',
            # Manually trigger event
            set_parser=_trigger_context_to_value,
            set_cmd='tint {}',
        )

    def _set_up_simple_functions(self) -> None:
        self.add_function('reset', call_cmd='*rst')
        self.add_function('abort', call_cmd='abor')

    def _check_instrument_name(self, name: str) -> None:
        if name.isidentifier():
            return
        raise ValueError(
            f'Instrument name "{name}" is incompatible with QCoDeS parameter '
            'generation (no spaces, punctuation, prepended numbers, etc)')
