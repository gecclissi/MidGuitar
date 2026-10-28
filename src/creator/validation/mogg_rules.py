"""Regras de validação do .mogg (cabeçalho Harmonix 0x0A + Ogg Vorbis).

Funções puras: devolvem List[Issue] / MoggInfo e nunca lançam exceção.
"""
import os
import struct
import tempfile
from dataclasses import dataclass
from typing import List, Optional

import soundfile as sf

from src.creator.validation.issues import Issue

_UNENCRYPTED_VERSION = 0x0A


@dataclass
class MoggInfo:
    version: int
    ogg_offset: int
    channels: Optional[int]
    sample_rate: Optional[int]


def _read_header(path: str):
    """Devolve (bytes do arquivo, versão, ogg_offset) ou None se ilegível."""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return None
    if len(data) < 20:
        return None
    version, offset = struct.unpack("<II", data[:8])
    return data, version, offset


def _probe_ogg(ogg: bytes):
    """Abre o trecho OGG via arquivo temporário (sempre removido). Lança se inválido."""
    fd, tmp = tempfile.mkstemp(suffix=".ogg")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(ogg)
        info = sf.info(tmp)
        return info.channels, info.samplerate
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def read_mogg_info(path: str) -> Optional[MoggInfo]:
    """Lê versão, offset, canais e taxa do .mogg; None se ilegível."""
    try:
        hdr = _read_header(path)
        if hdr is None:
            return None
        data, version, offset = hdr
        if version != _UNENCRYPTED_VERSION:
            return MoggInfo(version, offset, None, None)
        try:
            ch, sr = _probe_ogg(data[offset:])
        except Exception:
            return MoggInfo(version, offset, None, None)
        return MoggInfo(version, offset, ch, sr)
    except Exception:
        return None


def validate_mogg(path: str) -> List[Issue]:
    """Valida o .mogg. Nunca lança exceção."""
    fname = os.path.basename(str(path))
    try:
        hdr = _read_header(path)
        if hdr is None:
            return [Issue("error", "MOGG_UNREADABLE",
                          "O .mogg não existe, não abre ou tem menos de 20 bytes", fname)]
        data, version, offset = hdr
        if version != _UNENCRYPTED_VERSION:
            return [Issue("warning", "MOGG_ENCRYPTED",
                          "O .mogg está criptografado (versão %d): é válido para o jogo, "
                          "mas não dá para conferir os canais" % version, fname)]
        if data[offset:offset + 4] != b"OggS":
            return [Issue("error", "MOGG_BAD_OFFSET",
                          "O offset do áudio (%d) não aponta para um stream OggS" % offset,
                          fname)]
        try:
            _probe_ogg(data[offset:])
        except Exception as e:
            return [Issue("error", "MOGG_BAD_OGG",
                          "O áudio Ogg Vorbis dentro do .mogg não abre: %s" % e, fname)]
        return []
    except Exception as e:  # rede de segurança
        return [Issue("error", "MOGG_UNREADABLE",
                      "Não foi possível analisar o .mogg: %s" % e, fname)]
