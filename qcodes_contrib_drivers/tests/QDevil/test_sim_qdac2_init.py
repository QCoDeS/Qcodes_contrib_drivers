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
    # In qcodes < 0.32
    try:
        Instrument._all_instruments.pop(wrong_instrument)
    except KeyError:
        pass

def test_refuse_incompatible_firmware():
    # -----------------------------------------------------------------------
    with pytest.raises(ValueError) as error:
        QDAC2.QDac2('qdac', address='GPIB::3::INSTR', visalib=visalib)
    # -----------------------------------------------------------------------
    assert 'Incompatible firmware' in repr(error)
    # Circumvent Instrument not handling exceptions in constructor.
    # In qcodes < 0.32
    try:
        Instrument._all_instruments.pop('qdac')
    except KeyError:
        pass

def test_refuse_qcodes_incompatible_name():
    # -----------------------------------------------------------------------
    with pytest.raises(ValueError) as error:
        QDAC2.QDac2('QDAC-II', address='GPIB::1::INSTR', visalib=visalib)
    # -----------------------------------------------------------------------
    assert 'QDAC-II' in repr(error)
    assert 'incompatible with QCoDeS parameter' in repr(error)
