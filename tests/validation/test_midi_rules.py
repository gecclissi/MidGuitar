"""Testes das regras de MIDI do validador."""
import mido

from src.creator.auto_charter import auto_generate_chart
from src.creator.chart_model import ChartSong
from src.creator.midi_generator import generate_rbn_midi, save_midi
from src.creator.validation import Issue, PROFILES, has_errors, midi_track_names, validate_midi


def _trk(name, notes=(), texts=(), tempo=False):
    """notes: (início, fim, altura, velocity); texts: (tick, texto)."""
    ev = []
    for s, e, p, v in notes:
        ev.append((s, 1, mido.Message("note_on", note=p, velocity=v)))
        ev.append((e, 0, mido.Message("note_off", note=p, velocity=0)))
    for tk, tx in texts:
        ev.append((tk, 0, mido.MetaMessage("text", text=tx)))
    ev.sort(key=lambda x: (x[0], x[1]))
    t = mido.MidiTrack([mido.MetaMessage("track_name", name=name)])
    if tempo:
        t.append(mido.MetaMessage("set_tempo", tempo=500000))
    last = 0
    for tk, _, m in ev:
        m.time = tk - last
        last = tk
        t.append(m)
    return t


def _write_mid(tmp_path, tracks, tpb=480, name="t.mid"):
    mid = mido.MidiFile(type=1, ticks_per_beat=tpb)
    mid.tracks.extend(tracks)
    p = tmp_path / name
    mid.save(str(p))
    return str(p)


def _full(extra=(), events_texts=None):
    """MIDI mínimo válido para o RB3 mais trilhas extras."""
    texts = events_texts if events_texts is not None else [
        (0, "[music_start]"), (4000, "[music_end]"), (4000, "[end]")]
    return [_trk("tempo", tempo=True),
            _trk("BEAT", [(i * 480, i * 480 + 10, 12 if i % 4 == 0 else 13, 100) for i in range(9)]),
            _trk("EVENTS", texts=texts)] + list(extra)


def _codes(issues):
    return [(i.code, i.level) for i in issues]


def _plain(issues):
    return [i.code for i in issues]


def test_generated_song_passes_rb3_profile(tmp_path):
    s = auto_generate_chart(ChartSong(title="T", artist="A", bpm=120.0), total_duration_ms=60000,
                            selected_instruments=["guitar", "bass", "drum", "keys", "pro_guitar",
                                                  "pro_bass", "pro_keys"])
    p = tmp_path / "x.mid"
    save_midi(generate_rbn_midi(s), str(p))
    assert [i for i in validate_midi(str(p), PROFILES["rb3_ps3"]) if i.level == "error"] == []
    assert "BEAT" in midi_track_names(str(p))


def test_clean_minimal_midi_has_no_issues(tmp_path):
    p = _write_mid(tmp_path, _full([_trk("PART GUITAR", [(0, 100, 96, 100)])]))
    assert validate_midi(p, PROFILES["rb3_ps3"]) == []


def test_unreadable_file_is_error_not_exception(tmp_path):
    p = tmp_path / "bad.mid"
    p.write_bytes(b"not a midi")
    assert _plain(validate_midi(str(p), PROFILES["clonehero"])) == ["MIDI_UNREADABLE"]
    assert midi_track_names(str(p)) == set()


def test_missing_beat_is_error_for_rb3_warning_for_ch(tmp_path):
    tracks = [t for t in _full() if t[0].name != "BEAT"]
    p = _write_mid(tmp_path, tracks)
    assert ("MIDI_NO_BEAT", "error") in _codes(validate_midi(p, PROFILES["rb3_ps3"]))
    assert ("MIDI_NO_BEAT", "warning") in _codes(validate_midi(p, PROFILES["clonehero"]))


def test_forbidden_keys_track_on_rb2(tmp_path):
    p = _write_mid(tmp_path, _full([_trk("PART KEYS", [(0, 100, 96, 100)])]))
    assert ("MIDI_FORBIDDEN_TRACK", "error") in _codes(validate_midi(p, PROFILES["rb2"]))
    assert "MIDI_FORBIDDEN_TRACK" not in _plain(validate_midi(p, PROFILES["rb3_ps3"]))


def test_end_before_last_note(tmp_path):
    p = _write_mid(tmp_path, _full([_trk("PART GUITAR", [(0, 5000, 96, 100)])]))
    assert ("MIDI_END_BEFORE_NOTES", "error") in _codes(validate_midi(p, PROFILES["rb3_ps3"]))


def test_missing_marker_levels(tmp_path):
    p = _write_mid(tmp_path, _full(events_texts=[(0, "[music_start]")]))
    assert ("MIDI_MISSING_MARKER", "error") in _codes(validate_midi(p, PROFILES["rb3_ps3"]))
    assert ("MIDI_MISSING_MARKER", "warning") in _codes(validate_midi(p, PROFILES["clonehero"]))


def test_overlapping_same_pitch(tmp_path):
    # segunda note_on chega com a altura 96 ainda ativa
    t = mido.MidiTrack([mido.MetaMessage("track_name", name="PART GUITAR"),
                        mido.Message("note_on", note=96, velocity=100, time=0),
                        mido.Message("note_on", note=96, velocity=100, time=100),
                        mido.Message("note_off", note=96, velocity=0, time=100)])
    p = _write_mid(tmp_path, _full([t]))
    assert ("MIDI_OVERLAPPING_NOTE", "error") in _codes(validate_midi(p, PROFILES["rb3_ps3"]))


def test_unterminated_note(tmp_path):
    t = mido.MidiTrack([mido.MetaMessage("track_name", name="PART GUITAR"),
                        mido.Message("note_on", note=96, velocity=100, time=0)])
    p = _write_mid(tmp_path, _full([t]))
    assert ("MIDI_UNTERMINATED_NOTE", "error") in _codes(validate_midi(p, PROFILES["rb3_ps3"]))


def test_pro_guitar_bad_velocity(tmp_path):
    p = _write_mid(tmp_path, _full([_trk("PART REAL_GUITAR", [(0, 100, 96, 90)])]))
    assert ("MIDI_PRO_FRET_VELOCITY", "error") in _codes(validate_midi(p, PROFILES["rb3_ps3"]))


def test_pro_velocity_limit_depends_on_22_fret_track(tmp_path):
    notes = [(0, 100, 96, 120)]
    p17 = _write_mid(tmp_path, _full([_trk("PART REAL_GUITAR", notes)]))
    p22 = _write_mid(tmp_path, _full([_trk("PART REAL_GUITAR_22", notes)]), name="t22.mid")
    assert "MIDI_PRO_FRET_VELOCITY" in _plain(validate_midi(p17, PROFILES["rb3_ps3"]))
    assert "MIDI_PRO_FRET_VELOCITY" not in _plain(validate_midi(p22, PROFILES["rb3_ps3"]))


def test_vocal_note_outside_phrase_warns(tmp_path):
    p = _write_mid(tmp_path, _full([_trk("PART VOCALS", [(0, 100, 60, 100)])]))
    assert ("MIDI_VOCAL_NOTE_OUTSIDE_PHRASE", "warning") in _codes(
        validate_midi(p, PROFILES["rb3_ps3"]))


def test_vocal_note_inside_phrase_is_fine(tmp_path):
    p = _write_mid(tmp_path, _full([_trk("PART VOCALS", [(0, 400, 105, 100), (10, 100, 60, 100)])]))
    assert "MIDI_VOCAL_NOTE_OUTSIDE_PHRASE" not in _plain(validate_midi(p, PROFILES["rb3_ps3"]))


def test_repeated_warnings_are_grouped(tmp_path):
    notes = [(i * 100, i * 100 + 50, 20, 100) for i in range(50)]
    p = _write_mid(tmp_path, _full([_trk("PART GUITAR", notes)]))
    out = [i for i in validate_midi(p, PROFILES["rb3_ps3"]) if i.code == "MIDI_NOTE_OUT_OF_RANGE"]
    assert len(out) == 1 and "50" in out[0].message and out[0].level == "warning"
    assert "tick 0" in out[0].location


def test_range_check_ignores_real_keys_tracks(tmp_path):
    p = _write_mid(tmp_path, _full([_trk("PART REAL_KEYS_X", [(0, 100, 50, 100)])]))
    assert "MIDI_NOTE_OUT_OF_RANGE" not in _plain(validate_midi(p, PROFILES["rb3_ps3"]))


def test_wrong_tpb_and_no_tempo(tmp_path):
    p = _write_mid(tmp_path, [_trk("tempo"), _trk("BEAT"), _trk("EVENTS")], tpb=96)
    codes = _plain(validate_midi(p, PROFILES["clonehero"]))
    assert "MIDI_TPB_NOT_480" in codes and "MIDI_NO_TEMPO" in codes


def test_unknown_track_warns(tmp_path):
    p = _write_mid(tmp_path, _full([_trk("PART BANJO")]))
    assert ("MIDI_UNKNOWN_TRACK", "warning") in _codes(validate_midi(p, PROFILES["rb3_ps3"]))


def test_duplicate_track(tmp_path):
    p = _write_mid(tmp_path, _full([_trk("PART GUITAR"), _trk("PART GUITAR")]))
    assert ("MIDI_DUPLICATE_TRACK", "error") in _codes(validate_midi(p, PROFILES["rb3_ps3"]))


def test_beat_short(tmp_path):
    g = _trk("PART GUITAR", [(0, 100, 96, 100), (6000, 6100, 96, 100)])
    p = _write_mid(tmp_path, _full([g]))
    assert ("MIDI_BEAT_SHORT", "warning") in _codes(validate_midi(p, PROFILES["rb3_ps3"]))


def test_not_type1_is_error(tmp_path):
    mid = mido.MidiFile(type=0, ticks_per_beat=480)
    mid.tracks.append(_trk("tempo", tempo=True))
    p = tmp_path / "z.mid"
    mid.save(str(p))
    assert ("MIDI_NOT_TYPE1", "error") in _codes(validate_midi(str(p), PROFILES["clonehero"]))


def test_has_errors():
    assert has_errors([Issue("warning", "X", "m"), Issue("error", "Y", "m")])
    assert not has_errors([Issue("warning", "X", "m")])


def test_missing_markers_grouped_in_one_issue(tmp_path):
    p = _write_mid(tmp_path, _full(events_texts=[]))
    out = [i for i in validate_midi(p, PROFILES["rb3_ps3"]) if i.code == "MIDI_MISSING_MARKER"]
    assert len(out) == 1
    assert all(m in out[0].message for m in ("[music_start]", "[music_end]", "[end]"))


def test_animation_and_extra_notes_not_flagged(tmp_path):
    cases = {"PART GUITAR": [104, 126, 40, 59], "PART BASS": [104, 126, 40, 59],
             "PART KEYS": [104, 126], "PART DRUMS": [104, 126, 24, 51]}
    for name, pitches in cases.items():
        notes = [(i * 20, i * 20 + 10, p, 100) for i, p in enumerate(pitches)]
        p = _write_mid(tmp_path, _full([_trk(name, notes)]))
        assert "MIDI_NOTE_OUT_OF_RANGE" not in _plain(validate_midi(p, PROFILES["rb3_ps3"])), name


def test_note_on_before_note_off_at_same_tick_is_not_overlap(tmp_path):
    t = mido.MidiTrack([mido.MetaMessage("track_name", name="PART GUITAR"),
                        mido.Message("note_on", note=96, velocity=100, time=0),
                        mido.Message("note_on", note=96, velocity=100, time=480),
                        mido.Message("note_off", note=96, velocity=0, time=0),
                        mido.Message("note_off", note=96, velocity=0, time=480)])
    p = _write_mid(tmp_path, _full([t]))
    assert "MIDI_OVERLAPPING_NOTE" not in _plain(validate_midi(p, PROFILES["rb3_ps3"]))


# --- Calibração com custom real (Joe Dassin - Salut les amoureux, Clone Hero/YARG) ---

def test_same_tick_duplicate_note_is_warning_not_error(tmp_path):
    # customs reais repetem a mesma nota no mesmo tick (os jogos aceitam)
    t = mido.MidiTrack([mido.MetaMessage("track_name", name="PART DRUMS"),
                        mido.Message("note_on", note=97, velocity=96, time=0),
                        mido.Message("note_on", note=97, velocity=96, time=0),
                        mido.Message("note_off", note=97, velocity=0, time=60),
                        mido.Message("note_off", note=97, velocity=0, time=0)])
    codes = _codes(validate_midi(_write_mid(tmp_path, _full([t])), PROFILES["rb3_ps3"]))
    assert ("MIDI_DUPLICATE_NOTE", "warning") in codes
    assert not any(c == "MIDI_OVERLAPPING_NOTE" for c, _ in codes)


def test_clone_hero_extra_tracks_are_known_for_clonehero(tmp_path):
    extra = [_trk(n, notes=[(0, 120, 96, 100)]) for n in
             ("PART GUITAR GHL", "PART BASS GHL", "PART ELITE_DRUMS", "PART REAL_DRUMS_PS")]
    p = _write_mid(tmp_path, _full(extra))
    assert "MIDI_UNKNOWN_TRACK" not in [c for c, _ in _codes(validate_midi(p, PROFILES["clonehero"]))]
    assert "MIDI_UNKNOWN_TRACK" in [c for c, _ in _codes(validate_midi(p, PROFILES["rb3_ps3"]))]


def test_enhanced_open_notes_are_accepted_on_guitar_and_bass(tmp_path):
    notes = [(i * 240, i * 240 + 120, pitch, 100) for i, pitch in enumerate((59, 71, 83, 95))]
    p = _write_mid(tmp_path, _full([_trk("PART GUITAR", notes=notes), _trk("PART BASS", notes=notes)]))
    assert "MIDI_NOTE_OUT_OF_RANGE" not in [c for c, _ in _codes(validate_midi(p, PROFILES["clonehero"]))]
