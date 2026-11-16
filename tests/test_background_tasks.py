"""Exportação / abrir pacote / compilar pacote fora da thread da interface (sem janela)."""
import threading
import time
import types

import pytest

dialog = pytest.importorskip("src.ui.creator_studio_dialog", reason="UI indisponível neste ambiente")
from src.ui import background_task  # noqa: E402
from src.creator.chart_model import ChartSong  # noqa: E402


@pytest.fixture
def boxes(monkeypatch):
    got = {"warn": [], "error": [], "info": []}
    monkeypatch.setattr(dialog.messagebox, "showwarning", lambda *a, **k: got["warn"].append(a))
    monkeypatch.setattr(dialog.messagebox, "showerror", lambda *a, **k: got["error"].append(a))
    monkeypatch.setattr(dialog.messagebox, "showinfo", lambda *a, **k: got["info"].append(a))
    return got


def _fake_studio(tmp_path):
    song = ChartSong()
    song.title = "Salut les amoureux"
    song.artist = "Joe Dassin"
    fake = types.SimpleNamespace(song=song, results=[])
    fake._ensure_audio_loaded = lambda *a, **k: True
    fake._show_export_result = lambda *a: fake.results.append(a)
    return fake


EXPORTS = [
    ("_on_convert_to_rb3", "export_rb3_song_package", "rb3_ps3"),
    ("_on_export_rb2", "export_rb2_song_package", "rb2"),
    ("_on_export_ps3_pkg", "export_ps3_pkg_structure", "rb3_ps3"),
    ("_on_convert_to_clone_hero", "export_clone_hero_song", "clonehero"),
    ("_on_export_xbox360", "export_xbox360_structure", "xbox360"),
    ("_on_export_ps4", "export_ps4_structure", "ps4"),
]


@pytest.mark.parametrize("handler,export_name,target", EXPORTS)
def test_export_handlers_use_runner_and_show_result(monkeypatch, boxes, tmp_path, handler, export_name, target):
    out = tmp_path / "saida"
    out.mkdir()
    pkg = out / "pacote"
    pkg.mkdir()
    (pkg / "x.pkg").write_bytes(b"")
    monkeypatch.setattr(dialog.filedialog, "askdirectory", lambda **k: str(out))
    seen = {}

    def fake_export(song, out_dir):
        seen["thread"] = threading.current_thread().name
        seen["args"] = (song.title, out_dir)
        return str(pkg)
    monkeypatch.setattr(dialog, export_name, fake_export)
    runs = []

    def runner(owner, text, work, on_success, on_error):
        runs.append(text)
        background_task.run_sync(owner, text, work, on_success, on_error)
    monkeypatch.setattr(dialog, "TASK_RUNNER", runner)

    fake = _fake_studio(tmp_path)
    getattr(dialog.CreatorStudioDialog, handler)(fake)
    assert runs and "Exportando" in runs[0]
    assert seen["args"] == ("Salut les amoureux", str(out))
    assert len(fake.results) == 1
    title, message, pkg_dir, tgt = fake.results[0]
    assert pkg_dir == str(pkg) and tgt == target and str(pkg) in message
    assert not boxes["error"]


def test_export_error_reaches_user(monkeypatch, boxes, tmp_path):
    monkeypatch.setattr(dialog.filedialog, "askdirectory", lambda **k: str(tmp_path))

    def boom(song, out_dir):
        raise OSError("disco cheio")
    monkeypatch.setattr(dialog, "export_ps3_pkg_structure", boom)
    fake = _fake_studio(tmp_path)
    dialog.CreatorStudioDialog._on_export_ps3_pkg(fake)
    assert not fake.results
    assert boxes["error"] and "disco cheio" in boxes["error"][0][1]


def test_export_cancelled_does_nothing(monkeypatch, boxes, tmp_path):
    monkeypatch.setattr(dialog.filedialog, "askdirectory", lambda **k: "")
    monkeypatch.setattr(dialog, "export_xbox360_structure",
                        lambda *a: (_ for _ in ()).throw(AssertionError("não deve exportar")))
    fake = _fake_studio(tmp_path)
    dialog.CreatorStudioDialog._on_export_xbox360(fake)
    assert not fake.results and not boxes["error"]


def test_compile_pack_runs_in_task(monkeypatch, boxes, tmp_path):
    monkeypatch.setattr(dialog.filedialog, "askdirectory", lambda **k: str(tmp_path))
    monkeypatch.setattr(dialog, "compile_clone_hero_pack", lambda songs, name, out: f"{out}/{name}")
    fake = types.SimpleNamespace(
        batch_songs=[ChartSong()], batch_art_path=None,
        batch_name_entry=types.SimpleNamespace(get=lambda: "Meu Pack"),
        batch_target_combo=types.SimpleNamespace(get=lambda: "Clone Hero / YARG"))
    dialog.CreatorStudioDialog._on_compile_batch_pack(fake)
    assert boxes["info"] and "Meu Pack" in boxes["info"][0][1]


def test_compile_pack_error_reaches_user(monkeypatch, boxes, tmp_path):
    monkeypatch.setattr(dialog.filedialog, "askdirectory", lambda **k: str(tmp_path))
    monkeypatch.setattr(dialog, "compile_ps3_song_pack",
                        lambda *a: (_ for _ in ()).throw(ValueError("música sem notas")))
    fake = types.SimpleNamespace(
        batch_songs=[ChartSong()], batch_art_path=None,
        batch_name_entry=types.SimpleNamespace(get=lambda: "P"),
        batch_target_combo=types.SimpleNamespace(get=lambda: "PS3 / RPCS3"))
    dialog.CreatorStudioDialog._on_compile_batch_pack(fake)
    assert boxes["error"] and "música sem notas" in boxes["error"][0][1]


class _FakeTkOwner:
    """Imita o `after` do Tk: os callbacks rodam quando o teste "gira" o loop."""

    def __init__(self):
        self.pending = []

    def after(self, _ms, fn):
        self.pending.append(fn)

    def winfo_children(self):
        return []

    def pump(self, timeout=5.0):
        end = time.time() + timeout
        while self.pending and time.time() < end:
            fn = self.pending.pop(0)
            fn()
            time.sleep(0.005)


def test_run_with_progress_runs_work_in_other_thread_and_returns_on_ui_thread(monkeypatch):
    monkeypatch.setattr(background_task, "_ProgressWindow",
                        lambda owner, text: types.SimpleNamespace(close=lambda: None))
    owner = _FakeTkOwner()
    main = threading.current_thread()
    seen = {}

    def work():
        seen["work_thread"] = threading.current_thread()
        return 42

    def ok(v):
        seen["value"] = v
        seen["ok_thread"] = threading.current_thread()

    background_task.run_with_progress(owner, "Exportando…", work, ok, lambda e: seen.setdefault("err", e))
    owner.pump()
    assert seen["value"] == 42
    assert seen["work_thread"] is not main
    assert seen["ok_thread"] is main
    assert owner._background_busy is False


def test_run_with_progress_error_and_busy_guard(monkeypatch):
    monkeypatch.setattr(background_task, "_ProgressWindow",
                        lambda owner, text: types.SimpleNamespace(close=lambda: None))
    owner = _FakeTkOwner()
    errors = []
    gate = threading.Event()

    def work():
        gate.wait(5)
        raise RuntimeError("falhou no meio")

    background_task.run_with_progress(owner, "x", work, lambda v: None, errors.append)
    # segunda operação enquanto a primeira roda: recusada com mensagem
    background_task.run_with_progress(owner, "y", lambda: 1, lambda v: None, errors.append)
    assert len(errors) == 1 and "andamento" in str(errors[0])
    gate.set()
    owner.pump()
    assert len(errors) == 2 and "falhou no meio" in str(errors[1])
