"""QCoDeS driver for Santec TSL-570 Tunable Semiconductor Laser.

The driver uses the SCPI (Standard Commands for Programmable Instruments) command set,
which provides higher compatibility with other instruments and follows SCPI consortium standards.
"""

import logging
from typing import TYPE_CHECKING

from qcodes import validators as vals
from qcodes.instrument import VisaInstrumentKWArgs, IPInstrument
from qcodes.parameters import Parameter, create_on_off_val_mapping

if TYPE_CHECKING:
    from typing_extensions import Unpack

log = logging.getLogger(__name__)

# Physical constants
SPEED_OF_LIGHT = 299_792_458  # Speed of light in m/s


class SantecTSL570(IPInstrument):
    """
    QCoDeS driver for the Santec TSL-570 Tunable Semiconductor Laser.

    The driver automatically detects the model from the instrument's IDN response,
    applies appropriate wavelength limits, and sets the instrument to SCPI command mode
    during initialization.

    Args:
        name: Instrument name
        address: VISA resource address
        **kwargs: Additional arguments passed to VisaInstrument

    Supported models from TSL-570 datasheet:
    - 260360: 1260-1360 nm (O-band)
    - 240380: 1240-1380 nm (Extended O-band)
    - 355485: 1355-1485 nm (C-band standard)
    - 355505: 1355-1505 nm (C-band extended)
    - 500630: 1500-1630 nm (L-band standard)
    - 480640: 1480-1640 nm (Extended C/L-band)
    - 560680: 1560-1680 nm (L-band extended)

    Note:
        The instrument is automatically set to SCPI command mode during initialization.
        SCPI commands follow the Standard Commands for Programmable Instruments consortium standards.
    """

    MODEL_SPECS = {
        "260360": (1260e-9, 1360e-9),
        "240380": (1240e-9, 1380e-9),
        "355485": (1355e-9, 1485e-9),
        "355505": (1355e-9, 1505e-9),
        "500630": (1500e-9, 1630e-9),
        "480640": (1480e-9, 1640e-9),
        "560680": (1560e-9, 1680e-9),
    }

    default_terminator = "\n"

    def __init__(
            self,
            name: str,
            address: str,
            **kwargs: "Unpack[VisaInstrumentKWArgs]",
    ) -> None:
        kwargs.setdefault("write_confirmation", False)
        super().__init__(name, address, **kwargs)

        # Set instrument to SCPI command mode as first step
        self.write(":SYSTem:COMMunicate:CODe 1")
        log.info("Set instrument to SCPI command mode")

        # Detect model and set wavelength limit
        self.model = self.get_idn()['model']
        if self.model != "TSL-570":
            raise ValueError(f"Unexpected model '{self.model}' detected. Expected 'TSL-570'.")

        # if self.model in self.MODEL_SPECS:
        #     wavelength_min, wavelength_max = self.MODEL_SPECS[self.model]
        #     log.info(f"Detected model {self.model} with wavelength range {wavelength_min}-{wavelength_max} nm")
        # else:
        #     raise ValueError(f"Unknown model '{self.model}' detected.")
        #
        wavelength_min, wavelength_max = 1260e-9, 1680e-9

        frequency_min = SPEED_OF_LIGHT / wavelength_max
        frequency_max = SPEED_OF_LIGHT / wavelength_min

        # Wavelength parameters
        self.wavelength: Parameter = self.add_parameter(
            name="wavelength",
            label="Wavelength",
            unit="m",
            get_cmd=":WAVelength?",
            set_cmd=":WAVelength {:.10e}",
            get_parser=float,
            set_parser=float,
            vals=vals.Numbers(wavelength_min, wavelength_max),
        )
        """Output wavelength"""

        self.wavelength_unit: Parameter = self.add_parameter(
            name="wavelength_unit",
            label="Wavelength unit",
            get_cmd=":WAVelength:UNIT?",
            set_cmd=":WAVelength:UNIT {}",
            val_mapping={
                "NM": 0,
                "THz": 1,
            },
        )
        """Wavelength display unit (NM or THz)"""

        self.wavelength_fine: Parameter = self.add_parameter(
            name="wavelength_fine",
            label="Fine wavelength tuning",
            get_cmd=":WAV:FIN?",
            set_cmd=":WAV:FIN {:.2f}",
            get_parser=float,
            set_parser=float,
            vals=vals.Numbers(-100.0, 100.0),
        )
        """Fine-tuning offset"""

        self.frequency: Parameter = self.add_parameter(
            name="frequency",
            label="Optical frequency",
            unit="Hz",
            get_cmd=":WAVelength:FREQuency?",
            set_cmd=":WAVelength:FREQuency {:.0f}",
            get_parser=float,
            set_parser=float,
            vals=vals.Numbers(frequency_min, frequency_max),
        )
        """Output optical frequency"""

        # Coherence control
        self.coherence_control: Parameter = self.add_parameter(
            name="coherence_control",
            label="Coherence control",
            get_cmd=":COHCtrl?",
            set_cmd=":COHCtrl {}",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Coherence control enabled"""

        # Power parameters
        self.output: Parameter = self.add_parameter(
            name="output",
            label="Output state",
            get_cmd=":POWer:STATe?",
            set_cmd=":POWer:STATe {}",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Optical output enabled"""

        self.power_attenuation: Parameter = self.add_parameter(
            name="power_attenuation",
            label="Attenuator value",
            unit="dB",
            get_cmd=":POWer:ATTenuation?",
            set_cmd=":POWer:ATTenuation {:.2f}",
            get_parser=float,
            set_parser=float,
            vals=vals.Numbers(0, 30),
        )
        """Attenuator value (dB)"""

        self.power_auto: Parameter = self.add_parameter(
            name="power_auto",
            label="Automatic power control",
            get_cmd=":POWer:ATTenuation:AUTo?",
            set_cmd=":POWer:ATTenuation:AUTo {}",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Automatic power control enabled"""

        self.power: Parameter = self.add_parameter(
            name="power",
            label="Power",
            unit="mW",
            get_cmd=":POW?",
            set_cmd=":POW {:.10e}",
            get_parser=float,
            set_parser=float,
            vals=vals.Numbers(10 ** -1.5, 10 ** 1.3),
        )
        """Output power level (mW)"""

        self.power_actual: Parameter = self.add_parameter(
            name="power_actual",
            label="Actual optical power",
            unit="mW",
            get_cmd=":POWer:ACTual?",
            get_parser=float,
        )
        """Monitored optical power level (mW)"""

        self.shutter: Parameter = self.add_parameter(
            name="shutter",
            label="Shutter",
            get_cmd=":POWer:SHUTter?",
            set_cmd=":POWer:SHUTter {}",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Internal shutter open"""

        self.power_unit: Parameter = self.add_parameter(
            name="power_unit",
            label="Power unit",
            get_cmd=":POWer:UNIT?",
            set_cmd=":POWer:UNIT {}",
            val_mapping={
                "dBm": 0,
                "mW": 1,
            },
        )
        """Power display unit (dBm or mW)"""

        # Sweep parameters
        self.sweep_start_wavelength: Parameter = self.add_parameter(
            name="sweep_start_wavelength",
            label="Sweep start wavelength",
            unit="m",
            get_cmd=":WAVelength:SWEep:STARt?",
            set_cmd=":WAVelength:SWEep:STARt {:.10e}",
            get_parser=float,
            set_parser=float,
            vals=vals.Numbers(wavelength_min, wavelength_max),
        )
        """Sweep start wavelength"""

        self.sweep_stop_wavelength: Parameter = self.add_parameter(
            name="sweep_stop_wavelength",
            label="Sweep stop wavelength",
            unit="m",
            get_cmd=":WAVelength:SWEep:STOP?",
            set_cmd=":WAVelength:SWEep:STOP {:.10e}",
            get_parser=float,
            set_parser=float,
            vals=vals.Numbers(wavelength_min, wavelength_max),
        )
        """Sweep stop wavelength"""

        self.sweep_start_frequency: Parameter = self.add_parameter(
            name="sweep_start_frequency",
            label="Sweep start frequency",
            unit="Hz",
            get_cmd=":WAVelength:FREQuency:SWEep:STARt?",
            set_cmd=":WAVelength:FREQuency:SWEep:STARt {:.0f}",
            get_parser=float,
            set_parser=float,
            vals=vals.Numbers(frequency_min, frequency_max),
        )
        """Sweep start frequency"""

        self.sweep_stop_frequency: Parameter = self.add_parameter(
            name="sweep_stop_frequency",
            label="Sweep stop frequency",
            unit="Hz",
            get_cmd=":WAVelength:FREQuency:SWEep:STOP?",
            set_cmd=":WAVelength:FREQuency:SWEep:STOP {:.0f}",
            get_parser=float,
            set_parser=float,
            vals=vals.Numbers(frequency_min, frequency_max),
        )
        """Sweep stop frequency"""

        self.sweep_range_minimum: Parameter = self.add_parameter(
            name="sweep_range_minimum",
            label="Sweep range minimum wavelength",
            unit="m",
            get_cmd=":WAV:SWE:RANG:MAX?",
            get_parser=float,
        )
        """Minimum wavelength in configurable sweep range at current sweep speed"""

        self.sweep_range_maximum: Parameter = self.add_parameter(
            name="sweep_range_maximum",
            label="Sweep range maximum wavelength",
            unit="m",
            get_cmd=":WAV:SWE:RANG:MAX?",
            get_parser=float,
        )
        """Maximum wavelength in configurable sweep range at current sweep speed"""

        self.sweep_mode: Parameter = self.add_parameter(
            name="sweep_mode",
            label="Sweep mode",
            get_cmd=":WAVelength:SWEep:MODe?",
            set_cmd=":WAVelength:SWEep:MODe {}",
            get_parser=int,
            set_parser=int,
            vals=vals.Ints(0, 3),
        )
        """Sweep mode (0=step/one-way, 1=continuous/one-way, 2=step/two-way, 3=continuous/two-way)"""

        self.sweep_speed: Parameter = self.add_parameter(
            name="sweep_speed",
            label="Sweep speed",
            unit="nm/s",
            get_cmd=":WAVelength:SWEep:SPEed?",
            set_cmd=":WAVelength:SWEep:SPEed {:.4f}",
            get_parser=float,
            set_parser=float,
            vals=vals.Enum(1, 2, 5, 10, 20, 50, 100, 200),
        )
        """Sweep speed"""

        self.sweep_step: Parameter = self.add_parameter(
            name="sweep_step",
            label="Sweep step size",
            unit="m",
            get_cmd=":WAVelength:SWEep:STEP?",
            set_cmd=":WAVelength:SWEep:STEP {:.10e}",
            get_parser=float,
            set_parser=float,
            vals=vals.Numbers(0.1e-12, wavelength_max - wavelength_min),
        )
        """Sweep step size"""

        self.sweep_dwell: Parameter = self.add_parameter(
            name="sweep_dwell",
            label="Dwell time",
            unit="s",
            get_cmd=":WAVelength:SWEep:DWELl?",
            set_cmd=":WAVelength:SWEep:DWELl {:.1f}",
            get_parser=float,
            set_parser=float,
            vals=vals.Numbers(0, 999.9),
        )
        """Dwell time between steps"""

        self.sweep_cycles: Parameter = self.add_parameter(
            name="sweep_cycles",
            label="Sweep cycles",
            get_cmd=":WAVelength:SWEep:CYCLes?",
            set_cmd=":WAVelength:SWEep:CYCLes {:d}",
            get_parser=int,
            set_parser=int,
            vals=vals.Ints(0, 999),
        )
        """Number of sweep repetitions"""

        self.sweep_count: Parameter = self.add_parameter(
            name="sweep_count",
            label="Sweep cycle count",
            get_cmd=":WAVelength:SWEep:COUNt?",
            get_parser=int,
        )
        """Current number of completed sweeps"""

        self.sweep_delay: Parameter = self.add_parameter(
            name="sweep_delay",
            label="Sweep delay",
            unit="s",
            get_cmd=":WAVelength:SWEep:DELay?",
            set_cmd=":WAVelength:SWEep:DELay {:.1f}",
            get_parser=float,
            set_parser=float,
            vals=vals.Numbers(0, 999.9),
        )
        """Wait time between sweeps (seconds)"""

        self.sweep_state: Parameter = self.add_parameter(
            name="sweep_state",
            label="Sweep state",
            get_cmd=":WAVelength:SWEep:STATe?",
            get_parser=int,
            val_mapping={
                "STOPPED": 0,
                "RUNNING": 1,
                "TRIGGER_STANDBY": 3,
                "PREPARING": 4,
            },
        )
        """Sweep state (read-only): STOPPED (0), RUNNING (1), TRIGGER_STANDBY (3), PREPARING (4)"""

        # Data readout
        self.readout_points: Parameter = self.add_parameter(
            name="readout_points",
            label="Logged data points",
            get_cmd=":READout:POINts?",
            get_parser=int,
        )
        """Number of recorded data points"""

        # Modulation parameters
        self.modulation_state: Parameter = self.add_parameter(
            name="modulation_state",
            label="Amplitude modulation state",
            get_cmd=":AM:STATe?",
            set_cmd=":AM:STATe {}",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Amplitude modulation state"""

        self.modulation_source: Parameter = self.add_parameter(
            name="modulation_source",
            label="Amplitude modulation source",
            get_cmd=":AM:SOURce?",
            set_cmd=":AM:SOURce {}",
            get_parser=int,
            set_parser=int,
            val_mapping={
                "COHERENCE_CONTROL": 0,
                "INTENSITY_MODULATION": 1,
                "FREQUENCY_MODULATION": 3,
            },
        )
        """Modulation source (COHERENCE_CONTROL, INTENSITY_MODULATION, or FREQUENCY_MODULATION)"""

        self.wavelength_offset: Parameter = self.add_parameter(
            name="wavelength_offset",
            label="Wavelength offset",
            unit="m",
            get_cmd=":WAVelength:OFFSet?",
            set_cmd=":WAVelength:OFFSet {:.10e}",
            get_parser=float,
            set_parser=float,
            vals=vals.Numbers(-0.1e-9, 0.1e-9),
        )
        """Constant wavelength offset"""

        # Trigger parameters
        self.trigger_input_external: Parameter = self.add_parameter(
            name="trigger_input_external",
            label="External trigger input enabled",
            get_cmd=":TRIGger:INPut:EXTernal?",
            set_cmd=":TRIGger:INPut:EXTernal {}",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """External trigger input enabled"""

        self.trigger_input_polarity: Parameter = self.add_parameter(
            name="trigger_input_polarity",
            label="Trigger input polarity",
            get_cmd=":TRIGger:INPut:ACTive?",
            set_cmd=":TRIGger:INPut:ACTive {}",
            val_mapping={
                "RISE": 0,
                "FALL": 1,
            },
        )
        """Input trigger polarity: RISE (0=High Active/rising edge), FALL (1=Low Active/falling edge)"""

        self.trigger_input_standby: Parameter = self.add_parameter(
            name="trigger_input_standby",
            label="Trigger input standby",
            get_cmd=":TRIGger:INPut:STANdby?",
            set_cmd=":TRIGger:INPut:STANdby {}",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Trigger input standby enabled"""

        self.trigger_output_timing: Parameter = self.add_parameter(
            name="trigger_output_timing",
            label="Trigger output timing",
            get_cmd=":TRIGger:OUTPut?",
            set_cmd=":TRIGger:OUTPut {}",
            val_mapping={
                "NONE": 0,
                "STOP": 1,
                "START": 2,
                "STEP": 3,
            },
        )
        """Trigger output timing: NONE (0), STOP (1), START (2), STEP (3)"""

        self.trigger_output_polarity: Parameter = self.add_parameter(
            name="trigger_output_polarity",
            label="Trigger output polarity",
            get_cmd=":TRIGger:OUTPut:ACTive?",
            set_cmd=":TRIGger:OUTPut:ACTive {}",
            val_mapping={
                "RISE": 0,
                "FALL": 1,
            },
        )
        """Output trigger polarity: RISE (0=High Active/rising edge), FALL (1=Low Active/falling edge)"""

        self.trigger_output_step: Parameter = self.add_parameter(
            name="trigger_output_step",
            label="Trigger output interval",
            unit="m",
            get_cmd=":TRIGger:OUTPut:STEP?",
            set_cmd=":TRIGger:OUTPut:STEP {:.10e}",
            get_parser=float,
            set_parser=float,
            vals=vals.Numbers(0.0001e-9, wavelength_max - wavelength_min),
        )
        """Trigger output interval (0.0001 nm resolution)"""

        self.trigger_output_setting: Parameter = self.add_parameter(
            name="trigger_output_setting",
            label="Trigger output period mode",
            get_cmd=":TRIGger:OUTPut:SETTing?",
            set_cmd=":TRIGger:OUTPut:SETTing {}",
            val_mapping={
                "WAVELENGTH": 0,
                "TIME": 1,
            },
        )
        """Trigger output period mode: WAVELENGTH (0=periodic in wavelength), TIME (1=periodic in time)"""

        self.trigger_through: Parameter = self.add_parameter(
            name="trigger_through",
            label="Trigger through mode",
            get_cmd=":TRIGger:THRough?",
            set_cmd=":TRIGger:THRough {}",
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """Trigger through mode enabled"""

        # System parameters
        self.system_error: Parameter = self.add_parameter(
            name="system_error",
            label="Error queue",
            get_cmd=":SYSTem:ERRor?",
            get_parser=lambda s: dict(code=int(s.strip().split(",")[0]), message=s.strip().split(",")[1].strip('"'))
        )
        """Read and clear error from error queue (read-only, returns error number)"""

        self.command_set_param: Parameter = self.add_parameter(
            name="command_set_param",
            label="Command set",
            get_cmd=":SYSTem:COMMunicate:CODe?",
            get_parser=int,
            val_mapping={
                "LEGACY": 0,
                "SCPI": 1,
            },
        )
        """Instrument command set (read-only; always SCPI in this driver)"""

        self.system_lock: Parameter = self.add_parameter(
            name="system_lock",
            label="External interlock status",
            get_cmd=":SYSTem:LOCK?",
            get_parser=int,
            val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
        )
        """External interlock status (read-only): off (0=UNLOCKED), on (1=LOCKED)"""

        self.system_alert: Parameter = self.add_parameter(
            name="system_alert",
            label="Alert information",
            get_cmd=":SYSTem:ALERt?",
            get_parser=str,
        )
        """Read current alert information (read-only, returns alert number)"""

        self.system_version: Parameter = self.add_parameter(
            name="system_version",
            label="Firmware version",
            get_cmd=":SYSTem:VERSion?",
            get_parser=lambda s: s.strip(),
        )
        """Firmware version (read-only, format: ####.####.####)"""

        self.system_code: Parameter = self.add_parameter(
            name="system_code",
            label="Product code",
            get_cmd=":SYSTem:CODe?",
            get_parser=lambda s: s.strip(),
        )
        """Product code (read-only, format: *-******-*-*-**-**-*)"""

        self.connect_message()

    def reset(self) -> None:
        """Reset to factory defaults."""
        self.write("*RST")

    def disable_fine_tuning(self) -> None:
        """Terminate fine-tuning operation."""
        self.write(":WAVelength:FINetuning:DISable")

    def sweep_repeat(self) -> None:
        """Start repeat sweep."""
        self.write(":WAVelength:SWEep:STATe:REPeat")

    def sweep_single(self) -> None:
        self.write(":WAV:SWE 1")

    def sweep_stop(self) -> None:
        """Stop current sweep."""
        self.write(":WAV:SWE 0")

    def software_trigger(self) -> None:
        """Execute from trigger standby."""
        self.write(":TRIGger:INPut:SOFTtrigger")
