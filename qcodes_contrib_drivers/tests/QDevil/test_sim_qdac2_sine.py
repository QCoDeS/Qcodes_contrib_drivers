import pytest
from .sim_qdac2_fixtures import qdac  # noqa
from qcodes_contrib_drivers.drivers.QDevil.QDAC2 import ExternalInput


def test_sine_ambiguous(qdac):  # noqa
    # -----------------------------------------------------------------------
    with pytest.raises(ValueError) as error:
        qdac.ch01.sine_wave(period_s=1, frequency_Hz=10)
    # -----------------------------------------------------------------------
    assert 'frequency_Hz or period_s can be specified' in repr(error)


def test_sine_default_vaules(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch01.sine_wave()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour1:sin:trig:sour hold',
        'sour1:sin:freq 1000',
        'sour1:sin:pol norm',
        'sour1:sin:span 0.2',
        'sour1:sin:offs 0.0',
        'sour1:sin:slew inf',
        'sour1:sin:coun -1',
        'sour1:sin:trig:sour bus',
        'sour1:sin:init:cont on',
        'sour1:sin:init',
    ]


def test_sine_period(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch01.sine_wave(
        period_s=11,
        inverted=True,
        span_V=1,
        offset_V=-0.1,
        slew_V_s=1,
        repetitions=10
    )
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour1:sin:trig:sour hold',
        'sour1:sin:per 11',
        'sour1:sin:pol inv',
        'sour1:sin:span 1',
        'sour1:sin:offs -0.1',
        'sour1:sin:slew 1',
        'sour1:sin:coun 10',
        'sour1:sin:trig:sour bus',
        'sour1:sin:init:cont on',
        'sour1:sin:init',
    ]


def test_sine_frequency(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch01.sine_wave(frequency_Hz=1e5)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour1:sin:trig:sour hold',
        'sour1:sin:freq 100000.0',
        'sour1:sin:pol norm',
        'sour1:sin:span 0.2',
        'sour1:sin:offs 0.0',
        'sour1:sin:slew inf',
        'sour1:sin:coun -1',
        'sour1:sin:trig:sour bus',
        'sour1:sin:init:cont on',
        'sour1:sin:init',
    ]


def test_sine_start_without_explicit_trigger(qdac):  # noqa
    sine = qdac.ch24.sine_wave()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    sine.start()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour24:sin:init:cont off',
        'sour24:sin:trig:sour imm',
        'sour24:sin:init'
    ]


def test_sine_abort(qdac):  # noqa
    sine = qdac.ch01.sine_wave()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    sine.abort()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == ['sour1:sin:abor']


def test_sine_remaining(qdac):  # noqa
    sine = qdac.ch01.sine_wave(repetitions=10)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    sine.cycles_remaining()
    # -----------------------------------------------------------------------
    # Cannot sim test: assert remaining == 1
    assert qdac.get_recorded_scpi_commands() == ['sour1:sin:ncl?']


def test_sine_end_marker_alloc(qdac):  # noqa
    qdac._set_up_internal_triggers()
    sine = qdac.ch01.sine_wave(frequency_Hz=1000)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger = sine.end_marker()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:sin:mark:end {trigger.value}'
    ]


def test_sine_end_marker_reuse(qdac):  # noqa
    qdac._set_up_internal_triggers()
    sine = qdac.ch01.sine_wave(frequency_Hz=1000)
    trigger = sine.end_marker()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger2 = sine.end_marker()
    # -----------------------------------------------------------------------
    assert trigger2 == trigger
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:sin:mark:end {trigger.value}'
    ]


def test_sine_start_marker_alloc(qdac):  # noqa
    qdac._set_up_internal_triggers()
    sine = qdac.ch01.sine_wave(frequency_Hz=1000)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger = sine.start_marker()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:sin:mark:star {trigger.value}'
    ]


def test_sine_start_marker_reuse(qdac):  # noqa
    qdac._set_up_internal_triggers()
    sine = qdac.ch01.sine_wave(frequency_Hz=1000)
    trigger = sine.start_marker()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger2 = sine.start_marker()
    # -----------------------------------------------------------------------
    assert trigger2 == trigger
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:sin:mark:star {trigger.value}'
    ]


def test_sine_start_trigger_fires(qdac):  # noqa
    qdac._set_up_internal_triggers()
    sine = qdac.ch01.sine_wave(frequency_Hz=1000)
    trigger = qdac.allocate_trigger()
    sine.start_on(trigger)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    sine.start()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour1:sin:init:cont on',
        'sour1:sin:init',
        f'tint {trigger.value}'
    ]


def test_sine_period_end_trigger_alloc(qdac):  # noqa
    qdac._set_up_internal_triggers()
    sine = qdac.ch01.sine_wave(frequency_Hz=1000)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger = sine.period_end_marker()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:sin:mark:pend {trigger.value}'
    ]


def test_sine_period_end_trigger_reuse(qdac):  # noqa
    qdac._set_up_internal_triggers()
    sine = qdac.ch01.sine_wave(frequency_Hz=1000)
    trigger = sine.period_end_marker()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger2 = sine.period_end_marker()
    # -----------------------------------------------------------------------
    assert trigger2 == trigger
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:sin:mark:pend {trigger.value}'
    ]


def test_sine_period_start_trigger_alloc(qdac):  # noqa
    qdac._set_up_internal_triggers()
    sine = qdac.ch01.sine_wave(frequency_Hz=1000)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger = sine.period_start_marker()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:sin:mark:psta {trigger.value}'
    ]


def test_sine_period_start_trigger_reuse(qdac):  # noqa
    qdac._set_up_internal_triggers()
    sine = qdac.ch01.sine_wave(frequency_Hz=1000)
    trigger = sine.period_start_marker()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger2 = sine.period_start_marker()
    # -----------------------------------------------------------------------
    assert trigger2 == trigger
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:sin:mark:psta {trigger.value}'
    ]


def test_sine_trigger_on_internal(qdac):  # noqa
    sine = qdac.ch01.sine_wave(frequency_Hz=1000)
    trigger = qdac.allocate_trigger()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    sine.start_on(trigger)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:sin:trig:sour int{trigger.value}',
        f'sour1:sin:init:cont on',
        'sour1:sin:init'
    ]


def test_sine_trigger_on_external(qdac):  # noqa
    sine = qdac.ch01.sine_wave(frequency_Hz=1000)
    trigger = ExternalInput(1)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    sine.start_on_external(trigger)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:sin:trig:sour ext{trigger}',
        f'sour1:sin:init:cont on',
        'sour1:sin:init'
    ]
