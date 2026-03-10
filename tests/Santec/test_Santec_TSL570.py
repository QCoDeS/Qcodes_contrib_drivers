"""Tests for Santec TSL-570 driver.

These tests require a connected TSL570 instrument or a simulation backend.
To run with simulation, create a TSL570.yaml file in the sims directory.
"""

import re
import time

import numpy as np
import pytest

from qcodes_contrib_drivers.drivers.Santec import SantecTSL570


@pytest.fixture(scope="module")
def driver():
    """Create TSL570 instrument instance."""
    tsl = SantecTSL570("TSL570", address="TCPIP::192.168.50.29::5000::SOCKET")  # VisaInstrument
    yield tsl
    tsl.close()


def test_reset(driver):
    """Test instrument reset."""
    driver.reset()


def test_idn(driver):
    """Test instrument identification."""
    idn_dict = driver.get_idn()
    assert isinstance(idn_dict, dict)
    assert 'model' in idn_dict
    assert idn_dict['model'] == 'TSL-570'


@pytest.mark.parametrize("fine_val", [-50.0, 0.0, 50.0])
def test_wavelength_fine(driver, fine_val):
    """Test fine wavelength tuning."""
    driver.wavelength_fine(fine_val)
    assert driver.wavelength_fine() == fine_val


def test_disable_fine_tuning(driver):
    """Test disable fine-tuning command."""
    driver.disable_fine_tuning()


def test_wavelength_set_get(driver):
    """Test wavelength parameter set and get."""
    test_wavelength = 1550e-9  # 1550 nm in meters
    driver.wavelength(test_wavelength)
    assert driver.wavelength() == pytest.approx(test_wavelength, abs=1e-12)


@pytest.mark.parametrize("unit", ["NM", "THz"])
def test_wavelength_unit(driver, unit):
    """Test wavelength unit selection."""
    driver.wavelength_unit(unit)
    assert driver.wavelength_unit() == unit


def test_frequency_set_get(driver):
    """Test frequency parameter set and get."""
    test_freq = 193.5e12  # ~1550 nm
    driver.frequency(test_freq)
    assert driver.frequency() == pytest.approx(test_freq, abs=1e9)


@pytest.mark.parametrize("state", [True, False])
def test_coherence_control(driver, state):
    """Test coherence control."""
    driver.coherence_control(state)
    assert driver.coherence_control() == state


@pytest.mark.parametrize("state", [False, True])
def test_output(driver, state):
    """Test output state control."""
    driver.output(state)
    assert driver.output() == state


@pytest.mark.parametrize("state", [False, True])
def test_power_auto(driver, state):
    """Test automatic power control."""
    driver.power_auto(state)
    assert driver.power_auto() == state


@pytest.mark.parametrize("atten", [20, 10, 0])
def test_power_attenuation(driver, atten):
    """Test attenuator control."""
    driver.power_auto(False)  # Disable auto to set attenuation
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


@pytest.mark.parametrize("state", [True, False])
def test_shutter(driver, state):
    """Test shutter control."""
    driver.shutter(state)
    assert driver.shutter() == state


@pytest.mark.parametrize("unit", ["dBm", "mW"])
def test_power_unit(driver, unit):
    """Test power unit selection."""
    driver.power_unit(unit)
    assert driver.power_unit() == unit


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


# @pytest.mark.skip(reason="Command times out - firmware bug. Try updating firmware.")
def test_sweep_range_limits(driver):
    """Test sweep range minimum and maximum readout."""
    min_wl = driver.sweep_range_minimum()
    max_wl = driver.sweep_range_maximum()
    assert isinstance(min_wl, float)
    assert isinstance(max_wl, float)
    assert min_wl == pytest.approx(min_wl)
    assert max_wl == pytest.approx(max_wl)
    assert min_wl < max_wl


@pytest.mark.parametrize("mode", [0, 1, 2, 3])
def test_sweep_mode(driver, mode):
    """Test sweep mode selection."""
    driver.sweep_mode(mode)
    assert driver.sweep_mode() == mode


@pytest.mark.parametrize("speed", [1, 10, 100])
def test_sweep_speed(driver, speed):
    """Test sweep speed configuration."""
    driver.sweep_speed(speed)
    assert driver.sweep_speed() == speed


def test_sweep_step(driver):
    """Test sweep step size."""
    step = 1e-9  # 1 nm
    driver.sweep_step(step)
    assert driver.sweep_step() == pytest.approx(step, abs=1e-13)


@pytest.mark.parametrize("dwell", [0.1, 1.0, 10.0])
def test_sweep_dwell(driver, dwell):
    """Test sweep dwell time."""
    driver.sweep_dwell(dwell)
    assert driver.sweep_dwell() == dwell


@pytest.mark.parametrize("cycles", [100, 10, 1])
def test_sweep_cycles(driver, cycles):
    """Test sweep cycle count."""
    driver.sweep_cycles(cycles)
    assert driver.sweep_cycles() == cycles


def test_sweep_count(driver):
    """Test sweep count readout."""
    count = driver.sweep_count()
    assert isinstance(count, int)
    assert count >= 0


@pytest.mark.parametrize("delay", [0.0, 1.0, 10.0])
def test_sweep_delay(driver, delay):
    """Test sweep delay time."""
    driver.sweep_delay(delay)
    assert driver.sweep_delay() == delay


def test_sweep_state(driver):
    """Test sweep state readout."""
    assert driver.sweep_state() in ["STOPPED", "RUNNING", "TRIGGER_STANDBY", "PREPARING"]


def test_readout_points(driver):
    """Test readout points query."""
    points = driver.readout_points()
    assert isinstance(points, int)
    assert 0 <= points <= 500_000


def test_readout_data(driver):
    """Test wavelength logging data readout."""
    # Get the number of data points first
    num_points = driver.readout_points()
    data = driver.readout_data()
    assert isinstance(data, np.ndarray)
    assert len(data) == num_points

    # All values should be valid wavelengths (in meters, typically in infrared range)
    for wavelength in data:
        assert isinstance(wavelength, float)
        assert 1e-6 < wavelength < 2e-6  # Expect wavelengths in range 1-2 µm (typical for TSL570)


def test_readout_power_data(driver):
    """Test power logging data readout."""
    num_points = driver.readout_points()
    data = driver.readout_power_data()
    assert isinstance(data, np.ndarray)
    assert len(data) == num_points

    for power in data:
        assert isinstance(power, (float, np.floating))
        assert -120 <= power <= 30


@pytest.mark.parametrize("state", [True, False])
def test_modulation_state(driver, state):
    """Test amplitude modulation state."""
    driver.modulation_state(state)
    assert driver.modulation_state() == state


@pytest.mark.parametrize("source", ["COHERENCE_CONTROL", "INTENSITY_MODULATION", "FREQUENCY_MODULATION"])
def test_modulation_source(driver, source):
    """Test modulation source selection."""
    driver.modulation_source(source)
    assert driver.modulation_source() == source


def test_wavelength_offset(driver):
    """Test wavelength offset."""
    test_offset = 0.05e-9  # 0.05 nm
    driver.wavelength_offset(test_offset)
    assert driver.wavelength_offset() == pytest.approx(test_offset, abs=1e-13)


@pytest.mark.parametrize("state", [False, True])
def test_trigger_input_external(driver, state):
    """Test external trigger input enable."""
    driver.trigger_input_external(state)
    assert driver.trigger_input_external() == state


@pytest.mark.parametrize("pol", ["RISE", "FALL"])
def test_trigger_input_polarity(driver, pol):
    """Test trigger input polarity."""
    driver.trigger_input_polarity(pol)
    assert driver.trigger_input_polarity() == pol


@pytest.mark.parametrize("state", [False, True])
def test_trigger_input_standby(driver, state):
    """Test trigger input standby."""
    driver.trigger_input_standby(state)
    assert driver.trigger_input_standby() == state


@pytest.mark.parametrize("timing", ["NONE", "STOP", "START", "STEP"])
def test_trigger_output_timing(driver, timing):
    """Test trigger output timing configuration."""
    driver.trigger_output_timing(timing)
    assert driver.trigger_output_timing() == timing


@pytest.mark.parametrize("pol", ["RISE", "FALL"])
def test_trigger_output_polarity(driver, pol):
    """Test trigger output polarity."""
    driver.trigger_output_polarity(pol)
    assert driver.trigger_output_polarity() == pol


def test_trigger_output_step(driver):
    """Test trigger output interval."""
    step = 1e-9  # 1 nm
    driver.trigger_output_step(step)
    assert driver.trigger_output_step() == pytest.approx(step, abs=1e-13)


@pytest.mark.parametrize("setting", ["WAVELENGTH", "TIME"])
def test_trigger_output_setting(driver, setting):
    """Test trigger output period mode."""
    driver.trigger_output_setting(setting)
    assert driver.trigger_output_setting() == setting


@pytest.mark.parametrize("state", [False, True])
def test_trigger_through(driver, state):
    """Test trigger through mode."""
    driver.trigger_through(state)
    assert driver.trigger_through() == state


def test_system_error(driver):
    """Test error queue readout."""
    error = driver.system_error()
    assert isinstance(error, dict)
    assert 'code' in error
    assert error['code'] in [0, -102, -103, -108, -109, -113, -148, -200, -222, -410]


def test_command_set_param(driver):
    """Test command set readout."""
    cmd_set = driver.command_set()
    assert isinstance(cmd_set, str)
    assert cmd_set == "SCPI"


def test_system_lock(driver):
    """Test external interlock status readout."""
    lock_status = driver.system_lock()
    assert isinstance(lock_status, bool)


def test_system_alert(driver):
    """Test alert information readout."""
    alert = driver.system_alert()
    assert isinstance(alert, str)
    assert len(alert) > 0


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


def test_sweep_single(driver):
    """Test single sweep start."""
    driver.sweep_single()
    time.sleep(0.5)  # Allow time for sweep to start
    assert driver.sweep_state() in ["RUNNING", "TRIGGER_STANDBY", "PREPARING"]  # Should be running or preparing


def test_sweep_stop(driver):
    """Test sweep stop."""
    driver.sweep_stop()
    time.sleep(0.1)
    assert driver.sweep_state() == "STOPPED"  # Should be stopped


def test_sweep_repeat(driver):
    """Test repeat sweep start."""
    driver.sweep_repeat()
    time.sleep(0.5)
    assert driver.sweep_state() in ["RUNNING", "TRIGGER_STANDBY", "PREPARING"]  # Should be running or preparing


def test_software_trigger(driver):
    """Test software trigger command."""
    driver.trigger_input_standby(True)
    driver.software_trigger()
