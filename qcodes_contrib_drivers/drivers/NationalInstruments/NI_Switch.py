import logging
from typing import Optional, Dict, Union
from functools import partial

from qcodes import Instrument
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
                 #name_mapping: Optional[Dict[str, str]] = None,
                 reset_device: bool = False,
                 niswitch_kw: Optional[Dict] = None,
                 **kwargs):

        super().__init__(name=name, **kwargs)
        if niswitch_kw is None:
            niswitch_kw = {}
        self._session = Session(resource, reset_device=reset_device, **niswitch_kw)
        self.channelNames = [self._session.get_channel_name(i + 1)
                             for i in range(self._session.channel_count)]
        #self._name_map = name_mapping
        self.connect_message()
        # define parameter(s) in device-specific subclass

    def connect(self,
                channel1: Union[str, None],
                channel2: Union[str, None]) -> None:
        r"""
        Force connection between ``channel1`` and ``channel2``, disconnect ALL
        other connections. If either one is None, disconnect the other.
        """
        if channel1 is None and channel2 is not None:
            self._session.disconnect(channel2, self.read_connection(channel2))
            return
        if channel2 is None and channel1 is not None:
            self._session.disconnect(channel1, self.read_connection(channel1))
            return

        if channel1 in self.channelNames and channel2 in self.channelNames:
            status = self._session.can_connect(channel1, channel2)
            if status == PathCapability.PATH_EXISTS:
                # already connected, do nothing
                pass
            elif status == PathCapability.PATH_AVAILABLE:
                # not connected
                self._session.connect(channel1, channel2)
            elif status == PathCapability.RESOURCE_IN_USE:
                # connected to something else
                self._session.disconnect_all()
                self._session.connect(channel1, channel2)
            else:
                raise RuntimeError(f"Could not connect channels {channel1} "
                                   f"and {channel2}: {status.name}")
        else:
            #available = self._name_map.keys() if self._name_map else self.channelNames
            available = self.channelNames
            raise ValueError(f"Unrecognized channel name. Available: "
                             f"{available}, got '{channel1}', '{channel2}'")

    def disconnect_all(self) -> None:
        self._session.disconnect_all()

    def read_connection(self, channel) -> Union[str, None]:
        r"""
        Returns the name of the channel to which `channel` is connected to. If
        not connected, return None.
        """
        #if self._name_map:
        #    channel = self._name_map[channel]

        for ch in self.channelNames:
            res = self._session.can_connect(channel, ch)
            if res == PathCapability.PATH_EXISTS:
                return ch
        return None

    def get_idn(self):
        return {'vendor': self._session.instrument_manufacturer,
                'model': self._session.instrument_model,
                'serial': self._session.serial_number,
                'firmware': self._session.instrument_firmware_revision}


class PXIe_2597(NationalInstrumentsSwitch):
    r"""
    QCoDeS driver for National Instruments RF switch PXIe-2597.
    The device connects the common "com" port to any of the 6 other ports,
    labeled "ch1"..."ch6" by default. Use the ``name_mapping `` parameter
    to map additional aliases to the 

    Args:
        name: Qcodes name for this instrument
        resource: Network address or alias for the instrument.
        name_mapping: Optional dict that maps custom channel names to the default
            names ("ch1", "ch2" etc.).
        reset_device: whether to reset the device on initialization
    """
    def __init__(self, name: str, resource: str,
                 name_mapping: Optional[Dict[str, str]] = None,
                 reset_device: bool = False, **kwargs):
        super().__init__(name, resource, reset_device, **kwargs)

        val_mapping = {name: name for name in self.channelNames}
        if name_mapping is not None:
            val_mapping = dict(val_mapping, **name_mapping)
        val_mapping[None] = None

        self.add_parameter(name="channel",
                           get_cmd=self._get_channel,
                           set_cmd=partial(self.connect, 'com'),
                           val_mapping=val_mapping,
                           post_delay=1,
                           docstring='Name of the channel where the common '
                                     '"com" port is connected to',
                           label=f"{self.short_name} active channel")
                        
    def connect(self, channel1, channel2):
        self.channel.validate(channel1)
        self.channel.validate(channel2)
        mapping = self.channel.val_mapping
        # for some reason, super() doesn't work when setting the parameter
        # but using this _connect hack works...
        super().connect(mapping[channel1], mapping[channel2])

    def _get_channel(self):
        end_point = self.read_connection('com')
        return end_point if end_point is not None else 'com'
