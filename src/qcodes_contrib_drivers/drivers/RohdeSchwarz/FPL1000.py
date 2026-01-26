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
from qcodes.validators import Arrays, Ints
from qcodes import Parameter, ParameterWithSetpoints


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

        self.sweep_points = self.add_parameter(
            "sweep_points",
            label="Sweep points",
            get_cmd="SWEep:POINts?",
            set_cmd="SWEep:POINts {}",
            get_parser=int,
            # minimum & maximum from manual
            vals=Ints(min_value=101, max_value=100_001),
        )
        """
        This parameter defines the number of sweep points to analyze after a
        sweep.

        Note that the number of sweep points is limited to 10001 when measuring
        spurious emissions.
        """

        self.frequency_axis1 = self.add_parameter(
            "frequency_axis1",
            label="Trace 1 frequency",
            unit="Hz",
            parameter_class=FPL1000FrequencyAxis,
            trace_number=1,
            vals=Arrays(shape=(self.sweep_points.get_latest,)),
        )

        self.spectrum1 = self.add_parameter(
            "spectrum1",
            label="Trace 1 spectrum",
            parameter_class=FPL1000Spectrum,
            setpoints=(self.frequency_axis1,),
            #unit=???, # TODO
            trace_number=1,
            vals=Arrays(shape=(self.sweep_points.get_latest,)),
        )

        self.connect_message()


# FPL1000 supports up to 6 traces
TraceNumber = Literal[1, 2, 3, 4, 5, 6]


class FPL1000FrequencyAxis(Parameter):
    """
    Array-valued parameter for frequency axis of FPL1000 spectrum analyzer
    """
    def __init__(
        self,
        name: str,
        instrument: RohdeSchwarz_FPL1000,
        trace_number: TraceNumber,
        **kwargs,
    ):
        super().__init__(
            name=name,
            instrument=instrument,
            **kwargs,
        )
        self.trace_number = trace_number

    def get_raw(self):
        query = f"TRACe:X? TRACE{self.trace_number}"
        # note: assumes ASCII format
        return np.array([
            float(x) for x in self.instrument.ask(query).split(",")
        ])


class FPL1000Spectrum(ParameterWithSetpoints):
    """
    Array-valued parameter for retrieving spectrum data

    If a long-running sweep is interrupted, the SCPI buffers should be cleared
    with the device_clear() function.
    """
    def __init__(
        self,
        name: str,
        instrument: RohdeSchwarz_FPL1000,
        trace_number: TraceNumber,
        **kwargs,
    ) -> None:
        super().__init__(name=name, instrument=instrument, **kwargs)
        self.trace_number = trace_number

    def get_raw(self):
        query = f"TRACe? TRACE{self.trace_number}"
        # note: assumes ASCII format
        return np.array([
            float(x) for x in self.instrument.ask(query).split(",")
        ])
