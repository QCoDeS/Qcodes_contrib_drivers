"""Interface to the andor SDK.

TODO: Copy documentation from the SDK help.
"""
import ctypes
import sys
from contextlib import contextmanager
from typing import Any, Literal, Optional, Sequence, Tuple

import numpy as np
from numpy import typing as npt


@contextmanager
def out_argtypes(func):
    argtypes = func.argtypes
    try:
        func.argtypes = None
        yield func
    finally:
        func.argtypes = argtypes


class SDKError(Exception):
    """An error originating in the andor SDK"""


class atmcd64d:
    """
    Wrapper class for the atmcd64.dll Andor library.
    The class has been tested for an Andor iDus DU401 BU2.

    Args:
        dll_path: Path to the atmcd64.dll file. If not set, a default path is used.
        verbose: Flag for the verbose behaviour. If true, successful events are printed.

    Attributes:
        verbose: Flag for the verbose behaviour.
        dll: WinDLL object for atmcd64.dll.

    """

    # default dll path
    _dll_path = 'C:\\Program Files\\Andor SDK\\atmcd64d.dll'

    # success and error codes
    success_codes = {20002: 'DRV_SUCCESS', 20035: 'DRV_TEMP_NOT_STABILIZED',
                     20036: 'DRV_TEMPERATURE_STABILIZED', 20037: 'DRV_TEMPERATURE_NOT_REACHED'}
    error_codes = {
        20001: 'DRV_ERROR_CODES', 20003: 'DRV_VXDNOTINSTALLED', 20004: 'DRV_ERROR_SCAN',
        20005: 'DRV_ERROR_CHECK_SUM', 20006: 'DRV_ERROR_FILELOAD', 20007: 'DRV_UNKNOWN_FUNCTION',
        20008: 'DRV_ERROR_VXD_INIT', 20009: 'DRV_ERROR_ADDRESS', 20010: 'DRV_ERROR_PAGELOCK',
        20011: 'DRV_ERROR_PAGE_UNLOCK', 20012: 'DRV_ERROR_BOARDTEST', 20013: 'DRV_ERROR_ACK',
        20014: 'DRV_ERROR_UP_FIFO', 20015: 'DRV_ERROR_PATTERN', 20017: 'DRV_ACQUISITION_ERRORS',
        20018: 'DRV_ACQ_BUFFER', 20019: 'DRV_ACQ_DOWNFIFO_FULL',
        20020: 'DRV_PROC_UNKNOWN_INSTRUCTION', 20021: 'DRV_ILLEGAL_OP_CODE',
        20022: 'DRV_KINETIC_TIME_NOT_MET', 20023: 'DRV_ACCUM_TIME_NOT_MET',
        20024: 'DRV_NO_NEW_DATA', 20026: 'DRV_SPOOLERROR', 20027: 'DRV_SPOOLSETUPERROR',
        20033: 'DRV_TEMPERATURE_CODES', 20034: 'DRV_TEMPERATURE_OFF',
        20038: 'DRV_TEMPERATURE_OUT_RANGE', 20039: 'DRV_TEMPERATURE_NOT_SUPPORTED',
        20040: 'DRV_TEMPERATURE_DRIFT', 20049: 'DRV_GENERAL_ERRORS', 20050: 'DRV_INVALID_AUX',
        20051: 'DRV_COF_NOTLOADED', 20052: 'DRV_FPGAPROG', 20053: 'DRV_FLEXERROR',
        20054: 'DRV_GPIBERROR', 20064: 'DRV_DATATYPE', 20065: 'DRV_DRIVER_ERRORS',
        20066: 'DRV_P1INVALID', 20067: 'DRV_P2INVALID', 20068: 'DRV_P3INVALID',
        20069: 'DRV_P4INVALID', 20070: 'DRV_INIERROR', 20071: 'DRV_COFERROR',
        20072: 'DRV_ACQUIRING', 20073: 'DRV_IDLE', 20074: 'DRV_TEMPCYCLE',
        20075: 'DRV_NOT_INITIALIZED', 20076: 'DRV_P5INVALID', 20077: 'DRV_P6INVALID',
        20078: 'DRV_INVALID_MODE', 20079: 'DRV_INVALID_FILTER', 20080: 'DRV_I2CERRORS',
        20081: 'DRV_DRV_I2CDEVNOTFOUND', 20082: 'DRV_I2CTIMEOUT', 20083: 'DRV_P7INVALID',
        20089: 'DRV_USBERROR', 20090: 'DRV_IOCERROR', 20091: 'DRV_VRMVERSIONERROR',
        20093: 'DRV_USB_INTERRUPT_ENDPOINT_ERROR', 20094: 'DRV_RANDOM_TRACK_ERROR',
        20095: 'DRV_INVALID_TRIGGER_MODE', 20096: 'DRV_LOAD_FIRMWARE_ERROR',
        20097: 'DRV_DIVIDE_BY_ZERO_ERROR', 20098: 'DRV_INVALID_RINGEXPOSURES',
        20990: 'DRV_ERROR_NOCAMERA', 20991: 'DRV_NOT_SUPPORTED', 20992: 'DRV_NOT_AVAILABLE',
        20115: 'DRV_ERROR_MAP', 20116: 'DRV_ERROR_UNMAP', 20117: 'DRV_ERROR_MDL',
        20118: 'DRV_ERROR_UNMDL', 20119: 'DRV_ERROR_BUFFSIZE', 20121: 'DRV_ERROR_NOHANDLE',
        20130: 'DRV_GATING_NOT_AVAILABLE', 20131: 'DRV_FPGA_VOLTAGE_ERROR',
        20099: 'DRV_BINNING_ERROR', 20100: 'DRV_INVALID_AMPLIFIER',
        20101: 'DRV_INVALID_COUNTCONVERT_MODE'}

    def __init__(self, dll_path: Optional[str] = None, verbose: bool = False):
        if sys.platform != 'win32':
            self.dll: Any = None
            raise OSError("\"atmcd64d\" is only compatible with Microsoft Windows")
        else:
            self.dll = ctypes.windll.LoadLibrary(dll_path or self._dll_path)
        self.verbose = verbose

        # specify input arguments for data acquisition functions so that numpy arrays
        # are treated as if passed by reference.
        self.dll.GetAcquiredData.argtypes = [
            np.ctypeslib.ndpointer(dtype=np.int32, ndim=1, flags='C_CONTIGUOUS'),
            ctypes.c_ulong
        ]
        self.dll.GetMostRecentImage.argtypes = [
            np.ctypeslib.ndpointer(dtype=np.int32, ndim=1, flags='C_CONTIGUOUS'),
            ctypes.c_ulong
        ]
        self.dll.GetOldestImage.argtypes = [
            np.ctypeslib.ndpointer(dtype=np.int32, ndim=1, flags='C_CONTIGUOUS'),
            ctypes.c_ulong
        ]
        self.dll.GetImages.argtypes = [
            ctypes.c_long,
            ctypes.c_long,
            np.ctypeslib.ndpointer(dtype=np.int32, ndim=1, flags='C_CONTIGUOUS'),
            ctypes.c_ulong,
            ctypes.POINTER(ctypes.c_long),
            ctypes.POINTER(ctypes.c_long)
        ]
        self.dll.PostProcessCountConvert.argtypes = [
            np.ctypeslib.ndpointer(dtype=np.int32, ndim=1, flags='C_CONTIGUOUS'),
            np.ctypeslib.ndpointer(dtype=np.int32, ndim=1, flags='C_CONTIGUOUS'),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_int,
            ctypes.c_int
        ]
        self.dll.PostProcessNoiseFilter.argtypes = [
            np.ctypeslib.ndpointer(dtype=np.int32, ndim=1, flags='C_CONTIGUOUS'),
            np.ctypeslib.ndpointer(dtype=np.int32, ndim=1, flags='C_CONTIGUOUS'),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_float,
            ctypes.c_int,
            ctypes.c_int
        ]
        self.dll.PostProcessPhotonCounting.argtypes = [
            np.ctypeslib.ndpointer(dtype=np.int32, ndim=1, flags='C_CONTIGUOUS'),
            np.ctypeslib.ndpointer(dtype=np.int32, ndim=1, flags='C_CONTIGUOUS'),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_int,
            ctypes.c_int
        ]

    def abort_acquisition(self) -> None:
        code = self.dll.AbortAcquisition()
        self.error_check(code, 'AbortAcquisition')

    def error_check(self, code, function_name=''):
        if code in self.success_codes.keys():
            if self.verbose:
                print("atmcd64d: [%s]: %s" % (function_name, self.success_codes[code]))
        elif code in self.error_codes.keys():
            if self.error_codes[code] == 'DRV_NOT_INITIALIZED' and function_name == 'ShutDown':
                # Silence this error on exit
                return
            print("atmcd64d: [%s]: %s" % (function_name, self.error_codes[code]))
            raise SDKError(self.error_codes[code])
        else:
            print("atmcd64d: [%s]: Unknown code: %s" % (function_name, code))
            raise SDKError()

    def cooler_off(self) -> None:
        code = self.dll.CoolerOFF()
        self.error_check(code, 'CoolerOFF')

    def cooler_on(self) -> None:
        code = self.dll.CoolerON()
        self.error_check(code, 'CoolerON')

    def set_cooler_mode(self, mode: int) -> None:
        """This function determines whether the cooler is switched off when the camera is shut down.
        
        Parameters
        ----------
        int mode: 
            1 – Temperature is maintained on ShutDown 
            0 – Returns to ambient temperature on ShutDown
        """
        code = self.dll.SetCoolerMode(mode)
        self.error_check(code, 'SetCoolerMode')

    def free_internal_memory(self) -> None:
        code = self.dll.FreeInternalMemory()
        self.error_check(code, 'FreeInternalMemory')

    def get_acquired_data_by_value(self, size: int) -> npt.NDArray[np.int32]:
        """Get data of *size* from the CCD and return as an array."""
        c_data_array = ctypes.c_int * size
        c_data = c_data_array()
        # Temporarily remove argtypes from the dll function as they are specified
        # for get_acquired_data_by_reference(), which is optimized for speed.
        with out_argtypes(self.dll.GetAcquiredData) as func:
            code = func(ctypes.byref(c_data), size)
        self.error_check(code, 'GetAcquiredData')
        return np.ctypeslib.as_array(c_data)

    def get_acquired_data_by_reference(self, arr: npt.NDArray[np.int32]) -> None:
        """Get data from the CCD and write into the 1D array *arr*."""
        code = self.dll.GetAcquiredData(arr, arr.size)
        self.error_check(code, 'GetAcquiredData')

    def get_acquisition_timings(self) -> Tuple[float, float, float]:
        c_exposure = ctypes.c_float()
        c_accumulate = ctypes.c_float()
        c_kinetic = ctypes.c_float()
        code = self.dll.GetAcquisitionTimings(ctypes.byref(c_exposure),
                                              ctypes.byref(c_accumulate),
                                              ctypes.byref(c_kinetic))
        self.error_check(code, 'GetAcquisitionTimings')
        return c_exposure.value, c_accumulate.value, c_kinetic.value

    def get_camera_handle(self, camera_index) -> int:
        c_camera_handle = ctypes.c_long()
        code = self.dll.GetCameraHandle(camera_index, ctypes.byref(c_camera_handle))
        self.error_check(code, 'GetCameraHandle')
        return c_camera_handle.value

    def get_camera_serial_number(self) -> int:
        c_serial_number = ctypes.c_int()
        code = self.dll.GetCameraSerialNumber(ctypes.byref(c_serial_number))
        self.error_check(code, 'GetCameraSerialNumber')
        return c_serial_number.value

    def get_hardware_version(self) -> Tuple[int, int, int, int, int, int]:
        c_pcb = ctypes.c_int()
        c_decode = ctypes.c_int()
        c_dummy1 = ctypes.c_int()
        c_dummy2 = ctypes.c_int()
        c_firmware_version = ctypes.c_int()
        c_firmware_build = ctypes.c_int()
        code = self.dll.GetHardwareVersion(ctypes.byref(c_pcb), ctypes.byref(c_decode),
                                           ctypes.byref(c_dummy1), ctypes.byref(c_dummy2),
                                           ctypes.byref(c_firmware_version),
                                           ctypes.byref(c_firmware_build))
        self.error_check(code)
        return (c_pcb.value, c_decode.value, c_dummy1.value, c_dummy2.value,
                c_firmware_version.value, c_firmware_build.value)

    def get_head_model(self) -> str:
        c_head_model = ctypes.create_string_buffer(128)
        code = self.dll.GetHeadModel(c_head_model)
        self.error_check(code)
        return c_head_model.value.decode('ascii')

    def get_detector(self) -> Tuple[int, int]:
        c_x_pixels = ctypes.c_int()
        c_y_pixels = ctypes.c_int()
        code = self.dll.GetDetector(ctypes.byref(c_x_pixels), ctypes.byref(c_y_pixels))
        self.error_check(code, 'GetDetector')
        return c_x_pixels.value, c_y_pixels.value

    def get_keep_clean_time(self) -> float:
        c_keep_clean_time = ctypes.c_float()
        code = self.dll.GetKeepCleanTime(ctypes.byref(c_keep_clean_time))
        self.error_check(code, 'GetKeepCleanTime')
        return c_keep_clean_time.value

    def get_pixel_size(self) -> Tuple[float, float]:
        c_x_pixel_size = ctypes.c_float()
        c_y_pixel_size = ctypes.c_float()
        code = self.dll.GetPixelSize(ctypes.byref(c_x_pixel_size), ctypes.byref(c_y_pixel_size))
        self.error_check(code, 'GetPixelSize')
        return c_x_pixel_size.value, c_y_pixel_size.value

    def get_fastest_recommended_vertical_shift_speed(self) -> Tuple[float, float]:
        c_index = ctypes.c_float()
        c_speed = ctypes.c_float()
        code = self.dll.GetFastestRecommendedVSSpeed(ctypes.byref(c_index), ctypes.byref(c_speed))
        self.error_check(code, 'GetFastestRecommendedVSSpeed')
        return c_index.value, c_speed.value

    def get_filter_mode(self) -> int:
        c_mode = ctypes.c_int()
        code = self.dll.GetFilterMode(ctypes.byref(c_mode))
        self.error_check(code, 'GetFilterMode')
        return c_mode.value

    def get_hs_speed(self, channel: int, typ: int, index: int) -> float:
        c_speed = ctypes.c_float()
        code = self.dll.GetHSSpeed(channel, typ, index, ctypes.byref(c_speed))
        self.error_check(code, 'GetHSSpeed')
        return c_speed.value

    def get_images_by_value(self, first: int, last: int, size: int) -> Tuple[npt.NDArray[np.int32],
                                                                    int, int]:
        """Get data of *size* from the CCD and return as an array."""
        c_data_array = ctypes.c_int * size
        c_data = c_data_array()
        c_validfirst = ctypes.c_long()
        c_validlast = ctypes.c_long()
        # Temporarily remove argtypes from the dll function as they are specified
        # for get_images_by_reference(), which is optimized for speed.
        with out_argtypes(self.dll.GetImages) as func:
            code = func(first, last, ctypes.byref(c_data), abs(size),
                        ctypes.byref(c_validfirst), ctypes.byref(c_validlast))
        self.error_check(code, 'GetImages')
        return np.ctypeslib.as_array(c_data), c_validfirst.value, c_validlast.value

    def get_images_by_reference(self, first: int, last: int,
                                arr: npt.NDArray[np.int32]) -> Tuple[int, int]:
        """Get images from the CCD and write into the 1D array *arr*."""
        c_validfirst = ctypes.c_long()
        c_validlast = ctypes.c_long()
        code = self.dll.GetMostRecentImage(first, last, arr, arr.size,
                                           ctypes.byref(c_validfirst), ctypes.byref(c_validlast))
        self.error_check(code, 'GetMostRecentImage')
        return c_validfirst.value, c_validlast.value

    def get_most_recent_image_by_value(self, size: int) -> npt.NDArray[np.int32]:
        """Get the most recent image of *size* from the CCD and return as an array."""
        c_data_array = ctypes.c_int * size
        c_data = c_data_array()
        # Temporarily remove argtypes from the dll function as they are specified
        # for get_most_recent_image_by_reference(), which is optimized for speed.
        with out_argtypes(self.dll.GetMostRecentImage) as func:
            code = func(ctypes.byref(c_data), size)
        self.error_check(code, 'GetMostRecentImage')
        return np.ctypeslib.as_array(c_data)

    def get_most_recent_image_by_reference(self, arr: npt.NDArray[np.int32]) -> None:
        """Get the most recent image from the CCD and write into the 1D array *arr*."""
        code = self.dll.GetMostRecentImage(arr, arr.size)
        self.error_check(code, 'GetMostRecentImage')

    def get_number_available_images(self) -> Tuple[int, int]:
        c_first = ctypes.c_int32()
        c_last = ctypes.c_int32()
        code = self.dll.GetNumberAvailableImages(ctypes.byref(c_first), ctypes.byref(c_first))
        self.error_check(code, 'GetNumberAvailableImages')
        return c_first.value, c_last.value

    def get_number_hs_speeds(self, channel: int, typ: int) -> int:
        c_speeds = ctypes.c_int()
        code = self.dll.GetNumberHSSpeeds(channel, typ, ctypes.byref(c_speeds))
        self.error_check(code, 'GetNumberHSSpeeds')
        return c_speeds.value

    def get_number_new_images(self) -> Tuple[int, int]:
        c_first = ctypes.c_long()
        c_last = ctypes.c_long()
        code = self.dll.GetNumberNewImages(ctypes.byref(c_first), ctypes.byref(c_first))
        self.error_check(code, 'GetNumberNewImages')
        return c_first.value, c_last.value

    def get_number_vs_speeds(self) -> int:
        c_speeds = ctypes.c_int()
        code = self.dll.GetNumberVSSpeeds(ctypes.byref(c_speeds))
        self.error_check(code, 'GetNumberVSSpeeds')
        return c_speeds.value

    def get_number_preamp_gains(self) -> int:
        c_gains = ctypes.c_int()
        code = self.dll.GetNumberPreAmpGains(ctypes.byref(c_gains))
        self.error_check(code, 'GetNumberPreAmpGains')
        return c_gains.value

    def get_oldest_image_by_value(self, size: int) -> npt.NDArray[np.int32]:
        """Get the oldest image of *size* from the CCD and return as an array."""
        c_data_array = ctypes.c_int * size
        c_data = c_data_array()
        # Temporarily remove argtypes from the dll function as they are specified
        # for get_oldest_image_by_reference(), which is optimized for speed.
        with out_argtypes(self.dll.GetOldestImage) as func:
            code = func(ctypes.byref(c_data), size)
        self.error_check(code, 'GetOldestImage')
        return np.ctypeslib.as_array(c_data)

    def get_oldest_image_by_reference(self, arr: npt.NDArray[np.int32]) -> None:
        """Get the oldest image from the CCD and write into the 1D array *arr*."""
        code = self.dll.GetOldestImage(arr, arr.size)
        self.error_check(code, 'GetOldestImage')

    def get_preamp_gain(self, index: int):
        """For those systems that provide a number of pre amp gains to apply to the data as it is read out; this function retrieves the amount of gain that is stored for a particular index. 
        
        The number of gains available can be obtained by calling the :meth:`get_number_preamp_gains` function and a specific Gain can be selected using the function :meth:`set_preamp_gain`.
        
        Parameters
        ----------
        int index: gain index Valid values: 0 to :meth:`get_number_preamp_gains`-1
        
        Returns
        -------
        float* gain: gain factor for this index.
        """
        c_gain = ctypes.c_float()
        code = self.dll.GetPreAmpGain(index, ctypes.byref(c_gain))
        self.error_check(code, 'GetPreAmpGain')
        return c_gain.value
        
    def get_preamp_gain_text(self, index: int) -> str:
        """This function will return a string with a pre amp gain description. 
        
        The pre amp gain is selected using the index. The SDK has a string associated with each of its pre amp gains. The maximum number of characters needed to store the pre amp gain descriptions is 30. The user has to specify the number of characters they wish to have returned to them from this function.
        
        Parameters
        ----------
        int index: gain index 
            Valid values: 0 to :meth:`get_number_preamp_gains`-1
        
        Returns
        -------
        char* name: A user allocated array of characters for storage of the description.
        """
        # TODO: UNTESTED
        c_name = ctypes.create_string_buffer(1024)
        code = self.dll.GetPreAmpGainText(index, c_name, 1024)
        self.error_check(code, 'GetPreAmpGainText')
        return c_name.value.decode('ascii')
        
    def get_qe(self, wavelength: float, mode: int) -> float:
        """Returns the percentage QE for a particular head model at a user specified wavelength. 
        
        Parameters
        ----------
        float wavelength: wavelength at which QE is required 
        unsigned int mode: Clara mode (Normal (0) or Extended NIR (1)). 0 for all other systems 
        
        Returns
        -------
        float* QE: requested QE
        """
        # TODO: UNTESTED
        c_qe = ctypes.c_float()
        code = self.dll.GetQE(self.get_head_model(), wavelength, mode, ctypes.byref(c_qe))
        self.error_check(code, 'GetQE')
        return c_qe.value

    def get_relative_image_times(self, first: int, last: int, size: int) -> npt.NDArray[np.int64]:
        """This function will return an array of the start times in nanoseconds of a user defined number of frames relative to the initial frame.
        
        Parameters
        ----------
        unsigned int first: Index of first frame in array.
        unsigned int last: Index of last frame in array. 
        int index: number of frames for which start time is required.
        
        Returns
        -------
        at_u64 * arr: array of times in nanoseconds for each frame from time of start.
        """
        # TODO: UNTESTED
        c_arr = (ctypes.c_longlong * size)()
        code = self.dll.GetRelativeImageTimes(first, last, ctypes.byref(c_arr), size)
        self.error_check(code, 'GetRelativeImageTimes')
        return np.ctypeslib.as_array(c_data)

    def get_size_of_circular_buffer(self) -> int:
        """This function will return the maximum number of images the circular buffer can store based on the current acquisition settings.
        
        Returns
        -------
        long* index: returns the maximum number of images the circular buffer can store.
        """
        c_index = ctypes.c_long()
        code = self.dll.GetSizeOfCircularBuffer(ctypes.byref(c_index))
        self.error_check(code, 'GetSizeOfCircularBuffer')
        return c_index.value

    def get_status(self) -> int:
        """This function will return the current status of the Andor SDK system. 
        
        This function should be called before an acquisition is started to ensure that it is IDLE and during an acquisition to monitor the process.
        
        Returns
        -------
        int* status: current status
        """
        c_status = ctypes.c_int()
        code = self.dll.GetStatus(ctypes.byref(c_status))
        self.error_check(code, 'GetStatus')
        return c_status.value

    def get_temperature(self) -> int:
        """This function returns the temperature of the detector to the nearest degree. 
        
        It also gives the status of cooling process.
        
        Returns
        -------
        int* temperature: temperature of the detector
        """
        c_temperature = ctypes.c_int()
        code = self.dll.GetTemperature(ctypes.byref(c_temperature))
        self.error_check(code, 'GetTemperature')
        return c_temperature.value

    def get_temperature_range(self) -> Tuple[int, int]:
        """This function returns the valid range of temperatures in centigrade to which the detector can be cooled.
        
        Returns
        -------
        int* mintemp: minimum temperature 
        int* maxtemp: maximum temperature
        """
        c_min_temp = ctypes.c_int()
        c_max_temp = ctypes.c_int()
        code = self.dll.GetTemperatureRange(ctypes.byref(c_min_temp), ctypes.byref(c_max_temp))
        self.error_check(code, 'GetTemperatureRange')
        return c_min_temp.value, c_max_temp.value

    def get_vs_speed(self, index: int) -> float:
        """As your Andor SDK system may be capable of operating at more than one vertical shift speed this function will return the actual speeds available. 
        
        The value returned is in microseconds.
        
        Parameters
        ----------
        int index: speed required. 
            Valid values: 0 to :meth:`get_number_vs_speeds`-1
            
        Returns
        -------
        float* speed: speed in microseconds per pixel shift.
        """
        c_speed = ctypes.c_float()
        code = self.dll.GetVSSpeed(index, ctypes.byref(c_speed))
        self.error_check(code, 'GetVSSpeed')
        return c_speed.value

    def initialize(self, directory: str) -> None:
        """This function will initialize the Andor SDK System.
        
        As part of the initialization procedure on some cameras (i.e. Classic, iStar and earlier iXion) the DLL will need access to a DETECTOR.INI which contains information relating to the detector head, number pixels, readout speeds etc. If your system has multiple cameras then see the section Controlling multiple cameras of the Andor SDK user's manual.
        Parameters
        ----------
        char* dir: Path to the directory containing the files
        """
        code = self.dll.Initialize(directory)
        self.error_check(code, 'Initialize')

    def is_cooler_on(self) -> int:
        c_cooler_status = ctypes.c_int()
        code = self.dll.IsCoolerOn(ctypes.byref(c_cooler_status))
        self.error_check(code, 'IsCoolerOn')
        return c_cooler_status.value

    def is_preamp_gain_available(self, channel: int, amplifier: int, index: int, pa: int) -> int:
        """This function checks that the AD channel exists, and that the amplifier, speed and gain are available for the AD channel.
        
        Parameters
        ----------
        int channel: AD channel index. 
        int amplifier: Type of output amplifier. 
        int index: Channel speed index.
        int pa: PreAmp gain index. 
        
        Returns
        -------
        int* status: 0: PreAmpGain not available. 
                     1: PreAmpGain Available.
        """
        c_status = ctypes.c_int()
        code = self.dll.IsPreAmpGainAvailable(channel, amplifier, index, pa,
                                              ctypes.byref(c_status))
        self.error_check(code, 'IsPreAmpGainAvailable')
        return c_status.value

    def post_process_count_convert(self, input_image: npt.NDArray[np.int32], num_images: int,
                                   baseline: int, mode: int, em_gain: int, qe: float,
                                   sensitivity: float, height: int,
                                   width: int) -> npt.NDArray[np.int32]:
        output_image = np.empty_like(input_image)
        breakpoint()
        code = self.dll.PostProcessCountConvert(input_image, output_image, output_image.size,
                                                num_images, baseline, mode, em_gain, qe,
                                                sensitivity, height, width)
        self.error_check(code, 'PostProcessCountConvert')
        return output_image

    def post_process_noise_filter(self, input_image: npt.NDArray[np.int32], baseline: int,
                                  mode: int, threshold: float, height: int,
                                  width: int) -> npt.NDArray[np.int32]:
        output_image = np.empty_like(input_image)
        code = self.dll.PostProcessNoiseFilter(input_image, output_image, output_image.size,
                                               baseline, mode, threshold, height, width)
        self.error_check(code, 'PostProcessNoiseFilter')
        return output_image

    def post_process_photon_counting(self, input_image: npt.NDArray[np.int32], num_images: int,
                                     num_frames: int, threshold: Sequence[float], height: int,
                                     width: int) -> npt.NDArray[np.int32]:
        output_image = np.empty_like(input_image)
        number_of_tresholds = len(threshold)
        c_threshold = (ctypes.c_float * number_of_tresholds)(*threshold)
        c_threshold_pointer = ctypes.cast(c_threshold, ctypes.POINTER(ctypes.c_float))
        code = self.dll.PostProcessPhotonCounting(input_image, output_image, output_image.size,
                                                  num_images, num_frames, number_of_tresholds,
                                                  c_threshold_pointer, height, width)
        self.error_check(code, 'PostProcessPhotonCounting')
        return output_image

    def prepare_acquisition(self) -> None:
        """This function reads the current acquisition setup and allocates and configures any memory that will be used during the acquisition. 
        
        The function call is not required as it will be called automatically by the :meth:`start_acquisition` function if it has not already been called externally. However for long kinetic series acquisitions the time to allocate and configure any memory can be quite long which can result in a long delay between calling :meth:`start_acquisition` and the acquisition actually commencing. For iDus, there is an additional delay caused by the camera being set-up with any new acquisition parameters. Calling :meth:`prepare_acquisition` first will reduce this delay in the :meth:`start_acquisition` call.
        """
        code = self.dll.PrepareAcquisition()
        self.error_check(code, 'PrepareAcquisition')

    def set_accumulation_cycle_time(self, cycle_time: float) -> None:
        """This function will set the accumulation cycle time to the nearest valid value not less than the given value. 
        
        The actual cycle time used is obtained by :meth:`get_acquisition_timings`. Please refer to section 5 of the Andor SDK user's manual for further information.
        
        Parameters
        ----------
        float time: the accumulation cycle time in seconds.
        """
        c_cycle_time = ctypes.c_float(cycle_time)
        code = self.dll.SetAccumulationCycleTime(c_cycle_time)
        self.error_check(code, 'SetAccumulationCycleTime')

    def set_acquisition_mode(self, mode: int) -> None:
        """This function will set the acquisition mode to be used on the next :meth:`start_acquisition`. 
        
        Parameters
        ----------
        int mode: the acquisition mode.
            Valid values: 1 Single Scan
                          2 Accumulate
                          3 Kinetics
                          4 Fast Kinetics
                          5 Run till abort
                                                      
        """
        c_mode = ctypes.c_int(mode)
        code = self.dll.SetAcquisitionMode(c_mode)
        self.error_check(code, 'SetAcquisitionMode')

    def set_current_camera(self, camera_handle: int) -> None:
        c_camera_handle = ctypes.c_long(camera_handle)
        code = self.dll.SetCurrentCamera(c_camera_handle)
        self.error_check(code, 'SetCurrentCamera')

    def set_exposure_time(self, exposure_time: float) -> None:
        """This function will set the exposure time to the nearest valid value not less than the given value. 
        
        The actual exposure time used is obtained by :meth:`get_acquisition_timings`. Please refer to section 5 of the Andor SDK user's manual for further information.
        
        Parameters
        ----------
        float time: the exposure time in seconds.
        """
        c_time = ctypes.c_float(exposure_time)
        code = self.dll.SetExposureTime(c_time)
        self.error_check(code, 'SetExposureTime')

    def set_filter_mode(self, mode: int) -> None:
        """This function will set the state of the cosmic ray filter mode for future acquisitions. 
        
        If the filter mode is on, consecutive scans in an accumulation will be compared and any cosmic ray-like features that are only present in one scan will be replaced with a scaled version of the corresponding pixel value in the correct scan.
        
        Parameters
        ----------
        int mode: current state of filter. 0 OFF
                                           2 ON   
        """
        c_mode = ctypes.c_int(mode)
        code = self.dll.SetFilterMode(c_mode)
        self.error_check(code, 'SetFilterMode')

    def set_hs_speed(self, typ: int, index: int) -> None:
        """This function will set the speed at which the pixels are shifted into the output node during the readout phase of an acquisition. 
        
        Typically your camera will be capable of operating at several horizontal shift speeds. To get the actual speed that an index corresponds to use the :meth`get_hs_speed` function.
        
        Parameters
        ----------
        int typ: output amplification. 
            Valid values: 0 electron multiplication/Conventional(clara).
                          1 conventional/Extended NIR mode(clara).
        int index: the horizontal speed to be used. 
            Valid values: 0 to :meth:`get_number_hs_speeds`-1
        """
        code = self.dll.SetHSSpeed(typ, index)
        self.error_check(code, 'SetHSSpeed')

    def set_image(self, hbin: int, vbin: int, hstart: int, hend: int, vstart: int,
                  vend: int) -> None:
        """This function will set the horizontal and vertical binning to be used when taking a full resolution image.
        
        Parameters
        ----------
        int hbin: number of pixels to bin horizontally. 
        int vbin: number of pixels to bin vertically. 
        int hstart: Start column (inclusive).
        int hend: End column (inclusive). 
        int vstart: Start row (inclusive). 
        int vend: End row (inclusive).
        """
        code = self.dll.SetImage(hbin, vbin, hstart, hend, vstart, vend)
        self.error_check(code, 'SetImage')

    def set_kinetic_cycle_time(self, time: float) -> None:
        """This function will set the kinetic cycle time to the nearest valid value not less than the given value. 
        
        The actual time used is obtained by :meth:`get_acquisition_timings`. Please refer to section 5 of the Andor SDK user's guide for further information.
        
        Parameters
        ----------
        float time: the kinetic cycle time in seconds.
        """
        code = self.dll.SetKineticCycleTime(time)
        self.error_check(code, 'SetKineticCycleTime')

    def set_multi_track(self, number: int, height: int, offset: int) -> Tuple[int, int]:
        """This function will set the multi-Track parameters. 
        
        The tracks are automatically spread evenly over the detector. Validation of the parameters is carried out in the following order: 
        
         - Number of tracks, 
         - Track height 
         - Offset.
         
        The first pixels row of the first track is returned via ‘bottom’. The number of rows between each track is returned via ‘gap’.
        
        Parameters
        ----------
        int number: number tracks 
            Valid values 1 to number of vertical pixels
        int height: height of each track 
            Valid values >0 (maximum depends on number of tracks)
        int offset: vertical displacement of tracks 
            Valid values depend on number of tracks and track height
        
        Returns
        -------
        int* bottom: first pixels row of the first track 
        int* gap: number of rows between each track (could be 0)
        """
        c_bottom = ctypes.c_int()
        c_gap = ctypes.c_int()
        code = self.dll.SetMultiTrack(number, height, offset, ctypes.byref(c_bottom),
                                      ctypes.byref(c_gap))
        self.error_check(code, 'SetMultiTrack')
        return c_bottom.value, c_gap.value

    def set_number_accumulations(self, number: int) -> None:
        """This function will set the number of scans accumulated in memory. 
        
        This will only take effect if the acquisition mode is either Accumulate or Kinetic Series.
        
        Parameters
        ----------
        int number: number of scans to accumulate
        """
        code = self.dll.SetNumberAccumulations(number)
        self.error_check(code, 'SetNumberAccumulations')

    def set_number_kinetics(self, number: int) -> None:
        """This function will set the number of scans (possibly accumulated scans) to be taken during a single acquisition sequence. 
        
        This will only take effect if the acquisition mode is Kinetic Series.
        
        Parameters
        ----------
        int number: number of scans to store
        """
        code = self.dll.SetNumberKinetics(number)
        self.error_check(code, 'SetNumberKinetics')

    def set_random_tracks(self, num_tracks: int, areas: Sequence[int]) -> npt.NDArray[np.int32]:
        """This function will set the Random-Track parameters. 
        
        The positions of the tracks are validated to ensure that the tracks are in increasing order and do not overlap. The horizontal binning is set via the SetCustomTrackHBin function. The vertical binning is set to the height of each track. 
        
        Some cameras need to have at least 1 row in between specified tracks. Ixon+ and the USB cameras allow tracks with no gaps in between. 
        
        Examples
        --------
        Tracks specified as 20 30 31 40 tells the SDK that the first track starts at row 20 in the CCD and finishes at row 30. The next track starts at row 31 (no gap between tracks) and ends at row 40.
        
        Parameters
        ----------
        int numTracks: number tracks 
            Valid values 1 to number of vertical pixels/2
        
        Returns
        -------
        int* areas: pointer to an array of track positions. The array has the form bottom1, top1, bottom2, top2 ….. bottomN, topN
        """
        c_areas = (ctypes.c_int * (2 * num_tracks))(*sorted(areas))
        code = self.dll.SetRandomTracks(num_tracks, ctypes.byref(c_areas))
        self.error_check(code, 'SetRandomTracks')
        return np.ctypeslib.as_array(c_areas)

    def set_read_mode(self, mode: int) -> None:
        """This function will set the readout mode to be used on the subsequent acquisitions. 
        
        Parameters
        ----------
        int mode: readout mode 
            Valid values: 0 Full Vertical Binning
                          1 Multi-Track
                          2 Random-Track
                          3 Single-Track
                          4 Image
                          
        """
        code = self.dll.SetReadMode(mode)
        self.error_check(code, 'SetReadMode')

    def set_single_track(self, centre: int, height: int) -> None:
        """This function will set the single track parameters. 
        
        The parameters are validated in the following order: centre row and then track height.
        
        Parameters
        ----------
        int centre: centre row of track Valid range 1 to number of vertical pixels.
        int height: height of track Valid range > 1 (maximum value depends on centre row and number of vertical pixels).
        """
        code = self.dll.SetSingleTrack(centre, height)
        self.error_check(code, 'SetSingleTrack')

    def set_shutter(self, typ: int, mode: int, closing_time: int, opening_time: int) -> None:
        c_typ = ctypes.c_int(typ)
        c_mode = ctypes.c_int(mode)
        c_closing_time = ctypes.c_int(closing_time)
        c_opening_time = ctypes.c_int(opening_time)
        code = self.dll.SetShutter(c_typ, c_mode, c_closing_time, c_opening_time)
        self.error_check(code, 'SetShutter')

    def set_temperature(self, temperature: int) -> None:
        c_temperature = ctypes.c_int(temperature)
        code = self.dll.SetTemperature(c_temperature)
        self.error_check(code, 'SetTemperature')

    def set_trigger_mode(self, mode: int) -> None:
        c_mode = ctypes.c_int(mode)
        code = self.dll.SetTriggerMode(c_mode)
        self.error_check(code, 'SetTriggerMode')

    def set_vs_speed(self, index: int) -> None:
        code = self.dll.SetVSSpeed(index)
        self.error_check(code, 'SetVSSpeed')

    def set_preamp_gain(self, index: int) -> None:
        code = self.dll.SetPreAmpGain(index)
        self.error_check(code, 'SetPreAmpGain')

    def shut_down(self) -> None:
        code = self.dll.ShutDown()
        self.error_check(code, 'ShutDown')

    def start_acquisition(self) -> None:
        code = self.dll.StartAcquisition()
        self.error_check(code, 'StartAcquisition')

    def wait_for_acquisition(self) -> None:
        code = self.dll.WaitForAcquisition()
        self.error_check(code, 'WaitForAcquisition')
