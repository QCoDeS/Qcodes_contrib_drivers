### TO Do, add a way to add traces!


from typing import Sequence, Union, Any
import time
import re
import logging

import numpy as np
from pyvisa import VisaIOError, errors
from qcodes import (VisaInstrument, InstrumentChannel, ArrayParameter, MultiParameter,
                    ChannelList)
from qcodes.utils.validators import Ints, Numbers, Enum, Bool

logger = logging.getLogger()


class MagPhaseSweep(MultiParameter):
    """
    Sweep that return magnitude and phase.
    """

    def __init__(self,
                 name: str, 
                 instrument: 'PNABase',
                 start,
                 stop,
                 npts,
                 sweep_format: str,
                  **kwargs: Any) -> None:
        super().__init__(name,
             instrument = instrument,
             names=("", ""),
             shapes=((), ()),
             **kwargs)
        self.sweep_format = sweep_format
        
        self._instrument = instrument
        self.set_sweep(start, stop, npts)
        self.names = ('{}_Magnitude'.format(instrument.name),
                      '{}_Phase'.format(instrument.name))
        self.labels = ('{}_Magnitude'.format(instrument.name),
                       '{}_Phase'.format(instrument.name))
        self.units = ('dB', 'deg')
        self.setpoint_units = (('Hz',), ('Hz',))
        self.setpoint_labels = (('Frequency',), ('Frequency',))
        self.setpoint_names = (('frequency',), ('frequency',))

    def set_sweep(self, start, stop, npts):
        #  needed to update config of the software parameter on sweep change
        # freq setpoints tuple as needs to be hashable for look up
        f = tuple(np.linspace(int(start), int(stop), num=npts))
        self.setpoints = ((f,), (f,))
        self.shapes = ((npts,), (npts,))

    def get_raw(self) -> Sequence[float]:
        if self._instrument is None:
            raise RuntimeError("Cannot get data without instrument")
        root_instr = self._instrument.root_instrument
        # Check if we should run a new sweep
        if root_instr.auto_sweep():
            self._instrument.run_sweep()
        # Ask for data, setting the format to the requested form
        self._instrument.format(self.sweep_format)
        root_instr.write(":FORM:DATA  REAL") # gets binary in 64 bit floating point, use datatype='d' for double

        data = root_instr.visa_handle.query_binary_values('CALC:DATA:FDAT?',
                                                          datatype='d',
                                                          is_big_endian=True)
        data = np.reshape(data, (root_instr.points(), 2))
        return data[:,0], np.unwrap(data[:,1]/180*np.pi)*180/np.pi



class MagPhasePoint(MultiParameter):
    """
    Returns the first popint of a sweep (at start frequency).
    In principle the VNA returns at least two points (or more, depending on the trace), but only the first is used.
    """

    def __init__(self,
                 name: str, 
                 instrument: 'PNABase',
                 start,
                 sweep_format: str,
                  **kwargs: Any) -> None:
        super().__init__(name,
             instrument = instrument,
             names=("", ""),
             shapes=((), ()),
             **kwargs)
        self.sweep_format = sweep_format
        
        self._instrument = instrument
        self.set_sweep(start)
        self.names = ('magnitude',
                      'phase')
        self.labels = ('{} Magnitude'.format(instrument.trace()),
                       '{} Phase'.format(instrument.trace()))
        self.units = ('dB', 'deg')
        self.setpoint_units = ('Hz', 'Hz')
        self.setpoint_labels = ('Frequency', 'Frequency')
        self.setpoint_names = ('frequency', 'frequency')

    def set_sweep(self, frequency):
        #  needed to update config of the software parameter on sweep change
        # freq setpoints tuple as needs to be hashable for look up
        self.setpoints = (frequency, frequency)
        self.shapes = ((), ())

    def get_raw(self) -> Sequence[float]:
        if self._instrument is None:
            raise RuntimeError("Cannot get data without instrument")
        root_instr = self._instrument.root_instrument
        # Check if we should run a new sweep
        if root_instr.auto_sweep():
            self._instrument.run_sweep(timeout=0.001)
        # Ask for data, setting the format to the requested form
        self._instrument.format(self.sweep_format)
        root_instr.write(":FORM:DATA  REAL") # gets binary in 64 bit floating point, use datatype='d' for double

        data = root_instr.visa_handle.query_binary_values('CALC:DATA:FDAT?',
                                                          datatype='d',
                                                          is_big_endian=True)
        data = np.reshape(data, (root_instr.points(), 2))
        return data[0,0], data[0,1]




class PNASweep(ArrayParameter):
    def __init__(self,
                 name: str,
                 instrument: 'PNABase',
                 **kwargs: Any) -> None:

        super().__init__(name,
                         instrument=instrument,
                         shape=(0,),
                         setpoints=((0,),),
                         **kwargs)

    @property # type: ignore
    def shape(self) -> Sequence[int]: # type: ignore
        if self._instrument is None:
            return (0,)
        return (self._instrument.root_instrument.points(),)
    @shape.setter
    def shape(self, val: Sequence[int]) -> None:
        pass

    @property # type: ignore
    def setpoints(self) -> Sequence: # type: ignore
        if self._instrument is None:
            raise RuntimeError("Cannot return setpoints if not attached "
                               "to instrument")
        start = self._instrument.root_instrument.start()
        stop = self._instrument.root_instrument.stop()
        return (np.linspace(start, stop, self.shape[0]),)
    @setpoints.setter
    def setpoints(self, val: Sequence[int]) -> None:
        pass


class MarkerData(MultiParameter):
    """
    Sweep that return magnitude and phase.
    """

    def __init__(self,
                 name: str, 
                 instrument: 'ENAMarker',
                  **kwargs: Any) -> None:
        super().__init__(name,
             instrument = instrument,
             names=("", ""),
             shapes=((), (), ()),
             **kwargs)
        
        self._instrument = instrument
        self.names = ('magnitude',
                      'phase', 
                      'frequency')
        self.labels = ('{} Magnitude'.format(instrument.trace()),
                       '{} Phase'.format(instrument.trace()),
                       ' Frequency')
        self.units = ('dB', 'deg', 'Hz')
        self.setpoint_units = (('Hz',), ('Hz',), ('Hz',))
        self.setpoint_labels = (('Frequency',), ('Frequency',), ('Frequency',))
        self.setpoint_names = (('frequency',), ('frequency',), ('frequency',))


    def get_raw(self) -> Sequence[float]:
        if self._instrument is None:
            raise RuntimeError("Cannot get data without instrument")
        root_instr = self._instrument.root_instrument
        # Check if we should run a new sweep
        if root_instr.auto_sweep():
            self._instrument.run_sweep()
        # Ask for data, setting the format to the requested form
        #self._instrument.format(self.sweep_format)
        root_instr.write(":FORM:DATA  REAL") # gets binary in 64 bit floating point, use datatype='d' for double

        assert isinstance(self.instrument, ENAMarker)
        data = root_instr.ask('CALC:TRAC1:MARK{}:DATA?'.format(self.instrument.marker_num))
        return data[:,0], data[:,1], data[:,2]


class FormattedSweep(PNASweep):
    """
    Mag will run a sweep, including averaging, before returning data.
    As such, wait time in a loop is not needed.
    """
    def __init__(self,
                 name: str,
                 instrument: 'PNABase',
                 sweep_format: str,
                 label: str,
                 unit: str,
                 memory: bool = False) -> None:
        super().__init__(name,
                         instrument=instrument,
                         label=label,
                         unit=unit,
                         setpoint_names=('frequency',),
                         setpoint_labels=('Frequency',),
                         setpoint_units=('Hz',)
                         )
        self.label = (instrument.trace() + " " +label)
        self.sweep_format = sweep_format
        self.memory = memory

    def get_raw(self) -> Sequence[float]:
        if self._instrument is None:
            raise RuntimeError("Cannot get data without instrument")
        root_instr = self._instrument.root_instrument
        # Check if we should run a new sweep
        if root_instr.auto_sweep():
            self._instrument.run_sweep()
        # Ask for data, setting the format to the requested form
        self._instrument.format(self.sweep_format)
        root_instr.write(":FORM:DATA  REAL") # gets binary in 64 bit floating point, use datatype='d' for double

        data = root_instr.visa_handle.query_binary_values('CALC:DATA:FDAT?',
                                                          datatype='d',
                                                          is_big_endian=True)
        data = np.reshape(data, (root_instr.points(), 2))
        return data[:,0]

class PNAPort(InstrumentChannel):
    """
    Allow operations on individual PNA ports.
    Note: This can be expanded to include a large number of extra parameters...
    """

    def __init__(self,
                 parent: 'PNABase',
                 name: str,
                 port: int,
                 min_power: Union[int, float],
                 max_power: Union[int, float]) -> None:
        super().__init__(parent, name)

        self.port = int(port)
        if self.port < 1 or self.port > 4:
            raise ValueError("Port must be between 1 and 4.")

        pow_cmd = f"SOUR:POW{self.port}"
        self.add_parameter("source_power",
                           label="power",
                           unit="dBm",
                           get_cmd=f"{pow_cmd}?",
                           set_cmd=f"{pow_cmd} {{}}",
                           get_parser=float,
                           vals=Numbers(min_value=min_power,
                                        max_value=max_power))

    def _set_power_limits(self,
                          min_power: Union[int, float],
                          max_power: Union[int, float]) -> None:
        """
        Set port power limits
        """
        self.source_power.vals = Numbers(min_value=min_power,
                                         max_value=max_power)
        
class ENAMarker(InstrumentChannel):
    """
    Generates up to four markers; which are all bound to trace1
    """
    def __init__(self,
                 parent: 'PNABase',
                 name: str,
                 marker_name: str,
                 marker_num: int) -> None:
        super().__init__(parent, name)
        self.marker_name = name
        self.marker_num = marker_num
        
        self.add_parameter(name = 'X_position',
                           get_cmd = ':CALCulate:TRAC1:MARK{}:X?'.format(marker_num),
                           get_parser = float,
                           set_cmd = self._set_marker_x_position,
                           vals=Numbers(min_value=self._parent.min_freq,
                                        max_value=self._parent.max_freq))
        self.add_parameter('data',
                           parameter_class=MarkerData)
        
        def _set_marker_x_position(self, value):
            self.write(":CALCulate:TRAC1:MARK{}:X {}".format(marker_num, value))
            
        def on(self):
            self.write(':CALC:MARK{} ON'.format(marker_num))
        
        def off(self):
            self.write(':CALC:MARK{} OFF'.format(marker_num))
        
        
    

class PNATrace(InstrumentChannel):
    """
    Allow operations on individual PNA traces.
    """

    def __init__(self,
                 parent: 'PNABase',
                 name: str,
                 trace_name: str,
                 trace_num: int) -> None:
        super().__init__(parent, name)
        self.trace_name = name
        self.trace_num = trace_num

        # Name of parameter (i.e. S11, S21 ...)
        self.add_parameter('trace',
                           label='Trace',
                           get_cmd=self._Sparam,
                           set_cmd=self._set_Sparam)
        # Format
        # Note: Currently parameters that return complex values are not
        # supported as there isn't really a good way of saving them into the
        # dataset

        self.add_parameter(name='format',
                           get_cmd='CALC:FORM?',
                           set_cmd=self._set_format,
                           val_mapping={'dB': 'MLOG',
                                        'Linear Magnitude': 'MLIN',
                                        'Phase': 'PHAS',
                                        'Unwr Phase': 'UPH',
                                        'Polar': 'POL',
                                        'Smith': 'SMIT',
                                        'Smith log': 'SLOG',
                                        'Inverse Smith': 'ISM',
                                        'SWR': 'SWR',
                                        'Real': 'REAL',
                                        'Imaginary': 'IMAG',
                                        'Delay': "GDEL",
                                        'Complex': "COMP"
                                        })

        # And a list of individual formats
        self.add_parameter('magnitude',
                           sweep_format='dB',
                           label='Magnitude',
                           unit='dB',
                           parameter_class=FormattedSweep)
        self.add_parameter('linear_magnitude',
                           sweep_format='Linear Magnitude',
                           label='Magnitude',
                           unit='ratio',
                           parameter_class=FormattedSweep)
        self.add_parameter('phase',
                           sweep_format='Phase',
                           label='Phase',
                           unit='deg',
                           parameter_class=FormattedSweep)
        self.add_parameter('unwrapped_phase',
                           sweep_format='Unwr Phase',
                           label='Unwrapped Phase',
                           unit='deg',
                           parameter_class=FormattedSweep)
        self.add_parameter("group_delay",
                           sweep_format='Delay',
                           label='Group Delay',
                           unit='s',
                           parameter_class=FormattedSweep)
        self.add_parameter('real',
                           sweep_format='Real',
                           label='Real',
                           unit='LinMag',
                           parameter_class=FormattedSweep)
        self.add_parameter('imaginary',
                           sweep_format='Imaginary',
                           label='Imaginary',
                           unit='LinMag',
                           parameter_class=FormattedSweep)
        self.add_parameter('MagPhase',
                           sweep_format='Smith log',
                           start=self._parent.start(),
                           stop=self._parent.stop(),
                           npts=self._parent.points(),
                           parameter_class=MagPhaseSweep)
        # Paramteter that returns a single tuble of Mag and Phase
        self.add_parameter('MagPhasePoint',
                           sweep_format='Smith log',
                           start=self._parent.start(),
                           parameter_class=MagPhasePoint)
        
    def _set_format(self, val) -> None:
        unit_mapping = {'MLOG\n': 'dB',
                        'MLIN\n': '',
                        'PHAS\n': 'rad',
                        'UPH\n': 'rad',
                        'POL\n': '',
                        'SMIT\n': '',
                        'SLOG\n': '',
                        'ISM\n': '',
                        'SWR\n': 'U',
                        'REAL\n': 'U',
                        'IMAG\n': 'U',
                        'GDEL\n': 'S',
                        'COMP\n': ''}
        label_mapping = {'MLOG\n': 'Magnitude',
                         'MLIN\n': 'Magnitude',
                         'PHAS\n': 'Phase',
                         'UPH\n': 'Unwrapped phase',
                         'POL\n': 'Complex Magnitude',
                         'SMIT\n': 'Complex Magnitude',
                         'SLOG\n': 'log mag and phase',
                         'ISM\n': 'Complex Magnitude',
                         'SWR\n': 'Standing Wave Ratio',
                         'REAL\n': 'Real Magnitude',
                         'IMAG\n': 'Imaginary Magnitude',
                         'GDEL\n': 'Delay',
                         'COMP\n': 'Complex Magnitude'}
        self.write(f"CALC:FORM {val}")

    def run_sweep(self, timeout=0.1) -> None:
        """
        Run a set of sweeps on the network analyzer.
        Note that this will run all traces on the current channel.
        """
        root_instr = self.root_instrument
        # Take instrument out of continuous mode, and send triggers equal to
        # the number of averages
        if root_instr.averages_enabled():
            root_instr.reset_averages()
            root_instr.average_trigger('on')
        # Put Continuous mode on and triger once, after completed measurement, continuous mode is off
        root_instr.continuous_mode('off')
        root_instr.set_immediate_mode()
        root_instr.write("*CLS")    #clear status bit register
        root_instr.single_trigger()
        root_instr.write("*OPC")    #"set correct bit, aka operation complete bit"
        # Once the sweep mode is in hold, we know we're done
        try:
            while int(root_instr.ask("*ESR?")) == 0:
                time.sleep(timeout)
        except KeyboardInterrupt:
            # If the user aborts because (s)he is stuck in the infinite loop
            # mentioned above, provide a hint of what can be wrong.
            msg = "User abort detected. "
            source = root_instr.trigger_source()
            if source == "MAN":
                msg += "The trigger source is manual. Are you sure this is " \
                       "correct? Please set the correct source with the " \
                       "'trigger_source' parameter"
            elif source == "EXT":
                msg += "The trigger source is external. Is the trigger " \
                       "source functional?"
            logger.warning(msg)
            

    def write(self, cmd: str) -> None:
        """
        Select correct trace before querying
        """
        self.root_instrument.active_trace(self.trace_num)
        super().write(cmd)

    def ask(self, cmd: str) -> str:
        """
        Select correct trace before querying
        """
        self.root_instrument.active_trace(self.trace_num)
        return super().ask(cmd)

    def _Sparam(self) -> str:
        """
        Extrace S_parameter from returned PNA format
        """
        paramspec = self.root_instrument.get_trace_catalog()
        for spec_ind in range(len(paramspec)//2):
            name, param = paramspec[spec_ind*2:(spec_ind+1)*2]
            if name == self.trace_name:
                return param
        raise RuntimeError("Can't find selected trace on the PNA")

    def _set_Sparam(self, val: str) -> None:
        """
        Set an S-parameter, in the format S<a><b>, where a and b
        can range from 1-2
        """
        if not re.match("S[1-2][1-2]", val):
            raise ValueError("Invalid S parameter spec")
        self.write("CALC:PAR{}:DEF {}".format(self.trace_num, val))

class PNABase(VisaInstrument):
    """
    Base qcodes driver for Agilent/Keysight series PNAs
    http://na.support.keysight.com/pna/help/latest/Programming/GP-IB_Command_Finder/SCPI_Command_Tree.htm

    Note: Currently this driver only expects a single channel on the PNA. We
          can handle multiple traces, but using traces across multiple channels
          may have unexpected results.
    """

    def __init__(self,
                 name: str,
                 address: str,
                 **kwargs: Any) -> None:
        super().__init__(name, address, terminator='\n', **kwargs)
        min_freq = 300e3
        max_freq = 20e9
        min_power = -85
        max_power = 10
        nports = 2
        
#
#        #Ports
#        ports = ChannelList(self, "PNAPorts", PNAPort)
#        self.add_submodule("ports", ports)
#        for port_num in range(1, nports+1):
#            port = PNAPort(self, f"port{port_num}", port_num,
#                           min_power, max_power)
#            ports.append(port)
##            self.add_submodule(f"port{port_num}", port)
#        ports.lock()


        # Drive power
        self.add_parameter('power',
                           label='Power',
                           get_cmd='SOUR:POW?',
                           get_parser=float,
                           set_cmd='SOUR:POW {:.2f}',
                           unit='dBm',
                           vals=Numbers(min_value=min_power,
                                        max_value=max_power))

        # IF bandwidth
        self.add_parameter('if_bandwidth',
                           label='IF Bandwidth',
                           get_cmd='SENS:BAND?',
                           get_parser=float,
                           set_cmd='SENS:BAND {:.2f}',
                           unit='Hz',
                           #vals=Numbers(min_value=10, max_value=15e6))
                           vals=Enum(
                           *np.append([10 ** 6, 15 * 10 ** 5],
                           np.kron([10, 15, 20, 30, 50, 70], 10 ** np.arange(5)))))
                           

        # Number of averages (also resets averages)
        self.add_parameter('averages_enabled',
                           label='Averages Enabled',
                           get_cmd="SENS:AVER?",
                           set_cmd="SENS:AVER {}",
                           val_mapping={True: '1', False: '0'})
        self.add_parameter('averages',
                           label='Averages',
                           get_cmd='SENS:AVER:COUN?',
                           get_parser=int,
                           set_cmd='SENS:AVER:COUN {:d}',
                           unit='',
                           vals=Numbers(min_value=1, max_value=999))
        self.add_parameter('average_trigger',
                           label='Average Trigger',
                           get_cmd=':TRIG:AVER?',
                           set_cmd=':TRIG:AVER {}',
                           vals=Enum('on', 'On', 'ON',
                                          'off', 'Off', 'OFF'))

        # Setting frequency range
        self.add_parameter('start',
                           label='Start Frequency',
                           get_cmd='SENS:FREQ:STAR?',
                           get_parser=float,
                           set_cmd='SENS:FREQ:STAR {}',
                           unit='Hz',
                           vals=Numbers(min_value=min_freq,
                                        max_value=max_freq))
        self.add_parameter('stop',
                           label='Stop Frequency',
                           get_cmd='SENS:FREQ:STOP?',
                           get_parser=float,
                           set_cmd='SENS:FREQ:STOP {}',
                           unit='Hz',
                           vals=Numbers(min_value=min_freq,
                                        max_value=max_freq))
        self.add_parameter('center',
                           label='Center Frequency',
                           get_cmd='SENS:FREQ:CENT?',
                           get_parser=float,
                           set_cmd='SENS:FREQ:CENT {}',
                           unit='Hz',
                           vals=Numbers(min_value=min_freq,
                                        max_value=max_freq))
        self.add_parameter('span',
                           label='Frequency Span',
                           get_cmd='SENS:FREQ:SPAN?',
                           get_parser=float,
                           set_cmd='SENS:FREQ:SPAN {}',
                           unit='Hz',
                           vals=Numbers(min_value=min_freq,
                                        max_value=max_freq))
        
        # Number of points in a sweep
        self.add_parameter('points',
                           label='Points',
                           get_cmd='SENS:SWE:POIN?',
                           get_parser=int,
                           set_cmd='SENS:SWE:POIN {}',
                           unit='',
                           vals=Numbers(min_value=1, max_value=20001))

        # Electrical delay
        self.add_parameter('electrical_delay',
                           label='Electrical Delay',
                           get_cmd='CALC:CORR:EDEL:TIME?',
                           get_parser=float,
                           set_cmd='CALC:CORR:EDEL:TIME {:.6e}',
                           unit='s',
                           vals=Numbers(min_value=0, max_value=100000))

        # Sweep Time
        self.add_parameter('sweep_time',
                           label='Time',
                           get_cmd='SENS:SWE:TIME?',
                           set_cmd='SENS:SWE:TIME {}',
                           get_parser=float,
                           unit='s',
                           vals=Numbers(0, 1e6))
        # Trigger Mode
        self.add_parameter('continuous_mode',
                           label='Continuous Mode',
                           get_cmd=':INIT:CONT?',
                           set_cmd=':INIT:CONT {}',
                           vals=Enum('on', 'On', 'ON', 1,
                                          'off', 'Off', 'OFF', 0))
        # Trigger Source
        self.add_parameter(name='trigger_source',
                           label='Trigger source',
                           get_cmd=":TRIG:SEQ:SOUR?",
                           set_cmd = ':TRIG:SEQ:SOUR {}',
                           get_parser=str,
                           vals = Enum('bus', 'BUS', 'Bus',
                                            'EXT', 'external', 'EXTERNAL', 'External',
                                            'INT', 'internal', 'INTERNAL', 'Internal',
                                            'MAN', 'manual', 'MANUAL', 'Manual'))
        # Traces
        self.add_parameter(name='num_traces',
                           label='Number of Traces',
                           get_cmd='CALC:PAR:COUN?',
                           set_cmd='CALC:PAR:Coun {}',
                           get_parser=int,
                           vals=Numbers(min_value=1, max_value=4))
        self.add_parameter('active_trace',
                           label='Active Trace',
                           set_cmd="CALC:PAR{}:SEL",
                           vals=Numbers(min_value=1, max_value=4))
        
        #Init the names of the traces on the VNA
        for n in range(self.num_traces()):
            self.write("CALC:PAR{}:TNAME:DATA TR{}".format(n+1, n+1))
            
        # Initialize the trigger source to "BUS"
        self.trigger_source('BUS')
        
        # Initialize sweep time to auto
        self.sweep_time(0)
        
        # Note: Traces will be accessed through the traces property which
        # updates the channellist to include only active trace numbers
        self._traces = ChannelList(self, "PNATraces", PNATrace)
        self.add_submodule("traces", self._traces)
#        # Add shortcuts to first trace
#        trace1 = self.traces[0]
#        for param in trace1.parameters.values():
#            self.parameters[param.name] = param
#        # And also add a link to run sweep
#        self.run_sweep = trace1.run_sweep
#        # Set this trace to be the default (it's possible to end up in a
#        # situation where no traces are selected, causing parameter snapshots
#        # to fail)
#        self.active_trace(trace1.trace_num)
        
        # Add markers to instrument        
        self._markers = ChannelList(self, "ENAMarkers", ENAMarker)
        self.add_submodule("markers", self._markers)        


        # Set auto_sweep parameter
        # If we want to return multiple traces per setpoint without sweeping
        # multiple times, we should set this to false
        self.add_parameter('auto_sweep',
                           label='Auto Sweep',
                           set_cmd=None,
                           get_cmd=None,
                           vals=Bool(),
                           initial_value=True)

        self.connect_message()

    @property
    def traces(self) -> ChannelList:
        """
        Update channel list with active traces and return the new list
        """

        # Get a list of traces from the instrument and fill in the traces list
        parlist = self.get_trace_catalog()
        self._traces.clear()
        for trace_name in parlist[::2]:
            trace_num = self.select_trace_by_name(trace_name)
            pna_trace = PNATrace(self, "TR{}".format(trace_num),
                                 trace_name, trace_num)
            self._traces.append(pna_trace)


        # Return the list of traces on the instrument
        return self._traces
    
    @property
    def markers(self) -> ChannelList:
        """
        Update channel list with markers and return the new list
        """

        self._markers.clear()
        for marker_num in range(1, 5):
            marker_name = "marker{}".format(marker_num) 
            ena_marker = ENAMarker(self, "marker{}".format(marker_num),
                                 marker_name, marker_num)
            self._markers.append(ena_marker)


        # Return the list of markers
        return self._markers    


    def get_options(self) -> Sequence[str]:
        # Query the instrument for what options are installed
        return self.ask('*OPT?').strip('"').split(',')

    def get_trace_catalog(self):
        """
        Get the trace catalog, that is a list of trace and sweep types
        from the PNA.

        The format of the returned trace is:
            trace_name,trace_type,trace_name,trace_type...
        """
        trace_catalog = []
        for n in range(self.num_traces()):
            trace_catalog.append(self.ask(":CALC:PAR{}:TNAMe:DATA?".format(n+1))[1:-1])
            trace_catalog.append(self.ask('CALC:PAR{}:DEF?'.format(n+1)))
        return trace_catalog

    def select_trace_by_name(self, trace_name: str) -> int:
        """
        Select a trace on the PNA by name.

        Returns:
            The trace number of the selected trace
        """
        self.write(f"CALC:PAR:TNAME:SEL '{trace_name}'")
        trace_catalog = self.get_trace_catalog()
#        print(int(trace_catalog.index(trace_name)/2+1))
        return int(trace_catalog.index(trace_name)/2+1)

    def reset_averages(self):
        """
        Reset averaging
        """
        self.write("SENS:AVER:CLE")

    def averages_on(self):
        """
        Turn on trace averaging
        """
        self.averages_enabled(True)

    def averages_off(self):
        """
        Turn off trace averaging
        """
        self.averages_enabled(False)

    def _set_power_limits(self,
                          min_power: Union[int, float],
                          max_power: Union[int, float]) -> None:
        """
        Set port power limits
        """
        self.power.vals = Numbers(min_value=min_power,
                                  max_value=max_power)
        for port in self.ports:
            port._set_power_limits(min_power, max_power)
        
    def single_trigger(self):
        self.write('TRIG:SING')

    def set_immediate_mode(self):
        self.write('INIT:IMM')

class PNAxBase(PNABase):
    def _enable_fom(self) -> None:
        '''
        PNA-x units with two sources have an enormous list of functions &
        configurations. In practice, most of this will be set up manually on
        the unit, with power and frequency varied in a sweep.
        '''
        self.add_parameter('aux_frequency',
                           label='Aux Frequency',
                           get_cmd='SENS:FOM:RANG4:FREQ:CW?',
                           get_parser=float,
                           set_cmd='SENS:FOM:RANG4:FREQ:CW {:.2f}',
                           unit='Hz',
                           vals=Numbers(min_value=self.min_freq,
                                        max_value=self.max_freq))
