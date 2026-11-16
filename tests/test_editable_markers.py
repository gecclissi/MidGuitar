"""Overdrive (116), solo (103) e frases vocais (105/106) importados viram dados editáveis.

Importar -> editar no editor -> exportar precisa refletir a edição (antes ficavam no
passthrough e as edições sumiam), sem perder a fidelidade do ciclo sem edição.
"""
import json

import pytest
from mido import MidiFile

from src.creator.chart_importer import import_song_from_folder
from src.creator.chart_model import ChartSong, NoteEvent
from src.creator.midi_generator import generate_rbn_midi
from tests.test_ch_fidelity import _signature, _synthetic_mid


@pytest.fixture
def song(tmp_path):
    folder = tmp_path / "synthetic"
    folder.mkdir()
    _synthetic_mid(str(folder / "notes.mid"))
    return import_song_from_folder(str(folder))


def _track_notes(song, name, **kw):
    for t in generate_rbn_midi(song, **kw).tracks:
        n, notes, _texts = _signature(t)
        if n == name:
            return notes
    return []


def _pitch(notes, pitch):
    return sorted((s, e, v) for s, e, p, v, _c in notes if p == pitch)


def test_imported_overdrive_and_solo_are_editor_lanes(song):
    od = [n for n in song.guitar_notes if n.lane == "overdrive"]
    solo = [n for n in song.guitar_notes if n.lane == "solo"]
    assert len(od) == 1 and len(solo) == 1
    assert od[0].velocity == 100 and od[0].is_overdrive
    extras = song.track_extras["PART GUITAR"]["notes"]
    assert not [x for x in extras if x[2] in (103, 116)]


def test_add_overdrive_in_editor_reaches_export(song):
    end = max(n.time_ms + n.duration_ms for n in song.guitar_notes)
    song.add_note("guitar", NoteEvent(time_ms=end + 1000, lane="overdrive", duration_ms=500,
                                      difficulty="Expert", is_overdrive=True))
    assert len(_pitch(_track_notes(song, "PART GUITAR"), 116)) == 2


def test_delete_overdrive_in_editor_removes_it_from_export(song):
    song.guitar_notes = [n for n in song.guitar_notes if n.lane != "overdrive"]
    assert _pitch(_track_notes(song, "PART GUITAR"), 116) == []


def test_delete_and_add_solo_in_editor(song):
    song.guitar_notes = [n for n in song.guitar_notes if n.lane != "solo"]
    assert _pitch(_track_notes(song, "PART GUITAR"), 103) == []
    song.add_note("guitar", NoteEvent(time_ms=500, lane="solo", duration_ms=400, difficulty="Expert"))
    assert len(_pitch(_track_notes(song, "PART GUITAR"), 103)) == 1


def test_new_song_solo_lane_exports_merged_103():
    s = ChartSong(title="t", artist="a")
    for i in range(8):
        s.add_note("guitar", NoteEvent(time_ms=1000 + 250 * i, lane="green"))
    s.add_note("guitar", NoteEvent(time_ms=1000, lane="solo", duration_ms=1000))
    s.add_note("guitar", NoteEvent(time_ms=1500, lane="solo", duration_ms=1000))   # sobreposto: une
    s.add_note("drum", NoteEvent(time_ms=1000, lane="kick"))
    s.add_note("drum", NoteEvent(time_ms=1000, lane="solo", duration_ms=500))
    assert len(_pitch(_track_notes(s, "PART GUITAR"), 103)) == 1
    assert len(_pitch(_track_notes(s, "PART DRUMS"), 103)) == 1


def test_solo_roundtrip_through_import(tmp_path):
    s = ChartSong(title="t", artist="a")
    for i in range(8):
        s.add_note("guitar", NoteEvent(time_ms=1000 + 250 * i, lane="green"))
    s.add_note("guitar", NoteEvent(time_ms=1000, lane="solo", duration_ms=1000))
    folder = tmp_path / "s"
    folder.mkdir()
    generate_rbn_midi(s).save(str(folder / "notes.mid"))
    (folder / "song.ini").write_text("[song]\nname=t\nartist=a\n", encoding="utf-8")
    back = import_song_from_folder(str(folder))
    solo = [n for n in back.guitar_notes if n.lane == "solo"]
    assert len(solo) == 1 and abs(solo[0].time_ms - 1000) <= 1 and abs(solo[0].duration_ms - 1000) <= 2


def test_vocal_phrases_are_editable(song):
    assert [v.is_phrase_end for v in song.vocal_notes] == [False, True, True]
    assert _pitch(_track_notes(song, "PART VOCALS"), 105) == [(900, 2000, 100), (2400, 3500, 100)]
    assert not [x for x in song.track_extras["PART VOCALS"]["notes"] if x[2] == 105]
    # Divide a 1ª frase no editor: marca a 1ª nota como fim de frase
    song.vocal_notes[0].is_phrase_end = True
    assert len(_pitch(_track_notes(song, "PART VOCALS"), 105)) == 3


def test_vocal_overdrive_edit_reaches_export(song):
    song.vocal_notes[2].is_overdrive = True
    od = _pitch(_track_notes(song, "PART VOCALS"), 106)
    assert od == [(2400, 3500, 100)]


def test_phrase_bounds_survive_project_json(song):
    back = ChartSong.from_dict(json.loads(json.dumps(song.to_dict())))
    assert _pitch(_track_notes(back, "PART VOCALS"), 105) == [(900, 2000, 100), (2400, 3500, 100)]


def test_old_project_with_markers_in_extras_is_migrated(song):
    """Projetos salvos antes: 116/103 no passthrough sobem para as lanes ao abrir."""
    data = song.to_dict()
    lifted = [n for n in data["guitar_notes"] if n["lane"] in ("overdrive", "solo")]
    data["guitar_notes"] = [n for n in data["guitar_notes"] if n["lane"] not in ("overdrive", "solo")]
    for n in lifted:
        pitch = 116 if n["lane"] == "overdrive" else 103
        data["track_extras"]["PART GUITAR"]["notes"].append(
            [n["time_ms"], n["time_ms"] + n["duration_ms"], pitch, n["velocity"], 0])
    back = ChartSong.from_dict(json.loads(json.dumps(data)))
    assert sorted(n.lane for n in back.guitar_notes if n.lane in ("overdrive", "solo")) == ["overdrive", "solo"]
    back.guitar_notes = [n for n in back.guitar_notes if n.lane != "overdrive"]
    assert _pitch(_track_notes(back, "PART GUITAR"), 116) == []
