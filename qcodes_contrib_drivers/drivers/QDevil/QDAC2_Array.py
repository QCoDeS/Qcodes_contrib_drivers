from .QDAC2 import QDac2, QDac2Channel, QDac2ExternalTrigger, \
    QDac2Trigger_Context, Arrangement_Context, ExternalInput, \
    comma_sequence_to_list_of_floats, diff_matrix
from typing import Tuple, Dict, Sequence, List, FrozenSet, Optional
import numpy as np
from time import sleep as sleep_s

# Version 0.1.1
#
# Guiding principles for this driver for multiple QDevil QDAC-IIs
# ---------------------------------------------------------------
#
# 1. Use the underlying QDAC2.py driver as much as possible.
#


#
# Future improvements
# -------------------
#
# - An array arrangement should support corrections between contacts
#   (which the indiviual arrangements on each instrument does).


def _check_for_reserved_outputs(triggers: Dict[str, int]) -> None:
    for trigger in triggers.values():
        if trigger in (4, 5):
            raise ValueError(f'External output trigger {trigger} is reserved')


class Array_Arrangement_Context:

    def __init__(self, qdacs: 'QDac2_Array',
                 contacts: Dict[str, Dict[str, int]],
                 output_triggers: Optional[Dict[str, Dict[str, int]]] = None,
                 internal_triggers: Optional[Sequence[str]] = None):
        self._qdacs = qdacs
        self._arrangements: Dict[str, Arrangement_Context] = dict()
        self._contacts: Dict[str, str] = dict()
        for qdac in qdacs._qdacs:
            qdac_name = qdac.full_name
            qdac_contacts = contacts.get(qdac_name, dict())
            qdac_outputs = output_triggers.get(qdac_name, dict()) if output_triggers else dict()
            is_contoller = (qdac_name == qdacs._controller_name)
            arrangement = None
            if is_contoller:
                _check_for_reserved_outputs(qdac_outputs)
                arrangement = \
                    qdac.arrange(qdac_contacts, qdac_outputs, internal_triggers)
            else:
                arrangement = qdac.arrange(qdac_contacts, qdac_outputs)
            self._arrangements[qdac_name] = arrangement
            for c_name in qdac_contacts.keys():
                if c_name in self._contacts:
                    raise ValueError(f'Contact name {c_name} used multiple times')
                self._contacts[c_name] = qdac_name

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for arrangement in self._arrangements.values():
            arrangement.__exit__(exc_type, exc_val, exc_tb)
        return False

    @property
    def contact_names(self) -> Sequence[str]:
        """
        Returns:
           Sequence[str]: Channel names
        """
        return [name for name in self._contacts.keys()]

    def channel(self, contact: str) -> QDac2Channel:
        """
        Args:
            contact (str): Name

        Returns:
           QDac2Channel: Instrument channel
        """
        qdac = self._get_qdac_for(contact)
        arrangement = self._arrangements[qdac]
        return arrangement.channel(contact)

    def qdac_names(self) -> Sequence[str]:
        return [qdac.full_name for qdac in self._qdacs._qdacs]

    def virtual_voltage(self, contact: str) -> float:
        """
        Args:
            contact (str): Name of contact

        Returns:
            float: Voltage before correction
        """
        qdac = self._get_qdac_for(contact)
        arrangement = self._arrangements[qdac]
        return arrangement.virtual_voltage(contact)

    def set_virtual_voltages(self, contacts_to_voltages: Dict[str, float]) -> None:
        for qdac in self.qdac_names():
            qdac_voltages: Dict[str, float] = dict()
            for contact, voltage in contacts_to_voltages.items():
                if self._get_qdac_for(contact) == qdac:
                    qdac_voltages[contact] = voltage
            arrangement = self._arrangements[qdac]
            arrangement.set_virtual_voltages(qdac_voltages)

    def currents_A(self, nplc: int = 1, current_range: str = "low") -> Sequence[float]:
        """Measure currents on all contacts

        The order is that of contacts()

        Args:
            nplc (int, optional): Number of powerline cycles to average over
            current_range (str, optional): Current range (default low)
        """
        # Setup current measurement on all instruments
        for qdac in self.qdac_names():
            arrangement = self._arrangements[qdac]
            channels_suffix = arrangement._all_channels_as_suffix()
            arrangement._qdac.write(f'sens:rang {current_range},{channels_suffix}')
        for qdac in self.qdac_names():
            arrangement = self._arrangements[qdac]
            channels_suffix = arrangement._all_channels_as_suffix()
            # Wait for relays to finish switching by doing a query
            arrangement._qdac.ask(f'*stb?')
            arrangement._qdac.write(f'sens:nplc {nplc},{channels_suffix}')
        # Wait for the current sensors to stabilize and then read
        slowest_line_freq_Hz = 50
        sleep_s((nplc + 1) / slowest_line_freq_Hz)
        values: List[float] = list()
        for qdac in self.qdac_names():
            arrangement = self._arrangements[qdac]
            channels_suffix = arrangement._all_channels_as_suffix()
            currents = arrangement._qdac.ask(f'read? {channels_suffix}')
            values += comma_sequence_to_list_of_floats(currents)
        return values

    def leakage(self, modulation_V: float, nplc: int = 2) -> np.ndarray:
        """Run a simple leakage test between the contacts

        Each contact is changed in turn and the resulting change in current from
        steady-state is recorded.  The resulting resistance matrix is calculated
        as modulation_voltage divided by current_change.

        Args:
            modulation_V (float): Virtual voltage added to each contact
            nplc (int, Optional): Powerline cycles to wait for each measurement

        Returns:
            ndarray: contact-to-contact resistance in Ohms
        """
        steady_state_A, currents_matrix = self._leakage_currents(modulation_V, nplc, 'low')
        with np.errstate(divide='ignore'):
            return np.abs(modulation_V / diff_matrix(steady_state_A, currents_matrix))

    def _leakage_currents(self, modulation_V: float, nplc: int,
                          current_range: str
                          ) -> Tuple[Sequence[float], Sequence[Sequence[float]]]:
        steady_state_A = self.currents_A(nplc, 'low')
        currents_matrix = list()
        for qdac in self.qdac_names():
            arrangement = self._arrangements[qdac]
            for index, channel_nr in enumerate(arrangement.channel_numbers):
                original_V = arrangement._virtual_voltages[index]
                arrangement._effectuate_virtual_voltage(index, original_V + modulation_V)
                currents = self.currents_A(nplc, current_range)
                arrangement._effectuate_virtual_voltage(index, original_V)
                currents_matrix.append(currents)
        return steady_state_A, currents_matrix

    def _get_qdac_for(self, contact: str) -> str:
        try:
            return self._contacts[contact]
        except KeyError:
            raise ValueError(f'No contact named "{contact}"')



class QDac2_Array:
    """A collection of interconnected QDAC-IIs

    The instruments are required to be connected as described in section 5.5
    'Synchronization of multiple QDAC-II units' in the manual.  The sync
    cables must be left in place after sync, so that the clock is
    continuously distributed, and the Controller can trigger all Listerners
    by sending pulses from Ext Out 4 to all Ext In 3 simultaneously.
    """

    def __init__(self, controller: QDac2, listeners: Sequence[QDac2]):
        self._controller = controller
        self._qdacs = [controller, *listeners]  # Order is important
        self._check_unique_names()

    @property
    def trigger_out(self) -> int:
        return 4

    @property
    def common_trigger_in(self) -> ExternalInput:
        return ExternalInput(3)

    @property
    def controller(self) -> str:
        """
            Returns:
               str: Name of Controller
        """
        return self._controller_name

    @property
    def names(self) -> FrozenSet[str]:
        """
            Returns:
               FrozenSet[str]: Names of all QDAC-IIs in the array
        """
        return self._qdac_names

    def allocate_trigger(self) -> QDac2Trigger_Context:
        """Allocate internal trigger on the Controller

        Returns:
            QDac2Trigger_Context: context manager
        """
        return self._controller.allocate_trigger()

    def connect_external_trigger(self, port: int, trigger: QDac2Trigger_Context,
                                 width_s: float = 1e-6
                                 ) -> None:
        """Route internal trigger to external trigger

        Args:
            port (int): External output trigger number
            trigger (QDac2Trigger_Context): Internal trigger
            width_s (float, optional): Output trigger width in seconds (default 1ms)
        """
        self._controller.connect_external_trigger(port, trigger, width_s)

    def trigger(self, internal_trigger: QDac2Trigger_Context):
        """Fire an internal trigger on the Controller

        Args:
            QDac2Trigger_Context: internal trigger
        """
        self._controller.trigger(internal_trigger)

    def sync(self) -> None:
        """Synchronizes the array of QDAC-IIs

        The Listeners will stop using their own clock and start using the
        Controller's clock.
        """
        if len(self._qdacs) < 2:
            raise ValueError('Need at least two instruments to sync')
        self._controller_write(['syst:cloc:send on'])
        self._listeners_write(['syst:cloc:sour ext', 'syst:cloc:sync'])
        self._controller_write(['syst:cloc:sync', 'outp:sync:sign'])

    def arrange(self, contacts: Dict[str, Dict[str, int]],
                output_triggers: Optional[Dict[str, Dict[str, int]]] = None,
                internal_triggers: Optional[Sequence[str]] = None
                ) -> Array_Arrangement_Context:
        """An arrangement of contacts across several QDAC-II instruments

        The arrangement is a collection of QDac2.arrangement, one for each
        instrument but with a dedicated controller.

        See QDac2.arrangement() for further documentation.  Note that an
        array arrangement does not (yet) support corrections between contacts
        (which the indiviual arrangements on each instrument does).

        Args:
            contacts (Dict[str,Dict[str, int]]): Instrument name to contact-name/channel pairs
            output_triggers (Dict[str,Dict[str, int]], optional): Instrument name to name/output-trigger pairs
            internal_triggers (Sequence[str], optional): List of names of internal triggers to allocate on the controller

        Returns:
            Array_Arrangement_Context: context manager
        """
        return Array_Arrangement_Context(self, contacts, output_triggers,
                                         internal_triggers)

    def _controller_write(self, commands: List[str]) -> None:
        for command in commands:
            self._controller.write(command)

    def _listeners_write(self, commands: List[str]) -> None:
        listeners = self._qdacs[1:]
        for listener in listeners:
            for command in commands:
                listener.write(command)

    def _check_unique_names(self) -> None:
        self._controller_name = self._controller.full_name
        self._qdac_names = frozenset([qdac.full_name for qdac in self._qdacs])
        if len(self._qdac_names) != len(self._qdacs):
            raise ValueError(f'Instruments need to have unique names: {self._qdac_names}')
