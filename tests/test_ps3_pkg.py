"""Pacote .pkg de debug do PS3: criação, extração e comparação com as referências."""
import filecmp
import os
import struct

import pytest

from src.creator.ps3_pkg import (ITEM_DIR, ITEM_EDAT, ITEM_FILE, ITEM_FILE_NO_OVERWRITE, PkgError,
                                 build_pkg, extract_pkg, keystream_xor, read_pkg)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REF_PKGS = [n for n in ("Gorillaz - Andromeda", "5 Seconds Of Summer - Ghost Of YouXB")
            if os.path.isfile(os.path.join(ROOT, "music", n + ".pkg"))
            and os.path.isdir(os.path.join(ROOT, "music", "_refs", n))]
CID = "UP8802-BLUS30463_00-MGTESTPASTA"


def _tree_diff(a, b):
    d = filecmp.dircmp(a, b)
    bad = d.left_only + d.right_only + d.diff_files + d.funny_files
    for s in d.common_dirs:
        bad += _tree_diff(os.path.join(a, s), os.path.join(b, s))
    return bad


def _make_tree(root):
    song = os.path.join(root, "USRDIR", "MGTESTPASTA", "songs", "teste")
    os.makedirs(os.path.join(song, "gen"))
    files = {
        "PARAM.SFO": b"\x00PSF" + bytes(100),
        "ICON0.PNG": bytes(range(256)) * 3,
        os.path.join("USRDIR", "MGTESTPASTA", "songs", "songs.dta"): b"(teste (name \"x\"))",
        os.path.join(song, "teste.mid.edat"): b"NPD\x00" + bytes(37),
        os.path.join(song, "teste.mogg"): os.urandom(70001),
        os.path.join(song, "gen", "teste_keep.png_ps3"): b"",
    }
    for rel, data in files.items():
        with open(os.path.join(root, rel), "wb") as f:
            f.write(data)


def test_keystream_is_offset_consistent():
    key = bytes(range(16))
    data = os.urandom(100)
    whole = keystream_xor(data, key, 5)
    assert keystream_xor(data[:37], key, 5) + keystream_xor(data[37:], key, 42) == whole
    assert keystream_xor(whole, key, 5) == data


def test_build_extract_roundtrip(tmp_path):
    src = str(tmp_path / "src")
    _make_tree(src)
    pkg = build_pkg(src, str(tmp_path / "t.pkg"), CID)
    info = read_pkg(pkg)
    assert info.revision == 0 and info.pkg_type == 1
    assert info.content_id == CID
    assert info.digests_ok() and info.klicensee_ok()
    assert info.metadata == {1: struct.pack(">I", 3), 2: struct.pack(">I", 5),
                             3: struct.pack(">I", 0x0E), 4: struct.pack(">Q", info.data_size),
                             5: b"\x10\x61\x00\x00"}
    assert info.metadata_offset == 0xC0 and info.metadata_size == 0x80 and info.data_offset == 0x140
    assert os.path.getsize(pkg) == info.total_size == info.data_offset + info.data_size + 0x60
    flags = {i.name: i.flags for i in info.items}
    assert flags["ICON0.PNG"] == flags["PARAM.SFO"] == ITEM_FILE_NO_OVERWRITE
    assert flags["USRDIR"] == ITEM_DIR
    assert flags["USRDIR/MGTESTPASTA/songs/teste/teste.mid.edat"] == ITEM_EDAT
    assert flags["USRDIR/MGTESTPASTA/songs/teste/teste.mogg"] == ITEM_FILE
    names = [i.name for i in info.items]
    # arquivos da pasta antes das subpastas, como nas referências
    assert names.index("USRDIR/MGTESTPASTA/songs/songs.dta") < names.index("USRDIR/MGTESTPASTA/songs/teste")
    out = str(tmp_path / "out")
    extract_pkg(pkg, out)
    assert _tree_diff(src, out) == []


def test_include_filters_root(tmp_path):
    src = str(tmp_path / "src")
    _make_tree(src)
    with open(os.path.join(src, "LEIA.txt"), "w") as f:
        f.write("fora do pacote")
    pkg = build_pkg(src, str(tmp_path / "t.pkg"), CID, include=["PARAM.SFO", "ICON0.PNG", "USRDIR"])
    assert "LEIA.txt" not in {i.name for i in read_pkg(pkg).items}


def test_not_a_pkg(tmp_path):
    p = tmp_path / "x.pkg"
    p.write_bytes(b"nada" * 100)
    with pytest.raises(PkgError):
        read_pkg(str(p))


@pytest.mark.skipif(not REF_PKGS, reason="PKGs de referência ausentes")
@pytest.mark.parametrize("name", REF_PKGS)
def test_reference_pkg_extract_and_rebuild(name, tmp_path):
    ref_pkg = os.path.join(ROOT, "music", name + ".pkg")
    ref_tree = os.path.join(ROOT, "music", "_refs", name)
    info = read_pkg(ref_pkg)
    assert info.revision == 0 and info.digests_ok() and info.klicensee_ok()
    assert info.content_id.startswith("UP8802-BLUS30463_00-")
    out = str(tmp_path / "x")
    extract_pkg(ref_pkg, out)
    assert _tree_diff(out, ref_tree) == []

    # Reconstruído da árvore extraída: cabeçalho, metadados e dados decifrados idênticos
    mine = read_pkg(build_pkg(ref_tree, str(tmp_path / "re.pkg"), info.content_id))
    assert mine.header[:0x60] == info.header[:0x60]
    assert mine.metadata_raw == info.metadata_raw
    assert [(i.name, i.flags, i.offset, i.size) for i in mine.items] == \
        [(i.name, i.flags, i.offset, i.size) for i in info.items]
    assert mine.digests_ok() and mine.klicensee_ok()
    with open(mine.path, "rb") as a, open(ref_pkg, "rb") as b:
        assert mine.read_data(a, 0, mine.data_size) == info.read_data(b, 0, info.data_size)
