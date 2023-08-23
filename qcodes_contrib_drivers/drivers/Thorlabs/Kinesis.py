import os
import ctypes
from ctypes import wintypes

class Thorlabs_KinesisException(Exception):
    pass

class Thorlabs_Kinesis():
    
    def __init__(self, dll_path: str, sim: bool) -> None:
            
        os.add_dll_directory(r"C:\Program Files\Thorlabs\Kinesis")
        self.dll = ctypes.cdll.LoadLibrary(dll_path)
        
        if sim:
            self.enable_simulation()
        else:
            pass

    # See Thorlabs Kinesis C API documentation for error description
    def error_check(self, r: int, source:str) -> int:
        if r != 0:
            raise Thorlabs_KinesisException("Kinesis: [{}]: Error code {}".format(source, r))
        else:
            pass
        
        return r

    # Connects to simulator (which must be already running but 
    # without GUI open, only one port)
    def enable_simulation(self) -> None:
        r = self.dll.TLI_InitializeSimulations()
        # Throws error message even if simulation was successfull, 
        # check the log in the Kinesis simulator for confirmation instead
        # self.error_check(r, 'Enable simulation') 

    def disable_simulation(self) -> None:
        r = self.dll.TLI_UninitializeSimulations()
        self.error_check(r, 'Disable simulation')
    
    # Returns list with all the available (and closed?) devices
    def device_list(self) -> list:
        r = self.dll.TLI_BuildDeviceList()
        if r == 0 or r == 16:
            device_list = ctypes.create_string_buffer(250)
            r2 = self.dll.TLI_GetDeviceListExt(ctypes.byref(device_list), 250)
            self.error_check(r2, 'Get device list')
        else:
            self.error_check(r, 'Build device list')
        
        return device_list.value.decode("utf-8").rstrip(',').split(",")

    # Helper convertion function
    def to_char_p(self, s: str) -> ctypes.c_char_p:
        return ctypes.c_char_p(s.encode('ascii'))

    # Functions for starting and stopping connection to the laser source
    def open_laser(self, serial_number: str) -> None:
        r = self.dll.LS_Open(self.to_char_p(serial_number))
        self.error_check(r, 'Opening device')
    
    def start_polling(self, serial_number: str, polling_speed: int) -> None:
        # Note: this function returns a boolean (for some reason)
        r = self.dll.LS_StartPolling(self.to_char_p(serial_number), ctypes.c_int(polling_speed))
        if r != 1:
            # 21 = FT_SpecificFunctionFail - The function failed to complete succesfully.
            # If unsuccessful, then r seems to be -1749177856 but this is not explained in the documentation
            self.error_check(21, 'Start polling')

    def close_laser(self, serial_number: str) -> None:
        self.dll.LS_Close(self.to_char_p(serial_number))

    def stop_polling(self, serial_number: str) -> None:
        self.dll.LS_StopPolling(self.to_char_p(serial_number))

    # Gets device information from a serial number
    def laser_info(self, serial_number: str) -> list:
        # Defining variables for information storing
        model = ctypes.create_string_buffer(8)
        model_size = ctypes.wintypes.DWORD(8)
        type_num = ctypes.wintypes.WORD()
        channel_num = ctypes.wintypes.WORD()
        notes = ctypes.create_string_buffer(48)
        notes_size = ctypes.c_ulong(48)
        firmware_version = ctypes.wintypes.DWORD()
        hardwware_version = ctypes.wintypes.WORD()
        modification_state = ctypes.wintypes.WORD()

        r = self.dll.LS_GetHardwareInfo(self.to_char_p(serial_number), ctypes.byref(model), model_size, 
                                    ctypes.byref(type_num), ctypes.byref(channel_num),
                                    ctypes.byref(notes), notes_size, ctypes.byref(firmware_version),
                                    ctypes.byref(hardwware_version), ctypes.byref(modification_state))
        self.error_check(r, 'Get hardware info')

        return [model, type_num, channel_num, notes, firmware_version, hardwware_version, modification_state]
    
    # Returns a string with the status in binary (see doc. for bit meaning)
    def laser_status_bits(self, serial_number: str) -> int:
        # Note: status bits updated at polling interval, hence no LS_RequestStatusBits
        integer = self.dll.LS_GetStatusBits(self.to_char_p(serial_number))
        if integer == 0x40000000:
            return self.error_check(integer, 'Get status bits')
        else:
            return integer
        
    # Turnng the laser on/off (on only if safety key is on)
    def laser_enable_output(self, serial_number: str) -> None:
        r = self.dll.LS_EnableOutput(self.to_char_p(serial_number))
        self.error_check(r, 'Enable laser output')

    def laser_disable_output(self, serial_number: str) -> None:
        r = self.dll.LS_DisableOutput(self.to_char_p(serial_number))
        self.error_check(r, 'Disable laser output')

    # Reading laser power
    def get_laser_power(self, serial_number: str) -> float:
        max_num = 32767
        max_power_W = 0.007
        num = self.dll.LS_GetPowerReading(self.to_char_p(serial_number))
        
        return num/max_num * max_power_W
    
    # [ATTENTION] Setting laser power 
    def set_laser_power(self, serial_number: str, power_W: float) -> None:
        # Maximum integer level for laser power 
        max_num = 32767
        max_power_W = 0.007
        # [ATTENTION] Maximum power is 7mW for actual device but 10mW for the simulator (somehow)
        percentage = power_W/max_power_W
        r = self.dll.LS_SetPower(self.to_char_p(serial_number), int(percentage*max_num))
        self.error_check(r, 'Set laser power')

