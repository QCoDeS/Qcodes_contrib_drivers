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

    Todo: include all temperature sensors in the driver
    """

    def __init__(
            self,
            name: str,
            address: Optional[str] = 'localhost',
            port: Optional[int] = 5000,
            **kwargs: Any) -> None:
        super().__init__(name, **kwargs)

        try:
            from MultiPyVu import Client
        except ImportError as e:
            multipyvu_import_failed_msg = (
                "Missing required MultiPyVu package for initializing QuantumDesign Opticool "
                f"instrument with name {name}. Install it first, e.g. pip install MultiPyVu."
            )
            raise ImportError(multipyvu_import_failed_msg) from e

        self.client = Client(host=address, port=port)

        self._FIELD_APPROACH_MAPPING = {
            'no_overshoot': self.client.field.approach_mode.no_overshoot,
            'oscillate': self.client.field.approach_mode.oscillate,
            'linear': self.client.field.approach_mode.linear,
        }
        self._FIELD_DRIVEN_MAPPING = {
            'driven': self.client.field.driven_mode.driven,
            'persistent': self.client.field.driven_mode.persistent,
        }
        self._TEMPERATURE_APPROACH_MAPPING = {
            'no_overshoot': self.client.temperature.approach_mode.no_overshoot,
            'fast_settle': self.client.temperature.approach_mode.fast_settle
        }

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
            instrument=self
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

    def ask_raw(self, cmd: str, query:str=''):
        """Send a query to the server

        Parameters:
            action : str - the general command sent to the MultiVu server.
                (TEMP(?), FIELD(?), CHAMBER(?), etc. Second item is the query
            query : str, optional - specific details of the command

        Returns:
            out"""
        self.client._query_server(cmd, query)

    def ramp_field(self):
        """Ramp field to values specified using magnet_ramp_* parameters"""
        self.log.info(
            f'Ramping field to target={self._field_setpoint}, \
            rate={self._field_ramp_rate}, approach={self._field_ramp_method}, \
            driven={self._field_driven_mode}')

        ramp_method = self._FIELD_APPROACH_MAPPING.get(
            self._field_ramp_method, self._field_ramp_method)
        driven_mode = self._FIELD_DRIVEN_MAPPING.get(
            self._field_driven_mode, self._field_driven_mode)
        if isinstance(self._field_ramp_method, str):
            self._field_ramp_method = ramp_method
        if isinstance(self._field_driven_mode, str):
            self._field_driven_mode = driven_mode
        self.client.set_field(
            self._field_setpoint,
            self._field_ramp_rate,
            self._field_ramp_method,
            self._field_driven_mode
        )

    def ramp_temp(self):
        """Ramp temperature to valuess specified using temperature_ramp_*
        parameters"""
        self.log.info(
            f'Ramping temperature to target={self._temp_setpoint}, \
            rate={self._temp_ramp_rate}, method={self._temp_ramp_method}')

        ramp_method = self._TEMPERATURE_APPROACH_MAPPING.get(
            self._temp_ramp_method, self._temp_ramp_method)
        if isinstance(self._temp_ramp_method, str):
            self._temp_ramp_method = ramp_method
        self.client.set_temperature(
            self._temp_setpoint,
            self._temp_ramp_rate,
            self._temp_ramp_method,
        )

    def seal(self):
        """Seal chamber"""
        self.log.info('Seal chamber')
        self.client.set_chamber(self.client.chamber.mode.seal)

    def purge_seal(self):
        """Purge seal"""
        self.log.info('Purge Seal')
        self.client.set_chamber(self.client.chamber.mode.purge_seal)

    def vent_seal(self):
        """Vent seal"""
        self.log.info('Vent Seal')
        self.client.set_chamber(self.client.chamber.mode.vent_seal)

    def pump_continuous(self):
        """Continuous pumping of chamber"""
        self.log.info('Start continuous pumping of the chamber')
        self.client.set_chamber(self.client.chamber.mode.pump_continuous)

    def vent_continuous(self):
        """Continuous venting of chamber"""
        self.log.info('Start continuous venting of the chamber')
        self.client.set_chamber(self.client.chamber.mode.vent_continuous)

    def high_vacuum(self):
        """High vacuum mode"""
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

    def _get_temperature_sample(self):
        temp, _ = self.client.get_temperature()
        return temp

    def _get_temperature_aux(self):
        temp, _ = self.client.get_aux_temperature()
        return temp

    def _get_temperature_setpoint(self):
        temp, _, _ = self.client.get_temperature_setpoints()
        self._temp_setpoint = temp
        return temp

    def _get_temperature_ramp_method(self):
        _, _, mode = self.client.get_temperature_setpoints()
        self._temp_ramp_method = mode
        return mode

    def _get_temperature_ramp_rate(self):
        _, rate, _ = self.client.get_temperature_setpoints()
        self._temp_ramp_rate = rate
        return rate

    def _get_status_cryostat(self):
        return self.client.get_server_status()

    def _get_status_magnet(self):
        _, status = self.client.get_field()
        return status

    def _get_status_chamber(self):
        return self.client.get_chamber()

    def _get_status_temperature_sample(self):
        _, status = self.client.get_temperature()
        return status

    def _get_status_temperature_aux(self):
        _, status = self.client.get_aux_temperature()
        return status

    def _get_magnet_field(self):
        field, _ = self.client.get_field()
        return field

    def _get_magnet_ramp_setpoint(self):
        field, _, _, _ = self.client.get_field_setpoints()
        if self._field_setpoint == field:
            pass
        else:
            print(f'magnet setpoint is set to {field} on instrument, \
                  {self._field_setpoint} in QCoDeS driver.')
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
        ramp_method = self._TEMPERATURE_APPROACH_MAPPING.get(
            self._temp_ramp_method, self._temp_ramp_method)
        if isinstance(self._temp_ramp_method, str):
            self._temp_ramp_method = ramp_method
        self.client.set_temperature(setpoint, self._temp_ramp_rate, self._temp_ramp_method)

    def _set_temperature_setpoint(self, setpoint):
        self._temp_setpoint = setpoint

    def _set_temperature_ramp_method(self, method):
        ramp_method = self._TEMPERATURE_APPROACH_MAPPING.get(
            method, method)
        if isinstance(self._temp_ramp_method, str):
            self._temp_ramp_method = ramp_method

    def _set_temperature_ramp_rate(self, rate):
        self._temp_ramp_rate = rate

    def _set_status_chamber(self, status):
        self.client.set_chamber(status)

    def _set_magnet_field(self, setpoint):
        ramp_method = self._FIELD_APPROACH_MAPPING.get(
            self._field_ramp_method, self._field_ramp_method)
        driven_mode = self._FIELD_DRIVEN_MAPPING.get(
            self._field_driven_mode, self._field_driven_mode)
        if isinstance(self._field_ramp_method, str):
            self._field_ramp_method = ramp_method
        if isinstance(self._field_driven_mode, str):
            self._field_driven_mode = driven_mode
        self.client.set_field(
            setpoint, self._field_ramp_rate,
            self._field_ramp_method, self._field_driven_mode)

    def _set_magnet_ramp_setpoint(self, setpoint):
        self._field_setpoint = setpoint

    def _set_magnet_ramp_rate(self, rate):
        self._field_ramp_rate = rate

    def _set_magnet_ramp_method(self, method):
        ramp_method = self._FIELD_APPROACH_MAPPING.get(method, method)
        if isinstance(self._field_ramp_method, str):
            self._field_ramp_method = ramp_method

    def _set_magnet_driven_mode(self, mode):
        driven_mode = self._FIELD_DRIVEN_MAPPING.get(mode, mode)
        if isinstance(self._field_driven_mode, str):
            self._field_driven_mode = driven_mode

    def _parse_oersted_to_tesla(self, val):
        return float(val)*1e-4

    def _parse_tesla_to_oersted(self, val):
        return float(val)*10000.
