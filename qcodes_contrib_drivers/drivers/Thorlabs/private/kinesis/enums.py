import enum


class KinesisHWType(enum.Enum):
    BenchtopBrushlessMotor20X = 73
    BenchtopBrushlessMotor30X = 103
    BenchtopDCServo1Ch = 43
    BenchtopDCServo3Ch = 79
    BenchtopNanoTrak = 22
    BenchtopPiezo1Ch = 41
    BenchtopPiezo3Ch = 71
    BenchtopPrecisionPiezo1Ch = 44
    BenchtopPrecisionPiezo2Ch = 95
    BenchtopStepperMotor1Ch = 40
    BenchtopStepperMotor3Ch = 70
    BenchtopVoiceCoil = 100
    FilterFlipper = 37
    FilterWheel = 47
    IntegratedPrecisionPiezo = 92
    IntegratedXStage = 105
    IntegratedXYStage = 101
    KCubeBrushlessMotor = 28
    KCubeDCServo = 27
    KCubeInertialMotor1Ch = 74
    KCubeInertialMotor4Ch = 97
    KCubeLaserDiode = 98
    KCubeLaserSource = 56
    KCubeNanoTrak = 57
    KCubePiezo = 29
    KCubePositionAligner = 69
    KCubeSolenoid = 68
    KCubeStepperMotor = 26
    LongTravelStage = 45
    CageRotator = 55
    LabJack490 = 46
    LabJack050 = 49
    ModularRack = 48
    # ModularRack = 75  # ??
    ModularBrushless = 54
    ModularNanoTrak = 52
    ModularPiezo = 51
    ModularStepperMotor = 50
    Polarizer = 38
    PositionReadoutEncoder = 111
    TCubeBrushlessMotor = 67
    TCubeDCServo = 83
    TCubeInertialMotor = 65
    TCubeLaserSource = 86
    TCubeLaserDiode = 64
    TCubeNanoTrak = 82
    TCubeQuad = 89
    TCubeSolenoid = 85
    TCubeStepperMotor = 80
    TCubeStrainGauge = 84
    TCubeTEC = 87
    VerticalStage = 24


class MotorTypes(enum.Enum):
    """Values that represent different Motor Types."""
    NotMotor = 0
    """Not a motor."""
    DCMotor = 1
    """Motor is a DC Servo motor."""
    StepperMotor = 2
    """Motor is a Stepper Motor."""
    BrushlessMotor = 3
    """Motor is a Brushless Motor."""
    CustomMotor = 100
    """Motor is a custom motor."""


class UnitType(enum.Enum):
    Distance = 0
    Velocity = 1
    Acceleration = 2


class JogModes(enum.Enum):
    JogModeUndefined = 0
    """Undefined."""
    Continuous = 1
    """Continuous jogging."""
    SingleStep = 2
    """Jog 1 step at a time."""


class StopModes(enum.Enum):
    StopModeUndefined = 0
    """Undefined."""
    Immediate = 1
    """Stops immediate."""
    Profiled = 2
    """Stops using a velocity profile."""


class MovementModes(enum.Enum):
    LinearRange = 0
    """Fixed Limit, cannot rotate."""
    RotationalUnlimited = 1
    """Ranges between +/- Infinity."""
    RotationalWrapping = 2
    """Ranges between 0 to 360 with wrapping."""


class MovementDirections(enum.Enum):
    Quickest = 0
    """Always takes the shortest path."""
    Forwards = 1
    "Always moves forwards."
    Backwards = 2
    "Always moves backwards."


class TravelDirection(enum.Enum):
    TravelDirectionDisabled = 0
    """Disabled or Undefined."""
    Forwards = 1
    """Move in a Forward direction."""
    Reverse = 2
    """Move in a Backward / Reverse direction."""


class HomeLimitSwitchDirection(enum.Enum):
    """Values that represent Limit Switch Directions."""
    LimitSwitchDirectionUndefined = 0
    """Undefined."""
    ReverseLimitSwitch = 1
    """Limit switch in forward direction."""
    ForwardLimitSwitch = 1
    """Limit switch in reverse direction."""
