import logging

from .GenericMotorCLI_AdvancedMotor import GenericAdvancedMotorCLI

log = logging.getLogger(__name__)


class IntegratedStepperMotor(GenericAdvancedMotorCLI):
    """
    This class is the common base class to all Integrated Stepper Controls.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
