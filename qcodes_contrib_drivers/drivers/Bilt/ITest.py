# This Python file uses the following encoding: utf-8
# Loick Le Guevel, 2019
# Etienne Dumur <etienne.dumur@gmail.com>, 2021

from typing import Union, Tuple
from functools import partial
from math import ceil

from qcodes.instrument.base import Instrument
from qcodes.instrument.channel import InstrumentChannel, ChannelList
from qcodes.instrument.channel import MultiChannelInstrumentParameter
from qcodes.instrument.visa import VisaInstrument


class iTestChannel(InstrumentChannel):
    """
    A single channel of iTest.
    """
    
    def __init__(self, parent: Instrument,
                       name: str,
                       chan_num: int) -> None:
        """
        Args:
            parent: The instrument to which the channel is attached.
            name: The name of the channel.
            chan_num: The number of the channel in question
        """
        super().__init__(parent, name)
        
        self.chan_num = chan_num
        # Get channel id
        i, c = round(chan_num/4.)+1, chan_num%4
        self.chan_id = 'i{};c{};'.format(i,c)

        self.add_parameter('v',
                           label='Channel {} voltage'.format(chan_num),
                           unit='V',
                           docstring='Voltage of the channel in volt.',
                           get_cmd=partial(self._parent._get_voltage, chan_num),
                           set_cmd=partial(self._parent._set_voltage, chan_num),
                           get_parser=float
                           )
        
        self.add_parameter('v_and_trig',
                           label='Channel {} voltage'.format(chan_num),
                           unit='V',
                           docstring='Voltage of the channel in volt. Send a trigger after setting the voltage.',
                           get_cmd=partial(self._parent._get_voltage, chan_num),
                           set_cmd=partial(self._parent._set_voltage, chan_num, trigger=True),
                           get_parser=float
                           )
           
        self.add_parameter('i',
                           label='Channel {} current'.format(chan_num),
                           unit='A',
                           docstring='Current of the channel in ampere.',
                           get_cmd=partial(self._parent._get_current, chan_num),
                           get_parser=float
                           )
        
        self.add_parameter('ramp_slope',
                           label='Channel {} ramp slope'.format(chan_num),
                           unit='V/ms',
                           docstring='Slope of the ramp in V/ms.',
                           get_cmd=partial(self._parent._get_ramp_slope, chan_num),
                           get_parser=float,
                           set_cmd=partial(self._parent._set_ramp_slope, chan_num),
                           set_parser=float
                           )
        
        self.add_parameter('output_mode',
                           label='Channel {} output mode'.format(chan_num),
                           docstring='Mode of the output {exp, ramp}.',
                           get_cmd=partial(self._parent._get_output_function, chan_num),
                           set_cmd=partial(self._parent._set_output_function, chan_num),
                           get_parser=str
                           )
        
        self.add_parameter('range',
                           label = 'Channel {} voltage range'.format(chan_num),
                           docstring='Range of the channelin volt.',
                           set_cmd=partial(self._parent._set_chan_range, chan_num),
                           set_parser=float,
                           get_cmd=partial(self._parent._get_chan_range, chan_num),
                           get_parser=float)
        
        self.add_parameter('state',
                           docstring='State of the channel {on, off}.',
                           get_cmd=partial(self._parent._get_chan_state, chan_num),
                           get_parser=bool,
                           set_cmd=partial(self._parent._set_chan_state, chan_num),
                           set_parser=bool)
        
        self.add_parameter('pos_sat',
                           get_cmd=partial(self._parent._get_chan_pos_sat, chan_num),
                           get_parser=str,
                           set_cmd=partial(self._parent._set_chan_pos_sat, chan_num))
        
        self.add_parameter('neg_sat',
                           get_cmd=partial(self._parent._get_chan_neg_sat, chan_num),
                           get_parser=str,
                           set_cmd=partial(self._parent._set_chan_neg_sat, chan_num))
        
        self.add_parameter('trigger',
                           get_cmd=partial(self._parent._trig_chan, chan_num))
        
        self.add_parameter('bilt_name',
                           set_cmd=partial(self._parent._set_chan_name, chan_num),
                           set_parser=str)
        
        self.add_function('start',
                          call_cmd=lambda: self._parent._set_chan_state(self.chan_num, 1))
        
        self.add_function('stop',
                          call_cmd=lambda: self._parent._set_chan_state(self.chan_num, 0))
    
        self.bilt_name(f'Chan{chan_num:02d}')


class iTestMultiChannelParameter(MultiChannelInstrumentParameter):
    """
    """
    
    def __init__(self, channels, param_name, *args, **kwargs):
        super().__init__(channels, param_name, *args, **kwargs)

    def trigger(self,*args,**kwargs):
        print(args,kwargs)


class ITest(VisaInstrument):
    """
    This is the QCoDeS python driver for the iTest device from Bilt.
    """
    
    def __init__(self,name:str,
                      address:str,
                      num_chans:int=16,
                      init_start:bool=False,
                      **kwargs) -> None:
        """
        Instantiate the instrument.
        
        Args:
            name: The instrument name used by qcodes
            address: The VISA name of the resource
            num_chans: Number of channels to assign. Default: 16
            init_start: If true set all channels to 0V, 1.2V range and switch
                then on.
            
        Returns:
            ITest object
        """
        super().__init__(name, address=address,
                               terminator='\n',
                               device_clear=False)
        
        self.idn = self.get_idn()
        self.num_chans = num_chans
        self.chan_range = range(1,self.num_chans+1)
        
        # Create the channels
        channels = ChannelList(parent=self,
                               name='Channels',
                               chan_type=iTestChannel,
                               multichan_paramclass=iTestMultiChannelParameter)
        
        for i in self.chan_range:
            
            channel = iTestChannel(self,'chan{:02}'.format(i),i)
            channels.append(channel)
            self.add_submodule('ch{:02}'.format(i),channel)
        
        channels.lock()
        self.add_submodule('channels',channels)
        
        if init_start:
            self.channels[:].v.set(0)
            self.channels[:].range(1.2)
            self.channels[:].start()

        self.connect_message()


    def _set_voltage(self, chan:int,
                           v_set:float,
                           trigger:bool=False) -> None:
        """
        Set cmd for the chXX_v parameter
        
        Args:
            chan: The 1-indexed channel number
            v_set: The target voltage
            trigger: If True, send a trigger signal after the voltage is set.
        """
        i,c = self.chan_to_ic(chan)
        self.write('i{};c{};VOLT {:.8f}'.format(i,c,v_set))
        
        if trigger:
            self._trig_chan(chan)


    def _get_voltage(self, chan:int) -> float:
        """
        Get cmd for the chXX_v parameter
        
        Args:
            chan: The 1-indexed channel number

        Returns:
            Voltage
        """
        i,c = self.chan_to_ic(chan)
        
        return float(self.ask('i{};c{};MEAS:VOLT?'.format(i,c)))


    def _get_current(self, chan:int) -> float:
        """
        Get cmd for the chXX_i parameter
        
        Args:
            chan: The 1-indexed channel number

        Returns:
            Current
        """
        i,c = self.chan_to_ic(chan)
        
        return float(self.ask('i{};c{};MEAS:CURR?'.format(i,c)))


    def _set_ramp_slope(self, chan:int,
                              slope:float) -> None:
        """
        Set slope of chXX for ramp mode
        
        Args:
            chan The 1-indexed channel number
            slope Slope of chXX in V/ms
        """
        chan_id = self.chan_to_id(chan)
        self.write(chan_id + 'VOLT:SLOP {:.8f}'.format(slope))


    def _get_ramp_slope(self, chan:int) -> float:
        """
        Get slope of chXX
        
        Args:
            chan: The 1-indexed channel number
            
        Returns:
            chXX_slope parameter
        """
        chan_id = self.chan_to_id(chan)
        return self.ask(chan_id + 'VOLT:SLOP?')


    def _set_output_function(self, chan:int,
                                   outf: Union[int, str]) -> None:
        """
        Set how to perform output voltage update
        
        Args:
            chan: The 1-indexed channel number
            ouf: Mode
        """
        chan_id = self.chan_to_id(chan)
        
        if isinstance(outf,(int,float)):
            mode = str(outf)
        else:
            if outf=='exp':
                mode = '0'
            elif outf=='ramp':
                mode = '1'
        
        self.write(chan_id + 'trig:input ' + mode)


    def _get_output_function(self, chan:int) -> str:
        """
        Get output volage update  function
        
        Args:
            chan: The 1-indexed channel number
        
        Returns:
            mode
        """
        chan_id = self.chan_to_id(chan)
        mode = int(self.ask(chan_id + 'TRIG:INPUT?'))
        if mode == 0:
            return 'exp'
        elif mode == 1:
            return 'ramp'
        else:
            return 'ERROR'


    def _set_chan_range(self, chan:int,
                              volt: float) -> None:
        """
        Set output voltage range
        
        Args:
            chan : The 1-indexed channel number
            volt : Voltage range (1.2 or 12)
        """
        chan_id = self.chan_to_id(chan)
        self.write(chan_id + 'VOLT:RANGE ' + str(volt))


    def _get_chan_range(self, chan:int) -> str:
        """
        Get output voltage range
        
        Args:
            chan: The 1-indexed channel number
            
        Returns:
            volt: Output voltage range
        """
        chan_id = self.chan_to_id(chan)
        
        return self.ask(chan_id + 'VOLT:RANGE?')[:-2]


    def _set_chan_pos_sat(self, chan:int,
                                pos_sat: Union[int, str]) -> None:
        chan_id = self.chan_to_id(chan)
        if isinstance(pos_sat,(int,float)):
            self.write(chan_id + 'VOLT:SAT:POS {:.8f}'.format(pos_sat))
        elif isinstance(pos_sat,str):
            self.write(chan_id + 'VOLT:SAT:POS MAX')


    def _set_chan_neg_sat(self, chan:int,
                                neg_sat: Union[int, str]) -> None:
        chan_id = self.chan_to_id(chan)
        if isinstance(neg_sat,(int,float)):
            self.write(chan_id + 'VOLT:SAT:NEG {:.8f}'.format(neg_sat))
        elif isinstance(neg_sat,str):
            self.write(chan_id + 'VOLT:SAT:NEG MIN')


    def _get_chan_pos_sat(self, chan:int) -> str:
        chan_id = self.chan_to_id(chan)
        return self.ask(chan_id + 'VOLT:SAT:POS ?')


    def _get_chan_neg_sat(self, chan:int) -> str:
        chan_id = self.chan_to_id(chan)
        return self.ask(chan_id + 'VOLT:SAT:NEG ?')


    def _trig_chan(self, chan:int) -> None:
        """
        Send trigger signals
        
        Args:
            chan: The 1-indexed channel number
        """
        chan_id = self.chan_to_id(chan)
        self.write(chan_id + 'TRIG:INPUT:INIT')


    def _get_chan_state(self, chan:int) -> bool:
        """
        Get channel power state
        
        Args:
            chan: The 1-indexed channel number
            
        Returns:
            state: Power state 
        """
        chan_id = self.chan_to_id(chan)
        state = self.ask(chan_id + 'OUTP ?')
        
        if state == '1':
            return True
        elif state == '0':
            return False


    def _set_chan_state(self, chan:int,
                              state: bool) -> None:
        """
        Set channel power state
        
        Args:
            chan: The 1-indexed channel number
            state: power state
        """
        chan_id = self.chan_to_id(chan)
        if state:
            state_str = 'on'
        else:
            state_str = 'off'
        self.write(chan_id + 'OUTP ' + state_str)


    def _set_chan_name(self, chan:int,
                             name: str) -> None:
        """
        Set the name of the channel

        Args:
            chan: Channel to be named
            name: Name of the channel
        """
        chan_id = self.chan_to_id(chan)
        self.write(chan_id + 'chan:name "{}"'.format(name))


    def chan_to_ic(self, chan:int) -> Tuple[int]:
        """
        Indexing conversion from channel number (1 to 16)
        to iX;c;
        Args:
            chan: The 1-indexed channel number
            
        Returns:
            i,c: i=card number, c=channel number of card i
        """
        i = ceil(chan/4.)
        c = chan-(i-1)*4
        return i,c


    def chan_to_id(self, chan:int) -> str:
        i,c = self.chan_to_ic(chan)

        return 'i{};c{};'.format(i,c)
