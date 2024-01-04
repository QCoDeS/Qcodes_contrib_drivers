import pytest
from .sim_qdac2_fixtures import qdac  # noqa
from qcodes_contrib_drivers.drivers.QDevil.QDAC2 import ExternalInput


def test_square_ambiguous(qdac):  # noqa
    # -----------------------------------------------------------------------
    with pytest.raises(ValueError) as error:
        qdac.ch01.square_wave(period_s=1, frequency_Hz=10)
    # -----------------------------------------------------------------------
    assert 'frequency_Hz or period_s can be specified' in repr(error)


def test_square_default_values(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch24.square_wave()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour24:squ:trig:sour hold',
        'sour24:squ:freq 1000',
        'sour24:squ:dcyc 50.0',
        'sour24:squ:typ symm',
        'sour24:squ:pol norm',
        'sour24:squ:span 0.2',
        'sour24:squ:offs 0.0',
        'sour24:squ:slew inf',
        'sour24:squ:del 0',
        'sour24:squ:coun -1',
        'sour24:squ:trig:sour bus',
        'sour24:squ:init:cont on',
    ]


def test_square_period(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch24.square_wave(
        period_s=11,
        inverted=True,
        span_V=1,
        offset_V=-0.1,
        kind='positive',
        duty_cycle_percent=99,
        delay_s=0.02,
        slew_V_s=2
    )
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour24:squ:trig:sour hold',
        'sour24:squ:per 11',
        'sour24:squ:dcyc 99',
        'sour24:squ:typ pos',
        'sour24:squ:pol inv',
        'sour24:squ:span 1',
        'sour24:squ:offs -0.1',
        'sour24:squ:slew 2',
        'sour24:squ:del 0.02',
        'sour24:squ:coun -1',
        'sour24:squ:trig:sour bus',
        'sour24:squ:init:cont on',
    ]


def test_square_slew(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch24.square_wave(slew_V_s=0.1)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour24:squ:trig:sour hold',
        'sour24:squ:freq 1000',
        'sour24:squ:dcyc 50.0',
        'sour24:squ:typ symm',
        'sour24:squ:pol norm',
        'sour24:squ:span 0.2',
        'sour24:squ:offs 0.0',
        'sour24:squ:slew 0.1',
        'sour24:squ:del 0',
        'sour24:squ:coun -1',
        'sour24:squ:trig:sour bus',
        'sour24:squ:init:cont on',
    ]


def test_square_negative(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch24.square_wave(
        period_s=111,
        repetitions=10,
        span_V=5,
        kind='negative',
        duty_cycle_percent=1,
    )
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour24:squ:trig:sour hold',
        'sour24:squ:per 111',
        'sour24:squ:dcyc 1',
        'sour24:squ:typ neg',
        'sour24:squ:pol norm',
        'sour24:squ:span 5',
        'sour24:squ:offs 0.0',
        'sour24:squ:slew inf',
        'sour24:squ:del 0',
        'sour24:squ:coun 10',
        'sour24:squ:trig:sour bus',
        'sour24:squ:init:cont on',
    ]


def test_square_frequency(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch24.square_wave(frequency_Hz=1e5)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour24:squ:trig:sour hold',
        'sour24:squ:freq 100000.0',
        'sour24:squ:dcyc 50.0',
        'sour24:squ:typ symm',
        'sour24:squ:pol norm',
        'sour24:squ:span 0.2',
        'sour24:squ:offs 0.0',
        'sour24:squ:slew inf',
        'sour24:squ:del 0',
        'sour24:squ:coun -1',
        'sour24:squ:trig:sour bus',
        'sour24:squ:init:cont on',
    ]


def test_square_start_without_explicit_trigger(qdac):  # noqa
    square = qdac.ch24.square_wave()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    square.start()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour24:squ:init:cont off',
        'sour24:squ:trig:sour imm',
        'sour24:squ:init'
    ]


def test_square_abort(qdac):  # noqa
    square = qdac.ch24.square_wave()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    square.abort()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == ['sour24:squ:abor']


def test_square_remaining(qdac):  # noqa
    square = qdac.ch01.square_wave(repetitions=10)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    square.cycles_remaining()
    # -----------------------------------------------------------------------
    # Cannot sim test: assert remaining == 1
    assert qdac.get_recorded_scpi_commands() == ['sour1:squ:ncl?']


def test_square_end_marker_alloc(qdac):  # noqa
    qdac.free_all_triggers()
    square = qdac.ch01.square_wave(frequency_Hz=1000)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger = square.end_marker()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:squ:mark:end {trigger.value}'
    ]


def test_square_end_marker_reuse(qdac):  # noqa
    qdac.free_all_triggers()
    square = qdac.ch01.square_wave(frequency_Hz=1000)
    trigger = square.end_marker()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger2 = square.end_marker()
    # -----------------------------------------------------------------------
    assert trigger2 == trigger
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:squ:mark:end {trigger.value}'
    ]


def test_square_start_marker_alloc(qdac):  # noqa
    qdac.free_all_triggers()
    square = qdac.ch01.square_wave(frequency_Hz=1000)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger = square.start_marker()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:squ:mark:star {trigger.value}'
    ]


def test_square_start_marker_reuse(qdac):  # noqa
    qdac.free_all_triggers()
    square = qdac.ch01.square_wave(frequency_Hz=1000)
    trigger = square.start_marker()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger2 = square.start_marker()
    # -----------------------------------------------------------------------
    assert trigger2 == trigger
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:squ:mark:star {trigger.value}'
    ]


def test_square_start_trigger_fires(qdac):  # noqa
    qdac.free_all_triggers()
    square = qdac.ch01.square_wave(frequency_Hz=1000)
    trigger = qdac.allocate_trigger()
    square.start_on(trigger)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    square.start()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour1:squ:init:cont on',
        f'tint {trigger.value}'
    ]


def test_square_period_end_trigger_alloc(qdac):  # noqa
    qdac.free_all_triggers()
    square = qdac.ch01.square_wave(frequency_Hz=1000)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger = square.period_end_marker()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:squ:mark:pend {trigger.value}'
    ]


def test_square_period_end_trigger_reuse(qdac):  # noqa
    qdac.free_all_triggers()
    square = qdac.ch01.square_wave(frequency_Hz=1000)
    trigger = square.period_end_marker()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger2 = square.period_end_marker()
    # -----------------------------------------------------------------------
    assert trigger2 == trigger
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:squ:mark:pend {trigger.value}'
    ]


def test_square_period_start_trigger_alloc(qdac):  # noqa
    qdac.free_all_triggers()
    square = qdac.ch01.square_wave(frequency_Hz=1000)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger = square.period_start_marker()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:squ:mark:pstart {trigger.value}'
    ]


def test_square_period_start_trigger_reuse(qdac):  # noqa
    qdac.free_all_triggers()
    square = qdac.ch01.square_wave(frequency_Hz=1000)
    trigger = square.period_start_marker()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger2 = square.period_start_marker()
    # -----------------------------------------------------------------------
    assert trigger2 == trigger
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:squ:mark:pstart {trigger.value}'
    ]


def test_square_trigger_on_internal(qdac):  # noqa
    square = qdac.ch01.square_wave(frequency_Hz=1000)
    trigger = qdac.allocate_trigger()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    square.start_on(trigger)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:squ:trig:sour int{trigger.value}',
        f'sour1:squ:init:cont on',
    ]


def test_square_trigger_on_external(qdac):  # noqa
    square = qdac.ch01.square_wave(frequency_Hz=1000)
    trigger = ExternalInput(1)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    square.start_on_external(trigger)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:squ:trig:sour ext{trigger}',
        f'sour1:squ:init:cont on',
    ]


def test_square_main_trigger_is_deallocated_on_exit(qdac):  # noqa
    qdac._set_up_internal_triggers()
    trigger = qdac.allocate_trigger()
    # -----------------------------------------------------------------------
    with qdac.ch01.square_wave(frequency_Hz=1000) as square:
        square.start_on(trigger)
        qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour1:squ:abor',
        'sour1:squ:trig:sour imm'
    ]
    assert trigger.value in qdac._internal_triggers


def test_square_main_trigger_external_is_dismissed_on_exit(qdac):  # noqa
    trigger = ExternalInput(2)
    # -----------------------------------------------------------------------
    with qdac.ch01.square_wave(frequency_Hz=1000) as square:
        square.start_on_external(trigger)
        qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour1:squ:abor',
        'sour1:squ:trig:sour imm'
    ]


def test_square_start_marker_is_removed_on_exit(qdac):  # noqa
    qdac._set_up_internal_triggers()
    # -----------------------------------------------------------------------
    with qdac.ch01.square_wave(frequency_Hz=1000) as square:
        trigger = square.start_marker()
        qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour1:squ:abor',
        'sour1:squ:mark:star 0',
        'sour1:squ:trig:sour imm'
    ]
    assert trigger.value in qdac._internal_triggers


def test_square_end_marker_is_removed_on_exit(qdac):  # noqa
    qdac._set_up_internal_triggers()
    # -----------------------------------------------------------------------
    with qdac.ch01.square_wave(frequency_Hz=1000) as square:
        trigger = square.end_marker()
        qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour1:squ:abor',
        'sour1:squ:mark:end 0',
        'sour1:squ:trig:sour imm'
    ]
    assert trigger.value in qdac._internal_triggers


def test_square_period_start_marker_is_removed_on_exit(qdac):  # noqa
    qdac._set_up_internal_triggers()
    # -----------------------------------------------------------------------
    with qdac.ch01.square_wave(frequency_Hz=1000) as square:
        trigger = square.period_start_marker()
        qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour1:squ:abor',
        'sour1:squ:mark:pstart 0',
        'sour1:squ:trig:sour imm'
    ]
    assert trigger.value in qdac._internal_triggers


def test_square_period_end_marker_is_removed_on_exit(qdac):  # noqa
    qdac._set_up_internal_triggers()
    # -----------------------------------------------------------------------
    with qdac.ch01.square_wave(frequency_Hz=1000) as square:
        trigger = square.period_end_marker()
        qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour1:squ:abor',
        'sour1:squ:mark:pend 0',
        'sour1:squ:trig:sour imm'
    ]
    assert trigger.value in qdac._internal_triggers
