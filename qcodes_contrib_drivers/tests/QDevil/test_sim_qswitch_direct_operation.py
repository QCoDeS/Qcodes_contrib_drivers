import pytest
from .common import assert_items_equal
from .sim_qswitch_fixtures import qswitch  # noqa


def test_cached_state_can_be_updated(qswitch):  # noqa
    # -----------------------------------------------------------------------
    qswitch.state_force_update()
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['stat?']


def test_get_state(qswitch):  # noqa
    # -----------------------------------------------------------------------
    state = qswitch.state()
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['stat?']
    assert state == '(@1!0:24!0)'


def test_set_state_changes_the_state(qswitch, mocker):  # noqa
    mocker.patch.object(qswitch, 'state_force_update')
    # -----------------------------------------------------------------------
    qswitch.closed_relays(
        [(24, 8), (24, 8), (22, 7), (20, 6), (1, 9), (2, 0)])
    # -----------------------------------------------------------------------
    assert qswitch.state() == '(@2!0,20!6,22!7,24!8,1!9)'


def test_set_state_only_sends_diff(qswitch):  # noqa
    # -----------------------------------------------------------------------
    qswitch.closed_relays(
        [(24, 8), (24, 8), (22, 7), (20, 6), (1, 9), (2, 0)])
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == [
        'clos (@20!6,22!7,24!8,1!9)',
        'open (@1!0,3!0:24!0)'
    ]


def test_set_state_ignores_empty_diff(qswitch):  # noqa
    qswitch.closed_relays(
        [(24, 8), (24, 8), (22, 7), (20, 6), (1, 9), (2, 0)])
    qswitch.start_recording_scpi()
    # -----------------------------------------------------------------------
    qswitch.closed_relays([(24, 8), (22, 7), (20, 6), (1, 9), (2, 0)])
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == []


def test_states_are_sanitised(qswitch, mocker):  # noqa
    mocker.patch.object(qswitch, 'state_force_update')
    # -----------------------------------------------------------------------
    qswitch.closed_relays(
        [(24, 8), (22, 7), (20, 6), (1, 9), (2, 0), (24, 8), (20, 6)])
    # -----------------------------------------------------------------------
    assert_items_equal(
        qswitch.closed_relays(),
        [(1, 9), (2, 0), (20, 6), (22, 7), (24, 8)]
    )


def test_individual_relays_can_be_closed(qswitch):  # noqa
    # -----------------------------------------------------------------------
    qswitch.close_relays([(14, 1), (22, 7)])
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['clos (@14!1,22!7)']


def test_individual_relay_can_be_closed(qswitch):  # noqa
    # -----------------------------------------------------------------------
    qswitch.close_relay(22, 7)
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['clos (@22!7)']


def test_individual_relays_can_be_opened(qswitch):  # noqa
    # -----------------------------------------------------------------------
    qswitch.open_relays([(14, 0), (22, 0), (1, 1)])
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['open (@14!0,22!0)']


def test_individual_relay_can_be_opened(qswitch):  # noqa
    # -----------------------------------------------------------------------
    qswitch.open_relay(14, 0)
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['open (@14!0)']


def test_beeper_can_be_turned_on(qswitch):  # noqa
    # -----------------------------------------------------------------------
    qswitch.error_indicator('on')
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['beep:stat on']


def test_beeper_can_be_turned_off(qswitch):  # noqa
    # -----------------------------------------------------------------------
    qswitch.error_indicator('off')
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['beep:stat off']


def test_beeper_state_can_be_queried(qswitch):  # noqa
    # -----------------------------------------------------------------------
    state = qswitch.error_indicator()
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['beep:stat?']
    assert state == 'off'


def test_autosave_can_be_turned_on(qswitch):  # noqa
    # -----------------------------------------------------------------------
    qswitch.auto_save('on')
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['aut on']


def test_autosave_can_be_turned_off(qswitch):  # noqa
    # -----------------------------------------------------------------------
    qswitch.auto_save('off')
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['aut off']


def test_autosave_state_can_be_queried(qswitch):  # noqa
    # -----------------------------------------------------------------------
    state = qswitch.auto_save()
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['aut?']
    assert state == 'off'
