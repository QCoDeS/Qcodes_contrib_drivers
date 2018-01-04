import socket
import json
import threading
import time
import random

from qcodes.instrument.ip import IPInstrument


class Solstis3(IPInstrument):
    def __init__(self, name, address=None, port=None, timeout=5, controller_address=None,
                  persistent=True, write_confirmation=True, testing=False,**kwargs):

        super().__init__(name, address=address, port=port, timeout=timeout,
                         persistent=False, write_confirmation=write_confirmation, terminator='', **kwargs)

        self._controller_address = controller_address

        self.set_persistent(persistent)

        #self.add_parameter('wavelenngth',
                           #set_cmd)

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

    def _set_wavelength(self,wavelength):
        parameters = {'wavelength':[wavelength]}
        self.send_message('set_wave_m',parameters)

    def _get_wavelength(self):
        status = self._get_status()
        return status['wavelength'][0]

    def _get_status(self):
        return self.send_message('get_status')

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

