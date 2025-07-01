from qcodes.instrument import Instrument
from qcodes.validators import Numbers, Enum
from qcodes_contrib_drivers.drivers.Lakeshore.modules.senseBase import senseBase

class cm10(senseBase):

    def __init__(self, parent: Instrument, name: str, Channel: str, **kwargs) -> None:
        super().__init__(parent, name, Channel, **kwargs)

        # add the CM-10 specific parameters here
        self.add_parameter(name='current_range',
            label='current range',
            unit='A',
            get_cmd=self._param_getter('CURRent:RANGe?'),
            set_cmd=self._param_setter('CURRent:RANGe', '{}'),
            vals=Enum(100e-3, 10e-3, 1e-3, 100e-6, 10e-6, 1e-6, 100e-9, 10e-9),
            get_parser=float
            )

        self.add_parameter(name='current_autorange_enabled',
            label='current autorange enabled',
            get_cmd=self._param_getter('CURRent:RANGe:AUTO?'),
            set_cmd=self._param_setter('CURRent:RANGe:AUTO', '{}'),
            val_mapping={True: '1', False: '0'}
            )

        self.add_parameter(name='bias_voltage_enabled',
            label='bias voltage state',
            get_cmd=self._param_getter('BIAS:STATe?'),
            set_cmd=self._param_setter('BIAS:STATe', '{}'),
            val_mapping={True: '1', False: '0'}
            )

        self.add_parameter(name='bias_voltage',
            label='bias voltage',
            unit='V',
            get_cmd=self._param_getter('BIAS:VOLTage:DC?'),
            get_parser = float,
            set_cmd=self._param_setter('BIAS:VOLTage:DC', '{}'),
            vals=Numbers(min_value=-10, max_value=10)
            )

        self.add_parameter(name='frequency_range_threshold',
            label='frequency range threshold',
            unit='% of -3 db',
            get_cmd=self._param_getter('FRTHreshold?'),
            get_parser = lambda value: 100*float(value),
            set_cmd=self._param_setter('FRTHreshold', '{}'),
            set_parser = lambda value: float(value)/100,
            vals=Numbers(min_value=0, max_value=100)
            )
