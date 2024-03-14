# -*- coding: utf-8 -*-
"""QCoDeS-Driver for Rohde & Schwartz SMB100A microwave signal generator:
https://www.rohde-schwarz.com/us/products/test-and-measurement/analog-signal-generators/rs-smb100a-microwave-signal-generator_63493-9379.html

Authors:
    Julien Barrier <julien@julienbarrier.eu>, 2023
"""
import logging
from typing import Any

from qcodes.instrument import VisaInstrument
from qcodes.parameters import Parameter, create_on_off_val_mapping
from qcodes import validators as vals

log = logging.getLogger(__name__)


class RohdeSchwarz_SMB100A(VisaInstrument):
    """
    Class to represent a Rohde & Schwartz SMB100A microwave signal generator

    status: beta-version

    Args:
        name: name for the instrument
        address: Visa resource name to connect
    """
    def __init__(self, name: str, address: str, **kwargs: Any) -> None:
        super().__init__(name, address, terminator='\n', **kwargs)

        self.frequency = Parameter(
            'frequency',
            label='Frequency',
            unit='Hz',
            get_cmd='SOUR:FREQ?',
            set_cmd='SOUR:FREQ {:.2f}',
            get_parser=float,
            vals=vals.Numbers(1e5, 20e9),
            instrument=self
        )

        self.phase = Parameter(
            'phase',
            label='Phase',
            unit='deg',
            get_cmd='SOUR:PHAS?',
            set_cmd='SOUR:PHAS {:.2f}',
            get_parser=float,
            vals=vals.Numbers(0, 360),
            instrument=self
        )

        self.power = Parameter(
            'power',
            label='Power',
            unit='dBm',
            get_cmd='SOUR:POW?',
            set_cmd='SOUR:POW {:.2f}',
            get_parser=float,
            vals=vals.Numbers(-120, 30),
            instrument=self
        )

        self.status = Parameter(
            'status',
            label='RF Output',
            get_cmd=':OUTP:STAT?',
            set_cmd=':OUTP:STAT {}',
            val_mapping=create_on_off_val_mapping(on_val='1', off_val='0'),
            vals=vals.Ints(0, 1),
            instrument=self
        )

        self.pulsemod_state = Parameter(
            'pulsemod_state',
            label='Pulse Modulation',
            get_cmd=':SOUR:PULM:STAT?',
            set_cmd=':SOUR:PULM:STAT {}',
            val_mapping=create_on_off_val_mapping(on_val='1', off_val='0'),
            vals=vals.Ints(0, 1),
            instrument=self
        )

        self.sweep_freq_start = Parameter(
            'sweep_freq_start',
            label='Sweep: start frequency',
            unit='Hz',
            get_cmd='FREQ:START?',
            set_cmd='FREQ:START {:.12f} Hz',
            get_parser=float,
            vals=vals.Numbers(100e3, 20e9),
            instrument=self
        )

        self.sweep_freq_stop = Parameter(
            'sweep_freq_stop',
            label='Sweep: stop frequency',
            unit='Hz',
            get_cmd='FREQ:STOP?',
            set_cmd='FREQ:STOP {:.12f} Hz',
            get_parser=float,
            vals=vals.Numbers(100e3, 20e9),
            instrument=self
        )

        self.sweep_step = Parameter(
            'sweep_stop',
            label='Sweep: frequency step',
            unit='Hz',
            get_cmd='SWE:STEP?',
            set_cmd='SWE:STEP {:.12f} Hz',
            get_parser=float,
            vals=vals.Numbers(100e3, 20e9),
            instrument=self
        )

        self.sweep_points = Parameter(
            'sweep_points',
            label='Sweep: frequency points',
            unit='',
            get_cmd='SWE:POIN?',
            set_cmd='SWE:POIN {:.12f}',
            get_parser=int,
            vals=vals.Numbers(2, 20e9),
            instrument=self
        )

        self.sweep_dwell_time = Parameter(
            'sweep_dwell_time',
            label='Sweep: dwell time',
            unit='s',
            get_cmd='SWE:DWEL?',
            set_cmd='SWE:DWEL {:.12f} s',
            get_parser=float,
            vals=vals.Numbers(5e-3, 1000),
            instrument=self
        )

        self.sourcemode = Parameter(
            'sourcemode',
            label='Source mode',
            get_cmd='SOUR:FREQ:MODE?',
            set_cmd='SOUR:FREQ:MODE {}',
            val_mapping={
                'CW': 'CW',
                'sweep': 'SWE'},
            vals=vals.Enum('CW', 'SWE'),
            instrument=self
        )

        self.sweepmode = Parameter(
            'sweepmode',
            label='Frequency sweep mode',
            get_cmd='TRIG:FSW:SOUR?',
            set_cmd='TRIG:FSW:SOUR {}',
            val_mapping={
                'auto': 'AUTO',
                'single': 'SING'},
            vals=vals.Enum('AUTO', 'SING'),
            instrument=self
        )

        self.connect_message()

    def reset(self) -> None:
        self.log.info('Reset')
        self.write('*RST')

    def run_self_tests(self) -> None:
        self.log.info('Initiate self-test of the instrument.')
        self.write('*TST?')

    def on(self) -> None:
        self.log.info('Output on')
        self.status('on')

    def off(self) -> None:
        self.log.info('Output off')
        self.status('off')

    def start_sweep(self) -> None:
        self.log.info('Start sweep (generate manual trigger signal)')
        self.write('*TRG')
