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
        "The first channel": "ch1",
        "aux": "ch3",
        "center": "com"
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


def test_channel(pxie_2597):
    pxie_2597.disconnect_all()

    for ch in range(1, 6+1):
        ch_name = f"ch{ch}"
        pxie_2597.channel(ch_name)
        assert pxie_2597.channel() == ch_name

    pxie_2597.channel(None)
    assert pxie_2597.channel() is None


def test_read_connection(pxie_2597):
    for ch in range(1, 6+1):
        ch_name = f"ch{ch}"
        pxie_2597.disconnect_all()
        assert pxie_2597.read_connection("com") is None
        assert pxie_2597.read_connection(ch_name) is None

        pxie_2597.channel(ch_name)
        assert pxie_2597.read_connection("com") == ch_name
        assert pxie_2597.read_connection(ch_name) == "com"


def test_connect(pxie_2597, pxie_2597_with_name_map):
    for instr in [pxie_2597, pxie_2597_with_name_map]:
        for ch in range(1, 6+1):
            ch_name = f"ch{ch}"

            instr.disconnect_all()
            instr.connect(ch_name, "com")
            assert instr.channel() == ch_name
            instr.disconnect_all()
            instr.connect("com", ch_name)
            assert instr.channel() == ch_name
            instr.connect(ch_name, "com")
            assert instr.channel() == ch_name

        instr.connect("ch1", "com")
        instr.connect("ch1", None)
        assert instr.channel() is None
        instr.connect("ch1", "com")
        instr.connect(None, "ch1")
        assert instr.channel() is None

        instr.connect("com", "com")
        assert instr.channel() is None


def test_name_map(pxie_2597_with_name_map):
    instr = pxie_2597_with_name_map
    com_key = [k for k, v in NAME_MAPPING.items() if v == "com"][0]

    from qcodes.instrument.parameter import invert_val_mapping
    # check that the generated val_mapping is one to one
    val_mapping = instr.channel.val_mapping
    assert invert_val_mapping(invert_val_mapping(val_mapping)) == val_mapping

    for k in NAME_MAPPING.keys():
        if k == com_key:
            continue

        instr.disconnect_all()
        instr.channel(k)
        assert instr.channel() == k

        for ck in ["com", com_key]:
            instr.disconnect_all()
            instr.connect(k, ck)
            assert instr.channel() == k
            instr.disconnect_all()
            instr.connect(ck, k)
            assert instr.channel() == k
