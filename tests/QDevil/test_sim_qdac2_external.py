import pytest
from .sim_qdac2_fixtures import qdac  # noqa


def test_external_outputs_available(qdac):  # noqa
    # -----------------------------------------------------------------------
    ntriggers = qdac.n_external_outputs()
    # -----------------------------------------------------------------------
    assert ntriggers == 5


def test_external_inputs_available(qdac):  # noqa
    # -----------------------------------------------------------------------
    ntriggers = qdac.n_external_inputs()
    # -----------------------------------------------------------------------
    assert ntriggers == 4


def test_external_output_from_trigger(qdac):  # noqa
    trigger = qdac.allocate_trigger()
    # -----------------------------------------------------------------------
    qdac.ext2.source_from_trigger(trigger)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'outp:trig2:sour int{trigger.value}'
    ]


def test_external_output_from_bus(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ext5.source_from_bus()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == ['outp:trig5:sour bus']


def test_external_output_from_input(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ext2.source_from_input(4)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == ['outp:trig2:sour ext4']


def test_external_output_width(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ext2.width_s(1e-4)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == ['outp:trig2:widt 0.0001']


def test_external_output_width_q(qdac):  # noqa
    qdac.ext2.width_s(1e-3)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    width = qdac.ext2.width_s()
    # -----------------------------------------------------------------------
    assert width == 0.001
    assert qdac.get_recorded_scpi_commands() == ['outp:trig2:widt?']


@pytest.mark.parametrize('polarity', ('inv', 'norm'))
def test_external_output_polarity(polarity, qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ext2.polarity(polarity)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'outp:trig2:pol {polarity}'
    ]


def test_external_output_polarity_q(qdac):  # noqa
    qdac.ext2.polarity('norm')
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    polarity = qdac.ext2.polarity()
    # -----------------------------------------------------------------------
    assert polarity == 'norm'
    assert qdac.get_recorded_scpi_commands() == ['outp:trig2:pol?']


def test_external_output_delay(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ext2.delay_s(1e-3)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == ['outp:trig2:del 0.001']


def test_external_output_delay_q(qdac):  # noqa
    qdac.ext2.delay_s(1e-4)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    delay = qdac.ext2.delay_s()
    # -----------------------------------------------------------------------
    assert delay == 0.0001
    assert qdac.get_recorded_scpi_commands() == ['outp:trig2:del?']


def test_external_output_signal(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ext2.signal()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == ['outp:trig2:sign']
