# This Python file uses the following encoding: utf-8

import numpy as np
from typing import Tuple

from qcodes import (Instrument, VisaInstrument,
                    ManualParameter, MultiParameter,
                    validators as vals)
from qcodes.instrument.channel import InstrumentChannel
from qcodes.utils.validators import Numbers, Enum, Ints


class HS9002BChannel(InstrumentChannel):
    """
    Class to hold the Holzworth channels, i.e.
    CH1 and CH2.
    """

    def __init__(self, parent: Instrument, name: str, channel: str) -> None:
        """
        Args:
            parent: The Instrument instance to which the channel is
                to be attached.
            name: The 'colloquial' name of the channel
            channel: The name used by the Holzworth, i.e. either
                'CH1' or 'CH2'
        """

        super().__init__(parent, name)

        '''
        This block of function is there to determine the maximum and minimum values
        of the RF source and give it as a float in Hz, dBm and degree
        '''
        self._min_f = self._parse_f_unit(self.ask_raw(':{}:Freq:MIN?'.format(channel)))
        self._max_f = self._parse_f_unit(self.ask_raw(':{}:Freq:MAX?'.format(channel)))
        self._min_pwr = self._parse_pwr_unit(self.ask_raw(':{}:PWR:MIN?'.format(channel)))
        self._max_pwr = self._parse_pwr_unit(self.ask_raw(':{}:PWR:MAX?'.format(channel)))
        self._min_phase = self._parse_phase_unit(self.ask_raw(':{}:PHASE:MIN?'.format(channel)))
        self._max_phase = self._parse_phase_unit(self.ask_raw(':{}:PHASE:MAX?'.format(channel)))

        '''
        All parameters of the RF source are added. Since the command set_cmd cannot handle
        a response from the device, we have created a function to deal with its reply
        '''
        self.add_parameter(name='state',
                           label='State',
                           get_parser=str,
                           get_cmd=self._get_state,
                           set_cmd=self._set_state,
                           vals=Enum('ON', 'OFF'))

        self.add_parameter(name='power',
                           label='Power',
                           get_parser=float,
                           get_cmd=self._get_pwr,
                           set_cmd= self._set_pwr,
                           unit='dBm',
                           vals=Numbers(min_value=self._min_pwr,
                                        max_value=self._max_pwr))

        self.add_parameter(name='frequency',
                           label='Frequency',
                           get_parser=float,
                           get_cmd=self._get_f,
                           set_cmd= self._set_f,
                           unit='Hz',
                           vals=Numbers(min_value=self._min_f,
                                        max_value=self._max_f))

        self.add_parameter(name='phase',
                           label='Phase',
                           get_parser=float,
                           get_cmd=self._get_phase,
                           set_cmd= self._set_phase,
                           unit='deg',
                           vals=Numbers(min_value=self._min_phase,
                                        max_value=self._max_phase))

        self.add_parameter(name='temp',
                           label='Temperature',
                           get_parser=str,
                           get_cmd=self._get_temp,
                           unit='C')

        self.channel = channel

    def _parse_f_unit(self, raw_str:str) -> float:
        f, unit = raw_str.split(' ')
        unit_dict = {
            'GHz': 1e9,
            'MHz': 1e6,
            'kHz': 1e3
        }
        if unit not in unit_dict.keys():
            raise RuntimeError('{} is not in {}. Cannot parse {}.'.format(unit, unit_dict.keys(), unit))
        frequency = float(f) * unit_dict[unit]
        return frequency

    def _parse_pwr_unit(self, raw_str:str) -> float:
        try:
            power = float(raw_str)
        except:
            pwr, unit = raw_str.split(' ')
            power = float(pwr)
        return power

    def _parse_phase_unit(self, raw_str:str) -> float:
        try:
            phase = float(raw_str)
        except:
            phase = float(raw_str[:-3])
        return phase

    def _get_state(self) -> float:
        return self.ask(':{}:PWR:RF?'.format(self.channel))

    def _set_state(self, st) -> None:
        write_str = ':{}:PWR:RF:'.format(self.channel) + str(st)
        read_str = self.ask(write_str)
        if read_str != 'RF POWER '+str(st):
            raise RuntimeError('{} is not \'State Set\'. Setting state did not work'.format(read_str))

    def _get_f(self) -> float:
        raw_str = self.ask(':{}:FREQ?'.format(self.channel))
        return self._parse_f_unit(raw_str)

    def _set_f(self, f) -> None:
        write_str = ':{}:FREQ:'.format(self.channel) + str(f/1e9) + 'GHz'
        read_str = self.ask(write_str)
        if read_str != 'Frequency Set':
            raise RuntimeError('{} is not \'Frequency Set\'. Setting frequency did not work'.format(read_str))

    def _get_pwr(self) -> float:
        raw_str = self.ask(':{}:PWR?'.format(self.channel))
        return self._parse_pwr_unit(raw_str)

    def _set_pwr(self, pwr) -> None:
        write_str = ':{}:PWR:'.format(self.channel) + str(pwr) + 'dBm'
        read_str = self.ask(write_str)
        if read_str != 'Power Set':
            raise RuntimeError('{} is not \'Power Set\'. Setting power did not work'.format(read_str))

    def _get_phase(self) -> float:
        raw_str = self.ask(':{}:PHASE?'.format(self.channel))
        return self._parse_phase_unit(raw_str)

    def _set_phase(self, ph) -> None:
        write_str = ':{}:PHASE:'.format(self.channel) + str(float(ph)) + 'deg'
        read_str = self.ask(write_str)
        if read_str != 'Phase Set':
            raise RuntimeError('{} is not \'Phase Set\'. Setting phase did not work'.format(read_str))

    def _get_temp(self) -> float:
        raw_str = self.ask(':{}:TEMP?'.format(self.channel))
        T = raw_str.split(' ')[-1][:-1]
        return T


class HS9002B(VisaInstrument):
    """
    This is the qcodes driver for the
    """
    def __init__(self, name: str, address: str, **kwargs) -> None:
        """
        Args:
            name: Name to use internally in QCoDeS
            address: VISA ressource address
        """
        super().__init__(name, address, terminator='\n', **kwargs)

        self.add_parameter(name='channel_names',
                           label='Channels',
                           get_parser=str,
                           get_cmd=self._get_channels) #No of ports

        """
        The driver has been tried to be written also for other similar models from Holzworth
        however we could not test it. Hence only the bulletproof version have been listed as
        known models
        """
        model = self.ask_raw(':IDN?').split(', ')[1]
        knownmodels = ['HS9002B']
        if model not in knownmodels:
            kmstring = ('{}, '*(len(knownmodels)-1)).format(*knownmodels[:-1])
            kmstring += 'and {}.'.format(knownmodels[-1])
            raise ValueError('Unknown model. Known model are: ' + kmstring)

        # Add the channel to the instrument
        channels = self.ask_raw(':ATTACH?').split(':')[2:-1]
        for ch_name in channels:
            channel = HS9002BChannel(self, ch_name, ch_name)
            self.add_submodule(ch_name, channel)

        # display parameter
        # Parameters NOT specific to a channel still belong on the Instrument object
        # In this case, the Parameter controls the text on the display

        self.connect_message()

    def _get_channels(self) -> float:
        raw_str = self.ask(':ATTACH?')
        channels = raw_str.split(':')[2:-1]
        return channels
