"""Check the notebook's DAQ adapter without connecting to hardware."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest
from qcodes import config
from qcodes.dataset import do0d, do1d, initialise_or_create_database_at, new_experiment
from qcodes.instrument import Instrument, InstrumentChannel
from qcodes.parameters import ManualParameter, MultiParameter


class NotebookDevice(Instrument):
    def get_idn(self):
        return {
            "vendor": "test",
            "model": "lockin",
            "serial": "devtest",
            "firmware": "test",
        }


@pytest.fixture
def trace_setup():
    notebook_path = (
        Path(__file__).parents[1] / "docs/examples/ZurichInstruments_lockins.ipynb"
    )
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = next(c["source"] for c in notebook["cells"] if c["id"] == "trace-helper")
    namespace = {"np": np, "MultiParameter": MultiParameter}
    exec(compile("".join(source), str(notebook_path), "exec"), namespace)

    device = NotebookDevice("notebook_lia")
    device.serial = "devtest"
    device.clockbase = MagicMock(return_value=1.8e9)
    device.sigins = [SimpleNamespace(scaling=MagicMock(return_value=1))]
    device.extrefs = []
    channel = InstrumentChannel(device, "demod0")
    device.add_submodule("demod0", channel)
    for name, value in [
        ("adcselect", 0),
        ("enable", 1),
        ("trigger", 0),
        ("rate", 1000),
    ]:
        channel.add_parameter(
            name, parameter_class=ManualParameter, initial_value=value
        )

    # Large timestamps and a slightly quantized grid must survive conversion.
    timestamps = np.array([[2**54 + i * 17999999 for i in range(4)]], dtype=np.uint64)
    paths = [f"/devtest/demods/0/sample.{component}" for component in ("x", "y")]
    data = {
        path: [
            {
                "value": np.array([[1.0, 2.0, 3.0, 4.0]]) * sign,
                "timestamp": timestamps.copy(),
            }
        ]
        for path, sign in zip(paths, [1, -1])
    }
    module = MagicMock()
    module.read.return_value = data
    factory = MagicMock(return_value=module)
    device.session = SimpleNamespace(modules=SimpleNamespace(create_daq_module=factory))
    channel.add_parameter(
        "xy_trace",
        parameter_class=namespace["XYTrace"],
        demod_index=0,
        duration=0.04,
        points=4,
    )
    yield SimpleNamespace(
        trace=channel.xy_trace,
        device=device,
        channel=channel,
        module=module,
        factory=factory,
        data=data,
        paths=paths,
        ticks=timestamps[0],
    )
    device.close()


@pytest.mark.parametrize("clockbase", [60e6, 1.8e9])
def test_trace_uses_aligned_device_timestamps_and_releases_module(
    trace_setup, clockbase
):
    setup = trace_setup
    setup.device.clockbase.return_value = clockbase
    x, y = setup.trace()
    np.testing.assert_array_equal(x, [1, 2, 3, 4])
    np.testing.assert_array_equal(y, [-1, -2, -3, -4])
    expected_time = (setup.ticks - setup.ticks[0]) / clockbase
    np.testing.assert_array_equal(setup.trace.time_axis, expected_time)
    for setpoints in setup.trace.setpoints:
        np.testing.assert_array_equal(setpoints[0], expected_time)
    setup.module.read.assert_called_once_with(raw=True)
    setup.module.finish.assert_called_once()
    setup.module.unsubscribe.assert_called_once_with("*")
    setup.module.raw_module.clear.assert_called_once()
    setup.module.close.assert_called_once()


@pytest.mark.parametrize(
    "failure", ["missing", "empty", "short", "nan", "misaligned", "repeated"]
)
def test_incomplete_or_invalid_traces_are_rejected(trace_setup, failure):
    setup = trace_setup
    burst = setup.data[setup.paths[1]][0]
    if failure == "missing":
        del setup.data[setup.paths[1]]
    elif failure == "empty":
        setup.data[setup.paths[1]] = []
    elif failure == "short":
        burst["value"] = burst["value"][:, :3]
    elif failure == "nan":
        burst["value"][0, 1] = np.nan
    elif failure == "misaligned":
        burst["timestamp"][0, 0] += 1
    else:
        for path in setup.paths:
            setup.data[path][0]["timestamp"][0, 1] = setup.ticks[0]
    with pytest.raises(RuntimeError):
        setup.trace()
    setup.module.raw_module.clear.assert_called_once()
    setup.module.close.assert_called_once()


def test_timeout_releases_module_and_does_not_return_old_data(trace_setup):
    setup = trace_setup
    setup.module.wait_done.side_effect = TimeoutError("stopped stream")
    with pytest.raises(TimeoutError, match="stopped stream"):
        setup.trace()
    setup.module.read.assert_not_called()
    setup.module.raw_module.clear.assert_called_once()
    setup.module.close.assert_called_once()


def test_setup_change_during_trace_rejects_stale_units(trace_setup):
    setup = trace_setup
    setup.module.wait_done.side_effect = lambda **kwargs: setup.channel.adcselect(1)
    with pytest.raises(RuntimeError, match="unscaled Signal Input"):
        setup.trace()


@pytest.mark.parametrize("setting,value", [("enable", 0), ("trigger", 1), ("rate", 1)])
def test_trace_rejects_unsuitable_stream_before_creating_module(
    trace_setup, setting, value
):
    setup = trace_setup
    setup.channel.parameters[setting](value)
    with pytest.raises((RuntimeError, ValueError)):
        setup.trace()
    setup.factory.assert_not_called()


def test_do0d_and_do1d_save_xy_arrays_with_actual_time_coordinates(
    trace_setup, tmp_path, monkeypatch
):
    setup = trace_setup
    monkeypatch.setitem(config.core, "db_location", str(tmp_path / "traces.db"))
    initialise_or_create_database_at(config.core.db_location)
    experiment = new_experiment("trace_example", "simulated")
    trace = setup.trace
    frequency = ManualParameter("frequency", unit="Hz", initial_value=0)
    single, _, _ = do0d(trace, exp=experiment, do_plot=False)
    swept, _, _ = do1d(
        frequency,
        100,
        300,
        3,
        0,
        trace,
        exp=experiment,
        do_plot=False,
        show_progress=False,
    )
    times = (setup.ticks - setup.ticks[0]) / setup.device.clockbase()
    for dataset, shape in [(single, (4,)), (swept, (3, 4))]:
        data = dataset.get_parameter_data()
        assert len(data) == 2
        for name, sign in zip(trace.full_names, [1, -1]):
            columns = data[name]
            np.testing.assert_array_equal(
                columns[name], np.broadcast_to(np.arange(1, 5) * sign, shape)
            )
            time_name = trace.setpoint_full_names[0][0]
            np.testing.assert_allclose(
                columns[time_name], np.broadcast_to(times, shape), rtol=1e-14, atol=0
            )
            assert dataset.paramspecs[name].unit == "V"
            assert dataset.paramspecs[time_name].unit == "s"
            if dataset is swept:
                np.testing.assert_array_equal(
                    columns["frequency"], [[100] * 4, [200] * 4, [300] * 4]
                )
    assert setup.factory.call_count == 4  # A separate module for every acquisition.
