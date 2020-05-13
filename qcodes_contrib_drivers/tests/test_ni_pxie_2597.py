import pytest
try:
    import niswitch
    from niswitch.errors import DriverError
except ImportError:
    pytest.skip("niswitch not found", allow_module_level=True)

from qcodes_contrib_drivers.drivers.NationalInstruments.PXIe_2597 import NI_PXIe_2597 as PXIe_2597

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


@pytest.fixture(scope="module")
def pxie_2597_with_shuffled_channels():
    instr = get_pxie_2597("PXIe-2597-sim-with-shuffled-channels",
                          name_mapping={"ch1": "ch2",
                                        "ch2": "ch3",
                                        "ch3": "ch1"})
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
        assert len(getattr(pxie_2597.channels, ch_name).connection_list) == 0


def test_connect_to(pxie_2597, pxie_2597_with_name_map):
    for instr in [pxie_2597, pxie_2597_with_name_map]:
        ch1, ch2 = instr.channels[:2]
        com = instr.channels.com
        assert ch1 is not com
        assert ch2 is not com
        instr.disconnect_all()

        with pytest.raises(DriverError):
            ch1.connect_to(ch2)
        with pytest.raises(DriverError):
            ch2.connect_to(ch1)

        ch1.connect_to(com)
        assert ch1.connections() == [com.short_name]
        assert ch2.connections() == []
        for (c1, c2) in [(ch2, com),
                         (ch2, com),
                         (com, ch2)]:
            c1.connect_to(c2)
            assert ch1.connections() == []
            assert ch2.connections() == [com.short_name]

        instr.disconnect_all()
        for ch in [ch1, ch2, com]:
            with pytest.raises(ValueError):
                ch.connect_to("foo")


def test_disconnect_from(pxie_2597, pxie_2597_with_name_map):
    from itertools import combinations_with_replacement
    for instr in [pxie_2597, pxie_2597_with_name_map]:
        ch1, ch2 = instr.channels[:2]
        com = instr.channels.com
        instr.disconnect_all()
        for (c1, c2) in combinations_with_replacement([ch1, ch2, com], 2):
            with pytest.raises(DriverError):
                c1.disconnect_from(c2)
            with pytest.raises(DriverError):
                c2.disconnect_from(c1)

        ch1.connect_to(com)
        with pytest.raises(DriverError):
            ch1.disconnect_from(ch2)
        with pytest.raises(DriverError):
            ch2.disconnect_from(ch1)
        with pytest.raises(DriverError):
            ch2.disconnect_from(com)
        with pytest.raises(DriverError):
            com.disconnect_from(ch2)


def test_disconnect_from_all(pxie_2597, pxie_2597_with_name_map):
    for instr in [pxie_2597, pxie_2597_with_name_map]:
        com = instr.channels.com
        for ch in instr.channels:
            if ch is com:
                continue
            for ch_to_disconnect in [ch, com]:
                com.connect_to(ch)
                assert ch.connections() == ["com"]
                ch_to_disconnect.disconnect_from_all()
                assert ch.connections() == []
                assert com.connections() == []


def test_connect_to_other_instrument(pxie_2597, pxie_2597_with_name_map):
    instr1, instr2 = pxie_2597, pxie_2597_with_name_map
    instr1.disconnect_all()
    instr2.disconnect_all()
    with pytest.raises(ValueError):
        # attempting to connect channels on two different devices is an error
        instr1.channels[0].connect_to(instr2.channels.com)
    with pytest.raises(ValueError):
        instr2.channels[0].connect_to(instr1.channels.com)

    for instr in [instr1, instr2]:
        assert instr1.channels[0].connections() == []
        assert instr1.channels.com.connections() == []
        assert instr1.channel() is None
        assert instr2.channel() is None


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
    assert len(ch.connection_list) == 0


def test_com_alias_ignored(pxie_2597_with_name_map):
    instr = pxie_2597_with_name_map
    ch_names = [ch.short_name for ch in instr.channels]
    assert "com" in ch_names
    assert NAME_MAPPING["com"] not in ch_names


def test_parameters(pxie_2597,
                    pxie_2597_with_name_map,
                    pxie_2597_with_shuffled_channels):
    for instr in [pxie_2597,
                  pxie_2597_with_name_map,
                  pxie_2597_with_shuffled_channels]:
        for ch in instr.channels:
            ch_name = ch.short_name
            if ch_name == "com":
                continue

            instr.channel(ch_name)
            assert instr.channels.com.connections() == [ch_name]
            assert ch.connections() == ["com"]
            instr.disconnect_all()
            assert instr.channel() is None
            assert instr.channels.com.connections() == []
            assert ch.connections() == []
