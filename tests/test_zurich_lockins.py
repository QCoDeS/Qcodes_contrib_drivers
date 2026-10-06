"""Hardware-free checks of the shared Zurich lock-in acquisition contract."""

from collections import deque
from types import SimpleNamespace

import numpy as np
import pytest
from qcodes import config
from qcodes.dataset import (
    LinSweep,
    dond,
    initialise_or_create_database_at,
    new_experiment,
)
from qcodes.instrument import ChannelList, Instrument, InstrumentChannel
from qcodes.parameters import ManualParameter, Parameter

from qcodes_contrib_drivers.drivers.ZurichInstruments._lockin import (
    ComplexSampleParameter,
    LockinMixin,
)


class FakeLockin(LockinMixin, Instrument):
    """Real QCoDeS channels with controllable, in-memory device values."""

    def __init__(self, model, *, scaling=1.0, options="", session=None):
        Instrument.__init__(self, "test_" + model.lower())
        self._lockin_model = self.device_type = model
        self._measurement_demodulators = (0,) if model == "MFLI" else tuple(range(8))
        self._output_mixers = (1,) if model == "MFLI" else (3, 7)
        self.options = options
        self.session = session if session is not None else SimpleNamespace()
        self.samples = deque()
        self.sample_calls = 0
        self.sample_hook = None
        self.timestamp = 2**54
        demods = self._channels("demods", 2 if model == "MFLI" else 8)
        for demod in demods:
            for name, value in [("enable", 1), ("adcselect", 0), ("rate", 1000)]:
                demod.add_parameter(
                    name, parameter_class=ManualParameter, initial_value=value
                )
            demod.add_parameter(
                "sample",
                get_cmd=self.next_sample,
                snapshot_get=False,
                snapshot_value=False,
            )
        for group, count in [("sigins", 1 if model == "MFLI" else 2), ("currins", 1)]:
            for channel in self._channels(group, count):
                channel.add_parameter(
                    "scaling", parameter_class=ManualParameter, initial_value=scaling
                )
        references = (1,) if model == "MFLI" else (3, 7)
        for channel, index in zip(
            self._channels("extrefs", len(references)), references
        ):
            channel.add_parameter(
                "enable", parameter_class=ManualParameter, initial_value=0
            )
            channel.add_parameter(
                "demodselect", parameter_class=ManualParameter, initial_value=index
            )
        for channel, mixer in zip(
            self._channels("sigouts", len(self._output_mixers)), self._output_mixers
        ):
            for name, value in [("on", 0), ("raw_amplitude", 0.25), ("raw_enabled", 0)]:
                channel.add_parameter(
                    name, parameter_class=ManualParameter, initial_value=value
                )
            channel.amplitudes = {mixer: SimpleNamespace(value=channel.raw_amplitude)}
            channel.enables = {mixer: SimpleNamespace(value=channel.raw_enabled)}
        self._initialize_lockin()

    def _channels(self, name, count):
        channels = ChannelList(self, name, InstrumentChannel, snapshotable=True)
        for index in range(count):
            channels.append(InstrumentChannel(self, name + str(index)))
        self.add_submodule(name, channels)
        return channels

    def device_options(self):
        return self.options

    def get_idn(self):
        return {
            "vendor": "test",
            "model": self.device_type,
            "serial": "test",
            "firmware": "test",
        }

    def next_sample(self):
        self.sample_calls += 1
        if self.sample_hook is not None:
            self.sample_hook()
        if self.samples:
            return self.samples.popleft()
        self.timestamp += 1
        return sample(self.timestamp)


def sample(timestamp=1, x=3.0, y=4.0):
    return {
        "timestamp": np.array([timestamp], dtype=np.uint64),
        "x": [x],
        "y": [y],
        "phase": [123.0],
    }


@pytest.fixture
def make_lockin():
    instruments = []

    def make(model="MFLI", **kwargs):
        instrument = FakeLockin(model, **kwargs)
        instruments.append(instrument)
        return instrument

    yield make
    for instrument in instruments:
        instrument.close()


@pytest.mark.parametrize("model", ["MFLI", "UHFLI"])
def test_combined_readout_uses_one_advancing_sample(make_lockin, model):
    instrument = make_lockin(model)
    base = 2**54
    instrument.samples.extend(
        [sample(base, 1, 1), sample(base, 2, 2), sample(base + 1)]
    )
    result = instrument.demods[0].readout()
    assert result == pytest.approx((3, 4, 5, 53.13010235415598))
    assert all(type(value) is float for value in result)
    assert instrument.sample_calls == 3


def test_scalar_reads_are_independent_and_read_only(make_lockin):
    instrument = make_lockin()
    channel = instrument.demods[0]
    for name, expected in [("x", 3), ("y", 4), ("r", 5), ("theta", 53.13010235415598)]:
        assert channel.parameters[name]() == pytest.approx(expected)
        assert not channel.parameters[name].settable
    assert instrument.sample_calls == 8


@pytest.mark.parametrize(
    "x,y", [(3, 4), ([3.0], [4.0]), (np.array([3.0]), np.array([4.0]))]
)
def test_legacy_complex_parameter_accepts_scalar_and_array_values(x, y):
    raw = Parameter("raw", get_cmd=lambda: {"x": x, "y": y})
    parameter = ComplexSampleParameter("complex_sample", dict_parameter=raw)
    assert parameter() == 3 + 4j


def test_legacy_latest_sample_and_missing_parameter(make_lockin):
    instrument = make_lockin()
    assert instrument.demods[0].complex_sample() == 3 + 4j
    assert instrument.sample_calls == 1
    assert instrument.demods[0].complex_sample.label == "Vrms"
    assert instrument.demods[0].complex_sample.unit == ""
    with pytest.raises(TypeError, match="requires a dict_parameter"):
        ComplexSampleParameter("bad")


def test_reference_only_channel_has_no_new_readouts(make_lockin):
    instrument = make_lockin()
    assert "readout" not in instrument.demods[1].parameters
    with pytest.raises(RuntimeError, match="reference-only"):
        instrument.demods[1].complex_sample()
    assert instrument.sample_calls == 0


def test_external_reference_and_disabled_channels_fail_before_sampling(make_lockin):
    instrument = make_lockin("UHFLI")
    instrument.extrefs[0].enable(1)
    with pytest.raises(RuntimeError, match="external-reference"):
        instrument.demods[3].readout()
    instrument.demods[0].enable(0)
    for parameter in [instrument.demods[0].x, instrument.demods[0].complex_sample]:
        with pytest.raises(RuntimeError, match="streaming is disabled"):
            parameter()
    assert instrument.sample_calls == 0
    assert instrument.demods[0].enable() == 0


def test_timeout_and_timestamp_reset(make_lockin):
    instrument = make_lockin()
    instrument.acquisition_timeout(0.02)
    instrument.samples.extend([sample(10)] * 100)
    with pytest.raises(TimeoutError, match="no newer sample"):
        instrument.demods[0].readout()
    instrument.samples.clear()
    instrument.samples.extend([sample(10), sample(9)])
    with pytest.raises(RuntimeError, match="backwards"):
        instrument.demods[0].readout()


@pytest.mark.parametrize(
    "bad_sample",
    [
        {},
        {"x": [], "y": []},
        sample(1, float("nan")),
        sample(1, float("inf")),
        {"x": [1, 2], "y": [3, 4]},
        sample(0),
        {"x": 1, "y": 2, "timestamp": 1.5},
        {"x": 1, "y": 2, "timestamp": True},
    ],
)
def test_invalid_samples_are_not_measurements(make_lockin, bad_sample):
    instrument = make_lockin()
    instrument.samples.append(bad_sample)
    with pytest.raises(ValueError):
        instrument.demods[0].readout()


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf")])
def test_timeout_must_be_positive_and_finite(make_lockin, timeout):
    with pytest.raises(ValueError):
        make_lockin().acquisition_timeout(timeout)


def test_units_follow_input_selection_before_dataset_registration(make_lockin):
    instrument = make_lockin()
    channel = instrument.demods[0]
    assert channel.readout.units == ("V", "V", "V", "deg")
    channel.adcselect(1)
    with pytest.raises(RuntimeError, match="configure_readout"):
        channel.r()
    instrument.configure_readout()
    assert channel.readout.units == ("A", "A", "A", "deg")
    assert [channel.parameters[name].unit for name in ["x", "y", "r", "theta"]] == [
        "A",
        "A",
        "A",
        "deg",
    ]
    assert channel.r() == 5
    instrument.currins[0].scaling(1e6)
    with pytest.raises(RuntimeError, match="configure_readout"):
        channel.r()
    with pytest.raises(ValueError, match="specify unit explicitly"):
        instrument.configure_readout()
    instrument.configure_readout(unit="uA")
    assert channel.r.unit == "uA"
    assert channel.r() == 5  # No second application of the device scaling.


def test_scaled_input_at_construction_requires_explicit_unit(make_lockin):
    instrument = make_lockin(scaling=10)
    with pytest.raises(RuntimeError, match="units need configuration"):
        instrument.demods[0].x()
    instrument.configure_readout(unit="")
    assert instrument.demods[0].x() == 3


@pytest.mark.parametrize(
    "model,source,unit",
    [("UHFLI", 1, "V"), ("MFLI", 8, "V"), ("UHFLI", 9, "V"), ("MFLI", 174, "")],
)
def test_other_known_input_units(make_lockin, model, source, unit):
    instrument = make_lockin(model)
    instrument.demods[0].adcselect(source)
    instrument.configure_readout()
    assert instrument.demods[0].readout.units == (unit, unit, unit, "deg")
    assert instrument.demods[0].r() == 5


def test_unknown_input_requires_explicit_unit(make_lockin):
    instrument = make_lockin()
    instrument.demods[0].adcselect(999)
    with pytest.raises(ValueError, match="specify unit explicitly"):
        instrument.configure_readout()
    with pytest.raises(RuntimeError, match="configure_readout"):
        instrument.demods[0].readout()
    instrument.configure_readout(unit="Hz")
    assert instrument.demods[0].r.unit == "Hz"
    assert instrument.demods[0].r() == 5


def test_disabling_stream_during_acquisition_is_rejected(make_lockin):
    instrument = make_lockin()
    instrument.sample_hook = lambda: instrument.demods[0].enable(0)
    with pytest.raises(RuntimeError, match="streaming is disabled"):
        instrument.demods[0].readout()


def test_invalid_newer_sample_is_not_returned(make_lockin):
    instrument = make_lockin()
    instrument.samples.extend([sample(1), sample(2, float("nan"))])
    with pytest.raises(ValueError, match="Non-finite"):
        instrument.demods[0].readout()


def test_configuration_change_during_acquisition_is_rejected(make_lockin):
    instrument = make_lockin()
    instrument.sample_hook = lambda: instrument.sigins[0].scaling(2)
    with pytest.raises(RuntimeError, match="configure_readout"):
        instrument.demods[0].readout()


@pytest.mark.parametrize("index", [-1, 1, 999, True, 0.0])
def test_configure_rejects_invalid_demodulator(make_lockin, index):
    with pytest.raises(ValueError, match="No scalar readout"):
        make_lockin().configure_readout(index)


def test_snapshot_does_not_acquire_and_records_units(make_lockin):
    instrument = make_lockin()
    instrument.configure_readout(unit="A")
    snapshot = instrument.demods[0].snapshot(update=True)
    assert instrument.sample_calls == 0
    assert snapshot["parameters"]["readout"]["units"] == ("A", "A", "A", "deg")
    for name in ["sample", "complex_sample", "x", "y", "r", "theta", "readout"]:
        assert "value" not in snapshot["parameters"][name]


@pytest.mark.parametrize("model", ["MFLI", "UHFLI"])
def test_output_aliases_use_correct_mixer_and_keep_output_off(make_lockin, model):
    instrument = make_lockin(model)
    for output in instrument.sigouts:
        assert output.amplitude() == 0.25
        output.amplitude(-0.125)
        assert output.raw_amplitude() == -0.125
        output.amplitude_enabled(1)
        assert output.raw_enabled() == 1
        assert output.on() == 0


def test_existing_optional_mfli_complex_channels_are_preserved(make_lockin):
    instrument = make_lockin(options="MD")
    assert instrument.demods[1].complex_sample() == 3 + 4j
    assert "amplitude" not in instrument.sigouts[0].parameters


@pytest.mark.parametrize("use_threads", [False, True])
def test_dond_writes_separate_columns_for_both_instruments(
    make_lockin, tmp_path, monkeypatch, use_threads
):
    monkeypatch.setitem(config.core, "db_location", str(tmp_path / "lockins.db"))
    initialise_or_create_database_at(config.core.db_location)
    experiment = new_experiment("lockins", "simulated")
    shared_session = SimpleNamespace()
    mfli = make_lockin(session=shared_session)
    uhfli = make_lockin("UHFLI", session=shared_session)
    assert mfli._readout_lock is uhfli._readout_lock
    sweep = ManualParameter("sweep", initial_value=0)
    dataset, _, _ = dond(
        LinSweep(sweep, 0, 1, 3, 0),
        mfli.demods[0].readout,
        uhfli.demods[4].readout,
        mfli.demods[0].r,
        mfli.demods[0].complex_sample,
        exp=experiment,
        do_plot=False,
        show_progress=False,
        use_threads=use_threads,
    )
    data = dataset.get_parameter_data()
    for instrument, index in [(mfli, 0), (uhfli, 4)]:
        readout = instrument.demods[index].readout
        for name, value, unit in zip(
            readout.full_names, [3, 4, 5, 53.13010235415598], ["V", "V", "V", "deg"]
        ):
            np.testing.assert_allclose(data[name][name], value)
            np.testing.assert_allclose(data[name]["sweep"], [0, 0.5, 1])
            assert dataset.paramspecs[name].unit == unit
    complex_name = mfli.demods[0].complex_sample.full_name
    np.testing.assert_allclose(data[complex_name][complex_name], 3 + 4j)
