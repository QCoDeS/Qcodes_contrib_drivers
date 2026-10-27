"""Offline regression tests. These tests never connect to physical hardware."""

from __future__ import annotations

import numpy as np
import pytest
from pyvisa.errors import VisaIOError

from qcodes_contrib_drivers.drivers.Tektronix.keithley_2280s import (
    Keithley2280S,
    _parse_data,
)


@pytest.fixture
def supply():
    driver = Keithley2280S(
        "supply",
        "GPIB::1::INSTR",
        pyvisa_sim_file="qcodes_contrib_drivers.sims:Keithley_2280S.yaml",
    )
    yield driver
    driver.close()


@pytest.mark.parametrize(
    "address,model,voltage,current",
    [
        ("GPIB::1::INSTR", "2280S-32-6", 32, 6.1),
        ("GPIB::2::INSTR", "2280S-60-3", 60, 3.3),
    ],
)
def test_model_limits(address, model, voltage, current):
    driver = Keithley2280S(
        "model_test",
        address,
        pyvisa_sim_file="qcodes_contrib_drivers.sims:Keithley_2280S.yaml",
    )
    try:
        assert driver.IDN()["model"] == model
        driver.source_voltage.validate(voltage)
        driver.source_current.validate(current)
        for parameter, invalid in (
            (driver.source_voltage, voltage + 0.1),
            (driver.source_current, current + 0.1),
            (driver.source_voltage, -0.1),
            (driver.source_current, -0.1),
        ):
            with pytest.raises(ValueError):
                parameter(invalid)
    finally:
        driver.close()


def test_unsupported_model_closes_connection(monkeypatch):
    monkeypatch.setattr(Keithley2280S, "get_idn", lambda _: {"model": "2400"})
    with pytest.raises(ValueError, match="Unsupported"):
        Keithley2280S(
            "unsupported",
            "GPIB::1::INSTR",
            pyvisa_sim_file="qcodes_contrib_drivers.sims:Keithley_2280S.yaml",
        )
    assert not Keithley2280S.exist("unsupported")


def test_setpoints_and_voltage_limit(supply):
    supply.voltage_limit(2)
    supply.source_voltage(1.25)
    supply.source_current(0.001)
    assert supply.source_voltage() == 1.25
    assert supply.source_current() == 0.001
    with pytest.raises(ValueError):
        supply.source_voltage(2.1)
    assert supply.source_voltage() == 1.25


@pytest.mark.parametrize("state", ["on", "off", "disabled"])
def test_three_output_states(supply, state):
    supply.output(state)
    assert supply.output() == state


@pytest.mark.parametrize("frequency,maximum", [(50, 12), (60, 15)])
def test_line_frequency_nplc_limits(supply, monkeypatch, frequency, maximum):
    monkeypatch.setattr(supply.line_frequency, "get", lambda: frequency)
    supply.concurrent.nplc(maximum)
    assert supply.concurrent.nplc() == maximum
    with pytest.raises(ValueError):
        supply.concurrent.nplc(maximum + 0.01)


def test_numeric_scalar_and_concurrent_measurements_restore_format(supply):
    supply.output("on")
    supply.data_format("READ,SOUR,UNIT,REL")
    assert supply.voltage.measure() == pytest.approx(0.05)
    assert supply.current.measure() == pytest.approx(1.5e-6)
    assert supply.concurrent.measure() == pytest.approx((1.5e-6, 0.05))
    assert supply.concurrent.measure.units == ("A", "V")
    assert supply.data_format() == "READ,SOUR,UNIT,REL"


def test_measurement_restores_format_on_timeout(supply, monkeypatch):
    supply.output("on")
    original_ask = supply.ask_raw

    def ask(command):
        if command == ":MEAS:VOLT?":
            raise VisaIOError(-1073807339)
        return original_ask(command)

    monkeypatch.setattr(supply, "ask_raw", ask)
    with pytest.raises(VisaIOError):
        supply.voltage.measure()
    assert supply.data_format() == "READ,SOUR,UNIT,REL"


@pytest.mark.parametrize(
    "name,expected,unit", [("current", 1.5e-6, "A"), ("voltage", 0.05, "V")]
)
def test_concurrent_scalar_uses_concurrent_acquisition(
    supply, monkeypatch, name, expected, unit
):
    commands = []
    original_ask = supply.ask_raw

    def ask(command):
        commands.append(command)
        return original_ask(command)

    monkeypatch.setattr(supply, "ask_raw", ask)
    parameter = supply.concurrent.parameters[name]
    assert not parameter.settable
    assert parameter.unit == unit
    with pytest.raises(RuntimeError, match="Enable the output"):
        parameter()
    supply.output("on")
    assert parameter() == pytest.approx(expected)
    assert [c for c in commands if c.startswith(":MEAS")] == [":MEAS:CONC?"]
    assert supply.data_format() == "READ,SOUR,UNIT,REL"


def test_measurement_does_not_enable_output(supply):
    with pytest.raises(RuntimeError, match="Enable the output"):
        supply.voltage.measure()
    with pytest.raises(RuntimeError, match="Enable the output"):
        supply.acquire(3)
    assert supply.output() == "off"


def test_relative_acquisition_takes_a_fresh_reading(supply, monkeypatch):
    commands = []
    original_ask = supply.ask_raw
    original_write = supply.write_raw

    def ask(command):
        commands.append(command)
        return original_ask(command)

    def write(command):
        commands.append(command)
        return original_write(command)

    monkeypatch.setattr(supply, "ask_raw", ask)
    monkeypatch.setattr(supply, "write_raw", write)
    supply.output("on")
    supply.voltage.acquire_relative()
    assert commands.index(":MEAS:VOLT?") < commands.index(":SENS:VOLT:REF:ACQ")


def test_malformed_concurrent_response_is_rejected(supply, monkeypatch):
    supply.output("on")
    original_ask = supply.ask_raw
    monkeypatch.setattr(
        supply,
        "ask_raw",
        lambda command: "1e-6" if command == ":MEAS:CONC?" else original_ask(command),
    )
    with pytest.raises(ValueError, match="Unexpected CONC"):
        supply.concurrent.measure()


def test_metadata_parser_does_not_corrupt_modes_or_timestamps():
    assert _parse_data(
        "+1.25E-6A,+5E-2V,+0.2s,CV,10/20/2026,12:34:56.1234,0008RNDG#"
    ) == (1.25e-6, 0.05, 0.2, "CV", "10/20/2026", "12:34:56.1234", 8.0)


def test_snapshot_never_triggers_or_consumes_errors(supply, monkeypatch):
    asked = []
    original_ask = supply.ask_raw

    def ask(command):
        asked.append(command)
        return original_ask(command)

    monkeypatch.setattr(supply, "ask_raw", ask)
    supply.snapshot(update=True)
    assert not any(
        command.startswith(
            (":MEAS", ":READ", ":FETC", ":CALC2:IMM", ":SYST:ERR", "*OPC")
        )
        for command in asked
    )
    assert ":SOUR:VOLT?" in asked
    assert ":SENS:CONC:NPLC?" in asked


@pytest.mark.parametrize(
    "parameter,value",
    [
        ("data_format", "READ,BOGUS"),
        ("data_format", 'READ";:OUTP ON'),
        ("display_text", 'hello"\n:OUTP ON'),
        ("arm_count", 0),
        ("trigger_count", 2501),
        ("trigger_source", "BUS"),
    ],
)
def test_invalid_settings_are_rejected(supply, parameter, value):
    with pytest.raises(ValueError):
        supply.parameters[parameter](value)


def test_read_and_fetch_keep_metadata(supply, monkeypatch):
    calls = []

    def ask(command):
        calls.append(command)
        return "+1E-6A,+0.05V,CV,10/20/2026 12:00:00"

    monkeypatch.setattr(supply, "ask_raw", ask)
    expected = (1e-6, 0.05, "CV", "10/20/2026 12:00:00")
    assert supply.read() == expected
    assert supply.fetch() == expected
    assert calls == [":READ?", ":FETC?"]


def test_statistics_avoid_firmware_dependent_order(supply, monkeypatch):
    values = {"MIN": 1.0, "MAX": 5.0, "MEAN": 3.0, "PKPK": 4.0, "SDEV": 2.0}
    original_ask = supply.ask_raw

    def ask(command):
        if command == ":CALC2:IMM?":
            return str(values[supply.calculate.format()])
        return original_ask(command)

    monkeypatch.setattr(supply, "ask_raw", ask)
    previous = supply.calculate.format()
    assert supply.calculate.statistics() == {k.lower(): v for k, v in values.items()}
    assert supply.calculate.format() == previous
    assert supply.calculate.data_format() == "READ,UNIT"
    assert not supply.calculate.enabled()


def test_buffer_bounds_and_empty_buffer(supply):
    assert supply.buffer.get_data() == ()
    for start, end in [(0, 1), (5, 4), (1, 2501)]:
        with pytest.raises(ValueError):
            supply.buffer.get_data(start, end)


@pytest.mark.parametrize("fail", [False, True])
def test_acquisition_sequence_and_cleanup(supply, monkeypatch, fail):
    commands = []
    original_ask = supply.ask_raw
    original_write = supply.write_raw

    def ask(command):
        commands.append(command)
        if command == ':TRAC:DATA:SEL? 1,3,"READ,SOUR,REL"':
            return "1e-6,0.05,0,2e-6,0.05,0.1,3e-6,0.05,0.2"
        if command == "*OPC?" and fail:
            raise VisaIOError(-1073807339)
        return original_ask(command)

    def write(command):
        commands.append(command)
        original_write(command)

    monkeypatch.setattr(supply, "ask_raw", ask)
    monkeypatch.setattr(supply, "write_raw", write)
    supply.output("on")
    if fail:
        with pytest.raises(VisaIOError):
            supply.acquire(3)
    else:
        result = supply.acquire(3)
        np.testing.assert_allclose(result[:, 0], [1e-6, 2e-6, 3e-6])
        np.testing.assert_allclose(result[:, 1], 0.05)
        np.testing.assert_allclose(result[:, 2], [0, 0.1, 0.2])
    assert commands.index(":INIT:CONT 0") < commands.index(":ABOR")
    assert commands.index(":ABOR") < commands.index(":TRAC:CLE")
    assert commands.index(":TRAC:CLE") < commands.index(":TRAC:FEED:CONT NEXT")
    assert commands.index(":TRAC:FEED:CONT NEXT") < commands.index(":INIT")
    assert commands[-1] == ":ABOR"


def test_opc_zero_is_false_and_error_message_can_contain_commas(supply, monkeypatch):
    monkeypatch.setattr(supply, "ask_raw", lambda _: "0")
    assert supply.opc() is False
    monkeypatch.setattr(
        supply, "ask_raw", lambda _: '-222,"Data out of range, voltage"'
    )
    assert supply.get_error() == (-222, "Data out of range, voltage")


def test_do1d_and_do2d_save_both_measurements(supply, tmp_path, monkeypatch):
    import qcodes as qc
    from qcodes.dataset import (
        do1d,
        do2d,
        initialise_database,
        new_experiment,
    )

    monkeypatch.setitem(qc.config.core, "db_location", str(tmp_path / "sweeps.db"))
    initialise_database()
    experiment = new_experiment("2280S", "simulator")
    supply.output("on")
    kwargs = {
        "exp": experiment,
        "do_plot": False,
        "use_threads": False,
        "show_progress": False,
    }
    one, _, _ = do1d(
        supply.source_voltage, 0, 0.02, 3, 0, supply.concurrent.measure, **kwargs
    )
    two, _, _ = do2d(
        supply.source_current,
        0.0005,
        0.001,
        2,
        0,
        supply.source_voltage,
        0,
        0.02,
        3,
        0,
        supply.concurrent.measure,
        **kwargs,
    )
    for dataset, count in [(one, 3), (two, 6)]:
        data = dataset.get_parameter_data()
        for name, value, unit in zip(
            supply.concurrent.measure.full_names, [1.5e-6, 0.05], ["A", "V"]
        ):
            assert data[name][name].size == count
            np.testing.assert_allclose(data[name][name], value)
            assert dataset.paramspecs[name].unit == unit


@pytest.mark.parametrize("name,expected", [("current", 1.5e-6), ("voltage", 0.05)])
def test_do1d_saves_only_selected_concurrent_measurement(
    supply, tmp_path, monkeypatch, name, expected
):
    import qcodes as qc
    from qcodes.dataset import do1d, initialise_database, new_experiment

    monkeypatch.setitem(
        qc.config.core, "db_location", str(tmp_path / "scalar_sweep.db")
    )
    initialise_database()
    experiment = new_experiment("2280S", "simulator")
    supply.output("on")
    parameter = supply.concurrent.parameters[name]
    dataset, _, _ = do1d(
        supply.source_current,
        0,
        0.01,
        3,
        0,
        parameter,
        exp=experiment,
        do_plot=False,
        use_threads=False,
        show_progress=False,
    )
    data = dataset.get_parameter_data()
    assert set(data) == {parameter.full_name}
    assert set(dataset.paramspecs) == {
        supply.source_current.full_name,
        parameter.full_name,
    }
    np.testing.assert_allclose(
        data[parameter.full_name][parameter.full_name], [expected] * 3
    )
    np.testing.assert_allclose(
        data[parameter.full_name][supply.source_current.full_name], [0, 0.005, 0.01]
    )
    assert dataset.paramspecs[parameter.full_name].unit == parameter.unit
