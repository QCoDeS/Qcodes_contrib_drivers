from qcodes import VisaInstrument
from qcodes.utils.validators import Numbers

class RigolDP932E(VisaInstrument):
    """
    QCoDeS driver for the Rigol DP932E Programmable DC Power Supply.
    """

    def __init__(self, name: str, address: str, **kwargs):
        super().__init__(name, address, **kwargs)

        # Add parameters for each channel
        for channel in range(1, 4):
            self.add_parameter(f'voltage_{channel}',
                               label=f'Channel {channel} Voltage',
                               unit='V',
                               get_cmd=f':MEASure:VOLTage? CH{channel}',
                               set_cmd=f':APPLy CH{channel},{{}}',
                               get_parser=float,
                               vals=Numbers(0, 31.5))  # According to manual, max voltage is 31.5V for DP932E

            self.add_parameter(f'current_{channel}',
                               label=f'Channel {channel} Current',
                               unit='A',
                               get_cmd=f':MEASure:CURRent? CH{channel}',
                               set_cmd=f':APPLy CH{channel},,,{{}}',
                               get_parser=float,
                               vals=Numbers(0, 3.15))  # According to manual, max current is 3.15A for DP932E

            self.add_parameter(f'output_{channel}',
                               label=f'Channel {channel} Output',
                               get_cmd=f':OUTPut:STATe? CH{channel}',
                               set_cmd=f':OUTPut:STATe {{}} CH{channel}',
                               val_mapping={'ON': 1, 'OFF': 0})

        # Reset the instrument
        self.write('*RST')
        self.connect_message()

    def reset(self):
        """Resets the instrument to its default settings."""
        self.write('*RST')

    def enable_output(self, channel: int):
            """Enables the output for the specified channel."""
            self.write(f':OUTPut CH{channel},ON')

    def disable_output(self, channel: int):
        """Disables the output for the specified channel."""
        self.write(f':OUTPut CH{channel},OFF')

    def measure_voltage(self, channel: int) -> float:
        """Measures the voltage at the output terminal of the specified channel."""
        return float(self.ask(f':MEASure:VOLTage? CH{channel}'))

    def measure_current(self, channel: int) -> float:
        """Measures the current at the output terminal of the specified channel."""
        return float(self.ask(f':MEASure:CURRent? CH{channel}'))

    def set_voltage(self, channel: int, voltage: float):
        """Sets the output voltage for the specified channel."""
        self.write(f':APPLy CH{channel},{voltage}')

    def set_current(self, channel: int, current: float):
        """Sets the output current for the specified channel."""
        self.write(f':APPLy CH{channel},,,{current}')

    def set_output_state(self, channel: int, state: str):
        """Sets the output state (ON/OFF) for the specified channel."""
        self.write(f':OUTPut:STATe {state},CH{channel}')

    def measure_power(self, channel: int) -> float:
        """Measures the power at the output terminal of the specified channel."""
        return float(self.ask(f':MEASure:POWEr? CH{channel}'))
