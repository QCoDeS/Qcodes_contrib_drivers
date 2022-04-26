import pytest
from .sim_qdac2_fixtures import qdac  # noqa
from qcodes_contrib_drivers.drivers.QDevil.QDAC2 import ExternalInput


def test_measurement_default_values(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch02.measurement()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        #'sens2:trig:sour hold',
        'sens2:del 0.0',
        'sens2:rang high',
        'sens2:nplc 1',
        'sens2:coun 1',
        'sens2:trig:sour bus',
        'sens2:init',
    ]


def test_measurement_ambiguous(qdac):  # noqa
    # -----------------------------------------------------------------------
    with pytest.raises(ValueError) as error:
        qdac.ch02.measurement(aperture_s=1e-3, nplc=2)
    # -----------------------------------------------------------------------
    assert 'Only one of nplc or aperture_s can be specified' in repr(error)


def test_measurement_aperture(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch02.measurement(
        delay_s=1e-3,
        repetitions=10,
        current_range='low',
        aperture_s=1e-3,
    )
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        #'sens2:trig:sour hold',
        'sens2:del 0.001',
        'sens2:rang low',
        'sens2:aper 0.001',
        'sens2:coun 10',
        'sens2:trig:sour bus',
        'sens2:init',
    ]


def test_measurement_start_without_explicit_trigger(qdac):  # noqa
    measurement = qdac.ch02.measurement()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    measurement.start()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sens2:init:cont off',
        'sens2:trig:sour imm',
        'sens2:init'
    ]


def test_measurement_trigger_on_internal(qdac):  # noqa
    measurement = qdac.ch02.measurement()
    trigger = qdac.allocate_trigger()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    measurement.start_on(trigger)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sens2:trig:sour int{trigger.value}',
        f'sens2:init:cont on',
        'sens2:init'
    ]


def test_measurement_start_trigger_fires(qdac):  # noqa
    measurement = qdac.ch02.measurement()
    trigger = qdac.allocate_trigger()
    measurement.start_on(trigger)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    measurement.start()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'tint {trigger.value}'
    ]


def test_measurement_trigger_on_external(qdac):  # noqa
    measurement = qdac.ch02.measurement()
    trigger = ExternalInput(1)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    measurement.start_on_external(trigger)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sens2:trig:sour ext{trigger}',
        f'sens2:init:cont on',
        'sens2:init'
    ]


def test_measurement_start(qdac):  # noqa
    measurement = qdac.ch02.measurement()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    measurement.abort()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == ['sens2:abor']


def test_measurement_abort(qdac):  # noqa
    measurement = qdac.ch02.measurement()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    measurement.abort()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == ['sens2:abor']


def test_measurement_remaining(qdac):  # noqa
    measurement = qdac.ch02.measurement()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    remaining = measurement.n_cycles_remaining()
    # -----------------------------------------------------------------------
    assert remaining == 0
    assert qdac.get_recorded_scpi_commands() == ['sens2:ncl?']


def test_measurement_points(qdac):  # noqa
    # The Simulated instrument returns two measurements.
    measurement = qdac.ch02.measurement()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    points = measurement.n_available()
    # -----------------------------------------------------------------------
    assert points == 2
    assert qdac.get_recorded_scpi_commands() == ['sens2:data:poin?']


def test_measurement_remove_two(qdac):  # noqa
    # The Simulated instrument returns two measurements.
    measurement = qdac.ch02.measurement()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    available = measurement.available_A()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sens2:data:poin?',
        'sens2:data:rem?'
    ]
    assert len(available) == 2
    assert isinstance(available[0], float)
    assert isinstance(available[1], float)


def test_measurement_last(qdac):  # noqa
    measurement = qdac.ch02.measurement()
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    current = measurement.peek_A()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == ['sens2:data:last?']
    assert current == 0.0


#
# Direct current measurement (some of this will probably go away)
#


def test_current_read_immediately(qdac):  # noqa
    # -----------------------------------------------------------------------
    currents = qdac.ch02.read_current_A()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == ['read2?']
    assert currents == [0.001]


def test_current_fetch(qdac):  # noqa
    # -----------------------------------------------------------------------
    currents = qdac.ch02.fetch_current_A()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == ['fetc2?']
    assert currents == [0.01, 0.02]


def test_current_range_invalid(qdac):  # noqa
    # -----------------------------------------------------------------------
    with pytest.raises(ValueError) as error:
        qdac.ch24.measurement_range('med')
    # -----------------------------------------------------------------------
    assert "'med' is not in" in repr(error)
    assert "'low'" in repr(error)
    assert "'high'" in repr(error)


@pytest.mark.parametrize('range', ['low', 'high'])
def test_current_range(range, qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch02.measurement_range(range)
    r = qdac.ch02.measurement_range()
    # -----------------------------------------------------------------------
    assert r == range
    assert qdac.get_recorded_scpi_commands() == [
        f'sens2:rang {range}',
        'sens2:rang?'
    ]


def test_current_aperture(qdac):  # noqa
    seconds = 0.06
    # -----------------------------------------------------------------------
    qdac.ch02.measurement_aperture_s(seconds)
    aperture = qdac.ch02.measurement_aperture_s()
    # -----------------------------------------------------------------------
    assert aperture == seconds
    assert qdac.get_recorded_scpi_commands() == [
        f'sens2:aper {seconds}',
        'sens2:aper?'
    ]


def test_current_nplc(qdac):  # noqa
    nplc = 10
    # -----------------------------------------------------------------------
    qdac.ch02.measurement_nplc(nplc)
    n = qdac.ch02.measurement_nplc()
    # -----------------------------------------------------------------------
    assert n == nplc
    assert qdac.get_recorded_scpi_commands() == [
        f'sens2:nplc {nplc}',
        'sens2:nplc?'
    ]


def test_current_delay(qdac):  # noqa
    seconds = 0.01
    # -----------------------------------------------------------------------
    qdac.ch02.measurement_delay_s(seconds)
    s = qdac.ch02.measurement_delay_s()
    # -----------------------------------------------------------------------
    assert s == seconds
    assert qdac.get_recorded_scpi_commands() == [
        f'sens2:del {seconds}',
        'sens2:del?'
    ]


def test_current_abort(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch02.measurement_abort()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == ['sens2:abor']


def test_clear_current_measurements(qdac):  # noqa
    # -----------------------------------------------------------------------
    measurements = qdac.ch02.clear_measurements()
    # -----------------------------------------------------------------------
    assert measurements == [0.01, 0.02]
    assert qdac.get_recorded_scpi_commands() == [
        'sens2:data:poin?',
        'sens2:data:rem?'
    ]


def test_current_count(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch02.measurement_count(5)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == ['sens2:coun 5']


def test_current_count_q(qdac):  # noqa
    qdac.ch02.measurement_count(10)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    count = qdac.ch02.measurement_count()
    # -----------------------------------------------------------------------
    count == 10
    assert qdac.get_recorded_scpi_commands() == ['sens2:coun?']


def test_current_remaining(qdac):  # noqa
    # -----------------------------------------------------------------------
    qdac.ch02.n_masurements_remaining()
    # -----------------------------------------------------------------------
    # Cannot sim test: assert remaining == 1
    assert qdac.get_recorded_scpi_commands() == ['sens2:ncl?']


def test_current_data_last(qdac):  # noqa
    # -----------------------------------------------------------------------
    current = qdac.ch02.current_last_A()
    # -----------------------------------------------------------------------
    assert current == 0.0
    assert qdac.get_recorded_scpi_commands() == ['sens2:data:last?']


def test_current_data_points(qdac):  # noqa
    # The Simulated instrument returns two measurements.
    # -----------------------------------------------------------------------
    points = qdac.ch02.n_measurements_available()
    # -----------------------------------------------------------------------
    assert points == 2
    assert qdac.get_recorded_scpi_commands() == ['sens2:data:poin?']


# def test_current_trigger_on_bus(qdac):  # noqa
#     # -----------------------------------------------------------------------
#     qdac.ch02.measurement_start_on(trigger)
#     # -----------------------------------------------------------------------
#     assert qdac.get_recorded_scpi_commands() == [
#         f'sens2:trig:sour int{trigger.value}'
#     ]


def test_current_trigger_on_internal(qdac):  # noqa
    trigger = qdac.allocate_trigger()
    # -----------------------------------------------------------------------
    qdac.ch02.current_start_on(trigger)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'sens2:trig:sour int{trigger.value}'
    ]
