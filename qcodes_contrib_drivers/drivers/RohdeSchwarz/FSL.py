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
    def __init__(self, startparam     : Parameter,
                       stopparam      : Parameter,
                       numpointsparam : Parameter,
                       *args,
                       **kwargs):
        super().__init__(*args, **kwargs)
        self._startparam = startparam
        self._stopparam = stopparam
        self._numpointsparam = numpointsparam

    def get_raw(self) -> np.ndarray:
        start = self._startparam()
        assert start is not None
        stop = self._stopparam()
        assert stop is not None
        n_points = self._numpointsparam()
        assert n_points is not None

        return np.linspace(start, stop, n_points)

class SpectrumArray(ParameterWithSetpoints):
    """
    Freequency sweep that returns a spectrum.
    """
    def get_raw(self) -> np.ndarray:
        assert isinstance(self.root_instrument, FSL)
        self.root_instrument.write_raw("INIT:CONT OFF") #set single sweep mode
        self.root_instrument.write_raw("ABOR") #abort and reset trigger
        self.root_instrument.write_raw("INIT") #start measurement
        self.root_instrument.ask_raw("*OPC?") #wait for measurement to complete
        spec = self.root_instrument.ask_raw("TRAC1? TRACE1").split(',')
        return np.array(spec).astype(np.float64)

class FSL(VisaInstrument):
    """
    QCoDeS driver for the Rhode & Schwarz spectrum analyzer FSL.
    """

    def __init__(self, name       : str,
                       address    : str,
                       terminator : str="\n",
                       timeout    : int=100000,
                       **kwargs):
        """Initializes the instrument

        Args:
            name (str): Name of the instrument
            address (str): Address of instrument
            terminator (str, optional): Terminator. Defaults to "\n".
            timeout (int, optional): Communication timeout in untis of s.
                                     Defaults to 100000.
        """

        super().__init__(name=name,
                         address=address,
                         terminator=terminator,
                         timeout=timeout,
                         **kwargs)

        self.add_parameter(name = 'center',
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

        self.add_parameter(name = 'start',
                           label = 'Start Frequency',
                           get_parser = float,
                           get_cmd = 'FREQ:START?',
                           set_cmd = 'FREQUENCY:START {}Hz',
                           unit = 'Hz',
                           vals = Numbers(min_value=float(self.ask_raw(
                                                    'SENS:FREQ:START? MIN')),
                                          max_value=float(self.ask_raw(
                                                    'SENS:FREQ:START? MAX'))))

        self.add_parameter(name = 'stop',
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
                           label = 'Analyzer Frequency',
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
