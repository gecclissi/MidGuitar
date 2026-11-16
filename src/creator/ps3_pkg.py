"""
Leitura e criação de pacotes .pkg de DEBUG do PS3 (revisão 0x0000), o formato dos
pacotes de customs do Rock Band (instaláveis no RPCS3 em File > Install Packages e no
PS3 com HEN/CFW pelo Package Manager).

Layout (conferido byte a byte nas duas referências):
- 0x00 cabeçalho (0x80): magic 7F"PKG", revisão 0, tipo 1 (PS3), offset/quantidade/tamanho
  dos metadados, quantidade de itens, tamanho total, offset/tamanho dos dados, content
  id (0x30), QA digest (0x10, chave do keystream) e klicensee derivada do QA digest;
- 0x80 digests (0x40): SHA-1 do cabeçalho + preenchimento cifrado;
- 0xC0 metadados (id, tamanho, valor): DRM 3 (livre), tipo de conteúdo 5, tipo de pacote 0xE,
  tamanho dos dados e revisão do make_package_npdrm (0x1061);
- 0x100 digests dos metadados (0x40); 0x140 dados cifrados com keystream SHA-1:
  tabela de itens (0x20 cada), nomes (alinhados em 16) e arquivos (alinhados em 16);
- 0x60 bytes zerados no fim.
"""

import hashlib
import os
import struct
from typing import Callable, Dict, List, Optional, Tuple

PKG_MAGIC = b"\x7fPKG"
PKG_HEADER_SIZE = 0x80
PKG_TRAILER = 0x60

ITEM_FILE_NO_OVERWRITE = 0x00000003
ITEM_EDAT = 0x80000002
ITEM_FILE = 0x80000003
ITEM_DIR = 0x80000004
# Arquivos de metadados do jogo: não sobrescrevem os do jogo já instalado
_ROOT_KEEP = {"PARAM.SFO", "ICON0.PNG", "PIC1.PNG"}

# Metadados iguais aos das referências
_META_DRM_FREE = 3
_META_CONTENT_TYPE = 5
_META_PACKAGE_TYPE = 0x0E
_META_REVISION = b"\x10\x61\x00\x00"

_BLOCK = 16
_INDEX_FOR_KLIC = 0xFFFFFFFFFFFFFFFF


class PkgError(ValueError):
    """Pacote inválido ou não suportado."""


def _key_prefix(key_source: bytes) -> bytes:
    """Os 0x38 bytes que precedem o índice do bloco no SHA-1 do keystream."""
    return key_source[0:8] + key_source[0:8] + key_source[8:16] + key_source[8:16] + bytes(0x18)


def keystream_xor(data: bytes, key_source: bytes, start_offset: int = 0) -> bytes:
    """Cifra/decifra `data` que começa em `start_offset` (bytes) da área de dados."""
    if not data:
        return b""
    prefix = _key_prefix(key_source)
    first = start_offset // _BLOCK
    skip = start_offset % _BLOCK
    count = (skip + len(data) + _BLOCK - 1) // _BLOCK
    sha1 = hashlib.sha1
    pack = struct.Struct(">Q").pack
    stream = b"".join(sha1(prefix + pack((first + i) & 0xFFFFFFFFFFFFFFFF)).digest()[:16]
                      for i in range(count))
    stream = stream[skip:skip + len(data)]
    n = len(data)
    return (int.from_bytes(data, "big") ^ int.from_bytes(stream, "big")).to_bytes(n, "big")


def _sha1_16(data: bytes) -> bytes:
    return hashlib.sha1(data).digest()[3:19]


def _digests(header: bytes, metadata: bytes) -> Tuple[bytes, bytes]:
    """(digest após o cabeçalho, digest após os metadados), como nas referências."""
    head_sha = _sha1_16(header)
    meta_sha = _sha1_16(metadata)
    pad = keystream_xor(bytes(0x30), meta_sha)
    return head_sha + keystream_xor(pad, head_sha), meta_sha + pad


class PkgItem:
    def __init__(self, name: str, flags: int, offset: int, size: int):
        self.name = name
        self.flags = flags
        self.offset = offset
        self.size = size

    @property
    def is_dir(self) -> bool:
        return (self.flags & 0xFF) == 4

    def __repr__(self):
        return "PkgItem(%r, 0x%08X, %d)" % (self.name, self.flags, self.size)


def _read_exact(f, size: int) -> bytes:
    """Lê exatamente `size` bytes; arquivo cortado vira PkgError (nunca dado incompleto)."""
    if size < 0:
        raise PkgError("Tamanho inválido no .pkg")
    data = f.read(size)
    if len(data) != size:
        raise PkgError("Arquivo .pkg truncado")
    return data


class PkgInfo:
    """Cabeçalho, metadados e itens de um .pkg de debug."""

    def __init__(self, path: str):
        self.path = path
        with open(path, "rb") as f:
            self.header = f.read(PKG_HEADER_SIZE)
            if len(self.header) < PKG_HEADER_SIZE or self.header[:4] != PKG_MAGIC:
                raise PkgError("Não é um arquivo .pkg do PS3")
            (self.revision, self.pkg_type, self.metadata_offset, self.metadata_count,
             self.metadata_size, self.item_count, self.total_size, self.data_offset,
             self.data_size) = struct.unpack(">HHIIIIQQQ", self.header[4:0x30])
            if self.revision & 0x8000:
                raise PkgError("PKG retail (finalizado) ainda não é suportado; só PKG de debug")
            if self.pkg_type != 1:
                raise PkgError("PKG não é de PS3 (tipo %d)" % self.pkg_type)
            self.content_id = self.header[0x30:0x60].split(b"\x00", 1)[0].decode("ascii", "replace")
            self.qa_digest = self.header[0x60:0x70]
            self.klicensee = self.header[0x70:0x80]
            file_size = os.fstat(f.fileno()).st_size
            if self.metadata_size < 0x40 or self.metadata_offset + self.metadata_size > file_size:
                raise PkgError("Metadados do .pkg inválidos ou truncados")
            if self.data_offset + self.item_count * 0x20 > file_size:
                raise PkgError("Tabela de itens do .pkg truncada")
            self.digest1 = _read_exact(f, 0x40)
            f.seek(self.metadata_offset)
            meta_raw = _read_exact(f, self.metadata_size - 0x40)
            self.metadata_raw = meta_raw
            self.digest2 = _read_exact(f, 0x40)
            self.metadata: Dict[int, bytes] = {}
            pos = 0
            for _ in range(self.metadata_count):
                if pos + 8 > len(meta_raw):
                    raise PkgError("Metadados do .pkg truncados")
                mid, ln = struct.unpack(">II", meta_raw[pos:pos + 8])
                if pos + 8 + ln > len(meta_raw):
                    raise PkgError("Metadados do .pkg truncados")
                self.metadata[mid] = meta_raw[pos + 8:pos + 8 + ln]
                pos += 8 + ln
            self.items: List[PkgItem] = []
            table = self.read_data(f, 0, self.item_count * 0x20)
            for i in range(self.item_count):
                name_off, name_size, d_off, d_size, flags, _pad = struct.unpack(
                    ">IIQQII", table[i * 0x20:(i + 1) * 0x20])
                if name_size > 0x1000:
                    raise PkgError("Nome de item do .pkg inválido")
                name = self.read_data(f, name_off, name_size).decode("utf-8", "replace")
                self.items.append(PkgItem(name, flags, d_off, d_size))

    def read_data(self, f, offset: int, size: int) -> bytes:
        f.seek(self.data_offset + offset)
        return keystream_xor(_read_exact(f, size), self.qa_digest, offset)

    def digests_ok(self) -> bool:
        d1, d2 = _digests(self.header, self.metadata_raw)
        return d1 == self.digest1 and d2 == self.digest2

    def klicensee_ok(self) -> bool:
        expected = keystream_xor(bytes(16), self.qa_digest, _INDEX_FOR_KLIC * _BLOCK)
        return self.klicensee == expected


def read_pkg(path: str) -> PkgInfo:
    return PkgInfo(path)


def _safe_dest(out_dir: str, name: str) -> Optional[str]:
    root = os.path.normpath(os.path.abspath(out_dir))
    dest = os.path.normpath(os.path.join(root, name.replace("\\", "/")))
    if dest != root and not dest.startswith(root + os.sep):
        return None   # caminho suspeito (../ ou absoluto)
    return dest


def extract_pkg(path: str, out_dir: str,
                want: Optional[Callable[[str], bool]] = None) -> List[str]:
    """Extrai um .pkg de debug para `out_dir`. `want(nome)` filtra os arquivos.
    Devolve os caminhos dos arquivos gravados."""
    info = PkgInfo(path)
    written = []
    chunk = 1 << 20
    with open(path, "rb") as f:
        for item in info.items:
            dest = _safe_dest(out_dir, item.name)
            if dest is None:
                continue
            if item.is_dir:
                os.makedirs(dest, exist_ok=True)
                continue
            if want is not None and not want(item.name):
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            tmp = dest + ".tmp"
            try:
                with open(tmp, "wb") as o:
                    done = 0
                    while done < item.size:
                        n = min(chunk, item.size - done)
                        o.write(info.read_data(f, item.offset + done, n))
                        done += n
                os.replace(tmp, dest)
            except BaseException:
                _remove_quietly(tmp)
                raise
            written.append(dest)
    return written


def _collect(src_dir: str, include: Optional[List[str]] = None) -> List[Tuple[str, Optional[str], int]]:
    """(nome no pacote, caminho local ou None para pasta, flags) na ordem das referências:
    arquivos da pasta (ordem alfabética) e depois as subpastas. `include` limita os
    itens da raiz (ex.: PARAM.SFO, ICON0.PNG, USRDIR)."""
    out: List[Tuple[str, Optional[str], int]] = []

    def walk(rel: str, local: str):
        entries = sorted(os.listdir(local))
        if not rel and include is not None:
            wanted = {n.upper() for n in include}
            entries = [e for e in entries if e.upper() in wanted]
        files = [e for e in entries if os.path.isfile(os.path.join(local, e))]
        dirs = [e for e in entries if os.path.isdir(os.path.join(local, e))]
        for name in files:
            full = os.path.join(local, name)
            pkg_name = rel + "/" + name if rel else name
            if not rel and name.upper() in _ROOT_KEEP:
                flags = ITEM_FILE_NO_OVERWRITE
            else:
                with open(full, "rb") as fh:
                    magic = fh.read(4)
                flags = ITEM_EDAT if name.lower().endswith(".edat") and magic == b"NPD\x00" else ITEM_FILE
            out.append((pkg_name, full, flags))
        for name in dirs:
            pkg_name = rel + "/" + name if rel else name
            out.append((pkg_name, None, ITEM_DIR))
            walk(pkg_name, os.path.join(local, name))

    walk("", src_dir)
    return out


def _pad16(n: int) -> int:
    return (n + 0xF) & ~0xF


def build_pkg(src_dir: str, pkg_path: str, content_id: str,
              include: Optional[List[str]] = None) -> str:
    """Cria um .pkg de debug com o conteúdo de `src_dir` (PARAM.SFO, ICON0.PNG, USRDIR/...).
    `include` restringe os itens da raiz que entram no pacote."""
    cid = content_id.encode("ascii")
    if len(cid) >= 0x30:
        raise PkgError("Content id longo demais: %s" % content_id)
    entries = _collect(src_dir, include)
    if not entries:
        raise PkgError("Pasta vazia: %s" % src_dir)

    # Nomes (alinhados em 16) logo após a tabela; depois os arquivos (alinhados em 16)
    table_size = 0x20 * len(entries)
    names = bytearray()
    name_pos = []
    for name, _local, _flags in entries:
        raw = name.encode("utf-8")
        name_pos.append((table_size + len(names), len(raw)))
        names += raw + bytes((-len(raw)) % 16)
    data_start = table_size + len(names)
    records = bytearray()
    sizes = []
    pos = data_start
    for (name, local, flags), (n_off, n_len) in zip(entries, name_pos):
        size = os.path.getsize(local) if local else 0
        sizes.append(size)
        records += struct.pack(">IIQQII", n_off, n_len, pos, size, flags, 0)
        pos += _pad16(size)
    data_size = pos
    index = bytes(records) + bytes(names)

    metadata = b"".join([
        struct.pack(">II", 1, 4) + struct.pack(">I", _META_DRM_FREE),
        struct.pack(">II", 2, 4) + struct.pack(">I", _META_CONTENT_TYPE),
        struct.pack(">II", 3, 4) + struct.pack(">I", _META_PACKAGE_TYPE),
        struct.pack(">II", 4, 8) + struct.pack(">Q", data_size),
        struct.pack(">II", 5, 4) + _META_REVISION,
    ])
    metadata_offset = PKG_HEADER_SIZE + 0x40
    metadata_size = len(metadata) + 0x40
    data_offset = metadata_offset + metadata_size

    def header_bytes(content: bytes, qa: bytes, klic: bytes) -> bytes:
        return (PKG_MAGIC + struct.pack(">HHIIIIQQQ", 0, 1, metadata_offset, 5, metadata_size,
                                        len(entries), data_offset + data_size + PKG_TRAILER,
                                        data_offset, data_size)
                + content.ljust(0x30, b"\x00") + qa + klic)

    # QA digest: SHA-1 dos arquivos + cabeçalho provisório + índice (como o Onyx)
    sha = hashlib.sha1()
    for (_name, local, _flags) in entries:
        if local:
            with open(local, "rb") as fh:
                for block in iter(lambda: fh.read(1 << 20), b""):
                    sha.update(block)
    sha.update(header_bytes(b"", bytes(16), bytes(16)))
    sha.update(index)
    qa = sha.digest()[:16]
    klic = keystream_xor(bytes(16), qa, _INDEX_FOR_KLIC * _BLOCK)
    header = header_bytes(cid, qa, klic)
    digest1, digest2 = _digests(header, metadata)

    tmp = pkg_path + ".tmp"
    try:
        _write_pkg_body(tmp, header, digest1, metadata, digest2, index, qa, entries, sizes, records)
        os.replace(tmp, pkg_path)
    except BaseException:
        _remove_quietly(tmp)
        raise
    return pkg_path


def _remove_quietly(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


def _write_pkg_body(tmp, header, digest1, metadata, digest2, index, qa, entries, sizes, records):
    with open(tmp, "wb") as out:
        out.write(header + digest1 + metadata + digest2)
        out.write(keystream_xor(index, qa, 0))
        for (name, local, _flags), size, rec in zip(entries, sizes, range(len(entries))):
            if not local:
                continue
            off = struct.unpack(">Q", records[rec * 0x20 + 8:rec * 0x20 + 16])[0]
            done = 0
            with open(local, "rb") as fh:
                while True:
                    block = fh.read(1 << 20)
                    if not block:
                        break
                    out.write(keystream_xor(block, qa, off + done))
                    done += len(block)
            if done != size:
                raise PkgError("Arquivo mudou de tamanho durante o empacotamento: %s" % name)
            pad = (-size) % 16
            if pad:
                out.write(keystream_xor(bytes(pad), qa, off + done))
        out.write(bytes(PKG_TRAILER))
