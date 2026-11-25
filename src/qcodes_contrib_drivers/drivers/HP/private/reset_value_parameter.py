from typing import Any, Union, Optional
from qcodes import ParameterBase
import logging

log = logging.getLogger(__name__)

def reset_value_parameter_factory(base_class: type = ParameterBase) -> type:
    """
    Factory function to create a custom QCoDeS parameter class with reset functionality.

    This function creates a subclass of the given base class (default is `ParameterBase`)
    that includes a method to reset the parameter's value to a predefined default.

    Args:
        base_class (type): The base class to extend, must be a subclass of `ParameterBase`.

    Returns:
        type: A new class that extends the base class with reset functionality.

    Raises:
        TypeError: If the base_class is not a subclass of `ParameterBase`.
    """
    if not issubclass(base_class, ParameterBase):
        raise TypeError("base_class must be a subclass of ParameterBase")

    class FactoryResetValueParameter(base_class):
        """
        Extends a QCoDeS Parameter with a reset_value method and value_after_reset attribute.

        Attributes:
            value_after_reset (Union[Any, Literal[False], None]): The value to reset the
                parameter to when `reset_value` is called.

        Methods:
            reset_value(): Resets the parameter's value to `value_after_reset`.
        """

        def __init__(
            self, 
            value_after_reset: Optional[Union[Any, Literal[False]]] = False, 
            **kwargs: Any
        ) -> None:
            """
            Initializes a new FactoryResetValueParameter instance.

            Args:
                value_after_reset (Optional[Union[Any, Literal[False]]]): The value to reset to.
                    If None or False, the reset functionality is disabled.
                **kwargs: Additional keyword arguments for the base class.
            """
            self.value_after_reset = value_after_reset
            super().__init__(**kwargs)

        def reset_value(self) -> None:
            """Resets the parameter's value to `value_after_reset`, if it is set."""
            if self.value_after_reset is not None:
                self.cache.set(self.value_after_reset)

    return FactoryResetValueParameter
