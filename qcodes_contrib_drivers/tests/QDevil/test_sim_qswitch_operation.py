import pytest
from unittest.mock import call
from .sim_qswitch_fixtures import qswitch  # noqa


@pytest.mark.wip
def test_unground_by_name(qswitch):  # noqa
    # -----------------------------------------------------------------------
    qswitch.unground('15')
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['open (@15!0)']


@pytest.mark.wip
def test_ground_by_name(qswitch):  # noqa
    qswitch.unground('15')
    qswitch.start_recording_scpi()
    # -----------------------------------------------------------------------
    qswitch.ground('15')
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['clos (@15!0)']


@pytest.mark.wip
def test_unground_by_names(qswitch):  # noqa
    # -----------------------------------------------------------------------
    qswitch.unground(['15', '14'])
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['open (@14!0:15!0)']


@pytest.mark.wip
def test_ground_by_names(qswitch):  # noqa
    qswitch.unground(['15', '14'])
    qswitch.start_recording_scpi()
    # -----------------------------------------------------------------------
    qswitch.ground(['15', '14'])
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['clos (@14!0:15!0)']


@pytest.mark.wip
def test_connect_by_name(qswitch):  # noqa
    # -----------------------------------------------------------------------
    qswitch.connect('15')
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['clos (@15!9)']


@pytest.mark.wip
def test_disconnect_by_name(qswitch):  # noqa
    qswitch.connect('15')
    qswitch.start_recording_scpi()
    # -----------------------------------------------------------------------
    qswitch.disconnect('15')
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['open (@15!9)']


@pytest.mark.wip
def test_connect_by_names(qswitch):  # noqa
    # -----------------------------------------------------------------------
    qswitch.connect(['15', '14'])
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['clos (@14!9:15!9)']


@pytest.mark.wip
def test_disconnect_by_names(qswitch):  # noqa
    qswitch.connect(['15', '14'])
    qswitch.start_recording_scpi()
    # -----------------------------------------------------------------------
    qswitch.disconnect(['15', '14'])
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['open (@14!9:15!9)']


@pytest.mark.wip
def test_break_out_by_name(qswitch):  # noqa
    # -----------------------------------------------------------------------
    qswitch.breakout('22', '7')
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['clos (@22!7)']


@pytest.mark.wip
def test_unbreak_out_by_name(qswitch):  # noqa
    qswitch.breakout('22', '7')
    qswitch.start_recording_scpi()
    # -----------------------------------------------------------------------
    qswitch.unbreakout('22', '7')
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['open (@22!7)']


@pytest.mark.wip
def test_arrangement_gives_names_to_connections(qswitch):  # noqa
    # -----------------------------------------------------------------------
    qswitch.arrange(
        breakouts={'DMM': 2, 'VNA': 1},
        lines={'plunger': 14, 'sensor': 3}
    )
    qswitch.breakout('plunger', 'VNA')
    qswitch.unground('sensor')
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['clos (@14!1)', 'open (@3!0)']
