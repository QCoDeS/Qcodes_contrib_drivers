# This Python file uses the following encoding: utf-8

"""
Created by Paritosh Karnatak <paritosh.karnatak@unibas.ch>, Feb 2019
Updated by Elyjah <elyjah.kiyooka@cea.fr>, June 2022

"""

import logging
from qcodes import VisaInstrument, validators as vals
from qcodes.utils.delaykeyboardinterrupt import DelayedKeyboardInterrupt

log = logging.getLogger(__name__)

class ITC503(VisaInstrument):
    """
    The qcodes driver for communication with
    ITC503, "Oxford Instruments Intelligent Temperature Controller"
    """

    def __init__(self, name: str, address: str, **kwargs):

        log.debug('Initializing instrument')
        super().__init__(name, address, terminator='\r', **kwargs)

        self._address = address
        self._values = {}

        self.add_parameter(name='temp_1',
                            label='Temperature of sensor 1',
                            get_cmd=lambda: self.get_temp('R1'),
                            get_parser=float,
                            unit='K',
                            vals = vals.Numbers(),
                            docstring="Reads the temperature of the 1st sensor.")

        self.add_parameter(name='temp_2',
                            label='Temperature of sensor 2',
                            get_cmd=lambda: self.get_temp('R2'),
                            get_parser=float,
                            unit='K',
                            vals = vals.Numbers(),
                            docstring="Reads the temperature of the 2nd sensor.")

        self.add_parameter(name='temp_3',
                            label='Temperature of sensor 3',
                            get_cmd=lambda: self.get_temp('R3'),
                            get_parser=float,
                            unit='K',
                            vals = vals.Numbers(),
                            docstring="Reads the temperature of the 3rd sensor.")

        self.add_parameter(name='temp_set_point',
                            label='Set point temperature',
                            get_cmd=lambda: self.get_temp('R0'),
                            get_parser=float,
                            set_cmd='T0000{}',
                            set_parser=float,
                            vals=vals.Numbers(min_value=.3, max_value=40),
                            unit='K',
                            docstring="Gets and sets the temperature set point. "
                                "Set point depends on which heater is selected. "
                                "Must be in remote mode to set.")

        self.add_parameter(name='heater_power',
                            label='Reads heating power',
                            get_cmd=lambda: self.get_temp('R5'),
                            get_parser=float,
                            set_cmd='O00{}',
                            set_parser=float,
                            vals=vals.Numbers(min_value=0, max_value=99.9),
                            unit='%',
                            docstring="Gets and sets the heating power. "
                                "Set point depends on which heater is selected. "
                                "Must be in remote mode to set.")

        self.add_parameter(name='remote_mode',
                            label='Remote mode',
                            get_cmd=self._get_status_remote,
                            get_parser=int,
                            set_cmd='C{}',
                            set_parser=str,
                            val_mapping = {'local_locked': 0,
                                            'remote_locked': 1,
                                            'local_unlocked': 2,
                                            'remote_unlocked': 3},
                            docstring="Get and set the desired remote mode. "
                                    "Remote/local is the type of control. "
                                    "Locked/unlocked is whether or not it can be changed.")

        self.add_parameter(name='heater_mode',
                            label='Heater mode',
                            get_cmd=self._get_status_auto,
                            get_parser=int,
                            set_cmd='A{}',
                            set_parser=str,
                            val_mapping = {'manual': 0,
                                            'auto': 1,},
                            docstring="Get and set the mode the heater is in. "
                                "Warning going to 'auto' will immediately change heater power to go to temp_set_point. "
                                "Must be in remote mode to set.")

        self.add_parameter(name='select_heater',
                            label='Choose desired heater',
                            get_cmd=self._get_status_heater,
                            get_parser=int,
                            set_cmd='H{}',
                            set_parser=str,
                            val_mapping = {'heater_1': 1,
                                            'heater_2': 2,
                                            'heater_3': 3,},
                            docstring="Get and set the heater/sensor you use. "
                                "Will change the value of the temp set point to the current temp everytime to change. "
                                "Appears the heater connections are hard-wired, so (until changed) it always heats #1 the Sorb.  "
                                "Must be in remote mode to set.")

    def get_temp(self, cmd:str) -> float:
        """Reimplementaion of ask function to strip response of a prefix 'R' .
        Args:
            cmd: Command to be sent (asked) to the ITC.
        Returns:
            str: Return string from ITC with 'R' character removed.
        """
        with DelayedKeyboardInterrupt():
            try:
                response = self.visa_handle.query(cmd)
                if response.find('R') >= 0:
                    return float(response.split('R')[-1])
                else:
                    print("Error: Command %s not recognized" % cmd)
                    return float('NAN')
            except ValueError:
                print('Not good response')
                return float('NAN')

    def write_raw(self, cmd:str) -> None:
        """Reimplementation of write function. Prints warning if command not recognized.
        Args:
            cmd: Command to be sent (asked) to ITC.
        """
        self.visa_handle.write(cmd)
        result = self.visa_handle.read()
        if result.find('R') >= 0:
            print("Error: Command %s not recognized" % cmd)

    def _get_status_remote(self) -> int:
        """Gets status of remote mode by parcing the examine 'X' command \n
        for the letter 'C' (the variable concerning the remote mode), and using the following value
        to determine its status. Prints error if 'C' not found.
        """
        self.visa_handle.write('X')
        result = self.visa_handle.read()
        if result.find('?') >= 0:
            print("Error: Command %s not recognized" % 'C')
        else:
            return int(result.split('C')[1][0])

    def _get_status_auto(self) -> int:
        """Gets status of auto mode by parcing the examine 'X' command \n
        for the letter 'A' (the variable concerning the auto mode), and using the following value
        to determine its status. Prints error if 'A' not found.
        """
        self.visa_handle.write('X')
        result = self.visa_handle.read()
        if result.find('?') >= 0:
            print("Error: Command %s not recognized" % 'A')
        else:
            return int(result.split('A')[1][0])

    def _get_status_heater(self) -> int:
        """Gets status of heater by parcing the examine 'X' command \n
        for the letter 'H' (the variable concerning the heater mode), and using the following value
        to determine its status. Prints error if 'H' not found.
        """
        self.visa_handle.write('X')
        result = self.visa_handle.read()
        if result.find('?') >= 0:
            print("Error: Command %s not recognized" % 'H')
        else:
            return int(result.split('H')[1][0])