import pytest
from qcodes_contrib_drivers.drivers.QDevil.QDAC2 import QDac2, split_version_string_into_components
from qcodes.instrument.base import Instrument
from .sim_qdac2_fixtures import visalib

@pytest.mark.parametrize('version,components', [
    ('3-0.9.6', ['3', '0.9.6']),
    ('10.2-1.14', ['10.2', '1.14'])
])
def test_split_version_string_into_components(version, components):
    assert split_version_string_into_components(version) == components


def test_refuse_wrong_model():
    # Use simulated instruments for the tests.
    wrong_instrument = 'dmm'
    # -----------------------------------------------------------------------
    with pytest.raises(ValueError) as error:
        QDac2(wrong_instrument, address='GPIB::2::INSTR', visalib=visalib)
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
        QDac2('qdac', address='GPIB::3::INSTR', visalib=visalib)
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
        QDac2('QDAC-II', address='GPIB::1::INSTR', visalib=visalib)
    # -----------------------------------------------------------------------
    assert 'QDAC-II' in repr(error)
    assert 'incompatible with QCoDeS parameter' in repr(error)
