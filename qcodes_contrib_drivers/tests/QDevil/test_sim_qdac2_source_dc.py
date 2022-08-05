import pytest
from .sim_qdac2_fixtures import qdac  # noqa


@pytest.mark.parametrize('range', ['low', 'high'])
def test_select_voltage_range(range, qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch02.output_range(range)
    r = qdac.ch02.output_range()
    # -----------------------------------------------------------------------
    assert r == range
    assert qdac.get_recorded_scpi_commands() == [
        f'sour2:rang {range}',
        'sour2:rang?'
    ]


def test_select_invalid_voltage_range(qdac):  # noqa
    # -----------------------------------------------------------------------
    with pytest.raises(ValueError) as error:
        qdac.ch02.output_range('med')
    # -----------------------------------------------------------------------
    assert "'med' is not in" in repr(error)
    assert "'low'" in repr(error)
    assert "'high'" in repr(error)


def test_voltage_range_low_min(qdac):  # noqa
    # -----------------------------------------------------------------------
    voltage = qdac.ch02.output_low_range_minimum_V()
    # -----------------------------------------------------------------------
    assert -10 < voltage < 10
    assert qdac.get_recorded_scpi_commands() == [f'sour2:rang:low:min?']


def test_voltage_range_low_max(qdac):  # noqa
    # -----------------------------------------------------------------------
    voltage = qdac.ch02.output_low_range_maximum_V()
    # -----------------------------------------------------------------------
    assert -10 < voltage < 10
    assert qdac.get_recorded_scpi_commands() == [f'sour2:rang:low:max?']


def test_voltage_range_high_min(qdac):  # noqa
    # -----------------------------------------------------------------------
    voltage = qdac.ch02.output_high_range_minimum_V()
    # -----------------------------------------------------------------------
    assert -10 < voltage < 10
    assert qdac.get_recorded_scpi_commands() == [f'sour2:rang:high:min?']


def test_voltage_range_high_max(qdac):  # noqa
    # -----------------------------------------------------------------------
    voltage = qdac.ch02.output_high_range_maximum_V()
    # -----------------------------------------------------------------------
    assert -10 < voltage < 10
    assert qdac.get_recorded_scpi_commands() == [f'sour2:rang:high:max?']


@pytest.mark.parametrize('selector', ['dc', 'med', 'high'])
def test_select_voltage_filter(selector, qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch02.output_filter(selector)
    filter = qdac.ch02.output_filter()
    # -----------------------------------------------------------------------
    assert filter == selector
    assert qdac.get_recorded_scpi_commands() == [
        f'sour2:filt {selector}',
        'sour2:filt?'
    ]


@pytest.mark.parametrize('u', [-1.0, 0.0, 1])
def test_dc_voltage_low(u, qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch02.dc_constant_V(u)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour2:volt:mode fix',
        f'sour2:volt {u}'
    ]


def test_dc_voltage_q(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch03.dc_constant_V()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == ['sour3:volt?']


@pytest.mark.parametrize('u', [-11.0, 11])
def test_invalid_dc_voltage(u, qdac):  # noqa
    # -----------------------------------------------------------------------
    with pytest.raises(ValueError) as error:
        qdac.ch01.dc_constant_V(u)
    # -----------------------------------------------------------------------
    assert f'{u} is invalid' in repr(error)


def test_voltage_immediate(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch02.dc_constant_V(0.1)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour2:volt:mode fix',
        'sour2:volt 0.1'
    ]


def test_voltage_last(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch02.dc_last_V()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == ['sour2:volt:last?']


def test_voltage_trigger_set_from_immediate(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch01.dc_next_V()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == ['sour1:volt:trig?']


def test_voltage_trigger_direct(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch02.dc_next_V(0.32)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == ['sour2:volt:trig 0.32']


def test_voltage_slew(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch02.dc_slew_rate_V_per_s(10)
    slew = qdac.ch02.dc_slew_rate_V_per_s()
    # -----------------------------------------------------------------------
    assert slew == 10
    assert qdac.get_recorded_scpi_commands() == [
        'sour2:volt:slew 10',
        'sour2:volt:slew?',
    ]


@pytest.mark.parametrize('mode', ['fixed', 'list', 'sweep'])
def test_select_voltage_mode(mode, qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch02.dc_mode(mode)
    mode = qdac.ch02.dc_mode()
    # -----------------------------------------------------------------------
    assert mode.lower() in ('swe', 'sweep', 'fix', 'fixed', 'list')
    assert qdac.get_recorded_scpi_commands() == [
        f'sour2:volt:mode {mode}',
        'sour2:volt:mode?'
    ]


def test_invalid_voltage_mode(qdac):  # noqa
    # -----------------------------------------------------------------------
    with pytest.raises(ValueError) as error:
        qdac.ch01.dc_mode('step')
    # -----------------------------------------------------------------------
    assert "'step' is not in" in repr(error)
    assert "'fixed'" in repr(error)
    assert "'list'" in repr(error)
    assert "'sweep'" in repr(error)


def test_dc_initiate(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch02.dc_initiate()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == ['sour2:dc:init']


def test_dc_abort(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch02.dc_abort()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == ['sour2:dc:abor']
