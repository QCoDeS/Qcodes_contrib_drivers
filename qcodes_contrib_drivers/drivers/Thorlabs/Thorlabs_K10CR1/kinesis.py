from __future__ import annotations

from qcodes_contrib_drivers.drivers.Thorlabs.private.kinesis import enums, isc


class ThorlabsK10CR1(isc.KinesisISCInstrument, prefix='ISC',
                     hardware_type=enums.KinesisHWType.CageRotator):
    """Kinesis driver for Thorlabs K10CR1 cage rotator."""
