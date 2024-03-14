import pytest
import numpy
from .sim_qdac2_fixtures import qdac  # noqa
from qcodes_contrib_drivers.drivers.QDevil.QDAC2 import ExternalInput


def test_trace_remove_all(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.remove_traces()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == ['trac:rem:all']


def test_trace_catalog(qdac):  # noqa
    # -----------------------------------------------------------------------
    traces = qdac.traces()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == ['trac:cat?']
    assert traces == []


def test_trace_define(qdac):  # noqa
    name = 'my_1st_trace'
    length = 1024
    # -----------------------------------------------------------------------
    trace = qdac.allocate_trace(name, length)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [f'trac:def "{name}",{length}']
    assert trace.name == name
    assert trace.size == length
    assert len(trace) == length


def test_trace_removed(qdac):  # noqa
    name = 'my_4th_trace'
    qdac.allocate_trace(name, 1024)
    # -----------------------------------------------------------------------
    qdac.remove_traces()
    # -----------------------------------------------------------------------
    assert name not in qdac.traces()


# Cannot test:
# # def test_trace_duplicate(qdac):  # noqa
#     name = 'my_1st_trace'
#     qdac.allocate_trace(name, 1024)
#     # -----------------------------------------------------------------------
#     with pytest.raises(ValueError) as error:
#         qdac.allocate_trace(name, 2048)
#     # -----------------------------------------------------------------------
#     assert name in repr(error)
#     assert 'exist' in repr(error)


def test_trace_data(qdac):  # noqa
    name = 'my_2nd_trace'
    trace = qdac.allocate_trace(name, 6)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trace.waveform(numpy.linspace(0, 1, 6))
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'trac:data "{name}",0,0.2,0.4,0.6,0.8,1']


def test_trace_data_length_mismatch(qdac):  # noqa
    name = 'my_2nd_trace'
    trace = qdac.allocate_trace(name, 6)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    with pytest.raises(ValueError) as error:
        trace.waveform(numpy.linspace(0, 1, 5))
    # -----------------------------------------------------------------------
    assert 'length 5 does not match allocated length 6' in repr(error)


def test_awg_default_values(qdac):  # noqa
    name = '3rd_trace'
    trace = qdac.allocate_trace(name, 6)
    trace.waveform(numpy.linspace(0, 1, 6))
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    qdac.ch05.arbitrary_wave(trace.name)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour5:awg:trig:sour hold',
        f'sour5:awg:def "{trace.name}"',
        'sour5:awg:scal 1.0',
        'sour5:awg:offs 0.0',
        'sour5:awg:slew inf',
        'sour5:awg:coun 1',
        'sour5:awg:trig:sour bus',
        'sour5:awg:init:cont on',
    ]


def test_awg_parameters(qdac):  # noqa
    name = '3rd_trace'
    trace = qdac.allocate_trace(name, 6)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    qdac.ch05.arbitrary_wave(
        trace.name,
        repetitions=10,
        scale=-2,
        offset_V=-0.1,
        slew_V_s=2,
    )
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour5:awg:trig:sour hold',
        f'sour5:awg:def "{trace.name}"',
        'sour5:awg:scal -2',
        'sour5:awg:offs -0.1',
        'sour5:awg:slew 2',
        'sour5:awg:coun 10',
        'sour5:awg:trig:sour bus',
        'sour5:awg:init:cont on',
    ]


def test_awg_start_without_explicit_trigger(qdac):  # noqa
    trace = qdac.allocate_trace('my-trace', 6)
    awg = qdac.ch05.arbitrary_wave(trace.name)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    awg.start()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour5:awg:init:cont off',
        'sour5:awg:trig:sour imm',
        'sour5:awg:init'
    ]


def test_awg_abort(qdac):  # noqa
    trace = qdac.allocate_trace('my-trace', 6)
    awg = qdac.ch05.arbitrary_wave(trace.name)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    awg.abort()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == ['sour5:awg:abor']


def test_awg_remaining(qdac):  # noqa
    trace = qdac.allocate_trace('my-trace', 6)
    awg = qdac.ch05.arbitrary_wave(trace.name)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    awg.cycles_remaining()
    # -----------------------------------------------------------------------
    # Cannot sim test: assert remaining == 1
    assert qdac.get_recorded_scpi_commands() == ['sour5:awg:ncl?']


def test_awg_end_marker_alloc(qdac):  # noqa
    qdac._set_up_internal_triggers()
    trace = qdac.allocate_trace('my-trace', 6)
    awg = qdac.ch05.arbitrary_wave(trace.name)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger = awg.end_marker()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour5:awg:mark:end {trigger.value}'
    ]


def test_awg_end_marker_reuse(qdac):  # noqa
    qdac._set_up_internal_triggers()
    trace = qdac.allocate_trace('my-trace', 6)
    awg = qdac.ch05.arbitrary_wave(trace.name)
    trigger = awg.end_marker()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger2 = awg.end_marker()
    # -----------------------------------------------------------------------
    assert trigger2 == trigger
    assert qdac.get_recorded_scpi_commands() == [
        f'sour5:awg:mark:end {trigger.value}'
    ]


def test_awg_start_marker_alloc(qdac):  # noqa
    qdac._set_up_internal_triggers()
    trace = qdac.allocate_trace('my-trace', 6)
    awg = qdac.ch05.arbitrary_wave(trace.name)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger = awg.start_marker()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour5:awg:mark:star {trigger.value}'
    ]


def test_awg_start_marker_reuse(qdac):  # noqa
    qdac._set_up_internal_triggers()
    trace = qdac.allocate_trace('my-trace', 6)
    awg = qdac.ch05.arbitrary_wave(trace.name)
    trigger = awg.start_marker()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger2 = awg.start_marker()
    # -----------------------------------------------------------------------
    assert trigger2 == trigger
    assert qdac.get_recorded_scpi_commands() == [
        f'sour5:awg:mark:star {trigger.value}'
    ]


def test_awg_start_trigger_fires(qdac):  # noqa
    qdac._set_up_internal_triggers()
    trace = qdac.allocate_trace('my-trace', 6)
    awg = qdac.ch05.arbitrary_wave(trace.name)
    trigger = qdac.allocate_trigger()
    awg.start_on(trigger)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    awg.start()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour5:awg:init:cont on',
        f'tint {trigger.value}'
    ]


def test_awg_period_end_trigger_alloc(qdac):  # noqa
    qdac._set_up_internal_triggers()
    trace = qdac.allocate_trace('my-trace', 6)
    awg = qdac.ch05.arbitrary_wave(trace.name)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger = awg.period_end_marker()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour5:awg:mark:pend {trigger.value}'
    ]


def test_awg_period_end_trigger_reuse(qdac):  # noqa
    qdac._set_up_internal_triggers()
    trace = qdac.allocate_trace('my-trace', 6)
    awg = qdac.ch05.arbitrary_wave(trace.name)
    trigger = awg.period_end_marker()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger2 = awg.period_end_marker()
    # -----------------------------------------------------------------------
    assert trigger2 == trigger
    assert qdac.get_recorded_scpi_commands() == [
        f'sour5:awg:mark:pend {trigger.value}'
    ]


def test_awg_period_start_trigger_alloc(qdac):  # noqa
    qdac._set_up_internal_triggers()
    trace = qdac.allocate_trace('my-trace', 6)
    awg = qdac.ch05.arbitrary_wave(trace.name)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger = awg.period_start_marker()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour5:awg:mark:pstart {trigger.value}'
    ]


def test_awg_period_start_trigger_reuse(qdac):  # noqa
    qdac._set_up_internal_triggers()
    trace = qdac.allocate_trace('my-trace', 6)
    awg = qdac.ch05.arbitrary_wave(trace.name)
    trigger = awg.period_start_marker()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger2 = awg.period_start_marker()
    # -----------------------------------------------------------------------
    assert trigger2 == trigger
    assert qdac.get_recorded_scpi_commands() == [
        f'sour5:awg:mark:pstart {trigger.value}'
    ]


def test_awg_trigger_on_internal(qdac):  # noqa
    trace = qdac.allocate_trace('my-trace', 6)
    awg = qdac.ch05.arbitrary_wave(trace.name)
    trigger = qdac.allocate_trigger()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    awg.start_on(trigger)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour5:awg:trig:sour int{trigger.value}',
        f'sour5:awg:init:cont on',
    ]


def test_awg_trigger_once_on_internal(qdac):  # noqa
    trace = qdac.allocate_trace('my-trace', 6)
    awg = qdac.ch05.arbitrary_wave(trace.name)
    trigger = qdac.allocate_trigger()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    awg.start_once_on(trigger)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour5:awg:trig:sour int{trigger.value}',
        f'sour5:awg:init:cont off',
    ]


def test_awg_trigger_on_external(qdac):  # noqa
    trace = qdac.allocate_trace('my-trace', 6)
    awg = qdac.ch05.arbitrary_wave(trace.name)
    trigger = ExternalInput(1)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    awg.start_on_external(trigger)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour5:awg:trig:sour ext{trigger}',
        f'sour5:awg:init:cont on',
    ]


def test_awg_trigger_once_on_external(qdac):  # noqa
    trace = qdac.allocate_trace('my-trace', 6)
    awg = qdac.ch05.arbitrary_wave(trace.name)
    trigger = ExternalInput(1)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    awg.start_once_on_external(trigger)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour5:awg:trig:sour ext{trigger}',
        f'sour5:awg:init:cont off',
    ]
