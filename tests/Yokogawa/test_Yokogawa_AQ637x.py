import numpy as np
import pytest

from qcodes_contrib_drivers.drivers.Yokogawa.Yokogawa_AQ637x import YokogawaAQ637x

# Tests run against the PyVISA-sim backend so they can execute in CI. To test
# against a real instrument, comment out the ``pyvisa_sim_file`` argument below.
USE_SIM = True

# The trace ATTRibute keyword commands (write_mode/fix/max_hold/min_hold) rely on
# the instrument normalizing e.g. ``WRITe`` -> ``0`` on read-back, which PyVISA-sim
# cannot emulate (it echoes the stored token verbatim). These are skipped under the
# sim and only run against real hardware.
skip_on_sim = pytest.mark.skipif(
    USE_SIM, reason="requires instrument-side ATTRibute keyword normalization"
)

# Some commands need an instrument-side precondition that a bare bench cannot
# satisfy: gated sweep blocks until an external gate signal arrives, template
# level/wavelength shifts require a template loaded on the instrument, and
# selecting EXTERNAL data-logging memory needs USB media inserted. Under the
# sim these round-trip fine, so they are only skipped against real hardware.
requires_gate_signal = pytest.mark.skipif(
    not USE_SIM, reason="gated sweep blocks without an external gate signal"
)
requires_template = pytest.mark.skipif(
    not USE_SIM, reason="requires a template loaded on the instrument"
)
requires_usb_media = pytest.mark.skipif(
    not USE_SIM, reason="EXTERNAL memory requires USB media inserted"
)
# Queries/commands that are unsupported on the bench AQ6370C (no response ->
# VISA timeout) or need an instrument option / active session not present here.
requires_gpib2 = pytest.mark.skipif(
    not USE_SIM, reason="GP-IB2 port/option not present on the bench instrument"
)
requires_active_logging = pytest.mark.skipif(
    not USE_SIM, reason="ETIMe? requires an active data-logging session"
)
requires_fspeed = pytest.mark.skipif(
    not USE_SIM, reason="FSPeed? is not supported on the AQ6370C"
)
skip_slow_alignment = pytest.mark.skipif(
    not USE_SIM,
    reason="triggers slow physical optical alignment (fired back-to-back "
           "without OPC sync, this intermittently times out on real hardware)",
)


# Real-hardware address, used only when USE_SIM is False. Set this to your
# instrument's VISA resource string when running against physical hardware.
HW_ADDRESS = "TCPIP::<instrument-ip>::INSTR"


@pytest.fixture
def driver():
    if USE_SIM:
        osa = YokogawaAQ637x(
            "OSA",
            address="TCPIP::192.0.2.10::INSTR",
            pyvisa_sim_file="qcodes_contrib_drivers.sims:Yokogawa_AQ637x.yaml",
        )
    else:
        # A longer timeout absorbs the slower responses of a busy instrument.
        osa = YokogawaAQ637x("OSA", address=HW_ADDRESS, timeout=20)
    # Test isolation: abort any continuous sweep a previous test may have left
    # running (REPEAT/AUTO), which would otherwise make settings not take and
    # queries time out on real hardware.
    osa.stop()
    if not USE_SIM:
        # Periodic monitor auto-zeroing closes the shutter for several seconds
        # and makes the instrument drop set-commands while it runs, which
        # intermittently poisons whichever test coincides with it. Disable it
        # for the duration of the hardware test session.
        osa.calibration_zero_auto(False)
    yield osa
    osa.close()


## Common Commands

def test_idn(driver):
    idn_dict = driver.get_idn()
    assert idn_dict['model'] == 'AQ6370C'


def test_clear_status(driver):
    driver.clear_status()


def test_event_status_enable(driver):
    driver.event_status_enable(251)
    assert driver.event_status_enable() == 251


def test_event_status_register(driver):
    val = driver.event_status_register()
    assert isinstance(val, int)
    assert 0 <= val <= 255


def test_operation_complete(driver):
    driver.operation_complete()
    val = driver.operation_complete()
    assert val in (0, 1)


def test_reset(driver):
    driver.reset()


def test_service_request_enable(driver):
    driver.service_request_enable(0)
    assert driver.service_request_enable() == 0


def test_status_byte(driver):
    val = driver.status_byte()
    assert isinstance(val, int)
    assert 0 <= val <= 255


def test_trigger(driver):
    driver.trigger()


def test_wait(driver):
    driver.wait()


def test_self_test(driver):
    val = driver.self_test()
    assert isinstance(val, int)


def test_stop(driver):
    driver.stop()


def test_system_error(driver):
    err = driver.system_error()
    assert isinstance(err, str)
    assert err != ""


## Instrument specific commands
# Display Sub System Commands

@pytest.mark.parametrize("mode", range(0, 6))
def test_display_color(driver, mode):
    driver.display_color(mode)
    assert driver.display_color() == mode


def test_display_enabled(driver):
    driver.display_enabled(False)
    assert driver.display_enabled() is False
    driver.display_enabled(True)
    assert driver.display_enabled() is True


@pytest.mark.parametrize("mode", ["OFF", "LEFT", "RIGHT"])
def test_display_overview_position(driver, mode):
    driver.display_overview_position(mode)
    assert driver.display_overview_position() == mode


@pytest.mark.parametrize("size", ["LARGE", "SMALL"])
def test_display_overview_size(driver, size):
    driver.display_overview_size(size)
    assert driver.display_overview_size() == size


def test_display_split(driver):
    driver.display_split(True)
    assert driver.display_split() is True
    driver.display_split(False)
    assert driver.display_split() is False


def test_display_split_hold_lower(driver):
    driver.display_split(True)
    driver.display_split_hold_lower(True)
    assert driver.display_split_hold_lower() is True
    driver.display_split_hold_lower(False)
    assert driver.display_split_hold_lower() is False


def test_display_split_hold_upper(driver):
    driver.display_split(True)
    driver.display_split_hold_upper(True)
    assert driver.display_split_hold_upper() is True
    driver.display_split_hold_upper(False)
    assert driver.display_split_hold_upper() is False


def test_display_text_clear(driver):
    driver.display_text_clear()


def test_display_text_data(driver):
    text = "Optical Spectrum Analyzer"
    driver.display_text_data(text)
    assert driver.display_text_data() == text


def test_display_trace_x_center(driver):
    val = driver.display_trace_x_center()
    assert isinstance(val, float)
    driver.display_trace_x_center(val)
    assert driver.display_trace_x_center() == val


def test_display_trace_x_initialize(driver):
    driver.display_trace_x_initialize()


def test_display_trace_x_smscale(driver):
    driver.display_trace_x_smscale()


def test_display_trace_x_span(driver):
    val = driver.display_trace_x_span()
    assert isinstance(val, float)
    driver.display_trace_x_span(val)
    assert driver.display_trace_x_span() == val


def test_display_trace_x_srange(driver):
    driver.display_trace_x_srange(True)
    assert driver.display_trace_x_srange() is True
    driver.display_trace_x_srange(False)
    assert driver.display_trace_x_srange() is False


def test_display_trace_x_start(driver):
    val = driver.display_trace_x_start()
    assert isinstance(val, float)
    driver.display_trace_x_start(val)
    assert driver.display_trace_x_start() == val


def test_display_trace_x_stop(driver):
    val = driver.display_trace_x_stop()
    assert isinstance(val, float)
    driver.display_trace_x_stop(val)
    assert driver.display_trace_x_stop() == val


def test_display_trace_y_nmask(driver):
    driver.display_trace_y_nmask(-999)
    assert driver.display_trace_y_nmask() == pytest.approx(-999.0, rel=1e-6)
    driver.display_trace_y_nmask(-40)
    assert driver.display_trace_y_nmask() == pytest.approx(-40.0, rel=1e-6)


@pytest.mark.parametrize("mode", ["VERTICAL", "HORIZONTAL"])
def test_display_trace_y_nmask_type(driver, mode):
    driver.display_trace_y_nmask_type(mode)
    assert driver.display_trace_y_nmask_type() == mode


@pytest.mark.parametrize("n", (8, 10, 12))
def test_display_trace_y_dnumber(driver, n):
    driver.display_trace_y_dnumber(n)
    assert driver.display_trace_y_dnumber() == n


def test_display_trace_y1_blevel(driver):
    val = driver.display_trace_y1_blevel()
    assert isinstance(val, float)
    driver.display_trace_y1_blevel(val)
    assert driver.display_trace_y1_blevel() == val


def test_display_trace_y1_pdivision(driver):
    val = driver.display_trace_y1_pdivision()
    assert isinstance(val, float)
    driver.display_trace_y1_pdivision(val)
    assert driver.display_trace_y1_pdivision() == val


def test_display_trace_y1_rlevel(driver):
    val = driver.display_trace_y1_rlevel()
    assert isinstance(val, float)
    driver.display_trace_y1_rlevel(val)
    assert driver.display_trace_y1_rlevel() == val


def test_display_trace_y1_rposition(driver):
    driver.display_trace_y1_rposition(10)
    assert driver.display_trace_y1_rposition() == 10


@pytest.mark.parametrize("mode", ["LOG", "LINEAR"])
def test_display_trace_y1_spacing(driver, mode):
    driver.display_trace_y1_spacing(mode)
    assert driver.display_trace_y1_spacing() == mode


@pytest.mark.parametrize("unit", ["DBM", "W", "DBM_PER_NM", "W_PER_NM"])
def test_display_trace_y1_unit(driver, unit):
    driver.display_trace_y1_unit(unit)
    assert driver.display_trace_y1_unit() == unit


def test_display_trace_y2_auto(driver):
    driver.display_trace_y2_auto(True)
    assert driver.display_trace_y2_auto() is True
    driver.display_trace_y2_auto(False)
    assert driver.display_trace_y2_auto() is False


def test_display_trace_y2_length(driver):
    val = driver.display_trace_y2_length()
    assert isinstance(val, float)
    driver.display_trace_y2_length(val)
    assert driver.display_trace_y2_length() == val


def test_display_trace_y2_olevel(driver):
    val = driver.display_trace_y2_olevel()
    assert isinstance(val, float)
    driver.display_trace_y2_olevel(val)
    assert driver.display_trace_y2_olevel() == val


def test_display_trace_y2_pdivision(driver):
    val = driver.display_trace_y2_pdivision()
    assert isinstance(val, float)
    driver.display_trace_y2_pdivision(val)
    assert driver.display_trace_y2_pdivision() == val


def test_display_trace_y2_rposition(driver):
    driver.display_trace_y2_rposition(10)
    assert driver.display_trace_y2_rposition() == 10


def test_display_trace_y2_sminimum(driver):
    driver.reset()
    # SMINimum only applies when the Y2 sub-scale is in a linear unit.
    driver.display_trace_y2_unit("LINEAR")
    driver.display_trace_y2_sminimum(0.0)
    assert driver.display_trace_y2_sminimum() == 0.0


@pytest.mark.parametrize("unit", ["DB", "LINEAR", "DB_PER_KM", "PERCENT"])
def test_display_trace_y2_unit(driver, unit):
    driver.display_trace_y2_unit(unit)
    assert driver.display_trace_y2_unit() == unit


@pytest.mark.parametrize("fmt", ["ASCII", "REAL64", "REAL32"])
def test_format_data(driver, fmt):
    driver.format_data(fmt)
    assert driver.format_data() == fmt


def test_sense_average_count(driver):
    driver.sense_average_count(100)
    assert driver.sense_average_count() == 100


def test_sense_bandwidth_resolution(driver):
    val = driver.sense_bandwidth_resolution()
    assert isinstance(val, float)
    driver.sense_bandwidth_resolution(val)
    assert driver.sense_bandwidth_resolution() == val


def test_sense_chopper(driver):
    for mode in ["OFF", "SWITCH"]:
        driver.sense_chopper(mode)
        assert driver.sense_chopper() == mode


def test_sense_correction_level_shift(driver):
    val = driver.sense_correction_level_shift()
    assert isinstance(val, float)
    driver.sense_correction_level_shift(val)
    assert driver.sense_correction_level_shift() == val


@pytest.mark.parametrize("medium", ["AIR", "VACUUM"])
def test_sense_correction_rvelocity_medium(driver, medium):
    driver.sense_correction_rvelocity_medium(medium)
    assert driver.sense_correction_rvelocity_medium() == medium


def test_sense_correction_wavelength_shift(driver):
    val = driver.sense_correction_wavelength_shift()
    assert isinstance(val, float)
    driver.sense_correction_wavelength_shift(val)
    assert driver.sense_correction_wavelength_shift() == val


@pytest.mark.parametrize("mode", ["NORMAL_HOLD", "NORMAL_AUTO", "MID", "HIGH1", "HIGH2", "HIGH3", "NORMAL"])
def test_sense_sensitivity(driver, mode):
    driver.sense_sensitivity(mode)
    assert driver.sense_sensitivity() == mode


@pytest.mark.parametrize("mode", ["OFF", "ON_MODE1"])
def test_sense_setting_correction(driver, mode):
    driver.sense_setting_correction(mode)
    assert driver.sense_setting_correction() == mode


@pytest.mark.parametrize("mode", ["NORMAL", "ANGLED"])
def test_sense_setting_fconnector(driver, mode):
    driver.sense_setting_fconnector(mode)
    assert driver.sense_setting_fconnector() == mode


def test_sense_setting_smoothing(driver):
    driver.sense_setting_smoothing(True)
    assert driver.sense_setting_smoothing() is True
    driver.sense_setting_smoothing(False)
    assert driver.sense_setting_smoothing() is False


def test_sense_sweep_points(driver):
    driver.sense_sweep_points(20001)
    assert driver.sense_sweep_points() == 20001


def test_sense_sweep_points_auto(driver):
    driver.sense_sweep_points_auto(True)
    assert driver.sense_sweep_points_auto() is True
    driver.sense_sweep_points_auto(False)
    assert driver.sense_sweep_points_auto() is False


def test_sense_sweep_segment_points(driver):
    driver.sense_sweep_segment_points(100)
    assert driver.sense_sweep_segment_points() == 100


@pytest.mark.parametrize("speed", ["1X", "2X"])
def test_sense_sweep_speed(driver, speed):
    driver.reset()
    driver.sense_sweep_speed(speed)
    assert driver.sense_sweep_speed() == speed


def test_sense_sweep_step(driver):
    val = driver.sense_sweep_step()
    assert isinstance(val, float)
    driver.sense_sweep_step(val)
    assert driver.sense_sweep_step() == val


def test_sense_sweep_time_0nm(driver):
    driver.sense_sweep_time_0nm(10)
    assert driver.sense_sweep_time_0nm() == 10


def test_sense_sweep_time_interval(driver):
    driver.sense_sweep_time_interval(100)
    assert driver.sense_sweep_time_interval() == 100


def test_sense_sweep_tlssync(driver):
    driver.reset()
    driver.sense_sweep_tlssync(True)
    assert driver.sense_sweep_tlssync() is True
    driver.sense_sweep_tlssync(False)
    assert driver.sense_sweep_tlssync() is False


def test_sense_wavelength_center(driver):
    val = driver.sense_wavelength_center()
    assert isinstance(val, float)
    driver.sense_wavelength_center(val)
    assert driver.sense_wavelength_center() == val


def test_sense_wavelength_span(driver):
    val = driver.sense_wavelength_span()
    assert isinstance(val, float)
    driver.sense_wavelength_span(val)
    assert driver.sense_wavelength_span() == val


def test_sense_wavelength_srange(driver):
    driver.sense_wavelength_srange(True)
    assert driver.sense_wavelength_srange() is True
    driver.sense_wavelength_srange(False)
    assert driver.sense_wavelength_srange() is False


def test_sense_wavelength_start(driver):
    val = driver.sense_wavelength_start()
    assert isinstance(val, float)
    driver.sense_wavelength_start(val)
    assert driver.sense_wavelength_start() == val


def test_sense_wavelength_stop(driver):
    val = driver.sense_wavelength_stop()
    assert isinstance(val, float)
    driver.sense_wavelength_stop(val)
    assert driver.sense_wavelength_stop() == val


def test_trace_state(driver):
    for tr in driver.traces:
        tr.state(False)
        assert tr.state() is False
        tr.state(True)
        assert tr.state() is True


def test_trace_active(driver):
    for tr in driver.traces:
        tr.active()


# 'CALCULATE' is not settable via :TRACe:ATTRibute directly — the attribute
# only becomes CALC once a math expression is assigned via :CALCulate:MATH.
@pytest.mark.parametrize("attribute", ['WRITE', 'FIX', 'MAX_HOLD', 'MIN_HOLD', 'ROLLING_AVERAGE'])
def test_trace_attribute(driver, attribute):
    for tr in driver.traces:
        tr.attribute(attribute)
        assert tr.attribute() == attribute


def test_trace_roll_avg(driver):
    for tr in driver.traces:
        tr.roll_avg(10)
        assert tr.roll_avg() == 10
        tr.roll_avg(2)
        assert tr.roll_avg() == 2


def test_trace_data_sample_number(driver):
    for tr in driver.traces:
        val = tr.data_sample_number()
        assert isinstance(val, int)
        assert val >= 0


def test_trace_axis(driver):
    data = driver.TRA.trace_axis()
    assert isinstance(data, np.ndarray)
    assert data.dtype == np.float64
    # Point count is backend-specific (fixed blob under the sim, live sweep
    # length on real hardware), so only assert the block parsed to some points.
    assert len(data) > 0


def test_trace_data(driver):
    data = driver.TRA.data()
    assert isinstance(data, np.ndarray)
    assert data.dtype == np.float64
    assert len(data) > 0


def test_trace_data_query_binary_contract(driver, monkeypatch):
    # Pin the pyvisa contract for the binary trace read: the REAL64 format maps
    # to datatype 'd' and the AQ637x transmits little-endian (is_big_endian=False).
    # These two choices are what real-hardware testing must confirm.
    captured = {}

    def fake_query_binary_values(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return np.array([1.0, 2.0, 3.0])

    monkeypatch.setattr(driver.visa_handle, "query_binary_values", fake_query_binary_values)

    data = driver.TRA.trace_axis()

    assert captured["cmd"] == ":TRACe:DATA:X? TRA"
    assert captured["kwargs"]["datatype"] == "d"
    assert captured["kwargs"]["is_big_endian"] is False
    np.testing.assert_array_equal(data, np.array([1.0, 2.0, 3.0]))


def test_trace_delete(driver):
    for tr in driver.traces:
        tr.delete()


def test_trace_delete_all(driver):
    driver.delete_all_traces()


@skip_on_sim
def test_trace_write(driver):
    for tr in driver.traces:
        tr.write_mode()
        assert tr.attribute() == 'WRITE'


@skip_on_sim
def test_trace_fix(driver):
    for tr in driver.traces:
        tr.fix()
        assert tr.attribute() == 'FIX'


@skip_on_sim
def test_trace_max_hold(driver):
    for tr in driver.traces:
        tr.max_hold()
        assert tr.attribute() == 'MAX_HOLD'


@skip_on_sim
def test_trace_min_hold(driver):
    for tr in driver.traces:
        tr.min_hold()
        assert tr.attribute() == 'MIN_HOLD'


@pytest.mark.parametrize("mode", ("SINGLE", "REPEAT", "AUTO", "SEGMENT"))
def test_sweep_mode(driver, mode):
    driver.sweep_mode(mode)
    assert driver.sweep_mode() == mode


def test_single(driver):
    driver.single()
    assert driver.sweep_mode() == "SINGLE"


def test_repeat(driver):
    driver.repeat()
    assert driver.sweep_mode() == "REPEAT"


def test_auto(driver):
    driver.auto()
    assert driver.sweep_mode() == "AUTO"


# Model-gated parameter: sense_setting_fiber exists only on AQ6373/AQ6373B.

@pytest.fixture
def driver_aq6373():
    osa = YokogawaAQ637x(
        "OSA6373",
        address="TCPIP::192.0.2.11::INSTR",
        pyvisa_sim_file="qcodes_contrib_drivers.sims:Yokogawa_AQ637x.yaml",
    )
    yield osa
    osa.close()


@pytest.mark.parametrize("mode", ["SMALL", "LARGE"])
def test_sense_setting_fiber(driver_aq6373, mode):
    driver_aq6373.sense_setting_fiber(mode)
    assert driver_aq6373.sense_setting_fiber() == mode


# CALibration Sub System Commands

@skip_slow_alignment
def test_calibration_align(driver):
    driver.align()
    driver.align_external()
    driver.align_internal()


def test_calibrate_bandwidth(driver):
    driver.calibrate_bandwidth()
    driver.calibrate_bandwidth_initialize()


def test_calibration_bandwidth_wavelength(driver):
    val = driver.calibration_bandwidth_wavelength()
    assert isinstance(val, float)


def test_calibrate_wavelength(driver):
    driver.calibrate_wavelength_internal()
    driver.calibrate_wavelength_external()


# EMISSION is not selectable on the AQ6370C (the set is rejected); it is kept
# in the driver's mapping for models that support it.
@pytest.mark.parametrize("source", ["LASER", "GASCELL"])
def test_calibration_wavelength_external_source(driver, source):
    driver.calibration_wavelength_external_source(source)
    assert driver.calibration_wavelength_external_source() == source


def test_calibration_wavelength_external_wavelength(driver):
    driver.calibration_wavelength_external_wavelength(1.55e-6)
    assert driver.calibration_wavelength_external_wavelength() == pytest.approx(1.55e-6)


def test_calibration_zero_auto(driver):
    driver.calibration_zero_auto(True)
    assert driver.calibration_zero_auto() is True
    driver.calibration_zero_auto(False)
    assert driver.calibration_zero_auto() is False


def test_zero_once(driver):
    driver.zero_once()


def test_calibration_zero_interval(driver):
    driver.calibration_zero_interval(20)
    assert driver.calibration_zero_interval() == 20


def test_calibration_zero_status(driver):
    val = driver.calibration_zero_status()
    assert isinstance(val, int)


def test_calibration_power_offset_table(driver):
    driver.calibration_power_offset_table(1, 0.5)


def test_calibration_wavelength_offset_table(driver):
    driver.calibration_wavelength_offset_table(1, 0.0)


# TRIGger Sub System Commands

def test_trigger_delay(driver):
    driver.trigger_delay(1.0e-3)
    assert driver.trigger_delay() == pytest.approx(1.0e-3)


@requires_gate_signal
def test_trigger_gate_time(driver):
    driver.trigger_gate_time(2.0e-3)
    assert driver.trigger_gate_time() == pytest.approx(2.0e-3)


@requires_gate_signal
@pytest.mark.parametrize("logic", ["POSITIVE", "NEGATIVE"])
def test_trigger_gate_logic(driver, logic):
    driver.trigger_gate_logic(logic)
    assert driver.trigger_gate_logic() == logic


@requires_gate_signal
@pytest.mark.parametrize("slope", ["RISE", "FALL"])
def test_trigger_gate_slope(driver, slope):
    driver.trigger_gate_slope(slope)
    assert driver.trigger_gate_slope() == slope


@requires_gate_signal
@pytest.mark.parametrize("state", ["OFF", "ON", "PEAK_HOLD"])
def test_trigger_gate_state(driver, state):
    driver.trigger_gate_state(state)
    assert driver.trigger_gate_state() == state


@pytest.mark.parametrize("mode", ["EXTERNAL_TRIGGER", "SAMPLE_TRIGGER", "SWEEP_ENABLE"])
def test_trigger_input(driver, mode):
    # :TRIGger:DELay/:PHOLd:HTIMe (exercised by the tests above) engage
    # "external trigger mode" (:TRIGger:STATe ON/PHOLd) as a side effect;
    # while that is engaged, :TRIGger:INPut changes are silently ignored.
    driver.write(":TRIGger:STATe 0")
    driver.trigger_input(mode)
    assert driver.trigger_input() == mode


@pytest.mark.parametrize("mode", ["OFF", "SWEEP_STATUS"])
def test_trigger_output(driver, mode):
    driver.trigger_output(mode)
    assert driver.trigger_output() == mode


def test_trigger_phold_htime(driver):
    # :TRIGger:PHOLd:HTIMe is silently ignored unless :TRIGger:INPut is
    # ETRigger (EXTERNAL_TRIGGER); test_trigger_input above can leave it on
    # a different source.
    driver.trigger_input("EXTERNAL_TRIGGER")
    driver.trigger_phold_htime(5.0e-3)
    assert driver.trigger_phold_htime() == pytest.approx(5.0e-3)


# MEMory Sub System Commands (command-string construction)

def test_memory_store(driver, monkeypatch):
    sent = []
    monkeypatch.setattr(driver, "write", lambda cmd: sent.append(cmd))
    driver.memory_store(1, "TRA")
    assert sent == [":MEMory:STORe 1,TRA"]


def test_memory_load(driver, monkeypatch):
    sent = []
    monkeypatch.setattr(driver, "write", lambda cmd: sent.append(cmd))
    driver.memory_load(2, "TRB")
    assert sent == [":MEMory:LOAD 2,TRB"]


def test_memory_clear(driver, monkeypatch):
    sent = []
    monkeypatch.setattr(driver, "write", lambda cmd: sent.append(cmd))
    driver.memory_clear(3)
    assert sent == [":MEMory:CLEar 3"]


def test_memory_empty(driver, monkeypatch):
    asked = []

    def fake_ask(cmd):
        asked.append(cmd)
        return "1"

    monkeypatch.setattr(driver, "ask", fake_ask)
    assert driver.memory_empty(1) == 1
    assert asked == [":MEMory:EMPty? 1"]


# MMEMory Sub System Commands (command-string construction)

MMEMORY_WRITE_CASES = [
    (lambda d: d.mmemory_auto_name("DATE"), ":MMEMory:ANAMe DATE"),
    (lambda d: d.mmemory_change_directory("logs"), ':MMEMory:CDIRectory "logs"'),
    (lambda d: d.mmemory_change_drive("EXTernal"), ":MMEMory:CDRive EXTernal"),
    (lambda d: d.mmemory_copy("a.csv", "b.csv"), ':MMEMory:COPY "a.csv","b.csv"'),
    (lambda d: d.mmemory_copy("a", "b", "INTernal", "EXTernal"),
     ':MMEMory:COPY "a",INTernal,"b",EXTernal'),
    (lambda d: d.mmemory_delete("a.csv"), ':MMEMory:DELete "a.csv"'),
    (lambda d: d.mmemory_make_directory("d"), ':MMEMory:MDIRectory "d"'),
    (lambda d: d.mmemory_remove(), ":MMEMory:REMove"),
    (lambda d: d.mmemory_rename("new", "old"), ':MMEMory:REName "new","old"'),
    (lambda d: d.mmemory_load_all_trace("f"), ':MMEMory:LOAD:ATRace "f"'),
    (lambda d: d.mmemory_load_data_logging("f"), ':MMEMory:LOAD:DLOGing "f"'),
    (lambda d: d.mmemory_load_memory(1, "f"), ':MMEMory:LOAD:MEMory 1,"f"'),
    (lambda d: d.mmemory_load_program(1, "f"), ':MMEMory:LOAD:PROGram 1,"f"'),
    (lambda d: d.mmemory_load_setting("f"), ':MMEMory:LOAD:SETTing "f"'),
    (lambda d: d.mmemory_load_template("TEMPL", "f"), ':MMEMory:LOAD:TEMPlate TEMPL,"f"'),
    (lambda d: d.mmemory_load_trace("TRA", "f"), ':MMEMory:LOAD:TRACe TRA,"f"'),
    (lambda d: d.mmemory_store_analysis_result("f"), ':MMEMory:STORe:ARESult "f"'),
    (lambda d: d.mmemory_store_all_trace("f"), ':MMEMory:STORe:ATRace "f"'),
    (lambda d: d.mmemory_store_data("f"), ':MMEMory:STORe:DATA "f"'),
    (lambda d: d.mmemory_store_data_item("TRACe", True), ":MMEMory:STORe:DATA:ITEM TRACe,1"),
    (lambda d: d.mmemory_store_data_mode("OVER"), ":MMEMory:STORe:DATA:MODE OVER"),
    (lambda d: d.mmemory_store_data_type("CSV"), ":MMEMory:STORe:DATA:TYPE CSV"),
    (lambda d: d.mmemory_store_data_logging("f"), ':MMEMory:STORe:DLOGging "f"'),
    (lambda d: d.mmemory_store_data_logging_csave(True), ":MMEMory:STORe:DLOGging:CSAVe 1"),
    (lambda d: d.mmemory_store_data_logging_tsave(False), ":MMEMory:STORe:DLOGging:TSAVe 0"),
    (lambda d: d.mmemory_store_graphics("COLor", "BMP", "img"),
     ':MMEMory:STORe:GRAPhics COLor,BMP,"img"'),
    (lambda d: d.mmemory_store_memory(1, "CSV", "f"), ':MMEMory:STORe:MEMory 1,CSV,"f"'),
    (lambda d: d.mmemory_store_program(1, "f"), ':MMEMory:STORe:PROGram 1,"f"'),
    (lambda d: d.mmemory_store_setting("f"), ':MMEMory:STORe:SETTing "f"'),
    (lambda d: d.mmemory_store_template("TEMPL", "f"), ':MMEMory:STORe:TEMPlate TEMPL,"f"'),
    (lambda d: d.mmemory_store_trace("TRA", "CSV", "spec"), ':MMEMory:STORe:TRACe TRA,CSV,"spec"'),
    (lambda d: d.mmemory_store_trace("TRA", "CSV", "spec", "INTernal"),
     ':MMEMory:STORe:TRACe TRA,CSV,"spec",INTernal'),
]


@pytest.mark.parametrize("action,expected", MMEMORY_WRITE_CASES)
def test_mmemory_write_command(driver, monkeypatch, action, expected):
    sent = []
    monkeypatch.setattr(driver, "write", lambda cmd: sent.append(cmd))
    action(driver)
    assert sent == [expected]


def test_mmemory_catalog(driver, monkeypatch):
    asked = []

    def fake_ask(cmd):
        asked.append(cmd)
        return '256,"spectrum.csv"'

    monkeypatch.setattr(driver, "ask", fake_ask)
    driver.mmemory_catalog()
    driver.mmemory_catalog("INTernal")
    assert asked == [":MMEMory:CATalog?", ":MMEMory:CATalog? INTernal"]


def test_mmemory_data(driver, monkeypatch):
    asked = []

    def fake_ask(cmd):
        asked.append(cmd)
        return "raw"

    monkeypatch.setattr(driver, "ask", fake_ask)
    driver.mmemory_data("spectrum.csv")
    assert asked == [':MMEMory:DATA? "spectrum.csv"']


# CALCulate Sub System — Auto markers (AMARker1 round-trip via sim)

@pytest.mark.xfail(
    condition=not USE_SIM,
    reason="advanced-marker assignment intermittently wedges after enough "
           "real-hardware round trips in a suite run (STATe writes are "
           "silently ignored, no error/timeout); only a full *RST clears it, "
           "but that corrupts the trace data the later amarker value tests "
           "rely on, so it is not applied here",
    strict=False,
)
def test_amarker1_state(driver):
    # Assigning a moving marker needs an active trace; select one non-
    # destructively (this preserves the acquired spectrum the later
    # amarker value tests rely on, unlike a full *RST). Also clear any
    # "external trigger mode" (:TRIGger:STATe) left engaged by the TRIGger
    # tests above (PHOLd mode has been observed to block marker assignment).
    driver.write(":TRIGger:STATe 0")
    driver.TRA.active()
    driver.amarker1.state(True)
    assert driver.amarker1.state() is True
    driver.amarker1.state(False)
    assert driver.amarker1.state() is False


@pytest.mark.parametrize("tr", ["TRA", "TRC", "TRG"])
def test_amarker1_trace(driver, tr):
    driver.amarker1.trace(tr)
    assert driver.amarker1.trace() == tr


def test_amarker1_x(driver):
    driver.amarker1.x(1.55e-6)
    assert driver.amarker1.x() == pytest.approx(1.55e-6)


def test_amarker1_y(driver):
    assert isinstance(driver.amarker1.y(), float)


def test_amarker1_integral(driver):
    driver.amarker1.integral_state(True)
    assert driver.amarker1.integral_state() is True
    # IRANge is an integration *frequency* range in Hz.
    driver.amarker1.integral_range(40e9)
    assert driver.amarker1.integral_range() == pytest.approx(40e9)
    assert isinstance(driver.amarker1.integral_result(), float)


def test_amarker1_pdensity(driver):
    driver.amarker1.pdensity_state(True)
    assert driver.amarker1.pdensity_state() is True
    driver.amarker1.pdensity_bandwidth(1.0e-9)
    assert driver.amarker1.pdensity_bandwidth() == pytest.approx(1.0e-9)
    assert isinstance(driver.amarker1.pdensity_result(), float)


AMARKER_ACTION_CASES = [
    (lambda m: m.off(), "AOFF"),
    (lambda m: m.function_preset(), "FUNCtion:PRESet"),
    (lambda m: m.maximum(), "MAXimum"),
    (lambda m: m.maximum_left(), "MAXimum:LEFT"),
    (lambda m: m.maximum_next(), "MAXimum:NEXT"),
    (lambda m: m.maximum_right(), "MAXimum:RIGHt"),
    (lambda m: m.minimum(), "MINimum"),
    (lambda m: m.minimum_left(), "MINimum:LEFT"),
    (lambda m: m.minimum_next(), "MINimum:NEXT"),
    (lambda m: m.minimum_right(), "MINimum:RIGHt"),
]


@pytest.mark.parametrize("idx", [1, 2, 3, 4])
@pytest.mark.parametrize("action,suffix", AMARKER_ACTION_CASES)
def test_amarker_action(driver, monkeypatch, idx, action, suffix):
    marker = getattr(driver, f"amarker{idx}")
    sent = []
    monkeypatch.setattr(marker, "write", lambda cmd: sent.append(cmd))
    action(marker)
    assert sent == [f":CALCulate:AMARker{idx}:{suffix}"]


def test_amarkers_channeltuple(driver):
    assert len(driver.amarkers) == 4


# CALCulate Sub System — Manual markers (instrument-level params via sim)

def test_marker_auto(driver):
    driver.marker_auto(True)
    assert driver.marker_auto() is True
    driver.marker_auto(False)
    assert driver.marker_auto() is False


@pytest.mark.parametrize("fmt", ["OFFSET", "SPACING"])
def test_marker_function_format(driver, fmt):
    driver.marker_function_format(fmt)
    assert driver.marker_function_format() == fmt


def test_marker_function_update(driver):
    driver.marker_function_update(True)
    assert driver.marker_function_update() is True


def test_marker_maximum_scenter_auto(driver):
    driver.marker_maximum_scenter_auto(True)
    assert driver.marker_maximum_scenter_auto() is True


def test_marker_maximum_srlevel_auto(driver):
    driver.marker_maximum_srlevel_auto(True)
    assert driver.marker_maximum_srlevel_auto() is True


def test_marker_msearch(driver):
    driver.marker_msearch(True)
    assert driver.marker_msearch() is True


@pytest.mark.parametrize("sort", ["WAVELENGTH", "LEVEL"])
def test_marker_msearch_sort(driver, sort):
    driver.marker_msearch_sort(sort)
    assert driver.marker_msearch_sort() == sort


def test_marker_msearch_threshold(driver):
    driver.marker_msearch_threshold(10.0)
    assert driver.marker_msearch_threshold() == pytest.approx(10.0)


# WNUMBER is only available on the AQ6375/AQ6375B; the sim/bench is an AQ6370C.
@pytest.mark.parametrize("unit", ["WAVELENGTH", "FREQUENCY"])
def test_marker_unit(driver, unit):
    driver.marker_unit(unit)
    assert driver.marker_unit() == unit


MARKER_ACTION_CASES = [
    (lambda d: d.clear_all_markers(), ":CALCulate:MARKer:AOFF"),
    (lambda d: d.marker_maximum(), ":CALCulate:MARKer:MAXimum"),
    (lambda d: d.marker_maximum_left(), ":CALCulate:MARKer:MAXimum:LEFT"),
    (lambda d: d.marker_maximum_next(), ":CALCulate:MARKer:MAXimum:NEXT"),
    (lambda d: d.marker_maximum_right(), ":CALCulate:MARKer:MAXimum:RIGHt"),
    (lambda d: d.marker_maximum_scenter(), ":CALCulate:MARKer:MAXimum:SCENter"),
    (lambda d: d.marker_maximum_srlevel(), ":CALCulate:MARKer:MAXimum:SRLevel"),
    (lambda d: d.marker_maximum_szcenter(), ":CALCulate:MARKer:MAXimum:SZCenter"),
    (lambda d: d.marker_minimum(), ":CALCulate:MARKer:MINimum"),
    (lambda d: d.marker_minimum_left(), ":CALCulate:MARKer:MINimum:LEFT"),
    (lambda d: d.marker_minimum_next(), ":CALCulate:MARKer:MINimum:NEXT"),
    (lambda d: d.marker_minimum_right(), ":CALCulate:MARKer:MINimum:RIGHt"),
    (lambda d: d.marker_scenter(), ":CALCulate:MARKer:SCENter"),
    (lambda d: d.marker_srlevel(), ":CALCulate:MARKer:SRLevel"),
    (lambda d: d.marker_szcenter(), ":CALCulate:MARKer:SZCenter"),
    (lambda d: d.marker_set_state(2, True), ":CALCulate:MARKer:STATe 2,1"),
    (lambda d: d.marker_set_x(2, 1.55e-6), ":CALCulate:MARKer:X 2,1.55e-06"),
    (lambda d: d.line_marker_all_off(), ":CALCulate:LMARker:AOFF"),
    (lambda d: d.line_marker_sspan(), ":CALCulate:LMARker:SSPan"),
    (lambda d: d.line_marker_szspan(), ":CALCulate:LMARker:SZSPan"),
    (lambda d: d.line_marker_set_x(1, 1.55e-6), ":CALCulate:LMARker:X 1,1.55e-06"),
    (lambda d: d.line_marker_set_y(3, -20.0), ":CALCulate:LMARker:Y 3,-20.0"),
]


@pytest.mark.parametrize("action,expected", MARKER_ACTION_CASES)
def test_marker_action_command(driver, monkeypatch, action, expected):
    sent = []
    monkeypatch.setattr(driver, "write", lambda cmd: sent.append(cmd))
    action(driver)
    assert sent == [expected]


def test_marker_get_x_y(driver, monkeypatch):
    asked = []

    def fake_ask(cmd):
        asked.append(cmd)
        return "1.55e-06"

    monkeypatch.setattr(driver, "ask", fake_ask)
    assert driver.marker_get_x(2) == pytest.approx(1.55e-6)
    assert driver.marker_get_y(2) == pytest.approx(1.55e-6)
    assert asked == [":CALCulate:MARKer:X? 2", ":CALCulate:MARKer:Y? 2"]


def test_line_marker_srange(driver):
    driver.line_marker_srange(True)
    assert driver.line_marker_srange() is True
    driver.line_marker_srange(False)
    assert driver.line_marker_srange() is False


# Phase 4 — SYSTem / STATus / UNIT / template / data-logging parameters (sim round-trip)

def test_system_version(driver):
    assert isinstance(driver.system_version(), str)


@requires_fspeed
def test_system_fspeed(driver):
    assert isinstance(driver.system_fspeed(), str)


@pytest.mark.parametrize("param", [
    "system_buzzer_click", "system_buzzer_warning",
    pytest.param("system_communicate_gpib2_scontroller", marks=requires_gpib2),
    "system_communicate_lockout",
    "system_communicate_rmonitor", "system_display_transparent", "system_display_uncal",
])
def test_system_on_off_params(driver, param):
    p = getattr(driver, param)
    p(True)
    assert p() is True
    p(False)
    assert p() is False


@requires_gpib2
def test_system_gpib2_addresses(driver):
    driver.system_communicate_gpib2_address(5)
    assert driver.system_communicate_gpib2_address() == 5
    driver.system_communicate_gpib2_tls_address(7)
    assert driver.system_communicate_gpib2_tls_address() == 7


def test_system_date_time(driver):
    # The instrument does not zero-pad month/day on read-back.
    driver.system_date("2026,7,21")
    assert driver.system_date() == "2026,7,21"
    # Time is set as "hh,mm,ss" but read back as "hh:mm:ss" on hardware
    # (seconds truncated to 00); normalize the separator before comparing.
    driver.system_time("12,30,00")
    assert driver.system_time().replace(":", ",") == "12,30,00"


@pytest.mark.parametrize("grid", ["12.5GHZ", "50GHZ", "CUSTOM"])
def test_system_grid(driver, grid):
    driver.system_grid(grid)
    assert driver.system_grid() == grid


def test_system_grid_custom_values(driver):
    # Reset so the display unit is wavelength (the grid start/stop read-back
    # unit follows it), then enable CUSTOM grid mode to edit its values.
    driver.reset()
    driver.system_grid("CUSTOM")
    driver.system_grid_custom_spacing(50.0)
    assert driver.system_grid_custom_spacing() == pytest.approx(50.0)
    driver.system_grid_custom_start(1.5e-6)
    assert driver.system_grid_custom_start() == pytest.approx(1.5e-6)
    driver.system_grid_custom_stop(1.6e-6)
    assert driver.system_grid_custom_stop() == pytest.approx(1.6e-6)
    driver.system_grid_reference(1.55e-6)
    assert driver.system_grid_reference() == pytest.approx(1.55e-6)


def test_status_operation_registers(driver):
    assert isinstance(driver.status_operation_condition(), int)
    assert isinstance(driver.status_operation_event(), int)
    driver.status_operation_enable(255)
    assert driver.status_operation_enable() == 255


def test_status_questionable_registers(driver):
    assert isinstance(driver.status_questionable_condition(), int)
    assert isinstance(driver.status_questionable_event(), int)
    driver.status_questionable_enable(128)
    assert driver.status_questionable_enable() == 128


@pytest.mark.parametrize("digit", [1, 2, 3])
def test_unit_power_digit(driver, digit):
    driver.unit_power_digit(digit)
    assert driver.unit_power_digit() == digit


# WNUMBER is only available on the AQ6375/AQ6375B; the sim/bench is an AQ6370C.
@pytest.mark.parametrize("unit", ["WAVELENGTH", "FREQUENCY"])
def test_unit_x(driver, unit):
    driver.unit_x(unit)
    assert driver.unit_x() == unit


@requires_template
def test_template_gonogo(driver):
    driver.template_gonogo(True)
    assert driver.template_gonogo() is True


@requires_template
def test_template_level_shift(driver):
    driver.template_level_shift(3.0)
    assert driver.template_level_shift() == pytest.approx(3.0)


def test_template_result(driver):
    assert isinstance(driver.template_result(), str)


@pytest.mark.parametrize("ttype", ["UPPER", "LOWER", "UPPER_AND_LOWER"])
def test_template_ttype(driver, ttype):
    driver.template_ttype(ttype)
    assert driver.template_ttype() == ttype


@requires_template
def test_template_wavelength_shift(driver):
    driver.template_wavelength_shift(1.0e-9)
    assert driver.template_wavelength_shift() == pytest.approx(1.0e-9)


@requires_active_logging
def test_dlog_elapsed_time(driver):
    assert isinstance(driver.dlog_elapsed_time(), int)


def test_dlog_numeric_params(driver):
    driver.dlog_interval(5)
    assert driver.dlog_interval() == 5
    driver.dlog_item(2)
    assert driver.dlog_item() == 2
    driver.dlog_lmode(2)
    assert driver.dlog_lmode() == 2
    driver.dlog_tduration(60)
    assert driver.dlog_tduration() == 60
    # MTHResh is a wavelength-match threshold in metres (not a dB level).
    driver.dlog_mthresh(1.0e-9)
    assert driver.dlog_mthresh() == pytest.approx(1.0e-9)
    driver.dlog_pdetect_athresh(-50.0)
    assert driver.dlog_pdetect_athresh() == pytest.approx(-50.0)
    # RTHResh (relative peak-detection threshold) is a positive dB value.
    driver.dlog_pdetect_rthresh(3.0)
    assert driver.dlog_pdetect_rthresh() == pytest.approx(3.0)


@pytest.mark.parametrize("mem", [
    "INTERNAL",
    pytest.param("EXTERNAL", marks=requires_usb_media),
])
def test_dlog_memory(driver, mem):
    driver.dlog_memory(mem)
    assert driver.dlog_memory() == mem


@pytest.mark.parametrize("ttype", ["ABSOLUTE", "RELATIVE"])
def test_dlog_pdetect_ttype(driver, ttype):
    driver.dlog_pdetect_ttype(ttype)
    assert driver.dlog_pdetect_ttype() == ttype


def test_dlog_tlogging(driver):
    driver.dlog_tlogging(True)
    assert driver.dlog_tlogging() is True


@pytest.mark.parametrize("state", ["STOP", "START"])
def test_dlog_state(driver, state):
    driver.dlog_state(state)
    assert driver.dlog_state() == state


# Phase 4 — action / argument commands (command-string construction)

PHASE4_ACTION_CASES = [
    (lambda d: d.status_operation_preset(), ":STATus:OPERation:PRESet"),
    (lambda d: d.system_preset(), ":SYSTem:PRESet"),
    (lambda d: d.system_operator_lock(True, "pw"), ':SYSTem:OLOCK 1,"pw"'),
    (lambda d: d.system_grid_custom_clear_all(), ":SYSTem:GRID:CUSTom:CLEar:ALL"),
    (lambda d: d.system_grid_custom_delete(2), ":SYSTem:GRID:CUSTom:DELete 2"),
    (lambda d: d.system_grid_custom_insert(1.55e-6), ":SYSTem:GRID:CUSTom:INSert 1.55e-06M"),
    (lambda d: d.display_position("TRA", "UP"), ":DISPlay:POSition TRA,UP"),
    (lambda d: d.program_execute(1), ":PROGram:EXECute 1"),
    (lambda d: d.trace_copy("TRA", "TRB"), ":TRACe:COPY TRA,TRB"),
    (lambda d: d.template_data("TEMPL", 1.55e-6, -20.0), ":TRACe:TEMPlate:DATA TEMPL,1.55e-06,-20.0"),
    (lambda d: d.template_all_delete("TEMPL"), ":TRACe:TEMPlate:ADELete TEMPL"),
    (lambda d: d.template_edit_type("TEMPL", "A"), ":TRACe:TEMPlate:ETYPe TEMPL,A"),
    (lambda d: d.template_mode("TEMPL", "ABSolute"), ":TRACe:TEMPlate:MODE TEMPL,ABSolute"),
    (lambda d: d.template_display("TEMPL", True), ":TRACe:TEMPlate:DISPlay TEMPL,1"),
]


@pytest.mark.parametrize("action,expected", PHASE4_ACTION_CASES)
def test_phase4_action_command(driver, monkeypatch, action, expected):
    sent = []
    monkeypatch.setattr(driver, "write", lambda cmd: sent.append(cmd))
    action(driver)
    assert sent == [expected]


def test_system_information(driver, monkeypatch):
    asked = []

    def fake_ask(cmd):
        asked.append(cmd)
        return "info"

    monkeypatch.setattr(driver, "ask", fake_ask)
    driver.system_information(0)
    assert asked == [":SYSTem:INFormation? 0"]


def test_trace_power_density(driver, monkeypatch):
    asked = []

    def fake_ask(cmd):
        asked.append(cmd)
        return "-45.0"

    monkeypatch.setattr(driver, "ask", fake_ask)
    driver.trace_power_density("TRA", 1.0e-9)
    assert asked == [":TRACe:PDENsity? TRA,1e-09"]
