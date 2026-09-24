# -*- coding: utf-8 -*-
"""Shared implementation for the Rohde & Schwarz SMB100A/SMB100B signal generators.

This class MUST NOT be instantiated directly. Use
:class:`.SMB100A.RohdeSchwarzSMB100A` or
:class:`.SMB100B.RohdeSchwarzSMB100B`.

Authors:
    Julien Barrier <julien@julienbarrier.eu>, 2023
    Thibault Wildi <thibault.wildi@qant.gmbh>, 2026
"""
import logging
from typing import TYPE_CHECKING

from qcodes.instrument import VisaInstrument, VisaInstrumentKWArgs
from qcodes.parameters import Parameter, create_on_off_val_mapping
from qcodes import validators as vals

if TYPE_CHECKING:
    from typing_extensions import Unpack

log = logging.getLogger(__name__)


class _RohdeSchwarzSMB100(VisaInstrument):
    """
    Base class for the Rohde & Schwartz SMB100A/SMB100B signal generators

    status: beta-version

    Args:
        name: name for the instrument
        address: Visa resource name to connect
    """

    default_terminator = '\n'

    model: str
    """Model this subclass drives, as reported by ``*IDN?``."""

    def __init__(self, name: str, address: str, **kwargs: 'Unpack[VisaInstrumentKWArgs]') -> None:
        super().__init__(name, address, **kwargs)

        idn_model = self.get_idn()['model']
        if idn_model != self.model:
            self.close()
            raise ValueError(
                f'Connected instrument reports model {idn_model!r}, but this driver targets the {self.model}.')

        freq_min, freq_max = self._query_limits('SOUR:FREQ')
        phase_min, phase_max = self._query_limits('SOUR:PHAS')
        step_min = self._query_limits('SWE:STEP')[0]
        points_min, points_max = self._query_limits('SWE:POIN')
        dwell_min, dwell_max = self._query_limits('SWE:DWEL')

        self.frequency = Parameter(
            'frequency',
            label='Frequency',
            unit='Hz',
            get_cmd='SOUR:FREQ?',
            set_cmd='SOUR:FREQ {:.2f}',
            get_parser=float,
            vals=vals.Numbers(freq_min, freq_max),
            instrument=self
        )

        self.phase = Parameter(
            'phase',
            label='Phase',
            unit='deg',
            get_cmd='SOUR:PHAS?',
            set_cmd='SOUR:PHAS {:.2f}',
            get_parser=float,
            vals=vals.Numbers(phase_min, phase_max),
            instrument=self
        )

        # The level limits depend on the frequency, so the instrument rather
        # than a validator rejects an out-of-range level.
        self.power = Parameter(
            'power',
            label='Power',
            unit='dBm',
            get_cmd='SOUR:POW?',
            set_cmd='SOUR:POW {:.2f}',
            get_parser=float,
            instrument=self
        )

        self.status = Parameter(
            'status',
            label='RF Output',
            get_cmd=':OUTP:STAT?',
            set_cmd=':OUTP:STAT {}',
            val_mapping=create_on_off_val_mapping(on_val='1', off_val='0'),
            instrument=self
        )

        self.pulsemod_state = Parameter(
            'pulsemod_state',
            label='Pulse Modulation',
            get_cmd=':SOUR:PULM:STAT?',
            set_cmd=':SOUR:PULM:STAT {}',
            val_mapping=create_on_off_val_mapping(on_val='1', off_val='0'),
            instrument=self
        )

        self.sweep_freq_start = Parameter(
            'sweep_freq_start',
            label='Sweep: start frequency',
            unit='Hz',
            get_cmd='FREQ:START?',
            set_cmd='FREQ:START {:.12f} Hz',
            get_parser=float,
            vals=vals.Numbers(freq_min, freq_max),
            instrument=self
        )

        self.sweep_freq_stop = Parameter(
            'sweep_freq_stop',
            label='Sweep: stop frequency',
            unit='Hz',
            get_cmd='FREQ:STOP?',
            set_cmd='FREQ:STOP {:.12f} Hz',
            get_parser=float,
            vals=vals.Numbers(freq_min, freq_max),
            instrument=self
        )

        self.sweep_step = Parameter(
            'sweep_step',
            label='Sweep: frequency step',
            unit='Hz',
            get_cmd='SWE:STEP?',
            set_cmd='SWE:STEP {:.12f} Hz',
            get_parser=float,
            vals=vals.Numbers(step_min, freq_max - freq_min),
            instrument=self
        )

        self.sweep_points = Parameter(
            'sweep_points',
            label='Sweep: frequency points',
            unit='',
            get_cmd='SWE:POIN?',
            set_cmd='SWE:POIN {:d}',
            get_parser=int,
            vals=vals.Ints(int(points_min), int(points_max)),
            instrument=self
        )

        self.sweep_dwell_time = Parameter(
            'sweep_dwell_time',
            label='Sweep: dwell time',
            unit='s',
            get_cmd='SWE:DWEL?',
            set_cmd='SWE:DWEL {:.12f} s',
            get_parser=float,
            vals=vals.Numbers(dwell_min, dwell_max),
            instrument=self
        )

        self.sourcemode = Parameter(
            'sourcemode',
            label='Source mode',
            get_cmd='SOUR:FREQ:MODE?',
            set_cmd='SOUR:FREQ:MODE {}',
            val_mapping={'CW': 'CW', 'sweep': 'SWE'},
            vals=vals.Enum('CW', 'SWE'),
            instrument=self
        )

        self.sweepmode = Parameter(
            'sweepmode',
            label='Frequency sweep mode',
            get_cmd='TRIG:FSW:SOUR?',
            set_cmd='TRIG:FSW:SOUR {}',
            val_mapping={'auto': 'AUTO', 'single': 'SING'},
            vals=vals.Enum('AUTO', 'SING'),
            instrument=self
        )

        self.connect_message()

    def _query_limits(self, cmd: str) -> tuple[float, float]:
        """Query the settable range of a command from the instrument.

        Uses the SCPI ``MINimum``/``MAXimum`` special numeric values. The
        bounds therefore reflect the options installed in the connected
        instrument.

        Args:
            cmd: SCPI command to query, without the trailing ``?``.

        Returns:
            The lowest and the highest settable value.
        """
        return (float(self.ask(f'{cmd}? MIN')), float(self.ask(f'{cmd}? MAX')))

    def reset(self) -> None:
        self.log.info('Reset')
        self.write('*RST')

    def run_self_tests(self, timeout: float = 60.) -> int:
        """Run the self-tests of the instrument.

        Args:
            timeout: VISA timeout in seconds to apply while the self-tests
                run. They outlast the default timeout of the instrument.

        Returns:
            The error code. Zero means that no error occurred. The service
            manual lists the other codes.
        """
        self.log.info('Initiate self-test of the instrument.')
        previous_timeout = self.timeout()
        self.timeout(timeout)
        try:
            return int(self.ask('*TST?'))
        finally:
            self.timeout(previous_timeout)

    def on(self) -> None:
        self.log.info('Output on')
        self.status('on')

    def off(self) -> None:
        self.log.info('Output off')
        self.status('off')

    def start_sweep(self) -> None:
        self.log.info('Start sweep (generate manual trigger signal)')
        self.write('*TRG')
