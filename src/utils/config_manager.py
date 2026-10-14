import json
import os
import sys

def get_base_dir() -> str:
    """Retorna o diretório base correto, mesmo quando empacotado pelo PyInstaller."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def get_config_path() -> str:
    return os.path.join(get_base_dir(), "config.json")

def get_presets_dir() -> str:
    path = os.path.join(get_base_dir(), "presets")
    os.makedirs(path, exist_ok=True)
    return path

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
    path = get_config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[ConfigManager] Erro ao salvar config.json: {e}")
        return False

def list_presets() -> list[tuple[str, str]]:
    """Retorna lista de tuplas (id, nome_amigável) de todos os presets disponíveis."""
    presets_dir = get_presets_dir()
    result = []
    if os.path.exists(presets_dir):
        for fname in sorted(os.listdir(presets_dir)):
            if fname.endswith(".json"):
                preset_id = fname[:-5]
                filepath = os.path.join(presets_dir, fname)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        name = data.get("name", preset_id)
                        result.append((preset_id, name))
                except Exception:
                    result.append((preset_id, preset_id))
    return result

def load_preset(preset_id: str) -> dict:
    presets_dir = get_presets_dir()
    filepath = os.path.join(presets_dir, f"{preset_id}.json")
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ConfigManager] Erro ao carregar preset {preset_id}: {e}")
    return {}
