import logging
from typing import Optional

from qcodes.instrument.channel import InstrumentBase
from qcodes.utils.helpers import create_on_off_val_mapping
import clr
from System import Decimal as DotNetDecimal

from .GenericMotorCLI import GenericMotorCLI, StatusBase
from .GenericMotorCLI_ControlParameters import (
    HomeParameters, IDCPIDParameters, LimitSwitchParameters, VelocityParameters, JogParameters)
from .qcodes_thorlabs_integration import PyDecimalNumbers, ThorlabsObjectWrapper


log = logging.getLogger(__name__)


class GenericAdvancedMotorCLI(GenericMotorCLI):
    """
    Interface to Thorlabs' GenericAdvancedMotorCLI as a Qcodes Instrument class.

    Extends GenericMotorCLI to provide additional advanced features as per 
    Thorlabs' .NET API's inheritance structure, interfaced through QCoDeS.

    Attributes:
        advanced_limits: Module for advanced motor limits settings.
        can_home: Determine if we can home
        home_parameters: Module for home position parameters.
        needs_homing: Home requiring stage
        velocity_parameters: Module for velocity settings.
        status: Module representing the current status of the device.
        limit_switch_parameters: Module for limit switch settings.
        wait_for_movement: Flag to wait for the move operation to finish.
        position: Parameter for the current position of the stage.

    Methods:
        home: Sends the motor to its home position considering 'wait_for_movement'.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        advanced_limits = AdvancedMotorLimits(self, 'advanced_limits')
        self.add_submodule('advanced_limits', advanced_limits)

        home_parameters = HomeParameters(self, 'home_parameters')
        self.add_submodule('home_parameters', home_parameters)

        velocity_parameters = VelocityParameters(self, 'velocity_parameters')
        self.add_submodule('velocity_parameters', velocity_parameters)

        jog_parameters = JogParameters(self, 'jog_parameters')
        self.add_submodule('jog_parameters', jog_parameters)

        status_class = self._status_class()
        status = status_class(self, 'status')
        self.add_submodule('status', status)

        limit_switch_parameters = LimitSwitchParameters(self, 'limit_switch_parameters')
        self.add_submodule('limit_switch_parameters', limit_switch_parameters)

        self._wait_for_movement = True  # Default value

        self.add_parameter(
            'backlash',
            get_cmd=lambda: self._get_thorlabs_decimal(getter_name='GetBacklash'),
            set_cmd=lambda x: self._set_thorlabs_decimal(x, getter_name='SetBacklash'),
            unit=self.advanced_limits.length_unit()
        ),
        

        self.add_parameter(
            'enabled',
            get_cmd=lambda: self._get_thorlabs_attribute('IsEnabled'),
            set_cmd=self._set_enabled_state, 
            docstring='Determine whether this stage is enabled.',
            val_mapping=create_on_off_val_mapping(
                on_val=True, off_val=False)
        )

        self.add_parameter(
            'wait_for_movement',
            get_cmd=lambda: self._wait_for_movement,
            set_cmd=lambda x: setattr(self, '_wait_for_movement', x),
            val_mapping=create_on_off_val_mapping(
                on_val=True, off_val=False),            
            docstring='Wait for the move operation to finish.'
        )

        self.add_parameter(
            'position',
            get_cmd=lambda: self._get_thorlabs_decimal('Position'),
            set_cmd=self._set_position,
            vals=self._get_position_vals(),
            unit=self.advanced_limits.length_unit(),
            docstring='Position of the stage. '
                      'The operation will use the current value of "movement_timeout" for the move operation.'
        )

        self.add_parameter(
            'needs_homing',
            get_cmd=lambda: self._get_thorlabs_attribute('NeedsHoming'),
            docstring='Determines whether the motor is of a type that must be Homed before a valid move can be performed.',
        )

        self.add_parameter(
            'can_home',
            get_cmd=lambda: self._get_thorlabs_attribute('CanHome'),
            docstring='Determine if we can home.'
        )



    def _get_position_vals(self):
        """
        Retrieves the validator for the position parameter based on the stage's limit settings.

        This method checks the mode of the motor to determine if it operates within a
        rotational range or a linear range. It returns a Validator object that enforces
        the minimum and maximum allowable positions for the motor. For a rotational range,
        the Validator ensures the position is within 0-360 degrees, accounting for multiple
        rotations. For a linear range, it simply enforces the minimum and maximum position
        values as set by the advanced limits.

        Returns:
            Validator: An instance of `RotationalStageValidator` if the motor operates in
            a rotational range, enforcing a 0-360 degrees limit, or an instance of
            `Numbers` for a linear range, enforcing the set minimum and maximum position values.

        Raises:
            ValueError: If the advanced limits have not been set correctly or if the mode
            is unrecognized.
        """

        position_min = self.advanced_limits.length_min()
        position_max = self.advanced_limits.length_max()

        if position_max > position_min:
            if self.motor_position_limits.mode() == 'RotationalRange':
                return RotationalStageValidator(position_min, position_max)
            else:
                return PyDecimalNumbers(position_min, position_max)
        else:
            return None

    def _status_class(self):
        """
        Determines the appropriate class for the status submodule based on the type of `api_interface`.

        Returns:
            The appropriate class for the status submodule.
        """
        StepperStatusType = "<class 'Thorlabs.MotionControl.GenericMotorCLI.AdvancedMotor.StepperStatus'>"
        DCStatusType = "<class 'Thorlabs.MotionControl.GenericMotorCLI.AdvancedMotor.DCStatus'>"

        status_type = str(type(self._api_interface.Status))

        if status_type == StepperStatusType:
            return StepperStatus
        elif status_type == DCStatusType:
            return DCStatus
        else:
            return StatusBase

    def home(self) -> None:
        """
        Send the motor to its home position.

        This operation considers the current value of "wait_for_movement" for
        the move operation.

        Raises:
            NotImplementedError: If the inherited method is not implemented.
        """
        # Calculate the maximum distance the motor can move
        max_distance = abs(
            self.advanced_limits.length_max() - 
            self.advanced_limits.length_min()
        )

        # Determine timeout based on whether the motor should wait for movement
        if self.wait_for_movement():
            # Calculate required time for the movement
            time_needed = self._compute_move_time_ms(
                max_distance,
                self.advanced_limits.acceleration_max(),
                self.home_parameters.velocity()
            )
            timeout_ms = 2000 + time_needed
        else:
            timeout_ms = 0

        # Call the parent class's home method
        super().home(timeout_ms)

    def _set_position(self, position) -> None:
        """
        Moves the axis to the specified position.
        If 'wait_for_movement' is set to False, the method will return immediately.

        This method commands the axis to move to a given position, provided that the axis 
        has been previously homed. It calculates the movement timeout based on the 
        maximum acceleration and the set homing velocity. If the axis operates in a 
        rotational mode, it accounts for the wrap-around behavior to determine the 
        shortest path to the target position. For non-rotational modes, it simply 
        calculates the direct distance to the target position.

        Args:
            position: The desired absolute position to move the axis to.

        Raises:
            AxisNotHomedError: Raised if the axis has not been homed prior to the 
                               move command.
            NotImplementedError: Raised if the current direction setting is not 
                                 configured to 'Quickest', which is required for 
                                 calculating the shortest path.
        """
        if not self.status.homed():
            raise AxisNotHomedError("The axis must be homed before setting its position.")

        actual_direction = self.motor_position_limits.direction()
        if actual_direction != 'Quickest':
            raise NotImplementedError

        # Check if the axis mode is rotational and adjust the target position accordingly
        mode = self.motor_position_limits.mode()
        current_position = self.position()
        if mode == 'RotationalRange':
            # Normalize the current and target positions to a 0-360 range
            current_position %= 360
            position %= 360

            # Compute the shortest distance considering the rotational wrap-around
            direct_distance = abs(current_position - position)
            wrap_around_distance = 360 - direct_distance
            shortest_distance = min(direct_distance, wrap_around_distance)
        else:
            # For non-rotational modes, compute the distance directly
            shortest_distance = abs(current_position - position)

        if self.wait_for_movement():
            # Calculate time required for movement based on the shortest distance
            time_needed = self._compute_move_time_ms(
                shortest_distance,
                self.advanced_limits.acceleration_max(),
                self.home_parameters.velocity()
            )
            timeout_ms = 1000 + time_needed
        else:
            timeout_ms = 0

        self.move_to(position, timeout_ms)

    def move_to(self, position: DotNetDecimal, timeout_ms=0) -> None:
        """
        Move the device to the position identified in Real World Units.

        Args:
            position: 
            timeout_ms: If 0 the function will return immediately.
                        If this value is non zero, then the function will wait
                        until the move completes or the timeout elapses,
                        whichever comes first. 
        """
        self._api_interface.MoveTo(DotNetDecimal(position), timeout_ms)

    def _set_enabled_state(self, value: bool) -> None:
        """
        Set the enabled state of the stage.

        This method enables or disables the stage based on the boolean value
        provided as an argument. It calls the respective `enable` or `disable`
        methods to change the state of the stage.

        Args:
            value (bool): The state to set. True to enable, False to disable.

        Returns:
            None: This method does not return anything.

        """
        if value:
            self.enable()
        else:
            self.disable()

    def _compute_move_time_ms(
        self, 
        distance: float, 
        acceleration: float, 
        velocity_max: float
    ) -> int:
        """
        Compute the time required for the motor to move a given distance.

        The function calculates the time required based on acceleration,
        maximum velocity, and distance to be covered. The time is returned
        in milliseconds.

        Args:
            distance (float): Distance the motor needs to cover.
            acceleration (float): Acceleration of the motor.
            velocity_max (float): Maximum velocity the motor can attain.

        Returns:
            int: Time required in milliseconds to cover the given distance.

        Raises:
            NotImplementedError: Raised if the units are not supported.
        """

        # Check if the units are in "/s" and "/s²" to determine the time factor
        unit_s = (
            self.advanced_limits.acceleration_unit().endswith("/s²") and
            self.advanced_limits.velocity_unit().endswith("/s")
        )

        if unit_s:
            time_factor = 1000
        else:
            raise NotImplementedError("Units other than '/s' and '/s²' are not supported.")

        # Calculate the time required to reach the maximum velocity
        t_acc = velocity_max / acceleration

        # Calculate the distance covered during acceleration and deceleration
        d_acc_dec = acceleration * (t_acc ** 2)

        # Calculate the distance covered during constant velocity
        d_con = distance - d_acc_dec

        if d_con < 0:
            # The object never reaches max velocity; time is calculated based on acceleration only
            time = 2 * (2 * distance / acceleration) ** 0.5
        else:
            # Calculate time taken during the constant velocity phase
            t_con = d_con / velocity_max
            time = 2 * t_acc + t_con  # Total time

        return int(round(time * time_factor))


class AxisNotHomedError(Exception):
    """Exception raised when the axis is not homed."""
    def __init__(self, message="The axis is not homed."):
        super().__init__(message)


class AdvancedMotorLimits(ThorlabsObjectWrapper):
    """
    Manages advanced motor limits for Thorlabs stages.

    Provides an interface to handle advanced motor limits
    parameters such as acceleration and length maximum and minimum.

    Attributes:
        acceleration_unit: Parameter for getting the acceleration units.
        acceleration_max: Parameter for getting the maximum acceleration.
        length_unit: Parameter for getting the length units.
        length_max: Parameter for getting the maximum travel length.
        length_min: Parameter for getting the minimum travel length.
        velocity_unit: Parameter for getting the velocity units.
        velocity_max: Parameter for getting the maximum velocity.
    """
    def __init__(
        self, 
        parent,
        name,
        object_key: Optional[str] = 'AdvancedMotorLimits',
        getter_name: Optional[str] = None,
        setter_name: Optional[str] = None,
        **kwargs
    ):
        super().__init__(parent, name, object_key, getter_name, setter_name, **kwargs)

        self.add_parameter(
            'acceleration_unit',
            get_cmd=lambda: self._get_thorlabs_attribute('AccelerationUnits'),
            docstring='Gets the acceleration units.'
        )

        self.add_parameter(
            'acceleration_max',
            get_cmd=lambda: self._get_thorlabs_decimal('AccelerationMaximum'),
            unit=self.acceleration_unit(),
            docstring='Gets the maximum acceleration for the stage.'
        )

        self.add_parameter(
            'length_unit',
            get_cmd=lambda: self._get_thorlabs_attribute('LengthUnits'),
            docstring='Gets the length units.'
        )

        self.add_parameter(
            'length_max',
            get_cmd=lambda: self._get_thorlabs_decimal('LengthMaximum'),
            unit=self.length_unit(),
            docstring='Gets the maximum travel for the stage.'
        )

        self.add_parameter(
            'length_min',
            get_cmd=lambda: self._get_thorlabs_decimal('LengthMinimum'),
            unit=self.length_unit(),
            docstring='Gets the minimum travel for the stage.'
        )

        self.add_parameter(
            'velocity_unit',
            get_cmd=lambda: self._get_thorlabs_attribute('VelocityUnits'),
            docstring='Gets the velocity units.'
        )

        self.add_parameter(
            'velocity_max',
            get_cmd=lambda: self._get_thorlabs_decimal('AccelerationMaximum'),
            unit=self.velocity_unit(),
            docstring='Gets the maximum velocity for the stage.'
        )


class StepperStatus(StatusBase):
    """
    Represents the status of Thorlabs stepper motor stages.

    Provides an interface for status parameters specific to
    stepper motors like TSTxxx, BSCxxx, and MSTxxx.

    Attributes:
        limit_sw_bwd: Parameter indicating if the stage is at its backward limit.
        limit_sw_fwd: Parameter indicating if the stage is at its forward limit.
        limit_sw: Parameter indicating if the stage is at a software limit.
        interlocked: Parameter indicating if the stage is interlocked.
        motor_connected: Parameter indicating if the motor is connected.
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
            "limit_sw_bwd",
            get_cmd=lambda: self._get_thorlabs_attribute('IsAtBackwardSWLimit'),
            docstring = 'Is the stage at its backward limit.'
        )

        self.add_parameter(
            "limit_sw_fwd",
            get_cmd=lambda: self._get_thorlabs_attribute('IsAtForwardSWLimit'),
            docstring = 'Is the stage at its forward limit.'
        )

        self.add_parameter(
            "limit_sw",
            get_cmd=lambda: self._get_thorlabs_attribute('IsAtSWLimit'),
            docstring = 'Is the stage at its software limit.'
        )

        self.add_parameter(
            'interlocked',
            get_cmd=lambda: self._get_thorlabs_attribute('IsInterlocked'),
            docstring = 'Is the stage interlocked.'
        )

        self.add_parameter(
            'motor_connected',
            get_cmd=lambda: self._get_thorlabs_attribute('IsMotorConnected'),
            docstring = 'Is the motor connected.'
        )


class DCStatus(StatusBase):
    """
    Represents the status of Thorlabs DC motor stages.

    Provides an interface for status parameters specific to
    DC motors like TDCxxx, TBDxxx, and BBDxxx.

    Attributes:
        error_current_limit: Parameter indicating if a current limit error has been triggered.
        error: Parameter indicating if the stage is in an error state.
        error_position: Parameter indicating if a position error is active.
        settled: Parameter indicating if the stage is in a settled state.
        tracking: Parameter indicating if tracking is enabled for the stage.
    """
    def __init__(
        self,
        parent: InstrumentBase,
        name: str,
        object_key: Optional[str] = 'Status',
        getter_name: Optional[str] = None,
        setter_name: Optional[str] = None,
        **kwargs
    ):
        super().__init__(parent, name, object_key, getter_name, setter_name, **kwargs)

        self.add_parameter(
            'error_current_limit',
            get_cmd=lambda: self._get_thorlabs_attribute(IsCurrentLimitError),
            docstring = 'Has current Limit error been triggered.'
        )

        self.add_parameter(
            'error',
            get_cmd=lambda: self._get_thorlabs_attribute(IsError),
            docstring = 'Is the stage in an error state.'
        )

        self.add_parameter(
            'error_position',
            get_cmd=lambda: self._get_thorlabs_attribute(IsPositionError),
            docstring = 'Is position error active.'
        )

        self.add_parameter(
            'settled',
            get_cmd=lambda: self._get_thorlabs_attribute(IsSettled),
            docstring = 'Is stage in a settled state.'
        )

        self.add_parameter(
            'tracking',
            get_cmd=lambda: self._get_thorlabs_attribute(IsTracking),
            docstring = 'Is tracking enabled for this stage.'
        )


class RotationalStageValidator(PyDecimalNumbers):
    """
    Validator for a rotational stage that wraps around, allowing values from a
    given range and values that wrap around 360 degrees. For example, initializing
    with (-4, 4) allows values from 356 to 360 and 0 to 4, considering a wrap at 360 degrees.
    
    Args:
        min_value: Minimum allowed value in the non-wrap range.
        max_value: Maximum allowed value in the non-wrap range.
        wrap_at: The value at which the range wraps. For a standard rotational stage, this would be 360 degrees.
    
    Methods:
        validate: Validates if a value is within the allowed range considering wrap-around.
    """
    def __init__(self, min_value: float, max_value: float, wrap_at: float = 360) -> None:
        super().__init__(min_value, max_value)
        self.wrap_at = wrap_at
        self._valid_values = (min_value, max_value)  # This needs to be revised to provide valid values appropriately.

    def validate(self, value: float, context: str = "") -> None:
        """
        Validates that the value is within the allowed range, considering the wrap-around.

        Args:
            value: The value to validate.
            context: Additional context for validation error messages.
        """
        if not isinstance(value, self.validtypes):
            raise TypeError(f"{value!r} is not a valid number type; {context}")

        # Normalize the value to be within the 0 to wrap_at range
        normalized_value = value % self.wrap_at

        # Check if the value is within the wrapped range
        if self._min_value < 0:
            wrap_min = self.wrap_at + self._min_value
            if not (wrap_min <= normalized_value <= self.wrap_at or 0 <= normalized_value <= self._max_value):
                raise ValueError(f"{value!r} is invalid; {context}")
        else:
            if not (self._min_value <= normalized_value <= self._max_value):
                raise ValueError(f"{value!r} is invalid; {context}")

    def __repr__(self) -> str:
        return f"<RotationalStageValidator wrapping at {self.wrap_at} with range ({self._min_value}, {self._max_value})>"

