import pytest
from unittest.mock import call
import numpy as np
import math
from .sim_qdac2_fixtures import qdac  # noqa
from qcodes_contrib_drivers.drivers.QDevil.QDAC2 import diff_matrix


def test_diff_matrix():
    # -----------------------------------------------------------------------
    diff = diff_matrix([0.1, 0.2], [[0.1, 0.3], [0.3, 0.2]])
    # -----------------------------------------------------------------------
    expected = np.array([[0.0, 0.1], [0.2, 0.0]])
    assert np.allclose(diff, expected)


def test_arrangement_steady_state(qdac, mocker):
    sleep_s = mocker.patch('qcodes_contrib_drivers.drivers.QDevil.QDAC2.sleep_s') # Don't sleep
    gates = {'sensor1': 1, 'plunger2': 2, 'plunger3': 3}
    arrangement = qdac.arrange(gates)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    nplc = 2
    currents_A = arrangement.currents_A(nplc=nplc)
    # -----------------------------------------------------------------------
    assert currents_A == [0.1, 0.2, 0.3]  # Hard-coded in simulation
    commands = qdac.get_recorded_scpi_commands()
    assert commands == [
        'sens:rang low,(@1,2,3)',
        '*stb?',
        'sens:nplc 2,(@1,2,3)',
        # (Sleep NPLC / line_freq)
        'read? (@1,2,3)',
    ]
    measure_s = (nplc + 1) / 50
    sleep_s.assert_has_calls([call(measure_s)])


def test_arrangement_leakage(qdac, mocker):  # noqa
    mocker.patch('qcodes_contrib_drivers.drivers.QDevil.QDAC2.sleep_s')
    gates = {'sensor1': 1, 'plunger2': 2, 'plunger3': 3}
    arrangement = qdac.arrange(gates)
    arrangement.set_virtual_voltages({'sensor1': 0.3, 'plunger3': 0.4})
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    nplc = 2
    leakage_matrix = arrangement.leakage(modulation_V=0.005, nplc=nplc)
    # -----------------------------------------------------------------------
    commands = qdac.get_recorded_scpi_commands()
    assert commands == [
        'sens:rang low,(@1,2,3)',
        '*stb?',
        'sens:nplc 2,(@1,2,3)',
        # Steady-state reading
        'read? (@1,2,3)',
        # First modulation
        'sour1:volt:mode fix',
        'sour1:volt 0.305',
        'sour2:volt:mode fix',
        'sour2:volt 0.0',
        'sour3:volt:mode fix',
        'sour3:volt 0.4',
        'sens:rang low,(@1,2,3)',
        '*stb?',
        'sens:nplc 2,(@1,2,3)',
        'read? (@1,2,3)',
        'sour1:volt:mode fix',
        'sour1:volt 0.3',
        'sour2:volt:mode fix',
        'sour2:volt 0.0',
        'sour3:volt:mode fix',
        'sour3:volt 0.4',
        # Second modulation
        'sour1:volt:mode fix',
        'sour1:volt 0.3',
        'sour2:volt:mode fix',
        'sour2:volt 0.005',
        'sour3:volt:mode fix',
        'sour3:volt 0.4',
        'sens:rang low,(@1,2,3)',
        '*stb?',
        'sens:nplc 2,(@1,2,3)',
        'read? (@1,2,3)',
        'sour1:volt:mode fix',
        'sour1:volt 0.3',
        'sour2:volt:mode fix',
        'sour2:volt 0.0',
        'sour3:volt:mode fix',
        'sour3:volt 0.4',
        # Third modulation
        'sour1:volt:mode fix',
        'sour1:volt 0.3',
        'sour2:volt:mode fix',
        'sour2:volt 0.0',
        'sour3:volt:mode fix',
        'sour3:volt 0.405',
        'sens:rang low,(@1,2,3)',
        '*stb?',
        'sens:nplc 2,(@1,2,3)',
        'read? (@1,2,3)',
        'sour1:volt:mode fix',
        'sour1:volt 0.3',
        'sour2:volt:mode fix',
        'sour2:volt 0.0',
        'sour3:volt:mode fix',
        'sour3:volt 0.4',
    ]
    # The current readings are fixed by the simulation.
    inf = math.inf
    expected = [[inf, inf, inf], [inf, inf, inf], [inf, inf, inf]]
    assert np.allclose(leakage_matrix, np.array(expected))
