from typing import TYPE_CHECKING
from unittest.mock import MagicMock, call

import pytest
from pyvisa.errors import VisaIOError
from pyvisa.resources import MessageBasedResource

from qcodes.instrument import VisaInstrument
from qcodes.parameters import Parameter

from qcodes_contrib_drivers.drivers.Teledyne import (
    TeledyneT3PS3000,
    TeledyneT3PS3000Channel,
    TeledyneT3PS30051P,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from pytest_mock import MockerFixture


@pytest.fixture
def visa_handle(mocker: "MockerFixture") -> MagicMock:
    handle = MagicMock(spec=MessageBasedResource)
    handle.visalib = MagicMock()
    mocker.patch.object(VisaInstrument, "_open_resource", return_value=handle)
    return handle


@pytest.fixture
def single_supply(
    visa_handle: MagicMock,
) -> "Generator[TeledyneT3PS30051P, None, None]":
    visa_handle.query.side_effect = AssertionError("Unexpected initialization query")
    supply = TeledyneT3PS30051P("single_supply", "USB::1::INSTR")
    visa_handle.query.side_effect = None
    try:
        yield supply
    finally:
        supply.close()


@pytest.fixture
def multi_supply(
    visa_handle: MagicMock,
) -> "Generator[TeledyneT3PS3000, None, None]":
    visa_handle.query.return_value = "Teledyne LeCroy,T3PS3000,456,1.0"
    supply = TeledyneT3PS3000("multi_supply", "TCPIP::192.0.2.1::5025::SOCKET")
    try:
        yield supply
    finally:
        supply.close()


def test_single_initialization(
    single_supply: TeledyneT3PS30051P, visa_handle: MagicMock
) -> None:
    assert single_supply.IDN() == {
        "vendor": "Teledyne LeCroy",
        "model": "T3PS30051P",
        "serial": None,
        "firmware": None,
    }
    assert visa_handle.read_termination == "\n"
    assert visa_handle.write_termination == "\n"
    assert visa_handle.query_delay == 1.0
    visa_handle.query.assert_not_called()
    visa_handle.write.assert_not_called()


def test_single_snapshot_without_idn_query(
    single_supply: TeledyneT3PS30051P, visa_handle: MagicMock
) -> None:
    visa_handle.query.return_value = "0"

    snapshot = single_supply.snapshot(update="All")

    assert snapshot["parameters"]["IDN"]["value"] == single_supply.IDN()
    assert call("*IDN?") not in visa_handle.query.call_args_list
    assert visa_handle.query.called


def test_single_write_pacing(
    single_supply: TeledyneT3PS30051P,
    visa_handle: MagicMock,
    mocker: "MockerFixture",
) -> None:
    elapsed = 0.0
    ready_at = 0.0

    def wait(seconds: float) -> None:
        nonlocal elapsed
        elapsed += seconds

    def write(command: str) -> None:
        nonlocal ready_at
        assert elapsed >= ready_at, "Command sent before the supply was ready"
        ready_at = elapsed + 0.1

    def query(command: str) -> str:
        assert elapsed >= ready_at, "Query sent before the write had settled"
        return "10"

    mocker.patch(
        "qcodes_contrib_drivers.drivers.Teledyne.T3PS30051P.sleep",
        side_effect=wait,
    )
    visa_handle.write.side_effect = write
    visa_handle.query.side_effect = query

    single_supply.output(False)
    single_supply.voltage(10.0)
    single_supply.current(0.4)
    assert single_supply.voltage() == 10.0
    assert visa_handle.write.call_args_list == [
        call("OUTP CH1,OFF"),
        call("VOLT 10.0"),
        call("CURR 0.4"),
    ]


def test_multi_initialization(
    multi_supply: TeledyneT3PS3000, visa_handle: MagicMock
) -> None:
    assert multi_supply.IDN()["model"] == "T3PS3000"
    assert visa_handle.read_termination == "\n"
    assert visa_handle.write_termination == "\n"
    assert tuple(multi_supply.channels) == (multi_supply.ch1, multi_supply.ch2)
    assert multi_supply.ch1.parent is multi_supply
    assert multi_supply.ch3.parent is multi_supply
    assert {"ch1", "ch2", "ch3"} <= multi_supply.snapshot(update="Never")[
        "submodules"
    ].keys()
    visa_handle.write.assert_not_called()


@pytest.mark.parametrize(
    "name,command,value,unit",
    [("voltage", "VOLT", 10.25, "V"), ("current", "CURR", 0.4, "A")],
)
def test_single_setpoints(
    single_supply: TeledyneT3PS30051P,
    visa_handle: MagicMock,
    name: str,
    command: str,
    value: float,
    unit: str,
) -> None:
    parameter = single_supply.parameters[name]
    assert isinstance(parameter, Parameter)
    assert parameter.unit == unit
    parameter(value)
    visa_handle.write.assert_called_once_with(f"{command} {value}")
    visa_handle.query.return_value = f"{value}\n"
    assert parameter() == value
    visa_handle.query.assert_called_with(f"{command}?")


@pytest.mark.parametrize("channel", [1, 2])
@pytest.mark.parametrize(
    "name,command,value",
    [("voltage", "VOLT", 5.25), ("current", "CURR", 0.2)],
)
def test_channel_setpoints(
    multi_supply: TeledyneT3PS3000,
    visa_handle: MagicMock,
    channel: int,
    name: str,
    command: str,
    value: float,
) -> None:
    parameter = multi_supply.channels[channel - 1].parameters[name]
    parameter(value)
    visa_handle.write.assert_called_once_with(f"CH{channel}:{command} {value}")
    visa_handle.query.return_value = str(value)
    assert parameter() == value
    visa_handle.query.assert_called_with(f"CH{channel}:{command}?")


@pytest.mark.parametrize("name,maximum", [("voltage", 30), ("current", 5)])
def test_single_limits(
    single_supply: TeledyneT3PS30051P,
    visa_handle: MagicMock,
    name: str,
    maximum: float,
) -> None:
    parameter = single_supply.parameters[name]
    parameter(0)
    parameter(maximum)
    visa_handle.reset_mock()
    for invalid in (-0.001, maximum + 0.001, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            parameter(invalid)
    visa_handle.write.assert_not_called()


@pytest.mark.parametrize("channel", [1, 2])
@pytest.mark.parametrize("name,maximum", [("voltage", 32), ("current", 3.2)])
def test_channel_limits(
    multi_supply: TeledyneT3PS3000,
    visa_handle: MagicMock,
    channel: int,
    name: str,
    maximum: float,
) -> None:
    parameter = multi_supply.channels[channel - 1].parameters[name]
    parameter(0)
    parameter(maximum)
    visa_handle.reset_mock()
    for invalid in (-0.001, maximum + 0.001, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            parameter(invalid)
    visa_handle.write.assert_not_called()


@pytest.mark.parametrize("status", ["0x0", "0x1", "0x10", "0x11", "256"])
def test_single_status(
    single_supply: TeledyneT3PS30051P, visa_handle: MagicMock, status: str
) -> None:
    visa_handle.query.return_value = status
    raw = int(status, 0)
    assert single_supply.status() == raw
    assert single_supply.output() is bool(raw & 16)
    assert single_supply.mode() == ("CC" if raw & 1 else "CV")
    visa_handle.query.assert_called_with("SYST:STAT?")


@pytest.mark.parametrize("enabled", [False, True])
def test_single_output(
    single_supply: TeledyneT3PS30051P, visa_handle: MagicMock, enabled: bool
) -> None:
    single_supply.output(enabled)
    state = "ON" if enabled else "OFF"
    visa_handle.write.assert_called_once_with(f"OUTP CH1,{state}")


@pytest.mark.parametrize("channel", [1, 2])
@pytest.mark.parametrize("bit", range(10))
def test_channel_status_bits(
    multi_supply: TeledyneT3PS3000,
    visa_handle: MagicMock,
    channel: int,
    bit: int,
) -> None:
    visa_handle.query.return_value = hex(1 << bit)
    output = multi_supply.channels[channel - 1]
    assert output.output() is (bit == channel + 3)
    assert output.timer_enabled() is (bit == channel + 5)
    assert output.waveform_enabled() is (bit == channel + 7)
    assert output.mode() == ("CC" if bit == channel - 1 else "CV")


@pytest.mark.parametrize("channel", [1, 2])
@pytest.mark.parametrize(
    "name,command",
    [("output", "OUTP"), ("timer_enabled", "TIME"), ("waveform_enabled", "OUTP:WAVE")],
)
@pytest.mark.parametrize("enabled", [False, True])
def test_channel_switches(
    multi_supply: TeledyneT3PS3000,
    visa_handle: MagicMock,
    channel: int,
    name: str,
    command: str,
    enabled: bool,
) -> None:
    visa_handle.query.return_value = "0x4"
    multi_supply.channels[channel - 1].parameters[name](enabled)
    state = "ON" if enabled else "OFF"
    visa_handle.write.assert_called_once_with(f"{command} CH{channel},{state}")


def test_fixed_channel_write_only(
    multi_supply: TeledyneT3PS3000, visa_handle: MagicMock
) -> None:
    assert not multi_supply.ch3.output.gettable
    assert "voltage" not in multi_supply.ch3.parameters
    assert "current" not in multi_supply.ch3.parameters
    multi_supply.ch3.output(True)
    multi_supply.ch3.output(False)
    assert visa_handle.write.call_args_list == [
        call("OUTP CH3,ON"),
        call("OUTP CH3,OFF"),
    ]
    visa_handle.reset_mock()
    multi_supply.ch3.snapshot(update="All")
    visa_handle.query.assert_not_called()


@pytest.mark.parametrize(
    "name,command",
    [
        ("measured_voltage", "MEAS:VOLT?"),
        ("measured_current", "MEAS:CURR?"),
        ("measured_power", "MEAS:POWE?"),
    ],
)
def test_single_measurements(
    single_supply: TeledyneT3PS30051P,
    visa_handle: MagicMock,
    name: str,
    command: str,
) -> None:
    visa_handle.query.return_value = "1.234"
    parameter = single_supply.parameters[name]
    assert not parameter.settable
    assert parameter() == 1.234
    visa_handle.query.assert_called_with(f"{command} CH1")


@pytest.mark.parametrize("channel", [1, 2])
@pytest.mark.parametrize(
    "name,command",
    [
        ("measured_voltage", "MEAS:VOLT?"),
        ("measured_current", "MEAS:CURR?"),
        ("measured_power", "MEAS:POWE?"),
    ],
)
def test_channel_measurements(
    multi_supply: TeledyneT3PS3000,
    visa_handle: MagicMock,
    channel: int,
    name: str,
    command: str,
) -> None:
    visa_handle.query.return_value = "1.234"
    parameter = multi_supply.channels[channel - 1].parameters[name]
    assert not parameter.settable
    assert parameter() == 1.234
    visa_handle.query.assert_called_with(f"{command} CH{channel}")


@pytest.mark.parametrize(
    "mode,status,value",
    [("independent", "0x4", 0), ("series", "0xc", 1), ("parallel", "0x8", 2)],
)
def test_operation_mode(
    multi_supply: TeledyneT3PS3000,
    visa_handle: MagicMock,
    mode: str,
    status: str,
    value: int,
) -> None:
    visa_handle.query.return_value = status
    assert multi_supply.operation_mode() == mode
    multi_supply.operation_mode(mode)
    visa_handle.write.assert_called_once_with(f"OUTP:TRACK {value}")


def test_unknown_operation_mode(
    multi_supply: TeledyneT3PS3000, visa_handle: MagicMock
) -> None:
    visa_handle.query.return_value = "0x0"
    with pytest.raises(ValueError, match="Unknown T3PS3000"):
        multi_supply.operation_mode()
    with pytest.raises(ValueError):
        multi_supply.operation_mode("invalid")
    visa_handle.write.assert_not_called()


@pytest.mark.parametrize("status", ["0x8", "0xc"])
def test_timer_requires_independent_mode(
    multi_supply: TeledyneT3PS3000, visa_handle: MagicMock, status: str
) -> None:
    visa_handle.query.return_value = status
    with pytest.raises(ValueError, match="independent"):
        multi_supply.ch1.timer_enabled(True)
    visa_handle.write.assert_not_called()
    multi_supply.ch1.timer_enabled(False)
    visa_handle.write.assert_called_once_with("TIME CH1,OFF")


@pytest.mark.parametrize("channel", [1, 2])
@pytest.mark.parametrize("group", [1, 5])
def test_timer_steps(
    multi_supply: TeledyneT3PS3000,
    visa_handle: MagicMock,
    channel: int,
    group: int,
) -> None:
    output = multi_supply.channels[channel - 1]
    output.set_timer(group, 32, 3.2, 10000)
    visa_handle.write.assert_called_once_with(
        f"TIME:SET CH{channel},{group},32,3.2,10000"
    )
    visa_handle.query.return_value = "32,3.2,10000\n"
    assert output.get_timer(group) == (32.0, 3.2, 10000.0)
    visa_handle.query.assert_called_with(f"TIME:SET? CH{channel},{group}")
    output.set_timer(group, 0, 0, 0)
    visa_handle.write.assert_called_with(f"TIME:SET CH{channel},{group},0,0,0")


@pytest.mark.parametrize(
    "group,voltage,current,duration",
    [
        (0, 1, 1, 1),
        (6, 1, 1, 1),
        (1.5, 1, 1, 1),
        (1, -1, 1, 1),
        (1, 32.001, 1, 1),
        (1, 1, -1, 1),
        (1, 1, 3.201, 1),
        (1, 1, 1, -1),
        (1, 1, 1, 10001),
        (1, 1, 1, float("nan")),
    ],
)
def test_invalid_timer_steps(
    multi_supply: TeledyneT3PS3000,
    visa_handle: MagicMock,
    group: int,
    voltage: float,
    current: float,
    duration: float,
) -> None:
    with pytest.raises((ValueError, TypeError)):
        multi_supply.ch1.set_timer(group, voltage, current, duration)
    visa_handle.write.assert_not_called()


@pytest.mark.parametrize("group", [0, 6, 1.5])
def test_invalid_timer_query(
    multi_supply: TeledyneT3PS3000, visa_handle: MagicMock, group: int
) -> None:
    visa_handle.reset_mock()
    with pytest.raises((ValueError, TypeError)):
        multi_supply.ch1.get_timer(group)
    visa_handle.query.assert_not_called()


@pytest.mark.parametrize("response", ["1,2", "1,2,3,4", "1,x,3"])
def test_malformed_timer_response(
    multi_supply: TeledyneT3PS3000, visa_handle: MagicMock, response: str
) -> None:
    visa_handle.query.return_value = response
    with pytest.raises(ValueError):
        multi_supply.ch1.get_timer(1)


@pytest.mark.parametrize(
    "response,enabled",
    [("DHCP:ON", True), ("DHCP:OFF", False), ("ON\n", True), ("off", False)],
)
def test_dhcp(
    multi_supply: TeledyneT3PS3000,
    visa_handle: MagicMock,
    response: str,
    enabled: bool,
) -> None:
    visa_handle.query.return_value = response
    assert multi_supply.dhcp() is enabled
    multi_supply.dhcp(enabled)
    state = "ON" if enabled else "OFF"
    visa_handle.write.assert_called_once_with(f"DHCP {state}")


@pytest.mark.parametrize(
    "name,command,address",
    [
        ("ip_address", "IPaddr", "192.0.2.10"),
        ("subnet_mask", "MASKaddr", "255.255.255.0"),
        ("gateway", "GATEaddr", "192.0.2.1"),
    ],
)
def test_network_settings(
    multi_supply: TeledyneT3PS3000,
    visa_handle: MagicMock,
    name: str,
    command: str,
    address: str,
) -> None:
    parameter = multi_supply.parameters[name]
    visa_handle.query.return_value = address + "\n"
    assert parameter() == address
    visa_handle.query.assert_called_with(f"{command}?")
    visa_handle.query.return_value = "DHCP:OFF"
    parameter(address)
    visa_handle.write.assert_called_once_with(f"{command} {address}")
    visa_handle.reset_mock()
    visa_handle.query.return_value = "DHCP:ON"
    with pytest.raises(ValueError, match="Disable DHCP"):
        parameter(address)
    visa_handle.write.assert_not_called()


@pytest.mark.parametrize("name", ["ip_address", "subnet_mask", "gateway"])
@pytest.mark.parametrize("address", ["256.0.0.1", "::1", "192.0.2.1\n*RST"])
def test_invalid_network_address(
    multi_supply: TeledyneT3PS3000,
    visa_handle: MagicMock,
    name: str,
    address: str,
) -> None:
    with pytest.raises(ValueError):
        multi_supply.parameters[name](address)
    visa_handle.write.assert_not_called()


def test_selected_channel(
    multi_supply: TeledyneT3PS3000, visa_handle: MagicMock
) -> None:
    multi_supply.selected_channel("CH2")
    visa_handle.write.assert_called_once_with("INST CH2")
    visa_handle.query.return_value = "CH2\n"
    assert multi_supply.selected_channel() == "CH2"
    visa_handle.query.assert_called_with("INST?")
    with pytest.raises(ValueError):
        multi_supply.selected_channel("CH3")


@pytest.mark.parametrize("channel", [0, 3])
def test_invalid_channel(multi_supply: TeledyneT3PS3000, channel: int) -> None:
    with pytest.raises(ValueError):
        TeledyneT3PS3000Channel(multi_supply, "invalid", channel)


def test_io_error_propagates(
    multi_supply: TeledyneT3PS3000, visa_handle: MagicMock
) -> None:
    visa_handle.query.side_effect = VisaIOError(-1073807339)
    with pytest.raises(VisaIOError):
        multi_supply.ch1.voltage()


def test_close(multi_supply: TeledyneT3PS3000, visa_handle: MagicMock) -> None:
    multi_supply.close()
    visa_handle.close.assert_called_once()
