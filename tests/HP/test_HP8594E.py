import pytest
import numpy as np
from qcodes_contrib_drivers.drivers.HP.HP8594E import HP8594E


@pytest.fixture(scope="function")
def driver():
    HP_sim = HP8594E(
        "HP_sim",
        "GPIB::1::INSTR",
        pyvisa_sim_file="qcodes_contrib_drivers.sims:HP8594E.yaml",
    )
    yield HP_sim

    HP_sim.close()


def test_init(driver):
    """
    Test that simple initialisation works
    """

    idn_dict = driver.IDN()

    assert idn_dict["vendor"] == "QCoDeS"


def test_freq_axis(driver):
    driver.start_freq(9000)
    driver.stop_freq(2900000000.0)
    assert (driver.freq_axis() == np.linspace(9000, 2900000000.0, 401)).all
