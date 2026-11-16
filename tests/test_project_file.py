"""Projeto do MidGuitar (.mgproj): salvar/abrir sem perder nada."""
import json
import types

import pytest

from src.creator.chart_model import (ChartSong, NoteEvent, ProGuitarNote, ProKeysNote, TextEvent,
                                     VocalNote, load_project, save_project)
from src.creator.tempo_map import TempoChange, TempoMap


def _full_song():
    s = ChartSong(title="Projeto", artist="Banda", bpm=150.0, preview_start_ms=12345, duration_ms=200000,
                  audio_path="a.ogg", audio_stems=["g.ogg", "b.ogg"], audio_offset_ms=-40,
                  lyrics_raw="Salut les amoureux", diff_vocals=1, diff_pro_guitar=5, diff_pro_bass=0,
                  diff_pro_keys=6, diff_band=4, time_signature=(3, 4))
    s.tempo_map = TempoMap(480, [TempoChange(0, 400000), TempoChange(960, 500000)])
    s.add_note("guitar", NoteEvent(time_ms=10, lane="green", velocity=96))
    s.add_note("drum", NoteEvent(time_ms=10, lane="kick", velocity=127))
    s.add_vocal_note(VocalNote(time_ms=20, lyric="Sa-", is_phrase_end=True, velocity=96))
    s.add_pro_guitar_note(ProGuitarNote(time_ms=30, string_idx=2, fret=7, channel=13))
    s.add_pro_keys_note(ProKeysNote(time_ms=40, pitch=60, velocity=96))
    s.events.append(TextEvent(0, "[section intro]"))
    s.passthrough_tracks = [{"name": "VENUE", "events": [[1.5, {"type": "text", "text": "[x]", "meta": True}]]}]
    s.track_extras = {"PART GUITAR": {"notes": [[0.0, 100.0, 116, 100, 0]], "events": []}}
    s.tempo_track_name = "notes"
    s.ini_extra = {"pro_drums": "True"}
    return s


def test_project_roundtrip_keeps_everything(tmp_path):
    s = _full_song()
    path = str(tmp_path / "x.mgproj")
    save_project(s, path)
    back = load_project(path)
    assert back.to_dict() == json.loads(json.dumps(s.to_dict()))
    assert back.time_signature == (3, 4) and back.audio_offset_ms == -40
    assert back.tempo_map.tempos[1].us_per_beat == 500000
    assert back.vocal_notes[0].is_phrase_end and back.pro_guitar_notes[0].channel == 13


def test_load_project_rejects_other_json(tmp_path):
    p = tmp_path / "x.mgproj"
    p.write_text('{"foo": 1}', encoding="utf-8")
    with pytest.raises(ValueError):
        load_project(str(p))


# ---------------------------------------------------------------------------
# Botões "Salvar Projeto" / "Abrir Projeto" do estúdio (sem abrir janela)
# ---------------------------------------------------------------------------
dialog = pytest.importorskip("src.ui.creator_studio_dialog", reason="UI indisponível neste ambiente")


@pytest.fixture
def boxes(monkeypatch):
    got = {"info": [], "error": []}
    monkeypatch.setattr(dialog.messagebox, "showinfo", lambda *a, **k: got["info"].append(a))
    monkeypatch.setattr(dialog.messagebox, "showerror", lambda *a, **k: got["error"].append(a))
    return got


def _fake(song=None):
    fake = types.SimpleNamespace(song=song or ChartSong(), applied=[])
    fake._sync_fields_to_song = lambda: None
    fake._apply_loaded_song = lambda s: fake.applied.append(s)
    return fake


def test_save_and_open_project_buttons(monkeypatch, boxes, tmp_path):
    path = str(tmp_path / "meu.mgproj")
    monkeypatch.setattr(dialog.filedialog, "asksaveasfilename", lambda **k: path)
    dialog.CreatorStudioDialog._on_save_project(_fake(_full_song()))
    assert boxes["info"] and not boxes["error"]

    monkeypatch.setattr(dialog.filedialog, "askopenfilename", lambda **k: path)
    fake = _fake()
    dialog.CreatorStudioDialog._on_open_project(fake)
    assert len(fake.applied) == 1 and fake.applied[0].title == "Projeto"
    assert fake.applied[0].track_extras["PART GUITAR"]["notes"][0][2] == 116


def test_open_project_error_shows_message(monkeypatch, boxes, tmp_path):
    bad = tmp_path / "ruim.mgproj"
    bad.write_text("não é json", encoding="utf-8")
    monkeypatch.setattr(dialog.filedialog, "askopenfilename", lambda **k: str(bad))
    fake = _fake()
    dialog.CreatorStudioDialog._on_open_project(fake)
    assert boxes["error"] and not fake.applied


def test_cancel_does_nothing(monkeypatch, boxes):
    monkeypatch.setattr(dialog.filedialog, "asksaveasfilename", lambda **k: "")
    monkeypatch.setattr(dialog.filedialog, "askopenfilename", lambda **k: "")
    dialog.CreatorStudioDialog._on_save_project(_fake())
    dialog.CreatorStudioDialog._on_open_project(_fake())
    assert not boxes["info"] and not boxes["error"]
