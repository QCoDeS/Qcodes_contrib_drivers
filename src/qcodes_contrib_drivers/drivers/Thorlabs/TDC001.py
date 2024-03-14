# -*- coding: utf-8 -*-
"""QCoDes-Driver for Thorlab TDC001 T-Cube Brushed DC Servo Motor Controller
https://www.thorlabs.com/thorproduct.cfm?partnumber=TDC001

Authors:
    Julien Barrier, <julien@julienbarrier.eu>
"""

from .private.kinesis import enums
from .private.kinesis.cc import KinesisCCInstrument


class ThorlabsTDC001(KinesisCCInstrument, prefix='CC',
                     hardware_type=enums.KinesisHWType.TCubeDCServo):
    """Instrument driver for the Thorlabs TDC001 servo motor controller.
    """
