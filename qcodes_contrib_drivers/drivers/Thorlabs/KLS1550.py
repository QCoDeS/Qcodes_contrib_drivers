# -*- coding: utf-8 -*-
"""QCoDeS-Driver for Thorlab KLS1550 Laser source

Authors:
    iago-rst https://github.com/iago-rst, 2023
    Julien Barrier <julien@julienbarrier.eu>, 2023
"""
import logging
from .private.LS import _Thorlabs_LS

log = logging.getLogger(__name__)

class Thorlabs_KLS1550(_Thorlabs_LS):
    """Instrument driver for the Thorlabs KLS1550

    Args:
        name (str): Instrument name.
        serial_number (str): Serial number of the device.
        simulation (bool): Enables the simulation manager. Defaults to False
        polling (int): Polling rate in ms. Defaults to 200.
    """
    def __init__(self,
                 name: str,
                 serial_number: str,
                 simulation: bool = False,
                 polling: int = 200,
                 **kwargs):
        self._dll_path = 'Thorlabs. .dll'
        super().__init__(name, serial_number, self._dll_path,
                         self._simulation, self._polling, **kwargs)
