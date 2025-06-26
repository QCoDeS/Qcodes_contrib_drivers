from typing import Any
import unicodedata
from qcodes.instrument import Instrument
from qcodes.validators import Numbers, Enum
from qcodes_contrib_drivers.drivers.Lakeshore.modules.moduleBase import moduleBase


class sourceBase(moduleBase):
    """Derived base class for M81 source modules"""

    def __init__(self, parent: Instrument, name: str, Channel: str, **kwargs) -> None:
        super().__init__(parent, name, Channel, **kwargs)

        self.set_shape = None
        self.target_shape = None

        self.add_parameter(name='shape',
                        label='shape',
                        get_cmd=self._param_getter('FUNCtion:SHAPe?'),
                        set_cmd=lambda value: self._param_shape_setter(value),
                        vals=Enum('DC', 'SINUSOID', 'TRIANGLE', 'SQUARE')
                        )

        # Attempt to read the current shape from the instrument
        self.target_shape = self.get('shape')
        # And now configure the instrument in-line with the current set up.
        # This accommodates the use-case where the instrument may have been
        # configured 'by hand' prior to remote connection.
        self._param_shape_setter(self.target_shape)

        # And the other paramters common to source modules
        self.add_parameter(name='output_enabled',
                        label='Source output enabled',
                        get_cmd=self._param_getter('STATe?'),
                        get_parser = lambda status: True if int(status) == 1 else False,
                        set_cmd=self._param_setter('STATe', '{}'),
                        val_mapping={True: 1, False: 0}
                        )

    def output_on(self) -> None:
        self.set('output_enabled', True)
        
    def output_off(self) -> None:
        self.set('output_enabled', False)
        
    def _param_shape_setter(self, value: Any) -> None: # Not great having Any, but cant get mypy to work with str|None
        """ Function to configure the module based on the shape requested """

        self.target_shape = value
        # Check if the device is being configured for DC shape
        if 'DC' in value:
            # Device being set for DC shape, so
            self._configure_for_DC()
        elif 'SIN' in value:
            # Device being set for SIN shape, so
            self._configure_for_sine()
        elif 'TRI' in value:
            self._configure_for_tri_squ()
        elif 'SQU' in value:
            self._configure_for_tri_squ()
        else:
            pass

        # and finally change the shape on the module
        self.write(f"{self.command_prefix}:FUNCtion:SHAPe {value}")
        # and update the driver variable
        self.set_shape = self.target_shape

        #read new parameters values so they get added to station
        if 'SIN' in value:
            self._read_new_sine_params()
        if 'TRI' in value:
            self._read_new_tri_squ_params()
        if 'SQU' in value:
            self._read_new_tri_squ_params()


    def _configure_for_DC(self) -> None:
        """
        Function to add / remove parameters as required
        for the module to operate in DC shape
        """
        # First check if the driver is
        # not already set to DC shape
        if self.set_shape != 'DC':
            if self.set_shape == None:
                # No mode has ever been set - so no
                pass
            elif self.set_shape == 'SINUSOID':
                # remove Sine parameters
                self._remove_sine_params()
            else:
                self._remove_tri_squ_params()


    def _read_new_sine_params(self) -> None:
        self.get('frequency')
        self.get('synchronize_enabled')
        self.get('synchronize_phase')
        self.get('synchronize_source')

    def _remove_sine_params(self) -> None:
        del self.parameters['frequency']
        del self.parameters['synchronize_enabled']
        del self.parameters['synchronize_phase']
        del self.parameters['synchronize_source']
        
    def _configure_for_sine(self) -> None:
        """
        Function to add / remove parameters as required
        for the module to operate in Sine shape
        """
        # First check if the driver is
        # not already set to Sine shape
        if self.set_shape != 'SINUSOID':
            if self.set_shape == None:
                # No mode has ever been set - so no
                self._add_sine_params()
            elif self.set_shape == 'TRIANGLE':
                self._remove_tri_squ_params()
                self._add_sine_params()
            elif self.set_shape == 'SQUARE':
                self._remove_tri_squ_params()
                self._add_sine_params()
            elif self.set_shape == 'DC':
                self._add_sine_params()

    def _add_sine_params(self) -> None:
        self.add_parameter(name='frequency',
                        label='frequency',
                        unit='Hz',
                        get_cmd=self._param_getter('FREQuency?'),
                        get_parser = float,
                        set_cmd=self._param_setter('FREQuency', '{}')
                        )
    
        self.add_parameter(name='synchronize_enabled',
                        label='Source synchronized',
                        get_cmd=self._param_getter('SYNChronize?'),
                        get_parser = lambda status: True if int(status) == 1 else False,
                        set_cmd=self._param_setter('SYNChronize', '{}'),
                        val_mapping={True: 1, False: 0}
                        )
        
        self.add_parameter(name='synchronize_phase',
                        label='Source synchronize phase',
                        unit=unicodedata.lookup('DEGREE SIGN'),
                        get_cmd=self._param_getter('SYNChronize:PHASe?'),
                        get_parser = float,
                        set_cmd=self._param_setter('SYNChronize:PHASe', '{}'),
                        vals=Numbers(min_value=-360.0, max_value=360.0)
                        )
        
        self.add_parameter(name='synchronize_source',
                        label='Source synchronize source',
                        get_cmd=self._param_getter('SYNChronize:SOURce?'),
                        set_cmd=self._param_setter('SYNChronize:SOURce', '{}')
                        )

    
    def _read_new_tri_squ_params(self) -> None:
        self.get('frequency')
        self.get('synchronize_enabled')
        self.get('synchronize_phase')
        self.get('synchronize_source')
        self.get('duty_cycle')

    def _remove_tri_squ_params(self) -> None:
        del self.parameters['frequency']
        del self.parameters['synchronize_enabled']
        del self.parameters['synchronize_phase']
        del self.parameters['synchronize_source']
        del self.parameters['duty_cycle']
        
    def _configure_for_tri_squ(self) -> None:
        """
        Function to add / remove parameters as required
        for the module to operate in Triangle/Square shape
        """
        # First check if the driver is
        # not already set to Triangle/Square shpe
        if self.set_shape != 'TRIANGLE' or self.set_shape != 'SQUARE':
            if self.set_shape == None:
                # No mode has ever been set - so no
                self._add_tri_squ_params()
            elif self.set_shape == 'SINUSOID':
                self._remove_sine_params()
                self._add_tri_squ_params()
            elif self.set_shape == 'DC':
                self._add_tri_squ_params()
            

    def _add_tri_squ_params(self) -> None:
        self.add_parameter(name='frequency',
                        label='frequency',
                        unit='Hz',
                        get_cmd=self._param_getter('FREQuency?'),
                        get_parser = float,
                        set_cmd=self._param_setter('FREQuency', '{}')
                        )
    
        self.add_parameter(name='synchronize_enabled',
                        label='Source synchronized',
                        get_cmd=self._param_getter('SYNChronize?'),
                        get_parser = lambda status: True if int(status) == 1 else False,
                        set_cmd=self._param_setter('SYNChronize', '{}'),
                        val_mapping={True: 1, False: 0}
                        )
        
        self.add_parameter(name='synchronize_phase',
                        label='Source synchronize phase',
                        unit=unicodedata.lookup('DEGREE SIGN'),
                        get_cmd=self._param_getter('SYNChronize:PHASe?'),
                        get_parser = float,
                        set_cmd=self._param_setter('SYNChronize:PHASe', '{}'),
                        vals=Numbers(min_value=-360.0, max_value=360.0)
                        )
        
        self.add_parameter(name='synchronize_source',
                        label='Source synchronize source',
                        get_cmd=self._param_getter('SYNChronize:SOURce?'),
                        set_cmd=self._param_setter('SYNChronize:SOURce', '{}')
                        )
        
        self.add_parameter(name='duty_cycle',
                        label='duty cycle',
                        get_cmd=self._param_getter('DCYCle?'),
                        get_parser = float,
                        set_cmd=self._param_setter('DCYCle', '{}'),
                        vals=Numbers(min_value=0.0, max_value=1.0) 
                        )