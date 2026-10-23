"""Zurich MFLI with scalar and coherent QCoDeS lock-in readouts."""

from typing import Any

from zhinst.qcodes import MFLI as VendorMFLI

from ._lockin import ComplexSampleParameter as ComplexSampleParameter, LockinMixin


class MFLI(LockinMixin, VendorMFLI):
    """Extend the vendor MFLI driver without changing instrument configuration.

    The base instrument's measurement demodulator, ``demods[0]``, gains ``x``,
    ``y``, ``r``, ``theta`` (degrees), and coherent ``readout`` parameters.
    ``demods[0].readout("r", "theta")`` selects a MultiParameter for a dataset;
    calling ``demods[0].readout()`` still reads all four quantities.
    ``sample`` and the existing ``complex_sample`` interface are retained.
    Core controls and LabOne modules remain accessible through the vendor API.
    ``configure_trace(duration=...)`` prepares a time trace; supplying
    ``sweep_parameter``, ``start`` and ``stop`` prepares a parameter sweep.
    Both return a trace parameter for ``do0d`` or ``do1d``.

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
