import logging
from typing import Optional, Dict, List, cast

from qcodes import Instrument, InstrumentChannel, ChannelList
from qcodes.utils.validators import Enum

from niswitch import Session, PathCapability

logger = logging.getLogger(__name__)


class NationalInstrumentsSwitch(Instrument):
    r"""
    This is the QCoDeS driver for National Instruments RF switch devices based
    on the NI-SWITCH driver, using the ``niswitch`` module. ``Parameter``s for
    specific instruments should be defined in subclasses.

    This class has functions for connecting two channels, and reading to which
    channel another is connected to. Driver is mainly written for 1-to-many
    port devices (e.g. NI PXI-2597). More complex features supported by the
    ``niswitch`` module are not implemented.

    Tested with

    - NI PXI-2597

    Args:
        name: Qcodes name for this instrument
        resource: Network address or alias for the instrument.
        name_mapping: Optional mapping from custom channel names to default
            names
        reset_device: whether to reset the device on initialization
        niswitch_kw: keyword arguments passed to the ``niswitch.Session``
            constructor
    """

    def __init__(self, name: str, resource: str,
                 name_mapping: Optional[Dict[str, str]] = None,
                 reset_device: bool = False,
                 niswitch_kw: Optional[Dict] = None,
                 **kwargs):

        super().__init__(name=name, **kwargs)
        if name_mapping is None:
            name_mapping = {}
        if niswitch_kw is None:
            niswitch_kw = {}
        self.session = Session(resource, reset_device=reset_device,
                               **niswitch_kw)

        new_channels = ChannelList(self, "all_channels", SwitchChannel)
        self.add_submodule("channels", new_channels)
        for i in range(self.session.channel_count):
            api_name = self.session.get_channel_name(i + 1)
            alias = name_mapping.get(api_name, api_name)
            ch = SwitchChannel(self, alias, api_name)
            new_channels.append(ch)
        self.snapshot(update=True)  # make all channels read their conenctions

        self.connect_message()

    def disconnect_all(self) -> None:
        self.session.disconnect_all()
        self.snapshot(update=True)

    def get_idn(self):
        return {'vendor': self.session.instrument_manufacturer,
                'model': self.session.instrument_model,
                'serial': self.session.serial_number,
                'firmware': self.session.instrument_firmware_revision}


class SwitchChannel(InstrumentChannel):
    """ Represents one output or input terminal of a switch instrument. """
    def __init__(self, instrument: NationalInstrumentsSwitch,
                 name: str, api_name: str):
        super().__init__(instrument, name)

        self._session = self.root_instrument.session
        self.api_name = api_name
        self.connection_list = ChannelList(self.root_instrument, "connections",
                                           type(self), snapshotable=False)

        self.add_parameter("connections",
                           get_cmd=self._read_connections,
                           set_cmd=False,
                           )

    def _update_connection_list(self) -> None:
        self.connection_list.clear()
        for ch in self.root_instrument.channels:
            if ch is self:
                continue
            status = self._session.can_connect(self.api_name, ch.api_name)
            if status == PathCapability.PATH_EXISTS:
                self.connection_list.append(ch)

    def _read_connections(self) -> List[str]:
        r"""
        Returns a list of the channels to which this terminal is connected to.
        """
        self._update_connection_list()
        return [ch.short_name for ch in self.connection_list]

    def connect_to(self, other: "InstrumentChannel") -> None:
        self.root_instrument.channels.get_validator().validate(other)

        status = self._session.can_connect(self.api_name, other.api_name)
        if status == PathCapability.PATH_EXISTS:
            # already connected, do nothing
            return
        elif status == PathCapability.PATH_AVAILABLE:
            # not connected
            pass
        elif status == PathCapability.RESOURCE_IN_USE:
            # connected to something else
            self.disconnect_from_all()
            other.disconnect_from_all()
        self._session.connect(self.api_name, other.api_name)
        self.connection_list.append(other)
        other.connection_list.append(self)

    def disconnect_from(self, other: "InstrumentChannel") -> None:
        self.root_instrument.channels.get_validator().validate(other)
        self._session.disconnect(self.api_name, other.api_name)
        other.connection_list.remove(self)
        self.connection_list.remove(other)

    def disconnect_from_all(self) -> None:
        while len(self.connection_list) > 0:
            ch = cast(InstrumentChannel, self.connection_list[0])
            self.disconnect_from(ch)


class PXIe_2597(NationalInstrumentsSwitch):
    r"""
    QCoDeS driver for National Instruments RF switch PXIe-2597.
    The device connects the common "com" port to any of the 6 other ports,
    labeled "ch1"..."ch6" by default. Use the ``name_mapping `` parameter
    to map additional aliases to the

    Args:
        name: Qcodes name for this instrument
        resource: Network address or alias for the instrument
        name_mapping: Optional dict that maps the default channel names to
            custom aliases
        reset_device: whether to reset the device on initialization
    """
    def __init__(self, name: str, resource: str,
                 name_mapping: Optional[Dict[str, str]] = None,
                 reset_device: bool = False, **kwargs):

        if name_mapping is not None:
            # don't mutate external dict
            name_mapping = name_mapping.copy()
            name_mapping["com"] = "com"

        super().__init__(name, resource, name_mapping, reset_device, **kwargs)

        self.channels.lock()
        valid_choices = [ch.short_name for ch in self.channels]
        valid_choices.remove("com")

        self.add_parameter(name="channel",
                           get_cmd=self._get_channel,
                           set_cmd=self._set_channel,
                           vals=Enum(*tuple(valid_choices + [None])),
                           post_delay=1,
                           docstring='Name of the channel where the common '
                                     '"com" port is connected to',
                           label=f"{self.short_name} active channel")

    def _set_channel(self, name_to_connect: Optional[str]) -> None:
        if name_to_connect is None:
            self.channels.com.disconnect_from_all()
        else:
            ch = getattr(self.channels, name_to_connect)
            self.channels.com.connect_to(ch)

    def _get_channel(self) -> Optional[str]:
        com_list = self.channels.com.connection_list
        if len(com_list) == 0:
            return None
        elif len(com_list) == 1:
            return com_list[0].short_name
        else:
            raise RuntimeError("this shouldn't happen.")
