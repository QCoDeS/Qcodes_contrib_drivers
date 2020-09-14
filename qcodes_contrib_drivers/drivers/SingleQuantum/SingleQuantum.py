"""
The MIT License (MIT)

Copyright (c) 2020 Single Quantum B. V.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import numpy as np
import socket
import json
import threading
import time
import sys

from qcodes.instrument.ip import Instrument
from qcodes.instrument.base import Parameter
from qcodes.instrument.parameter import ParameterWithSetpoints, MultiParameter
from qcodes.utils.validators import Arrays


class SQTalk(threading.Thread):
    def __init__(self, TCP_IP_ADR='localhost', TCP_IP_PORT=12000,
                 error_callback=None):
        threading.Thread.__init__(self)
        self.TCP_IP_ADR = TCP_IP_ADR
        self.TCP_IP_PORT = TCP_IP_PORT

        self.socket = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.TCP_IP_ADR, self.TCP_IP_PORT))
        self.socket.settimeout(.1)
        self.BUFFER = 10000000
        self.shutdown = False
        self.labelProps = dict()

        self.error_callback = error_callback

        self.lock = threading.Lock()

    def close(self):
        # Print("Closing Socket")
        self.socket.close()
        self.shutdown = True

    def send(self, msg):
        self.socket.send(bytes(msg, "utf-8"))

    def sub_jsons(self, msg):
        """Return sub json strings.
        {}{} will be returned as [{},{}]
        """
        i = 0
        result = []
        split_msg = msg.split('}{')
        for s in range(len(split_msg)):
            if i == 0 and len(split_msg) == 1:
                result.append(split_msg[s])
            elif i == 0 and len(split_msg) > 1:
                result.append(split_msg[s] + "}")
            elif i == len(split_msg) - 1 and len(split_msg) > 1:
                result.append("{" + split_msg[s])
            else:
                result.append("{" + split_msg[s] + "}")
            i += 1
        return result

    def add_labelProps(self, data):
        if "label" in data.keys():
            # After get labelProps, queries also bounds, units etc...
            if isinstance(data["value"], (dict)):
                self.labelProps[data["label"]] = data["value"]
            # General label communication, for example from broadcasts
            else:
                try:
                    self.labelProps[data["label"]
                                    ]["value"] = data["value"]
                except Exception:
                    None

    def check_error(self, data):
        if "label" in data.keys():
            if "Error" in data["label"]:
                self.error_callback(data["value"])

    def get_label(self, label):
        timeout = 10
        dt = .1
        i = 0
        while True:
            if i * dt > timeout:
                raise IOError("Could not acquire label")
            try:
                return self.labelProps[label]
            except Exception:
                self.send(json.dumps(
                    {"request": "labelProps", "value": "None"}))
                time.sleep(dt)
            i += 1

    def get_all_labels(self, label):
        return self.labelProps

    def run(self):
        self.send(json.dumps(
            {"request": "labelProps", "value": "None"}))
        rcv_msg = []

        while self.shutdown is False:
            try:
                rcv = "" + rcv_msg[1]
            except Exception:
                rcv = ""
            data = {}
            r = ""
            while "\x17" not in rcv:
                try:
                    r = str(self.socket.recv(self.BUFFER), 'utf-8')
                except Exception:
                    None
                rcv = rcv + r

            rcv_msg = rcv.split("\x17")

            for rcv_line in rcv_msg:
                rcv_split = self.sub_jsons(rcv_line)
                for msg in rcv_split:
                    try:
                        data = json.loads(msg)
                    except Exception:
                        None

                    with self.lock:
                        self.add_labelProps(data)
                        self.check_error(data)


class SQCounts(threading.Thread):
    def __init__(
            self,
            TCP_IP_ADR='localhost',
            TCP_IP_PORT=12345,
            CNTS_BUFFER=100):
        threading.Thread.__init__(self)
        self.lock = threading.Lock()
        self.rlock = threading.RLock()
        self.TCP_IP_ADR = TCP_IP_ADR
        self.TCP_IP_PORT = TCP_IP_PORT

        self.socket = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.TCP_IP_ADR, self.TCP_IP_PORT))
        # self.socket.settimeout(.1)
        self.BUFFER = 1000000
        self.shutdown = False

        self.cnts = []
        self.CNTS_BUFFER = CNTS_BUFFER
        self.n = 0

    def close(self):
        # print("Closing Socket")
        self.socket.close()
        self.shutdown = True

    def get_n(self, n):
        n0 = self.n
        while self.n < n0 + n:
            time.sleep(0.001)
        cnts = self.cnts
        return cnts[-n:]

    def run(self):
        while self.shutdown is False:
            data_raw = str(self.socket.recv(self.BUFFER), 'utf-8')

            data_newline = data_raw.split('\n')

            v = []
            for d in data_newline[0].split(','):
                v.append(float(d))

            with self.lock:
                self.cnts.append(v)
                # Keep Size of self.cnts
                len_ = len(self.cnts)
                if len_ > self.CNTS_BUFFER:
                    self.cnts = self.cnts[len_ - self.CNTS_BUFFER:]
                self.n += 1


class ChannelArray(ParameterWithSetpoints):
    """Fetches the correct row from the matrix counters,  based on the channel
    This is a parameter with setpoints, where the setpoints are the time stamps
    Args:
        channel (int): the channel number to select the row from the counters matrix
    Return (numpy_array): a numpy vector of length npts, containing the counts
    """

    def __init__(self, channel, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._channel = channel

    def get_raw(self):
        return self.root_instrument.counters.get_latest()[
            self._channel]


class TimeArray(Parameter):
    """Fetches the row with time stamps, currently channel 0
    This parameter is used as the setpoints for the channelarray
    Args:
        channel (int): the channel number to select the row from the counters matrix (channel 0 is the timestamp)
    Return (numpy_array): a numpy vector of length npts, containing the time stamps
    """

    def __init__(self, channel, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._channel = channel

    def get_raw(self):
        return np.array(self.root_instrument.counters.get_latest()[
            self._channel])


class CommunicationHandler(object):
    """Handles the communication, creates JSON strings"""

    def __init__(
            self,
            root_instrument,
            log,
            TCP_IP_ADR='localhost',
            CONTROL_PORT=12000,
            COUNTS_PORT=12345):
        self.root_instrument = root_instrument
        self.log = log
        self.TCP_IP_ADR = TCP_IP_ADR
        self.CONTROL_PORT = CONTROL_PORT
        self.COUNTS_PORT = COUNTS_PORT
        self.NUMBER_OF_DETECTORS = 0

        self.talk = SQTalk(
            TCP_IP_ADR=self.TCP_IP_ADR,
            TCP_IP_PORT=self.CONTROL_PORT,
            error_callback=self.error)
        # Daemonic Thread close when main progam is closed
        self.talk.daemon = True
        self.talk.start()

        self.cnts = SQCounts(TCP_IP_ADR=self.TCP_IP_ADR,
                             TCP_IP_PORT=self.COUNTS_PORT)
        # Daemonic Thread close when main progam is closed
        self.cnts.daemon = True
        self.cnts.start()

        self.NUMBER_OF_DETECTORS = self.talk.get_label(
            "NumberOfDetectors")["value"]

    def acquire_cnts_t(self):
        """Acquire n count measurments transposed.
        Return (numpy_array): Acquired counts with timestamp in first row.
        """
        n = self.root_instrument.npts()
        cnts = self.cnts.get_n(n)
        return np.array(cnts).T

    def set_measurement_periode(self, t_in_ms):
        msg = json.dumps(
            dict(
                command="SetMeasurementPeriod",
                label="InptMeasurementPeriod",
                value=t_in_ms))
        self.talk.send(msg)

    def get_number_of_detectors(self):
        return self.talk.get_label("NumberOfDetectors")["value"]

    def get_measurement_periode(self):
        """Get measurment periode in ms.
        Return (float): time
        """
        return self.talk.get_label("InptMeasurementPeriod")["value"]

    def get_bias_current(self):
        return self.talk.get_label("BiasCurrent")["value"]

    def get_trigger_level(self):
        return self.talk.get_label("TriggerLevel")["value"]

    def get_bias_voltage(self):
        msg = json.dumps(dict(request="BiasVoltage"))
        self.talk.send(msg)
        return self.talk.get_label("BiasVoltage")["value"]

    def set_bias_current(self, current_in_uA):
        array = current_in_uA
        msg = json.dumps(dict(command="SetAllBiasCurrents",
                              label="BiasCurrent", value=array))
        self.talk.send(msg)

    def set_trigger_level(self, trigger_level_mV):
        array = trigger_level_mV
        msg = json.dumps(dict(command="SetAllTriggerLevels",
                              label="TriggerLevel", value=array))
        self.talk.send(msg)

    def enable_detectors(self, state=True):
        msg = json.dumps(dict(command="DetectorEnable",
                              label="DetectorEnable", value=state))
        self.talk.send(msg)

    def set_dark_counts_auto_iv(self, dark_counts):
        """Set the dark counts for the automatic detector calibration.
        After this command execute: self.auto_cali_bias_currents()
        """
        if self.NUMBER_OF_DETECTORS != len(dark_counts):
            raise ValueError(
                'Dark counts not the same lenght as number of detectors')
        else:
            msg = json.dumps(
                dict(
                    command="DarkCountsAutoIV",
                    label="DarkCountsAutoIV",
                    value=dark_counts))
            self.talk.send(msg)

    def auto_cali_bias_currents(self):
        """Performs the automatic bias calibration. Make sure that no light reaches the detectors during this procedure.
        To check if this function has finished use self.auto_cali_finished() which return true or false.
        """
        msg = json.dumps(
            dict(
                command="AutoCaliBiasCurrents",
                value=True))
        self.talk.send(msg)

    def auto_cali_finished(self):
        """Check if auto calibration of the bias currents to find a given dark count value has finished.
        Returns: True if finished, False otherwise
        """
        msg = json.dumps(dict(request="StartAutoIV"))
        self.talk.send(msg)
        return not(self.talk.get_label("StartAutoIV")["value"])

    def error(self, error_msg):
        """Called in case of an error"""
        self.log.warning("ERROR DETECTED")
        self.log.warning(error_msg)


class WebSQControlqcode(Instrument):
    """The instrument.

    IMPORTANT: the QCoDeS parameter 'counters' updates the time stamp and counters from the detectors.
    Always call 'counters' if you want to fetch the next 'npts' counts.
    """

    def __init__(self, name, address, port, **kwargs):
        # super().__init__(name, address, port, **kwargs)
        super().__init__(name, **kwargs)

        self.TCP_IP_ADR = address
        self.CONTROL_PORT = port
        self.COUNTS_PORT = 12345
        self.NUMBER_OF_DETECTORS = 0

        self.comm = CommunicationHandler(self.root_instrument, self.log,
                                         self.TCP_IP_ADR, self.CONTROL_PORT, self.COUNTS_PORT)

        self.NUMBER_OF_DETECTORS = self.comm.talk.get_label(
            "NumberOfDetectors")["value"]

        self.add_parameter(
            'bias_current',
            unit='uA',
            get_cmd=self.comm.get_bias_current,
            set_cmd=self.comm.set_bias_current,
            docstring='Bias current setting'
        )

        self.add_parameter(
            name='npts',
            initial_value=1,
            label='Number of points',
            get_cmd=None,
            set_cmd=None,
            docstring='Number of points to acquire (see measurement_periode)'
        )

        self.add_parameter(
            'detectors',
            get_cmd=self.comm.enable_detectors,
            set_cmd=None,
            docstring='Enables/disables the detectors'
        )

        self.add_parameter(
            'number_of_detectors',
            get_cmd=self.comm.get_number_of_detectors,
            set_cmd=None,
            docstring='Gets the number of detectors in the instrument'
        )

        self.add_parameter(
            'counters',
            get_cmd=self.comm.acquire_cnts_t,
            docstring='Acquire points'
        )

        self.add_parameter(
            'measurement_periode',
            unit='ms',
            get_cmd=self.comm.get_measurement_periode,
            set_cmd=self.comm.set_measurement_periode,
            docstring='Measurement periode setting, determines the time that each point counts'
        )

        self.add_parameter(
            'timing',
            unit='ms',
            label='Time',
            parameter_class=TimeArray,
            channel=0,
            vals=Arrays(shape=(self.npts.get_latest, )),
            docstring='Parameter with timestamps for each point acquired'
        )

        for i in range(self.NUMBER_OF_DETECTORS):
            channel = i + 1
            name = 'channel' + str(channel)

            self.add_parameter(
                name,
                unit='',
                label='Counts',
                parameter_class=ChannelArray,
                channel=channel,
                setpoints=(self.timing,),
                vals=Arrays(shape=(self.npts.get_latest, )),
                snapshot_value=True,
                docstring='Parameter with setpoints with the counts for each point acquired'
            )

        self.add_parameter(
            'trigger_level',
            unit='mV',
            get_cmd=None,
            set_cmd=self.comm.set_trigger_level,
            docstring='Trigger level setting'
        )

        self.add_parameter(
            'bias_voltage',
            unit='mV',
            get_cmd=self.comm.get_bias_voltage,
            set_cmd=None,
            docstring='Gets the bias voltage'
        )

        self.connect_message()
