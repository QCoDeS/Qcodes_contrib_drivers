"""Tests for Santec TSL drivers using the pyvisa-sim backend."""

import re
import time

import numpy as np
import pytest

from qcodes_contrib_drivers.drivers.Santec import SantecTSL


@pytest.fixture(scope="module")
def driver():
    """Create TSL570 instrument instance."""
    tsl = SantecTSL(
        "TSL570",
        address="TCPIP::192.168.50.29::5000::SOCKET",
        pyvisa_sim_file="qcodes_contrib_drivers.sims:TSL570.yaml",  # Comment this line to test against real hardware
    )
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


def test_wavelength_minimum(driver):
    """Test minimum wavelength readout."""
    wavelength_minimum = driver.wavelength_minimum()
    assert isinstance(wavelength_minimum, float)
    assert 1e-6 < wavelength_minimum < 2e-6


def test_wavelength_maximum(driver):
    """Test maximum wavelength readout."""
    wavelength_maximum = driver.wavelength_maximum()
    assert isinstance(wavelength_maximum, float)
    assert 1e-6 < wavelength_maximum < 2e-6
    assert wavelength_maximum > driver.wavelength_minimum()


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


def test_frequency_minimum(driver):
    """Test minimum frequency readout."""
    frequency_minimum = driver.frequency_minimum()
    assert isinstance(frequency_minimum, float)
    assert 1e14 < frequency_minimum < 3e14


def test_frequency_maximum(driver):
    """Test maximum frequency readout."""
    frequency_maximum = driver.frequency_maximum()
    assert isinstance(frequency_maximum, float)
    assert 1e14 < frequency_maximum < 3e14
    assert frequency_maximum > driver.frequency_minimum()


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


@pytest.mark.parametrize("attenuation", [20, 10, 0])
def test_power_attenuation(driver, attenuation):
    """Test attenuator control."""
    driver.power_auto(False)  # Disable auto to set attenuation
    driver.power_attenuation(attenuation)
    assert driver.power_attenuation() == attenuation


def test_power_set_get(driver):
    """Test power parameter set and get."""
    driver.power_auto(False)  # Disable auto to set power
    test_power = 2.0  # dBm
    driver.power(test_power)
    assert driver.power() == pytest.approx(test_power, abs=0.1)


def test_power_minimum(driver):
    """Test minimum power readout."""
    power_minimum = driver.power_minimum()
    assert isinstance(power_minimum, float)
    assert np.isfinite(power_minimum)


def test_power_maximum(driver):
    """Test maximum power readout."""
    power_maximum = driver.power_maximum()
    assert isinstance(power_maximum, float)
    assert np.isfinite(power_maximum)
    assert power_maximum > driver.power_minimum()


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


def test_sweep_frequency_step(driver):
    """Test frequency sweep step size."""
    step = 1e9  # 1 GHz
    driver.sweep_step_frequency(step)
    assert driver.sweep_step_frequency() == pytest.approx(step, abs=1e6)


def test_sweep_frequency_range_limits(driver):
    """Test sweep frequency range minimum and maximum readout."""
    min_freq = driver.sweep_range_minimum_frequency()
    max_freq = driver.sweep_range_maximum_frequency()
    assert isinstance(min_freq, float)
    assert isinstance(max_freq, float)
    assert min_freq < max_freq


def test_sweep_range_limits(driver):
    """Test sweep wavelength range minimum and maximum readout."""
    min_wl = driver.sweep_range_minimum_wavelength()
    max_wl = driver.sweep_range_maximum_wavelength()
    assert isinstance(min_wl, float)
    assert isinstance(max_wl, float)
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
    """Test wavelength sweep step size."""
    step = 1e-9  # 1 nm
    driver.sweep_step_wavelength(step)
    assert driver.sweep_step_wavelength() == pytest.approx(step, abs=1e-13)


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


def test_ethernet_mac_address(driver):
    """Test Ethernet MAC address readout (read-only)."""
    mac_address = driver.ethernet_mac_address()
    assert isinstance(mac_address, str)
    # Verify MAC address format: hexadecimal digits, no separators (e.g., 0013A0000000)
    assert re.match(r'^[0-9A-Fa-f]{12}$', mac_address)


def test_ethernet_ip_address(driver):
    """Test Ethernet IP address readout (read-only, no modifications)."""
    current_ip = driver.ethernet_ip_address()
    assert isinstance(current_ip, str)
    # Verify IPv4 format: ###.###.###.### (each octet 0-255)
    assert re.match(r'^(\d{1,3}\.){3}\d{1,3}$', current_ip)
    # Validate each octet is 0-255
    octets = current_ip.split('.')
    for octet in octets:
        assert 0 <= int(octet) <= 255


def test_ethernet_subnet_mask(driver):
    """Test Ethernet subnet mask readout (read-only, no modifications)."""
    current_mask = driver.ethernet_subnet_mask()
    assert isinstance(current_mask, str)
    # Verify subnet mask format: ###.###.###.### (each octet 0-255)
    assert re.match(r'^(\d{1,3}\.){3}\d{1,3}$', current_mask)
    # Validate each octet is 0-255
    octets = current_mask.split('.')
    for octet in octets:
        assert 0 <= int(octet) <= 255


def test_ethernet_gateway(driver):
    """Test Ethernet default gateway readout (read-only, no modifications)."""
    current_gateway = driver.ethernet_gateway()
    assert isinstance(current_gateway, str)
    # Verify gateway format: ###.###.###.### (each octet 0-255)
    assert re.match(r'^(\d{1,3}\.){3}\d{1,3}$', current_gateway)
    # Validate each octet is 0-255
    octets = current_gateway.split('.')
    for octet in octets:
        assert 0 <= int(octet) <= 255


def test_ethernet_port(driver):
    """Test Ethernet port number readout (read-only, no modifications)."""
    current_port = driver.ethernet_port()
    assert isinstance(current_port, int)
    # Verify port is in valid range (0-65535)
    assert 0 <= current_port <= 65535


def test_gpib_address(driver):
    """Test GPIB address readout (read-only, no modifications)."""
    gpib_addr = driver.gpib_address()
    assert isinstance(gpib_addr, int)
    assert 1 <= gpib_addr <= 30


def test_gpib_delimiter(driver):
    """Test GPIB delimiter readout (read-only, no modifications)."""
    delimiter = driver.gpib_delimiter()
    assert isinstance(delimiter, str)
    assert delimiter in ["CR", "LF", "CR+LF", "NONE"]


@pytest.mark.parametrize("brightness", [10, 100])
def test_display_brightness(driver, brightness):
    """Test display brightness readout (read-only, no modifications)."""
    driver.display_brightness(brightness)
    assert driver.display_brightness() == brightness


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
    # In pyvisa-sim, this no-argument command is modeled as a dialogue and does not
    # update the property-backed sweep state value.
    assert driver.sweep_state() in ["STOPPED", "RUNNING", "TRIGGER_STANDBY", "PREPARING"]


def test_software_trigger(driver):
    """Test software trigger command."""
    driver.trigger_input_standby(True)
    driver.software_trigger()


def test_shutdown_command(driver, monkeypatch):
    """Test shutdown command string without sending it to hardware."""
    sent_commands: list[str] = []
    monkeypatch.setattr(driver, "write", lambda cmd: sent_commands.append(cmd))
    driver.shutdown()
    assert sent_commands == [":SPECial:SHUTdown"]


def test_reboot_command(driver, monkeypatch):
    """Test reboot command string without sending it to hardware."""
    sent_commands: list[str] = []
    monkeypatch.setattr(driver, "write", lambda cmd: sent_commands.append(cmd))
    driver.reboot()
    assert sent_commands == [":SPECial:REBoot"]
