import json
import os
import shutil
import sys

APP_DATA_FOLDER = "MidGuitar"

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

def get_user_data_dir() -> str:
    """Pasta gravável das configurações do usuário.

    No .exe é %APPDATA%\\MidGuitar (a pasta do programa pode estar em "Arquivos de Programas",
    onde o Windows não deixa gravar). Rodando pelo código-fonte continua sendo a raiz do projeto.
    A variável de ambiente MIDGUITAR_USER_DIR troca a pasta (testes).
    """
    override = os.environ.get("MIDGUITAR_USER_DIR")
    if override:
        base = override
    elif getattr(sys, 'frozen', False):
        appdata = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
        base = os.path.join(appdata, APP_DATA_FOLDER)
    else:
        return get_user_dir()
    try:
        os.makedirs(base, exist_ok=True)
    except OSError as e:
        print(f"[ConfigManager] Não foi possível criar {base}: {e}")
        return get_user_dir()
    return base


def _migrate_legacy_config(new_path: str) -> None:
    """Copia o config.json antigo (gravado ao lado do .exe) para a pasta nova, uma vez só."""
    if os.path.exists(new_path):
        return
    legacy = os.path.join(get_user_dir(), "config.json")
    if os.path.abspath(legacy) == os.path.abspath(new_path) or not os.path.exists(legacy):
        return
    try:
        shutil.copy2(legacy, new_path)
        print(f"[ConfigManager] config.json migrado de {legacy} para {new_path}")
    except OSError as e:
        print(f"[ConfigManager] Falha ao migrar config.json antigo: {e}")


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

def get_writable_config_path() -> str:
    """Onde o config.json é gravado."""
    return os.path.join(get_user_data_dir(), "config.json")


def get_config_path() -> str:
    # Para leitura: pasta do usuário (migrando o config antigo do lado do .exe), depois o bundle
    user_path = get_writable_config_path()
    _migrate_legacy_config(user_path)
    if os.path.exists(user_path):
        return user_path
    legacy = os.path.join(get_user_dir(), "config.json")
    if os.path.exists(legacy):
        return legacy
    bundle_path = os.path.join(get_bundle_dir(), "config.json")
    if os.path.exists(bundle_path):
        return bundle_path
    return user_path

def get_presets_dirs() -> list[str]:
    """Retorna lista de diretórios onde presets podem existir."""
    dirs = []
    data_dir = get_user_data_dir()
    if os.path.abspath(data_dir) != os.path.abspath(get_user_dir()):
        # No .exe os presets editados vão para %APPDATA%\MidGuitar\presets (gravável)
        data_p = os.path.join(data_dir, "presets")
        try:
            os.makedirs(data_p, exist_ok=True)
            dirs.append(data_p)
        except OSError:
            pass
    user_p = os.path.join(get_user_dir(), "presets")
    if os.path.exists(user_p):
        dirs.append(user_p)
    bundle_p = os.path.join(get_bundle_dir(), "presets")
    if os.path.exists(bundle_p) and bundle_p not in dirs:
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
    "auto_connect": True,
    "custom_samples": {},
    "key_sound_map": {}
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
    # Sempre salva na pasta gravável do usuário (%APPDATA%\MidGuitar no .exe)
    path = get_writable_config_path()
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
