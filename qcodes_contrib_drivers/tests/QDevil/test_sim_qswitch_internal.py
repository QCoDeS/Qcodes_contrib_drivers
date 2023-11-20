import pytest
from qcodes_contrib_drivers.drivers.QDevil.QSwitch import (
    _state_diff,
    channel_list_to_state,
    compress_channel_list,
    expand_channel_list)


@pytest.mark.parametrize(('input', 'output'), [
    ('(@)', []),
    ('(@1!0,2!0)', [(1,0), (2,0)]),
    ('(@1!0:2!0)', [(1,0), (2,0)]),
    ('(@1!0,1!9)', [(1,0), (1,9)]),
    ('(@1!0:3!0,4!9,23!7:24!7)', [(1,0), (2,0), (3,0), (4,9), (23,7), (24,7)]),
])
def test_channel_list_to_map(input, output):  # noqa
    # -----------------------------------------------------------------------
    unpacked = channel_list_to_state(input)
    # -----------------------------------------------------------------------
    assert unpacked == output


def test_channel_list_can_be_unpacked():  # noqa
    # -----------------------------------------------------------------------
    unpacked = expand_channel_list('(@1!0:3!0,4!9,23!7:24!7)')
    # -----------------------------------------------------------------------
    assert unpacked == '(@1!0,2!0,3!0,4!9,23!7,24!7)'


@pytest.mark.parametrize(('input', 'output'), [
    ('(@)', '(@)'),
    ('(@1!2)', '(@1!2)'),
    ('(@1!2,3!2)', '(@1!2,3!2)'),
    ('(@1!0,2!0,3!0,4!9,23!7,24!7)', '(@1!0:3!0,23!7:24!7,4!9)')
])
def test_channel_list_can_be_packed(input, output):  # noqa
    # -----------------------------------------------------------------------
    packed = compress_channel_list(input)
    # -----------------------------------------------------------------------
    assert packed == output


@pytest.mark.parametrize(('before', 'after', 'positive', 'negative'), [
    ([], [], [], []),
    ([], [(1,2)], [(1,2)], []),
    ([(7,5)], [(1,2)], [(1,2)], [(7,5)]),
    ([(7,5), (3,4)], [(1,2), (3,4)], [(1,2)], [(7,5)]),
])
def test_state_diff(before, after, positive, negative):  # noqa
    # -----------------------------------------------------------------------
    pos, neg, _ = _state_diff(before, after)
    # -----------------------------------------------------------------------
    assert pos == positive
    assert neg == negative
