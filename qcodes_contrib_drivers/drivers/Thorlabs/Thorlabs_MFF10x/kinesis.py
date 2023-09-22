from __future__ import annotations

import pathlib
from typing import Mapping, Any, Literal

from qcodes_contrib_drivers.drivers.Thorlabs.private.kinesis import (
    KinesisInstrument
)
from qcodes_contrib_drivers.drivers.Thorlabs.private.kinesis import enums


class ThorlabsMFF10x(KinesisInstrument):
    def __init__(self, name: str, dll_dir: str | pathlib.Path | None = None,
                 position_mapping: Mapping[str, Literal[1, 2]] | None = None,
                 metadata: Mapping[Any, Any] | None = None,
                 label: str | None = None):
        super().__init__(name, dll_dir, metadata, label)

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
