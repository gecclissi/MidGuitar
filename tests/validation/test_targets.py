"""Testes da validação por destino (validate_export / detect_target)."""
import os

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


def test_ps3_export_has_edat_and_no_errors(song, out):
    d = export_ps3_pkg_structure(song, out)
    issues = validate_export(d, "rb3_ps3")
    assert [i for i in issues if i.level == "error"] == []
    assert {i.code for i in issues} == {"PS3_MISSING_MILO"}
    assert detect_target(d) == "rb3_ps3"


def _only_edat(d):
    import glob
    return glob.glob(os.path.join(d, "USRDIR", "*", "songs", "*", "*.mid.edat"))[0]


def test_ps3_edat_in_renamed_folder_is_flagged(song, out):
    import shutil
    d = export_ps3_pkg_structure(song, out)
    usr = os.path.join(d, "USRDIR")
    old = os.listdir(usr)[0]
    shutil.move(os.path.join(usr, old), os.path.join(usr, "OUTRAPASTA"))
    codes = {i.code for i in validate_export(d, "rb3_ps3")}
    assert "PS3_BAD_EDAT" in codes


def test_ps3_corrupted_edat_is_flagged(song, out):
    d = export_ps3_pkg_structure(song, out)
    p = _only_edat(d)
    data = bytearray(open(p, "rb").read())
    data[0x200] ^= 0xFF
    with open(p, "wb") as f:
        f.write(bytes(data))
    codes = {i.code for i in validate_export(d, "rb3_ps3")}
    assert "PS3_BAD_EDAT" in codes


def test_xbox_export_has_con_and_validates(song, out):
    d = export_xbox360_structure(song, out)
    issues = validate_export(d, "xbox360")
    assert not [i for i in issues if i.level == "error"]
    codes = {i.code for i in issues}
    assert codes == {"XBOX_MISSING_MILO", "PROFILE_UNVERIFIED"}
    assert detect_target(d) == "xbox360"


def test_xbox_folder_without_con_is_flagged(tmp_path):
    (tmp_path / "songs").mkdir()
    codes = {i.code for i in validate_export(str(tmp_path), "xbox360")}
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


def _ch_dir(tmp_path, ini_bytes, mid="notes.mid", ini="song.ini"):
    d = tmp_path / "ch"
    d.mkdir()
    (d / ini).write_bytes(ini_bytes)
    (d / mid).write_bytes(b"")
    _write_ogg(d / "song.ogg")
    return str(d)


def _ch_codes(d):
    return {i.code for i in validate_export(d, "clonehero")}


def test_ini_with_comment_and_bare_key_is_tolerated(tmp_path):
    d = _ch_dir(tmp_path, b"[song]\n//comentario\nbarekey\nname = A\nartist = B\n")
    codes = _ch_codes(d)
    assert not codes & {"CH_INI_MISSING", "CH_INI_FIELD"}


def test_ini_lenient_fallback_still_checks_fields(tmp_path):
    d = _ch_dir(tmp_path, b"[song]\n[[lixo\nname = A\n")
    codes = _ch_codes(d)
    assert "CH_INI_FIELD" in codes and "CH_INI_MISSING" not in codes


def test_utf16_ini_is_read(tmp_path):
    raw = "[song]\nname = A\nartist = B\n".encode("utf-16")  # com BOM
    d = _ch_dir(tmp_path, raw)
    assert not _ch_codes(d) & {"CH_INI_MISSING", "CH_INI_FIELD"}


def test_detect_target_is_case_insensitive(tmp_path):
    d = _ch_dir(tmp_path, b"[song]\nname=A\nartist=B\n", mid="Notes.mid", ini="Song.ini")
    assert detect_target(d) == "clonehero"


def test_dta_song_name_path_differs_from_key(tmp_path):
    root = tmp_path / "r" / "songs"
    sdir = root / "OtherDir"
    (sdir / "gen").mkdir(parents=True)
    (root / "songs.dta").write_text(
        '(mykey (name "T") (artist "A") (song_id 1) (game_origin "ugc_plus")\n'
        ' (rank (guitar 1)) (vocal_parts 0)\n'
        ' (song (name "songs/OtherDir/otherbase") (tracks ((guitar (0 1)))) '
        '(pans (-1 1)) (vols (0 0)) (cores (-1 -1))) (album_art FALSE))', encoding="utf-8")
    (sdir / "otherbase.mid.edat").write_bytes(b"NPD\x00")
    (sdir / "otherbase.mogg").write_bytes(b"")
    (sdir / "gen" / "otherbase.milo_ps3").write_bytes(b"")
    codes = {i.code for i in validate_export(str(tmp_path / "r"), "rb3_ps3")}
    assert not codes & {"LAYOUT_MISSING_SONG_DIR", "PS3_MISSING_EDAT",
                        "PS3_MISSING_MILO", "PS3_PLAIN_MID"}
    assert "LAYOUT_MISSING_MOGG" not in codes


def test_ghwt_definitive_edition_mod_is_not_clone_hero(tmp_path):
    # mod do GHWT:DE: song.ini com [ModInfo]/[SongInfo], sem notes.mid e sem [song]
    d = tmp_path / "PAVLO - Mediterranean Eyes"
    (d / "Content").mkdir(parents=True)
    (d / "song.ini").write_text("[ModInfo]\nName=X\n\n[SongInfo]\nTitle=X\nArtist=Y\n", encoding="utf-8")
    assert detect_target(str(d)) is None


def test_song_ini_with_song_section_is_clone_hero(tmp_path):
    d = tmp_path / "ch"
    d.mkdir()
    (d / "song.ini").write_text("[Song]\nname = X\nartist = Y\n", encoding="utf-8")
    assert detect_target(str(d)) == "clonehero"
