import numpy as np
from qcodes.instrument import Instrument, InstrumentChannel
from qcodes.validators import Numbers, Enum, Validator
from qcodes_contrib_drivers.drivers.Lakeshore.modules.sourceBase import sourceBase

class ValidateInput(Validator):
    """
    Validator class for voltage high limit, voltage low limit
    voltage peak amplitude and voltage rms amplitude parameters
    """

    def __init__(self, parent: InstrumentChannel, param: str) -> None:
        self.parent = parent
        self.param = param

    def validate(self, value: float, context='') -> None:
        match self.param:
            case 'voltage_low_limit':
                self._validator = Numbers(-10.000000000001, self.parent.get('voltage_peak_amplitude'))
            case 'voltage_high_limit':
                self._validator = Numbers(self.parent.get('voltage_peak_amplitude'), 10.000000000001)
            case 'voltage_peak_amplitude':
                self._validator = Numbers(self.parent.get('voltage_low_limit'), self.parent.get('voltage_high_limit'))
            case 'voltage_rms_amplitude':
                self._validator = Numbers(self.parent.get('voltage_low_limit')/np.sqrt(2), self.parent.get('voltage_high_limit')/np.sqrt(2))

        self._validator.validate(value)

class vs10(sourceBase):

    def __init__(self, parent: Instrument, name: str, Channel: str, **kwargs) -> None:
        super().__init__(parent, name, Channel, **kwargs)

        self.add_parameter(name='voltage_autorange_enabled',
                               label='voltage autorange status',
                               get_cmd=self._param_getter('VOLTage:RANGe:AUTO?'),
                               get_parser = lambda status: True if int(status) == 1 else False,
                               set_cmd=self._param_setter('VOLTage:RANGe:AUTO', '{}'),
                               val_mapping={True: 1, False: 0},
                               )

        self.add_parameter(name='voltage_range',
                               label='voltage range',
                               unit='V',
                               get_cmd=self._param_getter('VOLTage:RANGe?'),
                               set_cmd=self._param_setter('VOLTage:RANGe', '{}'),
                               vals=Enum(10e-3, 100e-3, 1, 10),
                               get_parser=float
                               )

        self.add_parameter(name='voltage_range_dc',
                               label='voltage range dc',
                               unit='V',
                               get_cmd=self._param_getter('VOLTage:RANGe:DC?'),
                               get_parser=float,
                               set_cmd=self._param_setter('VOLTage:RANGe:DC', '{}'),
                               vals=Enum(10e-3, 100e-3, 1, 10),
                               )

        self.add_parameter(name='voltage_low_limit',
                               label='voltage low limit',
                               unit='V',
                               get_cmd=self._param_getter('VOLTage:LIMit:LOW?'),
                               get_parser = float,
                               set_cmd=self._param_setter('VOLTage:LIMit:LOW', '{}'),
                               vals=ValidateInput(self, 'voltage_low_limit')
                               )

        self.add_parameter(name='voltage_high_limit',
                               label='voltage high limit',
                               unit='V',
                               get_cmd=self._param_getter('VOLTage:LIMit:HIGH?'),
                               get_parser = float,
                               set_cmd=self._param_setter('VOLTage:LIMit:HIGH', '{}'),
                               vals=ValidateInput(self, 'voltage_high_limit')
                               )

        self.add_parameter(name='current_protection_limit',
                               label='current protection limit',
                               unit='A',
                               get_cmd=self._param_getter('CURRent:PROTection?'),
                               get_parser = float,
                               set_cmd=self._param_setter('CURRent:PROTection', '{}')
                               )

        self.add_parameter(name='current_protection_tripped',
                               label='current protection tripped',
                               get_cmd=self._param_getter('CURRent:PROTection:TRIPped?'),
                               get_parser = lambda status: True if int(status) == 1 else False,
                               val_mapping={True: 1, False: 0}
                          )

        self.add_parameter(name='voltage_peak_amplitude',
                                label='voltage peak amplitude',
                               unit='V',
                               get_cmd=self._param_getter('VOLTage:LEVel:AMPLitude:PEAK?'),
                               get_parser = float,
                               set_cmd=self._param_setter('VOLTage:LEVel:AMPLitude:PEAK', '{}'),
                               vals=ValidateInput(self, 'voltage_peak_amplitude')
                               )

        self.add_parameter(name='voltage_rms_amplitude',
                               label='voltage rms amplitude',
                               unit='V RMS',
                               get_cmd=self._get_RMS,
                               set_cmd=self._param_setter('VOLTage:LEVel:AMPLitude:RMS', '{}'),
                               vals=ValidateInput(self, 'voltage_rms_amplitude')
                               )

        self.add_parameter(name='voltage_offset',
                               label='voltage offset',
                               unit='V',
                               get_cmd=self._param_getter('VOLTage:LEVel:OFFSet?'),
                               get_parser = float,
                               set_cmd=self._param_setter('VOLTage:LEVel:OFFSet', '{}')
                               )


    def _get_RMS(self) -> float|None:
        # get function for getting shape
        shape_cmd = self._param_getter('FUNCtion:SHAPe?')
        # ask the instrument for the current shape
        current_shape = self.ask(shape_cmd)
        if current_shape == 'SINUSOID':
            # if current shape is SINUSOID ask for RMS parameter
            rms_cmd = self._param_getter('VOLTage:LEVel:AMPLitude:RMS?')
            rms = float(self.ask(rms_cmd))
        else:
            # if not SINUSOID set RMS as None
            rms = None
        return rms
