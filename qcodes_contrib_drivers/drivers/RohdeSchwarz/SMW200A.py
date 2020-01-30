# -*- coding: utf-8 -*-
"""
File: SMW200A.py
Date: Mai / Jun 2019
Author: Michael Wagener, ZEA-2, m.wagener@fz-juelich.de
        Sarah Fleitmann, ZEA-2, s.fleitmann@fz-juelich.de
Purpose: QCoDeS-Driver for Rohde&Schwarz Vector Signal Generator RS_SMW200A
"""


import logging
from functools import partial
import time

# real mode:
from qcodes import VisaInstrument
# simulation mode:
#from qcodes.instrument_drivers.rohde_schwarz.SMW200Asim import MockVisa

## do not forget to change the main class accordingly:
## real  -> class RohdeSchwarz_SMW200A(VisaInstrument):
## simul -> class RohdeSchwarz_SMW200A(MockVisa):

from qcodes.instrument.channel import InstrumentChannel, ChannelList
from qcodes import validators as vals

log = logging.getLogger(__name__)



class IQChannel(InstrumentChannel): # doc done ********************************
    """
    The I/Q channels are the analog output channels of the device.
    Parameters:
        state: Actives/deactives the I/Q output. Values are 'ON' and 'OFF'.
        type: Sets the type of the analog signal. Values are 'SING' (single) and
            'DIFF' (differential, only available with option SMW-K16)
        mode: Determines the mode for setting the output parameters. Values are
            'FIX': Locks the I/Q output settings
            'VAR': Unlocks the settings (only available with option SMW-K16)
        level: Sets the off-load voltage Vp of the analog I/Q signal output.
            Values are in range 0.04V to 4V for option SMW-B10 and in range 0.04V
            to 2V for option SMW-B9. The value range is adjusted so that the maximum
            overall output voltage does not exceed 4V. Only settable when mode has
            the value 'VAR'.
        coupling: Couples the bias setting of the I and Q signal components.
            Values are 'ON and 'OFF'.
        i_bias: Specifies the amplifier bias of the I component. The value range
            is adjusted so that the maximum overall output voltage does not
            exceed 4V. Is only settable, if the mode parameter has the value 'VAR'.
        q_bias: Specifies the amplifier bias of the Q component. The value range
            is adjusted so that the maximum overall output voltage does not
            exceed 4V. Is only settable, if the mode parameter has the value 'VAR'.
        i_offset: Sets an offset between the inverting and non-inverting input
            of the differential analog I/Q output signal for the I component.
            The value range is adjusted so that the maximum overall output voltage
            does not exceed 4V. Is only settable, if parameter mode has the value
            'VAR'.
        q_offset: Sets an offset between the inverting and non-inverting input
            of the differential analog I/Q output signal for the Q component.
            The value range is adjusted so that the maximum overall output voltage
            does not exceed 4V. Is only settable, if parameter mode has the value
            'VAR'.
    """
    def __init__(self, parent: 'RohdeSchwarz_SMW200A', name: str, hwchan: int):
        """
        Creates a new IQChannel
        Args:
            parent: the parent instrument of this channel
            name  : the internal QCoDeS name of this channel
            hwchan: the internal number of the hardware channel used in the communication
        """
        self.hwchan = hwchan
        super().__init__(parent, name)

        self.add_parameter('state',
                           label='State',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'IQ:OUTP:ANAL:STAT {}',
                           get_cmd='SOUR{}:'.format(self.hwchan)+'IQ:OUTP:ANAL:STAT?',
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="Actives/deactives the I/Q output. Values are 'ON' and 'OFF'.")

        if 'SMW-K16' in self._parent.options:
            type_validator = vals.Enum('SING', 'DIFF')
            mode_validator = vals.Enum('FIX', 'VAR')
        else:
            type_validator = vals.Enum('SING')
            mode_validator = vals.Enum('FIX')
        self.add_parameter('type',
                           label='Type',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'IQ:OUTP:ANAL:TYPE {}',
                           get_cmd='SOUR{}:'.format(self.hwchan)+'IQ:OUTP:ANAL:TYPE?',
                           vals=type_validator,
                           docstring="Sets the type of the analog signal. Values are"
                                     " 'SING' (single) and 'DIFF' (differential, only"
                                     " available with option SMW-K16)")

        self.add_parameter('mode',
                           label='Mode',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'IQ:OUTP:ANAL:MODE {}',
                           get_cmd='SOUR{}:'.format(self.hwchan)+'IQ:OUTP:ANAL:MODE?',
                           vals=mode_validator,
                           docstring="""
                           Determines the mode for setting the output parameters. Values are:
                               'FIX': Locks the I/Q output settings
                               'VAR': Unlocks the settings (only available with option SMW-K16)
                           """)

        if 'SMW-B10' in self._parent.options:
            level_validator = vals.Numbers(0.04, 4)
        else: #option SMW-B9
            level_validator = vals.Numbers(0.04, 2)
        self.add_parameter('level',
                           label='Level',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'IQ:OUTP:LEV {}' \
                                   if self.mode() == 'VAR' else False,
                           get_cmd='SOUR{}:'.format(self.hwchan)+'IQ:OUTP:LEV?',
                           get_parser=float,
                           vals=level_validator,
                           unit='V',
                           docstring="Sets the off-load voltage Vp of the analog I/Q signal"
                                     " output. Values are in range 0.04V to 4V for option"
                                     " SMW-B10 and in range 0.04V to 2V for option SMW-B9."
                                     " The value range is adjusted so that the maximum"
                                     " overall output voltage does not exceed 4V. Only"
                                     " settable when mode has the value 'VAR'.")

        self.add_parameter('coupling',
                           label='Coupling',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'IQ:OUTP:ANAL:BIAS:COUP:STAT {}',
                           get_cmd='SOUR{}:'.format(self.hwchan)+'IQ:OUTP:ANAL:BIAS:COUP:STAT?',
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="Couples the bias setting of the I and Q signal"
                                     " components. Values are 'ON and 'OFF'.")

        if 'SMW-B10' in self._parent.options:
            lower = -4+self.level()/2+self.i_offset()/2
            upper = 4-self.level()/2-self.i_offset()/2
            bias_validator = vals.Numbers(lower, upper)
        else: #option SMW-B9
            bias_validator = vals.Numbers(-0.2, 2.5)
        self.add_parameter('i_bias',
                           label='I bias',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'IQ:OUTP:ANAL:BIAS:I {}' \
                                   if self.mode() == 'VAR' else False,
                           get_cmd='SOUR{}:'.format(self.hwchan)+'IQ:OUTP:ANAL:BIAS:I?',
                           get_parser=float,
                           vals=bias_validator,
                           unit='V',
                           docstring="Specifies the amplifier bias of the I component."
                                     " The value range is adjusted so that the maximum"
                                     " overall output voltage does not exceed 4V. Is only"
                                     " settable, if the mode parameter has the value 'VAR'.")

        if 'SMW-B10' in self._parent.options:
            lower = -4+self.level()/2+self.q_offset()/2
            upper = 4-self.level()/2-self.q_offset()/2
            bias_validator = vals.Numbers(lower, upper)
        else: #option SMW-B9
            bias_validator = vals.Numbers(-0.2, 2.5)
        self.add_parameter('q_bias',
                           label='Q bias',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'IQ:OUTP:ANAL:BIAS:Q {}' \
                                   if self.mode() == 'VAR' else False,
                           get_cmd='SOUR{}:'.format(self.hwchan)+'IQ:OUTP:ANAL:BIAS:Q?',
                           get_parser=float,
                           vals=bias_validator,
                           unit='V',
                           docstring="Specifies the amplifier bias of the Q component."
                                     " The value range is adjusted so that the maximum"
                                     " overall output voltage does not exceed 4V. Is only"
                                     " settable, if the mode parameter has the value 'VAR'.")

        if 'SMW-B10' in self._parent.options:
            lower = -4+self.level()/2+self.i_bias()/2
            upper = 4-self.level()/2-self.i_bias()/2
            offset_validator = vals.Numbers(lower, upper)
        else: #option SMW-B9
            lower = -2+self.level()
            upper = 2-self.level()
            offset_validator = vals.Numbers(lower, upper)
        self.add_parameter('i_offset',
                           label='I offset',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'IQ:OUTP:ANAL:OFFS:I {}' \
                                   if self.mode() == 'VAR' else False,
                           get_cmd='SOUR{}:'.format(self.hwchan)+'IQ:OUTP:ANAL:OFFS:I?',
                           get_parser=float,
                           vals=offset_validator,
                           unit='V',
                           docstring="Sets an offset between the inverting and non-inverting"
                                     " input of the differential analog I/Q output signal"
                                     " for the I component."
                                     " The value range is adjusted so that the maximum"
                                     " overall output voltage does not exceed 4V. Is only"
                                     " settable, if the mode parameter has the value 'VAR'.")

        if 'SMW-B10' in self._parent.options:
            lower = -4+self.level()/2+self.q_bias()/2
            upper = 4-self.level()/2-self.q_bias()/2
            offset_validator = vals.Numbers(lower, upper)
        else: #option SMW-B9
            lower = -2+self.level()
            upper = 2-self.level()
            offset_validator = vals.Numbers(lower, upper)
        self.add_parameter('q_offset',
                           label='Q offset',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'IQ:OUTP:ANAL:OFFS:Q {}' \
                                   if self.mode() == 'VAR' else False,
                           get_cmd='SOUR{}:'.format(self.hwchan)+'IQ:OUTP:ANAL:OFFS:Q?',
                           get_parser=float,
                           vals=offset_validator,
                           unit='V',
                           docstring="Sets an offset between the inverting and non-inverting"
                                     " input of the differential analog I/Q output signal"
                                     " for the Q component."
                                     " The value range is adjusted so that the maximum"
                                     " overall output voltage does not exceed 4V. Is only"
                                     " settable, if the mode parameter has the value 'VAR'.")

        # TODO: setter methods for the last 4 parameters
        # --> they have dynamic validators


class IQModulation(InstrumentChannel): # doc done *****************************
    """
    Combines all the parameters concerning the IQ modulation.
    Parameters:
        state: Activates/deactivates the I/Q modulation. Values are 'ON', and 'OFF'.
        source: Selects/reads the input signal source for the I/Q modulator.
            Values are:
            'BAS': internal baseband signal
            'ANAL': external analog signal
            'DIFF': differential analog signal (only with option SMW-K739)
        gain: Optimizes the modulation of the I/Q modulator for a subset of
            measurement requirements. Values are:
            'DB0', 'DB2', 'DB4', 'DB6', 'DB8': Activates the specified gain of
                0 dB, +2 dB, +4 dB, +6 dB, +8 dB
            'DBM2', 'DBM4': Activates the specified gain of -2 dB, -4 dB
            'DBM3', 'DB3': Provided only for backward compatibility with other
                Rohde & Schwarz signal generators. The R&S SMW accepts these
                values and maps them automatically as follows:
                DBM3 = DBM2, DB3 = DB2
            'AUTO': The gain value is retrieved form the connected R&S SZU. The
                I/Q modulator is configured automatically.
        swap: Activates/Deactives the swapping of the I and Q channel. Values are
            'ON' and 'OFF'.
        crest_factor: If source set to `ANAL' (Analog Wideband I/Q Input), sets
            the crest factor of the externally supplied analog signal. The crest
            factor gives the difference in level between the peak envelope power
            (PEP) and the average power value (RMS) in dB. The R&S SMW uses this
            value for the calculation of the RF output power. The allowed range
            is from 0 dB to 35 dB.
        wideband: Activates/deactivates optimization for wideband modulation signals
            (higher I/Q modulation bandwidth). Values are 'ON' and 'OFF'.
    """
    def __init__(self, parent: 'RohdeSchwarz_SMW200A', name: str, hwchan: int):
        """
        Creates a new IQModulation
        Args:
            parent: the parent instrument of this channel
            name  : the internal QCoDeS name of this channel
            hwchan: the internal number of the hardware channel used in the communication
        """
        self.hwchan = hwchan
        super().__init__(parent, name)

        if 'SMW-K739' in self._parent.options:
            source_validator = vals.Enum('BAS', 'ANAL', 'DIFF')
        else:
            source_validator = vals.Enum('BAS', 'ANAL')
        self.add_parameter('source',
                           label='Source',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'IQ:SOUR {}',
                           get_cmd='SOUR{}:'.format(self.hwchan)+'IQ:SOUR?',
                           vals=source_validator,
                           docstring="""
                           Selects/reads the input signal source for the I/Q modulator.
                           Values are:
                               'BAS': internal baseband signal
                               'ANAL': external analog signal
                               'DIFF': differential analog signal (only with option SMW-K739)
                           """)

        self.add_parameter('state',
                           label='State',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'IQ:STAT {}',
                           get_cmd='SOUR{}:'.format(self.hwchan)+'IQ:STAT?',
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="Activates/deactivates the I/Q modulation. Values"
                                     " are 'ON', and 'OFF'")

        self.add_parameter('gain',
                           label='Gain',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'IQ:GAIN {}',
                           get_cmd='SOUR{}:'.format(self.hwchan)+'IQ:GAIN?',
                           vals=vals.Enum('DBM4', 'DBM2', 'DB0', 'DB2', 'DB4', \
                                          'DB8', 'DB6', 'DBM3', 'DB3', 'AUTO'),
                           docstring="""
                           Optimizes the modulation of the I/Q modulator for a subset
                           of measurement requirements. Possible values are:
                               'DB0'=0dB, 'DB2'=+2dB, 'DB4'=+4dB, 'DB6'=+6dB, 'DB8'=+8dB
                               'DBM2'=-2dB, 'DBM4'=-4dB
                               'DB3' and 'DBM3' provided for backward compatibility (+/-2dB)
                               'AUTO': The gain value is retrieved form the connected R&S SZU.
                               The I/Q modulator is configured automatically.
                           """)

        self.add_parameter('crest_factor',
                           label='Crest factor',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'IQ:CRES {}',
                           get_cmd='SOUR{}:'.format(self.hwchan)+'IQ:CRES?',
                           get_parser=float,
                           vals=vals.Numbers(0, 35),
                           unit='dB',
                           docstring="If source set to `ANAL' (Analog Wideband I/Q Input),"
                                     " sets the crest factor of the externally supplied"
                                     " analog signal. The crest factor gives the difference"
                                     " in level between the peak envelope power (PEP) and"
                                     " the average power value (RMS) in dB. The R&S SMW uses"
                                     " this value for the calculation of the RF output power."
                                     " The allowed range is from 0 dB to 35 dB.")

        self.add_parameter('swap',
                           label='Swap',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'IQ:SWAP:STAT {}',
                           get_cmd='SOUR{}:'.format(self.hwchan)+'IQ:SWAP:STAT?',
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="Activates/Deactives the swapping of the I"
                                     " and Q channel. Values are 'ON' and 'OFF'.")

        self.add_parameter('wideband',
                           label='Wideband',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'IQ:WBST {}',
                           get_cmd='SOUR{}:'.format(self.hwchan)+'IQ:WBST?',
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="Activates/deactivates optimization for wideband"
                                     " modulation signals (higher I/Q modulation"
                                     " bandwidth). Values are 'ON' and 'OFF'.")



class FrequencyModulation(InstrumentChannel): # doc done **********************
    """
    Combines all the parameters concerning the frequency modulation.
    Parameters:
        state: actives/deactivates the frequency modulation. Values are 'ON' and 'OFF'.
        deviation: Sets the modulation deviation of the frequency modulation in Hz.
        source: Selects the modulation source. Values are:
            'INT': internally generated LF signal = 'LF1' (for channel 2 only
                available with option SMW-K24)
            'EXT': externally supplied LF signal  = 'EXT1' (for channel 2 only
                available with option SMW-K24)
            'LF1': first internally generated signal
            'LF2': second internally gererated signal (only available with option SMW-K24)
            'NOIS': internally generated noise signal (only available with option SMW-K24)
            'EXT1': first externally supplied signal
            'EXT2': second externally supplied signal
            'INTB': internal baseband signal (only available with option SMW-B9)
        coupling_mode: Selects the coupling mode. The coupling mode parameter also
            determines the mode for fixing the total deviation. Values are:
            'UNC': Does not couple the LF signals. The deviation values of both paths are
                   independent.
            'TOT': Couples the deviation of both paths.
            'RAT': Couples the deviation ratio of both paths
        total_deviation: Sets the total deviation of the LF signal when using combined
            signal sources in frequency modulation.
        deviation_ratio: Sets the deviation ratio (path2 to path1) in percent.
        mode: Selects the mode for the frequency modulation. Values are:
            'NOR': normal mode
            'LNO': low noise mode
        sensitivity: (ReadOnly) Queries the sensitivity of the externally supplied signal for
            frequency modulation. The sensitivity depends on the set modulation deviation.

    """
    def __init__(self, parent: 'RohdeSchwarz_SMW200A', name: str, hwchan: int, chnum: int):
        """
        Creates a new FrequencyModulation
        Args:
            parent: the parent instrument of this channel
            name  : the internal QCoDeS name of this channel
            hwchan: the internal number of the hardware channel used in the communication
            chnum : the internal number of the channel used for the communication
        """
        self.hwchan = hwchan
        self.chnum = chnum
        super().__init__(parent, name)

        self.add_parameter('state',
                           label='State',
                           set_cmd='SOUR{}:FM{}:'.format(self.hwchan, self.chnum)+'STAT {}',
                           get_cmd='SOUR{}:FM{}:STAT?'.format(self.hwchan, self.chnum),
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="actives/deactivates the frequency modulation."
                                     " Values are 'ON' and 'OFF'.")

        self.add_parameter('deviation',
                           label='Deviation',
                           set_cmd='SOUR{}:FM{}:'.format(self.hwchan, self.chnum)+'DEV {}',
                           get_cmd='SOUR{}:FM{}:DEV?'.format(self.hwchan, self.chnum),
                           get_parser=float,
                           vals=vals.Numbers(0, 1.6e8),
                           unit='Hz',
                           docstring="Sets the modulation deviation of the frequency"
                                     " modulation in Hz.")

        # Select the set of available values from the installed options
        if 'SMW-B9' in self._parent.options and not 'SMW-K24' in self._parent.options:
            sv = ['INT', 'LF1', 'EXT', 'EXT1', 'EXT2', 'INTB'] \
            if self.chnum == 1 else ['LF1', 'EXT1', 'EXT2', 'INTB']
        elif not 'SMW-B9' in self._parent.options and 'SMW-K24' in self._parent.options:
            sv = ['INT', 'LF1', 'LF2', 'NOIS', 'EXT', 'EXT1', 'EXT2']
        elif 'SMW-B9' in self._parent.options and 'SMW-K24' in self._aprent.options:
            sv = ['INT', 'LF1', 'LF2', 'NOIS', 'EXT', 'EXT1', 'EXT2', 'INTB']
        else:
            sv = ['INT', 'LF1', 'EXT', 'EXT1', 'EXT2'] \
            if self.chnum == 1 else ['LF1', 'EXT1', 'EXT2']
        # Generate part of the docstring value according to the validator strings
        ds = ""
        if 'INT' in sv:
            ds += "\n'INT': internally generated LF signal = 'LF1'"
        if 'EXT' in sv:
            ds += "\n'EXT': externally supplied LF signal  = 'EXT1'"
        if 'LF1' in sv:
            ds += "\n'LF1': first internally generated signal"
        if 'LF2' in sv:
            ds += "\n'LF2': second internally gererated signal"
        if 'NOIS' in sv:
            ds += "\n'NOIS': internally generated noise signal"
        if 'EXT1' in sv:
            ds += "\n'EXT1': first externally supplied signal"
        if 'EXT2' in sv:
            ds += "\n'EXT2': second externally supplied signal"
        if 'INTB' in sv:
            ds += "\n'INTB': internal baseband signal"
        self.add_parameter('source',
                           label='Source',
                           set_cmd='SOUR{}:FM{}:'.format(self.hwchan, self.chnum)+'SOUR {}',
                           get_cmd='SOUR{}:FM{}:SOUR?'.format(self.hwchan, self.chnum),
                           vals=vals.Enum(*sv),
                           docstring="Selects the modulation source. Values are:"+ds)

        if 'SMW-XXX' in self._parent.options: #TODO: welche Option wird hierfür benötigt?
            self.add_parameter('coupling_mode',
                               label='Coupling mode',
                               set_cmd='SOUR{}:'.format(self.hwchan)+'FM:DEV:MODE {}',
                               get_cmd='SOUR{}:'.format(self.hwchan)+'FM:DEV:MODE?',
                               vals=vals.Enum('UNC', 'TOT', 'RAT'))

        if 'SMW-XXX' in self._parent.options: #TODO: welche Option wird hierfür benötigt?
            self.add_parameter('total_deviation',
                               label='Total deviation',
                               set_cmd='SOUR{}:'.format(self.hwchan)+'FM:DEV:SUM {}',
                               get_cmd='SOUR{}:'.format(self.hwchan)+'FM:DEV:SUM?',
                               get_parser=float,
                               vals=vals.Numbers(0, 40e6))

        self.add_parameter('deviation_ratio',
                           label='Deviation ratio',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'FM:RAT {}',
                           get_cmd='SOUR{}:'.format(self.hwchan)+'FM:RAT?',
                           get_parser=float,
                           vals=vals.Numbers(0, 100),
                           unit='%',
                           docstring="Sets the deviation ratio (path2 to path1) in percent.")

        self.add_parameter('mode',
                           label='Mode',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'FM:MODE {}',
                           get_cmd='SOUR{}:'.format(self.hwchan)+'FM:MODE?',
                           vals=vals.Enum('NORM', 'LNO'),
                           docstring="Selects the mode for the frequency modulation."
                                     " 'NOR'=normal mode, 'LNO'=low noise mode")

        self.add_parameter('sensitivity',
                           label='Sensitivity',
                           set_cmd=False,
                           get_cmd='SOUR{}:'.format(self.hwchan)+'FM:SENS?',
                           get_parser=float,
                           unit='Hz/V',
                           docstring="(ReadOnly) Queries the sensitivity of the externally"
                                     " supplied signal for frequency modulation. The"
                                     " sensitivity depends on the set modulation deviation.")



class AmplitudeModulation(InstrumentChannel): # doc done **********************
    """
    Combines all the parameters concerning the amplitude modulation. Activation
    of amplitude modulation deactivates ARB, I/Q modulation, digital modulation
    and all digital standards.
    Parameters:
        state: actives/deactivates the amplitude modulation. Values are 'ON' and 'OFF'.
        source: Selects the modulation source. Values are:
            'INT': internally generated LF signal = 'LF1' (for channel 2 only
                available with option SMW-K24)
            'EXT': externally supplied LF signal  = 'EXT1' (for channel 2 only
                available with option SMW-K24)
            'LF1': first internally generated signal
            'LF2': second internally gererated signal (only available with option SMW-K24)
            'NOIS': internally generated noise signal (only available with option SMW-K24)
            'EXT1': first externally supplied signal
            'EXT2': second externally supplied signal
        depth: Sets the depth of the amplitude modulation in percent.
        total_depth: Sets the total depth of the LF signal when using combined
            signal sources in amplitude modulation.
        coupling_mode: Selects the coupling mode. The coupling mode parameter also
            determines the modefor fixing the total depth. Values are:
            'UNC': Does not couple the LF signals. The deviation depth values of
                both paths are independent.
            'TOT': Couples the deviation depth of both paths.
            'RAT': Couples the deviation depth ratio of both paths.
        deviation_ratio: Sets the deviation ratio (path2 to path1) in percent.
        sensitivity: (ReadOnly) Queries the sensitivity of the externally applied signal.
            The sensitivity depends on the set modulation depth. The returned value
            reports the sensitivity in %/V. It is assigned to the voltage value for
            full modulation of the input.
    """
    def __init__(self, parent: 'RohdeSchwarz_SMW200A', name: str, hwchan: int, chnum: int):
        """
        Creates a new AmplitudeModulation
        Args:
            parent: the parent instrument of this channel
            name  : the internal QCoDeS name of this channel
            hwchan: the internal number of the hardware channel used in the communication
            chnum : the internal number of the channel used in the communication
        """
        self.hwchan = hwchan
        self.chnum = chnum
        super().__init__(parent, name)

        self.add_parameter('state',
                           label='State',
                           set_cmd='SOUR{}:AM{}:'.format(self.hwchan, self.chnum)+'STAT {}',
                           get_cmd='SOUR{}:AM{}:STAT?'.format(self.hwchan, self.chnum),
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="""
                           Actives/deactivates the amplitude modulation. Values are 'ON' and 'OFF'.
                           Activation of amplitude modulation deactivates ARB, I/Q modulation,
                           digital modulation and all digital standards.
                           """)

        # Select the set of available values from the installed options
        if 'SMW-K24' in self._parent.options:
            sv = ['LF1', 'LF2', 'EXT1', 'EXT2', 'NOIS', 'INT', 'EXT']
        else:
            sv = ['LF1', 'EXT1', 'EXT2', 'INT', 'EXT'] if chnum == 1 \
            else ['LF1', 'EXT1', 'EXT2']
        # Generate part of the docstring value according to the validator strings
        ds = ""
        if 'INT' in sv:
            ds += "\n'INT': internally generated LF signal = 'LF1'"
        if 'EXT' in sv:
            ds += "\n'EXT': externally supplied LF signal  = 'EXT1'"
        if 'LF1' in sv:
            ds += "\n'LF1': first internally generated signal"
        if 'LF2' in sv:
            ds += "\n'LF2': second internally gererated signal"
        if 'NOIS' in sv:
            ds += "\n'NOIS': internally generated noise signal"
        if 'EXT1' in sv:
            ds += "\n'EXT1': first externally supplied signal"
        if 'EXT2' in sv:
            ds += "\n'EXT2': second externally supplied signal"
        self.add_parameter('source',
                           label='Source',
                           set_cmd='SOUR{}:AM{}:'.format(self.hwchan, self.chnum)+'SOUR {}',
                           get_cmd='SOUR{}:AM{}:SOUR?'.format(self.hwchan, self.chnum),
                           vals=vals.Enum(*sv),
                           docstring="Selects the modulation source. Values are:"+ds)

        self.add_parameter('depth',
                           label='Depth',
                           set_cmd='SOUR{}:AM{}:'.format(self.hwchan, self.chnum)+'DEPT {}',
                           get_cmd='SOUR{}:AM{}:DEPT?'.format(self.hwchan, self.chnum),
                           get_parser=float,
                           unit='%',
                           vals=vals.Numbers(0, 100),
                           docstring="Sets the depth of the amplitude modulation in percent.")

        if 'SMW-XXX' in self._parent.options: #TODO: welche Option wird hierfür benötigt?
            self.add_parameter('total_depth',
                               label='Total depth',
                               set_cmd='SOUR{}:'.format(self.hwchan)+'AM:DEPT:SUM {}',
                               get_cmd='SOUR{}:'.format(self.hwchan)+'AM:DEPT:SUM?',
                               get_parser=float,
                               vals=vals.Numbers(0, 100))

        if 'SMW-XXX' in self._parent.options: #TODO: welche Option wird hierfür benötigt?
            self.add_parameter('coupling_mode',
                               label='Coupling mode',
                               set_cmd='SOUR{}:'.format(self.hwchan)+'AM:DEV:MODE {}',
                               get_cmd='SOUR{}:'.format(self.hwchan)+'AM:DEV:MODE?',
                               vals=vals.Enum('UNC', 'TOT', 'RAT'))

        self.add_parameter('deviation_ratio',
                           label='Deviation ratio',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'AM:RAT {}',
                           get_cmd='SOUR{}:'.format(self.hwchan)+'AM:RAT?',
                           get_parser=float,
                           vals=vals.Numbers(0, 100),
                           unit='%',
                           docstring="Sets the deviation ratio (path2 to path1) in percent.")

        self.add_parameter('sensitivity',
                           label='Sensitifity',
                           set_cmd=False,
                           get_cmd='SOUR{}:'.format(self.hwchan)+'AM:SENS?',
                           get_parser=float,
                           unit='%/V',
                           docstring="(ReadOnly) Queries the sensitivity of the externally"
                                     " applied signal. The sensitivity depends on the set"
                                     " modulation depth. The returned value reports the"
                                     " sensitivity in %/V. It is assigned to the voltage"
                                     " value for full modulation of the input.")



class PulseModulation(InstrumentChannel): # doc done **************************
    """
    Combines all the parameters concerning the pulse modulation.
    Parameters:
        state: Activates/deactivates the pulse modulation. Values are 'ON' and 'OFF'.
        source: Selects the modulation source. Values are:
            'INT': internally generated signal is used (only available with option SMW-K23)
            'EXT': externally supplied signal is used
        transition_type: sets the transition mode for the pulse signal. Values are:
            'SMO': flattens the slew , resulting in longer rise/fall times (SMOothed)
            'FAST': enables fast transition with shortest rise and fall times
        video_polarity: Sets the polarity of the pulse video (modulating) signal,
            related to the RF (modulated) signal. Values are:
            'NORM': the video signal follows the RF signal, that means it is high
                when RF signal is high and vice versa
            'INV': the video signal follows in inverted mode
        polarity: sets the polarity of the externally applied modulation signal
            'NORM': Suppresses the RF signal during the pulse pause
            'INV': Suppresses the RF signal during the pulse
        impedance: Sets the impedance for the external pulse modulation input.
            Values are 'G50' and 'G1K'
        trigger_impedance: Sets the impedance for the external pulse trigger.
            Values are 'G50' and 'G10K'

        Only available with option SMW-K23:
            mode: Selects the mode for the pulse modulation. Values can be:
                'SING': generates a single pulse
                'DOUB': generates two pulses within one pulse period
            double_delay: Sets the delay from the start of the first pulse to
                the start of the second pulse.
            double_width: Sets the width of the second pulse.
            trigger_mode: Selects a trigger mode for generating the modulation signal.
                Values are 'AUTO' (AUTOmatic), 'EXT' (EXTernal), 'EGAT' (External GATed),
                'ESIN' (External single).
            period: Sets the period of the generated pulse, that means the
                repetition frequency of the internally generated modulation signal.
            width: Sets the width of the generated pulse, that means the pulse length.
                It must be at least 20ns less than the set pulse period.
            delay: Sets the pulse delay.
    """
    def __init__(self, parent: 'RohdeSchwarz_SMW200A', name: str, hwchan: int):
        """
        Creates a new PulseModulation
        Args:
            parent: the parent instrument of this channel
            name  : the internal QCoDeS name of this channel
            hwchan: the internal number of the hardware channel used in the communication
        """
        self.hwchan = hwchan
        super().__init__(parent, name)

        if 'SMW-K23' in self._parent.options:
            self.add_parameter('mode',
                               label='Mode',
                               set_cmd='SOUR{}:'.format(self.hwchan)+'PULM:MODE {}',
                               get_cmd='SOUR{}:'.format(self.hwchan)+'PULM:MODE?',
                               vals=vals.Enum('SING', 'DOUB'),
                               docstring="""
                               Selects the mode for the pulse modulation.
                               'SING': generates a single pulse
                               'DOUB': generates two pulses within one pulse period.
                               """)

            self.add_parameter('double_delay',
                               label='Double delay',
                               set_cmd='SOUR{}:'.format(self.hwchan)+'PULM:DOUB:DEL {}',
                               get_cmd='SOUR{}:'.format(self.hwchan)+'PULM:DOUB:DEL?',
                               get_parser=float,
                               docstring="Sets the delay from the start of the first"
                                         " pulse to the start of the second pulse.")

            self.add_parameter('double_width',
                               label='Double width',
                               set_cmd='SOUR{}:'.format(self.hwchan)+'PULM:DOUB:WID {}',
                               get_cmd='SOUR{}:'.format(self.hwchan)+'PULM:DOUB:WID?',
                               get_parser=float,
                               docstring="Sets the width of the second pulse.")

            self.add_parameter('trigger_mode',
                               label='Trigger mode',
                               set_cmd='SOUR{}:'.format(self.hwchan)+'PULM:TRIG:MODE {}',
                               get_cmd='SOUR{}:'.format(self.hwchan)+'PULM:TRIG:MODE?',
                               vals=vals.Enum('AUTO', 'EXT', 'EGAT', 'ESIN'),
                               docstring="Selects a trigger mode for generating the modulation"
                                         " signal. Values are 'AUTO' (AUTOmatic), 'EXT'"
                                         " (EXTernal), 'EGAT' (External GATed), 'ESIN'"
                                         " (External single).")

            self.add_parameter('period',
                               label='Period',
                               set_cmd='SOUR{}:'.format(self.hwchan)+'PULM:PER {}',
                               get_cmd='SOUR{}:'.format(self.hwchan)+'PULM:PER?',
                               get_parser=float,
                               vals=vals.Numbers(20e-9, 100),
                               unit='s',
                               docstring="Sets the period of the generated pulse, that"
                                         " means the repetition frequency of the internally"
                                         " generated modulation signal.")

            self.add_parameter('width',
                               label='Width',
                               set_cmd=partial(self._setwidth),
                               get_cmd='SOUR{}:'.format(self.hwchan)+'PULM:WIDT?',
                               get_parser=float,
                               vals=vals.Numbers(20e-9, 100),
                               unit='s',
                               docstring="Sets the width of the generated pulse, that"
                                         " means the pulse length. It must be at least"
                                         " 20ns less than the set pulse period.")

            self.add_parameter('delay',
                               label='Delay',
                               set_cmd='SOUR{}:'.format(self.hwchan)+'PULM:DEL {}',
                               get_cmd='SOUR{}:'.format(self.hwchan)+'PULM:DEL?',
                               get_parser=float,
                               vals=vals.Numbers(),
                               unit='s',
                               docstring="Sets the pulse delay.")

        self.add_parameter('state',
                           label='State',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'PULM:STAT {}',
                           get_cmd='SOUR{}:'.format(self.hwchan)+'PULM:STAT?',
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="Activates/deactivates the pulse modulation."
                                     " Values are 'ON' and 'OFF'.")

        sv = ['INT', 'EXT'] if 'SMW-K23' in self._parent.options else ['EXT']
        ds = ""
        if 'INT' in sv:
            ds += "\n'INT': internally generated signal"
        if 'EXT' in sv:
            ds += "\n'EXT': externally supplied signal"
        self.add_parameter('source',
                           label='Source',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'PULM:SOUR {}',
                           get_cmd='SOUR{}:'.format(self.hwchan)+'PULM:SOUR?',
                           vals=vals.Enum(*sv),
                           docstring="Selects the modulation source. Values are:"+ds)

        self.add_parameter('transition_type',
                           label='Transition type',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'PULM:TTYP {}',
                           get_cmd='SOUR{}:'.format(self.hwchan)+'PULM:TTYP?',
                           vals=vals.Enum('SMO', 'FAST'),
                           docstring="""
                           Sets the transition mode for the pulse signal.
                           'SMO': flattens the slew, resulting in longer rise/fall times (SMOothed),
                           'FAST': enables fast transition with shortest rise and fall times
                           """)

        self.add_parameter('video_polarity',
                           label='Video polaraity',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'PULM:OUTP:VID:POL {}',
                           get_cmd='SOUR{}:'.format(self.hwchan)+'PULM:OUTP:VID:POL?',
                           vals=vals.Enum('NORM', 'INV'),
                           docstring="""
                           Sets the polarity of the pulse video (modulating) signal, related to
                           the RF (modulated) signal.
                           'NORM': the video signal follows the RF signal, that means it is high
                            when RF signal is high and vice versa
                           'INV': the video signal follows in inverted mode
                           """)

        self.add_parameter('polarity',
                           label='Polarity',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'PULM:POL {}',
                           get_cmd='SOUR{}:'.format(self.hwchan)+'PULM:POL?',
                           vals=vals.Enum('NORM', 'INV'),
                           docstring="""
                           sets the polarity of the externally applied modulation signal
                           'NORM': Suppresses the RF signal during the pulse pause
                           'INV': Suppresses the RF signal during the pulse
                           """)

        self.add_parameter('impedance',
                           label='Impedance',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'PULM:IMP {}',
                           get_cmd='SOUR{}:'.format(self.hwchan)+'PULM:IMP?',
                           vals=vals.Enum('G50', 'G1K'),
                           docstring="Sets the impedance for the external pulse modulation"
                                     " input. Values are 'G50' and 'G1K'")

        self.add_parameter('trigger_impedance',
                           label='Trigger impedance',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'PULM:TRIG:EXT:IMP {}',
                           get_cmd='SOUR{}:'.format(self.hwchan)+'PULM:TRIG:EXT:IMP?',
                           vals=vals.Enum('G50', 'G10K'),
                           docstring="Sets the impedance for the external pulse trigger."
                                     " Values are 'G50' and 'G10K'")

    def _setwidth(self, val):
        """
        Helper function to check the maximum allowed value for the step
        """
        maxwidth = self.period()-20e-9
        if val > maxwidth:
            raise ValueError('{} is invalid: must be between 20e-9 '
                             'and {} inclusive.'.format(repr(val), maxwidth))
        self.write('SOUR{}:'.format(self.hwchan)+'PULM:WIDT {}'.format(val))



class PulseGenerator(InstrumentChannel):
    """
    Combines all the parameters concerning the pulse generator for setting output
    of the pulse modulation signal. Available only with option SMW-K23 installed.
    Parameters:
        polarity: Sets the polarity of the pulse output signal. Values are:
            'NORM': Outputs the pulse signal during the pulse width, that means during
                    the high state.
            'INV' : Inverts the pulse output signal polarity. The pulse output signal
                    is suppressed during the pulse width, but provided during the low state.
        output: Activates the output of the pulse modulation signal. Possible values: OFF or ON.
        state: Enables the output of the video/sync signal. If the pulse generator is the
               current modulation source, activating the pulse modulation automatically
               activates the signal output and the pulse generator.
    Configurations for the Pulse Generator set with another subclass:
        Pulse Mode         -> PulseModulation.mode()
        Trigger Mode       -> PulseModulation.trigger_mode()
        Pulse Period       -> PulseModulation.period()
        Pulse Width        -> PulseModulation.width()
        Double Pulse Width -> PulseModulation.double_width()
        Pulse Delay        -> PulseModulation.delay()
        Double Pulse Delay -> PulseModulation.double_delay()
    """
    def __init__(self, parent: 'RohdeSchwarz_SMW200A', name: str, hwchan: int):
        """
        Creates a new PulseGenerator
        Args:
            parent: the parent instrument of this channel
            name  : the internal QCoDeS name of this channel
            hwchan: the internal number of the hardware channel used in the communication
        """
        self.hwchan = hwchan
        super().__init__(parent, name)
        if not 'SMW-K23' in self._parent.options:
            raise RuntimeError("Invalid usage of class without installed option K23")

        self.add_parameter('polarity',
                           label='Polarity',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'PGEN:OUTP:POL {}',
                           get_cmd='SOUR{}:'.format(self.hwchan)+'PGEN:OUTP:POL?',
                           vals=vals.Enum('NORM', 'INV'),
                           docstring="""
                           Sets the polarity of the pulse output signal.
                           'NORM': Outputs the pulse signal during the pulse width,
                           that means during the high state.
                           'INV': Inverts the pulse output signal polarity. The
                           pulse output signal is suppressed during the pulse width,
                           but provided during the low state.
                           """)

        self.add_parameter('output',
                           label='Output',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'PGEN:OUTP:STAT {}',
                           get_cmd='SOUR{}:'.format(self.hwchan)+'PGEN:OUTP:STAT?',
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="""
                           Activates the output of the pulse modulation signal.
                           Possible values: OFF or ON.
                           """)

        self.add_parameter('state',
                           label='State',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'PGEN:STAT {}',
                           get_cmd='SOUR{}:'.format(self.hwchan)+'PGEN:STAT?',
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="""
                           Enables the output of the video/sync signal.
                           If the pulse generator is the current modulation source,
                           activating the pulse modulation automatically activates
                           the signal output and the pulse generator.
                           Possible values: OFF or ON.
                           """)

        self.add_parameter('mode',
                           label='',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'PGEN:STAT {}',
                           get_cmd='SOUR{}:'.format(self.hwchan)+'PGEN:STAT?',
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="""
                           """)

        self.add_parameter('test',
                           label='State',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'PGEN:STAT {}',
                           get_cmd='SOUR{}:'.format(self.hwchan)+'PGEN:STAT?',
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="""
                           """)



class PhaseModulation(InstrumentChannel): # doc done **************************
    """
    Combines all the parameters concerning the phase modulation.
    Parameters:
        state: Activates or deactivates phase modulation.
            Activation of phase modulation deactivates frequency modulation.
            Possible values are 'ON' and 'OFF'.
        deviation: Sets the modulation deviation of the phase modulation in RAD.
        source: Selects the modulation source. Values are:
            'INT': internally generated LF signal = 'LF1' (for channel 2 only
                available with option SMW-K24)
            'EXT': externally supplied LF signal  = 'EXT1' (for channel 2 only
                available with option SMW-K24)
            'LF1': first internally generated signal
            'LF2': second internally gererated signal (only available with option SMW-K24)
            'NOIS': internally generated noise signal (only available with option SMW-K24)
            'EXT1': first externally supplied signal
            'EXT2': second externally supplied signal
            'INTB': internal baseband signal (only available with option SMW-B9)
        mode: Selects the mode for the phase modulation. Possible values are:
            'HBAN': sets the maximum available bandwidth (High BANdwidth)
            'HDEV': sets the maximum range for deviation (High DEViation)
            'LNO': selects a phase modulation mode with phase noise and spurious
                characteristics close to CW mode. (Low NOise)
        coupling_mode: Selects the coupling mode. Possible values are:
            'UNC': Does not couple the LF signals. The deviation values of both
                paths are independent.
            'TOT': Couples the deviation of both paths.
            'RAT': Couples the deviation ratio of both paths.
        total_deviation: Sets the total deviation of the LF signal when using
            combined signal sources. Possible values range from 0 to 20.
        ratio: Sets the deviation ratio (path2 to path1) in percent.
        sensitivity: Queries the sensitivity of the externally applied signal for phase
            modulation. The returned value reports the sensitivity in RAD/V. It is assigned
            to the voltage value for full modulation of the input.
    """
    def __init__(self, parent: 'RohdeSchwarz_SMW200A', name: str, hwchan: int, chnum: int):
        """
        Creates a new PhaseModulation
        Args:
            parent: the parent instrument of this channel
            name  : the internal QCoDeS name of this channel
            hwchan: the internal number of the hardware channel used in the communication
            chnum : the internal number of the channel used in the communication
        """
        self.hwchan = hwchan
        self.chnum = chnum
        super().__init__(parent, name)

        self.add_parameter('state',
                           label='State',
                           set_cmd='SOUR{}:PM{}:'.format(self.hwchan, self.chnum)+'STAT {}',
                           get_cmd='SOUR{}:PM{}:STAT?'.format(self.hwchan, self.chnum),
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="Activates or deactivates phase modulation. Values are"
                                     " 'ON' and 'OFF'. Activation of phase modulation"
                                     " deactivates frequency modulation.")

        self.add_parameter('deviation',
                           label='Deviation',
                           set_cmd='SOUR:PM{}:'.format(self.chnum)+'DEV {}',
                           get_cmd='SOUR:PM{}:DEV?'.format(self.chnum),
                           vals=vals.Numbers(0, 16),
                           unit='RAD',
                           docstring="Sets the modulation deviation of the phase"
                                     "modulation in RAD.")

        # Select the set of available values from the installed options
        if 'SMW-B9' in self._parent.options and not 'SMW-K24' in self._parent.options:
            sv = ['INT', 'LF1', 'EXT', 'EXT1', 'EXT2', 'INTB'] \
            if self.chnum == 1 else ['LF1', 'EXT1', 'EXT2', 'INTB']
        elif not 'SMW-B9' in self._parent.options and 'SMW-K24' in self._parent.options:
            sv = ['INT', 'LF1', 'LF2', 'NOIS', 'EXT', 'EXT1', 'EXT2']
        elif 'SMW-B9' in self._parent.options and 'SMW-K24' in self._aprent.options:
            sv = ['INT', 'LF1', 'LF2', 'NOIS', 'EXT', 'EXT1', 'EXT2', 'INTB']
        else:
            sv = ['INT', 'LF1', 'EXT', 'EXT1', 'EXT2'] \
            if self.chnum == 1 else ['LF1', 'EXT1', 'EXT2']
        # Generate part of the docstring value according to the validator strings
        ds = ""
        if 'INT' in sv:
            ds += "\n'INT': internally generated LF signal = 'LF1'"
        if 'EXT' in sv:
            ds += "\n'EXT': externally supplied LF signal  = 'EXT1'"
        if 'LF1' in sv:
            ds += "\n'LF1': first internally generated signal"
        if 'LF2' in sv:
            ds += "\n'LF2': second internally gererated signal"
        if 'NOIS' in sv:
            ds += "\n'NOIS': internally generated noise signal"
        if 'EXT1' in sv:
            ds += "\n'EXT1': first externally supplied signal"
        if 'EXT2' in sv:
            ds += "\n'EXT2': second externally supplied signal"
        if 'INTB' in sv:
            ds += "\n'INTB': internal baseband signal"
        self.add_parameter('source',
                           label='Source',
                           set_cmd='SOUR{}:PM{}:'.format(self.hwchan, self.chnum)+'SOUR {}',
                           get_cmd='SOUR{}:PM{}:SOUR?'.format(self.hwchan, self.chnum),
                           vals=vals.Enum(*sv),
                           docstring="Selects the modulations source. Values are:"+ds)

        self.add_parameter('mode',
                           label='Mode',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'PM:MODE {}',
                           get_cmd='SOUR{}:'.format(self.hwchan)+'PM:MODE?',
                           vals=vals.Enum('HBAN', 'HDEV', 'LNO'),
                           docstring="""
                           Selects the mode for the phase modulation. Possible values are:
                           'HBAN': sets the maximum available bandwidth (High BANdwidth)
                           'HDEV': sets the maximum range for deviation (High DEViation)
                           'LNO': selects a phase modulation mode with phase noise and spurious
                               characteristics close to CW mode. (Low NOise)
                           """)

        if 'SMW-XXX' in self._parent.options: #TODO: welche Option wird hierfür benötigt?
            self.add_parameter('coupling_mode',
                               label='Coupling mode',
                               set_cmd='SOUR{}:'.format(self.hwchan)+'PM:DEV:MODE {}',
                               get_cmd='SOUR{}:'.format(self.hwchan)+'PM:DEV:MODE?',
                               vals=vals.Enum('UNC', 'TOT', 'RAT'))

        if 'SMW-XXX' in self._parent.options: #TODO: welche Option wird hierfür benötigt?
            self.add_parameter('total_deviation',
                               label='Total deviation',
                               set_cmd='SOUR{}:'.format(self.hwchan)+'PM:DEV:SUM {}',
                               get_cmd='SOUR{}:'.format(self.hwchan)+'PM:DEV:SUM?',
                               vals=vals.Numbers(0, 20))

        self.add_parameter('ratio',
                           label='Ratio',
                           set_cmd='SOUR{}:'.format(self.hwchan)+'PM:RAT {}',
                           get_cmd='SOUR{}:'.format(self.hwchan)+'PM:RAT?',
                           vals=vals.Numbers(0, 100),
                           unti='%',
                           docstring="Sets the deviation ratio (path2 to path1) in percent.")

        self.add_parameter('sensitivity',
                           label='Sensitivity',
                           set_cmd=False,
                           get_cmd='SOUR{}:'.format(self.hwchan)+'PM:SENS?',
                           unit='RAD/V',
                           docstring="(ReadOnly) Queries the sensitivity of the externally"
                                     " applied signal for phase modulation. The returned"
                                     " value reports the sensitivity in RAD/V. It is assigned"
                                     " to the voltage value for full modulation of the input.")




class LFOutputSweep(InstrumentChannel): # doc done ****************************
    """
    Combines all the parameters concerning one LF output Sweeping.
    The LF output is used as modulation signal for the analog modulation.
    Parameters:
        dwell: Dwell time in seconds from 0.5 ms to 100 s.
        mode: Cycle mode for level sweep.
                'AUTO': Each trigger triggers exactly one complete sweep.
                'MAN':  You can trigger every step individually with a command.
                'STEP': Each trigger triggers one sweep step only.
        points: Steps within level sweep range
        shape: Waveform shape for sweep. Allowed values are 'SAWTOOTH'
                and 'TRIANGLE'
        execute: Executes one RF level sweep. Use this without any ( )
        retrace: Activates that the signal changes to the start frequency value
            while it is waiting for the next trigger event. Values are 'ON' and
            'OFF'. You can enable this feature, when you are working with sawtooth
            shapes in sweep mode 'MAN' or 'STEP'.
        running: (ReadOnly) Reports the current sweep state. Returnvalues
                are 'ON' or 'OFF'.
        spacing: calculationmode of frequency intervals. Values are 'LIN' or 'LOG'
        log_step: Sets the step width factor for logarithmic sweeps to calculate
            the frequencies of the steps. The value can be from 0.01% upto 100%.
        lin_step: Set the step size for linear sweep. The value can be from 0.01
                up to the value of <OutputChannel::sweep_span>
    """
    def __init__(self, parent: 'RohdeSchwarz_SMW200A', name: str, hwchan: int):
        """
        Creates a new LFOutputSweep
        Args:
            parent: the parent instrument of this channel
            name  : the internal QCoDeS name of this channel
            hwchan: the internal number of the hardware channel used in the communication
        """
        self.hwchan = hwchan

        super().__init__(parent, name)

        self.add_parameter('dwell',
                           label='Dwell time',
                           set_cmd='SOUR{}:LFO:SWE:'.format(self.hwchan)+'DWEL {}',
                           get_cmd='SOUR{}:LFO:SWE:DWEL?'.format(self.hwchan),
                           get_parser=float,
                           vals=vals.Numbers(0.0005, 100),
                           unit='s',
                           docstring="Dwell time in seconds from 0.5 ms to 100 s.")

        sweepmode = vals.Enum('AUTO', 'MAN', 'STEP')
        self.add_parameter('mode',
                           label='Cycle mode for level sweep',
                           set_cmd='SOUR{}:LFO:SWE:'.format(self.hwchan)+'MODE {}',
                           get_cmd='SOUR{}:LFO:SWE:MODE?'.format(self.hwchan),
                           vals=sweepmode,
                           docstring="""
                           Cycle mode for level sweep. Values are:
                           'AUTO': Each trigger triggers exactly one complete sweep.
                           'MAN': You can trigger every step individually with a command.
                           'STEP': Each trigger triggers one sweep step only.
                           """)

        self.add_parameter('points',
                           label='Steps within level sweep range',
                           set_cmd='SOUR{}:LFO:SWE:'.format(self.hwchan)+'POIN {}',
                           get_cmd='SOUR{}:LFO:SWE:POIN?'.format(self.hwchan),
                           get_parser=int,
                           vals=vals.Numbers(2),    # Upperlimit=MAXINT
                           docstring="Steps within level sweep range")

        self.add_parameter('shape',
                           label='Waveform shape for sweep',
                           set_cmd='SOUR{}:LFO:SWE:'.format(self.hwchan)+'SHAP {}',
                           get_cmd='SOUR{}:LFO:SWE:SHAP?'.format(self.hwchan),
                           vals=vals.Enum('SAWTOOTH', 'TRIANGLE'),
                           docstring="Waveform shape for sweep. Allowed values"
                                     " are 'SAWTOOTH' and 'TRIANGLE'")

        self.add_parameter('execute',
                           label='Executes one RF level sweep',
                           call_cmd='SOUR{}:LFO:SWE:EXEC'.format(self.hwchan),
                           docstring="Executes one RF level sweep. Use this without any ( )")

        self.add_parameter('retrace',
                           label='Set to start frequency while waiting for trigger  ',
                           set_cmd='SOUR{}:LFO:SWE:'.format(self.hwchan)+'RETR {}',
                           get_cmd='SOUR{}:LFO:SWE:RETR?'.format(self.hwchan),
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="Activates that the signal changes to the start frequency"
                                     " value while it is waiting for the next trigger event."
                                     " Values are 'ON' and 'OFF'. You can enable this feature,"
                                     " when you are working with sawtooth shapes in sweep mode"
                                     " 'MAN' or 'STEP'.")

        self.add_parameter('running',
                           label='Current sweep state',
                           set_cmd=False,
                           get_cmd='SOUR{}:LFO:SWE:RUNN?'.format(self.hwchan),
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="(ReadOnly) Reports the current sweep state."
                                     " Returnvalues are 'ON' or 'OFF'.")

        self.add_parameter('spacing',
                           label='calculationmode of frequency intervals',
                           set_cmd='SOUR{}:LFO:SWE:'.format(self.hwchan)+'SPAC {}',
                           get_cmd='SOUR{}:LFO:SWE:SPAC?'.format(self.hwchan),
                           vals=vals.Enum('LIN', 'LOG'),
                           docstring="Calculationmode of frequency intervals."
                                     " Values are 'LIN' or 'LOG'.")

        self.add_parameter('log_step',
                           label='logarithmically determined step size for the RF freq sweep',
                           set_cmd='SOUR{}:LFO:SWE:STEP:'.format(self.hwchan)+'LOG {}',
                           get_cmd='SOUR{}:LFO:SWE:STEP:LOG?'.format(self.hwchan),
                           get_parser=float,
                           vals=vals.Numbers(0.01, 100),
                           unit='%',
                           docstring="Sets the step width factor for logarithmic sweeps"
                                     " to calculate the frequencies of the steps. The"
                                     " value can be from 0.01% upto 100%.")

        self.add_parameter('lin_step',
                           label='step size for linear RF freq sweep',
                           set_cmd=partial(self._setlinstep),
                           get_cmd='SOUR{}:LFO:SWE:STEP?'.format(self.hwchan),
                           get_parser=float,
                           vals=vals.Numbers(0.01),
                           unit='Hz',
                           docstring="""
                           Set the step size for linear sweep.
                           The maximum is the sweep_span of the output channel
                           and will be read during the set lin_step command.
                           """)

    def _setlinstep(self, val):
        """
        Helper function to check the maximum allowed value for the step
        """
        maxfreq = float(self.ask('SOUR{}:FREQ:SPAN?'.format(self.hwchan)))
        if val > maxfreq:
            raise ValueError('{} is invalid: must be between '
                             '0.01 and {} inclusive.'.format(repr(val), maxfreq))
        self.write('SOUR{}:LFO:SWE:STEP {}'.format(self.hwchan, val))




class LFOutputChannel(InstrumentChannel): # doc done **************************
    """
    Combines all the parameters concerning one LF output.
    The LF output is used as modulation signal for the analog modulation.
    Parameters:
        bandwidth: (ReadOnly) Requests the current bandwidth.
    Parameters only for the first RF-Source available:
        state: The state of the output. Values are 'ON' or 'OFF'.
        offset: DC offset voltage in the range from -3.6V to +3.6V.
        source: Determines the LF signal to be synchronized, when monitoring is
            enabled. Values are:
            'LF1', 'LF2', 'LF1A', 'LF2A', 'LF1B', 'LF2B'
                Selects an internally generated LF signal.
            'NOISE', 'NOISA', 'NOISB'
                Selects an internally generated noise signal.
            'EXT1', 'EXT2'
                Selects an externally supplied LF signal.
            'AM', 'AMA', 'AMB'
                Selects the AM signal.
            'FMPM', 'FMPMA', 'FMPMB'
                Selects the signal also used by the frequency or phase modulations.
        source_path: Path of the LF output source, only with option SMW-???
            available. Values are 'A' or 'B'
        voltage: Output voltage of the LF output. The valid range will be dynamic
            as shown in the datasheet.
    Parameters only for the first LF-Channel available:
        period: ReadOnly. Queries the repetition frequency of the sine signal.
        frequency: The Frequency of the LF signal when the mode() is `FIX'. Valid
            range is from 0.1Hz and ends depending on the installed options.
        freq_manual: Manual frequency set only valid in the range given by the
            parameters freq_min and freq_max.
        freq_min: Set minimum for manual frequency from 0.1Hz to 1MHz.
        freq_max: Set maximum for manual frequency from 0.1Hz to 1MHz.
        mode: Set the used mode:
            FIX = fixed frequency mode (CW is a synonym)
            SWE = set sweep mode (use LFOutputSweep class)
    Parameters only with SMW-K24 option available:
        shape: Define the shape of the signal. Valid values are: 'SINE',
            'SQUARE', 'TRIANGLE', 'TRAPEZE'.
        shape_duty_cycle: Duty cycle for shape pulse (*)
        shape_period: Period for shape pulse (*)
        shape_width: Width for shape pulse (*)
        trapez_fall: Fall time for the trapezoid shape (*)
        trapez_height; High time for the trapezoid signal (*)
        trapez_period: Period of the generated trapezoid shape (*)
        trapez_rise: Rise time for the trapezoid shape (*)
        triangle_period: Period of the generated pulse (*)
        triangle_rise: Rise time for the triangle shape (*)
            (*) All the last parameters have a valid range from 1e-6 to 100.
    """
    def __init__(self, parent: 'RohdeSchwarz_SMW200A', name: str, hwchan: int, lfchan: int):
        """
        Creates a new LFOutputChannel
        Args:
            parent: the parent instrument of this channel
            name  : the internal QCoDeS name of this channel
            hwchan: the internal number of the hardware channel used in the communication
            lfchan: the internal number of the LF output channel used
        """
        self.hwchan = hwchan
        self.lfchan = lfchan

        super().__init__(parent, name)

        # aks the limits for "freq_manual"
        self.freqmin = float(self.ask('SOUR{}:LFO:FREQ:STAR?'.format(self.hwchan)))
        self.freqmax = float(self.ask('SOUR{}:LFO:FREQ:STOP?'.format(self.hwchan)))

        self.add_parameter('bandwidth',
                           label='Bandwidth',
                           set_cmd=False,
                           get_cmd='SOUR:LFO{}:BAND?'.format(self.lfchan),
                           docstring="(ReadOnly) Requests the current bandwidth.")

        if 'SMW-K24' in self._parent.options:
            shape_ids = vals.Enum('SINE', 'SQUARE', 'TRIANGLE', 'TRAPEZE')
            self.add_parameter('shape',
                               label='Shape',
                               set_cmd='SOUR{}:LFO{}'.format(self.hwchan, self.lfchan)+':SHAP {}',
                               get_cmd='SOUR{}:LFO{}:SHAP?'.format(self.hwchan, self.lfchan),
                               vals=shape_ids)

            self.add_parameter('shape_duty_cycle',
                               label='Duty cycle for shape pulse',
                               set_cmd='SOUR{}:LFO{}:SHAP:PULS'.format(self.hwchan, self.lfchan)+':DCYC {}',
                               get_cmd='SOUR{}:LFO{}:SHAP:PULS:DCYC?'.format(self.hwchan, self.lfchan),
                               get_parser=float,
                               vals=vals.Numbers(1e-6, 100),
                               unit='%')

            self.add_parameter('shape_period',
                               label='Period for shape pulse',
                               set_cmd='SOUR{}:LFO{}:SHAP:PULS'.format(self.hwchan, self.lfchan)+':PER {}',
                               get_cmd='SOUR{}:LFO{}:SHAP:PULS:PER?'.format(self.hwchan, self.lfchan),
                               get_parser=float,
                               vals=vals.Numbers(1e-6, 100))

            self.add_parameter('shape_width',
                               label='Width for shape pulse',
                               set_cmd='SOUR{}:LFO{}:SHAP:PULS'.format(self.hwchan, self.lfchan)+':WIDT {}',
                               get_cmd='SOUR{}:LFO{}:SHAP:PULS:WIDT?'.format(self.hwchan, self.lfchan),
                               get_parser=float,
                               vals=vals.Numbers(1e-6, 100))

            self.add_parameter('trapez_fall',
                               label='Fall time for the trapezoid shape',
                               set_cmd='SOUR{}:LFO{}:SHAP:TRAP'.format(self.hwchan, self.lfchan)+':FALL {}',
                               get_cmd='SOUR{}:LFO{}:SHAP:TRAP:FALL?'.format(self.hwchan, self.lfchan),
                               get_parser=float,
                               vals=vals.Numbers(1e-6, 100))

            self.add_parameter('trapez_height',
                               label='High time for the trapezoid signal',
                               set_cmd='SOUR{}:LFO{}:SHAP:TRAP'.format(self.hwchan, self.lfchan)+':HIGH {}',
                               get_cmd='SOUR{}:LFO{}:SHAP:TRAP:HIGH?'.format(self.hwchan, self.lfchan),
                               get_parser=float,
                               vals=vals.Numbers(1e-6, 100))

            self.add_parameter('trapez_period',
                               label='Period of the generated trapezoid shape',
                               set_cmd='SOUR{}:LFO{}:SHAP:TRAP'.format(self.hwchan, self.lfchan)+':PER {}',
                               get_cmd='SOUR{}:LFO{}:SHAP:TRAP:PER?'.format(self.hwchan, self.lfchan),
                               get_parser=float,
                               vals=vals.Numbers(1e-6, 100))

            self.add_parameter('trapez_rise',
                               label='Rise time for the trapezoid shape',
                               set_cmd='SOUR{}:LFO{}:SHAP:TRAP'.format(self.hwchan, self.lfchan)+':RISE {}',
                               get_cmd='SOUR{}:LFO{}:SHAP:TRAP:RISE?'.format(self.hwchan, self.lfchan),
                               get_parser=float,
                               vals=vals.Numbers(1e-6, 100))

            self.add_parameter('triangle_period',
                               label='period of the generated pulse',
                               set_cmd='SOUR{}:LFO{}:SHAP:TRI'.format(self.hwchan, self.lfchan)+':PER {}',
                               get_cmd='SOUR{}:LFO{}:SHAP:TRI:PER?'.format(self.hwchan, self.lfchan),
                               get_parser=float,
                               vals=vals.Numbers(1e-6, 100))

            self.add_parameter('triangle_rise',
                               label='Rise time for the triangle shape',
                               set_cmd='SOUR{}:LFO{}:SHAP:TRI'.format(self.hwchan, self.lfchan)+':RISE {}',
                               get_cmd='SOUR{}:LFO{}:SHAP:TRI:RISE?'.format(self.hwchan, self.lfchan),
                               get_parser=float,
                               vals=vals.Numbers(1e-6, 100))


        if self.hwchan == 1:
            # The following parameters are only available for the SOURCE1

            self.add_parameter('state',
                               label='State',
                               set_cmd='SOUR:LFO{}'.format(self.lfchan)+':STAT {}',
                               get_cmd='SOUR:LFO{}:STAT?'.format(self.lfchan),
                               val_mapping={'ON': 1, 'OFF': 0},
                               vals=vals.Enum('ON', 'OFF'),
                               docstring="The state of the output. Values are 'ON' or 'OFF'.")

            self.add_parameter('offset',
                               label='DC offset voltage',
                               set_cmd='SOUR:LFO{}'.format(self.lfchan)+':OFFS {}',
                               get_cmd='SOUR:LFO{}:OFFS?'.format(self.lfchan),
                               get_parser=float,
                               vals=vals.Numbers(-3.6, +3.6),
                               unit='V',
                               docstring="DC offset voltage in the range from -3.6V to +3.6V.")

            source_val = vals.Enum('LF1', 'LF2', 'NOISE', 'AM', 'FMPM', 'EXT1',
                                   'EXT2', 'LF1B', 'LF2B', 'AMB', 'NOISB', 'FMPMB',
                                   'LF1A', 'LF2A', 'NOISA', 'FMPMA', 'AMA')
            self.add_parameter('source',
                               label='Source',
                               set_cmd='SOUR:LFO{}'.format(self.lfchan)+':SOUR {}',
                               get_cmd='SOUR:LFO{}:SOUR?'.format(self.lfchan),
                               vals=source_val,
                               docstring="""
                               Determines the LF signal to be synchronized, when monitoring is
                               enabled. Values are:
                               'LF1', 'LF2', 'LF1A', 'LF2A', 'LF1B', 'LF2B'
                               --> Selects an internally generated LF signal.
                               'NOISE', 'NOISA', 'NOISB'
                               --> Selects an internally generated noise signal.
                               'EXT1', 'EXT2'
                               --> Selects an externally supplied LF signal.
                               'AM', 'AMA', 'AMB'
                               --> Selects the AM signal.
                               'FMPM', 'FMPMA', 'FMPMB'
                               --> Selects the signal also used by the frequency or phase modulations.
                               """)

            if 'SMW-XXX' in self._parent.options: #TODO: welche Option wird hierfür benötigt?
                self.add_parameter('source_path',
                                   label='Path of the LF output source',
                                   set_cmd='SOUR:LFO{}:SOUR'.format(self.lfchan)+':PATH {}',
                                   get_cmd='SOUR:LFO{}:SOUR:PATH?'.format(self.lfchan),
                                   vals=vals.Enum('A', 'B'))

            self.add_parameter('voltage',
                               label='Output voltage of the LF output',
                               set_cmd='SOUR:LFO{}'.format(self.lfchan)+':VOLT {}',
                               get_cmd='SOUR:LFO{}:VOLT?'.format(self.lfchan),
                               get_parser=float,
                               unit='V',
                               docstring="Output voltage of the LF output. The valid"
                                         " range will be dynamic as shown in the datasheet.")

        if self.lfchan == 1:
            # With other channel numbers the device said: no hardware

            self.add_parameter('period',
                               label='Period',
                               set_cmd=False,
                               get_cmd='SOUR:LFO{}:PER?'.format(self.lfchan),
                               get_parser=float,
                               unit='s',
                               docstring="(ReadOnly) Queries the repetition frequency of the"
                                         " sine signal.")

            if 'SMW-K24' in self._parent.options:
                maxfreq = 20e9 # TODO: dieser Wert wird nicht passen, finde aber nichts dazu
            else:
                maxfreq = 1e9 # Information vom Gerät
            self.add_parameter('frequency',
                               label='Frequency',
                               set_cmd='SOUR{}:LFO{}'.format(self.hwchan, self.lfchan)+':FREQ {}',
                               get_cmd='SOUR{}:LFO{}:FREQ?'.format(self.hwchan, self.lfchan),
                               get_parser=float,
                               vals=vals.Numbers(0.1, maxfreq),
                               unit='Hz',
                               docstring="The Frequency of the LF signal when the mode() is `FIX'."
                                         " Valid range is from 0.1Hz and ends depending on the"
                                         " installed options.")
            # The frequency parameter is only readable for lfchan==1 even if the channel
            # number is given in the communication string.

            self.add_parameter('freq_manual',
                               label='Manual frequency set',
                               set_cmd=partial(self._setfreqvalue),
                               get_cmd='SOUR{}:LFO:FREQ:MAN?'.format(self.hwchan),
                               get_parser=float,
                               unit='Hz',
                               docstring="Manual frequency set only valid in the range given"
                                         " by the parameters freq_min and freq_max.")
            self.add_parameter('freq_min',
                               label='Set minimum for manual frequency',
                               set_cmd=partial(self._setfreqmin),
                               get_cmd='SOUR{}:LFO:FREQ:STAR?'.format(self.hwchan),
                               get_parser=float,
                               vals=vals.Numbers(0.1, 1e6),
                               unit='Hz',
                               docstring="Set minimum for manual frequency from 0.1Hz to 1MHz.")
            self.add_parameter('freq_max',
                               label='Set maximum for manual frequency',
                               set_cmd=partial(self._setfreqmax),
                               get_cmd='SOUR{}:LFO:FREQ:STOP?'.format(self.hwchan),
                               get_parser=float,
                               vals=vals.Numbers(0.1, 1e6),
                               unit='Hz',
                               docstring="Set maximum for manual frequency from 0.1Hz to 1MHz.")

            lfmode = vals.Enum('CW', 'FIX', 'SWE')
            self.add_parameter('mode',
                               label='Mode',
                               set_cmd='SOUR{}:LFO:FREQ:'.format(self.hwchan)+'MODE {}',
                               get_cmd='SOUR{}:LFO:FREQ:MODE?'.format(self.hwchan),
                               vals=lfmode,
                               docstring="""
                               Set the used mode:
                               'FIX' = fixed frequency mode ('CW' is a synonym)
                               'SWE' = set sweep mode (use LFOutputSweep class)
                               """)

    def _setfreqmin(self, val):
        """
        Helper function to set the minimum frequency and store it in a local variable
        """
        self.freqmin = val
        self.write('SOUR{}:LFO:FREQ:STAR {}'.format(self.hwchan, val))

    def _setfreqmax(self, val):
        """
        Helper function to set the maximum frequency and store it in a local variable
        """
        self.freqmax = val
        self.write('SOUR{}:LFO:FREQ:STOP {}'.format(self.hwchan, val))

    def _setfreqvalue(self, val):
        """
        Helper function to set the manual frequency and checks it against the
        local variables before
        """
        if val < self.freqmin or self.freqmax < val:
            raise ValueError('{} is invalid: must be between {} and {}.'
                             .format(repr(val), self.freqmin, self.freqmax))
        self.write('SOUR{}:LFO:FREQ:MAN {}'.format(self.hwchan, val))




class OutputLevelSweep(InstrumentChannel): # doc done *************************
    """
    Combines all the parameters concerning one RF output level (power) sweeping.
    Parameters:
        attenuator: Power attenuator mode for level sweep. Values are:
            'NORM': Performs the level settings in the range of the
                    built-in attenuator.
            'HPOW': Performs the level settings in the high level range.
        dwell: Dwell time for level sweep, valid range is from 0.001s to 100s.
        mode: Cycle mode for level sweep. Values are:
            'AUTO': Each trigger triggers exactly one complete sweep.
            'MAN':  You can trigger every step individually with a command.
            'STEP': Each trigger triggers one sweep step only.
        points: Steps within level sweep range, minimum is 2.
        log_step: Logarithmically determined step size for the RF level sweep,
            valid range is 0.01dB to 139dB.
        shape: Waveform shape for sweep. Valid are 'SAWTOOTH' and 'TRIANGLE'.
        execute: Executes one RF level sweep. Use no braces () here!
        retrace: Activates that the signal changes to the start frequency value
            while it is waiting for the next trigger event. Values are 'ON' and
            'OFF'. You can enable this feature, when you are working with sawtooth
            shapes in sweep mode 'MAN' or 'STEP'.
        running: ReadOnly parameter to get the current sweep state. Return
            values are 'ON' or 'OFF'.
        reset: Resets all active sweeps to the starting point. Use no
            braces () here!
    """
    def __init__(self, parent: 'RohdeSchwarz_SMW200A', name: str, hwchan: int):
        """
        Creates a new OutputLevelSweep
        Args:
            parent: the parent instrument of this channel
            name  : the internal QCoDeS name of this channel
            hwchan: the internal number of the hardware channel used in the communication
        """
        self.hwchan = hwchan
        super().__init__(parent, name)

        self.add_parameter('attenuator',
                           label='Power attenuator mode for level sweep',
                           set_cmd='SOUR{}:SWE:POW:'.format(self.hwchan)+'AMOD {}',
                           get_cmd='SOUR{}:SWE:POW:AMOD?'.format(self.hwchan),
                           vals=vals.Enum('NORM', 'HPOW'),
                           docstring="""
                           Power attenuator mode for level sweep. Values are:
                           'NORM' = Performs the level settings in the range of the built-in
                                    attenuator.
                           'HPOW' = Performs the level settings in the high level range.
                           """)

        self.add_parameter('dwell',
                           label='Dwell time for level sweep',
                           set_cmd='SOUR{}:SWE:POW:'.format(self.hwchan)+'DWEL {}',
                           get_cmd='SOUR{}:SWE:POW:DWEL?'.format(self.hwchan),
                           get_parser=float,
                           vals=vals.Numbers(0.001, 100),
                           unit='s',
                           docstring="Dwell time for level sweep, valid range is from 0.001s"
                                     " to 100s.")

        sweepmode = vals.Enum('AUTO', 'MAN', 'STEP')
        self.add_parameter('mode',
                           label='Cycle mode for level sweep',
                           set_cmd='SOUR{}:SWE:POW:'.format(self.hwchan)+'MODE {}',
                           get_cmd='SOUR{}:SWE:POW:MODE?'.format(self.hwchan),
                           vals=sweepmode,
                           docstring="""
                           Cycle mode for level sweep. Values are:
                           'AUTO' = Each trigger triggers exactly one complete sweep.
                           'MAN'  = You can trigger every step individually with a command.
                           'STEP' = Each trigger triggers one sweep step only.
                           """)

        self.add_parameter('points',
                           label='Steps within level sweep range',
                           set_cmd='SOUR{}:SWE:POW:'.format(self.hwchan)+'POIN {}',
                           get_cmd='SOUR{}:SWE:POW:POIN?'.format(self.hwchan),
                           get_parser=int,
                           vals=vals.Numbers(2),    # Upperlimit=MAXINT
                           docstring="Steps within level sweep range, minimum is 2.")

        self.add_parameter('log_step',
                           label='logarithmically determined step size for the RF level sweep',
                           set_cmd='SOUR{}:SWE:POW:'.format(self.hwchan)+'STEP {}',
                           get_cmd='SOUR{}:SWE:POW:STEP?'.format(self.hwchan),
                           get_parser=float,
                           vals=vals.Numbers(0.01, 139),
                           unit='dB',
                           docstring="Logarithmically determined step size for the RF level"
                                     " sweep, valid range is 0.01dB to 139dB.")

        self.add_parameter('shape',
                           label='Waveform shape for sweep',
                           set_cmd='SOUR{}:SWE:POW:'.format(self.hwchan)+'SHAP {}',
                           get_cmd='SOUR{}:SWE:POW:SHAP?'.format(self.hwchan),
                           vals=vals.Enum('SAWTOOTH', 'TRIANGLE'),
                           docstring="Waveform shape for sweep. Valid are 'SAWTOOTH' and"
                                     " 'TRIANGLE'.")

        self.add_parameter('execute',
                           label='Executes one RF level sweep',
                           call_cmd='SOUR{}:SWE:POW:EXEC'.format(self.hwchan),
                           docstring="Executes one RF level sweep. Use no braces () here!")

        self.add_parameter('retrace',
                           label='Set to start frequency while waiting for trigger  ',
                           set_cmd='SOUR{}:SWE:POW:'.format(self.hwchan)+'RETR {}',
                           get_cmd='SOUR{}:SWE:POW:RETR?'.format(self.hwchan),
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="Activates that the signal changes to the start frequency"
                                     " value while it is waiting for the next trigger event."
                                     " Values are 'ON' and 'OFF'. You can enable this feature,"
                                     " when you are working with sawtooth shapes in sweep mode"
                                     " 'MAN' or 'STEP'.")

        self.add_parameter('running',
                           label='Current sweep state',
                           set_cmd=False,
                           get_cmd='SOUR{}:SWE:POW:RUNN?'.format(self.hwchan),
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="(ReadOnly) Get the current sweep state. Return"
                                     " values are 'ON' or 'OFF'.")

        self.add_parameter('reset',
                           label='Reset the sweep',
                           call_cmd='SOUR{}:SWE:RES'.format(self.hwchan),
                           docstring="Resets all active sweeps to the starting point."
                                     " Use no braces () here!")



class OutputFrequencySweep(InstrumentChannel): # doc done *********************
    """
    Combines all the parameters concerning one RF output frequency sweeping.
    Parameters:
        dwell: Dwell time for frequency sweep. Valid range from 0.001s to 100s.
        mode: Cycle mode for frequency sweep. Values are:
            'AUTO': Each trigger triggers exactly one complete sweep.
            'MAN':  You can trigger every step individually with a command.
            'STEP': Each trigger triggers one sweep step only.
        points: Steps within frequency sweep range, minimum is 2.
        spacing: Calculationmode of frequency intervals. Values are 'LIN' or 'LOG'.
        shape: Waveform shape for sweep. Valid values are 'SAWTOOTH' or 'TRIANGLE'.
        execute: Executes one RF frequency sweep. Use no braces () here!
        retrace: Activates that the signal changes to the start frequency value
            while it is waiting for the next trigger event. Values are 'ON' and
            'OFF'. You can enable this feature, when you are working with sawtooth
            shapes in sweep mode 'MAN' or 'STEP'.
        running: ReadOnly parameter to get the current sweep state. Return
            values are 'ON' or 'OFF'.
        log_step: Logarithmically determined step size for the RF frequency
            sweep. Valid range is 0.01 to 100.
        lin_step: Step size for linear RF frequency sweep. The minimum is 0.01
            and the maximum is the sweep_span of the output channel and will
            be read during the set lin_step command.
        reset: Resets all active sweeps to the starting point. Use no
            braces () here!
    """
    def __init__(self, parent: 'RohdeSchwarz_SMW200A', name: str, hwchan: int):
        """
        Creates a new OutputFrequencySweep
        Args:
            parent: the parent instrument of this channel
            name  : the internal QCoDeS name of this channel
            hwchan: the internal number of the hardware channel used in the communication
        """
        self.hwchan = hwchan

        super().__init__(parent, name)

        self.add_parameter('dwell',
                           label='Dwell time for frequency sweep',
                           set_cmd='SOUR{}:SWE:'.format(self.hwchan)+'DWEL {}',
                           get_cmd='SOUR{}:SWE:DWEL?'.format(self.hwchan),
                           get_parser=float,
                           vals=vals.Numbers(0.001, 100),
                           unit='s',
                           docstring="Dwell time for frequency sweep. Valid range from 0.001s"
                                     " to 100s.")

        sweepmode = vals.Enum('AUTO', 'MAN', 'STEP')
        self.add_parameter('mode',
                           label='Cycle mode for frequency sweep',
                           set_cmd='SOUR{}:SWE:'.format(self.hwchan)+'MODE {}',
                           get_cmd='SOUR{}:SWE:MODE?'.format(self.hwchan),
                           vals=sweepmode,
                           docstring="""
                           Cycle mode for frequency sweep. Values are:
                           'AUTO' = Each trigger triggers exactly one complete sweep.
                           'MAN'  = You can trigger every step individually with a command.
                           'STEP' = Each trigger triggers one sweep step only.
                           """)

        self.add_parameter('points',
                           label='Steps within frequency sweep range',
                           set_cmd='SOUR{}:SWE:'.format(self.hwchan)+'POIN {}',
                           get_cmd='SOUR{}:SWE:POIN?'.format(self.hwchan),
                           get_parser=int,
                           vals=vals.Numbers(2),    # Upperlimit=MAXINT
                           docstring="Steps within frequency sweep range, minimum is 2.")

        self.add_parameter('spacing',
                           label='calculationmode of frequency intervals',
                           set_cmd='SOUR{}:SWE:'.format(self.hwchan)+'SPAC {}',
                           get_cmd='SOUR{}:SWE:SPAC?'.format(self.hwchan),
                           vals=vals.Enum('LIN', 'LOG'),
                           docstring="Calculationmode of frequency intervals. Values are 'LIN'"
                                     " or 'LOG'.")

        self.add_parameter('shape',
                           label='Waveform shape for sweep',
                           set_cmd='SOUR{}:SWE:'.format(self.hwchan)+'SHAP {}',
                           get_cmd='SOUR{}:SWE:SHAP?'.format(self.hwchan),
                           vals=vals.Enum('SAWTOOTH', 'TRIANGLE'),
                           docstring="Waveform shape for sweep. Valid values are 'SAWTOOTH' or"
                                     " 'TRIANGLE'.")

        self.add_parameter('execute',
                           label='Executes one RF frequency sweep',
                           call_cmd='SOUR{}:SWE:EXEC'.format(self.hwchan),
                           docstring="Executes one RF frequency sweep. Use no braces () here!")

        self.add_parameter('retrace',
                           label='Set to start frequency while waiting for trigger  ',
                           set_cmd='SOUR{}:SWE:'.format(self.hwchan)+'RETR {}',
                           get_cmd='SOUR{}:SWE:RETR?'.format(self.hwchan),
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="Activates that the signal changes to the start frequency"
                                     " value while it is waiting for the next trigger event."
                                     " when you are working Values are 'ON' and 'OFF'. You can"
                                     " enable this feature, with sawtooth shapes in sweep mode"
                                     " 'MAN' or 'STEP'.")

        self.add_parameter('running',
                           label='Current sweep state',
                           set_cmd=False,
                           get_cmd='SOUR{}:SWE:RUNN?'.format(self.hwchan),
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="(ReadOnly) Get the current sweep state. Return"
                                     " values are 'ON' or 'OFF'.")

        self.add_parameter('log_step',
                           label='logarithmically determined step size for the RF freq sweep',
                           set_cmd='SOUR{}:SWE:STEP:'.format(self.hwchan)+'LOG {}',
                           get_cmd='SOUR{}:SWE:STEP:LOG?'.format(self.hwchan),
                           get_parser=float,
                           vals=vals.Numbers(0.01, 100),
                           unit='%',
                           docstring="Logarithmically determined step size for the RF"
                                     " frequency sweep. Valid range is 0.01 to 100.")

        self.add_parameter('lin_step',
                           label='step size for linear RF freq sweep',
                           set_cmd=partial(self._setlinstep),
                           get_cmd='SOUR{}:SWE:STEP?'.format(self.hwchan),
                           get_parser=float,
                           vals=vals.Numbers(0.01),
                           unit='Hz',
                           docstring="Step size for linear RF frequency sweep. The"
                                     " minimum is 0.01 and the maximum is the sweep_span"
                                     " of the output channel and will be read during the"
                                     " set lin_step command.")

        self.add_parameter('reset',
                           label='Reset the sweep',
                           call_cmd='SOUR{}:SWE:RES'.format(self.hwchan),
                           docstring="Resets all active sweeps to the starting point."
                                     " Use no braces () here!")

    def _setlinstep(self, val):
        """
        Helper function to check the maximum allowed value for the step
        """
        maxfreq = float(self.ask('SOUR{}:FREQ:SPAN?'.format(self.hwchan)))
        if val > maxfreq:
            raise ValueError('{} is invalid: must be between '
                             '0.01 and {} inclusive.'.format(repr(val), maxfreq))
        self.write('SOUR{}:SWE:STEP {}'.format(self.hwchan, val))





class OutputChannel(InstrumentChannel): # doc done ****************************
    """
    Combines all the parameters concerning one RF output.
    Parameters:
        state: actives/deactivates the RF output. Values are 'ON' and 'OFF'.
        frequency: set/read the main frequency of the oscillator.
        level: set/read the output power level.
        mode: selects the mode of the oscillator. Valid values are:
            FIX  = fixed frequency mode (CW is a synonym)
            SWE  = set sweep mode (use sweep_start/sweep_stop/sweep_center/sweep_span)
            LIST = use a special loadable list of frequencies - the list functions
                    are not yet implemented here.
        sweep_center: set/read the center frequency of the sweep.
        sweep_span: set/read the span of frequency sweep range.
        sweep_start: set/read the start frequency of the sweep.
        sweep_stop: set/read the stop frequency of the sweep.
        losc_input: read the LOscillator input frequency (ReadOnly).
        losc_mode: set/read the LOscillator mode. Valid values are:
            INT  = A&B Internal / Internal (one path instrument)
                    Uses the internal oscillator signal in both paths.
            EXT  = A External & B Internal (one path instrument)
                    Uses an external signal in path A. B uses its internal signal.
            COUP = A Internal & A->B Coupled
                    Assigns the internal oscillator signal of path A also to path B.
            ECO  = A External & A->B Coupled
                    Assigns an externally supplied signal to both paths.
            BOFF = A Internal & B RF Off
                    Uses the internal local oscillator signal of path A, if the
                    selected frequency exceeds the maximum frequency of path B.
            EBOF = A External & B RF Off
                    Uses the LO IN signal for path A, if the selected RF frequency
                    exceeds the maximum frequency of path B.
            AOFF = A RF Off & B External
                    Uses the LO IN signal for path B, if the selected RF frequency
                    exceeds the maximum frequency of path A.
        losc_output: read the LOscillator output frequency (ReadOnly).
        losc_state: set/read the LOscillator state. Valid values are 'ON' and 'OFF'.
    """
    def __init__(self, parent: 'RohdeSchwarz_SMW200A', name: str, chnum: int):
        """
        Creates a new OutputChannel which is used for RF output
        Args:
            parent: the parent instrument of this channel
            name  : the internal QCoDeS name of this channel
            chnum : the internal number of the channel used in the communication
        """

        self.chnum = chnum
        super().__init__(parent, name)
        if self.chnum == 1:
            if 'SMW-B120' in self._parent.options:
                maxfreq = 20e9
            elif 'SMW-B103' in self._parent.options:
                maxfreq = 3e9
            elif 'SMW-B106' in self._parent.options:
                maxfreq = 6e9
            elif 'SMW-B112' in self._parent.options:
                maxfreq = 12.75e9
            elif 'SMW-B131' in self._parent.options:
                maxfreq = 31.8e9
            elif 'SMW-B140' in self._parent.options:
                maxfreq = 40e9
            else:
                raise RuntimeError("Missing frequency option for first RF path") #maxfreq = 1e9
        elif self.chnum == 2:
            if 'SMW-B203' in self._parent.options:
                maxfreq = 3e9
            elif 'SMW-B206' in self._parent.options:
                maxfreq = 6e9
            elif 'SMW-B207' in self._parent.options:
                maxfreq = 7.5e9
            elif 'SMW-B212' in self._parent.options:
                maxfreq = 12.75e9
            elif 'SMW-220' in self._parent.options:
                maxfreq = 20e9
            else:
                raise RuntimeError("Missing frequency option for second RF path")
        self.add_parameter('frequency',
                           label='Frequency',
                           set_cmd='SOUR{}'.format(self.chnum)+':FREQ {}',
                           get_cmd='SOUR{}:FREQ?'.format(self.chnum),
                           get_parser=float,
                           vals=vals.Numbers(100e3, maxfreq),
                           unit='Hz',
                           docstring="The main frequency of the oscillator."
                                     " The minimum is 100kHz and the maximum"
                                     " depends on the installed option.")

        # TODO: sind die folgenden Parameter notwendig/sinnvoll?
        # 'offset' This value represents the frequency shift of a downstream
        #          instrument, like for example a mixer.
        # 'multiplier': This value represents the multiplication factor of a
        #          downstream instrument, like for example a multiplier.

        self.add_parameter('level',
                           label='Level',
                           set_cmd='SOUR{}:'.format(self.chnum)+'POW:POW {}',
                           get_cmd='SOUR{}:POW:POW?'.format(self.chnum),
                           get_parser=float,
                           vals=vals.Numbers(-145, 30),
                           unit='dBm',
                           docstring="The output power level. Valid values are"
                                     " from -145dBm up to 30dBm.")

        self.add_parameter('state',
                           label='State',
                           set_cmd='OUTP{}:'.format(self.chnum)+'STAT {}',
                           get_cmd='OUTP{}:STAT?'.format(self.chnum),
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="actives/deactivates the RF output. Values are 'ON' and 'OFF'")

        rfmode = vals.Enum('CW', 'FIX', 'SWE', 'LIST')
        self.add_parameter('mode',
                           label='Mode',
                           set_cmd='SOUR{}:FREQ:'.format(self.chnum)+'MODE {}',
                           get_cmd='SOUR{}:FREQ:MODE?'.format(self.chnum),
                           vals=rfmode,
                           docstring="""
                           Selects the mode of the oscillator. Valid values are:
                           'FIX'  = fixed frequency mode (CW is a synonym)
                           'SWE'  = set sweep mode (use start/stop/center/span)
                           'LIST' = use a special loadable list of frequencies (nyi here)
                           """)

        # Parameter for the sweep mode
        self.add_parameter('sweep_center',
                           label='Center frequency of the sweep',
                           set_cmd='SOUR{}:FREQ:'.format(self.chnum)+'CENT {}',
                           get_cmd='SOUR{}:FREQ:CENT?'.format(self.chnum),
                           get_parser=float,
                           vals=vals.Numbers(300e3, maxfreq),
                           unit='Hz',
                           docstring="""
                           The center frequency of the sweep.
                           Use sweep_center and sweep_span or
                           use sweep_start and sweep_stop
                           to define the sweep range.
                           """)

        self.add_parameter('sweep_span',
                           label='Span of frequency sweep range',
                           set_cmd='SOUR{}:FREQ:'.format(self.chnum)+'SPAN {}',
                           get_cmd='SOUR{}:FREQ:SPAN?'.format(self.chnum),
                           get_parser=float,
                           vals=vals.Numbers(0, maxfreq),
                           unit='Hz',
                           docstring="""
                           The span of frequency sweep range.
                           Use sweep_center and sweep_span or
                           use sweep_start and sweep_stop
                           to define the sweep range.
                           """)

        self.add_parameter('sweep_start',
                           label='Start frequency of the sweep',
                           set_cmd='SOUR{}:FREQ:'.format(self.chnum)+'STAR {}',
                           get_cmd='SOUR{}:FREQ:STAR?'.format(self.chnum),
                           get_parser=float,
                           vals=vals.Numbers(300e3, maxfreq),
                           unit='Hz',
                           docstring="""
                           The start frequency of the sweep.
                           Use sweep_start and sweep_stop or
                           use sweep_center and sweep_span
                           to define the sweep range.
                           """)

        self.add_parameter('sweep_stop',
                           label='Stop frequency of the sweep',
                           set_cmd='SOUR{}:FREQ:'.format(self.chnum)+'STOP {}',
                           get_cmd='SOUR{}:FREQ:STOP?'.format(self.chnum),
                           get_parser=float,
                           vals=vals.Numbers(300e3, maxfreq),
                           unit='Hz',
                           docstring="""
                           The stop frequency of the sweep.
                           Use sweep_start and sweep_stop or
                           use sweep_center and sweep_span
                           to define the sweep range.
                           """)

        # Parameter for the LOSCILLATOR
        self.add_parameter('losc_input',
                           label='LOscillator input frequency',
                           set_cmd=False,
                           get_cmd='SOUR{}:FREQ:LOSC:INP:FREQ?'.format(self.chnum),
                           get_parser=float,
                           unit='Hz',
                           docstring="(ReadOnly) Read the LOscillator input frequency.")

        lomode = vals.Enum('INT', 'EXT', 'COUP', 'ECO', 'BOFF', 'EBOF', 'AOFF')
        self.add_parameter('losc_mode',
                           label='LOscillator mode',
                           set_cmd='SOUR{}:FREQ:LOSC:'.format(self.chnum)+'MODE {}',
                           get_cmd='SOUR{}:FREQ:LOSC:MODE?'.format(self.chnum),
                           vals=lomode,
                           docstring="""
                           The LOscillator mode. Valid values are:
                           'INT'  = A&B Internal / Internal (one path instrument) - Uses the internal oscillator signal in both paths.
                           'EXT'  = A External & B Internal (one path instrument) - Uses an external signal in path A. B uses its internal signal.
                           'COUP' = A Internal & A->B Coupled - Assigns the internal oscillator signal of path A also to path B.
                           'ECO'  = A External & A->B Coupled - Assigns an externally supplied signal to both paths.
                           'BOFF' = A Internal & B RF Off - Uses the internal local oscillator signal of path A, if the selected frequency exceeds the maximum frequency of path B.
                           'EBOF' = A External & B RF Off - Uses the LO IN signal for path A, if the selected RF frequency exceeds the maximum frequency of path B.
                           'AOFF' = A RF Off & B External - Uses the LO IN signal for path B, if the selected RF frequency exceeds the maximum frequency of path A.
                           """)

        self.add_parameter('losc_output',
                           label='LOscillator output frequency',
                           set_cmd=False,
                           get_cmd='SOUR{}:FREQ:LOSC:OUTP:FREQ?'.format(self.chnum),
                           get_parser=float,
                           unit='Hz',
                           docstring="(ReadOnly) Read the LOscillator output frequency.")

        self.add_parameter('losc_state',
                           label='LOscillator state',
                           set_cmd='SOUR{}:FREQ:LOSC:OUTP:'.format(self.chnum)+'STAT {}',
                           get_cmd='SOUR{}:FREQ:LOSC:OUTP:STAT?'.format(self.chnum),
                           val_mapping={'ON': 1, 'OFF': 0},
                           vals=vals.Enum('ON', 'OFF'),
                           docstring="Set the LOscillator state. Valid values are 'ON' and 'OFF'.")



class RohdeSchwarz_SMW200A(VisaInstrument):
#class RohdeSchwarz_SMW200A(MockVisa):
    """
    This is the qcodes driver for the Rohde & Schwarz SMW200A vector signal
    generator.

    Status:
        coding: almost finished
        communication tests: done
        usage in experiment: outstanding
    """

    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, **kwargs)

        # for security check the ID from the device
        self.idn = self.ask("*IDN?").strip()
        if not self.idn.startswith("Rohde&Schwarz,SMW200A,"):
            raise RuntimeError("Invalid device ID found: "+self.idn)

        log.debug(__name__ + ' : Initializing instrument ' + self.idn)

        # save the option flags as a string array for later usage
        self.options = self.ask("*OPT?").strip().split(",")
        self.add_parameter('options',
                           label='Options',
                           set_cmd=False,
                           get_cmd=self.get_options,
                           docstring="(ReadOnly) List of installed options.")

        # RF output submodules
        rfchannels = ChannelList(self, "OutputChannels", OutputChannel,
                                 snapshotable=False)
        if 'SMW-B203' in self.options or 'SMW-B206' in self.options \
                or 'SMW-B207' in self.options or 'SMW-B212' in self.options \
                or 'SMW-B220' in self.options:
            self.rfoutput_no = 2
        else:
            self.rfoutput_no = 1
        for chnum in range(1, self.rfoutput_no+1):
            name = 'rfoutput{}'.format(chnum)
            rfchannel = OutputChannel(self, name, chnum)
            rfchannels.append(rfchannel)
            self.add_submodule(name, rfchannel)
        rfchannels.lock()
        self.add_submodule('output_channels', rfchannels)

        # RF output sweep submodules (for Level and Frequency)
        rflevelsweeps = ChannelList(self, "OutputLevelSweep", OutputLevelSweep,
                                    snapshotable=False)
        for rfnum in range(1, self.rfoutput_no+1):
            name = 'level_sweep{}'.format(rfnum)
            rfsweep = OutputLevelSweep(self, name, rfnum)
            rflevelsweeps.append(rfsweep)
            self.add_submodule(name, rfsweep)
        rflevelsweeps.lock()
        self.add_submodule('rflevelsweep_channels', rflevelsweeps)

        rffreqsweeps = ChannelList(self, "OutputFrequencySweep", OutputFrequencySweep,
                                   snapshotable=False)
        for rfnum in range(1, self.rfoutput_no+1):
            name = 'freq_sweep{}'.format(rfnum)
            rfsweep = OutputFrequencySweep(self, name, rfnum)
            rffreqsweeps.append(rfsweep)
            self.add_submodule(name, rfsweep)
        rffreqsweeps.lock()
        self.add_submodule('rffreqsweep_channels', rffreqsweeps)

        # LF output submodules
        lfchannels = ChannelList(self, "LFOutputChannels", LFOutputChannel,
                                 snapshotable=False)
        self.lfoutput_no = 2 # TODO: wie fragen wir das ab?
        for rfnum in range(1, self.rfoutput_no+1):
            for lfnum in range(1, self.lfoutput_no+1):
                name = 'lf{}output{}'.format(rfnum, lfnum)
                lfchannel = LFOutputChannel(self, name, rfnum, lfnum)
                lfchannels.append(lfchannel)
                self.add_submodule(name, lfchannel)
        lfchannels.lock()
        self.add_submodule('lfoutput_channels', lfchannels)

        # LF output sweep submodules
        lfsweeps = ChannelList(self, "LFOutputSweep", LFOutputSweep,
                               snapshotable=False)
        for rfnum in range(1, self.rfoutput_no+1):
            name = 'lf{}sweep'.format(rfnum)
            lfsweep = LFOutputSweep(self, name, rfnum)
            lfsweeps.append(lfsweep)
            self.add_submodule(name, lfsweep)
        lfsweeps.lock()
        self.add_submodule('lfsweep_channels', lfsweeps)

        #Amplitude Modulation submodules
        amchannels = ChannelList(self, "AMChannels", AmplitudeModulation,
                                 snapshotable=False)
        self.am_no = 2
        for rfnum in range(1, self.rfoutput_no+1):
            for chnum in range(1, self.am_no+1):
                name = 'am{}_{}'.format(rfnum, chnum)
                amchannel = AmplitudeModulation(self, name, rfnum, chnum)
                amchannels.append(amchannel)
                self.add_submodule(name, amchannel)
        amchannels.lock()
        self.add_submodule('am_channels', amchannels)

        if 'SMW-B22' or 'SMW-B20' in self.options:
            #Frequency Modulation submodules
            fmchannels = ChannelList(self, "FMChannels", FrequencyModulation,
                                     snapshotable=False)
            self.fm_no = 2
            for rfnum in range(1, self.rfoutput_no+1):
                for chnum in range(1, self.fm_no+1):
                    name = 'fm{}_{}'.format(rfnum, chnum)
                    fmchannel = FrequencyModulation(self, name, rfnum, chnum)
                    fmchannels.append(fmchannel)
                    self.add_submodule(name, fmchannel)
            fmchannels.lock()
            self.add_submodule('fm_channels', fmchannels)

            #Phase Modulation submodules
            pmchannels = ChannelList(self, "PMChannels", PhaseModulation,
                                     snapshotable=False)
            self.pm_no = 2
            for rfnum in range(1, self.rfoutput_no+1):
                for chnum in range(1, self.pm_no+1):
                    name = 'pm{}_{}'.format(rfnum, chnum)
                    pmchannel = PhaseModulation(self, name, rfnum, chnum)
                    pmchannels.append(pmchannel)
                    self.add_submodule(name, pmchannel)
            pmchannels.lock()
            self.add_submodule('pm_channels', pmchannels)

        #Pulse modulation submodule
        if 'SMW-K22' in self.options:
            for rfnum in range(1, self.rfoutput_no+1):
                name = 'pulsemod{}'.format(rfnum)
                pulsemchannel = PulseModulation(self, name, rfnum)
                self.add_submodule(name, pulsemchannel)

            if 'SMW-K23' in self.options:
                #Pulse generator
                pgenchannels = ChannelList(self, "PGenChannels", PulseGenerator,
                                           snapshotable=False)
                self.pgen_no = 1
                for chnum in range(1, self.pgen_no+1):
                    name = 'pulsegen{}'.format(chnum)
                    pgenchannel = PulseGenerator(self, name, chnum)
                    pgenchannels.append(pgenchannel)
                    self.add_submodule(name, pgenchannel)
                pgenchannels.lock()
                self.add_submodule('pgen_channels', pgenchannels)
                self.add_parameter('genTriggerPulse',
                                   label='Trigger Pulse',
                                   set_cmd=self.genTriggerPulse,
                                   get_cmd=False,
                                   docstring="(WriteOnly) Generates on trigger pulse.")

        #IQ modulation submodule
        for rfnum in range(1, self.rfoutput_no+1):
            name = 'iqmod{}'.format(rfnum)
            IQmodchannel = IQModulation(self, name, rfnum)
            self.add_submodule(name, IQmodchannel)

        #analog IQ outputs submodule
        iqchannels = ChannelList(self, "IQChannels", IQChannel, snapshotable=False)
        self.iqoutput_no = 2
        for iq_num in range(1, self.iqoutput_no+1):
            name = 'iqoutput{}'.format(iq_num)
            iqchannel = IQChannel(self, name, iq_num)
            iqchannels.append(iqchannel)
            self.add_submodule(name, iqchannel)
        iqchannels.lock()
        self.add_submodule('iqoutput_channels', iqchannels)


    def get_id(self):
        """
        Get the device identification
        Args:
            None
        Output:
            Strings from the *IDN? command
        """
        return self.idn


    def get_options(self):
        """
        Get the device option flags
        Args:
            None
        Output:
            Stringarray with the options installed in the device
        """
        return self.options


    def close(self):
        """
        Close the connection
        Args:
            None
        Output:
            None
        """
        log.info(__name__ + ': close connection')
        super().close()


    def reset(self):
        """
        Resets the instrument to default values.
        Args:
            None
        Output:
            None
        """
        log.info(__name__ + ': Resetting instrument')
        self.write('*RST')


    def get_error(self):
        """
        Reads the errors from the device
        Args:
            None
        Output:
            List of strings containing error number and string representation
        """
        #count = int( self.ask('SYST:ERR:COUNT?') )
        #print( "Error count: ", count )
        retval = self.ask('SYST:ERR:ALL?').strip().split("\n")
        #print( "Error strings:", retval )
        return retval


    def gen_trigger_pulse(self, val):
        """
        Function to generate a trigger pulse. The port for this is always defined
        by the user. And the Options SMW-K22 and SMW-K23 must be installed.
        Args:
            val: the time value in seconds (tested with 0.0001)
        """
        if not 'SMW-K22' in self.options or not 'SMW-K23' in self.options:
            raise RuntimeError('Invalid options installed (SMW-K22 and SMW-K23 needed)')
        # get the required submodules
        pgen = self.submodules['pulsegen1']
        pmod = self.submodules['pulsemod1']
        # configure the submodules
        pgen.polarity('NORM')
        pmod.delay(0)
        pmod.mode('SING')
        pmod.trigger_mode('AUTO')
        # calculate the period to the third of the requested width
        if val < 0.1:
            # if the requested width is too short, make it longer
            pmod.period(val + 0.3)
        else:
            pmod.period(val * 3.0)
        pmod.width(val)
        # active the pulse
        pgen.output('ON')
        # wait some time longer than the pulse but shorter than the period
        if val < 0.1:
            time.sleep(val + 0.1)
        else:
            time.sleep(val * 1.4)
        # deactivate the output to prevent the second pulse
        pgen.output('OFF')



    def getall(self, submod="*"):
        """
        Read all parameters and retun them to the caller. This will scan all
        submodules with all parameters, so in this function no changes are
        necessary for new modules or parameters.
        Args:
            submod: (optional) returns only the parameters for this submodule
        Output:
            dict with all parameters, the key is the modulename and the parametername
        """
        retval = {}
        if submod == "*":
            # ID and options only if all modules are returned
            retval.update({"ID": self.idn})
            retval.update({"Options": self.options})

        for m in self.submodules:
            mod = self.submodules[m]
            if not isinstance(mod, ChannelList) and submod in ("*", m):
                for p in mod.parameters:
                    par = mod.parameters[p]
                    try:
                        if par.unit.isEmpty():
                            val = str(par()).strip()
                        else:
                            val = str(par()).strip() + " " + par.unit
                    except:
                        val = "** not readable **"
                    retval.update({m + "." + p: val})

        return retval
