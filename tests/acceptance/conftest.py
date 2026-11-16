"""Fixtures dos testes de aceitação (diagnóstico 2026-11-16).

Usam as músicas de referência em music/_refs e music/_unsupported (fora do Git).
Sem essas pastas, os testes que dependem delas são pulados. Nada é escrito nas
pastas originais: tudo que é lido por importadores que gravam arquivos ao lado
da origem é copiado antes para tmp_path.
"""
import glob
import os
import shutil

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REFS = os.path.join(ROOT, "music", "_refs")
UNSUPPORTED = os.path.join(ROOT, "music", "_unsupported")
JOE = os.path.join(REFS, "Joe Dassin - Salut les amoureux")
XBOX_CON = os.path.join(REFS, "xbox_con", "Joe Dassin - Salut les amoureux_rb3con")
GORILLAZ = os.path.join(REFS, "Gorillaz - Andromeda")
FIVESOS = os.path.join(REFS, "5 Seconds Of Summer - Ghost Of YouXB")
PAVLO = os.path.join(UNSUPPORTED, "PAVLO - Mediterranean Eyes")
PKG_FILE = os.path.join(ROOT, "music", "Gorillaz - Andromeda.pkg")


def need(path):
    """Marca de skip quando a referência não existe."""
    return pytest.mark.skipif(not os.path.exists(path), reason=f"referência ausente: {os.path.basename(path)}")


def ps3_song_dir(pkg_root):
    hits = glob.glob(os.path.join(pkg_root, "USRDIR", "*", "songs", "*", ""))
    return hits[0].rstrip("\\/") if hits else None


@pytest.fixture(scope="session")
def joe_song():
    """Joe Dassin importado da pasta Clone Hero (só leitura: a pasta não tem .mogg)."""
    if not os.path.isdir(JOE):
        pytest.skip("referência Joe Dassin ausente")
    from src.creator.chart_importer import import_song_from_folder
    return import_song_from_folder(JOE)


@pytest.fixture
def copy_ref(tmp_path):
    """Copia uma pasta/arquivo de referência para tmp_path e devolve o novo caminho."""
    def _copy(src):
        dst = os.path.join(str(tmp_path), "ref", os.path.basename(src))
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
        return dst
    return _copy
