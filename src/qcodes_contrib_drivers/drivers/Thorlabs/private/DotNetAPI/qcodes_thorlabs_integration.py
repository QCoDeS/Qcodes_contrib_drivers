import importlib
import logging
import math
import os
import sys
from decimal import Decimal as PyDecimal
from typing import Callable, Dict, Optional, Tuple, Union, Any
import numpy as np
from qcodes import Instrument
from qcodes.instrument.channel import InstrumentModule
from qcodes.utils.validators import Validator, range_str, Enum as QcodesEnumValidator
import clr
from System import (
    Decimal as DotNetDecimal,
    Enum as DotNetEnum,
    FlagsAttribute,
)
from System.Globalization import CultureInfo

from enum import auto, Enum as PyEnum

from .DeviceManagerCLI import IGenericCoreDeviceCLI

log = logging.getLogger(__name__)


class ThorlabsMixin:
    """
    A mixin class for integrating with Thorlabs .NET API alongside QCoDeS InstrumentBase
    classes (Instrument, InstrumentChannel, InstrumentModule). It facilitates the conversion
    and management of .NET Decimals, Enums, and provides streamlined access to device attributes.
    Before utilizing methods in this class, `_set_api_interface` must be invoked to set up the
    connection to the Thorlabs device API.

    Args:
        decimal_as_float (bool): If True, automatically converts .NET Decimal attributes to Python floats.

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
        _get_thorlabs_enum: Retrieves the integer representation of a Thorlabs .NET Enum value.
        _set_thorlabs_enum: Sets a Thorlabs .NET Enum value using its integer representation.
        _get_thorlabs_enum_dict: Creates a dictionary mapping enum names to integer values for use 
                                 with QCoDeS val_mapping.

    Raises:
        ValueError: If invalid arguments are provided for API interface methods or attribute operations.
        AttributeError: If API interface methods are invoked before setting the interface or if an
                        attribute/getter/setter is not found in the API object.
        AssertionError: If logic errors are detected in attribute operation methods.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the ThorlabsMixin.

        Args:
            decimal_as_float (bool): If True, automatically converts .NET Decimal attributes to Python floats.
            **kwargs: Additional keyword arguments for the superclass.

        Raises:
            TypeError: If 'decimal_as_float' is not provided or is not a boolean.
        """
        try:
            self.decimal_as_float = kwargs.pop('decimal_as_float')
        except KeyError:
            raise TypeError("Missing required keyword argument: 'decimal_as_float'") from None

        if not isinstance(self.decimal_as_float, bool):
            raise TypeError(
                f"'decimal_as_float' must be of type bool, got {type(self.decimal_as_float).__name__}"
            )

        log.debug(f"ThorlabsMixin initialized with decimal_as_float={self.decimal_as_float}")

        super().__init__(*args, **kwargs)

    class ApiAccessMode(PyEnum):
        """
        Enum representing the access mode of the Thorlabs API interface.
        """
        DIRECT = auto()
        ACCESSOR = auto()

    def _set_api_interface(self, api_interface: Optional[Any]) -> None:
        """
        Sets the '_api_interface' to 'api_interface' which represents the 
        .NET API interface object for this mixin. If 'api_interface' is None,
        the function will return without changing '_api_interface'.

        Args:
            api_interface (Optional[Any]): The .NET API interface for the Thorlabs device.

        Raises:
            ValueError: If 'api_interface' is a string, which is invalid.
        """
        if api_interface is None:
            log.debug("No API interface provided; skipping _api_interface setup.")
            return

        if isinstance(api_interface, str):
            raise ValueError("api_interface should not be a string.")

        self._api_interface = api_interface
        log.debug(f"API interface set to: {self._api_interface}")

    def _validate_exactly_one(self, **kwargs) -> None:
        """
        Validates that exactly one of the provided keyword arguments is not None.

        Args:
            **kwargs: Variable keyword arguments to check.

        Raises:
            ValueError: If not exactly one argument is provided.
        """
        non_none = [k for k, v in kwargs.items() if v is not None]
        if len(non_none) != 1:
            raise ValueError(f"Provide exactly one of: {', '.join(kwargs.keys())}.")

    def _reflect_dotnet_type(
        self,
        *,
        api_object: Any,
        access_mode: 'ThorlabsMixin.ApiAccessMode',
        attribute_key: Optional[str] = None,
        setter_name: Optional[str] = None
    ) -> Any:
        """
        Reflects on the .NET type of a property or method parameter based on the provided key or setter
        and the access mode.

        Args:
            api_object (Any): The .NET API object.
            access_mode (ThorlabsMixin.ApiAccessMode): The access mode (DIRECT or ACCESSOR).
            attribute_key (Optional[str]): The key of the attribute.
            setter_name (Optional[str]): The name of the setter method.

        Returns:
            Any: The .NET type object (e.g., System.Type).

        Raises:
            AttributeError: If the property or method is not found.
            ValueError: If method does not have exactly one parameter or does not expect a .NET Enum.
        """
        if access_mode == self.ApiAccessMode.ACCESSOR:
            if attribute_key:
                prop_info = api_object.GetType().GetProperty(attribute_key)
                if not prop_info:
                    raise AttributeError(f"Property '{attribute_key}' not found.")
                return prop_info.PropertyType
            else:
                raise ValueError("In ACCESSOR mode, only 'attribute_key' can be provided.")
        elif access_mode == self.ApiAccessMode.DIRECT:
            if setter_name:
                method_info = api_object.GetType().GetMethod(setter_name)
                if not method_info:
                    raise AttributeError(f"Setter method '{setter_name}' not found.")
                params = method_info.GetParameters()
                if len(params) != 1:
                    raise ValueError(f"'{setter_name}' must expect exactly one parameter.")
                return params[0].ParameterType
            elif attribute_key:
                prop_info = api_object.GetType().GetProperty(attribute_key)
                if not prop_info:
                    raise AttributeError(f"Property '{attribute_key}' not found.")
                return prop_info.PropertyType
            else:
                raise ValueError("In DIRECT mode, either 'attribute_key' or 'setter_name' must be provided.")
        else:
            raise AssertionError("Unhandled API access mode.")

    def _get_api_object_and_mode(self, assert_api_setter: bool = True) -> Tuple[Any, 'ThorlabsMixin.ApiAccessMode']:
        """
        Determine the current Thorlabs API object and its access mode.

        Args:
            assert_api_setter (bool): Indicates if a setter must be present when in ACCESSOR mode.

        Returns:
            Tuple[Any, ThorlabsMixin.ApiAccessMode]: A tuple containing the active API object and its access mode.

        Raises:
            AttributeError: If no active Thorlabs API interface is set or if a setter is required but not present.
        """
        has_getter = hasattr(self, '_api_interface_getter')
        has_setter = hasattr(self, '_api_interface_setter')

        if has_getter:
            if assert_api_setter and not has_setter:
                raise AttributeError("Setter method is required but not found in ACCESSOR API interface.")
            api_object = self._api_interface_getter()
            log.debug("API access mode set to ACCESSOR.")
            return api_object, self.ApiAccessMode.ACCESSOR

        if hasattr(self, '_api_interface'):
            api_object = self._api_interface
            log.debug("API access mode set to DIRECT.")
            return api_object, self.ApiAccessMode.DIRECT

        raise AttributeError("No active Thorlabs API interface is set.")

    def _get_thorlabs_attribute(
        self,
        attribute_key: Optional[str] = None,
        getter_name: Optional[str] = None,
    ) -> Any:
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
            ValueError: If neither or both of 'attribute_key' and 'getter_name' are provided.
            AttributeError: If the API interface is not set or the attribute/getter
                            is not found.
            AssertionError: If an internal logic error occurs.
        """
        self._validate_exactly_one(attribute_key=attribute_key, getter_name=getter_name)

        api_object, access_mode = self._get_api_object_and_mode(assert_api_setter=False)

        if access_mode == self.ApiAccessMode.ACCESSOR:
            if not attribute_key:
                raise ValueError("In ACCESSOR mode, only 'attribute_key' can be provided.")
            try:
                value = getattr(api_object, attribute_key)
                log.debug(f"Retrieved attribute '{attribute_key}' via ACCESSOR: {value}")
                return value
            except AttributeError:
                raise AttributeError(f"Attribute '{attribute_key}' not found in ACCESSOR API object.")

        elif access_mode == self.ApiAccessMode.DIRECT:
            if getter_name:
                try:
                    getter = getattr(api_object, getter_name)
                    value = getter()
                    log.debug(f"Retrieved attribute via getter '{getter_name}': {value}")
                    return value
                except AttributeError:
                    raise AttributeError(f"Getter method '{getter_name}' not found in DIRECT API object.")
                except Exception as e:
                    raise AssertionError(f"Error invoking getter '{getter_name}': {e}")
            elif attribute_key:
                try:
                    value = getattr(api_object, attribute_key)
                    log.debug(f"Retrieved attribute '{attribute_key}' via DIRECT access: {value}")
                    return value
                except AttributeError:
                    raise AttributeError(f"Attribute '{attribute_key}' not found in DIRECT API object.")

        raise AssertionError("_get_thorlabs_attribute should have returned by now. Therefore there is a bug in it.")

    def _set_thorlabs_attribute(
        self,
        value: Any,
        attribute_key: Optional[str] = None,
        setter_name: Optional[str] = None,
        api_object_and_mode: Optional[Tuple[Any, 'ThorlabsMixin.ApiAccessMode']] = None
    ) -> None:
        """
        Set the value of a Thorlabs attribute using either the attribute key or
        the setter method name.

        Args:
            value (Any): The value to set for the attribute.
            attribute_key (Optional[str]): The key of the attribute to set.
            setter_name (Optional[str]): The name of the setter method to use for
                setting the attribute.
            api_object_and_mode (Optional[Tuple[Any, ThorlabsMixin.ApiAccessMode]]): 
                A tuple containing the API object and its access mode. If not provided,
                the method will retrieve the API object and mode internally.

        Raises:
            ValueError: If neither or both of 'attribute_key' and 'setter_name' are provided,
                        or if the value type is incompatible with the .NET type.
            AttributeError: If the API interface is not set, the attribute/setter is not found,
                            or if attempting to set on an ACCESSOR interface without a setter.
            AssertionError: If an internal logic error occurs.
        """
        self._validate_exactly_one(attribute_key=attribute_key, setter_name=setter_name)

        if api_object_and_mode is None:
            api_object, access_mode = self._get_api_object_and_mode(assert_api_setter=True)
        else:
            api_object, access_mode = api_object_and_mode

        try:
            dotnet_type = self._reflect_dotnet_type(
                api_object=api_object, 
                access_mode=access_mode, 
                attribute_key=attribute_key, 
                setter_name=setter_name
            )
        except AttributeError as e:
            raise AttributeError(str(e))
        except ValueError as ve:
            raise ValueError(f"Type mismatch when setting: {ve}")

        if access_mode == self.ApiAccessMode.ACCESSOR:
            try:
                setattr(api_object, attribute_key, value)
                self._api_interface_setter(api_object)
                log.debug(f"Set attribute '{attribute_key}' via ACCESSOR to {value}")
            except AttributeError:
                raise AttributeError(f"Attribute '{attribute_key}' not found in ACCESSOR API object.")
            except Exception as e:
                raise AssertionError(f"Error setting attribute '{attribute_key}' via ACCESSOR: {e}")

        elif access_mode == self.ApiAccessMode.DIRECT:
            if setter_name:
                try:
                    setter_method = getattr(api_object, setter_name)
                    setter_method(value)
                    log.debug(f"Set attribute via setter '{setter_name}' to {value}")
                except AttributeError:
                    raise AttributeError(f"Setter method '{setter_name}' not found in DIRECT API object.")
                except Exception as e:
                    raise AssertionError(f"Error invoking setter '{setter_name}': {e}")
            elif attribute_key:
                try:
                    setattr(api_object, attribute_key, value)
                    log.debug(f"Set attribute '{attribute_key}' via DIRECT access to {value}")
                except AttributeError:
                    raise AttributeError(f"Attribute '{attribute_key}' not found in DIRECT API object.")
                except Exception as e:
                    raise AssertionError(f"Error setting attribute '{attribute_key}' via DIRECT access: {e}")
        else:
            raise AssertionError("Unhandled API access mode.")

    def _get_thorlabs_converted(
        self,
        attribute_key: Optional[str] = None,
        getter_name: Optional[str] = None,
        transform: Optional[Callable[[Any], Any]] = None
    ) -> Any:
        """
        Retrieve and optionally transform a Thorlabs attribute.

        Args:
            attribute_key (Optional[str]): The key of the attribute to retrieve.
            getter_name (Optional[str]): The name of the getter method to use for
                retrieving the attribute.
            transform (Optional[Callable[[Any], Any]]): A function to transform the raw value.

        Returns:
            Any: The transformed value if 'transform' is provided, else the raw value.

        Raises:
            AssertionError: If an error occurs during transformation.
            Inherits exceptions from '_get_thorlabs_attribute'.
        """
        raw_value = self._get_thorlabs_attribute(attribute_key, getter_name)
        if transform and raw_value is not None:
            try:
                transformed_value = transform(raw_value)
                return transformed_value
            except Exception as e:
                raise AssertionError(f"Error transforming attribute '{attribute_key or getter_name}': {e}")
        return raw_value

    def _get_thorlabs_decimal(
        self,
        attribute_key: Optional[str] = None,
        getter_name: Optional[str] = None,
        decimal_as_float: Optional[bool] = None
    ) -> Union[PyDecimal, float, None]:
        """
        Retrieve the value of a Thorlabs attribute as a Python Decimal, assuming
        the attribute is a .NET Decimal.

        Args:
            attribute_key (Optional[str]): The key of the attribute to retrieve.
            getter_name (Optional[str]): The name of the getter method to use for
                retrieving the attribute.
            decimal_as_float (Optional[bool]): Override the instance's decimal_as_float setting.

        Returns:
            Union[PyDecimal, float, None]: The value as Decimal, float, or None.

        Raises:
            ValueError: If neither or both of 'attribute_key' and 'getter_name' are provided.
            TypeError: If the received value is neither Decimal nor None.
            AttributeError: If the API interface is not set or the attribute/getter is not found.
            AssertionError: If an internal logic error occurs during transformation.
        """
        convert_to_float = self.decimal_as_float if decimal_as_float is None else decimal_as_float
        raw_value = self._get_thorlabs_attribute(attribute_key, getter_name)
        if raw_value is None:
            return None

        def decimal_transform(raw_value):
            if not isinstance(raw_value, DotNetDecimal):
                raise TypeError(f"Expected a .NET Decimal, got {type(raw_value)} instead.")
            decimal_str = raw_value.ToString(CultureInfo.InvariantCulture)
            if convert_to_float:
                try:
                    value = float(decimal_str)
                    log.debug(f"Converted .NET Decimal {raw_value} to float: {value}")
                except ValueError as e:
                    raise TypeError(f"Failed to convert .NET Decimal '{decimal_str}' to float: {e}")
            else:
                try:
                    value = PyDecimal(decimal_str)
                    log.debug(f"Converted .NET Decimal {raw_value} to Python Decimal: {value}")
                except Exception as e:
                    raise AssertionError(f"Error converting .NET Decimal to Python Decimal: {e}")

            return value

        return self._get_thorlabs_converted(
            attribute_key,
            getter_name,
            transform=decimal_transform
        )

    def _set_thorlabs_decimal(
        self,
        value: Union[PyDecimal, float, int],
        attribute_key: Optional[str] = None,
        setter_name: Optional[str] = None,
        decimal_as_float: Optional[bool] = None
    ) -> None:
        """
        Set the value of a Thorlabs attribute, assuming the attribute is a .NET Decimal,
        using either the attribute key or the setter method name.

        Args:
            value (Union[PyDecimal, float, int]): The Python Decimal value to set for the attribute.
            attribute_key (Optional[str]): The key of the attribute to set.
            setter_name (Optional[str]): The name of the setter method to use for
                setting the attribute.
            decimal_as_float (Optional[bool]): Override the instance's decimal_as_float setting.

        Raises:
            ValueError: If neither or both of 'attribute_key' and 'setter_name' are provided,
                        or if the value cannot be converted to a .NET Decimal.
            AttributeError: If the API interface is not set or the attribute/setter is not found.
            TypeError: If the value type is incompatible with the 'decimal_as_float' setting.
            AssertionError: If an internal logic error occurs during conversion or setting.
        """
        convert_to_float = self.decimal_as_float if decimal_as_float is None else decimal_as_float
        assert_decimal = not convert_to_float

        if isinstance(value, PyDecimal):
            try:
                dot_net_decimal = DotNetDecimal.Parse(str(value), CultureInfo.InvariantCulture)
                log.debug(f"Converted Python Decimal {value} to .NET Decimal: {dot_net_decimal}")
            except OverflowError:
                raise ValueError(f"Cannot convert {value} to .NET Decimal; value out of range.")
            except Exception as e:
                raise AssertionError(f"Error converting Python Decimal to .NET Decimal: {e}")

        if assert_decimal:
            if not isinstance(value, PyDecimal):
                raise TypeError(f"Expected a Python Decimal when decimal_as_float=False, got {type(value)} instead.")
        elif not isinstance(value, PyDecimal):
            if isinstance(value, (float, int)):
                try:
                    dot_net_decimal = DotNetDecimal.Parse(str(value), CultureInfo.InvariantCulture)
                    log.debug(f"Converted {type(value).__name__} {value} to .NET Decimal: {dot_net_decimal}")
                except OverflowError:
                    raise ValueError(f"Cannot convert {value} to .NET Decimal; value out of range.")
                except Exception as e:
                    raise AssertionError(f"Error converting {type(value).__name__} to .NET Decimal: {e}")
            else:
                raise TypeError(f"Unsupported type for setting decimal_as_float=True: {type(value)}")

        self._set_thorlabs_attribute(dot_net_decimal, attribute_key, setter_name)

    def _get_thorlabs_enum(
        self,
        attribute_key: Optional[str] = None,
        getter_name: Optional[str] = None
    ) -> Optional[int]:
        """
        Retrieve a .NET enum as an integer, verifying that the enum's underlying
        type is actually Int32.

        Returns:
            int or None
        """
        raw_value = self._get_thorlabs_attribute(attribute_key, getter_name)
        if raw_value is None:
            return None

        dotnet_type = raw_value.GetType()
        if not dotnet_type.IsEnum:
            raise ValueError("The retrieved property is not a .NET enum.")
        # Verify underlying type is int
        underlying_type = DotNetEnum.GetUnderlyingType(dotnet_type)
        if underlying_type.FullName != "System.Int32":
            raise ValueError(f"Enum '{dotnet_type}' is not an Int32-based enum.")

        numeric_value = int(raw_value)
        log.debug(f"_get_thorlabs_enum: returning int={numeric_value} for '{dotnet_type}'")
        return numeric_value

    def _set_thorlabs_enum(
        self,
        value: int,
        attribute_key: Optional[str] = None,
        setter_name: Optional[str] = None
    ) -> None:
        """
        Set a .NET enum by providing an integer. The method checks if the enum's
        underlying type is Int32, then calls DotNetEnum.ToObject before setting.

        Args:
            value (int): The integer representation of the enum.
        """
        self._validate_exactly_one(attribute_key=attribute_key, setter_name=setter_name)
        api_object, access_mode = self._get_api_object_and_mode(assert_api_setter=True)
        dotnet_type = self._reflect_dotnet_type(
            api_object=api_object,
            access_mode=access_mode,
            attribute_key=attribute_key,
            setter_name=setter_name
        )
        if not dotnet_type.IsEnum:
            raise ValueError("The target property is not a .NET enum.")
        # Verify underlying type is int
        underlying_type = DotNetEnum.GetUnderlyingType(dotnet_type)
        if underlying_type.FullName != "System.Int32":
            raise ValueError(f"Enum '{dotnet_type}' is not an Int32-based enum.")

        # Convert the Python int to a proper .NET enum object
        enum_object = DotNetEnum.ToObject(dotnet_type, value)

        log.debug(f"_set_thorlabs_enum: setting int={value} for '{dotnet_type}'")
        # Use our internal method to set
        self._set_thorlabs_attribute(enum_object, attribute_key, setter_name, (api_object, access_mode))

    def _get_thorlabs_enum_dict(
        self,
        attribute_key: Optional[str] = None,
        getter_name: Optional[str] = None,
        setter_name: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Create a dictionary { 'EnumMemberName': intValue } for the .NET enum linked
        to exactly one of:
          - attribute_key
          - getter_name
          - setter_name
    
        This is useful for QCoDeS 'val_mapping'. For example:
            val_mapping = KLS._get_thorlabs_enum_dict(attribute_key="SomeEnumProp")
    
        Then you can create a parameter like:
            self.add_parameter(
                "some_enum",
                get_cmd=lambda: self._get_thorlabs_enum(attribute_key="SomeEnumProp"),
                set_cmd=lambda val: self._set_thorlabs_enum(val, attribute_key="SomeEnumProp"),
                val_mapping=val_mapping,
                docstring="Example enum"
            )
    
        Raises:
            ValueError: If the property/method is not an Int32-based .NET enum.
            AttributeError: If the reflected property or method is not found.
            AssertionError: If logic errors occur during reflection.
        """
        # Ensure exactly one was provided
        self._validate_exactly_one(
            attribute_key=attribute_key,
            getter_name=getter_name,
            setter_name=setter_name
        )
    
        api_object, access_mode = self._get_api_object_and_mode(assert_api_setter=True)
    
        if getter_name is not None:
            method_info = api_object.GetType().GetMethod(getter_name)
            if not method_info:
                raise AttributeError(f"Getter method '{getter_name}' not found in DIRECT API object.")
            dotnet_type = method_info.ReturnType
    
        else:
            dotnet_type = self._reflect_dotnet_type(
                api_object=api_object,
                access_mode=access_mode,
                attribute_key=attribute_key,
                setter_name=setter_name
            )
    
        if not dotnet_type.IsEnum:
            raise ValueError("The target property/method return type is not a .NET enum.")
    
        underlying_type = DotNetEnum.GetUnderlyingType(dotnet_type)
        if underlying_type.FullName != "System.Int32":
            raise ValueError(f"Enum '{dotnet_type}' is not an Int32-based enum.")
    
        enum_names = list(DotNetEnum.GetNames(dotnet_type))
        enum_dict = {}
        for name in enum_names:
            val = DotNetEnum.Parse(dotnet_type, name)
            enum_dict[name] = int(val)
    
        log.debug(f"_get_thorlabs_enum_dict({attribute_key or getter_name or setter_name}): {enum_dict}")
        return enum_dict



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
        super().__init__(
            parent, 
            name, 
            decimal_as_float=parent.decimal_as_float,
            **kwargs
        )

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
        self.disconnect()
        self.shut_down()
        
        if self._simulation:
            self._dll.SimulationManager.Instance.UninitializeSimulations()

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

