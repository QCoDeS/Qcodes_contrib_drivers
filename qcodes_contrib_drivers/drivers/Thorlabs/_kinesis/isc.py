from __future__ import annotations

import pathlib
from typing import Mapping, Any

from .core import KinesisInstrument, ThorlabsKinesis


class KinesisIntegratedStepperMotor(KinesisInstrument):
    """Devices which are controlled from the IntegratedStepperMotor dll.
    """

    def __init__(self, name: str, dll_dir: str | pathlib.Path | None = None,
                 metadata: Mapping[Any, Any] | None = None,
                 label: str | None = None):
        super().__init__(name, dll_dir, metadata, label)
        self.kinesis = ThorlabsKinesis(
            'Thorlabs.MotionControl.IntegratedStepperMotors.dll',
            dll_dir
        )

    def open_device(self, serial: int):
        super().open_device(serial)
        self.kinesis.error_check(self.kinesis.lib.ISC_Open(self._c_serial))

    def close_device(self):
        super().close_device()
        self.kinesis.lib.ISC_Open(self._c_serial)
