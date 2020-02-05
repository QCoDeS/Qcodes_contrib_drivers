#from unittest import TestCase
#from unittest.mock import patch
import visa
from qcodes.instrument.visa import VisaInstrument
from qcodes.utils.validators import Numbers
#import warnings


class MockVisa(VisaInstrument):
    def __init__(self, *args, **kwargs):
        #print("DBG-Mock:", args, kwargs)
        super().__init__(*args, **kwargs)
        self.add_parameter('state',
                           get_cmd='STAT?', get_parser=float,
                           set_cmd='STAT:{:.3f}',
                           vals=Numbers(-20, 20))

    def set_address(self, address):
        self.visa_handle = MockVisaHandle()


class MockVisaHandle:
    '''
    Simulate the API needed for a visa handle.
    '''
    
    # List of possible commands asked the instrument to give a realistic answer.
    cmddef = {'*IDN?': 'Rohde&Schwarz,SMW200A,1412.0000K02/105578,04.30.005.29 SP2',
              '*OPT?': 'SMW-B13T,SMW-B22,SMW-B120,SMW-K22,SMW-K23',
              
              'STAT?': '0',
              
              'SOUR1:FREQ?': '20000000000.0',
              'SOUR1:POW:POW?': '-145.0',
              'OUTP1:STAT?': '0',
              'SOUR1:FREQ:MODE?': 'CW',
              'SOUR1:FREQ:CENT?': '300000000.0',
              'SOUR1:FREQ:SPAN?': '400000000.0',
              'SOUR1:FREQ:STAR?': '100000000.0',
              'SOUR1:FREQ:STOP?': '500000000.0',
              'SOUR1:FREQ:LOSC:INP:FREQ?': '0',
              'SOUR1:FREQ:LOSC:MODE?': 'INT',
              'SOUR1:FREQ:LOSC:OUTP:FREQ?': '0',
              'SOUR1:FREQ:LOSC:OUTP:STAT?': '0',
              
              'SOUR1:SWE:POW:AMOD?': 'AUTO', # TODO: ist nicht dokumentiert
              'SOUR1:SWE:POW:DWEL?': '0.01',
              'SOUR1:SWE:POW:MODE?': 'AUTO',
              'SOUR1:SWE:POW:POIN?': '21',
              'SOUR1:SWE:POW:STEP?': '1.0',
              'SOUR1:SWE:POW:SHAP?': 'SAWT',
              'SOUR1:SWE:POW:RETR?': '0',
              'SOUR1:SWE:POW:RUNN?': '0',
              'SOUR1:SWE:DWEL?': '0.01',
              'SOUR1:SWE:MODE?': 'AUTO',
              'SOUR1:SWE:POIN?': '401',
              'SOUR1:SWE:SPAC?': 'LIN',
              'SOUR1:SWE:SHAP?': 'SAWT',
              'SOUR1:SWE:RETR?': '0',
              'SOUR1:SWE:RUNN?': '0',
              'SOUR1:SWE:STEP:LOG?': '1.0',
              'SOUR1:SWE:STEP?': '1000000.0',
              
              'SOUR:LFO1:BAND?': 'BW10',
              'SOUR:LFO1:STAT?': '0',
              'SOUR:LFO1:OFFS?': '0',
              'SOUR:LFO1:SOUR?': 'LF1',
              'SOUR:LFO1:VOLT?': '1.0',
              'SOUR:LFO1:PER?': '0.001',
              
              'SOUR1:LFO1:FREQ?': '1000.0',
              'SOUR1:LFO:FREQ:MAN?': '1000.0',
              'SOUR1:LFO:FREQ:STAR?': '1000.0',
              'SOUR1:LFO:FREQ:STOP?': '50000.0',
              'SOUR1:LFO:FREQ:MODE?': 'CW',
              
              'SOUR:LFO2:BAND?': 'BW10',
              'SOUR:LFO2:STAT?': '0',
              'SOUR:LFO2:OFFS?': '0',
              'SOUR:LFO2:SOUR?': 'EXT1',
              'SOUR:LFO2:VOLT?': '1.0',
              
              'SOUR1:LFO:SWE:DWEL?': '0.01',
              'SOUR1:LFO:SWE:MODE?': 'AUTO',
              'SOUR1:LFO:SWE:POIN?': '50',
              'SOUR1:LFO:SWE:SHAP?': 'SAWT',
              'SOUR1:LFO:SWE:RETR?': '0',
              'SOUR1:LFO:SWE:RUNN?': '0',
              'SOUR1:LFO:SWE:SPAC?': 'LIN',
              'SOUR1:LFO:SWE:STEP:LOG?': '1.0',
              'SOUR1:LFO:SWE:STEP?': '1000.0',
              
              'SOUR1:AM1:STAT?': '0',
              'SOUR1:AM1:SOUR?': 'LF1',
              'SOUR1:AM1:DEPT?': '50.0',
              'SOUR1:AM:RAT?': '50.0', # Ratio Path2 to Path1
              'SOUR1:AM:SENS?': '50.0', # Sensitivity for EXT
              
              'SOUR1:AM2:STAT?': '0',
              'SOUR1:AM2:SOUR?': 'LF1',
              'SOUR1:AM2:DEPT?': '50.0',        
              
              'SOUR1:FM1:STAT?': '0',
              'SOUR1:FM1:DEV?': '1000.0',
              'SOUR1:FM1:SOUR?': 'LF1',
              'SOUR1:FM:RAT?': '100.0',
              'SOUR1:FM:MODE?': 'NORM',
              'SOUR1:FM:SENS?': '1000.0',
              
              'SOUR1:FM2:STAT?': '0',
              'SOUR1:FM2:DEV?': '1000.0',
              'SOUR1:FM2:SOUR?': 'EXT1',
              
              'SOUR1:PM1:STAT?': '0',
              'SOUR:PM1:DEV?': '1',
              'SOUR1:PM1:SOUR?': 'LF1',
              'SOUR1:PM:MODE?': 'HBAN',
              'SOUR1:PM:RAT?': '100',
              'SOUR1:PM:SENS?': '1',
              
              'SOUR1:PM2:STAT?': '0',
              'SOUR:PM2:DEV?': '1',
              'SOUR1:PM2:SOUR?': 'EXT1',
              'SOUR1:PM:MODE?': 'HBAN',
              
              'SOUR1:PULM:MODE?': '0',      # Diese Werte werden
              'SOUR1:PULM:DOUB:DEL?': '0',  # beim ReadAll nicht
              'SOUR1:PULM:DOUB:WID?': '0',  # angezeigt. Sollten
              'SOUR1:PULM:TRIG:MODE?': '0', # diese nur intern
              'SOUR1:PULM:PER?': '2.0',     # Verwendung finden?
              'SOUR1:PULM:WIDT?': '0',      # TODO
              'SOUR1:PULM:DEL?': '0',       #
              'SOUR1:PULM:STAT?': '0',
              'SOUR1:PULM:SOUR?': 'EXT',
              'SOUR1:PULM:TTYP?': 'FAST',
              'SOUR1:PULM:OUTP:VID:POL?': 'NORM',
              'SOUR1:PULM:POL?': 'NORM',
              'SOUR1:PULM:IMP?': 'G1K',
              'SOUR1:PULM:TRIG:EXT:IMP?': 'G50',
              
              'SOUR1:PGEN:OUTP:POL?': 'NORM',
              'SOUR1:PGEN:OUTP:STAT': 'OFF',
              'SOUR1:PGEN:STAT': 'OFF',
              
              'SOUR1:IQ:SOUR?': 'BAS',
              'SOUR1:IQ:STAT?': '0',
              'SOUR1:IQ:GAIN?': 'DB4',
              'SOUR1:IQ:CRES?': '0.0',
              'SOUR1:IQ:SWAP:STAT?': '0',
              'SOUR1:IQ:WBST?': '0',
              
              'SOUR1:IQ:OUTP:ANAL:STAT?': '0',
              'SOUR1:IQ:OUTP:ANAL:TYPE?': 'SING',
              'SOUR1:IQ:OUTP:ANAL:MODE?': 'FIX',
              'SOUR1:IQ:OUTP:LEV?': '1.0',
              'SOUR1:IQ:OUTP:ANAL:BIAS:COUP:STAT?': '0',
              'SOUR1:IQ:OUTP:ANAL:BIAS:I?': '0',
              'SOUR1:IQ:OUTP:ANAL:BIAS:Q?': '0',
              'SOUR1:IQ:OUTP:ANAL:OFFS:I?': '0',
              'SOUR1:IQ:OUTP:ANAL:OFFS:Q?': '0',

              'SOUR2:IQ:OUTP:ANAL:STAT?': '0',
              'SOUR2:IQ:OUTP:ANAL:TYPE?': 'SING',
              'SOUR2:IQ:OUTP:ANAL:MODE?': 'FIX',
              'SOUR2:IQ:OUTP:LEV?': '1.0',
              'SOUR2:IQ:OUTP:ANAL:BIAS:COUP:STAT?': '0',
              'SOUR2:IQ:OUTP:ANAL:BIAS:I?': '0',
              'SOUR2:IQ:OUTP:ANAL:BIAS:Q?': '0',
              'SOUR2:IQ:OUTP:ANAL:OFFS:I?': '0',
              'SOUR2:IQ:OUTP:ANAL:OFFS:Q?': '0'
              }
    
    def __init__(self):
        #print("DBG-Mock: MockVisaHandle init")
        self.state = 0
        self.closed = False

    def clear(self):
        #print("DBG-Mock: MockVisaHandle clear")
        self.state = 0

    def close(self):
        # make it an error to ask or write after close
        #print("DBG-Mock: MockVisaHandle close")
        self.closed = True

    def write(self, cmd):
        print("DBG-Mock: MockVisaHandle write", cmd)
        if self.closed:
            raise RuntimeError("Trying to write to a closed instrument")
        try:
            num = float(cmd.split(':')[-1])
        except:
            num = 1
        self.state = num

        if num < 0:
            raise ValueError('be more positive!')

        if num == 0:
            ret_code = visa.constants.VI_ERROR_TMO
        else:
            ret_code = 0

        return len(cmd), ret_code

    def ask(self, cmd):
        print("DBG-Mock: MockVisaHandle ask", cmd)
        if self.closed:
            raise RuntimeError("Trying to ask a closed instrument")
        if self.state > 10:
            raise ValueError("I'm out of fingers")
        return self.state

    def query(self, cmd):
        #print("DBG-Mock: MockVisaHandle query", cmd)
        if cmd in self.cmddef:
            return self.cmddef[cmd]
        if self.state > 10:
            raise ValueError("I'm out of fingers")
        return self.state


"""

Werte vom Gerät am 15.08.2019 gegen 09:40

==========  Version informations  ==========
ID: Rohde&Schwarz,SMW200A,1412.0000K02/105578,04.30.005.29 SP2
Options: ['SMW-B13T', 'SMW-B22', 'SMW-B120', 'SMW-K22']

==========  Main Device  ==========
IDN  |  IDN :  {'vendor': 'Rohde&Schwarz', 'model': 'SMW200A', 'serial': '1412.0000K02/105578', 'firmware': '04.30.005.29 SP2'} 
timeout  |  timeout :  5.0 s

==========  rfoutput1  ==========
frequency  |  Frequency :  20000000000.0 Hz
level  |  Level :  -145.0 dBm
state  |  State :  OFF 
mode  |  Mode :  CW 
DOC:  FIX = fixed frequency mode (CW is a synonym)
 SWE = set sweep mode (use start/stop/center/span)
 LIST = use a special loadable list of frequencies (nyi here) 

sweep_center  |  Center frequency of the sweep :  300000000.0 Hz
DOC:  Use sweep_center and sweep_span or
 use sweep_start and sweep_stop
 to define the sweep range. 

sweep_span  |  Span of frequency sweep range :  400000000.0 Hz
DOC:  Use sweep_center and sweep_span or
 use sweep_start and sweep_stop
 to define the sweep range. 

sweep_start  |  Start frequency of the sweep :  100000000.0 Hz
DOC:  Use sweep_start and sweep_stop or
 use sweep_center and sweep_span
 to define the sweep range. 

sweep_stop  |  Stop frequency of the sweep :  500000000.0 Hz
DOC:  Use sweep_start and sweep_stop or
 use sweep_center and sweep_span
 to define the sweep range. 

losc_input  |  LOscillator input frequency :  0.0 Hz
losc_mode  |  LOscillator mode :  INT 
DOC:  INT = A&B Internal / Internal (one path instrument) - Uses the internal oscillator signal in both paths.
 EXT = A External & B Internal (one path instrument) - Uses an external signal in path A. B uses its internal signal.
 COUP = A Internal & A->B Coupled - Assigns the internal oscillator signal of path A also to path B.
 ECO = A External & A->B Coupled - Assigns an externally supplied signal to both paths.
 BOFF = A Internal & B RF Off - Uses the internal local oscillator signal of path A, if the selected frequency exceeds the maximum frequency of path B.
 EBOF = A External & B RF Off - Uses the LO IN signal for path A, if the selected RF frequency exceeds the maximum frequency of path B.
 AOFF = A RF Off & B External - Uses the LO IN signal for path B, if the selected RF frequency exceeds the maximum frequency of path A. 

losc_output  |  LOscillator output frequency :  0.0 Hz
losc_state  |  LOscillator state :  OFF 

==========  level_sweep1  ==========
attenuator  |  Power attenuator mode for level sweep :  AUTO 
DOC:  NORM = Performs the level settings in the range of the built-in attenuator.
 HPOW = Performs the level settings in the high level range. 

dwell  |  Dwell time for level sweep :  0.01 s
mode  |  Cycle mode for level sweep :  AUTO 
DOC:  AUTO = Each trigger triggers exactly one complete sweep.
 MAN = You can trigger every step individually with a command.
 STEP = Each trigger triggers one sweep step only. 

points  |  Steps within level sweep range :  21 
log_step  |  logarithmically determined step size for the RF level sweep :  1.0 dB
shape  |  Waveform shape for sweep :  SAWT 
execute  |  Executes one RF level sweep :  None 
retrace  |  Set to start frequency while waiting for trigger   :  0 
running  |  Current sweep state :  0 
reset  |  Reset the sweep :  None 
DOC:  Resets all active sweeps to the starting point. 


==========  freq_sweep1  ==========
dwell  |  Dwell time for frequency sweep :  0.01 s
mode  |  Cycle mode for frequency sweep :  AUTO 
DOC:  AUTO = Each trigger triggers exactly one complete sweep.
 MAN = You can trigger every step individually with a command.
 STEP = Each trigger triggers one sweep step only. 

points  |  Steps within frequency sweep range :  401 
spacing  |  calculationmode of frequency intervals :  LIN 
shape  |  Waveform shape for sweep :  SAWT 
execute  |  Executes one RF frequency sweep :  None 
retrace  |  Set to start frequency while waiting for trigger   :  0 
running  |  Current sweep state :  0 
log_step  |  logarithmically determined step size for the RF freq sweep :  1.0 %
lin_step  |  step size for linear RF freq sweep :  1000000.0 Hz
DOC:  The maximum is the sweep_span of the output channel
 and will be read during the set lin_step command. 

reset  |  Reset the sweep :  None 
DOC:  Resets all active sweeps to the starting point. 


==========  lf1output1  ==========
bandwidth  |  Bandwidth :  BW10 
state  |  State :  OFF 
offset  |  DC offset voltage :  0.0 V
source  |  Source :  LF1 
voltage  |  Output voltage of the LF output :  1.0 V
DOC:  The valid range will be dynamic as shown in the datasheet. 

period  |  Period :  0.001 s
frequency  |  Frequency :  1000.0 Hz
freq_manual  |  Manual frequency set :  1000.0 Hz
freq_min  |  Set minimum for manual frequency :  1000.0 Hz
freq_max  |  Set maximum for manual frequency :  50000.0 Hz
mode  |  Mode :  CW 
DOC:  FIX = fixed frequency mode (CW is a synonym)
 SWE = set sweep mode (use LFOutputSweep class) 


==========  lf1output2  ==========
bandwidth  |  Bandwidth :  BW10 
state  |  State :  OFF 
offset  |  DC offset voltage :  0.0 V
source  |  Source :  EXT1 
voltage  |  Output voltage of the LF output :  1.0 V
DOC:  The valid range will be dynamic as shown in the datasheet. 


==========  lf1sweep  ==========
dwell  |  Dwell time :  0.01 s
mode  |  Cycle mode for level sweep :  AUTO 
DOC:  AUTO = Each trigger triggers exactly one complete sweep.
 MAN = You can trigger every step individually with a command.
 STEP = Each trigger triggers one sweep step only. 

points  |  Steps within level sweep range :  50 
shape  |  Waveform shape for sweep :  SAWT 
execute  |  Executes one RF level sweep :  None 
retrace  |  Set to start frequency while waiting for trigger   :  0 
running  |  Current sweep state :  0 
spacing  |  calculationmode of frequency intervals :  LIN 
log_step  |  logarithmically determined step size for the RF freq sweep :  1.0 %
lin_step  |  step size for linear RF freq sweep :  1000.0 Hz
DOC:  The maximum is the sweep_span of the output channel
 and will be read during the set lin_step command. 


==========  am1_1  ==========
state  |  State :  OFF 
source  |  Source :  LF1 
depth  |  Depth :  50.0 %
deviation_ratio  |  Deviation ratio :  50.0 %
sensitivity  |  Sensitifity :  50.0 %/V

==========  am1_2  ==========
state  |  State :  OFF 
source  |  Source :  LF1 
depth  |  Depth :  50.0 %
deviation_ratio  |  Deviation ratio :  50.0 %
sensitivity  |  Sensitifity :  50.0 %/V

==========  fm1_1  ==========
state  |  State :  OFF 
deviation  |  Deviation :  1000.0 Hz
source  |  Source :  LF1 
deviation_ratio  |  Deviation ratio :  100.0 %
mode  |  Mode :  NORM 
sensitivity  |  Sensitivity :  1000.0 Hz/V

==========  fm1_2  ==========
state  |  State :  OFF 
deviation  |  Deviation :  1000.0 Hz
source  |  Source :  EXT1 
deviation_ratio  |  Deviation ratio :  100.0 %
mode  |  Mode :  NORM 
sensitivity  |  Sensitivity :  1000.0 Hz/V

==========  pm1_1  ==========
state  |  State :  OFF 
deviation  |  Deviation :  1 RAD
source  |  Source :  LF1 
mode  |  Mode :  HBAN 
ratio  |  Ratio :  100 
sensitivity  |  Sensitivity :  1 RAD/V

==========  pm1_2  ==========
state  |  State :  OFF 
deviation  |  Deviation :  1 RAD
source  |  Source :  EXT1 
mode  |  Mode :  HBAN 
ratio  |  Ratio :  100 
sensitivity  |  Sensitivity :  1 RAD/V

==========  pulsemod1  ==========
state  |  State :  OFF 
source  |  Source :  EXT 
transition_type  |  Transition type :  FAST 
video_polarity  |  Video polaraity :  NORM 
polarity  |  Polarity :  NORM 
impedance  |  Impedance :  G1K 
trigger_impedance  |  Trigger impedance :  G50 

==========  iqmod1  ==========
source  |  Source :  BAS 
state  |  State :  OFF 
gain  |  Gain :  DB4 
crest_factor  |  Crest factor :  0.0 dB
swap  |  Swap :  OFF 
wideband  |  Wideband :  OFF 

==========  iqoutput1  ==========
state  |  State :  OFF 
type  |  Type :  SING 
mode  |  Mode :  FIX 
level  |  Level :  1.0 V
coupling  |  Coupling :  OFF 
i_bias  |  I bias :  0.0 V
q_bias  |  Q bias :  0.0 V
i_offset  |  I offset :  0.0 V
q_offset  |  Q offset :  0.0 V

==========  iqoutput2  ==========
state  |  State :  OFF 
type  |  Type :  SING 
mode  |  Mode :  FIX 
level  |  Level :  1.0 V
coupling  |  Coupling :  OFF 
i_bias  |  I bias :  0.0 V
q_bias  |  Q bias :  0.0 V
i_offset  |  I offset :  0.0 V
q_offset  |  Q offset :  0.0 V


"""
