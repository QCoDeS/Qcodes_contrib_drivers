"""Zurich MFLI with scalar and coherent QCoDeS lock-in readouts."""

from typing import Any

from zhinst.qcodes import MFLI as VendorMFLI

from ._lockin import ComplexSampleParameter as ComplexSampleParameter, LockinMixin


class MFLI(LockinMixin, VendorMFLI):
    """Extend the vendor MFLI driver without changing instrument configuration.

    The base instrument's measurement demodulator, ``demods[0]``, gains ``x``,
    ``y``, ``r``, ``theta`` (degrees), and coherent ``readout`` parameters.
    ``sample`` and the existing ``complex_sample`` interface are retained.
    Core controls and LabOne modules remain accessible through the vendor API.

    Args:
        name: QCoDeS instrument name.
        serial: Device serial, for example ``"dev7920"``.
        host: LabOne data-server address, for example ``"localhost"``.
        **kwargs: Passed to ``zhinst.qcodes.MFLI`` (port, interface, etc.).
    """

    _lockin_model = "MFLI"
    _measurement_demodulators = (0,)
    _output_mixers = (1,)

    def __init__(self, name: str, serial: str, host: str, **kwargs: Any):
        super().__init__(name=name, serial=serial, host=host, **kwargs)
        try:
            self._initialize_lockin()
        except Exception:
            self.close()
            raise
