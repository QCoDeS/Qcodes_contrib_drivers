import unicodedata
import os
import time
import matplotlib.pyplot as plt
import json
import re
import qcodes as qc
from enum import auto
from strenum import StrEnum
from qcodes.instrument import VisaInstrument, InstrumentModule
from qcodes import Parameter
from qcodes.validators import Ints, Numbers, MultiTypeOr, Enum, Bool
from types import SimpleNamespace
from typing import Union, Any, Optional

from qcodes_contrib_drivers.drivers.Lakeshore.Contact_Check_Plots import show_contact_check_results, plot_check, apply_plot_style

class M91_FastHall(VisaInstrument):
    """
    Driver class for the Lakeshore M91 FastHall Controller.
    """      

    def __init__(self, name: str, address: str, **kwargs: Any):
        super().__init__(name, address, terminator='\n', **kwargs)

        self.connect_message()

        self.add_parameter(name='keypad_lock',
                label='keypad lock status',
                get_cmd='SYSTem:KLOCk?',
                get_parser = lambda status: True if int(status) == 1 else False,
                set_cmd='SYSTem:KLOCk {}',
                val_mapping={True: 1, False: 0}
                )
        
        # Lock keypad at start up
        self.keypad_lock(True)
            
        self.add_submodule("Resistivity", Resistivity(self, "Resistivity", "RESISTIVITY"))
        self.add_submodule("DCHall", DCHall(self, "DCHall", "HALL:DC"))
        self.add_submodule("ContactCheck", ContactCheck(self, "ContactCheck", "CCHECK"))
        self.add_submodule("FourWire", FourWire(self, "FourWire", "FWIRE"))

        self.add_parameter(name="sample_type",
                           set_cmd=lambda value: self._sample_type_setter(value),
                           label="sample_type",
                           vals=Enum("van_der_Pauw", "Hall_bar"),
                           initial_value="van_der_Pauw")

    def _sample_type_setter(self, value: str) -> None:
        value = sample_type(value)
        if value == self.sample_type():
            pass
        else:
            if value == "Hall_bar":
                self.ContactCheck.auto_optimise(False)
                del self.ContactCheck.parameters["auto_optimise"]
                self.Resistivity.auto_optimise(False)
                del self.Resistivity.parameters["auto_optimise"]
                self.Resistivity.add_parameter(name="width", parameter_class=BoundedValueParameter, value=0, min_val=0, unit="m")
                self.Resistivity.add_parameter(name="separation", parameter_class=BoundedValueParameter, value=0, min_val=0, unit="m")
                del self.submodules["FastHall"]

            elif value == "van_der_Pauw":
                self.add_submodule("FastHall", FastHall(self, "FastHall", "FASTHALL"))
                self.ContactCheck.add_parameter(name="auto_optimise", set_cmd=lambda value: self.ContactCheck.optimise_setter(value), label="auto_optimise", vals=Bool(), initial_value=True)
                self.Resistivity.add_parameter(name="auto_optimise", set_cmd=lambda value: self.Resistivity.optimise_setter(value), label="auto_optimise", vals=Bool(), initial_value=True)
                try:
                    del self.Resistivity.parameters["width"]
                    del self.Resistivity.parameters["separation"]
                except Exception as e:
                    pass

    def display_measurement_results(self, results: SimpleNamespace) -> None:
        """
        Function can be used to print the results output of four wire 
        measurement functions, resistivity measurement functions and 
        Hall measurement functions in a more readable format. 
        """
        if isinstance(results, SimpleNamespace):
            dictionary = results.__dict__ # create a dictionary from the data 
            # print the set-up parameters 
            print('-----------------------') 
            print('Setup:') 
            print('-----------------------')
            for k in dictionary.get('Setup').__dict__:
                words = re.findall('[A-Z][^A-Z]*', k)
                print(f"{' '.join(words)}: {dictionary.get('Setup').__dict__.get(k)}")
            print('-----------------------') 
            # print the results 
            print('Results:') 
            print('-----------------------') 
            for k in dictionary.keys(): 
                if k == 'Setup': # skip the setup namespace because this is all printed above 
                    continue
                words = re.findall('[A-Z][^A-Z]*', k)
                print(f"{' '.join(words)}: {dictionary.get(k)}")
            print('-----------------------') 
        else: 
            print('Data is not of the correct type. Data should be of type SimpleNamespace.')

    def read_error_queue(self): 
        """
        Queries the error/event queue for all the unread items and removes them
        from the queue.
        """
        err = self.ask("SYST:ERR:ALL?")
        return err
        
    def close(self) -> None:
        """
        Close connection to device.
        """
        # Unlock keypad on exit
        self.keypad_lock(False)
        
        super().close()
        print('Connection closed to M91.')

class MeasureModule(InstrumentModule):
    """
    InstrumentModule class for the different measurement functions of the M91.
    Includes reset, get_running_status, get_results and get_all_results functions.
    """
    def __init__(self, parent: M91_FastHall, name: str, cmd_name: str, **kwargs: Any) -> None:
        super().__init__(parent, name, **kwargs)
        self.cmd_name = cmd_name # e.g 'FWIRE' for command string

    def reset(self) -> None:
        """
        Resets the measurement to a not run state, cancelling any running measurement.
        Removes any data from the previously run measurement.
        """
        cmd = f"{self.cmd_name}:RESET"
        self.parent.write(cmd)
        print(f"{self.cmd_name} measurement reset.")

    def get_running_status(self) -> bool:
        """
        Indicates if this measurement is running.
        """
        cmd = f"{self.cmd_name}:RUNNING?"
        return bool(int(self.parent.ask(cmd)))

    def get_results(self) -> Optional[SimpleNamespace]:
        """
        Returns a dictionary representing the summary results of the last run measurement.
        """
        cmd = f"{self.cmd_name}:RESULT:JSON? 0"
        try:
            json_results = self.parent.ask(cmd)
        except:
            print("Error getting results - no results available. Perhaps measurement has not yet been run.")
            return None
        else:
            measurement_results: SimpleNamespace = json.loads(json_results, object_hook=lambda d: SimpleNamespace(**d))
            return measurement_results

    def get_all_results(self) -> Optional[SimpleNamespace]:
        """
        Returns a dictionary representing all measurement data from the last run measurement.
        """
        cmd = f"{self.cmd_name}:RESULT:JSON:ALL? 0"
        try:
            json_results = self.parent.ask(cmd)
        except:
            print("Error getting results - no results available. Perhaps measurement has not yet been run.")
            return None
        else:
            measurement_results: SimpleNamespace = json.loads(json_results, object_hook=lambda d: SimpleNamespace(**d))
            return measurement_results

class BoundedValueParameter(Parameter):
    """
    Parameter class for coerced values. 'min_val' and 'max_val' determine the bounds on this parameter -
    if not specified they will be -inf & inf.
    When setting the value of a BoundedValueParameter, if the value falls outside the bounds, then the min/max
    value will be set instead (see 'set_raw' method below).
    By default, the validator allows any values from 'Numbers()', set 'integer' to True to change the
    validator to 'Ints()' only.
    """
    def __init__(self, name: str, value: float | int | None = None, min_val: float | int = -float("inf"),
                 max_val: float | int = float("inf"), unit: str | None = None, integer: bool = False, **kwargs: Any):
        super().__init__(
            name,
            vals=Ints() if integer else Numbers(),
            unit=unit,
            label=name,
            **kwargs
        )
        self.value = value
        self.min_val = min_val
        self.max_val = max_val

    def get_raw(self) -> Union[float | int | None]:
        return self.value

    def set_raw(self, val: Union[float | int | None]) -> None:
        if isinstance(val, float | int):
            if val < self.min_val:
                print(f"Setting {self.name} - {val} is lower than minimum value ({self.min_val}) => setting to minimum value ({self.min_val}) instead.")
                self.value = self.min_val
            elif val > self.max_val:
                print(f"Setting {self.name} - {val} exceeds maximum value ({self.max_val}) => setting to maximum value ({self.max_val}) instead.")
                self.value = self.max_val
            else:
                self.value = val
        else:
            self.value = None
            
        return None

class BoundedValueOrStringParameter(Parameter):
    """
    Same behaviour as BoundedValueParameter but with a 'MultiTypeOr()' validator such that some valid
    string is acceptable in addition to numbers.
    """
    def __init__(self, name: str, valid_str: str, value: Union[float | int | str | None] = None,
                 min_val: float | int = -float("inf"), max_val: float | int = float("inf"),
                 unit: str | None = None, integer: bool = False, **kwargs: Any):
        super().__init__(
            name,
            vals=MultiTypeOr(Ints() if integer else Numbers(), Enum(f"{valid_str}")),
            unit=unit,
            label=name,
            **kwargs
        )
        self.value = value
        self.min_val = min_val
        self.max_val = max_val
        self.valid_str = valid_str

    def get_raw(self) -> Union[float | int | str | None]:
        return self.value

    def set_raw(self, val: Union[float | int | str | None]) -> None:
        if isinstance(val, str):
            self.value = val
        elif isinstance(val, (float, int)):
            if val < self.min_val:
                print(f"Setting {self.name} - {val} is lower than minimum value ({self.min_val}) => setting to minimum value ({self.min_val}) instead.")
                self.value = self.min_val
            elif val > self.max_val:
                print(f"Setting {self.name} - {val} exceeds maximum value ({self.max_val}) => setting to maximum value ({self.max_val}) instead.")
                self.value = self.max_val
            else:
                self.value = val
        else:
            self.value = None
            
        return None

class named_consts(StrEnum):
    AUTO = auto()
    INF = auto()
    DEF = auto()

class excitation_type(StrEnum):
    VOLT = auto()
    CURR = auto()

class sample_type(StrEnum):
    vdp = "van_der_Pauw"
    hall = "Hall_bar"
    
def _excitation_type_setter(module: InstrumentModule, value: str, contact_check: bool = False) -> None:
    """
    Function to set excitation type to voltage/current and add or remove the
    associated parameters.

    Args:
        module: InstrumentModule i.e. which measurement type
        value: "VOLT" or "CURR"
        contact_check: if contact check is True then the exitation start & end parameters
            will be added instead of the excitation value & range parameters
    """
    value = excitation_type(value)
    if value == module.excitation_type():
        pass
    else:
        format_str = "voltage" if value == "CURR" else "current"
        measure_str = "current" if value == "CURR" else "voltage"
    
        try:
            del module.parameters[f"excitation_{format_str}_start"]
            del module.parameters[f"excitation_{format_str}_end"]
        except Exception as e:
            pass
        try:
            del module.parameters[f"excitation_{format_str}_value"]
            del module.parameters[f"excitation_measure_{format_str}_range"]
        except Exception as e:
            pass
        try:
            del module.parameters[f"excitation_{format_str}_range"]
            del module.parameters[f"measure_{measure_str}_range"]
            del module.parameters[f"compliance_{measure_str}"]
        except Exception as e:
            pass

        if value == "CURR":
            _add_current_excitation_params(module, contact_check)
        elif value == "VOLT":
            _add_voltage_excitation_params(module, contact_check)
    
        if contact_check:
            module.excitation_start_stop_parameters = [module.parameters["excitation_type"],  # type: ignore[attr-defined]
                                module.parameters[f"excitation_{measure_str}_start"],
                                module.parameters[f"excitation_{measure_str}_end"],
                                module.parameters[f"excitation_{measure_str}_range"],
                                module.parameters[f"measure_{format_str}_range"],
                                module.parameters[f"compliance_{format_str}"]]
    
        else:
            module.excitation_value_range_parameters = [module.parameters["excitation_type"],  # type: ignore[attr-defined]
                        module.parameters[f"excitation_{measure_str}_value"],
                        module.parameters[f"excitation_{measure_str}_range"],
                        module.parameters[f"excitation_measure_{measure_str}_range"],
                        module.parameters[f"measure_{format_str}_range"],
                        module.parameters[f"compliance_{format_str}"]]

def _min_snr_setter(module: InstrumentModule, value: str | float | int) -> None:
    """
    Setter for minimum snr parameter. Changes min value of maximum samples.

    Args:
        module: InstrumentModule i.e. which measurement type
        value: the value to set
    """
    if value == "INF":
        module.maximum_samples.min_val = 1
    else:
        module.maximum_samples.min_val = 10

def _add_current_excitation_params(module: InstrumentModule, contact_check: bool) -> None:
    """
    Function adds the current excitation parameters to an InstrumentModule.

    Args:
        module: InstrumentModule i.e. which measurement type
        contact_check: if True then the excitation start & end parameters
            will be added instead of the value & range ones
    """
    if contact_check:
        module.add_parameter(name="excitation_current_start", parameter_class=BoundedValueParameter, min_val=-0.1, max_val=0.1, unit="A")
        module.add_parameter(name="excitation_current_end", parameter_class=BoundedValueParameter, min_val=-0.1, max_val=0.1, unit="A")
    else:
        module.add_parameter(name="excitation_current_value", parameter_class=BoundedValueParameter, min_val=-0.1, max_val=0.1, unit="A")
        module.add_parameter(name="excitation_measure_current_range", parameter_class=BoundedValueOrStringParameter,
                       valid_str=named_consts.AUTO, value=named_consts.AUTO, min_val=0, max_val=0.1, unit="A")
    module.add_parameter(name="excitation_current_range", parameter_class=BoundedValueOrStringParameter,
                       valid_str=named_consts.AUTO, value=named_consts.AUTO, min_val=0, max_val=0.1, unit="A")
    module.add_parameter(name="measure_voltage_range", parameter_class=BoundedValueOrStringParameter,
                       valid_str=named_consts.AUTO, value=named_consts.AUTO, min_val=0, max_val=10, unit="V")
    module.add_parameter(name="compliance_voltage", parameter_class=BoundedValueParameter, min_val=1, max_val=10, value=10, unit="V")

def _add_voltage_excitation_params(module: InstrumentModule, contact_check: bool) -> None:
    """
    Function adds the voltage excitation parameters to an InstrumentModule.

    Args:
        module: InstrumentModule i.e. which measurement type
        contact_check: if True then the excitation start & end parameters
            will be added instead of the value & range ones
    """
    if contact_check:
        module.add_parameter(name="excitation_voltage_start", parameter_class=BoundedValueParameter, min_val=-10, max_val=10, unit="V")
        module.add_parameter(name="excitation_voltage_end", parameter_class=BoundedValueParameter, min_val=-10, max_val=10, unit="V")
    else:
        module.add_parameter(name="excitation_voltage_value", parameter_class=BoundedValueParameter, min_val=-10, max_val=10, unit="V")
        module.add_parameter(name="excitation_measure_voltage_range", parameter_class=BoundedValueOrStringParameter,
                       valid_str=named_consts.AUTO, value=named_consts.AUTO, min_val=0, max_val=10, unit="V")
    module.add_parameter(name="excitation_voltage_range", parameter_class=BoundedValueOrStringParameter,
                       valid_str=named_consts.AUTO, value=named_consts.AUTO, min_val=0, max_val=10, unit="V")
    module.add_parameter(name="measure_current_range", parameter_class=BoundedValueOrStringParameter,
                       valid_str=named_consts.AUTO, value=named_consts.AUTO, min_val=0, max_val=100E-3, unit="A")
    module.add_parameter(name="compliance_current", parameter_class=BoundedValueParameter, min_val=100E-9, max_val=100E-3, value=100E-3, unit="A")

def excitation_start_stop_command(module: InstrumentModule) -> str:
    """
    Returns excitation start stop command string for an InstrumentModule.
    """
    cmd = ", ".join([f'{x()}' for x in module.excitation_start_stop_parameters])
    return cmd
    
def excitation_value_range_command(module: InstrumentModule) -> str:
    """
    Returns excitation value range command string for an InstrumentModule.
    """
    cmd = ", ".join([f'{x()}' for x in module.excitation_value_range_parameters])
    return cmd

class ContactCheck(MeasureModule):
    """
    ContactCheck MeasureModule.
    """
    def __init__(self, parent: M91_FastHall, name: str, cmd_name: str, **kwargs: Any) -> None:
        super().__init__(parent, name, cmd_name, **kwargs)

        self.add_parameter(name="sampling_time", parameter_class=BoundedValueOrStringParameter, value=named_consts.DEF,
                            valid_str=named_consts.DEF, min_val=0.01E-3, max_val=1, unit="s",
                            docstring="the sampling time which measurements will be averaged over to get one sample")
        self.add_parameter(name="minimum_r_squared", parameter_class=BoundedValueParameter, value=0.999, min_val=0, max_val=1)
        self.add_parameter(name="number_of_points", parameter_class=BoundedValueParameter, min_val=2, max_val=100, value=11, integer=True,
                          docstring="number of points to measure between the excitation start and end")

    def optimise_setter(self, value: bool) -> None:
        """
        Setter for the auto_optimise parameter. Adds/removes
        associated parameters.
        """
        if value:
            try:
                del self.parameters["blanking_time"]
                if self.excitation_type() == "CURR":
                    del self.parameters[f"excitation_current_start"]
                    del self.parameters[f"excitation_current_end"]
                    del self.parameters[f"excitation_current_range"]
                    del self.parameters[f"measure_voltage_range"]
                    del self.parameters[f"compliance_voltage"]
                else:
                    del self.parameters[f"excitation_voltage_start"]
                    del self.parameters[f"excitation_voltage_end"]
                    del self.parameters[f"excitation_voltage_range"]
                    del self.parameters[f"measure_current_range"]
                    del self.parameters[f"compliance_current"]
                del self.parameters["excitation_type"]
            except Exception as e:
                pass
            if "maximum_current" and "maximum_voltage" not in self.parameters.keys():
                self.add_parameter(name="maximum_current", parameter_class=BoundedValueParameter, value=0.1, min_val=-0.1, max_val=0.1, unit="A",
                                  docstring="optimised algorithm will not exceed this output current value")
                self.add_parameter(name="maximum_voltage", parameter_class=BoundedValueParameter, value=10, min_val=-10, max_val=10, unit="V",
                                  docstring="optimised algorithm will not exceed this output voltage value")
        else:
            if "maximum_current" and "maximum_voltage" in self.parameters.keys():
                del self.parameters["maximum_current"]
                del self.parameters["maximum_voltage"]
            try:
                self.add_parameter(name="blanking_time", parameter_class=BoundedValueParameter, value=0.002, min_val=0.5E-3, max_val=300, unit="s",
                                  docstring="the time to wait for the hardware to settle before gathering readings")
                self.add_parameter(name="excitation_type",
                   set_cmd=lambda value: _excitation_type_setter(self, value, contact_check=True),
                   label="excitation_type",
                   vals=Enum("CURR", "VOLT"), # only current excitation available if not the high resistance option
                   initial_value="CURR")
            except Exception as e:
                pass
                
    def start(self) -> None:
        """
        Performs either a), b) or c) depending on sample type (and whether auto optimise
        is enabled for a van der Pauw measurement).
        
        a) Performs a contact check measurement on contact pairs 1-2,
        2-3, 3-4, 4-1 for a van der Pauw sample.

        b) Automatically determines excitation value and ranges. Then runs 
        contact check on all 4 pairs for a van der Pauw sample.

        c) Performs a contact check measurement on contact pairs 5-6,
        5-1, 5-2, 5-3, 5-4 and 6-1 for a Hall bar sample.
        """
        try:
            self.validate_status()
        except Exception as e:
            print(f"Invalid parameter setting: {e}")
            return None
        else:
            opt = True if "auto_optimise" in self.parameters.keys() and self.auto_optimise() else False
            print(opt)
            if opt:
                command_string = (f"CCHECK:VDP:STAR:OPT {self.maximum_current()}," +
                                f"{self.maximum_voltage()}," + f"{self.number_of_points()}," +
                                f"{self.minimum_r_squared()}," + f"{self.sampling_time()}")
            else:
                if self.parent.sample_type() == "Hall_bar":
                    command_string = f"CCH:HBAR:STAR {excitation_start_stop_command(self)}"
                elif self.parent.sample_type() == "van_der_Pauw":
                    command_string = f"CCHECK:START:MANUAL {excitation_start_stop_command(self)}"
                command_string = (f"{command_string}, {self.number_of_points()}," + f"{self.minimum_r_squared()}," +
                                f"{self.blanking_time()}," + f"{self.sampling_time()}")
    
            self.parent.write(command_string)

            err = False
            time.sleep(0.5)
            if not self.get_running_status():
                err = True
                print('ERROR: Contact check unsuccessful. Check configured settings or `read_error_queue`.')
                return None
            else:
                print("Contact Check in progress ... ", end="")

            while self.get_running_status():
                pass

           print("Contact Check complete.")
            time.sleep(1) # short delay to ensure results are available to be retrieved

            
            count = 0
            while True:
                try:
                    results = self.get_all_results()
                except:
                    time.sleep(1)
                    print("Retrying to get data")
                    count += 1
                    if count == 60:
                        print('Failed to get data')
                        results = None
                        break
                else:
                    break
            
            if results is None:
                print("No results available.")
                return None
                
            show_contact_check_results(results.ContactPairIVResults)
            fig, axs = plt.subplots(1, 6 if self.parent.sample_type() == "Hall_bar" else 4, figsize=(17,4), sharex=True, sharey=True)
            plot_check(results, axs)
            apply_plot_style(fig, axs, "DARK")
        
            return None
                
class FastHall(MeasureModule):
    """
    FastHall MeasureModule.
    """
    def __init__(self, parent: M91_FastHall, name: str, cmd_name: str, **kwargs: Any) -> None:
        super().__init__(parent, name, cmd_name, **kwargs)

        self.tm = "ᵀᴹ"
        
        self.add_parameter(name="auto_optimise", set_cmd=lambda value: self.optimise_setter(value), label="auto_optimise", vals=Bool(), initial_value=True,
                          docstring="if True then the last run contact check and resistivity measurement's parameters will be used")
        self.add_parameter(name="user_defined_field", parameter_class=BoundedValueParameter, value=0, unit="T",
                          docstring="field that the sample is being subjected to")
        self.add_parameter(name="maximum_samples", parameter_class=BoundedValueParameter, value=100, min_val=1, max_val=1000, integer=True,
                          docstring="when minimum snr is INF, the total number of sample to average 1-1000; when minimum snr is specified, the max number of samples to average 10-1000")
        self.add_parameter(name="sample_thickness", parameter_class=BoundedValueOrStringParameter,
                           valid_str=named_consts.DEF, value=named_consts.DEF, min_val=0, max_val=10E-3, unit="m",
                          docstring="thickness of the sample, (DEF = 0)")
        self.add_parameter(name="averaging_samples", parameter_class=BoundedValueOrStringParameter,
                           valid_str=named_consts.DEF, value=named_consts.DEF, min_val=1, max_val=120, integer=True,
                          docstring="number of voltage compensation samples to average, only applied for excitation type voltage (DEF = 60)")
        self.add_parameter(name="minimum_SNR", label="mininum_SNR", set_cmd= lambda value: _min_snr_setter(self, value),
                            initial_value=30, vals=MultiTypeOr(Numbers(1.1,1000), Enum(f"{named_consts.INF}")),
                          docstring="desired signal-to-noise ratio of the measurement calculated using average Hall voltage/error")
    
    def optimise_setter(self, value: bool) -> None:
        """
        Setter for the auto_optimise parameter. Adds/removes 
        associated parameters.
        """
        if value:
            try:
                del self.parameters["blanking_time"]
                del self.parameters["sampling_time"]
                del self.parameters["resistivity"]
                if self.excitation_type() == "CURR":
                    del self.parameters[f"excitation_current_value"]
                    del self.parameters[f"excitation_current_range"]
                    del self.parameters[f"measure_voltage_range"]
                    del self.parameters[f"compliance_voltage"]
                    del self.parameters[f"excitation_measure_current_range"]
                else:
                    del self.parameters[f"excitation_voltage_value"]
                    del self.parameters[f"excitation_voltage_range"]
                    del self.parameters[f"measure_current_range"]
                    del self.parameters[f"compliance_current"]
                    del self.parameters[f"excitation_measure_voltage_range"]
                del self.parameters["excitation_type"]
            except Exception as e:
                pass
            if "measure_range" not in self.parameters.keys():
                self.add_parameter(name="measure_range", parameter_class=BoundedValueOrStringParameter,
                                   valid_str=named_consts.AUTO, value=named_consts.AUTO, min_val=0, max_val=10, unit="A or V",
                                  docstring="depending on exictation type, the voltage measurement range (0-10 V) or the current measurement range (0-0.1 A)")
        else:
            if "measure_range" in self.parameters.keys():
                del self.parameters["measure_range"]
            try:
                self.add_parameter(name="blanking_time", parameter_class=BoundedValueParameter, value=0.002, min_val=0.5E-3, max_val=300, unit="s",
                                  docstring="time to wait for hardware to settle before gathering readings")
                self.add_parameter(name="sampling_time", parameter_class=BoundedValueOrStringParameter, value=named_consts.DEF,
                                   valid_str=named_consts.DEF, min_val=0.01E-3, max_val=1, unit="s", 
                                  docstring="the sampling time which measurements will be averaged over to get one sample")
                self.add_parameter(name="resistivity", parameter_class=BoundedValueOrStringParameter,
                           valid_str=named_consts.DEF, value=named_consts.DEF, min_val=0,
                           unit=f"{unicodedata.lookup('greek capital letter omega')}.m or {unicodedata.lookup('greek capital letter omega')}/{unicodedata.lookup('White square')}",
                                  docstring="resistivity of the sample in ohm*metres (bulk) or ohms per square (sheet) - defaults to not a number (NaN) which will propagate through calculated values")
                self.add_parameter(name="excitation_type",
                   set_cmd=lambda value: _excitation_type_setter(self, value),
                   label="excitation_type",
                   vals=Enum("CURR", "VOLT"), # only current excitation available if not the high resistance option
                   initial_value="CURR")
            except Exception as e:
                pass
        
    def start(self, show_results: bool = True, print_status: bool = True) -> Optional[SimpleNamespace]:
        """
        Performs either a) or b) depending on whether auto optimise is enabled or not.
        
        a) Performs a FastHallTM measurement for a van der Pauw sample.

        b) Performs a FastHallTM measurement, for a van der Pauw sample, that uses the last 
        run contact check measurements' excitation type, compliance limit, blanking time,
        excitation range, and the largest absolute value of start and end excitation
        values along with the last run resistivity measurement's resistivity average and 
        sample thickness.

        Args:
            show_results, bool: if True results will be printed
            print_status, bool: if True progress of measurement statements will be printed.
        """
        try:
            self.validate_status()
        except Exception as e:
            print(f"Invalid parameter setting: {e}")
            return None
        else:
            if self.auto_optimise():
                command_string = (f"FASTHALL:VDP:START:LINK {self.user_defined_field()}," +
                                f"{self.measure_range()}," + f"{self.maximum_samples()}," +
                                f"{self.minimum_SNR()}," + f"{self.averaging_samples()}," + f"{self.sample_thickness()}")
            else:
                command_string = (f"FASTHALL:START {excitation_value_range_command(self)}," +
                                f"{self.user_defined_field()}," + f"{self.maximum_samples()}," +
                                f"{self.resistivity()}," + f"{self.blanking_time()}," +
                                f"{self.averaging_samples()}," + f"{self.sample_thickness()}," +
                                f"{self.minimum_SNR()}," + f"{self.sampling_time()}")
    
            self.parent.write(command_string)
            
            err = False
            time.sleep(0.5)
            if not self.get_running_status():
                err = True
                print('ERROR: Measurement unsuccessful. Check configured settings or `read_error_queue`.')
                return None
            if print_status == True:
                print(f"FastHall{self.tm} in progress ... ", end="")
                
            while self.get_running_status():
                pass

            if print_status == True:
                print(f"FastHall{self.tm} complete")

            count = 0
            while True:
                try:
                    results = self.get_results()
                except:
                    time.sleep(1)
                    print("Retrying to get data")
                    count += 1
                    if count == 60:
                        print('Failed to get data')
                        results = None
                        break
                else:
                    break
            
            if results is None:
                print("No results available.")
                return None
    
            if show_results:
                self.parent.display_measurement_results(results) 
            return results

class DCHall(MeasureModule):
    """
    DCHall MeasureModule.
    """
    def __init__(self, parent: M91_FastHall, name: str, cmd_name: str, **kwargs: Any) -> None:
        super().__init__(parent, name, cmd_name, **kwargs)
    
        self.add_parameter(name="excitation_type",
                           set_cmd=lambda value: _excitation_type_setter(self, value),
                           label="excitation_type",
                           vals=Enum("CURR", "VOLT"), # only current excitation available if not the high resistance option
                           initial_value="CURR")

        self.add_parameter(name="blanking_time", parameter_class=BoundedValueParameter, value=0.002, min_val=0.5E-3, max_val=300, unit="s",
                          docstring="time to wait for the hardware to settle before gathering readings")
        self.add_parameter(name="sampling_time", parameter_class=BoundedValueOrStringParameter, value=named_consts.DEF,
                            valid_str=named_consts.DEF, min_val=0.01E-3, max_val=1, unit="s", 
                            docstring="the sampling time which measurements will be averaged over to get one sample")
        self.add_parameter(name="field_reversal", parameter_class=BoundedValueParameter, value=1, min_val=0, max_val=1, integer=True, val_mapping={"ON": 1, "OFF": 0},
                          docstring="specifies whether or not to apply field reversal")
        self.add_parameter(name="user_defined_field", parameter_class=BoundedValueParameter, value=0, unit="T",
                          docstring="the field the sample is being subjected to")
        self.add_parameter(name="resistivity", parameter_class=BoundedValueOrStringParameter,
                           valid_str=named_consts.DEF, value=named_consts.DEF, min_val=0,
                           unit=f"{unicodedata.lookup('greek capital letter omega')}.m or {unicodedata.lookup('greek capital letter omega')}/{unicodedata.lookup('White square')}",
                          docstring="resistivity of the sample in ohm*metres (bulk) or ohms per square (sheet) - defaults to not a number (NaN) which will propagate through calculated values")
        self.add_parameter(name="maximum_samples", parameter_class=BoundedValueParameter, value=100, min_val=1, max_val=1000, integer=True,
                          docstring="when minimum snr is INF, the total number of samples to average (1-1000); when minimum snr is specified, the maximum number of samples to average (10-1000)")
        self.add_parameter(name="minimum_SNR", label="mininum_SNR", set_cmd= lambda value: _min_snr_setter(self, value),
                            initial_value=30, vals=MultiTypeOr(Numbers(1.1,1000), Enum(f"{named_consts.INF}")),
                          docstring="the desired signal-to-noise ratio of the measured resistance, calaculated using measurement average voltage/error of mean")
        self.add_parameter(name="sample_thickness", parameter_class=BoundedValueOrStringParameter,
                           valid_str=named_consts.DEF, value=named_consts.DEF, min_val=0, max_val=10E-3, unit="m")

    def get_waiting_status(self) -> bool:
        return bool(int(self.parent.ask("HALL:WAITing?")))

    def start(self, show_results: bool = True, print_status: bool = True) -> Optional[SimpleNamespace]:
        """
        Performs a DC Hall measurement for a Hall bar sample or a van
        der Pauw sample.

        Args:
            show_results, bool: if True results will be printed
            print_status, bool: if True progress of measurement statements will be printed.
        """
        try:
            self.validate_status()
        except Exception as e:
            print(f"Invalid parameter setting: {e}")
            return None
        else:
            if self.parent.sample_type() == "Hall_bar":
                command_string = f"HALL:HBAR:DC:STAR {excitation_value_range_command(self)}"
            elif self.parent.sample_type() == "van_der_Pauw":
                command_string = f"HALL:DC:START {excitation_value_range_command(self)}"
            command_string = (f"{command_string}, {self.maximum_samples()}," +
                            f"{self.user_defined_field()}," + f"{self.field_reversal()}," +
                            f"{self.resistivity()}," + f"{self.blanking_time()}," + f"{self.sample_thickness()},"
                            f"{self.minimum_SNR()}," + f"{self.sampling_time()}")
    
            self.parent.write(command_string)

            if self.get_waiting_status():
                print("ERROR: DC Hall measurement is in the waiting state. Reset before running new measurement.")
                
            err = False
            time.sleep(0.5)
            if not self.get_running_status():
                err = True
                print('ERROR: Measurement unsuccessful. Check configured settings or `read_error_queue`.')
                return None
            if print_status == True:
                print("DC Hall measurement in progress ... ", end="")
            
            while self.get_running_status():
                pass
                
            time.sleep(0.5)
            if print_status == True:
                print("DC Hall measurement complete.")
            if self.get_waiting_status():
                print("DC Hall measurement is in the waiting state. Reverse the field and then `continue_dc_hall`.")

            count = 0
            while True:
                try:
                    results = self.get_results()
                except:
                    time.sleep(1)
                    print("Retrying to get data")
                    count += 1
                    if count == 60:
                        print('Failed to get data')
                        results = None
                        break
                else:
                    break
            
            if results is None:
                print("No results available.")
                return None

            if show_results:
                self.parent.display_measurement_results(results)
            return results
                                        
    def continue_dc_hall(self, show_results: bool = True, print_status: bool = True) -> Optional[SimpleNamespace]:
        """
        Continues the DC Hall measurement if it is in a waiting state. To be used
        after the field has been reversed.

        Args:
            show_results, bool: if True results will be printed
            print_status, bool: if True progress of measurement statements will be printed.
        """
        
        if not self.get_waiting_status():
            print("ERROR: DC Hall measurement is not in a waiting state.")
            return None
            
        command_string = f"HALL:DC:CONTINUE"

        self.parent.write(command_string)
        
        err = False
        time.sleep(0.5)
        if not self.get_running_status():
            err = True
            print('ERROR: Measurement unsuccessful.')
            return None
        if print_status == True:
            print("DC Hall measurement in progress ... ", end="")
            
        while self.get_running_status():
            pass

        if print_status == True:
            print("DC Hall measurement complete.")

        count = 0
        while True:
            try:
                results = self.get_results()
            except:
                time.sleep(1)
                print("Retrying to get data")
                count += 1
                if count == 60:
                    print('Failed to get data')
                    results = None
                    break
            else:
                break

        if results is None:
                print("No results available.")
                return None

        if show_results:
            self.parent.display_measurement_results(results)
        return results
       
class FourWire(MeasureModule):
    """
    FourWire MeasureModule.
    """
    def __init__(self, parent: M91_FastHall, name: str, cmd_name: str, **kwargs: Any) -> None:
        super().__init__(parent, name, cmd_name, **kwargs)
    
        self.add_parameter(name="excitation_type",
                           set_cmd=lambda value: _excitation_type_setter(self, value),
                           label="excitation_type",
                           vals=Enum("CURR", "VOLT"), # only current excitation available if not the high resistance option
                           initial_value="CURR")
        self.add_parameter(name="excitation_plus_channel", parameter_class=BoundedValueParameter, min_val=1, max_val=6, integer=True,
                          docstring="exicitation plus channel, cannot be the same as excitation minus channel")
        self.add_parameter(name="excitation_minus_channel", parameter_class=BoundedValueParameter, min_val=1, max_val=6, integer=True,
                          docstring="excitation minus channel, cannot be the same as exictation plus channel")
        self.add_parameter(name="measure_plus_channel", parameter_class=BoundedValueParameter, min_val=1, max_val=6, integer=True,
                          docstring="measure plus channel, cannot be the same as measure minus channel")
        self.add_parameter(name="measure_minus_channel", parameter_class=BoundedValueParameter, min_val=1, max_val=6, integer=True,
                          docstring="measure minus channel, cannot be the same as measure plus channel")
        self.add_parameter(name="excitation_reversal", parameter_class=BoundedValueParameter, value=0, min_val=0, max_val=1, val_mapping={"ON": 1, "OFF": 0},
                          docstring="ON to reverse the excitation")
        self.add_parameter(name="blanking_time", parameter_class=BoundedValueParameter, value=0.002, min_val=0.5E-3, max_val=300, unit="s",
                          docstring="time to wait for the hardware to settle before gathering readings")
        self.add_parameter(name="sampling_time", parameter_class=BoundedValueOrStringParameter, value=named_consts.DEF,
                            valid_str=named_consts.DEF, min_val=0.01E-3, max_val=1, unit="s", 
                            docstring="the sampling time which measurements will be averaged over to get one sample")
        self.add_parameter(name="maximum_samples", parameter_class=BoundedValueParameter, value=100, min_val=1, max_val=1000, integer=True,
                          docstring="when minimum SNR is INF, the total number of samples to average 1-1000; when minimum SNR is specified, the maximum number of samples to average 10-1000")
        self.add_parameter(name="minimum_SNR", label="mininum_SNR", set_cmd= lambda value: _min_snr_setter(self, value),
                            initial_value=30, vals=MultiTypeOr(Numbers(1.1,1000), Enum(f"{named_consts.INF}")),
                          docstring="desired signal-to-noise ratio of the measured resistance, calculated using measurement average/error")

    def start(self, show_results: bool = True, print_status: bool = True) -> Optional[SimpleNamespace]:
        """
        Performs a four wire measurement. Excitation is sourced from contact point 1
        to contact point 2. Voltage is measured/senses between contact point 3 and 
        contact point 4.

        Args:
            show_results, bool: if True results will be printed
            print_status, bool: if True progress of measurement statements will be printed.
        """
        try:
            self.validate_status()
        except Exception as e:
            print(f"Invalid parameter setting: {e}")
            return None
        else:
            command_string = (f"FWIRe:STARt {self.excitation_plus_channel()}," +
                            f"{self.excitation_minus_channel()}," + f"{self.measure_plus_channel()}," +
                            f"{self.measure_minus_channel()}," + f"{excitation_value_range_command(self)}," +
                            f"{self.blanking_time()}," + f"{self.maximum_samples()}," + f"{self.minimum_SNR()}," +
                            f"{self.excitation_reversal()}," + f"{self.sampling_time()}")
    
            self.parent.write(command_string)

            err = False
            time.sleep(0.5)
            if not self.get_running_status():
                err = True
                print('ERROR: Measurement unsuccessful. Check configured settings or `read_error_queue`.')
                return None
            if print_status == True:
                print("Four Wire measurement in progress ... ", end="")
                
            while self.get_running_status():
                pass

            if print_status == True:
                print("Four Wire measurement complete.")

            count = 0
            while True:
                try:
                    results = self.get_results()
                except:
                    time.sleep(1)
                    print("Retrying to get data")
                    count += 1
                    if count == 60:
                        print('Failed to get data')
                        results = None
                        break
                else:
                    break

            if results is None:
                    print("No results available.")
                    return None
                    
            if show_results:
                self.parent.display_measurement_results(results)
            return results
    
class Resistivity(MeasureModule):
    """
    Resistivity MeasureModule.
    """
    def __init__(self, parent: M91_FastHall, name: str, cmd_name: str, **kwargs: Any) -> None:
        super().__init__(parent, name, cmd_name, **kwargs)

        self.add_parameter(name="maximum_samples", parameter_class=BoundedValueParameter, value=100, min_val=1, max_val=1000, integer=True,
                          docstring="when minimum snr is INF, the total number of samples to average (1-1000); when minimum SNR is specified, the maximum number of samples to average (10-1000)")
        self.add_parameter(name="minimum_SNR", label="mininum_SNR", set_cmd= lambda value: _min_snr_setter(self, value),
                            initial_value=30, vals=MultiTypeOr(Numbers(1.1,1000), Enum(f"{named_consts.INF}")),
                          docstring="the desired signal to noise ratio of the measurement calculated using average resistivity / error of mean")
        self.add_parameter(name="sample_thickness", parameter_class=BoundedValueOrStringParameter,
                           valid_str=named_consts.DEF, value=named_consts.DEF, min_val=0, max_val=10E-3, unit="m")
        
    def optimise_setter(self, value: bool) -> None:
        """
        Setter for the auto_optimise parameter. Adds/removes 
        associated parameters.
        """
        if value:
            try:
                del self.parameters["blanking_time"]
                del self.parameters["sampling_time"]
                if self.excitation_type() == "CURR":
                    del self.parameters[f"excitation_current_value"]
                    del self.parameters[f"excitation_current_range"]
                    del self.parameters[f"measure_voltage_range"]
                    del self.parameters[f"compliance_voltage"]
                    del self.parameters[f"excitation_measure_current_range"]
                else:
                    del self.parameters[f"excitation_voltage_value"]
                    del self.parameters[f"excitation_voltage_range"]
                    del self.parameters[f"measure_current_range"]
                    del self.parameters[f"compliance_current"]
                    del self.parameters[f"excitation_measure_voltage_range"]
                del self.parameters["excitation_type"]
            except Exception as e:
                pass
            if "measure_range" not in self.parameters.keys():
                self.add_parameter(name="measure_range", parameter_class=BoundedValueOrStringParameter,
                               valid_str=named_consts.AUTO, value=named_consts.AUTO, min_val=0, max_val=10, unit="A or V",
                                docstring="depending on exictation type, the voltage measurement range (0-10 V) or the current measurement range (0-0.1 A)")
        else:
            if "measure_range" in self.parameters.keys():
                del self.parameters["measure_range"]
            try:
                self.add_parameter(name="blanking_time", parameter_class=BoundedValueParameter, value=0.002, min_val=0.5E-3, max_val=300, unit="s",
                                  docstring="time to wait for hardware to settle before gathering readings")
                self.add_parameter(name="sampling_time", parameter_class=BoundedValueOrStringParameter, value=named_consts.DEF,
                                   valid_str=named_consts.DEF, min_val=0.01E-3, max_val=1, unit="s", 
                                  docstring="the sampling time which measurements will be averaged over to get one sample")
                self.add_parameter(name="excitation_type",
                   set_cmd=lambda value: _excitation_type_setter(self, value),
                   label="excitation_type",
                   vals=Enum("CURR", "VOLT"), # only current excitation available if not the high resistance option
                   initial_value="CURR")
            except Exception as e:
                pass

    def start(self, show_results: bool = True, print_status: bool = True) -> Optional[SimpleNamespace]:
        """
        Performs either a), b) or c) depending on sample type (and whether auto optimise
        is enabled for a van der Pauw measurement).
        
        a) Performs a resistivity measurement for a van der Pauw sample.

        b) Performs a resistivity measurement, for a van der Pauw sample, that uses 
        the last run contact check measurement's excitation type, compliance limit,
        blanking time, excitation range, and the largest absolute value of start 
        and end excitation values.

        c) Performs a resistivity measurement for on a Hall bar sample.

        Args:
            show_results, bool: if True results will be printed
            print_status, bool: if True progress of measurement statements will be printed.
        """
        try:
            self.validate_status()
        except Exception as e:
            print(f"Invalid parameter setting: {e}")
            return None
        else:
            opt = True if "auto_optimise" in self.parameters.keys() and self.auto_optimise() else False
            if opt:
                command_string = (f"RESISTIVITY:START:LINK {self.measure_range()}," + f"{self.sample_thickness()}," +
                                  f"{self.minimum_SNR()}," + f"{self.maximum_samples()}")
            else:
                if self.parent.sample_type() == "Hall_bar":
                    command_string = (f"RESISTIVITY:HBAR:START {excitation_value_range_command(self)}," +
                                         f"{self.width()}," + f"{self.separation()},")
                else:
                    command_string = f"RESISTIVITY:START {excitation_value_range_command(self)},"
                command_string = (f"{command_string} {self.maximum_samples()}," +
                                 f"{self.blanking_time()}," + f"{self.sample_thickness()}," +
                                 f"{self.minimum_SNR()}," + f"{self.sampling_time()}")
                
            self.parent.write(command_string)
            
            err = False
            time.sleep(0.5)
            if not self.get_running_status():
                err = True
                print('ERROR: Measurement unsuccessful. Check configured settings or `read_error_queue`.')
                return None
            if print_status == True:
                print("Resistivity measurement in progress ... ", end="")

            while self.get_running_status():
                pass

            if print_status == True:
                print("Resistivity measurement complete.")

            count = 0
            while True:
                try:
                    results = self.get_results()
                except:
                    time.sleep(1)
                    print("Retrying to get data")
                    count += 1
                    if count == 60:
                        print('Failed to get data')
                        results = None
                        break
                else:
                    break

            if results is None:
                    print("No results available.")
                    return None
                    
            if show_results:
                self.parent.display_measurement_results(results)
            return results