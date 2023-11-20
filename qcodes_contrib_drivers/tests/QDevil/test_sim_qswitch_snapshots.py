import pytest
from .sim_qswitch_fixtures import qswitch  # noqa


def test_initial_state_is_recorded_in_snapshot(qswitch):  # noqa
    # -----------------------------------------------------------------------
    snapshot = qswitch.snapshot(True)
    # -----------------------------------------------------------------------
    relays = snapshot['parameters']['state']['value']
    assert relays == '(@1!0:24!0)'


def test_state_change_is_recorded_in_snapshot(qswitch):  # noqa
    # -----------------------------------------------------------------------
    qswitch.closed_relays([(24,8), (22,7), (20,6), (1,9), (2,0)])
    snapshot = qswitch.snapshot()
    # -----------------------------------------------------------------------
    relays = snapshot['parameters']['state']['value']
    assert relays == '(@2!0,20!6,22!7,24!8,1!9)'
