import unittest
from unittest.mock import MagicMock
from unittest.mock import patch


class TestM2j(unittest.TestCase):

    @staticmethod
    def test_M4i_wait_ready():

        mock_pyspcm_module = MagicMock(name='pyspcm')

        with patch.dict('sys.modules', pyspcm=mock_pyspcm_module):
            import qcodes.instrument_drivers.Spectrum.M4i
            m4i = qcodes.instrument_drivers.Spectrum.M4i.M4i('test_m4i_instrument')

            m4i.sample_rate()
            mock_pyspcm_module.int32.assert_called()
            m4i.wait_ready()
            mock_pyspcm_module.spcm_dwSetParam_i32.assert_called()
            m4i.close()


