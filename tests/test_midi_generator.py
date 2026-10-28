"""Testes do gerador MIDI: mapa de tempo, BEAT por compasso, EVENTS e notas sem sobreposição."""
import mido

from src.creator.chart_model import ChartSong, NoteEvent, TextEvent
from src.creator.chart_importer import _parse_midi_into_song
from src.creator.midi_generator import generate_rbn_midi, ms_to_ticks, ticks_to_ms
from src.creator.tempo_map import TempoMap, TempoChange, TimeSigChange


def _track(mid, name):
    for t in mid.tracks:
        if any(m.type == "track_name" and m.name == name for m in t):
            return t
    return None


def _abs(track):
    """Lista de (tick_absoluto, mensagem)."""
    out, tick = [], 0
    for m in track:
        tick += m.time
        out.append((tick, m))
    return out


def _event_texts(mid):
    return [m.text for m in _track(mid, "EVENTS") if m.type == "text"]


def _roundtrip(song, tmp_path):
    mid = generate_rbn_midi(song)
    path = tmp_path / "notes.mid"
    mid.save(str(path))
    back = ChartSong()
    _parse_midi_into_song(mido.MidiFile(str(path)), back)
    return back


def _assert_no_overlaps(track):
    active = set()
    seen_on = set()
    for tick, m in _abs(track):
        if m.type == "note_on" and m.velocity > 0:
            assert m.note not in active, f"note_on {m.note} já ativa no tick {tick}"
            assert (tick, m.note) not in seen_on
            seen_on.add((tick, m.note))
            active.add(m.note)
        elif m.type == "note_off" or (m.type == "note_on" and m.velocity == 0):
            active.discard(m.note)


def test_tempo_track_writes_all_tempo_changes():
    s = ChartSong(bpm=120.0, tempo_map=TempoMap(480, [TempoChange(0, 500000), TempoChange(1920, 400000)]))
    s.guitar_notes = [NoteEvent(time_ms=3000, lane="green", difficulty="Expert")]
    tempos = [m for m in generate_rbn_midi(s).tracks[0] if m.type == "set_tempo"]
    assert [m.tempo for m in tempos] == [500000, 400000]


def test_beat_track_follows_time_signature_change():
    # 4/4 até o tick 1920 e 3/4 depois: primeiros downbeats (nota 12) em 0, 1920, 3360
    tm = TempoMap(480, [TempoChange(0, 500000)], [TimeSigChange(0, 4, 4), TimeSigChange(1920, 3, 4)])
    s = ChartSong(bpm=120.0, tempo_map=tm)
    s.guitar_notes = [NoteEvent(time_ms=3000, lane="green", difficulty="Expert")]
    beat = _track(generate_rbn_midi(s), "BEAT")
    downbeat_ticks = [t for t, m in _abs(beat) if m.type == "note_on" and m.note == 12]
    assert downbeat_ticks[:3] == [0, 1920, 3360]


def test_events_have_single_markers_in_order():
    s = ChartSong(); s.events = [TextEvent(0, "[music_start]"), TextEvent(5000, "[end]")]
    s.guitar_notes = [NoteEvent(time_ms=4000, lane="green", difficulty="Expert")]
    texts = _event_texts(generate_rbn_midi(s))
    assert texts.count("[music_start]") == 1 and texts.count("[music_end]") == 1 and texts.count("[end]") == 1
    assert texts.index("[music_end]") < texts.index("[end]")


def test_dense_same_pitch_notes_do_not_overlap_and_survive_roundtrip(tmp_path):
    # 16 notas green Expert a cada 60 ms com duration_ms=100 (como sai do importador)
    s = ChartSong(bpm=200.0)
    s.guitar_notes = [NoteEvent(time_ms=1000 + i * 60, lane="green", duration_ms=100, difficulty="Expert") for i in range(16)]
    _assert_no_overlaps(_track(generate_rbn_midi(s), "PART GUITAR"))
    back = _roundtrip(s, tmp_path)   # generate_rbn_midi -> save -> _parse_midi_into_song
    assert len([n for n in back.guitar_notes if n.difficulty == "Expert"]) == 16


def test_roundtrip_with_tempo_changes_within_2ms(tmp_path):
    tm = TempoMap(480, [TempoChange(0, 500000), TempoChange(1920, 375000), TempoChange(7680, 600000)])
    s = ChartSong(bpm=120.0, tempo_map=tm)
    s.guitar_notes = [NoteEvent(time_ms=t, lane="red", difficulty="Expert") for t in range(500, 20000, 731)]
    # generate_rbn_midi acrescenta Hard/Medium/Easy em s.guitar_notes; guarda o Expert antes
    expected = [n.time_ms for n in s.guitar_notes]
    back = _roundtrip(s, tmp_path)
    got = [n.time_ms for n in back.guitar_notes if n.difficulty == "Expert"]
    assert len(got) == len(expected)
    assert all(abs(a - b) <= 2 for a, b in zip(expected, got))


def test_overdrive_chord_emits_single_phrase():
    s = ChartSong(bpm=120.0)
    s.guitar_notes = [NoteEvent(time_ms=1000, lane=lane, difficulty="Expert", is_overdrive=True)
                      for lane in ("green", "red", "yellow")]
    guitar = _track(generate_rbn_midi(s), "PART GUITAR")
    od_on = [t for t, m in _abs(guitar) if m.type == "note_on" and m.note == 116]
    assert len(od_on) == 1
    _assert_no_overlaps(guitar)


def test_overdrive_lane_becomes_phrase_spanning_duration():
    s = ChartSong(bpm=120.0)
    s.guitar_notes = [
        NoteEvent(time_ms=1000, lane="green", difficulty="Expert"),
        NoteEvent(time_ms=1000, lane="overdrive", duration_ms=4000, difficulty="Expert", is_overdrive=True),
    ]
    guitar = _track(generate_rbn_midi(s), "PART GUITAR")
    ev = _abs(guitar)
    ons = [t for t, m in ev if m.type == "note_on" and m.note == 116]
    offs = [t for t, m in ev if m.type == "note_off" and m.note == 116]
    # 120 BPM: 1000 ms = 960 ticks, 5000 ms = 4800 ticks
    assert ons == [960] and offs == [4800]
    _assert_no_overlaps(guitar)


def test_constant_bpm_helpers_keep_behavior():
    assert ms_to_ticks(1000, 120.0) == 960
    assert ticks_to_ms(960, 120.0) == 1000
    assert ms_to_ticks(333, 150.0) == int((0.333 * 2.5) * 480)


def test_negative_times_are_clamped_and_midi_saves(tmp_path):
    s = ChartSong(bpm=120.0)
    s.guitar_notes = [NoteEvent(time_ms=-30, lane="green", difficulty="Expert"),
                      NoteEvent(time_ms=1000, lane="red", difficulty="Expert")]
    s.events = [TextEvent(-10, "[section intro]")]
    mid = generate_rbn_midi(s)
    mid.save(str(tmp_path / "neg.mid"))
    for track in mid.tracks:
        assert all(m.time >= 0 for m in track)
    assert "[section intro]" in _event_texts(mid)


def test_user_event_after_total_ticks_stays_before_end():
    s = ChartSong(bpm=120.0)
    s.guitar_notes = [NoteEvent(time_ms=1000, lane="green", difficulty="Expert")]
    s.events = [TextEvent(10_000_000, "[section late]")]
    ev = _track(generate_rbn_midi(s), "EVENTS")
    texts = [(t, m.text) for t, m in _abs(ev) if m.type == "text"]
    names = [x[1] for x in texts]
    assert names.index("[music_end]") < names.index("[end]")
    assert names[-1] == "[end]"
    late = dict((n, t) for t, n in texts)
    assert late["[end]"] > late["[section late]"]
