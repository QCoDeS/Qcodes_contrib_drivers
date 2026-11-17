import time
from typing import TYPE_CHECKING, Self

from qcodes.instrument import InstrumentChannel, VisaInstrument, VisaInstrumentKWArgs
from qcodes.validators import Ints, Numbers

if TYPE_CHECKING:
    from typing import Unpack

    from qcodes.instrument import InstrumentBaseKWArgs
    from qcodes.parameters import Parameter


class SIM900(VisaInstrument):
    """
    Stanford Research Systems SIM900 mainframe.

    Modules communicate through the mainframe using packet-mode commands, without
    switching the host connection into transparent mode. The driver expects
    newline-terminated module responses and exclusive use of the port buffers.
    Module streaming must be stopped before issuing queries.

    Args:
        name: Instrument name.
        address: VISA resource address.
        query_delay: Seconds between polls of a module's input buffer.
        **kwargs: Forwarded to :class:`qcodes.instrument.VisaInstrument`. For a
            serial connection, configure the VISA handle's baud rate to match
            the mainframe if it differs from the power-on default of 9600 baud.

    """

    default_terminator = "\n"
    default_timeout = 4

    def __init__(
        self,
        name: str,
        address: str,
        query_delay: float = 0.3,
        **kwargs: "Unpack[VisaInstrumentKWArgs]",
    ) -> None:
        Numbers(0).validate(query_delay, "query_delay")
        self.query_delay = query_delay
        super().__init__(name, address, **kwargs)
        self.write("FLSH")
        self.connect_message()

    def write_port(self, port: int, cmd: str) -> None:
        """Send a command to a module in port 1 through 8."""
        Ints(1, 8).validate(port, "port")
        if "\r" in cmd or "\n" in cmd:
            raise ValueError("Module commands must not contain line terminators")
        # SIM900 quoted strings escape a quote by doubling it.
        message = cmd.replace('"', '""')
        self.write(f'SNDT {port},"{message}"')

    def in_waiting(self, port: int) -> int:
        """Return the number of bytes waiting in a module's input buffer."""
        Ints(1, 8).validate(port, "port")
        return int(self.ask(f"NINP? {port}"))

    def read_port(self, port: int, nbytes: int | None = None) -> str:
        """
        Read bytes already available from a module, without stripping terminators.

        If omitted, ``nbytes`` is obtained from the input buffer count. An empty
        buffer returns an empty string. An explicit count must not exceed the
        available bytes: the mainframe rejects such RAWN queries.
        """
        Ints(1, 8).validate(port, "port")
        available = self.in_waiting(port)
        if nbytes is None:
            nbytes = available
        Ints(0, 4096).validate(nbytes, "nbytes")
        if nbytes > available:
            raise ValueError(
                f"Port {port} has {available} bytes available, not {nbytes}"
            )
        if nbytes == 0:
            return ""
        self.write(f"RAWN? {port},{nbytes}")
        # RAWN adds no framing. Read exactly the requested bytes, including CR/LF.
        response = self.visa_handle.read_bytes(nbytes).decode("ascii")
        self.visa_log.debug("Read from port %s: %s", port, response)
        return response

    def ask_port(self, port: int, cmd: str) -> str:
        """
        Flush stale input, send a query and read a complete module response.

        Uses the mainframe's ``timeout`` (seconds) while waiting for the module.
        A timeout raises :class:`TimeoutError`, including any partial response.
        """
        self.flush(port)
        self.write_port(port, cmd)
        return self._read_response(port)

    def _read_response(self, port: int) -> str:
        timeout = self.timeout()
        start = time.monotonic()
        response = ""
        while True:
            response += self.read_port(port)
            if response.endswith("\n"):
                return response.strip()
            if timeout is not None and time.monotonic() - start >= timeout:
                raise TimeoutError(
                    f"Timed out waiting for SIM900 port {port}: {response!r}"
                )
            time.sleep(self.query_delay)

    def flush(self, port: int | None = None) -> None:
        """Flush input buffers for one port, or all ports if omitted."""
        if port is None:
            self.write("FLSI")
        else:
            Ints(1, 8).validate(port, "port")
            self.write(f"FLSI {port}")

    def scan_ports(self) -> list[str | None]:
        """
        Return ID strings for ports 1 through 8, or None for unresponsive ports.

        Each module is given ``query_delay`` seconds to start responding. Input
        buffers are flushed before scanning; do not scan during streaming.
        """
        identities: list[str | None] = []
        for port in range(1, 9):
            self.flush(port)
            self.write_port(port, "*IDN?")
            time.sleep(self.query_delay)
            if self.in_waiting(port):
                identities.append(self._read_response(port))
            else:
                identities.append(None)
        return identities


class SIM900Module(InstrumentChannel[SIM900]):
    """
    Base class for a module connected to a SIM900 port.

    Register the instance with ``parent.add_submodule(name, module)`` to include
    its parameters in station snapshots.

    Args:
        parent: SIM900 mainframe.
        name: Submodule name.
        port: Mainframe port number, from 1 through 8.
        **kwargs: Forwarded to :class:`qcodes.instrument.InstrumentChannel`.

    """

    def __init__(
        self,
        parent: SIM900,
        name: str,
        port: int,
        **kwargs: "Unpack[InstrumentBaseKWArgs]",
    ) -> None:
        Ints(1, 8).validate(port, "port")
        super().__init__(parent, name, **kwargs)
        self.port = port
        self.IDN: Parameter[str, Self] = self.add_parameter(
            "IDN", get_cmd="*IDN?", set_cmd=False
        )
        """The module identification string, not the mainframe identity."""

    def write(self, cmd: str) -> None:
        """Write to this module's port."""
        self.parent.write_port(self.port, cmd)

    def ask(self, cmd: str) -> str:
        """Query this module's port."""
        return self.parent.ask_port(self.port, cmd)
