from __future__ import annotations

import json
import random
import time
from typing import Any, Sequence

from qcodes.instrument.ip import IPInstrument
from qcodes.parameters import create_on_off_val_mapping
from qcodes.utils.validators import Numbers


class M2Solstis3(IPInstrument):
    """Driver for the M² Solstis laser.

    Args:
        name: The name of the instrument.
        address: The IP address of the Laser.
        port: The Port number of the Laser.
        controller_address: The IP address of the laser controller (PC).

    """
    _sleep_interval: float = 0.2
    """Amount of time slept before querying for the status after a wavelength 
    move. If 0, the status will often not be updated yet and the blocking 
    mechanism will fail."""

    def __init__(self, name: str, address: str, port: int,
                 controller_address: str, timeout: float = 5,
                 terminator: str = "", persistent: bool = True,
                 write_confirmation: bool = True, **kwargs: Any):

        self._controller_address = controller_address

        super().__init__(name, address, port, timeout, terminator, persistent,
                         write_confirmation, **kwargs)

        self.add_parameter('wavelength_m',
                           get_cmd=self._get_wavelength,
                           set_cmd=self._set_wave_m,
                           label='Wavelength locked',
                           unit='nm',
                           set_parser=float,
                           vals=Numbers(min_value=700, max_value=1000),
                           docstring='wavelength locked')

        self.add_parameter('wavelength_t',
                           get_cmd=self._get_wavelength,
                           set_cmd=self._move_wave_t,
                           label='Wavelength table',
                           unit='nm',
                           set_parser=float,
                           vals=Numbers(min_value=700, max_value=1000),
                           docstring='wavelength not locked')

        self.add_parameter('lock',
                           get_cmd=self._is_wave_locked_m,
                           set_cmd=self._lock_wave_m,
                           val_mapping=create_on_off_val_mapping())

        self.add_parameter('tuning_m',
                           get_cmd=lambda: self.poll_wave_m()[0],
                           val_mapping={'tuning software not active': 0,
                                        'no link to wavelength meter': 1,
                                        'tuning in progress': 2,
                                        'wavelength lock being maintained': 3},
                           docstring='Wavelength locked tuning status.')

        self.add_parameter('tuning_t',
                           get_cmd=lambda: self.poll_move_wave_t()[0],
                           val_mapping={'tuning completed': 0,
                                        'tuning in progress': 1,
                                        'tuning failed': 2},
                           docstring='Wavelength table tuning in progress.')

        self.connect_message()

    @staticmethod
    def _generate_transmission_id():
        return random.randint(1, 2 ** 14)

    def _connect(self):
        super()._connect()
        answer = self.send_message('start_link',
                                   {'ip_address': self._controller_address})

        if answer['status'] != 'ok':
            super()._disconnect()
            raise RuntimeError('Connection to controller failed', answer)

    ########## tuning WITHOUT solstis ##########
    def _move_wave_t(self, wavelength):
        parameters = {'wavelength': [wavelength]}
        self.send_message('move_wave_t', parameters)
        time.sleep(self._sleep_interval)
        while self.tuning_t() == 'tuning in progress':
            pass

        if self.tuning_t.get_latest() == 'tuning completed':
            self.log.info(f'Completed move_wave_t to {wavelength}.')
        elif self.tuning_t.get_latest() == 'tuning failed':
            self.log.error(f'Failed move_wave_t to {wavelength}.')

    def poll_move_wave_t(self):
        current_status = self.send_message('poll_move_wave_t')
        status = current_status['status'][0]
        current_wavelength = current_status['current_wavelength'][0]
        return status, current_wavelength

    def stop_move_wave_t(self):
        self.send_message('stop_move_wave_t')
        # delay between stop cmd sent and effective stop -> read final
        # wavelength
        time.sleep(0.5)
        return self._get_wavelength()

    ########## tuning WITH solstis ##########
    def _set_wave_m(self, wavelength):
        parameters = {'wavelength': [wavelength]}
        self.send_message('set_wave_m', parameters)
        time.sleep(self._sleep_interval)
        while self.tuning_m() == 'tuning in progress':
            pass

        if self.tuning_m.get_latest() == 'wavelength lock being maintained':
            self.log.info(f'Completed set_wave_m to {wavelength}.')
        else:
            self.log.error(f'Failed move_wave_t to {wavelength}: '
                           f'{self.tuning_m.get_latest()}.')

    def poll_wave_m(self):
        current_status = self.send_message('poll_wave_m')
        status = current_status['status'][0]
        current_wavelength = current_status['current_wavelength'][0]
        lock_status = current_status['lock_status'][0]
        return status, current_wavelength, lock_status

    def stop_wave_m(self):
        stop_status = self.send_message('stop_wave_m')
        return stop_status['current_wavelength'][0]

    def _lock_wave_m(self, will_be_locked):
        if will_be_locked:
            parameters = {'operation': 'on'}
        else:
            parameters = {'operation': 'off'}
        locking_status = self.send_message('lock_wave_m', parameters)

    def _is_wave_locked_m(self):
        status, current_wavelength, lock_status = self.poll_wave_m()
        return lock_status

    ######### read STATUS #########
    def _get_wavelength(self):
        status = self.get_status()
        return status['wavelength'][0]

    def get_status(self):
        return self.send_message('get_status')

    def get_idn(self) -> dict[str, str | None]:
        return {'vendor': 'M²',
                'model': 'Solstis 3',
                'serial': None,
                'firmware': None}

    ######### ASK command #########
    def send_message(self, op, parameters=None, verbose=False):
        transmission_id = self._generate_transmission_id()

        query = {'message': {'transmission_id': [transmission_id], 'op': op}}
        if parameters:
            query['message']['parameters'] = parameters

        query_string = json.dumps(query, separators=(',', ':'))
        if verbose:
            print('query:', query_string)
        answer_string = self.ask_raw(query_string)
        if verbose:
            print('answer:', answer_string)
        answer = json.loads(answer_string)

        if answer['message']['transmission_id'] != [transmission_id]:
            raise RuntimeError('Invalid transmission ID', answer)

        return answer['message']['parameters']

    def snapshot_base(
            self, update: bool | None = False,
            params_to_skip_update: Sequence[str] | None = None
    ) -> dict[Any, Any]:
        snapshot = super().snapshot_base(update, params_to_skip_update)
        snapshot['controller_address'] = self._controller_address
        if update and 'status' not in (params_to_skip_update or []):
            snapshot['status'] = self.get_status()
        return snapshot
