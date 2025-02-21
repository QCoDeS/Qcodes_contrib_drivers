import pytest
from qcodes_contrib_drivers.drivers.PeakTech.PeakTech_15xx import PeakTech15xx

@pytest.fixture(scope="function")
def driver():
    peaktech_sim = PeakTech15xx(
        "peaktech_sim",
        "ASRL1::INSTR",
        pyvisa_sim_file="qcodes_contrib_drivers.sims:PeakTech15xx.yaml",
    )
    yield peaktech_sim
    peaktech_sim.close()

def test_init(driver):
    """
    Test that the instrument initializes correctly and returns the expected IDN information.
    """
    idn_dict = driver.get_idn()
    assert idn_dict["vendor"] == "PeakTech"
    assert idn_dict["model"] == "15xx (Simulated)"
