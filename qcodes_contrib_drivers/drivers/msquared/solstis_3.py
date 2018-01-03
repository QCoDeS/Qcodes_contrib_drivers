import socket
import json
import threading
import time
import random

from qcodes.instrument.ip import IPInstrument


class Solstis3(IPInstrument):
    def __init__(self, name, address=None, port=None, timeout=5, controller_address=None,
                  persistent=True, write_confirmation=True, testing=False,
                 **kwargs):
        super().__init__(name, address=address, port=port, timeout=timeout,
                         persistent=False, write_confirmation=write_confirmation, testing=testing, terminator='', **kwargs)

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
            raise RuntimeError('Connection failed', answer)


    def send_message(self, op, parameters=None):
        transmission_id = self._generate_transmission_id()

        query = {'message':
                     {'transmission_id': [transmission_id],
                      'op': op}}
        if parameters:
            query['message']['parameters'] = parameters

        query_string = json.dumps(query, separators=(',', ':'))
        print('query:', query_string)
        answer_string = self.ask_raw(query_string)
        print('answer:', answer_string)
        answer = json.loads(answer_string)

        if answer['message']['transmission_id'] != [transmission_id]:
            raise RuntimeError('Invalid transmission ID', answer)

        return answer['message']['parameters']

    def snapshot_base(self, update=False):
        snapshot = super().snapshot_base(update)

        snapshot['controller_address'] = self._controller_address

        return snapshot

