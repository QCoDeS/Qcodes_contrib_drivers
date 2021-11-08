import pytest
import re
from .sim_qdac2_fixtures import qdac  # noqa


def test_idn(qdac):  # noqa
    # -----------------------------------------------------------------------
    idn_dict = qdac.IDN()
    # -----------------------------------------------------------------------
    assert idn_dict['vendor'] == 'QDevil'
    assert idn_dict['model'] == 'QDAC-II'
    assert re.fullmatch('[A-Z]+[0-9]+', idn_dict['serial'])
    assert re.fullmatch('[0-9]+-[0-9]+\\.[0-9]+\\.[0-9]+', idn_dict['firmware'])


def test_abort(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.abort()
    # -----------------------------------------------------------------------
    commands = qdac.get_recorded_scpi_commands()
    assert commands == ['abor']


def test_reset(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.reset()
    # -----------------------------------------------------------------------
    commands = qdac.get_recorded_scpi_commands()
    assert commands == ['*rst']


def test_internal_trigger(qdac):  # noqa
    trigger = qdac.allocate_trigger()
    # -----------------------------------------------------------------------
    qdac.trigger(trigger)
    # -----------------------------------------------------------------------
    commands = qdac.get_recorded_scpi_commands()
    assert commands == [f'tint {trigger.value}']


def test_bus_trigger(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.start_all()
    # -----------------------------------------------------------------------
    commands = qdac.get_recorded_scpi_commands()
    assert commands == ['*trg']
