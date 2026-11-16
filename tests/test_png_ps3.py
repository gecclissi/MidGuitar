"""Capa png_ps3 (gen/<s>_keep.png_ps3): decodificador contra as referências reais e ida e volta."""
import glob
import os

import numpy as np
import pytest
from PIL import Image

from src.creator.png_ps3 import (HEADER_SIZE, decode_png_ps3, encode_png_ps3, parse_header,
                                 write_png_ps3)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REF_ARTS = sorted(glob.glob(os.path.join(ROOT, "music", "_refs", "*", "USRDIR", "*", "songs",
                                         "*", "gen", "*_keep.png_ps3")))
needs_refs = pytest.mark.skipif(not REF_ARTS, reason="referências PS3 ausentes")


def _test_image():
    y, x = np.mgrid[0:256, 0:256]
    img = np.zeros((256, 256, 4), np.uint8)
    img[..., 0] = x
    img[..., 1] = y
    img[..., 2] = np.where((x // 32 + y // 32) % 2, 200, 40)
    img[..., 3] = 255
    return img


@needs_refs
def test_reference_header_and_size():
    for path in REF_ARTS:
        data = open(path, "rb").read()
        hdr = parse_header(data)
        assert len(data) == 87444
        assert (hdr["width"], hdr["height"], hdr["encoding"], hdr["bpp"]) == (256, 256, 24, 8)


@needs_refs
def test_reference_decodes_to_plausible_image():
    for path in REF_ARTS:
        img = decode_png_ps3(open(path, "rb").read())
        assert img.shape == (256, 256, 4)
        assert (img[..., 3] == 255).all()
        # Capa real: cores variadas, nada de ruído nem imagem chapada
        assert img[..., :3].std() > 30
        # Mipmap 128 é a mesma imagem reduzida
        half = np.asarray(Image.fromarray(img).resize((128, 128), Image.BOX), np.float64)
        lvl1 = decode_png_ps3(open(path, "rb").read(), level=1).astype(np.float64)
        assert np.abs(half - lvl1)[..., :3].mean() < 10
        # Vizinhos parecidos (imagem coerente, não blocos trocados)
        diff = np.abs(np.diff(img[..., :3].astype(int), axis=1)).mean()
        assert diff < 20


@needs_refs
def test_encoder_header_matches_references():
    ours = encode_png_ps3(Image.fromarray(_test_image()))
    for path in REF_ARTS:
        ref = open(path, "rb").read()
        assert ours[:HEADER_SIZE] == ref[:HEADER_SIZE]
        assert len(ours) == len(ref)
        assert ours[-4:] == ref[-4:]


def test_round_trip_close_to_source():
    src = _test_image()
    data = encode_png_ps3(Image.fromarray(src))
    assert len(data) == 87444
    out = decode_png_ps3(data)
    err = np.abs(out[..., :3].astype(int) - src[..., :3].astype(int))
    assert err.mean() < 6
    assert (out[..., 3] == 255).all()
    small = decode_png_ps3(data, level=8)
    assert small.shape == (1, 1, 4)


def test_round_trip_flat_and_alpha():
    src = np.zeros((256, 256, 4), np.uint8)
    src[..., :3] = (10, 120, 250)
    src[..., 3] = np.tile(np.arange(256, dtype=np.uint8), (256, 1))
    out = decode_png_ps3(encode_png_ps3(src))
    assert np.abs(out[..., :3].astype(int) - src[..., :3]).max() <= 8
    assert np.abs(out[..., 3].astype(int) - src[..., 3]).max() <= 20


def test_write_png_ps3_resizes_any_image(tmp_path):
    src = tmp_path / "capa.jpg"
    Image.new("RGB", (500, 300), (200, 30, 30)).save(src)
    dest = tmp_path / "x_keep.png_ps3"
    assert write_png_ps3(str(src), str(dest))
    img = decode_png_ps3(dest.read_bytes())
    assert img.shape == (256, 256, 4)
    assert abs(int(img[..., 0].mean()) - 200) < 8
