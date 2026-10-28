"""Formata os achados da validação para exibir em caixas de diálogo."""
from typing import List

from src.creator.validation.issues import Issue


def format_issues_for_dialog(issues: List[Issue], limit: int = 10) -> str:
    """Devolve o bloco de texto da verificação de compatibilidade ("" se não houver achados)."""
    if not issues:
        return ""
    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level != "error"]
    lines = [f"\n\n⚠️ Verificação de compatibilidade: {len(errors)} erro(s), {len(warnings)} aviso(s)"]
    ordered = errors + warnings
    for issue in ordered[:limit]:
        icon = "❌" if issue.level == "error" else "⚠️"
        lines.append(f"• {icon} {issue.message}")
    rest = len(ordered) - limit
    if rest > 0:
        lines.append(f"• … e mais {rest} item(ns)")
    return "\n".join(lines)
