"""
Leitura e criação de pacotes STFS do Xbox 360 (CON / LIVE / PIRS), o formato das DLCs e
dos customs do Rock Band 3 no Xbox (RGH/JTAG e Xenia).

Portado do Onyx (mtolly/onyx, Onyx/Xbox/STFS.hs) e conferido com uma CON real
(Joe Dassin - Salut les amoureux_rb3con, gerada pelo C3 CON Tools):

- 0x000 magic "CON " + certificado do console (0x1A8) + assinatura RSA (0x80, invertida);
  LIVE/PIRS: assinatura de 0x100 + 0x128 zeros;
- 0x22C metadados: 16 licenças, SHA-1 do cabeçalho (0x344 até 0xB000), tamanho do
  cabeçalho (0xAD0E), tipo de conteúdo, versão dos metadados, tamanho do conteúdo,
  title id (0x45410914 = Rock Band 3), descritor do volume STFS, nomes/descrições em
  9 idiomas (UTF-16BE), publicador, nome do jogo, flags e as duas miniaturas PNG;
- 0xB000 em diante: blocos de 0x1000 bytes, intercalando tabelas de hash (nível 0 a cada
  0xAA blocos de dados, nível 1 a cada 0xAA tabelas de nível 0, nível 2...) e dados.
  Cada registro de hash (0x18 bytes) tem o SHA-1 do bloco, o estado (0x80 = usado) e o
  próximo bloco da cadeia (24 bits big-endian, 0xFFFFFF no último);
- tabela de arquivos (0x40 bytes por entrada) nos primeiros blocos de dados.

Assinatura CON: PKCS#1 v1.5 com SHA-1 dos 0x118 bytes em 0x22C (licenças, hash do
cabeçalho e tamanho), com a chave do KV.bin que o Onyx distribui (a mesma do C3 CON
Tools/X360): a CON de referência foi assinada com exatamente essa chave (o certificado
é idêntico e a assinatura dela confere com a chave pública).
"""

import hashlib
import os
import struct
from typing import Callable, Dict, Iterator, List, Optional, Tuple

BLOCK = 0x1000
HASHES_PER_TABLE = 0xAA
_HASH_RECORD = 0x18
_ENTRY_SIZE = 0x40

RB3_TITLE_ID = 0x45410914
RB2_TITLE_ID = 0x45410869
CONTENT_SAVED_GAME = 0x1           # o que o Onyx/C3 gravam em pacotes CON
CONTENT_MARKETPLACE = 0x2          # DLC oficial (pacotes LIVE)
_HEADER_SIZE_CON = 0xAD0E
_DATA_START = 0xC000               # bloco "real" 0 (o -1 é a primeira tabela de hash)

STATUS_UNUSED = 0x00
STATUS_FREE = 0x40
STATUS_USED = 0x80
STATUS_NEW = 0xC0

# Data/hora FAT usada pelo Onyx nas entradas (vinda de DLC do GH:WoR)
_FAT_TIMESTAMP = 0x20006F2D

# Certificado do console do KV.bin do Onyx (offset 0x9B8, 0x1A8 bytes): tamanho,
# console id 09 12 BA 26 E3, peça X803395-001, varejo, data 09-18-06, expoente,
# módulo (em blocos de 8 bytes invertidos) e a assinatura do certificado.
# Idêntico ao da CON de referência.
_KV_CERTIFICATE = bytes.fromhex(
    "01a80912ba26e3583830333339352d3030310000000000000000000230392d31"
    "382d303600010001c32f8c9192306fdbd956c8c3c3209d6437de51e8d71ce156"
    "f7749d6f17837eb59be5a3c02790c29723ef256d00917724cbc5d630f406ed24"
    "5e2353141888cb6f384eaf070c61ab51e7befa3f9e156f6ce062fd7c54559ee0"
    "5cae86ef927b90d1d1f84cef534cd54e86589b172b1005b89021fad10c64192b"
    "a31d6ce5fa95fde8f9700d2a89399ed54e658744f94f2090894137502ef83008"
    "cc6ecdd157e7c3b796b02a8059cb7e43fbdb7e0cef6c5e000b1e87e10264a708"
    "2432b9531500e9e3530c15e15d59c609abd173b5eec5e750bcc2b22598baa00a"
    "84f4f82d1ad2c97fdccf5d02219a25e069116cfc88060149f474408dd891db83"
    "c960ce0d7f97aa2a36a5f00c1063e9a9394fbb476c4422f1be3a4901ed5b4700"
    "4321bdfbb2959a5fb446f4a712244b0b7fb88ebb528322581e06b7ad7a3a167e"
    "c8d737819e8af2c4660888fea70e8f9d875f0e7b489a0662f72425cdb04f7368"
    "970ce4ade8559ab4fa65b5a358fe814054aa1f002af1dd8a1f454e9dff82465a"
    "5a9025a0580ff227"
)
# Primos da chave privada do mesmo KV.bin (offsets 0x318 e 0x358, desembaralhados)
_KV_P = bytes.fromhex(
    "cce75dfe72b6fde71de31a0eac337ab921e88a849bda9f1e5834687ab11d7e1c"
    "1852657b978ea76a9dee5a77523b718f33d0495ec330397236bf1dd9f224e871"
)
_KV_Q = bytes.fromhex(
    "cbca5874d403629306501f42f6aa5936a7a1f3975c9ac86a27cf85052a66416a"
    "7f2f84c81813c61d8dc7322f72193fa4ed71e761c0cf61ae8ba068a77d83230b"
)


class StfsError(ValueError):
    """Pacote STFS inválido ou não suportado."""


def is_stfs_file(path: str) -> bool:
    """Arquivo que começa com "CON ", "LIVE" ou "PIRS"."""
    try:
        if not os.path.isfile(path):
            return False
        with open(path, "rb") as f:
            return f.read(4) in (b"CON ", b"LIVE", b"PIRS")
    except OSError:
        return False


def _stock_scramble(b: bytes) -> bytes:
    """Inverte a ordem dos blocos de 8 bytes (formato dos números no KV/certificado)."""
    n = len(b) // 8
    return b"".join(b[(n - 1 - i) * 8:(n - i) * 8] for i in range(n))


def _kv_public() -> Tuple[int, int]:
    e = int.from_bytes(_KV_CERTIFICATE[0x24:0x28], "big")
    n = int.from_bytes(_stock_scramble(_KV_CERTIFICATE[0x28:0xA8]), "big")
    return n, e


def _kv_rsa_key():
    from Crypto.PublicKey import RSA
    n, e = _kv_public()
    p = int.from_bytes(_KV_P, "big")
    q = int.from_bytes(_KV_Q, "big")
    if p * q != n:
        raise StfsError("Chave do KV inconsistente")
    d = pow(e, -1, (p - 1) * (q - 1))
    return RSA.construct((n, e, d, p, q))


def con_signature(signed: bytes) -> bytes:
    """Assinatura CON (0x80 bytes, já invertida) dos 0x118 bytes em 0x22C."""
    from Crypto.Hash import SHA1
    from Crypto.Signature import pkcs1_15
    sig = pkcs1_15.new(_kv_rsa_key()).sign(SHA1.new(signed))
    return sig[::-1]


def _rsa_verify(cert: bytes, signed: bytes, signature: bytes) -> bool:
    """Confere a assinatura CON com a chave pública do certificado do próprio pacote."""
    from Crypto.Hash import SHA1
    from Crypto.PublicKey import RSA
    from Crypto.Signature import pkcs1_15
    try:
        e = int.from_bytes(cert[0x24:0x28], "big")
        n = int.from_bytes(_stock_scramble(cert[0x28:0xA8]), "big")
        pkcs1_15.new(RSA.construct((n, e))).verify(SHA1.new(signed), signature[::-1])
        return True
    except (ValueError, TypeError):
        return False


def _int24le(b: bytes) -> int:
    return b[0] | (b[1] << 8) | (b[2] << 16)


def _p24le(v: int) -> bytes:
    return bytes((v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF))


def _int24be(b: bytes) -> int:
    return (b[0] << 16) | (b[1] << 8) | b[2]


def _utf16(raw: bytes) -> str:
    text = raw.decode("utf-16-be", errors="replace")
    return text.split("\x00", 1)[0]


def _utf16_field(text: str, size: int) -> bytes:
    """Texto UTF-16BE cortado/preenchido com zeros em `size` bytes (como o Onyx)."""
    raw = (text or "").encode("utf-16-be")[:size]
    return raw.ljust(size, b"\x00")


# ---------------------------------------------------------------------------
# Posição dos blocos (fórmulas do Onyx/X360)


def _table_shift(header_size: int) -> int:
    return 0 if ((header_size + 0xFFF) & 0xF000) >> 12 == 0xB else 1


def _fix_block_number(blk: int, shift: int) -> int:
    """Bloco de dados -> bloco "real" (pulando as tabelas de hash)."""
    real = blk
    if blk >= 0xAA:
        real += ((blk // 0xAA) + 1) << shift
    if blk >= 0x70E4:
        real += ((blk // 0x70E4) + 1) << shift
    return real


def _hash_table_real(blk: int, shift: int, table_offset: int) -> int:
    """Bloco real da tabela de nível 0 que guarda o hash do bloco de dados `blk`."""
    num = (blk // 0xAA) * (0xAB if shift == 0 else 0xAC)
    if blk >= 0xAA:
        num += ((blk // 0x70E4) + 1) << shift
    if blk >= 0x70E4:
        num += 1 << shift
    return num + table_offset - (1 << shift)


def _real_offset(real: int) -> int:
    return _DATA_START + real * BLOCK


def _block_pattern(data_blocks: int) -> Iterator[Tuple[str, int]]:
    """Sequência ("L0"/"D"/"L1"/"L2", índice) dos blocos reais a partir do -1 (Shift0),
    até cobrir `data_blocks` blocos de dados (port de blockContentsPattern)."""
    counters = {"L0": 0, "D": 0, "L1": 0, "L2": 0}

    def emit(kind):
        i = counters[kind]
        counters[kind] += 1
        return kind, i

    def l0():
        yield emit("L0")
        for _ in range(0xAA):
            yield emit("D")

    def l1(first: bool):
        if first:
            yield from l0()
            yield emit("L1")
            reps = 0xA9
        else:
            yield emit("L1")
            reps = 0xAA
        for _ in range(reps):
            yield from l0()

    def l2():
        yield from l1(True)
        yield emit("L2")
        for _ in range(0xA9):
            yield from l1(False)

    for item in l2():
        if item[0] == "D" and item[1] >= data_blocks:
            return
        yield item


def _layout(data_blocks: int) -> Dict[str, List[int]]:
    """Blocos reais de cada tabela/dado (Shift0) para `data_blocks` blocos de dados."""
    out: Dict[str, List[int]] = {"L0": [], "D": [], "L1": [], "L2": []}
    for real, (kind, _i) in enumerate(_block_pattern(data_blocks), start=-1):
        out[kind].append(real)
    # tabelas criadas sem nenhum bloco abaixo (o padrão termina antes) não existem
    need_l0 = (data_blocks + 0xA9) // 0xAA
    need_l1 = (need_l0 + 0xA9) // 0xAA if data_blocks >= 0xAA else 0
    need_l2 = 1 if data_blocks >= 0xAA * 0xAA else 0
    out["L0"] = out["L0"][:max(1, need_l0)]
    out["L1"] = out["L1"][:need_l1]
    out["L2"] = out["L2"][:need_l2]
    return out


# ---------------------------------------------------------------------------
# Leitura


class StfsEntry:
    """Entrada da tabela de arquivos."""

    def __init__(self, index: int, raw: bytes):
        flags = raw[0x28]
        self.index = index
        self.name = raw[:flags & 0x3F].decode("latin-1")
        self.consecutive = bool(flags & 0x40)
        self.is_dir = bool(flags & 0x80)
        self.blocks = _int24le(raw[0x29:0x2C])
        self.blocks2 = _int24le(raw[0x2C:0x2F])
        self.first_block = _int24le(raw[0x2F:0x32])
        self.path_index = struct.unpack(">h", raw[0x32:0x34])[0]
        self.size = struct.unpack(">I", raw[0x34:0x38])[0]
        self.update_time, self.access_time = struct.unpack("<II", raw[0x38:0x40])
        self.path = self.name

    def __repr__(self):
        return "StfsEntry(%r, %s, %d bytes)" % (self.path, "dir" if self.is_dir else "file", self.size)


class StfsPackage:
    """Cabeçalho, metadados e tabela de arquivos de um pacote STFS."""

    def __init__(self, path: str):
        self.path = path
        with open(path, "rb") as f:
            head = f.read(0x971A)
        if len(head) < 0x971A:
            raise StfsError("Arquivo curto demais para um pacote STFS")
        magic = head[:4]
        if magic not in (b"CON ", b"LIVE", b"PIRS"):
            raise StfsError("Não é um pacote CON/LIVE do Xbox 360")
        self.magic = magic.decode("ascii").strip()
        self.head = head
        if self.magic == "CON":
            self.certificate = head[4:0x1AC]
            self.console_id = head[6:0xB]
            self.console_part_number = head[0xB:0x1F].split(b"\x00", 1)[0].decode("ascii", "replace")
            self.console_type = head[0x1F]          # 1 = devkit, 2 = varejo
            self.cert_date = head[0x20:0x28].decode("ascii", "replace")
            self.signature = head[0x1AC:0x22C]
        else:
            self.certificate = b""
            self.console_id = b""
            self.console_part_number = ""
            self.console_type = 0
            self.cert_date = ""
            self.signature = head[4:0x104]
        self.licenses = [struct.unpack(">qii", head[0x22C + i * 16:0x23C + i * 16]) for i in range(16)]
        self.header_sha1 = head[0x32C:0x340]
        (self.header_size, self.content_type, self.metadata_version, self.content_size,
         self.media_id, self.version, self.base_version, self.title_id) = struct.unpack(
            ">IIIqIiiI", head[0x340:0x364])
        self.platform, self.executable_type, self.disc_number, self.disc_in_set = head[0x364:0x368]
        self.save_game_id = struct.unpack(">I", head[0x368:0x36C])[0]
        self.profile_id = head[0x371:0x379]
        d = head[0x379:0x379 + 0x24]
        self.descriptor_size = d[0]
        self.block_separation = d[2]
        self.file_table_blocks = struct.unpack("<h", d[3:5])[0]
        self.file_table_first = _int24le(d[5:8])
        self.top_hash = d[8:0x1C]
        self.allocated_blocks, self.unallocated_blocks = struct.unpack(">ii", d[0x1C:0x24])
        self.descriptor_type = struct.unpack(">I", head[0x3A9:0x3AD])[0]
        if self.descriptor_type != 0:
            raise StfsError("Pacote SVOD não é suportado (só STFS)")
        self.display_names = [_utf16(head[0x411 + i * 0x100:0x511 + i * 0x100]) for i in range(9)]
        self.descriptions = [_utf16(head[0xD11 + i * 0x100:0xE11 + i * 0x100]) for i in range(9)]
        self.publisher = _utf16(head[0x1611:0x1691])
        self.title_name = _utf16(head[0x1691:0x1711])
        self.transfer_flags = head[0x1711]
        thumb_size, title_thumb_size = struct.unpack(">ii", head[0x1712:0x171A])
        self.thumbnail = head[0x171A:0x171A + max(0, min(thumb_size, 0x4000))]
        self.title_thumbnail = head[0x571A:0x571A + max(0, min(title_thumb_size, 0x4000))]
        self.shift = _table_shift(self.header_size)
        self.entries: List[StfsEntry] = []
        with open(path, "rb") as f:
            self._read_entries(f)

    # -- blocos
    @property
    def display_name(self) -> str:
        return self.display_names[0]

    @property
    def description(self) -> str:
        return self.descriptions[0]

    def _read_real(self, f, real: int) -> bytes:
        f.seek(_real_offset(real))
        return f.read(BLOCK)

    def _hash_record(self, f, blk: int) -> Tuple[bytes, int, int]:
        def read(table_offset):
            real = _hash_table_real(blk, self.shift, table_offset)
            f.seek(_real_offset(real) + (blk % 0xAA) * _HASH_RECORD)
            rec = f.read(_HASH_RECORD).ljust(_HASH_RECORD, b"\x00")
            return rec[:20], rec[20], _int24be(rec[21:24])
        rec = read(0)
        if self.shift == 1 and rec[1] < STATUS_USED:
            rec = read(1)
        return rec

    def _read_data_block(self, f, blk: int) -> bytes:
        return self._read_real(f, _fix_block_number(blk, self.shift))

    def _read_entries(self, f):
        raw = bytearray()
        blk = self.file_table_first
        for _ in range(max(0, self.file_table_blocks)):
            raw += self._read_data_block(f, blk).ljust(BLOCK, b"\x00")
            blk = self._hash_record(f, blk)[2]
        for i in range(len(raw) // _ENTRY_SIZE):
            chunk = bytes(raw[i * _ENTRY_SIZE:(i + 1) * _ENTRY_SIZE])
            if not chunk[0x28] & 0x3F:
                break
            self.entries.append(StfsEntry(i, chunk))
        by_index = {e.index: e for e in self.entries}
        for e in self.entries:
            parts = [e.name]
            seen = set()
            p = e.path_index
            while p != -1 and p in by_index and p not in seen:
                seen.add(p)
                parts.append(by_index[p].name)
                p = by_index[p].path_index
            e.path = "/".join(reversed(parts))

    def files(self) -> List[StfsEntry]:
        return [e for e in self.entries if not e.is_dir]

    def find(self, path: str) -> Optional[StfsEntry]:
        low = path.replace("\\", "/").lower()
        for e in self.entries:
            if e.path.lower() == low:
                return e
        return None

    def _file_blocks(self, f, entry: StfsEntry) -> List[int]:
        count = (entry.size + BLOCK - 1) // BLOCK
        if entry.consecutive:
            return list(range(entry.first_block, entry.first_block + count))
        blocks = []
        blk = entry.first_block
        status = STATUS_USED
        left = entry.size
        while left > 0 and 0 <= blk < self.allocated_blocks and status >= STATUS_USED:
            blocks.append(blk)
            _sha, status, nxt = self._hash_record(f, blk)
            left -= BLOCK
            blk = nxt
        return blocks

    def iter_file(self, entry: StfsEntry, f=None) -> Iterator[bytes]:
        own = f is None
        if own:
            f = open(self.path, "rb")
        try:
            left = entry.size
            for blk in self._file_blocks(f, entry):
                if left <= 0:
                    break
                data = self._read_data_block(f, blk)[:min(BLOCK, left)]
                left -= len(data)
                yield data
            if left > 0:
                raise StfsError("Arquivo %s truncado no pacote" % entry.path)
        finally:
            if own:
                f.close()

    def read_file(self, entry) -> bytes:
        if isinstance(entry, str):
            found = self.find(entry)
            if found is None:
                raise StfsError("Arquivo %s não existe no pacote" % entry)
            entry = found
        return b"".join(self.iter_file(entry))

    def extract(self, out_dir: str, want: Optional[Callable[[str], bool]] = None) -> List[str]:
        """Extrai os arquivos para `out_dir` (cria as pastas). `want(caminho)` filtra."""
        root = os.path.normpath(os.path.abspath(out_dir))
        written = []
        with open(self.path, "rb") as f:
            for e in self.entries:
                dest = os.path.normpath(os.path.join(root, *e.path.split("/")))
                if dest != root and not dest.startswith(root + os.sep):
                    continue   # caminho suspeito
                if e.is_dir:
                    os.makedirs(dest, exist_ok=True)
                    continue
                if want is not None and not want(e.path):
                    continue
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "wb") as o:
                    for chunk in self.iter_file(e, f):
                        o.write(chunk)
                written.append(dest)
        return written

    # -- verificação
    def signature_status(self) -> Optional[bool]:
        """True/False para CON (assinatura confere com o certificado do pacote);
        None para LIVE/PIRS (assinatura da Microsoft, impossível de conferir aqui)."""
        if self.magic != "CON":
            return None
        return _rsa_verify(self.certificate, self.head[0x22C:0x344], self.signature)

    def signed_with_known_kv(self) -> bool:
        return self.magic == "CON" and self.certificate == _KV_CERTIFICATE

    def verify(self) -> List[str]:
        """Confere hash do cabeçalho, tabelas de hash (todos os níveis), hash do topo e,
        em CON, a assinatura. Devolve a lista de problemas (vazia = tudo certo)."""
        problems: List[str] = []
        with open(self.path, "rb") as f:
            f.seek(0x344)
            end = (self.header_size + 0xFFF) & ~0xFFF
            if hashlib.sha1(f.read(end - 0x344)).digest() != self.header_sha1:
                problems.append("SHA-1 do cabeçalho não confere")
            bad = 0
            for blk in range(self.allocated_blocks):
                sha, _status, _nxt = self._hash_record(f, blk)
                if hashlib.sha1(self._read_data_block(f, blk).ljust(BLOCK, b"\x00")).digest() != sha:
                    bad += 1
            if bad:
                problems.append("%d bloco(s) de dados com hash errado" % bad)
            if self.shift == 0:
                problems.extend(self._verify_tables(f))
        sig = self.signature_status()
        if sig is False:
            problems.append("Assinatura CON não confere com o certificado do pacote")
        return problems

    def _verify_tables(self, f) -> List[str]:
        lay = _layout(self.allocated_blocks)
        problems = []
        for upper, lower in (("L1", "L0"), ("L2", "L1")):
            for ti, treal in enumerate(lay[upper]):
                table = self._read_real(f, treal)
                for j in range(0xAA):
                    k = ti * 0xAA + j
                    if k >= len(lay[lower]):
                        break
                    sha = hashlib.sha1(self._read_real(f, lay[lower][k]).ljust(BLOCK, b"\x00")).digest()
                    if table[j * _HASH_RECORD:j * _HASH_RECORD + 20] != sha:
                        problems.append("Tabela %s %d: hash da tabela %s %d errado" % (upper, ti, lower, k))
        if self.allocated_blocks < 0xAA:
            top = lay["L0"][0]
        elif self.allocated_blocks < 0xAA * 0xAA:
            top = lay["L1"][0]
        else:
            top = lay["L2"][0]
        if hashlib.sha1(self._read_real(f, top)).digest() != self.top_hash:
            problems.append("Hash da tabela do topo não confere com o descritor")
        return problems


def read_stfs(path: str) -> StfsPackage:
    return StfsPackage(path)


def extract_stfs(path: str, out_dir: str, want: Optional[Callable[[str], bool]] = None) -> List[str]:
    return StfsPackage(path).extract(out_dir, want)


# ---------------------------------------------------------------------------
# Criação (port do makeCONGeneral do Onyx)


def _collect_tree(src_dir: str) -> List[Tuple[int, str, Optional[str], int]]:
    """(índice do pai, nome, caminho local ou None para pasta, tamanho) na ordem do Onyx:
    em cada pasta, primeiro as subpastas (cada uma seguida do seu conteúdo) e depois os
    arquivos, em ordem alfabética."""
    plan: List[Tuple[int, str, Optional[str], int]] = []

    def walk(local: str, parent: int):
        names = sorted(os.listdir(local))
        dirs = [n for n in names if os.path.isdir(os.path.join(local, n))]
        files = [n for n in names if os.path.isfile(os.path.join(local, n))]
        for d in dirs:
            plan.append((parent, d, None, 0))
            walk(os.path.join(local, d), len(plan) - 1)
        for n in files:
            path = os.path.join(local, n)
            plan.append((parent, n, path, os.path.getsize(path)))

    walk(src_dir, -1)
    for _parent, name, _path, _size in plan:
        raw = name.encode("latin-1", errors="replace")
        if not raw or len(raw) > 0x28:
            raise StfsError("Nome inválido para STFS (1 a 40 caracteres): %s" % name)
    return plan


def _blocks_for(size: int) -> int:
    return (size - 1) // BLOCK + 1 if size > 0 else 0


def _entry_bytes(name: str, is_dir: bool, blocks: int, first: int, parent: int, size: int) -> bytes:
    raw = name.encode("latin-1", errors="replace")
    flags = len(raw) | 0x40 | (0x80 if is_dir else 0)   # sempre consecutivo, como o Onyx
    return (raw.ljust(0x28, b"\x00") + bytes((flags,)) + _p24le(blocks) + _p24le(blocks)
            + _p24le(first) + struct.pack(">hI", parent, size)
            + struct.pack("<II", _FAT_TIMESTAMP, _FAT_TIMESTAMP))


def _metadata_bytes(display_name: str, description: str, title_id: int, title_name: str,
                    thumbnail: bytes, title_thumbnail: bytes, list_blocks: int,
                    total_blocks: int, content_size: int, top_hash: bytes) -> bytes:
    """Metadados de 0x22C a 0x971A (o resto do cabeçalho até 0xB000 é zero). O SHA-1
    do cabeçalho (0x32C) fica zerado e é preenchido depois."""
    out = bytearray()
    out += struct.pack(">qii", -1, 1, 0)           # licença: desbloqueado para todos
    out += bytes(15 * 16)
    out += bytes(20)                               # SHA-1 do cabeçalho
    out += struct.pack(">IIIqIiiI", _HEADER_SIZE_CON, CONTENT_SAVED_GAME, 2, content_size,
                       0, 0, 0, title_id)
    out += bytes((0, 0, 0, 0))                     # plataforma, tipo, disco, discos
    out += struct.pack(">I", 0)                    # save game id
    out += bytes(5) + bytes(8)                     # console id, profile id
    out += bytes((0x24, 0, 1)) + struct.pack("<h", list_blocks) + _p24le(0)
    out += top_hash + struct.pack(">ii", total_blocks, 0)
    out += struct.pack(">iqII", 0, 0, 0, 0)        # data files, tamanho, STFS, reservado
    out += bytes(0x4C) + bytes(0x14)
    out += _utf16_field(display_name, 0x100) + bytes(0x100 * 8)
    out += _utf16_field(description, 0x100) + bytes(0x100 * 8)
    out += _utf16_field("", 0x80) + _utf16_field(title_name, 0x80)
    out += bytes((0xC0,))                          # transfer flags
    thumbnail = thumbnail[:0x4000]
    title_thumbnail = title_thumbnail[:0x4000]
    out += struct.pack(">ii", len(thumbnail), len(title_thumbnail))
    out += thumbnail.ljust(0x4000, b"\x00") + title_thumbnail.ljust(0x4000, b"\x00")
    if len(out) != 0x971A - 0x22C:
        raise StfsError("Metadados STFS com tamanho errado")
    return bytes(out)


def build_con(src_dir: str, con_path: str, display_name: str, description: str = "",
              title_id: int = RB3_TITLE_ID, title_name: str = "Rock Band 3",
              thumbnail: bytes = b"", title_thumbnail: Optional[bytes] = None) -> str:
    """Cria um pacote CON (STFS assinado com o KV do Onyx/C3) com o conteúdo de `src_dir`
    (normalmente a pasta que contém `songs/`). Mesmo layout do Onyx: com os mesmos
    arquivos e metadados, o resultado é idêntico byte a byte à CON de referência."""
    if title_thumbnail is None:
        title_thumbnail = thumbnail
    plan = _collect_tree(src_dir)
    list_blocks = (len(plan) + 1) // 64 + 1
    total = list_blocks + sum(_blocks_for(size) for _p, _n, path, size in plan if path)
    lay = _layout(total)
    l0_tables = [bytearray(BLOCK) for _ in lay["L0"]]

    # tabela de arquivos (com a entrada vazia final) e blocos de cada arquivo
    entries = bytearray()
    first = list_blocks
    for parent, name, path, size in plan:
        blocks = _blocks_for(size) if path else 0
        entries += _entry_bytes(name, path is None, blocks, first if path else 0, parent,
                                size if path else 0)
        first += blocks
    entries += bytes(_ENTRY_SIZE)

    # Grava num .tmp e só troca no fim: erro no meio não deixa CON corrompida no destino
    tmp = con_path + ".tmp"
    try:
        with open(tmp, "wb") as out:
            out.write(bytes(0xB000))

            def write_block(n: int, data: bytes, has_next: bool):
                data = data.ljust(BLOCK, b"\x00")
                out.seek(_real_offset(lay["D"][n]))
                out.write(data)
                rec = (hashlib.sha1(data).digest() + bytes((STATUS_USED,))
                       + (struct.pack(">I", n + 1)[1:] if has_next else b"\xff\xff\xff"))
                t, r = divmod(n, 0xAA)
                l0_tables[t][r * _HASH_RECORD:(r + 1) * _HASH_RECORD] = rec

            for i in range(list_blocks):
                write_block(i, bytes(entries[i * BLOCK:(i + 1) * BLOCK]), i + 1 < list_blocks)
            n = list_blocks
            for _parent, _name, path, size in plan:
                if not path:
                    continue
                count = _blocks_for(size)
                with open(path, "rb") as f:
                    for i in range(count):
                        data = f.read(BLOCK)
                        if len(data) != min(BLOCK, size - i * BLOCK):
                            raise StfsError("Arquivo mudou de tamanho durante o empacotamento: %s"
                                            % path)
                        write_block(n, data, i + 1 < count)
                        n += 1
                    if f.read(1):
                        raise StfsError("Arquivo mudou de tamanho durante o empacotamento: %s"
                                        % path)

            # tabelas de hash: nível 0, depois 1 (hash das tabelas 0) e 2
            hashes = {"L0": [hashlib.sha1(bytes(t)).digest() for t in l0_tables]}
            for t, real in zip(l0_tables, lay["L0"]):
                out.seek(_real_offset(real))
                out.write(bytes(t))
            for level, lower in (("L1", "L0"), ("L2", "L1")):
                hashes[level] = []
                for ti, real in enumerate(lay[level]):
                    table = bytearray(BLOCK)
                    for j, sha in enumerate(hashes[lower][ti * 0xAA:(ti + 1) * 0xAA]):
                        table[j * _HASH_RECORD:j * _HASH_RECORD + 20] = sha
                    covered = total if level == "L2" else min(0xAA * 0xAA, total - 0xAA * 0xAA * ti)
                    table[0xFF0:0xFF4] = struct.pack(">i", covered)
                    hashes[level].append(hashlib.sha1(bytes(table)).digest())
                    out.seek(_real_offset(real))
                    out.write(bytes(table))
            out.seek(0, os.SEEK_END)
            size = out.tell()
            if size % BLOCK:
                out.write(bytes(BLOCK - size % BLOCK))
                size += BLOCK - size % BLOCK
            top = hashes["L0"][0] if total < 0xAA else (
                hashes["L1"][0] if total < 0xAA * 0xAA else hashes["L2"][0])

            header = bytearray(0xB000)
            header[0x22C:0x971A] = _metadata_bytes(display_name, description, title_id, title_name,
                                                   thumbnail, title_thumbnail, list_blocks, total,
                                                   size - 0xB000, top)
            header[0x32C:0x340] = hashlib.sha1(bytes(header[0x344:0xB000])).digest()
            header[0:4] = b"CON "
            header[4:0x1AC] = _KV_CERTIFICATE
            header[0x1AC:0x22C] = con_signature(bytes(header[0x22C:0x344]))
            out.seek(0)
            out.write(bytes(header))
        os.replace(tmp, con_path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
    return con_path
