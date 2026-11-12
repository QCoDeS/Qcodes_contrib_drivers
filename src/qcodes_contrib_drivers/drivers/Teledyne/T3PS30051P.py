from time import sleep
from typing import TYPE_CHECKING, Self

from qcodes.instrument import VisaInstrument, VisaInstrumentKWArgs
from qcodes.validators import Numbers

if TYPE_CHECKING:
    from typing import Unpack

    from qcodes.parameters import Parameter


class TeledyneT3PS30051P(VisaInstrument):
    """
    Teledyne LeCroy T3PS30051P single-channel, 30 V / 5 A DC power supply.

    Construction does not reset the supply or change its output. Closing the
    connection does not turn the output off. Identification uses the known
    vendor and model without sending the unsupported ``*IDN?`` query; serial
    number and firmware are unavailable. Writes wait 100 ms after transmission
    before returning so subsequent commands do not arrive too soon. Queries wait
    one second before reading the response.

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

        self.voltage: Parameter[float, Self] = self.add_parameter(
            "voltage",
            label="Voltage setpoint",
            unit="V",
            get_cmd="VOLT?",
            set_cmd="VOLT {}",
            get_parser=float,
            vals=Numbers(0, 30),
        )
        """Programmed output voltage, from 0 to 30 V."""
        self.current: Parameter[float, Self] = self.add_parameter(
            "current",
            label="Current limit",
            unit="A",
            get_cmd="CURR?",
            set_cmd="CURR {}",
            get_parser=float,
            vals=Numbers(0, 5),
        )
        """Programmed current limit, from 0 to 5 A."""
        self.status: Parameter[int, Self] = self.add_parameter(
            "status",
            get_cmd="SYST:STAT?",
            set_cmd=False,
            get_parser=lambda response: int(response, 0),
        )
        """
        System status register: bit 0 selects CC/CV, bit 4 is output enabled,
        bit 5 is four-wire sense, bit 6 is timer enabled, and bit 8 is waveform
        display enabled.
        """
        # Note: Output On/Off command format is "OUTP CH1,ON" or "OUTP CH1,OFF"
        #  This was tested on a unit running:
        #  - Software Version: 2.1.1.8
        #  - Hardware Version: V1.0
        # Note other software versions may be slightly different
        self.output: Parameter[bool, Self] = self.add_parameter(
            "output",
            label="Output enabled",
            get_cmd=self._get_output,
            set_cmd="OUTP CH1,{}",
            val_mapping={False: "OFF", True: "ON"},
        )
        """Enable the output; readback is obtained from status bit 4."""
        self.mode: Parameter[str, Self] = self.add_parameter(
            "mode",
            label="Regulation mode",
            get_cmd=lambda: "CC" if self.status() & 1 else "CV",
            set_cmd=False,
        )
        """Present constant-current (CC) or constant-voltage (CV) mode."""
        self.measured_voltage: Parameter[float, Self] = self.add_parameter(
            "measured_voltage",
            unit="V",
            get_cmd="MEAS:VOLT? CH1",
            set_cmd=False,
            get_parser=float,
        )
        """Measured output voltage."""
        self.measured_current: Parameter[float, Self] = self.add_parameter(
            "measured_current",
            unit="A",
            get_cmd="MEAS:CURR? CH1",
            set_cmd=False,
            get_parser=float,
        )
        """Measured output current."""
        self.measured_power: Parameter[float, Self] = self.add_parameter(
            "measured_power",
            unit="W",
            get_cmd="MEAS:POWE? CH1",
            set_cmd=False,
            get_parser=float,
        )
        """Measured output power."""

        self.connect_message()

    def write_raw(self, cmd: str) -> None:
        """Send a command and allow the supply 100 ms to process it."""
        super().write_raw(cmd)
        sleep(0.1)

    def get_idn(self) -> dict[str, str | None]:
        """Return model metadata without querying the instrument."""
        return {
            "vendor": "Teledyne LeCroy",
            "model": "T3PS30051P",
            "serial": None,
            "firmware": None,
        }

    def _get_output(self) -> str:
        return "ON" if self.status() & (1 << 4) else "OFF"
