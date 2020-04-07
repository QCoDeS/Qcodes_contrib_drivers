import pytest
try:
    import niswitch
except ImportError:
    pytest.skip("niswitch not found", allow_module_level=True)

from qcodes_contrib_drivers.drivers.NationalInstruments.NI_Switch import PXIe_2597

# NOTE: if running tests in parallel, a lock file should be used, see
# https://github.com/ni/nimi-python/blob/master/src/niswitch/system_tests/test_system_niswitch.py


def get_pxie_2597(name, name_mapping=None):
    return PXIe_2597(
            name=name,
            resource="",
            name_mapping=name_mapping,
            niswitch_kw=dict(
                # use simulation mode provided by the NI-Switch driver
                simulate=True,
                topology="2597/6x1 Terminated Mux",
                )
            )


@pytest.fixture(scope="module")
def pxie_2597():
    instr = get_pxie_2597("PXIe-2597-sim")
    yield instr
    instr.close()


# example name mapping to use in the tests
NAME_MAPPING = {
        "ch1": "The first channel",
        "ch3": "aux",
        "com": "mistake"  # this should be ignored
        }


@pytest.fixture(scope="module")
def pxie_2597_with_name_map():
    instr = get_pxie_2597(name="PXIe-2597-sim-with-name-map",
                          name_mapping=NAME_MAPPING)
    yield instr
    instr.close()


def test_disconnect_all(pxie_2597):
    pxie_2597.disconnect_all()
    assert pxie_2597.channel() is None
    for ch in range(1, 6+1):
        ch_name = f"ch{ch}"
        assert len(pxie_2597.channels.com.connection_list) == 0
        assert len(getattr(pxie_2597.channels, ch_name).connection_list)  == 0


def test_channel(pxie_2597):
    pxie_2597.disconnect_all()

    for ch in range(1, 6+1):
        ch_name = f"ch{ch}"
        ch = getattr(pxie_2597.channels, ch_name)
        pxie_2597.channel(ch_name)
        assert pxie_2597.channel() == ch_name
        assert ch in pxie_2597.channels.com.connection_list
        assert pxie_2597.channels.com in ch.connection_list

    pxie_2597.channel(None)
    assert pxie_2597.channel() is None
    assert len(pxie_2597.channels.com.connection_list) == 0
    assert len(ch.connection_list)  == 0


def test_parameters(pxie_2597, pxie_2597_with_name_map):
    for instr in [pxie_2597, pxie_2597_with_name_map]:
        for ch in range(1, 6+1):
            ch_name = f"ch{ch}"
            if instr is pxie_2597_with_name_map and ch_name in NAME_MAPPING: 
                ch_name = NAME_MAPPING[ch_name]
            ch = getattr(instr.channels, ch_name)

            instr.channel(ch_name)
            assert ch_name in instr.channels.com.connections()
            assert "com" in ch.connections()
            instr.disconnect_all()
            assert instr.channels.com.connections() == []
            assert ch.connections() == []
