"""Descriptografia de .mogg (0x0B / 0x0D) e áudio de pacotes PS3 importados.

As referências (music/_refs, só leitura) são copiadas para tmp_path."""
import glob
import os
import shutil
import struct

import numpy as np
import pytest
import soundfile as sf

from src.creator.mogg_crypt import (MoggCryptError, SUPPORTED_ENCRYPTED_VERSIONS, decrypt_mogg,
                                    decrypt_mogg_bytes, mogg_version)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(ROOT, "music", "_refs")
# (pasta, versão do .mogg, song_length do songs.dta em ms, canais)
REF_MOGGS = [
    ("5 Seconds Of Summer - Ghost Of YouXB", 0x0B, 200463, 9),
    ("Gorillaz - Andromeda", 0x0D, 202919, 10),
]


def _ref_mogg(name):
    hits = glob.glob(os.path.join(REFS, name, "USRDIR", "*", "songs", "*", "*.mogg"))
    return hits[0] if hits else None


def _copy(src, tmp_path):
    dst = os.path.join(str(tmp_path), os.path.basename(src))
    shutil.copy2(src, dst)
    return dst


@pytest.mark.parametrize("name,version,length_ms,channels", REF_MOGGS)
def test_decrypt_reference_mogg(name, version, length_ms, channels, tmp_path):
    src = _ref_mogg(name)
    if src is None:
        pytest.skip("referência ausente: %s" % name)
    mogg = _copy(src, tmp_path)
    assert mogg_version(mogg) == version
    ogg = str(tmp_path / "out.ogg")
    plain = str(tmp_path / "out.mogg")
    data = decrypt_mogg(mogg, ogg_out_path=ogg, mogg_out_path=plain)
    assert data[:4] == b"OggS" and b"vorbis" in data[:256]

    audio, rate = sf.read(ogg, dtype="float32", always_2d=True)
    assert rate == 44100 and audio.shape[1] == channels
    assert abs(len(audio) / rate * 1000 - length_ms) < 500
    # Não é ruído: há sinal, os pares estéreo se correlacionam e o cruzamento por zero
    # fica bem abaixo do de ruído branco (~0.5)
    rms = np.sqrt((audio ** 2).mean(axis=0))
    assert (rms > 0.02).sum() >= channels - 1
    zc = (np.diff(np.sign(audio), axis=0) != 0).mean(axis=0)
    assert zc.max() < 0.25
    corr = [np.corrcoef(audio[:, c], audio[:, c + 1])[0, 1] for c in range(0, channels - 1, 2)
            if rms[c] > 0.02 and rms[c + 1] > 0.02]
    assert corr and min(corr) > 0.2

    # .mogg 0x0A gerado: mesma tabela de busca, abre como .mogg comum
    with open(plain, "rb") as f:
        head = f.read(20)
    ver, off, _m, _b, entries = struct.unpack("<iIIII", head)
    assert ver == 0x0A and off == 20 + 8 * entries
    assert decrypt_mogg_bytes(open(plain, "rb").read()) == data


def test_unsupported_and_corrupt_versions_raise(tmp_path):
    for v in (0x0E, 0x10, 0x11, 0x09):
        assert v not in SUPPORTED_ENCRYPTED_VERSIONS
    blob = struct.pack("<iIIII", 0x0E, 20 + 8, 16, 20000, 1) + bytes(8) + bytes(200)
    with pytest.raises(MoggCryptError):
        decrypt_mogg_bytes(blob)
    # 0x0B com dados que não são do formato: a chave não gera "OggS" -> erro, nunca lixo
    blob = struct.pack("<iIIII", 0x0B, 20 + 8 + 16, 16, 20000, 1) + bytes(8) + bytes(16) + bytes(64)
    with pytest.raises(MoggCryptError):
        decrypt_mogg_bytes(blob)


def test_dta_layout_and_export_layout():
    from src.creator.mogg_import import audio_layout_from_source, layout_from_dta_song
    song_fields = [["name", "songs/x/x"], ["tracks", [["drum", [0, 1, 2]], ["bass", 3],
                                                     ["keys", [4, 5]]]],
                   ["pans", [0.0, -1.0, 1.0, 0.0, -1.0, 1.0, -1.0, 1.0]],
                   ["vols", [0.0] * 8], ["crowd_channels", 6, 7]]
    lay = layout_from_dta_song(song_fields)
    assert lay["tracks"] == {"drum": [0, 1, 2], "bass": [3], "keys": [4, 5]}
    assert lay["crowd"] == [6, 7]
    src = dict(lay, channels=8)
    out = audio_layout_from_source(src, {"drum": True, "bass": True, "keys": False})
    assert out.tracks == {"drum": [0, 1, 2], "bass": [3]}
    assert out.backing == [4, 5, 6, 7] and out.channels == 8
    assert out.drum_mix == 4 and len(out.pans) == 8


def _ref_pkg(name):
    p = os.path.join(ROOT, "music", name + ".pkg")
    return p if os.path.isfile(p) else None


@pytest.mark.refs
@pytest.mark.skipif(not os.environ.get("MIDGUITAR_REFS"),
                    reason="importação + exportação de .pkg só roda com MIDGUITAR_REFS (lento)")
@pytest.mark.parametrize("name,version,length_ms,channels", REF_MOGGS)
def test_imported_pkg_audio_and_ps3_reexport_keep_channels(name, version, length_ms, channels,
                                                           tmp_path):
    from src.creator.chart_importer import import_song_from_folder
    from src.creator.mogg_generator import extract_ogg_from_mogg
    from src.creator.ps3_pkg_exporter import export_ps3_pkg_structure
    from src.creator.validation import validate_export
    from src.creator.validation.dta_parser import parse_dta
    pkg = _ref_pkg(name)
    if pkg is None:
        pytest.skip("pkg de referência ausente: %s" % name)
    song = import_song_from_folder(_copy(pkg, tmp_path))
    assert song.import_warnings == []
    info = sf.info(song.audio_path)
    assert info.channels == 2 and abs(info.duration * 1000 - length_ms) < 500
    mix, _sr = sf.read(song.audio_path, dtype="float32")
    assert np.sqrt((mix ** 2).mean()) > 0.02
    names = {os.path.splitext(os.path.basename(p))[0] for p in song.audio_stems}
    assert {"drums", "bass", "vocals", "song"} <= names
    for p in song.audio_stems:
        assert sf.info(p).channels == 2

    root = export_ps3_pkg_structure(song, str(tmp_path / "out"))
    mogg = glob.glob(os.path.join(root, "USRDIR", "*", "songs", "*", "*.mogg"))[0]
    ogg = extract_ogg_from_mogg(mogg, str(tmp_path / "re.ogg"))
    assert sf.info(ogg).channels == channels
    dta = glob.glob(os.path.join(root, "USRDIR", "*", "songs", "songs.dta"))[0]
    entry = parse_dta(open(dta, encoding="utf-8").read())[0]
    song_f = next(x for x in entry if isinstance(x, list) and x and x[0] == "song")
    pans = next(x for x in song_f if isinstance(x, list) and x and x[0] == "pans")[1]
    assert len(pans) == channels
    codes = {i.code for i in validate_export(root, "rb3_ps3")}
    assert not codes & {"DTA_MOGG_CHANNELS", "DTA_CHANNEL_MISMATCH", "LAYOUT_MISSING_MOGG"}
