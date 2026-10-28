from src.creator.validation import Issue
from src.creator.validation.report import format_issues_for_dialog


def test_empty_issues_gives_empty_text():
    assert format_issues_for_dialog([]) == ""


def test_errors_first_and_limit():
    issues = [Issue("warning", "W", f"aviso {i}") for i in range(8)] + [Issue("error", "E", f"erro {i}") for i in range(5)]
    text = format_issues_for_dialog(issues, limit=10)
    lines = [l for l in text.splitlines() if l.startswith("• ")]
    assert lines[0].startswith("• ❌") and len(lines) == 11 and lines[-1] == "• … e mais 3 item(ns)"
    assert "5 erro(s), 8 aviso(s)" in text
