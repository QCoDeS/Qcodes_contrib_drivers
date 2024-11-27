import warnings
from typing import Any

from qcodes.instrument import ParameterWithSetpoints, VisaInstrument
from qcodes.instrument.parameter import Parameter
from qcodes.utils.helpers import create_on_off_val_mapping
from qcodes.utils.validators import Enum, Ints, Numbers, Arrays 
import numpy

from private.bit_name_mapper import BitNameMapper
from private.interdependent_parameter import interdependent_parameter_factory

InterdependentParameter = interdependent_parameter_factory(Parameter)

class HP4395A(VisaInstrument):
    """
        This is the QCoDeS python driver for the HP/Agilent 4395A
    """

    def __init__(
        self,
        name: str,
        address: str,
        terminator: str = '\n',
        timeout: int = 100000,
        **kwargs: Any
    ) -> None:
        """
        QCoDeS driver for the HP/Agilent 4395A.

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
            2: 'Event Status Register B Summary Bit',
            3: 'Questionable Status Register Summary Bit',
            4: 'Message in Output Queue A ',
            5: 'Standard Event Status Register Summary Bit',
            6: 'Request Service',
            7: 'Operation Status Register Summary Bit'
        })

        self._map_ESR = BitNameMapper({
            0: 'Operation Complete',
            1: 'Request Control',
            2: 'Query Error',
            3: 'Device Dependent Error',
            4: 'Execution Error',
            5: 'Command Error',
            6: 'User Request',
            7: 'Power ON',
        })

        self._map_ESB = BitNameMapper({
            0: 'SING, NUMG or Cal Std. Complete',
            1: 'Service Routine Waiting or Bus Trigger Waiting',
            2: 'Data Entry Complete',
            3: 'Limit Failed, Ch 2',
            4: 'Limit Failed, Ch 1',
            5: 'Search Failed, Ch 2',
            6: 'Search Failed, Ch 1',
            7: 'Point Measurement Complete',
            8: 'Reverse GET',
            9: 'Forward GET'
        })

        self.add_parameter(  # p354
            'status_mask',
            get_cmd='*SRE?',
            set_cmd='*SRE {}',
            get_parser=lambda x: self._map_STB.value_to_bitnames(int(x), [6]),
            set_parser=lambda x: self._map_STB.bitnames_to_value(x),
            docstring='Sets the enable bits of the Status Byte Register.'
                      ' (STB)\n (0 to 255 - decimal expression of enable'
                      ' bits of the status byte register)\n'
                      '\n' + self._map_STB.docstring([6]),
        )

        self.add_parameter(  # p263
            'status_mask_instrument',
            get_cmd='ESNB?',
            set_cmd='ESNB {}',
            get_parser=lambda x: self._map_ESB.value_to_bitnames(int(x)),
            set_parser=lambda x: self._map_ESB.bitnames_to_value(x),
            docstring='Enables the bits of Event Status register B'
                      ' (ESB)\n (Instrument Evenet Status'
                      ' register).\n(0 to 65535 - decimal expression'
                      ' of the contents of the register)\n'
                      '\n' + self._map_ESB.docstring(),
        )

        self.add_parameter(  # p262
            'status_mask_event',
            get_cmd='*ESE?',
            set_cmd='*ESE {}',
            get_parser=lambda x: self._map_ESR.value_to_bitnames(int(x)),
            set_parser=lambda x: self._map_ESR.bitnames_to_value(x),
            docstring='Sets the enable bits of the Standard Event Status'
                      ' Register. (ESR)\n (0 to 255 - decimal expression'
                      ' of enable bits of the operation status register)\n'
                      '\n' + self._map_ESR.docstring(),
        )

        self.add_parameter(  # p262
            'status',
            get_cmd='*STB?',
            get_parser=lambda x: self._map_ESR.value_to_bitnames(int(x)),
            docstring='Returns Status Byte Register contents.'
        )

        self.add_parameter(  # p303, p339, p373
            'analyzer_mode',
            parameter_class=InterdependentParameter,
            set_cmd='{}',
            get_cmd=self._analyzer_mode_get,
            docstring='Selects the analyzer mode.',
            val_mapping={'Network': 'NA',
                         'Spectrum': 'SA',
                         'Impedance': 'ZA'},
        )
        self.add_parameter(  # p238
            'active_channel',
            set_cmd='{}',
            get_cmd=self._active_channel_get,
            docstring='Selects channel 1 or 2 as the active channel.',
            val_mapping={1: 'CHAN1', 2: 'CHAN2'},
        )

        self.add_parameter(  # p273
            'hold',
            set_cmd='HOLD',
            get_cmd='HOLD?',
            docstring='Freezes the data trace on the display.'
                      ' The analyzer stops sweeping and taking data.'
                      ' (SWEEP: HOLD under [Trigger])',
            val_mapping=create_on_off_val_mapping(
                on_val='1', off_val='0'),
        )

        self.add_parameter(  # p258
            'display_trace',
            set_cmd='DISP {}',
            get_cmd='DISP?',
            docstring='Selects the display trace type. (DISPLAY: DATA, MEMORY,'
                      ' DATA and MEMORY under [Display]',
            val_mapping={
                'Data': 'DATA',
                'Memory': 'MEMO',
                'Data and memory': 'DATM',
            }
        )

        self.add_parameter(  # p345
            'scale_for',
            set_cmd='SCAF {}',
            get_cmd='SCAF?',
            docstring='Selects one of the "DATA" or "MEMORY" traces to be'
                      ' scaled.\n([SCALE FOR [] under [Scale Ref]; No'
                      ' equivalent SCPI command)',
            val_mapping={
                'Data': 'DATA',
                'Memory': 'MEMORY',
            },
        )

        self.add_parameter(  # p307
            'options',
            parameter_class=InterdependentParameter,
            get_cmd='*OPT?',
            docstring='Queries the options installed. (Query only)'
            # val mapping is broken since instrument does not answer as expected
            # *OPT? returns 1D6,010 
            # val_mapping={
            #     'None': None,
            #     'HP Instrument BASIC': '1C2',
            #     'Time-gated spectrum analysis': '1D6'
            # }
        )

        self.add_parameter(  # p362
            'trigger_source',
            parameter_class=InterdependentParameter,
            dependent_on=['analyzer_mode', 'options'],
            # dependent_on=['analyzer_mode'],
            update_method=self._trigger_source_update,
            get_cmd='TRGS?',
            set_cmd='TRGS {}',
            docstring='Selects the trigger source, which is common to'
                      ' both channels. (TRIGGER: []  under [Trigger])',
            val_mapping={
                'Internal trigger': 'INT',
                'External trigger': 'EXT',
                'GPIB trigger': 'BUS',
                'Video trigger': 'VID',
                'Manual trigger': 'MAN',
                'External gate trigger': 'GAT'
            }
        )

        self.add_parameter(  # p266
            'display_format',
            parameter_class=InterdependentParameter,
            dependent_on=['analyzer_mode'],
            update_method=self._display_format_update,
            get_cmd='FMT?',
            set_cmd='FMT {}',
            docstring='Selects the display format.',
            val_mapping={
                'Log magnitude': 'LOGM',
                'Phase': 'PHAS',
                'Delay': 'DELA',
                'Linear magnitude': 'LINM',
                'SWR': 'SWR',
                'Real': 'REAL',
                'Imaginary': 'IMAG',
                'Smith chart': 'SMITH',
                'Polar chart': 'POLA',
                'Admittance Smith chart': 'ADMIT',
                'Spectrum': 'SPECT',
                'Noise level': 'NOISE',
                'Linear Y-axis': 'LINY',
                'Log Y-axis': 'LOGY',
                'Complex plane': 'COMP',
                'Expanded phase': 'EXPP',
            }
        )

        self.add_parameter(  # p292
            'measure',
            parameter_class=InterdependentParameter,
            dependent_on=['analyzer_mode'],
            update_method=self._measure_update,
            get_cmd='MEAS?',
            set_cmd='MEAS {}',
            docstring='Selects the parameters or inputs to be measured.',
            val_mapping={
                'A/R': 'AR',
                'B/R': 'BR',
                'A/B': 'AB',  # missing in prog. manual
                'R': 'R',
                'A': 'A',
                'B': 'B',
                'S11 - Reflection Forward': 'S11',
                'S12 - Transmission Forward': 'S12',
                'S21 - Transmission Reverse': 'S21',
                'S22 - Reflection Reverse': 'S22',
                # 'S': 'S',  # command not valid but in prog. manual
                'Impedance ABS': 'IMAG',
                'Impedance Phase': 'IPH',
                'Resistance': 'IRE',
                'Reactance': 'IIM',
                'Admittance ABS': 'AMAG',
                'Admittance Phase': 'APH',
                'Conductance': 'ARE',
                'Susceptance': 'AIM',
                'Reflection Coefficient ABS': 'RCM',
                'Reflection Coefficient Phase': 'RCPH',
                'Reflection Coefficient Real': 'RCR',
                'Reflection Coefficient Imaginary': 'RCIM',
                'Parallel Capacitance': 'CP',
                'Series Capacitance': 'CS',
                'Parallel Inductance': 'LP',
                'Series Inductance': 'LS',
                'Dissipation Factor': 'D',
                'Quality Factor': 'Q',
                'Parallel Resistance': 'RP',
                'Series Resistance': 'RS',
            }
        )

        self.add_parameter(  # p358
            'sweep_type',
            parameter_class=InterdependentParameter,
            dependent_on=['analyzer_mode'],
            update_method=self._sweep_type_update,
            get_cmd='SWPT?',
            set_cmd='SWPT {}',
            docstring='Selects the sweep type.',
            val_mapping={
                'Linear frequency': 'LINF',
                'Log frequency': 'LOGF',
                'List frequency': 'LIST',
                'Power': 'POWE',
            }
        )

        self.add_parameter(  # p352
            'span',
            parameter_class=InterdependentParameter,
            dependent_on=['analyzer_mode', 'sweep_type'],
            # update_method=self._span_update,
            get_cmd='SPAN?',
            get_parser=float,
            docstring='Sets the span of the sweep parameters. This command is'
                      ' not valid when the list sweeping mode is selected.'
                      ' ([Span])\nWhen editing a list sweep table, the command'
                      ' sets the span of a segment. ([SPAN] under [Sweep])'
        )

        self.add_parameter(  # p327
            'power_level',
            parameter_class=InterdependentParameter,
            dependent_on=['analyzer_mode', 'sweep_type', 'span'],
            update_method=self._power_level_update,
            get_cmd='POWE?',
            set_parser=lambda x: round(x, 1),
            get_parser=float,
            unit='dBm',
            vals=Numbers(-50, 15),
            docstring='Sets the power level segment by segment, or sets the'
                      ' power level for the list  sweep  table.  ([POWER]'
                      ' under [Sweep])\nThis command is valid when the linear'
                      ' frequency or log frequency sweeping mode is selected'
                      ' in the network and impedance analyzer modes, or when'
                      ' measuring on zero span in the spectrum analyzer mode.'
        )

        self.add_parameter(  # p234
            'bandwidth_auto',
            parameter_class=InterdependentParameter,
            dependent_on=['analyzer_mode', 'sweep_type'],
            update_method=self._bandwidth_auto_update,
            get_cmd='BWAUTO?',
            val_mapping=create_on_off_val_mapping(
                on_val='1', off_val='0'),
            docstring='When log frequency sweeping mode is selected, sets'
                      ' either the automatic or manual IF bandwidth ON.'
                      ' (Network and impedance analyzers)\nWhen'
                      ' linear frequency sweeping mode is selected, sets'
                      ' either the automatic or manual resolution bandwidth'
                      ' ON. (Spectrum analyzeronly)'
        )

        self.add_parameter(  # p233
            'bandwidth',
            parameter_class=InterdependentParameter,
            dependent_on=['analyzer_mode', 'span', 'bandwidth_auto'],
            update_method=self._bandwidth_update,
            get_cmd='BW?',
            unit='Hz',
            get_parser=lambda x: int(float(x)),
            docstring='Sets the bandwidth value for IF bandwidth reduction, or'
                      ' sets the IF bandwidth of the list sweep table.\nThis'
                      ' command is valid only if the automatic IF bandwidth'
                      ' setting is off by BWAUTO OFF command. (Network and'
                      ' impedance analyzers)\nSets the bandwidth value for the'
                      ' resolution bandwidth reduction, or sets the resolution'
                      ' bandwidth of the list sweep table. This command is'
                      ' valid only if the automatic resolution bandwidth'
                      ' setting is off by BWAUTO OFF command.'
                      ' (Spectrum analyzer)'
        )

        self.add_parameter(  # p355
            'start',
            parameter_class=InterdependentParameter,
            dependent_on=['analyzer_mode', 'sweep_type'],
            update_method=lambda: self._sweep_start_stop_update('start'),
            get_cmd='STAR?',
            get_parser=float,
            docstring='Sets the start value of the sweep parameters. This'
                      ' command is not valid when the list sweeping mode is'
                      ' selected. ([Start])\nWhen editing a list sweep table,'
                      ' the command sets the start value of a segment.'
                      ' ([SEGMENT: START] under [Sweep])'
        )

        self.add_parameter(  # p356
            'stop',
            parameter_class=InterdependentParameter,
            dependent_on=['analyzer_mode', 'sweep_type'],
            update_method=lambda: self._sweep_start_stop_update('stop'),
            get_cmd='STOP?',
            get_parser=float,
            docstring='Sets the stop value of the sweep parameters. This'
                      ' command is not valid when the list sweeping mode is'
                      ' selected. ([Stop])\nWhen editing a list sweep table,'
                      ' the command sets the stop value of a segment.'
                      ' ([SEGMENT: STOP] under [Sweep])'
        )

        self.add_parameter(  # p325
            'n_points',
            parameter_class=InterdependentParameter,
            dependent_on=['analyzer_mode', 'span'],
            update_method=self._n_points_update,
            get_cmd='POIN?',
            get_parser=int,
            vals=Ints(2, 801),
            docstring='Sets the number of points for the segment, or sets the'
                      ' number of points for the list sweep table. (In the'
                      ' spectrum analyzer mode, this command can set the'
                      ' number of points for zero span measurement only; can'
                      ' be used to query in the other measurement types.)'
        )

        self.add_parameter(  # p232
            'beep_on_warn',
            get_cmd='BEEPWARN?',
            set_cmd='BEEPWARN {}',
            val_mapping=create_on_off_val_mapping(
                on_val='1', off_val='0'),
            docstring='Sets the warning annunciator. When the annunciator is'
                      ' ON, it sounds a warning when a cautionary message is'
                      ' displayed.'
        )

        self.add_parameter(  # p232
            'beep_on_fail',
            get_cmd='BEEPFAIL?',
            set_cmd='BEEPFAIL {}',
            val_mapping=create_on_off_val_mapping(
                on_val='1', off_val='0'),
            docstring='Turns the limit fail beeper ON or OFF. When the limit'
                      ' testing is ON and the fail beeper is ON, a beep is'
                      ' emitted each time a limit test is performed and a'
                      ' failure is detected.'
        )

        self.add_parameter(  # p260
            'display_dual_channel',
            get_cmd='DUAC?',
            set_cmd='DUAC {}',
            val_mapping=create_on_off_val_mapping(
                on_val='1', off_val='0'),
            docstring='Selects the display of both measurement channels or'
                      'the active channel only.'
                      ' ([DUAL CHAN ON off] under [Display])'
        )

        self.add_parameter(  # p354
            'display_split',
            get_cmd='SPLD?',
            set_cmd='SPLD {}',
            val_mapping=create_on_off_val_mapping(
                on_val='1', off_val='0'),
            docstring='Sets the dual channel display mode. ([SPLIT DISP ON'
                      ' off] under [Display])\nOFF - Full-screen single'
                      ' graticule display\nON - Split display with two'
                      ' half-screen graticules'
        )

        self.add_parameter(  # p229
            'averaging',
            get_cmd='AVER?',
            set_cmd='AVER {}',
            val_mapping=create_on_off_val_mapping(
                on_val='1', off_val='0'),
            docstring='Turns the averaging function ON or OFF for the active'
                      ' channel. ([AVERAGING ON off] under [Bw/Avg])'
        )

        self.add_parameter(  # p230
            'averaging_factor',
            get_cmd='AVERFACT?',
            set_cmd='AVERFACT {}',
            get_parser=lambda x: int(float(x)),
            vals=Ints(1, 999),
            docstring='Turns the averaging function ON or OFF for the active'
                      ' channel. ([AVERAGING ON off] under [Bw/Avg])'
        )

        self.add_parameter(  # p323
            'unit_phase',
            parameter_class=InterdependentParameter,
            dependent_on=['analyzer_mode'],
            set_cmd='PHAU {}',
            get_cmd='PHAU?',
            docstring='Selects the unit of phase format. ([PHASE UNIT []]'
                      ' under [Format]; Impedance analyzer only.)',
            val_mapping={
                '°': 'DEG',
                'rad': 'RAD',
            },
        )

        self.add_parameter(  # p339
            'unit_spectrum',
            parameter_class=InterdependentParameter,
            dependent_on=['analyzer_mode'],
            set_cmd='SAUNIT {}',
            get_cmd='SAUNIT?',
            docstring='Selects the unit of the measurement data on the active'
                      ' channel when operating in the spectrum analyzer mode.'
                      ' (Spectrum analyzer only) ([UNIT: dBm], [dBV], [dBµV],'
                      ' [WATT], [VOLT] under [Format])',
            val_mapping={
                'dBm': 'DBM',
                'dBV': 'DBV',
                'dBµV': 'DBUV',
                'Watt': 'W',
                'Volt': 'V',
            },
        )

        self.add_parameter(  # p267
            'transfer_format',
            set_cmd='{}',
            docstring='Sets the format to transfer the trace data via GPIB.'
                      ' (No query)',
            val_mapping={
                '32-bit le': 'FORM2',
                '64-bit le': 'FORM3',
                'ASCII': 'FORM4',
                '32-bit be': 'FORM5',
            },
            snapshot_value=False
        )

        self.add_parameter(
            'sweep_parameter',
            get_cmd=self._get_sweep_parameter,
            vals=Arrays(shape=(self.n_points.cache.get,)),
            snapshot_value=False
        )

        self.add_parameter(
            'sweep_trace',
            parameter_class=ParameterWithSetpoints,
            get_cmd=self._get_sweep_trace,
            setpoints=(self.sweep_parameter,),
            snapshot_value=False,
            vals=Arrays(shape=(self.n_points.cache.get,)),
            # vals=Arrays(
            #     shape=(self.n_points.cache.get,),
            #     valid_types=(float, complex)),
        )

        model = self.IDN()['model']
        knownmodels = [
            '4395A',
            'Agilent 4395A (Simulated)'
        ]
        if model not in knownmodels:
            raise ValueError(f"'{model}' is an unknown model.")

        self.connect_message()
        self.status_clear()
        if '(Simulated)' not in model:
            self.snapshot(True)

    def write(self, cmd: str) -> None:
        super().write(cmd)
        if not self.operation_complete():
            warnings.warn("Operation seems to not have completed succesfully.",
                          stacklevel=2)

    def ask(self, cmd: str) -> str:
        returnVal = super().ask(cmd)

        esr = self.get_status_event()
        if esr:
            warnings.warn(f"Instrument event status register indicates "
                          f"the follwing errors: {esr}",
                          stacklevel=2)
        return returnVal

    def operation_complete(self) -> bool:  # p306
        ("'*OPC?' query places an ASCII character 1 in to the analyzer's"
         " output queue when all pending operations have been completed.")
        if self.ask('*OPC?') == '1':
            return True
        else:
            return False

    def get_status_event(self) -> list[str]:  # p263
        ('Returns and clears the:\n'
         '   ESR - Standard Event Status Register.')
        esr = int(self.ask_raw('*ESR?'))
        return self._map_ESR.value_to_bitnames(esr)

    def get_status_instrument(self) -> list[str]:  # p262
        ('Returns and clears the:\n'
         '    ESB - Event Status register B\n'
         '        (Instrument Event Status register)')
        esb = int(self.ask_raw('*ESB?'))
        return self._map_ESB.value_to_bitnames(esb)

    def _analyzer_mode_get(self) -> str:
        cmd_list = self.analyzer_mode.val_mapping.values()
        for cmd in cmd_list:
            if (self.ask(f'{cmd}?') == '1'):
                return cmd

    def _active_channel_get(self) -> str:
        channel_list = self.active_channel.val_mapping.values()
        for channel in channel_list:
            if (self.ask(f'{channel}?') == '1'):
                return channel

    def _trigger_source_update(self) -> None:
        vals = (
            'Internal trigger',
            'External trigger',
            'GPIB trigger',
            'Manual trigger',
        )

        if self.analyzer_mode.cache() == 'Spectrum':
            vals += ('Video trigger',)
            if '1D6' in self.options.cache():
                vals += ('External gate trigger',)

        # The * syntax is used to unpack the tuple vals
        #   and pass them as separate arguments to Enum.
        self.trigger_source.vals = Enum(*vals)

    def _display_format_update(self) -> None:
        if self.analyzer_mode.cache() == 'Network':
            self.display_format.vals = Enum(
                'Log magnitude',
                'Phase',
                'Delay',
                'Linear magnitude',
                'SWR',
                'Real',
                'Imaginary',
                'Smith chart',
                'Polar chart',
                'Admittance Smith chart',
                'Expanded phase',
            )
        if self.analyzer_mode.cache() == 'Spectrum':
            self.display_format.vals = Enum(
                'Spectrum',
                'Noise level',
            )
        if self.analyzer_mode.cache() == 'Impedance':
            self.display_format.vals = Enum(
                'Smith chart',
                'Polar chart',
                'Admittance Smith chart',
                'Linear Y-axis',
                'Log Y-axis',
                'Complex plane',
            )

    def _measure_update(self) -> None:
        if self.analyzer_mode.cache() == 'Network':
            self.measure.vals = Enum(
                'A/R',
                'B/R',
                'R',
                'A',
                'B',
                'S11',
                'S12',
                'S21',
                'S22',
            )
        if self.analyzer_mode.cache() == 'Spectrum':
            self.measure.vals = Enum(
                # 'S',  # command not valid but in prog. manual
                'R',
                'A',
                'B',
            )
        if self.analyzer_mode.cache() == 'Impedance':
            self.measure.vals = Enum(
                'Impedance ABS',
                'Impedance Phase',
                'Resistance',
                'Reactance',
                'Admittance ABS',
                'Admittance Phase',
                'Conductance',
                'Susceptance',
                'Reflection Coefficient ABS',
                'Reflection Coefficient Phase',
                'Reflection Coefficient Real',
                'Reflection Coefficient Imaginary',
                'Parallel Capacitance',
                'Series Capacitance',
                'Parallel Inductance',
                'Series Inductance',
                'Dissipation Factor',
                'Quality Factor',
                'Parallel Resistance',
                'Series Resistance',
            )

    def _sweep_type_update(self) -> None:
        if self.sweep_type.cache() == 'List frequency':
            raise NotImplementedError
        if self.analyzer_mode.cache() == 'Spectrum':
            self.sweep_type.vals = Enum(
                'Linear frequency',
                'List frequency',
            )
        else:
            self.sweep_type.vals = Enum(
                'Linear frequency',
                'Log frequency',
                'List frequency',
                'Power',
            )

    def _power_level_update(self) -> None:
        if self.analyzer_mode.cache() == 'Spectrum':
            if self.span.cache() == 0:
                set_cmd = 'POWE {}DBM'
            else:
                set_cmd = self._error_cmd_not_valid
        else:
            if (self.sweep_type.cache() == 'Linear frequency') or (self.sweep_type.cache() == 'Log frequency'):
                set_cmd = 'POWE {}DBM'
            else:
                set_cmd = self._error_cmd_not_valid
        self.power_level.set_cmd = set_cmd

    def _bandwidth_update(self) -> None:
        if self.bandwidth_auto.cache() is False:
            set_cmd = 'BW {}HZ'
        else:
            set_cmd = self._error_cmd_not_valid
        self.bandwidth.set_cmd = set_cmd

        if self.analyzer_mode.cache() == 'Spectrum':
            if self.span.cache() == 0:
                self.bandwidth.vals = Enum(
                    3e3, 5e3, 10e3, 20e3, 40e3, 100e3, 200e3, 400e3, 800e3,
                    1.5e6, 3e6, 5e6
                )
            else:
                self.bandwidth.vals = Enum(
                    1, 3, 10, 30, 100, 300,
                    1e3, 3e3, 10e3, 30e3, 100e3, 300e3,
                    1e6, 3e6
                )
        else:
            self.bandwidth.vals = Enum(
                2, 10, 30, 100, 300,
                1e3, 3e3, 10e3, 30e3
            )

    def _sweep_start_stop_update(self, parameter_name: str) -> None:
        if self.sweep_type.cache() == 'Power':
            set_cmd_tail = 'DBM'
            unit = 'dBm'
            vals = Numbers(-50, 15)
        else:
            set_cmd_tail = 'HZ'
            unit = 'Hz'
            if self.analyzer_mode.cache() == 'Spectrum':
                vals = Numbers(0, 510e6)
            else:
                vals = Numbers(10, 510e6)

        if 'start' == parameter_name:
            self.start.set_cmd = 'STAR {}' + set_cmd_tail
            self.start.unit = unit
            self.start.vals = vals

        if 'stop' == parameter_name:
            self.stop.set_cmd = 'STOP {}' + set_cmd_tail
            self.stop.unit = unit
            self.stop.vals = vals

        self._sweep_unit_update()

    def _span_update(self) -> None:
        raise NotImplementedError

    def _n_points_update(self) -> None:
        if self.analyzer_mode.cache() == 'Spectrum':
            if self.span.cache() != 0:
                set_cmd = self._error_cmd_not_valid
            else:
                set_cmd = 'POIN {}'
        else:
            set_cmd = 'POIN {}'
        self.n_points.set_cmd = set_cmd

    def _bandwidth_auto_update(self) -> None:
        if self.analyzer_mode.cache() == 'Spectrum':
            if self.sweep_type.cache() == 'Linear frequency':
                set_cmd = 'BWAUTO{}',
            else:
                set_cmd = self._error_cmd_not_valid
        else:
            if self.sweep_type.cache() == 'Log frequency':
                set_cmd = 'BWAUTO{}',
            else:
                set_cmd = self._error_cmd_not_valid
        self.n_points.set_cmd = set_cmd

    def _error_cmd_not_valid(self, value):
        raise ValueError(
            "Command not valid in current instrument configuration."
        )

    def _sweep_unit_update(self) -> None:  # 104
        # sweep_parameter unit
        if self.sweep_type.cache() == 'Power':
            self.sweep_parameter.unit = 'dBm'
        else:
            self.sweep_parameter.unit = 'Hz'

        # sweep_trace unit
        display_format = self.display_format.cache()
        analyzer_mode = self.analyzer_mode.cache()
        unit_phase = self.unit_phase.cache()
        measure = self.measure.cache()
        unit_spectrum = self.unit_spectrum.cache()

        cirf_dependent = [
            'Smith chart',
            'Polar chart',
            'Admittance Smith chart']
        if display_format in cirf_dependent:
            # depends on CIRF Command parameter, Amplitude Value (Value 2)
            raise NotImplementedError(
                'display_format units not implemented')

        if analyzer_mode == 'Network':
            if display_format == 'Log magnitude':
                sweep_trace_unit = 'dB'
            elif display_format in ['Phase', 'Expanded phase']:
                sweep_trace_unit = unit_phase
            elif display_format == 'Delay':
                sweep_trace_unit = 's'
            elif display_format == 'Linear magnitude':
                sweep_trace_unit = 'V'
            # elif display_format == 'SWR':
            #    sweep_trace_unit = ''
            # elif display_format == 'Real':
            #    sweep_trace_unit = ''
            # elif display_format == 'Imaginary':
            #    sweep_trace_unit = ''
            else:
                raise NotImplementedError(
                    'Unit needs to be implemented in _sweep_unit_update')

        if analyzer_mode == 'Spectrum':
            sweep_trace_unit = unit_spectrum

        if analyzer_mode == 'Impedance':
            ohm = [
                'Impedance ABS',
                'Resistance',
                'Reactance',
                'Parallel Resistance',
                'Series Resistance',
            ]
            phase = [
                'Impedance Phase',
                'Admittance Phase',
            ]
            siemens = [
                'Admittance ABS',
                'Conductance',
                'Susceptance',
            ]
            farad = [
                'Parallel Capacitance',
                'Series Capacitance',
            ]
            henry = [
                'Parallel Inductance',
                'Series Inductance',
            ]

            if measure in ohm:
                sweep_trace_unit = 'ohm'
            elif measure in phase:
                sweep_trace_unit = unit_phase
            elif measure in siemens:
                sweep_trace_unit = 'S'
            elif measure in farad:
                sweep_trace_unit = 'F'
            elif measure in henry:
                sweep_trace_unit = 'H'
            else:
                raise NotImplementedError(
                    'Unit needs to be implemented in _sweep_unit_update')

        self.sweep_trace.unit = sweep_trace_unit

    def status_clear(self) -> None:  # p240
        ('Clears the error queues:'
         ' * STB - Status Byte\n'
         ' * OSR - Operational Status register\n'
         ' * ESR - Standard Event Status register,\n'
         ' * ESB - Event Status register B'
         ' (Instrument Event Status register)')
        self.write_raw('*CLS')

    def wait_for_srq(self, timeout=25) -> None:
        ('Wait for service request (SRQ) from instrument.')
        return self.visa_handle.wait_for_srq(timeout)

    def _get_sweep_trace(
        self,
        number: list[int] = [1],
        retrun_val_2=False
    ) -> None:  # p314
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

    def _get_sweep_parameter(self) -> list[float]:  # p319
        ('Outputs the sweep parameter data. (Query only)')
        self._sweep_unit_update()
        if not self.transfer_format.cache == '32-bit le':
            self.transfer_format('32-bit le')
        returnVal = self.visa_handle.query_binary_values(
            'OUTPSWPRM?', is_big_endian=True)
        return numpy.array(returnVal)

    def scale_auto(self) -> None:  # p229
        ('Brings the trace data, defined by the SCAF command, in view on the'
         ' display. (Network and impedance analyzers only) ([AUTO SCALE] under'
         ' [Scale Ref]; No query)')
        if self.analyzer_mode.cache() == 'Spectrum':
            self._error_cmd_not_valid
        else:
            self.write('AUTO')

    def reset(self) -> None:  # 337
        ('Resets the analyzer to its default values (No query):\n'
         ' * Initializes the instrument settings.\n'
         ' * Sets the trigger mode to HOLD.\n'
         ' * Resets HP Instrument BASIC\n'
         '   (only if executed on the external controller)')
        self.write('*RST')
        # self.snapshot(update=True)

    def single(self) -> None:  # p350
        ('Makes one sweep of the data and returns to the hold mode.'
         ' Instrument BASIC EXECUTE executable;\n[SINGLE] under'
         ' [Trigger]; No query;\nWhen you execute this command by [EXECUTE]'
         ' command of the instrument BASIC, the analyzer sweeps once and then'
         ' back the control to the analyzer. The program waits the completion'
         ' of sweep. You can use this method instead of detecting the sweep'
         ' end by monitoring the status register to synchronize the program'
         ' with the analyzer.')
        self.write('SING')

    def number_of_groups(self, number: int) -> None:  # p 303
        ('Triggers a user-specified number of sweeps and returns to the'
         ' HOLD mode.\n([NUMBER OF GROUPS] under [Trigger]; No query')
        self.write(f'NUMG {number}')
