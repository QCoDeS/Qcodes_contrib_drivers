import atexit
import importlib
import logging
import math
import os
import sys
from decimal import Decimal as PyDecimal
from typing import Dict, Optional, Union

import numpy as np
from qcodes import Instrument
from qcodes.instrument.channel import InstrumentModule
from qcodes.utils.validators import Validator, range_str
import clr
from System import Decimal as DotNetDecimal
from System import Enum as DotNetEnum

from .DeviceManagerCLI import IGenericCoreDeviceCLI

log = logging.getLogger(__name__)


class ThorlabsMixin:
    """
    A mixin class for integrating with Thorlabs .NET API alongside QCoDeS InstrumentBase
    classes (Instrument, InstrumentChannel, InstrumentModule). It facilitates the conversion
    and management of .NET Decimals, Enums, and provides streamlined access to device attributes.
    Before utilizing methods in this class, `_set_api_interface` must be invoked to set up the
    connection to the Thorlabs device API.

    Attributes:
        _api_interface: Direct interface to the Thorlabs device API object if available.
        _api_interface_getter: Method to retrieve the API object if direct access isn't used.
        _api_interface_setter: Method to set the API object if direct access isn't used.

    Methods:
        _set_api_interface: Binds the API interface to the Thorlabs device for further interactions.
        _get_thorlabs_attribute: Fetches a value from a Thorlabs device attribute.
        _set_thorlabs_attribute: Assigns a value to a Thorlabs device attribute.
        _get_thorlabs_decimal: Retrieves a Thorlabs attribute value as a Python Decimal.
        _set_thorlabs_decimal: Sets a Thorlabs attribute value, converted to a .NET Decimal.
        _get_thorlabs_enum: Gets the string representation of a Thorlabs .NET Enum value.
        _set_thorlabs_enum: Sets a Thorlabs .NET Enum value from its string representation.

    Raises:
        ValueError: If invalid arguments are provided for API interface methods or attribute operations.
        AttributeError: If API interface methods are invoked before setting the interface or if an
                        attribute/getter/setter is not found in the API object.
        AssertionError: If logic errors are detected in attribute operation methods.
    """
    def _set_api_interface(self, api_interface: Optional[str]) -> None:
        """
        Sets '_api_interface' to 'api_interface' which represents the 
        .Net API interface objet for this mixin.
        If 'api_interface' is None, the function will return without
        changing '_api_interface'.

        Args:
            api_interface: The .NET API interface for the Thorlabs device.

        Raises:
            ValueError: If an invalid type is provided to the API interface methods.
            AttributeError: If API interface methods are called before the interface
                is set.
            AssertionError: If internal logic errors occur in attribute methods.
        """
        if api_interface is None:
            return
        
        if isinstance(api_interface, str):
            raise ValueError("api_interface should not be a string.")

        self._api_interface = api_interface

    def _get_thorlabs_attribute(
        self, 
        attribute_key: Optional[str] = None,
        getter_name: Optional[str] = None,
    ):
        """
        Retrieve the value of a Thorlabs attribute using either the attribute
        key or the getter method name.

        Args:
            attribute_key (Optional[str]): The key of the attribute to retrieve.
            getter_name (Optional[str]): The name of the getter method to use for
                retrieving the attribute.

        Returns:
            Any: The value of the Thorlabs attribute.

        Raises:
            ValueError: If neither or both of attribute_key and getter_name are provided.
            AttributeError: If the API interface is not set or the attribute/getter
                is not found.
            AssertionError: If an internal logic error occurs.
        """
        has_attribute_key = attribute_key is not None
        has_getter_name = getter_name is not None
        has_api_interface_getter = hasattr(self, '_api_interface_getter')

        if sum([has_attribute_key, has_getter_name]) != 1:
            raise ValueError("Provide only one of: attribute_key, getter_name, getter")

        if has_api_interface_getter:
            if not has_attribute_key:
                raise ValueError("For use with api_interface_getter only attribute_key can be provided")
            else:
                return getattr(self._api_interface_getter(), attribute_key)
        else:
            if not hasattr(self, '_api_interface'):
                raise AttributeError("'_set_api_interface' needs to be called first.")
            if has_getter_name:
                getter = getattr(self._api_interface, getter_name)
                return getter()
            elif has_attribute_key:
                return getattr(self._api_interface, attribute_key)

        raise AssertionError("_get_thorlabs_attribute should have returned by now. Therefore there is a bug in it.")

    def _set_thorlabs_attribute(
        self,
        value,
        attribute_key: Optional[str] = None,
        setter_name: Optional[str] = None
    ) -> None:
        """
        Set the value of a Thorlabs attribute using either the attribute key or
        the setter method name.

        Args:
            value (Any): The value to set for the attribute.
            attribute_key (Optional[str]): The key of the attribute to set.
            setter_name (Optional[str]): The name of the setter method to use for
                setting the attribute.

        Raises:
            ValueError: If neither or both of attribute_key and setter_name are provided.
            AttributeError: If the API interface is not set or the attribute/setter
                is not found.
            AssertionError: If an internal logic error occurs.
        """
        has_attribute_key = attribute_key is not None
        has_setter_name = setter_name is not None
        has_api_interface_getter = hasattr(self, '_api_interface_getter')
        has_api_interface_setter = hasattr(self, '_api_interface_setter')

        if sum([has_attribute_key, has_setter_name]) != 1:
            raise ValueError("Provide only one of: attribute_key, setter_name, setter.")

        if has_api_interface_getter:
            if not has_attribute_key:
                raise ValueError("For use with api_interface_setter only attribute_key can be provided")
            elif not has_api_interface_setter:
                raise ValueError('api_interface_setter not found')
            else:
                api_object = self._api_interface_getter()
                setattr(api_object, attribute_key, value)
                self._api_interface_setter(api_object)
        else:
            if not hasattr(self, '_api_interface'):
                raise AttributeError("'_set_api_interface' needs to be called first.")
            if has_setter_name:
                setter = getattr(self._api_interface, setter_name)
                setter(value)
            elif has_attribute_key:
                setattr(self._api_interface, attribute_key, value)

        raise AssertionError("_get_thorlabs_attribute should have returned by now. Therefore there is a bug in it.")

    def _get_thorlabs_decimal(
        self,
        attribute_key: Optional[str] = None,
        getter_name: Optional[str] = None
    ) -> Optional[PyDecimal]:
        """
        Retrieve the value of a Thorlabs attribute as a Python Decimal, assuming
        the attribute is a .NET Decimal.

        Args:
            attribute_key (Optional[str]): The key of the attribute to retrieve.
            getter_name (Optional[str]): The name of the getter method to use for
                retrieving the attribute.

        Returns:
            Optional[PyDecimal]: The value of the attribute as a Python Decimal,
                or None if the attribute is None.

        Raises:
            ValueError: If neither or both of attribute_key and getter_name are provided.
            AttributeError: If the API interface is not set or the getter
                is not found.
            AssertionError: If an internal logic error occurs.
        """
        raw_value = self._get_thorlabs_attribute(attribute_key, getter_name)
        return PyDecimal(raw_value.ToString()) if raw_value is not None else None

    def _set_thorlabs_decimal(
        self,
        value: PyDecimal,
        attribute_key: Optional[str] = None,
        setter_name: Optional[str] = None
    ) -> None:
        """
        Set the value of a Thorlabs attribute, assuming the attribute is a .NET Decimal,
        using either the attribute key or the setter method name.

        Args:
            value (PyDecimal): The Python Decimal value to set for the attribute.
            attribute_key (Optional[str]): The key of the attribute to set.
            setter_name (Optional[str]): The name of the setter method to use for
                setting the attribute.

        Raises:
            ValueError: If neither or both of attribute_key and setter_name are provided,
                or if the value cannot be converted to a .NET Decimal.
            AttributeError: If the API interface is not set or the setter
                is not found.
            AssertionError: If an internal logic error occurs.
        """
        self._set_thorlabs_attribute(DotNetDecimal(value), attribute_key, setter_name)

    def _get_thorlabs_enum(
        self,
        attribute_key: Optional[str] = None,
        getter_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Retrieve the string representation of a Thorlabs attribute value, assuming
        the attribute is a .NET Enum.

        Args:
            attribute_key (Optional[str]): The key of the attribute to retrieve.
            getter_name (Optional[str]): The name of the getter method to use for
                retrieving the attribute.

        Returns:
            Optional[str]: The string representation of the .NET Enum value, or
                None if the attribute is None.

        Raises:
            ValueError: If neither or both of attribute_key and getter_name are provided.
            AttributeError: If the API interface is not set or the getter
                is not found.
            AssertionError: If an internal logic error occurs.
        """
        raw_value = self._get_thorlabs_attribute(attribute_key, getter_name)
        return raw_value.ToString() if raw_value is not None else None

    def _set_thorlabs_enum(
        self,
        value: str,
        attribute_key: Optional[str] = None,
        setter_name: Optional[str] = None
    ) -> None:
        """
        Set the value of a Thorlabs attribute, assuming the attribute is a .NET Enum,
        using either the attribute key or the setter method name.

        Args:
            value (str): The string representation of the .NET Enum value to set.
            attribute_key (Optional[str]): The key of the attribute to set.
            setter_name (Optional[str]): The name of the setter method to use for
                setting the attribute.

        Raises:
            ValueError: If neither or both of attribute_key and setter_name are provided,
                or if the value cannot be parsed as the appropriate .NET Enum.
            AttributeError: If the API interface is not set or the setter
                is not found.
            AssertionError: If an internal logic error occurs.
        """
        # Retrieve the current enum class for validation
        raw_value = self._get_thorlabs_attribute(attribute_key)
        if not isinstance(raw_value, DotNetEnum):
            raise ValueError("Not a .NET enum.")
        
        # Parse the new enum value
        # dot_net_enum = raw_value.__class__
        # new_enum = dot_net_enum.Parse(dot_net_enum, value)
        new_enum = raw_value.Parse(raw_value, value)

        # Set the new enum value
        self._set_thorlabs_attribute(new_enum, attribute_key, setter_name)

class ThorlabsObjectWrapper(ThorlabsMixin, InstrumentModule):
    """
    Wraps a Thorlabs API object to integrate with a QCoDeS InstrumentModule.

    The class enables access to Thorlabs API objects that can be retrieved
    via an object key or accessor names (getter and setter). It should be used
    within a ThorlabsMixin instance.

    Attributes:
        _object_key: The key to access the Thorlabs API object directly from the parent's API interface.
        _getter_name: Name of the getter function in the Thorlabs API interface.
        _setter_name: Name of the setter function in the Thorlabs API interface.
        parent: The parent ThorlabsMixin instance associated with this object.

    Raises:
        ValueError: If the parent instance is not a ThorlabsMixin, or if incorrect parameters are provided.
        AttributeError: If the Thorlabs API object cannot be accessed with the given object key or accessors.
        TypeError: If the object_key, getter_name, or setter_name parameters are not of string type.
    """
    def __init__(
        self,
        parent,
        name,
        object_key: Optional[str] = None,
        getter_name: Optional[str] = None,
        setter_name: Optional[str] = None,
        **kwargs
    ) -> None:
        super().__init__(parent, name, **kwargs)

        if not isinstance(self.parent, ThorlabsMixin):
            raise ValueError("The parent of this isinstance should be a ThorlabsMixin")

        if not hasattr(self.parent, '_api_interface'):
            raise AttributeError("'_set_api_interface' of the parent "
                                 "should already have been called.")

        has_object_key = object_key is not None
        has_getter = getter_name is not None
        has_setter = setter_name is not None
        has_accessor = has_getter or has_setter

        if sum([has_object_key, has_accessor]) != 1:
            raise ValueError("Either object_key or getter_name/(setter_name) have to be provided, not both.")

        if has_setter and not has_getter:
            raise ValueError("setter_name cannot be provided without getter_name.")

        if has_object_key:
            if not isinstance(object_key, str):
                raise TypeError(f"Expected object_key to be a string or None, got {type(object_key)} instead.")

            try:
                api_interface = getattr(self.parent._api_interface, object_key)
            except AttributeError:
                raise ValueError(f"Object key {object_key} not found in parent._api_interface")

            self._set_api_interface(api_interface)
        
        if has_getter:
            if not isinstance(getter_name, str):
                raise TypeError(f"Expected getter_name to be a string or None, got {type(getter_name)} instead.")

            self._set_api_interface(None)

            try:
                api_interface_getter = getattr(self.parent._api_interface, getter_name)
            except AttributeError:
                raise ValueError(f"Getter {getter_name} not found in parent._api_interface")

            if not callable(api_interface_getter):
                raise ValueError(f"Getter {getter_name} is not callable")

            self._api_interface_getter = api_interface_getter
            
        if has_setter:
            if not isinstance(setter_name, str):
                raise TypeError(f"Expected setter_name to be a string or None, got {type(setter_name)} instead.")
            try:
                api_interface_setter = getattr(self.parent._api_interface, setter_name)
            except AttributeError:
                raise ValueError(f"Setter {setter_name} not found in parent._api_interface")

            if not callable(api_interface_setter):
                raise ValueError(f"Setter {setter_name} is not callable")

            self._api_interface_setter = api_interface_setter


class ThorlabsDLLMixin:
    """
    Manages loading of Thorlabs .NET DLLs, ensuring the Thorlabs devices' required .NET
    assemblies are accessible for QCoDeS instruments. It addresses the initialization
    of these DLLs and encapsulates them for easy reference throughout the implementation.

    Attributes:
        _dll: A container holding references to loaded DLLs.
        _dll_directory: The directory path where Thorlabs Kinesis DLLs are stored.

    Methods:
        __init__: Constructor to initialize the mixin and set up DLL references.
        _set_dll_directory: Sets the DLL directory based on user input or default.
        _add_dll: Adds a reference to a .NET assembly DLL.
        _import_dll_class: Imports a .NET class from a namespace into the DLL container.

    Raises:
        OSError: If the operating system is not compatible (Thorlabs .NET API is Windows-only).
        ImportError: If there is a failure in loading a .NET class from its namespace.
    """
    def __init__(self, *args, dll_directory: Optional[str] = None, **kwargs):
        if sys.platform != "win32":
            self._dll: Optional[DLLContainer] = None
            raise OSError("Thorlabs .Net API Instrument only works on Windows")

        self._set_dll_directory(kwargs.pop('dll_directory', dll_directory))

        super().__init__(*args, **kwargs)

        self._dll = DLLContainer()

    def _set_dll_directory(self, dll_directory: Optional[str]) -> None:
        """
        Sets the directory where Thorlabs Kinesis DLLs are located.

        Args:
            dll_directory (Optional[str]): The directory path provided by the user.
                If None, the default directory is used.
        """
        if dll_directory:
            self._dll_directory = dll_directory
        else:
            program_files_path = os.environ.get("ProgramFiles", "C:\\Program Files")
            self._dll_directory = os.path.join(program_files_path, "Thorlabs", "Kinesis")

    def _add_dll(self, dll_filename: str) -> None:
        """
        Adds the DLL reference for the .NET assembly to the DLL container.

        Args:
            dll_filename (str): The filename of the DLL to add a reference to.

        Raises:
            FileNotFoundError: If the DLL file does not exist at the specified path.
        """
        dll_full_path = os.path.join(self._dll_directory, dll_filename)
        if not os.path.isfile(dll_full_path):
            raise FileNotFoundError(f"The DLL file {dll_full_path} does not exist.")
        clr.AddReference(dll_full_path)

    def _import_dll_class(self, namespace, class_name):
        """
        Imports the specified class from the given namespace into the DLL container.

        Args:
            namespace (str): The namespace of the class to import.
            class_name (str): The name of the class to import.

        Raises:
            ImportError: If the class cannot be loaded from the namespace.
        """
        try:
            module = importlib.import_module(namespace)
            class_ = getattr(module, class_name, None)
            if class_ is not None:
                setattr(self._dll, class_name, class_)
            else:
                error_message = f"Failed to load {class_name} from {namespace}."
                log.error(error_message)
                raise ImportError(error_message)
        except Exception as e:
            log.exception("An unexpected error occurred while importing the DLL class.")
            raise e


class DLLContainer:
    """
    Container class to hold references to loaded .NET DLLs for Thorlabs instruments.
    """
    pass


class ThorlabsQcodesInstrument(IGenericCoreDeviceCLI, ThorlabsDLLMixin, ThorlabsMixin, Instrument):
    """
    Base class for Thorlabs instruments using the .NET API within QCoDeS.

    This class extends QCoDeS Instrument to handle common functionalities for
    Thorlabs devices, such as DLL loading, connection management, and API
    interface initialization.

    Attributes:
        name (str): Identifier for the instrument, used for logging and referencing within QCoDeS.
        serial_number (str): The unique serial number of the Thorlabs device.
        simulation (bool): Indicates if the instrument is being simulated.
        model (Parameter): QCoDeS Parameter representing the device's model.
        firmware_version (Parameter): QCoDeS Parameter representing the device's firmware version.

    Methods:
        get_idn: Retrieves ID information specific to the Thorlabs instrument, overriding the base QCoDeS method.
    """
    def __init__(
        self,
        *args,
        simulation: bool = False,
        **kwargs
    ):
        self._simulation = kwargs.pop('simulation', simulation)
        super().__init__(*args, **kwargs)

        atexit.register(self._exit_generic_device)

        # Import common DLLs.
        try:
            self._add_dll('Thorlabs.MotionControl.DeviceManagerCLI.dll')
            self._import_dll_class('Thorlabs.MotionControl.DeviceManagerCLI', 'DeviceManagerCLI')
            self._import_dll_class('Thorlabs.MotionControl.DeviceManagerCLI', 'DeviceConfiguration')
            self._import_dll_class('Thorlabs.MotionControl.DeviceManagerCLI', 'SimulationManager')
        except Exception as e:
            self.log.error("Failed to import generic Thorlabs  DLLs.")
            raise

        if hasattr(self, '_edit_startup_mode'):
            self._edit_startup_mode()

        # Import device specific DLLs.
        try:
            self._import_device_dll()
        except Exception as e:
            self.log.error(f"Failed to import DLLs for Thorlabs device with serial number {self._serial_number}")
            raise

        # Enable siumulation if self._simulation is True.
        if self._simulation:
            self._dll.SimulationManager.Instance.InitializeSimulations()

        # Connect to instrument.
        try:
            self._dll.DeviceManagerCLI.BuildDeviceList()

            self._set_api_interface(self._get_api_interface_from_dll(self._serial_number))
        
            self.connect()
        except Exception as e:
            self.log.error(f"Failed to connect to Thorlabs device with serial number {self._serial_number}")
            raise

        # Create parameters with device information needed by 'get_idn'
        self._create_idn_parameters()

        # Call '_post_connection' for device specific initalization.
        try:
            self._post_connection()
        except Exception as e:
            self.log.error(f"Failed to initialize Thorlabs {self._model()} with serial number {self._serial_number}")
            raise

    def _exit_generic_device(self) -> None:
        """
        Safely terminate operations at exit by:
        * disconnect the device
        * stop the simulation if needed
        """
        self.disconnect()
        if self._simulation:
            self._dll.SimulationManager.Instance.UninitializeSimulations()

    def _import_device_dll(self):
        """Import the device-specific DLLs and classes from the .NET API."""
        raise NotImplementedError("This method should be implemented by subclasses.")

    def _get_api_interface_from_dll(self, serial_number: str):
        """Retrieve the API interface for the Thorlabs device using its serial number."""
        raise NotImplementedError("This method should be implemented by subclasses.")

    def _post_connection(self):
        """
        Will run after after establishing a connection, updating 'get_idn'
        and adding parameters 'model', 'serial_number' and 'firmware_version'.
        """
        pass

    def _create_idn_parameters(self):
        device_info = self._api_interface.GetDeviceInfo()

        self.add_parameter(
            'model',
            get_cmd=lambda: device_info.Name.strip(),
            docstring='Serial model of the device, read-only.')

        self.add_parameter(
            'serial_number',
            get_cmd=lambda: self._serial_number,
            docstring='Serial number of the device, read-only.')

        self.add_parameter(
            'firmware_version',
            get_cmd=lambda: device_info.FirmwareVersion.ToString(),
            docstring='Serial model of the device, read-only.')

    def get_idn(self) -> Dict[str, str]:
        """
        Overwrites the get_idn method to provide ID information.

        Returns:
            A dictionary containing keys 'vendor', 'model', 'serial', and 
            'firmware', and their corresponding values.
        """
        vendor = 'Thorlabs'
        model = self.model()
        serial = self.serial_number()
        firmware = self.firmware_version()

        idparts = [vendor, model, serial, firmware]

        return dict(zip(("vendor", "model", "serial", "firmware"), idparts))

    def close(self) -> None:
        self.shut_down()
        super().close()


numbertypes = Union[float, int, np.floating, np.integer, PyDecimal]

class PyDecimalNumbers(Validator[numbertypes]):
    """
    Requires a number of type:
        int, float, numpy.integer, numpy.floating, or python Decimal

    Args:
        min_value: Minimal value allowed, default -inf.
        max_value: Maximal value allowed, default inf.

    Raises:
        TypeError: If min or max value not a number. Or if min_value is
            larger than the max_value.
    """

    validtypes = (float, int, np.integer, np.floating, PyDecimal)

    def __init__(
        self,
        min_value: numbertypes = -float("inf"),
        max_value: numbertypes = float("inf"),
    ) -> None:
        if isinstance(min_value, self.validtypes):
            self._min_value = min_value
        else:
            raise TypeError("min_value must be a number")

        valuesok = max_value > min_value

        if isinstance(max_value, self.validtypes) and valuesok:
            self._max_value = max_value
        else:
            raise TypeError("max_value must be a number bigger than min_value")

        self._valid_values = (min_value, max_value)

    def validate(self, value: numbertypes, context: str = "") -> None:
        """
        Validate if number else raises error.

        Args:
            value: A number.
            context: Context for validation.

        Raises:
            TypeError: If not int or float.
            ValueError: If number is not between the min and the max value.
        """
        if not isinstance(value, self.validtypes):
            raise TypeError(f"{value!r} is not an int, float, numpy.integer,"
                            f" numpy.floating, or python Decimal; {context}")

        if not (self._min_value <= value <= self._max_value):
            raise ValueError(
                f"{value!r} is invalid: must be between "
                f"{self._min_value} and {self._max_value} inclusive; {context}"
            )

    is_numeric = True

    def __repr__(self) -> str:
        minv = self._min_value if math.isfinite(self._min_value) else None
        maxv = self._max_value if math.isfinite(self._max_value) else None
        return "<Numbers{}>".format(range_str(minv, maxv, "v"))

    @property
    def min_value(self) -> float:
        return float(self._min_value)

    @property
    def max_value(self) -> float:
        return float(self._max_value)
