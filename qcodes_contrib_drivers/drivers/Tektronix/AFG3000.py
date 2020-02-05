import logging
log = logging.getLogger(__name__)

from qcodes import VisaInstrument
import qcodes.utils.validators as vals

class AFG3000(VisaInstrument):
    """Qcodes driver for Tektronix AFG3000 series arbitrary function generator.
    
    Not all instrument functionality is included here.
    """
    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, terminator='\n', timeout=20, **kwargs)

        self.add_parameter(
            name='trigger_mode',
            label='Trigger mode',
            get_cmd='OUTPut:TRIGger:MODE?',
            get_parser=str,
            set_cmd='OUTPut:TRIGger:MODE {}',
            vals=vals.Enum('TRIGger', 'TRIG', 'SYNC')
        )

        # Source/output parameters, 2 channels
        for src in [1, 2]:

            # Outputs
            self.add_parameter(
                name=f'impedance_output{src}',
                label=f'Output {src} impedance',
                unit='Ohm',
                get_cmd=f'OUTPut{src}:IMPedance?',
                get_parser=float,
                set_cmd=f'OUTPut{src}:IMPedance {{}}OHM',
                vals=vals.Numbers(1,10000)
            )
            self.add_parameter(
                name=f'polarity_output{src}',
                label=f'Output {src} polarity',
                get_cmd=f'OUTPut{src}:POLarity?',
                get_parser=str,
                set_cmd=f'OUTPut{src}:POLarity {{}}',
                vals=vals.Enum('NORMal', 'NORM', 'INVerted', 'INV')
            ) 
            self.add_parameter(
                name=f'state_output{src}',
                label=f'Output {src} state',
                get_cmd=f'OUTPut{src}:STATe?',
                get_parser=lambda x: bool(int(x)),
                set_cmd=f'OUTPut{src}:STATe {{}}',
                vals=vals.Enum('OFF', 0, 'ON', 1)
            )  

            # Amplitude modulation
            self.add_parameter(
                name=f'am_depth{src}',
                label=f'Source {src} AM depth',
                unit='%',
                get_cmd=f'SOURce{src}:AM:DEPTh?',
                get_parser=float,
                set_cmd=f'SOURce{src}:AM:DEPTh {{}}PCT',
                vals=vals.Multiples(divisor=0.1, min_value=0, max_value=120)
            )

            # Frequency modulation
            self.add_parameter(
                name=f'fm_deviation{src}',
                label=f'Source {src} FM deviation',
                unit='Hz',
                get_cmd=f'SOURce{src}:FM:DEViation?',
                get_parser=float,
                set_cmd=f'SOURce{src}:FM:DEViation {{}}Hz',
                vals=vals.Numbers()
            )

            # Phase modulation
            self.add_parameter(
                name=f'pm_deviation{src}',
                label=f'Source {src} PM deviation',
                unit='degrees',
                get_cmd=f'SOURce{src}:PM:DEViation?',
                get_parser=float,
                set_cmd=f'SOURce{src}:PM:DEViation {{}}DEG',
                vals=vals.Ints(0, 180)
            )

            # Pulse-width modulation
            self.add_parameter(
                name=f'pwm_duty_deviation{src}',
                label=f'Source {src} PWM duty cycle deviation',
                unit='%',
                get_cmd=f'SOURce{src}:PWM:DEViation:DCYCle?',
                get_parser=float,
                set_cmd=f'SOURce{src}:PWM:DEViation:DCYCle {{}}PCT',
                vals=vals.Numbers(0, 100)
            )

            # Amplitude, frequency, phase, and pulse-width modulation
            for mod_type in ['AM', 'FM', 'PM', 'PWM']:
                self.add_parameter(
                    name=f'{mod_type.lower()}_internal_freq{src}',
                    label=f'Source {src} {mod_type} interal frequency',
                    unit='Hz',
                    get_cmd=f'SOURce{src}:{mod_type}:INTernal:FREQuency?',
                    get_parser=float,
                    set_cmd=f'SOURce{src}:{mod_type}:INTernal:FREQuency {{}}Hz',
                    vals=vals.Multiples(divisor=1e-3, min_value=2e-3, max_value=5e4)
                )              
                self.add_parameter(
                    name=f'{mod_type.lower()}_internal_function{src}',
                    label=f'Source {src} {mod_type} interal function',
                    get_cmd=f'SOURce{src}:{mod_type}:INTernal:FUNCtion?',
                    get_parser=str,
                    set_cmd=f'SOURce{src}:{mod_type}:INTernal:FUNCtion {{}}',
                    vals=vals.Enum(
                    'SINusoid', 'SIN',
                    'SQUare',  'SQU',
                    'TRIangle', 'TRI',
                    'RAMP',
                    'NRAMp', 'NRAM',
                    'PRNoise', 'PRN',
                    'USER', 'USER1', 'USER2', 'USER3', 'USER4',
                    'EMEMory', 'EMEM',
                    'EFILe', 'EFIL')
                ) 
                self.add_parameter(
                    name=f'{mod_type.lower()}_internal_efile{src}',
                    label=f'Source {src} {mod_type} interal EFile',
                    get_cmd=f'SOURce{src}:{mod_type}:INTernal:FUNCtion:EFILe?',
                    get_parser=str,
                    set_cmd=f'SOURce{src}:{mod_type}:INTernal:FUNCtion:EFILe {{}}',
                    vals=vals.Strings()
                )
                self.add_parameter(
                    name=f'{mod_type.lower()}_internal_source{src}',
                    label=f'Source {src} {mod_type} source',
                    get_cmd=f'SOURce{src}:{mod_type}:SOURce?',
                    get_parser=str,
                    set_cmd=f'SOURce{src}:{mod_type}:SOURce? {{}}',
                    vals=vals.Enum('INTernal', 'INT', 'EXTernal', 'EXT')
                )
                self.add_parameter(
                    name=f'{mod_type.lower()}_state{src}',
                    label=f'Source {src} {mod_type} interal state',
                    get_cmd=f'SOURce{src}:{mod_type}:STATe?',
                    get_parser=lambda x: bool(int(x)),
                    set_cmd=f'SOURce{src}:{mod_type}:STATe {{}}',
                    vals=vals.Enum('OFF', 0, 'ON', 1)
                )

            # Burst mode
            self.add_parameter(
                name=f'burst_mode{src}',
                label=f'Source {src} burst mode',
                get_cmd=f'SOURce{src}:BURSt:MODE?',
                get_parser=str,
                set_cmd=f'SOURce{src}:BURSt:MODE {{}}',
                vals=vals.Enum('TRIGgered', 'TRIG', 'GATed', 'GAT')
            )
            self.add_parameter(
                name=f'burst_ncycles{src}',
                label=f'Source {src} burst N cycles',
                get_cmd=f'SOURce{src}:BURSt:NCYCles?',
                get_parser=float,
                set_cmd=f'SOURce{src}:BURSt:NCYCles {{}}',
                vals=vals.MultiType(
                    vals.Ints(min_value=1, max_value=1000000),
                    vals.Enum('INFinity', 'INF', 'MAXimum', 'MAX', 'MINimum', 'MIN'))
            )
            self.add_parameter(
                name=f'burst_state{src}',
                label=f'Source {src} burst state',
                get_cmd=f'SOURce{src}:BURSt:STATe?',
                get_parser=lambda x: bool(int(x)),
                set_cmd=f'SOURce{src}:BURSt:STATe {{}}',
                vals=vals.Enum('OFF', 0, 'ON', 1)
            )
            self.add_parameter(
                name=f'burst_tdelay{src}',
                label=f'Source {src} burst time delay',
                unit='s',
                get_cmd=f'SOURce{src}:BURSt:TDELay?',
                get_parser=float,
                set_cmd=f'SOURce{src}:BURSt:TDELay {{}}s',
                vals=vals.Numbers(0, 85)
            )

            if src == 1:
                combine_enum = ('NOISe', 'NOIS', 'EXTernal', 'EXT', 'BOTH', '')
            else:
                combine_enum = ('NOISe', 'NOIS', '')
            self.add_parameter(
                name=f'combine{src}',
                label=f'Source {src} combine signals',
                get_cmd=f'SOURce{src}:COMBine:FEED?',
                get_parser=str,
                set_cmd=f'SOURce{src}:COMBine:FEED {{}}',
                vals=vals.Enum(combine_enum)
            ) 

            # Frequency controls                 
            self.add_parameter(
                name=f'center_freq{src}',
                label=f'Source {src} center frequency',
                unit='Hz',
                get_cmd=f'SOURce{src}:FREQuency:CENTer?',
                get_parser=float,
                set_cmd=f'SOURce{src}:FREQuency:CENTer {{}}Hz',
                vals=vals.Numbers()
            )
            self.add_parameter(
                name=f'freq_concurrent{src}',
                label=f'Source {src} concurrent frequency',
                get_cmd=f'SOURce{src}:FREQuency:CONCurrent?',
                get_parser=lambda x: bool(int(x)),
                set_cmd=f'SOURce{src}:FREQuency:CONCurrent {{}}',
                vals=vals.Enum('OFF', 0, 'ON', 1)
            ) 
            self.add_parameter(
                name=f'freq_cw{src}',
                label=f'Source {src} continuous frequency',
                unit='Hz',
                get_cmd=f'SOURce{src}:FREQuency:CW?',
                get_parser=float,
                set_cmd=f'SOURce{src}:FREQuency:CW {{}}Hz',
                vals=vals.Numbers()
            )
            self.add_parameter(
                name=f'freq_mode{src}',
                label=f'Source {src} frequency mode',
                get_cmd=f'SOURce{src}:FREQuency:MODE?',
                get_parser=str,
                set_cmd=f'SOURce{src}:FREQuency:MODE {{}}',
                vals=vals.Enum('CW', 'FIXed', 'FIX', 'SWEep', 'SWE')
            )
            self.add_parameter(
                name=f'freq_span{src}',
                label=f'Source {src} frequency span',
                unit='Hz',
                get_cmd=f'SOURce{src}:FREQuency:SPAN?',
                get_parser=float,
                set_cmd=f'SOURce{src}:FREQuency:SPAN {{}}Hz',
                vals=vals.Numbers()
            )
            self.add_parameter(
                name=f'freq_start{src}',
                label=f'Source {src} frequency start',
                unit='Hz',
                get_cmd=f'SOURce{src}:FREQuency:STARt?',
                get_parser=float,
                set_cmd=f'SOURce{src}:FREQuency:STARt {{}}Hz',
                vals=vals.Numbers()
            )
            self.add_parameter(
                name=f'freq_stop{src}',
                label=f'Source {src} frequency stop',
                unit='Hz',
                get_cmd=f'SOURce{src}:FREQuency:STOP?',
                get_parser=float,
                set_cmd=f'SOURce{src}:FREQuency:STOP {{}}Hz',
                vals=vals.Numbers()
            )

            # FSK modulation
            self.add_parameter(
                name=f'fsk_freq{src}',
                label=f'Source {src} FSK frequency',
                unit='Hz',
                get_cmd=f'SOURce{src}:FSKey:FREQuency?',
                get_parser=float,
                set_cmd=f'SOURce{src}:FSKey:FREQuency {{}}Hz',
                vals=vals.Numbers()
            )            
            self.add_parameter(
                name=f'fsk_internal_rate{src}',
                label=f'Source {src} FSK internal rate',
                unit='Hz',
                get_cmd=f'SOURce{src}:FSKey:INTernal:RATE?',
                get_parser=float,
                set_cmd=f'SOURce{src}:FSKey:INTernal:RATE {{}}Hz',
                vals=vals.Numbers()
            )
            self.add_parameter(
                name=f'fsk_source{src}',
                label=f'Source {src} FSK source',
                get_cmd=f'SOURce{src}:FSKey:SOURce?',
                get_parser=str,
                set_cmd=f'SOURce{src}:FSKey:SOURce {{}}',
                vals=vals.Enum('INTernal', 'INT', 'EXTernal', 'EXT')
            )
            self.add_parameter(
                name=f'fsk_state{src}',
                label=f'Source {src} FSK state',
                get_cmd=f'SOURce{src}:FSKey:STATe?',
                get_parser=lambda x: bool(int(x)),
                set_cmd=f'SOURce{src}:FSKey:STATe {{}}',
                vals=vals.Enum('OFF', 0, 'ON', 1)
            )

            # Function parameters
            self.add_parameter(
                name=f'function_efile{src}',
                label=f'Source {src} function efile',
                get_cmd=f'SOURce{src}:FUNCtion:EFILe?',
                get_parser=str,
                set_cmd=f'SOURce{src}:FUNCtion:EFILe {{}}',
                vals=vals.Strings()
            )
            self.add_parameter(
                name=f'function_ramp_symmetry{src}',
                label=f'Source {src} function ramp symmetry',
                unit='%',
                get_cmd=f'SOURce{src}:FUNCtion:RAMP:SYMMetry?',
                get_parser=float,
                set_cmd=f'SOURce{src}:FUNCtion:RAMP:SYMMetry {{}}PCT',
                vals=vals.Numbers(0, 100)
            )
            self.add_parameter(
                name=f'function_shape{src}',
                label=f'Source {src} function shape',
                get_cmd=f'SOURce{src}:FUNCtion:SHAPe?',
                get_parser=str,
                set_cmd=f'SOURce{src}:FUNCtion:SHAPe {{}}',
                vals=vals.Enum(
                'SINusoid', 'SIN',
                'SQUare',  'SQU',
                'TRIangle', 'TRI',
                'RAMP',
                'NRAMp', 'NRAM',
                'PRNoise', 'PRN',
                'USER', 'USER1', 'USER2', 'USER3', 'USER4',
                'EMEMory', 'EMEM',
                'EFILe', 'EFIL',
                'USER', 'USER1', 
                'USER2', 'USER3', 'USER4',
                'EMEMory', 'EMEM',
                'EFILe', 'EFIL')
            )

            # Phase parameters
            self.add_parameter(
                name=f'phase{src}',
                label=f'Source {src} phase',
                unit='degrees',
                get_cmd=f'SOURce{src}:PHASe:ADJust?',
                get_parser=float,
                set_cmd=f'SOURce{src}:PHASe:ADJust {{}}DEG',
                vals=vals.Numbers(-180, 180)
            )

            # Pulse parameters
            self.add_parameter(
                name=f'pulse_duty_cycle{src}',
                label=f'Source {src} pulse duty cycle',
                unit='%',
                get_cmd=f'SOURce{src}:PULSe:DCYCle?',
                get_parser=float,
                set_cmd=f'SOURce{src}:PULSe:DCYCle {{}}PCT',
                vals=vals.Numbers(1e-3, 99.999)
            )            
            self.add_parameter(
                name=f'pulse_delay{src}',
                label=f'Source {src} pulse delay',
                unit='s',
                get_cmd=f'SOURce{src}:PULSe:DELay?',
                get_parser=float,
                set_cmd=f'SOURce{src}:PULSe:DELay {{}}s',
                vals=vals.Numbers(min_value=0)
            )
            self.add_parameter(
                name=f'pulse_hold{src}',
                label=f'Source {src} pulse hold',
                get_cmd=f'SOURce{src}:PULSe:HOLD?',
                get_parser=str,
                set_cmd=f'SOURce{src}:PULSe:HOLD {{}}',
                vals=vals.Enum('WIDTh', 'WIDT', 'DUTY')
            )
            self.add_parameter(
                name=f'pulse_period{src}',
                label=f'Source {src} pulse period',
                unit='s',
                get_cmd=f'SOURce{src}:PULSe:PERiod?',
                get_parser=float,
                set_cmd=f'SOURce{src}:PULSe:PERiod {{}}s',
                vals=vals.Numbers()
            )
            self.add_parameter(
                name=f'pulse_trans_lead{src}',
                label=f'Source {src} pulse leading edge time',
                unit='s',
                get_cmd=f'SOURce{src}:PULSe:TRANsition:LEADing?',
                get_parser=float,
                set_cmd=f'SOURce{src}:PULSe:TRANsition:LEADing {{}}s',
                vals=vals.Numbers()
            )
            self.add_parameter(
                name=f'pulse_trans_trail{src}',
                label=f'Source {src} pulse trailing edge time',
                unit='s',
                get_cmd=f'SOURce{src}:PULSe:TRANsition:TRAiling?',
                get_parser=float,
                set_cmd=f'SOURce{src}:PULSe:TRANsition:TRAiling {{}}s',
                vals=vals.Numbers()
            )
            self.add_parameter(
                name=f'pulse_width{src}',
                label=f'Source {src} pulse width',
                unit='s',
                get_cmd=f'SOURce{src}:PULSe:WIDTh?',
                get_parser=float,
                set_cmd=f'SOURce{src}:PULSe:WIDTh {{}}s',
                vals=vals.Numbers()
            )

            # Sweep parameters
            self.add_parameter(
                name=f'sweep_hold_time{src}',
                label=f'Source {src} sweep hold time',
                unit='s',
                get_cmd=f'SOURce{src}:SWEep:HTIMe?',
                get_parser=float,
                set_cmd=f'SOURce{src}:SWEep:HTIMe {{}}s',
                vals=vals.Numbers()
            )            
            self.add_parameter(
                name=f'sweep_mode{src}',
                label=f'Source {src} sweep mode',
                get_cmd=f'SOURce{src}:SWEep:MODE?',
                get_parser=str,
                set_cmd=f'SOURce{src}:SWEep:MODE {{}}',
                vals=vals.Enum('AUTO', 'MANual', 'MAN')
            )
            self.add_parameter(
                name=f'sweep_return_time{src}',
                label=f'Source {src} sweep return time',
                unit='s',
                get_cmd=f'SOURce{src}:SWEep:RTIMe?',
                get_parser=float,
                set_cmd=f'SOURce{src}:SWEep:RTIMe {{}}s',
                vals=vals.Numbers()
            )                  
            self.add_parameter(
                name=f'sweep_spacing{src}',
                label=f'Source {src} sweep spacing',
                get_cmd=f'SOURce{src}:SWEep:SPACing?',
                get_parser=str,
                set_cmd=f'SOURce{src}:SWEep:SPACing {{}}',
                vals=vals.Enum('LINear', 'LIN', 'LOGarithmic', 'LOG')
            )
            self.add_parameter(
                name=f'sweep_time{src}',
                label=f'Source {src} sweep time',
                unit='s',
                get_cmd=f'SOURce{src}:SWEep:TIME?',
                get_parser=float,
                set_cmd=f'SOURce{src}:SWEep:TIME {{}}s',
                vals=vals.Numbers(1e-3, 300)
            )

            # Voltage parameters       
            self.add_parameter(
                name=f'voltage_concurrent{src}',
                label=f'Source {src} concurrent voltage',
                get_cmd=f'SOURce{src}:VOLTage:CONCurrent:STATe?',
                get_parser=lambda x: bool(int(x)),
                set_cmd=f'SOURce{src}:VOLTage:CONCurrent:STATe {{}}',
                vals=vals.Enum('OFF', 0, 'ON', 1)
            ) 
            self.add_parameter(
                name=f'voltage_high{src}',
                label=f'Source {src} high voltage level',
                unit='V',
                get_cmd=f'SOURce{src}:VOLTage:LEVel:IMMediate:HIGH?',
                get_parser=float,
                set_cmd=f'SOURce{src}:VOLTage:LEVel:IMMediate:HIGH {{}}V',
                vals=vals.Numbers()
            ) 
            self.add_parameter(
                name=f'voltage_low{src}',
                label=f'Source {src} low voltage level',
                unit='V',
                get_cmd=f'SOURce{src}:VOLTage:LEVel:IMMediate:LOW?',
                get_parser=float,
                set_cmd=f'SOURce{src}:VOLTage:LEVel:IMMediate:LOW {{}}V',
                vals=vals.Numbers()
            )
            self.add_parameter(
                name=f'voltage_offset{src}',
                label=f'Source {src} voltage offset',
                unit='V',
                get_cmd=f'SOURce{src}:VOLTage:LEVel:IMMediate:OFFSet?',
                get_parser=float,
                set_cmd=f'SOURce{src}:VOLTage:LEVel:IMMediate:OFFSet {{}}V',
                vals=vals.Numbers()
            )
            self.add_parameter(
                name=f'voltage_unit{src}',
                label=f'Source {src} voltage unit',
                get_cmd=f'SOURce{src}:VOLTage:UNIT?',
                get_parser=str,
                set_cmd=f'SOURce{src}:VOLTage:UNIT {{}}',
                vals=vals.Enum('VPP', 'VRMS', 'DBM')
            )
            self.add_parameter(
                name=f'voltage_amplitude{src}',
                label=f'Source {src} voltage amplitude',
                get_cmd=f'SOURce{src}:VOLTage:LEVel:IMMediate:AMPLitude?',
                get_parser=float,
                set_cmd=f'SOURce{src}:VOLTage:LEVel:IMMediate:AMPLitude {{}}V',
                vals=vals.Numbers()
            )
            self.add_parameter(
                name=f'voltage_limit_high{src}',
                label=f'Source {src} voltage limit high',
                unit='V',
                get_cmd=f'SOURce{src}:VOLTage:LIMit:HIGH?',
                get_parser=float,
                set_cmd=f'SOURce{src}:VOLTage:LIMit:HIGH {{}}V',
                vals=vals.Numbers()
            )
            self.add_parameter(
                name=f'voltage_limit_low{src}',
                label=f'Source {src} voltage limit low',
                unit='V',
                get_cmd=f'SOURce{src}:VOLTage:LIMit:LOW?',
                get_parser=float,
                set_cmd=f'SOURce{src}:VOLTage:LIMit:LOW {{}}V',
                vals=vals.Numbers()
            )

        # Noise parameters
        for src in [3, 4]:
            self.add_parameter(
                name=f'noise_level{src}',
                label=f'Source {src} relative noise level',
                unit='%',
                get_cmd=f'SOURce{src}:POWer:LEVel:IMMediate:AMPLitude?',
                get_parser=float,
                set_cmd=f'SOURce{src}:POWer:LEVel:IMMediate:AMPLitude {{}}PCT',
                vals=vals.Numbers(0, 50),
                docstring='Noise level applied to output, as a percentage of current amplitude.'
            )

        self.add_parameter(
            name='ref_osc_source',
            label='Reference clock source',
            get_cmd='SOURce:ROSCillator:SOURce?',
            get_parser=str,
            set_cmd='SOURce:ROSCillator:SOURce {}',
            vals=vals.Enum('INTernal', 'INT', 'EXTernal', 'EXT')
        )

        # Trigger parameters
        self.add_parameter(
            name='trigger_slope',
            label='Trigger slope',
            get_cmd='TRIGger:SEQuence:SLOPe?',
            get_parser=str,
            set_cmd='TRIGger:SEQuence:SLOPe {}',
            vals=vals.Enum('POSitive', 'POS', 'NEGative', 'NEG')
        )
        self.add_parameter(
            name='trigger_source',
            label='Trigger source',
            get_cmd='TRIGger:SEQuence:SOURce?',
            get_parser=str,
            set_cmd='TRIGger:SEQuence:SOURce {}',
            vals=vals.Enum('TIMer', 'TIM', 'EXTernal', 'EXT')
        )
        self.add_parameter(
            name='trigger_timer',
            label='Trigger timer period',
            unit='s',
            get_cmd='TRIGger:SEQuence:TIMer?',
            get_parser=float,
            set_cmd='TRIGger:SEQuence:TIMer {}s',
            vals=vals.Numbers(1e-6, 500)
        )

        self.snapshot(update=True)
        self.connect_message()

    def self_calibrate(self):
        self.write('CALibration:ALL')
        self.wait()

    def self_test(self):
        self.write('DIAGnostic:ALL')
        self.wait()

    def abort(self):
        self.write('ABORt')
        self.wait()

    def reset(self):
        log.info(f'Resetting {self.name}.')
        self.write('*RST')
        self.wait()

    def wait(self):
        self.write('*WAI')

    def save(self, location: int) -> None:
        if location not in [0, 1, 2, 3, 4]:
            raise ValueError(f'Location must be in {[0, 1, 2, 3, 4]}.')
        log.info(f'Instrument settings saved to location {location}.')
        self.write(f'*SAVE {location}')

    def recall(self, location: int) -> None:
        if location not in [0, 1, 2, 3, 4]:
            raise ValueError(f'Location must be in {[0, 1, 2, 3, 4]}.')
        log.info(f'Recalling instrument settings from location {location}.')
        self.write(f'*RCL {location}')

    def synchronize_phase(self, src: int) -> None:
        log.info('Synchronizing CH1 and CH2 phase.')
        self.write(f'SOURce{src}:PHASe:INITiate')

class AFG3252(AFG3000):
    pass
    
