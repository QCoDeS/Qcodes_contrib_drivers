from collections import ChainMap
from typing import Any, Dict

# import qcodes.validators as vals
from qcodes.instrument.channel import ChannelList

from .sdg_channel import SiglentSDGChannel
from .sdx import SiglentSDx


class SiglentSDGx(SiglentSDx):
    def __init__(self, *args, **kwargs):
        n_channels = kwargs.pop("n_channels", 0)
        channel_type = kwargs.pop("channel_type", SiglentSDGChannel)
        channel_kwargs = {"n_channels": n_channels}
        for ch_param in (
            "extra_outp_params",
            "extra_bswv_params",
            "extra_mdwv_params",
            "extra_swwv_params",
            "extra_btwv_params",
        ):
            if ch_param in kwargs:
                channel_kwargs[ch_param] = kwargs.pop(ch_param)

        self._ranges = kwargs.pop("ranges", {})

        super().__init__(*args, **kwargs)

        channels = ChannelList(self, "channels", SiglentSDGChannel, snapshotable=False)

        for channel_number in range(1, n_channels + 1):
            name = f"channel{channel_number}"
            channel = channel_type(self, name, channel_number, **channel_kwargs)
            self.add_submodule(name, channel)
            channels.append(channel)

        self.add_submodule("channels", channels)


class Siglent_SDG_60xx(SiglentSDGx):
    def __init__(self, *args, **kwargs):
        default_params = {
            "n_channels": 2,
            "extra_outp_params": {"POWERON_STATE"},
            "extra_bswv_params": {"MAX_OUTPUT_AMP"},
            "extra_mdwv_params": {"CARR,DLY", "CARR,RISE", "CARR,FALL"},
            "extra_swwv_params": {"TRMD", "EDGE"},
            "extra_btwv_params": {
                "TRMD",
                "EDGE",
                "COUNTER",
                "CARR,DLY",
                "CARR,RISE",
                "CARR,FALL",
            },
        }

        default_ranges = {
            "vpp": (2e-3, 20.0),
            "vrms": (2e-3, 10.0),
            "offset": (-10, 10),
            "burst_period": (1.0e-6, 1000.0),
            "burst_phase": (-360.0, 360.0),
            "burst_ncycles": (1, 1000000),
            "burst_trigger_delay": (0, 100),
            "arwv_index": (2, 198),
        }

        ranges_kwargs = _provide_defaults_to_dict_kwarg(
            kwargs, "ranges", default_ranges
        )
        kwargs = ChainMap(ranges_kwargs, kwargs, default_params)
        super().__init__(*args, **kwargs)


class Siglent_SDG_20xx(SiglentSDGx):
    def __init__(self, *args, **kwargs):
        default_params = {
            "n_channels": 2,
            "extra_bswv_params": {"MAX_OUTPUT_AMP"},
            "extra_mdwv_params": {"CARR,DLY", "CARR,RISE", "CARR,FALL"},
            "extra_swwv_params": {"TRMD", "EDGE"},
            "extra_btwv_params": {"TRMD", "EDGE", "CARR,DLY", "CARR,RISE", "CARR,FALL"},
        }

        default_ranges = {
            "vpp": (2e-3, 20.0),
            "vrms": (2e-3, 10.0),
            "offset": (-10, 10),
            "burst_period": (1.0e-6, 1000.0),
            "burst_phase": (-360.0, 360.0),
            "burst_ncycles": (1, 1000000),
            "burst_trigger_delay": (0, 100),
            "arwv_index": (2, 198),
        }

        ranges_kwargs = _provide_defaults_to_dict_kwarg(
            kwargs, "ranges", default_ranges
        )
        kwargs = ChainMap(ranges_kwargs, kwargs, default_params)
        super().__init__(*args, **kwargs)


class Siglent_SDG_6022X(Siglent_SDG_60xx):
    def __init__(self, *args, **kwargs):
        default_ranges = {
            "frequency": (1e-3, 200e6),
        }
        ranges_kwargs = _provide_defaults_to_dict_kwarg(
            kwargs, "ranges", default_ranges
        )

        kwargs = ChainMap(ranges_kwargs, kwargs)
        super().__init__(*args, **kwargs)


class Siglent_SDG_2042X(Siglent_SDG_20xx):
    def __init__(self, *args, **kwargs):
        default_ranges = {
            "frequency": (1e-3, 40e6),
        }

        ranges_kwargs = _provide_defaults_to_dict_kwarg(
            kwargs, "ranges", default_ranges
        )
        kwargs = ChainMap(ranges_kwargs, kwargs)

        super().__init__(*args, **kwargs)


# tricky
# generate a dictionary which can be chained with the kwargs
# to provide default values to items of the dictionary-type kwarg
# with the given key
def _provide_defaults_to_dict_kwarg(
    kwargs: Dict[str, Any], kwarg_name: str, default_values: dict
) -> Dict[str, Any]:
    if kwarg_name in kwargs:
        dict_item = kwargs[kwarg_name]
        default_values = ChainMap(dict_item, default_values)  # type: ignore

    return {kwarg_name: default_values}
