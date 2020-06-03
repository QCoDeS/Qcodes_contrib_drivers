from abc import ABC, abstractmethod
from enum import IntEnum
from typing import Optional
import warnings

_all__ = ["ANC350LibError", "ANC350DeviceType", "ANC350TriggerMode", "ANC350TriggerPolarity",
          "ANC350ActuatorType"]


class ANC350LibError(Exception, ABC):
    SUCCESS_CODES = [0]
    WARNING_CODES = []
    ERROR_MESSAGES = {0: "Success"}

    def __init__(self, message: str, code: Optional[int]):
        self.code = code
        self.message = self._process_code_message(code, message)

        super().__init__(self.message)

    @classmethod
    def __new__(cls, *args, **kwargs):
        if cls is ANC350LibError:
            # Prevent from instantiating the abstract class
            raise TypeError("Can't instantiate abstract class {} directly".format(
                cls.__name__))
        return super().__new__(*args, **kwargs)

    @classmethod
    def check_error(cls, code: int, function: Optional[str] = None) -> None:
        if code not in cls.SUCCESS_CODES:
            if function:
                function = "In function " + function
            if code in cls.WARNING_CODES:
                warnings.warn(cls._process_code_message(code, function))
            else:
                raise cls(function, code)

    @classmethod
    def _process_code_message(cls, code: Optional[int], message: Optional[str]) -> str:
        message_out = "Error in ANC350 library"
        if code is not None:
            message_out += " ({}): ".format(code)
            if code in cls.ERROR_MESSAGES:
                message_out += cls.ERROR_MESSAGES[code]
            else:
                message_out += "Unknown error"
        if message:
            message_out += ": " + message

        return message_out


class ANC350DeviceType(IntEnum):
    Res = 0  # RES sensors
    Num = 1  # NUM sensors
    Fps = 2  # FPS sensors
    Nothing = 3  # No device / invalid

    @classmethod
    def _missing_(cls, value):
        return cls.Nothing


class ANC350TriggerMode(IntEnum):
    Disable = 0
    Quadrature = 1
    Trigger = 2


class ANC350TriggerPolarity(IntEnum):
    Low = 0
    High = 1


class ANC350ActuatorType(IntEnum):
    Linear = 0  # Actuator is of linear type
    Goniometer = 1  # Actuator is of goniometer type
    Rotator = 2  # Actuator is of rotator type
