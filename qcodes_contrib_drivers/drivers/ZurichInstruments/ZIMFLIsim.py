# -*- coding: utf-8 -*-
"""
Created on Wed Jun 26 09:51:56 2019

Author: Michael Wagener, ZEA-2, m.wagener@fz-juelich.de

Simulation code for the ZIMFLI driver.
"""

import time


# this factor is used to convert the system time to the device time so that
# the conversion backwards in the driver must not be changed.
fixedClockBase = 60000000


class ZIMFLIsweeper():
    """
    Special class for the Sweeper Simulation. In the ZI software this is a part
    of the ziDAQServer, running on the computer or the device.
    """
    params = {}
    isRunning = False
    startTime = 0
    
# All starts with "sweep/" witch is omitted here!
#Setting/Path        | Type   | Unit    | Description
#device              | string | -       | The device ID to perform the sweep on, e.g., dev123 (compulsory parameter).
#gridnode            | string | Node    | The device parameter (specified by node) to be swept, e.g., "oscs/0/freq".
#start               | double | Many    | The start value of the sweep parameter.
#stop                | double | Many    | The stop value of the sweep parameter.
#samplecount         | uint64 | -       | The number of measurement points to set the sweep on.
#endless             | bool   | -       | Enable Endless mode; run the sweeper continuously.
#remainingtime       | double | Seconds | Read only: Reports the remaining time of the current sweep. A valid number
#                    |        |         | is only displayed once the sweeper has been started. An undefined sweep
#                    |        |         | time is indicated as NAN.
#averaging/sample    | uint64 | Samples | Sets the number of data samples per sweeper parameter point that is considered
#                    |        |         | in the measurement. The maximum of this value and sweep/averaging/tc is taken
#                    |        |         | as the effective calculation time. See Figure 3.13.
#averaging/tc        | double | Seconds | Sets the effective measurement time per sweeper parameter point that is
#                    |        |         | considered in the measurement. The maximum between of this value and
#                    |        |         | sweep/averaging/ sample is taken as the effective calculation time.
#bandwidthcontrol    | uint64 | -       | Specify how the sweeper should specify the bandwidth of each measurement point,
#                    |        |         | Automatic is recommended, in particular for logarithmic sweeps and assures the
#                    |        |         | whole spectrum is covered. 0=Manual (the sweeper module leaves the demodulator
#                    |        |         | bandwidth settings entirely untouched); 1=Fixed (use the value from sweep/bandwidth);
#                    |        |         | 2=Automatic. Note, to use either Fixed or Manual mode, sweep/bandwidth must be set
#                    |        |         | to a value > 0 (even though in manual mode it is ignored).
#bandwidthoverlap    | bool   | -       | If enabled the bandwidth of a sweep point may overlap with the frequency of
#                    |        |         | neighboring sweep points. The effective bandwidth is only limited by the maximal
#                    |        |         | bandwidth setting and omega suppression. As a result, the bandwidth is independent
#                    |        |         | of the number of sweep points. For frequency response analysis bandwidth overlap
#                    |        |         | should be enabled to achieve maximal sweep speed.
#bandwidth           | double | Hz      | Defines the measurement bandwidth when using Fixed bandwidth mode (bandwidthcontrol=1),
#                    |        |         | and corresponds to the noise equivalent power bandwidth (NEP).
#order               | uint64 | -       | Defines the filter roll off to use in Fixed bandwidth mode (bandwidthcontrol=1).
#                    |        |         | Valid values are between 1 (6 dB/octave) and 8 (48 dB/octave).
#maxbandwidth        | double | Hz      | Specifies the maximum bandwidth used when in Auto bandwidth mode (bandwidthcontrol=2).
#                    |        |         | The default is 1.25 MHz.
#omegasuppression    | double | dB      | Damping of omega and 2omega components when in Auto bandwidth mode (bandwidthcontrol=2).
#                    |        |         | Default is 40dB in favor of sweep speed. Use a higher value for strong offset values
#                    |        |         | or 3omega measurement methods.
#loopcount           | uint64 | -       | The number of sweeps to perform.
#phaseunwrap         | bool   | -       | Enable unwrapping of slowly changing phase evolutions around the +/-180 degree boundary.
#sincfilter          | bool   | -       | Enables the sinc filter if the sweep frequency is below 50 Hz. This will improve the
#                    |        |         | sweep speed at low frequencies as omega components do not need to be suppressed by the
#                    |        |         | normal low pass filter.
#scan                | uint64 | -       | Selects the scanning type: 0=Sequential (incremental scanning from start to stop
#                    |        |         | value); 1=Binary (Nonsequential sweep continues increase of resolution over entire
#                    |        |         | range), 2=Bidirectional (Sequential sweep from Start to Stop value and back to Start
#                    |        |         | again), 3=Reverse (reverse sequential scanning from stop to start value).
#settling/time       | double | Seconds | Minimum wait time in seconds between setting the new sweep parameter value and the
#                    |        |         | start of the measurement. The maximum between this value and settling/tc is taken
#                    |        |         | as effective settling time.
#settling/inaccuracy | double | -       | Demodulator filter settling inaccuracy defining the wait time between a sweep
#                    |        |         | parameter change and recording of the next sweep point. The settling time is calculated
#                    |        |         | as the time required to attain the specified remaining proportion [1e-13, 0.1] of an
#                    |        |         | incoming step function. Typical inaccuracy values: 10m for highest sweep speed for
#                    |        |         | large signals, 100u for precise amplitude measurements, 100n for precise noise
#                    |        |         | measurements. Depending on the order of the demodulator filter the settling inaccuracy
#                    |        |         | will define the number of filter time constants the sweeper has to wait. The maximum
#                    |        |         | between this value and the settling time is taken as wait time until the next sweep
#                    |        |         | point is recorded.
#settling/tc         | double | TC      | Minimum wait time in factors of the time constant (TC) between setting the new sweep
#                    |        |         | parameter value and the start of the measurement. This filter settling time is
#                    |        |         | preferably configured via the settling/inaccuracy). The maximum between this value
#                    |        |         | and settling/time is taken as effective settling time.
#xmapping            | uint64 | -       | Selects the spacing of the grid used by sweep/gridnode (the sweep parameter): 0=linear
#                    |        |         | and 1=logarithmic distribution of sweep parameter values.
#historylength       | uint64 | -       | Maximum number of entries stored in the measurement history.
#clearhistory        | bool   | -       | Remove all records from the history list.
#directory           | string | -       | The directory to which sweeper measurements are saved to via save().
#fileformat          | string | -       | The format of the file for saving sweeper measurements. 0=Matlab, 1=CSV.


    def __init__(self):
        #print("DBG: ZIMFLIsweeper(): Init")
        self.params.update( {'device': '?', # The device ID to perform the sweep on
                             'gridnode': ['oscs/0/freq'], # The device parameter (specified by node) to be swept
                             'start': [0],
                             'stop': [0],
                             'samplecount': [0],
                             'endless': [0], # val_mapping={'ON': 1, 'OFF': 0})
                             'remainingtime': [float('nan')], # ReadOnly; NAN=invalid time; during sweep time will be valid
                             'averaging': {'sample': [1], # Ints(1, 2**64-1))
                                           'tc': [0],
                                           'time': [0]},
                             'bandwidthcontrol': [0], #val_mapping={'auto': 2, 'fixed': 1, 'current': 0})
                             'bandwidthoverlap': [0], #val_mapping={'ON': 1, 'OFF': 0})
                             'bandwidth': [0],
                             'order': [1], # vals=vals.Ints(1, 8))
                             'maxbandwidth': [1250000.0], # 1.25MHz
                             'omegasuppression': [40], # dB
                             'loopcount': [0], # vals=vals.Ints(0, 2**64-1))
                             'phaseunwrap': [0], #val_mapping={'ON': 1, 'OFF': 0})
                             'sincfilter': [0], #val_mapping={'ON': 1, 'OFF': 0})
                             'scan': [0], #{'sequential':0, 'binary':1, 'biderectional':2, 'reverse':3}
                             'settling': {'time': [0],
                                          'inaccuracy': [0],
                                          'tc': [0] }, # ReadOnly
                             'xmapping': [0], #val_mapping={'linear': 0, 'logarithmic': 1})
                             'historylength': [0], #vals=vals.Ints(0, 2**64-1))
                             'clearhistory': [0], # val_mapping={'ON': 1, 'OFF': 0})
                             'directory': ['./'],
                             'fileformat': [1],  #val_mapping={'Matlab': 0, 'CSV': 1})
                             'awgcontrol': [0],
                             'save': {'csvlocale': ['C'],
                                      'csvseparator': [';'],
                                      'directory': ['C:\\Users\\lablocal\\Documents\\Zurich Instruments\\LabOne\\WebServer'],
                                      'fileformat': [0],
                                      'filename': ['sweep'],
                                      'save': [0],
                                      'saveonread': [0] }
                             } )

    def set( self, topic:str, value ) -> None:
        if topic.startswith('sweep/'):
            topic = topic[6:]
        print("DBG: ZIMFLIsweeper(): Set ", topic, "=", value )
        t = topic.split("/")
        if len(t) == 1:
            self.params.update( {topic: [value]} )
        elif len(t) == 2:
            tmp = self.params[t[0]]
            tmp.update( {t[1]: [value]} )
            self.params.update( {t[0]: tmp} )
            if topic == 'settling/time':
                tmp = self.params[t[0]]
                tmp.update( {'tc': [value/11.0]} )
                self.params.update( {t[0]: tmp} )
                #print("DBG:                  Set  settling/tc =", value/11.0 )
        else:
            raise RuntimeError("More than 2 depth in nested dict")
        
    def get( self, setting:str ) -> dict:
        #print("DBG: ZIMFLIsweeper(): get ", setting )
        return self.params # dict!
    
    def clear(self):
        pass

    def subscribe( self, path:str ) -> None:
        print("SIM: ZIMFLIsweeper(): subscribe ", path)

    def unsubscribe( self, path:str ) -> None:
        print("SIM: ZIMFLIsweeper(): unsubscribe ", path)

    def execute(self):
        self.startTime = time.time()
        self.duration  = self.params['samplecount'][0] * self.params['averaging']['time'][0]
        #print("SIM: ZIMFLIsweeper(): duration ", self.duration)
        self.isRunning = True
    
    def finished(self) -> bool:
        """
        Simulation of a short running time. This function will be called
        inside the waiting loop in the Sweeper function.
        The data will be calculated in the read() function.
        """
        if time.time() - self.startTime >= self.duration:
            self.isRunning = False
        return not self.isRunning
    
    def finish(self) -> None:
        self.isRunning = False
    
    def read(self, flag:bool) -> dict:
        rv = {}
        for k,v in self.params.items():
            if isinstance(v,dict):
                for k2,v2 in v.items():
                    if isinstance(v2,dict):
                        print( "DBG:", k, "/", k2, "DICT", v2, "***" )
                    else:
                        rv.update( {k+"/"+k2: v2} )
            else:
                rv.update( {k: v} )
        hdr = { 'systemtime': [time.time()],
                'createdtimestamp': [time.time()],
                'changedtimestamp': [time.time()],
                'flags': [57],
                'moduleflags': [0],
                'chunksizebytes': [0],
                'name': '000 15:17:40.7374', # TODO
                'status': [0],
                'groupindex': [0],
                'color': [0],
                'activerow': [0],
                'triggernumber': [0],
                'gridrows': [0],
                'gridcols': [0],
                'gridmode': [0],
                'gridoperation': [0],
                'griddirection': [0],
                'gridrepetitions': [0],
                'gridcoldelta': [0.],
                'gridcoloffset': [0.],
                'gridrowdelta': [0.],
                'gridrowoffset': [0.],
                'bandwidth': self.params['bandwidth'],
                'center': [0.],
                'nenbw': [0.]
                }
        auxin0 = []          # [V] Aux Input 1 value
        auxin0pwr = []       # = auxin0²
        auxin0stddev = []    # Standard deviation
        auxin1 = []          # [V] Aux Input 2 value
        auxin1pwr = []       # = auxin1²
        auxin1stddev = []    # Standard deviation
        bandwidth = []       # [Hz] Demodulator filter's bandwidth as calculated from sweep/tc (if performing a frequency sweep).
        frequency = []       # [Hz] Qscillator frequency for each step
        frequencypwr = []    # = frequency²
        frequencystddev = [] # Standard deviation
        grid = []            # VALUE OF SWEEPING SETTING
        phase = []           # [Radians] Demodulator phase value
        phasepwr = []        # = phase²
        phasestddev = []     # Standard deviation
        r = []               # [VoltRMS] Demodulator R value
        rpwr = []            # = r²
        rstddev = []         # Standard deviation
        settling = []        # [sec] The waiting time for each measurement point.
        tc = []              # [sec] Demodulator's filter time constant as set for each measurement point.
        tcmeas = []          # Reserved for future use
        x = []               # [V] Demodulator X value
        xpwr = []            # = x²
        xstddev = []         # Standard deviation
        y = []               # [V] Demodulator Y value
        ypwr = []            # = y²
        ystddev = []         # Standard deviation
        count = []           # The number of measurement points actually used by the sweeper when averaging the data. This depends on the values of the parameters in the sweep/averaging/branch.
        settimestamp = []    # Time at verification of settled frequency
        nexttimestamp = []   # Time at measurement point (a littel bit larger than settimestamp)
        freqstep = (self.params['stop'][0] - self.params['start'][0]) / (self.params['samplecount'][0] - 1)
        for s in range(self.params['samplecount'][0]):
            """
            Generate the simulated data.
            All *stddev are NAN as I checked it at the real instrument.
            """
            auxin0.append(s*0.001)
            auxin0pwr.append(s*0.00001)
            auxin0stddev.append(float('nan'))
            auxin1.append(s*0.002)
            auxin1pwr.append(s*0.00002)
            auxin1stddev.append(float('nan'))
            bandwidth.append(hdr['bandwidth'][0])
            # we assume sweeping over the frequency here
            f = freqstep * s + self.params['start'][0]
            frequency.append( f )
            frequencypwr.append( f**2)
            frequencystddev.append(float('nan'))
            grid.append( f )
            phase.append(float(s))
            phasepwr.append(float(s)**2)
            phasestddev.append(float('nan'))
            r.append(float(s))
            rpwr.append(float(s)**2)
            rstddev.append(float('nan'))
            settling.append(self.params['settling']['time'][0])
            tc.append(self.params['settling']['tc'][0])
            tcmeas.append(self.params['settling']['tc'][0])
            x.append(s*0.1)
            xpwr.append((s*0.1)**2)
            xstddev.append(float('nan'))
            y.append(s*0.2)
            ypwr.append((s*0.2)**2)
            ystddev.append(float('nan'))
            count.append(self.params['averaging']['sample'][0])
            settimestamp.append(time.time()+s)
            nexttimestamp.append(time.time()+s+1)
        
        data1 = {'header': hdr,
                 'timestamp': time.time(),  # normally Ticks
                 'samplecount': self.params['samplecount'],
                 'flags': 0,
                 'sampleformat': 1,  # reserved for future use
                 'sweepmode': self.params['scan'][0],
                 'bandwidthmode': self.params['bandwidthcontrol'],
                 'auxin0': auxin0,
                 'auxin0pwr': auxin0pwr,
                 'auxin0stddev': auxin0stddev,
                 'auxin1': auxin1,
                 'auxin1pwr': auxin1pwr,
                 'auxin1stddev': auxin1stddev,
                 'bandwidth': bandwidth,
                 'frequency': frequency,
                 'frequencypwr': frequencypwr,
                 'frequencystddev': frequencystddev,
                 'grid': grid,
                 'phase': phase,
                 'phasepwr': phasepwr,
                 'phasestddev': phasestddev,
                 'r': r,
                 'rpwr': rpwr,
                 'rstddev': rstddev,
                 'settling': settling,
                 'tc': tc,
                 'tcmeas': tcmeas,
                 'x': x,
                 'xpwr': xpwr,
                 'xstddev': xstddev,
                 'y': y,
                 'ypwr': ypwr,
                 'ystddev': ystddev,
                 'count': count,
                 'nexttimestamp': nexttimestamp,
                 'settimestamp': settimestamp
                }
        rv.update( { '/'+self.params['device'][0]+'/demods/0/sample': [ [ data1 ] ] } )
        return rv



class ZIMFLIsim():
    """
    global dicts to hold all values of the instrument grouped by the datatype
    """
    valuesStr = {}      # all string values
    valuesInt = {}      # all integer values
    valuesDbl = {}      # all double / float values
    valuesSample = {}   # all sample values
    subscriptions = []  # all subscriptions for poll function
    
    
    def __init__(self):
        """
        This will fill all the global dicts with the default values. For better
        understanding this is grouped by the subclasses in the driver. The number
        behind the class names are the running numbers for the instances.
        """
        # class AUXInputChannel(InstrumentChannel): 0
        self.valuesInt.update( {'/dev4039/auxins/0/averaging': 0} )
        self.valuesSample.update( {'/dev4039/demods/0/sample': 0} )
        # the auxin/0/values/* are not readable but are used in the poll function
        self.valuesDbl.update( {'/dev4039/auxins/0/values/0': 0,    # TODO Simul
                                '/dev4039/auxins/0/values/1': 0} )  # TODO Simul
        # class AUXOutputChannel(InstrumentChannel): 0,1,2,3
        self.valuesDbl.update( {'/dev4039/auxouts/0/scale': 0,
                                '/dev4039/auxouts/0/preoffset': 0,
                                '/dev4039/auxouts/0/offset': 0,
                                '/dev4039/auxouts/0/limitlower': 0,
                                '/dev4039/auxouts/0/limitupper': 5,
                                '/dev4039/auxouts/0/value': 0,
                                '/dev4039/auxouts/1/scale': 0,
                                '/dev4039/auxouts/1/preoffset': 0,
                                '/dev4039/auxouts/1/offset': 0,
                                '/dev4039/auxouts/1/limitlower': 0,
                                '/dev4039/auxouts/1/limitupper': 5,
                                '/dev4039/auxouts/1/value': 0,
                                '/dev4039/auxouts/2/scale': 0,
                                '/dev4039/auxouts/2/preoffset': 0,
                                '/dev4039/auxouts/2/offset': 0,
                                '/dev4039/auxouts/2/limitlower': 0,
                                '/dev4039/auxouts/2/limitupper': 5,
                                '/dev4039/auxouts/2/value': 0,
                                '/dev4039/auxouts/3/scale': 0,
                                '/dev4039/auxouts/3/preoffset': 0,
                                '/dev4039/auxouts/3/offset': 0,
                                '/dev4039/auxouts/3/limitlower': 0,
                                '/dev4039/auxouts/3/limitupper': 5,
                                '/dev4039/auxouts/3/value': 0} )
        self.valuesInt.update( {'/dev4039/auxouts/0/demodselect': 1,
                                '/dev4039/auxouts/0/outputselect': 0,
                                '/dev4039/auxouts/1/demodselect': 1,
                                '/dev4039/auxouts/1/outputselect': 0,
                                '/dev4039/auxouts/2/demodselect': 1,
                                '/dev4039/auxouts/2/outputselect': 0,
                                '/dev4039/auxouts/3/demodselect': 1,
                                '/dev4039/auxouts/3/outputselect': 0} )
        # class DemodulatorChannel(InstrumentChannel): 0,1
        self.valuesDbl.update( {'/dev4039/demods/0/freq': 100000,   # TODO Simul
                                '/dev4039/demods/0/harmonic': 1,
                                '/dev4039/demods/0/phaseshift': 0,  # TODO Simul
                                '/dev4039/demods/0/rate': 1,
                                '/dev4039/demods/0/timeconstant': 0,
                                '/dev4039/demods/1/freq': 100000,
                                '/dev4039/demods/1/harmonic': 1,
                                '/dev4039/demods/1/phaseshift': 0,
                                '/dev4039/demods/1/rate': 1,
                                '/dev4039/demods/1/timeconstant': 0} )
        self.valuesInt.update( {'/dev4039/demods/0/adcselect': 0,
                                '/dev4039/demods/0/bypass': 0,
                                '/dev4039/demods/0/enable': 0,
                                '/dev4039/demods/0/order': 1,
                                '/dev4039/demods/0/oscselect': 0,
                                '/dev4039/demods/0/phaseadjust': 0,
                                '/dev4039/demods/0/sinc': 0,
                                '/dev4039/demods/0/trigger': 0,     # TODO Simul
                                '/dev4039/demods/1/adcselect': 0,
                                '/dev4039/demods/1/bypass': 0,
                                '/dev4039/demods/1/enable': 0,
                                '/dev4039/demods/1/order': 1,
                                '/dev4039/demods/1/oscselect': 0,
                                '/dev4039/demods/1/phaseadjust': 0,
                                '/dev4039/demods/1/sinc': 0,
                                '/dev4039/demods/1/trigger': 0} )
        #self.valuesSample.update( {'/dev4039/demods/0/sample': 0} ) - AUXInputChannel
        # class SignalInputChannel(InstrumentChannel): 0
        self.valuesDbl.update( {'/dev4039/sigins/0/max': 10,
                                '/dev4039/sigins/0/min': 0,
                                '/dev4039/sigins/0/range': 1,
                                '/dev4039/sigins/0/scaling': 1} )
        self.valuesInt.update( {'/dev4039/sigins/0/ac': 0,
                                '/dev4039/sigins/0/autorange': 0,
                                '/dev4039/sigins/0/diff': 0,
                                '/dev4039/sigins/0/float': 0,
                                '/dev4039/sigins/0/imp50': 0,
                                '/dev4039/sigins/0/on': 0,
                                '/dev4039/sigins/0/rangestep/trigger': 0} )
        # class CurrentInputChannel(InstrumentChannel): 0
        self.valuesDbl.update( {'/dev4039/currins/0/max': 10,
                                '/dev4039/currins/0/min': 0,
                                '/dev4039/currins/0/range': 1,
                                '/dev4039/currins/0/scaling': 1} )
        self.valuesInt.update( {'/dev4039/currins/0/autorange': 0,
                                '/dev4039/currins/0/float': 0,
                                '/dev4039/currins/0/on': 0,
                                '/dev4039/currins/0/rangestep/trigger': 0} )
        # class SignalOutputChannel(InstrumentChannel):
        self.valuesDbl.update( {'/dev4039/sigouts/0': 0,
                                '/dev4039/sigouts/0/amplitudes/1': 0,
                                '/dev4039/sigouts/0/amplitudes/2': 0,
                                '/dev4039/sigouts/0/offset': 0,
                                '/dev4039/sigouts/0/range': 1} )
        self.valuesInt.update( {'/dev4039/sigouts/0/add': 0,
                                '/dev4039/sigouts/0/autorange': 0,
                                '/dev4039/sigouts/0/diff': 0,
                                '/dev4039/sigouts/0/enables/1': 0,
                                '/dev4039/sigouts/0/enables/2': 0,
                                '/dev4039/sigouts/0/imp50': 0,
                                '/dev4039/sigouts/0/on': 0,
                                '/dev4039/sigouts/0/over': 0} )
        # class TriggerInputChannel(InstrumentChannel): 0,1
        self.valuesDbl.update( {'/dev4039/triggers/in/0/level': 1,
                                '/dev4039/triggers/in/1/level': 1} )
        self.valuesInt.update( {'/dev4039/triggers/in/0/autothreshold': 0,
                                '/dev4039/triggers/in/1/autothreshold': 0} )
        # class TriggerOutputChannel(InstrumentChannel):
        self.valuesDbl.update( {'/dev4039/triggers/out/0/pulsewidth': 0,
                                '/dev4039/triggers/out/1/pulsewidth': 0} )
        self.valuesInt.update( {'/dev4039/triggers/out/0/source': 0,
                                '/dev4039/triggers/out/1/source': 0} )
        # class ExternalReferenceChannel(InstrumentChannel):
        self.valuesInt.update( {'/dev4039/extrefs/0/adcselect': 0,
                                '/dev4039/extrefs/0/automode': 4,
                                '/dev4039/extrefs/0/demodselect': 0,
                                '/dev4039/extrefs/0/enable': 0,
                                '/dev4039/extrefs/0/locked': 0,
                                '/dev4039/extrefs/0/oscselect': 0} )
        # class DIOChannel(InstrumentChannel):
        self.valuesInt.update( {'/dev4039/dios/0/decimation': 0,
                                '/dev4039/dios/0/drive': 0,
                                '/dev4039/dios/0/extclk': 0,
                                '/dev4039/dios/0/input': 0,         # TODO Simul
                                '/dev4039/dios/0/mode': 0,
                                '/dev4039/dios/0/output':0} )
        # class MDSChannel(InstrumentChannel):
        self.valuesInt.update( {'/dev4039/mds/armed': 0,
                                '/dev4039/mds/drive': 0,
                                '/dev4039/mds/enable': 0,
                                '/dev4039/mds/source': 0,
                                '/dev4039/mds/syncvalid': 0,
                                '/dev4039/mds/timestamp': 0} )
        # class PIDChannel(InstrumentChannel): - not used
        # class SweeperChannel(InstrumentChannel): - used in a special way
        # Scope* - will not be simulated
        # ZIMFLI():
        self.valuesInt.update( {'/dev4039/clockbase': fixedClockBase,
                                '/dev4039/system/fpgarevision': 52856,
                                '/dev4039/system/fwrevision': 53700,
                                '/zi/about/fwrevision': 0,
                                '/zi/about/revision': 54618} )
        self.valuesDbl.update( {'/dev4039/oscs/0/freq': 100000} )
        self.valuesStr.update( {'/dev4039/features/options': 'F5M',
                                '/dev4039/features/devtype': 'MFLI',
                                '/dev4039/features/serial': '4039',
                                '/dev4039/system/boardrevisions/0': '0',
                                '/dev4039/system/owner': 'FZJ',
                                '/zi/about/copyright': '(c) 2008-2018 Zurich Instruments AG',
                                '/zi/about/dataserver': 'Simulation',
                                '/zi/about/version': '0.1'} )

    
    """
    The set and get functions for all datatypes.
    if the key is not in the dicts, the getter prints a warning and returns zero,
    the setter adds the key/value to the dicts.
    """
    def getString( self, key:str ) -> str:
        if key.lower() not in self.valuesStr:
            print( "DAQ::getString(", key, ") missing" )
            return "?"
        return self.valuesStr[key.lower()]

    def setString( self, key:str, val:str ) -> None:
        if key.lower() not in self.valuesStr:
            self.valuesStr.update( {key.lower(): val} )
        self.valuesStr[key.lower()] = val

    def getInt( self, key:str ) -> int:
        if key.lower() not in self.valuesInt:
            print( "DAQ::getInt(", key, ") missing" )
            return 0
        return self.valuesInt[key.lower()]

    def setInt( self, key:str, val:int ) -> None:
        if key.lower() not in self.valuesInt:
            self.valuesInt.update( {key.lower(): val} )
        self.valuesInt[key.lower()] = val

    def getDouble( self, key:str ) -> float:
        if key.lower() not in self.valuesDbl:
            print( "DAQ::getDouble(", key, ") missing" )
            return 0
        return self.valuesDbl[key.lower()]

    def setDouble( self, key:str, val:float ) -> None:
        if key.lower() not in self.valuesDbl:
            self.valuesDbl.update( {key.lower(): val} )
        self.valuesDbl[key.lower()] = val

    def getSample( self, key:str ) -> dict:
        """
        The getSample has to calculate the simulation data.
        """
        if key.lower() not in self.valuesSample:
            raise RuntimeError("DAQ::getSample("+key+") missing")
        # value = self.daq.getSample(querystr)
        retval = {'timestamp': [ time.time() * fixedClockBase ],
                  'x': 1,
                  'y': 2}
        # TODO: simulationslauf ...
        return retval

    def get( self, key:str ) -> dict:
        """
        Unified getter function used in Sweep().get()
        """
        keylow = key.lower()
        keys = key.split('/')[1:]  # Device (first part) must be uppercase!
        if keylow in self.valuesStr:
            val = self.valuesStr[keylow]
        elif keylow in self.valuesInt:
            val = self.valuesInt[keylow]
        elif keylow in self.valuesDbl:
            val = self.valuesDbl[keylow]
        else:
            print( "DAQ::get(", key, ") missing" )
            val = 0
        rv = { 'value': [val] }
        for k in reversed(keys):
            tmp = { k: rv }
            rv = tmp
        return rv

        
    """
    Some routines with no functionality in the simulation. But they will be called
    from the Zurich Instruments interface.
    """
    def setDebugLevel( self, lvl:int ) -> None:
        pass

    def disconnect(self):
        pass

    def set( self, arr ):
        pass
    
    def sync(self):
        pass
    

    """
    Listing / searching of nodes
    """
    def getList( self, key:str, flag:int ) -> list:
        print( "DAQ:getList(", key, ",", flag, ")" )
        return self.listNodes(key,flag)

    def listNodes( self, key:str, flag:int ) -> list:
        """
        |  listNodes(...)
        |      listNodes( (ziDAQServer)arg1, (str)arg2, (int)arg3) -> list :
        |          This function returns a list of node names found at the specified path.
        |              arg1: Reference to the ziDAQServer class.
        |              arg2: Path for which the nodes should be listed. The path may
        |                    contain wildcards so that the returned nodes do not
        |                    necessarily have to have the same parents.
        |              arg3: Enum that specifies how the selected nodes are listed.
        |                    ziPython.ziListEnum.none -> 0x00
        |                         The default flag, returning a simple
        |                         listing of the given node
        |                    ziPython.ziListEnum.recursive -> 0x01
        |                         Returns the nodes recursively
        |                    ziPython.ziListEnum.absolute -> 0x02
        |                         Returns absolute paths
        |                    ziPython.ziListEnum.leafsonly -> 0x04
        |                         Returns only nodes that are leafs,
        |                         which means the they are at the
        |                         outermost level of the tree.
        |                    ziPython.ziListEnum.settingsonly -> 0x08
        |                         Returns only nodes which are marked
        |                         as setting
        |                    ziPython.ziListEnum.streamingonly -> 0x10
        |                         Returns only streaming nodes
        |                    ziPython.ziListEnum.subscribedonly -> 0x20
        |                         Returns only subscribed nodes
        |                    ziPython.ziListEnum.basechannel -> 0x40
        |                         Return only one instance of a node in case of multiple
        |                         channels
        |                    Or any combination of flags can be used.
        """
        
        def listNodeHelper( vals:list, vor:str, nach:str, flag:int ) -> list:
            rv = []
            for k in vals.keys():
                if len(vor) == 0 or k.startswith(vor):
                    if flag == 0:
                        rv.append([k])
                    else:
                        rv.append(k)
            return rv

        #'/{}/scopes/0/segments/enable'.format(device), 0) != ['']:
        retval = []
        if '*' == key:
            # Jetzt sollen alle gesucht werden
            print( "DAQ:listNodes( * ,", flag, ")" )
            retval += listNodeHelper( self.valuesInt, "", "", flag )
            retval += listNodeHelper( self.valuesDbl, "", "", flag )
            retval += listNodeHelper( self.valuesStr, "", "", flag )
            retval += listNodeHelper( self.valuesSample, "", "", flag )
        elif '*' in key:
            # Jetzt wird ein Wildcard genutzt
            vor,nach = key.lower().split('*')
            print( "DAQ:listNodes(", key, ",", flag, ") ", vor, nach )
            retval += listNodeHelper( self.valuesInt, vor, nach, flag )
            retval += listNodeHelper( self.valuesDbl, vor, nach, flag )
            retval += listNodeHelper( self.valuesStr, vor, nach, flag )
            retval += listNodeHelper( self.valuesSample, vor, nach, flag )
        return retval


    """
    The polling function uses subscriptions and is used in buffered loops.
    """
    def subscribe( self, key:str ) -> None:
        if not key in self.subscriptions:
            self.subscriptions.append(key)
    
    def unsubscribe( self, key:str ) -> None:
        if key == '*':
            self.subscriptions = []
        elif key in self.subscriptions:
            self.subscriptions.remove(key)

    def poll( self, poll_length, poll_timeout, poll_flags, poll_return_flat_dict ):
        """
        poll_length  = 0.1  # [s]
        poll_timeout = 500  # [ms]
        poll_flags   = 0
        poll_return_flat_dict = True
        """
        retval = {}
        for sub in self.subscriptions:
            rv = {'timestamp': [],
                  'x': [],
                  'y': [],
                  'frequency': [],
                  'phase': [],
                  'dio': [],
                  'trigger': [],
                  'auxin0': [],
                  'auxin1': [],
                  'time': {'trigger': 0, 'dataloss': False, 'blockloss': False,
                           'ratechange': False, 'invalidtimestamp': False, 'mindelta': 0}
                  }
            for i in range(5):
                # 5 Messpunkte ...
                s = self.getSample(sub)
                rv['timestamp'].append( s['timestamp'][0] )
                rv['x'].append( s['x'] )
                rv['y'].append( s['y'] )
                rv['frequency'].append( self.getDouble('/dev4039/demods/0/freq') )
                rv['phase'].append( self.getDouble('/dev4039/demods/0/phaseshift') )
                rv['dio'].append( self.getInt('/dev4039/dios/0/input') )
                rv['trigger'].append( self.getInt('/dev4039/demods/0/trigger') )
                rv['auxin0'].append( self.getDouble('/dev4039/auxins/0/values/0') )
                rv['auxin1'].append( self.getDouble('/dev4039/auxins/0/values/1') )
            retval.update( {sub: rv} )
        return retval
    
    """
    Sweep-Functions
    """
    def sweep(self):
        return ZIMFLIsweeper()

"""
Logging vom Gerät:

Settings -> Application -> Parameter Sweep
******************************************
# Starting module sweep on 2019/07/09 10:44:10
h = daq.sweep()
h.get('sweep/xmapping')
h.set('sweep/xmapping', 1)
h.get('sweep/start')
h.get('sweep/stop')
h.get('sweep/scan')
h.get('sweep/samplecount')
h.get('sweep/loopcount')
h.get('sweep/gridnode')
h.get('sweep/settling/time')
h.get('sweep/settling/inaccuracy')
h.get('sweep/averaging/sample')
h.get('sweep/averaging/time')
h.get('sweep/averaging/tc')
h.get('sweep/bandwidth')
h.get('sweep/maxbandwidth')
h.get('sweep/bandwidthoverlap')
h.get('sweep/omegasuppression')
h.get('sweep/bandwidthcontrol')
h.get('sweep/save/save')
h.get('sweep/save/directory')
h.get('sweep/order')
h.get('sweep/phaseunwrap')
h.get('sweep/sincfilter')
h.get('sweep/awgcontrol')
h.set('sweep/device', 'dev4039')
h.set('sweep/historylength', 100)
h.get('sweep/historylength')
h.set('sweep/settling/inaccuracy', 0.0001000)
h.set('sweep/averaging/sample', 1)
h.set('sweep/bandwidth', 1000.0000000)
h.set('sweep/maxbandwidth', 1250000.0000000)
h.set('sweep/omegasuppression', 40.0000000)
h.set('sweep/order', 4)
h.set('sweep/bandwidth', 0.0000000)
h.set('sweep/gridnode', 'oscs/0/freq')
h.set('sweep/save/directory', '/data/LabOne/WebServer')
h.set('sweep/averaging/tc', 0.0000000)
h.set('sweep/averaging/time', 0.0000000)
h.set('sweep/bandwidth', 1000.0000000)
h.set('sweep/start', 1000.0000000)
h.set('sweep/stop', 1000000.0000000)
h.set('sweep/omegasuppression', 40.0000000)
h.set('sweep/order', 4)
h.set('sweep/settling/inaccuracy', 0.0001000)
h.set('sweep/endless', 1)
h.subscribe('/dev4039/demods/0/sample')
h.execute()
#result = 0
#while not h.finished():
  #time.sleep(1);
  #result = h.read()
  #print "Progress %.2f%%\r" %(h.progress() * 100)
  # Using intermediate reads you can plot an ongoing function.
h.finish()
h.unsubscribe('*')

Settings -> Application -> Parameter Sweep Averaged
***************************************************
h.set('sweep/averaging/sample', 20)
h.set('sweep/averaging/tc', 15.0000000)
h.set('sweep/averaging/time', 0.0200000)

Settings -> Application -> Noise Amplitude Sweep
************************************************
h.set('sweep/settling/inaccuracy', 0.0000001)
h.set('sweep/averaging/sample', 1000)
h.set('sweep/averaging/tc', 50.0000000)
h.set('sweep/averaging/time', 0.1000000)
h.set('sweep/bandwidth', 10.0000000)
h.set('sweep/omegasuppression', 60.0000000)

"""
