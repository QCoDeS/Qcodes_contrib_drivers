from functools import partial
from typing import Optional

from qcodes import Instrument
import numpy as np
import socket
import nanonis_tramea
"""
IMPORTANT

Before using the Driver, you must have our python package installed, because many of functions in this driver are merely
wrapper functions of functions from said package. How to install:

pip install nanonis-tramea
"""


class NanonisTramea(Instrument):
    # log = logging.getLogger(__name__)

    def __init__(self, name: str, address: str, port: int, **kwargs):
        super().__init__(name, **kwargs)

        self._address = address
        self._port = port

        self.model = "Tramea"
        self.serial = 1234
        self.firmware = 1

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((self._address, self._port))

        self.n = nanonis_tramea.Nanonis(self._socket)

        for out in range(1, 51):
            self.add_parameter(
                name="{}{}".format("Output", out),
                set_cmd=partial(self.n.UserOut_ValSet, out),
                get_cmd=(lambda out=out: self.n.Signals_ValGet(out + 23, 1)[2][0])
            )
        for inp in range(24):
            self.add_parameter(
                name="{}{}".format("Input", inp+1),
                get_cmd=(lambda inp=inp: self.n.Signals_ValGet(inp, 1)[2][0])
            )
				

    def ThreeDSwp_SwpAcqChsSet(self, channelIndexes: np.ndarray[np.integer]):
        return self.n.ThreeDSwp_AcqChsSet(channelIndexes)[2]
    
    def ThreeDSwp_SwpAcqChsGet(self):
        return self.n.ThreeDSwp_AcqChsGet()[2]
    
    def ThreeDSwp_SwpSaveOptionsGet(self):
        return self.n.ThreeDSwp_SaveOptionsGet()[2]
    
    def ThreeDSwp_SwpSaveOptionsSet(self, seriesName: str, createDateandTimeFolder: np.int32, comment: str,
                                    moduleNamesSize: np.int32, moduleNames: np.ndarray[str]):
        return self.n.ThreeDSwp_SaveOptionsSet(seriesName, createDateandTimeFolder, comment, moduleNamesSize, moduleNames)[2]
    
    def ThreeDSwpStart(self):
        return self.n.ThreeDSwp_Start()[2]
    
    def ThreeDSwpStop(self):
        return self.n.ThreeDSwp_Stop()[2]
    
    def ThreeDSwpOpen(self):
        return self.n.ThreeDSwp_Open()[2]
    
    def ThreeDSwp_SwpStatusGet(self):
        return self.n.ThreeDSwp_StatusGet()[2]
    
    def ThreeDSwp_SwpChSignalSet(self, sweepChannelIndex: np.int32):
        return self.n.ThreeDSwp_SwpChSignalSet(sweepChannelIndex)[2]
    
    def ThreeDSwp_SwpChSignalGet(self):
        return self.n.ThreeDSwp_SwpChSignalGet()[2]
    
    def ThreeDSwp_SwpChLimitsSet(self, start: np.float32, stop: np.float32):
        return self.n.ThreeDSwp_SwpChLimitsSet(start, stop)[2]
    
    def ThreeDSwp_SwpChLimitsGet(self):
        return self.n.ThreeDSwp_SwpChLimitsGet()[2]
    
    def ThreeDSwp_SwpChPropsSet(self, noOfPoints: np.int32, noOfSweeps: np.int32, backwardSweep: np.int32,
                                endOfSweepAction: np.int32, endOfSweepArbitraryValue: np.float32, saveAll: np.int32):
        return self.n.ThreeDSwp_SwpChPropsSet(noOfPoints, noOfSweeps, backwardSweep, endOfSweepAction,
                                        endOfSweepArbitraryValue, saveAll)[2]
    
    def ThreeDSwp_SwpChPropsGet(self):
        return self.n.ThreeDSwp_SwpChPropsGet()[2]
    
    def ThreeDSwp_SwpChTimingSet(self, InitSettlingTime, SettlingTime, IntegrationTime, EndSettlingTime, MaxSlewRate):
        return self.n.ThreeDSwp_SwpChTimingSet(InitSettlingTime, SettlingTime, IntegrationTime, EndSettlingTime, MaxSlewRate)[2]
    
    def ThreeDSwp_SwpChTimingGet(self):
        return self.n.ThreeDSwp_SwpChTimingGet()[2]
    
    def ThreeDSwp_SwpChModeSet(self, Segments_Mode):
        return self.n.ThreeDSwp_SwpChModeSet(Segments_Mode)[2]
    
    def ThreeDSwp_SwpChModeGet(self):
        return self.n.ThreeDSwp_SwpChModeGet()[2]
    
    def ThreeDSwp_SwpChMLSSet(self, NumOfSegments, StartVals, StopVals, SettlingTimes, IntegrationTimes, NoOfSteps,
                                LastSegmentArray):
        return self.n.ThreeDSwp_SwpChMLSSet(NumOfSegments, StartVals, StopVals, SettlingTimes, IntegrationTimes, NoOfSteps,
                                        LastSegmentArray)[2]
    
    def ThreeDSwp_SwpChMLSGet(self):
        return self.n.ThreeDSwp_SwpChMLSGet()[2]
    
    def ThreeDSwp_StpCh1SignalSet(self, StepChannelOneIndex):
        return self.n.ThreeDSwp_StpCh1SignalSet(StepChannelOneIndex)[2]
    
    def ThreeDSwp_StpCh1SignalGet(self):
        return self.n.ThreeDSwp_StpCh1SignalGet()[2]
    
    def ThreeDSwp_StpCh1LimitsSet(self, Start, Stop):
        return self.n.ThreeDSwp_StpCh1LimitsSet(Start, Stop)[2]
    
    def ThreeDSwp_StpCh1LimitsGet(self):
        return self.n.ThreeDSwp_StpCh1LimitsGet()[2]
    
    def ThreeDSwp_StpCh1PropsSet(self, NoOfPoints, BwdSweep, EndOfSweep, EndOfSweepVal):
        return self.n.ThreeDSwp_StpCh1PropsSet(NoOfPoints, BwdSweep, EndOfSweep, EndOfSweepVal)[2]
    
    def ThreeDSwp_StpCh1PropsGet(self):
        return self.n.ThreeDSwp_StpCh1PropsGet()[2]
    
    def ThreeDSwp_StpCh1TimingSet(self, InitSettlingTime, EndSettlingTime, MaxSlewRate):
        return self.n.ThreeDSwp_StpCh1TimingSet(InitSettlingTime, EndSettlingTime, MaxSlewRate)[2]
    
    def ThreeDSwp_StpCh1TimingGet(self):
        return self.n.ThreeDSwp_StpCh1TimingGet()[2]
    
    def ThreeDSwp_StpCh2SignalSet(self, StepChannel2Name):
        return self.n.ThreeDSwp_StpCh2SignalSet(StepChannel2Name)[2]
    
    def ThreeDSwp_StpCh2SignalGet(self):
        return self.n.ThreeDSwp_StpCh2SignalGet()[2]
    
    def ThreeDSwp_StpCh2LimitsSet(self, Start, Stop):
        return self.n.ThreeDSwp_StpCh2LimitsSet(Start, Stop)[2]
    
    def ThreeDSwp_StpCh2LimitsGet(self):
        return self.n.ThreeDSwp_StpCh2LimitsGet()[2]
    
    def ThreeDSwp_StpCh2PropsSet(self, NumOfPoints, BwdSweep, EndOfSweep, EndOfSweepVal):
        return self.n.ThreeDSwp_StpCh2PropsSet(NumOfPoints, BwdSweep, EndOfSweep, EndOfSweepVal)[2]
    
    def ThreeDSwp_StpCh2PropsGet(self):
        return self.n.ThreeDSwp_StpCh2PropsGet()[2]
    
    def ThreeDSwp_StpCh2TimingSet(self, InitSettlingTime, EndSettlingTime, MaxSlewRate):
        return self.n.ThreeDSwp_StpCh2TimingSet(InitSettlingTime, EndSettlingTime, MaxSlewRate)[2]
    
    def ThreeDSwp_StpCh2TimingGet(self):
        return self.n.ThreeDSwp_StpCh2TimingGet()[2]
    
    def ThreeDSwp_TimingRowLimitSet(self, RowIndex, MaxTime, ChannelIndex):
        return self.n.ThreeDSwp_TimingRowLimitSet(RowIndex, MaxTime, ChannelIndex)[2]
    
    def ThreeDSwp_TimingRowLimitGet(self, RowIndex):
        return self.n.ThreeDSwp_TimingRowLimitGet(RowIndex)[2]
    
    def ThreeDSwp_TimingRowMethodsSet(self, RowIndex, MethodLower, MethodMiddle, MethodUpper, MethodAlt):
        return self.n.ThreeDSwp_TimingRowMethodsSet(RowIndex, MethodLower, MethodMiddle, MethodUpper, MethodAlt)[2]
    
    def ThreeDSwp_TimingRowMethodsGet(self, RowIndex):
        return self.n.ThreeDSwp_TimingRowMethodsGet(RowIndex)[2]
    
    def ThreeDSwp_TimingRowValsSet(self, RowIndex, MiddleRangeFrom, LowerRangeVal, MiddleRangeVal, MiddleRangeTo,
                                    UpperRangeVal, AltRangeVal):
        return self.n.ThreeDSwp_TimingRowValsSet(RowIndex, MiddleRangeFrom, LowerRangeVal, MiddleRangeVal, MiddleRangeTo,
                                            UpperRangeVal, AltRangeVal)[2]
    
    def ThreeDSwp_TimingRowValsGet(self, RowIndex):
        return self.n.ThreeDSwp_TimingRowValsGet(RowIndex)[2]
    
    def ThreeDSwp_TimingEnable(self, Enable):
        return self.n.ThreeDSwp_TimingEnable(Enable)[2]
    
    def ThreeDSwp_TimingSend(self):
        return self.n.ThreeDSwp_TimingSend()[2]
    
    def ThreeDSwp_FilePathsGet(self):
        return self.n.ThreeDSwp_FilePathsGet()[2]
    
    def OneDSwp_AcqChsSet(self, ChannelIndexes):
        return self.n.OneDSwp_AcqChsSet(ChannelIndexes)[2]
    
    def OneDSwp_AcqChsGet(self):
        return self.n.OneDSwp_AcqChsGet()[2]
    
    def OneDSwp_SwpSignalSet(self, SweepChannelName):
        return self.n.OneDSwp_SwpSignalSet(SweepChannelName)[2]
    
    def OneDSwp_SwpSignalGet(self):
        return self.n.OneDSwp_SwpSignalGet()[2]
    
    def OneDSwp_LimitsSet(self, LowerLimit, UpperLimit):
        return self.n.OneDSwp_LimitsSet(LowerLimit, UpperLimit)[2]
    
    def OneDSwp_LimitsGet(self):
        return self.n.OneDSwp_LimitsGet()[2]
    
    def OneDSwp_PropsSet(self, InitSettlingTime, MaxSlewRate, NoOfSteps, Period, Autosave, SaveDialogBox, SettlingTime):
        return self.n.OneDSwp_PropsSet(InitSettlingTime, MaxSlewRate, NoOfSteps, Period, Autosave, SaveDialogBox, SettlingTime)[2]
    
    def OneDSwp_PropsGet(self):
        return self.n.OneDSwp_PropsGet()[2]
    
    def OneDSwp_Start(self, GetData, SweepDirection, SaveBaseName, ResetSignal):
        return self.n.OneDSwp_Start(GetData, SweepDirection, SaveBaseName, ResetSignal)[2]
    
    def OneDSwp_Stop(self):
        return self.n.OneDSwp_Stop()[2]
    
    def OneDSwp_Open(self):
        return self.n.OneDSwp_Open()[2]
    
    def LockIn_ModOnOffSet(self, Modulator_number, Lock_In_OndivOff):
        return self.n.LockIn_ModOnOffSet(Modulator_number, Lock_In_OndivOff)[2]
    
    def LockIn_ModOnOffGet(self, Modulator_number):
        return self.n.LockIn_ModOnOffGet(Modulator_number)[2]
    
    def LockIn_ModSignalSet(self, Modulator_number, Modulator_Signal_Index):
        return self.n.LockIn_ModSignalSet(Modulator_number, Modulator_Signal_Index)[2]
    
    def LockIn_ModSignalGet(self, Modulator_number):
        return self.n.LockIn_ModSignalGet(Modulator_number)[2]
    
    def LockIn_ModPhasRegSet(self, Modulator_number, Phase_Register_Index):
        return self.n.LockIn_ModPhasRegSet(Modulator_number, Phase_Register_Index)[2]
    
    def LockIn_ModPhasRegGet(self, Modulator_number):
        return self.n.LockIn_ModPhasRegGet(Modulator_number)[2]
    
    def LockIn_ModHarmonicSet(self, Modulator_number, Harmonic_):
        return self.n.LockIn_ModHarmonicSet(Modulator_number, Harmonic_)[2]
    
    def LockIn_ModHarmonicGet(self, Modulator_number):
        return self.n.LockIn_ModHarmonicGet(Modulator_number)[2]
    
    def LockIn_ModPhasSet(self, Modulator_number, Phase_deg_):
        return self.n.LockIn_ModPhasSet(Modulator_number, Phase_deg_)[2]
    
    def LockIn_ModPhasGet(self, Modulator_number):
        return self.n.LockIn_ModPhasGet(Modulator_number)[2]
    
    def LockIn_ModAmpSet(self, Modulator_number, Amplitude_):
        return self.n.LockIn_ModAmpSet(Modulator_number, Amplitude_)[2]
    
    def LockIn_ModAmpGet(self, Modulator_number):
        return self.n.LockIn_ModAmpGet(Modulator_number)[2]
    
    def LockIn_ModPhasFreqSet(self, Modulator_number, Frequency_Hz_):
        return self.n.LockIn_ModPhasFreqSet(Modulator_number, Frequency_Hz_)[2]
    
    def LockIn_ModPhasFreqGet(self, Modulator_number):
        return self.n.LockIn_ModPhasFreqGet(Modulator_number)[2]
    
    def LockIn_DemodSignalSet(self, Demodulator_number, Demodulator_Signal_Index):
        return self.n.LockIn_DemodSignalSet(Demodulator_number, Demodulator_Signal_Index)[2]
    
    def LockIn_DemodSignalGet(self, Demodulator_number):
        return self.n.LockIn_DemodSignalGet(Demodulator_number)[2]
    
    def LockIn_DemodHarmonicSet(self, Demodulator_number, Harmonic_):
        return self.n.LockIn_DemodHarmonicSet(Demodulator_number, Harmonic_)[2]
    
    def LockIn_DemodHarmonicGet(self, Demodulator_number):
        return self.n.LockIn_DemodHarmonicGet(Demodulator_number)[2]
    
    def LockIn_DemodHPFilterSet(self, Demodulator_number, HP_Filter_Order, HP_Filter_Cutoff_Frequency_Hz):
        return self.n.LockIn_DemodHPFilterSet(Demodulator_number, HP_Filter_Order, HP_Filter_Cutoff_Frequency_Hz)[2]
    
    def LockIn_DemodHPFilterGet(self, Demodulator_number):
        return self.n.LockIn_DemodHPFilterGet(Demodulator_number)[2]
    
    def LockIn_DemodLPFilterSet(self, Demodulator_number, LP_Filter_Order, LP_Filter_Cutoff_Frequency_Hz):
        return self.n.LockIn_DemodLPFilterSet(Demodulator_number, LP_Filter_Order, LP_Filter_Cutoff_Frequency_Hz)[2]
    
    def LockIn_DemodLPFilterGet(self, Demodulator_number):
        return self.n.LockIn_DemodLPFilterGet(Demodulator_number)[2]
    
    def LockIn_DemodPhasRegSet(self, Demodulator_number, Phase_Register_Index):
        return self.n.LockIn_DemodPhasRegSet(Demodulator_number, Phase_Register_Index)[2]
    
    def LockIn_DemodPhasRegGet(self, Demodulator_number):
        return self.n.LockIn_DemodPhasRegGet(Demodulator_number)[2]
    
    def LockIn_DemodPhasSet(self, Demodulator_number, Phase_deg_):
        return self.n.LockIn_DemodPhasSet(Demodulator_number, Phase_deg_)[2]
    
    def LockIn_DemodPhasGet(self, Demodulator_number):
        return self.n.LockIn_DemodPhasGet(Demodulator_number)[2]
    
    def LockIn_DemodSyncFilterSet(self, Demodulator_number, Sync_Filter_):
        return self.n.LockIn_DemodSyncFilterSet(Demodulator_number, Sync_Filter_)[2]
    
    def LockIn_DemodSyncFilterGet(self, Demodulator_number):
        return self.n.LockIn_DemodSyncFilterGet(Demodulator_number)[2]
    
    def LockIn_DemodRTSignalsSet(self, Demodulator_number, RT_Signals_):
        return self.n.LockIn_DemodRTSignalsSet(Demodulator_number, RT_Signals_)[2]
    
    def LockIn_DemodRTSignalsGet(self, Demodulator_number):
        return self.n.LockIn_DemodRTSignalsGet(Demodulator_number)[2]
    
    def LockInFreqSwp_Open(self):
        return self.n.LockInFreqSwp_Open()[2]
    
    def LockInFreqSwp_Start(self, Get_Data, Direction):
        return self.n.LockInFreqSwp_Start(Get_Data, Direction)[2]
    
    def LockInFreqSwp_SignalSet(self, Sweep_signal_index):
        return self.n.LockInFreqSwp_SignalSet(Sweep_signal_index)[2]
    
    def LockInFreqSwp_SignalGet(self):
        return self.n.LockInFreqSwp_SignalGet()[2]
    
    def LockInFreqSwp_LimitsSet(self, Lower_limit_Hz, Upper_limit_Hz):
        return self.n.LockInFreqSwp_LimitsSet(Lower_limit_Hz, Upper_limit_Hz)[2]
    
    def LockInFreqSwp_LimitsGet(self):
        return self.n.LockInFreqSwp_LimitsGet()[2]
    
    def LockInFreqSwp_PropsSet(self, Number_of_steps, Integration_periods, Minimum_integration_time_s, Settling_periods,
                                Minimum_Settling_time_s, Autosave, Save_dialog, Basename):
        return self.n.LockInFreqSwp_PropsSet(Number_of_steps, Integration_periods, Minimum_integration_time_s,
                                        Settling_periods,
                                        Minimum_Settling_time_s, Autosave, Save_dialog, Basename)[2]
    
    def LockInFreqSwp_PropsGet(self):
        return self.n.LockInFreqSwp_PropsGet()[2]
    
    def Script_Load(self, Script_file_path, Load_session):
        return self.n.Script_Load(Script_file_path, Load_session)[2]
    
    def Script_Save(self, Script_file_path, Save_session):
        return self.n.Script_Save(Script_file_path, Save_session)[2]
    
    def Script_Deploy(self, Script_index):
        return self.n.Script_Deploy(Script_index)[2]
    
    def Script_Undeploy(self, Script_index):
        return self.n.Script_Undeploy(Script_index)[2]
    
    def Script_Run(self, Script_index, Wait_until_script_finishes):
        return self.n.Script_Run(Script_index, Wait_until_script_finishes)[2]
    
    def Script_Stop(self):
        return self.n.Script_Stop()[2]
    
    def Script_ChsGet(self, Acquire_buffer):
        return self.n.Script_ChsGet(Acquire_buffer)[2]
    
    def Script_ChsSet(self, Acquire_buffer, Number_of_channels, Channel_indexes):
        return self.n.Script_ChsSet(Acquire_buffer, Number_of_channels, Channel_indexes)[2]
    
    def Script_DataGet(self, Acquire_buffer, Sweep_number):
        return self.n.Script_DataGet(Acquire_buffer, Sweep_number)[2]
    
    def Script_Autosave(self, Acquire_buffer, Sweep_number, All_sweeps_to_same_file):
        return self.n.Script_Autosave(Acquire_buffer, Sweep_number, All_sweeps_to_same_file)[2]
    
    def Signals_NamesGet(self):
        return self.n.Signals_NamesGet()[2]
    
    def Signals_CalibrGet(self, Signal_index):
        return self.n.Signals_CalibrGet(Signal_index)[2]
    
    def Signals_RangeGet(self, Signal_index):
        return self.n.Signals_RangeGet(Signal_index)[2]
    
    def Signals_MeasNamesGet(self):
        return self.n.Signals_MeasNamesGet()[2][2]
    
    def Signals_AddRTGet(self):
        return self.n.Signals_AddRTGet()[2][2]
    
    def Signals_AddRTSet(self, Additional_RT_signal_1, Additional_RT_signal_2):
        return self.n.Signals_AddRTSet(Additional_RT_signal_1, Additional_RT_signal_2)[2]
    
    def UserIn_CalibrSet(self, Input_index, Calibration_per_volt, Offset_in_physical_units):
        return self.n.UserIn_CalibrSet(Input_index, Calibration_per_volt, Offset_in_physical_units)[2]
    
    def UserOut_ModeSet(self, Output_index, Output_mode):
        return self.n.UserOut_ModeSet(Output_index, Output_mode)[2]
    
    def UserOut_ModeGet(self, Output_index):
        return self.n.UserOut_ModeGet(Output_index)[2]
    
    def UserOut_MonitorChSet(self, Output_index, Monitor_channel_index):
        return self.n.UserOut_MonitorChSet(Output_index, Monitor_channel_index)[2]
    
    def UserOut_MonitorChGet(self, Output_index):
        return self.n.UserOut_MonitorChGet(Output_index)[2]
    
    def UserOut_CalibrSet(self, Output_index, Calibration_per_volt, Offset_in_physical_units):
        self.n.UserOut_CalibrSet(Output_index, Calibration_per_volt, Offset_in_physical_units)
    
    def UserOut_CalcSignalNameSet(self, Output_index, Calculated_signal_name):
        return self.n.UserOut_CalcSignalNameSet(Output_index, Calculated_signal_name)[2]
    
    def UserOut_CalcSignalNameGet(self, Output_index):
        return self.n.UserOut_CalcSignalNameGet(Output_index)[2]
    
    def UserOut_CalcSignalConfigSet(self, Output_index, Signal_1, Operation, Signal_2):
        return self.n.UserOut_CalcSignalConfigSet(Output_index, Signal_1, Operation, Signal_2)[2]
    
    def UserOut_CalcSignalConfigGet(self, Output_index):
        return self.n.UserOut_CalcSignalConfigGet(Output_index)[2]
    
    def UserOut_LimitsSet(self, Output_index, Upper_limit, Lower_limit):
        return self.n.UserOut_LimitsSet(Output_index, Upper_limit, Lower_limit)[2]
    
    def UserOut_LimitsGet(self, Output_index):
        return self.n.UserOut_LimitsGet(Output_index)[2]
    
    def UserOut_SlewRateSet(self, Output_Index, Slew_Rate):
        return self.n.UserOut_SlewRateSet(Output_Index, Slew_Rate)[2]
    
    def UserOut_SlewRateGet(self):
        return self.n.UserOut_SlewRateGet()[2]
    
    def DigLines_PropsSet(self, Digital_line, Port, Direction, Polarity):
        return self.n.DigLines_PropsSet(Digital_line, Port, Direction, Polarity)[2]
    
    def DigLines_OutStatusSet(self, Port, Digital_line, Status):
        return self.n.DigLines_OutStatusSet(Port, Digital_line, Status)[2]
    
    def DigLines_TTLValGet(self, Port):
        return self.n.DigLines_TTLValGet(Port)[2]
    
    def DigLines_Pulse(self, Port, Digital_lines, Pulse_width_s, Pulse_pause_s, Number_of_pulses,
                        Wait_until_finished):
        return self.n.DigLines_Pulse(Port, Digital_lines, Pulse_width_s, Pulse_pause_s, Number_of_pulses,
                                Wait_until_finished)[2]
    
    def DataLog_Open(self):
        return self.n.DataLog_Open()[2]
    
    def DataLog_Start(self):
        return self.n.DataLog_Start()[2]
    
    def DataLog_Stop(self):
        return self.n.DataLog_Stop()[2]
    
    def DataLog_StatusGet(self):
        return self.n.DataLog_StatusGet()[2]
    
    def DataLog_ChsSet(self, Channel_indexes):
        return self.n.DataLog_ChsSet(Channel_indexes)[2]
    
    def DataLog_ChsGet(self):
        return self.n.DataLog_ChsGet()[2]
    
    def DataLog_PropsSet(self, Acquisition_mode, Acquisition_duration_hours, Acquisition_duration_minutes,
                            Acquisition_duration_seconds, Averaging, Basename, Comment, List_of_modules):
        return self.n.DataLog_PropsSet(Acquisition_mode, Acquisition_duration_hours, Acquisition_duration_minutes,
                                Acquisition_duration_seconds, Averaging, Basename, Comment, List_of_modules)[2]
    
    def DataLog_PropsGet(self):
        return self.n.DataLog_PropsGet()[2]
    
    def TCPLog_Start(self):
        return self.n.TCPLog_Start()[2]
    
    def TCPLog_Stop(self):
        return self.n.TCPLog_Stop()[2]
    
    def TCPLog_ChsSet(self, Channel_indexes):
        return self.n.TCPLog_ChsSet(Channel_indexes)[2]
    
    def TCPLog_OversamplSet(self, Oversampling_value):
        return self.n.TCPLog_OversamplSet(Oversampling_value)[2]
    
    def TCPLog_StatusGet(self):
        return self.n.TCPLog_StatusGet()[2]
    
    def OsciHR_ChSet(self, Channel_index):
        return self.n.OsciHR_ChSet(Channel_index)[2]
    
    def OsciHR_ChGet(self):
        return self.n.OsciHR_ChGet()[2]
    
    def OsciHR_OversamplSet(self, Oversampling_index):
        return self.n.OsciHR_OversamplSet(Oversampling_index)[2]
    
    def OsciHR_OversamplGet(self):
        return self.n.OsciHR_OversamplGet()[2]
    
    def OsciHR_CalibrModeSet(self, Calibration_mode):
        return self.n.OsciHR_CalibrModeSet(Calibration_mode)[2]
    
    def OsciHR_CalibrModeGet(self):
        return self.n.OsciHR_CalibrModeGet()[2]
    
    def OsciHR_SamplesSet(self, Number_of_samples):
        return self.n.OsciHR_SamplesSet(Number_of_samples)[2]
    
    def OsciHR_SamplesGet(self):
        return self.n.OsciHR_SamplesGet()[2]
    
    def OsciHR_PreTrigSet(self, Pre_Trigger_samples, Pre_Trigger_s):
        return self.n.OsciHR_PreTrigSet(Pre_Trigger_samples, Pre_Trigger_s)[2]
    
    def OsciHR_PreTrigGet(self):
        return self.n.OsciHR_PreTrigGet()[2]
    
    def OsciHR_Run(self):
        return self.n.OsciHR_Run()[2]
    
    def OsciHR_OsciDataGet(self, Data_to_get, Timeout_s):
        return self.n.OsciHR_OsciDataGet(Data_to_get, Timeout_s)[2]
    
    def OsciHR_TrigModeSet(self, Trigger_mode):
        return self.n.OsciHR_TrigModeSet(Trigger_mode)[2]
    
    def OsciHR_TrigModeGet(self):
        return self.n.OsciHR_TrigModeGet()[2]
    
    def OsciHR_TrigLevChSet(self, Level_trigger_channel_index):
        return self.n.OsciHR_TrigLevChSet(Level_trigger_channel_index)[2]
    
    def OsciHR_TrigLevChGet(self):
        return self.n.OsciHR_TrigLevChGet()[2]
    
    def OsciHR_TrigLevValSet(self, Level_trigger_value):
        return self.n.OsciHR_TrigLevValSet(Level_trigger_value)[2]
    
    def OsciHR_TrigLevValGet(self):
        return self.n.OsciHR_TrigLevValGet()[2]
    
    def OsciHR_TrigLevHystSet(self, Level_trigger_Hysteresis):
        return self.n.OsciHR_TrigLevHystSet(Level_trigger_Hysteresis)[2]
    
    def OsciHR_TrigLevHystGet(self):
        return self.n.OsciHR_TrigLevHystGet()[2]
    
    def OsciHR_TrigLevSlopeSet(self, Level_trigger_slope):
        return self.n.OsciHR_TrigLevSlopeSet(Level_trigger_slope)[2]
    
    def OsciHR_TrigLevSlopeGet(self):
        return self.n.OsciHR_TrigLevSlopeGet()[2]
    
    def OsciHR_TrigDigChSet(self, Digital_trigger_channel_index):
        return self.n.OsciHR_TrigDigChSet(Digital_trigger_channel_index)[2]
    
    def OsciHR_TrigDigChGet(self):
        return self.n.OsciHR_TrigDigChGet()[2]
    
    def OsciHR_TrigArmModeSet(self, Trigger_arming_mode):
        return self.n.OsciHR_TrigArmModeSet(Trigger_arming_mode)[2]
    
    def OsciHR_TrigArmModeGet(self):
        return self.n.OsciHR_TrigArmModeGet()[2]
    
    def OsciHR_TrigDigSlopeSet(self, Digital_trigger_slope):
        return self.n.OsciHR_TrigDigSlopeSet(Digital_trigger_slope)[2]
    
    def OsciHR_TrigDigSlopeGet(self):
        return self.n.OsciHR_TrigDigSlopeGet()[2]
    
    def OsciHR_TrigRearm(self):
        return self.n.OsciHR_TrigRearm()[2]
    
    def OsciHR_PSDShow(self, Show_PSD_section):
        return self.n.OsciHR_PSDShow(Show_PSD_section)[2]
    
    def OsciHR_PSDWeightSet(self, PSD_Weighting):
        return self.n.OsciHR_PSDWeightSet(PSD_Weighting)[2]
    
    def OsciHR_PSDWeightGet(self):
        return self.n.OsciHR_PSDWeightGet()[2]
    
    def OsciHR_PSDWindowSet(self, PSD_window_type):
        return self.n.OsciHR_PSDWindowSet(PSD_window_type)[2]
    
    def OsciHR_PSDWindowGet(self):
        return self.n.OsciHR_PSDWindowGet()[2]
    
    def OsciHR_PSDAvrgTypeSet(self, PSD_averaging_type):
        return self.n.OsciHR_PSDAvrgTypeSet(PSD_averaging_type)[2]
    
    def OsciHR_PSDAvrgTypeGet(self):
        return self.n.OsciHR_PSDAvrgTypeGet()[2]
    
    def OsciHR_PSDAvrgCountSet(self, PSD_averaging_count):
        return self.n.OsciHR_PSDAvrgCountSet(PSD_averaging_count)[2]
    
    def OsciHR_PSDAvrgCountGet(self):
        return self.n.OsciHR_PSDAvrgCountGet()[2]
    
    def OsciHR_PSDAvrgRestart(self):
        return self.n.OsciHR_PSDAvrgRestart()[2]
    
    def OsciHR_PSDDataGet(self, Data_to_get, Timeout_s):
        return self.n.OsciHR_PSDDataGet(Data_to_get, Timeout_s)[2]
    
    def Util_SessionPathGet(self):
        return self.n.Util_SessionPathGet()[2]
    
    def Util_SettingsLoad(self, Settings_file_path, Load_session_settings):
        return self.n.Util_SettingsLoad(Settings_file_path, Load_session_settings)[2]
    
    def Util_SettingsSave(self, Settings_file_path, Save_session_settings):
        return self.n.Util_SettingsSave(Settings_file_path, Save_session_settings)[2]
    
    def Util_LayoutLoad(self, Layout_file_path, Load_session_layout):
        return self.n.Util_LayoutLoad(Layout_file_path, Load_session_layout)[2]
    
    def Util_LayoutSave(self, Layout_file_path, Save_session_layout):
        return self.n.Util_LayoutSave(Layout_file_path, Save_session_layout)[2]
    
    def Util_Lock(self):
        return self.n.Util_Lock()[2]
    
    def Util_UnLock(self):
        return self.n.Util_UnLock()[2]
    
    def Util_RTFreqSet(self, RT_frequency):
        return self.n.Util_RTFreqSet(RT_frequency)[2]
    
    def Util_RTFreqGet(self):
        return self.n.Util_RTFreqGet()[2]
    
    def Util_AcqPeriodSet(self, Acquisition_Period_s):
        return self.n.Util_AcqPeriodSet(Acquisition_Period_s)[2]
    
    def Util_AcqPeriodGet(self):
        return self.n.Util_AcqPeriodGet()[2]
    
    def Util_RTOversamplSet(self, RT_oversampling):
        return self.n.Util_RTOversamplSet(RT_oversampling)[2]
    
    def Util_RTOversamplGet(self):
        return self.n.Util_RTOversamplGet()[2]
    
    def Util_Quit(self, Use_Stored_Values, Settings_Name, Layout_Name, Save_Signals):
        return self.n.Util_Quit(Use_Stored_Values, Settings_Name, Layout_Name, Save_Signals)[2]
    
    def ReturnDebugInfo(self, returnInfo):
        self.n.returnDebugInfo(returnInfo)
    
    def OneDSwpOpen(self):
        return self.n.OneDSwp_Open()[2]
    
    def OneDSwpStart(self, GetData: np.uint32, SweepDirection: np.uint32, SaveBaseName: str, ResetSignal: np.uint32):
        return self.n.OneDSwp_Start(GetData, SweepDirection, SaveBaseName, ResetSignal)[2]