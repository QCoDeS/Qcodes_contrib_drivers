import pytest
from .sim_qdac2_fixtures import qdac  # noqa


def test_channels_available(qdac):  # noqa
    # -----------------------------------------------------------------------
    nchannels = qdac.n_channels()
    # -----------------------------------------------------------------------
    assert nchannels == 24


@pytest.mark.parametrize('channel', [1, 24])
def test_channel_voltage_range(channel, qdac):  # noqa
    # -----------------------------------------------------------------------
    getattr(qdac, f'ch{channel:02}').output_range('low')
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [f'sour{channel}:rang low']


@pytest.mark.parametrize('channel', [2, 23])
def test_channel_abort(channel, qdac):  # noqa
    # -----------------------------------------------------------------------
    getattr(qdac, f'ch{channel:02}').abort()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [f'sour{channel}:all:abor']


def test_channel_context(qdac):  # noqa
    # -----------------------------------------------------------------------
    channel = qdac.channel(8)
    # -----------------------------------------------------------------------
    channel.dc_constant_V(0.5)
