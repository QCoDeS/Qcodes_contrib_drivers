from typing import Any
import logging
from functools import partial
from typing import Optional

import numpy as np

from qcodes.utils.validators import Enum, Strings, Ints
from qcodes import VisaInstrument, Instrument
from qcodes import MultiParameter, ArrayParameter


log = logging.getLogger(__name__)


class FrequencySweepMagPhase(MultiParameter):

    def __init__(self, name: str, instrument: Instrument,
                 start: float, stop: float, npts: int, channel: int, **kwargs) -> None:
        super().__init__(name, names=("", ""), shapes=((), ()), **kwargs)
        self._instrument = instrument
        self.set_sweep(start, stop, npts)
        self._channel = channel
        self.names = ('magnitude',
                      'phase')
        self.labels = (f'{instrument.short_name} magnitude',
                       f'{instrument.short_name} phase')
        self.units = ('', 'rad')
        self.setpoint_units = (('Hz',), ('Hz',))
        self.setpoint_labels = (
            (f'{instrument.short_name} frequency',),
            (f'{instrument.short_name} frequency',)
        )
        self.setpoint_names = (
            (f'{instrument.short_name}_frequency',),
            (f'{instrument.short_name}_frequency',)
        )


    def set_sweep(self, start: float, stop: float, npts: int) -> None:
        f = tuple(np.linspace(int(start), int(stop), num=npts))
        self.setpoints = ((f,), (f,))
        self.shapes = ((npts,), (npts,))

    def get_raw(self):
        old_format = self._instrument.format()
        self._instrument.format('Complex')
        data = self._instrument._get_sweep_data(force_polar=True)
        self._instrument.format(old_format)
        return abs(data), np.angle(data)


class FrequencySweep(ArrayParameter):

    def __init__(self, name: str, instrument: Instrument,
                 start: float, stop: float, npts: int, channel: int, **kwargs) -> None:
        super().__init__(name, shape=(npts,),
                         instrument=instrument,
                         unit='dB',
                         label=f'{instrument.short_name} magnitude',
                         setpoint_units=('Hz',),
                         setpoint_labels=(f'{instrument.short_name}'
                                          ' frequency',),
                         setpoint_names=(f'{instrument.short_name}_frequency',),
                         **kwargs,
                         )
        self.set_sweep(start, stop, npts)
        self._channel = channel

    def set_sweep(self, start: float, stop: float, npts: int) -> None:

        f = tuple(np.linspace(int(start), int(stop), num=npts))
        self.setpoints = (f,)
        self.shape = (npts,)

    def get_raw(self):
        data = self._instrument._get_sweep_data()
        if self._instrument.format() in ['Polar', 'Complex',
                                         'Smith', 'Inverse Smith']:
            log.warning("QCoDeS Dataset does not currently support Complex "
                        "values. Will discard the imaginary part. In order to "
                        "acquire phase and amplitude use the "
                        "FrequencySweepMagPhase parameter.")
        return data


class ComplexSweep(ArrayParameter):
    def __init__(self, name: str, instrument: Instrument,
                 start: float, stop: float, npts: int, channel:int, **kwargs) -> None:
        super().__init__(name, shape=(npts,),
                         instrument=instrument,
                         unit='dB',
                         label=f'{instrument.short_name} magnitude',
                         setpoint_units=('Hz',),
                         setpoint_labels=(f'{instrument.short_name}'
                                          ' frequency',),
                         setpoint_names=(f'{instrument.short_name}_frequency',),
                         **kwargs,
                         )
        self.set_sweep(start, stop, npts)
        self._channel = channel

    def set_sweep(self, start: float, stop: float, npts: int) -> None:
        f = tuple(np.linspace(int(start), int(stop), num=2*npts))
        self.setpoints = (f,)
        self.shape = (2*npts,)

    def get_raw(self):
        data = self._instrument._get_sweep_data(force_polar=True)
        if self._instrument.format() in ['Polar', 'Complex',
                                         'Smith', 'Inverse Smith']:
            log.warning("QCoDeS Dataset does not currently support Complex "
                        "values. Will discard the imaginary part. In order to "
                        "acquire phase and amplitude use the "
                        "FrequencySweepMagPhase parameter.")
        return data
    

class SAFrequencySweep(ArrayParameter):
    def __init__(self, name: str, instrument: Instrument,
                 start: float, stop: float, npts: int, channel: int, **kwargs) -> None:
        super().__init__(name, shape=(npts,),
                         instrument=instrument,
                         unit='dBm',
                         label=f'{instrument.short_name} magnitude',
                         setpoint_units=('Hz',),
                         setpoint_labels=(f'{instrument.short_name}'
                                          ' frequency',),
                         setpoint_names=(f'{instrument.short_name}_frequency',),
                         **kwargs,
                         )
        self.set_sweep(start, stop, npts)
        self._channel = channel

    def set_sweep(self, start: float, stop: float, npts: int) -> None:

        f = tuple(np.linspace(int(start), int(stop), num=npts))
        self.setpoints = (f,)
        self.shape = (npts,)

    def get_raw(self):
        data = self._instrument._get_sweep_data_SA()
        return data


class ZVL13(VisaInstrument):
    def __init__(
            self,
            name: str,
            address: str,
            terminator='\n',
            **kwargs: Any):
        super().__init__(name, address, terminator=terminator, **kwargs)

        self.add_parameter(name='mode',
                           label='VNA Mode',
                           get_cmd=self._get_mode,
                           set_cmd=self._set_mode,
                           get_parser=str)

        mode = self.mode.get()
        if mode == 'SAN':
            n = int(1)
            self._tracename = 'Trc1'
        if mode == 'NWA':
            _, trace_name = self._get_trace_name()
            self._tracename = trace_name

        self.inf_lim = 9e+3
        
        self.sup_lim = 13.6e+9

        self.timeout_sweep = 40
        self.timeout_sa = 40

        self.add_parameter('start',
                           get_cmd='FREQ:STAR?',
                           get_parser=float,
                           set_cmd=self._set_start,
                           unit = 'Hz',
                           label='Start Frequency')
        
        self.add_parameter('stop',
                           get_cmd='FREQ:STOP?',
                           get_parser=float,
                           set_cmd=self._set_stop,
                           unit = 'Hz',
                           label='Stop Frequency')
        
        self.add_parameter('center',
                           get_cmd='FREQ:CENT?',
                           get_parser=float,
                           set_cmd=self._set_center,
                           unit = 'Hz',
                           label='Center Frequency')
        
        self.add_parameter('span',
                            get_cmd='FREQ:SPAN?',
                            get_parser=float,
                            set_cmd=self._set_span,
                            unit = 'Hz',
                            label='Center Frequency')
        
        self.add_parameter('npts',
                           get_cmd='SWE:POIN?',
                           get_parser=int,
                           set_cmd=self._set_npts,
                           label='Number of points')
        
        self.add_parameter('power',
                            get_cmd='SOUR:POW?',
                            get_parser=float,
                            set_cmd=self._set_power,
                            unit = 'dBm',
                            label='Power')
        
        self.add_parameter('format',
                            vals=Strings(),
                            get_cmd=partial(self._get_format,
                                            tracename=self._tracename),
                            set_cmd=self._form,
                            label='Format')        
        
        self.add_parameter('avg',
                            get_parser=int,
                            vals=Ints(1, 5000),
                            get_cmd='AVER:COUN?',
                            set_cmd=self._average,
                            label='Averages')
        
        self.add_parameter(name='num_ports',
                           get_cmd='INST:PORT:COUN?',
                           get_parser=int)
        
        self.add_parameter(name='S_parameter',
                           label='S parameter',
                           get_cmd=f"CALC:PAR:MEAS? '{self._tracename}'",
                           set_cmd=self._set_s_parameter,
                           vals=Strings())
        
        self.add_parameter(name='trace_mag_phase',
                           start=self.start(),
                           stop=self.stop(),
                           npts=self.npts(),
                           channel = n,
                           parameter_class=FrequencySweepMagPhase)
        
        self.add_parameter(name='trace',
                           start=self.start(),
                           stop=self.stop(),
                           npts=self.npts(),
                           channel = n,
                           parameter_class=FrequencySweep)
        
        self.add_parameter(name='S_trace',
                           start=self.start(),
                           stop=self.stop(),
                           npts=self.npts(),
                           channel = n,
                           parameter_class=ComplexSweep)
        
        self.add_parameter(name='spectrum',
                           start=self.start(),
                           stop=self.stop(),
                           npts=self.npts(),
                           channel = n,
                           parameter_class=SAFrequencySweep)
        
        self.add_parameter(name='status',
                            get_cmd='CONF:CHAN1:STAT?',
                            set_cmd='CONF:CHAN1:STAT {{}}',
                            get_parser=int)
        
        self.add_parameter(name='rf_power',
                            get_cmd='OUTP?',
                            set_cmd=self._set_rf_power,
                            get_parser=int)
        
        self.add_parameter(name='bandwidth',
                           label='Bandwidth',
                           unit='Hz',
                           get_cmd='SENS:BAND?',
                           set_cmd=self._set_bandwidth,
                           get_parser=int)
        
        self.add_parameter(name='freq_step',
                           label='Frequency step size',
                           unit='Hz',
                           get_cmd='SENS:SWE:STEP?',
                           set_cmd=self._set_freq_step,
                           get_parser=int)

        self.calibration_file = 'Cal_17_11_2021.cal'
        
        self.add_function('autoscale', call_cmd = 'DISP:WIND:TRAC:Y:AUTO ONCE')

        self.add_function('electrical_delay_auto',
                          call_cmd='CORR:EDEL:AUTO ONCE')
        self.add_function('data_to_mem',
                          call_cmd='CALC:MATH:MEM')
        self.add_function('cont_meas_on',
                          call_cmd='INIT:CONT:ALL ON')
        self.add_function('cont_meas_off',
                          call_cmd='INIT:CONT:ALL OFF')

    def reset(self):
        self.write("*RST")

    def calibration(self):
        """
        Loads calibration file as specified by ``self.calibration_file``.
        """
        self.write(f"MMEMory:LOAD:CORRection 1, '{self.calibration_file}'")

    def _get_mode(self):
        mode_raw = ((self.ask('INST?')).split('\n')[0]).strip()
        mode_mapping = {
            "SAN": "sa",
            "NWA": "na",
        }
        return mode_mapping[mode_raw]

    def _set_mode(self, mode: str):
        if mode == 'sa':
            self.sa_mode()
        elif mode == 'na':
            self.na_mode()
        else:
            raise AttributeError(
                'Wrong string. To set in Spectrum Analyzer mode write "sa", to set in Network Analyzer mode write "na".'
            )

    def sa_mode(self):
        self.write('INST SAN')
        n = int(1)
        self._tracename = 'Trc1'
        self.mode.cache.set("sa")

    def na_mode(self):
        self.write('INST NWA')

        _, trace_name = self._get_trace_name()
        self._tracename = trace_name

        self.mode.cache.set("na")

    def _get_trace_catalog(self):
        return self.ask("CONFigure:TRACe:CATalog?").split(',')

    def _get_trace_name(self):
        trace_catalog = self._get_trace_catalog()
        if len(trace_catalog) == 2:            
            ch, trace_name = trace_catalog
            n = ch[1]
            trace_name = trace_name[:-1]
        else:
            n = trace_catalog[0][1]
            trace_name = trace_catalog[1]
        return n, trace_name

    def _set_freq_step(self, n: int):
        min_step = (self.stop_f() - self.start_f())/(4001)
        max_step = (self.stop_f() - self.start_f())/1 

        if n>min_step and n<max_step:
            self.write("SENS:SWE:STEP " + str(n))
            self.update_traces()
        else:
            raise AttributeError('Step size must be in the range between' + str(min_step) +' Hz and ' + str(max_step) + ' Hz.')

    def _set_npts(self, n: int) -> None:
        self.write("SWE:POIN " + str(n))
        self.update_traces()
        
    def _set_s_parameter(self, msg: str) -> None:
        S_params = ['S11','S12','S21','S22']

        if msg in S_params:
            self.write(f"CALC:PAR:MEAS '{self._tracename}', '{msg}'")
        else: 
            raise AttributeError('Illegal string. Allowed S parameters: S11, S12, S21, S22')

    def _set_bandwidth(self, val:int) -> None:
        if val <= 10e6 and val > 10:
            self.write('SENS:BAND '+str(int(val)))
        else: 
            raise AttributeError('Bandwidth value out of range')
        
    def _set_rf_power(self, val: int) -> None:
        if val == 0:
            self.write('OUTP OFF')
        elif val == 1: 
            self.write('OUTP ON')
        else:
            raise AttributeError('Write 1 to switch on and 0 to switch off')

    def _get_format(self, tracename: str) -> str:
        return self.ask("CALC:FORM?")

    def _form(self, msg:str) -> None:
        if msg == 'phase':                
            self.write('CALC:FORM PHAS')
        elif msg == 'dbm':
            self.write('CALC:FORM MLOG')
        elif msg == 'polar':                
            self.write('CALC:FORM POL')          
        elif msg == 'swr':                
            self.write('CALC:FORM SWR')
        elif msg == 'magnitude':
            self.write('CALC:FORM MLIN')            
        elif msg == 'real':                
            self.write('CALC:FORM REAL')
        elif msg == 'img':
            self.write('CALC:FORM IMAG')
        elif msg == 'unwrapped phase':                
            self.write('CALC:FORM UPH')
        elif msg == 'smith':
            self.write('CALC:FORM SMIT')
        elif msg == 'data/mem':
            self.data_to_mem()
            self.write('CALC:MATH:FUNC DIV')
        else:
            raise AttributeError(
                'Format does not exist. Choose one of the following: '
                'dbm, phase, polar, swr, magnitude, real, img, unwrapped phase, smith, data/mem'
            )

    def _average(self, num:float) -> None:
        self.write('AVER:STAT OFF')
        self.write('AVER:COUN ' + str(int(num)))
        self.write('AVER:STAT ON')
        self.write('AVER:CLE')
            
    def _set_start(self, val: float):
        start = val
        stop = self.stop()
        if start >= stop:
            raise ValueError("Stop frequency must be larger than start frequency.")
        else:
            self.write('FREQ:STAR '+ str(int(start)))

        self.update_traces()
                
    def _set_stop(self, val: float):
        stop = val
        start = self.start()
        if stop <= start:
            raise ValueError("Stop frequency must be larger than start frequency.")
        else:
            self.write('FREQ:STOP '+ str(int(stop)))

        self.update_traces()
                
    def _set_center(self, val: float):
        center = val

        if center <= self.inf_lim or center >= self.sup_lim:
            raise ValueError("Out of the VNA limit.")
        else:
            self.write('FREQ:CENT '+ str(int(center)))

        self.update_traces()

    def _set_span(self, val: float):
        span = val   
        center = self.center()

        if center + span * 0.5 >= self.sup_lim or center - span * 0.5 <= self.inf_lim:
            raise ValueError("Out of the VNA limit.")
        else:        
            self.write('FREQ:SPAN '+ str(int(span)))

        self.update_traces()

    def _set_power(self, val: float):        
        if val > 0:
            raise ValueError(
                "Attenuation cannot be positive.")
        elif val < -40:
            raise ValueError("Unleveled power")
        else:
            self.write('SOUR:POW ' + str(int(val)))

    def _get_sweep_data(self, force_polar: bool = False):
        if force_polar:
            data_format_command = 'SDAT'
        else:
            data_format_command = 'FDAT'

        self.write('SENS:AVER:STAT ON')
        self.write('SENS:AVER:CLE')

        # preserve original state of the znb
        with self.status.set_to(1):
            self.root_instrument.cont_meas_off()
            try:
                with self.root_instrument.timeout.set_to(self.timeout_sweep):
                    self.write('SENS:SWEEP:COUNT '+ str(self.avg()))
                    self.write('INIT:IMMEDIATE:SCOPE:SINGLE')                        
                    self.write('INIT:CONT OFF')
                    self.write('INIT:IMM; *WAI')
                    self.write("CALC:PAR:SEL '{self._tracename}'")
                    data_str = self.ask(f'CALC:DATA? {data_format_command}')

                data = np.array(data_str.rstrip().split(',')).astype('float64')
            finally:
                self.root_instrument.cont_meas_on()
        return data

    def _get_sweep_data_SA(self):
        self.write('SENS:AVER:STAT ON')
        self.write('SENS:AVER:CLE')

        self.root_instrument.cont_meas_off()
        try:
            with self.root_instrument.timeout.set_to(self.timeout_sa):
                self.write('SENS:SWEEP:COUNT '+ str(self.avg()))
                self.write('INIT:IMMEDIATE:SCOPE:SINGLE')                        
                self.write('INIT:CONT OFF')
                self.write('INIT:IMM; *WAI')
                data_str = self.ask('FORM ASC;TRAC? TRACE1')

            data = np.array(data_str.rstrip().split(',')).astype('float64')
        finally:
            self.root_instrument.cont_meas_on()
        return data

    def update_traces(self):
        start = self.start()
        stop = self.stop()
        npts = self.npts()
        for _, parameter in self.parameters.items():
            if isinstance(parameter, (ArrayParameter, MultiParameter)):
                try:
                    parameter.set_sweep(start, stop, npts)
                except AttributeError:
                    pass
