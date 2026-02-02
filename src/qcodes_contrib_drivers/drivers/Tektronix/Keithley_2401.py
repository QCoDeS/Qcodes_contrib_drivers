from qcodes.instrument import VisaInstrument
from qcodes.validators import Numbers
import numpy as np
import time


class Keithley2400(VisaInstrument):
    """
    QCoDeS driver for Keithley 2400 SourceMeter.
    Provides functionality for sourcing and measuring voltage, current, and resistance.
    Includes support for voltage sweeps and detailed parameter configuration.
    """

    def __init__(self, name: str, address: str, **kwargs):
        """
        Initialize the Keithley 2400 SourceMeter.
        Args:
            name (str): Name of the instrument.
            address (str): Visa address of the instrument.
        """
        super().__init__(name, address, terminator='\n', **kwargs)

        # Parameters
        self.add_parameter(
            'voltage',
            label='Set Voltage',
            unit='V',
            get_cmd=':SOUR:VOLT:LEV:IMM:AMPL?',
            set_cmd=':SOUR:VOLT:LEV:IMM:AMPL {:.4f}',
            get_parser=float,
            vals=Numbers(-210, 210)
        )

        self.add_parameter(
            'current',
            label='Measured Current',
            unit='A',
            get_cmd=self._measure_current
        )

        self.add_parameter(
            'set_current',
            label='Set Current',
            unit='A',
            get_cmd=':SOUR:CURR:LEV:IMM:AMPL?',
            set_cmd=':SOUR:CURR:LEV:IMM:AMPL {:.4f}',
            get_parser=float,
            vals=Numbers(-1.05, 1.05)  # Adjust the range based on the Keithley 2400 specs
        )

        self.add_parameter(
            'measured_voltage',
            label='Measured Voltage',
            unit='V',
            get_cmd=self._measure_voltage
        )

        self.add_parameter(
            'resistance',
            label='Measured Resistance',
            unit='Ohm',
            get_cmd=self._measure_resistance
        )

        self.add_parameter(
            'output',
            label='Output State',
            get_cmd=':OUTP?',
            set_cmd=':OUTP {}',
            val_mapping={'on': 1, 'off': 0}
        )

        self.add_parameter(
            'current_range',
            label='Current Range',
            get_cmd=':SENS:CURR:RANG?',
            set_cmd=':SENS:CURR:RANG {:.4f}',
            get_parser=float,
            vals=Numbers(1e-9, 1e1)
        )

        self.add_parameter(
            'auto_range',
            label='Auto Range',
            get_cmd=':SENS:CURR:RANG:AUTO?',
            set_cmd=':SENS:CURR:RANG:AUTO {}',
            val_mapping={True: 'ON', False: 'OFF'}
        )

        self.add_parameter(
            'sweep_voltage',
            label='Sweep Voltage',
            unit='V',
            set_cmd=self.set_voltage
        )

        self.connect_message()

    def _measure_voltage(self):
        """
        Measure the voltage in the selected range or auto-range.
        Returns:
            float: Measured voltage in volts.
        """
        self.write(':FUNC "VOLT"')
        self.write(':FORM:ELEM VOLT')
        response = self.ask(':READ?')
        return float(response)

    def _measure_current(self):
        """
        Measure the current in the selected range or auto-range.
        Returns:
            float: Measured current in amperes.
        """
        self.write(':FUNC "CURR"')
        self.write(':FORM:ELEM CURR')
        response = self.ask(':READ?')
        return float(response)

    def _measure_resistance(self):
        """
        Measure the resistance in the selected range.
        Returns:
            float: Measured resistance in ohms.
        """
        self.write(':FUNC "RES"')
        self.write(':FORM:ELEM RES')
        response = self.ask(':READ?')
        return float(response)

    def enable_output(self, state: bool = True):
        """
        Enable or disable the output.
        Args:
            state (bool): Set True to enable, False to disable.
        """
        self.output('on' if state else 'off')

    def set_voltage(self, voltage: float):
        """
        Set the output voltage.
        Args:
            voltage (float): The voltage level to set in volts.
        """
        self.voltage(voltage)

    def sweep_voltage_measure(self, voltage_start: float, voltage_stop: float, steps: int):
        """
        Sweep voltage from start to stop in specified steps and measure voltage and current.
        Args:
            voltage_start (float): Starting voltage.
            voltage_stop (float): Ending voltage.
            steps (int): Number of steps.
        Returns:
            list of dict: Contains 'voltage_set', 'voltage_measured', and 'current_measured'.
        """
        voltage_values = np.linspace(voltage_start, voltage_stop, steps)
        measurements = []
        self.write(':FUNC "VOLT","CURR"')
        self.write(':FORM:ELEM VOLT,CURR')

        for voltage in voltage_values:
            self.voltage(voltage)
            time.sleep(0.1)  # Allow settling
            response = self.ask(':READ?')
            voltage_measured, current_measured = map(float, response.split(','))
            measurements.append({
                'voltage_set': voltage,
                'voltage_measured': voltage_measured,
                'current_measured': current_measured
            })
        return measurements
