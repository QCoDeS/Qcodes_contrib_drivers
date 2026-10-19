"""Trace acquisition with simulated modules and real QCoDeS datasets."""

import threading
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
from qcodes.station import Station
from qcodes.dataset import do0d, do1d, initialise_or_create_database_at, new_experiment
from qcodes.instrument import Instrument, InstrumentChannel
from qcodes.parameters import Parameter
from qcodes.validators import Numbers

from qcodes_contrib_drivers.drivers.ZurichInstruments._lockin import (
    LockinMixin,
    _DemodulatorReadout,
    _ReadoutParameter,
)


class SimulatedLockin(LockinMixin, Instrument):
    def __init__(self, model):
        super().__init__("trace_lockin")
        self._lockin_model = model
        self._lockin_options = set()
        self.serial = "dev1234"
        self.session = SimpleNamespace(modules=Mock())
        self._readout_lock = threading.RLock()
        self.extrefs = []
        self.sigins = [SimpleNamespace(scaling=lambda: 1.0)]
        self.currins = [SimpleNamespace(scaling=lambda: 1.0)]
        self.add_parameter("clockbase", get_cmd=lambda: 60e6 if model == "MFLI" else 1.8e9)
        channel = InstrumentChannel(self, "demod0")
        self.add_submodule("demod0", channel)
        self.demods = [channel]
        for name, value in dict(adcselect=0, enable=1, trigger=0, rate=1000).items():
            channel.add_parameter(name, set_cmd=None, initial_value=value)
        reader = _DemodulatorReadout(self, 0)
        self._readouts = {0: reader}
        channel.add_parameter("readout", parameter_class=_ReadoutParameter, reader=reader)
        reader.configure()
        self.add_parameter("frequency", unit="Hz", label="Frequency", set_cmd=None,
                           initial_value=10.0, vals=Numbers(0, 1e6))
        self.frequency.zi_node = "/dev1234/oscs/0/freq"
        self.add_parameter("amplitude", unit="V", label="Amplitude", set_cmd=None,
                           initial_value=0.1, vals=Numbers(0, 1))
        self.amplitude.zi_node = "/dev1234/sigouts/0/amplitudes/1"


@pytest.fixture(params=["MFLI", "UHFLI"])
def lockin(request):
    instrument = SimulatedLockin(request.param)
    yield instrument
    instrument.close()


def time_data(lockin, *, rate=10):
    # Deliberately differ from the nominal grid and exceed float timestamp precision.
    ticks = np.array([[2**60 + i * int(lockin.clockbase() / rate) for i in range(3)]], dtype=np.uint64)
    return {
        f"/dev1234/demods/0/sample.{c}": [dict(value=np.array([v]), timestamp=ticks.copy())]
        for c, v in (("x", [3.0, 0.0, -3.0]), ("y", [4.0, 2.0, -4.0]))
    }


def sweep_data():
    return {"/dev1234/demods/0/sample": [[dict(
        grid=np.array([1.0, 2.1, 3.0]), frequency=np.array([100., 200., 300.]),
        x=np.array([3., 0., -3.]), y=np.array([4., 2., -4.]),
    )]]}


def prepare(lockin, mode, **kwargs):
    if mode in ("time", "exact"):
        module = lockin.session.modules.create_daq_module.return_value
        if mode == "exact":
            module.read.return_value = time_data(lockin, rate=lockin.demods[0].rate())
            trace = lockin.configure_trace(grid_mode=4, points=3, **kwargs)
        else:
            module.read.return_value = time_data(lockin)
            trace = lockin.configure_trace(duration=0.5, points=3, **kwargs)
    else:
        module = lockin.session.modules.create_sweeper_module.return_value
        module.read.return_value = sweep_data()
        trace = lockin.configure_trace(sweep_parameter=lockin.frequency,
                                       start=1, stop=3, points=3, **kwargs)
        # Model a sweep changing the device, so restoration is exercised.
        module.execute.side_effect = lambda: lockin.frequency(3)
    return trace, module


@pytest.mark.parametrize("mode", ["time", "exact", "sweep"])
def test_do0d_saves_one_acquisition_with_actual_axis(lockin, mode, tmp_path):
    trace, module = prepare(lockin, mode, parameters=("theta", "r", "x", "y"))
    module.execute.assert_not_called()
    # Station snapshot includes the trace settings, but does not acquire data.
    station = Station(lockin)
    snapshot = station.snapshot(update=True)
    meta = snapshot["instruments"][lockin.name]["submodules"]["demod0"]["parameters"][trace.name]["metadata"]
    assert meta["acquisition"] == ("time" if mode == "exact" else mode)
    if mode == "exact":
        assert meta["grid_mode"] == "exact"
        assert meta["duration_s"] == pytest.approx(0.003)
        np.testing.assert_allclose(trace.axis, [0, 0.001, 0.002])
    module.execute.assert_not_called()
    initialise_or_create_database_at(tmp_path / "trace.db")
    experiment = new_experiment("trace", "simulated")
    for _ in range(2):
        dataset, _, _ = do0d(trace, exp=experiment, do_plot=False, use_threads=False)
        data = dataset.get_parameter_data()
        expected_axis = {"time": [0., 0.1, 0.2], "exact": [0., 0.001, 0.002],
                         "sweep": [1., 2.1, 3.]}[mode]
        for i, expected in enumerate((np.degrees(np.arctan2([4, 2, -4], [3, 0, -3])),
                                      [5, 2, 5], [3, 0, -3], [4, 2, -4])):
            name = trace.full_names[i]
            np.testing.assert_allclose(data[name][name].ravel(), expected)
            np.testing.assert_allclose(data[name][trace.setpoint_full_names[i][0]].ravel(), expected_axis)
        np.testing.assert_allclose(trace.axis, expected_axis)
    assert module.execute.call_count == 2
    assert module.finish.call_count == 2
    assert module.unsubscribe.call_count == 2
    assert module.raw_module.clear.call_count == 2
    assert module.close.call_count == 2
    assert lockin.frequency() == 10.0
    assert trace.root_instrument is lockin
    if mode == "sweep":
        module.bandwidthcontrol.assert_called_with(0)
        module.scan.assert_called_with(0)
    else:
        module.grid.mode.assert_called_with(4 if mode == "exact" else 2)
        if mode == "exact":
            module.duration.assert_not_called()
        else:
            module.duration.assert_called_with(0.5)
    station.remove_component(lockin.name)


@pytest.mark.parametrize("mode", ["time", "exact", "sweep"])
def test_outer_do1d_saves_both_axes(lockin, mode, tmp_path):
    trace, module = prepare(lockin, mode, parameters=("r",))
    initialise_or_create_database_at(tmp_path / "outer.db")
    experiment = new_experiment("outer", "simulated")
    outer = Parameter("outer", set_cmd=None, initial_value=0)
    dataset, _, _ = do1d(outer, 1, 2, 2, 0, trace, exp=experiment,
                         do_plot=False, use_threads=False, show_progress=False)
    result = dataset.get_parameter_data()[trace.full_names[0]]
    np.testing.assert_allclose(result["outer"].ravel(), [1, 1, 1, 2, 2, 2])
    np.testing.assert_allclose(result[trace.full_names[0]].ravel(), [5, 2, 5] * 2)
    assert module.execute.call_count == 2


@pytest.mark.parametrize("mode", ["time", "exact", "sweep"])
@pytest.mark.parametrize("stage", ["device", "execute", "wait_done", "read"])
def test_failure_releases_module_and_restores_setting(lockin, mode, stage):
    trace, module = prepare(lockin, mode)
    def fail(*args, **kwargs):
        if mode == "sweep":
            lockin.frequency(2)
        raise TimeoutError("acquisition failed")
    getattr(module, stage).side_effect = fail
    with pytest.raises(TimeoutError, match="acquisition failed"):
        trace()
    module.finish.assert_called_once()
    module.unsubscribe.assert_called_once_with("*")
    module.raw_module.clear.assert_called_once()
    module.close.assert_called_once()
    assert lockin.frequency() == 10.0


def test_cleanup_failure_still_closes_and_restores(lockin):
    trace, module = prepare(lockin, "sweep")
    module.finish.side_effect = RuntimeError("finish failed")
    with pytest.raises(RuntimeError, match="finish failed"):
        trace()
    module.unsubscribe.assert_called_once_with("*")
    module.raw_module.clear.assert_called_once()
    module.close.assert_called_once()
    assert lockin.frequency() == 10.0


@pytest.mark.parametrize("mode", ["time", "sweep"])
def test_rejects_incomplete_results(lockin, mode):
    trace, module = prepare(lockin, mode)
    module.read.return_value = {}
    with pytest.raises(RuntimeError, match="Invalid or incomplete"):
        trace()
    module.close.assert_called_once()


@pytest.mark.parametrize("fault", ["misaligned", "float_timestamps", "reverse", "short", "nan"])
def test_rejects_invalid_time_data(lockin, fault):
    trace, module = prepare(lockin, "time")
    burst = module.read.return_value["/dev1234/demods/0/sample.y"][0]
    if fault == "misaligned":
        burst["timestamp"] += 1
    elif fault == "float_timestamps":
        burst["timestamp"] = burst["timestamp"].astype(float)
    elif fault == "reverse":
        for bursts in module.read.return_value.values():
            bursts[0]["timestamp"] = bursts[0]["timestamp"][:, ::-1]
    elif fault == "short":
        burst["value"] = burst["value"][:, :2]
    else:
        burst["value"][0, 1] = np.nan
    with pytest.raises(RuntimeError, match="Invalid or incomplete time trace"):
        trace()


@pytest.mark.parametrize("kwargs", [
    {}, dict(duration=0), dict(duration=-1), dict(duration=float("nan")),
    dict(duration=1, start=1), dict(duration=1, spacing="log"),
    dict(duration=1, settling_time=0), dict(duration=1, averaging_time=0),
    dict(duration=1, points=2.5), dict(duration=1, points=True),
    dict(duration=1, points=1), dict(duration=1, timeout=0),
    dict(duration=1, parameters=()), dict(duration=1, parameters=("x", "x")),
    dict(duration=1, parameters=("bad",)), dict(duration=1, demod=True),
    dict(duration=1, demod=1), dict(duration=0.001),
    dict(grid_mode=4, duration=1), dict(grid_mode=1), dict(grid_mode=2),
    dict(duration=1, grid_mode=0), dict(duration=1, grid_mode=3),
    dict(duration=1, grid_mode=True), dict(duration=1, grid_mode=2.0),
    dict(duration=1, grid_mode="exact"),
])
def test_bad_configuration_does_not_create_module(lockin, kwargs):
    with pytest.raises((ValueError, TypeError)):
        lockin.configure_trace(**kwargs)
    lockin.session.modules.create_daq_module.assert_not_called()
    lockin.session.modules.create_sweeper_module.assert_not_called()


@pytest.mark.parametrize("changes", [dict(start=None), dict(stop=None), dict(duration=1),
    dict(start=3, stop=1), dict(spacing="bad"), dict(spacing="log", start=0),
    dict(settling_time=-1), dict(averaging_time=float("inf")), dict(stop=2e6),
    dict(grid_mode=2), dict(grid_mode=4)])
def test_bad_sweep_configuration(lockin, changes):
    kwargs = dict(sweep_parameter=lockin.frequency, start=1, stop=3)
    kwargs.update(changes)
    with pytest.raises((ValueError, TypeError)):
        lockin.configure_trace(**kwargs)
    lockin.session.modules.create_sweeper_module.assert_not_called()


@pytest.mark.parametrize("grid_mode", [1, 2])
def test_interpolated_grid_modes(lockin, grid_mode):
    trace, module = prepare(lockin, "time", grid_mode=grid_mode)
    np.testing.assert_allclose(trace.axis, np.arange(3) * 0.5 / 3)
    trace()
    module.grid.mode.assert_called_once_with(grid_mode)
    module.duration.assert_called_once_with(0.5)
    np.testing.assert_allclose(trace.axis, [0, 0.1, 0.2])


@pytest.mark.parametrize("rate", [0, -1, float("nan"), float("inf")])
def test_exact_requires_positive_finite_rate(lockin, rate):
    lockin.demods[0].rate(rate)
    with pytest.raises(ValueError, match="rate"):
        lockin.configure_trace(points=3, grid_mode=4)
    lockin.session.modules.create_daq_module.assert_not_called()


def test_exact_rate_change_requires_new_trace(lockin):
    trace, module = prepare(lockin, "exact")
    lockin.demods[0].rate(500)
    with pytest.raises(RuntimeError, match="Streaming rate changed"):
        trace()
    module.execute.assert_not_called()
    new_trace, module = prepare(lockin, "exact")
    np.testing.assert_allclose(new_trace.axis, [0, 0.002, 0.004])
    new_trace()
    np.testing.assert_allclose(new_trace.axis, [0, 0.002, 0.004])


def test_units_configuration_and_streaming_guards(lockin):
    trace, module = prepare(lockin, "time")
    lockin.demods[0].enable(0)
    with pytest.raises(RuntimeError, match="disabled"):
        trace()
    lockin.demods[0].enable(1)
    lockin.demods[0].trigger(1)
    with pytest.raises(RuntimeError, match="continuous"):
        trace()
    lockin.demods[0].trigger(0)
    lockin.sigins[0].scaling = lambda: 2.0
    with pytest.raises(RuntimeError, match="configure_readout"):
        trace()
    lockin.configure_readout(unit="K")
    with pytest.raises(RuntimeError, match="new trace"):
        trace()
    new_trace = lockin.configure_trace(duration=0.5, points=3, parameters=("r", "theta"))
    assert new_trace.units == ("K", "deg")
    assert new_trace.name != trace.name
    assert trace.units == ("V", "V")
    module.execute.assert_not_called()


def test_log_sweep_and_non_frequency_axis(lockin):
    trace = lockin.configure_trace(sweep_parameter=lockin.amplitude,
                                   start=0.01, stop=0.1, points=3, spacing="log",
                                   settling_time=0.2, averaging_time=0.3)
    module = lockin.session.modules.create_sweeper_module.return_value
    module.read.return_value = sweep_data()
    grid = np.array([0.01, 0.031, 0.1])
    module.read.return_value["/dev1234/demods/0/sample"][0][0]["grid"] = grid
    trace()
    np.testing.assert_allclose(trace.axis, grid)
    assert trace.setpoint_units == (("V",), ("V",))
    module.xmapping.assert_called_once_with(1)
    module.settling.time.assert_called_once_with(0.2)
    module.averaging.time.assert_called_once_with(0.3)


def test_explicit_duplicate_name_does_not_replace_trace(lockin):
    trace, _ = prepare(lockin, "time", name="my_trace")
    with pytest.raises(ValueError, match="already has"):
        prepare(lockin, "time", name="my_trace")
    assert lockin.demods[0].parameters["my_trace"] is trace


@pytest.mark.parametrize("fault", ["missing_grid", "reverse", "short", "nan", "extra_sweep"])
def test_rejects_invalid_sweep_data(lockin, fault):
    trace, module = prepare(lockin, "sweep")
    sweeps = module.read.return_value["/dev1234/demods/0/sample"]
    sample = sweeps[0][0]
    if fault == "missing_grid":
        del sample["grid"]  # Never substitute demodulator frequency for the sweep axis.
    elif fault == "reverse":
        sample["grid"] = sample["grid"][::-1]
    elif fault == "short":
        sample["x"] = sample["x"][:2]
    elif fault == "nan":
        sample["y"][1] = np.nan
    else:
        sweeps.append(sweeps[0])
    with pytest.raises(RuntimeError, match="Invalid or incomplete sweep trace"):
        trace()
    assert lockin.frequency() == 10.0
    module.close.assert_called_once()


@pytest.mark.parametrize("fault", ["alias", "foreign_node", "unbound", "scaled"])
def test_rejects_non_native_sweep_parameters(lockin, fault):
    parameter = lockin.frequency
    if fault == "alias":
        del parameter.zi_node
    elif fault == "foreign_node":
        parameter.zi_node = "/dev9999/oscs/0/freq"
    elif fault == "unbound":
        parameter = Parameter("foreign", set_cmd=None, initial_value=1)
        parameter.zi_node = "/dev1234/oscs/0/freq"
    else:
        parameter.scale = 2
    with pytest.raises(ValueError, match="native"):
        lockin.configure_trace(sweep_parameter=parameter, start=1, stop=3)
    lockin.session.modules.create_sweeper_module.assert_not_called()
