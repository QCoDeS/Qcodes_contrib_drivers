"""
Driver for Valon 5015 Frequency Synthesizer.

Please refer to Valon's 5015 Frequency Synthesizer manual for further
details and functionality. This model is not SCPI compliant.

Working with FW 2.0a
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
    __frequency_regex = re.compile(r"F (?P<frequency>-?\d+([.]\d+)?) MHz")
    __offset_regex = re.compile(r"OFFSET (?P<offset>-?\d+([.]\d+)?) MHz")
    __power_regex = re.compile(r"PWR (?P<power>-?\d+[.]\d+)")
    __modulation_db_regex = re.compile(r"AMD (?P<modulation_db>-?\d+[.]\d+) dB")
    __modulation_frequency_regex = re.compile(r"AMF (?P<modulation_frequency>-?\d+([.]\d+)?) kHz")
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
                           vals=Numbers(-4295e6, 4295e6),
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
                           set_cmd=self._set_modulation_frequency, # Doesn't appear to work
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

    def askv(self, cmd: str, ltr: int = 1):
        self._flush()
        self.write(cmd)
        return [self.visa_handle.read() for _ in range(ltr)]

    def _get_status(self):
        responses = self.askv('stat', 14)
        responses = "\n".join(responses[1:])
        return responses

    def _get_id(self):
        responses = self.askv("id", 2)
        responses = "\n".join(responses[1:])
        return responses

    def _set_id(self, n):
        self.askv(f"id {n}")

    def _get_frequency(self):
        response = self.askv("frequency", 2)[1]
        match = self.__frequency_regex.match(response)
        frequency = match.group("frequency")
        return float(frequency) * 1e6

    def _set_frequency(self, frequency):
        self.askv(f"frequency {int(frequency)} Hz")

    def _get_offset(self):
        response = self.askv("offset", 2)[1]
        match = self.__offset_regex.match(response)
        offset = match.group("offset")
        return float(offset) * 1e6

    def _set_offset(self, offset):
        self.askv(f"offset {int(offset)} Hz")

    def _get_power(self):
        response = self.askv("power", 2)[1]
        match = self.__power_regex.match(response)
        power = match.group("power")
        return float(power)

    def _set_power(self, power):
        self.askv(f"power {power}")

    def _get_modulation_db(self):
        response = self.askv("amd", 2)[1]
        match = self.__modulation_db_regex.match(response)
        modulation_db = match.group("modulation_db")
        return float(modulation_db)

    def _set_modulation_db(self, modulation_db):
        self.askv(f"amd {modulation_db}")

    def _get_modulation_frequency(self):
        response = self.askv("amf", 2)[1]
        match = self.__modulation_frequency_regex.match(response)
        modulation_frequency = match.group("modulation_frequency")
        return float(modulation_frequency) * 1e3

    def _set_modulation_frequency(self, modulation_frequency):
        self.askv(f"amf {int(modulation_frequency)}")

    def _get_low_power_mode_enabled(self):
        response = self.askv("pdn", 2)[1]
        match = self.__low_power_mode_enabled_regex.match(response)
        low_power_mode_enabled = match.group("low_power_mode_enabled")
        return True if low_power_mode_enabled == "1" else False

    def _set_low_power_mode_enabled(self, low_power_mode_enabled):
        low_power_mode_enabled = "1" if low_power_mode_enabled else "0"
        self.askv(f"pdn {low_power_mode_enabled}")

    def _get_buffer_amplifiers_enabled(self):
        response = self.askv("oen", 2)[1]
        match = self.__buffer_amplifiers_enabled_regex.match(response)
        buffer_amplifiers_enabled = match.group("buffer_amplifiers_enabled")
        return True if buffer_amplifiers_enabled == "1" else False

    def _set_buffer_amplifiers_enabled(self, buffer_amplifiers_enabled):
        buffer_amplifiers_enabled = "1" if buffer_amplifiers_enabled else "0"
        self.askv(f"oen {buffer_amplifiers_enabled}")

    def _flush(self):
        self.visa_handle.flush(vi_const.VI_IO_IN_BUF_DISCARD)