from typing import TYPE_CHECKING, Self

from qcodes.validators import Bool, MultiType, Numbers

from .SIM900 import SIM900, SIM900Module

if TYPE_CHECKING:
    from typing import Unpack

    from qcodes.instrument import InstrumentBaseKWArgs
    from qcodes.parameters import Parameter


class SIM960(SIM900Module):
    """
    Stanford Research Systems SIM960 analog PID controller in a SIM900 mainframe.

    The SIM960 is a double-width module. Use the port to which its connector is
    attached, not the adjacent slot covered by its panel.

    Construction sets numeric response tokens and CRLF response termination but
    does not change any PID settings or enable the output.

    Args:
        parent: SIM900 mainframe.
        name: Submodule name.
        port: Mainframe port to which the module is connected.
        **kwargs: Forwarded to :class:`.SIM900Module`.

    """

    def __init__(
        self,
        parent: SIM900,
        name: str,
        port: int,
        **kwargs: "Unpack[InstrumentBaseKWArgs]",
    ) -> None:
        super().__init__(parent, name, port, **kwargs)
        self.write("TOKN OFF")
        self.write("TERM CRLF")

        self.gain: Parameter[float, Self] = self.add_parameter(
            "gain",
            label="Proportional gain",
            unit="V/V",
            get_cmd="GAIN?",
            set_cmd="GAIN {:.2g}",
            get_parser=float,
            vals=MultiType(Numbers(-1000, -0.1), Numbers(0.1, 1000)),
        )
        """Signed proportional gain. Setting gain also changes polarity."""
        self.integral: Parameter[float, Self] = self.add_parameter(
            "integral",
            label="Integral gain",
            unit="1/s",
            get_cmd="INTG?",
            set_cmd="INTG {:.2g}",
            get_parser=float,
            vals=Numbers(0.01, 500000),
        )
        """Integral gain; does not enable integral action."""
        self.derivative: Parameter[float, Self] = self.add_parameter(
            "derivative",
            label="Derivative gain",
            unit="s",
            get_cmd="DERV?",
            set_cmd="DERV {:.2g}",
            get_parser=float,
            vals=Numbers(1e-6, 10),
        )
        """Derivative gain; does not enable derivative action."""
        self.offset: Parameter[float, Self] = self.add_parameter(
            "offset",
            label="Output offset",
            unit="V",
            get_cmd="OFST?",
            set_cmd="OFST {:.3f}",
            get_parser=float,
            vals=Numbers(-10, 10),
        )
        """Output offset, with millivolt resolution."""
        self.polarity: Parameter[str, Self] = self.add_parameter(
            "polarity",
            get_cmd="APOL?",
            set_cmd="APOL {}",
            val_mapping={"negative": 0, "positive": 1},
        )
        """Controller polarity. Setting polarity overrides the sign of gain."""
        self.proportional_enable: Parameter[bool, Self] = self.add_parameter(
            "proportional_enable",
            get_cmd="PCTL?",
            set_cmd="PCTL {}",
            val_mapping={False: 0, True: 1},
        )
        """Enable proportional action."""
        self.integral_enable: Parameter[bool, Self] = self.add_parameter(
            "integral_enable",
            get_cmd="ICTL?",
            set_cmd="ICTL {}",
            val_mapping={False: 0, True: 1},
        )
        """Enable integral action."""
        self.derivative_enable: Parameter[bool, Self] = self.add_parameter(
            "derivative_enable",
            get_cmd="DCTL?",
            set_cmd="DCTL {}",
            val_mapping={False: 0, True: 1},
        )
        """Enable derivative action."""
        self.offset_enable: Parameter[bool, Self] = self.add_parameter(
            "offset_enable",
            get_cmd="OCTL?",
            set_cmd="OCTL {}",
            val_mapping={False: 0, True: 1},
        )
        """Enable the output offset."""
        self.output_mode: Parameter[str, Self] = self.add_parameter(
            "output_mode",
            get_cmd="AMAN?",
            set_cmd="AMAN {}",
            val_mapping={"manual": 0, "pid": 1},
        )
        """Select manual output or PID control."""
        self.setpoint_source: Parameter[str, Self] = self.add_parameter(
            "setpoint_source",
            get_cmd="INPT?",
            set_cmd="INPT {}",
            val_mapping={"internal": 0, "external": 1},
        )
        """Select the internal setpoint or the front-panel Setpoint input."""
        self.setpoint: Parameter[float, Self] = self.add_parameter(
            "setpoint",
            unit="V",
            get_cmd="SETP?",
            set_cmd="SETP {:.3f}",
            get_parser=float,
            vals=Numbers(-10, 10),
        )
        """Internal setpoint, with millivolt resolution."""
        self.ramp_rate: Parameter[float, Self] = self.add_parameter(
            "ramp_rate",
            unit="V/s",
            get_cmd="RATE?",
            set_cmd="RATE {:.2g}",
            get_parser=float,
            vals=Numbers(1e-3, 1e4),
        )
        """Slew rate for internal setpoint ramps."""
        self.ramp_enable: Parameter[bool, Self] = self.add_parameter(
            "ramp_enable",
            get_cmd="RAMP?",
            set_cmd="RAMP {}",
            val_mapping={False: 0, True: 1},
        )
        """Enable constant-slew-rate internal setpoint changes."""
        self.ramp_status: Parameter[str, Self] = self.add_parameter(
            "ramp_status",
            get_cmd="RMPS?",
            set_cmd=False,
            val_mapping={"idle": 0, "pending": 1, "ramping": 2, "paused": 3},
        )
        """Current setpoint ramp state."""
        self.manual_output: Parameter[float, Self] = self.add_parameter(
            "manual_output",
            unit="V",
            get_cmd="MOUT?",
            set_cmd="MOUT {:.3f}",
            get_parser=float,
            vals=Numbers(-10, 10),
        )
        """Manual output voltage; does not change output mode."""
        self.output_limit_lower: Parameter[float, Self] = self.add_parameter(
            "output_limit_lower",
            unit="V",
            get_cmd="LLIM?",
            set_cmd=self._set_output_limit_lower,
            get_parser=float,
            vals=Numbers(-10, 10),
        )
        """Lower output limit, with 10 mV resolution, not above the upper limit."""
        self.output_limit_upper: Parameter[float, Self] = self.add_parameter(
            "output_limit_upper",
            unit="V",
            get_cmd="ULIM?",
            set_cmd=self._set_output_limit_upper,
            get_parser=float,
            vals=Numbers(-10, 10),
        )
        """Upper output limit, with 10 mV resolution, not below the lower limit."""
        self.display: Parameter[str, Self] = self.add_parameter(
            "display",
            get_cmd="DISP?",
            set_cmd="DISP {}",
            val_mapping={
                "gain": 0,
                "integral": 1,
                "derivative": 2,
                "offset": 3,
                "ramp_rate": 4,
                "setpoint": 5,
                "manual_output": 6,
                "output_limit_upper": 7,
                "output_limit_lower": 8,
                "setpoint_monitor": 9,
                "measure_monitor": 10,
                "error_monitor": 11,
                "output_monitor": 12,
            },
        )
        """Select the front-panel display field."""
        self.setpoint_monitor: Parameter[float, Self] = self.add_parameter(
            "setpoint_monitor",
            unit="V",
            get_cmd="SMON?",
            set_cmd=False,
            get_parser=float,
        )
        """Single measurement of the setpoint input to the error amplifier."""
        self.measure_monitor: Parameter[float, Self] = self.add_parameter(
            "measure_monitor",
            unit="V",
            get_cmd="MMON?",
            set_cmd=False,
            get_parser=float,
        )
        """Single measurement of the Measure input."""
        self.error_monitor: Parameter[float, Self] = self.add_parameter(
            "error_monitor",
            unit="V",
            get_cmd="EMON?",
            set_cmd=False,
            get_parser=float,
        )
        """Single measurement of the proportional-amplified error."""
        self.output_monitor: Parameter[float, Self] = self.add_parameter(
            "output_monitor",
            unit="V",
            get_cmd="OMON?",
            set_cmd=False,
            get_parser=float,
        )
        """Single measurement of the output voltage."""

    def _set_output_limit_lower(self, value: float) -> None:
        if value > self.output_limit_upper():
            raise ValueError("Lower output limit must not exceed upper output limit")
        self.write(f"LLIM {value:.2f}")

    def _set_output_limit_upper(self, value: float) -> None:
        if value < self.output_limit_lower():
            raise ValueError("Upper output limit must not be below lower output limit")
        self.write(f"ULIM {value:.2f}")

    def start_ramping(self, enable: bool) -> None:
        """
        Continue (True) or pause (False) an active setpoint ramp.

        A pending ramp can only be started using the front-panel Ramp Start/Stop
        button; this command cannot initiate it.
        """
        Bool().validate(enable, "enable")
        self.write(f"STRT {int(enable)}")
