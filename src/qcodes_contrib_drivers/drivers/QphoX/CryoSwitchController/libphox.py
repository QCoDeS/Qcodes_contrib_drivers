import serial
import serial.tools.list_ports
import time
import json
import socket
import numpy as np
import subprocess
import os
import logging

class Labphox:
    _logger = logging.getLogger("libphox")

    def __init__(self, port=None, debug=False, IP=None, cmd_logging=False, SN=None, HW_val=False):
        self.debug = debug
        self.time_out = 5


        if self.debug or cmd_logging:
            self.log = True
            self.logging_dir = r'\logging'
            self.logger_init(self._logger)
        else:
            self.log = False

        self.SW_version = 3
        self.board_SN = SN
        self.board_FW = None

        self.adc_ref = 3.3
        self.N_channel = 0

        self.COM_port = None

        self.ETH_HOST = None  # The server's IP address
        self.ETH_PORT = 7  # The port used by the server
        self.ETH_buff_size = 1024

        self.communication_handler_sleep_time = 0
        self.packet_handler_sleep_time = 0
        if IP:
            self.USB_or_ETH = 2  # 1 for USB, 2 for ETH
            self.ETH_HOST = IP  # The server's IP address
            self.ETH_PORT = 7  # The port used by the server
            self.ETH_buff_size = 1024
        else:
            self.USB_or_ETH = 1  # 1 for USB, 2 for ETH
            self.COM_port = port

        self.connect(HW_val=HW_val)


    def connect(self, HW_val=True):
        if self.USB_or_ETH == 1:
            if self.COM_port:
                # TODO
                pass
            elif self.board_SN:
                for device in serial.tools.list_ports.comports():
                    if device.pid == 1812:
                        try:
                            self.serial_com = serial.Serial(device.device)
                            if self.board_SN == self.utility_cmd('sn'):
                                self.COM_port = device.device
                                self.PID = device.pid
                                self.serial_com.close()
                                break
                            self.serial_com.close()
                        except Exception as error:
                            pass
                            # print('Port' + str(device.device) + ' is already in use:', error)

            else:
                for device in serial.tools.list_ports.comports():
                    if device.pid == 1812:
                        self.PID = device.pid
                        self.COM_port = device.device
                        if self.debug:
                            for i in device:
                                print(i)

            try:
                self.serial_com = serial.Serial(self.COM_port)

                self.board_info = ''
                self.name = ''
                self.board_SN = None
                self.utility_cmd('info')
                print('Connected to ' + self.name + ' on COM port ' + self.COM_port + ', PID:',
                      str(self.PID) + ', SerialN: ' + str(self.board_SN) + ', Channels:' + str(self.N_channel))
                print(self.HW, ', FW_Ver.', self.board_FW)
            except:
                print('ERROR: Couldn\'t connect via serial')

        elif self.USB_or_ETH == 2:
            socket.setdefaulttimeout(self.time_out)

            self.board_info = ''
            self.name = ''
            self.board_SN = None
            self.utility_cmd('info')
            print('Connected to ' + self.name + ', IP:',
                  str(self.ETH_HOST) + ', SerialN: ' + str(self.board_SN) + ', Channels:' + str(self.N_channel))
            print(self.HW, ', FW_Ver.', self.board_FW)
        if not self.board_SN:
            raise Exception(
                "Couldn\'t connect, please check that the device is properly connected or try providing a valid SN, COM port or IP number")

        elif self.board_FW != self.SW_version and HW_val:
            print("Board Firmware version and Software version are not up to date, Board FW=" + str(
                self.board_FW) + " while SW=" + str(self.SW_version))

    def disconnect(self):
        if self.USB_or_ETH == 1:
            self.serial_com.close()
        elif self.USB_or_ETH == 2:
            pass

    def input_buffer(self):
        return self.serial_com.inWaiting()

    def flush_input_buffer(self):
        return self.serial_com.flushInput()

    def write(self, cmd):
        if self.log:
            pass
            #self.logging('actions', cmd)

        if self.USB_or_ETH == 1:
            self.serial_com.write(cmd)
        else:
            pass

    def read(self, size):
        if self.USB_or_ETH == 1:
            data_back = self.serial_com.read(size)
        else:
            data_back = ''

        return data_back

    def read_buffer(self):
        return self.read(self.input_buffer())

    def decode_buffer(self):
        return list(self.read_buffer())

    def debug_func(self, cmd, reply):
        print('Command', cmd)
        print('Reply', reply)
        print('')
        # self._logger.debug(f'Debug: {cmd}')
        self._logger.info(f'Debug: {cmd}')
        self._logger.debug(f'Command: {cmd}')
        self._logger.debug(f'Reply: {reply}')

    def logger_init(self, logger_instance, outfolder=None):
        logger_instance.setLevel(logging.DEBUG)

        if outfolder is None:
            outfolder = os.path.realpath('.') + self.logging_dir

        os.makedirs(name=outfolder, exist_ok=True)

        date_fmt = "%d/%m/%Y %H:%M:%S"

        # remove all old handlers
        for hdlr in logger_instance.handlers[:]:
            logger_instance.removeHandler(hdlr)

        # INFO level logger
        # file logger
        fmt = "[%(asctime)s] [%(levelname)s] %(message)s"
        log_format = logging.Formatter(fmt=fmt, datefmt=date_fmt)

        info_handler = logging.FileHandler(os.path.join(outfolder, 'info.log'))
        info_handler.setFormatter(log_format)
        info_handler.setLevel(logging.INFO)
        logger_instance.addHandler(info_handler)

        # DEBUG level logger
        fmt = "[%(asctime)s] [%(levelname)s] [%(funcName)s(): line %(lineno)s] %(message)s"
        log_format = logging.Formatter(fmt=fmt, datefmt=date_fmt)

        debug_handler = logging.FileHandler(os.path.join(outfolder, 'debug.log'))
        debug_handler.setFormatter(log_format)
        debug_handler.setLevel(logging.DEBUG)
        logger_instance.addHandler(debug_handler)

        # _logger = logging.getLogger("libphox")

        return logger_instance

    def read_line(self):
        if self.USB_or_ETH == 1:
            return self.serial_com.readline()
        else:
            return ''

    def query_line(self, cmd):
        self.write(cmd)
        if self.USB_or_ETH == 1:
            return self.serial_com.readline()
        else:
            return ''

    def compare_cmd(self, cmd1, cmd2):
        if cmd1.upper() == cmd2.upper():
            return True
        else:
            return False

    def encode(self, value):
        return str(value).encode()

    def decode_simple_response(self, response):
        return response.decode('UTF-8').strip()

    def parse_response(self):
        ##time.sleep(1)

        reply = ''

        initial_time = time.time()
        end = False
        while not end:
            time.sleep(self.communication_handler_sleep_time)
            if self.input_buffer():
                reply += self.read_buffer().decode()
            if ';' in reply:
                end = True

            elif (time.time() - initial_time) > self.time_out:
                raise Exception("LABPHOX time out exceeded", self.time_out, 's')

        reply = reply.split(';')[0]
        response = {'reply': reply, 'command': reply.split(':')[:-2], 'value': reply.split(':')[-1]}

        if self.log:
            self.logging('received', reply)

        return response

    def TCP_communication_handler(self, encoded_cmd=None):
        reply = ''
        with socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM) as TCP_connection:
            TCP_connection.connect((self.ETH_HOST, self.ETH_PORT))
            TCP_connection.sendall(encoded_cmd)
            packet = TCP_connection.recv(self.ETH_buff_size)

        try:
            reply += packet.decode()
        except:
            print('Invalid packet character', packet)

        reply = reply.split(';')[0]
        return reply

    def UDP_communication_handler(self, encoded_cmd=None):
        reply = ''
        with socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM) as UDP_connection:
            UDP_connection.sendto(encoded_cmd, (self.ETH_HOST, self.ETH_PORT))
            end = False
            while not end:
                # time.sleep(self.communication_handler_sleep_time)
                packet = UDP_connection.recvfrom(self.ETH_buff_size)[0]
                if b';' in packet:
                    reply += packet.split(b';')[0].decode()
                    end = True
                else:
                    try:
                        reply += packet.decode()
                    except:
                        print('Invalid packet character', packet)
                        break

            return reply

    def USB_communication_handler(self, encoded_cmd=None):
        reply = ''
        self.flush_input_buffer()
        self.write(encoded_cmd)

        initial_time = time.time()
        end = False
        while not end:
            time.sleep(self.communication_handler_sleep_time)
            if self.input_buffer():
                reply += self.read_buffer().decode()
            if ';' in reply:
                end = True

            elif (time.time() - initial_time) > self.time_out:
                raise Exception("LABPHOX time out exceeded", self.time_out, 's')

        reply = reply.split(';')[0]
        return reply

    def standard_reply_parser(self, cmd, reply):
        response = {'reply': reply, 'command': reply.split(':')[:-1], 'value': reply.split(':')[-1]}
        if not self.validate_reply(cmd, response):
            self.raise_value_mismatch(cmd, response)

        return response

    def communication_handler(self, cmd, standard=True, is_encoded=False):
        response = ''
        if is_encoded:
            encoded_cmd = cmd
        else:
            encoded_cmd = cmd.encode()

        if self.USB_or_ETH == 1:
            reply = self.USB_communication_handler(encoded_cmd)
        elif self.USB_or_ETH == 2:
            reply = self.UDP_communication_handler(encoded_cmd)
        elif self.USB_or_ETH == 3:
            reply = self.TCP_communication_handler(encoded_cmd)
        else:
            raise Exception("Invalid communication options USB_or_ETH=", self.USB_or_ETH)

        try:
            if standard:
                if is_encoded:
                    response = self.standard_reply_parser(cmd=cmd.decode(), reply=reply)
                else:
                    response = self.standard_reply_parser(cmd=cmd, reply=reply)
            else:
                response = reply
        except:
            print('Reply Error', reply)

        if self.debug:
            self.debug_func(cmd, response)

        return response

    def validate_reply(self, cmd, response):
        stripped = cmd.strip(';').split(':')
        command = stripped[:-1]
        value = stripped[-1]

        match = True
        if command != response['command']:
            match = False

        return match

    def USB_packet_handler(self, encoded_cmd, end_sequence):
        reply = b''
        self.flush_input_buffer()
        self.write(encoded_cmd)

        initial_time = time.time()
        end = False
        while not end:
            time.sleep(self.packet_handler_sleep_time)
            if self.input_buffer():
                reply += self.read_buffer()
            if end_sequence in reply[-5:]:
                end = True

            elif (time.time() - initial_time) > self.time_out:
                raise Exception("LABPHOX time out exceeded", self.time_out, 's')

        reply = reply.replace(end_sequence, b'').replace(encoded_cmd, b'')
        return reply

    def UDP_packet_handler(self, encoded_cmd, end_sequence):
        reply = b''
        with socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM) as s:
            s.sendto(encoded_cmd, (self.ETH_HOST, self.ETH_PORT))
            end = False
            while not end:
                time.sleep(self.packet_handler_sleep_time)
                packet = s.recvfrom(self.ETH_buff_size)[0]
                reply += packet
                if end_sequence in reply[-5:]:
                    end = True

        reply = reply.replace(end_sequence, b'').replace(encoded_cmd, b'')
        return reply[7:]

    def packet_handler(self, cmd, end_sequence=b'\x00\xff\x00\xff'):
        encoded_cmd = cmd.encode()

        if self.USB_or_ETH == 1:
            reply = self.USB_packet_handler(encoded_cmd, end_sequence)
            return reply

        elif self.USB_or_ETH == 2:
            reply = self.UDP_packet_handler(encoded_cmd, end_sequence)
            return reply

    def raise_value_mismatch(self, cmd, response):
        print('Command mismatch!')
        print('Command:', cmd)
        print('Reply:', response['command'])

    def utility_cmd(self, cmd, value=0):
        response = False
        if self.compare_cmd(cmd, 'info'):
            self.name = self.utility_cmd('name').upper()
            if 'LabP'.upper() in self.name:
                self.HW = self.utility_cmd('hw')
                self.board_SN = self.utility_cmd('sn')
                self.board_FW = int(self.utility_cmd('fw').split('.')[-1])
                self.N_channel = int(self.utility_cmd('channels').split()[1])

        elif self.compare_cmd(cmd, 'name'):
            response = self.communication_handler('W:2:A:;', standard=False)

        elif self.compare_cmd(cmd, 'fw'):
            response = self.communication_handler('W:2:B:;', standard=False)

        elif self.compare_cmd(cmd, 'hw'):
            response = self.communication_handler('W:2:D:;', standard=False)

        elif self.compare_cmd(cmd, 'sn'):
            response = self.communication_handler('W:2:E:;', standard=False)

        elif self.compare_cmd(cmd, 'channels'):
            response = self.communication_handler('W:2:F:;', standard=False)

        elif self.compare_cmd(cmd, 'connected'):
            response = self.communication_handler('W:2:C:;')
            return response['value']

        elif self.compare_cmd(cmd, 'UID'):
            response = self.communication_handler('W:2:G:' + str(value) + ';')
            return response['value']

        elif self.compare_cmd(cmd, 'sleep'):
            response = self.communication_handler('W:2:S:' + str(value) + ';')

        return response

    def DAC_cmd(self, cmd, DAC=1, value=0):
        response = None
        if DAC == 1:
            sel_DAC = 5
        elif DAC == 2:
            sel_DAC = 8
        else:
            return None

        if self.compare_cmd(cmd, 'on'):
            response = self.communication_handler('W:' + str(sel_DAC) + ':T:1;')

        elif self.compare_cmd(cmd, 'off'):
            response = self.communication_handler('W:' + str(sel_DAC) + ':T:0;')

        elif self.compare_cmd(cmd, 'set'):
            response = self.communication_handler('W:' + str(sel_DAC) + ':S:' + str(value) + ';')

        elif self.compare_cmd(cmd, 'buffer'):
            response = self.communication_handler('W:' + str(sel_DAC) + ':B:' + str(value) + ';')

        return response

    def application_cmd(self, cmd, value=0):
        response = False
        if self.compare_cmd(cmd, 'pulse'):
            ##self.serial_com.flushInput()
            ##response = self.communication_handler('W:3:T:' + str(value) + ';', standard=False)
            response = self.packet_handler('W:3:T:' + str(value) + ';')
            return np.fromstring(response, dtype=np.uint8)

        elif self.compare_cmd(cmd, 'acquire'):
            response = self.communication_handler('W:3:Q:' + str(value) + ';')

        elif self.compare_cmd(cmd, 'voltage'):
            response = self.communication_handler('W:3:V:' + str(value) + ';')

        elif self.compare_cmd(cmd, 'test_circuit'):
            response = self.communication_handler('W:3:P:' + str(value) + ';')

        return response

    def timer_cmd(self, cmd, value=0):
        response = False
        if self.compare_cmd(cmd, 'duration'):
            response = self.communication_handler('W:0:A:' + str(value) + ';')
            if int(response['value']) != int(value):
                self.raise_value_mismatch(cmd, response)

        if self.compare_cmd(cmd, 'sampling'):
            response = self.communication_handler('W:0:S:' + str(value) + ';')

        return response

    def ADC_cmd(self, cmd, value=0):
        response = None
        if self.compare_cmd(cmd, 'channel'):
            response = self.communication_handler('W:4:C:' + str(value) + ';')

        elif self.compare_cmd(cmd, 'start'):
            response = self.communication_handler('W:4:T:1;')

        elif self.compare_cmd(cmd, 'stop'):
            response = self.communication_handler('W:4:T:0;')

        elif self.compare_cmd(cmd, 'select'):  ##Select and sample
            response = self.communication_handler('W:4:S:' + str(value) + ';')


        elif self.compare_cmd(cmd, 'get'):
            response = self.communication_handler('W:4:G:;')
            return int(response['value'])

        elif self.compare_cmd(cmd, 'interrupt'):  ##Enable interrupt mode
            response = self.communication_handler('W:4:I:' + str(value) + ';')

        elif self.compare_cmd(cmd, 'buffer'):  ##Enable interrupt mode
            response = self.communication_handler('W:4:B:' + str(value) + ';')
            return int(response['value'])

        return response


    def ADC3_cmd(self, cmd, value=0):
        response = None
        if self.compare_cmd(cmd, 'channel'):
            response = self.communication_handler('W:W:C:' + str(value) + ';')

        elif self.compare_cmd(cmd, 'start'):
            response = self.communication_handler('W:W:T:1;')

        elif self.compare_cmd(cmd, 'stop'):
            response = self.communication_handler('W:W:T:0;')

        elif self.compare_cmd(cmd, 'select'):  ##Select and sample
            response = self.communication_handler('W:W:S:' + str(value) + ';')

        elif self.compare_cmd(cmd, 'get'):
            response = self.communication_handler('W:W:G:;')
            return int(response['value'])

        return response

    def gpio_cmd(self, cmd, value=0):
        response = None
        if self.compare_cmd(cmd, 'EN_3V3'):
            response = self.communication_handler('W:1:A:' + str(value) + ';')

        elif self.compare_cmd(cmd, 'EN_5V'):
            response = self.communication_handler('W:1:B:' + str(value) + ';')

        elif self.compare_cmd(cmd, 'EN_CHGP'):
            response = self.communication_handler('W:1:C:' + str(value) + ';')

        elif self.compare_cmd(cmd, 'FORCE_PWR_EN'):
            response = self.communication_handler('W:1:D:' + str(value) + ';')

        elif self.compare_cmd(cmd, 'PWR_EN'):
            response = self.communication_handler('W:1:E:' + str(value) + ';')

        elif self.compare_cmd(cmd, 'DCDC_EN'):
            response = self.communication_handler('W:1:F:' + str(value) + ';')

        elif self.compare_cmd(cmd, 'CHOPPING_EN'):
            response = self.communication_handler('W:1:G:' + str(value) + ';')

        elif self.compare_cmd(cmd, 'PWR_STATUS'):
            response = self.communication_handler('W:1:H:0;')
            return int(response['value'])

        elif self.compare_cmd(cmd, 'OCP_OUT_STATUS'):
            response = self.communication_handler('W:1:I:0;')
            return int(response['value'])

        return response

    def IO_expander_cmd(self, cmd, port='A', value=0):
        response = None
        if self.compare_cmd(cmd, 'connect'):
            response = self.communication_handler('W:' + str(port) + ':C:' + str(value) + ';')

        elif self.compare_cmd(cmd, 'disconnect'):
            response = self.communication_handler('W:' + str(port) + ':D:' + str(value) + ';')

        elif self.compare_cmd(cmd, 'on'):
            response = self.communication_handler('W:6:O:' + str(value) + ';')

        elif self.compare_cmd(cmd, 'off'):
            response = self.communication_handler('W:6:U:' + str(value) + ';')

        elif self.compare_cmd(cmd, 'type'):
            response = self.communication_handler('W:6:S:' + str(value) + ';')

        return response

    def reset_cmd(self, cmd):
        response = None
        if self.compare_cmd(cmd, 'reset'):
            response = self.communication_handler('W:7:R:;')

        elif self.compare_cmd(cmd, 'boot'):
            response = self.communication_handler('W:7:B:;')

        elif self.compare_cmd(cmd, 'soft_reset'):
            response = self.communication_handler('W:7:S:;')

        return response

    def logging(self, list_name, cmd):
        with open('history.json', "r") as history_file:
            data = json.load(history_file)

        if type(cmd) == str:
            data_to_append = cmd
        elif type(cmd) == bytes:
            data_to_append = cmd.decode()

        if list_name in data.keys():
            data[list_name].append({'data': data_to_append, 'date': time.time()})
        else:
            data[list_name] = [{'data': data_to_append, 'date': time.time()}]

        with open('history.json', "w") as file:
            json.dump(data, file)

    def ETHERNET_cmd(self, cmd, value=0):
        response = None
        if self.compare_cmd(cmd, 'read'):
            response = self.communication_handler('W:Q:R:' + str(value) + ';')
        elif self.compare_cmd(cmd, 'set_ip'):
            response = self.communication_handler('W:Q:I:' + str(value) + ';')
        elif self.compare_cmd(cmd, 'get_ip'):
            response = self.communication_handler('W:Q:G:' + str(value) + ';')

        elif self.compare_cmd(cmd, 'set_ip_str'):
            int_IP = int.from_bytes(socket.inet_aton(value), "little")
            response = self.communication_handler('W:Q:I:' + str(int_IP) + ';')
        elif self.compare_cmd(cmd, 'get_ip_str'):
            response = self.communication_handler('W:Q:G:' + str(value) + ';')
            IP = socket.inet_ntoa(int(response['value']).to_bytes(4, 'little'))
            print('IP:', IP)
            return IP

        elif self.compare_cmd(cmd, 'set_mask_str'):
            int_mask = int.from_bytes(socket.inet_aton(value), "little")
            response = self.communication_handler('W:Q:K:' + str(int_mask) + ';')

        elif self.compare_cmd(cmd, 'get_mask_str'):
            response = self.communication_handler('W:Q:L:' + str(value) + ';')
            print(response)
            mask = socket.inet_ntoa(int(response['value']).to_bytes(4, 'little'))
            print('Subnet mask:', mask)
            return mask

        elif self.compare_cmd(cmd, 'get_detection'):
            response = self.communication_handler('W:Q:D:;')

        return response

    def UPGRADE_cmd(self, cmd, value):
        response = None

        if self.compare_cmd(cmd, 'upgrade'):
            response = self.communication_handler('U:A:0' + ':' + str(value) + ';')
            if int(response['value']) == value:
                print('Update successful,', value, 'channels enabled')
            else:
                print('Couldn\'t update channel number')

        elif self.compare_cmd(cmd, 'stream_key'):
            for idx, element in enumerate(value):
                response = self.communication_handler('U:B:' + str(chr(65 + idx)) + ':' + str(element) + ';')
                if int(response['value']) != element:
                    print('Error while sending key!')

        return response

    def FLASH_utils(self, path=None):
        DFU_name = '0483:df11'
        found = False
        process = subprocess.Popen(['.\Firmware\dfu-util', '-l'], shell=True,
                                   stdout=subprocess.PIPE,
                                   universal_newlines=True)

        start_time = time.time()
        exc_time = 0
        output = ''
        while exc_time < self.time_out:
            output = process.stdout.readline()
            if 'Internal Flash' in output and 'Found DFU: [' + DFU_name + ']' in output:
                found = True
                break
            exc_time = time.time() - start_time

        if not found:
            print('Couldn\'t find the the device')
        else:
            print('Device found in', output.strip().strip('Found DFU: '))

            if not path:
                path = '.'
            process = subprocess.Popen('.\Firmware\dfu-util -d ' + DFU_name + ' -a 0 -s 0x08000000:leave -D ' + path + '\Firmware\Labphox.bin', shell=True,
                                       stdout=subprocess.PIPE,
                                       universal_newlines=True)

            start_time = time.time()
            exc_time = 0
            poll = process.poll()
            while poll is None:
                output = process.stdout.readline()
                if 'Download' in output or 'device'.upper() in output.upper() or 'dfu'.upper() in output.upper() and 'bugs' not in output:
                    print(output.strip())
                exc_time = time.time() - start_time

                if exc_time > self.time_out:
                    break
                else:
                    poll = process.poll()

            print('Flashing time', round(exc_time, 2), 's')
            print('Flash ended! Please disconnect the device.')


if __name__ == "__main__":
    labphox = Labphox(debug=True, IP='192.168.1.101')

