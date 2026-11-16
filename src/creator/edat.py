"""
Leitura e gravação de arquivos NPD/EDAT do PS3 (o `<s>.mid.edat` do Rock Band).

Formato (mesma lógica do make_npdata / EDAT.cpp do RPCS3):
- 0x00 cabeçalho NPD (0x80): magic "NPD\\0", versão, licença, tipo, content id (0x30),
  digest (0x10, usado como IV dos blocos), title hash (CMAC do content id + nome do
  arquivo), dev hash (CMAC do cabeçalho com a klicensee);
- 0x80 cabeçalho EDAT: flags, tamanho do bloco, tamanho do arquivo original, hash da
  seção de metadados (0x90), hash do cabeçalho (0xA0) e assinaturas ECDSA (zeradas);
- 0x100 metadados: um CMAC (0x10) por bloco; depois os blocos AES-128-CBC;
- rodapé de 0x10 bytes ("EDATA 2.4.0.W" na versão 2).

Modo usado pelos customs do Rock Band 3 (VERIFICADO contra os dois .mid.edat de
referência: title hash, dev hash, hash do cabeçalho, hash dos metadados, CMAC de cada
bloco e MIDI resultante válido): versão 2, licença 3 (livre), tipo 0, flags 0x0C,
blocos de 16 KiB, klicensee = MD5("Ih38rtW1ng3r" + <pasta em USRDIR> + "10025250")
(fórmula do Onyx / C3 CON Tools) e content id "UP8802-BLUS30463_00-<pasta>".
"""

import hashlib
import os
import struct
from typing import Iterable, List, Optional

from Crypto.Cipher import AES
from Crypto.Hash import CMAC

NPD_MAGIC = b"NPD\x00"
NPD_HEADER_SIZE = 0x80
EDAT_HEADER_END = 0x100

# Chaves públicas do formato NPD (key_vault do RPCS3 / make_npdata).
# Cada uma é conferida pelos hashes das referências (ver docstring do módulo).
NP_OMAC_KEY_2 = bytes.fromhex("6BA52976EFDA16EF3C339FB2971E256B")
NP_OMAC_KEY_3 = bytes.fromhex("9B515FEACF75064981AA604D91A54E97")
EDAT_KEY_0 = bytes.fromhex("BE959CA8308DEFA2E5E180C63712A9AE")
EDAT_IV = bytes(16)

# Digest fixo que o make_npdata grava (e que os blocos usam como IV)
FAKE_DIGEST = b"GoodLuckFromPSPx"
EDAT_FOOTER_V2 = b"EDATA 2.4.0.W\x00\x00\x00"

EDAT_COMPRESSED_FLAG = 0x00000001
EDAT_FLAG_0x02 = 0x00000002
EDAT_ENCRYPTED_KEY_FLAG = 0x00000008
EDAT_FLAG_0x10 = 0x00000010
EDAT_FLAG_0x20 = 0x00000020
SDAT_FLAG = 0x01000000
EDAT_DEBUG_DATA_FLAG = 0x80000000

RB3_FLAGS = 0x0C
RB3_BLOCK_SIZE = 0x4000
RB3_CONTENT_PREFIX = "UP8802-BLUS30463_00-"
_RB_KLIC_PREFIX = b"Ih38rtW1ng3r"
_RB_KLIC_SUFFIX = b"10025250"


class EdatError(ValueError):
    """Arquivo EDAT inválido, não suportado ou com klicensee errada."""


def rock_band_klic(folder: str) -> bytes:
    """Klicensee dos customs do Rock Band a partir da pasta em USRDIR/."""
    return hashlib.md5(_RB_KLIC_PREFIX + folder.encode("utf-8") + _RB_KLIC_SUFFIX).digest()


def rb3_content_id(folder: str) -> str:
    """Content id que os pacotes RB3 de referência usam no .mid.edat."""
    cid = RB3_CONTENT_PREFIX + folder
    if len(cid.encode("utf-8")) > 0x30:
        raise EdatError("Content id longo demais (máx. 48 bytes): %s" % cid)
    return cid


def _cmac(key: bytes, data: bytes) -> bytes:
    c = CMAC.new(key, ciphermod=AES)
    c.update(data)
    return c.digest()


def _aes_cbc_dec(key: bytes, iv: bytes, data: bytes) -> bytes:
    return AES.new(key, AES.MODE_CBC, iv).decrypt(data)


def _aes_ecb_enc(key: bytes, data: bytes) -> bytes:
    return AES.new(key, AES.MODE_ECB).encrypt(data)


def _xor(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


class NpdHeader:
    """Campos do cabeçalho NPD + EDAT (0x00-0x100)."""

    def __init__(self, data: bytes):
        if len(data) < EDAT_HEADER_END or data[:4] != NPD_MAGIC:
            raise EdatError("Não é um arquivo NPD/EDAT")
        self.raw = data[:EDAT_HEADER_END]
        self.version, self.license, self.type = struct.unpack(">III", data[4:16])
        self.content_id = data[0x10:0x40].split(b"\x00", 1)[0].decode("ascii", "replace")
        self.digest = data[0x40:0x50]
        self.title_hash = data[0x50:0x60]
        self.dev_hash = data[0x60:0x70]
        self.flags, self.block_size, self.file_size = struct.unpack(">IIQ", data[0x80:0x90])
        self.metadata_hash = data[0x90:0xA0]
        self.header_hash = data[0xA0:0xB0]

    @property
    def block_count(self) -> int:
        if self.block_size <= 0:
            return 0
        return (self.file_size + self.block_size - 1) // self.block_size

    def content_label(self) -> str:
        """Parte do content id depois de "XXYYYY-TITLEID_00-"."""
        return self.content_id[20:] if len(self.content_id) > 20 else ""


def title_hash_ok(header: NpdHeader, file_name: str) -> bool:
    data = header.raw[0x10:0x40] + file_name.encode("utf-8")
    return _cmac(NP_OMAC_KEY_3, data) == header.title_hash


def dev_hash_ok(header: NpdHeader, klic: bytes) -> bool:
    return _cmac(_xor(klic, NP_OMAC_KEY_2), header.raw[:0x60]) == header.dev_hash


def _hash_key(header: NpdHeader, klic: bytes) -> bytes:
    """Chave CMAC dos hashes do cabeçalho/metadados (modo 0x10000002 com flag 0x08)."""
    if header.flags & EDAT_ENCRYPTED_KEY_FLAG:
        return _aes_cbc_dec(EDAT_KEY_0, EDAT_IV, klic)
    return klic


def _check_supported(header: NpdHeader):
    if header.version not in (2, 3):
        raise EdatError("Versão NPD %d não suportada" % header.version)
    if header.flags & SDAT_FLAG:
        raise EdatError("SDAT não suportado")
    if header.flags & (EDAT_COMPRESSED_FLAG | EDAT_FLAG_0x02 | EDAT_FLAG_0x10 | EDAT_FLAG_0x20
                       | EDAT_DEBUG_DATA_FLAG):
        raise EdatError("Flags EDAT 0x%08X não suportadas (só 0x0C, como nos customs RB3)"
                        % header.flags)
    if (header.license & 0x3) != 0x3:
        raise EdatError("Licença %d exige RAP/RIF (só a licença livre 3 é suportada)" % header.license)
    if header.block_size <= 0 or header.block_size % 16:
        raise EdatError("Tamanho de bloco inválido: %d" % header.block_size)


def _block_key(header: NpdHeader, index: int) -> bytes:
    return header.dev_hash[:12] + struct.pack(">I", index)


def _block_keys(header: NpdHeader, klic: bytes, index: int):
    """(chave AES do bloco, chave CMAC do bloco); ambas passam por EDAT_KEY_0 (flag 0x08)."""
    key_result = _aes_ecb_enc(klic, _block_key(header, index))
    if header.flags & EDAT_ENCRYPTED_KEY_FLAG:
        key_result = _aes_cbc_dec(EDAT_KEY_0, EDAT_IV, key_result)
    return key_result, key_result


def _layout(header: NpdHeader):
    n = header.block_count
    meta_off = EDAT_HEADER_END
    data_off = meta_off + 0x10 * n
    return n, meta_off, data_off


def verify_edat(data: bytes, file_name: str, klic: bytes) -> List[str]:
    """Lista de problemas encontrados (vazia = todos os hashes conferem)."""
    problems = []
    try:
        header = NpdHeader(data)
        _check_supported(header)
    except EdatError as e:
        return [str(e)]
    if not title_hash_ok(header, file_name):
        problems.append("title hash não confere (nome do arquivo ou content id alterado)")
    if not dev_hash_ok(header, klic):
        problems.append("dev hash não confere (klicensee errada: a pasta em USRDIR mudou?)")
        return problems
    hkey = _hash_key(header, klic)
    if _cmac(hkey, data[:0xA0]) != header.header_hash:
        problems.append("hash do cabeçalho EDAT não confere")
    n, meta_off, data_off = _layout(header)
    meta = data[meta_off:meta_off + 0x10 * n]
    if len(meta) != 0x10 * n or _cmac(hkey, meta) != header.metadata_hash:
        problems.append("hash da seção de metadados não confere")
    return problems


def decrypt_edat(data: bytes, file_name: str, klic: bytes, verify: bool = True) -> bytes:
    """Decifra um EDAT (licença livre, flags 0x0C). Lança EdatError se algum hash falhar."""
    header = NpdHeader(data)
    _check_supported(header)
    if verify:
        problems = verify_edat(data, file_name, klic)
        if problems:
            raise EdatError("; ".join(problems))
    n, meta_off, data_off = _layout(header)
    out = bytearray()
    pos = data_off
    for i in range(n):
        length = header.block_size
        if i == n - 1 and header.file_size % header.block_size:
            length = header.file_size % header.block_size
        padded = (length + 0xF) & ~0xF
        enc = data[pos:pos + padded]
        if len(enc) != padded:
            raise EdatError("EDAT truncado no bloco %d" % i)
        aes_key, mac_key = _block_keys(header, klic, i)
        if verify and _cmac(mac_key, enc) != data[meta_off + 0x10 * i:meta_off + 0x10 * (i + 1)]:
            raise EdatError("CMAC do bloco %d não confere" % i)
        out += _aes_cbc_dec(aes_key, header.digest, enc)[:length]
        pos += padded
    return bytes(out)


def encrypt_edat(plain: bytes, file_name: str, content_id: str, klic: bytes,
                 block_size: int = RB3_BLOCK_SIZE) -> bytes:
    """Gera um EDAT versão 2, licença livre, flags 0x0C (igual às referências RB3)."""
    cid = content_id.encode("ascii")
    if len(cid) > 0x30:
        raise EdatError("Content id longo demais: %s" % content_id)
    npd = bytearray(NPD_HEADER_SIZE)
    npd[0:4] = NPD_MAGIC
    npd[4:16] = struct.pack(">III", 2, 3, 0)
    npd[0x10:0x40] = cid.ljust(0x30, b"\x00")
    npd[0x40:0x50] = FAKE_DIGEST
    npd[0x50:0x60] = _cmac(NP_OMAC_KEY_3, bytes(npd[0x10:0x40]) + file_name.encode("utf-8"))
    npd[0x60:0x70] = _cmac(_xor(klic, NP_OMAC_KEY_2), bytes(npd[:0x60]))

    head = bytearray(EDAT_HEADER_END)
    head[:NPD_HEADER_SIZE] = npd
    head[0x80:0x90] = struct.pack(">IIQ", RB3_FLAGS, block_size, len(plain))
    header = NpdHeader(bytes(head))

    n = header.block_count
    metas, blocks = [], []
    for i in range(n):
        chunk = plain[i * block_size:(i + 1) * block_size]
        chunk += b"\x00" * ((-len(chunk)) % 16)
        aes_key, mac_key = _block_keys(header, klic, i)
        enc = AES.new(aes_key, AES.MODE_CBC, FAKE_DIGEST).encrypt(chunk)
        blocks.append(enc)
        metas.append(_cmac(mac_key, enc))
    meta = b"".join(metas)

    hkey = _hash_key(header, klic)
    head[0x90:0xA0] = _cmac(hkey, meta)
    head[0xA0:0xB0] = _cmac(hkey, bytes(head[:0xA0]))
    # 0xB0-0x100: assinaturas ECDSA, zeradas como nas referências
    return bytes(head) + meta + b"".join(blocks) + EDAT_FOOTER_V2


def usrdir_folder(path: str) -> Optional[str]:
    """Nome da pasta logo abaixo de USRDIR/ no caminho do arquivo (None se não houver)."""
    parts = os.path.normpath(os.path.abspath(path)).split(os.sep)
    upper = [p.upper() for p in parts]
    if "USRDIR" in upper:
        i = len(upper) - 1 - upper[::-1].index("USRDIR")
        if i + 1 < len(parts) - 1:
            return parts[i + 1]
    return None


def klic_candidates(path: str, header: Optional[NpdHeader] = None) -> List[str]:
    """Nomes de pasta que podem ter gerado a klicensee: a de USRDIR/<pasta>/ primeiro,
    o rótulo do content id e as demais pastas acima do arquivo."""
    names: List[str] = []
    parts = os.path.normpath(os.path.abspath(path)).split(os.sep)
    folder = usrdir_folder(path)
    if folder:
        names.append(folder)
    if header is not None and header.content_label():
        names.append(header.content_label())
    names.extend(reversed(parts[:-1]))
    seen, out = set(), []
    for n in names:
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def find_rock_band_klic(data: bytes, path: str, extra_folders: Iterable[str] = (),
                        installed: bool = False) -> Optional[bytes]:
    """Klicensee cujo dev hash confere com o arquivo (None se nenhuma servir).

    Com `installed=True` e o arquivo dentro de USRDIR/<pasta>/, só vale a chave dessa
    pasta: é a que o jogo usa, então renomear a pasta quebra o .mid.edat."""
    header = NpdHeader(data)
    folder = usrdir_folder(path) if installed else None
    names = [folder] if folder else list(extra_folders) + klic_candidates(path, header)
    for name in names:
        klic = rock_band_klic(name)
        if dev_hash_ok(header, klic):
            return klic
    return None


def read_rock_band_mid_edat(path: str, extra_folders: Iterable[str] = (),
                            installed: bool = False) -> bytes:
    """Decifra o <s>.mid.edat de um custom de Rock Band e devolve os bytes do MIDI.
    `installed`: exige a chave da pasta em USRDIR/ (ver find_rock_band_klic)."""
    with open(path, "rb") as f:
        data = f.read()
    klic = find_rock_band_klic(data, path, extra_folders, installed=installed)
    if klic is None:
        raise EdatError("Nenhuma klicensee confere com %s (pasta USRDIR renomeada?)"
                        % os.path.basename(path))
    plain = decrypt_edat(data, os.path.basename(path), klic)
    if not plain.startswith(b"MThd"):
        raise EdatError("O conteúdo decifrado não é um MIDI")
    return plain


def write_rock_band_mid_edat(midi_bytes: bytes, dest_path: str, folder: str):
    """Grava <s>.mid.edat para a pasta USRDIR/<folder> (klic e content id do RB3)."""
    data = encrypt_edat(midi_bytes, os.path.basename(dest_path), rb3_content_id(folder),
                        rock_band_klic(folder))
    with open(dest_path, "wb") as f:
        f.write(data)
