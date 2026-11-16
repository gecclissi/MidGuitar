"""Capa png_xbox (HMX bitmap DXT1 com bytes trocados) comparada com a CON real."""
import os

import numpy as np
import pytest
from PIL import Image

from src.creator.png_xbox import HEADER, decode_png_xbox, encode_png_xbox, swap16, write_png_xbox
from src.creator.xbox_stfs import StfsPackage

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REF_CON = os.path.join(ROOT, "music", "_refs", "xbox_con", "Joe Dassin - Salut les amoureux_rb3con")
REF_ART = os.path.join(ROOT, "music", "_refs", "Joe Dassin - Salut les amoureux", "album.png")
needs_ref = pytest.mark.skipif(not (os.path.isfile(REF_CON) and os.path.isfile(REF_ART)),
                               reason="CON de referência ausente")


def _psnr(a, b):
    mse = ((a.astype(float) - b.astype(float)) ** 2).mean()
    return 10 * np.log10(255 ** 2 / max(mse, 1e-9))


def _test_image():
    y, x = np.mgrid[0:300, 0:300]
    img = np.stack([x * 255 // 299, y * 255 // 299, (x + y) * 255 // 598], -1)
    return Image.fromarray(img.astype(np.uint8))


@pytest.fixture(scope="module")
def ref_art():
    pkg = StfsPackage(REF_CON)
    entry = next(e for e in pkg.files() if e.path.endswith("_keep.png_xbox"))
    return pkg.read_file(entry)


def test_swap16():
    assert swap16(b"\x01\x02\x03\x04\x05") == b"\x02\x01\x04\x03\x05"


def test_round_trip_close_to_source(tmp_path):
    img = _test_image()
    data = encode_png_xbox(img)
    assert data[:32] == HEADER and len(data) == 43720
    out = decode_png_xbox(data)
    src = np.asarray(img.resize((256, 256), Image.Resampling.LANCZOS))
    assert out.shape == (256, 256, 4)
    assert _psnr(out[..., :3], src) > 30
    assert decode_png_xbox(data, 6).shape == (4, 4, 4)
    p = tmp_path / "a.png"
    img.save(p)
    assert write_png_xbox(str(p), str(tmp_path / "a_keep.png_xbox"))


@needs_ref
def test_reference_header_and_size(ref_art):
    assert len(ref_art) == 43720
    assert ref_art[:32] == HEADER


@needs_ref
def test_reference_decodes_to_clone_hero_cover(ref_art):
    """A capa decodificada da CON é a mesma do album.png do Clone Hero (só a troca de
    bytes do Xbox dá uma imagem coerente)."""
    ch = np.asarray(Image.open(REF_ART).convert("RGB").resize((256, 256), Image.Resampling.LANCZOS))
    assert _psnr(decode_png_xbox(ref_art)[..., :3], ch) > 30
    from src.creator.png_ps3 import decode_level
    unswapped = decode_level(ref_art[32:32 + 32768], 256, 256, 8)
    assert _psnr(unswapped[..., :3], ch) < 15


@needs_ref
def test_reencode_reference_is_close(ref_art):
    img = decode_png_xbox(ref_art)[..., :3]
    again = encode_png_xbox(Image.fromarray(img))
    assert len(again) == len(ref_art)
    assert _psnr(decode_png_xbox(again)[..., :3], img) > 40
