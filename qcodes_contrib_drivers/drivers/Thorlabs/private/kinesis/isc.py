from __future__ import annotations

import pathlib
from typing import Any, Mapping

from .core import KinesisInstrument, ThorlabsKinesis


class KinesisISCInstrument(KinesisInstrument):
    """Devices which are controlled from the IntegratedStepperMotor dll.
    """

    def __init__(self, name: str, dll_dir: str | pathlib.Path | None = '',
                 serial: int | None = None, simulation: bool = False,
                 metadata: Mapping[Any, Any] | None = None,
                 label: str | None = None):
        super().__init__(name, dll_dir, serial, simulation, metadata, label)

        # Update the device with stored settings. This is necessary to be able
        # to convert units since there are specific formulae for each motor
        # taking into account Gearing, Pitch, Steps Per Revolution etc.
        self._kinesis.load_settings()

    def _init_kinesis(self, dll_dir: str | pathlib.Path | None,
                      simulation: bool) -> ThorlabsKinesis:
        return ThorlabsKinesis(
            'Thorlabs.MotionControl.IntegratedStepperMotors.dll',
            self._prefix,
            dll_dir,
            simulation
        )
