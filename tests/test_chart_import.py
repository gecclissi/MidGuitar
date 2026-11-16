"""Importação de notes.chart (Clone Hero / Moonscraper) e lanes de bateria."""
import os
import shutil

import pytest

from src.creator.chart_importer import import_song_from_folder
from src.creator.chart_model import ChartSong, NoteEvent
from src.creator.midi_generator import generate_rbn_midi
from src.creator.rbn_specs import DRUM_NOTES

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "chart_song")


@pytest.fixture
def chart_song(tmp_path):
    dst = tmp_path / "chart_song"
    shutil.copytree(FIXTURE, str(dst))
    return import_song_from_folder(str(dst))


def _abs(track):
    tick, out = 0, []
    for m in track:
        tick += m.time
        out.append((tick, m))
    return out


def _track(mid, name):
    return next(t for t in mid.tracks if any(m.type == "track_name" and m.name == name for m in t))


def _ons(track):
    return [(t, m.note) for t, m in _abs(track) if m.type == "note_on" and m.velocity > 0]


def test_chart_metadata(chart_song):
    s = chart_song
    assert (s.title, s.artist, s.album, s.year, s.charter) == ("Chart Fixture", "Banda Teste", "Disco", 1999, "Fulano")


def test_chart_events(chart_song):
    texts = [(e.time_ms, e.text) for e in chart_song.events]
    assert texts == [(0, "[section Intro]"), (2000, "[section Verse 1]"), (4000, "[end]")]


def test_chart_star_power_becomes_overdrive(chart_song):
    od = [n for n in chart_song.guitar_notes if n.lane == "overdrive"]
    assert [(n.time_ms, n.duration_ms) for n in od] == [(2000, 1000)]
    guitar = _track(generate_rbn_midi(chart_song), "PART GUITAR")
    ev = _abs(guitar)
    assert [t for t, m in ev if m.type == "note_on" and m.note == 116] == [1920]
    assert [t for t, m in ev if m.type == "note_off" and m.note == 116] == [2880]


def test_chart_forced_tap_and_open(chart_song):
    guitar = _track(generate_rbn_midi(chart_song), "PART GUITAR")
    ons = _ons(guitar)
    assert (480, 101) in ons      # N 5 numa nota que seria palhetada -> HOPO forçado
    assert (640, 102) in ons      # N 5 numa nota que seria HOPO -> palhetada forçada
    assert (960, 104) in ons      # N 6 -> tap
    assert (1440, 95) in ons      # N 7 -> open (ENHANCED_OPENS)
    assert any(m.type == "text" and m.text == "[ENHANCED_OPENS]" for m in guitar)
    lanes = {n.lane for n in chart_song.guitar_notes}
    assert lanes <= {"green", "red", "yellow", "blue", "orange", "overdrive", "open"}


def test_chart_drums_use_canonical_lanes(chart_song):
    exp = sorted((n.time_ms, n.lane) for n in chart_song.drum_notes if n.difficulty == "Expert")
    assert exp == [(0, "double_kick"), (0, "kick"), (500, "snare"), (1000, "yellow"),
                   (1500, "blue"), (2000, "green")]


# ---------------------------------------------------------------------------
# Lanes de bateria: um só vocabulário (rbn_specs.DRUM_NOTES)
# ---------------------------------------------------------------------------
def test_editor_drum_lanes_match_drum_notes():
    from src.ui.mini_reaper_canvas import LANE_NAMES_DRUMS
    playable = [k for k, _ in LANE_NAMES_DRUMS if k not in ("overdrive", "solo")]
    assert playable == ["kick", "snare", "yellow", "blue", "green"]
    assert set(playable) <= set(DRUM_NOTES["Expert"])


def test_imported_drum_lanes_are_editor_rows():
    from src.ui.mini_reaper_canvas import LANE_NAMES_DRUMS
    rows = {k for k, _ in LANE_NAMES_DRUMS}
    for lane in DRUM_NOTES["Hard"]:
        assert lane in rows


def test_legacy_drum_project_lanes_are_mapped():
    data = ChartSong().to_dict()
    data["drum_notes"] = [{"time_ms": 0, "lane": "orange"}, {"time_ms": 10, "lane": "red"},
                          {"time_ms": 20, "lane": "yellow", "campo_futuro": 1}]
    data["guitar_notes"] = [{"time_ms": 0, "lane": "orange"}]
    back = ChartSong.from_dict(data)
    assert [n.lane for n in back.drum_notes] == ["kick", "snare", "yellow"]
    assert back.guitar_notes[0].lane == "orange"


def test_drum_lower_difficulties_keep_kick_and_snare():
    from src.creator.auto_charter import recalculate_track_difficulties
    s = ChartSong()
    for i in range(16):
        s.add_note("drum", NoteEvent(time_ms=i * 500, lane="kick" if i % 2 == 0 else "snare"))
    recalculate_track_difficulties(s, ["drum"])
    for diff in ("Hard", "Medium", "Easy"):
        lanes = {n.lane for n in s.drum_notes if n.difficulty == diff}
        assert lanes and lanes <= {"kick", "snare"}, diff
