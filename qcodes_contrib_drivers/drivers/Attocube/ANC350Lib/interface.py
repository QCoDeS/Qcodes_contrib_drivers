"""Collection of shared classes used by multiple versions of ANC350Lib

Author:
    Lukas Lankes, Forschungszentrum Jülich GmbH / ZEA-2, l.lankes@fz-juelich.de
"""

from abc import ABC, abstractmethod
from enum import IntEnum
from typing import List, Optional
import warnings

__all__ = ["ANC350LibError", "ANC350LibDeviceType", "ANC350LibExternalTriggerMode",
           "ANC350LibTriggerPolarity", "ANC350LibActuatorType", "ANC350LibAmplitudeControlMode",
           "ANC350LibSignalEdge", "ANC350LibTriggerInputMode", "ANC350LibTriggerOutputMode"]


class ANC350LibError(Exception, ABC):
    """Base class for exceptions occurring in ANC350v?Lib-classes

    Attributes:
        message: Error message
        code: Error code from dll (or None)
    """
    SUCCESS_CODES: List[int] = [0]
    WARNING_CODES: List[int] = []

    def __init__(self, message: Optional[str], code: Optional[int]):
        """Create instance of ``ANC350LibError``

        Args:
            message: Error message
            code: Error code from dll
        """
        self.code = code
        self.message = self._process_code_message(code, message)

        super().__init__(self.message)

    @classmethod
    def check_error(cls, code: int, function: Optional[str] = None) -> None:
        """Checks the error code and raises an exception, if necessary

        If the error code is in ``SUCCESS_CODES``, no exception is raises. Same applies if the code
        is contained in ``WARNING_CODES``. Then, a warning is generated. If neither of both is the
        case, an exception is generated based on the error code.

        Args:
            code: Occurred error code
            function: Dll-function that returned the error code

        Raises:
            If code is not in ``SUCCESS_CODES`` or ``WARNING_CODES``, an ANC350LibError is raised
        """
        if code not in cls.SUCCESS_CODES:
            if function:
                function = "In function " + function
            if code in cls.WARNING_CODES:
                warnings.warn(cls._process_code_message(code, function))
            else:
                raise cls(function, code)

    @classmethod
    def _process_code_message(cls, code: Optional[int], message: Optional[str]) -> str:
        """Converts error code and message into a more detailed error message

        Args:
            code: Occurred error code
            message: Error message

        Returns:
            Detailed error message
        """
        message_out = "Error in ANC350Lib"
        if code is not None:
            message_out += f" ({code}): "
            message_out += cls._get_message_for_code(code) or "Unknown error"
        if message:
            message_out += ": " + message

        return message_out

    @classmethod
    @abstractmethod
    def _get_message_for_code(cls, code: int) -> Optional[str]:
        """Override this function to convert return codes into error messages

        Args:
            code: Occurred error code

        Returns:
            Corresponding error message for code
        """
        raise NotImplementedError()


class ANC350LibDeviceType(IntEnum):
    """An enumeration for possible values of the return value's first component in
    ``ANC350v3Lib.get_device_info`` and ``ANC350v4Lib.get_device_info``"""
    Res = 0  # RES sensors
    Num = 1  # NUM sensors
    Fps = 2  # FPS sensors
    Nothing = 3  # No device / invalid


class ANC350LibExternalTriggerMode(IntEnum):
    """An enumeration for possible values of parameter "mode" in
    ``ANC350v3Lib.configure_ext_trigger`` and ``ANC350v4Lib.configure_ext_trigger``."""
    Disable = 0
    Quadrature = 1
    Trigger = 2


class ANC350LibTriggerPolarity(IntEnum):
    """An enumeration for possible values of parameter "polarity" in
    ``ANC350v2Lib.set_trigger_polarity``, ``ANC350v3Lib.configure_rng_trigger_pol`` and
    ``ANC350v4Lib.configure_rng_trigger_pol``."""
    Low = 0
    High = 1


class ANC350LibActuatorType(IntEnum):
    """An enumeration of possible return values ``ANC350v3Lib.get_actuator_type`` and
    ``ANC350v4Lib.get_actuator_type``."""
    Linear = 0  # Actuator is of linear type
    Goniometer = 1  # Actuator is of goniometer type
    Rotator = 2  # Actuator is of rotator type


class ANC350LibAmplitudeControlMode(IntEnum):
    """An enumeration for possible values of parameter "mode" in
    ``ANC350v2Lib.set_amplitude_control_mode``."""
    Speed = 0
    Amplitude = 1
    StepSize = 2


class ANC350LibSignalEdge(IntEnum):
    """An enumeration for possible values of parameter "edge" in
    ``ANC350v2Lib.set_external_step_input_edge``."""
    Rising = 0
    Falling = 1


class ANC350LibTriggerInputMode(IntEnum):
    """An enumeration for possible values of parameter "mode" in
    ``ANC350v2Lib.set_input_trigger_mode``."""
    Disable = 0  # The inputs don’t trigger anything
    Quadratur = 1  # Three pairs of trigger in signals are used to accept AB-Signals for relative positioning
    Coarse = 2  # The trigger in signals are used to generate coarse steps


class ANC350LibTriggerOutputMode(IntEnum):
    """An enumeration for possible values of parameter "mode" in
    ``ANC350v2Lib.set_output_trigger_mode``."""
    Disable = 0  # The inputs don’t trigger anything
    Position = 1  # The Trigger Outputs reacts to the defined position ranges with the selected polarity
    Quadratur = 2  # Three pairs of trigger out signals are used to signal relative movement as AB-signals
    IcHaus = 3  # The trigger out signals are used to output the internal position signal of num-sensors
