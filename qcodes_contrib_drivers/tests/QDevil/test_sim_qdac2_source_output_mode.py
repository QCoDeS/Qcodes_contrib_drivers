import pytest
from .sim_qdac2_fixtures import qdac  # noqa


def test_output_mode_defaults(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch02.output_mode()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour2:rang high',
        'sour2:filt high',
        'sour2:ilim:low 2e-07',
        'sour2:ilim:high 0.01',
    ]


def test_output_mode_arg(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch02.output_mode(
        range='low',
        filter='dc',
        low_current_limit_A=50e-12,
        high_current_limit_A=0.00001
    )
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour2:rang low',
        'sour2:filt dc',
        'sour2:ilim:low 5e-11',
        'sour2:ilim:high 1e-05',
    ]
