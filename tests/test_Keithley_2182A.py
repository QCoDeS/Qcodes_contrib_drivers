"""
Tests for the Keithley 2182A nanovoltmeter driver. Tested on a real instrument with firmware version C08/B01.

This test file uses PyVISA simulation as described in:
https://microsoft.github.io/Qcodes/examples/writing_drivers/Creating-Simulated-PyVISA-Instruments.html
"""

import pytest
import numpy as np

from qcodes_contrib_drivers.drivers.Tektronix.Keithley_2182A import Keithley2182A


@pytest.fixture(scope="function", name="driver")
def _make_driver():
    """Create a simulated Keithley 2182A instrument for testing."""
    driver = Keithley2182A(
        "Keithley_2182A",
        address="GPIB0::1::INSTR",
        pyvisa_sim_file="qcodes_contrib_drivers.sims:Keithley_2182A.yaml",  # Comment out this line to test on a real instrument
    )
    driver.reset()
    driver.clear()
    yield driver
    driver.close()


def test_idn(driver) -> None:
    """Test instrument identification."""
    expected_idn = {
        "vendor": "KEITHLEY INSTRUMENTS INC.",
        "model": "2182A",
    }
    idn = driver.get_idn()
    assert idn["vendor"] == expected_idn["vendor"]
    assert idn["model"] == expected_idn["model"]
    assert len(idn["serial"]) == 7  # Serial number length check
    assert idn["serial"].isalnum() is True
    assert len(idn["firmware"]) == 7


def test_measurement_modes(driver) -> None:
    """Test measurement mode setting and getting."""
    # Test DC voltage mode
    driver.mode("dc voltage")
    assert driver.mode() == "dc voltage"


def test_voltage_measurement(driver) -> None:
    """Test voltage measurement functionality."""
    # Set to voltage mode
    driver.mode("dc voltage")

    # Test direct voltage measurement
    voltage = driver.voltage()
    assert isinstance(voltage, float)


def test_fetch_command(driver) -> None:
    """Test the FETCh command functionality."""
    # Set to voltage mode
    driver.mode("dc voltage")
    driver.initiate_measurement()

    # Test fetch
    fetched_value = driver.fetch()
    assert isinstance(fetched_value, float)


def test_read_command(driver) -> None:
    """Test the READ command functionality."""
    # Set to voltage mode
    driver.mode("dc voltage")

    # Test read
    read_value = driver.read()
    assert isinstance(read_value, float)


def test_range_control(driver) -> None:
    """Test measurement range control."""
    # Test auto range
    driver.auto_range_enabled(True)
    assert driver.auto_range_enabled() is True

    # Test manual range
    driver.auto_range_enabled(False)
    assert driver.auto_range_enabled() is False

    # Test range setting
    driver.range(1.0)
    assert driver.range() == pytest.approx(1.0, rel=1e-6)


def test_nplc_control(driver) -> None:
    """Test NPLC (integration time) control."""
    # Test NPLC setting
    driver.nplc(1.0)
    assert driver.nplc() == pytest.approx(1.0, rel=1e-6)

    # Test other NPLC values
    driver.nplc(0.1)
    assert driver.nplc() == pytest.approx(0.1, rel=1e-6)


def test_aperture_time(driver) -> None:
    """Test aperture time control."""
    # Test aperture time setting
    driver.aperture_time(0.02)
    assert driver.aperture_time() == pytest.approx(0.02, rel=1e-3)


def test_trigger_system(driver) -> None:
    """Test trigger system functionality."""
    # Test trigger source
    driver.trigger_source("immediate")
    assert driver.trigger_source() == "immediate"

    driver.trigger_source("external")
    assert driver.trigger_source() == "external"

    # Test trigger delay
    driver.trigger_delay(0.1)
    assert driver.trigger_delay() == pytest.approx(0.1, rel=1e-6)


def test_display_control(driver) -> None:
    """Test display control."""
    # Test display enable/disable
    driver.display_enabled(True)
    assert driver.display_enabled() is True

    driver.display_enabled(False)
    assert driver.display_enabled() is False


def test_filters(driver) -> None:
    """Test analog and digital filter control."""
    # Test analog filter
    driver.analog_filter(True)
    assert driver.analog_filter() is True

    driver.analog_filter(False)
    assert driver.analog_filter() is False

    # Test digital filter
    driver.digital_filter(True)
    assert driver.digital_filter() is True

    driver.digital_filter(False)
    assert driver.digital_filter() is False


def test_auto_zero(driver) -> None:
    """Test auto-zero functionality."""
    # Test via method
    driver.auto_zero(True)
    assert driver.get_auto_zero() is True

    driver.auto_zero(False)
    assert driver.get_auto_zero() is False


def test_trigger_commands(driver) -> None:
    """Test trigger command functionality."""
    # Test initiate measurement
    driver.initiate_measurement()

    # Test trigger
    driver.trigger()

    # Test abort
    driver.abort_measurement()


def test_configuration_methods(driver) -> None:
    """Test configuration convenience methods."""
    # Test voltage measurement configuration
    driver.configure_voltage_measurement(auto_range=True, nplc=1.0, auto_zero=True)
    assert driver.mode() == "dc voltage"
    assert driver.auto_range_enabled() is True
    assert driver.nplc() == pytest.approx(1.0, rel=1e-6)


def test_optimization_presets(driver) -> None:
    """Test optimization preset methods."""
    # Test low noise optimization
    driver.optimize_for_low_noise()
    assert driver.nplc() == pytest.approx(10.0, rel=1e-6)
    assert driver.digital_filter() is True
    assert driver.analog_filter() is True

    # Test speed optimization
    driver.optimize_for_speed()
    assert driver.nplc() == pytest.approx(0.1, rel=1e-6)
    assert driver.digital_filter() is False
    assert driver.analog_filter() is False


def test_measurement_speed_presets(driver) -> None:
    """Test measurement speed preset functionality."""
    # Test fast preset
    driver.set_measurement_speed("fast")
    assert driver.nplc() == pytest.approx(0.1, rel=1e-6)
    assert driver.analog_filter() is False
    assert driver.digital_filter() is False

    # Test medium preset
    driver.set_measurement_speed("medium")
    assert driver.nplc() == pytest.approx(1.0, rel=1e-6)
    assert driver.analog_filter() is False
    assert driver.digital_filter() is False

    # Test slow preset
    driver.set_measurement_speed("slow")
    assert driver.nplc() == pytest.approx(10.0, rel=1e-6)
    assert driver.analog_filter() is True
    assert driver.digital_filter() is True


def test_statistics_measurement(driver) -> None:
    """Test statistical measurement functionality."""
    # Set to voltage mode
    driver.mode("dc voltage")

    # Test statistics measurement
    stats = driver.measure_voltage_statistics(num_measurements=5)

    assert "mean" in stats
    assert "stdev" in stats
    assert "min" in stats
    assert "max" in stats
    assert "count" in stats
    assert "measurements" in stats

    assert stats["count"] == 5
    assert len(stats["measurements"]) == 5
    assert isinstance(stats["mean"], float)
    assert isinstance(stats["stdev"], float)


def test_status_monitoring(driver) -> None:
    """Test status monitoring functionality."""
    # Test measurement status
    status = driver.get_measurement_status()

    assert "mode" in status
    assert "range" in status
    assert "auto_range" in status
    assert "nplc" in status
    assert "trigger_source" in status
    assert "trigger_delay" in status


def test_error_handling(driver) -> None:
    """Test error handling functionality."""
    # Test error query
    error_code, error_message = driver.get_error()
    assert error_code == 0
    assert "No error" in error_message

    # Test clear errors
    driver.clear()


def test_self_test(driver) -> None:
    """Test instrument self-test functionality."""
    result = driver.self_test()
    assert result is True


def test_range_info(driver) -> None:
    """Test range information functionality."""
    # Test voltage ranges
    driver.mode("dc voltage")
    ranges = driver.check_ranges()

    assert "available_ranges" in ranges
    assert "current_range" in ranges
    assert "auto_range" in ranges


def test_reset(driver) -> None:
    """Test instrument reset functionality."""
    # Change some settings
    driver.nplc(5.0)
    driver.digital_filter(True)

    # Reset the instrument
    driver.reset()

    # The instrument should be reset (values may vary depending on defaults)
    # This test mainly checks that reset doesn't cause errors
