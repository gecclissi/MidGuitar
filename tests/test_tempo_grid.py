"""Grade do editor, snap e geradores seguem o mapa de tempo (mudanças de BPM e de compasso)."""
import pytest

from src.creator.chart_model import ChartSong
from src.creator.tempo_map import TempoChange, TempoMap, TimeSigChange

TPB = 480


def _map():
    # 120 BPM, vai para 90 BPM no tick 3840 (compasso 3) e muda para 3/4 no tick 7680
    return TempoMap(TPB, [TempoChange(0, 500000), TempoChange(3840, 666667)],
                    [TimeSigChange(0, 4, 4), TimeSigChange(7680, 3, 4)])


def _song():
    s = ChartSong(title="t", artist="a")
    s.tempo_map = _map()
    s.bpm = round(s.tempo_map.initial_bpm(), 2)
    return s


def _beat_ms_set(tm, end_ms):
    return [ms for ms, _down in tm.beats_ms(end_ms)]


def _near_beat(tm, t, end_ms, tol=1.5):
    return min(abs(t - b) for b in _beat_ms_set(tm, end_ms)) <= tol


def test_beats_ms_follow_tempo_and_signature():
    tm = _map()
    beats = tm.beats_ms(15000)
    assert beats[0] == (0.0, True)
    assert beats[1][0] == pytest.approx(500.0)
    # depois da mudança para 90 BPM (4000 ms), cada batida tem ~666,7 ms
    assert beats[9][0] - beats[8][0] == pytest.approx(666.667, abs=0.01)
    downs = [ms for ms, d in beats if d]
    # 3/4 a partir do tick 7680: compassos de 3 batidas
    i = next(k for k, (ms, _d) in enumerate(beats) if ms >= tm.tick_to_ms(7680) - 0.01)
    assert [d for _ms, d in beats[i:i + 7]] == [True, False, False, True, False, False, True]
    assert len(downs) >= 4


def test_snap_ms_lands_on_map_beat():
    tm = _map()
    t = tm.tick_to_ms(3840 + 2 * TPB) + 90   # um pouco depois de uma batida a 90 BPM
    snapped = tm.snap_ms(t, 1)
    assert snapped == pytest.approx(tm.tick_to_ms(3840 + 2 * TPB))
    # subdivisão 1/4 de batida: cai em múltiplos de 120 ticks
    s4 = tm.snap_ms(t, 4)
    assert tm.ms_to_tick(s4) % 120 == 0


def test_editor_snap_uses_tempo_map():
    from src.ui.mini_reaper_canvas import snap_time_ms
    s = _song()
    t = s.tempo_map.tick_to_ms(3840 + 3 * TPB) + 70
    assert snap_time_ms(s, t, 1) == pytest.approx(s.tempo_map.tick_to_ms(3840 + 3 * TPB), abs=1)


def test_editor_grid_lines_use_tempo_map():
    from src.ui.mini_reaper_canvas import grid_lines_ms
    s = _song()
    lines = grid_lines_ms(s, 9000)
    assert any(abs(ms - s.tempo_map.tick_to_ms(3840 + TPB)) < 0.01 for ms, _d in lines)
    assert not any(abs(ms - 4500) < 0.01 for ms, _d in lines)   # 120 BPM constante teria 4500


@pytest.mark.parametrize("inst", ["drum", "bass", "guitar", "keys"])
def test_generated_missing_instrument_falls_on_map_beats(inst):
    from src.creator.auto_charter import generate_missing_instruments_only
    s = _song()
    s.duration_ms = 30000
    generate_missing_instruments_only(s, [inst], generate_all_diffs=False)
    notes = [n for n in s.get_track_notes(inst) if n.lane not in ("overdrive", "solo")]
    assert notes
    late = [n for n in notes if n.time_ms > 4500]
    assert late
    # Todas as notas de semínima ficam na grade do mapa (colcheias: metade da batida)
    tm = s.tempo_map
    for n in late:
        tick = tm.ms_to_tick(n.time_ms)
        assert abs(tm.tick_to_ms(round(tick / 240.0) * 240) - n.time_ms) <= 1.5, (inst, n.time_ms)


def test_generated_lyrics_fall_on_map_beats():
    from src.creator.lyric_processor import align_lyrics_to_song
    s = _song()
    align_lyrics_to_song(s, "um dois tres quatro cinco seis sete oito\nnove dez onze doze treze\n",
                         start_delay_ms=3000)
    tm = s.tempo_map
    later = [v for v in s.vocal_notes if v.time_ms > 4500]
    assert later
    for v in later:
        assert _near_beat(tm, v.time_ms, 60000), v.time_ms
