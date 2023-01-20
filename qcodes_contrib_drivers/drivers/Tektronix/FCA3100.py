from functools import partial
from qcodes import VisaInstrument
from qcodes.instrument.parameter import MultiParameter

class TimeStatistics(MultiParameter):
    def __init__(self, name, instrument):

        super().__init__(name=name, names=("mean", "stddev", "minval", "maxval"), 
                          shapes=((), (),(),()),
                          labels=('Mean time', 'Standart deviation','Min value', 'Max value'),
                          units=('s', 's', 's', 's'),
                          setpoints=((), (), (), ()))
        self._instrument = instrument
        
    def get_raw(self):
        self._instrument.write('CALCulate:AVERage:STAT 1')
        self._instrument.write('INIT') # start measurement
        self._instrument.ask('*OPC?') # wait for it to complete
        reply = self._instrument.ask("CALCulate:AVERage:ALL?")
        mean, stddev, minval, maxval, _ = reply.split(",")

        return (float(mean), float(stddev), float(minval), float(maxval))

        


class FCA3100(VisaInstrument):
    """
    This is the qcodes driver for the FCA3100 counter

    Args:
      name (str): What this instrument is called locally.
      address (str): The GPIB address of this instrument
      kwargs (dict): kwargs to be passed to VisaInstrument class
      terminator (str): read terminator for reads/writes to the instrument.
    """

    def __init__(self,
                 name: str,
                 address: str, 
                 terminator : str="\n",
                 timeout    : int=10,
                 **kwargs) -> None:
        super().__init__(name, address, terminator = terminator, timeout = timeout, device_clear = False, **kwargs)
        self.write('INIT:CONT 0')
       
        self.add_parameter('timeinterval',
                           label='timeinterval',
                           unit='s',
                           get_cmd="MEASure:TINTerval",
                           get_parser=float,
                           docstring='Measured time interval'
                           )

        self.add_parameter(name='timestats',
                           parameter_class=TimeStatistics)

        self.add_parameter(name='samples_number',
                           label='samples_number',
                           get_cmd='CALCulate:AVERage:COUNt?',
                           set_cmd='CALCulate:AVERage:COUNt {}',
                           get_parser=float,
                           docstring='Number of samples in the current statistics sampling'
                           )

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


        
        self.connect_message()

    
    def reset(self):
        return
    
    def startread(self):
        self.ask("Read?")
        return
