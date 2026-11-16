"""Exportação Rock Band no formato dos pacotes PS3 reais (passo 3A).

Layout USRDIR/<pasta>/songs/, PARAM.SFO como as referências, .mogg multicanal a 44100 Hz
coerente com o songs.dta, campos do DTA no estilo Magma C3, filtro de trilhas e png_ps3.
"""
import glob
import os
import shutil
import struct

import mido
import numpy as np
import pytest
import soundfile as sf

from src.creator.chart_model import ChartSong, NoteEvent, ProGuitarNote, VocalNote
from src.creator.validation import parse_dta, read_mogg_info, validate_export

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REFS = os.path.join(ROOT, "music", "_refs")
REF_SFOS = sorted(glob.glob(os.path.join(REFS, "*", "PARAM.SFO")))
JOE = os.path.join(REFS, "Joe Dassin - Salut les amoureux")


def _tone(path, freq, seconds=2.0, sr=48000, channels=2):
    t = np.arange(int(sr * seconds)) / float(sr)
    x = (0.2 * np.sin(2 * np.pi * freq * t)).astype("float32")
    sf.write(path, np.stack([x] * channels, 1) if channels > 1 else x, sr)
    return path


def _song(title="Exemplo", artist="Diag", charter="Eu"):
    s = ChartSong(title=title, artist=artist, charter=charter)
    for i in range(20):
        t = 1000 + i * 400
        s.add_note("guitar", NoteEvent(time_ms=t, lane="green"))
        s.add_note("bass", NoteEvent(time_ms=t, lane="red"))
        s.add_note("drum", NoteEvent(time_ms=t, lane="kick"))
    s.vocal_notes = [VocalNote(time_ms=1000 + i * 500, lyric="la") for i in range(6)]
    return s


def _entry(dta_path):
    tree = parse_dta(open(dta_path, encoding="utf-8").read())
    assert len(tree) == 1
    return tree[0]


def _field(lst, key):
    for item in lst:
        if isinstance(item, list) and item and item[0] == key:
            return item
    return None


def _songs_dta(root):
    hits = glob.glob(os.path.join(root, "USRDIR", "*", "songs", "songs.dta"))
    assert len(hits) == 1, hits
    return hits[0]


# ---------------------------------------------------------------------------
# Layout e instalador
# ---------------------------------------------------------------------------
def test_ps3_layout_unique_folder_per_song(tmp_path):
    from src.creator.ps3_pkg_exporter import export_ps3_pkg_structure
    a, b = _song("Primeira"), _song("Segunda")
    ra = export_ps3_pkg_structure(a, str(tmp_path / "out"))
    rb = export_ps3_pkg_structure(b, str(tmp_path / "out"))
    da, db = _songs_dta(ra), _songs_dta(rb)
    fa = os.path.basename(os.path.dirname(os.path.dirname(da)))
    fb = os.path.basename(os.path.dirname(os.path.dirname(db)))
    assert fa != fb and len(fa) <= 27 and fa.isalnum()
    # "Instala" as duas no mesmo USRDIR: os dois songs.dta continuam lá
    usrdir = tmp_path / "rpcs3" / "dev_hdd0" / "game" / "BLUS30463" / "USRDIR"
    for root in (ra, rb):
        for f in os.listdir(os.path.join(root, "USRDIR")):
            shutil.copytree(os.path.join(root, "USRDIR", f), str(usrdir / f))
    assert len(glob.glob(str(usrdir / "*" / "songs" / "songs.dta"))) == 2
    bat = open(os.path.join(ra, "INSTALAR_NO_RPCS3_AUTOMATICO.bat"), encoding="utf-8").read()
    assert "USRDIR\\%s" % fa in bat and "BLUS30463\\USRDIR" in bat
    assert '"USRDIR\\songs"' not in bat


def test_rb3_and_rb2_and_pack_use_usrdir_folder(tmp_path):
    from src.creator.pack_compiler import compile_ps3_song_pack
    from src.creator.rb2_exporter import export_rb2_song_package
    from src.creator.rb3_dta_exporter import export_rb3_song_package
    s = _song()
    _songs_dta(export_rb3_song_package(s, str(tmp_path / "rb3")))
    rb2 = export_rb2_song_package(s, str(tmp_path / "rb2"))
    _songs_dta(rb2)
    bat = open(os.path.join(rb2, "INSTALAR_NO_RB2_RPCS3.bat"), encoding="utf-8").read()
    assert "BLUS30147\\USRDIR" in bat and '"USRDIR\\songs"' not in bat
    pack = compile_ps3_song_pack([s, _song("Outra")], "Pacote", str(tmp_path / "pk"))
    tree = parse_dta(open(_songs_dta(pack), encoding="utf-8").read())
    ids = [_field(e, "song_id")[1] for e in tree]
    assert len(tree) == 2 and len(set(ids)) == 2


# ---------------------------------------------------------------------------
# PARAM.SFO
# ---------------------------------------------------------------------------
def _sfo_fields(data):
    _magic, _ver, key_off, data_off, n = struct.unpack_from("<4sIIII", data, 0)
    out = {}
    for i in range(n):
        k, fmt, length, _max, off = struct.unpack_from("<HHIII", data, 20 + 16 * i)
        key = data[key_off + k:data.index(b"\x00", key_off + k)].decode()
        raw = data[data_off + off:data_off + off + length]
        out[key] = struct.unpack("<I", raw)[0] if fmt == 0x0404 else raw.rstrip(b"\x00").decode()
    return out


@pytest.mark.skipif(not REF_SFOS, reason="referências PS3 ausentes")
def test_param_sfo_identical_to_references():
    from src.creator.ps3_pkg_exporter import generate_param_sfo
    ours = generate_param_sfo("Rock Band 3", "UP0006-BLUS30463_00-X")
    for ref in REF_SFOS:
        assert ours == open(ref, "rb").read()


def test_param_sfo_fields_for_song():
    from src.creator.ps3_pkg_exporter import generate_param_sfo
    f = _sfo_fields(generate_param_sfo("RB3: Salut les amoureux - Joe Dassin é" * 5))
    assert f["CATEGORY"] == "GD" and f["TITLE_ID"] == "BLUS30463"
    assert f["PARENTAL_LEVEL"] == 5 and f["VERSION"] == "01.00"
    assert len(f["TITLE"].encode("utf-8")) <= 127


# ---------------------------------------------------------------------------
# songs.dta
# ---------------------------------------------------------------------------
def test_dta_fields_like_magma(tmp_path):
    from src.creator.rb3_dta_exporter import export_rb3_song_package
    s = _song(title='Salut les "amoureux" é', artist="Joe Dassin")
    s.audio_path = _tone(str(tmp_path / "mix.wav"), 440, seconds=3.0)
    root = export_rb3_song_package(s, str(tmp_path / "out"))
    dta = _songs_dta(root)
    raw = open(dta, "rb").read().decode("utf-8")
    assert '\\q' in raw
    e = _entry(dta)
    assert _field(e, "name")[1] == 'Salut les \\qamoureux\\q é'
    assert _field(e, "encoding")[1] == "utf8"
    assert _field(e, "genre")[1] == "rock"
    assert _field(e, "game_origin")[1] == "ugc_plus"
    assert abs(_field(e, "song_length")[1] - 3000) < 50
    assert _field(e, "album_art")[1] == 1
    song = _field(e, "song")
    assert _field(_field(song, "drum_solo"), "seqs")[1][0] == "kick.cue"
    assert _field(_field(song, "drum_freestyle"), "seqs")[1][2] == "hat.cue"
    assert _field(song, "vocal_parts")[1] == 1
    sid = _field(e, "song_id")[1]
    assert 1000000000 <= sid <= 2147483647
    rank = _field(e, "rank")
    assert _field(rank, "keys")[1] == 0 and _field(rank, "guitar")[1] in (139, 176, 221, 267, 333, 409)
    # Instrumentos sem notas não aparecem em tracks
    names = [t[0] for t in _field(song, "tracks")[1]]
    assert "keys" not in names and "guitar" in names
    art = glob.glob(os.path.join(os.path.dirname(dta), "*", "gen", "*_keep.png_ps3"))
    assert len(art) == 1 and os.path.getsize(art[0]) == 87444


def test_genre_symbols():
    from src.creator.rb3_dta_exporter import rb3_genre
    assert rb3_genre("Rock") == "rock" and rb3_genre("Country Pop") == "other"
    assert rb3_genre("Pop") == "poprock" and rb3_genre("Hip Hop") == "hiphoprap"
    assert rb3_genre("") == "other"


def test_song_id_unique_and_stable():
    from src.creator.rb3_dta_exporter import stable_song_id
    a = stable_song_id(_song(charter="A"))
    assert a == stable_song_id(_song(charter="A"))
    assert a != stable_song_id(_song(charter="B"))
    ids = {stable_song_id(_song(title="Música %d" % i)) for i in range(500)}
    assert len(ids) == 500 and all(1000000000 <= i <= 2147483647 for i in ids)


def test_vocal_parts_from_harmonies_and_pro_tunings():
    from src.creator.rb3_dta_exporter import generate_songs_dta_content
    s = _song()
    on = {"type": "note_on", "channel": 0, "note": 60, "velocity": 100}
    s.passthrough_tracks = [{"name": n, "events": [[1000.0, on]]} for n in ("HARM1", "HARM2", "HARM3")]
    s.pro_guitar_notes = [ProGuitarNote(time_ms=1000)]
    s.pro_bass_notes = [ProGuitarNote(time_ms=1000)]
    s.ini_extra = {"real_guitar_tuning": "0 0 0 0 0 -2"}
    e = parse_dta(generate_songs_dta_content(s, "x", song_length_ms=1000))[0]
    assert _field(_field(e, "song"), "vocal_parts")[1] == 3
    assert _field(e, "real_guitar_tuning")[1] == [0, 0, 0, 0, 0, -2]
    assert _field(e, "real_bass_tuning")[1] == [0, 0, 0, 0]
    s.passthrough_tracks = s.passthrough_tracks[:2]
    e = parse_dta(generate_songs_dta_content(s, "x", song_length_ms=1000))[0]
    assert _field(_field(e, "song"), "vocal_parts")[1] == 2


# ---------------------------------------------------------------------------
# Filtro de trilhas do MIDI
# ---------------------------------------------------------------------------
_CH_ONLY = ("PART GUITAR GHL", "PART BASS GHL", "PART ELITE_DRUMS", "PART REAL_DRUMS_PS", "PART RHYTHM")
_RB_KEEP = ("HARM1", "VENUE", "PART REAL_GUITAR_22")


def _with_passthrough(song):
    on = {"type": "note_on", "channel": 0, "note": 60, "velocity": 100}
    off = {"type": "note_off", "channel": 0, "note": 60, "velocity": 0}
    song.passthrough_tracks = [{"name": n, "events": [[1000.0, on], [1100.0, off]]}
                               for n in _CH_ONLY + _RB_KEEP]
    return song


def _track_names(mid_path):
    return {t.name for t in _open_mid(mid_path).tracks}


def _open_mid(path):
    """MIDI solto ou .mid.edat (decifrado com a chave da pasta em USRDIR)."""
    if path.endswith(".edat"):
        import io
        from src.creator.edat import read_rock_band_mid_edat
        return mido.MidiFile(file=io.BytesIO(read_rock_band_mid_edat(path, installed=True)))
    return mido.MidiFile(path)


def test_rock_band_exports_drop_clone_hero_tracks(tmp_path):
    from src.creator.rb2_exporter import export_rb2_song_package
    from src.creator.rb3_dta_exporter import export_rb3_song_package
    s = _with_passthrough(_song())
    mid = glob.glob(os.path.join(export_rb3_song_package(s, str(tmp_path / "a")),
                                 "USRDIR", "*", "songs", "*", "*.mid.edat"))[0]
    names = _track_names(mid)
    assert not names & set(_CH_ONLY)
    assert set(_RB_KEEP) | {"BEAT", "EVENTS", "PART DRUMS"} <= names
    drums = next(t for t in _open_mid(mid).tracks if t.name == "PART DRUMS")
    mixes = sorted(m.text for m in drums if m.type == "text" and m.text.startswith("[mix"))
    assert mixes == ["[mix %d drums0]" % d for d in range(4)]
    rb2 = export_rb2_song_package(s, str(tmp_path / "b"))
    mid2 = glob.glob(os.path.join(rb2, "USRDIR", "*", "songs", "*", "*.mid.edat"))[0]
    assert not glob.glob(os.path.join(rb2, "USRDIR", "*", "songs", "*", "*.mid"))
    assert glob.glob(os.path.join(rb2, "Xbox360_Content", "**", "*.mid"), recursive=True)
    names2 = _track_names(mid2)
    assert not names2 & set(_CH_ONLY) and "HARM1" not in names2 and "VENUE" in names2


def test_clone_hero_midi_keeps_all_passthrough():
    from src.creator.midi_generator import generate_rbn_midi
    names = {t.name for t in generate_rbn_midi(_with_passthrough(_song())).tracks}
    assert set(_CH_ONLY) <= names


# ---------------------------------------------------------------------------
# .mogg multicanal
# ---------------------------------------------------------------------------
FREQS = {"guitar": 300, "bass": 500, "drums_1": 700, "drums_2": 900, "vocals": 1100,
         "rhythm": 1300, "keys": 1500, "crowd": 1700}


def _mogg_audio(mogg, tmp_path):
    from src.creator.mogg_generator import extract_ogg_from_mogg
    ogg = extract_ogg_from_mogg(mogg, str(tmp_path / "x.ogg"))
    return sf.read(ogg, dtype="float32")


def _peaks(x, sr, freqs):
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    hz = np.fft.rfftfreq(len(x), 1.0 / sr)
    level = {f: spec[np.argmin(np.abs(hz - f))] for f in freqs}
    top = max(level.values())
    return {f for f, v in level.items() if v > 0.1 * top}


def test_multitrack_mogg_matches_dta(tmp_path):
    from src.creator.rb3_dta_exporter import export_rb3_song_package
    s = _song()   # guitarra, baixo, bateria e vocal com notas; teclado sem notas
    stems = []
    for name, f in FREQS.items():
        stems.append(_tone(str(tmp_path / ("%s.wav" % name)), f, channels=1 if name == "vocals" else 2))
    s.audio_stems = stems
    s.audio_path = stems[0]
    root = export_rb3_song_package(s, str(tmp_path / "out"))
    dta = _songs_dta(root)
    e = _entry(dta)
    song = _field(e, "song")
    tracks = {t[0]: t[1] for t in _field(song, "tracks")[1]}
    assert tracks == {"drum": [0, 1], "bass": [2, 3], "guitar": [4, 5], "vocals": [6, 7]}
    assert _field(song, "tracks_count")[1] == [2, 2, 2, 2, 0, 2]
    assert len(_field(song, "pans")[1]) == 10
    mogg = glob.glob(os.path.join(os.path.dirname(dta), "*", "*.mogg"))[0]
    info = read_mogg_info(mogg)
    assert info.channels == 10
    data, sr = _mogg_audio(mogg, tmp_path)
    assert sr == 44100 and data.shape[1] == 10
    mid = data[len(data) // 4: 3 * len(data) // 4]
    allf = list(FREQS.values())
    assert _peaks(mid[:, 0], sr, allf) == {700, 900}        # drums_1 + drums_2
    assert _peaks(mid[:, 2], sr, allf) == {500}             # baixo
    assert _peaks(mid[:, 5], sr, allf) == {300}             # guitarra
    assert _peaks(mid[:, 7], sr, allf) == {1100}            # vocal mono duplicado
    assert _peaks(mid[:, 8], sr, allf) == {1300, 1500}      # rhythm + teclado sem notas
    codes = {i.code for i in validate_export(root, "rb3_ps3")}
    assert not codes & {"DTA_MOGG_CHANNELS", "DTA_CHANNEL_MISMATCH", "LAYOUT_MISSING_MOGG",
                        "PS3_MISSING_ART", "DTA_SYNTAX"}
    # Nada de stems soltos na pasta da música
    assert not glob.glob(os.path.join(os.path.dirname(dta), "*", "*.wav"))


def test_single_mix_is_two_channels_44100(tmp_path):
    from src.creator.ps3_pkg_exporter import export_ps3_pkg_structure
    s = _song()
    s.audio_path = _tone(str(tmp_path / "mix.wav"), 440)
    root = export_ps3_pkg_structure(s, str(tmp_path / "out"))
    dta = _songs_dta(root)
    song = _field(_entry(dta), "song")
    assert len(_field(song, "pans")[1]) == 2 and _field(song, "tracks_count") is None
    mogg = glob.glob(os.path.join(os.path.dirname(dta), "*", "*.mogg"))[0]
    data, sr = _mogg_audio(mogg, tmp_path)
    assert sr == 44100 and data.shape[1] == 2
    codes = {i.code for i in validate_export(root, "rb3_ps3")}
    assert not codes & {"DTA_MOGG_CHANNELS", "DTA_CHANNEL_MISMATCH", "PS3_MISSING_ART"}


def test_rb2_mixes_stems_to_stereo(tmp_path):
    from src.creator.rb2_exporter import export_rb2_song_package
    s = _song()
    s.audio_stems = [_tone(str(tmp_path / "guitar.wav"), 300), _tone(str(tmp_path / "bass.wav"), 500)]
    s.audio_path = s.audio_stems[0]
    root = export_rb2_song_package(s, str(tmp_path / "out"))
    mogg = glob.glob(os.path.join(root, "USRDIR", "*", "songs", "*", "*.mogg"))[0]
    data, sr = _mogg_audio(mogg, tmp_path)
    assert data.shape[1] == 2 and sr == 44100
    assert _peaks(data[len(data) // 4: 3 * len(data) // 4, 0], sr, [300, 500]) == {300, 500}


# ---------------------------------------------------------------------------
# Joe Dassin completo (lento: só na suíte de referências)
# ---------------------------------------------------------------------------
@pytest.mark.refs
@pytest.mark.skipif(not os.environ.get("MIDGUITAR_REFS") or not os.path.isdir(JOE),
                    reason="exportação completa do Joe Dassin só roda com MIDGUITAR_REFS")
def test_joe_dassin_ps3_export(tmp_path):
    from src.creator.chart_importer import import_song_from_folder
    from src.creator.ps3_pkg_exporter import export_ps3_pkg_structure
    song = import_song_from_folder(JOE)
    root = export_ps3_pkg_structure(song, str(tmp_path / "out"))
    dta = _songs_dta(root)
    e = _entry(dta)
    assert _field(e, "name")[1] == "Salut les amoureux"
    song_f = _field(e, "song")
    assert _field(song_f, "vocal_parts")[1] == 3
    assert _field(song_f, "tracks_count")[1] == [2, 2, 2, 2, 2, 2]
    assert abs(_field(e, "song_length")[1] - 245541) < 100
    mogg = glob.glob(os.path.join(os.path.dirname(dta), "*", "*.mogg"))[0]
    assert read_mogg_info(mogg).channels == 12
    import io
    from src.creator.edat import read_rock_band_mid_edat
    assert not glob.glob(os.path.join(os.path.dirname(dta), "*", "*.mid"))
    edat = glob.glob(os.path.join(os.path.dirname(dta), "*", "*.mid.edat"))[0]
    mid = mido.MidiFile(file=io.BytesIO(read_rock_band_mid_edat(edat, installed=True)))
    names = {t.name for t in mid.tracks}
    assert not names & {"PART GUITAR GHL", "PART BASS GHL", "PART ELITE_DRUMS", "PART RHYTHM"}
    # Validador: só o aviso do .milo_ps3 (animações) que ainda não geramos
    assert [(i.level, i.code) for i in validate_export(root, "rb3_ps3")] == [
        ("warning", "PS3_MISSING_MILO")]

    # .pkg -> extração -> importação: tempos das notas preservados (±2 ms)
    from src.creator.chart_importer import import_song_from_folder
    pkg = glob.glob(os.path.join(root, "*.pkg"))[0]
    back = import_song_from_folder(pkg)
    for track in ("guitar", "bass", "drum", "keys", "pro_guitar", "pro_bass", "pro_keys"):
        for diff in ("Expert", "Hard", "Medium", "Easy"):
            a = sorted(n.time_ms for n in getattr(song, track + "_notes") if n.difficulty == diff)
            b = sorted(n.time_ms for n in getattr(back, track + "_notes") if n.difficulty == diff)
            assert len(a) == len(b), (track, diff)
            assert all(abs(x - y) <= 2 for x, y in zip(a, b)), (track, diff)
    va = sorted(n.time_ms for n in song.vocal_notes)
    vb = sorted(n.time_ms for n in back.vocal_notes)
    assert len(va) == len(vb) and all(abs(x - y) <= 2 for x, y in zip(va, vb))
    assert back.title == "Salut les amoureux"
    assert {"HARM1", "HARM2", "HARM3", "VENUE", "PART REAL_GUITAR_22"} <= names
