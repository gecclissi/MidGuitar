"""Exportação PS3 (.mid.edat + .pkg) e importação de .pkg / pasta PS3 / .mid.edat."""
import filecmp
import glob
import os
import types

import numpy as np
import pytest
import soundfile as sf

from src.creator.chart_importer import import_song_from_folder
from src.creator.chart_model import ChartSong, NoteEvent
from src.creator.ps3_pkg import extract_pkg, read_pkg
from src.creator.ps3_pkg_exporter import export_ps3_pkg_structure
from src.creator.rb3_dta_exporter import stable_song_id
from src.creator.validation import validate_export

TOL_MS = 2


def _song(tmp_path):
    s = ChartSong(title="Canção \"Teste\"", artist="Banda Á", album="Disco", year=1999)
    s.bpm = 120.0
    lanes = ["green", "red", "yellow", "blue", "orange"]
    for i in range(40):
        t = 2000 + i * 375
        s.add_note("guitar", NoteEvent(time_ms=t, lane=lanes[i % 5]))
        s.add_note("bass", NoteEvent(time_ms=t, lane=lanes[(i + 2) % 5]))
        s.add_note("drum", NoteEvent(time_ms=t, lane="kick" if i % 2 else "snare"))
    sr = 44100
    x = (0.2 * np.sin(2 * np.pi * 220 * np.arange(sr * 20) / sr)).astype("float32")
    p = str(tmp_path / "mix.wav")
    sf.write(p, np.stack([x, x], axis=1), sr)
    s.audio_path = p
    s.preview_start_ms = 4000
    return s


def _expert_times(song, track):
    return sorted(n.time_ms for n in getattr(song, track + "_notes") if n.difficulty == "Expert")


def _assert_same_times(a, b):
    for track in ("guitar", "bass", "drum"):
        ta, tb = _expert_times(a, track), _expert_times(b, track)
        assert len(ta) == len(tb), track
        assert max(abs(x - y) for x, y in zip(ta, tb)) <= TOL_MS, track


@pytest.fixture
def exported(tmp_path):
    song = _song(tmp_path)
    root = export_ps3_pkg_structure(song, str(tmp_path / "out"))
    return song, root


def _pkg(root):
    pkgs = glob.glob(os.path.join(root, "*.pkg"))
    assert len(pkgs) == 1
    return pkgs[0]


def test_export_writes_edat_pkg_and_validates(exported, tmp_path):
    song, root = exported
    sdir = glob.glob(os.path.join(root, "USRDIR", "*", "songs", "*", ""))[0]
    assert glob.glob(os.path.join(sdir, "*.mid.edat"))
    assert not glob.glob(os.path.join(sdir, "*.mid"))
    issues = validate_export(root, "rb3_ps3")
    assert [i.code for i in issues] == ["PS3_MISSING_MILO"]

    info = read_pkg(_pkg(root))
    folder = os.listdir(os.path.join(root, "USRDIR"))[0]
    assert info.content_id == "UP8802-BLUS30463_00-" + folder
    assert info.digests_ok() and info.klicensee_ok()
    out = str(tmp_path / "x")
    extract_pkg(_pkg(root), out)
    assert sorted(os.listdir(out)) == ["ICON0.PNG", "PARAM.SFO", "USRDIR"]
    d = filecmp.dircmp(out, root)
    assert not d.diff_files
    cmp = filecmp.dircmp(os.path.join(out, "USRDIR"), os.path.join(root, "USRDIR"))

    def same(c):
        return not (c.left_only or c.right_only or c.diff_files) and all(same(s) for s in c.subdirs.values())
    assert same(cmp)


def test_pkg_roundtrip_keeps_note_times_and_metadata(exported):
    song, root = exported
    back = import_song_from_folder(_pkg(root))
    _assert_same_times(song, back)
    assert (back.title, back.artist, back.album, back.year) == (song.title, song.artist, "Disco", 1999)
    assert back.dta_song_id == stable_song_id(song)
    assert back.preview_start_ms == 4000
    assert back.audio_path and os.path.exists(back.audio_path)   # .mogg 0x0A extraído
    assert back.import_warnings == []


@pytest.mark.parametrize("where", ["root", "usrdir_folder", "songs", "song_dir", "edat_file"])
def test_import_ps3_folder_variants(exported, where):
    song, root = exported
    folder = glob.glob(os.path.join(root, "USRDIR", "*"))[0]
    sdir = glob.glob(os.path.join(folder, "songs", "*", ""))[0].rstrip("\\/")
    path = {"root": root, "usrdir_folder": folder, "songs": os.path.join(folder, "songs"),
            "song_dir": sdir, "edat_file": glob.glob(os.path.join(sdir, "*.mid.edat"))[0]}[where]
    back = import_song_from_folder(path)
    _assert_same_times(song, back)
    assert back.title == song.title


def test_encrypted_mogg_leaves_audio_empty_with_warning(exported):
    _song_, root = exported
    mogg = glob.glob(os.path.join(root, "USRDIR", "*", "songs", "*", "*.mogg"))[0]
    data = bytearray(open(mogg, "rb").read())
    data[0] = 0x0B
    with open(mogg, "wb") as f:
        f.write(bytes(data))
    back = import_song_from_folder(os.path.dirname(mogg))
    assert back.audio_path is None and not back.audio_stems
    assert len(back.import_warnings) == 1 and "criptografado" in back.import_warnings[0]
    assert back.guitar_notes


# ---------------------------------------------------------------------------
# Interface (sem janela): botão "Abrir .pkg" e avisos da importação
# ---------------------------------------------------------------------------
dialog = pytest.importorskip("src.ui.creator_studio_dialog", reason="UI indisponível neste ambiente")


class _Entry:
    def __init__(self):
        self.text = ""

    def delete(self, *_a):
        self.text = ""

    def insert(self, _i, t):
        self.text = t


def _fake():
    fake = types.SimpleNamespace(folder_entry=_Entry(), applied=[])
    fake._apply_loaded_song = lambda s: fake.applied.append(s)
    fake._import_folder_path = lambda p: dialog.CreatorStudioDialog._import_folder_path(fake, p)
    return fake


@pytest.fixture
def boxes(monkeypatch):
    got = {"warn": [], "error": []}
    monkeypatch.setattr(dialog.messagebox, "showwarning", lambda *a, **k: got["warn"].append(a))
    monkeypatch.setattr(dialog.messagebox, "showerror", lambda *a, **k: got["error"].append(a))
    return got


def test_open_pkg_button_imports_song(monkeypatch, boxes, exported):
    song, root = exported
    monkeypatch.setattr(dialog.filedialog, "askopenfilename", lambda **k: _pkg(root))
    fake = _fake()
    dialog.CreatorStudioDialog._on_browse_import_pkg(fake)
    assert len(fake.applied) == 1 and fake.applied[0].title == song.title
    assert fake.folder_entry.text == _pkg(root)
    assert not boxes["warn"] and not boxes["error"]


def test_import_warnings_are_shown(monkeypatch, boxes):
    s = ChartSong()
    s.import_warnings.append("O áudio 'x.mogg' está criptografado")
    monkeypatch.setattr(dialog, "import_song_from_folder", lambda p: s)
    fake = _fake()
    dialog.CreatorStudioDialog._import_folder_path(fake, "qualquer")
    assert fake.applied == [s]
    assert boxes["warn"] and "criptografado" in boxes["warn"][0][1]


def test_import_error_is_shown(monkeypatch, boxes):
    def boom(_p):
        raise ValueError("pacote quebrado")
    monkeypatch.setattr(dialog, "import_song_from_folder", boom)
    fake = _fake()
    dialog.CreatorStudioDialog._import_folder_path(fake, "x.pkg")
    assert not fake.applied and "pacote quebrado" in boxes["error"][0][1]


def test_cancel_open_pkg(monkeypatch, boxes):
    monkeypatch.setattr(dialog.filedialog, "askopenfilename", lambda **k: "")
    fake = _fake()
    dialog.CreatorStudioDialog._on_browse_import_pkg(fake)
    assert not fake.applied


# ---------------------------------------------------------------------------
# PKGs reais (suíte de referências)
# ---------------------------------------------------------------------------
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REF_PKGS = [n for n in ("Gorillaz - Andromeda", "5 Seconds Of Summer - Ghost Of YouXB")
            if os.path.isfile(os.path.join(ROOT, "music", n + ".pkg"))]
_TRACKS = ("guitar", "bass", "drum", "keys", "pro_guitar", "pro_bass", "pro_keys")


@pytest.mark.refs
@pytest.mark.skipif(not REF_PKGS, reason="PKGs de referência ausentes")
@pytest.mark.parametrize("name", REF_PKGS)
def test_reference_pkg_import_matches_decrypted_midi(name, tmp_path):
    import collections
    from src.creator.edat import read_rock_band_mid_edat
    pkg = os.path.join(ROOT, "music", name + ".pkg")
    song = import_song_from_folder(pkg)

    # Mesmo MIDI decifrado direto do .mid.edat da árvore extraída, importado como .mid solto
    edat = glob.glob(os.path.join(ROOT, "music", "_refs", name, "USRDIR", "*", "songs", "*",
                                  "*.mid.edat"))[0]
    plain = tmp_path / "solto"
    plain.mkdir()
    (plain / "notes.mid").write_bytes(read_rock_band_mid_edat(edat))
    direct = import_song_from_folder(str(plain))

    total = 0
    for track in _TRACKS:
        a = collections.Counter(n.difficulty for n in getattr(song, track + "_notes"))
        b = collections.Counter(n.difficulty for n in getattr(direct, track + "_notes"))
        assert a == b, track
        total += sum(a.values())
    assert total > 1000
    assert len(song.vocal_notes) == len(direct.vocal_notes) > 100
    assert [t.get("name") for t in song.passthrough_tracks] == \
        [t.get("name") for t in direct.passthrough_tracks]
    assert {"HARM1", "HARM2", "HARM3"} <= {t.get("name") for t in song.passthrough_tracks}
    assert song.title not in ("", "Nova Música") and song.dta_song_id
    # .mogg criptografado descriptografado: mix + stems + canais originais para reexportar
    assert song.audio_path and os.path.exists(song.audio_path) and song.import_warnings == []
    assert song.source_mogg["channels"] >= 9 and len(song.audio_stems) >= 4
