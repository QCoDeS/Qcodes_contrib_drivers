import dataclasses
import os
import sys
from collections.abc import Mapping, Sequence
from functools import partial
from itertools import chain, zip_longest
from typing import Any, overload

import numpy as np
from qcodes import validators
from qcodes.instrument import InstrumentChannel, Instrument, ChannelTuple
from qcodes.parameters import (Parameter, MultiParameter, create_on_off_val_mapping,
                               ParamRawDataType)

_POSITION_SCALE = 10 ** 6


@dataclasses.dataclass
class MultiAxisPosition(Sequence[float]):
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
            value_dict.update({f'axis_{i}': val for i, val in enumerate(value)})
        else:
            raise ValueError('Too many values, expected at most 3')

        # tuples of boolean indicating whether axis is set and position
        vals = [(setit := not np.isnan(value_dict[key]),
                 value_dict[key] * _POSITION_SCALE if setit else 0.0)
                for key in ('axis_1', 'axis_2', 'axis_3')]
        try:
            *_, x, y, z = self.instrument.device.control.MultiAxisPositioning(*chain(*zip(*vals)))
        except self.instrument.exception_type as err:
            raise NotImplementedError from err
        else:
            self._update_cache(x, y, z)

    def _update_cache(self, x, y, z):
        for pos, ax in zip([x, y, z], self.instrument.axis_channels):
            ax.position.cache.set(pos)


class AMC100Axis(InstrumentChannel):

    def __init__(self, parent: 'AttocubeAMC100', name: str, axis: int, label: str | None = None,
                 **kwargs: Any) -> None:
        super().__init__(parent, name, label=label, **kwargs)

        self.actor_type = Parameter(
            'actor_type',
            get_cmd=partial(self.parent.device.control.getActorType, axis-1),
            val_mapping={'linear': 0, 'rotator': 1, 'goniometer': 2},
            label='Actor type',
            instrument=self
        )
        self.open_loop_status = Parameter(
            'open_loop_status',
            get_cmd=partial(self.parent.device.status.getOlStatus, axis-1),
            val_mapping={'NUM': 0, 'OL': 1, 'None': 2, 'RES': 3},
            label='Feedback status',
            instrument=self
        )
        self.reference_position_valid = Parameter(
            'reference_position_valid',
            get_cmd=partial(self.parent.device.status.getStatusReference, axis-1),
            label='Refrence position valid',
            instrument=self
        )
        self.reference_position = Parameter(
            'reference_position',
            get_cmd=partial(self._get_reference_position, axis-1),
            scale=_POSITION_SCALE,
            label=f"Reference Position {f'axis {axis}' if label is None else label}",
            unit='mm' if self.actor_type() == 'linear' else '°',
            instrument=self
        )
        self.position = Parameter(
            'position',
            get_cmd=partial(self.parent.device.move.getPosition, axis-1),
            set_cmd=partial(self._move_to_target_position, axis-1),
            set_parser=int,
            scale=10**6,
            label=f"Position {f'axis {axis}' if label is None else label}",
            unit='mm' if self.actor_type() == 'linear' else '°',
            instrument=self
        )
        self.frequency = Parameter(
            'frequency',
            get_cmd=partial(self.parent.device.control.getControlFrequency, axis-1),
            set_cmd=partial(self.parent.device.control.setControlFrequency, axis-1),
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
            get_cmd=partial(self.parent.device.control.getControlAmplitude, axis-1),
            set_cmd=partial(self.parent.device.control.setControlAmplitude, axis-1),
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
            get_cmd=partial(self.parent.device.control.getControlOutput, axis-1),
            set_cmd=partial(self.parent.device.control.setControlOutput, axis-1),
            val_mapping=create_on_off_val_mapping(),
            label=f"Output {f'axis {axis}' if label is None else label}",
            instrument=self
        )

    def _get_reference_position(self, axis: int) -> int:
        if not self.reference_position_valid():
            self.parent.device.control.searchReferencePosition(axis)
        return self.parent.device.control.getReferencePosition(axis)

    def _move_to_target_position(self, axis: int, position: int):
        self.parent.device.move.setControlTargetPosition(axis, position)
        self.parent.device.control.setControlMove(axis, True)
        while not self.parent.device.status.getStatusTargetRange(axis):
            # Update qcodes cache
            self.position.get()
        self.parent.device.control.setControlMove(axis, False)


class AttocubeAMC100(Instrument):
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
