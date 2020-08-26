# This Python file uses the following encoding: utf-8
# Etienne Dumur <etienne.dumur@gmail.com>, august 2020


from qcodes import VisaInstrument
from qcodes.utils.validators import Numbers


class Agilent_N9000A(VisaInstrument):
    """
    This is the QCoDeS python driver for the Agilent CXA N9000A power spectrum
    analyzer.
    """


    def __init__(self, name       : str,
                       address    : str,
                       terminator : str="\n",
                       **kwargs):
        """
        QCoDeS driver for the power spectrum analyzer Agilent N9000A.

        Args:
        name (str): Name of the instrument.
        address (str): Address of the instrument.
        terminator (str, optional, by default "\n"): Terminator character of
            the string reply.
        """


        super().__init__(name       = name,
                         address    = address,
                         terminator = terminator,
                         **kwargs)


        self.add_function('reset', call_cmd='*RST')


        self.add_parameter(name       = 'rf_center_frequency',
                           unit       = 'GHz',
                           get_parser = float,
                           set_cmd    = ':sense:frequency:rf:center {} GHz',
                           get_cmd    = ':sense:frequency:rf:center?',
                           docstring  = 'The RF center frequency',
                           vals       = Numbers(9e-6, 3)
                           )

        self.add_parameter(name       = 'video_bandwidth',
                           unit       = 'MHz',
                           get_parser = float,
                           set_cmd    = ':sense:chpower:bandwidth:video {} MHz',
                           get_cmd    = ':sense:chpower:bandwidth:video?',
                           docstring  = 'The analyzer post-detection filter (VBW)'
                           )

        self.add_parameter(name       = 'resolution_bandwidth',
                           unit       = 'MHz',
                           get_parser = float,
                           set_cmd    = ':sense:chpower:bandwidth:resolution {} MHz',
                           get_cmd    = ':sense:chpower:bandwidth:resolution?',
                           docstring  = 'The resolution bandwidth'
                           )

        self.add_parameter(name       = 'power',
                           unit       = 'dBm',
                           get_parser = lambda val, output='power' : self.power_parser(val, output),
                           get_cmd    = ':initiate:chpower; :fetch:chpower?',
                           docstring  = 'Absolute power at the RF center frequency'
                           )

        self.add_parameter(name       = 'power_spectral_density',
                           unit       = 'dBm/Hz',
                           get_parser = lambda val, output='psd' : self.power_parser(val, output),
                           get_cmd    = ':initiate:chpower; :fetch:chpower?',
                           docstring  = 'Power Spectral Density at the RF center frequency'
                           )
        
        self.connect_message()



    def power_parser(self, val: str, output: str) -> float:
        """
        Parse the reply from a strin containing 'power, psd' to float depending
        of the output.

        Args:
            val (str): Reply of the power spectral analyzer.
            output (str): Desired output format.

        Returns:
            power or power spectral density (float):
                power in dBm.
                power spectral density in dBm/Hz.
        """
        
        power, psd = val.split(',')
        
        if output=='power':
            return float(power)
        elif output=='psd':
            return float(psd)
        else: 
            return 0.