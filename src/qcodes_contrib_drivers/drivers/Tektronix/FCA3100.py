import logging
import numpy as np
from typing import Any, Tuple
from qcodes.instrument import VisaInstrument
from qcodes.parameters import MultiParameter, Parameter, ParameterWithSetpoints
from qcodes.validators import Arrays, Ints

log = logging.getLogger(__name__)

class TimeStatistics(MultiParameter):
    """
    Returns the statistical values of a timing statistics.
    """
    def __init__(self,
                 name:str,
                 instrument:"FCA3100",
                 **kwargs: Any
                 ) -> None:
        """
        Statistical values of a timing statistics.

        Args:
            name: name of the timing statistics
            instrument: Instrument to which the timing statistic is bound to.
        """

        super().__init__(name=name,
                         instrument=instrument,
                         names=(
                            f"{instrument.short_name}_{name}_mean",
                            f"{instrument.short_name}_{name}_stddev",
                            f"{instrument.short_name}_{name}_minval",
                            f"{instrument.short_name}_{name}_maxval"),
                         shapes=((), (),(),()),
                         labels=(
                            f"{instrument.short_name} {name} mean time",
                            f"{instrument.short_name} {name} standard deviation",
                            f"{instrument.short_name} {name} min value",
                            f"{instrument.short_name} {name} max value"),
                         units=('s', 's', 's', 's'),
                         setpoints=((), (), (), ()),
                         **kwargs)

    def get_raw(self) -> Tuple[float, float, float, float]:
        """
        Gets data from the instrument

        Returns:
            Tuple: Statistical values of the time statistic
        """
        assert isinstance(self.instrument, FCA3100)
        self.instrument.write('CALCulate:AVERage:STAT 1')
        self.instrument.write('INIT') # start measurement
        self.instrument.ask('*OPC?') # wait for it to complete
        reply = self.instrument.ask("CALCulate:AVERage:ALL?")
        mean, stddev, minval, maxval, _ = reply.split(",")

        return float(mean), float(stddev), float(minval), float(maxval)

class CompleteTimeStatistics(ParameterWithSetpoints):
    def __init__(self,
                 name:str,
                 instrument:"FCA3100",
                 **kwargs: Any
                 ) -> None:
        """
        Parameter for a complete time statistics containing all measured switching times.

        Args:
            name: name of the complete time statistics
            instrument: Instrument to which the complete time statistic is bound to.
        """
        super().__init__(name=name,
                         instrument=instrument,
                         label='Times till switching',
                         unit='s',
                         docstring='Arrays of switching times',
                         **kwargs)

    def get_raw(self) -> np.ndarray:
        """
        Gets the data from the instrument.

        Returns:
            np.ndarray: Array of swithing times
        """
        assert isinstance(self.instrument, FCA3100)
        self.instrument.write('CALCulate:AVERage:STATe 0')
        self.instrument.write('ARM:COUN {}'.format(self.instrument.samples_number.get_latest()))
        data_str=self.instrument.ask("READ:ARRay? {}".format(self.instrument.samples_number.get_latest()))
        data = np.array(data_str.rstrip().split(",")).astype("float64")
        return data

class GeneratedSetPoints(Parameter):
    """
    A parameter that generates a setpoint array from start, stop and num points
    parameters.
    """
    def __init__(self, numpointsparam, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._numpointsparam = numpointsparam

    def get_raw(self):
        return np.arange(self._numpointsparam())


class FCA3100(VisaInstrument):
    """
    This is the qcodes driver for the FCA3100 counter
    """

    def __init__(self,
                 name: str,
                 address: str,
                 terminator : str="\n",
                 timeout    : int=10,
                 **kwargs) -> None:
        """
        Qcodes driver for the Textronix FCA3100 frequency counter.

        Args:
            name: Name of the instrument
            address: Address of the instrument
            terminator (optional): Terminator character of
                the string reply. Defaults to "\\n".
            timeout (optional): VISA timeout is set purposely
                to a long time to allow long measurements. Defaults to 10.
        """

        super().__init__(name = name,
                         address = address,
                         terminator = terminator,
                         timeout = timeout,
                         device_clear = False,
                         **kwargs)

        self.write('INIT:CONT 0')

        self.add_parameter(name='timestats',
                           parameter_class=TimeStatistics)

        self.add_parameter(name='samples_number',
                           label='samples_number',
                           get_cmd='CALCulate:AVERage:COUNt?',
                           set_cmd='CALCulate:AVERage:COUNt {}',
                           get_parser=float,
                           vals=Ints(2, int(2e9)),
                           docstring='Number of samples in the current statistics sampling'
                           )

        self.add_parameter('counter_axis',
                           unit='#',
                           label='Counter Axis',
                           parameter_class=GeneratedSetPoints,
                           numpointsparam=self.samples_number,
                           vals=Arrays(shape=(self.samples_number.get_latest,)))

        self.add_parameter(name='threshold_A',
                          label='threshold_A',
                          get_cmd='INPut1:LEVel?',
                          set_cmd='INPut1:LEVel {}',
                          get_parser=float,
                          unit='V',
                          docstring='Absolute voltage trigger threshold channel A'
                          )

        self.add_parameter(name='threshold_B',
                          label='threshold_B',
                          get_cmd='INPut2:LEVel?',
                          set_cmd='INPut2:LEVel {}',
                          get_parser=float,
                          unit='V',
                          docstring='Absolute voltage trigger threshold channel B'
                          )

        self.add_parameter(name='time_array',
                           parameter_class=CompleteTimeStatistics,
                           setpoints=(self.counter_axis,),
                           vals=Arrays(shape=(self.samples_number.get_latest,))
                           )

        self.connect_message()
