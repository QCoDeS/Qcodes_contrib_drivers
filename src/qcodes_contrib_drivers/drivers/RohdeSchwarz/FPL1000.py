# QCoDeS driver to communicate with Rohde & Schwarz FPL1000 series spectrum analyzers
# Copyright (C) 2026 RIKEN, András Márton Gunyhó <andras.gunyho@riken.jp>
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>.

from typing import Literal

import numpy as np
from qcodes.instrument import VisaInstrument


class RohdeSchwarz_FPL1000(VisaInstrument):
    """
    QCoDeS driver for Rohde & Schwarz FPL1000 series spectrum analyzers.

    Tested on FPL1026.

    Args:
        name: name for the instrument
        address: Visa resource address, for exmample "TCPIP::192.123.45.67::inst0::INSTR"
    """

    def __init__(
        self, name: str, address: str, terminator: str = "\n", **kwargs
    ) -> None:
        super().__init__(name=name, address=address, terminator=terminator, **kwargs)

        self.frequency_start = self.add_parameter(
            "frequency_start",
            label="Sweep start frequency",
            unit="Hz",
            get_cmd="FREQuency:STARt?",
            set_cmd="FREQuency:STARt {}",
            get_parser=float,
        )

        self.frequency_stop = self.add_parameter(
            "frequency_stop",
            label="Sweep stop frequency",
            unit="Hz",
            get_cmd="FREQuency:STOP?",
            set_cmd="FREQuency:STOP {}",
            get_parser=float,
        )

        self.frequency_center = self.add_parameter(
            "frequency_center",
            label="Sweep center frequency",
            unit="Hz",
            get_cmd="FREQuency:CENTer?",
            set_cmd="FREQuency:CENTer {}",
            get_parser=float,
        )

        self.frequency_span = self.add_parameter(
            "frequency_span",
            label="Sweep frequency span",
            unit="Hz",
            get_cmd="FREQuency:SPAN?",
            set_cmd="FREQuency:SPAN {}",
            get_parser=float,
        )
        """
        Defines the frequency span.

        If you set a span of 0 Hz, the FPL starts a measurement in the time
        domain.
        """

        self.connect_message()
