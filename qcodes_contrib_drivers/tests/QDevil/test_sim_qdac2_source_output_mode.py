from .sim_qdac2_fixtures import qdac  # noqa


def test_output_mode_defaults(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch02.output_mode()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour2:rang high',
        'sour2:filt high',
    ]


def test_output_mode_arg(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch02.output_mode(
        range='low',
        filter='dc',
    )
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour2:rang low',
        'sour2:filt dc',
    ]
