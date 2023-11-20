import pytest
from unittest.mock import call
from .sim_qswitch_fixtures import qswitch  # noqa


def test_ground_by_name(qswitch):  # noqa
    qswitch.close_relay(15, 9)
    qswitch.open_relay(15, 0)
    qswitch.start_recording_scpi()
    # -----------------------------------------------------------------------
    qswitch.ground('15')
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['clos (@15!0)', 'open (@15!9)']


def test_ground_by_names(qswitch):  # noqa
    qswitch.close_relay(14, 9)
    qswitch.open_relay(14, 0)
    qswitch.close_relay(15, 9)
    qswitch.open_relay(15, 0)
    qswitch.start_recording_scpi()
    # -----------------------------------------------------------------------
    qswitch.ground(['15', '14'])
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['clos (@14!0:15!0)', 'open (@14!9:15!9)']


def test_connect_by_name(qswitch):  # noqa
    # -----------------------------------------------------------------------
    qswitch.connect('15')
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['clos (@15!9)', 'open (@15!0)']


def test_connect_by_names(qswitch):  # noqa
    # -----------------------------------------------------------------------
    qswitch.connect(['14', '15'])
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['clos (@14!9:15!9)', 'open (@14!0:15!0)']


def test_breakout_by_name(qswitch):  # noqa
    # -----------------------------------------------------------------------
    qswitch.breakout('22', '7')
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['clos (@22!7)', 'open (@22!0)']


def test_arrangement_gives_names_to_connections(qswitch):  # noqa
    # -----------------------------------------------------------------------
    qswitch.arrange(
        breakouts={'DMM': 2, 'VNA': 1},
        lines={'plunger': 14, 'sensor': 3}
    )
    qswitch.breakout('plunger', 'VNA')
    qswitch.connect('sensor')
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == [
        'clos (@14!1)', 'open (@14!0)',
        'clos (@3!9)', 'open (@3!0)']


def test_ground_disconnects_everything(qswitch):  # noqa
    qswitch.close_relay(15, 9)
    qswitch.close_relay(15, 1)
    qswitch.open_relay(15, 0)
    qswitch.start_recording_scpi()
    # -----------------------------------------------------------------------
    qswitch.ground('15')
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['clos (@15!0)', 'open (@15!1,15!9)']


def test_ground_disconnects_multiple(qswitch):  # noqa
    qswitch.close_relay(14, 9)
    qswitch.close_relay(14, 1)
    qswitch.open_relay(14, 0)
    qswitch.close_relay(15, 9)
    qswitch.close_relay(15, 1)
    qswitch.open_relay(15, 0)
    qswitch.start_recording_scpi()
    # -----------------------------------------------------------------------
    qswitch.ground(['15', '14'])
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['clos (@14!0:15!0)', 'open (@14!1:15!1,14!9:15!9)']

