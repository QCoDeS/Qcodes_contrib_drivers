from __future__ import annotations

import pathlib
from typing import Mapping, Any, Literal

from qcodes_contrib_drivers.drivers.Thorlabs.private.kinesis import (
    KinesisInstrument
)
from qcodes_contrib_drivers.drivers.Thorlabs.private.kinesis import enums


class ThorlabsMFF10x(KinesisInstrument):
    """Kinesis driver for Thorlabs MFF10x filter flipper.

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
        simulation (optional):
            Enable the Kinesis simulator mode. Note that the serial
            number assigned to the simulated device should be given
            since otherwise the first available device will be
            connected (which might not be a simulated but a real one).
        position_mapping (optional):
            A val mapping for a more human-readable position mapping
            than the internally used 1 and 2. Defaults to
            ``{'open': 1, 'close': 2}``.
        metadata (optional):
            Additional static metadata.
        label (optional):
            Nicely formatted name of the instrument.

    """

    def __init__(self, name: str, dll_dir: str | pathlib.Path | None = None,
                 serial: int | None = None, simulation: bool = False,
                 position_mapping: Mapping[str, Literal[1, 2]] | None = None,
                 metadata: Mapping[Any, Any] | None = None,
                 label: str | None = None):
        super().__init__(name, dll_dir, serial, simulation, metadata, label)

        position_mapping = position_mapping or {'open': 1, 'close': 2}
        self.add_parameter('position',
                           get_cmd=self.kinesis.get_position,
                           set_cmd=self.kinesis.set_position,
                           val_mapping=position_mapping,
                           label='Position')

    @classmethod
    @property
    def _prefix(cls):
        return 'FF'

    @classmethod
    @property
    def hardware_type(cls) -> enums.KinesisHWType:
        return enums.KinesisHWType.FilterFlipper

    def toggle_position(self):
        """Toggle the position of the flipper."""
        # val_mapping is dynamic, so use inverse_val_mapping together
        # with the hardware values
        if self.position() == self.position.inverse_val_mapping[1]:
            self.position(self.position.inverse_val_mapping[2])
        else:
            self.position(self.position.inverse_val_mapping[1])
