from qcodes.utils.validators import ComplexNumbers
from qcodes.instrument.parameter import ParamRawDataType
from typing import Any, Optional
from qcodes import Parameter
from zhinst.qcodes import MFLI as mfli

class ComplexSampleParameter(Parameter):
    def __init__(
        self, *args: Any, dict_parameter: Optional[Parameter] = None, **kwargs: Any
    ):
        super().__init__(*args, **kwargs)
        if dict_parameter is None:
            raise TypeError("ComplexCampleParameter requires a dict_parameter")
        self._dict_parameter = dict_parameter

    def get_raw(self) -> ParamRawDataType:
        values_dict = self._dict_parameter.get()
        return complex(values_dict["x"], values_dict["y"])
        
class MFLI(mfli):
    """
    This wrapper adds back a "complex sample" parameter to the demodulators such that
    we can use them in the way that we have done with "sample" parameter
    in version 0.2 of ZHINST-qcodes
    written by jenshnielsen: https://github.com/zhinst/zhinst-qcodes/issues/41
    """

    def __init__(self, name: str, serial: str, host: str, **kwargs: Any):
        super().__init__(
            name=name, serial=serial, host=host, **kwargs
        )
        for demod in self.demods:
            demod.add_parameter(
                "complex_sample",
                label="Vrms",
                vals=ComplexNumbers(),
                parameter_class=ComplexSampleParameter,
                dict_parameter=demod.sample,
                snapshot_value=False,
            )