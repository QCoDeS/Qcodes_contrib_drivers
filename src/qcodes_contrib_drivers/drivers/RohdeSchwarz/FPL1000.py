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
from qcodes.validators import Arrays, Ints, Numbers, Enum
from qcodes.parameters import (
    Parameter,
    ParameterWithSetpoints,
    create_on_off_val_mapping,
)


class RohdeSchwarz_FPL1000(VisaInstrument):
    """
    QCoDeS driver for Rohde & Schwarz FPL1000 series spectrum analyzers.

    Tested on FPL1026.

    Note that this driver assumes a certain configuration of the instrument
    state, and changing some settings in the GUI, such as the measurement mode
    (spectrum or spurious emissions), may lead to unexpected results. Because of
    this, a reset to the initial state (equivalent to pressing the PRESET button
    on the front panel) is performed by default when connecting.

    Args:
        name: name for the instrument
        address: Visa resource address, for exmample "TCPIP::192.123.45.67::inst0::INSTR"
        reset: Reset the device to the preset state after connecting
    """

    def __init__(
        self,
        name: str,
        address: str,
        terminator: str = "\n",
        reset: bool = True,
        **kwargs,
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

        self.sweep_count = self.add_parameter(
            "sweep_count",
            label="Averaging sweep count",
            get_cmd="SWEep:COUNt?",
            set_cmd="SWEep:COUNt {}",
            get_parser=int,
            vals=Ints(min_value=0),
        )
        """
        Defines the number of sweeps that the application uses to average
        traces.

        In continuous sweep mode, the application calculates the moving average
        over the average count. If the sweep count is zero, the trace is a
        weighted average of the last 10 traces, with a weight of 9 on the most
        recent trace (see the section "How many traces are averaged - sweep
        count + Sweep mode" in the manual for details).

        In single sweep mode, the application stops the measurement and
        calculates the average after the average count has been reached. If the
        sweep count is zero, the trace is the average of the previously measured
        trace and the current trace (see the section "How many traces are
        averaged - sweep count + Sweep mode" in the manual for details).
        """

        self.sweep_time = self.add_parameter(
            "sweep_time",
            label="Sweep time",
            unit="s",
            get_cmd="SWEep:TIME?",
            set_cmd="SWEep:TIME {}",
            get_parser=float,
        )
        """
        Defines the sweep time. Setting this parameter automatically decouples
        the time from any other settings.

        Note that this command queries only the time required to capture the
        data, not to process it. To obtain an estimation of the total capture
        and processing time, use the sweep_duration parameter.
        """

        self.sweep_time_auto_enabled = self.add_parameter(
            "sweep_time_auto_enabled",
            label="Automatic sweep time",
            get_cmd="SWEep:TIME:AUTO?",
            set_cmd="SWEep:TIME:AUTO {}",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """
        Enable or disable automatic sweep time based on the span and the
        resolution and video bandwidths.
        """

        self.sweep_duration = self.add_parameter(
            "sweep_duration",
            label="Sweep acquisition duration estimate",
            unit="s",
            get_cmd="SWEep:DURation?",
            set_cmd=False,
            get_parser=float,
        )
        """
        Provides an estimation of the total time required to capture the data
        and process it. This time span may be considerably longer than the
        actual sweep time (see the sweep_time parameter).

        Tip: To determine the necessary timeout for data capturing in a remote
        control program, double the estimated time and add 1 second.
        """

        self.continuous_sweep_enabled = self.add_parameter(
            "continuous_sweep_enabled",
            label="Continuous sweep mode",
            get_cmd="INITiate:CONTinuous?",
            set_cmd="INITiate:CONTinuous {}",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )

        self.resolution_bandwidth = self.add_parameter(
            "resolution_bandwidth",
            label="Resolution bandwidth",
            unit="Hz",
            get_cmd="BWIDth:RESolution?",
            set_cmd="BWIDth:RESolution {}",
            get_parser=float,
            # note: actual value limits depend on model
            vals=Numbers(min_value=0),
        )
        """
        Defines the resolution bandwidth and decouples the resolution bandwidth
        from the span.

        For statistics measurements, this command defines the *demodulation*
        bandwidth.
        """

        self.resolution_bandwidth_auto_enabled = self.add_parameter(
            "resolution_bandwidth_auto_enabled",
            label="Automatic resolution bandwidth",
            get_cmd="BWIDth:RESolution:AUTO?",
            set_cmd="BWIDth:RESolution:AUTO {}",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """
        Couples and decouples the resolution bandwidth to the span.
        """

        self.video_bandwidth = self.add_parameter(
            "video_bandwidth",
            label="Video bandwidth",
            unit="Hz",
            get_cmd="BWIDth:VIDeo?",
            set_cmd="BWIDth:VIDeo {}",
            get_parser=float,
            # note: actual value limits depend on model
            vals=Numbers(min_value=0),
        )
        """
        Defines the video bandwidth.

        Setting this parameter decouples the video bandwidth from the resolution
        bandwidths.
        """

        self.video_bandwidth_auto_enabled = self.add_parameter(
            "video_bandwidth_auto_enabled",
            label="Automatic video bandwidth",
            get_cmd="BWIDth:VIDeo:AUTO?",
            set_cmd="BWIDth:VIDeo:AUTO {}",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """
        Couples and decouples the video bandwidth to the resolution bandwidth.
        """

        self.frequency = self.add_parameter(
            "frequency",
            label="Frequency",
            unit="Hz",
            parameter_class=FPL1000FrequencyAxis,
            # Only support one trace for now
            trace_number=1,
            vals=Arrays(shape=(self.sweep_points.get_latest,)),
            snapshot_exclude=True,
        )
        """
        Frequency axis of trace 1. In zero-span mode, this is the time axis.
        """

        self.spectrum = self.add_parameter(
            "spectrum",
            label="Spectrum",
            parameter_class=FPL1000Spectrum,
            setpoints=(self.frequency,),
            # note: according to the manual, the unit may be actually different
            # depending on the acquisition mode, that is left as an exercise for
            # a future driver version
            unit="dBm",
            # Only support one trace for now
            trace_number=1,
            vals=Arrays(shape=(self.sweep_points.get_latest,)),
            snapshot_exclude=True,
        )
        """
        Spectrum of trace 1.
        """

        self.reference_oscillator_source = self.add_parameter(
            "reference_oscillator_source",
            label="Reference oscillator source",
            get_cmd="ROSCillator:SOURce?",
            set_cmd="ROSCillator:SOURce {}",
            vals=Enum("INT", "EXT"),
        )
        """
        Select the reference oscillator. INT uses the internal 10 MHz reference
        oscillator, while EXT uses the external reference from the "REF INPUT
        10 MHZ" connector. If the external reference is not available, an error
        indicator is shown on the screen.
        """

        if reset:
            self.reset()

        self.connect_message()

    def reset(self):
        """
        Sets the instrument to a defined default status. The default settings
        are indicated in the description of commands.
        """
        self.write("SYSTem:PRESet")


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
        return np.array([float(x) for x in self.instrument.ask(query).split(",")])


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
        instr: RohdeSchwarz_FPL1000 = self.root_instrument
        with (
            instr.continuous_sweep_enabled.set_to(False),
            instr.timeout.set_to(self._get_timeout()),
        ):
            instr.write("INITiate")
            instr.ask("*OPC?")
            query = f"TRACe? TRACE{self.trace_number}"
            # note: assumes ASCII format
            return np.array([float(x) for x in instr.ask(query).split(",")])

    def _get_timeout(self):
        """
        Approximate timeout required to acquire all data, including averaging
        """
        instr: RohdeSchwarz_FPL1000 = self.root_instrument
        # sweep count may be set to zero
        n_avg = max(instr.sweep_count(), 1)
        timeout = max(
            instr.timeout(),
            # from the manual: "Tip: To determine the necessary timeout for data
            # capturing in a remote control program, double the estimated time
            # and add 1 second."
            (instr.sweep_duration() * n_avg) * 2 + 1,
        )
        return timeout
