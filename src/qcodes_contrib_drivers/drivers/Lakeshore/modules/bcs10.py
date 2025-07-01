import numpy as np
from qcodes.instrument import Instrument, InstrumentChannel
from qcodes.validators import Numbers, Enum, Validator
from qcodes_contrib_drivers.drivers.Lakeshore.modules.sourceBase import sourceBase

class ValidateInput(Validator):
    """
    Validator class for current low limit, current high limit,
    current peak amplitude and current rms amplitude.
    """

    def __init__(self, parent: InstrumentChannel, param: str) -> None:
        self.parent = parent
        self.param = param

    def validate(self, value: float, context: str = '') -> None:
        match self.param:
            case 'current_low_limit':
                self._validator = Numbers(-0.10000000000001, self.parent.get('current_peak_amplitude'))
            case 'current_high_limit':
                self._validator = Numbers(self.parent.get('current_peak_amplitude'), 0.10000000000001)
            case 'current_peak_amplitude':
                self._validator = Numbers(self.parent.get('current_low_limit'), self.parent.get('current_high_limit'))
            case 'current_rms_amplitude':
                self._validator = Numbers(self.parent.get('current_low_limit')/np.sqrt(2), self.parent.get('current_high_limit')/np.sqrt(2))

        self._validator.validate(value)

class bcs10(sourceBase):

    def __init__(self, parent: Instrument, name: str, Channel: str, **kwargs) -> None:
        super().__init__(parent, name, Channel, **kwargs)

        self.add_parameter(name='coupling',
                               label='coupling',
                               get_cmd=self._param_getter('COUPling?'),
                               set_cmd=self._param_setter('COUPling', '{}') # AC or DC
                               )

        self.add_parameter(name='coupling_auto_enabled',
                               label='coupling auto status',
                               get_cmd=self._param_getter('COUPling:AUTO?'),
                               get_parser = lambda status: True if int(status) == 1 else False,
                               set_cmd=self._param_setter('COUPling:AUTO', '{}'),
                               val_mapping={True: 1, False: 0},
                               )

        self.add_parameter(name='guard_state',
                               label='guard state',
                               get_cmd=self._param_getter('GUARd?'),
                               get_parser = lambda status: True if int(status) == 1 else False,
                               set_cmd=self._param_setter('GUARd', '{}'),
                               val_mapping={True: 1, False: 0}
                               )

        self.add_parameter(name='current_autorange_enabled',
                               label='current autorange status',
                               get_cmd=self._param_getter('CURRent:RANGe:AUTO?'),
                               get_parser = lambda status: True if int(status) == 1 else False,
                               set_cmd=self._param_setter('CURRent:RANGe:AUTO', '{}'),
                               val_mapping={True: 1, False: 0},
                               )

        self.add_parameter(name='current_range',
                               label='current range',
                               unit='A',
                               get_cmd=self._param_getter('CURRent:RANGe?'),
                               set_cmd=self._param_setter('CURRent:RANGe', '{}'),
                               vals=Enum(100e-3, 10e-3, 1e-3, 100e-6, 10e-6, 1e-6, 100e-9, 10e-9),
                               get_parser=float
                               )

        self.add_parameter(name='cmf_enabled',
                               label='common mode feedback state',
                               get_cmd=self._param_getter('CMF:STATe?'),
                               get_parser = lambda status: True if int(status) == 1 else False,
                               set_cmd=self._param_setter('CMF:STATe', '{}'),
                               val_mapping={True: 1, False: 0}
                               )

        self.add_parameter(name='cmf_node',
                               label='common mode feedback node',
                               get_cmd=self._param_getter('CMF:NODe?'),
                               set_cmd=self._param_setter('CMF:NODe', '{}'),
                               vals=Enum('INTERNAL', 'EXTERNAL')
                               )

        self.add_parameter(name='current_low_limit',
                               label='current low limit',
                               unit='A',
                               get_cmd=self._param_getter('CURRent:LIMit:LOW?'),
                               get_parser = float,
                               set_cmd=self._param_setter('CURRent:LIMit:LOW', '{}'),
                               vals=ValidateInput(self, 'current_low_limit')
                               )

        self.add_parameter(name='current_high_limit',
                               label='current high limit',
                               unit='A',
                               get_cmd=self._param_getter('CURRent:LIMit:HIGH?'),
                               get_parser = float,
                               set_cmd=self._param_setter('CURRent:LIMit:HIGH', '{}'),
                               vals=ValidateInput(self, 'current_high_limit')
                               )

        self.add_parameter(name='disable_on_compliance',
                               label='disable on compliance',
                               get_cmd=self._param_getter('DOCompliance?'),
                               get_parser = lambda status: True if int(status) == 1 else False,
                               set_cmd=self._param_setter('DOCompliance', '{}'),
                               val_mapping={True: 1, False: 0}
                               )

        self.add_parameter(name='current_offset',
                               label='current offset',
                               unit='A',
                               get_cmd=self._param_getter('CURRent:LEVel:OFFSet?'),
                               get_parser = float,
                               set_cmd=self._param_setter('CURRent:LEVel:OFFSet', '{}')
                               )

        self.add_parameter(name='current_peak_amplitude',
                               label='current peak amplitude',
                               unit='A',
                               get_cmd=self._param_getter('CURRent:LEVel:AMPLitude:PEAK?'),
                               get_parser = float,
                               set_cmd=self._param_setter('CURRent:LEVel:AMPLitude:PEAK', '{}'),
                               vals=ValidateInput(self, 'current_peak_amplitude')
                               )

        self.add_parameter(name='current_rms_amplitude',
                               label='current rms amplitude',
                               unit='A RMS',
                               get_cmd=self._get_RMS,
                               set_cmd=self._param_setter('CURRent:LEVel:AMPLitude:RMS', '{}'),
                               vals=ValidateInput(self, 'current_rms_amplitude')
                               )

    def _get_RMS(self) -> float|None:
        # get function for getting shape
        shape_cmd = self._param_getter('FUNCtion:SHAPe?')
        # ask the instrument for the current shape
        current_shape = self.ask(shape_cmd)
        if current_shape == 'SINUSOID':
            # if current shape is SINUSOID ask for RMS parameter
            rms_cmd = self._param_getter('CURRent:LEVel:AMPLitude:RMS?')
            rms = float(self.ask(rms_cmd))
        else:
            # if not SINUSOID set RMS as None
            rms = None
        return rms
