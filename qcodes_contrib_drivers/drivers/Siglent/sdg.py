from collections import ChainMap
from .sdx import SiglentSDx, SiglentChannel, InstrumentBase

from qcodes.parameters import Group, GroupParameter

from qcodes.instrument.channel import ChannelList

from qcodes.validators.validators import MultiTypeOr, Numbers, Enum as EnumVals

from enum import Enum

class SiglentSDGChannel(SiglentChannel):
    def __init__(
        self, parent: InstrumentBase, name: str, channel_number: int, **kwargs
    ):
        super().__init__(parent, name, channel_number)
        self._ch_num_prefix = (
            f"C{channel_number}:" if channel_number is not None else ""
        )

        self._add_outp_parameter_group(
            has_poweron_state=kwargs.pop("has_outp_poweron_state", False)
        )

    def _add_outp_parameter_group(self, *, has_poweron_state: bool):
        ch_num_prefix = self._ch_num_prefix
        ch_num_prefix_len = len(ch_num_prefix)

        outp_set_elements = []
        outp_group_params = []

        self.add_parameter(
            "enabled",
            parameter_class=GroupParameter,
            label="Enabled",
            val_mapping={True: "ON", False: "OFF"},
            # set_cmd=ch_num_prefix + "OUTP {}"
        )

        outp_group_params.append(self.enabled)
        outp_set_elements.append("{enabled}")

        self.add_parameter(
            "load",
            parameter_class=GroupParameter,
            label="Output load",
            unit="Ω",
            vals=MultiTypeOr(Numbers(50, 1e5), EnumVals("HZ")),
            # set_cmd=ch_num_prefix + "OUTP LOAD,{}"
        )

        outp_group_params.append(self.load)
        outp_set_elements.append("LOAD,{load}")

        if has_poweron_state:
            self.add_parameter(
                "poweron_state",
                parameter_class=GroupParameter,
                label="Power-on state",
                val_mapping={
                    False: 0,
                    True: 1,
                },
            )
            outp_group_params.append(self.poweron_state)
            outp_set_elements.append("POWERON_STATE,{poweron_state}")

        self.add_parameter(
            "polarity",
            parameter_class=GroupParameter,
            label="Polarity",
            val_mapping={
                "normal": "NOR",
                "inverted": "INVT",
            },
        )
        outp_group_params.append(self.polarity)
        outp_set_elements.append("PLRT,{polarity}")

        def parse_outp(response: str):
            response = response[ch_num_prefix_len + 5 :]
            values = response.split(",")
            outp_remap = {
                "LOAD": "load",
                "PLRT": "polarity",
                "POWERON_STATE": "poweron_state",
            }
            res = {"enabled": values[0]}
            for k, v in zip(*2 * [iter(values[1:])]):
                res[outp_remap.get(k, k)] = v
            return res

        self.output_group = Group(
            outp_group_params,
            set_cmd=ch_num_prefix + "OUTP " + ",".join(outp_set_elements),
            get_cmd=ch_num_prefix + "OUTP?",
            get_parser=parse_outp,
        )


class SiglentSDGx(SiglentSDx):
    def __init__(self, *args, **kwargs):
        n_channels = kwargs.pop("n_channels", None)
        channel_type = kwargs.pop("channel_type", SiglentSDGChannel)
        channel_kwargs = {}
        if kwargs.pop("has_outp_poweron_state", False):
            channel_kwargs["has_outp_poweron_state"] = True

        super().__init__(*args, **kwargs)

        channels = ChannelList(self, "channel", SiglentSDGChannel, snapshotable=False)

        for channel_number in range(1, n_channels + 1):
            name = f"channel{channel_number}"
            channel = channel_type(self, name, channel_number, **channel_kwargs)
            self.add_submodule(name, channel)
            channels.append(channel)

        self.add_submodule("channel", channels)


class Siglent_SDG_60xx(SiglentSDGx):
    def __init__(self, *args, **kwargs):
        kwargs = ChainMap(kwargs, {"n_channels": 2, "has_outp_poweron_state": True})
        super().__init__(*args, **kwargs)
