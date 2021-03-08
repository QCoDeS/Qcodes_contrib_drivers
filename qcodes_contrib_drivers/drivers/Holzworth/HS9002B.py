# This Python file uses the following encoding: utf-8

import numpy as np
from typing import Tuple

from qcodes import VisaInstrument
from qcodes.utils.validators import Numbers, Enum, Ints


class HS9002B(VisaInstrument):
    """
    This is the QCoDeS python driver for the
    """


    def __init__(self, name       : str,
                       address    : str,
                       terminator : str="\n",
                       timeout    : int=100000,
                       **kwargs):
        """
        QCoDeS driver for the VNA S5180 from Copper Mountain

        Args:
        name (str): Name of the instrument.
        address (str): Address of the instrument.
        terminator (str, optional, by default "\n"): Terminator character of
            the string reply.
        timeout (int, optional, by default 100000): VISA timeout is set purposly
            to a long time to allow long spectrum measurement.
        """

        super().__init__(name       = name,
                         address    = address,
                         terminator = terminator,
                         timeout    = timeout,
                         **kwargs)

        self.add_function('reset', call_cmd='*RST')

        self.connect_message()
