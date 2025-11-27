# -*- coding: utf-8 -*-
"""QCoDeS Driver for Quantum Design Opticool Magnet Optical Cryostat.
Requires MultiPyVu installed for client-server communication.
Tested on a system with 7T bore magnet.
https://qdusa.com/products/opticool.html

Authors:
    Julien Barrier, <julien@julienbarrier.eu>
"""

import logging
from typing import Optional, Any
import MultiPyVu as mpv

from qcodes.instrument.base import Instrument
from qcodes.parameters import Parameter
from qcodes import validators as vals

log = logging.getLogger(__name__)


class Opticool(Instrument):
    """
    Class to represent an Opticool cryostat.

    Args:
        name (str): name for the instrument
        address (str): IP address of the MultiPyVu server instance
        port (int): port to connect IP. Defaults to 5000
        
    Status: work-in-progress
    
    Todo:
        write down all the _functions and test driver
        check parsing
        check val_mapping
        try to write more _set functions
    """

    def __init__(
            self,
            name: str,
            address: str,
            port: Optional[int] = 5000,
            **kwargs: Any) -> None:
        super().__init__(name, **kwargs)
        self.client = mpv.Client(host=address, port=port)
        
        self.temperature_shield = Parameter(
            name='temperature_shield',
            label='Shield temperature',
            unit='K',
            get_cmd=self._get_temperature_shield,
            get_parser=float,
            instrument=self
        )
        
        self.temperature_4k_plate = Parameter(
            name='temperature_4k_plate',
            label='4K plate temperature',
            unit='K',
            get_cmd=self._get_temperature_4k_plate,
            get_parser=float,
            instrument=self
        )
        
        self.temperature_magnet = Parameter(
            name='temperature_magnet',
            label='Magnet temperature',
            unit='K',
            get_cmd=self._get_temperature_magnet,
            get_parser=float,
            instrument=self
        )
        
        self.temperature_sample = Parameter(
            name='temperature_sample',
            label='Sample temperature',
            unit='K',
            get_cmd=self._get_temperature_sample,
            get_parser=float,
            set_cmd=self._set_temperature_sample,
            vals=vals.Numbers(1.4, 350),
            instrument=self
        )
        
        self.temperature_ramp_method = Parameter(
            name='temperature_ramp_method',
            label='Ramp method for the sample stage temperature',
            get_cmd=self._get_temperature_ramp_method,
            set_cmd=self._set_temperature_ramp_method,
            val_mapping=,#TODO
            instrument=self
        )
        
        self.temperature_ramp_rate = Parameter(
            name='temperature_ramp_rate',
            label='Temperature ramp rate for the sample stage',
            unit='K/min',
            get_cmd=self._get_temperature_ramp_rate,
            set_cmd=self._set_temperature_ramp_rate,
            instrument=self
        )
        
        self.heater_power_4k_plate = Parameter(
            name='heater_power_4k_plate',
            label='Heater power at the 4K plate',
            unit='',
            get_cmd=self._get_heater_power_4k_plate,
            get_parser=float,
            instrument=self
        )
        
        self.heater_power_sample = Parameter(
            name='heater_power_sample',
            label='Heater power at the sample plate',
            unit='',
            get_cmd=self._get_heater_power_sample,
            get_parser=float,
            instrument=self
        )
        
        self.status_cryostat = Parameter(
            name='status_cryostat',
            label='Cryostat status mode',
            get_cmd=self._get_status_cryostat,
            instrument=self
        )
        
        self.status_magnet = Parameter(
            name='status_magnet',
            label='Magnet status',
            get_cmd=self._get_status_magnet,
            instrument=self
        )
        
        self.status_compressor = Parameter(
            name='status_compressor',
            label='Compressor status',
            get_cmd=self._get_status_compressor,
            instrument=self,
        )
        
        self.status_cooler = Parameter(
            name='status_cooler',
            label='Cooler status',
            get_cmd=self._get_status_cooler,
            instrument=self
        )
        
        self.status_liquid = Parameter(
            name='status_liquid',
            label='Status of liquid in cooling chamber',
            get_cmd=self._get_status_liquid,
            instrument=self
        )
        
        self.status_temperature = Parameter(
            name='status_temperature',
            label='Status of temperature control',
            get_cmd=self._get_status_temperature,
            instrument=self
        )
        
        self.pressure_cooler = Parameter(
            name='pressure_cooler',
            label='Pressure in the circulation loop',
            get_cmd=self._get_pressure_cooler,
            instrument=self
        )
        
        self.pressure_vacuum_chamber = Parameter(
            name='pressure_vacuum_chamber',
            label='Vacuum chamber pressure',
            get_cmd=self._get_pressure_vacuum_chamber
        )
        
        self.magnet_field = Parameter(
            name='magnet_field',
            label='Magnetic field',
            unit='T',
            get_cmd=self._get_magnet_field,
            get_parser=self._parse_oersted_to_tesla,
            set_cmd=self._set_magnet_field,
            set_parser=self._parse_tesla_to_oersted,
            vals=vals.Numbers(min_value=-7, max_value=7),
            instrument=self,
        )
        
        self.magnet_ramp_rate = Parameter(
            name='magnet_ramp_rate',
            label='Magnet ramp rate',
            unit='T/min',
            get_cmd=self._get_magnet_ramp_rate,
            get_parser=self._parse_oersted_to_tesla,
            set_cmd=self._set_magnet_ramp_rate,
            set_parser=self._parse_tesla_to_oersted,
            vals=vals.Numbers(min_value=0, max_value=1), #TODO - change values
            instrument=self,
        )
        
        self.magnet_ramp_method = Parameter(
            name='magnet_ramp_method',
            label='Magnet ramp methode',
            get_cmd=self._get_magnet_ramp_method,
            set_cmd=self._set_magnet_ramp_method,
            val_mapping=,#TODO
            instrument=self,
        )

        self.client.open()
        self.connect_message()

    def ramp_field(self, target, rate):
        self.client.set_field(target, rate)
        
    def close(self) -> None:
        """Close the connection"""
        self.log.debug(f"close connection to {self.name}")
        self.client.close_server()

    def get_idn(self) -> dict[str, str | None]:
        """Return the Instrument Identifier Message"""
        #TODO
        
    def _get_temperature_shield():
        #TODO
        
    def _get_temperature_4k_plate():
        #TODO
        
    def _get_temperature_magnet():
        #TODO
        
    def _get_temperature_sample():
        T, _ = self.client.get_temperature()
        return T
        
    def _get_temperature_ramp_method():
        #TODO
        
    def _get_temperature_ramp_rate():
        #TODO
        
    def _get_heater_power_4k_plate():
        #TODO
        
    def _get_heater_power_sample():
        #TODO
        
    def _get_status_cryostat():
        #TODO
        
    def _get_status_magnet():
        _, sB = self.client.get_field()
        return sB
        
    def _get_status_compressor():
        #TODO
        
    def _get_status_cooler():
        #TODO
        
    def _get_status_liquid():
        #TODO
        
    def _get_status_temperature():
        _, sT = self.client.get_temperature()
        return sT
        
    def _get_pressure_cooler():
        #TODO
        
    def _get_pressure_vacuum_chamber():
        #TODO
        
    def _get_magnet_field():
        B, _ = self.client.get_field()
        
    def _get_magnet_ramp_rate():
        #TODO
        
    def _get_magnet_ramp_method():
        #TODO
        
    def _set_temperature_sample():
        T, sT = self.client.get_temperature()
        #TODO
        
    def _set_temperature_ramp_method():
        #TODO
        
    def _set_temperature_ramp_rate():
        #TODO
        
    def _set_magnet_field():
        #TODO
        
    def _set_magnet_ramp_rate():
        #TODO
        
    def _set_magnet_ramp_method():
        #TODO
    

    def _parse_oersted_to_tesla(val):
        return float(val)*1e-4

    def _parse_tesla_to_oersted(val):
        return float(val)*10000.
