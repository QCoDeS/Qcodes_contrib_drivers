# This Python file uses the following encoding: utf-8
# Etienne Dumur <etienne.dumur@gmail.com>, august 2020
# Simon Zihlmannr <zihlmann.simon@gmail.com>, february/march 2021
import logging
import numpy as np
from typing import Tuple, Optional

from qcodes import VisaInstrument
from qcodes.utils.validators import Numbers, Enum, Ints
from qcodes.utils.helpers import create_on_off_val_mapping

from qcodes.instrument.parameter import (
    MultiParameter,
    ParamRawDataType
)

log = logging.getLogger(__name__)

class FrequencySweepMagPhase(MultiParameter):
    """
    Sweep that returns magnitude and phase.
    """

    def __init__(self,
        name: str,
        start: float,
        stop: float,
        npts: int,
        instrument: "M5180",
        ) -> None:
        """
        Linear frequency sweep that returns magnitude and phase for a single
        trace.

        Args:
            name (str): Name of the linear frequency sweep
            start (float): Start frequency of linear sweep
            stop (float): Stop frequency of linear sweep
            npts (int): Number of points of linear sweep
            instrument: Instrument to which sweep is bound to.
        """
        super().__init__(
            name,
            instrument=instrument,
            names=(
                f"{instrument.short_name}_{name}_magnitude",
                f"{instrument.short_name}_{name}_phase"),
            labels=(
                f"{instrument.short_name} {name} magnitude",
                f"{instrument.short_name} {name} phase",
            ),
            units=("dB", "rad"),
            setpoint_units=(("Hz",), ("Hz",)),
            setpoint_labels=(
                (f"{instrument.short_name} frequency",),
                (f"{instrument.short_name} frequency",),
            ),
            setpoint_names=(
                (f"{instrument.short_name}_frequency",),
                (f"{instrument.short_name}_frequency",),
            ),
            shapes=((npts,), (npts,),),
        )
        self.set_sweep(start, stop, npts)

    def set_sweep(self, start: float, stop: float, npts: int) -> None:
        """Updates the setpoints and shapes based on start, stop and npts.

        Args:
            start (float): start frequency
            stop (float): stop frequency
            npts (int): number of points
        """
        f = tuple(np.linspace(int(start), int(stop), num=npts))
        self.setpoints = ((f,), (f,))
        self.shapes = ((npts,), (npts,))

    def get_raw(self) -> Tuple[ParamRawDataType, ParamRawDataType]:
        """Gets data from instrument

        Returns:
            Tuple[ParamRawDataType, ...]: magnitude, phase
        """
        assert isinstance(self.instrument, M5180)
        self.instrument.write('CALC1:PAR:COUN 1') # 1 trace
        self.instrument.write('CALC1:PAR1:DEF {}'.format(self.name))
        self.instrument.write('CALC1:TRAC1:FORM SMITH')  # Trace format
        self.instrument.trigger_source('bus') # set the trigger to bus
        self.instrument.write('TRIG:SEQ:SING') # Trigger a single sweep
        self.instrument.ask('*OPC?') # Wait for measurement to complete

        # get data from instrument
        sxx_raw = self.instrument.ask("CALC1:TRAC1:DATA:FDAT?")

        # Get data as numpy array
        sxx = np.fromstring(sxx_raw, dtype=float, sep=',')
        sxx = sxx[0::2] + 1j*sxx[1::2]

        return self.instrument._db(sxx), np.unwrap(np.angle(sxx))


class PointMagPhase(MultiParameter):
    """
    Returns the first point of a sweep (at start frequency).
    Work around for a CW mode where only one point is read.
    Ideally, npts is set to 2 and stop = start + 1 (in Hz), this will maximize
    the measurement speed.
    """

    def __init__(self,
        name: str,
        start: float,
        stop: float,
        npts: int,
        instrument: "M5180",
        ) -> None:
        """Magnitude and phase measurement of a single point at start
        frequency.

        Args:
            name (str): Name of point measurement
            start (float): Start frequency (frequency at which it will measure)
            stop (float): Stop frequency, ideally start - 1 Hz
            npts (int): Number of points of the sweep, ideally 2
            instrument:  Instrument to which sweep is bound to.
        """

        super().__init__(
            name,
            instrument=instrument,
            names=(
                f"{instrument.short_name}_{name}_magnitude",
                f"{instrument.short_name}_{name}_phase"),
            labels=(
                f"{instrument.short_name} {name} magnitude",
                f"{instrument.short_name} {name} phase",
            ),
            units=("dB", "rad"),
            setpoint_units=(("Hz",), ("Hz",)),
            setpoint_labels=(
                (f"{instrument.short_name} frequency",),
                (f"{instrument.short_name} frequency",),
            ),
            setpoint_names=(
                (f"{instrument.short_name}_frequency",),
                (f"{instrument.short_name}_frequency",),
            ),
            shapes=((npts,), (npts,),),
        )
        self.set_sweep(start, stop, npts)

    def set_sweep(self, start: float, stop: float, npts: int) -> None:
        """Updates the setpoints and shapes based on start, stop and npts.

        Args:
            start (float): start frequency
            stop (float): stop frequency, not used
            npts (int): number of points, not used
        """
        f = tuple(np.linspace(int(start), int(stop), num=npts))
        self.setpoints = ((start,), (start,))
        self.shapes = ((), ())

    def get_raw(self) -> Tuple[ParamRawDataType, ParamRawDataType]:
        """Gets data from instrument

        Returns:
            Tuple[ParamRawDataType, ...]: magnitude, phase
        """
        assert isinstance(self.instrument, M5180)
        self.instrument.write('CALC1:PAR:COUN 1') # 1 trace
        self.instrument.write('CALC1:PAR1:DEF {}'.format(self.name[-3:]))
        self.instrument.write('CALC1:TRAC1:FORM SMITH')  # Trace format
        self.instrument.trigger_source('bus') # set the trigger to bus
        self.instrument.write('TRIG:SEQ:SING') # Trigger a single sweep
        self.instrument.ask('*OPC?') # Wait for measurement to complete

        # get data from instrument
        sxx_raw = self.instrument.ask("CALC1:TRAC1:DATA:FDAT?")

        # Get data as numpy array
        sxx = np.fromstring(sxx_raw, dtype=float, sep=',')
        sxx = sxx[0::2] + 1j*sxx[1::2]

        # Return only the first point of the trace, which will have "start" as
        # its setpoint
        return self.instrument._db(sxx[0]), np.angle(sxx[0])


class M5180(VisaInstrument):
    """
    This is the QCoDeS python driver for the VNA M5180 from Copper Mountain
    """

    def __init__(self, name       : str,
                       address    : str,
                       terminator : str="\n",
                       timeout    : int=100000,
                       **kwargs):
        """
        QCoDeS driver for the VNA S5180 from Copper Mountain

        Args:
        name (str): Name of the instrument.
        address (str): Address of the instrument.
        terminator (str, optional, default "\n"): Terminator character of
            the string reply.
        timeout (int, optional, default 100000): VISA timeout is set purposely
            to a long time to allow long spectrum measurement.
        """

        super().__init__(name       = name,
                         address    = address,
                         terminator = terminator,
                         timeout    = timeout,
                         **kwargs)

        self.add_function('reset', call_cmd='*RST')

        self.add_parameter(name='output',
                           label='Output',
                           get_parser=str,
                           get_cmd='OUTP:STAT?',
                           set_cmd='OUTP:STAT {}',
                           val_mapping=create_on_off_val_mapping(on_val='1',
                                                                 off_val='0'))

        self.add_parameter(name='power',
                           label='Power',
                           get_parser=float,
                           get_cmd='SOUR:POW?',
                           set_cmd='SOUR:POW {}',
                           unit='dBm',
                           vals=Numbers(min_value=-50,
                                        max_value=10))

        self.add_parameter(name='if_bandwidth',
                           label='IF Bandwidth',
                           get_parser=float,
                           get_cmd='SENS1:BWID?',
                           set_cmd='SENS1:BWID {}',
                           unit='Hz',
                           vals=Enum(1, 3, 1e1, 3e1, 1e2, 3e2,
                                     1e3, 3e3, 1e4, 3e4, 1e5, 3e5))

        self.add_parameter('averages_enabled',
                           label='Averages Status',
                           get_cmd='SENS1:AVER:STAT?',
                           set_cmd='SENS1:AVER:STAT {}',
                           val_mapping=create_on_off_val_mapping(on_val='1',
                                                                 off_val='0'))

        self.add_parameter('averages_trigger_enabled',
                           label='Trigger average status',
                           get_cmd='TRIG:SEQ:AVER?',
                           set_cmd='TRIG:SEQ:AVER {}',
                           val_mapping=create_on_off_val_mapping(on_val='1',
                                                                 off_val='0'))

        self.add_parameter('averages',
                           label='Averages',
                           get_cmd='SENS1:AVER:COUN?',
                           set_cmd='SENS1:AVER:COUN {}',
                           get_parser=int,
                           set_parser=int,
                           unit='',
                           vals=Numbers(min_value=1, max_value=999))

        self.add_parameter(name='start',
                           label='Start Frequency',
                           get_parser=float,
                           get_cmd='SENS1:FREQ:STAR?',
                           set_cmd=self._set_start,
                           unit='Hz',
                           vals=Numbers(min_value=100e3,
                                        max_value=18e9))

        self.add_parameter(name='stop',
                           label='Stop Frequency',
                           get_parser=float,
                           get_cmd='SENS1:FREQ:STOP?',
                           set_cmd=self._set_stop,
                           unit='Hz',
                           vals=Numbers(min_value=100e3,
                                        max_value=18e9))

        self.add_parameter(name='center',
                           label='Center Frequency',
                           get_parser=float,
                           get_cmd='SENS1:FREQ:CENT?',
                           set_cmd=self._set_center,
                           unit='Hz',
                           vals=Numbers(min_value=100e3,
                                        max_value=18e9))

        self.add_parameter(name='span',
                           label='Frequency Span',
                           get_parser=float,
                           get_cmd='SENS1:FREQ:SPAN?',
                           set_cmd=self._set_span,
                           unit='Hz',
                           vals=Numbers(min_value=100e3,
                                        max_value=18e9))

        self.add_parameter('npts',
                           label='Number of points',
                           get_parser=int,
                           set_parser=int,
                           get_cmd='SENS1:SWE:POIN?',
                           set_cmd=self._set_npts,
                           unit='',
                           vals=Ints(min_value=2,
                                        max_value=200001))

        self.add_parameter('nb_traces',
                           label='Number of traces',
                           get_parser=int,
                           set_parser=int,
                           get_cmd='CALC1:PAR:COUN?',
                           set_cmd='CALC1:PAR:COUN {}',
                           unit='',
                           vals=Ints(min_value=1,
                                     max_value=16))

        self.add_parameter(name='trigger_source',
                           label='Trigger source',
                           get_parser=str,
                           get_cmd=self._get_trigger,
                           set_cmd=self._set_trigger,
                           vals = Enum('bus', 'external', 'internal', 'manual'))

        self.add_parameter(name='data_transfer_format',
                           label='Data format during transfer',
                           get_parser=str,
                           get_cmd='FORM:DATA?',
                           set_cmd='FORM:DATA {}',
                           vals = Enum('ascii', 'real', 'real32'))

        self.add_parameter(name='s11',
                           start=self.start(),
                           stop=self.stop(),
                           npts=self.npts(),
                           parameter_class=FrequencySweepMagPhase)

        self.add_parameter(name='s12',
                           start=self.start(),
                           stop=self.stop(),
                           npts=self.npts(),
                           parameter_class=FrequencySweepMagPhase)

        self.add_parameter(name='s21',
                           start=self.start(),
                           stop=self.stop(),
                           npts=self.npts(),
                           parameter_class=FrequencySweepMagPhase)

        self.add_parameter(name='s22',
                           start=self.start(),
                           stop=self.stop(),
                           npts=self.npts(),
                           parameter_class=FrequencySweepMagPhase)

        self.add_parameter(name='point_s11',
                           start=self.start(),
                           stop=self.stop(),
                           npts=self.npts(),
                           parameter_class=PointMagPhase)

        self.add_parameter(name='point_s12',
                           start=self.start(),
                           stop=self.stop(),
                           npts=self.npts(),
                           parameter_class=PointMagPhase)

        self.add_parameter(name='point_s21',
                           start=self.start(),
                           stop=self.stop(),
                           npts=self.npts(),
                           parameter_class=PointMagPhase)

        self.add_parameter(name='point_s22',
                           start=self.start(),
                           stop=self.stop(),
                           npts=self.npts(),
                           parameter_class=PointMagPhase)

        self.connect_message()

    def _set_start(self, val: float) -> None:
        """Sets the start frequency and updates linear trace parameters.

        Args:
            val (float): start frequency to be set

        Raises:
            ValueError: If start > stop
        """
        stop = self.stop()
        if val >= stop:
            raise ValueError("Stop frequency must be larger than start "
                             "frequency.")
        self.write("SENS1:FREQ:STAR {}".format(val))
        # we get start as the vna may not be able to set it to the
        # exact value provided.
        start = self.start()
        if abs(val - start) >= 1:
            log.warning(
                "Could not set start to {} setting it to "
                "{}".format(val, start)
            )
        self.update_lin_traces()

    def _set_stop(self, val: float) -> None:
        """Sets the start frequency and updates linear trace parameters.

        Args:
            val (float): start frequency to be set

        Raises:
            ValueError: If stop < start
        """
        start = self.start()
        if val <= start:
            raise ValueError("Stop frequency must be larger than start "
                             "frequency.")
        self.write("SENS1:FREQ:STOP {}".format(val))
        # We get stop as the vna may not be able to set it to the
        # exact value provided.
        stop = self.stop()
        if abs(val - stop) >= 1:
            log.warning(
                "Could not set stop to {} setting it to "
                "{}".format(val, stop)
            )
        self.update_lin_traces()

    def _set_span(self, val: float) -> None:
        """Sets frequency span and updates linear trace parameters.

        Args:
            val (float): frequency span to be set
        """
        self.write("SENS1:FREQ:SPAN {}".format(val))
        self.update_lin_traces()

    def _set_center(self, val: float) -> None:
        """Sets center frequency and updates linear trace parameters.

        Args:
            val (float): center frequency to be set
        """
        self.write("SENS1:FREQ:CENT {}".format(val))
        self.update_lin_traces()

    def _set_npts(self, val: int) -> None:
        """Sets number of points and updates linear trace parameters.

        Args:
            val (int): number of points to be set.
        """
        self.write("SENS1:SWE:POIN {}".format(val))
        self.update_lin_traces()

    def _get_trigger(self) -> str:
        """Gets trigger source.

        Returns:
            str: Trigger source.
        """
        r = self.ask('TRIG:SOUR?')

        if r.lower()=='int':
            return 'internal'
        elif r.lower()=='ext':
            return 'external'
        elif r.lower()=='man':
            return 'manual'
        else:
            return 'bus'

    def _set_trigger(self, trigger: str) -> None:
        """Sets trigger source.

        Args:
            trigger (str): Trigger source
        """
        self.write('TRIG:SOUR '+trigger.upper())

    def get_s(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray,
                             np.ndarray, np.ndarray, np.ndarray, np.ndarray,
                             np.ndarray]:
        """
        Return all S parameters as magnitude in dB and phase in rad.

        Returns:
            Tuple[np.ndarray]: frequency [GHz],
                               s11 magnitude [dB], s11 phase [rad],
                               s12 magnitude [dB], s12 phase [rad],
                               s21 magnitude [dB], s21 phase [rad],
                               s22 magnitude [dB], s22 phase [rad]
        """

        self.write('CALC1:PAR:COUN 4') # 4 trace
        self.write('CALC1:PAR1:DEF S11') # Choose S11 for trace 1
        self.write('CALC1:PAR2:DEF S12') # Choose S12 for trace 2
        self.write('CALC1:PAR3:DEF S21') # Choose S21 for trace 3
        self.write('CALC1:PAR4:DEF S22') # Choose S22 for trace 4
        self.write('CALC1:TRAC1:FORM SMITH')  # Trace format
        self.write('CALC1:TRAC2:FORM SMITH')  # Trace format
        self.write('CALC1:TRAC3:FORM SMITH')  # Trace format
        self.write('CALC1:TRAC4:FORM SMITH')  # Trace format
        self.write('TRIG:SEQ:SING') # Trigger a single sweep
        self.ask('*OPC?') # Wait for measurement to complete

        # Get data as string
        freq_raw = self.ask("SENS1:FREQ:DATA?")
        s11_raw = self.ask("CALC1:TRAC1:DATA:FDAT?")
        s12_raw = self.ask("CALC1:TRAC2:DATA:FDAT?")
        s21_raw = self.ask("CALC1:TRAC3:DATA:FDAT?")
        s22_raw = self.ask("CALC1:TRAC4:DATA:FDAT?")

        # Get data as numpy array
        freq = np.fromstring(freq_raw, dtype=float, sep=',')
        s11 = np.fromstring(s11_raw, dtype=float, sep=',')
        s11 = s11[0::2] + 1j*s11[1::2]
        s12 = np.fromstring(s12_raw, dtype=float, sep=',')
        s12 = s12[0::2] + 1j*s12[1::2]
        s21 = np.fromstring(s21_raw, dtype=float, sep=',')
        s21 = s21[0::2] + 1j*s21[1::2]
        s22 = np.fromstring(s22_raw, dtype=float, sep=',')
        s22 = s22[0::2] + 1j*s22[1::2]

        return (np.array(freq), self._db(s11), np.array(np.angle(s11)),
                                self._db(s12), np.array(np.angle(s12)),
                                self._db(s21), np.array(np.angle(s21)),
                                self._db(s22), np.array(np.angle(s22)))

    def update_lin_traces(self) -> None:
        """
        Updates start, stop and npts of all trace parameters so that the
        setpoints and shape are updated for the sweep.
        """
        start = self.start()
        stop = self.stop()
        npts = self.npts()
        for _, parameter in self.parameters.items():
            if isinstance(parameter, (FrequencySweepMagPhase, PointMagPhase)):
                try:
                    parameter.set_sweep(start, stop, npts)
                except AttributeError:
                    pass

    def reset_averages(self) -> None:
        """
        Resets average count to 0
        """
        self.write("SENS1.AVER.CLE")

    @staticmethod
    def _db(data: np.ndarray) -> np.ndarray:
        """
        Return dB from magnitude

        Args:
            data (np.ndarray): data to be transformed into dB.

        Returns:
            data (np.ndarray): data transformed in dB.
        """

        return 20.*np.log10(np.abs(data))
