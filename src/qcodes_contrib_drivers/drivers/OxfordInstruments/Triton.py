# This Python file uses the following encoding: utf-8
# Etienne Dumur <etienne.dumur@gmail.com>, october 2020
import os
from typing import Optional
import pandas as pd
import subprocess
import time


from qcodes.instrument.base import Instrument


class Triton(Instrument):
    """
    This is the QCoDeS python driver to extract the temperature and pressure
    from a Oxford Triton fridge.
    """

    def __init__(self, name: str, file_path: str, converter_path: str,
                 threshold_temperature: float = 4, conversion_timer: float = 30,
                 magnet: bool = False, **kwargs) -> None:
        """
        QCoDeS driver for Oxford Triton fridges.
        ! This driver get parameters from the fridge log files.
        ! It does not interact with the fridge electronics.
        Since Oxford fridges use binary format for their log file "vcl", this
        driver convert vcl log files into csv files before returning fridge
        parameters.
        The conversion is done by using a binary file named
        "VCL_2_ASCII_CONVERTER.exe" that is provided by Oxford Instrument along
        with other binaries to handle the fridge log files.
        You must provide a valid path toward the VCL converter and consequently
        we advice users to make sure the converter is always reachable by the
        driver.

        Args:
            name: Name of the instrument.
            file_path: Path of the vcl log file.
            converter_path: Path of the vcl converter file.
            threshold_temperature: Threshold temperature of
                the mixing chamber thermometers.
                Defaults to 4K.
                Below, the temperature is read from the RuO2.
                Above, the temperature is read from the cernox.
            conversion_timer: Time between two vcl conversions.
                Defaults to 30s.
            magnet: Is there a magnet in the fridge.
                Default True.
        """

        if not os.path.isfile(converter_path):
            raise ValueError('converter_path is not a valid file path.')

        if not os.path.isfile(file_path):
            raise ValueError('file_path is not a valid file path.')
        
        super().__init__(name=name, **kwargs)
        
        self.file_path = os.path.abspath(file_path)
        self.threshold_temperature = threshold_temperature
        self.converter_path = os.path.abspath(converter_path)
        self.conversion_timer = conversion_timer
        self._timer = time.time()

        self.add_parameter(name='pressure_condensation_line',
                           unit='Bar',
                           get_parser=float,
                           get_cmd=lambda: self.get_pressure('condensation'),
                           docstring='Pressure of the condensation line',)

        self.add_parameter(name='pressure_mixture_tank',
                           unit='Bar',
                           get_parser=float,
                           get_cmd=lambda: self.get_pressure('tank'),
                           docstring='Pressure of the mixture tank',)

        self.add_parameter(name='pressure_forepump_back',
                           unit='Bar',
                           get_parser=float,
                           get_cmd=lambda: self.get_pressure('forepump'),
                           docstring='Pressure of the forepump back',)

        self.add_parameter(name='temperature_50k_plate',
                           unit='K',
                           get_parser=float,
                           get_cmd=lambda: self.get_temperature('50k'),
                           docstring='Temperature of the 50K plate',)

        self.add_parameter(name='temperature_4k_plate',
                           unit='K',
                           get_parser=float,
                           get_cmd=lambda: self.get_temperature('4k'),
                           docstring='Temperature of the 4K plate',)

        if magnet:
            self.add_parameter(name='temperature_magnet',
                               unit='K',
                               get_parser=float,
                               get_cmd=lambda: self.get_temperature('magnet'),
                               docstring='Temperature of the magnet',)

        self.add_parameter(name='temperature_still',
                           unit='K',
                           get_parser=float,
                           get_cmd=lambda: self.get_temperature('still'),
                           docstring='Temperature of the still',)

        self.add_parameter(name='temperature_100mk',
                           unit='K',
                           get_parser=float,
                           get_cmd=lambda: self.get_temperature('100mk'),
                           docstring='Temperature of the 100mk plate',)

        self.add_parameter(name='temperature_mixing_chamber',
                           unit='K',
                           get_parser=float,
                           get_cmd=lambda: self.get_temperature('mc'),
                           docstring='Temperature of the mixing chamber',)
        
        self.connect_message()

    def vcl2csv(self) -> Optional[str]:
        """
        Convert vcl file into csv file using proprietary binary exe.
        The executable is called through the python subprocess library.
        To avoid to frequent file conversion, a timer of self.conversion_timer
        second is used.

        Returns:
            str: The output of the bash command
        """
        
        conversion = False
        if self._timer+self.conversion_timer <= time.time():
            conversion = True
        elif not os.path.isfile(self.file_path[:-3]+'txt'):
            conversion = True

        if conversion:
            self._timer = time.time()
            
            # Run a bash command to convert vcl into csv
            cp = subprocess.run([self.converter_path, self.file_path],
                                stdout=subprocess.PIPE,
                                universal_newlines=True,
                                shell=True)
    
            return cp.stdout
        else:
            return None

    def get_temperature(self, channel: str) -> float:
        """
        Return the last registered temperature of the channel.
        
        Args:
            channel: Channel from which the temperature is extracted.

        Returns:
            temperature: Temperature of the channel in Kelvin.
        """

        # Convert the vcl file into csv file
        self.vcl2csv()
        
        df = pd.read_csv(self.file_path[:-3]+'txt', delimiter="\t")

        if channel == '50k':
            return df.iloc[-1]['PT1 Plate T(K)']
        elif channel == '4k':
            return df.iloc[-1]['PT2 Plate T(K)']
        elif channel == 'magnet':
            return df.iloc[-1]['Magnet T(K)']
        elif channel == 'still':
            return df.iloc[-1]['Still T(K)']
        elif channel == '100mk':
            return df.iloc[-1]['100mK Plate T(K)']
        elif channel == 'mc':
            # There are two thermometers for the mixing chamber.
            # Depending of the threshold temperature we return one or the other
            temp = df.iloc[-1]['MC cernox T(K)']
            
            if temp > self.threshold_temperature:
                return temp
            else:
                return df.iloc[-1]['MC RuO2 T(K)']
        else:
            raise ValueError('Unknown channel: '+channel)

    def get_pressure(self, channel: str) -> float:
        """
        Return the last registered pressure of the channel.
        
        Args:
            channel: Channel from which the pressure is extracted.

        Returns:
            pressure: Pressure of the channel in Bar.
        """
        
        # Convert the vcl file into csv file
        self.vcl2csv()
        
        df = pd.read_csv(self.file_path[:-3]+'txt', delimiter="\t")
        
        if channel == 'condensation':
            return df.iloc[-1]['P2 Condense (Bar)']
        elif channel == 'tank':
            return df.iloc[-1]['P1 Tank (Bar)']
        elif channel == 'forepump':
            return df.iloc[-1]['P5 ForepumpBack (Bar)']
        else:
            raise ValueError('Unknown channel: '+channel)
