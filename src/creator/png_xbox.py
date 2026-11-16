"""Capa do álbum no formato do Rock Band 3 Xbox 360 (`gen/<s>_keep.png_xbox`).

Formato (Onyx, Onyx/Image/DXT.hs `toDXT1File PNGXbox`; conferido com a CON de referência,
43720 bytes):

- cabeçalho HMX Bitmap de 32 bytes, o mesmo do png_ps3 mas com DXT1:
    versão 1, 4 bits por pixel, codificação 8 (DXT1), mipmaps 4 (byte 6),
    largura 256, altura 256, 128 bytes por linha, zeros até 32;
- dados DXT1 (blocos de 8 bytes) dos níveis 256, 128, 64, 32, 16, 8 e 4 (sem 2 e 1),
  sem rodapé;
- cada bloco tem os bytes trocados de 2 em 2 (palavras de 16 bits big-endian do Xbox):
  [1, 0, 3, 2, 5, 4, 7, 6]. Trocar de volta dá o bloco DXT1 comum (como no png_ps3).
"""
from typing import List, Tuple

import numpy as np

from src.creator.png_ps3 import (ENCODING_DXT1, HEADER_SIZE, _encode_color, _image_to_blocks,
                                 decode_level, parse_header)

SIZE = 256
LEVELS: Tuple[int, ...] = (256, 128, 64, 32, 16, 8, 4)
HEADER = bytes([0x01, 0x04, 0x08, 0x00, 0x00, 0x00, 0x04, 0x00,
                0x01, 0x00, 0x01, 0x80]).ljust(HEADER_SIZE, b"\x00")


def swap16(data: bytes) -> bytes:
    """Troca os bytes de cada par (Xbox <-> PS3/PC)."""
    a = np.frombuffer(data[:len(data) // 2 * 2], np.uint8).reshape(-1, 2)[:, ::-1]
    return a.tobytes() + data[len(data) // 2 * 2:]


def _level_offsets(width: int, height: int) -> List[Tuple[int, int, int]]:
    """(largura, altura, offset) de cada nível gravado."""
    out = []
    off = HEADER_SIZE
    w, h = width, height
    while w >= 4 and h >= 4:
        out.append((w, h, off))
        off += (w // 4) * (h // 4) * 8
        w, h = w // 2, h // 2
    return out


def decode_png_xbox(data: bytes, level: int = 0) -> np.ndarray:
    """Arquivo png_xbox (DXT1) -> imagem RGBA (h, w, 4) do nível pedido (0 = maior)."""
    hdr = parse_header(data)
    if hdr["encoding"] != ENCODING_DXT1:
        raise ValueError("codificação png_xbox não suportada: %d" % hdr["encoding"])
    levels = _level_offsets(hdr["width"], hdr["height"])
    if level >= len(levels):
        raise ValueError("nível de mipmap inexistente: %d" % level)
    w, h, off = levels[level]
    size = (w // 4) * (h // 4) * 8
    if off + size > len(data):
        raise ValueError("png_xbox truncado")
    return decode_level(swap16(data[off:off + size]), w, h, ENCODING_DXT1)


def encode_level_dxt1(rgb: np.ndarray) -> bytes:
    """Imagem RGB (h, w, 3) com lados múltiplos de 4 -> blocos DXT1 comuns."""
    return _encode_color(_image_to_blocks(np.asarray(rgb, np.float64))).tobytes()


def encode_png_xbox(image) -> bytes:
    """Imagem PIL (ou array) -> bytes de um `_keep.png_xbox` 256x256 DXT1 com mipmaps."""
    from PIL import Image
    if isinstance(image, np.ndarray):
        image = Image.fromarray(image.astype(np.uint8))
    im = image.convert("RGB")
    if im.size != (SIZE, SIZE):
        im = im.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    parts = [HEADER]
    for s in LEVELS:
        lvl = im if s == SIZE else im.resize((s, s), Image.Resampling.BOX)
        parts.append(swap16(encode_level_dxt1(np.asarray(lvl, dtype=np.float64))))
    return b"".join(parts)


def write_png_xbox(image_path: str, dest_path: str) -> bool:
    """Converte uma imagem (png/jpg...) para `_keep.png_xbox`. False se falhar."""
    try:
        from PIL import Image
        with Image.open(image_path) as im:
            data = encode_png_xbox(im)
        with open(dest_path, "wb") as f:
            f.write(data)
        return True
    except Exception as e:
        print("[png_xbox] Erro ao gerar capa: %s" % e)
        return False
