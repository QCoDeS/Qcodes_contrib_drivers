from qcodes_contrib_drivers.drivers.Thorlabs.private.kinesis.enums import (
    KinesisHWType
)
from qcodes_contrib_drivers.drivers.Thorlabs.private.kinesis.isc import (
    KinesisIntegratedStepperMotor
)


class ThorlabsK10CR1(KinesisIntegratedStepperMotor):
    @classmethod
    @property
    def _prefix(self):
        return 'ISC'

    @classmethod
    @property
    def hardware_type(cls) -> KinesisHWType:
        return KinesisHWType.CageRotator
