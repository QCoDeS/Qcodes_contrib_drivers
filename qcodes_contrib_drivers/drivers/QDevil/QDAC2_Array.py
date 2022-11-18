from .QDAC2 import QDac2, QDac2Channel, QDac2ExternalTrigger, \
    QDac2Trigger_Context, ExternalInput
from typing import Dict, Sequence, List, FrozenSet, Optional

# Version 0.1.0
#
# Guiding principles for this driver for multiple QDevil QDAC-IIs
# ---------------------------------------------------------------
#
# TODO:


def check_for_reserved_outputs(triggers: Dict[str, int]) -> None:
    for trigger in triggers.values():
        if trigger in (4,5):
            raise ValueError(f'External output trigger {trigger} is reserved')


class Array_Arrangement_Context:

    def __init__(self, qdacs: 'QDAC2_Array',
                 contacts: Dict[str,Dict[str, int]],
                 output_triggers: Optional[Dict[str,Dict[str, int]]] = None,
                 internal_triggers: Optional[Sequence[str]] = None):
        self._qdacs = qdacs
        self._arrangements = {}
        self._contacts = {}
        for qdac in qdacs._qdacs:
            name = qdac.full_name
            qdac_contacts = contacts.get(name, {})
            qdac_outputs = output_triggers.get(name, {}) if output_triggers else {}
            is_contoller = (name == qdacs._controller_name)
            arrangement = None
            if is_contoller:
                check_for_reserved_outputs(qdac_outputs)
                arrangement = \
                    qdac.arrange(qdac_contacts, qdac_outputs, internal_triggers)
            else:
                arrangement = qdac.arrange(qdac_contacts, qdac_outputs)
            self._arrangements[name] = arrangement
            for c_name in qdac_contacts.keys():
                if c_name in self._contacts:
                    raise ValueError(f'Contact name {c_name} used multiple times')
                self._contacts[c_name] = name

    def channel(self, contact: str) -> QDac2Channel:
        qdac = self._contacts[contact]
        arrangement = self._arrangements[qdac]
        return arrangement.channel(contact)


class QDac2_Array:
    """[summary]

    The sync cables must be left in place after sync, so that the clock is
    continuously distributed, and the Controller can trigger all Listerners
    by sending pulses from Ext Out 4 to all Ext In 3 simultaneously.
    """
    def __init__(self, controller: QDac2, listeners: Sequence[QDac2]):
        self._controller = controller
        self._qdacs = [controller, *listeners]
        self._check_unique_names()

    @property
    def trigger_out(self) -> int:
        return 4

    @property
    def common_trigger_in(self) -> ExternalInput:
        return ExternalInput(3)

    @property
    def controller(self) -> str:
        return self._controller_name

    @property
    def names(self) -> FrozenSet[str]:
        return self._qdac_names

    def allocate_trigger(self) -> QDac2Trigger_Context:
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
        self._controller.trigger(internal_trigger)

    def sync(self) -> None:
        if len(self._qdacs) < 2:
            raise ValueError('Need at least two instruments to sync')
        self._controller_write(['syst:cloc:send on'])
        self._listeners_write(['syst:cloc:sour ext', 'syst:cloc:sync'])
        self._controller_write(['syst:cloc:sync', 'outp:sync:sign'])

    def arrange(self, contacts: Dict[str,Dict[str, int]],
                output_triggers: Optional[Dict[str,Dict[str, int]]] = None,
                internal_triggers: Optional[Sequence[str]] = None
                ) -> Array_Arrangement_Context:
        """[summary]

        [description]

        Args:
            contacts (Dict[str,Dict[str, int]]): [description]
            output_triggers (Dict[str,Dict[str, int]]): [description] (default: `None`)
            internal_triggers (Sequence[str]): [description] (default: `None`)

        Returns:
            Array_Arrangement_Context: [description]
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
