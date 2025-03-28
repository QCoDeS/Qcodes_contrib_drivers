from qcodes.instrument import Instrument, InstrumentChannel

class moduleBase(InstrumentChannel):
    """ Base class for all M81 SSM modules"""

    def __init__(self, parent: Instrument, name: str, Channel: str, **kwargs) -> None:
        super().__init__(parent, name, **kwargs)

        self.module_name = Channel
        self.command_prefix = self._get_prefix()

        self.add_parameter(name='model',
                               label='model',
                               get_cmd=self._param_getter('MODel?'),
                               get_parser = lambda resp: resp.strip('"')
                               )

        self.add_parameter(name='serial',
                               label='serial',
                               get_cmd=self._param_getter('SERial?'),
                               get_parser = lambda resp: resp.strip('"')
                               )

    def _get_prefix(self) -> str:
        match self.module_name:
            case 'S1': return "SOURce1"
            case 'S2': return "SOURCe2"
            case 'S3': return "SOURCe3"
            case 'M1': return "SENSe1"
            case 'M2': return "SENSe2"
            case 'M3': return "SENSe3"
            case _: raise ValueError('Channel must be either S[1-3] or M[1-3]')

    def _param_getter(self, get_cmd: str) -> str:
        return f"{self.command_prefix}:{get_cmd}"
    
    def _param_setter(self, set_cmd: str, value: str) -> str:
        return f"{self.command_prefix}:{set_cmd} {value}"
    
    def reset_to_default(self) -> None:
        self.write(f"{self.command_prefix}:PRESet")
