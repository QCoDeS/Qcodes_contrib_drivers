from collections.abc import Generator
from unittest.mock import MagicMock, call, patch

import pytest
from pyvisa.errors import VisaIOError
from pyvisa.resources import MessageBasedResource

from qcodes_contrib_drivers.drivers.StanfordResearchSystems.SIM900 import SIM900
from qcodes_contrib_drivers.drivers.StanfordResearchSystems.SIM960 import SIM960


@pytest.fixture
def visa_handle() -> Generator[MagicMock, None, None]:
    handle = MagicMock(spec=MessageBasedResource)
    handle.visalib = MagicMock()
    handle.query.return_value = "Stanford Research Systems,SIM900,s/n123,ver3.6"
    with patch.object(SIM900, "_open_resource", return_value=handle):
        yield handle


@pytest.fixture
def sim900(visa_handle: MagicMock) -> Generator[SIM900, None, None]:
    instrument = SIM900("sim900", "GPIB::1::INSTR", query_delay=0)
    try:
        yield instrument
    finally:
        instrument.close()


@pytest.fixture
def sim960(sim900: SIM900) -> SIM960:
    module = SIM960(sim900, "pid", 1)
    sim900.add_submodule("pid", module)
    return module


def test_initialization(sim960: SIM960, visa_handle: MagicMock) -> None:
    assert visa_handle.read_termination == "\n"
    assert visa_handle.write_termination == "\n"
    assert visa_handle.timeout == 4000
    assert visa_handle.write.call_args_list == [
        call("FLSH"),
        call('SNDT 1,"TOKN OFF"'),
        call('SNDT 1,"TERM CRLF"'),
    ]
    assert sim960.parent.IDN()["model"] == "SIM900"
    assert "pid" in sim960.parent.snapshot(update=False)["submodules"]


def test_fragmented_module_response(sim960: SIM960, visa_handle: MagicMock) -> None:
    visa_handle.query.side_effect = ["0", "3", "0", "3", "1"]
    visa_handle.read_bytes.side_effect = [b"1.2", b"34\r", b"\n"]
    visa_handle.reset_mock()
    assert sim960.measure_monitor() == 1.234
    assert visa_handle.write.call_args_list == [
        call("FLSI 1"),
        call('SNDT 1,"MMON?"'),
        call("RAWN? 1,3"),
        call("RAWN? 1,3"),
        call("RAWN? 1,1"),
    ]


@pytest.mark.parametrize("partial", [b"", b"1.23"])
def test_module_timeout(
    sim900: SIM900, visa_handle: MagicMock, partial: bytes
) -> None:
    sim900.timeout(0)
    visa_handle.query.return_value = str(len(partial))
    visa_handle.read_bytes.return_value = partial
    with pytest.raises(TimeoutError, match="SIM900 port 1"):
        sim900.ask_port(1, "SMON?")


def test_io_error_propagates(sim900: SIM900, visa_handle: MagicMock) -> None:
    visa_handle.query.side_effect = VisaIOError(-1073807339)
    with pytest.raises(VisaIOError):
        sim900.ask_port(1, "SMON?")


def test_port_commands(sim900: SIM900, visa_handle: MagicMock) -> None:
    sim900.write_port(8, 'ECHO? "test"')
    visa_handle.write.assert_called_with('SNDT 8,"ECHO? ""test"""')
    visa_handle.reset_mock()
    for port in (0, 9):
        with pytest.raises(ValueError):
            SIM960(sim900, "invalid", port)
        with pytest.raises(ValueError):
            sim900.write_port(port, "*IDN?")
    for command in ("GAIN 1\n*RST", "GAIN 1\r"):
        with pytest.raises(ValueError, match="line terminators"):
            sim900.write_port(1, command)
    visa_handle.write.assert_not_called()


@pytest.mark.parametrize("count", [-1, 8])
def test_invalid_read_count(
    sim900: SIM900, visa_handle: MagicMock, count: int
) -> None:
    visa_handle.query.return_value = "7"
    visa_handle.reset_mock()
    with pytest.raises(ValueError):
        sim900.read_port(1, count)
    visa_handle.write.assert_not_called()


def test_scan_ports(sim900: SIM900, visa_handle: MagicMock) -> None:
    identity = b"Stanford Research Systems,SIM960,s/n456,ver2.0\r\n"
    visa_handle.query.side_effect = [str(len(identity)), str(len(identity))] + ["0"] * 7
    visa_handle.read_bytes.return_value = identity
    assert sim900.scan_ports() == [identity.decode().strip()] + [None] * 7


@pytest.mark.parametrize(
    "name,command,value,formatted",
    [
        ("gain", "GAIN", -2.5, "-2.5"),
        ("integral", "INTG", 0.015, "0.015"),
        ("derivative", "DERV", 0.000015, "1.5e-05"),
        ("offset", "OFST", 1.234, "1.234"),
        ("setpoint", "SETP", -1.234, "-1.234"),
        ("manual_output", "MOUT", 1.234, "1.234"),
        ("ramp_rate", "RATE", 0.0022, "0.0022"),
    ],
)
def test_numeric_parameters(
    sim960: SIM960, name: str, command: str, value: float, formatted: str
) -> None:
    with (
        patch.object(SIM900, "ask_port", return_value=str(value)) as ask,
        patch.object(SIM900, "write_port") as write,
    ):
        parameter = sim960.parameters[name]
        assert parameter() == value
        ask.assert_called_once_with(1, f"{command}?")
        parameter(value)
        write.assert_called_once_with(1, f"{command} {formatted}")


@pytest.mark.parametrize("value", [-1001, -0.01, 0, 0.01, 1001])
def test_invalid_gain(sim960: SIM960, visa_handle: MagicMock, value: float) -> None:
    visa_handle.reset_mock()
    with pytest.raises(ValueError):
        sim960.gain(value)
    visa_handle.write.assert_not_called()


@pytest.mark.parametrize(
    "name,command,values",
    [
        ("polarity", "APOL", ["negative", "positive"]),
        ("output_mode", "AMAN", ["manual", "pid"]),
        ("setpoint_source", "INPT", ["internal", "external"]),
        ("proportional_enable", "PCTL", [False, True]),
        ("integral_enable", "ICTL", [False, True]),
        ("derivative_enable", "DCTL", [False, True]),
        ("offset_enable", "OCTL", [False, True]),
        ("ramp_enable", "RAMP", [False, True]),
    ],
)
def test_mapped_parameters(
    sim960: SIM960, name: str, command: str, values: list[str] | list[bool]
) -> None:
    with (
        patch.object(SIM900, "ask_port") as ask,
        patch.object(SIM900, "write_port") as write,
    ):
        parameter = sim960.parameters[name]
        for raw, value in enumerate(values):
            ask.return_value = str(raw)
            assert parameter() == value
            ask.assert_called_with(1, f"{command}?")
            parameter(value)
            write.assert_called_with(1, f"{command} {raw}")


@pytest.mark.parametrize(
    "name,command,response,expected",
    [
        ("IDN", "*IDN?", "SRS,SIM960,123,2.0", "SRS,SIM960,123,2.0"),
        ("setpoint_monitor", "SMON?", "-0.123456", -0.123456),
        ("measure_monitor", "MMON?", "-0.123456", -0.123456),
        ("error_monitor", "EMON?", "-0.123456", -0.123456),
        ("output_monitor", "OMON?", "-0.123456", -0.123456),
        ("ramp_status", "RMPS?", "2", "ramping"),
    ],
)
def test_read_only_parameters(
    sim960: SIM960, name: str, command: str, response: str, expected: str | float
) -> None:
    with patch.object(SIM900, "ask_port", return_value=response) as ask:
        parameter = sim960.parameters[name]
        assert parameter() == expected
        assert not parameter.settable
        ask.assert_called_once_with(1, command)


@pytest.mark.parametrize(
    "name,other,value,command",
    [
        ("output_limit_lower", "ULIM?", 2, "LLIM"),
        ("output_limit_upper", "LLIM?", -2, "ULIM"),
    ],
)
def test_output_limit_ordering(
    sim960: SIM960, name: str, other: str, value: float, command: str
) -> None:
    with (
        patch.object(SIM900, "ask_port", return_value="0") as ask,
        patch.object(SIM900, "write_port") as write,
    ):
        with pytest.raises(ValueError, match="output limit"):
            sim960.parameters[name](value)
        ask.assert_called_once_with(1, other)
        write.assert_not_called()
        sim960.parameters[name](0)
        write.assert_called_once_with(1, f"{command} 0.00")


@pytest.mark.parametrize("enable", [False, True])
def test_start_ramping(sim960: SIM960, visa_handle: MagicMock, enable: bool) -> None:
    sim960.start_ramping(enable)
    visa_handle.write.assert_called_with(f'SNDT 1,"STRT {int(enable)}"')


def test_close_releases_resource(sim900: SIM900, visa_handle: MagicMock) -> None:
    sim900.close()
    visa_handle.close.assert_called_once()
