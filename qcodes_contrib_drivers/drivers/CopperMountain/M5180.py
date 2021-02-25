# This Python file uses the following encoding: utf-8
# Etienne Dumur <etienne.dumur@gmail.com>, august 2020
import numpy as np
from typing import Tuple

from qcodes import VisaInstrument
from qcodes.utils.validators import Numbers, Enum, Ints


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
        terminator (str, optional, by default "\n"): Terminator character of
            the string reply.
        timeout (int, optional, by default 100000): VISA timeout is set purposly
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
                           get_cmd=lambda : self._get_output,
                           set_cmd=lambda a: self._set_output(a),
                           vals=Enum('on', 'off'))
        
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
        
        self.add_parameter(name='start_frequency',
                           label='Start Frequency',
                           get_parser=float,
                           get_cmd='SENS1:FREQ:STAR?',
                           set_cmd='SENS1:FREQ:STAR {}',
                           unit='Hz',
                           vals=Numbers(min_value=100e3,
                                        max_value=18e9))
        
        self.add_parameter(name='stop_frequency',
                           label='Stop Frequency',
                           get_parser=float,
                           get_cmd='SENS1:FREQ:STOP?',
                           set_cmd='SENS1:FREQ:STOP {}',
                           unit='Hz',
                           vals=Numbers(min_value=100e3,
                                        max_value=18e9))
        
        self.add_parameter(name='center_frequency',
                           label='Center Frequency',
                           get_parser=float,
                           get_cmd='SENS1:FREQ:CENT?',
                           set_cmd='SENS1:FREQ:CENT {}',
                           unit='Hz',
                           vals=Numbers(min_value=100e3,
                                        max_value=18e9))
        
        self.add_parameter(name='span_frequency',
                           label='Frequency Span',
                           get_parser=float,
                           get_cmd='SENS1:FREQ:SPAN?',
                           set_cmd='SENS1:FREQ:SPAN {}',
                           unit='Hz',
                           vals=Numbers(min_value=100e3,
                                        max_value=18e9))
        
        self.add_parameter('nb_points',
                           label='Number of points',
                           get_parser=int,
                           get_cmd='SENS1:SWE:POIN?',
                           set_cmd='SENS1:SWE:POIN {}',
                           unit='',
                           vals=Ints(min_value=1,
                                        max_value=200001))

        self.add_parameter('nb_traces',
                           label='Number of traces',
                           get_parser=int,
                           get_cmd='CALC1:PAR:COUN?',
                           set_cmd='CALC1:PAR:COUN {}',
                           unit='',
                           vals=Ints(min_value=1,
                                     max_value=16))
        
        self.add_parameter(name='trigger_source',
                           label='Trigger source',
                           get_parser=str,
                           get_cmd=lambda : self._get_trigger,
                           set_cmd =lambda a: self._set_trigger(a),
                           vals = Enum('bus', 'external', 'internal', 'manual'))
        
        self.add_parameter(name='data_transfer_format',
                           label='Data format during transfer',
                           get_parser=str,
                           get_cmd='FORM:DATA?',
                           set_cmd='FORM:DATA {}',
                           vals = Enum('ascii', 'real', 'real32'))
        
        self.connect_message()
        

    def _get_trigger(self) -> str:
        
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
        
        self.write('TRIG:SOUR '+trigger.upper())

    def _get_output(self) -> str:
        
        r = self.ask('OUTP:STAT?')
        
        if r==1:
            return 'on'
        else:
            return 'off'

    def _set_output(self, output: str) -> None:

        
        if output.lower()=='on':
            self.write('OUTP:STAT 1')
        else:
            self.write('OUTP:STAT 0')

    def get_s11(self) -> Tuple[np.ndarray]:
        """
        Return S11 parameter as magnitude in dB and phase in rad.

        Returns:
            Tuple[np.ndarray]: frequency [GHz], magnitude [dB], phase [rad]
        """
        
        self.write('CALC1:PAR:COUN 1') # 1 trace
        self.write('CALC1:PAR1:DEF S11') # Choose S11 for trace 1
        self.write('CALC1:TRAC1:FORM SMITH')  # Trace format
        self.write('TRIG:SEQ:SING') # Trigger a single sweep
        self.ask('*OPC?') # Wait for measurement to complete
        
        # Get data as string
        freq = self.ask("SENS1:FREQ:DATA?") 
        s11 = self.ask("CALC1:TRAC1:DATA:FDAT?")
        
        # Get data as numpy array
        freq = np.fromstring(freq, dtype=float, sep=',')
        s11 = np.fromstring(s11, dtype=float, sep=',')
        s11 = s11[0::2] + 1j*s11[1::2]
        
        return freq, self._db(s11), np.angle(s11)

    def get_s12(self) -> Tuple[np.ndarray]:
        """
        Return S12 parameter as magnitude in dB and phase in rad.

        Returns:
            Tuple[np.ndarray]: frequency [GHz], magnitude [dB], phase [rad]
        """
        
        self.write('CALC1:PAR:COUN 1') # 1 trace
        self.write('CALC1:PAR1:DEF S12') # Choose S12 for trace 1
        self.write('CALC1:TRAC1:FORM SMITH')  # Trace format
        self.write('TRIG:SEQ:SING') # Trigger a single sweep
        self.ask('*OPC?') # Wait for measurement to complete
        
        # Get data as string
        freq = self.ask("SENS1:FREQ:DATA?") 
        s12 = self.ask("CALC1:TRAC1:DATA:FDAT?")
        
        # Get data as numpy array
        freq = np.fromstring(freq, dtype=float, sep=',')
        s12 = np.fromstring(s12, dtype=float, sep=',')
        s12 = s12[0::2] + 1j*s12[1::2]
        
        return freq, self._db(s12), np.angle(s12)

    def get_s21(self) -> Tuple[np.ndarray]:
        """
        Return S21 parameter as magnitude in dB and phase in rad.

        Returns:
            Tuple[np.ndarray]: frequency [GHz], magnitude [dB], phase [rad]
        """
        
        self.write('CALC1:PAR:COUN 1') # 1 trace
        self.write('CALC1:PAR1:DEF S21') # Choose S21 for trace 1
        self.write('CALC1:TRAC1:FORM SMITH')  # Trace format
        self.write('TRIG:SEQ:SING') # Trigger a single sweep
        self.ask('*OPC?') # Wait for measurement to complete
        
        # Get data as string
        freq = self.ask("SENS1:FREQ:DATA?") 
        s21 = self.ask("CALC1:TRAC1:DATA:FDAT?")
        
        # Get data as numpy array
        freq = np.fromstring(freq, dtype=float, sep=',')
        s21 = np.fromstring(s21, dtype=float, sep=',')
        s21 = s21[0::2] + 1j*s21[1::2]
        
        return freq, self._db(s21), np.angle(s21)

    def get_s22(self) -> Tuple[np.ndarray]:
        """
        Return S22 parameter as magnitude in dB and phase in rad.

        Returns:
            Tuple[np.ndarray]: frequency [GHz], magnitude [dB], phase [rad]
        """
        
        self.write('CALC1:PAR:COUN 1') # 1 trace
        self.write('CALC1:PAR1:DEF S22') # Choose S22 for trace 1
        self.write('CALC1:TRAC1:FORM SMITH')  # Trace format
        self.write('TRIG:SEQ:SING') # Trigger a single sweep
        self.ask('*OPC?') # Wait for measurement to complete
        
        # Get data as string
        freq = self.ask("SENS1:FREQ:DATA?") 
        s22 = self.ask("CALC1:TRAC1:DATA:FDAT?")
        
        # Get data as numpy array
        freq = np.fromstring(freq, dtype=float, sep=',')
        s22 = np.fromstring(s22, dtype=float, sep=',')
        s22 = s22[0::2] + 1j*s22[1::2]
        
        return freq, self._db(s22), np.angle(s22)

    def get_s(self) -> Tuple[np.ndarray]:
        """
        Return S parameter as magnitude in dB and phase in rad.

        Returns:
            Tuple[np.ndarray]: frequency [GHz],
                               s11 magnitude [dB], s11 phase [rad],
                               s12 magnitude [dB], s12 phase [rad],
                               s21 magnitude [dB], s21 phase [rad],
                               s22 magnitude [dB], s22 phase [rad]
        """
        
        self.write('CALC1:PAR:COUN 4') # 4 trace
        self.write('CALC1:PAR1:DEF S11') # Choose S22 for trace 1
        self.write('CALC1:PAR2:DEF S12') # Choose S22 for trace 2
        self.write('CALC1:PAR3:DEF S21') # Choose S22 for trace 3
        self.write('CALC1:PAR4:DEF S22') # Choose S22 for trace 4
        self.write('CALC1:TRAC1:FORM SMITH')  # Trace format
        self.write('CALC1:TRAC2:FORM SMITH')  # Trace format
        self.write('CALC1:TRAC3:FORM SMITH')  # Trace format
        self.write('CALC1:TRAC4:FORM SMITH')  # Trace format
        self.write('TRIG:SEQ:SING') # Trigger a single sweep
        self.ask('*OPC?') # Wait for measurement to complete
        
        # Get data as string
        freq = self.ask("SENS1:FREQ:DATA?") 
        s11 = self.ask("CALC1:TRAC1:DATA:FDAT?")
        s12 = self.ask("CALC1:TRAC2:DATA:FDAT?")
        s21 = self.ask("CALC1:TRAC3:DATA:FDAT?")
        s22 = self.ask("CALC1:TRAC4:DATA:FDAT?")
        
        # Get data as numpy array
        freq = np.fromstring(freq, dtype=float, sep=',')
        s11 = np.fromstring(s11, dtype=float, sep=',')
        s11 = s11[0::2] + 1j*s11[1::2]
        s12 = np.fromstring(s12, dtype=float, sep=',')
        s12 = s12[0::2] + 1j*s12[1::2]
        s21 = np.fromstring(s21, dtype=float, sep=',')
        s21 = s21[0::2] + 1j*s21[1::2]
        s22 = np.fromstring(s22, dtype=float, sep=',')
        s22 = s22[0::2] + 1j*s22[1::2]
        
        return (freq, self._db(s11), np.angle(s11),
                      self._db(s12), np.angle(s12),
                      self._db(s21), np.angle(s21),
                      self._db(s22), np.angle(s22))
    
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