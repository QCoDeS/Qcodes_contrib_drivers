from __future__ import annotations

import pathlib
from functools import partial
from typing import Mapping, Any

from qcodes import validators as vals
from qcodes_contrib_drivers.drivers.Thorlabs.private.kinesis import enums
from qcodes_contrib_drivers.drivers.Thorlabs.private.kinesis.enums import (
    KinesisHWType
)
from qcodes_contrib_drivers.drivers.Thorlabs.private.kinesis.isc import (
    KinesisISCIntrument
)


class ThorlabsK10CR1(KinesisISCIntrument):
    """Kinesis driver for Thorlabs K10CR1 cage rotator.

    Args:
        name:
            An identifier for this instrument.
        dll_dir (optional):
            The directory where the kinesis dlls reside.
        serial (optional):
            The serial number of the device to connect to. If omitted,
            the first available device found will be used. For a list
            of all available devices, use
            :meth:`list_available_devices` on an existing instance or
            :func:`qcodes_contrib_drivers.drivers.Thorlabs.private.kinesis.core.list_available_devices`.
        metadata (optional):
            Additional static metadata.
        label (optional):
            Nicely formatted name of the instrument.

    """

    def __init__(self, name: str, dll_dir: str | pathlib.Path | None = None,
                 serial: int | None = None,
                 metadata: Mapping[Any, Any] | None = None,
                 label: str | None = None):
        super().__init__(name, dll_dir, serial, metadata, label)

        self.add_parameter(
            "position",
            get_cmd=self.kinesis.get_position,
            set_cmd=self.kinesis.set_position,
            get_parser=partial(self.kinesis.real_value_from_device_unit,
                               unit_type=enums.ISCUnitType.Distance),
            set_parser=partial(self.kinesis.device_unit_from_real_value,
                               unit_type=enums.ISCUnitType.Distance),
            vals=vals.Numbers(0, 360),
            unit=u"\u00b0",
            label="Position"
        )

    @classmethod
    @property
    def hardware_type(cls) -> KinesisHWType:
        return KinesisHWType.CageRotator
