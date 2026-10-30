from itertools import combinations
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
from qcodes.dataset import Measurement, initialise_or_create_database_at, new_experiment
from qcodes.instrument import Instrument, InstrumentChannel
from qcodes.parameters import MultiParameter, Parameter

from qcodes_contrib_drivers.drivers.ZurichInstruments import _lockin as lockin_driver
from qcodes_contrib_drivers.drivers.ZurichInstruments._lockin import (
    LockinMixin,
    _DemodulatorReadout,
    _ReadoutParameter,
)


class AcquisitionClock:
    """Advance acquisition time without real sleeps or hardware."""

    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        assert seconds > 0
        self.sleeps.append(seconds)
        self.now += seconds


class SimulatedScalarLockin(LockinMixin):
    """Emulate device nodes while retaining the real readout and guards."""

    def __init__(self, model):
        self._lockin_model = model
        self._lockin_options = set()
        self._readout_lock = threading.RLock()
        self.extrefs = []
        self.sigins = [SimpleNamespace(scaling=lambda: 1.0)]
        self.acquisition_timeout = lambda: 0.025
        channel = SimpleNamespace(
            adcselect=lambda: 0, enable=lambda: 1, sample=Mock(),
        )
        self.demods = [channel]
        reader = _DemodulatorReadout(self, 0)
        self._readouts = {0: reader}
        channel.readout = _ReadoutParameter("readout", reader=reader)
        self.configure_readout(demod=0)


@pytest.fixture(params=["MFLI", "UHFLI"])
def scalar_acquisition(request, monkeypatch):
    clock = AcquisitionClock()
    # Replace this driver's time module, not the process-wide clock used by pytest.
    monkeypatch.setattr(lockin_driver, "time", clock)
    return SimulatedScalarLockin(request.param), clock


def scalar_sample(timestamp, x=3.0, y=4.0):
    return dict(
        timestamp=np.array([timestamp], dtype=np.uint64),
        x=np.array([x]), y=np.array([y]),
    )


@pytest.mark.parametrize("enabled, selected, error", [
    pytest.param(0, 0, None, id="disabled-matching"),
    pytest.param(0, None, None, id="disabled-without-demodselect"),
    pytest.param(1, 0, "being used for external-reference recovery", id="enabled-matching"),
    pytest.param(1, 1, None, id="enabled-other-demodulator"),
    pytest.param(1, None, "extrefs\\[1\\].demodselect is unavailable", id="enabled-without-demodselect"),
])
def test_scalar_external_reference_guard(scalar_acquisition, enabled, selected, error):
    instrument, _ = scalar_acquisition
    reference = SimpleNamespace(enable=Mock(return_value=enabled))
    if selected is not None:
        reference.demodselect = Mock(return_value=selected)
    # Check the second reference too, after skipping a disabled reference.
    instrument.extrefs = [SimpleNamespace(enable=lambda: 0), reference]
    channel = instrument.demods[0]
    channel.sample.side_effect = [scalar_sample(100), scalar_sample(101)]

    if error is not None:
        with pytest.raises(RuntimeError, match=error):
            channel.readout()
        channel.sample.assert_not_called()
    else:
        assert channel.readout() == pytest.approx((3, 4, 5, np.degrees(np.arctan2(4, 3))))
        assert channel.sample.call_count == 2
    if not enabled and selected is not None:
        reference.demodselect.assert_not_called()


def test_scalar_rechecks_external_reference_after_sampling(scalar_acquisition):
    instrument, _ = scalar_acquisition
    reference = SimpleNamespace(enable=Mock(return_value=0), demodselect=lambda: 0)
    instrument.extrefs = [reference]

    def sample():
        reference.enable.return_value = 1
        return scalar_sample(100 + instrument.demods[0].sample.call_count)

    instrument.demods[0].sample.side_effect = sample
    with pytest.raises(RuntimeError, match="being used for external-reference recovery"):
        instrument.demods[0].readout()


def test_scalar_acquisition_waits_for_fresh_timestamp(scalar_acquisition):
    instrument, clock = scalar_acquisition
    channel = instrument.demods[0]
    # A one-tick increase must remain distinguishable above float precision.
    timestamp = 2**60
    baseline = scalar_sample(timestamp, x=-7, y=0)
    channel.sample.side_effect = [
        baseline, baseline,
        scalar_sample(timestamp, x=9, y=12),  # Changed values alone are not fresh.
        scalar_sample(timestamp + 1, x=3, y=-4),
    ]

    values = channel.readout()

    assert values == pytest.approx((3, -4, 5, np.degrees(np.arctan2(-4, 3))))
    assert channel.sample.call_count == 4
    assert clock.sleeps


def test_scalar_acquisition_waits_for_new_sample_on_each_read(scalar_acquisition):
    instrument, _ = scalar_acquisition
    channel = instrument.demods[0]
    previous = scalar_sample(100, x=0, y=0)
    first = scalar_sample(101, x=3, y=4)
    second = scalar_sample(102, x=0, y=-2)
    channel.sample.side_effect = [previous, first, first, second]

    assert channel.readout() == pytest.approx((3, 4, 5, np.degrees(np.arctan2(4, 3))))
    assert channel.readout() == pytest.approx((0, -2, 2, -90))


@pytest.mark.parametrize("after_success", [False, True])
def test_scalar_acquisition_times_out_when_samples_stop(scalar_acquisition, after_success):
    instrument, clock = scalar_acquisition
    channel = instrument.demods[0]
    frozen = scalar_sample(101)
    if after_success:
        channel.sample.side_effect = [scalar_sample(100), frozen]
        assert channel.readout()[:3] == (3, 4, 5)
        channel.sample.side_effect = None
    channel.sample.return_value = frozen

    with pytest.raises(TimeoutError, match="supplied no newer sample within 0.025 s"):
        channel.readout()

    assert clock.now >= instrument.acquisition_timeout()
    assert clock.sleeps


def test_scalar_acquisition_rejects_sample_arriving_after_timeout(scalar_acquisition):
    instrument, clock = scalar_acquisition
    channel = instrument.demods[0]
    samples = iter((scalar_sample(100), scalar_sample(101)))

    # Simulate the sample transport crossing the deadline on its second call.
    def get_sample():
        sample = next(samples)
        if sample["timestamp"].item() == 101:
            clock.now += 2 * instrument.acquisition_timeout()
        return sample

    channel.sample.side_effect = get_sample

    with pytest.raises(TimeoutError, match="supplied no newer sample"):
        channel.readout()


def test_scalar_acquisition_rejects_backwards_timestamp(scalar_acquisition):
    instrument, _ = scalar_acquisition
    channel = instrument.demods[0]
    channel.sample.side_effect = [scalar_sample(2**60), scalar_sample(2**60 - 1)]

    with pytest.raises(RuntimeError, match="timestamp moved backwards; reconnect"):
        channel.readout()


@pytest.mark.parametrize(
    "components",
    [
        subset
        for size in range(1, 5)
        for subset in combinations(("x", "y", "r", "theta"), size)
    ]
    + [("theta", "x", "r")],
)
def test_selected_dataset_uses_one_read(tmp_path, components):
    values = dict(x=3.0, y=4.0, r=5.0, theta=53.13)
    reader = SimpleNamespace(
        read=Mock(return_value=tuple(values.values())),
        instrument=SimpleNamespace(_readout_lock=threading.RLock()),
    )
    readout = _ReadoutParameter("readout", reader=reader)
    readout.units = ("V", "V", "V", "deg")
    selected = readout(*components)
    assert isinstance(selected, MultiParameter)
    reader.read.assert_not_called()
    assert selected is readout(parameters=components)
    assert selected.names == tuple(f"readout_{name}" for name in components)
    assert selected.labels == tuple(
        name.upper() if name != "theta" else "Theta" for name in components
    )
    assert selected.units == tuple(
        "deg" if name == "theta" else "V" for name in components
    )
    assert selected.shapes == ((),) * len(components)
    assert selected.setpoints == ((),) * len(components)
    assert readout.names == ("readout_x", "readout_y", "readout_r", "readout_theta")
    initialise_or_create_database_at(tmp_path / "selected.db")
    new_experiment("selected", "test")
    measurement = Measurement()
    measurement.register_parameter(selected)
    with measurement.run() as saver:
        saver.add_result((selected, selected()))
    reader.read.assert_called_once_with()
    data = saver.dataset.get_parameter_data()
    assert set(data) == set(selected.names)
    for component in components:
        name = f"readout_{component}"
        assert data[name][name].item() == values[component]


def test_default_readout_and_selection_preserve_channel_binding():
    reader = SimpleNamespace(
        read=Mock(return_value=(3.0, 4.0, 5.0, 53.13)),
        instrument=SimpleNamespace(_readout_lock=threading.RLock()),
    )
    instrument = Instrument("selected_lockin")
    try:
        channel = InstrumentChannel(instrument, "demod0")
        instrument.add_submodule("demod0", channel)
        channel.add_parameter("readout", parameter_class=_ReadoutParameter, reader=reader)
        readout = channel.readout
        assert readout() == (3.0, 4.0, 5.0, 53.13)
        reader.read.assert_called_once_with()
        selected = readout("r", "theta")
        assert selected.instrument is channel
        assert selected.root_instrument is instrument
        assert selected.full_names == (
            "selected_lockin_demod0_readout_r",
            "selected_lockin_demod0_readout_theta",
        )
        assert channel.parameters["readout"] is readout
        assert "readout_r_theta" not in channel.parameters
        assert selected("y", "x") is readout("y", "x")
    finally:
        instrument.close()


@pytest.mark.parametrize(
    "args, kwargs, error",
    [
        (("invalid",), {}, ValueError),
        (("x", "x"), {}, ValueError),
        ((1,), {}, ValueError),
        ((), {"parameters": []}, ValueError),
        ((), {"parameters": "theta"}, TypeError),
        ((), {"parameters": 1}, TypeError),
        (("x",), {"parameters": ["y"]}, TypeError),
        ((), {"unknown": ["x"]}, TypeError),
    ],
)
def test_invalid_selection_does_not_read(args, kwargs, error):
    reader = SimpleNamespace(read=Mock())
    readout = _ReadoutParameter("readout", reader=reader)
    with pytest.raises(error):
        readout(*args, **kwargs)
    reader.read.assert_not_called()


def test_selected_units_refresh_and_configuration_guard():
    channel = SimpleNamespace(adcselect=lambda: 0)
    instrument = SimpleNamespace(
        demods=[channel],
        sigins=[SimpleNamespace(scaling=lambda: 1.0)],
        _readout_lock=threading.RLock(),
    )
    reader = _DemodulatorReadout(instrument, 0)
    reader.parameters = [Parameter(name) for name in ("x", "y", "r", "theta")]
    channel.readout = _ReadoutParameter("readout", reader=reader)
    reader.configure()
    selected = channel.readout("theta", "y", "r")
    assert selected.units == ("deg", "V", "V")
    assert selected.metadata == channel.readout.metadata
    selected.cache.set((53.13, 4.0, 5.0))
    reader.configure("scaled V")
    assert selected.units == ("deg", "scaled V", "scaled V")
    assert not selected.cache.valid
    assert selected.metadata == channel.readout.metadata
    instrument.sigins[0].scaling = lambda: 2.0
    with pytest.raises(RuntimeError, match="configure_readout"):
        reader._check_configuration()
