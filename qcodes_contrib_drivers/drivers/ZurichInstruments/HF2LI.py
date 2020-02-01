from typing import Dict, List, Optional, Sequence, Any, Union
import numpy as np
import logging
log = logging.getLogger(__name__)

import zhinst.ziPython, zhinst.utils
import qcodes as qc
from qcodes.instrument.base import Instrument
import qcodes.utils.validators as vals

class HF2LI(Instrument):
    """Qcodes driver for Zurich Instruments HF2LI lockin amplifier.

    This driver is meant to emulate a single-channel lockin amplifier,
    so one instance has a single demodulator, a single sigout channel,
    and multiple auxout channels (for X, Y, R, Theta, or an arbitrary manual value).
    Multiple instances can be run simultaneously as independent lockin amplifiers.

    Args:
        name (str): Name of instrument.
        device (str): Device name, e.g. "dev204", used to create zhinst API session.
        demod (int): Index of the demodulator to use.
        sigout (int): Index of the sigout channel to use as excitation source.
        auxouts (dict[str, int]): Dict of the form {output: index},
            where output is a key of HF2LI.OUTPUT_MAPPING, for example {"X": 0, "Y": 3}
            to use the instrument as a lockin amplifier in X-Y mode with auxout channels 0 and 3.
    """
    OUTPUT_MAPPING = {-1: 'manual', 0: 'X', 1: 'Y', 2: 'R', 3: 'Theta'}
    def __init__(self, name: str, device: str, demod: int, sigout: int,
        auxouts: Dict[str, int], **kwargs) -> None:
        super().__init__(name, **kwargs)
        instr = zhinst.utils.create_api_session(device, 1, required_devtype='HF2LI')
        self.daq, self.dev_id, self.props = instr
        self.demod = demod
        self.sigout = sigout
        self.auxouts = auxouts
        log.info('Successfully connected to {}.'.format(name))

        for ch in self.auxouts:
            self.add_parameter(name=ch,
                               label='Scaled {} output value'.format(ch),
                               unit='V',
                               get_cmd=lambda ch=ch: self._get_output_value(channel=ch),
                               get_parser=float
                               )
            self.add_parameter(name='gain_{}'.format(ch),
                               label='{} output gain'.format(ch),
                               unit='V/Vrms',
                               get_cmd=lambda ch=ch: self._get_gain(channel=ch),
                               get_parser=float,
                               set_cmd=lambda gain, ch=ch: self._set_gain(gain, channel=ch),
                               vals=vals.Numbers()
                               )
            self.add_parameter(name='offset_{}'.format(ch),
                               label='{} output offset'.format(ch),
                               unit='V',
                               get_cmd=lambda ch=ch: self._get_offset(channel=ch),
                               get_parser=float,
                               set_cmd=lambda offset, ch=ch: self._set_offset(offset, channel=ch),
                               vals=vals.Numbers(-2560, 2560)
                               )
            self.add_parameter(name='output_{}'.format(ch),
                               label='{} outptut select'.format(ch),
                               unit='',
                               get_cmd=lambda ch=ch: self._get_output_select(channel=ch),
                               get_parser=str,
                            #    set_cmd=lambda output, ch=ch: self._set_output_select(output, channel=ch),
                            #    vals=vals.Ints(-1,3)
                               )
            self._set_output_select(channel=ch)
            
        self.add_parameter(name='phase',
                           label='Phase',
                           unit='deg',
                           get_cmd=self._get_phase,
                           get_parser=float,
                           set_cmd=self._set_phase,
                           vals=vals.Numbers(-180,180)
                           )
        self.add_parameter(name='time_constant',
                           label='Time constant',
                           unit='s',
                           get_cmd=self._get_time_constant,
                           get_parser=float,
                           set_cmd=self._set_time_constant,
                           vals=vals.Numbers()
                           )  
        self.add_parameter(name='frequency',
                           label='Frequency',
                           unit='Hz',
                           get_cmd=self._get_frequency,
                           get_parser=float
                           ) 
        self.add_parameter(name='sigout_range',
                           label='Signal output range',
                           unit='V',
                           get_cmd=self._get_sigout_range,
                           get_parser=float,
                           set_cmd=self._set_sigout_range,
                           vals=vals.Enum(0.01, 0.1, 1, 10),
                           snapshot_get=False
                           )
        self.add_parameter(name='sigout_offset',
                           label='Signal output offset',
                           unit='V',
                           get_cmd=self._get_sigout_offset,
                           get_parser=float,
                           set_cmd=self._set_sigout_offset,
                           vals=vals.Numbers(-1, 1),
                           snapshot_get=False
                           )
        self.add_parameter(name='sigout_amplitude',
                           label='Signal output amplitude',
                           unit='V',
                           get_cmd=self._get_sigout_amplitude,
                           get_parser=float,
                           set_cmd=self._set_sigout_amplitude,
                           vals=vals.Numbers(-1, 1),
                           snapshot_get=False
                           )

    def _get_phase(self):
        path = '/{}/demods/{}/phaseshift/'.format(self.dev_id, self.demod)
        phase = self.daq.getDouble(path)
        return phase

    def _set_phase(self, phase):
        path = '/{}/demods/{}/phaseshift/'.format(self.dev_id, self.demod)
        self.daq.setDouble(path, phase)
        
    def _get_gain(self, channel=None):
        path = '/{}/auxouts/{}/scale/'.format(self.dev_id, self.auxouts[channel])
        gain = self.daq.getDouble(path)
        return gain

    def _set_gain(self, gain, channel=None):
        path = '/{}/auxouts/{}/scale/'.format(self.dev_id, self.auxouts[channel])
        self.daq.setDouble(path, gain)

    def _get_offset(self, channel=None):
        path = '/{}/auxouts/{}/offset/'.format(self.dev_id, self.auxouts[channel])
        gain = self.daq.getDouble(path)
        return gain

    def _set_offset(self, offset, channel=None):
        path = '/{}/auxouts/{}/offset/'.format(self.dev_id, self.auxouts[channel])
        self.daq.setDouble(path, offset)

    def _get_output_value(self, channel=None):
        path = '/{}/auxouts/{}/value/'.format(self.dev_id, self.auxouts[channel])
        value = self.daq.getDouble(path)
        return value

    def _get_output_select(self, channel=None):
        path = '/{}/auxouts/{}/outputselect/'.format(self.dev_id, self.auxouts[channel])
        idx = int(self.daq.getDouble(path))
        output = self.OUTPUT_MAPPING[idx]
        return output

    def _set_output_select(self, channel=None):
        path = '/{}/auxouts/{}/outputselect/'.format(self.dev_id, self.auxouts[channel])
        keys = list(self.OUTPUT_MAPPING.keys())
        idx = keys[list(self.OUTPUT_MAPPING.values()).index(channel)]
        self.daq.setInt(path, idx)

    def _get_time_constant(self):
        path = '/{}/demods/{}/timeconstant/'.format(self.dev_id, self.demod)
        tc = self.daq.getDouble(path)
        return tc

    def _set_time_constant(self, tc):
        path = '/{}/demods/{}/timeconstant/'.format(self.dev_id, self.demod)
        self.daq.setDouble(path, tc)

    def _get_sigout_range(self):
        path = '/{}/sigouts/{}/range/'.format(self.dev_id, self.sigout[0])
        range = self.daq.getDouble(path)
        return range

    def _set_sigout_range(self, rng):
        path = '/{}/sigouts/{}/range/'.format(self.dev_id, self.sigout[0])
        self.daq.setDouble(path, rng)

    def _get_sigout_offset(self):
        path = '/{}/sigouts/{}/offset/'.format(self.dev_id, self.sigout[0])
        range = self.daq.getDouble(path)
        return range

    def _set_sigout_offset(self, offset):
        path = '/{}/sigouts/{}/offset/'.format(self.dev_id, self.sigout[0])
        self.daq.setDouble(path, offset)

    def _get_sigout_amplitude(self):
        path = '/{}/sigouts/{}/amplitudes/{}/'.format(self.dev_id, self.sigout[0], self.sigout[1])
        range = self.daq.getDouble(path)
        return range

    def _set_sigout_amplitude(self, amp):
        path = '/{}/sigouts/{}/amplitudes/{}/'.format(self.dev_id, self.sigout[0], self.sigout[1])
        self.daq.setDouble(path, amp)

    def _get_frequency(self):
        path = '/{}/demods/{}/freq/'.format(self.dev_id, self.demod)
        freq = self.daq.getDouble(path)
        return freq

    def sample(self):
        path = '/{}/demods/{}/sample/'.format(self.dev_id, self.demod)
        return self.daq.getSample(path)