# Keithley 2182A Nanovoltmeter Driver

This directory contains the QCoDeS driver for the Keithley 2182A nanovoltmeter, implementing full functionality based on sections 12–15 of the user manual with special focus on MEASure and FETCh commands.

## Features

### Core Measurement Capabilities
- **DC Voltage Measurement**: High-precision nanovolt measurements
- **Temperature Measurement**: Support for temperature probes with multiple units (K, °C, °F)
- **Auto-ranging**: Automatic range selection for optimal measurement accuracy
- **Manual ranging**: Precise control over measurement ranges

### Measurement Control
- **NPLC Control**: Integration time control via Number of Power Line Cycles (0.01 to 10 NPLC)
- **Aperture Time**: Direct aperture time control (0.0002 to 0.2 seconds)
- **Line Frequency**: Support for 50 Hz and 60 Hz power line frequencies

### Noise Reduction
- **Auto-zero**: Automatic zero correction for improved accuracy
- **Analog Filter**: Low-pass filtering for noise reduction
- **Digital Filter**: Additional digital filtering capability
- **Averaging**: Configurable measurement averaging (1-100 measurements)

### Trigger System
- **Multiple Trigger Sources**: Immediate, external, timer, manual, and bus triggers
- **Trigger Delay**: Configurable trigger delay (0 to 999999.999 seconds)
- **Measurement Initiation**: Manual control over measurement timing

### Advanced Features
- **Input Impedance Control**: Automatic input impedance selection
- **Preset Configurations**: Optimized settings for speed vs. noise performance
- **Statistical Analysis**: Built-in statistics for multiple measurements
- **Comprehensive Status**: Detailed instrument status and configuration reporting

## Usage Example

```python
from qcodes_contrib_drivers.drivers.Tektronix.Keithley_2182A import Keithley2182A

# Initialize the instrument
voltmeter = Keithley2182A('k2182a', 'TCPIP::192.168.1.100::INSTR')

# Basic voltage measurement
voltmeter.configure_voltage_measurement(
    auto_range=True,
    nplc=1.0,
    auto_zero=True
)

# Single measurement
voltage = voltmeter.voltage()
print(f"Voltage: {voltage:.6f} V")

# Optimize for low noise
voltmeter.optimize_for_low_noise()

# Take statistical measurements
stats = voltmeter.measure_voltage_statistics(num_measurements=10)
print(f"Mean: {stats['mean']:.6f} V, Std: {stats['stdev']:.6f} V")

# Temperature measurement
voltmeter.configure_temperature_measurement(units="celsius")
temperature = voltmeter.temperature()
print(f"Temperature: {temperature:.2f} °C")
```

## Key Methods

### Measurement Commands
- `voltage()`: Measure DC voltage using MEASure command
- `temperature()`: Measure temperature 
- `fetch()`: Retrieve last measurement from buffer (FETCh command)
- `read()`: Combined trigger and fetch operation
- `measure_voltage_statistics()`: Multiple measurements with statistics

### Configuration Methods
- `configure_voltage_measurement()`: Complete voltage measurement setup
- `configure_temperature_measurement()`: Complete temperature measurement setup
- `optimize_for_low_noise()`: Configure for maximum accuracy
- `optimize_for_speed()`: Configure for fastest measurements
- `set_measurement_speed()`: Preset speed configurations

### Trigger Control
- `initiate_measurement()`: Start measurement sequence
- `trigger()`: Send software trigger
- `abort_measurement()`: Abort current measurement

### Status and Diagnostics
- `get_measurement_status()`: Comprehensive status information
- `get_error()`: Read error queue
- `self_test()`: Instrument self-test
- `check_ranges()`: Available measurement ranges

## Parameters

### Measurement Parameters
- `mode`: Measurement function (DC voltage, temperature)
- `range`: Measurement range
- `auto_range_enabled`: Auto-range enable/disable
- `nplc`: Integration time in power line cycles
- `aperture_time`: Integration time in seconds
- `line_frequency`: Power line frequency (50/60 Hz)

### Noise Reduction Parameters
- `averaging_enabled`: Enable measurement averaging
- `averaging_count`: Number of measurements to average
- `analog_filter`: Analog low-pass filter enable
- `digital_filter`: Digital filter enable
- `input_impedance`: Auto input impedance selection

### Trigger Parameters
- `trigger_source`: Trigger source selection
- `trigger_delay`: Trigger delay in seconds

### Display and System Parameters
- `display_enabled`: Front panel display control
- `temperature_units`: Temperature measurement units

## SCPI Command Implementation

The driver implements the following key SCPI command groups:

### MEASure Commands
- `MEAS:VOLT:DC?`: Measure DC voltage
- `MEAS:TEMP?`: Measure temperature

### FETCh Commands
- `FETC?`: Fetch last measurement

### SENSe Commands
- `SENS:FUNC`: Measurement function selection
- `SENS:VOLT:DC:RANG`: Range control
- `SENS:VOLT:DC:NPLC`: Integration time control
- `SENS:AVER`: Averaging control

### TRIGger Commands
- `TRIG:SOUR`: Trigger source
- `TRIG:DEL`: Trigger delay
- `INIT`: Initiate measurement
- `ABOR`: Abort measurement

## Compatibility

This driver is designed to be compatible with:
- QCoDeS framework
- VISA communication protocol
- Keithley 2182A nanovoltmeter hardware
- Python 3.11+

## Notes

- The driver follows QCoDeS conventions and patterns
- All parameters include comprehensive docstrings
- Error handling is implemented for robust operation
- The driver supports both immediate measurements and triggered acquisition
- Temperature measurements require appropriate temperature probes
- Measurement ranges and capabilities depend on instrument configuration