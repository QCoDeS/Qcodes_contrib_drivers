# -*- coding: utf-8 -*-
"""QCoDes-Driver for Thorlab KDC101 K-Cube Brushed DC Servo Motor Controller
https://www.thorlabs.com/thorproduct.cfm?partnumber=KDC101

Authors:
    Julien Barrier, <julien@julienbarrier.eu>
"""
import logging
from typing import Optional

from .private.CC import _Thorlabs_CC

log = logging.getLogger(__name__)

class Thorlabs_KDC101(_Thorlabs_CC):
    """Instrument driver for the Thorlabs KDC101 servo motor controller

    Args:
        name: Instrument name.
        serial_number: Serial number of the device.
        dll_path: Path to the kinesis dll for the instrument to use.
        dll_dir: Directory in which the kinesis dll are stored.
        simulation: Enables the simulation manager.
        polling: Polling rate in ms.
        home: Sets the device to home state.
    """
    def __init__(self,
                 name: str,
                 serial_number: str,
                 dll_path: Optional[str] = None,
                 dll_dir: Optional[str] = None,
                 simulation: bool = False,
                 polling: int = 200,
                 home: bool = False,
                 **kwargs):
        if dll_path:
            self._dll_path = dll_path
        else:
            self._dll_path = 'Thorlabs.MotionControl.KCube.DCServo.dll'
        self._dll_dir: Optional[str] = dll_dir if dll_dir else None
        super().__init__(name, serial_number, self._dll_path, self._dll_dir,
                         simulation, polling, home, **kwargs)
