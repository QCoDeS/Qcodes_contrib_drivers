import enum
from typing import Tuple

import qcodes.utils.validators as vals
from qcodes import Instrument

from .APT import Thorlabs_APT, ThorlabsHWType


class RotationDirection(enum.Enum):
    """Constants for the rotation direction of Thorlabs K10CR1 rotator"""
    FORWARD = "fwd"
    REVERSE = "rev"


class HomeLimitSwitch(enum.Enum):
    """Constants for the home limit switch of Thorlabs K10CR1 rotator"""
    REVERSE = "rev"
    FORWARD = "fwd"


class Thorlabs_K10CR1(Instrument):
    """
    Instrument driver for the Thorlabs K10CR1 rotator.

    Args:
        name: Instrument name.
        device_id: ID for the desired rotator.
        apt: Thorlabs APT server.

    Attributes:
        apt: Thorlabs APT server.
        serial_number: Serial number of the device.
        model: Model description.
        version: Firmware version.
    """

    def __init__(self, name: str, device_id: int, apt: Thorlabs_APT, **kwargs):
        super().__init__(name, **kwargs)

        # Save APT server reference
        self.apt = apt

        # initialization
        self.serial_number = self.apt.get_hw_serial_num_ex(ThorlabsHWType.K10CR1, device_id)
        self.apt.init_hw_device(self.serial_number)
        self.model, self.version, _ = self.apt.get_hw_info(self.serial_number)

        # Set velocity and move-home parameters to previous values. Otherwise the velocity is very
        # very low and it is not the velocity stored in the parameters... For whatever reason?
        self._set_velocity_parameters()
        self._set_home_parameters()

        # Helpers
        direction_val_mapping = {RotationDirection.FORWARD: 1,
                                 RotationDirection.FORWARD.value: 1,
                                 RotationDirection.REVERSE: 2,
                                 RotationDirection.REVERSE.value: 2}
        lim_switch_val_mapping = {HomeLimitSwitch.REVERSE: 1,
                                  HomeLimitSwitch.REVERSE.value: 1,
                                  HomeLimitSwitch.FORWARD: 4,
                                  HomeLimitSwitch.FORWARD.value: 4}

        # PARAMETERS
        # Position
        self.add_parameter("position",
                           get_cmd=self._get_position,
                           set_cmd=self._set_position,
                           vals=vals.Numbers(0, 360),
                           unit=u"\u00b0",
                           label="Position")
        self.add_parameter("position_async",
                           get_cmd=None,
                           set_cmd=self._set_position_async,
                           vals=vals.Numbers(0, 360),
                           unit=u"\u00b0",
                           label="Position")

        # Velocity Parameters
        self.add_parameter("velocity_min",
                           set_cmd=self._set_velocity_min,
                           get_cmd=self._get_velocity_min,
                           vals=vals.Numbers(0, 25),
                           unit=u"\u00b0/s",
                           label="Minimum Velocity")
        self.add_parameter("velocity_acceleration",
                           set_cmd=self._set_velocity_acceleration,
                           get_cmd=self._get_velocity_acceleration,
                           vals=vals.Numbers(0, 25),
                           unit=u"\u00b0/s\u00b2",
                           label="Acceleration")
        self.add_parameter("velocity_max",
                           set_cmd=self._set_velocity_max,
                           get_cmd=self._get_velocity_max,
                           vals=vals.Numbers(0, 25),
                           unit=u"\u00b0/s",
                           label="Maximum Velocity")

        # Move home parameters
        self.add_parameter("move_home_direction",
                           set_cmd=self._set_home_direction,
                           get_cmd=self._get_home_direction,
                           val_mapping=direction_val_mapping,
                           label="Direction for Moving Home")
        self.add_parameter("move_home_limit_switch",
                           set_cmd=self._set_home_lim_switch,
                           get_cmd=self._get_home_lim_switch,
                           val_mapping=lim_switch_val_mapping,
                           label="Limit Switch for Moving Home")
        self.add_parameter("move_home_velocity",
                           set_cmd=self._set_home_velocity,
                           get_cmd=self._get_home_velocity,
                           vals=vals.Numbers(0, 25),
                           unit=u"\u00b0/s",
                           label="Velocity for Moving Home")
        self.add_parameter("move_home_zero_offset",
                           set_cmd=self._set_home_zero_offset,
                           get_cmd=self._get_home_zero_offset,
                           vals=vals.Numbers(0, 360),
                           unit=u"\u00b0",
                           label="Zero Offset for Moving Home")

        # FUNCTIONS
        # Stop motor
        self.add_function("stop",
                          call_cmd=self._stop,
                          args=[])

        # Moving direction
        self.add_function("move_direction",
                          call_cmd=self._move_direction,
                          args=[vals.Enum(*direction_val_mapping)],
                          arg_parser=lambda val: direction_val_mapping[val])

        # Enable/disable
        self.add_function("enable",
                          call_cmd=self._enable,
                          args=[])
        self.add_function("disable",
                          call_cmd=self._disable,
                          args=[])

        # Move home
        self.add_function("move_home",
                          call_cmd=self._move_home,
                          args=[])
        self.add_function("move_home_async",
                          call_cmd=self._move_home_async,
                          args=[])

        # print connect message
        self.connect_message()

    def get_idn(self):
        """Returns hardware information of the device."""
        return {"vendor": "Thorlabs", "model": self.model,
                "firmware": self.version, "serial": self.serial_number}

    def _get_position(self) -> float:
        return self.apt.mot_get_position(self.serial_number)

    def _set_position(self, position: float):
        self.apt.mot_move_absolute_ex(self.serial_number, position, True)

    def _set_position_async(self, position: float):
        self.apt.mot_move_absolute_ex(self.serial_number, position, False)

    def _get_velocity_parameters(self) -> Tuple[float, float, float]:
        return self.apt.mot_get_velocity_parameters(self.serial_number)

    def _set_velocity_parameters(self,
                                 min_vel: float = None, accn: float = None, max_vel: float = None):
        if min_vel is None or accn is None or max_vel is None:
            old_min_vel, old_accn, old_max_vel = self._get_velocity_parameters()
            if min_vel is None:
                min_vel = old_min_vel
            if accn is None:
                accn = old_accn
            if max_vel is None:
                max_vel = old_max_vel
        return self.apt.mot_set_velocity_parameters(self.serial_number, min_vel, accn, max_vel)

    def _get_velocity_min(self) -> float:
        min_vel, _, _ = self._get_velocity_parameters()
        return min_vel

    def _set_velocity_min(self, min_vel: float):
        self._set_velocity_parameters(min_vel=min_vel)

    def _get_velocity_acceleration(self) -> float:
        _, accn, _ = self._get_velocity_parameters()
        return accn

    def _set_velocity_acceleration(self, accn: float):
        self._set_velocity_parameters(accn=accn)

    def _get_velocity_max(self) -> float:
        _, _, max_vel = self._get_velocity_parameters()
        return max_vel

    def _set_velocity_max(self, max_vel: float):
        self._set_velocity_parameters(max_vel=max_vel)

    def _get_home_parameters(self) -> Tuple[int, int, float, float]:
        return self.apt.mot_get_home_parameters(self.serial_number)

    def _set_home_parameters(self, direction: int = None, lim_switch: int = None,
                             velocity: float = None, zero_offset:float = None):
        if direction is None or lim_switch is None or velocity is None or zero_offset is None:
            old_direction, old_lim_switch, old_velocity, old_zero_offset = self._get_home_parameters()
            if direction is None:
                direction = old_direction
            if lim_switch is None:
                lim_switch = old_lim_switch
            if velocity is None:
                velocity = old_velocity
            if zero_offset is None:
                zero_offset = old_zero_offset

        return self.apt.mot_set_home_parameters(self.serial_number,
                                                direction, lim_switch, velocity, zero_offset)

    def _get_home_direction(self) -> int:
        direction, _, _, _ = self._get_home_parameters()
        return direction

    def _set_home_direction(self, direction: int):
        self._set_home_parameters(direction=direction)

    def _get_home_lim_switch(self) -> int:
        _, lim_switch, _, _ = self._get_home_parameters()
        return lim_switch

    def _set_home_lim_switch(self, lim_switch: int):
        self._set_home_parameters(lim_switch=lim_switch)

    def _get_home_velocity(self) -> float:
        _, _, velocity, _ = self._get_home_parameters()
        return velocity

    def _set_home_velocity(self, velocity: float):
        self._set_home_parameters(velocity=velocity)

    def _get_home_zero_offset(self) -> float:
        _, _, _, zero_offset = self._get_home_parameters()
        return zero_offset

    def _set_home_zero_offset(self, zero_offset: float):
        self._set_home_parameters(zero_offset=zero_offset)

    def _stop(self):
        self.apt.mot_stop_profiled(self.serial_number)

    def _move_direction(self, direction: int):
        self.apt.mot_move_velocity(self.serial_number, direction)

    def _enable(self):
        self.apt.enable_hw_channel(self.serial_number)

    def _disable(self):
        self.apt.disable_hw_channel(self.serial_number)

    def _move_home(self):
        self.apt.mot_move_home(self.serial_number, True)

    def _move_home_async(self):
        self.apt.mot_move_home(self.serial_number, False)
