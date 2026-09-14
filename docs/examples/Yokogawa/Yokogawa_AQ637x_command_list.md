# Yokogawa AQ637x SCPI Command Reference

Complete SCPI command reference with all commands in Command/Parameter/Page format.

---

## COMMON Commands (IEEE 488.2)

| Command | Parameter | Page |
|---------|-----------|------|
| `*CLS` | none | 7-39 |
| `*ESE` | `<integer>` | 7-39 |
| `*ESE?` | none | 7-39 |
| `*ESR?` | none | 7-39 |
| `*IDN?` | none | 7-39 |
| `*OPC` | none | 7-39 |
| `*OPC?` | none | 7-39 |
| `*RST` | none | 7-40 |
| `*SRE` | `<integer>` | 7-40 |
| `*SRE?` | none | 7-40 |
| `*STB?` | none | 7-40 |
| `*TRG` | none | 7-40 |
| `*TST?` | none | 7-40 |
| `*WAI` | none | 7-40 |

---

## ABORt

| Command | Parameter | Page |
|---------|-----------|------|
| `ABORt` | none | 7-41 |

---

## APPLication:DLOGging (Data Logging)

| Command | Parameter | Page |
|---------|-----------|------|
| `APPLication:DLOGging:ETIMe?` | none | 7-41 |
| `APPLication:DLOGging:LPARameter:INTerval` | `<integer>` | 7-41 |
| `APPLication:DLOGging:LPARameter:ITEM` | `0\|1\|2\|3` | 7-42 |
| `APPLication:DLOGging:LPARameter:LMODe` | `1\|2` | 7-42 |
| `APPLication:DLOGging:LPARameter:MEMory` | `INTernal\|EXTernal` | 7-42 |
| `APPLication:DLOGging:LPARameter:MTHResh` | `<NRf>` | 7-42 |
| `APPLication:DLOGging:LPARameter:PDETect:ATHResh` | `<NRf>` | 7-43 |
| `APPLication:DLOGging:LPARameter:PDETect:RTHResh` | `<NRf>` | 7-43 |
| `APPLication:DLOGging:LPARameter:PDETect:TTYPe` | `ABSolute\|RELative` | 7-43 |
| `APPLication:DLOGging:LPARameter:TDURation` | `<integer>` | 7-43 |
| `APPLication:DLOGging:LPARameter:TLOGging` | `OFF\|ON\|0\|1` | 7-44 |
| `APPLication:DLOGging:STATe` | `STOP\|STARt\|0\|1` | 7-44 |

---

## CALCulate (Analysis, Markers, Math)

### Auto Markers [1|2|3|4]

| Command | Parameter | Page |
|---------|-----------|------|
| `CALCulate:AMARker[1\|2\|3\|4]:AOFF` | none | 7-44 |
| `CALCulate:AMARker[1\|2\|3\|4]:FUNCtion:INTegral:IRANge` | `<NRf>[Hz]` | 7-45 |
| `CALCulate:AMARker[1\|2\|3\|4]:FUNCtion:INTegral:RESult?` | none | 7-45 |
| `CALCulate:AMARker[1\|2\|3\|4]:FUNCtion:INTegral[:STATe]` | `OFF\|ON\|0\|1` | 7-45 |
| `CALCulate:AMARker[1\|2\|3\|4]:FUNCtion:PDENsity\|NOISe:BWIDth\|BANDwidth` | `<NRf>[M]` | 7-46 |
| `CALCulate:AMARker[1\|2\|3\|4]:FUNCtion:PDENsity\|NOISe:RESult?` | none | 7-46 |
| `CALCulate:AMARker[1\|2\|3\|4]:FUNCtion:PDENsity\|NOISe[:STATe]` | `OFF\|ON\|0\|1` | 7-46 |
| `CALCulate:AMARker[1\|2\|3\|4]:FUNCtion:PRESet` | none | 7-46 |
| `CALCulate:AMARker[1\|2\|3\|4]:MAXimum` | none | 7-47 |
| `CALCulate:AMARker[1\|2\|3\|4]:MAXimum:LEFT` | none | 7-47 |
| `CALCulate:AMARker[1\|2\|3\|4]:MAXimum:NEXT` | none | 7-47 |
| `CALCulate:AMARker[1\|2\|3\|4]:MAXimum:RIGHt` | none | 7-47 |
| `CALCulate:AMARker[1\|2\|3\|4]:MINimum` | none | 7-47 |
| `CALCulate:AMARker[1\|2\|3\|4]:MINimum:LEFT` | none | 7-47 |
| `CALCulate:AMARker[1\|2\|3\|4]:MINimum:NEXT` | none | 7-48 |
| `CALCulate:AMARker[1\|2\|3\|4]:MINimum:RIGHt` | none | 7-48 |
| `CALCulate:AMARker[1\|2\|3\|4][:STATe]` | `OFF\|ON\|0\|1` | 7-48 |
| `CALCulate:AMARker[1\|2\|3\|4]:TRACe` | `TRA\|TRB\|TRC\|TRD\|TRE\|TRF\|TRG` | 7-48 |
| `CALCulate:AMARker[1\|2\|3\|4]:X` | `<NRf>[M\|Hz]` | 7-48 |
| `CALCulate:AMARker[1\|2\|3\|4]:Y?` | none | 7-49 |

### Analysis Functions

| Command | Parameter | Page |
|---------|-----------|------|
| `CALCulate:ARESolution?` | `<Trace name>,[<start point>,<stop point>]` | 7-49 |
| `CALCulate:CATegory` | `SWTHresh\|SWENvelope\|SWRMs\|SWPKrms\|NOTCh\|DFBLd\|FPLD\|LED\|SMSR\|POWer\|PMD\|WDM\|NF\|FILPk\|FILBtm\|WFPeak\|WFBtm\|OSNR\|COLor` | 7-49 |
| `CALCulate:DATA?` | none | 7-50 |
| `CALCulate:CGAin?` | none | 7-50 |
| `CALCulate:CNF?` | none | 7-50 |
| `CALCulate:COLor?` | none | 7-50 |
| `CALCulate:CPOWers?` | none | 7-50 |
| `CALCulate:CSNR?` | none | 7-51 |
| `CALCulate:CWAVelengths?` | none | 7-51 |
| `CALCulate:DFBLd?` | none | 7-51 |
| `CALCulate:NCHannels?` | none | 7-51 |
| `CALCulate:OSLope?` | none | 7-52 |
| `CALCulate:DISPlay` | `0\|1\|2\|3\|4` | 7-52 |
| `CALCulate:GRAPh:LMARker:Y` | `1\|2,<NRf>[DB]` | 7-52 |
| `CALCulate[:IMMediate]` | none | 7-52 |
| `CALCulate:AUTO` | `OFF\|ON\|0\|1` | 7-52 |

### Line Markers

| Command | Parameter | Page |
|---------|-----------|------|
| `CALCulate:LMARker:AOFF` | none | 7-52 |
| `CALCulate:LMARker:SRANge` | `OFF\|ON\|0\|1` | 7-52 |
| `CALCulate:LMARker:SSPan` | none | 7-53 |
| `CALCulate:LMARker:SZSPan` | none | 7-53 |
| `CALCulate:LMARker:X` | `1\|2,<NRf>[M\|HZ]` | 7-53 |
| `CALCulate:LMARker:Y` | `3\|4,<NRf>[DBM/DB/%]` | 7-53 |

### Manual Markers

| Command | Parameter | Page |
|---------|-----------|------|
| `CALCulate:MARKer:AOFF` | none | 7-53 |
| `CALCulate:MARKer:AUTO` | `OFF\|ON\|0\|1` | 7-53 |
| `CALCulate:MARKer:FUNCtion:FORMat` | `OFFSet\|SPACing\|0\|1` | 7-53 |
| `CALCulate:MARKer:FUNCtion:UPDate` | `OFF\|ON\|0\|1` | 7-53 |
| `CALCulate:MARKer:MAXimum` | none | 7-53 |
| `CALCulate:MARKer:MAXimum:LEFT` | none | 7-54 |
| `CALCulate:MARKer:MAXimum:NEXT` | none | 7-54 |
| `CALCulate:MARKer:MAXimum:RIGHt` | none | 7-54 |
| `CALCulate:MARKer:MAXimum:SCENter` | none | 7-54 |
| `CALCulate:MARKer:MAXimum:SCENter:AUTO` | `OFF\|ON\|0\|1` | 7-54 |
| `CALCulate:MARKer:MAXimum:SRLevel` | none | 7-54 |
| `CALCulate:MARKer:MAXimum:SRLevel:AUTO` | `OFF\|ON\|0\|1` | 7-54 |
| `CALCulate:MARKer:MAXimum:SZCenter` | none | 7-54 |
| `CALCulate:MARKer:MINimum` | none | 7-54 |
| `CALCulate:MARKer:MINimum:LEFT` | none | 7-54 |
| `CALCulate:MARKer:MINimum:NEXT` | none | 7-54 |
| `CALCulate:MARKer:MINimum:RIGHt` | none | 7-55 |
| `CALCulate:MARKer:MSEarch` | `OFF\|ON\|0\|1` | 7-55 |
| `CALCulate:MARKer:MSEarch:SORT` | `WAVelength\|LEVel\|0\|1` | 7-55 |
| `CALCulate:MARKer:MSEarch:THResh` | `<NRf>[DB]` | 7-55 |
| `CALCulate:MARKer:SCENter` | none | 7-55 |
| `CALCulate:MARKer:SRLevel` | none | 7-55 |
| `CALCulate:MARKer[:STATe]` | `<marker>,OFF\|ON\|0\|1` | 7-55 |
| `CALCulate:MARKer:SZCenter` | none | 7-56 |
| `CALCulate:MARKer:UNIT` | `WAVelength\|FREQuency\|WNUMber` | 7-56 |
| `CALCulate:MARKer:X` | `<marker>,<NRf>[M\|HZ]` | 7-56 |
| `CALCulate:MARKer:Y?` | `<marker>` | 7-56 |

### Math Operations

| Command | Parameter | Page |
|---------|-----------|------|
| `CALCulate:MATH:TRC` | `A-B(LOG)\|B-A(LOG)\|A+B(LOG)\|A+B(LIN)\|A-B(LIN)\|B-A(LIN)\|1-K(A/B)\|1-K(B/A)` | 7-56 |
| `CALCulate:MATH:TRC:K` | `<NRf>` | 7-57 |
| `CALCulate:MATH:TRF` | `C-D(LOG)\|D-C(LOG)\|C+D(LOG)\|D-E(LOG)\|E-D(LOG)\|D+E(LOG)\|C+D(LIN)\|C-D(LIN)\|D-C(LIN)\|D+E(LIN)\|D-E(LIN)\|E-D(LIN)\|PWRNBWA\|PWRNBWB\|PWRNBWC\|PWRNBWD\|PWRNBWE` | 7-57 |
| `CALCulate:MATH:TRF:PNBW:BWIDth` | `<NRf>[M]` | 7-57 |
| `CALCulate:MATH:TRG` | `C-F(LOG)\|F-C(LOG)\|C+F(LOG)\|E-F(LOG)\|F-E(LOG)\|E+F(LOG)\|C+F(LIN)\|C-F(LIN)\|F-C(LIN)\|E+F(LIN)\|E-F(LIN)\|F-E(LIN)\|NORMA\|NORMB\|NORMC\|CVFTA\|CVFTB\|CVFTC\|MKRFT\|PKCVFTA\|PKCVFTB\|PKCVFTC` | 7-57 |
| `CALCulate:MATH:TRG:CVFT:FALGo` | `GAUSS\|LORENz\|3RD\|4TH\|5TH\|0\|1\|2\|3\|4` | 7-57 |
| `CALCulate:MATH:TRG:CVFT:OPARea` | `ALL\|INL1-L2\|OUTL1-L2\|0\|1\|2` | 7-58 |
| `CALCulate:MATH:TRG:CVFT:THResh` | `<integer>[DB]` | 7-58 |
| `CALCulate:MATH:TRG:PCVFt:THResh` | `<integer>[DB]` | 7-58 |

### Analysis Parameters

| Command | Parameter | Page |
|---------|-----------|------|
| `CALCulate:PARameter[:CATegory]:DFBLd` | `<item>,<parameter name>,<data>` | 7-58 |
| `CALCulate:PARameter[:CATegory]:FILBtm` | `<item>,<parameter name>,<data>` | 7-59 |
| `CALCulate:PARameter[:CATegory]:FILPk` | `<item>,<parameter name>,<data>` | 7-59 |
| `CALCulate:PARameter[:CATegory]:FPLD` | `<item>,<parameter name>,<data>` | 7-60 |
| `CALCulate:PARameter[:CATegory]:LED` | `<item>,<parameter name>,<data>` | 7-60 |
| `CALCulate:PARameter[:CATegory]:NF:AALGo` | `AFIX\|MFIX\|ACENter\|MCENter\|0\|1\|2\|3` | 7-61 |
| `CALCulate:PARameter[:CATegory]:NF:FALGo` | `LINear\|GAUSs\|LORenz\|3RD\|4TH\|5TH\|0\|1\|2\|3\|4\|5` | 7-61 |
| `CALCulate:PARameter[:CATegory]:NF:FARea` | `<NRf>[M]` | 7-61 |
| `CALCulate:PARameter[:CATegory]:NF:IOFFset` | `<NRf>[DB]` | 7-61 |
| `CALCulate:PARameter[:CATegory]:NF:IRANge` | `<NRf>` | 7-61 |
| `CALCulate:PARameter[:CATegory]:NF:MARea` | `<NRf>[M]` | 7-62 |
| `CALCulate:PARameter[:CATegory]:NF:MDIFf` | `<NRf>[DB]` | 7-62 |
| `CALCulate:PARameter[:CATegory]:NF:OOFFset` | `<NRf>[DB]` | 7-62 |
| `CALCulate:PARameter[:CATegory]:NF:PDISplay` | `OFF\|ON\|0\|1` | 7-62 |
| `CALCulate:PARameter[:CATegory]:NF:TH` | `<NRf>[DB]` | 7-62 |
| `CALCulate:PARameter[:CATegory]:NF:RBWidth` | `MEASURED\|CAL\|0\|1` | 7-62 |
| `CALCulate:PARameter[:CATegory]:NF:SNOise` | `OFF\|ON\|0\|1` | 7-63 |
| `CALCulate:PARameter[:CATegory]:NF:SPOWer` | `PEAK\|INTegral\|0\|1` | 7-63 |
| `CALCulate:PARameter[:CATegory]:NOTCh:K` | `<NRf>` | 7-63 |
| `CALCulate:PARameter[:CATegory]:NOTCh:TH` | `<NRf>[DB]` | 7-63 |
| `CALCulate:PARameter[:CATegory]:NOTCh:TYPE` | `PEAK\|BOTTom\|0\|1` | 7-63 |
| `CALCulate:PARameter[:CATegory]:PMD:TH` | `<NRf>[DB]` | 7-63 |
| `CALCulate:PARameter[:CATegory]:POWer:OFFSet` | `<NRf>[DB]` | 7-64 |
| `CALCulate:PARameter[:CATegory]:SMSR:MASK` | `<NRf>[M]` | 7-64 |
| `CALCulate:PARameter[:CATegory]:SMSR:MODE` | `SMSR1\|SMSR2\|SMSR3\|SMSR4` | 7-64 |
| `CALCulate:PARameter[:CATegory]:SWENvelope:K` | `<NRf>` | 7-64 |
| `CALCulate:PARameter[:CATegory]:SWENvelope:TH1` | `<NRf>[DB]` | 7-64 |
| `CALCulate:PARameter[:CATegory]:SWENvelope:TH2` | `<NRf>[DB]` | 7-64 |
| `CALCulate:PARameter[:CATegory]:SWPKrms:K` | `<NRf>` | 7-64 |
| `CALCulate:PARameter[:CATegory]:SWPKrms:TH` | `<NRf>[DB]` | 7-65 |
| `CALCulate:PARameter[:CATegory]:SWRMs:K` | `<NRf>` | 7-65 |
| `CALCulate:PARameter[:CATegory]:SWRMs:TH` | `<NRf>[DB]` | 7-65 |
| `CALCulate:PARameter[:CATegory]:SWTHresh:K` | `<NRf>` | 7-65 |
| `CALCulate:PARameter[:CATegory]:SWTHresh:MFIT` | `OFF\|ON\|0\|1` | 7-65 |
| `CALCulate:PARameter[:CATegory]:SWTHresh:TH` | `<NRf>[DB]` | 7-65 |
| `CALCulate:PARameter[:CATegory]:WDM:DMASk` | `<NRf>[DB]` | 7-66 |
| `CALCulate:PARameter[:CATegory]:WDM:DTYPe` | `ABSolute\|RELative\|MDRIft\|GDRIft\|0\|1\|2\|3` | 7-66 |
| `CALCulate:PARameter[:CATegory]:WDM:DUAL` | `OFF\|ON\|0\|1` | 7-66 |
| `CALCulate:PARameter[:CATegory]:WDM:FALGo` | `LINear\|GAUSs\|LORenz\|3RD\|4TH\|5TH\|0\|1\|2\|3\|4\|5` | 7-66 |
| `CALCulate:PARameter[:CATegory]:WDM:IRANge` | `<NRf>` | 7-67 |
| `CALCulate:PARameter[:CATegory]:WDM:MARea` | `<NRf>[M]` | 7-67 |
| `CALCulate:PARameter[:CATegory]:WDM:MDIFf` | `<NRf>[DB]` | 7-67 |
| `CALCulate:PARameter[:CATegory]:WDM:MMReset` | None | 7-67 |
| `CALCulate:PARameter[:CATegory]:WDM:NALGo` | `AFIX\|MFIX\|ACENter\|MCENter\|PIT\|0\|1\|2\|3\|4` | 7-67 |
| `CALCulate:PARameter[:CATegory]:WDM:NARea` | `<NRf>[M]` | 7-67 |
| `CALCulate:PARameter[:CATegory]:WDM:NBW` | `<NRf>[M]` | 7-67 |
| `CALCulate:PARameter[:CATegory]:WDM:OSLope` | `OFF\|ON\|0\|1` | 7-68 |
| `CALCulate:PARameter[:CATegory]:WDM:PDISplay` | `OFF\|ON\|0\|1` | 7-68 |
| `CALCulate:PARameter[:CATegory]:WDM:RCH` | `<integer>` | 7-68 |
| `CALCulate:PARameter[:CATegory]:WDM:RELation` | `OFFSet\|SPACing\|0\|1` | 7-68 |
| `CALCulate:PARameter[:CATegory]:WDM:SPOWer` | `PEAK\|INTegral\|0\|1` | 7-68 |
| `CALCulate:PARameter[:CATegory]:WDM:TH` | `<NRf>[DB]` | 7-68 |
| `CALCulate:PARameter[:CATegory]:WFBottom` | `<item>,<parameter name>,<data>` | 7-69 |
| `CALCulate:PARameter[:CATegory]:WFPeak` | `<item>,<parameter name>,<data>` | 7-69 |
| `CALCulate:PARameter:COMMON:MDIFf` | `<NRf>[DB]` | 7-69 |

---

## CALibration

| Command | Parameter | Page |
|---------|-----------|------|
| `CALibration:ALIGn[:IMMediate]` | none | 7-70 |
| `CALibration:ALIGn:EXTernal[:IMMediate]` | none | 7-70 |
| `CALibration:ALIGn:INTernal[:IMMediate]` | none | 7-70 |
| `CALibration:BANDwidth\|BWIDth[:IMMediate]` | none | 7-70 |
| `CALibration:BANDwidth\|BWIDth:INITialize` | none | 7-70 |
| `CALibration:BANDwidth\|BWIDth:WAVelength?` | none | 7-70 |
| `CALibration:POWer:OFFSet:TABLe` | `<integer>,<NRf>[DB]` | 7-70 |
| `CALibration:WAVelength:EXTernal[:IMMediate]` | none | 7-71 |
| `CALibration:WAVelength:EXTernal:SOURce` | `LASEr\|GASCell\|EMISsion` | 7-71 |
| `CALibration:WAVelength:EXTernal:WAVelength` | `<NRf>M` | 7-71 |
| `CALibration:WAVelength:INTernal[:IMMediate]` | none | 7-71 |
| `CALibration:WAVelength:OFFSet:TABLe` | `<integer>,<NRf>` | 7-71 |
| `CALibration:ZERO[:AUTO]` | `OFF\|ON\|0\|1\|ONCE` | 7-72 |
| `CALibration:ZERO:INTerval` | `<integer>` | 7-72 |
| `CALibration:ZERO:STATus?` | none | 7-72 |

---

## DISPlay

| Command | Parameter | Page |
|---------|-----------|------|
| `DISPlay:COLor` | `0\|1\|2\|3\|4\|5` | 7-72 |
| `DISPlay[:WINDow]` | `OFF\|ON\|0\|1` | 7-72 |
| `DISPlay:OVIew:POSition` | `OFF\|LEFT\|RIGHt\|0\|1\|2` | 7-72 |
| `DISPlay:OVIew:SIZE` | `LARGe\|SMALl\|0\|1` | 7-72 |
| `DISPlay:SPLIt` | `OFF\|ON\|0\|1` | 7-73 |
| `DISPlay:HOLD:LOWer` | `OFF\|ON\|0\|1` | 7-73 |
| `DISPlay:HOLD:UPPer` | `OFF\|ON\|0\|1` | 7-73 |
| `DISPlay:POSition` | `<trace name>,UP\|LOW\|0\|1` | 7-73 |
| `DISPlay:TEXT:CLEar` | none | 7-73 |
| `DISPlay:TEXT:DATA` | `<"string">` | 7-73 |
| `DISPlay:TRACe:X[:SCALe]:CENTer` | `<NRf>[M\|HZ]` | 7-73 |
| `DISPlay:TRACe:X[:SCALe]:INITialize` | none | 7-73 |
| `DISPlay:TRACe:X[:SCALe]:SMSCale` | none | 7-74 |
| `DISPlay:TRACe:X[:SCALe]:SPAN` | `<NRf>[M\|HZ]` | 7-74 |
| `DISPlay:TRACe:X[:SCALe]:SRANge` | `OFF\|ON\|0\|1` | 7-74 |
| `DISPlay:TRACe:X[:SCALe]:STARt` | `<NRf>[M\|HZ]` | 7-74 |
| `DISPlay:TRACe:X[:SCALe]:STOP` | `<NRf>[M\|HZ]` | 7-74 |
| `DISPlay:TRACe:Y:NMASk` | `<NRf>DB` | 7-74 |
| `DISPlay:TRACe:Y:TYPE` | `VERTical\|HORizontal\|0\|1` | 7-75 |
| `DISPlay:TRACe:Y[:SCALe]:DNUMber` | `8\|10\|12` | 7-75 |
| `DISPlay:TRACe:Y1[:SCALe]:BLEVel` | `<NRf>[W\|MW\|UW\|NW]` | 7-75 |
| `DISPlay:TRACe:Y1[:SCALe]:PDIVision` | `<NRf>[DB]` | 7-75 |
| `DISPlay:TRACe:Y1[:SCALe]:RLEVel` | `<NRf>[DBM\|W]` | 7-75 |
| `DISPlay:TRACe:Y1[:SCALe]:RPOSition` | `<integer>[DIV]` | 7-76 |
| `DISPlay:TRACe:Y1[:SCALe]:SPACing` | `LOGarithmic\|LINear\|0\|1` | 7-76 |
| `DISPlay:TRACe:Y1[:SCALe]:UNIT` | `DBM\|W\|DBM/NM\|W/NM\|0\|1\|2\|3` | 7-76 |
| `DISPlay:TRACe:Y2[:SCALe]:AUTO` | `OFF\|ON\|0\|1` | 7-76 |
| `DISPlay:TRACe:Y2[:SCALe]:LENGth` | `<NRf>[KM]` | 7-76 |
| `DISPlay:TRACe:Y2[:SCALe]:OLEVel` | `<NRf>[DB\|DB/KM]` | 7-76 |
| `DISPlay:TRACe:Y2[:SCALe]:PDIVision` | `<NRf>[DB\|DB\|KM\|%]` | 7-77 |
| `DISPlay:TRACe:Y2[:SCALe]:RPOSition` | `<integer>[DIV]` | 7-77 |
| `DISPlay:TRACe:Y2[:SCALe]:SMINimum` | `<NRf>[%]` | 7-77 |
| `DISPlay:TRACe:Y2[:SCALe]:UNIT` | `DB\|LINear\|DB/KM\|%\|0\|1\|2\|3` | 7-77 |

---

## FORMat

| Command | Parameter | Page |
|---------|-----------|------|
| `FORMat[:DATA]` | `REAL[,64\|,32]\|ASCii` | 7-78 |

---

## HCOPy

| Command | Parameter | Page |
|---------|-----------|------|
| `HCOPy:DESTination` | `INTernal\|FILE\|0\|2` | 7-78 |
| `HCOPy[:IMMediate]` | none | 7-78 |
| `HCOPy:FEED` | `[<integer>]` | 7-78 |
| `HCOPy:FUNCtion:CALCulate:LIST` | none | 7-78 |
| `HCOPy:FUNCtion:MARKer:LIST` | none | 7-78 |

---

## INITiate

| Command | Parameter | Page |
|---------|-----------|------|
| `INITiate[:IMMediate]` | none | 7-79 |
| `INITiate:SMODe` | `SINGle\|REPeat\|AUTO\|SEGment\|1\|2\|3\|4` | 7-79 |

---

## MEMory

| Command | Parameter | Page |
|---------|-----------|------|
| `MEMory:CLEar` | `<integer>` | 7-79 |
| `MEMory:EMPty?` | `<integer>` | 7-79 |
| `MEMory:LOAD` | `<integer>,<trace name>` | 7-79 |
| `MEMory:STORe` | `<integer>,<trace name>` | 7-79 |

---

## MMEMory

### File Operations

| Command | Parameter | Page |
|---------|-----------|------|
| `MMEMory:ANAMe` | `NUMBer\|DATE` | 7-80 |
| `MMEMory:CATalog?` | `[INTernal\|EXTernal]` | 7-80 |
| `MMEMory:CDIRectory` | `<"directory name">` | 7-80 |
| `MMEMory:CDRive` | `INTernal\|EXTernal` | 7-80 |
| `MMEMory:COPY` | `<"source file name">[,INTernal\|EXTernal],<"destination file name">[,INTernal\|EXTernal]` | 7-80 |
| `MMEMory:DATA?` | `<"file name">[,INTernal\|EXTernal]` | 7-80 |
| `MMEMory:DELete` | `<"file name">[,INTernal\|EXTernal]` | 7-80 |
| `MMEMory:MDIRectory` | `<"directory name">[,INTernal\|EXTernal]` | 7-81 |
| `MMEMory:REMove` | None | 7-81 |
| `MMEMory:REName` | `<"new file name">,<"old file name">[,INTernal\|EXTernal]` | 7-82 |

### Load Commands

| Command | Parameter | Page |
|---------|-----------|------|
| `MMEMory:LOAD:ATRace` | `<"file name">[,INTernal\|EXTernal]` | 7-81 |
| `MMEMory:LOAD:DLOGing` | `<"file name">[,INTernal\|EXTernal]` | 7-81 |
| `MMEMory:LOAD:MEMory` | `<integer>,<"filename">[,INTernal\|EXTernal]` | 7-81 |
| `MMEMory:LOAD:PROGram` | `<integer>,<"filename">[,INTernal\|EXTernal]` | 7-81 |
| `MMEMory:LOAD:SETTing` | `<"filename">[,INTernal\|EXTernal]` | 7-81 |
| `MMEMory:LOAD:TEMPlate` | `<template>,<"filename">[,INTernal\|EXTernal]` | 7-81 |
| `MMEMory:LOAD:TRACe` | `<trace name>,<"filename">[,INTernal\|EXTernal]` | 7-81 |

### Store Commands

| Command | Parameter | Page |
|---------|-----------|------|
| `MMEMory:STORe:ARESult` | `<"filename">[,INTernal\|EXTernal]` | 7-82 |
| `MMEMory:STORe:ATRace` | `<"file name">[,INTernal\|EXTernal]` | 7-82 |
| `MMEMory:STORe:DATA` | `<"filename">[,INTernal\|EXTernal]` | 7-82 |
| `MMEMory:STORe:DATA:ITEM` | `DATE\|LABel\|DATA\|CONDition\|TRACe,OFF\|ON\|0\|1` | 7-82 |
| `MMEMory:STORe:DATA:MODE` | `ADD\|OVER\|0\|1` | 7-82 |
| `MMEMory:STORe:DATA:TYPE` | `CSV\|DT\|0\|1` | 7-82 |
| `MMEMory:STORe:DLOGging` | `<"filename">[,INTernal\|EXTernal]` | 7-83 |
| `MMEMory:STORe:DLOGging:CSAVe` | `OFF\|ON\|0\|1` | 7-83 |
| `MMEMory:STORe:DLOGging:TSAVe` | `OFF\|ON\|0\|1` | 7-83 |
| `MMEMory:STORe:GRAPhics` | `B&W\|COLor\|PCOLor,BMP\|TIFF,<"filename">[,INTernal\|EXTernal]` | 7-83 |
| `MMEMory:STORe:MEMory` | `<integer>,BI\|CSV,<"filename">[,INTernal\|EXTernal]` | 7-83 |
| `MMEMory:STORe:PROGram` | `<integer>,<"filename">[,INTernal\|EXTernal]` | 7-83 |
| `MMEMory:STORe:SETTing` | `<"filename">[,INTernal\|EXTernal]` | 7-84 |
| `MMEMory:STORe:TEMPlate` | `<template>,<"filename">[,INTernal\|EXTernal]` | 7-84 |
| `MMEMory:STORe:TRACe` | `<trace name>,BIN\|CSV,<"filename">[,INTernal\|EXTernal]` | 7-84 |

---

## PROGram

| Command | Parameter | Page |
|---------|-----------|------|
| `PROGram:EXECute` | `<integer>` | 7-84 |

---

## SENSe

| Command | Parameter | Page |
|---------|-----------|------|
| `SENSe:AVERage:COUNt` | `<integer>` | 7-85 |
| `SENSe:BANDwidth\|BWIDth[:RESolution]` | `<NRf>[M\|Hz]` | 7-85 |
| `SENSe:CHOPper` | `OFF\|SWITch\|0\|2` | 7-85 |
| `SENSe:CORRection:LEVel:SHIFt` | `<NRf>[DB]` | 7-85 |
| `SENSe:CORRection:RVELocity:MEDium` | `AIR\|VACuum\|0\|1` | 7-85 |
| `SENSe:CORRection:WAVelength:SHIFt` | `<NRf>[M]` | 7-85 |
| `SENSe:SENSe` | `NHLD\|NAUT\|NORMal\|MID\|HIGH1\|HIGH2\|HIGH3\|0\|1\|6\|2\|3\|4\|5` | 7-85 |
| `SENSe:SETTing:CORRection` | `OFF\|ON\|0\|1\|2\|MODE1\|MODE2` | 7-86 |
| `SENSe:SETTing:FCONnetcor` | `NORMal\|ANGLed\|0\|1` | 7-86 |
| `SENSe:SETTing:FIBer` | `SMALl\|LARGe\|0\|1` | 7-86 |
| `SENSe:SETTing:SMOothing` | `OFF\|ON\|0\|1` | 7-86 |
| `SENSe:SWEep:POINts` | `<integer>` | 7-86 |
| `SENSe:SWEep:POINts:AUTO` | `OFF\|ON\|0\|1` | 7-86 |
| `SENSe:SWEep:SEGMent:POINts` | `<integer>` | 7-86 |
| `SENSe:SWEep:SPEed` | `1x\|2x\|0\|1` | 7-87 |
| `SENSe:SWEep:STEP` | `<NRf>[M]` | 7-87 |
| `SENSe:SWEep:TIME:0NM` | `<integer>[SEC]` | 7-87 |
| `SENSe:SWEep:TIME:INTerval` | `<integer>[SEC]` | 7-87 |
| `SENSe:SWEep:TLSSync` | `OFF\|ON\|0\|1` | 7-87 |
| `SENSe:WAVelength:CENTer` | `<NRf>[M\|HZ]` | 7-87 |
| `SENSe:WAVelength:SPAN` | `<NRf>[M\|HZ]` | 7-87 |
| `SENSe:WAVelength:SRANge` | `OFF\|ON\|0\|1` | 7-88 |
| `SENSe:WAVelength:STARt` | `<NRf>[M\|HZ]` | 7-88 |
| `SENSe:WAVelength:STOP` | `<NRf>[M\|HZ]` | 7-88 |

---

## STATus

### Operation Status

| Command | Parameter | Page |
|---------|-----------|------|
| `STATus:OPERation:CONDition?` | none | 7-88 |
| `STATus:OPERation:ENABle` | `<integer>` | 7-88 |
| `STATus:OPERation[:EVENt]?` | none | 7-88 |
| `STATus:OPERation:PRESet` | none | 7-88 |

### Questionable Status

| Command | Parameter | Page |
|---------|-----------|------|
| `STATus:QUEStionable:CONDition?` | none | 7-89 |
| `STATus:QUEStionable:ENABle` | `<integer>` | 7-89 |
| `STATus:QUEStionable[:EVENt]?` | none | 7-89 |

---

## SYSTem

### Buzzer

| Command | Parameter | Page |
|---------|-----------|------|
| `SYSTem:BUZZer:CLIC` | `OFF\|ON\|0\|1` | 7-89 |
| `SYSTem:BUZZer:WARNing` | `OFF\|ON\|0\|1` | 7-89 |

### Communication

| Command | Parameter | Page |
|---------|-----------|------|
| `SYSTem:COMMunicate:CFORmat` | `AQ6317\|AQ6370\|AQ6370C\|AQ6370D\|AQ6373\|AQ6373B\|AQ6375\|AQ6375B\|0\|1` | 7-89 |
| `SYSTem:COMMunicate:GP-IB2:ADDRess` | `<integer>` | 7-90 |
| `SYSTem:COMMunicate:GP-IB2:SCONtroller` | `OFF\|ON\|0\|1` | 7-90 |
| `SYSTem:COMMunicate:GP-IB2:TLS:ADDRess` | `<integer>` | 7-90 |
| `SYSTem:COMMunicate:LOCKout` | `OFF\|ON\|0\|1` | 7-90 |
| `SYSTem:COMMunicate:RMONitor` | `OFF\|ON\|0\|1` | 7-91 |

### Date and Time

| Command | Parameter | Page |
|---------|-----------|------|
| `SYSTem:DATE` | `yyyy,mm,dd` | 7-91 |
| `SYSTem:TIME` | `hh,mm,ss` | 7-93 |

### Display

| Command | Parameter | Page |
|---------|-----------|------|
| `SYSTem:DISPlay:TRANsparent` | `OFF\|ON\|0\|1` | 7-91 |
| `SYSTem:DISPlay:UNCal` | `OFF\|ON\|0\|1` | 7-91 |

### Error

| Command | Parameter | Page |
|---------|-----------|------|
| `SYSTem:ERRor[:NEXT]?` | none | 7-91 |

### Grid

| Command | Parameter | Page |
|---------|-----------|------|
| `SYSTem:GRID` | `12.5GHZ\|25GHz\|50GHZ\|100GHZ\|200GHZ\|CUSTom\|0\|1\|2\|3\|4\|5` | 7-91 |
| `SYSTem:GRID:CUSTom:CLEar:ALL` | none | 7-91 |
| `SYSTem:GRID:CUSTom:DELete` | `<grid number>` | 7-91 |
| `SYSTem:GRID:CUSTom:INSert` | `<NRf>[M\|HZ]` | 7-92 |
| `SYSTem:GRID:CUSTom:SPACing` | `<NRf>[GHZ]` | 7-92 |
| `SYSTem:GRID:CUSTom:STARt` | `<NRf>[M\|HZ]` | 7-92 |
| `SYSTem:GRID:CUSTom:STOP` | `<NRf>[M\|HZ]` | 7-92 |
| `SYSTem:GRID:REFerence` | `<NRf>[M\|HZ]` | 7-92 |

### System Information

| Command | Parameter | Page |
|---------|-----------|------|
| `SYSTem:INFormation?` | `0\|1` | 7-92 |
| `SYSTem:FSPeed?` | none | 7-93 |
| `SYSTem:VERSion?` | none | 7-93 |

### Other System Settings

| Command | Parameter | Page |
|---------|-----------|------|
| `SYSTem:OLOCK` | `OFF\|ON\|0\|1,<"password">` | 7-93 |
| `SYSTem:PRESet` | none | 7-93 |

---

## TRACe

### Trace Attributes

| Command | Parameter | Page |
|---------|-----------|------|
| `TRACe:ACTive` | `<trace name>` | 7-93 |
| `TRACe:ATTRibute[:<trace name>]` | `WRITe\|FIX\|MAX\|MIN\|RAVG\|CALC` | 7-93 |
| `TRACe:ATTRibute:RAVG[:<trace name>]` | `<integer>` | 7-94 |
| `TRACe:COPY` | `<source trace>,<destination trace>` | 7-94 |
| `TRACe:DELete` | `<trace name>` | 7-95 |
| `TRACe:DELete:ALL` | none | 7-95 |
| `TRACe:STATe[:<trace name>]` | `OFF\|ON\|0\|1` | 7-95 |

### Trace Data

| Command | Parameter | Page |
|---------|-----------|------|
| `TRACe[:DATA]:SNUMber?` | `<trace name>` | 7-94 |
| `TRACe[:DATA]:X?` | `<trace name>[,<start point>,<stop point>]` | 7-94 |
| `TRACe[:DATA]:Y?` | `<trace name>[,<start point>,<stop point>]` | 7-94 |
| `TRACe:PDENsity?` | `<trace name>,<NRF>[,<start point>,<stop point>]` | 7-95 |

### Template

| Command | Parameter | Page |
|---------|-----------|------|
| `TRACe:TEMPlate:DATA` | `<template>,<wavelength>,<level>` | 7-95 |
| `TRACe:TEMPlate:ADELete` | `<template>` | 7-96 |
| `TRACe:TEMPlate:ETYPe` | `<template>,NONE\|A\|B\|0\|1\|2` | 7-96 |
| `TRACe:TEMPlate:MODE` | `<template>,ABSolute\|RELative\|0\|1` | 7-96 |
| `TRACe:TEMPlate:DISPlay` | `<template>,OFF\|ON\|0\|1` | 7-96 |
| `TRACe:TEMPlate:GONogo` | `OFF\|ON\|0\|1` | 7-96 |
| `TRACe:TEMPlate:LEVel:SHIFt` | `<NRf>[DB]` | 7-96 |
| `TRACe:TEMPlate:RESult?` | none | 7-96 |
| `TRACe:TEMPlate:TTYPe` | `UPPer\|LOWer\|U&L\|0\|1\|2` | 7-97 |
| `TRACe:TEMPlate:WAVelength:SHIFt` | `<NRf>[M]` | 7-97 |

---

## TRIGger

| Command | Parameter | Page |
|---------|-----------|------|
| `TRIGger[:SEQuence]:DELay` | `<NRf>[S\|MS\|US]` | 7-97 |
| `TRIGger[:SEQuence]:GATE:TIMe` | `<NRf>[s]` | 7-97 |
| `TRIGger[:SEQuence]:GATE:LOGic` | `POSI\|NEGA\|0\|1` | 7-97 |
| `TRIGger[:SEQuence]:GATE:SLOPe` | `RISE\|FALL\|0\|1` | 7-98 |
| `TRIGger[:SEQuence]:GATE:STATe` | `OFF\|ON\|PHOLd\|0\|1\|2` | 7-98 |
| `TRIGger[:SEQuence]:INPut` | `ETRigger\|STRigger\|SENable\|0\|1\|2` | 7-98 |
| `TRIGger[:SEQuence]:OUTPut` | `OFF\|SSTatus\|0\|1` | 7-98 |
| `TRIGger[:SEQuence]:PHOLd:HTIMe` | `<NRf>[s]` | 7-98 |

---

## UNIT

| Command | Parameter | Page |
|---------|-----------|------|
| `UNIT:POWer:DIGit` | `1\|2\|3` | 7-99 |
| `UNIT:X` | `WAVelength\|FREQuency\|WNUMBer\|0\|1\|2` | 7-99 |

---

## Notes

- **Notation**:
  - `<integer>` : Integer value
  - `<NRf>` : Numeric representation format (float)
  - `[unit]` : Optional unit specifier
  - `option1|option2` : Alternative choices
  - `[:optional]` : Optional command segment
  - `[1|2|3|4]` : Array index or channel number

- **Trace names**: TRA, TRB, TRC, TRD, TRE, TRF, TRG

- All commands reference **Yokogawa AQ637x Manual pages 7-39 through 7-99**
