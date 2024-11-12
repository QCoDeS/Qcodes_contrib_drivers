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
        npts = self._numpointsparam()
        assert npts is not None

        return np.linspace(start, stop, npts)

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

        self._span_min = float(self.ask_raw('SENS:FREQ:SPAN? MIN'))
        self._span_max = float(self.ask_raw('SENS:FREQ:SPAN? MAX'))
        self._start_min = float(self.ask_raw('SENS:FREQ:START? MIN'))
        self._start_max = float(self.ask_raw('SENS:FREQ:START? MAX'))
        self._stop_min = float(self.ask_raw('SENS:FREQ:STOP? MIN'))
        self._stop_max = float(self.ask_raw('SENS:FREQ:STOP? MAX'))
        self._center_min = float(self.ask_raw('SENS:FREQ:CENT? MIN'))
        self._center_max = float(self.ask_raw('SENS:FREQ:CENT? MAX'))
        self._rlevel_min = float(self.ask_raw('DISP:TRAC:Y:RLEV? MIN'))
        self._rlevel_max = float(self.ask_raw('DISP:TRAC:Y:RLEV? MAX'))
        self._bw_min = float(self.ask_raw('SENS:BAND:RES? MIN'))
        self._bw_max = float(self.ask_raw('SENS:BAND:RES? MAX'))
        self._video_bw_min = float(self.ask_raw('SENS:BAND:VID? MIN'))
        self._video_bw_max = float(self.ask_raw('SENS:BAND:VID? MAX'))
        self._npts_min = float(self.ask_raw('SWE:POIN? MIN'))
        self._npts_max = float(self.ask_raw('SWE:POIN? MAX'))


        self.add_parameter(name = 'center',
                           label = 'Center Frequency',
                           get_parser = float,
                           get_cmd = 'FREQ:CENT?',
                           set_cmd = 'FREQUENCY:CENTER {}Hz',
                           unit = 'Hz',
                           vals = Numbers(min_value=self._center_min,
                                          max_value=self._center_max))

        self.add_parameter(name = 'span',
                           label = 'Span',
                           get_parser = float,
                           get_cmd = 'FREQ:SPAN?',
                           set_cmd = 'FREQUENCY:SPAN {}Hz',
                           unit = 'Hz',
                           vals = Numbers(min_value=self._span_min,
                                          max_value=self._span_max))

        self.add_parameter(name = 'start',
                           label = 'Start Frequency',
                           get_parser = float,
                           get_cmd = 'FREQ:START?',
                           set_cmd = 'FREQUENCY:START {}Hz',
                           unit = 'Hz',
                           vals = Numbers(min_value=self._start_min,
                                          max_value=self._start_max))

        self.add_parameter(name = 'stop',
                           label = 'Stop Frequency',
                           get_parser = float,
                           get_cmd = 'FREQ:STOP?',
                           set_cmd = 'FREQUENCY:STOP {}Hz',
                           unit = 'Hz',
                           vals = Numbers(min_value=self._stop_min,
                                          max_value=self._stop_max))

        self.add_parameter(name = 'rlevel',
                           label = 'Power Reference Level',
                           get_parser = float,
                           get_cmd = 'DISP:TRAC:Y:RLEV?',
                           set_cmd = 'DISPLAY:TRACE:Y:RLEVEL {}dBm',
                           unit = 'dBm',
                           vals = Numbers(min_value=self._rlevel_min,
                                          max_value=self._rlevel_max))

        self.add_parameter(name = 'bw',
                           label = 'Resolution Bandwidth',
                           get_parser = float,
                           get_cmd = 'BAND:RES?',
                           set_cmd = 'BAND:RES {}Hz',
                           unit = 'Hz',
                           vals = Numbers(min_value=self._bw_min,
                                          max_value=self._bw_max))

        self.add_parameter(name = 'video_bw',
                           label = 'Video Bandwidth',
                           get_parser = float,
                           get_cmd = 'BAND:VID?',
                           set_cmd = 'BAND:VID {}Hz',
                           unit = 'Hz',
                           vals = Numbers(min_value=self._video_bw_min,
                                          max_value=self._video_bw_max))

        self.add_parameter(name = 'npts',
                           unit = '',
                           get_parser = int,
                           get_cmd = 'SWE:POIN?',
                           set_cmd = self._set_npts,
                           vals = Numbers(min_value=self._npts_min,
                                          max_value=self._npts_max))

        self.add_parameter(name = 'freq_axis',
                           unit = 'Hz',
                           label = 'Analyzer Frequency',
                           parameter_class = GeneratedSetPoints,
                           startparam = self.start,
                           stopparam = self.stop,
                           numpointsparam = self.npts,
                           vals = Arrays(shape=(self.npts(),)))

        self.add_parameter(name = 'spectrum',
                           unit = 'dBm',
                           setpoints = (self.freq_axis,),
                           label = 'Spectrum',
                           parameter_class = SpectrumArray,
                           vals = Arrays(shape=(self.npts(),)))

        self.add_parameter(name = 'point_power',
                           unit = 'dBm',
                           label = 'Power',
                           vals = Numbers(-np.inf, np.inf),
                           get_cmd = self._get_point_power,
                           )

        self.connect_message()

    def reset(self) -> None:
        self.root_instrument.write_raw('*CLS')
        self.root_instrument.write_raw('*RST')

    def _get_point_power(self,) -> float:
        # set smallest number of points
        self.npts(self._npts_min)
        self.span(self._span_min)
        return np.mean(self.spectrum())

    def _set_npts(self, val:int) -> None:
        self.write_raw('SWE:POIN {}'.format(val))
        self.spectrum.vals = Arrays(shape=(self.npts(),))
        self.freq_axis.vals = Arrays(shape=(self.npts(),))
