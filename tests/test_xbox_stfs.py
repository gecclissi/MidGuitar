"""Pacote STFS (CON) do Xbox 360: leitura, verificação e criação, comparando com a CON real."""
import filecmp
import os
import shutil

import pytest

from src.creator import xbox_stfs as X
from src.creator.xbox_stfs import StfsError, StfsPackage, build_con, is_stfs_file

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REF_CON = os.path.join(ROOT, "music", "_refs", "xbox_con", "Joe Dassin - Salut les amoureux_rb3con")
needs_ref = pytest.mark.skipif(not os.path.isfile(REF_CON), reason="CON de referência ausente")
SHORT = "o856659797_salutlesamoureu"


@pytest.fixture(scope="module")
def ref_con(tmp_path_factory):
    dst = str(tmp_path_factory.mktemp("con") / "ref_rb3con")
    shutil.copyfile(REF_CON, dst)
    return dst


def _tree_diff(a, b):
    d = filecmp.dircmp(a, b)
    bad = d.left_only + d.right_only + d.diff_files + d.funny_files
    for s in d.common_dirs:
        bad += _tree_diff(os.path.join(a, s), os.path.join(b, s))
    return bad


def _make_tree(root, mogg_size=70001):
    song = os.path.join(root, "songs", "teste")
    os.makedirs(os.path.join(song, "gen"))
    files = {
        os.path.join("songs", "songs.dta"): b"(teste (name \"x\"))",
        os.path.join(song, "teste.mid"): b"MThd" + bytes(50),
        os.path.join(song, "teste.mogg"): os.urandom(mogg_size),
        os.path.join(song, "gen", "teste_keep.png_xbox"): b"",
    }
    for rel, data in files.items():
        with open(os.path.join(root, rel), "wb") as f:
            f.write(data)


def test_layout_formulas_match_pattern():
    """Fórmulas de posição do Onyx == padrão de blocos (inclusive com tabelas nível 2)."""
    n = 0xAA * 0xAA * 2 + 5
    lay = X._layout(n)
    assert lay["L0"][:3] == [-1, 171, 342] and lay["L1"][0] == 170
    for b in range(0, n, 37):
        assert X._fix_block_number(b, 0) == lay["D"][b]
        assert X._hash_table_real(b, 0, 0) == lay["L0"][b // 0xAA]


@pytest.mark.parametrize("mogg_size", [70001, 0xAA * 0x1000 + 1, 0])
def test_build_read_roundtrip(tmp_path, mogg_size):
    src = str(tmp_path / "src")
    _make_tree(src, mogg_size)
    con = build_con(src, str(tmp_path / "t_rb3con"), "Artista - Título", "Descrição",
                    thumbnail=b"\x89PNG fake")
    assert is_stfs_file(con)
    pkg = StfsPackage(con)
    assert pkg.verify() == []
    assert pkg.signature_status() is True and pkg.signed_with_known_kv()
    assert pkg.magic == "CON" and pkg.title_id == X.RB3_TITLE_ID
    assert pkg.content_type == X.CONTENT_SAVED_GAME
    assert pkg.display_name == "Artista - Título" and pkg.description == "Descrição"
    assert pkg.title_name == "Rock Band 3" and pkg.thumbnail == b"\x89PNG fake"
    assert pkg.content_size == os.path.getsize(con) - 0xB000
    out = str(tmp_path / "out")
    pkg.extract(out)
    assert _tree_diff(src, out) == []
    assert pkg.read_file("songs/songs.dta") == b"(teste (name \"x\"))"


def test_tampering_is_detected(tmp_path):
    src = str(tmp_path / "src")
    _make_tree(src)
    con = build_con(src, str(tmp_path / "t_rb3con"), "x")
    with open(con, "r+b") as f:
        f.seek(0xC000 + 2 * 0x1000 + 10)
        b = f.read(1)
        f.seek(-1, 1)
        f.write(bytes([b[0] ^ 0xFF]))
        f.seek(0x412)
        f.write(b"Z")
    problems = StfsPackage(con).verify()
    assert any("bloco" in p for p in problems)
    assert any("cabeçalho" in p for p in problems)


def test_not_stfs(tmp_path):
    p = tmp_path / "x.bin"
    p.write_bytes(b"NOPE" + bytes(0x10000))
    assert not is_stfs_file(str(p))
    with pytest.raises(StfsError):
        StfsPackage(str(p))


@needs_ref
def test_reference_header_and_tree(ref_con):
    pkg = StfsPackage(ref_con)
    assert pkg.magic == "CON" and pkg.console_type == 2
    assert pkg.console_part_number == "X803395-001" and pkg.cert_date == "09-18-06"
    assert pkg.title_id == 0x45410914 and pkg.title_name == "Rock Band 3"
    assert pkg.content_type == X.CONTENT_SAVED_GAME and pkg.metadata_version == 2
    assert pkg.header_size == 0xAD0E and pkg.licenses[0] == (-1, 1, 0)
    assert pkg.display_name == "Joe Dassin - Salut les amoureux"
    assert pkg.thumbnail[:4] == b"\x89PNG"
    assert sorted(e.path for e in pkg.files()) == sorted([
        "songs/songs.dta",
        "songs/%s/%s.mid" % (SHORT, SHORT),
        "songs/%s/%s.mogg" % (SHORT, SHORT),
        "songs/%s/gen/%s.milo_xbox" % (SHORT, SHORT),
        "songs/%s/gen/%s_keep.png_xbox" % (SHORT, SHORT),
    ])


@needs_ref
def test_reference_hashes_and_signature(ref_con):
    pkg = StfsPackage(ref_con)
    assert pkg.verify() == []                 # cabeçalho, blocos, tabelas L1 e topo
    assert pkg.signature_status() is True     # assinatura confere com o certificado
    assert pkg.signed_with_known_kv()         # e é o certificado do KV do Onyx/C3


@needs_ref
def test_rebuild_reference_is_byte_identical(ref_con, tmp_path):
    """Extrair e recriar com os mesmos metadados dá exatamente a CON real (inclusive a
    assinatura): confirma layout, hashes, metadados e a chave de assinatura."""
    pkg = StfsPackage(ref_con)
    ext = str(tmp_path / "ext")
    pkg.extract(ext)
    out = build_con(ext, str(tmp_path / "rebuilt"), pkg.display_name, pkg.description,
                    thumbnail=pkg.thumbnail, title_thumbnail=pkg.title_thumbnail)
    assert filecmp.cmp(ref_con, out, shallow=False)


@needs_ref
def test_reference_signature_reproduced(ref_con):
    with open(ref_con, "rb") as f:
        head = f.read(0x344)
    assert X.con_signature(head[0x22C:0x344]) == head[0x1AC:0x22C]
