import logging
from time import sleep
from typing import Optional

from qcodes.utils.helpers import create_on_off_val_mapping

from .DeviceManagerCLI import IGenericDeviceCLI
from .qcodes_thorlabs_integration import ThorlabsObjectWrapper, ThorlabsMixin

log = logging.getLogger(__name__)

class GenericMotorCLI(IGenericDeviceCLI):
    """
    Base class for interfacing with Thorlabs motorized stages via the GenericMotorCLI .NET API in QCoDeS.

    This class provides the basic functionalities for motor control, including initialization,
    movement, and polling. It is intended to be extended by more specific motor classes.

    Attributes:
        initializing: Determine whether this stage is initializing
        state: Read-only parameter indicating the current state of the motor.
        terminated: Determine whether this stage is busy

    Methods:
        home: Sends the motor to its home position.
        clear_exceptions: Clears the last stage exceptions if any.
    """

    def __init__(self, *args, **kwargs):

        if not isinstance(self, ThorlabsMixin):
            raise TypeError("GenericMotorCLI should only be mixed with "
                            "subclasses of ThorlabsMixin")            

        super().__init__(*args, **kwargs)

        motor_position_limits = LimitsData(self, 'motor_position_limits')
        self.add_submodule('motor_position_limits', motor_position_limits)

        self.add_parameter(
            'state',
            get_cmd=lambda: self._get_thorlabs_enum('State'),
            docstring='Current motor state. One of the following: '
                      'Idle, Moving, Homing, Initializing, Stopping, or Terminated.'
        )

        self.add_parameter(
            'initializing',
            get_cmd=lambda: self._get_thorlabs_attribute('Initializing'),
            docstring='Determine whether this motor is initializing.',
            val_mapping=create_on_off_val_mapping(
                on_val=True, off_val=False)
        )

        self.add_parameter(
            'terminated',
            get_cmd=lambda: self._get_thorlabs_attribute('Terminated'),
            docstring='Determine whether this Motor has terminated.',
            val_mapping=create_on_off_val_mapping(
                on_val=True, off_val=False)
        )

    def _exit_generic_motor(self):
        """
        Safely terminate operations at exit by:
        * stop polling the motor
        """
        self.stop_polling()

    def wait_for_idle(self, timeout_s=None, rate_s=0.05):
        """
        Block until the motor reaches an idle state.

        Args:
            timeout_s: The maximum time to wait for the motor to become idle, in seconds.
            rate_s: The interval at which to check the motor's state, in seconds.
    
        Raises:
            ThorlabsTimeoutError: If the motor does not reach an idle state within the timeout.
        """
        while self.state() != 'Idle':
            if countdown.passed():
                raise ThorlabsTimeoutError("Motor did not become idle within the timeout period")
            sleep(rate_s)

    def clear_exceptions(self) -> None:
        """Clears the the last stage exceptions if any."""
        self._api_interface.ClearDeviceExceptions()

    def home(self, timeout_ms: int):
        """
        Sends the motor to it's home position.

        Args:
            timeout_ms (int): The wait timeout
                If this is value is 0 then the function will return immediately.
                If this value is non zero, then the function will wait until
                the move completes or the timeout elapses, whichever comes first. 
        """

        self._api_interface.Home(timeout_ms)

"""
    self.addParameter(
        'GetLEDSwitches', # ()
        docstring='Gets the LED switches state.'
    )
"""
class ThorlabsTimeoutError(Exception):
    """Exception raised when a Thorlabs device operation times out."""
    pass


class LimitsData(ThorlabsObjectWrapper):
    """
    Provides an interface to the motion limits and travel modes of a Thorlabs
    motorized stage as defined in the Thorlabs .NET API.

    Attributes:
        direction: Rotation travel direction, indicating the shortest path or specific direction.
        mode: Travel mode of the stage, which can be linear or rotational.
        travel_max: Maximum travel value in device units.
        travel_min: Minimum travel value in device units.
    """
    def __init__(
        self, 
        parent,
        name,
        object_key: Optional[str] = 'MotorPositionLimits',
        getter_name: Optional[str] = None,
        setter_name: Optional[str] = None,
        **kwargs
    ):    
        super().__init__(parent, name, object_key, getter_name, setter_name, **kwargs)

        self.add_parameter(
            "direction",
            get_cmd=lambda: self._get_thorlabs_enum('Direction'),
            docstring='Gets the rotation travel direction. Can be Quickest, Forward, Reverse'
                      'Quickest: Motor will travel in the shortest direction to reach target.'
        )

        self.add_parameter(
            "mode",
            get_cmd=lambda: self._get_thorlabs_enum('Mode'),
            docstring='Gets the travel mode, Linear or Rotational.'
                      ''
                      '  LinearRange - The rotation has a fixed range of travel.'
                      '  RotationalUnlimited - The rotation has an unlimited range of travel.'
                      '  RotationalRange - The rotation has a full 360 travel.'
        )

        self.add_parameter(
            "travel_max",
            get_cmd=lambda: self._get_thorlabs_attribute('MaxValue'),
            docstring='Gets the maximum travel value in Device Units. '
        )

        self.add_parameter(
            "travel_min",
            get_cmd=lambda: self._get_thorlabs_attribute('MinValue'),
            docstring='Gets the minimum travel value in Device Units. '
        )


class StatusBase(ThorlabsObjectWrapper):
    """
    Serves as a common base for representing the status of Thorlabs motorized stages.

    This class allows access to various status information of a motor, such as limit states,
    motion states, and error conditions.

    Attributes:
        limit_hw_bwd: Indicates if the motor is at the backward hardware limit.
        limit_hw_fwd: Indicates if the motor is at the forward hardware limit.
        limit_hw: Indicates if the motor is at any hardware limit.
        enabled: Indicates if the stage is enabled for operation.
        error: Indicates if there is an error condition on the motor.
        homed: Indicates if the motor has been successfully homed.
        homing: Indicates if the motor is currently in the process of homing.
        in_motion: Indicates if the motor is currently in motion.
        jogging: Indicates if the motor is currently jogging.
        jogging_bwd: Indicates if the motor is jogging in the backward direction.
        jogging_fwd: Indicates if the motor is jogging in the forward direction.
        moving: Indicates if the motor is moving.
        moving_bwd: Indicates if the motor is moving backward.
        moving_fwd: Indicates if the motor is moving forward.
    """
    def __init__(
        self, parent, name,
        object_key: Optional[str] = 'Status',
        getter_name: Optional[str] = None,
        setter_name: Optional[str] = None,
        **kwargs
    ):    
        super().__init__(parent, name, object_key, getter_name, setter_name, **kwargs)

        self.add_parameter(
            "limit_hw_bwd",
            get_cmd=lambda: self._get_thorlabs_attribute('IsAtBackwardHWLimit'),
            docstring='Determine whether this motor is at backward limit.'
        )

        self.add_parameter(
            "limit_hw_fwd",
            get_cmd=lambda: self._get_thorlabs_attribute('IsAtForwardHWLimit'),
            docstring='Determine whether this motor is at forward limit.'
        )

        self.add_parameter(
            "limit_hw",
            get_cmd=lambda: self._get_thorlabs_attribute('IsAtHWLimit'),
            docstring='Determine whether this motor is at limit.'
        )

        self.add_parameter(
            "enabled",
            get_cmd=lambda: self._get_thorlabs_attribute('IsEnabled'),
            docstring='Determine whether this stage is enabled.'
        )

        self.add_parameter(
            "error",
            get_cmd=lambda: self._get_thorlabs_attribute('IsError'),
            docstring='Determine whether this motor is error.'
        )

        self.add_parameter(
            "homed",
            get_cmd=lambda: self._get_thorlabs_attribute('IsHomed'),
            docstring='Determine whether this motor is homed.'
        )

        self.add_parameter(
            "homing",
            get_cmd=lambda: self._get_thorlabs_attribute('IsHoming'),
            docstring='Determine whether this motor is homing.'
        )

        self.add_parameter(
            "in_motion",
            get_cmd=lambda: self._get_thorlabs_attribute('IsInMotion'),
            docstring='Determine whether this motor is in motion.'
        )

        self.add_parameter(
            "jogging",
            get_cmd=lambda: self._get_thorlabs_attribute('IsJogging'),
            docstring='Determine whether this motor is jogging.'
        )

        self.add_parameter(
            "jogging_bwd",
            get_cmd=lambda: self._get_thorlabs_attribute('IsJoggingBackward'),
            docstring='Determine whether this motor is jogging backward.'
        )

        self.add_parameter(
            "jogging_fwd",
            get_cmd=lambda: self._get_thorlabs_attribute('IsJoggingForward'),
            docstring='Determine whether this motor is jogging forward.'
        )

        self.add_parameter(
            "moving",
            get_cmd=lambda: self._get_thorlabs_attribute('IsMoving'),
            docstring='Determine whether this motor is moving.'
        )

        self.add_parameter(
            "moving_bwd",
            get_cmd=lambda: self._get_thorlabs_attribute('IsMovingBackward'),
            docstring='Determine whether this motor is moving backward.'
        )

        self.add_parameter(
            "moving_fwd",
            get_cmd=lambda: self._get_thorlabs_attribute('IsMovingForward'),
            docstring='Determine whether this motor is moving forward.'
        )
