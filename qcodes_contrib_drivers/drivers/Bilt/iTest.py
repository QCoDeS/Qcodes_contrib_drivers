# -*- coding: utf-8 -*-
"""
Created on Tue Jan  8 10:07:31 2019

@author: ll252805
"""

import time
import visa
import numpy as np
from functools import partial
from math import ceil

from qcodes.instrument.channel import InstrumentChannel, ChannelList
from qcodes.instrument.channel import MultiChannelInstrumentParameter
from qcodes.instrument.visa import VisaInstrument
from qcodes.utils import validators as vals

class iTestChannel(InstrumentChannel):
    """
    A single channel of iTest
    """
    
    def __init__(self,parent,name,chan_num):
        """
        Args:
            parent (Instrument): The instrument to which the channel is
                attached.
            name (str): The name of the channel.
            chan_num (int): The number of the channel in question
        """
        super().__init__(parent,name)
        self.chan_num = chan_num
        
        i,c = round(chan_num/4.)+1,chan_num%4
        self.chan_id = 'i{};c{};'.format(i,c)
        
        # Channel Voltages
        self.add_parameter('v',
                           label='Channel {} voltage'.format(chan_num),
                           unit='V',
                           get_cmd=partial(self._parent._get_voltage,chan_num),
                           set_cmd=partial(self._parent._set_voltage,chan_num),
                           get_parser=float
                           )
        
        
        # Channel Voltages and trigger
        self.add_parameter('v_and_trig',
                           label='Channel {} voltage'.format(chan_num),
                           unit='V',
                           get_cmd=partial(self._parent._get_voltage,chan_num),
                           set_cmd=partial(self._parent._set_voltage,chan_num,trigger=True),
                           get_parser=float
                           )
           
        self.add_parameter('i',
                           label='Channel {} current'.format(chan_num),
                           unit='A',
                           get_cmd=partial(self._parent._get_current,chan_num),
                           get_parser=float
                           )
        # Channel Slopes
        self.add_parameter('ramp_slope',
                           label='Channel {} ramp slope'.format(chan_num),
                           unit='V/ms',
                           get_cmd=partial(self._parent._get_ramp_slope,chan_num),
                           set_cmd=partial(self._parent._set_ramp_slope,chan_num),
                           get_parser=float,
                           set_parser = float
                           )
        
        self.add_parameter('output_mode',
                           label='Channel {} output mode'.format(chan_num),
                           get_cmd=partial(self._parent._get_output_function,chan_num),
                           set_cmd=partial(self._parent._set_output_function,chan_num),
                           get_parser=str
                           )
        
        self.add_parameter('range',
                           label = 'Channel {} voltage range'.format(chan_num),
                           set_cmd = partial(self._parent._set_chan_range,chan_num),
                           get_cmd = partial(self._parent._get_chan_range,chan_num),
                           get_parser = float)
        
        self.add_parameter('state',
                           get_cmd = partial(self._parent._get_chan_state,chan_num),
                           get_parser = bool,
                           set_cmd = partial(self._parent._set_chan_state,chan_num),
                           set_parser = bool)
        
        self.add_parameter('pos_sat',
                           get_cmd = partial(self._parent._get_chan_pos_sat,
                                             chan_num),
                           get_parser = str,
                           set_cmd = partial(self._parent._set_chan_pos_sat,
                                             chan_num))
        
        self.add_parameter('neg_sat',
                           get_cmd = partial(self._parent._get_chan_neg_sat,
                                             chan_num),
                           get_parser = str,
                           set_cmd = partial(self._parent._set_chan_neg_sat,
                                             chan_num))    
                           
                           
        self.add_parameter('trigger',
                           get_cmd = partial(self._parent._trig_chan,chan_num))
                           
        self.add_parameter('bilt_name',
                           set_cmd = partial(self._parent._set_chan_name,chan_num),
                           set_parser = str)    
    
        self.bilt_name(f'Chan{chan_num:02d}')

        self.chan_num = chan_num
        # self.full_name = self._parent.name + "_" + name
#    def trigger(self):
#        """
#        Send trigger signals for channel
#        """
#        self._parent._trig_chan(self.chan_num)
        
    def start(self):
        self._parent._set_chan_state(self.chan_num,1)
    
    def stop(self):
        self._parent._set_chan_state(self.chan_num,0)


class iTestMultiChannelParameter(MultiChannelInstrumentParameter):
    """
    """
    
    def __init__(self, channels, param_name, *args, **kwargs):
        super().__init__(channels, param_name, *args, **kwargs)

    def trigger(self,*args,**kwargs):
        print(args,kwargs)
        
class ITest(VisaInstrument):
    """
    
    """
    
    def __init__(self,name,address,num_chans=16,init_start=False,**kwargs):
        """
        Instantiate the instrument.
        
        Args:
            name (str): The instrument name used by qcodes
            address (str): The VISA name of the resource
            num_chans (int): Number of channels to assign. Default: 16
            
        Returns:
            ITest object
        """
        super().__init__(name,address=address,terminator='\n',
                         device_clear=False) #[?]  Needed, else NotImplementedError
        
    

        
        self.idn = self.get_idn()
        self.num_chans = num_chans
        self.chan_range = range(1,self.num_chans+1)
        
        channels = ChannelList(self, "Channels", iTestChannel,
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
        
    def _set_voltage(self,chan,v_set,trigger=False):
        """
        Set cmd for the chXX_v parameter
        
        Args:
            chan (int): The 1-indexed channel number
            v_set (float): The target voltage
        """
        i,c = self.chan_to_ic(chan)
        self.write('i{};c{};VOLT {:.8f}'.format(i,c,v_set))
        
        if trigger:
            self._trig_chan(chan)
            
    def _get_voltage(self,chan):
        """
        Get cmd for the chXX_v parameter
        
        Args:
            chan (int): The 1-indexed channel number

        Returns:
            (float) Voltage
        """
        i,c = self.chan_to_ic(chan)
        v = self.ask('i{};c{};MEAS:VOLT?'.format(i,c))
        return float(v)
    
    def _get_current(self,chan):
        """
        Get cmd for the chXX_i parameter
        
        Args:
            chan (int): The 1-indexed channel number

        Returns:
            (float) Current
        """
        i,c = self.chan_to_ic(chan)
        curr = self.ask('i{};c{};MEAS:CURR?'.format(i,c))
        return float(curr)
    
    

    def _set_ramp_slope(self,chan,slope):
        """
        Set slope of chXX for ramp mode
        
        Args:
            chan (int): The 1-indexed channel number
            slope (float): Slope of chXX in V/ms
            
        Returns:
            (float): chXX_slope parameter
        """
        chan_id = self.chan_to_id(chan)
        self.write(chan_id + 'VOLT:SLOP {:.8f}'.format(slope))


    def _get_ramp_slope(self,chan):
        """
        Get slope of chXX
        
        Args:
            chan (int): The 1-indexed channel number
            
        Returns:
            (float): chXX_slope parameter
        """
        chan_id = self.chan_to_id(chan)
        slope = self.ask(chan_id + 'VOLT:SLOP?')
        return slope

    def _set_output_function(self,chan,outf):
        """
        Set how to perform output voltage update
        
        Args:
            chan (int): The 1-indexed channel number
            ouf (int or str): Mode
        """
        chan_id = self.chan_to_id(chan)
        if isinstance(outf,(int,float)):
            mode = str(outf)
        else:
            if outf=="exp":
                mode = "0"
            elif outf=="ramp":
                mode = "1"
        self.write(chan_id + "trig:input " + mode)

    def _get_output_function(self,chan):
        """
        Get output volage update  function
        Args:
            chan (int): The 1-indexed channel number
        
        Returns:
            mode
        """
        chan_id = self.chan_to_id(chan)
        mode = int(self.ask(chan_id + 'TRIG:INPUT?'))
        if mode == 0:
            return "exp"
        elif mode == 1:
            return "ramp"
        else:
            return "ERROR"
    
    def _set_chan_range(self,chan,volt):
        """
        Set output voltage range
        
        Args:
            chan (int): The 1-indexed channel number
            volt (float): Voltage range (1.2 or 12)
        """
        chan_id = self.chan_to_id(chan)
        self.write(chan_id + "VOLT:RANGE " + str(volt))
    
    def _get_chan_range(self,chan):
        """
        Get output voltage range
        
        Args:
            chan (int): The 1-indexed channel number
            
        Returns:
            volt (str): Output voltage range
        """
        chan_id = self.chan_to_id(chan)
        volt = self.ask(chan_id + "VOLT:RANGE?")
        return volt[:-2]
    
    def _set_chan_pos_sat(self,chan,pos_sat):
        chan_id = self.chan_to_id(chan)
        if isinstance(pos_sat,(int,float)):
            self.write(chan_id + "VOLT:SAT:POS {:.8f}".format(pos_sat))
        elif isinstance(pos_sat,str):
            self.write(chan_id + "VOLT:SAT:POS MAX")
    
    def _set_chan_neg_sat(self,chan,neg_sat):
        chan_id = self.chan_to_id(chan)
        if isinstance(neg_sat,(int,float)):
            self.write(chan_id + "VOLT:SAT:NEG {:.8f}".format(neg_sat))
        elif isinstance(neg_sat,str):
            self.write(chan_id + "VOLT:SAT:NEG MIN")
    
    def _get_chan_pos_sat(self,chan):
        chan_id = self.chan_to_id(chan)
        pos_sat = self.ask(chan_id + "VOLT:SAT:POS ?")
        return pos_sat
    
    def _get_chan_neg_sat(self,chan):
        chan_id = self.chan_to_id(chan)
        neg_sat = self.ask(chan_id + "VOLT:SAT:NEG ?")
        return neg_sat
    
    def _trig_chan(self,chan):
        """
        Send trigger signals
        
        Args:
            chan (int): The 1-indexed channel number
        """
        chan_id = self.chan_to_id(chan)
        self.write(chan_id + "TRIG:INPUT:INIT")
    
    
    
    def _get_chan_state(self,chan):
        """
        Get channel power state
        
        Args:
            chan (int): The 1-indexed channel number
            
        Returns:
            state (bool): Power state 
        """
        chan_id = self.chan_to_id(chan)
        state = self.ask(chan_id + 'OUTP ?')
        
        if state == '1':
            return True
        elif state == '0':
            return False

    
    def _set_chan_state(self,chan,state):
        """
        Set channel power state
        
        Args:
            chan (int): The 1-indexed channel number
            state (bool): power state
        """
        chan_id = self.chan_to_id(chan)
        if state:
            state_str = 'on'
        else:
            state_str = 'off'
        self.write(chan_id + 'OUTP ' + state_str)


    def _set_chan_name(self,chan,name):
        """
        """
        chan_id = self.chan_to_id(chan)
        self.write(chan_id + 'chan:name "{}"'.format(name))
        
    def chan_to_ic(self,chan):
        """
        Indexing conversion from channel number (1 to 16)
        to iX;c;
        Args:
            chan (int): The 1-indexed channel number
            
        Returns:
            i,c (int tuple): i=card number, c=channel number of card i
        """
        i = ceil(chan/4.)
        c = chan-(i-1)*4
        return i,c
    

    def chan_to_id(self,chan):
        i,c = self.chan_to_ic(chan)
        return 'i{};c{};'.format(i,c)
    



if __name__=='__main__':    
     import random    

     iTest_address = "TCPIP0::192.168.150.102::5025::SOCKET"

     instr = ITest('DAC' + str(random.randint(0,1000)), iTest_address)
#
#     instr.channels[:].start.get()
#     instr.ch03.v.get()
#     instr.channels[2].v.get()
#     instr.channels[:].v.set(0.2)
#     instr.channels[1:3].v.set(0.1)
#     print(instr.channels[:].v.get())
#     instr.channels[:].stop.get()