import logging
import textwrap

from typing import Optional

from .DeviceManagerCLI import IGenericDeviceCLI, IGenericCoreDeviceCLI, ILockableDeviceCLI

from .qcodes_thorlabs_integration import PyDecimalNumbers, ThorlabsObjectWrapper

log = logging.getLogger(__name__)


class ILaserSource(IGenericDeviceCLI, IGenericCoreDeviceCLI):
    """
    Interface for Laser Source devices. 
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        laser_limits = LaserLimits(self, 'laser_limits')
        self.add_submodule('laser_limits', laser_limits)

        self.add_parameter(
            "control_source",
            label="Control Source",
            get_cmd=lambda: self._get_thorlabs_enum(getter_name='GetControlSource'),
            set_cmd=lambda x: self._set_thorlabs_enum(x, setter_name='SetControlSource'),
            val_mapping={
                'Software': 0, 
                'Software, External': 1, 
                'Software, Potentiometer, External': 4
            },
            docstring="Laser control source"
        )

        self.add_parameter(
            "current",
            label="Current",
            get_cmd=lambda: self._get_thorlabs_decimal(getter_name='GetCurrentReading'),
            unit="mA",
            docstring="Current Current reading from the Laser Source."
        )
        
        self.add_parameter(
            "wavelength",
            label="Wavelength",
            get_cmd=lambda: self._get_thorlabs_decimal(getter_name='GetWavelength'),
            unit="nm",
            docstring="Laser Source wavelength"
        )
        
        self.add_parameter(
            "set_power",
            label="Laser Power",
            get_cmd=lambda: self._get_thorlabs_attribute(getter_name='GetSetPower'), 
            set_cmd=lambda x: self._set_thorlabs_decimal(x, setter_name='SetPower'),
            unit="mW",
            vals=PyDecimalNumbers(0, self.laser_limits.max_power())
        )

        self.add_parameter(
            "power",
            label="Laser Power",
            get_cmd=lambda: self._get_thorlabs_decimal(getter_name='GetPowerReading'),
            unit="mW",
            docstring="Current Power reading from the Laser Source"
        )

        self.add_parameter(
            "interlock_state",
            label="Interlock State",
            get_cmd=lambda: self._get_thorlabs_attribute(getter_name='GetInterlockState'),
            docstring="Interlock State. True if the safety interlock is enabled."
        )

        self.add_parameter(
            'output_enabled',
            get_cmd=lambda: self._get_thorlabs_attribute(getter_name='GetStatusBits'),
            set_cmd=lambda x: self._api_interface.SetOn() if x else self._api_interface.SetOff(),
            get_parser=lambda i: bool(0x1 & i),
            docstring=textwrap.dedent(
                """
                Laser Output Enabled State.

                Indicates whether the laser output is enabled.

                Laser will be enabled only if interlock is in place AND
                keyswitch is at ON position. 
                """
            )
        )

        self.add_parameter(
            'key_switch_enabled',
            get_cmd=lambda: self._get_thorlabs_attribute(getter_name='GetStatusBits'),
            get_parser=lambda i: bool(0x2 & i),
            docstring=textwrap.dedent(
                """
                Key Switch Enabled State.

                Indicates whether the key switch is enabled.
                """
            )
        )

        self.add_parameter(
            'control_mode',
            get_cmd=lambda: self._get_thorlabs_attribute(getter_name='GetStatusBits'),
            get_parser=lambda i: bool(0x4 & i),
            val_mapping={
                'Constant I (Open Loop)': False,
                'Constant P (Closed Loop)': True
            },
            docstring=textwrap.dedent(
                """
                Laser Control Mode.

                Indicates the control mode of the laser.
                """
            )
        )

        self.add_parameter(
            'safety_interlock_enabled',
            get_cmd=lambda: self._get_thorlabs_attribute(getter_name='GetStatusBits'),
            get_parser=lambda i: bool(0x8 & i),
            docstring=textwrap.dedent(
                """
                Safety Interlock Enabled State.

                Indicates whether the safety interlock is enabled.
                """
            )
        )

        self.add_parameter(
            'units_mode_mA',
            get_cmd=lambda: self._get_thorlabs_attribute(getter_name='GetStatusBits'),
            get_parser=lambda i: bool(0x10 & i),
            docstring=textwrap.dedent(
                """
                Units Mode - mA.

                Indicates if the units mode is set to milliAmperes (mA).
                """
            )
        )

        self.add_parameter(
            'units_mode_mW',
            get_cmd=lambda: self._get_thorlabs_attribute(getter_name='GetStatusBits'),
            get_parser=lambda i: bool(0x20 & i),
            docstring=textwrap.dedent(
                """
                Units Mode - mW.

                Indicates if the units mode is set to milliWatts (mW).
                """
            )
        )

        self.add_parameter(
            'units_mode_dBm',
            get_cmd=lambda: self._get_thorlabs_attribute(getter_name='GetStatusBits'),
            get_parser=lambda i: bool(0x40 & i),
            docstring=textwrap.dedent(
                """
                Units Mode - dBm.

                Indicates if the units mode is set to decibel-milliwatts (dBm).
                """
            )
        )

        self.add_parameter(
            'error',
            get_cmd=lambda: self._get_thorlabs_attribute(getter_name='GetStatusBits'),
            get_parser=lambda i: bool(0x40000000 & i),
            docstring=textwrap.dedent(
                """
                Error Flag.

                Indicates if an error is present.
                """
            )
        )


class LaserLimits(ThorlabsObjectWrapper):
    """
    The Laser limits structure. 

    The Laser Limits are defined by the Laser Source and are Read Only. 

    Attributes:
        max_current: The Laser Source maximum current.
        max_power: The Laser Source maximum power.
    """
    def __init__(
        self, 
        parent,
        name,
        object_key: Optional[str] = None,
        getter_name: Optional[str] = 'GetLimits',
        setter_name: Optional[str] = None,
        **kwargs
    ):
        super().__init__(parent, name, object_key, getter_name, setter_name, **kwargs)

        self.add_parameter(
            'max_current',
            get_cmd=lambda: self._get_thorlabs_decimal('MaxCurrent'),
            unit="mA",
            docstring="The Laser Source maximum current, range 0 to 655.35 mA."
        )

        self.add_parameter(
            'max_power',
            get_cmd=lambda: self._get_thorlabs_decimal('MaxPower'),
            unit="mW",
            docstring="The Laser Source maximum power, range 0 to 6.5535 mW."
        )


class KCubeLaserSource(ILockableDeviceCLI, ILaserSource):
    """
    Cube laser source. 
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

