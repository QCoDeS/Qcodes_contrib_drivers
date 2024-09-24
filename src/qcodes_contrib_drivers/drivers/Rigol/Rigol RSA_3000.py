'''
Driver for Rigol RSA3000 spectrum analyzer

Written by Ben Mowbray (http://wp.lancs.ac.uk/laird-group/)

Examples:

	***Setting up instrument and examples***

	$ from qcodes.instrument_drivers.rigol.Rigol_RSA3000 import RigolRSA3000
	$ rs_1 = RigolRSA3000('r_3000_1', 'USB0::0x1AB1::0x0968::RSA3J232100168::0::INSTR')
	$ rs_1.output.state(1) # turns on output of tracking generator
	$ rs_1.sense.sweep._sweep_time(50) # Sets sweep time

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

		self.add_parameter('bandwidth_NDB',
							label='N value in N dB BW measurement',
							set_cmd=':CALCulate:BANDwidth:NDB {}',
							get_cmd=':CALCulate:BANDwidth:NDB?',
							vals=vals.Numbers(-140,-0.01),
							unit='dB',
							get_parser=float)

		self.add_parameter('bandwidth_result',
							label='query measurement result of N dB band',
							get_cmd=':CALCulate:BANDwidth:RESult?',
							unit='Hz',
							get_parser=float)

		self.add_parameter('bandwidth_left',
							label='query frequency value at left side of current marker',
							get_cmd=':CALCulate:BANDwidth:RLEFt?',
							unit='Hz',
							get_parser=float)

		self.add_parameter('bandwidth_right',
							label='query frequency value at right side of current marker',
							get_cmd=':CALCulate:BANDwidth:RRIGht?',
							unit='Hz',
							get_parser=float)

		self.add_parameter('bandwidth_function',
							label='N dB bandwidth measurement function',
							set_cmd=':CALCulate:BANDwidth:STATe {}',
							get_cmd=':CALCulate:BANDwidth:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('line_limit',
							label='limit line test function status',
							set_cmd=':CALCulate:LLINe:TEST {}',
							get_cmd=':CALCulate:LLINe:TEST?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('couple_marker_state',
							label='couple marker function state',
							set_cmd=':CALCulate:MARKer:COUPle:STATe {}',
							get_cmd=':CALCulate:MARKer:COUPle:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('peak_offset',
							label='peak offset',
							set_cmd=':CALCulate:MARKer:PEAK:EXCursion {}',
							get_cmd=':CALCulate:MARKer:PEAK:EXCursion?',
							vals=vals.Numbers(0,100),
							unit='dB',
							get_parser=float)

		self.add_parameter('peak_offset_state',
							label='peak offset function state',
							set_cmd=':CALCulate:MARKer:PEAK:EXCursion:STATe {}',
							get_cmd=':CALCulate:MARKer:PEAK:EXCursion:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('peak_search',
							label='peak search mode',
							set_cmd=':CALCulate:MARKer:PEAK:SEARch:MODE {}',
							get_cmd=':CALCulate:MARKer:PEAK:SEARch:MODE?',
							vals=vals.Enum('PAR', 'MAX'),
							get_parser=str.rstrip)

		self.add_parameter('sort_order',
							label='sorting order of data in peak table',
							set_cmd=':CALCulate:MARKer:PEAK:SORT {}',
							get_cmd=':CALCulate:MARKer:PEAK:SORT?',
							vals=vals.Enum('FREQ', 'AMPL'),
							get_parser=str.rstrip)

		self.add_parameter('peak_criteria',
							label='peak criteria displaeyd peak must meet',
							set_cmd=':CALCulate:MARKer:PEAK:TABLe:READout',
							get_cmd=':CALCulate:MARKer:PEAK:TABLe:READout?',
							vals=vals.Enum('ALL', 'GTDL', 'LTDL', 'NORM', 'DLM', 'DLL'),
							get_parser=str.rstrip)

		self.add_parameter('peak_table',
							label='peak table status',
							set_cmd=':CALCulate:MARKer:PEAK:TABLe:STATe {}',
							get_cmd=':CALCulate:MARKer:PEAK:TABLe:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('peak_threshold',
							label='peak threshold',
							set_cmd=':CALCulate:MARKer:PEAK:THReshold {}',
							get_cmd=':CALCulate:MARKer:PEAK:THReshold?',
							vals=vals.Numbers(-200,0),
							unit='dBm',
							get_parser=float)

		self.add_parameter('threshold_state',
							label='peak threshold function state',
							set_cmd=':CALCulate:MARKer:PEAK:THReshold:STATe {}',
							get_cmd=':CALCulate:MARKer:PEAK:THReshold:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('table_state',
							label='marker table state',
							set_cmd=':CALCulate:MARKer:TABLe:STATe {}',
							get_cmd=':CALCulate:MARKer:TABLe:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('signal_track_state',
							label='signal track state',
							set_cmd=':CALCulate:MARKer:TRCKing:STATe {}',
							get_cmd=':CALCulate:MARKer:TRCKing:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('_math',
							label='mathematical operations between traces',
							set_cmd=':CALCulate:MATH {}')

		self.add_parameter('math_query',
							label='query operations between traces',
							get_cmd=':CALCulate:MATH? {}',
							vals=vals.Enum('TRACE1', 'TRACE2', 'TRACE3', 'TRACE4', 'TRACE5', 'TRACE6'),
							get_parser=str.rstrip)

		self.add_parameter('normalization',
							label='normalization function state',
							set_cmd=':CALCulate:NTData:STATe {}',
							get_cmd=':CALCulate:NTData:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)


		for i in range(1,8+1):
			marker_module=Marker(self, f'ma{i}', i)
			self.add_submodule(f'ma{i}', marker_module)

	def math(self, destination, function, tr1, tr2, offset, reference):
		'''
		Math parameter wrapper
		Args:
			destination
			function
			trace1
			trace2
			offset
			reference
		'''
		vals.Enum('TRACE1', 'TRACE2', 'TRACE3', 'TRACE4', 'TRACE5', 'TRACE6').validate(destination)
		vals.Enum('PDIF', 'PSUM', 'LOFF', 'LMOFF', 'LDIF', 'OFF').validate(function)
		vals.Enum('TRACE1', 'TRACE2', 'TRACE3', 'TRACE4', 'TRACE5', 'TRACE6').validate(tr1)
		vals.Enum('TRACE1', 'TRACE2', 'TRACE3', 'TRACE4', 'TRACE5', 'TRACE6').validate(tr2)
		vals.Numbers(-100,100).validate(offset)
		vals.Numbers(-170,30).validate(reference)
		input=f'{destination},{function},{tr1},{tr2},{offset},{reference}'
		self._math(input)
	
	def all_delete(self): self.write(':CALCulate:LLINe:ALL:DELete')
	
	def all_off(self): self.write(':CALCulate:MARKer:AOFF')

class Marker(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, marknum):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('continuous',
							label=f'Marker {marknum} continuous peak search function',
							set_cmd=f':CALCulate:MARKer{marknum}:CPSearch:STATe {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:CPSearch:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('marker_gatetime',
							label=f'Marker {marknum} gate time for marker n',
							set_cmd=f':CALCulate:MARKer{marknum}:FCOunt:GATetime {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:FCOunt:GATetime?',
							vals=vals.Numbers(1e-6,500e-3),
							unit='s',
							get_parser=float)

		self.add_parameter('gatetime_auto',
							label=f'Marker {marknum} auto gate time for marker n status',
							set_cmd=f':CALCulate:MARKer{marknum}:FCOunt:GATetime:AUTO {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:FCOunt:GATetime:AUTO?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('frequency_counter',
							label=f'Marker {marknum} frequency counter function',
							set_cmd=f':CALCulate:MARKer{marknum}:FCOunt:STATe {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:FCOunt:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('specified_counter',
							label=f'Marker {marknum} query readout frequency counter of specified marker',
							get_cmd=f':CALCulate:MARKer{marknum}:FCOunt:X?',
							unit='Hz',
							get_parser=int)

		self.add_parameter('special_type',
							label=f'Marker {marknum} special measurement type for specified marker',
							set_cmd=f':CALCulate:MARKer{marknum}:FUNCtion {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:FUNCtion?',
							vals=vals.Enum('NOIS', 'BPOW', 'BDEN', 'OFF'),
							get_parser=str.rstrip)

		self.add_parameter('_left_edge',
							label=f'Marker {marknum} left edge frequency of time of signal',
							set_cmd=f':CALCulate:MARKer{marknum}:FUNCtion:BAND:LEFT {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:FUNCtion:BAND:LEFT?',
							vals=vals.Numbers(0),
							get_parser=float)

		self.add_parameter('_right_edge',
							label=f'Marker {marknum} right edge frequency of time of signal',
							set_cmd=f':CALCulate:MARKer{marknum}:FUNCtion:BAND:RIGHt {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:FUNCtion:BAND:RIGHt?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('edge_span',
							label=f'Marker {marknum} time span of signal',
							set_cmd=f':CALCulate:MARKer{marknum}:FUNCtion:BAND:SPAN {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:FUNCtion:BAND:SPAN?',
							vals=vals.Numbers(0),
							get_parser=float)

		self.add_parameter('span_auto',
							label=f'Marker {marknum} band span auto function',
							set_cmd=f':CALCulate:MARKer{marknum}:FUNCtion:BAND:SPAN:AUTO {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:FUNCtion:BAND:SPAN:AUTO?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('marker_line',
							label=f'Marker {marknum} marker line of specified marker',
							set_cmd=f':CALCulate:MARKer{marknum}:LINes:STATe {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:LINes:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('marker_mode',
							label=f'Marker {marknum} type of specified marker',
							set_cmd=f':CALCulate:MARKer{marknum}:MODE {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:MODE?',
							vals=vals.Enum('POS', 'DELT', 'FIX', 'OFF'),
							get_parser=str.rstrip)

		self.add_parameter('reference',
							label=f'Marker {marknum} reference marker for specified marker',
							set_cmd=f':CALCulate:MARKer{marknum}:REFerence {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:REFerence?',
							vals=vals.Ints(1,8),
							get_parser=int)

		self.add_parameter('specified_state',
							label=f'Marker {marknum} specified marker state',
							set_cmd=f':CALCulate:MARKer{marknum}:STATe {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)
		
		self.add_parameter('specified_trace',
							label=f'Marker {marknum} marker trace for specified marker',
							set_cmd=f':CALCulate:MARKer{marknum}:TRACe {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:TRACe?',
							vals=vals.Ints(1,6),
							get_parser=int)

		self.add_parameter('auto_trace',
							label=f'Marker {marknum} auto trace of specified marker state',
							set_cmd=f':CALCulate:MARKer{marknum}:TRACe:AUTO {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:TRACe:AUTO?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('_marker_x',
							label=f'Marker {marknum} x axis value of specified marker',
							set_cmd=f':CALCulate:MARKer{marknum}:X {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:X?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('marker_readout',
							label=f'Marker {marknum} readout mode of x axis of specified marker',
							set_cmd=f':CALCulate:MARKer{marknum}:X:READout {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:X:READout?',
							vals=vals.Enum('FREQ', 'TIME', 'ITIM', 'PER'),
							get_parser=str.rstrip)

		self.add_parameter('readout_auto',
							label=f'Marker {marknum} auto readout mode state',
							set_cmd=f':CALCulate:MARKer{marknum}:X:READout:AUTO {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:X:READout:AUTO?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('marker_y',
							label=f'Marker {marknum} y axis value of marker',
							set_cmd=f':CALCulate:MARKer{marknum}:Y {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:Y?',
							vals=vals.Numbers(-170,30),
							unit='dBm',
							get_parser=float)

		self.add_parameter('spectrogram_number',
							label=f'Marker {marknum} trace number of trace where marker stays in spectrogram view',
							set_cmd=f':CALCulate:MARKer{marknum}:Z:POSition {{}}',
							get_cmd=f':CALCulate:MARKer{marknum}:Z:POSition?',
							vals=vals.Ints(1,8192),
							get_parser=int)

	def left_edge(self, left_edge: float=None):
		if left_edge==None:
			return self._left_edge()
		limit=self._right_edge
		if left_edge<0 or let_edge>limit:
			raise ValueError('Left edge is outside the limit.\n'
							'Must be between 0 and the right edge.\n'
							f'Currently must be less than {limit}s.\n')
		else:
			self._left_edge(left_edge)

	def right_edge(self, right_edge: float=None):
		if right_edge==None:
			return self._right_edge()
		limit=self._left_edge
		if right_edge<limit:
			raise ValueError('Right edge is outside the limit.\n'
							'Must be more than left edge.\n'
							f'Currently must be more than {limit}s.\n')
		else:
			self._right_edge(right_edge)

	def marker_x(self, param):
		'''
		Marker x parameter wrapper
		Args:
			parameter
		'''
		dom=self.ask(f':CALCulate:MARKer{marknum}:X:READout?').rstrip()
		if dom=='FREQ':
			vals.Lists(vals.Numbers(9e3,self.freq_max)).validate(param)
		else:
			vals.Lists(vals.Numbers(1/9e3,1/self.freq_max)).validate(param)
		input=f'{param}'
		self._marker_x(input)


	def max_left(self): self.write(f':CALCulate:MARKer{marknum}:MAXimum:LEFT')
	def max(self): self.write(f':CALCulate:MARKer{marknum}:MAXimum:MAX')
	def max_next(self): self.write(f':CALCulate:MARKer{marknum}:MAXimum:NEXT')
	def max_right(self): self.write(f':CALCulate:MARKer{marknum}:MAXimum:RIGHt')
	def min(self): self.write(f':CALCulate:MARKer{marknum}:MINimum')
	def peak(self): self.write(f':CALCulate:MARKer{marknum}:PTPeak')
	def center(self): self.write(f':CALCulate:MARKer{marknum}:SET:CENTer')
	def delta_center(self): self.write(f':CALCulate:MARKer{marknum}:SET:DELTa:CENTer')
	def delta_span(self): self.write(f':CALCulate:MARKer{marknum}:SET:DELTa:SPAN')
	def reference(self): self.write(f':CALCulate:MARKer{marknum}:SET:RLEVel')
	def start_freq(self): self.write(f':CALCulate:MARKer{marknum}:SET:STARt')
	def step(self): self.write(f':CALCulate:MARKer{marknum}:SET:STEP')
	def stop(self): self.write(f':CALCulate:MARKer{marknum}:SET:STOP')
	def line_delete(self): self.write(f':CALCulate:LLINe{tracenum}:DELete')

class Calibration(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('auto',
							label='auto calibration setting',
							set_cmd=':CALibration:AUTO {}',
							get_cmd=':CALibration:AUTO?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)
						
	def all(self): self.write(':CALibration:ALL')

class Configure(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('measurement',
							label='current measurement function query',
							get_cmd=':CONFigure?',
							get_parser=str.rstrip)

	def AC_power(self): self.write(':CONFigure:ACPower')
	def CN_ratio(self): self.write(':CONFigure:CNRatio')
	def Density(self): self.write(':CONFigure:DENSity')
	def Density_Spectrogram(self): self.write(':CONFigure:DSPEctrogram')
	def EBW(self): self.write(':CONFigure:EBWidth')
	def Harmonic_Distortion(self): self.write(':CONFigure:HDISt')
	def Reset(self): self.write(':CONFigure:LPSTep')
	def MCHP(self): self.write(':CONFigure:MCHPower')
	def Normal(self): self.write(':CONFigure:NORMal')
	def OBW(self): self.write(':CONFigure:OBWidth')
	def PvT_Spectrogram(self): self.write(':CONFigure:PSGRam')
	def PvT_Spectrum(self): self.write(':CONFigure:PSPectrum')
	def PvT(self): self.write(':CONFigure:PVT')
	def swept(self): self.write(':CONFigure:SANalyzer')
	def Spectogram(self): self.write(':CONFigure:SPECtrogram')
	def TOI(self): self.write(':CONFigure:TOI')
	def T_Power(self): self.write(':CONFigure:TPOWer')

class Couple(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

	def all(self): self.write(':COUPle ALL')

class Display(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('backlight',
							label='backlight brightness',
							set_cmd=':DISPlay:BACKlight {}',
							get_cmd=':DISPlay:BACKlight?',
							vals=vals.Ints(1,100),
							get_parser=int)

		self.add_parameter('LCD',
							label='LCD status',
							set_cmd=':DISPlay:ENABle {}',
							get_cmd=':DISPlay:ENABle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('graticule',
							label='graticule status',
							set_cmd=':DISPlay:GRATicule:STATe {}',
							get_cmd=':DISPlay:GRATicule:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('HDMI',
							label='HDMi status',
							set_cmd=':DISPlay:HDMI:STATe {}',
							get_cmd=':DISPlay:HDMI:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('x_autoscale_PvT',
							label='auto scale function for horizontal axis in PvT view',
							set_cmd=':DISPlay:PVTime:WINDow:TRACe:X:SCALe:COUPle {}',
							get_cmd=':DISPlay:PVTime:WINDow:TRACe:X:SCALe:COUPle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('x_division_PvT',
							label='unit per division of horizontal PvT view',
							set_cmd=':DISPlay:PVTime:WINDow:TRACe:X:SCALe:PDIVision {}',
							get_cmd=':DISPlay:PVTime:WINDow:TRACe:X:SCALe:PDIVision?',
							vals=vals.Numbers(20e-6,4),
							unit='s',
							get_parser=float)

		self.add_parameter('x_reference_PvT',
							label='reference time in horizontal PvT view',
							set_cmd=':DISPlay:PVTime:WINDow:TRACe:X:SCALe:RLEVel {}',
							get_cmd=':DISPlay:PVTime:WINDow:TRACe:X:SCALe:RLEVel?',
							vals=vals.Numbers(-1,40),
							unit='s',
							get_parser=float)

		self.add_parameter('x_reference_position',
							label='position of reference time of horizontal PvT view',
							set_cmd=':DISPlay:PVTime:WINDow:TRACe:X:SCALe:RPOSition {}',
							get_cmd=':DISPlay:PVTime:WINDow:TRACe:X:SCALe:RPOSition?',
							vals=vals.Enum('LEFT', 'CENT', 'RIGH'),
							get_parser=str.rstrip)

		self.add_parameter('y_division_PvT',
							label='unit per division in vertical PvT view',
							set_cmd=':DISPlay:PVTime:WINDow:TRACe:Y:SCALe:PDIVision {}',
							get_cmd=':DISPlay:PVTime:WINDow:TRACe:Y:SCALe:PDIVision?',
							vals=vals.Numbers(0.1,20),
							get_parser=float)

		self.add_parameter('y_reference_PvT',
							label='reference level in vertical PvT view',
							set_cmd=':DISPlay:PVTime:WINDow:TRACe:Y:SCALe:RLEVel {}',
							get_cmd=':DISPlay:PVTime:WINDow:TRACe:Y:SCALe:RLEVel?',
							vals=vals.Numbers(-250,250),
							unit='dBm',
							get_parser=float)

		self.add_parameter('curve_nonlinearity',
							label='curve nonlinearity',
							set_cmd=':DISPlay:VIEW:DENSity:CNONlinear {}',
							get_cmd=':DISPlay:VIEW:DENSity:CNONlinear?',
							vals=vals.Numbers(-100,100),
							get_parser=float)

		self.add_parameter('color_palette',
							label='color palette of density',
							set_cmd=':DISPlay:VIEW:DENSity:CPALettes {}',
							get_cmd=':DISPlay:VIEW:DENSity:CPALettes?',
							vals=vals.Enum('COOL', 'WARM', 'RAD', 'FIRE', 'FROS'),
							get_parser=str.rstrip)

		self.add_parameter('highest_hue',
							label='highest density hue',
							set_cmd=':DISPlay:VIEW:DENSity:HDHue {}',
							get_cmd=':DISPlay:VIEW:DENSity:HDHue?',
							vals=vals.Numbers(0.1,100),
							get_parser=float)

		self.add_parameter('lowest_hue',
							label='lowest density hue',
							set_cmd=':DISPlay:VIEW:DENSity:LDHue {}',
							get_cmd=':DISPlay:VIEW:DENSity:LDHue?',
							vals=vals.Numbers(0,99.9),
							get_parser=float)

		self.add_parameter('persistence_time',
							label='persistence time',
							set_cmd=':DISPlay:VIEW:DENSity:PERSistence {}',
							get_cmd=':DISPlay:VIEW:DENSity:PERSistence?',
							vals=vals.Numbers(0,10),
							unit='s',
							get_parser=float)

		self.add_parameter('infinite_mode',
							label='persistence time infinite mode status',
							set_cmd=':DISPlay:VIEW:DENSity:PERSistence:INFinite {}',
							get_cmd=':DISPlay:VIEW:DENSity:PERSistence:INFinite?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('display_view',
							label='current display view',
							set_cmd=':DISPlay:VIEW:SELect {}',
							get_cmd=':DISPlay:VIEW:SELect?',
							vals=vals.Enum('NORM', 'SPEC', 'DENS', 'DSP', 'PVT', 'PVTS', 'PSP'),
							get_parser=str.rstrip)

		self.add_parameter('bottom_position',
							label='bottom hue position in graticule',
							set_cmd=':DISPlay:VIEW:SPECtrogram:BOTTom {}',
							get_cmd=':DISPlay:VIEW:SPECtrogram:BOTTom?',
							vals=vals.Ints(0,90),
							unit='Hz',
							get_parser=int)

		self.add_parameter('reference_hue',
							label='reference hue',
							set_cmd=':DISPlay:VIEW:SPECtrogram:HUE {}',
							get_cmd=':DISPlay:VIEW:SPECtrogram:HUE?',
							vals=vals.Numbers(0,359.9),
							get_parser=float)

		self.add_parameter('spectrogram_trace',
							label='trace displayed in spectrogram',
							set_cmd=':DISPlay:VIEW:SPECtrogram:POSition {}',
							get_cmd=':DISPlay:VIEW:SPECtrogram:POSition?',
							vals=vals.Ints(1,8192),
							get_parser=int)

		self.add_parameter('reference_position',
							label='position of reference hue in graticule',
							set_cmd=':DISPlay:VIEW:SPECtrogram:REFerence {}',
							get_cmd=':DISPlay:VIEW:SPECtrogram:REFerence?',
							vals=vals.Ints(10,100),
							unit='%',
							get_parser=int)

		self.add_parameter('coupling_state',
							label='coupling the marker to the trace',
							set_cmd=':DISPlay:VIEW:SPECtrogram:TRACe:COUPle {}',
							get_cmd=':DISPlay:VIEW:SPECtrogram:TRACe:COUPle?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('trace_selection',
							label='selection method for displayed trace',
							set_cmd=':DISPlay:VIEW:SPECtrogram:TRACe:SELection {}',
							get_cmd=':DISPlay:VIEW:SPECtrogram:TRACe:SELection?',
							vals=vals.Enum('TIME', 'TNUM'),
							get_parser=str.rstrip)

		self.add_parameter('window_select',
							label='select window in current view',
							set_cmd=':DISPlay:WINDow:SELect {}',
							get_cmd=':DISPlay:WINDow:SELect?',
							vals=vals.Enum('SPEC', 'PVT'),
							get_parser=str.rstrip)

		self.add_parameter('_display_line',
							label='position of display line',
							set_cmd=':DISPlay:WINDow:TRACe:Y:DLINe {}',
							get_cmd=':DISPlay:WINDow:TRACe:Y:DLINe?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('display_state',
							label='display line state',
							set_cmd=':DISPlay:WINDow:TRACe:Y:DLINe:STATe {}',
							get_cmd=':DISPlay:WINDow:TRACe:Y:DLINe:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('normalization_reference',
							label='reference level of normalization',
							set_cmd=':DISPlay:WINDow:TRACe:Y:SCALe:NRLevel {}',
							get_cmd=':DISPlay:WINDow:TRACe:Y:SCALe:NRLevel?',
							vals=vals.Numbers(-200,200),
							unit='dBm',
							get_parser=float)

		self.add_parameter('normalization_position',
							label='reference position of normalization',
							set_cmd=':DISPlay:WINDow:TRACe:Y:SCALe:NRPosition {}',
							get_cmd=':DISPlay:WINDow:TRACe:Y:SCALe:NRPosition?',
							vals=vals.Ints(0,100),
							unit='%',
							get_parser=int)

		self.add_parameter('y_scale',
							label='y axis scale type',
							set_cmd=':DISPlay:WINDow:TRACe:Y:SCALe:PDIVision {}',
							get_cmd=':DISPlay:WINDow:TRACe:Y:SCALe:PDIVision?',
							vals=vals.Numbers(0.1,20),
							unit='dB',
							get_parser=float)

		self.add_parameter('y_level',
							label='y reference level',
							set_cmd=':DISPlay:WINDow:TRACe:Y:SCALe:RLEVel {}',
							get_cmd=':DISPlay:WINDow:TRACe:Y:SCALe:RLEVel?',
							vals=vals.Numbers(-170,30),
							unit='dBm',
							get_parser=float)

		self.add_parameter('y_offset',
							label='y reference level offset',
							set_cmd=':DISPlay:WINDow:TRACe:Y:SCALe:RLEVel:OFFSet {}',
							get_cmd=':DISPlay:WINDow:TRACe:Y:SCALe:RLEVel:OFFSet?',
							vals=vals.Numbers(-300,300),
							unit='dBm',
							get_parser=float)

		self.add_parameter('y_axis',
							label='y axis scale type',
							set_cmd=':DISPlay:WINDow:TRACe:Y:SCALe:SPACing {}',
							get_cmd=':DISPlay:WINDow:TRACe:Y:SCALe:SPACing?',
							vals=vals.Enum('LIN', 'LOG'),
							get_parser=str.rstrip) 
							
	def display_line(self, display_line: float=None):
		if display_line==None:
			return self._display_line()
		low_limit=self.ask(':SENSe:SIGCapture:2FSK:AMPDown?').float()
		up_limit=self.ask(':SENSe:SIGCapture:2FSK:AMPUp?').float()
		if display_line<low_limit or display_line>up_limit:
			raise ValueError('display line is outside the limit.\n'
							'Must be between lower and upper limit.\n'
							f'Currently must be between {low_limit} and {up_limit}s.\n')
		else:
			self._display_line(display_line)
		
	
	def auto_adjust(self): self.write(':DISPlay:VIEW:SPECtrogram:AADJust')

class Fetch(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('AC_power',
							label='adjacent channel power query',
							get_cmd=':FETCh:ACPower?',
							get_parser=str.rstrip)

		self.add_parameter('AC_power_lower',
							label='adjacent channel lower power query',
							get_cmd=':FETCh:ACPower:LOWer?',
							get_parser=float)

		self.add_parameter('AC_power_main',
							label='adjacent channel main power query',
							get_cmd=':FETCh:ACPower:MAIN?',
							get_parser=float)

		self.add_parameter('AC_power_upper',
							label='adjacent channel upper power query',
							get_cmd=':FETCh:ACPower:UPPer?',
							get_parser=float)

		self.add_parameter('CN_ratio',
							label='C/N ratio query',
							get_cmd=':FETCh:CNRatio?',
							get_parser=float)

		self.add_parameter('carrier_power',
							label='carrier power query',
							get_cmd=':FETCh:CNRatio:CARRier?',
							get_parser=float)

		self.add_parameter('CN_result',
							label='C/N ratio result query',
							get_cmd=':FETCh:CNRatio:CNRatio?',
							get_parser=float)

		self.add_parameter('noise',
							label='noise power query',
							get_cmd=':FETCh:CNRatio:NOISe?',
							get_parser=float)

		self.add_parameter('emission_bandwidth',
							label='emission bandwidth query',
							get_cmd=':FETCh:EBWidth?',
							get_parser=float)

		self.add_parameter('harmonics_amplitude_all',
							label='amplitudes of first ten harmonics query',
							get_cmd=':FETCh:HARMonics:AMPLitude:ALL?',
							get_parser=str.rstrip)

		self.add_parameter('harmonic_amplitude',
							label='specified harmonic amplitude query',
							get_cmd=':FETCh:HARMonics:AMPLitude? {}',
							vals=vals.Ints(1,10),
							get_parser=float)

		self.add_parameter('distortion',
							label='percentage of total harmonic distortion query',
							get_cmd=':FETCh:HARMonics:DISTortion?',
							get_parser=float)

		self.add_parameter('harmonics_frequency_all',
							label='frequencies of first ten harmonics query',
							get_cmd=':FETCh:HARMonics:FREQuency:ALL?',
							get_parser=str.rstrip)

		self.add_parameter('harmonic_frequency',
							label='specified harmonic frequency query',
							get_cmd=':FETCh:HARMonics:FREQuency? {}',
							vals=vals.Ints(1,10),
							get_parser=float)

		self.add_parameter('harmonics_fundamental',
							label='frequency of fundamental waveform query',
							get_cmd=':FETCh:HARMonics:FUNDamental?',
							get_parser=float)

		self.add_parameter('occupied_bandwidth_result',
							label='occupied bandwidth result query',
							get_cmd=':FETCh:OBWidth?',
							get_parser=str.rstrip)

		self.add_parameter('occupied_bandwidth',
							label='occupied bandwidth query',
							get_cmd=':FETCh:OBWidth:OBWidth?',
							get_parser=float)

		self.add_parameter('transmit_error',
							label='transmit frequency error query',
							get_cmd=':FETCh:OBWidth:OBWidth:FERRor?',
							get_parser=float)

		self.add_parameter('TOI',
							label='TOI measurement result query',
							get_cmd=':FETCh:TOIntercept?',
							get_parser=str.rstrip)

		self.add_parameter('IP3',
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
							label='binary data byte order for data transmission',
							set_cmd=':FORMat:BORDer {}',
							get_cmd=':FORMat:BORDer?',
							vals=vals.Enum('NORM', 'SWAP'),
							get_parser=str.rstrip)

		self.add_parameter('trace_data',
							label='input/output format of trace data',
							set_cmd=':FORMat:TRACe:DATA {}',
							get_cmd=':FORMat:TRACe:DATA?',
							vals=vals.Enum('ASCii', 'INTeger,32', 'REAL,32', 'REAL,64'),
							get_parser=str.rstrip)

class Initiate(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('continuous',
							label='continuous mode',
							set_cmd=':INITiate:CONTinuous {}',
							get_cmd=':INITiate:CONTinuous?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)
	
	def initiate(self): self.write(':INITiate:IMMediate')

class Instrument(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('global_frequency',
							label='global frequency center of instrument',
							set_cmd=':INSTrument:COUPle:FREQuency:CENTer {}',
							get_cmd=':INSTrument:COUPle:FREQuency:CENTer?',
							vals=vals.Enum('ALL', 'NONE'),
							get_parser=str.rstrip)

		self.add_parameter('n_mode',
							label='working mode of instrument',
							set_cmd=':INSTrument:NSELect {}',
							get_cmd=':INSTrument:NSELect?',
							vals=vals.Enum(1,2),
							get_parser=str.rstrip)

		self.add_parameter('mode',
							label='working mode of instrument',
							set_cmd=':INSTrument:SELect {}',
							get_cmd=':INSTrument:SELect?',
							vals=vals.Enum('GPSA', 'RTSA'),
							val_mapping={'GPSA':'SA', 'RTSA':'RTSA'},
							get_parser=str.rstrip)

class MassMemory(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('delete',
							label='deletes specified file',
							set_cmd=':MMEMory:DELete {}',
							vals=vals.Strings())

		self.add_parameter('_load_FMT',
							label='loads edited FMT file',
							set_cmd=':MMEMory:LOAD:FMT {}')

		self.add_parameter('_load_limit',
							label='imports edited limit line file',
							set_cmd=':MMEMory:LOAD:LIMit {}')

		self.add_parameter('load_state',
							label='imports specified state file',
							set_cmd=':MMEMory:LOAD:STATe {}',
							vals=vals.Strings())

		self.add_parameter('_load_trace',
							label='imports specified trace file',
							set_cmd=':MMEMory:LOAD:TRACe {}')

		self.add_parameter('_load_data',
							label='imports specified measurement data file',
							set_cmd=':MMEMory:LOAD:TRACe:DATA {}')

		self.add_parameter('_move',
							label='renames specified file',
							set_cmd=':MMEMory:MOVE {}')

		self.add_parameter('_store_limit',
							label='saves current edited limit line with specified file name',
							set_cmd=':MMEMory:STORe:LIMit {}')

		self.add_parameter('marker_table',
							label='saves marker table with specified filename',
							set_cmd=':MMEMory:STORe:MTABle {}',
							vals=vals.Strings())

		self.add_parameter('peak_table',
							label='saves peak table with specified filename',
							set_cmd=':MMEMory:STORe:PTABle {}',
							vals=vals.Strings())

		self.add_parameter('results',
							label='saves current measurement result with specified filename',
							set_cmd=':MMEMory:STORe:RESults {}',
							vals=vals.Strings())

		self.add_parameter('screen_image',
							label='saves current screen image with specified filename',
							set_cmd=':MMEMory:STORe:SCReen {}',
							vals=vals.Strings())

		self.add_parameter('store_state',
							label='saves current instrument state with specified filename',
							set_cmd=':MMEMory:STORe:STATe {}',
							vals=vals.Strings())

		self.add_parameter('_store_trace',
							label='saves specified trace+state file with specified filename',
							set_cmd=':MMEMory:STORe:TRACe {}')

		self.add_parameter('_store_data',
							label='saves trace measurement results with specified filename',
							set_cmd=':MMEMory:STORe:TRACe:DATA {}')

	def load_FMT(self, line, filename):
		'''
		Load FMT parameter wrapper
		Args:
			line
			filename
		'''
		vals.Enum('UPP', 'LOW').validate(line)
		vals.Strings().validate(filename)
		input=f'{line},{filename}'
		self._load_FMT(input)

	def load_limit(self, line, filename):
		'''
		Load limit parameter wrapper
		Args:
			line
			filename
		'''
		vals.Enum('LLINE1', 'LLINE2', 'LLINE3', 'LLINE4', 'LLINE5', 'LLINE6').validate(line)
		vals.Strings().validate(filename)
		input=f'{line},{filename}'
		self._load_limit(input)

	def load_trace(self, trace, filename):
		'''
		Load trace parameter wrapper
		Args:
			trace
			filename
		'''
		vals.Enum('TRACE1', 'TRACE2', 'TRACE3', 'TRACE4', 'TRACE5', 'TRACE6').validate(trace)
		vals.Strings().validate(filename)
		input=f'{trace},{filename}'
		self._load_trace(input)

	def load_data(self, trace, filename):
		'''
		Load data parameter wrapper
		Args:
			trace
			filename
		'''
		vals.Enum('TRACE1', 'TRACE2', 'TRACE3', 'TRACE4', 'TRACE5', 'TRACE6').validate(trace)
		vals.Strings().validate(filename)
		input=f'{trace},{filename}'
		self._load_data(input)

	def move(self, file1, file2):
		'''
		Move parameter wrapper
		Args:
			file1
			file2
		'''
		vals.Strings().validate(file1)
		vals.Strings().validate(file2)
		input=f'{file1},{file2}'
		self._move(input)

	def store_limit(self, line, filename):
		'''
		Store limit parameter wrapper
		Args:
			line
			filename
		'''
		vals.Enum('LLINE1', 'LLINE2', 'LLINE3', 'LLINE4', 'LLINE5', 'LLINE6').validate(line)
		vals.Strings().validate(filename)
		input=f'{line},{filename}'
		self._store_limit(input)

	def store_trace(self, trace, filename):
		'''
		Store trace parameter wrapper
		Args:
			trace
			filename
		'''
		vals.Enum('TRACE1', 'TRACE2', 'TRACE3', 'TRACE4', 'TRACE5', 'TRACE6').validate(trace)
		vals.Strings().validate(filename)
		input=f'{trace},{filename}'
		self._store_trace(input)

	def store_data(self, trace, filename):
		'''
		Store data parameter wrapper
		Args:
			trace
			filename
		'''
		vals.Enum('TRACE1', 'TRACE2', 'TRACE3', 'TRACE4', 'TRACE5', 'TRACE6').validate(trace)
		vals.Strings().validate(filename)
		input=f'{trace},{filename}'
		self._store_data(input)

class Output(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('state',
							label='output of tracking generator state',
							set_cmd=':OUTPut:EXTernal:STATe {}',
							get_cmd=':OUTPut:EXTernal:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)		

class Read(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('AC_power',
							label='adjacent channel power measurement',
							get_cmd=':READ:ACPower?',
							get_parser=str.rstrip)

		self.add_parameter('AC_power_lower',
							label='adjacent lower channel power measurement',
							get_cmd=':READ:ACPower:LOWer?',
							get_parser=float)

		self.add_parameter('AC_power_main',
							label='adjacent main channel power measurement',
							get_cmd=':READ:ACPower:MAIN?',
							get_parser=float)

		self.add_parameter('AC_power_upper',
							label='adjacent upper channel power measurement',
							get_cmd=':READ:ACPower:UPPer?',
							get_parser=float)

		self.add_parameter('CN_measurement',
							label='C/N ratio returns measurement',
							get_cmd=':READ:CNRatio?',
							get_parser=str.rstrip)

		self.add_parameter('CN_carrier_power',
							label='C/N ratio returns carrier power',
							get_cmd=':READ:CNRatio:CARRier?',
							get_parser=float)

		self.add_parameter('CN_ratio',
							label='C/N ratio',
							get_cmd=':READ:CNRatio:CNRatio?',
							get_parser=float)

		self.add_parameter('CN_noise',
							label='C/N ratio returns noise power',
							get_cmd=':READ:CNRatio:NOISe?',
							get_parser=float)

		self.add_parameter('emission_bandwidth',
							label='emission bandwidth measurement',
							get_cmd=':READ:EBWidth?',
							get_parser=float)

		self.add_parameter('harmonics_amplitude_all',
							label='harmonic distortion measurement returns amplitudes of first ten harmonics',
							get_cmd=':READ:HARMonics:AMPLitude:ALL?',
							get_parser=str.rstrip)

		self.add_parameter('harmonic_amplitude',
							label='harmonic distortion returns amplitude of specified harmonic',
							get_cmd=':READ:HARMonics:AMPLitude? {}',
							get_parser=float)

		self.add_parameter('distortion',
							label='returns percentage of total harmonic distortion',
							get_cmd=':READ:HARMonics:DISTortion?',
							get_parser=float)

		self.add_parameter('harmonics_frequency_all',
							label='harmonic distortion measurement returns frequencies of first ten harmonics',
							get_cmd=':READ:HARMonics:FREQuency:ALL?',
							get_parser=str.rstrip)

		self.add_parameter('harmonic_frequency',
							label='harmonic distortion returns frequency of specified harmonic',
							get_cmd=':READ:HARMonics:FREQuency? {}',
							vals=vals.Ints(1,10),
							get_parser=float)

		self.add_parameter('harmonics_fundamental',
							label='harmonic distortion returns fundamental waveform frequency',
							get_cmd=':READ:HARMonics:FUNDamental?',
							get_parser=float)

		self.add_parameter('occupied_bandwidth_measurement',
							label='occupied bandwidth measurement',
							get_cmd=':READ:OBWidth?',
							get_parser=str.rstrip)

		self.add_parameter('occupied_bandwidth',
							label='occupied bandwidth',
							get_cmd=':READ:OBWidth:OBWidth:FERRor?',
							get_parser=float)

		self.add_parameter('TOI',
							label='TOI measurement',
							get_cmd=':READ:TOIntercept?',
							get_parser=str.rstrip)

		self.add_parameter('IP3',
							label='IP3 measurement',
							get_cmd=':READ:TOIntercept:IP3?',
							get_parser=float)

		self.add_parameter('T_power',
							label='T-power measurement',
							get_cmd=':READ:TPOWer?',
							get_parser=float)

class Sense(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('input_impedance',
							label='input impedance for voltage to power conversion',
							set_cmd=':INPut:IMPedance {}',
							get_cmd=f':INPut:IMPedance?',
							vals=vals.Enum(50,75),
							unit='ohm',
							get_parser=str.rstrip)
		
		self.add_parameter('correction_impedance',
							label='input impedance for voltage to power conversion',
							set_cmd=':SENSe:CORRection:IMPedance:INPut:MAGNitude {}',
							get_cmd=':SENSe:CORRection:IMPedance:INPut:MAGNitude?',
							vals=vals.Enum(50,75),
							unit='Ohm',
							get_parser=str.rstrip)

		self.add_parameter('external_gain',
							label='external gain',
							set_cmd=':SENSe:CORRection:SA:RF:GAIN {}',
							get_cmd=':SENSe:CORRection:SA:RF:GAIN?',
							vals=vals.Numbers(-120,120),
							unit='dB',
							get_parser=float)

		acquisition_module=Acquisition(self, 'acquisition')
		self.add_submodule('acquisition', acquisition_module)

		adjacent_module=Adjacent(self, 'adjacent')
		self.add_submodule('adjacent', adjacent_module)

		average_module=Average(self, 'average')
		self.add_submodule('average', average_module)

		bandwidth_module=Bandwidth(self, 'bandwidth')
		self.add_submodule('bandwidth', bandwidth_module)

		cn_module=CN(self, 'cn')
		self.add_submodule('cn', cn_module)

		demodulation_module=Demodulation(self, 'demodulation')
		self.add_submodule('demodulation', demodulation_module)

		emission_module=Emission(self, 'emission')
		self.add_submodule('emission', emission_module)

		frequency_module=Frequency(self, 'frequency')
		self.add_submodule('frequency', frequency_module)

		for i in range(1,6+1):
			detector_module=Detector(self, f'tr{i}', i)
			self.add_submodule(f'tr{i}', detector_module)

		harmonic_module=Harmonic(self, 'harmonic')
		self.add_submodule('harmonic', harmonic_module)

		multi_module=Multi(self, 'multi')
		self.add_submodule('multi', multi_module)

		occupied_module=Occupied(self, 'occupied')
		self.add_submodule('occupied', occupied_module)

		power_module=Power(self, 'power')
		self.add_submodule('power', power_module)

		sig_module=Sig_Capture(self, 'sig')
		self.add_submodule('sig', sig_module)

		sweep_module=Sweep(self, 'sweep')
		self.add_submodule('sweep', sweep_module)

		toi_module=TOI(self, 'toi')
		self.add_submodule('toi', toi_module)

		tpower_module=T_Power(self, 'tpower')
		self.add_submodule('tpower', tpower_module)

class Acquisition(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('acquisition_time',
							label='aquisition time',
							set_cmd=':SENSe:ACQuisition:TIME {}',
							get_cmd=':SENSe:ACQuisition:TIME?',
							vals=vals.Numbers(32e-3,40),
							unit='s',
							get_parser=float)

		self.add_parameter('acquisition_auto',
							label='acquisition auto function',
							set_cmd=':SENSe:ACQuisition:TIME:AUTO {}',
							get_cmd=':SENSe:ACQuisition:TIME:AUTO?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('acquisition_PvTime',
							label='aquisition time PvT',
							set_cmd=':SENSe:ACQuisition:TIME:PVTime {}',
							get_cmd=':SENSe]:ACQuisition:TIME:PVTime?',
							vals=vals.Numbers(0,40),
							unit='s',
							get_parser=float)

		self.add_parameter('acquisition_PvTime_auto',
							label='acquisition time PvT auto function',
							set_cmd=':SENSe:ACQuisition:TIME:PVTime:AUTO {}',
							get_cmd=':SENSe:ACQuisition:TIME:PVTime:AUTO?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

class Adjacent(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('ACP_average_count',
							label='average count of ACP',
							set_cmd=':SENSe:ACPower:AVERage:COUNt {}',
							get_cmd=':SENSe:ACPower:AVERage:COUNt?',
							vals=vals.Ints(1,1000),
							get_parser=int)

		self.add_parameter('ACP_average',
							label='ACP average function state',
							set_cmd=':SENSe:ACPower:AVERage:STATe {}',
							get_cmd=':SENSe:ACPower:AVERage:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('ACP_average_mode',
							label='ACP average mode',
							set_cmd=':SENSe:ACPower:AVERage:TCONtrol {}',
							get_cmd=':SENSe:ACPower:AVERage:TCONtrol?',
							vals=vals.Enum('EXP', 'REP'),
							get_parser=str.rstrip)

		self.add_parameter('ACP_bandwidth',
							label='ACP adjacent bandwidth',
							set_cmd=':SENSe:ACPower:BANDwidth:ACHannel {}',
							get_cmd=':SENSe:ACPower:BANDwidth:ACHannel?',
							vals=vals.Numbers(33,1.5e9),
							unit='Hz',
							get_parser=float)

		self.add_parameter('ACP_integration',
							label='ACP main bandwidth',
							set_cmd=':SENSe:ACPower:BANDwidth:INTegration {}',
							get_cmd=':SENSe:ACPower:BANDwidth:INTegration?',
							vals=vals.Numbers(33,1.5e9),
							unit='Hz',
							get_parser=float)

		self.add_parameter('ACP_spacing',
							label='channel spacing',
							set_cmd=':SENSe:ACPower:CSPacing {}',
							get_cmd=':SENSe:ACPower:CSPacing?',
							vals=vals.Numbers(33,1.5e9),
							unit='Hz',
							get_parser=float)

class Average(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('average_count',
							label='average count of current measurement',
							set_cmd=':SENSe:AVERage:COUNt {}',
							get_cmd=':SENSe]AVERage:COUNt?',
							vals=vals.Ints(1,10000),
							get_parser=int)

		self.add_parameter('current_average',
							label='query current average times',
							get_cmd=':SENSe:AVERage:COUNt:CURRent?',
							get_parser=int)

		self.add_parameter('average_type',
							label='average type',
							set_cmd=':SENSe:AVERage:TYPE {}',
							get_cmd=':SENSe:AVERage:TYPE?',
							vals=vals.Enum('LOG', 'RMS', 'SCAL'),
							get_parser=str.rstrip)

		self.add_parameter('type_auto',
							label='average type auto setting',
							set_cmd=':SENSe:AVERage:TYPE:AUTO {}',
							get_cmd=':SENSe:AVERage:TYPE:AUTO?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

class Bandwidth(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('EMI_filter',
							label='EMI filter status',
							set_cmd=':SENSe:BANDwidth:EMIFilter:STATe {}',
							get_cmd=':SENSe:BANDwidth:EMIFilter:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('resolution_bandwidth',
							label='resolution bandwidth',
							set_cmd=':SENSe:BANDwidth:RESolution {}',
							get_cmd=':SENSe:BANDwidth:RESolution?',
							vals=vals.Numbers(10,3e6),
							unit='Hz',
							get_parser=float)

		self.add_parameter('RBW_auto',
							label='resolution bandwidth auto setting',
							set_cmd=':SENSe:BANDwidth:RESolution:AUTO {}',
							get_cmd=':SENSe:BANDwidth:RESolution:AUTO?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('bandwidth_resolution',
							label='bandwidth resolution',
							set_cmd=':SENSe:BANDwidth:RESolution:SELect {}',
							get_cmd=':SENSe:BANDwidth:RESolution:SELect?',
							vals=vals.Enum('RBW1', 'RBW2', 'RBW3', 'RBW4', 'RBW5', 'RBW6'),
							get_parser=str.rstrip)

		self.add_parameter('auto_RBW',
							label='auto setting of RBW',
							set_cmd=':SENSe:BANDwidth:RESolution:SELect:AUTO:STATe {}',
							get_cmd=':SENSe:BANDwidth:RESolution:SELect:AUTO:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('shape',
							label='filter type',
							set_cmd=':SENSe:BANDwidth:SHAPe {}',
							get_cmd=':SENSe:BANDwidth:SHAPe?',
							vals=vals.Enum('GAUS', 'FLAT', 'BHAR', 'RECT', 'HANN', 'KAIS'),
							get_parser=str.rstrip)

		self.add_parameter('video_bandwidth',
							label='video bandwidth',
							set_cmd=':SENSe:BANDwidth:VIDeo {}',
							get_cmd=':SENSe:BANDwidth:VIDeo?',
							vals=vals.Numbers(1,10e6),
							unit='Hz',
							get_parser=float)

		self.add_parameter('video_auto',
							label='video bandwidth auto setting',
							set_cmd=':SENSe:BANDwidth:VIDeo:AUTO {}',
							get_cmd=':SENSe:BANDwidth:VIDeo:AUTO?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('video_ratio',
							label='ratio of VBW to RBW',
							set_cmd=':SENSe:BANDwidth:VIDeo:RATio {}',
							get_cmd=':SENSe:BANDwidth:VIDeo:RATio?',
							vals=vals.Numbers(0.00001,3000000),
							get_parser=float)

		self.add_parameter('ratio_auto',
							label='V/R ratio auto setting',
							set_cmd=':SENSe:BANDwidth:VIDeo:RATio:AUTO {}',
							get_cmd=':SENSe:BANDwidth:VIDeo:RATio:AUTO?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

class CN(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('CN_count',
							label='avergae count of C/N ratio measurement',
							set_cmd=':SENSe:CNRatio:AVERage:COUNt {}',
							get_cmd=':SENSe:CNRatio:AVERage:COUNt?',
							vals=vals.Ints(1,1000),
							get_parser=int)

		self.add_parameter('CN_average_state',
							label='C/N ratio average state',
							set_cmd=':SENSe:CNRatio:AVERage:STATe {}',
							get_cmd=':SENSe:CNRatio:AVERage:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('CN_mode',
							label='C/N ratio average mode',
							set_cmd=':SENSe:CNRatio:AVERage:TCONtrol {}',
							get_cmd=':SENSe:CNRatio:AVERage:TCONtrol?',
							vals=vals.Enum('EXP', 'REP'),
							get_parser=str.rstrip)

		self.add_parameter('CN_carrier',
							label='C/N carrier bandwidth',
							set_cmd=':SENSe:CNRatio:BANDwidth:INTegration {}',
							get_cmd=':SENSe:CNRatio:BANDwidth:INTegration?',
							vals=vals.Numbers(33,1.5e9),
							unit='Hz',
							get_parser=int)

		self.add_parameter('CN_noise',
							label='C/N noise bandwidth',
							set_cmd=':SENSe:CNRatio:BANDwidth:NOISe {}',
							get_cmd=':SENSe:CNRatio:BANDwidth:NOISe?',
							vals=vals.Numbers(33,1.5e9),
							unit='Hz',
							get_parser=int)

		self.add_parameter('CN_offset',
							label='offset frequency between carrier waveform and noise',
							set_cmd=':SENSe:CNRatio:OFFSet {}',
							get_cmd=':SENSe:CNRatio:OFFSet?',
							vals=vals.Numbers(33,1.5e9),
							unit='Hz',
							get_parser=int)

class Demodulation(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('demodulation',
							label='demodulation type or disable',
							set_cmd=':SENSe:DEMod {}',
							get_cmd=':SENSe:DEMod?',
							vals=vals.Enum('AM', 'FM', 'OFF'),
							get_parser=str.rstrip)

		self.add_parameter('demodulation_auto',
							label='auto setting of demodulation',
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
							label='demodulation function state',
							set_cmd=':SENSe:DEMod:STATe {}',
							get_cmd=':SENSe:DEMod:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

class Detector(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, tracenum):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('PvT_type',
							label='detector type of trace in PvT view',
							set_cmd=':SENSe:DETector:TRACe:PVTime {}',
							get_cmd=':SENSe:DETector:TRACe:PVTime?',
							vals=vals.Enum('AVER', 'NEG', 'POS', 'SAMP'),
							get_parser=str.rstrip)

		self.add_parameter('detector_auto',
							label=f'Trace {tracenum} auto setting of detector function',
							set_cmd=f':SENSe:DETector:TRACe{tracenum}:AUTO {{}}',
							get_cmd=f':SENSe:DETector:TRACe{tracenum}:AUTO?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)
		
		self.add_parameter('detector_type',
							label='detector type',
							set_cmd=':SENSe:DETector:FUNCtion {}',
							get_cmd=':SENSe:DETector:FUNCtion?',
							vals=vals.Enum('AVER', 'NEG', 'NORM', 'POS', 'SAMP', 'QPE', 'RAV'),
							get_parser=str.rstrip)

		self.add_parameter('specified_type',
							label=f'Trace {tracenum} detector type for specified trace',
							set_cmd=f':SENSe:DETector:TRACe{tracenum} {{}}',
							get_cmd=f':SENSe:DETector:TRACe{tracenum}?',
							vals=vals.Enum('AVER', 'NEG', 'NORM', 'POS', 'SAMP', 'QPE', 'RAV'),
							get_parser=str.rstrip)

class Emission(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('emission_average',
							label='average count of emission bandwidth',
							set_cmd=':SENSe:EBWidth:AVERage:COUNt {}',
							get_cmd=':SENSe:EBWidth:AVERage:COUNt?',
							vals=vals.Ints(1,1000),
							get_parser=int)

		self.add_parameter('emission_state',
							label='average function of emission bandwidth state',
							set_cmd=':SENSe:EBWidth:AVERage:STATe {}',
							get_cmd=':SENSe:EBWidth:AVERage:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('emission_mode',
							label='average mode of emission bandwidth measurement',
							set_cmd=':SENSe:EBWidth:AVERage:TCONtrol {}',
							get_cmd=':SENSe:EBWidth:AVERage:TCONtrol?',
							vals=vals.Enum('EXP', 'REP'),
							get_parser=str.rstrip)

		self.add_parameter('emission_span',
							label='span of emission bandwidth measurement',
							set_cmd=':SENSe:EBWidth:FREQuency:SPAN {}',
							get_cmd=':SENSe:EBWidth:FREQuency:SPAN?',
							vals=vals.Numbers(100,4.5e9),
							get_parser=float)

		self.add_parameter('emission_max',
							label='emission bandwidth max hold state',
							set_cmd=':SENSe:EBWidth:MAXHold:STATe {}',
							get_cmd=':SENSe:EBWidth:MAXHold:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('emission_x',
							label='value of X dB for EBW measurement',
							set_cmd=':SENSe:EBWidth:XDB {}',
							get_cmd=':SENSe:EBWidth:XDB?',
							vals=vals.Numbers(-100,-0.1),
							unit='dB',
							get_parser=float)

class Frequency(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('_center_frequency',
							label='center frequency',
							set_cmd=':SENSe:FREQuency:CENTer {}',
							get_cmd=':SENSe:FREQuency:CENTer?',
							vals=vals.Numbers(),
							unit='Hz',
							get_parser=float)

		self.add_parameter('center_auto',
							label='center frequency auto setting',
							set_cmd=':SENSe:FREQuency:CENTer:STEP:AUTO {}',
							get_cmd=':SENSe:FREQuency:CENTer:STEP:AUTO?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('_center_step',
							label='center frequency step',
							set_cmd=':SENSe:FREQuency:CENTer:STEP:INCRement {}',
							get_cmd=':SENSe:FREQuency:CENTer:STEP:INCRement?',
							vals=vals.Numbers(),
							unit='Hz',
							get_parser=float)

		self.add_parameter('frequency_offset',
							label='frequency offset',
							set_cmd=':SENSe:FREQuency:OFFSet {}',
							get_cmd=':SENSe:FREQuency:OFFSet?',
							vals=vals.Numbers(-500e9,500e9),
							unit='Hz',
							get_parser=float)

		self.add_parameter('_frequency_span',
							label='frequency span',
							set_cmd=':SENSe:FREQuency:SPAN {}',
							get_cmd=':SENSe:FREQuency:SPAN?',
							vals=vals.Numbers(),
							unit='Hz',
							get_parser=float)

		self.add_parameter('RBW_span',
							label='ratio of span to RBW',
							set_cmd=':SENSe:FREQuency:SPAN:BANDwidth:RESolution:RATio {}',
							get_cmd=':SENSe:FREQuency:SPAN:BANDwidth:RESolution:RATio?',
							vals=vals.Ints(2,10000),
							get_parser=int)

		self.add_parameter('span_auto',
							label='span/RBW ratio auto setting',
							set_cmd=':SENSe:FREQuency:SPAN:BANDwidth:RESolution:RATio:AUTO {}',
							get_cmd=':SENSe:FREQuency:SPAN:BANDwidth:RESolution:RATio:AUTO?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('_start_frequency',
							label='start frequency',
							set_cmd=':SENSe:FREQuency:STARt {}',
							get_cmd=':SENSe:FREQuency:STARt?',
							vals=vals.Numbers(),
							unit='Hz',
							get_parser=float)

		self.add_parameter('_stop_frequency',
							label='stop frequency',
							set_cmd=':SENSe:FREQuency:STOP {}',
							get_cmd=':SENSe:FREQuency:STOP?',
							vals=vals.Numbers(),
							unit='Hz',
							get_parser=float)
						
	def full_span(self): self.write(':SENSe:FREQuency:SPAN:FULL')
	def prev_span(self): self.write(':SENSe:FREQuency:SPAN:PREVious')
	def zero_span(self): self.write(':SENSe:FREQuency:SPAN:ZERO')
	def tune_immediate(self): self.write(':SENSe:FREQuency:TUNE:IMMediate')

	def center_frequency(self, freq):
		'''
		Center frequency parameter wrapper
		Args:
			frequency
		'''
		span=self.ask(':SENSe:FREQuency:SPAN?').float()
		mode=self.ask(':INSTrument:SELect?').rstrip()
		if mode=='GPSA':
			if span==0:
				vals.Lists(vals.Numbers(0,self.freq_max)).validate(freq)
			else:
				vals.Lists(vals.Numbers(50,self.freq_max-50)).validate(freq)
		else:
			vals.Lists(vals.Numbers(2.5e3,self.freq_max-2.5e3)).validate(freq)
		input=f'{freq}'
		self._center_frequency(center_frequency)

	def frequency_span(self, freq):
		'''
		Frequency span parameter wrapper
		Args:
			frequency
		'''
		mode=self.ask(':INSTrument:SELect?').rstrip()
		if mode=='GPSA':
			vals.Lists(vals.MultiType(vals.Enum(0), vals.Numbers(100,self.freq_max))).validate(freq)
		else:
			vals.Lists(vals.Numbers(5e3,10e6)).validate(freq)
		input=f'{freq}'
		self._frequency_span(frequency_span)

	def start_frequency(self, freq):
		'''
		Start frequency parameter wrapper
		Args:
			frequency
		'''
		span=self.ask(':SENSe:FREQuency:SPAN?').float()
		mode=self.ask(':INSTrument:SELect?').rstrip()
		if mode=='GPSA':
			if span==0:
				vals.Lists(vals.Numbers(0,self.freq_max)).validate(freq)
			else:
				vals.Lists(vals.Numbers(0,self.freq_max-100)).validate(freq)
		else:
			vals.Lists(vals.Numbers(0,self.freq_max-5e3)).validate(freq)
		input=f'{freq}'
		self._start_frequency(start_frequency)

	def stop_frequency(self, freq):
		'''
		Stop frequency parameter wrapper
		Args:
			frequency
		'''
		span=self.ask(':SENSe:FREQuency:SPAN?').float()
		mode=self.ask(':INSTrument:SELect?').rstrip()
		if mode=='GPSA':
			if span==0:
				vals.Lists(vals.Numbers(0,self.freq_max)).validate(freq)
			else:
				vals.Lists(vals.Numbers(100,self.freq_max)).validate(freq)
		else:
			vals.Lists(vals.Numbers(5e3,self.freq_max)).validate(freq)
		input=f'{freq}'
		self._stop_frequency(stop_frequency)




	def center_step(self, center_step: float=None):
		if center_step==None:
			return self.center_step()
		lower_limit=-self.freq_max
		upper_limit=self.freq_max
		if center_step<lower_limit or center_step>upper_limit:
			raise ValueError('Center step is outside the limit.\n'
							'Must be between minus max frequency and max frequency.\n'
							f'Currently must be between {lower_limit} and {upper_limit}s.\n')

class Harmonic(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('harmonic_count',
							label='average count of harmonic distortion',
							set_cmd=':SENSe:HDISt:AVERage:COUNt {}',
							get_cmd=':SENSe:HDISt:AVERage:COUNt?',
							vals=vals.Ints(1,1000),
							get_parser=int)

		self.add_parameter('harmonic_average',
							label='harmonic distortion average function',
							set_cmd=':SENSe:HDISt:AVERage:STATe {}',
							get_cmd=':SENSe:HDISt:AVERage:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('harmonic_mode',
							label='average mode of harmonic distortion',
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

		self.add_parameter('harmonics_time',
							label='sweep time of harmonic distortion',
							set_cmd=':SENSe:HDISt:TIME {}',
							get_cmd=':SENSe:HDISt:TIME?',
							vals=vals.Numbers(1e-6,6e3),
							unit='s',
							get_parser=float)

class Multi(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('multi_count',
							label='average count of multi-channel power',
							set_cmd=':SENSe:MCHPower:AVERage:COUNt {}',
							get_cmd=':SENSe:MCHPower:AVERage:COUNt?',
							vals=vals.Ints(1,1000),
							get_parser=int)

		self.add_parameter('multi_average',
							label='average function of multi-channel power',
							set_cmd=':SENSe:MCHPower:AVERage:STATe {}',
							get_cmd=':SENSe:MCHPower:AVERage:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('multi_mode',
							label='average mode of multi-channel power',
							set_cmd=':SENSe:MCHPower:AVERage:TCONtrol {}',
							get_cmd=':SENSe:MCHPower:AVERage:TCONtrol?',
							vals=vals.Enum('EXP', 'REP'),
							get_parser=str.rstrip)

class Occupied(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('occupied_count',
							label='average count of occupied bandwidth',
							set_cmd=':SENSe:OBWidth:AVERage:COUNt',
							get_cmd=':SENSe:OBWidth:AVERage:COUNt?',
							vals=vals.Ints(1,1000),
							get_parser=int)

		self.add_parameter('occupied_average',
							label='averaege function of occupied bandwidth',
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
							get_cmd=':SENSe:OBWidth:FREQuency:SPAN?',
							vals=vals.Numbers(100,4.5e9),
							unit='Hz',
							get_parser=float)

		self.add_parameter('occupied_max',
							label='max hold of occupied bandwidth',
							set_cmd=':SENSe:OBWidth:MAXHold:STATe {}',
							get_cmd=':SENSe:OBWidth:MAXHold:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('occupied_percent',
							label='percentage signal power takes up in whole span power',
							set_cmd=':SENSe:OBWidth:PERCent {}',
							get_cmd=':SENSe:OBWidth:PERCent?',
							vals=vals.Numbers(1,99.99),
							unit='%',
							get_parser=float)

class Power(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('RF_attenuation',
							label='attenuation of RF front-end attenuator',
							set_cmd=':SENSe:POWer:RF:ATTenuation {}',
							get_cmd=':SENSe:POWer:RF:ATTenuation?',
							vals=vals.Ints(0,50),
							unit='dB',
							get_parser=int)

		self.add_parameter('RF_auto',
							label='auto setting of input attenuation',
							set_cmd=':SENSe:POWer:RF:ATTenuation:AUTO',
							get_cmd=':SENSe:POWer:RF:ATTenuation:AUTO?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('preamplifier',
							label='preamplifier state',
							set_cmd=':SENSe:POWer:RF:GAIN:STATe {}',
							get_cmd=':SENSe:POWer:RF:GAIN:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('input_max',
							label='maximum power of input mixer',
							set_cmd=':SENSe:POWer:RF:MIXer:RANGe:UPPer {}',
							get_cmd=':SENSe:POWer:RF:MIXer:RANGe:UPPer?',
							vals=vals.Numbers(-50,-10),
							unit='dBm',
							get_parser=float)

class Sig_Capture(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('_FSK2_lower',
							label='lower limit of amplitude of 2FSK',
							set_cmd=':SENSe:SIGCapture:2FSK:AMPDown {}',
							get_cmd=':SENSe:SIGCapture:2FSK:AMPDown?',
							vals=vals.Numbers(-400,320),
							unit='dBm',
							get_parser=float)

		self.add_parameter('_FSK2_upper',
							label='upper limit of amplitude of 2FSK',
							set_cmd=':SENSe:SIGCapture:2FSK:AMPUp {}',
							get_cmd=':SENSe:SIGCapture:2FSK:AMPUp?',
							vals=vals.Numbers(-100,320),
							unit='dBm',
							get_parser=float)

		self.add_parameter('_FSK2_mark1',
							label='frequency value at marker 1',
							set_cmd=':SENSe:SIGCapture:2FSK:MARK1:FREQ {}',
							get_cmd=':SENSe:SIGCapture:2FSK:MARK1:FREQ?',
							vals=vals.Numbers(),
							unit='Hz',
							get_parser=float)

		self.add_parameter('mark1_state',
							label='state of marker 1',
							set_cmd=':SENSe:SIGCapture:2FSK:MARK1:SWitch:STATe {}',
							get_cmd=':SENSe:SIGCapture:2FSK:MARK1:SWitch:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('_FSK2_mark2',
							label='frequency value at marker 2',
							set_cmd=':SENSe:SIGCapture:2FSK:MARK2:FREQ {}',
							get_cmd=':SENSe:SIGCapture:2FSK:MARK2:FREQ?',
							vals=vals.Numbers(),
							unit='Hz',
							get_parser=float)

		self.add_parameter('mark2_state',
							label='state of marker 2',
							set_cmd=':SENSe:SIGCapture:2FSK:MARK2:SWitch:STATe {}',
							get_cmd=':SENSe:SIGCapture:2FSK:MARK2:SWitch:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('FSK2_max',
							label='max hold function of 2FSK',
							set_cmd=':SENSe:SIGCapture:2FSK:MAXHold:STATe {}',
							get_cmd=':SENSe:SIGCapture:2FSK:MAXHold:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('FSK2_peakamp',
							label='query amplitude of nth peak in SSC measurement',
							get_cmd=':SENSe:SIGCapture:2FSK:PEAKAmp? {}',
							vals=vals.Ints(1,6),
							get_parser=float)

		self.add_parameter('FSK2_peakfreq',
							label='query frequency of nth peak in SSC function',
							get_cmd=':SENSe:SIGCapture:2FSK:PEAKFreq? {}',
							vals=vals.Ints(1,6),
							get_parser=float)

		self.add_parameter('FSK2_fail',
							label='query result of pass/fail function',
							get_cmd=':SENSe:SIGCapture:2FSK:PF?',
							get_parser=str.rstrip)

		self.add_parameter('FSK2_pass',
							label='2FSK pass fail function state',
							set_cmd=':SENSe:SIGCapture:2FSK:PFSWitch:STATe {}',
							get_cmd=':SENSe:SIGCapture:2FSK:PFSWitch:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('FSK2_signal',
							label='signal limit for pass/fail test',
							set_cmd=':SENSe:SIGCapture:2FSK:SIGNal {}',
							get_cmd=':SENSe:SIGCapture:2FSK:SIGNal?',
							vals=vals.Enum(0,1,2),
							get_parser=str.rstrip)

	def FSK2_lower(self, FSK2_lower: float=None):
		if FSK2_lower==None:
			return self._FSK2_lower()
		limit=self._FSK2_upper
		if FSK2_lower>limit or FSK2_lower<-400:
			raise ValueError('Amplitude lower limit is outside the limit.\n'
							'Must be between -400dBm and upper limit.\n'
							f'Currently must be less than {limit}s.\n')
		else:
			self._FSK2_lower(FSK2_lower)

	def FSK2_upper(self, FSK2_upper: float=None):
		if FSK2_upper==None:
			return self._FSK2_upper()
		limit=self._FSK2_lower
		if FSK2_upper<limit or FSK2_upper>320:
			raise ValueError('Amplitude upper limit is outside the limit.\n'
							'Must be between lower limit and 400dBm.\n'
							f'Currently must be more than {limit}s.\n')
		else:
			self._FSK2_upper(FSK2_upper)

	def FSK2_mark1(self, FSK2_mark1: float=None):
		if FSK2_mark1==None:
			return self._FSK2_mark1()
		upper_limit=parent.stop_frequency()
		lower_limit=parent.start_frequency()
		if FSK2_mark1<lower_limit or FSK2_mark1>upper_limit:
			raise ValueError('Marker 1 is outside the limit.\n'
							'Must be between start frequency and stop frequency.\n'
							f'Currently must be between {lower_limit} and {upper_limit}s.\n')
		else:
			self._FSK2_mark1(FSK2_mark1)

	def FSK2_mark2(self, FSK2_mark2: float=None):
		if FSK2_mark2==None:
			return self._FSK2_mark2()
		upper_limit=parent.stop_frequency()
		lower_limit=parent.start_frequency()
		if FSK2_mark2<lower_limit or FSK2_mark2>upper_limit:
			raise ValueError('Marker 2 is outside the limit.\n'
							'Must be between start frequency and stop frequency.\n'
							f'Currently must be between {lower_limit} and {upper_limit}s.\n')
		else:
			self._FSK2_mark2(FSK2_mark2)
	
	def reset(self): self.write(':SENSe:SIGCapture:2FSK:RESet')

class Sweep(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('sweep_points',
							label='number of sweep points',
							set_cmd=':SENSe:SWEep:POINts {}',
							get_cmd=':SENSe:SWEep:POINts?',
							vals=vals.Ints(101,10001),
							get_parser=int)

		self.add_parameter('_sweep_time',
							label='sweep time',
							set_cmd=':SENSe:SWEep:TIME {}',
							get_cmd=':SENSe:SWEep:TIME?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('time_auto',
							label='sweep time auto function',
							set_cmd=':SENSe:SWEep:TIME:AUTO {}',
							get_cmd=':SENSe:SWEep:TIME:AUTO?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('sweep_type',
							label='sweep type',
							set_cmd=':SENSe:SWEep:TIME:AUTO:RULes {}',
							get_cmd=':SENSe:SWEep:TIME:AUTO:RULes?',
							vals=vals.Enum('NORM', 'ACC'),
							get_parser=str.rstrip)

	def sweep_time(self, sweep_time: float=None):
		if sweep_time==None:
			return self._sweep_time()
		if parent.frequency_span()==0:
			upper_limit=6000
			lower_limit=1e-6
		else:
			upper_limit=4000
			lower_limit=1e-3
		if sweep_time<lower_limit or sweep_time>upper_limit:
			raise ValueError('Sweep time is outside the limit.\n'
							'Must be between lower limit and upper limit.\n'
							f'Currently must be between {lower_limit} and {upper_limit}s.\n')
		else:
			self._sweep_time(sweep_time)

class TOI(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('TOI_count',
							label='average count of TOI measurement',
							set_cmd=':SENSe:TOI:AVERage:COUNt {}',
							get_cmd=':SENSe:TOI:AVERage:COUNt?',
							vals=vals.Ints(1,1000),
							get_parser=int)

		self.add_parameter('TOI_average',
							label='average function of TOI measurement',
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
							vals=vals.Numbers(100,4.5e9),
							unit='Hz',
							get_parser=float)

class T_Power(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('Tpower_count',
							label='average count of T-power measurement',
							set_cmd=':SENSe:TPOWer:AVERage:COUNt {}',
							get_cmd=':SENSe:TPOWer:AVERage:COUNt?',
							vals=vals.Ints(1,1000),
							get_parser=int)

		self.add_parameter('Tpower_average',
							label='average function of T-power measurement',
							set_cmd=':SENSe:TPOWer:AVERage:STATe {}',
							get_cmd=':SENSe:TPOWer:AVERage:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('Tpower_mode',
							label='average mode of T-power measurement',
							set_cmd=':SENSe:TPOWer:AVERage:TCONtrol {}',
							get_cmd=':SENSe:TPOWer:AVERage:TCONtrol?',
							vals=vals.Enum('EXP', 'REP'),
							get_parser=str.rstrip)

		self.add_parameter('_Tpower_limit',
							label='start line for T-power measurement',
							set_cmd=':SENSe:TPOWer:LLIMit {}',
							get_cmd=':SENSe:TPOWer:LLIMit?',
							vals=vals.Numbers(0e-6),
							unit='s',
							get_parser=float)
						
		self.add_parameter('Tpower_type',
							label='power type for T-power measurement',
							set_cmd=':SENSe:TPOWer:MODE {}',
							get_cmd=':SENSe:TPOWer:MODE?',
							vals=vals.Enum('AVER', 'PEAK', 'RMS'),
							get_parser=str.rstrip)

		self.add_parameter('_Tpower_stop',
							label='stop line for T-power measurement',
							set_cmd=':SENSe:TPOWer:RLIMit {}',
							get_cmd=':SENSe:TPOWer:RLIMit?',
							vals=vals.Numbers(),
							unit='s',
							get_parser=float)

	def Tpower_limit(self, Tpower_limit: float=None):
		if Tpower_limit==None:
			return self._Tpower_limit()
		limit=self._Tpower_stop
		if Tpower_limit<0e-6 or Tpower_limit>limit:
			raise ValueError('T-power start is outside the limit.\n'
							'Must be between 0e-6 and the stop line.\n'
							f'Currently must be less than {limit}s.\n')
		else:
			self._Tpower_limit(Tpower_limit)

	def Tpower_stop(self, Tpower_stop: float=None):
		if Tpower_stop==None:
			return self._Tpower_stop()
		lower_limit=self._Tpower_limimt
		upper_limit=parent.harmonics_time()
		if Tpower_limit<lower_limit or Tpower_limit>upper_limit:
			raise ValueError('T-power stop is outside the limit.\n'
							'Must be between start line and the sweep time.\n'
							f'Currently must be between {lower_limit} and {upper_limit}s.\n')
		else:
			self._Tpower_stop(Tpower_stop)

class Source(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('offset',
							label='offset of output amplitude of tracking generator',
							set_cmd=':SOURce:CORRection:OFFSet {}',
							get_cmd=':SOURce:CORRection:OFFSet?',
							vals=vals.Numbers(-200,200),
							unit='dB',
							get_parser=float)

		self.add_parameter('output_amplitude',
							label='output amplitude of tracking generator',
							set_cmd=':SOURce:EXTernal:POWer:LEVel:IMMediate:AMPLitude {}',
							get_cmd=':SOURce:EXTernal:POWer:LEVel:IMMediate:AMPLitude?',
							vals=vals.Numbers(-40,0),
							unit='dBm',
							get_parser=float)

		self.add_parameter('reference_trace',
							label='reference trace state',
							set_cmd=':SOURce:TRACe:REFerence:STATe {}',
							get_cmd=':SOURce:TRACe:REFerence:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

	def store(self): self.write(':SOURce:TRACe:STORref')

class Status(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('condition',
							label='query condition register of operation status register',
							get_cmd=':STATus:OPERation:CONDition?',
							get_parser=int)

		self.add_parameter('operation',
							label='enable register of operation status register',
							set_cmd=':STATus:OPERation:ENABle {}',
							get_cmd=':STATus:OPERation:ENABle?',
							vals=vals.Ints(0,32767),
							get_parser=int)

		self.add_parameter('event',
							label='query event register of operation status register',
							get_cmd=':STATus:OPERation:EVENt?',
							get_parser=int)

		self.add_parameter('questionable_condition',
							label='query condition register of questionable status register',
							set_cmd=':STATus:QUEStionable:ENABle {}',
							get_cmd=':STATus:QUEStionable:ENABle?',
							vals=vals.Ints(0,32767),
							get_parser=int)

		self.add_parameter('questionable_event',
							label='query event register of questionable status register',
							get_cmd=':STATus:QUEStionable:EVENt?',
							get_parser=int)		
 
	def preset(self): self.write(':STATus:PRESet')

class System(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('beeper',
							label='beeper status',
							set_cmd=':SYSTem:BEEPer:STATe {}',
							get_cmd=':SYSTem:BEEPer:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('auto_IP',
							label='auto IP setting mode',
							set_cmd=':SYSTem:COMMunicate:LAN:SELF:AUToip:STATe {}',
							get_cmd=':SYSTem:COMMunicate:LAN:SELF:AUToip:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('DHCP',
							label='DHCP configuration mode',
							set_cmd=':SYSTem:COMMunicate:LAN:SELF:DHCP:STATe {}',
							get_cmd=':SYSTem:COMMunicate:LAN:SELF:DHCP:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('IP_address',
							label='IP address',
							set_cmd=':SYSTem:COMMunicate:LAN:SELF:IP:ADDRess {}',
							get_cmd=':SYSTem:COMMunicate:LAN:SELF:IP:ADDRess?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('DNS',
							label='mode to obtain DNS',
							set_cmd=':SYSTem:COMMunicate:LAN:SELF:IP:DNS:AUTO:STATe {}',
							get_cmd=':SYSTem:COMMunicate:LAN:SELF:IP:DNS:AUTO:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('backup_address',
							label='DNS backup address',
							set_cmd=':SYSTem:COMMunicate:LAN:SELF:IP:DNSBack {}',
							get_cmd=':SYSTem:COMMunicate:LAN:SELF:IP:DNSBack?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('DNS_preferred',
							label='preferred address for DNS',
							set_cmd=':SYSTem:COMMunicate:LAN:SELF:IP:DNSPreferred {}',
							get_cmd=':SYSTem:COMMunicate:LAN:SELF:IP:DNSPreferred?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('DNS_server',
							label='preferred address for DNS',
							set_cmd=':SYSTem:COMMunicate:LAN:SELF:IP:DNSServer {}',
							get_cmd=':SYSTem:COMMunicate:LAN:SELF:IP:DNSServer?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('gateway',
							label='default gateway',
							set_cmd=':SYSTem:COMMunicate:LAN:SELF:IP:GATeway {}',
							get_cmd=':SYSTem:COMMunicate:LAN:SELF:IP:GATeway?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('subnet_mask',
							label='subnet mask',
							set_cmd=':SYSTem:COMMunicate:LAN:SELF:IP:SUBMask {}',
							get_cmd=':SYSTem:COMMunicate:LAN:SELF:IP:SUBMask?',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('manual_IP',
							label='manual IP setting mode',
							set_cmd=':SYSTem:COMMunicate:LAN:SELF:MANuip:STATe {}',
							get_cmd=':SYSTem:COMMunicate:LAN:SELF:MANuip:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('network_state',
							label='state of network information sending',
							set_cmd=':SYSTem:COMMunicate:LAN:SELF:MDNS:STATe {}',
							get_cmd=':SYSTem:COMMunicate:LAN:SELF:MDNS:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('information',
							label='query system information of spectrum analyzer',
							get_cmd=':SYSTem:CONFigure:INFormation?',
							get_parser=str.rstrip)

		self.add_parameter('_date',
							label='date of instrument',
							set_cmd=':SYSTem:DATE {}',
							get_cmd=':SYSTem:DATE?',
							get_parser=str.rstrip)

		self.add_parameter('power',
							label='power switc on front panel setting',
							set_cmd=':SYSTem:FSWitch:STATe {}',
							get_cmd=':SYSTem:FSWitch:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)
					
		self.add_parameter('language',
							label='language of instrument',
							set_cmd=':SYSTem:LANGuage {}',
							get_cmd=':SYSTem:LANGuage?',
							vals=vals.Enum('ENGL', 'CHIN'),
							get_parser=str.rstrip)

		self.add_parameter('_key',
							label='installs and activates specified options',
							set_cmd=':SYSTem:LKEY {}')

		self.add_parameter('option',
							label='query option activation',
							get_cmd=':SYSTem:OPTion:STATe? {}',
							vals=vals.Strings(),
							get_parser=str.rstrip)

		self.add_parameter('power_on',
							label='setting type instrument recalls at power on',
							set_cmd=':SYSTem:PON:TYPE {}',
							get_cmd=':SYSTem:PON:TYPE?',
							vals=vals.Enum('PRES', 'LAST'),
							get_parser=str.rstrip)

		self.add_parameter('save_preset',
							label='saves specified user setting',
							set_cmd=':SYSTem:PRESet:SAVE {}',
							vals=vals.Enum('USER1', 'USER2', 'USER3', 'USER4', 'USER5', 'USER6'))

		self.add_parameter('preset_type',
							label='preset type of system',
							set_cmd=':SYSTem:PRESet:TYPe {}',
							get_cmd=':SYSTem:PRESet:TYPe?',
							vals=vals.Enum('FACT', 'USER1', 'USER2', 'USER3', 'USER4', 'USER5', 'USER6'),
							get_parser=str.rstrip)

		self.add_parameter('SCPI_display',
							label='SCPI display status',
							set_cmd=':SYSTem:SCPI:DISPlay {}',
							get_cmd=':SYSTem:SCPI:DISPlay?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('show',
							label='system_related_information',
							set_cmd=':SYSTem:SHOW {}',
							get_cmd=':SYSTem:SHOW?',
							vals=vals.Enum('OFF', 'SYST', 'OPT', 'LIC'),
							get_parser=str.rstrip)

		self.add_parameter('_time',
							label='system time of instrument',
							set_cmd=':SYSTem:TIME {}',
							get_cmd=':SYSTem:TIME?',
							get_parser=str.rstrip)

	def date(self, year, month, day):
		'''
		Date parameter wrapper
		Args:
			year
			month
			day
		'''
		vals.Ints(2000,2099).validate(year)
		vals.Ints(1,12).validate(month)
		vals.Ints(1,31).validate(day)
		input=f'{year},{month},{day}'
		self._date(input)

	def key(self, option, licence):
		'''
		Key parameter wrapper
		Args:
			option
			license
		'''
		vals.Strings().validate(option)
		vals.Strings().validate(licence)
		input=f'{option},{licence}'
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
		input=f'{hour},{minute},{second}'
		self._time(input)
	
	
	
	def apply(self): self.write(':SYSTem:COMMunicate:LAN:SELF:APPLy')
	def LAN_reset(self): self.write(':SYSTem:COMMunicate:LAN:SELF:RESet')
	def preset(self): self.write(':SYSTem:PRESet')
	def user_save(self): self.write(':SYSTem:PRESet:USER:SAVE')
		
class Trace(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, tracenum):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('_data',
							label=f'Trace {tracenum} data',
							set_cmd=f':TRACe:DATA TRACE{tracenum},{{}}',
							get_cmd=f':TRACe:DATA? TRACE{tracenum}',
							get_parser=_data_parser)

		self.add_parameter('math_A',
							label='Op1 in trace math operation formula',
							set_cmd=':TRACe:MATH:A {}',
							get_cmd=':TRACe:MATH:A?',
							vals=vals.Enum('T1', 'T2', 'T3', 'T4', 'T5', 'T6'),
							get_parser=str.rstrip)

		self.add_parameter('math_B',
							label='Op2 in trace math operation formula',
							set_cmd=':TRACe:MATH:B {}',
							get_cmd=':TRACe:MATH:B?',
							vals=vals.Enum('T1', 'T2', 'T3', 'T4', 'T5', 'T6'),
							get_parser=str.rstrip)

		self.add_parameter('log_offset',
							label='log offset in trace math operation formula',
							set_cmd=':TRACe:MATH:CONSt {}',
							get_cmd=':TRACe:MATH:CONSt?',
							vals=vals.Numbers(-100,100),
							unit='dB',
							get_parser=float)

		self.add_parameter('peak',
							label='query frequencies and amplituydes of peaks in peak table',
							get_cmd=':TRACe:MATH:PEAK:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('peak_points',
							label='query number of peaks in peak table',
							get_cmd=':TRACe:MATH:PEAK:POINts?',
							get_parser=int)

		self.add_parameter('log_reference',
							label='log reference in trace math operation formula',
							set_cmd=':TRACe:MATH:REFerence {}',
							get_cmd=':TRACe:MATH:REFerence?',
							vals=vals.Numbers(-170,30),
							unit='dBm',
							get_parser=float)

		self.add_parameter('math_state',
							label='math operation status',
							set_cmd=':TRACe:MATH:STATe {}',
							get_cmd=':TRACe:MATH:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('math_type',
							label='trace operation type',
							set_cmd=':TRACe:MATH:TYPE {}',
							get_cmd=':TRACe:MATH:TYPE?',
							vals=vals.Enum('A+B', 'A-B', 'A+CONST', 'A-CONST', 'A-B+REF'),
							get_parser=str.rstrip)

		self.add_parameter('display',
							label=f'Trace {tracenum} display of specified trace status',
							set_cmd=f':TRACe{tracenum}:DISPlay:STATe {{}}',
							get_cmd=f':TRACe{tracenum}:DISPlay:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('mode',
							label=f'Trace {tracenum} type of specified trace',
							set_cmd=f':TRACe{tracenum}:MODE {{}}',
							get_cmd=f':TRACe{tracenum}:MODE?',
							vals=vals.Enum('WRIT', 'AVER', 'MAXH', 'MINH'),
							get_parser=str.rstrip)

		self.add_parameter('type',
							label=f'Trace {tracenum} type of specified trace',
							set_cmd=f':TRACe{tracenum}:TYPE {{}}',
							get_cmd=f':TRACe{tracenum}:TYPE?',
							vals=vals.Enum('WRIT', 'AVER', 'MAXH', 'MINH'),
							get_parser=str.rstrip)

		self.add_parameter('update',
							label=f'Trace {tracenum} update of specified trace status',
							set_cmd=f':TRACe{tracenum}:UPDate:STATe {{}}',
							get_cmd=f':TRACe{tracenum}:UPDate:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('sort_order',
							label='sorting order of data in peak table',
							set_cmd=':TRACe:MATH:PEAK:SORT {}',
							get_cmd=':TRACe:MATH:PEAK:SORT?',
							vals=vals.Enum('FREQ', 'AMPL'),
							get_parser=str.rstrip)

		self.add_parameter('peak_criteria',
							label='peak criteria displayed peak must meet',
							set_cmd=':TRACe:MATH:PEAK:THReshold {}',
							get_cmd=':TRACe:MATH:PEAK:THReshold?',
							vals=vals.Enum('ALL', 'GTDL', 'LTDL', 'NORM', 'DLM', 'DLL'),
							get_parser=str.rstrip)

		self.add_parameter('peak_table',
							label='peak table status',
							set_cmd=':TRACe:MATH:PEAK:TABLe:STATe {}',
							get_cmd=':TRACe:MATH:PEAK:TABLe:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('cache',
							label=f'Trace {tracenum} query trace data in cache area',
							get_cmd=f':FETCh:SANalyzer{tracenum}?',
							get_parser=str.rstrip)

		self.add_parameter('read',
							label=f'Trace {tracenum} query trace data in buffer',
							get_cmd=f':READ:SANalyzer{tracenum}?',
							get_parser=str.rstrip)

		self.add_parameter('coupling_function',
							label=f'Trace {tracenum} coupling functions between limit line data and reference level',
							set_cmd=f':CALCulate:LLINe{tracenum}:AMPLitude:CMODe:RELative {{}}',
							get_cmd=f':CALCulate:LLINe{tracenum}:AMPLitude:CMODe:RELative?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('build',
							label=f'Trace {tracenum} builds limit line from trace',
							set_cmd=f':CALCulate:LLINe{tracenum}:BUILd {{}}',
							vals=vals.Enum('TRACE1', 'TRACE2', 'TRACE3', 'TRACE4', 'TRACE5', 'TRACE6'))

		self.add_parameter('copy',
							label=f'Trace {tracenum} copies selected limit line to current',
							set_cmd=f':CALCulate:LLINe{tracenum}:COPY {{}}',
							vals=vals.Enum('LLINE1', 'LLINE2', 'LLINE3', 'LLINE4', 'LLINE5', 'LLINE6'))

		self.add_parameter('_datal',
							label=f'Trace {tracenum} edits one limit line and marks with n',
							set_cmd=f':CALCulate:LLINe{tracenum}:DATA {{}}',
							get_cmd=f':CALCulate:LLINe{tracenum}:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('limit_state',
							label=f'Trace {tracenum} seleceted limit line state',
							set_cmd=f':CALCulate:LLINe{tracenum}:DISPlay',
							get_cmd=f':CALCulate:LLINe{tracenum}:DISPlay?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('limit_fail',
							label=f'query measurement results of selected limit line and its trace',
							get_cmd=f'Trace {tracenum} query result of limit line and associated trace',
							get_parser=str.rstrip)

		self.add_parameter('coupling_state',
							label=f'Trace {tracenum} coupling function status',
							set_cmd=f':CALCulate:LLINe{tracenum}:FREQuency:CMODe:RELative {{}}',
							get_cmd=f':CALCulate:LLINe{tracenum}:FREQuency:CMODe:RELative?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('margin',
							label=f'Trace {tracenum} margin for limit line',
							set_cmd=f':CALCulate:LLINe{tracenum}:MARGin {{}}',
							get_cmd=f':CALCulate:LLINe{tracenum}:MARGin?',
							vals=vals.Numbers(-40,0),
							unit='dB',
							get_parser=float)

		self.add_parameter('margin_state',
							label=f'Trace {tracenum} margin status',
							set_cmd=f':CALCulate:LLINe{tracenum}:MARGin:STATe {{}}',
							get_cmd=f':CALCulate:LLINe{tracenum}:MARGin:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('trace_test',
							label=f'Trace {tracenum} trace to be tested against limit line',
							set_cmd=f':CALCulate:LLINe{tracenum}:TRACe {{}}',
							get_cmd=f':CALCulate:LLINe{tracenum}:TRACe?',
							vals=vals.Enum(1,2,3,4,5,6),
							get_parser=str.rstrip)

		self.add_parameter('limit_type',
							label=f'Trace {tracenum} type of specified limit line',
							set_cmd=f':CALCulate:LLINe{tracenum}:TYPE {{}}',
							get_cmd=f':CALCulate:LLINe{tracenum}:TYPE?',
							vals=vals.Enum('UPP', 'LOW'),
							get_parser=str.rstrip)

	def datal(self, freq, ampl, connect):
		'''
		Data parameter wrapper
		Args:
			frequency
			amplitude
			connect
		'''
		vals.Numbers(0,self.freq_max).validate(freq)
		vals.Numbers(-1000,1000).validate(ampl)
		vals=vals.Enum(0,1).validate(connect)
		input=f'{freq},{amp},{connect}'
		self._datal(input)
	
	def clear_all(self): self.write(':TRACe:CLEar:ALL')
	def reset_all(self): self.write(':TRACe:PRESet:ALL')
	
	def data(self, data:list=None):
		if data==None:
			return self._data()
		else:
			#TODO: fix for uploading data
			pass

class Trigger(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name, channum):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('analyzer_time',
							label='time analyzer waits for trigger to be initiated automatically',
							set_cmd=':TRIGger:SEQuence:ATRigger {}',
							get_cmd=':TRIGger:SEQuence:ATRigger?',
							vals=vals.Numbers(1e-3,100),
							unit='s',
							get_parser=float)

		self.add_parameter('auto_state',
							label='auto trigger function',
							set_cmd=':TRIGger:SEQuence:ATRigger:STATe {}',
							get_cmd=':TRIGger:SEQuence:ATRigger:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('delay_time',
							label=f'channel {channum} external trigger delay time',
							set_cmd=f':TRIGger:SEQuence:EXTernal{channum}:DELay {{}}',
							get_cmd=f':TRIGger:SEQuence:EXTernal{channum}:DELay?',
							vals=vals.Numbers(0e-6,500e-3),
							unit='s',
							get_parser=float)

		self.add_parameter('external_delay',
							label=f'channel {channum} external trigger delay function',
							set_cmd=f':TRIGger:SEQuence:EXTernal{channum}:DELay:STATe {{}}',
							get_cmd=f':TRIGger:SEQuence:EXTernal{channum}:DELay:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('external_edge',
							label=f'channel {channum} trigger edge for external trigger',
							set_cmd=f':TRIGger:SEQuence:EXTernal{channum}:SLOPe {{}}',
							get_cmd=f':TRIGger:SEQuence:EXTernal{channum}:SLOPe?',
							vals=vals.Enum('POS', 'NEG'),
							get_parser=str.rstrip)

		self.add_parameter('_acquisition_numbers',
							label='number of times for acquisition after each effective trigger is completed',
							set_cmd=':TRIGger:SEQuence:FMT:APTRigger {}',
							get_cmd=':TRIGger:SEQuence:FMT:APTRigger?',
							vals=vals.Ints(),
							get_parser=int)

		self.add_parameter('FMT_criteria',
							label='trigger criteria for FMT',
							set_cmd=':TRIGger:SEQuence:FMT:CRITeria {}',
							get_cmd=':TRIGger:SEQuence:FMT:CRITeria?',
							vals=vals.Enum('ENT', 'LEAV', 'INS', 'OUTS', 'ELE', 'LENT'),
							get_parser=str.rstrip)

		self.add_parameter('FMT_delay',
							label='delay time for FMT',
							set_cmd=':TRIGger:SEQuence:FMT:DELay {}',
							get_cmd=':TRIGger:SEQuence:FMT:DELay?',
							vals=vals.Numbers(0e-6,500e-3),
							unit='s',
							get_parser=float)

		self.add_parameter('delay_state',
							label='FMT trigger delay function state',
							set_cmd=':TRIGger:SEQuence:FMT:DELay:STATe {}',
							get_cmd=':TRIGger:SEQuence:FMT:DELay:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('mask',
							label='mask used for current trigger',
							set_cmd=':TRIGger:SEQuence:FMT:MASK {}',
							get_cmd=':TRIGger:SEQuence:FMT:MASK?',
							vals=vals.Enum('UPP', 'LOW', 'BOTH'),
							get_parser=str.rstrip)

		self.add_parameter('mask_edit',
							label='mask type current viewed/edited',
							set_cmd=':TRIGger:SEQuence:FMT:MASK:EDIT {}',
							get_cmd=':TRIGger:SEQuence:FMT:MASK:EDIT?',
							vals=vals.Enum('UPP', 'LOW'),
							get_parser=str.rstrip)
						
		self.add_parameter('mask_amplitude',
							label='whether amplitudes of mask points are coupled to reference level of instrument',
							set_cmd=':TRIGger:SEQuence:FMT:MASK:RELative:AMPLitude {}',
							get_cmd=':TRIGger:SEQuence:FMT:MASK:RELative:AMPLitude?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('mask_frequency',
							label='whether frequencies of mask points are coupled to center frequency of instrument',
							set_cmd=':TRIGger:SEQuence:FMT:MASK:RELative:FREQuency {}',
							get_cmd=':TRIGger:SEQuence:FMT:MASK:RELative:FREQuency?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('build',
							label=f'channel {channum} create mask from a trace',
							set_cmd=f':TRIGger:SEQuence:FMT:MASK{channum}:BUILd',
							vals=vals.Enum('TRACE1', 'TRACE2', 'TRACE3', 'TRACE4', 'TRACE5', 'TRACE6'))

		self.add_parameter('_mask_data',
							label=f'channel {channum} mask parameters',
							set_cmd=f':TRIGger:SEQuence:FMT:MASK{channum}:DATA {{}}',
							get_cmd=f':TRIGger:SEQuence:FMT:MASK{channum}:DATA?',
							get_parser=str.rstrip)

		self.add_parameter('_holdoff_time',
							label='trigger holdoff time',
							set_cmd=':TRIGger:SEQuence:HOLDoff {}',
							get_cmd=':TRIGger:SEQuence:HOLDoff?',
							vals=vals.Numbers(),
							get_parser=float)

		self.add_parameter('holdoff',
							label='trigger holdoff function',
							set_cmd=':TRIGger:SEQuence:HOLDoff:STATe {}',
							get_cmd=':TRIGger:SEQuence:HOLDoff:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('source',
							label='trigger source',
							set_cmd=':TRIGger:SEQuence:SOURce {}',
							get_cmd=':TRIGger:SEQuence:SOURce?',
							vals=vals.Enum('EXT1', 'EXT2', 'IMM', 'VID', 'FMT', 'POW'),
							get_parser=str.rstrip)

		self.add_parameter('video_delay',
							label='delay time for video trigger',
							set_cmd=':TRIGger:SEQuence:VIDeo:DELay {}',
							get_cmd=':TRIGger:SEQuence:VIDeo:DELay?',
							vals=vals.Numbers(0e-6,500e-3),
							unit='s',
							get_parser=float)

		self.add_parameter('delay_function',
							label='video trigger delay function',
							set_cmd=':TRIGger:SEQuence:VIDeo:DELay:STATe {}',
							get_cmd=':TRIGger:SEQuence:VIDeo:DELay:STATe?',
							val_mapping={'ON':1,'OFF':0},
							get_parser=str.rstrip)

		self.add_parameter('video_level',
							label='trigger level of video trigger',
							set_cmd=':TRIGger:SEQuence:VIDeo:LEVel {}',
							get_cmd=':TRIGger:SEQuence:VIDeo:LEVel?',
							vals=vals.Numbers(-140,30),
							unit='dBm',
							get_parser=float)

		self.add_parameter('video_polarity',
							label='polarity of video trigger',
							set_cmd=':TRIGger:SEQuence:VIDeo:SLOPe {}',
							get_cmd=':TRIGger:SEQuence:VIDeo:SLOPe?',
							vals=vals.Enum('POS', 'NEG'),
							get_parser=str.rstrip)

		self.add_parameter('mode_2',
							label='interface type of external trigger 2',
							set_cmd=':TRIGger2:MODE {}',
							get_cmd=':TRIGger2:MODE?',
							val_mapping={'OUT':1,'IN':0},
							get_parser=str.rstrip)
	
	def acquisition_numbers(self, num):
		'''
		acquisition numbers parameter wrapper
		Args:
			number
		'''
		config=self.ask(':CONFigure?').rstrip()
		criteria=self.ask(':TRIGger:SEQuence:FMT:CRITeria?').rstrip()
		if criteria=='INS' or criteria=='OUTS':
			vals.Lists(vals.Numbers(1,1)).validate(num)
		if config=='SPEC':
			vals.Lists(vals.Numbers(1,10000)).validate(num)
		if config=='PVT':
			vals.Lists(vals.Numbers(1,5000)).validate(num)
		else:
			raise ValueError('no values')
	
	
	def holdoff_time(self, time):
		'''
		holdoff time parameter wrapper
		Args:
			time
		'''
		mode=self.ask(':INSTrument:SELect?').rstrip()
		if mode=='GPSA':
			vals.Lists(vals.Numbers(100e-6,500e-3)).validate(time)
		else:
			vals.Lists(vals.Numbers(0e-6,10)).validate(time)
		input=f'{time}'
		self._holdoff_time(holdoff_time)
	
	def mask_data(self, freq, ampl):
		'''
		mask data parameter wrapper
		Args:
			frequency
			amplitude
		'''
		vals.Numbers(0,self.freq_max).validate(freq)
		vals.Numbers(-1000,1000).validate(ampl)
		input=f'{freq},{ampl}'
		self._mask_data(mask_data)

	def mask_delete(self): self.write(f':TRIGger:SEQuence:FMT:MASK{channum}:DELete')
	def mask_new(self): self.write(f':TRIGger:SEQuence:FMT:MASK{channum}:NEW')

class Unit(InstrumentChannel):
	def __init__(self, parent: InstrumentChannel, name):
		super().__init__(parent, name)
		self.freq_max=parent.freq_max

		self.add_parameter('power',
							label='unit of y axis',
							set_cmd=':UNIT:POWer {}',
							get_cmd=':UNIT:POWer?',
							vals=vals.Enum('DBM', 'DBMV', 'DBUV', 'V', 'W'),
							get_parser=str.rstrip)		

class Rigol_RSA3000(VisaInstrument):
	'''
	Rigol RSA3000 QCoDes driver
	Structure:
		Instrument-
			-Calculate-
					-Marker
			-Calibration
			-Configure
			-Couple
			-Display
			-Fetch
			-Format
			-Initiate
			-Instrument
			-MassMemory
			-Output
			-Read
			-Sense-
					-Acquistion
					-Adjacent
					-Average
					-Bandwidth
					-CN
					-Demodulation
					-Detector
					-Emission
					-Frequency
					-Harmonic
					-Multi
					-Ocuppied
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

		self.model=self.IDN()['model']
		self.freq_max=float(self.model[5:7])*1e8
		
		calculate_module=Calculate(self, 'calculate')
		self.add_submodule('calculate', calculate_module)

		calibration_module=Calibration(self, 'calibration')
		self.add_submodule('calibration', calibration_module)

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

		initiate_module=Initiate(self, 'initiate')
		self.add_submodule('initiate', initiate_module)

		instrument_module=Instrument(self, 'instrument')
		self.add_submodule('instrument', instrument_module)

		massmemory_module=MassMemory(self, 'massmemory')
		self.add_submodule('massmemory', massmemory_module)

		output_module=Output(self, 'output')
		self.add_submodule('output', output_module)

		read_module=Read(self, 'read')
		self.add_submodule('read', read_module)

		sense_module=Sense(self, 'sense')
		self.add_submodule('sense', sense_module)

		source_module=Source(self, 'source')
		self.add_submodule('source', source_module)

		status_module=Status(self, 'status')
		self.add_submodule('status', status_module)

		system_module=System(self, 'system')
		self.add_submodule('system', system_module)

		for i in range(1,6+1):
			trace_module=Trace(self, f'tr{i}', i)
			self.add_submodule(f'tr{i}', trace_module)

		for i in range(1,2+1):
			trigger_module=Trigger(self, f'ch{i}', i)
			self.add_submodule(f'ch{i}', trigger_module)

		unit_module=Unit(self, 'unit')
		self.add_submodule('unit', unit_module)

		self.add_parameter('ESE',
							label='enable register for standard event status register',
							set_cmd='*ESE {}',
							get_cmd='*ESE?',
							vals=vals.Ints(0,255),
							get_parser=int)

		self.add_parameter('ESR',
							label='queries and clears event register for standard event status',
							get_cmd='*ESR?',
							get_parser=int)

		self.add_parameter('OPC',
							label='OPC',
							set_cmd='*OPC',
							get_cmd='*OPC?',
							get_parser=str.rstrip)

		self.add_parameter('RCL',
							label='recalls selected register',
							set_cmd='*RCL {}',
							vals=vals.Ints(1,16))

		self.add_parameter('SAV',
							label='saves current instrument to selected register',
							set_cmd='*SAV {}',
							vals=vals.Ints(1,16))

		self.add_parameter('SRE',
							label='enable register for the status byte register',
							set_cmd='*SRE {}',
							get_cmd='*SRE?',
							vals=vals.Ints(0,255),
							get_parser=int)

		self.add_parameter('STB',
							label='queries event register for status byte register',
							get_cmd='*STB?',
							get_parser=int)

		self.add_parameter('TST',
							label='queries whether self-check operation is finished',
							get_cmd='*TST?',
							get_parser=str.rstrip)
		
	def Wait(self): self.write('*WAI')
	def Trigger(self): self.write('*TRG')	
	def Reset(self): self.write('*RST')
	def CLS(self): self.write('*CLS')				
