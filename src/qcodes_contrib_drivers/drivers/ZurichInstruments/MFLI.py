from qcodes.validators import ComplexNumbers
from qcodes.parameters import ParamRawDataType, Parameter
from typing import Any, Optional
from zhinst.qcodes import MFLI as mfli


class ComplexSampleParameter(Parameter):
    """
    This defines a Complex Sample Parameter for use in the MFLI class.
    """
    def __init__(
        self,
        *args: Any,
        dict_parameter: Optional[Parameter] = None,
        **kwargs: Any
    ):
        super().__init__(*args, **kwargs)
        if dict_parameter is None:
            raise TypeError("ComplexSampleParameter requires a dict_parameter")
        self._dict_parameter = dict_parameter

    def get_raw(self) -> ParamRawDataType:
        values_dict = self._dict_parameter.get()
        x = values_dict["x"]
        y = values_dict["y"]
        if hasattr(x, "__len__"):
            return complex(x[0], y[0])
        return complex(x,y)

class MFLI(mfli):
    """
    This wrapper adds back a "complex sample" parameter to the demodulators
    such that we can use them in the way that it was done with "sample"
    parameter in version 0.2 of ZHINST-qcodes
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
