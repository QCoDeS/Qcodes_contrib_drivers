from typing import Optional, Dict
from qcodes.utils.validators import Enum
from .Switch import NI_Switch


class NI_PXIe_2597(NI_Switch):
    r"""
    QCoDeS driver for National Instruments RF switch PXIe-2597. The device
    connects the common "com" port to any of the 6 other ports, labeled
    "ch1"..."ch6" by default. Use the ``name_mapping`` argument to alias the
    channel names.

    Args:
        name: Qcodes name for this instrument
        resource: Network address or VISA alias for the instrument.
        name_mapping: Optional mapping from default channel names to custom
            aliases
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
