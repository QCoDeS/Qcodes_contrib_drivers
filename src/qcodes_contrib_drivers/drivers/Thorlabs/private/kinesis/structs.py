import ctypes
import enum

from . import enums


class StructureWithEnums(ctypes.Structure):
    """Add missing enum feature to ctypes Structures.

    Taken from https://gist.github.com/christoph2/9c390e5c094796903097
    """
    _map: dict[str, enum.EnumMeta] = {}

    def __getattribute__(self, name):
        _map = ctypes.Structure.__getattribute__(self, '_map')
        value = ctypes.Structure.__getattribute__(self, name)
        if name in _map:
            EnumClass = _map[name]
            if isinstance(value, ctypes.Array):
                return [EnumClass(x) for x in value]
            else:
                return EnumClass(value)
        else:
            return value

    def __str__(self):
        result = ["struct {0} {{".format(self.__class__.__name__)]
        for field in self._fields_:
            attr, attrType = field
            if attr in self._map:
                attrType = self._map[attr]
            value = getattr(self, attr)
            result.append("    {0} [{1}] = {2!r};".format(
                attr, attrType.__name__, value)
            )
        result.append("};")
        return '\n'.join(result)

    __repr__ = __str__


class VelocityParameters(ctypes.Structure):
    """Structure containing the velocity parameters.

    Moves are performed using a velocity profile. The move starts at
    the Minimum Velocity (always 0 at present) and accelerated to the
    Maximum Velocity using the defined Acceleration. The move is
    usually completed using a similar deceleration.

    Fields
    ------
    acceleration : int
        The acceleration in Device Units.
    maxVelocity : int
        The maximum velocity in Device Units.
    minVelocity : int
        The minimum velocity in Device Units usually 0.
    """
    _fields_ = [('acceleration', ctypes.c_int),
                ('maxVelocity', ctypes.c_int),
                ('minVelocity', ctypes.c_int)]


class JogParameters(StructureWithEnums):
    """Structure containing the jog parameters.

    Jogs are performed using a velocity profile over small fixed
    distances. The move starts at the Minimum Velocity (always 0 at
    present) and accelerated to the Maximum Velocity using the defined
    Acceleration. The move is usually completed using a similar
    deceleration.

    Fields
    ------
    mode : class:`enums.JogModes`
        The jogging mode.

        The mode can be one of the following:

        +---+-------------------------------------------------------+
        |   | Continuous Jogging                                    |
        | 1 | The device will continue moving until the end stop is |
        |   | reached or the device button is raised.               |
        +---+-------------------------------------------------------+
        |   | Step Jog                                              |
        | 2 | The device will move by a fixed amount as defined in  |
        |   | this structure.                                       |
        +---+-------------------------------------------------------+

    stepSize : uint
        The step size in Device Units.
    stopMode : :class:`enums.StopModes`
        The Stop Mode.

        The Stop Mode determines how the jog should stop.

        +---+-----------+
        | 1 | Immediate |
        +---+-----------+
        | 2 | Profiled. |
        +---+-----------+

    velParams : VelocityParameters
        The VelocityParameters for the jog.
    """
    _fields_ = [('mode', ctypes.c_int),
                ('stepSize', ctypes.c_uint),
                ('stopMode', ctypes.c_int),
                ('velParams', VelocityParameters)]

    _map = {'mode': enums.JogModes, 'stopMode': enums.StopModes}


class HomingParameters(StructureWithEnums):
    """Structure containing the homing parameters.

    Homing is performed using a constant velocity. The home starts
    moving the motor in the defined direction until the limit switch is
    detected. The device will then back off from the limit switch by
    the defined offset distance.

    Fields
    ------
    direction : int
        The Homing direction sense

        The Homing Operation will always move in a decreasing position
        sense, but the actuator gearing may change the actual physical
        sense. Therefore the homing direction can correct the physical
        sense.

        +---+------------+
        | 1 | Forwards   |
        +---+------------+
        | 2 | Backwards. |
        +---+------------+

    limitSwitch : int
        The limit switch direction.

        The limit switch which will be hit when homing completes.

        +---+-----------------------+
        | 1 | Forward Limit Switch  |
        +---+-----------------------+
        | 2 | Reverse Limit Switch. |
        +---+-----------------------+

    offsetDistance : uint
        Distance of home from limit in small indivisible units.
    velocity : uint
        The velocity in small indivisible units.

        As the homing operation is performed at a much lower velocity,
        to achieve accuracy, a profile is not required.
    """
    _fields_ = [('direction', ctypes.c_int),
                ('limitSwitch', ctypes.c_int),
                ('offsetDistance', ctypes.c_uint),
                ('velocity', ctypes.c_uint)]

    _map = {'direction': enums.TravelDirection,
            'limitSwitch': enums.HomeLimitSwitchDirection}
