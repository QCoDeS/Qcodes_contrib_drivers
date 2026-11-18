import logging

from .GenericMotorCLI_AdvancedMotor import GenericAdvancedMotorCLI
from .GenericMotorCLI_ControlParameters import IDCPIDParameters
from .DeviceManagerCLI import ILockableDeviceCLI, IDeviceScanning


IDCPIDParameters

log = logging.getLogger(__name__)

class TCubeDCServo(IDCPIDParameters, IDeviceScanning, GenericAdvancedMotorCLI):
    """
    This is the main entry class for the TCubeDCServo.

    This class provides direct access to manually control the TCube DC Servo and 
    to read the TCube DC Servo state.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
