# This Python file uses the following encoding: utf-8

import numpy as np

from qcodes import VisaInstrument
from qcodes.utils.validators import Numbers, Arrays
from qcodes.instrument.parameter import ParameterWithSetpoints, Parameter


class GeneratedSetPoints(Parameter):
    """
    A parameter that generates a setpoint array from start, stop and
    num points parameters. It is used to define the frequency axis.
    """
    def __init__(self, startparam     : float,
                       stopparam      : float,
                       numpointsparam : int,
                       *args,
                       **kwargs):
        super().__init__(*args, **kwargs)
        self._startparam = startparam
        self._stopparam = stopparam
        self._numpointsparam = numpointsparam

    def get_raw(self) -> np.array:
        return np.linspace(self._startparam(),
                           self._stopparam(),
                           self._numpointsparam())

class SpectrumArray(ParameterWithSetpoints):
    """
    Conducting the measurement and obtain the measurement from the
    instrument. It is used to obtain the spectrum with the previoulsy
    generated frequency axis.
    Args:
        ParameterWithSetpoints (Parameter): This Parameter class is intended
                                            for anything where a call to the 
                                            instrument returns an array of 
                                            values.
    """
    def get_raw(self, ) -> np.array:
        self.root_instrument.write_raw("INIT:CONT OFF")
        self.root_instrument.write_raw("ABOR")
        self.root_instrument.write_raw("INIT")
        self.root_instrument.ask_raw("*OPC?")
        spec = self.root_instrument.ask_raw("TRAC1? TRACE1").split(',')
        return np.array(spec).astype(np.float64)
        """
        Instrument is initialized, starts measurement and data is obtained.
        Args:
            'INIT:CONT OFF': Switching to single sweep mode
            'ABOR': Aborting current measurement and resetting trigger system
            'INIT': Starting new measurement
            '*OPC?': Checks bit in the event status register  which is only 0 
                     after all preceding commands have been executed
            'TRAC1? TRACE1': Reading measurement data of trace 1
        """

class FSL(VisaInstrument):
    """
    QCoDeS driver for the Rhode & Schwarz spectrum analyzer FSL. 
    It contains all parameters of the instrument.
    """

    def __init__(self, name       : str,
                       address    : str,
                       terminator : str="\n",
                       timeout    : int=100,
                       **kwargs):
        """[summary]

        Args:
            name (str): Name of the instrument
            address (str): Address of instrument
            terminator (str, optional): Terminator. Defaults to "\n".
            timeout (int, optional): Communication timeout in untis of s. 
                                     Defaults to 100.
        """

        super().__init__(name       = name,
                         address    = address,
                         terminator = terminator,
                         timeout    = timeout,
                         **kwargs)

        self.add_parameter(name = 'frequency',
                           label = 'Center Frequency',
                           get_parser = float,
                           get_cmd = 'FREQ:CENT?',
                           set_cmd = 'FREQUENCY:CENTER {}Hz',
                           unit = 'Hz',
                           vals = Numbers(min_value=float(self.ask_raw(
                                                    'SENS:FREQ:CENT? MIN')),
                                          max_value=float(self.ask_raw(
                                                    'SENS:FREQ:CENT? MAX'))))

        self.add_parameter(name = 'span',
                           label = 'Span',
                           get_parser = float,
                           get_cmd = 'FREQ:SPAN?',
                           set_cmd = 'FREQUENCY:SPAN {}Hz',
                           unit = 'Hz',
                           vals = Numbers(min_value=float(self.ask_raw(
                                                    'SENS:FREQ:SPAN? MIN')),
                                          max_value=float(self.ask_raw(
                                                    'SENS:FREQ:SPAN? MAX'))))

        self.add_parameter(name = 'f_start',
                           label = 'Start Frequency',
                           get_parser = float,
                           get_cmd = 'FREQ:START?',
                           set_cmd = 'FREQUENCY:START {}Hz',
                           unit = 'Hz',
                           vals = Numbers(min_value=float(self.ask_raw(
                                                    'SENS:FREQ:START? MIN')),
                                          max_value=float(self.ask_raw(
                                                    'SENS:FREQ:START? MAX'))
                                          ))

        self.add_parameter(name = 'f_stop',
                           label = 'Stop Frequency',
                           get_parser = float,
                           get_cmd = 'FREQ:STOP?',
                           set_cmd = 'FREQUENCY:STOP {}Hz',
                           unit = 'Hz',
                           vals = Numbers(min_value=float(self.ask_raw(
                                                    'SENS:FREQ:STOP? MIN')),
                                          max_value=float(self.ask_raw(
                                                    'SENS:FREQ:STOP? MAX'))))

        self.add_parameter(name = 'rlevel',
                           label = 'Power Reference Level',
                           get_parser = float,
                           get_cmd = 'DISP:TRAC:Y:RLEV?',
                           set_cmd = 'DISPLAY:TRACE:Y:RLEVEL {}dBm',
                           unit = 'dBm',
                           vals = Numbers(min_value=float(self.ask_raw(
                                                    'DISP:TRAC:Y:RLEV? MIN')),
                                          max_value=float(self.ask_raw(
                                                    'DISP:TRAC:Y:RLEV? MAX'))))

        self.add_parameter(name = 'bw',
                           label = 'Resolution Bandwidth',
                           get_parser = float,
                           get_cmd = 'BAND:RES?',
                           set_cmd = 'BAND:RES {}Hz',
                           unit = 'Hz',
                           vals = Numbers(min_value=float(self.ask_raw(
                                                    'SENS:BAND:RES? MIN')),
                                          max_value=float(self.ask_raw(
                                                    'SENS:BAND:RES? MAX'))))

        self.add_parameter(name = 'video_bw',
                           label = 'Video Bandwidth',
                           get_parser = float,
                           get_cmd = 'BAND:VID?',
                           set_cmd = 'BAND:VID {}Hz',
                           unit = 'Hz',
                           vals = Numbers(min_value=float(self.ask_raw(
                                                    'SENS:BAND:VID? MIN')),
                                          max_value=float(self.ask_raw(
                                                    'SENS:BAND:VID? MAX'))))

        self.add_parameter(name = 'n_points',
                           unit = '',
                           get_parser = int,
                           get_cmd = 'SWE:POIN?',
                           set_cmd = 'SWE:POIN {}',
                           vals = Numbers(min_value=float(self.ask_raw(
                                                    'SWE:POIN? MIN')),
                                          max_value=float(self.ask_raw(
                                                    'SWE:POIN? MAX'))))

        self.add_parameter(name = 'freq_axis',
                           unit = 'Hz',
                           label = 'Freq Axis',
                           parameter_class = GeneratedSetPoints,
                           startparam = self.f_start,
                           stopparam = self.f_stop,
                           numpointsparam = self.n_points,
                           vals = Arrays(shape=(self.n_points,)))

        self.add_parameter(name = 'spectrum', 
                           unit = 'dBm',
                           setpoints = (self.freq_axis,),
                           label = 'Spectrum',
                           parameter_class = SpectrumArray,
                           vals = Arrays(shape=(self.n_points,)))

        self.connect_message()

    def reset(self) -> None:
        self.root_instrument.write_raw('*CLS')
        self.root_instrument.write_raw('*RST')
