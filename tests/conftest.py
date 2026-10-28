"""Configuração compartilhada dos testes.

Garante que a raiz do repositório esteja no sys.path, para que
`import src.creator...` funcione independentemente de onde o pytest é chamado.
"""
import os
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def refs_dir() -> pathlib.Path:
    """Pasta com customs de referência reais (variável MIDGUITAR_REFS).

    Pula o teste se a variável não estiver definida ou não apontar para uma pasta.
    """
    value = os.environ.get("MIDGUITAR_REFS")
    if not value:
        pytest.skip("MIDGUITAR_REFS não definida")
    path = pathlib.Path(value)
    if not path.is_dir():
        pytest.skip("MIDGUITAR_REFS não é uma pasta existente")
    return path
