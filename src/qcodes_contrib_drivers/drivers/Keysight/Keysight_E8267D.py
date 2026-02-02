import numpy as np

from qcodes import validators as vals
from qcodes.instrument import VisaInstrument
from qcodes.parameters import Parameter, create_on_off_val_mapping
from qcodes.validators import Numbers

frequency_mode_docstring = """
This command sets the frequency mode of the signal generator.

*FIXed* and *CW* These choices are synonymous. Any currently running frequency
sweeps are turned off, and the current CW frequency settings are used to control
the output frequency.

*SWEep* The effects of this choice are determined by the sweep generation type
selected. In analog sweep generation, the ramp sweep frequency settings (start,
stop, center, and span) control the output frequency. In step sweep generation,
the current step sweep frequency settings control the output frequency. In both
cases, this selection also activates the sweep. This choice is available with
Option 007 only.

*LIST* This choice selects the swept frequency mode. If sweep triggering is set
to immediate along with continuous sweep mode, executing the command starts the
LIST or STEP frequency sweep.
"""

IQsource_docstring = """
This command selects the I/Q modulator source for one of the two possible paths.

*EXTernal* This choice selects an external 50 ohm source as the I/Q input to I/Q
modulator.
*INTernal* This choice is for backward compatibility with ESG E44xxB models and
performs the same function as the BBG1 selection.
*BBG1* This choice selects the baseband generator as the source for the I/Q
modulator.
*EXT600* This choice selects a 600 ohm impedance for the I and Q input connectors
and routes the applied signals to the I/Q modulator.
*OFF* This choice disables the I/Q input.
"""


class Keysight_E8267D(VisaInstrument):
    """
    This is the qcodes driver for the Keysight_E8267D signal generator

    Status: beta-version.
        TODO:
        - Add all parameters that are in the manual

    This driver will most likely work for multiple Agilent sources.

    This driver does not contain all commands available for the E8527D but only
    the ones most commonly used.
    """

    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, **kwargs)

        # Frequency parameters
        self.frequency: Parameter = self.add_parameter(
            name="frequency",
            label="Frequency",
            unit="Hz",
            get_cmd="FREQ:CW?",
            set_cmd="FREQ:CW" + " {:.4f}",
            get_parser=float,
            set_parser=float,
            vals=vals.Numbers(1e5, 20e9),
            docstring="Adjust the RF output frequency",
        )
        self.freq_offset: Parameter = self.add_parameter(
            name="freq_offset",
            label="Frequency offset",
            unit="Hz",
            get_cmd="FREQ:OFFS?",
            set_cmd="FREQ:OFFS {}",
            get_parser=float,
            vals=Numbers(min_value=-200e9, max_value=200e9),
        )
        self.frequency_offset = self.freq_offset  # Deprecated alias for freq_offset
        self.freq_mode: Parameter = self.add_parameter(
            "freq_mode",
            label="Frequency mode",
            set_cmd="FREQ:MODE {}",
            get_cmd="FREQ:MODE?",
            get_parser=lambda s: s.strip(),
            vals=vals.Enum("FIX", "CW", "SWE", "LIST"),
            docstring=frequency_mode_docstring,
        )
        self.frequency_mode = self.freq_mode  # Deprecated alias for freq_mode
        self.phase: Parameter = self.add_parameter(
            name="phase",
            label="Phase",
            unit="deg",
            get_cmd="PHASE?",
            set_cmd="PHASE" + " {:.8f}",
            get_parser=self.rad_to_deg,
            set_parser=self.deg_to_rad,
            vals=vals.Numbers(-180, 180),
        )

        # Power parameters
        self.power: Parameter = self.add_parameter(
            name="power",
            label="Power",
            unit="dBm",
            get_cmd="POW:AMPL?",
            set_cmd="POW:AMPL" + " {:.4f}",
            get_parser=float,
            set_parser=float,
            vals=vals.Numbers(-130, 25),
        )
        self.output_rf: Parameter = self.add_parameter(
            "output_rf",
            get_cmd=":OUTP?",
            set_cmd="OUTP {}",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        self.status = self.output_rf
        self.modulation_rf: Parameter = self.add_parameter(
            name="modulation_rf",
            get_cmd="OUTP:MOD?",
            set_cmd="OUTP:MOD {}",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        self.modulation_rf_enabled = self.modulation_rf
        self.alc_enabled: Parameter = self.add_parameter(
            "alc_enabled",
            get_cmd="POW:ALC?",
            set_cmd="POW:ALC {}",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
            docstring="Enables or disables the automatic leveling control (ALC) circuit.",
        )
        self.attenuator_hold_enabled: Parameter = self.add_parameter(
            "attenuator_hold_enabled",
            get_cmd="POW:ATT:AUTO?",
            set_cmd="POW:ATT:AUTO {}",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
            docstring="Sets the state of the attenuator hold function.",
        )
        self.attenuator_level: Parameter = self.add_parameter(
            "attenuator_level",
            label="Attenuator Level",
            unit="dB",
            get_cmd="POW:ATT?",
            set_cmd="POW:ATT {:.1f}",
            get_parser=float,
            set_parser=float,
            vals=vals.Numbers(0, 115),
            docstring="Sets the attenuation level when the attenuator hold is active.",
        )

        # IQ Modulation parameters
        self.IQmodulator_enabled: Parameter = self.add_parameter(
            "IQmodulator_enabled",
            get_cmd="DM:STATe?",
            set_cmd="DM:STATe {}",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
            docstring="Enables or disables the internal I/Q modulator. Source can be external or internal.",
        )
        self.IQsource1: Parameter = self.add_parameter(
            "IQsource1",
            get_cmd="DM:SOUR1?",
            set_cmd="DM:SOUR1 {}",
            get_parser=lambda s: s.strip(),
            vals=vals.Enum("OFF", "EXT", "EXT600", "INT"),
            docstring=IQsource_docstring,
        )
        self.IQsource2: Parameter = self.add_parameter(
            "IQsource2",
            get_cmd="DM:SOUR2?",
            set_cmd="DM:SOUR2 {}",
            get_parser=lambda s: s.strip(),
            vals=vals.Enum("OFF", "EXT", "EXT600", "INT"),
            docstring=IQsource_docstring,
        )
        self.IQadjustments_enabled: Parameter = self.add_parameter(
            "IQadjustments_enabled",
            get_cmd="DM:IQAD?",
            set_cmd="DM:IQAD {}",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
            docstring="Enable or disable IQ adjustments",
        )
        self.I_offset: Parameter = self.add_parameter(
            "I_offset",
            get_cmd="DM:IQAD:IOFF?",
            set_cmd="DM:IQAD:IOFF {}",
            get_parser=float,
            set_parser=float,
            vals=vals.Numbers(-100, 100),
            docstring="I channel offset in percentage",
        )
        self.Q_offset: Parameter = self.add_parameter(
            "Q_offset",
            get_cmd="DM:IQAD:QOFF?",
            set_cmd="DM:IQAD:QOFF {}",
            get_parser=float,
            set_parser=float,
            vals=vals.Numbers(-100, 100),
            docstring="Q channel offset in percentage",
        )
        self.IQ_quadrature: Parameter = self.add_parameter(
            "IQ_quadrature",
            get_cmd="DM:IQAD:QSK?",
            set_cmd="DM:IQAD:QSK {}",
            get_parser=float,
            set_parser=float,
            docstring="IQ quadrature offset",
            unit="deg",
        )

        # Pulse Modulation parameters
        self.pulse_modulation_enabled: Parameter = self.add_parameter(
            "pulse_modulation_enabled",
            get_cmd="PULM:STATe?",
            set_cmd="PULM:STATe {}",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
            docstring="Enable or disable pulse modulation path",
        )
        self.pulse_modulation_source: Parameter = self.add_parameter(
            "pulse_modulation_source",
            get_cmd="PULM:SOURce?",
            set_cmd="PULM:SOURce {}",
            get_parser=lambda s: s.strip(),
            vals=vals.Enum("EXT", "INT", "SCAL"),
        )

        # Wideband Modulation parameters
        self.wideband_amplitude_modulation_enabled: Parameter = self.add_parameter(
            "wideband_amplitude_modulation_enabled",
            get_cmd="AM:WID:STATe?",
            set_cmd="AM:WID:STATe {}",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
            docstring="This command enables or disables wideband amplitude modulation",
        )
        self.wideband_IQ_enabled: Parameter = self.add_parameter(
            "wideband_IQ_enabled",
            get_cmd="WDM:STATe?",
            set_cmd="WDM:STATe {}",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
            docstring="This command enables or disables the wideband I/Q modulator.",
        )
        self.wideband_IQ_adjustments_enabled: Parameter = self.add_parameter(
            "wideband_IQ_adjustments_enabled",
            get_cmd="WDM:IQADjustment:STATe?",
            set_cmd="WDM:IQADjustment:STATe {}",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
            docstring="This command enables or disables the wideband I/Q adjustments.",
        )
        self.wideband_I_offset: Parameter = self.add_parameter(
            "wideband_I_offset",
            get_cmd="WDM:IQADjustment:IOFFset?",
            set_cmd="WDM:IQADjustment:IOFFset {}",
            get_parser=float,
            set_parser=float,
            vals=vals.Numbers(-50, 50),
            docstring="This command sets the I channel offset value for wideband modulation.",
        )
        self.wideband_Q_offset: Parameter = self.add_parameter(
            "wideband_Q_offset",
            get_cmd="WDM:IQADjustment:QOFFset?",
            set_cmd="WDM:IQADjustment:QOFFset {}",
            get_parser=float,
            set_parser=float,
            vals=vals.Numbers(-50, 50),
            docstring="This command sets the Q channel offset value for wideband modulation.",
        )
        self.wideband_IQ_quadrature: Parameter = self.add_parameter(
            "wideband_IQ_quadrature",
            get_cmd="WDM:IQADjustment:QSKew?",
            set_cmd="WDM:IQADjustment:QSKew {}",
            get_parser=float,
            set_parser=float,
            vals=vals.Numbers(-10, 10),
            unit="deg",
            docstring=(
                "This command adjusts the phase angle between the I and Q vectors for "
                "wideband modulation."
            ),
        )

        self.connect_message()

    def on(self):
        """Turn the RF output on."""
        self.output_rf("on")

    def off(self):
        """Turn the RF output off."""
        self.output_rf("off")

    @staticmethod
    def deg_to_rad(angle_deg):
        """Convert degrees to radians."""
        return np.deg2rad(float(angle_deg))

    @staticmethod
    def rad_to_deg(angle_rad):
        """Convert radians to degrees."""
        return np.rad2deg(float(angle_rad))
