from __future__ import annotations

import pathlib
from typing import Any, Literal, Mapping

from qcodes.parameters import Parameter
from qcodes.validators import validators as vals
from qcodes_contrib_drivers.drivers.Thorlabs.private.kinesis import enums
from qcodes_contrib_drivers.drivers.Thorlabs.private.kinesis.core import (
    KinesisInstrument
)


class ThorlabsMFF10x(KinesisInstrument, prefix='FF',
                     hardware_type=enums.KinesisHWType.FilterFlipper):
    """Kinesis driver for Thorlabs MFF10x filter flipper.

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
            :func:`~qcodes_contrib_drivers.drivers.Thorlabs.private.kinesis.core.list_available_devices`.
        simulation (optional):
            Enable the Kinesis simulator mode. Note that the serial
            number assigned to the simulated device should be given
            since otherwise the first available device will be
            connected (which might not be a simulated but a real one).
        position_mapping (optional):
            A val mapping for a more human-readable position mapping
            than the internally used 1 and 2. Defaults to
            ``{'open': 1, 'close': 2}``.
        metadata (optional):
            Additional static metadata.
        label (optional):
            Nicely formatted name of the instrument.

    """

    def __init__(self, name: str, dll_dir: str | pathlib.Path | None = '',
                 serial: int | None = None, simulation: bool = False,
                 polling: int = 200, home: bool = False,
                 position_mapping: Mapping[str, Literal[1, 2]] | None = None,
                 metadata: Mapping[Any, Any] | None = None,
                 label: str | None = None):
        super().__init__(name, dll_dir, serial, simulation, polling, home,
                         metadata, label)

        self.position = Parameter(
            'position',
            get_cmd=self._kinesis.get_position,
            set_cmd=self._kinesis.move_to_position,
            val_mapping=position_mapping or {'open': 1, 'close': 2},
            label='Position',
            instrument=self
        )
        """The position of the flipper."""
        self.transit_time = Parameter(
            'transit_time',
            get_cmd=self._kinesis.get_transit_time,
            set_cmd=self._kinesis.set_transit_time,
            vals=vals.Ints(300, 2800),
            set_parser=int,
            unit='ms',
            label='Transit time',
            instrument=self
        )
        """The transit time between two positions."""

    def toggle_position(self):
        """Toggle the position of the flipper."""
        # val_mapping is dynamic, so use inverse_val_mapping together
        # with the hardware values
        if self.position() == self.position.inverse_val_mapping[1]:
            self.position(self.position.inverse_val_mapping[2])
        else:
            self.position(self.position.inverse_val_mapping[1])
