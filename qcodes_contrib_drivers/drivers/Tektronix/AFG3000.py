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

        self.add_parameter('trigger_mode',
                label='Trigger mode',
                unit='',
                get_cmd='OUTPut:TRIGger:MODE?',
                get_parser=str,
                set_cmd='OUTPut:TRIGger:MODE {}',
                vals=vals.Enum('TRIGger', 'TRIG', 'SYNC')
        )

        # Source/output parameters, 2 channels
        for src in [1, 2]:

            # Outputs
            self.add_parameter('impedance_output{}'.format(src),
                   label='Output {} impedance'.format(src),
                   unit='Ohm',
                   get_cmd='OUTPut{}:IMPedance?'.format(src),
                   get_parser=float,
                   set_cmd='OUTPut{}:IMPedance {{}}'.format(src),
                   vals=vals.Strings()
            )
            self.add_parameter('polarity_output{}'.format(src),
                   label='Output {} polarity'.format(src),
                   unit='',
                   get_cmd='OUTPut{}:POLarity?'.format(src),
                   get_parser=str,
                   set_cmd='OUTPut{}:POLarity {{}}'.format(src),
                   vals=vals.Enum('NORMal', 'NORM', 'INVerted', 'INV')
            ) 
            self.add_parameter('state_output{}'.format(src),
                   label='Output {} state'.format(src),
                   unit='',
                   get_cmd='OUTPut{}:STATe?'.format(src),
                   get_parser=lambda x: bool(int(x)),
                   set_cmd='OUTPut{}:STATe {{}}'.format(src),
                   vals=vals.Enum('OFF', 0, 'ON', 1)
            )  

            # Amplitude modulation
            self.add_parameter('am_depth{}'.format(src),
                   label='Source {} AM depth'.format(src),
                   unit='%',
                   get_cmd='SOURce{}:AM:DEPTh?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:AM:DEPTh {{}}'.format(src),
                   vals=vals.Strings()
            )

            # Frequency modulation
            self.add_parameter('fm_deviation{}'.format(src),
                   label='Source {} FM deviation'.format(src),
                   unit='Hz',
                   get_cmd='SOURce{}:FM:DEViation?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:FM:DEViation {{}}'.format(src),
                   vals=vals.Strings()
            )

            # Phase modulation
            self.add_parameter('pm_deviation{}'.format(src),
                   label='Source {} PM deviation'.format(src),
                   unit='Radians',
                   get_cmd='SOURce{}:PM:DEViation?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:PM:DEViation {{}}'.format(src),
                   vals=vals.Strings()
            )

            # Pulse-width modulation
            self.add_parameter('pwm_duty_deviation{}'.format(src),
                   label='Source {} PWM duty cycle deviation'.format(src),
                   unit='%',
                   get_cmd='SOURce{}:PWM:DEViation:DCYCle?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:PWM:DEViation:DCYCle {{}}'.format(src),
                   vals=vals.Numbers(min_value=0, max_value=100)
            )

            # Amplitude, frequency, phase, and pulse-width modulation
            for mod_type in ['AM', 'FM', 'PM', 'PWM']:
                self.add_parameter('{}_internal_freq{}'.format(mod_type.lower(), src),
                       label='Source {} {} interal frequency'.format(src, mod_type),
                       unit='Hz',
                       get_cmd='SOURce{}:{}:INTernal:FREQuency?'.format(src, mod_type),
                       get_parser=float,
                       set_cmd='SOURce{}:{}:INTernal:FREQuency {{}}'.format(src, mod_type),
                       vals=vals.Strings()
                )              
                self.add_parameter('{}_internal_function{}'.format(mod_type.lower(), src),
                       label='Source {} {} interal function'.format(src, mod_type),
                       unit='',
                       get_cmd='SOURce{}:{}:INTernal:FUNCtion?'.format(src, mod_type),
                       get_parser=str,
                       set_cmd='SOURce{}:{}:INTernal:FUNCtion {{}}'.format(src, mod_type),
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
                self.add_parameter('{}_internal_efile{}'.format(mod_type.lower(), src),
                       label='Source {} {} interal EFile'.format(src, mod_type),
                       unit='',
                       get_cmd='SOURce{}:{}:INTernal:FUNCtion:EFILe?'.format(src, mod_type),
                       get_parser=str,
                       set_cmd='SOURce{}:{}:INTernal:FUNCtion:EFILe {{}}'.format(src, mod_type),
                       vals=vals.Strings()
                )
                self.add_parameter('{}_internal_source{}'.format(mod_type.lower(), src),
                       label='Source {} {} source'.format(src, mod_type),
                       unit='',
                       get_cmd='SOURce{}:{}:SOURce?'.format(src, mod_type),
                       get_parser=str,
                       set_cmd='SOURce{}:{}:SOURce? {{}}'.format(src, mod_type),
                       vals=vals.Enum('INTernal', 'INT', 'EXTernal', 'EXT')
                )
                self.add_parameter('{}_state{}'.format(mod_type.lower(), src),
                       label='Source {} {} interal state'.format(src, mod_type),
                       unit='',
                       get_cmd='SOURce{}:{}:STATe?'.format(src, mod_type),
                       get_parser=lambda x: bool(int(x)),
                       set_cmd='SOURce{}:{}:STATe {{}}'.format(src, mod_type),
                       vals=vals.Enum('OFF', 0, 'ON', 1)
                )

            # Burst mode
            self.add_parameter('burst_mode{}'.format(src),
                   label='Source {} burst mode'.format(src),
                   unit='',
                   get_cmd='SOURce{}:BURSt:MODE?'.format(src),
                   get_parser=str,
                   set_cmd='SOURce{}:BURSt:MODE {{}}'.format(src),
                   vals=vals.Enum('TRIGgered', 'TRIG', 'GATed', 'GAT')
            )
            self.add_parameter('burst_ncycles{}'.format(src),
                   label='Source {} burst N cycles'.format(src),
                   unit='',
                   get_cmd='SOURce{}:BURSt:NCYCles?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:BURSt:NCYCles {{}}'.format(src),
                   vals=vals.MultiType(
                        vals.Ints(min_value=1, max_value=1000000),
                        vals.Enum('INFinity', 'INF', 'MAXimum', 'MAX', 'MINimum', 'MIN'))
            )
            self.add_parameter('burst_state{}'.format(src),
                   label='Source {} burst state'.format(src),
                   unit='',
                   get_cmd='SOURce{}:BURSt:STATe?'.format(src),
                   get_parser=lambda x: bool(int(x)),
                   set_cmd='SOURce{}:BURSt:STATe {{}}'.format(src),
                   vals=vals.Enum('OFF', 0, 'ON', 1)
            )
            self.add_parameter('burst_tdelay{}'.format(src),
                   label='Source {} burst time delay'.format(src),
                   unit='s',
                   get_cmd='SOURce{}:BURSt:TDELay?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:BURSt:TDELay {{}}'.format(src),
                   vals=vals.Strings()
            )

            if src == 1:
                combine_enum = ('NOISe', 'NOIS', 'EXTernal', 'EXT', 'BOTH', '')
            else:
                combine_enum = ('NOISe', 'NOIS', '')
            self.add_parameter('combine{}'.format(src),
                   label='Source {} combine signals'.format(src),
                   unit='',
                   get_cmd='SOURce{}:COMBine:FEED?'.format(src),
                   get_parser=str,
                   set_cmd='SOURce{}:COMBine:FEED {{}}'.format(src),
                   vals=vals.Enum(combine_enum)
            ) 

            # Frequency controls                 
            self.add_parameter('center_freq{}'.format(src),
                   label='Source {} center frequency'.format(src),
                   unit='Hz',
                   get_cmd='SOURce{}:FREQuency:CENTer?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:FREQuency:CENTer {{}}'.format(src),
                   vals=vals.Strings()
            )
            self.add_parameter('freq_concurrent{}'.format(src),
                   label='Source {} concurrent frequency'.format(src),
                   unit='',
                   get_cmd='SOURce{}:FREQuency:CONCurrent?'.format(src),
                   get_parser=lambda x: bool(int(x)),
                   set_cmd='SOURce{}:FREQuency:CONCurrent {{}}'.format(src),
                   vals=vals.Enum('OFF', 0, 'ON', 1)
            ) 
            self.add_parameter('freq_cw{}'.format(src),
                   label='Source {} continuous frequency'.format(src),
                   unit='Hz',
                   get_cmd='SOURce{}:FREQuency:CW?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:FREQuency:CW {{}}'.format(src),
                   vals=vals.Strings()
            )
            self.add_parameter('freq_fixed{}'.format(src),
                   label='Source {} fixed frequency'.format(src),
                   unit='Hz',
                   get_cmd='SOURce{}:FREQuency:FIXed?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:FREQuency:FIXed {{}}'.format(src),
                   vals=vals.Strings()
            )
            self.add_parameter('freq_mode{}'.format(src),
                   label='Source {} frequency mode'.format(src),
                   unit='',
                   get_cmd='SOURce{}:FREQuency:MODE?'.format(src),
                   get_parser=str,
                   set_cmd='SOURce{}:FREQuency:MODE {{}}'.format(src),
                   vals=vals.Enum('CW', 'FIXed', 'FIX', 'SWEep', 'SWE')
            )
            self.add_parameter('freq_span{}'.format(src),
                   label='Source {} frequency span'.format(src),
                   unit='Hz',
                   get_cmd='SOURce{}:FREQuency:SPAN?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:FREQuency:SPAN {{}}'.format(src),
                   vals=vals.Strings()
            )
            self.add_parameter('freq_start{}'.format(src),
                   label='Source {} frequency start'.format(src),
                   unit='Hz',
                   get_cmd='SOURce{}:FREQuency:STARt?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:FREQuency:STARt {{}}'.format(src),
                   vals=vals.Strings()
            )
            self.add_parameter('freq_stop{}'.format(src),
                   label='Source {} frequency stop'.format(src),
                   unit='Hz',
                   get_cmd='SOURce{}:FREQuency:STOP?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:FREQuency:STOP {{}}'.format(src),
                   vals=vals.Strings()
            )

            # FSK modulation
            self.add_parameter('fsk_freq{}'.format(src),
                   label='Source {} FSK frequency'.format(src),
                   unit='Hz',
                   get_cmd='SOURce{}:FSKey:FREQuency?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:FSKey:FREQuency {{}}'.format(src),
                   vals=vals.Strings()
            )            
            self.add_parameter('fsk_internal_rate{}'.format(src),
                   label='Source {} FSK internal rate'.format(src),
                   unit='Hz',
                   get_cmd='SOURce{}:FSKey:INTernal:RATE?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:FSKey:INTernal:RATE {{}}'.format(src),
                   vals=vals.Strings()
            )
            self.add_parameter('fsk_source{}'.format(src),
                   label='Source {} FSK source'.format(src),
                   unit='',
                   get_cmd='SOURce{}:FSKey:SOURce?'.format(src),
                   get_parser=str,
                   set_cmd='SOURce{}:FSKey:SOURce {{}}'.format(src),
                   vals=vals.Enum('INTernal', 'INT', 'EXTernal', 'EXT')
            )
            self.add_parameter('fsk_state{}'.format(src),
                   label='Source {} FSK state'.format(src),
                   unit='',
                   get_cmd='SOURce{}:FSKey:STATe?'.format(src),
                   get_parser=lambda x: bool(int(x)),
                   set_cmd='SOURce{}:FSKey:STATe {{}}'.format(src),
                   vals=vals.Enum('OFF', 0, 'ON', 1)
            )

            # Function parameters
            self.add_parameter('function_efile{}'.format(src),
                   label='Source {} function efile'.format(src),
                   unit='',
                   get_cmd='SOURce{}:FUNCtion:EFILe?'.format(src),
                   get_parser=str,
                   set_cmd='SOURce{}:FUNCtion:EFILe {{}}'.format(src),
                   vals=vals.Strings()
            )
            self.add_parameter('function_ramp_symmetry{}'.format(src),
                   label='Source {} function ramp symmetry'.format(src),
                   unit='%',
                   get_cmd='SOURce{}:FUNCtion:RAMP:SYMMetry?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:FUNCtion:RAMP:SYMMetry {{}}'.format(src),
                   vals=vals.Numbers(min_value=0, max_value=100)
            )
            self.add_parameter('function_shape{}'.format(src),
                   label='Source {} function shape'.format(src),
                   unit='',
                   get_cmd='SOURce{}:FUNCtion:SHAPe?'.format(src),
                   get_parser=str,
                   set_cmd='SOURce{}:FUNCtion:SHAPe {{}}'.format(src),
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
            self.add_parameter('phase{}'.format(src),
                   label='Source {} phase'.format(src),
                   unit='Radians',
                   get_cmd='SOURce{}:PHASe:ADJust?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:PHASe:ADJust {{}}'.format(src),
                   vals=vals.Strings()
            )

            # Pulse parameters
            self.add_parameter('pulse_duty_cycle{}'.format(src),
                   label='Source {} pulse duty cycle'.format(src),
                   unit='%',
                   get_cmd='SOURce{}:PULSe:DCYCle?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:PULSe:DCYCle {{}}'.format(src),
                   vals=vals.Strings()
            )            
            self.add_parameter('pulse_delay{}'.format(src),
                   label='Source {} pulse delay'.format(src),
                   unit='s',
                   get_cmd='SOURce{}:PULSe:DELay?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:PULSe:DELay {{}}'.format(src),
                   vals=vals.Strings()
            )
            self.add_parameter('pulse_hold{}'.format(src),
                   label='Source {} pulse hold'.format(src),
                   unit='',
                   get_cmd='SOURce{}:PULSe:HOLD?'.format(src),
                   get_parser=str,
                   set_cmd='SOURce{}:PULSe:HOLD {{}}'.format(src),
                   vals=vals.Enum('WIDTh', 'WIDT', 'DUTY')
            )
            self.add_parameter('pulse_period{}'.format(src),
                   label='Source {} pulse period'.format(src),
                   unit='s',
                   get_cmd='SOURce{}:PULSe:PERiod?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:PULSe:PERiod {{}}'.format(src),
                   vals=vals.Strings()
            )
            self.add_parameter('pulse_trans_lead{}'.format(src),
                   label='Source {} pulse leading edge time'.format(src),
                   unit='s',
                   get_cmd='SOURce{}:PULSe:TRANsition:LEADing?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:PULSe:TRANsition:LEADing {{}}'.format(src),
                   vals=vals.Strings()
            )
            self.add_parameter('pulse_trans_trail{}'.format(src),
                   label='Source {} pulse trailing edge time'.format(src),
                   unit='s',
                   get_cmd='SOURce{}:PULSe:TRANsition:TRAiling?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:PULSe:TRANsition:TRAiling {{}}'.format(src),
                   vals=vals.Strings()
            )
            self.add_parameter('pulse_width{}'.format(src),
                   label='Source {} pulse width'.format(src),
                   unit='s',
                   get_cmd='SOURce{}:PULSe:WIDTh?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:PULSe:WIDTh {{}}'.format(src),
                   vals=vals.Strings()
            )

            # Sweep parameters
            self.add_parameter('sweep_hold_time{}'.format(src),
                   label='Source {} sweep hold time'.format(src),
                   unit='s',
                   get_cmd='SOURce{}:SWEep:HTIMe?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:SWEep:HTIMe {{}}'.format(src),
                   vals=vals.Strings()
            )            
            self.add_parameter('sweep_mode{}'.format(src),
                   label='Source {} sweep mode'.format(src),
                   unit='',
                   get_cmd='SOURce{}:SWEep:MODE?'.format(src),
                   get_parser=str,
                   set_cmd='SOURce{}:SWEep:MODE {{}}'.format(src),
                   vals=vals.Enum('AUTO', 'MANual', 'MAN')
            )
            self.add_parameter('sweep_return_time{}'.format(src),
                   label='Source {} sweep return time'.format(src),
                   unit='s',
                   get_cmd='SOURce{}:SWEep:RTIMe?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:SWEep:RTIMe {{}}'.format(src),
                   vals=vals.Strings()
            )                  
            self.add_parameter('sweep_spacing{}'.format(src),
                   label='Source {} sweep spacing'.format(src),
                   unit='',
                   get_cmd='SOURce{}:SWEep:SPACing?'.format(src),
                   get_parser=str,
                   set_cmd='SOURce{}:SWEep:SPACing {{}}'.format(src),
                   vals=vals.Enum('LINear', 'LIN', 'LOGarithmic', 'LOG')
            )
            self.add_parameter('sweep_time{}'.format(src),
                   label='Source {} sweep time'.format(src),
                   unit='s',
                   get_cmd='SOURce{}:SWEep:TIME?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:SWEep:TIME {{}}'.format(src),
                   vals=vals.Strings()
            )

            # Voltage parameters       
            self.add_parameter('voltage_concurrent{}'.format(src),
                   label='Source {} concurrent voltage'.format(src),
                   unit='',
                   get_cmd='SOURce{}:VOLTage:CONCurrent:STATe?'.format(src),
                   get_parser=lambda x: bool(int(x)),
                   set_cmd='SOURce{}:VOLTage:CONCurrent:STATe {{}}'.format(src),
                   vals=vals.Enum('OFF', 0, 'ON', 1)
            ) 
            self.add_parameter('voltage_high{}'.format(src),
                   label='Source {} high voltage level'.format(src),
                   unit='V',
                   get_cmd='SOURce{}:VOLTage:LEVel:IMMediate:HIGH?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:VOLTage:LEVel:IMMediate:HIGH {{}}'.format(src),
                   vals=vals.Strings()
            ) 
            self.add_parameter('voltage_low{}'.format(src),
                   label='Source {} low voltage level'.format(src),
                   unit='V',
                   get_cmd='SOURce{}:VOLTage:LEVel:IMMediate:LOW?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:VOLTage:LEVel:IMMediate:LOW {{}}'.format(src),
                   vals=vals.Strings()
            )
            self.add_parameter('voltage_offset{}'.format(src),
                   label='Source {} voltage offset'.format(src),
                   unit='V',
                   get_cmd='SOURce{}:VOLTage:LEVel:IMMediate:OFFSet?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:VOLTage:LEVel:IMMediate:OFFSet {{}}'.format(src),
                   vals=vals.Strings()
            )
            self.add_parameter('voltage_unit{}'.format(src),
                   label='Source {} voltage unit'.format(src),
                   unit='',
                   get_cmd='SOURce{}:VOLTage:UNIT?'.format(src),
                   get_parser=str,
                   set_cmd='SOURce{}:VOLTage:UNIT {{}}'.format(src),
                   vals=vals.Enum('VPP', 'VRMS', 'DBM')
            )
            self.add_parameter('voltage_amplitude{}'.format(src),
                   label='Source {} voltage amplitude'.format(src),
                   unit=getattr(self, 'voltage_unit{}'.format(src))(),
                   get_cmd='SOURce{}:VOLTage:LEVel:IMMediate:AMPLitude?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:VOLTage:LEVel:IMMediate:AMPLitude {{}}'.format(src),
                   vals=vals.Strings()
            )
            self.add_parameter('voltage_limit_high{}'.format(src),
                   label='Source {} voltage limit high'.format(src),
                   unit='V',
                   get_cmd='SOURce{}:VOLTage:LIMit:HIGH?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:VOLTage:LIMit:HIGH {{}}'.format(src),
                   vals=vals.Strings()
            )
            self.add_parameter('voltage_limit_low{}'.format(src),
                   label='Source {} voltage limit low'.format(src),
                   unit='V',
                   get_cmd='SOURce{}:VOLTage:LIMit:LOW?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:VOLTage:LIMit:LOW {{}}'.format(src),
                   vals=vals.Strings()
            )

        # Noise parameters
        for src in [3, 4]:
            self.add_parameter('noise_level{}'.format(src),
                   label='Source {} noise level'.format(src),
                   unit='%',
                   get_cmd='SOURce{}:POWer:LEVel:IMMediate:AMPLitude?'.format(src),
                   get_parser=float,
                   set_cmd='SOURce{}:POWer:LEVel:IMMediate:AMPLitude {{}}'.format(src),
                   vals=vals.Strings()
            )

        self.add_parameter('ref_osc_source',
               label='Reference clock source',
               unit='',
               get_cmd='SOURce:ROSCillator:SOURce?',
               get_parser=str,
               set_cmd='SOURce:ROSCillator:SOURce {}',
               vals=vals.Enum('INTernal', 'INT', 'EXTernal', 'EXT')
        )

        # Trigger parameters
        self.add_parameter('trigger_slope',
               label='Trigger slope',
               unit='',
               get_cmd='TRIGger:SEQuence:SLOPe?',
               get_parser=str,
               set_cmd='TRIGger:SEQuence:SLOPe {}',
               vals=vals.Enum('POSitive', 'POS', 'NEGative', 'NEG')
        )
        self.add_parameter('trigger_source',
               label='Trigger source',
               unit='',
               get_cmd='TRIGger:SEQuence:SOURce?',
               get_parser=str,
               set_cmd='TRIGger:SEQuence:SOURce {}',
               vals=vals.Enum('TIMer', 'TIM', 'EXTernal', 'EXT')
        )
        self.add_parameter('trigger_timer',
               label='Trigger timer period',
               unit='s',
               get_cmd='TRIGger:SEQuence:TIMer?',
               get_parser=float,
               set_cmd='TRIGger:SEQuence:TIMer {}',
               vals=vals.Strings()
        )

        self.snapshot(update=True)
        self.connect_message()

    def calibrate(self):
        self.write('CALibration:ALL')
        self.wait()

    def self_test(self):
        self.write('DIAGnostic:ALL')
        self.wait()

    def abort(self):
        self.write('ABORt')
        self.wait()

    def reset(self):
        log.info('Resetting {}.'.format(self.name))
        self.write('*RST')
        self.wait()

    def wait(self):
        self.write('*WAI')

    def save(self, location):
        if location not in [0, 1, 2, 3, 4]:
            raise ValueError('location must be in {}.'.format([0, 1, 2, 3, 4]))
        log.info('Instrument settings saved to location {}.'.format(location))
        self.write('*SAVE {}'.format(location))

    def recall(self, location):
        if location not in [0, 1, 2, 3, 4]:
            raise ValueError('location must be in {}.'.format([0, 1, 2, 3, 4]))
        log.info('Recalling instrument settings from location {}.'.format(location))
        self.write('*RCL {}'.format(location))

    def synchronize_phase(self, src: int) -> None:
        log.info('Synchronizing CH1 and CH2 phase.')
        self.write('SOURce{}:PHASe:INITiate'.format(src))

class AFG3252(AFG3000):
    pass