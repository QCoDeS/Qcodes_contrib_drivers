# -*- coding: utf-8 -*-
"""
File:    ANC300.py
Date:    Jan 2020
Author:  Michael Wagener, FZJ / ZEA-2, m.wagener@fz-juelich.de
Purpose: Main instrument driver for the Attocube ANC300 controller

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!! This driver code is written for our instrument, the ANC300 with two !!!
!!! ANM150 modules. Therefore this code contains no functions to        !!!
!!! automatically distinguish between the modules.                      !!!
!!! In the comments the axis types are noted and the code not suitable  !!!
!!! for the ANM150 is commented out.                                    !!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

PyLint rating: Your code has been rated at 9.06/10

"""

from typing import List
import serial

from qcodes.instrument.base import Instrument
from qcodes.instrument.channel import InstrumentChannel, ChannelList
from qcodes import validators as vals

# if set to True, every communication line is printed
_USE_DEBUG = False

# if set to True, the simulation in ANC300sim.py is used and no real device
_USE_SIMULATION = False




class Anc300Axis(InstrumentChannel):
    """
    The Attocube ANC300 piezo controller has up to 7 axis.
    Parameters:
        frequency: Set the frequency of the output signal. The maximum is
            restricted by the combination of output voltage and
            Capacitance of the piezo actuators.
        amplitude: Set the maximum level of the output signal.
        offset: Add a constant voltage to the output signal.
            Attention: the output level is only from 0 to 150 V.
        filter: Set the filter frequency of the internal low pass filter.
        mode: Setting to a certain mode typically switches other functionalities
            off. Especially, there are the following modes:
                'gnd': Setting to this mode diables all outputs and
                       connects them to chassis mass.
                'inp': In this mode, AC-IN and DC-IN can be enabled
                       using the setaci and setdci commands. Setting
                       to inp mode disables stepping and offset modes.
                'cap': Setting to cap mode starts a capacitance measurement.
                       The axis returns to gnd mode afterwards. It is not
                       needed to switch to gnd mode before.
                'stp': This enables stepping mode. AC-IN and DC-IN
                       functionalities are not modified, while an offset
                       function would be turned off.
                'off': This enables offset mode. AC-IN and DC-IN
                       functionalities are not modified, while any
                       stepping would be turned off.
                'stp+': This enables additive offset + stepping mode.
                        Stepping waveforms are added to an offset.
                        AC-IN and DC-IN functionalities are not modified.
                'stp-': This enables subtractive offset + stepping mode.
                        Stepping waveforms are subtracted from an offset.
                        AC-IN and DC-IN functionalities, are not modified.
        ac: When switching on the AC-IN feature, a voltage of up to 10 VAC
            can be added to the output (gain 1, no amplification) using
            the AC-IN BNC on the frontplate of the module.
        dc: When switching on the DC-IN feature, a voltage in the range
            -10 .. +10 V can be added to the output. The gain is 15.
        move: Start the movement with the given steps. For moving out
              use positive numbers and to move in use negative numbers.
        start: Start a continous movement in the given direction.
        triggerUp: Set/get input trigger up number on axis
        triggerDown: Set/get input trigger down number on axis
    """
    def __init__(self, parent: 'ANC300', name: str, axis: int) -> None:
        """
        Creates a new Anc300Axis class instance
        Args:
            parent: the internal QCoDeS name of the instrument this axis belongs to
            name: the internal QCoDeS name of the axis itself
            axis: the Index of the axis
        """
        super().__init__(parent, name)
        self._axisnr = axis
        self.add_parameter('frequency',
                           label='Set/get the stepping frequency',
                           get_cmd='getf {}'.format(axis),
                           set_cmd='setf {}'.format(axis)+' {}',
                           vals=vals.Ints(1, 10000),
                           unit='Hz',
                           docstring="""
                           Set the frequency of the output signal. The maximum is
                           restricted by the combination of output voltage and
                           Capacitance of the piezo actuators.
                           """
                           )
        self.add_parameter('amplitude',
                           label='Set/get the stepping amplitude',
                           get_cmd='getv {}'.format(axis),
                           set_cmd='setv {}'.format(axis)+' {}',
                           vals=vals.Numbers(0.0, 150.0),
                           unit='V',
                           docstring="Set the maximum level of the output signal."
                           )
        self.add_parameter('offset',
                           label='Set/get the offset voltage',
                           get_cmd='geta {}'.format(axis),
                           set_cmd='seta {}'.format(axis)+' {}',
                           vals=vals.Numbers(0.0, 150.0),
                           unit='V',
                           docstring="""
                           Add a constant voltage to the output signal.
                           Attention: the output level is only from 0 to 150 V.
                           """
                           )
        # this is not for ANM150
        #self.add_parameter('filter',
        #                   label='Set/get filter setting',
        #                   get_cmd='getfil {}'.format(axis),
        #                   set_cmd='setfil {}'.format(axis)+' {}',
        #                   vals=vals.Enum('off', '16', '160'),
        #                   unit='Hz',
        #                   docstring="Set the filter frequency of the internal low pass filter."
        #                   )
        self.add_parameter('mode',
                           label='Set/get mode',
                           get_cmd='getm {}'.format(axis),
                           set_cmd='setm {}'.format(axis)+' {}',
                           #vals=vals.Enum(...'inp'...) not for ANM150
                           vals=vals.Enum('gnd', 'cap', 'stp', 'off', 'stp+', 'stp-'),
                           docstring="""
                           Setting to a certain mode typically switches other functionalities
                           off. Especially, there are the following modes:
                               'gnd': Setting to this mode diables all outputs and
                                      connects them to chassis mass.
                               'cap': Setting to cap mode starts a capacitance measurement.
                                      The axis returns to gnd mode afterwards. It is not
                                      needed to switch to gnd mode before.
                               'stp': This enables stepping mode. AC-IN and DC-IN
                                      functionalities are not modified, while an offset
                                      function would be turned off.
                               'off': This enables offset mode. AC-IN and DC-IN
                                      functionalities are not modified, while any
                                      stepping would be turned off.
                               'stp+': This enables additive offset + stepping mode.
                                       Stepping waveforms are added to an offset.
                                       AC-IN and DC-IN functionalities are not modified.
                               'stp-': This enables subtractive offset + stepping mode.
                                       Stepping waveforms are subtracted from an offset.
                                       AC-IN and DC-IN functionalities, are not modified.
                            """
                           # not for ANM150:
                           #'inp': In this mode, AC-IN and DC-IN can be enabled
                           #       using the setaci and setdci commands. Setting
                           #       to inp mode disables stepping and offset modes.
                           )
        self.add_parameter('ac',
                           label='Set/get status of AC-IN input',
                           get_cmd='getaci {}'.format(axis),
                           set_cmd='setaci {}'.format(axis)+' {}',
                           vals=vals.Enum('off', 'on'),
                           docstring="""
                           When switching on the AC-IN feature, a voltage of up to 10 VAC
                           can be added to the output (gain 1, no amplification) using
                           the AC-IN BNC on the frontplate of the module.
                           """
                           )
        self.add_parameter('dc',
                           label='Set/get status of DC-IN input',
                           get_cmd='getdci {}'.format(axis),
                           set_cmd='setdci {}'.format(axis)+' {}',
                           vals=vals.Enum('off', 'on'),
                           docstring="""
                           When switching on the DC-IN feature, a voltage in the range
                           -10 .. +10 V can be added to the output. The gain is 15.
                           """
                           )
        self.add_parameter('move',
                           label='Move steps',
                           get_cmd=False,
                           set_cmd=self._domove,
                           vals=vals.Ints(),
                           docstring="""
                           Start the movement with the given steps. For moving out
                           use positive numbers and to move in use negative numbers.
                           """
                           )
        self.add_parameter('start',
                           label='Move continously',
                           get_cmd=False,
                           set_cmd=self._contmove,
                           vals=vals.Enum('up', 'down'),
                           docstring="Start a continous movement in the given direction."
                           )
        self.add_parameter('triggerUp',
                           label='Set/get input trigger up number on axis',
                           get_cmd='gettu {}'.format(axis),
                           set_cmd='settu {}'.format(axis)+' {}',
                           vals=vals.Enum('off', '1', '2', '3', '4', '5', '6', '7'),
                           docstring="Set/get input trigger up number on axis"
                           )
        self.add_parameter('triggerDown',
                           label='Set/get input trigger down numbers on axis',
                           get_cmd='gettd {}'.format(axis),
                           set_cmd='settd {}'.format(axis)+' {}',
                           vals=vals.Enum('off', '1', '2', '3', '4', '5', '6', '7'),
                           docstring="Set/get input trigger down number on axis"
                           )

    def _domove(self, value: int):
        """
        Internal helper function to start the movement.
        Parameter:
            value - the amount of steps to move, the sign denotes the direction
        """
        if value < 0:
            self._parent.write('stepd {} {}'.format(self._axisnr, -value))
        elif value > 0:
            self._parent.write('stepu {} {}'.format(self._axisnr, value))
        else:
            raise RuntimeError("zero is an invalid move parameter")

    def _contmove(self, direc: str):
        """
        Internal helper function to start the continous movement.
        Parameter:
            direc - the direction 'up' or 'down'
        """
        if direc == 'up':
            self._parent.write('stepu {} c'.format(self._axisnr))
        elif direc == 'down':
            self._parent.write('stepd {} c'.format(self._axisnr))

    def waitMove(self):
        """
        Global function to wait until the movement is finished.
        """
        self._parent.write('stepw {}'.format(self._axisnr))

    def stopMove(self):
        """
        Global function to stop the movement.
        """
        self._parent.write('stop {}'.format(self._axisnr))



class Anc300TriggerOut(InstrumentChannel):
    """
    The Attocube ANC300 piezo controller has three trigger outputs.
    Parameters:
        state: Set / get the state of the output
    NOT FOR THE CURRENT TEST DEVICE!
    """
    def __init__(self, parent: 'ANC300', name: str, num: int) -> None:
        """
        Creates a new TriggerOut Signal
        Args:
            parent: the internal QCoDeS name of the instrument this output belongs to
            name: the internal QCoDeS name of the output itself
            num: the Index of the trigger output
        """
        super().__init__(parent, name)
        self.add_parameter('state',
                           label='Set/get trigger output level',
                           get_cmd='getto {}'.format(num),
                           set_cmd='setto {}'.format(num)+' {}',
                           val_mapping={'off': 0, 'on': 1},
                           vals=vals.Enum('off', 'on'),
                           docstring="Sets the trigger output signal"
                           )



class ANC300(Instrument):
    """
    This is the qcodes driver for the Attocube ANC300.

    Status:
        coding: finished
        communication tests: done
        usage in experiment: not yet
    """

    def __init__(self, name, address, **kwargs):
        super().__init__(name, **kwargs)

        if _USE_SIMULATION:
            # The simulation class has the same functions as the serial.Serial():
            #   write() / readline() / close()
            from qcodes.instrument_drivers.attocube.ANC300sim import MockComHandle
            self._comport = MockComHandle()
        else:
            # initialization of serial port
            self._comport = serial.Serial()
            self._comport.port = address
            self._comport.timeout = 2
            try:
                self._comport.open()
            except:
                # make a second try to open the port. If this fails then report it
                self._comport.close()
                self._comport.open()
            self._comport.flushInput()
            self._comport.flushOutput()

        # for security check the ID from the device
        self.idn = self.ask("ver")
        if _USE_DEBUG:
            print("DBG:", self.idn)
        if not self.idn[0].startswith("attocube ANC300"):
            raise RuntimeError("Invalid device ID found: "+str(self.idn))

        # instantiate the axis channels
        axischannels = ChannelList(self, "Anc300Channels", Anc300Axis,
                                   snapshotable=False)
        for ax in range(1, 7+1):
            name = 'axis{}'.format(ax)
            axischan = Anc300Axis(self, name, ax)
            axischannels.append(axischan)
            self.add_submodule(name, axischan)
        axischannels.lock()
        self.add_submodule('axis_channels', axischannels)

        # instantiate the trigger channels
        triggerchannels = ChannelList(self, "Anc300Trigger", Anc300TriggerOut,
                                      snapshotable=False)
        for ax in [1, 2, 3]:
            name = 'trigger{}'.format(ax)
            trigchan = Anc300TriggerOut(self, name, ax)
            triggerchannels.append(trigchan)
            self.add_submodule(name, trigchan)
        triggerchannels.lock()
        self.add_submodule('trigger_channels', triggerchannels)


    def _write(self, cmd: str):
        """
        Central routine for a simple write and read the answers until the device
        sends an "OK" or "ERROR".
        """
        # all lines have to end with a CR / LF
        setstr = cmd + '\r\n'
        # the device can not handle unicode strings
        self._comport.write(setstr.encode('ascii'))
        # first, the device echos what was written
        rv = self._comport.readline().decode('ascii')
        if _USE_DEBUG:
            print("DBG write-echo:" + rv)
        # then we collect the output lines until an OK or ERROR comes
        output: List[str] = []
        while True:
            rv = self._comport.readline().decode('ascii').rstrip()
            if _USE_DEBUG:
                print("DBG write-answ:" + rv)
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
                print("DBG ask:" + outval[1].split()[0])
            return outval[1].split()[0] # return only the value without the unit
        # returns the complete output (for version information)
        return output


    def stopall(self):
        """
        Routine to stop all axis, regardless if the axis is available
        """
        if _USE_DEBUG:
            print("Stop all axis")
        for a in range(7):
            self._write('stop {}'.format(a+1))


    def close(self):
        """
        Override of the base class' close function
        """
        self._comport.close()
        super().close()


    def version(self):
        """
        Read all possible version informations and returns them as a dict
        """
        retval = dict()
        retval['Version'] = self.ask('ver')
        retval['ContrSN'] = self.ask('getcser')
        for i in range(7):
            try:
                retval['SN{}'.format(i+1)] = self.ask('getser {}'.format(i+1))
            except:
                # if the axis module is not installed ...
                retval['SN{}'.format(i+1)] = 'EMPTY'
        return retval


    def getall(self, submod="*"):
        """
        Read all parameters and retun them to the caller. This will scan all
        submodules with all parameters, so in this function no changes are
        necessary for new modules or parameters.
        Args:
            submod: (optional) returns only the parameters for this submodule
        Output:
            dict with all parameters, the key is the modulename and the parametername
        """
        retval = {}
        if submod == "*":
            # ID and options only if all modules are returned
            retval.update({"ID": self.idn})

        for m in self.submodules:
            mod = self.submodules[m]
            if not isinstance(mod, ChannelList) and (submod in ("*", m)):
                for p in mod.parameters:
                    par = mod.parameters[p]
                    try:
                        if par.unit:
                            val = str(par()).strip() + " " + par.unit
                        else:
                            val = str(par()).strip()
                    except:
                        val = "** not readable **"
                    retval.update({m + "." + p: val})

        return retval
