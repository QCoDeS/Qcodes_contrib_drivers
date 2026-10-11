from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from qcodes.dataset import Measurement, initialise_or_create_database_at, new_experiment
from qcodes.parameters import Parameter

from qcodes_contrib_drivers.drivers.ZurichInstruments._lockin import (
    _DemodulatorReadout,
    _PolarReadoutParameter,
    _ReadoutParameter,
    _XYReadoutParameter,
)


@pytest.mark.parametrize(
    "parameter_class, names, values",
    [
        (_PolarReadoutParameter, ("readout_r", "readout_theta"), (5.0, 53.13)),
        (_XYReadoutParameter, ("readout_x", "readout_y"), (3.0, 4.0)),
    ],
)
def test_paired_dataset_uses_one_read(tmp_path, parameter_class, names, values):
    reader = SimpleNamespace(read=Mock(return_value=(3.0, 4.0, 5.0, 53.13)))
    polar = parameter_class("paired_readout", reader=reader)
    initialise_or_create_database_at(tmp_path / "polar.db")
    new_experiment("polar", "test")
    measurement = Measurement()
    measurement.register_parameter(polar)
    with measurement.run() as saver:
        saver.add_result((polar, polar()))
    reader.read.assert_called_once_with()
    data = saver.dataset.get_parameter_data()
    assert set(data) == set(names)
    for name, value in zip(names, values):
        assert data[name][name].item() == value


def test_polar_units_refresh_and_configuration_guard():
    channel = SimpleNamespace(adcselect=lambda: 0)
    instrument = SimpleNamespace(
        demods=[channel],
        sigins=[SimpleNamespace(scaling=lambda: 1.0)],
    )
    reader = _DemodulatorReadout(instrument, 0)
    reader.parameters = [Parameter(name) for name in ("x", "y", "r", "theta")]
    channel.readout = _ReadoutParameter("readout", reader=reader)
    channel.readout_polar = _PolarReadoutParameter("readout_polar", reader=reader)
    channel.readout_xy = _XYReadoutParameter("readout_xy", reader=reader)
    reader.configure()
    polar = channel.readout_polar
    assert polar.units == ("V", "deg")
    polar.cache.set((5.0, 53.13))
    xy = channel.readout_xy
    assert xy.units == ("V", "V")
    xy.cache.set((3.0, 4.0))
    reader.configure("scaled V")
    assert polar.units == ("scaled V", "deg")
    assert not polar.cache.valid
    assert polar.metadata == channel.readout.metadata
    assert xy.units == ("scaled V", "scaled V")
    assert not xy.cache.valid
    assert xy.metadata == channel.readout.metadata
    instrument.sigins[0].scaling = lambda: 2.0
    with pytest.raises(RuntimeError, match="configure_readout"):
        reader._check_configuration()
