import sys

from qcodes.parameters import DelegateParameter
from qcodes.utils import QCoDeSDeprecationWarning

if sys.version_info >= (3, 13):
    from warnings import deprecated
else:
    from typing_extensions import deprecated

from .Andor_iDus4xx import AndorIDus4xx


@deprecated(
    "The Andor_DU401 class name is deprecated. Please use AndorIDus4xx from Andor_iDus4xx.py "
    "instead",
    category=QCoDeSDeprecationWarning,
    stacklevel=2,
)
class Andor_DU401(AndorIDus4xx):
    def __init__(self, name: str, dll_path: str | None = None, camera_id: int = 0,
                 setup: bool = True, min_temperature: int | None = None, **kwargs):
        super().__init__(name, dll_path=dll_path, camera_id=camera_id,
                         min_temperature=min_temperature, **kwargs)

        self.x_pixels, self.y_pixels = self.detector_pixels()

        self.filter_mode = self.add_parameter(
            "filter_mode",
            DelegateParameter,
            source=self.cosmic_ray_filter_mode
        )
        """Deprecated. Use :attr:`cosmic_ray_filter_mode` instead."""

        self.spectrum = self.add_parameter(
            "spectrum",
            get_cmd=self._get_spectrum,
            shape=(1, self.x_pixels),
            label="spectrum"
        )
        """Deprecated. Use attr:`ccd_data` instead."""

        # set up detector with default settings
        if setup:
            self.cooler.set(True)
            self.set_temperature.set(-60)
            self.read_mode.set("full vertical binning")
            self.acquisition_mode.set("single scan")
            self.trigger_mode.set("internal")
            self.shutter_mode.set("fully auto")

    def _get_spectrum(self) -> list[int]:
        if self.acquisition_mode() not in ("single scan", "accumulate"):
            raise RuntimeError("Spectrum can only be acquired in single scan or accumulate mode")
        if self.read_mode() not in ("full vertical binning", "single track"):
            raise RuntimeError(
                "Spectrum can only be acquired in full vertical binning or single track mode"
            )
        return self.ccd_data.get()
