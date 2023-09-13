/*******************************************************************/
/*                                                                 */
/* File Name:   HolzworthMulti.h                                   */
/*                                                                 */
/*                                                                 */
/*******************************************************************/
#ifdef __cplusplus
#define HOLZ_INIT extern "C" __declspec(dllexport)
#else
#define HOLZ_INIT __declspec(dllexport)
#endif

//Use the functions below for HS9000 series or legacy
HOLZ_INIT int deviceAttached(const char *serialnum);
HOLZ_INIT int openDevice(const char *serialnum);
HOLZ_INIT char* getAttachedDevices();
HOLZ_INIT void close_all (void);

//Use the function below for HS9000 series only
HOLZ_INIT char* usbCommWrite(const char *serialnum, const char *pBuf);

//Use the functions below for legacy only
HOLZ_INIT int RFPowerOn(const char *serialnum);
HOLZ_INIT int RFPowerOff(const char *serialnum);
HOLZ_INIT short isRFPowerOn(const char *serialnum);
HOLZ_INIT int setPower(const char *serialnum, short powernum);
HOLZ_INIT int setPowerS(const char *serialnum, const char *powerstr);
HOLZ_INIT short readPower(const char *serialnum);
HOLZ_INIT int setPhase(const char *serialnum, short phasenum);
HOLZ_INIT int setPhaseS(const char *serialnum, const char *phasestr);
HOLZ_INIT short readPhase(const char *serialnum);
HOLZ_INIT int setFrequency(const char *serialnum, long long frequencynum);
HOLZ_INIT int setFrequencyS(const char *serialnum, const char *frequencystr);
//HOLZ_INIT int setFTWS(const char *serialnum, const char *frequencystr);
HOLZ_INIT long long readFrequency(const char *serialnum);
HOLZ_INIT int recallFactoryPreset(const char *serialnum);
HOLZ_INIT int saveCurrentState(const char *serialnum);
HOLZ_INIT int recallSavedState(const char *serialnum);
HOLZ_INIT int ModEnableNo(const char *serialnum);
HOLZ_INIT int ModEnableFM(const char *serialnum);
HOLZ_INIT int ModEnablePulse(const char *serialnum);
HOLZ_INIT int ModEnablePM(const char *serialnum);
HOLZ_INIT int setFMDeviation(const char *serialnum, short fmDevnum);
HOLZ_INIT int setFMDeviationS(const char *serialnum,const char *fmDevstr);
HOLZ_INIT int setPMDeviation(const char *serialnum, short pmnum);
HOLZ_INIT int setPMDeviationS(const char *serialnum,const char *pmstr);

HOLZ_INIT char* write_string3(const char* serialnum, const char *pBuf);
