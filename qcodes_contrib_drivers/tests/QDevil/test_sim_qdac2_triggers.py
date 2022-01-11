import pytest
from .sim_qdac2_fixtures import qdac  # noqa


def test_trigger_all_free(qdac):  # noqa
    qdac.free_all_triggers()
    # -----------------------------------------------------------------------
    assert qdac.n_triggers() == len(qdac._internal_triggers)


def test_trigger_context(qdac):  # noqa
    free_triggers = len(qdac._internal_triggers)
    # -----------------------------------------------------------------------
    with qdac.allocate_trigger() as trigger:
        n = trigger.value
    # -----------------------------------------------------------------------
    assert n == 1
    assert free_triggers == len(qdac._internal_triggers)


def test_trigger_allocation(qdac):  # noqa
    # -----------------------------------------------------------------------
    trigger_x = qdac.allocate_trigger()
    trigger_y = qdac.allocate_trigger()
    # -----------------------------------------------------------------------
    assert trigger_x.value != trigger_y.value
    assert trigger_y.value <= qdac.n_triggers()
    assert trigger_x.value not in qdac._internal_triggers
    assert trigger_y.value not in qdac._internal_triggers


def test_trigger_deallocation(qdac):  # noqa
    trigger = qdac.allocate_trigger()
    qdac.allocate_trigger()
    # -----------------------------------------------------------------------
    qdac.free_trigger(trigger)
    # -----------------------------------------------------------------------
    assert trigger.value in qdac._internal_triggers


def test_no_more_triggers(qdac):  # noqa
    # -----------------------------------------------------------------------
    with pytest.raises(ValueError) as error:
        for _ in range(qdac.n_triggers()):
            qdac.allocate_trigger()
    # -----------------------------------------------------------------------
    assert 'no free internal triggers' in repr(error)


def test_external_inputs(qdac):  # noqa
    assert qdac.n_external_inputs() == 4


def test_external_ouputs(qdac):  # noqa
    assert qdac.n_external_outputs() == 5


def test_connect_external_trigger_default(qdac):  # noqa
    qdac.free_all_triggers()
    port = qdac.n_external_outputs()
    internal = qdac.allocate_trigger()
    # -----------------------------------------------------------------------
    qdac.connect_external_trigger(port, internal)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'outp:trig{port}:sour int{internal.value}',
        f'outp:trig{port}:widt 1e-06'
    ]


def test_connect_external_trigger_width(qdac):  # noqa
    port = 1
    internal = qdac.allocate_trigger()
    # -----------------------------------------------------------------------
    qdac.connect_external_trigger(port, internal, width_s=1e-3)
    # -----------------------------------------------------------------------
    assert qdac.get_recorded_scpi_commands() == [
        f'outp:trig{port}:sour int{internal.value}',
        f'outp:trig{port}:widt 0.001'
    ]
