# This Python file uses the following encoding: utf-8
# Loick Le Guevel, 2019
# Etienne Dumur <etienne.dumur@gmail.com>, 2021
# Simon Zihlmann <zihlmann.simon@gmail.com>, 2021
# Victor Millory <victor.millory@cea.fr>, 2021

from typing import Union, Tuple, Any
from functools import partial
from math import ceil
from time import sleep

from qcodes.instrument import Instrument
from qcodes.instrument import InstrumentChannel, ChannelList
from qcodes.parameters import MultiChannelInstrumentParameter
from qcodes.instrument import VisaInstrument
from qcodes.utils import validators as vals
from qcodes.parameters import create_on_off_val_mapping

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
            chan_num: The number of the channel in question.
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
                           get_parser=float,
                           set_cmd=partial(self._parent._set_voltage, chan_num),
                           inter_delay=self._parent._v_inter_delay,
                           post_delay=self._parent._v_post_delay,
                           step=self._parent._v_step,
                           vals=vals.Numbers(-12, 12)
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
                           vals=vals.Numbers(0, 1)
                           )

        self.add_parameter('output_mode',
                           label='Channel {} output mode'.format(chan_num),
                           docstring='Mode of the output {exp, ramp}.',
                           get_cmd=partial(self._parent._get_output_function, chan_num),
                           get_parser=str,
                           set_cmd=partial(self._parent._set_output_function, chan_num),
                           set_parser=str,
                           initial_value='exp',
                           vals=vals.Enum('ramp', 'exp')
                           )

        self.add_parameter('v_range',
                           label = 'Channel {} voltage range'.format(chan_num),
                           docstring='Range of the channel in volt.',
                           set_cmd=partial(self._parent._set_chan_range, chan_num),
                           set_parser=float,
                           get_cmd=partial(self._parent._get_chan_range, chan_num),
                           get_parser=float,
                           vals=vals.Numbers(1.2, 12)
                           )

        self.add_parameter('state',
                           docstring='State of the channel {on, off}.',
                           get_cmd=partial(self._parent._get_chan_state, chan_num),
                           set_cmd=partial(self._parent._set_chan_state, chan_num),
                           val_mapping=create_on_off_val_mapping(on_val='1',
                                                                 off_val='0')
                           )

        self.add_parameter('pos_sat',
                           get_cmd=partial(self._parent._get_chan_pos_sat, chan_num),
                           get_parser=str,
                           set_cmd=partial(self._parent._set_chan_pos_sat, chan_num),
                           set_parser=str,
                           initial_value=12
                           )

        self.add_parameter('neg_sat',
                           get_cmd=partial(self._parent._get_chan_neg_sat, chan_num),
                           get_parser=str,
                           set_cmd=partial(self._parent._set_chan_neg_sat, chan_num),
                           set_parser=str,
                           initial_value=-12
                           )

        self.add_parameter('bilt_name',
                           set_cmd=partial(self._parent._set_chan_name, chan_num),
                           set_parser=str,
                           initial_value=f'Chan{chan_num:02d}'
                           )

        self.add_parameter('synchronous_enable',
                           docstring='Is the channel in synchronous mode.',
                           get_cmd=None,
                           get_parser=bool,
                           set_cmd=None,
                           vals=vals.Bool(),
                           initial_value=False
                           )

        self.add_parameter('synchronous_delay',
                           docstring='Time between to voltage measurement in second.',
                           get_cmd=None,
                           get_parser=float,
                           set_cmd=None,
                           vals=vals.Numbers(1e-3, 10),
                           initial_value=1e-3
                           )

        self.add_parameter('synchronous_threshold',
                           docstring='Threshold to unblock communication in volt.',
                           get_cmd=None,
                           get_parser=float,
                           set_cmd=None,
                           vals=vals.Numbers(0, 1e-3),
                           initial_value=1e-5
                           )

        self.add_parameter('v_autorange',
                           docstring='If the voltage autorange is activated.',
                           get_cmd=partial(self._parent._get_chan_v_autorange, chan_num),
                           get_parser=bool,
                           set_cmd=partial(self._parent._set_chan_v_autorange, chan_num),
                           vals=vals.Bool(),
                           initial_value=False
                           )


    def start(self) -> None:
        """
        Switch on the channel.
        """
        self._parent._set_chan_state(self.chan_num, '1')


    def stop(self) -> None:
        """
        Switch off the channel.
        """
        self._parent._set_chan_state(self.chan_num, '0')

    def clear_alarm(self) -> None:
        """
        Clear the alarm and warnings of the channel.
        """
        self._parent._clear_chan_alarm(self.chan_num)

class iTestMultiChannelParameter(MultiChannelInstrumentParameter):
    """
    """

    def __init__(self, channels, param_name, *args, **kwargs):
        super().__init__(channels, param_name, *args, **kwargs)


class ITest(VisaInstrument):
    """
    This is the QCoDeS python driver for the iTest device from Bilt.
    """

    def __init__(self,name:str,
                      address:str,
                      num_chans:int=16,
                      init_start:bool=False,
                      synchronous_enable:bool=False,
                      synchronous_delay:float=1,
                      synchronous_threshold:float=1e-5,
                      v_inter_delay:float=5e-3,
                      v_post_delay:float=45e-3, # settling time to 99%
                      v_step:float=20e-3,
                      **kwargs: Any) -> None:
        """
        Instantiate the instrument.

        Args:
            name: The instrument name used by qcodes
            address: The VISA name of the resource
            num_chans: Number of channels to assign. Default: 16
            init_start: If true: set all channels to 0V, 12V range, exponential mode and switch
                them on.
            synchronous_enable: If true, block the communication until the set voltage
                is reached. The communication is block through a simple while loop
                with a waiting time "synchronous_delay" at each iteration until the
                set voltage and the measured voltage difference is below
                "synchronous_threshold".
            synchronous_delay: Time between to voltage measurement in second.
            synchronous_threshold: Threshold to unblock communication in volt.
            v_inter_delay: delay in units of s between setting new value of the voltage parameter, defaults to 5e-3.
            v_post_delay: delay in units of s after setting voltage parameter to final value, defaults to 45e-3.
            v_step: max step size of the voltage parameter in units of V, defaults to 20e-3.

        Returns:
            ITest object
        """
        super().__init__(name, address=address,
                               terminator='\n',
                               device_clear=False,
                               **kwargs)

        self.idn = self.get_idn()
        self.num_chans = num_chans
        self._v_inter_delay = v_inter_delay
        self._v_post_delay = v_post_delay
        self._v_step = v_step
        self.chan_range = range(1,self.num_chans+1)

        # Create the channels
        channels = ChannelList(parent=self,
                               name='Channels',
                               chan_type=iTestChannel,
                               multichan_paramclass=iTestMultiChannelParameter)

        for i in self.chan_range:

            channel = iTestChannel(self, name='chan{:02}'.format(i),
                                         chan_num=i)
            channels.append(channel)
            self.add_submodule('ch{:02}'.format(i),channel)

        channels.lock()
        self.add_submodule('channels',channels)

        if init_start:
            for channel in self.channels:
                channel.stop()
                channel.v.set(0)
                channel.v_range(12)
                channel.v_autorange(False)
                channel.synchronous_enable(False)
                channel.output_mode('exp')
                channel.start()

        self.connect_message()

    def _set_voltage(self, chan:int,
                           v_set:float) -> None:
        """
        Set cmd for the chXX_v parameter

        Args:
            chan: The 1-indexed channel number
            v_set: The target voltage
        """
        chan_id = self.chan_to_id(chan)
        self.write('{}VOLT {:.8f}'.format(chan_id, v_set))
        self.write(chan_id + 'TRIG:INPUT:INIT')
        if self.channels[chan-1].synchronous_enable():
            v = self._get_voltage(chan)
            while abs(v_set - v)>=self.channels[chan-1].synchronous_threshold():
                sleep(self.channels[chan-1].synchronous_delay())
                v = self._get_voltage(chan)

    def _get_voltage(self, chan:int) -> float:
        """
        Get cmd for the chXX_v parameter

        Args:
            chan: The 1-indexed channel number

        Returns:
            Voltage
        """
        chan_id = self.chan_to_id(chan)

        return float(self.ask('{}MEAS:VOLT?'.format(chan_id)))

    def _get_current(self, chan:int) -> float:
        """
        Get cmd for the chXX_i parameter

        Args:
            chan: The 1-indexed channel number

        Returns:
            Current
        """
        chan_id = self.chan_to_id(chan)

        return float(self.ask('{}MEAS:CURR?'.format(chan_id)))

    def _set_ramp_slope(self, chan:int,
                              slope:float) -> None:
        """
        Set slope of chXX for ramp mode

        Args:
            chan The 1-indexed channel number
            slope Slope of chXX in V/ms
        """
        chan_id = self.chan_to_id(chan)
        self.write('{}VOLT:SLOP {:.8f}'.format(chan_id, slope))

    def _get_ramp_slope(self, chan:int) -> str:
        """
        Get slope of chXX

        Args:
            chan: The 1-indexed channel number

        Returns:
            chXX_slope parameter
        """
        chan_id = self.chan_to_id(chan)
        return self.ask('{}VOLT:SLOP?'.format(chan_id))

    def _set_output_function(self, chan:int,
                                   outf:str) -> None:
        """
        Set how to perform output voltage update

        Args:
            chan: The 1-indexed channel number
            ouf: Mode
        """
        chan_id = self.chan_to_id(chan)

        if outf=='exp':
            mode = '0'
        elif outf=='ramp':
            mode = '1'
        else:
            raise ValueError(f'Got unexpected output function mode: {outf}.')

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
            raise ValueError('Got unexpected output function mode: {}.'.format(mode))

    def _set_chan_range(self, chan:int,
                              volt: float) -> None:
        """
        Set output voltage range

        Args:
            chan : The 1-indexed channel number
            volt : Voltage range (1.2 or 12)
        """
        chan_id = self.chan_to_id(chan)
        if self._get_chan_state(chan)=='1':
            print('Channel {} is on and therefore the range cannot be changed. Turn it off first.'.format(chan))
        else:
            # update the pos and neg saturation parameter
            self._set_chan_pos_sat(chan, abs(volt))
            self._set_chan_neg_sat(chan, -abs(volt))
            # self.channels[chan-1].v.vals=vals.Numbers(-abs(volt), abs(volt)) #does not work, throws an error at init since channels are not yet attached to instrument
            # --> solve problem by moving all the communication functions to the level of the channel and not on the leel of instrument. Like this other parameters from the same channel are easily accessible via self.parameter
            # change the range
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

    def _get_chan_v_autorange(self, chan:int) -> bool:
            """
            Get the channel voltage autorange state

            Args:
                chan: The 1-indexed channel number

            Returns:
                chXX_v_autorange parameter
            """
            chan_id = self.chan_to_id(chan)
            v_autorange_state = self.ask('{}VOLT:RANGE:AUTO?'.format(chan_id))

            if v_autorange_state in ['1', '0'] :
                return True if v_autorange_state=='1' else False
            else:
                raise ValueError('Unknown state output: {}'.format(v_autorange_state))
            return False

    def _set_chan_v_autorange(self, chan:int, state:bool) -> None:
        """
        Set channel voltage autorange state

        Args:
            chan: The 1-indexed channel number
            state: power state
        """
        chan_id = self.chan_to_id(chan)
        self.write(chan_id + 'VOLT:RANGE:AUTO {}'.format('1' if(state) else '0') )

    def _set_chan_pos_sat(self, chan:int,
                                pos_sat: Union[float, str]) -> None:
        chan_id = self.chan_to_id(chan)
        if isinstance(pos_sat,(int,float)):
            self.write(chan_id + 'VOLT:SAT:POS {:.8f}'.format(pos_sat))
        elif isinstance(pos_sat,str):
            self.write(chan_id + 'VOLT:SAT:POS MAX')

    def _set_chan_neg_sat(self, chan:int,
                                neg_sat: Union[float, str]) -> None:
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

    def _get_chan_state(self, chan:int) -> str:
        """
        Get channel power state

        Args:
            chan: The 1-indexed channel number

        Returns:
            state: Power state
        """
        chan_id = self.chan_to_id(chan)
        state = self.ask(chan_id + 'OUTP ?')

        if state in ['1', '0'] :
            return state
        else:
            raise ValueError('Unknown state output: {}'.format(state))

    def _set_chan_state(self, chan:int,
                              state:str) -> None:
        """
        Set channel power state

        Args:
            chan: The 1-indexed channel number
            state: power state
        """
        chan_id = self.chan_to_id(chan)
        self.write(chan_id + 'OUTP ' + state)

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

    def _clear_chan_alarm(self, chan:int) -> None:
        """
        Clear the alarm/warning for a given channel

        Args:
            chan: The 1-indexed channel number
        """
        chan_id = self.chan_to_id(chan)
        self.write(chan_id + 'LIM:CLEAR')
        self.write(chan_id + 'STAT:CLEAR')

    def chan_to_ic(self, chan:int) -> Tuple[int, int]:
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

    def set_dacs_zero(self) -> None:
        """
        Ramp all voltages to zero.
        """
        for ch in self.channels:
            ch.v(0)

    def print_dac_voltages(self) -> None:
        """
        Prints the voltage of all channels to cmdl.
        """
        for ch in self.channels:
            print('voltage on {}:{} {}'.format(ch.name, ch.v(), ch.v.unit))
