# -*- coding: utf-8 -*-
"""QCoDeS-Driver for Thorlab KLS1550 Laser source

Authors:
    iago-rst https://github.com/iago-rst, 2023
    Julien Barrier <julien@julienbarrier.eu>, 2023
"""
import logging
from typing import Optional
from .private.LS import _Thorlabs_LS

log = logging.getLogger(__name__)

class Thorlabs_KLS1550(_Thorlabs_LS):
    """Instrument driver for the Thorlabs KLS1550

    Args:
        name: Instrument name.
        serial_number: Serial number of the device.
        dll_path: Path to the kinesis dll for the instrument to use.
        dll_dir: Directory in which the kinesis dll are stored.
        simulation: Enables the simulation manager.
        polling: Polling rate in ms.
    """
    def __init__(self,
                 name: str,
                 serial_number: str,
                 dll_path: Optional[str] = None,
                 dll_dir: Optional[str] = None,
                 simulation: bool = False,
                 polling: int = 200,
                 **kwargs):
        if dll_path:
            self._dll_path = dll_path
        else:
            self._dll_path = 'Thorlabs.MotionControl.KCube.LaserSource.dll'
        self._dll_dir: Optional[str] = dll_dir if dll_dir else None
        super().__init__(name, serial_number, self._dll_path, self._dll_dir,
                         simulation, polling, **kwargs)
