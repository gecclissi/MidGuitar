"""Configuração compartilhada dos testes.

Garante que a raiz do repositório esteja no sys.path, para que
`import src.creator...` funcione independentemente de onde o pytest é chamado.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

