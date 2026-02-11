"""Driver for NanoVNA H4

Written by Edward Laird (http://wp.lancs.ac.uk/laird-group/).

A documentation notebook is in the docs/examples/ directory.
"""

import numpy as np
from typing import Any, Dict
import pynanovna

from qcodes import Instrument
from qcodes.parameters import ParameterWithSetpoints
from qcodes.validators import Arrays, Enum

class NanoVNA(Instrument):
    """
    QCoDeS driver for the NanoVNA vector network analyzer using pynanovna backend.

    Provides sweep control parameters, frequency axis, and S-parameter measurements (S11 and S21).
    """

    def __init__(self, name: str, **kwargs):
        """
        Initialize the NanoVNA instrument driver.

        Args:
            name: The name to use for this instrument instance.
            **kwargs: Additional keyword arguments forwarded to Instrument base class.
        """
        super().__init__(name, **kwargs)

        self._vna = pynanovna.VNA()

        self._start_freq = 1e6
        self._stop_freq = 1e9
        self._npts = 201

        # --- sweep control parameters ---
        self.add_parameter(
            "start_freq",
            unit="Hz",
            get_cmd=lambda: self._start_freq,
            set_cmd=self._set_start_freq,
        )

        self.add_parameter(
            "stop_freq",
            unit="Hz",
            get_cmd=lambda: self._stop_freq,
            set_cmd=self._set_stop_freq,
        )

        self.add_parameter(
            "npts",
            get_cmd=lambda: self._npts,
            set_cmd=self._set_npts,
            vals=Enum(11, 51, 101, 201, 301, 401),
        )

        # --- frequency axis ---
        self.add_parameter(
            "frequency",
            unit="Hz",
            get_cmd=self._get_frequency,
            vals=Arrays(shape=(self._npts,)),
        )

        # --- S11 components ---
        self.add_parameter(
            "s11_real",
            unit="",
            parameter_class=ParameterWithSetpoints,
            get_cmd=self._get_s11_real,
            setpoints=(self.frequency,),
            vals=Arrays(shape=(self._npts,)),
        )

        self.add_parameter(
            "s11_imag",
            unit="",
            parameter_class=ParameterWithSetpoints,
            get_cmd=self._get_s11_imag,
            setpoints=(self.frequency,),
            vals=Arrays(shape=(self._npts,)),
        )

        self.add_parameter(
            "s11_mag_lin",
            unit="",
            parameter_class=ParameterWithSetpoints,
            get_cmd=self._get_s11_mag_lin,
            setpoints=(self.frequency,),
            vals=Arrays(shape=(self._npts,)),
        )

        self.add_parameter(
            "s11_mag_db",
            unit="dB",
            parameter_class=ParameterWithSetpoints,
            get_cmd=self._get_s11_mag_db,
            setpoints=(self.frequency,),
            vals=Arrays(shape=(self._npts,)),
        )

        self.add_parameter(
            "s11_phase",
            unit="rad",
            parameter_class=ParameterWithSetpoints,
            get_cmd=self._get_s11_phase,
            setpoints=(self.frequency,),
            vals=Arrays(shape=(self._npts,)),
        )

        self.add_parameter(
            "s11",
            unit="",
            parameter_class=ParameterWithSetpoints,
            get_cmd=self._get_s11_complex,
            setpoints=(self.frequency,),
            vals=Arrays(shape=(self._npts,)),
        )


        # --- S21 components ---
        self.add_parameter(
            "s21_real",
            unit="",
            parameter_class=ParameterWithSetpoints,
            get_cmd=self._get_s21_real,
            setpoints=(self.frequency,),
            vals=Arrays(shape=(self._npts,)),
        )

        self.add_parameter(
            "s21_imag",
            unit="",
            parameter_class=ParameterWithSetpoints,
            get_cmd=self._get_s21_imag,
            setpoints=(self.frequency,),
            vals=Arrays(shape=(self._npts,)),
        )

        self.add_parameter(
            "s21_mag_lin",
            unit="",
            parameter_class=ParameterWithSetpoints,
            get_cmd=self._get_s21_mag_lin,
            setpoints=(self.frequency,),
            vals=Arrays(shape=(self._npts,)),
        )

        self.add_parameter(
            "s21_mag_db",
            unit="dB",
            parameter_class=ParameterWithSetpoints,
            get_cmd=self._get_s21_mag_db,
            setpoints=(self.frequency,),
            vals=Arrays(shape=(self._npts,)),
        )

        self.add_parameter(
            "s21_phase",
            unit="rad",
            parameter_class=ParameterWithSetpoints,
            get_cmd=self._get_s21_phase,
            setpoints=(self.frequency,),
            vals=Arrays(shape=(self._npts,)),
        )

        # --- complex S21 parameter ---
        self.add_parameter(
            "s21",
            unit="",
            parameter_class=ParameterWithSetpoints,
            get_cmd=self._get_s21_complex,
            setpoints=(self.frequency,),
            vals=Arrays(shape=(self._npts,))
        )

        self.connect_message()

    def _set_start_freq(self, val):
        """
        Set the start frequency for the sweep and update hardware.
        """
        self._start_freq = val
        self._update_hardware()

    def _set_stop_freq(self, val):
        """
        Set the stop frequency for the sweep and update hardware.
        """
        self._stop_freq = val
        self._update_hardware()

    def _set_npts(self, val):
        """
        Set the number of sweep points and update parameter validators accordingly,
        then update hardware.
        """
        self._npts = int(val)

        # Update validators for all parameters with this shape
        self.frequency.vals = Arrays(shape=(self._npts,))
        self.s11_real.vals = Arrays(shape=(self._npts,))
        self.s11_imag.vals = Arrays(shape=(self._npts,))
        self.s11_mag_lin.vals = Arrays(shape=(self._npts,))
        self.s11_mag_db.vals = Arrays(shape=(self._npts,))
        self.s11_phase.vals = Arrays(shape=(self._npts,))
        self.s11.vals = Arrays(shape=(self._npts,))
        self.s21_real.vals = Arrays(shape=(self._npts,))
        self.s21_imag.vals = Arrays(shape=(self._npts,))
        self.s21_mag_lin.vals = Arrays(shape=(self._npts,))
        self.s21_mag_db.vals = Arrays(shape=(self._npts,))
        self.s21_phase.vals = Arrays(shape=(self._npts,))
        self.s21.vals = Arrays(shape=(self._npts,))

        self._update_hardware()

    def _update_hardware(self):
        """
        Apply current sweep settings to the hardware and clear cached data to
        force a fresh sweep on next read.
        """
        self._vna.set_sweep(
            self._start_freq,
            self._stop_freq,
            self._npts,
        )
        # Clear cached data to force fresh sweep on next read
        if hasattr(self, '_cached_s21'):
            del self._cached_s21
        if hasattr(self, '_cached_freq'):
            del self._cached_freq

    def _perform_sweep(self):
        """
        Perform a sweep measurement, cache the frequency axis and S11, S21 data.
        Logs and raises exceptions if sweep fails.
        """
        try:
            s11, s21, freq = self._vna.sweep()
        except Exception as e:
            self.log.error(f"Sweep failed: {e}")
            raise
        self._cached_freq = freq
        self._cached_s11 = s11
        self._cached_s21 = s21

    def _get_frequency(self):
        """
        Get cached frequency axis data, performing a sweep if needed.

        Returns:
            np.ndarray: Frequency array for the sweep.
        """
        if not hasattr(self, '_cached_freq'):
            self._perform_sweep()
        return self._cached_freq

    def _get_s11_real(self):
        """
        Get real part of S11 parameter, performing a sweep if needed.

        Returns:
            np.ndarray: Real part of S11.
        """
        if not hasattr(self, '_cached_s21'):
            self._perform_sweep()
        return np.real(self._cached_s11)

    def _get_s11_imag(self):
        """
        Get imaginary part of S11 parameter, performing a sweep if needed.

        Returns:
            np.ndarray: Imaginary part of S11.
        """
        if not hasattr(self, '_cached_s21'):
            self._perform_sweep()
        return np.imag(self._cached_s11)

    def _get_s11_mag_lin(self):
        """
        Get linear magnitude of S11 parameter, performing a sweep if needed.

        Returns:
            np.ndarray: Linear magnitude of S11.
        """
        if not hasattr(self, '_cached_s21'):
            self._perform_sweep()
        return np.abs(self._cached_s11)

    def _get_s11_mag_db(self):
        """
        Get magnitude of S11 parameter in dB, performing a sweep if needed.

        Returns:
            np.ndarray: Magnitude of S11 in dB.
        """
        if not hasattr(self, '_cached_s21'):
            self._perform_sweep()
        mag = np.abs(self._cached_s11)
        mag = np.clip(mag, 1e-12, None)
        return 20 * np.log10(mag)

    def _get_s11_phase(self):
        """
        Get phase of S11 parameter in radians, performing a sweep if needed.

        Returns:
            np.ndarray: Phase of S11 in radians.
        """
        if not hasattr(self, '_cached_s21'):
            self._perform_sweep()
        return np.angle(self._cached_s11)

    def _get_s11_complex(self):
        """
        Get complex S11 parameter, performing a sweep if needed.

        Returns:
            np.ndarray: Complex S11 values.
        """
        if not hasattr(self, '_cached_s21'):
            self._perform_sweep()
        return self._cached_s11

    def _get_s21_real(self):
        """
        Get real part of S21 parameter, performing a sweep if needed.

        Returns:
            np.ndarray: Real part of S21.
        """
        if not hasattr(self, '_cached_s21'):
            self._perform_sweep()
        return np.real(self._cached_s21)

    def _get_s21_imag(self):
        """
        Get imaginary part of S21 parameter, performing a sweep if needed.

        Returns:
            np.ndarray: Imaginary part of S21.
        """
        if not hasattr(self, '_cached_s21'):
            self._perform_sweep()
        return np.imag(self._cached_s21)

    def _get_s21_mag_lin(self):
        """
        Get linear magnitude of S21 parameter, performing a sweep if needed.

        Returns:
            np.ndarray: Linear magnitude of S21.
        """
        if not hasattr(self, '_cached_s21'):
            self._perform_sweep()
        return np.abs(self._cached_s21)

    def _get_s21_mag_db(self):
        """
        Get magnitude of S21 parameter in dB, performing a sweep if needed.

        Returns:
            np.ndarray: Magnitude of S21 in dB.
        """
        if not hasattr(self, '_cached_s21'):
            self._perform_sweep()
        mag = np.abs(self._cached_s21)
        mag = np.clip(mag, 1e-12, None)
        return 20 * np.log10(mag)

    def _get_s21_phase(self):
        """
        Get phase of S21 parameter in radians, performing a sweep if needed.

        Returns:
            np.ndarray: Phase of S21 in radians.
        """
        if not hasattr(self, '_cached_s21'):
            self._perform_sweep()
        return np.angle(self._cached_s21)

    def _get_s21_complex(self):
        """
        Get complex S21 parameter, performing a sweep if needed.

        Returns:
            np.ndarray: Complex S21 values.
        """
        if not hasattr(self, '_cached_s21'):
            self._perform_sweep()
        return self._cached_s21

    def get_idn(self) -> Dict[str, Any]:
        """
        Return identification information for the instrument.

        Returns:
            dict: Dictionary with keys 'vendor', 'model', 'serial', and 'firmware'.
        """
        return dict(vendor="NanoVNA", model="NanoVNA", serial=None, firmware=self._vna.info()['Version'])

    def close(self):
        """
        Close connection to the NanoVNA instrument, kill the backend connection,
        clear cached data, and call base class close.
        """
        try:
            self._vna.kill()
        except Exception as e:
            self.log.warning(f"Exception when closing NanoVNA connection: {e}")

        # Clear cached data
        if hasattr(self, '_cached_s21'):
            del self._cached_s21
        if hasattr(self, '_cached_s11'):
            del self._cached_s11
        if hasattr(self, '_cached_freq'):
            del self._cached_freq

        super().close()
