from typing import Union
from functools import partial
import logging

import numpy as np

from qcodes.instrument.visa import VisaInstrument
from qcodes.instrument.parameter import ArrayParameter
import qcodes.utils.validators as vals

log = logging.getLogger(__name__)

_unit_map = {'Log Mag': 'dB',
             'Phase': 'degree',
             'Group Delay': None,
             'Smith': 'dim. less',
             'Polar': 'dim. less',
             'Lin mag': 'dim. less',
             'Real': None,
             'Imag': None,
             'SWR': 'dim. less'}


def CMTIntParser(value: str) -> int:
    """
    Small custom parser for ints

    Args:
        value: the VISA return string using exponential notation
    """
    return int(float(value))


class TraceNotReady(Exception):
    pass


class CMTS5048Trace(ArrayParameter):
    """
    Class to hold a the trace from the S5048 network analyzer

    Although the trace can have two values per frequency, this
    class only returns the first value
    """

    def __init__(self, name, instrument):
        super().__init__(name=name,
                         shape=(1,),  # is overwritten by prepare_trace
                         label='',  # is overwritten by prepare_trace
                         unit='',  # is overwritten by prepare_trace
                         setpoint_names=('Frequency',),
                         setpoint_labels=('Frequency',),
                         setpoint_units=('Hz',),
                         snapshot_get=False
                         )

        self._instrument = instrument

    def prepare_trace(self):
        """
        Update setpoints, units and labels
        """

        # we don't trust users to keep their fingers off the front panel,
        # so we query the instrument for all values

        fstart = self._instrument.start_freq()
        fstop = self._instrument.stop_freq()
        npts = self._instrument.trace_points()

        sps = np.linspace(fstart, fstop, npts)
        self.setpoints = (tuple(sps),)
        self.shape = (len(sps),)

        self.label = self._instrument.s_parameter()
        self.unit = _unit_map[self._instrument.display_format()]

        self._instrument._traceready = True

    def get_raw(self):
        """
        Return the trace
        """
        inst = self._instrument

        if not inst._traceready:
            raise TraceNotReady('Trace not ready. Please run prepare_trace.')

        inst.write('CALC:DATA:FDAT') 
        old_read_termination = inst.visa_handle.read_termination
        try:
            inst.visa_handle.read_termination = ''
            raw_resp = inst.visa_handle.read_raw()
        finally:
            inst.visa_handle.read_termination = old_read_termination

        first_points = B''
        
        for n in range((len(raw_resp)-4)//4):
            first_points += raw_resp[4:][2*n*4:(2*n+1)*4]

        dt = np.dtype('f')
        trace1 = np.fromstring(first_points, dtype=dt)


class CMTS5048(VisaInstrument):
    """
    This is the QCoDeS driver for the S5048 Network Analyzer
    """

    def __init__(self, name: str, address: str, **kwargs) -> None:
        super().__init__(name, address, terminator='\n', **kwargs)

        self.add_parameter(
            'start_freq',
            label='Sweep start frequency',
            unit='Hz',
            set_cmd=partial(self.invalidate_trace, 'SENS:FREQ:STAR {}'),
            get_cmd='SENS:FREQ:STAR?',
            get_parser=float,
            vals=vals.Numbers(20000, 4800000000))

        self.add_parameter(
            'stop_freq',
            label='Sweep stop frequency',
            unit='Hz',
            set_cmd=partial(self.invalidate_trace, 'SENS:FREQ:STOP {}'),
            get_cmd='SENS:FREQ:STOP?',
            get_parser=float,
            vals=vals.Numbers(20000, 4800000000))

        self.add_parameter(
            'averaging',
            label='Averaging state',
            set_cmd='SENS:AVER{}',
            get_cmd='SENS:AVER?',
            val_mapping={'ON': 1, 'OFF': 0})

        self.add_parameter(
            'number_of_averages',
            label='Number of averages',
            set_cmd='SENS:AVER:COUN{}',
            get_cmd='SENS:AVER:COUN?',
            get_parser=CMTIntParser,
            vals=vals.Ints(0, 999))

        self.add_parameter(
            'trace_points',
            label='Number of points in trace',
            set_cmd=partial(self.invalidate_trace, 'SENS:SWE:POIN{}'),
            get_cmd='SENS:SWE:POIN?',
            get_parser=CMTIntParser,
            vals=vals.Enum(3, 11, 26, 51, 101, 201, 401,
                           801, 1601))

        self.add_parameter(
            'sweep_time',
            label='Sweep time',
            set_cmd='SENS:SWE:POIN:TIME{}',
            get_cmd='SENS:SWE:POIN:TIME?',
            unit='s',
            get_parser=float,
            vals=vals.Numbers(0, 0.3),
            )

        self.add_parameter(
            'output_power',
            label='Output power',
            unit='dBm',
            set_cmd='SOUR:POW{}',
            get_cmd='SOUR:POW?',
            get_parser=float,
            vals=vals.Numbers(-80, 20))
        
        self.add_parameter(
            's_parameter',
            label='S-parameter',
            set_cmd=self._s_parameter_setter,
            get_cmd=self._s_parameter_getter)


        # DISPLAY / Y SCALE PARAMETERS
        self.add_parameter(
            'display_format',
            label='Display format',
            set_cmd=self._display_format_setter,
            get_cmd=self._display_format_getter)

        # TODO: update this on startup and via display format
        self.add_parameter(
            'display_reference',
            label='Display reference level',
            unit=None,  # will be set by display_format
            get_cmd='DISP:WIND:TRAC:Y:RLEV?',
            set_cmd='DISP:WIND:TRAC:Y:RLEV{}',
            get_parser=float,
            vals=vals.Numbers(-10e-18, 1e18))

        self.add_parameter(
            'display_scale',
            label='Display scale',
            unit=None,  # will be set by display_format
            get_cmd='DISP:WIND:TRAC:Y:PDIV?',
            set_cmd='DISP:WIND:TRAC:Y:PDIV{}',
            get_parser=float,
            vals=vals.Numbers(-10e-18, 1e18))

        self.add_parameter(
            name='trace',
            parameter_class=CMTS5048Trace)

        # Startup
        self.startup()
        self.connect_message()
        
    def reset(self) -> None:
        """
        Resets the instrument to factory default state
        """
        # use OPC to make sure we wait for operation to finish
        self.ask('*OPC?;SYST:PRES')

    def run_continously(self) -> None:
        """
        Set the instrument in run continously mode
        """
        self.write('INIT:CONT:ALL:ON')

    def run_N_times(self, N: int) -> None:
        """
        Run N sweeps and then hold. We wait for a response before returning
        """

        st = self.sweep_time.get_latest()

        if N not in range(1, 1000):
            raise ValueError('Can not run {} times.'.format(N) +
                             ' please select a number from 1-999.')

        # set a longer timeout, to not timeout during the sweep
        new_timeout = 1000*st*N + 1000

        with self.timeout.set_to(new_timeout):
            log.debug(f'Making {N} blocking sweeps, setting VISA timeout to {new_timeout/1000} s.')
            self.ask(f'*OPC?;NUMG{N}')

    def invalidate_trace(self, cmd: str,
                         value: Union[float, int, str]) -> None:
        """
        Wrapper for set_cmds that make the trace not ready
        """
        self._traceready = False
        self.write(cmd.format(value))

    def startup(self) -> None:
        self._traceready = False
        self.display_format(self.display_format())

    def _s_parameter_setter(self, param: str) -> None:
        """
        set_cmd for the s_parameter parameter
        """
        allowed_s_params = {'S11', 'S12', 'S21', 'S22'}
        if param not in allowed_s_params:
            raise ValueError(f"Cannot set s-parameter to {param}, should be one of {allowed_s_params}")

        # the trace labels changes
        self._traceready = False

        self.write(f"CALC:PAR:DEF \"{param}\"")

    def _s_parameter_getter(self) -> str:
        """
        get_cmd for the s_parameter parameter
        """
        for cmd in ['S11', 'S12', 'S21', 'S22']:
            resp = self.ask('CALC:PAR:DEF?')
            if resp in ['1', '1\n']:
                break

        return cmd.replace('?', '')

    def _display_format_setter(self, fmt: str) -> None:
        """
        set_cmd for the display_format parameter
        """
        val_mapping = {'Log Mag': 'MLOG',
                       'Phase': 'PHAS',
                       'Group Delay': 'GDEL',
                       'Smith': 'SMIT',
                       'Polar': 'POL',
                       'Lin Mag': 'MLIN',
                       'Real': 'REAL',
                       'Imag': 'IMAG',
                       'SWR': 'SWR'}

        if fmt not in val_mapping:
            raise ValueError(f"Cannot set display_format to {fmt}, should be one of {set(val_mapping.keys())}")

        self._traceready = False
        
        self.display_reference.unit = _unit_map[fmt]
        self.display_scale.unit = _unit_map[fmt] 
        
        self.write(f'CALC:FORM "{val_mapping[fmt]}"')

    def _display_format_getter(self) -> str:
        """
        get_cmd for the display_format parameter
        """
        val_mapping = {'MLOG': 'Log Mag',
                       'PHAS': 'Phase',
                       'GDEL': 'Group Delay',
                       'SMIT': 'Smith',
                       'POL': 'Polar',
                       'MLIN': 'Lin Mag',
                       'REAL': 'Real',
                       'IMAG': 'Imag',
                       'SWR': 'SWR'}

        # keep asking until we find the currently used format
        for cmd in val_mapping:
            resp = self.ask(f'CALC:FORM? "{cmd}"')
            if resp in {'1', '1\n'}:
                break

        return val_mapping[cmd]
