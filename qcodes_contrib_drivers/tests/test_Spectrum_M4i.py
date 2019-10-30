import unittest
from unittest.mock import MagicMock
from unittest.mock import patch


class TestM2j(unittest.TestCase):

    def setUp(self):
        self.mock_pyspcm_module = MagicMock(name='pyspcm')

    def test_M4i_wait_ready(self):

        with patch.dict('sys.modules', pyspcm=self.mock_pyspcm_module):
            import qcodes_contrib_drivers.drivers.Spectrum.M4i
            m4i = qcodes_contrib_drivers.drivers.Spectrum.M4i.M4i('test_m4i_instrument')
            self.addCleanup(qcodes_contrib_drivers.drivers.Spectrum.M4i.M4i.close_all)

            m4i.sample_rate()
            self.mock_pyspcm_module.int32.assert_called()
            m4i.wait_ready()
            self.mock_pyspcm_module.spcm_dwSetParam_i32.assert_called()
            m4i.close()
