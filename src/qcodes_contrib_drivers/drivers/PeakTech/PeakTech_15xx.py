from typing import Any, Optional

import pyvisa

from qcodes.instrument.visa import VisaInstrument
from qcodes.utils import DelayedKeyboardInterrupt
from qcodes.utils.helpers import create_on_off_val_mapping
from qcodes.utils.validators import Numbers


class PeakTech15xx(VisaInstrument):
    """
    Driver for the PeakTech 15xx power supply.

    This driver implements the necessary commands to control the PeakTech
    15xx power supply using QCoDeS.

    Attributes:
        set_voltage (Parameter): Set or get the preset voltage value.
        set_current (Parameter): Set or get the preset current value.
        output_enabled (Parameter): Enable or disable the output of the power
            supply.
        voltage_limit (Parameter): Set or get the preset upper limit of voltage.
        current_limit (Parameter): Set or get the preset upper limit of current.
        voltage (Parameter): Get the measured voltage from the power supply.
        current (Parameter): Get the measured current from the power supply.
        status (Parameter): Get the status of the power supply (CV or CC mode).

    Methods:
        get_idn(): Get the instrument identification information.
        read_until(termination, timeout=None): Read from the instrument until
            the termination sequence is found.
        write_raw(cmd): Write a command to the instrument.
        ask_raw(cmd): Write a command to the instrument and read the response.
    """

    def __init__(
        self,
        name: str,
        address: str,
        gmax: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize the PeakTech 15xx instrument.

        Args:
            name: Name of the instrument.
            address: VISA resource name of the instrument.
            gmax: Optional. A string specifying the maximum voltage and
                  current in the format 'VVVAAA', where 'VVV' is the maximum
                  voltage (e.g., 162 for 16.2 V) and 'AAA' is the maximum
                  current (e.g., 430 for 4.30 A). 
                  If it doesn't match the response of `GMAX` from the 
                  instrument, a error will be raised.
                  Use "ask('GMAX')" to retrieve it.

        """
        super().__init__(
            name=name,
            address=address,
            **kwargs
        )

        self.visa_handle.baud_rate = 9600
        self.visa_handle.data_bits = 8
        self.visa_handle.stop_bits = pyvisa.constants.StopBits.one
        self.visa_handle.parity    = pyvisa.constants.Parity.none
        self.visa_handle.read_termination  = None
        self.visa_handle.write_termination = '\r'

        self._write_acknowledge = 'OK\r'
        self._ask_answer_end    = '\rOK\r'

        # Initialize maximum voltage and current
        self._max_voltage: Optional[float] = None
        self._max_current: Optional[float] = None
        self._get_max_values(gmax)

        self.add_parameter(
            "set_voltage",
            label="Set Voltage",
            unit="V",
            get_cmd="GETS",
            set_cmd="VOLT{}",
            get_parser=lambda x: self._get_parser(x[:3]),
            set_parser=self._set_parser,
            vals=Numbers(0, self._max_voltage if self._max_voltage else 99.9),
            docstring="""
            Set or get the preset voltage value of the power supply.
            """
        )

        self.add_parameter(
            "set_current",
            label="Set Current",
            unit="A",
            get_cmd="GETS",
            set_cmd="CURR{}",
            get_parser=lambda x: self._get_parser(x[3:]),
            set_parser=self._set_parser,
            vals=Numbers(0, self._max_current if self._max_current else 99.9),
            docstring="""
            Set or get the preset current value of the power supply.
            """
        )

        self.add_parameter(
            "output_enabled",
            label="Output Enabled",
            get_cmd="GOUT",
            set_cmd="SOUT{}",
            val_mapping=create_on_off_val_mapping(on_val='0', off_val='1'),
            docstring="""
            Enable or disable the output of the power supply.
            """
        )

        self.add_parameter(
            "voltage_limit",
            label="Voltage Limit",
            unit="V",
            get_cmd="GOVP",
            set_cmd="SOVP{}",
            get_parser=self._get_parser,
            set_parser=self._set_parser,
            vals=Numbers(0, self._max_voltage if self._max_voltage else 99.9),
            docstring="""
            Set or get the preset upper limit of voltage.
            """
        )

        self.add_parameter(
            "current_limit",
            label="Current Limit",
            unit="A",
            get_cmd="GOCP",
            set_cmd="SOCP{}",
            get_parser=self._get_parser,
            set_parser=self._set_parser,
            vals=Numbers(0, self._max_current if self._max_current else 99.9),
            docstring="""
            Set or get the preset upper limit of current.
            """
        )

        self.add_parameter(
            "voltage",
            label="Measured Voltage",
            unit="V",
            get_cmd="GETD",
            get_parser=lambda x: self._get_parser(x[:4], 4),
            docstring="""
            Get the measured voltage from the power supply.
            """
        )

        self.add_parameter(
            "current",
            label="Measured Current",
            unit="A",
            get_cmd="GETD",
            get_parser=lambda x: self._get_parser(x[4:8], 4),
            docstring="""
            Get the measured current from the power supply.
            """
        )

        self.add_parameter(
            "mode",
            label="Mode",
            get_cmd="GETD",
            get_parser=lambda x: x[8],
            val_mapping={
                'CV': '0',
                'CC': '1'
            },
            docstring="""
            Get the mode of the power supply.

            Values:
                'CV': Constant Voltage mode
                'CC': Constant Current mode
            """
        )

    def get_idn(self) -> dict[str, Optional[str]]:
        """
        Get the instrument identification information.

        Returns:
            A dictionary containing vendor, model, serial, and firmware
            information.

        Note:
            The instrument does not support the standard '*IDN?' command.
            This method returns predefined identification information.
        """
        idparts: list[Optional[str]] = ["PeakTech", "15xx", None, None]
        return dict(zip(("vendor", "model", "serial", "firmware"), idparts))

    def _check_and_flush_buffer(self) -> None:
        """
        Check if the serial read buffer is empty. If not, log a warning and
        flush the buffer.
        """
        available_bytes = self.visa_handle.get_visa_attribute(
            pyvisa.constants.VI_ATTR_ASRL_AVAIL_NUM
        )
        if available_bytes > 0:
            read_bytes = self.visa_handle.read_bytes(available_bytes)
            read_ascii = read_bytes.decode('ascii', errors='backslashreplace')
            self.log.warning(
                f"{available_bytes} bytes in serial read buffer. "
                f"Flushing buffer. Flushed data: {repr(read_ascii)}"
            )

    def read_until(
        self,
        termination: str,
        timeout: Optional[float] = None
    ) -> str:
        """
        Read from the instrument until the termination sequence is found.

        Args:
            termination: The termination sequence to look for.
            timeout: The timeout in seconds. If None, uses the instrument's
                default timeout.

        Returns:
            The data read from the instrument, including the termination
            sequence.

        Raises:
            TimeoutError: If the read operation times out before finding the
                termination sequence.
        """
        if timeout is None:
            timeout = self._get_visa_timeout()
        import time
        start_time = time.time()
        buf = ''
        term_len = len(termination)
        while True:
            byte = self.visa_handle.read_bytes(1, break_on_termchar=False)
            if not byte:
                continue
            char = byte.decode('ascii', errors='ignore')
            buf += char
            if buf[-term_len:] == termination:
                break
            if timeout is not None and (time.time() - start_time) > timeout:
                raise TimeoutError(
                    "Read until termination sequence timed out"
                )
        return buf

    def write_raw(self, cmd: str) -> None:
        """
        Write a command to the instrument.

        Overrides the base method to handle the instrument's acknowledge
        response and flush the read buffer if necessary.

        Args:
            cmd: The command string to write to the instrument.

        Raises:
            IOError: If the instrument's acknowledge response does not match
                the expected response.
        """
        self._check_and_flush_buffer()

        with DelayedKeyboardInterrupt(
            context={"instrument": self.name, "reason": "Visa Instrument write"}
        ):
            self.visa_log.debug(f"Writing: {cmd}")
            self.visa_handle.write(cmd)
            response = self.read_until(self._write_acknowledge)
            self.visa_log.debug(f"Response: {response}")
            if response != self._write_acknowledge:
                raise IOError(
                    f"Expected {repr(self._write_acknowledge)} response, "
                    f"but got: {repr(response)}"
                )

    def ask_raw(self, cmd: str) -> str:
        """
        Write a command to the instrument and read the response.

        Overrides the base method to handle the instrument's response and
        flush the read buffer if necessary.

        Args:
            cmd: The command string to write to the instrument.

        Returns:
            The response string from the instrument, excluding the termination
            sequence.

        Raises:
            IOError: If an error occurs during communication.
        """
        self._check_and_flush_buffer()

        with DelayedKeyboardInterrupt(
            context={"instrument": self.name, "reason": "Visa Instrument ask"}
        ):
            self.visa_log.debug(f"Querying: {cmd}")
            self.visa_handle.write(cmd)
            response = self.read_until(self._ask_answer_end)
            self.visa_log.debug(f"Response: {response}")
            return response.rstrip(self._ask_answer_end)

    def _get_parser(self, input_string: str, length: int = 3) -> float:
        """
        Convert a string of digits into a float with a decimal point.

        Args:
            input_string: A numeric string consisting of digits.
            length: Expected length of the input string (must be 3 or 4).

        Returns:
            The converted float value.

        Raises:
            ValueError: If input_string contains non-digit characters, length
                is not 3 or 4, or if input_string's length doesn't match the
                specified length.
        """
        try:
            if length not in [3, 4]:
                raise ValueError("Length parameter must be 3 or 4.")
            if not input_string.isdigit():
                raise ValueError("Input string must contain only digits.")
            if len(input_string) != length:
                raise ValueError(
                    f"Input string length must be {length} characters."
                )
            divisor = 10 if length == 3 else 100
            return float(input_string) / divisor
        except Exception as e:
            raise ValueError(f"Error parsing input string: {e}")

    def _set_parser(self, input_float: float) -> str:
        """
        Convert a float smaller than 100 and non-negative into a string.

        Args:
            input_float: A float value (e.g., 12.7).

        Returns:
            A 3-character string with the decimal point removed and 
            leading zeros if necessary (e.g., '127', '005').

        Raises:
            ValueError: If the input float is negative or >= 100.
        """
        try:
            if input_float < 0 or input_float >= 100:
                raise ValueError(
                    "Input float must be non-negative and smaller than 100."
                )
            scaled_value = int(input_float * 10)
            #return f"{scaled_value}"
            return f"{scaled_value:03}"
        except Exception as e:
            raise ValueError(f"Error converting float to string: {e}")

    def _get_max_values(self, gmax: Optional[str] = None) -> None:
        """
        Get the maximum voltage and current from the instrument or validate
        against the provided `gmax` parameter.
    
        Args:
            gmax: Optional string specifying the maximum voltage and
                  current in the format 'VVVAAA'. If provided, this method
                  validates it against the instrument's response.
    
        Raises:
            ValueError: If the instrument's `GMAX` response does not match
                        the provided `gmax`.
        """
        try:
            if gmax:
                response = self.ask("GMAX").strip()
                if response != gmax:
                    raise ValueError(
                        f"Instrument's GMAX response ({response}) does not "
                        f"match the provided gmax ({gmax}). Ensure the correct "
                        f"instrument is connected."
                    )
                voltage_str = gmax[:3]
                current_str = gmax[3:]
                self._max_voltage = self._get_parser(voltage_str)
                self._max_current = self._get_parser(current_str)
            else:
                response = self.ask("GMAX").strip()
                voltage_str = response[:3]
                current_str = response[3:]
                self._max_voltage = self._get_parser(voltage_str)
                self._max_current = self._get_parser(current_str)
        except Exception as e:
            raise ValueError(
                f"Failed to validate instrument: {e}. Ensure the instrument "
                f"is connected and responds to the 'GMAX' command."
            )
    