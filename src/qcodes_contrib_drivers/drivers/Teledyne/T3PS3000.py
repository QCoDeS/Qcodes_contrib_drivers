from functools import partial
from ipaddress import IPv4Address
from time import sleep
from typing import TYPE_CHECKING, Self

from qcodes.instrument import (
    ChannelTuple,
    InstrumentChannel,
    VisaInstrument,
    VisaInstrumentKWArgs,
)
from qcodes.validators import Enum, Ints, Numbers, Strings

if TYPE_CHECKING:
    from typing import Unpack

    from qcodes.instrument import InstrumentBaseKWArgs
    from qcodes.parameters import Parameter


class TeledyneT3PS3000Channel(InstrumentChannel["TeledyneT3PS3000"]):
    """
    An adjustable T3PS3000 output (CH1 or CH2), rated at 32 V / 3.2 A.

    Setpoints and limits apply to an individual channel, including when tracking
    is enabled. Timer operation is supported only in independent mode.

    Args:
        parent: T3PS3000 supply.
        name: Channel name.
        channel: Channel number, 1 or 2.
        **kwargs: Forwarded to :class:`qcodes.instrument.InstrumentChannel`.

    """

    def __init__(
        self,
        parent: "TeledyneT3PS3000",
        name: str,
        channel: int,
        **kwargs: "Unpack[InstrumentBaseKWArgs]",
    ) -> None:
        Ints(1, 2).validate(channel, "channel")
        super().__init__(parent, name, **kwargs)
        self.channel = channel
        prefix = f"CH{channel}"

        self.voltage: Parameter[float, Self] = self.add_parameter(
            "voltage",
            label="Voltage setpoint",
            unit="V",
            get_cmd=f"{prefix}:VOLT?",
            set_cmd=f"{prefix}:VOLT {{}}",
            get_parser=float,
            vals=Numbers(0, 32),
        )
        """Programmed channel voltage, from 0 to 32 V."""
        self.current: Parameter[float, Self] = self.add_parameter(
            "current",
            label="Current limit",
            unit="A",
            get_cmd=f"{prefix}:CURR?",
            set_cmd=f"{prefix}:CURR {{}}",
            get_parser=float,
            vals=Numbers(0, 3.2),
        )
        """Programmed channel current limit, from 0 to 3.2 A."""
        self.output: Parameter[bool, Self] = self.add_parameter(
            "output",
            label="Output enabled",
            get_cmd=partial(self._get_status_state, channel + 3),
            set_cmd=f"OUTP {prefix},{{}}",
            val_mapping={False: "OFF", True: "ON"},
        )
        """Enable the channel output."""
        self.mode: Parameter[str, Self] = self.add_parameter(
            "mode",
            label="Regulation mode",
            get_cmd=lambda: (
                "CC" if self.parent.status() & (1 << (channel - 1)) else "CV"
            ),
            set_cmd=False,
        )
        """Present constant-current (CC) or constant-voltage (CV) mode."""
        self.measured_voltage: Parameter[float, Self] = self.add_parameter(
            "measured_voltage",
            unit="V",
            get_cmd=f"MEAS:VOLT? {prefix}",
            set_cmd=False,
            get_parser=float,
        )
        """Measured channel voltage."""
        self.measured_current: Parameter[float, Self] = self.add_parameter(
            "measured_current",
            unit="A",
            get_cmd=f"MEAS:CURR? {prefix}",
            set_cmd=False,
            get_parser=float,
        )
        """Measured channel current."""
        self.measured_power: Parameter[float, Self] = self.add_parameter(
            "measured_power",
            unit="W",
            get_cmd=f"MEAS:POWE? {prefix}",
            set_cmd=False,
            get_parser=float,
        )
        """Measured channel power."""
        self.timer_enabled: Parameter[bool, Self] = self.add_parameter(
            "timer_enabled",
            get_cmd=partial(self._get_status_state, channel + 5),
            set_cmd=self._set_timer_enabled,
            val_mapping={False: "OFF", True: "ON"},
        )
        """Enable the five-step timer sequence in independent mode."""
        self.waveform_enabled: Parameter[bool, Self] = self.add_parameter(
            "waveform_enabled",
            get_cmd=partial(self._get_status_state, channel + 7),
            set_cmd=f"OUTP:WAVE {prefix},{{}}",
            val_mapping={False: "OFF", True: "ON"},
        )
        """Select the channel's waveform display instead of the digital display."""

    def _get_status_state(self, bit: int) -> str:
        return "ON" if self.parent.status() & (1 << bit) else "OFF"

    def _set_timer_enabled(self, state: str) -> None:
        if state == "ON" and self.parent.operation_mode() != "independent":
            raise ValueError("Timers require independent operation mode")
        self.write(f"TIME CH{self.channel},{state}")

    def set_timer(
        self, group: int, voltage: float, current: float, time_sec: float
    ) -> None:
        """
        Set one timer step without starting the timer.

        Args:
            group: Step number from 1 through 5.
            voltage: Voltage in volts, from 0 through 32.
            current: Current limit in amperes, from 0 through 3.2.
            time_sec: Duration in seconds, from 0 through 10000.

        """
        Ints(1, 5).validate(group, "timer group")
        self.voltage.validate(voltage)
        self.current.validate(current)
        Numbers(0, 10000).validate(time_sec, "timer duration")
        self.write(f"TIME:SET CH{self.channel},{group},{voltage},{current},{time_sec}")

    def get_timer(self, group: int) -> tuple[float, float, float]:
        """Return a timer step's (voltage, current limit, duration) in V, A, s."""
        Ints(1, 5).validate(group, "timer group")
        response = self.ask(f"TIME:SET? CH{self.channel},{group}")
        values = response.strip().split(",")
        if len(values) != 3:
            raise ValueError(f"Expected three timer values, received {response!r}")
        voltage, current, duration = map(float, values)
        return voltage, current, duration


class TeledyneT3PS3000FixedChannel(InstrumentChannel["TeledyneT3PS3000"]):
    """
    T3PS3000 CH3, with front-panel selection of 2.5, 3.3, or 5 V.

    Only output switching is supported remotely. Output readback is unavailable
    in the status register, so ``output`` is explicitly write-only.

    Args:
        parent: T3PS3000 supply.
        name: Channel name.
        **kwargs: Forwarded to :class:`qcodes.instrument.InstrumentChannel`.

    """

    def __init__(
        self,
        parent: "TeledyneT3PS3000",
        name: str,
        **kwargs: "Unpack[InstrumentBaseKWArgs]",
    ) -> None:
        super().__init__(parent, name, **kwargs)
        self.output: Parameter[bool, Self] = self.add_parameter(
            "output",
            label="Output enabled",
            get_cmd=False,
            set_cmd="OUTP CH3,{}",
            val_mapping={False: "OFF", True: "ON"},
        )
        """Switch CH3 output; its physical state cannot be queried."""


class TeledyneT3PS3000(VisaInstrument):
    """
    Teledyne LeCroy T3PS3000 three-channel DC power supply.

    CH1 and CH2 support independent, series, and parallel operation. CH3 has
    front-panel voltage selection and write-only remote output control.
    Construction and closing the connection do not change output settings.
    Writes wait 100 ms after transmission before returning so subsequent
    commands do not arrive too soon.
    Queries wait one second before reading, including the initial identification
    query, to allow the supply time to prepare its response.

    Args:
        name: Instrument name.
        address: VISA resource address (USB or LAN).
        **kwargs: Forwarded to :class:`qcodes.instrument.VisaInstrument`.

    """

    default_terminator = "\n"

    def __init__(
        self, name: str, address: str, **kwargs: "Unpack[VisaInstrumentKWArgs]"
    ) -> None:
        super().__init__(name, address, **kwargs)
        self.visa_handle.query_delay = 1.0
        self.status: Parameter[int, Self] = self.add_parameter(
            "status",
            get_cmd="SYST:STAT?",
            set_cmd=False,
            get_parser=lambda response: int(response, 0),
        )
        """System status register, returned as an integer."""
        self.operation_mode: Parameter[str, Self] = self.add_parameter(
            "operation_mode",
            get_cmd=self._get_operation_mode,
            set_cmd="OUTP:TRACK {}",
            val_mapping={"independent": 0, "series": 1, "parallel": 2},
        )
        """CH1/CH2 tracking mode. Changing it can change the physical outputs."""
        self.selected_channel: Parameter[str, Self] = self.add_parameter(
            "selected_channel",
            get_cmd="INST?",
            set_cmd="INST {}",
            get_parser=str.strip,
            vals=Enum("CH1", "CH2"),
        )
        """Front-panel selected channel; channel parameters use explicit addressing."""
        self.dhcp: Parameter[bool, Self] = self.add_parameter(
            "dhcp",
            get_cmd="DHCP?",
            set_cmd="DHCP {}",
            get_parser=lambda response: (
                response.strip().upper().removeprefix("DHCP:").strip()
            ),
            val_mapping={False: "OFF", True: "ON"},
        )
        """Enable DHCP. Changing network settings can disconnect a LAN session."""
        self.ip_address: Parameter[str, Self] = self.add_parameter(
            "ip_address",
            get_cmd="IPaddr?",
            set_cmd=partial(self._set_network_address, "IPaddr"),
            get_parser=str.strip,
            vals=Strings(),
        )
        """IPv4 address. Setting it requires DHCP to be disabled."""
        self.subnet_mask: Parameter[str, Self] = self.add_parameter(
            "subnet_mask",
            get_cmd="MASKaddr?",
            set_cmd=partial(self._set_network_address, "MASKaddr"),
            get_parser=str.strip,
            vals=Strings(),
        )
        """IPv4 subnet mask. Setting it requires DHCP to be disabled."""
        self.gateway: Parameter[str, Self] = self.add_parameter(
            "gateway",
            get_cmd="GATEaddr?",
            set_cmd=partial(self._set_network_address, "GATEaddr"),
            get_parser=str.strip,
            vals=Strings(),
        )
        """IPv4 gateway. Setting it requires DHCP to be disabled."""

        self.ch1 = self.add_submodule("ch1", TeledyneT3PS3000Channel(self, "ch1", 1))
        self.ch2 = self.add_submodule("ch2", TeledyneT3PS3000Channel(self, "ch2", 2))
        self.ch3 = self.add_submodule("ch3", TeledyneT3PS3000FixedChannel(self, "ch3"))
        self.channels = self.add_submodule(
            "channels",
            ChannelTuple(
                self,
                "channels",
                TeledyneT3PS3000Channel,
                [self.ch1, self.ch2],
                snapshotable=False,
            ),
        )
        """The two programmable channels; CH3 is exposed separately."""

        self.connect_message()

    def write_raw(self, cmd: str) -> None:
        """Send a command and allow the supply 100 ms to process it."""
        super().write_raw(cmd)
        sleep(0.1)

    def _get_operation_mode(self) -> int:
        bits = (self.status() >> 2) & 3
        # Status encodings differ from the OUTP:TRACK command values.
        modes = {1: 0, 3: 1, 2: 2}
        if bits not in modes:
            raise ValueError(f"Unknown T3PS3000 tracking status bits: {bits:02b}")
        return modes[bits]

    def _set_network_address(self, command: str, value: str) -> None:
        address = str(IPv4Address(value))
        if self.dhcp():
            raise ValueError("Disable DHCP before setting a static network address")
        self.write(f"{command} {address}")
