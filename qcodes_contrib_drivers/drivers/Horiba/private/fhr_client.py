from __future__ import annotations

import ctypes
import os
import pathlib
from pathlib import Path
from typing import Tuple

try:
    from msl.loadlib import Client64
except ImportError:
    raise ImportError('This driver requires the msl.loadlib package for '
                      'communicating with a 32-bit dll. You can install it '
                      "by running 'pip install msl.loadlib'")


class FHRClient(Client64):

    def __init__(self, dll_dir: str | os.PathLike | pathlib.Path,
                 filename: str = 'SpeControl'):
        module32 = str(Path(__file__).parent / 'fhr_server')
        super().__init__(module32=module32, dll_dir=dll_dir, filename=filename)

    def CreateSpe(self) -> int:
        """Create new spectrometer handle."""
        return self.request32('CreateSpe')

    def DeleteSpe(self, h_spe: int) -> Tuple[int, None]:
        """Delete spectrometer handle h_spe."""
        return self.request32('DeleteSpe', h_spe)

    def SpeCommand(
            self, h_spe: int, a_dsp: str, a_fun: str,
            aPar: ctypes._SimpleCData | None = None
    ) -> Tuple[int, int | None]:
        """Send command (execute a function) named "a_fun" for the
        function dispatcher named "a_dsp" for the spectrometer handled
        "h_spe". "a_par" is a pointer to the function parameters."""
        return self.request32('SpeCommand', h_spe, a_dsp, a_fun, aPar)

    def SpeCommandSetup(self, h_spe: int, a_dsp: str,
                        fields: Tuple[int, ...]) -> Tuple[int, None]:
        """Send command to set up a motor.

        Need to treat this separately since the SpeSetup structure
        must be defined in the 32-bit module. Otherwise, the 32-bit
        executable would need to know about qcodes_contrib_drivers.
        """
        return self.request32('SpeCommandSetup', h_spe, a_dsp, fields)

    def SpeCommandIniParams(self, h_spe: int, a_dsp: str,
                            fields: Tuple[int, ...]) -> Tuple[int, None]:
        """Send command to initialize a grating motor.

        Need to treat this separately since the SpeIniParams structure
        must be defined in the 32-bit module. Otherwise, the 32-bit
        executable would need to know about qcodes_contrib_drivers.
        """
        return self.request32('SpeCommandIniParams', h_spe, a_dsp, fields)
