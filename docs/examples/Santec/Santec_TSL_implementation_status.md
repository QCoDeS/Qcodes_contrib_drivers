# TSL570 Driver Command Implementation Status

## Summary Statistics

- **Manual commands tracked**: 62 driver-facing commands
- **Implemented manual commands**: 62
- **Not implemented manual commands**: 0
- **Implemented commands with test coverage**: 62 / 62 (100%)

> Notes:
> - Set/get pairs are grouped into a single driver-facing command row.
> - Query-only commands such as `...:MINimum?` and `...:MAXimum?` are counted individually.
> - `*RST` is implemented in the driver as `reset()`, but it is not part of `Santec_TSL570_command_list.txt` and is therefore excluded from the totals below.

---

## Manual Command Coverage

### Optical Output Related Commands

| Command(s)                                                                                   | Description                                       | Status            | Driver implementation                           | Test coverage                                                 |
|----------------------------------------------------------------------------------------------|---------------------------------------------------|-------------------|-------------------------------------------------|---------------------------------------------------------------|
| `:WAVelength` / `:WAVelength?`                                                               | Output wavelength                                 | ✅ Implemented     | `wavelength`                                    | ✅ `test_wavelength_set_get`                                   |
| `:WAVelength:UNIT` / `:WAVelength:UNIT?`                                                     | Wavelength display unit                           | ✅ Implemented     | `wavelength_unit`                               | ✅ `test_wavelength_unit`                                      |
| `:WAVelength:FINe` / `:WAVelength:FINe?`                                                     | Fine-tuning value                                 | ✅ Implemented     | `wavelength_fine`                               | ✅ `test_wavelength_fine`                                      |
| `:WAVelength:FINetuning:DISable`                                                             | Disable fine tuning                               | ✅ Implemented     | `disable_fine_tuning()`                         | ✅ `test_disable_fine_tuning`                                  |
| `[:WAVelength]:FREQuency` / `[:WAVelength]:FREQuency?`                                       | Optical frequency                                 | ✅ Implemented     | `frequency`                                     | ✅ `test_frequency_set_get`                                    |
| `:COHCtrl` / `:COHCtrl?`                                                                     | Coherence control                                 | ✅ Implemented     | `coherence_control`                             | ✅ `test_coherence_control`                                    |
| `:POWer:STATe` / `:POWer:STATe?`                                                             | Optical output state                              | ✅ Implemented     | `output`                                        | ✅ `test_output`                                               |
| `:POWer:ATTenuation` / `:POWer:ATTenuation?`                                                 | Attenuator value                                  | ✅ Implemented     | `power_attenuation`                             | ✅ `test_power_attenuation`                                    |
| `:POWer:ATTenuation:AUTo` / `:POWer:ATTenuation:AUTo?`                                       | Automatic attenuation mode                        | ✅ Implemented     | `power_auto`                                    | ✅ `test_power_auto`                                           |
| `:POWer[:LEVel]` / `:POWer[:LEVel]?`                                                         | Output power level                                | ✅ Implemented     | `power`                                         | ✅ `test_power_set_get`                                        |
| `:POWer:ACTual[:LEVel]?`                                                                     | Actual monitored power                            | ✅ Implemented     | `power_actual`                                  | ✅ `test_power_actual`                                         |
| `:POWer:SHUTter` / `:POWer:SHUTter?`                                                         | Internal shutter state                            | ✅ Implemented     | `shutter`                                       | ✅ `test_shutter`                                              |
| `:POWer:UNIT` / `:POWer:UNIT?`                                                               | Power unit                                        | ✅ Implemented     | `power_unit`                                    | ✅ `test_power_unit`                                           |
| `:WAVelength:SWEep:STARt` / `:WAVelength:SWEep:STARt?`                                       | Sweep start wavelength                            | ✅ Implemented     | `sweep_start_wavelength`                        | ✅ `test_sweep_start_stop`                                     |
| `[:WAVelength]:FREQuency:SWEep:STARt` / `[:WAVelength]:FREQuency:SWEep:STARt?`               | Sweep start frequency                             | ✅ Implemented     | `sweep_start_frequency`                         | ✅ `test_sweep_start_stop_frequency`                           |
| `:WAVelength:SWEep:STOP` / `:WAVelength:SWEep:STOP?`                                         | Sweep stop wavelength                             | ✅ Implemented     | `sweep_stop_wavelength`                         | ✅ `test_sweep_start_stop`                                     |
| `:WAVelength:SWEep:RANGe:MINimum?`                                                           | Minimum allowed sweep wavelength at current speed | ✅ Implemented     | `sweep_range_minimum_wavelength`                | ✅ `test_sweep_range_limits` *(can time out on some firmware)* |
| `:WAVelength:SWEep:RANGe:MAXimum?`                                                           | Maximum allowed sweep wavelength at current speed | ✅ Implemented     | `sweep_range_maximum_wavelength`                | ✅ `test_sweep_range_limits` *(can time out on some firmware)* |
| `[:WAVelength]:FREQuency:SWEep:STOP` / `[:WAVelength]:FREQuency:SWEep:STOP?`                 | Sweep stop frequency                              | ✅ Implemented     | `sweep_stop_frequency`                          | ✅ `test_sweep_start_stop_frequency`                           |
| `[:WAVelength]:FREQuency:SWEep:RANGe:MINimum?`                                               | Minimum allowed sweep frequency at current speed  | ✅ Implemented     | `sweep_range_minimum_frequency`                 | ✅ `test_sweep_frequency_range_limits`                         |
| `[:WAVelength]:FREQuency:SWEep:RANGe:MAXimum?`                                               | Maximum allowed sweep frequency at current speed  | ✅ Implemented     | `sweep_range_maximum_frequency`                 | ✅ `test_sweep_frequency_range_limits`                         |
| `:WAVelength:SWEep:MODe` / `:WAVelength:SWEep:MODe?`                                         | Sweep mode                                        | ✅ Implemented     | `sweep_mode`                                    | ✅ `test_sweep_mode`                                           |
| `:WAVelength:SWEep:SPEed` / `:WAVelength:SWEep:SPEed?`                                       | Sweep speed                                       | ✅ Implemented     | `sweep_speed`                                   | ✅ `test_sweep_speed`                                          |
| `:WAVelength:SWEep:STEP[:WIDTh]` / `:WAVelength:SWEep:STEP[:WIDTh]?`                         | Wavelength sweep step                             | ✅ Implemented     | `sweep_step_wavelength`                         | ✅ `test_sweep_step`                                           |
| `[:WAVelength]:FREQuency:SWEep:STEP[:WIDTh]` / `[:WAVelength]:FREQuency:SWEep:STEP[:WIDTh]?` | Frequency sweep step                              | ✅ Implemented     | `sweep_step_frequency`                          | ✅ `test_sweep_frequency_step`                                 |
| `:WAVelength:SWEep:DWELl` / `:WAVelength:SWEep:DWELl?`                                       | Step-sweep dwell time                             | ✅ Implemented     | `sweep_dwell`                                   | ✅ `test_sweep_dwell`                                          |
| `:WAVelength:SWEep:CYCLes` / `:WAVelength:SWEep:CYCLes?`                                     | Sweep repetition count                            | ✅ Implemented     | `sweep_cycles`                                  | ✅ `test_sweep_cycles`                                         |
| `:WAVelength:SWEep:COUNt?`                                                                   | Completed sweep count                             | ✅ Implemented     | `sweep_count`                                   | ✅ `test_sweep_count`                                          |
| `:WAVelength:SWEep:DELay` / `:WAVelength:SWEep:DELay?`                                       | Delay between sweeps                              | ✅ Implemented     | `sweep_delay`                                   | ✅ `test_sweep_delay`                                          |
| `:WAVelength:SWEep[:STATe]` / `:WAVelength:SWEep[:STATe]?`                                   | Sweep state and single-sweep start/stop           | ✅ Implemented     | `sweep_state`, `sweep_single()`, `sweep_stop()` | ✅ `test_sweep_state`, `test_sweep_single`, `test_sweep_stop`  |
| `:WAVelength:SWEep[:STATe]:REPeat`                                                           | Repeat sweep start                                | ✅ Implemented     | `sweep_repeat()`                                | ✅ `test_sweep_repeat`                                         |
| `:READout:POINts?`                                                                           | Logged point count                                | ✅ Implemented     | `readout_points`                                | ✅ `test_readout_points`                                       |
| `:READout:DATa?`                                                                             | Logged wavelength data                            | ✅ Implemented     | `readout_data`                                  | ✅ `test_readout_data`                                         |
| `:READout:DATa:POWer?`                                                                       | Logged power data                                 | ✅ Implemented     | `readout_power_data`                            | ✅ `test_readout_power_data`                                   |
| `:AM:STATe` / `:AM:STATe?`                                                                   | AM enable/disable                                 | ✅ Implemented     | `modulation_state`                              | ✅ `test_modulation_state`                                     |
| `:AM:SOURce` / `:AM:SOURce?`                                                                 | AM source                                         | ✅ Implemented     | `modulation_source`                             | ✅ `test_modulation_source`                                    |
| `[:SOURce]:WAVelength:OFFSet` / `[:SOURce]:WAVelength:OFFSet?`                               | Wavelength offset                                 | ✅ Implemented     | `wavelength_offset`                             | ✅ `test_wavelength_offset`                                    |

**Optical Output Summary**: 37 / 37 implemented

### Input/Output Related Commands

| Command(s)                                                               | Description                   | Status        | Driver implementation     | Test coverage                    |
|--------------------------------------------------------------------------|-------------------------------|---------------|---------------------------|----------------------------------|
| `:TRIGger:INPut:EXTernal` / `:TRIGger:INPut:EXTernal?`                   | External trigger input enable | ✅ Implemented | `trigger_input_external`  | ✅ `test_trigger_input_external`  |
| `:TRIGger:INPut[:EXTernal]:ACTive` / `:TRIGger:INPut[:EXTernal]:ACTive?` | Input trigger polarity        | ✅ Implemented | `trigger_input_polarity`  | ✅ `test_trigger_input_polarity`  |
| `:TRIGger:INPut:STANdby` / `:TRIGger:INPut:STANdby?`                     | Trigger standby mode          | ✅ Implemented | `trigger_input_standby`   | ✅ `test_trigger_input_standby`   |
| `:TRIGger:INPut:SOFTtrigger`                                             | Software trigger              | ✅ Implemented | `software_trigger()`      | ✅ `test_software_trigger`        |
| `:TRIGger:OUTPut` / `:TRIGger:OUTPut?`                                   | Trigger output timing         | ✅ Implemented | `trigger_output_timing`   | ✅ `test_trigger_output_timing`   |
| `:TRIGger:OUTPut:ACTive` / `:TRIGger:OUTPut:ACTive?`                     | Output trigger polarity       | ✅ Implemented | `trigger_output_polarity` | ✅ `test_trigger_output_polarity` |
| `:TRIGger:OUTPut:STEP[:WIDTh]` / `:TRIGger:OUTPut:STEP[:WIDTh]?`         | Trigger output spacing        | ✅ Implemented | `trigger_output_step`     | ✅ `test_trigger_output_step`     |
| `:TRIGger:OUTPut:SETTing` / `:TRIGger:OUTPut:SETTing?`                   | Trigger output period mode    | ✅ Implemented | `trigger_output_setting`  | ✅ `test_trigger_output_setting`  |
| `:TRIGger:THRough` / `:TRIGger:THRough?`                                 | Trigger-through mode          | ✅ Implemented | `trigger_through`         | ✅ `test_trigger_through`         |

**Input/Output Summary**: 9 / 9 implemented

### System Related Commands

| Command(s)                                                                           | Description               | Status            | Driver implementation                                       | Test coverage                 |
|--------------------------------------------------------------------------------------|---------------------------|-------------------|-------------------------------------------------------------|-------------------------------|
| `:SYSTem:ERRor?`                                                                     | Error queue readout       | ✅ Implemented     | `system_error`                                              | ✅ `test_system_error`         |
| `:SYSTem:COMMunicate:GPIB:ADDRess` / `:SYSTem:COMMunicate:GPIB:ADDRess?`             | GPIB address              | ✅ Implemented     | `gpib_address`                                              | ✅ `test_gpib_address`         |
| `:SYSTem:COMMunicate:GPIB:DELimiter` / `:SYSTem:COMMunicate:GPIB:DELimiter?`         | GPIB delimiter            | ✅ Implemented     | `gpib_delimiter`                                            | ✅ `test_gpib_delimiter`       |
| `:SYSTem:COMMunicate:ETHernet:MACaddress?`                                           | Ethernet MAC address      | ✅ Implemented     | `ethernet_mac_address`                                      | ✅ `test_ethernet_mac_address` |
| `:SYSTem:COMMunicate:ETHernet:IPADdress` / `:SYSTem:COMMunicate:ETHernet:IPADdress?` | Ethernet IP address       | ✅ Implemented     | `ethernet_ip_address`                                       | ✅ `test_ethernet_ip_address`  |
| `:SYSTem:COMMunicate:ETHernet:SMASk` / `:SYSTem:COMMunicate:ETHernet:SMASk?`         | Ethernet subnet mask      | ✅ Implemented     | `ethernet_subnet_mask`                                      | ✅ `test_ethernet_subnet_mask` |
| `:SYSTem:COMMunicate:ETHernet:DGATeway` / `:SYSTem:COMMunicate:ETHernet:DGATeway?`   | Ethernet default gateway  | ✅ Implemented     | `ethernet_gateway`                                          | ✅ `test_ethernet_gateway`     |
| `:SYSTem:COMMunicate:ETHernet:PORT` / `:SYSTem:COMMunicate:ETHernet:PORT?`           | Ethernet port number      | ✅ Implemented     | `ethernet_port`                                             | ✅ `test_ethernet_port`        |
| `:SYSTem:COMMunicate:CODe` / `:SYSTem:COMMunicate:CODe?`                             | Command-set selection     | ✅ Implemented     | `command_set` *(read-only; driver forces SCPI during init)* | ✅ `test_command_set_param`    |
| `:SYSTem:LOCK?`                                                                      | External interlock status | ✅ Implemented     | `system_lock`                                               | ✅ `test_system_lock`          |
| `:DISPlay:BRIGhtness` / `:DISPlay:BRIGhtness?`                                       | Display brightness        | ✅ Implemented     | `display_brightness`                                        | ✅ `test_display_brightness`   |
| `:SPECial:SHUTdown`                                                                  | Shutdown device           | ✅ Implemented     | `shutdown()`                                                | ✅ `test_shutdown_command`      |
| `:SPECial:REBoot`                                                                    | Reboot device             | ✅ Implemented     | `reboot()`                                                  | ✅ `test_reboot_command`        |
| `:SYSTem:ALERt?`                                                                     | Alert information         | ✅ Implemented     | `system_alert`                                              | ✅ `test_system_alert`         |
| `:SYSTem:VERSion?`                                                                   | Firmware version          | ✅ Implemented     | `system_version`                                            | ✅ `test_system_version`       |
| `:SYSTem:CODe?`                                                                      | Product code              | ✅ Implemented     | `system_code`                                               | ✅ `test_system_code`          |

**System Summary**: 16 / 16 implemented

---

## Overall Implementation Coverage

| Category       | Implemented |  Total | Percentage |      Tested |
|----------------|------------:|-------:|-----------:|------------:|
| Optical Output |          37 |     37 |       100% |     37 / 37 |
| Input/Output   |           9 |      9 |       100% |       9 / 9 |
| System         |          16 |     16 |       100% |     16 / 16 |
| **TOTAL**      |      **62** | **62** |   **100%** | **62 / 62** |

---

## Notes

- This file is derived from the manual command inventory in `Santec_TSL570_command_list.txt` and the current implementation in `Santec_TSL.py`.
- `:READout:DATa?` is implemented and covered by `test_readout_data`.
- `:SYSTem:COMMunicate:CODe` is exposed as a read-only parameter in the driver; the driver sets SCPI mode automatically during initialization.
- `:WAVelength:SWEep:RANGe:MINimum?` and `:WAVelength:SWEep:RANGe:MAXimum?` are implemented, but the instrument firmware may time out on some hardware/firmware revisions.
- **Parameter naming convention updated**: All sweep parameters now use suffix pattern `[property]_[domain]` (e.g., `sweep_range_minimum_wavelength`, `sweep_step_frequency`) for improved searchability.
- **All optical output commands are now 100% implemented**, including both wavelength and frequency sweep control with step support.
- All five Ethernet configuration commands (`:SYSTem:COMMunicate:ETHernet:*`) are implemented with full read/write support (MAC, IP, subnet mask, gateway, port).
- GPIB communication commands (`:SYSTem:COMMunicate:GPIB:ADDRess` and `:SYSTem:COMMunicate:GPIB:DELimiter`) are implemented for systems with GPIB connectivity.
- Display brightness (`:DISPlay:BRIGhtness`) is implemented for display control (0-100%).
- Device power-control commands `:SPECial:SHUTdown` and `:SPECial:REBoot` are implemented as `shutdown()` and `reboot()` with safe command-string tests.
