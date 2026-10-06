# -*- coding: utf-8 -*-
"""QCoDeS-Driver for Rohde & Schwartz SMB100A microwave signal generator:
https://www.rohde-schwarz.com/us/products/test-and-measurement/analog-signal-generators/rs-smb100a-microwave-signal-generator_63493-9379.html

Authors:
    Julien Barrier <julien@julienbarrier.eu>, 2023
"""
from .private.SMB100 import _RohdeSchwarzSMB100


class RohdeSchwarzSMB100A(_RohdeSchwarzSMB100):
    """
    Class to represent a Rohde & Schwartz SMB100A microwave signal generator

    status: beta-version

    Args:
        name: name for the instrument
        address: Visa resource name to connect
    """

    model = 'SMB100A'


#: Legacy name, kept so that existing code and station configurations keep
#: working.
RohdeSchwarz_SMB100A = RohdeSchwarzSMB100A
