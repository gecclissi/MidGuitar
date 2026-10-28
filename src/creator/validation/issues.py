"""Tipo de problema devolvido pelo validador de exportação."""
from dataclasses import dataclass
from typing import Iterable


@dataclass
class Issue:
    """Um problema encontrado. level: 'error' ou 'warning'."""
    level: str
    code: str
    message: str
    location: str = ""


def has_errors(issues: Iterable[Issue]) -> bool:
    """True se existir ao menos um problema de nível 'error'."""
    return any(i.level == "error" for i in issues)
