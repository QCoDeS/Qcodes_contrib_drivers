from __future__ import annotations

import pathlib
from functools import partial
from typing import Any, Mapping

from qcodes import Parameter, validators as vals
from qcodes_contrib_drivers.drivers.Thorlabs.private.kinesis import enums, isc


class ThorlabsK10CR1(isc.KinesisISCInstrument, prefix='ISC',
                     hardware_type=enums.KinesisHWType.CageRotator):
    """Kinesis driver for Thorlabs K10CR1 cage rotator.

    Args:
        name:
            An identifier for this instrument.
        dll_dir (optional):
            The directory where the kinesis dlls reside.
        serial (optional):
            The serial number of the device to connect to. If omitted,
            the first available device found will be used. For a list
            of all available devices, use
            :meth:`list_available_devices` on an existing instance or
            :func:`qcodes_contrib_drivers.drivers.Thorlabs.private.kinesis.core.list_available_devices`.
        simulation (optional):
            Enable the Kinesis simulator mode. Note that the serial
            number assigned to the simulated device should be given
            since otherwise the first available device will be
            connected (which might not be a simulated but a real one).
        metadata (optional):
            Additional static metadata.
        label (optional):
            Nicely formatted name of the instrument.

    """

    def __init__(self, name: str, dll_dir: str | pathlib.Path | None = '',
                 serial: int | None = None, simulation: bool = False,
                 metadata: Mapping[Any, Any] | None = None,
                 label: str | None = None):
        super().__init__(name, dll_dir, serial, simulation, metadata, label)

        self.position = Parameter(
            "position",
            get_cmd=self._kinesis.get_position,
            set_cmd=self._kinesis.move_to_position,
            get_parser=partial(self._kinesis.real_value_from_device_unit,
                               unit_type=enums.ISCUnitType.Distance),
            set_parser=partial(self._kinesis.device_unit_from_real_value,
                               unit_type=enums.ISCUnitType.Distance),
            vals=vals.Numbers(0, 360),
            unit=u"\u00b0",
            label="Position",
            instrument=self
        )
        """The wheel position in degrees. 
        
        Use :meth:`move_to_position` with argument block=True to block 
        execution until the targeted position is reached. You should 
        probably invalidate the parameter cache afterwards though.
        """
