# -*- coding: utf-8 -*-
"""
File:    ANC300sim.py
Date:    Jan 2020
Author:  Michael Wagener, FZJ / ZEA-2, m.wagener@fz-juelich.de
Purpose: Simulation for the Attocube ANC300 driver in the same way as
         it is used in our lab.
"""

#from unittest import TestCase
#from unittest.mock import patch
import pyvisa
from qcodes.instrument.visa import VisaInstrument
from qcodes.utils.validators import Numbers
#import warnings

# if set to True, every communication line is printed
_USE_DEBUG = True

# The ANC300 script implies an echo from the device
# The AttocubeController script implies no echo!!!!
_USE_ECHO = True



class MockVisa(VisaInstrument):
    def __init__(self, *args, **kwargs):
        #print("DBG-Mock:", args, kwargs)
        super().__init__(*args, **kwargs)
        ##self.add_parameter('state',
        ##                   get_cmd='STAT?', get_parser=float,
        ##                   set_cmd='STAT:{:.3f}',
        ##                   vals=Numbers(-20, 20))

    def set_address(self, address):
        self.visa_handle = MockVisaHandle()


class MockVisaHandle:
    '''
    Simulate the API needed for the communication.
    '''
    
    # List of possible commands asked the instrument to give a realistic answer.
    cmddef = {'ver': ['attocube ANC300 controller version 1.1.0-1304 2013-10-17 08:16',
                      'ANC150 compatibillity console'],
              'getcser' : ['ANC300B-C-1514-3006076'],
              'getser 1': ['ANM150A-M-1545-3010045'],
              'getser 2': ['ANM150A-M-1545-3010041'],
              'getser 3': ['Wrong axis type','ERROR'],
              'getser 4': ['Wrong axis type','ERROR'],
              'getser 5': ['Wrong axis type','ERROR'],
              'getser 6': ['Wrong axis type','ERROR'],
              'getser 7': ['Wrong axis type','ERROR'],

              'getf 1': ['frequency = 210 Hz'],
              'getf 2': ['frequency = 210 Hz'],
              'getf 3': ['Wrong axis type','ERROR'],
              'getf 4': ['Wrong axis type','ERROR'],
              'getf 5': ['Wrong axis type','ERROR'],
              'getf 6': ['Wrong axis type','ERROR'],
              'getf 7': ['Wrong axis type','ERROR'],

              'getv 1': ['voltage = 20.000000 V'],
              'getv 2': ['voltage = 20.000000 V'],
              'getv 3': ['Wrong axis type','ERROR'],
              'getv 4': ['Wrong axis type','ERROR'],
              'getv 5': ['Wrong axis type','ERROR'],
              'getv 6': ['Wrong axis type','ERROR'],
              'getv 7': ['Wrong axis type','ERROR'],

              'geta 1': ['voltage = 0.000000 V'],
              'geta 2': ['voltage = 0.000000 V'],
              'geta 3': ['Wrong axis type','ERROR'],
              'geta 4': ['Wrong axis type','ERROR'],
              'geta 5': ['Wrong axis type','ERROR'],
              'geta 6': ['Wrong axis type','ERROR'],
              'geta 7': ['Wrong axis type','ERROR'],

              'getm 1': ['mode = gnd'],
              'getm 2': ['mode = gnd'],
              'getm 3': ['Wrong axis type','ERROR'],
              'getm 4': ['Wrong axis type','ERROR'],
              'getm 5': ['Wrong axis type','ERROR'],
              'getm 6': ['Wrong axis type','ERROR'],
              'getm 7': ['Wrong axis type','ERROR'],

              'getaci 1': ['acin = off'],
              'getaci 2': ['acin = off'],
              'getaci 3': ['Wrong axis type','ERROR'],
              'getaci 4': ['Wrong axis type','ERROR'],
              'getaci 5': ['Wrong axis type','ERROR'],
              'getaci 6': ['Wrong axis type','ERROR'],
              'getaci 7': ['Wrong axis type','ERROR'],

              'getdci 1': ['dcin = off'],
              'getdci 2': ['dcin = off'],
              'getdci 3': ['Wrong axis type','ERROR'],
              'getdci 4': ['Wrong axis type','ERROR'],
              'getdci 5': ['Wrong axis type','ERROR'],
              'getdci 6': ['Wrong axis type','ERROR'],
              'getdci 7': ['Wrong axis type','ERROR'],

              'gettu 1': ['trigger = off'],
              'gettu 2': ['trigger = 2'],
              'gettu 3': ['Wrong axis type','ERROR'],
              'gettu 4': ['Wrong axis type','ERROR'],
              'gettu 5': ['Wrong axis type','ERROR'],
              'gettu 6': ['Wrong axis type','ERROR'],
              'gettu 7': ['Wrong axis type','ERROR'],

              'gettd 1': ['trigger = 1'],
              'gettd 2': ['trigger = 3'],
              'gettd 3': ['Wrong axis type','ERROR'],
              'gettd 4': ['Wrong axis type','ERROR'],
              'gettd 5': ['Wrong axis type','ERROR'],
              'gettd 6': ['Wrong axis type','ERROR'],
              'gettd 7': ['Wrong axis type','ERROR'],
              
              'getc 1':  ['cap = 5 nF'], # TODO
              'getc 2':  ['cap = 5 nF'], # TODO
              'getc 3':  ['Wrong axis type','ERROR'],
              'getc 4':  ['Wrong axis type','ERROR'],
              'getc 5':  ['Wrong axis type','ERROR'],
              'getc 6':  ['Wrong axis type','ERROR'],
              'getc 7':  ['Wrong axis type','ERROR'],

              'stepu 1': ['0'],
              'stepu 2': ['0'],
              'stepd 1': ['0'],
              'stepd 2': ['0'],
              # There is no simulation for the correct movement

              }
    
    def __init__(self):
        if _USE_DEBUG:
            print("DBG-Mock: init")
        self.closed = False
        self.answer = []

    def clear(self):
        if _USE_DEBUG:
            print("DBG-Mock: clear")
        self.answer = []

    def close(self):
        # make it an error to ask or write after close
        if _USE_DEBUG:
            print("DBG-Mock: close")
        self.closed = True

##    @property
##    def session(self):
##        """Resource Manager session handle.
##
##        :raises: :class:`pyvisa.errors.InvalidSession` if session is closed.
##        """
##        return None # not used here

##    def write(self, session, data):
    def write(self, data):
        """Writes data to device or interface synchronously.

        Corresponds to viWrite function of the VISA library.

        :param session: Unique logical identifier to a session.
        :param data: data to be written.
        :type data: str
        :return: Number of bytes actually transferred, return value of the library call.
        :rtype: int, :class:`pyvisa.constants.StatusCode`
        """
        if self.closed:
            raise RuntimeError("Trying to write to a closed instrument")
        ##cmd = data.decode('ascii').rstrip()
        cmd = data.rstrip()
        if _USE_DEBUG:
            print("DBG-Mock: write", cmd)
        # setxx <axis> <val> --> <kenn> = <val> <unit>
        # getxx <axis> <val> --> <kenn> = <val> <unit>
        if cmd.startswith('set'):
            if _USE_ECHO:
                self.answer = [ cmd, 'OK' ]
            else:
                self.answer = [ 'OK' ]
            tmp = cmd.split()
            cmd = tmp[0].replace('set','get') + ' ' + tmp[1]
            if cmd in self.cmddef:
                val = self.cmddef[cmd]
                if isinstance( val, (list, tuple) ):
                    val = val[0]
            else:
                val = ""
            val = val.split(' = ')
            if len(val) == 2:
                unit = val[1].split()
                if len(unit) > 1:
                    unit = unit[1]
                else:
                    unit = "" # unit[0]
                setval = [ val[0]+' = '+tmp[2]+' '+unit ]
                self.cmddef.update( {cmd: setval} )
            else:
                self.cmddef.update( {cmd: tmp[2]} )
        elif cmd in self.cmddef:
            if _USE_ECHO:
                self.answer.append(cmd)
            for c in self.cmddef[cmd]:
                self.answer.append(c)
            if self.answer[-1] != 'ERROR':
                self.answer.append( 'OK' )
        else:
            if _USE_ECHO:
                self.answer.append(cmd)
            self.answer.append('OK')
        return len(cmd), pyvisa.constants.StatusCode.success

##    def read(self, session, count):
    def read(self):
        """Reads data from device or interface synchronously.

        Corresponds to viRead function of the VISA library.

        :param session: Unique logical identifier to a session.
        :param count: Number of bytes to be read.
        :return: data read, return value of the library call.
        :rtype: bytes, :class:`pyvisa.constants.StatusCode`
        """
        if self.closed:
            raise RuntimeError("Trying to read from a closed instrument")
        if _USE_DEBUG:
            print("DBG-Mock: read", self.answer)
        if len(self.answer) > 0:
            ##return self.answer.pop(0).encode('ascii'), pyvisa.constants.StatusCode.success
            return self.answer.pop(0)
        ##return 'ERROR'.encode('ascii'), pyvisa.constants.StatusCode.error_io
        return 'ERROR'

    def ask(self, cmd):
        print("DBG-Mock: MockVisaHandle ask", cmd)
        if self.closed:
            raise RuntimeError("Trying to ask a closed instrument")
        ##self.write(None, cmd)
        ##return self.read(None, 100)
        self.write(cmd)
        return self.read()

    def query(self, cmd):
        #print("DBG-Mock: MockVisaHandle query", cmd)
        ##self.write(None, cmd)
        ##return self.read(None, 100)
        self.write(cmd)
        return self.read()



    # Damit AttocubeController.py auch funktioniert....

    def _write(self, cmd: str):
        """
        Central routine for a simple write and read the answers until the device
        sends an "OK" or "ERROR".
        """
        ##sess = self.visa_handle.session
        # all lines have to end with a CR / LF
        setstr = cmd + '\r\n'
        # the device can not handle unicode strings
        ##cnt, sta = self.visa_handle.write(sess, setstr.encode('ascii') )
        self.write(setstr)
        # first, the device echos what was written
        ##rv, sta = self.visa_handle.read(sess, 1000) # .decode('ascii')
        rv = self.read()
        rv = rv.rstrip()
        if _USE_DEBUG:
            print("DBG write-echo:", rv)
        # then we collect the output lines until an OK or ERROR comes
        output = []
        while True:
            ##rv, sta = self.visa_handle.read(sess, 1000)
            rv = self.read()
            ##rv = rv.decode('ascii').rstrip()
            rv = rv.rstrip()
            if _USE_DEBUG:
                print("DBG write-answ:", rv)
            if rv.startswith('OK'):
                # positive answer returns all answer lines
                return output
            if rv.startswith('ERROR'):
                # negative answer raises an exception
                raise RuntimeError(output[-1])
            if output != "":
                # the output array contains all lines read from the device
                output.append(rv)


    def write_raw(self, cmd: str) -> None:
        """
        Central routine to send a value to the device
        """
        self._write(cmd)


    def ask_raw(self, cmd: str) -> str:
        """
        Central routine for a query (write and read).
        """
        output = self._write(cmd)
        # The output array contains all lines read from the device. If the
        # version information is read, it consists of two lines. The normal
        # answers have only one line.
        outval = output[-1].split(' = ')
        # The normal output format for values is <parameter> = <value> <unit>
        if len(outval) == 2:
            if _USE_DEBUG:
                print("DBG ask:", outval[1].split()[0])
            return outval[1].split()[0] # return only the value without the unit
        # returns the complete output (for version information)
        return output
