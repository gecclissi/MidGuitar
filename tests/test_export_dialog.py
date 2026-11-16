"""Resultado da exportação: o validador nunca pode quebrar a mensagem de sucesso."""
import sys

import pytest

dialog = pytest.importorskip("src.ui.creator_studio_dialog", reason="UI indisponível neste ambiente")


class _Calls:
    def __init__(self):
        self.info, self.warn = [], []


@pytest.fixture
def calls(monkeypatch):
    c = _Calls()
    monkeypatch.setattr(dialog.messagebox, "showinfo", lambda *a, **k: c.info.append(a))
    monkeypatch.setattr(dialog.messagebox, "showwarning", lambda *a, **k: c.warn.append(a))
    return c


def _call(title="Pronto", msg="Exportado"):
    dialog.CreatorStudioDialog._show_export_result(object(), title, msg, "pkg", "rb3")


def test_import_failure_still_shows_success(monkeypatch, calls):
    monkeypatch.setitem(sys.modules, "src.creator.validation", None)  # import levanta ImportError
    _call()
    assert len(calls.info) == 1 and not calls.warn
    assert calls.info[0][0] == "Pronto"
    assert calls.info[0][1].startswith("Exportado")
    assert "Não foi possível verificar a compatibilidade" in calls.info[0][1]


def test_validate_failure_still_shows_success(monkeypatch, calls):
    import src.creator.validation as v
    monkeypatch.setattr(v, "validate_export", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
    _call()
    assert len(calls.info) == 1 and "boom" in calls.info[0][1]


def test_errors_use_showwarning(monkeypatch, calls):
    import src.creator.validation as v
    monkeypatch.setattr(v, "validate_export", lambda *a: ["x"])
    monkeypatch.setattr(v, "has_errors", lambda issues: True)
    monkeypatch.setattr(v, "format_issues_for_dialog", lambda issues: "\n\nERRO")
    _call()
    assert len(calls.warn) == 1 and not calls.info
    assert calls.warn[0] == ("Pronto", "Exportado\n\nERRO")


def test_import_ghwtde_folder_shows_unsupported_message(monkeypatch, calls, tmp_path):
    """Pasta de mod do GHWT:DE: aviso claro em vez de importar uma música vazia."""
    (tmp_path / "Content").mkdir()
    (tmp_path / "Content" / "x_song.pak.xen").write_bytes(b"\0")
    (tmp_path / "song.ini").write_text("[ModInfo]\nname=x\n[SongInfo]\ntitle=x\n", encoding="utf-8")
    errors = []
    monkeypatch.setattr(dialog.messagebox, "showerror", lambda *a, **k: errors.append(a))

    class _Entry:
        def delete(self, *a): pass
        def insert(self, *a): pass

    class _Fake:
        folder_entry = _Entry()
        def _apply_loaded_song(self, song):
            raise AssertionError("não deve carregar a música")

    dialog.CreatorStudioDialog._import_folder_path(_Fake(), str(tmp_path))
    assert not errors and not calls.info
    assert len(calls.warn) == 1
    assert calls.warn[0][0] == "Formato não suportado"
    assert "GHWT:DE ainda não suportado" in calls.warn[0][1]
