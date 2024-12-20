import logging
from typing import Optional

from qcodes.utils.validators import Enum, Numbers

from .qcodes_thorlabs_integration import PyDecimalNumbers, ThorlabsObjectWrapper


log = logging.getLogger(__name__)


class IDCPIDParameters:
    """
    IDCPIDParameters interface definition.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class HomeParameters(ThorlabsObjectWrapper):
    """
    Provides an interface for homing parameters of a Thorlabs motion stage.
    
    Attributes:
        direction: Direction to travel to find the home position.
        limit_switch: Limit switch direction parameter.
        offset_distance: Home offset distance.
        velocity: Homing velocity.
    """    
    def __init__(
        self, 
        parent,
        name,
        object_key: Optional[str] = None,
        getter_name: Optional[str] = 'GetHomingParams',
        setter_name: Optional[str] = 'SetHomingParams',
        length_unit: Optional[str] = None,
        velocity_unit: Optional[str] = None,
        **kwargs
    ):    
        super().__init__(parent, name, object_key, getter_name, setter_name, **kwargs)

        if hasattr(self.parent, 'advanced_limits'):
            advanced_limits = self.parent.advanced_limits

            if length_unit is None:
                length_unit = advanced_limits.length_unit()
            if velocity_unit is None:
                velocity_unit =     advanced_limits.velocity_unit()

        self.add_parameter(
            "direction",
            get_cmd=lambda: self._get_thorlabs_enum('Direction'),
            set_cmd=lambda x: self._set_thorlabs_enum(x, 'Direction'),
            docstring="Direction to travel to find the home position.",
            vals=Enum('Clockwise', 'CounterClockwise')
        )

        self.add_parameter(
            "limit_switch",
            get_cmd=lambda: self._get_thorlabs_enum('LimitSwitch'),
            set_cmd=lambda x: self._set_thorlabs_enum(x, 'LimitSwitch'),
            docstring="Limit switch direction parameter.",
            vals=Enum('Ignore', 'ClockwiseHard', 'CounterClockwiseHard')
        )

        self.add_parameter(
            "offset_distance",
            get_cmd=lambda: self._get_thorlabs_decimal('OffsetDistance'),
            set_cmd=lambda x: self._set_thorlabs_decimal(x, 'OffsetDistance'),
            unit=length_unit,
            docstring="Home offset distance."
        )

        self.add_parameter(
            "velocity",
            get_cmd=lambda: self._get_thorlabs_decimal('Velocity'),
            set_cmd=lambda x: self._set_thorlabs_decimal(x, 'Velocity'),
            unit=velocity_unit,
            docstring="Homing velocity."
        )


class VelocityParameters(ThorlabsObjectWrapper):
    """
    Provides an interface for velocity parameters of a Thorlabs motion stage.
    
    Attributes:
        acceleration: Gets or sets the acceleration.
        velocity_min: Gets the minimum velocity.
        velocity_max: Gets the maximum velocity.
    """
    def __init__(
        self, 
        parent,
        name,
        object_key: Optional[str] = None,
        getter_name: Optional[str] = 'GetVelocityParams',
        setter_name: Optional[str] = 'SetVelocityParams',
        acceleration_unit: Optional[str] = None,
        acceleration_min = 0,
        acceleration_max = None,
        velocity_unit: Optional[str] = None,
        velocity_max = None,
        **kwargs
    ):    
        super().__init__(parent, name, object_key, getter_name, setter_name, **kwargs)

        if hasattr(self.parent, 'advanced_limits'):
            advanced_limits = self.parent.advanced_limits

            if velocity_unit is None:
                velocity_unit = advanced_limits.velocity_unit()
            if acceleration_unit is None:
                acceleration_unit = advanced_limits.acceleration_unit()
            if acceleration_max is None:
                acceleration_max = advanced_limits.acceleration_max()
            if velocity_max is None:
                velocity_max = advanced_limits.velocity_max()

        self.add_parameter(
            "acceleration",
            get_cmd=lambda: self._get_thorlabs_decimal('Acceleration'),
            set_cmd=lambda x: self._set_thorlabs_decimal(x, 'Acceleration'),
            unit=acceleration_unit,
            vals=PyDecimalNumbers(acceleration_min, acceleration_max),
            docstring="Gets or sets the acceleration."
        )

        self.add_parameter(
            "velocity_min",
            get_cmd=lambda: self._get_thorlabs_decimal('MinVelocity'),
            unit=velocity_unit,
            docstring="Gets the minimum velocity."
        )

        self.add_parameter(
            "velocity_max",
            get_cmd=lambda: self._get_thorlabs_decimal('MaxVelocity'),
            set_cmd=lambda x: self._set_thorlabs_decimal(x, 'MaxVelocity'),
            unit=velocity_unit,
            vals=PyDecimalNumbers(self.velocity_min(), velocity_max),
            docstring="Gets the maximum velocity."
        )


class LimitSwitchParametersBase(ThorlabsObjectWrapper):
    """
    Base class for limit switch parameters of a Thorlabs motion stage.
    
    Attributes:
        hard_limit_action_ccw: Action on hitting the counter-clockwise hardware limit.
        hard_limit_action_cw: Action on hitting the clockwise hardware limit.
        soft_limit_action: Action on hitting the soft limit.
    """
    def __init__(
        self, 
        parent,
        name,
        object_key: Optional[str] = None,
        getter_name: Optional[str] = 'GetLimitSwitchParams',
        setter_name: Optional[str] = 'SetLimitSwitchParams',
        **kwargs
    ):    
        super().__init__(parent, name, object_key, getter_name, setter_name, **kwargs)

        self.add_parameter(
            "hard_limit_action_ccw",
            get_cmd=lambda: self._get_thorlabs_enum('AnticlockwiseHardwareLimit'),
            set_cmd=lambda x: self._set_thorlabs_enum(x, 'AnticlockwiseHardwareLimit'),
            vals=Enum('Ignore', 'Make', 'Break', 'Home_Make', 'Home_Break', 'PMD_Index')
        )

        self.add_parameter(
            "hard_limit_action_cw",
            get_cmd=lambda: self._get_thorlabs_enum('ClockwiseHardwareLimit'),
            set_cmd=lambda x: self._set_thorlabs_enum(x, 'ClockwiseHardwareLimit'),
            vals=Enum('Ignore', 'Make', 'Break', 'Home_Make', 'Home_Break', 'PMD_Index')
        )

        self.add_parameter(
            "soft_limit_action",
            get_cmd=lambda: self._get_thorlabs_enum('SoftLimitModes'),
            set_cmd=lambda x: self._set_thorlabs_enum(x, 'SoftLimitModes'),
            vals=Enum('Ignore', 'Make', 'Break', 'Home_Make', 'Home_Break', 'PMD_Index')
        )


class LimitSwitchParameters(LimitSwitchParametersBase):
    """
    Provides an interface for limit switch parameters of a Thorlabs motion stage.
    
    Attributes:
        position_ccw: Counter-clockwise limit switch position.
        position_cw: Clockwise limit switch position.
    """
    def __init__(
        self, 
        parent,
        name,
        object_key: Optional[str] = None,
        getter_name: Optional[str] = 'GetLimitSwitchParams',
        setter_name: Optional[str] = 'SetLimitSwitchParams',
        length_unit: Optional[str] = None,
        length_min = None,
        length_max = None,
        **kwargs
    ):    
        super().__init__(parent, name, object_key, getter_name, setter_name, **kwargs)

        if hasattr(self.parent, 'advanced_limits'):
            advanced_limits = self.parent.advanced_limits

            if length_unit is None:
                length_unit = advanced_limits.length_unit()
            if length_min is None:
                length_min = advanced_limits.length_min()
            if length_max is None:
                length_max = advanced_limits.length_max()

        if length_max > length_min:
            vals = PyDecimalNumbers(length_min, length_max)
        else:
            vals = None

        self.add_parameter(
            "position_ccw",
            get_cmd=lambda: self._get_thorlabs_decimal('AnticlockwisePosition'),
            set_cmd=lambda x: self._set_thorlabs_decimal(x, 'AnticlockwisePosition'),
            unit=length_unit,
            vals=vals,
        )

        self.add_parameter(
            "position_cw",
            get_cmd=lambda: self._get_thorlabs_decimal('ClockwisePosition'),
            set_cmd=lambda x: self._set_thorlabs_decimal(x, 'ClockwisePosition'),
            unit=length_unit,
            vals=vals,
        )


class JogParametersBase(ThorlabsObjectWrapper):
    """
    Provides an interface to the common Jog Parameters required to perform a 
    Jog Operation on a Thorlabs motion stage.
    
    Attributes:
    """
    def __init__(
        self, 
        parent,
        name,
        object_key: Optional[str] = None,
        getter_name: Optional[str] = 'GetJogParams',
        setter_name: Optional[str] = 'SetJogParams',
        **kwargs
    ):
        super().__init__(parent, name, object_key, getter_name, setter_name, **kwargs)

        self.add_parameter(
            "jog_mode",
            get_cmd=lambda: self._get_thorlabs_enum('JogMode'),
            set_cmd=lambda x: self._set_thorlabs_enum(x, 'JogMode'),
            docstring="Jog Mode",
            # vals=Enum('Continuous', 'SingleStep')
            vals=Enum('ContinuousHeld', 'SingleStep', 'ContinuousUnheld')

        )

        self.add_parameter(
            "stop_mode",
            get_cmd=lambda: self._get_thorlabs_enum('StopMode'),
            set_cmd=lambda x: self._set_thorlabs_enum(x, 'StopMode'),
            docstring="Stop Mode",
            vals=Enum('Immediate', 'Profiled')

        )


class JogParameters(JogParametersBase):
    """
    Provides an interface to the Jog Parameters (in Real World Units)
    required to perform a Jog Operation required to perform a 
    Jog Operation on a Thorlabs motion stage.
    
    Attributes:
    """
    def __init__(
        self, 
        parent,
        name,
        object_key: Optional[str] = None,
        getter_name: Optional[str] = 'GetJogParams',
        setter_name: Optional[str] = 'SetJogParams',
        length_unit: Optional[str] = None,        
        **kwargs
    ):
        super().__init__(parent, name, object_key, getter_name, setter_name, **kwargs)

        if hasattr(self.parent, 'advanced_limits'):
            advanced_limits = self.parent.advanced_limits

            if length_unit is None:
                length_unit = advanced_limits.length_unit()

        self.add_parameter(
            "step_size",
            get_cmd=lambda: self._get_thorlabs_decimal('StepSize'),
            set_cmd=lambda x: self._set_thorlabs_decimal(x, 'StepSize'),
            unit=length_unit,
            docstring="Stop Mode",
        )
