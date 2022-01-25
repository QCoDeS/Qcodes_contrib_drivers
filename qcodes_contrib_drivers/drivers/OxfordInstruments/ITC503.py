# This Python file uses the following encoding: utf-8

"""
Created by Paritosh Karnatak <paritosh.karnatak@unibas.ch>, Feb 2019
Updated by Elyjah <elyjah.kiyooka@cea.fr>, Jan 2022

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

        # Add parameters
        self.add_parameter('temp_1',
                        get_cmd='R1',
                        label='Temperature of sensor 1',
                        get_parser=float,
                        unit='K',
                        vals = vals.Numbers(),
                        docstring="Reads the temperature of the 1st sensor "
                            "only gettable.")

        self.add_parameter('temp_2',
                        get_cmd='R2',
                        label='Temperature of sensor 2',
                        get_parser=float,
                        unit='K',
                        vals = vals.Numbers(),
                        docstring="Reads the temperature of the 2nd sensor "
                            "only gettable.")

        self.add_parameter('temp_3',
                        get_cmd='R3',
                        label='Temperature of sensor 3',
                        get_parser=float,
                        unit='K',
                        vals = vals.Numbers(),
                        docstring="Reads the temperature of the 3rd sensor "
                            "only gettable.")

        self.add_parameter('temp_set_point',
                        get_cmd='R0',
                        label='Set point temperature',
                        get_parser=float,
                        set_cmd='T0000{}',
                        set_parser=float,
                        vals=vals.Numbers(min_value=.3, max_value=40),
                        unit='K',
                        docstring="Gets and sets the temperature set point "
                            "Set point depends on which heater is selected "
                            "Must be in remote mode to set")

        self.add_parameter('heater_power',
                        get_cmd='R5',
                        label='Reads heating power',
                        get_parser=float,
                        set_cmd='O00{}',
                        set_parser=float,
                        vals=vals.Numbers(min_value=0, max_value=99.9),
                        unit='%',
                        docstring="Gets and sets the heating power "
                            "Set point depends on which heater is selected "
                            "Must be in remote mode to set")

        self.add_parameter(name='remote_mode',
                        label='Remote mode',
                        get_cmd=self._get_status_remote,
                        get_parser=str,
                        set_cmd='C{}',
                        val_mapping = {'local_locked': 0,
                                        'remote_locked': 1,
                                        'local_unlocked': 2,
                                        'remote_unlocked': 3},
                        docstring="Get and set the desired remote mode "
                                "Remote locked means front panel can't be used")

        self.add_parameter(name='heater_mode',
                        label='Heater mode',
                        get_cmd=self._get_status_auto,
                        get_parser=str,
                        set_cmd='A{}',
                        val_mapping = {'manual': 0,
                                        'auto': 1,},
                        docstring="Get and set the mode the heater is in; "
                            "Warning will immediately change heater power to go to temp "
                            "Must be in remote mode to set")

        self.add_parameter(name='select_heater',
                        label='Choose desired heater',
                        get_cmd=self._get_status_heater,
                        get_parser=str,
                        set_cmd='H{}',
                        val_mapping = {'heater_1': 1,
                                        'heater_2': 2,
                                        'heater_3': 3,},
                        docstring="Read and set the heater/sensor you use; "
                            "Will change the value of the temp set point to the current temp everytime to change "
                            "Must be in remote mode to set")

    def ask_raw(self, cmd:str) -> str:
        """Reimplementaion of ask function to handle R in response.
        Args:
            cmd: Command to be sent (asked) to lockin.
        Returns:
            str: Return string from lockin with R character stripped of.
        """
        with DelayedKeyboardInterrupt():
            response = self.visa_handle.query(cmd)
            if response.startswith('R'):
                resp = response[1:]
                return resp
            else:
                print(response)

    def write_raw(self, cmd:str) -> None:
        """Reimplementation of write function to write and read lockin echo.
        Args:
            cmd: Command to be sent (asked) to lockin.
        """
        self.visa_handle.write(cmd)
        result = self.visa_handle.read()
        if result.find('?') >= 0:
            print("Error: Command %s not recognized" % cmd)
        else:
            return result

    def _get_status_remote(self) -> str:
        """Gets status of remote mode by parcing the examine 'X' command \n
        for 'C' the variable concerning the remote mode
        """
        self.visa_handle.write('X')
        result = self.visa_handle.read()
        if result.find('?') >= 0:
            print("Error: Command %s not recognized" % 'C')
        else:
            return int(result.split('C')[1][0])

    def _get_status_auto(self) -> str:
        """Gets status of remote mode by parcing the examine 'X' command \n
        for 'A' the variable concerning the auto mode
        """
        self.visa_handle.write('X')
        result = self.visa_handle.read()
        if result.find('?') >= 0:
            print("Error: Command %s not recognized" % 'A')
        else:
            return int(result.split('A')[1][0])

    def _get_status_heater(self) -> str:
        """Gets status of remote mode by parcing the examine 'X' command \n
        for 'H' the variable concerning the heater mode
        """
        self.visa_handle.write('X')
        result = self.visa_handle.read()
        if result.find('?') >= 0:
            print("Error: Command %s not recognized" % 'H')
        else:
            return int(result.split('H')[1][0])