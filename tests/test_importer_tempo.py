"""Testes do importador com várias mudanças de tempo (.mid e .chart)."""
import mido
import pytest
from mido import MidiFile, MidiTrack, Message, MetaMessage

from src.creator.chart_model import ChartSong
from src.creator.chart_importer import _parse_midi_into_song, _parse_chart_file_into_song


def _abs_track(events, name=None):
    """Monta uma trilha a partir de (tick_absoluto, mensagem)."""
    track = MidiTrack()
    if name:
        track.append(MetaMessage('track_name', name=name, time=0))
    last = 0
    for tick, msg in sorted(events, key=lambda e: e[0]):
        msg.time = tick - last
        last = tick
        track.append(msg)
    return track


def _import_mid(tmp_path, tpb=480, tempos=None, extra_tempo_in_events=None, guitar=None):
    mid = MidiFile(ticks_per_beat=tpb)
    mid.tracks.append(_abs_track([(t, MetaMessage('set_tempo', tempo=us)) for t, us in (tempos or [])]))
    events = []
    if extra_tempo_in_events:
        t, us = extra_tempo_in_events
        events.append((t, MetaMessage('set_tempo', tempo=us)))
    mid.tracks.append(_abs_track(events, name="EVENTS"))
    g = []
    for start, dur, note in (guitar or []):
        g.append((start, Message('note_on', note=note, velocity=100)))
        g.append((start + dur, Message('note_off', note=note, velocity=0)))
    mid.tracks.append(_abs_track(g, name="PART GUITAR"))
    path = tmp_path / "notes.mid"
    mid.save(str(path))
    song = ChartSong()
    _parse_midi_into_song(MidiFile(str(path)), song)
    return song


def _import_chart(tmp_path, resolution=192, bpms=None, expert_single=None, ts=None):
    lines = ["[ExpertSingle]", "{"]
    lines += ["  %d = N %d %d" % n for n in (expert_single or [])]
    lines += ["}", "[Song]", "{", "  Resolution = %d" % resolution, "}", "[SyncTrack]", "{"]
    lines += ["  0 = TS 4"]
    lines += ["  %d = B %d" % b for b in (bpms or [])]
    lines += ["  %d = TS %s" % (t, v) for t, v in (ts or [])]
    lines += ["}"]
    path = tmp_path / "notes.chart"
    path.write_text("\n".join(lines), encoding="utf-8")
    song = ChartSong()
    _parse_chart_file_into_song(str(path), song)
    return song


def test_midi_tempo_change_mid_song(tmp_path):
    song = _import_mid(tmp_path, tempos=[(0, 500000), (960, 1000000)], guitar=[(1440, 480, 96)])
    n = song.guitar_notes[0]
    assert n.time_ms == pytest.approx(2000, abs=2)
    assert n.duration_ms == pytest.approx(1000, abs=2)
    assert len(song.tempo_map.tempos) == 2 and song.bpm == pytest.approx(120.0)


def test_midi_tempo_in_non_zero_track_is_used(tmp_path):
    song = _import_mid(tmp_path, tempos=[(0, 500000)], extra_tempo_in_events=(480, 1000000),
                       guitar=[(960, 120, 96)])
    assert song.guitar_notes[0].time_ms == pytest.approx(1500, abs=2)


def test_midi_resolution_192_is_rescaled(tmp_path):
    song = _import_mid(tmp_path, tpb=192, tempos=[(0, 500000)], guitar=[(192, 96, 96)])
    assert song.guitar_notes[0].time_ms == pytest.approx(500, abs=2)
    assert song.tempo_map.ticks_per_beat == 480


def test_chart_multiple_bpm_events(tmp_path):
    song = _import_chart(tmp_path, resolution=192, bpms=[(0, 120000), (384, 60000)],
                         expert_single=[(576, 0, 0)])
    assert song.guitar_notes[0].time_ms == pytest.approx(2000, abs=2)
    assert len(song.tempo_map.tempos) == 2


def test_chart_time_signature_is_read(tmp_path):
    song = _import_chart(tmp_path, bpms=[(0, 120000)], ts=[(768, "6 3")], expert_single=[(0, 0, 0)])
    assert any(ts.numerator == 6 and ts.denominator == 8 for ts in song.tempo_map.time_sigs)
