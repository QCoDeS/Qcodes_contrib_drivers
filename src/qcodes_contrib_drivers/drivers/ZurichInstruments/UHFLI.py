"""Zurich UHFLI with scalar and coherent QCoDeS lock-in readouts."""

from typing import Any

from zhinst.qcodes import UHFLI as VendorUHFLI

from ._lockin import LockinMixin


class UHFLI(LockinMixin, VendorUHFLI):
    """Extend the vendor UHFLI driver without changing instrument configuration.

    Each of ``demods[0]`` through ``demods[7]`` gains ``x``, ``y``, ``r``,
    ``theta`` (degrees), coherent ``readout``, and ``complex_sample`` parameters.
    ``demods[0].readout("r", "theta")`` selects a MultiParameter for a dataset;
    calling ``demods[0].readout()`` still reads all four quantities.
    Readout rejects disabled channels and channels used for external reference.
    Core controls and LabOne modules remain accessible through the vendor API.
    ``configure_trace(duration=...)`` prepares a time trace; supplying
    ``sweep_parameter``, ``start`` and ``stop`` prepares a parameter sweep.
    Both return a trace parameter for ``do0d`` or ``do1d``.

    Args:
        name: QCoDeS instrument name.
        serial: Device serial, for example ``"dev20046"``.
        host: LabOne data-server address, for example ``"localhost"``.
        **kwargs: Passed to ``zhinst.qcodes.UHFLI`` (port, interface, etc.).
    """

    _lockin_model = "UHFLI"
    _measurement_demodulators = tuple(range(8))
    _output_mixers = (3, 7)

    def __init__(self, name: str, serial: str, host: str, **kwargs: Any):
        super().__init__(name=name, serial=serial, host=host, **kwargs)
        try:
            self._initialize_lockin()
        except Exception:
            self.close()
            raise
