from __future__ import annotations

import logging
from pathlib import Path
from typing import Tuple

from msl.loadlib import Server32

try:
    import ctypes.wintypes
except ImportError:
    import ctypes
    from types import ModuleType

    ctypes.wintypes = ModuleType('wintypes')
    ctypes.wintypes.DWORD = ctypes.c_ulong

LOG = logging.getLogger(__name__)


# Uncomment the line below to log (cannot control the logger from the
# client since the server runs on a different executable).
# logging.basicConfig(filename='path/to/log', level=logging.DEBUG)


class FHRServer(Server32):
    class _SpeSetup(ctypes.Structure):
        _fields_ = [('Size', ctypes.wintypes.DWORD),
                    ('MinSpeed', ctypes.c_int),
                    ('MaxSpeed', ctypes.c_int),
                    ('Ramp', ctypes.c_int),
                    ('Backlash', ctypes.c_int),
                    ('Step', ctypes.c_int),
                    ('Revers', ctypes.c_int)]

    class _SpeIniParams(ctypes.Structure):
        _fields_ = [('Size', ctypes.wintypes.DWORD),
                    ('Phase', ctypes.c_int),
                    ('MinSpeed', ctypes.c_int),
                    ('MaxSpeed', ctypes.c_int),
                    ('Ramp', ctypes.c_int)]

    def __init__(self, host, port, dll_dir='', filename='SpeControl'):
        path = str(Path(dll_dir, filename).with_suffix('.dll'))

        LOG.info('Initializing FHRServer.')
        LOG.debug(f'host = {host}')
        LOG.debug(f'port = {port}')
        LOG.debug(f'path = {path}')

        super().__init__(path, 'cdll', host, port)

    def CreateSpe(self) -> int:
        """Create new spectrometer handle."""
        LOG.info('Creating spe handle.')

        return self.lib.CreateSpe()

    def DeleteSpe(self, h_spe: int):
        """Delete spectrometer handle h_spe."""
        hSpe = ctypes.c_int(h_spe)

        LOG.info(f'Deleting spe handle {hSpe}.')

        self.lib.DeleteSpe(hSpe)

    def SpeCommand(
            self, h_spe: int, a_dsp: str, a_fun: str,
            aPar: _SpeSetup | _SpeIniParams | ctypes.c_int | None = None
    ) -> Tuple[int, int | None]:
        """Send command (execute a function) named "a_fun" for the
        function dispatcher named "a_dsp" for the spectrometer handled
        "h_spe". "a_par" is a pointer to the function parameters."""
        hSpe = ctypes.c_int(h_spe)
        aDsp = ctypes.c_char_p(a_dsp.encode())
        aFun = ctypes.c_char_p(a_fun.encode())

        LOG.info('Calling SpeCommand.')
        LOG.debug(f'hSpe = {hSpe}')
        LOG.debug(f'aDsp = {aDsp}')
        LOG.debug(f'aFun = {aFun}')
        LOG.debug(f'aPar = {aPar}')

        code = self.lib.SpeCommand(
            hSpe, aDsp, aFun, ctypes.byref(aPar) if aPar is not None else None
        )
        if isinstance(aPar, ctypes._SimpleCData):
            return code, aPar.value
        return code, None

    def SpeCommandSetup(self, h_spe: int, a_dsp: str,
                        fields: Tuple[int, ...]) -> Tuple[int, int | None]:
        """Send command to set up a motor.

        Need to treat this separately since the SpeSetup structure
        must be defined in the 32-bit module. Otherwise, the 32-bit
        executable would need to know about qcodes_contrib_drivers.
        """
        setup = self._SpeSetup(28, *fields)
        return self.SpeCommand(h_spe, a_dsp, 'SetSetup', setup)

    def SpeCommandIniParams(self, h_spe: int, a_dsp: str,
                            fields: Tuple[int, ...]) -> Tuple[int, int | None]:
        """Send command to initialize a grating motor.

        Need to treat this separately since the SpeIniParams structure
        must be defined in the 32-bit module. Otherwise, the 32-bit
        executable would need to know about qcodes_contrib_drivers.
        """
        iniParams = self._SpeIniParams(20, *fields)
        return self.SpeCommand(h_spe, a_dsp, 'SetIniParams', iniParams)
