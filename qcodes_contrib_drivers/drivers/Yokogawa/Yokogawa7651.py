from qcodes import VisaInstrument
from typing import Dict, Optional
import re

class Yokogawa7651(VisaInstrument):
    """
    QCoDeS driver for Yokogawa 7651 current source.
    """
    def __init__(self, name: str, address: str, **kwargs):
        """
        Args:
            name: Name to use internally in QCoDeS
            address: VISA ressource address
        """
        super().__init__(name, address, **kwargs)

        self.add_parameter(name='output',
                           set_cmd='O{}E',
                           get_cmd=self._get_status,
                           val_mapping={'on': 1,
                                        'off': 0})
        
        self.add_parameter(name='mode',
                           set_cmd='F{}E',
                           get_cmd=self._get_mode,
                           val_mapping={'C.V.': 1,
                                        'C.C.': 5})

        self.add_parameter(name='range',
                           set_cmd=self._set_range,
                           get_cmd=self._get_range)

        self.add_parameter(name='value',
                           set_cmd=self._set_value,
                           get_cmd=self._get_value)

    def _set_range(self, range: str):
        """Function to set range based on output mode.

        Parameters
        ----------
        range : str
            Desired output range
        """
        allowed_range = {'C.V.': {'10mV': 'R2',
                                  '100mV': 'R3',
                                  '1V': 'R4',
                                  '10V': 'R5',
                                  '30V': 'R6'},
                         'C.C.': {'1mA': 'R4',
                                  '10mA': 'R5',
                                  '100mA': 'R6'}}

        try:
            range_str = allowed_range[self.mode()][range]
        except:
            raise ValueError('Specified range is not supported or in wrong unit.')

        self.write(range_str+'E')

    def _get_range(self):
        """Function to get range based on return value of "OS" command.
        """
        range = {'F1': {'R2': '10mV',
                        'R3': '100mV',
                        'R4': '1V',
                        'R5': '10V',
                        'R6': '30V'},
                 'F5': {'R4': '1mA',
                        'R5': '10mA',
                        'R6': '100mA'}}
        response = self._setting_output()['line1']

        return range[response[0]][response[1]]

    def _set_value(self, value: float):
        """Function to set output value.

        Parameters
        ----------
        value : float
            Desired output value, in the unit of mV (or mA)
        """
        value_str = f'{abs(value)/1000:.10f}'

        if value < 0:
            polarity_str = '-'
        else:
            polarity_str = '+'

        self.write('S'+polarity_str+value_str+'E')

    def _get_value(self):
        """Function to get output value based on return value of "OD" command.
        """
        response = self._data_output()

        return 1000*float(response[3])*10**(float(response[4]))

    def _get_mode(self):
        """Function to get mode based on return value of "OD" command.
        """
        response = self._data_output()

        if response[2] == 'V':
            return 1
        else:
            return 5

    def _get_status(self):
        """Function to get output status based on return value of "OC" command.
        """
        code = self._status_output()

        return int((bin(code)[2:].zfill(8))[3])

    def _status_output(self):
        """Inquire "OC"
        """
        string = self.ask_raw("OC")

        pattern = "STS1=(\d*)"
        matched = re.match(pattern, string).groups()

        return int(matched[0])

    def _data_output(self):
        """Inquire "OD"
        """
        string = self.ask_raw("OD")

        pattern = "(\w)(\w\w)(\w)([\+\-\d\.]*)E([\+\-]\d*)"
        matched = re.match(pattern, string)

        return matched.groups()

    def _setting_output(self):
        """Inquire "OS"
        """
        self.visa_handle.write("OS", termination="\r\n")
        line0 = self.visa_handle.read()
        line1 = self.visa_handle.read()
        line2 = self.visa_handle.read()
        line3 = self.visa_handle.read()
        line4 = self.visa_handle.read()

        response_dict = {}

        pattern0 = "([A-Z]*)([\d]*)([A-Z]*)([\d\.]*)"
        response_dict["line0"] = re.match(pattern0, line0).groups()

        pattern1 = "(\w\w)(\w\w)\w([\+\-\d\.]*)E([\+\-\d]*)"
        response_dict["line1"] = re.match(pattern1, line1).groups()

        return response_dict

    def get_idn(self):
        model = self._setting_output()["line0"][1]
        firmware = self._setting_output()["line0"][3]

        IDN: Dict[str, Optional[str]] = {
            'vendor': 'Yokogawa', 'model': model,
            'serial': None, 'firmware': firmware}
        return IDN
