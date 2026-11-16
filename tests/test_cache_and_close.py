"""Limpeza do cache de áudio (%TEMP%/midguitar_cache), aviso de áudio ausente ao abrir
projeto e confirmação ao fechar com operação em andamento."""
import os
import time
import types

import pytest

from src.creator.chart_model import ChartSong, missing_audio_files, save_project
from src.creator.mogg_import import cleanup_cache


def _entry(root, name, size, age_s):
    d = os.path.join(root, name)
    os.makedirs(d, exist_ok=True)
    f = os.path.join(d, "a.ogg")
    with open(f, "wb") as fh:
        fh.write(b"x" * size)
    t = time.time() - age_s
    os.utime(f, (t, t))
    os.utime(d, (t, t))
    return d


def test_cleanup_cache_keeps_newest_up_to_limit(tmp_path):
    root = str(tmp_path / "midguitar_cache")
    old = _entry(root, "velho", 600, 3000)
    mid = _entry(root, "medio", 600, 2000)
    new = _entry(os.path.join(root, "mogg"), "novo", 600, 10)
    removed = cleanup_cache(max_bytes=1300, root=root)
    assert os.path.isdir(new) and os.path.isdir(mid)
    assert not os.path.exists(old)
    assert removed == 1


def test_cleanup_cache_keeps_protected_paths(tmp_path):
    root = str(tmp_path / "midguitar_cache")
    old = _entry(root, "velho", 600, 3000)
    _entry(root, "novo", 600, 10)
    cleanup_cache(max_bytes=700, root=root, keep=[os.path.join(old, "a.ogg")])
    assert os.path.isdir(old)


def test_cleanup_cache_missing_root_is_noop(tmp_path):
    assert cleanup_cache(max_bytes=1, root=str(tmp_path / "nao_existe")) == 0


def test_missing_audio_files_lists_absent_paths(tmp_path):
    real = tmp_path / "ok.ogg"
    real.write_bytes(b"x")
    s = ChartSong(audio_path=str(tmp_path / "sumiu.ogg"), audio_stems=[str(real), str(tmp_path / "x.ogg")])
    assert missing_audio_files(s) == [str(tmp_path / "sumiu.ogg"), str(tmp_path / "x.ogg")]
    assert missing_audio_files(ChartSong()) == []


# ---------------------------------------------------------------------------
# Interface (sem janela)
# ---------------------------------------------------------------------------
dialog = pytest.importorskip("src.ui.creator_studio_dialog", reason="UI indisponível neste ambiente")
from src.ui import background_task  # noqa: E402


def test_open_project_with_missing_audio_warns(monkeypatch, tmp_path):
    path = str(tmp_path / "p.mgproj")
    save_project(ChartSong(title="X", audio_path=str(tmp_path / "cache" / "mix.ogg")), path)
    monkeypatch.setattr(dialog.filedialog, "askopenfilename", lambda **k: path)
    warned = []
    monkeypatch.setattr(dialog.messagebox, "askyesno", lambda *a, **k: warned.append(a) or False)
    monkeypatch.setattr(dialog.messagebox, "showerror", lambda *a, **k: pytest.fail("erro"))
    fake = types.SimpleNamespace(applied=[])
    fake._apply_loaded_song = lambda s: fake.applied.append(s)
    fake._load_audio_file_smart = lambda f: pytest.fail("não deveria recarregar")
    dialog.CreatorStudioDialog._on_open_project(fake)
    assert fake.applied and warned
    assert "mix.ogg" in warned[0][1]


def test_open_project_relink_audio(monkeypatch, tmp_path):
    path = str(tmp_path / "p.mgproj")
    save_project(ChartSong(title="X", audio_path=str(tmp_path / "sumiu.ogg"), audio_stems=["a", "b"]), path)
    new_audio = str(tmp_path / "novo.ogg")
    answers = iter([path, new_audio])
    monkeypatch.setattr(dialog.filedialog, "askopenfilename", lambda **k: next(answers))
    monkeypatch.setattr(dialog.messagebox, "askyesno", lambda *a, **k: True)
    fake = types.SimpleNamespace(applied=[], loaded=[])
    fake._apply_loaded_song = lambda s: fake.applied.append(s)
    fake._load_audio_file_smart = lambda f: fake.loaded.append(f)
    dialog.CreatorStudioDialog._on_open_project(fake)
    assert fake.loaded == [new_audio]
    assert fake.applied[0].audio_stems == []


def test_any_busy_and_confirm_close():
    child = types.SimpleNamespace(_background_busy=True, winfo_children=lambda: [])
    root = types.SimpleNamespace(winfo_children=lambda: [child])
    assert background_task.any_busy(root)
    asked = []
    assert background_task.confirm_close_if_busy(root, ask=lambda *a: asked.append(a) or False) is False
    assert asked
    child._background_busy = False
    assert background_task.confirm_close_if_busy(root, ask=lambda *a: pytest.fail("não pergunta"))


def test_studio_close_asks_while_busy(monkeypatch):
    fake = types.SimpleNamespace(_background_busy=True, winfo_children=lambda: [], destroyed=[])
    fake.destroy = lambda: fake.destroyed.append(1)
    monkeypatch.setattr(dialog.messagebox, "askyesno", lambda *a, **k: False)
    dialog.CreatorStudioDialog._on_close_request(fake)
    assert not fake.destroyed
    monkeypatch.setattr(dialog.messagebox, "askyesno", lambda *a, **k: True)
    dialog.CreatorStudioDialog._on_close_request(fake)
    assert fake.destroyed
