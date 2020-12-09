# -*- coding: utf-8 -*-
"""Simulation for the QCoDeS-Driver SMW200A.

This simulation is used to generate meanfull answers
to the comunication from the driver if the hardware
is not available.

Authors:
    Michael Wagener, ZEA-2, m.wagener@fz-juelich.de
"""
import pyvisa
from qcodes.instrument.visa import VisaInstrument
from qcodes.utils.validators import Numbers


class MockVisa(VisaInstrument):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_parameter('state',
                           get_cmd='STAT?', get_parser=float,
                           set_cmd='STAT:{:.3f}',
                           vals=Numbers(-20, 20))

    def set_address(self, address):
        self.visa_handle = MockVisaHandle()


class MockVisaHandle:
    '''
    Simulate the API needed for a visa handle.
    '''
    
    # List of possible commands asked the instrument to give a realistic answer.
    cmddef = {'*IDN?': 'Rohde&Schwarz,SMW200A,1412.0000K02/105578,04.30.005.29 SP2',
              '*OPT?': 'SMW-B13T,SMW-B22,SMW-B120,SMW-K22,SMW-K23',
              
              'STAT?': '0',
              
              'SOUR1:FREQ?': '20000000000.0',
              'SOUR1:POW:POW?': '-145.0',
              'OUTP1:STAT?': '0',
              'SOUR1:FREQ:MODE?': 'CW',
              'SOUR1:FREQ:CENT?': '300000000.0',
              'SOUR1:FREQ:SPAN?': '400000000.0',
              'SOUR1:FREQ:STAR?': '100000000.0',
              'SOUR1:FREQ:STOP?': '500000000.0',
              'SOUR1:FREQ:LOSC:INP:FREQ?': '0',
              'SOUR1:FREQ:LOSC:MODE?': 'INT',
              'SOUR1:FREQ:LOSC:OUTP:FREQ?': '0',
              'SOUR1:FREQ:LOSC:OUTP:STAT?': '0',
              
              'SOUR1:SWE:POW:AMOD?': 'AUTO',
              'SOUR1:SWE:POW:DWEL?': '0.01',
              'SOUR1:SWE:POW:MODE?': 'AUTO',
              'SOUR1:SWE:POW:POIN?': '21',
              'SOUR1:SWE:POW:STEP?': '1.0',
              'SOUR1:SWE:POW:SHAP?': 'SAWT',
              'SOUR1:SWE:POW:RETR?': '0',
              'SOUR1:SWE:POW:RUNN?': '0',
              'SOUR1:SWE:DWEL?': '0.01',
              'SOUR1:SWE:MODE?': 'AUTO',
              'SOUR1:SWE:POIN?': '401',
              'SOUR1:SWE:SPAC?': 'LIN',
              'SOUR1:SWE:SHAP?': 'SAWT',
              'SOUR1:SWE:RETR?': '0',
              'SOUR1:SWE:RUNN?': '0',
              'SOUR1:SWE:STEP:LOG?': '1.0',
              'SOUR1:SWE:STEP?': '1000000.0',
              
              'SOUR:LFO1:BAND?': 'BW10',
              'SOUR:LFO1:STAT?': '0',
              'SOUR:LFO1:OFFS?': '0',
              'SOUR:LFO1:SOUR?': 'LF1',
              'SOUR:LFO1:VOLT?': '1.0',
              'SOUR:LFO1:PER?': '0.001',
              
              'SOUR1:LFO1:FREQ?': '1000.0',
              'SOUR1:LFO:FREQ:MAN?': '1000.0',
              'SOUR1:LFO:FREQ:STAR?': '1000.0',
              'SOUR1:LFO:FREQ:STOP?': '50000.0',
              'SOUR1:LFO:FREQ:MODE?': 'CW',
              
              'SOUR:LFO2:BAND?': 'BW10',
              'SOUR:LFO2:STAT?': '0',
              'SOUR:LFO2:OFFS?': '0',
              'SOUR:LFO2:SOUR?': 'EXT1',
              'SOUR:LFO2:VOLT?': '1.0',
              
              'SOUR1:LFO:SWE:DWEL?': '0.01',
              'SOUR1:LFO:SWE:MODE?': 'AUTO',
              'SOUR1:LFO:SWE:POIN?': '50',
              'SOUR1:LFO:SWE:SHAP?': 'SAWT',
              'SOUR1:LFO:SWE:RETR?': '0',
              'SOUR1:LFO:SWE:RUNN?': '0',
              'SOUR1:LFO:SWE:SPAC?': 'LIN',
              'SOUR1:LFO:SWE:STEP:LOG?': '1.0',
              'SOUR1:LFO:SWE:STEP?': '1000.0',
              
              'SOUR1:AM1:STAT?': '0',
              'SOUR1:AM1:SOUR?': 'LF1',
              'SOUR1:AM1:DEPT?': '50.0',
              'SOUR1:AM:RAT?': '50.0', # Ratio Path2 to Path1
              'SOUR1:AM:SENS?': '50.0', # Sensitivity for EXT
              
              'SOUR1:AM2:STAT?': '0',
              'SOUR1:AM2:SOUR?': 'LF1',
              'SOUR1:AM2:DEPT?': '50.0',        
              
              'SOUR1:FM1:STAT?': '0',
              'SOUR1:FM1:DEV?': '1000.0',
              'SOUR1:FM1:SOUR?': 'LF1',
              'SOUR1:FM:RAT?': '100.0',
              'SOUR1:FM:MODE?': 'NORM',
              'SOUR1:FM:SENS?': '1000.0',
              
              'SOUR1:FM2:STAT?': '0',
              'SOUR1:FM2:DEV?': '1000.0',
              'SOUR1:FM2:SOUR?': 'EXT1',
              
              'SOUR1:PM1:STAT?': '0',
              'SOUR:PM1:DEV?': '1',
              'SOUR1:PM1:SOUR?': 'LF1',
              'SOUR1:PM:MODE?': 'HBAN',
              'SOUR1:PM:RAT?': '100',
              'SOUR1:PM:SENS?': '1',
              
              'SOUR1:PM2:STAT?': '0',
              'SOUR:PM2:DEV?': '1',
              'SOUR1:PM2:SOUR?': 'EXT1',
              'SOUR1:PM:MODE?': 'HBAN',
              
              'SOUR1:PULM:MODE?': '0',
              'SOUR1:PULM:DOUB:DEL?': '0',
              'SOUR1:PULM:DOUB:WID?': '0',
              'SOUR1:PULM:TRIG:MODE?': '0',
              'SOUR1:PULM:PER?': '2.0',
              'SOUR1:PULM:WIDT?': '0',
              'SOUR1:PULM:DEL?': '0',
              'SOUR1:PULM:STAT?': '0',
              'SOUR1:PULM:SOUR?': 'EXT',
              'SOUR1:PULM:TTYP?': 'FAST',
              'SOUR1:PULM:OUTP:VID:POL?': 'NORM',
              'SOUR1:PULM:POL?': 'NORM',
              'SOUR1:PULM:IMP?': 'G1K',
              'SOUR1:PULM:TRIG:EXT:IMP?': 'G50',
              
              'SOUR1:PGEN:OUTP:POL?': 'NORM',
              'SOUR1:PGEN:OUTP:STAT': 'OFF',
              'SOUR1:PGEN:STAT': 'OFF',
              
              'SOUR1:IQ:SOUR?': 'BAS',
              'SOUR1:IQ:STAT?': '0',
              'SOUR1:IQ:GAIN?': 'DB4',
              'SOUR1:IQ:CRES?': '0.0',
              'SOUR1:IQ:SWAP:STAT?': '0',
              'SOUR1:IQ:WBST?': '0',
              
              'SOUR1:IQ:OUTP:ANAL:STAT?': '0',
              'SOUR1:IQ:OUTP:ANAL:TYPE?': 'SING',
              'SOUR1:IQ:OUTP:ANAL:MODE?': 'FIX',
              'SOUR1:IQ:OUTP:LEV?': '1.0',
              'SOUR1:IQ:OUTP:ANAL:BIAS:COUP:STAT?': '0',
              'SOUR1:IQ:OUTP:ANAL:BIAS:I?': '0',
              'SOUR1:IQ:OUTP:ANAL:BIAS:Q?': '0',
              'SOUR1:IQ:OUTP:ANAL:OFFS:I?': '0',
              'SOUR1:IQ:OUTP:ANAL:OFFS:Q?': '0',

              'SOUR2:IQ:OUTP:ANAL:STAT?': '0',
              'SOUR2:IQ:OUTP:ANAL:TYPE?': 'SING',
              'SOUR2:IQ:OUTP:ANAL:MODE?': 'FIX',
              'SOUR2:IQ:OUTP:LEV?': '1.0',
              'SOUR2:IQ:OUTP:ANAL:BIAS:COUP:STAT?': '0',
              'SOUR2:IQ:OUTP:ANAL:BIAS:I?': '0',
              'SOUR2:IQ:OUTP:ANAL:BIAS:Q?': '0',
              'SOUR2:IQ:OUTP:ANAL:OFFS:I?': '0',
              'SOUR2:IQ:OUTP:ANAL:OFFS:Q?': '0'
              }
    
    def __init__(self):
        self.state = 0
        self.closed = False

    def clear(self):
        self.state = 0

    def close(self):
        # make it an error to ask or write after close
        self.closed = True

    def write(self, cmd):
        if self.closed:
            raise RuntimeError("Trying to write to a closed instrument")
        try:
            num = float(cmd.split(':')[-1])
        except:
            num = 1
        self.state = num

        if num < 0:
            raise ValueError('be more positive!')

        if num == 0:
            ret_code = pyvisa.constants.VI_ERROR_TMO
        else:
            ret_code = 0

        return len(cmd), ret_code

    def ask(self, cmd):
        if self.closed:
            raise RuntimeError("Trying to ask a closed instrument")
        if self.state > 10:
            raise ValueError("I'm out of fingers")
        return self.state

    def query(self, cmd):
        if cmd in self.cmddef:
            return self.cmddef[cmd]
        if self.state > 10:
            raise ValueError("I'm out of fingers")
        return self.state
