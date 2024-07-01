from __future__ import annotations

import dataclasses
import os
import sys
from collections.abc import Mapping, Sequence
from functools import partial
from itertools import compress, zip_longest
from typing import Any, overload

import numpy as np
from qcodes import validators
from qcodes.instrument import InstrumentChannel, Instrument, ChannelTuple
from qcodes.parameters import (Parameter, MultiParameter, create_on_off_val_mapping,
                               ParamRawDataType)

_POSITION_SCALE = 10 ** 6


@dataclasses.dataclass(frozen=True)
class MultiAxisPosition(Sequence[float]):
    """A tuple-like representation of (a subset of) axis positions.

    Use this class to set any number of positions simultaneously using
    :attr:`AttocubeAMC100.multi_axis_position`.
    """
    axis_1: float = np.nan
    axis_2: float = np.nan
    axis_3: float = np.nan

    @overload
    def __getitem__(self, index: int, /) -> float: ...

    @overload
    def __getitem__(self, index: slice, /) -> Sequence[float]: ...

    def __getitem__(self, index):
        return dataclasses.astuple(self)[index]

    def __len__(self) -> int:
        return 3

    def _JSONEncoder(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


class MultiAxisPositionParameter(MultiParameter):
    """A parameter that simulatenously sets multiple axis positions.

    Always returns all three axes, but accepts a variable number for
    setting. The following are allowed for the single value argument:

     - an instance of :class:`MultiAxisPosition`
     - a mapping with possible keys ``axis_1``, ``axis_2``, ``axis_3``
       and float values
     - a sequence of floats which will be interpreted as
       `(axis_1, axis_2, ...)`

    """

    def get_raw(self) -> ParamRawDataType:
        if self.instrument is None:
            raise RuntimeError("No instrument attached to Parameter.")

        try:
            x, y, z, *_ = self.instrument.device.control.getPositionsAndVoltages()
        except self.instrument.exception_type as err:
            raise NotImplementedError from err
        else:
            self._update_cache(x, y, z)

        return MultiAxisPosition(x / _POSITION_SCALE,
                                 y / _POSITION_SCALE,
                                 z / _POSITION_SCALE)

    def set_raw(self, value: ParamRawDataType) -> None:
        if self.instrument is None:
            raise RuntimeError("No instrument attached to Parameter.")

        value_dict = dict.fromkeys(['axis_1', 'axis_2', 'axis_3'], np.nan)
        if isinstance(value, MultiAxisPosition):
            value_dict.update(dataclasses.asdict(value))
        elif isinstance(value, Mapping):
            value_dict.update(value)
        elif len(value) <= 3:
            value_dict.update({f'axis_{i}': val for i, val in enumerate(value, start=1)})
        else:
            raise ValueError('Too many values, expected at most 3')

        # tuples of boolean indicating whether axis is set and position
        vals = [(setit := not np.isnan(value_dict[key]),
                 value_dict[key] * _POSITION_SCALE if setit else 0.0)
                for key in ('axis_1', 'axis_2', 'axis_3')]
        sets, targets = zip(*vals)
        axes_to_move = list(compress(range(3), sets))
        try:
            # Set target positions
            self.instrument.device.control.MultiAxisPositioning(*sets, *targets)
            # Start moving
            for axis in axes_to_move:
                self.instrument.device.control.setControlMove(axis, True)
            # Wait for target reached
            while not all(self.instrument.device.status.getStatusTargetRange(axis)
                          for axis in axes_to_move):
                pass
            # Stop moving
            for axis in axes_to_move:
                self.instrument.device.control.setControlMove(axis, False)
        except self.instrument.exception_type as err:
            raise NotImplementedError from err
        else:
            # Cache target position on axis channels
            self._update_cache(**value_dict)

    def _update_cache(self, axis_1: float = np.nan, axis_2: float = np.nan,
                      axis_3: float = np.nan):
        if self.instrument is None:
            # mypy :)
            raise RuntimeError("No instrument attached to Parameter.")

        if not np.isnan(axis_1):
            self.instrument.axis_1.position.cache.set(axis_1)
        if not np.isnan(axis_2):
            self.instrument.axis_2.position.cache.set(axis_2)
        if not np.isnan(axis_3):
            self.instrument.axis_3.position.cache.set(axis_3)


class AMC100Axis(InstrumentChannel):

    def __init__(self, parent: 'AttocubeAMC100', name: str, axis: int, label: str | None = None,
                 **kwargs: Any) -> None:
        super().__init__(parent, name, label=label, **kwargs)

        self._axis = axis - 1
        self.actor_type = Parameter(
            'actor_type',
            get_cmd=partial(self.parent.device.control.getActorType, self._axis),
            val_mapping={'linear': 0, 'rotator': 1, 'goniometer': 2},
            label='Actor type',
            instrument=self
        )
        self.open_loop_status = Parameter(
            'open_loop_status',
            get_cmd=partial(self.parent.device.status.getOlStatus, self._axis),
            val_mapping={'NUM': 0, 'OL': 1, 'None': 2, 'RES': 3},
            label='Feedback status',
            instrument=self
        )
        self.reference_position_valid = Parameter(
            'reference_position_valid',
            get_cmd=partial(self.parent.device.status.getStatusReference, self._axis),
            label='Refrence position valid',
            instrument=self
        )
        self.reference_position = Parameter(
            'reference_position',
            get_cmd=self._get_reference_position,
            scale=_POSITION_SCALE,
            label=f"Reference Position {f'axis {axis}' if label is None else label}",
            unit='mm' if self.actor_type() == 'linear' else '°',
            instrument=self
        )
        self.position = Parameter(
            'position',
            get_cmd=partial(self.parent.device.move.getPosition, self._axis),
            set_cmd=self._move_to_target_position,
            set_parser=int,
            scale=10**6,
            label=f"Position {f'axis {axis}' if label is None else label}",
            unit='mm' if self.actor_type() == 'linear' else '°',
            instrument=self
        )
        self.frequency = Parameter(
            'frequency',
            get_cmd=partial(self.parent.device.control.getControlFrequency, self._axis),
            set_cmd=partial(self.parent.device.control.setControlFrequency, self._axis),
            set_parser=int,
            scale=1e3,
            # Validator is not int because it's run before the parsers,
            # and we allow numbers that can be cast to ints
            vals=validators.Numbers(3, 5000),
            label=f"Frequency {f'axis {axis}' if label is None else label}",
            unit='Hz',
            instrument=self
        )
        self.amplitude = Parameter(
            'amplitude',
            get_cmd=partial(self.parent.device.control.getControlAmplitude, self._axis),
            set_cmd=partial(self.parent.device.control.setControlAmplitude, self._axis),
            set_parser=int,
            scale=1e3,
            # Validator is not int because it's run before the parsers,
            # and we allow numbers that can be cast to ints
            vals=validators.Numbers(0, 45),
            label=f"Amplitude {f'axis {axis}' if label is None else label}",
            unit='V',
            instrument=self
        )
        self.output = Parameter(
            'output',
            get_cmd=partial(self.parent.device.control.getControlOutput, self._axis),
            set_cmd=partial(self.parent.device.control.setControlOutput, self._axis),
            val_mapping=create_on_off_val_mapping(),
            label=f"Output {f'axis {axis}' if label is None else label}",
            instrument=self
        )

    def _get_reference_position(self) -> int:
        if not self.reference_position_valid():
            self.parent.device.control.searchReferencePosition(self._axis)
        return self.parent.device.control.getReferencePosition(self._axis)

    def _move_to_target_position(self, position: int):
        self.parent.device.move.setControlTargetPosition(self._axis, position)
        self.parent.device.control.setControlMove(self._axis, True)
        while not self.parent.device.status.getStatusTargetRange(self._axis):
            # Update qcodes cache
            self.position.get()
        self.parent.device.control.setControlMove(self._axis, False)

    def move_to_reference_position(self):
        """This function starts an approach to the reference position.

        A running motion command is aborted; closed loop moving is
        switched on. Requires a valid reference position.
        """
        self.parent.device.move.moveReference(self._axis)

    def single_step(self, backward: bool):
        """This function triggers one step on the selected axis in
        desired direction.

        Parameters
        ----------
        backward : Selects the desired direction. False triggers a
            forward step, true a backward step.
        """
        self.parent.device.move.setSingleStep(self._axis, backward)


class AttocubeAMC100(Instrument):
    """Driver for the AMC100 position controller."""
    # Tested with fw 1.3.23

    def __init__(self, name: str, api_dir: os.PathLike, address: str | None = None,
                 axis_labels: Sequence[str] = (), **kwargs: Any):
        super().__init__(name, **kwargs)

        try:
            sys.path.append(str(api_dir))
            import AMC
            from ACS import AttoException
        except ImportError as err:
            sys.path.remove(str(api_dir))
            raise ImportError('This driver requires the AMC-APIs package which comes packaged '
                              'with the AMC software or can be downloaded from here:\n'
                              'https://github.com/attocube-systems/AMC-APIs') from err
        else:
            self._exception_type = AttoException

        if address is None:
            if not (discovered := AMC.discover()):
                raise ValueError('No devices discovered')
            address = list(discovered)[0]

        self.device = AMC.Device(address)
        self.device.connect()

        axes = []
        for i, label in zip_longest((1, 2, 3), axis_labels, fillvalue=None):
            # Mypy ...
            if i is None:
                break
            axes.append(axis := AMC100Axis(self, name := f'axis_{i}', i, label))
            self.add_submodule(name, axis)

        self.add_submodule('axis_channels', ChannelTuple(self, 'axis_channels', AMC100Axis, axes))

        self.add_parameter('multi_axis_position',
                           parameter_class=MultiAxisPositionParameter,
                           names=('axis_1', 'axis_2', 'axis_3'),
                           shapes=((), (), ()),
                           units=[ax.position.unit for ax in self.axis_channels],
                           labels=[ax.position.label for ax in self.axis_channels])

        self.connect_message()

    @property
    def exception_type(self) -> Exception:
        return self._exception_type

    def close(self):
        self.device.close()
        super().close()

    def get_idn(self) -> dict[str, str | None]:
        return {"vendor": "Attocube",
                "model": self.device.description.getDeviceType(),
                "serial": self.device.system_service.getSerialNumber(),
                "firmware": self.device.system_service.getFirmwareVersion()}
