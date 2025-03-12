import logging
from time import sleep
from typing import Optional

from .private.DotNetAPI.GenericMotorCLI_ControlParameters import IDCPIDParameters
from .private.DotNetAPI.DeviceManagerCLI import IDeviceScanning
from .private.DotNetAPI.GenericMotorCLI_KCubeMotor import GenericKCubeMotorCLI
from .private.DotNetAPI.qcodes_thorlabs_integration import ThorlabsQcodesInstrument

log = logging.getLogger(__name__)

class ThorlabsKDC101(IDCPIDParameters, IDeviceScanning, GenericKCubeMotorCLI, ThorlabsQcodesInstrument):
    """
    Driver for interfacing with the Thorlabs KDC101 K-Cube Brushed DC Servo Motor
    Controller via the QCoDeS framework and the .NET API.

    This class allows for control and management of the KDC101.

    This class integrates the Thorlabs device, using the .NET API.
    For further .NET API details please refer to:
    .private/DotNetAPI/README.md

    Args:
        name (str): Name of the instrument.
        serial_number (str): The serial number of the Thorlabs device.
        actuator_name: The name of the actuator to be used.
        startup_mode_value: .Net Enum value to be stored in '_startup_mode' and used as 
                            'startupSettingsMode' in 'LoadMotorConfiguration'
            Valid startup modes:
                UseDeviceSettings: Use settings from device
                UseFileSettings: Use settings stored locally
                UseConfiguredSettings: Use one of the above according to chooice in
                                       Kinesis Sortware
        simulation (Optional[bool]): Flag to determine if the device is in simulation mode.
        polling_rate_ms (int): Polling rate in milliseconds for the device.
        dll_directory (Optional[str]): The directory where the DLL files are located.
    Raises:
        ValueError: If the model is not recognized as a known model.
    """
    def __init__(
        self,
        name: str,
        serial_number: str,
        actuator_name: Optional[str] = None,
        startup_mode_value: str = 'UseConfiguredSettings',
        simulation: Optional[bool] = False,
        polling_rate_ms: int = 250,
        dll_directory: Optional[str] = None,
        **kwargs
    ):
        self._actuator_name = actuator_name

        super().__init__(
            name,                                   # Instrument (Qcodes
            serial_number=serial_number,            # IGenericCoreDeviceCLI
            startup_mode_value=startup_mode_value,  # IGenericDeviceCLI
            simulation=simulation,                  # ThorlabsQcodesInstrument
            polling_rate_ms=polling_rate_ms,        # IGenericDeviceCLI
            dll_directory=dll_directory,            # ThorlabsDLLMixin
            **kwargs)

        if '(Simulated)' not in self.model():
            self.snapshot(True)

        self.connect_message()

    def _import_device_dll(self):
        """Import the device-specific DLLs and classes from the .NET API."""
        self._add_dll('Thorlabs.MotionControl.GenericMotorCLI.dll')
        self._add_dll('Thorlabs.MotionControl.KCube.DCServoCLI.dll')
        self._import_dll_class('Thorlabs.MotionControl.KCube.DCServoCLI', 'KCubeDCServo')

    def _get_api_interface_from_dll(self, serial_number: str):
        """Retrieve the API interface for the Thorlabs device using its serial number."""
        return self._dll.KCubeDCServo.CreateKCubeDCServo(serial_number)

    def _post_connection(self):
        """
        Will run after after establishing a connection, updating 'get_idn'
        and adding parameters 'model', 'serial_number' and 'firmware_version'.
        """
        knownmodels = [
            'KDC101'#,
            #'KDC101 (Simulated)'
        ]
        if self.model() not in knownmodels:
            raise ValueError(f"'{self.model()}' is an unknown model.")

    def _post_enable(self):
        """
        This method can be overwritten by a subclass.
        Will run after polling has started and the device/channel is enabled.
        """
        # Load any configuration settings needed by the device/channel
        serial = self._serial_number
        mode = self._startup_mode
        self._configuration = (
            self._api_interface.LoadMotorConfiguration(serial, mode))

        self._configuration.DeviceSettingsName = self._actuator_name
        self._configuration.UpdateCurrentConfiguration()

        self._api_interface.SetSettings(self._api_interface.MotorDeviceSettings, True, False)
        sleep(0.5)
