import pytest
from .sim_qdac2_fixtures import qdac  # noqa
from qcodes_contrib_drivers.drivers.QDevil.QDAC2 import ExternalInput


def test_list_explicit(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch01.dc_list(
        repetitions=10,
        voltages=[-1, 0, 1],
        dwell_s=1e-6,
        backwards=True,
        stepped=True
    )
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour1:dc:trig:sour hold',
        'sour1:volt:mode list',
        'sour1:list:volt -1,0,1',
        'sour1:list:tmod step',
        'sour1:list:dwel 1e-06',
        'sour1:list:dir down',
        'sour1:list:coun 10',
        'sour1:dc:trig:sour bus',
        'sour1:dc:init:cont on',
        'sour1:dc:init',
    ]


def test_list_implicit(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch01.dc_list(voltages=range(1, 5))
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour1:dc:trig:sour hold',
        'sour1:volt:mode list',
        'sour1:list:volt 1,2,3,4',
        'sour1:list:tmod auto',
        'sour1:list:dwel 0.001',
        'sour1:list:dir up',
        'sour1:list:coun 1',
        'sour1:dc:trig:sour bus',
        'sour1:dc:init:cont on',
        'sour1:dc:init',
    ]


def test_list_points(qdac):  # noqa
    dc_list = qdac.ch01.dc_list(voltages=range(1, 5))
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    dc_list.points()
    # -----------------------------------------------------------------------
    # Cannot sim test: assert points == 4
    assert qdac.get_recorded_scpi_commands() == ['sour1:list:poin?']


def test_list_remaining(qdac):  # noqa
    dc_list = qdac.ch01.dc_list(voltages=range(1, 5))
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    dc_list.cycles_remaining()
    # -----------------------------------------------------------------------
    # Cannot sim test: assert remaining == 1
    assert qdac.get_recorded_scpi_commands() == ['sour1:list:ncl?']


def test_list_append(qdac):  # noqa
    dc_list = qdac.ch01.dc_list(voltages=range(1, 5))
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    dc_list.append(range(5, 7))
    # -----------------------------------------------------------------------
    # Cannot sim test: assert points == 6
    assert qdac.get_recorded_scpi_commands() == [
        'sour1:list:volt:app 5,6',
        'sour1:dc:init:cont on',
        'sour1:dc:init',
    ]


def test_list_start_without_explicit_trigger(qdac):  # noqa
    dc_list = qdac.ch01.dc_list(voltages=range(1, 5))
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    dc_list.start()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour1:dc:init:cont off',
        'sour1:dc:trig:sour imm',
        'sour1:dc:init'
    ]


def test_list_abort(qdac):  # noqa
    dc_list = qdac.ch01.dc_list(voltages=range(1, 5))
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    dc_list.abort()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == ['sour1:dc:abor']


def test_list_infinite(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch01.dc_list(voltages=range(1, 5), repetitions=-1)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour1:dc:trig:sour hold',
        'sour1:volt:mode list',
        'sour1:list:volt 1,2,3,4',
        'sour1:list:tmod auto',
        'sour1:list:dwel 0.001',
        'sour1:list:dir up',
        'sour1:list:coun -1',
        'sour1:dc:trig:sour bus',
        'sour1:dc:init:cont on',
        'sour1:dc:init',
    ]


def test_list_end_marker_alloc(qdac):  # noqa
    qdac._set_up_internal_triggers()
    dc_list = qdac.ch01.dc_list(voltages=range(1, 5))
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger = dc_list.end_marker()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [f'sour1:dc:mark:end {trigger.value}']


def test_list_end_marker_reuse(qdac):  # noqa
    qdac._set_up_internal_triggers()
    dc_list = qdac.ch01.dc_list(voltages=range(1, 5))
    trigger = dc_list.end_marker()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger2 = dc_list.end_marker()
    # -----------------------------------------------------------------------
    assert trigger2 == trigger
    assert qdac.get_recorded_scpi_commands() == [f'sour1:dc:mark:end {trigger.value}']


def test_list_start_marker_alloc(qdac):  # noqa
    qdac._set_up_internal_triggers()
    dc_list = qdac.ch01.dc_list(voltages=range(1, 5))
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger = dc_list.start_marker()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [f'sour1:dc:mark:star {trigger.value}']


def test_list_start_marker_reuse(qdac):  # noqa
    qdac._set_up_internal_triggers()
    dc_list = qdac.ch01.dc_list(voltages=range(1, 5))
    trigger = dc_list.start_marker()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger2 = dc_list.start_marker()
    # -----------------------------------------------------------------------
    assert trigger2 == trigger
    assert qdac.get_recorded_scpi_commands() == [f'sour1:dc:mark:star {trigger.value}']


def test_list_start_trigger_fires(qdac):  # noqa
    dc_list = qdac.ch01.dc_list(voltages=range(1, 5))
    trigger = qdac.allocate_trigger()
    dc_list.start_on(trigger)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    dc_list.start()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour1:dc:init:cont on',
        'sour1:dc:init',
        f'tint {trigger.value}'
    ]


def test_list_step_end_trigger_alloc(qdac):  # noqa
    qdac._set_up_internal_triggers()
    dc_list = qdac.ch01.dc_list(voltages=range(1, 5))
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger = dc_list.step_end_marker()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [f'sour1:dc:mark:send {trigger.value}']


def test_list_step_end_trigger_reuse(qdac):  # noqa
    qdac._set_up_internal_triggers()
    dc_list = qdac.ch01.dc_list(voltages=range(1, 5))
    trigger = dc_list.step_end_marker()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger2 = dc_list.step_end_marker()
    # -----------------------------------------------------------------------
    assert trigger2 == trigger
    assert qdac.get_recorded_scpi_commands() == [f'sour1:dc:mark:send {trigger.value}']


def test_list_step_start_trigger_alloc(qdac):  # noqa
    qdac._set_up_internal_triggers()
    dc_list = qdac.ch01.dc_list(voltages=range(1, 5))
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger = dc_list.step_start_marker()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [f'sour1:dc:mark:sst {trigger.value}']


def test_list_step_start_trigger_reuse(qdac):  # noqa
    qdac._set_up_internal_triggers()
    dc_list = qdac.ch01.dc_list(voltages=range(1, 5))
    trigger = dc_list.step_start_marker()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    trigger2 = dc_list.step_start_marker()
    # -----------------------------------------------------------------------
    assert trigger2 == trigger
    assert qdac.get_recorded_scpi_commands() == [f'sour1:dc:mark:sst {trigger.value}']


def test_list_trigger_on_internal(qdac):  # noqa
    dc_list = qdac.ch01.dc_list(voltages=range(1, 5))
    trigger = qdac.allocate_trigger()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    dc_list.start_on(trigger)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:dc:trig:sour int{trigger.value}',
        f'sour1:dc:init:cont on',
        'sour1:dc:init'
    ]


def test_list_trigger_on_external(qdac):  # noqa
    dc_list = qdac.ch01.dc_list(voltages=range(1, 5))
    trigger = ExternalInput(1)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    dc_list.start_on_external(trigger)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sour1:dc:trig:sour ext{trigger}',
        f'sour1:dc:init:cont on',
        'sour1:dc:init'
    ]


def test_list_get_voltages(qdac):  # noqa
    dc_list = qdac.ch01.dc_list(voltages=[-0.123, 0, 1.234])
    # -----------------------------------------------------------------------
    voltages = dc_list.values_V()
    # -----------------------------------------------------------------------
    assert voltages == [-0.123, 0, 1.234]


# def test_list_internal_trigger(qdac):  # noqa
#     trigger = qdac.allocate_trigger()
#     # -----------------------------------------------------------------------
#     qdac.ch01.dc_list(voltages=range(1, 5), start_on=trigger)
#     # -----------------------------------------------------------------------
#     assert qdac.get_recorded_scpi_commands() == [
#         'sour1:dc:trig:sour hold',
#         'sour1:volt:mode list',
#         'sour1:list:volt 1, 2, 3, 4',
#         'sour1:list:tmod auto',
#         'sour1:list:dwel 0.001',
#         'sour1:list:dir up',
#         'sour1:list:coun 1',
#         'sour1:dc:init:cont off',
#         f'sour1:dc:trig:sour int{trigger.value}',
#         'sour1:dc:init',
#     ]
