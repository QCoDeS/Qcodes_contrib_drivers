from typing import Any
import unicodedata
from qcodes.instrument import Instrument
from qcodes.validators import Numbers, Ints, Enum
from qcodes_contrib_drivers.drivers.Lakeshore.modules.moduleBase import moduleBase


class senseBase(moduleBase):
    """Derived base class for M81 sense modules"""

    def __init__(self, parent: Instrument, name: str, Channel: str, **kwargs) -> None:
        super().__init__(parent, name, Channel, **kwargs)

        self.set_mode = None
        self.target_mode = None

        self.add_parameter(name='mode',
            label='mode',
            get_cmd=self._param_getter('MODE?'),
            set_cmd=lambda value: self._param_mode_setter(value),
            vals=Enum('DC', 'AC', 'LIA')
            )

        # Attempt to read the current mode from the instrument
        self.target_mode = self.get('mode')
        # And now configure the instrument in-line with the current set up.
        # This accommodates the use-case where the instrument may have been
        # configured 'by hand' prior to remote connection.
        self._param_mode_setter(self.target_mode)

        # And the other paramters common to sense modules
        self.add_parameter(name='input_filter_enabled',
            label='input filter enabled',
            get_cmd=self._param_getter('FILTer?'),
            set_cmd=self._param_setter('FILTer', '{}'),
            val_mapping={True: '1', False: '0'}
            )

        self.add_parameter(name='input_filter_highpass_rolloff',
            label='highpass filter rolloff',
            unit='dB/octave',
            get_cmd=self._param_getter('FILTer:HPASs:ATTenuation?'),
            set_cmd=self._param_setter('FILTer:HPASs:ATTenuation', '{}'),
            val_mapping={6: 'R6', 12: 'R12'}
            )

        self.add_parameter(name='input_filter_highpass_cutoff',
            label='highpass filter cutoff frequency',
            unit='Hz',
            get_cmd=self._param_getter('FILTer:HPASs:FREQuency?'),
            set_cmd=self._param_setter('FILTer:HPASs:FREQuency', '{}'),
            val_mapping={
                'NONE'   : 'NONE', # 0 should make sense here..?
                10       : 'F10',
                30       : 'F30',
                100      : 'F100',
                300      : 'F300',
                1000     : 'F1000',
                3000     : 'F3000',
                10000    : 'F10000'}
            )

        self.add_parameter(name='input_filter_lowpass_rolloff',
            label='lowpass filter rolloff',
            unit='dB/octave',
            get_cmd=self._param_getter('FILTer:LPASs:ATTenuation?'),
            set_cmd=self._param_setter('FILTer:LPASs:ATTenuation', '{}'),
            val_mapping={6: 'R6', 12: 'R12'}
            )

        self.add_parameter(name='input_filter_lowpass_cutoff',
            label='lowpass filter cutoff frequency',
            unit='Hz',
            get_cmd=self._param_getter('FILTer:LPASs:FREQuency?'),
            set_cmd=self._param_setter('FILTer:LPASs:FREQuency', '{}'),
            val_mapping={
                'NONE'   : 'NONE', # better as math.inf or 0?
                10       : 'F10',
                30       : 'F30',
                100      : 'F100',
                300      : 'F300',
                1000     : 'F1000',
                3000     : 'F3000',
                10000    : 'F10000'}
            )

        self.add_parameter(name='input_filter_optimization',
            label='filter_optimization',
            get_cmd=self._param_getter('FILTer:OPTimization?'),
            set_cmd=self._param_setter('FILTer:OPTimization', '{}'),
            vals=Enum('NOISE', 'RESERVE')
            )

        self.add_parameter(name='calculated_resistance_source',
            label='calculated_resistance_source',
            get_cmd=f"CALCulate:{self._param_getter('RESistance:SOURce?')}",
            get_parser = str,
            set_cmd=f"CALCulate:{self._param_setter('RESistance:SOURce', '{}')}",
            vals=Enum('S1', 'S2', 'S3')
            )

    # ---------------------read parameter functions
    def read_DC(self) -> float:
        """
        Acquires and returns the DC measurement for the specified module.
        The value is returned after waiting for the configured NPLC to complete.
        The module must be in DC or AC mode.
        """
        try:
            cmd = self._param_reader('DC?')
            value = float(self.ask(cmd))
        except Exception as err:
            print('DC can only be read in DC or AC mode.')
            print(f'Instrument error message: {err}')
        return value

    def read_DC_relative(self) -> float:
        """
        Acquires and returns the relative DC measurement for the specified module.
        The value is returned after waiting for the configured NPLC to complete.
        The module must be in DC mode.
        """
        try:
            cmd = self._param_reader('DC:RELative?')
            value = float(self.ask(cmd))
        except Exception as err:
            print('DC relative can only be read in DC mode.')
            print(f'Instrument error message: {err}')
        return value

    def read_RMS(self) -> float:
        """
        Acquires and returns the RMS measurement for the specified module.
        The value is returned after waiting for the configured NPLC to complete.
        The module must be in DC or AC mode.
        """
        try:
            cmd = self._param_reader('RMS?')
            value = float(self.ask(cmd))
        except Exception as err:
            print('RMS can only be read in DC or AC mode.')
            print(f'Instrument error message: {err}')
        return value

    def read_RMS_relative(self) -> float:
        """
        Acquires and returns the relative RMS measurement for the specified module.
        The value is returned after waiting for the configured NPLC to complete.
        The module must be in AC mode.
        """
        try:
            cmd = self._param_reader('RMS:RELative?')
            value = float(self.ask(cmd))
        except Exception as err:
            print('RMS relative can only be read in AC mode.')
            print(f'Instrument error message: {err}')
        return value

    def read_r(self) -> float:
        """
        Returns the present magnitude measurement from the lock-in for the specified module.
        The module must be in lock-in mode.
        """
        try:
            cmd = self._param_fetcher('LIA:R?')
            value = float(self.ask(cmd))
        except Exception as err:
            print('R can only be read in LIA mode.')
            print(f'Instrument error message: {err}')
        return value

    def read_theta(self) -> float:
        """
        Returns the present angle measurement from the lock-in for the specified module.
        The module must be in lock-in mode.
        """
        try:
            cmd = self._param_fetcher('LIA:THETa?')
            value = float(self.ask(cmd))
        except Exception as err:
            print('Theta can only be read in LIA mode.')
            print(f'Instrument error message: {err}')
        return value

    def read_x(self) -> float:
        """
        Returns the present X measurement from the lock-in for the specified module.
        The module must be in lock-in mode.
        """
        try:
            cmd = self._param_fetcher('LIA:X?')
            value = float(self.ask(cmd))
        except Exception as err:
            print('X can only be read in LIA mode.')
            print(f'Instrument error message: {err}')
        return value

    def read_y(self) -> float:
        """
        Returns the present Y measurement from the lock-in for the specified module.
        The module must be in lock-in mode.
        """
        try:
            cmd = self._param_fetcher('LIA:Y?')
            value = float(self.ask(cmd))
        except Exception as err:
            print('Y can only be read in LIA mode.')
            print(f'Instrument error message: {err}')
        return value

    def read_LIA_DC(self) -> float:
        """
        Returns the DC measurement in lock in mode.
        The module must be in lock-in mode.
        """
        try:
            cmd = self._param_fetcher('LIA:DC?')
            value = float(self.ask(cmd))
        except Exception as err:
            print('LIA DC can only be read in LIA mode.')
            print(f'Instrument error message: {err}')
        return value

    def read_frequency(self) -> float:
        """
        Returns the present lock-in frequency.
        The module must be in lock-in mode.
        """
        try:
            cmd = self._param_fetcher('LIA:FREQuency?')
            value = float(self.ask(cmd))
        except Exception as err:
            print('LIA frequency can only be read in LIA mode.')
            print(f'Instrument error message: {err}')
        return value

    def read_npeak(self) -> float:
        """
        Acquires and returns the negative peak measurement for the specified module.
        The value is returned after waiting for the configured NPLC to complete.
        """
        try:
            cmd = self._param_reader('NPEak?')
            value = float(self.ask(cmd))
        except Exception as err:
            print(f'Instrument error message: {err}')
        return value

    def read_ppeak(self) -> float:
        """
        Acquires and returns the positive peak measurement for the specified module.
        The value is returned after waiting for the configured NPLC to complete.
        """
        try:
            cmd = self._param_reader('PPEak?')
            value = float(self.ask(cmd))
        except Exception as err:
            print(f'Instrument error message: {err}')
        return value

    def read_ptpeak(self) -> float:
        """
        Acquires and returns the peak to peak measurement for the specified module.
        The value is returned after waiting for the configured NPLC to complete.
        """
        try:
            cmd = self._param_reader('PTPEak?')
            value = float(self.ask(cmd))
        except Exception as err:
            print(f'Instrument error message: {err}')
        return value


    # ---------------------read calculated value function
    def calculated_resistance(self) -> float:
        """
        Immediately returns the resistance in Ohms. When in DC mode, this is the DC resistance.
        When in AC (lock-in) mode, this is the in-phase component of the resistance.
        May return a NaN if attempting to divide by zero, if the source is incompatible,
        or if either measure module or its designated source have an error.
        """
        try:
            cmd = f"CALCulate:{self._param_getter('RESistance?')}"
            value = float(self.ask(cmd))
        except Exception as err:
            print(f'Instrument error message: {err}')
        return value


    # -----------------parameter filtering by mode
    def _param_mode_setter(self, value: Any) -> None: # Not great having Any, but cant get mypy to work with str|None
        """ Function to configure the module based on the mode requested """

        self.target_mode = value
        # Check if the device is being configured for lock-in mode
        if 'LIA' in value:
            # Device being set for LIA mode, so
            self._configure_for_LIA()
        else:
            # Leaving or not entering LIA, so
            self._configure_for_ACDC()

        # and finally change the mode on the module
        self.write(f"{self.command_prefix}:MODE {value}")
        # and update the driver variable
        self.set_mode = self.target_mode
        # read parameters so there values get added to station
        if 'LIA' in value:
            self._read_new_LIA_params()
        else:
            self._read_new_ACDC_params()

    def _read_new_ACDC_params(self) -> None:
        self.get('nplc')

    def _read_new_LIA_params(self) -> None:
        self.get('reference_frequency')
        self.get('harmonic')
        self.get('phase')
        self.get('averaging_filter_enabled')
        self.get('averaging_filter_cycles')
        self.get('traditional_lowpass_enabled')
        self.get('output_filter_rolloff')
        self.get('reference_source')
        self.get('time_constant')
        self.get('digital_highpass_enabled')
        self.get('settling_time')
        self.get('ENBW')


    def _configure_for_LIA(self) -> None:
        """
        Function to add / remove parameters as required
        for the module to operate in LIA mode
        """
        # First check if the driver is
        # not already set to lock-in mode
        if self.set_mode != 'LIA':
            # Are there AC/DC parameters that should be removed?
            if self.set_mode == None:
                # No mode has ever been set - so no
                pass
            else:
                # Remove AC/DC parameters
                self._remove_ACDC_params()

            # Now set LIA parameters
            self._add_LIA_params()

    def _configure_for_ACDC(self) -> None:
        """
        Function to add / remove parameters as required
        for the module to operate in AC/DC mode
        """
        # First check if driver is in LIA mode
        if self.set_mode == 'LIA':
            # It is, so remove those parameters
            self._remove_LIA_params()
            # And then add the AC/DC ones
            self._add_ACDC_params()


        # Or if a mode has never been set
        if self.set_mode == None:
            # No mode ever set, so
            self._add_ACDC_params()

        # Other wise we're already in AC/DC so nothing else to do


    def _remove_ACDC_params(self) -> None:
        del self.parameters['nplc']

    def _add_ACDC_params(self) -> None:
        self.add_parameter(name='nplc',
            label='nplc',
            get_cmd=self._param_getter('NPLCycles?'),
            get_parser = float,
            set_cmd=self._param_setter('NPLCycles', '{}'),
            vals=Numbers(min_value=0.01, max_value=600.00)
            )

    def _remove_LIA_params(self) -> None:
        del self.parameters['reference_frequency']
        delattr(self, 'set_auto_phase')
        del self.parameters['harmonic']
        del self.parameters['phase']
        del self.parameters['averaging_filter_enabled']
        del self.parameters['averaging_filter_cycles']
        del self.parameters['traditional_lowpass_enabled']
        del self.parameters['output_filter_rolloff']
        del self.parameters['reference_source']
        del self.parameters['time_constant']
        del self.parameters['digital_highpass_enabled']
        del self.parameters['settling_time']
        del self.parameters['ENBW']


    def _add_LIA_params(self) -> None:
        self.add_parameter(name='harmonic',
            label='lock in harmonic',
            get_cmd=self._param_getter('LIA:DHARmonic?'),
            get_parser = int,
            set_cmd=self._param_setter('LIA:DHARmonic', '{}'),
            vals=Ints(min_value=1)
            )

        self.add_parameter(name='phase',
            label='lock in phase',
            get_cmd=self._param_getter('LIA:DPHase?'),
            get_parser = float,
            set_cmd=self._param_setter('LIA:DPHase', '{}'),
            vals=Numbers(min_value=-360.0, max_value=360.0),
            unit=unicodedata.lookup('DEGREE SIGN')
            )

        setattr(self, 'set_auto_phase', lambda: self.write(f"{self.command_prefix}:LIA:DPHase:AUTO"))

        self.add_parameter(name='averaging_filter_enabled',
            label='lock in PSD output averaging/FIR filter enabled',
            get_cmd=self._param_getter('LIA:AVERage?'),
            set_cmd=self._param_setter('LIA:AVERage', '{}'),
            val_mapping={True: 1, False: 0}
            )

        self.add_parameter(name='averaging_filter_cycles',
            label='lock in PSD output averaging/FIR filter cycles',
            get_cmd=self._param_getter('LIA:REFerence:CYCLes?'),
            get_parser = int,
            set_cmd=self._param_setter('LIA:REFerence:CYCLes', '{}'),
            vals=Ints(min_value=1)
            )

        self.add_parameter(name='traditional_lowpass_enabled',
            label='lock in PSD output IIR/traditional lpass filter enabled',
            get_cmd=self._param_getter('LIA:LPASs?'),
            set_cmd=self._param_setter('LIA:LPASs', '{}'),
            val_mapping={True: 1, False: 0}
            )

        self.add_parameter(name='output_filter_rolloff',
            label='output filter rolloff',
            unit='dB/octave',
            get_cmd=self._param_getter('LIA:ROLLoff?'),
            set_cmd=self._param_setter('LIA:ROLLoff', '{}'),
            val_mapping={
                6 : 'R6',
                12 : 'R12',
                18 : 'R18',
                24 : 'R24'}
            )

        self.add_parameter(name='reference_source',
            label='lock in reference source',
            get_cmd=self._param_getter('LIA:RSOurce?'),
            set_cmd=self._param_setter('LIA:RSOurce', '{}'),
            vals=Enum('S1', 'S2', 'S3', 'RIN')
            )

        self.add_parameter(name='time_constant',
            label='lock in timeconstant',
            unit='s',
            get_cmd=self._param_getter('LIA:TIMEconstant?'),
            set_cmd=self._param_setter('LIA:TIMEconstant', '{}'),
            vals=Numbers(min_value=0.0001, max_value=10000.0)
            )

        self.add_parameter(name='digital_highpass_enabled',
            label='lock in digital highpass filter enabled',
            get_cmd=self._param_getter('DIGital:FILTer:HPASs?'),
            set_cmd=self._param_setter('DIGital:FILTer:HPASs', '{}'),
            val_mapping={True: '1', False: '0'}
            )

        self.add_parameter(name='reference_frequency',
            label='read lock in reference frequency',
            get_cmd=self._param_fetcher('LIA:LOCK?'),
            get_parser = float,
            unit = 'Hz'
            )

        self.add_parameter(name='settling_time',
            label='lock in settling time',
            get_cmd=self._param_getter('LIA:STIMe?'),
            get_parser = float,
            unit = 's'
            )

        self.add_parameter(name='ENBW',
            label='lock in equivalent noise bandwidth',
            get_cmd=self._param_getter('LIA:ENBW?'),
            get_parser = float,
            unit = 'Hz'
            )


    def _param_reader(self, get_cmd: str) -> str:
        return f"READ:{self.command_prefix}:{get_cmd}"

    def _param_fetcher(self, get_cmd: str) -> str:
        return f"FETCH:{self.command_prefix}:{get_cmd}"
