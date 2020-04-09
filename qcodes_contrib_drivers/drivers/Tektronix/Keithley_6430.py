# Qcodes driver Keithley 6430 SMU
#
# Based on qtlab legacy driver by
# Russell Lake <russell.lake@aalto.fi>, 2012
# Based on driver for Keithley 2700 by:
# Pieter de Groot <pieterdegroot@gmail.com>, 2008
# Martijn Schaafsma <qtlab@mcschaafsma.nl>, 2008
# Reinier Heeres <reinier@heeres.eu>, 2008
#
# Update december 2009:
# Michiel Jol <jelle@michieljol.nl>

from qcodes.instrument.visa import VisaInstrument
from qcodes.utils.validators import Ints, Numbers, Bool, Strings, Enum
from qcodes.utils.helpers import create_on_off_val_mapping
import types
import logging
import warnings
from functools import partial

on_off_vals = create_on_off_val_mapping(on_val=1, off_val=0)


class Keithley_6430(VisaInstrument):

    def __init__(self, name, address, reset=False, **kwargs):
        r"""
        Args:
            name: The name used internally by QCoDeS
            address: Newtwork address or alias of the instrument
            reset: resets to default values
        """

        super().__init__(name, address, terminator='\n', **kwargs)

        self.add_parameter('source_current_compliance',
                           units='A',
                           get_parser=float,
                           set_cmd='SENS:CURR:PROT {}',
                           get_cmd='SENS:CURR:PROT?',
                           vals=Numbers(1e-9, 105e-3)
                           )
        self.add_parameter('source_voltage_compliance',
                           units='V',
                           get_parser=float,
                           set_cmd='SENS:VOLT:PROT {}',
                           get_cmd='SENS:VOLT:PROT?',
                           vals=Numbers(1e-12, 210)
                           )
        self.add_parameter('source_current_compliance_tripped',
                           get_cmd='SENS:CURR:PROT:TRIP?',
                           val_mapping=on_off_vals,
                           docstring='True if current has reached specified '
                                     'compliance.',
                           )
        self.add_parameter('source_voltage_compliance_tripped',
                           get_cmd='SENS:VOLT:PROT:TRIP?',
                           val_mapping=on_off_vals,
                           docstring='True if voltage has reached specified '
                                     'compliance.',
                           )
        self.add_parameter('source_current',
                           units='A',
                           get_parser=float,
                           label='Source current',
                           set_cmd='SOUR:CURR:LEV {}',
                           get_cmd='SOUR:CURR:LEV?',
                           vals=Numbers(-105e-3, 105e-3),
                           docstring='When in current sourcing mode, try to '
                                     'set current to this level.',
                           )
        self.add_parameter('sense_current',
                           units='A',
                           get_parser=float,
                           label='Measured current',
                           get_cmd=partial(self._read_value, 'CURR:DC'),
                           snapshot_value=False,
                           docstring='Value of measured current, when in '
                                     'current sensing mode.',
                           )
        self.add_parameter('sense_voltage',
                           units='V',
                           get_parser=float,
                           label='Measured voltage',
                           get_cmd=partial(self._read_value, 'VOLT:DC'),
                           snapshot_value=False,
                           docstring='Value of measured voltage, when in '
                                     'voltage sensing mode.',
                           )
        self.add_parameter('sense_resistance',
                           units='Ohm',
                           get_parser=float,
                           label='Measured resistance',
                           get_cmd=partial(self._read_value, 'RES'),
                           snapshot_value=False,
                           docstring='Value of measured resistance, when in '
                                     'resistance sensing mode.',
                           )
        self.add_parameter('source_current_range',
                           units='A',
                           get_parser=float,
                           set_cmd='SOUR:CURR:RANG {}',
                           get_cmd='SOUR:CURR:RANG?',
                           vals=Numbers(1e-12, 105e-3)
                           )
        self.add_parameter('source_voltage',
                           units='V',
                           get_parser=float,
                           label='Source voltage',
                           set_cmd='SOUR:VOLT:LEV {}',
                           get_cmd='SOUR:VOLT:LEV?',
                           vals=Numbers(-210, 210),
                           docstring='When in voltage sourcing mode, try to '
                                     'set voltage to this level.',
                           )
        self.add_parameter('source_voltage_range',
                           units='V',
                           get_parser=float,
                           set_cmd='SOUR:VOLT:RANG {}',
                           get_cmd='SOUR:VOLT:RANG?',
                           vals=Numbers(200e-3, 200)
                           )
        self.add_parameter('source_delay_auto',
                           set_cmd=':SOUR:DEL:AUTO {}',
                           get_cmd=':SOUR:DEL:AUTO?',
                           val_mapping=on_off_vals,
                           )
        self.add_parameter('source_delay',
                           units='s',
                           get_parser=float,
                           set_cmd=':SOUR:DEL {}',
                           get_cmd=':SOUR:DEL?',
                           vals=Numbers(0, 9999.998)
                           )
        self.add_parameter('output_on',
                           set_cmd='OUTP {}',
                           get_cmd='OUTP?',
                           val_mapping=on_off_vals,
                           docstring='True if the instrument is outputting.',
                           )
        self.add_parameter('output_auto_off',
                           set_cmd=':SOUR:CLE:AUTO {}',
                           get_cmd='OUTP?',
                           val_mapping=on_off_vals,
                           )
        self.add_parameter('source_mode',
                           set_cmd='SOUR:FUNC {}',
                           get_cmd=self._get_source_mode,
                           vals=Enum('VOLT', 'CURR'),
                           docstring="Either 'VOLT' to set source function "
                                     "voltage, or 'CURR' for current.",
                           )
        self.add_parameter('sense_mode',
                           set_cmd=self._set_sense_mode,
                           get_cmd=self._get_sense_mode,
                           vals=Strings(),
                           docstring="Sensing mode. Set to 'VOLT:DC', "
                                     "'CURR:DC', or 'RES', or a combination "
                                     "thereof by using comma."
                           )
        self.add_parameter('sense_autorange',
                           set_cmd=self._set_sense_autorange,
                           get_cmd=self._get_sense_autorange,
                           vals=Bool(),
                           docstring="If True, all ranges in all modes are "
                                     "chosen automatically",
                           )
        self.add_parameter('sense_current_range',
                           units='A',
                           get_parser=float,
                           set_cmd=':SENS:CURR:RANG {}',
                           get_cmd=':SENS:CURR:RANG?',
                           vals=Numbers(1e-12, 1e-1),
                           )
        self.add_parameter('sense_voltage_range',
                           units='V',
                           get_parser=float,
                           set_cmd=':SENS:VOLT:RANG {}',
                           get_cmd=':SENS:VOLT:RANG?',
                           vals=Enum(200, 20, 2, 0.2),
                           )
        self.add_parameter('sense_resistance_range',
                           units='Ohm',
                           get_parser=float,
                           set_cmd=':SENS:RES:RANG {}',
                           get_cmd=':SENS:RES:RANG?',
                           vals=Numbers(2, 2e13),
                           )
        self.add_parameter('sense_resistance_ocomp',
                           set_cmd=':SENS:RES:OCOM {}',
                           get_cmd=':SENS:RES:OCOM?',
                           val_mapping=on_off_vals,
                           docstring="Set offset compensation on/off for "
                                     "resistance measurements."
                           )
        self.add_parameter('trigger_source',
                           set_cmd=':TRIG:SOUR {}',
                           get_cmd=':TRIG:SOUR?',
                           vals=Enum('IMM', 'TLIN'),
                           )
        self.add_parameter('arm_source',
                           set_cmd=':ARM:SOUR {}',
                           get_cmd=':ARM:SOUR?',
                           vals=Enum('IMM', 'TLIN'),
                           )
        self.add_parameter('trigger_count',
                           set_cmd=':TRIG:COUN {}',
                           get_cmd=':TRIG:COUN?',
                           vals=Ints(),
                           )
        self.add_parameter('arm_count',
                           set_cmd=':ARM:COUN {}',
                           get_cmd=':ARM:COUN?',
                           vals=Ints(),
                           )
        self.add_parameter('nplc',
                           get_parser=float,
                           set_cmd=':NPLC {}',
                           get_cmd=':NPLC?',
                           vals=Numbers(0.01, 10),
                           docstring="Set integration time to the specified "
                                     "value in Number of Powerline Cycles."
                           )
        self.add_parameter('digits',
                           get_parser=int,
                           set_cmd='DISP:DIG  {}',
                           get_cmd='DISP:DIG?',
                           vals=Ints(4, 7),
                           )
        self.add_parameter('autozero',
                           set_cmd='SYST:AZER:STAT {}',
                           get_cmd='SYST:AZER:STAT?',
                           val_mapping=on_off_vals,
                           )
        self.add_parameter('filter_auto',
                           set_cmd='AVER:AUTO {}',
                           get_cmd='AVER:AUTO?',
                           val_mapping=on_off_vals,
                           )
        self.add_parameter('filter_repeat_enabled',
                           set_cmd=':AVER:REP:STAT {}',
                           get_cmd='AVER:AUTO?',
                           val_mapping=on_off_vals,
                           )
        self.add_parameter('filter_median_enabled',
                           set_cmd=':MED:STAT {}',
                           get_cmd=':MED:STAT?',
                           val_mapping=on_off_vals,
                           )
        self.add_parameter('filter_moving_enabled',
                           set_cmd=':AVER:STAT {}',
                           get_cmd=':AVER:STAT?',
                           val_mapping=on_off_vals,
                           )
        self.add_parameter('filter_repeat',
                           get_parser=int,
                           set_cmd=':AVER:REP:COUN {}',
                           get_cmd=':AVER:REP:COUN?',
                           vals=Ints(),
                           )
        self.add_parameter('filter_median',
                           get_parser=int,
                           set_cmd=':MED:RANK {}',
                           get_cmd=':MED:RANK?',
                           vals=Ints(),
                           )
        self.add_parameter('filter_moving',
                           get_parser=int,
                           set_cmd=':AVER:COUN {}',
                           get_cmd=':AVER:COUN?',
                           vals=Ints(),
                           )

        self.connect_message()

        if reset:
            self.reset()

    def reset(self):
        '''
        Resets instrument to default values
        '''
        self.write('*RST')

    def set_defaults(self):
        '''
        Set to driver defaults:
        Sense voltage and source current
        Output=data only
        source_mode=curr
        sense_mode=volt
        Digits=7
        NPLC=10
        Averaging=off
        source current compliance = 1 uA
        source voltage compliance = 1 mV
        '''
        self.write('SYST:PRES')
        # self.write(':FORM:ELEM READ')
        '''
        Sets the format to only the read out, all options are:
        READing = DMM reading, UNITs = Units,
        TSTamp = Timestamp, RNUMber = Reading number,
        CHANnel = Channel number, LIMits = Limits reading
        '''
        self.source_mode('CURR')
        self.sense_mode('VOLT:DC,CURR:DC')
        # self.set_trigger_cont(True)
        self.source_current_range(1e-6)
        self.source_current(0e-6)
        self.source_current_compliance(1e-6)
        self.source_voltage_range(200e-3)
        self.source_voltage_compliance(1e-3)
        self.digits(7)
        self.nplc(10)
        # self.set_averaging(False)

    def read(self):
        '''
        Arm, trigger, and readout (voltage (V), current (A), resistance (Ohm)).

        Note that the values may not be valid if sense mode doesn't include
        them.
        '''
        if not (self.output_on() or self.output_auto_off()):
            raise Exception(
                    'Either source must be turned on manually or auto_off has '
                    'to be enabled before calling read().'
                    )
        s = self.ask(':READ?')
        logging.debug('Read: %s' % s)

        # We don't know what [3:5] are...
        return [float(n) for n in s.split(',')][:3]

    def _read_value(self, quantity: str):
        '''
        Read voltage, current or resistance through the sensing module. Issues
        a warning if reading a value that does not correspond to the sensing
        mode quantity: "VOLT:DC", "CURR:DC" or "RES"
        '''
        mode_now = self.sense_mode()
        if quantity not in mode_now:
            warnings.warn(f"{self.short_name} tried reading {quantity}, but "
                          f"mode is set to {mode_now}. Value might be old.")
        mapping = {"VOLT:DC": 0, "CURR:DC": 1, "RES": 2}
        return self.read()[mapping[quantity]]

    def init(self):
        '''
        Go into the arm/trigger layers from the idle mode.
        '''
        self.write(':INIT')

    def fetch_last(self):
        '''
        Fetch the last measured value. Typically used after send_init.

        Note that the values may not be valid if sense mode doesn't include
        them.
        '''
        s = self.ask(':FETC?')

        # We don't know what [-2:] are...
        return [float(n) for n in s.split(',')][-5:-2]

    def set_trigger_cont(self):
        '''
        Set trigger and arm modes to immediate.
        '''
        self.trigger_source('IMM')
        self.arm_source('IMM')

    def _set_sense_mode(self, mode):
        '''
        Set the sense_mode to the specified value
        Input:
            mode (string) : mode(s) to be set. Choose from self._sense_modes.
                            Use comma to separate multiple modes.
        '''

        mode = [m.strip(' ') for m in mode.split(',')]

        if not all([m in ["RES", "CURR:DC", "VOLT:DC"] for m in mode]):
            raise ValueError('invalid sense_mode %s' % mode)

        mode = '"' + '","'.join(mode) + '"'

        string = ':SENS:FUNC %s' % mode

        self.write(':SENS:FUNC:OFF:ALL')
        self.write(string)

    def _get_sense_mode(self):
        '''
        Read the sense_mode from the device
        '''
        string = 'SENS:FUNC?'
        ans = self.ask(string).replace('"', '')
        return ans

    def _get_source_mode(self):
        '''
        Read the source_mode from the device
        '''
        string = 'SOUR:FUNC?'
        ans = self.ask(string).strip('"')
        return ans

    def _set_sense_autorange(self, val):
        '''
        Switch sense_autorange on or off for all modes.
        '''
        val = int(val)
        self.write(f'SENS:CURR:RANG:AUTO {val}')
        self.write(f'SENS:VOLT:RANG:AUTO {val}')
        self.write(f'SENS:RES:RANG:AUTO {val}')

    def _get_sense_autorange(self):
        '''
        Get status of sense_autorange. Returns true iff true for all modes
        '''
        reply0 = bool(int(self.ask('SENS:CURR:RANG:AUTO?')))
        reply1 = bool(int(self.ask('SENS:VOLT:RANG:AUTO?')))
        reply2 = bool(int(self.ask('SENS:RES:RANG:AUTO?')))
        return reply0 and reply1 and reply2
