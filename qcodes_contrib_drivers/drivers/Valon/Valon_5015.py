"""
Driver for Valon 5015 Frequency Synthesizer.

Please refer to Valon's 5015 Frequency Synthesizer manual for further
details and functionality. This model is not SCPI compliant.
"""
import re
import logging
from typing import Any

from qcodes.utils.validators import Ints, Numbers, Bool
from qcodes import VisaInstrument
import pyvisa.constants as vi_const


log = logging.getLogger(__name__)


class Valon5015(VisaInstrument):
    """Driver for Valon 5015 Frequency Synthesizer.

    This driver does not contain all commands available for the Valon 5015 but
    only the ones most commonly used.
    """
    __frequency_regex = re.compile(r"F (?P<frequency>\d+([.]\d+)?) MHz")
    __offset_regex = re.compile(r"OFFSET (?P<offset>\d+([.]\d+)?) MHz")
    __power_regex = re.compile(r"PWR (?P<power>\d+[.]\d+)")
    __modulation_db_regex = re.compile(r"AMD (?P<modulation_db>\d+[.]\d+) dB")
    __modulation_frequency_regex = re.compile(r"AMF (?P<modulation_frequency>\d+([.]\d+)?) kHz")
    __low_power_mode_enabled_regex = re.compile(r"PDN (?P<low_power_mode_enabled>[01])")
    __buffer_amplifiers_enabled_regex = re.compile(r"OEN (?P<buffer_amplifiers_enabled>[01])")

    def __init__(self, name: str, address: str, **kwargs: Any):
        super().__init__(name, address, terminator='\r\n', **kwargs)

        self.add_parameter(name='status',
                           label='Status',
                           get_cmd=self._get_status,
                           docstring="Get the manufacturer's name, model, serial number, firmware version, firmware build date and time, uP clock rate, power supply voltage (VBAT), internal temperature, LM, and UID.")
        
        self.add_parameter(name='id',
                           label='ID',
                           get_cmd=self._get_id,
                           set_cmd=self._set_id,
                           vals=Ints(0),
                           docstring="Get an identifying string containing the following information: Valon Technology, 5015/5019, serial number, firmware revision. Setting a number to the `id` method will flash the `Status LED` in short burst of 1 second for the number of times entered.")

        self.add_parameter(name='frequency',
                           label='Frequency',
                           unit='Hz',
                           get_cmd=self._get_frequency,
                           set_cmd=self._set_frequency,
                           vals=Numbers(10e6, 15e9),
                           docstring="Get/set the frequency of the single tone. The allowed range is from 10 MHz to 15 GHz and the value is expressed in Hz.")
        
        self.add_parameter(name='offset',
                           label='Offset',
                           unit='Hz',
                           get_cmd=self._get_offset,
                           set_cmd=self._set_offset,
                           vals=Numbers(-4295e3, 4295e3),
                           docstring="Get/set the offset to be added or substracted from the frequency. The allowed range is from -4.295 GHz to 4295 GHz and the value is expressed in Hz.")
        
        self.add_parameter(name='power',
                           label='Power',
                           unit='dBm',
                           get_cmd=self._get_power,
                           set_cmd=self._set_power,
                           docstring="Get/Set the power level in dBm.")
        
        self.add_parameter(name='modulation_db',
                           label='Modulation_dB',
                           unit='dB',
                           get_cmd=self._get_modulation_db,
                           set_cmd=self._set_modulation_db,
                           vals=Numbers(0.0),
                           docstring="Get/Set the AM modulation in dB. A value of 0 dB disables the AM modulation.")
        
        self.add_parameter(name='modulation_frequency',
                           label='Modulation_Frequency',
                           unit='Hz',
                           get_cmd=self._get_modulation_frequency,
                           set_cmd=self._set_modulation_frequency,
                           vals=Numbers(1, 2e3),
                           docstring="Get/Set the AM modulation frequency. The allowed range is from 1 Hz to 2 kHz and the value is expressed in Hz.")

        self.add_parameter(name='low_power_mode_enabled',
                           label='Low Power Mode Enabled',
                           get_cmd=self._get_low_power_mode_enabled,
                           set_cmd=self._set_low_power_mode_enabled,
                           vals=Bool(),
                           docstring="Enables or disables the low power mode.")
        
        self.add_parameter(name='buffer_amplifiers_enabled',
                           label='Buffer Amplifiers Enabled',
                           get_cmd=self._get_buffer_amplifiers_enabled,
                           set_cmd=self._set_buffer_amplifiers_enabled,
                           vals=Bool(),
                           docstring="Enables or disables the RF output buffer amplifiers.")

    def _get_status(self):
        responses = [self.ask("stat") for _ in range(14)]
        responses = "\n".join(responses[1:])
        self._flush()
        return responses

    def _get_id(self):
        responses = [self.ask("id") for _ in range(2)]
        responses = "\n".join(responses[1:])
        self._flush()
        return responses
    
    def _set_id(self, n):
        self.ask(f"id {n}")
        self._flush()

    def _get_frequency(self):
        response = [self.ask("frequency") for _ in range(2)][1]
        match = self.__frequency_regex.match(response)
        frequency = match.group("frequency")
        self._flush()
        return float(frequency) * 1e6

    def _set_frequency(self, frequency):
        self.ask(f"frequency {int(frequency)} Hz")
        self._flush()

    def _get_offset(self):
        response = [self.ask("offset") for _ in range(2)][1]
        match = self.__offset_regex.match(response)
        offset = match.group("offset")
        self._flush()
        return float(offset) * 1e6

    def _set_offset(self, offset):
        self.ask(f"offset {int(offset)} Hz")
        self._flush()

    def _get_power(self):
        response = [self.ask("power") for _ in range(2)][1]
        match = self.__power_regex.match(response)
        power = match.group("power")
        self._flush()
        return float(power)

    def _set_power(self, power):
        self.ask(f"power {power}")
        self._flush()

    def _get_modulation_db(self):
        response = [self.ask("amd") for _ in range(2)][1]
        match = self.__modulation_db_regex.match(response)
        modulation_db = match.group("modulation_db")
        self._flush()
        return float(modulation_db)

    def _set_modulation_db(self, modulation_db):
        self.ask(f"amd {modulation_db}")
        self._flush()

    def _get_modulation_frequency(self):
        response = [self.ask("amf") for _ in range(2)][1]
        match = self.__modulation_frequency_regex.match(response)
        modulation_frequency = match.group("modulation_frequency")
        self._flush()
        return float(modulation_frequency) * 1e3

    def _set_modulation_frequency(self, modulation_frequency):
        self.ask(f"amd {int(modulation_frequency)}")
        self._flush()

    def _get_low_power_mode_enabled(self):
        response = [self.ask("pdn") for _ in range(2)][1]
        match = self.__low_power_mode_enabled_regex.match(response)
        low_power_mode_enabled = match.group("low_power_mode_enabled")
        self._flush()
        return True if low_power_mode_enabled == "1" else False

    def _set_low_power_mode_enabled(self, low_power_mode_enabled):
        low_power_mode_enabled = "1" if low_power_mode_enabled else "0"
        self.ask(f"pdn {low_power_mode_enabled}")
        self._flush()

    def _get_buffer_amplifiers_enabled(self):
        response = [self.ask("oen") for _ in range(2)][1]
        match = self.__buffer_amplifiers_enabled_regex.match(response)
        buffer_amplifiers_enabled = match.group("buffer_amplifiers_enabled")
        self._flush()
        return True if buffer_amplifiers_enabled == "1" else False

    def _set_buffer_amplifiers_enabled(self, buffer_amplifiers_enabled):
        buffer_amplifiers_enabled = "1" if buffer_amplifiers_enabled else "0"
        self.ask(f"oen {buffer_amplifiers_enabled}")
        self._flush()

    def _flush(self):
        self.visa_handle.flush(vi_const.VI_READ_BUF | vi_const.VI_READ_BUF_DISCARD)
