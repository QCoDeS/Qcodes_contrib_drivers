import numpy
from qcodes_contrib_drivers.drivers.QDevil.QDAC2 import (
    comma_sequence_to_list, floats_to_comma_separated_list)


def test_comma_list_empty():
    assert comma_sequence_to_list("") == []


def test_comma_list_space():
    assert comma_sequence_to_list("1, 2") == ['1', '2']


def test_comma_list_no_space():
    assert comma_sequence_to_list("1,2") == ['1', '2']


def test_floats_to_list_empty():
    assert floats_to_comma_separated_list([]) == ''


def test_floats_to_list_direct():
    assert floats_to_comma_separated_list([1, 2]) == '1,2'


def test_floats_to_list_rounding():
    unrounded = numpy.linspace(0, 1, 11)
    assert floats_to_comma_separated_list(unrounded) == \
        '0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1'
