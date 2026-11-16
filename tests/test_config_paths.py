"""config.json do .exe vai para %APPDATA%\\MidGuitar, com migração do config antigo."""
import json
import sys

from src.utils import config_manager as cm


def _frozen(monkeypatch, tmp_path):
    exe_dir = tmp_path / "Arquivos de Programas" / "MidGuitar"
    exe_dir.mkdir(parents=True)
    bundle = exe_dir / "_internal"
    bundle.mkdir()
    (bundle / "config.json").write_text(json.dumps({"volume": 10}), encoding="utf-8")
    appdata = tmp_path / "AppData" / "Roaming"
    monkeypatch.delenv("MIDGUITAR_USER_DIR", raising=False)
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)
    monkeypatch.setattr(sys, "executable", str(exe_dir / "MidGuitar.exe"))
    return exe_dir, appdata / "MidGuitar"


def test_frozen_saves_config_in_appdata(monkeypatch, tmp_path):
    exe_dir, data_dir = _frozen(monkeypatch, tmp_path)
    cfg = cm.load_config()
    assert cfg["volume"] == 10  # padrão do bundle
    cfg["volume"] = 55
    assert cm.save_config(cfg)
    assert (data_dir / "config.json").exists()
    assert not (exe_dir / "config.json").exists()
    assert cm.load_config()["volume"] == 55


def test_frozen_migrates_legacy_config(monkeypatch, tmp_path):
    exe_dir, data_dir = _frozen(monkeypatch, tmp_path)
    (exe_dir / "config.json").write_text(json.dumps({"volume": 77}), encoding="utf-8")
    assert cm.load_config()["volume"] == 77
    assert json.loads((data_dir / "config.json").read_text(encoding="utf-8"))["volume"] == 77


def test_frozen_presets_are_saved_in_appdata(monkeypatch, tmp_path):
    exe_dir, data_dir = _frozen(monkeypatch, tmp_path)
    dirs = cm.get_presets_dirs()
    assert dirs[0] == str(data_dir / "presets")


def test_source_mode_keeps_project_root(monkeypatch):
    monkeypatch.delenv("MIDGUITAR_USER_DIR", raising=False)
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    assert cm.get_user_data_dir() == cm.get_user_dir()
