# -*- coding: utf-8 -*-
"""QCoDes-Driver for Thorlab TDC001 T-Cube Brushed DC Servo Motor Controller
https://www.thorlabs.com/thorproduct.cfm?partnumber=TDC001

Authors:
    Julien Barrier, <julien@julienbarrier.eu>
"""
import logging

from .private.CC import _Thorlabs_CC

log = logging.getLogger(__name__)

class Thorlabs_TDC001(_Thorlabs_CC):
    """Instrument driver for the Thorlabs TDC001 servo motor controller

    Args:
        name (str): Instrument name.
        serial_number (str): Serial number of the device.
        simulation (bool): Enables the simulation manager. Defaults to False.
        polling (int): Polling rate in ms. Defaults to 200.
        home (bool): Sets the device to home state. Defaults to False.
    """
    _CONDITIONS = ['homed', 'moved', 'stopped', 'limit_updated']
    def __init__(self,
                 name: str,
                 serial_number: str,
                 simulation: bool = False,
                 polling: int = 200,
                 home: bool = False,
                 **kwargs):
        self._dll_path = 'Thorlabs.MotionControl.TCube.DCServo.dll'
        super().__init__(name, serial_number, self._dll_path,
                         simulation, polling, home, **kwargs)