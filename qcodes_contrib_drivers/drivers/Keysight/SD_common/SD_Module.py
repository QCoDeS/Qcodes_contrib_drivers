import warnings
import os
from typing import List, Union, Callable, Any
from qcodes.instrument.base import Instrument

try:
    import keysightSD1
except ImportError:
    raise ImportError('to use the Keysight SD drivers install the keysightSD1 module '
                      '(http://www.keysight.com/main/software.jspx?ckey=2784055)')

# check whether SD1 version 2.x or 3.x
is_sd1_3x = 'SD_SandBoxRegister' in dir(keysightSD1)


def result_parser(value: Any, name: str = 'result',
                  verbose: bool = False) -> Any:
    """
    This method is used for parsing the result in the get-methods.
    For values that are non-negative, the value is simply returned.
    Negative values indicate an error, so an error is raised
    with a reference to the error code.

    The parser also can print to the result to the shell if verbose is 1.

    Args:
        value: the value to be parsed
        name: name of the value to be parsed
        verbose: boolean indicating verbose mode

    Returns:
        parsed value, which is the same as value if non-negative or not a number
    """
    if isinstance(value, int) and (int(value) < 0):
        error_message = keysightSD1.SD_Error.getErrorMessage(value)
        call_message = f' ({name})' if name != 'result' else ''
        raise Exception(f'Error in call to module ({value}): '
                        f'{error_message}{call_message}')
    else:
        if verbose:
            print(f'{name}: {value}')
        return value


class SD_Module(Instrument):
    """
    This is the general SD_Module driver class that implements shared
    parameters and functionality among all PXIe-based digitizer/awg/combo
    cards by Keysight.

    This driver was written to be inherited from by either the SD_AWG,
    SD_DIG or SD_Combo class, depending on the functionality of the card.

    Specifically, this driver was written with the M3201A and M3300A cards in
    mind.

    This driver makes use of the Python library provided by Keysight as part
    of the SD1 Software package (v.2.01.00).

    Args:
        name: an identifier for this instrument, particularly for
            attaching it to a Station.
        chassis: identification of the chassis.
        slot: slot of the module in the chassis.
    """

    def __init__(self, name: str, chassis: int, slot: int,
                 module_class: Callable = keysightSD1.SD_Module,
                 **kwargs) -> None:
        super().__init__(name, **kwargs)

        # Create instance of keysight module class
        self.SD_module = module_class()

        # Open the device, using the specified chassis and slot number
        self.module_name = self.SD_module.getProductNameBySlot(chassis, slot)
        result_parser(self.module_name,
                      f'getProductNameBySlot({chassis}, {slot})')

        result_code = self.SD_module.openWithSlot(self.module_name, chassis, slot)
        result_parser(result_code,
                      f'openWithSlot({self.module_name}, {chassis}, {slot})')

        self.add_parameter('module_count',
                           label='module count',
                           get_cmd=self.get_module_count,
                           docstring='The number of Keysight modules '
                                     'installed in the system')
        self.add_parameter('product_name',
                           label='product name',
                           get_cmd=self.get_product_name,
                           docstring='The product name of the device')
        self.add_parameter('serial_number',
                           label='serial number',
                           get_cmd=self.get_serial_number,
                           docstring='The serial number of the device')
        self.add_parameter('chassis_number',
                           label='chassis number',
                           get_cmd=self.get_chassis,
                           docstring='The chassis number where the device is '
                                     'located')
        self.add_parameter('slot_number',
                           label='slot number',
                           get_cmd=self.get_slot,
                           docstring='The slot number where the device is '
                                     'located')
        self.add_parameter('status',
                           label='status',
                           get_cmd=self.get_status,
                           docstring='The status of the device')
        self.add_parameter('firmware_version',
                           label='firmware version',
                           get_cmd=self.get_firmware_version,
                           docstring='The firmware version of the device')
        self.add_parameter('hardware_version',
                           label='hardware version',
                           get_cmd=self.get_hardware_version,
                           docstring='The hardware version of the device')
        self.add_parameter('instrument_type',
                           label='type',
                           get_cmd=self.get_type,
                           docstring='The type of the device')
        self.add_parameter('open',
                           label='open',
                           get_cmd=self.get_open,
                           docstring='Indicating if device is open, '
                                     'True (open) or False (closed)')

    #
    # Get-commands
    #

    def get_module_count(self, verbose: bool = False) -> Any:
        """Returns the number of SD modules installed in the system"""
        value = self.SD_module.moduleCount()
        value_name = 'module_count'
        return result_parser(value, value_name, verbose)

    def get_product_name(self, verbose: bool = False) -> Any:
        """Returns the product name of the device"""
        value = self.SD_module.getProductName()
        value_name = 'product_name'
        return result_parser(value, value_name, verbose)

    def get_serial_number(self, verbose: bool = False) -> Any:
        """Returns the serial number of the device"""
        value = self.SD_module.getSerialNumber()
        value_name = 'serial_number'
        return result_parser(value, value_name, verbose)

    def get_chassis(self, verbose: bool = False) -> Any:
        """Returns the chassis number where the device is located"""
        value = self.SD_module.getChassis()
        value_name = 'chassis_number'
        return result_parser(value, value_name, verbose)

    def get_slot(self, verbose: bool = False) -> Any:
        """Returns the slot number where the device is located"""
        value = self.SD_module.getSlot()
        value_name = 'slot_number'
        return result_parser(value, value_name, verbose)

    def get_status(self, verbose: bool = False) -> Any:
        """Returns the status of the device"""
        value = self.SD_module.getStatus()
        value_name = 'status'
        return result_parser(value, value_name, verbose)

    def get_firmware_version(self, verbose: bool = False) -> Any:
        """Returns the firmware version of the device"""
        value = self.SD_module.getFirmwareVersion()
        value_name = 'firmware_version'
        return result_parser(value, value_name, verbose)

    def get_hardware_version(self, verbose: bool = False) -> Any:
        """Returns the hardware version of the device"""
        value = self.SD_module.getHardwareVersion()
        value_name = 'hardware_version'
        return result_parser(value, value_name, verbose)

    def get_type(self, verbose: bool = False) -> Any:
        """Returns the type of the device"""
        value = self.SD_module.getType()
        value_name = 'type'
        return result_parser(value, value_name, verbose)

    def get_open(self, verbose: bool = False) -> Any:
        """Returns whether the device is open (True) or not (False)"""
        value = self.SD_module.isOpen()
        value_name = 'open'
        return result_parser(value, value_name, verbose)

    def get_pxi_trigger(self, pxi_trigger: int, verbose: bool = False) -> int:
        """
        Returns the digital value of the specified PXI trigger

        Args:
            pxi_trigger: PXI trigger number (4000 + Trigger No.)
            verbose: boolean indicating verbose mode

        Returns:
            Digital value with negated logic, 0 (ON) or 1 (OFF), or negative
                numbers for errors
        """
        value = self.SD_module.PXItriggerRead(pxi_trigger)
        value_name = f'pxi_trigger number {pxi_trigger}'
        return result_parser(value, value_name, verbose)

    #
    # Set-commands
    #

    def set_pxi_trigger(self, value: int, pxi_trigger: int,
                        verbose: bool = False) -> Any:
        """
        Sets the digital value of the specified PXI trigger

        Args:
            pxi_trigger: PXI trigger number (4000 + Trigger No.)
            value: Digital value with negated logic, 0 (ON) or 1 (OFF)
            verbose: boolean indicating verbose mode
        """
        result = self.SD_module.PXItriggerWrite(pxi_trigger, value)
        value_name = f'set pxi_trigger {pxi_trigger} to {value}'
        return result_parser(result, value_name, verbose)

    #
    # FPGA related functions
    #

    def get_fpga_pc_port(self, port: int, data_size: int, address: int,
                         address_mode: int, access_mode: int,
                         verbose: bool = False) -> Any:
        """
        Reads data at the PCport FPGA Block

        Args:
            port: PCport number
            data_size: number of 32-bit words to read (maximum is 128 words)
            address: address that wil appear at the PCport interface
            address_mode: auto-increment (0), or fixed (1)
            access_mode: non-dma (0), or dma (1)
            verbose: boolean indicating verbose mode
        """
        data = self.SD_module.FPGAreadPCport(port, data_size, address,
                                          address_mode, access_mode)
        value_name = f'data at PCport {port}'
        return result_parser(data, value_name, verbose)

    def set_fpga_pc_port(self, port: int, data: List[int], address: int,
                         address_mode: int, access_mode: int,
                         verbose: bool = False) -> Any:
        """
        Writes data at the PCport FPGA Block

        Args:
            port: PCport number
            data: array of integers containing the data
            address: address that will appear at the PCport interface
            address_mode: auto-increment (0), or fixed (1)
            access_mode: non-dma (0), or dma (1)
            verbose: boolean indicating verbose mode
        """
        result = self.SD_module.FPGAwritePCport(port, data, address,
                                               address_mode,
                                             access_mode)
        value_name = f'set fpga PCport {port} to data:{data}, ' \
                     f'address:{address}, address_mode:{address_mode}, ' \
                     f'access_mode:{access_mode}'
        return result_parser(result, value_name, verbose)

    def load_fpga_image(self, filename: str) -> Any:
        if not os.path.exists(filename):
            raise Exception(f'FPGA bitstream {filename} not found')
        result = result_parser(self.SD_module.FPGAload(filename),
                               f'loading FPGA bitstream: {filename}')
        if isinstance(result, int) and result < 0:
            raise Exception(f'Failed to load FPGA bitstream')
        return result

    #
    # HVI related functions
    #

    def set_hvi_register(self, register: Union[int, str], value: int,
                         verbose: bool = False) -> Any:
        """
        Sets value of specified HVI register.

        Args:
            register: register to set.
            value: new value.
            verbose: boolean indicating verbose mode
        """
        if type(register) == int:
            result = self.SD_module.writeRegisterByNumber(register, value)
        else:
            result = self.SD_module.writeRegisterByName(register, value)
        value_name = f'set HVI register {register}:{value}'
        result_parser(result, value_name, verbose)

    def get_hvi_register(self, register: Union[int, str],
                         verbose: bool = False) -> int:
        """
        Returns value of specified HVI register.

        Args:
            register: register to read.
            verbose: boolean indicating verbose mode
        Returns:
            register value.
        """
        if type(register) == int:
            error, result = self.SD_module.readRegisterByNumber(register)
        else:
            error, result = self.SD_module.readRegisterByName(register)

        value_name = f'get HVI register {register}'
        result_parser(error, value_name, verbose)
        return result

    #
    # The methods below are not used for setting or getting parameters,
    # but can be used in the test functions of the test suite e.g. The main
    # reason they are defined is to make this driver more complete
    #

    def get_product_name_by_slot(self, chassis: int, slot: int,
                                 verbose: bool = False) -> Any:
        value = self.SD_module.getProductNameBySlot(chassis, slot)
        value_name = 'product_name'
        return result_parser(value, value_name, verbose)

    def get_product_name_by_index(self, index: Any,
                                  verbose: bool = False) -> Any:
        value = self.SD_module.getProductNameByIndex(index)
        value_name = 'product_name'
        return result_parser(value, value_name, verbose)

    def get_serial_number_by_slot(self, chassis: int, slot: int,
                                  verbose: bool = False) -> Any:
        warnings.warn('Returns faulty serial number due to error in Keysight '
                      'lib v.2.01.00', UserWarning)
        value = self.SD_module.getSerialNumberBySlot(chassis, slot)
        value_name = 'serial_number'
        return result_parser(value, value_name, verbose)

    def get_serial_number_by_index(self, index: Any,
                                   verbose: bool = False) -> Any:
        warnings.warn('Returns faulty serial number due to error in Keysight '
                      'lib v.2.01.00', UserWarning)
        value = self.SD_module.getSerialNumberByIndex(index)
        value_name = 'serial_number'
        return result_parser(value, value_name, verbose)

    def get_type_by_slot(self, chassis: int, slot: int,
                         verbose: bool = False) -> Any:
        value = self.SD_module.getTypeBySlot(chassis, slot)
        value_name = 'type'
        return result_parser(value, value_name, verbose)

    def get_type_by_index(self, index: Any, verbose: bool = False) -> Any:
        value = self.SD_module.getTypeByIndex(index)
        value_name = 'type'
        return result_parser(value, value_name, verbose)

    #
    # The methods below are useful for controlling the device, but are not
    # used for setting or getting parameters
    #

    def close(self) -> None:
        """
        Closes the hardware device and frees resources.

        If you want to open the instrument again, you have to initialize a
        new instrument object
        """
        # Note: module keeps track of open/close state. So, keep the reference.
        self.SD_module.close()
        super().close()

    # only closes the hardware device, does not delete the current instrument
    # object
    def close_soft(self) -> None:
        self.SD_module.close()

    def open_with_serial_number(self, name: str, serial_number: int) -> Any:
        result = self.SD_module.openWithSerialNumber(name, serial_number)
        return result_parser(result,
                             f'openWithSerialNumber({name}, {serial_number})')

    def open_with_slot(self, name: str, chassis: int, slot: int) -> Any:
        result = self.SD_module.openWithSlot(name, chassis, slot)
        return result_parser(result, f'openWithSlot({name}, {chassis}, {slot})')

    def run_self_test(self) -> Any:
        value = self.SD_module.runSelfTest()
        print(f'Did self test and got result: {value}')
        return value
