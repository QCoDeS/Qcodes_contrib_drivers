'''
Driver for Rigol DSA800 spectrum analyzer

Written by Ben Mowbray (http://wp.lancs.ac.uk/laird-group/)

Examples:

	***Setting up and example test***

	$ from qcodes.instrument_drivers.rigol.Rigol_DSA800 import RigolDSA800
	$ ds_1 = RigolDSA800('rs_800_1', 'USB0::0x1AB1::0x0960::DSA8A191400227::0::INSTR')
	$ ds_1.calibrate.auto(1) # Turns on auto calibration mode
	$ ds_1.sense.frequency.frequency_center(500) # Sets center frequency 

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

class Calculate(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('bandwidth_number',
							label='value of N in bandwidth measurement',
							set_cmd=':CALCulate:BANDwidth:NDB {}',
							get_cmd=':CALCulate:BANDwidth:NDB?',
							vals=vals.Numbers(-100,100),
							unit='dB',
							get_parser=float)

		self.add_parameter('bandwidth_result',
							label='bandiwth number query',
							get_cmd=':CALCulate:BANDwidth:RESult?',
							get_parser=float)

		self.add_parameter('x_domain',
							label='x axis frequency or time domain',
							set_cmd=':CALCulate:LLINe:CONTrol:DOMain {}',
							get_cmd=':CALCulate:LLINe:CONTrol:DOMain?',
							vals=vals.Enum('FREQ', 'TIME'),
							get_parser=str.rstrip)

		self.add_parameter('fail',
							label='pass fail query',
							get_cmd=':CALCulate:LLINe:FAIL?',
							get_parser=str.rstrip)

		self.add_parameter('fail_ratio',
							label='pass fail ratio query',
							get_cmd=':CALCulate:LLINe:FAIL:RATIo?',
							get_parser=float)

		self.add_parameter('fail_stop',
							label='stop test on fail status',
							set_cmd=':CALCulate:LLINe:FAIL:STOP:STATe {}',
							get_cmd=':CALCulate:LLINe:FAIL:STOP:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('counter_resolution',
							label='resolution of frequency counter',
							set_cmd=':CALCulate:MARKer:FCOunt:RESolution {}',
							get_cmd=':CALCulate:MARKer:FCOunt:RESolution?',
							val_mapping={'1Hz':1, '10Hz':10, '100Hz':100, '1kHz':1000, '10kHz':10000, '100kHz':100000},
							get_parser=str.rstrip)

		self.add_parameter('counter_auto',
							label='frequency counter resolution auto',
							set_cmd=':CALCulate:MARKer:FCOunt:RESolution:AUTO {}',
							get_cmd=':CALCulate:MARKer:FCOunt:RESolution:AUTO?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('frequency_counter',
							label='query frequency counter reading',
							get_cmd=':CALCulate:MARKer:FCOunt:X?',
							get_parser=int)

		self.add_parameter('counter_state',
							label='frequency counter state',
							set_cmd=':CALCulate:MARKer:FCOunt:STATe {}',
							get_cmd=':CALCulate:MARKer:FCOunt:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)	

		self.add_parameter('marker_table',
							label='marker table',
							set_cmd=':CALCulate:MARKer:TABLe:STATe {}',
							get_cmd=':CALCulate:MARKer:TABLe:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('signal_track',
							label='signal track state',
							set_cmd=':CALCulate:MARKer:TRACking:STATe {}',
							get_cmd=':CALCulate:MARKer:TRACking:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('normalization',
							label='normalization state',
							set_cmd=':CALCulate:NTData:STATe {}',
							get_cmd=':CALCulate:NTData:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		line_limit=LimitLine(self, 'limit_line')
		self.add_submodule('limit_line', line_limit)

		marker=MarkerNumber(self, 'marker')
		self.add_submodule('marker', marker)
	
	def markers_disable(self): self.write(':CALCulate:MARKer:AOFF')
	def delete_limit_line(self): self.write(':CALCulate:LLINe:ALL:DELete')

class Calibrate(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('auto',
							label='auto calibration status',
							set_cmd=':CALibration:AUTO {}',
							get_cmd=':CALibration:AUTO?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

	def calibration(self): self.write(':CALibration:ALL')

class Configure(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('configure',
							label='configure query',
							get_cmd=':CONFigure?',
							get_parser=str.rstrip)

	def ACPower(self): self.write(':CONFigure:ACPower')
	def CHPower(self): self.write(':CONFigure:CHPower')
	def CNRatio(self): self.write(':CONFigure:CNRatio')
	def EBWidth(self): self.write(':CONFigure:EBWidth')
	def Harmonic_Distortion(self): self.write(':CONFigure:HDISt')
	def OBWidth(self): self.write(':CONFigure:OBWidth')
	def PF(self): self.write(':CONFigure:PF')
	def spectrum_analyzer(self): self.write(':CONFigure:SANalyzer')
	def TOI(self): self.write(':CONFigure:TOI')
	def TPower(self): self.write(':CONFigure:TPOWer')

class Couple(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('couple',
							label='couple relationship status',
							set_cmd=':COUPle {}',
							get_cmd=':COUPle?',
							vals=vals.Enum('ALL', 'NONE'),
							get_parser=str.rstrip)

class Display(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('active_function_area',
							label='position of active function area',
							set_cmd=':DISPlay:AFUnction:POSition {}',
							get_cmd=':DISPlay:AFUnction:POSition?',
							vals=vals.Enum('BOTT', 'CENT', 'TOP'),
							get_parser=str.rstrip)

		self.add_parameter('clock',
							label='time and date setting',
							set_cmd=':DISPlay:ANNotation:CLOCk:STATe {}',
							get_cmd=':DISPlay:ANNotation:CLOCk:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('brightness',
							label='screen brightness',
							set_cmd=':DISPlay:BRIGhtness {}',
							get_cmd=':DISPlay:BRIGhtness?',
							vals=vals.Ints(1,10),
							get_parser=int)

		self.add_parameter('display',
							label='screen status',
							set_cmd=':DISPlay:ENABle {}',
							get_cmd=':DISPlay:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('message_display',
							label='message display status',
							set_cmd=':DISPlay:MSGswitch:STATe {}',
							get_cmd=':DISPlay:MSGswitch:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('userkey',
							label='userkey status',
							set_cmd=':DISPlay:UKEY:STATe {}',
							get_cmd=':DISPlay:UKEY:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('grid_brightness',
							label='screen grid brightness',
							set_cmd=':DISPlay:WINdow:TRACe:GRATicule:GRID {}',
							get_cmd=':DISPlay:WINdow:TRACe:GRATicule:GRID?',
							vals=vals.Ints(0,10),
							get_parser=int)

		self.add_parameter('x_scale',
							label='x axis scale type',
							set_cmd=':DISPlay:WINdow:TRACe:X:SCALe:SPACing {}',
							get_cmd=':DISPlay:WINdow:TRACe:X:SCALe:SPACing?',
							vals=vals.Enum('LIN', 'LOG'),
							get_parser=str.rstrip)

		self.add_parameter('dl_position',
							label='display line position',
							set_cmd=':DISPlay:WINdow:TRACe:Y:DLINe {}',
							get_cmd=':DISPlay:WINdow:TRACe:Y:DLINe?',
							vals=vals.Numbers(-400,320),
							unit='dBm',
							get_parser=float)

		self.add_parameter('display_line',
							label='display line status',
							set_cmd=':DISPlay:WINdow:TRACe:Y:DLINe:STATe {}',
							get_cmd=':DISPlay:WINdow:TRACe:Y:DLINe:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('reference_level',
							label='reference level of normalisation',
							set_cmd=':DISPlay:WINdow:TRACe:Y:SCALe:NRLevel {}',
							get_cmd=':DISPlay:WINdow:TRACe:Y:SCALe:NRLevel?',
							vals=vals.Numbers(-200,200),
							unit='dB',
							get_parser=float)

		self.add_parameter('reference_position',
							label='reference position of normalisation',
							set_cmd=':DISPlay:WINdow:TRACe:Y:SCALe:NRPosition {}',
							get_cmd=':DISPlay:WINdow:TRACe:Y:SCALe:NRPosition?',
							vals=vals.Ints(0,100),
							unit='%',
							get_parser=int)

		self.add_parameter('y_axis',
							label='y axis scale',
							set_cmd=':DISPlay:WINdow:TRACe:Y:SCALe:PDIVision {}',
							get_cmd=':DISPlay:WINdow:TRACe:Y:SCALe:PDIVision?',
							vals=vals.Numbers(0.1,20),
							unit='dB',
							get_parser=float)

		self.add_parameter('reference',
							label='reference level',
							set_cmd=':DISPlay:WINdow:TRACe:Y:SCALe:RLEVel {}',
							get_cmd=':DISPlay:WINdow:TRACe:Y:SCALe:RLEVel?',
							vals=vals.Numbers(-100,20),
							unit='dBm',
							get_parser=float)

		self.add_parameter('reference_offset',
							label='offset of reference level',
							set_cmd=':DISPlay:WINdow:TRACe:Y:SCALe:RLEVel:OFFSet {}',
							get_cmd=':DISPlay:WINdow:TRACe:Y:SCALe:RLEVel:OFFSet?',
							vals=vals.Numbers(-300,300),
							unit='dB',
							get_parser=float)

		self.add_parameter('y_scale',
							label='y axis scale type',
							set_cmd=':DISPlay:WINdow:TRACe:Y:SCALe:SPACing {}',
							get_cmd=':DISPlay:WINdow:TRACe:Y:SCALe:SPACing?',
							vals=vals.Enum('LIN', 'LOG'),
							get_parser=str.rstrip)

class Fetch(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('AC',
							label='adjacent channel query',
							get_cmd=':FETCh:ACPower?',
							get_parser=str.rstrip)

		self.add_parameter('AC_lower',
							label='lower adjacent channel power query',
							get_cmd=':FETCh:ACPower:LOWer?',
							get_parser=float)

		self.add_parameter('AC_main',
							label='main adjacent channel power query',
							get_cmd=':FETCh:ACPower:MAIN?',
							get_parser=float)

		self.add_parameter('AC_upper',
							label='upper adjacent channel power query',
							get_cmd=':FETCh:ACPower:UPPer?',
							get_parser=float)

		self.add_parameter('measurement',
							label='channel power measurement query',
							get_cmd=':FETCh:CHPower?',
							get_parser=str.rstrip)

		self.add_parameter('channel_power',
							label='channel power query',
							get_cmd=':FETCh:CHPower:CHPower?',
							get_parser=float)

		self.add_parameter('density',
							label='channel power spectral density query',
							get_cmd=':FETCh:CHPower:DENSity?',
							get_parser=float)

		self.add_parameter('CN_ratio',
							label='C/N ratio measurement',
							get_cmd=':FETCh:CNRatio?',
							get_parser=str.rstrip)

		self.add_parameter('noise',
							label='noise power query',
							get_cmd=':FETCh:CNRatio:NOISe?',
							get_parser=float)

		self.add_parameter('emission_bandwidth',
							label='emission bandwidth measurement query',
							get_cmd=':FETCh:EBWidth?',
							get_parser=float)

		self.add_parameter('harmonics_amplitude_all',
							label='first ten harmonics amplitude query',
							get_cmd=':FETCh:HARMonics:AMPLitude:ALL?',
							get_parser=str.rstrip)

		self.add_parameter('harmonics_amplitude',
							label='specified harmonic amplitude query',
							get_cmd=':FETCh:HARMonics:AMPLitude? {}',
							vals=vals.Ints(1,10),
							get_parser=float)

		self.add_parameter('harmonics_distortion',
							label='harmonic distortion percentage query',
							get_cmd=':FETCh:HARMonics:DISTortion?',
							get_parser=float)

		self.add_parameter('harmonics_frequency_all',
							label='first ten harmonics frequency query',
							get_cmd=':FETCh:HARMonics:FREQuency:ALL?',
							get_parser=str.rstrip)

		self.add_parameter('harmonics_frequency',
							label='specified harmonic frequency query',
							get_cmd=':FETCh:HARMonics:FREQuency?',
							get_parser=float)

		self.add_parameter('harmonics_fundamental',
							label='fundamental frequency query',
							get_cmd=':FETCh:HARMonics:FUNDamental?',
							get_parser=float)

		self.add_parameter('OB_measurement',
							label='occupied bandwidth measurement query',
							get_cmd=':FETCh:OBWidth?',
							get_parser=str.rstrip)

		self.add_parameter('occupied_bandwidth',
							label='occupied bandwidth query',
							get_cmd=':FETCh:OBWidth:OBWidth?',
							get_parser=float)

		self.add_parameter('OB_error',
							label='transmit frequency error query',
							get_cmd=':FETCh:OBWidth:OBWidth:FERRor?',
							get_parser=float)

		self.add_parameter('TOI_intercept',
							label='TOI measurement query',
							get_cmd=':FETCh:TOIntercept?',
							get_parser=str.rstrip)

		self.add_parameter('TOI_IP3',
							label='IP3 query',
							get_cmd=':FETCh:TOIntercept:IP3?',
							get_parser=float)

		self.add_parameter('T_power',
							label='T-power measurement query',
							get_cmd=':FETCh:TPOWer?',
							get_parser=float)

class Format(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('border',
							label='byte order',
							set_cmd=':FORMat:BORDer {}',
							get_cmd=':FORMat:BORDer?',
							vals=vals.Enum('NORM', 'SWAP'),
							get_parser=str.rstrip)

		self.add_parameter('trace_data',
							label='format of trace data',
							set_cmd=':FORMat:TRACe:DATA {}',
							get_cmd=':FORMat:TRACe:DATA?',
							vals=vals.Enum('ASC', 'REAL[,32]'),
							get_parser=str.rstrip)

class Hcopy(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('color',
							label='print color',
							set_cmd=':HCOPy:IMAGe:COLor:STATe {}',
							get_cmd=':HCOPy:IMAGe:COLor:STATe?',
							val_mapping={'ON':1,'OFF':0},
							docstring='gray=0,off color=1,on',
							get_parser=str.rstrip)

		self.add_parameter('type',
							label='image type',
							set_cmd=':HCOPy:IMAGe:FTYPe {}',
							get_cmd=':HCOPy:IMAGe:FTYPe?',
							vals=vals.Enum('DEF', 'EXIF'),
							get_parser=str.rstrip)

		self.add_parameter('invert',
							label='inverted print status',
							set_cmd=':HCOPy:IMAGe:INVert {}',
							get_cmd=':HCOPy:IMAGe:INVert?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('time',
							label='date print status',
							set_cmd=':HCOPy:IMAGe:PTIMe {}',
							get_cmd=':HCOPy:IMAGe:PTIMe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('quality',
							label='print quality',
							set_cmd=':HCOPy:IMAGe:QUALity {}',
							get_cmd=':HCOPy:IMAGe:QUALity?',
							vals=vals.Enum('DEF', 'NORM', 'DRAF', 'FINE'),
							get_parser=str.rstrip)

		self.add_parameter('orientation',
							label='print orientation',
							set_cmd=':HCOPy:PAGE:ORIentation {}',
							get_cmd=':HCOPy:PAGE:ORIentation?',
							vals=vals.Enum('LAND', 'PORT'),
							get_parser=str.rstrip)

		self.add_parameter('copies',
							label='print copies',
							set_cmd=':HCOPy:PAGE:PRINts {}',
							get_cmd=':HCOPy:PAGE:PRINts?',
							vals=vals.Ints(1,999),
							get_parser=int)

		self.add_parameter('size',
							label='page size',
							set_cmd=':HCOPy:PAGE:SIZE {}',
							get_cmd=':HCOPy:PAGE:SIZE?',
							vals=vals.Enum('DEF', 'A4', 'A5', 'A6', 'B5'),
							get_parser=str.rstrip)

	def abort(self): self.write(':HCOPy:ABORt')
	def hcopy(self): self.write(':HCOPy:IMMediate')
	def resume(self): self.write(':HCOPy:RESume')

class Initiate(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('mode',
							label='sweep or measurement mode',
							set_cmd=':INITiate:CONTinuous {}',
							get_cmd=':INITiate:CONTinuous?',
							val_mapping={'ON':1,'OFF':0},
							docstring='continuous=1,on single =0,off',
							get_parser=str.rstrip)

	def initiate(self): self.write(':INITiate:IMMediate')
	def pause(self): self.write(':INITiate:PAUSe')
	def restart(self): self.write(':INITiate:RESTart')
	def resume(self): self.write(':INITiate:RESume')

class Input(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('impedance',
							label='impedance inmput',
							set_cmd=':INPut:IMPedance {}',
							get_cmd=':INPut:IMPedance?',
							vals=vals.Enum(50,75),
							get_parser=float)

class LimitLine(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		upper_limit=line_limit(self, 'upper', 2)
		self.add_submodule('upper', upper_limit)

		lower_limit=line_limit(self, 'lower', 1)
		self.add_submodule('lower', lower_limit)

class line_limit(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, linenum):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('interpolation_mode',
							label=f'line {linenum} frequency interpolation mode',
							set_cmd=f':CALCulate:LLINe{linenum}:CONTrol:INTerpolate:TYPE {{}}',
							get_cmd=f':CALCulate:LLINe{linenum}:CONTrol:INTerpolate:TYPE?',
							vals=vals.Enum('LOG', 'LIN'),
							get_parser=str.rstrip)

		self.add_parameter('_limit_line',
							label=f'line {linenum} limit line',
							set_cmd=f':CALCulate:LLINe{linenum}:DATA {{}}',
							get_cmd=f':CALCulate:LLINe{linenum}:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('_data_merge',
							label=f'line {linenum} add points to edited limit line',
							set_cmd=f':CALCulate:LLINe{linenum}:DATA:MERGe {{}}')

		self.add_parameter('delete',
							label=f'line {linenum} delete specified limit line',
							set_cmd=f':CALCulate:LLINe{linenum}:DELete')

		self.add_parameter('REL_ampl',
							label=f'line {linenum} REL amplitude state',
							set_cmd=f':CALCulate:LLINe{linenum}:RELAmpt:STATe {{}}',
							get_cmd=f':CALCulate:LLINe{linenum}:RELAmpt?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('REL_freq',
							label=f'line {linenum} REL frequency state',
							set_cmd=f':CALCulate:LLINe{linenum}:RELFreq:STATe {{}}',
							get_cmd=f':CALCulate:LLINe{linenum}:RELFreq?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('limit_state',
							label=f'line {linenum} line limit status',
							set_cmd=f':CALCulate:LLINe{linenum}:STATe {{}}',
							get_cmd=f':CALCulate:LLINe{linenum}:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

	def limit_line(self, x_axis: list, ampl: list, connected: list):
		'''
		limit line parameter wrapper
		Args:
			x_axis: Hz/s
			ampl: dBm
			connected
		'''
		if len(x_axis)!=len(ampl) or len(x_axis)!=len(connected):
			raise ValueError('length of x axis and ampl and connected should be the same')
		dom=self.ask(':CALCulate:LLINe:CONTrol:DOMain?').rstrip()
		if dom=='FREQ':
			vals.Lists(vals.Numbers(0,self.freq_max)).validate(x_axis)
		else:
			vals.Lists(vals.Numbers(0,7.5e3)).validate(x_axis)
		vals.Numbers(-400,320).validate(ampl)
		vals.Enum(0,1).validate(connected)
		input=f'{x_axis},{ampl},{connected}'
		self._limit_line(input)
		
	def data_merge(self, x_axis: list, ampl: list, connected: list):
		'''
		data merge parameter wrapper
		Args:
			x_axis: Hz/s
			ampl: dBm
			connected
		'''
		if len(x_axis)!=len(ampl) or len(x_axis)!=len(connected):
			raise ValueError('length of x axis and ampl and connected should be the same')
		dom=self.ask(':CALCulate:LLINe:CONTrol:DOMain?').rstrip()
		if dom=='FREQ':
			vals.Lists(vals.Numbers(0,self.freq_max)).validate(x_axis)
		else:
			vals.Lists(vals.Numbers(0,7.5e3)).validate(x_axis)
		vals.Numbers(-400,320).validate(ampl)
		vals.Enum(0,1).validate(connected)
		input=f'{x_axis},{ampl},{connected}'
		self._data_merge(input)

class Marker(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, marknum):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('continuous_peak',
							label=f'marker {marknum} continuous peak search state',
							set_cmd=f':CALCulate:MARKer{marknum}:CPEak:STATe {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:CPEak:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('special_measurement',
							label=f'marker {marknum} special measurement type',
							set_cmd=f':CALCulate:MARKer{marknum}:FUNCtion {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:FUNCtion?',
							vals=vals.Enum('NDB', 'NOIS', 'OFF'),
							get_parser=str.rstrip)

		self.add_parameter('marker_mode',
							label=f'marker {marknum} type of specified marker',
							set_cmd=f':CALCulate:MARKer{marknum}:MODE {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:FUNCtion?',
							vals=vals.Enum('POS', 'DELT', 'BAND', 'SPAN'),
							get_parser=str.rstrip)

		self.add_parameter('excursion',
							label=f'marker {marknum} peak excursion',
							set_cmd=f':CALCulate:MARKer{marknum}:PEAK:EXCursion {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:PEAK:EXCursion?',
							vals=vals.Numbers(0,200),
							unit='dB',
							get_parser=float)

		self.add_parameter('peak_mode',
							label=f'marker {marknum} peak search mode',
							set_cmd=f':CALCulate:MARKer{marknum}:PEAK:SEARch:MODE {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:PEAK:SEARch:MODE?',
							vals=vals.Enum('PAR', 'MAX'),
							get_parser=str.rstrip)

		self.add_parameter('peak_threshold',
							label=f'marker {marknum} peak threshold',
							set_cmd=f':CALCulate:MARKer{marknum}:PEAK:THReshold {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:PEAK:THReshold?',
							vals=vals.Numbers(-200,0),
							unit='dBm',
							get_parser=float)

		self.add_parameter('marker_state',
							label=f'marker {marknum} specified marker state',
							set_cmd=f':CALCulate:MARKer{marknum}:STATe {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('marker_trace',
							label=f'marker {marknum} trace of specified marker',
							set_cmd=f':CALCulate:MARKer{marknum}:TRACe {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:TRACe?',
							vals=vals.Ints(1,4),
							get_parser=int)

		self.add_parameter('trace_auto',
							label=f'marker trace auto status',
							set_cmd=f':CALCulate:MARKer{marknum}:TRACe:AUTO {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:TRACe:AUTO?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('reflection_coefficient',
							label=f'marker {marknum} query reflection coefficient',
							get_cmd=f':CALCulate:MARKer{marknum}:VSRefl?',
							get_parser=float)

		self.add_parameter('VSWR',
							label=f'marker {marknum} query VSWR',
							get_cmd=f':CALCulate:MARKer{marknum}:VSValue?',
							get_parser=float)

		self.add_parameter('_marker_x',
							label=f'marker {marknum} x axis value of marker',
							set_cmd=f':CALCulate:MARKer{marknum}:X {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:X?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('_center_x',
							label=f'marker {marknum} x axis center value',
							set_cmd=f':CALCulate:MARKer{marknum}:X:CENTer {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:X:CENTer?',
							vals=vals.Numbers(),
							get_parser=float)
		
		self.add_parameter('normal_position',
							label=f'marker {marknum} position of specified normal marker',
							set_cmd=f':CALCulate:MARKer{marknum}:X:POSition {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:X:POSition?',
							vals=vals.Ints(0,600),
							get_parser=int)

		self.add_parameter('center_position',
							label=f'marker {marknum} center position of span pair marker',
							set_cmd=f':CALCulate:MARKer{marknum}:X:POSition:CENTer {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:X:POSition:CENTer?',
							vals=vals.Ints(0,600),
							get_parser=int)

		self.add_parameter('span_position',
							label=f'marker {marknum} number of points correspoding to span pair marker',
							set_cmd=f':CALCulate:MARKer{marknum}:X:POSition:SPAN {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:X:POSition:SPAN?',
							vals=vals.Ints(0,600),
							get_parser=int)

		self.add_parameter('start_position',
							label=f'marker {marknum} position of reference marker of delta pair marker',
							set_cmd=f':CALCulate:MARKer{marknum}:X:POSition:STARt {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:X:POSition:STARt?',
							vals=vals.Ints(0,600),
							get_parser=int)

		self.add_parameter('stop_position',
							label=f'marker {marknum} delta marker position of delta pair marker',
							set_cmd=f':CALCulate:MARKer{marknum}:X:POSition:STOP {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:X:POSition:STOP?',
							vals=vals.Ints(0,600),
							get_parser=int)

		self.add_parameter('readout_mode',
							label=f'marker {marknum} readout mode of x axis',
							set_cmd=f':CALCulate:MARKer{marknum}:X:READout {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:X:READout?',
							vals=vals.Enum('FREQ', 'TIME', 'ITIM', 'PER'),
							get_parser=str.rstrip)

		self.add_parameter('_span_x',
							label=f'marker {marknum} x value of span pair marker',
							set_cmd=f':CALCulate:MARKer{marknum}:X:SPAN {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:X:SPAN?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('_start_x',
							label=f'marker {marknum} x value of reference marker',
							set_cmd=f':CALCulate:MARKer{marknum}:X:STARt {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:X:STARt?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('_stop_x',
							label=f'marker {marknum} x value of delta marker',
							set_cmd=f':CALCulate:MARKer{marknum}:X:STOP {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:X:STOP?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('y_axis',
							label=f'marker {marknum} query y axis value',
							get_cmd=f':CALCulate:MARKer{marknum}:Y?',
							get_parser=int)

	def marker_x(self, parameter: list):
		'''
		x marker parameter wrapper
		Args:
			parameter
		'''
		dom=self.ask(':CALCulate:LLINe:CONTrol:DOMain?').rstrip()
		if dom=='FREQ':
			vals.Lists(vals.Numbers(0,self.freq_max)).validate(parameter)
		else:
			vals.Lists(vals.Numbers(0,7.5e3)).validate(parameter)
		input=f'{parameter}'
		self._marker_x(input)

	def center_x(self, parameter: list):
		'''
		center x parameter wrapper
		Args:
			parameter
		'''
		dom=self.ask(':CALCulate:LLINe:CONTrol:DOMain?').rstrip()
		if dom=='FREQ':
			vals.Lists(vals.Numbers(0,self.freq_max)).validate(parameter)
		else:
			vals.Lists(vals.Numbers(0,7.5e3)).validate(parameter)
		input=f'{parameter}'
		self._center_x(input)

	def span_x(self, parameter: list):
		'''
		span x parameter wrapper
		Args:
			parameter
		'''
		dom=self.ask(':CALCulate:LLINe:CONTrol:DOMain?').rstrip()
		if dom=='FREQ':
			vals.Lists(vals.Numbers(0,self.freq_max)).validate(parameter)
		else:
			vals.Lists(vals.Numbers(0,7.5e3)).validate(parameter)
		input=f'{parameter}'
		self._span_x(input)

	def start_x(self, parameter: list):
		'''
		start x parameter wrapper
		Args:
			parameter
		'''
		dom=self.ask(':CALCulate:LLINe:CONTrol:DOMain?').rstrip()
		if dom=='FREQ':
			vals.Lists(vals.Numbers(0,self.freq_max)).validate(parameter)
		else:
			vals.Lists(vals.Numbers(0,7.5e3)).validate(parameter)
		input=f'{parameter}'
		self._start_x(input)

	def stop_x(self, parameter: list):
		'''
		stop x parameter wrapper
		Args:
			parameter
		'''
		dom=self.ask(':CALCulate:LLINe:CONTrol:DOMain?').rstrip()
		if dom=='FREQ':
			vals.Lists(vals.Numbers(0,self.freq_max)).validate(parameter)
		else:
			vals.Lists(vals.Numbers(0,7.5e3)).validate(parameter)
		input=f'{parameter}'
		self._stop_x(input)

	

	def center_frequency(self): self.write(f':CALCulate:MARKer{marknum}:DELTa:SET:CENTer')
	def spectrum_span(self): self.write(f':CALCulate:MARKer{marknum}:DELTa:SET:SPAN')
	def left(self): self.write(f':CALCulate:MARKer{marknum}:MAXimum:LEFT')
	def max(self): self.write(f':CALCulate:MARKer{marknum}:MAXimum:MAX')
	def next(self): self.write(f':CALCulate:MARKer{marknum}:MAXimum:NEXT')
	def right(self): self.write(f':CALCulate:MARKer{marknum}:MAXimum:RIGHt')
	def min(self): self.write(f':CALCulate:MARKer{marknum}:MINimum')
	def peak_search(self): self.write(f':CALCulate:MARKer{marknum}:PEAK:SET:CF')
	def peak_peak(self): self.write(f':CALCulate:MARKer{marknum}:PTPeak')
	def marker_center(self): self.write(f':CALCulate:MARKer{marknum}:SET:CENTer')
	def reference_level(self): self.write(f':CALCulate:MARKer{marknum}:SET:RLEVel')
	def start_frequency(self): self.write(f':CALCulate:MARKer{marknum}:SET:STARt')
	def spectrum_center(self): self.write(f':CALCulate:MARKer{marknum}:SET:STEP')
	def stop_frequency(self): self.write(f':CALCulate:MARKer{marknum}:SET:STOP')
	
class MarkerNumber(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		marker1=Marker(self, 'marker1', 1)
		self.add_submodule('marker1', marker1)

		marker2=Marker(self, 'marker2', 2)
		self.add_submodule('marker2', marker2)

		marker3=Marker(self, 'marker3', 3)
		self.add_submodule('marker3', marker3)

		marker4=Marker(self, 'marker4', 4)
		self.add_submodule('marker4', marker4)

class MassMemory(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('delete_file',
							label='delete specified file',
							set_cmd=':MMEMory:DELete {}',
							vals=vals.Strings())

		self.add_parameter('disk_information',
							label='query disk information',
							get_cmd=':MMEMory:DISK:INFormation?',
							get_parser=str.rstrip)
		
		self.add_parameter('_amplitude_correction',
							label='amplitude correction of loaded data of file',
							set_cmd=':MMEMory:LOAD:CORRection {}')

		self.add_parameter('load_limit',
							label='load edited limit line file',
							set_cmd=':MMEMory:LOAD:LIMit {}',
							vals=vals.Strings())

		self.add_parameter('load_mtable',
							label='load the edited limit line file',
							set_cmd=':MMEMory:LOAD:MTABle {}',
							vals=vals.Strings())

		self.add_parameter('load_setup',
							label='load specified setup',
							set_cmd=':MMEMory:LOAD:SETUp {}',
							vals=vals.Strings())

		self.add_parameter('load_state',
							label='load specified state',
							set_cmd=':MMEMory:LOAD:STATe 1, {}',
							vals=vals.Strings())

		self.add_parameter('load_trace',
							label='load specified trace',
							set_cmd=':MMEMory:LOAD:TRACe {}',
							vals=vals.Strings())

		self.add_parameter('_move',
							label='rename file',
							set_cmd=':MMEMory:MOVE {}')

		self.add_parameter('_store_correction',
							label='amplitude correction data file',
							set_cmd=':MMEMory:STORe:CORRection {}')

		self.add_parameter('store_limit',
							label='limit line for specified filename',
							set_cmd=':MMEMory:STORe:LIMit {}',
							vals=vals.Strings())

		self.add_parameter('markertable_save',
							label='save marker table in USB with specified filename',
							set_cmd=':MMEMory:STORe:MTABle {}',
							vals=vals.Strings())

		self.add_parameter('peaktable_save',
							label='save peak table in USB with specified filename',
							set_cmd=':MMEMory:STORe:PTABle {}',
							vals=vals.Strings())

		self.add_parameter('results_save',
							label='save results in USB with specified filename',
							set_cmd=':MMEMory:STORe:RESults {}',
							vals=vals.Strings())

		self.add_parameter('screen_save',
							label='save current screen image on USB',
							set_cmd=':MMEMory:STORe:SCReen {}',
							vals=vals.Strings())

		self.add_parameter('setup_save',
							label='save current setting with specified filename',
							set_cmd=':MMEMory:STORe:SETUp {}',
							vals=vals.Strings())

		self.add_parameter('state_save',
							label='save current instrument state',
							set_cmd=':MMEMory:STORe:STATe 1, {}',
							vals=vals.Strings())

		self.add_parameter('_trace_save',
							label='save specified trace with specified filename',
							set_cmd=':MMEMory:STORe:TRACe {}')

		

		

	def amplitude_correction(self, mode, filename):
		'''
		Amplitude correction parameter wrapper
		Args:
			mode
			file
		'''
		vals.Enum('ANT', 'CABL', 'OTH', 'USER').validate(mode)
		vals.Strings().validate(filename)
		input=f'{mode},{filename}'
		self._amplitude_correction(input)

	def move(self, filename1, filename2):
		'''
		Move parameter wrapper
		Args:
			filename1
			filename2
		'''
		vals.Strings().validate(filename1)
		vals.Strings().validate(filename2)
		input=f'{filename1},{filename2}'
		self._move(input)

	def store_correction(self, mode, filename):
		'''
		Store correction parameter wrapper
		Args:
			mode
			filename
		'''
		vals.Enum('ANT', 'CABL', 'OTH', 'USER').validate(mode)
		vals.Strings().validate(filename)
		input=f'{mode},{filename}'
		self._store_correction(input)

	def trace_save(self, mode, filename):
		'''
		Trace save parameter wrapper
		Args:
			mode
			filename
		'''
		vals.Enum('TRACE1', 'TRACE2', 'TRACE3', 'MATH', 'ALL').validate(mode)
		vals.Strings().validate(filename)
		input=f'{mode},{filename}'
		self._trace_save(input)

class Output(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('state',
							label='output of tracking generator',
							set_cmd=':OUTPut:STATe {}',
							get_cmd=':OUTPut:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

class Read(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('AC_power',
							label='query adjacent channel power measurement',
							get_cmd=':READ:ACPower?',
							get_parser=str.rstrip)

		self.add_parameter('AC_power_lower',
							label='query lower power measurement',
							get_cmd=':READ:ACPower:LOWer?',
							get_parser=str.rstrip)

		self.add_parameter('AC_power_main',
							label='query main power measurement',
							get_cmd=':READ:ACPower:MAIN?',
							get_parser=str.rstrip)

		self.add_parameter('AC_power_upper',
							label='query upper power measurement',
							get_cmd=':READ:ACPower:UPPer?',
							get_parser=str.rstrip)

		self.add_parameter('channel_measurement',
							label='query measurement',
							get_cmd=':READ:CHPower?',
							get_parser=str.rstrip)

		self.add_parameter('channel_power',
							label='query channel power',
							get_cmd=':READ:CHPower:CHPower?',
							get_parser=str.rstrip)

		self.add_parameter('density',
							label='query spectral density',
							get_cmd=':READ:CHPower:DENSity?',
							get_parser=str.rstrip)

		self.add_parameter('CN_measurement',
							label='query C/N ratio and return measurement results',
							get_cmd=':READ:CNRatio?',
							get_parser=str.rstrip)

		self.add_parameter('carrier_power',
							label='query carrier power',
							get_cmd=':READ:CNRatio:CARRier?',
							get_parser=str.rstrip)

		self.add_parameter('CN_ratio',
							label='query C/N ratio and return ratio',
							get_cmd=':READ:CNRatio:CNRatio?',
							get_parser=str.rstrip)

		self.add_parameter('noise',
							label='query C/N ratio and return power noise',
							get_cmd=':READ:CNRatio:NOISe?',
							get_parser=str.rstrip)

		self.add_parameter('emission_bandwidth',
							label='query emission bandwidth',
							get_cmd=':READ:EBWidth?',
							get_parser=str.rstrip)

		self.add_parameter('harmonics_amplitude_all',
							label='query amplitude of first ten harmonics',
							get_cmd=':READ:HARMonics:AMPLitude:ALL?',
							get_parser=str.rstrip)

		self.add_parameter('harmonics_amplitude',
							label='query amplitude of specified harmonic',
							get_cmd=':READ:HARMonics:AMPLitude? {}',
							vals=vals.Ints(1,10),
							get_parser=int)

		self.add_parameter('harmonics_distortion',
							label='query harmonics distortion',
							get_cmd=':READ:HARMonics:DISTortion?',
							get_parser=str.rstrip)

		self.add_parameter('harmonics_frequency_all',
							label='query first 10 harmonics frequencies',
							get_cmd=':READ:HARMonics:FREQuency:ALL?',
							get_parser=str.rstrip)

		self.add_parameter('harmonics_frequency',
							label='query specified harmonics frequency',
							get_cmd=':READ:HARMonics:FREQuency? {}',
							vals=vals.Ints(1,10),
							get_parser=int)

		self.add_parameter('harmonics_fundamental',
							label='query fundamental frequency',
							get_cmd=':READ:HARMonics:FUNDamental?',
							get_parser=str.rstrip)

		self.add_parameter('OB_measurement',
							label='query occupied bandwith and return measurement',
							get_cmd=':READ:OBWidth?',
							get_parser=str.rstrip)

		self.add_parameter('occupied_bandwidth',
							label='query and return occupied bandwidth',
							get_cmd=':READ:OBWidth:OBWidth?',
							get_parser=str.rstrip)

		self.add_parameter('OB_error',
							label='query occupied bandwidth and return frequency error',
							get_cmd=':READ:OBWidth:OBWidth:FERRor?',
							get_parser=str.rstrip)

		self.add_parameter('intercept',
							label='query TOI measurement',
							get_cmd=':READ:TOIntercept?',
							get_parser=str.rstrip)

		self.add_parameter('intercept_IP3',
							label='query TOI IP3 measurement',
							get_cmd=':READ:TOIntercept:IP3?',
							get_parser=str.rstrip)

		self.add_parameter('power',
							label='query T-power measurement',
							get_cmd=':READ:TPOWer?',
							get_parser=float,
							unit='dBm/dBmV/V/W',
							docstring='Power unit depends on current Y axis setting')

class Sense(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('detector',
							label='detector type',
							set_cmd=':SENSe:DETector:FUNCtion {}',
							get_cmd=':SENSe:DETector:FUNCtion?',
							vals=vals.Enum('NEG', 'NORM', 'POS', 'RMS', 'SAMP', 'VAV', 'QPE'),
							get_parser=str.rstrip)		

		self.add_parameter('reference',
							label='reference state query',
							get_cmd=':SENSe:EXTRef:STATe?',
							get_parser=float)				

		self.add_parameter('VSWR',
							label='VSWR status',
							set_cmd=':SENSe:VSWR:STATe {}',
							get_cmd=':SENSe:VSWR:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		ac_module=AC(self, 'AC')
		self.add_submodule('AC', ac_module)

		frequency_module=Frequency(self, 'frequency')
		self.add_submodule('frequency', frequency_module)

		bandwidth_module=Bandwidth(self, 'bandwidth')
		self.add_submodule('bandwidth', bandwidth_module)

		channel_power_module=Channel_power(self, 'channel_power')
		self.add_submodule('channel_power', channel_power_module)

		emission_bandwidth_module=Emission_bandwidth(self, 'emission_bandwidth')
		self.add_submodule('emission_bandwidth', emission_bandwidth_module)

		sig_capture_module=Sig_Capture(self, 'sig_capture')
		self.add_submodule('sig_capture', sig_capture_module)

		cn_ratio_module=CN_Ratio(self, 'cn_ratio')
		self.add_submodule('cn_ratio', cn_ratio_module)

		demodulation_module=Demodulation(self, 'demodulation')
		self.add_submodule('demodulation', demodulation_module)

		sweep_module=Sweep(self, 'sweep')
		self.add_submodule('sweep', sweep_module)

		occupied_bandwidth_module=Occupied_Bandwidth(self, 'occupied_bandwidth')
		self.add_submodule('occupied_bandwidth', occupied_bandwidth_module)

		t_power_module=T_Power(self, 't_power')
		self.add_submodule('t_power', t_power_module)

		for i in range(1,4+1):
			correction_channel_module=CorrectionChannel(self, f'ch{i}', i)
			self.add_submodule(f'ch{i}', correction_channel_module)

		correction_module=Correction(self, 'correction')
		self.add_submodule('correction', correction_module)

		power_module=Power(self, 'power')
		self.add_submodule('power', power_module)

		toi_module=TOI(self, 'toi')
		self.add_submodule('toi', toi_module)
	
	def frequency_interpolation(self, mode):
		'''
		frequency interpolation parameter wrapper
		Args:
			mode
		'''
		vals.Enum('LIN', 'LOG').validate(mode)
		input=f'{mode}'
		self._frequency_interpolation(input)

	def first(self): self.write(':SENSe:VSWR:FREFlect')
	def second(self): self.write(':SENSe:VSWR: NREFlect')
	def restore(self): self.write(':SENSe:VSWR:RESet')

class AC(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('AC_average_count',
							label='averages of adjacent channel',
							set_cmd=':SENSe:ACPower:AVERage:COUNt {}',
							get_cmd=':SENSe:ACPower:AVERage:COUNt?',
							vals=vals.Ints(1,1000),
							get_parser=int)

		self.add_parameter('AC_average_state',
							label='averages measurement state',
							set_cmd=':SENSe:ACPower:AVERage:STATe {}',
							get_cmd=':SENSe:ACPower:AVERage:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('AC_average_power_control',
							label='avreage mode of adjacent channel',
							set_cmd=':SENSe:ACPower:AVERage:TCONtrol {}',
							get_cmd=':SENSe:ACPower:AVERage:TCONtrol?',
							vals=vals.Enum('EXP', 'REP'),
							get_parser=str.rstrip)

		self.add_parameter('AC_bandwidth_channel',
							label='adjacent channel bandwidth',
							set_cmd=':SENSe:ACPower:BANDwidth:ACHannel {}',
							get_cmd=':SENSe:ACPower:BANDwidth:ACHannel?',
							vals=vals.Numbers(33,2.5e9),
							unit='Hz',
							get_parser=float)

		self.add_parameter('AC_bandwidth_integration',
							label='main channel bandwidth',
							set_cmd=':SENSe:ACPower:BANDwidth:INTegration {}',
							get_cmd=':SENSe:ACPower:BANDwidth:INTegration?',
							vals=vals.Numbers(33,2.5e9),
							unit='Hz',
							get_parser=float)

		self.add_parameter('AC_channel_spacing',
							label='channel spacing',
							set_cmd=':SENSe:ACPower:CSPacing {}',
							get_cmd='[:SENSe]:ACPower:CSPacing?',
							vals=vals.Numbers(33,2.5e9),
							unit='Hz',
							get_parser=float)

class Bandwidth(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('EMI_state',
							label='bandwidth EMI filter state',
							set_cmd=':SENSe:BANDwidth:EMIFilter:STATe {}',
							get_cmd=':SENSe:BANDwidth:EMIFilter:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('bandwidth_resolution',
							label='resolution bandwidth',
							set_cmd=':SENSe:BANDwidth:RESolution {}',
							get_cmd=':SENSe:BANDwidth:RESolution?',
							vals=vals.Numbers(10,1e6),
							unit='Hz',
							get_parser=float)

		self.add_parameter('resolution_auto',
							label='auto setting state',
							set_cmd=':SENSe:BANDwidth:RESolution:AUTO {}',
							get_cmd=':SENSe:BANDwidth:RESolution:AUTO?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('bandwidth_video',
							label='video bandwidth',
							set_cmd=':SENSe:BANDwidth:VIDeo {}',
							get_cmd=':SENSe:BANDwidth:VIDeo?',
							vals=vals.Numbers(1,3e6),
							unit='Hz',
							get_parser=float)

		self.add_parameter('video_auto',
							label='video auto setting',
							set_cmd=':SENSe:BANDwidth:VIDeo:AUTO',
							get_cmd=':SENSe:BANDwidth:VIDeo:AUTO?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('video_ratio',
							label='V/R ratio',
							set_cmd=':SENSe:BANDwidth:VIDeo:RATio {}',
							get_cmd=':SENSe:BANDwidth:VIDeo:RATio?',
							vals=vals.Numbers(1e-6,3e4),
							get_parser=float)

class Channel_power(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('average_count',
							label='averages of channel power measurement',
							set_cmd=':SENSe:CHPower:AVERage:COUNt {}',
							get_cmd=':SENSe:CHPower:AVERage:COUNt?',
							vals=vals.Ints(1,1000),
							get_parser=int)

		self.add_parameter('average_state',
							label='average of channel power state',
							set_cmd=':SENSe:CHPower:AVERage:STATe {}',
							get_cmd=':SENSe:CHPower:AVERage:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('average_mode',
							label='average mode of channel power',
							set_cmd=':SENSe:CHPower:AVERage:TCONtrol {}',
							get_cmd=':SENSe:CHPower:AVERage:TCONtrol?',
							vals=vals.Enum('EXP', 'REP'),
							get_parser=str.rstrip)		

		self.add_parameter('bandwidth_integration',
							label='integration bandwidth',
							set_cmd=':SENSe:CHPower:BANDwidth:INTegration {}',
							get_cmd=':SENSe:CHPower:BANDwidth:INTegration?',
							vals=vals.Numbers(100,self.freq_max),
							unit='Hz',
							get_parser=float)

		self.add_parameter('frequency_span',
							label='channel frequency span',
							set_cmd=':SENSe:CHPower:FREQuency:SPAN {}',
							get_cmd=':SENSe:CHPower:FREQuency:SPAN?',
							vals=vals.Numbers(100,self.freq_max),
							unit='Hz',
							get_parser=float)

class CN_Ratio(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent,name)
		self.freq_max=parent.freq_max

		self.add_parameter('average_state',
							label='averages measurement state',
							set_cmd=':SENSe:CNRatio:AVERage:STATe {}',
							get_cmd=':SENSe:CNRatio:AVERage:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('average_control',
							label='average mode control',
							set_cmd=':SENSe:CNRatio:AVERage:TCONtrol {}',
							get_cmd=':SENSe:CNRatio:AVERage:TCONtrol?',
							vals=vals.Enum('EXP', 'REP'),
							get_parser=str.rstrip)

		self.add_parameter('count_average',
							label='number of averages of C/N ratio',
							set_cmd=':SENSe:CNRatio:AVERage:COUNt {}',
							get_cmd=':SENSe:CNRatio:AVERage:COUNt?',
							vals=vals.Ints(1,1000),
							get_parser=int)

		self.add_parameter('CN_average',
							label='average mode of C/N ratio',
							set_cmd=':SENSe:CNRatio:AVERage:TCONtrol {}',
							get_cmd=':SENSe:CNRatio:AVERage:TCONtrol?',
							vals=vals.Enum('EXP', 'REP'),
							get_parser=str.rstrip)
		
		self.add_parameter('carrier_bandwidth',
							label='carrier bandwidth',
							set_cmd=':SENSe:CNRatio:BANDwidth:INTegration {}',
							get_cmd=':SENSe:CNRatio:BANDwidth:INTegration?',
							vals=vals.Numbers(33,2.5e9),
							unit='Hz',
							get_parser=float)

		self.add_parameter('noise_bandwidth',
							label='noise bandwidth',
							set_cmd=':SENSe:CNRatio:BANDwidth:NOISe {}',
							get_cmd=':SENSe:CNRatio:BANDwidth:NOISe?',
							vals=vals.Numbers(33,2.5e9),
							unit='Hz',
							get_parser=float)

		self.add_parameter('offset_frequency',
							label='offset frequency',
							set_cmd=':SENSe:CNRatio:OFFSet {}',
							get_cmd=':SENSe:CNRatio:OFFSet?',
							vals=vals.Numbers(33,2.5e9),
							unit='Hz',
							get_parser=float)

class Correction(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('amplitude_correction_state',
							label='amplitude correction function state',
							set_cmd=':SENSe:CORRection:CSET:ALL:STATe {}',
							get_cmd=':SENSe:CORRection:CSET:ALL:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)
						
		self.add_parameter('correction_table',
							label='correction table state',
							set_cmd=':SENSe:CORRection:CSET:TABLe:STATe {}',
							get_cmd=':SENSe:CORRection:CSET:TABLe:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

	def delete_cset(self): self.write(':SENSe:CORRection:CSET:ALL:DELete')

class CorrectionChannel(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, channum):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max
		
		self.add_parameter('_correction_amplitude',
							label=f'channel {channum} amplitude correction curve',
							set_cmd=f':SENSe:CORRection:CSET{channum}:DATA {{}}',
							get_cmd=f':SENSe:CORRection:CSET{channum}:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('_correction_data',
							label=f'channel {channum} add correction data to curve',
							set_cmd=f':SENSe:CORRection:CSET{channum}:DATA:MERGe {{}}')

		self.add_parameter('_CSET_state',
							label=f'channel {channum} specified amplitude correction function',
							set_cmd=f':SENSe:CORRection:CSET{channum}:STATe {{}}',
							get_cmd=f':SENSe:CORRection:CSET{channum}:STATe?',
							get_parser=float)

		self.add_parameter('_frequency_interpolation',
							label=f'channel {channum} frequency interpolation mode of amplitude correction',
							set_cmd=f':SENSe:CORRection:CSET{channum}:X:SPACing {{}}',
							get_cmd=f':SENSe:CORRection:CSET{channum}:X:SPACing?',
							get_parser=str.rstrip)

	def cset_delete(self): self.write(f':SENSe:CORRection:CSET{channum}:DELete')

	def correction_amplitude(self, frequency, rel_ampl):
		'''
		correction amplitude parameter wrapper
		Args:
			frequency: Hz
			rel_ampl: dB
		'''
		vals.Numbers(0,self.freq_max).validate(frequency)
		vals.Numbers(-120,100).validate(rel_ampl)
		input=f'{frequency}, {rel_ampl}'
		self._correction_amplitude(input)

	def correction_data(self, frequency, rel_ampl):
		'''
		correction data parameter wrapper
		Args:
			frequency: Hz
			rel_ampl: dB
		'''
		vals.Numbers(0,self.freq_max).validate(frequency)
		vals.Numbers(-120,100).validate(rel_ampl)
		input=f'{frequency}, {rel_ampl}'
		self._correction_data(input)

	def CSET_state(self, state):
		'''
		CSET state parameter wrapper
		Args:
			state
		'''
		vals.Enum('ON', 'OFF').valdiate(state)
		on_off_dict={"ON":1,"OFF":0}
		input=f'{on_off_dict[state]}'
		self._CSET_state(input)

class Demodulation(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent,name)
		self.freq_max=parent.freq_max

		self.add_parameter('demodulation',
							label='demodulation type or disable',
							set_cmd=':SENSe:DEMod {}',
							get_cmd=':SENSe:DEMod?',
							vals=vals.Enum('AM', 'FM', 'OFF'),
							get_parser=str.rstrip)

		self.add_parameter('auto_gain',
							label='signal gain auto setting',
							set_cmd=':SENSe:DEMod:GAIN:AUTO {}',
							get_cmd=':SENSe:DEMod:GAIN:AUTO?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('signal_gain',
							label='signal gain',
							set_cmd=':SENSe:DEMod:GAIN:INCRement {}',
							get_cmd=':SENSe:DEMod:GAIN:INCRement?',
							vals=vals.Ints(1,7),
							get_parser=int)

		self.add_parameter('demodulation_state',
							label='demodulation state',
							set_cmd=':SENSe:DEMod:STATe {}',
							get_cmd=':SENSe:DEMod:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('demodulation_time',
							label='demodulation time',
							set_cmd=':SENSe:DEMod:TIME {}',
							get_cmd=':SENSe:DEMod:TIME?',
							vals=vals.Numbers(5e-3,1000),
							unit='s',
							get_parser=float)

class Emission_bandwidth(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('bandwidth_count',
							label='number of averages of emission bandwidth',
							set_cmd=':SENSe:EBWidth:AVERage:COUNt {}',
							get_cmd=':SENSe:EBWidth:AVERage:COUNt?',
							vals=vals.Ints(1,1000),
							get_parser=int)

		self.add_parameter('bandwidth_state',
							label='average measurement state',
							set_cmd=':SENSe:EBWidth:AVERage:STATe {}',
							get_cmd=':SENSe:EBWidth:AVERage:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('bandwidth_mode',
							label='average mode of emission bandwidth',
							set_cmd=':SENSe:EBWidth:AVERage:TCONtrol {}',
							get_cmd=':SENSe:EBWidth:AVERage:TCONtrol?',
							vals=vals.Enum('EXP', 'REP'),
							get_parser=str.rstrip)

		self.add_parameter('bandwidth_span',
							label='span of emission bandwidth',
							set_cmd=':SENSe:EBWidth:FREQuency:SPAN {}',
							get_cmd=':SENSe:EBWidth:FREQuency:SPAN?',
							vals=vals.Numbers(100,self.freq_max),
							get_parser=float)

		self.add_parameter('max_hold',
							label='max hold state',
							set_cmd=':SENSe:EBWidth:MAXHold:STATe {}',
							get_cmd=':SENSe:EBWidth:MAXHold:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('EBW_X',
							label='X value of EBW measurement',
							set_cmd=':SENSe:EBWidth:XDB {}',
							get_cmd=':SENSe:EBWidth:XDB?',
							vals=vals.Numbers(-100,-0.1),
							unit='dB',
							get_parser=float)

class Frequency(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('frequency_center',
							label='center frequency',
							set_cmd=':SENSe:FREQuency:CENTer {}',
							get_cmd=':SENSe:FREQuency:CENTer?',
							vals=vals.Numbers(0,self.freq_max),
							unit='Hz',
							get_parser=float)

		self.add_parameter('center_auto',
							label='center frequency step auto status',
							set_cmd=':SENSe:FREQuency:CENTer:STEP:AUTO {}',
							get_cmd=':SENSe:FREQuency:CENTer:STEP:AUTO?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('step_increment',
							label='center frequency step',
							set_cmd=':SENSe:FREQuency:CENTer:STEP:INCRement {}',
							get_cmd=':SENSe:FREQuency:CENTer:STEP:INCRement?',
							vals=vals.Numbers(1,self.freq_max),
							unit='Hz',
							get_parser=float)

		self.add_parameter('frequency_offset',
							label='frequency offset',
							set_cmd=':SENSe:FREQuency:OFFSet {}',
							get_cmd=':SENSe:FREQuency:OFFSet?',
							vals=vals.Numbers(-100e9,100e9),
							get_parser=float)

		self.add_parameter('frequency_start',
							label='start frequency',
							set_cmd=':SENSe:FREQuency:STARt {}',
							get_cmd=':SENSe:FREQuency:STARt?',
							vals=vals.Numbers(0,self.freq_max),
							unit='Hz',
							get_parser=float)

		self.add_parameter('frequency_stop',
							label='stop frequency',
							set_cmd=':SENSe:FREQuency:STOP {}',
							get_cmd=':SENSe:FREQuency:STOP?',
							vals=vals.Numbers(0,self.freq_max),
							unit='Hz',
							get_parser=float)

		self.add_parameter('frequency_span',
							label='span frequency',
							set_cmd=':SENSe:FREQuency:SPAN {}',
							get_cmd=':SENSe:FREQuency:SPAN?',
							vals=vals.Numbers(0,self.freq_max),
							unit='Hz',
							get_parser=float)

	def center_down(self): self.write(':SENSe:FREQuency:CENTer:DOWN')
	def center_step(self): self.write(':SENSe:FREQuency:CENTer:SET:STEP')
	def center_up(self): self.write(':SENSe:FREQuency:CENTer:UP')
	def span_full(self): self.write(':SENSe:FREQuency:SPAN:FULL')
	def span_prev(self): self.write(':SENSe:FREQuency:SPAN:PREVious')
	def span_half(self): self.write(':SENSe:FREQuency:SPAN:ZIN')
	def span_double(self): self.write(':SENSe:FREQuency:SPAN:ZOUT')

class Harmonic_Distortion(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('distortion_count',
							label='number of averages of harmonic distortion',
							set_cmd=':SENSe:HDISt:AVERage:COUNt {}',
							get_cmd=':SENSe:HDISt:AVERage:COUNt?',
							vals=vals.Ints(1,1000),
							get_parser=int)

		self.add_parameter('distortion_average',
							label='harmonic distortion average function',
							set_cmd=':SENSe:HDISt:AVERage:STATe {}',
							get_cmd=':SENSe:HDISt:AVERage:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('distortion_average_mode',
							label='avreage mode of harmonic distortion',
							set_cmd=':SENSe:HDISt:AVERage:TCONtrol {}',
							get_cmd=':SENSe:HDISt:AVERage:TCONtrol?',
							vals=vals.Enum('EXP', 'REP'),
							get_parser=str.rstrip)

		self.add_parameter('harmonics_numbers',
							label='number of harmonics measured',
							set_cmd=':SENSe:HDISt:NUMBers {}',
							get_cmd=':SENSe:HDISt:NUMBers?',
							vals=vals.Ints(2,10),
							get_parser=int)

		self.add_parameter('harmonic_time',
							label='sweep time of harmonic distortion',
							set_cmd=':SENSe:HDISt:TIME {}',
							get_cmd=':SENSe:HDISt:TIME?',
							vals=vals.Numbers(20e-6,7.5e3),
							unit='s',
							get_parser=float)

		self.add_parameter('harmonic_time_auto',
							label='sweep time status',
							set_cmd=':SENSe:HDISt:TIME:AUTO:STATe {}',
							get_cmd=':SENSe:HDISt:TIME:AUTO:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

class Occupied_Bandwidth(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent,name)
		self.freq_max=parent.freq_max

		self.add_parameter('occupied_count',
							label='occupied bandwidth number of averages',
							set_cmd=':SENSe:OBWidth:AVERage:COUNt {}',
							get_cmd=':SENSe:OBWidth:AVERage:COUNt?',
							vals=vals.Ints(1,1000),
							get_parser=int)

		self.add_parameter('occupied_average',
							label='average function of occupied bandwidth state',
							set_cmd=':SENSe:OBWidth:AVERage:STATe {}',
							get_cmd=':SENSe:OBWidth:AVERage:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('occupied_mode',
							label='average mode of occupied bandwidth',
							set_cmd=':SENSe:OBWidth:AVERage:TCONtrol {}',
							get_cmd=':SENSe:OBWidth:AVERage:TCONtrol?',
							vals=vals.Enum('EXP', 'REP'),
							get_parser=str.rstrip)

		self.add_parameter('occupied_span',
							label='span of occupied bandwidth',
							set_cmd=':SENSe:OBWidth:FREQuency:SPAN {}',
							get_cmd=':SENSe]OBWidth:FREQuency:SPAN?',
							vals=vals.Numbers(100,self.freq_max),
							unit='Hz',
							get_parser=float)

		self.add_parameter('occupied_max_hold',
							label='max hold of occupied bandwidth',
							set_cmd=':SENSe:OBWidth:MAXHold:STATe {}',
							get_cmd=':SENSe:OBWidth:MAXHold:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('occupied_percent',
							label='signal power percentage of whole span power',
							set_cmd=':SENSe:OBWidth:PERCent {}',
							get_cmd=':SENSe:OBWidth:PERCent?',
							vals=vals.Numbers(1,99.99),
							unit='%',
							get_parser=float)

class Power(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('attenuation',
							label='RF attenuator attenuation',
							set_cmd=':SENSe:POWer:RF:ATTenuation {}',
							get_cmd=':SENSe:POWer:RF:ATTenuation?',
							vals=vals.Ints(0,30),
							unit='dB',
							get_parser=int)

		self.add_parameter('attenuation_auto',
							label='attenuation auto setting',
							set_cmd=':SENSe:POWer:RF:ATTenuation:AUTO {}',
							get_cmd=':SENSe:POWer:RF:ATTenuation:AUTO?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('preamplifier',
							label='preamplifier state',
							set_cmd=':SENSe:POWer:RF:GAIN:STATe {}',
							get_cmd=':SENSe:POWer:RF:GAIN:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('power_mixer',
							label='maximum power of input mixer',
							set_cmd=':SENSe:POWer:RF:MIXer:RANGe:UPPer {}',
							get_cmd=':SENSe:POWer:RF:MIXer:RANGe:UPPer?',
							vals=vals.Ints(-30,0),
							unit='dBm',
							get_parser=int)

	def auto_scale(self): self.write(':SENSe:POWer:ASCale')
	def power_autorange(self): self.write(':SENSe:POWer:ARANge')
	def power_autoscale(self): self.write(':SENSe:POWer:ASCale')
	def power_autotune(self): self.write(':SENSe:POWer:ATUNe')

class Sig_Capture(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent,name)
		self.freq_max=parent.freq_max

		self.add_parameter('sig_capture',
							label='sig capture function state',
							set_cmd=':SENSe:SIGCapture:STATe {}',
							get_cmd=':SENSe:SIGCapture:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('real_time',
							label='real time trace status',
							set_cmd=':SENSe:SIGCapture:SIGC:STATe {}',
							get_cmd=':SENSe:SIGCapture:SIGC:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('sig_max_hold',
							label='max hold status',
							set_cmd=':SENSe:SIGCapture:MAXHold:STATe {}',
							get_cmd=':SENSe:SIGCapture:MAXHold:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('FSK2',
							label='2FSK status',
							set_cmd=':SENSe:SIGCapture:2FSK:STATe {}',
							get_cmd=':SENSe:SIGCapture:2FSK:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('FSK2_max_hold',
							label='2FSK max hold status',
							set_cmd=':SENSe:SIGCapture:2FSK:MAXHold:STATe',
							get_cmd=':SENSe:SIGCapture:2FSK:MAXHold:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('FSK2_fail',
							label='2FSK pass/fail function',
							set_cmd=':SENSe:SIGCapture:2FSK:PFSWitch',
							get_cmd=':SENSe:SIGCapture:2FSK:PFSWitch?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('FSK2_signal',
							label='desired 2FSK signal',
							set_cmd=':SENSe:SIGCapture:2FSK:SIGNal {}',
							get_cmd=':SENSe:SIGCapture:2FSK:SIGNal?',
							vals=vals.Enum(0,1,2),
							get_parser=float)

		self.add_parameter('_FSK2_ampup',
							label='amplitude upper limit of 2FSK',
							set_cmd=':SENSe:SIGCapture:2FSK:AMPUp {}',
							get_cmd=':SENSe:SIGCapture:2FSK:AMPUp?',
							vals=vals.Numbers(-400,320),
							unit='dB',
							get_parser=float)

		self.add_parameter('_FSK2_ampdown',
							label='amplitude lower limit of 2FSK',
							set_cmd=':SENSe:SIGCapture:2FSK:AMPDown {}',
							get_cmd=':SENSe:SIGCapture:2FSK:AMPDown?',
							vals=vals.Numbers(-400,320),
							unit='dB',
							get_parser=float)

		self.add_parameter('_FSK2_mark1_frequency',
							label='2FSK marker 1 frequency',
							set_cmd=':SENSe:SIGCapture:2FSK:MARK1:FREQ {}',
							get_cmd=':SENSe:SIGCapture:2FSK:MARK1:FREQ?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('FSK2_mark1',
							label='2FSK marker 1 state',
							set_cmd=':SENSe:SIGCapture:2FSK:MARK1:Switch:STATe {}',
							get_cmd=':SENSe:SIGCapture:2FSK:MARK1:Switch:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('_FSK2_mark2_frequency',
							label='2FSK marker 2 frequency',
							set_cmd=':SENSe:SIGCapture:2FSK:MARK2:FREQ {}',
							get_cmd=':SENSe:SIGCapture:2FSK:MARK2:FREQ?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('FSK2_mark2',
							label='2FSK marker 2 state',
							set_cmd=':SENSe:SIGCapture:2FSK:MARK2:Switch:STATe {}',
							get_cmd=':SENSe:SIGCapture:2FSK:MARK2:Switch:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

	def FSK2_ampup(self, FSK2_ampup: float=None):
		if FSK2_ampup==None:
			return self._FSK2_ampup()
		limit=self._FSK2_ampdown
		if FSK2_ampup<limit or FSK2_ampup>320:
			raise ValueError('Amplitude upper limit is outside the limit.\n'
							'Must be between lower amplitude limit and 320 dBm.\n'
							f'Currently must be more than {limit}s.\n')
		else:
			self._FSK2_ampup(FSK2_ampup)

	def FSK2_ampdown(self, FSK2_ampdown: float=None):
		if FSK2_ampdown==None:
			return self._FSK2_ampdown()
		limit=self._FSK2_ampup
		if FSK2_ampdown<-400 or FSK2_ampdown>limit:
			raise ValueError('Amplitude lower limit is outside the limit.\n'
							'Must be between -400 dBm and upper limit.\n'
							f'Currently must be less than {limit}s.\n')
		else:
			self._FSK2_ampdown(FSK2_ampdown)

	def FSK2_mark1_frequency(self, FSK2_mark1_frequency: float=None):
		if FSK2_mark1_frequency==None:
			return self._FSK2_mark1_frequency()
		freq_center=parent.frequency_center()
		freq_span=parent.frequency_span()
		lower_limit=freq_center-freq_span/2
		upper_limit=freq_center+freq_span/2
		if FSK2_mark1_frequency<lower_limit or FSK2_mark1_frequency>upper_limit:
			raise ValueError('Marker 1 is outside the limit.\n',
							'Must be between lower limit and upper limit.\n',
							f'Currently must be between {lower_limit} and {upper_limit}.\n')
		else:
			self._FSK2_mark1_frequency(FSK2_mark1_frequency)

	def FSK2_mark2_frequency(self, FSK2_mark2_frequency: float=None):
		if FSK2_mark2_frequency==None:
			return self._FSK2_mark2_frequency()
		freq_center=parent.frequency_center()
		freq_span=parent.frequency_span()
		lower_limit=freq_center-freq_span/2
		upper_limit=freq_center+freq_span/2
		if FSK2_mark2_frequency<lower_limit or FSK2_mark2_frequency>upper_limit:
			raise ValueError('Marker 2 is outside the limit.\n',
							'Must be between lower limit and upper limit.\n',
							f'Currently must be between {lower_limit} and {upper_limit}.\n')
		else:
			self._FSK2_mark2_frequency(FSK2_mark2_frequency)


	def sig_reset(self): self.write(':SENSe:SIGCapture:RESet')
	def FSK2_reset(self): self.write(':SENSe:SIGCapture:2FSK:RESet')

class Sweep(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent,name)
		self.freq_max=parent.freq_max

		self.add_parameter('sweep_count',
							label='number of sweeps in a single sweep',
							set_cmd=':SENSe:SWEep:COUNt {}',
							get_cmd=':SENSe:SWEep:COUNt?',
							vals=vals.Ints(1,9999),
							get_parser=int)

		self.add_parameter('current_count',
							label='number of weeps finished query',
							get_cmd=':SENSe:SWEep:COUNt:CURRent?',
							get_parser=int)

		self.add_parameter('sweep_point',
							label='sweep points',
							set_cmd=':SENSe:SWEep:POINts {}',
							get_cmd=':SENSe:SWEep:POINts?',
							vals=vals.Ints(101,3001),
							get_parser=int)

		self.add_parameter('sweep_time',
							label='sweep time',
							set_cmd=':SENSe:SWEep:TIME {}',
							get_cmd=':SENSe:SWEep:TIME?',
							vals=vals.Numbers(20e-6,7500),
							unit='s',
							get_parser=float)

		self.add_parameter('sweep_auto',
							label='auto sweep time status',
							set_cmd=':SENSe:SWEep:TIME:AUTO {}',
							get_cmd=':SENSe:SWEep:TIME:AUTO?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('auto_method',
							label='method of auto sweep time',
							set_cmd=':SENSe:SWEep:TIME:AUTO:RULes {}',
							get_cmd=':SENSe:SWEep:TIME:AUTO:RULes?',
							vals=vals.Enum('NORM', 'ACC'),
							get_parser=str.rstrip)

class TOI(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('TOI_count',
							label='number of averages of TOI measurement',
							set_cmd=':SENSe:TOI:AVERage:COUNt {}',
							get_cmd=':SENSe:TOI:AVERage:COUNt?',
							vals=vals.Ints(1,1000),
							get_parser=int)

		self.add_parameter('TOI_state',
							label='TOI average measurement state',
							set_cmd=':SENSe:TOI:AVERage:STATe {}',
							get_cmd=':SENSe:TOI:AVERage:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('TOI_mode',
							label='average mode of TOI measurement',
							set_cmd=':SENSe:TOI:AVERage:TCONtrol {}',
							get_cmd=':SENSe:TOI:AVERage:TCONtrol?',
							vals=vals.Enum('EXP', 'REP'),
							get_parser=str.rstrip)

		self.add_parameter('TOI_span',
							label='span of TOI measurement',
							set_cmd=':SENSe:TOI:FREQuency:SPAN {}',
							get_cmd=':SENSe:TOI:FREQuency:SPAN?',
							vals=vals.Numbers(100,),
							unit='Hz',
							get_parser=float)

class T_Power(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('T_power_count',
							label='number of averages of T-power',
							set_cmd=':SENSe:TPOWer:AVERage:COUNt {}',
							get_cmd=':SENSe:TPOWer:AVERage:COUNt?',
							vals=vals.Ints(1,1000),
							get_parser=int)

		self.add_parameter('T_power',
							label='T-power state',
							set_cmd=':SENSe:TPOWer:AVERage:STATe {}',
							get_cmd=':SENSe:TPOWer:AVERage:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('T_power_mode',
							label='average mode of T-power measurement',
							set_cmd=':SENSe:TPOWer:AVERage:TCONtrol {}',
							get_cmd=':SENSe:TPOWer:AVERage:TCONtrol?',
							vals=vals.Enum('EXP', 'REP'),
							get_parser=str.rstrip)

		self.add_parameter('T_power_start',
							label='start line of T-power measurement',
							set_cmd=':SENSe:TPOWer:LLIMit {}',
							get_cmd=':SENSe:TPOWer:LLIMit?',
							vals=vals.Numbers(0e-6,7500),
							unit='s',
							get_parser=float)

		self.add_parameter('T_power_type',
							label='power type ofT-power measurement',
							set_cmd=':SENSe:TPOWer:MODE {}',
							get_cmd=':SENSe:TPOWer:MODE?',
							vals=vals.Enum('AVER', 'PEAK', 'RMS'),
							get_parser=str.rstrip)

		self.add_parameter('T_power_stop',
							label='stop line of T-power measurement',
							set_cmd=':SENSe:TPOWer:RLIMit {}',
							get_cmd=':SENSe:TPOWer:RLIMit?',
							vals=vals.Numbers(0e-6,7500),
							unit='s',
							get_parser=float)

class Source(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('correction_offset',
							label='output amplitude offset',
							set_cmd=':SOURce:CORRection:OFFSet {}',
							get_cmd=':SOURce:CORRection:OFFSet?',
							vals=vals.Ints(-200,200),
							unit='dB',
							get_parser=int)

		self.add_parameter('fixed_power_amplitude',
							label='output amplitude in fixed power output mode',
							set_cmd=':SOURce:POWer:LEVel:IMMediate:AMPLitude {}',
							get_cmd=':SOURce:POWer:LEVel:IMMediate:AMPLitude?',
							vals=vals.Ints(-40,0),
							unit='dBm',
							get_parser=int)

		self.add_parameter('power_mode',
							label='power output mode',
							set_cmd=':SOURce:POWer:MODE {}',
							get_cmd=':SOURce:POWer:MODE?',
							vals=vals.Enum('FIX', 'SWE'),
							get_parser=str.rstrip)

		self.add_parameter('power_span',
							label='fixed power output amplitude range',
							set_cmd=':SOURce:POWer:SPAN {}',
							get_cmd=':SOURce:POWer:SPAN?',
							vals=vals.Ints(0,20),
							unit='dB',
							get_parser=int)

		self.add_parameter('power_start',
							label='start output amplitude in power sweep mode',
							set_cmd=':SOURce:POWer:STARt {}',
							get_cmd=':SOURce:POWer:STARt?',
							vals=vals.Ints(-40,0),
							unit='dBm',
							get_parser=int)

		self.add_parameter('power_sweep',
							label='output amplitude range in power sweep mode',
							set_cmd=':SOURce:POWer:SWEep {}',
							get_cmd=':SOURce:POWer:SWEep?',
							vals=vals.Ints(0,20),
							unit='dB',
							get_parser=int)

		self.add_parameter('reference_trace_state',
							label='reference trace state',
							set_cmd=':SOURce:TRACe:REF:STATe{}',
							get_cmd=':SOURce:TRACe:REF:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

	def save(self): self.write(':SOURce:TRACe:STORref')

class Status(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('operation_condition',
							label='condition register query',
							get_cmd=':STATus:OPERation:CONDition?',
							get_parser=int)

		self.add_parameter('operation_enable',
							label='enable register',
							set_cmd=':STATus:OPERation:ENABle {}',
							get_cmd=':STATus:OPERation:ENABle?',
							vals=vals.Ints(0,32767),
							get_parser=int)

		self.add_parameter('operation_event',
							label='event register query',
							get_cmd=':STATus:OPERation:EVENt?',
							get_parser=int)

		self.add_parameter('questionable_condition',
							label='condition register query',
							get_cmd=':STATus:QUEStionable:CONDition?',
							get_parser=int)

		self.add_parameter('questionable_enable',
							label='questionable status register',
							set_cmd=':STATus:QUEStionable:ENABle {}',
							get_cmd=':STATus:QUEStionable:ENABle?',
							vals=vals.Ints(0,32767),
							get_parser=int)

		self.add_parameter('questionable_event',
							label='questionable register query',
							get_cmd=':STATus:QUEStionable:EVENt?',
							get_parser=int)

	def preset(self): self.write(':STATus:PRESet')

class System(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('beeper',
							label='beeper state',
							set_cmd=':SYSTem:BEEPer:STATe {}',
							get_cmd=':SYSTem:BEEPer:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('port',
							label='port options',
							set_cmd=':SYSTem:COMMunicate:APORt {}',
							get_cmd=':SYSTem:COMMunicate:APORt?',
							vals=vals.Enum('GPIB', 'LAN', 'USB', 'OFF'),
							get_parser=str.rstrip)

		self.add_parameter('BRMT',
							label='instrument state',
							set_cmd=':SYSTem:COMMunicate:BRMT {}',
							get_cmd=':SYSTem:COMMunicate:BRMT?',
							val_mapping={'ON':1,'OFF':0},
							docstring='local=0,off remote=1,on',
							get_parser=str.rstrip)

		self.add_parameter('GPIB_address',
							label='GPIB address',
							set_cmd=':SYSTem:COMMunicate:GPIB:SELF:ADDRess {}',
							get_cmd=':SYSTem:COMMunicate:GPIB:SELF:ADDRess?',
							vals=vals.Ints(0,30),
							get_parser=int)

		self.add_parameter('IP_auto',
							label='auto IP setting mode',
							set_cmd=':SYSTem:COMMunicate:LAN:SELF:AUToip:STATe {}',
							get_cmd=':SYSTem:COMMunicate:LAN:SELF:AUToip:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('DHCP',
							label='DHCP status',
							set_cmd=':SYSTem:COMMunicate:LAN:SELF:DHCP:STATe {}',
							get_cmd=':SYSTem:COMMunicate:LAN:SELF:DHCP:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('IP_address',
							label='IP_address',
							set_cmd=':SYSTem:COMMunicate:LAN:SELF:IP:ADDress {}',
							get_cmd=':SYSTem:COMMunicate:LAN:SELF:IP:ADDress?',
							vals=vals.Strings(7,15),
							get_parser=str.rstrip)

		self.add_parameter('DNS_address',
							label='DNS address',
							set_cmd=':SYSTem:COMMunicate:LAN:SELF:IP:DNSServer {}',
							get_cmd=':SYSTem:COMMunicate:LAN:SELF:IP:DNSServer?',
							vals=vals.Strings(7,15),
							get_parser=str.rstrip)

		self.add_parameter('default_gateway',
							label='default gateway',
							set_cmd=':SYSTem:COMMunicate:LAN:SELF:IP:GATeway {}',
							get_cmd=':SYSTem:COMMunicate:LAN[:SELF]:IP:GATeway?',
							vals=vals.Strings(7,15),
							get_parser=str.rstrip)

		self.add_parameter('subnet',
							label='subnet mask',
							set_cmd=':SYSTem:COMMunicate:LAN:SELF:IP:SUBMask {}',
							get_cmd=':SYSTem:COMMunicate:LAN:SELF:IP:SUBMask?',
							vals=vals.Strings(7,15),
							get_parser=str.rstrip)

		self.add_parameter('IP_manual',
							label='manual IP setting',
							set_cmd=':SYSTem:COMMunicate:LAN:SELF:MANuip:STATe {}',
							get_cmd=':SYSTem:COMMunicate:LAN:SELF:MANuip:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('USB_address',
							label='USB device address query',
							get_cmd=':SYSTem:COMMunicate:USB:SELF:ADDRess?',
							get_parser=str.rstrip)

		self.add_parameter('USB_class',
							label='USB device class',
							set_cmd=':SYSTem:COMMunicate:USB:SELF:CLASs {}',
							get_cmd=':SYSTem:COMMunicate:USB:SELF:CLASs?',
							vals=vals.Enum('TMC', 'PRIN', 'AUTO'),
							get_parser=str.rstrip)

		self.add_parameter('system_information',
							label='spectrum analyzer system information query',
							get_cmd=':SYSTem:CONFigure:INFormation?',
							get_parser=str.rstrip)

		self.add_parameter('message',
							label='message displayed lately query',
							get_cmd=':SYSTem:CONFigure:MESSage?',
							get_parser=str.rstrip)

		self.add_parameter('_date',
							label='date of instrument',
							set_cmd=':SYSTem:DATE {}',
							get_cmd=':SYSTem:DATE?',
							get_parser=str.rstrip)

		self.add_parameter('next',
							label='query and delete last message',
							get_cmd=':SYSTem:ERRor:NEXT?',
							get_parser=str.rstrip)

		self.add_parameter('power_switch',
							label='front panel power switch',
							set_cmd=':SYSTem:FSWItch:STATe {}',
							get_cmd=':SYSTem:FSWItch:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('_key_lock',
							label='lock specified key',
							set_cmd=':SYSTem:KLOCk {}',
							get_cmd=':SYSTem:KLOCk?',
							get_parser=str.rstrip)

		self.add_parameter('language',
							label='language of instrument',
							set_cmd=':SYSTem:LANGuage',
							get_cmd=':SYSTem:LANGuage?',
							vals=vals.Enum('ENGL', 'CHIN', 'JAP', 'PORT', 'GERM', 'POL', 'KOR', 'TCH'),
							get_parser=str.rstrip)

		self.add_parameter('linemode',
							label='query line mode status',
							get_cmd=':SYSTem:LINemod:STATe?',
							get_parser=str.rstrip)

		self.add_parameter('linemode_type',
							label='preset setting of line mode',
							set_cmd=':SYSTem:LINemod:TYPe FACTory {}',
							vals=vals.Enum('FACT', 'USER1', 'USER2', 'USER3', 'USER4', 'USER5', 'USER6', 'OFF'))

		self.add_parameter('license_activate',
							label='license_key',
							set_cmd=':SYSTem:LKEY {}',
							vals=vals.Strings())

		self.add_parameter('license_query',
							label='license_query',
							get_cmd=':SYSTem:LKEY? {}',
							vals=vals.Ints(1,4),
							get_parser=str.rstrip)

		self.add_parameter('options',
							label='query options status',
							get_cmd=':SYSTem:OPTions?',
							get_parser=str.rstrip)

		self.add_parameter('power_on',
							label='power on recall last setting',
							set_cmd=':SYSTem:PON:TYPE {}',
							get_cmd=':SYSTem:PON:TYPE?',
							vals=vals.Enum('PRES', 'LAST'),
							get_parser=str.rstrip)

		self.add_parameter('_preset_save',
							label='save user setting',
							set_cmd=':SYSTem:PRESet:SAVE {}')

		self.add_parameter('preset_type',
							label='system preset type',
							set_cmd=':SYSTem:PRESet:TYPe {}',
							get_cmd=':SYSTem:PRESet:TYPe?',
							vals=vals.Enum('FACT', 'USER1', 'USER2', 'USER3', 'USER4', 'USER5', 'USER6'),
							get_parser=str.rstrip)

		self.add_parameter('speaker_state',
							label='earphone in demodulation status',
							set_cmd=':SYSTem:SPEaker:STATe {}',
							get_cmd=':SYSTem:SPEaker:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('volume',
							label='earphone in demodulation volume',
							set_cmd=':SYSTem:SPEaker:VOLume {}',
							get_cmd=':SYSTem:SPEaker:VOLume?',
							vals=vals.Ints(0,225),
							get_parser=int)

		self.add_parameter('_time',
							label='instrument time',
							set_cmd=':SYSTem:TIME {}',
							get_cmd=':SYSTem:TIME?',
							get_parser=str.rstrip)

		self.add_parameter('TX',
							label='TX1000 connection status query',
							get_cmd=':SYSTem:TX:STATe?',
							get_parser=str.rstrip)

		self.add_parameter('_TX_state',
							label='TX1000 status',
							set_cmd=':SYSTem:TX:SWset {}')

		self.add_parameter('TX_query',
							label='TX1000 state query',
							get_cmd=':SYSTem:TX:SWSTa? {}',
							vals=vals.Enum('SW1', 'SW2', 'SW3', 'SW4', 'SW5'),
							get_parser=str.rstrip)

		self.add_parameter('userkey',
							label='related function for userkey',
							set_cmd=':SYSTem:USERkey:KEYCmd {}',
							get_cmd=':SYSTem:USERkey:KEYCmd?',
							vals=vals.Enum('FREQ', 'SPAN', 'AMP', 'BW', 'SWEep', 'TUNE', 'DEM', 'TRAC', 'TG', 'MEAS', 'MEASset', 'MARK', 'MARKfunc', 'MARKto', 'PEAK', 'PRESet', 'SYSTem', 'STORage', 'PRINt', 'PRINtsetup', 'HELP', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'RETUrn', 'PAGEdown'),
							get_parser=str.rstrip)

		self.add_parameter('userkey_state',
							label='userkey status',
							set_cmd=':SYSTem:USERkey:STATe {}',
							get_cmd=':SYSTem:USERkey:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('version',
							label='SCPI version query',
							get_cmd=':SYSTem:VERSion?',
							get_parser=str.rstrip)

		

	def date(self, year, month, day):
		'''
		date parameter wrapper
		Args:
			year
			month
			day
		'''
		vals.Ints(2000,2099).validate(year)
		vals.Ints(1,12).valdiate(month)
		vals.Ints(1,31).validate(day)
		input=f'{year},{month},{day}'
		self._date(input)

	def key_lock(self, state, key):
		'''
		key lock parameter wrapper
		Args:
			state
			key
		'''
		vals.Enum('ON', 'OFF').valdiate(state)
		on_off_dict={"ON":1,"OFF":0}
		vals.Enum('FREQ', 'SPAN', 'AMP', 'BW', 'SWEEP', 'TRACE', 'TG', 'MARK', 'MARKFUNC', 'MARKTO', 'PEAK', 'TUNE', 'MEAS', 'MEASSET', 'DEMOD', 'SYSTEM', 'PRINTSETUP', 'STORAGE', 'PRESET', 'PRINT').validate(key)
		input=f'{on_off_dict[state]},{key}'
		self._key_lock(input)

	def preset_save(self, user, path):
		'''
		preset save parameter wrapper
		Args:
			user
			path
		'''
		vals.Enum('USER1', 'USER2', 'USER3', 'USER4', 'USER5', 'USER6').validate(user)
		vals.Strings().validate(path)
		input=f'{user}, {path}'
		self._preset_save(input)

	def time(self, hour, minute, second):
		'''
		time parameter wrapper
		Args:
			hour
			minute
			second
		'''
		vals.Ints(00,23).validate(hour)
		vals.Ints(00,59).validate(minute)
		vals.Ints(00,59).validate(second)
		input=f'{hour},{minute},{second}'
		self._time(input)

	def TX_state(self, switch, state):
		'''
		TX state parameter wrapper
		Args:
			switch
			state
		'''
		vals.Enum('SW1', 'SW2', 'SW3', 'SW4', 'SW5').validate(switch)
		vals.Enum('ON', 'OFF').valdiate(state)
		on_off_dict={"ON":1,"OFF":0}
		input=f'{switch},{on_off_dict[state]}'
		self._TX_state(input)

	def clear(self): self.write(':SYSTem:CLEar')
	def LAN_setting(self): self.write(':SYSTem:COMMunicate:LAN:SELF:RESet')
	def preset_recall(self): self.write(':SYSTem:PRESet')
	def userkey_confirm(self): self.writre(':SYSTem:USERkey:CONFirm')

class Trace(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, tracenum):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('_data',
							label=f'Trace {tracenum} data',
							set_cmd=f':TRACe:DATA TRACE{tracenum},{{}}',
							get_cmd=f':TRACe:DATA? TRACE{tracenum}',
							get_parser=_data_parser)

		self.add_parameter('average_count',
							label='number of averages of the trace',
							set_cmd=':TRACe:AVERage:COUNt {}',
							get_cmd=':TRACe:AVERage:COUNt?',
							vals=vals.Ints(1,1000),
							get_parser=int)

		self.add_parameter('count_current',
							label='query number of averages currently executed',
							get_cmd=':TRACe:AVERage:COUNt:CURRent?',
							get_parser=int)

		self.add_parameter('mathA',
							label='denotion of A',
							set_cmd=':TRACe:MATH:A {}',
							get_cmd=':TRACe:MATH:A?',
							vals=vals.Enum('T1', 'T2', 'T3'),
							get_parser=str.rstrip)

		self.add_parameter('mathB',
							label='denotion of B',
							set_cmd=':TRACe:MATH:B {}',
							get_cmd=':TRACe:MATH:B?',
							vals=vals.Enum('T1', 'T2', 'T3'),
							get_parser=str.rstrip)

		self.add_parameter('constant',
							label='constant',
							set_cmd=':TRACe:MATH:CONSt {}',
							get_cmd=':TRACe:MATH:CONSt?',
							vals=vals.Numbers(-300,300),
							get_parser=float)

		self.add_parameter('peak_data',
							label='query frequencies and amplitudes of peaks',
							get_cmd=':TRACe:MATH:PEAK:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('peak_points',
							label='query number of peaks',
							get_cmd=':TRACe:MATH:PEAK:POINts?',
							get_parser=int)

		self.add_parameter('peak_sort',
							label='sorting rule of peak table',
							set_cmd=':TRACe:MATH:PEAK:SORT {}',
							get_cmd=':TRACe:MATH:PEAK:SORT?',
							vals=vals.Enum('AMPL', 'FREQ'),
							get_parser=str.rstrip)

		self.add_parameter('peak_table',
							label='peak table status',
							set_cmd=':TRACe:MATH:PEAK:TABLe:STATe {}',
							get_cmd=':TRACe:MATH:PEAK:TABLe:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('peak_mode',
							label='display mode of peak',
							set_cmd=':TRACe:MATH:PEAK:THReshold {}',
							get_cmd=':TRACe:MATH:PEAK:THReshold?',
							vals=vals.Enum('NORM', 'DLM', 'DLL'),
							get_parser=str.rstrip)

		self.add_parameter('math_state',
							label='math status',
							set_cmd=':TRACe:MATH:STATe {}',
							get_cmd=':TRACe:MATH:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('math_type',
							label='operation type of trace',
							set_cmd=':TRACe:MATH:TYPE {}',
							get_cmd=':TRACe:MATH:TYPE?',
							vals=vals.Enum('A-B', 'A+CONST', 'A-CONST'),
							get_parser=str.rstrip)

		self.add_parameter('average_type',
							label=f'Trace {tracenum} average type of trace',
							set_cmd=f':TRACe{tracenum}:AVERage:TYPE {{}}',
							get_cmd=f':TRACe{tracenum}:AVERage:TYPE?',
							vals=vals.Enum('VID', 'RMS'),
							get_parser=str.rstrip)

		self.add_parameter('trace_type',
							label=f'Trace {tracenum} type of trace',
							set_cmd=f':TRACe{tracenum}:MODE {{}}',
							get_cmd=f':TRACe{tracenum}:MODE?',
							vals=vals.Enum('WRIT', 'MAXH', 'MINH', 'VIEW', 'BLANK', 'VID', 'POW'),
							get_parser=str.rstrip)
		

	def data(self, data:list=None):
		if data==None:
			return self._data()
		else:
			#TODO: fix for uploading data
			pass

	def average_clear(self): self.write(':TRACe:AVERage:CLEar')
	def average_reset(self): self.write(':TRACe:AVERage:RESet')
	def clear_all(self): self.write(':TRACe:CLEar:ALL')

class Trigger(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('ready',
							label='trigger ready query',
							get_cmd=':TRIGger:SEQuence:EXTernal:READy?',
							get_parser=str.rstrip)

		self.add_parameter('slope',
							label='external trigger edge',
							set_cmd=':TRIGger:SEQuence:EXTernal:SLOPe {}',
							get_cmd=':TRIGger:SEQuence:EXTernal:SLOPe?',
							vals=vals.Enum('POS', 'NEG'),
							get_parser=str.rstrip)

		self.add_parameter('source',
							label='trigger type',
							set_cmd=':TRIGger:SEQuence:SOURce {}',
							get_cmd=':TRIGger:SEQuence:SOURce?',
							vals=vals.Enum('IMM', 'VID', 'EXT'),
							get_parser=str.rstrip)

		self.add_parameter('video_level',
							label='video trigger level',
							set_cmd=':TRIGger:SEQuence:VIDeo:LEVel {}',
							get_cmd=':TRIGger:SEQuence:VIDeo:LEVel?',
							vals=vals.Numbers(-300,50),
							unit='dBm',
							get_parser=float)

class Unit(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('power',
							label='y axis unit',
							set_cmd=':UNIT:POWer {}',
							get_cmd=':UNIT:POWer?',
							vals=vals.Enum('DBM', 'DBMV', 'DBUV', 'V', 'W'),
							get_parser=str.rstrip)							

class Rigol_DSA800(VisaInstrument):
	'''
	Rigol DSA800 QCoDes driver
	Structure:
		Instrument-
			-Calculate
			-Calibrate
			-Configure
			-Couple
			-Display
			-Fetch
			-Format
			-Hcopy
			-Initiate
			-Input
			-Limitline
			-line_limit
			Marker-
					-MarkerNumber
			-MassMemory
			-Output
			Read
			Sense-
					-AC
					-Bandwidth
					-Channel_power
					-CN_Ratio
					-Correction
					-CorrectionChannel
					-Demodulation
					-Emission_bandwidth
					-Frequency
					-Harmonic_Distrortion
					-Occupied_Bandwidth
					-Power
					-Sig_Capture
					-Sweep
					-TOI
					-T_Power
			-Source
			-Status
			-System
			-Trace
			-Trigger
			-Unit
	'''
	
	def __init__(self, name, address, **kwargs):
		kwargs["device_clear"] = False
		super().__init__(name, address, **kwargs)

		model_freq=str(self.ask('*IDN?'))
		freq_num=float(model_freq[23:25])
		self.freq_max=freq_num*1e8

		calculate_module=Calculate(self, 'calculate')
		self.add_submodule('calculate', calculate_module)

		calibrate_module=Calibrate(self, 'calibrate')
		self.add_submodule('calibrate', calibrate_module)

		configure_module=Configure(self, 'configure')
		self.add_submodule('configure', configure_module)

		couple_module=Couple(self, 'couple')
		self.add_submodule('couple', couple_module)
		
		display_module=Display(self, 'display')
		self.add_submodule('display', display_module)

		fetch_module=Fetch(self, 'fetch')
		self.add_submodule('fetch', fetch_module)

		format_module=Format(self, 'format')
		self.add_submodule('format', format_module)

		hcopy_module=Hcopy(self, 'hcopy')
		self.add_submodule('hcopy', hcopy_module)

		initiate_module=Initiate(self, 'initiate')
		self.add_submodule('initiate', initiate_module)

		input_module=Input(self, 'input')
		self.add_submodule('input', input_module)

		massmemory_module=MassMemory(self, 'massmemory')
		self.add_submodule('massmemory', massmemory_module)

		output_module=Output(self, 'output')
		self.add_submodule('output', output_module)

		read_module=Read(self, 'read')
		self.add_submodule('read', read_module)

		source_module=Source(self, 'source')
		self.add_submodule('source', source_module)

		status_module=Status(self, 'status')
		self.add_submodule('status', status_module)

		system_module=System(self, 'system')
		self.add_submodule('system', system_module)

		trigger_module=Trigger(self, 'trigger')
		self.add_submodule('trigger', trigger_module)

		unit_module=Unit(self, 'unit')
		self.add_submodule('unit', unit_module)

		for i in range(1,3+1):
			trace_module=Trace(self, f'tr{i}', i)
			self.add_submodule(f'tr{i}', trace_module)

		sense_module=Sense(self, 'sense')
		self.add_submodule('sense', sense_module) 

		self.add_parameter('OPC',
							label='OPC',
							set_cmd='*OPC',
							get_cmd='*OPC?',
							get_parser=str.rstrip)

		self.add_parameter('SRE',
							label='status byte register',
							set_cmd='*SRE {}',
							get_cmd='*SRE?',
							vals=vals.Ints(0,255),
							get_parser=int)

		self.add_parameter('STB',
							label='status byte register query',
							get_cmd='*STB?',
							get_parser=int)

		self.add_parameter('TST',
							label='self check finished query',
							get_cmd='*TST?',
							get_parser=str.rstrip)

		self.connect_message()

		
	def abort(self): self.write(':ABORt')
	def RST(self): self.write('*RST')
	def TRG(self): self.write('*TRG')
	def wait(self): self.write('*WAI')
