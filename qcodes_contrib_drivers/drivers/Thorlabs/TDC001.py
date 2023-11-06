# -*- coding: utf-8 -*-
"""QCoDes-Driver for Thorlab TDC001 T-Cube Brushed DC Servo Motor Controller
https://www.thorlabs.com/thorproduct.cfm?partnumber=TDC001

Authors:
    Julien Barrier, <julien@julienbarrier.eu>
"""
import logging
from typing import Optional

from .private.CC import _Thorlabs_CC

log = logging.getLogger(__name__)

class Thorlabs_TDC001(_Thorlabs_CC):
    """Instrument driver for the Thorlabs TDC001 servo motor controller

    Args:
        name: Instrument name.
        serial_number: Serial number of the device.
        dll_path: Path to the kinesis dll for the instrument to use.
        dll_dir: Directory in which the kinesis dll are stored.
        simulation: Enables the simulation manager. Defaults to False.
        polling: Polling rate in ms. Defaults to 200.
        home: Sets the device to home state. Defaults to False.
    """
    _CONDITIONS = ['homed', 'moved', 'stopped', 'limit_updated']
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
            self._dll_path = 'Thorlabs.MotionControl.TCube.DCServo.dll'
            self._dll_dir: Optional[str] = dll_dir if dll_dir else None
        super().__init__(name, serial_number, self._dll_path, self._dll_dir,
                         simulation, polling, home, **kwargs)
