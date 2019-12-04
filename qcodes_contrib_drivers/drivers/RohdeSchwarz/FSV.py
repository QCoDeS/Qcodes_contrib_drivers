"""
Driver for Rhode & Schwartz Spectrum analyzer FSV series

Tested on FSV40-N, can probably be extended (or even used as is) for other devices in the FSV series.

Based on qtlab driver by
Russell Lake <russell.lake@aalto.fi>, 2013
Joonas Govenius <joonas.govenius@aalto.fi>, 2013
"""



import logging
import warnings
import time
from typing import Optional, List, Any
from functools import partial
import numpy as np
from qcodes import VisaInstrument, ArrayParameter
from qcodes.utils.validators import Numbers, Ints, Enum, Bool
from qcodes.utils.helpers import create_on_off_val_mapping as on_off


class FrequencySweep(ArrayParameter):
    """
        Data container for acquired sweep spectrum. Contains the frequency axis as setpoints.

        Args:
            name: parameter name
            instrument: instrument the parameter belongs to
            npts: number of points in the spectrum

        Methods:
              get_raw(): executes a sweep and returns power array
    """

    def __init__(self, name, instrument, npts):
        super().__init__(name, shape=(npts,),
                         instrument=instrument,
                         unit='dBm',
                         label='Magnitude',
                         setpoint_units=('Hz',),
                         setpoint_labels=('Frequency',),
                         setpoint_names=('Frequency',))

    def get_raw(self):
        powers = self._instrument.get_data(1)
        freqs = self._instrument.get_frequency_data(1)
        npts = len(freqs)
        self.setpoints = (tuple(freqs),)
        self.shape = (npts,)
        return powers


class RohdeSchwarz_FSV(VisaInstrument):
    """
    Driver for the Rohde & Schwarz FSV spectrum analyzer series.
    """

    def __init__(self, name: str, address: str, reset: bool=False, **kwargs):
        '''
        Initializes a R&S FSV, and communicates with the instrument.

        Input:
        name: Instrument name
        address: Address or alias of instrument
        reset: resets to default values
        **kwargs: passed to base class
        '''
        super().__init__(name=name, address=address, terminator="\n", **kwargs)

        self._freq_unit = 1
        self._freq_unit_symbol = 'Hz'

        self.add_parameter(name='spectrum',
                           npts=10,
                           parameter_class=FrequencySweep,
                           docstring="Get this parameter to measure the spectrum with current settings.",
                           )
        self.add_parameter(name='start_frequency',
                           vals=Numbers(0, 27e9),
                           get_parser=float,
                           get_cmd="SENS:FREQ:STAR?",
                           set_cmd="SENS:FREQ:STAR {0:.6E}",
                           unit='Hz',
                           )
        self.add_parameter(name='stop_frequency',
                           vals=Numbers(0, 27e9),
                           get_parser=float,
                           get_cmd="SENS:FREQ:STOP?",
                           set_cmd="SENS:FREQ:STOP {0:.6E}",
                           unit='Hz',
                           )
        self.add_parameter(name='center_frequency',
                           vals=Numbers(0, 27e9),
                           get_parser=float,
                           get_cmd="SENS:FREQ:CENT?",
                           set_cmd="SENS:FREQ:CENT {0:.6E}",
                           unit='Hz',
                           )
        self.add_parameter(name='num_points',
                           vals=Ints(101, 32001),
                           get_parser=int,
                           get_cmd="SWE:POIN?",
                           set_cmd="SWE:POIN {}",
                           docstring="Number of data points in the sweep.",
                           )
        self.add_parameter(name='span',
                           vals=Numbers(0, 27e9),
                           get_parser=float,
                           get_cmd="SENS:FREQ:SPAN?",
                           set_cmd="SENS:FREQ:SPAN {0:0.6E}",
                           unit='Hz',
                           )
        self.add_parameter(name='if_bandwidth',
                           get_parser=float,
                           get_cmd=self._get_if_bandwidth,
                           set_cmd=self._set_if_bandwidth,
                           unit=self._freq_unit_symbol,
                           )
        self.add_parameter(name='sweep_time',
                           get_parser=float,
                           get_cmd="SWE:TIME?",
                           unit='s',
                           )
        self.add_parameter(name='averaging',
                           val_mapping=on_off(on_val='ON', off_val='OFF'),
                           get_cmd=partial(self._read_on_off_value, "SENS:AVER?"),
                           set_cmd="SENS:AVER {}",
                           docstring="Boolean indicating if the averaging mode is on. The number of averages is"
                                        " set by the `average_count` parameter.",
                           )
        self.add_parameter(name='average_count',
                           vals=Ints(0, 2000),
                           get_parser=int,
                           get_cmd="SENS:AVER:COUN?",
                           set_cmd="SENS:AVER:COUN {}",
                           docstring="Number of times each data point is measured and averaged. "
                                        "`averaging` must be `True` for this to take effect.",
                           )
        self.add_parameter(name='sweeptime_auto',
                           val_mapping=on_off(on_val="ON", off_val="OFF"),
                           get_cmd=partial(self._read_on_off_value, "SWE:TIME:AUTO?"),
                           set_cmd="SWE:TIME:AUTO {}",
                           docstring="Boolean indicating if the sweep time is chosen automatically.",
                           )
        self.add_parameter(name='trigger_source',
                           vals=Enum(*tuple(["imm", "ext", "line", "tim", "rtcl", "man"])),
                           get_cmd=self._get_trigger_source,
                           set_cmd="TRIGGER:SEQUENCE:SOURCE {}",
                           docstring='Possible values: "imm": immediate (continuous), "ext": external, '
                                     '"line": line, "tim": periodic timer, "rtcl": real time clock, "man": manual '
                           )
        self.add_parameter(name='trigger_level',
                           vals=Numbers(-5, 5),
                           get_parser=float,
                           get_cmd="TRIG:LEV?",
                           set_cmd="TRIG:LEV {0:0.1f}",
                           unit="V",
                           )
        self.add_parameter(name='resolution_bandwidth',
                           vals=Numbers(1, 1e7),
                           get_parser=float,
                           get_cmd="SENS:BAND:RES?",
                           set_cmd="SENS:BAND:RES {0:0.6E}",
                           unit='Hz',
                           )
        self.add_parameter(name='resolution_bandwidth_auto',
                           val_mapping=on_off(on_val="ON", off_val="OFF"),
                           get_cmd=partial(self._read_on_off_value, "SENS:BAND:AUTO?"),
                           set_cmd="SENS:BAND:AUTO {}",
                           docstring="Boolean indicating if the resolution bandwidth is chosen automatically"
                                        " based on span.",
                           )
        self.add_parameter(name='video_bandwidth',
                           vals=Numbers(1, 1e7),
                           get_parser=float,
                           get_cmd="SENS:BAND:VID?",
                           set_cmd="SENS:BAND:VID {0:0.6E}",
                           unit='Hz',
                           )
        self.add_parameter(name='video_bandwidth_auto',
                           val_mapping=on_off(on_val="ON", off_val="OFF"),
                           get_cmd=partial(self._read_on_off_value, "SENS:BAND:VID:AUTO?"),
                           set_cmd="SENS:BAND:VID:AUTO {}",
                           docstring="Boolean indicating if video BW is automatically kept at 3x reolution BW.",
                           )
        self.add_parameter(name='continuous_sweep_mode',
                           val_mapping=on_off(on_val="ON", off_val="OFF"),
                           get_cmd=partial(self._read_on_off_value, "INIT:CONT?"),
                           set_cmd="INIT:CONT {}",
                           docstring="Boolean indicating if sweeping continuously or only when triggered.",
                           )
        self.add_parameter(name='external_reference',
                           get_parser=bool,
                           vals=Bool(),
                           get_cmd=self._get_external_reference,
                           set_cmd=self._set_external_reference,
                           docstring="Boolean indicating whether to use an external reference clock.",
                            )
        self.add_parameter(name='external_reference_frequency',
                           getparser=int,
                           get_cmd="SENS:ROSC:EXT:FREQ?",
                           set_cmd="SENS:ROSC:EXT:FREQ {0:.0f}",
                           unit='Hz',
                           )
        # self.add_parameter(name='source_status',
        #                    val_mapping=on_off(on_val="ON", off_val="OFF"),
        #                    get_cmd=partial(self._read_on_off_value, "OUTP:STAT?"),
        #                    set_cmd="OUTP:STAT {}",
        #                   )
        # self.add_parameter(name='measure_mode',
        #                    vals=Ints(1, 5),
        #                    get_parser=int,
        #                    get_cmd="INST:NSEL?",
        #                    set_cmd="INST:NSEL  {}",
        #                    )
        # self.add_parameter(name='source_power',
        #                    get_parser=float,
        #                    get_cmd="SOUR:POW?",
        #                    set_cmd="SOUR:POW {} dBm",
        #                    unit='dBm',
        #                    )

        self.connect_message()
        if reset:
            self.reset()

    def reset(self):
        self.write('*RST')  # reset to default settings
        # self.set_default_channel_config()
        # self.set_default_window_config()
        # self.sweep_mode('single')

    def send_trigger(self):
        s = self.trigger_source()
        if s == 'imm':
            self.write('INIT:IMM')
        elif s == 'man':
            self.write('*TRG')
        else:
            raise Exception(f'Not sure how to trigger manually when trigger source is set to {s}')

    def set_default_window_config(self):
        self.write('DISPlay:FORMat QQSPlit')
        for chan in range(1, 5):
            self.write('DISP:WIND%u:DIAG CDB' % chan)
            self.write('CALC%u:FORMat MAGNitude' % chan)
        self.autoscale_once()

    def autoscale_once(self):
        for chan in range(1, 5):
            self.write('DISPlay:WIND%u:TRAC:Y:SCALe:AUTO ONCE' % chan)

    def get_data(self, chan):
        self.write('FORM REAL,32')
        return self.visa_handle.query_binary_values('TRAC? TRACE%s' % chan,
                                                        datatype='f',
                                                        is_big_endian=False,
                                                        container=np.array,
                                                        header_fmt='ieee')

    def get_frequency_data(self, num):
        mini = self.start_frequency()
        maxi = self.stop_frequency()
        points = self.num_points()
        return np.linspace(mini, maxi, points)

    # def get_transm(self, num):
    #     '''
    #     Gives the transmission spectrum
    #     Use self.source_status(1) before!!
    #     '''
    #     self.write('TRAC%s' % num)
    #     self.write('CORR:METH:TRAN')
    #     return self.get_data(num)

    def _read_on_off_value(self, cmd):
        """
        The instrument requires inputting boolean values as "ON" or "OFF",
        but returns them as 1 or 0...
        cmd should include "?"
        """
        return "ON" if bool(self.ask(cmd)) else "OFF"

    def _get_if_bandwidth(self):  # in Hz
        r = self.ask('BAND?')
        if r.strip().lower().startswith('max'):
            r = 26000
        return float(r) / self._freq_unit

    def _set_if_bandwidth(self, if_bandwidth):  # in Hz
        '''
        Note that video BW is automatically kept at 3x reolution BW
        It can be change manually on the FSL or using 'BAND:VID %sHz'
        '''
        if np.abs(if_bandwidth - 26e3) > 1:
            self.write(f'BAND {if_bandwidth}Hz')
        else:
            self.write('BAND MAX')
        self.sweeptime()

    def _get_external_reference(self):
        return self.ask('SENS:ROSC:SOUR?').lower().startswith('ext')

    def _set_external_reference(self, val):
        self.write('SENS:ROSC:SOUR %s' % (val))

    def _get_trigger_source(self):
        r = self.ask('TRIGGER:SEQUENCE:SOURCE?').lower().strip()
        if r.startswith('lin') or r.startswith('rtc'):
            r = r[:4]
        else:
            r = r[:3]
        return r

