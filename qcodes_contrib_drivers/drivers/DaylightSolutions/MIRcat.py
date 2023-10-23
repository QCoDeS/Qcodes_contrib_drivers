# -*- coding: utf-8 -*-
"""QCoDeS-Driver for DRS Daylight Solutions Ultra-broadly tunable mid-IR
external cavity CW/Pulsed MIRcat laser system:
https://daylightsolutions.com/product/mircat/

This driver relies on the MIRcatSDK. It requires a Windows system.

Authors:
    Julien Barrier, <julien@julienbarrier.eu>
"""

import logging
import time
import sys
import ctypes
from typing import Optional, Any, Sequence
from functools import partial

from qcodes import Instrument, Parameter
from qcodes import validators as vals

log = logging.getLogger(__name__)


class DRSDaylightSolutions_MIRcat(Instrument):
    """
    Class to represent a DaylightSolutions MIRcat tunable mid-IR laser QCL
    system.

    status: beta-version

    Args:
        name: name for the instrument
        dll_path: path to the MIRcatSDK driver dll library file. Defaults to None.
        wavelength: sequence of 2-tuple for the wavelength boundaries of all chips.
    """
    dll_path = 'C:\\MIRcat_laser\\libs\\x64\\MIRcatSDK.dll'

    _GET_STATUS = {
        0: 'unarmed',
        1: 'armed and not emitting',
        2: 'armed and emitting'
    }

    _GET_ERROR = {
        1: 'Unsupported `commType` for communication and transport',
        32: 'MIRcat controller initialisation failed *[System Error]*',
        64: 'Arm/Disarm failure *[System Error]*',
        65: 'Start/Tune failure *[System Error]*',
        66: 'Interlocks/Keyswitch not set',
        67: 'Stop scan failure *[System Error]*',
        68: 'Pause scan failure *[System Error]*',
        69: 'Resume scan failure *[System Error]*',
        70: 'Manual step scan failure *[System Error]*',
        71: 'Start sweep scan failure *[System Error]*',
        72: 'Start step/measure scan failure *[System Error]*',
        73: 'Index out of bounds',
        74: 'Start multi-spectral scan failure *[System Error]*',
        75: 'Too many elements',
        76: 'Not enough elements',
        77: 'Buffer too small for the character array',
        78: 'Favourite name not recognised',
        79: 'Favourite recall failure',
        80: 'Wavelength out of the valid tuning range',
        81: 'No scan in progress',
        82: 'Failure to enable the laser emission *[System Error]*',
        83: 'Emission already off',
        84: 'Failure to disable the laser emission *[System Error]*',
        85: 'Emission already on',
        86: 'Specified pulse rate out of range',
        87: 'Specified pulse width out of range',
        88: 'Specified current out of range',
        89: 'Fuuilure to save the QCL settings *[System Error]*',
        90: 'Specified QCL out of range. Must be comprised between 1 and 4',
        91: 'Laser already armed',
        92: 'Laser already disarmed',
        93: 'Laser not armed',
        94: 'Laser not tuned',
        95: 'System not operating at the set temperature *[System Error]*',
        96: 'Specified QCL does not support CW',
        97: 'Invalid laser mode',
        98: 'Temperature out of range',
        99: 'Failure to power off the laser *[System Error]*',
        100: 'Communication error *[System Error]*',
        101: 'MIRcat not initialised',
        102: 'MIRcat already created',
        103: 'Failure to start a sweep-advanced scan *[System Error]*',
        104: 'Failure to inject a process trigger *[System Error]*',
    }

    def __init__(self,
                 name: str,
                 dll_path: Optional[str] = None,
                 **kwargs: Any) -> None:
        super().__init__(name, **kwargs)
        

        if sys.platform != 'win32':
            self._dll: Any = None
            raise OSError('MIRcat only works on Windows')
        else:
            self._dll = ctypes.cdll.LoadLibrary(dll_path or self.dll_path)

        # Initialise MIRcatSDK & connect
        self._execute('MIRcatSDK_Initialize')
        self._num_qcl = ctypes.c_uint8()
        self._execute('MIRcatSDK_GetNumInstalledQcls',
                      [ctypes.byref(self._num_qcl)])
        self._is_interlock_set = ctypes.c_bool(False)
        self._execute('MIRcatSDK_IsInterlockedStatusSet',
                      [ctypes.byref(self._is_interlock_set)])
        self._is_keyswitch_set = ctypes.c_bool(False)
        self._execute('MIRcatSDK_IsKeySwitchStatusSet',
                      [ctypes.byref(self._is_keyswitch_set)])
        self._limits_chip1 = self.get_limits(1)
        self._limits_chip2 = self.get_limits(2)
        self._limits_chip3 = self.get_limits(3)
        self._limits_chip4 = self.get_limits(4)
        self._range_chip1: tuple[float, float] = self.get_ranges(1)
        self._range_chip2: tuple[float, float] = self.get_ranges(2)
        self._range_chip3: tuple[float, float] = self.get_ranges(3)
        self._range_chip4: tuple[float, float] = self.get_ranges(4)

        self.status = Parameter(
            'status',
            label='Status of the QCL',
            set_cmd=self._set_status,
            get_cmd=self._get_status,
            vals=vals.Ints(0, 2),
            instrument=self
        )

        self.wavelength = Parameter(
            'wavelength',
            label='QCL wavelength',
            get_cmd=self._get_wavelength,
            set_cmd=self._set_wavelength,
            vals=vals.Numbers(self._range_chip1[0], self._range_chip4[1]),
            unit='m',
            instrument=self
        )

        self.wavenumber = Parameter(
            'wavenumber',
            label='QCL wavenumber',
            get_cmd=self._get_wavenumber,
            set_cmd=self._set_wavenumber,
            vals=vals.Numbers(1/self._range_chip4[1]/100, 1/self._range_chip1[0]/100),
            unit='cm' + '\u207b\u00b9',
            instrument=self
        )

        self.chip = Parameter(
            'chip',
            label='chip currently in used',
            get_cmd=self._get_chip,
            get_parser=int,
            vals=vals.Ints(1, 4),
            instrument=self
        )

        self.T1 = Parameter(
            'T1',
            label='Temperature of chip 1',
            get_cmd=partial(self._get_temperature, chip=1),
            vals=vals.Numbers(),
            unit='\u00b0'+'C',
            instrument=self
        )

        self.T2 = Parameter(
            'T2',
            label='Temperature of chip 2',
            get_cmd=partial(self._get_temperature, chip=2),
            vals=vals.Numbers(),
            unit='\u00b0'+'C',
            instrument=self
        )

        self.T3 = Parameter(
            'T3',
            label='Temperature of chip 3',
            get_cmd=partial(self._get_temperature, chip=3),
            vals=vals.Numbers(),
            unit='\u00b0'+'C',
            instrument=self
        )

        self.T4 = Parameter(
            'T4',
            label='Temperature of chip 4',
            get_cmd=partial(self._get_temperature, chip=4),
            vals=vals.Numbers(),
            unit='\u00b0'+'C',
            instrument=self
        )

        self.pulse_rate_1 = Parameter(
            'pulse_rate_1',
            label='Pulse rate for chip 1',
            get_cmd=partial(self._get_pulse_rate, chip=1),
            set_cmd=partial(self._set_pulse_rate, chip=1),
            vals=vals.Numbers(max_value=self._limits_chip1[0]),
            unit='Hz',
            instrument=self
        )

        self.pulse_rate_2 = Parameter(
            'pulse_rate_2',
            label='Pulse rate for chip 2',
            get_cmd=partial(self._get_pulse_rate, chip=2),
            set_cmd=partial(self._set_pulse_rate, chip=2),
            vals=vals.Numbers(max_value=self._limits_chip2[0]),
            unit='Hz',
            instrument=self
        )

        self.pulse_rate_3 = Parameter(
            'pulse_rate_3',
            label='Pulse rate for chip 3',
            get_cmd=partial(self._get_pulse_rate, chip=3),
            set_cmd=partial(self._set_pulse_rate, chip=3),
            vals=vals.Numbers(max_value=self._limits_chip3[0]),
            unit='Hz',
            instrument=self
        )

        self.pulse_rate_4 = Parameter(
            'pulse_rate_4',
            label='Pulse rate for chip 4',
            get_cmd=partial(self._get_pulse_rate, chip=4),
            set_cmd=partial(self._set_pulse_rate, chip=4),
            vals=vals.Numbers(max_value=self._limits_chip4[0]),
            unit='Hz',
            instrument=self
        )

        self.pulse_width_1 = Parameter(
            'pulse_width_1',
            label='Pulse width for chip 1',
            get_cmd=partial(self._get_pulse_width, chip=1),
            set_cmd=partial(self._set_pulse_width, chip=1),
            vals=vals.Numbers(max_value=self._limits_chip1[1]),
            unit='s',
            instrument=self
        )

        self.pulse_width_2 = Parameter(
            'pulse_width_2',
            label='Pulse width for chip 2',
            get_cmd=partial(self._get_pulse_width, chip=2),
            set_cmd=partial(self._set_pulse_width, chip=2),
            vals=vals.Numbers(max_value=self._limits_chip2[1]),
            unit='s',
            instrument=self
        )

        self.pulse_width_3 = Parameter(
            'pulse_width_3',
            label='Pulse width for chip 3',
            get_cmd=partial(self._get_pulse_width, chip=3),
            set_cmd=partial(self._set_pulse_width, chip=3),
            vals=vals.Numbers(max_value=self._limits_chip3[1]),
            unit='s',
            instrument=self
        )

        self.pulse_width_4 = Parameter(
            'pulse_width_4',
            label='Pulse width for chip 4',
            get_cmd=partial(self._get_pulse_width, chip=4),
            set_cmd=partial(self._set_pulse_width, chip=4),
            vals=vals.Numbers(max_value=self._limits_chip4[1]),
            unit='s',
            instrument=self
        )

        self.pulse_current_1 = Parameter(
            'pulse_current_1',
            label='Pulse current for chip 1',
            get_cmd=partial(self._get_pulse_current, chip=1),
            set_cmd=partial(self._set_pulse_current, chip=1),
            vals=vals.Numbers(max_value=self._limits_chip1[3]),
            unit='A',
            instrument=self
        )

        self.pulse_current_2 = Parameter(
            'pulse_current_2',
            label='Pulse current for chip 2',
            get_cmd=partial(self._get_pulse_current, chip=2),
            set_cmd=partial(self._set_pulse_current, chip=2),
            vals=vals.Numbers(max_value=self._limits_chip2[3]),
            unit='A',
            instrument=self
        )
        self.pulse_current_3 = Parameter(
            'pulse_current_3',
            label='Pulse current for chip 3',
            get_cmd=partial(self._get_pulse_current, chip=3),
            set_cmd=partial(self._set_pulse_current, chip=3),
            vals=vals.Numbers(max_value=self._limits_chip3[3]),
            unit='A',
            instrument=self
        )
        self.pulse_current_4 = Parameter(
            'pulse_current_4',
            label='Pulse current for chip 4',
            get_cmd=partial(self._get_pulse_current, chip=4),
            set_cmd=partial(self._set_pulse_current, chip=4),
            vals=vals.Numbers(max_value=self._limits_chip4[3]),
            unit='A',
            instrument=self
        )
        
        self.connect_message()

    def get_pulse_parameters(self, chip: int = 0) -> tuple:
        """Get all pulse parameters for a given QCL chip.

        Args:
            chip (int, optional). Defaults to =0 (active chip).

        Returns:
            tuple: (pulse_rate (Hz), pulse_width (s), current (A))
        """
        tup = (
            self._get_pulse_rate(chip),
            self._get_pulse_width(chip),
            self._get_pulse_current(chip)
        )
        return tup

    def set_pulse_parameters(self,
                             pulse_rate: float,
                             pulse_width: float,
                             current: float,
                             chip: int) -> None:
        """Set pulse parameters for the QCL.

        Args:
            pulse_rate (float): pulse rate in Hz
            pulse_width (float): pulse width in s
            current (float): current in A
            chip (int): QCL chip
        """
        self.log.info('Set the following pulse parameters for QCL chip'
                      f'{chip}:\npulse rate: {pulse_rate}, pulse width: '
                      f'{pulse_width}, current: {current}.')
        self._execute('MIRcatSDK_SetQCLParams',
                      [ctypes.c_uint8(chip),
                       ctypes.c_float(pulse_rate),
                       ctypes.c_float(pulse_width*1e9),
                       ctypes.c_float(current*1e3)])

    def get_limits(self, chip: int = 0) -> tuple[float, ...]:
        """Get the limits for a given QCL chip.

        Args:
            chip (int, optional). Defaults to =0 (active chip).

        Returns:
            tuple: (pulse_rate_max (Hz), pulse_width_max (s), duty_cycle_max,
            current_max(A))
        """
        if chip == 0:
            units = ctypes.c_uint8()
            tuned_ww = ctypes.c_float()
            _chip = ctypes.c_uint8()
            self._execute('MIRcatSDK_GetTuneWW',
                          [ctypes.byref(tuned_ww),
                           ctypes.byref(units),
                           ctypes.byref(_chip)])
            chip = _chip.value
        self.log.info(f'Get limits for QCL chip {chip}.')
        pulse_rate_max = ctypes.c_float()
        pulse_width_max = ctypes.c_float()
        duty_cycle_max = ctypes.c_uint16()
        current_max = ctypes.c_float()

        self._execute('MIRcatSDK_GetQCLPulseLimits',
                      [chip,
                       ctypes.byref(pulse_rate_max),
                       ctypes.byref(pulse_width_max),
                       ctypes.byref(duty_cycle_max)])
        self._execute('MIRcatSDK_GetQCLMaxPulsedCurrent',
                      [chip, ctypes.byref(current_max)])
        return (pulse_rate_max.value, pulse_width_max.value/1e9,
                duty_cycle_max.value, current_max.value/1e3)

    def arm(self) -> None:
        """Arm the MIRcat QCL system.
        """
        self.log.info('Arm the MIRcat QCL system.')
        at_temperature = ctypes.c_bool(False)
        is_armed = ctypes.c_bool(False)
        self._execute('MIRcatSDK_IsLaserArmed', [ctypes.byref(is_armed)])
        if not is_armed.value:
            self._execute('MIRcatSDK_ArmDisarmLaser')

        while not is_armed.value:
            self._execute('MIRcatSDK_IsLaserArmed', [ctypes.byref(is_armed)])
            time.sleep(1)

        self._execute('MIRcatSDK_AreTECsAtSetTemperature',
                      [ctypes.byref(at_temperature)])
        tec_current = ctypes.c_uint16(0)
        qcl_temp = ctypes.c_float(0)
        num_qcl = ctypes.c_uint8()
        self._execute('MIRcatSDK_GetNumInstalledQcls', [ctypes.byref(num_qcl)])

        while not at_temperature.value:
            for i in range(0, num_qcl.value):
                self._execute('MIRcatSDK_GetQCLTemperature',
                              [ctypes.c_uint8(i+1), ctypes.byref(qcl_temp)])
                self._execute('MIRcatSDK_GetTecCurrent',
                              [ctypes.c_uint8(i+1), ctypes.byref(tec_current)])
            self._execute('MIRcatSDK_AreTECsAtSetTemperature',
                          [ctypes.byref(at_temperature)])
            time.sleep(.1)
            
    def disarm(self) -> None:
        """Disarm the MIRcat QCL system.
        """
        self.log.info('Disarm the MIRcat QCL system.')
        is_armed = ctypes.c_bool()
        is_emitting = ctypes.c_bool()
        self._execute('MIRcatSDK_IsEmissionOn', [ctypes.byref(is_emitting)])
        self._execute('MIRcatSDK_IsLaserArmed', [ctypes.byref(is_armed)])
        if is_emitting.value:
            self._execute('MIRcatSDK_TurnEmissionOff')
            while is_emitting.value:
                self._execute('MIRcatSDK_IsEmissionOn', [ctypes.byref(is_emitting)])
                time.sleep(1)
        if is_armed.value:
            self._execute('MIRcatSDK_DisarmLaser')
            while is_armed.value:
                self._execute('MIRcatSDK_IsLaserArmed', [ctypes.byref(is_armed)])
                time.sleep(1)

    def get_ranges(self, chip: int = 0) -> tuple[float, float]:
        """Get the acceptable range for a given QCL chip.

        Args:
            chip (int, optional). Defaults to 0.

        Returns:
            tuple: (pf_min_range (m), pf_max_range (m))
        """
        if chip == 0:
            units = ctypes.c_uint8()
            tuned_ww = ctypes.c_float()
            _chip = ctypes.c_uint8()
            self._execute('MIRcatSDK_GetTuneWW',
                          [ctypes.byref(tuned_ww),
                           ctypes.byref(units),
                           ctypes.byref(_chip)])
            chip = _chip.value
        self.log.info(f'Get range for QCL QCL chip {chip}.')
        pf_min_range = ctypes.c_float()
        pf_max_range = ctypes.c_float()
        pb_units = ctypes.c_uint8()

        self._execute('MIRcatSDK_GetQclTuningRange',
                      [chip, ctypes.byref(pf_min_range),
                       ctypes.byref(pf_max_range),
                       ctypes.byref(pb_units)])
        return (pf_min_range.value*1e-6, pf_max_range.value*1e-6)

    def check_tune(self) -> float:
        """Check the QCL tune.
        """
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('Check tune.')
        is_tuned = ctypes.c_bool(False)
        tuned_ww = ctypes.c_float()
        qcl = ctypes.c_uint8()
        units = ctypes.c_uint8()
        while not is_tuned.value:
            self._execute('MIRcatSDK_IsTuned', [ctypes.byref(is_tuned)])
            self._execute('MIRcatSDK_GetTuneWW',
                          [ctypes.byref(tuned_ww),
                           ctypes.byref(units),
                           ctypes.byref(qcl)])
        if units == ctypes.c_ubyte(1):
            return tuned_ww.value*1e-6
        elif units == ctypes.c_ubyte(2):
            return 1e2/tuned_ww.value  # convert from cm-1 to m
        else:
            raise ValueError

    def get_idn(self) -> dict:
        idparts = [
            'DRS Daylight Solutions', 'MIRcat',
            None, self._get_api_version()
        ]
        return dict(zip(('vendor', 'model', 'serial', 'firmware'), idparts))

    def _execute(self, func: str, params: Sequence = []) -> int:
        ret = self._dll.__getattr__(func)(*params)
        return self._check_error(ret)

    def _check_error(self, ret: int):
        if not ret:
            return None
        if self._GET_ERROR[ret][-16:] == '*[System Error]*':
            raise RuntimeError(self._GET_ERROR[ret][:-16])
        else:
            raise ValueError(self._GET_ERROR[ret])

    def _get_api_version(self) -> str:
        self.log.info('Get API version.')
        major = ctypes.c_uint16()
        minor = ctypes.c_uint16()
        patch = ctypes.c_uint16()
        self._execute('MIRcatSDK_GetAPIVersion',
                      [ctypes.byref(major),
                       ctypes.byref(minor),
                       ctypes.byref(patch)])
        return f'{major.value}.{minor.value}.{patch.value}'

    def _get_status(self) -> str:
        self.log.info('Get status.')
        is_armed = ctypes.c_bool(True)
        is_emitting = ctypes.c_bool(True)
        self._execute('MIRcatSDK_IsLaserArmed', [ctypes.byref(is_armed)])
        time.sleep(0.05)
        self._execute('MIRcatSDK_IsEmissionOn', [ctypes.byref(is_emitting)])
        res = int(is_armed.value) + int(is_emitting.value)
        return self._GET_STATUS[res]

    def _set_status(self, mode: int) -> None:
        """
        Args:
            mode (int): see dictionary of allowed values _GET_SATUS
        """
        if mode in self._GET_STATUS.keys():
            self.log.info('Set device remote status to' +
                          self._GET_STATUS[mode] + '.')
            is_armed = ctypes.c_bool()
            is_emitting = ctypes.c_bool()
            self._execute('MIRcatSDK_IsLaserArmed', [ctypes.byref(is_armed)])
            time.sleep(0.05)
            self._execute('MIRcatSDK_IsEmissionOn',
                          [ctypes.byref(is_emitting)])
            state = int(is_armed.value) + int(is_emitting.value)

            if not state and mode:
                self.arm()
                time.sleep(.05)
                if mode == 2:
                    self._execute('MIRcatSDK_TurnEmissionOn')
            elif not mode and state:
                if state == 2:
                    self._execute('MIRcatSDK_TurnEmissionOff')
                    time.sleep(.05)
                self._execute('MIRcatSDK_DisarmLaser')
                time.sleep(.05)
            elif mode == 2 and state == 1:
                self._execute('MIRcatSDK_TurnEmissionOn')
                time.sleep(.05)
            elif mode == 1 and state == 2:
                self._execute('MIRcatSDK_TurnEmissionOff')
                time.sleep(.05)
        else:
            print('Invalid mode inserted.')

    def _get_wavelength(self) -> float:
        self.log.info('Get wavelength.')
        actual_ww = ctypes.c_float()
        units = ctypes.c_uint8()
        light_valid = ctypes.c_bool()
        tuned_ww = ctypes.c_float()
        qcl = ctypes.c_uint8()
        self._execute('MIRcatSDK_GetActualWW',
                      [ctypes.byref(actual_ww),
                       ctypes.byref(units),
                       ctypes.byref(light_valid)])
        self._execute('MIRcatSDK_GetTuneWW',
                      [ctypes.byref(tuned_ww),
                       ctypes.byref(units),
                       ctypes.byref(qcl)])
        return actual_ww.value/1e6

    def _get_wavenumber(self):
        self.log.info('Get wavenumber.')
        actual_ww = ctypes.c_float()
        units = ctypes.c_uint8()
        light_valid = ctypes.c_bool()
        tuned_ww = ctypes.c_float()
        qcl = ctypes.c_uint8()
        self._execute('MIRcatSDK_GetActualWW',
                      [ctypes.byref(actual_ww),
                       ctypes.byref(units),
                       ctypes.byref(light_valid)])
        self._execute('MIRcatSDK_GetTuneWW',
                      [ctypes.byref(tuned_ww),
                       ctypes.byref(units),
                       ctypes.byref(qcl)])
        if actual_ww.value < 6:
            wavenum = 1e4/tuned_ww.value  # from um to cm-1
        else:
            wavenum = 1e4/actual_ww.value
        return wavenum

    def _get_temperature(self, chip: int) -> float:
        self.log.info(f'Get temperature of QCL chip {chip}.')
        temp = ctypes.c_float()
        self._execute('MIRcatSDK_GetQCLTemperature',
                      [chip, ctypes.byref(temp)])
        return temp.value
    
    def _get_pulse_rate(self, chip: int = 0) -> float:
        if chip == 0:
            units = ctypes.c_uint8()
            tuned_ww = ctypes.c_float()
            _chip = ctypes.c_uint8()
            self._execute('MIRcatSDK_GetTuneWW',
                          [ctypes.byref(tuned_ww),
                           ctypes.byref(units),
                           ctypes.byref(_chip)])
            chip = _chip.value
        self.log.info(f'Get pulse rate for QCL chip {chip}.')
        pulse_rate = ctypes.c_float()
        self._execute('MIRcatSDK_GetQCLPulseRate',
                      [ctypes.c_uint8(chip), ctypes.byref(pulse_rate)])
        return pulse_rate.value

    def _get_pulse_width(self, chip: int = 0) -> float:
        if chip == 0:
            units = ctypes.c_uint8()
            tuned_ww = ctypes.c_float()
            _chip = ctypes.c_uint8()
            self._execute('MIRcatSDK_GetTuneWW',
                          [ctypes.byref(tuned_ww),
                           ctypes.byref(units),
                           ctypes.byref(_chip)])
            chip = _chip.value
        self.log.info(f'Get pulse width for QCL chip {chip}.')
        pulse_width = ctypes.c_float()
        self._execute('MIRcatSDK_GetQCLPulseWidth',
                      [ctypes.c_uint8(chip), ctypes.byref(pulse_width)])
        return pulse_width.value/1e9

    def _get_pulse_current(self, chip: int = 0) -> float:
        if chip == 0:
            units = ctypes.c_uint8()
            tuned_ww = ctypes.c_float()
            _chip = ctypes.c_uint8()
            self._execute('MIRcatSDK_GetTuneWW',
                          [ctypes.byref(tuned_ww),
                           ctypes.byref(units),
                           ctypes.byref(_chip)])
            chip = _chip.value
        self.log.info(f'Get pulse current for QCL chip {chip}.')
        pulse_current = ctypes.c_float()
        self._execute('MIRcatSDK_GetQCLCurrent',
                      [ctypes.c_uint8(chip), ctypes.byref(pulse_current)])
        return pulse_current.value/1e3

    def _get_chip(self) -> int:
        """Check the active chip"""
        self.log.info('Get the active chip number.')
        actual_ww = ctypes.c_float()
        units = ctypes.c_uint8()
        light_valid = ctypes.c_bool()
        tuned_ww = ctypes.c_float()
        chip = ctypes.c_uint8()
        self._execute('MIRcatSDK_GetActualWW',
                      [ctypes.byref(actual_ww),
                       ctypes.byref(units),
                       ctypes.byref(light_valid)])
        self._execute('MIRcatSDK_GetTuneWW',
                      [ctypes.byref(tuned_ww),
                       ctypes.byref(units),
                       ctypes.byref(chip)])
        time.sleep(.05)
        return chip.value

    def _set_pulse_rate(self, pulse_rate: float, chip: int = 0) -> None:
        if chip == 0:
            units = ctypes.c_uint8()
            tuned_ww = ctypes.c_float()
            _chip = ctypes.c_uint8()
            self._execute('MIRcatSDK_GetTuneWW',
                          [ctypes.byref(tuned_ww),
                           ctypes.byref(units),
                           ctypes.byref(_chip)])
            chip = _chip.value

        self.log.info(f'Set pulse rate to {pulse_rate} on QCL chip {chip}.')
        pulse_width = ctypes.c_float()
        pulse_current = ctypes.c_float()

        self._execute('MIRcatSDK_GetQCLPulseWidth',
                      [ctypes.c_uint8(chip), ctypes.byref(pulse_width)])
        time.sleep(.05)
        self._execute('MIRcatSDK_GetQCLCurrent',
                      [ctypes.c_uint8(chip), ctypes.byref(pulse_current)])
        time.sleep(.05)
        self._execute('MIRcatSDK_SetQCLParams',
                      [ctypes.c_uint8(chip),
                       ctypes.c_float(pulse_rate),
                       ctypes.c_float(pulse_width.value),
                       ctypes.c_float(pulse_current.value)])

    def _set_pulse_width(self, pulse_width: float, chip: int = 0) -> None:
        if chip == 0:
            units = ctypes.c_uint8()
            tuned_ww = ctypes.c_float()
            _chip = ctypes.c_uint8()
            self._execute('MIRcatSDK_GetTuneWW',
                          [ctypes.byref(tuned_ww),
                           ctypes.byref(units),
                           ctypes.byref(_chip)])
            chip = _chip.value

        self.log.info(f'Set pulse width to {pulse_width} on QCL chip {chip}.')
        pulse_rate = ctypes.c_float()
        pulse_current = ctypes.c_float()

        self._execute('MIRcatSDK_GetQCLPulseRate',
                      [ctypes.c_uint8(chip), ctypes.byref(pulse_rate)])
        time.sleep(.05)
        self._execute('MIRcatSDK_GetQCLCurrent',
                      [ctypes.c_uint8(chip), ctypes.byref(pulse_current)])
        time.sleep(.05)
        self._execute('MIRcatSDK_SetQCLParams',
                      [ctypes.c_uint8(chip),
                       ctypes.c_float(pulse_rate.value),
                       ctypes.c_float(pulse_width*1e9),
                       ctypes.c_float(pulse_current.value)])

    def _set_pulse_current(self, pulse_current: float, chip: int = 0) -> None:
        if chip == 0:
            units = ctypes.c_uint8()
            tuned_ww = ctypes.c_float()
            _chip = ctypes.c_uint8()
            self._execute('MIRcatSDK_GetTuneWW',
                          [ctypes.byref(tuned_ww),
                           ctypes.byref(units),
                           ctypes.byref(_chip)])
            chip = _chip.value

        self.log.info(f'Set pulse current to {pulse_current} on QCL chip '
                      f'{chip}.')
        pulse_rate = ctypes.c_float()
        pulse_width = ctypes.c_float()

        self._execute('MIRcatSDK_GetQCLPulseRate',
                      [ctypes.c_uint8(chip), ctypes.byref(pulse_rate)])
        time.sleep(.05)
        self._execute('MIRcatSDK_GetQCLPulseWidth',
                      [ctypes.c_uint8(chip), ctypes.byref(pulse_width)])
        time.sleep(.05)
        self._execute('MIRcatSDK_SetQCLParams',
                      [ctypes.c_uint8(chip),
                       ctypes.c_float(pulse_rate.value),
                       ctypes.c_float(pulse_width.value),
                       ctypes.c_float(pulse_current*1e3)])

    def _set_wavelength(self, wavelength: float, chip: int = 0) -> None:
        wavelength = wavelength*1e6
        if chip == 0:
            if wavelength <= self._range_chip1[1]:
                chip = 1
            elif self._range_chip2[0] < wavelength <= self._range_chip2[1]:
                chip = 2
            elif self._range_chip3[0] < wavelength <= self._range_chip3[1]:
                chip = 3
            elif self._range_chip4[0] < wavelength:
                chip = 4
            else:
                raise ValueError('selected wavelength is not supported')

        self.log.info(f'Set wavelength to {wavelength} on QCL chip {chip}.')
        self._execute('MIRcatSDK_TuneToWW',
                      [ctypes.c_float(wavelength),
                       ctypes.c_ubyte(1),
                       ctypes.c_uint8(chip)])
        self._get_wavenumber()
        
    def _set_wavenumber(self, wavenumber: float, chip: int = 0) -> None:
        if chip == 0:
            if wavenumber >= 1/self._range_chip4[1]/100:
                chip = 4
            elif 1/self._range_chip3[0]/100 > wavenumber >= 1/self._range_chip3[1]/100:
                chip = 3
            elif 1/self._range_chip2[0]/100 > wavenumber >= 1/self._range_chip2[1]/100:
                chip = 2
            elif 1/self._range_chip1[0]/100 > wavenumber:
                chip = 1
            else:
                raise ValueError(f'selected wavenumber {wavenumber} is not supported')

        self.log.info(f'Set wavenumber to {wavenumber} on QCL chip {chip}.')
        self._execute('MIRcatSDK_TuneToWW',
                      [ctypes.c_float(wavenumber), ctypes.c_ubyte(2),
                       ctypes.c_uint8(chip)])
        self._get_wavelength()
