from qcodes.instrument import Instrument
from qcodes.validators import Enum
from qcodes_contrib_drivers.drivers.Lakeshore.modules.senseBase import senseBase


class vm10(senseBase):

    def __init__(self, parent: Instrument, name: str, Channel: str, **kwargs) -> None:
        super().__init__(parent, name, Channel, **kwargs)

        # add the VM-10 specific parameters here
        self.add_parameter(name='voltage_range',
            label='voltage range',
            unit='V',
            get_cmd=self._param_getter('VOLTage:RANGe?'),
            set_cmd=self._param_setter('VOLTage:RANGe', '{}'),
            vals=Enum(10e-3, 100e-3, 1, 10),
            get_parser=float
            )

        self.add_parameter(name='voltage_autorange_enabled',
            label='voltage autorange status',
            get_cmd=self._param_getter('VOLTage:RANGe:AUTO?'),
            set_cmd=self._param_setter('VOLTage:RANGe:AUTO', '{}'),
            val_mapping={True: '1', False: '0'}
            )

        self.add_parameter(name='input_configuration',
            label='input configuration',
            get_cmd=self._param_getter('CONFiguration?'),
            set_cmd=self._param_setter('CONFiguration', '{}'),
            vals=Enum('AB', 'A', 'GROUND')
            )

        self.add_parameter(name='coupling',
            label='coupling',
            get_cmd=self._param_getter('COUPling?'),
            set_cmd=self._param_setter('COUPling', '{}'),
            vals=Enum('AC', 'DC')
            )
