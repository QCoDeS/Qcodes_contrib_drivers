import logging
from typing import Optional, Dict, List, cast

from qcodes import Instrument, InstrumentChannel, ChannelList

from niswitch import Session, PathCapability

logger = logging.getLogger(__name__)


class NI_Switch(Instrument):
    r"""
    This is the QCoDeS driver for National Instruments RF switch devices based
    on the NI-SWITCH driver, using the ``niswitch`` module. ``Parameter`` s for
    specific instruments should be defined in subclasses.

    This main class mostly just maintains a reference to a
    ``niswitch.Session``, and  holds ``ChannelList`` of channels, or ports.
    Actually making connections between the channels is implemented by the
    ``SwitchChannel`` class.

    Tested with

    - NI PXI-2597

    Args:
        name: Qcodes name for this instrument
        resource: Network address or VISA alias for the instrument.
        name_mapping: Optional mapping from default ("raw") channel names to
            custom aliases
        reset_device: whether to reset the device on initialization
        niswitch_kw: other keyword arguments passed to the ``niswitch.Session``
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
        for i in range(self.session.channel_count):
            raw_name = self.session.get_channel_name(i + 1)
            alias = name_mapping.get(raw_name, raw_name)
            ch = SwitchChannel(self, alias, raw_name)
            new_channels.append(ch)
        new_channels.lock()
        self.add_submodule("channels", new_channels)
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

    def close(self):
        if hasattr(self, "session"):
            self.session.close()
        super().close()


class SwitchChannel(InstrumentChannel):
    """
    This class represents one input or output port of a switch instrument.

    Args:
        instrument: the instrument to which this port belongs to
        name: name or alias of this port in the parent instrument's
            ChannelList
        raw_name: name of this port in the driver's channel table, as given by
            ``self._session.get_channel_name``
    """
    def __init__(self, instrument: NI_Switch,
                 name: str, raw_name: str):
        super().__init__(instrument, name)

        self._session = self.root_instrument.session
        self.raw_name = raw_name
        self.connection_list = ChannelList(self.root_instrument, "connections",
                                           type(self), snapshotable=False)

        self.add_parameter("connections",
                           docstring="The value of this read-only parameter "
                                     "is a list of the names of the channels "
                                     "to which this channel is connected to.",
                           get_cmd=self._read_connections,
                           set_cmd=False,
                           )

    def _update_connection_list(self) -> None:
        self.connection_list.clear()
        for ch in self.root_instrument.channels:
            if ch is self:
                continue
            status = self._session.can_connect(self.raw_name, ch.raw_name)
            if status == PathCapability.PATH_EXISTS:
                self.connection_list.append(ch)

    def _read_connections(self) -> List[str]:
        r"""
        Returns a list of the channels to which this channel is connected to.
        """
        self._update_connection_list()
        return [ch.short_name for ch in self.connection_list]

    def connect_to(self, other: "InstrumentChannel") -> None:
        """
        Connect this channel to another channel. If either of the channels is
        already connected to something else, disconnect both channels first. If
        the channels are already connected to each other, do nothing. If the
        two channels cannot be connected, raises a ``DriverError``, see
        the ``niswitch.Session.connect`` documentation for further details.
        """
        self.root_instrument.channels.get_validator().validate(other)

        status = self._session.can_connect(self.raw_name, other.raw_name)
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
        self._session.connect(self.raw_name, other.raw_name)
        self.connection_list.append(other)
        other.connection_list.append(self)

    def disconnect_from(self, other: "InstrumentChannel") -> None:
        """
        Disconnect this channel from another chanel. If the channels are not
        connected, raises a ``DriverError``.
        """
        self.root_instrument.channels.get_validator().validate(other)
        self._session.disconnect(self.raw_name, other.raw_name)
        other.connection_list.remove(self)
        self.connection_list.remove(other)

    def disconnect_from_all(self) -> None:
        """
        Disconnect this channel from all channels it is connected to.
        """
        while len(self.connection_list) > 0:
            ch = cast(InstrumentChannel, self.connection_list[0])
            self.disconnect_from(ch)
