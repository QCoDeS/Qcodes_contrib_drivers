# -*- coding: utf-8 -*-
"""
Created on Tuesday Jan 04, 2022

@author: Elyjah 

This is the qcodes driver for the SR_7270.

Driver notes:

All commands begin end with the echo \n\x00.
We chanage terminator to remove this. 
We redefine write_raw command to also read the echo to remove from buffer.
Now writing throws error that read doesn't find \n\x00 terminator.
This error is seemingly harmless and for now is ignored.

Get commands with . as in 'X.' are known as floating point in manual.

Never change noise mode as TC values will not be correct.
(If you want to change this then the driver will need to updated.)

Change Imode for measuring current instead of voltage.

Change Vmode for measuring A, -B or A - B voltages.

Reference frequency is set by INT, EXT_REAR or EXT_FRONT.
If in mode INT then oscillator frequency changes reference frequency.
Otherwise, reference frequency controlled by input.

    
"""

from qcodes import VisaInstrument, validators as vals
from qcodes.utils.delaykeyboardinterrupt import DelayedKeyboardInterrupt

class Signalrecovery7270(VisaInstrument):

    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, terminator='', device_clear = True, **kwargs)
        idn = self.IDN.get()
        self.model = idn['model']


        self.add_parameter(name='getX',
                        label='Lock-In X',
                        get_cmd='X.',
                        get_parser=float,
                        unit='V')

        self.add_parameter('getY',
                        label='Lock-In Y',
                        get_cmd='Y.',
                        get_parser=float,
                        unit='V')
        
        self.add_parameter('getXY',
                        label='Lock-In XY',
                        get_cmd=self._get_complex_voltage,
                        unit='V')
        
        self.add_parameter(name='getR',
                        label='Lock-In R',
                        get_cmd='MAG.',
                        get_parser=float,
                        unit='V')    
        
        self.add_parameter(name='getPhi',
                        label='Lock-In Phi',
                        get_cmd='PHA.',
                        get_parser=float,
                        unit='Degrees')  
          
        self.add_parameter(name='frequency',
                        label='Frequency',
                        unit='Hz',
                        get_cmd='FRQ.',
                        get_parser=float)
        
        self.add_parameter(name='osc_amplitude',
                        label='Osc_Amplitude',
                        unit='V',
                        set_cmd='OA. {}',
                        set_parser=float)

        self.add_parameter(name='osc_frequency',
                        label='Osc_Frequency',
                        unit='Hz',
                        set_cmd='OF. {}',
                        set_parser=float)

        self.add_parameter(name='reference',
                        label='Reference',
                        get_cmd='IE',
                        set_cmd='IE {}',
                        val_mapping = {'INT':       0,
                                        'EXT_rear':  1,
                                        'EXT_front': 2})
 
        self.add_parameter(name='noisemode',
                        label='Noisemode',
                        get_cmd='NOISEMODE',
                        set_cmd='NOISEMODE {}',
                        val_mapping = {'OFF':    0,
                                        'ON':  1},
                        docstring=('Should always leave off \n'
                                   'will change values of TC \n'
                                   'and low pass filter slope'))
        
        self.add_parameter(name='Imode',
                        label='Imode',
                        get_cmd='IMODE',
                        set_cmd='IMODE {}',
                        val_mapping = {'CURRENT_MODE_OFF': 0,
                                        'CURRENT_MODE_ON_HIGH_BW': 1,
                                        'CURRENT_MODE_ON_LOW_BW': 2},
                        docstring=('n Input mode'
                                    '0 Current mode off - voltage mode input enabled'
                                    '1 High bandwidth current mode enabled -'
                                    'connect signal to B (I) input connector'
                                    '2 Low noise current mode enabled -'
                                    'connect signal to B (I) input connector'
                                    'If n = 0 then the input configuration '
                                    'is determined by the VMODE command.'
                                    'If n > 0 then current mode '
                                    'is enabled irrespective of the VMODE setting.'))
                                    
        self.add_parameter(name='Vmode',
                        label='Vmode',
                        get_cmd='VMODE',
                        set_cmd='VMODE {}',
                        val_mapping = {'INPUTS_GNDED': 0,
                                        'A_INPUT_ONLY': 1,
                                        '-B_INPUT_ONLY': 2,
                                        'A_B_DIFFERENTIAL': 3},
                        docstring=('Note that the IMODE command takes precedence over the VMODE command.'))
 
        self.add_parameter(name='sensitivity',
                        label='Sensitivity',
                        unit='V',
                        get_cmd='SEN',
                        set_cmd='SEN {}',
                        val_mapping={   2e-9: 1,
                                        5e-9: 2,
                                        10e-9: 3,
                                        20e-9: 4,
                                        50e-9: 5,
                                        100e-9: 6,
                                        200e-9: 7,
                                        500e-9: 8,
                                        1e-6: 9,
                                        2e-6: 10,
                                        5e-6: 11,
                                        10e-6: 12,
                                        20e-6: 13,
                                        50e-6: 14,
                                        100e-6: 15,
                                        200e-6: 16,
                                        500e-6: 17,
                                        1e-3: 18,
                                        2e-3: 19,
                                        5e-3: 20,
                                        10e-3: 21,
                                        20e-3: 22,
                                        50e-3: 23, 
                                        100e-3: 24, 
                                        200e-3: 25, 
                                        500e-3: 26,                                                                                                                                                                                                                                               
                                        1: 27})  
              
        self.add_parameter(name='timeconstant',
                        label='Timeconstant',
                        unit='s',
                        get_cmd='TC',
                        set_cmd='TC {}',
                        val_mapping={   10e-6: 0,
                                        20e-6: 1,
                                        50e-6: 2,
                                        100e-6: 3,
                                        200e-6: 4,
                                        500e-6: 5,
                                        1e-3: 6,
                                        2e-3: 7,
                                        5e-3: 8,
                                        10e-3: 9,
                                        20e-3: 10,
                                        50e-3: 11,
                                        100e-3: 12,
                                        200e-3: 13,
                                        500e-3: 14,
                                        1: 15,
                                        2: 16,
                                        5: 17,
                                        10: 18,
                                        20: 19,
                                        50: 20,
                                        100: 21,
                                        200: 22,
                                        500: 23, 
                                        1e+3: 24, 
                                        2e+3: 25, 
                                        5e+3: 26,                                         
                                        10e+3: 27,                                         
                                        20e+3: 28,                                         
                                        50e+3: 29,                                                                                                                                                                                                         
                                        100e+3: 30})
        
    def write_raw(self, cmd:str) -> None:
        with DelayedKeyboardInterrupt():
            status = self.ask_raw(cmd)
        
    def ask_raw(self, cmd:str) -> str:
        """Reimplementaion of ask function to handle specific communication with lockin.

        Args:
            cmd (str): Command to be sent (asked) to lockin.

        Raises:
            Runtimeerror: [description]

        Returns:
            str: Return string from lockin with terminator character stripped of.
        """
        with DelayedKeyboardInterrupt():
            response = self.visa_handle.query(cmd)
            if response.endswith('\x00'):
                resp = response[:-1]
                if resp.endswith('\n'):
                    return resp[:-1]
                else:
                    return resp
            else:
                print('we are not happy about the terminator character')
                raise Runtimeerror(response)
        
    def _get_complex_voltage(self) -> complex:
            XY = self.ask_raw('XY.')
            x = float(XY.split(',',1)[0])
            y = float(XY.split(',',1)[1])
            return x + 1.0j*y
