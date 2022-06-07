import pytest
from .sim_qdac2_fixtures import qdac  # noqa
from qcodes_contrib_drivers.drivers.QDevil.QDAC2 import ExternalInput


def test_sweep_explicit(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch10.dc_sweep(
        repetitions=10,
        start_V=-1,
        stop_V=1,
        points=6,
        dwell_s=1e-6,
        backwards=True,
        stepped=True
    )
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour10:dc:trig:sour hold',
        'sour10:volt:mode swe',
        'sour10:swe:star -1',
        'sour10:swe:stop 1',
        'sour10:swe:poin 6',
        'sour10:swe:gen step',
        'sour10:swe:dwel 1e-06',
        'sour10:swe:dir down',
        'sour10:swe:coun 10',
        'sour10:dc:trig:sour bus',
        'sour10:dc:init:cont on',
        'sour10:dc:init',
    ]


def test_sweep_implicit(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch10.dc_sweep(start_V=-2, stop_V=2, points=12)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour10:dc:trig:sour hold',
        'sour10:volt:mode swe',
        'sour10:swe:star -2',
        'sour10:swe:stop 2',
        'sour10:swe:poin 12',
        'sour10:swe:gen step',
        'sour10:swe:dwel 0.001',
        'sour10:swe:dir up',
        'sour10:swe:coun 1',
        'sour10:dc:trig:sour bus',
        'sour10:dc:init:cont on',
        'sour10:dc:init',
    ]


def test_sweep_points(qdac):  # noqa
    dc_sweep = qdac.ch01.dc_sweep(start_V=-2, stop_V=2, points=12)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    points = dc_sweep.points()
    # -----------------------------------------------------------------------
    assert points == 12
    assert qdac.get_recorded_scpi_commands() == ['sour1:swe:poin?']


def test_sweep_remaining(qdac):  # noqa
    dc_sweep = qdac.ch01.dc_sweep(start_V=-2, stop_V=2, points=12)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    dc_sweep.cycles_remaining()
    # -----------------------------------------------------------------------
    # Cannot sim test: assert remaining == 1
    assert qdac.get_recorded_scpi_commands() == ['sour1:swe:ncl?']


def test_sweep_start_without_explicit_trigger(qdac):  # noqa
    dc_sweep = qdac.ch01.dc_sweep(start_V=-1, stop_V=1, points=7)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    dc_sweep.start()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour1:dc:init:cont off',
        'sour1:dc:trig:sour imm',
        'sour1:dc:init'
    ]


def test_sweep_abort(qdac):  # noqa
    dc_sweep = qdac.ch01.dc_sweep(start_V=-2, stop_V=2, points=10)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    dc_sweep.abort()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == ['sour1:dc:abor']


def test_sweep_infinite(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch01.dc_sweep(start_V=-2, stop_V=2, points=10, repetitions=-1)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour1:dc:trig:sour hold',
        'sour1:volt:mode swe',
        'sour1:swe:star -2',
        'sour1:swe:stop 2',
        'sour1:swe:poin 10',
        'sour1:swe:gen step',
        'sour1:swe:dwel 0.001',
        'sour1:swe:dir up',
        'sour1:swe:coun -1',
        'sour1:dc:trig:sour bus',
        'sour1:dc:init:cont on',
        'sour1:dc:init',
    ]


def test_sweep_time(qdac):  # noqa
    dc_sweep = qdac.ch01.dc_sweep(start_V=0, stop_V=1, points=10, dwell_s=1e-3)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    dc_sweep.time_s()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == ['sour1:swe:time?']
    # Cannot sim test: assert seconds == 0.01


def test_sweep_end_marker_alloc(qdac):  # noqa
    qdac._set_up_internal_triggers()
    dc_sweep = qdac.ch01.dc_sweep(start_V=0, stop_V=1, points=10)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger = dc_sweep.end_marker()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [f'sour1:dc:mark:end {trigger.value}']


def test_sweep_end_marker_reuse(qdac):  # noqa
    qdac._set_up_internal_triggers()
    dc_sweep = qdac.ch01.dc_sweep(start_V=0, stop_V=1, points=10)
    trigger = dc_sweep.end_marker()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger2 = dc_sweep.end_marker()
    # -----------------------------------------------------------------------
    assert trigger2 == trigger
    assert qdac.get_recorded_scpi_commands() == [f'sour1:dc:mark:end {trigger.value}']


def test_sweep_start_marker_alloc(qdac):  # noqa
    qdac._set_up_internal_triggers()
    dc_sweep = qdac.ch01.dc_sweep(start_V=0, stop_V=1, points=10)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger = dc_sweep.start_marker()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [f'sour1:dc:mark:star {trigger.value}']


def test_sweep_start_marker_reuse(qdac):  # noqa
    qdac._set_up_internal_triggers()
    dc_sweep = qdac.ch01.dc_sweep(start_V=0, stop_V=1, points=10)
    trigger = dc_sweep.start_marker()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger2 = dc_sweep.start_marker()
    # -----------------------------------------------------------------------
    assert trigger2 == trigger
    assert qdac.get_recorded_scpi_commands() == [f'sour1:dc:mark:star {trigger.value}']


def test_sweep_start_trigger_fires(qdac):  # noqa
    dc_sweep = qdac.ch01.dc_sweep(start_V=0, stop_V=1, points=10)
    trigger = qdac.allocate_trigger()
    dc_sweep.start_on(trigger)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    dc_sweep.start()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour1:dc:init:cont on',
        'sour1:dc:init',
        f'tint {trigger.value}'
    ]


def test_sweep_step_end_trigger_alloc(qdac):  # noqa
    qdac._set_up_internal_triggers()
    dc_sweep = qdac.ch01.dc_sweep(start_V=0, stop_V=1, points=10)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger = dc_sweep.step_end_marker()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [f'sour1:dc:mark:send {trigger.value}']


def test_sweep_step_end_trigger_reuse(qdac):  # noqa
    qdac._set_up_internal_triggers()
    dc_sweep = qdac.ch01.dc_sweep(start_V=0, stop_V=1, points=10)
    trigger = dc_sweep.step_end_marker()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger2 = dc_sweep.step_end_marker()
    # -----------------------------------------------------------------------
    assert trigger2 == trigger
    assert qdac.get_recorded_scpi_commands() == [f'sour1:dc:mark:send {trigger.value}']


def test_sweep_step_start_trigger_alloc(qdac):  # noqa
    qdac._set_up_internal_triggers()
    dc_sweep = qdac.ch01.dc_sweep(start_V=0, stop_V=1, points=10)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger = dc_sweep.step_start_marker()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [f'sour1:dc:mark:sst {trigger.value}']


def test_sweep_step_start_trigger_reuse(qdac):  # noqa
    qdac._set_up_internal_triggers()
    dc_sweep = qdac.ch01.dc_sweep(start_V=0, stop_V=1, points=10)
    trigger = dc_sweep.step_start_marker()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger2 = dc_sweep.step_start_marker()
    # -----------------------------------------------------------------------
    assert trigger2 == trigger
    assert qdac.get_recorded_scpi_commands() == [f'sour1:dc:mark:sst {trigger.value}']


def test_sweep_trigger_on_internal(qdac):  # noqa
    dc_sweep = qdac.ch01.dc_sweep(start_V=0, stop_V=1, points=10)
    trigger = qdac.allocate_trigger()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    dc_sweep.start_on(trigger)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:dc:trig:sour int{trigger.value}',
        f'sour1:dc:init:cont on',
        'sour1:dc:init'
    ]


def test_sweep_trigger_on_external(qdac):  # noqa
    dc_sweep = qdac.ch01.dc_sweep(start_V=0, stop_V=1, points=10)
    trigger = ExternalInput(1)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    dc_sweep.start_on_external(trigger)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:dc:trig:sour ext{trigger}',
        f'sour1:dc:init:cont on',
        'sour1:dc:init'
    ]


def test_sweep_get_start(qdac):  # noqa
    dc_sweep = qdac.ch01.dc_sweep(start_V=-1.2345, stop_V=1.2345, points=3)
    # -----------------------------------------------------------------------
    voltage = dc_sweep.start_V()
    # -----------------------------------------------------------------------
    assert voltage == -1.2345


def test_sweep_get_stop(qdac):  # noqa
    dc_sweep = qdac.ch01.dc_sweep(start_V=-1.2345, stop_V=1.2345, points=3)
    # -----------------------------------------------------------------------
    voltage = dc_sweep.stop_V()
    # -----------------------------------------------------------------------
    assert voltage == 1.2345


def test_sweep_get_voltages(qdac):  # noqa
    dc_sweep = qdac.ch01.dc_sweep(start_V=-1.23, stop_V=1.23, points=3)
    # -----------------------------------------------------------------------
    voltages = dc_sweep.values_V()
    # -----------------------------------------------------------------------
    assert voltages == [-1.23, 0, 1.23]
