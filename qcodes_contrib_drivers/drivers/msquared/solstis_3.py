import socket
import json
import threading
import time
import random

from qcodes.instrument.ip import IPInstrument
from qcodes.utils.validators import Numbers, Ints, Enum, MultiType, Anything, Strings


class Solstis3(IPInstrument):
    def __init__(self, name, address=None, port=None, timeout=5, controller_address=None,
                  persistent=True, write_confirmation=True, testing=False,**kwargs):

        super().__init__(name, address=address, port=port, timeout=timeout,
                         persistent=False, write_confirmation=write_confirmation, terminator='', **kwargs)

        self._controller_address = controller_address

        self.set_persistent(persistent)

        self.add_parameter('wavelength_m',
                           get_cmd = self._get_wavelength,
                           set_cmd = self._set_wave_m,
                           label = 'Wavelength',
                           unit = 'nm',
                           vals = Numbers(min_value = 700, max_value = 1000),
                           docstring = 'wavelength locked')

        self.add_parameter('wavelength_t',
                           get_cmd = self._get_wavelength,
                           set_cmd = self._move_wave_t,
                           label= 'Wavelength',
                           unit = 'nm',
                           vals = Numbers(min_value = 700, max_value = 1000),
                           docstring = 'wavelength not locked')

        self.add_parameter('lock',
                           get_cmd = self._is_wave_locked_m,
                           set_cmd = self._lock_wave_m,
                           vals = Enum(True,False))

    @staticmethod
    def _generate_transmission_id():
        return random.randint(1, 2 ** 14)

    def _connect(self):
        if self._controller_address is None:
            raise RuntimeError('No Controller address')

        super()._connect()
        answer = self.send_message('start_link', {'ip_address': self._controller_address})

        if answer['status'] != 'ok':
            super()._disconnect()
            raise RuntimeError('Connection to Solstis failed', answer)
        else:
            print('Connection to Solstis successful')

    ########## tuning WITHOUT solstis ##########
    def _move_wave_t(self,wavelength):
        parameters = {'wavelength':[wavelength]}
        self.send_message('move_wave_t',parameters)

    def poll_move_wave_t(self):
        current_status = self.send_message('poll_move_wave_t')
        inProgress = False
        if current_status['status'][0] == 1:
            inProgress = True
        current_wavelength = current_status['current_wavelength'][0]
        return inProgress, current_wavelength

    def stop_move_wave_t(self):
        self.send_message('stop_move_wave_t')
        time.sleep(0.5) #delay between stop cmd sent and effective stop -> read final wavelength
        return self._get_wavelength()

    ########## tuning WITH solstis ##########
    def _set_wave_m(self, wavelength):
        parameters = {'wavelength':[wavelength]}
        self.send_message('set_wave_m',parameters)

    def poll_wave_m(self):
        current_status = self.send_message('poll_wave_m')
        inProgress = False
        if current_status['status'][0] == 1:
            inProgress = True
        current_wavelength = current_status['current_wavelength'][0]
        lock_status = current_status['lock_status'][0]
        return inProgress, current_wavelength, lock_status

    def stop_wave_m(self):
        stop_status = self.send_message('stop_wave_m')
        return stop_status['current_wavelength'][0]

    def _lock_wave_m(self,will_be_locked):
        if will_be_locked:
            parameters = {'operation':'on'}
        else:
            parameters = {'operation':'off'}
        locking_status = self.send_message('lock_wave_m',parameters)

    def _is_wave_locked_m(self):
        onProgress, current_wavelength, lock_status = self.poll_wave_m()
        return lock_status

    ######### read STATUS #########
    def _get_wavelength(self):
        status = self.get_status()
        return status['wavelength'][0]

    def get_status(self):
        return self.send_message('get_status')

    ######### ASK command #########
    def send_message(self, op, parameters=None, verbose=False):
        transmission_id = self._generate_transmission_id()

        query = {'message':
                     {'transmission_id': [transmission_id],
                      'op': op}}
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

    def snapshot_base(self, update=False):
        snapshot = super().snapshot_base(update)

        snapshot['controller_address'] = self._controller_address

        return snapshot

