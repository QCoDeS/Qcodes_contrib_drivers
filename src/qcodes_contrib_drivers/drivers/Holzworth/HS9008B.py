# This Python file uses the following encoding: utf-8
# Valentin John, spring 2021
# Simon Zihlmannr <zihlmann.simon@gmail.com>, spring 2021
# Tongyu Zhao <ty.zhao.work@gmail.com>, spring 2022
import warnings
import pyvisa as visa

from qcodes import Instrument, VisaInstrument
from qcodes.instrument.channel import InstrumentChannel
from qcodes.utils.validators import Numbers, Enum
from qcodes.utils.helpers import create_on_off_val_mapping


class HS9008BChannel(InstrumentChannel):
    """
    Class to hold the Holzworth HS9008B channels, i.e.
    CH1, CH2, ...
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

        self.channel = channel

        self._min_f = self._parse_f_unit(
                      self.ask_raw(':{}:Freq:MIN?'.format(channel)))
        self._max_f = self._parse_f_unit(
                      self.ask_raw(':{}:Freq:MAX?'.format(channel)))
        self._min_pwr = self._parse_pwr_unit(
                        self.ask_raw(':{}:PWR:MIN?'.format(channel)))
        self._max_pwr = self._parse_pwr_unit(
                        self.ask_raw(':{}:PWR:MAX?'.format(channel)))
        self._min_phase = self._parse_phase_unit(
                          self.ask_raw(':{}:PHASE:MIN?'.format(channel)))
        self._max_phase = self._parse_phase_unit(
                          self.ask_raw(':{}:PHASE:MAX?'.format(channel)))

        self.add_parameter(name='state',
                           label='State',
                           get_parser=str,
                           get_cmd=':{}:PWR:RF?'.format(self.channel),
                           set_cmd=self._set_state,
                           val_mapping=create_on_off_val_mapping(on_val='ON',
                                                                 off_val='OFF')
                           )

        self.add_parameter(name='power',
                           label='Power',
                           get_parser=float,
                           get_cmd=':{}:PWR?'.format(self.channel),
                           set_cmd= self._set_pwr,
                           unit='dBm',
                           vals=Numbers(min_value=self._min_pwr,
                                        max_value=self._max_pwr)
                           )

        self.add_parameter(name='frequency',
                           label='Frequency',
                           get_parser=float,
                           get_cmd=self._get_f,
                           set_cmd= self._set_f,
                           unit='Hz',
                           vals=Numbers(min_value=self._min_f,
                                        max_value=self._max_f)
                           )

        self.add_parameter(name='phase',
                           label='Phase',
                           get_parser=float,
                           get_cmd=':{}:PHASE?'.format(self.channel),
                           set_cmd= self._set_phase,
                           unit='deg',
                           vals=Numbers(min_value=self._min_phase,
                                        max_value=self._max_phase)
                           )

        self.add_parameter(name='temp',
                           label='Temperature',
                           get_parser=float,
                           get_cmd=self._get_temp,
                           unit='C')

    def _parse_f_unit(self, raw_str:str) -> float:
        """
        Function that converts strings consisting of a number and a unit into
        frequencies in Hz and returing it as a float:

        Args:
            raw_str: String of the form '100 MHz'
        """
        f, unit = raw_str.split(' ')
        unit_dict = {
            'GHz': 1e9,
            'MHz': 1e6,
            'kHz': 1e3
        }
        if unit not in unit_dict.keys():
            raise RuntimeError('{} is not in {}. Cannot parse {}.'
                               .format(unit, unit_dict.keys(), unit))
        frequency = float(f) * unit_dict[unit]
        return frequency


    def _parse_pwr_unit(self, raw_str:str) -> float:
        """
        Function that converts strings consisting of a number only or
        a number plus a unit dBm into a float in dBm:

        Args:
            raw_str: String of the form '-10' or '-10 dBm'
        """
        try:
            power = float(raw_str)
        except:
            pwr, unit = raw_str.split(' ')
            power = float(pwr)
        return power

    def _parse_phase_unit(self, raw_str:str) -> float:
        """
        Function that converts strings consisting of a number only or
        a number plus a unit deg into a float in deg:

        Args:
            raw_str: String of the form '90' or '90deg'
        """
        try:
            phase = float(raw_str)
        except:
            phase = float(raw_str[:-3])
        return phase

    def _set_state(self, st:str) -> None:
        """
        Function that turns the channel on or off

        Args:
            st (str): accepts as argument 'ON' or 'OFF', only in CAPITAL
            letters

        Raises:
            RuntimeError: Function compares reply from instrument and raises
            RuntimeError if state setting was not performed sucessfully
        """
        write_str = ':{}:PWR:RF:'.format(self.channel) + str(st)
        read_str = self.ask(write_str)
        if read_str != 'RF POWER '+str(st):
            raise RuntimeError(
                         '{} is not \'State Set\'. Setting state did not work'
                         .format(read_str))

    def _get_f(self) -> float:
        """
        Getting the fundamental frequency from the RF source channel
        in Hz. Instrument gives frequency as a string in the format
        '800.0 MHz'.

        Returns:
            float: frequency in Hz, e.g. 0.8e9
        """
        raw_str = self.ask(':{}:FREQ?'.format(self.channel))
        return self._parse_f_unit(raw_str)

    def _set_f(self, f:float) -> None:
        """Function that sets the frequency of a channel.

        Args:
            f (float): RF source channel fundamental frequency in Hz

        Raises:
            RuntimeError: Instrument tells us if frequency has been set
            correctly.
            Otherwise RuntimeError.
        """
        write_str = ':{}:FREQ:'.format(self.channel) + str(f/1e9) + 'GHz'
        read_str = self.ask(write_str)
        if read_str != 'Frequency Set':
            raise RuntimeError(
                 '{} is not \'Frequency Set\'. Setting frequency did not work'
                 .format(read_str))

    def _set_pwr(self, pwr:float) -> None:
        """Setting the power of the RF source channel in dBm.

        Args:
            pwr (float): power in dBm

        Raises:
            RuntimeError: Instrument tells us if frequency has been set
            correctly.
            Otherwise RuntimeError.
        """
        write_str = f':{self.channel}:PWR:{pwr:.2f}dBm'
        read_str = self.ask(write_str)
        if read_str != f'Power Set to {pwr:.2f} dBm':
            raise RuntimeError(
                         f'{read_str} is not \'Power Set to {pwr:.2f} dBm\'. Setting power did not work')

    def _set_phase(self, ph:float) -> None:
        """Setting the phase in deg.

        Args:
            ph (float): phase angle in deg

        Raises:
            RuntimeError: Instrument tells us if phase has been set correctly.
            Otherwise RuntimeError.
        """
        write_str = ':{}:PHASE:'.format(self.channel) + str(float(ph)) + 'deg'
        read_str = self.ask(write_str)
        if read_str != 'Phase Set':
            raise RuntimeError(
                         '{} is not \'Phase Set\'. Setting phase did not work'
                         .format(read_str))

    def _get_temp(self) -> float:
        """Getting the temperature of a channel input/output in deg Celsius.
        Instrument returns string in the form 'Temp = 54C'

        Returns:
            float: Temperature in C, e.g. 54
        """
        raw_str = self.ask(':{}:TEMP?'.format(self.channel))
        T = raw_str.split(' ')[-1][:-1]
        return float(T)

class HS9008B(VisaInstrument):
    """
    QCoDeS driver for the Holzworth HS9008B RF synthesizer.
    """
    def __init__(self, name: str, address: str, **kwargs) -> None:
        """
        Args:
            name: Name to use internally in QCoDeS
            address: VISA ressource address
        """
        super().__init__(name, address, terminator='', **kwargs)

        self.add_parameter(name='channel_names',
                           label='Channels',
                           get_parser=str,
                           get_cmd=self._get_channels) # No of ports

        self.add_parameter(name='ref',
                           label='Reference',
                           get_parser=str,
                           get_cmd=':REF:STATUS?',
                           set_cmd=self._set_ref,
                           vals=Enum('ext10', 'ext100', 'int100'))

        self.add_parameter(name='ref_locked',
                           label='Clock Locked',
                           get_parser=str,
                           get_cmd=self._get_ref_locked)

        model = self.IDN()['model']
        knownmodels = ['HS9008B']
        # Driver was tested with 'HS9008B'.
        if model not in knownmodels:
            kmstring = ('{}, '*(len(knownmodels)-1)).format(*knownmodels[:-1])
            kmstring += 'and {}.'.format(knownmodels[-1])
            warnings.warn('This model {} is unknown and might not be'
                          'compatible with the driver. Known models'
                          'are: {}'.format(model, kmstring))

        # Add the channel to the instrument
        channels = self.ask_raw(':ATTACH?').split(':')[2:-1]
        for ch_name in channels:
            channel = HS9008BChannel(self, ch_name, ch_name)
            self.add_submodule(ch_name, channel)

        self.connect_message()

    def set_address(self, address: str) -> None:
        """
        Set the address for this instrument.

        Args:
            address: The visa resource name to use to connect. The address
                should be the actual address and just that. If you wish to
                change the backend for VISA, use the self.visalib attribute
                (and then call this function).
        """

        # in case we're changing the address - close the old handle first
        if getattr(self, 'visa_handle', None):
            self.visa_handle.close()

        if self.visalib:
            self.visa_log.info('Opening PyVISA Resource Manager with visalib:'
                          ' {}'.format(self.visalib))
            resource_manager = visa.ResourceManager(self.visalib)
            self.visabackend = self.visalib.split('@')[1]
        else:
            self.visa_log.info('Opening PyVISA Resource Manager with default'
                          ' backend.')
            resource_manager = visa.ResourceManager()
            self.visabackend = 'ni'

        self.visa_log.info(f'Opening PyVISA resource at address: {address}')
        resource = resource_manager.open_resource(address, send_end=False)
        if not isinstance(resource, visa.resources.MessageBasedResource):
            raise TypeError("QCoDeS only support MessageBasedResource "
                            "Visa resources")
        self.visa_handle = resource
        self._address = address

    def _get_channels(self) -> list:
        """Getting the available channel names. Instrument returns string
        in the form :REF:CH1:CH2:'

        Returns:
            list: list with available channel names, e.g. ['CH1', 'CH2']
        """
        raw_str = self.ask(':ATTACH?')
        channels = raw_str.split(':')[2:-1]
        return channels

    def _set_ref(self, f_ref_str:str) -> None:
        """
        Function that sets clock reference

        Args:
            f_ref_str (str): accepts as argument ext10, ext100 and int100,
                             for internal and external reference with a clock
                             reference frequency of 10 or 100 MHz

        Raises:
            RuntimeError: Function compares reply from instrument and raises
                          RuntimeError if reference setting was not performed
                          sucessfully
        """
        location = f_ref_str[:3]
        f_ref = f_ref_str[3:]
        write_str = ':REF:{}:{}MHz'.format(location.swapcase(), str(f_ref))
        read_str = self.ask(write_str)
        PLL = {'ext10':'PLL Enabled',
               'ext100':'PLL Enabled',
               'int100':'PLL Disabled'
               }
        response = 'Reference Set to {}MHz {}ernal, {}'.format(str(f_ref),
                                                                location.capitalize(),
                                                                PLL[f_ref_str])
        if read_str != response:
            raise RuntimeError(
                '\'{}\' is not \'Reference Set to {}MHz {}ernal, {}\'.'\
                'Setting reference did not work.'
                .format(read_str,
                        str(f_ref),
                        location.capitalize(),
                        PLL[f_ref_str]))

    def _get_ref_locked(self) -> bool:
        """
        Function that checks whether the Holzworth is locked through a PLL
        with an external reference

        Returns:
            bool: True if properly locked via the phase locked loop (PLL),
            False if not.
        """
        locked = False
        read_str = self.ask(':REF:PLL?')
        if read_str == '1 PLL Locked, 0 errors':
            locked = True
        return locked

