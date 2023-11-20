import pytest
from .sim_qswitch_fixtures import qswitch  # noqa


def test_unknown_line_name_gives_error(qswitch):  # noqa
    # -----------------------------------------------------------------------
    with pytest.raises(ValueError) as error:
        qswitch.breakout('plunger', '1')
    # -----------------------------------------------------------------------
    assert 'Unknown line' in repr(error)


def test_unknown_tap_name_gives_error(qswitch):  # noqa
    # -----------------------------------------------------------------------
    with pytest.raises(ValueError) as error:
        qswitch.breakout('1', 'VNA')
    # -----------------------------------------------------------------------
    assert 'Unknown tap' in repr(error)
