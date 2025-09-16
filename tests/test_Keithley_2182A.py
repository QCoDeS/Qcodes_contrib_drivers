"""
Tests for the Keithley 2182A nanovoltmeter driver.

This test file uses PyVISA simulation as described in:
https://microsoft.github.io/Qcodes/examples/writing_drivers/Creating-Simulated-PyVISA-Instruments.html
"""

import pytest
import numpy as np

from qcodes_contrib_drivers.drivers.Tektronix.Keithley_2182A import Keithley2182A
import qcodes.instrument.sims as sims


@pytest.fixture(scope="module")
def keithley_2182a():
    """Create a simulated Keithley 2182A instrument for testing."""
    instrument = Keithley2182A(
        "Keithley_2600",
        address="GPIB::1::INSTR",
        pyvisa_sim_file="qcodes_contrib_drivers.sims:Keithley_2182A.yaml",
        terminator="\n",
    )
    yield instrument
    instrument.close()


def test_idn(keithley_2182a):
    """Test instrument identification."""
    idn_dict = keithley_2182a.IDN()
    assert idn_dict["vendor"] == "KEITHLEY INSTRUMENTS INC."
    assert idn_dict["model"] == "2182A"
    assert idn_dict["serial"] == "1234567"
    assert idn_dict["firmware"] == "3.0.1"


def test_measurement_modes(keithley_2182a):
    """Test measurement mode setting and getting."""
    # Test DC voltage mode
    keithley_2182a.mode("dc voltage")
    assert keithley_2182a.mode() == "dc voltage"

    # Test temperature mode
    keithley_2182a.mode("temperature")
    assert keithley_2182a.mode() == "temperature"


def test_voltage_measurement(keithley_2182a):
    """Test voltage measurement functionality."""
    # Set to voltage mode
    keithley_2182a.mode("dc voltage")

    # Test direct voltage measurement
    voltage = keithley_2182a.voltage()
    assert isinstance(voltage, float)
    assert voltage == pytest.approx(1.234567e-6, rel=1e-6)


def test_temperature_measurement(keithley_2182a):
    """Test temperature measurement functionality."""
    # Set to temperature mode
    keithley_2182a.mode("temperature")

    # Test temperature measurement
    temperature = keithley_2182a.temperature()
    assert isinstance(temperature, float)
    assert temperature == pytest.approx(298.15, rel=1e-3)


def test_fetch_command(keithley_2182a):
    """Test the FETCh command functionality."""
    # Set to voltage mode
    keithley_2182a.mode("dc voltage")

    # Test fetch
    fetched_value = keithley_2182a.fetch()
    assert isinstance(fetched_value, float)
    assert fetched_value == pytest.approx(1.234567e-6, rel=1e-6)


def test_read_command(keithley_2182a):
    """Test the READ command functionality."""
    # Set to voltage mode
    keithley_2182a.mode("dc voltage")

    # Test read
    read_value = keithley_2182a.read()
    assert isinstance(read_value, float)
    assert read_value == pytest.approx(1.234567e-6, rel=1e-6)


def test_range_control(keithley_2182a):
    """Test measurement range control."""
    # Test auto range
    keithley_2182a.auto_range_enabled(True)
    assert keithley_2182a.auto_range_enabled() is True

    # Test manual range
    keithley_2182a.auto_range_enabled(False)
    assert keithley_2182a.auto_range_enabled() is False

    # Test range setting
    keithley_2182a.range(1.0)
    assert keithley_2182a.range() == pytest.approx(1.0, rel=1e-6)


def test_nplc_control(keithley_2182a):
    """Test NPLC (integration time) control."""
    # Test NPLC setting
    keithley_2182a.nplc(1.0)
    assert keithley_2182a.nplc() == pytest.approx(1.0, rel=1e-6)

    # Test other NPLC values
    keithley_2182a.nplc(0.1)
    assert keithley_2182a.nplc() == pytest.approx(0.1, rel=1e-6)


def test_aperture_time(keithley_2182a):
    """Test aperture time control."""
    # Test aperture time setting
    keithley_2182a.aperture_time(0.02)
    assert keithley_2182a.aperture_time() == pytest.approx(0.016667, rel=1e-3)


def test_line_frequency(keithley_2182a):
    """Test line frequency setting."""
    # Test 60 Hz
    keithley_2182a.line_frequency(60)
    assert keithley_2182a.line_frequency() == 60

    # Test 50 Hz
    keithley_2182a.line_frequency(50)
    assert keithley_2182a.line_frequency() == 50


def test_averaging(keithley_2182a):
    """Test averaging functionality."""
    # Test averaging enable/disable
    keithley_2182a.averaging_enabled(True)
    assert keithley_2182a.averaging_enabled() is True

    keithley_2182a.averaging_enabled(False)
    assert keithley_2182a.averaging_enabled() is False

    # Test averaging count
    keithley_2182a.averaging_count(10)
    assert keithley_2182a.averaging_count() == 10


def test_trigger_system(keithley_2182a):
    """Test trigger system functionality."""
    # Test trigger source
    keithley_2182a.trigger_source("immediate")
    assert keithley_2182a.trigger_source() == "immediate"

    keithley_2182a.trigger_source("external")
    assert keithley_2182a.trigger_source() == "external"

    # Test trigger delay
    keithley_2182a.trigger_delay(0.1)
    assert keithley_2182a.trigger_delay() == pytest.approx(0.0, rel=1e-6)


def test_temperature_units(keithley_2182a):
    """Test temperature units setting."""
    # Test Kelvin
    keithley_2182a.temperature_units("kelvin")
    assert keithley_2182a.temperature_units() == "kelvin"

    # Test Celsius
    keithley_2182a.temperature_units("celsius")
    assert keithley_2182a.temperature_units() == "celsius"

    # Test Fahrenheit
    keithley_2182a.temperature_units("fahrenheit")
    assert keithley_2182a.temperature_units() == "fahrenheit"


def test_display_control(keithley_2182a):
    """Test display control."""
    # Test display enable/disable
    keithley_2182a.display_enabled(True)
    assert keithley_2182a.display_enabled() is True

    keithley_2182a.display_enabled(False)
    assert keithley_2182a.display_enabled() is False


def test_filters(keithley_2182a):
    """Test analog and digital filter control."""
    # Test analog filter
    keithley_2182a.analog_filter(True)
    assert keithley_2182a.analog_filter() is True

    keithley_2182a.analog_filter(False)
    assert keithley_2182a.analog_filter() is False

    # Test digital filter
    keithley_2182a.digital_filter(True)
    assert keithley_2182a.digital_filter() is True

    keithley_2182a.digital_filter(False)
    assert keithley_2182a.digital_filter() is False


def test_input_impedance(keithley_2182a):
    """Test input impedance control."""
    keithley_2182a.input_impedance(True)
    assert keithley_2182a.input_impedance() is True

    keithley_2182a.input_impedance(False)
    assert keithley_2182a.input_impedance() is False


def test_auto_zero(keithley_2182a):
    """Test auto-zero functionality."""
    # Test via method
    keithley_2182a.auto_zero(True)
    assert keithley_2182a.get_auto_zero() is True

    keithley_2182a.auto_zero(False)
    assert keithley_2182a.get_auto_zero() is False


def test_trigger_commands(keithley_2182a):
    """Test trigger command functionality."""
    # Test initiate measurement
    keithley_2182a.initiate_measurement()

    # Test trigger
    keithley_2182a.trigger()

    # Test abort
    keithley_2182a.abort_measurement()


def test_configuration_methods(keithley_2182a):
    """Test configuration convenience methods."""
    # Test voltage measurement configuration
    keithley_2182a.configure_voltage_measurement(
        auto_range=True, nplc=1.0, auto_zero=True
    )
    assert keithley_2182a.mode() == "dc voltage"
    assert keithley_2182a.auto_range_enabled() is True
    assert keithley_2182a.nplc() == pytest.approx(1.0, rel=1e-6)

    # Test temperature measurement configuration
    keithley_2182a.configure_temperature_measurement(units="celsius", nplc=1.0)
    assert keithley_2182a.mode() == "temperature"
    assert keithley_2182a.temperature_units() == "celsius"


def test_optimization_presets(keithley_2182a):
    """Test optimization preset methods."""
    # Test low noise optimization
    keithley_2182a.optimize_for_low_noise()
    assert keithley_2182a.nplc() == pytest.approx(10.0, rel=1e-6)
    assert keithley_2182a.averaging_enabled() is True
    assert keithley_2182a.averaging_count() == 10

    # Test speed optimization
    keithley_2182a.optimize_for_speed()
    assert keithley_2182a.nplc() == pytest.approx(0.1, rel=1e-6)
    assert keithley_2182a.averaging_enabled() is False


def test_measurement_speed_presets(keithley_2182a):
    """Test measurement speed preset functionality."""
    # Test fast preset
    keithley_2182a.set_measurement_speed("fast")
    assert keithley_2182a.nplc() == pytest.approx(0.1, rel=1e-6)
    assert keithley_2182a.analog_filter() is False
    assert keithley_2182a.digital_filter() is False

    # Test medium preset
    keithley_2182a.set_measurement_speed("medium")
    assert keithley_2182a.nplc() == pytest.approx(1.0, rel=1e-6)
    assert keithley_2182a.analog_filter() is True
    assert keithley_2182a.digital_filter() is False

    # Test slow preset
    keithley_2182a.set_measurement_speed("slow")
    assert keithley_2182a.nplc() == pytest.approx(10.0, rel=1e-6)
    assert keithley_2182a.analog_filter() is True
    assert keithley_2182a.digital_filter() is True


def test_statistics_measurement(keithley_2182a):
    """Test statistical measurement functionality."""
    # Set to voltage mode
    keithley_2182a.mode("dc voltage")

    # Test statistics measurement
    stats = keithley_2182a.measure_voltage_statistics(num_measurements=5)

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


def test_status_monitoring(keithley_2182a):
    """Test status monitoring functionality."""
    # Test measurement status
    status = keithley_2182a.get_measurement_status()

    assert "mode" in status
    assert "range" in status
    assert "auto_range" in status
    assert "nplc" in status
    assert "averaging_enabled" in status
    assert "trigger_source" in status
    assert "trigger_delay" in status


def test_error_handling(keithley_2182a):
    """Test error handling functionality."""
    # Test error query
    error_code, error_message = keithley_2182a.get_error()
    assert error_code == 0
    assert "No error" in error_message

    # Test clear errors
    keithley_2182a.clear_errors()


def test_self_test(keithley_2182a):
    """Test instrument self-test functionality."""
    result = keithley_2182a.self_test()
    assert result is True


def test_range_info(keithley_2182a):
    """Test range information functionality."""
    # Test voltage ranges
    keithley_2182a.mode("dc voltage")
    ranges = keithley_2182a.check_ranges()

    assert "available_ranges" in ranges
    assert "current_range" in ranges
    assert "auto_range" in ranges

    # Test temperature ranges
    keithley_2182a.mode("temperature")
    temp_ranges = keithley_2182a.check_ranges()

    assert "current_units" in temp_ranges


def test_reset(keithley_2182a):
    """Test instrument reset functionality."""
    # Change some settings
    keithley_2182a.nplc(5.0)
    keithley_2182a.averaging_enabled(True)

    # Reset the instrument
    keithley_2182a.reset()

    # The instrument should be reset (values may vary depending on defaults)
    # This test mainly checks that reset doesn't cause errors
