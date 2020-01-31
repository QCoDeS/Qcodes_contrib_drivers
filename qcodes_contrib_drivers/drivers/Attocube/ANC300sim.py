# -*- coding: utf-8 -*-
"""
File:    ANC300sim.py
Date:    Jan 2020
Author:  Michael Wagener, FZJ / ZEA-2, m.wagener@fz-juelich.de
Purpose: Simulation for the Attocube ANC300 driver in the same way as
         it is used in our lab.
"""

# if set to True, every communication line is printed
_USE_DEBUG = False


class MockComHandle:
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

    def close(self):
        # make it an error to ask or write after close
        if _USE_DEBUG:
            print("DBG-Mock: close")
        self.closed = True

    def write(self, cmd):
        if self.closed:
            raise RuntimeError("Trying to write to a closed instrument")
        cmd = cmd.decode('ascii').rstrip()
        if _USE_DEBUG:
            print("DBG-Mock: write", cmd)
        # setxx <axis> <val> --> <kenn> = <val> <unit>
        # getxx <axis> <val> --> <kenn> = <val> <unit>
        if cmd.startswith('set'):
            self.answer = [ cmd, 'OK' ]
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
                    unit = unit[0]
                setval = [ val[0]+' = '+tmp[2]+' '+unit ]
                self.cmddef.update( {cmd: setval} )
            else:
                self.cmddef.update( {cmd: tmp[2]} )
            return
        if cmd in self.cmddef:
            self.answer = [ cmd ]
            for c in self.cmddef[cmd]:
                self.answer.append(c)
            if self.answer[-1] != 'ERROR':
                self.answer.append( 'OK' )
            return
        self.answer = [ cmd, 'OK' ]

    def readline(self):
        if _USE_DEBUG:
            print("DBG-Mock: readline", self.answer)
        if len(self.answer) > 0:
            return self.answer.pop(0).encode('ascii')
        return 'ERROR'.encode('ascii')
