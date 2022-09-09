import pytest
import re
from .real_qdac2_fixtures import (  # noqa
    qdac, instrument_connected, not_implemented)


@instrument_connected
def test_idn(qdac):  # noqa
    # -----------------------------------------------------------------------
    idn_dict = qdac.IDN()
    # -----------------------------------------------------------------------
    assert idn_dict['vendor'] == 'QDevil'
    assert idn_dict['model'] == 'QDAC-II'
    assert re.fullmatch('[0-9]+', idn_dict['serial'])
    assert re.fullmatch('[0-9]+-[0-9]+\\.[0-9]+(\\.[0-9]+)?', idn_dict['firmware'])


@instrument_connected
def test_abort(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.abort()
    # -----------------------------------------------------------------------
    commands = qdac.get_recorded_scpi_commands()
    assert commands == ['abor']


@instrument_connected
def test_reset(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.reset()
    # -----------------------------------------------------------------------
    commands = qdac.get_recorded_scpi_commands()
    assert commands == ['*rst']


@instrument_connected
def test_manual_trigger(qdac):  # noqa
    trigger = qdac.allocate_trigger()
    # -----------------------------------------------------------------------
    qdac.trigger(trigger)
    # -----------------------------------------------------------------------
    commands = qdac.get_recorded_scpi_commands()
    assert commands == [f'tint {trigger.value}']
