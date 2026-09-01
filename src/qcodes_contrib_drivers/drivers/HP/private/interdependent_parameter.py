import os
from typing import Any, Union, Optional, Callable, List
from typing_extensions import Literal
from qcodes import ParameterBase
import logging

log = logging.getLogger(__name__)

def interdependent_parameter_factory(base_class: type = ParameterBase) -> type:
    """
    Factory function to create a class extending a given base class with interdependency features.

    Args:
        base_class (type): The base class to extend, must be a subclass of `ParameterBase`.

    Returns:
        A class that extends the given `base_class` with interdependency capabilities.

    Raises:
        TypeError: If the `base_class` is not a subclass of `ParameterBase`.
    """
    if not issubclass(base_class, ParameterBase):
        raise TypeError("base_class must be a subclass of ParameterBase")


    class FactoryInterdependentParameter(ParameterBase):
        """
        Extends `ParameterBase` to handle interdependencies with other parameters.
        
        This class allows the parameter to be dependent on other parameters,
        triggering update actions when those parameters change.
        `InterdependentParameters` can only depend on other `InterdependentParameters`.
    
        Attributes:
            dependent_on (List[str] or Literal[False]): Names of parameters this parameter depends on.
            update_method (Callable or Literal[False]): Method called when a dependent parameter changes.
        """
    
        def __init__(
            self,
            get_cmd: Optional[Union[str, Callable[..., Any], Literal[False]]] = None,
            set_cmd: Optional[Union[str, Callable[..., Any], Literal[False]]] = False,
            update_method: Optional[Union[Callable[..., Any], Literal[False]]] = False,
            dependent_on: Optional[Union[List[str], Literal[False]]] = False,
            docstring: Optional[str] = None,
            **kwargs: Any
        ) -> None:
            super().__init__(get_cmd=None, set_cmd=False, docstring=docstring, **kwargs)
            self.get_cmd = get_cmd
            self.set_cmd = set_cmd
            self.update_method = update_method
            self._dependent_on = dependent_on
            self._dependent_parameter_list = []
            self.docstring = docstring
    
            if self._dependent_on:
                for dependent in dependent_on:
                    parameter = getattr(self.instrument, dependent)
                    parameter.add_dependent_parameter(self)
    
        @property
        def dependent_on(self) -> Union[List[str], Literal[False]]:
            """
            Return list of parameter names that this parameter depends on.
        
            Returns:
                A list of strings representing the names of dependent parameters,
                or False if there are none.
            """
            return self._dependent_on
    
        def add_dependent_parameter(self, dependent_parameter: 'FactoryInterdependentParameter') -> None:
            """
            Adds a parameter to the list of dependent parameters.
    
            This method is used to register another parameter as dependent on this parameter.
            When the value of this parameter changes, the registered dependent parameter 
            is updated accordingly.
    
            Args:
                dependent_parameter: The parameter to add as a dependent.
            """        
            self._dependent_parameter_list.append(dependent_parameter)
    
        def get_raw(self) -> Any:
            """
            Retrieves the raw value of the parameter, executing any update actions if the parameter has changed.
    
            This method is a core part of the QCoDeS parameter interface. It is used to get the current value of the 
            parameter from the instrument. If the parameter is dependent on others, it also triggers the update 
            mechanism for those parameters.
    
            Returns:
                The raw value of the parameter.
            """        
            if isinstance(self.get_cmd, str):
                raw_value = self.instrument.ask(self.get_cmd)
            elif isinstance(self.get_cmd, Callable):
                raw_value = self.get_cmd()
            else:
                if hasattr(self, 'val_mapping'):
                    raw_value = self.val_mapping[self.cache.get()]
                else:
                    raw_value = self.cache.get()

            self._execute_on_change(raw_value)
            return raw_value
    
        def set_raw(self, raw_value: Union[float, int, str]) -> None:
            """
            Sets the raw value of the parameter, executing any update actions if the parameter changes.
    
            This method is a core part of the QCoDeS parameter interface. It is used to set the value of the 
            parameter on the instrument. If the parameter is dependent on others, it also triggers the update 
            mechanism for those parameters.
    
            Args:
                raw_value: The new value to set for the parameter.
            """        
            if isinstance(self.set_cmd, str):
                self.instrument.write(self.set_cmd.format(raw_value))
            elif callable(self.set_cmd):
                self.set_cmd(raw_value)
    
            self._execute_on_change(raw_value)
    
        def update_docstring(self) -> None:
            """
            Updates the docstring of the parameter to reflect its current state.
    
            This method constructs a new docstring based on the parameter's name, 
            label, unit, and validator (`vals`). It appends any additional documentation
            provided in `self.docstring` to the automatically generated docstring.
            This is useful for keeping the documentation of the parameter up-to-date with 
            its runtime state.
            """
            self.__doc__ = os.linesep.join(
                (
                    "Parameter class:",
                    "",
                    f"* `name`: {self.name}",
                    f"* `label`: {self.label}",
                    f"* `unit`: {self.unit}",
                    f"* `vals`: {repr(self.vals)}",
                )
            )
            if self.docstring is not None:
                self.__doc__ = os.linesep.join((self.docstring, "", self.__doc__))
    
        def _execute_on_change(self, raw_value: Union[float, int, str]) -> None:
            """
            Executes the update method for all dependent parameters when this parameter's value changes.
    
            This private method is called whenever the value of this parameter is read or set. It compares the 
            new value with the cached value, and if they differ, it updates the cache and calls the `update_method` 
            for each parameter that depends on this one. This ensures that changes in this parameter's value 
            propagate to all dependent parameters.
    
            Args:
                raw_value: The new raw value of the parameter.
            """        
            value = self._from_raw_value_to_value(raw_value)
            if self.cache.get(False) != value:
                self.cache.set(value)
                for parameter in self._dependent_parameter_list:
                    if parameter.update_method:
                        parameter.update_method()
                        parameter.update_docstring()
                        parameter.get()
                if self.update_method:
                    self.update_method()
                    self.update_docstring()

    return FactoryInterdependentParameter
