import pytest

from src.creator.tempo_map import TempoChange, TempoMap, TimeSigChange


def test_constant_120_one_beat_is_500ms():
    tm = TempoMap.constant(120.0)
    assert tm.tick_to_ms(480) == pytest.approx(500.0)
    assert tm.ms_to_tick(500.0) == 480


def test_two_tempos_accumulate_segments():
    tm = TempoMap(480, [TempoChange(0, 500000), TempoChange(960, 1000000)])  # 120 BPM, depois 60 BPM
    assert tm.tick_to_ms(960) == pytest.approx(1000.0)
    assert tm.tick_to_ms(1440) == pytest.approx(2000.0)
    assert tm.ms_to_tick(2000.0) == 1440


def test_roundtrip_ms_tick_within_one_tick():
    tm = TempoMap(480, [TempoChange(0, 500000), TempoChange(1000, 400000), TempoChange(5000, 650000)])
    for tick in range(0, 20000, 37):
        assert abs(tm.ms_to_tick(tm.tick_to_ms(tick)) - tick) <= 1


def test_missing_tick0_defaults_to_120bpm():
    tm = TempoMap(480, [TempoChange(960, 1000000)])
    assert tm.initial_bpm() == pytest.approx(120.0)
    assert tm.tick_to_ms(960) == pytest.approx(1000.0)


def test_zero_tempo_entry_is_discarded():
    tm = TempoMap(480, [TempoChange(0, 500000), TempoChange(480, 0)])
    assert len(tm.tempos) == 1


def test_rescaled_preserves_ms():
    tm = TempoMap(192, [TempoChange(0, 500000), TempoChange(384, 1000000)])
    tm2 = tm.rescaled(480)
    assert tm2.ticks_per_beat == 480
    assert tm2.tick_to_ms(960) == pytest.approx(tm.tick_to_ms(384))


def test_dict_roundtrip():
    tm = TempoMap(480, [TempoChange(0, 500000), TempoChange(960, 600000)], [TimeSigChange(0, 4, 4), TimeSigChange(1920, 3, 4)])
    tm2 = TempoMap.from_dict(tm.to_dict())
    assert tm2.tempos == tm.tempos and tm2.time_sigs == tm.time_sigs
