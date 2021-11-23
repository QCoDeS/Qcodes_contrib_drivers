import pytest
from .sim_qdac2_fixtures import qdac  # noqa
from qcodes_contrib_drivers.drivers.QDevil.QDAC2 import ExternalInput


def test_triangle_ambiguous(qdac):  # noqa
    # -----------------------------------------------------------------------
    with pytest.raises(ValueError) as error:
        qdac.ch01.triangle_wave(period_s=1, frequency_Hz=10)
    # -----------------------------------------------------------------------
    assert 'frequency_Hz or period_s can be specified' in repr(error)


def test_triangle_default_vaules(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch24.triangle_wave()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour24:tri:trig:sour hold',
        'sour24:tri:freq 1000',
        'sour24:tri:dcyc 50.0',
        'sour24:tri:pol norm',
        'sour24:tri:span 0.2',
        'sour24:tri:offs 0.0',
        'sour24:tri:slew inf',
        'sour24:tri:coun -1',
        'sour24:tri:trig:sour bus',
        'sour24:tri:init:cont on',
        'sour24:tri:init',
    ]


def test_triangle_period(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch24.triangle_wave(
        period_s=11,
        inverted=True,
        span_V=1,
        offset_V=-0.1,
        duty_cycle_percent=99,
        slew_V_s=1
    )
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour24:tri:trig:sour hold',
        'sour24:tri:per 11',
        'sour24:tri:dcyc 99',
        'sour24:tri:pol inv',
        'sour24:tri:span 1',
        'sour24:tri:offs -0.1',
        'sour24:tri:slew 1',
        'sour24:tri:coun -1',
        'sour24:tri:trig:sour bus',
        'sour24:tri:init:cont on',
        'sour24:tri:init',
    ]


def test_triangle_negative(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch24.triangle_wave(
        period_s=111,
        repetitions=10,
        span_V=5,
        duty_cycle_percent=1,
    )
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour24:tri:trig:sour hold',
        'sour24:tri:per 111',
        'sour24:tri:dcyc 1',
        'sour24:tri:pol norm',
        'sour24:tri:span 5',
        'sour24:tri:offs 0.0',
        'sour24:tri:slew inf',
        'sour24:tri:coun 10',
        'sour24:tri:trig:sour bus',
        'sour24:tri:init:cont on',
        'sour24:tri:init',
    ]


def test_triangle_frequency(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch24.triangle_wave(frequency_Hz=1e5)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour24:tri:trig:sour hold',
        'sour24:tri:freq 100000.0',
        'sour24:tri:dcyc 50.0',
        'sour24:tri:pol norm',
        'sour24:tri:span 0.2',
        'sour24:tri:offs 0.0',
        'sour24:tri:slew inf',
        'sour24:tri:coun -1',
        'sour24:tri:trig:sour bus',
        'sour24:tri:init:cont on',
        'sour24:tri:init',
    ]


def test_triangle_start_without_explicit_trigger(qdac):  # noqa
    triangle = qdac.ch24.triangle_wave()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    triangle.start()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour24:tri:init:cont off',
        'sour24:tri:trig:sour imm',
        'sour24:tri:init'
    ]


def test_triangle_abort(qdac):  # noqa
    triangle = qdac.ch24.triangle_wave()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    triangle.abort()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == ['sour24:tri:abor']


def test_triangle_remaining(qdac):  # noqa
    triangle = qdac.ch01.triangle_wave(repetitions=10)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    triangle.cycles_remaining()
    # -----------------------------------------------------------------------
    # Cannot sim test: assert remaining == 1
    assert qdac.get_recorded_scpi_commands() == ['sour1:tri:ncl?']


def test_triangle_end_marker_alloc(qdac):  # noqa
    qdac._set_up_internal_triggers()
    triangle = qdac.ch01.triangle_wave(frequency_Hz=1000)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger = triangle.end_marker()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:tri:mark:end {trigger.value}'
    ]


def test_triangle_end_marker_reuse(qdac):  # noqa
    qdac._set_up_internal_triggers()
    triangle = qdac.ch01.triangle_wave(frequency_Hz=1000)
    trigger = triangle.end_marker()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger2 = triangle.end_marker()
    # -----------------------------------------------------------------------
    assert trigger2 == trigger
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:tri:mark:end {trigger.value}'
    ]


def test_triangle_start_marker_alloc(qdac):  # noqa
    qdac._set_up_internal_triggers()
    triangle = qdac.ch01.triangle_wave(frequency_Hz=1000)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger = triangle.start_marker()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:tri:mark:star {trigger.value}'
    ]


def test_triangle_start_marker_reuse(qdac):  # noqa
    qdac._set_up_internal_triggers()
    triangle = qdac.ch01.triangle_wave(frequency_Hz=1000)
    trigger = triangle.start_marker()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger2 = triangle.start_marker()
    # -----------------------------------------------------------------------
    assert trigger2 == trigger
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:tri:mark:star {trigger.value}'
    ]


def test_triangle_start_trigger_fires(qdac):  # noqa
    qdac._set_up_internal_triggers()
    triangle = qdac.ch01.triangle_wave(frequency_Hz=1000)
    trigger = qdac.allocate_trigger()
    triangle.start_on(trigger)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    triangle.start()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour1:tri:init:cont on',
        'sour1:tri:init',
        f'tint {trigger.value}'
    ]


def test_triangle_period_end_marker_alloc(qdac):  # noqa
    qdac._set_up_internal_triggers()
    triangle = qdac.ch01.triangle_wave(frequency_Hz=1000)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger = triangle.period_end_marker()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:tri:mark:pend {trigger.value}'
    ]


def test_triangle_period_end_marker_reuse(qdac):  # noqa
    qdac._set_up_internal_triggers()
    triangle = qdac.ch01.triangle_wave(frequency_Hz=1000)
    trigger = triangle.period_end_marker()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger2 = triangle.period_end_marker()
    # -----------------------------------------------------------------------
    assert trigger2 == trigger
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:tri:mark:pend {trigger.value}'
    ]


def test_triangle_period_start_marker_alloc(qdac):  # noqa
    qdac._set_up_internal_triggers()
    triangle = qdac.ch01.triangle_wave(frequency_Hz=1000)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger = triangle.period_start_marker()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:tri:mark:psta {trigger.value}'
    ]


def test_triangle_period_start_marker_reuse(qdac):  # noqa
    qdac._set_up_internal_triggers()
    triangle = qdac.ch01.triangle_wave(frequency_Hz=1000)
    trigger = triangle.period_start_marker()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger2 = triangle.period_start_marker()
    # -----------------------------------------------------------------------
    assert trigger2 == trigger
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:tri:mark:psta {trigger.value}'
    ]


def test_triangle_trigger_on_internal(qdac):  # noqa
    triangle = qdac.ch01.triangle_wave(frequency_Hz=1000)
    trigger = qdac.allocate_trigger()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    triangle.start_on(trigger)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:tri:trig:sour int{trigger.value}',
        f'sour1:tri:init:cont on',
        'sour1:tri:init'
    ]


def test_triangle_trigger_on_external(qdac):  # noqa
    triangle = qdac.ch01.triangle_wave(frequency_Hz=1000)
    trigger = ExternalInput(1)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    triangle.start_on_external(trigger)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:tri:trig:sour ext{trigger}',
        f'sour1:tri:init:cont on',
        'sour1:tri:init'
    ]
