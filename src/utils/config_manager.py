import json
import os
import sys

def get_bundle_dir() -> str:
    """Retorna o diretório onde os recursos empacotados pelo PyInstaller residem (_MEIPASS ou código fonte)."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def get_user_dir() -> str:
    """Retorna o diretório do executável (onde o usuário pode salvar novos presets e configs)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def get_asset_path(relative_path: str) -> str:
    """Localiza um arquivo de asset (ícone, som, etc.) no diretório do usuário ou no bundle."""
    # 1. Tenta no diretório do usuário
    user_path = os.path.join(get_user_dir(), relative_path)
    if os.path.exists(user_path):
        return user_path
    # 2. Tenta no bundle interno do PyInstaller
    bundle_path = os.path.join(get_bundle_dir(), relative_path)
    if os.path.exists(bundle_path):
        return bundle_path
    return user_path

def get_config_path() -> str:
    # Para leitura, verifica usuário depois bundle
    user_path = os.path.join(get_user_dir(), "config.json")
    if os.path.exists(user_path):
        return user_path
    bundle_path = os.path.join(get_bundle_dir(), "config.json")
    if os.path.exists(bundle_path):
        return bundle_path
    return user_path

def get_presets_dirs() -> list[str]:
    """Retorna lista de diretórios onde presets podem existir."""
    dirs = []
    user_p = os.path.join(get_user_dir(), "presets")
    if os.path.exists(user_p):
        dirs.append(user_p)
    bundle_p = os.path.join(get_bundle_dir(), "presets")
    if os.path.exists(bundle_p) and bundle_p != user_p:
        dirs.append(bundle_p)
    if not dirs:
        os.makedirs(user_p, exist_ok=True)
        dirs.append(user_p)
    return dirs

DEFAULT_CONFIG = {
    "midi_in_port": None,
    "midi_out_port": None,
    "use_internal_synth": True,
    "instrument_id": 29,
    "volume": 85,
    "octave_shift": 0,
    "current_preset": "rock_power_chords",
    "theme": "dark",
    "auto_connect": True
}

def load_config() -> dict:
    path = get_config_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                config = DEFAULT_CONFIG.copy()
                config.update(data)
                return config
        except Exception as e:
            print(f"[ConfigManager] Erro ao ler config.json: {e}")
    return DEFAULT_CONFIG.copy()

def save_config(config: dict) -> bool:
    # Sempre salva no diretório do usuário/executável
    path = os.path.join(get_user_dir(), "config.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[ConfigManager] Erro ao salvar config.json: {e}")
        return False

def list_presets() -> list[tuple[str, str]]:
    """Retorna lista de tuplas (id, nome_amigável) de todos os presets disponíveis."""
    seen_ids = set()
    result = []
    for pdir in get_presets_dirs():
        if os.path.exists(pdir):
            for fname in sorted(os.listdir(pdir)):
                if fname.endswith(".json"):
                    preset_id = fname[:-5]
                    if preset_id in seen_ids:
                        continue
                    seen_ids.add(preset_id)
                    filepath = os.path.join(pdir, fname)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            name = data.get("name", preset_id)
                            result.append((preset_id, name))
                    except Exception:
                        result.append((preset_id, preset_id))
    return result

def load_preset(preset_id: str) -> dict:
    for pdir in get_presets_dirs():
        filepath = os.path.join(pdir, f"{preset_id}.json")
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[ConfigManager] Erro ao carregar preset {preset_id}: {e}")
    return {}
