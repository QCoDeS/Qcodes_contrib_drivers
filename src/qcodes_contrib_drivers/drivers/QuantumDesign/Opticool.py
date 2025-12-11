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
from  MultiPyVu import Client

from qcodes.instrument import Instrument
from qcodes.parameters import Parameter
from qcodes import validators as vals

log = logging.getLogger(__name__)


class Opticool(Instrument):
    """
    Class to represent an Opticool cryostat.

    Args:
        name (str): name for the instrument
        address (str): IP address of the MultiPyVu server instance. Defaults to
            localhost
        port (int): port to connect IP. Defaults to 5000

    Status: work-in-progress

    Todo:
        find a way to get the remaining functions (may involve bypassing MultiPyVu)
    """

    def __init__(
            self,
            name: str,
            address: Optional[str] = 'localhost',
            port: Optional[int] = 5000,
            **kwargs: Any) -> None:
        super().__init__(name, **kwargs)
        self.client = Client(host=address, port=port)

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

        self.temperature_ramp_setpoint = Parameter(
            name='temperature_ramp_setpoint',
            label='Ramp setpoint for the sample stage temperature',
            unit='K',
            get_cmd=self._get_temperature_setpoint,
            get_parser=float,
            set_cmd=self._set_temperature_setpoint,
            vals=vals.Numbers(1.4, 350),
            instrument=self
        )

        self.temperature_ramp_method = Parameter(
            name='temperature_ramp_method',
            label='Ramp method for the sample stage temperature',
            get_cmd=self._get_temperature_ramp_method,
            set_cmd=self._set_temperature_ramp_method,
            vals=vals.Enum('no_overshoot', 'fast_settle'),
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

        self.status_temperature_sample = Parameter(
            name='status_temperature_sample',
            label='Status of sample temperature control',
            get_cmd=self._get_status_temperature_sample,
            instrument=self
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

        self.magnet_ramp_setpoint = Parameter(
            name='magnet_ramp_setpoint',
            label='Magnetic ramp setpoint',
            unit='T',
            get_cmd=self._get_magnet_ramp_setpoint,
            get_parser=self._parse_oersted_to_tesla,
            set_cmd=self._set_magnet_ramp_setpoint,
            set_parser=self._parse_tesla_to_oersted,
            vals=vals.Numbers(min_value = -7, max_value=7),
            instrument=self
        )
        
        self.magnet_ramp_rate = Parameter(
            name='magnet_ramp_rate',
            label='Magnet ramp rate',
            unit='T/s',
            get_cmd=self._get_magnet_ramp_rate,
            get_parser=self._parse_oersted_to_tesla,
            set_cmd=self._set_magnet_ramp_rate,
            set_parser=self._parse_tesla_to_oersted,
            instrument=self,
        )

        self.magnet_ramp_method = Parameter(
            name='magnet_ramp_method',
            label='Magnet ramp methode',
            get_cmd=self._get_magnet_ramp_method,
            set_cmd=self._set_magnet_ramp_method,
            vals=vals.Enum('linear', 'no_overshoot', 'oscillate'),
            instrument=self,
        )

        self.magnet_ramp_mode = Parameter(
            name='magnet_ramp_mode',
            label='Magnet ramp mode',
            get_cmd=self._get_magnet_driven_mode,
            set_cmd=self._set_magnet_driven_mode,
            vals=vals.Enum('driven', 'persistent'),
            insrument=self
        )

        self.client.open()
        self.connect_message()
        (
            self._temp_setpoint,
            self._temp_ramp_rate,
            self._temp_ramp_method
        ) = self.client.get_temperature_setpoints()
        (
            self._field_setpoint,
            self._field_ramp_rate,
            self._field_ramp_method,
            self._field_driven_mode
        ) = self.client.get_field_setpoints()


    def ramp_field(self):
        self.log.info('Ramping field to target=%s, rate=%s, approach=%s, driven=%s'
            % (self._field_target, self.field_rate,
               self._field_approach_mode, self._field_driven_mode))

        self.client.set_field(
            self._field_target,
            self._field_rate,
            self._field_approach_mode,
            self._field_driven_mode
        )

    def ramp_temp(self):
        self.log.info('Ramping temperature to target=%s, rate=%s, method=%s'
            % (self._temp_setpoint, self._temp_ramp_rate, self._temp_ramp_method))
        
        self.client.set_temperature(
            self._temp_setpoint,
            self._temp_ramp_rate,
            self._temp_ramp_method,
        )

    def seal(self):
        self.log.info('Seal chamber')
        self.client.set_chamber(self.client.chamber.mode.seal)

    def purge_seal(self):
        self.log.info('Purge Seal')
        self.client.set_chamber(self.client.chamber.mode.purge_seal)

    def vent_seal(self):
        self.log.info('Vent Seal')
        self.client.set_chamber(self.client.chamber.mode.vent_seal)

    def pump_continuous(self):
        self.log.info('Start continuous pumping of the chamber')
        self.client.set_chamber(self.client.chamber.mode.pump_continuous)

    def vent_continuous(self):
        self.log.info('Start continuous venting of the chamber')
        self.client.set_chamber(self.client.chamber.mode.vent_continuous)

    def high_vacuum(self):
        self.log.info('Start high vacuum mode')
        self.client.set_chamber(self.client.chamber.mode.high_vacuum)

    def close(self) -> None:
        """Close the connection"""
        self.log.debug(f"close connection to {self.name}")
        self.client.close_server()

    def get_idn(self) -> dict[str, str | None]:
        """Overrides instrument function

        Returns:
            A dict containing vendor, model, serial, and firmware."""
        idparts = ['Quantum Design', self.client.instrument_name, None, self.client.get_version()]

        return dict(zip(('vendor', 'model', 'serial', 'firmware'), idparts))

    #def _get_temperature_shield(self):
    #    print('TODO')

    #def _get_temperature_4k_plate(self):
    #    print('TODO')

    #def _get_temperature_magnet(self):
    #    print('TODO')

    def _get_temperature_sample(self):
        T, _ = self.client.get_temperature()
        return T
    
    def _get_temperature_aux(self):
        T, _ = self.client.get_aux_temperature()
        return T
    
    def _get_temperature_setpoint(self):
        T, _, _ = self.client.get_temperature_setpoints()
        self._temp_setpoint = T
        return T

    def _get_temperature_ramp_method(self):
        _, _, mode = self.client.get_temperature_setpoints()
        self._temp_ramp_method = mode
        return mode

    def _get_temperature_ramp_rate(self):
        _, rate, _ = self.client.get_temperature_setpoints()
        self._temp_ramp_rate = rate
        return rate

    #def _get_heater_power_4k_plate():
    #    print('TODO')

    #def _get_heater_power_sample():
    #    print('TODO')

    def _get_status_cryostat(self):
        return self.client.get_server_status()

    def _get_status_magnet(self):
        _, sB = self.client.get_field()
        return sB

    #def _get_status_compressor():
    #    print('TODO')

    #def _get_status_cooler():
    #    print('TODO')

    #def _get_status_liquid():
    #    print('TODO')

    def _get_status_chamber(self):
        return self.client.get_chamber()

    def _get_status_temperature_sample(self):
        _, sT = self.client.get_temperature()
        return sT
    
    def _get_status_temperature_aux(self):
        _, sT = self.client.get_aux_temperature()
        return sT

    #def _get_pressure_cooler():
    #    print('TODO')

    #def _get_pressure_vacuum_chamber():
    #    print('TODO')

    def _get_magnet_field(self):
        B, _ = self.client.get_field()
        return B
    
    def _get_magnet_ramp_setpoint(self):
        B, _, _, _ = self.client.get_field_setpoints()
        if self._field_setpoint == B:
            pass
        else:
            print('magnet setpoint is set to {B} on instrument, {self._field_setpoint} in QCoDeS driver.') 
        return self._field_setpoint

    def _get_magnet_ramp_rate(self):
        _, rate, _, _ = self.client.get_field_setpoints()
        self._field_ramp_rate = rate
        return rate

    def _get_magnet_ramp_method(self):
        _, _, mode, _ = self.client.get_field_setpoints()
        self._field_ramp_method = mode
        return mode

    def _get_magnet_driven_mode(self):
        _, _, _, mode = self.client.get_field_setpoints()
        self._field_driven_mode = mode
        return mode

    def _set_temperature_sample(self, setpoint):
        self.client.set_temperature(setpoint, self._temp_ramp_rate, self._temp_ramp_method)

    def _set_temperature_setpoint(self, setpoint):
        self._temp_setpoint = setpoint

    def _set_temperature_ramp_method(self, method):
        if method == 'no_overshoot':
            self._temp_ramp_method = self.client.temperature.approach_mode.no_overshoot
        else:
            self._temp_ramp_method = self.client.temperature.approach_mode.fast_settle

    def _set_temperature_ramp_rate(self, rate):
        self._temp_ramp_rate = rate

    def _set_status_chamber(self, status):
        """accept items seal, purge_seal, vent, vent_seal, pump_continuous,
        vent_continuous and high_vacuum.
        """
        self.client.set_chamber(status)

    def _set_magnet_field(self, setpoint):
        self.client.set_field(
            setpoint, self._field_ramp_rate,
            self._field_ramp_method, self._field_driven_mode)
        
    def _set_magnet_ramp_setpoint(self, setpoint):
        self._field_setpoint = setpoint

    def _set_magnet_ramp_rate(self, rate):
        self._field_ramp_rate = rate

    def _set_magnet_ramp_method(self, method):
        if method == 'no_overshoot':
            self._field_ramp_method = self.client.field.approach_mode.no_overshoot
        elif method == 'oscillate':
            self._field_ramp_method = self.client.field.approach_mode.oscillate
        else:
            self._field_ramp_method = self.client.field.approach_mode.linear

    def _set_magnet_driven_mode(self, mode):
        if mode == 'driven':
            self._field_driven_mode = self.client.field.driven_mode.driven
        else:
            self._field_driven_mode = self.client.field.driven_mode.persistent

    def _parse_oersted_to_tesla(self, val):
        return float(val)*1e-4

    def _parse_tesla_to_oersted(self, val):
        return float(val)*10000.
