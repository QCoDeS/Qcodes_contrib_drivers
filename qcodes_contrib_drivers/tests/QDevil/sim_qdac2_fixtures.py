import pytest
import uuid
from qcodes_contrib_drivers.drivers.QDevil import QDAC2
import qcodes_contrib_drivers.sims as sims
from qcodes.instrument.base import Instrument

# Use simulated instruments for the tests.
visalib = sims.__file__.replace('__init__.py', 'QDAC2.yaml@sim')


@pytest.fixture(scope='function')
def qdac():
    name = 'dac-' + str(uuid.uuid4())
    try:
        dac = QDAC2.QDac2(name, address='GPIB::1::INSTR', visalib=visalib)
    except Exception as error:
        # Circumvent Instrument not handling exceptions in constructor.
        Instrument._all_instruments.pop(name)
        print(f'CAUGHT: {error}')
        raise
    else:
        dac._no_binary_values = True
        dac.start_recording_scpi()
        yield dac
        lingering = dac.clear_read_queue()
        dac.close()
        if lingering:
            raise ValueError(f'Lingering messages in visa queue: {lingering}')
