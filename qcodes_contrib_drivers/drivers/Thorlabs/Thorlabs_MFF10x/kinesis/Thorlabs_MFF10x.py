from __future__ import annotations

import ctypes
import pathlib
import warnings
from typing import Mapping, Any

from qcodes.validators import validators
from qcodes_contrib_drivers.drivers.Thorlabs._kinesis import enums
from qcodes_contrib_drivers.drivers.Thorlabs._kinesis.core import (
    ThorlabsKinesis,
    KinesisInstrument
)


def _position_get_parser(val) -> str:
    val = int(val)
    if val == 1:
        return 'open'
    elif val == 2:
        return 'close'
    raise ValueError('Invalid return code', val)


def _position_set_parser(val) -> int:
    if val == 'open':
        return 1
    elif val == 'close':
        return 2
    else:
        return int(val)


class ThorlabsMFF10x(KinesisInstrument):
    def __init__(self, name: str, dll_dir: str | pathlib.Path | None = None,
                 metadata: Mapping[Any, Any] | None = None,
                 label: str | None = None):
        self.kinesis = ThorlabsKinesis('FilterFlipper', dll_dir)

        super().__init__(name, dll_dir, metadata, label)

        self.add_parameter('position',
                           get_cmd=self.kinesis.get_position,
                           set_cmd=self.kinesis.set_position,
                           get_parser=_position_get_parser,
                           set_parser=_position_set_parser,
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
        if self.position() == 'open':
            self.position('close')
        else:
            self.position('open')
