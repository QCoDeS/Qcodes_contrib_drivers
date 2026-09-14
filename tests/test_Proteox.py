import pytest
import sys
import subprocess
import types
import platform
from unittest.mock import MagicMock

from qcodes_contrib_drivers.drivers.QuantumDesign._decsvisa.src.decs_visa_tools import decs_visa_settings

# The following decorator makes the driver
# available to all the functions in this module
@pytest.fixture(scope="function", name="proteox_sim")

def proteox_driver_init_on_windows(monkeypatch):

    mock_process = MagicMock()
    mock_process.args = []
    mock_process.returncode = 0
    mock_process.wait.return_value = 0
    mock_process.communicate.return_value = (b"", b"")
    mock_process.__enter__.return_value = mock_process

    monkeypatch.setattr(
        subprocess,
        "Popen",
        MagicMock(return_value=mock_process),
    )

    # import driver after monkeypatching so it picks up the patched settings
    from qcodes_contrib_drivers.drivers.QuantumDesign import Proteox

    # Force the constructor onto the Windows subprocess branch
    #monkeypatch.setattr(Proteox, "running_on", lambda: "Windows-10")

    monkeypatch.setattr(Proteox, "HOST", "127.0.0.1")
    monkeypatch.setattr(Proteox, "PORT", "33578")
    monkeypatch.setattr(Proteox, "WRITE_DELIM", "\n")

    # Make all parameters available for testing
    monkeypatch.setattr(Proteox, "SYSTEM_HAS_MAGNET", True)
    monkeypatch.setattr(Proteox, "MAGNET_HAS_SWITCH", True)
    monkeypatch.setattr(Proteox, "DUAL_PTRS_FITTED", True)
    monkeypatch.setattr(Proteox, "DUAL_TURBO_FITTED", True)
    monkeypatch.setattr(Proteox, "HE3_FLOW_METER_FITTED", True)

    # initialise the driver with the simulation file
    proteox_sim = Proteox.DECS(
        "proteox_sim",
        decs_visa_path="dummy_decs_visa.py",  # never actually used
        pyvisa_sim_file="qcodes_contrib_drivers.sims:Proteox.yaml",
    )
    yield proteox_sim

    proteox_sim.close()

def proteox_driver_init_not_on_windows(monkeypatch):

    # Make HOST/PORT/WRITE_DELIM match the YAML
    monkeypatch.setattr(decs_visa_settings, "HOST", "127.0.0.1", raising=False)
    monkeypatch.setattr(decs_visa_settings, "PORT", "33576", raising=False)
    monkeypatch.setattr(decs_visa_settings, "WRITE_DELIM", "\n", raising=False)

    mock_process = MagicMock()
    mock_process.args = []
    mock_process.returncode = 0
    mock_process.wait.return_value = 0
    mock_process.communicate.return_value = (b"", b"")
    mock_process.__enter__.return_value = mock_process

    monkeypatch.setattr(
        subprocess,
        "Popen",
        MagicMock(return_value=mock_process),
    )

    monkeypatch.setattr(platform, "platform",  lambda: "Linux-5.15")

    from qcodes_contrib_drivers.drivers.QuantumDesign import Proteox

    # Make all parameters available for testing
    monkeypatch.setattr(Proteox, "SYSTEM_HAS_MAGNET", True)
    monkeypatch.setattr(Proteox, "MAGNET_HAS_SWITCH", True)
    monkeypatch.setattr(Proteox, "DUAL_PTRS_FITTED", True)
    monkeypatch.setattr(Proteox, "DUAL_TURBO_FITTED", True)
    monkeypatch.setattr(Proteox, "HE3_FLOW_METER_FITTED", True)

    # initialise the driver with the simulation file
    proteox_sim = Proteox.DECS(
        "proteox_sim",
        decs_visa_path="dummy_decs_visa.py",  # never actually used
        pyvisa_sim_file="qcodes_contrib_drivers.sims:Proteox.yaml",
    )
    yield proteox_sim

    proteox_sim.close()

def test_idn(proteox_sim) -> None:
    """Test identification."""
    expected_idn = {
        "vendor": "QD - Oxford",
        "model": "DECS",
    }
    idn = proteox_sim.get_idn()
    assert idn["vendor"] == expected_idn["vendor"]
    assert idn["model"] == expected_idn["model"]

def test_Sample_Temp(proteox_sim) -> None:
    """Test Sample Temperature."""
    # check a float is returned
    value= proteox_sim.Sample_Temperature()
    assert isinstance(value, float)

def test_MC_Temp(proteox_sim) -> None:
    """Test Mixing Chamber Temperature."""
    # check a float is returned
    value= proteox_sim.Mixing_Chamber_Temperature()
    assert isinstance(value, float)


def test_MC_Setpoint(proteox_sim) -> None:
    """Test Mixing Chamber Setpoint."""
    # check a float is returned
    value= proteox_sim.Mixing_Chamber_Temperature_Target()
    assert isinstance(value, float)

def test_MC_Heater_Power(proteox_sim) -> None:
    """Test Mixing Chamber Heater Power."""
    # check a float is returned
    value= proteox_sim.Mixing_Chamber_Heater_Power()
    assert isinstance(value, float)

def test_Still_Plate_Temp(proteox_sim) -> None:
    """Test Still Plate Temperature."""
    # check a float is returned
    value= proteox_sim.Still_Plate_Temperature()
    assert isinstance(value, float)

def test_Still_Heater_Power(proteox_sim) -> None:
    """Test Still Heater Power."""
    # check a float is returned
    value= proteox_sim.Still_Heater_Power()
    assert isinstance(value, float)

def test_Cold_Plate_Temp(proteox_sim) -> None:
    """Test Cold Plate Temperature."""
    # check a float is returned
    value= proteox_sim.Cold_Plate_Temperature()
    assert isinstance(value, float)

def test_Sorb_Temp(proteox_sim) -> None:
    """Test Sorb Temperature."""
    # check a float is returned
    value= proteox_sim.Sorb_Temperature()
    assert isinstance(value, float)

def test_PT1_Head_Temp(proteox_sim) -> None:
    """Test PT1 Head Temperature."""
    # check a float is returned
    value= proteox_sim.PT1_Head_Temperature()
    assert isinstance(value, float)

def test_PT1_Plate_Temp(proteox_sim) -> None:
    """Test PT1 Plate Temperature."""
    # check a float is returned
    value= proteox_sim.PT1_Plate_Temperature()
    assert isinstance(value, float)

def test_PT2_Head_Temp(proteox_sim) -> None:
    """Test PT2 Head Temperature."""
    # check a float is returned
    value= proteox_sim.PT2_Head_Temperature()
    assert isinstance(value, float)

def test_PT2_Plate_Temp(proteox_sim) -> None:
    """Test PT2 Plate Temperature."""
    # check a float is returned
    value= proteox_sim.PT2_Plate_Temperature()
    assert isinstance(value, float)

def test_OVC_Pressure(proteox_sim) -> None:
    """Test OVC Pressure."""
    # check a float is returned
    value= proteox_sim.OVC_Pressure()
    assert isinstance(value, float)

def test_P1_Pressure(proteox_sim) -> None:
    """Test P1 Pressure."""
    # check a float is returned
    value= proteox_sim.P1_Pressure()
    assert isinstance(value, float)

def test_P2_Pressure(proteox_sim) -> None:
    """Test P2 Pressure."""
    # check a float is returned
    value= proteox_sim.P2_Pressure()
    assert isinstance(value, float)

def test_P3_Pressure(proteox_sim) -> None:
    """Test P3 Pressure."""
    # check a float is returned
    value= proteox_sim.P3_Pressure()
    assert isinstance(value, float)

def test_P4_Pressure(proteox_sim) -> None:
    """Test P4 Pressure."""
    # check a float is returned
    value= proteox_sim.P4_Pressure()
    assert isinstance(value, float)

def test_P5_Pressure(proteox_sim) -> None:
    """Test P5 Pressure."""
    # check a float is returned
    value= proteox_sim.P5_Pressure()
    assert isinstance(value, float)

def test_P6_Pressure(proteox_sim) -> None:
    """Test P6 Pressure."""
    # check a float is returned
    value= proteox_sim.P6_Pressure()
    assert isinstance(value, float)

def test_Mag_Temp(proteox_sim) -> None:
    """Test Magnet Temperature."""
    # check a float is returned
    value= proteox_sim.Magnet_Temperature()
    assert isinstance(value, float)

def test_Mag_State(proteox_sim) -> None:
    """Test Magnet State."""
    # check a float is returned
    value= proteox_sim.Magnet_State()
    assert isinstance(value, str)

def test_Magnetic_Field_Vector(proteox_sim) -> None:
    """Test Magnetic Field Vector."""
    # check a tuple of three floats is returned
    value = proteox_sim.Magnetic_Field_Vector()
    assert isinstance(value, tuple)
    assert len(value) == 3
    assert all(isinstance(v, float) for v in value)

def test_Magnet_Current_Vector(proteox_sim) -> None:
    """Test Magnet Current Vector."""
    # check a tuple of three floats is returned
    value = proteox_sim.Magnet_Current_Vector()
    assert isinstance(value, tuple)
    assert len(value) == 3
    assert all(isinstance(v, float) for v in value)

def test_magnetic_field_parameters_set_raw(proteox_sim, capsys) -> None:
    """Test MagneticFieldParameters.set_raw prints the expected warning."""

    proteox_sim.Magnetic_Field_Vector([1.0, 2.0, 3.0])

    captured = capsys.readouterr()
    assert "*** Field cannot be set directly with this function ***" in captured.out

def test_magnet_current_parameters_set_raw(proteox_sim, capsys) -> None:
    """Test MagnetCurrentParameters.set_raw prints the expected warning."""

    proteox_sim.Magnet_Current_Vector([1.0, 2.0, 3.0])

    captured = capsys.readouterr()
    assert "*** Current cannot be set directly with this function ***" in captured.out

def test_Switch_State(proteox_sim) -> None:
    """Test Switch State."""
    # check a string is returned
    value = proteox_sim.Switch_State()
    assert isinstance(value, str)

def test_He3_Flow(proteox_sim) -> None:
    """Test He3_Flow."""
    # check a float is returned
    value = proteox_sim.He3_Flow()
    assert isinstance(value, float)

def test_mixing_chamber_heater_off(proteox_sim) -> None:
    """Test that the mixing chamber heater can be turned off."""

    proteox_sim.mixing_chamber_heater_off()

def test_still_heater_off(proteox_sim) -> None:
    """Test that the still heater can be turned off."""

    proteox_sim.still_heater_off()

def test_set_magnet_target_rate(proteox_sim, capsys) -> None:
    """Test that the magnet target can be set."""

    proteox_sim.set_magnet_target(0,0,0,0,'RATE',0.3,False)
    proteox_sim.set_magnet_target(0,0,0,0,'RATE',0.3,True)

    proteox_sim.set_magnet_target(0,0,0,0,'TIME',0.3,False)
    proteox_sim.set_magnet_target(0,0,0,0,'TIME',0.3,True)

    proteox_sim.set_magnet_target(0,0,0,0,'ASAP',0.3,False)
    proteox_sim.set_magnet_target(0,0,0,0,'ASAP',0.3,True)

    proteox_sim.set_magnet_target(0,0,0,0,'INCORRECT',0.3,False)
    captured = capsys.readouterr()
    assert "Incorrect inputs." in captured.out
    assert "[coord,x,y,z,mode,rate,persist_on_completion]" in captured.out

def test_set_output_current_target(proteox_sim, capsys) -> None:
    """Test that the output current target can be set."""

    proteox_sim.set_output_current_target(0,0,0,'RATE',0.3,False)
    proteox_sim.set_output_current_target(0,0,0,'RATE',0.3,True)

    proteox_sim.set_output_current_target(0,0,0,'TIME',0.3,False)
    proteox_sim.set_output_current_target(0,0,0,'TIME',0.3,True)

    proteox_sim.set_output_current_target(0,0,0,'ASAP',0.3,False)
    proteox_sim.set_output_current_target(0,0,0,'ASAP',0.3,True)

    proteox_sim.set_output_current_target(0,0,0,'INCORRECT',0.3,False)
    captured = capsys.readouterr()
    assert "Incorrect inputs." in captured.out
    assert "[x,y,z,mode,rate,persist_on_completion]" in captured.out

def test_set_magnet_state(proteox_sim, monkeypatch, capsys) -> None:
    """Test that the magnet state can be set."""

    calls = []

    def fake_param_setter(set_cmd, value):
        calls.append((set_cmd, value))

    monkeypatch.setattr(proteox_sim, "_param_setter", fake_param_setter)

    proteox_sim.set_magnet_state(0)
    captured = capsys.readouterr()
    assert "Holding Field" in captured.out
    assert calls[-1] == ("set_MAG_STATE", 0)

    proteox_sim.set_magnet_state(10)
    captured = capsys.readouterr()
    assert "Entering Persistent Mode" in captured.out
    assert calls[-1] == ("set_MAG_STATE", 10)

    proteox_sim.set_magnet_state(20)
    captured = capsys.readouterr()
    assert "Leaving Persistent Mode" in captured.out
    assert calls[-1] == ("set_MAG_STATE", 20)

    proteox_sim.set_magnet_state(30)
    captured = capsys.readouterr()
    assert "Sweeping Field" in captured.out
    assert calls[-1] == ("set_MAG_STATE", 30)

    proteox_sim.set_magnet_state(40)
    captured = capsys.readouterr()
    assert "Sweeping PSU Output" in captured.out
    assert calls[-1] == ("set_MAG_STATE", 40)

    proteox_sim.set_magnet_state(5)
    captured = capsys.readouterr()
    assert "**NB** Demandable states are:" in captured.out
    assert "0 - Hold, 10 - Enter Persistent Mode" in captured.out
    assert "20 - Leave Persistent Mode, 30 - Sweep Field, 40 - Sweep PSU Output" in captured.out
    assert calls[-1] != ("set_MAG_STATE", 5)

def test_sweep_field(proteox_sim, monkeypatch) -> None:
    """Test that sweep_field can be called."""

    calls = []

    def fake_param_setter(set_cmd, value):
        calls.append((set_cmd, value))

    monkeypatch.setattr(proteox_sim, "_param_setter", fake_param_setter)

    proteox_sim.sweep_field()
    assert calls[-1] == ("set_MAG_STATE", 30)

def test_sweep_psu_output(proteox_sim, monkeypatch) -> None:
    """Test that sweep_psu_output can be called."""

    calls = []

    def fake_param_setter(set_cmd, value):
        calls.append((set_cmd, value))

    monkeypatch.setattr(proteox_sim, "_param_setter", fake_param_setter)

    proteox_sim.sweep_psu_output()
    assert calls[-1] == ("set_MAG_STATE", 40)

def test_enter_persistent_mode(proteox_sim, monkeypatch) -> None:
    """Test that enter_persistent_mode can be called."""

    calls = []

    def fake_param_setter(set_cmd, value):
        calls.append((set_cmd, value))

    monkeypatch.setattr(proteox_sim, "_param_setter", fake_param_setter)

    proteox_sim.enter_persistent_mode()
    assert calls[-1] == ("set_MAG_STATE", 10)

def test_leave_persistent_mode(proteox_sim, monkeypatch) -> None:
    """Test that leave_persistent_mode can be called."""

    calls = []

    def fake_param_setter(set_cmd, value):
        calls.append((set_cmd, value))

    monkeypatch.setattr(proteox_sim, "_param_setter", fake_param_setter)

    proteox_sim.leave_persistent_mode()
    assert calls[-1] == ("set_MAG_STATE", 20)

def test_hold_field(proteox_sim, monkeypatch) -> None:
    """Test that hold_field can be called."""

    calls = []

    def fake_param_setter(set_cmd, value):
        calls.append((set_cmd, value))

    monkeypatch.setattr(proteox_sim, "_param_setter", fake_param_setter)

    proteox_sim.hold_field()
    assert calls[-1] == ("set_MAG_STATE", 0)

def test_open_switch(proteox_sim, monkeypatch) -> None:
    """Test that open_switch can be called."""

    calls = []

    def fake_param_setter(set_cmd, value):
        calls.append((set_cmd, value))

    monkeypatch.setattr(proteox_sim, "_param_setter", fake_param_setter)

    proteox_sim.open_switch()
    assert calls[-1] == ("set_MAG_STATE", 20)

def test_close_switch(proteox_sim, monkeypatch) -> None:
    """Test that close_switch can be called."""

    calls = []

    def fake_param_setter(set_cmd, value):
        calls.append((set_cmd, value))

    monkeypatch.setattr(proteox_sim, "_param_setter", fake_param_setter)

    proteox_sim.close_switch()
    assert calls[-1] == ("set_MAG_STATE", 10)

def test_sweep_small_field_step(proteox_sim, monkeypatch) -> None:
    """Test that sweep_small_field_step can be called."""

    calls = []
    def fake_param_setter(set_cmd, value):
        calls.append((set_cmd, value))

    state_calls = 0
    def fake_magnet_state() -> str:
            nonlocal state_calls
            state_calls += 1
            if state_calls >= 5:
                return "Holding Not Persistent"
            return "Ramping Magnetic Field"

    monkeypatch.setattr(proteox_sim, "Magnet_State", fake_magnet_state)
    monkeypatch.setattr(proteox_sim, "_param_setter", fake_param_setter)

    proteox_sim.sweep_small_field_step('X')
    assert calls[-1] == ("set_MAG_X_STATE", 10)

    proteox_sim.sweep_small_field_step('Y')
    assert calls[-1] == ("set_MAG_Y_STATE", 10)

    proteox_sim.sweep_small_field_step('Z')
    assert calls[-1] == ("set_MAG_Z_STATE", 10)


def test_wait_until_field_stable(monkeypatch, proteox_sim) -> None:
    """Test the wait-until-field-stable loop without sleeping in real time."""

    # Simulate a magnet that is not stable at first, then becomes stable.
    states = iter(["Ramping Magnetic Field", "Ramping Magnetic Field", "Holding Not Persistent"])
    calls = []

    # Return the next mocked status value each time the loop checks the magnet state.
    def fake_magnet_state() -> str:
        calls.append("checked")
        return next(states, "Holding Not Persistent")

    # Avoid real waiting and replace the status with the mocked sequence.
    monkeypatch.setattr(proteox_sim, "Magnet_State", fake_magnet_state)

    proteox_sim.wait_until_field_stable()

    # Ensure the loop actually checked the state more than once.
    assert len(calls) >= 2

def test_wait_until_field_stable_timeout(monkeypatch, proteox_sim, capsys) -> None:
    """Test that the timeout path runs when the magnet stays in a ramping state."""

    state_calls = 0

    def fake_magnet_state() -> str:
        nonlocal state_calls
        state_calls += 1
        if state_calls >= 30:
            return "Holding Not Persistent"
        return "Ramping Magnetic Field"

    monkeypatch.setattr(proteox_sim, "Magnet_State", fake_magnet_state)
    monkeypatch.setattr(proteox_sim, "_param_setter", lambda *args, **kwargs: None)

    proteox_sim.wait_until_field_stable_timeout(timeout=1)
    captured = capsys.readouterr()

    assert "Status:" in captured.out

def test_wait_until_field_persistent(monkeypatch, proteox_sim) -> None:
    """Test the wait-until-field-persistent loop without sleeping in real time."""

    # Simulate a magnet that is not stable at first, then becomes stable.
    states = iter(["Ramping Magnetic Field", "Ramping Magnetic Field", "Holding Persistent"])
    calls = []

    # Return the next mocked status value each time the loop checks the magnet state.
    def fake_magnet_state() -> str:
        calls.append("checked")
        return next(states, "Holding Persistent")

    # Avoid real waiting and replace the status with the mocked sequence.
    monkeypatch.setattr(proteox_sim, "Magnet_State", fake_magnet_state)

    proteox_sim.wait_until_field_persistent()

    # Ensure the loop actually checked the state more than once.
    assert len(calls) >= 2

def test_wait_until_field_depersisted(monkeypatch, proteox_sim) -> None:
    """Test the wait-until-field-depersisted loop without sleeping in real time."""

    # Simulate a magnet that is not stable at first, then becomes stable.
    states = iter(["Ramping Magnetic Field", "Ramping Magnetic Field", "Holding Not Persistent"])
    calls = []

    # Return the next mocked status value each time the loop checks the magnet state.
    def fake_magnet_state() -> str:
        calls.append("checked")
        return next(states, "Holding Not Persistent")

    # Avoid real waiting and replace the status with the mocked sequence.
    monkeypatch.setattr(proteox_sim, "Magnet_State", fake_magnet_state)

    proteox_sim.wait_until_field_depersisted()

    # Ensure the loop actually checked the state more than once.
    assert len(calls) >= 2

def test_wait_until_temperature_stable_std_control(proteox_sim, capsys) -> None:
    """Test the wait_until_temperature_stable_std_control."""

    proteox_sim.wait_until_temperature_stable_std_control(stable_mean=0.1, stable_std=0.1, time_between_readings=0.1)
    captured = capsys.readouterr()
    assert 'Temperature =' in captured.out
    assert 'Temperature stable after' in captured.out
    assert 'Mean-Target = ' in captured.out
    assert 'StdDev = ' in captured.out

def test_publish(proteox_sim) -> None:
    """Test publish command"""

    proteox_sim.publish('Test', 'Measurement')
