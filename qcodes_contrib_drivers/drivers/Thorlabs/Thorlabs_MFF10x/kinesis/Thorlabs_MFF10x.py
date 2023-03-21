from __future__ import annotations

import pathlib
import warnings
from typing import Mapping, Any

from qcodes_contrib_drivers.drivers.Thorlabs._kinesis.core import (
    ThorlabsKinesis,
    KinesisHWType,
    KinesisInstrument
)


class ThorlabsMFF10x(KinesisInstrument):
    def __init__(self, name: str, dll_dir: str | pathlib.Path | None = None,
                 metadata: Mapping[Any, Any] | None = None,
                 label: str | None = None):
        self.kinesis = ThorlabsKinesis('FilterFlipper', dll_dir)

        super().__init__(name, dll_dir, metadata, label)

    @classmethod
    @property
    def hardware_type(cls) -> KinesisHWType:
        return KinesisHWType.FilterFlipper

    def open_device(self, serial: int):
        super().open_device(serial)
        self.kinesis.error_check(self.kinesis.lib.FF_Open(self._c_serial))

    def close_device(self):
        super().close_device()
        self.kinesis.lib.FF_Close(self._c_serial)
