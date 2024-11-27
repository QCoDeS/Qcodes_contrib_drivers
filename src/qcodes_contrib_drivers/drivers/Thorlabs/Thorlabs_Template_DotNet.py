import logging
from typing import Optional

from .private.DotNetAPI.<namespace> import <class_name>
from .private.DotNetAPI.qcodes_thorlabs_integration import ThorlabsQcodesInstrument

log = logging.getLogger(__name__)

class <model>(<class_name>, ThorlabsQcodesInstrument):
    """
    Driver for interfacing with the Thorlabs <model> Motorised Rotation Mount
    via the QCoDeS framework and the .NET API.

    This class allows for control and management of the <model>.

    This class integrates the Thorlabs device, using the .NET API.
    For further .NET API details please refer to:
    .private/DotNetAPI/README.md

    Args:
        name (str): Name of the instrument.
        serial_number (str): The serial number of the Thorlabs device.
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
        startup_mode_value: str = '<compare_thorlabs_code_value>', # UseConfiguredSettings, UseDeviceSettings
        simulation: Optional[bool] = False,
        polling_rate_ms: int = 250,
        dll_directory: Optional[str] = None,
        **kwargs
    ):

        super().__init__(
            name,                             # Instrument (Qcodes)
            serial_number=serial_number,      # ThorlabsQcodesInstrument
            startup_mode_value=startup_mode_value,
            simulation=simulation,            # ThorlabsQcodesInstrument
            polling_rate_ms=polling_rate_ms,  # GenericMotoCLI
            dll_directory=dll_directory,      # ThorlabsDLLMixin
            **kwargs)

        if '(Simulated)' not in self.model():
            self.snapshot(True)

        self.connect_message()

    def _import_device_dll(self):
        """Import the device-specific DLLs and classes from the .NET API."""
        # self._add_dll('Thorlabs.MotionControl.GenericMotorCLI.dll')
        self._add_dll('Thorlabs.MotionControl.<name>.dll')
        self._import_dll_class('Thorlabs.MotionControl.<namespace>', '<class_name>')

    def _get_api_interface_from_dll(self, serial_number: str):
        """Retrieve the API interface for the Thorlabs device using its serial number."""
        return self._dll.<class_name>.<create_method>(serial_number)

    def _post_connection(self):
        """
        Will run after after establishing a connection, updating 'get_idn'
        and adding parameters 'model', 'serial_number' and 'firmware_version'.
        """
        knownmodels = [
            '<model>'#,
            #'<model> (Simulated)'
        ]
        if self.model() not in knownmodels:
            raise ValueError(f"'{model}' is an unknown model.")

    def _post_enable(self):
        """
        Will run after polling has started and the device/channel is enabled.
        """
        # Load any configuration settings needed by the device/channel
        serial = self._serial_number
        mode = self._startup_mode
        # self._configuration = self._api_interface.LoadMotorConfiguration(serial, mode)
