# -*- coding: utf-8 -*-
"""
File: ZIMFLI.py
Date: Feb / Mar 2019
Author: Michael Wagener, FZJ / ZEA-2, m.wagener@fz-juelich.de
Author: Sarah Fleitmann, FZJ / ZEA-2, s.fleitmann@fz-juelich.de
Author: Rene Otten and other, RWTH Aachen
Purpose: Main instrument driver for the Zurich Instruments Lock-In Amplifier
"""


#import os, platform # used in version() if the git command is activated
import time
import logging
from functools import partial
from math import sqrt
from enum import IntEnum
from typing import Callable, List, Union, Dict, Tuple
import numpy as np

softSweep = True  # set to False to disable the software sweep function and
                  #  use only the hardware sweep if it is installed (MD-Option)

realFlag = True   # False=use simulation
try:
    import zhinst.utils
    import zhinst.ziPython
except ImportError:
    realFlag = False
    print("no zhinst.* found")
    #raise ImportError('''Could not find Zurich Instruments Lab One software.
    #                     Please refer to the Zi MFLI User Manual for
    #                     download and installation instructions.
    #                  ''')

from qcodes.instrument.parameter import MultiParameter, BufferedSweepableParameter, BufferedReadableArrayParameter
from qcodes.instrument.base import Instrument
from qcodes.instrument.channel import InstrumentChannel, ChannelList
from qcodes.utils import validators as vals

log = logging.getLogger(__name__)

bufferedConfig = {}


class Mode(IntEnum):
    """
    Mapping the mode for the ZIMFLI._setter and ._getter methods
    """
    INT = 0
    DOUBLE = 1
    SAMPLE = 2


class AUXInputChannel(InstrumentChannel): # doc done **************************
    """
    The device has two auxiliary inputs. Because of the demodulator functionality
    the input values are only available as fields in the dict of the demodulator
    sample reading.
    Parameters:
        averaging: Defines the number of samples on the input to average as a
            power of two. Possible values are in the range [0, 16]. A value of
            0 corresponds to the sampling rate of the auxiliary input's ADC.
        sample: This returns the same dict as the demodulator parameter sample.
            The auxiliary input values are available as fields in a demodulator
            sample and are aligned by timestamp with the demodulator output.
    """
    def __init__(self, parent:'ZIMFLI', name: str, channum: int) -> None:
        """
        Creates a new AUXInputChannel
        Args:
            parent: the internal QCoDeS name of the instrument the channel belongs to
            name: the internal QCoDeS name of the channel itself
            channum: the Index of the channel
        """
        super().__init__(parent, name)
        self.add_parameter('averaging',
                           label='Number of samples to average',
                           get_cmd=partial(self._parent._getter, 'auxins',
                                           channum-1, Mode.INT, 'averaging'),
                           set_cmd=partial(self._parent._setter, 'auxins',
                                           channum-1, Mode.INT, 'averaging'),
                           vals=vals.Ints(0, 16),
                           docstring="Defines the number of samples on the input"
                                     " to average as a power of two. Possible"
                                     " values are in the range [0, 16]. A value"
                                     " of 0 corresponds to the sampling rate of"
                                     " the auxiliary input's ADC."
                           )
        self.add_parameter('sample',
                           label='Demodulator sample',
                           get_cmd=partial(self._parent._getter, 'demods', # !!!
                                           channum-1, Mode.SAMPLE, 'sample'),
                           set_cmd=False,
                           docstring="This returns the same dict as the demodulator"
                                     " parameter sample. The auxiliary input values"
                                     " are available as fields in a demodulator sample"
                                     " and are aligned by timestamp with the"
                                     " demodulator output."
                           )
        #self.add_parameter('value1',
        #                   label='Auxiliary Input value',
        #                   unit='V',
        #                   get_cmd=partial(self._parent._getter, 'auxins',
        #                                   channum-1, Mode.DOUBLE, 'value/0'),
        #                   set_cmd=False)
        #self.add_parameter('value2',
        #                   label='Auxiliary Input value',
        #                   unit='V',
        #                   get_cmd=partial(self._parent._getter, 'auxins',
        #                                   channum-1, Mode.DOUBLE, 'value/1'),
        #                   set_cmd=False)
        # --> Not available if demodulator is implemented


class AUXOutputChannel(InstrumentChannel): # doc done *************************
    """"
    The device has four auxiliary outputs.
    Parameters:
        scale: Multiplication factor to scale the signal.
        preoffset: Add a pre-offset to the signal before scaling is applied.
        offset: Add the specified offset voltage to the signal after scaling.
        limitlower: Lower limit for the signal at the Auxiliary Output.
            A smaller value will be clipped. Can have a value between -10 an +10 V.
        limitupper: Upper limit for the signal at the Auxiliary Output.
            A larger value will be clipped. Can have a value between -10 an +10 V.
        channel: channel according to the selected signal source
        output: signal source of the signal to amplify. Allowed values are
            'Demod X', 'Demod Y', 'Demod R', 'Demod THETA',
            'TU Filtered Value', 'TU Output Value'.
            With the MD option installed, this list is extended by
            'PID Out', 'PID Shift', 'PID Error'.
        value: (ReadOnly) Voltage present on the Auxiliary Output.
            Auxiliary Output Value = (Signal + Preoffset) * Scale + Offset
    """

    def __init__(self, parent: 'ZIMFLI', name: str, channum: int) -> None:
        """
        Creates a new AUXOutputChannel
        Args:
            parent: the Instrument the Channel belongs to, in this case 'ZIMFLI'
            name: the internal QCoDeS name of the channel
            channum: the channel number of the current channel, used as index
                in the ChannelList of the OutputChannels
        """
        super().__init__(parent, name)
        self.add_parameter('scale',
                           label='scale',
                           unit='',
                           get_cmd=partial(self._parent._getter, 'auxouts',
                                           channum - 1, Mode.DOUBLE, 'scale'),
                           set_cmd=partial(self._parent._setter, 'auxouts',
                                           channum - 1, Mode.DOUBLE, 'scale'),
                           vals=vals.Numbers(),
                           docstring="Multiplication factor to scale the signal.")
        self.add_parameter('preoffset',
                           label='preoffset',
                           unit='signal units',
                           get_cmd=partial(self._parent._getter, 'auxouts',
                                           channum - 1, Mode.DOUBLE, 'preoffset'),
                           set_cmd=partial(self._parent._setter, 'auxouts',
                                           channum - 1, Mode.DOUBLE, 'preoffset'),
                           vals=vals.Numbers(),
                           docstring="Add a pre-offset to the signal before scaling is applied.")
        self.add_parameter('offset',
                           label='offset',
                           unit='V',
                           get_cmd=partial(self._parent._getter, 'auxouts',
                                           channum - 1, Mode.DOUBLE, 'offset'),
                           set_cmd=partial(self._parent._setter, 'auxouts',
                                           channum - 1, Mode.DOUBLE, 'offset'),
                           vals=vals.Numbers(),
                           docstring="Add the specified offset voltage to the signal after scaling.")
        self.add_parameter('limitlower',
                           label='Lower limit',
                           unit='V',
                           get_cmd=partial(self._parent._getter, 'auxouts',
                                           channum - 1, Mode.DOUBLE, 'limitlower'),
                           set_cmd=partial(self._parent._setter, 'auxouts',
                                           channum - 1, Mode.DOUBLE, 'limitlower'),
                           vals=vals.Numbers(-10, 10),
                           docstring="Lower limit for the signal at the Auxiliary Output."
                                     " A smaller value will be clipped. Can have a value"
                                     " between -10 an +10 V.")
        self.add_parameter('limitupper',
                           label='Upper limit',
                           unit='V',
                           get_cmd=partial(self._parent._getter, 'auxouts',
                                           channum - 1, Mode.DOUBLE, 'limitupper'),
                           set_cmd=partial(self._parent._setter, 'auxouts',
                                           channum - 1, Mode.DOUBLE, 'limitupper'),
                           vals=vals.Numbers(-10, 10),
                           docstring="Upper limit for the signal at the Auxiliary Output."
                                     " A larger value will be clipped. Can have a value"
                                     " between -10 an +10 V.")
        self.add_parameter('channel',
                           label='Channel',
                           unit='',
                           get_cmd=partial(self._parent._getter, 'auxouts',
                                           channum - 1, Mode.INT, 'demodselect'),
                           set_cmd=partial(self._parent._setter, 'auxouts',
                                           channum - 1, Mode.INT, 'demodselect'),
                           get_parser=lambda x: x+1,  # internal: 0, 1, ...
                           set_parser=lambda x: x-1,  # for the user: 1, 2, ...
                           vals=vals.Ints( 1, self._parent.demodulator_no ),
                           docstring="Channel according to the selected signal source.")
        outputvalmapping = {'Demod X': 0,
                            'Demod Y': 1,
                            'Demod R': 2,
                            'Demod THETA': 3,
                            'TU Filtered Value': 11,
                            'TU Output Value': 13}
        if 'MD' in self._parent.options:
            outputvalmapping.update({'PID Out': 5,
                                     'PID Shift': 9,
                                     'PID Error': 10})
        self.add_parameter('output',
                           label='Output',
                           unit='',
                           get_cmd=partial(self._parent._getter, 'auxouts',
                                           channum - 1, Mode.INT, 'outputselect'),
                           set_cmd=partial(self._parent._setter, 'auxouts',
                                           channum - 1, Mode.INT, 'outputselect'),
                           val_mapping=outputvalmapping,
                           docstring="Signal source of the signal to amplify."
                                     " Allowed values are: 'Demod X', 'Demod Y',"
                                     " 'Demod R', 'Demod THETA', 'TU Filtered Value',"
                                     " 'TU Output Value'. With the MD option"
                                     " installed, this list is extended by"
                                     " 'PID Out', 'PID Shift', 'PID Error'.")
        self.add_parameter('value',
                           label='Value',
                           unit='V',
                           get_cmd=partial(self._parent._getter, 'auxouts',
                                           channum - 1, Mode.DOUBLE, 'value'),
                           set_cmd=False,
                           docstring="""
                                     (ReadOnly) Voltage present on the Auxiliary Output.
                                     Value = (Signal + Preoffset) * Scale + Offset
                                     """
                           )


class DemodulatorChannel(InstrumentChannel): # doc done ***********************
    """
    The Lock-In-Amplifier has two demodulator channels. Not all parameters are
    accessible for the second channel. If the MD option is installed, there
    are four channels available.
    Parameters accessible by all channels:
        bypass: Allows to bypass the demodulator low-pass filter, thus increasing
            the bandwidth.
        frequency: (ReadOnly) Indicates the frequency used for demodulation and
            for output generation. The demodulation frequency is calculated with
            oscillator frequency times the harmonic factor. When the MOD option
            is used, linear combinations of oscillator frequencies including the
            harmonic factors define the demodulation frequencies.
        order: Selects the filter roll off. Allowed Values:
            1 = 1st order filter 6 dB/oct
            2 = 2nd order filter 12 dB/oct
            3 = 3rd order filter 18 dB/oct
            4 = 4th order filter 24 dB/oct
            5 = 5th order filter 30 dB/oct
            6 = 6th order filter 36 dB/oct
            7 = 7th order filter 42 dB/oct
            8 = 8th order filter 48 dB/oct
        harmonic: Multiplies the demodulator's reference frequency by an integer
            factor. If the demodulator is used as a phase detector in external
            reference mode (PLL), the effect is that the internal oscillator
            locks to the external frequency divided by the integer factor.
        oscselect: Connects the demodulator with the supplied oscillator.
            Number of available oscillators depends on the installed options.
            Is a number between 0 and the number of oscillators -1.
        phaseadjust: Adjust the demodulator phase automatically in order to read 0 degrees.
        phaseshift: Phase shift applied to the reference input of the demodulator.
            The value is clipped by the device to -180 .. +180 degrees.
        timeconstant: Sets the integration time constant or in other words, the
            cutoff frequency of the demodulator low pass filter.
        sinc: Enables the sinc filter. When the filter bandwidth is comparable
            to or larger than the demodulation frequency, the demodulator output
            may contain frequency components at the frequency of demodulation
            and its higher harmonics. The sinc is an additional filter that
            attenuates these unwanted components in the demodulator output.
            Possible values are: 'ON', 'OFF'.
        signalinput: Selects the input signal for the demodulator. Possible
            values: 'Sig In 1', 'Curr In 1', 'Trigger 1', 'Trigger 2', 'Aux Out 1',
            'Aux Out 2', 'Aux Out 3', 'Aux Out 4', 'Aux In 1', 'Aux In 2',
            'Constant input'.
        x: (ReadOnly) get sample of x coordinate. See note below.
        y: (ReadOnly) get sample of y coordinate. See note below.
        R: (ReadOnly) get sample of absolute value of x+y*i. See note below.
        phi: (ReadOnly) get sample of angle of x+y*i. See note below.
        cfgTimeout: stores the used timeout in seconds for the readings of
            sample data (default 0.07). The valid range is from 0 to 1 second.
    Parameters accessible only by the first channel or with MD option on all channels:
        samplerate: Defines the demodulator sampling rate, the number of samples
            that are sent to the host computer per second. A rate of about 7-10
            higher as compared to the filter bandwidth usually provides sufficient
            aliasing suppression. This is also the rate of data received by LabOne
            Data Server and saved to the computer hard disk. This setting has no
            impact on the sample rate on the auxiliary outputs connectors.
            Note: the value inserted by the user may be approximated to the
            nearest value supported by the instrument.
        sample: (ReadOnly) Returns a dict with streamed demodulator samples with
            sample interval defined by the demodulator data rate. See note below.
            The dict contains the following entries:
                'timestamp' = array of uint64 with the internal timestamp of the
                        measurement. Divide this by zidev.clockbase to get the
                        real time in seconds.
                'x' = array of double with the x part of the demodulated cartesian coordinates
                'y' = array of double with the y part of the demodulated cartesian coordinates
                'frequency' = array of double with the current frequency of the oscillator
                'phase' = array of double with the angle of the demodulator polar coordinates
                'dio' = array of uint32 with the values of the digital inputs
                'trigger' = array of uint32 (TODO)
                'auxin0' = array of double with the voltage of the first auxiliary input
                'auxin1' = array of double with the voltage of the second auxiliary input
                'R' = array of double with the calculated radius of the demodulated
                        polar coordinates, see note below.
                'phi' = array of double with the calculated angle of the demodulated
                        polar coordinates, see note below.
                Note: The values of x and y are inside the sample dict, the values
                of R and phi are calculated. To have all values at the same measurement
                timestamp, the driver asks the device only if the last sample request
                is more than the cfgTimeout seconds ago.
        streaming: Enables the data acquisition for the corresponding demodulator.
            Possible values are: `ON', `OFF'.
        trigger: Selects the acquisition mode (i.e. triggering) or the demodulator.
            The possible values are:
                'Continuous' = demodulator data is continuously streamed to the host computer
                'Trigger in 1 Rise' = rising edge triggered
                'Trigger in 1 Fall' = falling edge triggered
                'Trigger in 1 Both' = triggering on both rising and falling edge
                'Trigger in 2 Rise' = rising edge triggered
                'Trigger in 2 Fall' = falling edge triggered
                'Trigger in 2 Both' = triggering on both rising and falling edge
                'Trigger in 1$\mid$2 Rise' = rising edge triggered on either input
                'Trigger in 1$\mid$2 Fall' = falling edge triggered on either input
                'Trigger in 1$\mid$2 Both' = triggering on both rising and falling
                        edge or either trigger input
                'Trigger in 1 Low' = demodulator data is streamed to the host
                        computer when the level is low (TTL)
                'Trigger in 1 High' = demodulator data is streamed to the host
                        computer when the level is high (TTL)
                'Trigger in 2 Low' = demodulator data is streamed to the host
                        computer when the level is low (TTL)
                'Trigger in 2 High' = demodulator data is streamed to the host
                        computer when the level is high (TTL)
                'Trigger in 1$\mid$2 Low' = demodulator data is streamed to the
                        host computer when either level is low (TTL)
                'Trigger in 1$\mid$2 High' = demodulator data is streamed to the
                        host computer when either level is high (TTL)
    """

    def __init__(self, parent: 'ZIMFLI', name: str, channum: int) -> None:
        """
        Creates a new DemodulatorChannel
        Args:
            parent: the Instrument the Channel belongs to, here 'ZIMFLI'
            name: the internal QCoDeS name of the channel
            channum: the channel number of the current channel, used as index
                in the ChannelList of the DemodulatorChannels
        """
        super().__init__(parent, name)
        self.configTimeout = 0.07
        self.datadict = None
        self.add_parameter('bypass',
                           label='bypass low-pass filter',
                           get_cmd=partial(self._parent._getter, 'demods',
                                           channum-1, Mode.INT, 'bypass'),
                           set_cmd=partial(self._parent._setter, 'demods',
                                           channum-1, Mode.INT, 'bypass'),
                           vals=vals.Ints(),
                           docstring="Allows to bypass the demodulator low-pass"
                                     " filter, thus increasing the bandwidth.")
        self.add_parameter('frequency',
                           label='frequency for demodulation',
                           unit='Hz',
                           get_cmd=partial(self._parent._getter, 'demods',
                                           channum-1, Mode.DOUBLE, 'freq'),
                           set_cmd=False,
                           docstring="(ReadOnly) Indicates the frequency used for"
                                     " demodulation and for output generation."
                                     " The demodulation frequency is calculated with"
                                     " oscillator frequency times the harmonic factor."
                                     " When the MOD option is used, linear combinations"
                                     " of oscillator frequencies including the harmonic"
                                     " factors define the demodulation frequencies."
                           )
        self.add_parameter('order',
                           label='Filter order',
                           get_cmd=partial(self._parent._getter, 'demods',
                                           channum-1, Mode.INT, 'order'),
                           set_cmd=partial(self._parent._setter, 'demods',
                                           channum-1, Mode.INT, 'order'),
                           vals=vals.Ints(1, 8),
                           docstring="Selects the filter roll off: <val>*6 dB/oct")
        self.add_parameter('harmonic',
                           label=('Reference frequency multiplication factor'),
                           get_cmd=partial(self._parent._getter, 'demods',
                                           channum-1, Mode.DOUBLE, 'harmonic'),
                           set_cmd=partial(self._parent._setter, 'demods',
                                           channum-1, Mode.DOUBLE, 'harmonic'),
                           vals=vals.Ints(1, 999), # same range as input field in web
                           docstring="Multiplies the demodulator's reference frequency"
                                     " by an integer factor. If the demodulator is"
                                     " used as a phase detector in external reference"
                                     " mode (PLL), the effect is that the internal"
                                     " oscillator locks to the external frequency"
                                     " divided by the integer factor.")
        oscsel_doc = "Connects the demodulator with the supplied oscillator. Number" \
                     " of available oscillators depends on the installed options."
        if self._parent.no_oscs == 1:
            # The validator checks the range min <= val <= max and cannot be
            # initialized with min==max. So, if there is only one oscillator,
            # a local setter function is used with a special validation.
            self.add_parameter('oscselect',
                           label='Select oscillator',
                           get_cmd=partial(self._parent._getter, 'demods',
                                           channum-1, Mode.INT, 'oscselect'),
                           set_cmd=partial(self._setter, 'demods',
                                           channum-1, Mode.INT, 'oscselect'),
                           docstring=oscsel_doc
                           )
        else:
            self.add_parameter('oscselect',
                           label='Select oscillator',
                           get_cmd=partial(self._parent._getter, 'demods',
                                           channum-1, Mode.INT, 'oscselect'),
                           set_cmd=partial(self._parent._setter, 'demods',
                                           channum-1, Mode.INT, 'oscselect'),
                           vals=vals.Ints(0, self._parent.no_oscs-1),
                           docstring=oscsel_doc
                           )

        self.add_parameter('phaseadjust',
                           label='Phase adjustment',
                           get_cmd=partial(self._parent._getter, 'demods',
                                           channum-1, Mode.INT, 'phaseadjust'),
                           set_cmd=partial(self._parent._setter, 'demods',
                                           channum-1, Mode.INT, 'phaseadjust'),
                           vals=vals.Ints(),
                           docstring="Adjust the demodulator phase automatically"
                                     " in order to read 0 degrees."
                           )
        self.add_parameter('phaseshift',
                           label='Phase shift',
                           unit='degrees',
                           get_cmd=partial(self._parent._getter, 'demods',
                                           channum-1, Mode.DOUBLE, 'phaseshift'),
                           set_cmd=partial(self._parent._setter, 'demods',
                                           channum-1, Mode.DOUBLE, 'phaseshift'),
                           vals=vals.Numbers(),
                           docstring="Phase shift applied to the reference input"
                                     " of the demodulator. The value is clipped by"
                                     " the device to -180 .. +180 degrees."
                           )
        self.add_parameter('timeconstant',
                           label='Filter time constant',
                           get_cmd=partial(self._parent._getter, 'demods',
                                           channum-1, Mode.DOUBLE, 'timeconstant'),
                           set_cmd=partial(self._parent._setter, 'demods',
                                           channum-1, Mode.DOUBLE, 'timeconstant'),
                           unit='s',
                           vals=vals.Numbers(),
                           docstring="Sets the integration time constant or in other"
                                     " words, the cutoff frequency of the demodulator"
                                     " low pass filter."
                           )
        if channum == 1 or 'MD' in self._parent.options:
            self.add_parameter('samplerate',
                               label='Sampling rate',
                               get_cmd=partial(self._parent._getter, 'demods',
                                               channum-1, Mode.DOUBLE, 'rate'),
                               set_cmd=partial(self._parent._setter, 'demods',
                                               channum-1, Mode.DOUBLE, 'rate'),
                               unit='1/s',
                               vals=vals.Numbers(),
                               docstring="""
                               Defines the demodulator sampling rate, the number of samples
                               that are sent to the host computer per second. A rate of about 7-10
                               higher as compared to the filter bandwidth usually provides sufficient
                               aliasing suppression. This is also the rate of data received by LabOne
                               Data Server and saved to the computer hard disk. This setting has no
                               impact on the sample rate on the auxiliary outputs connectors.
                               Note: the value inserted by the user may be approximated to the
                               nearest value supported by the instrument.
                                         """
                               )
            self.add_parameter('sample',
                               label='Sample',
                               get_cmd=partial(self._parent._getter, 'demods',
                                               channum-1, Mode.SAMPLE, 'sample'),
                               set_cmd=False,
                               snapshot_value=False,
                               docstring="""
                               (ReadOnly) Returns a dict with streamed demodulator samples with
                               sample interval defined by the demodulator data rate. See note below.
                               The dict contains the following entries:
                                'timestamp' = array of uint64 with the internal timestamp of the measurement. Divide this by zidev.clockbase to get the real time in seconds.
                                'x' = array of double with the x part of the demodulated cartesian coordinates
                                'y' = array of double with the y part of the demodulated cartesian coordinates
                                'frequency' = array of double with the current frequency of the oscillator
                                'phase' = array of double with the angle of the demodulator polar coordinates
                                'dio' = array of uint32 with the values of the digital inputs
                                'trigger' = array of uint32 (TODO)
                                'auxin0' = array of double with the voltage of the first auxiliary input
                                'auxin1' = array of double with the voltage of the second auxiliary input
                                'R' = array of double with the calculated radius of the demodulated polar coordinates, see note below.
                                'phi' = array of double with the calculated angle of the demodulated polar coordinates, see note below.
                               Note: The values of x and y are inside the sample dict, the values
                               of R and phi are calculated. To have all values at the same measurement
                               timestamp, the driver asks the device only if the last sample request
                               is more than the cfgTimeout seconds ago.
                               """ )

        self.add_parameter('sinc',
                           label='Sinc filter',
                           get_cmd=partial(self._parent._getter, 'demods',
                                           channum-1, Mode.INT, 'sinc'),
                           set_cmd=partial(self._parent._setter, 'demods',
                                           channum-1, Mode.INT, 'sinc'),
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="""
                           Enables the sinc filter. When the filter bandwidth is comparable
                           to or larger than the demodulation frequency, the demodulator output
                           may contain frequency components at the frequency of demodulation
                           and its higher harmonics. The sinc is an additional filter that
                           attenuates these unwanted components in the demodulator output.
                           Possible values are: 'ON', 'OFF'.
                           """ )
        # val_mapping for the demodX_signalin parameter
        dmsigins = {'Sig In 1': 0,
                    'Curr In 1': 1,
                    'Trigger 1': 2,
                    'Trigger 2': 3,
                    'Aux Out 1': 4,
                    'Aux Out 2': 5,
                    'Aux Out 3': 6,
                    'Aux Out 4': 7,
                    'Aux In 1': 8,
                    'Aux In 2': 9,
                    'Constant input': 174}
        self.add_parameter('signalin',
                           label='Signal input',
                           get_cmd=partial(self._parent._getter, 'demods',
                                           channum-1, Mode.INT,'adcselect'),
                           set_cmd=partial(self._parent._setter, 'demods',
                                           channum-1, Mode.INT, 'adcselect'),
                           val_mapping=dmsigins,
                           docstring="Selects the input signal for the demodulator.")
        self.add_parameter('streaming',
                           label='Data streaming',
                           get_cmd=partial(self._parent._getter, 'demods',
                                           channum-1, Mode.INT, 'enable'),
                           set_cmd=partial(self._parent._setter, 'demods',
                                           channum-1, Mode.INT, 'enable'),
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="Enables the data acquisition for the corresponding"
                                     " demodulator. Possible values are: `ON', `OFF'." )
        dmtrigs = {'Continuous': 0,            #demodulator data is continuously streamed
                                               #to the host computer.
                   'Trigger in 1 Rise': 1,     #rising edge triggered.
                   'Trigger in 1 Fall': 2,     #falling edge triggered.
                   'Trigger in 1 Both': 3,     #triggering on both rising and falling edge.
                   'Trigger in 2 Rise': 4,     #rising edge triggered.
                   'Trigger in 1|2 Rise': 5,   #rising edge triggered on either input.
                   'Trigger in 2 Fall': 8,     #falling edge triggered.
                   'Trigger in 1|2 Fall': 10,  #falling edge triggered on either input.
                   'Trigger in 2 Both': 12,    #triggering on both rising and falling edge.
                   'Trigger in 1|2 Both': 15,  #triggering on both rising and falling
                                               #edge or either trigger input.
                   'Trigger in 1 Low': 16,     #demodulator data is streamed to the host
                                               #computer when the level is low (TTL).
                   'Trigger in 1 High': 32,    #demodulator data is streamed to the host
                                               #computer when the level is high (TTL).
                   'Trigger in 2 Low': 64,     #demodulator data is streamed to the host
                                               #computer when the level is low (TTL).
                   'Trigger in 1|2 Low': 80,   #demodulator data is streamed to the host
                                               #computer when either level is low (TTL).
                   'Trigger in 2 High': 128,   #demodulator data is streamed to the host
                                               #computer when the level is high (TTL).
                   'Trigger in 1|2 High': 160, #demodulator data is streamed to the host
                                               #computer when either level is high (TTL).
                  }
        self.add_parameter('trigger',
                           label='Trigger',
                           get_cmd=partial(self._parent._getter, 'demods',
                                           channum-1, Mode.INT, 'trigger'),
                           set_cmd=partial(self._parent._setter, 'demods',
                                           channum-1, Mode.INT, 'trigger'),
                           val_mapping=dmtrigs,
                           docstring="""
                           trigger: Selects the acquisition mode (i.e. triggering) or the demodulator.
                           The possible values are:
                             'Continuous' = demodulator data is continuously streamed to the host computer
                             'Trigger in 1 Rise' = rising edge triggered
                             'Trigger in 1 Fall' = falling edge triggered
                             'Trigger in 1 Both' = triggering on both rising and falling edge
                             'Trigger in 2 Rise' = rising edge triggered
                             'Trigger in 2 Fall' = falling edge triggered
                             'Trigger in 2 Both' = triggering on both rising and falling edge
                             'Trigger in 1|2 Rise' = rising edge triggered on either input
                             'Trigger in 1|2 Fall' = falling edge triggered on either input
                             'Trigger in 1|2 Both' = triggering on both rising and falling edge or either trigger input
                             'Trigger in 1 Low' = demodulator data is streamed to the host computer when the level is low (TTL)
                             'Trigger in 1 High' = demodulator data is streamed to the host computer when the level is high (TTL)
                             'Trigger in 2 Low' = demodulator data is streamed to the host computer when the level is low (TTL)
                             'Trigger in 2 High' = demodulator data is streamed to the host computer when the level is high (TTL)
                             'Trigger in 1|2 Low' = demodulator data is streamed to the host computer when either level is low (TTL)
                             'Trigger in 1|2 High' = demodulator data is streamed to the host computer when either level is high (TTL)
                             """
                             )
        if channum == 1:
            for demod_param in ['x', 'y', 'R', 'phi']:
                if demod_param in ('x', 'y', 'R'):
                    unit = 'V'
                else:
                    unit = 'deg'
                self.add_parameter('{}'.format(demod_param),
                                   label='{}'.format(demod_param),
                                   get_cmd=partial(self._get_sample,
                                                   channum - 1, demod_param),
                                   set_cmd=False,
                                   snapshot_value=False,
                                   unit=unit,
                                   docstring="For description see 'sample'" )
        self.add_parameter('cfgTimeout',
                           label='Timeout for sample request',
                           get_cmd=partial(self._getTimeout),
                           set_cmd=partial(self._setTimeout),
                           vals=vals.Numbers(0.0, 1.0),
                           docstring="stores the used timeout in seconds for the"
                                     " readings of sample data (default 0.07)."
                                     " The valid range is from 0 to 1 second." )

    @property
    def _instrument(self):
        return self._parent

    def _get_sample(self, number: int, demod_param: str) -> float:
        """
        Getter function for all sample parameters (x, y, R, phi). It calls
        the getter method of the parent.
        """
        #log.debug("getting demod %s param %s", number, demod_param)
        mode = Mode.SAMPLE
        module = 'demods'
        setting = 'sample'
        # not really needed, because we don't add an invalid parameter
        if demod_param not in ['x', 'y', 'R', 'phi']:
            raise RuntimeError("Invalid demodulator parameter")
        if (self.datadict is None) or (time.time() - self._parent.lastSampleSecs >= self.configTimeout):
            self.datadict = self._parent._getter(module, number, mode, setting)
        # The following calculations are done in the parent getter.
        #self.datadict['R'] = np.abs(self.datadict['x'] + 1j * self.datadict['y'])
        #self.datadict['phi'] = np.angle(self.datadict['x'] + 1j * self.datadict['y'], deg=True)
        return self.datadict[demod_param]

    def _getTimeout(self) -> float:
        return self.configTimeout

    def _setTimeout(self, val):
        self.configTimeout = val

    def _setter(self, module, number, mode, setting, value):
        """
        Copy of _parent._setter() function. This is needed for the setting of
        the selected oscillator channel if only one exists. The used validator
        cannot be called with min == max (in this case both 0).
        """

        if value != 0:
            context = "class DemodulatorChannel, function set oscillator channel"
            # This code is copied from the validator function
            if not isinstance(value, (int, np.integer) ):
                raise TypeError(
                        '{} is not an int; {}'.format(repr(value), context))
            raise ValueError(
                        '{} is invalid: must be zero; {}'
                        .format(repr(value), context))

        setstr = '/{}/{}/{}/{}'.format(self._parent.device, module, number, setting)

        if mode == 0:
            self._parent.daq.setInt(setstr, value)
        if mode == 1:
            self._parent.daq.setDouble(setstr, value)


class SignalInputChannel(InstrumentChannel): # doc done ***********************
    """
    The Lock-In-Amplifier has one voltage sensitive input channel.
    Parameters:
        autorange: Automatic adjustment of the Range to about two times the
            maximum signal input amplitude measured over about 100 ms.
        range: Defines the gain of the analog input amplifier. The range should
            exceed the incoming signal by roughly a factor two including a
            potential DC offset. The instrument selects the next higher available
            range relative to a value inserted by the user. A suitable choice of
            this setting optimizes the accuracy and signal-to-noise ratio by
            ensuring that the full dynamic range of the input ADC is used.
        float: Switches the input between floating ('ON') and connected to
            ground ('OFF'). This setting applies both to the voltage and the
            current input. It is recommended to discharge the test device
            before connecting or to enable this setting only after the signal
            source has been connected to the Signal Input in grounded mode.
        scaling: Applies the given scaling factor to the input signal.
        ac: Defines the input coupling for the Signal Inputs. AC coupling
            ('ON') inserts a high-pass filter. 'OFF' means DC ccoupling.
        impedance: Switches the input impedance between 50 Ohm ('ON') and
            10 M Ohm ('OFF').
        diff: Switches between single ended ('OFF', use only +V input) and
            differential ('ON', use both +V and -V inputs) measurements.
        max: Indicates the maximum measured value at the input.
        min: Indicates the minimum measured value at the input.
        on: Enables the signal input.
        trigger: Switches to the next appropriate input range such that the
            range fits best with the measured input signal amplitude.
    """

    def __init__(self, parent: 'ZIMFLI', name: str, channum) -> None:
        """
        Creates a new SignalInputChannel
        Args:
            parent: the Instrument the Channel belongs to, in this case 'ZIMFLI'
            name: the internal QCoDeS name of the channel
            channum: the channel number of the current channel, used as index
                in the ChannelList of the SignalInputChannels
        """
        super().__init__(parent, name)
        self.add_parameter('autorange',
                           label='Automatic Range adjustment',
                           get_cmd=partial(self._parent._getter, 'sigins',
                                           channum-1, Mode.INT, 'autorange'),
                           set_cmd=partial(self._parent._setter, 'sigins',
                                           channum-1, Mode.INT, 'autorange'),
                           vals=vals.Ints(),
                           docstring="Automatic adjustment of the Range to about"
                                     " two times the maximum signal input amplitude"
                                     " measured over about 100 ms." )
        self.add_parameter('range',
                           label='Input range',
                           set_cmd=partial(self._parent._setter, 'sigins',
                                           channum-1, Mode.DOUBLE, 'range'),
                           get_cmd=partial(self._parent._getter, 'sigins',
                                           channum-1, Mode.DOUBLE, 'range'),
                           unit='V',
                           vals=vals.Numbers(),
                           docstring="Defines the gain of the analog input amplifier."
                                     " The range should exceed the incoming signal by"
                                     " roughly a factor two including a potential DC"
                                     " offset. The instrument selects the next higher"
                                     " available range relative to a value inserted by"
                                     " the user. A suitable choice of this setting"
                                     " optimizes the accuracy and signal-to-noise ratio"
                                     " by ensuring that the full dynamic range of the"
                                     " input ADC is used." )
        self.add_parameter('float',
                           label='floating',
                           get_cmd=partial(self._parent._getter, 'sigins',
                                           channum-1, Mode.INT, 'float'),
                           set_cmd=partial(self._parent._setter, 'sigins',
                                           channum-1, Mode.INT, 'float'),
                           val_mapping={'OFF': 0, 'ON': 1},
                           vals=vals.Enum('OFF', 'ON'),
                           docstring="Switches the input between floating ('ON')"
                                     " and connected to ground ('OFF'). This setting"
                                     " applies both to the voltage and the current"
                                     " input. It is recommended to discharge the test"
                                     " device before connecting or to enable this"
                                     " setting only after the signal source has been"
                                     " connected to the Signal Input in grounded mode.")
        self.add_parameter('scaling',
                           label='Input scaling',
                           set_cmd=partial(self._parent._setter, 'sigins',
                                           channum-1, Mode.DOUBLE, 'scaling'),
                           get_cmd=partial(self._parent._getter, 'sigins',
                                           channum-1, Mode.DOUBLE, 'scaling'),
                           vals=vals.Numbers(),
                           docstring="Applies the given scaling factor to the input signal.")
        self.add_parameter('ac',
                           label='AC coupling',
                           set_cmd=partial(self._parent._setter,'sigins',
                                           channum-1, Mode.INT, 'ac'),
                           get_cmd=partial(self._parent._getter, 'sigins',
                                           channum-1, Mode.INT, 'ac'),
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="Defines the input coupling for the Signal Inputs."
                                     " AC coupling ('ON') inserts a high-pass filter."
                                     " 'OFF' means DC ccoupling.")
        self.add_parameter('impedance',
                           label='Input impedance',
                           set_cmd=partial(self._parent._setter, 'sigins',
                                           channum-1, Mode.INT, 'imp50'),
                           get_cmd=partial(self._parent._getter, 'sigins',
                                           channum-1, Mode.INT, 'imp50'),
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="Switches the input impedance between 50 Ohm"
                                     " ('ON') and 10 M Ohm ('OFF').")
        self.add_parameter('diff',
                           label='Differential measurements',
                           set_cmd=partial(self._parent._setter, 'sigins',
                                           channum-1, Mode.INT, 'diff'),
                           get_cmd=partial(self._parent._getter, 'sigins',
                                           channum-1, Mode.INT, 'diff'),
                           val_mapping={'OFF': 0, 'ON': 1},
                           vals=vals.Enum('OFF', 'ON'),
                           docstring="Switches between single ended ('OFF', use only"
                                     " +V input) and differential ('ON', use both +V"
                                     " and -V inputs) measurements.")
        self.add_parameter('max',
                           label='maximum measured value',
                           get_cmd=partial(self._parent._getter, 'sigins',
                                           channum-1, Mode.DOUBLE, 'max'),
                           set_cmd=partial(self._parent._setter, 'sigins',
                                           channum-1, Mode.DOUBLE, 'max'),
                           unit='V',
                           vals=vals.Numbers(),
                           docstring="Indicates the maximum measured value at the input.")
        self.add_parameter('min',
                           label='minimum measured value',
                           get_cmd=partial(self._parent._getter, 'sigins',
                                           channum-1, Mode.DOUBLE, 'min'),
                           set_cmd=partial(self._parent._setter, 'sigins',
                                           channum-1, Mode.DOUBLE, 'min'),
                           unit='V',
                           vals=vals.Numbers(),
                           docstring="Indicates the minimum measured value at the input.")
        self.add_parameter('on',
                           label='Enable signal input',
                           get_cmd=partial(self._parent._getter, 'sigins',
                                           channum-1, Mode.INT, 'on'),
                           set_cmd=partial(self._parent._setter, 'sigins',
                                           channum-1, Mode.INT, 'on'),
                           vals=vals.Ints(),
                           docstring="Enables the signal input.")
        self.add_parameter('trigger',
                           label='Trigger',
                           get_cmd=partial(self._parent._getter, 'sigins',
                                           channum-1, Mode.INT, 'rangestep/trigger'),
                           set_cmd=partial(self._parent._setter, 'sigins',
                                           channum-1, Mode.INT, 'rangestep/trigger'),
                           vals=vals.Ints(),
                           docstring="Switches to the next appropriate input range"
                                     " such that the range fits best with the"
                                     " measured input signal amplitude.")



class CurrentInputChannel(InstrumentChannel): # doc done **********************
    """
    The device has one current sensitive input channel.
    Parameters:
        autorange: Automatic adjustment of the Range to about two times the maximum
            signal input amplitude measured over about 100 ms.
        range: Defines the gain of the analog input amplifier. The range should
            exceed the incoming signal by roughly a factor two including a potential
            DC offset. The instrument selects the next higher available range relative
            to a value inserted by the user. A suitable choice of this setting optimizes
            the accuracy and signal-to-noise ratio by ensuring that the full dynamic
            range of the input ADC is used.
        float: Switches the input between floating ('ON') and connected to ground
            ('OFF'). This setting applies both to the voltage and the current
            input. It is recommended to discharge the test device before connecting
            or to enable this setting only after the signal source has been connected
            to the Signal Input in grounded mode.
        scaling: Applies the given scaling factor to the input signal.
        max: Indicates the maximum measured value at the input.
        min: Indicates the minimum measured value at the input.
        on: Enables the signal input.
        trigger: Switches to the next appropriate input range such that the range
            fits best with the measured input signal amplitude.
    """

    def __init__(self, parent: 'ZIMFLI', name: str, channum) -> None:
        """
        Creates a new SignalInputChannel
        Args:
            parent: the Instrument the Channel belongs to, in this case 'ZIMFLI'
            name: the internal QCoDeS name of the channel
            channum: the channel number of the current channel, used as index
                in the ChannelList of the CurrentInputChannels
        """
        super().__init__(parent, name)
        self.add_parameter('autorange',
                           label='Automatic Range adjustment',
                           get_cmd=partial(self._parent._getter, 'currins',
                                           channum-1, Mode.INT, 'autorange'),
                           set_cmd=partial(self._parent._setter, 'currins',
                                           channum-1, Mode.INT, 'autorange'),
                           vals=vals.Ints(),
                           docstring="Automatic adjustment of the Range to about"
                                     " two times the maximum signal input amplitude"
                                     " measured over about 100 ms.")
        self.add_parameter('range',
                           label='Input range',
                           set_cmd=partial(self._parent._setter, 'currins',
                                           channum-1, Mode.DOUBLE, 'range'),
                           get_cmd=partial(self._parent._getter, 'currins',
                                           channum-1, Mode.DOUBLE, 'range'),
                           unit='V',
                           vals=vals.Numbers(),
                           docstring="Defines the gain of the analog input amplifier."
                                     " The range should exceed the incoming signal by"
                                     " roughly a factor two including a potential DC"
                                     " offset. The instrument selects the next higher"
                                     " available range relative to a value inserted by"
                                     " the user. A suitable choice of this setting"
                                     " optimizes the accuracy and signal-to-noise"
                                     " ratio by ensuring that the full dynamic range"
                                     " of the input ADC is used.")
        self.add_parameter('float',
                           label='floating',
                           get_cmd=partial(self._parent._getter, 'currins',
                                           channum-1, Mode.INT, 'float'),
                           set_cmd=partial(self._parent._setter, 'currins',
                                           channum-1, Mode.INT, 'float'),
                           val_mapping={'OFF': 0, 'ON': 1},
                           vals=vals.Enum('OFF', 'ON'),
                           docstring="Switches the input between floating ('ON') and"
                                     " connected to ground ('OFF'). This setting applies"
                                     " both to the voltage and the current input. It is"
                                     " recommended to discharge the test device before"
                                     " connecting or to enable this setting only after"
                                     " the signal source has been connected to the Signal"
                                     " Input in grounded mode.")
        self.add_parameter('scaling',
                           label='Input scaling',
                           set_cmd=partial(self._parent._setter, 'currins',
                                           channum-1, Mode.DOUBLE, 'scaling'),
                           get_cmd=partial(self._parent._getter, 'currins',
                                           channum-1, Mode.DOUBLE, 'scaling'),
                           vals=vals.Numbers(),
                           docstring="Applies the given scaling factor to the input signal.")
        self.add_parameter('max',
                           label='maximum measured value',
                           get_cmd=partial(self._parent._getter, 'currins',
                                           channum-1, Mode.DOUBLE, 'max'),
                           set_cmd=partial(self._parent._setter, 'currins',
                                           channum-1, Mode.DOUBLE, 'max'),
                           unit='V',
                           vals=vals.Numbers(),
                           docstring="Indicates the maximum measured value at the input.")
        self.add_parameter('min',
                           label='minimum measured value',
                           get_cmd=partial(self._parent._getter, 'currins',
                                           channum-1, Mode.DOUBLE, 'min'),
                           set_cmd=partial(self._parent._setter, 'currins',
                                           channum-1, Mode.DOUBLE, 'min'),
                           unit='V',
                           vals=vals.Numbers(),
                           docstring="Indicates the minimum measured value at the input.")
        self.add_parameter('on',
                           label='Enable signal input',
                           get_cmd=partial(self._parent._getter, 'currins',
                                           channum-1, Mode.INT, 'on'),
                           set_cmd=partial(self._parent._setter, 'currins',
                                           channum-1, Mode.INT, 'on'),
                           vals=vals.Ints(),
                           docstring="Enables the signal input.")
        self.add_parameter('trigger',
                           label='Trigger',
                           get_cmd=partial(self._parent._getter, 'currins',
                                           channum-1, Mode.INT, 'rangestep/trigger'),
                           set_cmd=partial(self._parent._setter, 'currins',
                                           channum-1, Mode.INT, 'rangestep/trigger'),
                           vals=vals.Ints(),
                           docstring="Switches to the next appropriate input range"
                                     " such that the range fits best with the measured"
                                     " input signal amplitude.")


class SignalOutputChannel(InstrumentChannel): # doc done **********************
    """
    The device has one signal output channel.
    Parameters:
        add: The signal supplied to the Aux Input 1 is added to the signal output.
            For differential output the added signal is a common mode offset.
            The allowed values are 'ON' and 'OFF'.
        autorange: If enabled, selects the most suited output range automatically.
            Allowed values are `ON' and `OFF'.
        differential: Switch between single-ended output ('OFF') and differential
            output ('ON'). In differential mode the signal swing is defined between
            Signal Output +V and -V.
        imp50: Select the load impedance between 50 Ohm ('ON') and HiZ ('OFF').
            The impedance of the output is always 50 Ohm. For a load impedance
            of 50 Ohm the displayed voltage is half the output voltage to reflect
            the voltage seen at the load.
        offset: Defines the DC voltage that is added to the dynamic part of the
            output signal. Currently this value is only valid for the driver in
            the range from -1.5V to +1.5V.
        on: Enabling/Disabling the Signal Output. Corresponds to the blue LED
            indicator on the instrument front panel. The allowed values are
            'ON' and 'OFF'.
        overloaded: (ReadOnly) Indicates that the signal output is overloaded.
        range: Sets the output voltage range. Currently this value is only valid
            for the driver in the range from 0.001 to 3.0. The device will select
            the next higher available range automatically.
        amplitude: Sets the peak amplitude that the oscillator assigned to the
            given demodulation channel contributes to the signal output. Should
            be given as Vpk value.
        ampdef: Internal storage for the used unit for the amplitude. Possible
            values are `Vpk', `Vrms' or `dBm', default is `Vpk'.
        enable: Enables individual output signal amplitude. The allowed values
            are 'ON' and 'OFF'. When the MD option is installed, it is possible
            to generate signals being the linear combination of the available
            demodulator frequencies.
    """
    def __init__(self, parent: 'ZIMFLI', name: str, channum: int) -> None:
        super().__init__(parent, name)

        # store the channelnumber internally but zero-based
        self.channum = channum-1

        self.add_parameter('add',
                           label='add signal from aux1 input',
                           set_cmd=partial(self._setter, Mode.INT, 'add'),
                           get_cmd=partial(self._getter, Mode.INT, 'add'),
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="The signal supplied to the Aux Input 1 is added"
                                     " to the signal output. For differential output"
                                     " the added signal is a common mode offset. The"
                                     " allowed values are 'ON' and 'OFF'.")
        self.add_parameter('autorange',
                           label='Enable signal output range.',
                           set_cmd=partial(self._setter, Mode.INT, 'autorange'),
                           get_cmd=partial(self._getter, Mode.INT, 'autorange'),
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="If enabled, selects the most suited output"
                                     " range automatically. Allowed values are"
                                     " `ON' and `OFF'.")
        self.add_parameter('differential',
                           label='single-ended(OFF) or differential(ON) output',
                           set_cmd=partial(self._setter, Mode.INT, 'diff'),
                           get_cmd=partial(self._getter, Mode.INT, 'diff'),
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="Switch between single-ended output ('OFF')"
                                     " and differential output ('ON'). In differential"
                                     " mode the signal swing is defined between"
                                     " Signal Output +V and -V.")
        self.add_parameter('imp50',
                           label='Switch to turn on 50 Ohm impedance',
                           set_cmd=partial(self._setter, Mode.INT, 'imp50'),
                           get_cmd=partial(self._getter, Mode.INT, 'imp50'),
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="Select the load impedance between 50 Ohm ('ON')"
                                     " and HiZ ('OFF'). The impedance of the output"
                                     " is always 50 Ohm. For a load impedance of 50"
                                     " Ohm the displayed voltage is half the output"
                                     " voltage to reflect the voltage seen at the load.")
        self.add_parameter('offset',
                           label='Signal output offset',
                           set_cmd=partial(self._setter, Mode.DOUBLE, 'offset'),
                           get_cmd=partial(self._getter, Mode.DOUBLE, 'offset'),
                           vals=vals.Numbers(-1.5, 1.5), #TODO why is this only between -1.5 and 1.5?
                           unit='V',
                           docstring="Defines the DC voltage that is added to the"
                                     " dynamic part of the output signal. Currently"
                                     " this value is only valid for the driver in"
                                     " the range from -1.5V to +1.5V.")
        self.add_parameter('on',
                           label='Turn signal output on and off.',
                           set_cmd=partial(self._setter, Mode.INT, 'on'),
                           get_cmd=partial(self._getter, Mode.INT, 'on'),
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="Enabling/Disabling the Signal Output. Corresponds"
                                     " to the blue LED indicator on the instrument front"
                                     " panel. The allowed values are 'ON' and 'OFF'.")
        self.add_parameter('overloaded',
                           label='Overloaded',
                           set_cmd=False,
                           get_cmd=partial(self._getter, Mode.INT, 'over'),
                           docstring="(ReadOnly) Indicates that the signal output is overloaded.")
        self.add_parameter('range',
                           label='Signal output range',
                           set_cmd=partial(self._setter, Mode.DOUBLE, 'range'),
                           get_cmd=partial(self._getter, Mode.DOUBLE, 'range'),
                           vals=vals.Numbers( 0.001, 3.0 ),
                           docstring="Sets the output voltage range. Currently this"
                                     " value is only valid for the driver in the range"
                                     " from 0.001 to 3.0. The device will select the"
                                     " next higher available range automatically.")
        self.add_parameter('amplitude',
                           label='Signal output amplitude',
                           set_cmd=partial(self._setter, Mode.DOUBLE,
                                           'amplitudes/{}'.format(channum)),
                           get_cmd=partial(self._getter, Mode.DOUBLE,
                                           'amplitudes/{}'.format(channum)),
                           unit='V',
                           vals=vals.Numbers(),
                           docstring="Sets the peak amplitude that the oscillator"
                                     " assigned to the given demodulation channel"
                                     " contributes to the signal output. Should be"
                                     " given as Vpk value.")
        self.add_parameter('ampdef',
                           label="Signal output amplitude's definition",
                           get_cmd=None,
                           set_cmd=None,    #is only set indirectly
                           initial_value='Vpk',
                           vals=vals.Enum('Vpk','Vrms', 'dBm'),
                           docstring="Internal storage for the used unit for the"
                                     " amplitude. Possible values are `Vpk', `Vrms'"
                                     " or `dBm', default is `Vpk'.")
        self.add_parameter('enable',
                           label="Enable signal output's amplitude.",
                           set_cmd=partial(self._setter, Mode.INT,
                                           'enables/{}'.format(channum)),
                           get_cmd=partial(self._getter, Mode.INT,
                                           'enables/{}'.format(channum)),
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="Enables individual output signal amplitude."
                                     " The allowed values are 'ON' and 'OFF'. When"
                                     " the MD option is installed, it is possible"
                                     " to generate signals being the linear combination"
                                     " of the available demodulator frequencies.")

    def _getter(self, mode, setting):
        """
        Function to query the settings of signal outputs. Specific setter
        function is needed as parameters depend on each other and need to be
        checked and updated accordingly.

        Args:
            mode (bool): Indicating whether we are asking for an int or double
            setting (str): The module's setting to set.
        """

        querystr = '/{}/sigouts/{}/{}'.format(self.parent.device, self.channum, setting)
        if mode == 0:
            value = self.parent.daq.getInt(querystr)
        if mode == 1:
            value = self.parent.daq.getDouble(querystr)

        return value

    def _setter(self, mode: int, setting: str, value: Union[int, float]) -> None:
        """
        Function to set signal output's settings. A specific setter function is
        needed as parameters depend on each other and need to be checked and
        updated accordingly.
        Args:
            mode: Indicating whether we want to set an int (0 = Mode.INT) or double (1 = Mode.DOUBLE)
            setting (str): The module's setting to set.
            value (Union[int, float]): The value to set the setting to.
        """

        # convenient reference
        params = self.parameters

        #validation of the amplitude
        def amp_valid():
            nonlocal value
            ampdef_val = params['ampdef'].get()
            autorange_val = params['autorange'].get()

            if autorange_val == 'ON':
                imp50_val = params['imp50'].get()
                imp50_dic = {'OFF': 1.5, 'ON': 0.75}
                range_val = imp50_dic[imp50_val]

            else:
                so_range = params['range'].get()
                range_val = round(so_range, 3)

            amp_val_dict={'Vpk': lambda value: value,               #value for amplitude has to be given in Vpk
                          'Vrms': lambda value: value*sqrt(2),
                          'dBm': lambda value: 10**((value-10)/20)
                         }

            if -range_val < amp_val_dict[ampdef_val](value) > range_val:
                raise ValueError('Signal Output:'
                                 + ' Amplitude too high for chosen range.')
            value = amp_val_dict[ampdef_val](value) #value of the amplitude

        #validation of the offset
        def offset_valid():
            nonlocal value
            #nonlocal number
            range_val = params['range'].get()
            range_val = round(range_val, 3)
            amp_val = params['amplitude'].get()
            amp_val = round(amp_val, 3)
            if -range_val < value+amp_val > range_val:
                raise ValueError('Signal Output: Offset too high for '
                                 'chosen range.')

        #validation of the range
        def range_valid():
            nonlocal value
            #nonlocal number
            toget = params['autorange']
            autorange_val = toget.get()
            #imp50_val = params['imp50'].get()
            #imp50_dic = {'OFF': [1.5, 0.15], 'ON': [0.75, 0.075]}

            if autorange_val == "ON":
                raise ValueError('Signal Output :'
                                ' Cannot set range as autorange is turned on.')

            # The usermanual shows no limitations for this parameter. The instrument
            #  can select 10mV, 100mV, 1V, 10V and will use the next higher than
            #  set with this parameter.
            #if value not in imp50_dic[imp50_val]:
            #    raise ValueError('Signal Output: Choose a valid range:'
            #                     '[0.75, 0.075] if imp50 is on, [1.5, 0.15]'
            #                     ' otherwise.')

        #validation of the amplitude definition
        def ampdef_valid():
            # check which amplitude definition you can use.
            # dBm is only possible with 50 Ohm imp ON
            imp50_val = params['imp50'].get()
            imp50_ampdef_dict = {'ON': ['Vpk','Vrms', 'dBm'],
                                 'OFF': ['Vpk','Vrms']}
            if value not in imp50_ampdef_dict[imp50_val]:
                raise ValueError("Signal Output: Choose a valid amplitude "
                                 "definition; ['Vpk','Vrms', 'dBm'] if imp50 is"
                                 " on, ['Vpk','Vrms'] otherwise.")
            else:
                params['ampdef'] # TODO: is this correct?

        dynamic_validation = {'range': range_valid,
                              'ampdef': ampdef_valid,
                              'amplitudes/1': amp_valid,
                              'amplitudes/2': amp_valid,
                              'offset': offset_valid}

        #updates range, offset and amplitude value and checks if the range value
        #fits the offset and amplitude value, also raises an error if that is not
        #the case
        def update_range_offset_amp():
            range_val = params['range'].get()
            offset_val = params['offset'].get()
            amp_val = params['amplitude'].get()
            if -range_val < offset_val + amp_val > range_val:
                #The GUI would allow higher values but it would clip the signal.
                raise ValueError('Signal Output: Amplitude and/or '
                                 'offset out of range.')
        #what are these methods for, why do you get a value to do nothing with it?
        def update_offset():
            self.parameters['offset'].get()

        def update_amp():
            self.parameters['amplitude'].get()

        def update_ampdef():
            self.parameters['ampdef'].set(value) #TODO test if this works correctly

        def update_range():
            self.parameters['autorange'].get()

        # parameters which will potentially change other parameters
        changing_param = {'imp50': [update_range_offset_amp, update_range],
                          'autorange': [update_range],
                          'range': [update_offset, update_amp],
                          'amplitudes/1': [update_range, update_amp],
                          'amplitudes/2': [update_range, update_amp],
                          'offset': [update_range]
                         }

        setstr = '/{}/sigouts/{}/{}'.format(self.parent.device, self.channum, setting)

        #validates the setting. If it is not valid an error is raised
        if setting in dynamic_validation:
            dynamic_validation[setting]()

        #sending the new settings to the device
        if mode == 0:
            self.parent.daq.setInt(setstr, value)
        if mode == 1:
            self.parent.daq.setDouble(setstr, value)

        #updates the parameter, which also may be effected by the setting, so
        #that they have the correct current value
        #is that necessary? Shouln't the value be updated by the instrument itself?
        if setting in changing_param:
            for f in changing_param[setting]:
                f()


class TriggerInputChannel(InstrumentChannel): # doc done **********************
    """
    The Lock-In-Amplifier has two TTL compatible trigger input lines. The
    connectors are on the back side of the device.
    Parameters:
        autothreshold: Automatically adjust the trigger threshold. The level is
            adjusted to fall in the center of the applied transitions. Allowed
            values are 'ON' and 'OFF'.
        level: Trigger voltage level at which the trigger input toggles between
            low and high. Use 50% amplitude for digital input and consider the
            trigger hysteresis.
    """
    def __init__(self, parent: 'ZIMFLI', name: str, channum: int):
        """
        Creates a new TriggerInputChannel
        Args:
            parent (ZIMFLI): parent instrument of the TriggerInputChannel
            name (str): QCoDeS internal name for the channel
            channum (int): number of the channel (1-based indexing)
        """
        super().__init__(parent, name)
        self.add_parameter('autothreshold',
                           label='autothreshold',
                           set_cmd=partial(self._parent._setter, 'triggers/in',
                                           channum-1, Mode.INT, 'autothreshold'),
                           get_cmd=partial(self._parent._getter, 'triggers/in',
                                           channum-1, Mode.INT, 'autothreshold'),
                           val_mapping={'ON': 1, 'OFF':0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="Automatically adjust the trigger threshold."
                                     " The level is adjusted to fall in the center"
                                     " of the applied transitions. Allowed values"
                                     " are 'ON' and 'OFF'.")
        self.add_parameter('level',
                           label='trigger voltage level',
                           set_cmd=partial(self._parent._setter, 'triggers/in',
                                           channum-1, Mode.DOUBLE, 'level'),
                           get_cmd=partial(self._parent._getter, 'triggers/in',
                                           channum-1, Mode.DOUBLE, 'level'),
                           unit='V',
                           vals=vals.Numbers(),
                           docstring="Trigger voltage level at which the trigger"
                                     " input toggles between low and high. Use 50%"
                                     " amplitude for digital input and consider the"
                                     " trigger hysteresis.")


class TriggerOutputChannel(InstrumentChannel): # doc done *********************
    """
    The Lock-In-Amplifier has two TTL compatible trigger output lines. The
    connectors are on the back side of the device.
    Parameters:
        pulsewidth: Defines the minimal pulse width for the case of Scope events
            written to the trigger outputs of the device. Currently this value
            is only valid for the driver in the range from 0 to 0.149 seconds.
        source: Select the signal assigned to the trigger output. Possible
            values are:
                'disabled'
                'osc phase of demod 2' (Channel 1, only without[!] MD option)
                'osc phase of demod 4' (Channel 2, only with[!] MD option)
                'Threshold Logic Unit 1'
                'Threshold Logic Unit 2'
                'Threshold Logic Unit 3'
                'Threshold Logic Unit 4'
                'MDS Sync Out'
                If the DIG option is installed, some Scope functions can be
                used as a Trigger too.

    """
    def __init__(self, parent: 'ZIMFLI', name: str, channum: int):
        """
        Creates a new TriggerOutputChannel
        Args:
            parent (ZIMFLI): parent instrument of the TriggerOutputChannel
            name (str): QCoDeS internal name for the channel
            channum (int): number of the channel (1-based indexing)
        """
        super().__init__(parent, name)
        self.add_parameter('pulsewidth',
                           label='minimal pulse width',
                           set_cmd=partial(self._parent._setter, 'triggers/out',
                                           channum-1, Mode.DOUBLE, 'pulsewidth'),
                           get_cmd=partial(self._parent._getter, 'triggers/out',
                                           channum-1, Mode.DOUBLE, 'pulsewidth'),
                           unit='s',
                           vals=vals.Numbers(0, 0.149),
                           docstring="Defines the minimal pulse width for the case"
                                     " of Scope events written to the trigger outputs"
                                     " of the device. Currently this value is only"
                                     " valid for the driver in the range from 0 to"
                                     " 0.149 seconds.")

        sources = {'disabled': 0,
                   'osc phase of demod 2' if channum == 1 else 'osc phase of demod 4': 1,
                   'Threshold Logic Unit 1': 36,
                   'Threshold Logic Unit 2': 37,
                   'Threshold Logic Unit 3': 38,
                   'Threshold Logic Unit 4': 39,
                   'MDS Sync Out': 52}
        if 'DIG' in parent.options:
            sources.update( {'Scope Trigger': 2,
                             'Scope /Trigger': 3,
                             'Scope Armed': 4,
                             'Scope /Armed': 5,
                             'Scope Active': 6,
                             'Scope /Active': 7} )
        self.add_parameter('source',
                           label='signal source',
                           set_cmd=partial(self._parent._setter, 'triggers/out',
                                           channum-1, Mode.INT, 'source'),
                           get_cmd=partial(self._parent._getter, 'triggers/out',
                                           channum-1, Mode.INT, 'source'),
                           val_mapping=sources,
                           vals=vals.Enum(*list(sources.keys())),
                           docstring="Select the signal assigned to the trigger output.")



class ExternalReferenceChannel(InstrumentChannel): # doc done *****************
    """
    The device has the capability to synchronize its internal oscillator used
    for demodulation with an external reference clock signal.
    Parameters:
        signalin: (ReadOnly) Indicates the input signal selection for the selected
            demodulator. Possible Values are 'Sig In 1', 'Curr In 1', `Trigger 1',
            'Trigger 2', 'Aux Out 1', 'Aux Out 2', 'Aux Out 3', 'Aux Out 4',
            'Aux In 1', 'Aux In 2', `Constant'. This value can be set with the
            'signalinput' parameter in the 'demod1/2' module.
        automode: (Only with MD option installed) This defines the type of automatic
            adaptation of parameters in the PID used for external reference.
            Allowed values are 'None', 'PID Auto', 'PID Low', 'PID High', 'PID All'.
        bandwidth: (Only without MD option installed) This defines the bandwidth
            used for external reference. Allowed values are `None', `Low', `High'.
        channel: (ReadOnly) Indicates the demodulator connected to the extref channel.
        enable: Enables the external reference. Allowed Values are 'ON' and 'OFF'.
        locked: (ReadOnly) Indicates whether the external reference is locked.
        oscselect: (ReadOnly) Indicates which oscillator is being locked to the
            external reference.
    In the following example the external reference is switched on, set to low
    bandwidth and the input is set to the auxiliary input 1:
        er = zidev.submodules['extref1']    # select submodule
        er.enable('ON')                     # switch external reference on
        er.bandwidth('Low')                 # select low bandwidth
        dm2 = zidev.submodules['demod2']    # get another submodule
        dm2.signalin('Aux In 1')            # select input for external reference
    """
    def __init__(self, parent: 'ZIMFLI', name: str, channum) -> None:
        """
        Creates a new ExternalReferenceChannel
        Args:
            parent: the Instrument the Channel belongs to, in this case 'ZIMFLI'
            name: the internal QCoDeS name of the channel
            channum: the channel number of the current channel, used as index
                in the ChannelList of the CurrentInputChannels
        """
        super().__init__(parent, name)
        # val_mapping for the extrefX_signalin parameter
        ersigins = {'Sig In 1': 0,
                    'Curr In 1': 1,
                    'Trigger 1': 2, #not documented in manual, but available in GUI
                    'Trigger 2': 3,
                    'Aux Out 1': 4,
                    'Aux Out 2': 5,
                    'Aux Out 3': 6,
                    'Aux Out 4': 7,
                    'Aux In 1': 8,
                    'Aux In 2': 9,
                    'Constant': 174}
        self.add_parameter('signalin',
                           label='Signal input',
                           get_cmd=partial(self._parent._getter, 'extrefs',
                                           channum-1, Mode.INT,'adcselect'),
                           set_cmd=False,
                           val_mapping=ersigins,
                           docstring="(ReadOnly) Indicates the input signal selection"
                                     " for the selected demodulator. This value can be"
                                     " set with the 'signalinput' parameter in the"
                                     " 'demod1/2' module.")
        if 'MD' in self._parent.options:
            # With this option the automode parameter select some PID settings
            ermode = {'None': 0,
                      'PID Auto': 1,
                      'PID Low': 2,
                      'PID High': 3,
                      'PID All': 4}
            self.add_parameter('automode',
                               label='Automatic adaption for PID',
                               get_cmd=partial(self._parent._getter, 'extrefs',
                                               channum-1, Mode.INT,'automode'),
                               set_cmd=partial(self._parent._setter, 'extrefs',
                                               channum-1, Mode.INT, 'automode'),
                               val_mapping=ermode,
                               docstring="This defines the type of automatic adaptation"
                                         " of parameters in the PID used for external"
                                         " reference.")
        else:
            # Without MD option the automode parameter can be used to select
            # the bandwidth of the external reference. This is not documented
            # in the manual but checked with the Web-GUI
            ermode = {'Low': 2,
                      'High': 3,
                      'None': 4}
            self.add_parameter('bandwidth',
                               label='Select bandwidth',
                               get_cmd=partial(self._parent._getter, 'extrefs',
                                               channum-1, Mode.INT,'automode'),
                               set_cmd=partial(self._parent._setter, 'extrefs',
                                               channum-1, Mode.INT, 'automode'),
                               val_mapping=ermode,
                               docstring="This defines the bandwidth used for"
                                         " external reference.")
        self.add_parameter('channel',
                           label='Demodulator channel',
                           get_cmd=partial(self._parent._getter, 'extrefs',
                                           channum - 1, Mode.INT, 'demodselect'),
                           set_cmd=False,
                           docstring="(ReadOnly) Indicates the demodulator connected"
                                     " to the extref channel.")
        self.add_parameter('enable',
                           label='Enables the external reference',
                           get_cmd=partial(self._parent._getter, 'extrefs',
                                           channum-1, Mode.INT, 'enable'),
                           set_cmd=partial(self._parent._setter, 'extrefs',
                                           channum-1, Mode.INT, 'enable'),
                           val_mapping={'OFF': 0, 'ON': 1},
                           vals=vals.Enum('OFF', 'ON'),
                           docstring="Enables the external reference. Allowed"
                                     " Values are 'ON' and 'OFF'.")
        self.add_parameter('locked',
                           label='Is the reference locked',
                           get_cmd=partial(self._parent._getter, 'extrefs',
                                           channum-1, Mode.INT, 'locked'),
                           set_cmd=False,
                           vals=vals.Ints(),
                           docstring="(ReadOnly) Indicates whether the external reference is locked.")
        self.add_parameter('oscselect',
                           label='Select oscillator',
                           get_cmd=partial(self._parent._getter, 'extrefs',
                                           channum-1, Mode.INT, 'oscselect'),
                           set_cmd=False,
                           docstring="(ReadOnly) Indicates which oscillator is being"
                                     " locked to the external reference.")


class DIOChannel(InstrumentChannel): # doc done *******************************
    """
    Combines all the parameters concerning the digital input/output
    Parameters:
            decimation: Sets the decimation factor for DIO data streamed to the
                host computer.
            drive: When on, the corresponding 8-bit bus is in output mode.
                When off, it is in input mode. Bit 0 corresponds to the least
                significant byte. For example, the value 1 drives the least significant
                byte, the value 8 drives the most significant byte.
            extclk: OFF: internally clocked with a fixed frequency of 60 MHz
                    ON:  externally clocked with a clock signal connected to DIO Pin 68.
                         The available range is from 1 Hz up to the internal clock
                         frequency
            input: Gives the value of the DIO input for those bytes where drive
                is disabled. Attention: this value is not readable in the instrument
                but the values are accessible via the sample data dict of the
                demodulator (streaming node)
            mode: Manual: Manual setting of the DIO output value.
                  Threshold unit: Enables setting of DIO output values by the
                      threshold unit.
            output: Sets the value of the DIO output for those bytes where 'drive'
                is enabled.
    """
    def __init__(self, parent: 'ZIMFLI', name: str, channum: int):
        """
        Creates a new DIOChannel
        Args:
            parent (ZIMFLI): the parent instrument of this channel
            name (str): the internal QCoDeS name of this channel
            channum: the channelnumber of this channel
        """
        super().__init__(parent, name)
        self.add_parameter('decimation',
                           label='decimation factor',
                           set_cmd=partial(self._parent._setter, 'dios',
                                           channum-1, Mode.INT, 'decimation'),
                           get_cmd=partial(self._parent._getter, 'dios',
                                           channum-1, Mode.INT, 'decimation'),
                           vals=vals.Ints(),
                           docstring="Sets the decimation factor for DIO data"
                                     " streamed to the host computer.")
        self.add_parameter('direction',
                           label='Input(0)-Output(1) Bitmask',
                           set_cmd=partial(self._parent._setter, 'dios',
                                           channum-1, Mode.INT, 'drive'),
                           get_cmd=partial(self._parent._getter, 'dios',
                                           channum-1, Mode.INT, 'drive'),
                           vals=vals.Ints(0, 15),
                           docstring="Bitmask for the direction of the four bytes"
                                     " of the digital interface. The first bit is"
                                     " for the first byte, the 4th bit is for the"
                                     " last byte. High denotes an output byte and"
                                     " Low denotes an input byte.")
        self.add_parameter('extclk',
                           label='external clocking',
                           set_cmd=partial(self._parent._setter, 'dios',
                                           channum-1, Mode.INT, 'extclk'),
                           get_cmd=partial(self._parent._getter, 'dios',
                                           channum-1, Mode.INT, 'extclk'),
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="'OFF': internally clocked with a fixed frequency"
                                     " of 60 MHz. 'ON': externally clocked with a clock"
                                     " signal connected to DIO Pin 68. The available"
                                     " range is from 1 Hz up to the internal clock"
                                     " frequency")
        #self.add_parameter('input',
        #                   label='DIO input',
        #                   set_cmd=False,
        #                   get_cmd=partial(self._parent._getter, 'dios',
        #                                   channum-1, Mode.INT, 'input')
        #                  )
        # not readable in the instrument (streaming node)
        self.add_parameter('mode',
                           label='mode',
                           set_cmd=partial(self._parent._setter, 'dios',
                                           channum-1, Mode.INT, 'mode'),
                           get_cmd=partial(self._parent._getter, 'dios',
                                           channum-1, Mode.INT, 'mode'),
                           val_mapping={'Manual': 0, 'Threshold unit': 3},
                           vals=vals.Enum('Manual', 'Threshold unit'),
                           docstring="'Manual': Manual setting of the DIO output value."
                                     " 'Threshold unit': Enables setting of DIO output"
                                     " values by the threshold unit.")
        self.add_parameter('output',
                           label='DIO output',
                           set_cmd=partial(self._parent._setter, 'dios',
                                           channum-1, Mode.INT, 'output'),
                           get_cmd=partial(self._parent._getter, 'dios',
                                           channum-1, Mode.INT, 'output'),
                           vals=vals.Ints(),
                           docstring="Sets the value of the DIO output for those"
                                     " bytes where 'drive' is enabled.")



class MDSChannel(InstrumentChannel): # doc done *******************************
    """
    The feature Multi device synchronization can be used to sync more than one
    Lock-In Amplifier to use always the same clock phase. For more informations
    please look into the manual. This feature is not tested!
    Parameter:
        armed: (ReadOnly) Indicates whether the mds module is armed and waiting
            for pulses.
        drive: Enables output of synch pulses on trigger output 1. Possible
            values are 'ON' and 'OFF'.
        enable: Enables the mds module. Possible values are 'ON' and 'OFF'.
        source: Select input source for mds synch signal.
        syncvalid: (ReadOnly) Indicates if sync pulses are received.
        timestamp: Used to set the resulting adjusted timestamp.

    TODO: what are possible values -> validate
    """
    def __init__(self, parent: 'ZIMFLI', name: str):
        super().__init__(parent, name)
        self.add_parameter('armed',
                           set_cmd=False,
                           get_cmd=partial(self._getter, 'armed'),
                           docstring="(ReadOnly) Indicates whether the mds module"
                                     " is armed and waiting for pulses.")
        self.add_parameter('drive',
                           set_cmd=partial(self._setter, 'drive'),
                           get_cmd=partial(self._getter, 'drive'),
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="Enables output of synch pulses on trigger output 1")
        self.add_parameter('enable',
                           set_cmd=partial(self._setter, 'enable'),
                           get_cmd=partial(self._getter, 'enable'),
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="Enables the mds module.")
        self.add_parameter('source',
                           set_cmd=partial(self._setter, 'source'),
                           get_cmd=partial(self._getter, 'source'),
                           vals=vals.Ints(),
                           docstring="Select input source for mds synch signal.") # TODO
        self.add_parameter('syncvalid',
                           set_cmd=False,
                           get_cmd=partial(self._getter, 'syncvalid'),
                           docstring="(ReadOnly) Indicates if sync pulses are received.")
        self.add_parameter('timestamp',
                           set_cmd=partial(self._setter, 'timestamp'),
                           get_cmd=partial(self._getter, 'timestamp'),
                           vals=vals.Ints(),
                           docstring="Used to set the resulting adjusted timestamp.")


    def _getter(self, label):
        """
        Function to query the settings of MDS.

        Args:
            label (str): string to query
        """

        querystr = '/{}/mds/{}'.format(self.parent.device, label)
        value = self.parent.daq.getInt(querystr)

        return value

    def _setter(self, setting: str, value: int) -> None:
        """
        Function to set MDS settings.

        Args:
            setting (str): The module's setting to set.
            value (int): The value to set the setting to.
        """

        setstr = '/{}/mds/{}'.format(self.parent.device, setting)
        self.parent.daq.setInt(setstr, value)


class PIDChannel(InstrumentChannel):
    """
    Combines all parameters concerning the PIDs
    These Parameters are only available if the MF-PID Quad PID/PLL Controller
    option is installed on the MFLI parent Instrument.
    ATTENTION: this function is not tested!
    Parameters:
        center: Sets the center value for the PID output. After adding the
            Center value, the signal is clamped to Center + Lower Limit and
            Center + Upper Limit.
        derivative_gain: PID derivative gain.
        d_limit_time_constant: The cutoff of the low-pass filter for the D
            (derivative gain) limitation given as time constant. When set to
            0, the lowpass filter is disabled.
        enable: Enable the PID controller
            Possible values: 'ON', 'OFF'
        integral_gain: PID integral gain I
        input: Select the input source of the PID controller and also
            select input channel of PID controller.
            Possible values: 'Demod X <1, 2, ..., 8>' , 'Demod Y <1, 2, ..., 8>',
                'Demod R <1, 2, ..., 8>', 'Demod Theta <1, 2, ..., 8>',
                'Aux In <1, 2>', 'Aux Out <1, 2, 3, 4>'
        limit_lower: Sets the lower limit for the PID output. After adding
            the Center value, the signal is clamped to Center + Lower Limit
            and Center + Upper Limit.
        limit_upper: Sets the upper limit for the PID output. After adding
            the Center value, the signal is clamped to Center + Lower Limit
            and Center + Upper Limit.
        mode: Sets the operation mode of the PID module.
            Possible value: 'PID', 'PLL' (phase locked loop),
                'ExtRef' (external reference)
        output: Select the output of the PID controller
            Possible values:
                'Main signal Amps <1, 2>' (Feedback to the main signal
                                           output amplitudes),
                'Internal oscs <1, 2>' (Feedback to any of the internal
                                        oscillator frequencies),
                'Demod phase <1, 2, ..., 8>' (Feedback to any of the 8
                                              demodulator phase set points),
                'Aux Out <1, 2, 3, 4>' (Feedback to any of the 4 Auxiliary
                                        Output's Offset),
                'Main signal Offset <1, 2>' (Feedback to the main Signal
                                             Output offset adjustment)
        proportional_gain: PID Proportional gain
        phaseunwrap: Enables the phase unwrapping to track phase errors past
            the +/-180 degree boundary and increase PLL bandwidth.
        rate: PID sampling rate and update rate of PID outputs. Needs to be
            set substantially higher than the targeted loop filter bandwidth.
        setpoint: PID controller setpoint
        shift: Difference between the current output value Out and the Center.
            Shift = P*Error + I*Int(Error, dt) + D*dError/dt
        value: curretn PID output value
        auto_adaptation: This defines the type of automatic adaptation of
            parameters in the PID.
            Possible values: 'no adaptation' (No automatic adaption.),
                  'coefficients' (The coefficients of the PID controller are
                                  automatically set.),
                  'low bw' (The PID coefficients, the filter bandwidth
                            and the output limits are automatically
                            set using a low bandwidth.),
                  'high bw' (The PID coefficients, the filter bandwidth
                             and the output limits are automatically
                             set using a high bandwidth.),
                  'all parameters' (All parameters of the PID including the
                                    center frequency are adapted.)
        enable_setpoint_toggle: Enables the setpoint toggle
            Possible values: 'ON', 'OFF'
        setpoint_toggle_rate: Defines the rate of setpoint toggling.
            Note that possible values are logarithmically spaced with a
            factor of 4 between values.
        setpoint_toggle_setpoint: Defines the setpoint value used for setpoint
            toggle.
    """
    def __init__(self, parent: 'ZIMFLI', name: str, channum: int):
        super().__init__(parent, name)
        self.add_parameter('center',
                           label='center value',
                           set_cmd=partial(self._parent._setter, 'pids',
                                           channum-1, Mode.DOUBLE, 'center'),
                           get_cmd=partial(self._parent._getter, 'pids',
                                           channum-1, Mode.DOUBLE, 'center'),
                           vals=vals.Numbers())
        self.add_parameter('derivativ_gain',
                           label='Derivative Gain',
                           set_cmd=partial(self._parent._setter, 'pids',
                                           channum-1, Mode.DOUBLE, 'D'),
                           get_cmd=partial(self._parent._getter, 'pids',
                                           channum-1, Mode.DOUBLE, 'D'),
                           vals=vals.Numbers())
        self.add_parameter('d_limit_time_constant',
                           label='derivative gain limitation given as time constant',
                           set_cmd=partial(self._parent._setter, 'pids',
                                           channum-1, Mode.DOUBLE, 'dlimittimeconstant'),
                           get_cmd=partial(self._parent._getter, 'pids',
                                           channum-1, Mode.DOUBLE, 'dlimittimeconstant'),
                           unit='s',
                           vals=vals.Numbers())
        self.add_parameter('enable',
                           label='enable',
                           set_cmd=partial(self._parent._setter, 'pids',
                                           channum-1, Mode.INT, 'enable'),
                           get_cmd=partial(self._parent._getter, 'pids',
                                           channum-1, Mode.INT, 'enable'),
                           val_mapping={'ON': 1, 'OFF': 0})
        self.add_parameter('integral_gain',
                           label='Integral gain',
                           set_cmd=partial(self._parent._setter, 'pids',
                                           channum-1, Mode.DOUBLE, 'I'),
                           get_cmd=partial(self._parent._getter, 'pids',
                                           channum-1, Mode.DOUBLE, 'I'),
                           vals=vals.Numbers())
        input_dict={'Demod X 1': '0 0',
                    'Demod X 2': '0 1',
                    'Demod X 3': '0 2',
                    'Demod X 4': '0 3',
                    'Demod X 5': '0 4',
                    'Demod X 6': '0 5',
                    'Demod X 7': '0 6',
                    'Demod X 8': '0 7',
                    'Demod Y 1': '1 0',
                    'Demod Y 2': '1 1',
                    'Demod Y 3': '1 2',
                    'Demod Y 4': '1 3',
                    'Demod Y 5': '1 4',
                    'Demod Y 6': '1 5',
                    'Demod Y 7': '1 6',
                    'Demod Y 8': '1 7',
                    'Demod R 1': '2 0',
                    'Demod R 2': '2 1',
                    'Demod R 3': '2 2',
                    'Demod R 4': '2 3',
                    'Demod R 5': '2 4',
                    'Demod R 6': '2 5',
                    'Demod R 7': '2 6',
                    'Demod R 8': '2 7',
                    'Demod Theta 1': '3 0',
                    'Demod Theta 2': '3 1',
                    'Demod Theta 3': '3 2',
                    'Demod Theta 4': '3 3',
                    'Demod Theta 5': '3 4',
                    'Demod Theta 6': '3 5',
                    'Demod Theta 7': '3 6',
                    'Demod Theta 8': '3 7',
                    'Aux In 1': '4 0',
                    'Aux In 2': '4 1',
                    'Aux Out 1': '5 0',
                    'Aux Out 2': '5 1',
                    'Aux Out 3': '5 2',
                    'Aux Out 4': '5 3'}
        self.add_parameter('input',
                           label='input source and channel number',
                           set_cmd=partial(self.input_setter(channum)),
                           get_cmd=partial(self.input_getter(channum)),
                           val_mapping=input_dict)
        self.add_parameter('limit_lower',
                           label='lower limit',
                           set_cmd=partial(self._parent._setter, 'pids',
                                           channum-1, Mode.DOUBLE, 'limitlower'),
                           get_cmd=partial(self._parent._getter, 'pids',
                                           channum-1, Mode.DOUBLE, 'limitlower'),
                           vals=vals.Numbers())
        self.add_parameter('limit_upper',
                           label='upper limit',
                           set_cmd=partial(self._parent._setter, 'pids',
                                           channum-1, Mode.DOUBLE, 'limitupper'),
                           get_cmd=partial(self._parent._getter, 'pids',
                                           channum-1, Mode.DOUBLE, 'limitupper'),
                           vals=vals.Numbers())
        self.add_parameter('mode',
                           label='operation mode',
                           set_cmd=partial(self._parent._setter, 'pids',
                                           channum-1, Mode.INT, 'mode'),
                           get_cmd=partial(self._parent._getter, 'pids',
                                           channum-1, Mode.INT, 'mode'),
                           val_mapping={'PID': 0,
                                        'PLL': 1,
                                        'ExtRef': 2})
        output_dict = {'Main signal Amps 1': '0 0', #TODO are the signal outputs 'Main signal'?
                       'Main signal Amps 2': '0 1',
                       'Internal oscs 1': '1 0',
                       'Internal oscs 2': '1 1',
                       'Demod phase 1': '2 0',
                       'Demod phase 2': '2 1',
                       'Demod phase 3': '2 2',
                       'Demod phase 4': '2 3',
                       'Demod phase 5': '2 4',
                       'Demod phase 6': '2 5',
                       'Demod phase 7': '2 6',
                       'Demod phase 8': '2 7',
                       'Aux Out 1': '3 0',
                       'Aux Out 2': '3 1',
                       'Aux Out 3': '3 2',
                       'Aux Out 4': '3 3',
                       'Main signal Offset 1': '4 0',
                       'Main signal Offset 2': '4 1',}
        self.add_parameter('output',
                           label='output selection',
                           set_cmd=partial(self.output_setter, channum),
                           get_cmd=partial(self.output_getter, channum),
                           val_mapping=output_dict)
        self.add_parameter('proportional_gain',
                           label='Proportional gain',
                           set_cmd=partial(self._parent._setter, 'pids',
                                           channum-1, Mode.DOUBLE, 'P'),
                           get_cmd=partial(self._parent._getter, 'pids',
                                           channum-1, Mode.DOUBLE, 'P'),
                           vals=vals.Numbers())
        self.add_parameter('phaseunwrap',
                           label='Enable/Disable phase unwrapping',
                           set_cmd=partial(self._parent._setter, 'pids',
                                           channum-1, Mode.INT, 'phaseunwrap'),
                           get_cmd=partial(self._parent._getter, 'pids',
                                           channum-1, Mode.INT, 'phaseunwrap'),
                           val_mapping={'ON':1, 'OFF':2})
        self.add_parameter('rate',
                           label='sampling and update rate',
                           set_cmd=partial(self._parent._setter, 'pids',
                                           channum-1, Mode.DOUBLE, 'rate'),
                           get_cmd=partial(self._parent._getter, 'pids',
                                           channum-1, Mode.DOUBLE, 'rate'),
                           unit='Hz',
                           vals=vals.Numbers())
        self.add_parameter('setpoint',
                           label='setpoint',
                           set_cmd=partial(self._parent._setter, 'pids',
                                           channum-1, Mode.DOUBLE, 'setpoint'),
                           get_cmd=partial(self._parent._getter, 'pids',
                                           channum-1, Mode.DOUBLE, 'setpoint'),
                           vals=vals.Numbers())
        self.add_parameter('shift',
                           label='shift',
                           set_cmd=partial(self._parent._setter, 'pids',
                                           channum-1, Mode.DOUBLE, 'shift'),
                           get_cmd=partial(self._parent._getter, 'pids',
                                           channum-1, Mode.DOUBLE, 'shift'),
                           vals=vals.Numbers())
        self.add_parameter('value',
                           label='value',
                           set_cmd=None,
                           get_cmd=partial(self._parent._getter, 'pids',
                                           channum-1, Mode.DOUBLE, 'value'),
                           vals=vals.Numbers)
        adapt_dict = {'no adaptation': 0,
                      'coefficients': 1,
                      'low bw': 2,
                      'high bw': 3,
                      'all parameters': 4}
        self.add_parameter('auto_adaptation',
                           label='type of automatic adaptation',
                           set_cmd=partial(self._parent._setter, 'pids',
                                           channum-1, Mode.INT, 'pll/automode'),
                           get_cmd=partial(self._parent._getter, 'pids',
                                           channum-1, Mode.INT, 'pll/automode'),
                           val_mapping=adapt_dict)
        self.add_parameter('enable_setpoint_toggle',
                           lable='enable/disable the setpoint toggle',
                           set_cmd=partial(self._parent._setter, 'pids',
                                           channum-1, Mode.INT, 'setpointtoggle/enable'),
                           get_cmd=partial(self._parent._getter, 'pids',
                                           channum-1, Mode.INT, 'setpointtoggle/enable'),
                           val_mapping={'ON': 1, 'OFF': 0})
        self.add_parameter('setpoint_toggle_rate',
                           label='rate of settpoint toggling',
                           set_cmd=partial(self._parent._setter, 'pids',
                                           channum-1, Mode.DOUBLE, 'setpointtoggle/rate'),
                           get_cmd=partial(self._parent._getter, 'pids',
                                           channum-1, Mode.DOUBLE, 'setpointtoggle/rate'),
                           unit='Hz',
                           vals=vals.Numbers())
        self.add_parameter('setpoint_toggle_setpoint',
                           label='setpoint value used for setpoint toggle',
                           set_cmd=partial(self._parent._setter, 'pids',
                                           channum-1, Mode.DOUBLE, 'setpointtoggle/setpoint'),
                           get_cmd=partial(self._parent._getter, 'pids',
                                           channum-1, Mode.DOUBLE, 'setpointtoggle/setpoint'),
                           vals=vals.Numbers())

    def input_setter(self, channum: int, cmd: str) -> None:
        (source, channel) = cmd.split(" ")
        self._parent.daq.setInt('{}/pids/{}/input'.format(self._parent.device,
                                channum), int(source))
        self._parent.daq.setInt('{}/pid/{}/inputchannel'.format(self._parent.device,
                                channum), int(channel))

    def input_getter(self, channum: int) -> str:
        ret = str(self._parent.daq.getInt('{}/pids/{}/input'.format(self._parent.device,
                                          channum)))+' '
        ret += str(self._parent.daq.setInt('{}/pid/{}/inputchannel'.format(self._parent.device,
                                           channum)))
        return ret

    def output_setter(self, channum: int, cmd: str) -> None:
        (output, channel) = cmd.split(" ")
        self._parent.daq.setInt('{}/pids/{}/output'.format(self._parent.device,
                                channum), int(output))
        self._parent.daq.setInt('{}/pids/{}/outputchannel'.format(self._parent.device,
                                channum), int(channel))

    def output_getter(self, channum: int) -> str:
        ret = str(self._parent.daq.getInt('{}/pids/{}/output'.format(self._parent.device,
                                          channum)))+' '
        ret += str(self._parent.daq.setInt('{}/pid/{}/outputchannel'.format(self._parent.device,
                                           channum)))
        return ret


class SweeperChannel(InstrumentChannel): # doc done ***************************
    """
    This submodule is used to configure the sweep functionality. All parameter
    values are stored in a local dict and send to the data server with the
    build_sweep function of the Sweep class.
    Parameter:
        param: the device parameter to be swept
            Possible values: 'Aux Out 1 Offset', 'Aux Out 2 Offset',
                'Aux Out 3 Offset', 'Aux Out 4 Offset', 'Demod 1 Phase Shift'
                'Demod 2 Phase Shift', 'Osc 1 Frequency', 'Output 1 Amplitude 2',
                'Output 1 Offset'
            for devices with the MF-MD option there are also the values:
                'Osc 2 Frequency', 'Demod 2 Phase Shift', 'Demod 3 Phase Shift',
                'Demod 4 Phase Shift', 'Output 1 Amplitude 4',
                'Output 2 Amplitude 8', 'Output 2 Offset'
        start: start value of the sweep parameter.
        stop: stop value of the sweep parameter, both values are included in the sweep range.
        samplecount: number of measurement points to set the sweep on.
        endless: Enable Endless mode to run the sweeper continuously ('ON'). If
            disabled ('OFF') the sweep runs only once.
        remaining_time: (ReadOnly) Reports the remaining time of the current sweep.
            A valid number is only returned once the sweeper has been started. An
            undefined sweep time is indicated as NAN, that means, the sweeper is
            not running.
        averaging_samples: Sets the number of data samples per sweeper parameter
            point that is considered in the measurement. The maximum of this value
            and averaging_time is taken as the effective calculation time. The
            actual number of samples is the maximum of this value and the averaging_time
            times the relevant sample rate.
        averaging_tc: Minimal averaging time constant.
        averaging_time: Sets the effective measurement time per sweeper parameter
            point that is considered in the measurement. The maximum between of
            this value and averaging_samples is taken as the effective calculation
            time. The actual number of samples is the maximum of this value times
            the relevant sample rate and the averaging_samples.
        bandwidth_mode: Specify how the sweeper should specify the bandwidth of
            each measurement point. Automatic is recommended in particular for
            logarithmic sweeps and assures the whole spectrum is covered. Possible
            values are:
                'current': the sweeper module leaves the demodulator bandwidth
                    settings entirely untouched
                'fixed': use the value from the parameter bandwidth
                'auto': bandwidth is set automatically
        bandwidth_overlap: If enabled the bandwidth of a sweep point may overlap
            with the frequency of neighboring sweep points. The effective bandwidth
            is only limited by the maximal bandwidth setting and omega suppression.
            As a result, the bandwidth is independent of the number of sweep points.
            For frequency response analysis bandwidth overlap should be enabled
            to achieve maximal sweep speed. Possible values are 'ON' or 'OFF'.
        bandwidth: This is the NEP {noise-equivalent bandwidth} bandwidth used by
            the sweeper if 'bandwidth_mode' is set to 'fixed'. If 'bandwidth_mode'
            is either 'auto' or 'current', this value is ignored.
        order: Defines the filter roll off to use when 'bandwidth_mode' is set to
            'fixed'. Valid values are between 1 (6 dB/octave) and 8 (48 dB/octave).
        max_bandwidth: Specifies the maximum bandwidth used when 'bandwidth_mode'
            is set to 'auto'. The default is 1.25 MHz.
        omega_supression: Damping of omega and 2omega components when 'bandwidth_mode'
            is set to 'auto'. Default is 40dB in favor of sweep speed. Use a higher
            value for strong offset values or 3omega measurement methods.
        loopcount: The number of sweeps to perform.
        phaseunwrap: Enable unwrapping of slowly changing phase evolutions around
            the +/-180 degree boundary. Possible values are: 'ON' or 'OFF'.
        sinc_filter: Enables the sinc filter if the sweep frequency is below 50 Hz.
            This will improve the sweep speed at low frequencies as omega components
            do not need to be suppressed by the normal low pass filter.
        mode: Selects the scanning type. Possible values are:
            `sequential': incremental scanning from start to stop value.
            `binary': Nonsequential sweep continues increase of resolution over
                entire range. It starts in the middle between start and stop, then
                it goes to the middle of the first range, then to the middle of the
                second range. After this it goes to the middle of all 4 subranges
                and so on.
            `bidirectional': Sequential sweep from Start to Stop value and back
                to Start again.
            `reverse': reverse sequential scanning from stop to start value.
        settling_time: Minimum wait time in seconds between setting the new sweep
            parameter value and the start of the measurement. The maximum between
            this value and 'settling_tc' is taken as effective settling time. Note
            that the filter settings may result in a longer actual waiting/settling
            time.
        settling_inaccuracy: Demodulator filter settling inaccuracy defining the wait
            time between a sweep parameter change and recording of the next sweep point.
            The settling time is calculated as the time required to attain the specified
            remaining proportion [1e-13, 0.1] of an incoming step function. Typical
            inaccuracy values: 10m for highest sweep speed for large signals, 100u for
            precise amplitude measurements, 100n for precise noise measurements.
            Depending on the order of the demodulator filter the settling inaccuracy
            will define the number of filter time constants the sweeper has to wait.
            The maximum between this value and the settling time is taken as wait time
            until the next sweep point is recorded.
        settling_tc: Minimum wait time in factors of the time constant (TC) between
            setting the new sweep parameter value and the start of the measurement.
            This filter settling time is preferably configured via 'settling_inaccuracy'.
            The maximum between this value and 'settling_time' is taken as effective
            settling time.
        xmapping: Selects the spacing of the grid used by param. Possible values are:
            `linear': linear distribution of sweep parameter values
            `logarithmic': logarithmic distribution of sweep parameter values
        history_length: Maximum number of entries stored in the measurement history.
        clear_history: Remove all records from the history list. Possible values
            are: 'ON' or 'OFF'.
        directory: The directory to which sweeper measurements are saved to via
            Sweep.save().
        fileformat: The format of the file for saving sweeper measurements.
            Possible values are: `Matlab' or `CSV'.
       sweeptime: (ReadOnly) calculate the estimation of the sweep duration.
            This is not precise to more than a few percent. The return is None if
            the 'bandwidth_mode' setting is 'auto' (then all bets are off), otherwise
            a time in seconds.
        units: (ReadOnly) get the unit of the current sweep parameter ('param').
        sweeper_timeout: holds the maximum number of seconds for the sweep to finsh.
            If the sweep duration exeeds this time, it will be stopped. The initial
            value is set to 600s.
    """
    def __init__(self, parent: 'ZIMFLI', name: str):
        super().__init__(parent, name)
        self._sweepTimeout = 600
        # val_mapping for sweeper_param parameter
        sweepparams = {'Aux Out 1 Offset':     'auxouts/0/offset',
                       'Aux Out 2 Offset':     'auxouts/1/offset',
                       'Aux Out 3 Offset':     'auxouts/2/offset',
                       'Aux Out 4 Offset':     'auxouts/3/offset',
                       'Demod 1 Phase Shift':  'demods/0/phaseshift',
                       'Demod 2 Phase Shift':  'demods/1/phaseshift',
                       'Osc 1 Frequency':      'oscs/0/freq',
                       'Output 1 Amplitude 2': 'sigouts/0/amplitudes/1',
                       'Output 1 Offset':      'sigouts/0/offset',
                       }
        if 'MD' in parent.options:
            sweepparams.update( {'Demod 3 Phase Shift':  'demods/2/phaseshift',
                                 'Demod 4 Phase Shift':  'demods/3/phaseshift',
                                 'Osc 2 Frequency':      'oscs/1/freq',
                                 'Output 1 Amplitude 4': 'sigouts/0/amplitudes/3',
                                 'Output 2 Amplitude 8': 'sigouts/1/amplitudes/7',
                                 'Output 2 Offset':      'sigouts/1/offset'
                                 } )
        self.add_parameter('param',
                           label='Parameter to sweep (sweep x-axis)',
                           set_cmd=partial(self._setter, 'sweep/gridnode'),
                           get_cmd=partial(self._getter, 'sweep/gridnode'),
                           val_mapping=sweepparams,
                           docstring="The device parameter to be swept."
                                     +self._parent.possibleValues(sweepparams))
        self.add_parameter('start',
                            label='Start value of the sweep',
                            set_cmd=partial(self._setter, 'sweep/start'),
                            get_cmd=partial(self._getter, 'sweep/start'),
                            vals=vals.Numbers(),
                            docstring="start value of the sweep parameter.")
        self.add_parameter('stop',
                            label='Stop value of the sweep',
                            set_cmd=partial(self._setter, 'sweep/stop'),
                            get_cmd=partial(self._getter, 'sweep/stop'),
                            vals=vals.Numbers(),
                            docstring="stop value of the sweep parameter, included in sweep")
        self.add_parameter('samplecount',
                            label='Length of the sweep (pts)',
                            set_cmd=partial(self._setter, 'sweep/samplecount'),
                            get_cmd=partial(self._getter, 'sweep/samplecount'),
                            vals=vals.Ints(0, 2**64-1),
                            docstring="number of measurement points to set the sweep on.")
        self.add_parameter('endless',
                           label='enable endless sweep',
                           set_cmd=partial(self._setter, 'sweep/endless'),
                           get_cmd=partial(self._getter, 'sweep/endless'),
                           val_mapping={'ON': 1, 'OFF': 0},
                           docstring="Enable Endless mode to run the sweeper continuously"
                                     " ('ON'). If disabled ('OFF') the sweep runs only once.")
        self.add_parameter('remaining_time',
                           label='remaining time of current sweep',
                           set_cmd=False,
                           get_cmd=partial(self._getter, 'sweep/remainingtime'),
                           unit='s',
                           docstring="(ReadOnly) Reports the remaining time of the"
                                     " current sweep. A valid number is only returned"
                                     " once the sweeper has been started. An undefined"
                                     " sweep time is indicated as NAN, that means, the"
                                     " sweeper is not running.")
        self.add_parameter('averaging_samples',
                           label=('Minimal no. of samples to average at ' +
                                  'each sweep point'),
                           set_cmd=partial(self._setter, 'sweep/averaging/sample'),
                           get_cmd=partial(self._getter,'sweep/averaging/sample'),
                           vals=vals.Ints(1, 2**64-1),
                           docstring="Sets the number of data samples per sweeper"
                                     " parameter point that is considered in the"
                                     " measurement. The maximum of this value and"
                                     " averaging_time is taken as the effective"
                                     " calculation time. The actual number of samples"
                                     " is the maximum of this value and the averaging_time"
                                     " times the relevant sample rate.")
        self.add_parameter('averaging_tc',
                           label=('Minimal averaging time constant'),
                           set_cmd=partial(self._setter, 'sweep/averaging/tc'),
                           get_cmd=partial(self._getter, 'sweep/averaging/tc'),
                           unit='s',
                           vals=vals.Numbers(),
                           docstring="Minimal averaging time constant.")
        self.add_parameter('averaging_time',
                           label=('Minimal averaging time'),
                           set_cmd=partial(self._setter, 'sweep/averaging/time'),
                           get_cmd=partial(self._getter, 'sweep/averaging/time'),
                           unit='s',
                           vals=vals.Numbers(),
                           docstring="Sets the effective measurement time per sweeper"
                                     " parameter point that is considered in the"
                                     " measurement. The maximum between of this value"
                                     " and averaging_samples is taken as the effective"
                                     " calculation time. The actual number of samples"
                                     " is the maximum of this value times the relevant"
                                     " sample rate and the averaging_samples.")
        self.add_parameter('bandwidth_mode',
                           label='bandwidth control mode',
                           set_cmd=partial(self._setter, 'sweep/bandwidthcontrol'),
                           get_cmd=partial(self._getter, 'sweep/bandwidthcontrol'),
                           val_mapping={'auto': 2, 'fixed': 1, 'current': 0},
                           docstring="""
                           Specify how the sweeper should specify the bandwidth of
                           each measurement point. Automatic is recommended in particular for
                           logarithmic sweeps and assures the whole spectrum is covered. Possible
                           values are:
                               'current': the sweeper module leaves the demodulator bandwidth settings entirely untouched
                               'fixed': use the value from the parameter bandwidth
                               'auto': bandwidth is set automatically
                           """)
        self.add_parameter('bandwidth_overlap',
                           label='overlapping bandwidth between neighbouring'
                                   +'sweep point',
                           set_cmd=partial(self._setter, 'sweep/bandwidthoverlap'),
                           get_cmd=partial(self._getter, 'sweep/bandwidthoverlap'),
                           val_mapping={'ON': 1, 'OFF': 0},
                           docstring="If enabled the bandwidth of a sweep point may overlap"
                                     " with the frequency of neighboring sweep points. The"
                                     " effective bandwidth is only limited by the maximal"
                                     " bandwidth setting and omega suppression. As a result,"
                                     " the bandwidth is independent of the number of sweep"
                                     " points. For frequency response analysis bandwidth"
                                     " overlap should be enabled to achieve maximal sweep"
                                     " speed. Possible values are 'ON' or 'OFF'.")
        self.add_parameter('bandwidth',
                           label='Fixed bandwidth sweeper bandwidth (NEP)',
                           set_cmd=partial(self._setter, 'sweep/bandwidth'),
                           get_cmd=partial(self._getter, 'sweep/bandwidth'),
                           unit='Hz',
                           vals=vals.Numbers(),
                           docstring="This is the NEP {noise-equivalent bandwidth}"
                                     " bandwidth used by the sweeper if 'bandwidth_mode'"
                                     " is set to 'fixed'. If 'bandwidth_mode' is either"
                                     " 'auto' or 'current', this value is ignored.")
        self.add_parameter('order',
                           label='Sweeper filter order',
                           set_cmd=partial(self._setter, 'sweep/order'),
                           get_cmd=partial(self._getter, 'sweep/order'),
                           vals=vals.Ints(1, 8),
                           docstring="Defines the filter roll off to use when"
                                     " 'bandwidth_mode' is set to 'fixed'. Valid"
                                     " values are between 1 (6 dB/octave) and 8"
                                     " (48 dB/octave).")
        self.add_parameter('max_bandwidth',
                           label='maximum bandwidth',
                           set_cmd=partial(self._setter, 'sweep/maxbandwidth'),
                           get_cmd=partial(self._getter, 'sweep/maxbandwidth'),
                           unit = 'Hz',
                           vals=vals.Numbers(),
                           docstring="Specifies the maximum bandwidth used when"
                                     " 'bandwidth_mode' is set to 'auto'. The"
                                     " default is 1.25 MHz.")
        self.add_parameter('omega_suppression',
                           label='damping of omega',
                           set_cmd=partial(self._setter, 'sweep/omegasuppression'),
                           get_cmd=partial(self._getter, 'sweep/omegasuppression'),
                           unit='dB',
                           vals=vals.Numbers(),
                           docstring="Damping of omega and 2omega components when"
                                     " 'bandwidth_mode' is set to 'auto'. Default"
                                     " is 40dB in favor of sweep speed. Use a higher"
                                     " value for strong offset values or 3omega"
                                     " measurement methods.")
        self.add_parameter('loopcount',
                           label='no. of sweeps',
                           set_cmd=partial(self._setter, 'sweep/loopcount'),
                           get_cmd=partial(self._getter, 'sweep/loopcount'),
                           vals=vals.Ints(0, 2**64-1),
                           docstring="The number of sweeps to perform.")
        self.add_parameter('phaseunwrap',
                           label='unwrapping of slowly changing phase evolution',
                           set_cmd=partial(self._setter, 'sweep/phaseunwrap'),
                           get_cmd=partial(self._getter, 'sweep/phaseunwrap'),
                           val_mapping={'ON': 1, 'OFF': 0},
                           docstring="Enable unwrapping of slowly changing phase"
                                     " evolutions around the +/-180 degree boundary."
                                     " Possible values are: 'ON' or 'OFF'.")
        self.add_parameter('sinc_filter',
                           label='enable sinc filter',
                           set_cmd=partial(self._setter, 'sweep/sincfilter'),
                           get_cmd=partial(self._getter, 'sweep/sincfilter'),
                           val_mapping={'ON': 1, 'OFF': 0},
                           docstring="Enables the sinc filter if the sweep frequency"
                                     " is below 50 Hz. This will improve the sweep"
                                     " speed at low frequencies as omega components"
                                     " do not need to be suppressed by the normal"
                                     " low pass filter.")
        # val_mapping for mode parameter
        sweepmodes = {'sequential': 0,
                      'binary': 1,
                      'biderectional': 2,
                      'reverse': 3}
        self.add_parameter('mode',
                            label='Sweep mode',
                            set_cmd=partial(self._setter, 'sweep/scan'),
                            get_cmd=partial(self._getter, 'sweep/scan'),
                            val_mapping=sweepmodes,
                            docstring="""
                            Selects the scanning type. Possible values are:
                                `sequential': incremental scanning from start to stop value.
                                `binary': Nonsequential sweep continues increase of resolution over
                                    entire range. It starts in the middle between start and stop, then
                                    it goes to the middle of the first range, then to the middle of the
                                    second range. After this it goes to the middle of all 4 subranges
                                    and so on.
                                `bidirectional': Sequential sweep from Start to Stop value and back
                                    to Start again.
                                `reverse': reverse sequential scanning from stop to start value.
                            """)
        self.add_parameter('settling_time',
                           label=('Minimal settling time for the sweeper'),
                           set_cmd=partial(self._setter, 'sweep/settling/time'),
                           get_cmd=partial(self._getter, 'sweep/settling/time'),
                           vals=vals.Numbers(0),
                           unit='s',
                           docstring="Minimum wait time in seconds between setting the"
                                     " new sweep parameter value and the start of the"
                                     " measurement. The maximum between this value and"
                                     " 'settling_tc' is taken as effective settling time."
                                     " Note that the filter settings may result in a longer"
                                     " actual waiting/settling time.")
        self.add_parameter('settling_inaccuracy',
                           label='Demodulator filter settling inaccuracy',
                           set_cmd=partial(self._setter, 'sweep/settling/inaccuracy'),
                           get_cmd=partial(self._getter, 'sweep/settling/inaccuracy'),
                           vals=vals.Numbers(),
                           docstring="Demodulator filter settling inaccuracy defining the wait"
                                     " time between a sweep parameter change and recording of"
                                     " the next sweep point. The settling time is calculated"
                                     " as the time required to attain the specified remaining"
                                     " proportion [1e-13, 0.1] of an incoming step function."
                                     " Typical inaccuracy values: 10m for highest sweep speed"
                                     " for large signals, 100u for precise amplitude measurements,"
                                     " 100n for precise noise measurements. Depending on the order"
                                     " of the demodulator filter the settling inaccuracy will"
                                     " define the number of filter time constants the sweeper has"
                                     " to wait. The maximum between this value and the settling"
                                     " time is taken as wait time until the next sweep point is"
                                     " recorded.")
        self.add_parameter('settling_tc',
                           label='Sweep filter settling time',
                           get_cmd=partial(self._getter, 'sweep/settling/tc'),
                           docstring="Minimum wait time in factors of the time constant (TC)"
                                     " between setting the new sweep parameter value and the"
                                     " start of the measurement. This filter settling time is"
                                     " preferably configured via 'settling_inaccuracy'. The"
                                     " maximum between this value and 'settling_time' is taken"
                                     " as effective settling time.")
        self.add_parameter('xmapping',
                           label='Sweeper x mapping',
                           set_cmd=partial(self._setter, 'sweep/xmapping'),
                           get_cmd=partial(self._getter, 'sweep/xmapping'),
                           val_mapping={'linear': 0, 'logarithmic': 1},
                           docstring="Selects the spacing of the grid used by param."
                                     " Possible values are 'linear' or 'logarithmic'")
        self.add_parameter('history_length',
                           label='number of entries stored in measurement history',
                           set_cmd=partial(self._setter, 'sweep/historylength'),
                           get_cmd=partial(self._getter, 'sweep/historylength'),
                           vals=vals.Ints(0, 2**64-1),
                           docstring="Maximum number of entries stored in the"
                                     " measurement history.")
        self.add_parameter('clear_history',
                           label='Remove all records from the history list',
                           set_cmd=partial(self._setter, 'sweep/clearhistory'),
                           get_cmd=partial(self._getter, 'sweep/clearhistory'),
                           val_mapping={'ON': 1, 'OFF': 0},
                           docstring="Remove all records from the history list."
                                     " Possible values are: 'ON' or 'OFF'.")
        self.add_parameter('directory',
                           label='directory to which measurements are saved',
                           set_cmd=partial(self._setter, 'sweep/directory'),
                           get_cmd=partial(self._getter, 'sweep/directory'),
                           docstring="The directory to which sweeper measurements"
                                     " are saved to via Sweep.save().")
        self.add_parameter('fileformat',
                           label='format of the saving files',
                           set_cmd=partial(self._setter, 'sweep/fileformat'),
                           get_cmd=partial(self._getter, 'sweep/fileformat'),
                           val_mapping={'Matlab': 0, 'CSV': 1},
                           docstring="The format of the file for saving sweeper"
                                     " measurements. Possible values are: `Matlab'"
                                     " or `CSV'.")
        # val_mapping for sweeper_units parameter
        sweepunits = {'Aux Out 1 Offset': 'V',
                      'Aux Out 2 Offset': 'V',
                      'Aux Out 3 Offset': 'V',
                      'Aux Out 4 Offset': 'V',
                      'Demod 1 Phase Shift': 'degrees',
                      'Demod 2 Phase Shift': 'degrees',
                      'Demod 3 Phase Shift': 'degrees',
                      'Demod 4 Phase Shift': 'degrees',
                      'Osc 1 Frequency': 'Hz',
                      'Osc 2 Frequency': 'Hz',
                      'Output 1 Amplitude 2': 'V',
                      'Output 1 Amplitude 4': 'V',
                      'Output 1 Offset': 'V',
                      'Output 2 Amplitude 8': 'V',
                      'Output 2 Offset': 'V'
                      }
        self.add_parameter('units',
                           label='Units of sweep x-axis',
                           get_cmd=self.parameters['param'],
                           get_parser=lambda x:sweepunits[x],
                           docstring="(ReadOnly) get the unit of the current"
                                     " sweep parameter ('param').")
        self.add_parameter('sweeptime',
                           label='Expected sweep time',
                           unit='s',
                           get_cmd=self._get_sweep_time,
                           docstring="(ReadOnly) calculate the estimation of the sweep"
                                     " duration. This is not precise to more than a few"
                                     " percent. The return is None if the 'bandwidth_mode'"
                                     " setting is 'auto' (then all bets are off), otherwise"
                                     " a time in seconds.")
        self.add_parameter('sweeper_timeout',
                           label='Sweep timeout',
                           unit='s',
                           get_cmd=self._getSwTimeout,
                           set_cmd=self._setSwTimeout,
                           docstring="holds the maximum number of seconds for the sweep"
                                     " to finsh. If the sweep duration exeeds this time,"
                                     " it will be stopped. The initial value is set to 600s.")

    def _setSwTimeout(self, t):
        self._sweepTimeout = t

    def _getSwTimeout(self):
        return self._sweepTimeout

    def _setter(self, setting, value):
        """
        set_cmd for all sweeper parameters. The value and setting are saved in
        a dictionary which is read by the Sweep parameter's build_sweep method
        and only then sent to the instrument.
        """
        key = '/'.join(setting.split('/')[1:])
        self._parent._sweepdict[key] = value
        self._parent.sweep_correctly_built = False

    def _getter(self, setting):
        """
        General get_cmd for sweeper parameters
        The built-in sweeper.get command returns a dictionary, but we want
        single values.
        Args:
            setting (str): the path used by ZI to describe the setting,
            e.g. 'sweep/settling/time'
        """
        returndict = self._parent.sweeper.get(setting)  # this is a dict
        # The dict may have different 'depths' depending on the parameter.
        # The depth is encoded in the setting string (number of '/')
        keys = setting.split('/')[1:]
        while keys != []:
            key = keys.pop(0)
            returndict = returndict[key]
        rawvalue = returndict
        if (isinstance(rawvalue, np.ndarray) or isinstance(rawvalue, list))\
        and len(rawvalue) == 1:
            value = rawvalue[0]
        else:
            value = rawvalue
        return value

    def _get_sweep_time(self):
        """
        get_cmd for the sweeptime parameter.
        Note: this calculation is only an estimation and not precise to more
        than a few percent.
        Returns:
            Union[float, None]: None if the bandwidthcontrol setting is
              'auto' (then all bets are off), otherwise a time in seconds.
        Raises:
            ValueError: if no signals are added to the sweep
        """
        if self._parent._sweeper_signals == []:
            raise ValueError('No signals selected! Can not find sweep time.')
        mode = self.bandwidth_mode()
        # The effective time constant of the demodulator depends on the
        # sweeper/bandwidthcontrol setting.
        # If this setting is 'current', the largest current
        # time constant of the involved demodulators is used
        # If the setting is 'fixed', the NEP BW specified under
        # sweep/bandwidth is used. The filter order is needed to convert
        # the NEP BW to a time constant
        demods = set( [sig for sig in range(self._parent.demodulator_no)] )
        rates = []
        for demod in demods:
            rates.append(self._parent._getter('demods', demod, 1, 'rate')) #get the rate of the demodulators
        rate = min(rates)
        if mode == 'current':
            tcs = []
            for demod in demods:
                tcs.append(self._parent._getter('demods', demod, 1, 'timeconstant'))
            tau_c = max(tcs)
        elif mode == 'fixed':
            order = self.order()
            BW = self.bandwidth()
            tau_c = self.NEPBW_to_timeconstant(BW, order)
        elif mode == 'auto':
            return None
        settlingtime = max(self.parameters['settling_tc'].get()*tau_c,
                           self.parameters['settling_time'].get())
        averagingtime = max(self.parameters['averaging_time'].get()*tau_c*rate,
                            self.parameters['averaging_samples'].get())/rate
        time_est = (settlingtime+averagingtime)*self.samplecount()
        return time_est

    #@staticmethod why should this be static?
    def NEPBW_to_timeconstant(self, NEPBW, order):
        """
        Helper function to translate a NEP BW and a filter order
        to a filter time constant. Meant to be used when calculating
        sweeper sweep times.
        Note: precise only to within a few percent.
        Args:
            NEPBW (float): The NEP bandwidth in Hz
            order (int): The filter order
        Returns:
            float: The filter time constant in s.
        """
        const = {1: 0.249, 2: 0.124, 3: 0.093, 4: 0.078, 5: 0.068,
                 6: 0.061, 7: 0.056, 8: 0.052}
        tau_c = const[order]/NEPBW
        return tau_c


class Sweep(MultiParameter):
    """
    Parameter class for the ZIMFLI instrument class for the sweeper.
    The get method returns a tuple of arrays, where each array contains the
    values of a signal added to the sweep (e.g. demodulator 4 phase).
    Attributes:
        names (tuple): Tuple of strings containing the names of the sweep
          signals (to be measured)
        units (tuple): Tuple of strings containing the units of the signals
        shapes (tuple): Tuple of tuples each containing the length of a
          signal.
        setpoints (tuple): Tuple of N copies of the sweep x-axis points,
          where N is the number of measured signals
        setpoint_names (tuple): Tuple of N identical strings with the name
          of the sweep x-axis.
    TODO
    """
    def __init__(self, name, instrument, **kwargs):
        # The __init__ requires that we supply names and shapes,
        # but there is no way to know what they could be known at this time.
        # They are updated via build_sweep.
        super().__init__(name, names=('',), shapes=((1,),), **kwargs)
        self._instrument = instrument

    def build_sweep(self):
        """
        Build a sweep with the current sweep settings. Must be called
        before the sweep can be executed.
        For developers:
        This is a general function for updating the sweeper.
        Every time a parameter of the sweeper is changed, this function
        must be called to update the sweeper. Although such behaviour is only
        strictly necessary for parameters that affect the setpoints of the
        Sweep parameter, having to call this function for any parameter is
        deemed more user friendly (easier to remember; when? -always).
        The function sets all (user specified) settings on the sweeper and
        additionally sets names, units, and setpoints for the Sweep
        parameter.
        """
        if hasattr(self._instrument, 'sweep_correctly_built'):
            if self._instrument.sweep_correctly_built is True:
                return

        signals = self._instrument._sweeper_signals
        sweepdict = self._instrument._sweepdict

        log.info('Built a sweep')

        # Combination <username> -> <unit>
        sigunits = {'X': 'V', 'Y': 'V', 'R': 'Vrms', 'phase': 'degrees',
                    'Xrms': 'Vrms', 'Yrms': 'Vrms', 'Rrms': 'Vrms',
                    'phasePwr': '',
                    'Freq': 'Hz', 'FreqPwr': 'Hz',
                    'In1': 'V', 'In2': 'V',
                    'In1Pwr': 'V', 'In2Pwr': 'V'
                    }

        names = []
        units = []
        for sig in signals:
            name = sig.split('/')[-1]
            names.append(name)
            units.append(sigunits[name])
        self.names = tuple(names)
        self.units = tuple(units)
        self.labels = tuple(names)  # TODO: What are good labels?

        spnamedict = {'auxouts/0/offset': 'Volts',
                      'auxouts/1/offset': 'Volts',
                      'auxouts/2/offset': 'Volts',
                      'auxouts/3/offset': 'Volts',
                      'demods/0/phaseshift': 'degrees',
                      'demods/1/phaseshift': 'degrees',
                      'demods/2/phaseshift': 'degrees',
                      'demods/3/phaseshift': 'degrees',
                      'oscs/0/freq': 'Hz',
                      'oscs/1/freq': 'Hz',
                      'sigouts/0/amplitudes/3': 'Volts',
                      'sigouts/0/offset': 'Volts',
                      'sigouts/1/amplitudes/7': 'Volts',
                      'sigouts/1/offset': 'Volts'
                      }
        sp_name = spnamedict[sweepdict['gridnode']]

        self.setpoint_names = ((sp_name,),)*len(signals)
        start = sweepdict['start']
        stop = sweepdict['stop']
        npts = sweepdict['samplecount']
        # TODO: make sure that these setpoints are correct, i.e. actually
        # matching what the MFLI does
        # TODO: support non-sequential sweep mode
        if not sweepdict['scan'] == 0:
            raise NotImplementedError('Only sequential scanning is supported.')
        if sweepdict['xmapping'] == 0:
            sw = tuple(np.linspace(start, stop, npts))
        else:
            logstart = np.log10(start)
            logstop = np.log10(stop)
            sw = tuple(np.logspace(logstart, logstop, npts))
        self.setpoints = ((sw,),)*len(signals)
        self.shapes = ((npts,),)*len(signals)

        # Now actually send  the settings to the instrument
        for (setting, value) in sweepdict.items():
            setting = 'sweep/' + setting
            self._instrument.sweeper.set(setting, value)

        self._instrument.sweep_correctly_built = True


    def save(self):
        """
        Helper function to use the data servers save function.
        """
        self._instrument.sweeper.save()


    def get(self):
        """
        Execute the sweeper and return the data corresponding to the
        subscribed signals, used in qc.Loop().
        Returns:
            tuple: Tuple containing N numpy arrays where N is the number
              of signals added to the sweep.
        Raises:
            ValueError: If no signals have been added to the sweep
            ValueError: If a sweep setting has been modified since
              the last sweep, but Sweep.build_sweep has not been run
        """
        daq = self._instrument.daq
        signals = self._instrument._sweeper_signals
        sweeper = self._instrument.sweeper

        if signals == []:
            raise ValueError('No signals selected! Can not perform sweep.')

        if self._instrument.sweep_correctly_built is False:
            raise ValueError('The sweep has not been correctly built.' +
                             ' Please run Sweep.build_sweep.')

        # We must enable the demodulators we use.
        # After the sweep, they should be returned to their original state
        streamsettings = []  # This list keeps track of the pre-sweep settings
        for sigstr in signals:
            path = '/'.join(sigstr.split('/')[:-1])
            (_, dev, _, dmnum, _) = path.split('/')

            # If the setting has never changed, get returns an empty dict.
            # In that case, we assume that it's zero (factory default)
            try:
                toget = path.replace('sample', 'enable')
                # ZI like nesting inside dicts...
                setting = daq.get(toget)[dev]['demods'][dmnum]['enable']['value'][0]
            except KeyError:
                setting = 0
            streamsettings.append(setting)
            daq.setInt(path.replace('sample', 'enable'), 1)

            # We potentially subscribe several times to the same demodulator,
            # but that should not be a problem
            sweeper.subscribe(path)

        sweeper.execute()
        timeout = self._instrument.submodules['sweeper_channel'].sweeper_timeout()
        start = time.time()
        while not sweeper.finished():  # Wait until the sweep is done/timeout
            time.sleep(0.2)  # Check every 200 ms whether the sweep is done
            # Here we could read intermediate data via:
            # data = sweeper.read(True)...
            # and process it while the sweep is completing.
            if (time.time() - start) > timeout:
                # If for some reason the sweep is blocking, force the end of the
                # measurement.
                log.error("Sweep still not finished, forcing finish...")
                # should exit function with error message instead of returning
                sweeper.finish()

        print( "DBG: Sweeper execution time =", time.time() - start, "sec" )
        return_flat_dict = True
        data = sweeper.read(return_flat_dict)

        sweeper.unsubscribe('*')
        for (state, sigstr) in zip(streamsettings, signals):
            path = '/'.join(sigstr.split('/')[:-1])
            daq.setInt(path.replace('sample', 'enable'), int(state))

        return self._parsesweepdata(data)

    def _parsesweepdata(self, sweepresult):
        """
        Parse the raw result of a sweep into just the data asked for by the
        added sweeper signals. Used by Sweep.get.
        Args:
            sweepresult (dict): The dict returned by sweeper.read
        Returns:
            tuple: The requested signals in a tuple
        """
        # Translation <username> -> <dataname>
        trans = {'X': 'x',  'Y': 'y', 'R': 'r', 'phase': 'phase',
                 'Xrms': 'xpwr', 'Yrms': 'ypwr', 'Rrms': 'rpwr',
                 'phasePwr': 'phasepwr',
                 'Freq': 'frequency', 'FreqPwr': 'frequencypwr',
                 'In1': 'auxin0', 'In2': 'auxin1',
                 'In1Pwr': 'auxin0pwr', 'In2Pwr': 'auxin1pwr'
                 }

        returndata = []

        for signal in self._instrument._sweeper_signals:
            path = '/'.join(signal.split('/')[:-1])
            attr = signal.split('/')[-1]
            data = sweepresult[path][0][0][trans[attr]]
            returndata.append(data)

        return tuple(returndata)


class ScopeChannelChannel(InstrumentChannel):
    """
        ** NOT COMPLETLY TESTES YET ***

    Combines all the Parameters for the Scope channels, which can be found
    under DEV.../SCOPES/0/CHANNELS/n/
    Parameters:
        bw_limitation: Selects between sample decimation(OFF) and sample averaging(ON)
            for sample rates lower than the maximal available sampling rate.
            Averaging avoids aliasing, but may conceal signal peaks.
        full_scale: Indicates the full scale value of the scope channel
        input_select: Selects the scope input signal
            Possible Values: 'Signal Input 1', 'Current Input 1', 'Trigger 1',
                'Trigger 2', 'Aux Output 1', 'Aux Output 2', 'Aux Output 3',
                'Aux Output 4', 'Aux Input 1', 'Aux Input 2', 'Osc phi Demod 2',
                'Osc phi Demod 4', 'Demod 1 X', 'Demod 2 X', 'Demod 3 X',
                'Demod 4 X', 'Demod 1 Y', 'Demod 2 Y', 'Demod 3 Y', 'Demod 4 Y',
                'Demod 1 R', 'Demod 2 R', 'Demod 3 R', 'Demod 4 R', 'Demod 1 phi',
                'Demod 2 phi', 'Demod 3 phi', 'Demod 4 phi', 'PID 1 value',
                'PID 2 value', 'PID 3 value', 'PID 4 value', 'PID 1 Shift',
                'PID 2 Shift', 'PID 3 Shift', 'PID 4 Shift'
        limit_lower: Lower limit of the scope full scale range. For demodulator,
            PID, Boxcar, and AU signals the limit should be adjusted so that the
            signal covers the specified range to achieve optimal resolution.
        limit_upper: Upper limit of the scope full scale range. For demodulator,
            PID, Boxcar, and AU signals the limit should be adjusted so that the
            signal covers the specified range to achieve optimal resolution.
        offset: Indicates the offset value of the scope channel
        enable_stream: Enable scope streaming for the specified channel. This
            allows for continuous recording of scope data on the plotter and
            streaming to disk. Note: scope streaming requires the DIG option.
    """
    def __init__(self, parent: 'ZIMFLI', name: str, channum: int):
        """
        Creates a new ScopeChannelChannel.
        parent: should be the ZIMFLI device because the parent should be
            an Instrument and not an InstrumentChannel even if the ScopeChannelChannel
            belongs to the ScopeChannel and not really directly to the ZIMFLI
        name: QCoDeS internal name
        """
        super().__init__(parent, name)
        self._channum = channum

        self.add_parameter('bw_limitation',
                           label='sample averaging or sample decimation',
                           set_cmd=partial(self._parent._parent._setter, 'scopes/0/channels',
                                           channum-1, Mode.INT, 'bwlimit'),
                           get_cmd=partial(self._parent._parent._getter, 'scopes/0/channels',
                                           channum-1, Mode.INT, 'bwlimit'),
                           val_mapping={'ON': 0, 'OFF': 1},
                           vals=vals.Enum('ON', 'OFF'))
        self.add_parameter('full_scale',
                           label='full scale value',
                           set_cmd=partial(self._parent._parent._setter, 'scopes/0/channels',
                                           channum-1, Mode.DOUBLE, 'fullscale'),
                           get_cmd=partial(self._parent._parent._getter, 'scopes/0/channels',
                                           channum-1, Mode.DOUBLE, 'fullscale'),
                           vals=vals.Numbers())
        inputselect_dict = {'Signal Input 1': 0,
                            'Current Input 1': 1,
                            'Trigger 1': 2,
                            'Trigger 2': 3,
                            'Aux Output 1': 4,
                            'Aux Output 2': 5,
                            'Aux Output 3': 6,
                            'Aux Output 4': 7,
                            'Aux Input 1': 8,
                            'Aux Input 2': 9,
                            'Osc phi Demod 2': 10,
                            'Osc phi Demod 4': 11,
                            'PID 1 value': 80,
                            'PID 2 value': 81,
                            'PID 3 value': 82,
                            'PID 4 value': 83,
                            'PID 1 Shift': 144,
                            'PID 2 Shift': 145,
                            'PID 3 Shift': 146,
                            'PID 4 Shift': 147}
        if 'DIG' in self._parent._parent.options:
            demodulators = {'Demod 1 X': 16,
                            'Demod 2 X': 17,
                            'Demod 3 X': 18,
                            'Demod 4 X': 19,
                            'Demod 1 Y': 32,
                            'Demod 2 Y': 33,
                            'Demod 3 Y': 34,
                            'Demod 4 Y': 35,
                            'Demod 1 R': 48,
                            'Demod 2 R': 49,
                            'Demod 3 R': 50,
                            'Demod 4 R': 51,
                            'Demod 1 phi': 64,
                            'Demod 2 phi': 65,
                            'Demod 3 phi': 66,
                            'Demod 4 phi': 67,}
            inputselect_dict.update(demodulators)
        self.add_parameter('input_select',
                           label='Scope input signal',
                           set_cmd=partial(self._parent._parent._setter, 'scopes/0/channels',
                                           channum-1, Mode.INT, 'inputselect'),
                           get_cmd=partial(self._parent._parent._getter, 'scopes/0/channels',
                                           channum-1, Mode.INT, 'inputselect'),
                           val_mapping=inputselect_dict) #extra validation not needed,
                                                         #because an Enum-Validator is
                                                         #genereated with the keys of
                                                         #val_mapping is in
                                                         #the Parameters constructor
        self.add_parameter('limit_lower',
                           label='lower limit of full scale',
                           set_cmd=partial(self._parent._parent._setter, 'scopes/0/channels',
                                           channum-1, Mode.DOUBLE, 'limitlower'),
                           get_cmd=partial(self._parent._parent._getter, 'scopes/0/channels',
                                           channum-1, Mode.DOUBLE, 'limitlower'),
                           vals=vals.Numbers())
        self.add_parameter('limit_upper',
                           label='upper limit of full scale',
                           set_cmd=partial(self._parent._parent._setter, 'scopes/0/channels',
                                           channum-1, Mode.DOUBLE, 'limitupper'),
                           get_cmd=partial(self._parent._parent._getter, 'scopes/0/channels',
                                           channum-1, Mode.DOUBLE, 'limitupper'),
                           vals=vals.Numbers())
        self.add_parameter('offset',
                           label='offset vlaue of scope channel',
                           set_cmd=partial(self._parent._parent._setter, 'scopes/0/channels',
                                           channum-1, Mode.DOUBLE, 'offset'),
                           get_cmd=partial(self._parent._parent._getter, 'scopes/0/channels',
                                           channum-1, Mode.DOUBLE, 'offset'),
                           vals=vals.Numbers())
        if 'DIG' in self._parent._parent.options:
            self.add_parameter('enable_stream',
                               lable='enable stream of this channel',
                               set_cmd=partial(self._parent._parent._setter,
                                               'scopes/0/stream/enables',
                                               channum-1, Mode.INT, ''),
                               get_cmd=partial(self._parent._parent._setter,
                                               'scopes/0/stream/enables',
                                               channum-1, Mode.INT, ''),
                               val_mapping={'ON': 1, 'OFF': 0})


class ScopeChannel(InstrumentChannel):
    """
        ** NOT COMPLETLY TESTES YET ***

    Combines all the parameters for the Scope
    Parameters:
            channels: activates the scope channels
                Possible values:
                    1: Channel 1 on, Channel 2 off.
                    2: Channel 1 off, Channel 2 on.
                    3: Channel 1 on, Channel 2 on.
            runstop: Enables/disables the acquisition of scope shots
                Possible values: 'run' or 'stop'
            length: Defines the length of the recorded scope shot in
                number of samples
            single: TODO
            samplingrate: Defines the sampling rate of the scope
                Possible values: '60 MHz', '30 MHz', '15 MHZ', '7.5 MHz',
                    '3.75 MHz', '1.88 MHz', '938 kHz', '469 kHz', '234 kHz',
                    '117 kHz', '58.6 kHz', '29.3 kHz', '14.6 kHz', '7.32 kHz',
                    '3.66 kHz', '1.83 kHz'
            duration: total recording time for each sample in seconds
                (scope_length divided by scope_samplingrate in Hz)
            streamrate: Defines the streaming rate of the scope
                Possible values: '3.75 MHz', '1.88 MHz', '938 kHz', '469 kHz',
                    '234 kHz', '117 kHz', '58.6 kHz', '29.3 kHz', '14.6 kHz',
                    '7.32 kHz', '3.66 kHz', '1.83 kHz'
            streamsample: only gettable for getting a stream sample of
                the scope
            trig_signal: Selects the trigger source signal
                Possible values:
                    TODO
            trig_delay: Trigger position relative to reference. A positive
                delay results in less data being acquired before the trigger point,
                a negative delay results in more data being acquired before the
                trigger point.
            trig_enable: When triggering is enabled scope data are
                acquired every time the defined trigger condition is met.
                Possible Values: 'ON' or 'OFF'
            trig_holdoffseconds: is only existing in the beginning and
                when scope_trig_holdoffmode is changed to 's'
                Defines the time before the trigger is rearmed after a recording event.
            trig_holdoffevents: is only existing when the scope_trig_holdoffmode
                is changed to 'events'
                Defines the trigger event number that will trigger the next
                recording after a recording event. A value of '1' will start
                a recording for each trigger event.
            trig_holdoffmode: Selects the holdoff mode as time in seconds
                or number of events
                Possible Values: 's' or 'events'
            trig_level: defines the trigger level
            trig_reference: Trigger reference position relative to the
                acquired data. Default is 50% (0.5) which results in a
                reference point in the middle of the acquired data.
                Between 0 and 1
            trig_slope: Sets on which slope of the trigger signal the
                scope should trigger.
                Possible Values: 'None', 'Rise', 'Fall', 'Both'
            trig_state: When 1, indicates that the trigger signal satifies
                the conditions of the trigger. (only getable) TODO
            segments_count: Specifies the number of segments to be recorded
                in device memory. The maximum scope shot size is given by the
                available memory divided by the number of segments. This functionality
                requires the DIG option.
            segments: Enable segmented scope recording. This allows for
                full bandwidth recording of scope shots with a minimum dead time
                between individual shots. This functionality requires the DIG option.
            trig_gating_enable: If enabled the trigger will be gated by
                the trigger gating input signal. This feature requires the DIG
                option.
                Possible Values: 'ON' or 'OFF'
            trig_gating_source: Select the signal source used for trigger
                gating if gating is enabled. This feature requires the DIG option.
                Possible values: 'Trigger In 1 High', 'Trigger In 1 Low',
                     'Trigger In 2 High', 'Trigger In 2 Low'
            trig_hystabsolute: Defines the voltage the source signal
                must deviate from the trigger level before the trigger is
                rearmed again. Set to 0 to turn it off. The sign is defined
                by the Edge setting.
            trig_hystmode: Selects the mode to define the hysteresis strength.
                The relative mode will work best over the full input range as
                long as the analog input signal does not suffer from excessive noise.
                Possible Values: 'absolute', 'relative'
            trig_hystrelative: Hysteresis relative to the adjusted full
                scale signal input range. A hysteresis value larger than 1
                (100%) is allowed.
            bwlimit: Selects between sample decimation(OFF) and sample
                averaging(ON) for sample rates lower than the maximal
                available sampling rate. Averaging avoids aliasing, but may
                conceal signal peaks.
    Submodules:
            channels: ChannelList, which contains the two ScopeChannelChannels
            channel1: first ScopeChannelChannel, is needed to be able to set the
                parameters under .../scopes/0/channels/0
            channel2: first ScopeChannelChannel, is needed to be able to set the
                parameters under .../scopes/0/channels/1
    """
    def __init__(self, parent: 'ZIMFLI', name: str):
        super().__init__(parent, name)

        # This parameter corresponds to the Run/Stop button in the GUI
        #Enables the acqisition of the scope shots
        self.add_parameter('runstop',
                           label='run state',
                           set_cmd=partial(self._parent._setter, 'scopes', 0,
                                           Mode.INT, 'enable'),
                           get_cmd=partial(self._parent._getter, 'scopes', 0,
                                           Mode.INT,'enable'),
                           val_mapping={'run': 1, 'stop': 0},
                           vals=vals.Enum('run', 'stop'),
                           docstring='This parameter corresponds to the '
                                      'run/stop button in the GUI.')
        scopemodes = {'Time Domain': 1,
                      'Freq Domain FFT': 3}
        self.add_parameter('mode',
                           label='set mode to time or frequency domain',
                           set_cmd=partial(self._setter, 1, 0, 'mode'),
                           get_cmd=False,
                           val_mapping=scopemodes)
        self.add_parameter('scope_channels',
                           label='Recorded scope channels',
                           set_cmd=partial(self._setter, 0, 0, 'channel'),
                           get_cmd=partial(self._parent._getter, 'scopes', 0,
                                           Mode.INT, 'channel'),
                           vals=vals.Enum(1, 2, 3))
        self._samplingrate_codes = {'60 MHz': 0,
                                    '30 MHz': 1,
                                    '15 MHZ': 2,
                                    '7.5 MHz': 3,
                                    '3.75 MHz': 4,
                                    '1.88 MHz': 5,
                                    '938 kHz': 6,
                                    '469 kHz': 7,
                                    '234 kHz': 8,
                                    '117 kHz': 9,
                                    '58.6 kHz': 10,
                                    '29.3 kHz': 11,
                                    '14.6 kHz': 12,
                                    '7.32 kHz': 13,
                                    '3.66 kHz': 14,
                                    '1.83 kHz': 15}
        self.add_parameter('samplingrate',
                           label="sampling rate",
                           set_cmd=partial(self._setter, 0, 0, 'time'),
                           get_cmd=partial(self._parent._getter, 'scopes', 0,
                                           Mode.INT, 'time'),
                           val_mapping=self._samplingrate_codes)
        self.add_parameter('streamrate',
                           label="streaming rate",
                           set_cmd=partial(self._setter, 0, Mode.INT,
                                           'stream/rate'),
                           get_cmd=partial(self._getter, 0, Mode.INT,
                                           'stream/rate'),
                           val_mapping=self._samplingrate_codes)
        self.add_parameter('streamsample',
                           label='Sample of the Scope stream',
                           set_cmd=False,
                           get_cmd=partial(self._getter, 0, Mode.SAMPLE,
                                           'stream/sample'))
        self.add_parameter('length',
                           label="Length of scope trace (pts)",
                           set_cmd=partial(self._setter, 0, 1,
                                           'length'),
                           get_cmd=partial(self._parent._getter, 'scopes', 0,
                                           1, 'length'),
                           vals=vals.Ints(4096, 128000000),
                           get_parser=int)
        self.add_parameter('duration',
                           label="Scope trace duration",
                           set_cmd=partial(self._setter, 0, 0, 'duration'),
                           get_cmd=partial(self._getter, 'duration'),
                           vals=vals.Numbers(2.27e-6,4.660e3),
                           unit='s')
        #This is not what the user manual says
        #According to the user manual there are only 4 demodulators and moreover
        #you can set more then just the inputselect, so instead use two ScopeChannelChannels
        #as submodules
#        # Map the possible input sources to LabOne's IDs.
#        # The IDs can be seen in log file of LabOne UI
#        inputselect = {'Signal Input 1': 0,  # TODO
#                       'Signal Input 2': 1,
#                       'Trig Input 1': 2,
#                       'Trig Input 2': 3,
#                       'Aux Output 1': 4,
#                       'Aux Output 2': 5,
#                       'Aux Output 3': 6,
#                       'Aux Output 4': 7,
#                       'Aux In 1 Ch 1': 8,
#                       'Aux In 1 Ch 2': 9,
#                       'Osc phi Demod 4': 10,
#                       'Osc phi Demod 8': 11,
#                       'AU Cartesian 1': 112,
#                       'AU Cartesian 2': 113,
#                       'AU Polar 1': 128,
#                       'AU Polar 2': 129,
#                       }
#        # Add all 8 demodulators and their respective parameters
#        # to inputselect as well.
#        # Numbers correspond to LabOne IDs, taken from UI log.
#        for demod in range(1,9):
#            inputselect['Demod {} X'.format(demod)] = 15+demod
#            inputselect['Demod {} Y'.format(demod)] = 31+demod
#            inputselect['Demod {} R'.format(demod)] = 47+demod
#            inputselect['Demod {} Phase'.format(demod)] = 63+demod
#
#        for channel in range(1,3):
#            self.add_parameter('scope_channel{}_input'.format(channel),
#                            label=("Scope's channel {}".format(channel) +
#                                   " input source"),
#                            set_cmd=partial(self._scope_setter, 0, 0,
#                                            ('channels/{}/'.format(channel-1) +
#                                             'inputselect')),
#                            get_cmd=partial(self._getter, 'scopes', 0, 0,
#                                            ('channels/{}/'.format(channel-1) +
#                                             'inputselect')),
#                            val_mapping=inputselect,
#                            vals=vals.Enum(*list(inputselect.keys()))
#                            )
        channels = ChannelList(self, "channels", ScopeChannelChannel, snapshotable=False)
        for scopenum in range(1, 3):
            name = 'channel{}'.format(scopenum)
            channel = ScopeChannelChannel(self, name, scopenum)
            channels.append(channel)
            self.add_submodule(name, channel)
        channels.lock()
        self.add_submodule('channels', channels)
        self.add_parameter('average_weight',
                           label="Scope Averages",
                           set_cmd=partial(self._setter, 1, 0,
                                           'averager/weight'),
                           get_cmd=partial(self._getter,
                                           'averager/weight'),
                           vals=vals.Numbers(min_value=1))
        self.add_parameter('historylength',
                           label="History Length",
                           set_cmd=partial(self._setter, 1, 0,
                                           'historylength'),
                           get_cmd=partial(self._getter,
                                           'historylength'),
                           vals=vals.Numbers())
        self.add_parameter('singleshot',
                           label="Puts the scope into single shot mode.",
                           set_cmd=partial(self._parent._setter, 'scopes', 0,
                                           0, 'single'),
                           get_cmd=partial(self._parent._getter, 'scopes', 0,
                                           0, 'single'),
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'))
        self.add_parameter('trig_enable',
                           label="Enable triggering for scope readout",
                           set_cmd=partial(self._parent._setter, 'scopes', 0,
                                           0, 'trigenable'),
                           get_cmd=partial(self._parent._getter, 'scopes', 0,
                                           0, 'trigenable'),
                           val_mapping={'ON': 0, 'OFF': 1}, # UserManual says it's this way.
                           vals=vals.Enum('ON', 'OFF'))
        trigger_source_dict = {'Signal Input 1': 0,
                               'Current Input 1': 1,
                               'Trigger 1': 2,
                               'Trigger 2': 3,
                               'Aux Output 1': 4,
                               'Aux Output 2': 5,
                               'Aux Output 3': 6,
                               'Aux Output 4': 7,
                               'Aux Input 1': 8,
                               'Aux Input 2': 9,
                               'Osc phi Demod 2': 10,
                               'Osc phi Demod 4': 11}
        if 'DIG' in self._parent.options:
            demodulators = {'Demod 1 X': 16,
                           'Demod 2 X': 17,
                           'Demod 3 X': 18,
                           'Demod 4 X': 19,
                           'Demod 1 Y': 32,
                           'Demod 2 Y': 33,
                           'Demod 3 Y': 34,
                           'Demod 4 Y': 35,
                           'Demod 1 R': 48,
                           'Demod 2 R': 49,
                           'Demod 3 R': 50,
                           'Demod 4 R': 51,
                           'Demod 1 phi': 64,
                           'Demod 2 phi': 65,
                           'Demod 3 phi': 66,
                           'Demod 4 phi': 67,
                           'PID 1 value': 80,
                           'PID 2 value': 81,
                           'PID 3 value': 82,
                           'PID 4 value': 83,
                           'PID 1 Shift': 144,
                           'PID 2 Shift': 145,
                           'PID 3 Shift': 146,
                           'PID 4 Shift': 147}
            trigger_source_dict.update(demodulators)
        self.add_parameter('trig_signal',
                           label="Trigger signal source",
                           set_cmd=partial(self._parent._setter, 'scopes', 0,
                                           0, 'trigchannel'),
                           get_cmd=partial(self._parent._getter, 'scopes', 0,
                                           0, 'trigchannel'),
                           val_mapping=trigger_source_dict)

        slopes = {'None': 0, 'Rise': 1, 'Fall': 2, 'Both': 3}

        self.add_parameter('scope_trig_slope',
                           label="Scope's triggering slope",
                           set_cmd=partial(self._parent._setter, 'scopes', 0,
                                           0, 'trigslope'),
                           get_cmd=partial(self._parent._getter, 'scopes', 0,
                                           0, 'trigslope'),
                           val_mapping=slopes)

        # TODO: figure out how value/percent works for the trigger level
        self.add_parameter('scope_trig_level',
                           label="Scope trigger level",
                           set_cmd=partial(self._parent._setter, 'scopes', 0,
                                           1, 'triglevel'),
                           get_cmd=partial(self.parent._getter, 'scopes', 0,
                                           1, 'triglevel'),
                           unit='V',
                           vals=vals.Numbers())

        self.add_parameter('scope_trig_hystmode',
                           label="Enable triggering for scope readout",
                           set_cmd=partial(self._parent._setter, 'scopes', 0,
                                           0, 'trighysteresis/mode'),
                           get_cmd=partial(self._parent._getter, 'scopes', 0,
                                           0, 'trighysteresis/mode'),
                           val_mapping={'absolute': 0, 'relative': 1},
                           vals=vals.Enum('absolute', 'relative'))

        self.add_parameter('scope_trig_hystrelative',
                           label="Trigger hysteresis, relative value in %",
                           set_cmd=partial(self._parent._setter, 'scopes', 0,
                                           1, 'trighysteresis/relative'),
                           get_cmd=partial(self._parent._getter, 'scopes', 0,
                                           1, 'trighysteresis/relative'),
                           # val_mapping= lambda x: 0.01*x,
                           vals=vals.Numbers(0))

        self.add_parameter('scope_trig_hystabsolute',
                           label="Trigger hysteresis, absolute value",
                           set_cmd=partial(self._parent._setter, 'scopes', 0,
                                           1, 'trighysteresis/absolute'),
                           get_cmd=partial(self._parent._getter, 'scopes', 0,
                                           1, 'trighysteresis/absolute'),
                           unit='V',
                           vals=vals.Numbers(0, 20))

        triggates = {'Trigger In 1 High': 0, 'Trigger In 1 Low': 1,
                     'Trigger In 2 High': 2, 'Trigger In 2 Low': 3}
        self.add_parameter('scope_trig_gating_source',
                           label='Scope trigger gating source',
                           set_cmd=partial(self._parent._setter, 'scopes', 0, 0,
                                           'triggate/inputselect'),
                           get_cmd=partial(self._parent._getter, 'scopes', 0, 0,
                                           'triggate/inputselect'),
                           val_mapping=triggates)

        self.add_parameter('scope_trig_gating_enable',
                           label='Scope trigger gating ON/OFF',
                           set_cmd=partial(self._parent._setter, 'scopes', 0, 0,
                                           'triggate/enable'),
                           get_cmd=partial(self._parent._getter, 'scopes', 0, 0,
                                           'triggate/enable'),
                           val_mapping = {'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'))

        self.add_parameter('scope_trig_holdoffmode',
                           label="Scope trigger holdoff mode",
                           set_cmd=partial(self._parent._setter, 'scopes', 0,
                                           0, 'trigholdoffmode'),
                           get_cmd=partial(self._parent._getter, 'scopes', 0,
                                           0, 'trigholdoffmode'),
                           val_mapping={'s': 0, 'events': 1},
                           vals=vals.Enum('s', 'events'))

        #is added in the beginning because the default for holdoffmode should be 0
        #when the mode is changed, this parameter will be deleted
        self.add_parameter('scope_trig_holdoffseconds',
                           label='Scope trigger holdoff',
                           set_cmd=partial(self._setter, 0, Mode.INT,
                                           'trigholdoff'),
                           get_cmd=partial(self._parent._getter, 'scopes', 0,
                                           Mode.INT, 'trigholdoff'),
                           unit='s',
                           vals=vals.Numbers(20e-6, 10))

        self.add_parameter('scope_trig_reference',
                           label='Scope trigger reference',
                           set_cmd=partial(self._setter, 0, 1,
                                           'trigreference'),
                           get_cmd=partial(self._parent._getter, 'scopes', 0,
                                           1, 'trigreference'),
                           vals=vals.Numbers(0, 1))

        # TODO: add validation. What's the minimal/maximal delay?
        self.add_parameter('scope_trig_delay',
                           label='Scope trigger delay',
                           set_cmd=partial(self._setter, 0, 1,
                                           'trigdelay'),
                           get_cmd=partial(self._parent._getter, 'scopes', 0, 1,
                                           'trigdelay'),
                           unit='s',
                           vals=vals.Numbers())

        self.add_parameter('scope_segments',
                           label='Enable/disable segments',
                           set_cmd=partial(self._setter, 0, 0,
                                           'segments/enable'),
                           get_cmd=partial(self._parent._getter, 'scopes', 0,
                                           0, 'segments/enable'),
                           val_mapping={'OFF': 0, 'ON': 1},
                           vals=vals.Enum('ON', 'OFF'))

        self.add_parameter('scope_segments_count',
                           label='No. of segments returned by scope',
                           set_cmd=partial(self._parent._setter, 'scopes', 0, 1,
                                           'segments/count'),
                           get_cmd=partial(self._parent._getter, 'scopes', 0, 1,
                                          'segments/count'),
                           vals=vals.Ints(1, 32768),
                           get_parser=int)


        self.add_function('scope_reset_avg',
                          call_cmd=partial(self._parent.scope.set,
                                           'scopeModule/averager/restart', 1))

    def _setter(self, scopemodule, mode, setting, value):
        """
        set_cmd for all scope parameters. The value and setting are saved in
        a dictionary which is read by the Scope parameter's build_scope method
        and only then sent to the instrument.
        Args:
            scopemodule (bool): Indicates whether this is a setting of the
                scopeModule or not. 1: it is a scopeModule setting,
                0: it is not.
            mode (int): Indicates whether we are setting an int or a float.
                0: int, 1: float. NOTE: Ignored if scopemodule==1.
            setting (str): The setting, e.g. 'length'.
            value (Union[int, float, str]): The value to set.
        """
        # Because setpoints need to be built
        self.scope_correctly_built = False

        # Some parameters are linked to each other in specific ways
        # Therefore, we need special actions for setting these parameters

        #needed to convert the sampling rate into Hz
        SRtranslation = {'kHz': 1e3, 'MHz': 1e6, 'GHz': 1e9,
                         'khz': 1e3, 'Mhz': 1e6, 'Ghz': 1e9}

        def setlength(value):
            """
            Sets the length of the scope via /dev.../scopes/0/length
            and saves the value (number of samples) divided by samplingrate
            in the parameter duration
            """
            # TODO: add validation. The GUI seems to correct this value
            SR_str = self.parameters['samplingrate'].get()
            (number, unit) = SR_str.split(' ')
            SR = float(number)*SRtranslation[unit]  #sampling rate in Hz
            self.parameters['duration']._save_val(value/SR)
            self._parent.daq.setInt('/{}/scopes/0/length'.format(self._parent.device), value)

        def setduration(value):
            """
            Sets the length of the scope by mulitplying the value with the
            samplingrate in Hz and also saves this value in the parameter scope_length
            Saves the delivered value in duration
            """
            # TODO: validation? should be done in the parameter if possible
            SR_str = self.parameters['samplingrate'].get()
            (number, unit) = SR_str.split(' ')
            SR = float(number)*SRtranslation[unit]  #sampling rate in Hz
            N = int(np.round(value*SR))     #number of samples per scope shot=scope_length
            self.parameters['scope_length']._save_val(N)
            self._parent.daq.setInt('/{}/scopes/0/length'.format(self._parent.device), N)
            self.parameters['duration']._save_val(value)

        def setholdoffmode(value):
            """
            Sets the parameter scope_trig_holdoffmode and creates a parameter
            scope_trig_holdoffseconds, if it is set to 's' and a parameter
            scope_trig_holdoffevents if it is set to 'events'
            """
            if value == 's' and 'scope_trig_holdoffseconds' not in self.parameters:
                self.add_parameter('scope_trig_holdoffseconds',
                                   label='Scope trigger holdoff',
                                   set_cmd=partial(self._scope_setter, 0, Mode.INT,
                                                   'trigholdoff'),
                                   get_cmd=partial(self._getter, 'scopes', 0,
                                                   Mode.INT, 'trigholdoff'),
                                   unit='s',
                                   vals=vals.Numbers(20e-6, 10)
                                   )
                if self.parameters['scope_trig_holdoffevents']:
                    self.parameters.remove('scope_trig_holdoffevents')
                self._parent.daq.setInt('{}/scopes/0/trigholdoffmode'.format(self._parent.device), 0)
            elif value == 'events' and 'scope_trig_holdoffevent' not in self.parameters:
                self.add_parameter('scope_trig_holdoffevents',
                                   label='Scope trigger holdoff',
                                   set_cmd=partial(self._scope_setter, 0, Mode.INT,
                                                   'trigholdoffcount'),
                                   get_cmd=partial(self._getter, 'scopes', 0, Mode.INT,
                                                   'triggerholdoffcount'),
                                   vals = vals.Ints())
                if self.parameters['scope_trig_seconds']:
                    self.parameters.remove('scope_trig_seconds')
                self._parent.daq.setInt('{}/scopes/0/trigholdoffmode'.format(self._parent.device), 1)


        def setholdoffseconds(value):
            """
            Sets the trigholdoffmode to seconds and then sets the value of trigholdoff
            """
            self.parameters['scope_trig_holdoffmode'].set('s')
            self._parent.daq.setDouble('/{}/scopes/0/trigholdoff'.format(self._parent.device),
                                       value)

        def setholdoffevents(value):
            """
            Sets the triggerholdoffmode to events and then sets the value of
            trigholdoffcount
            """
            self.parameters['scope_trig_holdoffevents'].set('events')
            self._parent.daq.setInt('/{}/scopes/0/trigholdoffcount'.format(self._parent.device),
                                    value)

        def setsamplingrate(value):
            """
            Sets the samplingrate to value and also adjusts the scope_duration
            """
            # When the sample rate is changed, the number of points of the trace
            # remains unchanged and the duration changes accordingly
            newSR_str = list(self._samplingrate_codes.keys())[ value ] # value starts at 0
            (number, unit) = newSR_str.split(' ')
            newSR = float(number)*SRtranslation[unit]   # new sampling rate in Hz
            scopelength = self.parameters['length'].get()
            newduration = scopelength/newSR
            self.parameters['duration']._save_val(newduration)
            self._parent.daq.setInt('/{}/scopes/0/time'.format(self._parent.device), value)

        specialcases = {'length': setlength,
                        'duration': setduration,
                        'trigholdoffmode': setholdoffmode,
                        'trigholdoff': setholdoffseconds,
                        'trigholdoffcount': setholdoffevents,
                        'time': setsamplingrate}

        if setting in specialcases:
            specialcases[setting](value)
        else:
            # We have two different parameter types: those under
            # /scopes/0/ and those under scopeModule/
            if scopemodule:
                self._parent.scope.set('scopeModule/{}'.format(setting), value)
            elif mode == 0:
                self._parent.daq.setInt('/{}/scopes/0/{}'.format(self._parent.device,
                                                                 setting), value)
            elif mode == 1:
                self._parent.daq.setDouble('/{}/scopes/0/{}'.format(self._parent.device,
                                                                    setting), value)
        self._parent.daq.sync()

    def _getter(self, setting):
        """
        get_cmd for scopeModule parameters
        """
        # There are a few special cases
        SRtranslation = {'kHz': 1e3, 'MHz': 1e6, 'GHz': 1e9,
                         'khz': 1e3, 'Mhz': 1e6, 'Ghz': 1e9}

        def getduration():
            """
            Calculates a new value for scope_duration
            """
            SR_str = self.parameters['samplingrate'].get()
            (number, unit) = SR_str.split(' ')
            SR = float(number)*SRtranslation[unit] #sampling rate in Hz
            N = self.parameters['length'].get() #number of samplings in the scope
            duration = N/SR #duration for one sample
            return duration

        specialcases = {'duration': getduration}

        if setting in specialcases:
            value = specialcases[setting]()
        else:
            querystr = 'scopeModule/' + setting
            returndict =  self._parent.scope.get(querystr)
            # The dict may have different 'depths' depending on the parameter.
            # The depth is encoded in the setting string (number of '/')
            keys = setting.split('/')[1:]

            while keys != []:
                key = keys.pop(0)
                returndict = returndict[key]
                rawvalue = returndict

            if isinstance(rawvalue, np.ndarray) and len(rawvalue) == 1:
                value = rawvalue[0]
            elif isinstance(rawvalue, list) and len(rawvalue) == 1:
                value = rawvalue[0]
            else:
                value = rawvalue

        return value


class Scope(MultiParameter):
    """
        ** NOT COMPLETLY TESTES YET ***

    Parameter class for the ZI MFLI Scope Channel
    The .get method launches an acquisition and returns a tuple of two
    np.arrays
    FFT mode is NOT supported.
    Attributes:
        names (tuple): Tuple of strings containing the names of the sweep
          signals (to be measured)
        units (tuple): Tuple of strings containg the units of the signals
        shapes (tuple): Tuple of tuples each containing the Length of a
          signal.
        setpoints (tuple): Tuple of N copies of the sweep x-axis points,
          where N is he number of measured signals
        setpoint_names (tuple): Tuple of N identical strings with the name
          of the sweep x-axis.
    """
    def __init__(self, name, instrument, **kwargs):
        # The __init__ requires that we supply names and shapes,
        # but there is no way to know what they could be known at this time.
        # They are updated via prepare_scope.
        super().__init__(name, names=('',), shapes=((1,),), **kwargs)
        self._instrument = instrument
        self._scopeactions = []  # list of callables

    def add_post_trigger_action(self, action: Callable) -> None:
        """
        Add an action to be performed immediately after the trigger
        has been armed. The action must be a callable taking zero
        arguments
        """
        if action not in self._scopeactions:
            self._scopeactions.append(action)

    @property
    def post_trigger_actions(self) -> List[Callable]:
        """
        Access property for local variable
        """
        return self._scopeactions

    def prepare_scope(self):
        """
        Prepare the scope for a measurement. Must immediately proceed a
        measurement.
        """

        log.info('Preparing the scope')

        # A convenient reference
        #-MW- params = self._instrument.parameters
        params = self._instrument.submodules['scope_channel1'].parameters

        # First figure out what the user has asked for
        # activate Channel1 and/or Channel2
        chans = {1: (True, False), 2: (False, True), 3: (True, True)}
        channels = chans[params['scope_channels'].get()]
        # /dev4039/scopes/0/channel = 1

        sample_no = params['length'].get()
        # /dev4039/scopes/0/length = 16384

        # Find out whether segments are enabled
        if 'scope_segments' in params and params['scope_segments'].get() == 'ON':
            segs = params['scope_segments_count'].get()
        else:
            segs = 1

        inputunits = {'Signal Input 1': 'V',
                      'Signal Input 2': 'V',
                      'Trig Input 1': 'V',
                      'Trig Input 2': 'V',
                      'Aux Output 1': 'V',
                      'Aux Output 2': 'V',
                      'Aux Output 3': 'V',
                      'Aux Output 4': 'V',
                      'Aux In 1 Ch 1': 'V',
                      'Aux In 1 Ch 2': 'V',
                      'Osc phi Demod 4': '°',
                      'Osc phi Demod 8': '°',
                      'AU Cartesian 1': 'arb. un.',
                      'AU Cartesian 2': 'arb. un',
                      'AU Polar 1': 'arb. un.',
                      'AU Polar 2': 'arb. un.',
                      'Demod 1 X': 'V',
                      'Demod 1 Y': 'V',
                      'Demod 1 R': 'V',
                      'Demod 1 Phase':  '°',
                      'Demod 2 X': 'V',
                      'Demod 2 Y': 'V',
                      'Demod 2 R': 'V',
                      'Demod 2 Phase': '°',
                      'Demod 3 X': 'V',
                      'Demod 3 Y': 'V',
                      'Demod 3 R': 'V',
                      'Demod 3 Phase': '°',
                      'Demod 4 X': 'V',
                      'Demod 4 Y': 'V',
                      'Demod 4 R': 'V',
                      'Demod 4 Phase': '°',
                      }

        #TODO: what are good names? Look up if these are the same names as used
        #in ScopeChannel -> not really needed because the mapped values doesn't
        #really give more information
        inputnames = {'Signal Input 1': 'Sig. In 1',
                      'Signal Input 2': 'Sig. In 2',
                      'Trig Input 1': 'Trig. In 1',
                      'Trig Input 2': 'Trig. In 2',
                      'Aux Output 1': 'Aux. Out 1',
                      'Aux Output 2': 'Aux. Out 2',
                      'Aux Output 3': 'Aux. Out 3',
                      'Aux Output 4': 'Aux. Out 4',
                      'Aux In 1 Ch 1': 'Aux. In 1 Ch 1',
                      'Aux In 1 Ch 2': 'Aux. In 1 Ch 2',
                      'Osc phi Demod 4': 'Demod. 4 Phase',  # TODO
                      'Osc phi Demod 8': 'Demod. 8 Phase',  # TODO
                      'AU Cartesian 1': 'AU Cartesian 1',  # TODO
                      'AU Cartesian 2': 'AU Cartesian 2',  # TODO
                      'AU Polar 1': 'AU Polar 1',  # TODO
                      'AU Polar 2': 'AU Polar 2',  # TODO
                      'Demod 1 X': 'Demodulator 1 X',
                      'Demod 1 Y': 'Demodulator 1 Y',
                      'Demod 1 R': 'Demodulator 1 R',
                      'Demod 1 Phase':  'Demodulator 1 Phase',
                      'Demod 2 X': 'Demodulator 2 X',
                      'Demod 2 Y': 'Demodulator 2 Y',
                      'Demod 2 R': 'Demodulator 2 R',
                      'Demod 2 Phase': 'Demodulator 2 Phase',
                      'Demod 3 X': 'Demodulator 3 X',
                      'Demod 3 Y': 'Demodulator 3 Y',
                      'Demod 3 R': 'Demodulator 3 R',
                      'Demod 3 Phase': 'Demodulator 3 Phase',
                      'Demod 4 X': 'Demodulator 4 X',
                      'Demod 4 Y': 'Demodulator 4 Y',
                      'Demod 4 R': 'Demodulator 4 R',
                      'Demod 4 Phase': 'Demodulator 4 Phase',
                      }

        # Make the basic setpoints (the x-axis)
        duration = params['duration'].get()
        delay = params['scope_trig_delay'].get()
        #starttime = params['scope_trig_reference'].get()*0.01*duration + delay #TODO was ist das für ein Wert?
        starttime = params['scope_trig_reference'].get()*duration + delay
        stoptime = starttime + duration

        setpointlist = tuple(np.linspace(starttime, stoptime, sample_no))  # x-axis
        #setpoints for the messurement of one sample
        channel1 = self._instrument.submodules["scope_channel1"]
        #the value for input_select is mapped to a better name
        input1 = inputnames[channel1.channel().input_select()]
        unit1 = inputunits[params[input1].get()]
        channel2 = self._instrument.submodules["scope_channel2"]
        input2 = inputnames[channel2.input_select()]
        unit2 = inputunits[params[input2].get()]

        self.setpoints = ((tuple(range(segs)), (setpointlist,)*segs),)*2
        #self.setpoints = ((setpointlist,)*segs,)*2
        self.setpoint_names = (('Segments', 'Time'), ('Segments', 'Time'))
        self.inputs = (input1, input2)
        self.units = (unit1, unit2)
        self.labels = ('Scope channel 1', 'Scope channel 2')
        #number of segments per scope shot and number of samples
        self.shapes = ((segs, sample_no), (segs, sample_no))

        self._instrument.daq.sync()
        self._instrument.scope_correctly_built = True

    # def get(self):
    # qutech\qcodes\qcodes\instrument\parameter.py:247: UserWarning: Wrapping get
    # method, original get method will not be directly accessible. It is
    # recommended to define get_raw in your subclass instead.
    def get_raw(self):
        """
        Acquire data from the scope.
        Returns:
            tuple: Tuple of two n X m arrays where n is the number of segments
                and m is the number of points in the scope trace.
        Raises:
            ValueError: If the scope has not been prepared by running the
                prepare_scope function.
        """
        #used for timeout when measurements fail
        t_start = time.monotonic()
        log.info('Scope get method called')

        if not self._instrument.scope_correctly_built:
            raise RuntimeError('Scope not properly prepared. Please run '
                               'prepare_scope before measuring.')

        # A convenient reference
        params = self._instrument.parameters
        #channel1 and/or channel2 activated
        chans = {1: (True, False), 2: (False, True), 3: (True, True)}
        channels = chans[params['scope_channels'].get()]

        if params['scope_trig_holdoffmode'].get_latest() == 'events':
            #TODO implement
            raise NotImplementedError('Scope trigger holdoff in number of '
                                      'events not supported. Please specify '
                                      'holdoff in seconds.')

        #######################################################
        # The following steps SEEM to give the correct result

        # Make sure all settings have taken effect
        self._instrument.daq.sync()

        # Calculate the time needed for the measurement. We often have failed
        # measurements, so a timeout is needed.
        if 'scope_segments' in params and params['scope_segments'].get() == 'ON':
            segs = params['scope_segments_count'].get()
        else:
            segs = 1
        deadtime = params['scope_trig_holdoffseconds'].get_latest()
        # We add one second to account for latencies and random delays
        meas_time = segs*(params['scope_duration'].get()+deadtime)+1 #time the meassurement takes
        sample_no = params['scope_length'].get()

        zi_error = False
        error_counter = 0
        num_retries = 10
        timedout = False
        while (zi_error or timedout) and error_counter < num_retries:
            # one shot per trigger. This needs to be set every time
            # the scope is enabled as below using scope_runstop
            try:
                # we wrap this in try finally to ensure that
                # scope.finish is always called even if the
                # measurement is interrupted
                self._instrument.daq.setInt('/{}/scopes/0/single'.format(self._instrument.device), 1)
                #put the scope in single shot mode

                scope = self._instrument.scope #scopeModule of the Instrument
                scope.set('scopeModule/clearhistory', 1)

                # Start the scope triggering/acquiring
                # set /dev/scopes/0/enable to 1
                params['scope_runstop'].set('run')

                self._instrument.daq.sync()

                log.debug('Starting ZI scope acquisition.')
                # Start acquiring data from the scope
                scope.execute()

                # Now perform actions that may produce data, e.g. running an AWG
                for action in self._scopeactions:
                    action()

                starttime = time.time()
                timedout = False

                progress = scope.progress()
                while progress < 1:
                    log.debug('Scope progress is {}'.format(progress))
                    progress = scope.progress()
                    time.sleep(0.1)  # This while+sleep is how ZI engineers do it
                    if (time.time()-starttime) > 20*meas_time+1: # why 20*meas_time+1?
                        timedout = True
                        break
                zi_error = bool(scope.getInt('scopeModule/error'))

                # Stop the scope from running
                params['scope_runstop'].set('stop')

                if timedout or zi_error:
                    log.warning('[-] ZI scope acquisition attempt {} '
                                'failed, Timeout: {}, Error: {}, '
                                'retrying'.format(error_counter, timedout,
                                                  scope.getInt('scopeModule/error')))
                    rawdata = None
                    data = (None, None)
                    error_counter += 1
                else:
                    log.info('[+] ZI scope acquisition completed OK')
                    rawdata = scope.read()
                    if 'error' in rawdata:
                        zi_error = bool(rawdata['error'][0])
                    data = self._scopedataparser(rawdata, self._instrument.device,
                                                 sample_no, segs, channels)

                if error_counter >= num_retries:
                    log.error('[+] ZI scope acquisition failed, maximum number'
                              'of retries performed. No data returned')
                    raise RuntimeError('[+] ZI scope acquisition failed, maximum number'
                                       'of retries performed. No data returned')
            finally:
                # cleanup and make ready for next scope acquisition
                scope.finish()

        t_stop = time.monotonic()
        log.info('scope get method returning after {} s'.format(t_stop -
                                                                t_start))
        return data

    @staticmethod
    def _scopedataparser(rawdata, deviceID, scopelength, segments, channels):
        """
        Cast the scope return value dict into a tuple.
        Args:
            rawdata (dict): The return of scopeModule.read()
            deviceID (str): The device ID string of the instrument.
            scopelength (int): The length of each segment in number of samples
            segments (int): The number of segments
            channels (tuple): Tuple of two bools controlling what data to return
                (True, False) will return data for channel 1 etc.
        Returns:
            tuple: A 2-tuple of either None or np.array with dimensions
                segments x scopelength.
        """

        data = rawdata['{}'.format(deviceID)]['scopes']['0']['wave'][0][0]
        if channels[0]:
            ch1data = data['wave'][0].reshape(segments, scopelength)
        else:
            ch1data = None
        if channels[1]:
            ch2data = data['wave'][1].reshape(segments, scopelength)
        else:
            ch2data = None

        return (ch1data, ch2data)



class lockinBufferedArrayParameter(BufferedReadableArrayParameter):
    """
    This parameter is used in the qc BufferedLoop to get the result. See
    the example below at lockinBufferedParameter.
    """
    global bufferedConfig  # store the config data globally
    dbgprt = False

    def __init__(self, name: str,
                 instrument: 'Instrument',
                 **kwargs) -> None:
        """
        Creates a new lockinBufferedArrayParameter.
        Args:
            name: the internal QCoDeS name of the parameter ('buffered_result')
            instrument: the internal parent instrument
            **kwargs: more arguments passed to the base class
        """
        # Calculate the shape of the return array from the number of used
        #  channels in the sweeper output. This shape is not changable
        #  after the base class is initialized.
        shape = 1
        if hasattr(instrument, '_sweeper_signals'):
            shape = len(instrument._sweeper_signals)
            if shape < 1:
                shape = 1
        if self.dbgprt:
            print("DBG: arr-init", name, shape)
        # Initialize base class
        super().__init__(name,
                         get_buffered_cmd=self._getter,
                         config_meas_cmd=self._configMeas,
                         arm_meas_cmd=self._armMeas,
                         shape=(shape,),
                         **kwargs)
        self._instr = instrument

    def _configMeas(self, measdict={}):
        """
        Routine called with a filles measdict (return from routine _getMeas())
        to do some configurations before the measurement is started. Then this
        routine is called without an argument at the start of each buffered loop.

        For the Lock-In there is nothing to do here.
        """
        if self.dbgprt:
            print("DBG: configMeas", measdict)

    def _armMeas(self):
        """
        This routine is called after the configMeas each time the buffered loop
        goes to the next step (including the first one).
        """
        if self.dbgprt:
            print("DBG: armMeas")

    def _getter(self, name:str):
        """
        The getter function is called for each data value if the QCoDeS
        BufferedLoop will read the data.
        Parameter:
            name: the internal QCoDeS name of the parameter ('buffered_result')
        Return:
            Array of data values. The shape of the array is defined in the
            Constructor of this class.
        """
        i = bufferedConfig['index']
        if self.dbgprt:
            print("DBG: arr-getter", name, i)
        bufferedConfig['index'] = i + 1
        if i >= len(bufferedConfig['data'][0]):
            print(bufferedConfig)
            raise RuntimeError("BufferedArrayParameter: internal index too large")
        # generate an array with the data values returned from the sweep
        retval = []
        for r in range(len(bufferedConfig['data'])):
            retval.append( bufferedConfig['data'][r][i] )
        return retval

    def reset(self):
        """
        Perform a reset of the output parameter. This is called just before the
        data will be read.
        """
        if self.dbgprt:
            print("DBG: arr-reset")
        bufferedConfig['index'] = 0 # -> set the read index to zero



class lockinBufferedParameter(BufferedSweepableParameter):
    """
    This is the sweepable parameter for the QCoDeS BufferedLoop.
    Example:
        bf = zidev.buffered_freq1.sweep( freq_start, freq_stop, step=freq_step )
        l  = qc.Repetition(2).buffered_loop(bf).each(zidev.buffered_result)
        data = l.run()
    For a complete documentation see the User-Doc.
    """
    global bufferedConfig  # store the config data globally
    dbgprt = False

    def __init__(self, name: str,
                 instrument: 'Instrument',
                 parameter: str,
                 *args, **kwargs) -> None:
        """
        Creates a new BufferedSweepableParameter.
        Args:
            name: the internal QCoDeS name of the parameter
            instrument: the internal parent instrument
            parameter: the device parameter to be swept (for the sweeper channel)
            **kwargs: more arguments passed to the base class
        """
        if self.dbgprt:
            print("DBG: lockinBufferedParameter - init", name, parameter, args, kwargs)
        super().__init__(name, instrument,
                         sweep_parameter_cmd=self._sweep,
                         repeat_parameter_cmd=None, # not supported by BufferedLoop
                         send_buffer_cmd=self._send,
                         run_program_cmd=self._run,
                         get_meas_windows=self._getMeas,
                         set_cmd=self._setter, # not used but required function
                         get_cmd=self._getter, # not used but required function
                         docstring="Special parameter for BufferedLoop function"
                         )

        self._par = parameter

    def debug(self):
        """
        Helper function to print all relevant informations for this BufferedParameter
        """
        print("--- Buffered config ---")
        print("  Last data index:", bufferedConfig['index'])
        print("  Sweep channel:", bufferedConfig['param'])
        print("  Sweep values:", bufferedConfig['sweep'])
        print("  Measurement time per point:", bufferedConfig['tmeas'])
        print("  Settling time per point:", bufferedConfig['t_set'])
        print("--- Measured data ---")
        i = 0
        for d in bufferedConfig['data']:
            print("   ",self._instrument._sweeper_signals[i].split('/')[-1],d)
            i += 1
        print("--- Sweeper config ---")
        self._instrument.print_sweeper_settings()


    def _sweep(self, param:str, sweep_values:list, layer:int) -> None:
        """
        Function to define the sweep for the following BufferedLoop.
        Parameter:
            param: Name of the BufferedParameter object
            sweep_values: List of sweep values
            layer: index of nested sweeps (>0 not allowed here)
        """
        if self.dbgprt:
            print("DBG: sweep", layer, param, sweep_values)
        if layer != 0:
            raise RuntimeError("BufferedParameter("+str(param)+"): no nested sweeps allowed.")
        # setting fixed parameters for the sweeper channel
        sc = self._instrument.submodules['sweeper_channel']
        sc.param( self._par )
        sc.endless('OFF')
        sc.start( sweep_values[0] )
        sc.stop( sweep_values[-1] )
        sc.samplecount( len(sweep_values) )
        sc.loopcount( 1 )
        sc.mode( 'sequential' )
        sc.xmapping( 'linear' )
        sc.bandwidth_mode( 'fixed' )
        # Read values for the timing from the other parameters, check them and
        # store the values as meta informations in the global config data
        #avg_sam = sc.averaging_samples()   # number of measurements for one data point
        #avg_tc  = sc.averaging_tc()        # minimal averaging time constant
        #avg_tim = sc.averaging_time()      # effective measurement time per sweeper point
        set_tim = sc.settling_time()       # minimum time [sec] from setting and measure
        #set_acc = sc.settling_inaccuracy() # wait time from setting to recording sweep point
        #if avg_tim <= 0:
        #    avg_tim = 1.0 / self._instrument.submodules['demod1'].samplerate() # -> sec/sample
        #if set_tim < set_acc:
        #    set_tim = set_acc
        #if set_tim * avg_sam > avg_tim:
        #    print("***ERROR: settling", set_tim*avg_sam, "greater than averaging time", avg_tim)
        self._instrument.Sweep.build_sweep() # to calculate the sweeptime correctly
        bufferedConfig.update({'param': param,
                               'sweep': sweep_values,
                               'layer': layer,
                               'tmeas': sc.sweeptime() / len(sweep_values),
                               't_set': set_tim})

    def _send(self, layer):
        """
        Build the internal sweep settings and send them to the device.
        Parameter:
            layer: numerical index of the current layer of loops. If this is
                not zero, the behaviour is not tested, but it will be blocked
                because of error message in sweep() function
        """
        if self.dbgprt:
            print("DBG: send", layer)
        self._instrument.Sweep.build_sweep()

    def _run(self, layer):
        """
        Run the sweep and retrieve the data.
        ATTENTION: this call blocks until the sweep is finished!
        Parameter:
            layer: numerical index of the current layer of loops. If this is
                not zero, the behaviour is not tested, but it will be blocked
                because of error message in sweep() function
        """
        if self.dbgprt:
            print("DBG: run", layer)
        data = self._instrument.Sweep.get()
        bufferedConfig.update({'data' : data, # only once
                               'index': 0})
        #print(len(data), len(data[0]), data)

    def _getMeas(self) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
        """
        Calculate the measurement windows.
        Return:
            { <channelname>: ([<starttime>,...], [<duration>,...]) }
            (all times in nanoseconds!)
        """
        if self.dbgprt:
            print("DBG: getMeas")
            #print("DBG: glob cfg", bufferedConfig)
        tanf   = []
        tlen   = []
        t = 0
        t_set = bufferedConfig['t_set'] * 1e9  # in Nanoseconds!
        tmeas = bufferedConfig['tmeas'] * 1e9  # in Nanoseconds!
        for s in bufferedConfig['sweep']:
            tanf.append( t + t_set )
            tlen.append( tmeas )
            t += t_set + tmeas
        retval = {'demod': (tanf, tlen)}
        #print("DBG: measwin", retval)
        return retval

    def _setter(self, val):
        """
        Setter function. Not used but needed by the parent interface.
        """
        #print("DBG: setter", val)

    def _getter(self, *args, **kwargs):
        """
        Getter function. Not used but needed by the parent interface.
        Return:
            Fixed 0.
        """
        #print("DBG: getter", args, kwargs)
        return 0

    def reset_programs(self):
        """
        Reset of the sweep configuration.
        """
        global bufferedConfig
        if self.dbgprt:
            print("DBG: reset_programs")
        bufferedConfig = {}



class ZIMFLI(Instrument):
    """
    QCoDeS driver for ZI MFLI.

    Requires ZI Lab One software to be installed on the computer running QCoDeS.
    Furthermore, the Data Server and Web Server must be running and a connection
    between the two must be made.
    """

    def __init__(self, name: str, device_ID: str, **kwargs) -> None:
        """
        Create an instance of the instrument.

        Args:
            name (str): The internal QCoDeS name of the instrument
            device_ID (str): The device name as listed in the web server.
        """
        global realFlag

        super().__init__(name, **kwargs)

        self.device_ID = device_ID
        self.api_level = 6 # old: 5
        if realFlag:
            try:
                zisession = zhinst.utils.create_api_session(device_ID, self.api_level)
                (self.daq, self.device, self.props) = zisession
            except RuntimeError:
                realFlag = False
        if not realFlag:
            from qcodes.instrument_drivers.ZI.ZIMFLIsim import ZIMFLIsim
            self.daq    = ZIMFLIsim()
            self.device = device_ID
            self.props  = { 'devicetype': 'MFLI', 'options': 'M5F' }
            print("*** Use SIMULATION mode ***")

        # The device I used for the tests has version 18.05
        # The latest library version is 18.12
        # --> version check == False
        # print( "API Server Version Check =", zhinst.utils.api_server_version_check(self.daq) )
        # >UserWarning: There is a mismatch between the versions of the API and
        # >Data Server. The API reports version `18.12' (revision: 59107) whilst
        # >the Data Server has version `18.05' (revision 54618). See the ``Compatibility''
        # >Section in the LabOne Programming Manual for more information.

        self.daq.setDebugLevel(3)
        self.clockbase = float(self.daq.getInt('/{}/clockbase'.format(device_ID)))
        self.lastSampleSecs = 0  # in seconds
        self.lastsampletime = 0  # timestamp from device

        ########################################
        # Ask installed options to configure other classes
        self.options = self.daq.getString('/{}/features/options'.format(device_ID))
        # Options = "F5M" or "MD"

        # create (instantiate) an instance of each module we will use
        if softSweep or "MD" in self.options:
            self.sweeper = self.daq.sweep()
            self.sweeper.set('sweep/device', self.device)

        if realFlag:
            self.scope = self.daq.scopeModule()
            self.scope.subscribe('/{}/scopes/0/wave'.format(self.device))
            # Because setpoints need to be built
            self.scope_correctly_built = False

        ########################################
        # INSTRUMENT PARAMETERS

        ########################################
        # Oscillators
        self.no_oscs = 1
        if 'MD' in self.options:
            self.no_oscs = 4
        freq_max = 500000 # 500 kHz max frequency
        if 'F5M' in self.options:
            freq_max = 5e6 # 5 MHz as option
        for oscs in range(1, self.no_oscs+1):
            self.add_parameter('oscillator{}_freq'.format(oscs),
                               label='Frequency of oscillator {}'.format(oscs),
                               unit='Hz',
                               set_cmd=partial(self._setter, 'oscs',
                                                oscs-1, 1, 'freq'),
                               get_cmd=partial(self._getter, 'oscs',
                                                oscs-1, 1, 'freq'),
                               vals=vals.Numbers(0, freq_max),
                               docstring="The frequency of the oscillator. Before"
                                         " writing, the driver checks the valid range"
                                         " from 0 Hz to 500 kHz (or 5 MHz if the F5M"
                                         " option is installed)."
                               )

        ########################################
        #demodulator submodules
        demodulatorchannels = ChannelList(self, "DemodulatorChannels", DemodulatorChannel,
                                          snapshotable=False)
        # In the demodulator we have 2 channels, the second has not all
        # parameters available.
        self.demodulator_no = 2
        if 'MD' in self.options:
            # With this option we have more channels - NOT TESTED BY MW !
            self.demodulator_no = 4
        for demodchannum in range(1, self.demodulator_no+1):
            name = 'demod{}'.format(demodchannum)
            demodchannel = DemodulatorChannel(self, name, demodchannum)
            demodulatorchannels.append(demodchannel)
            self.add_submodule(name, demodchannel)
        demodulatorchannels.lock()
        self.add_submodule('demodulator_channels', demodulatorchannels)

        ########################################
        #signal input submodules
        signalinputchannels = ChannelList(self, "SignalInputChannels", SignalInputChannel,
                                          snapshotable=False)
        self.signalinput_no = 1
        for sigin in range(1, self.signalinput_no+1):
            name = 'signal_in{}'.format(sigin)
            siginchannel = SignalInputChannel(self, name, sigin)
            signalinputchannels.append(siginchannel)
            self.add_submodule(name, siginchannel)
        signalinputchannels.lock()
        self.add_submodule('signal_input_channels', signalinputchannels)

        # current input submodules
        currentinputchannels = ChannelList(self, "CurrentInputChannels", CurrentInputChannel,
                                           snapshotable=False)
        self.currentinput_no = 1
        for currin in range(1, self.currentinput_no+1):
            name = 'current_in{}'.format(currin)
            currinchannel = CurrentInputChannel(self, name, currin)
            currentinputchannels.append(currinchannel)
            self.add_submodule(name, currinchannel)
        currentinputchannels.lock()
        self.add_submodule('current_input_channels', currentinputchannels)

        #auxiliary input submodules
        auxinputchannels = ChannelList(self, "AUXInputChannels", AUXInputChannel,
                                       snapshotable=False)
        self.auxinput_no = 1
        # Via demods/1/sample ['auxin0'] and ['auxin1'] two auxiliary inputs are accessible,
        # but via auxin-class is only the first one available.
        for auxinchannum in range(1, self.auxinput_no+1):
            name = 'aux_in{}'.format(auxinchannum)
            auxinchannel = AUXInputChannel(self, name, auxinchannum)
            auxinputchannels.append(auxinchannel)
            self.add_submodule(name, auxinchannel)
        auxinputchannels.lock()
        self.add_submodule('aux_in_channels', auxinputchannels)

        #external reference submodules
        extrefchannels = ChannelList(self, "ExternalReferenceChannels",
                                     ExternalReferenceChannel, snapshotable=False)
        self.extref_no = 1
        for extrefchannum in range(1, self.extref_no+1):
            name = 'extref{}'.format(extrefchannum)
            extrefchannel = ExternalReferenceChannel(self, name, extrefchannum)
            extrefchannels.append(extrefchannel)
            self.add_submodule(name, extrefchannel)
        extrefchannels.lock()
        self.add_submodule('extref_channels', extrefchannels)

        ########################################
        # signal output submodules
        signaloutputchannels = ChannelList(self, "SignalOutputChannels", SignalOutputChannel,
                                           snapshotable=False)
        self.signalout_no = 1
        for sigout in range(1, self.signalout_no+1):
            name = 'signal_out{}'.format(sigout)
            sigoutchannel = SignalOutputChannel(self, name, sigout)
            signaloutputchannels.append(sigoutchannel)
            self.add_submodule(name, sigoutchannel)
        signaloutputchannels.lock()
        self.add_submodule('signal_output_channels', signaloutputchannels)

        #auxiliary output submodules
        auxoutputchannels = ChannelList(self, "AUXOutputChannels", AUXOutputChannel,
                                        snapshotable=False)
        self.auxout_no = 4
        for auxchannum in range(1, self.auxout_no+1):
            name = 'aux_out{}'.format(auxchannum)
            auxchannel = AUXOutputChannel(self, name, auxchannum)
            auxoutputchannels.append(auxchannel)
            self.add_submodule(name, auxchannel)
        auxoutputchannels.lock()
        self.add_submodule('aux_out_channels', auxoutputchannels)

        ########################################
        # trigger input submodules
        triggerinputchannels = ChannelList(self, "TriggerInputChannels", TriggerInputChannel,
                                           snapshotable=False)
        self.trigger_no = 2
        for triggerin in range(1, self.trigger_no+1):
            name = 'trigger_in{}'.format(triggerin)
            triggerinchannel = TriggerInputChannel(self, name, triggerin)
            triggerinputchannels.append(triggerinchannel)
            self.add_submodule(name, triggerinchannel)
        triggerinputchannels.lock()
        self.add_submodule('trigger_in_channels', triggerinputchannels)

        # trigger output submodules
        triggeroutputchannels = ChannelList(self, "TriggerOutputChannels", TriggerOutputChannel,
                                            snapshotable=False)
        for triggerout in range(1,3):
            name = 'trigger_out{}'.format(triggerout)
            triggeroutchannel = TriggerOutputChannel(self, name, triggerout)
            triggeroutputchannels.append(triggeroutchannel)
            self.add_submodule(name, triggeroutchannel)
        triggeroutputchannels.lock()
        self.add_submodule('trigger_out_channels', triggeroutputchannels)

        ########################################
        # digitial input/output submodule
        diochannel = DIOChannel(self, 'dio', 1)
        self.add_submodule('dio', diochannel)

        # multi device sync submodule
        mdschannel = MDSChannel(self, "mds")
        self.add_submodule('mds', mdschannel)

        if softSweep or "MD" in self.options:
            ########################################
            # SWEEPER PARAMETERS
            sweeperchannel = SweeperChannel(self, 'sweeper_channel')
            self.add_submodule('sweeper_channel', sweeperchannel)
            ########################################
            # THE SWEEP ITSELF
            self.add_parameter('Sweep',
                               parameter_class=Sweep,
                               docstring="Sweeper class"
                               )

            # A "manual" parameter: a list of the signals for the sweeper
            # to subscribe to
            self._sweeper_signals = [] # type: List[str]

            # This is the dictionary keeping track of the sweeper settings
            # These are the default settings
            self._sweepdict = {'start': 1e6,
                               'stop': 10e6,
                               'samplecount': 25,
                               'bandwidthcontrol': 1,  # fixed mode
                               'bandwidth': 50,
                               'gridnode': 'oscs/0/freq',
                               'scan': 0,  # sequential scan
                               'order': 1,
                               'settling/time': 1e-6,
                               'settling/inaccuracy': 10e-3,
                               'averaging/sample': 25,
                               'averaging/tc': 100e-3,
                               'xmapping': 0,  # linear
                               }
            # Set up the sweeper with the above settings
            self.Sweep.build_sweep()

            # Define all sweepable parameter as BufferedParameter. They have all
            # the same class and the parameter string denotes the sweepable param.
            self.add_parameter('buffered_freq1',
                               parameter_class=lockinBufferedParameter,
                               parameter='Osc 1 Frequency')
            self.add_parameter('buffered_auxout1',
                               parameter_class=lockinBufferedParameter,
                               parameter='Aux Out 1 Offset')
            self.add_parameter('buffered_auxout2',
                               parameter_class=lockinBufferedParameter,
                               parameter='Aux Out 2 Offset')
            self.add_parameter('buffered_auxout3',
                               parameter_class=lockinBufferedParameter,
                               parameter='Aux Out 3 Offset')
            self.add_parameter('buffered_auxout4',
                               parameter_class=lockinBufferedParameter,
                               parameter='Aux Out 4 Offset')
            self.add_parameter('buffered_phase1',
                               parameter_class=lockinBufferedParameter,
                               parameter='Demod 1 Phase Shift')
            self.add_parameter('buffered_phase2',
                               parameter_class=lockinBufferedParameter,
                               parameter='Demod 2 Phase Shift')
            self.add_parameter('buffered_out1ampl2',
                               parameter_class=lockinBufferedParameter,
                               parameter='Output 1 Amplitude 2')
            self.add_parameter('buffered_out1off',
                               parameter_class=lockinBufferedParameter,
                               parameter='Output 1 Offset')
            if 'MD' in self.options:
                self.add_parameter('buffered_phase3',
                                   parameter_class=lockinBufferedParameter,
                                   parameter='Demod 3 Phase Shift')
                self.add_parameter('buffered_phase4',
                                   parameter_class=lockinBufferedParameter,
                                   parameter='Demod 4 Phase Shift')
                self.add_parameter('buffered_freq2',
                                   parameter_class=lockinBufferedParameter,
                                   parameter='Osc 2 Frequency')
                self.add_parameter('buffered_out1ampl4',
                                   parameter_class=lockinBufferedParameter,
                                   parameter='Output 1 Amplitude 4')
                self.add_parameter('buffered_out2ampl8',
                                   parameter_class=lockinBufferedParameter,
                                   parameter='Output 2 Amplitude 8')
                self.add_parameter('buffered_out2off',
                                   parameter_class=lockinBufferedParameter,
                                   parameter='Output 2 Offset')


        ########################################
        # scope submodule for the settings of the scope
        if realFlag:
            scopechannels = ChannelList(self, "ScopeChannels", ScopeChannel,
                                        snapshotable=False)
            self.scopechan_no = 2
            for scchan in range(1, self.scopechan_no+1):
                name = 'scope_channel{}'.format(scchan)
                scopechan = ScopeChannel(self, name)
                scopechannels.append(scopechan)
                self.add_submodule(name, scopechan)
            scopechannels.lock()
            self.add_submodule('scopechannels_channels', scopechannels)

            # THE SCOPE ITSELF
            self.add_parameter('Scope',
                               parameter_class=Scope,
                               )


    def _setter(self, module, number, mode, setting, value):
        """
        General function to set/send settings to the device.

        The module (e.g demodulator, input, output,..) number is counted in a
        zero indexed fashion.

        Args:
            module (str): The module (eg. demodulator, input, output, ..)
                to set.
            number (int): Module's index
            mode (bool): Indicating whether we are setting an int or double
            setting (str): The module's setting to set.
            value (int/double): The value to set.
        """
        setstr = '/{}/{}/{}/{}'.format(self.device, module, number, setting)
        if mode == 0:
            self.daq.setInt(setstr, value)
        if mode == 1:
            self.daq.setDouble(setstr, value)


    def _getter(self, module: str, number: int,
                mode: int, setting: str) -> Union[float, int, str, dict]:
        """
        General get function for generic parameters. Note that some parameters
        use more specialised setter/getters.

        The module (e.g demodulator, input, output,..) number is counted in a
        zero indexed fashion.

        Args:
            module (str): The module (eg. demodulator, input, output, ..)
                we want to know the value of.
            number (int): Module's index
            mode (int): Indicating whether we are asking for an int or double.
                0: Int, 1: double, 2: Sample
            setting (str): The module's setting to set.
        returns:
            inquered value

        """
        querystr = '/{}/{}/{}/{}'.format(self.device, module, number, setting)
        log.debug("getting %s", querystr)
        if mode == 0:
            value = self.daq.getInt(querystr)
        elif mode == 1:
            value = self.daq.getDouble(querystr)
        elif mode == 2:
            value = self.daq.getSample(querystr)
            self.lastsampletime = value['timestamp'][0]
            self.lastSampleSecs = time.time()
            value['R']   = np.abs(value['x'] + 1j * value['y'])
            value['phi'] = np.angle(value['x'] + 1j * value['y'], deg=True)
        else:
            raise RuntimeError("Invalid mode supplied")
        # Weird exception, samplingrate returns a string
        return value


    def _list_nodes(self, node):
        """
        Returns a list with all nodes in the sub-tree below the specified node.

        Args:
            node (str): Module of which you want to know the parameters.
        return:
            list of sub-nodes
        """
        node_list = self.daq.getList('/{}/{}/'.format(self.device, node), 0 )

        return node_list


    def add_signal_to_sweeper(self, demodulator, attribute):
        """
        Add a signal to the output of the sweeper. When the sweeper sweeps,
        the signals added to the sweeper are returned.

        Args:
            demodulator (int): A number from 1-8 choosing the demodulator.
              The same demodulator can be chosen several times for
              different attributes, e.g. demod1 X, demod1 phase
            attribute (str): The attribute to record, e.g. phase or Y

        Raises:
            ValueError: if a demodulator outside the allowed range is
              selected
            ValueError: if an attribute not in the list of allowed attributes
              is selected
        """
        if not softSweep and not "MD" in self.options:
            raise RuntimeError('no MD option installed')

        # List of all possible <username>
        valid_attributes = ['X', 'Y', 'R', 'phase',  # the sample measurements
                            'Xrms', 'Yrms', 'Rrms',  # the square values
                            'phasePwr',
                            'Freq', 'FreqPwr',       # Frequency and its square
                            'In1', 'In2',            # Aux-Inputs
                            'In1Pwr', 'In2Pwr'       # and the squares
                            ]
        # Other values possible but I see no need for them:
        #  bandwidth, settling, tc, tcmeas, grid, count,
        #  auxin0stddev, auxin1stddev, frequencystddev, phasestddev,
        #  rstddev, xstddev, ystddev, nexttimestamp, settimestamp

        # Validation
        if demodulator not in range(1, 9):
            raise ValueError('Can not select demodulator' +
                             ' {}. Only '.format(demodulator) +
                             'demodulators 1-8 are available.')
        if attribute not in valid_attributes:
            raise ValueError('Can not select attribute:'+
                             '{}. Only the following attributes are' +
                             ' available: ' +
                             ('{}, '*len(valid_attributes)).format(*valid_attributes))

        # internally, we use strings very similar to the ones used by the
        # instrument, but with the attribute added, e.g.
        # '/dev2189/demods/0/sample/X' means X of demodulator 1.
        signalstring = ('/' + self.device +
                        '/demods/{}/sample/{}'.format(demodulator-1,
                                                      attribute))
        if signalstring not in self._sweeper_signals:
            self._sweeper_signals.append(signalstring)

        self.parameters['buffered_result'] = \
            lockinBufferedArrayParameter('buffered_result',self)


    def remove_signal_from_sweeper(self, demodulator, attribute):
        """
        Remove a signal from the output of the sweeper. If the signal
        has not previously been added, a warning is logged.

        Args:
            demodulator (int): A number from 1-8 choosing the demodulator.
              The same demodulator can be chosen several times for
              different attributes, e.g. demod1 X, demod1 phase
            attribute (str): The attribute to record, e.g. phase or Y
        """
        if not softSweep and not "MD" in self.options:
            raise RuntimeError('no MD option installed')

        signalstring = ('/' + self.device +
                        '/demods/{}/sample/{}'.format(demodulator-1,
                                                      attribute))
        if signalstring not in self._sweeper_signals:
            log.warning('Can not remove signal with {} of'.format(attribute) +
                        ' demodulator {}, since it was'.format(demodulator) +
                        ' not previously added.')
        else:
            self._sweeper_signals.remove(signalstring)
            self.parameters['buffered_result'] = \
                lockinBufferedArrayParameter('buffered_result',self)


    def print_sweeper_settings(self):
        """
        Pretty-print the current settings of the sweeper.
        If Sweep.build_sweep and Sweep.get are called, the sweep described
        here will be performed.
        """
        if not softSweep and not "MD" in self.options:
            raise RuntimeError('no MD option installed')

        swchan = self.submodules['sweeper_channel']

        print('ACQUISITION')
        toprint = ['bandwidth_mode', 'bandwidth', 'order',
                   'averaging_samples', 'averaging_time',
                   'settling_time', 'settling_tc']
        for paramname in toprint:
            parameter = swchan.parameters[paramname]
            print('    {}: {} {}'.format(parameter.label, parameter.get(),
                                         parameter.unit))

        print('HORIZONTAL')
        toprint = ['start', 'stop', 'units', 'samplecount', 'param', 'mode',
                   'sweeper_timeout']
        for paramname in toprint:
            parameter = swchan.parameters[paramname]
            print('    {}: {}'.format(parameter.label, parameter.get()))

        print('VERTICAL')
        count = 1
        for signal in self._sweeper_signals:
            (_, _, _, dm, _, attr) = signal.split('/')
            fmt = (count, int(dm)+1, attr)
            print('    Signal {}: Demodulator {}: {}'.format(*fmt))
            count += 1

        features = ['timeconstant', 'order', 'samplerate']
        print('DEMODULATORS')
        demods = []
        for signal in self._sweeper_signals:
            demods.append(int(signal.split('/')[3]))
        demods = set(demods)
        for dm in demods:
            for feat in features:
                demod = self.submodules['demod{:d}'.format(dm+1)]
                parameter = demod.parameters[feat]
                fmt = (dm+1, parameter.label, parameter.get(), parameter.unit)
                print('    Demodulator {}: {}: {:.6f} {}'.format(*fmt))
        print('META')
        swptime = swchan.parameters['sweeptime'].get()
        if swptime is not None:
            print('    Expected sweep time: {:.1f} s'.format(swptime))
        else:
            print('    Expected sweep time: N/A in auto mode')
        print('    Sweep timeout: {} s'.format(swchan.sweeper_timeout()))
        ready = self.sweep_correctly_built
        print('    Sweep built and ready to execute: {}'.format(ready))


    def close(self):
        """
        Override of the base class' close function
        """
        if realFlag:
            self.scope.unsubscribe('/{}/scopes/0/wave'.format(self.device))
            self.scope.clear()
        if softSweep or "MD" in self.options:
            self.sweeper.clear()
        self.daq.disconnect()
        super().close()


    def version(self):
        """
        Read all possible version informations and returns them as a dict
        """
        retval = dict()
        # GitTag is removed because it is not clear if the script is started
        # at a directory just above the Qcodes directory in which the git
        # informations are available
        #if platform.system() == "Windows":
        #    retval['GitTag'] = os.popen("cd Qcodes & git describe --tag").read().strip()
        #else:
        #    retval['GitTag'] = os.popen("cd Qcodes ; git describe --tag").read().strip()
        dev = '/{}/'.format(self.device)
        retval['DevType'   ] = self.daq.getString(dev+'FEATURES/DEVTYPE')
        retval['Options'   ] = self.daq.getString(dev+'FEATURES/OPTIONS').strip()
        retval['Serial'    ] = self.daq.getString(dev+'FEATURES/SERIAL')
        if realFlag:
            tdev = self.daq.getInt(dev+'STATUS/TIME')
            tsys = zhinst.utils.systemtime_to_datetime(tdev)
            retval['DevTime'   ] = tsys.strftime('%d.%m.%Y %H:%M:%S.%f')
        else:
            retval['DevTime'   ] = time.strftime('%d.%m.%Y %H:%M:%S')
        retval['Owner'     ] = self.daq.getString(dev+'SYSTEM/OWNER')
        retval['FPGARev'   ] = self.daq.getInt(dev+'SYSTEM/FPGAREVISION')
        retval['DevFWRev'  ] = self.daq.getInt(dev+'SYSTEM/FWREVISION')
        retval['BoardRev1' ] = self.daq.getString(dev+'SYSTEM/BOARDREVISIONS/0')
        retval['Copyright' ] = self.daq.getString('/ZI/ABOUT/COPYRIGHT')
        retval['Dataserver'] = self.daq.getString('/ZI/ABOUT/DATASERVER')
        retval['ZI_FWRev'  ] = self.daq.getInt('/ZI/ABOUT/FWREVISION')
        retval['ZIRevision'] = self.daq.getInt('/ZI/ABOUT/REVISION')
        retval['Version'   ] = self.daq.getString('/ZI/ABOUT/VERSION')
        return retval


    def bufferedReader(self, demod_index, total_time, dolog=False, copyFreq=False,
                       copyPhase=False, copyDIO=False, copyTrigger=False, copyAuxin=False):
        """
        Read the sample informations from the given demodulator and returns
        the dict.
        Parameters:
            demod_index = index of demodulator channel (1,2)
            total_time  = number of seconds for measurement, this time the function
                          is blocking
            dolog       = Flag if this function print some informations during
                          running (elapsed time and data length)
                * The following flags can be set to False (default) to preserve memory usage *
            copyFreq    = Flag to copy the frequency data
            copyPhase   = Flag to copy the phase data
            copyDIO     = Flag to copy the digital I/O data
            copyTrigger = Flag to copy the trigger data
            copyAuxin   = Flag to copy both auxin port data
        Return:
            dict() with dict_keys(['timestamp', 'x', 'y', 'frequency', 'phase', 'dio', 'trigger',
                    'auxin0', 'auxin1', 'time', 'R', 'phi'])
            The filed 'time' has the fields:
                'trigger': 0,
                'dataloss': False,
                'blockloss': False,
                'ratechange': False,
                'invalidtimestamp': False,
                'mindelta': 0,
                'clockbase': 60000000.0  - this is used to calculate the correct time from the timestamps
        """
        if 'demod{}'.format(demod_index) not in self.submodules:
            raise RuntimeError('bufferedReader: invalid demodulator index given')
        if total_time <= 0:
            raise RuntimeError('bufferedReader: invalid total time given')

        # Subscribe to the demodulator's sample node path.
        path = '/%s/demods/%d/sample' % (self.device, demod_index-1)
        if dolog:
            print("bufferedReader: subscription path =", path)
        self.daq.subscribe(path)

        # Let's check how many seconds of demodulator data were returned by poll.
        # First, get the sampling rate of the device's ADCs, the device clockbase...
        #clockbase = float(self.daq.getInt('/%s/clockbase' % self.device))
        if dolog:
            print("bufferedReader: clockbase =", self.clockbase)

        # Sleep for demonstration purposes: Allow data to accumulate in the data
        # server's buffers for one second: poll() will not only return the data
        # accumulated during the specified poll_length, but also for data
        # accumulated since the subscribe() or the previous poll.
        sleep_length = 1.0
        if sleep_length > total_time:
            sleep_length = total_time / 3
        time.sleep(sleep_length)

        # Poll the subscribed data from the data server. Poll will block and record
        # for poll_length seconds.
        poll_length = 0.1  # [s]
        poll_timeout = 500  # [ms]
        poll_flags = 0
        poll_return_flat_dict = True

        data = self.daq.poll(poll_length, poll_timeout, poll_flags, poll_return_flat_dict)

        while True:
            tmp = self.daq.poll(poll_length, poll_timeout, poll_flags, poll_return_flat_dict)
            data[path]['timestamp'] = np.append(data[path]['timestamp'], tmp[path]['timestamp'])
            data[path]['x']         = np.append(data[path]['x'],         tmp[path]['x'])
            data[path]['y']         = np.append(data[path]['y'],         tmp[path]['y'])
            if copyFreq:
                data[path]['frequency'] = np.append(data[path]['frequency'], tmp[path]['frequency'])
            if copyPhase:
                data[path]['phase']     = np.append(data[path]['phase'],     tmp[path]['phase'])
            if copyDIO:
                data[path]['dio']       = np.append(data[path]['dio'],       tmp[path]['dio'])
            if copyTrigger:
                data[path]['trigger']   = np.append(data[path]['trigger'],   tmp[path]['trigger'])
            if copyAuxin:
                data[path]['auxin0']    = np.append(data[path]['auxin0'],    tmp[path]['auxin0'])
                data[path]['auxin1']    = np.append(data[path]['auxin1'],    tmp[path]['auxin1'])
            # 'time': {'trigger': 0, 'dataloss': False, 'blockloss': False, 'ratechange': False, 'invalidtimestamp': False, 'mindelta': 0}}}
            time_elapsed = (data[path]['timestamp'][-1] - data[path]['timestamp'][0])/self.clockbase
            if dolog:
                print('bufferedReader: time={0:6.2f}s,  data length={1}'.format(time_elapsed,
                      len(data[path]['x'])))
            if time_elapsed >= total_time:
                break
            time.sleep(sleep_length)

        # Unsubscribe from all paths.
        self.daq.unsubscribe('*')

        # Check the dictionary returned is non-empty
        assert data, "poll() returned an empty data dictionary, did you subscribe to any paths?"

        # Copy the data to remove the path-key and remove all not copied arrays
        sample = data[path]
        if not copyFreq:
            sample.pop("frequency")
        if not copyPhase:
            sample.pop("phase")
        if not copyDIO:
            sample.pop("dio")
        if not copyTrigger:
            sample.pop("trigger")
        if not copyAuxin:
            sample.pop("auxin0")
            sample.pop("auxin1")
        # Calculate the demodulator's magnitude and phase and add them to the dict.
        sample['R'] = np.abs(sample['x'] + 1j*sample['y'])
        sample['phi'] = np.angle(sample['x'] + 1j*sample['y'])
        sample['time']['clockbase'] = self.clockbase

        return sample


    def getClockbase(self):
        """
        Returns the clockbase factor to calculate the time in seconds from the device timestamp
        """
        return self.clockbase


    def getOptions(self):
        """
        Returns the option string read from the device at startup.
        """
        return self.options


    def getLastSampleTimestamp(self):
        """
        Get time of last sample request.
        Returns an array with three values:
            [0] = in seconds
            [1] = in device timestamp
            [2] = device timestamp in seconds
        """
        return [self.lastSampleSecs,
                self.lastsampletime,
                self.lastsampletime/self.clockbase]


    def possibleValues(self, d: dict) -> str:
        """
        Helper function to print a list of all possible values from a command dict.
        This is used in the docstring argument to print the current values.
        """
        return " Possible values are: '"+"', '".join(list(d.keys()))+"'"
