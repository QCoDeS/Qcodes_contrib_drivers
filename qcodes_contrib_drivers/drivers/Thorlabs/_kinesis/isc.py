from __future__ import annotations

import ctypes
import pathlib
from typing import Mapping, Any

from . import enums
from .core import KinesisInstrument, ThorlabsKinesis, KinesisError


class KinesisIntegratedStepperMotor(KinesisInstrument):
    """Devices which are controlled from the IntegratedStepperMotor dll.
    """

    def __init__(self, name: str, dll_dir: str | pathlib.Path | None = None,
                 metadata: Mapping[Any, Any] | None = None,
                 label: str | None = None):

        self.kinesis = ThorlabsKinesis(
            'Thorlabs.MotionControl.IntegratedStepperMotors.dll',
            self._prefix,
            dll_dir
        )
        super().__init__(name, dll_dir, metadata, label)

    @classmethod
    @property
    def _prefix(cls) -> str:
        return 'ISC'
