from typing import List, Dict, Union, Optional, Sequence, Any, Tuple
import numpy as np
import visa
import time
import logging
log = logging.getLogger(__name__)

from qcodes.instrument.visa import VisaInstrument
import qcodes.utils.validators as vals

class AttocubeController(VisaInstrument):
    """Base class for Attocube controller instrument.

    This driver has "low temperature" and "room temperature" modes, with different
    voltage limits to protect the Attocubes.

    I have found the Attocube serial communication to be kind of sketchy,
    so ask_raw() is overwritten to try to make communication more robust. YMMV.

    Args:
        atto_config: Configuration dict (example below).
        temp: 'LT' or 'RT', depending on whether the attocubes are at room temp. or low temp.
        kwargs: Keyword arguments to be passed to VisaInstrument constructor.

    An example of the atto_config dictionary is provided below:
    {
        'name': 'atto',
        'model': 'ANC300',
        "address": "ASRL1::INSTR",
        'timeout': 5,
        'terminator': '\r\n',
        'baud_rate' : 38400,
        'axes': {'x': 1, 'y': 2, 'z': 3}, # {axis_name: controller_output}
        'voltage_limits': {
            'RT': {'x': 25, 'y': 25, 'z': 25}, # room temperature limits, V
            'LT': {'x': 60, 'y': 60, 'z': 60} # low temperature limits, V
        },
        'default_frequency': {'x': 100, 'y': 100, 'z': 100}, # stepping frequency, Hz
    }
    """
    def __init__(self, atto_config: Dict, temp: str, **kwargs) -> None:
        super().__init__(atto_config['name'], atto_config['address'], atto_config['timeout'],
                         atto_config['terminator'], **kwargs)
        if temp.upper() not in ['LT', 'RT']:
            raise ValueError('Temperature must be "LT" or "RT".')
        if 'history' not in atto_config:
            atto_config['history'] = {} # dict of past attocube movements, so you don't get lost
        self.metadata.update(atto_config)
        self.visa_handle.baud_rate = atto_config['baud_rate']
        self.visa_handle.stop_bits = visa.constants.StopBits.one
        self.visa_handle.parity = visa.constants.Parity.none
        self.visa_handle.read_termination = '\r\n'
        _ = self.parameters.pop('IDN') # Get rid of this parameter
        self.temp = temp
        self.timestamp_fmt = r'%Y-%m-%d_%H:%M:%S'
        self.axes = self.metadata['axes']
        self.voltage_limits = {}
        self.add_parameter('version',
                            label='Version',
                            get_cmd='ver',
                            get_parser=str,
                            snapshot_get=False
                            )
        for axis, idx in self.axes.items():
            self.voltage_limits.update({axis: self.metadata['voltage_limits'][temp][axis]}) # Volts
            # axis mode
            self.add_parameter('mode_ax{}'.format(idx),
                                label='{} axis mode'.format(axis),
                                unit='',
                                get_cmd='getm {}'.format(idx),
                                set_cmd='setm {} {{}}'.format(idx),
                                vals=vals.Enum('gnd', 'inp', 'cap', 'stp', 'off', 'stp+', 'stp-'),
                                get_parser=self._mode_parser,
                                snapshot_get=False
                                )
            # axis voltage, with limits set according to temperature mode
            self.add_parameter('voltage_ax{}'.format(idx),
                                label='{} axis voltage'.format(axis),
                                unit='V',
                                get_cmd='getv {}'.format(idx),
                                set_cmd='setv {} {{:.3f}}'.format(idx),
                                vals=vals.Numbers(min_value=0, max_value=self.voltage_limits[axis]),
                                get_parser=self._voltage_parser,
                                snapshot_get=True
                                )
            # axis frequency
            self.add_parameter('freq_ax{}'.format(idx),
                                label='{} axis frequency'.format(axis),
                                unit='Hz',
                                get_cmd=(lambda idx=idx: self._get_freq(idx)),
                                set_cmd='setf {} {{:.0f}}'.format(idx),
                                vals=vals.Numbers(min_value=1, max_value=10000),
                                get_parser=self._freq_parser,
                                snapshot_get=True
                                )
            # axis capacitance (gettable, will fail if Attocubes are grounded with e.g. a GND cap)
            self.add_parameter('cap_ax{}'.format(idx),
                               label='{} axis capacitance'.format(axis),
                               unit='nF',
                               get_cmd=(lambda idx=idx: self._get_cap(idx)),
                               get_parser=self._cap_parser,
                               snapshot_get=False
                              )
    
    def ask_raw(self, cmd: str) -> str:
        """Query instrument with cmd and return response.
        
        Args:
            cmd: Command to write to controller.

        Returns:
            (str): Response of Attocube controller to the query `cmd`.
        """
        self.device_clear()
        response = super().ask_raw(cmd)
        status = super().ask_raw(cmd)
        self.check_response(status)
        time.sleep(0.2)
        return response
        
    def write_raw(self, cmd: str) -> str:
        """Write cmd and don't wait for response.
        
        Args:
            cmd: Command to write to controller.
        """
        self.visa_handle.write(cmd)
        
    def check_response(self, response: str) -> None:
        """Raise an exception if controller responds with 'ERROR'.
                
        Args:
            response: Response from controller.
        """
        if 'ERROR' in response:
            raise RuntimeError(response)
        
    def stop(self, axis: Union[int, str]) -> None:
        """Stops all motion along axis and then grounds the output.
        
        Args:
            axis: Either axis label (str, e.g. 'y') or index (int, e.g. 2)
        """  
        ax, idx = self._parse_axis(axis)
        log.info('Stopping {} axis motion.'.format(ax))
        self.write('stop {}'.format(idx))
        getattr(self, 'mode_ax{}'.format(idx))('gnd')

    def step(self, axis: Union[int, str], steps: int) -> None:
        """Performs a given number of Attocube steps. steps > 0 corresponds to stepu (up),
        steps < 0 corresponds to stepd (down).
        
        Args:
            axis: Either axis label (str, e.g. 'y') or index (int, e.g. 2)
            steps: Number of steps to perform (>0 for 'u', <0 for 'd')
        """
        axis, idx = self._parse_axis(axis)
        if not isinstance(steps, int):
            raise ValueError('Steps must be an integer.')
        freq = getattr(self, 'freq_ax{}'.format(idx))()
        log.info('Performing {} steps along axis {}.'.format(steps, axis))
        getattr(self, 'mode_ax{}'.format(idx))('stp')
        direc = 'u' if steps > 0 else 'd'
        self.ask('step{} {} {}'.format(direc, idx, abs(steps)))
        self.write('stepw {}'.format(idx))
        # do nothing while stepping
        time.sleep(abs(steps) / freq * 1.25)
        getattr(self, 'mode_ax{}'.format(idx))('gnd')
        ts = time.strftime(self.timestamp_fmt)
        msg = 'Moved {} steps along {} axis.'.format(steps, axis)
        self.metadata['history'].update({ts: msg})

    def _parse_axis(self, axis: Union[int, str]) -> Tuple[str, int]:
        """Returns axis label and index given either one.
        e.g. self._parse_axis('y') == self._parse_axis(2) == ('y', 2)
        
        Args:
            axis: Either axis label (str, e.g. 'y') or index (int, e.g. 2)

        Returns:
            Tuple[str, int]: Axis label, axis index.
        """
        axes = list(self.axes.keys())
        idxs = list(self.axes.values())
        if isinstance(axis, int):
            idx = axis
            axis = axes[idxs.index(idx)]
            if idx not in idxs:
                 raise ValueError('axis must be in {} or {}.'.format(axes, idxs))
        elif isinstance(axis, str):
            idx = self.axes[axis]
            if axis not in axes:
                raise ValueError('axis must be in {} or {}.'.format(axes, idxs))
        else:
            raise ValueError('axis of type str or int.')
        return axis, idx
    
    def _mode_parser(self,response: str) -> str:
        """Parse controller response like 'mode = gnd'.
        
        Args:
            response: Response from controller.

        Returns:
            str: parsed response
        """
        return response.split('=')[1].strip()
    
    def _freq_parser(self, response: str) -> float:
        """Parse controller response like 'frequency = 100 Hz'.
        
        Args:
            response: Response from controller.

        Returns:
            float: parsed response
        """
        return float(response.split('=')[1].split('H')[0])
    
    def _voltage_parser(self, response: str) -> float:
        """Parse controller response like 'voltage = 20 V'.
        
        Args:
            response: Response from controller.

        Returns:
            float: parsed response
        """
        return float(response.split('=')[1].split('V')[0])
    
    def _cap_parser(self, response: str) -> float:
        """Parse capacitance like 'capacitance = 1000 nF'.
        
        Args:
            response: Response from controller.

        Returns:
            float: parsed response
        """
        return float(response.split('=')[1].split('nF')[0].strip())
    
    def _get_freq(self, idx: int) -> str:
        """Query frequency of axis given by idx.
        
        Args:
            idx: axis index (1, 2, or 3)

        Returns:
            str: response
        """
        self.set_terminator('\n') # Bug in ANC300! Response for getf is terminated with '\n'
        response = self.ask('getf {}'.format(idx))
        self.set_terminator('\r\n') # Set terminator back to '\r\n', works for other paramaters
        return response
    
    def _get_cap(self, idx: int) -> str:
        """Query capacitance of axis given by idx.
        
        Args:
            idx: axis index (1, 2, or 3)

        Returns:
            str: response
        """
        self.parameters['mode_ax{}'.format(idx)].set('cap')
        self.write('capw {}'.format(idx))
        response = self.ask('getc {}'.format(idx))
        return response

class ANC300(AttocubeController):
    """ANC300 Attocube controller instrument.
    """
    def __init__(self, atto_config: Dict, temp: str, **kwargs) -> None:
        super().__init__(atto_config, temp, **kwargs)
        self.add_parameter('serialnum',
                    label='Controller serial number',
                    get_cmd='getcser',
                    get_parser=str,
                    snapshot_get=False
                    )
        for axis, idx in self.axes.items():
            # serial number for axis controller module (gettable only)
            self.add_parameter('serialnum_ax{}'.format(idx),
                                label='{} axis serial number'.format(axis),
                                get_cmd='getser {}'.format(idx),
                                get_parser=str,
                                snapshot_get=False
                                )
        self.initialize()

    def initialize(self) -> None:
        """Initialize instrument with parameters from self.metadata.
        """
        log.info('Initializing ANC300 controller.')
        for axis, idx in self.axes.items():
            freq_in_Hz = self.metadata['default_frequency'][axis]
            voltage_lim = self.voltage_limits[axis]
            self.parameters['freq_ax{}'.format(idx)].set(freq_in_Hz)
            self.parameters['voltage_ax{}'.format(idx)].set(voltage_lim)
            self.parameters['mode_ax{}'.format(idx)].set('gnd')
        self.serialnum()
        self.serialnum_ax1()
        self.serialnum_ax2()
        self.serialnum_ax3()
        logging.info('Connected to: {}.'.format(self.version()))
        
class ANC150(AttocubeController):
    """ANC150 Attocube controller instrument.
    """
    def __init__(self, atto_config: Dict, temp: str, **kwargs) -> None:
        super().__init__(atto_config, temp, **kwargs)
        self.initialize()

    def initialize(self) -> None:
        """Initialize instrument with parameters from self.metadata.
        """
        log.info('Initializing ANC150 controller.')
        for axis, idx in self.axes.items():
            freq_in_Hz = self.metadata['default_frequency'][axis]
            voltage_lim = self.voltage_limits[axis]
            self.parameters['freq_ax{}'.format(idx)].set(freq_in_Hz)
            self.parameters['voltage_ax{}'.format(idx)].set(voltage_lim)
            self.parameters['mode_ax{}'.format(idx)].set('gnd')
        logging.info('Connected to: {}.'.format(self.version()))
