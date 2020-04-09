"""Qcodes drivers for National Instrument mutlifunction I/O devices (DAQs).

Requires nidaqmx package: https://nidaqmx-python.readthedocs.io/en/latest/

This was written for/tested with National Instruments USB-6363 DAQ,
but the nidaqmx API is pretty general, so I expect it will work with other devices
with minimal changes.

For an example of synchronously writing data to multiple analog outputs and
acquiring data on multiple analog inputs, see
https://scanning-squid.readthedocs.io/en/latest/_modules/microscope/susceptometer.html#SusceptometerMicroscope.scan_surface
"""

from typing import Dict, Optional, Sequence, Any, Union
import numpy as np

import nidaqmx
from nidaqmx.constants import AcquisitionType, TaskMode
from qcodes.instrument.base import Instrument
from qcodes.instrument.parameter import Parameter, ArrayParameter

class DAQAnalogInputVoltages(ArrayParameter):
    """Acquires data from one or several DAQ analog inputs.

    Args:
        name: Name of parameter (usually 'voltage').
        task: nidaqmx.Task with appropriate analog inputs channels.
        samples_to_read: Number of samples to read. Will be averaged based on shape.
        shape: Desired shape of averaged array, i.e. (nchannels, target_points).
        timeout: Acquisition timeout in seconds.
        kwargs: Keyword arguments to be passed to ArrayParameter constructor.
    """
    def __init__(self, name: str, task: Any, samples_to_read: int,
                 shape: Sequence[int], timeout: Union[float, int], **kwargs) -> None:
        super().__init__(name, shape, **kwargs)
        self.task = task
        self.nchannels, self.target_points = shape
        self.samples_to_read = samples_to_read
        self.timeout = timeout
        
    def get_raw(self):
        """Averages data to get `self.target_points` points per channel.
        If `self.target_points` == `self.samples_to_read`, no averaging is done.
        """
        data_raw = np.array(self.task.read(number_of_samples_per_channel=self.samples_to_read, timeout=self.timeout))
        return np.mean(np.reshape(data_raw, (self.nchannels, self.target_points, -1)), 2)
    
class DAQAnalogInputs(Instrument):
    """Instrument to acquire DAQ analog input data in a qcodes Loop or measurement.

    Args:
        name: Name of instrument (usually 'daq_ai').
        dev_name: NI DAQ device name (e.g. 'Dev1').
        rate: Desired DAQ sampling rate per channel in Hz.
        channels: Dict of analog input channel configuration.
        task: fresh nidaqmx.Task to be populated with ai_channels.
        min_val: minimum of input voltage range (-0.1, -0.2, -0.5, -1, -2, -5 [default], or -10)
        max_val: maximum of input voltage range (0.1, 0.2, 0.5, 1, 2, 5 [default], or 10)
        clock_src: Sample clock source for analog inputs. Default: None
        samples_to_read: Number of samples to acquire from the DAQ
            per channel per measurement/loop iteration.
            Default: 2 (minimum number of samples DAQ will acquire in this timing mode).
        target_points: Number of points per channel we want in our final array.
            samples_to_read will be averaged down to target_points.
        timeout: Acquisition timeout in seconds. Default: 60.
        kwargs: Keyword arguments to be passed to Instrument constructor.
    """
    def __init__(self, name: str, dev_name: str, rate: Union[int, float], channels: Dict[str, int],
                 task: Any, min_val: Optional[float]=-5, max_val: Optional[float]=5,
                 clock_src: Optional[str]=None, samples_to_read: Optional[int]=2,
                 target_points: Optional[int]=None, timeout: Optional[Union[float, int]]=60, **kwargs) -> None:
        super().__init__(name, **kwargs)
        if target_points is None:
            if samples_to_read == 2: # minimum number of samples DAQ will read in this timing mode
                target_points = 1
            else:
                target_points = samples_to_read
        self.rate = rate
        nchannels = len(channels)
        self.samples_to_read = samples_to_read
        self.task = task
        self.metadata.update({
            'dev_name': dev_name,
            'rate': f'{rate} Hz',
            'channels': channels})
        for ch, idx in channels.items():
            channel = f'{dev_name}/ai{idx}'
            self.task.ai_channels.add_ai_voltage_chan(channel, ch, min_val=min_val, max_val=max_val)
        if clock_src is None:
            # Use default sample clock timing: ai/SampleClockTimebase
            self.task.timing.cfg_samp_clk_timing(
                rate,
                sample_mode=AcquisitionType.FINITE,
                samps_per_chan=samples_to_read)
        else:
            # Clock the inputs on some other clock signal, e.g. ao/SampleClock for synchronous acquisition
            self.task.timing.cfg_samp_clk_timing(
                    rate,
                    source=clock_src,
                    sample_mode=AcquisitionType.FINITE,
                    samps_per_chan=samples_to_read
            )
        # We need a parameter in order to acquire voltage in a qcodes Loop or Measurement
        self.add_parameter(
            name='voltage',
            parameter_class=DAQAnalogInputVoltages,
            task=self.task,
            samples_to_read=samples_to_read,
            shape=(nchannels, target_points),
            timeout=timeout,
            label='Voltage',
            unit='V'
        ) 

class DAQAnalogOutputVoltage(Parameter):
    """Writes data to one or several DAQ analog outputs. This only writes one channel at a time,
    since Qcodes ArrayParameters are not settable.

    Args:
        name: Name of parameter (usually 'voltage').
        dev_name: DAQ device name (e.g. 'Dev1').
        idx: AO channel index.
        kwargs: Keyword arguments to be passed to ArrayParameter constructor.
    """
    def __init__(self, name: str, dev_name: str, idx: int, **kwargs) -> None:
        super().__init__(name, **kwargs)
        self.dev_name = dev_name
        self.idx = idx
        self._voltage = np.nan
     
    def set_raw(self, voltage: Union[int, float]) -> None:
        with nidaqmx.Task('daq_ao_task') as ao_task:
            channel = f'{self.dev_name}/ao{self.idx}'
            ao_task.ao_channels.add_ao_voltage_chan(channel, self.name)
            ao_task.write(voltage, auto_start=True)
        self._voltage = voltage

    def get_raw(self):
        """Returns last voltage array written to outputs.
        """
        return self._voltage

class DAQAnalogOutputs(Instrument):
    """Instrument to write DAQ analog output data in a qcodes Loop or measurement.

    Args:
        name: Name of instrument (usually 'daq_ao').
        dev_name: NI DAQ device name (e.g. 'Dev1').
        channels: Dict of analog output channel configuration.
        **kwargs: Keyword arguments to be passed to Instrument constructor.
    """
    def __init__(self, name: str, dev_name: str, channels: Dict[str, int], **kwargs) -> None:
        super().__init__(name, **kwargs)
        self.metadata.update({
            'dev_name': dev_name,
            'channels': channels})
        # We need parameters in order to write voltages in a qcodes Loop or Measurement
        for ch, idx in channels.items():
            self.add_parameter(
                name=f'voltage_{ch.lower()}',
                dev_name=dev_name,
                idx=idx,
                parameter_class=DAQAnalogOutputVoltage,
                label='Voltage',
                unit='V'
            )
            
