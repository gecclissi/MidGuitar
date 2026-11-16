"""Gravação atômica (CON e .pkg) e entradas corrompidas/truncadas com o erro do próprio módulo."""
import os
import struct

import pytest

from src.creator import ps3_pkg as P
from src.creator import xbox_stfs as X
from src.creator.mogg_crypt import MoggCryptError, read_mogg_header
from src.creator.ps3_pkg import PkgError, build_pkg, extract_pkg, read_pkg
from src.creator.xbox_stfs import StfsError, build_con

CID = "UP8802-BLUS30463_00-MGTESTPASTA"


def _tree(root):
    d = os.path.join(root, "USRDIR", "MGTESTPASTA", "songs")
    os.makedirs(d)
    with open(os.path.join(root, "PARAM.SFO"), "wb") as f:
        f.write(b"\x00PSF" + bytes(100))
    with open(os.path.join(d, "songs.dta"), "wb") as f:
        f.write(b"(x)")
    with open(os.path.join(d, "big.bin"), "wb") as f:
        f.write(os.urandom(50000))
    return root


def _leftovers(folder):
    return sorted(n for n in os.listdir(folder) if n.endswith(".tmp") or ".tmp" in n)


# ---------------------------------------------------------------------------
# CON (Xbox)
# ---------------------------------------------------------------------------
def _con_src(tmp_path):
    src = tmp_path / "src" / "songs" / "abc"
    src.mkdir(parents=True)
    (src / "abc.mid").write_bytes(os.urandom(9000))
    return str(tmp_path / "src")


def test_build_con_error_keeps_previous_file_and_no_tmp(tmp_path, monkeypatch):
    src = _con_src(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    con = out / "song_rb3con"
    con.write_bytes(b"ANTIGO")

    def boom(_signed):
        raise RuntimeError("falha simulada")
    monkeypatch.setattr(X, "con_signature", boom)
    with pytest.raises(RuntimeError):
        build_con(src, str(con), "Teste")
    assert con.read_bytes() == b"ANTIGO"
    assert os.listdir(str(out)) == ["song_rb3con"]


def test_build_con_short_read_raises(tmp_path, monkeypatch):
    src = _con_src(tmp_path)
    real = X._collect_tree

    def inflated(d):
        return [(p, n, path, size + 5000 if path else size) for p, n, path, size in real(d)]
    monkeypatch.setattr(X, "_collect_tree", inflated)
    out = tmp_path / "out"
    out.mkdir()
    with pytest.raises(StfsError):
        build_con(src, str(out / "song_rb3con"), "Teste")
    assert os.listdir(str(out)) == []


# ---------------------------------------------------------------------------
# .pkg (PS3)
# ---------------------------------------------------------------------------
def test_build_pkg_error_removes_tmp(tmp_path, monkeypatch):
    src = _tree(str(tmp_path / "src"))
    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.setattr(P, "PKG_TRAILER", -1)   # bytes(-1) falha no fim da gravação
    with pytest.raises(ValueError):
        build_pkg(src, str(out / "x.pkg"), CID)
    assert os.listdir(str(out)) == []


def _good_pkg(tmp_path):
    src = _tree(str(tmp_path / "src"))
    pkg = str(tmp_path / "x.pkg")
    build_pkg(src, pkg, CID)
    return pkg


def test_pkg_small_metadata_size_is_pkg_error(tmp_path):
    pkg = _good_pkg(tmp_path)
    data = bytearray(open(pkg, "rb").read())
    data[0x10:0x14] = struct.pack(">I", 0x10)   # metadata_size < 0x40
    bad = tmp_path / "bad.pkg"
    bad.write_bytes(bytes(data))
    with pytest.raises(PkgError):
        read_pkg(str(bad))


@pytest.mark.parametrize("cut", [0x90, 0x110, 0x150, 0x200])
def test_pkg_truncated_tables_is_pkg_error(tmp_path, cut):
    pkg = _good_pkg(tmp_path)
    bad = tmp_path / "bad.pkg"
    bad.write_bytes(open(pkg, "rb").read()[:cut])
    with pytest.raises(PkgError):
        read_pkg(str(bad))


def test_pkg_garbage_counts_is_pkg_error(tmp_path):
    pkg = _good_pkg(tmp_path)
    data = bytearray(open(pkg, "rb").read())
    data[0x0C:0x10] = struct.pack(">I", 500)     # metadata_count absurdo
    bad = tmp_path / "bad.pkg"
    bad.write_bytes(bytes(data))
    with pytest.raises(PkgError):
        read_pkg(str(bad))


def test_extract_truncated_pkg_raises_and_leaves_no_partial_file(tmp_path):
    pkg = _good_pkg(tmp_path)
    raw = open(pkg, "rb").read()
    bad = tmp_path / "bad.pkg"
    bad.write_bytes(raw[:len(raw) - 30000])     # corta no meio de big.bin
    out = tmp_path / "ext"
    with pytest.raises(PkgError):
        extract_pkg(str(bad), str(out))
    files = [os.path.join(dp, f) for dp, _, fs in os.walk(str(out)) for f in fs]
    assert not any(f.endswith("big.bin") for f in files)
    assert not any(".tmp" in f for f in files)


# ---------------------------------------------------------------------------
# .mogg
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("data", [
    struct.pack("<iIIII", 0x10, 0, 0, 0, 1000),            # tabela maior que o arquivo
    struct.pack("<iIIII", 0x0B, 0, 0, 0, 0) + b"\x01" * 4,  # nonce curto
    struct.pack("<iIIII", 0x0C, 0, 0, 0, 0) + bytes(20),    # seeds truncados
    struct.pack("<iIIII", 0x0A, 0, 0, 0, 0xFFFFFFF),        # sem cripto, tabela absurda
])
def test_read_mogg_header_garbage_is_mogg_error(data):
    with pytest.raises(MoggCryptError):
        read_mogg_header(data)
