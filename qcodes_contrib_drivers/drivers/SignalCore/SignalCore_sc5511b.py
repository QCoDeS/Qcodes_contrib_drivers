# -*- coding: utf-8 -*-
"""
Created on Fri Mar 19 14:11:31 2021

@author: Theo Shaw

A simple driver for SignalCore SC5511B to be used with QCoDes, transferred from the one written Chao Zhou, from Erick Brindock
"""

import ctypes
import logging
from typing import Any, Dict, Optional, List

from qcodes import (Instrument, validators as vals)
from qcodes.utils.validators import Numbers

import numpy as np


class Device_rf_params_t(ctypes.Structure):
    _fields_ = [("rf1_freq", ctypes.c_double),
                ("start_freq", ctypes.c_double),
                ("stop_freq", ctypes.c_double),
                ("step_freq", ctypes.c_double),
                ("sweep_dwell_time", ctypes.c_uint32),
                ("sweep_cycles", ctypes.c_uint32),
                ("buffer_points", ctypes.c_uint32),
                ("rf_level", ctypes.c_float),
                ("rf2_freq", ctypes.c_uint16)
                ]


class Device_temperature_t(ctypes.Structure):
    _fields_ = [("device_temp", ctypes.c_float)]


class Operate_status_t(ctypes.Structure):
    _fields_ = [("rf1_lock_mode", ctypes.c_ubyte),
                ("rf1_loop_gain", ctypes.c_ubyte),
                ("device_access", ctypes.c_ubyte),
                ("rf2_standby", ctypes.c_ubyte),
                ("rf1_standby", ctypes.c_ubyte),
                ("auto_pwr_disable", ctypes.c_ubyte),
                ("alc_mode", ctypes.c_ubyte),
                ("rf1_out_enable", ctypes.c_ubyte),
                ("ext_ref_lock_enable", ctypes.c_ubyte),
                ("ext_ref_detect", ctypes.c_ubyte),
                ("ref_out_select", ctypes.c_ubyte),
                ("list_mode_running", ctypes.c_ubyte),
                ("rf1_mode", ctypes.c_ubyte),
                ("over_temp", ctypes.c_ubyte),
                ("harmonic_ss", ctypes.c_ubyte)
                ]


class Pll_status_t(ctypes.Structure):
    _fields_ = [("sum_pll_ld", ctypes.c_ubyte),
                ("crs_pll_ld", ctypes.c_ubyte),
                ("fine_pll_ld", ctypes.c_ubyte),
                ("crs_ref_pll_ld", ctypes.c_ubyte),
                ("crs_aux_pll_ld", ctypes.c_ubyte),
                ("ref_100_pll_ld", ctypes.c_ubyte),
                ("ref_10_pll_ld", ctypes.c_ubyte),
                ("rf2_pll_ld", ctypes.c_ubyte)]


class List_mode_t(ctypes.Structure):
    _fields_ = [("sss_mode", ctypes.c_ubyte),
                ("sweep_dir", ctypes.c_ubyte),
                ("tri_waveform", ctypes.c_ubyte),
                ("hw_trigger", ctypes.c_ubyte),
                ("step_on_hw_trig", ctypes.c_ubyte),
                ("return_to_start", ctypes.c_ubyte),
                ("trig_out_enable", ctypes.c_ubyte),
                ("trig_out_on_cycle", ctypes.c_ubyte)]


class Device_status_t(ctypes.Structure):
    _fields_ = [("list_mode", List_mode_t),
                ("operate_status_t", Operate_status_t),
                ("pll_status_t", Pll_status_t)]


class Device_info_t(ctypes.Structure):
    _fields_ = [("serial_number", ctypes.c_uint32),
                ("hardware_revision", ctypes.c_float),
                ("firmware_revision", ctypes.c_float),
                ("manufacture_date", ctypes.c_uint32)
                ]


# End of Structures------------------------------------------------------------
class SignalCore_SC5511B(Instrument):

    dllpath = r"C:\Program Files\SignalCore\SC5510B_11B\api\c\x64\sc5511b_usb.dll"

    def __init__(self, name: str, serial_number: str,
                 dllpath: Optional[str] = None, debug=False, **kwargs: Any):
        super().__init__(name, **kwargs)

        logging.info(__name__ + f' : Initializing instrument SignalCore generator {serial_number}')
        if dllpath is not None:
            self._dll = ctypes.CDLL(dllpath)
        else:
            self._dll = ctypes.CDLL(self.dllpath)

        if debug:
            print(self._dll)

        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        
        
        self._handle = ctypes.c_void_p()
        
        status_open = self._dll.sc5511b_usb_open_device(bytes(serial_number, 'utf-8'), ctypes.byref(self._handle))

        
        self._serial_number = ctypes.c_char_p(bytes(serial_number, 'utf-8'))
        self._rf_params = Device_rf_params_t(0, 0, 0, 0, 0, 0, 0, 0, 0)
        self._status = Operate_status_t(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        self._open = False
        self._temperature = Device_temperature_t(0)

        self._pll_status = Pll_status_t()
        self._list_mode = List_mode_t()
        self._device_status = Device_status_t(self._list_mode, self._status, self._pll_status)
        
        if debug:
            print(serial_number, self._handle)
            self._dll.sc5511b_usb_get_device_status.argtypes = ctypes.c_char_p,ctypes.c_void_p #not sure of the type for dev status pointer
            self._dll.sc5511b_usb_get_device_status.restype = ctypes.c_long
            self._dll.sc5511b_usb_get_device_status(self._handle, ctypes.byref(self._device_status))
            status = self._device_status.operate_status_t.rf1_out_enable
            print('check status', status)
        
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle) #why are we closing it here?
        
        self._device_info = Device_info_t(0, 0, 0, 0)
        self.get_idn()
        self.do_set_auto_level_disable(0)  # setting this to 1 will lead to unstable output power

        self.add_parameter('sweep_start_frequency',
                           label='sweep_start_frequency',
                           get_cmd=self.do_get_sweep_start_frequency,
                           get_parser=float,
                           set_cmd=self.do_set_sweep_start_frequency,
                           set_parser=float,
                           unit='Hz',
                           vals=Numbers(min_value=0, max_value=20e9)
                           )

        self.add_parameter('sweep_stop_frequency',
                           label='sweep_stop_frequency',
                           get_cmd=self.do_get_sweep_stop_frequency,
                           get_parser=float,
                           set_cmd=self.do_set_sweep_stop_frequency,
                           set_parser=float,
                           unit='Hz',
                           vals=Numbers(min_value=0, max_value=20e9)
                           )

        self.add_parameter('sweep_step_frequency',
                           label='sweep_step_frequency',
                           get_cmd=self.do_get_sweep_step_frequency,
                           get_parser=float,
                           set_cmd=self.do_set_sweep_step_frequency,
                           set_parser=float,
                           unit='Hz',
                           vals=Numbers(min_value=0, max_value=20e9)
                           )

        self.add_parameter('sweep_dwell_time',
                           label='sweep_dwell_time',
                           get_cmd=self.do_get_sweep_dwell_time,
                           get_parser=int,
                           set_cmd=self.do_set_sweep_dwell_time,
                           set_parser=int,
                           unit='',
                           vals=Numbers(min_value=1)
                           )

        self.add_parameter('sweep_cycles',
                           label='sweep_cycles',
                           get_cmd=self.do_get_sweep_cycles,
                           get_parser=int,
                           set_cmd=self.do_set_sweep_cycles,
                           set_parser=int,
                           unit='',
                           vals=Numbers(min_value=0)
                           )

        self.add_parameter('trig_out_enable',
                           label='trig_out_enable',
                           get_cmd=self.do_get_trig_out_enable,
                           set_cmd=self.do_set_trig_out_enable,
                           unit='',
                           vals=vals.Enum(0, 1)
                           )

        self.add_parameter('trig_out_on_cycle',
                           label='trig_out_on_cycle',
                           get_cmd=self.do_get_trig_out_on_cycle,
                           set_cmd=self.do_set_trig_out_on_cycle,
                           unit='',
                           vals=vals.Enum(0, 1)
                           )

        self.add_parameter('step_on_hw_trig',
                           label='step_on_hw_trig',
                           get_cmd=self.do_get_step_on_hw_trig,
                           set_cmd=self.do_set_step_on_hw_trig,
                           unit='',
                           vals=vals.Enum(0, 1)
                           )

        self.add_parameter('return_to_start',
                           label='return_to_start',
                           get_cmd=self.do_get_return_to_start,
                           set_cmd=self.do_set_return_to_start,
                           unit='',
                           vals=vals.Enum(0, 1)
                           )

        self.add_parameter('hw_trigger',
                           label='hw_trigger',
                           get_cmd=self.do_get_hw_trig,
                           set_cmd=self.do_set_hw_trig,
                           unit='',
                           vals=vals.Enum(0, 1)
                           )

        self.add_parameter('tri_waveform',
                           label='tri_waveform',
                           get_cmd=self.do_get_tri_waveform,
                           set_cmd=self.do_set_tri_waveform,
                           unit='',
                           vals=vals.Enum(0, 1)
                           )

        self.add_parameter('sweep_dir',
                           label='sweep_dir',
                           get_cmd=self.do_get_sweep_dir,
                           set_cmd=self.do_set_sweep_dir,
                           unit='',
                           vals=vals.Enum(0, 1)
                           )

        self.add_parameter('sss_mode',
                           label='sss_mode',
                           get_cmd=self.do_get_sss_mode,
                           set_cmd=self.do_set_sss_mode,
                           unit='',
                           vals=vals.Enum(0, 1)
                           )

        self.add_parameter('rf1_mode',
                           label='rf1_mode',
                           get_cmd=self.do_get_rf1_mode,
                           set_cmd=self.do_set_rf1_mode,
                           unit='',
                           )

        self.add_parameter('power',
                           label='power',
                           get_cmd=self.do_get_power,
                           get_parser=float,
                           set_cmd=self.do_set_power,
                           set_parser=float,
                           unit='dBm',
                           vals=Numbers(min_value=-144, max_value=19))

        #equivalent to sc.output in om's
        self.add_parameter('output_status',
                           label='output_status',
                           get_cmd=self.do_get_output_status,
                           get_parser=int,
                           set_cmd=self.do_set_output_status,
                           set_parser=int,
                           vals=Numbers(min_value=0, max_value=1))
        
        self.add_parameter('standby',
                           label='standby',
                           get_cmd=self.do_get_standby,
                           get_parser=int,
                           set_cmd=self.do_set_standby,
                           set_parser=int,
                           vals=Numbers(min_value=0, max_value=1))

        self.add_parameter('frequency',
                           label='frequency',
                           get_cmd=self.do_get_frequency,
                           get_parser=float,
                           set_cmd=self.do_set_frequency,
                           set_parser=float,
                           unit='Hz',
                           vals=Numbers(min_value=0, max_value=20e9))

        self.add_parameter('reference_source',
                           label='reference_source',
                           get_cmd=self.do_get_reference_source,
                           get_parser=int,
                           set_cmd=self.do_set_reference_source,
                           set_parser=int,
                           vals=Numbers(min_value=0, max_value=1))

        self.add_parameter('auto_level_disable',
                           label='0 = power is leveled on frequency change',
                           get_cmd=self.do_get_auto_level_disable,
                           get_parser=int,
                           set_cmd=self.do_set_auto_level_disable,
                           set_parser=int,
                           vals=Numbers(min_value=0, max_value=1))

        self.add_parameter('temperature',
                           label='temperature',
                           get_cmd=self.do_get_device_temp,
                           get_parser=float,
                           unit="C",
                           vals=Numbers(min_value=0, max_value=200))
        
        
        #we could get better control by making these parameters arrays, e.g. one parameter to hold all the frequencies
        #but I don't need that so I'm not going to add it right now
        self.add_parameter('list_points_number',
                           label = 'list_points_number',
                           get_cmd = self.do_get_list_points_number,
                           get_parser = int,
                           set_cmd = self.do_set_list_points_number,
                           set_parser = int,
                           unit = '')

        self.add_parameter('list_start_frequency',
                           label='list_start_frequency',
                           get_cmd=self.do_get_list_start_frequency,
                           get_parser=float,
                           set_cmd=self.do_set_list_start_frequency,
                           set_parser=float,
                           unit='Hz',
                           vals=Numbers(min_value=0, max_value=20e9)
                           )
                
        self.add_parameter('list_step_frequency',
                           label='list_step_frequency',
                           get_cmd=self.do_get_list_step_frequency,
                           get_parser=float,
                           set_cmd=self.do_set_list_step_frequency,
                           set_parser=float,
                           unit='Hz',
                           vals=Numbers(min_value=-20e9, max_value=20e9)
                           )

        self.add_parameter('list_start_power',
                           label='list_start_power',
                           get_cmd=self.do_get_list_start_power,
                           get_parser=float,
                           set_cmd=self.do_set_list_start_power,
                           set_parser=float,
                           unit='dBm',
                           vals=Numbers(min_value=-30, max_value=15)
                           )
        
        self.add_parameter('list_step_power',
                           label='list_step_power',
                           get_cmd=self.do_get_list_step_power,
                           get_parser=float,
                           set_cmd=self.do_set_list_step_power,
                           set_parser=float,
                           unit='dBm',
                           vals=Numbers(min_value=-40, max_value=40)
                           )
        
        self.add_parameter('list_start_dwell',
                           label='list_start_dwell',
                           get_cmd=self.do_get_list_start_dwell,
                           get_parser=float,
                           set_cmd=self.do_set_list_start_dwell,
                           set_parser=float,
                           unit='ms',
                           vals=Numbers(min_value=2, max_value=5000)
                           )
        
        self.add_parameter('list_step_dwell',
                           label='list_step_dwell',
                           get_cmd=self.do_get_list_step_dwell,
                           get_parser=float,
                           set_cmd=self.do_set_list_step_dwell,
                           set_parser=float,
                           unit='ms',
                           vals=Numbers(min_value=-5000, max_value=5000)
                           )

        self.local_list_points_number = self.list_points_number()
        self.local_list_start_frequency = self.list_start_frequency()
        self.local_list_step_frequency = self.list_step_frequency()
        self.local_list_start_dwell = self.list_start_dwell()
        self.local_list_step_dwell = self.list_step_dwell()
        self.local_list_start_power = self.list_start_power()
        self.local_list_step_power = self.list_step_power()

        if self._device_status.operate_status_t.ext_ref_lock_enable == 0:
            self.do_set_reference_source(1)

    @classmethod
    def connected_instruments(cls, max_n_gens: int = 100, sn_len: int = 100) -> List[str]:
        """
        Return the serial numbers of the connected generators.

        The parameters are very unlikely to be needed, and are just for making sure
        we allocated the right amount of memory when calling the SignalCore dll.sc5510b_
        Parameters:
            max_n_gens: maximum number of generators expected
            sn_len: max length of serial numbers.
        """
        
        
        serial_list = (ctypes.c_char_p * 128)()
        for i in range(128):
            serial_list[i] = ctypes.cast(ctypes.create_string_buffer(8), ctypes.c_char_p)

        num_devices = ctypes.c_uint32(99)
        device = serial_list[0]

        
        dll = ctypes.CDLL(cls.dllpath)
        
        search = dll.sc5511b_usb_search_devices

        # # generate and allocate string memory
        # mem_type = (ctypes.c_char_p * max_n_gens)
        # mem = mem_type()
        # for i in range(max_n_gens):
        #     mem[i] = b' ' * sn_len

        search.argtypes = ctypes.POINTER(ctypes.c_char_p), ctypes.POINTER(ctypes.c_uint32)
        search.restype = ctypes.c_long #search returns SCISTATUS which is a long

        status_search = usb_dll.sc5511b_usb_search_devices(serial_list, ctypes.byref(num_devices))
        
        n_gens_found = num_devices.value
        return [sn.decode('utf-8') for sn in serial_list[:n_gens_found]]

    def set_open(self, open) -> bool:
        if open and not self._open:
            
            self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
            self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
            
            
            temp_handle = ctypes.c_void_p()
            
            status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
            if status_open == 0:
                self._open = True
                self._handle = temp_handle
            else:
                raise ValueError('Unable to open SC5511B')
        elif not open and self._open:
            self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
            self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
            self._dll.sc5511b_usb_close_device(self._handle)
        return True

    def soft_trigger(self) -> None:
        """
        Send out a soft trigger, so that the we can start the sweep
        Generator need to be configured for list mode and soft trigger is selected as the trigger source
        """
        logging.info(__name__ + ' : Send a soft trigger to the generator')
        
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
            
            
        self._dll.sc5511b_usb_list_soft_trigger.argtypes = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_list_soft_trigger.restype = ctypes.c_long 
        self._dll.sc5511b_usb_list_soft_trigger(self._handle)
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        return None

    def do_set_output_status(self, enable) -> None:
        """
        Turns the output of RF1 on or off.
            Input:
                enable (int) = OFF = 0 ; ON = 1
        """
        logging.info(__name__ + ' : Setting output to %s' % enable)
        c_enable = ctypes.c_ubyte(enable)
        
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
            
            
        self._dll.sc5511b_usb_set_output.argtypes = ctypes.c_void_p, ctypes.c_uint8 #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_set_output.restype = ctypes.c_long
        completed = self._dll.sc5511b_usb_set_output(self._handle, c_enable)
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        
        return completed

    def do_get_output_status(self) -> int:
        """
        Reads the output status of RF1
            Output:
                status (int) : OFF = 0 ; ON = 1
        """
        logging.info(__name__ + ' : Getting output')
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
            
        self._dll.sc5511b_usb_get_device_status.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_device_status.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_device_status(self._handle, ctypes.byref(self._device_status))
        status = self._device_status.operate_status_t.rf1_out_enable
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        return status

    def do_set_standby(self, standby) -> None:
        """
        Turns the RF1 electronics on or off.
            Input:
                standby (int) = ON = 1 ; OFF = 1
        """
        logging.info(__name__ + ' : Setting standby to %s' % standby)
        c_standby = ctypes.c_uint8(standby)
        
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
            
            
        self._dll.sc5511b_usb_set_standby.argtypes = ctypes.c_void_p, ctypes.c_uint8 #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_set_standby.restype = ctypes.c_long
        completed = self._dll.sc5511b_usb_set_standby(self._handle, c_standby)
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        
        return completed

    def do_get_standby(self) -> int:
        """
        Reads the output status of RF1
            Output:
                standby (int) : OFF = 0 ; ON = 1
        """
        logging.info(__name__ + ' : Getting standby')
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
            
        self._dll.sc5511b_usb_get_device_status.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_device_status.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_device_status(self._handle, ctypes.byref(self._device_status))
        status = self._device_status.operate_status_t.rf1_standby
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        return status

    def do_set_sweep_start_frequency(self, sweep_start_frequency) -> None:
        """
        Set the sweep start frequency of RF1 in the unit of Hz
        """
        c_sweep_start_freq = ctypes.c_double(int(sweep_start_frequency))
        logging.info(__name__ + ' : Setting sweep start frequency to %s' % sweep_start_frequency)
        close = False
        if not self._open:
            self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
            self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
            temp_handle = ctypes.c_void_p()
            status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
            if status_open == 0:
                #self._open = True
                self._handle = temp_handle
            else:
                raise ValueError('Unable to open SC5511B')
                
            close = True
            
        self._dll.sc5511b_usb_list_start_freq.argtypes = ctypes.c_void_p, ctypes.c_double #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_list_start_freq.restype = ctypes.c_long
        if_set = self._dll.sc5511b_usb_list_start_freq(self._handle, c_sweep_start_freq)
        
        if close:
            self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
            self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
            self._dll.sc5511b_usb_close_device(self._handle)
        return if_set

    def do_get_sweep_start_frequency(self) -> float:
        """
        Get the sweep start frequency that is used in the sweep mode
        The frequency returned is in the unit of Hz
        """
        logging.info(__name__ + 'Getting sweep start frequency')
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
        
        self._dll.sc5511b_usb_get_rf_parameters.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_rf_parameters.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_rf_parameters(self._handle, ctypes.byref(self._rf_params))
        sweep_start_frequency = self._rf_params.start_freq
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        return sweep_start_frequency

    def do_set_sweep_stop_frequency(self, sweep_stop_frequency) -> None:
        """
        Set the sweep stop frequency of RF1 in the unit of Hz
        """
        c_sweep_stop_frequency = ctypes.c_double(int(sweep_stop_frequency))
        logging.info(__name__ + ' : Setting sweep stop frequency to %s' % sweep_stop_frequency)
        close = False
        if not self._open:
            self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
            self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
            temp_handle = ctypes.c_void_p()
            status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
            if status_open == 0:
                #self._open = True
                self._handle = temp_handle
            else:
                raise ValueError('Unable to open SC5511B')
            close = True
        
        self._dll.sc5511b_usb_list_stop_freq.argtypes = ctypes.c_void_p, ctypes.c_double #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_list_stop_freq.restype = ctypes.c_long
        if_set = self._dll.sc5511b_usb_list_stop_freq(self._handle, c_sweep_stop_frequency)
        
        if close:
            self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
            self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
            self._dll.sc5511b_usb_close_device(self._handle)
        return if_set

    def do_get_sweep_stop_frequency(self) -> float:
        """
        Get the sweep stop frequency that is used in the sweep mode
        The frequency returned is in the unit of Hz
        """
        logging.info(__name__ + 'Getting sweep stop frequency')
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
        
        self._dll.sc5511b_usb_get_rf_parameters.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_rf_parameters.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_rf_parameters(self._handle, ctypes.byref(self._rf_params))
        
        sweep_stop_frequency = self._rf_params.stop_freq
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        return sweep_stop_frequency

    def do_set_sweep_step_frequency(self, sweep_step_frequency) -> None:
        """
        Set the sweep step frequency of RF1 in the unit of Hz
        """
        c_sweep_step_frequency = ctypes.c_ulonglong(int(sweep_step_frequency))
        logging.info(__name__ + ' : Setting sweep step frequency to %s' % sweep_step_frequency)
        close = False
        if not self._open:
            self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
            self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
            temp_handle = ctypes.c_void_p()
            status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
            if status_open == 0:
                #self._open = True
                self._handle = temp_handle
            else:
                raise ValueError('Unable to open SC5511B')
            
            close = True
                
        self._dll.sc5511b_usb_list_step_freq.argtypes = ctypes.c_void_p, ctypes.c_double #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_list_step_freq.restype = ctypes.c_long
        if_set = self._dll.sc5511b_usb_list_step_freq(self._handle, c_sweep_step_frequency)
        
        if close:
            self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
            self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
            self._dll.sc5511b_usb_close_device(self._handle)
            
        return if_set

    def do_get_sweep_step_frequency(self) -> float:
        """
        Get the sweep step frequency that is used in the sweep mode
        The frequency returned is in the unit of Hz
        """
        logging.info(__name__ + 'Getting sweep step frequency')
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
        
        self._dll.sc5511b_usb_get_rf_parameters.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_rf_parameters.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_rf_parameters(self._handle, ctypes.byref(self._rf_params))
        
        sweep_step_frequency = self._rf_params.step_freq
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        return sweep_step_frequency

    def do_set_sweep_dwell_time(self, sweep_dwell_time) -> None:
        """
        Set the sweep/list time at each frequency point.
        Note that the dwell time is set as multiple of 500 us.
        The input value is an unsigned int, it means how many multiple of 500 us.
        """
        c_sweep_dwell_time = ctypes.c_uint32(int(sweep_dwell_time))
        logging.info(__name__ + ': Setting sweep dwell time to %s' % sweep_dwell_time)
        close = False
        if not self._open:
            self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
            self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
            temp_handle = ctypes.c_void_p()
            status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
            if status_open == 0:
                #self._open = True
                self._handle = temp_handle
            else:
                raise ValueError('Unable to open SC5511B')
            close = True
            
        self._dll.sc5511b_usb_list_step_freq.argtypes = ctypes.c_void_p, ctypes.c_uint32 #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_list_step_freq.restype = ctypes.c_long
        if_set = self._dll.sc5511b_usb_list_dwell_time(self._handle, c_sweep_dwell_time)
        
        if close:
            self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
            self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
            self._dll.sc5511b_usb_close_device(self._handle)
            
        return if_set

    def do_get_sweep_dwell_time(self) -> int:
        """
        Get the dwell time of the sweep mode.
        Return value is the unit multiple of 500 us, e.g. a return value 3 means the dwell time is 1500 us.
        """
        logging.info(__name__ + 'Getting sweep dwell time in the unit of how many multiple of 500 us')
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
        
        self._dll.sc5511b_usb_get_rf_parameters.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_rf_parameters.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_rf_parameters(self._handle, ctypes.byref(self._rf_params))
        
        sweep_dwell_time = self._rf_params.sweep_dwell_time
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        return sweep_dwell_time

    def do_set_sweep_cycles(self, sweep_cycles) -> None:
        """
        Set the number of sweep cycles to perform before stopping.
        To repeat the sweep continuously, set the value to 0.
        """
        c_sweep_cycles = ctypes.c_uint32(int(sweep_cycles))
        logging.info(__name__ + ': Setting sweep cycle number to %s ' % sweep_cycles)
        close = False
        if not self._open:
            self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
            self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
            temp_handle = ctypes.c_void_p()
            status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
            if status_open == 0:
                #self._open = True
                self._handle = temp_handle
            else:
                raise ValueError('Unable to open SC5511B')
            close = True
        self._dll.sc5511b_usb_list_cycle_count.argtypes = ctypes.c_void_p, ctypes.c_uint32 #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_list_cycle_count.restype = ctypes.c_long
        if_set = self._dll.sc5511b_usb_list_cycle_count(self._handle, c_sweep_cycles)
        
        if close:
            self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
            self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
            self._dll.sc5511b_usb_close_device(self._handle)
            
        return if_set

    def do_get_sweep_cycles(self) -> int:
        """
        Get the number of sweep cycles to perform before stopping.
        To repeat the sweep continuously, the value is 0.
        """
        logging.info(__name__ + 'Getting number of sweep cycles')
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
        
        self._dll.sc5511b_usb_get_rf_parameters.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_rf_parameters.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_rf_parameters(self._handle, ctypes.byref(self._rf_params))
        
        sweep_cycles = self._rf_params.sweep_cycles
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        return sweep_cycles

    def do_set_trig_out_enable(self, trig_out_enable) -> None:
        """
        Set the trigger output status.
        It does not send out the trigger, just enable the generator to send out the trigger
        0 = No trigger output
        1 = Puts a trigger pulse on the TRIGOUT pin
        """
        c_trig_out_enable = ctypes.c_ubyte(int(trig_out_enable))
        logging.info(__name__ + ': Setting sweep cycle number to %s ' % trig_out_enable)
        close = False
        if not self._open:
            self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
            self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
            temp_handle = ctypes.c_void_p()
            status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
            if status_open == 0:
                #self._open = True
                self._handle = temp_handle
            else:
                raise ValueError('Unable to open SC5511B')
                
            close = True
        
        self._dll.sc5511b_usb_get_device_status.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_device_status.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_device_status(self._handle, ctypes.byref(self._device_status))
        
        self._device_status.list_mode.trig_out_enable = c_trig_out_enable
        
        self._dll.sc5511b_usb_list_mode_config.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_list_mode_config.restype = ctypes.c_long
        if_set = self._dll.sc5511b_usb_list_mode_config(self._handle, ctypes.byref(self._device_status.list_mode))

        if close:
            self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
            self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
            self._dll.sc5511b_usb_close_device(self._handle)
            
        return if_set

    def do_get_trig_out_enable(self) -> int:
        """
        Get the status of the trigger output status
        0 = No trigger output
        1 = Puts a trigger pulse on the TRIGOUT pin
        """
        logging.info(__name__ + 'Getting trigger output status')
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
            
        self._dll.sc5511b_usb_get_device_status.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_device_status.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_device_status(self._handle, ctypes.byref(self._device_status))
        
        trig_out_enable = self._device_status.list_mode.trig_out_enable
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        
        return trig_out_enable

    def do_set_trig_out_on_cycle(self, trig_out_on_cycle) -> None:
        """
        Set the trigger output mode
        0 = Puts out a trigger pulse at each frequency change
        1 = Puts out a trigger pulse at the completion of each sweep/list cycle
        """
        c_trig_out_on_cycle = ctypes.c_ubyte(int(trig_out_on_cycle))
        logging.info(__name__ + ': Setting sweep cycle number to %s ' % trig_out_on_cycle)
        close = False
        if not self._open:
            self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
            self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
            temp_handle = ctypes.c_void_p()
            status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
            if status_open == 0:
                #self._open = True
                self._handle = temp_handle
            else:
                raise ValueError('Unable to open SC5511B')
                
            close = True

        self._dll.sc5511b_usb_get_device_status.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_device_status.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_device_status(self._handle, ctypes.byref(self._device_status))
        
        self._device_status.list_mode.trig_out_on_cycle = c_trig_out_on_cycle
        
        self._dll.sc5511b_usb_list_mode_config.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_list_mode_config.restype = ctypes.c_long
        if_set = self._dll.sc5511b_usb_list_mode_config(self._handle, ctypes.byref(self._device_status.list_mode))

        if close:
            self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
            self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
            self._dll.sc5511b_usb_close_device(self._handle)
            
        return if_set

    def do_get_trig_out_on_cycle(self) -> int:
        """
        Get the trigger output mode
        0 = Puts out a trigger pulse at each frequency change
        1 = Puts out a trigger pulse at the completion of each sweep/list cycle
        """
        logging.info(__name__ + 'Getting trigger output mode ')
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
            
        self._dll.sc5511b_usb_get_device_status.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_device_status.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_device_status(self._handle, ctypes.byref(self._device_status))
        
        trig_out_enable = self._device_status.list_mode.trig_out_on_cycle
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        
        return trig_out_enable

    def do_set_step_on_hw_trig(self, step_on_hw_trig) -> None:
        """
        Set the behavior of the sweep/list mode when receiving a trigger.
        0 = Start/Stop behavior. The sweep starts and continues to step through the list for the number of cycles set,
            dwelling at each step frequency for a period set by the dwell time. The sweep/list will end on a consecutive
            trigger.
        1 = Step-on-trigger. This is only available if hardware triggering is selected. The device will step to the next
            frequency on a trigger.Upon completion of the number of cycles, the device will exit from the stepping state
            and stop.
        """
        c_step_on_hw_trig = ctypes.c_ubyte(int(step_on_hw_trig))
        logging.info(__name__ + ': Setting sweep cycle number to %s ' % step_on_hw_trig)
        close = False
        if not self._open:
            self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
            self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
            temp_handle = ctypes.c_void_p()
            status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
            if status_open == 0:
                #self._open = True
                self._handle = temp_handle
            else:
                raise ValueError('Unable to open SC5511B')
                
            close = True

        self._dll.sc5511b_usb_get_device_status.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_device_status.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_device_status(self._handle, ctypes.byref(self._device_status))
        
        
        self._device_status.list_mode.step_on_hw_trig = c_step_on_hw_trig
        
        self._dll.sc5511b_usb_list_mode_config.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_list_mode_config.restype = ctypes.c_long 
        if_set = self._dll.sc5511b_usb_list_mode_config(self._handle, ctypes.byref(self._device_status.list_mode))

        if close:
            self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
            self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
            self._dll.sc5511b_usb_close_device(self._handle)
            
        return if_set

    def do_get_step_on_hw_trig(self) -> int:
        """
        Set the behavior of the sweep/list mode when receiving a trigger.
        0 = Start/Stop behavior
        1 = Step-on-trigger
        """
        logging.info(__name__ + 'Getting status of step on trigger mode ')
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
            
        self._dll.sc5511b_usb_get_device_status.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_device_status.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_device_status(self._handle, ctypes.byref(self._device_status))
        
        step_on_hw_trig = self._device_status.list_mode.step_on_hw_trig
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        return step_on_hw_trig

    def do_set_return_to_start(self, return_to_start) -> None:
        """
        Set how the frequency will change at the end of the list/sweep
        0 = Stop at end of sweep/list. The frequency will stop at the last point of the sweep/list
        1 = Return to start. The frequency will return and stop at the beginning point of the sweep or list after a
            cycle.
        """
        c_return_to_start = ctypes.c_ubyte(int(return_to_start))
        logging.info(__name__ + ': Setting sweep cycle number to %s ' % return_to_start)
        close = False
        if not self._open:
            self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
            self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
            temp_handle = ctypes.c_void_p()
            status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
            if status_open == 0:
                #self._open = True
                self._handle = temp_handle
            else:
                raise ValueError('Unable to open SC5511B')
                
            close = True

        self._dll.sc5511b_usb_get_device_status.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_device_status.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_device_status(self._handle, ctypes.byref(self._device_status))
        
        self._device_status.list_mode.return_to_start = c_return_to_start
        
        self._dll.sc5511b_usb_list_mode_config.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_list_mode_config.restype = ctypes.c_long
        if_set = self._dll.sc5511b_usb_list_mode_config(self._handle, ctypes.byref(self._device_status.list_mode))

        if close:
            self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
            self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
            self._dll.sc5511b_usb_close_device(self._handle)
            
        return if_set

    def do_get_return_to_start(self) -> int:
        """
        Get the status of how the frequency will change at the end of the list/sweep
        0 = Stop at end of sweep/list. The frequency will stop at the last point of the sweep/list
        1 = Return to start. The frequency will return and stop at the beginning point of the sweep or list after a
            cycle.
        """
        logging.info(__name__ + 'Getting status of return to start ')
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
            
        self._dll.sc5511b_usb_get_device_status.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_device_status.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_device_status(self._handle, ctypes.byref(self._device_status))
        
        return_to_start = self._device_status.list_mode.return_to_start
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        
        return return_to_start

    def do_set_hw_trig(self, hw_trigger) -> None:
        """
        Set the status of hardware trigger
        0 = Software trigger. Softtrigger can only be used to start and stop a sweep/list cycle. It does not work for
            step-on-trigger mode.
        1 = Hardware trigger. A high-to-low transition on the TRIGIN pin will trigger the device. It can be used for
            both start/stop or step-on-trigger functions.
        """
        c_hw_trigger = ctypes.c_ubyte(int(hw_trigger))
        logging.info(__name__ + ': Setting sweep cycle number to %s ' % hw_trigger)
        close = False
        if not self._open:
            self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
            self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
            temp_handle = ctypes.c_void_p()
            status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
            if status_open == 0:
                #self._open = True
                self._handle = temp_handle
            else:
                raise ValueError('Unable to open SC5511B')
                
            close = True

        self._dll.sc5511b_usb_get_device_status.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_device_status.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_device_status(self._handle, ctypes.byref(self._device_status))
        
        self._device_status.list_mode.hw_trigger = c_hw_trigger
        
        self._dll.sc5511b_usb_list_mode_config.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_list_mode_config.restype = ctypes.c_long
        if_set = self._dll.sc5511b_usb_list_mode_config(self._handle, ctypes.byref(self._device_status.list_mode))

        if close:
            self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
            self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
            self._dll.sc5511b_usb_close_device(self._handle)
            
        return if_set

    def do_get_hw_trig(self) -> int:
        """
        Get the status of hardware trigger
        0 = Software trigger. Softtrigger can only be used to start and stop a sweep/list cycle. It does not work for
            step-on-trigger mode.
        1 = Hardware trigger. A high-to-low transition on the TRIGIN pin will trigger the device. It can be used for
            both start/stop or step-on-trigger functions.
        """
        logging.info(__name__ + 'Getting status of hardware trigger ')
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
            
        self._dll.sc5511b_usb_get_device_status.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_device_status.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_device_status(self._handle, ctypes.byref(self._device_status))
        
        hw_trigger = self._device_status.list_mode.hw_trigger
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        return hw_trigger

    def do_set_tri_waveform(self, tri_waveform) -> None:
        """
        Set the triangular waveform of the generator
        0 = Sawtooth waveform. Frequency returns to the beginning frequency upon reaching the end of a sweep cycle
        1 = Triangular waveform. Frequency reverses direction at the end of the list and steps back towards the
            beginning to complete a cycle
        """
        c_tri_waveform = ctypes.c_ubyte(int(tri_waveform))
        logging.info(__name__ + ': Setting sweep cycle number to %s ' % tri_waveform)
        close = False
        if not self._open:
            self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
            self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
            temp_handle = ctypes.c_void_p()
            status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
            if status_open == 0:
                #self._open = True
                self._handle = temp_handle
            else:
                raise ValueError('Unable to open SC5511B')
                
            close = True

        self._dll.sc5511b_usb_get_device_status.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_device_status.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_device_status(self._handle, ctypes.byref(self._device_status))
        
        self._device_status.list_mode.tri_waveform = c_tri_waveform
        
        self._dll.sc5511b_usb_list_mode_config.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_list_mode_config.restype = ctypes.c_long
        if_set = self._dll.sc5511b_usb_list_mode_config(self._handle, ctypes.byref(self._device_status.list_mode))

        if close:
            self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
            self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
            self._dll.sc5511b_usb_close_device(self._handle)
            
        return if_set

    def do_get_tri_waveform(self) -> int:
        """
        Get the triangular waveform of the generator
        0 = Sawtooth waveform. Frequency returns to the beginning frequency upon reaching the end of a sweep cycle
        1 = Triangular waveform. Frequency reverses direction at the end of the list and steps back towards the
            beginning to complete a cycle
        """
        logging.info(__name__ + 'Getting status of triangular waveform ')
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
            
        self._dll.sc5511b_usb_get_device_status.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_device_status.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_device_status(self._handle, ctypes.byref(self._device_status))
        
        hw_trigger = self._device_status.list_mode.tri_waveform
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        
        return hw_trigger

    def do_set_sweep_dir(self, sweep_dir) -> None:
        """
        Set the sweep direction of the generator
        0 = Forward. Sweeps start from the lowest start frequency or starts at the beginning of the list buffer
        1 = Reverse. Sweeps start from the stop frequency and steps down toward the start frequency or starts at the
            end and steps toward the beginning of the buffer
        """
        c_sweep_dir = ctypes.c_ubyte(int(sweep_dir))
        logging.info(__name__ + ': Setting sweep cycle number to %s ' % sweep_dir)
        close = False
        if not self._open:
            self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
            self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
            temp_handle = ctypes.c_void_p()
            status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
            if status_open == 0:
                #self._open = True
                self._handle = temp_handle
            else:
                raise ValueError('Unable to open SC5511B')
                
            close = True

        self._dll.sc5511b_usb_get_device_status.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_device_status.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_device_status(self._handle, ctypes.byref(self._device_status))
        
        self._device_status.list_mode.sweep_dir = c_sweep_dir
        
        self._dll.sc5511b_usb_list_mode_config.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_list_mode_config.restype = ctypes.c_long
        if_set = self._dll.sc5511b_usb_list_mode_config(self._handle, ctypes.byref(self._device_status.list_mode))

        if close:
            self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
            self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
            self._dll.sc5511b_usb_close_device(self._handle)
            
        return if_set

    def do_get_sweep_dir(self) -> int:
        """
        Get the sweep direction of the generator
        0 = Forward. Sweeps start from the lowest start frequency or starts at the beginning of the list buffer
        1 = Reverse. Sweeps start from the stop frequency and steps down toward the start frequency or starts at the
            end and steps toward the beginning of the buffer
        """
        logging.info(__name__ + 'Getting status of sweep direction ')
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
            
        self._dll.sc5511b_usb_get_device_status.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_device_status.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_device_status(self._handle, ctypes.byref(self._device_status))
        
        hw_trigger = self._device_status.list_mode.sweep_dir
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        return hw_trigger

    def do_set_sss_mode(self, sss_mode) -> None:
        """
        Set the list/sweep mode of the generator
        0 = List mode. Device gets its frequency points from the list buffer uploaded via LIST_BUFFER_WRITE register
        1 = Sweep mode. The device computes the frequency points using the Start, Stop and Step frequencies
        """
        c_sss_mode = ctypes.c_ubyte(int(sss_mode))
        logging.info(__name__ + ': Setting sweep cycle number to %s ' % sss_mode)
        close = False
        if not self._open:
            self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
            self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
            temp_handle = ctypes.c_void_p()
            status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
            if status_open == 0:
                #self._open = True
                self._handle = temp_handle
            else:
                raise ValueError('Unable to open SC5511B')
                
            close = True

        self._dll.sc5511b_usb_get_device_status.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_device_status.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_device_status(self._handle, ctypes.byref(self._device_status))
        
        self._device_status.list_mode.sss_mode = c_sss_mode
        
        self._dll.sc5511b_usb_list_mode_config.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_list_mode_config.restype = ctypes.c_long
        if_set = self._dll.sc5511b_usb_list_mode_config(self._handle, ctypes.byref(self._device_status.list_mode))

        if close:
            self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
            self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
            self._dll.sc5511b_usb_close_device(self._handle)
            
        return if_set

    def do_get_sss_mode(self) -> int:
        """
        Get the list/sweep mode of the generator
        0 = List mode. Device gets its frequency points from the list buffer uploaded via LIST_BUFFER_WRITE register
        1 = Sweep mode. The device computes the frequency points using the Start, Stop and Step frequencies
        """
        logging.info(__name__ + 'Getting status of sss mode')
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
            
        self._dll.sc5511b_usb_get_device_status.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_device_status.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_device_status(self._handle, ctypes.byref(self._device_status))
        
        sss_mode = self._device_status.list_mode.sss_mode
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        return sss_mode

    def do_set_rf1_mode(self, rf1_mode) -> None:
        """
        Set the RF mode for rf1
        0 = single fixed tone mode
        1 = sweep/list mode
        """
        c_rf1_mode = ctypes.c_uint8(rf1_mode)
        logging.info(__name__ + ' : Setting frequency to %s' % rf1_mode)
        close = False
        if not self._open:
            self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
            self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
            temp_handle = ctypes.c_void_p()
            status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
            if status_open == 0:
                #self._open = True
                self._handle = temp_handle
            else:
                raise ValueError('Unable to open SC5511B')
                
            close = True
            
        self._dll.sc5511b_usb_set_rf_mode.argtypes = ctypes.c_void_p, ctypes.c_uint8 #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_set_rf_mode.restype = ctypes.c_long
        if_set = self._dll.sc5511b_usb_set_rf_mode(self._handle, c_rf1_mode)
        
        if close:
            self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
            self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
            self._dll.sc5511b_usb_close_device(self._handle)
            
        return if_set

    def do_get_rf1_mode(self) -> int:
        """
        Get the RF mode for rf1
        0 = single fixed tone mode
        1 = sweep/list mode
        """
        logging.info(__name__ + 'Getting the RF mode for rf1')
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
            
        self._dll.sc5511b_usb_get_device_status.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_device_status.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_device_status(self._handle, ctypes.byref(self._device_status))
        
        rf1_mode = self._device_status.operate_status_t.rf1_mode
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        return rf1_mode

    def do_set_frequency(self, frequency) -> None:
        """
        Sets RF1 frequency in the unit of Hz. Valid between 100MHz and 20GHz
            Args:
                frequency (int) = frequency in Hz
        """
        c_freq = ctypes.c_double(int(frequency))
        logging.info(__name__ + ' : Setting frequency to %s' % frequency)
        close = False
        if not self._open:
            self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
            self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
            temp_handle = ctypes.c_void_p()
            status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
            if status_open == 0:
                #self._open = True
                self._handle = temp_handle
            else:
                raise ValueError('Unable to open SC5511B')
                
            close = True
            
        self._dll.sc5511b_usb_set_freq.argtypes = ctypes.c_void_p, ctypes.c_double #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_set_freq.restype = ctypes.c_long
        if_set = self._dll.sc5511b_usb_set_freq(self._handle, c_freq)
        
        if close:
            self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
            self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
            self._dll.sc5511b_usb_close_device(self._handle)
            
        return if_set

    def do_get_frequency(self) -> float:
        """
        Gets RF1 frequency in the unit of Hz.
        """
        logging.info(__name__ + ' : Getting frequency')
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
            
        self._dll.sc5511b_usb_get_rf_parameters.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_rf_parameters.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_rf_parameters(self._handle, ctypes.byref(self._rf_params))
        
        frequency = self._rf_params.rf1_freq
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        
        return frequency

    def do_set_reference_source(self, lock_to_external) -> None:
        """
        Set the generator reference source
        0 = internal source
        1 = external source

        Note here high is set to 0, means we always use 10 MHz clock when use external lock
        """
        logging.info(__name__ + ' : Setting reference source to %s' % lock_to_external)
        high = ctypes.c_uint8(0)
        lock = ctypes.c_uint8(lock_to_external)
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
        
        self._dll.sc5511b_usb_set_clock_reference.argtypes = ctypes.c_void_p, ctypes.c_uint8, ctypes.c_uint8 #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_set_clock_reference.restype = ctypes.c_long
        source = self._dll.sc5511b_usb_set_clock_reference(self._handle, high, lock)
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        
        return source

    def do_get_reference_source(self) -> int:
        """
        Get the generator reference source
        0 = internal source
        1 = external source
        """
        logging.info(__name__ + ' : Getting reference source')
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
            
        enabled = self._device_status.operate_status_t.ext_ref_lock_enable
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        
        return enabled

    def do_set_power(self, power) -> None:
        """
        Set the power of the generator in the unit of dBm
        """
        logging.info(__name__ + ' : Setting power to %s' % power)
        c_power = ctypes.c_float(power)
        close = False
        if not self._open:
            self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
            self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
            temp_handle = ctypes.c_void_p()
            status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
            if status_open == 0:
                #self._open = True
                self._handle = temp_handle
            else:
                raise ValueError('Unable to open SC5511B')
                
            close = True
            
            
        self._dll.sc5511b_usb_set_level.argtypes = ctypes.c_void_p, ctypes.c_float #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_set_level.restype = ctypes.c_long
        completed = self._dll.sc5511b_usb_set_level(self._handle, c_power)
        
        if close:
            self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
            self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
            self._dll.sc5511b_usb_close_device(self._handle)
            
        return completed

    def do_get_power(self) -> float:
        """
        Get the power of the generator in the unit of dBm
        """
        logging.info(__name__ + ' : Getting Power')
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
            
        self._dll.sc5511b_usb_get_rf_parameters.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_rf_parameters.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_rf_parameters(self._handle, ctypes.byref(self._rf_params))
        
        rf_level = self._rf_params.rf_level
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        
        return rf_level

    def do_set_auto_level_disable(self, enable) -> None:
        """
        Set if we want to disable the auto level
        """
        logging.info(__name__ + ' : Settingalc auto to %s' % enable)
        if enable == 1:
            enable = 0
        elif enable == 0:
            enable = 1
        c_enable = ctypes.c_uint8(enable)
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
        
        self._dll.sc5511b_usb_set_auto_level_disable.argtypes = ctypes.c_void_p, ctypes.c_uint8 #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_set_auto_level_disable.restype = ctypes.c_long
        completed = self._dll.sc5511b_usb_set_auto_level_disable(self._handle, c_enable)
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        
        return completed

    def do_get_auto_level_disable(self) -> int:
        """
        Get if we disable to auto level
        """
        logging.info(__name__ + ' : Getting alc auto status')
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
            
        self._dll.sc5511b_usb_get_device_status.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_device_status.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_device_status(self._handle, ctypes.byref(self._device_status))
        
        enabled = self._device_status.operate_status_t.auto_pwr_disable
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        
        if enabled == 1:
            enabled = 0
        elif enabled == 0:
            enabled = 1
        return enabled

    def do_get_device_temp(self)  -> float:
        """
        Get the device temperature in unit of C
        """
        logging.info(__name__ + " : Getting device temperature")
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
        
        self._dll.sc5511b_usb_get_device_status.argtypes = ctypes.c_void_p, ctypes.POINTER(ctypes.c_float) #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_device_status.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_temperature(self._handle, ctypes.byref(self._temperature))
        
        device_temp = self._temperature.device_temp
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        
        return device_temp

    def get_idn(self) -> Dict[str, Optional[str]]:
        """
        Get the identification information of the current device
        """
        logging.info(__name__ + " : Getting device info")
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
            
        self._dll.sc5511b_usb_get_device_info.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_device_info.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_device_info(self._handle, ctypes.byref(self._device_info))
        
        device_info = self._device_info
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        
        def date_decode(date_int: int):
            date_str = f"{date_int:032b}"
            yr = f"20{int(date_str[:8], 2)}"
            month = f"{int(date_str[16:24], 2)}"
            day = f"{int(date_str[8:16], 2)}"
            return f"{month}/{day}/{yr}"

        IDN: Dict[str, Optional[str]] = {
            'vendor': "SignalCore",
            'model': "SC5511B",
            'serial_number': self._serial_number.value.decode("utf-8"),
            'firmware_revision': device_info.firmware_revision,
            'hardware_revision': device_info.hardware_revision,
            'manufacture_date': date_decode(device_info.manufacture_date)
        }
        return IDN

    def do_get_list_points_number(self) -> int:
        logging.info(__name__ + " : Getting list points number")
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
        
        self._dll.sc5511b_usb_get_rf_parameters.argtypes = ctypes.c_void_p, ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_get_rf_parameters.restype = ctypes.c_long
        self._dll.sc5511b_usb_get_rf_parameters(self._handle, ctypes.byref(self._rf_params))
        
        list_points_number = self._rf_params.buffer_points
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        
        return list_points_number
       
    def do_set_list_points_number(self, points) -> None:
        logging.info(__name__ + " : Setting list points number")
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
                
        self._dll.sc5511b_usb_list_buffer_points.argtypes = ctypes.c_void_p, ctypes.c_uint32 #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_list_buffer_points.restype = ctypes.c_long
        updated = self._dll.sc5511b_usb_list_buffer_points(self._handle, ctypes.c_uint32(points))
        
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        
        self.local_list_points_number = points
        
        self.update_list()
        
        return updated
        
    def do_get_list_start_frequency(self) -> int:
        logging.info(__name__ + " : Getting list start frequency")
        points = self.list_points_number()
        
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
        
        
        c_points = ctypes.c_uint32(points)
        c_freqs = (ctypes.c_double * points)()
        c_dwells = (ctypes.c_float * points)()
        c_powers = (ctypes.c_float * points)()
        
        freq_pointer = ctypes.cast(c_freqs, ctypes.POINTER(ctypes.c_double))
        dwells_pointer = ctypes.cast(c_dwells, ctypes.POINTER(ctypes.c_float))
        powers_pointer = ctypes.cast(c_powers, ctypes.POINTER(ctypes.c_float))
        
        self._dll.sc5511b_usb_list_buffer_read.argtypes = ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float)
        self._dll.sc5511b_usb_list_buffer_read.restype = ctypes.c_long
        self._dll.sc5511b_usb_list_buffer_read(self._handle, c_points, freq_pointer, 
                                           powers_pointer, dwells_pointer)
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        
        
        return c_freqs[0]
       
    def do_set_list_start_frequency(self, start_freq) -> None:
        logging.info(__name__ + " : Setting list start frequency")
        self.local_list_start_frequency = start_freq
        updated = self.update_list()
        
        return updated

    def do_get_list_step_frequency(self) -> int:
        logging.info(__name__ + " : Getting list step frequency")
        points = self.list_points_number()
        if points < 2:
            return 0
        
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
        
        
        c_points = ctypes.c_uint32(points)
        c_freqs = (ctypes.c_double * points)()
        c_dwells = (ctypes.c_float * points)()
        c_powers = (ctypes.c_float * points)()
        
        freq_pointer = ctypes.cast(c_freqs, ctypes.POINTER(ctypes.c_double))
        dwells_pointer = ctypes.cast(c_dwells, ctypes.POINTER(ctypes.c_float))
        powers_pointer = ctypes.cast(c_powers, ctypes.POINTER(ctypes.c_float))
        
        self._dll.sc5511b_usb_list_buffer_read.argtypes = ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float)
        self._dll.sc5511b_usb_list_buffer_read.restype = ctypes.c_long
        self._dll.sc5511b_usb_list_buffer_read(self._handle, c_points, freq_pointer, 
                                           powers_pointer, dwells_pointer)
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        
        
        return c_freqs[1] - c_freqs[0]
       
    def do_set_list_step_frequency(self, step_freq) -> None:
        logging.info(__name__ + " : Setting list step frequency")
        self.local_list_step_frequency = step_freq
        updated = self.update_list()
        
        return updated    
 
    
    def do_get_list_start_power(self) -> int:
        logging.info(__name__ + " : Getting list start power")
        points = self.list_points_number()
        
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
        
        
        c_points = ctypes.c_uint32(points)
        c_freqs = (ctypes.c_double * points)()
        c_dwells = (ctypes.c_float * points)()
        c_powers = (ctypes.c_float * points)()
        
        freq_pointer = ctypes.cast(c_freqs, ctypes.POINTER(ctypes.c_double))
        dwells_pointer = ctypes.cast(c_dwells, ctypes.POINTER(ctypes.c_float))
        powers_pointer = ctypes.cast(c_powers, ctypes.POINTER(ctypes.c_float))
        
        self._dll.sc5511b_usb_list_buffer_read.argtypes = ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float)
        self._dll.sc5511b_usb_list_buffer_read.restype = ctypes.c_long
        self._dll.sc5511b_usb_list_buffer_read(self._handle, c_points, freq_pointer, 
                                           powers_pointer, dwells_pointer)
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        
        
        return c_powers[0]
       
    def do_set_list_start_power(self, start_power) -> None:
        logging.info(__name__ + " : Setting list start power")
        self.local_list_start_power = start_power
        updated = self.update_list()
        
        return updated

    def do_get_list_step_power(self) -> int:
        logging.info(__name__ + " : Getting list step power")
        points = self.list_points_number()
        if points < 2:
            return 0
        
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
        
        
        c_points = ctypes.c_uint32(points)
        c_freqs = (ctypes.c_double * points)()
        c_dwells = (ctypes.c_float * points)()
        c_powers = (ctypes.c_float * points)()
        
        freq_pointer = ctypes.cast(c_freqs, ctypes.POINTER(ctypes.c_double))
        dwells_pointer = ctypes.cast(c_dwells, ctypes.POINTER(ctypes.c_float))
        powers_pointer = ctypes.cast(c_powers, ctypes.POINTER(ctypes.c_float))
        
        self._dll.sc5511b_usb_list_buffer_read.argtypes = ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float)
        self._dll.sc5511b_usb_list_buffer_read.restype = ctypes.c_long
        self._dll.sc5511b_usb_list_buffer_read(self._handle, c_points, freq_pointer, 
                                           powers_pointer, dwells_pointer)
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        
        
        return c_powers[1] - c_powers[0]
       
    def do_set_list_step_power(self, step_power) -> None:
        logging.info(__name__ + " : Setting list step power")
        self.local_list_step_power = step_power
        updated = self.update_list()
        
        return updated
    
    def do_get_list_start_dwell(self) -> int:
        logging.info(__name__ + " : Getting list start dwell")
        points = self.list_points_number()
        
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
        
        
        c_points = ctypes.c_uint32(points)
        c_freqs = (ctypes.c_double * points)()
        c_dwells = (ctypes.c_float * points)()
        c_powers = (ctypes.c_float * points)()
        
        freq_pointer = ctypes.cast(c_freqs, ctypes.POINTER(ctypes.c_double))
        dwells_pointer = ctypes.cast(c_dwells, ctypes.POINTER(ctypes.c_float))
        powers_pointer = ctypes.cast(c_powers, ctypes.POINTER(ctypes.c_float))
        
        self._dll.sc5511b_usb_list_buffer_read.argtypes = ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float)
        self._dll.sc5511b_usb_list_buffer_read.restype = ctypes.c_long
        self._dll.sc5511b_usb_list_buffer_read(self._handle, c_points, freq_pointer, 
                                           powers_pointer, dwells_pointer)
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        
        
        return c_dwells[0]
       
    def do_set_list_start_dwell(self, start_dwell) -> None:
        logging.info(__name__ + " : Setting list start dwell")
        self.local_list_start_dwell = start_dwell
        updated = self.update_list()
        
        return updated

    def do_get_list_step_dwell(self) -> int:
        logging.info(__name__ + " : Getting list step dwell")
        points = self.list_points_number()
        if points < 2:
            return 0
        
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
        
        
        c_points = ctypes.c_uint32(points)
        c_freqs = (ctypes.c_double * points)()
        c_dwells = (ctypes.c_float * points)()
        c_powers = (ctypes.c_float * points)()
        
        freq_pointer = ctypes.cast(c_freqs, ctypes.POINTER(ctypes.c_double))
        dwells_pointer = ctypes.cast(c_dwells, ctypes.POINTER(ctypes.c_float))
        powers_pointer = ctypes.cast(c_powers, ctypes.POINTER(ctypes.c_float))
        
        self._dll.sc5511b_usb_list_buffer_read.argtypes = ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float)
        self._dll.sc5511b_usb_list_buffer_read.restype = ctypes.c_long
        self._dll.sc5511b_usb_list_buffer_read(self._handle, c_points, freq_pointer, 
                                           powers_pointer, dwells_pointer)
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        
        
        return c_dwells[1] - c_dwells[0]
       
    def do_set_list_step_dwell(self, step_dwell) -> None:
        logging.info(__name__ + " : Setting list step dwell")
        self.local_list_step_dwell = step_dwell
        updated = self.update_list()
        
        return updated  
    
    
    def update_list(self) -> None:
        logging.info(__name__ + " : Updating list")
        
        points = self.local_list_points_number
        start_freq = self.local_list_start_frequency
        step_freq = self.local_list_step_frequency
        start_dwell = self.local_list_start_dwell
        step_dwell = self.local_list_step_dwell
        start_power = self.local_list_start_power
        step_power = self.local_list_step_power
        
        frequencies = np.linspace(start_freq, 
                                start_freq + (points-1)*step_freq, 
                                points)
        
        dwells = np.linspace(start_dwell, 
                                start_dwell + (points-1)*step_dwell, 
                                points)
        
        powers = np.linspace(start_power, 
                                start_power + (points-1)*step_power, 
                                points)
        
        
        c_freqs = (ctypes.c_double * points)()
        c_dwells = (ctypes.c_float * points)()
        c_powers = (ctypes.c_float * points)()
        for i in range(points):
            c_freqs[i] = frequencies[i]
            c_dwells[i] = dwells[i]
            c_powers[i] = powers[i]
            
        freq_pointer = ctypes.cast(c_freqs, ctypes.POINTER(ctypes.c_double))
        dwells_pointer = ctypes.cast(c_dwells, ctypes.POINTER(ctypes.c_float))
        powers_pointer = ctypes.cast(c_powers, ctypes.POINTER(ctypes.c_float))
        
        
        self.rf1_mode(0) #support says you have to do this before setting up a list
        
        self._dll.sc5511b_usb_open_device.argtypes = ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
        self._dll.sc5511b_usb_open_device.restype = ctypes.c_uint64
        temp_handle = ctypes.c_void_p()
        status_open = self._dll.sc5511b_usb_open_device(self._serial_number, ctypes.byref(temp_handle))
        if status_open == 0:
            #self._open = True
            self._handle = temp_handle
        else:
            raise ValueError('Unable to open SC5511B')
        
        self._dll.sc5511b_usb_list_buffer_write.argtypes = ctypes.c_void_p, ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float), ctypes.c_uint32 #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_list_buffer_write.restype = ctypes.c_long
        self._dll.sc5511b_usb_list_buffer_write(self._handle, freq_pointer, 
                                                powers_pointer, dwells_pointer, 
                                                ctypes.c_uint32(points))
        
        
        #push buffer to RAM
        self._dll.sc5511b_usb_list_buffer_transfer.argtype = ctypes.c_void_p, ctypes.c_uint8 #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_list_buffer_transfer.restype = ctypes.c_long 
        transferred = self._dll.sc5511b_usb_list_buffer_transfer(self._handle, ctypes.c_uint8(0)) #thought it was 1 but this works
        
        self._dll.sc5511b_usb_close_device.argtype = ctypes.c_void_p #not sure of the type for dev status pointer
        self._dll.sc5511b_usb_close_device.restype = ctypes.c_long 
        self._dll.sc5511b_usb_close_device(self._handle)
        
        return transferred
        

# get_cmd=self.do_get_list_start_power,
# set_cmd=self.do_set_list_start_power,

# get_cmd=self.do_get_list_step_power,
# set_cmd=self.do_set_list_step_power,

# get_cmd=self.do_get_list_start_dwell,
# set_cmd=self.do_set_list_start_dwell,

# get_cmd=self.do_get_list_step_dwell,
# set_cmd=self.do_set_list_step_dwell,
