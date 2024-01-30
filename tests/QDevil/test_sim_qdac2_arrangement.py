import pytest
from .sim_qdac2_fixtures import qdac  # noqa
from qcodes_contrib_drivers.drivers.QDevil.QDAC2 import forward_and_back
import numpy as np


def test_arrangement_default_correction(qdac):  # noqa
    # -----------------------------------------------------------------------
    arrangement = qdac.arrange(contacts={'plunger1': 1, 'plunger2': 2, 'plunger3': 3})
    # -----------------------------------------------------------------------
    assert np.array_equal(arrangement.correction_matrix,
                          np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]]))


def test_arrangement_contact_names(qdac):  # noqa
    arrangement = qdac.arrange(contacts={'plunger1': 1, 'plunger2': 2, 'plunger3': 3})
    # -----------------------------------------------------------------------
    contacts = arrangement.contact_names
    # -----------------------------------------------------------------------
    assert contacts == ['plunger1', 'plunger2', 'plunger3']


def test_arrangement_set_virtual_voltage_non_exiting_contact(qdac):  # noqa
    arrangement = qdac.arrange(contacts={'plunger': 1})
    # -----------------------------------------------------------------------
    with pytest.raises(ValueError) as error:
        arrangement.set_virtual_voltage('sensor', 1.0)
    # -----------------------------------------------------------------------
    assert 'No contact named "sensor"' in repr(error)


def test_arrangement_set_virtual_voltage_effectuated_immediately(qdac):  # noqa
    arrangement = qdac.arrange(contacts={'plunger1': 1, 'plunger2': 2, 'plunger3': 3})
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    arrangement.set_virtual_voltage('plunger2', 0.5)
    # -----------------------------------------------------------------------
    commands = qdac.get_recorded_scpi_commands()
    assert commands == [
        'sour1:volt:mode fix',
        'sour1:volt 0.0',
        'sour2:volt:mode fix',
        'sour2:volt 0.5',
        'sour3:volt:mode fix',
        'sour3:volt 0.0',
    ]


def test_arrangement_releases_trigger(qdac):  # noqa
    before = len(qdac._internal_triggers)
    # -----------------------------------------------------------------------
    with qdac.arrange(contacts={}, output_triggers={'dmm': 4}):
        pass
    # -----------------------------------------------------------------------
    after = len(qdac._internal_triggers)
    assert before == after


def test_arrangement_cleanup_on_exit(qdac):  # noqa
    qdac._set_up_internal_triggers()
    # -----------------------------------------------------------------------
    with qdac.arrange(contacts={'gate1': 1, 'gate2': 2},
                      output_triggers={'dmm': 4, 'vna': 5},
                      internal_triggers=('wave',), outer_trigger_channel=3
                      ) as arrangement:
        with arrangement.virtual_sweep2d(
            inner_contact='gate1', inner_voltages=np.linspace(-0.2, 0.6, 5),
            outer_contact='gate2', outer_voltages=np.linspace(-0.7, 0.15, 5),
            inner_step_trigger='dmm', outer_step_trigger='vna'
        ):
            qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour1:dc:mark:sst 0',
        'sour1:dc:abor',
        'sour1:dc:trig:sour imm',
        'sour2:dc:abor',
        'sour2:dc:trig:sour imm',
        'outp:trig4:sour hold',
        'outp:trig5:sour hold',
        'sour3:sine:abor',
        'sour3:sine:mark:pstart 0',
        'sour3:sine:trig:sour imm'
    ]


def test_arrangement_cleanup_on_close(qdac):  # noqa
    qdac._set_up_internal_triggers()
    arrangement = qdac.arrange(
        contacts={'gate1': 1, 'gate2': 2},
        output_triggers={'dmm': 4, 'vna': 5},
        internal_triggers=('wave',), outer_trigger_channel=3)
    sweep = arrangement.virtual_sweep2d(
        inner_contact='gate1', inner_voltages=np.linspace(-0.2, 0.6, 5),
        outer_contact='gate2', outer_voltages=np.linspace(-0.7, 0.15, 5),
        inner_step_trigger='dmm', outer_step_trigger='vna')
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    sweep.close()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'sour1:dc:mark:sst 0',
        'sour1:dc:abor',
        'sour1:dc:trig:sour imm',
        'sour2:dc:abor',
        'sour2:dc:trig:sour imm',
        'outp:trig4:sour hold',
        'outp:trig5:sour hold',
        'sour3:sine:abor',
        'sour3:sine:mark:pstart 0',
        'sour3:sine:trig:sour imm'
    ]


def test_arrangement_set_virtual_voltage_affects_whole_arrangement(qdac):  # noqa
    arrangement = qdac.arrange(contacts={'gate1': 1, 'gate2': 2, 'gate3': 3})
    arrangement.initiate_correction('gate1', [1.0, 0.5, -0.5])
    arrangement.initiate_correction('gate2', [-0.5, 1.0, 0.5])
    arrangement.initiate_correction('gate3', [0.0, 0.0, 1.0])
    arrangement.set_virtual_voltage('gate1', 1)
    arrangement.set_virtual_voltage('gate2', 2)
    arrangement.set_virtual_voltage('gate3', 3)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    arrangement.set_virtual_voltage('gate2', 4)
    # -----------------------------------------------------------------------
    commands = qdac.get_recorded_scpi_commands()
    assert commands == [
        'sour1:volt:mode fix',
        'sour1:volt 1.5',
        'sour2:volt:mode fix',
        'sour2:volt 5.0',
        'sour3:volt:mode fix',
        'sour3:volt 3.0'
    ]


def test_arrangement_set_virtual_voltages_affects_at_once(qdac):  # noqa
    arrangement = qdac.arrange(contacts={'gate1': 1, 'gate2': 2})
    arrangement.initiate_correction('gate1', [1.0, 0.12])
    arrangement.initiate_correction('gate2', [-0.12, 0.98])
    # -----------------------------------------------------------------------
    arrangement.set_virtual_voltages({'gate1': 0.1, 'gate2': 0.2})
    # -----------------------------------------------------------------------
    commands = qdac.get_recorded_scpi_commands()
    assert commands == [
        'sour1:volt:mode fix',
        'sour1:volt 0.124',
        'sour2:volt:mode fix',
        'sour2:volt 0.184',
    ]


def test_forward_and_back():
    assert list(forward_and_back(-1, 1, 3)) == [-1, 0, 1, 0]
    assert list(forward_and_back(-2, 2, 5)) == [-2, -1, 0, 1, 2, 1, 0, -1]


def test_arrangement_channel_numbers(qdac):  # noqa
    gates = {'sensor1': 1, 'plunger2': 2, 'plunger3': 3}
    arrangement = qdac.arrange(gates)
    # -----------------------------------------------------------------------
    numbers = arrangement.channel_numbers
    # -----------------------------------------------------------------------
    assert numbers == [1, 2, 3]


def test_channel_by_name(qdac):  # noqa
    contacts = {'sensor1': 1, 'plunger2': 2, 'plunger3': 3}
    arrangement = qdac.arrange(contacts)
    # -----------------------------------------------------------------------
    channel = arrangement.channel('plunger2')
    # -----------------------------------------------------------------------
    assert channel.number == 2
