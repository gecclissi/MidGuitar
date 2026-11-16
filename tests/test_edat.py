"""NPD/EDAT (.mid.edat do PS3): cifra, decifra e verificação contra as referências."""
import glob
import io
import os
import struct

import mido
import pytest

from src.creator.edat import (EDAT_FOOTER_V2, FAKE_DIGEST, EdatError, NpdHeader,
                              decrypt_edat, encrypt_edat, find_rock_band_klic, rb3_content_id,
                              read_rock_band_mid_edat, rock_band_klic, verify_edat,
                              write_rock_band_mid_edat)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REF_EDATS = sorted(glob.glob(os.path.join(ROOT, "music", "_refs", "*", "USRDIR", "*", "songs",
                                          "*", "*.mid.edat")))
FOLDER = "MG123456ARTISTASONG"


def _midi_bytes(notes=50):
    mid = mido.MidiFile(ticks_per_beat=480)
    t = mido.MidiTrack()
    t.append(mido.MetaMessage("track_name", name="PART GUITAR"))
    for i in range(notes):
        t.append(mido.Message("note_on", note=96, velocity=100, time=0 if i == 0 else 240))
        t.append(mido.Message("note_off", note=96, velocity=0, time=120))
    mid.tracks.append(t)
    buf = io.BytesIO()
    mid.save(file=buf)
    return buf.getvalue()


@pytest.mark.parametrize("size", [1, 15, 16, 0x4000, 0x4001, 54049])
def test_roundtrip_sizes(size):
    plain = bytes((i * 7 + 3) & 0xFF for i in range(size))
    klic = rock_band_klic(FOLDER)
    data = encrypt_edat(plain, "x.mid.edat", rb3_content_id(FOLDER), klic)
    assert verify_edat(data, "x.mid.edat", klic) == []
    assert decrypt_edat(data, "x.mid.edat", klic) == plain
    blocks = (size + 0x3FFF) // 0x4000
    assert len(data) == 0x100 + 0x10 * blocks + ((size + 15) & ~15) + 0x10


def test_header_mirrors_references():
    data = encrypt_edat(_midi_bytes(), "song.mid.edat", rb3_content_id(FOLDER), rock_band_klic(FOLDER))
    h = NpdHeader(data)
    assert data[:4] == b"NPD\x00"
    assert (h.version, h.license, h.type) == (2, 3, 0)
    assert h.content_id == "UP8802-BLUS30463_00-" + FOLDER
    assert h.digest == FAKE_DIGEST
    assert (h.flags, h.block_size) == (0x0C, 0x4000)
    assert data[0x70:0x80] == bytes(16) and data[0xB0:0x100] == bytes(0x50)
    assert data.endswith(EDAT_FOOTER_V2)


def test_wrong_key_name_or_tamper_is_rejected():
    plain = _midi_bytes()
    klic = rock_band_klic(FOLDER)
    data = encrypt_edat(plain, "song.mid.edat", rb3_content_id(FOLDER), klic)
    with pytest.raises(EdatError):
        decrypt_edat(data, "song.mid.edat", rock_band_klic("OUTRA"))
    with pytest.raises(EdatError):
        decrypt_edat(data, "outro.mid.edat", klic)
    bad = bytearray(data)
    bad[0x150] ^= 1
    with pytest.raises(EdatError):
        decrypt_edat(bytes(bad), "song.mid.edat", klic)


def test_klic_from_usrdir_folder(tmp_path):
    d = tmp_path / "USRDIR" / FOLDER / "songs" / "song"
    d.mkdir(parents=True)
    p = str(d / "song.mid.edat")
    write_rock_band_mid_edat(_midi_bytes(), p, FOLDER)
    assert read_rock_band_mid_edat(p, installed=True) == _midi_bytes()
    # Copiado para fora do USRDIR: ainda abre pelo rótulo do content id
    other = tmp_path / "solto"
    other.mkdir()
    os.replace(p, str(other / "song.mid.edat"))
    assert read_rock_band_mid_edat(str(other / "song.mid.edat")) == _midi_bytes()


def test_content_id_limit():
    with pytest.raises(EdatError):
        rb3_content_id("X" * 29)


@pytest.mark.skipif(not REF_EDATS, reason="referências PS3 ausentes")
@pytest.mark.parametrize("path", REF_EDATS, ids=[os.path.basename(p) for p in REF_EDATS])
def test_reference_edat_verifies_and_reencrypts_identically(path):
    data = open(path, "rb").read()
    name = os.path.basename(path)
    folder = path.replace("\\", "/").split("/USRDIR/")[1].split("/")[0]
    klic = rock_band_klic(folder)
    assert find_rock_band_klic(data, path) == klic
    assert verify_edat(data, name, klic) == []
    plain = decrypt_edat(data, name, klic)
    assert plain.startswith(b"MThd")
    assert len(mido.MidiFile(file=io.BytesIO(plain)).tracks) > 5
    h = NpdHeader(data)
    assert h.content_id == rb3_content_id(folder)
    assert encrypt_edat(plain, name, h.content_id, klic) == data
    assert struct.unpack(">I", data[0x80:0x84])[0] == 0x0C
