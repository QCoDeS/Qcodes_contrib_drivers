import logging
from time import sleep
from typing import Optional, List

from qcodes.instrument.channel import InstrumentChannel
from .private.DotNetAPI.DeviceManagerCLI import IGenericRackDevice
from .private.DotNetAPI.GenericMotorCLI_AdvancedMotor import GenericAdvancedMotorCLI
from .private.DotNetAPI.qcodes_thorlabs_integration import ThorlabsQcodesInstrument, ThorlabsMixin


log = logging.getLogger(__name__)

class ThorlabsBSCxxx(IGenericRackDevice, ThorlabsQcodesInstrument):
    """
    Instrument driver for the Thorlabs Benchtop Stepper Motor series BSCxxx.

    This driver interfaces with a Thorlabs motor using the .NET API, providing
    control over the motor's functions. It handles the initialization and
    management of the motor and its channels.
    
    This class integrates the Thorlabs device, using the .NET API.
    For further .NET API details please refer to:
    .private/DotNetAPI/README.md

    Args:
        name: Name of the instrument.
        serial_number: The serial number of the Thorlabs device.
        actuator_names: List of actuator names, size should match channel number.
        startup_mode_values: List of startup_mode_values, size should match channel number.
            startup_mode_value: .Net Enum value to be stored in '_startup_mode' and used as 
                                'startupSettingsMode' in 'LoadMotorConfiguration'
                Valid startup modes:
                    UseDeviceSettings: Use settings from device
                    UseFileSettings: Use settings stored locally
                    UseConfiguredSettings: Use one of the above according to
                                           choice in Kinesis Software
        dll_directory: The directory where the DLL files are located.
        simulation: Flag to determine if the device is in simulation mode.
        polling_rate_ms: Polling rate in milliseconds for the device.

    Raises:
        ValueError: If the model is not recognized as a known model.
    """    
    def __init__(self,
                 name: str,
                 serial_number: str,
                 actuator_names: Optional[List[str]] = None,
                 startup_mode_values: List[str] = ['UseConfiguredSettings', 'UseConfiguredSettings', 'UseConfiguredSettings'],
                 simulation: Optional[bool] = False,
                 polling_rate_ms: int = 250,
                 dll_directory: Optional[str] = None,
                 **kwargs
    ):
        super().__init__(
            name,                         # Instrument (Qcodes)
            serial_number=serial_number,  # ThorlabsQcodesInstrument
            simulation=simulation,        # ThorlabsQcodesInstrument
            dll_directory=dll_directory,  # ThorlabsDLLMixin
            **kwargs)


        # Initialize channels 
        for channel_number in range(1, self.channel_count() + 1):
            if actuator_names is not None:
                actuator_name = actuator_names[channel_number - 1]
            else:
                actuator_name = None 
            
            startup_mode_value = startup_mode_values[channel_number - 1]
    
            channel = ThorlabsBSCxxxChannel(
                self, 
                f"channel{channel_number}",
                self._api_interface.GetChannel(channel_number),
                actuator_name,
                startup_mode_value,
                polling_rate_ms
            )
            self.add_submodule(f"channel{channel_number}", channel)  

        self.connect_message()

        if '(Simulated)' not in self.model():
            self.snapshot(True)

    def _import_device_dll(self):
        """Import the device-specific DLLs and classes from the .NET API."""        
        self._add_dll('Thorlabs.MotionControl.GenericMotorCLI.dll')
        self._add_dll('Thorlabs.MotionControl.Benchtop.StepperMotorCLI.dll')
        self._import_dll_class('Thorlabs.MotionControl.Benchtop.StepperMotorCLI', 'BenchtopStepperMotor')

    def _get_api_interface_from_dll(self, serial_number: str):
        """Retrieve the API interface for the Thorlabs device using its serial number."""        
        return self._dll.BenchtopStepperMotor.CreateBenchtopStepperMotor(serial_number)

    def _post_connection(self):
        """
        Will run after after establishing a connection, updating 'get_idn'
        and adding parameters 'model', 'serial_number' and 'firmware_version'.
        """
        knownmodels = [
            'BSC203'#,
            #'BSC203 (Simulated)'
        ]
        if self.model() not in knownmodels:
            raise ValueError(f"'{self.model()}' is an unknown model.")


class ThorlabsBSCxxxChannel(GenericAdvancedMotorCLI, ThorlabsMixin, InstrumentChannel):
    """
    Channel class for a single channel of the Thorlabs BSCxxx Benchtop Stepper Motor.

    Each channel represents an individual motor and provides methods to interact with
    it, such as initialization and setting parameters, through the .NET API.

    This class integrates the Thorlabs channel, using the .NET API.
    For further .NET API details please refer to:
    .private/DotNetAPI/README.md

    Args:
        parent: The parent Qcodes Instrument or Station.
        name: Name to identify this instance.
        api_interface: The API interface for the channel.
        actuator_name: The name of the actuator.
        startup_mode_value: .Net Enum value to be stored in '_startup_mode' and used as 
                            'startupSettingsMode' in 'LoadMotorConfiguration'
            Valid startup modes:
                UseDeviceSettings: Use settings from device
                UseFileSettings: Use settings stored locally
                UseConfiguredSettings: Use one of the above according to
                                       choice in Kinesis Software
        polling_rate_ms: Polling rate in milliseconds for the channel.
        **kwargs: Additional keyword arguments.

    Raises:
        RuntimeError: If unable to connect to the channel.
    """

    def __init__(self, parent: ThorlabsBSCxxx,
                 name: str,
                 api_interface, 
                 actuator_name: str,
                 startup_mode_value: str,
                 polling_rate_ms: int = 250,
                 **kwargs):
        self._actuator_name = actuator_name

        super().__init__(
            parent,
            name,
            api_interface=api_interface,
            startup_mode_value=startup_mode_value,
            polling_rate_ms=polling_rate_ms,
            **kwargs)

    def _post_enable(self):
        """
        This method can be overwritten by a subclass.
        Will run after polling has started and the device/channel is enabled.
        """
        # Load any configuration settings needed by the device/channel
        if self.parent.model() == 'BSC203':
            serial = self._api_interface.DeviceID.strip()
        else:
            serial = self.parent.serial_number()

        mode = self._startup_mode

        self._configuration = (
            self._api_interface.LoadMotorConfiguration(serial, mode))

        # self._settings = self._api_interface.MotorDeviceSettings
        # self._api_interface.GetSettings(self._settings)

        self._configuration.DeviceSettingsName = self._actuator_name
        self._configuration.UpdateCurrentConfiguration()
        # self._api_interface.SetSettings(self._settings, True, False)

        self._api_interface.SetSettings(self._api_interface.MotorDeviceSettings, True, False)
        sleep(0.5)
