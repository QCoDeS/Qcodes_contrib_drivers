import pytest
import sys
import subprocess
import types
import requests

# The following decorator makes the driver
# available to all the functions in this module
@pytest.fixture(scope="function", name="m91_sim")
def _m91_driver():

    # import driver
    from qcodes_contrib_drivers.drivers.Lakeshore import M91_FastHall

    # initialise the driver with the simulation file
    m91_sim = M91_FastHall.M91_FastHall(
        "M91_sim",
        address="TCPIP0::127.0.0.1::33577::SOCKET",
        pyvisa_sim_file="qcodes_contrib_drivers.sims:Lakeshore_M91_FastHall.yaml",
    )
    yield m91_sim

    m91_sim.close()


def test_idn(m91_sim) -> None:
    """Test identification."""
    expected_idn = {
        "vendor": "Lake Shore",
        "model": "M91",
    }
    idn = m91_sim.get_idn()
    assert idn["vendor"] == expected_idn["vendor"]
    assert idn["model"] == expected_idn["model"]

def test_keypad_lock(m91_sim) -> None:
    """Test Keypad Lock."""
    # check a bool is returned
    value= m91_sim.keypad_lock()
    assert isinstance(value, bool)

    # check setting
    m91_sim.keypad_lock(False)
    assert m91_sim.keypad_lock() == False

def test_error_queue(m91_sim) -> None:
    """Test Error Queue."""
    value = m91_sim.read_error_queue()
    print(value)

    assert isinstance(value, str)
    assert "No error" in value


# Testing settings values etc.
def test_sample_type(m91_sim) -> None:
    """Test Sample Type."""
    # check a str is returned
    value= m91_sim.sample_type()
    assert isinstance(value, str)

    # check setting
    m91_sim.sample_type('Hall_bar')
    assert m91_sim.sample_type() == 'Hall_bar'

    m91_sim.sample_type('van_der_Pauw')
    assert m91_sim.sample_type() == 'van_der_Pauw'

    # check pass if value is already set
    m91_sim.sample_type('van_der_Pauw')
    assert m91_sim.sample_type() == 'van_der_Pauw'

def test_contact_check_excitation(m91_sim) -> None:
    """Test Contact Check excitation type."""
    # check a bool is returned for auto optimise
    value = m91_sim.ContactCheck.auto_optimise()
    assert isinstance(value, bool)

    # check a string is returned when auto optimise is off
    value = m91_sim.ContactCheck.auto_optimise(False)
    value = m91_sim.ContactCheck.excitation_type()
    assert isinstance(value, str)

    # check setting
    m91_sim.ContactCheck.excitation_type('CURR')
    assert m91_sim.ContactCheck.excitation_type() == 'CURR'

    # Check excitation current start parameter exists
    m91_sim.ContactCheck.excitation_current_start(0.1)
    value = m91_sim.ContactCheck.excitation_current_start()
    assert isinstance(value, float)

    m91_sim.ContactCheck.excitation_type('VOLT')
    assert m91_sim.ContactCheck.excitation_type() == 'VOLT'

    # Check excitation voltage start parameter exists
    m91_sim.ContactCheck.excitation_voltage_start(0.1)
    value = m91_sim.ContactCheck.excitation_voltage_start()
    assert isinstance(value, float)


@pytest.mark.parametrize("excitation_name", [
    "CURR",
    "VOLT"
])
def test_four_wire_excitation(m91_sim,excitation_name) -> None:
    """Test Four Wire excitation type setting."""
    # check setting
    m91_sim.FourWire.excitation_type(excitation_name)
    assert m91_sim.FourWire.excitation_type() == excitation_name

def test_min_snr(m91_sim) -> None:
    """Test setting minimum signal to noise ratio parameter."""
    m91_sim.Resistivity.minimum_SNR("INF")
    assert m91_sim.Resistivity.maximum_samples.min_val == pytest.approx(1.0, rel=1e-6)

    m91_sim.Resistivity.minimum_SNR(100)
    assert m91_sim.Resistivity.maximum_samples.min_val == pytest.approx(10, rel=1e-6)

def test_resistivity_optimise_setter(m91_sim) -> None:
    """Test that Resistivity optimise setter adds/removes associated parameters."""
    m91_sim.Resistivity.auto_optimise(False)
    m91_sim.Resistivity.excitation_type("CURR")
    assert "excitation_current_value" in m91_sim.Resistivity.parameters.keys()
    m91_sim.Resistivity.optimise_setter(True)
    assert "excitation_current_value" not in m91_sim.Resistivity.parameters.keys()

    m91_sim.Resistivity.auto_optimise(False)
    m91_sim.Resistivity.excitation_type("VOLT")
    assert "excitation_voltage_value" in m91_sim.Resistivity.parameters.keys()
    m91_sim.Resistivity.optimise_setter(True)
    assert "excitation_voltage_value" not in m91_sim.Resistivity.parameters.keys()

def test_fasthall_optimise_setter(m91_sim) -> None:
    """Test that FastHall optimise setter adds/removes associated parameters."""
    m91_sim.FastHall.auto_optimise(False)
    m91_sim.FastHall.excitation_type("CURR")
    assert "excitation_current_value" in m91_sim.FastHall.parameters.keys()
    m91_sim.FastHall.optimise_setter(True)
    assert "excitation_current_value" not in m91_sim.FastHall.parameters.keys()

    m91_sim.FastHall.auto_optimise(False)
    m91_sim.FastHall.excitation_type("VOLT")
    assert "excitation_voltage_value" in m91_sim.FastHall.parameters.keys()
    m91_sim.FastHall.optimise_setter(True)
    assert "excitation_voltage_value" not in m91_sim.FastHall.parameters.keys()

def test_fasthall_optimise_setter_exception(m91_sim,monkeypatch) -> None:
    """Test exception for FastHall optimise setter."""
    m91_sim.FastHall.auto_optimise(False)
    m91_sim.FastHall.excitation_type("VOLT")
    assert "excitation_voltage_value" in m91_sim.FastHall.parameters.keys()

    def raise_error():
        raise Exception
    monkeypatch.setattr(m91_sim.FastHall,'add_parameter', raise_error)
    m91_sim.FastHall.optimise_setter(False)


def test_contact_check_optimise_setter(m91_sim) -> None:
    """Test that Resistivity optimise setter adds/removes associated parameters."""
    m91_sim.ContactCheck.auto_optimise(False)
    m91_sim.ContactCheck.excitation_type("CURR")
    assert "excitation_current_start" in m91_sim.ContactCheck.parameters.keys()
    m91_sim.ContactCheck.optimise_setter(True)
    assert "excitation_current_start" not in m91_sim.ContactCheck.parameters.keys()

    m91_sim.ContactCheck.auto_optimise(False)
    m91_sim.ContactCheck.excitation_type("VOLT")
    assert "excitation_voltage_start" in m91_sim.ContactCheck.parameters.keys()
    m91_sim.ContactCheck.optimise_setter(True)
    assert "excitation_voltage_start" not in m91_sim.ContactCheck.parameters.keys()

def test_display_results(m91_sim,capsys) -> None:
    """Test Display Results produces results from json data and gives an error for other data types."""
    data = m91_sim.FourWire.get_all_results()
    m91_sim.display_measurement_results(data)

    captured = capsys.readouterr()
    assert "Setup", "Results" in captured.out

    # Test error
    m91_sim.display_measurement_results(1)
    captured = capsys.readouterr()
    assert "Data is not of the correct type. Data should be of type SimpleNamespace." in captured.out

def test_measurement_reset(m91_sim,capsys) -> None:
    """Test measurement reset runs without error"""
    m91_sim.Resistivity.reset()
    captured = capsys.readouterr()
    assert "RESISTIVITY measurement reset." in captured.out

def test_setting_val(m91_sim) -> None:
    """ Test setting values.
    Test values are set to min/max if input is outside lower/upper limits"""
    m91_sim.ContactCheck.auto_optimise(False)
    m91_sim.ContactCheck.excitation_type("CURR")
    m91_sim.ContactCheck.excitation_current_start(1)
    assert m91_sim.ContactCheck.excitation_current_start() == pytest.approx(0.1, rel=1e-6)

    m91_sim.ContactCheck.excitation_current_start(-1)
    assert m91_sim.ContactCheck.excitation_current_start() == pytest.approx(-0.1, rel=1e-6)

    m91_sim.ContactCheck.excitation_current_start(-0.01)
    assert m91_sim.ContactCheck.excitation_current_start() == pytest.approx(-0.01, rel=1e-6)

    # Check TypeError for str input
    with pytest.raises(TypeError):
        m91_sim.ContactCheck.excitation_current_start("AUTO")

def test_setting_val_or_string(m91_sim) -> None:
    """ Test setting values.
    Test values are set to min/max if input is outside lower/upper limits"""
    m91_sim.ContactCheck.auto_optimise(False)
    m91_sim.ContactCheck.excitation_type("CURR")
    m91_sim.ContactCheck.excitation_current_range(1)
    assert m91_sim.ContactCheck.excitation_current_range() == pytest.approx(0.1, rel=1e-6)

    m91_sim.ContactCheck.excitation_current_range(-1)
    assert m91_sim.ContactCheck.excitation_current_range() == pytest.approx(0, rel=1e-6)

    m91_sim.ContactCheck.excitation_current_range(0.01)
    assert m91_sim.ContactCheck.excitation_current_range() == pytest.approx(0.01, rel=1e-6)

    m91_sim.ContactCheck.excitation_current_range("AUTO")
    assert m91_sim.ContactCheck.excitation_current_range() == "AUTO"

def test_setting_val_or_string_incorrect(m91_sim) -> None:
    """Test that trying to set parameters with wrong data type doesn't work"""
    m91_sim.ContactCheck.auto_optimise(False)
    m91_sim.ContactCheck.excitation_type("CURR")

    m91_sim.ContactCheck.excitation_current_start.set_raw(None)
    assert m91_sim.ContactCheck.excitation_current_start.get_raw() == None

    m91_sim.ContactCheck.excitation_current_range.set_raw(None)
    assert m91_sim.ContactCheck.excitation_current_range.get_raw() == None


# Type checking
def test_contact_check_running(m91_sim) -> None:
    """Test Contact Check running."""
    # check a bool is returned
    value= m91_sim.ContactCheck.get_running_status()
    assert isinstance(value, bool)

def test_four_wire_running(m91_sim) -> None:
    """Test Four Wire running."""
    # check a bool is returned
    value= m91_sim.FourWire.get_running_status()
    assert isinstance(value, bool)

def test_resistivity_running(m91_sim) -> None:
    """Test Resistivity running."""
    # check a bool is returned
    value= m91_sim.Resistivity.get_running_status()
    assert isinstance(value, bool)

def test_fasthall_running(m91_sim) -> None:
    """Test FastHall running."""
    # check a bool is returned
    value= m91_sim.FastHall.get_running_status()
    assert isinstance(value, bool)

def test_dchall_running(m91_sim) -> None:
    """Test DC Hall running."""
    # check a bool is returned
    value= m91_sim.DCHall.get_running_status()
    assert isinstance(value, bool)

def test_dchall_waiting(m91_sim) -> None:
    """Test DC Hall waiting."""
    # check a bool is returned
    value= m91_sim.DCHall.get_waiting_status()
    assert isinstance(value, bool)

def test_contact_check_results(m91_sim) -> None:
    """Test Contact Check results."""
    # check a SimpleNamespace is returned
    value= m91_sim.ContactCheck.get_results()
    assert isinstance(value, types.SimpleNamespace)

def test_contact_check_results_all(m91_sim) -> None:
    """Test Contact Check all results."""
    # check a SimpleNamespace is returned
    value= m91_sim.ContactCheck.get_all_results()
    assert isinstance(value, types.SimpleNamespace)

def test_dchall_results(m91_sim) -> None:
    """Test DC Hall results."""
    # check a SimpleNamespace is returned
    value= m91_sim.DCHall.get_results()
    assert isinstance(value, types.SimpleNamespace)

def test_dchall_results_all(m91_sim) -> None:
    """Test DC Hall all results."""
    # check a SimpleNamespace is returned
    value= m91_sim.DCHall.get_all_results()
    assert isinstance(value, types.SimpleNamespace)

def test_fasthall_results(m91_sim) -> None:
    """Test FastHall results."""
    # check a SimpleNamespace is returned
    value= m91_sim.FastHall.get_results()
    assert isinstance(value, types.SimpleNamespace)

def test_fasthall_results_all(m91_sim) -> None:
    """Test FastHall all results."""
    # check a SimpleNamespace is returned
    value= m91_sim.FastHall.get_all_results()
    assert isinstance(value, types.SimpleNamespace)

def test_four_wire_results(m91_sim) -> None:
    """Test Four Wire results."""
    # check a SimpleNamespace is returned
    value= m91_sim.FourWire.get_results()
    assert isinstance(value, types.SimpleNamespace)

def test_four_wire_results_all(m91_sim) -> None:
    """Test Four Wire all results."""
    # check a SimpleNamespace is returned
    value= m91_sim.FourWire.get_all_results()
    assert isinstance(value, types.SimpleNamespace)

def test_resistivity_results(m91_sim) -> None:
    """Test Resistivity results."""
    # check a SimpleNamespace is returned
    value= m91_sim.Resistivity.get_results()
    assert isinstance(value, types.SimpleNamespace)

def test_resistivity_results_all(m91_sim) -> None:
    """Test Resistivity all results."""
    # check a SimpleNamespace is returned
    value= m91_sim.Resistivity.get_all_results()
    assert isinstance(value, types.SimpleNamespace)


# Checking measurements run
def test_contact_check_start(m91_sim,monkeypatch,capsys) -> None:
    """Test Contact Check measurement runs without error"""
    inputs = iter([True,True,False,None])
    monkeypatch.setattr(m91_sim.ContactCheck,'get_running_status', lambda : next(inputs))

    m91_sim.ContactCheck.auto_optimise(True)
    m91_sim.sample_type('van_der_Pauw')
    m91_sim.ContactCheck.start()

    captured = capsys.readouterr()
    assert "complete" in captured.out

    inputs = iter([True,True,False,None])
    monkeypatch.setattr(m91_sim.ContactCheck,'get_running_status', lambda : next(inputs))

    m91_sim.ContactCheck.auto_optimise(False)
    m91_sim.ContactCheck.excitation_type("CURR")
    m91_sim.ContactCheck.excitation_current_start(-0.01)
    m91_sim.ContactCheck.excitation_current_end(0.01)
    m91_sim.sample_type('van_der_Pauw')
    m91_sim.ContactCheck.start()

    captured = capsys.readouterr()
    assert "complete" in captured.out

    inputs = iter([True,True,False,None])
    monkeypatch.setattr(m91_sim.ContactCheck,'get_running_status', lambda : next(inputs))

    m91_sim.sample_type('Hall_bar')
    m91_sim.ContactCheck.excitation_current_start(-0.01)
    m91_sim.ContactCheck.excitation_current_end(0.01)
    m91_sim.ContactCheck.start()

    captured = capsys.readouterr()
    assert "complete" in captured.out

def test_fasthall_start(m91_sim,monkeypatch,capsys) -> None:
    """Test FastHall measurement runs without error"""
    inputs = iter([True,True,False,None])
    monkeypatch.setattr(m91_sim.FastHall,'get_running_status', lambda : next(inputs))

    m91_sim.FastHall.auto_optimise(True)
    m91_sim.FastHall.start()

    captured = capsys.readouterr()
    assert "complete" in captured.out

    inputs = iter([True,True,False,None])
    monkeypatch.setattr(m91_sim.FastHall,'get_running_status', lambda : next(inputs))

    m91_sim.FastHall.auto_optimise(False)
    m91_sim.FastHall.excitation_type("CURR")
    m91_sim.FastHall.excitation_current_value(0.001)
    m91_sim.FastHall.resistivity(100)
    data = m91_sim.FastHall.start()

    captured = capsys.readouterr()
    assert "complete" in captured.out
    assert isinstance(data, types.SimpleNamespace)

def test_dchall_start(m91_sim,monkeypatch,capsys) -> None:
    """Test DC Hall measurement runs without error"""

    inputs = iter([True,True,False,None])
    monkeypatch.setattr(m91_sim.DCHall,'get_running_status', lambda : next(inputs))

    m91_sim.sample_type('Hall_bar')
    m91_sim.DCHall.excitation_current_value(0.01)
    m91_sim.DCHall.resistivity(100)
    data = m91_sim.DCHall.start()

    captured = capsys.readouterr()
    assert "complete" in captured.out
    assert isinstance(data, types.SimpleNamespace)

    inputs = iter([True,True,False,None])
    monkeypatch.setattr(m91_sim.DCHall,'get_running_status', lambda : next(inputs))

    waiting_inputs = iter([False,True,None])
    monkeypatch.setattr(m91_sim.DCHall,'get_waiting_status', lambda : next(waiting_inputs))

    m91_sim.sample_type('van_der_Pauw')
    m91_sim.DCHall.excitation_current_value(0.01)
    m91_sim.DCHall.resistivity(100)
    m91_sim.DCHall.start()

    captured = capsys.readouterr()
    assert "complete" in captured.out
    assert "DC Hall measurement is in the waiting state" in captured.out

    # Check DC Hall measurement won't continue while not in a waiting state
    m91_sim.DCHall.continue_dc_hall()
    captured = capsys.readouterr()
    assert "ERROR: DC Hall measurement is not in a waiting state." in captured.out

def test_dchall_continue(m91_sim,monkeypatch,capsys) -> None:
    """Test DC Hall measurement will continue when in a waiting state"""
    def mock_waiting_status():
        return True
    monkeypatch.setattr(m91_sim.DCHall,'get_waiting_status',mock_waiting_status)

    inputs = iter([True,True,False,None])
    monkeypatch.setattr(m91_sim.DCHall,'get_running_status', lambda : next(inputs))

    data = m91_sim.DCHall.continue_dc_hall()

    captured = capsys.readouterr()
    assert "complete" in captured.out
    assert isinstance(data, types.SimpleNamespace)


def test_four_wire_start(m91_sim,monkeypatch,capsys) -> None:
    """Test Four Wire measurement runs without error"""
    inputs = iter([True,True,False,None])
    monkeypatch.setattr(m91_sim.FourWire,'get_running_status', lambda : next(inputs))

    m91_sim.FourWire.excitation_plus_channel(1)
    m91_sim.FourWire.excitation_minus_channel(2)
    m91_sim.FourWire.measure_plus_channel(3)
    m91_sim.FourWire.measure_minus_channel(4)
    m91_sim.FourWire.excitation_type("CURR")
    m91_sim.FourWire.excitation_current_value(0.001)
    data = m91_sim.FourWire.start()

    captured = capsys.readouterr()
    assert "complete" in captured.out
    assert isinstance(data, types.SimpleNamespace)

def test_resistivity_start(m91_sim,monkeypatch,capsys) -> None:
    """Test Resistivity measurement runs without error"""
    inputs = iter([True,True,False,None])
    monkeypatch.setattr(m91_sim.Resistivity,'get_running_status', lambda : next(inputs))

    m91_sim.Resistivity.auto_optimise(True)
    m91_sim.sample_type('van_der_Pauw')
    m91_sim.Resistivity.start()

    captured = capsys.readouterr()
    assert "complete" in captured.out

    inputs = iter([True,True,False,None])
    monkeypatch.setattr(m91_sim.Resistivity,'get_running_status', lambda : next(inputs))

    m91_sim.Resistivity.auto_optimise(False)
    m91_sim.Resistivity.excitation_type("CURR")
    m91_sim.Resistivity.excitation_current_value(0.01)
    m91_sim.Resistivity.start()

    captured = capsys.readouterr()
    assert "complete" in captured.out

    inputs = iter([True,True,False,None])
    monkeypatch.setattr(m91_sim.Resistivity,'get_running_status', lambda : next(inputs))

    m91_sim.sample_type('Hall_bar')
    m91_sim.Resistivity.excitation_type("CURR")
    m91_sim.Resistivity.excitation_current_value(0.01)
    data = m91_sim.Resistivity.start()

    captured = capsys.readouterr()
    assert "complete" in captured.out
    assert isinstance(data, types.SimpleNamespace)


# Testing errors and exceptions
def test_fasthall_not_running(m91_sim,monkeypatch,capsys) -> None:
    """Test error if FastHall does not run"""
    def mock_running_status():
        return False
    monkeypatch.setattr(m91_sim.FastHall,'get_running_status',mock_running_status)
    m91_sim.FastHall.start()

    captured = capsys.readouterr()
    assert "ERROR: Measurement unsuccessful." in captured.out

    m91_sim.FastHall.auto_optimise(False)
    m91_sim.FastHall.excitation_type("CURR")
    # Don't set a value - stays as None, so starting returns an error
    m91_sim.FastHall.start()

    captured = capsys.readouterr()
    assert "Invalid" in captured.out

def test_dchall_not_running(m91_sim,monkeypatch,capsys) -> None:
    """Test error if DC Hall does not run"""

    # Don't set any values - stay as None, so starting returns an error
    m91_sim.DCHall.start()
    captured = capsys.readouterr()
    assert "Invalid" in captured.out

    def mock_running_status():
        return False
    monkeypatch.setattr(m91_sim.DCHall,'get_running_status',mock_running_status)
    m91_sim.sample_type('van_der_Pauw')
    m91_sim.DCHall.excitation_current_value(0.01)
    m91_sim.DCHall.resistivity(100)
    m91_sim.DCHall.start()

    captured = capsys.readouterr()
    assert "ERROR: Measurement unsuccessful." in captured.out

    def mock_waiting_status():
        return True
    m91_sim.sample_type('van_der_Pauw')
    m91_sim.DCHall.excitation_current_value(0.01)
    m91_sim.DCHall.resistivity(100)
    monkeypatch.setattr(m91_sim.DCHall,'get_waiting_status',mock_waiting_status)
    m91_sim.DCHall.start()

    captured = capsys.readouterr()
    assert "ERROR: DC Hall measurement is in the waiting state." in captured.out

def test_dchall_not_continuing(m91_sim,monkeypatch,capsys) -> None:
    """Test error if DC Hall does not run"""
    def mock_waiting_status():
        return False
    monkeypatch.setattr(m91_sim.DCHall,'get_waiting_status',mock_waiting_status)
    m91_sim.sample_type('van_der_Pauw')
    m91_sim.DCHall.excitation_current_value(0.01)
    m91_sim.DCHall.resistivity(100)
    m91_sim.DCHall.continue_dc_hall()

    captured = capsys.readouterr()
    assert "ERROR: DC Hall measurement is not in a waiting state." in captured.out

    def mock_waiting_status():
        return True
    monkeypatch.setattr(m91_sim.DCHall,'get_waiting_status',mock_waiting_status)

    def mock_running_status():
        return False
    monkeypatch.setattr(m91_sim.DCHall,'get_running_status',mock_running_status)
    m91_sim.sample_type('van_der_Pauw')
    m91_sim.DCHall.excitation_current_value(0.01)
    m91_sim.DCHall.resistivity(100)
    m91_sim.DCHall.continue_dc_hall()

    captured = capsys.readouterr()
    assert "ERROR: Measurement unsuccessful." in captured.out

def test_contact_check_not_running(m91_sim,monkeypatch,capsys) -> None:
    """Test error if contact check does not run"""
    def mock_running_status():
        return False
    monkeypatch.setattr(m91_sim.ContactCheck,'get_running_status',mock_running_status)
    m91_sim.ContactCheck.start()

    captured = capsys.readouterr()
    assert "ERROR: Contact check unsuccessful." in captured.out

    m91_sim.ContactCheck.auto_optimise(False)
    m91_sim.ContactCheck.excitation_type("CURR")
    # Don't set a value - stays as None, so starting returns an error
    m91_sim.ContactCheck.start()

    captured = capsys.readouterr()
    assert "Invalid" in captured.out

def test_four_wire_not_running(m91_sim,monkeypatch,capsys) -> None:
    """Test error if Four Wire does not run"""

    # Don't set any values - stay as None, so starting returns an error
    m91_sim.FourWire.start()
    captured = capsys.readouterr()
    assert "Invalid" in captured.out

    def mock_running_status():
        return False
    m91_sim.FourWire.excitation_plus_channel(1)
    m91_sim.FourWire.excitation_minus_channel(2)
    m91_sim.FourWire.measure_plus_channel(3)
    m91_sim.FourWire.measure_minus_channel(4)
    m91_sim.FourWire.excitation_type("CURR")
    m91_sim.FourWire.excitation_current_value(0.001)
    monkeypatch.setattr(m91_sim.FourWire,'get_running_status',mock_running_status)
    m91_sim.FourWire.start()

    captured = capsys.readouterr()
    assert "ERROR: Measurement unsuccessful." in captured.out

def test_resistivity_not_running(m91_sim,monkeypatch,capsys) -> None:
    """Test error if Resistivity does not run"""
    def mock_running_status():
        return False
    monkeypatch.setattr(m91_sim.Resistivity,'get_running_status',mock_running_status)
    m91_sim.Resistivity.start()

    captured = capsys.readouterr()
    assert "ERROR: Measurement unsuccessful." in captured.out

    m91_sim.Resistivity.auto_optimise(False)
    m91_sim.Resistivity.excitation_type("CURR")
    # Don't set a value - stays as None, so starting returns an error
    m91_sim.Resistivity.start()

    captured = capsys.readouterr()
    assert "Invalid" in captured.out

def test_no_results(m91_sim,monkeypatch,capsys) -> None:
    def mock_cmd_name():
        return "NONE"

    monkeypatch.setattr(m91_sim.FastHall,'cmd_name',mock_cmd_name)
    m91_sim.FastHall.get_results()

    captured = capsys.readouterr()
    assert "Error getting results" in captured.out

    monkeypatch.setattr(m91_sim.FastHall,'cmd_name', mock_cmd_name)
    m91_sim.FastHall.get_all_results()

    captured = capsys.readouterr()
    assert "Error getting results" in captured.out

def test_contact_check_error_results(m91_sim,monkeypatch,capsys) -> None:
    """Test error trying to get contact check results."""
    def raise_error():
        raise Exception

    inputs = iter([True,True,False,None])
    monkeypatch.setattr(m91_sim.ContactCheck,'get_running_status', lambda : next(inputs))

    monkeypatch.setattr(m91_sim.ContactCheck,'get_all_results',raise_error)

    m91_sim.ContactCheck.auto_optimise(True)
    m91_sim.sample_type('van_der_Pauw')
    m91_sim.ContactCheck.start()

    captured = capsys.readouterr()
    assert "Failed to get data" in captured.out

def test_fasthall_error_results(m91_sim,monkeypatch,capsys) -> None:
    """Test error trying to get FastHall results."""
    def raise_error():
        raise Exception

    inputs = iter([True,True,False,None])
    monkeypatch.setattr(m91_sim.FastHall,'get_running_status', lambda : next(inputs))

    monkeypatch.setattr(m91_sim.FastHall,'get_results',raise_error)

    m91_sim.FastHall.auto_optimise(True)
    m91_sim.FastHall.start()

    captured = capsys.readouterr()
    assert "Failed to get data" in captured.out

def test_dchall_error_results(m91_sim,monkeypatch,capsys) -> None:
    """Test error trying to get DCHall results."""
    def raise_error():
        raise Exception

    inputs = iter([True,True,False,None])
    monkeypatch.setattr(m91_sim.DCHall,'get_running_status', lambda : next(inputs))

    monkeypatch.setattr(m91_sim.DCHall,'get_results',raise_error)

    m91_sim.sample_type('van_der_Pauw')
    m91_sim.DCHall.excitation_current_value(0.01)
    m91_sim.DCHall.resistivity(100)
    m91_sim.DCHall.start()

    captured = capsys.readouterr()
    assert "Failed to get data" in captured.out

def test_dchall_continue_error_results(m91_sim,monkeypatch,capsys) -> None:
    """Test error trying to get DCHall results from continue_dc_hall."""
    def raise_error():
        raise Exception
    def mock_waiting_status():
        return True
    monkeypatch.setattr(m91_sim.DCHall,'get_waiting_status',mock_waiting_status)

    inputs = iter([True,True,False,None])
    monkeypatch.setattr(m91_sim.DCHall,'get_running_status', lambda : next(inputs))

    monkeypatch.setattr(m91_sim.DCHall,'get_results',raise_error)

    m91_sim.sample_type('van_der_Pauw')
    m91_sim.DCHall.excitation_current_value(0.01)
    m91_sim.DCHall.resistivity(100)
    m91_sim.DCHall.continue_dc_hall()

    captured = capsys.readouterr()
    assert "Failed to get data" in captured.out

def test_four_wire_error_results(m91_sim,monkeypatch,capsys) -> None:
    """Test error trying to get Four Wire results."""
    def raise_error():
        raise Exception

    inputs = iter([True,True,False,None])
    monkeypatch.setattr(m91_sim.FourWire,'get_running_status', lambda : next(inputs))

    monkeypatch.setattr(m91_sim.FourWire,'get_results',raise_error)

    m91_sim.FourWire.excitation_plus_channel(1)
    m91_sim.FourWire.excitation_minus_channel(2)
    m91_sim.FourWire.measure_plus_channel(3)
    m91_sim.FourWire.measure_minus_channel(4)
    m91_sim.FourWire.excitation_type("CURR")
    m91_sim.FourWire.excitation_current_value(0.001)
    data = m91_sim.FourWire.start()

    captured = capsys.readouterr()
    assert "Failed to get data" in captured.out

def test_resistivity_error_results(m91_sim,monkeypatch,capsys) -> None:
    """Test error trying to get Resistivity results."""
    def raise_error():
        raise Exception

    inputs = iter([True,True,False,None])
    monkeypatch.setattr(m91_sim.Resistivity,'get_running_status', lambda : next(inputs))

    monkeypatch.setattr(m91_sim.Resistivity,'get_results',raise_error)

    m91_sim.Resistivity.auto_optimise(True)
    m91_sim.sample_type('van_der_Pauw')
    m91_sim.Resistivity.start()

    captured = capsys.readouterr()
    assert "Failed to get data" in captured.out
