import pytest
import uuid
from qcodes_contrib_drivers.drivers.QDevil import QDAC2
import qcodes_contrib_drivers.sims as sims
from qcodes.instrument.base import Instrument

# Use simulated instruments for the tests.
visalib = sims.__file__.replace('__init__.py', 'QDAC2.yaml@sim')


class DUT:
    _instance = None

    @staticmethod
    def instance():
        if not DUT._instance:
            DUT()
        return DUT._instance

    def __init__(self):
        if DUT._instance:
            raise ValueError('DUT is a singleton, use instance() instead')
        DUT._instance = self
        name = ('dac' + str(uuid.uuid4())).replace('-', '')
        try:
            self.dac = QDAC2.QDac2(name, address='GPIB::1::INSTR', visalib=visalib)
        except Exception as error:
            # Circumvent Instrument not handling exceptions in constructor.
            Instrument._all_instruments.pop(name)
            print(f'CAUGHT: {error}')
            raise
        else:
            self.dac._no_binary_values = True

    def __exit__(self):
        self.dac.close()


class DUT2:
    _instance = None

    @staticmethod
    def instance():
        if not DUT2._instance:
            DUT2()
        return DUT2._instance

    def __init__(self):
        if DUT2._instance:
            raise ValueError('DUT2 is a singleton, use instance() instead')
        DUT2._instance = self
        name = ('dac' + str(uuid.uuid4())).replace('-', '')
        try:
            self.dac = QDAC2.QDac2(name, address='GPIB::1::INSTR', visalib=visalib)
        except Exception as error:
            # Circumvent Instrument not handling exceptions in constructor.
            Instrument._all_instruments.pop(name)
            print(f'CAUGHT: {error}')
            raise
        else:
            self.dac._no_binary_values = True

    def __exit__(self):
        self.dac.close()


@pytest.fixture(scope='function')
def qdac():
    dac = DUT.instance().dac
    dac.start_recording_scpi()
    yield dac
    lingering = dac.clear_read_queue()
    if lingering:
        raise ValueError(f'Lingering messages in visa queue: {lingering}')


@pytest.fixture(scope='function')
def qdac2():
    dac = DUT2.instance().dac
    dac.start_recording_scpi()
    yield dac
    lingering = dac.clear_read_queue()
    if lingering:
        raise ValueError(f'Lingering messages in visa queue: {lingering}')
