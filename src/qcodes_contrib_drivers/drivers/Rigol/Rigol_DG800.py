'''
Driver for Rigol DG800 waveform generator

Written by Ben Mowbray (http://wp.lancs.ac.uk/laird-group/)

Examples:

	***Setting up and testing instrument***

	$ from qcodes.instrument_drivers.rigol.Rigol_DG800 import RigolDG800
	$ dg_1 = RigolDG800('r_800_1', 'USB0::0x1AB1::0x0643::DG8A233804647::0::INSTR')
	$ dg_1.identify()	# Returns name of instrument
	$ dg_1.ch1.impedance(5) # Sets impedance of channel 1
	$ dg_1.ch1.sweep.return_time(200) # Sets return time of sweep 

'''
from qcodes import VisaInstrument
from qcodes import validators as vals
from qcodes.instrument.channel import InstrumentChannel
from qcodes.instrument.base import Instrument

def _apply_parser(msg: str):
	output=list(map(_to_float, msg.split(',')))
	return {'function': output[0],
			'frequency': output[1],
			'amplitude': output[0],
			'offset': output[2],
			'phase': output[3]
			}

def _to_float(msg: str):
	try:
		return float(msg)
	except:
		return msg

def _int_parser(msg: str):
	return int(float(msg.rstrip()))

class Counter(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		# COUNTER MENU

		self.add_parameter('coupling',
							label='counter coupling',
							set_cmd=':COUNter:COUPling {}',
							get_cmd=':COUNter:COUPling?',
							vals=vals.Enum('AC', 'DC'),
							get_parser=str.rstrip)

		self.add_parameter('gate_time',
							label='counter gate time',
							set_cmd=':COUNter:GATEtime {}',
							get_cmd=':COUNter:GATEtime?',
							vals=vals.Enum('USER1', 'USER2', 'USER3', 'USER4', 'USER5', 'USER6'),
							get_parser=str.rstrip)

		self.add_parameter('hf_rejection',
							label='high frequency rejection',
							set_cmd=':COUNter:HF {}',
							get_cmd=':COUNter:HF?',
							vals=vals.Enum('ON', 'OFF'),
							get_parser=str.rstrip)
							
		self.add_parameter('level',
							label='counter trigger level',
							set_cmd=':COUNter:LEVEl {}',
							get_cmd=':COUNter:LEVEl?',
							vals=vals.MultiType(vals.Enum('MIN', 'MAX'), vals.Numbers(-2.5,2.5)),
							unit='V',
							get_parser=float)

		self.add_parameter('measure',
							label='counter measurements',
							get_cmd=':COUNter:MEASure?',
							get_parser=float)

		self.add_parameter('sensitive',
							label='counter trigger sensitivity',
							set_cmd=':COUNter:SENSitive {}',
							get_cmd=':COUNter:SENSitive?',
							vals=vals.Enum('LOW', 'HIG'),
							get_parser=str.rstrip)

		self.add_parameter('state',
							label='counter status',
							set_cmd=':COUNter:STATe {}',
							get_cmd=':COUNter:STATe?',
							vals=vals.Enum('ON', 'OFF', 'RUN', 'STOP', 'SINGLE'),
							get_parser=str.rstrip)

		self.add_parameter('stats_state',
							label='statistics state',
							set_cmd=':COUNter:STATIstics:STATe {}',
							get_cmd=':COUNter:STATIstics:STATe?',
							vals=vals.Enum('ON', 'OFF'),
							get_parser=str.rstrip)

	def clear(self): self.write(':COUNter:STATIstics:CLEAr')
	def counter(self): self.write(':COUNter:AUTO')

class Display(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('brightness',
						   label='Screen brightness',
						   set_cmd=':DISPlay:BRIGhtness {}',
						   get_cmd=':DISPlay:BRIGhtness?',
						   vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Ints(1, 100)),
						   get_parser=_int_parser,
						   unit='%')
		
		self.add_parameter('screensaver_state',
						   label='Screen saver state',
						   set_cmd=':DISPlay:SAVer:STATe {}',
						   get_cmd=':DISPlay:SAVer:STATe?',
						   get_parser=str.rstrip,
						   vals=vals.Enum('ON', 'OFF'),
						   docstring='Shows screensaver after inactive for 15 minutes, black after 30 minutes'
						   )

	def screensaver(self): self.write(':DISPlay:SAVer:IMMediate')

class License(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('clear',
							label='clear option',
							set_cmd=':LICense:CLEAR {}',
							vals=vals.Enum('DCH', 'ARB' 'ALL'))

		self.add_parameter('state',
							label='installation state query',
							get_cmd=':LICense:STATe?',
							get_parser=str.rstrip)

		self.add_parameter('install',
							label='install license',
							set_cmd=':LICense:INSTall {}',
							vals=vals.Strings())

		self.add_parameter('set',
							label='set license',
							set_cmd=':LICense:SET {}',
							vals=vals.Strings())

class MassMemory(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('cd',
							label='current directory',
							set_cmd=':MMEMory:CDIRectory "{}"',
							get_cmd=':MMEMory:CDIRectory?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('copy',
							label='copy file from current directory',
							set_cmd=':MMEMory:COPY "{}"',
							vals=vals.Strings())

		self.add_parameter('delete',
							label='delete from current directory',
							set_cmd=':MMEMory:DELete "{}"',
							vals=vals.Strings())

		self.add_parameter('create_file',
							label='create file in current directory',
							set_cmd=':MMEMory:DOWNload:FNAMe "{}"',
							vals=vals.Strings())

		self.add_parameter('upload_to_file',
							label='upload to current file',
							set_cmd=':MMEMory:DOWNload:DATA "{}"',
							vals=vals.Strings())

		self.add_parameter('load',
							label='load from current directory',
							set_cmd=':MMEMory:LOAD:ALL "{}"',
							vals=vals.Strings())

		self.add_parameter('load_state',
							label='load state file in current directory',
							set_cmd=':MMEMory:LOAD:STATe "{}"',
							vals=vals.Strings())

		self.add_parameter('create_directory',
							label='create directory in current directory',
							set_cmd=':MMEMory:MDIRectory "{}"',
							vals=vals.Strings())

		self.add_parameter('move',
							label='move file from current directory to new path',
							set_cmd=':MMEMory:MOVE "{}"',
							vals=vals.Strings())

		self.add_parameter('directories',
							label='available direcotries query',
							get_cmd=':MMEMory:RDIRectory?',
							get_parser=str.rstrip)

		self.add_parameter('delete_directory',
							label='delete empty directory in current directory',
							set_cmd=':MMEMory:RDIRectory "{}"',
							vals=vals.Strings())

		self.add_parameter('save',
							label='save state or waveform in current directory',
							set_cmd=':MMEMory:STORe:ALL "{}"',
							vals=vals.Strings())
		
		self.add_parameter('save_state',
							label='save state in current directory',
							set_cmd=':MMEMory:STORe:STATe "{}"',
							vals=vals.Strings())
	
	def directory_files(self, folder: str=None): return self.ask(f':MMEMory:CATalog:ALL? {folder}')
	def arbitrary_files(self, folder: str=None): return self.ask(f':MMEMory:CATalog:DATA:ARBitrary? {folder}')
	def state_files(self, folder: str=None): return self.ask(f':MMEMory:CATalog:STATe? {folder}')	

	def move(self, file: str, path: str):
		self._move(f'"{file}","{path}"')

class Memory(InstrumentChannel):
	def __init__(self, parent: Instrument, name: str, num: int,):
		super().__init__(parent, name)
		
		self.add_parameter('state_name',
							label=f'memory state {num} name',
							set_cmd=f':MEMory:STATe:NAME {num}, {{}}',
							get_cmd=f':MEMory:STATe:NAME? {num}',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('valid',
							label=f'memory state {num} file exists query',
							get_cmd=f':MEMory:STATe:VALid? {num}',
							get_parser=_int_parser)


	def delete(self): self.write(f':MEMory:STATe:DELete {self.num}')

class Screenshot(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)

		self.add_parameter('capture',
							label='Screenshot capture',
							get_cmd=':HCOPy:SDUMp:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('format',
							label='Screenshot format',
							set_cmd=':HCOPy:SDUMp:DATA:FORMat {}',
							get_cmd=':HCOPy:SDUMp:DATA:FORMat?',
							vals=vals.Enum('BMP', 'PNG'),
							get_parser=str.rstrip)	

class OutputChannel(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, channum):
		super().__init__(parent, name)
		self.channum=channum
		self.max_freq=parent.max_freq

		# MMEMORY MENU
		self.add_parameter('load_wave',
							label=f'channel {channum} load waveform from current directory',
							set_cmd=f':MMEMory:LOAD:DATA{channum} "{{}}"')

		self.add_parameter('save_wave',
							label=f'Channel {channum} save arbitrary waveform to current directory',
							set_cmd=f':MMEMory:STORe:DATA{channum} "{{}}"')
		
		# OUTPUT MENU
		self.add_parameter('impedance',
							label=f'Channel {channum} impedance',
							set_cmd=f':OUTPut{channum}:IMPedance {{}}',
							get_cmd=f':OUTPut{channum}:IMPedance?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN', 'INF'), vals.Ints(1, int(1e4))),
							get_parser=float,
							unit='ohm')
		
		self.add_parameter('load',
							label=f'Channel {channum} load',
							set_cmd=self.impedance,
							get_cmd=self.impedance,
							)
		
		self.add_parameter('polarity',
							label=f'channel {channum} polarity',
							set_cmd=f':OUTPut{channum}:POLarity{{}}',
							get_cmd=f':OUTPut{channum}:POLarity?',
							vals=vals.Enum('NORM', 'INV'),
							get_parser=str.rstrip)
		
		self.add_parameter('output',
							label=f'channel {channum} output',
							set_cmd=f':OUTPut{channum} {{}}',
							get_cmd=f':OUTPut{channum}?',
							vals=vals.Enum('ON', 'OFF'),
							get_parser=str.rstrip)
		
		self.add_parameter('sync_polarity',
							label=f'channel {channum} sync_polarity',
							set_cmd=f':OUTPut{channum}:SYNC:POLarity {{}}',
							get_cmd=f':OUTPut{channum}:SYNC:POLarity?',
							vals=vals.Enum('POS', 'NEG'),
							get_parser=str.rstrip)
		
		self.add_parameter('sync_state',
							label=f'channel {channum} sync_state',
							set_cmd=f':OUTPut{channum}:SYNC {{}}',
							get_cmd=f':OUTPut{channum}:SYNC?',
							vals=vals.Enum('ON', 'OFF'),
							get_parser=str.rstrip)
		
		self.add_parameter('voltage_limit_high',
							label=f'channel {channum} voltage_limit_high',
							set_cmd=f':OUTPut{channum}:VOLLimit:HIGH {{}}',
							get_cmd=f':OUTPut{channum}:VOLLimit:HIGH?',
							unit='V',
							docstring='Acceptable range depends on current amplitude and offset settings',
							get_parser=float)
		
		self.add_parameter('voltage_limit_low',
							label=f'channel {channum} voltage_limit_low',
							set_cmd=f':OUTPut{channum}:VOLLimit:LOW {{}}',
							get_cmd=f':OUTPut{channum}:VOLLimit:LOW?',
							unit='V',
							docstring='Acceptable range depends on current amplitude and offset settings',
							get_parser=float)
		
		self.add_parameter('voltage_limit_state',
							label=f'channel {channum} voltage_limit_state',
							set_cmd=f':OUTPut{channum}:VOLLimit {{}}',
							get_cmd=f':OUTPut{channum}:VOLLimit?',
							vals=vals.Enum('ON', 'OFF'),
							get_parser=str.rstrip)
		
		# APPLY MENU
		self.add_parameter('applied_function',
							label=f'channel {channum} function',
							get_cmd=f':SOURce{channum}:APPLy?',
							get_parser=_apply_parser)
		
		self.add_parameter('DC',
							label=f'channel {channum} DC function',
							set_cmd=f':SOURce{channum}:APPLy:DC 1,1,{{}}',
							unit='V')
		
		self.add_parameter('_dualtone',
							label=f'channel {channum} dualtone function',
							set_cmd=f':SOURce{channum}:APPLy:DUALTone {{}}')
		
		self.add_parameter('_harmonic',
							label=f'channel {channum} harmonic function',
							set_cmd=f':SOURce{channum}:APPLy:HARMonic {{}}')
		
		self.add_parameter('_noise',
							label=f'channel {channum} noise function',
							set_cmd=f':SOURce{channum}:APPLy:NOISe {{}}')
		
		self.add_parameter('_PRBS',
							label=f'channel {channum} PRBS function',
							set_cmd=f':SOURce{channum}:APPLy:PRBS {{}}')
		
		self.add_parameter('_pulse',
							label=f'channel {channum} pulse function',
							set_cmd=f':SOURce{channum}:APPLy:PULSe {{}}')
		
		self.add_parameter('_ramp',
							label=f'channel {channum} ramp function',
							set_cmd=f':SOURce{channum}:APPLy:RAMP {{}}')
		
		self.add_parameter('_RS232',
							label=f'channel {channum} RS232 function',
							set_cmd=f':SOURce{channum}:APPLy:RS232 {{}}')
		
		self.add_parameter('_sequence',
							label=f'channel {channum} sequence function',
							set_cmd=f':SOURce{channum}:APPLy:SEQuence {{}}')
		
		self.add_parameter('_sinusoidal',
							label=f'channel {channum} sinusoidal function',
							set_cmd=f':SOURce{channum}:APPLy:SINusoid {{}}')
		
		self.add_parameter('_square',
							label=f'channel {channum} square function',
							set_cmd=f':SOURce{channum}:APPLy:SQUare {{}}')
		
		self.add_parameter('_arbitrary',
							label=f'channel {channum} arbitrary function',
							set_cmd=f':SOURce{channum}:APPLy:USER {{}}')	
		#SOURCE MENU
		self.add_parameter('frequency',
							label=f'channel {channum} frequency',
							set_cmd=f':SOURce{channum}:FREQuency:FIXed {{}}',
							get_cmd=f':SOURce{channum}:FREQuency:FIXed?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(1e-6,self.max_freq)),
							unit='Hz',
							get_parser=float)

		self.add_parameter('function',
							label=f'channel {channum} function shape',
							set_cmd=f':SOURce{channum}:FUNCtion:SHAPe {{}}',
							get_cmd=f':SOURce{channum}:FUNCtion:SHAPe?',
							vals=vals.Enum('SIN', 'SQU', 'RAMP', 'PULS', 'NOIS', 'USER', 'HARM', 'CUST', 'DC', 'KAISER', 'ROUNDPM', 'SINC','NEGRAMP','ATTALT','AMPALT','STAIRDN','STAIRUP','STAIRUD','CPULSE',
								'PPULSE','NPULSE','TRAPEZIA','ROUNDHALF','ABSSINE','ABSSINEHALF','SINETRA','SINEVER','EXPRISE','EXPFALL','TAN','COT','SQRT','X2DATA','GAUSS','HAVERSINE','LORENTZ',
								'DIRICHLET','GAUSSPULSE','AIRY','CARDIAC','QUAKE','GAMMA','VOICE','TV','COMBIN','BANDLIMITED','STEPRESP','BUTTERWORTH','CHEBYSHEV1','CHEBYSHEV2','BOXCAR','BARLETT',
								'TRIANG','BLACKMAN','HAMMING','HANNING','DUALTONE','ACOS','ACOSH','ACOTCON','ACOTPRO','ACOTHCON','ACOTHPRO','ACSCCON','ACSCPRO','ACSCHCON','ACSCHPRO','ASECCON','ASECPRO',
								'ASECH','ASIN','ASINH','ATAN','ATANH','BESSELJ','BESSELY','CAUCHY','COSH','COSINT','COTHCON','COTHPRO','CSCCON','CSCPRO','CSCHCON','CSCHPRO','CUBIC','ERF','ERFC','ERFCINV',
								'ERFINV','LAGUERRE','LAPLACE','LEGEND','LOG','LOGNORMAL','MAXWELL','RAYLEIGH','RECIPCON','RECIPPRO','SECCON','SECPRO','SECH','SINH','SININT','TANH','VERSIERA','WEIBULL',
								'BARTHANN','BLACKMANH','BOHMANWIN','CHEBWIN','FLATTOPWIN','NUTTALLWIN','PARZENWIN','TAYLORWIN','TUKEYWIN','CWPUSLE','LFPULSE','LFMPULSE','EOG','EEG','EMG','PULSILOGRAM',
								'TENS1','TENS2','TENS3','SURGE','DAMPEDOSC','SWINGOSC','RADAR','THREEAM','THREEFM','THREEPM','THREEPWM','THREEPFM','RESSPEED','MCNOSIE','PAHCUR','RIPPLE','ISO76372TP1',
								'ISO76372TP2A','ISO76372TP2B','ISO76372TP3A','ISO76372TP3B','ISO76372TP4','ISO76372TP5A','ISO76372TP5B','ISO167502SP','ISO167502VR','SCR','IGNITION','NIMHDISCHARGE','GATEVIBR'),
							get_parser=str.rstrip)

		self.add_parameter('period',
							label=f'channel {channum} period',
							set_cmd=f':SOURce{channum}:PERiod:FIXed {{}}',
							get_cmd=f':SOURce{channum}:PERiod:FIXed?',
							vals=vals.MultiType(vals.Enum('MAX','MIN'),vals.Numbers(1/self.max_freq,1/1e-6)),
							unit='s',
							get_parser=float)

		self.add_parameter('phase',
							label=f'channel {channum} phase adjust',
							set_cmd=f':SOURce{channum}:PHASe:ADJust {{}}',
							get_cmd=f':SOURce{channum}:PHASe:ADJust?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(0,360)),
							unit='degrees',
							get_parser=float)

		self.add_parameter('beeper_state',
							label='beeper state',
							set_cmd=':SYSTem:BEEPer:STATe {}',
							get_cmd=':SYSTem:BEEPer:STATe?',
							vals=vals.Enum('ON', 'OFF'),
							get_parser=str.rstrip)
		
		self.add_parameter('channel',
							label='channel select',
							set_cmd=':SYSTem:CHANnel:CURrent {}',
							get_cmd=':SYSTem:CHANnel:CURrent?',
							vals=vals.Enum('CH1', 'CH2'),
							get_parser=str.rstrip)
		
		self.add_parameter('channel_number',
							label='number of channels',
							get_cmd=':SYSTem:CHANnel:NUMber?',
							get_parser=_int_parser)
		
		self.add_parameter('GPIB_address',
							label='instrument GPIB address',
							set_cmd=':SYSTem:COMMunicate:GPIB:SELF:ADDRess {}',
							get_cmd=':SYSTem:COMMunicate:GPIB:SELF:ADDRess?',
							vals=vals.Ints(0,30),
							get_parser=_int_parser)
		
		self.add_parameter('LAN_auto',
							label='autoIP configuration mode',
							set_cmd=':SYSTem:COMMunicate:LAN:AUTOip:STATe {}',
							get_cmd=':SYSTem:COMMunicate:LAN:AUTOip:STATe?',
							vals=vals.Enum('ON', 'OFF'),
							get_parser=str.rstrip)
		
		self.add_parameter('LAN_control',
							label='port number of the initial control connecting port for socket communication',
							get_cmd=':SYSTem:COMMunicate:LAN:CONTrol?',
							get_parser=_int_parser)
		
		self.add_parameter('DHCP_state',
							label='DHCP configuration state',
							set_cmd=':SYSTem:COMMunicate:LAN:DHCP:STATe {}',
							get_cmd=':SYSTem:COMMunicate:LAN:DHCP:STATe?',
							vals=vals.Enum('ON', 'OFF'),
							get_parser=str.rstrip)
		
		self.add_parameter('DNS_address',
							label='DNS address',
							set_cmd=':SYSTem:COMMunicate:LAN:DNS {}',
							get_cmd=':SYSTem:COMMunicate:LAN:DNS?',
							vals=vals.Strings(7,15),
							get_parser=str.rstrip)
		
		self.add_parameter('LAN_gateway',
							label='default gateway',
							set_cmd=':SYSTem:COMMunicate:LAN:GATEway {}',
							get_cmd=':SYSTem:COMMunicate:LAN:GATEway?',
							vals=vals.Strings(7,15),
							get_parser=str.rstrip)
		
		self.add_parameter('IP_address',
							label='LAN IP address',
							set_cmd=':SYSTem:COMMunicate:LAN:IPADdress {}',
							get_cmd=':SYSTem:COMMunicate:LAN:IPADdress?',
							vals=vals.Strings(7,15),
							get_parser=str.rstrip)
		
		self.add_parameter('subnet_mask',
							label='subnet mask',
							set_cmd=':SYSTem:COMMunicate:LAN:SMASk {}',
							get_cmd=':SYSTem:COMMunicate:LAN:SMASk?',
							vals=vals.Strings(7,15),
							get_parser=str.rstrip)
		
		self.add_parameter('manual_IP',
							label='manual IP configuration state',
							set_cmd=':SYSTem:COMMunicate:LAN:STATic:STATe {}',
							get_cmd=':SYSTem:COMMunicate:LAN:STATic:STATe?',
							vals=vals.Enum('ON', 'OFF'),
							get_parser=str.rstrip)
		
		self.add_parameter('usb_information',
							label='instrument usb information',
							get_cmd=':SYSTem:COMMunicate:USB:INFormation?',
							get_parser=str.rstrip)
		
		self.add_parameter('error',
							label='error query',
							get_cmd=':SYSTem:ERRor?',
							get_parser=str.rstrip)
		
		self.add_parameter('key_lock',
							label='key lock',
							set_cmd=':SYSTem:KLOCk',
							get_cmd=':SYSTem:KLOCk?',
							vals=vals.Enum('ON', 'OFF'),
							get_parser=str.rstrip)
		
		self.add_parameter('language',
							label='language',
							set_cmd=':SYSTem:LANGuage {},',
							get_cmd=':SYSTem:LANGuage?',
							vals=vals.Enum('ENGL', 'SCH'),
							get_parser=str.rstrip)
		
		self.add_parameter('log_state',
							label='system log state',
							set_cmd=':SYSTem:LOG::STATE {}',
							get_cmd=':SYSTem:LOG::STATE?',
							vals=vals.Enum('ON', 'OFF'),
							get_parser=str.rstrip)
		
		self.add_parameter('power',
							label='power state',
							set_cmd=':SYSTem:POWeron {}',
							get_cmd=':SYSTem:POWeron?',
							vals=vals.Enum('DEFAULT', 'LAST'),
							get_parser=str.rstrip)
		
		self.add_parameter('delete_user_state',
							label='delete user state',
							set_cmd=':SYSTem:PRESet:DELete {}',
							vals=vals.Enum('USER1','USER2','USER3','USER4','USER5','USER6','USER7','USER8','USER9','USER10'),
							)
		
		self.add_parameter('recall_user_state',
							label='recall user state',
							set_cmd=':SYSTem:PRESet:RECall {}',
							vals=vals.Enum('DEF','USER1','USER2','USER3','USER4','USER5','USER6','USER7','USER8','USER9','USER10',))
		
		self.add_parameter('save_user_state',
							label='save user state',
							set_cmd=':SYSTem:PRESet:SAVe {}',
							vals=vals.Enum('USER1','USER2','USER3','USER4','USER5','USER6','USER7','USER8','USER9','USER10'),
							)
		
		self.add_parameter('user_states',
							label='user stored states',
							get_cmd=':SYSTem:PRESet:STATe?',
							get_parser=str.rstrip)
		
		self.add_parameter('reference',
							label='reference oscillator source',
							set_cmd=':SYSTem:ROSCillator:SOURce {}',
							get_cmd=':SYSTem:ROSCillator:SOURce?',
							vals=vals.Enum('INT', 'EXT'),
							get_parser=str.rstrip)
		
		burst_module=BurstModule(self, 'burst')
		self.add_submodule('burst', burst_module)

		dualtone_module=Dualtone(self, 'dualtone')
		self.add_submodule('dualtone',dualtone_module)
		
		prbs_module=PRBS(self, 'PRBS')
		self.add_submodule('PRBS', prbs_module)
		
		pulse_function_module=PulseFunction(self, 'pulse_function')
		self.add_submodule('pulse_function', pulse_function_module)

		ramp_module=Ramp(self, 'ramp')
		self.add_submodule('ramp', ramp_module)

		rs232_module=RS232(self, 'rs232')
		self.add_submodule('rs232', rs232_module)

		sequence_module=Sequence(self, 'sequence')
		self.add_submodule('sequence', sequence_module)

		square_module=Square(self, 'square')
		self.add_submodule('square', square_module)

		harmonic_module=Harmonic(self, 'harmonic')
		self.add_submodule('harmonic', harmonic_module)

		modulation_module=Modulation(self, 'modulation')
		self.add_submodule('modulation', modulation_module)

		pulse_module=Pulse(self, 'pulse')
		self.add_submodule('pulse', pulse_module)

		sum_module=Sum(self, 'sum')
		self.add_submodule('sum', sum_module)

		sweep_module=Sweep(self, 'sweep')
		self.add_submodule('sweep', sweep_module)

		trace_module=Trace(self, 'trace')
		self.add_submodule('trace', trace_module)

		track_module=Track(self, 'track')
		self.add_submodule('track', track_module)

		voltage_module=Voltage(self, 'voltage')
		self.add_submodule('voltage', voltage_module)

		trigger_module=Trigger(self, 'trigger')
		self.add_submodule('trigger', trigger_module)
	  
	def synchronize(self): self.write(f':SOURce{self.channum}:PHASe:SYNChronize')
	def align(self): self.synchronize()
	def initiate(self): self.synchronize()

	def copy(self):
		'''Copies other channel parameters'''
		self.write(f':SYSTem:CSCopy CH{self.channum}. CH{self.channum%2+1}')

	def dualtone(self, frequency, amplitude, offset):
		'''
		Dual tone parameter wrapper
		Args:
			frequency: Hz
			amplitude: Vpp
			offset: V
		'''
		vals.MultiType(vals.Enum('DEF', 'MAX', 'MIN'), vals.Numbers(1e-6,20e6)).validate(frequency)
		input=f'{frequency}, {amplitude}, {offset}'
		self._dualtone(input)
	   
	def harmonic(self, frequency, amplitude, offset, phase):
		'''
		Harmonic parameter wrapper
		Args:
			frequency: Hz
			amplitude: Vpp
			offset: V
			phase: degrees
		'''
		vals.MultiType(vals.Enum('DEF', 'MAX', 'MIN'),vals.Numbers(1e-6,15e6)).validate(frequency)
		vals.MultiType(vals.Enum('DEF', 'MAX', 'MIN'),vals.Numbers(0,360)).validate(phase)
		input=f'{frequency}, {amplitude}, {offset}, {phase}'
		self._harmonic(input)
		 
	def noise(self, amplitude, offset):
		'''
		Noise parameter wrapper
		Args:
			amplitude: Vpp
			offset: V
		'''
		input=f'{amplitude}, {offset}'
		self._noise(input)
   
	def PRBS(self, frequency, amplitude, offset):
		'''
		Pseudorandom binary sequence (PRBS) parameter wrapper
		Args:
			frequency: bps
			amplitude: Vpp
			offset: V
		'''
		vals.MultiType(vals.Enum('DEF', 'MAX', 'MIN'),vals.Numbers(2e3,30e6)).validate(frequency)
		input=f'{frequency}, {amplitude}, {offset}'
		self._PRBS(input)
   
	def pulse(self, frequency, amplitude, offset, phase):
		'''
		Pulse parameter wrapper
		Args:
			frequency: Hz
			amplitude: Vpp
			offset: V
			phase: degrees
		'''
		vals.MultiType(vals.Enum('DEF', 'MAX', 'MIN'),vals.Numbers(1e-6,10e6)).validate(frequency)
		vals.MultiType(vals.Enum('DEF', 'MAX', 'MIN'),vals.Numbers(0,360)).validate(phase)
		input=f'{frequency}, {amplitude}, {offset}, {phase}'
		self._pulse(input)
   
	def ramp(self, frequency, amplitude, offset, phase):
		'''
		Ramp parameter wrapper
		Args:
			frequency: Hz
			amplitude: Vpp
			offset: V
			phase: degrees
		'''
		vals.MultiType(vals.Enum('DEF', 'MAX', 'MIN'),vals.Numbers(1e-6,1e6)).validate(frequency)
		vals.MultiType(vals.Enum('DEF', 'MAX', 'MIN'),vals.Numbers(0,360)).validate(phase)
		input=f'{frequency}, {amplitude}, {offset}, {phase}'
		self._ramp(input)
   
	def RS232(self, amplitude, offset):
		'''
		RS232 parameter wrapper
		Args:
			amplitude: Vpp
			offset: V
		'''
		input=f'{amplitude}, {offset}'
		self._RS232(input)
   
	def sequence(self, sample_rate, amplitude, offset, phase):
		'''
		Sequence parameter wrapper
		Args:
			Sample rate: MSa/s
			amplitude: Vpp
			offset: V
			phase: degrees
		'''
		vals.MultiType(vals.Enum('DEF', 'MAX', 'MIN'), vals.Numbers(2e3,30e6)).validate(sample_rate)
		vals.MultiType(vals.Enum('DEF', 'MAX', 'MIN'), vals.Numbers(0,360)).validate(phase)
		input=f'{sample_rate}, {amplitude}, {offset}, {phase}'
		self._sequence(input)
   
	def sinusoid(self, frequency, amplitude, offset, phase):
		'''
		Sinusoid parameter wrapper
		Args:
			frequency: Hz
			amplitude: Vpp
			offset: V
			phase: degrees
		'''
		vals.MultiType(vals.Enum('DEF', 'MAX', 'MIN'), vals.Numbers(1e-6,self.max_freq)).validate(frequency)
		vals.MultiType(vals.Enum('DEF', 'MAX', 'MIN'), vals.Numbers(0,360)).validate(phase)
		input=f'{frequency}, {amplitude}, {offset}, {phase}'
		self._sinusoid(input)
   
	def square(self, frequency, amplitude, offset, phase):
		'''
		Square parameter wrapper
		Args:
			frequency: Hz
			amplitude: Vpp
			offset: V
			phase: degrees
		'''
		vals.MultiType(vals.Enum('DEF', 'MAX', 'MIN'), vals.Numbers(1e-6,1e6)).validate(frequency)
		vals.MultiType(vals.Enum('DEF', 'MAX', 'MIN'), vals.Numbers(0,360)).validate(phase)
		input=f'{frequency}, {amplitude}, {offset}, {phase}'
		self._square(input)

	def arbitrary(self, frequency, amplitude, offset, phase):
		'''
		Arbitrary parameter wrapper
		Args:
			frequency: Hz
			amplitude: Vpp
			offset: V
			phase: degrees
		'''
		vals.MultiType(vals.Enum('DEF', 'MAX', 'MIN'), vals.Numbers(1e-6,10e6)).validate(frequency)
		vals.MultiType(vals.Enum('DEF', 'MAX', 'MIN'), vals.Numbers(0,360)).validate(phase)
		input=f'{frequency}, {amplitude}, {offset}, {phase}'
		self._arbitrary(input)

class Coupling(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		channum=parent.channum
		# COUPLING MENU

		self.add_parameter('amplitude_deviation',
							label=f'channel {channum} coupling amplitude deviation',
							set_cmd=f':COUPling{channum}:AMPL:DEViation {{}}',
							get_cmd=f':COUPling{channum}:AMPL:DEViation?',
							vals=vals.Numbers(-19.998,19.998),
							unit='Vpp',
							get_parser=float)

		self.add_parameter('amplitude_mode',
							label=f'channel {channum} coupling amplitude mode',
							set_cmd=f':COUPling{channum}:AMPL:MODE {{}}',
							get_cmd=f':COUPling{channum}:AMPL:MODE?',
							vals=vals.Enum('OFFS', 'RAT'),
							get_parser=str.rstrip)

		self.add_parameter('amplitude_ratio',
							label=f'channel {channum} coupling amplitude ratio',
							set_cmd=f':COUPling{channum}:AMPL:RATio {{}}',
							get_cmd=f':COUPling{channum}:AMPL:RATio?',
							vals=vals.MultiType(vals.Enum('MIN', 'MAX'), vals.Numbers(0.001,1000)),
							get_parser=str.rstrip)

		self.add_parameter('amplitude_state',
							label=f'channel {channum} coupling amplitude state',
							set_cmd=f':COUPling{channum}:AMPL:STATe {{}}',
							get_cmd=f':COUPling{channum}:AMPL:STATe?',
							vals=vals.Enum('ON', 'OFF'),
							get_parser=str.rstrip)

		self.add_parameter('frequency_deviation',
							label=f'channel {channum} coupling frequency deviation',
							set_cmd=f':COUPling{channum}:FREQuency:DEViation {{}}',
							get_cmd=f':COUPling{channum}:FREQuency:DEViation?',
							vals=vals.Numbers(-99.9999999999E6,99.9999999999E6),
							unit='Hz',
							get_parser=float)

		self.add_parameter('frequency_mode',
							label=f'channel {channum} coupling frequency mode',
							set_cmd=f':COUPling{channum}:FREQuency:MODE {{}}',
							get_cmd=f':COUPling{channum}:FREQuency:MODE?',
							vals=vals.Enum('OFFS', 'RAT'),
							get_parser=str.rstrip)

		self.add_parameter('frequency_ratio',
							label=f'channel {channum} coupling frequency ratio',
							set_cmd=f':COUPling{channum}:FREQuency:RATio {{}}',
							get_cmd=f':COUPling{channum}:FREQuency:RATio?',
							vals=vals.Numbers(0.000001,1000000),
							get_parser=float)

		self.add_parameter('frequency_state',
							label=f'channel {channum} coupling frequency state',
							set_cmd=f':COUPling{channum}:FREQuency:STATe {{}}',
							get_cmd=f':COUPling{channum}:FREQuency:STATe?',
							vals=vals.Enum('ON', 'OFF'),
							get_parser=str.rstrip)

		self.add_parameter('phase_deviation',
							label=f'channel {channum} coupling phase deviation',
							set_cmd=f':COUPling{channum}:PHASe:DEViation {{}}',
							get_cmd=f':COUPling{channum}:PHASe:DEViation?',
							vals=vals.Numbers(-360,360),
							unit='degrees',
							get_parser=float)

		self.add_parameter('phase_mode',
							label=f'channel {channum} coupling phase mode',
							set_cmd=f':COUPling{channum}:PHASe:MODE {{}}',
							get_cmd=f':COUPling{channum}:PHASe:MODE?',
							vals=vals.Enum('OFFS', 'RAT'),
							get_parser=str.rstrip)

		self.add_parameter('phase_ratio',
							label=f'channel {channum} coupling phase ratio',
							set_cmd=f':COUPling{channum}:PHASe:RATio {{}}',
							get_cmd=f':COUPling{channum}:PHASe:RATio?',
							vals=vals.MultiType(vals.Enum('MIN', 'MAX'), vals.Numbers(0.01,100)),
							get_parser=float)

		self.add_parameter('phase_state',
							label=f'channel {channum} coupling phase state',
							set_cmd=f':COUPling{channum}:PHASe:STATe {{}}',
							get_cmd=f':COUPling{channum}:PHASe:STATe?',
							vals=vals.Enum('ON', 'OFF'),
							get_parser=str.rstrip)

		self.add_parameter('state',
							label=f'channel {channum} coupling state',
							set_cmd=f':COUPling{channum}:STATe {{}}',
							get_cmd=f':COUPling{channum}:STATe?',
							vals=vals.Enum('ON', 'OFF'),
							get_parser=str.rstrip)

		self.add_parameter('trigger_state',
							label=f'channel {channum} trigger coupling state',
							set_cmd=f':COUPling{channum}:TRIgger :STATe {{}}',
							get_cmd=f':COUPling{channum}:TRIgger :STATe?',
							vals=vals.Enum('ON', 'OFF'),
							get_parser=str.rstrip)

class BurstModule(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		channum=parent.channum
		
		# BURST MENU
		self.add_parameter('gate_polarity',
						   label=f'channel {channum} burst gate polarity',
						   set_cmd=f':SOURce{channum}:GATE:POLarity {{}}',
						   get_cmd=f':SOURce{channum}:BURSt:GATE:POLarity?',
						   vals=vals.Enum('NORM', 'INV'),
						   get_parser=str.rstrip)
		
		self.add_parameter('_period',
						   label=f'channel {channum} burst internal period',
						   set_cmd=f':SOURce{channum}:BURSt:INTernal:PERiod {{}}',
						   get_cmd=f':SOURce{channum}:BURSt:INTernal:PERiod?',
						   vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(2.1066e-6,500)),
						   get_parser=float,
						   unit='s',
						   docstring='Value must be greater than waveform duration + 2us')
		
		self.add_parameter('mode',
						   label=f'channel {channum} burst mode',
						   set_cmd=f':SOURce{channum}:BURSt:MODE {{}}',
						   get_cmd=f':SOURce{channum}:BURSt:MODE?',
						   vals=vals.Enum('TRIG', 'INF', 'GAT'),
						   get_parser=str.rstrip)
		
		self.add_parameter('_cycles',
						   label=f'channel {channum} burst number of cycles',
						   set_cmd=f':SOURce{channum}:BURSt:NCYCles {{}}',
						   get_cmd=f':SOURce{channum}:BURSt:NCYCles?',
						   get_parser=_int_parser)
		
		self.add_parameter('phase',
						   label=f'channel {channum} burst phase',
						   set_cmd=f':SOURce{channum}:BURSt:PHASe {{}}',
						   get_cmd=f':SOURce{channum}:BURSt:PHASe?',
						   vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(0,360)),
						   get_parser=float,
						   unit='degree')
		
		self.add_parameter('state',
						   label=f'channel {channum} burst state',
						   set_cmd=f':SOURce{channum}:BURSt:STATe {{}}',
						   get_cmd=f':SOURce{channum}:BURSt:STATe?',
						   vals=vals.Enum('ON', 'OFF'),
						   get_parser=str.rstrip)
		
		self.add_parameter('_delay',
						   label=f'channel {channum} burst t',
						   set_cmd=f':SOURce{channum}:BURSt:TDELay {{}}',
						   get_cmd=f':SOURce{channum}:BURSt:TDELay?',
						   vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(0,100)),
						   get_parser=float)
		
		self.add_parameter('trigger_slope',
						   label=f'channel {channum} burst trigger slope',
						   set_cmd=f':SOURce{channum}:BURSt:TRIGger:SLOPe {{}}',
						   get_cmd=f':SOURce{channum}:BURSt:TRIGger:SLOPe?',
						   vals=vals.Enum('POS', 'NEG'),
						   get_parser=float)
		
		self.add_parameter('trigger_source',
						   label=f'channel {channum} burst trigger source',
						   set_cmd=f':SOURce{channum}:BURSt:TRIGger:SOURce {{}}',
						   get_cmd=f':SOURce{channum}:BURSt:TRIGger:SOURce?',
						   vals=vals.Enum('INT', 'EXT', 'MAN'),
						   get_parser=str.rstrip)
		
		self.add_parameter('trigger_output',
						   label=f'channel {channum} burst trigger output',
						   set_cmd=f':SOURce{channum}:BURSt:TRIGger:TRIGOut {{}}',
						   get_cmd=f':SOURce{channum}:BURSt:TRIGger:TRIGOut?',
						   vals=vals.Enum('POS', 'NEG', 'OFF'),
						   get_parser=str.rstrip)
		
		self.add_parameter('idle',
						   label=f'channel {channum} burst idle level',
						   set_cmd=f':SOURce{channum}:BURSt:IDLE {{}}',
						   get_cmd=f':SOURce{channum}:BURSt:IDLE?',
						   vals=vals.MultiType(vals.Enum('FPT', 'TOP', 'CENTER', 'BOTTOM'), vals.Ints(0,16383)),
						   get_parser=float)
		
	def trigger(self): self.write(f':SOURce{self.channum}:BURSt:TRIGger:IMMediate')

	def period(self, period: float=None):
		if period==None:
			return self._period()
		wf_period=1/parent.frequency()
		limit=wf_period*self._cycles()+2e-6
		if period<limit or period not in ['MIN','MAX']:
			raise ValueError('Burst period is outside limit.\n'
							'Must be greater than waveform period times cycles plus 2us.\n'
							f'Currently must be greater than {limit}s')
		else:
			self._period(period)

	def cycles(self, cycles: int=None):
		if cycles==None:
			return self._cycles()
		if self.trigger_source()=='INT':
			vals.MultiType(vals.Enum('MIN', 'MAX'), vals.Ints(1,500e3)).validate(cycles)
		else:
			vals.MultiType(vals.Enum('MIN', 'MAX'), vals.Ints(1,1e6)).validate(cycles)
		self._cycles(cycles)

	def delay(self, delay: float=None):
		if delay==None:
			return self._delay()
		wf_period=1/parent.frequency()
		limit=self._period()-wf_period*self._cycles()-2e-6
		if self.trigger_source()=='INT':
			if delay<0 or delay>limit or delay not in ['MIN','MAX']:
				raise ValueError('Burst delay is outside limit.\n'
								'Must be between 0 and burst period minus waveform period times cycles minus 2us when on internal trigger\n'
								f'Currently must be less than {limit}\n')
		else:
			self._delay(delay)

class Dualtone(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		channum=parent.channum
		
		# DUALTONE MENU
		self.add_parameter('center_frequency',
						   label=f'channel {channum} center frequency',
						   set_cmd=f':SOURce{channum}:FUNCtion:DUALTone:CENTERFreq {{}}',
						   get_cmd=f':SOURce{channum}:FUNCtion:DUALTone:CENTERFreq?',
						   vals=vals.MultiType(vals.Enum('MAX','MIN'), vals.Numbers(1e-6,20e6)),
						   unit='Hz',
						   docstring='Value is (freq1+freq2)/2',
						   get_parser=float)
		
		self.add_parameter('frequency1',
						   label=f'channel {channum} frequency 1',
						   set_cmd=f':SOURce{channum}:FUNCtion:DUALTone:FREQ1 {{}}',
						   get_cmd=f':SOURce{channum}:FUNCtion:DUALTone:FREQ1?',
						   vals=vals.MultiType(vals.Enum('MAX','MIN'), vals.Numbers(1e-6,20e6)),
						   unit='Hz',
						   get_parser=float)
		
		self.add_parameter('frequency2',
						   label=f'channel {channum} frequency 2',
						   set_cmd=f':SOURce{channum}:FUNCtion:DUALTone:FREQ2 {{}}',
						   get_cmd=f':SOURce{channum}:FUNCtion:DUALTone:FREQ2?',
						   vals=vals.MultiType(vals.Enum('MAX','MIN'), vals.Numbers(1e-6,20e6)),
						   unit='Hz',
						   get_parser=float)
		
		self.add_parameter('offset_frequency',
						   label=f'channel {channum} offset frequency',
						   set_cmd=f':SOURce{channum}:FUNCtion:DUALTone:OFFSETFreq {{}}',
						   get_cmd=f':SOURce{channum}:FUNCtion:DUALTone:OFFSETFreq?',
						   vals=vals.MultiType(vals.Enum('MAX','MIN'), vals.Numbers(1e-6-20e6, 20e6-1e-6)),
						   unit='Hz',
						   docstring='Value is freq2-freq1',
						   get_parser=float)

class Harmonic(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		channum=parent.channum
		self.channum=channum
		
		# HARMONIC MENU
		self.add_parameter('_order',
							label=f'channel {channum} harmonic highest order',
							set_cmd=f':SOURce{channum}:HARMonic:ORDEr {{}}',
							get_cmd=f':SOURce{channum}:HARMonic:ORDEr?',
							get_parser=_int_parser,
							vals=vals.MultiType(vals.Enum('MIN', 'MAX'), vals.Ints(2,8)))
		
		self.add_parameter('harmonic_state',
							label=f'channel {channum} harmonic state',
							set_cmd=f':SOURce{channum}:HARMonic:STATe {{}}',
							get_cmd=f':SOURce{channum}:HARMonic:STATe?',
							vals=vals.Enum('ON', 'OFF'),
							get_parser=str.rstrip)
		
		self.add_parameter('harmonic_type',
							label=f'channel {channum} harmonic type',
							set_cmd=f':SOURce{channum}:HARMonic:TYPe {{}}',
							get_cmd=f':SOURce{channum}:HARMonic:TYPe',
							vals=vals.Enum('EVEN', 'ODD', 'ALL', 'USER'),
							get_parser=str.rstrip)
		
		self.add_parameter('user_harmonic',
							label=f'channel {channum} user harmonic',
							set_cmd=f':SOURce{channum}:HARMonic:USER {{}}',
							get_cmd=f':SOURce{channum}:HARMonic:USER?',
							vals=vals.Strings(8,8),
							docstring='Format "X0000000"',
							get_parser=str.rstrip)
		
		
		for i in range(2,8+1):
			order_module=HarmonicOrder(self, f'ord{i}', i)
			self.add_submodule(f'ord{i}', order_module)

	def order(self, order: int=None):
		if order==None:
			return self._order()
		f_max=float(self.ask(f':SOURce{channum}:FREQuency:FIXed? MAX'))
		f_fund=parent.frequency()
		if order>f_max/f_fund:
			raise ValueError('Order is outside the limit.\n'
							'Must be between 2 and 8.\n'
							f'Currently must be less than {limit}s.\n')
		else:
			self._order(order)

class HarmonicOrder(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, ordernum):
		super().__init__(parent, name)
		channum=parent.channum
		
		self.add_parameter('amplitude',
						   label=f'channel {channum} harmonic order {ordernum} amplitude',
						   set_cmd=f':SOURce{channum}:HARMonic:AMPL {ordernum}, {{}}',
						   get_cmd=f':SOURce{channum}:HARMonic:AMPL? {ordernum}',
						   get_parser=float,
						   vals=vals.MultiType(vals.Enum('MIN', 'MAX'), vals.Numbers(0)),
						   unit='Vpp')
		
		self.add_parameter('harmonic_phase',
						   label=f'channel {channum} harmonic order {ordernum} harmonic phase',
						   set_cmd=f':SOURce{channum}:HARMonic:PHASe {ordernum} {{}}',
						   get_cmd=f'[:SOURce{channum}:HARMonic:PHASe? {ordernum}',
						   vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(0,360)),
						   unit='degrees',
						   get_parser=float)

class Modulation(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		channum=parent.channum
		self.channum=channum
		
		# MODULATION MENU  
		
		self.add_parameter('state',
							label=f'channel {channum} modulation state',
							set_cmd=f':SOURce{channum}:MOD:STATe {{}}',
							get_cmd=f'SOURce{channum}:MOD:STATe?',
							vals=vals.Enum('ON', 'OFF'),
							get_parser=str.rstrip)
		
		self.add_parameter('type',
							label=f'channel {channum} modulation type',
							set_cmd=f':SOURce{channum}:MOD:TYPe {{}}',
							get_cmd=f':SOURce{channum}:MOD:TYPe?',
							vals=vals.Enum('AM', 'FM', 'PM', 'ASK', 'FSK', 'PSK', 'PWM'),
							get_parser=str.rstrip)
		
		AM=AmplitudeModulation(self, 'amplitude')
		self.add_submodule('amplitude', AM)
		
		ASK=AmplitudeShiftKeyModulation(self, 'ASK')
		self.add_submodule('ASK', ASK)
		
		FM=FrequencyModulation(self, 'frequency')
		self.add_submodule('frequency', FM)
		
		FSK=FrequencyShiftKeyModulation(self, 'FSK')
		self.add_submodule('FSK', FSK)
		
		PM=PhaseModulation(self, 'phase')
		self.add_submodule('phase', PM)
		
		PSK=PhaseShiftKeyModulation(self, 'PSK')
		self.add_submodule('PSK', PSK)
		
		PWM=PulseWidthModulation(self, 'pulse')
		self.add_submodule('pulse', PWM)

class AmplitudeModulation(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		channum=parent.channum
		
		# AMPLITUDE MODULATION MENU
		
		self.add_parameter('depth',
						   label=f'channel {channum} amplitude modulation depth',
						   set_cmd=f':SOURce{channum}:AM:DEPTh {{}}',
						   get_cmd=f':SOURce{channum}:AM:DEPTh?',
						   vals=vals.MultiType(vals.Enum('ON', 'OFF'), vals.Numbers(0,120)),
						   unit='%',
						   get_parser=float)
		
		self.add_parameter('carrier_suppression',
						   label=f'channel {channum} amplitude modulation carrier waveform suppression',
						   set_cmd=f':SOURce{channum}:AM:DSSC {{}}',
						   get_cmd=f':SOURce{channum}:AM:DSSC?',
						   vals=vals.Enum('ON', 'OFF'),
						   get_parser=str.rstrip)
		
		self.add_parameter('frequency',
						   label=f'channel {channum} amplitude modulation internal frequency',
						   set_cmd=f':SOURce{channum}:AM:INTernal:FREQuency {{}}',
						   get_cmd=f':SOURce{channum}:AM:INTernal:FREQuency?',
						   vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(2e-3,1e6)),
						   unit='Hz',
						   get_parser=float)
		
		self.add_parameter('function',
						   label=f'channel {channum} amplitude modulation internal frequency',
						   set_cmd=f':SOURce{channum}:AM:INTernal:FUNCtion {{}}',
						   get_cmd=f':SOURce{channum}:AM:INTernal:FUNCtion?',
						   vals=vals.Enum('SIN', 'SQU', 'TRI', 'RAMP', 'NRAM', 'NOIS', 'USER'),
						   get_parser=str.rstrip)
		
		self.add_parameter('source',
						   label=f'channel {channum} amplitude modulation source',
						   set_cmd=f':SOURce{channum}:AM:SOURce {{}}',
						   get_cmd=f':SOURce{channum}:AM:SOURce?',
						   vals=vals.Enum('INT', 'EXT'),
						   get_parser=str.rstrip)
		
		self.add_parameter('state',
						   label=f'channel {channum} amplitude modulation state',
						   set_cmd=f':SOURce{channum}:AM:STATe {{}}',
						   get_cmd=f':SOURce{channum}:AM:STATe?',
						   vals=vals.Enum('ON', 'OFF'),
						   get_parser=str.rstrip)
		
class AmplitudeShiftKeyModulation(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		channum=parent.channum
		
		# ASK MODULATION MENU
		
		self.add_parameter('amplitude',
						   label=f'channel {channum} ASK modulation amplitude',
						   set_cmd=f':SOURce{channum}:ASKey:AMPLitude {{}}',
						   get_cmd=f':SOURce{channum}:ASKey:AMPLitude?',
						   vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(0,10),),
						   unit='Vpp',
						   get_parser=float)
		
		self.add_parameter('rate',
						   label=f'channel {channum} ASK modulation rate',
						   set_cmd=f':SOURce{channum}:ASKey:INTernal:RATE {{}}',
						   get_cmd=f':SOURce{channum}:ASKey:INTernal:RATE?',
						   vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(2e-3,1e6)),
						   unit='Hz',
						   get_parser=float)
		
		self.add_parameter('polarity',
						   label=f'channel {channum} ASK modulation polarity',
						   set_cmd=f':SOURce{channum}:ASKey:POLarity {{}}',
						   get_cmd=f':SOURce{channum}:ASKey:POLarity?',
						   vals=vals.Enum('POS', 'NEG'),
						   get_parser=str.rstrip)
		
		self.add_parameter('source',
						   label=f'channel {channum} ASK modulation source',
						   set_cmd=f':SOURce{channum}:ASKey:SOURce {{}}',
						   get_cmd=f':SOURce{channum}:ASKey:SOURce?',
						   vals=vals.Enum('INT', 'EXT'),
						   get_parser=str.rstrip)
		
		self.add_parameter('state',
						   label=f'channel {channum} ASK modulation state',
						   set_cmd=f':SOURce{channum}:ASKey:STATe {{}}',
						   get_cmd=f':SOURce{channum}:ASKey:STATe?',
						   vals=vals.Enum('ON', 'OFF'),
						   get_parser=str.rstrip)
		
class FrequencyModulation(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		channum=parent.channum
		self.channum=channum
		
		# FM MODULATION MENU
		
		self.add_parameter('_deviation',
						   label=f'channel {channum} frequency modulation deviation',
						   set_cmd=f':SOURce{channum}:FM:DEViation {{}}',
						   get_cmd=f':SOURce{channum}:FM:DEViation?',
						   vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(0)),
						   unit='Hz',
						   get_parser=float)
		
		self.add_parameter('frequency',
						   label=f'channel {channum} frequency modulation frequency',
						   set_cmd=f':SOURce{channum}:FM:INTernal:FREQuency {{}}',
						   get_cmd=f':SOURce{channum}:FM:INTernal:FREQuency?',
						   vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(2e-3,1e6)),
						   unit='Hz',
						   get_parser=float)
		
		self.add_parameter('function',
						   label=f'channel {channum} frequency modulation function',
						   set_cmd=f':SOURce{channum}:FM:INTernal:FUNCtion {{}}',
						   get_cmd=f':SOURce{channum}:FM:INTernal:FUNCtion?',
						   vals=vals.Enum('SIN', 'SQU', 'TRI', 'RAMP', 'NRAM', 'NOIS', 'USER'),
						   get_parser=str.rstrip)
		
		self.add_parameter('source',
						   label=f'channel {channum} frequency modulation source',
						   set_cmd=f':SOURce{channum}:FM:SOURce {{}}',
						   get_cmd=f':SOURce{channum}:FM:SOURce?',
						   vals=vals.Enum('INT', 'EXT'),
						   get_parser=str.rstrip)
		
		self.add_parameter('state',
						   label=f'channel {channum} frequency modulation state',
						   set_cmd=f':SOURce{channum}:FM:STATe {{}}',
						   get_cmd=f':SOURce{channum}:FM:STATe?',
						   vals=vals.Enum('ON', 'OFF'),
						   get_parser=float)
	
	def deviation(self, deviation: float=None):
		if deviation==None:
			return self._deviation()
		freq_carrier=float(self.ask(f':SOURce{self.channum}:FREQuency:FIXed?'))
		freq_max=float(self.ask(f':SOURce{self.channum}:FREQuency:FIXed? MAX'))
		if deviation>freq_carrier or deviation+freq_carrier>freq_max+1e3 or deviation not in ['MIN','MAX']:
			raise ValueError(f'Frequency modulation {deviation} must be less than the carrier frequency \n'
								'and the deviation plus carrier frequency must be less than the maximum carrier frequency plus 1 kHz \n'
								f'Currently must be below {freq_carrier}')
		else:
			self._duty_cylce(duty_cylce)
		# TODO: carrier amplitude limit condition
		
class FrequencyShiftKeyModulation(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		channum=parent.channum
		
		# FSK MENU
		
		self.add_parameter('frequency',
							label=f'channel {channum} frequency shift key modulation frequency',
							set_cmd=f':SOURce{channum}:FSKey:FREQuency {{}}',
							get_cmd=f':SOURce{channum}:FSKey:FREQuency?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(1e-6,10e6)),
							unit='Hz',
							get_parser=float)
		
		self.add_parameter('rate',
							label=f'channel {channum} frequency shift key modulation rate',
							set_cmd=f':SOURce{channum}:FSKey:INTernal:RATE {{}}',
							get_cmd=f':SOURce{channum}:FSKey:INTernal:RATE?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(2e-3,1e6)),
							unit='Hz',
							get_parser=float)
		
		self.add_parameter('polarity',
							label=f'channel {channum} frequency shift key modulation polarity',
							set_cmd=f':SOURce{channum}:FSKey:POLarity {{}}',
							get_cmd=f':SOURce{channum}:FSKey:POLarity?',
							vals=vals.Enum('POS', 'NEG'),
							get_parser=str.rstrip)
		
		self.add_parameter('source',
							label=f'channel {channum} frequency shift modulation source',
							set_cmd=f':SOURce{channum}:FSKey:SOURce {{}}',
							get_cmd=f':SOURce{channum}:FSKey:SOURce?',
							vals=vals.Enum('INT', 'EXT'),
							get_parser=str.rstrip)
		
		self.add_parameter('state',
							label=f'channel {channum} frequency shift modulation state',
							set_cmd=f':SOURce{channum}:FSKey:STATe {{}}',
							get_cmd=f':SOURce{channum}:FSKey:STATe?',
							vals=vals.Enum('ON', 'OFF'),
							get_parser=str.rstrip)
	  
class PhaseModulation(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		channum=parent.channum
		
		# PM MENU
		
		self.add_parameter('deviation',
							label=f'channel {channum} phase modulation deviation',
							set_cmd=f':SOURce{channum}:PM[:DEViation] {{}}',
							get_cmd=f':SOURce{channum}:PM[:DEViation]?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(0,360)),
							unit='degrees',
							get_parser=float)
		
		self.add_parameter('frequency',
							label=f'channel {channum} phase modulation frequency',
							set_cmd=f':SOURce{channum}:PM:INTernal:FREQuency {{}}',
							get_cmd=f':SOURce{channum}:PM:INTernal:FREQuency?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(2e-3,1e6)),
							unit='Hz',
							get_parser=float)
		
		self.add_parameter('function',
							label=f'channel {channum} phase modulation function',
							set_cmd=f':SOURce{channum}:PM:INTernal:FUNCtion {{}}',
							get_cmd=f':SOURce{channum}:PM:INTernal:FUNCtion?',
							vals=vals.Enum('SIN', 'SQU', 'TRI', 'RAMP', 'NRAM', 'NOIS', 'USER'),
							get_parser=str.rstrip)
		
		self.add_parameter('source',
							label=f'channel {channum} phase modulation source',
							set_cmd=f':SOURce{channum}:PM:SOURce {{}}',
							get_cmd=f':SOURce{channum}:PM:SOURce?',
							vals=vals.Enum('INT', 'EXT'),
							get_parser=str.rstrip)
		
		self.add_parameter('state',
							label=f'channel {channum} phase modulation state',
							set_cmd=f':SOURce{channum}:PM:STATe {{}}',
							get_cmd=f':SOURce{channum}:PM:STATe?',
							vals=vals.Enum('ON', 'OFF'),
							get_parser=str.rstrip)

class PhaseShiftKeyModulation(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		channum=parent.channum
		
		# PSK MENU
		
		self.add_parameter('rate',
							label=f'channel {channum} phase shift key modulation rate',
							set_cmd=f':SOURce{channum}:PSKey:INTernal:RATE {{}}',
							get_cmd=f':SOURce{channum}:PSKey:INTernal:RATE?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(2e-3,1e6)),
							unit='Hz',
							get_parser=float)
		
		self.add_parameter('phase',
							label=f'channel {channum} phase shift key modulation phase',
							set_cmd=f':SOURce{channum}:PSKey:PHASe {{}}',
							get_cmd=f':SOURce{channum}:PSKey:PHASe?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(0,360)),
							unit='degrees',
							get_parser=float)
		
		self.add_parameter('polarity',
							label=f'channel {channum} phase shift key modulation polarity',
							set_cmd=f':SOURce{channum}:PSKey:POLarity {{}}',
							get_cmd=f':SOURce{channum}:PSKey:POLarity?',
							vals=vals.Enum('POS', 'NEG'),
							get_parser=str.rstrip)
		
		self.add_parameter('source',
							label=f'channel {channum} phase shift key modulation source',
							set_cmd=f':SOURce{channum}:PSKey:SOURce {{}}',
							get_cmd=f':SOURce{channum}:PSKey:SOURce?',
							vals=vals.Enum('INT', 'EXT'),
							get_parser=str.rstrip)
		
		self.add_parameter('state',
							label=f'channel {channum} phase shift key modulation state',
							set_cmd=f':SOURce{channum}:PSKey:STATe {{}}',
							get_cmd=f':SOURce{channum}:PSKey:STATe?',
							vals=vals.Enum('ON', 'OFF'),
							get_parser=str.rstrip)

class PulseWidthModulation(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		channum=parent.channum
		self.channum=channum
		
		# PWM MENU
		
		self.add_parameter('_duty_cycle',
							label=f'channel {channum} pulse width modulation duty cycle',
							set_cmd=f':SOURce{channum}:PWM[:DEViation]:DCYCle {{}}',
							get_cmd=f':SOURce{channum}:PWM[:DEViation]:DCYCle?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(0)),
							unit='%',
							get_parser=float)
		
		self.add_parameter('_width',
							label=f'channel {channum} pulse width modulation width',
							set_cmd=f':SOURce{channum}:PWM[:DEViation][:WIDTh] {{}}',
							get_cmd=f':SOURce{channum}:PWM[:DEViation][:WIDTh]?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(0)),
							unit='s',
							get_parser=float)
		
		self.add_parameter('frequency',
							label=f'channel {channum} pulse width modulation width',
							set_cmd=f':SOURce{channum}:PWM:INTernal:FREQuency {{}}',
							get_cmd=f':SOURce{channum}:PWM:INTernal:FREQuency?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(2e-3,1e6)),
							unit='Hz',
							get_parser=float)
		
		self.add_parameter('function',
							label=f'channel {channum} pulse width modulation function',
							set_cmd=f':SOURce{channum}:PWM:INTernal:FUNCtion {{}}',
							get_cmd=f':SOURce{channum}:PWM:INTernal:FUNCtion?',
							vals=vals.Enum('SIN', 'SQU', 'TRI', 'RAMP', 'NRAM', 'NOIS', 'USER'),
							get_parser=str.rstrip)
		
		self.add_parameter('source',
							label=f'channel {channum} pulse width modulation function',
							set_cmd=f':SOURce{channum}:PWM:SOURce {{}}',
							get_cmd=f':SOURce{channum}:PWM:SOURce?',
							vals=vals.Enum('INT', 'EXT'),
							get_parser=str.rstrip)
		
		self.add_parameter('state',
							label=f'channel {channum} pulse width modulation state',
							set_cmd=f':SOURce{channum}:PWM:STATe {{}}',
							get_cmd=f':SOURce{channum}:PWM:STATe?',
							vals=vals.Enum('ON', 'OFF'),
							get_parser=str.rstrip)
						
	def duty_cycle(self, duty_cycle: int=None):
		if duty_cycle==None:
			return self._duty_cycle()
		pulse_duty_cycle=float(self.ask(f':SOURce{self.channum}:PULSe:DCYCle?'))
		if duty_cycle>pulse_duty_cycle or duty_cycle not in ['MIN','MAX']:
			raise ValueError(f'Pulse width modulation {duty_cycle} must be less than the pulse duty cycle \n'
							f'Currently must be between below {pulse_duty_cycle}')
		else:
			self._duty_cylce(duty_cylce)

	def width(self, width: int=None):
		if width==None:
			return self._width()
		pulse_width=float(self.ask(f':SOURce{self.channum}:PULSe:WIDTh?'))
		if width>pulse_width or width not in ['MIN', 'MAX']:
			raise ValueError(f'Pulse width modulation {width} must be less than the pulse width \n'
							f'Currently must be below {pulse_width}')
		else:
			self._width(width)

class PRBS(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		channum=parent.channum
		
		# PRBS MENU
		self.add_parameter('bit_rate',
						   label=f'channel {channum} PRBS bit rate',
						   set_cmd=f':SOURce{channum}:FUNCtion:PRBS:BRATe {{}}',
						   get_cmd=f':SOURce{channum}:FUNCtion:PRBS:BRATe?',
						   vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(2e3,30e6)),
						   unit='bps',
						   get_parser=float)

		self.add_parameter('data_type',
						   label=f'channel {channum} PRBS data type',
						   set_cmd=f':SOURce{channum}:FUNCtion:PRBS:DATA {{}}',
						   get_cmd=f':SOURce{channum}:FUNCtion:PRBS:DATA?',
						   vals=vals.Enum('PN7', 'PN9', 'PN11'),
						   get_parser=str.rstrip)

class Pulse(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		channum=parent.channum
		self.channum=channum
		
		# PULSE MENU
		
		self.add_parameter('_duty_cycle',
							label=f'channel {channum} pulse duty cycle',
							set_cmd=f':SOURce{channum}:PULSe:DCYCle {{}}',
							get_cmd=f':SOURce{channum}:PULSe:DCYCle?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(0.001,99.999)),
							unit='%',
							get_parser=float)
		
		self.add_parameter('_rise_time',
							label=f'channe; {channum} pulse rise time',
							set_cmd=f':SOURce{channum}:PULSe:TRANsition:LEADing {{}}',
							get_cmd=f':SOURce{channum}:PULSe:TRANsition:LEADing?',
							vals=vals.MultiType(vals.Enum('MIN', 'MAX'), vals.Numbers(8e-9)),
							unit='s',
							get_parser=float)
		
		self.add_parameter('_fall_time',
							label=f'channel {channum} pulse fall time',
							set_cmd=f':SOURce{channum}:PULSe:TRANsition:TRAiling {{}}',
							get_cmd=f':SOURce{channum}:PULSe:TRANsition:TRAiling?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(8e-9)),
							unit='s',
							get_parser=float)
		
		self.add_parameter('_width',
							label=f'channel {channum} pulse fall time',
							set_cmd=f':SOURce{channum}:PULSe:WIDTh {{}}',
							get_cmd=f':SOURce{channum}:PULSe:WIDTh?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(16e-9,999.9999821185606e3)),
							unit='s',
							get_parser=float)

	def duty_cycle(self, duty_cycle: float=None):
		if duty_cycle==None:
			return self._duty_cycle()
		else:
			pulse_period=float(self.ask(f':SOURce{self.channum}:PERiod:FIXed?'))
			width_min=float(self.ask(f':SOURce{channum}:PULSe:WIDTh? MIN'))
			if duty_cycle<100*width_min/pulse_period or duty_cycle>100*(1-2*width_min/pulse_period) or duty_cycle not in ['MIN', 'MAX']:
				raise ValueError(f'Pulse {duty_cycle} must be more than 100 times minimum pulse width over pulse period \n'
								'and less than 100 times (1 minus 2 times minimum pulse width over pulse period \n'
								f'Currently must be between {100*width_min/pulse_period} and {100*(1-2*width_min/pulse_period)}')
			else:
				self._duty_cylce(duty_cylce)
	
	def rise_time(self, rise_time: float=None):
		if rise_time==None:
			return self._rise_time()
		limit=self._width()*0.625
		if rise_time<8e-9 or rise_time>limit or rise_time not in ['MIN','MAX']:
			raise ValueError('Rise time is outside the limit.\n'
							'Must be between 8e-9 and 0.625 times pulse width.\n'
							f'Currently must be less than {limit}s.\n')
		else:
			self._rise_time(rise_time)

	def fall_time(self, fall_time: float=None):
		if fall_time==None:
			return self._fall_time()
		limit=self._width()*0.625
		if fall_time<8e-9 or fall_time>limit or fall_time not in ['MIN','MAX']:
			raise ValueError('Fall time is outside the limit.\n'
							'Must be between 8e-9 and 0.625 times pulse width.\n'
							f'Currently must be less than {limit}s.\n')
		else:
			self._fall_time(fall_time)

	def width(self, width: float=None):
		if width==None:
			return self._width()
		pulse_period=float(self.ask(f':SOURce{self.channum}:PERiod:FIXed?'))
		width_min=16e-9
		limit=pulse_period-(2*width_min)
		if width<16e-9 or width>limit or width not in ['MIN','MAX']:
			raise ValueError('Width is outside the limit.\n'
							'Must be between 16e-9 and period minus times minimum pulse width.\n'
							f'Currently must be less than {limit}s.\n')
		else:
			self._width(width)

class PulseFunction(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		channum=parent.channum
		
		#PULSE MENU
		self.add_parameter('_duty_cycle',
						   label=f'channel {channum} pulse duty cycle',
						   set_cmd=f':SOURce{channum}:FUNCtion:PULSe:DCYCle {{}}',
						   get_cmd=f':SOURce{channum}:FUNCtion:PULSe:DCYCle?',
						   vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(0.001,99.999)),
						   unit='%',
						   get_parser=float)
		
		self.add_parameter('period',
						   label=f'channel {channum} pulse period',
						   set_cmd=f':SOURce{channum}:FUNCtion:PULSe:PERiod {{}}',
						   get_cmd=f':SOURce{channum}:FUNCtion:PULSe:PERiod?',
						   vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(40e-9,1e6)),
						   unit='s',
						   get_parser=float)
		
		self.add_parameter('_transition_time',
						   label=f'channel {channum} pulse transition time',
						   set_cmd=f':SOURce{channum}:FUNCtion:PULSe:TRANsition:BOTH {{}}',
						   vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(10e-9)),
						   unit='s',
						   get_parser=float)
		
		self.add_parameter('_rise_time',
						   label=f'channel {channum} pulse rise time',
						   set_cmd=f':SOURce{channum}:FUNCtion:PULSe:TRANsition:LEADing {{}}',
						   get_cmd=f':SOURce{channum}:FUNCtion:PULSe:TRANsition:LEADing?',
						   vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(10e-9)),
						   unit='s',
						   get_parser=float)
		
		self.add_parameter('_fall_time',
						   label=f'channel {channum} pulse fall time',
						   set_cmd=f':SOURce{channum}:FUNCtion:PULSe:TRANsition:TRAiling {{}}',
						   get_cmd=f':SOURce{channum}:FUNCtion:PULSe:TRANsition:TRAiling?',
						   vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(10e-9)),
						   unit='s',
						   get_parser=float)
		
		self.add_parameter('_width',
						   label=f'channel {channum} pulse width',
						   set_cmd=f':SOURce{channum}:FUNCtion:PULSe:WIDTh {{}}',
						   get_cmd=f':SOURce{channum}:FUNCtion:PULSe:WIDTh?',
						   vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(16e-9,999.9999821185906e3)),
						   unit='s',
						   get_parser=float)
		
	def duty_cycle(self, duty_cycle: float=None):
  		if duty_cylce==None:
  			return self._duty_cycle()
  		else:
  			ratio=float(self.ask(f':SOUR{self.channum}:FUNC:PULS:WIDT? MIN'))/self._period() # pulse width minimum / pulse period
  			if duty_cylce<100*ratio or duty_cycle>=100*(1-2*ratio) or duty_cycle in ['MIN','MAX']:
  				raise ValueError(f'Pulse duty cycle {duty_cylce}% must be greater than the minimum percentage the pulse width takes of the pulse period'
  								  'and less than the maximum percentage the minimum pulse can take\n'
  								  f'Currently must be between {100*ratio}% and {100*(1-2*ratio)}%')
  			else:
  				self._duty_cylce(duty_cylce)
	
	def transition_time(self, transition_time: float=None):
		if transition_time==None:
			return self._transition_time()
		limit=self._width()*0.625
		if transition_time<10e-9 or transition_time>limit or transition_time not in ['MIN','MAX']:
			raise ValueError('Transition time is outside the limit.\n'
							'Must be between 10e-9 and 0.625 times pulse width.\n'
							f'Currently must be less than {limit}s.\n')
		else:
			self._transition_time(transition_time)

	def rise_time(self, rise_time: float=None):
		if rise_time==None:
			return self._rise_time()
		limit=self._width()*0.625
		if rise_time<10e-9 or rise_time>limit or rise_time not in ['MIN','MAX']:
			raise ValueError('Rise time is outside the limit.\n'
							'Must be between 10e-9 and 0.625 times pulse width.\n'
							f'Currently must be less than {limit}s.\n')
		else:
			self._rise_time(rise_time)

	def fall_time(self, fall_time: float=None):
		if fall_time==None:
			return self._fall_time()
		limit=self._width()*0.625
		if fall_time<10e-9 or fall_time>limit or fall_time not in ['MIN','MAX']:
			raise ValueError('Fall time is outside the limit.\n'
							'Must be between 10e-9 and 0.625 times pulse width.\n'
							f'Currently must be less than {limit}s.\n')
		else:
			self._fall_time(fall_time)

	def width(self, width: float=None):
		if width==None:
			return self._width()
		width_min=16e-9
		limit=self._period()-(2*width_min)
		if width<16e-9 or width>limit or width not in ['MIN','MAX']:
			raise ValueError('Width is outside the limit.\n'
							'Must be between 16e-9 and period minus times minimum pulse width.\n'
							f'Currently must be less than {limit}s.\n')
		else:
			self._width(width)

class Ramp(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		channum=parent.channum
		
		#RAMP MENU
		self.add_parameter('ramp_symmetry',
							label=f'channel {channum} ramp symmetry',
							set_cmd=f':SOURce{channum}:FUNCtion:RAMP:SYMMetry {{}}',
							get_cmd=f':SOURce{channum}:FUNCtion:RAMP:SYMMetry?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(0,100)),
							unit='%',
							get_parser=float)

class RS232(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		channum=parent.channum
		
		# RS232 MENU
		self.add_parameter('baud_rate',
							label=f'channel {channum} RS232 baud rate',
							set_cmd=f':SOURce{channum}:FUNCtion:RS232:BAUDrate {{}}',
							get_cmd=f':SOURce{channum}:FUNCtion:RS232:BAUDrate?',
							vals=vals.Enum(9600,14400,19200,38400,57600,115200,128000,230400),
							get_parser=_int_parser)
		
		self.add_parameter('checkbit',
							label=f'channel {channum} RS232 checkbit',
							set_cmd=f':SOURce{channum}:FUNCtion:RS232:CHECKBit {{}}',
							get_cmd=f':SOURce{channum}:FUNCtion:RS232:CHECKBit?',
							vals=vals.Enum('NONE', 'ODD', 'EVEN'),
							get_parser=str.rstrip)
		
		self.add_parameter('data',
							label=f'channel {channum} RS232 data',
							set_cmd=f':SOURce{channum}:FUNCtion:RS232:DATA {{}}',
							get_cmd=f':SOURce{channum}:FUNCtion:RS232:DATA?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN'),vals.Ints(0,225)),
							get_parser=_int_parser)
		
		self.add_parameter('data_bit',
							label=f'channel {channum} RS232 data bits',
							set_cmd=f':SOURce{channum}:FUNCtion:RS232:DATABit {{}}',
							get_cmd=f':SOURce{channum}:FUNCtion:RS232:DATABit?',
							vals=vals.Enum(7,8),
							get_parser=_int_parser)
		
		self.add_parameter('stop_bit',
							label=f'channel {channum} RS232 stop bits',
							set_cmd=f':SOURce{channum}:FUNCtion:RS232:STOPBit {{}}',
							get_cmd=f':SOURce{channum}:FUNCtion:RS232:STOPBit?',
							vals=vals.Enum(1,1.5,2),
							get_parser=float)

class Sequence(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, ):
		super().__init__(parent, name)
		channum=parent.channum
		
		# SEQUENCE MENU
		self.add_parameter('_edge_time',
							label=f'channel {channum} sequence edge time',
							set_cmd=f':SOURce{channum}:FUNCtion:SEQuence:EDGETime {{}}',
							get_cmd=f':SOURce{channum}:FUNCtion:SEQuence:EDGETime?',
							vals=vals.Numbers(8e-9),
							unit='s',
							docstring='Only valid when the sequence filter is in interpolation mode',
							get_parser=float)
		
		self.add_parameter('filter',
							label=f'channel {channum} sequyence filter type',
							set_cmd=f':SOURce{channum}:FUNCtion:SEQuence:FILTer {{}}',
							get_cmd=f':SOURce{channum}:FUNCtion:SEQuence:FILTer?',
							vals=vals.Enum('SMOOTH', 'STEP', 'INSERT'),
							get_parser=str.rstrip)
		
		self.add_parameter('period',
							label=f'channel {channum} sequence period',
							set_cmd=f':SOURce{channum}:FUNCtion:SEQuence:PERiod {{}}',
							get_cmd=f':SOURce{channum}:FUNCtion:SEQuence:PERiod?',
							vals=vals.Ints(1,256),
							get_parser=_int_parser)
		
		self.add_parameter('rate',
							label=f'channel {channum} sequence sample rate',
							set_cmd=f':SOURce{channum}:FUNCtion:SEQuence:SRATe {{}}',
							get_cmd=f':SOURce{channum}:FUNCtion:SEQuence:SRATe?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(2e3,30e6)),
							unit='Sa/s',                    
							get_parser=float)
		
		self.add_parameter('state',
							label=f'channel {channum} sequence state',
							set_cmd=f':SOURce{channum}:FUNCtion:SEQuence[:STATe] {{}}',
							get_cmd=f':SOURce{channum}:FUNCtion:SEQuence[:STATe]?',
							vals=vals.Enum('ON', 'OFF'),
							get_parser=str.rstrip)
		
		self.add_parameter('wave',
							label=f'channel {channum} sequence waveform type',
							set_cmd=f':SOURce{channum}:FUNCtion:SEQuence:WAVE {{}}',
							get_cmd=f':SOURce{channum}:FUNCtion:SEQuence:WAVE?',
							vals=vals.Enum('SIN', 'SQU', 'RAMP', 'PULS', 'NOIS', 'USER', 'HARM', 'CUST', 'DC', 'KAISER', 'ROUNDPM', 'SINC','NEGRAMP','ATTALT','AMPALT','STAIRDN','STAIRUP','STAIRUD','CPULSE',
								'PPULSE','NPULSE','TRAPEZIA','ROUNDHALF','ABSSINE','ABSSINEHALF','SINETRA','SINEVER','EXPRISE','EXPFALL','TAN','COT','SQRT','X2DATA','GAUSS','HAVERSINE','LORENTZ',
								'DIRICHLET','GAUSSPULSE','AIRY','CARDIAC','QUAKE','GAMMA','VOICE','TV','COMBIN','BANDLIMITED','STEPRESP','BUTTERWORTH','CHEBYSHEV1','CHEBYSHEV2','BOXCAR','BARLETT',
								'TRIANG','BLACKMAN','HAMMING','HANNING','DUALTONE','ACOS','ACOSH','ACOTCON','ACOTPRO','ACOTHCON','ACOTHPRO','ACSCCON','ACSCPRO','ACSCHCON','ACSCHPRO','ASECCON','ASECPRO',
								'ASECH','ASIN','ASINH','ATAN','ATANH','BESSELJ','BESSELY','CAUCHY','COSH','COSINT','COTHCON','COTHPRO','CSCCON','CSCPRO','CSCHCON','CSCHPRO','CUBIC','ERF','ERFC','ERFCINV',
								'ERFINV','LAGUERRE','LAPLACE','LEGEND','LOG','LOGNORMAL','MAXWELL','RAYLEIGH','RECIPCON','RECIPPRO','SECCON','SECPRO','SECH','SINH','SININT','TANH','VERSIERA','WEIBULL',
								'BARTHANN','BLACKMANH','BOHMANWIN','CHEBWIN','FLATTOPWIN','NUTTALLWIN','PARZENWIN','TAYLORWIN','TUKEYWIN','CWPUSLE','LFPULSE','LFMPULSE','EOG','EEG','EMG','PULSILOGRAM',
								'TENS1','TENS2','TENS3','SURGE','DAMPEDOSC','SWINGOSC','RADAR','THREEAM','THREEFM','THREEPM','THREEPWM','THREEPFM','RESSPEED','MCNOSIE','PAHCUR','RIPPLE','ISO76372TP1',
								'ISO76372TP2A','ISO76372TP2B','ISO76372TP3A','ISO76372TP3B','ISO76372TP4','ISO76372TP5A','ISO76372TP5B','ISO167502SP','ISO167502VR','SCR','IGNITION','NIMHDISCHARGE','GATEVIBR'),
							get_parser=str.rstrip)

	def edge_time(self, edge_time: float=None):
		if edge_time==None:
			return self._edge_time()
		limit=(1/self.rate)/1.25
		if edge_time<8e-9 or edge_time>limit:
			raise ValueError('Edge time is outside the limit.\n'
							'Must be between 8e-9 and 1 over sample rate divided by 1.25.\n'
							f'Currently must be less than {limit}s.\n')
		else:
			self._edge_time(edge_time)

class SourceFrequency(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		channum=parent.channum
		
		# FREQUENCY MENU

		self.add_parameter('couple_mode',
						   label=f'channel {channum} frequency couple mode',
						   set_cmd=f':SOURce{channum}:FREQuency:COUPle:MODE {{}}',
						   get_cmd=f':SOURce{channum}:FREQuency:COUPle:MODE?',
						   vals=vals.Enum('OFFSET', 'RATIO'),
						   get_parser=str.rstrip)
		
		self.add_parameter('couple_offset',
						   label=f'channel {channum} frequency couple offset',
						   set_cmd=f':SOURce{channum}:FREQuency:COUPle:OFFSet {{}}',
						   get_cmd=f':SOURce{channum}:FREQuency:COUPle:OFFSet?',
						   vals=vals.Numbers(-99.9999999999e6,99.9999999999e6),
						   unit='Hz',
						   get_parser=float)
		
		self.add_parameter('couple_ratio',
						   label=f'channel {channum} frequency couple ratio',
						   set_cmd=f':SOURce{channum}:FREQuency:COUPle:RATio {{}}',
						   get_cmd=f':SOURce{channum}:FREQuency:COUPle:RATio?',
						   vals=vals.Numbers(1e-6,1e6),
						   get_parser=float)
		
		self.add_parameter('couple_state',
						   label=f'channel {channum} frequency couple state',
						   set_cmd=f':SOURce{channum}:FREQuency:COUPle[:STATe] {{}}',
						   get_cmd=f':SOURce{channum}:FREQuency:COUPle[:STATe]?',
						   vals=vals.Enum('ON', 'OFF'),
						   get_parser=str.rstrip)
	  
class Square(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, ):
		super().__init__(parent, name)
		channum=parent.channum
		
		# SQUARE MENU
		self.add_parameter('duty_cycle',
							label=f'channel {channum} square duty cycle',
							set_cmd=f':SOURce{channum}:FUNCtion:SQUare:DCYCle {{}}',
							get_cmd=f':SOURce{channum}:FUNCtion:SQUare:DCYCle?',
							vals=vals.MultiType(vals.Enum('MAX','MIN'),vals.Numbers(0.01,99.99)),
							docstring='Range is limited by the waveform frequency',
							unit='%',
							get_parser=float)
		
		self.add_parameter('period',
							label=f'channel {channum} square period',
							set_cmd=f':SOURce{channum}:FUNCtion:SQUare:PERiod {{}}',
							get_cmd=f':SOURce{channum}:FUNCtion:SQUare:PERiod?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(40e-9,1e6)),
							unit='s',
							get_parser=float)

class Sum(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		channum=parent.channum
		
		# SUM MENU
		
		self.add_parameter('amplitude',
							label=f'channel {channum} amplitude sum',
							set_cmd=f':SOURce{channum}:SUM:AMPLitude {{}}',
							get_cmd=f':SOURce{channum}:SUM:AMPLitude?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(0,100)),
							unit='%',
							get_parser=float)
		
		self.add_parameter('frequency',
							label=f'channel {channum} frequency sum',
							set_cmd=f':SOURce{channum}:SUM:INTernal:FREQuency {{}}',
							get_cmd=f':SOURce{channum}:SUM:INTernal:FREQuency?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(1e-6,35e6)),
							unit='Hz',
							get_parser=float)
		
		self.add_parameter('function',
							label=f'channel {channum} function sum',
							set_cmd=f':SOURce{channum}:SUM:INTernal:FUNCtion {{}}',
							get_cmd=f':SOURce{channum}:SUM:INTernal:FUNCtion?',
							vals=vals.Enum('SIN', 'SQU', 'RAMP', 'NOIS', 'ARB'),
							get_parser=str.rstrip)
		
		self.add_parameter('state',
							label=f'channel {channum} state sum',
							set_cmd=f':SOURce{channum}:SUM:STATe {{}}',
							get_cmd=f':SOURce{channum}:SUM:STATe?',
							vals=vals.Enum('ON', 'OFF'),
							get_parser=str.rstrip)

class Sweep(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		channum=parent.channum
		self.channum=channum
		
		# SWEEP MENU
		
		self.add_parameter('start_hold_time',
							label=f'channel {channum} sweep start hold time',
							set_cmd=f':SOURce{channum}:SWEep:HTIMe:STARt {{}}',
							get_cmd=f':SOURce{channum}:SWEep:HTIMe:STARt?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(0,500)),
							unit='s',
							get_parser=float)
		
		self.add_parameter('stop_hold_time',
							label=f'channel {channum} sweep stop hold time',
							set_cmd=f':SOURce{channum}:SWEep:HTIMe:STOP {{}}',
							get_cmd=f':SOURce{channum}:SWEep:HTIMe:STOP?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(0,500)),
							unit='s',
							get_parser=float)
		
		self.add_parameter('return_time',
							label=f'channel {channum} sweep return time',
							set_cmd=f':SOURce{channum}:SWEep:RTIMe {{}}',
							get_cmd=f':SOURce{channum}:SWEep:RTIMe?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(0,500)),
							unit='s',
							get_parser=float)
		
		self.add_parameter('spacing',
							label=f'channel {channum} sweep spacing',
							set_cmd=f':SOURce{channum}:SWEep:SPACing {{}}',
							get_cmd=f':SOURce{channum}:SWEep:SPACing?',
							vals=vals.Enum('LIN', 'LOG', 'STE'),
							get_parser=str.rstrip)
		
		self.add_parameter('state',
							label=f'channel {channum} sweep state',
							set_cmd=f':SOURce{channum}:SWEep:STATe {{}}',
							get_cmd=f':SOURce{channum}:SWEep:STATe?',
							vals=vals.Enum('ON', 'OFF'),
							get_parser=str.rstrip)
		
		self.add_parameter('step',
							label=f'channel {channum} sweep steps',
							set_cmd=f':SOURce{channum}:SWEep:STEP {{}}',
							get_cmd=f':SOURce{channum}:SWEep:STEP?',
							vals=vals.MultiType(vals.Enum('MIN', 'MAX'), vals.Ints(2,1024)),
							get_parser=_int_parser)
		
		self.add_parameter('time',
							label=f'channel {channum} sweep time',
							set_cmd=f':SOURce{channum}:SWEep:TIME {{}}',
							get_cmd=f':SOURce{channum}:SWEep:TIME?',
							vals=vals.MultiType(vals.Enum('MIN', 'MAX'), vals.Numbers(1e-3,500)),
							unit='s',
							get_parser=float)
		
		self.add_parameter('trigger_slope',
							label=f'channel {channum} sweep trigger slope',
							set_cmd=f':SOURce{channum}:SWEep:TRIGger:SLOPe {{}}',
							get_cmd=f':SOURce{channum}:SWEep:TRIGger:SLOPe?',
							vals=vals.Enum('POS', 'NEG'),
							get_parser=str.rstrip)
		
		self.add_parameter('trigger_source',
							label=f'channel {channum} sweep trigger source',
							set_cmd=f':SOURce{channum}:SWEep:TRIGger:SOURce {{}}',
							get_cmd=f':SOURce{channum}:SWEep:TRIGger:SOURce?',
							vals=vals.Enum('INT', 'EXT', 'MAN'),
							get_parser=str.rstrip)
		
		freq_module=SweepFrequency(self, 'frequency')
		self.add_submodule('frequency', freq_module)

		marker_module=SweepMarker(self, 'marker')
		self.add_submodule('marker', marker_module)
	
	def sweep_trigger(self): self.write(f':SOURce{self.channum}:SWEep:TRIGger:IMMediate')
   
class SweepFrequency(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		channum=parent.channum
		
		# SOURCE MENU
		self.add_parameter('center',
						   label=f'channel {channum} frequency center',
						   set_cmd=f':SOURce{channum}:FREQuency:CENTer {{}}',
						   get_cmd=f':SOURce{channum}:FREQuency:CENTer?',
						   vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(1e-6,30e6)),
						   unit='Hz',
						   get_parser=float)
		
		self.add_parameter('span',
						   label=f'channel {channum} frequency span',
						   set_cmd=f':SOURce{channum}:FREQuency:SPAN {{}}',
						   get_cmd=f':SOURce{channum}:FREQuency:SPAN?',
						   vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(1e-6,30e6)),
						   get_parser=float)
		
		self.add_parameter('start',
						   label=f'channel {channum} frequency start',
						   set_cmd=f':SOURce{channum}:FREQuency:STARt {{}}',
						   get_cmd=f':SOURce{channum}:FREQuency:STARt?',
						   vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(1e-6,30e6)),
						   get_parser=float)
		
		self.add_parameter('stop',
						   label=f'channel {channum} frequency stop',
						   set_cmd=f':SOURce{channum}:FREQuency:STOP {{}}',
						   get_cmd=f':SOURce{channum}:FREQuency:STOP?',
						   vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(1e-6,30e6)),
						   get_parser=float)

class SweepMarker(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		channum=parent.channum
		self.channum=channum
		
		# MARKER MENU
		self.add_parameter('_frequency',
						   label=f'channel {channum} marker frequency',
						   set_cmd=f':SOURce{channum}:MARKer:FREQuency {{}}',
						   get_cmd=f':SOURce{channum}:MARKer:FREQuency?',
						   docstring='Set between start frequency and stop frequency',
						   unit='Hz',
						   get_parser=float)
		
		self.add_parameter('state',
						   label=f'channel {channum} marker state',
						   set_cmd=f':SOURce{channum}:MARKer[:STATe] {{}}',
						   get_cmd=f':SOURce{channum}:MARKer[:STATe]?',
						   vals=vals.Enum('ON', 'OFF'),
						   get_parser=str.rstrip)

	def frequency(self, frequency: float=None):
		if frequency==None:
			return self._frequency()
		freq_start=float(self.ask(f':SOURce{self.channum}:FREQuency:STARt?'))
		freq_stop=float(self.ask(f':SOURce{self.channum}:FREQuency:STOP?'))
		vals.MultiType(vals.Enum('MIN', 'MAX'), vals.Numbers(freq_start, freq_stop))
		self._frequency(frequency)
				  
class Trace(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		channum=parent.channum
		
		# TRACE MENU
		
		self.add_parameter('_upload',
							label=f'Channel {channum} waveform table download to DDRIII internal memory',
							set_cmd=f':SOURce{channum}:TRACe:DATA:DAC16 VOLATILE {{}}')
		
	def upload(self, flag: str, data: str):
		vals.Enum('CON', 'END').validate(flag)
		self._upload(f'{flag},{data}')
						
class Track(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		channum=parent.channum
		
		# TRACK MENU
		
		self.add_parameter('track',
							label=f'channel {channum} track state',
							set_cmd=f':SOURce{channum}:TRACK {{}}',
							get_cmd=f':SOURce{channum}:TRACK?',
							vals=vals.Enum('ON', 'OFF', 'INV'),
							get_parser=str.rstrip)

class Trigger(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		channum=parent.channum
		
		# TRIGGER MENU 
		
		self.add_parameter('_delay',
							label=f'channel {channum} burst delay',
							set_cmd=f':TRIGger{channum}:DELay {{}}',
							get_cmd=f':TRIGger{channum}:DELay?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(0,100)),
							unit='s',
							get_parser=float)
		
		self.add_parameter('slope',
							label=f'channel {channum} trigger slope',
							set_cmd=f':TRIGger{channum}:SLOPe {{}}',
							get_cmd=f':TRIGger{channum}:SLOPe?',
							vals=vals.Enum('POS', 'NEG'),
							get_parser=str.rstrip)
		
		self.add_parameter('source',
							label=f'channel {channum} trigger source',
							set_cmd=f':TRIGger{channum}:SOURce {{}}',
							get_cmd=f':TRIGger{channum}:SOURce?',
							vals=vals.Enum('INT', 'EXT', 'BUS'),
							get_parser=str.rstrip)

	def delay(self, delay: float=None):
		if delay==None:
			return self._delay()
		wf_period=1/parent.frequency()
		n_cycles=float(self.ask(f':SOURce{channum}:BURSt:NCYCles?'))
		p_burst=float(self.ask(f':SOURce{channum}:BURSt:INTernal:PERiod?'))
		limit=p_burst-wf_period*n_cycles-2e-6
		if self.trigger_source()=='INT':
			if delay<0 or delay>limit or delay not in ['MIN','MAX']:
				raise ValueError('Trigger delay is outside limit.\n'
								'Must be between 0 and burst period minus waveform period times number of cycles minus 2us when on internal trigger\n'
								f'Currently must be less than {limit}\n')
		else:
			self._delay(delay)
	
	def trigger(self): self.write(f':TRIGger{self.channum}:IMMediate')

class Voltage(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		channum=parent.channum
		
		# VOLTAGE MENU
		
		self.add_parameter('couple_state',
							label=f'channel {channum} amplitude coupling',
							set_cmd=f':SOURce{channum}:VOLTage:COUPle:STATe {{}}',
							get_cmd=f':SOURce{channum}:VOLTage:COUPle:STATe?',
							vals=vals.Enum('ON', 'OFF'),
							get_parser=str.rstrip)
		
		self.add_parameter('amplitude',
							label=f'channel {channum} waveform amplitude',
							set_cmd=f':SOURce{channum}:VOLTage:LEVel:IMMediate:AMPLitude {{}}',
							get_cmd=f':SOURce{channum}:VOLTage:LEVel:IMMediate:AMPLitude?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers(2e-3)),
							unit='Vpp',
							get_parser=float)

							# TODO amplitude vals

		self.add_parameter('level',
							label=f'Channel {channum} waveform level',
							set_cmd=self.amplitude,
							get_cmd=self.amplitude,
							docstring='Wraps the amplitude parameter')
		
		self.add_parameter('_high_level',
							label=f'channel {channum} waveform high level',
							set_cmd=f':SOURce{channum}:VOLTage:LEVel:IMMediate:HIGH {{}}',
							get_cmd=f':SOURce{channum}:VOLTage:LEVel:IMMediate:HIGH?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers()),
							unit='Vpp',
							get_parser=float)
		
		self.add_parameter('_low_level',
							label=f'channel {channum} waveform low level',
							set_cmd=f':SOURce{channum}:VOLTage:LEVel:IMMediate:LOW {{}}',
							get_cmd=f':SOURce{channum}:VOLTage:LEVel:IMMediate:LOW?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers()),
							unit='Vpp',
							get_parser=float)
		
		self.add_parameter('_offset',
							label=f'channel {channum} waveform offset voltage',
							set_cmd=f':SOURce{channum}:VOLTage:LEVel:IMMediate:OFFSet {{}}',
							get_cmd=f':SOURce{channum}:VOLTage:LEVel:IMMediate:OFFSet?',
							vals=vals.MultiType(vals.Enum('MAX', 'MIN'), vals.Numbers()),
							unit='Vpp',
							get_parser=float)

							# TODO offset vals
		
		self.add_parameter('unit',
							label=f'channel {channum} amplitude unit',
							set_cmd=f':SOURce{channum}:VOLTage:UNIT {{}}',
							get_cmd=f':SOURce{channum}:VOLTage:UNIT?',
							vals=vals.Enum('VPP','VRMS', 'DBM'),
							get_parser=str.rstrip)

							# TODO maybe unit?
						
	def high_level(self, high_level: float=None):
		if high_level==None:
			return self._high_level()
		else:
			lim_max=self._offset()+self._amplitude()/2
			lim_min=self.offset()-self._amplitude()/2
			if high_level>lim_max or high_level<lim_min or high_level not in ['MIN', 'MAX']:
				raise ValueError(f'Voltage {high_level} must be less than the offset plus half the amplitude \n'
								'And more than offset minus half the amplitude\n'
								f'Currently must be between {lim_min} and {lim_max}')
			else:
				self._high_level(high_level)

	def low_level(self, low_level: float=None):
		if low_level==None:
			return self._low_level()
		else:
			lim_max=self._offset()+self._amplitude()/2
			lim_min=self.offset()-self._amplitude()/2
			if low_level>lim_max or low_level<lim_min or low_level not in ['MIN', 'MAX']:
				raise ValueError(f'Voltage {low_level} must be less than the offset plus half the amplitude \n'
								'And more than offset minus half the amplitude\n'
								f'Currently must be between {lim_min} and {lim_max}')
			else:
				self._high_level(high_level)
	  

		
	def beeper(self): self.write(':SYSTem:BEEPer:IMMediate')
	
	def LAN_apply(self): self.write(':SYSTem:COMMunicate:LAN:APPLy')
	
	def copy(self, file: str, target_directory: str):
		self._copy(f'{target_directory},{file}')
		
	def key_lock(self, key: str, lock: str=None):
		vals.Enum('HOME','MENU','PRESET','STORE','UTILITY','HELP','LOCK','TRIG','LEFT','RIGHT','KNOB','OUTPUT1','OUTPUT2','COUNTER','ALL').validate(key)
		if lock==None:
			return {'ON':1,'OFF':0}[int(self.ask(f'SYSTem:KLOCk {key}'))]
		else:
			vals.Enum('ON','OFF').validate(lock)
			self._key_lock(f'{key},{lock}')
	
class Rigol_DG800(VisaInstrument):
	'''
	Rigol DG800 QCoDes driver
	Structure:
		Instrument-
			-counter
			-display
			-license
			-mass_memory
			-memory{i}
			-screenshot
			-output channel (ch{i})
				-coupling
				-burst
				-dualtone
				-harmonic
						-order
				-modulation- 
						-amplitude
						-amplitude shift key
						-frequency
						-frequency shift key
						-phase
						-phase shift key
						-pulse width
				-PRBS
				-pulse
				-pulse_function
				-ramp
				-RS232
				-sequence
				-source_frequency
				-square
				-sum
				-sweep-	
						-frequency
						-marker
				-trace
				-track
				-trigger
				-voltage
	'''
	def __init__(self, name, address, **kwargs):
		super().__init__(name, address, **kwargs)

		self.model=self.IDN()['model']

		self._max_freqs={'DG81': 10e6,
                        'DG82': 25e6,
                        'DG83': 35e6
                        }

		self.max_freq=self._max_freqs[self.model[:-1]]

		channel_num=int(self.model[-1])
		for i in range(1,channel_num+1):
			channel = OutputChannel(self, f'ch{i}', i)
			self.add_submodule(f'ch{i}', channel)

		self.add_parameter('ESE',
							label='standard event register bit enable',
							set_cmd='*ESE {}',
							get_cmd='*ESE?',
							vals=vals.Ints())
					
		self.add_parameter('ESR',
							label='stadnard event register event query',
							get_cmd='*ESR?',
							get_parser=str.rstrip)

		self.add_parameter('identify',
							label='identify instrument',
							get_cmd='*IDN?',
							get_parser=str.rstrip)

		self.add_parameter('OPC',
							label='operation complete bit',
							get_cmd='*OPC?',
							get_parser=int)

		self.add_parameter('OPT',
							label='installation state of option query',
							get_cmd='*OPT?',
							get_parser=str.rstrip)

		self.add_parameter('PSC',
							label='register clearing at power on state',
							set_cmd='*PSC {}',
							get_cmd='*PSC?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('RCL',
							label='recall state file',
							set_cmd='*RCL {}',
							vals=vals.Ints(0,5))

		self.add_parameter('SAV',
							label='save state to file',
							set_cmd='*SAV {}',
							vals=vals.Ints(0,5))

		self.add_parameter('SRE',
							label='status byte register bit enable',
							set_cmd='*SRE {}',
							get_cmd='*SRE?',
							vals=vals.Ints(),
							get_parser=float)

		self.add_parameter('STB',
							label='status byte register query',
							get_cmd='*STB?',
							get_parser=str.rstrip)

		self.add_parameter('memory_state_recall',
							label='Recall memory storage state file on power on',
							set_cmd=':MEMory:STATe:RECall:AUTO {}',
							get_cmd=':MEMory:STATe:RECall:AUTO?',
							get_parser=str.rstrip,
							val_mapping={'ON':1,'OFF':0})

		self.add_parameter('memory_state_number',
							label='Number of storage locations',
							get_cmd=':MEMory:NSTates?',
							get_parser=_int_parser)

		self.add_parameter('memory_files',
							label='Storage file names',
							get_cmd=':MEMory:STATe:CATalog?',
							get_parser=str.rstrip)
			
		counter_module=Counter(self, 'counter')
		self.add_submodule('counter', counter_module)

		display_module=Display(self, 'display')
		self.add_submodule('display', display_module)

		screenshot_module=Screenshot(self, 'screenshot')
		self.add_submodule('screenshot', screenshot_module)

		license_module=License(self, 'license')
		self.add_submodule('license', license_module)

		for i in range(1,self.memory_state_number()+1):
			memory_module=Memory(self, f'memory{i}', i)
			self.add_submodule(f'memory{i}', memory_module)

		massmemory_module=MassMemory(self, 'mass_memory')
		self.add_submodule('mass_memory', massmemory_module)

	def clear(self): self.write('*CLS')
	def OPC(self): self.write('*OPC')	
	def reset(self): self.write('*RST')
	def trigger(self): self.write('*TRG')	
	def wait(self): self.write('*WAI')
