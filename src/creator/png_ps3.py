"""Capa do álbum no formato do Rock Band 3 PS3 (`gen/<s>_keep.png_ps3`).

Formato (engenharia reversa das duas referências reais, ambas com 87444 bytes):

- cabeçalho HMX Bitmap de 32 bytes (little-endian):
    0  u8   versão (1)
    1  u8   bits por pixel (8 = DXT5)
    2  u32  codificação (24 = DXT5; 8 seria DXT1)
    6  u8   mipmaps (4 nas referências; o arquivo ainda leva a cadeia completa)
    7  u16  largura (256)
    9  u16  altura (256)
    11 u16  bytes por linha (256 = largura * bpp / 8)
    13      zeros até 32
- dados DXT5 (blocos de 16 bytes: alfa 8 bytes + cor 8 bytes) em ordem normal
  (sem troca de bytes), nível 256x256 seguido dos mipmaps 128..1 (cadeia completa,
  com mínimo de 1 bloco por nível): 87408 bytes;
- 4 bytes finais 0xAA (preenchimento, copiado das referências).
"""
import struct
from typing import List

import numpy as np

HEADER_SIZE = 32
ENCODING_DXT1 = 8
ENCODING_DXT5 = 24
SIZE = 256
# Mipmaps declarados no cabeçalho das referências (a cadeia gravada é completa)
_HEADER_MIPMAPS = 4
_TRAILER = b"\xaa\xaa\xaa\xaa"


def _mip_sizes(width: int, height: int) -> List[tuple]:
    sizes = []
    w, h = width, height
    while True:
        sizes.append((w, h))
        if w == 1 and h == 1:
            break
        w, h = max(1, w // 2), max(1, h // 2)
    return sizes


def _level_bytes(w: int, h: int, block_size: int) -> int:
    return max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * block_size


def parse_header(data: bytes) -> dict:
    if len(data) < HEADER_SIZE:
        raise ValueError("png_ps3 curto demais")
    version, bpp, encoding, mips, width, height, bpl = struct.unpack_from("<BBIBHHH", data, 0)
    return {"version": version, "bpp": bpp, "encoding": encoding, "mipmaps": mips,
            "width": width, "height": height, "bytes_per_line": bpl}


def _rgb565_to_rgb(c: np.ndarray) -> np.ndarray:
    c = c.astype(np.uint32)
    r = (c >> 11) & 31
    g = (c >> 5) & 63
    b = c & 31
    return np.stack([(r * 255 + 15) // 31, (g * 255 + 31) // 63, (b * 255 + 15) // 31], -1).astype(np.int32)


def _decode_color_blocks(blk: np.ndarray, dxt1: bool) -> np.ndarray:
    """blk: (n, 8) uint8 -> (n, 16, 4) RGBA."""
    c0 = blk[:, 0].astype(np.uint16) | (blk[:, 1].astype(np.uint16) << 8)
    c1 = blk[:, 2].astype(np.uint16) | (blk[:, 3].astype(np.uint16) << 8)
    p0, p1 = _rgb565_to_rgb(c0), _rgb565_to_rgb(c1)
    four = (c0 > c1) | (not dxt1)
    p2 = np.where(four[:, None], (2 * p0 + p1) // 3, (p0 + p1) // 2)
    p3 = np.where(four[:, None], (p0 + 2 * p1) // 3, 0)
    palette = np.stack([p0, p1, p2, p3], 1)  # (n, 4, 3)
    alpha = np.full((len(blk), 4), 255, np.int32)
    if dxt1:
        alpha[:, 3] = np.where(four, 255, 0)
    bits = blk[:, 4:8].astype(np.uint32)
    idx_word = bits[:, 0] | (bits[:, 1] << 8) | (bits[:, 2] << 16) | (bits[:, 3] << 24)
    idx = ((idx_word[:, None] >> (2 * np.arange(16, dtype=np.uint32))) & 3).astype(np.int64)
    rows = np.arange(len(blk))[:, None]
    rgb = palette[rows, idx]
    a = alpha[rows, idx]
    return np.concatenate([rgb, a[..., None]], -1)


def _decode_alpha_blocks(blk: np.ndarray) -> np.ndarray:
    """blk: (n, 8) uint8 (alfa DXT5) -> (n, 16) alfa."""
    a0 = blk[:, 0].astype(np.int32)
    a1 = blk[:, 1].astype(np.int32)
    pal = np.zeros((len(blk), 8), np.int32)
    pal[:, 0], pal[:, 1] = a0, a1
    eight = a0 > a1
    for i in range(1, 7):
        pal[:, i + 1] = np.where(eight, ((7 - i) * a0 + i * a1) // 7, 0)
    for i in range(1, 5):
        pal[:, i + 1] = np.where(eight, pal[:, i + 1], ((5 - i) * a0 + i * a1) // 5)
    pal[:, 6] = np.where(eight, pal[:, 6], 0)
    pal[:, 7] = np.where(eight, pal[:, 7], 255)
    word = np.zeros(len(blk), np.uint64)
    for i in range(6):
        word |= blk[:, 2 + i].astype(np.uint64) << np.uint64(8 * i)
    idx = ((word[:, None] >> (np.uint64(3) * np.arange(16, dtype=np.uint64))) & np.uint64(7)).astype(np.int64)
    return pal[np.arange(len(blk))[:, None], idx]


def _blocks_to_image(px: np.ndarray, w: int, h: int) -> np.ndarray:
    bw, bh = max(1, (w + 3) // 4), max(1, (h + 3) // 4)
    img = px.reshape(bh, bw, 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(bh * 4, bw * 4, 4)
    return img[:h, :w].astype(np.uint8)


def decode_level(data: bytes, w: int, h: int, encoding: int) -> np.ndarray:
    """Decodifica um nível DXT1/DXT5 em RGBA (h, w, 4) uint8."""
    dxt1 = encoding == ENCODING_DXT1
    bsize = 8 if dxt1 else 16
    n = max(1, (w + 3) // 4) * max(1, (h + 3) // 4)
    blk = np.frombuffer(data[:n * bsize], np.uint8).reshape(n, bsize)
    if dxt1:
        px = _decode_color_blocks(blk, True)
    else:
        px = _decode_color_blocks(blk[:, 8:], False)
        px[:, :, 3] = _decode_alpha_blocks(blk[:, :8])
    return _blocks_to_image(px, w, h)


def decode_png_ps3(data: bytes, level: int = 0) -> np.ndarray:
    """Arquivo png_ps3 -> imagem RGBA (h, w, 4) do nível pedido (0 = maior)."""
    hdr = parse_header(data)
    if hdr["encoding"] not in (ENCODING_DXT1, ENCODING_DXT5):
        raise ValueError("codificação png_ps3 não suportada: %d" % hdr["encoding"])
    bsize = 8 if hdr["encoding"] == ENCODING_DXT1 else 16
    off = HEADER_SIZE
    for i, (w, h) in enumerate(_mip_sizes(hdr["width"], hdr["height"])):
        size = _level_bytes(w, h, bsize)
        if i == level:
            if off + size > len(data):
                raise ValueError("png_ps3 truncado")
            return decode_level(data[off:off + size], w, h, hdr["encoding"])
        off += size
    raise ValueError("nível de mipmap inexistente: %d" % level)


# ---------------------------------------------------------------------------
# Codificador
# ---------------------------------------------------------------------------
def _rgb_to_565(rgb: np.ndarray) -> np.ndarray:
    rgb = np.clip(np.rint(rgb), 0, 255).astype(np.uint32)
    return (((rgb[..., 0] * 31 + 127) // 255) << 11) | (((rgb[..., 1] * 63 + 127) // 255) << 5) \
        | ((rgb[..., 2] * 31 + 127) // 255)


def _image_to_blocks(img: np.ndarray) -> np.ndarray:
    """(h, w, c) com h, w múltiplos de 4 -> (n, 16, c)."""
    h, w, c = img.shape
    return img.reshape(h // 4, 4, w // 4, 4, c).transpose(0, 2, 1, 3, 4).reshape(-1, 16, c)


def _encode_color(px: np.ndarray) -> np.ndarray:
    """px: (n, 16, 3) float -> (n, 8) uint8 de cor DXT (modo de 4 cores)."""
    n = len(px)
    mean = px.mean(1, keepdims=True)
    centered = px - mean
    cov = np.einsum("nki,nkj->nij", centered, centered)
    # Eixo principal por iteração de potência (estável e vetorizado)
    axis = np.ones((n, 3)) / np.sqrt(3.0)
    for _ in range(8):
        axis = np.einsum("nij,nj->ni", cov, axis)
        norm = np.linalg.norm(axis, axis=1, keepdims=True)
        axis = np.where(norm > 1e-9, axis / np.maximum(norm, 1e-12), 1.0 / np.sqrt(3.0))
    proj = np.einsum("nki,ni->nk", centered, axis)
    lo = mean[:, 0] + axis * proj.min(1, keepdims=True)
    hi = mean[:, 0] + axis * proj.max(1, keepdims=True)
    c_hi = _rgb_to_565(hi)
    c_lo = _rgb_to_565(lo)
    # Modo de 4 cores exige c0 > c1; iguais -> todos os índices 0
    swap = c_hi < c_lo
    c0 = np.where(swap, c_lo, c_hi)
    c1 = np.where(swap, c_hi, c_lo)
    p0 = _rgb565_to_rgb(c0).astype(np.float64)
    p1 = _rgb565_to_rgb(c1).astype(np.float64)
    pal = np.stack([p0, p1, (2 * p0 + p1) / 3.0, (p0 + 2 * p1) / 3.0], 1)  # (n, 4, 3)
    dist = ((px[:, :, None, :] - pal[:, None, :, :]) ** 2).sum(-1)  # (n, 16, 4)
    idx = dist.argmin(-1).astype(np.uint32)
    idx = np.where((c0 == c1)[:, None], 0, idx)
    word = (idx << (2 * np.arange(16, dtype=np.uint32))).sum(1).astype(np.uint32)
    out = np.zeros((n, 8), np.uint8)
    out[:, 0], out[:, 1] = c0 & 0xFF, c0 >> 8
    out[:, 2], out[:, 3] = c1 & 0xFF, c1 >> 8
    for i in range(4):
        out[:, 4 + i] = (word >> (8 * i)) & 0xFF
    return out


def _encode_alpha(a: np.ndarray) -> np.ndarray:
    """a: (n, 16) -> (n, 8) uint8 de alfa DXT5 (modo de 8 valores)."""
    n = len(a)
    a = np.clip(np.rint(a), 0, 255).astype(np.int32)
    a0, a1 = a.max(1), a.min(1)
    out = np.zeros((n, 8), np.uint8)
    out[:, 0], out[:, 1] = a0, a1
    flat = a0 == a1
    pal = np.zeros((n, 8), np.float64)
    pal[:, 0], pal[:, 1] = a0, a1
    for i in range(1, 7):
        pal[:, i + 1] = ((7 - i) * a0 + i * a1) // 7
    idx = np.abs(a[:, :, None] - pal[:, None, :]).argmin(-1).astype(np.uint64)
    idx = np.where(flat[:, None], np.uint64(0), idx)
    word = np.zeros(n, np.uint64)
    for k in range(16):
        word |= idx[:, k] << np.uint64(3 * k)
    for i in range(6):
        out[:, 2 + i] = ((word >> np.uint64(8 * i)) & np.uint64(0xFF)).astype(np.uint8)
    return out


def encode_level(rgba: np.ndarray) -> bytes:
    """Imagem RGBA (h, w, 4) -> blocos DXT5 de um nível (níveis < 4 px são completados)."""
    h, w = rgba.shape[:2]
    ph, pw = max(4, (h + 3) // 4 * 4), max(4, (w + 3) // 4 * 4)
    img = np.zeros((ph, pw, 4), np.float64)
    img[:h, :w] = rgba
    if ph > h:
        img[h:, :w] = img[h - 1:h, :w]
    if pw > w:
        img[:, w:] = img[:, w - 1:w]
    blocks = _image_to_blocks(img)
    out = np.concatenate([_encode_alpha(blocks[:, :, 3]), _encode_color(blocks[:, :, :3])], 1)
    return out.tobytes()


def build_header(width: int = SIZE, height: int = SIZE) -> bytes:
    hdr = struct.pack("<BBIBHHH", 1, 8, ENCODING_DXT5, _HEADER_MIPMAPS, width, height, width)
    return hdr.ljust(HEADER_SIZE, b"\x00")


def encode_png_ps3(image) -> bytes:
    """Imagem PIL (ou array RGBA) -> bytes de um `_keep.png_ps3` 256x256 DXT5 com mipmaps."""
    from PIL import Image
    if isinstance(image, np.ndarray):
        image = Image.fromarray(image.astype(np.uint8))
    im = image.convert("RGBA")
    if im.size != (SIZE, SIZE):
        im = im.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    parts = [build_header()]
    for w, h in _mip_sizes(SIZE, SIZE):
        lvl = im if (w, h) == im.size else im.resize((w, h), Image.Resampling.BOX)
        parts.append(encode_level(np.asarray(lvl, dtype=np.float64)))
    parts.append(_TRAILER)
    return b"".join(parts)


def write_png_ps3(image_path: str, dest_path: str) -> bool:
    """Converte uma imagem (png/jpg...) para `_keep.png_ps3`. False se falhar."""
    try:
        from PIL import Image
        with Image.open(image_path) as im:
            data = encode_png_ps3(im)
        with open(dest_path, "wb") as f:
            f.write(data)
        return True
    except Exception as e:
        print("[png_ps3] Erro ao gerar capa: %s" % e)
        return False
