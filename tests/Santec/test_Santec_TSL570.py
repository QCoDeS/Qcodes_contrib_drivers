"""Tests for Santec TSL-570 driver.

These tests require a connected TSL570 instrument or a simulation backend.
To run with simulation, create a TSL570.yaml file in the sims directory.
"""

import re
import time

import pytest

from qcodes_contrib_drivers.drivers.Santec import SantecTSL570


@pytest.fixture(scope="module")
def driver():
    """Create TSL570 instrument instance."""
    tsl = SantecTSL570("TSL570", address="192.168.50.29", port=5000)
    # Or use simulation:
    # import qcodes_contrib_drivers.sims as sims
    # visalib = sims.__file__.replace('__init__.py', 'TSL570.yaml@sim')
    # tsl = TSL570("TSL570", address="GPIB::1::INSTR", visalib=visalib)
    yield tsl
    tsl.close()


def test_reset(driver):
    """Test instrument reset."""
    driver.reset()


def test_idn(driver):
    """Test instrument identification."""
    idn_dict = driver.get_idn()
    assert 'model' in idn_dict
    assert idn_dict['model'] == 'TSL-570'


def test_wavelength_fine(driver):
    """Test fine wavelength tuning."""
    for fine_val in [-50.0, 0.0, 50.0]:
        driver.wavelength_fine(fine_val)
        assert driver.wavelength_fine() == fine_val


def test_disable_fine_tuning(driver):
    """Test disable fine-tuning command."""
    driver.disable_fine_tuning()


# Wavelength parameters
def test_wavelength_set_get(driver):
    """Test wavelength parameter set and get."""
    test_wavelength = 1550e-9  # 1550 nm in meters
    driver.wavelength(test_wavelength)
    assert driver.wavelength() == pytest.approx(test_wavelength, abs=1e-12)


def test_wavelength_unit(driver):
    """Test wavelength unit selection."""
    for unit in ["NM", "THz"]:
        driver.wavelength_unit(unit)
        assert driver.wavelength_unit() == unit


def test_frequency_set_get(driver):
    """Test frequency parameter set and get."""
    test_freq = 193.5e12  # ~1550 nm
    driver.frequency(test_freq)
    assert driver.frequency() == pytest.approx(test_freq, abs=1e9)


# Coherence control
def test_coherence_control(driver):
    """Test coherence control."""
    driver.coherence_control(True)
    assert driver.coherence_control() == True
    driver.coherence_control(False)
    assert driver.coherence_control() == False


# Power parameters
def test_output(driver):
    """Test output state control."""
    driver.output(False)
    assert driver.output() == False
    driver.output(True)
    assert driver.output() == True


def test_power_auto(driver):
    """Test automatic power control."""
    driver.power_auto(False)
    assert driver.power_auto() == False
    driver.power_auto(True)
    assert driver.power_auto() == True


def test_power_attenuation(driver):
    """Test attenuator control."""
    driver.power_auto(False)  # Disable auto to set attenuation
    for atten in [20, 10, 0]:
        driver.power_attenuation(atten)
        assert driver.power_attenuation() == atten


def test_power_set_get(driver):
    """Test power parameter set and get."""
    driver.power_auto(False)  # Disable auto to set power
    test_power = 2.0  # dBm
    driver.power(test_power)
    assert driver.power() == pytest.approx(test_power, abs=0.1)


def test_power_actual(driver):
    """Test actual power readout."""
    power_actual = driver.power_actual()
    assert isinstance(power_actual, (int, float))


def test_shutter(driver):
    """Test shutter control."""
    driver.shutter(True)
    assert driver.shutter() == True
    driver.shutter(False)
    assert driver.shutter() == False


def test_power_unit(driver):
    """Test power unit selection."""
    for unit in ["dBm", "mW"]:
        driver.power_unit(unit)
        assert driver.power_unit() == unit


# Sweep parameters
def test_sweep_start_stop(driver):
    """Test sweep start and stop wavelength."""
    start_wl = 1510e-9
    stop_wl = 1580e-9
    driver.sweep_start_wavelength(start_wl)
    driver.sweep_stop_wavelength(stop_wl)
    assert driver.sweep_start_wavelength() == pytest.approx(start_wl, abs=1e-12)
    assert driver.sweep_stop_wavelength() == pytest.approx(stop_wl, abs=1e-12)


def test_sweep_start_stop_frequency(driver):
    """Test sweep start and stop frequency."""
    start_freq = 185e12  # ~1643 nm
    stop_freq = 195e12  # ~1500 nm
    driver.sweep_start_frequency(start_freq)
    driver.sweep_stop_frequency(stop_freq)
    assert driver.sweep_start_frequency() == pytest.approx(start_freq, abs=1e9)
    assert driver.sweep_stop_frequency() == pytest.approx(stop_freq, abs=1e9)


# TODO : Command times out (bug in instrument firmware?). Try to update firmware.
def test_sweep_range_limits(driver):
    """Test sweep range minimum and maximum readout."""
    min_wl = driver.sweep_range_minimum()
    max_wl = driver.sweep_range_maximum()
    assert isinstance(min_wl, float)
    assert isinstance(max_wl, float)
    assert min_wl == pytest.approx(min_wl)
    assert max_wl == pytest.approx(max_wl)
    assert min_wl < max_wl


def test_sweep_mode(driver):
    """Test sweep mode selection."""
    for mode in [0, 1, 2, 3]:
        driver.sweep_mode(mode)
        assert driver.sweep_mode() == mode


def test_sweep_speed(driver):
    """Test sweep speed configuration."""
    for speed in [1, 10, 100]:
        driver.sweep_speed(speed)
        assert driver.sweep_speed() == speed


def test_sweep_step(driver):
    """Test sweep step size."""
    step = 1e-9  # 1 nm
    driver.sweep_step(step)
    assert driver.sweep_step() == pytest.approx(step, abs=1e-13)


def test_sweep_dwell(driver):
    """Test sweep dwell time."""
    for dwell in [0.1, 1.0, 10.0]:
        driver.sweep_dwell(dwell)
        assert driver.sweep_dwell() == dwell


def test_sweep_cycles(driver):
    """Test sweep cycle count."""
    for cycles in [100, 10, 1]:
        driver.sweep_cycles(cycles)
        assert driver.sweep_cycles() == cycles


def test_sweep_count(driver):
    """Test sweep count readout."""
    count = driver.sweep_count()
    assert isinstance(count, int)
    assert count >= 0


def test_sweep_delay(driver):
    """Test sweep delay time."""
    for delay in [0.0, 1.0, 10.0]:
        driver.sweep_delay(delay)
        assert driver.sweep_delay() == delay


def test_sweep_state(driver):
    """Test sweep state readout."""
    state = driver.sweep_state()
    assert state in ["STOPPED", "RUNNING", "TRIGGER_STANDBY", "PREPARING"]


# Data readout
def test_readout_points(driver):
    """Test readout points query."""
    points = driver.readout_points()
    assert isinstance(points, int)
    assert 0 <= points <= 500_000


# Modulation parameters
def test_modulation_state(driver):
    """Test amplitude modulation state."""
    driver.modulation_state(True)
    assert driver.modulation_state() == True
    driver.modulation_state(False)
    assert driver.modulation_state() == False


def test_modulation_source(driver):
    """Test modulation source selection."""
    for source in ["COHERENCE_CONTROL", "INTENSITY_MODULATION", "FREQUENCY_MODULATION"]:
        driver.modulation_source(source)
        assert driver.modulation_source() == source


def test_wavelength_offset(driver):
    """Test wavelength offset."""
    test_offset = 0.05e-9  # 0.05 nm
    driver.wavelength_offset(test_offset)
    assert driver.wavelength_offset() == pytest.approx(test_offset, abs=1e-13)


# Trigger parameters
def test_trigger_input_external(driver):
    """Test external trigger input enable."""
    driver.trigger_input_external(False)
    assert driver.trigger_input_external() == False
    driver.trigger_input_external(True)
    assert driver.trigger_input_external() == True


def test_trigger_input_polarity(driver):
    """Test trigger input polarity."""
    for pol in ["RISE", "FALL"]:
        driver.trigger_input_polarity(pol)
        assert driver.trigger_input_polarity() == pol


def test_trigger_input_standby(driver):
    """Test trigger input standby."""
    driver.trigger_input_standby(False)
    assert driver.trigger_input_standby() == False
    driver.trigger_input_standby(True)
    assert driver.trigger_input_standby() == True


def test_trigger_output_timing(driver):
    """Test trigger output timing configuration."""
    for timing in ["NONE", "STOP", "START", "STEP"]:
        driver.trigger_output_timing(timing)
        assert driver.trigger_output_timing() == timing


def test_trigger_output_polarity(driver):
    """Test trigger output polarity."""
    for pol in ["RISE", "FALL"]:
        driver.trigger_output_polarity(pol)
        assert driver.trigger_output_polarity() == pol


def test_trigger_output_step(driver):
    """Test trigger output interval."""
    step = 1e-9  # 1 nm
    driver.trigger_output_step(step)
    assert driver.trigger_output_step() == pytest.approx(step, abs=1e-13)


def test_trigger_output_setting(driver):
    """Test trigger output period mode."""
    for setting in ["WAVELENGTH", "TIME"]:
        driver.trigger_output_setting(setting)
        assert driver.trigger_output_setting() == setting


def test_trigger_through(driver):
    """Test trigger through mode."""
    driver.trigger_through(False)
    assert driver.trigger_through() == False
    driver.trigger_through(True)
    assert driver.trigger_through() == True


# System parameters
def test_system_error(driver):
    """Test error queue readout."""
    error = driver.system_error()
    assert error['code'] in [0, -102, -103, -108, -109, -113, -148, -200, -222. - 410]


def test_command_set_param(driver):
    """Test command set readout."""
    cmd_set = driver.command_set_param()
    assert cmd_set in ["LEGACY", "SCPI"]


def test_system_lock(driver):
    """Test external interlock status readout."""
    lock_status = driver.system_lock()
    assert isinstance(lock_status, bool)


def test_system_alert(driver):
    """Test alert information readout."""
    alert = driver.system_alert()
    assert isinstance(alert, str)


def test_system_version(driver):
    """Test firmware version readout."""
    version = driver.system_version()
    assert isinstance(version, str)
    assert re.match(r'^\d{4}\.\d{4}\.\d{4}$', version)


def test_system_code(driver):
    """Test product code readout."""
    code = driver.system_code()
    assert isinstance(code, str)
    assert re.match(r'^[A-Z]-\d{6}-[A-Z]-[A-Z]-[A-Z]{2}-\d{2}-\d$', code)


# Method tests

def test_sweep_single(driver):
    """Test single sweep start."""
    driver.sweep_single()
    time.sleep(0.5)  # Allow time for sweep to start
    state = driver.sweep_state()
    assert state in ["RUNNING", "TRIGGER_STANDBY", "PREPARING"]  # Should be running or preparing


def test_sweep_stop(driver):
    """Test sweep stop."""
    driver.sweep_stop()
    time.sleep(0.1)
    assert driver.sweep_state() == "STOPPED"  # Should be stopped


def test_sweep_repeat(driver):
    """Test repeat sweep start."""
    driver.sweep_repeat()
    time.sleep(0.5)
    state = driver.sweep_state()
    assert state in ["RUNNING", "TRIGGER_STANDBY", "PREPARING"]  # Should be running or preparing


def test_software_trigger(driver):
    """Test software trigger command."""
    driver.trigger_input_standby(True)
    driver.software_trigger()
