import pytest
from qcodes_contrib_drivers.drivers.QDevil.QSwitch import QSwitch
from .sim_qswitch_fixtures import visalib


def test_refuse_wrong_model():
    # -----------------------------------------------------------------------
    with pytest.raises(ValueError) as error:
        QSwitch('dmm', address='GPIB::5::INSTR', visalib=visalib)
    # -----------------------------------------------------------------------
    assert 'Unknown model' in repr(error)


def test_refuse_incompatible_firmware():
    # -----------------------------------------------------------------------
    with pytest.raises(ValueError) as error:
        QSwitch('qswitch', address='GPIB::6::INSTR', visalib=visalib)
    # -----------------------------------------------------------------------
    assert 'Incompatible firmware' in repr(error)


def test_refuse_qcodes_incompatible_name():
    # -----------------------------------------------------------------------
    with pytest.raises(ValueError) as error:
        QSwitch('QSwitch-1', address='GPIB::4::INSTR', visalib=visalib)
    # -----------------------------------------------------------------------
    assert 'QSwitch-1' in repr(error)
    assert 'incompatible with QCoDeS parameter' in repr(error)
