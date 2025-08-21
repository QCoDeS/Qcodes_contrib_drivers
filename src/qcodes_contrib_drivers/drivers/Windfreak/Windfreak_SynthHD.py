from qcodes import Instrument, InstrumentChannel
import qcodes.parameters
from qcodes.validators import Numbers, Enum, Ints
from windfreak import SynthHD

LETTERS = '-ABCDEFGHIJKLMNOPQRSTUVWXYZ'

class SynthHDChannel(InstrumentChannel):
    def __init__(self, parent: Instrument, name: str, index: int, **kwargs):
        super().__init__(parent, name, **kwargs)
        self._channel = parent._synth[index-1]

        # Frequency parameter
        f_range = self._channel.frequency_range
        if f_range:
            self.add_parameter(
                "frequency",
                label="Frequency",
                unit="Hz",
                get_cmd=lambda: self._channel.frequency,
                set_cmd=lambda value: setattr(self._channel, 'frequency', value),
                vals=Numbers(f_range['start'], f_range['stop']),
                docstring="Frequency in Hz"
            )

        # Power parameter
        p_range = self._channel.power_range
        if p_range:
            self.add_parameter(
                "power",
                label="Power",
                unit="dBm",
                get_cmd=lambda: self._channel.power,
                set_cmd=lambda value: setattr(self._channel, 'power', value),
                vals=Numbers(p_range['start'], p_range['stop']),
                docstring="Power in dBm"
            )

        # Phase parameter
        self.add_parameter(
            "phase",
            label="Phase",
            unit="degrees",
            get_cmd=lambda: self._channel.phase,
            set_cmd=lambda value: setattr(self._channel, 'phase', value),
            vals=Numbers(0, 360),
            docstring="Phase in degrees"
        )

        # Enable output parameter
        self.add_parameter(
            "enable",
            label="Output Enable",
            get_cmd= lambda: self._synth.enable,
            set_cmd= lambda value: setattr(self._channel, 'enable', value),
            val_mapping= qcodes.parameters.create_on_off_val_mapping(),
            vals=Enum(True, False),
            docstring="Output enable"
        )

        # RF Enable parameter
        self.add_parameter(
            "rf_enable",
            label="RF Enable",
            get_cmd=lambda: self._channel.rf_enable,
            set_cmd=lambda value: setattr(self._channel, 'rf_enable', value),
            val_mapping= qcodes.parameters.create_on_off_val_mapping(),
            vals=Enum(True, False),
            docstring="RF output enable"
        )

        # PA Enable parameter
        self.add_parameter(
            "pa_enable",
            label="PA Enable",
            get_cmd=lambda: self._channel.pa_enable,
            set_cmd=lambda value: setattr(self._channel, 'pa_enable', value),
            val_mapping= qcodes.parameters.create_on_off_val_mapping(),
            vals=Enum(True, False),
            docstring="PA enable"
        )

        # PLL Enable parameter
        self.add_parameter(
            "pll_enable",
            label="PLL Enable",
            get_cmd=lambda: self._channel.pll_enable,
            set_cmd=lambda value: setattr(self._channel, 'pll_enable', value),
            val_mapping= qcodes.parameters.create_on_off_val_mapping(),
            vals=Enum(True, False),
            docstring="PLL enable"
        )

        # VGA DAC parameter
        vga_range = self._channel.vga_dac_range
        if vga_range:
            self.add_parameter(
                "vga_dac",
                label="VGA DAC",
                get_cmd=lambda: self._channel.vga_dac,
                set_cmd=lambda value: setattr(self._channel, 'vga_dac', value),
                vals=Ints(vga_range['start'], vga_range['stop']),
                docstring="VGA DAC value"
            )

        # Temperature Compensation Mode parameter
        self.add_parameter(
            "temp_compensation_mode",
            label="Temperature Compensation Mode",
            get_cmd=lambda: self._channel.temp_compensation_mode,
            set_cmd=lambda value: setattr(self._channel, 'temp_compensation_mode', value),
            vals=Enum(*self._channel.temp_compensation_modes),
            docstring="Temperature compensation mode"
        )

        # Channel Spacing parameter (only for v2)
        if hasattr(self._channel, 'channel_spacing_range'):
            cs_range = self._channel.channel_spacing_range
            if cs_range:
                self.add_parameter(
                    "channel_spacing",
                    label="Channel Spacing",
                    unit="Hz",
                    get_cmd=lambda: self._channel.channel_spacing,
                    set_cmd=lambda value: setattr(self._channel, 'channel_spacing', value),
                    vals=Numbers(cs_range['start'], cs_range['stop']),
                    docstring="Channel spacing in Hz"
                )


class WindfreakSynthHD(Instrument):
    def __init__(self, name: str, devpath: str, **kwargs):
        super().__init__(name, **kwargs)
        self._synth = SynthHD(devpath)

        # Add channels

        for i in range(1, len(self._synth)+1):
            channel = SynthHDChannel(self, f"channel_{LETTERS[i]}", i)
            self.add_submodule(f"channel_{LETTERS[i]}", channel)

        # Reference Mode parameter
        self.add_parameter(
            "reference_mode",
            label="Reference Mode",
            get_cmd= lambda: self._synth.reference_mode,
            set_cmd= lambda value: setattr(self._synth, 'reference_mode', value),
            vals=Enum(*self._synth.reference_modes),
            docstring="Frequency reference mode"
        )

        # Trigger Mode parameter
        self.add_parameter(
            "trigger_mode",
            label="Trigger Mode",
            get_cmd= lambda: self._synth.trigger_mode,
            set_cmd= lambda value: setattr(self._synth, 'trigger_mode', value),
            vals=Enum(*self._synth.trigger_modes),
            docstring="Trigger mode"
        )

        # Temperature parameter
        self.add_parameter(
            "temperature",
            label="Temperature",
            unit="Celsius",
            get_cmd= lambda: self._synth.temperature,
            docstring="Temperature in Celsius"
        )

        # Reference Frequency parameter
        ref_freq_range = self._synth.reference_frequency_range
        self.add_parameter(
            "reference_frequency",
            label="Reference Frequency",
            unit="Hz",
            get_cmd= lambda: self._synth.reference_frequency,
            set_cmd= lambda value: setattr(self._synth, 'reference_frequency', value),
            vals=Numbers(ref_freq_range['start'], ref_freq_range['stop']),
            docstring="Reference frequency in Hz"
        )

        # Sweep Enable parameter
        self.add_parameter(
            "sweep_enable",
            label="Sweep Enable",
            get_cmd= lambda: self._synth.sweep_enable,
            set_cmd= lambda value: setattr(self._synth, 'sweep_enable', value),
            val_mapping= qcodes.parameters.create_on_off_val_mapping(),
            vals=Enum(True, False),
            docstring="Sweep continuously enable"
        )

        # AM Enable parameter
        self.add_parameter(
            "am_enable",
            label="AM Enable",
            get_cmd= lambda: self._synth.am_enable,
            set_cmd= lambda value: setattr(self._synth, 'am_enable', value),
            val_mapping= qcodes.parameters.create_on_off_val_mapping(),
            vals=Enum(True, False),
            docstring="AM continuously enable"
        )

        # Pulse Modulation Enable parameter
        self.add_parameter(
            "pulse_mod_enable",
            label="Pulse Modulation Enable",
            get_cmd= lambda: self._synth.pulse_mod_enable,
            set_cmd= lambda value: setattr(self._synth, 'pulse_mod_enable', value),
            val_mapping= qcodes.parameters.create_on_off_val_mapping(),
            vals=Enum(True, False),
            docstring="Pulse modulation continuously enable"
        )

        # Dual Pulse Modulation Enable parameter
        self.add_parameter(
            "dual_pulse_mod_enable",
            label="Dual Pulse Modulation Enable",
            get_cmd= lambda: self._synth.dual_pulse_mod_enable,
            set_cmd= lambda value: setattr(self._synth, 'dual_pulse_mod_enable', value),
            val_mapping= qcodes.parameters.create_on_off_val_mapping(),
            vals=Enum(True, False),
            docstring="Dual pulse modulation enable"
        )

        # FM Enable parameter
        self.add_parameter(
            "fm_enable",
            label="FM Enable",
            get_cmd= lambda: self._synth.fm_enable,
            set_cmd= lambda value: setattr(self._synth, 'fm_enable', value),
            val_mapping= qcodes.parameters.create_on_off_val_mapping(),
            vals=Enum(True, False),
            docstring="FM continuously enable"
        )

        # Initialize the device
        self._synth.init()

    def get_idn(self):
        model = self._synth.model
        model_type = self._synth.model_type
        serial_number = self._synth.serial_number
        firmware_version = self._synth.firmware_version
        hardware_version = self._synth.hardware_version

        return f"Windfreak SynthHD, model {model}, type {model_type}, sn {serial_number}, firmware {firmware_version}, hardware {hardware_version}."


    def close(self):
        self._synth.close()
        super().close()
