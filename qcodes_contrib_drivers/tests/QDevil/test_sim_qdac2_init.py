import pytest
from qcodes_contrib_drivers.drivers.QDevil import QDAC2
from qcodes.instrument.base import Instrument
from .sim_qdac2_fixtures import visalib


def test_refuse_wrong_model():
    # Use simulated instruments for the tests.
    wrong_instrument = 'dmm'
    # -----------------------------------------------------------------------
    with pytest.raises(ValueError) as error:
        QDAC2.QDac2(wrong_instrument, address='GPIB::2::INSTR', visalib=visalib)
    # -----------------------------------------------------------------------
    assert 'Unknown model' in repr(error)
    # Circumvent Instrument not handling exceptions in constructor.
    Instrument._all_instruments.pop(wrong_instrument)


def test_refuse_incompatible_firmware():
    # -----------------------------------------------------------------------
    with pytest.raises(ValueError) as error:
        QDAC2.QDac2('qdac', address='GPIB::3::INSTR', visalib=visalib)
    # -----------------------------------------------------------------------
    assert 'Incompatible firmware' in repr(error)
    # Circumvent Instrument not handling exceptions in constructor.
    Instrument._all_instruments.pop('qdac')
