import pytest
from .sim_qdac2_fixtures import qdac  # noqa


def test_various_operations_have_common_functions(qdac):  # noqa
    operations = [
        qdac.ch01.square_wave(),
        qdac.ch02.sine_wave(),
        qdac.ch03.triangle_wave(),
        qdac.ch04.dc_sweep(start_V=-1, stop_V=1, points=11),
        qdac.ch05.dc_list(voltages=(-1,0,1)),
        qdac.ch05.measurement()
    ]
    # -----------------------------------------------------------------------
    for operation in operations:
        operation.start_on_external(4)
    # -----------------------------------------------------------------------
    commands = qdac.get_recorded_scpi_commands()
    assert 'sour1:squ:trig:sour ext4' in commands
    assert 'sour2:sine:trig:sour ext4' in commands
    assert 'sour3:tri:trig:sour ext4' in commands
    assert 'sour4:dc:trig:sour ext4' in commands
    assert 'sour5:dc:trig:sour ext4' in commands
    assert 'sens5:trig:sour ext4' in commands

    # -----------------------------------------------------------------------
    qdac.free_all_triggers()
    internal = qdac.allocate_trigger()
    for operation in operations:
        operation.start_on(internal)
    # -----------------------------------------------------------------------
    commands = qdac.get_recorded_scpi_commands()
    assert 'sour1:squ:trig:sour int1' in commands
    assert 'sour2:sine:trig:sour int1' in commands
    assert 'sour3:tri:trig:sour int1' in commands
    assert 'sour4:dc:trig:sour int1' in commands
    assert 'sour5:dc:trig:sour int1' in commands
    assert 'sens5:trig:sour int1' in commands
    # -----------------------------------------------------------------------
    for operation in operations:
        operation.abort()
    # -----------------------------------------------------------------------
    commands = qdac.get_recorded_scpi_commands()
    assert 'sour1:squ:abor' in commands
    assert 'sour2:sine:abor' in commands
    assert 'sour3:tri:abor' in commands
    assert 'sour4:dc:abor' in commands
    assert 'sour5:dc:abor' in commands
    assert 'sens5:abor' in commands
