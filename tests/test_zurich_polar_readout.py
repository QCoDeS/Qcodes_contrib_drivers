from itertools import combinations
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from qcodes.dataset import Measurement, initialise_or_create_database_at, new_experiment
from qcodes.instrument import Instrument, InstrumentChannel
from qcodes.parameters import MultiParameter, Parameter

from qcodes_contrib_drivers.drivers.ZurichInstruments._lockin import (
    _DemodulatorReadout,
    _ReadoutParameter,
)


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
