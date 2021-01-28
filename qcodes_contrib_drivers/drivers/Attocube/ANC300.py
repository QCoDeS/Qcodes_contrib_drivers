# -*- coding: utf-8 -*-
"""QCoDeS- Driver for the Attocube ANC300 controller.

This driver can be used with a simulation class (ANC300sim.py) to generate
reasonable answers to all requests. The only thing is to change two times
the comments as shown below (real mode/simulation mode).

Attention - the device has not feedback from the motor. That means, the current position is
not known. The driver can send a move command and the controller behaves like there is a motor
connected to it, even if there is no motor available.

Author:
    Michael Wagener, FZJ / ZEA-2, m.wagener@fz-juelich.de
"""

import time
import logging
import pyvisa

# real mode:
from qcodes import VisaInstrument
# simulation mode:
#from qcodes.instrument_drivers.attocube.ANC300sim import MockVisa

## do not forget to change the main class accordingly:
## real  -> class ANC300(VisaInstrument):
## simul -> class ANC300(MockVisa):

from qcodes.instrument.channel import InstrumentChannel, ChannelList
from qcodes import validators as vals


log = logging.getLogger(__name__)



class Anc300Axis(InstrumentChannel):

    def __init__(self, parent: 'ANC300', name: str, axis: int, sn: str) -> None:
        """Creates a new Anc300Axis class instance.
        
        The Attocube ANC300 piezo controller has up to 7 axis. Each of them are controlled
        by the same class.

        Args:
            parent: the internal QCoDeS name of the instrument this axis belongs to
            name: the internal QCoDeS name of the axis itself
            axis: the Index of the axis (1..7)
            sn: serial number of the axis controller to change some features

        Attributes:
            frequency: Set the frequency of the output signal. The maximum is restricted by the
                combination of output voltage and Capacitance of the piezo actuators.
            amplitude: Set the maximum level of the output signal.
            voltage: (Readonly) Reads the current stepping voltage.
            offset: Add a constant voltage to the output signal. Attention: the output level is
                only from 0 to 150 V.
            filter: Set the filter frequency of the internal low pass filter.
                For the ANM150 this attribute is not present.
                For the ANM200 and ANM300 this attribute has different allowed values.
            mode: Setting to a certain mode typically switches other functionalities off.
                'gnd': Setting to this mode diables all outputs and connects them to chassis mass.
                'inp': (Not for ANM150) In this mode, AC-IN and DC-IN can be enabled using the
                specific attributes. Setting to inp mode disables stepping and offset modes.
                'cap': Setting to cap mode starts a capacitance measurement. The axis returns to
                gnd mode afterwards. It is not needed to switch to gnd mode before.
                'stp': This enables stepping mode. AC-IN and DC-IN functionalities are not modified,
                while an offset function would be turned off.
                'off': This enables offset mode. AC-IN and DC-IN functionalities are not modified,
                while any stepping would be turned off.
                'stp+': This enables additive offset + stepping mode. Stepping waveforms are added
                to an offset. AC-IN and DC-IN functionalities are not modified.
                'stp-': This enables subtractive offset + stepping mode. Stepping waveforms are
                subtracted from an offset. AC-IN and DC-IN functionalities, are not modified.
            ac: When switching on the AC-IN feature, a voltage of up to 10 VAC can be added to the
                output (gain 1, no amplification) using the AC-IN BNC on the frontplate of the module.
            dc: When switching on the DC-IN feature, a voltage in the range -10 .. +10 V can be
                added to the output. The gain is 15.
            move: Start the movement with the given steps. For moving out use positive numbers and
                to move in use negative numbers.
            start: Start a continous movement in the given direction.
            triggerUp: Set/get input trigger up number on axis
            triggerDown: Set/get input trigger down number on axis
        """
        super().__init__(parent, name)
        self._axisnr = axis
        if sn != 'ANM200':
            self.add_parameter('frequency',
                               label='Set/get the stepping frequency',
                               get_cmd='getf {}'.format(axis),
                               set_cmd='setf {}'.format(axis)+' {}',
                               vals=vals.Ints(1, 10000),
                               get_parser=int,
                               unit='Hz',
                               docstring="""
                               Set the frequency of the output signal. The maximum is restricted by
                               the combination of output voltage and Capacitance of the piezo actuators.
                               """
                               )
        self.add_parameter('amplitude',
                           label='Set/get the stepping amplitude',
                           get_cmd='getv {}'.format(axis),
                           set_cmd='setv {}'.format(axis)+' {}',
                           vals=vals.Numbers(0.0, 150.0),
                           get_parser=float,
                           unit='V',
                           docstring="Set the maximum level of the output signal."
                           )
        self.add_parameter('voltage',
                           label='Set/get the stepping voltage',
                           get_cmd='geto {}'.format(axis),
                           set_cmd=False,
                           get_parser=float,
                           unit='V',
                           docstring="Reads the current stepping voltage."
                           )
        self.add_parameter('offset',
                           label='Set/get the offset voltage',
                           get_cmd='geta {}'.format(axis),
                           set_cmd='seta {}'.format(axis)+' {}',
                           vals=vals.Numbers(0.0, 150.0),
                           get_parser=float,
                           unit='V',
                           docstring="""
                           Add a constant voltage to the output signal.
                           Attention: the output level is only from 0 to 150 V.
                           """
                           )
        if sn == 'ANM200':
            self.add_parameter('filter',
                               label='Set/get filter setting',
                               get_cmd='getfil {}'.format(axis),
                               set_cmd='setfil {}'.format(axis)+' {}',
                               vals=vals.Enum('1.6', '16', '160', '1600'),
                               unit='Hz',
                               docstring="Set the filter frequency of the internal low pass filter."
                               )
        if sn == 'ANM300':
            self.add_parameter('filter',
                               label='Set/get filter setting',
                               get_cmd='getfil {}'.format(axis),
                               set_cmd='setfil {}'.format(axis)+' {}',
                               vals=vals.Enum('off', '16', '160'),
                               unit='Hz',
                               docstring="Set the filter frequency of the internal low pass filter."
                               )
        if sn == 'ANM150':
            mode_vals = ['gnd', 'cap', 'stp', 'off', 'stp+', 'stp-']
        elif sn == 'ANM200':
            mode_vals = ['gnd', 'cap', 'stp', 'off', 'stp+', 'stp-', 'inp']
        else: # ANM300
            mode_vals = ['gnd', 'cap', 'stp', 'off', 'stp+', 'stp-', 'inp']
        mode_docs = """
                    'gnd': Setting to this mode diables all outputs and connects them to chassis mass.
                    'cap': Setting to cap mode starts a capacitance measurement. The axis returns to
                           gnd mode afterwards. It is not needed to switch to gnd mode before.
                    'stp': This enables stepping mode. AC-IN and DC-IN functionalities are not
                           modified, while an offset function would be turned off.
                    'off': This enables offset mode. AC-IN and DC-IN functionalities are not
                           modified, while any stepping would be turned off.
                    'stp+': This enables additive offset + stepping mode. Stepping waveforms are
                            added to an offset. AC-IN and DC-IN functionalities are not modified.
                    'stp-': This enables subtractive offset + stepping mode. Stepping waveforms are
                            subtracted from an offset. AC-IN and DC-IN functionalities, are not modified.
                    """
        if 'inp' in mode_vals:
            mode_docs += """
                         'inp': In this mode, AC-IN and DC-IN can be enabled using the specific
                         attributes. Setting to inp mode disables stepping and offset modes.
                         """
        self.add_parameter('mode',
                           label='Set/get mode',
                           get_cmd='getm {}'.format(axis),
                           set_cmd='setm {}'.format(axis)+' {}',
                           vals=vals.Enum(*mode_vals),
                           docstring="""
                           Setting to a certain mode typically switches other functionalities off.
                           Especially, there are the following modes:
                           """ + mode_docs
                           )
        if sn != 'ANM150':
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
        Internal helper function to start the movement. This will not wait until the move is
        finished. So multiple axis can be started one after the other.

        Args:
            value: the amount of steps to move, the sign denotes the direction

        Returns:
            None

        Raises:
            ValueError: if the value is zero
        """
        if value < 0:
            self._parent.write('stepd {} {}'.format(self._axisnr, -value))
        elif value > 0:
            self._parent.write('stepu {} {}'.format(self._axisnr, value))
        else:
            raise ValueError("zero is an invalid move parameter")


    def _contmove(self, direc: str):
        """
        Internal helper function to start the continous movement. This will not wait until the move
        is finished. So multiple axis can be started one after the other.

        Args:
            direc: the direction 'up' or 'down'

        Returns:
            None

        Raises:
            ValueError: if the given direction is invalid
        """
        if direc == 'up':
            self._parent.write('stepu {} c'.format(self._axisnr))
        elif direc == 'down':
            self._parent.write('stepd {} c'.format(self._axisnr))
        else:
            raise ValueError("no 'up' or 'donw' given")


    def waitMove(self, wait=1.0, timeout=0):
        """Global function to wait until the movement is finished.

        The commandinterface has the function 'stepw n' to wait until the axis stops moving. The
        controller sends the 'OK' after the axis stops, so the communication is hanging. In the
        former version with the pyserial interface, it will work fine. But the visa library
        throws an error if the communication timed out. After this, the read function didn't
        get the needed 'OK'. To avoid this, this routine asks the current output voltage. This
        voltage will be zero if the axis has stopped.

        Args:
            wait: time to wait between the checks
            timeout: number of seconds to generate a RuntimeError if not finished moving

        Returns:
            None. This function will block, until the motion of this axis has been stopped.
        """
        start = time.time()
        while True:
            volt = self._parent.ask('geto {}'.format(self._axisnr))
            if float(volt) == 0.0:
                return
            time.sleep(wait)
            if timeout > 0:
                if time.time() - start >= timeout:
                    raise RuntimeError('waitMove timed out')


    def stopMove(self):
        """
        Global function to stop the movement.
        """
        self._parent.write('stop {}'.format(self._axisnr))



class Anc300TriggerOut(InstrumentChannel):

    def __init__(self, parent: 'ANC300', name: str, num: int) -> None:
        """The Attocube ANC300 piezo controller has three trigger outputs.
        
        This function cannot be tested because this function belongs to a specific controller
        feature code. This code was not available during the tests.
        
        Args:
            parent: the internal QCoDeS name of the instrument this output belongs to
            name: the internal QCoDeS name of the output itself
            num: the Index of the trigger output

        Attributes:
            state: Set / get the state of the output
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



class ANC300(VisaInstrument):
#class ANC300(MockVisa):
    """
    This is the qcodes driver for the Attocube ANC300.
    
    Be careful to correct the parameters if not useing the USB port.

    Status:
        coding: finished
        communication tests: done
        usage in experiment: not yet
    """

    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, 5, '\r\n', **kwargs)

        # configure the port
        if 'ASRL' not in address:
            self.visa_handle.baud_rate = 38400 # USB has no baud rate parameter
        self.visa_handle.stop_bits = pyvisa.constants.StopBits.one
        self.visa_handle.parity = pyvisa.constants.Parity.none
        self.visa_handle.read_termination = '\r\n'
        self.parameters.pop('IDN') # Get rid of this parameter

        # for security check the ID from the device
        self.idn = self.ask("ver")
        log.debug("Main version:", self.idn)
        if not self.idn.startswith("attocube ANC300"):
            raise RuntimeError("Invalid device ID found: "+str(self.idn))

        # Now request all serial numbers of the axis modules. The first 6 chars are the id
        # of the module type. This will be used to enable special parameters.
        # Instantiate the axis channels only for available axis
        axischannels = ChannelList(self, "Anc300Channels", Anc300Axis,
                                   snapshotable=False)
        for ax in range(1, 7+1):
            try:
                tmp = self.ask('getser {}'.format(ax))
                name = 'axis{}'.format(ax)
                axischan = Anc300Axis(self, name, ax, tmp[:6])
                axischannels.append(axischan)
                self.add_submodule(name, axischan)
            except:
                pass
        axischannels.lock()
        self.add_submodule('axis_channels', axischannels)

        # instantiate the trigger channels even if they could not be tested
        triggerchannels = ChannelList(self, "Anc300Trigger", Anc300TriggerOut,
                                      snapshotable=False)
        for ax in [1, 2, 3]:
            name = 'trigger{}'.format(ax)
            trigchan = Anc300TriggerOut(self, name, ax)
            triggerchannels.append(trigchan)
            self.add_submodule(name, trigchan)
        triggerchannels.lock()
        self.add_submodule('trigger_channels', triggerchannels)


    def write_raw(self, cmd: str) -> None:
        """Write cmd and wait until the 'OK' or 'ERROR' comes back from the device.
        
        Args:
            cmd: Command to write to controller.

        Returns:
            None

        Raises:
            RuntimeError: if Error-Message from the device is read.
        """
        status = super().ask_raw(cmd) # send the command to the device and read the echo/status
        if status == cmd:
            # now the device sends an echo
            status = self.visa_handle.read() # read the status line again
        if status.startswith('OK'):
            return
        if status.startswith('ERROR'):
            raise RuntimeError(status)
        # the line before the 'ERROR' a message will be send from the device
        response = status
        status = self.visa_handle.read() # read the last status line
        if status.startswith('ERROR'):
            raise RuntimeError(response)
        return


    def ask_raw(self, cmd: str) -> str:
        """Query instrument with cmd and return response.
        
        Args:
            cmd: Command to write to controller.

        Returns:
            Response of Attocube controller to the query.

        Raises:
            RuntimeError: if Error-Message from the device is read.
        """
        response = super().ask_raw(cmd) # send the command to the device and read the echo/status
        if response.startswith('> '): # sometimes the response starts with '> '. I don't know why.
            response = response[2:]
        if response == cmd:
            # now the device has send an echo
            response = self.visa_handle.read() # read the response line again
            if response.startswith('> '):
                response = response[2:]
        status = self.visa_handle.read() # read the status line
        if status.startswith('OK'):
            if '=' in response:
                # "frequency = 220 Hz" -> filter the 220
                tmp = response.split('=')
                return tmp[1].split()[0] # a single value
            return response # the complete string
        if status.startswith('ERROR'):
            raise RuntimeError(response)
        # the 'ver' command answers with two lines...
        response = response + " - " + status
        status = self.visa_handle.read() # read the second status line
        if status.startswith('ERROR'):
            raise RuntimeError(response)
        return response


    def stopall(self):
        """
        Routine to stop all axis, regardless if the axis is available
        """
        self.log.debug("Stop all axis.")
        for a in range(7):
            self.write('stop {}'.format(a+1))


    def close(self):
        """
        Override of the base class' close function
        """
        self.log.debug("Close the device.")
        super().close()


    def version(self):
        """
        Read all possible version informations.

        Args:
            None

        Returns:
            Dict with all version informations
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

        Returns:
            dict with all parameters, the key is the modulename and the parametername
        """
        retval = dict()
        if submod == "*":
            # ID and options only if all modules are returned
            retval.update(self.version())

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
