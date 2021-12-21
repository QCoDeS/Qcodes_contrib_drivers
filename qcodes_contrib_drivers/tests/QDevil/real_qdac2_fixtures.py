import pytest
import os
from time import strftime
from qcodes_contrib_drivers.drivers.QDevil import QDAC2

# Pick up the VISA address for the actual instrument.  If left undefined, then
# the tests that require a real instrument are not run.
qdac_ip_addr = os.environ.get('QDAC_IP_ADDR', '')


instrument_connected = pytest.mark.skipif(
    qdac_ip_addr == '',
    reason='IP address of QDAC-II instrument missing (QDAC_IP_ADDR)')


not_implemented = pytest.mark.skip(reason="Not implemented")


def display(*args):
    print(strftime('[%H:%M:%S]'), end=' ')
    print(*args)


class DUT:
    _instance = None

    @staticmethod
    def instance():
        if not DUT._instance:
            DUT()
        return DUT._instance

    def __init__(self):
        if DUT._instance:
            raise ValueError('DUT is a singleton, call instance()')
        DUT._instance = self
        display('Creating instance')
        name = 'qdac2'
        self.dac = QDAC2.QDac2(name, visalib='@py', address=f'TCPIP::{qdac_ip_addr}::5025::SOCKET')
        self.dac.visa_handle.timeout = 10 * 1000  # 10 seconds
        display('Clearing errors')
        self.dac.ask('syst:err:all?')  # Clear any errors

    def __exit__(self):
        self.dac.close()


@pytest.fixture(scope='function')
def qdac():
    display('Preparing fixture')
    dac = DUT.instance().dac
    dac.start_recording_scpi()
    dac.clear()
    display('Test')
    yield dac
    check_qdac_for_errors()
    display('Done')


@pytest.fixture(scope='session', autouse=True)
def session_cleanup():
    yield
    display('Cleaning up test session')
    dac = DUT.instance().dac
    dac.reset()


def check_qdac_for_errors():
    display('Check for errors')
    errors = get_qdac_errors()
    if errors:
        # This results in an Error, not a Fail as you might expect, see
        # https://github.com/pytest-dev/pytest/issues/5044
        pytest.fail(f'Error from QDAC: {repr(errors)}')


def get_qdac_errors():
    dac = DUT.instance().dac
    errors = dac.ask('syst:err:all?')
    no_error = '0, "No error"'
    if errors.startswith(no_error):
        errors = errors[len(no_error):]
    dac.visa_handle.clear()
    return errors
