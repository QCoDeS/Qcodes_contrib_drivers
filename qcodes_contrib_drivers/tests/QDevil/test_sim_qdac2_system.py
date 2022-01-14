import pytest
import re
from .sim_qdac2_fixtures import qdac  # noqa


def test_system_error_all(qdac):  # noqa
    # -----------------------------------------------------------------------
    errors = qdac.errors()
    # -----------------------------------------------------------------------
    assert errors == '0, "No error"'
    assert qdac.get_recorded_scpi_commands() == ['syst:err:all?']


def test_system_error_next(qdac):  # noqa
    # -----------------------------------------------------------------------
    error = qdac.error()
    # -----------------------------------------------------------------------
    assert error == '0, "No error"'
    assert qdac.get_recorded_scpi_commands() == ['syst:err?']


def test_system_error_count(qdac):  # noqa
    # -----------------------------------------------------------------------
    errors = qdac.n_errors()
    # -----------------------------------------------------------------------
    assert errors == 0
    assert qdac.get_recorded_scpi_commands() == ['syst:err:coun?']


def test_system_lan_mac(qdac):  # noqa
    # -----------------------------------------------------------------------
    mac = qdac.mac()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == ['syst:comm:lan:mac?']
    assert re.fullmatch('^([A-Z0-9][A-Z0-9]-)+[A-Z0-9][A-Z0-9]$', mac)
