"""Tests for the DriverE5080B class."""

# This test along the driver code are meant to be qcodes
from qcodes_contrib_drivers.drivers.Keysight.Keysight_E5080B import KeySight_E5080B
import pytest
import numpy as np
import pyvisa

@pytest.fixture(scope="function", name="vnaks")
def _make_vnaks():
    """
    Create a simulated Keysight E5080B instrument.
    The pyvisa_sim_file parameter instructs QCoDeS to use the simulation file.
    """
    driver = KeySight_E5080B(
        "Keysight_E5080B",
        address="TCPIP::192.168.0.10::INSTR",
        pyvisa_sim_file="qcodes_contrib_drivers.sims:Keysight_E5080B.yaml"
    )
    yield driver
    driver.close()

def verify_property(vnaks, param_name, vals):
    """
    For each value in vals, set the parameter and verify that it returns the expected value.
    """
    # Access the parameter from the instrument's parameters dictionary
    param = vnaks.parameters[param_name]
    for val in vals:
        param(val)
        new_val = param()
        if isinstance(new_val, float):
            assert np.isclose(new_val, val), f"{param_name} expected {val}, got {new_val}"
        else:
            assert new_val == val, f"{param_name} expected {val}, got {new_val}"

def test_start_freq(vnaks):
    verify_property(vnaks, "start_freq", [1e6, 2e6, 3e9, 20e9])

def test_stop_freq(vnaks):
    verify_property(vnaks, "stop_freq", [1e6, 2e6, 3e9, 20e9])

def test_center_freq(vnaks):
    verify_property(vnaks, "center_freq", [1e6, 2e6, 3e9, 20e9])

def test_span(vnaks):
    verify_property(vnaks, "span", [1e6, 2e6, 3e9, 20e9])

def test_cw(vnaks):
    # Test the continuous wave frequency, including a zero value
    verify_property(vnaks, "cw", [0, 1e6, 5e6])

def test_points(vnaks):
    verify_property(vnaks, "points", [11, 101, 1000])

def test_source_power(vnaks):
    verify_property(vnaks, "source_power", [0, 5, -4])

def test_if_bandwidth(vnaks):
    verify_property(vnaks, "if_bandwidth", [1, 1000, 5000, 15000000])

def test_sweep_type(vnaks):
    # Valid enum values: "LIN", "LOG", "POW", "CW", "SEGM"
    verify_property(vnaks, "sweep_type", ["LIN", "LOG", "POW"])

def test_sweep_mode(vnaks):
    # Valid enum values: "HOLD", "CONT", "GRO", "SING"
    verify_property(vnaks, "sweep_mode", ["HOLD", "CONT"])

def test_scattering_parameter(vnaks):
    # Valid enum values: "S11", "S12", "S21", "S22"
    verify_property(vnaks, "scattering_parameter", ["S11", "S21"])

def test_averages_enabled(vnaks):
    # Valid values for averages_enabled: "1" for on, "0" for off
    verify_property(vnaks, "averages_enabled", [True, False])

def test_averages_count(vnaks):
    verify_property(vnaks, "averages_count", [1, 100, 1000])

def test_averages_mode(vnaks):
    # Valid enum values: "POIN", "SWEEP"
    verify_property(vnaks, "averages_mode", ["POIN", "SWE"])

def test_format_data(vnaks):
    # Valid enum values: "REAL,32", "REAL,64", "ASCii,0"
    verify_property(vnaks, "format_data", ["REAL,32", "ASCii,0"])

def test_rf_on(vnaks):
    # Valid values for rf_on: "1" for on, "0" for off
    verify_property(vnaks, "rf_on", [True, False])

def test_format_border(vnaks):
    # Valid enum values: "NORM", "SWAP"
    verify_property(vnaks, "format_border", ["NORM", "SWAP"])


def test_get_data(vnaks, monkeypatch):
    # Arrange: have query_binary_values return a known list of floats
    expected = [0.1, -0.2, 0.3, -0.4]
    monkeypatch.setattr(vnaks.visa_handle, 'query_binary_values', lambda cmd: expected)

    # Act
    data = vnaks.get_data()

    # Assert
    assert data == expected

def test_get_frequencies_calls_format_and_returns_array(vnaks, monkeypatch):
    # Arrange
    # 1) Spy on format_data
    calls = []
    def fake_format(fmt):
        calls.append(fmt)
    monkeypatch.setattr(vnaks, 'format_data', fake_format)

    # 2) Simulate VISA returning a list of freqs
    freqs = [1e6, 2e6, 3e6]
    monkeypatch.setattr(vnaks.visa_handle, 'query_binary_values', lambda cmd: freqs)

    # Act
    out = vnaks.get_frequencies()

    # Assert
    # - format_data was called exactly once, with the right argument
    assert calls == ["REAL,64"]
    # - output is a numpy array of the returned freqs
    assert isinstance(out, np.ndarray)
    assert np.allclose(out, freqs)
