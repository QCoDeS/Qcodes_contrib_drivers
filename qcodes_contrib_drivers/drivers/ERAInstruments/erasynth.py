"""Driver for the ERASynth/ERASynth+/ERASynth++ signal generators.

Author: Victor Negîrneac, vnegirneac@qblox.com

For official instrument support visit:

- https://erainstruments.com
- https://github.com/erainstruments/

This module provides the following drivers:

- :class:`qcodes_contrib_drivers.drivers.ERAInstruments.ERASynth <qcodes_contrib_drivers.drivers.ERAInstruments.erasynth.ERASynth>`,
- :class:`qcodes_contrib_drivers.drivers.ERAInstruments.ERASynthPlus <qcodes_contrib_drivers.drivers.ERAInstruments.erasynth.ERASynthPlus>`, and
- :class:`qcodes_contrib_drivers.drivers.ERAInstruments.ERASynthPlusPlus <qcodes_contrib_drivers.drivers.ERAInstruments.erasynth.ERASynthPlusPlus>`.
"""
from __future__ import annotations

from typing import Dict, List, Union, Tuple, Optional
import time
import json
import logging

from qcodes import VisaInstrument, Parameter, validators

try:
    import pyvisa
except ModuleNotFoundError as e:
    raise ModuleNotFoundError(
        "ERAInstrument drivers require the `pyvisa` package to be installed.\n"
        "Install it with `pip install pyvisa` and try again."
    ) from e

logger = logging.getLogger(__name__)

BAUDRATE = 115200

_CMD_TO_JSON_MAPPING: Dict[str, str] = {
    # We will treat these differently when confirming the value
    # because the instrument replies with a sentence containing the value.
    # which is much faster than reading the full JSON
    # as fast as possible
    # "P0": "rfoutput",
    # "A": "amplitude",
    # "F": "frequency",
    "P1": "reference_int_ext",
    "P5": "reference_tcxo_ocxo",
    "MS": "modulation_on_off",
    "M2": "modulation_signal_waveform",
    "M1": "modulation_source",
    "M0": "modulation_type",
    "M3": "modulation_freq",
    "M5": "modulation_am_depth",
    "M4": "modulation_fm_deviation",
    "M6": "modulation_pulse_period",
    "M7": "modulation_pulse_width",
    "SS": "sweep_start_stop",
    "S0": "sweep_trigger",
    "S1": "sweep_start",
    "S2": "sweep_stop",
    "S3": "sweep_step",
    "S4": "sweep_dwell",
    "P9": "phase_noise_mode",
    "PEW": "wifi_mode",
    "PES0": "wifi_sta_ssid",
    "PEP0": "wifi_sta_password",
    "PES1": "wifi_ap_ssid",
    "PEP1": "wifi_ap_password",
    "PEI": "wifi_ip_address",
    "PEN": "wifi_subnet_address",
    "PEG": "wifi_gateway_address",
}
"""
A mapping used to read back certain commands to ensure they have been set.
This is necessary due to non-deterministic communication times.
"""

class ERASynthBase(VisaInstrument):
    r"""
    A Base class for the ERASynth/ERASynth+/ERASynth++ instruments.

    Example:

    .. code-block::

        from qcodes import Instrument
        from qcodes_contrib_drivers.drivers.ERAInstruments import ERASynthPlus

        # list communication ports
        ERASynthPlus.print_pyvisa_resources()

        # Instantiate the instrument
        lo = ERASynthPlus("ERASynthPlus", 'ASRL/dev/cu.usbmodem14101::INSTR')

        lo.off()  # Turn off the output

        # print updated snapshot once to make sure the snapshot will be up-to-date
        # takes a few seconds
        lo.print_readable_snapshot(update=True)

        # Configure the local oscillator
        lo.ref_osc_source("int")  # Use internal reference
        lo.frequency(4.7e9)
        lo.power(10)  # Set the amplitude to 10 dBm
        lo.on()  # Turn on the output


    .. seealso::

        The raw serial commands can be found here:
        https://github.com/erainstruments/erasynth-docs/blob/master/erasynth-command-list.pdf

        ``self.visa_handle`` can be used to interact directly with the serial pyvisa
        communication.
    """

    @staticmethod
    def print_pyvisa_resources() -> None:
        """Utility to list all."""
        resource_manager = pyvisa.ResourceManager()
        print(resource_manager.list_resources())

    def _prep_communication(self):
        """Makes sure the instrument config is compatible with this driver."""
        self.debug_messages_en(False)  # Print less messages to improve communication
        self.wifi_off()  # print less messages to improve communication

    def __init__(self, name: str, address: str, **kwargs):
        """
        Create an instance of the instrument.

        Args:
            name: Instrument name.
            address: Used to connect to the instrument.
                Run :meth:`.ERASynthBase.print_pyvisa_resources` to list available list.
        """
        super().__init__(name=name, address=address, terminator="\r\n", **kwargs)

        # ##############################################################################
        # Standard LO parameters
        # ##############################################################################

        # NB `initial_value` is not used because that would make the initialization slow

        self.status = Parameter(
            name="status",
            instrument=self,
            val_mapping={False: "0", True: "1"},
            get_cmd="RA:rfoutput",
            set_cmd=self._set_status,
        )
        """Sets the output state (`True`/`False`)."""

        self.power = Parameter(
            name="power",
            instrument=self,
            label="Power",
            unit="dBm",
            vals=validators.Numbers(min_value=-60.0, max_value=20.0),
            get_cmd="RA:amplitude",
            get_parser=float,
            set_parser=lambda power: f"{power:.2f}",
            set_cmd=self._set_power,
        )
        """Signal power in dBm of the ERASynth signal, 'amplitude' in EraSynth docs."""

        self.ref_osc_source = Parameter(
            name="ref_osc_source",
            instrument=self,
            val_mapping={"int": "0", "ext": "1"},
            get_cmd=f"RA:{_CMD_TO_JSON_MAPPING['P1']}",
            set_cmd="P1{}",
        )
        """
        Set to external if a 10 MHz reference is connected to the REF input connector.
        """

        # ##############################################################################
        # ERASynth specific parameters
        # ##############################################################################

        self.temperature = Parameter(
            name="temperature",
            instrument=self,
            label="Temperature",
            unit="\u00B0C",
            get_cmd="RD:temperature",
        )
        """Temperature of the device."""

        self.voltage = Parameter(
            name="voltage",
            instrument=self,
            label="Voltage",
            unit="V",
            get_cmd="RD:voltage",
        )
        """The input voltage value from power input of the ERASynth."""

        self.current = Parameter(
            name="current",
            instrument=self,
            label="Current",
            unit="V",
            get_cmd="RD:current",
        )
        """The current value drawn by the ERASynth."""

        self.embedded_version = Parameter(
            name="embedded_version",
            instrument=self,
            label="Embedded version",
            get_cmd="RD:em",
        )
        """The firmware version of the ERASynth."""

        self.wifi_rssi = Parameter(
            name="wifi_rssi",
            instrument=self,
            label="WiFi RSSI",
            get_cmd="RD:rssi",
        )
        """The Wifi received signal power."""

        self.pll_lmx1_status = Parameter(
            name="pll_lmx1_status",
            instrument=self,
            label="PLL LMX1 status",
            val_mapping={"locked": "1", "unlocked": "0"},
            get_cmd="RD:lock_lmx1",
        )
        """PLL lock status of LMX1."""

        self.pll_lmx2_status = Parameter(
            name="pll_lmx2_status",
            instrument=self,
            label="PLL LMX2 status",
            val_mapping={"locked": "1", "unlocked": "0"},
            get_cmd="RD:lock_lmx2",
        )
        """PLL lock status of LMX2."""

        self.pll_xtal_status = Parameter(
            name="pll_xtal_status",
            instrument=self,
            label="PLL XTAL status",
            val_mapping={"locked": "1", "unlocked": "0"},
            get_cmd="RD:lock_xtal",
        )
        """PLL lock status of XTAL."""

        self.modulation_en = Parameter(
            name="modulation_en",
            instrument=self,
            val_mapping={False: "0", True: "1"},
            get_cmd=f"RA:{_CMD_TO_JSON_MAPPING['MS']}",
            set_cmd="MS{}",
        )
        """Modulation on/off."""

        self.modulation_signal_waveform = Parameter(
            name="modulation_signal_waveform",
            instrument=self,
            val_mapping={"sine": "0", "triangle": "1", "ramp": "2", "square": "3"},
            get_cmd=f"RA:{_CMD_TO_JSON_MAPPING['M2']}",
            set_cmd="M2{}",
        )
        """Internal modulation waveform."""

        self.modulation_source = Parameter(
            name="modulation_source",
            instrument=self,
            val_mapping={"internal": "0", "external": "1", "microphone": "2"},
            get_cmd=f"RA:{_CMD_TO_JSON_MAPPING['M1']}",
            set_cmd="M1{}",
        )
        """Modulation source."""

        self.modulation_type = Parameter(
            name="modulation_type",
            instrument=self,
            val_mapping={
                "narrowband_fm": "0",
                "wideband_fm": "1",
                "am": "2",
                "pulse": "3",
            },
            get_cmd=f"RA:{_CMD_TO_JSON_MAPPING['M0']}",
            set_cmd="M0{}",
        )
        """Modulation type."""

        self.modulation_freq = Parameter(
            name="modulation_freq",
            instrument=self,
            label="Modulation frequency",
            unit="Hz",
            vals=validators.Numbers(min_value=0, max_value=20e9),
            get_cmd=f"RA:{_CMD_TO_JSON_MAPPING['M3']}",
            get_parser=int,
            set_cmd="M3{}",
            set_parser=lambda freq: str(int(freq)),
        )
        """Internal modulation frequency in Hz."""

        self.modulation_am_depth = Parameter(
            name="modulation_am_depth",
            instrument=self,
            label="AM depth",
            unit="%",
            vals=validators.Numbers(min_value=0, max_value=100),
            get_cmd=f"RA:{_CMD_TO_JSON_MAPPING['M5']}",
            get_parser=int,
            set_cmd="M5{}",
            set_parser=lambda depth: str(int(depth)),
        )
        """AM modulation depth."""

        self.modulation_fm_deviation = Parameter(
            name="modulation_fm_deviation",
            instrument=self,
            label="FM deviation",
            unit="Hz",
            vals=validators.Numbers(min_value=0, max_value=20e9),
            get_cmd=f"RA:{_CMD_TO_JSON_MAPPING['M4']}",
            get_parser=int,
            set_cmd="M4{}",
            set_parser=lambda freq: str(int(freq)),
        )
        """FM modulation deviation."""

        self.modulation_pulse_period = Parameter(
            name="modulation_pulse_period",
            instrument=self,
            label="Pulse period",
            unit="s",
            vals=validators.Numbers(min_value=1e-6, max_value=10),
            get_cmd=f"RA:{_CMD_TO_JSON_MAPPING['M6']}",
            get_parser=lambda val: int(val) * 1e-6,
            set_cmd="M6{}",
            set_parser=lambda period: str(int(period * 1e6)),
        )
        """Pulse period in seconds."""

        self.modulation_pulse_width = Parameter(
            name="modulation_pulse_width",
            instrument=self,
            label="Pulse width",
            unit="s",
            vals=validators.Numbers(min_value=1e-6, max_value=10),
            get_cmd=f"RA:{_CMD_TO_JSON_MAPPING['M7']}",
            get_parser=lambda val: int(val) * 1e-6,
            set_cmd="M7{}",
            set_parser=lambda period: str(int(period * 1e6)),
        )
        """Pulse width in s."""

        self.sweep_en = Parameter(
            name="sweep_en",
            instrument=self,
            val_mapping={False: "0", True: "1"},
            get_cmd=f"RA:{_CMD_TO_JSON_MAPPING['SS']}",
            set_cmd="SS{}",
        )
        """Sweep on/off."""

        self.sweep_trigger = Parameter(
            name="sweep_trigger",
            instrument=self,
            val_mapping={"freerun": "0", "external": "1"},
            get_cmd=f"RA:{_CMD_TO_JSON_MAPPING['S0']}",
            set_cmd="S0{}",
        )
        """Sweep trigger freerun/external."""

        self.sweep_dwell = Parameter(
            name="sweep_dwell",
            instrument=self,
            label="Sweep dwell",
            unit="s",
            vals=validators.Numbers(min_value=1e-3, max_value=10),
            get_cmd=f"RA:{_CMD_TO_JSON_MAPPING['S4']}",
            get_parser=lambda val: int(val) * 1e-3,
            set_cmd="S4{}",
            set_parser=lambda period: str(int(period * 1e3)),
        )
        """Sweep dwell time in s. Requires sweep_trigger('freerun')."""

        self.synthesizer_mode = Parameter(
            name="synthesizer_mode",
            instrument=self,
            val_mapping={"low_spurious": "0", "low_phase_noise": "1"},
            get_cmd=f"RA:{_CMD_TO_JSON_MAPPING['P9']}",
            set_cmd="P9{}",
        )
        """Synthesizer mode, low spurious/low phase noise."""

        # WiFi control, NB initial_cache_value is used to avoid overriding these values

        self.wifi_mode = Parameter(
            name="wifi_mode",
            instrument=self,
            val_mapping={"station": "0", "hotspot": "1", "": ""},
            get_cmd=f"RA:{_CMD_TO_JSON_MAPPING['PEW']}",
            set_cmd="PEW{}",
        )
        """WiFi Mode, station/hotspot."""

        self.wifi_station_ssid = Parameter(
            name="wifi_station_ssid",
            instrument=self,
            vals=validators.Strings(),
            get_cmd=f"RA:{_CMD_TO_JSON_MAPPING['PES0']}",
            set_cmd="PES0{}",
        )
        """Sets network SSID for WiFi module."""

        self.wifi_station_password = Parameter(
            name="wifi_station_password",
            instrument=self,
            vals=validators.Strings(),
            get_cmd=f"RA:{_CMD_TO_JSON_MAPPING['PEP0']}",
            set_cmd="PEP0{}",
        )
        """Sets network password for WiFi module."""

        self.wifi_hotspot_ssid = Parameter(
            name="wifi_hotspot_ssid",
            instrument=self,
            vals=validators.Strings(),
            get_cmd=f"RA:{_CMD_TO_JSON_MAPPING['PES1']}",
            set_cmd="PES1{}",
        )
        """Sets hotspot SSID for WiFi module."""

        self.wifi_hotspot_password = Parameter(
            name="wifi_hotspot_password",
            instrument=self,
            vals=validators.Strings(),
            get_cmd=f"RA:{_CMD_TO_JSON_MAPPING['PEP1']}",
            set_cmd="PEP1{}",
        )
        """Sets hotspot password for WiFi module."""

        self.wifi_ip_address = Parameter(
            name="wifi_ip_address",
            instrument=self,
            vals=validators.Strings(),
            get_cmd=f"RA:{_CMD_TO_JSON_MAPPING['PEI']}",
            set_cmd="PEI{}",
        )
        """Sets IP address for WiFi module."""

        self.wifi_subnet_address = Parameter(
            name="wifi_subnet_address",
            instrument=self,
            vals=validators.Strings(),
            get_cmd=f"RA:{_CMD_TO_JSON_MAPPING['PEN']}",
            set_cmd="PEN{}",
        )
        """Sets Subnet mask for WiFi module."""

        self.wifi_gateway_address = Parameter(
            name="wifi_gateway_address",
            instrument=self,
            vals=validators.Strings(),
            get_cmd=f"RA:{_CMD_TO_JSON_MAPPING['PEG']}",
            set_cmd="PEG{}",
        )
        """Sets default gateway for WiFi module."""

        self.debug_messages_en = Parameter(
            name="debug_messages_en",
            instrument=self,
            vals=validators.Strings(),
            initial_cache_value=None,
            val_mapping={True: "1", False: "0"},
            set_cmd="PD{}",
        )
        """Enables/disables debug printing on the serial port."""

        setattr(self.visa_handle, "baud_rate", BAUDRATE)
        self.timeout(10)  # generous timeout to avoid disrupting measurements
        self.connect_message()
        self._prep_communication()

    # ##################################################################################
    # Public methods
    # ##################################################################################

    # Standard LO methods

    def on(self) -> None:
        """
        Turns ON the RF output.
        """
        self.status(True)

    def off(self) -> None:
        """
        Turns OFF the RF output.
        """
        self.status(False)

    # Custom communication

    def get_idn(self) -> Dict[str, Optional[str]]:
        models = {"0": "ERASynth", "1": "ERASynth+", "2": "ERASynth++"}
        d_status = self.get_diagnostic_status()
        assert isinstance(d_status, Dict)
        return {
            "vendor": "ERA Instruments",
            "model": models[d_status["model"]],
            "serial": d_status["serial_number"],
            "firmware": d_status["em"],
        }

    def clear_read_buffer(self) -> None:
        """
        Clears the read buffer. The instrument often sends information we do not care
        about in this driver. This function discards the entire read buffer by reading
        it.
        """
        bytes_in_buffer = lambda: getattr(self.visa_handle, "bytes_in_buffer")
        while bytes_in_buffer():
            self.visa_handle.read_bytes(bytes_in_buffer())

    def ask(self, cmd: str) -> str:
        """Writes a command to the communication channel of the instrument and return
        the response.

        Commands are prefixed with `">"` as required by the ERASynth.

        NB the read buffer is discarded before and after reading one line.
        """
        self.clear_read_buffer()
        response = super().ask(f">{cmd}")
        self.clear_read_buffer()

        return response

    def ask_raw(self, cmd: str) -> str:
        """
        Detects special commands for which the `get_configuration` will be used.

        This makes it convenient to not implement individual getters for most commands.
        """
        if cmd[1:].startswith("RA:"):
            response = self.get_configuration(cmd[1 + len("RA:") :])
        elif cmd[1:].startswith("RD:"):
            response = self.get_diagnostic_status(cmd[1 + len("RD:") :])
        else:
            response = super().ask_raw(cmd)
        assert isinstance(response, str)
        return response

    def write(self, cmd: str) -> None:
        """Writes a command to the communication channel of the instrument.

        Commands are prefixed with `">"` as required by the ERASynth.

        NB the read buffer is discarded before and after reading one line.
        """
        self.clear_read_buffer()
        super().write(f">{cmd}")
        self.clear_read_buffer()

    def write_raw(self, cmd: str) -> None:
        """
        For some commands we confirm that the value has been set correctly.

        This is only possible for configurations that can be retrieved from the
        instrument.
        """
        is_readable_cmd = False
        for command in _CMD_TO_JSON_MAPPING:
            if cmd[1:].startswith(command):
                is_readable_cmd = True
                break

        if is_readable_cmd:
            json_key = _CMD_TO_JSON_MAPPING[command]
            cmd_arg = cmd[1 + len(command) :]
            while True:
                super().write_raw(cmd)
                self.clear_read_buffer()
                if self.get_configuration(json_key) == cmd_arg:
                    break
        else:
            super().write_raw(cmd)

    def _get_json(self, cmd: str, first_key: str) -> str:
        """
        Sends command and reads result until the result looks like a JSON.
        """
        timeout = 10
        t_start = time.time()
        first_key = '{"' + first_key + '"'
        while True:
            read_line = self.ask(cmd)
            # Ensure the line contains the json
            if first_key in read_line and read_line[-1] == "}":
                break
            if time.time() > t_start + timeout:
                raise TimeoutError(
                    f"Failed to query JSON within {timeout} s. "
                    f"Command {cmd!r} failed."
                )

        return "".join(["{", *read_line.split("{")[1:]])

    # ERASynth specific methods

    def get_configuration(self, par_name: str = None) -> Union[Dict[str, str], str]:
        """
        Returns the configuration JSON that contains all parameters.
        """
        config_json = json.loads(self._get_json("RA", "rfoutput"))

        return config_json if par_name is None else config_json[par_name]

    def get_diagnostic_status(self, par_name: str = None) -> Union[Dict[str, str], str]:
        """
        Returns the diagnostic JSON.
        """
        config_json = json.loads(self._get_json("RD", "temperature"))
        return config_json if par_name is None else config_json[par_name]

    def preset(self) -> None:
        """
        Presets the device to known values.

        .. warning::

            After the reset the output is set to power 0.0 dBm @ 1GHz!
        """
        self.write("PP")
        self._prep_communication()

    def factory_reset(self) -> None:
        """
        Does factory reset on the device.
        """
        self.write("PR")
        self._prep_communication()

    def esp8266_upload_mode(self) -> None:
        """Sets the ESP8266 module in upload mode."""
        self.write("U")

    def wifi_on(self) -> None:
        """Turn ESP8266 WiFi module on."""
        self.write("PE01")

    def wifi_off(self) -> None:
        """Turn ESP8266 WiFi module off."""
        self.write("PE00")

    def run_self_test(self) -> None:
        """
        Sets all settable parameters to different values.

        NB serves as self test of the instrument because setting readable parameters
        is done by setting and confirming the value.
        """
        par_values = list(_SELF_TEST_LIST)

        if isinstance(self, (ERASynthPlus, ERASynthPlusPlus)):
            # Only ERASynth+ and ERASynth++ have this functionality
            par_values += [
                ("reference_tcxo_ocxo", "tcxo"),
                ("reference_tcxo_ocxo", "ocxo"),
            ]

        num_tests = len(par_values)
        for i, (name, val) in enumerate(par_values):
            print(f"\r[{i+1:2d}/{num_tests}] Running...", end="")
            self.set(name, val)

        print("\nDone!")

    # ##################################################################################
    # set commands
    # ##################################################################################

    def _set_and_confirm(self, cmd: str, cmd_arg: str, str_back: str = None) -> None:
        """
        Because for this command the instrument replies with a text containing the
        value, we make use of it to ensure we waited enough time for the changes to
        take effect.
        """
        str_back = cmd_arg if str_back is None else str_back
        while True:
            read_line = self.ask(f"{cmd}{cmd_arg}")
            if str_back in read_line:
                break

    def _set_frequency(self, value: str) -> None:
        self._set_and_confirm(cmd="F", cmd_arg=value)

    def _set_power(self, value: str) -> None:
        self._set_and_confirm(cmd="A", cmd_arg=value)

    def _set_status(self, value: str) -> None:
        str_back = {"0": "OFF", "1": "ON"}[value]
        self._set_and_confirm(cmd="P0", cmd_arg=value, str_back=str_back)


def _mk_frequency(self, max_frequency: float) -> Parameter:
    frequency = Parameter(
        name="frequency",
        instrument=self,
        label="Frequency",
        unit="Hz",
        vals=validators.Numbers(min_value=250e3, max_value=max_frequency),
        get_cmd="RA:frequency",
        get_parser=int,
        set_cmd=self._set_frequency,
        set_parser=lambda freq: str(int(freq)),
    )
    frequency.__doc__ = "The RF Frequency in Hz."
    return frequency


def _mk_sweep_start_frequency(self, max_frequency: float) -> Parameter:
    sweep_start_frequency = Parameter(
        name="sweep_start_frequency",
        instrument=self,
        label="Sweep start",
        unit="Hz",
        vals=validators.Numbers(min_value=250e3, max_value=max_frequency),
        get_cmd=f"RA:{_CMD_TO_JSON_MAPPING['S1']}",
        get_parser=int,
        set_cmd="S1{}",
        set_parser=lambda freq: str(int(freq)),
    )
    sweep_start_frequency.__doc__ = "Sweep start frequency in Hz."
    return sweep_start_frequency


def _mk_sweep_stop_frequency(self, max_frequency: float) -> Parameter:
    sweep_stop_frequency = Parameter(
        name="sweep_stop_frequency",
        instrument=self,
        label="Sweep stop",
        unit="Hz",
        vals=validators.Numbers(min_value=250e3, max_value=max_frequency),
        get_cmd=f"RA:{_CMD_TO_JSON_MAPPING['S2']}",
        get_parser=int,
        set_cmd="S2{}",
        set_parser=lambda freq: str(int(freq)),
    )
    sweep_stop_frequency.__doc__ = "Sweep stop frequency in Hz."
    return sweep_stop_frequency


def _mk_sweep_step_frequency(self, max_frequency: float) -> Parameter:
    sweep_step_frequency = Parameter(
        name="sweep_step_frequency",
        instrument=self,
        label="Sweep step",
        unit="Hz",
        vals=validators.Numbers(min_value=0, max_value=max_frequency),
        get_cmd=f"RA:{_CMD_TO_JSON_MAPPING['S3']}",
        get_parser=int,
        set_cmd="S3{}",
        set_parser=lambda freq: str(int(freq)),
    )
    sweep_step_frequency.__doc__ = "Sweep step frequency in Hz."
    return sweep_step_frequency


class ERASynth(ERASynthBase):
    """
    Driver for the ERASynth model instrument.

    For ERASynth+/ERASynth++ see :class:`.EraSynthPlus`/:class:`.EraSynthPlusPlus`
    classes.
    """

    def __init__(self, name: str, address: str, **kwargs):
        super().__init__(name=name, address=address, **kwargs)

        self.frequency = _mk_frequency(self, max_frequency=6e9)
        self.sweep_start_frequency = _mk_sweep_start_frequency(self, max_frequency=6e9)
        self.sweep_stop_frequency = _mk_sweep_stop_frequency(self, max_frequency=6e9)
        self.sweep_step_frequency = _mk_sweep_step_frequency(
            self, max_frequency=6e9 - 250e3
        )

        self.reference_tcxo_ocxo = Parameter(
            name="reference_tcxo_ocxo",
            instrument=self,
            val_mapping={"tcxo": "0", "ocxo": "1"},
            get_cmd=f"RA:{_CMD_TO_JSON_MAPPING['P5']}",
        )
        """
        NB not tested if this parameter is available for the ERASynth model (<6GHz)!
        """


class ERASynthPlus(ERASynthBase):
    """
    Driver for the ERASynth+ model instrument.

    For ERASynth/ERASynth++ see :class:`.EraSynth`/:class:`.EraSynthPlusPlus` classes.
    """

    def __init__(self, name: str, address: str, **kwargs):
        super().__init__(name=name, address=address, **kwargs)

        self.frequency = _mk_frequency(self, max_frequency=15e9)
        self.sweep_start_frequency = _mk_sweep_start_frequency(self, max_frequency=15e9)
        self.sweep_stop_frequency = _mk_sweep_stop_frequency(self, max_frequency=15e9)
        self.sweep_step_frequency = _mk_sweep_step_frequency(
            self, max_frequency=15e9 - 250e3
        )

        self.reference_tcxo_ocxo = Parameter(
            name="reference_tcxo_ocxo",
            instrument=self,
            val_mapping={"tcxo": "0", "ocxo": "1"},
            get_cmd=f"RA:{_CMD_TO_JSON_MAPPING['P5']}",
            set_cmd="P5{}",
        )
        """Chooses reference type."""


class ERASynthPlusPlus(ERASynthPlus):
    """
    Driver for the ERASynth++ model instrument.

    For ERASynth/ERASynth+ see :class:`.EraSynth`/:class:`.EraSynthPlus` classes.
    """

    def __init__(self, name: str, address: str, **kwargs):
        super().__init__(name=name, address=address, **kwargs)

        self.frequency = _mk_frequency(self, max_frequency=20e9)
        self.sweep_start_frequency = _mk_sweep_start_frequency(self, max_frequency=20e9)
        self.sweep_stop_frequency = _mk_sweep_stop_frequency(self, max_frequency=20e9)
        self.sweep_step_frequency = _mk_sweep_step_frequency(
            self, max_frequency=20e9 - 250e3
        )


_SELF_TEST_LIST: List[Tuple[str, Union[bool, float, int, str]]] = [
    ("frequency", 3.3e9),
    ("modulation_am_depth", 30),
    ("modulation_fm_deviation", 1e3),
    ("modulation_freq", 2e3),
    ("modulation_pulse_period", 0.003),
    ("modulation_pulse_width", 0.002),
    ("power", 0.01),
    ("power", -0.01),
    ("sweep_dwell", 0.001),
    ("sweep_start_frequency", 2e9),
    ("sweep_step_frequency", 0.5e9),
    ("sweep_stop_frequency", 6e9),
    ("status", True),
    ("status", False),
    ("modulation_en", True),
    ("modulation_en", False),
    ("modulation_signal_waveform", "triangle"),
    ("modulation_signal_waveform", "ramp"),
    ("modulation_signal_waveform", "square"),
    ("modulation_signal_waveform", "sine"),
    ("modulation_source", "internal"),
    ("modulation_source", "external"),
    ("modulation_source", "microphone"),
    ("modulation_type", "narrowband_fm"),
    ("modulation_type", "am"),
    ("modulation_type", "pulse"),
    ("modulation_type", "wideband_fm"),
    ("ref_osc_source", "ext"),
    ("ref_osc_source", "int"),
    ("synthesizer_mode", "low_phase_noise"),
    ("synthesizer_mode", "low_spurious"),
    ("sweep_en", True),
    ("sweep_en", False),
    ("sweep_trigger", "freerun"),
    ("sweep_trigger", "external"),
    ("wifi_mode", "hotspot"),
    ("wifi_mode", "station"),
    ("wifi_station_ssid", "ERA_123"),
    ("wifi_station_ssid", "ERA"),
    ("wifi_station_password", "era1234"),
    ("wifi_station_password", "era19050"),
    ("wifi_hotspot_ssid", "ERA"),
    ("wifi_hotspot_ssid", "ERASynth"),
    ("wifi_hotspot_password", "erainstruments+"),
    ("wifi_hotspot_password", "erainstruments"),
    ("wifi_ip_address", "192.168.001.151"),
    ("wifi_ip_address", "192.168.001.150"),
    ("wifi_gateway_address", "192.168.001.002"),
    ("wifi_gateway_address", "192.168.001.001"),
    ("wifi_subnet_address", "255.255.255.001"),
    ("wifi_subnet_address", "255.255.255.000"),
]
"""
A list of `Tuple[<parameter_name, value>]` used for a self-test of the instrument.
It is intended to check that read/write parameters are set correctly.
"""
