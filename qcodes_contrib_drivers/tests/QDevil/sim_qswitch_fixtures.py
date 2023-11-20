import pytest
from unittest.mock import patch
import uuid
from qcodes_contrib_drivers.drivers.QDevil import QSwitch
import qcodes_contrib_drivers.sims as sims

# Use simulated instruments for the tests.
visalib = sims.__file__.replace('__init__.py', 'QSwitch.yaml@sim')


@pytest.fixture(scope='function')
def qswitch():
    name = ('switch' + str(uuid.uuid4())).replace('-', '')
    switch = QSwitch.QSwitch(name, address='GPIB::4::INSTR', visalib=visalib)
    switch.start_recording_scpi()
    patch('qcodes_contrib_drivers.drivers.QDevil.QSwitch.sleep_s')
    yield switch
    lingering = switch.clear_read_queue()
    if lingering:
        raise ValueError(f'Lingering messages in visa queue: {lingering}')
