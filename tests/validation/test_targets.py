"""Testes da validação por destino (validate_export / detect_target)."""
import numpy as np
import pytest
import soundfile as sf

from src.creator.auto_charter import auto_generate_chart
from src.creator.chart_model import ChartSong, NoteEvent
from src.creator.clonehero_exporter import export_clone_hero_song
from src.creator.ps3_pkg_exporter import export_ps3_pkg_structure
from src.creator.ps4_exporter import export_ps4_structure
from src.creator.rb2_exporter import export_rb2_song_package
from src.creator.xbox360_exporter import export_xbox360_structure
from src.creator.validation import detect_target, validate_export


def _write_ogg(path):
    t = np.arange(44100 * 3) / 44100
    mono = 0.3 * np.sin(2 * np.pi * 440 * t)
    sf.write(str(path), np.stack([mono, mono], axis=1), 44100, format="OGG", subtype="VORBIS")
    return path


@pytest.fixture
def song(tmp_path):
    s = auto_generate_chart(ChartSong(title="Teste", artist="Banda", bpm=120.0),
                            total_duration_ms=40000,
                            selected_instruments=["guitar", "bass", "drum"])
    s.audio_path = str(_write_ogg(tmp_path / "in.ogg"))
    return s


@pytest.fixture
def out(tmp_path):
    d = tmp_path / "out"
    d.mkdir()
    return str(d)


def test_clonehero_export_has_no_errors(song, out):
    d = export_clone_hero_song(song, out)
    assert [i for i in validate_export(d, "clonehero") if i.level == "error"] == []
    assert detect_target(d) == "clonehero"


def test_ps3_export_flags_missing_edat(song, out):
    # Fase 3/4 vai inverter este teste
    d = export_ps3_pkg_structure(song, out)
    codes = {i.code for i in validate_export(d, "rb3_ps3")}
    assert "PS3_MISSING_EDAT" in codes and "PS3_PLAIN_MID" in codes
    assert detect_target(d) == "rb3_ps3"


def test_xbox_export_flags_no_con(song, out):
    # Fase 3/4 vai inverter este teste
    d = export_xbox360_structure(song, out)
    codes = {i.code for i in validate_export(d, "xbox360")}
    assert "XBOX_NO_CON_PACKAGE" in codes and "PROFILE_UNVERIFIED" in codes


def test_rb2_export_has_no_forbidden_tracks(song, out):
    song.keys_notes = [NoteEvent(1000, "green")]
    d = export_rb2_song_package(song, out)
    assert "MIDI_FORBIDDEN_TRACK" not in {i.code for i in validate_export(d, "rb2")}


def test_ps4_export_does_not_raise(song, out):
    d = export_ps4_structure(song, out)
    issues = validate_export(d, "ps4")
    assert "VALIDATOR_CRASH" not in {i.code for i in issues}


def test_empty_folder_and_unknown_target_do_not_raise(tmp_path):
    assert validate_export(str(tmp_path), "clonehero")[0].code == "LAYOUT_MISSING_CHART"
    assert validate_export(str(tmp_path), "nintendo")[0].code == "TARGET_UNKNOWN"
    assert detect_target(str(tmp_path)) is None
    assert validate_export(str(tmp_path / "nao_existe"), "rb3_ps3")[0].level == "error"
