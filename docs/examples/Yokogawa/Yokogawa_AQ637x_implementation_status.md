# AQ637x Driver Command Implementation Status

## Summary Statistics

- **Manual commands tracked**: 336 SCPI commands (from `Yokogawa_AQ637x_command_list.md`)
- **Implemented manual commands**: 256
- **Not implemented manual commands**: 80
- **Overall implementation coverage**: 256 / 336 (76%)
- **Implemented commands with test coverage**: 256 / 256 (100%)

All subsystems are fully implemented and tested except the `CALCulate` spectral-analysis commands
(~80: analysis functions, the `PARameter:CATegory` configuration family, and trace `MATH`), which are
deliberately out of scope for this driver — see the [Not-Implemented (deferred)](#not-implemented-deferred)
section below.

> Notes:
> - Each row in `Yokogawa_AQ637x_command_list.md` is counted as one command. A command that carries a `?` query form (e.g. `DISPlay:COLor`) is counted once and covers both set and query, matching the way the driver exposes a single read/write `Parameter`.

---

## Implemented Subsystems

### COMMON Commands (IEEE 488.2)

| Command(s)      | Description                                   | Status        | Driver implementation      | Test coverage                  |
|-----------------|-----------------------------------------------|---------------|----------------------------|--------------------------------|
| `*CLS`          | Clear status registers and queues             | ✅ Implemented | `clear_status()`           | ✅ `test_clear_status`          |
| `*ESE` / `*ESE?`| Standard event status enable register         | ✅ Implemented | `event_status_enable`      | ✅ `test_event_status_enable`   |
| `*ESR?`         | Standard event status register (read & clear) | ✅ Implemented | `event_status_register`    | ✅ `test_event_status_register` |
| `*IDN?`         | Instrument identification                     | ✅ Implemented | `get_idn()` (inherited)    | ✅ `test_idn`                   |
| `*OPC` / `*OPC?`| Operation complete flag                       | ✅ Implemented | `operation_complete`       | ✅ `test_operation_complete`    |
| `*RST`          | Reset instrument to default state             | ✅ Implemented | `reset()`                  | ✅ `test_reset`                 |
| `*SRE` / `*SRE?`| Service request enable register               | ✅ Implemented | `service_request_enable`   | ✅ `test_service_request_enable`|
| `*STB?`         | Status byte register                          | ✅ Implemented | `status_byte`              | ✅ `test_status_byte`           |
| `*TRG`          | Force a single trigger sweep                  | ✅ Implemented | `trigger()`                | ✅ `test_trigger`               |
| `*TST?`         | Run self-test, return status code             | ✅ Implemented | `self_test`                | ✅ `test_self_test`             |
| `*WAI`          | Wait for all pending commands to complete     | ✅ Implemented | `wait()`                   | ✅ `test_wait`                  |

**COMMON Summary**: 14 / 14 implemented

### ABORt

| Command(s) | Description                                    | Status        | Driver implementation | Test coverage    |
|------------|------------------------------------------------|---------------|-----------------------|------------------|
| `ABORt`    | Stop measurement/calibration operations        | ✅ Implemented | `stop()`              | ✅ `test_stop`   |

**ABORt Summary**: 1 / 1 implemented

### DISPlay

| Command(s)                            | Description                                    | Status            | Driver implementation          | Test coverage                        |
|---------------------------------------|------------------------------------------------|-------------------|--------------------------------|--------------------------------------|
| `DISPlay:COLor`                       | Screen color mode                              | ✅ Implemented     | `display_color`                | ✅ `test_display_color`               |
| `DISPlay[:WINDow]`                    | Enable/disable the display                     | ✅ Implemented     | `display_enabled`              | ✅ `test_display_enabled`             |
| `DISPlay:OVIew:POSition`              | Overview display position                      | ✅ Implemented     | `display_overview_position`    | ✅ `test_display_overview_position`   |
| `DISPlay:OVIew:SIZE`                  | Overview display size                          | ✅ Implemented     | `display_overview_size`        | ✅ `test_display_overview_size`       |
| `DISPlay:SPLIt`                       | Split-screen display                           | ✅ Implemented     | `display_split`                | ✅ `test_display_split`               |
| `DISPlay:HOLD:LOWer`                  | Hold lower trace in split screen               | ✅ Implemented     | `display_split_hold_lower`     | ✅ `test_display_split_hold_lower`    |
| `DISPlay:HOLD:UPPer`                  | Hold upper trace in split screen               | ✅ Implemented     | `display_split_hold_upper`     | ✅ `test_display_split_hold_upper`    |
| `DISPlay:POSition`                    | Trace up/low screen position                   | ✅ Implemented     | `display_position()`           | ✅ `test_phase4_action_command`       |
| `DISPlay:TEXT:CLEar`                  | Clear all display text labels                  | ✅ Implemented     | `display_text_clear()`         | ✅ `test_display_text_clear`          |
| `DISPlay:TEXT:DATA`                   | Display text label                             | ✅ Implemented     | `display_text_data`            | ✅ `test_display_text_data`           |
| `DISPlay:TRACe:X[:SCALe]:CENTer`      | X-axis center                                  | ✅ Implemented     | `display_trace_x_center`       | ✅ `test_display_trace_x_center`      |
| `DISPlay:TRACe:X[:SCALe]:INITialize`  | Initialize X-axis scale                        | ✅ Implemented     | `display_trace_x_initialize()` | ✅ `test_display_trace_x_initialize`  |
| `DISPlay:TRACe:X[:SCALe]:SMSCale`     | Set display scale to measurement scale         | ✅ Implemented     | `display_trace_x_smscale()`    | ✅ `test_display_trace_x_smscale`     |
| `DISPlay:TRACe:X[:SCALe]:SPAN`        | X-axis span                                    | ✅ Implemented     | `display_trace_x_span`         | ✅ `test_display_trace_x_span`        |
| `DISPlay:TRACe:X[:SCALe]:SRANge`      | Limit analysis range to X-axis scale           | ✅ Implemented     | `display_trace_x_srange`       | ✅ `test_display_trace_x_srange`      |
| `DISPlay:TRACe:X[:SCALe]:STARt`       | X-axis start                                   | ✅ Implemented     | `display_trace_x_start`        | ✅ `test_display_trace_x_start`       |
| `DISPlay:TRACe:X[:SCALe]:STOP`        | X-axis stop                                    | ✅ Implemented     | `display_trace_x_stop`         | ✅ `test_display_trace_x_stop`        |
| `DISPlay:TRACe:Y:NMASk`               | Y-axis display mask threshold                  | ✅ Implemented     | `display_trace_y_nmask`        | ✅ `test_display_trace_y_nmask`       |
| `DISPlay:TRACe:Y:TYPE`                | Y-axis mask display type                       | ✅ Implemented     | `display_trace_y_nmask_type` ¹ | ✅ `test_display_trace_y_nmask_type`  |
| `DISPlay:TRACe:Y[:SCALe]:DNUMber`     | Number of Y-axis divisions                     | ✅ Implemented     | `display_trace_y_dnumber`      | ✅ `test_display_trace_y_dnumber`     |
| `DISPlay:TRACe:Y1[:SCALe]:BLEVel`     | Y1 base level (linear scale)                   | ✅ Implemented     | `display_trace_y1_blevel`      | ✅ `test_display_trace_y1_blevel`     |
| `DISPlay:TRACe:Y1[:SCALe]:PDIVision`  | Y1 level scale per division                    | ✅ Implemented     | `display_trace_y1_pdivision`   | ✅ `test_display_trace_y1_pdivision`  |
| `DISPlay:TRACe:Y1[:SCALe]:RLEVel`     | Y1 reference level                             | ✅ Implemented     | `display_trace_y1_rlevel`      | ✅ `test_display_trace_y1_rlevel`     |
| `DISPlay:TRACe:Y1[:SCALe]:RPOSition`  | Y1 reference level position                    | ✅ Implemented     | `display_trace_y1_rposition`   | ✅ `test_display_trace_y1_rposition`  |
| `DISPlay:TRACe:Y1[:SCALe]:SPACing`    | Y1 scale spacing (log/linear)                  | ✅ Implemented     | `display_trace_y1_spacing`     | ✅ `test_display_trace_y1_spacing`    |
| `DISPlay:TRACe:Y1[:SCALe]:UNIT`       | Y1 unit                                        | ✅ Implemented     | `display_trace_y1_unit`        | ✅ `test_display_trace_y1_unit`       |
| `DISPlay:TRACe:Y2[:SCALe]:AUTO`       | Y2 automatic scaling                           | ✅ Implemented     | `display_trace_y2_auto`        | ✅ `test_display_trace_y2_auto`       |
| `DISPlay:TRACe:Y2[:SCALe]:LENGth`     | Y2 optical fiber length (dB/km)                | ✅ Implemented     | `display_trace_y2_length`      | ✅ `test_display_trace_y2_length`     |
| `DISPlay:TRACe:Y2[:SCALe]:OLEVel`     | Y2 offset level                                | ✅ Implemented     | `display_trace_y2_olevel`      | ✅ `test_display_trace_y2_olevel`     |
| `DISPlay:TRACe:Y2[:SCALe]:PDIVision`  | Y2 scale per division                          | ✅ Implemented     | `display_trace_y2_pdivision`   | ✅ `test_display_trace_y2_pdivision`  |
| `DISPlay:TRACe:Y2[:SCALe]:RPOSition`  | Y2 reference level position                    | ✅ Implemented     | `display_trace_y2_rposition`   | ✅ `test_display_trace_y2_rposition`  |
| `DISPlay:TRACe:Y2[:SCALe]:SMINimum`   | Y2 scale minimum (linear/% mode)               | ✅ Implemented     | `display_trace_y2_sminimum`    | ✅ `test_display_trace_y2_sminimum`   |
| `DISPlay:TRACe:Y2[:SCALe]:UNIT`       | Y2 unit                                        | ✅ Implemented     | `display_trace_y2_unit`        | ✅ `test_display_trace_y2_unit`       |

¹ Driver issues `:DISPlay:TRACe:Y:NMASk:TYPE`, which differs slightly from the manual's `DISPlay:TRACe:Y:TYPE` — verify against target firmware.

**DISPlay Summary**: 33 / 33 implemented

### FORMat

| Command(s)       | Description                        | Status        | Driver implementation | Test coverage       |
|------------------|------------------------------------|---------------|-----------------------|---------------------|
| `FORMat[:DATA]`  | Data transfer format (ASCII/REAL)  | ✅ Implemented | `format_data`         | ✅ `test_format_data`|

**FORMat Summary**: 1 / 1 implemented

### INITiate

| Command(s)              | Description                       | Status        | Driver implementation                            | Test coverage                       |
|-------------------------|-----------------------------------|---------------|--------------------------------------------------|-------------------------------------|
| `INITiate[:IMMediate]`  | Start a sweep                     | ✅ Implemented | `immediate()`, `auto()`, `repeat()`, `single()`  | ✅ indirectly via `test_single/repeat/auto` |
| `INITiate:SMODe`        | Sweep mode (single/repeat/auto/segment) | ✅ Implemented | `sweep_mode`                              | ✅ `test_sweep_mode`                 |

**INITiate Summary**: 2 / 2 implemented

### SENSe

| Command(s)                          | Description                                | Status            | Driver implementation                | Test coverage                             |
|-------------------------------------|--------------------------------------------|-------------------|--------------------------------------|-------------------------------------------|
| `SENSe:AVERage:COUNt`               | Averages per measured point                | ✅ Implemented     | `sense_average_count`                | ✅ `test_sense_average_count`              |
| `SENSe:BANDwidth[:RESolution]`      | Measurement resolution (bandwidth)         | ✅ Implemented     | `sense_bandwidth_resolution`         | ✅ `test_sense_bandwidth_resolution`       |
| `SENSe:CHOPper`                     | Chopper mode                               | ✅ Implemented     | `sense_chopper`                      | ✅ `test_sense_chopper`                    |
| `SENSe:CORRection:LEVel:SHIFt`      | Level correction offset                    | ✅ Implemented     | `sense_correction_level_shift`       | ✅ `test_sense_correction_level_shift`     |
| `SENSe:CORRection:RVELocity:MEDium` | Wavelength reference medium (air/vacuum)   | ✅ Implemented     | `sense_correction_rvelocity_medium`  | ✅ `test_sense_correction_rvelocity_medium`|
| `SENSe:CORRection:WAVelength:SHIFt` | Wavelength correction offset               | ✅ Implemented     | `sense_correction_wavelength_shift`  | ✅ `test_sense_correction_wavelength_shift`|
| `SENSe:SENSe`                       | Measurement sensitivity setting            | ✅ Implemented     | `sense_sensitivity`                  | ✅ `test_sense_sensitivity`                |
| `SENSe:SETTing:CORRection`          | Resolution correction function             | ✅ Implemented     | `sense_setting_correction`           | ✅ `test_sense_setting_correction`         |
| `SENSe:SETTing:FCONnector`          | Fiber connector mode (normal/angled)       | ✅ Implemented     | `sense_setting_fconnector`           | ✅ `test_sense_setting_fconnector`         |
| `SENSe:SETTing:FIBer`               | Fiber core size (AQ6373/AQ6373B only)      | ✅ Implemented     | `sense_setting_fiber` ²              | ✅ `test_sense_setting_fiber` *(AQ6373 sim device)* |
| `SENSe:SETTing:SMOothing`           | Smoothing on/off                           | ✅ Implemented     | `sense_setting_smoothing`            | ✅ `test_sense_setting_smoothing`          |
| `SENSe:SWEep:POINts`                | Number of samples per sweep                | ✅ Implemented     | `sense_sweep_points`                 | ✅ `test_sense_sweep_points`               |
| `SENSe:SWEep:POINts:AUTO`           | Auto sweep points                          | ✅ Implemented     | `sense_sweep_points_auto`            | ✅ `test_sense_sweep_points_auto`          |
| `SENSe:SWEep:SEGMent:POINts`        | Sampling points per segment sweep          | ✅ Implemented     | `sense_sweep_segment_points`         | ✅ `test_sense_sweep_segment_points`       |
| `SENSe:SWEep:SPEed`                 | Sweep speed (1x/2x)                        | ✅ Implemented     | `sense_sweep_speed`                  | ✅ `test_sense_sweep_speed`                |
| `SENSe:SWEep:STEP`                  | Sampling interval                          | ✅ Implemented     | `sense_sweep_step`                   | ✅ `test_sense_sweep_step`                 |
| `SENSe:SWEep:TIME:0NM`              | Measurement time for 0-nm sweep            | ✅ Implemented     | `sense_sweep_time_0nm`               | ✅ `test_sense_sweep_time_0nm`             |
| `SENSe:SWEep:TIME:INTerval`         | Time between consecutive sweeps            | ✅ Implemented     | `sense_sweep_time_interval`          | ✅ `test_sense_sweep_time_interval`        |
| `SENSe:SWEep:TLSSync`               | Synchronous TLS sweep (not on D/B models)  | ✅ Implemented     | `sense_sweep_tlssync` ²              | ✅ `test_sense_sweep_tlssync`              |
| `SENSe:WAVelength:CENTer`           | Center wavelength                          | ✅ Implemented     | `sense_wavelength_center`            | ✅ `test_sense_wavelength_center`          |
| `SENSe:WAVelength:SPAN`             | Wavelength span                            | ✅ Implemented     | `sense_wavelength_span`              | ✅ `test_sense_wavelength_span`            |
| `SENSe:WAVelength:SRANge`           | Limit sweep to marker L1–L2 spacing        | ✅ Implemented     | `sense_wavelength_srange`            | ✅ `test_sense_wavelength_srange`          |
| `SENSe:WAVelength:STARt`            | Start wavelength                           | ✅ Implemented     | `sense_wavelength_start`             | ✅ `test_sense_wavelength_start`           |
| `SENSe:WAVelength:STOP`             | Stop wavelength                            | ✅ Implemented     | `sense_wavelength_stop`              | ✅ `test_sense_wavelength_stop`            |

² `sense_setting_fiber` and `sense_sweep_tlssync` are added conditionally depending on `self.model`.

**SENSe Summary**: 24 / 24 implemented

### TRACe

| Command(s)                   | Description                                | Status            | Driver implementation                                        | Test coverage                                             |
|------------------------------|--------------------------------------------|-------------------|--------------------------------------------------------------|-----------------------------------------------------------|
| `TRACe:ACTive`               | Set a trace to ACTIVE                       | ✅ Implemented     | `<trace>.active()`                                           | ✅ `test_trace_active`                                     |
| `TRACe:ATTRibute[:<trace>]`  | Trace attribute (write/fix/max/min/…)      | ✅ Implemented     | `<trace>.attribute`, `.write_mode()`, `.fix()`, `.max_hold()`, `.min_hold()` | ✅ `test_trace_attribute`, `test_trace_write/fix/max_hold/min_hold` |
| `TRACe:ATTRibute:RAVG`       | Rolling-average count                       | ✅ Implemented     | `<trace>.roll_avg`                                           | ✅ `test_trace_roll_avg`                                   |
| `TRACe:COPY`                 | Copy source trace to destination            | ✅ Implemented     | `trace_copy()`                                              | ✅ `test_phase4_action_command`                            |
| `TRACe:DELete`               | Delete a trace                              | ✅ Implemented     | `<trace>.delete()`                                          | ✅ `test_trace_delete`                                     |
| `TRACe:DELete:ALL`           | Delete all traces                           | ✅ Implemented     | `delete_all_traces()`                                       | ✅ `test_trace_delete_all`                                 |
| `TRACe:STATe[:<trace>]`      | Trace display state                         | ✅ Implemented     | `<trace>.state`                                             | ✅ `test_trace_state`                                      |
| `TRACe[:DATA]:SNUMber?`      | Number of sampled data points               | ✅ Implemented     | `<trace>.data_sample_number`                               | ✅ `test_trace_data_sample_number`                         |
| `TRACe[:DATA]:X?`            | Wavelength axis data (binary block)         | ✅ Implemented     | `<trace>.trace_axis`                                       | ✅ `test_trace_axis`                                       |
| `TRACe[:DATA]:Y?`            | Level axis data (binary block)              | ✅ Implemented     | `<trace>.data`                                             | ✅ `test_trace_data`                                       |
| `TRACe:PDENsity?`            | Power density readout                       | ✅ Implemented     | `trace_power_density()`                                     | ✅ `test_trace_power_density`                              |
| `TRACe:TEMPlate:*` (10 cmds) | Template / GO-NOGO judgement                | ✅ Implemented     | `template_*` params & methods                              | ✅ `test_template_*`, `test_phase4_action_command`         |

**TRACe Summary**: 21 / 21 implemented

### CALibration

| Command(s)                                    | Description                                 | Status        | Driver implementation                          | Test coverage                                   |
|-----------------------------------------------|---------------------------------------------|---------------|------------------------------------------------|-------------------------------------------------|
| `CALibration:ALIGn[:IMMediate]`               | Standard optical alignment                  | ✅ Implemented | `align()`                                      | ✅ `test_calibration_align`                      |
| `CALibration:ALIGn:EXTernal[:IMMediate]`      | Alignment with external source              | ✅ Implemented | `align_external()`                             | ✅ `test_calibration_align`                      |
| `CALibration:ALIGn:INTernal[:IMMediate]`      | Alignment with internal source              | ✅ Implemented | `align_internal()`                             | ✅ `test_calibration_align`                      |
| `CALibration:BANDwidth[:IMMediate]`           | Resolution-bandwidth calibration            | ✅ Implemented | `calibrate_bandwidth()`                        | ✅ `test_calibrate_bandwidth`                    |
| `CALibration:BANDwidth:INITialize`            | Reset bandwidth calibration                 | ✅ Implemented | `calibrate_bandwidth_initialize()`             | ✅ `test_calibrate_bandwidth`                    |
| `CALibration:BANDwidth:WAVelength?`           | Bandwidth-calibration wavelength            | ✅ Implemented | `calibration_bandwidth_wavelength`             | ✅ `test_calibration_bandwidth_wavelength`       |
| `CALibration:POWer:OFFSet:TABLe`              | Power-offset table entry                    | ✅ Implemented | `calibration_power_offset_table()`             | ✅ `test_calibration_power_offset_table`         |
| `CALibration:WAVelength:EXTernal[:IMMediate]` | External wavelength calibration             | ✅ Implemented | `calibrate_wavelength_external()`              | ✅ `test_calibrate_wavelength`                   |
| `CALibration:WAVelength:EXTernal:SOURce`      | External calibration source                 | ✅ Implemented | `calibration_wavelength_external_source` ³     | ✅ `test_calibration_wavelength_external_source` |
| `CALibration:WAVelength:EXTernal:WAVelength`  | External calibration reference wavelength   | ✅ Implemented | `calibration_wavelength_external_wavelength`   | ✅ `test_calibration_wavelength_external_wavelength` |
| `CALibration:WAVelength:INTernal[:IMMediate]` | Internal wavelength calibration             | ✅ Implemented | `calibrate_wavelength_internal()`              | ✅ `test_calibrate_wavelength`                   |
| `CALibration:WAVelength:OFFSet:TABLe`         | Wavelength-offset table entry               | ✅ Implemented | `calibration_wavelength_offset_table()`        | ✅ `test_calibration_wavelength_offset_table`    |
| `CALibration:ZERO[:AUTO]`                     | Automatic zeroing (and one-shot `ONCE`)     | ✅ Implemented | `calibration_zero_auto`, `zero_once()`         | ✅ `test_calibration_zero_auto`, `test_zero_once` |
| `CALibration:ZERO:INTerval`                   | Auto-zeroing interval                       | ✅ Implemented | `calibration_zero_interval`                    | ✅ `test_calibration_zero_interval`              |
| `CALibration:ZERO:STATus?`                    | Zeroing status                              | ✅ Implemented | `calibration_zero_status`                      | ✅ `test_calibration_zero_status`                |

³ `calibration_wavelength_external_source` assumes a query form (`...:SOURce?`) and the full keyword tokens
`LASER|GASCELL|EMISSION`; confirm the exact query support and returned token against real firmware.

**CALibration Summary**: 15 / 15 implemented

### TRIGger

| Command(s)                        | Description                          | Status        | Driver implementation   | Test coverage                 |
|-----------------------------------|--------------------------------------|---------------|-------------------------|-------------------------------|
| `TRIGger[:SEQuence]:DELay`        | Trigger-to-sweep delay               | ✅ Implemented | `trigger_delay`         | ✅ `test_trigger_delay`        |
| `TRIGger[:SEQuence]:GATE:TIMe`    | Gate open time                       | ✅ Implemented | `trigger_gate_time`     | ✅ `test_trigger_gate_time`    |
| `TRIGger[:SEQuence]:GATE:LOGic`   | Gate logic polarity                  | ✅ Implemented | `trigger_gate_logic`    | ✅ `test_trigger_gate_logic`   |
| `TRIGger[:SEQuence]:GATE:SLOPe`   | Gate trigger edge                    | ✅ Implemented | `trigger_gate_slope`    | ✅ `test_trigger_gate_slope`   |
| `TRIGger[:SEQuence]:GATE:STATe`   | Gated-sweep mode                     | ✅ Implemented | `trigger_gate_state`    | ✅ `test_trigger_gate_state`   |
| `TRIGger[:SEQuence]:INPut`        | External input mode                  | ✅ Implemented | `trigger_input`         | ✅ `test_trigger_input`        |
| `TRIGger[:SEQuence]:OUTPut`       | Trigger output mode                  | ✅ Implemented | `trigger_output`        | ✅ `test_trigger_output`       |
| `TRIGger[:SEQuence]:PHOLd:HTIMe`  | Peak-hold time                       | ✅ Implemented | `trigger_phold_htime`   | ✅ `test_trigger_phold_htime`  |

**TRIGger Summary**: 8 / 8 implemented

### MEMory

| Command(s)       | Description                          | Status        | Driver implementation | Test coverage         |
|------------------|--------------------------------------|---------------|-----------------------|-----------------------|
| `MEMory:CLEar`   | Clear internal memory entry          | ✅ Implemented | `memory_clear()`      | ✅ `test_memory_clear` |
| `MEMory:EMPty?`  | Query whether memory entry is empty  | ✅ Implemented | `memory_empty()`      | ✅ `test_memory_empty` |
| `MEMory:LOAD`    | Load memory entry into a trace       | ✅ Implemented | `memory_load()`       | ✅ `test_memory_load`  |
| `MEMory:STORe`   | Store a trace into memory            | ✅ Implemented | `memory_store()`      | ✅ `test_memory_store` |

**MEMory Summary**: 4 / 4 implemented

### MMEMory

All 32 mass-storage commands are implemented as methods on the instrument (`mmemory_*`) and verified by
`test_mmemory_write_command` (write commands), `test_mmemory_catalog` and `test_mmemory_data` (queries).

| Group          | Commands / driver methods                                                                                                      | Status        |
|----------------|--------------------------------------------------------------------------------------------------------------------------------|---------------|
| File ops (10)  | `ANAMe`, `CATalog?`, `CDIRectory`, `CDRive`, `COPY`, `DATA?`, `DELete`, `MDIRectory`, `REMove`, `REName`                        | ✅ Implemented |
| Load (7)       | `LOAD:ATRace`, `LOAD:DLOGing`, `LOAD:MEMory`, `LOAD:PROGram`, `LOAD:SETTing`, `LOAD:TEMPlate`, `LOAD:TRACe`                     | ✅ Implemented |
| Store (15)     | `STORe:ARESult`, `STORe:ATRace`, `STORe:DATA[:ITEM/:MODE/:TYPE]`, `STORe:DLOGging[:CSAVe/:TSAVe]`, `STORe:GRAPhics`, `STORe:MEMory`, `STORe:PROGram`, `STORe:SETTing`, `STORe:TEMPlate`, `STORe:TRACe` | ✅ Implemented |

Methods with an optional storage medium accept a trailing `medium="INTernal"|"EXTernal"` argument (built via
the private `_medium` helper). Exact command construction is asserted in the tests; confirm the argument
ordering/quoting for a few commands against real firmware.

**MMEMory Summary**: 32 / 32 implemented

### CALCulate — Markers

All 53 marker commands are implemented. Spectral analysis within `CALCulate` is **deferred** (see below).

| Group                     | Commands / driver API                                                                                                                    | Status        | Tests                                             |
|---------------------------|------------------------------------------------------------------------------------------------------------------------------------------|---------------|---------------------------------------------------|
| Auto markers (20)         | `AMARker1–4`: `STATe`, `TRACe`, `X`, `Y?`, `FUNCtion:INTegral[:STATe/:IRANge/:RESult?]`, `FUNCtion:PDENsity[:STATe/:BWIDth/:RESult?]`, `FUNCtion:PRESet`, `AOFF`, `MAXimum[:LEFT/NEXT/RIGHt]`, `MINimum[:LEFT/NEXT/RIGHt]` → `amarker1`…`amarker4` channels (`amarkers` tuple) | ✅ Implemented | `test_amarker1_*`, `test_amarker_action` (all 4 indices) |
| Manual markers (27)       | instrument params `marker_auto`, `marker_function_format/update`, `marker_maximum_scenter_auto`, `marker_maximum_srlevel_auto`, `marker_msearch[/_sort/_threshold]`, `marker_unit`; actions `clear_all_markers`, `marker_maximum[_left/next/right/scenter/srlevel/szcenter]`, `marker_minimum[…]`, `marker_scenter/srlevel/szcenter`; per-marker `marker_set_state/set_x/get_x/get_y` | ✅ Implemented | `test_marker_*`, `test_marker_action_command`, `test_marker_get_x_y` |
| Line markers (6)          | `line_marker_srange` (param); `line_marker_all_off`, `line_marker_sspan`, `line_marker_szspan`, `line_marker_set_x`, `line_marker_set_y`  | ✅ Implemented | `test_line_marker_srange`, `test_marker_action_command` |

Marker parameters use PyVISA-sim round-trip tests (`AMARker1` and the instrument-level manual/line params);
action methods and argument-based (`<marker>,…`) commands are verified by asserting the emitted SCPI string.
Enum tokens for `marker_unit` and the auto-marker `TRACe` assume keyword round-trip — confirm returned tokens
against real firmware.

**CALCulate (markers) Summary**: 53 / 53 marker commands implemented (analysis deferred)

### STATus

`status_operation_condition`, `status_operation_enable`, `status_operation_event`, `status_operation_preset()`,
`status_questionable_condition`, `status_questionable_enable`, `status_questionable_event` — enables reliable
sweep-complete detection via the operation status register. Tested by `test_status_operation_registers`,
`test_status_questionable_registers` and `test_phase4_action_command`.

**STATus Summary**: 7 / 7 implemented

### SYSTem (remainder)

Beyond `system_error`: buzzer (`system_buzzer_click/warning`), communication
(`system_communicate_gpib2_address/scontroller/tls_address`, `..._lockout`, `..._rmonitor`), date/time
(`system_date`, `system_time`), display (`system_display_transparent/uncal`), info
(`system_version`, `system_fspeed`, `system_information()`), WDM grid (`system_grid`,
`system_grid_custom_spacing/start/stop`, `system_grid_reference`, `system_grid_custom_clear_all()/delete()/insert()`),
`system_operator_lock()` and `system_preset()`. `SYSTem:COMMunicate:CFORmat` is intentionally left out
(it switches the command-set emulation and would break the driver's own I/O).

**SYSTem Summary**: 26 / 26 implemented

### UNIT

`unit_power_digit` (1–3) and `unit_x` (wavelength/frequency/wavenumber). Tested by `test_unit_power_digit`
and `test_unit_x`.

**UNIT Summary**: 2 / 2 implemented

### APPLication:DLOGging

`dlog_elapsed_time`, `dlog_interval`, `dlog_item`, `dlog_lmode`, `dlog_memory`, `dlog_mthresh`,
`dlog_pdetect_athresh/rthresh/ttype`, `dlog_tduration`, `dlog_tlogging`, `dlog_state` — time-series data
logging. Tested by `test_dlog_*`.

**APPLication:DLOGging Summary**: 12 / 12 implemented

### PROGram

`program_execute()` runs a stored program. Tested by `test_phase4_action_command`.

**PROGram Summary**: 1 / 1 implemented

---

## Not-Implemented (deferred)

Only the `CALCulate` spectral-analysis commands remain — deliberately deferred to a future effort.

| Group                                    | Commands | Functionality not exposed                                                  |
|------------------------------------------|---------:|----------------------------------------------------------------------------|
| `CALCulate` analysis functions           |      ~16 | Category selection/run/read (`CATegory`, `AUTO`, `[:IMMediate]`, `DATA?`) and result queries (WDM, NF, SMSR, DFB-LD, spectral width, power, …) |
| `CALCulate:PARameter[:CATegory]:*`       |       55 | Per-analysis-category configuration parameters                             |
| `CALCulate:MATH:*`                        |        9 | Trace math (log/linear combinations, curve fit, normalization)             |

**Deferred total**: ~80 `CALCulate` analysis commands.

---

## Overall Implementation Coverage

| Subsystem              | Implemented |   Total | Percentage |    Tested |
|------------------------|------------:|--------:|-----------:|----------:|
| COMMON (IEEE 488.2)    |          14 |      14 |       100% |     14/14 |
| ABORt                  |           1 |       1 |       100% |      1/1  |
| DISPlay                |          33 |      33 |       100% |     33/33 |
| FORMat                 |           1 |       1 |       100% |      1/1  |
| INITiate               |           2 |       2 |       100% |      2/2  |
| SENSe                  |          24 |      24 |       100% |     24/24 |
| TRACe                  |          21 |      21 |       100% |     21/21 |
| CALibration            |          15 |      15 |       100% |     15/15 |
| TRIGger                |           8 |       8 |       100% |       8/8 |
| MEMory                 |           4 |       4 |       100% |       4/4 |
| MMEMory                |          32 |      32 |       100% |     32/32 |
| CALCulate (markers)    |          53 |     133 |        40% |     53/53 |
| APPLication:DLOGging   |          12 |      12 |       100% |     12/12 |
| PROGram                |           1 |       1 |       100% |       1/1 |
| STATus                 |           7 |       7 |       100% |       7/7 |
| SYSTem                 |          26 |      26 |       100% |     26/26 |
| UNIT                   |           2 |       2 |       100% |       2/2 |
| **TOTAL**              |     **256** | **336** |    **76%** | **256/256** |

---

## Notes

- This file is derived from the command inventory in `Yokogawa_AQ637x_command_list.md` and the current implementation in `src/qcodes_contrib_drivers/drivers/Yokogawa/Yokogawa_AQ637x.py`.
- The driver targets the AQ6370C/AQ6370D/AQ6373/AQ6373B/AQ6375/AQ6375B family. Two parameters are added conditionally by model: `sense_setting_fiber` (AQ6373/AQ6373B) and `sense_sweep_tlssync` (all except AQ6370D/AQ6373B/AQ6375B).
- Traces are modelled as seven `YokogawaAQ637xChannel` submodules (`TRA`–`TRG`, also exposed as a `ChannelTuple` `traces`), each carrying `state`, `attribute`, `roll_avg`, `data_sample_number`, `trace_axis`, `data` plus `active()`, `delete()`, `write_mode()`, `fix()`, `max_hold()`, `min_hold()`. Following the QCoDeS convention, `trace_axis` is a plain `Parameter` (the X/setpoint axis) and `data` is a `ParameterWithSetpoints` whose `setpoints=(trace_axis,)`.
- Binary trace transfer (`trace_axis` / `data`) is handled by the custom `YokogawaData` / `YokogawaDataWithSetpoints` parameter classes, which read the IEEE-488.2 definite-length block via pyvisa's `query_binary_values` (`REAL64`→`d`, `REAL32`→`f`, little-endian). Covered by `test_trace_axis`/`test_trace_data` (parse hand-encoded REAL64 blocks in the sim) and `test_trace_data_query_binary_contract` (pins the datatype and byte order); validated on the real `AQ6370C`.
- **Testing**: `tests/Yokogawa/test_Yokogawa_AQ637x.py` runs against `sims/Yokogawa_AQ637x.yaml` (PyVISA-sim), so the suite executes in CI. The real-hardware address (a `TCPIP::<instrument-ip>::INSTR` VISA resource string, model `AQ6370C`) is kept in the fixture as a commented toggle for development against the physical instrument. A second sim device (`AQ6373`) exercises the model-gated `sense_setting_fiber`.
- The four trace `ATTRibute` keyword methods (`write_mode`/`fix`/`max_hold`/`min_hold`) are skipped under the sim (`skip_on_sim`) because they depend on instrument-side keyword→code normalization PyVISA-sim cannot reproduce; they still run against real hardware.
- The convenience methods `auto()`, `repeat()` and `single()` combine `sweep_mode` with `immediate()` to replicate the OSA front-panel sweep buttons.
- Possible SCPI-path discrepancies to confirm against firmware: `display_trace_y_nmask_type` issues `:DISPlay:TRACe:Y:NMASk:TYPE` (manual lists `DISPlay:TRACe:Y:TYPE`), and the split-hold parameters issue `:DISPlay:SPLit:HOLD:...` (manual lists `DISPlay:HOLD:...`).
