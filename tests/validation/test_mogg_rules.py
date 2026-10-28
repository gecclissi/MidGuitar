"""Testes das regras de .mogg."""
import struct

import numpy as np
import soundfile as sf

from src.creator.mogg_generator import create_unencrypted_mogg
from src.creator.validation import read_mogg_info, validate_mogg


def _write_sine_wav(tmp_path, seconds=2, channels=2, sr=44100):
    t = np.arange(int(sr * seconds)) / sr
    mono = 0.3 * np.sin(2 * np.pi * 440 * t)
    data = np.stack([mono] * channels, axis=1)
    p = tmp_path / "s.wav"
    sf.write(str(p), data, sr)
    return p


def _make_mogg(tmp_path):
    wav = _write_sine_wav(tmp_path)
    mogg = tmp_path / "x.mogg"
    assert create_unencrypted_mogg(str(wav), str(mogg))
    return mogg


def test_generated_mogg_is_valid(tmp_path):
    mogg = _make_mogg(tmp_path)
    assert validate_mogg(str(mogg)) == []
    info = read_mogg_info(str(mogg))
    assert info.channels == 2 and info.version == 0x0A and info.sample_rate == 44100


def test_missing_and_truncated_mogg_is_unreadable(tmp_path):
    assert [i.code for i in validate_mogg(str(tmp_path / "no.mogg"))] == ["MOGG_UNREADABLE"]
    p = tmp_path / "t.mogg"
    p.write_bytes(b"\x0a\x00\x00\x00")
    assert [i.code for i in validate_mogg(str(p))] == ["MOGG_UNREADABLE"]
    assert read_mogg_info(str(p)) is None


def test_encrypted_mogg_warns_and_has_no_channels(tmp_path):
    p = tmp_path / "e.mogg"
    p.write_bytes(struct.pack("<II", 0x0B, 24) + b"\x00" * 64)
    issues = validate_mogg(str(p))
    assert [(i.code, i.level) for i in issues] == [("MOGG_ENCRYPTED", "warning")]
    info = read_mogg_info(str(p))
    assert info.version == 0x0B and info.channels is None


def test_bad_offset(tmp_path):
    p = tmp_path / "b.mogg"
    p.write_bytes(struct.pack("<IIIII", 0x0A, 20, 0x10, 20000, 0) + b"garbage-not-ogg")
    assert [i.code for i in validate_mogg(str(p))] == ["MOGG_BAD_OFFSET"]


def test_offset_beyond_file_is_bad_offset(tmp_path):
    p = tmp_path / "b.mogg"
    p.write_bytes(struct.pack("<IIIII", 0x0A, 9999, 0x10, 20000, 0))
    assert [i.code for i in validate_mogg(str(p))] == ["MOGG_BAD_OFFSET"]


def test_bad_ogg_is_error(tmp_path):
    good = _make_mogg(tmp_path).read_bytes()
    off = struct.unpack("<II", good[:8])[1]
    p = tmp_path / "c.mogg"
    p.write_bytes(good[:off] + b"OggS" + b"\xff" * 100)
    assert [i.code for i in validate_mogg(str(p))] == ["MOGG_BAD_OGG"]
