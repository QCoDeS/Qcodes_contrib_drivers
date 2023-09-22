from __future__ import annotations

import ctypes
import pathlib

from . import enums
from .core import KinesisInstrument, ThorlabsKinesis, KinesisError


class KinesisIntegratedStepperMotor(KinesisInstrument):
    """Devices which are controlled from the IntegratedStepperMotor dll.
    """

    def _init_kinesis(self, dll_dir: str | pathlib.Path | None) -> ThorlabsKinesis:
        return ThorlabsKinesis('Thorlabs.MotionControl.IntegratedStepperMotors.dll', self._prefix,
                               dll_dir)

    @classmethod
    @property
    def _prefix(cls) -> str:
        return 'ISC'
