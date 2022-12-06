from typing import Any
from qcodes.parameters import Parameter, Group, GroupParameter, ParamRawDataType
from qcodes.instrument import InstrumentBase


class GroupGetParameter(Parameter):
    """
    Similar to GroupParameter but the set_cmd is still used to set the parameter.

    almost a textbook example of refused bequest anti-pattern
    """

    def __init__(
        self,
        name: str,
        instrument: InstrumentBase | None = None,
        initial_value: float | int | str | None = None,
        **kwargs: Any,
    ) -> None:

        if "get_cmd" in kwargs:
            raise ValueError("A GroupGetParameter does not use 'get_cmd' kwarg")

        self._group: Group | None = None
        self._initial_value = initial_value

        super().__init__(name, instrument=instrument, **kwargs)

    @property
    def group(self) -> Group | None:
        """
        The group that this parameter belongs to.
        """
        return self._group

    def get_raw(self) -> ParamRawDataType:
        if self.group is None:
            raise RuntimeError("Trying to get Group value but no group defined")
        self.group.update()
        return self.cache.raw_value

