"""Exportação Xbox 360 (pacote CON) e importação de CON / pasta Xbox extraída."""
import collections
import glob
import os
import shutil
import types

import numpy as np
import pytest
import soundfile as sf

from src.creator.chart_importer import import_song_from_folder
from src.creator.chart_model import ChartSong, NoteEvent
from src.creator.validation import validate_export
from src.creator.xbox360_exporter import export_xbox360_structure
from src.creator.xbox_stfs import RB3_TITLE_ID, StfsPackage

TOL_MS = 2
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REF_CON = os.path.join(ROOT, "music", "_refs", "xbox_con", "Joe Dassin - Salut les amoureux_rb3con")
REF_CH = os.path.join(ROOT, "music", "_refs", "Joe Dassin - Salut les amoureux")
_TRACKS = ("guitar", "bass", "drum", "keys", "pro_guitar", "pro_bass", "pro_keys")


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
    root = export_xbox360_structure(song, str(tmp_path / "out"))
    return song, root


def _con(root):
    cons = glob.glob(os.path.join(root, "*_rb3con"))
    assert len(cons) == 1
    return cons[0]


def test_export_writes_signed_con(exported):
    song, root = exported
    assert sorted(os.listdir(root)) == sorted([os.path.basename(_con(root)),
                                               "COMO_INSTALAR_NO_XBOX360.txt"])
    pkg = StfsPackage(_con(root))
    assert pkg.verify() == [] and pkg.signature_status() is True and pkg.signed_with_known_kv()
    assert pkg.magic == "CON" and pkg.title_id == RB3_TITLE_ID and pkg.content_type == 1
    assert pkg.display_name == "Banda Á - Canção \"Teste\"" and pkg.title_name == "Rock Band 3"
    assert pkg.thumbnail[:4] == b"\x89PNG"
    names = sorted(e.path.split("/", 2)[-1] if e.path.count("/") > 1 else e.path
                   for e in pkg.files())
    s = pkg.files()[0].path.split("/")[1]
    assert names == sorted(["songs/songs.dta", "%s.mid" % s, "%s.mogg" % s,
                            "gen/%s_keep.png_xbox" % s])
    dta = pkg.read_file("songs/songs.dta").decode("utf-8")
    assert '(name "songs/%s/%s")' % (s, s) in dta and "(album_art 1)" in dta
    mogg = pkg.read_file("songs/%s/%s.mogg" % (s, s))
    assert mogg[0] == 0x0A


def test_export_passes_validator(exported):
    _song_, root = exported
    issues = validate_export(root, "xbox360")
    assert not [i for i in issues if i.level == "error"], issues
    assert {i.code for i in issues} == {"XBOX_MISSING_MILO", "PROFILE_UNVERIFIED"}


def test_corrupted_con_is_flagged(exported):
    _song_, root = exported
    con = _con(root)
    with open(con, "r+b") as f:
        f.seek(0xC000 + 3 * 0x1000 + 100)
        b = f.read(1)
        f.seek(-1, 1)
        f.write(bytes([b[0] ^ 0xFF]))
    codes = {i.code for i in validate_export(root, "xbox360")}
    assert "XBOX_BAD_CON" in codes


def test_con_roundtrip_keeps_note_times_and_metadata(exported):
    song, root = exported
    back = import_song_from_folder(_con(root))
    _assert_same_times(song, back)
    assert back.title == song.title and back.artist == song.artist
    assert back.audio_path and os.path.exists(back.audio_path)
    assert back.album_art_path and back.album_art_path.endswith(".png")
    assert not back.import_warnings


@pytest.mark.parametrize("where", ["root", "songs", "song"])
def test_import_extracted_xbox_folder(exported, tmp_path, where):
    song, root = exported
    ext = str(tmp_path / "ext")
    StfsPackage(_con(root)).extract(ext)
    path = {"root": ext, "songs": os.path.join(ext, "songs"),
            "song": glob.glob(os.path.join(ext, "songs", "*", ""))[0]}[where]
    back = import_song_from_folder(path)
    _assert_same_times(song, back)
    assert back.title == song.title


# ---------------------------------------------------------------------------
# Interface (sem janela): botão "Abrir pacote" e arrastar um CON sem extensão
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
    fake = types.SimpleNamespace(folder_entry=_Entry(), applied=[],
                                 tk=types.SimpleNamespace(splitlist=lambda d: [d]))
    fake._apply_loaded_song = lambda s: fake.applied.append(s)
    fake._import_folder_path = lambda p: dialog.CreatorStudioDialog._import_folder_path(fake, p)
    return fake


@pytest.fixture
def boxes(monkeypatch):
    got = {"warn": [], "error": [], "info": []}
    monkeypatch.setattr(dialog.messagebox, "showwarning", lambda *a, **k: got["warn"].append(a))
    monkeypatch.setattr(dialog.messagebox, "showerror", lambda *a, **k: got["error"].append(a))
    monkeypatch.setattr(dialog.messagebox, "showinfo", lambda *a, **k: got["info"].append(a))
    return got


def test_open_package_button_imports_con(monkeypatch, boxes, exported):
    song, root = exported
    seen = {}

    def ask(**k):
        seen.update(k)
        return _con(root)
    monkeypatch.setattr(dialog.filedialog, "askopenfilename", ask)
    fake = _fake()
    dialog.CreatorStudioDialog._on_browse_import_pkg(fake)
    assert len(fake.applied) == 1 and fake.applied[0].title == song.title
    assert any("_rb3con" in ft[1] for ft in seen["filetypes"])
    assert not boxes["warn"] and not boxes["error"]


def test_drop_con_without_extension_imports(boxes, exported, tmp_path):
    song, root = exported
    plain = str(tmp_path / "PACOTESEMEXT")
    shutil.copyfile(_con(root), plain)
    fake = _fake()
    dialog.CreatorStudioDialog._on_files_dropped(fake, types.SimpleNamespace(data=plain))
    assert len(fake.applied) == 1 and fake.applied[0].title == song.title
    assert not boxes["error"]


# ---------------------------------------------------------------------------
# CON real (suíte de referências)
# ---------------------------------------------------------------------------
needs_ref = pytest.mark.skipif(
    not os.environ.get("MIDGUITAR_REFS") or not (os.path.isfile(REF_CON) and os.path.isdir(REF_CH)),
    reason="CON de referência só roda com MIDGUITAR_REFS (lento)")


@pytest.fixture(scope="module")
def ref_copy(tmp_path_factory):
    dst = str(tmp_path_factory.mktemp("con") / os.path.basename(REF_CON))
    shutil.copyfile(REF_CON, dst)
    return dst


@pytest.mark.refs
@needs_ref
def test_reference_con_matches_clone_hero_version(ref_copy):
    """A CON e a pasta Clone Hero são a mesma música: notas iguais por trilha e
    dificuldade (tempo exato). As notas abertas do baixo do CH (95/83, ENHANCED_OPENS)
    entram como lane "open"; na CON (RB3 não tem nota aberta) são notas verdes."""
    con = import_song_from_folder(ref_copy)
    ch = import_song_from_folder(REF_CH)
    total = 0
    for track in _TRACKS:
        for diff in ("Easy", "Medium", "Hard", "Expert"):
            a = sorted(n.time_ms for n in getattr(con, track + "_notes") if n.difficulty == diff)
            b = sorted(n.time_ms for n in getattr(ch, track + "_notes") if n.difficulty == diff)
            total += len(a)
            assert len(a) == len(b), (track, diff)
            assert all(abs(x - y) <= TOL_MS for x, y in zip(a, b)), (track, diff)
    assert total > 10000
    assert len(con.vocal_notes) == len(ch.vocal_notes) == 409
    assert (con.title, con.artist, con.album, con.year, con.genre) == \
        (ch.title, ch.artist, ch.album, ch.year, ch.genre)
    assert con.bpm == ch.bpm and con.preview_start_ms == ch.preview_start_ms
    assert con.diff_guitar == ch.diff_guitar and con.diff_drums == ch.diff_drums
    assert {"HARM1", "HARM2", "HARM3", "BEAT", "VENUE"} <= {t.get("name") for t in con.passthrough_tracks}
    # .mogg 0x0A de 16 canais: mix + stems + canais originais para reexportar
    assert con.audio_path and os.path.exists(con.audio_path) and con.import_warnings == []
    assert con.source_mogg["channels"] == 16 and len(con.audio_stems) >= 5
    assert con.album_art_path.endswith(".png")


@pytest.mark.refs
@needs_ref
def test_reference_con_passes_validator(ref_copy):
    issues = validate_export(os.path.dirname(ref_copy), "xbox360")
    assert not [i for i in issues if i.level == "error"], issues
    assert "XBOX_MISSING_MILO" not in {i.code for i in issues}


@pytest.mark.refs
@needs_ref
def test_joe_dassin_exports_to_xbox_without_errors(tmp_path):
    song = import_song_from_folder(REF_CH)
    root = export_xbox360_structure(song, str(tmp_path / "out"))
    issues = validate_export(root, "xbox360")
    assert not [i for i in issues if i.level == "error"], issues
    back = import_song_from_folder(_con(root))
    for track in _TRACKS:
        a = collections.Counter(n.difficulty for n in getattr(song, track + "_notes"))
        b = collections.Counter(n.difficulty for n in getattr(back, track + "_notes"))
        assert a == b, track
    assert len(back.vocal_notes) == len(song.vocal_notes)
