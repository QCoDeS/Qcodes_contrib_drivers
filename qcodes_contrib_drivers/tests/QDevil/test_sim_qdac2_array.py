import pytest
from unittest.mock import MagicMock
from qcodes_contrib_drivers.drivers.QDevil.QDAC2 import QDac2
from qcodes_contrib_drivers.drivers.QDevil.QDAC2_Array import QDac2_Array
from .sim_qdac2_fixtures import qdac, qdac2  # noqa
from typing import Tuple

# User Story 1
#
# To control 96 lines to my quantum experiment, as a QCoDeS user, I want to
# connect multiple QDAC-IIs together as one big virtual instrument so that their
# combined set of channels are synchronised in time.


# Test helper
def two_qdacs(controller: QDac2, listener: QDac2) -> Tuple[QDac2_Array, str, str]:
    controller.free_all_triggers()
    qdacs = QDac2_Array(controller, [listener])
    return qdacs, controller.full_name, listener.full_name


def test_fails_non_unique_names(qdac):  # noqa
    # -----------------------------------------------------------------------
    with pytest.raises(ValueError) as error:
        QDac2_Array(qdac, [qdac])
    # -----------------------------------------------------------------------
    assert 'Instruments need to have unique names' in repr(error)


def test_has_names_of_instruments(qdac, qdac2, mocker):  # noqa
    qdacs = QDac2_Array(qdac, [qdac2])
    # -----------------------------------------------------------------------
    names = qdacs.names
    # -----------------------------------------------------------------------
    assert names == frozenset([qdac.full_name, qdac2.full_name])


def test_name_of_controller(qdac, qdac2, mocker):  # noqa
    qdacs = QDac2_Array(qdac, [qdac2])
    # -----------------------------------------------------------------------
    name = qdacs.controller
    # -----------------------------------------------------------------------
    assert name == qdac.full_name


def test_fails_to_sync_one_instruments(qdac):
    qdacs = QDac2_Array(qdac, [])
    # -----------------------------------------------------------------------
    with pytest.raises(ValueError) as error:
        qdacs.sync()
    # -----------------------------------------------------------------------
    assert 'Need at least two instruments to sync' in repr(error)


def test_sync_two_instruments(qdac, qdac2, mocker):  # noqa
    qdacs = QDac2_Array(qdac, [qdac2])
    qdac.start_recording_scpi()
    qdac2.start_recording_scpi()
    # -----------------------------------------------------------------------
    qdacs.sync()
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        'syst:cloc:send on',
        'syst:cloc:sync',
        # Pause
        'outp:sync:sign'
    ]
    assert qdac2.get_recorded_scpi_commands() == [
        'syst:cloc:sour ext',
        'syst:cloc:sync',
    ]


@pytest.mark.parametrize('extout', (4, 5))
def test_fails_to_use_reserved_external_triggers(qdac, qdac2, extout):  # noqa
    qdacs = QDac2_Array(qdac, [qdac2])
    controller = qdac.full_name
    listener = qdac2.full_name
    # -----------------------------------------------------------------------
    with pytest.raises(ValueError) as error:
        qdacs.arrange(contacts={}, output_triggers={controller: {'aux': extout}})
    # -----------------------------------------------------------------------
    assert f'External output trigger {extout} is reserved' in repr(error)


def test_fails_on_non_unique_contact_names(qdac, qdac2):  # noqa
    qdacs = QDac2_Array(qdac, [qdac2])
    controller = qdac.full_name
    listener = qdac2.full_name
    # -----------------------------------------------------------------------
    with pytest.raises(ValueError) as error:
        qdacs.arrange(contacts={
            controller: {'sensorA': 1},
            listener: {'sensorA': 2, 'plungerB': 3}
        })
    # -----------------------------------------------------------------------
    assert f'Contact name sensorA used multiple times' in repr(error)


def test_internal_connect_to_trigger_out(qdac, qdac2):  # noqa
    qdacs, controller, listener = two_qdacs(qdac, qdac2)
    qdac.start_recording_scpi()
    # -----------------------------------------------------------------------
    external_in = qdacs.common_trigger_in
    internal_trigger = qdacs.allocate_trigger()
    qdacs.connect_external_trigger(qdacs.trigger_out, internal_trigger)
    qdacs.trigger(internal_trigger)
    # -----------------------------------------------------------------------
    commands = qdac.get_recorded_scpi_commands()
    assert 'outp:trig4:sour int1' in commands
    assert 'tint 1' in commands


def test_sync_square_waves(qdac, qdac2):  # noqa
    qdacs, controller, listener = two_qdacs(qdac, qdac2)
    qdacs.sync()  # Not needed for this test, but would be needed IRL
    contacts = {controller: {'contactA': 1}, listener: {'contactB': 1}}
    arrangement = qdacs.arrange(contacts)
    start_trigger = qdacs.allocate_trigger()
    qdac.start_recording_scpi()
    qdac2.start_recording_scpi()
    # -----------------------------------------------------------------------
    for contact in ('contactA', 'contactB'):
        square = arrangement.channel(contact).square_wave(period_s=10e-6, span_V=1)
        square.start_on_external(qdacs.common_trigger_in)
    qdacs.connect_external_trigger(qdacs.trigger_out, start_trigger)
    # -----------------------------------------------------------------------
    controller_commands = qdac.get_recorded_scpi_commands()
    assert 'sour1:squ:per 1e-05' in controller_commands
    assert 'sour1:squ:span 1' in controller_commands
    assert 'sour1:squ:trig:sour ext3' in controller_commands
    assert 'sour1:squ:init' in controller_commands
    assert 'outp:trig4:sour int1' in controller_commands
    listener_commands = qdac2.get_recorded_scpi_commands()
    assert 'sour1:squ:per 1e-05' in listener_commands
    assert 'sour1:squ:span 1' in listener_commands
    assert 'sour1:squ:trig:sour ext3' in listener_commands
    assert 'sour1:squ:init' in listener_commands
    # -----------------------------------------------------------------------
    qdacs.trigger(start_trigger)
    # -----------------------------------------------------------------------
    controller_commands = qdac.get_recorded_scpi_commands()
    assert 'tint 1' in controller_commands
