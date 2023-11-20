import pytest
import re
from .sim_qswitch_fixtures import qswitch  # noqa


def test_idn(qswitch):  # noqa
    # -----------------------------------------------------------------------
    idn_dict = qswitch.IDN()
    # -----------------------------------------------------------------------
    assert idn_dict['vendor'] == 'Quantum Machines'
    assert idn_dict['model'] == 'QSwitch'
    assert re.fullmatch('[0-9]+', idn_dict['serial'])
    assert re.fullmatch('[0-9]+\\.[0-9]+', idn_dict['firmware'])


def test_reset_syncs_and_wait(qswitch, mocker):  # noqa
    sleep_fn = mocker.patch('qcodes_contrib_drivers.drivers.QDevil.QSwitch.sleep_s')
    # -----------------------------------------------------------------------
    qswitch.reset()
    # -----------------------------------------------------------------------
    commands = qswitch.get_recorded_scpi_commands()
    assert commands == ['*rst', 'stat?']
    sleep_fn.assert_any_call(0.6)
