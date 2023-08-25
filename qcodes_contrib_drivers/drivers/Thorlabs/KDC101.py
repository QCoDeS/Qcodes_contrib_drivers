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

    def __init__(self, name: str, apt: Thorlabs_APT, device_id: int = 0, serial_number=0, **kwargs):
        super().__init__(name, device_id=device_id,
                         hw_type=ThorlabsHWType.KDC101,
                         serial_number=serial_number,
                         apt=apt, **kwargs)