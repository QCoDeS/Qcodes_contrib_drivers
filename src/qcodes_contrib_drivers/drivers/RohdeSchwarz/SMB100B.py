# -*- coding: utf-8 -*-
"""QCoDeS-Driver for Rohde & Schwartz SMB100B RF and microwave signal generator:
https://www.rohde-schwarz.com/us/products/test-and-measurement/analog-signal-generators/rs-smb100b-rf-and-microwave-signal-generator_63493-553988.html

Based on the SMB100A driver by:
    Julien Barrier <julien@julienbarrier.eu>, 2023
"""
from .private.SMB100 import _RohdeSchwarzSMB100


class RohdeSchwarzSMB100B(_RohdeSchwarzSMB100):
    """
    Class to represent a Rohde & Schwartz SMB100B RF and microwave signal
    generator

    status: beta-version

    Args:
        name: name for the instrument
        address: Visa resource name to connect
    """

    model = 'SMB100B'
