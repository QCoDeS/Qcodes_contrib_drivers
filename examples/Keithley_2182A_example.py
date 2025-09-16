"""
Example usage of the Keithley 2182A nanovoltmeter driver.

This script demonstrates the key features and typical usage patterns
of the Keithley2182A driver for QCoDeS.
"""

from qcodes_contrib_drivers.drivers.Tektronix.Keithley_2182A import Keithley2182A

def main():
    """
    Example of how to use the Keithley 2182A driver.
    
    Note: This is a demonstration script. In real usage, you would
    provide an actual VISA address for your instrument.
    """
    
    # Initialize the instrument
    # Replace 'TCPIP::192.168.1.100::INSTR' with your actual VISA address
    voltmeter = Keithley2182A('k2182a', 'TCPIP::192.168.1.100::INSTR')
    
    # Basic voltage measurement configuration
    print("=== Basic Voltage Measurement ===")
    voltmeter.configure_voltage_measurement(
        auto_range=True,
        nplc=1.0,
        auto_zero=True
    )
    
    # Single voltage measurement
    voltage = voltmeter.voltage()
    print(f"Measured voltage: {voltage:.6f} V")
    
    # Configure for low noise measurements
    print("\n=== Low Noise Configuration ===")
    voltmeter.optimize_for_low_noise()
    
    # Take multiple measurements with statistics
    stats = voltmeter.measure_voltage_statistics(num_measurements=10)
    print(f"Voltage statistics (n={stats['count']}):")
    print(f"  Mean: {stats['mean']:.6f} V")
    print(f"  Std Dev: {stats['stdev']:.6f} V")
    print(f"  Min: {stats['min']:.6f} V")
    print(f"  Max: {stats['max']:.6f} V")
    
    # Configure for fast measurements
    print("\n=== Fast Measurement Configuration ===")
    voltmeter.optimize_for_speed()
    
    # Use MEASure vs FETCh commands
    print("\n=== MEASure vs FETCh Commands ===")
    
    # MEASure - triggers new measurement
    measured_value = voltmeter._measure_voltage()
    print(f"MEASure command result: {measured_value:.6f} V")
    
    # FETCh - gets last measurement from buffer
    fetched_value = voltmeter.fetch()
    print(f"FETCh command result: {fetched_value:.6f} V")
    
    # Temperature measurement example
    print("\n=== Temperature Measurement ===")
    voltmeter.configure_temperature_measurement(
        units="celsius",
        nplc=1.0
    )
    
    # Note: This requires appropriate temperature probe
    try:
        temperature = voltmeter.temperature()
        print(f"Measured temperature: {temperature:.2f} °C")
    except Exception as e:
        print(f"Temperature measurement not available: {e}")
    
    # Check measurement status
    print("\n=== Measurement Status ===")
    status = voltmeter.get_measurement_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    # Check available ranges
    print("\n=== Available Ranges ===")
    ranges = voltmeter.check_ranges()
    for key, value in ranges.items():
        print(f"  {key}: {value}")
    
    # Trigger system example
    print("\n=== Trigger System ===")
    voltmeter.trigger_source("manual")
    voltmeter.initiate_measurement()
    print("Measurement initiated, waiting for manual trigger...")
    
    # In real usage, you would trigger externally here
    # For demo, we'll just trigger via software
    voltmeter.trigger()
    result = voltmeter.fetch()
    print(f"Triggered measurement result: {result:.6f} V")
    
    # Error checking
    print("\n=== Error Status ===")
    error_code, error_msg = voltmeter.get_error()
    if error_code == 0:
        print("No errors")
    else:
        print(f"Error {error_code}: {error_msg}")
    
    # Cleanup
    voltmeter.close()
    print("\nInstrument disconnected.")

if __name__ == "__main__":
    print("Keithley 2182A Driver Example")
    print("=============================")
    print("Note: This is a demonstration script.")
    print("Connect to a real instrument to see actual measurements.\n")
    
    # In a real scenario, uncomment the following line:
    # main()
    
    print("Example script completed successfully!")
    print("\nKey features demonstrated:")
    print("- Basic voltage measurement configuration")
    print("- Low noise vs fast measurement optimization")
    print("- MEASure and FETCh command usage")
    print("- Temperature measurement setup")
    print("- Trigger system configuration")
    print("- Status monitoring and error checking")
    print("- Statistical analysis of measurements")