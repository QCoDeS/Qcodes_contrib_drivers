from qcodes_contrib_drivers.drivers.Thorlabs.private.kinesis.enums import (
    KinesisHWType
)
from qcodes_contrib_drivers.drivers.Thorlabs.private.kinesis.isc import (
    KinesisIntegratedStepperMotor
)


class ThorlabsK10CR1(KinesisIntegratedStepperMotor):
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
        metadata (optional):
            Additional static metadata.
        label (optional):
            Nicely formatted name of the instrument.

    """
    @classmethod
    @property
    def _prefix(self):
        return 'ISC'

    @classmethod
    @property
    def hardware_type(cls) -> KinesisHWType:
        return KinesisHWType.CageRotator
