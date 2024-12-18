import logging
from typing import Optional

log = logging.getLogger(__name__)

from qcodes.utils.helpers import create_on_off_val_mapping


class IGenericCoreDeviceCLI():
    """
    Provides a high-level abstraction for the core functionalities of
    Thorlabs devices when used with the .NET API.
    
    Methods:
        connect: Establishes a connection to the Thorlabs device using its serial number.
        disconnect: Safely disconnects from the Thorlabs device and optionally shuts it down.
        shut_down: Shuts down the Thorlabs device, terminating its operation and releasing resources.
    """
    def __init__(self, *args, serial_number: str, **kwargs):
        super().__init__(*args, **kwargs)

        self._serial_number = str(kwargs.pop('serial_number', serial_number))

        self.add_parameter(
            'busy',
            get_cmd=lambda: self._get_thorlabs_attribute('IsDeviceBusy'),
            docstring='Determine whether this device is busy',
            val_mapping=create_on_off_val_mapping(
                on_val=True, off_val=False)
        )

    def connect(self):
        """Connects to the device using its serial number."""
        try:
            self._api_interface.Connect(self._serial_number)
        except Exception as e:
            self.log.exception(f"Failed to connect to instrument with serial number {self._serial_number}")
            raise

    def disconnect(self, shut_down: bool = False) -> None:
        """
        Disconnects from the device.

        Args:
            shut_down: A flag to indicate if the device should be shut down upon disconnection.
        """
        try:
            self._api_interface.Disconnect(shut_down)
        except Exception as e:
            self.log.exception(
                f"Failed to disconnect from instrument {self._serial_number}. "
                f"Error: {e}"
            )
            raise

    def shut_down(self):
        """Shuts down this device and frees any resources it is using."""
        self._api_interface.ShutDown()

class IGenericRackDevice():
    """
    Specialized interface for defining a Rack system, extending core device functionalities.
    
    This class is a mixin, designed to be used in conjunction with other classes that 
    inherit from IGenericCoreDeviceCLI or its descendants. It provides additional 
    functionalities specific to Rack systems that are part of the .NET API but allows 
    for integration with non-.NET API classes in a Pythonic way.

    It should be mixed to the left of IGenericCoreDeviceCLI or its descendants in the 
    inheritance list to maintain the correct method resolution order (MRO).

    Attributes:
        channel_count: Number of channels of the device, read-only.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not isinstance(self, IGenericCoreDeviceCLI):
            raise TypeError("IGenericRackDevice should only be mixed with "
                            "subclasses of IGenericCoreDeviceCLI")         

        self.add_parameter(
            'channel_count',
            get_cmd=lambda: self._get_thorlabs_attribute('ChannelCount'),
            docstring='Number of channels of the device, read-only.')


class IGenericDeviceCLI():
    """
    Represents the functionalities of a generic Thorlabs device channel,
    enabling control and state management within the QCoDeS framework.
    This interface complements the IGenericCoreDeviceCLI by 
    offering channel-specific functionalities for Thorlabs devices, when 
    interacting with the .NET API.

    Methods:
        disable: Powers down the device channel, permitting manual adjustments.
        enable: Powers up the device channel for automated control.
        identify: Issues a command for the device channel to identify itself, typically through an indicator like an LED.
        get_settings: Retrieves the current device channel settings into a specified data structure.
        set_settings: Applies a given settings data structure to the device channel.
        start_polling: Initiates a polling loop for continuous device channel status updates.
        stop_polling: Terminates the polling loop.
        settings_initalized: Verifies if the device channel settings have been initialized.
        settings_known: Checks if the device channel settings are available.
        wait_settings_initalized: Blocks execution until the device channel settings are initialized.
        shut_down: Turns off the device channel and frees associated resources.
    """
    def __init__(self, *args,
                 polling_rate_ms: int = 250,
                 api_interface=None,
                 startup_mode_value: Optional[str] = None,
                 **kwargs):

        from .qcodes_thorlabs_integration import ThorlabsMixin
        if not isinstance(self, ThorlabsMixin):
            raise TypeError("IGenericDeviceCLI should only be mixed with "
                            "subclasses of ThorlabsMixin")            

        self._polling_rate_ms = kwargs.pop('polling_rate_ms', polling_rate_ms)
        self._set_api_interface(kwargs.pop('api_interface', api_interface))
        self._set_startup_mode_value(kwargs.pop('startup_mode_value', startup_mode_value))

        super().__init__(*args, **kwargs)

        if hasattr(self, '_edit_startup_mode'):
            self._edit_startup_mode()

        self._intialize_IGenericDeviceCLI()

        if 'busy' not in self.parameters:
            self.add_parameter(
                'busy',
                get_cmd=lambda: self._get_thorlabs_attribute('IsDeviceBusy'),
                docstring='Determine whether this device is busy',
                val_mapping=create_on_off_val_mapping(
                    on_val=True, off_val=False)
            )        

    def _intialize_IGenericDeviceCLI(self):
        """
        Perform initialization of the decice/channel by executing these steps:
        * wait for settings to be initalized
        * start polling
        * enable decice/channel
        * calls '_post_enable' for device/channel specific initialization
        """

        if not self.settings_initalized():
            self.wait_settings_initalized()
            assert self.settings_initalized() is True

        self.start_polling()
        self.enable()

        self._post_enable()

    def _post_enable(self):
        """
        This method can be overwritten by a subclass.
        Will run after polling has started and the device/channel is enabled.
        """
        # Load any configuration settings needed by the device/channel
        pass

    def _set_startup_mode_value(self, mode: Optional[str]) -> None:
        """
        Sets '_startup_mode_value' representing the source of startup settings
        based on 'mode'. If 'mode' is None, the function 
        will return without changing '_startup_mode_value'.

            Valid startup modes:
                UseDeviceSettings: Use settings from device
                UseFileSettings: Use settings stored locally
                UseConfiguredSettings: Use one of the above according to chooice in
                                       Kinesis Sortware

        to acess this choice in the Kinesis Software:
            make sure the following is unchecked:
                File -> Options -> Application -> [ ] Use Device Persisted settings
            then choose Startup Setting Source:
                File -> Options -> Devices -> Startup Settings Source

        Args:
            mode (str): A string that determines the source of the settings to use.
                                It must be one of 'UseDeviceSettings', 'UseFileSettings', or 'UseConfiguredSettings'.

        Raises:
            ValueError: If the provided mode is not one of the accepted modes.
        """
        if mode is None:
            return

        valid_modes = ['UseDeviceSettings', 'UseFileSettings', 'UseConfiguredSettings']

        if mode not in valid_modes:
            raise ValueError(f"Invalid mode: '{mode}'. Must be one of {valid_modes}.")

        self._startup_mode_value = mode

    def _edit_startup_mode(self) -> None:
        """
        Sets '_startup_mode' as a .Net Enum representing the source of startup settings
        based on 'self._startup_mode_value'. If 'self._startup_mode_value' does not exit,
        the function will return without changing '_startup_mode'.

        Raises:
            ValueError: If the provided mode is not one of the accepted modes.
        """
        if not hasattr(self, '_set_startup_mode_value'):
            return

        mode = self._startup_mode_value
        valid_modes = ['UseDeviceSettings', 'UseFileSettings', 'UseConfiguredSettings']
        if mode not in valid_modes:
            raise ValueError(f"Invalid mode: '{mode}'. Must be one of {valid_modes}.")

        mode_enum = None
        if hasattr(self, '_dll'):
            if hasattr (self._dll, 'DeviceConfiguration'):
                mode_enum = self._dll.DeviceConfiguration.DeviceSettingsUseOptionType
        elif hasattr(self.parent, '_dll'):
            if hasattr (self.parent._dll, 'DeviceConfiguration'):
                mode_enum = self.parent._dll.DeviceConfiguration.DeviceSettingsUseOptionType

        if mode_enum is not None:
            self._startup_mode = mode_enum.Parse(mode_enum, mode)
        else:
            raise AttributeError("Neither self nor parent has '_dll.DeviceConfiguration'")

    def disable(self) -> None:
        """
        Disables this device/channel.
        This option takes the power off the device/channel allowing it to be moved by hand.
        """
        self._api_interface.DisableDevice()

    def enable(self) -> None:
        """Enables this device/channel."""
        self._api_interface.EnableDevice()

    def identify(self):
        """
        Send a command to the device/channel to make it identify itself. 
        This will usually result in an LED or a status panel on the device/channel flashing. 
        """
        self._api_interface.IdentifyDevice()

    def get_settings(self, settings_data) -> None:
        """
        Uploads the settings from the device/channel into the supplied data structure.

        Args:
        settings_data: settings data structure that recieves data
        """
        self._api_interface.GetSettings(settings_data)

    def set_settings(self, settings_data, persist: bool = False) -> None:
        """
        Downloads the supplied settings to the device/channel.

        Args:
            settings_data: settings data structure
            persist (bool): If True the device/channel writes settings to eeprom
        """
        self._api_interface.SetSettings(settings_data, persist)

    def persist_settings(self) -> None:
        """
        Persist the current device settings to EEprom.
        """
        self._api_interface.PersistSettings()

    def start_polling(self):
        """Starts the polling loop."""
        self._api_interface.StartPolling(self._polling_rate_ms)

    def stop_polling(self):
        """Stops the polling loop."""
        self._api_interface.StopPolling()

    def settings_known(self):
        """Determines whether the settings for this device are available."""
        return self._api_interface.IsSettingsKnown()

    def settings_initalized(self):
        """Determine if the devices settings have been uploaded from the device."""
        return self._api_interface.IsSettingsInitialized()

    def wait_settings_initalized(self, timeout_ms: int = 10000):
        """Stops the polling loop."""
        self._api_interface.WaitForSettingsInitialized(timeout_ms)

    def shut_down(self):
        """Shuts down this device and frees any resources it is using."""
        self._api_interface.ShutDown()


class ILockableDeviceCLI():
    """
    Interface to allow locking a device. 

    The ILockableDeviceCLI allows a host system (for instance Kinesis) to lock 
    a hardware device therefore prohibiting human interface.
    This will stop the device reacting to the hardware controls. 

    Attributes:
        front_panel_locked
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self._get_thorlabs_attribute('CanDeviceLockFrontPanel'):
            self.add_parameter(
                'front_panel_locked',
                docstring='Stop the device reacting to the hardware controls.',
                get_cmd=lambda: self._get_thorlabs_attribute(getter_name='GetFrontPanelLocked'),
                set_cmd=lambda x: self._set_thorlabs_attribute(x, getter_name='SetFrontPanelLock'),
                val_mapping=create_on_off_val_mapping(
                    on_val=True, off_val=False)
            )        


class IDeviceScanning:
    """
    IDeviceMaintenance interface definition. 
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
