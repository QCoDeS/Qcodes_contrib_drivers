import warnings
from typing import Any, Union, Optional, Callable
from typing_extensions import Literal

# from qcodes import ParameterWithSetpoints, VisaInstrument
from qcodes.instrument import ParameterWithSetpoints, VisaInstrument
from qcodes.instrument.parameter import Parameter  # , invert_val_mapping
from qcodes.utils.helpers import create_on_off_val_mapping
from qcodes.utils.validators import Enum, Ints, Numbers, Arrays  # , Lists,
import numpy
import os

from private.bit_name_mapper import BitNameMapper
from private.interdependent_parameter import interdependent_parameter_factory
from private.reset_value_parameter import reset_value_parameter_factory

ResetValueParameter = reset_value_parameter_factory(Parameter)
InterdependentParameter = interdependent_parameter_factory(ResetValueParameter)

class HP4194A(VisaInstrument):
    """
        This is the QCoDeS python driver for the HP 4194A
    """

    def __init__(
        self,
        name: str,
        address: str,
        terminator: str = '\r\n',
        # terminator: str = None,
        timeout: int = 10,
        # timeout: int = 100000,
        **kwargs: Any
    ) -> None:
        """
        QCoDeS driver for the HP 4194A.

        Args:
            name (str): Name of the instrument.
            address (str): Address of the instrument.
            terminator (str): Terminator character of
                the string reply. Optional, default `'\\n'`
            timeout (int): VISA timeout is set purposely
                to a long time to allow long spectrum measurement.
                Optional, default 100000
        """
        super().__init__(
            name=name,
            address=address,
            terminator=terminator,
            timeout=timeout,
            **kwargs
        )

        self._map_STB = BitNameMapper({
            0: 'Measurement complete',
            1: 'Sweep complete', ###
            3: 'End status',
            4: 'Ignore trigger',
            5: 'Error (Hardware trips)',  ###
            6: 'RQS',
        })

        self.add_parameter(  
            'transfer_format',
            parameter_class=ResetValueParameter,
            value_after_reset='ASCII',
            set_cmd='FMT{}',
            docstring='Sets the format to transfer the trace data via GPIB.'
                      ' (No query)',
            val_mapping={
                'ASCII': '1',
                '64-bit le': '2',
                '32-bit le': '3',  # p260
            },
            # snapshot_value=False
        )

        self.add_parameter(
            'status_mask',
            parameter_class=ResetValueParameter,
            value_after_reset=[],
            set_cmd='RQS{}',
            # get_cmd=self.status_mask.cache.get(),
            set_parser=lambda x: self._map_STB.bitnames_to_value(x),
            get_parser=lambda x: self._map_STB.value_to_bitnames(x),
            docstring='Mask the status byte'
                      '\n' + self._map_STB.docstring([6]),
        )

        self.add_parameter(  # 1-a: Function
            'analyzer_mode',
            parameter_class=InterdependentParameter,
            value_after_reset='Impedance',
            set_cmd='FNC{}',
            docstring='Selects the analyzer mode.',
            val_mapping={'Impedance': '1',
                         'Gain-Phase': '2',
                         'Impedance with Z Probe': '3'},
        )

        self.add_parameter(  # 1-a: Function
            'measure_impedance',
            parameter_class=InterdependentParameter,
            value_after_reset='|Z|-theta',
            set_cmd='IMP{}',
            docstring='Selects the measurement function for Impedance.',
            val_mapping={
                '|Z|-theta': '1',
                'R-X': '2',
                'Ls-Rs': '3',
                'Ls-Q': '4',
                'Cs-Rs': '5',
                'Cs-Q': '6',
                'CS-D': '7',
                '|X|-theta': '8',
                'G-B': '9',
                'Lp-G': '10',
                'Lp-Q': '11',
                'Cp-G': '12',
                'Cp-Q': '13',
                'Cp-D': '14',
                '|Z|-La': '15',
                '|Z|-Ca': '16',
                '|Z|-Lp': '17',
                '|Z|-Cp': '18',
                'Lp-Rp': '19',
                'Cp-Rp': '20',
            },
            update_method=self._sweep_unit_update,
        )

        self.add_parameter(  # 1-a: Function
            'measure_gain_phase',
            parameter_class=InterdependentParameter,
            value_after_reset='Tch/Rch(dB)-theta',
            set_cmd='GPP{}',
            docstring='Selects the measurement function for Gain-Phase.',
            val_mapping={
                'Tch/Rch(dB)-theta': '1',
                'Tch/Rch-theta': '2',
                'Tch/Rch(dB)-tau': '3',
                'Rch-Tch(V)': '4',
                'Rch-Tch(dBm)': '5',
                'Rch-Tch(dBV)': '6',
            },
            update_method=self._sweep_unit_update,
        )

        self.add_parameter(  # 7: Mesurement Unit
            'power_splitter_mode',
            parameter_class=ResetValueParameter,
            value_after_reset='Dual',
            set_cmd='PWS{}',
            docstring='Selects the power splitter mode.',
            val_mapping={
                'Dual': '1',
                'Single': '2',
            }
        )

        self.add_parameter(  # 1-b: Sweep
            'sweep_type',
            parameter_class=InterdependentParameter,
            value_after_reset='Linear',
            set_cmd='SWT{}',
            docstring='Selects the sweep type.',
            val_mapping={
                'Linear': '1',
                'Log': '2',
            }
        )

        self.add_parameter(  # 1-b: Sweep
            'sweep_parameter_mode',
            parameter_class=InterdependentParameter,
            dependent_on=['analyzer_mode', 'sweep_type'],
            update_method=self._sweep_parameter_mode_update,
            value_after_reset='Frequency',
            set_cmd='SWP{}',
            docstring='Selects the mode of the sweep parameter.',
            val_mapping={
                'Frequency': '1',
                'DC Bias': '2',  # (Impedance measurement Only)
                'Osc level(V)': '3',
                'Osc level(dBm)': '4',  # (Linear sweep Only)
                'Osc level(dBV)': '5',  # (Linear sweep only)
            }
        )

        self.add_parameter(  # 1-b: Sweep
            'sweep_direction',
            parameter_class=InterdependentParameter,
            value_after_reset='Up',
            set_cmd='SWD{}',
            docstring='Selects the sweep direction.',
            val_mapping={
                'Up': '1',
                'Down': '2',
            }
        )

        self.add_parameter(  # 1-b: Sweep
            'sweep_mode',
            parameter_class=InterdependentParameter,
            value_after_reset='Repeat',
            set_cmd='SWM{}',
            docstring='Selects the sweep mode.',
            val_mapping={
                'Repeat': '1',
                'Single': '2',
                'Manual': '3',
            }
        )

        self.add_parameter(  # 1-d: Display
            'display_mode',
            parameter_class=InterdependentParameter,
            value_after_reset='X-A&B',
            set_cmd='DSP{}',
            docstring='Selects the display mode.',
            val_mapping={
                'X-A&B': '1',
                'A-B': '2',
                'Table': '3',
            }
        )

        self.add_parameter(  # 1-d: Display
            'display_data_A',
            parameter_class=InterdependentParameter,
            value_after_reset=True,
            set_cmd='DPA{}',
            docstring='Display data A on/off. Effective for X-A&B mode.',
            val_mapping=create_on_off_val_mapping(
                on_val='1', off_val='0')
        )

        self.add_parameter(  # 1-d: Display
            'display_data_B',
            parameter_class=InterdependentParameter,
            value_after_reset=True,
            set_cmd='DPB{}',
            docstring='Display data B on/off. Effective for X-A&B mode.',
            val_mapping=create_on_off_val_mapping(
                on_val='1', off_val='0')
        )

        self.add_parameter(  # 1-d: Display
            'display_scale_A',
            parameter_class=InterdependentParameter,
            value_after_reset='Linear',
            set_cmd='ASC{}',
            docstring='Scale display data A to Linear/Log. Effective for X-A&B mode.',
            val_mapping={
                'Linear': '1',
                'Log': '2',
            }
        )

        self.add_parameter(  # 1-d: Display
            'display_scale_B',
            parameter_class=InterdependentParameter,
            value_after_reset='Linear',
            set_cmd='BSC{}',
            docstring='Scale display data B to Linear/Log. Effective for X-A&B mode.',
            val_mapping={
                'Linear': '1',
                'Log': '2',
            }
        )

        self.add_parameter(  # 1-d: Display
            'display_autoscale',
            parameter_class=Parameter,
            set_cmd='AUTO{}',
            docstring='Autoscale display to A/B. Effective for X-A&B mode.',
            vals=Enum('A', 'B'),
        )

        self.add_parameter(  # 6: Parameter
            'n_points',
            parameter_class=Parameter,
            set_cmd='NOP={}',
            get_cmd='NOP?',
            get_parser=lambda x: int(x),
            docstring='Number of measurement points.',
            vals=Ints(2, 401),
        )

        self.add_parameter(  # 6: Parameter
            'start',
            parameter_class=InterdependentParameter,
            dependent_on=['analyzer_mode', 'sweep_parameter_mode', 'sweep_type'],
            update_method=lambda: self._sweep_start_stop_update('start'),
            set_cmd='START={}',
            set_parser=lambda x: round(x, 3),
            get_cmd='START?',
            get_parser=lambda x: float(x),
            docstring='Sets the start value of the sweep parameters.',
        )

        self.add_parameter(  # 6: Parameter
            'stop',
            parameter_class=InterdependentParameter,
            dependent_on=['analyzer_mode', 'sweep_parameter_mode', 'sweep_type'],
            update_method=lambda: self._sweep_start_stop_update('stop'),
            set_cmd='STOP={}',
            set_parser=lambda x: round(x, 3),
            get_cmd='STOP?',
            get_parser=lambda x: float(x),
            docstring='Sets the stop value of the sweep parameters.',
        )

        
        # 
        # self.add_parameter(  # 6: Parameter
        #     'osc',
        #     parameter_class=Parameter,
        #     # dependent_on=['analyzer_mode', 'sweep_parameter_mode', 'start', 'stop'],
        #     # update_method=self._oscillator_level_update(),
        #     set_cmd='OSC={}',
        #     set_parser=lambda x: round(x, 2),
        #     get_cmd='OSC?',
        #     get_parser=lambda x: float(x),
        #     docstring='Sets the value of the oscillator level.',
        # )

        self.add_parameter(  # 6: Parameter
            'oscillator_level',
            parameter_class=InterdependentParameter,
            # dependent_on=['analyzer_mode', 'sweep_parameter_mode', 'start', 'stop'],
            # update_method=self._oscillator_level_update(),
            # set_cmd='OSC={}',
            get_cmd='OSC?',
            get_parser=lambda x: float(x),
            docstring='Sets the value of the oscillator level.',
        )

        self.add_parameter(  # 6: Parameter
            'oscillator_level_unit',
            parameter_class=Parameter,
            set_cmd=self._oscillator_level_unit_update,
            docstring='Sets the unit of the oscillator level.',
            vals=Enum('dBm', 'V'),
        )

        self.add_parameter(  # 5: Averaging
            'averaging_factor',
            parameter_class=Parameter,
            vals=Enum(1, 2, 4, 8, 16, 32, 64, 128, 256),
            set_cmd='NOA={}',
            get_cmd='NOA?',
            get_parser=lambda x: int(x),
            docstring='Sets the averaging factor.',
        )

        self.add_parameter(  # 4: Integ Time
            'integration_time',
            parameter_class=ResetValueParameter,
            value_after_reset=0.5,
            set_cmd='ITM{}',
            unit='ms',
            docstring='Sets the stop value of the sweep parameters.',
            vals=Enum(0.5, 5, 100),
            val_mapping={
                0.5: '1',
                5: '2',
                100: '3',
            }
        )

        self.add_parameter(  # 1-d: Display
            'sweep_parameter',
            parameter_class=Parameter,
            get_cmd=lambda: numpy.linspace(
                self.start.cache.get(),
                self.stop.cache.get(),
                self.n_points.cache.get()),
            # vals=Arrays(shape=(self.n_points,)),
            vals=Arrays(shape=(self.n_points.cache.get,)),
            snapshot_value=False,
        )

        self.add_parameter(  # 1-d: Display
            'sweep_trace_A',
            parameter_class=ParameterWithSetpoints,
            setpoints=(self.sweep_parameter,),
            get_cmd='A?',
            get_parser=lambda x: numpy.array(
                [float(v) for v in x.split(",")]),
            docstring='Register for display data A',
            # vals=Arrays(shape=(self.n_points,)),
            vals=Arrays(shape=(self.n_points.cache.get,)),
            snapshot_value=False,
        )

        self.add_parameter(  # 1-d: Display
            'sweep_trace_B',
            parameter_class=ParameterWithSetpoints,
            setpoints=(self.sweep_parameter,),
            get_cmd='B?',
            get_parser=lambda x: numpy.array(
                [float(v) for v in x.split(",")]),
            docstring='Register for display data A',
            # vals=Arrays(shape=(self.n_points,)),
            vals=Arrays(shape=(self.n_points.cache.get,)),
            snapshot_value=False,
        )



#################################################
#################################################
#################################################
        model = self.IDN()['model']
        knownmodels = [
            'HP4194A IMPEDANCE/GAIN-PHASE_ANALYZER OPT350',
            'HP4194A IMPEDANCE/GAIN-PHASE_ANALYZER OPT350 (Simulated)'
        ]
        if model not in knownmodels:
            raise ValueError(f"'{model}' is an unknown model.")

        self.connect_message()
        self.reset()
        #self.status_clear()
        if '(Simulated)' not in model:
            self.snapshot(True)

    def _sweep_parameter_mode_update(self) -> None:
        vals = {'Frequency': '1', }

        if 'Impedance' in self.analyzer_mode.cache():
            vals.update({'DC Bias': '2', })

        vals.update({'Osc level(V)': '3', })

        if self.sweep_type.cache() == 'Linear':
            vals.update({
                'Osc level(dBm)': '4',
                'Osc level(dBV)': '5',
            })

        self.sweep_parameter_mode.vals = Enum(*vals)

        if self.sweep_parameter_mode() == 'Frequency':
            self.sweep_parameter.unit = 'Hz'
        else:
            raise NotImplementedError

    def _oscillator_level_unit_update(self, osc_unit: str) -> None:
        if self.analyzer_mode.cache() == 'Gain-Phase':
            if osc_unit == 'V':
                self._oscillator_level_update(use_V=True)
            elif osc_unit == 'dBm':
                self._oscillator_level_update(use_V=False)
            else:
                raise ValueError
        else:
            raise NotImplementedError

        self.oscillator_level(self.oscillator_level.vals._min_value)

    def _oscillator_level_update(self, use_V = False) -> None:
        start = self.start.cache.get()
        stop = self.stop.cache.get()
        if self.sweep_parameter_mode.cache() == 'Frequency':
            if self.analyzer_mode.cache() == 'Impedance':
                set_cmd_tail = 'V'
                unit = 'V'
                set_parser = lambda x: round(x, 2)
                if (start > 10000e3) or (stop > 10000e3):
                    vals = Numbers(0.01, 0.5)
                else:
                    vals = Numbers(0.01, 1.0)
            elif ((self.analyzer_mode.cache() == 'Gain-Phase')
                  or (self.analyzer_mode.cache() == 'Impedance with Z Probe')):
                if use_V:
                    set_cmd_tail = 'V'
                    unit = 'V'
                    set_parser = lambda x: round(x, 2)
                    vals = Numbers(0.01, 1.2)
                else:
                    set_cmd_tail = 'DBM'
                    unit = 'dBm'
                    set_parser = lambda x: round(x, 1)
                    vals = Numbers(-65.0, 15.0)
            else:
                raise NotImplementedError
        else:
            raise NotImplementedError

        self.oscillator_level_unit.cache.set(unit)
        self.oscillator_level.unit = unit
        self.oscillator_level.vals = vals
        self.oscillator_level.set_parser = set_parser
        self.oscillator_level.set_cmd = 'OSC={}' + set_cmd_tail

    def _sweep_start_stop_update(self, parameter_name: str) -> None:
        if self.sweep_parameter_mode.cache() == 'Frequency':
            unit = 'Hz'
            if self.analyzer_mode.cache() == 'Impedance':
                if self.cable_length == '1m':
                    vals = Numbers(100, 15e6)
                else:
                    vals = Numbers(100, 40e6)
            elif self.analyzer_mode.cache() == 'Gain-Phase':
                vals = Numbers(10, 100e6)
            elif self.analyzer_mode.cache() == 'Impedance with Z Probe':
                vals = Numbers(10, 100e6)
            else:
                raise NotImplementedError
        else:
            raise NotImplementedError

        if 'start' == parameter_name:
            self.start.unit = unit
            self.start.vals = vals

        if 'stop' == parameter_name:
            self.stop.unit = unit
            self.stop.vals = vals

        self._oscillator_level_update()

    def _sweep_unit_update(self) -> None:
        analyzer_mode = self.analyzer_mode.cache()
        A_unit = None
        B_unit = None

        if analyzer_mode == 'Gain-Phase':
            meas = self.measure_gain_phase()
            if meas == 'Rch-Tch(V)':
                B_unit = 'V'
        elif analyzer_mode == 'Impedance':
            meas = self.measure_impedance()
            if meas == '|Z|-theta':
                B_unit = 'deg'
            elif meas == 'Cs-Rs':
                B_unit == 'Ohm'
            elif meas == 'Cs-D':
                A_unit == 'F'

        self.sweep_trace_A.unit = A_unit
        self.sweep_trace_B.unit = B_unit

    def sweep_start_trigger(self) -> None:
        """
            Sweep start trigger
        """
        self.write('SWTRG')

    def reset(self) -> None:
        """
            Reset the instrument
            Note
            The RST command resets the instrument to the power-on
            default conditions except for the following settings.
            1. Sweep mode is set to the Single sweep mode (code: SWM2)
               and the traces on the screen will be erased.
            2. Data registers (A ~ D), general purpose registers (RA - RL),
               all registers for compensation, Rn,  Z, and all
               read-only type registers are not reset.
            3. Program WORK AREA is not cleared.

        """
        self.write('RST')
        if float(self.ask('STOP?')) == 40000e3:
            self.cable_length = '0m'
        else:
            self.cable_length = '1m'

        for name, param in self.parameters.items():
            if hasattr(param, 'reset_value'):
                param.reset_value()

        for name, param in self.parameters.items():
            if hasattr(param, 'update_method'):
                if isinstance(param.update_method, Callable):
                    param.update_method()

    def get_idn(self) -> dict[str, Optional[str]]:
        """
        For the HP 4194A instrument, the response to 'ID?' command 
        is used as it does not support standard '*IDN?' command.

        Returns:
            A dict containing vendor, model, serial, and firmware.
        """
        idstr = ""  # in case self.ask fails
        try:
            original_termination = self.visa_handle.read_termination
            self.visa_handle.read_termination = None
            self.visa_handle.write('ID?')
            idstr = self.visa_handle.read()
            self.visa_handle.read_termination = original_termination

            # Full string as model, stripping leading and trailing whitespaces
            model = idstr.replace("\r\n", " ").strip()

            idparts: list[Optional[str]] = ["HP", model, None, None]

        except Exception:
            self.log.warning(
                f"Error getting or interpreting ID?: {idstr!r}", exc_info=True
            )
            idparts = [None, self.name, None, None]

        return dict(zip(("vendor", "model", "serial", "firmware"), idparts))

    def wait_for_srq(self, timeout=25) -> None:
        ('Wait for service request (SRQ) from instrument.')
        return self.visa_handle.wait_for_srq(timeout)

    def _get_sweep_trace(
        self,
        number: list[int] = [1],
        retrun_val_2=False
    ) -> None:
        ('Outputs DATA TRACE data. (Query only)')
        if not self.transfer_format.cache == '32-bit le':
            self.transfer_format('32-bit le')
        trace = self.visa_handle.query_binary_values(
            'OUTPDTRC?', is_big_endian=True)
        trace_length = len(trace)
        points = self.n_points.cache()
        if trace_length == points:
            returnVal = trace
        elif trace_length == 2 * points:
            val_1 = trace[0::2]  # Amplitude value
            if retrun_val_2 is True:
                # val_2 = trace[1::2]  # Auxiliary amplitude value
                raise NotImplementedError(
                    'Returning Auxiliary amplitude value not implemented.')
            returnVal = val_1
        else:
            raise ValueError(
                "Number of points recieved does not"
                f" match {self.name}.n_points")
        return numpy.array(returnVal)
# 
#         self.add_parameter('ID',
#                            get_cmd='ID?',
#                            get_parser=self.read_until_empty_line)
# 
# 
#     def read_until_empty_line(self, cmd):
#         response = []
#         while True:
#             line = self.instrument.readline().rstrip()  # rstrip to remove the '\r\n'
#             if line == '':
#                 break
#             response.append(line)
#         return response

#
#    def get_raw(self) -> np.ndarray:
#        """
#        Return the axis values, with values retrieved from the parent instrument
#        """
#        return np.linspace(self._startparam(), self._stopparam(), self._pointsparam())
#
#

"""
        self.add_parameter(
            'start',
            parameter_class=InterdependentParameter,
            dependent_on=['analyzer_mode', 'sweep_type'],
            update_method=lambda: self._sweep_parameter_update('start'),
            get_cmd='STAR?',
            get_parser=float,
            docstring='Sets the start value of the sweep parameters. This'
                      ' command is not valid when the list sweeping mode is'
                      ' selected. ([Start])\nWhen editing a list sweep table,'
                      ' the command sets the start value of a segment.'
                      ' ([SEGMENT: START] under [Sweep])'
        )





"""
