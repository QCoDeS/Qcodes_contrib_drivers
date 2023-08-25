# -*- coding: utf-8 -*-
"""QCoDes-Driver for Thorlab KDC101 K-Cube Brushed DC Servo Motor Controller
https://www.thorlabs.com/thorproduct.cfm?partnumber=KDC101

Authors:
    Julien Barrier, <julien@julienbarrier.eu>
"""

from .private.APT import Thorlabs_APT, ThorlabsHWType
from .private.rotators import _Thorlabs_rotator


class Thorlabs_KDC101(_Thorlabs_rotator):
    """
    Instrument driver for the Thorlabs KDC101 servo motor controller.

    Args:
        name: Instrument name.
        device_id: ID for the desired rotator.
        apt: Thorlabs APT server.

    Attributes:
        apt: Thorlabs APT server.
        serial_number: Serial number of the device.
        model: Model description.
        version: Firmware version.
    """

    def __init__(self, name: str, device_id: int, apt: Thorlabs_APT, **kwargs):
        super().__init__(name, device_id=device_id, hwtype=ThorlabsHWType.KDC101, apt=apt, **kwargs)