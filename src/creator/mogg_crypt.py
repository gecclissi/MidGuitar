"""
Descriptografia de .mogg do Rock Band (versões 0x0B, 0x0C e 0x0D).

Portado da implementação C++ do Onyx (mtolly/onyx, pacote onyx-moggcrypt/cbits:
VorbisReader.cpp, ByteGrinder.cpp, keygen.cpp, ops.c, keys.h), que por sua vez
segue o algoritmo da Harmonix:

- O stream Ogg depois do cabeçalho é AES-128 em modo CTR. O contador inicial
  (16 bytes) fica logo depois da tabela de busca e é somado como inteiro
  little-endian de 128 bits, um bloco por 16 bytes.
- 0x0B: chave CTR fixa (a mesma do SongCrypt).
- 0x0C/0x0D: a chave CTR = chave escondida (hiddenKeys[índice], revelada com o
  "masher" e convertida de hex) passada pelo "ByteGrinder" (ops sorteadas pelas
  sementes do arquivo) XOR a chave do arquivo decifrada com AES-ECB (HvKey 0).
  Os primeiros 32 bytes decifrados começam com "HMXA" e são corrigidos para "OggS".

Verificação (tests/test_mogg_crypt.py, com as referências em music/_refs):
0x0B (5 Seconds Of Summer - Ghost Of You) e 0x0D (Gorillaz - Andromeda) decifram
para Ogg Vorbis que o soundfile decodifica inteiro, com a duração do songs.dta.
0x0C usa exatamente o mesmo caminho do 0x0D (HvKey 0, mapa de 5 bits, só as ops
do RB2), por isso entra junto; não há referência 0x0C para conferir.
0x0E+ (chaves HvKey 1-4, mapa de 6 bits e ops do RB3) e 0x11 ficam sem suporte:
nenhuma referência para verificar.
"""

import struct

import numpy as np

# Versões que sabemos descriptografar (0x0A não é criptografada)
SUPPORTED_ENCRYPTED_VERSIONS = (0x0B, 0x0C, 0x0D)

_LCG_MUL = 0x19660D
_LCG_ADD = 0x3C6EF35F
_M32 = 0xFFFFFFFF

# keys.h (Onyx): chave CTR do 0x0B
_CTR_KEY_0B = bytes([
    0x37, 0xB2, 0xE2, 0xB9, 0x1C, 0x74, 0xFA, 0x9E, 0x38, 0x81, 0x08, 0xEA, 0x36, 0x23, 0xDB, 0xE4,
])

# keys.h (Onyx): HvKeys[0] (método 0, usado por 0x0C/0x0D)
_HV_KEY_0 = bytes([
    0x01, 0x22, 0x00, 0x38, 0xD2, 0x01, 0x78, 0x8B, 0xDD, 0xCD, 0xD0, 0xF0, 0xFE, 0x3E, 0x24, 0x7F,
])

# keys.h (Onyx): hiddenKeys (12 chaves de 32 bytes; o arquivo usa os índices 6 a 11)
_HIDDEN_KEYS = bytes([
    0x7F, 0x95, 0x5B, 0x9D, 0x94, 0xBA, 0x12, 0xF1, 0xD7, 0x5A, 0x67, 0xD9, 0x16, 0x45, 0x28, 0xDD,
    0x61, 0x55, 0x55, 0xAF, 0x23, 0x91, 0xD6, 0x0A, 0x3A, 0x42, 0x81, 0x18, 0xB4, 0xF7, 0xF3, 0x04,
    0x78, 0x96, 0x5D, 0x92, 0x92, 0xB0, 0x47, 0xAC, 0x8F, 0x5B, 0x6D, 0xDC, 0x1C, 0x41, 0x7E, 0xDA,
    0x6A, 0x55, 0x53, 0xAF, 0x20, 0xC8, 0xDC, 0x0A, 0x66, 0x43, 0xDD, 0x1C, 0xB2, 0xA5, 0xA4, 0x0C,
    0x7E, 0x92, 0x5C, 0x93, 0x90, 0xED, 0x4A, 0xAD, 0x8B, 0x07, 0x36, 0xD3, 0x10, 0x41, 0x78, 0x8F,
    0x60, 0x08, 0x55, 0xA8, 0x26, 0xCF, 0xD0, 0x0F, 0x65, 0x11, 0x84, 0x45, 0xB1, 0xA0, 0xFA, 0x57,
    0x79, 0x97, 0x0B, 0x90, 0x92, 0xB0, 0x44, 0xAD, 0x8A, 0x0E, 0x60, 0xD9, 0x14, 0x11, 0x7E, 0x8D,
    0x35, 0x5D, 0x5C, 0xFB, 0x21, 0x9C, 0xD3, 0x0E, 0x32, 0x40, 0xD1, 0x48, 0xB8, 0xA7, 0xA1, 0x0D,
    0x28, 0xC3, 0x5D, 0x97, 0xC1, 0xEC, 0x42, 0xF1, 0xDC, 0x5D, 0x37, 0xDA, 0x14, 0x47, 0x79, 0x8A,
    0x32, 0x5C, 0x54, 0xF2, 0x72, 0x9D, 0xD3, 0x0D, 0x67, 0x4C, 0xD6, 0x49, 0xB4, 0xA2, 0xF3, 0x50,
    0x28, 0x96, 0x5E, 0x95, 0xC5, 0xE9, 0x45, 0xAD, 0x8A, 0x5D, 0x64, 0x8E, 0x17, 0x40, 0x2E, 0x87,
    0x36, 0x58, 0x06, 0xFD, 0x75, 0x90, 0xD0, 0x5F, 0x3A, 0x40, 0xD4, 0x4C, 0xB0, 0xF7, 0xA7, 0x04,
    0x2C, 0x96, 0x01, 0x96, 0x9B, 0xBC, 0x15, 0xA6, 0xDE, 0x0E, 0x65, 0x8D, 0x17, 0x47, 0x2F, 0xDD,
    0x63, 0x54, 0x55, 0xAF, 0x76, 0xCA, 0x84, 0x5F, 0x62, 0x44, 0x80, 0x4A, 0xB3, 0xF4, 0xF4, 0x0C,
    0x7E, 0xC4, 0x0E, 0xC6, 0x9A, 0xEB, 0x43, 0xA0, 0xDB, 0x0A, 0x64, 0xDF, 0x1C, 0x42, 0x24, 0x89,
    0x63, 0x5C, 0x55, 0xF3, 0x71, 0x90, 0xDC, 0x5D, 0x60, 0x40, 0xD1, 0x4D, 0xB2, 0xA3, 0xA7, 0x0D,
    0x2C, 0x9A, 0x0B, 0x90, 0x9A, 0xBE, 0x47, 0xA7, 0x88, 0x5A, 0x6D, 0xDF, 0x13, 0x1D, 0x2E, 0x8B,
    0x60, 0x5E, 0x55, 0xF2, 0x74, 0x9C, 0xD7, 0x0E, 0x60, 0x40, 0x80, 0x1C, 0xB7, 0xA1, 0xF4, 0x02,
    0x28, 0x96, 0x5B, 0x95, 0xC1, 0xE9, 0x40, 0xA3, 0x8F, 0x0C, 0x32, 0xDF, 0x43, 0x1D, 0x24, 0x8D,
    0x61, 0x09, 0x54, 0xAB, 0x27, 0x9A, 0xD3, 0x58, 0x60, 0x16, 0x84, 0x4F, 0xB3, 0xA4, 0xF3, 0x0D,
    0x25, 0x93, 0x08, 0xC0, 0x9A, 0xBD, 0x10, 0xA2, 0xD6, 0x09, 0x60, 0x8F, 0x11, 0x1D, 0x7A, 0x8F,
    0x63, 0x0B, 0x5D, 0xF2, 0x21, 0xEC, 0xD7, 0x08, 0x62, 0x40, 0x84, 0x49, 0xB0, 0xAD, 0xF2, 0x07,
    0x29, 0xC3, 0x0C, 0x96, 0x96, 0xEB, 0x10, 0xA0, 0xDA, 0x59, 0x32, 0xD3, 0x17, 0x41, 0x25, 0xDC,
    0x63, 0x08, 0x04, 0xAE, 0x77, 0xCB, 0x84, 0x5A, 0x60, 0x4D, 0xDD, 0x45, 0xB5, 0xF4, 0xA0, 0x05,
])


class MoggCryptError(Exception):
    """O .mogg não pôde ser descriptografado (versão sem suporte ou dados inválidos)."""


def mogg_version(path: str) -> int:
    """Versão do cabeçalho do .mogg (0x0A = sem criptografia) ou -1 se ilegível."""
    try:
        with open(path, "rb") as f:
            head = f.read(4)
    except OSError:
        return -1
    if len(head) < 4:
        return -1
    return struct.unpack("<i", head)[0]


def is_supported_encrypted_mogg(path: str) -> bool:
    return mogg_version(path) in SUPPORTED_ENCRYPTED_VERSIONS


# ---------------------------------------------------------------------------
# Geração da chave (keygen.cpp / ByteGrinder.cpp / ops.c)
# ---------------------------------------------------------------------------

def _rotr(val: int, amt: int) -> int:
    return ((val >> amt) | (val << (8 - amt))) & 0xFF


def _op(n: int, bar: int, foo: int) -> int:
    """ops.c: só as ops 0-31 (opsRB2) são usadas por 0x0C/0x0D."""
    if n == 0:
        r = foo ^ bar
    elif n == 1:
        r = foo + bar
    elif n == 2:
        r = _rotr(foo, bar & 7)
    elif n == 3:
        r = _rotr(foo, 1 if bar == 0 else 0)
    elif n == 4:
        r = _rotr(1 if foo == 0 else 0, 1 if bar == 0 else 0)
    elif n == 5:
        r = _rotr(0xFF ^ foo, bar & 7)
    elif n == 6:
        r = bar ^ (1 if foo == 0 else 0)
    elif n == 7:
        r = bar + (1 if foo == 0 else 0)
    elif n == 8:
        r = bar ^ (foo + bar)
    elif n == 9:
        r = bar + (foo ^ bar)
    elif n == 10:
        r = bar ^ _rotr(foo, 1 if bar == 0 else 0)
    elif n == 11:
        r = bar ^ _rotr(foo, bar & 7)
    elif n == 12:
        r = bar + _rotr(foo, bar & 7)
    elif n == 13:
        r = bar + _rotr(foo, 1 if bar == 0 else 0)
    elif 14 <= n <= 20:
        r = bar + _rotr(foo, n - 13)
    elif 21 <= n <= 27:
        r = bar ^ _rotr(foo, n - 20)
    elif n == 28:
        r = bar ^ (bar + _rotr(foo, 5))
    elif n == 29:
        r = bar ^ (bar + _rotr(foo, 3))
    elif n == 30:
        r = bar + (bar ^ _rotr(foo, 3))
    elif n == 31:
        r = bar + (bar ^ _rotr(foo, 5))
    else:
        raise MoggCryptError(f"op {n} não suportada")
    return r & 0xFF


def _pick_one_of_32(seed: int):
    """PickOneOf32A/B: sequência sem repetição de 0..31 a partir de uma semente."""
    used = [False] * 32
    while True:
        seed = (seed * _LCG_MUL + _LCG_ADD) & _M32
        tmp = (seed >> 2) & 0x1F
        if not used[tmp]:
            used[tmp] = True
            yield tmp


def _op_table():
    """ByteGrinder(): O[índice sorteado] = opsRB2[i] (só a metade RB2 nos importa)."""
    table = [0] * 32
    gen = _pick_one_of_32(0xD5)
    for i in range(32):
        table[next(gen)] = i
    return table


def _grind_array(seed1: int, seed2: int, key: bytearray) -> None:
    """ByteGrinder::GrindArray para versão <= 0x0D (mapa de 5 bits)."""
    ops = _op_table()
    hash_map = []
    s = seed1
    for _ in range(256):
        hash_map.append((s >> 3) & 0x1F)
        s = (_LCG_MUL * s + _LCG_ADD) & _M32
    gen = _pick_one_of_32(seed2)
    switch_cases = [next(gen) for _ in range(32)]
    n = len(key)
    for i in range(n):
        foo = key[i]
        for ix in range(0, n, 2):
            foo = _op(ops[switch_cases[hash_map[key[ix]]]], key[ix + 1], foo)
        key[i] = foo


def _master_key() -> bytes:
    """KeyChain::getMasher: 8 valores do LCG (mult. 0x19660E) a partir de 0xEB, little-endian."""
    out = bytearray()
    s = 0xEB
    for _ in range(8):
        s = (s * 0x19660E + _LCG_ADD) & _M32
        out += struct.pack("<I", s)
    return bytes(out)


def _roll(x: int) -> int:
    return (x + 19) % 32


def _supershuffle(p: bytearray) -> None:
    def sw(a, b):
        p[a], p[b] = p[b], p[a]
    for i in range(8):
        sw(_roll(i * 4), i * 4 + 2)
        sw(_roll(i * 4 + 3), i * 4 + 1)
    for i in range(8):
        sw(29 - i * 4, i * 4 + 2)
        sw(28 - i * 4, i * 4 + 3)
    for i in range(8):
        sw(_roll(4 * (7 - i) + 1), i * 4 + 2)
        sw(4 * (7 - i), i * 4 + 3)
    for i in range(8):
        sw(29 - i * 4, i * 4 + 2)
        sw(_roll(4 * (7 - i)), i * 4 + 3)
    for i in range(8):
        sw(29 - i * 4, _roll(i * 4 + 2))
        sw(28 - i * 4, i * 4 + 3)
    for i in range(8):
        sw(29 - i * 4, i * 4 + 2)
        sw(28 - i * 4, _roll(i * 4 + 3))


def _hex_nibble(c: int) -> int:
    if c > 96:
        return c - 87
    if c > 64:
        return c - 55
    if c > 47:
        return c - 48
    return 0


def _hidden_key(index: int) -> bytes:
    revealed = bytearray(_HIDDEN_KEYS[32 * index:32 * index + 32])
    for _ in range(14):
        _supershuffle(revealed)
    master = _master_key()
    for c in range(32):
        revealed[c] ^= master[c]
    return bytes(((_hex_nibble(revealed[2 * k]) << 4) | _hex_nibble(revealed[2 * k + 1])) & 0xFF
                 for k in range(16))


def _magic_number(seed: int, kind: int) -> int:
    if kind == 1:
        return (_LCG_MUL * ((_LCG_MUL * (seed ^ 0x5C5C5C5C) + _LCG_ADD) & _M32) + _LCG_ADD) & _M32
    return (_LCG_MUL * (seed ^ 0x36363636) + _LCG_ADD) & _M32


# ---------------------------------------------------------------------------
# Descriptografia
# ---------------------------------------------------------------------------

def _aes_ecb(key: bytes):
    from Crypto.Cipher import AES
    return AES.new(key, AES.MODE_ECB)


def _ctr_keystream(key: bytes, nonce: bytes, length: int) -> np.ndarray:
    """Fluxo AES-CTR: contador little-endian de 128 bits somado de 1 por bloco."""
    blocks = (length + 15) // 16
    low0 = np.uint64(struct.unpack("<Q", nonce[:8])[0])
    high0 = np.uint64(struct.unpack("<Q", nonce[8:])[0])
    with np.errstate(over="ignore"):
        low = low0 + np.arange(blocks, dtype=np.uint64)
        high = high0 + (low < low0).astype(np.uint64)
    counters = np.empty((blocks, 2), dtype="<u8")
    counters[:, 0] = low
    counters[:, 1] = high
    stream = _aes_ecb(key).encrypt(counters.tobytes())
    return np.frombuffer(stream, dtype=np.uint8)[:length]


def read_mogg_header(data: bytes) -> dict:
    """Campos do cabeçalho Harmonix: versão, início do Ogg, tabela de busca e dados de cripto.

    Cabeçalho truncado ou com valores absurdos levanta MoggCryptError (nunca struct.error)."""
    try:
        return _read_mogg_header(data)
    except struct.error as e:
        raise MoggCryptError("cabeçalho .mogg truncado: %s" % e)


def _read_mogg_header(data: bytes) -> dict:
    if len(data) < 20:
        raise MoggCryptError("arquivo curto demais para ser .mogg")
    version, ogg_offset, map_version, buffer_size, entries = struct.unpack_from("<iIIII", data, 0)
    pos = 20 + 8 * entries
    if pos > len(data):
        raise MoggCryptError("tabela de busca do .mogg maior que o arquivo")
    info = {"version": version, "ogg_offset": ogg_offset, "map_version": map_version,
            "buffer_size": buffer_size, "entries": entries,
            "seek_table": data[20:pos]}
    if version == 0x0A:
        return info
    info["nonce"] = data[pos:pos + 16]
    if len(info["nonce"]) != 16:
        raise MoggCryptError("cabeçalho .mogg truncado (nonce)")
    pos += 16
    if version >= 0x0C:
        seed1, seed2 = struct.unpack_from("<QQ", data, pos)
        pos += 16
        pos += 16  # 16 bytes ignorados (VorbisReader::CheckHmxHeader)
        info["seed1"] = seed1 & _M32
        info["seed2"] = seed2 & _M32
        info["file_key"] = data[pos:pos + 16]
        if len(info["file_key"]) != 16:
            raise MoggCryptError("cabeçalho .mogg truncado (chave)")
        pos += 16
        if version == 0x11:
            pos += 8
        info["key_index"] = (struct.unpack_from("<Q", data, pos)[0] % 6) + 6
    return info


def _ctr_key_for(info: dict) -> bytes:
    version = info["version"]
    if version == 0x0B:
        return _CTR_KEY_0B
    if version in (0x0C, 0x0D):
        file_key = _aes_ecb(_HV_KEY_0).decrypt(info["file_key"])
        grinded = bytearray(_hidden_key(info["key_index"]))
        _grind_array(info["seed1"], info["seed2"], grinded)
        return bytes(a ^ b for a, b in zip(grinded, file_key))
    raise MoggCryptError(f".mogg versão {version} (0x{version:02X}) sem suporte de descriptografia")


def decrypt_mogg_bytes(data: bytes) -> bytes:
    """Devolve o stream Ogg puro (começa com 'OggS') de um .mogg 0x0A/0x0B/0x0C/0x0D."""
    info = read_mogg_header(data)
    version = info["version"]
    if version == 0x0A:
        ogg = data[info["ogg_offset"]:]
    else:
        if version not in SUPPORTED_ENCRYPTED_VERSIONS:
            raise MoggCryptError(f".mogg versão {version} (0x{version:02X}) sem suporte de descriptografia")
        key = _ctr_key_for(info)
        enc = np.frombuffer(data, dtype=np.uint8)[info["ogg_offset"]:]
        plain = bytearray((enc ^ _ctr_keystream(key, info["nonce"], len(enc))).tobytes())
        if plain[:4] == b"HMXA":
            # VorbisReader::ReadFirst32: corrige o cabeçalho da primeira página
            plain[0:4] = b"OggS"
            m1 = struct.pack(">I", _magic_number(info["seed1"], 1))
            m2 = struct.pack(">I", _magic_number(info["seed2"], 2))
            for k in range(4):
                plain[12 + k] ^= m1[k]
                plain[20 + k] ^= m2[k]
        ogg = bytes(plain)
    if ogg[:4] != b"OggS":
        raise MoggCryptError("a descriptografia não produziu um stream Ogg (chave incorreta?)")
    return ogg


def decrypt_mogg(src_path: str, ogg_out_path: str = None, mogg_out_path: str = None) -> bytes:
    """Descriptografa um .mogg. Grava o .ogg puro e/ou um .mogg 0x0A (mesma tabela de busca)."""
    with open(src_path, "rb") as f:
        data = f.read()
    ogg = decrypt_mogg_bytes(data)
    if ogg_out_path:
        with open(ogg_out_path, "wb") as f:
            f.write(ogg)
    if mogg_out_path:
        info = read_mogg_header(data)
        header = struct.pack("<iIIII", 0x0A, 20 + 8 * info["entries"], info["map_version"],
                             info["buffer_size"], info["entries"]) + info["seek_table"]
        with open(mogg_out_path, "wb") as f:
            f.write(header)
            f.write(ogg)
    return ogg
