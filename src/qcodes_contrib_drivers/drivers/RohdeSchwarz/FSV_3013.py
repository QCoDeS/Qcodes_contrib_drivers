import time
import time
from qcodes import VisaInstrument
from qcodes.utils.validators import Numbers, Enum
import numpy as np
from scipy.signal import find_peaks

class RFSpectrumAnalyzer(VisaInstrument):
    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, **kwargs)

        # Frequency parameters
        self.add_parameter('frequency', label='Center Frequency', unit='Hz',
                           get_cmd=self._get_numeric_value(':FREQ:CENT?'),
                           set_cmd=':FREQ:CENT {}',
                           vals=Numbers(1e6, 44e9))
        self.add_parameter('span', label='Frequency Span', unit='Hz',
                           get_cmd=self._get_numeric_value(':FREQ:SPAN?'),
                           set_cmd=':FREQ:SPAN {}',
                           vals=Numbers(1e3, 3.2e9))

        # Amplitude parameters
        self.add_parameter('amplitude', label='Amplitude', unit='dBm',
                           get_cmd=self._get_numeric_value(':DISP:WIND:TRAC:Y:SCAL:RLEV?'),
                           set_cmd=':DISP:WIND:TRAC:Y:SCAL:RLEV {}',
                           vals=Numbers(-120, 30))

        # Reference Level Control
        self.add_parameter('reference_level', label='Reference Level', unit='dBm',
                           get_cmd=self._get_numeric_value(':DISP:WIND:TRAC:Y:RLEV?'),
                           set_cmd=':DISP:WIND:TRAC:Y:RLEV {}',
                           vals=Numbers(-120, 30))

        # Bandwidth settings
        self.add_parameter('resolution_bandwidth', label='Resolution Bandwidth', unit='Hz',
                           get_cmd=self._get_numeric_value(':BAND:RES?'),
                           set_cmd=':BAND:RES {}',
                           vals=Numbers(1, 10e6))
        self.add_parameter('video_bandwidth', label='Video Bandwidth', unit='Hz',
                           get_cmd=self._get_numeric_value(':BAND:VID?'),
                           set_cmd=':BAND:VID {}',
                           vals=Numbers(1, 10e6))

        # Sweep settings
        self.add_parameter('sweep_time', label='Sweep Time', unit='s',
                           get_cmd=self._get_numeric_value(':SWE:TIME?'),
                           set_cmd=':SWE:TIME {}',
                           vals=Numbers(1e-6, 10000))
        self.add_parameter('sweep_mode', label='Sweep Mode',
                           get_cmd=self._get_enum_value(':INIT:CONT?'),
                           set_cmd=':INIT:CONT {}',
                           vals=Enum('ON', 'OFF'))

        # Trigger settings
        self.add_parameter('trigger_source', label='Trigger Source',
                           get_cmd=self._get_enum_value(':TRIG:SOUR?'),
                           set_cmd=':TRIG:SOUR {}',
                           vals=Enum('IMM', 'EXT', 'VID'))
        self.add_parameter('trigger_level', label='Trigger Level', unit='V',
                           get_cmd=self._get_numeric_value(':TRIG:LEV?'),
                           set_cmd=':TRIG:LEV {}',
                           vals=Numbers(-5, 5))

        # Correction settings
        self.add_parameter('correction_state', label='Correction State',
                           get_cmd=self._get_enum_value(':CORR:STAT?'),
                           set_cmd=':CORR:STAT {}',
                           vals=Enum('ON', 'OFF'))

        # Measurement settings
        self.add_parameter('measurement_state', label='Measurement State',
                           get_cmd=self._get_enum_value(':INIT:IMM?'),
                           set_cmd=':INIT:IMM')

        # Miscellaneous settings
        self.add_parameter('input_impedance', label='Input Impedance', unit='Ohm',
                           get_cmd=self._get_numeric_value(':INP:IMP?'),
                           set_cmd=':INP:IMP {}',
                           vals=Enum(50, 75))

        # Noise and Peak measurement settings
        self.add_parameter('noise_level_without_peak', label='Noise Level', unit='dBm',
                           get_cmd=lambda:self._get_noise_lvl_and_peaks()[0])
        self.add_parameter('peak_center', label='Peak Center', unit='Hz',
                           get_cmd=lambda:self._get_noise_lvl_and_peaks()[1])
        self.add_parameter('peak_height', label='Peak Height', unit='dBm',
                           get_cmd=lambda:self._get_noise_lvl_and_peaks()[2])
        self.add_parameter('peak_width', label='Peak Width', unit='Hz',
                           get_cmd=lambda:self._get_noise_lvl_and_peaks()[3])

        # Trace data parameters
        self.add_parameter('trace_frequencies',
                           label='Trace Frequencies',
                           unit='Hz',
                           get_cmd=self._get_trace_frequencies)

        self.add_parameter('trace_amplitudes',
                           label='Trace Amplitudes',
                           unit='dBm',
                           get_cmd=self._get_trace_amplitudes)

    def _get_numeric_value(self, cmd):
        """Fetch a value from the instrument and return it as a float."""
        return lambda: float(self.ask(cmd))

    def _get_enum_value(self, cmd):
        """Fetch a value from the instrument and return it as a string."""
        return lambda: self.ask(cmd).strip()

    def reset(self):
        """Resets the instrument to its default state."""
        self.write('*RST')

    def measure_power(self):
        """Performs a basic power measurement."""
        self.write(':INIT:IMM')
        return float(self.ask(':FETCH:POW:ACP?'))

    def get_trace(self):
        """Fetches the trace data from the instrument and calculates the frequency axis."""
        self.write(':FORM:TRAC ASC')
        center_frequency = float(self.frequency())
        span = float(self.span())

        # Start the sweep
        self.write(':INIT')

        # Add a waiting time of 1 second
        time.sleep(1)

        # Query operation complete to ensure sweep is done
        self.ask('*OPC?')

        # Fetch the trace data
        trace_data = self.ask(':TRAC:DATA? TRACE1')

        # Convert the acquired trace data into a list of floating-point numbers
        amplitudes = np.array([float(val) for val in trace_data.split(',')])

        # Calculate the corresponding frequency values
        num_points = len(amplitudes)
        frequencies = np.linspace(center_frequency - span/2, center_frequency + span/2, num_points)

        return frequencies, amplitudes

    def _get_noise_lvl_and_peaks(self):
        """Return mean noise level in the absence of a signal peak and peak parameters."""
        f, amplitudes = self.get_trace()
        try:
            pks = find_peaks(amplitudes, prominence=20, width=2)
            highest_peak_index = np.argmax(pks[1]["prominences"])
            peak_center = f[pks[0][highest_peak_index]]
            peak_height = amplitudes[pks[0][highest_peak_index]]
            peak_width = int(pks[1]["widths"][highest_peak_index])

            # Remove the peak region from noise calculation
            noise_data = np.delete(amplitudes, range(pks[0][highest_peak_index] - int(peak_width / 2 + 1), pks[0][highest_peak_index] + int(peak_width / 2 + 1)))
            noise_lvl = np.mean(noise_data)

        except Exception as e:
            print(f"Couldn't get peak for the data: {e}")
            noise_lvl = np.mean(amplitudes)
            peak_center = 0
            peak_width = 0
            peak_height = 0

        return noise_lvl, peak_center, peak_height, peak_width

    def _get_trace_frequencies(self):
        """Return the frequency axis for the current trace."""
        frequencies, _ = self.get_trace()
        return frequencies

    def _get_trace_amplitudes(self):
        """Return the amplitude data for the current trace."""
        _, amplitudes = self.get_trace()
        return amplitudes

    def close(self):
        """Override close to ensure proper disconnection."""
        self.write('SYST:LOC')
        super().close()
