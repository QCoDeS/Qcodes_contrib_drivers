'''
Driver for Rohde Schwarz RTM3000 spectrum analyzer

Written by Ben Mowbray (http://wp.lancs.ac.uk/laird-group/)

Examples:

	***Setting up instrument and examples***

	$ from qcodes.instrument_drivers.RohdeSchwarz.RS_RTM3000 import RS_RTM3000
	$ rt_1 = RS_RTM3000('rtm_3000_1', 'USB0::0x0AAD::0x01D6::104022::0::INSTR')
	$ rt_1.general_channel.display_settings.language('ENGL') sets langauage of display
	$ rt_1.signal_generation_channel.pattern_general.function('SQU') sets function of general pattern

'''
from qcodes import VisaInstrument
from qcodes import validators as vals
from qcodes.instrument.channel import InstrumentChannel
from qcodes.instrument.base import Instrument

def _data_parser(msg: str):
	output=msg.split(',')
	length=int(output[0][1])
	output[0]=output[0][2+length:]
	return list(map(float,output))

class Common(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('cal',
							label='cal',
							get_cmd='*CAL?',
							get_parser=str.rstrip)

		self.add_parameter('ese',
							label='ese',
							set_cmd='*ESE {}',
							get_cmd='*ESE?',
							vals=vals.Numbers(0,255),
							get_parser=float)

		self.add_parameter('esr',
							label='esr',
							get_cmd='*ESR?',
							get_parser=float)

		self.add_parameter('idn',
							label='idn',
							get_cmd='*IDN?',
							get_parser=str.rstrip)

		self.add_parameter('opc',
							label='opc',
							set_cmd='*OPC',
							get_cmd='*OPC?',
							get_parser=str.rstrip)

		self.add_parameter('opt',
							label='opt',
							get_cmd='*OPT?',
							get_parser=str.rstrip)

		self.add_parameter('psc',
							label='psc',
							set_cmd='*PSC {}',
							get_cmd='*PSC?',
							vals=vals.Enum(0,1),
							get_parser=str.rstrip)

		self.add_parameter('sre',
							label='sre',
							set_cmd='*SRE {}',
							get_cmd='*SRE?',
							vals=vals.Numbers(0,255),
							get_parser=float)

		self.add_parameter('stb',
							label='stb',
							get_cmd='*STB?',
							get_parser=float)

	def cls(self): self.write('*CLS')
	def rst(self): self.write('*RST')
	def trg(self): self.write('*TRG')
	def wai(self): self.write('*WAI')

# Waveform setup

class Waveform_Setup_Channel(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		waveform_module=Waveform(self, 'waveform')
		self.add_submodule('waveform', waveform_module)

		horizontal_module=Horizontal(self, 'horizontal')
		self.add_submodule('horizontal', horizontal_module)

		'''for i in range(1,4+1):
			vertical_module=Vertical(self, f'wv{i}', i)
			self.add_submodule(f'wv{i}', vertical_module)

			probe_passive_module=Probe_Passive(self, f'passive_wv{i}', i)
			self.add_submodule(f'passive_wv{i}', probe_passive_module)

			probe_active_module=Probe_Active(self, f'active_wv{i}', i)
			self.add_submodule(f'active_wv{i}', probe_active_module)

			probe_meter_module=Probe_Meter(self, f'meter_wv{i}', i)
			self.add_submodule(f'meter_wv{i}', probe_meter_module)

			acquisition_module=Acquisition(self, f'acquisition_wv{i}', i)
			self.add_submodule(f'acquisition_wv{i}', acquisition_module)

			waveform_data_module=Waveform_Data(self, f'data_wv{i}', i)
			self.add_submodule(f'data_wv{i}', waveform_data_module)'''

class Acquisition(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, wavenum):
		super().__init__(parent, name)

		self.add_parameter('points_auto',
							label='automatic points acquisition',
							set_cmd='ACQuire:POINts:AUTomatic {}',
							get_cmd='ACQuire:POINts:AUTomatic?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('points',
							label='acquisition points',
							set_cmd='ACQuire:POINts:VALue {}',
							get_cmd='ACQuire:POINts:VALue?',
							vals=vals.Enum(5e3,10e3,20e3,50e3,100e3,200e3,500e3,1e6,2e6,5e6,10e6,20e6,40e6,80e6),
							unit='Samples',
							get_parser=float)

		self.add_parameter('channel_type',
							label=f'waveform {wavenum} channel type',
							set_cmd=f'CHANnel{wavenum}:TYPE {{}}',
							get_cmd=f'CHANnel{wavenum}:TYPE?',
							vals=vals.Enum('SAMP', 'PDET', 'HRES'),
							get_parser=str.rstrip)

		self.add_parameter('type',
							label='acquisition mode type',
							set_cmd='ACQuire:TYPE {}',
							get_cmd='ACQuire:TYPE?',
							vals=vals.Enum('REF', 'AVER', 'ENV'),
							get_parser=str.rstrip)

		self.add_parameter('arithmetics',
							label=f'waveform {wavenum} channel arithmetics',
							set_cmd=f'CHANnel{wavenum}:ARIThmetics {{}}',
							get_cmd=f'CHANnel{wavenum}:ARIThmetics?',
							vals=vals.Enum('OFF', 'ENV', 'AVER'),
							get_parser=str.rstrip)

		self.add_parameter('peak_detect',
							label='peak detect acquisition mode',
							set_cmd='ACQuire:PEAKdetect {}',
							get_cmd='ACQuire:PEAKdetect?',
							vals=vals.Enum('AUTO', 'OFF'),
							get_parser=str.rstrip)

		self.add_parameter('high_resolution',
							label='high resolution acquisition mode',
							set_cmd='ACQuire:HRESolution {}',
							get_cmd='ACQuire:HRESolution?',
							vals=vals.Enum('AUTO', 'OFF'),
							get_parser=str.rstrip)

		self.add_parameter('single_number',
							label='number of waveforms with run single',
							set_cmd='ACQuire:NSINgle:COUNt {}',
							get_cmd='ACQuire:NSINgle:COUNt?',
							vals=vals.Ints(1),
							get_parser=int)

		self.add_parameter('average_count',
							label='average waveform number of waveforms',
							set_cmd='ACQuire:AVERage:COUNt {}',
							get_cmd='ACQuire:AVERage:COUNt?',
							vals=vals.Numbers(2,100000),
							get_parser=float)

		self.add_parameter('average_complete',
							label='averaging state',
							get_cmd='ACQuire:AVERage:COMPlete?',
							get_parser=int)

		self.add_parameter('roll_automatic',
							label='timebase automatic roll mode',
							set_cmd='TIMebase:ROLL:AUTomatic {}',
							get_cmd='TIMebase:ROLL:AUTomatic?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('roll_min',
							label='roll minimum time base',
							set_cmd='TIMebase:ROLL:MTIMe {}',
							get_cmd='TIMebase:ROLL:MTIMe?',
							vals=vals.Numbers(500e-3),
							unit='s/div',
							get_parser=float)

		self.add_parameter('interpolate',
							label='acquisition interpolation mode',
							set_cmd='ACQuire:INTerpolate {}',
							get_cmd='ACQuire:INTerpolate?',
							vals=vals.Enum('SINX', 'LIN', 'SMHD'),
							get_parser=str.rstrip)

		self.add_parameter('ADC_rate',
							label='ADC sample rate',
							get_cmd='ACQuire:POINts:ARATe?',
							get_parser=float)

		self.add_parameter('sample_rate',
							label='sample rate',
							get_cmd='ACQuire:SRATe?',
							get_parser=float)

	def average_reset(self): self.write('ACQuire:AVERage:RESet')

class Horizontal(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('scale',
							label='timebase scale',
							set_cmd='TIMebase:SCALe {}',
							get_cmd='TIMebase:SCALe?',
							vals=vals.Numbers(1e-9,50),
							unit='s/div',
							get_parser=float)

		self.add_parameter('position',
							label='timebase position',
							set_cmd='TIMebase:POSition {}',
							get_cmd='TIMebase:POSition?',
							vals=vals.Numbers(),
							unit='s',
							get_parser=float)

		self.add_parameter('reference',
							label='timebase reference',
							set_cmd='TIMebase:REFerence {}',
							get_cmd='TIMebase:REFerence?',
							vals=vals.Enum(8.33,50,91.67),
							unit='%',
							get_parser=float)

		self.add_parameter('acquisition_time',
							label='timebase acquisition time',
							set_cmd='TIMebase:ACQTime {}',
							get_cmd='TIMebase:ACQTime?',
							vals=vals.Numbers(250e-12,500),
							unit='s',
							get_parser=float)

		self.add_parameter('range',
							label='timebase acquisition time',
							set_cmd='TIMebase:RANGe {}',
							get_cmd='TIMebase:RANGe?',
							vals=vals.Numbers(250e-12,500),
							unit='s',
							get_parser=float)

		self.add_parameter('divisions',
							label='timebase divisions',
							get_cmd='TIMebase:DIVisions?',
							get_parser=str.rstrip)

		self.add_parameter('real_time',
							label='timebase real acquision time',
							get_cmd='TIMebase:RATime?',
							get_parser=float)

class Probe_Active(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, wavenum):
		super().__init__(parent, name)

		self.add_parameter('setup_mode',
							label=f'waveform {wavenum} setup mode',
							set_cmd=f'PROBe{wavenum}:SETup:MODE {{}}',
							get_cmd=f'PROBe{wavenum}:SETup:MODE?',
							vals=vals.Enum('RCON', 'RSIN', 'AUT', 'NOAC'),
							get_parser=str.rstrip)

		self.add_parameter('ID_build',
							label=f'waveform {wavenum} build ID',
							get_cmd=f'PROBe{wavenum}:ID:BUILd?',
							get_parser=int)

		self.add_parameter('ID_partnumber',
							label=f'waveform {wavenum} part number ID',
							get_cmd=f'PROBe{wavenum}:ID:PARTnumber?',
							get_parser=str.rstrip)

		self.add_parameter('ID_prdate',
							label=f'waveform {wavenum} production date',
							get_cmd=f'PROBe{wavenum}:ID:PRDate?',
							get_parser=str.rstrip)

		self.add_parameter('ID_srnumber',
							label=f'waveform {wavenum} serial number',
							get_cmd=f'PROBe{wavenum}:ID:SRNumber?',
							get_parser=str.rstrip)

		self.add_parameter('ID_swversion',
							label=f'waveform {wavenum} firmware version',
							get_cmd=f'PROBe{wavenum}:ID:SRNumber?',
							get_parser=str.rstrip)

		self.add_parameter('setup_type',
							label=f'waveform {wavenum} setup type',
							get_cmd=f'PROBe{wavenum}:SETup:TYPE?',
							get_parser=str.rstrip)

		self.add_parameter('setup_name',
							label=f'waveform {wavenum} setup name',
							get_cmd=f'PROBe{wavenum}:SETup:NAME?',
							get_parser=str.rstrip)

		self.add_parameter('setup_bandwidth',
							label=f'waveform {wavenum} setup bandwidth',
							get_cmd=f'PROBe{wavenum}:SETup:BANDwidth?',
							get_parser=float)

		self.add_parameter('auto_attenuation',
							label=f'waveform {wavenum} setup auto attenuation',
							get_cmd=f'PROBe{wavenum}:SETup:ATTenuation:AUTO?',
							get_parser=float)

		self.add_parameter('auto_gain',
							label=f'waveform {wavenum} setup auto gain',
							get_cmd=f'PROBe{wavenum}:SETup:GAIN:AUTO?',
							get_parser=float)

		self.add_parameter('setup_capacitance',
							label=f'waveform {wavenum} setup capacitance',
							get_cmd=f'PROBe{wavenum}:SETup:CAPacitance?',
							get_parser=float)

		self.add_parameter('setup_impedance',
							label=f'waveform {wavenum} setup impednace',
							get_cmd=f'PROBe{wavenum}:SETup:IMPedance?',
							get_parser=str.rstrip)

		self.add_parameter('advanced_zero_adjust',
							label=f'waveform {wavenum} advanced zero adjust',
							set_cmd=f'PROBe{wavenum}:SETup:ADVanced:ZADJust {{}}',
							get_cmd=f'PROBe{wavenum}:SETup:ADVanced:ZADJust?',
							vals=vals.Numbers(-100,100),
							unit='%',
							get_parser=float)

		self.add_parameter('pr_mode',
							label=f'waveform {wavenum} setup pr mode',
							set_cmd=f'PROBe{wavenum}:SETup:PRMode {{}}',
							get_cmd=f'PROBe{wavenum}:SETup:PRMode?',
							vals=vals.Enum('DMOD', 'CMOD', 'PMOD', 'NMOD'),
							get_parser=str.rstrip)

		self.add_parameter('setup_zaxv',
							label=f'waveform {wavenum} setup zaxv',
							set_cmd=f'PROBe{wavenum}:SETup:ZAXV {{}}',
							get_cmd=f'PROBe{wavenum}:SETup:ZAXV?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('audio_overload',
							label=f'waveform {wavenum} setup advanced audio overload',
							set_cmd=f'PROBe{wavenum}:SETup:ADVanced:AUDioverload {{}}',
							get_cmd=f'PROBe{wavenum}:SETup:ADVanced:AUDioverload?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('advanced_filter',
							label=f'waveform {wavenum} setup advanced filter',
							set_cmd=f'PROBe{wavenum}:SETup:ADVanced:FILTer {{}}',
							get_cmd=f'PROBe{wavenum}:SETup:ADVanced:FILTer?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('advanced_range',
							label=f'waveform {wavenum} setup advanced range',
							set_cmd=f'PROBe{wavenum}:SETup:ADVanced:RANGe {{}}',
							get_cmd=f'PROBe{wavenum}:SETup:ADVanced:RANGe?',
							vals=vals.Enum('AUTO', 'MHIG', 'MLOW'),
							get_parser=str.rstrip)

		self.add_parameter('AC_coupling',
							label=f'waveform {wavenum} setup AC coupling',
							set_cmd=f'PROBe{wavenum}:SETup:ACCoupling {{}}',
							get_cmd=f'PROBe{wavenum}:SETup:ACCoupling?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

	def advanced_PMT(self): self.write(f'PROBe{wavenum}:SETup:ADVanced:PMToffset')
	def setup_degauss(self): self.write(f'PROBe{wavenum}:SETup:DEGauss')
	def advanced_ST_probe(self): self.write(f'PROBe{wavenum}:SETup:ADVanced:STPRobe')

class Probe_Meter(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, wavenum):
		super().__init__(parent, name)

		self.add_parameter('visibility',
							label=f'waveform {wavenum} probemeter visibility',
							set_cmd=f'PROBe{wavenum}:PMETer:VISibility {{}}',
							get_cmd=f'PROBe{wavenum}:PMETer:VISibility?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('off_switch',
							label=f'waveform {wavenum} setup off switch',
							set_cmd=f'PROBe{wavenum}:SETup:OFFSwitch {{}}',
							get_cmd=f'PROBe{wavenum}:SETup:OFFSwitch?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('DC_offset',
							label=f'waveform {wavenum} setup DC offset',
							get_cmd=f'PROBe{wavenum}:SETup:DCOFfset?',
							get_parser=str.rstrip)

		self.add_parameter('results_single',
							label=f'waveform {wavenum} probemeter single results',
							get_cmd=f'PROBe{wavenum}:PMETer:RESults:SINGle?',
							get_parser=str.rstrip)

		self.add_parameter('results_common',
							label=f'waveform {wavenum} probemeter common results',
							get_cmd=f'PROBe{wavenum}:PMETer:RESults:COMMon?',
							get_parser=float)

		self.add_parameter('results_differential',
							label=f'waveform {wavenum} probemeter differential results',
							get_cmd=f'PROBe{wavenum}:PMETer:RESults:DIFFerential?',
							get_parser=float)

		self.add_parameter('results_negative',
							label=f'waveform {wavenum} probemeter negative results',
							get_cmd=f'PROBe{wavenum}:PMETer:RESults:NEGative?',
							get_parser=float)

		self.add_parameter('results_positive',
							label=f'waveform {wavenum} probemeter positive results',
							get_cmd=f'PROBe{wavenum}:PMETer:RESults:POSitive?',
							get_parser=float)

class Probe_Passive(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, wavenum):
		super().__init__(parent, name)

		self.add_parameter('attenutation_unit',
							label=f'waveform {wavenum} attenuation unit',
							set_cmd=f'PROBe{wavenum}:SETup:ATTenuation:UNIT {{}}',
							get_cmd=f'PROBe{wavenum}:SETup:ATTenuation:UNIT?',
							vals=vals.Enum('V', 'A'),
							get_parser=str.rstrip)

		self.add_parameter('attenuation_manual',
							label=f'waveform {wavenum} attenuation manual',
							set_cmd=f'PROBe{wavenum}:SETup:ATTenuation:MANual {{}}',
							get_cmd=f'PROBe{wavenum}:SETup:ATTenuation:MANual?',
							vals=vals.Numbers(0.0001,10e6),
							get_parser=float)

		self.add_parameter('gain_unit',
							label=f'waveform {wavenum} gain unit',
							set_cmd=f'PROBe{wavenum}:SETup:GAIN:UNIT {{}}',
							get_cmd=f'PROBe{wavenum}:SETup:GAIN:UNIT?',
							vals=vals.Enum('V', 'A'),
							get_parser=str.rstrip)

		self.add_parameter('gain_manual',
							label=f'waveform {wavenum} gain manual',
							set_cmd=f'PROBe{wavenum}:SETup:GAIN:MANual {{}}',
							get_cmd=f'PROBe{wavenum}:SETup:GAIN:MANual?',
							vals=vals.Numbers(0.0001,10000),
							get_parser=float)

class Vertical(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, wavenum):
		super().__init__(parent, name)

		self.add_parameter('state',
							label=f'waveform {wavenum} signal state',
							set_cmd=f'CHANnel{wavenum}:STATe {{}}',
							get_cmd=f'CHANnel{wavenum}:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('scale',
							label=f'waveform {wavenum} scale',
							set_cmd=f'CHANnel{wavenum}:SCALe {{}}',
							get_cmd=f'CHANnel{wavenum}:SCALe?',
							vals=vals.Numbers(1e-3,10),
							unit='V/div',
							get_parser=float)

		self.add_parameter('range',
							label=f'waveform {wavenum} range',
							set_cmd=f'CHANnel{wavenum}:RANGe {{}}',
							get_cmd=f'CHANnel{wavenum}:RANGe?',
							vals=vals.Numbers(8e-3,80),
							unit='V',
							get_parser=float)

		self.add_parameter('position',
							label=f'waveform {wavenum} position',
							set_cmd=f'CHANnel{wavenum}:POSition {{}}',
							get_cmd=f'CHANnel{wavenum}:POSition?',
							vals=vals.Ints(-5,5),
							unit='div',
							get_parser=int)

		self.add_parameter('offset',
							label=f'waveform {wavenum} offset',
							set_cmd=f'CHANnel{wavenum}:OFFSet {{}}',
							get_cmd=f'CHANnel{wavenum}:OFFSet?',
							unit='V',
							get_parser=float)

		self.add_parameter('coupling',
							label=f'waveform {wavenum} coupling',
							set_cmd=f'CHANnel{wavenum}:COUPling {{}}',
							get_cmd=f'CHANnel{wavenum}:COUPling?',
							vals=vals.Enum('DCL', 'ACL', 'GND', 'DC'),
							get_parser=str.rstrip)

		self.add_parameter('bandwidth',
							label=f'waveform {wavenum} bandwidth',
							set_cmd=f'CHANnel{wavenum}:BANDwidth {{}}',
							get_cmd=f'CHANnel{wavenum}:BANDwidth?',
							vals=vals.Enum('FULL', 'B20'),
							get_parser=str.rstrip)

		self.add_parameter('polarity',
							label=f'waveform {wavenum} polarity',
							set_cmd=f'CHANnel{wavenum}:POLarity {{}}',
							get_cmd=f'CHANnel{wavenum}:POLarity?',
							vals=vals.Enum('NORM' 'INV'),
							get_parser=str.rstrip)

		self.add_parameter('skew',
							label=f'waveform {wavenum} skew',
							set_cmd=f'CHANnel{wavenum}:SKEW {{}}',
							get_cmd=f'CHANnel{wavenum}:SKEW?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('offset_zero',
							label=f'waveform {wavenum} zero offset',
							set_cmd=f'CHANnel{wavenum}:ZOFFset:VALue {{}}',
							get_cmd=f'CHANnel{wavenum}:ZOFFset:VALue?',
							vals=vals.Numbers(),
							unit='V',
							get_parser=float)

		self.add_parameter('waveform_color',
							label=f'waveform {wavenum} color',
							set_cmd=f'CHANnel{wavenum}:WCOLor {{}}',
							get_cmd=f'CHANnel{wavenum}:WCOLor?',
							vals=vals.Enum('TEMP', 'RAIN', 'FIRE', 'DEF'),
							get_parser=str.rstrip)

		self.add_parameter('overload',
							label=f'waveform {wavenum} overload',
							set_cmd=f'CHANnel{wavenum}:OVERload {{}}',
							get_cmd=f'CHANnel{wavenum}:OVERload?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('threshold',
							label=f'waveform {wavenum} threshold',
							set_cmd=f'CHANnel{wavenum}:THReshold {{}}',
							get_cmd=f'CHANnel{wavenum}:THReshold?',
							vals=vals.Numbers(),
							unit='V',
							get_parser=float)

		self.add_parameter('threshold_hysteresis',
							label=f'waveform {wavenum} threshold hysteresis',
							set_cmd=f'CHANnel{wavenum}:THReshold:HYSTeresis {{}}',
							get_cmd=f'CHANnel{wavenum}:THReshold:HYSTeresis?',
							vals=vals.Enum('SMAL', 'MED', 'LARG'),
							get_parser=str.rstrip)

		self.add_parameter('label',
							label=f'waveform {wavenum} label',
							set_cmd=f'CHANnel{wavenum}:LABel {{}}',
							get_cmd=f'CHANnel{wavenum}:LABel?',
							vals=vals.Strings(1,8),
							get_parser=str.rstrip)

		self.add_parameter('label_state',
							label=f'waveform {wavenum} label state',
							set_cmd=f'CHANnel{wavenum}:LABel:STATe {{}}',
							get_cmd=f'CHANnel{wavenum}:LABel:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

	def findlevel(self): self.write(f'CHANnel{wavenum}:THReshold:FINDlevel')

	def analog_on(self): self.write(f'CHANnel{wavenum}:AON')
	def analog_off(self): self.write(f'CHANnel{wavenum}:AOFF')

class Waveform(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('acquisition_count',
							label='number of acquisitions',
							set_cmd='ACQuire:NSINgle:COUNt {}',
							get_cmd='ACQuire:NSINgle:COUNt?',
							vals=vals.Ints(1),
							get_parser=int)

		self.add_parameter('acquisition_state',
							label='acquisition state',
							set_cmd='ACQuire:STATe {}',
							get_cmd='ACQuire:STATe?',
							vals=vals.Enum('RUN', 'STOP', 'COMP', 'BRE'),
							get_parser=str.rstrip)

	def auto(self): self.write('AUToscale')
	def run(self): self.write('RUN')
	def runcont(self): self.write('RUNContinous')
	def single(self): self.write('SINGle')
	def runsingle(self): self.write('RUNSingle')
	def stop(self): self.write('STOP')

class Waveform_Data(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, wavenum):
		super().__init__(parent, name)

		self.add_parameter('_data_format',
							label='data format for export',
							set_cmd='FORMat:DATA {}',
							get_cmd='FORMat:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('byte_order',
							label='byte order for export',
							set_cmd='FORMat:BORDer {}',
							get_cmd='FORMat:BORDer?',
							vals=vals.Enum('MSBF', 'LSBF'),
							get_parser=str.rstrip)

		self.add_parameter('channel_data',
							label=f'waveform {wavenum} data',
							get_cmd=f'CHANnel{wavenum}:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('data_header',
							label=f'waveform {wavenum} data header',
							get_cmd=f'CHANnel{wavenum}:DATA:HEADer?',
							get_parser=str.rstrip)

		self.add_parameter('data_points',
							label=f'waveform {wavenum} data points',
							set_cmd=f'CHANnel{wavenum}:DATA:POINts {{}}',
							get_cmd=f'CHANnel{wavenum}:DATA:POINts?',
							vals=vals.Enum('DEF', 'MAX', 'DMAX'),
							get_parser=str.rstrip)

		self.add_parameter('data_envelope',
							label=f'waveform {wavenum} data envelope',
							get_cmd=f'CHANnel{wavenum}:DATA:ENVelope?',
							get_parser=str.rstrip)

		self.add_parameter('envelope_header',
							label=f'waveform {wavenum} data envelope header',
							get_cmd=f'CHANnel{wavenum}:DATA:ENVelope:HEADer?',
							get_parser=str.rstrip)

	def data_format(self, dataformat, accuracy):
		'''
		Data format parameter wrapper
		Args:
			format
			accuracy
		'''
		vals.Enum('ASC', 'REAL', 'UINT').validate(dataformat)
		vals.Enum(0,8,16,32).validate(accuracy)
		input=f'{dataformat}, {accuracy}'
		self._data_format(input)

# Trigger

class Trigger_Channel(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		trigger_module=Trigger(self, 'trigger')
		self.add_submodule('trigger', trigger_module)

		edge_AB_module=Edge_AB(self, 'edgeab')
		self.add_submodule('edgeab', edge_AB_module)

		event_module=Event(self, 'event')
		self.add_submodule('event', event_module)

		width_module=Width(self, 'width')
		self.add_submodule('width', width_module)

		pattern_module=Pattern(self, 'pattern')
		self.add_submodule('pattern', pattern_module)

		timeout_module=Timeout(self, 'timeout')
		self.add_submodule('timeout', timeout_module)

		video_module=Video(self, 'video')
		self.add_submodule('video', video_module)

		'''for i in range(1,5+1):
			edge_module=Edge(self, f'edge_lv{i}', i)
			self.add_submodule(f'edge_lv{i}', edge_module)

			risetime_module=Risetime(self, f'risetime_v{i}', i)
			self.add_submodule(f'risetime_lv{i}', risetime_module)

			runt_module=Runt(self, f'runt_lv{i}', i)
			self.add_submodule(f'runt_lv{i}', runt_module)'''

class Edge(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, levnum):
		super().__init__(parent, name)

		self.add_parameter('slope',
							label='edge trigger slope',
							set_cmd='TRIGger:A:EDGE:SLOPe {}',
							get_cmd='TRIGger:A:EDGE:SLOPe?',
							vals=vals.Enum('POS', 'NEG', 'EITH'),
							get_parser=str.rstrip)

		self.add_parameter('level',
							label=f'level {levnum} trigger level value',
							set_cmd=f'TRIGger:A:LEVel{levnum}:VALue {{}}',
							get_cmd=f'TRIGger:A:LEVel{levnum}:VALue?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('coupling',
							label='edge trigger coupling',
							set_cmd='TRIGger:A:EDGE:COUPling {}',
							get_cmd='TRIGger:A:EDGE:COUPling?',
							vals=vals.Enum('DC', 'AC', 'LFR'),
							get_parser=str.rstrip)

		self.add_parameter('hysteresis',
							label='edge trigger hysteresis',
							set_cmd='TRIGger:A:HYSTeresis {}',
							get_cmd='TRIGger:A:HYSTeresis?',
							vals=vals.Enum('AUTO', 'SMAL', 'MED', 'LARGE'),
							get_parser=str.rstrip)

		self.add_parameter('high_reject',
							label='high frequency reject filter',
							set_cmd='TRIGger:A:EDGE:FILTer:HFReject {}',
							get_cmd='TRIGger:A:EDGE:FILTer:HFReject?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('aditional_reject',
							label='additional lowpass filter',
							set_cmd='TRIGger:A:EDGE:FILTer:NREJect {}',
							get_cmd='TRIGger:A:EDGE:FILTer:NREJect?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		

	def find_level(self): self.write('TRIGger:A:FINDleve')

class Edge_AB(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('b_enable',
							label='B-trigger state',
							set_cmd='TRIGger:B:ENABle {}',
							get_cmd='TRIGger:B:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('b_source',
							label='B-trigger source',
							set_cmd='TRIGger:B:SOURce {}',
							get_cmd='TRIGger:B:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15'),
							get_parser=str.rstrip)

		self.add_parameter('b_slope',
							label='B-trigger slope',
							set_cmd='TRIGger:B:EDGE:SLOPe {}',
							get_cmd='TRIGger:B:EDGE:SLOPe?',
							vals=vals.Enum('POS', 'NEG', 'EITH'),
							get_parser=str.rstrip)

		self.add_parameter('b_mode',
							label='B-trigger mode',
							set_cmd='TRIGger:B:MODE {}',
							get_cmd='TRIGger:B:MODE?',
							vals=vals.Enum('DEL', 'EVEN'),
							get_parser=str.rstrip)

		self.add_parameter('b_delay',
							label='B-trigger delay',
							set_cmd='TRIGger:B:DELay {}',
							get_cmd='TRIGger:B:DELay?',
							vals=vals.Numbers(20e-9,6.871946854),
							unit='s',
							get_parser=float)

		self.add_parameter('b_count',
							label='B-trigger count',
							set_cmd='TRIGger:B:EVENt:COUNt {}',
							get_cmd='TRIGger:B:EVENt:COUNt?',
							vals=vals.Ints(1,65535),
							get_parser=int)

class Event(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('sound',
							label='sound state',
							set_cmd='TRIGger:EVENt:SOUNd {}',
							get_cmd='TRIGger:EVENt:SOUNd?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('reference_save',
							label='reference save status',
							set_cmd='TRIGger:EVENt:REFSave {}',
							get_cmd='TRIGger:EVENt:REFSave?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('screenshot',
							label='screenshot status',
							set_cmd='TRIGger:EVENt:SCRSave {}',
							get_cmd='TRIGger:EVENt:SCRSave?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('screenshot_destination',
							label='screenshot save destination',
							set_cmd='TRIGger:EVENt:SCRSave:DESTination {}',
							get_cmd='TRIGger:EVENt:SCRSave:DESTination?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('trigger_out',
							label='trigger out',
							set_cmd='TRIGger:EVENt:TRIGgerout {}',
							get_cmd='TRIGger:EVENt:TRIGgerout?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('waveform_save',
							label='trigger save waveform',
							set_cmd='TRIGger:EVENt:WFMSave {}',
							get_cmd='TRIGger:EVENt:WFMSave?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('waveform_destination',
							label='waveform save destination',
							set_cmd='TRIGger:EVENt:WFMSave:DESTination {}',
							get_cmd='TRIGger:EVENt:WFMSave:DESTination?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

class Pattern(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('source',
							label='trigger pattern source',
							set_cmd='TRIGger:A:PATTern:SOURce {}',
							get_cmd='TRIGger:A:PATTern:SOURce?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('function',
							label='trigger pattern function',
							set_cmd='TRIGger:A:PATTern:FUNCtion {}',
							get_cmd='TRIGger:A:PATTern:FUNCtion?',
							vals=vals.Enum('AND', 'OR'),
							get_parser=str.rstrip)
					
		self.add_parameter('condition',
							label='trigger pattern condition',
							set_cmd='TRIGger:A:PATTern:CONDition {}',
							get_cmd='TRIGger:A:PATTern:CONDition?',
							vals=vals.Enum('""TRUE""', '""FALSE""'),
							get_parser=str.rstrip)

		self.add_parameter('mode',
							label='trigger pattern mode',
							set_cmd='TRIGger:A:PATTern:MODE {}',
							get_cmd='TRIGger:A:PATTern:MODE?',
							vals=vals.Enum('OFF', 'TIM', 'WIDT'),
							get_parser=str.rstrip)

		self.add_parameter('width_range',
							label='trigger pattern width range',
							set_cmd='TRIGger:A:PATTern:WIDTh:RANGe {}',
							get_cmd='TRIGger:A:PATTern:WIDTh:RANGe?',
							vals=vals.Enum('WITH', 'OUTS', 'SHOR', 'LONG'),
							get_parser=str.rstrip)

		self.add_parameter('width',
							label='trigger pattern width width',
							set_cmd='TRIGger:A:PATTern:WIDTh:WIDTh {}',
							get_cmd='TRIGger:A:PATTern:WIDTh:WIDTh?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('width_delta',
							label='trigger pattern width range',
							set_cmd='TRIGger:A:PATTern:WIDTh:DELTa {}',
							get_cmd='TRIGger:A:PATTern:WIDTh:DELTa?',
							vals=vals.Numbers(),
							get_parser=float)

class Risetime(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, levnum):
		super().__init__(parent, name)

		self.add_parameter('lower',
							label=f'level {levnum} trigger level risetime lower',
							set_cmd=f'TRIGger:A:LEVel{levnum}:RISetime:LOWer {{}}',
							get_cmd=f'TRIGger:A:LEVel{levnum}:RISetime:LOWer?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('upper',
							label=f'level {levnum} trigger level risetime upper',
							set_cmd=f'TRIGger:A:LEVel{levnum}:RISetime:UPPer {{}}',
							get_cmd=f'TRIGger:A:LEVel{levnum}:RISetime:UPPer?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('delta',
							label='trigger risetime delta time',
							set_cmd='TRIGger:A:RISetime:DELTa {}',
							get_cmd='TRIGger:A:RISetime:DELTa?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('range',
							label='trigger risetime range',
							set_cmd='TRIGger:A:RISetime:RANGe {}',
							get_cmd='TRIGger:A:RISetime:RANGe?',
							vals=vals.Enum('LONG', 'SHOR', 'WITH', 'OUTS'),
							get_parser=str.rstrip)

		self.add_parameter('slope',
							label='trigger risetime slope',
							set_cmd='TRIGger:A:RISetime:SLOPe {}',
							get_cmd='TRIGger:A:RISetime:SLOPe?',
							vals=vals.Enum('POS', 'NEG'),
							get_parser=str.rstrip)

		self.add_parameter('time',
							label='trigger risetime time',
							set_cmd='TRIGger:A:RISetime:TIME {}',
							get_cmd='TRIGger:A:RISetime:TIME?',
							vals=vals.Numbers(),
							get_parser=float)

class Runt(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, levnum):
		super().__init__(parent, name)

		self.add_parameter('lower',
							label=f'level {levnum} lower voltage threshold',
							set_cmd=f'TRIGger:A:LEVel{levnum}:RUNT:LOWer {{}}',
							get_cmd=f'TRIGger:A:LEVel{levnum}:RUNT:LOWer?',
							vals=vals.Numbers(),
							get_parser=float)
							
		self.add_parameter('upper',
							label=f'level {levnum} upper voltage threshold',
							set_cmd=f'TRIGger:A:LEVel{levnum}:RUNT:UPPer {{}}',
							get_cmd=f'TRIGger:A:LEVel{levnum}:RUNT:UPPer?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('delta',
							label='trigger runt delta',
							set_cmd='TRIGger:A:RUNT:DELTa {}',
							get_cmd='TRIGger:A:RUNT:DELTa?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('polarity',
							label='trigger runt polarity',
							set_cmd='TRIGger:A:RUNT:POLarity {}',
							get_cmd='TRIGger:A:RUNT:POLarity?',
							vals=vals.Enum('POS', 'NEG'),
							get_parser=str.rstrip)

		self.add_parameter('range',
							label='trigger runt range',
							set_cmd='TRIGger:A:RUNT:RANGe {}',
							get_cmd='TRIGger:A:RUNT:RANGe?',
							vals=vals.Enum('LONG', 'SHOR', 'WITH', 'OUTS'),
							get_parser=str.rstrip)

		self.add_parameter('width',
							label='trigger runt width',
							set_cmd='TRIGger:A:RUNT:WIDTh {}',
							get_cmd='TRIGger:A:RUNT:WIDTh?',
							vals=vals.Numbers(),
							get_parser=float)

class Timeout(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('range',
							label='trigger timeout range',
							set_cmd='TRIGger:A:TIMeout:RANGe {}',
							get_cmd='TRIGger:A:TIMeout:RANGe?',
							vals=vals.Enum('HIGH', 'LOW'),
							get_parser=str.rstrip)

		self.add_parameter('time',
							label='trigger timeout time',
							set_cmd='TRIGger:A:TIMeout:TIME {}',
							get_cmd='TRIGger:A:TIMeout:TIME?',
							vals=vals.Numbers(3.2e-9,6.871928),
							get_parser=float)

class Trigger(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('mode',
							label='trigger mode',
							set_cmd='TRIGger:A:MODE {}',
							get_cmd='TRIGger:A:MODE?',
							vals=vals.Enum('AUTO', 'NORM'),
							get_parser=str.rstrip)

		self.add_parameter('source',
							label='trigger source',
							set_cmd='TRIGger:A:SOURce {}',
							get_cmd='TRIGger:A:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'EXT', 'LINE', 'SBUS1', 'SBUS2', 'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15'),
							get_parser=str.rstrip)

		self.add_parameter('type',
							label='trigger type',
							set_cmd='TRIGger:A:TYPE {}',
							get_cmd='TRIGger:A:TYPE?',
							vals=vals.Enum('EDGE', 'WIDT', 'TV', 'BUS', 'LOG', 'LINE', 'RIS', 'RUNT'),
							get_parser=str.rstrip)

		self.add_parameter('holdoff_mode',
							label='trigger holdoff mode',
							set_cmd='TRIGger:A:HOLDoff:MODE {}',
							get_cmd='TRIGger:A:HOLDoff:MODE?',
							vals=vals.Enum('TIME', 'OFF'),
							get_parser=str.rstrip)

		self.add_parameter('holdoff_time',
							label='trigger holdoff time',
							set_cmd='TRIGger:A:HOLDoff:TIME {}',
							get_cmd='TRIGger:A:HOLDoff:TIME?',
							vals=vals.Numbers(),
							unit='s',
							get_parser=float)

class Video(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('standard',
							label='color television standard',
							set_cmd='TRIGger:A:TV:STANdard {}',
							get_cmd='TRIGger:A:TV:STANdard?',
							vals=vals.Enum('PAL', 'NTSC', 'SEC', 'PALM', 'I576', 'P720', 'P1080', 'I1080'),
							get_parser=str.rstrip)

		self.add_parameter('polarity',
							label='signal polairty',
							set_cmd='TRIGger:A:TV:POLarity {}',
							get_cmd='TRIGger:A:TV:POLarity?',
							vals=vals.Enum('POS', 'NEG'),
							get_parser=str.rstrip)

		self.add_parameter('field',
							label='video trigger field',
							set_cmd='TRIGger:A:TV:FIELd {}',
							get_cmd='TRIGger:A:TV:FIELd?',
							vals=vals.Enum('EVEN', 'ODD', 'ALL', 'LINE', 'ALIN'),
							get_parser=str.rstrip)

		self.add_parameter('line',
							label='exact line number',
							set_cmd='TRIGger:A:TV:LINE {}',
							get_cmd='TRIGger:A:TV:LINE?',
							vals=vals.Ints(1),
							get_parser=int)

class Width(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('polarity',
							label='trigger width polarity',
							set_cmd='TRIGger:A:WIDTh:POLarity {}',
							get_cmd='TRIGger:A:WIDTh:POLarity?',
							vals=vals.Enum('POS', 'NEG'),
							get_parser=str.rstrip)

		self.add_parameter('range',
							label='trigger width range',
							set_cmd='TRIGger:A:WIDTh:RANGe {}',
							get_cmd='TRIGger:A:WIDTh:RANGe?',
							vals=vals.Enum('WITH', 'OUTS', 'SHOR', 'LONG'),
							get_parser=str.rstrip)

		self.add_parameter('width',
							label='trigger width width',
							set_cmd='TRIGger:A:WIDTh:WIDTh {}',
							get_cmd='TRIGger:A:WIDTh:WIDTh?',
							vals=vals.Numbers(20e-9,6.87194685440),
							get_parser=float)

		self.add_parameter('delta',
							label='trigger width variation range',
							set_cmd='TRIGger:A:WIDTh:DELTa {}',
							get_cmd='TRIGger:A:WIDTh:DELTa?',
							vals=vals.Numbers(0),
							get_parser=float)

# waveform analysis

class Waveform_Analysis_Channel(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		zoom_module=Zoom(self, 'zoom')
		self.add_submodule('zoom', zoom_module)

		search_module=Search(self, 'search')
		self.add_submodule('search', search_module)

		search_edge_module=Search_Edge(self, 'search_edge')
		self.add_submodule('search_edge', search_edge_module)

		search_width_module=Search_Width(self, 'search_width')
		self.add_submodule('search_width', search_width_module)

		search_measure_module=Search_Measure(self, 'search_measure')
		self.add_submodule('search_measure', search_measure_module)

		search_risetime_module=Search_Risetime(self, 'search_risetime')
		self.add_submodule('search_risetime', search_risetime_module)

		search_runt_module=Search_Runt(self, 'search_runt')
		self.add_submodule('search_runt', search_runt_module)

		search_dataclock_module=Search_Dataclock(self, 'search_dataclock')
		self.add_submodule('search_dataclock', search_dataclock_module)

		search_window_module=Search_Window(self, 'search_window')
		self.add_submodule('search_window', search_window_module)

		acquire_module=Acquire(self, 'acquire')
		self.add_submodule('acquire', acquire_module)

		history_spectrum_module=History_Spectrum(self, 'history_spectrum')
		self.add_submodule('history_spectrum', history_spectrum_module)

		timestamp_spectrum_module=Timestamp_Spectrum(self, 'timestamp_spectrum')
		self.add_submodule('timestamp_spectrum', timestamp_spectrum_module)

		export_module=Export(self, 'export')
		self.add_submodule('export', export_module)

		for i in range(1,5+1):
			math_module=Math(self, f'math_lv{i}', i)
			self.add_submodule(f'math_lv{i}', math_module)

			history_math_module=History_Math(self, f'hist_lv{i}', i)
			self.add_submodule(f'hist_lv{i}', history_math_module)

			timestamp_math_module=Timestamp_Math(self, f'time_lv{i}', i)
			self.add_submodule(f'time_lv{i}', timestamp_math_module)

		for i in range(1,4+1):
			reference_module=Reference(self, f'refmod_wv{i}', i)
			self.add_submodule(f'refmod_wv{i}', reference_module)

			search_pattern_module=Search_Pattern(self, f'search_wv{i}', i)
			self.add_submodule(f'search_wv{i}', search_pattern_module)

		for i in range(1,50+1):
			search_results_module=Search_Results(self, f'rs{i}', i)
			self.add_submodule(f'rs{i}', search_results_module)

		for i in range(1,4+1):
			history_channel_module=History_Channel(self, f'hist_ch{i}', i)
			self.add_submodule(f'hist_ch{i}', history_channel_module)

			timestamp_channel_module=Timestamp_Channel(self, f'time_ch{i}', i)
			self.add_submodule(f'time_ch{i}', timestamp_channel_module)

			export_channel_module=Export_Channel(self, f'export_ch{i}', i)
			self.add_submodule(f'export_ch{i}', export_channel_module)

		for i in range(0,15+1):
			history_digital_module=History_Digital(self, f'hist_dg{i}', i)
			self.add_submodule(f'hist_dg{i}', history_digital_module)

			timestamp_digital_module=Timestamp_Digital(self, f'time_dg{i}', i)
			self.add_submodule(f'time_dg{i}', timestamp_digital_module)

			export_digital_module=Export_Digital(self, f'export_dg{i}', i)
			self.add_submodule(f'export_dg{i}', export_digital_module)

		for i in range(1,2+1):
			history_pod_module=History_Pod(self, f'hist_pd{i}', i)
			self.add_submodule(f'hist_pd{i}', history_pod_module)

			timestamp_pod_module=Timestamp_Pod(self, f'time_pd{i}', i)
			self.add_submodule(f'time_pd{i}', timestamp_pod_module)

			export_pod_module=Export_Pod(self, f'export_pd{i}', i)
			self.add_submodule(f'export_pd{i}', export_pod_module)

		for i in range(1,4+1):
			history_bus_module=History_Bus(self, f'hist_bs{i}', i)
			self.add_submodule(f'hist_bs{i}', history_bus_module)

			timestamp_bus_module=Timestamp_Bus(self, f'time_bs{i}', i)
			self.add_submodule(f'time_bs{i}', timestamp_bus_module)

			export_bus_module=Export_Bus(self, f'export_bs{i}', i)
			self.add_submodule(f'export_bs{i}', export_bus_module)

class Acquire(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('memory_mode',
							label='acquire memory mode',
							set_cmd='ACQuire:MEMory:MODE {}',
							get_cmd='ACQuire:MEMory:MODE?',
							vals=vals.Enum('AUT', 'DMEM', 'MAN'),
							get_parser=str.rstrip)

		self.add_parameter('automatic_points',
							label='acquire automatic points',
							set_cmd='ACQuire:POINts:AUTomatic {}',
							get_cmd='ACQuire:POINts:AUTomatic?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('points',
							label='acquire points value',
							set_cmd='ACQuire:POINts:VALue {}',
							get_cmd='ACQuire:POINts:VALue?',
							vals=vals.Enum(5e3, 10e3, 20e3, 50e3, 100e3, 200e3, 500e3, 1e6, 2e6, 5e6, 10e6, 20e6, 40e6, 80e6),
							unit='Samples',
							get_parser=float)

		self.add_parameter('count',
							label='acquire count',
							set_cmd='ACQuire:COUNt {}',
							get_cmd='ACQuire:COUNt?',
							vals=vals.Ints(),
							get_parser=int)

		self.add_parameter('single_count',
							label='number of waveforms acquired in single count',
							set_cmd='ACQuire:NSINgle:COUNt {}',
							get_cmd='ACQuire:NSINgle:COUNt?',
							vals=vals.Numbers(1),
							get_parser=float)

		self.add_parameter('available',
							label='available for viewing segments',
							get_cmd='ACQuire:AVAilable?',
							get_parser=float)

		self.add_parameter('segmented_state',
							label='acquire segmented state',
							set_cmd='ACQuire:SEGMented:STATe {}',
							get_cmd='ACQuire:SEGMented:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('average_current',
							label='acquire average current',
							get_cmd='ACQuire:AVERage:CURRent?',
							get_parser=int)

class Export(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('bplot_name',
							label='name',
							set_cmd='BPLot:EXPort:NAME {}',
							get_cmd=';BPLot:EXPort:NAME?',
							vals=vals.Strings(),
							get_parser=str.rstrip)
						
		self.add_parameter('spectrum_name',
							label='name',
							set_cmd='SPECtrum:HISTory:EXPort:NAME {}',
							get_cmd='SPECtrum:HISTory:EXPort:NAME?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('atable_name',
							label='name',
							set_cmd='EXPort:ATABle:NAME {}',
							get_cmd='EXPort:ATABle:NAME?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

	def bplot_save(self): self.write('BPLot:EXPort:SAVE')
	def spectrum_save(self): self.write('SPECtrum:HISTory:EXPort:SAVE')
	def atable_save(self): self.write('EXPort:ATABle:SAVE')

class Export_Bus(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, busnum):
		super().__init__(parent, name)

		self.add_parameter('name',
							label=f'bus {busnum} name',
							set_cmd=f'BUS{busnum}:HISTory:EXPort:NAME {{}}',
							get_cmd=f'BUS{busnum}:HISTory:EXPort:NAME?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

	def save(self): self.write(f'BUS{busnum}:HISTory:EXPort:SAVE')

class Export_Channel(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, channum):
		super().__init__(parent, name)

		self.add_parameter('name',
							label=f'channel {channum} name',
							set_cmd=f'CHANnel{channum}:HISTory:EXPort:NAME {{}}',
							get_cmd=f'CHANnel{channum}:HISTory:EXPort:NAME?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

	def save(self): self.write(f'CHANnel{channum}:HISTory:EXPort:SAVE')

class Export_Digital(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, lognum):
		super().__init__(parent, name)

		self.add_parameter('name',
							label=f'logic {lognum} name',
							set_cmd=f'DIGital{lognum}:HISTory:EXPort:NAME {{}}',
							get_cmd=f'DIGital{lognum}:HISTory:EXPort:NAME?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

	def save(self): self.write(f'DIGital{lognum}:HISTory:EXPort:SAVE')

class Export_Pod(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, podnum):
		super().__init__(parent, name)

		self.add_parameter('name',
							label=f'pod {podnum} name',
							set_cmd=f'LOGic{podnum}:HISTory:EXPort:NAME {{}}',
							get_cmd=f'LOGic{podnum}:HISTory:EXPort:NAME?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

	def save(self): self.write(f'LOGic{podnum}:HISTory:EXPort:SAVE')

class History_Bus(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, busnum):
		super().__init__(parent, name)

		self.add_parameter('player_control',
							label=f'bus {busnum} player control',
							set_cmd=f'BUS{busnum}:HISTory:CONTrol:ENABle {{}}',
							get_cmd=f'BUS{busnum}:HISTory:CONTrol:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('current',
							label=f'bus {busnum} current',
							set_cmd=f'BUS{busnum}:HISTory:CURRent {{}}',
							get_cmd=f'BUS{busnum}:HISTory:CURRent?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('play_all',
							label=f'bus {busnum} play all',
							set_cmd=f'BUS{busnum}:HISTory:PALL {{}}',
							get_cmd=f'BUS{busnum}:HISTory:PALL?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('start',
							label=f'bus {busnum} start',
							set_cmd=f'BUS{busnum}:HISTory:STARt {{}}',
							get_cmd=f'BUS{busnum}:HISTory:STARt?',
							vals=vals.Ints(),
							get_parser=int)

		self.add_parameter('stop',
							label=f'bus {busnum} stop',
							set_cmd=f'BUS{busnum}:HISTory:STOP {{}}',
							get_cmd=f'BUS{busnum}:HISTory:STOP?',
							vals=vals.Ints(),
							get_parser=int)

		self.add_parameter('player_speed',
							label=f'bus {busnum} player speed',
							set_cmd=f'BUS{busnum}:HISTory:PLAYer:SPEed {{}}',
							get_cmd=f'BUS{busnum}:HISTory:PLAYer:SPEed?',
							vals=vals.Enum('SLOW', 'MED', 'FAST', 'AUTO'),
							get_parser=str.rstrip)

		self.add_parameter('replay',
							label=f'bus {busnum} replay',
							set_cmd=f'BUS{busnum}:HISTory:REPLay {{}}',
							get_cmd=f'BUS{busnum}:HISTory:REPLay?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('player_state',
							label=f'bus {busnum} player state',
							set_cmd=f'BUS{busnum}:HISTory:PLAYer:STATe {{}}',
							get_cmd=f'BUS{busnum}:HISTory:PLAYer:STATe?',
							vals=vals.Enum('RUN', 'STOP'),
							get_parser=str.rstrip)

class History_Channel(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, channum):
		super().__init__(parent, name)

		self.add_parameter('player_control',
							label=f'channel {channum} player control',
							set_cmd=f'CHANnel{channum}:HISTory:CONTrol:ENABle {{}}',
							get_cmd=f'CHANnel{channum}:HISTory:CONTrol:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('current',
							label=f'channel {channum} current',
							set_cmd=f'CHANnel{channum}:HISTory:CURRent {{}}',
							get_cmd=f'CHANnel{channum}:HISTory:CURRent?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('play_all',
							label=f'channel {channum} play all',
							set_cmd=f'CHANnel{channum}:HISTory:PALL {{}}',
							get_cmd=f'CHANnel{channum}:HISTory:PALL?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('start',
							label=f'channel {channum} start',
							set_cmd=f'CHANnel{channum}:HISTory:STARt {{}}',
							get_cmd=f'CHANnel{channum}:HISTory:STARt?',
							vals=vals.Ints(),
							get_parser=int)

		self.add_parameter('stop',
							label=f'channel {channum} stop',
							set_cmd=f'CHANnel{channum}:HISTory:STOP {{}}',
							get_cmd=f'CHANnel{channum}:HISTory:STOP?',
							vals=vals.Ints(),
							get_parser=int)

		self.add_parameter('player_speed',
							label=f'channel {channum} player speed',
							set_cmd=f'CHANnel{channum}:HISTory:PLAYer:SPEed {{}}',
							get_cmd=f'CHANnel{channum}:HISTory:PLAYer:SPEed?',
							vals=vals.Enum('SLOW', 'MED', 'FAST', 'AUTO'),
							get_parser=str.rstrip)

		self.add_parameter('replay',
							label=f'channel {channum} replay',
							set_cmd=f'CHANnel{channum}:HISTory:REPLay {{}}',
							get_cmd=f'CHANnel{channum}:HISTory:REPLay?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('player_state',
							label=f'channel {channum} player state',
							set_cmd=f'CHANnel{channum}:HISTory:PLAYer:STATe {{}}',
							get_cmd=f'CHANnel{channum}:HISTory:PLAYer:STATe?',
							vals=vals.Enum('RUN', 'STOP'),
							get_parser=str.rstrip)

class History_Digital(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, lognum):
		super().__init__(parent, name)

		self.add_parameter('player_control',
							label=f'logic {lognum} player control',
							set_cmd=f'DIGital{lognum}:HISTory:CONTrol:ENABle {{}}',
							get_cmd=f'DIGital{lognum}:HISTory:CONTrol:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('current',
							label=f'logic {lognum} current',
							set_cmd=f'DIGital{lognum}:HISTory:CURRent {{}}',
							get_cmd=f'DIGital{lognum}:HISTory:CURRent?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('play_all',
							label=f'logic {lognum} play all',
							set_cmd=f'DIGital{lognum}:HISTory:PALL {{}}',
							get_cmd=f'DIGital{lognum}:HISTory:PALL?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('start',
							label=f'logic {lognum} start',
							set_cmd=f'DIGital{lognum}:HISTory:STARt {{}}',
							get_cmd=f'DIGital{lognum}:HISTory:STARt?',
							vals=vals.Ints(),
							get_parser=int)

		self.add_parameter('stop',
							label=f'logic {lognum} stop',
							set_cmd=f'DIGital{lognum}:HISTory:STOP {{}}',
							get_cmd=f'DIGital{lognum}:HISTory:STOP?',
							vals=vals.Ints(),
							get_parser=int)

		self.add_parameter('player_speed',
							label=f'logic {lognum} player speed',
							set_cmd=f'DIGital{lognum}:HISTory:PLAYer:SPEed {{}}',
							get_cmd=f'DIGital{lognum}:HISTory:PLAYer:SPEed?',
							vals=vals.Enum('SLOW', 'MED', 'FAST', 'AUTO'),
							get_parser=str.rstrip)

		self.add_parameter('replay',
							label=f'logic {lognum} replay',
							set_cmd=f'DIGital{lognum}:HISTory:REPLay {{}}',
							get_cmd=f'DIGital{lognum}:HISTory:REPLay?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('player_state',
							label=f'logic {lognum} player state',
							set_cmd=f'DIGital{lognum}:HISTory:PLAYer:STATe {{}}',
							get_cmd=f'DIGital{lognum}:HISTory:PLAYer:STATe?',
							vals=vals.Enum('RUN', 'STOP'),
							get_parser=str.rstrip)

class History_Math(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, levnum):
		super().__init__(parent, name)

		self.add_parameter('player_control',
							label=f'level {levnum} player control',
							set_cmd=f'CALCulate:MATH{levnum}:HISTory:CONTrol:ENABle {{}}',
							get_cmd=f'CALCulate:MATH{levnum}:HISTory:CONTrol:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('current',
							label=f'level {levnum} current',
							set_cmd=f'CALCulate:MATH{levnum}:HISTory:CURRent {{}}',
							get_cmd=f'CALCulate:MATH{levnum}:HISTory:CURRent?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('play_all',
							label=f'level {levnum} play all',
							set_cmd=f'CALCulate:MATH{levnum}:HISTory:PALL {{}}',
							get_cmd=f'CALCulate:MATH{levnum}:HISTory:PALL?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('start',
							label=f'level {levnum} start',
							set_cmd=f'CALCulate:MATH{levnum}:HISTory:STARt {{}}',
							get_cmd=f'CALCulate:MATH{levnum}:HISTory:STARt?',
							vals=vals.Ints(),
							get_parser=int)

		self.add_parameter('stop',
							label=f'level {levnum} stop',
							set_cmd=f'CALCulate:MATH{levnum}:HISTory:STOP {{}}',
							get_cmd=f'CALCulate:MATH{levnum}:HISTory:STOP?',
							vals=vals.Ints(),
							get_parser=int)

		self.add_parameter('player_speed',
							label=f'level {levnum} player speed',
							set_cmd=f'CALCulate:MATH{levnum}:HISTory:PLAYer:SPEed {{}}',
							get_cmd=f'CALCulate:MATH{levnum}:HISTory:PLAYer:SPEed?',
							vals=vals.Enum('SLOW', 'MED', 'FAST', 'AUTO'),
							get_parser=str.rstrip)

		self.add_parameter('replay',
							label=f'level {levnum} replay',
							set_cmd=f'CALCulate:MATH{levnum}:HISTory:REPLay {{}}',
							get_cmd=f'CALCulate:MATH{levnum}:HISTory:REPLay?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('player_state',
							label=f'level {levnum} player state',
							set_cmd=f'CALCulate:MATH{levnum}:HISTory:PLAYer:STATe {{}}',
							get_cmd=f'CALCulate:MATH{levnum}:HISTory:PLAYer:STATe?',
							vals=vals.Enum('RUN', 'STOP'),
							get_parser=str.rstrip)

class History_Pod(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, podnum):
		super().__init__(parent, name)

		self.add_parameter('player_control',
							label=f'pod {podnum} player control',
							set_cmd=f'LOGic{podnum}:HISTory:CONTrol:ENABle {{}}',
							get_cmd=f'LOGic{podnum}:HISTory:CONTrol:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('current',
							label=f'pod {podnum} current',
							set_cmd=f'LOGic{podnum}:HISTory:CURRent {{}}',
							get_cmd=f'LOGic{podnum}:HISTory:CURRent?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('play_all',
							label=f'pod {podnum} play all',
							set_cmd=f'LOGic{podnum}:HISTory:PALL {{}}',
							get_cmd=f'LOGic{podnum}:HISTory:PALL?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('start',
							label=f'pod {podnum} start',
							set_cmd=f'LOGic{podnum}:HISTory:STARt {{}}',
							get_cmd=f'LOGic{podnum}:HISTory:STARt?',
							vals=vals.Ints(),
							get_parser=int)

		self.add_parameter('stop',
							label=f'pod {podnum} stop',
							set_cmd=f'LOGic{podnum}:HISTory:STOP {{}}',
							get_cmd=f'LOGic{podnum}:HISTory:STOP?',
							vals=vals.Ints(),
							get_parser=int)

		self.add_parameter('player_speed',
							label=f'pod {podnum} player speed',
							set_cmd=f'LOGic{podnum}:HISTory:PLAYer:SPEed {{}}',
							get_cmd=f'LOGic{podnum}:HISTory:PLAYer:SPEed?',
							vals=vals.Enum('SLOW', 'MED', 'FAST', 'AUTO'),
							get_parser=str.rstrip)

		self.add_parameter('replay',
							label=f'pod {podnum} replay',
							set_cmd=f'LOGic{podnum}:HISTory:REPLay {{}}',
							get_cmd=f'LOGic{podnum}:HISTory:REPLay?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('player_state',
							label=f'pod {podnum} player state',
							set_cmd=f'LOGic{podnum}:HISTory:PLAYer:STATe {{}}',
							get_cmd=f'LOGic{podnum}:HISTory:PLAYer:STATe?',
							vals=vals.Enum('RUN', 'STOP'),
							get_parser=str.rstrip)

class History_Spectrum(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('current',
							label='current',
							set_cmd='SPECtrum:HISTory:CURRent {}',
							get_cmd='SPECtrum:HISTory:CURRent?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('play_all',
							label='play all',
							set_cmd='SPECtrum:HISTory:PALL {}',
							get_cmd='SPECtrum:HISTory:PALL?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('start',
							label='start',
							set_cmd='SPECtrum:HISTory:STARt {}',
							get_cmd='SPECtrum:HISTory:STARt?',
							vals=vals.Ints(),
							get_parser=int)

		self.add_parameter('stop',
							label='stop',
							set_cmd='SPECtrum:HISTory:STOP {}',
							get_cmd='SPECtrum:HISTory:STOP?',
							vals=vals.Ints(),
							get_parser=int)
					
		self.add_parameter('player_speed',
							label='player speed',
							set_cmd='SPECtrum:HISTory:PLAYer:SPEed {}',
							get_cmd='SPECtrum:HISTory:PLAYer:SPEed?',
							vals=vals.Enum('SLOW', 'MED', 'FAST', 'AUTO'),
							get_parser=str.rstrip)

		self.add_parameter('replay',
							label='replay',
							set_cmd='SPECtrum:HISTory:REPLay {}',
							get_cmd='SPECtrum:HISTory:REPLay?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('player_state',
							label='player state',
							set_cmd='SPECtrum:HISTory:PLAYer:STATe {}',
							get_cmd='SPECtrum:HISTory:PLAYer:STATe?',
							vals=vals.Enum('RUN', 'STOP'),
							get_parser=str.rstrip)

class Math(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, levnum):
		super().__init__(parent, name)

		self.add_parameter('state',
							label=f'level {levnum} math state',
							set_cmd=f'CALCulate:MATH{levnum}:STATe {{}}',
							get_cmd=f'CALCulate:MATH{levnum}:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('define_expression',
							label=f'level {levnum} expression define',
							set_cmd=f'CALCulate:MATH{levnum}:EXPRession:DEFine {{}}',
							get_cmd=f'CALCulate:MATH{levnum}:EXPRession:DEFine?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('label',
							label=f'level {levnum} label',
							set_cmd=f'CALCulate:MATH{levnum}:LABel {{}}',
							get_cmd=f'CALCulate:MATH{levnum}:LABel?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('label_state',
							label=f'level {levnum} label state',
							set_cmd=f'CALCulate:MATH{levnum}:LABel:STATe {{}}',
							get_cmd=f'CALCulate:MATH{levnum}:LABel:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('position',
							label=f'level {levnum} position',
							set_cmd=f'CALCulate:MATH{levnum}:POSition {{}}',
							get_cmd=f'CALCulate:MATH{levnum}:POSition?',
							vals=vals.Numbers(0),
							get_parser=float)

		self.add_parameter('scale',
							label=f'level {levnum} scale',
							set_cmd=f'CALCulate:MATH{levnum}:SCALe {{}}',
							get_cmd=f'CALCulate:MATH{levnum}:SCALe?',
							vals=vals.Numbers(-1.0e-24,5.0e25),
							unit='V',
							get_parser=float)

		self.add_parameter('waveform_color',
							label=f'level {levnum} waveform color',
							set_cmd=f'CALCulate:MATH{levnum}:WCOLor {{}}',
							get_cmd=f'CALCulate:MATH{levnum}:WCOLor?',
							vals=vals.Enum('YELL', 'GRE', 'ORAN', 'BLUE', 'LBLUE', 'WHITE', 'CYAN', 'PINK', 'RED', 'TEMP', 'RAIN', 'FIRE', 'DEF'),
							get_parser=str.rstrip)

		self.add_parameter('track_edge',
							label=f'level {levnum} polarity',
							set_cmd=f'CALCulate:MATH{levnum}:TRACk:EDGE {{}}',
							get_cmd=f'CALCulate:MATH{levnum}:TRACk:EDGE?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('double_pulse',
							label=f'level {levnum} double pulse state',
							set_cmd=f'CALCulate:MATH{levnum}:TRACk:DPULse:ENABle {{}}',
							get_cmd=f'CALCulate:MATH{levnum}:TRACk:DPULse:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('threshold_hysteresis',
							label=f'level {levnum} hysteresis threshold',
							set_cmd=f'CALCulate:MATH{levnum}:TRACk:THReshold:HYSTeresis {{}}',
							get_cmd=f'CALCulate:MATH{levnum}:TRACk:THReshold:HYSTeresis?',
							vals=vals.Numbers(),
							unit='V',
							get_parser=float)

		self.add_parameter('threshold_upper',
							label=f'level {levnum} upper threshold',
							set_cmd=f'CALCulate:MATH{levnum}:TRACk:THReshold:UPPer {{}}',
							get_cmd=f'CALCulate:MATH{levnum}:TRACk:THReshold:UPPer?',
							vals=vals.Numbers(),
							unit='V',
							get_parser=float)

		self.add_parameter('threshold_lower',
							label=f'level {levnum} lower threshold',
							set_cmd=f'CALCulate:MATH{levnum}:TRACk:THReshold:LOWer {{}}',
							get_cmd=f'CALCulate:MATH{levnum}:TRACk:THReshold:LOWer?',
							vals=vals.Numbers(),
							unit='V',
							get_parser=float)

class Reference(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, wavenum):
		super().__init__(parent, name)

		self.add_parameter('source',
							label=f'waveform {wavenum} source',
							set_cmd=f'REFCurve{wavenum}:SOURce {{}}',
							get_cmd=f'REFCurve{wavenum}:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'MA1', 'MA2', 'MA3', 'MA4', 'MA5', 'RE1', 'RE2', 'RE3', 'RE4', 'D70', 'D158', 'SPEC', 'MINH', 'MAXH', 'AVER'),
							get_parser=str.rstrip)

		self.add_parameter('source_catalog',
							label=f'waveform {wavenum} source catalog',
							get_cmd=f'REFCurve{wavenum}:SOURce:CATalog?',
							get_parser=str.rstrip)

		self.add_parameter('state',
							label=f'waveform {wavenum} state',
							set_cmd=f'REFCurve{wavenum}:STATe {{}}',
							get_cmd=f'REFCurve{wavenum}:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('save',
							label=f'waveform {wavenum} save',
							set_cmd=f'REFCurve{wavenum}:SAVE {{}}',
							vals=vals.Strings())

		self.add_parameter('load',
							label=f'waveform {wavenum} load',
							set_cmd=f'REFCurve{wavenum}:LOAD {{}}',
							vals=vals.Strings())

		self.add_parameter('horizontal_position',
							label=f'waveform {wavenum} horizontal position',
							set_cmd=f'REFCurve{wavenum}:HORizontal:POSition {{}}',
							get_cmd=f'REFCurve{wavenum}:HORizontal:POSition?',
							vals=vals.Numbers(),
							unit='s',
							get_parser=float)

		self.add_parameter('horizontal_scale',
							label=f'waveform {wavenum} horizontal scale',
							set_cmd=f'REFCurve{wavenum}:HORizontal:SCALe {{}}',
							get_cmd=f'REFCurve{wavenum}:HORizontal:SCALe?',
							vals=vals.Numbers(),
							unit='s/div',
							get_parser=float)

		self.add_parameter('vertical_position',
							label=f'waveform {wavenum} vertical position',
							set_cmd=f'REFCurve{wavenum}:VERTical:POSition {{}}',
							get_cmd=f'REFCurve{wavenum}:VERTical:POSition?',
							vals=vals.Numbers(),
							unit='div',
							get_parser=float)

		self.add_parameter('vertical_scale',
							label=f'waveform {wavenum} vertical scale',
							set_cmd=f'REFCurve{wavenum}:VERTical:SCALe {{}}',
							get_cmd=f'REFCurve{wavenum}:VERTical:SCALe?',
							vals=vals.Numbers(),
							unit='V/div',
							get_parser=float)

		self.add_parameter('waveform_color',
							label=f'waveform {wavenum} color',
							set_cmd=f'REFCurve{wavenum}:WCOLor {{}}',
							get_cmd=f'REFCurve{wavenum}:WCOLor?',
							vals=vals.Enum('YELL', 'GRE', 'ORAN', 'BLUE', 'LBLUE', 'WHITE', 'CYAN', 'PINK', 'RED', 'TEMP', 'RAIN', 'FIRE', 'DEF'),
							get_parser=str.rstrip)

		self.add_parameter('label',
							label=f'waveform {wavenum} label',
							set_cmd=f'REFCurve{wavenum}:LABel {{}}',
							get_cmd=f'REFCurve{wavenum}:LABel?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

	def update(self): self.write(f'REFCurve{wavenum}:UPDate')
	def load_state(self): self.write(f'REFCurve{wavenum}:LOAD:STATe')

class Search(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('state',
							label='search state',
							set_cmd='SEARch:STATe {}',
							get_cmd='SEARch:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('condition',
							label='search condition',
							set_cmd='SEARch:CONDition {}',
							get_cmd='SEARch:CONDition?',
							vals=vals.Enum('EDGE', 'WIDT', 'PEAK', 'RUNT', 'RTIM', 'DAT', 'PATT', 'PROT', 'WIND'),
							get_parser=str.rstrip)

		self.add_parameter('source',
							label='search source',
							set_cmd='SEARch:SOURce {}',
							get_cmd='SEARch:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'QMA', 'RE1', 'RE2', 'RE3', 'RE4'),
							get_parser=str.rstrip)

class Search_Dataclock(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('clock_source',
							label='search dataclock source',
							set_cmd='SEARch:TRIGger:DATatoclock:CSOurce {}',
							get_cmd='SEARch:TRIGger:DATatoclock:CSOurce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4'),
							get_parser=str.rstrip)

		self.add_parameter('clock_level',
							label='search dataclock clock level',
							set_cmd='SEARch:TRIGger:DATatoclock:CLEVel {}',
							get_cmd='SEARch:TRIGger:DATatoclock:CLEVel?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('data_level',
							label='search dataclock data level',
							set_cmd='SEARch:TRIGger:DATatoclock:DLEVel {}',
							get_cmd='SEARch:TRIGger:DATatoclock:DLEVel?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('clock_delta',
							label='search dataclock clock delta',
							set_cmd='SEARch:TRIGger:DATatoclock:CLEVel:DELTa {}',
							get_cmd='SEARch:TRIGger:DATatoclock:CLEVel:DELTa?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('data_delta',
							label='search dataclock data delta',
							set_cmd='SEARch:TRIGger:DATatoclock:DLEVel:DELTa {}',
							get_cmd='SEARch:TRIGger:DATatoclock:DLEVel:DELTa?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('clock_edge',
							label='search dataclock clock edge',
							set_cmd='SEARch:TRIGger:DATatoclock:CEDGe {}',
							get_cmd='SEARch:TRIGger:DATatoclock:CEDGe?',
							vals=vals.Enum('POS', 'NEG', 'EITH'),
							get_parser=str.rstrip)

		self.add_parameter('hold_time',
							label='search dataclock hold time',
							set_cmd='SEARch:TRIGger:DATatoclock:HTIMe {}',
							get_cmd='SEARch:TRIGger:DATatoclock:HTIMe?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('setup_time',
							label='search dataclock setup time',
							set_cmd='SEARch:TRIGger:DATatoclock:STIMe {}',
							get_cmd='SEARch:TRIGger:DATatoclock:STIMe?',
							vals=vals.Numbers(),
							get_parser=float)

class Search_Edge(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('slope',
							label='search edge slope',
							set_cmd='SEARch:TRIGger:EDGE:SLOPe {}',
							get_cmd='SEARch:TRIGger:EDGE:SLOPe?',
							vals=vals.Enum('POS', 'NEG', 'EITH'),
							get_parser=str.rstrip)

		self.add_parameter('level',
							label='search edge level',
							set_cmd='SEARch:TRIGger:EDGE:LEVel {}',
							get_cmd='SEARch:TRIGger:EDGE:LEVel?',
							vals=vals.Numbers(),
							unit='V',
							get_parser=float)

		self.add_parameter('level_delta',
							label='search edge level delta',
							set_cmd='SEARch:TRIGger:EDGE:LEVel:DELTa {}',
							get_cmd='SEARch:TRIGger:EDGE:LEVel:DELTa?',
							vals=vals.Numbers(),
							get_parser=float)		

class Search_Measure(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('peak_polarity',
							label='search peak polarity',
							set_cmd='SEARch:MEASure:PEAK:POLarity {}',
							get_cmd='SEARch:MEASure:PEAK:POLarity?',
							vals=vals.Enum('POS', 'NEG', 'EITH'),
							get_parser=str.rstrip)

		self.add_parameter('peak_magnitude',
							label='search peak magnitude',
							set_cmd='SEARch:MEASure:LEVel:PEAK:MAGNitude {}',
							get_cmd='SEARch:MEASure:LEVel:PEAK:MAGNitude?',
							vals=vals.Numbers(),
							unit='V',
							get_parser=float)

class Search_Pattern(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, wavenum):
		super().__init__(parent, name)

		self.add_parameter('source',
							label='search pattern source',
							set_cmd='SEARch:TRIGger:PATTern:SOURce {}',
							get_cmd='SEARch:TRIGger:PATTern:SOURce?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('function',
							label='search pattern function',
							set_cmd='SEARch:TRIGger:PATTern:FUNCtion {}',
							get_cmd='SEARch:TRIGger:PATTern:FUNCtion?',
							vals=vals.Enum('AND', 'OR', 'NAND', 'NOR'),
							get_parser=str.rstrip)

		self.add_parameter('threshold_level',
							label=f'waveform {wavenum} threshold level',
							set_cmd=f'SEARch:TRIGger:PATTern:LEVel{wavenum} {{}}',
							get_cmd=f'SEARch:TRIGger:PATTern:LEVel{wavenum}?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('level_delta',
							label=f'waveform {wavenum} threshold level delta',
							set_cmd=f'SEARch:TRIGger:PATTern:LEVel{wavenum}:DELTa {{}}',
							get_cmd=f'SEARch:TRIGger:PATTern:LEVel{wavenum}:DELTa?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('width_range',
							label='search pattern width range',
							set_cmd='SEARch:TRIGger:PATTern:WIDTh:RANGe {}',
							get_cmd='SEARch:TRIGger:PATTern:WIDTh:RANGe?',
							vals=vals.Enum('WITH', 'OUTS', 'LONG', 'SHOR'),
							get_parser=str.rstrip)

		self.add_parameter('width',
							label='search pattern width',
							set_cmd='SEARch:TRIGger:PATTern:WIDTh:WIDTh {}',
							get_cmd='SEARch:TRIGger:PATTern:WIDTh:WIDTh?',
							vals=vals.Numbers(),
							unit='s',
							get_parser=float)

		self.add_parameter('width_delta',
							label='search pattern width delta',
							set_cmd='SEARch:TRIGger:PATTern:WIDTh:DELTa {}',
							get_cmd='SEARch:TRIGger:PATTern:WIDTh:DELTa?',
							vals=vals.Numbers(),
							unit='s',
							get_parser=float)

class Search_Results(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, resnum):
		super().__init__(parent, name)

		self.add_parameter('buffered_count',
							label='search results buffered count',
							get_cmd='SEARch:RESult:BCOunt?',
							get_parser=int)

		self.add_parameter('result_show',
							label='search result table state',
							set_cmd='SEARch:RESDiagram:SHOW {}',
							get_cmd='SEARch:RESDiagram:SHOW?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('all',
							label='search results all',
							get_cmd='SEARch:RESult:ALL?',
							get_parser=str.rstrip)

		self.add_parameter('specified',
							label=f'result {resnum} specified search result',
							get_cmd=f'SEARch:RESult{resnum}?',
							get_parser=str.rstrip)

		self.add_parameter('count',
							label='results count',
							get_cmd='SEARch:RCOunt?',
							get_parser=str.rstrip)

		self.add_parameter('export_name',
							label='search export name',
							set_cmd='EXPort:SEARch:NAME {}',
							get_cmd='EXPort:SEARch:NAME?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

	def save(self): self.write('EXPort:SEARch:SAVE')

class Search_Risetime(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('risetime_slope',
							label='search risetime slope',
							set_cmd='SEARch:TRIGger:RISetime:SLOPe {}',
							get_cmd='SEARch:TRIGger:RISetime:SLOPe?',
							vals=vals.Enum('POS', 'NEG', 'EITH'),
							get_parser=str.rstrip)

		self.add_parameter('risetime_lower',
							label='search risetime lower voltage',
							set_cmd='SEARch:TRIGger:LEVel:RISetime:LOWer {}',
							get_cmd='SEARch:TRIGger:LEVel:RISetime:LOWer?',
							vals=vals.Numbers(),
							unit='V',
							get_parser=float)

		self.add_parameter('risetime_upper',
							label='search risetime upper voltage',
							set_cmd='SEARch:TRIGger:LEVel:RISetime:UPPer {}',
							get_cmd='SEARch:TRIGger:LEVel:RISetime:UPPer?',
							vals=vals.Numbers(),
							unit='V',
							get_parser=float)

		self.add_parameter('risetime_range',
							label='search risetime range',
							set_cmd='SEARch:TRIGger:RISetime:RANGe {}',
							get_cmd='SEARch:TRIGger:RISetime:RANGe?',
							vals=vals.Enum('LONG', 'SHOR', 'WITH', 'OUTS'),
							get_parser=str.rstrip)

		self.add_parameter('risetime_time',
							label='search risetime time',
							set_cmd='SEARch:TRIGger:RISetime:TIME {}',
							get_cmd='SEARch:TRIGger:RISetime:TIME?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('risetime_delta',
							label='search risetime delta',
							set_cmd='SEARch:TRIGger:RISetime:DELTa {}',
							get_cmd='SEARch:TRIGger:RISetime:DELTa?',
							vals=vals.Numbers(),
							get_parser=float)

class Search_Runt(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('polarity',
							label='search runt polarity',
							set_cmd='SEARch:TRIGger:RUNT:POLarity {}',
							get_cmd='SEARch:TRIGger:RUNT:POLarity?',
							vals=vals.Enum('POS', 'NEG', 'EITH'),
							get_parser=str.rstrip)

		self.add_parameter('level_lower',
							label='search runt lower level',
							set_cmd='SEARch:TRIGger:LEVel:RUNT:LOWer {}',
							get_cmd='SEARch:TRIGger:LEVel:RUNT:LOWer?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('level_upper',
							label='search runt upper level',
							set_cmd='SEARch:TRIGger:LEVel:RUNT:UPPer {}',
							get_cmd='SEARch:TRIGger:LEVel:RUNT:UPPer?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('range',
							label='search runt range',
							set_cmd='SEARch:TRIGger:RUNT:RANGe {}',
							get_cmd='SEARch:TRIGger:RUNT:RANGe?',
							vals=vals.Enum('LONG', 'SHOR', 'WITH', 'OUTS'),
							get_parser=str.rstrip)

		self.add_parameter('width',
							label='search runt width',
							set_cmd='SEARch:TRIGger:RUNT:WIDTh {}',
							get_cmd='SEARch:TRIGger:RUNT:WIDTh?',
							vals=vals.Numbers(),
							get_parser=float)
						
		self.add_parameter('delta',
							label='search runt delta',
							set_cmd='SEARch:TRIGger:RUNT:DELTa {}',
							get_cmd='SEARch:TRIGger:RUNT:DELTa?',
							vals=vals.Numbers(),
							get_parser=float)

class Search_Width(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('polarity',
							label='search width polarity',
							set_cmd='SEARch:TRIGger:WIDTh:POLarity {}',
							get_cmd='SEARch:TRIGger:WIDTh:POLarity?',
							vals=vals.Enum('POS', 'NEG'),
							get_parser=str.rstrip)

		self.add_parameter('level',
							label='search width level',
							set_cmd='SEARch:TRIGger:WIDTh:LEVel {}',
							get_cmd='SEARch:TRIGger:WIDTh:LEVel?',
							vals=vals.Numbers(),
							unit='V',
							get_parser=float)

		self.add_parameter('level_delta',
							label='search width level delta',
							set_cmd='SEARch:TRIGger:WIDTh:LEVel:DELTa {}',
							get_cmd='SEARch:TRIGger:WIDTh:LEVel:DELTa?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('range',
							label='width range',
							set_cmd='SEARch:TRIGger:WIDTh:RANGe {}',
							get_cmd='SEARch:TRIGger:WIDTh:RANGe?',
							vals=vals.Enum('WITH', 'OUTS', 'SHOR', 'LONG'),
							get_parser=str.rstrip)
		
		self.add_parameter('width',
							label='search width width',
							set_cmd='SEARch:TRIGger:WIDTh:WIDTh {}',
							get_cmd='SEARch:TRIGger:WIDTh:WIDTh?',
							vals=vals.Numbers(),
							unit='s',
							get_parser=float)
					
		self.add_parameter('delta',
							label='search width delta',
							set_cmd='SEARch:TRIGger:WIDTh:DELTa {}',
							get_cmd='SEARch:TRIGger:WIDTh:DELTa?',
							vals=vals.Numbers(),
							get_parser=float)

class Search_Window(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('level_lower',
							label='search window lower level',
							set_cmd='SEARch:TRIGger:LEVel:WINDow:LOWer {}',
							get_cmd='SEARch:TRIGger:LEVel:WINDow:LOWer?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('level_upper',
							label='search window upper level',
							set_cmd='SEARch:TRIGger:LEVel:WINDow:UPPer {}',
							get_cmd='SEARch:TRIGger:LEVel:WINDow:UPPer?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('delta',
							label='search window delta',
							set_cmd='SEARch:TRIGger:WINDow:DELTa {}',
							get_cmd='SEARch:TRIGger:WINDow:DELTa?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('polarity',
							label='search window polarity',
							set_cmd='SEARch:TRIGger:WINDow:POLarity {}',
							get_cmd='SEARch:TRIGger:WINDow:POLarity?',
							vals=vals.Enum('POS', 'NEG', 'EITH'),
							get_parser=str.rstrip)

		self.add_parameter('range',
							label='search window range',
							set_cmd='SEARch:TRIGger:WINDow:RANGe {}',
							get_cmd='SEARch:TRIGger:WINDow:RANGe?',
							vals=vals.Enum('ENT', 'EXIT', 'WITH', 'OUTS', 'PASS', 'NPAS'),
							get_parser=str.rstrip)

		self.add_parameter('timerange',
							label='search window timerange',
							set_cmd='SEARch:TRIGger:WINDow:TIMerange {}',
							get_cmd='SEARch:TRIGger:WINDow:TIMerange?',
							vals=vals.Enum('WITH', 'OUTS', 'SHOR', 'LONG'),
							get_parser=str.rstrip)

		self.add_parameter('width',
							label='search window width',
							set_cmd='SEARch:TRIGger:WINDow:WIDTh {}',
							get_cmd='SEARch:TRIGger:WINDow:WIDTh?',
							get_parser=float)

class Timestamp_Bus(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, busnum):
		super().__init__(parent, name)

		self.add_parameter('timetable',
							label=f'bus {busnum} timetable state',
							set_cmd=f'BUS{busnum}:HISTory:TTABle:ENABle {{}}',
							get_cmd=f'BUS{busnum}:HISTory:TTABle:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('relative',
							label=f'bus {busnum} relative time',
							get_cmd=f'BUS{busnum}:HISTory:TSRelative?',
							get_parser=float)
	
		self.add_parameter('relative_all',
							label=f'bus {busnum} all relative time',
							get_cmd=f'BUS{busnum}:HISTory:TSRelative:ALL?',
							get_parser=str.rstrip)
							
		self.add_parameter('absolute',
							label=f'bus {busnum} absolute daytime',
							get_cmd=f'BUS{busnum}:HISTory:TSABsolute?',
							get_parser=str.rstrip)

		self.add_parameter('absolute_all',
							label=f'bus {busnum} all absolute daytime',
							get_cmd=f'BUS{busnum}:HISTory:TSABsolute:ALL?',
							get_parser=str.rstrip)

		self.add_parameter('date',
							label=f'bus {busnum} date',
							get_cmd=f'BUS{busnum}:HISTory:TSDate?',
							get_parser=str.rstrip)

		self.add_parameter('date_all',
							label=f'bus {busnum} all date',
							get_cmd=f'BUS{busnum}:HISTory:TSDate:ALL?',
							get_parser=str.rstrip)

class Timestamp_Channel(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, channum):
		super().__init__(parent, name)

		self.add_parameter('timetable',
							label=f'channel {channum} timetable state',
							set_cmd=f'CHANnel{channum}:HISTory:TTABle:ENABle {{}}',
							get_cmd=f'CHANnel{channum}:HISTory:TTABle:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('table_mode',
							label=f'channel {channum} table mode',
							set_cmd=f'CHANnel{channum}:HISTory:TMODe {{}}',
							get_cmd=f'CHANnel{channum}:HISTory:TMODe?',
							vals=vals.Enum('REL', 'ABS'),
							get_parser=str.rstrip)

		self.add_parameter('relative',
							label=f'channel {channum} relative time',
							get_cmd=f'CHANnel{channum}:HISTory:TSRelative?',
							get_parser=float)

		self.add_parameter('relative_all',
							label=f'channel {channum} all relative time',
							get_cmd=f'CHANnel{channum}:HISTory:TSRelative:ALL?',
							get_parser=float)

		self.add_parameter('absolute',
							label=f'channel {channum} absolute daytime',
							get_cmd=f'CHANnel{channum}:HISTory:TSABsolute?',
							get_parser=str.rstrip)

		self.add_parameter('absolute_all',
							label=f'channel {channum} all absolute daytime',
							get_cmd=f'CHANnel{channum}:HISTory:TSABsolute:ALL?',
							get_parser=str.rstrip)

		self.add_parameter('date',
							label=f'channel {channum} date',
							get_cmd=f'CHANnel{channum}:HISTory:TSDate?',
							get_parser=str.rstrip)

		self.add_parameter('date_all',
							label=f'channel {channum} all date',
							get_cmd=f'CHANnel{channum}:HISTory:TSDate:ALL?',
							get_parser=str.rstrip)

class Timestamp_Digital(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, lognum):
		super().__init__(parent, name)

		self.add_parameter('timetable',
							label=f'logic {lognum} timetable state',
							set_cmd=f'DIGital{lognum}:HISTory:TTABle:ENABle {{}}',
							get_cmd=f'DIGital{lognum}:HISTory:TTABle:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('relative',
							label=f'logic {lognum} relative time',
							get_cmd=f'DIGital{lognum}:HISTory:TSRelative?',
							get_parser=float)

		self.add_parameter('relative_all',
							label=f'logic {lognum} all relative time',
							get_cmd=f'DIGital{lognum}:HISTory:TSRelative:ALL?',
							get_parser=str.rstrip)

		self.add_parameter('absolute',
							label=f'logic {lognum} absolute daytime',
							get_cmd=f'DIGital{lognum}:HISTory:TSABsolute?',
							get_parser=str.rstrip)

		self.add_parameter('absolute_all',
							label=f'logic {lognum} all absolute daytime',
							get_cmd=f'DIGital{lognum}:HISTory:TSABsolute:ALL?',
							get_parser=str.rstrip)

		self.add_parameter('date',
							label=f'logic {lognum} date',
							get_cmd=f'DIGital{lognum}:HISTory:TSDate?',
							get_parser=str.rstrip)

		self.add_parameter('date_all',
							label=f'logic {lognum} all date',
							get_cmd=f'DIGital{lognum}:HISTory:TSDate:ALL?',
							get_parser=str.rstrip)

class Timestamp_Math(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, levnum):
		super().__init__(parent, name)

		self.add_parameter('timetable',
							label=f'level {levnum} timetable state',
							set_cmd=f'CALCulate:MATH{levnum}:HISTory:TTABle:ENABle {{}}',
							get_cmd=f'CALCulate:MATH{levnum}:HISTory:TTABle:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('relative',
							label=f'level {levnum} relative time',
							get_cmd=f'CALCulate:MATH{levnum}:HISTory:TSRelative?',
							get_parser=float)

		self.add_parameter('relative_all',
							label=f'level {levnum} all relative time',
							get_cmd=f'CALCulate:MATH{levnum}:HISTory:TSRelative:ALL?',
							get_parser=str.rstrip)

		self.add_parameter('absolute',
							label=f'level {levnum} absolute daytime',
							get_cmd=f'CALCulate:MATH{levnum}:HISTory:TSABsolute?',
							get_parser=str.rstrip)

		self.add_parameter('absolute_all',
							label=f'level {levnum} all absolute daytime',
							get_cmd=f'CALCulate:MATH{levnum}:HISTory:TSABsolute:ALL?',
							get_parser=str.rstrip)

		self.add_parameter('date',
							label=f'level {levnum} date',
							get_cmd=f'CALCulate:MATH{levnum}:HISTory:TSDate?',
							get_parser=str.rstrip)

		self.add_parameter('date_all',
							label=f'level {levnum} all date',
							get_cmd=f'CALCulate:MATH{levnum}:HISTory:TSDate:ALL?',
							get_parser=str.rstrip)

class Timestamp_Pod(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, podnum):
		super().__init__(parent, name)

		self.add_parameter('timetable',
							label=f'pod {podnum} timetable state',
							set_cmd=f'LOGic{podnum}:HISTory:TTABle:ENABle {{}}',
							get_cmd=f'LOGic{podnum}:HISTory:TTABle:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('relative',
							label=f'pod {podnum} relative time',
							get_cmd=f'LOGic{podnum}:HISTory:TSRelative?',
							get_parser=float)

		self.add_parameter('relative_all',
							label=f'pod {podnum} all relative time',
							get_cmd=f'LOGic{podnum}:HISTory:TSRelative:ALL?',
							get_parser=str.rstrip)

		self.add_parameter('absolute',
							label=f'pod {podnum} absolute daytime',
							get_cmd=f'LOGic{podnum}:HISTory:TSABsolute?',
							get_parser=str.rstrip)

		self.add_parameter('absolute_all',
							label=f'pod {podnum} all absolute daytime',
							get_cmd=f'LOGic{podnum}:HISTory:TSABsolute:ALL?',
							get_parser=str.rstrip)

		self.add_parameter('date',
							label=f'pod {podnum} date',
							get_cmd=f'LOGic{podnum}:HISTory:TSDate?',
							get_parser=str.rstrip)

		self.add_parameter('date_all',
							label=f'pod {podnum} all date',
							get_cmd=f'LOGic{podnum}:HISTory:TSDate:ALL?',
							get_parser=str.rstrip)

class Timestamp_Spectrum(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('relative',
							label='relative time',
							get_cmd='SPECtrum:HISTory:TSRelative?',
							get_parser=float)

		self.add_parameter('relative_all',
							label='all relative time',
							get_cmd='SPECtrum:HISTory:TSRelative:ALL?',
							get_parser=str.rstrip)

		self.add_parameter('absolute',
							label='absolute',
							get_cmd='SPECtrum:HISTory:TSABsolute?',
							get_parser=str.rstrip)

		self.add_parameter('absolute_all',
							label='all absolute',
							get_cmd='SPECtrum:HISTory:TSABsolute:ALL?',
							get_parser=str.rstrip)

		self.add_parameter('date',
							label='date',
							get_cmd='SPECtrum:HISTory:TSDate?',
							get_parser=str.rstrip)

		self.add_parameter('date_all',
							label='all date',
							get_cmd='SPECtrum:HISTory:TSDate:ALL?',
							get_parser=str.rstrip)

class Zoom(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('zoom_state',
							label='zoom state',
							set_cmd='TIMebase:ZOOM:STATe {}',
							get_cmd='TIMebase:ZOOM:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('scale',
							label='zoom scale',
							set_cmd='TIMebase:ZOOM:SCALe {}',
							get_cmd='TIMebase:ZOOM:SCALe?',
							vals=vals.Numbers(),
							unit='s/div',
							get_parser=float)

		self.add_parameter('time',
							label='zoom time',
							set_cmd='TIMebase:ZOOM:TIME {}',
							get_cmd='TIMebase:ZOOM:TIME?',
							vals=vals.Numbers(),
							unit='s',
							get_parser=float)

		self.add_parameter('position',
							label='zoom position',
							set_cmd='TIMebase:ZOOM:POSition {}',
							get_cmd='TIMebase:ZOOM:POSition?',
							vals=vals.Numbers(0,100),
							unit='%',
							get_parser=float)

		self.add_parameter('CBAR_position',
							label='zoom CBAR position',
							set_cmd='DISPlay:CBAR:ZOOM:POSition {}',
							get_cmd='DISPlay:CBAR:ZOOM:POSition?',
							vals=vals.Ints(0,800),
							unit='px',
							get_parser=int)

# Measurements

class Measurements_Channel(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		reference_levels_module=Reference_Levels(self, 'reference_levels')
		self.add_submodule('reference_levels', reference_levels_module)

		for i in range(1,8+1):
			measurement_quick_module=Measurement_Quick(self, f'quick_pl{i}', i)
			self.add_submodule(f'quick_pl{i}', measurement_quick_module)

			measurement_automatic_module=Measurement_Automatic(self, f'auto_pl{i}', i)
			self.add_submodule(f'auto_pl{i}', measurement_automatic_module)

			measurement_results_module=Measurement_Results(self, f'res_pl{i}', i)
			self.add_submodule(f'res_pl{i}', measurement_results_module)

		for i in range(1,1+1):
			for j in range(1,2+1):
				cursor_line_module=Cursor_Line(self, f'cur_cu{i}_lin_cl{j}', i, j)
				self.add_submodule(f'cur_cu{i}_lin_cl{j}', cursor_line_module)

		for i in range(1,8+1):
			for j in range(1, 50+1):
				measurement_statistics_module=Measurement_Statistics(self, f'stat_pl{i}_stat_bf{j}', i, j)
				self.add_submodule(f'stat_pl{i}_stat_bf{j}', measurement_statistics_module)

		for i in range(1,4+1):
			measurement_gate_module=Measurement_Gate(self, f'meas_gt{i}', i)
			self.add_submodule(f'meas_gt{i}', measurement_gate_module)

		for i in range(1,1+1):
			cursor_module=Cursor(self, f'cu{i}', i)
			self.add_submodule(f'cu{i}', cursor_module)
		
class Cursor(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, curnum):
		super().__init__(parent, name)

		self.add_parameter('state',
							label=f'cursor {curnum} state',
							set_cmd=f'CURSor{curnum}:STATe {{}}',
							get_cmd=f'CURSor{curnum}:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('type',
							label=f'cursor {curnum} type',
							set_cmd=f'CURSor{curnum}:FUNCtion {{}}',
							get_cmd=f'CURSor{curnum}:FUNCtion?',
							vals=vals.Enum('HOR', 'VERT', 'HVER'),
							get_parser=str.rstrip)

		self.add_parameter('source',
							label=f'cursor {curnum} source',
							set_cmd=f'CURSor{curnum}:SOURce {{}}',
							get_cmd=f'CURSor{curnum}:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'MA1', 'MA2', 'MA3', 'MA4', 'MA5', 'RE1', 'RE2', 'RE3', 'RE4', 'XY1', 'XY2', 'D70', 'D158', 'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15', 'SPEC', 'MINH', 'MAXH', 'AVER'),
							get_parser=str.rstrip)

		self.add_parameter('use_second',
							label=f'cursor {curnum} use second source',
							set_cmd=f'CURSor{curnum}:USSOURce {{}}',
							get_cmd=f'CURSor{curnum}:USSOURce?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('second_source',
							label=f'cursor {curnum} second source',
							set_cmd=f'CURSor{curnum}:SSOURce {{}}',
							get_cmd=f'CURSor{curnum}:SSOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'MA1', 'MA2', 'MA3', 'MA4', 'MA5', 'RE1', 'RE2', 'RE3', 'RE4', 'XY1', 'XY2', 'D70', 'D158', 'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15', 'SPEC', 'MINH', 'MAXH', 'AVER'),
							get_parser=str.rstrip)

		self.add_parameter('tracking_state',
							label=f'cursor {curnum} tracking state',
							set_cmd=f'CURSor{curnum}:TRACking:STATe {{}}',
							get_cmd=f'CURSor{curnum}:TRACking:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('x1_position',
							label=f'cursor {curnum} x1 position',
							set_cmd=f'CURSor{curnum}:X1Position {{}}',
							get_cmd=f'CURSor{curnum}:X1Position?',
							vals=vals.Numbers(),
							unit='s',
							get_parser=float)

		self.add_parameter('x2_position',
							label=f'cursor {curnum} x2 position',
							set_cmd=f'CURSor{curnum}:X2Position {{}}',
							get_cmd=f'CURSor{curnum}:X2Position?',
							vals=vals.Numbers(),
							unit='s',
							get_parser=float)

		self.add_parameter('y1_position',
							label=f'cursor {curnum} y1 position',
							set_cmd=f'CURSor{curnum}:Y1Position {{}}',
							get_cmd=f'CURSor{curnum}:Y1Position?',
							vals=vals.Numbers(),
							unit='V',
							get_parser=float)

		self.add_parameter('y2_position',
							label=f'cursor {curnum} y2 position',
							set_cmd=f'CURSor{curnum}:Y2Position {{}}',
							get_cmd=f'CURSor{curnum}:Y2Position?',
							vals=vals.Numbers(),
							unit='V',
							get_parser=float)

		self.add_parameter('y_coupling',
							label=f'cursor {curnum} y coupling',
							set_cmd=f'CURSor{curnum}:YCOupling {{}}',
							get_cmd=f'CURSor{curnum}:YCOupling?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('x_coupling',
							label=f'cursor {curnum} x coupling',
							set_cmd=f'CURSor{curnum}:XCOupling {{}}',
							get_cmd=f'CURSor{curnum}:XCOupling?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('scale_state',
							label=f'cursor {curnum} scale state',
							set_cmd=f'CURSor{curnum}:TRACking:SCALe:STATe {{}}',
							get_cmd=f'CURSor{curnum}:TRACking:SCALe:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('x_delta',
							label=f'cursor {curnum} x delta',
							get_cmd=f'CURSor{curnum}:XDELta:VALue?',
							get_parser=float)

		self.add_parameter('x_inverse',
							label=f'cursor {curnum} x delta inverse',
							get_cmd=f'CURSor{curnum}:XDELta:INVerse?',
							get_parser=float)

		self.add_parameter('y_delta',
							label=f'cursor {curnum} y delta',
							get_cmd=f'CURSor{curnum}:YDELta:VALue?',
							get_parser=float)

		self.add_parameter('y_slope',
							label=f'cursor {curnum} y delta slope',
							get_cmd=f'CURSor{curnum}:YDELta:SLOPe?',
							get_parser=float)

	def off(self): self.write(f'CURSor{curnum}:AOFF')
	def wave(self): self.write(f'CURSor{curnum}:SWAVe')

class Cursor_Line(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, curnum, curlin):
		super().__init__(parent, name)

	def ppeak(self): self.write(f'CURSor{curnum}:SPPeak{curlin}')
	def npeak(self): self.write(f'CURSor{curnum}:SNPeak{curlin}')

class Measurement_Automatic(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, placnum):
		super().__init__(parent, name)

		self.add_parameter('enable',
							label=f'place {placnum} measurement state',
							set_cmd=f'MEASurement{placnum}:ENABle {{}}',
							get_cmd=f'MEASurement{placnum}:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('type',
							label=f'place {placnum} measurement type',
							set_cmd=f'MEASurement{placnum}:MAIN {{}}',
							get_cmd=f'MEASurement{placnum}:MAIN?',
							vals=vals.Enum('FREQ', 'PER', 'PEAK', 'UPE', 'LPE', 'PPC', 'NPC', 'REC', 'FEC', 'HIGH', 'LOW', 'AMPL', 'MEAN', 'RMS', 'RTIM', 'FTIM', 'SRR', 'SRF', 'PDCY', 'NDCY', 'PPW', 'NPW', 'CYCM', 'CYCR', 'STDD', 'DEL', 'PHAS', 'DTOT', 'CYCS', 'POV', 'NOV', 'BWID'),
							get_parser=str.rstrip)

		self.add_parameter('_source',
							label=f'place {placnum} measurement source',
							set_cmd=f'MEASurement{placnum}:SOURce {{}}',
							get_cmd=f'MEASurement{placnum}:SOURce?',
							get_parser=str.rstrip)

		self.add_parameter('_delay_slope',
							label=f'place {placnum} delay slope',
							set_cmd=f'MEASurement{placnum}:DELay:SLOPe {{}}',
							get_cmd=f'MEASurement{placnum}:DELay:SLOPe?',
							get_parser=str.rstrip)

		self.add_parameter('_delay_direction',
							label=f'place {placnum} delay direction',
							set_cmd=f'MEASurement{placnum}:DELay:DIRection {{}}',
							get_cmd=f'MEASurement{placnum}:DELay:DIRection?',
							get_parser=str.rstrip)

		self.add_parameter('delay_marker',
							label=f'place {placnum} delay marker',
							set_cmd=f'MEASurement{placnum}:DELay:MARKer {{}}',
							get_cmd=f'MEASurement{placnum}:DELay:MARKer?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('statistics',
							label=f'place {placnum} statistics state',
							set_cmd=f'MEASurement{placnum}:STATistics:ENABle {{}}',
							get_cmd=f'MEASurement{placnum}:STATistics:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

	def reset(self): self.write(f'MEASurement{placnum}:STATistics:RESet')

	def source(self, source1, source2):
		'''
		Source parameter wrapper
		Args:
			source1
			source2
		'''
		vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'MA1', 'RE1', 'RE2', 'RE3', 'RE4', 'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15').validate(source1)
		vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'MA1', 'RE1', 'RE2', 'RE3', 'RE4', 'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15', 'None').validate(source2)
		input=f'{source1}, {source2}'
		self._source(input)

	def delay_slope(self, signalslope, referenceslope):
		'''
		Delay slope parameter wrapper
		Args:
			signalslope
			referenceslope
		'''
		vals.Enum('POS', 'NEG').validate(signalslope)
		vals.Enum('POS', 'NEG').validate(referenceslope)
		input=f'{signalslope}, {referenceslope}'
		self._delay_slope(input)

	def delay_direction(self, direction1, direction2):
		'''
		Delay direction parameter wrapper
		Args:
			direction1
			direction2
		'''
		vals.Enum('NEAR', 'FRFI', 'FRLA').validate(direction1)
		vals.Enum('NEAR', 'FRFI', 'FRLA').validate(direction2)
		input=f'{direction1}, {direction2}'
		self._delay_direction(input)
	
class Measurement_Gate(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, gatnum):
		super().__init__(parent, name)

		self.add_parameter('state',
							label=f'place {gatnum} measurement gate',
							set_cmd=f'MEASurement{gatnum}:GATE {{}}',
							get_cmd=f'MEASurement{gatnum}:GATE?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('mode',
							label=f'gate {gatnum} measurement gate mode',
							set_cmd=f'MEASurement{gatnum}:GATE:MODE {{}}',
							get_cmd=f'MEASurement{gatnum}:GATE:MODE?',
							vals=vals.Enum('RELative', 'ABSolute'),
							get_parser=str.rstrip)

		self.add_parameter('start_time',
							label=f'gate {gatnum} measurement gate start time',
							set_cmd=f'MEASurement{gatnum}:GATE:ABSolute:STARt {{}}',
							get_cmd=f'MEASurement{gatnum}:GATE:ABSolute:STARt?',
							vals=vals.Numbers(),
							unit='s',
							get_parser=float)

		self.add_parameter('stop_time',
							label=f'gate {gatnum} measurement gate stop time',
							set_cmd=f'MEASurement{gatnum}:GATE:ABSolute:STOP {{}}',
							get_cmd=f'MEASurement{gatnum}:GATE:ABSolute:STOP?',
							vals=vals.Numbers(),
							unit='s',
							get_parser=float)

		self.add_parameter('start_position',
							label=f'gate {gatnum} measurement gate start position',
							set_cmd=f'MEASurement{gatnum}:GATE:RELative:STARt {{}}',
							get_cmd=f'MEASurement{gatnum}:GATE:RELative:STARt?',
							vals=vals.Numbers(0,100),
							unit='%',
							get_parser=float)

		self.add_parameter('stop_position',
							label=f'gate {gatnum} measurement gate stop position',
							set_cmd=f'MEASurement{gatnum}:GATE:RELative:STOP {{}}',
							get_cmd=f'MEASurement{gatnum}:GATE:RELative:STOP?',
							vals=vals.Numbers(0,100),
							unit='%',
							get_parser=float)

class Measurement_Quick(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, placnum):
		super().__init__(parent, name)

		self.add_parameter('result',
							label=f'place {placnum} quick measurement result',
							get_cmd=f'MEASurement{placnum}:ARESult?',
							get_parser=str.rstrip)

		self.add_parameter('all_state',
							label=f'place {placnum} quick measurement state',
							set_cmd=f'MEASurement{placnum}:ALL:STATe {{}}',
							get_cmd=f'MEASurement{placnum}:ALL:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

	def off(self): self.write(f'MEASurement{placnum}:AOFF')
	def on(self): self.write(f'MEASurement{placnum}:AON')

class Measurement_Results(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, placnum):
		super().__init__(parent, name)

		self.add_parameter('timeout_time',
							label=f'place {placnum} timeout time',
							set_cmd=f'MEASurement{placnum}:TIMeoutTIME {{}}',
							get_cmd=f'MEASurement{placnum}:TIMeoutTIME?',
							vals=vals.Numbers(0),
							unit='s',
							get_parser=float)

		self.add_parameter('timeout_auto',
							label=f'place {placnum} timeout auto',
							set_cmd=f'MEASurement{placnum}:TIMeout:AUTO {{}}',
							get_cmd=f'MEASurement{placnum}:TIMeout:AUTO?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('actual',
							label=f'place {placnum} specified result',
							get_cmd=f'MEASurement{placnum}:RESult:ACTual?',
							get_parser=str.rstrip)

		self.add_parameter('average',
							label=f'place {placnum} average result',
							get_cmd=f'MEASurement{placnum}:RESult:AVG?',
							get_parser=float)

		self.add_parameter('standard_deviation',
							label=f'place {placnum} standard deviation result',
							get_cmd=f'MEASurement{placnum}:RESult:STDDev?',
							get_parser=float)

		self.add_parameter('negative_peak',
							label=f'place {placnum} negative peak result',
							get_cmd=f'MEASurement{placnum}:RESult:NPEak?',
							get_parser=float)
						
		self.add_parameter('positive_peak',
							label=f'place {placnum} positive peak result',
							get_cmd=f'MEASurement{placnum}:RESult:PPEak?',
							get_parser=float)

		self.add_parameter('waveform_count',
							label=f'place {placnum} waveform count result',
							get_cmd=f'MEASurement{placnum}:RESult:WFMCount?',
							get_parser=float)

		self.add_parameter('statistics_weight',
							label=f'place {placnum} statistics buffer size',
							get_cmd=f'MEASurement{placnum}:STATistics:WEIGht?',
							get_parser=float)

		self.add_parameter('statistics_all',
							label=f'place {placnum} all statistics values',
							get_cmd=f'MEASurement{placnum}:STATistics:VALue:ALL?',
							get_parser=str.rstrip)

		self.add_parameter('statistics_name',
							label=f'place {placnum} statistics name',
							set_cmd=f'EXPort:MEASurement{placnum}:STATistics:NAME {{}}',
							get_cmd=f'EXPort:MEASurement{placnum}:STATistics:NAME?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('statistics_all_name',
							label='statistics all name',
							set_cmd='EXPort:MEASurement:STATistics:ALL:NAME {}',
							get_cmd='EXPort:MEASurement:STATistics:ALL:NAME?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

	def save(self): self.write(f'EXPort:MEASurement{placnum}:STATistics:SAVE')
	def allsave(self): self.write('EXPort:MEASurement:STATistics:ALL:SAVE')

class Measurement_Statistics(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, placnum, bufnum):
		super().__init__(parent, name)

		self.add_parameter('statistics_specified',
							label=f'place {placnum} buf {bufnum}specified statistics value',
							get_cmd=f'MEASurement{placnum}:STATistics:VALue{bufnum}?',
							get_parser=str.rstrip)

class Reference_Levels(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('relative_mode',
							label='reference level relative mode',
							set_cmd='REFLevel:RELative:MODE {}',
							get_cmd='REFLevel:RELative:MODE?',
							vals=vals.Enum('TEN', 'TWEN', 'FIVE', 'USER'),
							get_parser=str.rstrip)

		self.add_parameter('lower_level',
							label='reference level lower level',
							set_cmd='REFLevel:RELative:LOWer {}',
							get_cmd='REFLevel:RELative:LOWer?',
							vals=vals.Numbers(0,100),
							unit='%',
							get_parser=float)

		self.add_parameter('upper_level',
							label='reference level upper level',
							set_cmd='REFLevel:RELative:UPPer {}',
							get_cmd='REFLevel:RELative:UPPer?',
							vals=vals.Numbers(0,100),
							unit='%',
							get_parser=float)

		self.add_parameter('middle_level',
							label='reference level middle level',
							set_cmd='REFLevel:RELative:MIDDle {}',
							get_cmd='REFLevel:RELative:MIDDle?',
							vals=vals.Numbers(0,100),
							unit='%',
							get_parser=float)

# Applications

class Applications_Channel(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		mask_module=Mask(self, 'mask')
		self.add_submodule('mask', mask_module)

		mask_violation_module=Mask_Violation(self, 'mask_violation')
		self.add_submodule('mask_violation', mask_violation_module)

		mask_test_module=Mask_Test(self, 'mask_test')
		self.add_submodule('mask_test', mask_test_module)

		general_module=General(self, 'general')
		self.add_submodule('general', general_module)

		frequency_module=Frequency(self, 'frequency')
		self.add_submodule('frequency', frequency_module)

		time_module=Time(self, 'time')
		self.add_submodule('time', time_module)

		waveform_setting_module=Waveform_Setting(self, 'waveform_setting')
		self.add_submodule('waveform_setting', waveform_setting_module)

		waveform_data_query_module=Waveform_Data_Query(self, 'waveform_data_query')
		self.add_submodule('waveform_data_query', waveform_data_query_module)

		spectrogram_module=Spectrogram(self, 'spectrogram')
		self.add_submodule('spectrogram', spectrogram_module)

		peak_list_module=Peak_List(self, 'peak_list')
		self.add_submodule('peak_list', peak_list_module)

		reference_marker_module=Reference_Marker(self, 'reference_marker')
		self.add_submodule('reference_marker', reference_marker_module)

		display_module=Display(self, 'display')
		self.add_submodule('display', display_module)

		xy_waveforms_module=XY_Waveforms(self, 'xy_waveforms')
		self.add_submodule('xy_waveforms', xy_waveforms_module)

		trigger_counter_module=Trigger_Counter(self, 'trigger_counter')
		self.add_submodule('trigger_counter', trigger_counter_module)

		bode_settings_module=Bode_Settings(self, 'bode_settings')
		self.add_submodule('bode_settings', bode_settings_module)

		for i in range(1,50+1):
			peak_list_result_module=Peak_List_Result(self, f'peak_rs{i}', i)
			self.add_submodule(f'peak_rs{i}', peak_list_result_module)

		for i in range(1,4+1):
			digital_voltmeter_module=Digital_Voltmeter(self, f'volt_mt{i}', i)
			self.add_submodule(f'volt_mt{i}', digital_voltmeter_module)

		for i in range(1,50+1):
			bode_plot_module=Bode_Plot(self, f'bode_pt{i}', i)
			self.add_submodule(f'bode_pt{i}', bode_plot_module)

		for i in range(1,2+1):
			bode_marker_module=Bode_Marker(self, f'bode_mk{i}', i)
			self.add_submodule(f'bode_mk{i}', bode_marker_module)

class Bode_Marker(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, marknum):
		super().__init__(parent, name)

		self.add_parameter('difference_frequency',
							label=f'marker {marknum} frequency difference',
							get_cmd=f'BPLot:MARKer{marknum}:DIFFerence:FREQ?',
							get_parser=float)

		self.add_parameter('difference_gain',
							label=f'marker {marknum} gain difference',
							get_cmd=f'BPLot:MARKer{marknum}:DIFFerence:GAIN?',
							get_parser=float)

		self.add_parameter('difference_phase',
							label=f'marker {marknum} phase difference',
							get_cmd=f'BPLot:MARKer{marknum}:DIFFerence:PHASe?',
							get_parser=float)

		self.add_parameter('frequency',
							label=f'marker {marknum} frequency',
							set_cmd=f'BPLot:MARKer{marknum}:FREQuency {{}}',
							get_cmd=f'BPLot:MARKer{marknum}:FREQuency?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('gain',
							label=f'marker {marknum} gain',
							get_cmd=f'BPLot:MARKer{marknum}:GAIN?',
							get_parser=float)

		self.add_parameter('index',
							label=f'marker {marknum} index',
							set_cmd=f'BPLot:MARKer{marknum}:INDex {{}}',
							get_cmd=f'BPLot:MARKer{marknum}:INDex?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('phase',
							label=f'marker {marknum} phase',
							get_cmd=f'BPLot:MARKer{marknum}:PHASe?',
							get_parser=float)

	def screen(self): self.write(f'BPLot:MARKer{marknum}:SSCReen')

class Bode_Plot(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, plotnum):
		super().__init__(parent, name)

		self.add_parameter('state',
							label='bode plot state',
							set_cmd='BPLot:ENABle',
							get_cmd='BPLot:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('profile_count',
							label='bode plot amplitude profile count',
							set_cmd='BPLot:AMPLitude:PROFile:COUNt {}',
							get_cmd='BPLot:AMPLitude:PROFile:COUNt?',
							vals=vals.Ints(2,16),
							get_parser=int)

		self.add_parameter('profile_amplitude',
							label=f'plot {plotnum} bode plot amplitude profile amplitude count',
							set_cmd=f'BPLot:AMPLitude:PROFile:POINt{plotnum}:AMPLitude {{}}',
							get_cmd=f'BPLot:AMPLitude:PROFile:POINt{plotnum}:AMPLitude?',
							vals=vals.Numbers(),
							get_parser=str.rstrip)

		self.add_parameter('profile_frequency',
							label=f'plot {plotnum} bode plot amplitude profile frequency count',
							set_cmd=f'BPLot:AMPLitude:PROFile:POINt{plotnum}:FREQuency {{}}',
							get_cmd=f'BPLot:AMPLitude:PROFile:POINt{plotnum}:FREQuency?',
							vals=vals.Numbers(),
							get_parser=str.rstrip)

		self.add_parameter('mode',
							label='bode plot amplitude mode',
							set_cmd='BPLot:AMPLitude:MODE {}',
							get_cmd='BPLot:AMPLitude:MODE?',
							vals=vals.Enum('CONS', 'PROF'),
							get_parser=str.rstrip)

		self.add_parameter('frequency_data',
							label='bode plot frequency data',
							get_cmd='BPLot:FREQuency:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('frequency_start',
							label='bode plot start frequency',
							set_cmd='BPLot:FREQuency:STARt {}',
							get_cmd='BPLot:FREQuency:STARt?',
							vals=vals.Ints(10,int(25e6)),
							get_parser=int)

		self.add_parameter('frequency_stop',
							label='bode plot stop frequency',
							set_cmd='BPLot:FREQuency:STOP {}',
							get_cmd='BPLot:FREQuency:STOP?',
							vals=vals.Ints(10,int(25e6)),
							get_parser=int)

		self.add_parameter('input_source',
							label='bode plot input source',
							set_cmd='BPLot:INPut:SOURce {}',
							get_cmd='BPLot:INPut:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4'),
							get_parser=str.rstrip)
							
		self.add_parameter('measurement_delay',
							label='bode plot measurement delay',
							set_cmd='BPLot:MEASurement:DELay {}',
							get_cmd='BPLot:MEASurement:DELay?',
							vals=vals.Numbers(0,10),
							get_parser=float)

		self.add_parameter('measurement_point',
							label='bode plot measurement point',
							set_cmd='BPLot:MEASurement:POINt:DISPLAY {}',
							get_cmd='BPLot:MEASurement:POINt:DISPLAY?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('output_source',
							label='bode plot output source',
							set_cmd='BPLot:OUTPut:SOURce {}',
							get_cmd='BPLot:OUTPut:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4'),
							get_parser=str.rstrip)

		self.add_parameter('points_logarithmic',
							label='bode plot output source',
							set_cmd='BPLot:POINts:LOGarithmic {}',
							get_cmd='BPLot:POINts:LOGarithmic?',
							vals=vals.Ints(10,500),
							get_parser=int)

		self.add_parameter('repeat',
							label='bode plot repeat state',
							set_cmd='BPLot:REPeat {}',
							get_cmd='BPLot:REPeat?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('start',
							label='bode plot start',
							set_cmd='BPLot:STATe {}',
							get_cmd='BPLot:STATe?',
							vals=vals.Enum('RUN', 'STOP'),
							get_parser=str.rstrip)

	def autoscale(self): self.write('BPLot:AUToscale')
	def reset(self): self.write('BPLot:RESet')

class Bode_Settings(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('data',
							label='bode plot gain data',
							get_cmd='BPLot:GAIN:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('gain_state',
							label='bode plot gain state',
							set_cmd='BPLot:GAIN:ENABle {}',
							get_cmd='BPLot:GAIN:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('gain_position',
							label='bode plot gain position',
							set_cmd='BPLot:GAIN:POSition {}',
							get_cmd='BPLot:GAIN:POSition?',
							vals=vals.Numbers(-20.0,20.0),
							get_parser=float)

		self.add_parameter('gain_scale',
							label='bode plot gain scale',
							set_cmd='BPLot:GAIN:SCALe {}',
							get_cmd='BPLot:GAIN:SCALe?',
							vals=vals.Numbers(0.1,20.0),
							get_parser=float)

		self.add_parameter('phase_data',
							label='bode plot phase data',
							get_cmd='BPLot:PHASe:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('phase_state',
							label='bode plot phase state',
							get_cmd='BPLot:PHASe:ENABle?',
							get_parser=str.rstrip)

		self.add_parameter('phase_position',
							label='bode plot phase position',
							get_cmd='BPLot:PHASe:POSition?',
							get_parser=float)

		self.add_parameter('phase_scale',
							label='bode plot phase scale',
							get_cmd='BPLot:PHASe:SCALe?',
							get_parser=float)

		self.add_parameter('amplitude_state',
							label='bode plot amplitude state',
							set_cmd='BPLot:AMPLitude:ENABle {}',
							get_cmd='BPLot:AMPLitude:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('amplitude_position',
							label='bode plot amplitude position',
							set_cmd='BPLot:AMPLitude:POSition {}',
							get_cmd='BPLot:AMPLitude:POSition?',
							vals=vals.Numbers(-10,10),
							get_parser=float)

		self.add_parameter('amplitude_scale',
							label='bode plot amplitude scale',
							set_cmd='BPLot:AMPLitude:SCALe {}',
							get_cmd='BPLot:AMPLitude:SCALe?',
							vals=vals.Numbers(0.1,2.0),
							get_parser=float)

class Digital_Voltmeter(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, metnum):
		super().__init__(parent, name)

		self.add_parameter('status',
							label=f'meter {metnum} dvm status',
							set_cmd=f'DVM{metnum}:ENABle {{}}',
							get_cmd=f'DVM{metnum}:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('source',
							label=f'meter {metnum} dvm source',
							set_cmd=f'DVM{metnum}:SOURce {{}}',
							get_cmd=f'DVM{metnum}:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4'),
							get_parser=str.rstrip)

		self.add_parameter('type',
							label=f'meter {metnum} dvm type',
							set_cmd=f'DVM{metnum}:TYPE {{}}',
							get_cmd=f'DVM{metnum}:TYPE?',
							vals=vals.Enum('DC', 'ACDC', 'ACRM', 'OFF'),
							get_parser=str.rstrip)

		self.add_parameter('result',
							label=f'meter {metnum} dvm result',
							get_cmd=f'DVM{metnum}:RESult:ACTual?',
							get_parser=str.rstrip)

		self.add_parameter('result_status',
							label=f'meter {metnum} dvm result status',
							get_cmd=f'DVM{metnum}:RESult:ACTual:STATus?',
							get_parser=str.rstrip)

class Display(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('auto_rbw',
							label='auto resolution bandiwdth state',
							set_cmd='SPECtrum:FREQuency:BANDwidth:RESolution:AUTO {}',
							get_cmd='SPECtrum:FREQuency:BANDwidth:RESolution:AUTO?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('magnitude_mode',
							label='waveform magnitude coloring state',
							set_cmd='SPECtrum:DIAGram:COLor:MAGNitude:MODE {}',
							get_cmd='SPECtrum:DIAGram:COLor:MAGNitude:MODE?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('maximum_level',
							label='maximum of color scale',
							set_cmd='SPECtrum:DIAGram:COLor:MAXimum:LEVel {}',
							get_cmd='SPECtrum:DIAGram:COLor:MAXimum:LEVel?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('minimum_level',
							label='minimum of color scale',
							set_cmd='SPECtrum:DIAGram:COLor:MINimum:LEVel {}',
							get_cmd='SPECtrum:DIAGram:COLor:MINimum:LEVel?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('domain_color',
							label='domain color scheme',
							set_cmd='SPECtrum:DIAGram:COLor:SCHeme:FDOMain {}',
							get_cmd='SPECtrum:DIAGram:COLor:SCHeme:FDOMain?',
							vals=vals.Enum('MON', 'TEMP', 'RAIN'),
							get_parser=str.rstrip)

		self.add_parameter('spectrogram_color',
							label='spectrogram color scheme',
							set_cmd='SPECtrum:DIAGram:COLor:SCHeme:SPECtrogram {}',
							get_cmd='SPECtrum:DIAGram:COLor:SCHeme:SPECtrogram?',
							vals=vals.Enum('MON', 'TEMP', 'RAIN'),
							get_parser=str.rstrip)

		self.add_parameter('spectrogram_diagram',
							label='spectrogram diagram state',
							set_cmd='SPECtrum:DIAGram:SPECtrogram:ENABle {}',
							get_cmd='SPECtrum:DIAGram:SPECtrogram:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

class Frequency(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('center',
							label='frequency center',
							set_cmd='SPECtrum:FREQuency:CENTer {}',
							get_cmd='SPECtrum:FREQuency:CENTer?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('span',
							label='frequency span',
							set_cmd='SPECtrum:FREQuency:SPAN {}',
							get_cmd='SPECtrum:FREQuency:SPAN?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('start',
							label='start frequency',
							set_cmd='SPECtrum:FREQuency:STARt {}',
							get_cmd='SPECtrum:FREQuency:STARt?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('stop',
							label='stop frequency',
							set_cmd='SPECtrum:FREQuency:STOP {}',
							get_cmd='SPECtrum:FREQuency:STOP?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('resolution_bandwidth',
							label='frequency resolution bandwidth',
							set_cmd='SPECtrum:FREQuency:BANDwidth:RESolution:VALue {}',
							get_cmd='SPECtrum:FREQuency:BANDwidth:RESolution:VALue?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('rbw_ratio',
							label='frequency bandwidth resolution ratio',
							set_cmd='SPECtrum:FREQuency:BANDwidth:RESolution:RATio {}',
							get_cmd='SPECtrum:FREQuency:BANDwidth:RESolution:RATio?',
							vals=vals.Enum(1024,2048,4096,8192,16384,32768),
							get_parser=int)



	def fullspan(self): self.write('SPECtrum:FREQuency:FULLspan')

class General(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('state',
							label='spectrum analysis state',
							set_cmd='SPECtrum:STATe {}',
							get_cmd='SPECtrum:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('source',
							label='spectrum analysis source',
							set_cmd='SPECtrum:SOURce {}',
							get_cmd='SPECtrum:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4'),
							get_parser=str.rstrip)

		self.add_parameter('frequency_type',
							label='spectrum analysis frequency window type',
							set_cmd='SPECtrum:FREQuency:WINDow:TYPE {}',
							get_cmd='SPECtrum:FREQuency:WINDow:TYPE?',
							vals=vals.Enum('RECT', 'HAMM', 'HANN', 'BLAC', 'FLAT'),
							get_parser=str.rstrip)

		self.add_parameter('frequency_magnitude_scale',
							label='spectrum analysis frequency scale magnitude',
							set_cmd='SPECtrum:FREQuency:MAGNitude:SCALe {}',
							get_cmd='SPECtrum:FREQuency:MAGNitude:SCALe?',
							vals=vals.Enum('LIN', 'DBM', 'DBV', 'DBUV'),
							get_parser=str.rstrip)

		self.add_parameter('frequency_position',
							label='spectrum analysis frequency position',
							set_cmd='SPECtrum:FREQuency:POSition {}',
							get_cmd='SPECtrum:FREQuency:POSition?',
							vals=vals.Numbers(),
							unit='div',
							get_parser=float)

		self.add_parameter('frequency_scale',
							label='spectrum analysis frequency scale',
							set_cmd='SPECtrum:FREQuency:SCALe {}',
							get_cmd='SPECtrum:FREQuency:SCALe?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('bar_position',
							label='spectrum analysis bar position',
							set_cmd='DISPlay:CBAR:FFT:POSition {}',
							get_cmd='DISPlay:CBAR:FFT:POSition?',
							vals=vals.Ints(0,800),
							unit='px',
							get_parser=int)

class Mask(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('state',
							label='mask state',
							set_cmd='MASK:STATe {}',
							get_cmd='MASK:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('source',
							label='mask source',
							set_cmd='MASK:SOURce {}',
							get_cmd='MASK:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4'),
							get_parser=str.rstrip)

		self.add_parameter('y_position',
							label='mask y position',
							set_cmd='MASK:YPOSition {}',
							get_cmd='MASK:YPOSition?',
							vals=vals.Numbers(),
							unit='div',
							get_parser=float)

		self.add_parameter('y_scale',
							label='mask y scale',
							set_cmd='MASK:YSCale {}',
							get_cmd='MASK:YSCale?',
							vals=vals.Numbers(),
							unit='%',
							get_parser=float)

		self.add_parameter('x_addition',
							label='mask x addition',
							set_cmd='MASK:XWIDth {}',
							get_cmd='MASK:XWIDth?',
							vals=vals.Numbers(),
							unit='div',
							get_parser=float)

		self.add_parameter('y_addition',
							label='mask y addition',
							set_cmd='MASK:YWIDth {}',
							get_cmd='MASK:YWIDth?',
							vals=vals.Numbers(),
							unit='div',
							get_parser=float)

		self.add_parameter('save',
							label='mask save',
							set_cmd='MASK:SAVE {}',
							vals=vals.Strings())

		self.add_parameter('load',
							label='mask load',
							set_cmd='MASK:LOAD {}',
							vals=vals.Strings())

	def copy(self): self.write('MASK:CHCopy')

class Mask_Test(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('test',
							label='mask test',
							set_cmd='MASK:TEST {}',
							get_cmd='MASK:TEST?',
							vals=vals.Enum('RUN', 'STOP', 'PAUS'),
							get_parser=str.rstrip)

		self.add_parameter('count',
							label='mask count',
							get_cmd='MASK:COUNt?',
							get_parser=int)

		self.add_parameter('hit_count',
							label='mask test hit count',
							get_cmd='MASK:VCOunt?',
							get_parser=int)

		self.add_parameter('mode',
							label='mask test mode',
							set_cmd='MASK:CAPTure:MODE {}',
							get_cmd='MASK:CAPTure:MODE?',
							vals=vals.Enum('ALL', 'FAILED'),
							get_parser=str.rstrip)

	def reset(self): self.write('MASK:RESet:COUNter')

class Mask_Violation(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('sound_mode',
							label='event sound mode',
							set_cmd='MASK:ACTion:SOUNd:EVENt:MODE {}',
							get_cmd='MASK:ACTion:SOUNd:EVENt:MODE?',
							vals=vals.Enum('OFF', 'EACH'),
							get_parser=str.rstrip)

		self.add_parameter('screensave_mode',
							label='event screensave mode',
							set_cmd='MASK:ACTion:SCRSave:EVENt:MODE {}',
							get_cmd='MASK:ACTion:SCRSave:EVENt:MODE?',
							vals=vals.Enum('OFF', 'EACH'),
							get_parser=str.rstrip)

		self.add_parameter('waveform_mode',
							label='event waveform save mode',
							set_cmd='MASK:ACTion:WFMSave:EVENt:MODE {}',
							get_cmd='MASK:ACTion:WFMSave:EVENt:MODE?',
							vals=vals.Enum('OFF', 'EACH'),
							get_parser=str.rstrip)

		self.add_parameter('pulse_mode',
							label='event pulse mode',
							set_cmd='MASK:ACTion:PULSe:EVENt:MODE {}',
							get_cmd='MASK:ACTion:PULSe:EVENt:MODE?',
							vals=vals.Enum('OFF', 'EACH'),
							get_parser=str.rstrip)

		self.add_parameter('stop_mode',
							label='event stop mode',
							set_cmd='MASK:ACTion:STOP:EVENt:MODE {}',
							get_cmd='MASK:ACTion:STOP:EVENt:MODE?',
							vals=vals.Enum('OFF', 'CYCL'),
							get_parser=str.rstrip)

		self.add_parameter('stop_count',
							label='event stop count',
							set_cmd='MASK:ACTion:STOP:EVENt:COUNt {}',
							get_cmd='MASK:ACTion:STOP:EVENt:COUNt?',
							vals=vals.Ints(),
							get_parser=int)

		self.add_parameter('screensave_destination',
							label='event screensave destination',
							set_cmd='MASK:ACTion:SCRSave:DESTination {}',
							get_cmd='MASK:ACTion:SCRSave:DESTination?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('waveform_destination',
							label='event waveform save destination',
							set_cmd='MASK:ACTion:WFMSave:DESTination {}',
							get_cmd='MASK:ACTion:WFMSave:DESTination?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('mode_state',
							label='event mode state',
							set_cmd='MASK:ACTion:YOUT:ENABle {}',
							get_cmd='MASK:ACTion:YOUT:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

class Peak_List(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('table_state',
							label='results table state',
							set_cmd='SPECtrum:MARKer:RTABle:ENABle {}',
							get_cmd='SPECtrum:MARKer:RTABle:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('marker_state',
							label='marker state',
							set_cmd='SPECtrum:MARKer:ENABle {}',
							get_cmd='SPECtrum:MARKer:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('marker_source',
							label='marker source',
							set_cmd='SPECtrum:MARKer:SOURce {}',
							get_cmd='SPECtrum:MARKer:SOURce?',
							vals=vals.Enum('SPEC', 'MINH', 'MAXH', 'AVER'),
							get_parser=str.rstrip)

		self.add_parameter('setup_mode',
							label='marker setup mode',
							set_cmd='SPECtrum:MARKer:SETup:MMODe {}',
							get_cmd='SPECtrum:MARKer:SETup:MMODe?',
							vals=vals.Enum('LONL', 'ADV'),
							get_parser=str.rstrip)

		self.add_parameter('setup_level',
							label='marker minimum level setup',
							set_cmd='SPECtrum:MARKer:SETup:MLEVel {}',
							get_cmd='SPECtrum:MARKer:SETup:MLEVel?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('setup_distance',
							label='marker distance setup',
							set_cmd='SPECtrum:MARKer:SETup:DISTance {}',
							get_cmd='SPECtrum:MARKer:SETup:DISTance?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('setup_excursion',
							label='marker excursion setup',
							set_cmd='SPECtrum:MARKer:SETup:EXCursion {}',
							get_cmd='SPECtrum:MARKer:SETup:EXCursion?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('setup_maxwidth',
							label='marker maximum width setup',
							set_cmd='SPECtrum:MARKer:SETup:MWIDth {}',
							get_cmd='SPECtrum:MARKer:SETup:MWIDth?',
							vals=vals.Numbers(),
							get_parser=float)

	def center_peak(self): self.write('SPECtrum:MARKer:REFerence:SETup:CMPeak')
	def center_screen(self): self.write('SPECtrum:MARKer:REFerence:SETup:CSCReen')

class Peak_List_Result(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, resnum):
		super().__init__(parent, name)

		self.add_parameter('marker_count',
							label='detected peaks number',
							get_cmd='SPECtrum:MARKer:RCOunt?',
							get_parser=float)

		self.add_parameter('marker_result',
							label=f'result {resnum} nth marker results',
							get_cmd=f'SPECtrum:MARKer:RESult{resnum}?',
							get_parser=str.rstrip)

		self.add_parameter('marker_all',
							label=f'result {resnum} all results',
							get_cmd=f'SPECtrum:MARKer:RESult{resnum}:ALL?',
							get_parser=str.rstrip)

		self.add_parameter('marker_all_delta',
							label=f'result {resnum} all delta results',
							get_cmd=f'SPECtrum:MARKer:RESult{resnum}:ALL:DELTa?',
							get_parser=str.rstrip)

		self.add_parameter('marker_delta',
							label=f'result {resnum} delta result',
							get_cmd=f'SPECtrum:MARKer:RESult{resnum}:DELTa?',
							get_parser=str.rstrip)

		self.add_parameter('marker_frequency',
							label=f'result {resnum} frequency result',
							get_cmd=f'SPECtrum:MARKer:RESult{resnum}:FREQuency?',
							get_parser=str.rstrip)

		self.add_parameter('marker_frequency_delta',
							label=f'result {resnum} marker frequency delta',
							get_cmd=f'SPECtrum:MARKer:RESult{resnum}:FREQuency:DELTa?',
							get_parser=str.rstrip)

		self.add_parameter('marker_level',
							label=f'result {resnum} marker level result',
							get_cmd=f'SPECtrum:MARKer:RESult{resnum}:LEVel?',
							get_parser=str.rstrip)

		self.add_parameter('marker_level_delta',
							label=f'result {resnum} marker level delta result',
							get_cmd=f'SPECtrum:MARKer:RESult{resnum}:LEVel:DELTa?',
							get_parser=str.rstrip)

class Reference_Marker(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('reference_mode',
							label='reference peak mode',
							set_cmd='SPECtrum:MARKer:REFerence:SETup:MODE {}',
							get_cmd='SPECtrum:MARKer:REFerence:SETup:MODE?',
							vals=vals.Enum('OFF', 'IND', 'RANG'),
							get_parser=str.rstrip)

		self.add_parameter('reference_index',
							label='reference peak index',
							set_cmd='SPECtrum:MARKer:REFerence:SETup:INDex {}',
							get_cmd='SPECtrum:MARKer:REFerence:SETup:INDex?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('reference_frequency',
							label='reference peak frequency',
							set_cmd='SPECtrum:MARKer:REFerence:SETup:FREQuency {}',
							get_cmd='SPECtrum:MARKer:REFerence:SETup:FREQuency?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('reference_span',
							label='reference span range',
							set_cmd='SPECtrum:MARKer:REFerence:SETup:SPAN {}',
							get_cmd='SPECtrum:MARKer:REFerence:SETup:SPAN?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('marker_values',
							label='reference marker values',
							get_cmd='SPECtrum:MARKer:RMARker?',
							get_parser=str.rstrip)

		self.add_parameter('marker_frequency',
							label='reference marker frequency',
							get_cmd='SPECtrum:MARKer:RMARker:FREQuency?',
							get_parser=float)

		self.add_parameter('marker_level',
							label='reference marker level',
							get_cmd='SPECtrum:MARKer:RMARker:LEVel?',
							get_parser=float)

		self.add_parameter('result_mode',
							label='reference marker result mode',
							set_cmd='SPECtrum:MARKer:RMODe {}',
							get_cmd='SPECtrum:MARKer:RMODe?',
							vals=vals.Enum('ABS', 'FREQ', 'LEV', 'FLEV'),
							get_parser=str.rstrip)

class Spectrogram(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('mode',
							label='spectrogram mode',
							set_cmd='SPECtrum:MODE {}',
							get_cmd='SPECtrum:MODE?',
							vals=vals.Enum('FFT', 'SPEC'),
							get_parser=str.rstrip)

		self.add_parameter('scale',
							label='spectrogram scale',
							set_cmd='SPECtrum:SPECtrogram:SCALe {}',
							get_cmd='SPECtrum:SPECtrogram:SCALe?',
							vals=vals.Ints(1,20),
							get_parser=int)

		self.add_parameter('position',
							label='spectrogram position',
							set_cmd='DISPlay:CBAR:SPECtrogram:POSition {}',
							get_cmd='DISPlay:CBAR:SPECtrogram:POSition?',
							vals=vals.Ints(0,800),
							unit='px',
							get_parser=int)

	def reset(self): self.write('SPECtrum:SPECtrogram:RESet')

class Time(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('time_position',
							label='spectrum time position',
							set_cmd='SPECtrum:TIME:POSition {}',
							get_cmd='SPECtrum:TIME:POSition?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('time_range',
							label='spectrum time range',
							set_cmd='SPECtrum:TIME:RANGe {}',
							get_cmd='SPECtrum:TIME:RANGe?',
							vals=vals.Numbers(),
							get_parser=float)

class Trigger_Counter(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('status',
							label='trigger counter status',
							set_cmd='TCOunter:ENABle {}',
							get_cmd='TCOunter:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('source',
							label='trigger counter source',
							set_cmd='TCOunter:SOURce {}',
							get_cmd='TCOunter:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'TRIG'),
							get_parser=str.rstrip)

		self.add_parameter('frequency_result',
							label='trigger counter frequency result',
							get_cmd='TCOunter:RESult:ACTual:FREQuency?',
							get_parser=float)

		self.add_parameter('period_result',
							label='trigger counter period result',
							get_cmd='TCOunter:RESult:ACTual:PERiod?',
							get_parser=float)

class Waveform_Data_Query(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('average_data',
							label='average data query',
							get_cmd='SPECtrum:WAVeform:AVERage:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('maximum_data',
							label='maximum data query',
							get_cmd='SPECtrum:WAVeform:MAXimum:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('minimum_data',
							label='minimum data query',
							get_cmd='SPECtrum:WAVeform:MINimum:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('spectrum_data',
							label='spectrum data query',
							get_cmd='SPECtrum:WAVeform:SPECtrum:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('average_header',
							label='average data header',
							get_cmd='SPECtrum:WAVeform:AVERage:DATA:HEADer?',
							get_parser=str.rstrip)

		self.add_parameter('maximum_header',
							label='maximum data header',
							get_cmd='SPECtrum:WAVeform:MAXimum:DATA:HEADer?',
							get_parser=str.rstrip)

		self.add_parameter('minimum_header',
							label='minimum data header',
							get_cmd='SPECtrum:WAVeform:MINimum:DATA:HEADer?',
							get_parser=str.rstrip)

		self.add_parameter('spectrum_header',
							label='spectrum data header',
							get_cmd='SPECtrum:WAVeform:SPECtrum:DATA:HEADer?',
							get_parser=str.rstrip)

		self.add_parameter('average_points',
							label='average data points',
							get_cmd='SPECtrum:WAVeform:AVERage:DATA:POINts?',
							get_parser=str.rstrip)

		self.add_parameter('maximum_points',
							label='maximum data points',
							get_cmd='SPECtrum:WAVeform:MAXimum:DATA:POINts?',
							get_parser=str.rstrip)

		self.add_parameter('minimum_points',
							label='minimum data points',
							get_cmd='SPECtrum:WAVeform:MINimum:DATA:POINts?',
							get_parser=str.rstrip)

		self.add_parameter('spectrum_points',
							label='spectrum data points',
							get_cmd='SPECtrum:WAVeform:SPECtrum:DATA:POINts?',
							get_parser=str.rstrip)

		self.add_parameter('average_x_increment',
							label='average data x increment',
							get_cmd='SPECtrum:WAVeform:AVERage:DATA:XINCrement?',
							get_parser=str.rstrip)

		self.add_parameter('maximum_x_increment',
							label='maximum data x increment',
							get_cmd='SPECtrum:WAVeform:MAXimum:DATA:XINCrement?',
							get_parser=str.rstrip)

		self.add_parameter('minimum_x_increment',
							label='minimum data x increment',
							get_cmd='SPECtrum:WAVeform:MINimum:DATA:XINCrement?',
							get_parser=str.rstrip)

		self.add_parameter('spectrum_x_increment',
							label='spectrum data x increment',
							get_cmd='SPECtrum:WAVeform:SPECtrum:DATA:XINCrement?',
							get_parser=str.rstrip)

		self.add_parameter('average_x_origin',
							label='average data x origin',
							get_cmd='SPECtrum:WAVeform:AVERage:DATA:XORigin?',
							get_parser=str.rstrip)

		self.add_parameter('maximum_x_origin',
							label='maximum data x origin',
							get_cmd='SPECtrum:WAVeform:MAXimum:DATA:XORigin?',
							get_parser=str.rstrip)

		self.add_parameter('minimum_x_origin',
							label='minimum data x origin',
							get_cmd='SPECtrum:WAVeform:MINimum:DATA:XORigin?',
							get_parser=str.rstrip)

		self.add_parameter('spectrum_x_origin',
							label='spectrum data x origin',
							get_cmd='SPECtrum:WAVeform:SPECtrum:DATA:XORigin?',
							get_parser=str.rstrip)

		self.add_parameter('average_y_increment',
							label='average data y increment',
							get_cmd='SPECtrum:WAVeform:AVERage:DATA:YINCrement?',
							get_parser=str.rstrip)

		self.add_parameter('maximum_y_increment',
							label='maximum data y increment',
							get_cmd='SPECtrum:WAVeform:MAXimum:DATA:YINCrement?',
							get_parser=str.rstrip)

		self.add_parameter('minimum_y_increment',
							label='minimum data y increment',
							get_cmd='SPECtrum:WAVeform:MINimum:DATA:YINCrement?',
							get_parser=str.rstrip)

		self.add_parameter('spectrum_y_increment',
							label='spectrum data y increment',
							get_cmd='SPECtrum:WAVeform:SPECtrum:DATA:YINCrement?',
							get_parser=str.rstrip)

		self.add_parameter('average_y_origin',
							label='average data y origin',
							get_cmd='SPECtrum:WAVeform:AVERage:DATA:YORigin?',
							get_parser=str.rstrip)

		self.add_parameter('maximum_y_origin',
							label='maximum data y origin',
							get_cmd='SPECtrum:WAVeform:MAXimum:DATA:YORigin?',
							get_parser=str.rstrip)

		self.add_parameter('minimum_y_origin',
							label='minimum data y origin',
							get_cmd='SPECtrum:WAVeform:MINimum:DATA:YORigin?',
							get_parser=str.rstrip)

		self.add_parameter('spectrum_y_origin',
							label='spectrum data y origin',
							get_cmd='SPECtrum:WAVeform:SPECtrum:DATA:YORigin?',
							get_parser=str.rstrip)

		self.add_parameter('average_y_resolution',
							label='average data y resolution',
							get_cmd='SPECtrum:WAVeform:AVERage:DATA:YRESolution?',
							get_parser=str.rstrip)

		self.add_parameter('maximum_y_resolution',
							label='maximum data y resolution',
							get_cmd='SPECtrum:WAVeform:MAXimum:DATA:YRESolution?',
							get_parser=str.rstrip)

		self.add_parameter('minimum_y_resolution',
							label='minimum data y resolution',
							get_cmd='SPECtrum:WAVeform:MINimum:DATA:YRESolution?',
							get_parser=str.rstrip)

		self.add_parameter('spectrum_y_resolution',
							label='spectrum data y resolution',
							get_cmd='SPECtrum:WAVeform:SPECtrum:DATA:YRESolution?',
							get_parser=str.rstrip)

class Waveform_Setting(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('average',
							label='average state',
							set_cmd='SPECtrum:WAVeform:AVERage:ENABle {}',
							get_cmd='SPECtrum:WAVeform:AVERage:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('maximum',
							label='maximum state',
							set_cmd='SPECtrum:WAVeform:MAXimum:ENABle {}',
							get_cmd='SPECtrum:WAVeform:MAXimum:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('minimum',
							label='minimum state',
							set_cmd='SPECtrum:WAVeform:MINimum:ENABle {}',
							get_cmd='SPECtrum:WAVeform:MINimum:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('spectrum',
							label='spectrum state',
							set_cmd='SPECtrum:WAVeform:SPECtrum:ENABle {}',
							get_cmd='SPECtrum:WAVeform:SPECtrum:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('average_count',
							label='frequency average count',
							set_cmd='SPECtrum:FREQuency:AVERage:COUNt {}',
							get_cmd='SPECtrum:FREQuency:AVERage:COUNt?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('average_complete',
							label='frequency average completion state',
							get_cmd='SPECtrum:FREQuency:AVERage:COMPlete?',
							get_parser=str.rstrip)

	def reset(self): self.write('SPECtrum:FREQuency:RESet')

class XY_Waveforms(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('mode',
							label='diagram mode',
							set_cmd='DISPlay:MODE {}',
							get_cmd='DISPlay:MODE?',
							vals=vals.Enum('YT', 'XY'),
							get_parser=str.rstrip)

		self.add_parameter('xy_xsource',
							label='xy x source',
							set_cmd='DISPlay:XY:XSOurce {}',
							get_cmd='DISPlay:XY:XSOurce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4'),
							get_parser=str.rstrip)

		self.add_parameter('y1_source',
							label='xy y1 source',
							set_cmd='DISPlay:XY:Y1Source {}',
							get_cmd='DISPlay:XY:Y1Source?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4'),
							get_parser=str.rstrip)

		self.add_parameter('y2_source',
							label='xy y2 source',
							set_cmd='DISPlay:XY:Y2Source {}',
							get_cmd='DISPlay:XY:Y2Source?',
							vals=vals.Enum('NONE', 'CH1', 'CH2', 'CH3', 'CH4'),
							get_parser=str.rstrip)

# Documenting

class Documenting_Channel(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		format_module=Format(self, 'format')
		self.add_submodule('format', format_module)

		mask_data_module=Mask_Data(self, 'mask_data')
		self.add_submodule('mask_data', mask_data_module)

		logic_mask_module=Logic_Mask(self, 'logic_mask')
		self.add_submodule('logic_mask', logic_mask_module)

		waveform_export_module=Waveform_Export(self, 'waveform_export')
		self.add_submodule('waveform_export', waveform_export_module)

		screenshot_module=Screenshot(self, 'screenshot')
		self.add_submodule('screenshot', screenshot_module)

		mass_memory_module=Mass_Memory(self, 'mass_memory')
		self.add_submodule('mass_memory', mass_memory_module)

		for i in range(1,4+1):
			analog_module=Analog(self, f'analog_ch{i}', i)
			self.add_submodule(f'analog_ch{i}', analog_module)

			logic_channel_module=Logic_Channel(self, f'logic_ch{i}', i)
			self.add_submodule(f'logic_ch{i}', logic_channel_module)

		for i in range(1,4+1):
			reference_waveform_module=Reference_Waveform(self, f'ref_rf{i}', i)
			self.add_submodule(f'ref_rf{i}', reference_waveform_module)

			logic_reference_module=Logic_Reference(self, f'logic_rf{i}', i)
			self.add_submodule(f'logic_rf{i}', logic_reference_module)

		for i in range(1,5+1):
			logic_math_module=Logic_Math(self, f'logic_lv{i}', i)
			self.add_submodule(f'logic_lv{i}', logic_math_module)

		for i in range(0,15+1):
			logic_digital_module=Logic_Digital(self, f'logic_dg{i}', i)
			self.add_submodule(f'logic_dg{i}', logic_digital_module)
			
		for i in range(1,2+1):
			logic_pod_module=Logic_Pod(self, f'logic_pd{i}', i)
			self.add_submodule(f'logic_pd{i}', logic_pod_module)

class Analog(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, channum):
		super().__init__(parent, name)

		self.add_parameter('data',
							label=f'channel {channum} data',
							get_cmd=f'CHANnel{channum}:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('header',
							label=f'channel {channum} header',
							get_cmd=f'CHANnel{channum}:DATA:HEADer?',
							get_parser=str.rstrip)

		self.add_parameter('data_points',
							label=f'channel {channum} data points',
							set_cmd=f'CHANnel{channum}:DATA:POINts {{}}',
							get_cmd=f'CHANnel{channum}:DATA:POINts?',
							vals=vals.Enum('DEF', 'MAX', 'DMAX'),
							get_parser=str.rstrip)

		self.add_parameter('data_envelope',
							label=f'channel {channum} data envelope',
							get_cmd=f'CHANnel{channum}:DATA:ENVelope?',
							get_parser=str.rstrip)

		self.add_parameter('envelope_header',
							label=f'channel {channum} daata envelope header',
							get_cmd=f'CHANnel{channum}:DATA:ENVelope:HEADer?',
							get_parser=str.rstrip)

		self.add_parameter('math_data',
							label=f'channel {channum} math data',
							get_cmd=f'CALCulate:MATH{channum}:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('math_header',
							label=f'channel {channum} math data header',
							get_cmd=f'CALCulate:MATH{channum}:DATA:HEADer?',
							get_parser=str.rstrip)

		self.add_parameter('math_points',
							label=f'channel {channum} math data points',
							get_cmd=f'CALCulate:MATH{channum}:DATA:POINts?',
							get_parser=str.rstrip)

class Format(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('border',
							label='format border',
							set_cmd='FORMat:BORDer {}',
							get_cmd='FORMat:BORDer?',
							vals=vals.Enum('MSBF', 'LSBF'),
							get_parser=str.rstrip)

class Logic_Channel(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, channum):
		super().__init__(parent, name)

		self.add_parameter('x_origin',
							label=f'channel {channum} x origin',
							get_cmd=f'CHANnel{channum}:DATA:XORigin?',
							get_parser=float)

		self.add_parameter('envelope_x_origin',
							label=f'channel {channum} envelope x origin',
							get_cmd=f'CHANnel{channum}:DATA:ENVelope:XORigin?',
							get_parser=float)

		self.add_parameter('x_increment',
							label=f'channel {channum} x increment',
							get_cmd=f'CHANnel{channum}:DATA:XINCrement?',
							get_parser=float)

		self.add_parameter('envelope_x_increment',
							label=f'channel {channum} envelope x increment',
							get_cmd=f'CHANnel{channum}:DATA:ENVelope:XINCrement?',
							get_parser=float)

		self.add_parameter('y_origin',
							label=f'channel {channum} y origin',
							get_cmd=f'CHANnel{channum}:DATA:YORigin?',
							get_parser=float)

		self.add_parameter('envlope_y_origin',
							label=f'channel {channum} envelope y origin',
							get_cmd=f'CHANnel{channum}:DATA:ENVelope:YORigin?',
							get_parser=float)

		self.add_parameter('y_increment',
							label=f'channel {channum} y increment',
							get_cmd=f'CHANnel{channum}:DATA:YINCrement?',
							get_parser=float)

		self.add_parameter('envelope_y_increment',
							label=f'channel {channum} envelope y increment',
							get_cmd=f'CHANnel{channum}:DATA:ENVelope:YINCrement?',
							get_parser=float)

		self.add_parameter('y_resolution',
							label=f'channel {channum} y resolution',
							get_cmd=f'CHANnel{channum}:DATA:YRESolution?',
							get_parser=str.rstrip)

		self.add_parameter('envelope_y_resolution',
							label=f'channel {channum} envelope y resolution',
							get_cmd=f'CHANnel{channum}:DATA:ENVelope:YRESolution?',
							get_parser=str.rstrip)
		
class Logic_Digital(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, lognum):
		super().__init__(parent, name)

		self.add_parameter('x_origin',
							label=f'logic {lognum} x origin',
							get_cmd=f'DIGital{lognum}:DATA:XORigin?',
							get_parser=float)

		self.add_parameter('x_increment',
							label=f'logic {lognum} x increment',
							get_cmd=f'DIGital{lognum}:DATA:XINCrement?',
							get_parser=float)

		self.add_parameter('y_origin',
							label=f'logic {lognum} y origin',
							get_cmd=f'DIGital{lognum}:DATA:YORigin?',
							get_parser=float)

		self.add_parameter('y_increment',
							label=f'logic {lognum} y increment',
							get_cmd=f'DIGital{lognum}:DATA:YINCrement?',
							get_parser=float)

		self.add_parameter('y_resolution',
							label=f'logic {lognum} y resolution',
							get_cmd=f'DIGital{lognum}:DATA:YRESolution?',
							get_parser=str.rstrip)

class Logic_Mask(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('x_origin',
							label='x origin',
							get_cmd='MASK:DATA:XORigin?',
							get_parser=float)

		self.add_parameter('x_increment',
							label='x increment',
							get_cmd='MASK:DATA:XINCrement?',
							get_parser=float)

		self.add_parameter('y_origin',
							label='y origin',
							get_cmd='MASK:DATA:YORigin?',
							get_parser=float)

		self.add_parameter('y_increment',
							label='y increment',
							get_cmd='MASK:DATA:YINCrement?',
							get_parser=float)

		self.add_parameter('y_resolution',
							label='y resolution',
							get_cmd='MASK:DATA:YRESolution?',
							get_parser=str.rstrip)

class Logic_Math(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, levnum):
		super().__init__(parent, name)

		self.add_parameter('x_origin',
							label=f'level {levnum} x origin',
							get_cmd=f'CALCulate:MATH{levnum}:DATA:XORigin?',
							get_parser=float)

		self.add_parameter('x_increment',
							label=f'level {levnum} x increment',
							get_cmd=f'CALCulate:MATH{levnum}:DATA:XINCrement?',
							get_parser=float)

		self.add_parameter('y_origin',
							label=f'level {levnum} y origin',
							get_cmd=f'CALCulate:MATH{levnum}:DATA:YORigin?',
							get_parser=float)

		self.add_parameter('y_increment',
							label=f'level {levnum} y increment',
							get_cmd=f'CALCulate:MATH{levnum}:DATA:YINCrement?',
							get_parser=float)

		self.add_parameter('y_resolution',
							label=f'level {levnum} y resolution',
							get_cmd=f'CALCulate:MATH{levnum}:DATA:YRESolution?',
							get_parser=str.rstrip)

class Logic_Pod(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, podnum):
		super().__init__(parent, name)

		self.add_parameter('x_origin',
							label=f'pod {podnum} x origin',
							get_cmd=f'LOGic{podnum}:DATA:XORigin?',
							get_parser=float)

		self.add_parameter('x_increment',
							label=f'pod {podnum} x increment',
							get_cmd=f'LOGic{podnum}:DATA:XINCrement?',
							get_parser=float)

		self.add_parameter('y_origin',
							label=f'pod {podnum} y origin',
							get_cmd=f'LOGic{podnum}:DATA:YORigin?',
							get_parser=float)

		self.add_parameter('y_increment',
							label=f'pod {podnum} y increment',
							get_cmd=f'LOGic{podnum}:DATA:YINCrement?',
							get_parser=float)

		self.add_parameter('y_resolution',
							label=f'pod {podnum} y resolution',
							get_cmd=f'LOGic{podnum}:DATA:YRESolution?',
							get_parser=str.rstrip)

class Logic_Reference(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, refnum):
		super().__init__(parent, name)

		self.add_parameter('x_origin',
							label=f'reference {refnum} x origin',
							get_cmd=f'REFCurve{refnum}:DATA:XORigin?',
							get_parser=float)

		self.add_parameter('x_increment',
							label=f'reference {refnum} x increment',
							get_cmd=f'REFCurve{refnum}:DATA:XINCrement?',
							get_parser=float)

		self.add_parameter('y_origin',
							label=f'reference {refnum} y origin',
							get_cmd=f'REFCurve{refnum}:DATA:YORigin?',
							get_parser=float)

		self.add_parameter('y_increment',
							label=f'reference {refnum} y increment',
							get_cmd=f'REFCurve{refnum}:DATA:YINCrement?',
							get_parser=float)

		self.add_parameter('y_resolution',
							label=f'reference {refnum} y resolution',
							get_cmd=f'REFCurve{refnum}:DATA:YRESolution?',
							get_parser=str.rstrip)

class Mask_Data(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('data',
							label='mask data',
							get_cmd='MASK:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('data_header',
							label='mask data header',
							get_cmd='MASK:DATA:HEADer?',
							get_parser=str.rstrip)

class Mass_Memory(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('drives',
							label='mass memory storage devices',
							get_cmd='MMEMory:DRIVes?',
							get_parser=str.rstrip)

		self.add_parameter('drive',
							label='mass memory storage location',
							set_cmd='MMEMory:MSIS {}',
							get_cmd='MMEMory:MSIS?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('new_directory',
							label='mass memory new directory name',
							set_cmd='MMEMory:MDIRectory {}',
							vals=vals.Strings())

		self.add_parameter('current_directory',
							label='mass memory current directory name',
							set_cmd='MMEMory:CDIRectory {}',
							get_cmd='MMEMory:CDIRectory?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('delete_directory',
							label='mass memory delete directory',
							set_cmd='MMEMory:RDIRectory {}',
							vals=vals.Strings())

		self.add_parameter('data_catalog',
							label='mass memory data catalog',
							get_cmd='MMEMory:DCATalog?',
							get_parser=str.rstrip)

		self.add_parameter('catalog_length',
							label='mass memory data catalog length',
							get_cmd='MMEMory:DCATalog:LENGth? {}',
							get_parser=str.rstrip)

		self.add_parameter('catalog',
							label='mass memory catalog',
							get_cmd='MMEMory:CATalog?',
							get_parser=str.rstrip)

		self.add_parameter('length',
							label='mass memory catalog length',
							get_cmd='MMEMory:CATalog:LENGth?',
							get_parser=str.rstrip)

		self.add_parameter('_copy',
							label='mass memory copy',
							set_cmd='MMEMory:COPY {}')

		self.add_parameter('_move',
							label='mass memory move',
							set_cmd='MMEMory:MOVE {}')

		self.add_parameter('delete',
							label='mass memory delete',
							set_cmd='MMEMory:DELete {}',
							vals=vals.Strings())

		self.add_parameter('_data',
							label='mass memory data',
							set_cmd='MMEMory:DATA {}',
							get_cmd='MMEMory:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('_store_state',
							label='mass memory store state',
							set_cmd='MMEMory:STORe:STATe {}')

		self.add_parameter('_load_state',
							label='mass memory load state',
							set_cmd='MMEMory:LOAD:STATe {}')

	def copy(self, filesource, filedestination):
		'''
		Copy parameter wrapper
		Args:
			filesource
			filedestination
		'''
		vals.Strings().validate(filesource)
		vals.Strings().validate(filedestination)
		input=f'{filesource}, {filedestination}'
		self._copy(input)

	def move(self, filesource, filedestination):
		'''
		Move parameter wrapper
		Args:
			filesource
			filedestination
		'''
		vals.Strings().validate(filesource)
		vals.Strings().validate(filedestination)
		input=f'{filesource}, {filedestination}'
		self._move(input)

	def data(self, filename, data):
		'''
		Data parameter wrapper
		Args:
			filename
			data
		'''
		vals.Strings().validate(filename)
		vals.Strings().validate(data)
		input=f'{filename}, {data}'
		self._data(input)

	def store_state(self, statenumber, filename):
		'''
		Store state parameter wrapper
		Args:
			statenumber
			filename
		'''
		vals.Ints(1,1).validate(statenumber)
		vals.Strings().validate(filename)
		input=f'{statenumber}, {filename}'
		self._store_state(input)

	def load_state(self, statenumber, filename):
		'''
		Load state parameter wrapper
		Args:
			statenumber
			filename
		'''
		vals.Ints(1,1).validate(statenumber)
		vals.Strings().validate(filename)
		input=f'{statenumber}, {filename}'
		self._load_state(input)

class Reference_Waveform(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, refnum):
		super().__init__(parent, name)

		self.add_parameter('data',
							label=f'reference {refnum} data',
							get_cmd=f'REFCurve{refnum}:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('data_header',
							label=f'reference {refnum} data header',
							get_cmd=f'REFCurve{refnum}:DATA:HEADer?',
							get_parser=str.rstrip)		

class Screenshot(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('screensave_destination',
							label='export screensave destination',
							set_cmd='EXPort:SCRSave:DESTination {}',
							get_cmd='EXPort:SCRSave:DESTination?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('name',
							label='file name',
							set_cmd='MMEMory:NAME {}',
							get_cmd='MMEMory:NAME?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('close_window',
							label='hcopy close window',
							set_cmd='HCOPy:CWINdow {}',
							get_cmd='HCOPy:CWINdow?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('data',
							label='hcopy data',
							get_cmd='HCOPy:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('format',
							label='hcopy format',
							set_cmd='HCOPy:FORMat {}',
							get_cmd='HCOPy:FORMat?',
							vals=vals.Enum('BMP', 'PNG', 'GIF'),
							get_parser=str.rstrip)

		self.add_parameter('language',
							label='hcopy language',
							set_cmd='HCOPy:LANGuage {}',
							get_cmd='HCOPy:LANGuage?',
							vals=vals.Enum('BMP', 'PNG', 'GIF'),
							get_parser=str.rstrip)

		self.add_parameter('size_x',
							label='hcopy x size',
							get_cmd='HCOPy:SIZE:X?',
							get_parser=int)

		self.add_parameter('size_y',
							label='hcopy y size',
							get_cmd='HCOPy:SIZE:Y?',
							get_parser=int)

		self.add_parameter('color_scheme',
							label='hcopy color scheme',
							set_cmd='HCOPy:COLor:SCHeme {}',
							get_cmd='HCOPy:COLor:SCHeme?',
							vals=vals.Enum('COL', 'GRAY', 'INV'),
							get_parser=str.rstrip)

	def hcopy(self): self.write('HCOPy:IMMediate')

class Waveform_Export(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('source',
							label='export waveform source',
							set_cmd='EXPort:WAVeform:SOURce {}',
							get_cmd='EXPort:WAVeform:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'D70', 'D158', 'MA1', 'RE1', 'RE2', 'RE3', 'RE4'),
							get_parser=str.rstrip)

		self.add_parameter('destination',
							label='export waveform save destination',
							set_cmd='EXPort:WFMSave:DESTination {}',
							get_cmd='EXPort:WFMSave:DESTination?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('name',
							label='export waveform name',
							set_cmd='EXPort:WAVeform:NAME {}',
							get_cmd='EXPort:WAVeform:NAME?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

	def save(self): self.write('EXPort:WAVeform:SAVE')

# General Instrument Setup

class General_Channel(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		display_settings_module=Display_Settings(self, 'display_settings')
		self.add_submodule('display_settings', display_settings_module)

		system_settings_module=System_Settings(self, 'system_settings')
		self.add_submodule('system_settings', system_settings_module)

		lan_settings_module=LAN_Settings(self, 'lan_settings')
		self.add_submodule('lan_settings', lan_settings_module)

		trigger_out_module=Trigger_Out(self, 'trigger_out')
		self.add_submodule('trigger_out', trigger_out_module)

		firmware_update_module=Firmware_Update(self, 'firmware_update')
		self.add_submodule('firmware_update', firmware_update_module)

class Display_Settings(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('language',
							label='display langauge',
							set_cmd='DISPlay:LANGuage {}',
							get_cmd='DISPlay:LANGuage?',
							vals=vals.Enum('ENGL', 'GERM', 'FREN', 'SPAN', 'RUSS', 'SCH', 'TCH', 'JAP', 'KOR', 'ITAL', 'PORT', 'CZEC', 'POL'),
							get_parser=str.rstrip)

		self.add_parameter('time_state',
							label='display time state',
							set_cmd='DISPlay:DTIMe {}',
							get_cmd='DISPlay:DTIMe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('persistence_type',
							label='display persistence type',
							set_cmd='DISPlay:PERSistence:TYPE {}',
							get_cmd='DISPlay:PERSistence:TYPE?',
							vals=vals.Enum('OFF', 'TIME', 'INF'),
							get_parser=str.rstrip)

		self.add_parameter('persistence_time',
							label='display persistence time',
							set_cmd='DISPlay:PERSistence:TIME {}',
							get_cmd='DISPlay:PERSistence:TIME?',
							vals=vals.Numbers(50e-3,12.8),
							get_parser=str.rstrip)

		self.add_parameter('persistence_state',
							label='display persistence state',
							set_cmd='DISPlay:PERSistence:STATe {}',
							get_cmd='DISPlay:PERSistence:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('persistence_infinite',
							label='display persistence infinite time',
							set_cmd='DISPlay:PERSistence:INFinite {}',
							get_cmd='DISPlay:PERSistence:INFinite?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('dialog_message',
							label='display dialog message',
							set_cmd='DISPlay:DIALog:MESSage {}',
							get_cmd='DISPlay:DIALog:MESSage?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('grid_style',
							label='display grid style',
							set_cmd='DISPlay:GRID:STYLe {}',
							get_cmd='DISPlay:GRID:STYLe?',
							vals=vals.Enum('LIN', 'RET', 'NONE'),
							get_parser=str.rstrip)

		self.add_parameter('intensity_grid',
							label='display grid intensity',
							set_cmd='DISPlay:INTensity:GRID {}',
							get_cmd='DISPlay:INTensity:GRID?',
							vals=vals.Ints(0,100),
							get_parser=int)

		self.add_parameter('intensity_waveform',
							label='display waveform intensity',
							set_cmd='DISPlay:INTensity:WAVeform {}',
							get_cmd='DISPlay:INTensity:WAVeform?',
							vals=vals.Ints(0,100),
							get_parser=int)

		self.add_parameter('palette',
							label='display palette',
							set_cmd='DISPlay:PALette {}',
							get_cmd='DISPlay:PALette?',
							vals=vals.Enum('NORM', 'INV', 'FC', 'IFC'),
							get_parser=str.rstrip)

		self.add_parameter('style',
							label='display style',
							set_cmd='DISPlay:STYLe {}',
							get_cmd='DISPlay:STYLe?',
							vals=vals.Enum('VECT', 'DOTS'),
							get_parser=str.rstrip)

		self.add_parameter('grid_annotation',
							label='display grid annotation',
							set_cmd='DISPlay:GRID:ANNotation:ENABle {}',
							get_cmd='DISPlay:GRID:ANNotation:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('annotation_track',
							label='display grid annotation track',
							set_cmd='DISPlay:GRID:ANNotation:TRACk {}',
							get_cmd='DISPlay:GRID:ANNotation:TRACk?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

	def clear(self): self.write('DISPlay:CLEar:SCReen')
	def persistence(self): self.write('DISPlay:PERSistence:CLEar')
	def close(self): self.write('DISPlay:DIALog:CLOSe')

class Firmware_Update(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('transfer_open',
							label='diagnostic update transfer open',
							set_cmd='DIAGnostic:UPDate:TRANsfer:OPEN {}',
							get_cmd='DIAGnostic:UPDate:TRANsfer:OPEN?',
							vals=vals.Enum('FIRM'),
							get_parser=str.rstrip)

		self.add_parameter('_transfer_data',
							label='diagnostic update data transfer',
							set_cmd='DIAGnostic:UPDate:TRANsfer:DATA {}')

		self.add_parameter('update_install',
							label='diagnostic update install',
							set_cmd='DIAGnostic:UPDate:INSTall {}',
							vals=vals.Strings())

	def close(self): self.write('DIAGnostic:UPDate:TRANsfer:CLOSe')

	def transfer_data(self, offset, checksum, data):
		'''
		Transfer data parameter wrapper
		Args:
			offset
			checksum
			data
		'''
		vals.Strings().validate(offset)
		vals.Strings().validate(checksum)
		vals.Strings().validate(data)
		input=f'{offset}, {checksum}, {data}'
		self._transfer_data(input)

class LAN_Settings(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('DHCP',
							label='DHCP state',
							set_cmd='SYSTem:COMMunicate:INTerface:ETHernet:DHCP {}',
							get_cmd='SYSTem:COMMunicate:INTerface:ETHernet:DHCP?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('_IP',
							label='IP Address',
							set_cmd='SYSTem:COMMunicate:INTerface:ETHernet:IPADdress {}',
							get_cmd='SYSTem:COMMunicate:INTerface:ETHernet:IPADdress?',
							get_parser=str.rstrip)

		self.add_parameter('_subnet',
							label='subnet',
							set_cmd='SYSTem:COMMunicate:INTerface:ETHernet:SUBNet {}',
							get_cmd='SYSTem:COMMunicate:INTerface:ETHernet:SUBNet?',
							get_parser=str.rstrip)

		self.add_parameter('_gateway',
							label='gateway',
							set_cmd='SYSTem:COMMunicate:INTerface:ETHernet:GATeway {}',
							get_cmd='SYSTem:COMMunicate:INTerface:ETHernet:GATeway?',
							get_parser=str.rstrip)

		self.add_parameter('IP_Port',
							label='IP port',
							set_cmd='SYSTem:COMMunicate:INTerface:ETHernet:IPPort {}',
							get_cmd='SYSTem:COMMunicate:INTerface:ETHernet:IPPort?',
							vals=vals.Ints(1024,65535),
							get_parser=int)

		self.add_parameter('VXI_Port',
							label='VXI port',
							set_cmd='SYSTem:COMMunicate:INTerface:ETHernet:VXIPort {}',
							get_cmd='SYSTem:COMMunicate:INTerface:ETHernet:VXIPort?',
							vals=vals.Ints(0,65535),
							get_parser=int)

		self.add_parameter('HTTP_Port',
							label='HTTP port',
							set_cmd='SYSTem:COMMunicate:INTerface:ETHernet:HTTPport {}',
							get_cmd='SYSTem:COMMunicate:INTerface:ETHernet:HTTPport?',
							vals=vals.Ints(0,65535),
							get_parser=int)

		self.add_parameter('transfer_mode',
							label='transfer mode',
							set_cmd='SYSTem:COMMunicate:INTerface:ETHernet:TRANsfer {}',
							get_cmd='SYSTem:COMMunicate:INTerface:ETHernet:TRANsfer?',
							vals=vals.Enum('AUTO', 'FD10', 'FD100', 'HD10', 'HD100'),
							get_parser=str.rstrip)

		self.add_parameter('mac_address',
							label='mac address',
							get_cmd='SYSTem:COMMunicate:INTerface:ETHernet:MACaddress?',
							get_parser=str.rstrip)

		self.add_parameter('USB_class',
							label='USB class',
							set_cmd='SYSTem:COMMunicate:INTerface:USB:CLASs {}',
							get_cmd='SYSTem:COMMunicate:INTerface:USB:CLASs?',
							vals=vals.Enum('TMC', 'VCP', 'MTP'),
							get_parser=str.rstrip)

	def IP(self, byte1, byte2, byte3, byte4):
		'''
		IP parameter wrapper
		Args:
			byte1
			byte2
			byte3
			byte4
		'''
		vals.Ints(0,255).validate(byte1)
		vals.Ints(0,255).validate(byte2)
		vals.Ints(0,255).validate(byte3)
		vals.Ints(0,255).validate(byte4)
		input=f'{byte1}, {byte2}, {byte3}, {byte4}'
		self._IP(input)

	def subnet(self, byte1, byte2, byte3, byte4):
		'''
		Subnet parameter wrapper
		Args:
			byte1
			byte2
			byte3
			byte4
		'''
		vals.Ints(0,255).validate(byte1)
		vals.Ints(0,255).validate(byte2)
		vals.Ints(0,255).validate(byte3)
		vals.Ints(0,255).validate(byte4)
		input=f'{byte1}, {byte2}, {byte3}, {byte4}'
		self._subnet(input)

	def gateway(self, byte1, byte2, byte3, byte4):
		'''
		Gateway parameter wrapper
		Args:
			byte1
			byte2
			byte3
			byte4
		'''
		vals.Ints(0,255).validate(byte1)
		vals.Ints(0,255).validate(byte2)
		vals.Ints(0,255).validate(byte3)
		vals.Ints(0,255).validate(byte4)
		input=f'{byte1}, {byte2}, {byte3}, {byte4}'
		self._gateway(input)

class System_Settings(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('calibration',
							label='system calibration',
							set_cmd='CALibration',
							get_cmd='CALibration?',
							get_parser=float)

		self.add_parameter('calibration_state',
							label='system calibration state',
							get_cmd='CALibration:STATe?',
							get_parser=str.rstrip)

		self.add_parameter('name',
							label='system name',
							set_cmd='SYSTem:NAME {}',
							get_cmd='SYSTem:NAME?',
							vals=vals.Strings(0,20),
							get_parser=str.rstrip)

		self.add_parameter('_date',
							label='system date',
							set_cmd='SYSTem:DATE {}',
							get_cmd='SYSTem:DATE?',
							get_parser=str.rstrip)

		self.add_parameter('_time',
							label='system time',
							set_cmd='SYSTem:TIME {}',
							get_cmd='SYSTem:TIME?',
							get_parser=str.rstrip)

		self.add_parameter('communicate_interface',
							label='system interface for communication',
							set_cmd='SYSTem:COMMunicate:INTerface:SELect {}',
							get_cmd='SYSTem:COMMunicate:INTerface:SELect?',
							vals=vals.Enum('USB', 'ETH'),
							get_parser=str.rstrip)

		self.add_parameter('beeper_control',
							label='beeper control state',
							set_cmd='SYSTem:BEEPer:CONTrol:STATe {}',
							get_cmd='SYSTem:BEEPer:CONTrol:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('beeper_error',
							label='beeper error state',
							set_cmd='SYSTem:BEEPer:ERRor:STATe {}',
							get_cmd='SYSTem:BEEPer:ERRor:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('beeper_trigger',
							label='beeper trigger state',
							set_cmd='SYSTem:BEEPer:TRIG:STATe {}',
							get_cmd='SYSTem:BEEPer:TRIG:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('setup',
							label='system setup',
							set_cmd='SYSTem:SET {}',
							get_cmd='SYSTem:SET?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('error',
							label='system error next',
							get_cmd='SYSTem:ERRor:NEXT?',
							get_parser=str.rstrip)

		self.add_parameter('error_all',
							label='system error all',
							get_cmd='SYSTem:ERRor:ALL?',
							get_parser=str.rstrip)

		self.add_parameter('footprint',
							label='system device footprint',
							get_cmd='SYSTem:DFPRint?',
							get_parser=str.rstrip)

		self.add_parameter('tree',
							label='syste, list of implemented commands',
							get_cmd='SYSTem:TREE?',
							get_parser=str.rstrip)

	def beeper(self): self.write('SYSTem:BEEPer:IMMediate')
	def preset(self): self.write('SYSTem:PRESet')
	def education(self): self.write('SYSTem:EDUCation:PRESet')

	def date(self, year, month, day):
		'''
		Date parameter wrapper
		Args:
			year
			month
			day
		'''
		vals.Ints().validate(year)
		vals.Ints(1,12).validate(month)
		vals.Ints(1,31).validate(day)
		input=f'{year}, {month}, {day}'
		self._date(input)

	def time(self, hour, minute, second):
		'''
		Time parameter wrapper
		Args:
			hour
			minute
			second
		'''
		vals.Ints(0,23).validate(hour)
		vals.Ints(0,59).validate(minute)
		vals.Ints(0,59).validate(second)
		input=f'{hour}, {minute}, {second}'
		self._time(input)

class Trigger_Out(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('output_mode',
							label='trigger out output mode',
							set_cmd='TRIGger:OUT:MODE {}',
							get_cmd='TRIGger:OUT:MODE?',
							vals=vals.Enum('OFF', 'TRIG', 'REF', 'MASK'),
							get_parser=str.rstrip)

		self.add_parameter('pulse_length',
							label='trigger out output pulse length',
							set_cmd='TRIGger:OUT:PLENgth {}',
							get_cmd='TRIGger:OUT:PLENgth?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('polarity',
							label='trigger out polarity',
							set_cmd='TRIGger:OUT:POLarity {}',
							get_cmd='TRIGger:OUT:POLarity?',
							vals=vals.Enum('POS', 'NEG'),
							get_parser=str.rstrip)

# Serial Bus Analysis

class Serial_Bus_Channel(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		spi_trigger_module=SPI_Trigger(self, 'spi_trigger')
		self.add_submodule('spi_trigger', spi_trigger_module)

		inter_integrated_trigger_module=Inter_Integrated_Trigger(self, 'inter_integrated_trigger')
		self.add_submodule('inter_integrated_trigger', inter_integrated_trigger_module)

		uart_trigger_module=UART_Trigger(self, 'uart_trigger')
		self.add_submodule('uart_trigger', uart_trigger_module)

		can_trigger_module=CAN_Trigger(self, 'can_trigger')
		self.add_submodule('can_trigger', can_trigger_module)

		can_search_module=CAN_Search(self, 'can_search')
		self.add_submodule('can_search', can_search_module)

		lin_trigger_module=LIN_Trigger(self, 'lin_trigger')
		self.add_submodule('lin_trigger', lin_trigger_module)

		lin_search_module=LIN_Search(self, 'lin_search')
		self.add_submodule('lin_search', lin_search_module)

		mil_trigger_module=MIL_Trigger(self, 'mil_trigger')
		self.add_submodule('mil_trigger', mil_trigger_module)

		mil_search_module=MIL_Search(self, 'mil_search')
		self.add_submodule('mil_search', mil_search_module)

		arinc_trigger_module=ARINC_Trigger(self, 'arinc_trigger')
		self.add_submodule('arinc_trigger', arinc_trigger_module)

		arinc_search_module=ARINC_Search(self, 'arinc_search')
		self.add_submodule('arinc_search', arinc_search_module)

		for i in range(1,4+1):
			bus_general_module=Bus_General(self, f'gen_bs{i}', i)
			self.add_submodule(f'gen_bs{i}', bus_general_module)

			spi_module=SPI(self, f'spi_bs{i}', i)
			self.add_submodule(f'spi_bs{i}', spi_module)

			sspi_module=SSPI(self, f'sspi_bs{i}', i)
			self.add_submodule(f'sspi_bs{i}', sspi_module)

			inter_integrated_config_module=Inter_Integrated_Config(self, f'iic_bs{i}', i)
			self.add_submodule(f'iic_bs{i}', inter_integrated_config_module)

			uart_module=UART(self, f'uart_bs{i}', i)
			self.add_submodule(f'uart_bs{i}', uart_module)

			can_module=CAN(self, f'can_bs{i}', i)
			self.add_submodule(f'can_bs{i}', can_module)

			lin_config_module=LIN_Config(self, f'lin_bs{i}', i)
			self.add_submodule(f'lin_bs{i}', lin_config_module)

			audio_config_module=Audio_Config(self, f'audio_bs{i}', i)
			self.add_submodule(f'audio_bs{i}', audio_config_module)

			mil_config_module=MIL_Config(self, f'mil_bs{i}', i)
			self.add_submodule(f'mil_bs{i}', mil_config_module)

			arinc_config_module=ARINC_Config(self, f'arinc_bs{i}', i)
			self.add_submodule(f'arinc_bs{i}', arinc_config_module)

		for i in range(1,50+1):
			audio_trigger_module=Audio_Trigger(self, f'audio_fr{i}', i)
			self.add_submodule(f'audio_fr{i}', audio_trigger_module)

		for i in range(1,2+1):
			general_bus_module=General_Bus(self, f'gen_by{i}', i)
			self.add_submodule(f'gen_by{i}', general_bus_module)

		for i in range(1,4+1):
			for j in range(1,50+1):
				for k in range(1,50+1):
					spi_decode_module=SPI_Decode(self, f'spidec_bs{i}_spidec_fr{j}_spidec_wr{k}', i, j, k)
					self.add_submodule(f'spidec_bs{i}_spidec_fr{j}_spidec_wr{k}', spi_decode_module)

					uart_decode_module=UART_Decode(self, f'uartdec_bs{i}_uartdec_fr{j}_uartdec_wr{k}', i, j ,k)
					self.add_submodule(f'uartdec_bs{i}_uartdec_fr{j}_uart_decwr{k}', uart_decode_module)

		for i in range(1,4+1):
			for j in range(1,50+1):
				for k in range(1,50+1):
					inter_integrated_decode_module=Inter_Integrated_Decode(self, f'iicdec_bs{i}_iicdec_fr{j}_iicdec_bt{k}', i, j, k)
					self.add_submodule(f'iicdec_bs{i}_iicdec_fr{j}_iicdec_bt{k}', inter_integrated_decode_module)

					can_decode_module=CAN_Decode(self, f'candec_bs{i}_candec_fr{j}_candec_bt{k}', i, j, k)
					self.add_submodule(f'candec_bs{i}_candec_fr{j}_candec_bt{k}', can_decode_module)

					lin_decode_module=LIN_Decode(self, f'lindec_bs{i}_lindec_fr{j}_lindec_bt{k}', i, j, k)
					self.add_submodule(f'lindec_bs{i}_lindec_fr{j}_lindecbt{k}', lin_decode_module)

		for i in range(1,4+1):
			for j in range(1,50+1):
				for k in range(1,8+1):
					audio_decode_tdm_module=Audio_Decode_TDM(self, f'tdmdec_bs{i}_tdmdec_fr{j}_tdmdec_td{k}', i, j, k)
					self.add_submodule(f'tdmdec_bs{i}_tdmdec_fr{j}_tdmdec_td{k}', audio_decode_tdm_module)

		for i in range(1,4+1):
			for j in range(1,50+1):
				audio_decode_module=Audio_Decode(self, f'audec_bs{i}_audec_fr{j}', i, j)
				self.add_submodule(f'audec_bs{i}_audec_fr{j}', audio_decode_module)

				mil_decode_module=MIL_Decode(self, f'mildec_bs{i}_mildec_fr{j}', i, j)
				self.add_submodule(f'mildec_bs{i}_mildec_fr{j}', mil_decode_module)

				arinc_decode_module=ARINC_Decode(self, f'aridec_bs{i}_aridec_fr{j}', i, j)
				self.add_submodule(f'aridec_bs{i}_aridec_fr{j}', arinc_decode_module)

class ARINC_Config(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, busnum):
		super().__init__(parent, name)

		self.add_parameter('bitrate_mode',
							label=f'bus {busnum} bit rate mode',
							set_cmd=f'BUS{busnum}:ARINc:BRMode {{}}',
							get_cmd=f'BUS{busnum}:ARINc:BRMode?',
							vals=vals.Enum('HIGH', 'LOW', 'USER'),
							get_parser=str.rstrip)

		self.add_parameter('bitrate_value',
							label=f'bus {busnum} bitrate value',
							set_cmd=f'BUS{busnum}:ARINc:BRValue {{}}',
							get_cmd=f'BUS{busnum}:ARINc:BRValue?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('polarity',
							label=f'bus {busnum} polarity',
							set_cmd=f'BUS{busnum}:ARINc:POLarity {{}}',
							get_cmd=f'BUS{busnum}:ARINc:POLarity?',
							vals=vals.Enum('ALEG', 'BLEG', 'NORM', 'INV'),
							get_parser=str.rstrip)

		self.add_parameter('source',
							label=f'bus {busnum} source',
							set_cmd=f'BUS{busnum}:ARINc:SOURce {{}}',
							get_cmd=f'BUS{busnum}:ARINc:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4'),
							get_parser=str.rstrip)

		self.add_parameter('threshold_high',
							label=f'bus {busnum} high threshold',
							set_cmd=f'BUS{busnum}:ARINc:THReshold:HIGH {{}}',
							get_cmd=f'BUS{busnum}:ARINc:THReshold:HIGH?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('threshold_low',
							label=f'bus {busnum} low threshold',
							set_cmd=f'BUS{busnum}:ARINc:THReshold:LOW {{}}',
							get_cmd=f'BUS{busnum}:ARINc:THReshold:LOW?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

class ARINC_Decode(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, busnum, framenum):
		super().__init__(parent, name)

		self.add_parameter('count',
							label=f'bus {busnum} count',
							get_cmd=f'BUS{busnum}:ARINc:WCOunt?',
							get_parser=int)

		self.add_parameter('standard_decode',
							label=f'bus {busnum} standard decode format',
							set_cmd=f'BUS{busnum}:ARINc:DATA:FORMat {{}}',
							get_cmd=f'BUS{busnum}:ARINc:DATA:FORMat?',
							vals=vals.Enum('DATA', 'DSSM', 'DSDI', 'DSSS'),
							get_parser=str.rstrip)

		self.add_parameter('value_specified',
							label=f'bus {busnum} frame {framenum} specified word value',
							get_cmd=f'BUS{busnum}:ARINc:WORD{framenum}:DATA:VALue?',
							get_parser=float)

		self.add_parameter('format_specified',
							label=f'bus {busnum} frame {framenum} specified word format',
							get_cmd=f'BUS{busnum}:ARINc:WORD{framenum}:FORMat?',
							get_parser=str.rstrip)

		self.add_parameter('label_specified',
							label=f'bus {busnum} frame {framenum} specified label',
							get_cmd=f'BUS{busnum}:ARINc:WORD{framenum}:LABel:VALue?',
							get_parser=float)

		self.add_parameter('word_parity',
							label=f'bus {busnum} frame {framenum} word parity',
							get_cmd=f'BUS{busnum}:ARINc:WORD{framenum}:PARity?',
							get_parser=str.rstrip)

		self.add_parameter('word_pattern',
							label=f'bus {busnum} frame {framenum} word pattern',
							get_cmd=f'BUS{busnum}:ARINc:WORD{framenum}:PATTern?',
							get_parser=float)

		self.add_parameter('word_SDI',
							label=f'bus {busnum} frame {framenum} word SDI',
							get_cmd=f'BUS{busnum}:ARINc:WORD{framenum}:SDI?',
							get_parser=str.rstrip)

		self.add_parameter('word_SSM',
							label=f'bus {busnum} frame {framenum} word SSM',
							get_cmd=f'BUS{busnum}:ARINc:WORD{framenum}:SSM?',
							get_parser=str.rstrip)

		self.add_parameter('word_start',
							label=f'bus {busnum} frame {framenum} word start',
							get_cmd=f'BUS{busnum}:ARINc:WORD{framenum}:STARt?',
							get_parser=str.rstrip)

		self.add_parameter('word_status',
							label=f'bus {busnum} frame {framenum} word status',
							get_cmd=f'BUS{busnum}:ARINc:WORD{framenum}:STATus?',
							get_parser=str.rstrip)

		self.add_parameter('word_stop',
							label=f'bus {busnum} frame {framenum} word stop',
							get_cmd=f'BUS{busnum}:ARINc:WORD{framenum}:STOP?',
							get_parser=str.rstrip)

class ARINC_Search(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('condition',
							label='search condition',
							set_cmd='SEARch:PROTocol:ARINc:CONDition {}',
							get_cmd='SEARch:PROTocol:ARINc:CONDition?',
							vals=vals.Enum('WORD', 'ERR', 'LAB', 'LDAT'),
							get_parser=str.rstrip)		

		self.add_parameter('data_condition',
							label='data condition',
							set_cmd='SEARch:PROTocol:ARINc:DATA:CONDition {}',
							get_cmd='SEARch:PROTocol:ARINc:DATA:CONDition?',
							vals=vals.Enum('EQU', 'NEQ', 'GTH', 'GEQ', 'LEQ', 'LTH', 'WITH', 'OUTS'),
							get_parser=str.rstrip)

		self.add_parameter('data_maximum',
							label='data maximum',
							set_cmd='SEARch:PROTocol:ARINc:DATA:MAXimum {}',
							get_cmd='SEARch:PROTocol:ARINc:DATA:MAXimum?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('data_minimum',
							label='data minimum',
							set_cmd='SEARch:PROTocol:ARINc:DATA:MINimum {}',
							get_cmd='SEARch:PROTocol:ARINc:DATA:MINimum?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('data_offset',
							label='data offset',
							set_cmd='SEARch:PROTocol:ARINc:DATA:OFFSet {}',
							get_cmd='SEARch:PROTocol:ARINc:DATA:OFFSet?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('data_size',
							label='data size',
							set_cmd='SEARch:PROTocol:ARINc:DATA:SIZE {}',
							get_cmd='SEARch:PROTocol:ARINc:DATA:SIZE?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('error',
							label='error',
							set_cmd='SEARch:PROTocol:ARINc:ERRor {}',
							get_cmd='SEARch:PROTocol:ARINc:ERRor?',
							vals=vals.Enum('ANY', 'PAR', 'GAP', 'COD'),
							get_parser=str.rstrip)

		self.add_parameter('format',
							label='format',
							set_cmd='SEARch:PROTocol:ARINc:FORMat {}',
							get_cmd='SEARch:PROTocol:ARINc:FORMat?',
							vals=vals.Enum('DATA', 'DSSM', 'DSDI', 'DSSS'),
							get_parser=str.rstrip)

		self.add_parameter('label_condition',
							label='label condition',
							set_cmd='SEARch:PROTocol:ARINc:LABel:CONDition {}',
							get_cmd='SEARch:PROTocol:ARINc:LABel:CONDition?',
							vals=vals.Enum('EQU', 'NEQ', 'GTH', 'GEQ', 'LEQ', 'LTH', 'WITH', 'OUTS'),
							get_parser=str.rstrip)

		self.add_parameter('label_maximum',
							label='label maximum',
							set_cmd='SEARch:PROTocol:ARINc:LABel:MAXimum {}',
							get_cmd='SEARch:PROTocol:ARINc:LABel:MAXimum?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('label_minimum',
							label='label minimum',
							set_cmd='SEARch:PROTocol:ARINc:LABel:MINimum {}',
							get_cmd='SEARch:PROTocol:ARINc:LABel:MINimum?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('SDI',
							label='SDI',
							set_cmd='SEARch:PROTocol:ARINc:SDI {}',
							get_cmd='SEARch:PROTocol:ARINc:SDI?',
							vals=vals.Enum('ANY', 'S00', 'S01', 'S10', 'S11'),
							get_parser=str.rstrip)

		self.add_parameter('SSM',
							label='SSM',
							set_cmd='SEARch:PROTocol:ARINc:SSM {}',
							get_cmd='SEARch:PROTocol:ARINc:SSM?',
							vals=vals.Enum('ANY', 'S00', 'S01', 'S10', 'S11'),
							get_parser=str.rstrip)

		self.add_parameter('word_type',
							label='word type',
							set_cmd='SEARch:PROTocol:ARINc:WORD:TYPE {}',
							get_cmd='SEARch:PROTocol:ARINc:WORD:TYPE?',
							vals=vals.Enum('STAR', 'STOP'),
							get_parser=str.rstrip)

class ARINC_Trigger(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('comparison_condition',
							label='condition comparison',
							set_cmd='TRIGger:A:ARINc:DATA:CONDition {}',
							get_cmd='TRIGger:A:ARINc:DATA:CONDition?',
							vals=vals.Enum('EQU', 'NEQ', 'GTH', 'GEQ', 'LEQ', 'LTH', 'WITH', 'OUTS'),
							get_parser=str.rstrip)

		self.add_parameter('data_max',
							label='data maximum',
							set_cmd='TRIGger:A:ARINc:DATA:MAXimum {}',
							get_cmd='TRIGger:A:ARINc:DATA:MAXimum?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('data_min',
							label='data minimum',
							set_cmd='TRIGger:A:ARINc:DATA:MINimum {}',
							get_cmd='TRIGger:A:ARINc:DATA:MINimum?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('data_offset',
							label='data offset',
							set_cmd='TRIGger:A:ARINc:DATA:OFFSet {}',
							get_cmd='TRIGger:A:ARINc:DATA:OFFSet?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('data_size',
							label='data size',
							set_cmd='TRIGger:A:ARINc:DATA:SIZE {}',
							get_cmd='TRIGger:A:ARINc:DATA:SIZE?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('error_coding',
							label='coding error',
							set_cmd='TRIGger:A:ARINc:ERRor:CODing {}',
							get_cmd='TRIGger:A:ARINc:ERRor:CODing?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('error_gap',
							label='gap error',
							set_cmd='TRIGger:A:ARINc:ERRor:GAP {}',
							get_cmd='TRIGger:A:ARINc:ERRor:GAP?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('error_parity',
							label='parity error',
							set_cmd='TRIGger:A:ARINc:ERRor:PARity {}',
							get_cmd='TRIGger:A:ARINc:ERRor:PARity?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('data_format',
							label='data format',
							set_cmd='TRIGger:A:ARINc:FORMat {}',
							get_cmd='TRIGger:A:ARINc:FORMat?',
							vals=vals.Enum('DATA', 'DSSM', 'DSDI', 'DSSS'),
							get_parser=str.rstrip)

		self.add_parameter('label_condition',
							label='label condition',
							set_cmd='TRIGger:A:ARINc:LABel:CONDition {}',
							get_cmd='TRIGger:A:ARINc:LABel:CONDition?',
							vals=vals.Enum('EQU', 'NEQ', 'GTH', 'GEQ', 'LEQ', 'LTH', 'WITH', 'OUTS'),
							get_parser=str.rstrip)

		self.add_parameter('label_maximum',
							label='label maximum',
							set_cmd='TRIGger:A:ARINc:LABel:MAXimum {}',
							get_cmd='TRIGger:A:ARINc:LABel:MAXimum?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('label_minimum',
							label='label minimum',
							set_cmd='TRIGger:A:ARINc:LABel:MINimum {}',
							get_cmd='TRIGger:A:ARINc:LABel:MINimum?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('SDI_value',
							label='SDI value',
							set_cmd='TRIGger:A:ARINc:SDI {}',
							get_cmd='TRIGger:A:ARINc:SDI?',
							vals=vals.Enum('ANY', 'S00', 'S01', 'S10', 'S11'),
							get_parser=str.rstrip)

		self.add_parameter('SSM_value',
							label='SSM value',
							set_cmd='TRIGger:A:ARINc:SSM {}',
							get_cmd='TRIGger:A:ARINc:SSM?',
							vals=vals.Enum('ANY', 'S00', 'S01', 'S10', 'S11'),
							get_parser=str.rstrip)

		self.add_parameter('transmission_time',
							label='transmission time',
							set_cmd='TRIGger:A:ARINc:TTIMe:CONDition {}',
							get_cmd='TRIGger:A:ARINc:TTIMe:CONDition?',
							vals=vals.Enum('GTH', 'LTH', 'WITH', 'OUTS'),
							get_parser=str.rstrip)

		self.add_parameter('transmission_max',
							label='tramsmission time max',
							set_cmd='TRIGger:A:ARINc:TTIMe:MAXimum {}',
							get_cmd='TRIGger:A:ARINc:TTIMe:MAXimum?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('transmission_min',
							label='transmission time min',
							set_cmd='TRIGger:A:ARINc:TTIMe:MINimum {}',
							get_cmd='TRIGger:A:ARINc:TTIMe:MINimum?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('trigger_type',
							label='trigger type',
							set_cmd='TRIGger:A:ARINc:TYPE {}',
							get_cmd='TRIGger:A:ARINc:TYPE?',
							vals=vals.Enum('WORD', 'ERR', 'LAB', 'LDAT', 'TTIM'),
							get_parser=str.rstrip)

		self.add_parameter('word_type',
							label='word type',
							set_cmd='TRIGger:A:ARINc:WORD:TYPE {}',
							get_cmd='TRIGger:A:ARINc:WORD:TYPE?',
							vals=vals.Enum('STAR', 'STOP'),
							get_parser=str.rstrip)

class Audio_Config(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, busnum):
		super().__init__(parent, name)

		self.add_parameter('count',
							label=f'bus {busnum} count',
							get_cmd=f'BUS{busnum}:I2S:FCOunt?',
							get_parser=int)
		
		self.add_parameter('variant',
							label=f'bus {busnum} variant',
							set_cmd=f'BUS{busnum}:I2S:AVARiant {{}}',
							get_cmd=f'BUS{busnum}:I2S:AVARiant?',
							vals=vals.Enum('I2S', 'LJ', 'RJ', 'TDM', 'DSP'),
							get_parser=str.rstrip)

		self.add_parameter('bit_order',
							label=f'bus {busnum} bit order',
							set_cmd=f'BUS{busnum}:I2S:BORDer {{}}',
							get_cmd=f'BUS{busnum}:I2S:BORDer?',
							vals=vals.Enum('MSBF', 'LSBF'),
							get_parser=str.rstrip)

		self.add_parameter('channel_length',
							label=f'bus {busnum} channel length',
							set_cmd=f'BUS{busnum}:I2S:CHANnel:LENGth {{}}',
							get_cmd=f'BUS{busnum}:I2S:CHANnel:LENGth?',
							vals=vals.Ints(),
							get_parser=int)

		self.add_parameter('channel_offset',
							label=f'bus {busnum} channel offset',
							set_cmd=f'BUS{busnum}:I2S:CHANnel:OFFSet {{}}',
							get_cmd=f'BUS{busnum}:I2S:CHANnel:OFFSet?',
							vals=vals.Ints(),
							get_parser=int)

		self.add_parameter('channel_order',
							label=f'bus {busnum} channel order',
							set_cmd=f'BUS{busnum}:I2S:CHANnel:ORDer {{}}',
							get_cmd=f'BUS{busnum}:I2S:CHANnel:ORDer?',
							vals=vals.Enum('LFIR', 'RFIR'),
							get_parser=str.rstrip)

		self.add_parameter('channel_count',
							label=f'bus {busnum} channel count',
							set_cmd=f'BUS{busnum}:I2S:CHANnel:TDMCount {{}}',
							get_cmd=f'BUS{busnum}:I2S:CHANnel:TDMCount?',
							vals=vals.Ints(),
							get_parser=int)

		self.add_parameter('clock_slope',
							label=f'bus {busnum} clock slope',
							set_cmd=f'BUS{busnum}:I2S:CLOCk:POLarity {{}}',
							get_cmd=f'BUS{busnum}:I2S:CLOCk:POLarity?',
							vals=vals.Enum('RIS', 'FALL'),
							get_parser=str.rstrip)

		self.add_parameter('clock_source',
							label=f'bus {busnum} clock source',
							set_cmd=f'BUS{busnum}:I2S:CLOCk:SOURce {{}}',
							get_cmd=f'BUS{busnum}:I2S:CLOCk:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15'),
							get_parser=str.rstrip)

		self.add_parameter('clock_threshold',
							label=f'bus {busnum} clock threshold',
							set_cmd=f'BUS{busnum}:I2S:CLOCk:THReshold {{}}',
							get_cmd=f'BUS{busnum}:I2S:CLOCk:THReshold?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('data_polarity',
							label=f'bus {busnum} data polarity',
							set_cmd=f'BUS{busnum}:I2S:DATA:POLarity {{}}',
							get_cmd=f'BUS{busnum}:I2S:DATA:POLarity?',
							vals=vals.Enum('ACTH', 'ACTL'),
							get_parser=str.rstrip)

		self.add_parameter('data_source',
							label=f'bus {busnum} data source',
							set_cmd=f'BUS{busnum}:I2S:DATA:SOURce {{}}',
							get_cmd=f'BUS{busnum}:I2S:DATA:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15'),
							get_parser=str.rstrip)

		self.add_parameter('threshold',
							label=f'bus {busnum} threshold',
							set_cmd=f'BUS{busnum}:I2S:DATA:THReshold {{}}',
							get_cmd=f'BUS{busnum}:I2S:DATA:THReshold?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('display_mode',
							label=f'bus {busnum} display mode',
							set_cmd=f'BUS{busnum}:I2S:DISPlay {{}}',
							get_cmd=f'BUS{busnum}:I2S:DISPlay?',
							vals=vals.Enum('SEQ', 'PAR', 'STR', 'PTR', 'TRAC', 'SDS'),
							get_parser=str.rstrip)

		self.add_parameter('frame_offset',
							label=f'bus {busnum} frame offset',
							set_cmd=f'BUS{busnum}:I2S:FOFFset {{}}',
							get_cmd=f'BUS{busnum}:I2S:FOFFset?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('word_length',
							label=f'bus {busnum} word length',
							set_cmd=f'BUS{busnum}:I2S:WLENgth {{}}',
							get_cmd=f'BUS{busnum}:I2S:WLENgth?',
							vals=vals.Ints(),
							get_parser=int)

		self.add_parameter('select_polarity',
							label=f'bus {busnum} word select polarity',
							set_cmd=f'BUS{busnum}:I2S:WSELect:POLarity {{}}',
							get_cmd=f'BUS{busnum}:I2S:WSELect:POLarity?',
							vals=vals.Enum('NORM', 'INV'),
							get_parser=str.rstrip)

		self.add_parameter('select_source',
							label=f'bus {busnum} word select source',
							set_cmd=f'BUS{busnum}:I2S:WSELect:SOURce {{}}',
							get_cmd=f'BUS{busnum}:I2S:WSELect:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15'),
							get_parser=str.rstrip)

		self.add_parameter('select_threshold',
							label=f'bus {busnum} word select threshold',
							set_cmd=f'BUS{busnum}:I2S:WSELect:THReshold {{}}',
							get_cmd=f'BUS{busnum}:I2S:WSELect:THReshold?',
							vals=vals.Numbers(),
							get_parser=float)

class Audio_Decode(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, busnum, framenum):
		super().__init__(parent, name)

		self.add_parameter('left_state',
							label=f'bus {busnum} frame {framenum} state',
							get_cmd=f'BUS{busnum}:I2S:FRAMe{framenum}:LEFT:STATe?',
							get_parser=str.rstrip)

		self.add_parameter('left_value',
							label=f'bus {busnum} frame {framenum} value',
							get_cmd=f'BUS{busnum}:I2S:FRAMe{framenum}:LEFT:VALue?',
							get_parser=float)

		self.add_parameter('right_state',
							label=f'bus {busnum} frame {framenum} state',
							get_cmd=f'BUS{busnum}:I2S:FRAMe{framenum}:RIGHt:STATe?',
							get_parser=str.rstrip)

		self.add_parameter('right_value',
							label=f'bus {busnum} frame {framenum} value',
							get_cmd=f'BUS{busnum}:I2S:FRAMe{framenum}:RIGHt:VALue?',
							get_parser=float)

		self.add_parameter('start',
							label=f'bus {busnum} frame {framenum} start',
							get_cmd=f'BUS{busnum}:I2S:FRAMe{framenum}:STARt?',
							get_parser=float)

		self.add_parameter('state',
							label=f'bus {busnum} frame {framenum} state',
							get_cmd=f'BUS{busnum}:I2S:FRAMe{framenum}:STATe?',
							get_parser=str.rstrip)

		self.add_parameter('stop',
							label=f'bus {busnum} frame {framenum} stop',
							get_cmd=f'BUS{busnum}:I2S:FRAMe{framenum}:STOP?',
							get_parser=float)

class Audio_Decode_TDM(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, busnum, framenum, tdmnum):
		super().__init__(parent, name)
		
		self.add_parameter('TDM_state',
							label=f'bus {busnum} frame {framenum} tdm {tdmnum}',
							get_cmd=f'BUS{busnum}:I2S:FRAMe{framenum}:TDM{tdmnum}:STATe?',
							get_parser=str.rstrip)

		self.add_parameter('TDM_value',
							label=f'bus {busnum} frame {framenum} tdm {tdmnum}',
							get_cmd=f'BUS{busnum}:I2S:FRAMe{framenum}:TDM{tdmnum}:VALue?',
							get_parser=float)

class Audio_Trigger(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, framenum):
		super().__init__(parent, name)

		self.add_parameter('left_condition',
							label='condition',
							set_cmd='TRIGger:A:I2S:CHANnel:LEFT:CONDition {}',
							get_cmd='TRIGger:A:I2S:CHANnel:LEFT:CONDition?',
							vals=vals.Enum('OFF', 'EQU', 'NEQ', 'GTH', 'LTH', 'INR', 'OOR'),
							get_parser=str.rstrip)
						
		self.add_parameter('left_max',
							label='maximum value',
							set_cmd='TRIGger:A:I2S:CHANnel:LEFT:DMAX {}',
							get_cmd='TRIGger:A:I2S:CHANnel:LEFT:DMAX?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('left_min',
							label='minimum value',
							set_cmd='RIGger:A:I2S:CHANnel:LEFT:DMIN {}',
							get_cmd='RIGger:A:I2S:CHANnel:LEFT:DMIN?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('right_condition',
							label='condition',
							set_cmd='TRIGger:A:I2S:CHANnel:RIGHt:CONDition {}',
							get_cmd='TRIGger:A:I2S:CHANnel:RIGHt:CONDition?',
							vals=vals.Enum('OFF', 'EQU', 'NEQ', 'GTH', 'LTH', 'INR', 'OOR'),
							get_parser=str.rstrip)

		self.add_parameter('right_max',
							label='maximum value',
							set_cmd='TRIGger:A:I2S:CHANnel:RIGHt:DMAX {}',
							get_cmd='TRIGger:A:I2S:CHANnel:RIGHt:DMAX?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('right_min',
							label='minimum value',
							set_cmd='TRIGger:A:I2S:CHANnel:RIGHt:DMIN {}',
							get_cmd='TRIGger:A:I2S:CHANnel:RIGHt:DMIN?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('condition',
							label='condition',
							set_cmd='TRIGger:A:I2S:CHANnel:RIGHt:CONDition {}',
							get_cmd='TRIGger:A:I2S:CHANnel:RIGHt:CONDition?',
							vals=vals.Enum('OFF', 'EQU', 'NEQ', 'GTH', 'LTH', 'INR', 'OOR'),
							get_parser=str.rstrip)

		self.add_parameter('max',
							label=f'frame {framenum} maximum value',
							set_cmd=f'TRIGger:A:I2S:CHANnel:TDM{framenum}:DMAX {{}}',
							get_cmd=f'TRIGger:A:I2S:CHANnel:TDM{framenum}:DMAX?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('min',
							label=f'frame {framenum} minimum value',
							set_cmd=f'TRIGger:A:I2S:CHANnel:TDM{framenum}:DMIN {{}}',
							get_cmd=f'TRIGger:A:I2S:CHANnel:TDM{framenum}:DMIN?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('function',
							label='function',
							set_cmd='TRIGger:A:I2S:FUNCtion {}',
							get_cmd='TRIGger:A:I2S:FUNCtion?',
							vals=vals.Enum('AND', 'OR'),
							get_parser=str.rstrip)

		self.add_parameter('type',
							label='trigger mode',
							set_cmd='TRIGger:A:I2S:TYPE {}',
							get_cmd='TRIGger:A:I2S:TYPE?',
							vals=vals.Enum('DATA', 'WIND', 'WSEL', 'ERRC'),
							get_parser=str.rstrip)

		self.add_parameter('words_length',
							label='window length',
							set_cmd='TRIGger:A:I2S:SOWords {}',
							get_cmd='TRIGger:A:I2S:SOWords?',
							vals=vals.Ints(),
							get_parser=int)

		self.add_parameter('window_length',
							label='window length',
							set_cmd='TRIGger:A:I2S:WINDow:LENGth {}',
							get_cmd='TRIGger:A:I2S:WINDow:LENGth?',
							vals=vals.Ints(),
							get_parser=int)

		self.add_parameter('select_slope',
							label='word select slope',
							set_cmd='TRIGger:A:I2S:WSELect:SLOPe {}',
							get_cmd='TRIGger:A:I2S:WSELect:SLOPe?',
							vals=vals.Enum('POS', 'NEG'),
							get_parser=str.rstrip)

		self.add_parameter('word_slope',
							label='word select slope',
							set_cmd='TRIGger:A:I2S:WSSLope {}',
							get_cmd='TRIGger:A:I2S:WSSLope?',
							vals=vals.Enum('POS', 'NEG'),
							get_parser=str.rstrip)

class Bus_General(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, busnum):
		super().__init__(parent, name)

		self.add_parameter('type',
							label=f'bus {busnum} type',
							set_cmd=f'BUS{busnum}:TYPE {{}}',
							get_cmd=f'BUS{busnum}:TYPE?',
							vals=vals.Enum('PAR', 'CPAR', 'I2C', 'SPI', 'SSPI', 'UART', 'CAN', 'LIN', 'I2S', 'MILS', 'ARIN'),
							get_parser=str.rstrip)

		self.add_parameter('state',
							label=f'bus {busnum} state',
							set_cmd=f'BUS{busnum}:STATe {{}}',
							get_cmd=f'BUS{busnum}:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('format',
							label=f'bus {busnum} format',
							set_cmd=f'BUS{busnum}:FORMat {{}}',
							get_cmd=f'BUS{busnum}:FORMat?',
							vals=vals.Enum('ASC', 'HEX', 'BIN', 'DEC', 'OCT'),
							get_parser=str.rstrip)

		self.add_parameter('bits_signals',
							label=f'bus {busnum} bits signals',
							set_cmd=f'BUS{busnum}:DSIGnals {{}}',
							get_cmd=f'BUS{busnum}:DSIGnals?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('display_size',
							label=f'bus {busnum} display size',
							set_cmd=f'BUS{busnum}:DSIZe {{}}',
							get_cmd=f'BUS{busnum}:DSIZe?',
							vals=vals.Enum('SMAL', 'MED', 'LARG', 'DIV2', 'DIV4'),
							get_parser=str.rstrip)

		self.add_parameter('position',
							label=f'bus {busnum} position',
							set_cmd=f'BUS{busnum}:POSition {{}}',
							get_cmd=f'BUS{busnum}:POSition?',
							vals=vals.Numbers(-5,5),
							get_parser=float)

		self.add_parameter('result',
							label=f'bus {busnum} result',
							set_cmd=f'BUS{busnum}:RESult {{}}',
							get_cmd=f'BUS{busnum}:RESult?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

class CAN(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, busnum):
		super().__init__(parent, name)

		self.add_parameter('data_source',
							label=f'bus {busnum} data source',
							set_cmd=f'BUS{busnum}:CAN:DATA:SOURce {{}}',
							get_cmd=f'BUS{busnum}:CAN:DATA:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15'),
							get_parser=str.rstrip)

		self.add_parameter('type',
							label=f'bus {busnum} signal type',
							set_cmd=f'BUS{busnum}:CAN:TYPE {{}}',
							get_cmd=f'BUS{busnum}:CAN:TYPE?',
							vals=vals.Enum('CANH', 'CANL'),
							get_parser=str.rstrip)

		self.add_parameter('sample_point',
							label=f'bus {busnum} sample point',
							set_cmd=f'BUS{busnum}:CAN:SAMPlepoint {{}}',
							get_cmd=f'BUS{busnum}:CAN:SAMPlepoint?',
							vals=vals.Ints(10,90),
							get_parser=int)

		self.add_parameter('bit_rate',
							label=f'bus {busnum} bit rate',
							set_cmd=f'BUS{busnum}:CAN:BITRate {{}}',
							get_cmd=f'BUS{busnum}:CAN:BITRate?',
							vals=vals.Numbers(100,5.04e6),
							get_parser=float)

class CAN_Decode(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, busnum, framenum, bytenum):
		super().__init__(parent, name)

		self.add_parameter('count',
							label=f'bus {busnum} count',
							get_cmd=f'BUS{busnum}:CAN:FCOunt?',
							get_parser=str.rstrip)

		self.add_parameter('type',
							label=f'bus {busnum} frame {framenum} type',
							get_cmd=f'BUS{busnum}:CAN:FRAMe{framenum}:STATus?',
							get_parser=str.rstrip)

		self.add_parameter('start',
							label=f'bus {busnum} frame {framenum} start',
							get_cmd=f'BUS{busnum}:CAN:FRAMe{framenum}:STARt?',
							get_parser=str.rstrip)

		self.add_parameter('stop',
							label=f'bus {busnum} frame {framenum} stop',
							get_cmd=f'BUS{busnum}:CAN:FRAMe{framenum}:STOP?',
							get_parser=str.rstrip)

		self.add_parameter('data',
							label=f'bus {busnum} frame {framenum} data',
							get_cmd=f'BUS{busnum}:CAN:FRAMe{framenum}:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('acknowledge_state',
							label=f'bus {busnum} frame {framenum} acknowledge field state',
							get_cmd=f'BUS{busnum}:CAN:FRAMe{framenum}:ACKState?',
							get_parser=str.rstrip)

		self.add_parameter('acknowledge_value',
							label=f'bus {busnum} frame {framenum} acknowledge field value',
							get_cmd=f'BUS{busnum}:CAN:FRAMe{framenum}:ACKValue?',
							get_parser=str.rstrip)

		self.add_parameter('checksum_state',
							label=f'bus {busnum} frame {framenum} checksum state',
							get_cmd=f'BUS{busnum}:CAN:FRAMe{framenum}:CSSTate?',
							get_parser=str.rstrip)

		self.add_parameter('checksum_value',
							label=f'bus {busnum} frame {framenum} checksum value',
							get_cmd=f'BUS{busnum}:CAN:FRAMe{framenum}:CSValue?',
							get_parser=float)

		self.add_parameter('data_length',
							label=f'bus {busnum} frame {framenum} data length code',
							get_cmd=f'BUS{busnum}:CAN:FRAMe{framenum}:DLCState',
							get_parser=str.rstrip)

		self.add_parameter('data_bytes',
							label=f'bus {busnum} frame {framenum} data bytes',
							get_cmd=f'BUS{busnum}:CAN:FRAMe{framenum}:DLCValue?',
							get_parser=int)

		self.add_parameter('ID_state',
							label=f'bus {busnum} frame {framenum} ID state',
							get_cmd=f'BUS{busnum}:CAN:FRAMe{framenum}:IDSTate?',
							get_parser=str.rstrip)

		self.add_parameter('ID_type',
							label=f'bus {busnum} frame {framenum} ID type',
							get_cmd=f'BUS{busnum}:CAN:FRAMe{framenum}:IDTYpe?',
							get_parser=str.rstrip)

		self.add_parameter('ID_value',
							label=f'bus {busnum} frame {framenum} ID value',
							get_cmd=f'BUS{busnum}:CAN:FRAMe{framenum}:IDValue?',
							get_parser=float)

		self.add_parameter('stuffing_error',
							label=f'bus {busnum} frame {framenum} stuffing error',
							get_cmd=f'BUS{busnum}:CAN:FRAMe{framenum}:BSEPosition?',
							get_parser=str.rstrip)

		self.add_parameter('byte_count',
							label=f'bus {busnum} frame {framenum} byte count',
							get_cmd=f'BUS{busnum}:CAN:FRAMe{framenum}:BCOunt?',
							get_parser=int)

		self.add_parameter('byte_state',
							label=f'bus {busnum} frame {framenum} byte {bytenum} byte state',
							get_cmd=f'BUS{busnum}:CAN:FRAMe{framenum}:BYTE{bytenum}:STATe?',
							get_parser=str.rstrip)

		self.add_parameter('byte_value',
							label=f'bus {busnum} frame {framenum} byte {bytenum} byte value',
							get_cmd=f'BUS{busnum}:CAN:FRAMe{framenum}:BYTE{bytenum}:VALue?',
							get_parser=float)

class CAN_Search(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('condition',
							label='search condition',
							set_cmd='SEARch:PROTocol:CAN:CONDition {}',
							get_cmd='SEARch:PROTocol:CAN:CONDition?',
							vals=vals.Enum('FRAM', 'ERR', 'IDEN', 'IDD', 'IDER'),
							get_parser=str.rstrip)

		self.add_parameter('frame',
							label='search frame',
							set_cmd='SEARch:PROTocol:CAN:FRAMe {}',
							get_cmd='SEARch:PROTocol:CAN:FRAMe?',
							vals=vals.Enum('SOF', 'EOF', 'OVER', 'ERR', 'DTA11', 'DTA29', 'REM11', 'REM29'),
							get_parser=str.rstrip)

		self.add_parameter('acknowledge_error',
							label='acknowledge error',
							set_cmd='SEARch:PROTocol:CAN:ACKerror {}',
							get_cmd='SEARch:PROTocol:CAN:ACKerror?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('bit_stuffing',
							label='bit stuffing error',
							set_cmd='SEARch:PROTocol:CAN:BITSterror {}',
							get_cmd='SEARch:PROTocol:CAN:BITSterror?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('cyclic_redundancy',
							label='cyclic redundancy error',
							set_cmd='SEARch:PROTocol:CAN:CRCerror {}',
							get_cmd='SEARch:PROTocol:CAN:CRCerror?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('form_error',
							label='form error',
							set_cmd='SEARch:PROTocol:CAN:FORMerror {}',
							get_cmd='SEARch:PROTocol:CAN:FORMerror?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('frame_type',
							label='frame type',
							set_cmd='SEARch:PROTocol:CAN:FTYPe {}',
							get_cmd='SEARch:PROTocol:CAN:FTYPe?',
							vals=vals.Enum('DATA', 'REM', 'ANY'),
							get_parser=str.rstrip)

		self.add_parameter('ID_type',
							label='ID type',
							set_cmd='SEARch:PROTocol:CAN:ITYPe {}',
							get_cmd='SEARch:PROTocol:CAN:ITYPe?',
							vals=vals.Enum('B11', 'B29'),
							get_parser=str.rstrip)

		self.add_parameter('ID_condition',
							label='ID condition',
							set_cmd='SEARch:PROTocol:CAN:ICONdition {}',
							get_cmd='SEARch:PROTocol:CAN:ICONdition?',
							vals=vals.Enum('EQU', 'NEQ', 'GTH', 'LTH'),
							get_parser=str.rstrip)

		self.add_parameter('identifier',
							label='identifier',
							set_cmd='SEARch:PROTocol:CAN:IDENtifier {}',
							get_cmd='SEARch:PROTocol:CAN:IDENtifier?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('data_length',
							label='data length',
							set_cmd='SEARch:PROTocol:CAN:DLENgth {}',
							get_cmd='SEARch:PROTocol:CAN:DLENgth?',
							vals=vals.Ints(0,8),
							get_parser=int)

		self.add_parameter('data_condition',
							label='data condition',
							set_cmd='SEARch:PROTocol:CAN:DCONdition {}',
							get_cmd='SEARch:PROTocol:CAN:DCONdition?',
							vals=vals.Enum('EQU', 'NEQ', 'GTH', 'LTH'),
							get_parser=str.rstrip)

		self.add_parameter('data',
							label='data',
							set_cmd='SEARch:PROTocol:CAN:DATA {}',
							get_cmd='SEARch:PROTocol:CAN:DATA?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

class CAN_Trigger(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('type',
							label='trigger type',
							set_cmd='TRIGger:A:CAN:TYPE {}',
							get_cmd='TRIGger:A:CAN:TYPE?',
							vals=vals.Enum('STOF', 'EOF', 'ID', 'IDDT', 'FTYP', 'ERRC'),
							get_parser=str.rstrip)

		self.add_parameter('frame_type',
							label='frame type',
							set_cmd='TRIGger:A:CAN:FTYPe {}',
							get_cmd='TRIGger:A:CAN:FTYPe?',
							vals=vals.Enum('DATA', 'REM', 'OVER', 'ANY'),
							get_parser=str.rstrip)

		self.add_parameter('identifier_type',
							label='identifier type',
							set_cmd='TRIGger:A:CAN:ITYPe {}',
							get_cmd='TRIGger:A:CAN:ITYPe?',
							vals=vals.Enum('B11', 'B29', 'ANY'),
							get_parser=str.rstrip)

		self.add_parameter('identifier_condition',
							label='identifier condition',
							set_cmd='TRIGger:A:CAN:ICONdition {}',
							get_cmd='TRIGger:A:CAN:ICONdition?',
							vals=vals.Enum('EQU', 'NEQ', 'GTH', 'LTH'),
							get_parser=str.rstrip)

		self.add_parameter('identifier',
							label='identifier',
							set_cmd='TRIGger:A:CAN:IDENtifier {}',
							get_cmd='TRIGger:A:CAN:IDENtifier?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('data_condition',
							label='data condition',
							set_cmd='TRIGger:A:CAN:DCONdition {}',
							get_cmd='TRIGger:A:CAN:DCONdition?',
							vals=vals.Enum('EQU', 'NEQ', 'GTH', 'LTH'),
							get_parser=str.rstrip)

		self.add_parameter('data_length',
							label='data length',
							set_cmd='TRIGger:A:CAN:DLC {}',
							get_cmd='TRIGger:A:CAN:DLC?',
							vals=vals.Ints(0,8),
							get_parser=int)

		self.add_parameter('data',
							label='data',
							set_cmd='TRIGger:A:CAN:DATA {}',
							get_cmd='TRIGger:A:CAN:DATA?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('acknowledge_error',
							label='acknowledge error',
							set_cmd='TRIGger:A:CAN:ACKerror {}',
							get_cmd='TRIGger:A:CAN:ACKerror?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('bit_stuffing',
							label='bit stuffing error',
							set_cmd='TRIGger:A:CAN:BITSterror {}',
							get_cmd='TRIGger:A:CAN:BITSterror?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('cyclic_redundancy',
							label='cyclic redundancy error',
							set_cmd='TRIGger:A:CAN:CRCerror {}',
							get_cmd='TRIGger:A:CAN:CRCerror?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('form_error',
							label='form error',
							set_cmd='TRIGger:A:CAN:FORMerror {}',
							get_cmd='TRIGger:A:CAN:FORMerror?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

class General_Bus(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, bustype):
		super().__init__(parent, name)

		self.add_parameter('label',
							label=f'bus {bustype} label',
							set_cmd=f'BUS{bustype}:LABel {{}}',
							get_cmd=f'BUS{bustype}:LABel?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('state',
							label=f'bus {bustype} state',
							set_cmd=f'BUS{bustype}:LABel:STATe {{}}',
							get_cmd=f'BUS{bustype}:LABel:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

class Inter_Integrated_Config(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, busnum):
		super().__init__(parent, name)

		self.add_parameter('clock_source',
							label=f'bus {busnum} clock source',
							set_cmd=f'BUS{busnum}:I2C:CLOCk:SOURce {{}}',
							get_cmd=f'BUS{busnum}:I2C:CLOCk:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15'),
							get_parser=str.rstrip)

		self.add_parameter('data_source',
							label=f'bus {busnum} data source',
							set_cmd=f'BUS{busnum}:I2C:DATA:SOURce {{}}',
							get_cmd=f'BUS{busnum}:I2C:DATA:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15'),
							get_parser=str.rstrip)

class Inter_Integrated_Decode(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, busnum, framenum, bytenum):
		super().__init__(parent, name)

		self.add_parameter('count',
							label=f'bus {busnum} frame count',
							get_cmd=f'BUS{busnum}:I2C:FCOunt?',
							get_parser=int)

		self.add_parameter('data',
							label=f'bus {busnum} frame {framenum} data',
							get_cmd=f'BUS{busnum}:I2C:FRAMe{framenum}:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('status',
							label=f'bus {busnum} frame {framenum} status',
							get_cmd=f'BUS{busnum}:I2C:FRAMe{framenum}:STATus?',
							get_parser=str.rstrip)

		self.add_parameter('start',
							label=f'bus {busnum} frame {framenum} start',
							get_cmd=f'BUS{busnum}:I2C:FRAMe{framenum}:STARt?',
							get_parser=float)

		self.add_parameter('stop',
							label=f'bus {busnum} frame {framenum} stop',
							get_cmd=f'BUS{busnum}:I2C:FRAMe{framenum}:STOP?',
							get_parser=float)

		self.add_parameter('address_acknowledge',
							label=f'bus {busnum} frame {framenum} address acknowledge',
							get_cmd=f'BUS{busnum}:I2C:FRAMe{framenum}:AACCess?',
							get_parser=str.rstrip)

		self.add_parameter('access',
							label=f'bus {busnum} frame {framenum} access',
							get_cmd=f'BUS{busnum}:I2C:FRAMe{framenum}:ACCess?',
							get_parser=str.rstrip)

		self.add_parameter('complete',
							label=f'bus {busnum} frame {framenum} complete',
							get_cmd=f'BUS{busnum}:I2C:FRAMe{framenum}:ACOMplete?',
							get_parser=str.rstrip)

		self.add_parameter('start_time',
							label=f'bus {busnum} frame {framenum} start time',
							get_cmd=f'BUS{busnum}:I2C:FRAMe{framenum}:ADBStart?',
							get_parser=float)

		self.add_parameter('address',
							label=f'bus {busnum} frame {framenum} address',
							get_cmd=f'BUS{busnum}:I2C:FRAMe{framenum}:ADDRess?',
							get_parser=int)

		self.add_parameter('decimal',
							label=f'bus {busnum} frame {framenum} decimal address',
							get_cmd=f'BUS{busnum}:I2C:FRAMe{framenum}:ADEVice?',
							get_parser=int)

		self.add_parameter('address_length',
							label=f'bus {busnum} frame {framenum} address length',
							get_cmd=f'BUS{busnum}:I2C:FRAMe{framenum}:AMODe?',
							get_parser=str.rstrip)

		self.add_parameter('address_start',
							label=f'bus {busnum} frame {framenum} address start',
							get_cmd=f'BUS{busnum}:I2C:FRAMe{framenum}:ASTart?',
							get_parser=float)

		self.add_parameter('bytes',
							label=f'bus {busnum} frame {framenum} data bytes count',
							get_cmd=f'BUS{busnum}:I2C:FRAMe{framenum}:BCOunt?',
							get_parser=str.rstrip)

		self.add_parameter('byte_access',
							label=f'bus {busnum} frame {framenum} byte {bytenum} access',
							get_cmd=f'BUS{busnum}:I2C:FRAMe{framenum}:BYTE{bytenum}:ACCess?',
							get_parser=str.rstrip)

		self.add_parameter('start_byte',
							label=f'bus {busnum} frame {framenum} byte {bytenum} start time',
							get_cmd=f'BUS{busnum}:I2C:FRAMe{framenum}:BYTE{bytenum}:ACKStart?',
							get_parser=float)

		self.add_parameter('byte_complete',
							label=f'bus {busnum} frame {framenum} byte {bytenum} complete',
							get_cmd=f'BUS{busnum}:I2C:FRAMe{framenum}:BYTE{bytenum}:COMPlete?',
							get_parser=str.rstrip)

		self.add_parameter('byte_start',
							label=f'bus {busnum} frame {framenum} byte {bytenum} byte start',
							get_cmd=f'BUS{busnum}:I2C:FRAMe{framenum}:BYTE{bytenum}:STARt?',
							get_parser=str.rstrip)

		self.add_parameter('byte_value',
							label=f'bus {busnum} frame {framenum} byte {bytenum} byte value',
							get_cmd=f'BUS{busnum}:I2C:FRAMe{framenum}:BYTE{bytenum}:VALue?',
							get_parser=int)

class Inter_Integrated_Trigger(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('mode',
							label='trigger mode',
							set_cmd='TRIGger:A:I2C:MODE {}',
							get_cmd='TRIGger:A:I2C:MODE?',
							vals=vals.Enum('STAR', 'REST', 'STOP', 'MACK', 'PATT'),
							get_parser=str.rstrip)

		self.add_parameter('access',
							label='trigger access',
							set_cmd='TRIGger:A:I2C:ACCess {}',
							get_cmd='TRIGger:A:I2C:ACCess?',
							vals=vals.Enum('READ', 'WRIT'),
							get_parser=str.rstrip)

		self.add_parameter('address',
							label='trigger address',
							set_cmd='TRIGger:A:I2C:ADDRess {}',
							get_cmd='TRIGger:A:I2C:ADDRess?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('address_mode',
							label='trigger address mode',
							set_cmd='TRIGger:A:I2C:AMODe {}',
							get_cmd='TRIGger:A:I2C:AMODe?',
							vals=vals.Enum('NORM', 'EXT'),
							get_parser=str.rstrip)

		self.add_parameter('data_pattern',
							label='trigger data pattern',
							set_cmd='TRIGger:A:I2C:PATTern {}',
							get_cmd='TRIGger:A:I2C:PATTern?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('pattern_length',
							label='trigger pattern length',
							set_cmd='TRIGger:A:I2C:PLENgth {}',
							get_cmd='TRIGger:A:I2C:PLENgth?',
							vals=vals.Ints(1,3),
							get_parser=int)

		self.add_parameter('byte_offset',
							label='trigger pattern byte offset',
							set_cmd='TRIGger:A:I2C:POFFset {}',
							get_cmd='TRIGger:A:I2C:POFFset?',
							vals=vals.Ints(0,4095),
							get_parser=int)

class LIN_Config(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, busnum):
		super().__init__(parent, name)

		self.add_parameter('source',
							label=f'bus {busnum} source',
							set_cmd=f'BUS{busnum}:LIN:DATA:SOURce {{}}',
							get_cmd=f'BUS{busnum}:LIN:DATA:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15'),
							get_parser=str.rstrip)

		self.add_parameter('polarity',
							label=f'bus {busnum} polarity',
							set_cmd=f'BUS{busnum}:LIN:POLarity {{}}',
							get_cmd=f'BUS{busnum}:LIN:POLarity?',
							vals=vals.Enum('IDLH', 'IDLL'),
							get_parser=str.rstrip)

		self.add_parameter('standard',
							label=f'bus {busnum} standard',
							set_cmd=f'BUS{busnum}:LIN:STANdard {{}}',
							get_cmd=f'BUS{busnum}:LIN:STANdard?',
							vals=vals.Enum('V1X', 'V2X', 'J2602', 'AUTO'),
							get_parser=str.rstrip)

		self.add_parameter('bit_rate',
							label=f'bus {busnum} bit rate',
							set_cmd=f'BUS{busnum}:LIN:BITRate {{}}',
							get_cmd=f'BUS{busnum}:LIN:BITRate?',
							vals=vals.Numbers(100,5e6),
							unit='Bit/s',
							get_parser=float)

class LIN_Decode(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, busnum, framenum, bytenum):
		super().__init__(parent, name)

		self.add_parameter('count',
							label=f'bus {busnum} count',
							get_cmd=f'BUS{busnum}:LIN:FCOunt?',
							get_parser=int)

		self.add_parameter('data',
							label=f'bus {busnum} frame {framenum} data',
							get_cmd=f'BUS{busnum}:LIN:FRAMe{framenum}:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('status',
							label=f'bus {busnum} frame {framenum} status',
							get_cmd=f'BUS{busnum}:LIN:FRAMe{framenum}:STATus?',
							get_parser=str.rstrip)

		self.add_parameter('start',
							label=f'bus {busnum} frame {framenum} start',
							get_cmd=f'BUS{busnum}:LIN:FRAMe{framenum}:STATus?',
							get_parser=float)

		self.add_parameter('stop',
							label=f'bus {busnum} frame {framenum} stop',
							get_cmd=f'BUS{busnum}:LIN:FRAMe{framenum}:STOP?',
							get_parser=float)

		self.add_parameter('checksum_state',
							label=f'bus {busnum} frame {framenum} checksum state',
							get_cmd=f'BUS{busnum}:LIN:FRAMe{framenum}:CSSTate?',
							get_parser=str.rstrip)

		self.add_parameter('checksum_value',
							label=f'bus {busnum} frame {framenum} checksum value',
							get_cmd=f'BUS{busnum}:LIN:FRAMe{framenum}:CSValue?',
							get_parser=float)

		self.add_parameter('parity',
							label=f'bus {busnum} frame {framenum} parity',
							get_cmd=f'BUS{busnum}:LIN:FRAMe{framenum}:IDPValue?',
							get_parser=float)

		self.add_parameter('identifier_state',
							label=f'bus {busnum} frame {framenum} identifier state',
							get_cmd=f'BUS{busnum}:LIN:FRAMe{framenum}:IDSTate?',
							get_parser=str.rstrip)

		self.add_parameter('identifier_value',
							label=f'bus {busnum} frame {framenum} identifier value',
							get_cmd=f'BUS{busnum}:LIN:FRAMe{framenum}:IDValue?',
							get_parser=float)

		self.add_parameter('sync_state',
							label=f'bus {busnum} frame {framenum} sync field state',
							get_cmd=f'BUS{busnum}:LIN:FRAMe{framenum}:SYSTate?',
							get_parser=str.rstrip)

		self.add_parameter('synchronization_value',
							label=f'bus {busnum} frame {framenum} synchronization value',
							get_cmd=f'BUS{busnum}:LIN:FRAMe{framenum}:SYValue?',
							get_parser=float)

		self.add_parameter('version',
							label=f'bus {busnum} frame {framenum} version',
							get_cmd=f'BUS{busnum}:LIN:FRAMe{framenum}:VERSion?',
							get_parser=str.rstrip)

		self.add_parameter('bytes_count',
							label=f'bus {busnum} frame {framenum} data bytes count',
							get_cmd=f'BUS{busnum}:LIN:FRAMe{framenum}:BCOunt?',
							get_parser=int)

		self.add_parameter('byte_state',
							label=f'bus {busnum} frame {framenum} byte {bytenum} data byte state',
							get_cmd=f'BUS{busnum}:LIN:FRAMe{framenum}:BYTE{bytenum}:STATe?',
							get_parser=str.rstrip)

		self.add_parameter('byte_value',
							label=f'bus {busnum} frame {framenum} byte {bytenum} data byte value',
							get_cmd=f'BUS{busnum}:LIN:FRAMe{framenum}:BYTE{bytenum}:VALue?',
							get_parser=float)

class LIN_Search(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('condition',
							label='search condition',
							set_cmd='SEARch:PROTocol:LIN:CONDition {}',
							get_cmd='SEARch:PROTocol:LIN:CONDition?',
							vals=vals.Enum('FRAMe', 'ERRor', 'IDEN', 'IDD', 'IDER'),
							get_parser=str.rstrip)

		self.add_parameter('frame',
							label='search frame',
							set_cmd='SEARch:PROTocol:LIN:FRAMe {}',
							get_cmd='SEARch:PROTocol:LIN:FRAMe?',
							vals=vals.Enum('SOF', 'WAK'),
							get_parser=str.rstrip)

		self.add_parameter('parity_error',
							label='ID parity error',
							set_cmd='SEARch:PROTocol:LIN:IPERror {}',
							get_cmd='SEARch:PROTocol:LIN:IPERror?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('checksum_error',
							label='checksum error',
							set_cmd='SEARch:PROTocol:LIN:CHKSerror {}',
							get_cmd='SEARch:PROTocol:LIN:CHKSerror?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('sync_error',
							label='sync error',
							set_cmd='SEARch:PROTocol:LIN:SYERror {}',
							get_cmd='SEARch:PROTocol:LIN:SYERror?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('identifier_condition',
							label='identifier condition',
							set_cmd='SEARch:PROTocol:LIN:ICONdition {}',
							get_cmd='SEARch:PROTocol:LIN:ICONdition?',
							vals=vals.Enum('EQU', 'NEQ', 'GTH', 'LTH'),
							get_parser=str.rstrip)

		self.add_parameter('identifier',
							label='identifier',
							set_cmd='SEARch:PROTocol:LIN:IDENtifier {}',
							get_cmd='SEARch:PROTocol:LIN:IDENtifier?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('data_length',
							label='data length',
							set_cmd='SEARch:PROTocol:LIN:DLENgth {}',
							get_cmd='SEARch:PROTocol:LIN:DLENgth?',
							vals=vals.Ints(1,8),
							get_parser=int)

		self.add_parameter('data_condition',
							label='data condition',
							set_cmd='SEARch:PROTocol:LIN:DCONdition {}',
							get_cmd='SEARch:PROTocol:LIN:DCONdition?',
							vals=vals.Enum('EQU', 'NEQ', 'GTH', 'LTH'),
							get_parser=str.rstrip)

		self.add_parameter('data',
							label='data',
							set_cmd='SEARch:PROTocol:LIN:DATA {}',
							get_cmd='SEARch:PROTocol:LIN:DATA?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

class LIN_Trigger(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('type',
							label='trigger type',
							set_cmd='TRIGger:A:LIN:TYPE {}',
							get_cmd='TRIGger:A:LIN:TYPE?',
							vals=vals.Enum('SYNC', 'WKFR', 'ID', 'IDDT', 'ERRC'),
							get_parser=str.rstrip)

		self.add_parameter('checksum_error',
							label='checksum error',
							set_cmd='TRIGger:A:LIN:CHKSerror {}',
							get_cmd='TRIGger:A:LIN:CHKSerror?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('parity_error',
							label='ID parity error',
							set_cmd='TRIGger:A:LIN:IPERror {}',
							get_cmd='TRIGger:A:LIN:IPERror?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('sync_error',
							label='sync error',
							set_cmd='TRIGger:A:LIN:SYERror {}',
							get_cmd='TRIGger:A:LIN:SYERror?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('identifier_condition',
							label='identifier_condition',
							set_cmd='TRIGger:A:LIN:ICONdition {}',
							get_cmd='TRIGger:A:LIN:ICONdition?',
							vals=vals.Enum('EQU', 'NEQ', 'GTH', 'LTH'),
							get_parser=str.rstrip)

		self.add_parameter('identifier',
							label='identifier',
							set_cmd='TRIGger:A:LIN:IDENtifier {}',
							get_cmd='TRIGger:A:LIN:IDENtifier?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('data',
							label='data',
							set_cmd='TRIGger:A:LIN:DATA {}',
							get_cmd='TRIGger:A:LIN:DATA?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('data_condition',
							label='data condition',
							set_cmd='TRIGger:A:LIN:DCONdition {}',
							get_cmd='TRIGger:A:LIN:DCONdition?',
							vals=vals.Enum('EQU', 'NEQ', 'GTH', 'LTH'),
							get_parser=str.rstrip)

		self.add_parameter('data_length',
							label='data length',
							set_cmd='TRIGger:A:LIN:DLENgth {}',
							get_cmd='TRIGger:A:LIN:DLENgth?',
							vals=vals.Ints(1,8),
							get_parser=int)

class MIL_Config(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, busnum):
		super().__init__(parent, name)

		self.add_parameter('max_infinite',
							label=f'bus {busnum} maximum infinite',
							set_cmd=f'BUS{busnum}:MILStd:IMGTime:INFinite {{}}',
							get_cmd=f'BUS{busnum}:MILStd:IMGTime:INFinite?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('max_time',
							label=f'bus {busnum} maximum time',
							set_cmd=f'BUS{busnum}:MILStd:IMGTime:MAXimum {{}}',
							get_cmd=f'BUS{busnum}:MILStd:IMGTime:MAXimum?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('min_time',
							label=f'bus {busnum} minimum time',
							set_cmd=f'BUS{busnum}:MILStd:IMGTime:MINimum {{}}',
							get_cmd=f'BUS{busnum}:MILStd:IMGTime:MINimum?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('polarity',
							label=f'bus {busnum} polarity',
							set_cmd=f'BUS{busnum}:MILStd:POLarity {{}}',
							get_cmd=f'BUS{busnum}:MILStd:POLarity?',
							vals=vals.Enum('POS', 'NEG'),
							get_parser=str.rstrip)

		self.add_parameter('response_infinite',
							label=f'bus {busnum} maximum infinite response time',
							set_cmd=f'BUS{busnum}:MILStd:RESPonsetime:INFinite {{}}',
							get_cmd=f'BUS{busnum}:MILStd:RESPonsetime:INFinite?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('response_max',
							label=f'bus {busnum} maximum response time',
							set_cmd=f'BUS{busnum}:MILStd:RESPonsetime:MAXimum {{}}',
							get_cmd=f'BUS{busnum}:MILStd:RESPonsetime:MAXimum?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('response_min',
							label=f'bus {busnum} minimum response time',
							set_cmd=f'BUS{busnum}:MILStd:RESPonsetime:MINimum {{}}',
							get_cmd=f'BUS{busnum}:MILStd:RESPonsetime:MINimum?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('source',
							label=f'bus {busnum} source',
							set_cmd=f'BUS{busnum}:MILStd:SOURce {{}}',
							get_cmd=f'BUS{busnum}:MILStd:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4'),
							get_parser=str.rstrip)

		self.add_parameter('upper_level',
							label=f'bus {busnum} upper level',
							set_cmd=f'BUS{busnum}:MILStd:THReshold:HIGH {{}}',
							get_cmd=f'BUS{busnum}:MILStd:THReshold:HIGH?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('lower_level',
							label=f'bus {busnum} lower level',
							set_cmd=f'BUS{busnum}:MILStd:THReshold:LOW {{}}',
							get_cmd=f'BUS{busnum}:MILStd:THReshold:LOW?',
							vals=vals.Numbers(),
							get_parser=float)

class MIL_Decode(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, busnum, framenum):
		super().__init__(parent, name)

		self.add_parameter('count',
							label=f'bus {busnum} count',
							get_cmd=f'BUS{busnum}:MILStd:WCOunt?',
							get_parser=int)

		self.add_parameter('modecode_type',
							label=f'bus {busnum} frame {framenum} modecode type',
							get_cmd=f'BUS{busnum}:MILStd:WORD{framenum}:COMMand:MCODe:CODE?',
							get_parser=str.rstrip)

		self.add_parameter('modecode_value',
							label=f'bus {busnum} frame {framenum} modecode value',
							get_cmd=f'BUS{busnum}:MILStd:WORD{framenum}:COMMand:MCODe:VALue?',
							get_parser=str.rstrip)

		self.add_parameter('rt_address',
							label=f'bus {busnum} frame {framenum} rt address',
							get_cmd=f'BUS{busnum}:MILStd:WORD{framenum}:COMMand:RTADdress?',
							get_parser=str.rstrip)

		self.add_parameter('sub_address',
							label=f'bus {busnum} frame {framenum} sub address',
							get_cmd=f'BUS{busnum}:MILStd:WORD{framenum}:COMMand:SADDress?',
							get_parser=str.rstrip)

		self.add_parameter('word_count',
							label=f'bus {busnum} frame {framenum} word count',
							get_cmd=f'BUS{busnum}:MILStd:WORD{framenum}:COMMand:WCOunt?',
							get_parser=str.rstrip)

		self.add_parameter('data_word',
							label=f'bus {busnum} frame {framenum} data word',
							get_cmd=f'BUS{busnum}:MILStd:WORD{framenum}:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('intermessage_gap',
							label=f'bus {busnum} frame {framenum} intermessage gap time',
							get_cmd=f'BUS{busnum}:MILStd:WORD{framenum}:IMGTime?',
							get_parser=float)

		self.add_parameter('word_parity',
							label=f'bus {busnum} frame {framenum} word parity',
							get_cmd=f'BUS{busnum}:MILStd:WORD{framenum}:PARity?',
							get_parser=float)

		self.add_parameter('response_time',
							label=f'bus {busnum} frame {framenum} response time',
							get_cmd=f'BUS{busnum}:MILStd:WORD{framenum}:RTIMe?',
							get_parser=float)

		self.add_parameter('start_time',
							label=f'bus {busnum} frame {framenum} start time',
							get_cmd=f'BUS{busnum}:MILStd:WORD{framenum}:STARt?',
							get_parser=float)

		self.add_parameter('status_word',
							label=f'bus {busnum} frame {framenum} status word',
							get_cmd=f'BUS{busnum}:MILStd:WORD{framenum}:STATus?',
							get_parser=str.rstrip)

		self.add_parameter('broadcast_received',
							label=f'bus {busnum} frame {framenum} broadacast command received',
							get_cmd=f'BUS{busnum}:MILStd:WORD{framenum}:STATus:BCReceived?',
							get_parser=str.rstrip)

		self.add_parameter('busy',
							label=f'bus {busnum} frame {framenum} busy',
							get_cmd=f'BUS{busnum}:MILStd:WORD{framenum}:STATus:BUSY?',
							get_parser=str.rstrip)

		self.add_parameter('dynamic_bus',
							label=f'bus {busnum} frame {framenum} dynamic bus',
							get_cmd=f'BUS{busnum}:MILStd:WORD{framenum}:STATus:DBCaccept?',
							get_parser=str.rstrip)

		self.add_parameter('instrumentation',
							label=f'bus {busnum} frame {framenum} instrumentation bit',
							get_cmd=f'BUS{busnum}:MILStd:WORD{framenum}:STATus:INSTrument?',
							get_parser=str.rstrip)

		self.add_parameter('message_error',
							label=f'bus {busnum} frame {framenum} message error',
							get_cmd=f'BUS{busnum}:MILStd:WORD{framenum}:STATus:MERRor?',
							get_parser=str.rstrip)

		self.add_parameter('rt_word',
							label=f'bus {busnum} frame {framenum} specified rt address',
							get_cmd=f'BUS{busnum}:MILStd:WORD{framenum}:STATus:RTADdress?',
							get_parser=str.rstrip)

		self.add_parameter('service_request',
							label=f'bus {busnum} frame {framenum} service request',
							get_cmd=f'BUS{busnum}:MILStd:WORD{framenum}:STATus:SREQuest?',
							get_parser=str.rstrip)

		self.add_parameter('subsystem_state',
							label=f'bus {busnum} frame {framenum} subsystem bit state',
							get_cmd=f'BUS{busnum}:MILStd:WORD{framenum}:STATus:SUBSystem?',
							get_parser=str.rstrip)

		self.add_parameter('terminal_flag',
							label=f'bus {busnum} frame {framenum} terminal flag',
							get_cmd=f'BUS{busnum}:MILStd:WORD{framenum}:STATus:TERMinal?',
							get_parser=str.rstrip)

		self.add_parameter('stop_time',
							label=f'bus {busnum} frame {framenum} stop time',
							get_cmd=f'BUS{busnum}:MILStd:WORD{framenum}:STOP?',
							get_parser=str.rstrip)

		self.add_parameter('transmission_direction',
							label=f'bus {busnum} frame {framenum} transmission direction',
							get_cmd=f'BUS{busnum}:MILStd:WORD{framenum}:TRMode?',
							get_parser=str.rstrip)

		self.add_parameter('word_type',
							label=f'bus {busnum} frame {framenum} word type',
							get_cmd=f'BUS{busnum}:MILStd:WORD{framenum}:TYPE?',
							get_parser=str.rstrip)

class MIL_Search(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('condition',
							label='search condition',
							set_cmd='SEARch:PROTocol:MILStd:CONDition {}',
							get_cmd='SEARch:PROTocol:MILStd:CONDition?',
							vals=vals.Enum('WST', 'ERR', 'STAT', 'DATA', 'COMM', 'MCOD', 'CDAT'),
							get_parser=str.rstrip)

		self.add_parameter('comparison_data_condition',
							label='comparison condition',
							set_cmd='SEARch:PROTocol:MILStd:DATA:CONDition {}',
							get_cmd='SEARch:PROTocol:MILStd:DATA:CONDition?',
							vals=vals.Enum('OFF', 'EQU', 'NEQ', 'GTH', 'GEQ', 'LEQ', 'LTH', 'WITH', 'OUTS'),
							get_parser=str.rstrip)

		self.add_parameter('data_max',
							label='data maximum',
							set_cmd='SEARch:PROTocol:MILStd:DATA:MAXimum {}',
							get_cmd='SEARch:PROTocol:MILStd:DATA:MAXimum?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('data_min',
							label='data minimum',
							set_cmd='SEARch:PROTocol:MILStd:DATA:MINimum {}',
							get_cmd='SEARch:PROTocol:MILStd:DATA:MINimum?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('data_offset',
							label='data offset',
							set_cmd='SEARch:PROTocol:MILStd:DATA:OFFSet {}',
							get_cmd='SEARch:PROTocol:MILStd:DATA:OFFSet?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('data_words',
							label='data words',
							set_cmd='SEARch:PROTocol:MILStd:DATA:WORDs {}',
							get_cmd='SEARch:PROTocol:MILStd:DATA:WORDs?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('error_type',
							label='error type',
							set_cmd='SEARch:PROTocol:MILStd:ERRor {}',
							get_cmd='SEARch:PROTocol:MILStd:ERRor?',
							vals=vals.Enum('SYNC', 'PAR', 'TIM', 'MANC', 'ANY'),
							get_parser=str.rstrip)

		self.add_parameter('modecode_type',
							label='modecode type',
							set_cmd='SEARch:PROTocol:MILStd:MCODe {}',
							get_cmd='SEARch:PROTocol:MILStd:MCODe?',
							vals=vals.Enum('DBC', 'TSYN', 'TST', 'ISEL', 'TSH', 'OTSH', 'ITER', 'OIT', 'RES', 'VECT', 'RSYN', 'TLAS', 'BITW', 'STSH', 'OSTS', 'ANY'),
							get_parser=str.rstrip)

		self.add_parameter('rt_comparison',
							label='rt address comparison condition',
							set_cmd='SEARch:PROTocol:MILStd:RTADdress:CONDition {}',
							get_cmd='SEARch:PROTocol:MILStd:RTADdress:CONDition?',
							vals=vals.Enum('OFF', 'EQU', 'NEQ', 'GTH', 'GEQ', 'LEQ', 'LTH', 'WITH', 'OUTS'),
							get_parser=str.rstrip)

		self.add_parameter('rt_maximum',
							label='rt address maximum',
							set_cmd='SEARch:PROTocol:MILStd:RTADdress:MAXimum {}',
							get_cmd='SEARch:PROTocol:MILStd:RTADdress:MAXimum?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('rt_minimum',
							label='rt address minimum',
							set_cmd='SEARch:PROTocol:MILStd:RTADdress:MINimum {}',
							get_cmd='SEARch:PROTocol:MILStd:RTADdress:MINimum?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('subaddress_comparison',
							label='subaddress comparison condition',
							set_cmd='SEARch:PROTocol:MILStd:SADDress:CONDition {}',
							get_cmd='SEARch:PROTocol:MILStd:SADDress:CONDition?',
							vals=vals.Enum('OFF', 'EQU', 'NEQ', 'GTH', 'GEQ', 'LEQ', 'LTH', 'WITH', 'OUTS'),
							get_parser=str.rstrip)

		self.add_parameter('subaddress_maximum',
							label='subaddress maximum',
							set_cmd='SEARch:PROTocol:MILStd:SADDress:MAXimum {}',
							get_cmd='SEARch:PROTocol:MILStd:SADDress:MAXimum?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('modecode_address',
							label='modecode address',
							set_cmd='SEARch:PROTocol:MILStd:SADDress:MCADdress {}',
							get_cmd='SEARch:PROTocol:MILStd:SADDress:MCADdress?',
							vals=vals.Enum('A0', 'A31', 'EITH'),
							get_parser=str.rstrip)

		self.add_parameter('subaddress_minimum',
							label='subaddress minimum',
							set_cmd='SEARch:PROTocol:MILStd:SADDress:MINimum {}',
							get_cmd='SEARch:PROTocol:MILStd:SADDress:MINimum?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('broadcast_received',
							label='broadcast receieved bit',
							set_cmd='SEARch:PROTocol:MILStd:STATus:BCReceived {}',
							get_cmd='SEARch:PROTocol:MILStd:STATus:BCReceived?',
							vals=vals.Enum(0,1,'X'),
							get_parser=str.rstrip)

		self.add_parameter('busy',
							label='busy bit',
							set_cmd='SEARch:PROTocol:MILStd:STATus:BUSY {}',
							get_cmd='SEARch:PROTocol:MILStd:STATus:BUSY?',
							vals=vals.Enum(0,1,'X'),
							get_parser=str.rstrip)

		self.add_parameter('dynamic_bus',
							label='dynamic bus control',
							set_cmd='SEARch:PROTocol:MILStd:STATus:DBCaccept {}',
							get_cmd='SEARch:PROTocol:MILStd:STATus:DBCaccept?',
							vals=vals.Enum(0,1,'X'),
							get_parser=str.rstrip)

		self.add_parameter('instrument_bit',
							label='instrument bit',
							set_cmd='SEARch:PROTocol:MILStd:STATus:INSTrument {}',
							get_cmd='SEARch:PROTocol:MILStd:STATus:INSTrument?',
							vals=vals.Enum(0,1,'X'),
							get_parser=str.rstrip)

		self.add_parameter('message_error',
							label='message error',
							set_cmd='SEARch:PROTocol:MILStd:STATus:MERRor {}',
							get_cmd='SEARch:PROTocol:MILStd:STATus:MERRor?',
							vals=vals.Enum(0,1,'X'),
							get_parser=str.rstrip)

		self.add_parameter('service_request',
							label='service request',
							set_cmd='SEARch:PROTocol:MILStd:STATus:SREQuest {}',
							get_cmd='SEARch:PROTocol:MILStd:STATus:SREQuest?',
							vals=vals.Enum(0,1,'X'),
							get_parser=str.rstrip)

		self.add_parameter('subsystem_bit',
							label='subsystem bit',
							set_cmd='SEARch:PROTocol:MILStd:STATus:SUBSystem {}',
							get_cmd='SEARch:PROTocol:MILStd:STATus:SUBSystem?',
							vals=vals.Enum(0,1,'X'),
							get_parser=str.rstrip)

		self.add_parameter('terminal_bit',
							label='subsystem bit',
							set_cmd='SEARch:PROTocol:MILStd:STATus:TERMinal {}',
							get_cmd='SEARch:PROTocol:MILStd:STATus:TERMinal?',
							vals=vals.Enum(0,1,'X'),
							get_parser=str.rstrip)

		self.add_parameter('transmission_mode',
							label='transmission mode',
							set_cmd='SEARch:PROTocol:MILStd:TRMode {}',
							get_cmd='SEARch:PROTocol:MILStd:TRMode?',
							vals=vals.Enum('TRAN', 'REC', 'EITH'),
							get_parser=str.rstrip)

		self.add_parameter('transmission_type',
							label='transmission type',
							set_cmd='SEARch:PROTocol:MILStd:TTYPe {}',
							get_cmd='SEARch:PROTocol:MILStd:TTYPe?',
							vals=vals.Enum('BCRT', 'RTBC', 'RTRT', 'MCD'),
							get_parser=str.rstrip)

		self.add_parameter('comparison_condition',
							label='comparison condition',
							set_cmd='SEARch:PROTocol:MILStd:WCOunt:CONDition {}',
							get_cmd='SEARch:PROTocol:MILStd:WCOunt:CONDition?',
							vals=vals.Enum('OFF', 'EQU', 'NEQ', 'GTH', 'GEQ', 'LEQ', 'LTH', 'WITH', 'OUTS'),
							get_parser=str.rstrip)

		self.add_parameter('wordcount_max',
							label='maximum word count',
							set_cmd='SEARch:PROTocol:MILStd:WCOunt:MAXimum {}',
							get_cmd='SEARch:PROTocol:MILStd:WCOunt:MAXimum?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('wordcount_min',
							label='minimum word count',
							set_cmd='SEARch:PROTocol:MILStd:WCOunt:MINimum {}',
							get_cmd='SEARch:PROTocol:MILStd:WCOunt:MINimum?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('word_start',
							label='word start',
							set_cmd='SEARch:PROTocol:MILStd:WSTart {}',
							get_cmd='SEARch:PROTocol:MILStd:WSTart?',
							vals=vals.Enum('COMM', 'STAT', 'DATA'),
							get_parser=str.rstrip)

class MIL_Trigger(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('command_type',
							label='command type',
							set_cmd='TRIGger:A:MILStd:COMMand:TYPE {}',
							get_cmd='TRIGger:A:MILStd:COMMand:TYPE?',
							vals=vals.Enum('AWOR', 'MCOD'),
							get_parser=str.rstrip)

		self.add_parameter('comparison_condition',
							label='comparison condition',
							set_cmd='TRIGger:A:MILStd:DATA:CONDition {}',
							get_cmd='TRIGger:A:MILStd:DATA:CONDition?',
							vals=vals.Enum('EQU', 'NEQ', 'GTH', 'GEQ', 'LEQ', 'LTH', 'WITH', 'OUTS'),
							get_parser=str.rstrip)

		self.add_parameter('data_max',
							label='data maximum',
							set_cmd='TRIGger:A:MILStd:DATA:MAXimum {}',
							get_cmd='TRIGger:A:MILStd:DATA:MAXimum?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('data_min',
							label='data minimum',
							set_cmd='TRIGger:A:MILStd:DATA:MINimum {}',
							get_cmd='TRIGger:A:MILStd:DATA:MINimum?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('data_offset',
							label='data offset',
							set_cmd='TRIGger:A:MILStd:DATA:OFFSet {}',
							get_cmd='TRIGger:A:MILStd:DATA:OFFSet?',
							vals=vals.Enum(0,1),
							get_parser=str.rstrip)

		self.add_parameter('offset_condition',
							label='data offset condition',
							set_cmd='TRIGger:A:MILStd:DATA:OFFSet:CONDition {}',
							get_cmd='TRIGger:A:MILStd:DATA:OFFSet:CONDition?',
							vals=vals.Enum('EQU', 'NEQ', 'GTH', 'GEQ', 'LEQ', 'LTH'),
							get_parser=str.rstrip)

		self.add_parameter('data_words',
							label='data words',
							set_cmd='TRIGger:A:MILStd:DATA:WORDs {}',
							get_cmd='TRIGger:A:MILStd:DATA:WORDs?',
							vals=vals.Enum(0,1),
							get_parser=str.rstrip)

		self.add_parameter('manchester',
							label='manchester',
							set_cmd='TRIGger:A:MILStd:ERRor:MANChester {}',
							get_cmd='TRIGger:A:MILStd:ERRor:MANChester?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('error_parity',
							label='error parity',
							set_cmd='TRIGger:A:MILStd:ERRor:PARity {}',
							get_cmd='TRIGger:A:MILStd:ERRor:PARity?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('error_sync',
							label='error sync',
							set_cmd='TRIGger:A:MILStd:ERRor:SYNC {}',
							get_cmd='TRIGger:A:MILStd:ERRor:SYNC?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('error_timeout',
							label='error timeout',
							set_cmd='TRIGger:A:MILStd:ERRor:TIMeout {}',
							get_cmd='TRIGger:A:MILStd:ERRor:TIMeout?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('frame',
							label='frame',
							set_cmd='TRIGger:A:MILStd:FRAMe {}',
							get_cmd='TRIGger:A:MILStd:FRAMe?',
							vals=vals.Enum('COMM', 'STAT', 'DATA', 'ALL'),
							get_parser=str.rstrip)

		self.add_parameter('mode_code',
							label='mode code',
							set_cmd='TRIGger:A:MILStd:MCODe:CODE {}',
							get_cmd='TRIGger:A:MILStd:MCODe:CODE?',
							vals=vals.Enum('DBC', 'TSYN', 'TST', 'ISEL', 'TSH', 'OTSH', 'ITER', 'OIT', 'RES', 'VECT', 'RSYN', 'TLAS', 'BITW', 'STSH', 'OSTS', 'ANY'),
							get_parser=str.rstrip)

		self.add_parameter('mode_value',
							label='mode code value',
							set_cmd='TRIGger:A:MILStd:MCODe:VALue {}',
							get_cmd='TRIGger:A:MILStd:MCODe:VALue?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('trigger_mode',
							label='trigger mode',
							set_cmd='TRIGger:A:MILStd:MODE {}',
							get_cmd='TRIGger:A:MILStd:MODE?',
							vals=vals.Enum('SYNC', 'FRAME', 'ERR', 'COMM', 'STAT', 'DATA', 'CDAT'),
							get_parser=str.rstrip)

		self.add_parameter('address_condition',
							label='address condition',
							set_cmd='TRIGger:A:MILStd:RTADdress:CONDition {}',
							get_cmd='TRIGger:A:MILStd:RTADdress:CONDition?',
							vals=vals.Enum('EQU', 'NEQ', 'GTH', 'GEQ', 'LEQ', 'LTH', 'WITH', 'OUTS'),
							get_parser=str.rstrip)

		self.add_parameter('address_maximum',
							label='address maximum',
							set_cmd='TRIGger:A:MILStd:RTADdress:MAXimum {}',
							get_cmd='TRIGger:A:MILStd:RTADdress:MAXimum?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('address_minimum',
							label='address minimum',
							set_cmd='TRIGger:A:MILStd:RTADdress:MINimum {}',
							get_cmd='TRIGger:A:MILStd:RTADdress:MINimum?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('subaddress_condition',
							label='subaddress condition',
							set_cmd='TRIGger:A:MILStd:SADDress:CONDition {}',
							get_cmd='TRIGger:A:MILStd:SADDress:CONDition?',
							vals=vals.Enum('EQU', 'NEQ', 'GTH', 'GEQ', 'LEQ', 'LTH', 'WITH', 'OUTS'),
							get_parser=str.rstrip)

		self.add_parameter('subaddress_maximum',
							label='subaddress maximum',
							set_cmd='TRIGger:A:MILStd:SADDress:MAXimum {}',
							get_cmd='TRIGger:A:MILStd:SADDress:MAXimum?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('modecode_address',
							label='modecode address',
							set_cmd='TRIGger:A:MILStd:SADDress:MCADdress {}',
							get_cmd='TRIGger:A:MILStd:SADDress:MCADdress?',
							vals=vals.Enum('A0', 'A31', 'EITH'),
							get_parser=str.rstrip)

		self.add_parameter('subaddress_minimum',
							label='subaddress minimum',
							set_cmd='TRIGger:A:MILStd:SADDress:MINimum {}',
							get_cmd='TRIGger:A:MILStd:SADDress:MINimum?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('broadcast_received',
							label='broadcast received',
							set_cmd='TRIGger:A:MILStd:STATus:BCReceived {}',
							get_cmd='TRIGger:A:MILStd:STATus:BCReceived?',
							vals=vals.Enum(0,1,'X'),
							get_parser=str.rstrip)

		self.add_parameter('busy_status',
							label='busy status',
							set_cmd='TRIGger:A:MILStd:STATus:BUSY {}',
							get_cmd='TRIGger:A:MILStd:STATus:BUSY?',
							vals=vals.Enum(0,1,'X'),
							get_parser=str.rstrip)

		self.add_parameter('dbc_accept',
							label='dbc accept',
							set_cmd='TRIGger:A:MILStd:STATus:DBCaccept {}',
							get_cmd='TRIGger:A:MILStd:STATus:DBCaccept?',
							vals=vals.Enum(0,1,'X'),
							get_parser=str.rstrip)

		self.add_parameter('instrumentation_status',
							label='instrumentation status',
							set_cmd='TRIGger:A:MILStd:STATus:INSTrument {}',
							get_cmd='TRIGger:A:MILStd:STATus:INSTrument?',
							vals=vals.Enum(0,1,'X'),
							get_parser=str.rstrip)

		self.add_parameter('message_error',
							label='error message',
							set_cmd='TRIGger:A:MILStd:STATus:MERRor {}',
							get_cmd='TRIGger:A:MILStd:STATus:MERRor?',
							vals=vals.Enum(0,1,'X'),
							get_parser=str.rstrip)

		self.add_parameter('state_request',
							label='state request',
							set_cmd='TRIGger:A:MILStd:STATus:SREQuest {}',
							get_cmd='TRIGger:A:MILStd:STATus:SREQuest?',
							vals=vals.Enum(0,1,'X'),
							get_parser=str.rstrip)

		self.add_parameter('subsystem',
							label='subsystem',
							set_cmd='TRIGger:A:MILStd:STATus:SUBSystem {}',
							get_cmd='TRIGger:A:MILStd:STATus:SUBSystem?',
							vals=vals.Enum(0,1,'X'),
							get_parser=str.rstrip)

		self.add_parameter('terminal',
							label='terminal status',
							set_cmd='TRIGger:A:MILStd:STATus:TERMinal {}',
							get_cmd='TRIGger:A:MILStd:STATus:TERMinal?',
							vals=vals.Enum(0,1,'X'),
							get_parser=str.rstrip)

		self.add_parameter('sync_mode',
							label='sync mode',
							set_cmd='TRIGger:A:MILStd:SYNC {}',
							get_cmd='TRIGger:A:MILStd:SYNC?',
							vals=vals.Enum('CST', 'DATA', 'EITH'),
							get_parser=str.rstrip)

		self.add_parameter('data_direction',
							label='data direction',
							set_cmd='TRIGger:A:MILStd:TRMode {}',
							get_cmd='TRIGger:A:MILStd:TRMode?',
							vals=vals.Enum('TRAN', 'REC', 'EITH'),
							get_parser=str.rstrip)

		self.add_parameter('transmission_type',
							label='transmission type',
							set_cmd='TRIGger:A:MILStd:TTYPe {}',
							get_cmd='TRIGger:A:MILStd:TTYPe?',
							vals=vals.Enum('BCRT', 'RTBC', 'RTRT', 'MCD'),
							get_parser=str.rstrip)

		self.add_parameter('trigger_type',
							label='trigger mode',
							set_cmd='TRIGger:A:MILStd:TYPE {}',
							get_cmd='TRIGger:A:MILStd:TYPE?',
							vals=vals.Enum('EQU', 'NEQ', 'GTH', 'GEQ', 'LEQ', 'LTH', 'WITH', 'OUTS'),
							get_parser=str.rstrip)

		self.add_parameter('wordcount_condition',
							label='wordcount condition',
							set_cmd='TRIGger:A:MILStd:WCOunt:CONDition {}',
							get_cmd='TRIGger:A:MILStd:WCOunt:CONDition?',
							vals=vals.Enum('EQU', 'NEQ', 'GTH', 'GEQ', 'LEQ', 'LTH', 'WITH', 'OUTS'),
							get_parser=str.rstrip)

		self.add_parameter('wordcount_maximum',
							label='wordcount maximum',
							set_cmd='TRIGger:A:MILStd:WCOunt:MAXimum {}',
							get_cmd='TRIGger:A:MILStd:WCOunt:MAXimum?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('wordcount_minimum',
							label='wordcount minimum',
							set_cmd='TRIGger:A:MILStd:WCOunt:MINimum {}',
							get_cmd='TRIGger:A:MILStd:WCOunt:MINimum?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('word_type',
							label='word type',
							set_cmd='TRIGger:A:MILStd:WORD {}',
							get_cmd='TRIGger:A:MILStd:WORD?',
							vals=vals.Enum('COMM', 'STAT', 'DATA', 'ALL'),
							get_parser=str.rstrip)

class SPI(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, busnum):
		super().__init__(parent, name)

		self.add_parameter('source',
							label=f'bus {busnum} source',
							set_cmd=f'BUS{busnum}:SPI:CS:SOURce {{}}',
							get_cmd=f'BUS{busnum}:SPI:CS:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15'),
							get_parser=str.rstrip)

		self.add_parameter('polarity',
							label=f'bus {busnum} polarity',
							set_cmd=f'BUS{busnum}:SPI:CS:POLarity {{}}',
							get_cmd=f'BUS{busnum}:SPI:CS:POLarity?',
							vals=vals.Enum('POS', 'NEG'),
							get_parser=str.rstrip)

		self.add_parameter('clock_source',
							label=f'bus {busnum} clock source',
							set_cmd=f'BUS{busnum}:SPI:CLOCk:SOURce {{}}',
							get_cmd=f'BUS{busnum}:SPI:CLOCk:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15'),
							get_parser=str.rstrip)

		self.add_parameter('clock_polarity',
							label=f'bus {busnum} clock polarity',
							set_cmd=f'BUS{busnum}:SPI:CLOCk:POLarity {{}}',
							get_cmd=f'BUS{busnum}:SPI:CLOCk:POLarity?',
							vals=vals.Enum('POS', 'NEG'),
							get_parser=str.rstrip)

		self.add_parameter('data_source',
							label=f'bus {busnum} data source',
							set_cmd=f'BUS{busnum}:SPI:DATA:SOURce {{}}',
							get_cmd=f'BUS{busnum}:SPI:DATA:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15'),
							get_parser=str.rstrip)

		self.add_parameter('mosi_source',
							label=f'bus {busnum} mosi source',
							set_cmd=f'BUS{busnum}:SPI:MOSI:SOURce {{}}',
							get_cmd=f'BUS{busnum}:SPI:MOSI:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15'),
							get_parser=str.rstrip)

		self.add_parameter('miso_source',
							label=f'bus {busnum} miso source',
							set_cmd=f'BUS{busnum}:SPI:MISO:SOURce {{}}',
							get_cmd=f'BUS{busnum}:SPI:MISO:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15', 'NONE'),
							get_parser=str.rstrip)

		self.add_parameter('data_polarity',
							label=f'bus {busnum} data polarity',
							set_cmd=f'BUS{busnum}:SPI:DATA:POLarity {{}}',
							get_cmd=f'BUS{busnum}:SPI:DATA:POLarity?',
							vals=vals.Enum('POS', 'NEG'),
							get_parser=str.rstrip)

		self.add_parameter('mosi_polarity',
							label=f'bus {busnum} mosi polarity',
							set_cmd=f'BUS{busnum}:SPI:MOSI:POLarity {{}}',
							get_cmd=f'BUS{busnum}:SPI:MOSI:POLarity?',
							vals=vals.Enum('ACTL', 'ACTH'),
							get_parser=str.rstrip)

		self.add_parameter('miso_polarity',
							label=f'bus {busnum} miso polarity',
							set_cmd=f'BUS{busnum}:SPI:MISO:POLarity {{}}',
							get_cmd=f'BUS{busnum}:SPI:BORDer?',
							vals=vals.Enum('ACTL', 'ACTH'),
							get_parser=str.rstrip)

		self.add_parameter('bit_order',
							label=f'bus {busnum} bit order',
							set_cmd=f'BUS{busnum}:SPI:BORDer {{}}',
							get_cmd=f'BUS{busnum}:SPI:BORDer?',
							vals=vals.Enum('MSBF', 'LSBF'),
							get_parser=str.rstrip)

		self.add_parameter('symbol_size',
							label=f'bus {busnum} symbol size',
							set_cmd=f'BUS{busnum}:SPI:SSIZe {{}}',
							get_cmd=f'BUS{busnum}:SPI:SSIZe?',
							vals=vals.Ints(4,32),
							get_parser=int)

class SPI_Decode(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, busnum, framenum, wordnum):
		super().__init__(parent, name)

		self.add_parameter('count',
							label=f'bus {busnum} count',
							get_cmd=f'BUS{busnum}:SPI:FCOunt?',
							get_parser=int)

		self.add_parameter('status',
							label=f'bus {busnum} frame {framenum} frame status',
							get_cmd=f'BUS{busnum}:SPI:FRAME{framenum}:STATus?',
							get_parser=str.rstrip)

		self.add_parameter('start',
							label=f'bus {busnum} frame {framenum} frame start',
							get_cmd=f'BUS{busnum}:SPI:FRAME{framenum}:STARt?',
							get_parser=float)

		self.add_parameter('stop',
							label=f'bus {busnum} frame {framenum} frame stop',
							get_cmd=f'BUS{busnum}:SPI:FRAME{framenum}:STOP?',
							get_parser=float)

		self.add_parameter('data_mosi',
							label=f'bus {busnum} frame {framenum} mosi data',
							get_cmd=f'BUS{busnum}:SPI:FRAME{framenum}:DATA:MISO?',
							get_parser=str.rstrip)

		self.add_parameter('word_count',
							label=f'bus {busnum} frame {framenum} word count',
							get_cmd=f'BUS{busnum}:SPI:FRAME{framenum}:WCOunt?',
							get_parser=int)

		self.add_parameter('word_start',
							label=f'bus {busnum} frame {framenum} word {wordnum} word start time',
							get_cmd=f'BUS{busnum}:SPI:FRAME{framenum}:WORD{wordnum}:STARt?',
							get_parser=str.rstrip)

		self.add_parameter('word_stop',
							label=f'bus {busnum} frame {framenum} word {wordnum} stop time',
							get_cmd=f'BUS{busnum}:SPI:FRAME{framenum}:WORD{wordnum}:STOP?',
							get_parser=str.rstrip)

		self.add_parameter('mosi_word',
							label=f'bus {busnum} frame {framenum} word {wordnum} mosi word',
							get_cmd=f'BUS{busnum}:SPI:FRAME{framenum}:WORD{wordnum}:MOSI?',
							get_parser=float)

		self.add_parameter('miso_word',
							label=f'bus {busnum} frame {framenum} word {wordnum} miso word',
							get_cmd=f'BUS{busnum}:SPI:FRAME{framenum}:WORD{wordnum}:MISO?',
							get_parser=float)

class SPI_Trigger(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('source',
							label='trigger spi source',
							set_cmd='TRIGger:A:SOURce:SPI {}',
							get_cmd='TRIGger:A:SOURce:SPI?',
							vals=vals.Enum('MISO', 'MOSI'),
							get_parser=str.rstrip)

		self.add_parameter('mode',
							label='trigger spi mode',
							set_cmd='TRIGger:A:SPI:MODE {}',
							get_cmd='TRIGger:A:SPI:MODE?',
							vals=vals.Enum('BST', 'BEND', 'NTHB', 'PATT'),
							get_parser=str.rstrip)

		self.add_parameter('data_pattern',
							label='trigger spi data pattern',
							set_cmd='TRIGger:A:SPI:PATTern {}',
							get_cmd='TRIGger:A:SPI:PATTern?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('pattern_length',
							label='trigger spi pattern length',
							set_cmd='TRIGger:A:SPI:PLENgth {}',
							get_cmd='TRIGger:A:SPI:PLENgth?',
							vals=vals.Ints(1,32),
							get_parser=int)

		self.add_parameter('bit_offset',
							label='trigger spi pattern bit offset',
							set_cmd='TRIGger:A:SPI:POFFset {}',
							get_cmd='TRIGger:A:SPI:POFFset?',
							vals=vals.Ints(0,4095),
							get_parser=int)

class SSPI(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, busnum):
		super().__init__(parent, name)

		self.add_parameter('clock_source',
							label=f'bus {busnum} clock source',
							set_cmd=f'BUS{busnum}:SSPI:CLOCk:SOURce {{}}',
							get_cmd=f'BUS{busnum}:SSPI:CLOCk:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15'),
							get_parser=str.rstrip)

		self.add_parameter('clock_polarity',
							label=f'bus {busnum} clock polarity',
							set_cmd=f'BUS{busnum}:SSPI:CLOCk:POLarity {{}}',
							get_cmd=f'BUS{busnum}:SSPI:CLOCk:POLarity?',
							vals=vals.Enum('POS', 'NEG'),
							get_parser=str.rstrip)

		self.add_parameter('data_source',
							label=f'bus {busnum} data source',
							set_cmd=f'BUS{busnum}:SSPI:DATA:SOURce {{}}',
							get_cmd=f'BUS{busnum}:SSPI:DATA:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15'),
							get_parser=str.rstrip)

		self.add_parameter('mosi_source',
							label=f'bus {busnum} mosi source',
							set_cmd=f'BUS{busnum}:SSPI:MOSI:SOURce {{}}',
							get_cmd=f'BUS{busnum}:SSPI:MOSI:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15'),
							get_parser=str.rstrip)

		self.add_parameter('miso_source',
							label=f'bus {busnum} miso source',
							set_cmd=f'BUS{busnum}:SSPI:MISO:SOURce {{}}',
							get_cmd=f'BUS{busnum}:SSPI:MISO:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15', 'NONE'),
							get_parser=str.rstrip)

		self.add_parameter('data_polarity',
							label=f'bus {busnum} data polarity',
							set_cmd=f'BUS{busnum}:SSPI:DATA:POLarity {{}}',
							get_cmd=f'BUS{busnum}:SSPI:DATA:POLarity?',
							vals=vals.Enum('POS', 'NEG'),
							get_parser=str.rstrip)

		self.add_parameter('mosi_polarity',
							label=f'bus {busnum} mosi polarity',
							set_cmd=f'BUS{busnum}:SSPI:MOSI:POLarity {{}}',
							get_cmd=f'BUS{busnum}:SSPI:MOSI:POLarity?',
							vals=vals.Enum('ACTL', 'ACTH'),
							get_parser=str.rstrip)

		self.add_parameter('miso_polarity',
							label=f'bus {busnum} miso polarity',
							set_cmd=f'BUS{busnum}:SSPI:MISO:POLarity {{}}',
							get_cmd=f'BUS{busnum}:SSPI:MISO:POLarity?',
							vals=vals.Enum('ACTL', 'ACTH'),
							get_parser=str.rstrip)

		self.add_parameter('burst_idle',
							label=f'bus {busnum} burst idle time',
							set_cmd=f'BUS{busnum}:SSPI:BITime {{}}',
							get_cmd=f'BUS{busnum}:SSPI:BITime?',
							vals=vals.Numbers(16e-9,838.832e-6),
							get_parser=float)

		self.add_parameter('bit_order',
							label=f'bus {busnum} bit order',
							set_cmd=f'BUS{busnum}:SSPI:BORDer {{}}',
							get_cmd=f'BUS{busnum}:SSPI:BORDer?',
							vals=vals.Enum('MSBF', 'LSBF'),
							get_parser=str.rstrip)

		self.add_parameter('symbol_size',
							label=f'bus {busnum} symbol size',
							set_cmd=f'BUS{busnum}:SSPI:SSIZe {{}}',
							get_cmd=f'BUS{busnum}:SSPI:SSIZe?',
							vals=vals.Ints(4,32),
							get_parser=int)

class UART(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, busnum):
		super().__init__(parent, name)

		self.add_parameter('rx_source',
							label=f'bus {busnum} rx source',
							set_cmd=f'BUS{busnum}:UART:RX:SOURce {{}}',
							get_cmd=f'BUS{busnum}:UART:RX:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15'),
							get_parser=str.rstrip)

		self.add_parameter('data_source',
							label=f'bus {busnum} data source',
							set_cmd=f'BUS{busnum}:UART:DATA:SOURce {{}}',
							get_cmd=f'BUS{busnum}:UART:DATA:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15'),
							get_parser=str.rstrip)

		self.add_parameter('tx_source',
							label=f'bus {busnum} tx source',
							set_cmd=f'BUS{busnum}:UART:TX:SOURce {{}}',
							get_cmd=f'BUS{busnum}:UART:TX:SOURce?',
							vals=vals.Enum('NONE', 'CH1', 'CH2', 'CH3', 'CH4', 'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15'),
							get_parser=str.rstrip)

		self.add_parameter('polarity',
							label=f'bus {busnum} polarity',
							set_cmd=f'BUS{busnum}:UART:POLarity {{}}',
							get_cmd=f'BUS{busnum}:UART:POLarity?',
							vals=vals.Enum('IDLL', 'IDLH'),
							get_parser=str.rstrip)

		self.add_parameter('data_polarity',
							label=f'bus {busnum} data polarity',
							set_cmd=f'BUS{busnum}:UART:DATA:POLarity {{}}',
							get_cmd=f'BUS{busnum}:UART:DATA:POLarity?',
							vals=vals.Enum('POS', 'NEG'),
							get_parser=str.rstrip)

		self.add_parameter('symbol_size',
							label=f'bus {busnum} symbol size',
							set_cmd=f'BUS{busnum}:UART:SSIZe {{}}',
							get_cmd=f'BUS{busnum}:UART:SSIZe?',
							vals=vals.Ints(5,9),
							get_parser=int)

		self.add_parameter('parity',
							label=f'bus {busnum} parity',
							set_cmd=f'BUS{busnum}:UART:PARity {{}}',
							get_cmd=f'BUS{busnum}:UART:PARity?',
							vals=vals.Enum('ODD', 'EVEN', 'NONE'),
							get_parser=str.rstrip)

		self.add_parameter('stop_bit',
							label=f'bus {busnum} stop bit number',
							set_cmd=f'BUS{busnum}:UART:SBIT {{}}',
							get_cmd=f'BUS{busnum}:UART:SBIT?',
							vals=vals.Enum('B1', 'B1_5', 'B2'),
							get_parser=str.rstrip)

		self.add_parameter('baudrate',
							label=f'bus {busnum} baudrate',
							set_cmd=f'BUS{busnum}:UART:BAUDrate {{}}',
							get_cmd=f'BUS{busnum}:UART:BAUDrate?',
							vals=vals.Numbers(100,78.1e6),
							get_parser=float)

		self.add_parameter('idle_time',
							label=f'bus {busnum} burst idle time',
							set_cmd=f'BUS{busnum}:UART:BITime {{}}',
							get_cmd=f'BUS{busnum}:UART:BITime?',
							vals=vals.Numbers(),
							get_parser=float)

class UART_Decode(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, busnum, framenum, wordnum):
		super().__init__(parent, name)

		self.add_parameter('count',
							label=f'bus {busnum} count',
							get_cmd=f'BUS{busnum}:UART:FCOunt?',
							get_parser=str.rstrip)

		self.add_parameter('rx_count',
							label=f'bus {busnum} rx count',
							get_cmd=f'BUS{busnum}:UART:RX:FCOunt?',
							get_parser=str.rstrip)

		self.add_parameter('tx_count',
							label=f'bus {busnum} tx count',
							get_cmd=f'BUS{busnum}:UART:TX:FCOunt?',
							get_parser=str.rstrip)

		self.add_parameter('start',
							label=f'bus {busnum} frame {framenum} start',
							get_cmd=f'BUS{busnum}:UART:FRAMe{framenum}:STARt?',
							get_parser=str.rstrip)

		self.add_parameter('rx_start',
							label=f'bus {busnum} frame {framenum} rx start',
							get_cmd=f'BUS{busnum}:UART:RX:FRAMe{framenum}:STARt?',
							get_parser=str.rstrip)

		self.add_parameter('tx_start',
							label=f'bus {busnum} frame {framenum} tx start',
							get_cmd=f'BUS{busnum}:UART:TX:FRAMe{framenum}:STARt?',
							get_parser=str.rstrip)

		self.add_parameter('stop',
							label=f'bus {busnum} frame {framenum} stop',
							get_cmd=f'BUS{busnum}:UART:FRAMe{framenum}:STOP?',
							get_parser=str.rstrip)

		self.add_parameter('rx_stop',
							label=f'bus {busnum} frame {framenum} rx stop',
							get_cmd=f'BUS{busnum}:UART:RX:FRAMe{framenum}:STOP?',
							get_parser=str.rstrip)

		self.add_parameter('tx_stop',
							label=f'bus {busnum} frame {framenum} tx stop',
							get_cmd=f'BUS{busnum}:UART:TX:FRAMe{framenum}:STOP?',
							get_parser=str.rstrip)

		self.add_parameter('state',
							label=f'bus {busnum} frame {framenum} state',
							get_cmd=f'BUS{busnum}:UART:FRAMe{framenum}:STATe?',
							get_parser=str.rstrip)

		self.add_parameter('rx_state',
							label=f'bus {busnum} frame {framenum} rx state',
							get_cmd=f'BUS{busnum}:UART:RX:FRAMe{framenum}:STATe?',
							get_parser=str.rstrip)

		self.add_parameter('tx_state',
							label=f'bus {busnum} frame {framenum} tx state',
							get_cmd=f'BUS{busnum}:UART:TX:FRAMe{framenum}:STATe?',
							get_parser=str.rstrip)

		self.add_parameter('word_count',
							label=f'bus {busnum} frame {framenum} word count',
							get_cmd=f'BUS{busnum}:UART:FRAMe{framenum}:WCOunt?',
							get_parser=str.rstrip)

		self.add_parameter('rx_word_count',
							label=f'bus {busnum} frame {framenum} rx word count',
							get_cmd=f'BUS{busnum}:UART:RX:FRAMe{framenum}:WCOunt?',
							get_parser=str.rstrip)

		self.add_parameter('tx_word_count',
							label=f'bus {busnum} frame {framenum} tx word count',
							get_cmd=f'BUS{busnum}:UART:TX:FRAMe{framenum}:WCOunt?',
							get_parser=str.rstrip)

		self.add_parameter('word_source',
							label=f'bus {busnum} frame {framenum} word {wordnum} word source',
							get_cmd=f'BUS{busnum}:UART:FRAMe{framenum}:WORD{wordnum}:SOURce?',
							get_parser=str.rstrip)

		self.add_parameter('word_state',
							label=f'bus {busnum} frame {framenum} word {wordnum} word state',
							get_cmd=f'BUS{busnum}:UART:FRAMe{framenum}:WORD{wordnum}:STATe?',
							get_parser=str.rstrip)

		self.add_parameter('rx_word_state',
							label=f'bus {busnum} frame {framenum} word {wordnum} rx word state',
							get_cmd=f'BUS{busnum}:UART:RX:FRAMe{framenum}:WORD{wordnum}:STATe?',
							get_parser=str.rstrip)

		self.add_parameter('tx_word_state',
							label=f'bus {busnum} frame {framenum} word {wordnum} tx word state',
							get_cmd=f'BUS{busnum}:UART:TX:FRAMe{framenum}:WORD{wordnum}:STATe?',
							get_parser=str.rstrip)

		self.add_parameter('word_start',
							label=f'bus {busnum} frame {framenum} word {wordnum} word start',
							get_cmd=f'BUS{busnum}:UART:FRAMe{framenum}:WORD{wordnum}:STARt?',
							get_parser=str.rstrip)

		self.add_parameter('rx_word_start',
							label=f'bus {busnum} frame {framenum} word {wordnum} rx word start',
							get_cmd=f'BUS{busnum}:UART:RX:FRAMe{framenum}:WORD{wordnum}:STARt?',
							get_parser=str.rstrip)

		self.add_parameter('tx_word_start',
							label=f'bus {busnum} frame {framenum} word {wordnum} tx word start',
							get_cmd=f'BUS{busnum}:UART:TX:FRAMe{framenum}:WORD{wordnum}:STARt?',
							get_parser=str.rstrip)

		self.add_parameter('word_stop',
							label=f'bus {busnum} frame {framenum} word {wordnum} word stop',
							get_cmd=f'BUS{busnum}:UART:FRAMe{framenum}:WORD{wordnum}:STOP?',
							get_parser=str.rstrip)

		self.add_parameter('rx_word_stop',
							label=f'bus {busnum} frame {framenum} word {wordnum} rx word stop',
							get_cmd=f'BUS{busnum}:UART:RX:FRAMe{framenum}:WORD{wordnum}:STOP?',
							get_parser=str.rstrip)

		self.add_parameter('tx_word_stop',
							label=f'bus {busnum} frame {framenum} word {wordnum} tx word stop',
							get_cmd=f'BUS{busnum}:UART:TX:FRAMe{framenum}:WORD{wordnum}:STOP?',
							get_parser=str.rstrip)

		self.add_parameter('word_value',
							label=f'bus {busnum} frame {framenum} word {wordnum} word value',
							get_cmd=f'BUS{busnum}:UART:FRAMe{framenum}:WORD{wordnum}:VALue?',
							get_parser=int)

		self.add_parameter('word_rx_value',
							label=f'bus {busnum} frame {framenum} word {wordnum} rx word value',
							get_cmd=f'BUS{busnum}:UART:FRAMe{framenum}:WORD{wordnum}:RXValue?',
							get_parser=int)

		self.add_parameter('word_tx_value',
							label=f'bus {busnum} frame {framenum} word {wordnum} tx word value',
							get_cmd=f'BUS{busnum}:UART:FRAMe{framenum}:WORD{wordnum}:TXValue?',
							get_parser=int)

		self.add_parameter('rx_word_value',
							label=f'bus {busnum} frame {framenum} word {wordnum} rx word value',
							get_cmd=f'BUS{busnum}:UART:RX:FRAMe{framenum}:WORD{wordnum}:VALue?',
							get_parser=int)

		self.add_parameter('tx_word_value',
							label=f'bus {busnum} frame {framenum} word {wordnum} tx word value',
							get_cmd=f'BUS{busnum}:UART:TX:FRAMe{framenum}:WORD{wordnum}:VALue?',
							get_parser=int)

class UART_Trigger(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('source',
							label='uart source',
							set_cmd='TRIGger:A:SOURce:UART {}',
							get_cmd='TRIGger:A:SOURce:UART?',
							vals=vals.Enum('RX', 'TX'),
							get_parser=str.rstrip)

		self.add_parameter('mode',
							label='uart mode',
							set_cmd='TRIGger:A:UART:MODE {}',
							get_cmd='TRIGger:A:UART:MODE?',
							vals=vals.Enum('BST', 'SBIT', 'NTHS', 'SYMB', 'PATT', 'PRER', 'SPER', 'BRE'),
							get_parser=str.rstrip)

		self.add_parameter('data_pattern',
							label='uart data pattern',
							set_cmd='TRIGger:A:UART:PATTern {}',
							get_cmd='TRIGger:A:UART:PATTern?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('pattern_length',
							label='uart pattern length',
							set_cmd='TRIGger:A:UART:PLENgth {}',
							get_cmd='TRIGger:A:UART:PLENgth?',
							vals=vals.Ints(1,4),
							get_parser=int)

		self.add_parameter('pattern_offset',
							label='uart pattern byte offset',
							set_cmd='TRIGger:A:UART:POFFset {}',
							get_cmd='TRIGger:A:UART:POFFset?',
							vals=vals.Ints(0,4095),
							get_parser=int)

# Power analysis

class Power_Analysis_Channel(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		power_report_module=Power_Report(self, 'power_report')
		self.add_submodule('power_report', power_report_module)

		power_consumption_module=Power_Consumption(self, 'power_consumption')
		self.add_submodule('power_consumption', power_consumption_module)

		power_efficiency_module=Power_Efficiency(self, 'power_efficiency')
		self.add_submodule('power_efficiency', power_efficiency_module)

		power_modulation_module=Power_Modulation(self, 'power_modulation')
		self.add_submodule('power_modulation', power_modulation_module)

		power_quality_average_module=Power_Quality_Average(self, 'power_quality_average')
		self.add_submodule('power_quality_average', power_quality_average_module)

		power_quality_negative_module=Power_Quality_Negative(self, 'power_quality_negative')
		self.add_submodule('power_quality_negative', power_quality_negative_module)

		power_quality_positive_module=Power_Quality_Positive(self, 'power_quality_positive')
		self.add_submodule('power_quality_positive', power_quality_positive_module)

		power_quality_deviation_module=Power_Quality_Deviation(self, 'power_quality_deviation')
		self.add_submodule('power_quality_deviation', power_quality_deviation_module)

		power_quality_waveform_module=Power_Quality_Waveform(self, 'power_quality_waveform')
		self.add_submodule('power_quality_waveform', power_quality_waveform_module)

		power_quality_actual_module=Power_Quality_Actual(self, 'power_quality_actual')
		self.add_submodule('power_quality_actual', power_quality_actual_module)

		power_ripple_frequency_module=Power_Ripple_Frequency(self, 'power_ripple_frequency')
		self.add_submodule('power_ripple_frequency', power_ripple_frequency_module)

		power_ripple_lpeak_module=Power_Ripple_Lpeak(self, 'power_ripple_lpeak')
		self.add_submodule('power_ripple_lpeak', power_ripple_lpeak_module)

		power_ripple_upeak_module=Power_Ripple_Upeak(self, 'power_ripple_upeak')
		self.add_submodule('power_ripple_upeak', power_ripple_upeak_module)

		power_ripple_mean_module=Power_Ripple_Mean(self, 'power_ripple_mean')
		self.add_submodule('power_ripple_mean', power_ripple_mean_module)

		power_ripple_nduty_module=Power_Ripple_Nduty(self, 'power_ripple_nduty')
		self.add_submodule('power_ripple_nduty', power_ripple_nduty_module)

		power_ripple_pduty_module=Power_Ripple_Pduty(self, 'power_ripple_pduty')
		self.add_submodule('power_ripple_pduty', power_ripple_pduty_module)

		power_ripple_peak_module=Power_Ripple_Peak(self, 'power_ripple_peak')
		self.add_submodule('power_ripple_peak', power_ripple_peak_module)

		power_ripple_period_module=Power_Ripple_Period(self, 'power_ripple_period')
		self.add_submodule('power_ripple_period', power_ripple_period_module)

		slew_rate_module=Slew_Rate(self, 'slew_rate')
		self.add_submodule('slew_rate', slew_rate_module)

		ripple_result_frequency_module=Ripple_Result_Frequency(self, 'ripple_result_frequency')
		self.add_submodule('ripple_result_frequency', ripple_result_frequency_module)

		slewrate_lpeak_module=Slewrate_Lpeak(self, 'slewrate_lpeak')
		self.add_submodule('slewrate_lpeak', slewrate_lpeak_module)

		ripple_result_mean_module=Ripple_Result_Mean(self, 'ripple_result_mean')
		self.add_submodule('ripple_result_mean', ripple_result_mean_module)

		ripple_result_nduty_module=Ripple_Result_Nduty(self, 'ripple_result_nduty')
		self.add_submodule('ripple_result_nduty', ripple_result_nduty_module)

		ripple_result_pduty_module=Ripple_Result_Pduty(self, 'ripple_result_pduty')
		self.add_submodule('ripple_result_pduty', ripple_result_pduty_module)

		ripple_result_peak_module=Ripple_Result_Peak(self, 'ripple_result_peak')
		self.add_submodule('ripple_result_peak', ripple_result_peak_module)

		ripple_result_period_module=Ripple_Result_Period(self, 'ripple_result_period')
		self.add_submodule('ripple_result_period', ripple_result_period_module)

		ripple_result_deviation_module=Ripple_Result_Deviation(self, 'ripple_result_deviation')
		self.add_submodule('ripple_result_deviation', ripple_result_deviation_module)

		slewrate_upeak_module=Slewrate_Upeak(self, 'slewrate_upeak')
		self.add_submodule('slewrate_upeak', slewrate_upeak_module)

		switching_module=Switching(self, 'switching')
		self.add_submodule('switching', switching_module)

		transient_module=Transient(self, 'transient')
		self.add_submodule('transient', transient_module)

		for i in range(1,4+1):
			power_general_module=Power_General(self, f'power_so{i}', i)
			self.add_submodule(f'power_so{i}', power_general_module)

		for i in range(1,2+1):
			power_dynamic_module=Power_Dynamic(self, f'dyn_gt{i}', i)
			self.add_submodule(f'dyn_gt{i}', power_dynamic_module)

			power_inrush_module=Power_Inrush(self, f'inr_gt{i}', i)
			self.add_submodule(f'inr_gt{i}', power_inrush_module)

			power_state_module=Power_State(self, f'state_gt{i}', i)
			self.add_submodule(f'state_gt{i}', power_state_module)

		for i in range(1,40+1):
			power_harmonics_module=Power_Harmonics(self, f'power_hm{i}', i)
			self.add_submodule(f'power_hm{i}', power_harmonics_module)

			spectrum_module=Spectrum(self, f'spec_hm{i}', i)
			self.add_submodule(f'spec_hm{i}', spectrum_module)

		for i in range(1,50+1):
			soa_module=SOA(self, f'soa_pn{i}', i)
			self.add_submodule(f'soa_pn{i}', soa_module)

class Power_Consumption(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('execute',
							label='execute',
							set_cmd='POWer:CONSumption:EXECute {}',
							val_mapping={'ON':1,'OFF':0})

		self.add_parameter('result_apparent',
							label='apparent result',
							get_cmd='POWer:CONSumption:RESult:APParent?',
							get_parser=str.rstrip)

		self.add_parameter('result_duration',
							label='result duration',
							get_cmd='POWer:CONSumption:RESult:DURation?',
							get_parser=float)

		self.add_parameter('result_energy',
							label='result energy',
							get_cmd='POWer:CONSumption:RESult:ENERgy?',
							get_parser=str.rstrip)

		self.add_parameter('power_factor',
							label='power factor result',
							get_cmd='POWer:CONSumption:RESult:PFACtor?',
							get_parser=float)

		self.add_parameter('result_phase',
							label='phase result',
							get_cmd='POWer:CONSumption:RESult:PHASe?',
							get_parser=str.rstrip)

		self.add_parameter('result_reactive',
							label='reactive result',
							get_cmd='POWer:CONSumption:RESult:REACtive?',
							get_parser=str.rstrip)

		self.add_parameter('real_power',
							label='real power result',
							get_cmd='POWer:CONSumption:RESult:REALpower?',
							get_parser=str.rstrip)

	def report_add(self): self.write('POWer:CONSumption:REPort:ADD')
	def restart(self): self.write('POWer:CONSumption:RESTart')

class Power_Dynamic(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, gatnum):
		super().__init__(parent, name)

		self.add_parameter('start',
							label=f'gate {gatnum} start',
							set_cmd=f'POWer:DONResistance:GATE{gatnum}:START {{}}',
							get_cmd=f'POWer:DONResistance:GATE{gatnum}:START?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('stop',
							label=f'gate {gatnum} stop',
							set_cmd=f'POWer:DONResistance:GATE{gatnum}STOP {{}}',
							get_cmd=f'POWer:DONResistance:GATE{gatnum}STOP?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('resistance',
							label='resistance',
							get_cmd='POWer:DONResistance:RESult:DONResistance?',
							get_parser=str.rstrip)

	def execute(self): self.write('POWer:DONResistance:EXECute')
	def add(self): self.write('POWer:DONResistance:REPort:ADD')

class Power_Efficiency(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('efficiency',
							label='efficiency',
							get_cmd='POWer:EFFiciency:RESult:EFFiciency:ACTual?',
							get_parser=float)

		self.add_parameter('average',
							label='average efficiency',
							get_cmd='POWer:EFFiciency:RESult:EFFiciency:AVG?',
							get_parser=float)

		self.add_parameter('negative',
							label='negative peak efficiency',
							get_cmd='POWer:EFFiciency:RESult:EFFiciency:NPEak?',
							get_parser=float)

		self.add_parameter('positive',
							label='positive peak efficiency',
							get_cmd='POWer:EFFiciency:RESult:EFFiciency:PPEak?',
							get_parser=float)

		self.add_parameter('standard_deviation',
							label='standard deviation efficiency',
							get_cmd='POWer:EFFiciency:RESult:EFFiciency:STDDev?',
							get_parser=float)

		self.add_parameter('waveform',
							label='waveform count',
							get_cmd='POWer:EFFiciency:RESult:EFFiciency:WFMCount?',
							get_parser=float)

		self.add_parameter('input',
							label='input',
							get_cmd='POWer:EFFiciency:RESult:INPut:REALpower:ACTual?',
							get_parser=float)

		self.add_parameter('input_average',
							label='average input',
							get_cmd='POWer:EFFiciency:RESult:INPut:REALpower:AVG?',
							get_parser=float)

		self.add_parameter('input_negative',
							label='negative peak input',
							get_cmd='POWer:EFFiciency:RESult:INPut:REALpower:NPEak?',
							get_parser=float)

		self.add_parameter('input_positive',
							label='positive peak input',
							get_cmd='POWer:EFFiciency:RESult:INPut:REALpower:PPEak?',
							get_parser=float)

		self.add_parameter('input_deviation',
							label='standard deviation input',
							get_cmd='POWer:EFFiciency:RESult:INPut:REALpower:STDDev?',
							get_parser=float)

		self.add_parameter('input_waveform',
							label='waveform count',
							get_cmd='POWer:EFFiciency:RESult:INPut:REALpower:WFMCount?',
							get_parser=float)

		self.add_parameter('output',
							label='output',
							get_cmd='POWer:EFFiciency:RESult:OUTPut:REALpower:ACTual?',
							get_parser=float)

		self.add_parameter('output_average',
							label='average output',
							get_cmd='POWer:EFFiciency:RESult:OUTPut:REALpower:AVG?',
							get_parser=float)

		self.add_parameter('output_negative',
							label='negative peak output',
							get_cmd='POWer:EFFiciency:RESult:OUTPut:REALpower:NPEak?',
							get_parser=float)

		self.add_parameter('output_positive',
							label='positive peak output',
							get_cmd='POWer:EFFiciency:RESult:OUTPut:REALpower:PPEak?',
							get_parser=float)

		self.add_parameter('output_deviation',
							label='standard deviation output',
							get_cmd='POWer:EFFiciency:RESult:OUTPut:REALpower:STDDev?',
							get_parser=float)

		self.add_parameter('output_waveform',
							label='waveform count',
							get_cmd='POWer:EFFiciency:RESult:OUTPut:REALpower:WFMCount?',
							get_parser=float)

	def execute(self): self.write('POWer:EFFiciency:EXECute')
	def add(self): self.write('POWer:EFFiciency:REPort:ADD')

class Power_General(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, sonum):
		super().__init__(parent, name)

		self.add_parameter('type',
							label='type',
							set_cmd='POWer:ATYPe {}',
							get_cmd='POWer:ATYPe?',
							vals=vals.Enum('OFF', 'QUAL', 'CONS', 'HARMINR', 'RIPP', 'SPECSWIT', 'SLEWMOD', 'DONR', 'EFFSWIT', 'TURN', 'TRAN'),
							get_parser=str.rstrip)

		self.add_parameter('enable',
							label='enable',
							set_cmd='POWer:ENABle {}',
							get_cmd='POWer:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('result_table',
							label='result table',
							set_cmd='POWer:RESult:TABLe {}',
							get_cmd='POWer:RESult:TABLe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('source_current',
							label=f'source {sonum} current',
							set_cmd=f'POWer:SOURce:CURRent{sonum} {{}}',
							get_cmd=f'POWer:SOURce:CURRent{sonum}?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'RE1', 'RE2', 'RE3', 'RE4'),
							get_parser=str.rstrip)

		self.add_parameter('source_voltage',
							label=f'source {sonum} voltage',
							set_cmd=f'POWer:SOURce:VOLTage{sonum} {{}}',
							get_cmd=f'POWer:SOURce:VOLTage{sonum}?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4', 'RE1', 'RE2', 'RE3', 'RE4'),
							get_parser=str.rstrip)

		self.add_parameter('visible',
							label='visible',
							set_cmd='POWer:STATistics:VISible {}',
							get_cmd='POWer:STATistics:VISible?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)
							
	def autoscale(self): self.write('POWer:AUToscale')
	def auto_current(self): self.write('POWer:AUToscale:CURRent')
	def auto_voltage(self): self.write('POWer:AUToscale:VOLTage')
	def reset(self): self.write('POWer:STATistics:RESet')
	def deskew(self): self.write('POWer:DESKew:EXECute')
	def zero(self): self.write('POWer:ZOFFset:EXECute')

class Power_Harmonics(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, harmnum):
		super().__init__(parent, name)

		self.add_parameter('available',
							label='available harmonics',
							get_cmd='POWer:HARMonics:AVAilable?',
							get_parser=int)

		self.add_parameter('do_frequency',
							label='do frequency',
							set_cmd='POWer:HARMonics:DOFRequency {}',
							get_cmd='POWer:HARMonics:DOFRequency?',
							vals=vals.Enum('F400', 'NVF', 'WVF'),
							get_parser=str.rstrip)

		self.add_parameter('EN_frequency',
							label='EN frequency',
							set_cmd='POWer:HARMonics:ENFRequency {}',
							get_cmd='POWer:HARMonics:ENFRequency?',
							vals=vals.Enum('AUTO', 'F50', 'F60'),
							get_parser=str.rstrip)

		self.add_parameter('duration',
							label='measurement duration',
							get_cmd='POWer:HARMonics:MEASurement:DURation?',
							get_parser=float)

		self.add_parameter('frequency_average',
							label='frequency average measurement',
							get_cmd='POWer:HARMonics:MEASurement:FREQuency:AVG?',
							get_parser=float)

		self.add_parameter('frequency_negative',
							label='minimum frequency',
							get_cmd='POWer:HARMonics:MEASurement:FREQuency:NPEak?',
							get_parser=float)

		self.add_parameter('frequency_positive',
							label='maximum frequency',
							get_cmd='POWer:HARMonics:MEASurement:FREQuency:PPeak?',
							get_parser=float)

		self.add_parameter('frequency_deviation',
							label='standard deviation frequency',
							get_cmd='POWer:HARMonics:MEASurement:FREQuency:STDDev?',
							get_parser=float)

		self.add_parameter('frequency',
							label='frequency value',
							get_cmd='POWer:HARMonics:MEASurement:FREQuency:ACTual?',
							get_parser=float)

		self.add_parameter('total_power',
							label='total power',
							get_cmd='POWer:HARMonics:MEASurement:REALpower:ACTual?',
							get_parser=float)

		self.add_parameter('harmonic_average',
							label='average harmonic distortion',
							get_cmd='POWer:HARMonics:MEASurement:THDistortion:AVG?',
							get_parser=float)

		self.add_parameter('harmonic_negative',
							label='minimum harmonic distortion',
							get_cmd='POWer:HARMonics:MEASurement:THDistortion:NPEak?',
							get_parser=float)

		self.add_parameter('harmonic_positive',
							label='maximum harmonic distortion',
							get_cmd='POWer:HARMonics:MEASurement:THDistortion:PPeak?',
							get_parser=float)

		self.add_parameter('harmonic_deviation',
							label='harmonic distortion deviation',
							get_cmd='POWer:HARMonics:MEASurement:THDistortion:STDDev?',
							get_parser=float)

		self.add_parameter('harmonic_distrortion',
							label='harmonic distortion value',
							get_cmd='POWer:HARMonics:MEASurement:THDistortion:ACTual?',
							get_parser=float)

		self.add_parameter('mil_frequency',
							label='mil frequency',
							set_cmd='POWer:HARMonics:MIFRequency {}',
							get_cmd='POWer:HARMonics:MIFRequency?',
							vals=vals.Enum('F60', 'F400'),
							get_parser=str.rstrip)

		self.add_parameter('frequency_harmonic',
							label=f'harmonic {harmnum} frequency',
							get_cmd=f'POWer:HARMonics:RESult{harmnum}:FREQency?',
							get_parser=float)

		self.add_parameter('limit_level',
							label=f'harmonic {harmnum} limit level',
							get_cmd=f'POWer:HARMonics:RESult{harmnum}:LEVel:LIMit?',
							get_parser=float)

		self.add_parameter('harmonic_level',
							label=f'harmonic {harmnum} level',
							get_cmd=f'POWer:HARMonics:RESult{harmnum}:LEVel:VALue?',
							get_parser=float)

		self.add_parameter('maximum_level',
							label=f'harmonic {harmnum} maximum level',
							get_cmd=f'POWer:HARMonics:RESult{harmnum}:MAXimum?',
							get_parser=float)

		self.add_parameter('average_level',
							label=f'harmonic {harmnum} average level',
							get_cmd=f'POWer:HARMonics:RESult{harmnum}:MEAN?',
							get_parser=float)

		self.add_parameter('minimum_level',
							label=f'harmonic {harmnum} minimum level',
							get_cmd=f'POWer:HARMonics:RESult{harmnum}:MINimum?',
							get_parser=float)

		self.add_parameter('valid',
							label=f'harmonic {harmnum} valid',
							get_cmd=f'POWer:HARMonics:RESult{harmnum}:VALid?',
							get_parser=str.rstrip)

		self.add_parameter('violate',
							label=f'harmonic {harmnum} violate',
							get_cmd=f'POWer:HARMonics:RESult{harmnum}:VCOunt?',
							get_parser=float)

		self.add_parameter('waveform_count',
							label=f'harmonic {harmnum} waveform count',
							get_cmd=f'POWer:HARMonics:RESult{harmnum}:WFMCount?',
							get_parser=float)

		self.add_parameter('standard',
							label='standard',
							set_cmd='POWer:HARMonics:STANdard {}',
							get_cmd='POWer:HARMonics:STANdard?',
							vals=vals.Enum('ENA', 'ENB', 'ENC', 'END', 'MIL', 'RTC'),
							get_parser=str.rstrip)

		self.add_parameter('export_path',
							label='export path',
							set_cmd='EXPort:POWer:NAME {}',
							get_cmd='EXPort:POWer:NAME?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

	def add(self): self.write('POWer:HARMonics:REPort:ADD')
	def reset(self): self.write(f'POWer:HARMonics:RESult{harmnum}:RESet')
	def execute(self): self.write('POWer:HARMonics:EXECute')
	def save(self): self.write('EXPort:POWer:SAVE')

class Power_Inrush(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, gatnum):
		super().__init__(parent, name)

		self.add_parameter('start_time',
							label=f'gate {gatnum} start time',
							set_cmd=f'POWer:INRushcurrent:GATE{gatnum}:STARt {{}}',
							get_cmd=f'POWer:INRushcurrent:GATE{gatnum}:STARt?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('stop_time',
							label=f'gate {gatnum} stop time',
							set_cmd=f'POWer:INRushcurrent:GATE{gatnum}:STOP {{}}',
							get_cmd=f'POWer:INRushcurrent:GATE{gatnum}:STOP?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('gate_count',
							label='gate count',
							set_cmd='POWer:INRushcurrent:GCOunt {}',
							get_cmd='POWer:INRushcurrent:GCOunt?',
							get_parser=int)

		self.add_parameter('area',
							label=f'gate {gatnum} area',
							get_cmd=f'POWer:INRushcurrent:RESult{gatnum}:AREA?',
							get_parser=float)

		self.add_parameter('maximum_current',
							label=f'gate {gatnum} maximum current',
							get_cmd=f'POWer:INRushcurrent:RESult{gatnum}:MAXCurrent?',
							get_parser=float)

	def execute(self): self.write('POWer:INRushcurrent:EXECute')
	def add(self): self.write('POWer:INRushcurrent:REPort:ADD')

class Power_Modulation(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('type',
							label='modulation type',
							set_cmd='POWer:MODulation:TYPE {}',
							get_cmd='POWer:MODulation:TYPE?',
							vals=vals.Enum('PER', 'FREQ', 'DCYC', 'PWID', 'UPER', 'UFR', 'UDCY', 'UPW', 'BPER', 'BFR', 'BDCY', 'BPW'),
							get_parser=str.rstrip)

		self.add_parameter('threshold_upper',
							label='upper threshold',
							set_cmd='POWer:MODulation:THReshold:UPPer {}',
							get_cmd='POWer:MODulation:THReshold:UPPer?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('threshold_lower',
							label='lower threshold',
							set_cmd='POWer:MODulation:THReshold:LOWer {}',
							get_cmd='POWer:MODulation:THReshold:LOWer?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('hysteresis',
							label='hysteresis',
							set_cmd='POWer:MODulation:THReshold:HYSTeresis {}',
							get_cmd='POWer:MODulation:THReshold:HYSTeresis?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('peak_average',
							label='peak average',
							get_cmd='POWer:MODulation:RESult:LPEak:AVG?',
							get_parser=float)

		self.add_parameter('peak_negative',
							label='negative peak',
							get_cmd='POWer:MODulation:RESult:LPEak:NPEak?',
							get_parser=float)

		self.add_parameter('peak_positive',
							label='positive peak',
							get_cmd='POWer:MODulation:RESult:LPEak:PPEak?',
							get_parser=float)

		self.add_parameter('peak_deviation',
							label='standard deviation peak',
							get_cmd='POWer:MODulation:RESult:LPEak:STDDev?',
							get_parser=float)

		self.add_parameter('peak_waveform',
							label='waveform count',
							get_cmd='POWer:MODulation:RESult:LPEak:WFMCount?',
							get_parser=float)

		self.add_parameter('peak',
							label='peak',
							get_cmd='POWer:MODulation:RESult:LPEak:ACTual?',
							get_parser=float)

		self.add_parameter('mean',
							label='mean',
							get_cmd='POWer:MODulation:RESult:MEAN:ACTual?',
							get_parser=float)

		self.add_parameter('mean_average',
							label='average mean',
							get_cmd='POWer:MODulation:RESult:MEAN:AVG?',
							get_parser=float)

		self.add_parameter('mean_negative',
							label='negative peak mean',
							get_cmd='POWer:MODulation:RESult:MEAN:NPEak?',
							get_parser=float)

		self.add_parameter('mean_positive',
							label='positive peak mean',
							get_cmd='POWer:MODulation:RESult:MEAN:PPEak?',
							get_parser=float)

		self.add_parameter('mean_deviation',
							label='standard deviation mean',
							get_cmd='POWer:MODulation:RESult:MEAN:STDDev?',
							get_parser=float)

		self.add_parameter('mean_waveform',
							label='waveform count',
							get_cmd='POWer:MODulation:RESult:MEAN:WFMCount?',
							get_parser=float)

		self.add_parameter('RMS',
							label='RMS',
							get_cmd='POWer:MODulation:RESult:RMS:ACTual?',
							get_parser=float)

		self.add_parameter('RMS_average',
							label='average RMS',
							get_cmd='POWer:MODulation:RESult:RMS:AVG?',
							get_parser=float)

		self.add_parameter('RMS_negative',
							label='negative peak RMS',
							get_cmd='POWer:MODulation:RESult:RMS:NPEak?',
							get_parser=float)

		self.add_parameter('RMS_positive',
							label='positive peak RMS',
							get_cmd='POWer:MODulation:RESult:RMS:PPEak?',
							get_parser=float)

		self.add_parameter('RMS_deviation',
							label='standard deviation RMS',
							get_cmd='POWer:MODulation:RESult:RMS:STDDev?',
							get_parser=float)

		self.add_parameter('RMS_waveform',
							label='waveform count',
							get_cmd='POWer:MODulation:RESult:RMS:WFMCount?',
							get_parser=float)

		self.add_parameter('deviation',
							label='standard deviation',
							get_cmd='POWer:MODulation:RESult:STDDev:ACTual?',
							get_parser=float)

		self.add_parameter('deviation_average',
							label='standard deviation average',
							get_cmd='POWer:MODulation:RESult:STDDev:AVG?',
							get_parser=float)

		self.add_parameter('deviation_negative',
							label='standard deviation negative',
							get_cmd='POWer:MODulation:RESult:STDDev:NPEak?',
							get_parser=float)

		self.add_parameter('deviation_positive',
							label='standard deviation positive',
							get_cmd='POWer:MODulation:RESult:STDDev:PPEak?',
							get_parser=float)

		self.add_parameter('deviation_standard',
							label='standard deviation standard deviation',
							get_cmd='POWer:MODulation:RESult:STDDev:STDDev?',
							get_parser=float)

		self.add_parameter('deviation_waveform',
							label='waveform count',
							get_cmd='POWer:MODulation:RESult:STDDev:WFMCount?',
							get_parser=float)

		self.add_parameter('upper_average',
							label='upper peak average',
							get_cmd='POWer:MODulation:RESult:UPEak:AVG?',
							get_parser=float)

		self.add_parameter('upper_negative',
							label='upper peak negative',
							get_cmd='POWer:MODulation:RESult:UPEak:NPEak?',
							get_parser=float)

		self.add_parameter('upper_positive',
							label='upper peak positive',
							get_cmd='POWer:MODulation:RESult:UPEak:PPEak?',
							get_parser=float)

		self.add_parameter('upper_deviation',
							label='upper peak standard deviation',
							get_cmd='POWer:MODulation:RESult:UPEak:STDDev?',
							get_parser=float)

		self.add_parameter('upper_peak',
							label='upper peak',
							get_cmd='POWer:MODulation:RESult:UPEak:ACTual?',
							get_parser=float)

		self.add_parameter('upper_waveform',
							label='waveform count',
							get_cmd='POWer:MODulation:RESult:UPEakWFMCount?',
							get_parser=float)

	def execute(self): self.write('POWer:MODulation:EXECute')
	def add(self): self.write('POWer:MODulation:REPort:ADD')

class Power_Report(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('description',
							label='description',
							set_cmd='POWer:REPort:DESCription {}',
							get_cmd='POWer:REPort:DESCription?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('DUT',
							label='DUT',
							set_cmd='POWer:REPort:DUT {}',
							get_cmd='POWer:REPort:DUT?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('output',
							label='output',
							set_cmd='POWer:REPort:OUTPut {}',
							get_cmd='POWer:REPort:OUTPut?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('site',
							label='site',
							set_cmd='POWer:REPort:SITE {}',
							get_cmd='POWer:REPort:SITE?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('temperature',
							label='temperature',
							set_cmd='POWer:REPort:TEMPerature {}',
							get_cmd='POWer:REPort:TEMPerature?',
							vals=vals.Ints(-273,32767),
							get_parser=str.rstrip)

		self.add_parameter('user',
							label='user',
							set_cmd='POWer:REPort:USER {}',
							get_cmd='POWer:REPort:USER?',
							vals=vals.Strings(),
							get_parser=str.rstrip)
		
	def add(self): self.write('POWer:REPort:ADD')

class Power_Ripple_Deviation(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('actual',
							label='actual',
							get_cmd='POWer:RIPPle:RESult:STDDev:ACTual?',
							get_parser=float)

		self.add_parameter('average',
							label='average',
							get_cmd='POWer:RIPPle:RESult:STDDev:AVG?',
							get_parser=float)

		self.add_parameter('negative',
							label='negative peak',
							get_cmd='POWer:RIPPle:RESult:STDDev:NPEak?',
							get_parser=float)

		self.add_parameter('positive',
							label='positive peak',
							get_cmd='POWer:RIPPle:RESult:STDDev:PPEak?',
							get_parser=float)

		self.add_parameter('deviation',
							label='deviation',
							get_cmd='POWer:RIPPle:RESult:STDDev:STDDev?',
							get_parser=float)

		self.add_parameter('waveform',
							label='waveform count',
							get_cmd='POWer:RIPPle:RESult:STDDev:WFMCount?',
							get_parser=float)

class Power_Ripple_Frequency(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('actual',
							label='actual frequency',
							get_cmd='POWer:RIPPle:RESult:FREQuency:ACTual?',
							get_parser=float)

		self.add_parameter('average',
							label='average frequency',
							get_cmd='POWer:RIPPle:RESult:FREQuency:AVG?',
							get_parser=float)

		self.add_parameter('negative',
							label='negative peak frequency',
							get_cmd='POWer:RIPPle:RESult:FREQuency:NPEak?',
							get_parser=float)

		self.add_parameter('positive',
							label='positive peak frequency',
							get_cmd='POWer:RIPPle:RESult:FREQuency:PPEak?',
							get_parser=float)

		self.add_parameter('deviation',
							label='deviation frequency',
							get_cmd='POWer:RIPPle:RESult:FREQuency:STDDev?',
							get_parser=float)

		self.add_parameter('waveform',
							label='waveform count',
							get_cmd='POWer:RIPPle:RESult:FREQuency:WFMCount?',
							get_parser=float)

	def execute(self): self.write('POWer:RIPPle:EXECute')
	def add(self): self.write('POWer:RIPPle:REPort:ADD')

class Power_Ripple_Lpeak(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('actual',
							label='actual',
							get_cmd='POWer:RIPPle:RESult:LPEak:ACTual?',
							get_parser=float)

		self.add_parameter('average',
							label='average',
							get_cmd='POWer:RIPPle:RESult:LPEak:AVG?',
							get_parser=float)

		self.add_parameter('negative',
							label='negative peak',
							get_cmd='POWer:RIPPle:RESult:LPEak:NPEak?',
							get_parser=float)

		self.add_parameter('positive',
							label='positive peak',
							get_cmd='POWer:RIPPle:RESult:LPEak:PPEak?',
							get_parser=float)

		self.add_parameter('deviation',
							label='deviation',
							get_cmd='POWer:RIPPle:RESult:LPEak:STDDev?',
							get_parser=float)

		self.add_parameter('waveform',
							label='waveform count',
							get_cmd='POWer:RIPPle:RESult:LPEak:WFMCount?',
							get_parser=float)

class Power_Ripple_Mean(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('actual',
							label='actual',
							get_cmd='POWer:RIPPle:RESult:MEAN:ACTual?',
							get_parser=float)

		self.add_parameter('average',
							label='average',
							get_cmd='POWer:RIPPle:RESult:MEAN:AVG?',
							get_parser=float)

		self.add_parameter('negative',
							label='negative peak',
							get_cmd='POWer:RIPPle:RESult:MEAN:NPEak?',
							get_parser=float)

		self.add_parameter('positive',
							label='positive peak',
							get_cmd='POWer:RIPPle:RESult:MEAN:PPEak?',
							get_parser=float)

		self.add_parameter('deviation',
							label='deviation',
							get_cmd='POWer:RIPPle:RESult:MEAN:STDDev?',
							get_parser=float)

		self.add_parameter('waveform',
							label='waveform count',
							get_cmd='POWer:RIPPle:RESult:MEAN:WFMCount?',
							get_parser=float)

class Power_Ripple_Nduty(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('actual',
							label='actual',
							get_cmd='POWer:RIPPle:RESult:NDCYcle:ACTual?',
							get_parser=float)

		self.add_parameter('average',
							label='average',
							get_cmd='POWer:RIPPle:RESult:NDCYcle:AVG?',
							get_parser=float)

		self.add_parameter('negative',
							label='negative peak',
							get_cmd='POWer:RIPPle:RESult:NDCYcle:NPEak?',
							get_parser=float)

		self.add_parameter('positive',
							label='positive peak',
							get_cmd='POWer:RIPPle:RESult:NDCYcle:PPEak?',
							get_parser=float)

		self.add_parameter('deviation',
							label='deviation',
							get_cmd='POWer:RIPPle:RESult:NDCYcle:STDDev?',
							get_parser=float)

		self.add_parameter('waveform',
							label='waveform count',
							get_cmd='POWer:RIPPle:RESult:NDCYcle:WFMCount?',
							get_parser=float)

class Power_Ripple_Pduty(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('actual',
							label='actual',
							get_cmd='POWer:RIPPle:RESult:PDCYcle:ACTual?',
							get_parser=float)

		self.add_parameter('average',
							label='average',
							get_cmd='POWer:RIPPle:RESult:PDCYcle:AVG?',
							get_parser=float)

		self.add_parameter('negative',
							label='negative peak',
							get_cmd='POWer:RIPPle:RESult:PDCYcle:NPEak?',
							get_parser=float)

		self.add_parameter('positive',
							label='positive peak',
							get_cmd='POWer:RIPPle:RESult:PDCYcle:PPEak?',
							get_parser=float)

		self.add_parameter('deviation',
							label='deviation',
							get_cmd='POWer:RIPPle:RESult:PDCYcle:STDDev?',
							get_parser=float)

		self.add_parameter('waveform',
							label='waveform count',
							get_cmd='POWer:RIPPle:RESult:PDCYcle:WFMCount?',
							get_parser=float)

class Power_Ripple_Peak(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('actual',
							label='actual',
							get_cmd='POWer:RIPPle:RESult:PEAK:ACTual?',
							get_parser=float)

		self.add_parameter('average',
							label='average',
							get_cmd='POWer:RIPPle:RESult:PEAK:AVG?',
							get_parser=float)

		self.add_parameter('negative',
							label='negative peak',
							get_cmd='POWer:RIPPle:RESult:PEAK:NPEak?',
							get_parser=float)

		self.add_parameter('positive',
							label='positive peak',
							get_cmd='POWer:RIPPle:RESult:PEAK:PPEak?',
							get_parser=float)

		self.add_parameter('deviation',
							label='deviation',
							get_cmd='POWer:RIPPle:RESult:PEAK:STDDev?',
							get_parser=float)

		self.add_parameter('waveform',
							label='waveform count',
							get_cmd='POWer:RIPPle:RESult:PEAK:WFMCount?',
							get_parser=float)

class Power_Ripple_Period(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('actual',
							label='actual',
							get_cmd='POWer:RIPPle:RESult:PERiod:ACTual?',
							get_parser=float)

		self.add_parameter('average',
							label='average',
							get_cmd='POWer:RIPPle:RESult:PERiod:AVG?',
							get_parser=float)

		self.add_parameter('negative',
							label='negative peak',
							get_cmd='POWer:RIPPle:RESult:PERiod:NPEak?',
							get_parser=float)

		self.add_parameter('positive',
							label='positive peak',
							get_cmd='POWer:RIPPle:RESult:PERiod:PPEak?',
							get_parser=float)

		self.add_parameter('deviation',
							label='deviation',
							get_cmd='POWer:RIPPle:RESult:PERiod:STDDev?',
							get_parser=float)

		self.add_parameter('waveform',
							label='waveform count',
							get_cmd='POWer:RIPPle:RESult:PERiod:WFMCount?',
							get_parser=float)

class Power_Ripple_Upeak(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('actual',
							label='actual',
							get_cmd='POWer:RIPPle:RESult:UPEak:ACTual?',
							get_parser=float)

		self.add_parameter('average',
							label='average',
							get_cmd='POWer:RIPPle:RESult:UPEak:AVG?',
							get_parser=float)

		self.add_parameter('negative',
							label='negative peak',
							get_cmd='POWer:RIPPle:RESult:UPEak:NPEak?',
							get_parser=float)

		self.add_parameter('positive',
							label='positive peak',
							get_cmd='POWer:RIPPle:RESult:UPEak:PPEak?',
							get_parser=float)

		self.add_parameter('deviation',
							label='deviation',
							get_cmd='POWer:RIPPle:RESult:UPEak:STDDev?',
							get_parser=float)

		self.add_parameter('waveform',
							label='waveform count',
							get_cmd='POWer:RIPPle:RESult:UPEak:WFMCount?',
							get_parser=float)

class Power_State(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, gatnum):
		super().__init__(parent, name)

		self.add_parameter('type',
							label='measurement type',
							set_cmd='POWer:ONOFf:MEASurement {}',
							get_cmd='POWer:ONOFf:MEASurement?',
							vals=vals.Enum('TON', 'TOFF'),
							get_parser=str.rstrip)

		self.add_parameter('time',
							label=f'gate {gatnum} time',
							get_cmd=f'POWer:ONOFf:RESult{gatnum}:TIME?',
							get_parser=float)

	def execute(self): self.write('POWer:ONOFf:EXECute')
	def add(self): self.write('POWer:ONOFf:REPort:ADD')

class Power_Quality_Actual(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('current_crestfactor',
							label='current crestfactor',
							get_cmd='POWer:QUALity:RESult:CURRent:CREStfactor:ACTual?',
							get_parser=float)

		self.add_parameter('current_frequency',
							label='current frequency',
							get_cmd='POWer:QUALity:RESult:CURRent:FREQuency:ACTual?',
							get_parser=float)

		self.add_parameter('current_RMS',
							label='RMS current',
							get_cmd='POWer:QUALity:RESult:CURRent:RMS:ACTual?',
							get_parser=float)

		self.add_parameter('power_apparent',
							label='apparent power',
							get_cmd='POWer:QUALity:RESult:POWer:APParent:ACTual?',
							get_parser=float)

		self.add_parameter('power_factor',
							label='power factor',
							get_cmd='POWer:QUALity:RESult:POWer:PFACtor:ACTual?',
							get_parser=float)

		self.add_parameter('power_phase',
							label='phase power',
							get_cmd='POWer:QUALity:RESult:POWer:PHASe:ACTual?',
							get_parser=float)

		self.add_parameter('power_reactive',
							label='reactive power',
							get_cmd='POWer:QUALity:RESult:POWer:REACtive:ACTual?',
							get_parser=float)

		self.add_parameter('real_power',
							label='real power',
							get_cmd='POWer:QUALity:RESult:POWer:REALpower:ACTual?',
							get_parser=float)

		self.add_parameter('voltage_crestfactor',
							label='crestfactor voltage',
							get_cmd='POWer:QUALity:RESult:VOLTage:CREStfactor:ACTual?',
							get_parser=float)

		self.add_parameter('voltage_frequency',
							label='voltage frequency',
							get_cmd='POWer:QUALity:RESult:VOLTage:FREQuency:ACTual?',
							get_parser=float)

		self.add_parameter('voltage_RMS',
							label='RMS voltage',
							get_cmd='POWer:QUALity:RESult:VOLTage:RMS:ACTual?',
							get_parser=float)

class Power_Quality_Average(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('current_crestfactor',
							label='current crestfactor',
							get_cmd='POWer:QUALity:RESult:CURRent:CREStfactor:AVG?',
							get_parser=float)

		self.add_parameter('current_frequency',
							label='current frequency',
							get_cmd='POWer:QUALity:RESult:CURRent:FREQuency:AVG?',
							get_parser=float)

		self.add_parameter('current_RMS',
							label='RMS current',
							get_cmd='POWer:QUALity:RESult:CURRent:RMS:AVG?',
							get_parser=float)

		self.add_parameter('power_apparent',
							label='apparent power',
							get_cmd='POWer:QUALity:RESult:POWer:APParent:AVG?',
							get_parser=float)

		self.add_parameter('power_factor',
							label='power factor',
							get_cmd='POWer:QUALity:RESult:POWer:PFACtor:AVG?',
							get_parser=float)

		self.add_parameter('power_phase',
							label='phase power',
							get_cmd='POWer:QUALity:RESult:POWer:PHASe:AVG?',
							get_parser=float)

		self.add_parameter('power_reactive',
							label='reactive power',
							get_cmd='POWer:QUALity:RESult:POWer:REACtive:AVG?',
							get_parser=float)

		self.add_parameter('real_power',
							label='real power',
							get_cmd='POWer:QUALity:RESult:POWer:REALpower:AVG?',
							get_parser=float)

		self.add_parameter('voltage_crestfactor',
							label='crestfactor voltage',
							get_cmd='POWer:QUALity:RESult:VOLTage:CREStfactor:AVG?',
							get_parser=float)

		self.add_parameter('voltage_frequency',
							label='voltage frequency',
							get_cmd='POWer:QUALity:RESult:VOLTage:FREQuency:AVG?',
							get_parser=float)

		self.add_parameter('voltage_RMS',
							label='RMS voltage',
							get_cmd='POWer:QUALity:RESult:VOLTage:RMS:AVG?',
							get_parser=float)

	def execute(self): self.write('POWer:QUALity:EXECute')
	def add(self): self.write('POWer:QUALity:REPort:ADD')

class Power_Quality_Deviation(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('current_crestfactor',
							label='current crestfactor',
							get_cmd='POWer:QUALity:RESult:CURRent:CREStfactor:STDDev?',
							get_parser=float)

		self.add_parameter('current_frequency',
							label='current frequency',
							get_cmd='POWer:QUALity:RESult:CURRent:FREQuency:STDDev?',
							get_parser=float)

		self.add_parameter('current_RMS',
							label='RMS current',
							get_cmd='POWer:QUALity:RESult:CURRent:RMS:STDDev?',
							get_parser=float)

		self.add_parameter('power_apparent',
							label='apparent power',
							get_cmd='POWer:QUALity:RESult:POWer:APParent:STDDev?',
							get_parser=float)

		self.add_parameter('power_factor',
							label='power factor',
							get_cmd='POWer:QUALity:RESult:POWer:PFACtor:STDDev?',
							get_parser=float)

		self.add_parameter('power_phase',
							label='phase power',
							get_cmd='POWer:QUALity:RESult:POWer:PHASe:STDDev?',
							get_parser=float)

		self.add_parameter('power_reactive',
							label='reactive power',
							get_cmd='POWer:QUALity:RESult:POWer:REACtive:STDDev?',
							get_parser=float)

		self.add_parameter('real_power',
							label='real power',
							get_cmd='POWer:QUALity:RESult:POWer:REALpower:STDDev?',
							get_parser=float)

		self.add_parameter('voltage_crestfactor',
							label='crestfactor voltage',
							get_cmd='POWer:QUALity:RESult:VOLTage:CREStfactor:STDDev?',
							get_parser=float)

		self.add_parameter('voltage_frequency',
							label='voltage frequency',
							get_cmd='POWer:QUALity:RESult:VOLTage:FREQuency:STDDev?',
							get_parser=float)

		self.add_parameter('voltage_RMS',
							label='RMS voltage',
							get_cmd='POWer:QUALity:RESult:VOLTage:RMS:STDDev?',
							get_parser=float)

class Power_Quality_Negative(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('current_crestfactor',
							label='current crestfactor',
							get_cmd='POWer:QUALity:RESult:CURRent:CREStfactor:NPEak?',
							get_parser=float)

		self.add_parameter('current_frequency',
							label='current frequency',
							get_cmd='POWer:QUALity:RESult:CURRent:FREQuency:NPEak?',
							get_parser=float)

		self.add_parameter('current_RMS',
							label='RMS current',
							get_cmd='POWer:QUALity:RESult:CURRent:RMS:NPEak?',
							get_parser=float)

		self.add_parameter('power_apparent',
							label='apparent power',
							get_cmd='POWer:QUALity:RESult:POWer:APParent:NPEak?',
							get_parser=float)

		self.add_parameter('power_factor',
							label='power factor',
							get_cmd='POWer:QUALity:RESult:POWer:PFACtor:NPEak?',
							get_parser=float)

		self.add_parameter('power_phase',
							label='phase power',
							get_cmd='POWer:QUALity:RESult:POWer:PHASe:NPEak?',
							get_parser=float)

		self.add_parameter('power_reactive',
							label='reactive power',
							get_cmd='POWer:QUALity:RESult:POWer:REACtive:NPEak?',
							get_parser=float)

		self.add_parameter('real_power',
							label='real power',
							get_cmd='POWer:QUALity:RESult:POWer:REALpower:NPEak?',
							get_parser=float)

		self.add_parameter('voltage_crestfactor',
							label='crestfactor voltage',
							get_cmd='POWer:QUALity:RESult:VOLTage:CREStfactor:NPEak?',
							get_parser=float)

		self.add_parameter('voltage_frequency',
							label='voltage frequency',
							get_cmd='POWer:QUALity:RESult:VOLTage:FREQuency:NPEak?',
							get_parser=float)

		self.add_parameter('voltage_RMS',
							label='RMS voltage',
							get_cmd='POWer:QUALity:RESult:VOLTage:RMS:NPEak?',
							get_parser=float)

class Power_Quality_Positive(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('current_crestfactor',
							label='current crestfactor',
							get_cmd='POWer:QUALity:RESult:CURRent:CREStfactor:PPEak?',
							get_parser=float)

		self.add_parameter('current_frequency',
							label='current frequency',
							get_cmd='POWer:QUALity:RESult:CURRent:FREQuency:PPEak?',
							get_parser=float)

		self.add_parameter('current_RMS',
							label='RMS current',
							get_cmd='POWer:QUALity:RESult:CURRent:RMS:PPEak?',
							get_parser=float)

		self.add_parameter('power_apparent',
							label='apparent power',
							get_cmd='POWer:QUALity:RESult:POWer:APParent:PPEak?',
							get_parser=float)

		self.add_parameter('power_factor',
							label='power factor',
							get_cmd='POWer:QUALity:RESult:POWer:PFACtor:PPEak?',
							get_parser=float)

		self.add_parameter('power_phase',
							label='phase power',
							get_cmd='POWer:QUALity:RESult:POWer:PHASe:PPEak?',
							get_parser=float)

		self.add_parameter('power_reactive',
							label='reactive power',
							get_cmd='POWer:QUALity:RESult:POWer:REACtive:PPEak?',
							get_parser=float)

		self.add_parameter('real_power',
							label='real power',
							get_cmd='POWer:QUALity:RESult:POWer:REALpower:PPEak?',
							get_parser=float)

		self.add_parameter('voltage_crestfactor',
							label='crestfactor voltage',
							get_cmd='POWer:QUALity:RESult:VOLTage:CREStfactor:PPEak?',
							get_parser=float)

		self.add_parameter('voltage_frequency',
							label='voltage frequency',
							get_cmd='POWer:QUALity:RESult:VOLTage:FREQuency:PPEak?',
							get_parser=float)

		self.add_parameter('voltage_RMS',
							label='RMS voltage',
							get_cmd='POWer:QUALity:RESult:VOLTage:RMS:PPEak?',
							get_parser=float)

class Power_Quality_Waveform(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('current_crestfactor',
							label='current crestfactor',
							get_cmd='POWer:QUALity:RESult:CURRent:CREStfactor:WFMCount?',
							get_parser=float)

		self.add_parameter('current_frequency',
							label='current frequency',
							get_cmd='POWer:QUALity:RESult:CURRent:FREQuency:WFMCount?',
							get_parser=float)

		self.add_parameter('current_RMS',
							label='RMS current',
							get_cmd='POWer:QUALity:RESult:CURRent:RMS:WFMCount?',
							get_parser=float)

		self.add_parameter('power_apparent',
							label='apparent power',
							get_cmd='POWer:QUALity:RESult:POWer:APParent:WFMCount?',
							get_parser=float)

		self.add_parameter('power_factor',
							label='power factor',
							get_cmd='POWer:QUALity:RESult:POWer:PFACtor:WFMCount?',
							get_parser=float)

		self.add_parameter('power_phase',
							label='phase power',
							get_cmd='POWer:QUALity:RESult:POWer:PHASe:WFMCount?',
							get_parser=float)

		self.add_parameter('power_reactive',
							label='reactive power',
							get_cmd='POWer:QUALity:RESult:POWer:REACtive:WFMCount?',
							get_parser=float)

		self.add_parameter('real_power',
							label='real power',
							get_cmd='POWer:QUALity:RESult:POWer:REALpower:WFMCount?',
							get_parser=float)

		self.add_parameter('voltage_crestfactor',
							label='crestfactor voltage',
							get_cmd='POWer:QUALity:RESult:VOLTage:CREStfactor:WFMCount?',
							get_parser=float)

		self.add_parameter('voltage_frequency',
							label='voltage frequency',
							get_cmd='POWer:QUALity:RESult:VOLTage:FREQuency:WFMCount?',
							get_parser=float)

		self.add_parameter('voltage_RMS',
							label='RMS voltage',
							get_cmd='POWer:QUALity:RESult:VOLTage:RMS:WFMCount?',
							get_parser=float)

class Ripple_Result_Frequency(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('actual',
							label='actual',
							get_cmd='POWer:RIPPle:RESult:FREQuency:ACTual?',
							get_parser=float)

		self.add_parameter('average',
							label='average',
							get_cmd='POWer:RIPPle:RESult:FREQuency:AVG?',
							get_parser=float)

		self.add_parameter('negative_peak',
							label='negative peak',
							get_cmd='POWer:RIPPle:RESult:FREQuency:NPEak?',
							get_parser=float)

		self.add_parameter('positive_peak',
							label='positive peak',
							get_cmd='POWer:RIPPle:RESult:FREQuency:PPEak?',
							get_parser=float)

		self.add_parameter('deviation',
							label='standard deviation',
							get_cmd='POWer:RIPPle:RESult:FREQuency:STDDev?',
							get_parser=float)

		self.add_parameter('waveform',
							label='waveform count',
							get_cmd='POWer:RIPPle:RESult:FREQuency:WFMCount?',
							get_parser=float)

class Ripple_Result_Mean(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('actual',
							label='actual',
							get_cmd='POWer:RIPPle:RESult:MEAN:ACTual?',
							get_parser=float)

		self.add_parameter('average',
							label='average',
							get_cmd='POWer:RIPPle:RESult:MEAN:AVG?',
							get_parser=float)

		self.add_parameter('negative_peak',
							label='negative peak',
							get_cmd='POWer:RIPPle:RESult:MEAN:NPEak?',
							get_parser=float)

		self.add_parameter('positive_peak',
							label='positive peak',
							get_cmd='POWer:RIPPle:RESult:MEAN:PPEak?',
							get_parser=float)

		self.add_parameter('deviation',
							label='standard deviation',
							get_cmd='POWer:RIPPle:RESult:MEAN:STDDev?',
							get_parser=float)

		self.add_parameter('waveform',
							label='waveform count',
							get_cmd='POWer:RIPPle:RESult:MEAN:WFMCount?',
							get_parser=float)

class Ripple_Result_Nduty(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('actual',
							label='actual',
							get_cmd='POWer:RIPPle:RESult:NDCYcle:ACTual?',
							get_parser=float)

		self.add_parameter('average',
							label='average',
							get_cmd='POWer:RIPPle:RESult:NDCYcle:AVG?',
							get_parser=float)

		self.add_parameter('negative_peak',
							label='negative peak',
							get_cmd='POWer:RIPPle:RESult:NDCYcle:NPEak?',
							get_parser=float)

		self.add_parameter('positive_peak',
							label='positive peak',
							get_cmd='POWer:RIPPle:RESult:NDCYcle:PPEak?',
							get_parser=float)

		self.add_parameter('deviation',
							label='standard deviation',
							get_cmd='POWer:RIPPle:RESult:NDCYcle:STDDev?',
							get_parser=float)

		self.add_parameter('waveform',
							label='waveform count',
							get_cmd='POWer:RIPPle:RESult:NDCYcle:WFMCount?',
							get_parser=float)

class Ripple_Result_Pduty(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('actual',
							label='actual',
							get_cmd='POWer:RIPPle:RESult:PDCYcle:ACTual?',
							get_parser=float)

		self.add_parameter('average',
							label='average',
							get_cmd='POWer:RIPPle:RESult:PDCYcle:AVG?',
							get_parser=float)

		self.add_parameter('negative_peak',
							label='negative peak',
							get_cmd='POWer:RIPPle:RESult:PDCYcle:NPEak?',
							get_parser=float)

		self.add_parameter('positive_peak',
							label='positive peak',
							get_cmd='POWer:RIPPle:RESult:PDCYcle:PPEak?',
							get_parser=float)

		self.add_parameter('deviation',
							label='standard deviation',
							get_cmd='POWer:RIPPle:RESult:PDCYcle:STDDev?',
							get_parser=float)

		self.add_parameter('waveform',
							label='waveform count',
							get_cmd='POWer:RIPPle:RESult:PDCYcle:WFMCount?',
							get_parser=float)

class Ripple_Result_Peak(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('actual',
							label='actual',
							get_cmd='POWer:RIPPle:RESult:PEAK:ACTual?',
							get_parser=float)

		self.add_parameter('average',
							label='average',
							get_cmd='POWer:RIPPle:RESult:PEAK:AVG?',
							get_parser=float)

		self.add_parameter('negative_peak',
							label='negative peak',
							get_cmd='POWer:RIPPle:RESult:PEAK:NPEak?',
							get_parser=float)

		self.add_parameter('positive_peak',
							label='positive peak',
							get_cmd='POWer:RIPPle:RESult:PEAK:PPEak?',
							get_parser=float)

		self.add_parameter('deviation',
							label='standard deviation',
							get_cmd='POWer:RIPPle:RESult:PEAK:STDDev?',
							get_parser=float)

		self.add_parameter('waveform',
							label='waveform count',
							get_cmd='POWer:RIPPle:RESult:PEAK:WFMCount?',
							get_parser=float)

class Ripple_Result_Period(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('actual',
							label='actual',
							get_cmd='POWer:RIPPle:RESult:PERiod:ACTual?',
							get_parser=float)

		self.add_parameter('average',
							label='average',
							get_cmd='POWer:RIPPle:RESult:PERiod:AVG?',
							get_parser=float)

		self.add_parameter('negative_peak',
							label='negative peak',
							get_cmd='POWer:RIPPle:RESult:PERiod:NPEak?',
							get_parser=float)

		self.add_parameter('positive_peak',
							label='positive peak',
							get_cmd='POWer:RIPPle:RESult:PERiod:PPEak?',
							get_parser=float)

		self.add_parameter('deviation',
							label='standard deviation',
							get_cmd='POWer:RIPPle:RESult:PERiod:STDDev?',
							get_parser=float)

		self.add_parameter('waveform',
							label='waveform count',
							get_cmd='POWer:RIPPle:RESult:PERiod:WFMCount?',
							get_parser=float)

class Ripple_Result_Deviation(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('actual',
							label='actual',
							get_cmd='POWer:RIPPle:RESult:STDDev:ACTual?',
							get_parser=float)

		self.add_parameter('average',
							label='average',
							get_cmd='POWer:RIPPle:RESult:STDDev:AVG?',
							get_parser=float)

		self.add_parameter('negative_peak',
							label='negative peak',
							get_cmd='POWer:RIPPle:RESult:STDDev:NPEak?',
							get_parser=float)

		self.add_parameter('positive_peak',
							label='positive peak',
							get_cmd='POWer:RIPPle:RESult:STDDev:PPEak?',
							get_parser=float)

		self.add_parameter('deviation',
							label='standard deviation',
							get_cmd='POWer:RIPPle:RESult:STDDev:STDDev?',
							get_parser=float)

		self.add_parameter('waveform',
							label='waveform count',
							get_cmd='POWer:RIPPle:RESult:STDDev:WFMCount?',
							get_parser=float)

class Slew_Rate(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('delta_sample',
							label='sample numbers',
							set_cmd='POWer:SLEWrate:DSAMple {}',
							get_cmd='POWer:SLEWrate:DSAMple?',
							vals=vals.Ints(),
							get_parser=int)

		self.add_parameter('delta_time',
							label='delta time',
							set_cmd='POWer:SLEWrate:DTIMe {}',
							get_cmd='POWer:SLEWrate:DTIMe?',
							vals=vals.Numbers(),
							get_parser=float)

	def execute(self): self.write('POWer:SLEWrate:EXECute')
	def add(self): self.write('POWer:SLEWrate:REPort:ADD')

class Slewrate_Lpeak(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('actual',
							label='actual',
							get_cmd='POWer:SLEWrate:RESult:LPEak:ACTual?',
							get_parser=float)

		self.add_parameter('average',
							label='average',
							get_cmd='POWer:SLEWrate:RESult:LPEak:AVG?',
							get_parser=float)

		self.add_parameter('negative_peak',
							label='negative peak',
							get_cmd='POWer:SLEWrate:RESult:LPEak:NPEak?',
							get_parser=float)

		self.add_parameter('positive_peak',
							label='positive peak',
							get_cmd='POWer:SLEWrate:RESult:LPEak:PPEak?',
							get_parser=float)

		self.add_parameter('deviation',
							label='standard deviation',
							get_cmd='POWer:SLEWrate:RESult:LPEak:STDDev?',
							get_parser=float)

		self.add_parameter('waveform',
							label='waveform',
							get_cmd='POWer:SLEWrate:RESult:LPEak:WFMCount?',
							get_parser=float)

class Slewrate_Upeak(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('actual',
							label='actual',
							get_cmd='POWer:SLEWrate:RESult:UPEak:ACTual?',
							get_parser=float)

		self.add_parameter('average',
							label='average',
							get_cmd='POWer:SLEWrate:RESult:UPEak:AVG?',
							get_parser=float)

		self.add_parameter('negative_peak',
							label='negative peak',
							get_cmd='POWer:SLEWrate:RESult:UPEak:NPEak?',
							get_parser=float)

		self.add_parameter('positive_peak',
							label='positive peak',
							get_cmd='POWer:SLEWrate:RESult:UPEak:PPEak?',
							get_parser=float)

		self.add_parameter('deviation',
							label='standard deviation',
							get_cmd='POWer:SLEWrate:RESult:UPEak:STDDev?',
							get_parser=float)

		self.add_parameter('waveform',
							label='waveform',
							get_cmd='POWer:SLEWrate:RESult:UPEak:WFMCount?',
							get_parser=float)

class SOA(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, poinum):
		super().__init__(parent, name)

		self.add_parameter('lin_count',
							label='linear count',
							get_cmd='POWer:SOA:LINear:COUNt?',
							get_parser=float)

		self.add_parameter('log_count',
							label='logarithmic count',
							get_cmd='POWer:SOA:LOGarithmic:COUNt?',
							get_parser=float)

		self.add_parameter('lin_insert',
							label='linear insert',
							set_cmd='POWer:SOA:LINear:INSert {}',
							vals=vals.Strings())

		self.add_parameter('log_insert',
							label='logarithmic insert',
							set_cmd='POWer:SOA:LOGarithmic:INSert {}',
							vals=vals.Strings())

		self.add_parameter('lin_current',
							label=f'point {poinum} linear current',
							set_cmd=f'POWer:SOA:LINear:POINt{poinum}:CURRent {{}}',
							get_cmd=f'POWer:SOA:LINear:POINt{poinum}:CURRent?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('log_current',
							label=f'point {poinum} logarithmic current',
							set_cmd=f'POWer:SOA:LOGarithmic:POINt{poinum}:CURRent {{}}',
							get_cmd=f'POWer:SOA:LOGarithmic:POINt{poinum}:CURRent?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('lin_current_max',
							label=f'point {poinum} linear maximum current',
							set_cmd=f'POWer:SOA:LINear:POINt{poinum}:CURRent:MAXimum {{}}',
							get_cmd=f'POWer:SOA:LINear:POINt{poinum}:CURRent:MAXimum?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('log_current_max',
							label=f'point {poinum} logarithmic maximum current',
							set_cmd=f'POWer:SOA:LOGarithmic:POINt{poinum}:CURRent:MAXimum {{}}',
							get_cmd=f'POWer:SOA:LOGarithmic:POINt{poinum}:CURRent:MAXimum?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('lin_current_min',
							label=f'point {poinum} linear minimum current',
							set_cmd=f'POWer:SOA:LINear:POINt{poinum}:CURRent:MINimum {{}}',
							get_cmd=f'POWer:SOA:LINear:POINt{poinum}:CURRent:MINimum?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('log_current_min',
							label=f'point {poinum} logarithmic minimum current',
							set_cmd=f'POWer:SOA:LOGarithmic:POINt{poinum}:CURRent:MINimum {{}}',
							get_cmd=f'POWer:SOA:LOGarithmic:POINt{poinum}:CURRent:MINimum?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('lin_voltage',
							label=f'point {poinum} linear voltage',
							set_cmd=f'POWer:SOA:LINear:POINt{poinum}:VOLTage {{}}',
							get_cmd=f'POWer:SOA:LINear:POINt{poinum}:VOLTage?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('log_voltage',
							label=f'point {poinum} logarithmic voltage',
							set_cmd=f'POWer:SOA:LOGarithmic:POINt{poinum}:VOLTage {{}}',
							get_cmd=f'POWer:SOA:LOGarithmic:POINt{poinum}:VOLTage?',
							vals=vals.Strings(),
							get_parser=float)

		self.add_parameter('lin_remove',
							label='linear remove',
							set_cmd='POWer:SOA:LINear:REMove {}',
							vals=vals.Strings())

		self.add_parameter('log_remove',
							label='logarithmic remove',
							set_cmd='POWer:SOA:LOGarithmic:REMove {}',
							vals=vals.Strings())

		self.add_parameter('result_failed',
							label='failed result',
							get_cmd='POWer:SOA:RESult:ACQuisition:FAILed?',
							get_parser=int)
						
		self.add_parameter('fail_rate',
							label='fail rate',
							get_cmd='POWer:SOA:RESult:ACQuisition:FRATe?',
							get_parser=float)

		self.add_parameter('result_passed',
							label='passed result',
							get_cmd='POWer:SOA:RESult:ACQuisition:PASSed?',
							get_parser=int)

		self.add_parameter('result_points',
							label='points',
							get_cmd='POWer:SOA:RESult:ACQuisition:POINts?',
							get_parser=int)

		self.add_parameter('result_state',
							label='state',
							get_cmd='POWer:SOA:RESult:ACQuisition:STATe?',
							get_parser=int)

		self.add_parameter('result_tolerance',
							label='tolerance',
							set_cmd='POWer:SOA:RESult:ACQuisition:TOLerance {}',
							get_cmd='POWer:SOA:RESult:ACQuisition:TOLerance?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('violation_count',
							label='violation count',
							get_cmd='POWer:SOA:RESult:ACQuisition:VCOunt?',
							get_parser=float)

		self.add_parameter('violation',
							label=f'point {poinum} violation',
							get_cmd=f'POWer:SOA:RESult:ACQuisition:VIOLation{poinum}?',
							get_parser=str.rstrip)

		self.add_parameter('violation_current',
							label=f'point {poinum} current violation',
							get_cmd=f'POWer:SOA:RESult:ACQuisition:VIOLation{poinum}:CURRent?',
							get_parser=float)

		self.add_parameter('total_count',
							label='total count',
							get_cmd='POWer:SOA:RESult:TOTal:COUNt?',
							get_parser=int)

		self.add_parameter('total_failed',
							label='total failed',
							get_cmd='POWer:SOA:RESult:TOTal:FAILed?',
							get_parser=int)

		self.add_parameter('total_fail_rate',
							label='total fail rate',
							get_cmd='POWer:SOA:RESult:TOTal:FRATe?',
							get_parser=float)

		self.add_parameter('total_passed',
							label='total passed',
							get_cmd='POWer:SOA:RESult:TOTal:PASSed?',
							get_parser=int)

		self.add_parameter('total_sample',
							label='total sample count',
							get_cmd='POWer:SOA:RESult:TOTal:SAMPle:COUNt?',
							get_parser=int)

		self.add_parameter('total_sample_failed',
							label='total sample failed',
							get_cmd='POWer:SOA:RESult:TOTal:SAMPle:FAILed?',
							get_parser=int)

		self.add_parameter('total_sample_passed',
							label='total sample passed',
							get_cmd='POWer:SOA:RESult:TOTal:SAMPle:PASSed?',
							get_parser=int)

		self.add_parameter('total_state',
							label='total state',
							get_cmd='POWer:SOA:RESult:TOTal:STATe?',
							get_parser=int)

		self.add_parameter('total_tolerance',
							label='total tolerance',
							set_cmd='POWer:SOA:RESult:TOTal:TOLerance {}',
							get_cmd='POWer:SOA:RESult:TOTal:TOLerance?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('total_violation_count',
							label='total violation count',
							get_cmd='POWer:SOA:RESult:TOTal:VCOunt?',
							get_parser=float)

		self.add_parameter('total_violation',
							label=f'point {poinum} total violation',
							get_cmd=f'POWer:SOA:RESult:TOTal:VIOLation{poinum}?',
							get_parser=str.rstrip)

		self.add_parameter('total_violation_current',
							label=f'point {poinum} violation current',
							get_cmd=f'POWer:SOA:RESult:TOTal:VIOLation{poinum}:CURRent?',
							get_parser=float)

		self.add_parameter('total_violation_voltage',
							label=f'point {poinum} violation voltage',
							get_cmd=f'POWer:SOA:RESult:TOTal:VIOLation{poinum}:VOLTage?',
							get_parser=float)

		self.add_parameter('total_current_data',
							label=f'point {poinum} violation current data',
							get_cmd=f'POWer:SOA:RESult:TOTal:VIOLation{poinum}:CURRent:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('total_voltage_data',
							label=f'point {poinum} violation voltage data',
							get_cmd=f'POWer:SOA:RESult:TOTal:VIOLation{poinum}:VOLTage:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('total_current_header',
							label=f'point {poinum} violation current header',
							get_cmd=f'POWer:SOA:RESult:TOTal:VIOLation{poinum}:CURRent:DATA:HEADer?',
							get_parser=str.rstrip)

		self.add_parameter('total_voltage_header',
							label=f'point {poinum}  violation voltage header',
							get_cmd=f'POWer:SOA:RESult:TOTal:VIOLation{poinum}:VOLTage:DATA:HEADer?',
							get_parser=str.rstrip)

		self.add_parameter('total_current_xincrement',
							label=f'point {poinum} violation current x increment',
							get_cmd=f'POWer:SOA:RESult:TOTal:VIOLation{poinum}:CURRent:DATA:XINCrement?',
							get_parser=float)

		self.add_parameter('total_voltage_xincrement',
							label=f'point {poinum} violation voltage x increment',
							get_cmd=f'POWer:SOA:RESult:TOTal:VIOLation{poinum}:VOLTage:DATA:XINCrement?',
							get_parser=float)
				
		self.add_parameter('total_current_xorigin',
							label=f'point {poinum} violation current x origin',
							get_cmd=f'POWer:SOA:RESult:TOTal:VIOLation{poinum}:CURRent:DATA:XORigin?',
							get_parser=float)

		self.add_parameter('total_voltage_xorigin',
							label=f'point {poinum} violation voltage x origin',
							get_cmd=f'POWer:SOA:RESult:TOTal:VIOLation{poinum}:VOLTage:DATA:XORigin?',
							get_parser=float)

		self.add_parameter('total_current_yincrement',
							label=f'point {poinum} violation current y increment',
							get_cmd=f'POWer:SOA:RESult:TOTal:VIOLation{poinum}:CURRent:DATA:YINCrement?',
							get_parser=float)

		self.add_parameter('total_voltage_yincrement',
							label=f'point {poinum} violation voltage y increment',
							get_cmd=f'POWer:SOA:RESult:TOTal:VIOLation{poinum}:VOLTage:DATA:YINCrement?',
							get_parser=float)

		self.add_parameter('total_current_yorigin',
							label=f'point {poinum} violation current y origin',
							get_cmd=f'POWer:SOA:RESult:TOTal:VIOLation{poinum}:CURRent:DATA:YORigin?',
							get_parser=float)

		self.add_parameter('total_voltage_yorigin',
							label=f'point {poinum} violation voltage y origin',
							get_cmd=f'POWer:SOA:RESult:TOTal:VIOLation{poinum}:VOLTage:DATA:YORigin?',
							get_parser=float)

		self.add_parameter('total_current_yresolution',
							label=f'point {poinum} violation current y resolution',
							get_cmd=f'POWer:SOA:RESult:TOTal:VIOLation{poinum}:CURRent:DATA:YRESolution?',
							get_parser=str.rstrip)

		self.add_parameter('total_voltage_yresolution',
							label=f'point {poinum} violation voltage y resolution',
							get_cmd=f'POWer:SOA:RESult:TOTal:VIOLation{poinum}:VOLTage:DATA:YRESolution?',
							get_parser=str.rstrip)

		self.add_parameter('scale',
							label='scale',
							set_cmd='POWer:SOA:SCALe {}',
							get_cmd='POWer:SOA:SCALe?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('scale_display',
							label='display scale',
							set_cmd='POWer:SOA:SCALe:DISPlay {}',
							get_cmd='POWer:SOA:SCALe:DISPlay?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('scale_mask',
							label='mask scale',
							set_cmd='POWer:SOA:SCALe:MASK {}',
							get_cmd='POWer:SOA:SCALe:MASK?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

	def execute(self): self.write('POWer:SOA:EXECute')
	def lin_add(self): self.write('POWer:SOA:LINear:ADD')
	def log_add(self): self.write('POWer:SOA:LOGarithmic:ADD')
	def report_add(self): self.write('POWer:SOA:REPort:ADD')
	def restart(self): self.write('POWer:SOA:RESTart')

class Spectrum(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, harmnum):
		super().__init__(parent, name)

		self.add_parameter('input_frequency',
							label='input frequency',
							set_cmd='POWer:SPECtrum:FREQuency {}',
							get_cmd='POWer:SPECtrum:FREQuency?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('frequency',
							label=f'harmonic {harmnum} frequency',
							get_cmd=f'POWer:SPECtrum:RESult{harmnum}:FREQuency?',
							get_parser=float)

		self.add_parameter('level',
							label=f'harmonic {harmnum} level',
							get_cmd=f'POWer:SPECtrum:RESult{harmnum}:LEVel:VALue?',
							get_parser=float)

		self.add_parameter('maximum_level',
							label=f'harmonic {harmnum} maximum level',
							get_cmd=f'POWer:SPECtrum:RESult{harmnum}:MAXimum?',
							get_parser=float)

		self.add_parameter('average_level',
							label=f'harmonic {harmnum} average level',
							get_cmd=f'POWer:SPECtrum:RESult{harmnum}:MEAN?',
							get_parser=float)

		self.add_parameter('minimum_level',
							label=f'harmonic {harmnum} minimum level',
							get_cmd=f'POWer:SPECtrum:RESult{harmnum}:MINimum?',
							get_parser=float)

		self.add_parameter('waveform',
							label=f'harmonic {harmnum} waveform count',
							get_cmd=f'POWer:SPECtrum:RESult{harmnum}:WFMCount?',
							get_parser=float)

		self.add_parameter('export_path',
							label='export path',
							set_cmd='EXPort:POWer:NAME {}',
							get_cmd='EXPort:POWer:NAME?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

	def execute(self): self.write('POWer:SPECtrum:EXECute')
	def add(self): self.write('POWer:SPECtrum:REPort:ADD')
	def reset(self): self.write(f'POWer:SPECtrum:RESult{harmnum}:RESet')
	def save(self): self.write('EXPort:POWer:SAVE')

class Switching(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('conduction_start',
							label='start time',
							set_cmd='POWer:SWITching:GATE:CONDuction:STARt {}',
							get_cmd='POWer:SWITching:GATE:CONDuction:STARt?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('conduction_stop',
							label='stop time',
							set_cmd='POWer:SWITching:GATE:CONDuction:STOP {}',
							get_cmd='POWer:SWITching:GATE:CONDuction:STOP?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('non_conduction_start',
							label='start time',
							set_cmd='POWer:SWITching:GATE:NCONduction:STARt {}',
							get_cmd='POWer:SWITching:GATE:NCONduction:STARt?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('non_conduction_stop',
							label='stop time',
							set_cmd='POWer:SWITching:GATE:NCONduction:STOP {}',
							get_cmd='POWer:SWITching:GATE:NCONduction:STOP?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('gate_off_start',
							label='start time',
							set_cmd='POWer:SWITching:GATE:TOFF:STARt {}',
							get_cmd='POWer:SWITching:GATE:TOFF:STARt?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('gate_off_stop',
							label='stop time',
							set_cmd='POWer:SWITching:GATE:TOFF:STOP {}',
							get_cmd='POWer:SWITching:GATE:TOFF:STOP?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('gate_on_start',
							label='start time',
							set_cmd='POWer:SWITching:GATE:TON:STARt {}',
							get_cmd='POWer:SWITching:GATE:TON:STARt?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('gate_on_stop',
							label='stop time',
							set_cmd='POWer:SWITching:GATE:TON:STOP {}',
							get_cmd='POWer:SWITching:GATE:TON:STOP?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('conduction_energy',
							label='conduction energy',
							get_cmd='POWer:SWITching:RESult:CONDuction:ENERgy?',
							get_parser=float)

		self.add_parameter('conduction_power',
							label='conduction power',
							get_cmd='POWer:SWITching:RESult:CONDuction:POWer?',
							get_parser=float)

		self.add_parameter('non_conduction_energy',
							label='non conduction energy',
							get_cmd='POWer:SWITching:RESult:NCONduction:ENERgy?',
							get_parser=float)

		self.add_parameter('non_conduction_power',
							label='non conduction power',
							get_cmd='POWer:SWITching:RESult:NCONduction:POWer?',
							get_parser=float)

		self.add_parameter('off_energy',
							label='turn off energy',
							get_cmd='POWer:SWITching:RESult:TOFF:ENERgy?',
							get_parser=float)

		self.add_parameter('off_power',
							label='turn off power',
							get_cmd='POWer:SWITching:RESult:TOFF:POWer?',
							get_parser=float)

		self.add_parameter('on_energy',
							label='turn on energy',
							get_cmd='POWer:SWITching:RESult:TON:ENERgy?',
							get_parser=float)

		self.add_parameter('on_power',
							label='turn on power',
							get_cmd='POWer:SWITching:RESult:TON:POWer?',
							get_parser=float)

		self.add_parameter('total_energy',
							label='total energy',
							get_cmd='POWer:SWITching:RESult:TOTal:ENERgy?',
							get_parser=float)

		self.add_parameter('total_power',
							label='total power',
							get_cmd='POWer:SWITching:RESult:TOTal:POWer?',
							get_parser=float)

		self.add_parameter('type',
							label='measurement type',
							set_cmd='POWer:SWITching:TYPE {}',
							get_cmd='POWer:SWITching:TYPE?',
							vals=vals.Enum('ENER', 'POW'),
							get_parser=str.rstrip)

	def execute(self): self.write('POWer:SWITching:EXECute')
	def waveform(self): self.write('POWer:SWITching:GATE:SWAVe')
	def add(self): self.write('POWer:SWITching:REPort:ADD')

class Transient(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('delay_time',
							label='delay time',
							get_cmd='POWer:TRANsient:RESult:DELay?',
							get_parser=float)

		self.add_parameter('overshoot',
							label='overshoot',
							get_cmd='POWer:TRANsient:RESult:OVERshoot?',
							get_parser=float)

		self.add_parameter('peak_time',
							label='peak time',
							get_cmd='POWer:TRANsient:RESult:PEAK:TIME?',
							get_parser=float)

		self.add_parameter('peak_value',
							label='peak value',
							get_cmd='POWer:TRANsient:RESult:PEAK:VALue?',
							get_parser=float)

		self.add_parameter('rise_time',
							label='rise time',
							get_cmd='POWer:TRANsient:RESult:RTIMe?',
							get_parser=float)

		self.add_parameter('settling_time',
							label='settling time',
							get_cmd='POWer:TRANsient:RESult:SETTlingtime?',
							get_parser=float)

		self.add_parameter('signal_high',
							label='signal high voltage value',
							set_cmd='POWer:TRANsient:SIGHigh {}',
							get_cmd='POWer:TRANsient:SIGHigh?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('signal_low',
							label='signal low voltage value',
							set_cmd='POWer:TRANsient:SIGLow {}',
							get_cmd='POWer:TRANsient:SIGLow?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('start_time',
							label='start time',
							set_cmd='POWer:TRANsient:STARt {}',
							get_cmd='POWer:TRANsient:STARt?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('stop_time',
							label='stop time',
							set_cmd='POWer:TRANsient:STOP {}',
							get_cmd='POWer:TRANsient:STOP?',
							vals=vals.Numbers(),
							get_parser=float)

	def execute(self): self.write('POWer:TRANsient:EXECute')
	def add(self): self.write('POWer:TRANsient:REPort:ADD')

# Mixed Signal Option

class Mixed_Signal_Channel(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		for i in range(1,2+1):
			logic_pod_module=Logic_Pod(self, f'logpod_pd{i}', i)
			self.add_submodule(f'logpod_pd{i}', logic_pod_module)

		for i in range(0,15+1):
			logic_log_module=Logic_Log(self, f'loglog_dg{i}', i)
			self.add_submodule(f'loglog_dg{i}', logic_log_module)

		for i in range(1,2+1):
			for j in range(1,50+1):
				parallel_bus_module=Parallel_Bus(self, f'bus_pa{i}_bus_bi{j}', i, j)
				self.add_submodule(f'bus_pa{i}_bus_bi{j}', parallel_bus_module)

		for i in range(1,2+1):
			for j in range(1,50+1):
				parallel_decode_module=Parallel_Decode(self, f'dec_pa{i}_dec_fr{j}', i, j)
				self.add_submodule(f'dec_pa{i}_dec_fr{j}', parallel_decode_module)

class Logic_Log(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, lognum):
		super().__init__(parent, name)

		self.add_parameter('maximum',
							label=f'log {lognum} maximum',
							get_cmd=f'DIGital{lognum}:CURRent:STATe:MAXimum?',
							get_parser=int)

		self.add_parameter('minimum',
							label=f'log {lognum} minimum',
							get_cmd=f'DIGital{lognum}:CURRent:STATe:MINimum?',
							get_parser=int)

		self.add_parameter('probe_enable',
							label=f'log {lognum} probe enable',
							get_cmd=f'DIGital{lognum}:PROBe:ENABle?',
							get_parser=str.rstrip)

		self.add_parameter('display',
							label=f'log {lognum} display state',
							set_cmd=f'DIGital{lognum}:DISPlay {{}}',
							get_cmd=f'DIGital{lognum}:DISPlay?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('technology',
							label=f'log {lognum} threshold mode',
							set_cmd=f'DIGital{lognum}:TECHnology {{}}',
							get_cmd=f'DIGital{lognum}:TECHnology?',
							vals=vals.Enum('TTL', 'ECL', 'CMOS', 'MAN'),
							get_parser=str.rstrip)

		self.add_parameter('threshold_coupling',
							label=f'log {lognum} threshold coupling',
							set_cmd=f'DIGital{lognum}:THCoupling {{}}',
							get_cmd=f'DIGital{lognum}:THCoupling?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('threshold_level',
							label=f'log {lognum} threshold level',
							set_cmd=f'DIGital{lognum}:THReshold {{}}',
							get_cmd=f'DIGital{lognum}:THReshold?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('hysteresis',
							label=f'log {lognum} hysteresis',
							set_cmd=f'DIGital{lognum}:HYSTeresis {{}}',
							get_cmd=f'DIGital{lognum}:HYSTeresis?',
							vals=vals.Enum('SMAL', 'MED', 'LARG'),
							get_parser=str.rstrip)

		self.add_parameter('deskew',
							label=f'log {lognum} deskew',
							set_cmd=f'DIGital{lognum}:DESKew {{}}',
							get_cmd=f'DIGital{lognum}:DESKew?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('size',
							label=f'log {lognum} vertical size',
							set_cmd=f'DIGital{lognum}:SIZE {{}}',
							get_cmd=f'DIGital{lognum}:SIZE?',
							vals=vals.Numbers(0.2,8),
							get_parser=float)

		self.add_parameter('position',
							label=f'log {lognum} vertical position',
							set_cmd=f'DIGital{lognum}:POSition {{}}',
							get_cmd=f'DIGital{lognum}:POSition?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('label',
							label=f'log {lognum} label',
							set_cmd=f'DIGital{lognum}:LABel {{}}',
							get_cmd=f'DIGital{lognum}:LABel?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('label_state',
							label=f'log {lognum} label state',
							set_cmd=f'DIGital{lognum}:LABel:STATe {{}}',
							get_cmd=f'DIGital{lognum}:LABel:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('data',
							label=f'log {lognum} data',
							get_cmd=f'DIGital{lognum}:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('header',
							label=f'log {lognum} header',
							get_cmd=f'DIGital{lognum}:DATA:HEADer?',
							get_parser=str.rstrip)

		self.add_parameter('data_points',
							label=f'log {lognum} data points',
							set_cmd=f'DIGital{lognum}:DATA:POINts {{}}',
							get_cmd=f'DIGital{lognum}:DATA:POINts?',
							vals=vals.Enum('DEF', 'MAX', 'DMAX'),
							get_parser=str.rstrip)

class Logic_Pod(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, podnum):
		super().__init__(parent, name)

		self.add_parameter('enable',
							label=f'pod {podnum} enable',
							get_cmd=f'LOGic{podnum}:PROBe:ENABle?',
							get_parser=int)

		self.add_parameter('maximum',
							label=f'pod {podnum} maximum',
							get_cmd=f'LOGic{podnum}:CURRent:STATe:MAXimum?',
							get_parser=int)

		self.add_parameter('minimum',
							label=f'pod {podnum} minimum',
							get_cmd=f'LOGic{podnum}:CURRent:STATe:MINimum?',
							get_parser=int)

		self.add_parameter('state',
							label=f'pod {podnum} state',
							set_cmd=f'LOGic{podnum}:STATe {{}}',
							get_cmd=f'LOGic{podnum}:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('type',
							label=f'pod {podnum} type',
							set_cmd=f'LOGic{podnum}:TYPE {{}}',
							get_cmd=f'LOGic{podnum}:TYPE?',
							vals=vals.Enum('SAMP', 'PDET'),
							get_parser=str.rstrip)

		self.add_parameter('data',
							label=f'pod {podnum} query data',
							get_cmd=f'LOGic{podnum}:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('header',
							label=f'pod {podnum} header',
							get_cmd=f'LOGic{podnum}:DATA:HEADer?',
							get_parser=str.rstrip)

		self.add_parameter('data_points',
							label=f'pod {podnum} data points',
							set_cmd=f'LOGic{podnum}:DATA:POINts {{}}',
							get_cmd=f'LOGic{podnum}:DATA:POINts?',
							vals=vals.Enum('DEF', 'MAX', 'DMAX'),
							get_parser=str.rstrip)

class Parallel_Bus(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, parnum, bitnum):
		super().__init__(parent, name)

		self.add_parameter('width',
							label=f'parallel {parnum} bus width',
							set_cmd=f'BUS{parnum}:PARallel:WIDTh {{}}',
							get_cmd=f'BUS{parnum}:PARallel:WIDTh?',
							vals=vals.Ints(1,4),
							get_parser=int)

		self.add_parameter('clocked_width',
							label=f'parallel {parnum} clocked bus width',
							set_cmd=f'BUS{parnum}:CPARallel:WIDTh {{}}',
							get_cmd=f'BUS{parnum}:CPARallel:WIDTh?',
							vals=vals.Ints(1,15),
							get_parser=int)

		self.add_parameter('data_source',
							label=f'parallel {parnum} bit {bitnum} data source',
							set_cmd=f'BUS{parnum}:PARallel:DATA{bitnum}:SOURce {{}}',
							get_cmd=f'BUS{parnum}:PARallel:DATA{bitnum}:SOURce?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

			
		self.add_parameter('clocked_source',
							label=f'parallel {parnum} bit {bitnum} clocked data source',
							set_cmd=f'BUS{parnum}:CPARallel:DATA{bitnum}:SOURce {{}}',
							get_cmd=f'BUS{parnum}:CPARallel:DATA{bitnum}:SOURce?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('clock_source',
							label=f'parallel {parnum} clock source',
							set_cmd=f'BUS{parnum}:CPARallel:CLOCk:SOURce {{}}',
							get_cmd=f'BUS{parnum}:CPARallel:CLOCk:SOURce?',
							vals=vals.Enum('D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15'),
							get_parser=str.rstrip)

		self.add_parameter('clock_slope',
							label=f'parallel {parnum} clock slope',
							set_cmd=f'BUS{parnum}:CPARallel:CLOCK:SLOPe {{}}',
							get_cmd=f'BUS{parnum}:CPARallel:CLOCK:SLOPe?',
							vals=vals.Enum('POS', 'NEG', 'EITH'),
							get_parser=str.rstrip)

		self.add_parameter('cs_enable',
							label=f'parallel {parnum} chip select enable',
							set_cmd=f'BUS{parnum}:CPARallel:CS:ENABle {{}}',
							get_cmd=f'BUS{parnum}:CPARallel:CS:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('cs_source',
							label=f'parallel {parnum} chip select source',
							set_cmd=f'BUS{parnum}:CPARallel:CS:SOURce {{}}',
							get_cmd=f'BUS{parnum}:CPARallel:CS:SOURce?',
							vals=vals.Enum('D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15'),
							get_parser=str.rstrip)

		self.add_parameter('cs_polarity',
							label=f'parallel {parnum} chip select polarity',
							set_cmd=f'BUS{parnum}:CPARallel:CS:POLarity {{}}',
							get_cmd=f'BUS{parnum}:CPARallel:CS:POLarity?',
							vals=vals.Enum('POS', 'NEG'),
							get_parser=str.rstrip)

class Parallel_Decode(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, parnum, framnum):
		super().__init__(parent, name)

		self.add_parameter('frame_count',
							label=f'parallel {parnum} frame count',
							get_cmd=f'BUS{parnum}:PARallel:FCOunt?',
							get_parser=str.rstrip)

		self.add_parameter('clocked_count',
							label=f'parallel {parnum} clocked frame count',
							get_cmd=f'BUS{parnum}:CPARallel:FCOunt?',
							get_parser=str.rstrip)

		self.add_parameter('frame_data',
							label=f'parallel {parnum} frame {framnum} data',
							get_cmd=f'BUS{parnum}:PARallel:FRAMe{framnum}:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('clocked_data',
							label=f'parallel {parnum} frame {framnum} clocked data',
							get_cmd=f'BUS{parnum}:CPARallel:FRAMe{framnum}:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('frame_state',
							label=f'parallel {parnum} frame {framnum} state',
							get_cmd=f'BUS{parnum}:PARallel:FRAMe{framnum}:STATe?',
							get_parser=str.rstrip)

		self.add_parameter('clocked_state',
							label=f'parallel {parnum} frame {framnum} clocked state',
							get_cmd=f'BUS{parnum}:CPARallel:FRAMe{framnum}:STATe?',
							get_parser=str.rstrip)

		self.add_parameter('frame_start',
							label=f'parallel {parnum} frame {framnum} start',
							get_cmd=f'BUS{parnum}:PARallel:FRAMe{framnum}:STARt?',
							get_parser=float)

		self.add_parameter('clocked_start',
							label=f'parallel {parnum} frame {framnum} clocked start',
							get_cmd=f'BUS{parnum}:CPARallel:FRAMe{framnum}:STARt?',
							get_parser=float)

		self.add_parameter('frame_stop',
							label=f'parallel {parnum} frame {framnum} stop',
							get_cmd=f'BUS{parnum}:PARallel:FRAMe{framnum}:STOP?',
							get_parser=float)

		self.add_parameter('clocked_stop',
							label=f'parallel {parnum} frame {framnum} clocked stop',
							get_cmd=f'BUS{parnum}:CPARallel:FRAMe{framnum}:STOP?',
							get_parser=float)

# Signal Generation

class Signal_Generation_Channel(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		function_generator_module=Function_Generator(self, 'function_generator')
		self.add_submodule('function_generator', function_generator_module)

		arbitrary_waveform_module=Arbitrary_Waveform(self, 'arbitrary_waveform')
		self.add_submodule('arbitrary_waveform', arbitrary_waveform_module)

		burst_function_module=Burst_Function(self, 'burst_function')
		self.add_submodule('burst_function', burst_function_module)

		modulation_function_module=Modulation_Function(self, 'modulation_function')
		self.add_submodule('modulation_function', modulation_function_module)

		sweep_function_module=Sweep_Function(self, 'sweep_function')
		self.add_submodule('sweep_function', sweep_function_module)

		pattern_general_module=Pattern_General(self, 'pattern_general')
		self.add_submodule('pattern_general', pattern_general_module)

		pattern_square_module=Pattern_Square(self, 'pattern_square')
		self.add_submodule('pattern_square', pattern_square_module)

		counter_pattern_module=Counter_Pattern(self, 'counter_pattern')
		self.add_submodule('counter_pattern', counter_pattern_module)

		pattern_arbitrary_module=Pattern_Arbitrary(self, 'pattern_arbitrary')
		self.add_submodule('pattern_arbitrary', pattern_arbitrary_module)

		pattern_pwm_module=Pattern_PWM(self, 'pattern_pwm')
		self.add_submodule('pattern_pwm', pattern_pwm_module)

		for i in range(0,3+1):
			pattern_manual_module=Pattern_Manual(self, f'man_pn{i}', i)
			self.add_submodule(f'man_pn{i}', pattern_manual_module)

class Arbitrary_Waveform(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('source',
							label='source',
							set_cmd='WGENerator:ARBitrary:SOURce {}',
							get_cmd='WGENerator:ARBitrary:SOURce?',
							vals=vals.Enum('CH1', 'CH2', 'CH3', 'CH4'),
							get_parser=str.rstrip)

		self.add_parameter('start_time',
							label='start time',
							set_cmd='WGENerator:ARBitrary:RANGe:START {}',
							get_cmd='WGENerator:ARBitrary:RANGe:START?',
							vals=vals.Numbers(),
							unit='s',
							get_parser=float)

		self.add_parameter('stop_time',
							label='stop time',
							set_cmd='WGENerator:ARBitrary:RANGe:STOP {}',
							get_cmd='WGENerator:ARBitrary:RANGe:STOP?',
							vals=vals.Numbers(),
							unit='s',
							get_parser=float)

		self.add_parameter('file_path',
							label='file path',
							set_cmd='WGENerator:ARBitrary:FILE:NAME {}',
							get_cmd='WGENerator:ARBitrary:FILE:NAME?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('visible',
							label='visible',
							set_cmd='WGENerator:ARBitrary:VISible {}',
							get_cmd='WGENerator:ARBitrary:VISible?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

	def update(self): self.write('WGENerator:ARBitrary:UPDate')
	def open(self): self.write('WGENerator:ARBitrary:FILE:OPEN')

class Burst_Function(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('idle_time',
							label='idle time',
							set_cmd='WGENerator:BURSt:ITIMe {}',
							get_cmd='WGENerator:BURSt:ITIMe?',
							vals=vals.Numbers(28e-9,17),
							unit='s',
							get_parser=float)

		self.add_parameter('cycles',
							label='number of cycles',
							set_cmd='WGENerator:BURSt:NCYCle {}',
							get_cmd='WGENerator:BURSt:NCYCle?',
							vals=vals.Ints(1,1023),
							get_parser=int)

		self.add_parameter('mode',
							label='trigger mode',
							set_cmd='WGENerator:BURSt:TRIGger:MODE {}',
							get_cmd='WGENerator:BURSt:TRIGger:MODE?',
							vals=vals.Enum('CONT', 'SING'),
							get_parser=str.rstrip)

		self.add_parameter('start_phase',
							label='start phase',
							set_cmd='WGENerator:BURSt:PHASe {}',
							get_cmd='WGENerator:BURSt:PHASe?',
							vals=vals.Numbers(0,360),
							get_parser=float)

		self.add_parameter('state',
							label='burst state',
							set_cmd='WGENerator:BURSt:STATe {}',
							get_cmd='WGENerator:BURSt:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

	def single(self): self.write('WGENerator:BURSt:TRIGger:SINGle')

class Counter_Pattern(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('frequency',
							label='frequency',
							set_cmd='PGENerator:PATTern:COUNter:FREQuency {}',
							get_cmd='PGENerator:PATTern:COUNter:FREQuency?',
							vals=vals.Numbers(2.380952425301e-2,2.5e7),
							unit='Hz',
							get_parser=float)

		self.add_parameter('count_direction',
							label='count direction',
							set_cmd='PGENerator:PATTern:COUNter:DIRection {}',
							get_cmd='PGENerator:PATTern:COUNter:DIRection?',
							vals=vals.Enum('UPW', 'DOWN'),
							get_parser=str.rstrip)

class Function_Generator(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('function',
							label='function',
							set_cmd='WGENerator:FUNCtion {}',
							get_cmd='WGENerator:FUNCtion?',
							vals=vals.Enum('DC', 'SIN', 'SQU', 'PULS', 'TRI', 'RAMP', 'SINC', 'ARB', 'EXP'),
							get_parser=str.rstrip)

		self.add_parameter('amplitude',
							label='amplitude',
							set_cmd='WGENerator:VOLTage {}',
							get_cmd='WGENerator:VOLTage?',
							vals=vals.Numbers(6e-2,6e0),
							unit='Vpp',
							get_parser=float)

		self.add_parameter('offset',
							label='offset',
							set_cmd='WGENerator:VOLTage:OFFSet {}',
							get_cmd='WGENerator:VOLTage:OFFSet?',
							vals=vals.Numbers(-3e0,3e0),
							unit='V',
							get_parser=float)

		self.add_parameter('frequency',
							label='frequency',
							set_cmd='WGENerator:FREQuency {}',
							get_cmd='WGENerator:FREQuency?',
							vals=vals.Numbers(),
							unit='Hz',
							get_parser=float)

		self.add_parameter('duty_cycle',
							label='pulse duty cycle',
							set_cmd='WGENerator:FUNCtion:PULSe:DCYCle {}',
							get_cmd='WGENerator:FUNCtion:PULSe:DCYCle?',
							vals=vals.Numbers(1e1,9e1),
							unit='%',
							get_parser=float)

		self.add_parameter('symmetry',
							label='symmetry',
							set_cmd='WGENerator:TRIangle:SYMMetry {}',
							get_cmd='WGENerator:TRIangle:SYMMetry?',
							vals=vals.Ints(1,99),
							get_parser=int)

		self.add_parameter('exponential_polarity',
							label='exponential polarity',
							set_cmd='WGENerator:FUNCtion:EXPonential:POLarity {}',
							get_cmd='WGENerator:FUNCtion:EXPonential:POLarity?',
							vals=vals.Enum('POS', 'NEG'),
							get_parser=str.rstrip)

		self.add_parameter('ramp_polarity',
							label='ramp polarity',
							set_cmd='WGENerator:FUNCtion:RAMP:POLarity {}',
							get_cmd='WGENerator:FUNCtion:RAMP:POLarity?',
							vals=vals.Enum('POS', 'NEG'),
							get_parser=str.rstrip)

		self.add_parameter('absolute_noise',
							label='absolute noise',
							set_cmd='WGENerator:NOISe:ABSolute {}',
							get_cmd='WGENerator:NOISe:ABSolute?',
							vals=vals.Numbers(),
							unit='V',
							get_parser=float)

		self.add_parameter('relative_noise',
							label='relative noise',
							set_cmd='WGENerator:NOISe:RELative {}',
							get_cmd='WGENerator:NOISe:RELative?',
							vals=vals.Numbers(),
							unit='%',
							get_parser=float)

		self.add_parameter('load',
							label='user load',
							set_cmd='WGENerator:OUTPut:LOAD {}',
							get_cmd='WGENerator:OUTPut:LOAD?',
							vals=vals.Enum('HIGH', 'R50'),
							get_parser=str.rstrip)

		self.add_parameter('output',
							label='output state',
							set_cmd='WGENerator:OUTPut:ENABle {}',
							get_cmd='WGENerator:OUTPut:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

class Modulation_Function(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('enable',
							label='enable',
							set_cmd='WGENerator:MODulation:ENABLE {}',
							get_cmd='WGENerator:MODulation:ENABLE?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('function',
							label='function',
							set_cmd='WGENerator:MODulation:FUNCtion {}',
							get_cmd='WGENerator:MODulation:FUNCtion?',
							vals=vals.Enum('SIN', 'SQU', 'TRI', 'RAMP'),
							get_parser=str.rstrip)

		self.add_parameter('type',
							label='modulation type',
							set_cmd='WGENerator:MODulation:TYPE {}',
							get_cmd='WGENerator:MODulation:TYPE?',
							vals=vals.Enum('AM', 'FM', 'ASK', 'FSK'),
							get_parser=str.rstrip)

		self.add_parameter('AM_frequency',
							label='AM frequency',
							set_cmd='WGENerator:MODulation:AM:FREQuency {}',
							get_cmd='WGENerator:MODulation:AM:FREQuency?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('AM_depth',
							label='AM depth',
							set_cmd='WGENerator:MODulation:AM:DEPTh {}',
							get_cmd='WGENerator:MODulation:AM:DEPTh?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('FM_frequency',
							label='FM frequency',
							set_cmd='WGENerator:MODulation:FM:FREQuency {}',
							get_cmd='WGENerator:MODulation:FM:FREQuency?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('FM_deviation',
							label='FM deviation',
							set_cmd='WGENerator:MODulation:FM:DEViation {}',
							get_cmd='WGENerator:MODulation:FM:DEViation?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('ASK_frequency',
							label='ASK frequency',
							set_cmd='WGENerator:MODulation:ASK:FREQuency {}',
							get_cmd='WGENerator:MODulation:ASK:FREQuency?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('ASK_depth',
							label='ASK depth',
							set_cmd='WGENerator:MODulation:ASK:DEPTh {}',
							get_cmd='WGENerator:MODulation:ASK:DEPTh?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('FSK_hopping',
							label='FSK hopping frequency',
							set_cmd='WGENerator:MODulation:FSK:HFREquency {}',
							get_cmd='WGENerator:MODulation:FSK:HFREquency?',
							vals=vals.Numbers(),
							unit='Hz',
							get_parser=float)

		self.add_parameter('FSK_rate',
							label='FSK rate',
							set_cmd='WGENerator:MODulation:FSK:RATE {}',
							get_cmd='WGENerator:MODulation:FSK:RATE?',
							vals=vals.Numbers(0.1,1e6),
							unit='Hz',
							get_parser=float)

		self.add_parameter('ramp_polarity',
							label='ramp polarity',
							set_cmd='WGENerator:MODulation:RAMP:POLarity {}',
							get_cmd='WGENerator:MODulation:RAMP:POLarity?',
							vals=vals.Enum('POS', 'NEG'),
							get_parser=str.rstrip)

class Pattern_Arbitrary(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('trigger_mode',
							label='trigger mode',
							set_cmd='PGENerator:PATTern:TRIGger:MODE {}',
							get_cmd='PGENerator:PATTern:TRIGger:MODE?',
							vals=vals.Enum('CONT', 'SING'),
							get_parser=str.rstrip)

		self.add_parameter('data_pattern',
							label='data pattern',
							set_cmd='PGENerator:PATTern:ARBitrary:DATA:SET {}',
							get_cmd='PGENerator:PATTern:ARBitrary:DATA:SET?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('pattern_length',
							label='pattern length',
							set_cmd='PGENerator:PATTern:ARBitrary:DATA:LENGth {}',
							get_cmd='PGENerator:PATTern:ARBitrary:DATA:LENGth?',
							vals=vals.Ints(1,2048),
							get_parser=int)

		self.add_parameter('append',
							label='data append',
							set_cmd='PGENerator:PATTern:ARBitrary:DATA:APPend {}',
							get_cmd='PGENerator:PATTern:ARBitrary:DATA:APPend?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('append_or',
							label='or append',
							set_cmd='PGENerator:PATTern:ARBitrary:DATA:APPend:BOR {}',
							get_cmd='PGENerator:PATTern:ARBitrary:DATA:APPend:BOR?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('append_and',
							label='and append',
							set_cmd='PGENerator:PATTern:ARBitrary:DATA:APPend:BAND {}',
							get_cmd='PGENerator:PATTern:ARBitrary:DATA:APPend:BAND?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('append_index',
							label='index append',
							set_cmd='PGENerator:PATTern:ARBitrary:DATA:APPend:INDex {}',
							get_cmd='PGENerator:PATTern:ARBitrary:DATA:APPend:INDex?',
							vals=vals.Ints(),
							get_parser=int)

		self.add_parameter('sample_time',
							label='sample time',
							set_cmd='PGENerator:PATTern:STIMe {}',
							get_cmd='PGENerator:PATTern:STIMe?',
							vals=vals.Numbers(2e-8,4.2e1),
							unit='s',
							get_parser=float)

		self.add_parameter('idle_time',
							label='idle time',
							set_cmd='PGENerator:PATTern:ITIMe {}',
							get_cmd='PGENerator:PATTern:ITIMe?',
							vals=vals.Numbers(2e-8,4.2e1),
							unit='s',
							get_parser=float)

		self.add_parameter('burst_state',
							label='burst state',
							set_cmd='PGENerator:PATTern:BURSt:STATe {}',
							get_cmd='PGENerator:PATTern:BURSt:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('pattern_cycles',
							label='pattern cycles',
							set_cmd='PGENerator:PATTern:BURSt:NCYCle {}',
							get_cmd='PGENerator:PATTern:BURSt:NCYCle?',
							vals=vals.Ints(1,4096),
							get_parser=int)

	def single(self): self.write('PGENerator:PATTern:TRIGger:SINGle')

class Pattern_General(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('function',
							label='pattern function',
							set_cmd='PGENerator:FUNCtion {}',
							get_cmd='PGENerator:FUNCtion?',
							vals=vals.Enum('SQU', 'COUN', 'ARB', 'SPI', 'I2C', 'UART', 'CAN', 'LIN', 'MAN', 'I2S', 'TDM', 'TPWM', 'PWM', 'LEDP'),
							get_parser=str.rstrip)

		self.add_parameter('state',
							label='pattern state',
							set_cmd='PGENerator:PATTern:STATe {}',
							get_cmd='PGENerator:PATTern:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('output_voltage',
							label='output voltage',
							set_cmd='PGENerator:OUTPut:VOLTage {}',
							get_cmd='PGENerator:OUTPut:VOLTage?',
							vals=vals.Numbers(),
							unit='Hz',
							get_parser=float)

		self.add_parameter('external_slope',
							label='external slope',
							set_cmd='PGENerator:PATTern:TRIGger:EXTern:SLOPe {}',
							get_cmd='PGENerator:PATTern:TRIGger:EXTern:SLOPe?',
							vals=vals.Enum('POS', 'NEG', 'EITH'),
							get_parser=str.rstrip)

class Pattern_Manual(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, pinnum):
		super().__init__(parent, name)

		self.add_parameter('state',
							label=f'pin {pinnum} manual state',
							set_cmd=f'PGENerator:MANual:STATe{pinnum} {{}}',
							get_cmd=f'PGENerator:MANual:STATe{pinnum}?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

class Pattern_PWM(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('duty_cycle',
							label='duty cycle',
							set_cmd='PGENerator:PATTern:PWM:DCYCle {}',
							get_cmd='PGENerator:PATTern:PWM:DCYCle?',
							vals=vals.Ints(1,99),
							unit='%',
							get_parser=int)

		self.add_parameter('direction',
							label='motor rotation direction',
							set_cmd='PGENerator:PATTern:PWM:DIRection {}',
							get_cmd='PGENerator:PATTern:PWM:DIRection?',
							vals=vals.Enum('POS', 'NEG'),
							get_parser=str.rstrip)

		self.add_parameter('enable',
							label='motor enable',
							set_cmd='PGENerator:PATTern:PWM:ENABle {}',
							get_cmd='PGENerator:PATTern:PWM:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('blue_duty',
							label='blue duty cycle',
							set_cmd='PGENerator:PATTern:LED:BLUE {}',
							get_cmd='PGENerator:PATTern:LED:BLUE?',
							vals=vals.Ints(1,99),
							unit='%',
							get_parser=int)

		self.add_parameter('green_duty',
							label='green duty cycle',
							set_cmd='PGENerator:PATTern:LED:GREen {}',
							get_cmd='PGENerator:PATTern:LED:GREen?',
							vals=vals.Ints(1,99),
							unit='%',
							get_parser=int)

		self.add_parameter('red_duty',
							label='red duty cycle',
							set_cmd='PGENerator:PATTern:LED:RED {}',
							get_cmd='PGENerator:PATTern:LED:RED?',
							vals=vals.Ints(1,99),
							unit='%',
							get_parser=int)

		self.add_parameter('led_intensity',
							label='led intensity',
							set_cmd='PGENerator:PATTern:LED:INTens {}',
							get_cmd='PGENerator:PATTern:LED:INTens?',
							vals=vals.Ints(1,99),
							unit='%',
							get_parser=int)

class Pattern_Square(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('polarity',
							label='polarity',
							set_cmd='PGENerator:PATTern:SQUarewave:POLarity {}',
							get_cmd='PGENerator:PATTern:SQUarewave:POLarity?',
							vals=vals.Enum('NORM', 'INV'),
							get_parser=str.rstrip)

		self.add_parameter('duty_cycle',
							label='duty cycle',
							set_cmd='PGENerator:PATTern:SQUarewave:DCYCle {}',
							get_cmd='PGENerator:PATTern:SQUarewave:DCYCle?',
							vals=vals.Numbers(1e0,9.9e1),
							unit='%',
							get_parser=float)

		self.add_parameter('pattern_period',
							label='pattern period',
							set_cmd='PGENerator:PATTern:PERiod {}',
							get_cmd='PGENerator:PATTern:PERiod?',
							vals=vals.Numbers(),
							unit='s',
							get_parser=float)

		self.add_parameter('pattern_frequency',
							label='pattern frequency',
							set_cmd='PGENerator:PATTern:FREQuency {}',
							get_cmd='PGENerator:PATTern:FREQuency?',
							vals=vals.Numbers(),
							unit='Hz',
							get_parser=float)

class Sweep_Function(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('stop_frequency',
							label='stop frequency',
							set_cmd='WGENerator:SWEep:FEND {}',
							get_cmd='WGENerator:SWEep:FEND?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('start_frequency',
							label='start frequency',
							set_cmd='WGENerator:SWEep:FSTart {}',
							get_cmd='WGENerator:SWEep:FSTart?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('sweep_time',
							label='sweep time',
							set_cmd='WGENerator:SWEep:TIME {}',
							get_cmd='WGENerator:SWEep:TIME?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('sweep_type',
							label='sweep type',
							set_cmd='WGENerator:SWEep:TYPE {}',
							get_cmd='WGENerator:SWEep:TYPE?',
							vals=vals.Enum('LIN', 'LOG', 'TRI'),
							get_parser=str.rstrip)

		self.add_parameter('enable',
							label='sweep enable',
							set_cmd='WGENerator:SWEep:ENABle {}',
							get_cmd='WGENerator:SWEep:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

# Status Reporting

class Status_Reporting_Channel(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		status_operation_module=Status_Operation(self, 'status_operation')
		self.add_submodule('status_operation', status_operation_module)

		status_questionable_condition_module=Status_Questionable_Condition(self, 'status_questionable_condition')
		self.add_submodule('status_questionable_condition', status_questionable_condition_module)

		status_questionable_enable_module=Status_Questionable_Enable(self, 'status_questionable_enable')
		self.add_submodule('status_questionable_enable', status_questionable_enable_module)

		status_questionable_event_module=Status_Questionable_Event(self, 'status_questionable_event')
		self.add_submodule('status_questionable_event', status_questionable_event_module)

		status_questionable_negative_module=Status_Questionable_Negative_Transition(self, 'status_questionable_negative')
		self.add_submodule('status_questionable_negative', status_questionable_negative_module)

		status_questionable_positive_module=Status_Questionable_Positive_Transition(self, 'status_questionable_positive')
		self.add_submodule('status_questionable_positive', status_questionable_positive_module)

class Status_Operation(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('condition',
							label='condition',
							get_cmd='STATus:OPERation:CONDition?',
							get_parser=int)

		self.add_parameter('enable',
							label='enable',
							set_cmd='STATus:OPERation:ENABle {}',
							get_cmd=';STATus:OPERation:ENABle?',
							vals=vals.Ints(1,65535),
							get_parser=int)

		self.add_parameter('negative_transition',
							label='negative transition',
							set_cmd='STATus:OPERation:NTRansition {}',
							get_cmd='STATus:OPERation:NTRansition?',
							vals=vals.Ints(1,65535),
							get_parser=int)

		self.add_parameter('positive_transition',
							label='positive transition',
							set_cmd='STATus:OPERation:PTRansition {}',
							get_cmd='STATus:OPERation:PTRansition?',
							vals=vals.Ints(1,65535),
							get_parser=int)

		self.add_parameter('event',
							label='event',
							get_cmd='STATus:OPERation:EVENt?',
							get_parser=int)

class Status_Questionable_Condition(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('condition',
							label='condition',
							get_cmd='STATus:QUEStionable:CONDition?',
							get_parser=int)

		self.add_parameter('condition_overload',
							label='overload condition',
							get_cmd='STATus:QUEStionable:COVerload:CONDition?',
							get_parser=int)

		self.add_parameter('condition_state',
							label='state condition',
							get_cmd='STATus:QUEStionable:ADCState:CONDition?',
							get_parser=int)

		self.add_parameter('condition_limit',
							label='limit condition',
							get_cmd='STATus:QUEStionable:LIMit:CONDition?',
							get_parser=int)

		self.add_parameter('condition_mask',
							label='mask condition',
							get_cmd='STATus:QUEStionable:MASK:CONDition?',
							get_parser=int)

	def preset(self): self.write('STATus:PRESet')

class Status_Questionable_Enable(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('enable',
							label='enable',
							set_cmd='STATus:QUEStionable:ENABle {}',
							get_cmd='STATus:QUEStionable:ENABle?',
							vals=vals.Ints(0,65535),
							get_parser=int)

		self.add_parameter('overload_enable',
							label='overload enable',
							set_cmd='STATus:QUEStionable:COVerload:ENABle {}',
							get_cmd='STATus:QUEStionable:COVerload:ENABle?',
							vals=vals.Ints(0,65535),
							get_parser=int)

		self.add_parameter('state_enable',
							label='state enable',
							set_cmd='STATus:QUEStionable:ADCState:ENABle {}',
							get_cmd='STATus:QUEStionable:ADCState:ENABle?',
							vals=vals.Ints(0,65535),
							get_parser=int)

		self.add_parameter('limit_enable',
							label='limit enable',
							set_cmd='STATus:QUEStionable:LIMit:ENABle {}',
							get_cmd='STATus:QUEStionable:LIMit:ENABle?',
							vals=vals.Ints(0,65535),
							get_parser=int)

		self.add_parameter('mask_enable',
							label='mask enable',
							set_cmd='STATus:QUEStionable:MASK:ENABle {}',
							get_cmd='STATus:QUEStionable:MASK:ENABle?',
							vals=vals.Ints(0,65535),
							get_parser=int)

class Status_Questionable_Event(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('event',
							label='event',
							get_cmd='STATus:QUEStionable:EVENt?',
							get_parser=int)

		self.add_parameter('event_overload',
							label='overload event',
							get_cmd='STATus:QUEStionable:COVerload:EVENt?',
							get_parser=int)

		self.add_parameter('event_state',
							label='state event',
							get_cmd='STATus:QUEStionable:ADCState:EVENt?',
							get_parser=int)

		self.add_parameter('event_limit',
							label='limit event',
							get_cmd='STATus:QUEStionable:LIMit:EVENt?',
							get_parser=int)

		self.add_parameter('event_mask',
							label='mask event',
							get_cmd='STATus:QUEStionable:MASK:EVENt?',
							get_parser=int)

class Status_Questionable_Negative_Transition(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('transition',
							label='transition',
							set_cmd='STATus:QUEStionable:NTRansition {}',
							get_cmd='STATus:QUEStionable:NTRansition?',
							vals=vals.Ints(0,65535),
							get_parser=int)

		self.add_parameter('overload',
							label='overload',
							set_cmd='STATus:QUEStionable:COVerload:NTRansition {}',
							get_cmd='STATus:QUEStionable:COVerload:NTRansition?',
							vals=vals.Ints(0,65535),
							get_parser=int)

		self.add_parameter('state',
							label='state',
							set_cmd='STATus:QUEStionable:ADCState:NTRansition {}',
							get_cmd='STATus:QUEStionable:ADCState:NTRansition?',
							vals=vals.Ints(0,65535),
							get_parser=int)

		self.add_parameter('limit',
							label='limit',
							set_cmd='STATus:QUEStionable:LIMit:NTRansition {}',
							get_cmd='STATus:QUEStionable:LIMit:NTRansition?',
							vals=vals.Ints(0,65535),
							get_parser=int)

		self.add_parameter('mask',
							label='mask',
							set_cmd='STATus:QUEStionable:MASK:NTRansition {}',
							get_cmd='STATus:QUEStionable:MASK:NTRansition?',
							vals=vals.Ints(0,65535),
							get_parser=int)

class Status_Questionable_Positive_Transition(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('transition',
							label='transition',
							set_cmd='STATus:QUEStionable:PTRansition {}',
							get_cmd='STATus:QUEStionable:PTRansition?',
							vals=vals.Ints(0,65535),
							get_parser=int)

		self.add_parameter('overload',
							label='overload',
							set_cmd='STATus:QUEStionable:COVerload:PTRansition {}',
							get_cmd='STATus:QUEStionable:COVerload:PTRansition?',
							vals=vals.Ints(0,65535),
							get_parser=int)

		self.add_parameter('state',
							label='state',
							set_cmd='STATus:QUEStionable:ADCState:PTRansition {}',
							get_cmd='STATus:QUEStionable:ADCState:PTRansition?',
							vals=vals.Ints(0,65535),
							get_parser=int)

		self.add_parameter('limit',
							label='limit',
							set_cmd='STATus:QUEStionable:LIMit:PTRansition {}',
							get_cmd='STATus:QUEStionable:LIMit:PTRansition?',
							vals=vals.Ints(0,65535),
							get_parser=int)

		self.add_parameter('mask',
							label='mask',
							set_cmd='STATus:QUEStionable:MASK:PTRansition {}',
							get_cmd='STATus:QUEStionable:MASK:PTRansition?',
							vals=vals.Ints(0,65535),
							get_parser=int)

class RS_RTM3000(VisaInstrument):
	'''
	RS_RTM3000 QCoDes driver
	Structure:
		Instrument-
			-Common
			-Waveform_Setup_Channel-
					-Acquisition
					-Horizontal
					-Probe_Active
					-Probe_Meter
					-Probe_Passive
					-Vertical
					-Waveform
					-Waveform_Data
			-Trigger_Channel-
					-Edge
					-Edge_AB
					-Event
					-Pattern
					-Risetime
					-Runt
					-Timeout
					-Trigger
					-Video
					-Width
			-Waveform_Analysis_Channel-
					-Acquire
					-Export
					-Export_Bus
					-Export_Channel
					-Export_Digital
					-Export-Pod
					-History_Bus
					-History_Channel
					-History_Digital
					-History_Math
					-History_Pod
					-History_Spectrum
					-Math
					-Reference
					-Search
					-Search_Dataclock
					-Search_Edge
					-Search_Measure
					-Search_Pattern
					-Search_Results
					-Search_Risetime
					-Search_Runt
					-Search_Width
					-Search_Window
					-Timestamp_Bus
					-Timestamp_Channel
					-Timestamp_Digital
					-Timestamp_Math
					-Timestamp_Pod
					-Timestamp_Spectrum
					-Zoom
			-Measurements_Channel-
					-Cursor
					-Cursor_Line
					-Measurement_Automatic
					-Measurement_Gate
					-Measurement_Quick
					-Measurement_Results
					-Meausrement_Statistics
					-Reference_Levels
			-Applications_Channel-
					-Bode_Marker
					-Bode_Plot
					-Bode_Settings
					-Digital_Voltmeter
					-Display
					-Frequency
					-General
					-Mask
					-Mask_Test
					-Mask_Violation
					-Peak_List
					-Peak_List_Result
					-Reference_Marker
					-Spectrogram
					-Time
					-Trigger_Counter
					-Waveform_Data_Query
					-Waveform_Setting
					-XY_Waveforms
			-Documenting_Channel-
					-Analog
					-Format
					-Logic_Channel
					-Logic_Digital
					-Logic_Mask
					-Logic_Math
					-Logic_Pod
					-Logic_Reference
					-Mask_Data
					-Mass_Memory
					-Reference_Waveform
					-Screenshot
					-Waveform_Export
			-General_Channel-
					-Display_Settings
					-Firmware_Update
					-LAN_Settings
					-System_Settings
					-Trigger_Out
			-Serial_Bus_Channel-
					-ARINC_Config
					-ARINC_Decode
					-ARINC_Search
					-ARINC_Trigger
					-Audio_Config
					-Audio_Decode
					-Audio_Decode_TDM
					-Audio_Trigger
					-Bus_General
					-CAN
					-CAN_Decode
					-CAN_Search
					-CAN_Trigger
					-General_Bus
					-Inter_Integrated_Config
					-Inter_Integrated_Decode
					-Inter_Integrated_Trigger
					-LIN_Config
					-LIN_Decode
					-LIN_Search
					-LIN_Trigger
					-MIL_Config
					-MIL_Decode
					-MIL_Search
					-MIL_Trigger
					-SPI
					-SPI_Decode
					-SPI_Trigger
					-SSPI
					-UART
					-UART_Decode
					-UART_Trigger
			-Power_Analysis_Channel-
					-Power_Consumption
					-Power_Dynamic
					-Power_Efficiency
					-Power_General
					-Power_Harmonics
					-Power_Inrush
					-Power_Modulation
					-Power_Report
					-Power_Ripple_Deviation
					-Power_Ripple_Frequency
					-Power_Ripple_Lpeak
					-Power_Ripple_Mean
					-Power_Ripple_Nduty
					-Power_Ripple_Pduty
					-Power_Ripple_Peak
					-Power_Ripple_Period
					-Power_Ripple_Upeak
					-Power_State
					-Power_Quality_Actual
					-Power_Quality_Average
					-Power_Quality_Deviation
					-Power_Quality_Negative
					-Power_Quality_Positive
					-Power_Quality_Waveform
					-Ripple-result_Frequency
					-Ripple-result_Mean
					-Ripple-result_Nduty
					-Ripple-result_Pduty
					-Ripple-result_Peak
					-Ripple-result_Period
					-Ripple-result_Deviation
					-Slew_Rate
					-Slewrate_Lpeak
					-Slewrate_Upeak
					-SOA
					-Spectrum
					-Switching
					-Transient
			-Mixed_Signal_Channel-
					-Logic_Log
					-Logic_Pod
					-Parallel_Bus
					-Parallel_Decode
			-Signal_Generation_Channel-
					-Arbitrary_Waveform
					-Burst_Function
					-Counter_Pattern
					-Function_Generator
					-Modulation_Function
					-Pattern_Arbitrary
					-Pattern_General
					-Pattern_PWM
					-Pattern_Square
					-Sweep_Function
			-Status_Reporting_Channel-
					-Status_Operation
					-Status_Questionable_Condition
					-Status_Questionable_Enable
					-Status_Questionable_Event
					-Status_Questionable_Negative_Transition
					-Status_Questionable_Positive_Transition
	'''
	def __init__(self, name, address, **kwargs):
		kwargs["device_clear"] = False
		super().__init__(name, address, **kwargs)

		common_module=Common(self, 'common')
		self.add_submodule('common', common_module)

		waveform_setup_module=Waveform_Setup_Channel(self, 'waveform_setup_module')
		self.add_submodule('waveform_setup_module', waveform_setup_module)

		trigger_channel_module=Trigger_Channel(self, 'trigger_channel')
		self.add_submodule('trigger_channel', trigger_channel_module)

		waveform_analysis_module=Waveform_Analysis_Channel(self, 'waveform_analysis')
		self.add_submodule('waveform_analysis', waveform_analysis_module)

		measurements_channel_module=Measurements_Channel(self, 'measurements_channel')
		self.add_submodule('measurements_channel', measurements_channel_module)

		applications_channel_module=Applications_Channel(self, 'applications_channel')
		self.add_submodule('applications_channel', applications_channel_module)

		documenting_channel_module=Documenting_Channel(self, 'documenting_channel')
		self.add_submodule('documenting_channel', documenting_channel_module)

		general_channel_module=General_Channel(self, 'general_channel')
		self.add_submodule('general_channel', general_channel_module)

		serial_bus_module=Serial_Bus_Channel(self, 'serial_bus_channel')
		self.add_submodule('serial_bus_channel', serial_bus_module)

		power_analysis_module=Power_Analysis_Channel(self, 'power_analysis_channel')
		self.add_submodule('power_analysis_channel', power_analysis_module)

		mixed_signal_module=Mixed_Signal_Channel(self, 'mixed_signal_channel')
		self.add_submodule('mixed_signal_channel', mixed_signal_module)

		signal_generation_module=Signal_Generation_Channel(self, 'signal_generation_channel')
		self.add_submodule('signal_generation_channel', signal_generation_module)

		status_reporting_module=Status_Reporting_Channel(self, 'status_reporting_channel')
		self.add_submodule('status_reporting_channel', status_reporting_module)
