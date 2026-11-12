"""Tests of the Rigol DHO900 driver against its PyVISA-sim model.

The model (sims/Rigol_DHO900.yaml) stores settings independently of each other and
returns one 1000-point waveform block for every channel: four periods of a 1 V sine.
"""

import math

import pytest
import pyvisa

from qcodes_contrib_drivers.drivers.Rigol.Rigol_DHO900 import (
    MEASUREMENT_ITEMS,
    RigolDHO900,
    offset_limit,
)

SIM = "qcodes_contrib_drivers.sims:Rigol_DHO900.yaml"
ADDRESS = "USB0::0x1AB1::0x044C::DHO9S000000000::INSTR"


@pytest.fixture
def dho():
    scope = RigolDHO900("dho_sim", ADDRESS, pyvisa_sim_file=SIM)
    yield scope
    scope.close()


def commands_sent(monkeypatch):
    """The commands (not queries) written from now on."""
    sent = []
    write = pyvisa.resources.MessageBasedResource.write

    def recording(self, message, *args, **kwargs):
        if "?" not in message:
            sent.append(message)
        return write(self, message, *args, **kwargs)

    monkeypatch.setattr(pyvisa.resources.MessageBasedResource, "write", recording)
    return sent


def test_connect_writes_nothing_and_sends_no_device_clear(monkeypatch):
    sent = commands_sent(monkeypatch)
    cleared = []
    monkeypatch.setattr(RigolDHO900, "device_clear", lambda self: cleared.append(self))
    scope = RigolDHO900("dho_connect", ADDRESS, pyvisa_sim_file=SIM)
    try:
        assert sent == [] and cleared == []
        assert scope.model == "DHO914S"
        assert scope.n_channels == 4
        assert scope.has_awg
        assert [c.short_name for c in scope.channels] == ["ch1", "ch2", "ch3", "ch4"]
    finally:
        scope.close()


def test_snapshot(dho):
    snap = dho.snapshot(update=True)
    assert snap["submodules"]["ch1"]["parameters"]["scale"]["value"] == 0.5
    assert "value" not in snap["submodules"]["ch1"]["parameters"]["trace"]


def test_enumerations(dho, monkeypatch):
    sent = commands_sent(monkeypatch)
    dho.trigger.sweep("normal")
    dho.trigger.edge_slope("either")
    dho.ch1.bandwidth_limit(True)
    assert sent == [":TRIGger:SWEep NORM", ":TRIGger:EDGE:SLOPe RFAL",
                    ":CHANnel1:BWLimit 20M"]
    assert dho.trigger.sweep() == "normal"
    assert dho.ch1.bandwidth_limit() is True


def test_trace_and_time_axis(dho):
    y = dho.ch1.trace()
    t = dho.waveform.time_axis()
    assert y.shape == t.shape == (1000,)
    assert y.max() == pytest.approx(1.0)
    assert y.min() == pytest.approx(-1.0)
    assert t[1] - t[0] == pytest.approx(1e-6)


def test_trace_of_a_channel_that_is_off(dho):
    with pytest.raises(RuntimeError, match="off"):
        dho.ch2.trace()


def test_block_reads_turn_the_termination_character_off(dho, monkeypatch):
    states = []
    query = pyvisa.resources.MessageBasedResource.query_binary_values

    def recording(self, *args, **kwargs):
        states.append(self.read_termination)
        return query(self, *args, **kwargs)

    monkeypatch.setattr(pyvisa.resources.MessageBasedResource, "query_binary_values",
                        recording)
    dho.ch1.trace()
    assert states == [None]
    assert dho.visa_handle.read_termination == "\n"


def test_out_of_range_values_are_refused(dho):
    with pytest.raises(ValueError, match="outside"):
        dho.ch1.scale(200)  # 0.5 V/div at probe ratio 10: at most 100 V/div
    with pytest.raises(ValueError, match="outside"):
        dho.ch1.offset(10.5)
    with pytest.raises(ValueError, match="outside"):
        dho.trigger.edge_level(2.3)
    dho.awg.function("square")
    with pytest.raises(ValueError, match="limit of square"):
        dho.awg.frequency(20e6)
    assert offset_limit(0.05, 1) == 1.0
    assert offset_limit(0.06, 1) == 8.0


def test_settings_the_instrument_would_ignore_are_refused(dho):
    with pytest.raises(ValueError, match="turn the channel on first"):
        dho.ch2.scale(1.0)  # ch2 is off
    with pytest.raises(ValueError, match="modulation is on"):
        dho.awg.am_depth(50)
    with pytest.raises(ValueError, match="counter is on"):
        dho.counter.statistics(True)


def test_measurements(dho):
    assert dho.ch1.vpp() == 2.0
    assert dho.ch1.positive_duty() == 0.5
    assert math.isnan(dho.measure("overshoot", wait=0))
    assert math.isnan(dho.ch2.vpp())  # off: not queried
    assert dho.measure_statistics("vpp")["count"] == 12
    with pytest.raises(ValueError, match="unknown measurement"):
        dho.measure("vpeak")
    assert len(MEASUREMENT_ITEMS) == 42


def test_dvm_reading_while_off_is_nan(dho):
    assert math.isnan(dho.dvm.value())
    dho.dvm.enabled(True)
    assert dho.dvm.value() == pytest.approx(0.7071)


def test_digitize_returns_once_stopped(dho):
    dho.digitize(timeout=2)
    assert dho.trigger.status() == "stop"
