"""
Autoteste do MidGuitar (`MidGuitar.exe --selftest` ou `python src/main.py --selftest`).

Importa todos os módulos do app e as bibliotecas de criptografia e áudio, confere os
arquivos que vão junto no build e codifica 0,1 s de áudio Vorbis. Não abre janela.
Escreve o relatório no console (quando houver) e em %TEMP%\\midguitar_selftest.txt.
Código de saída: 0 = tudo certo, 1 = alguma falha.
"""

import importlib
import io
import os
import sys
import tempfile
import traceback

MODULES = [
    # app
    "src.ui.app", "src.ui.creator_studio_dialog", "src.ui.background_task",
    "src.ui.mapping_dialog", "src.ui.sound_manager_dialog", "src.ui.sound_browser_dialog",
    "src.ui.lyrics_manager_dialog", "src.ui.batch_key_mapper_dialog",
    "src.midi.reader", "src.midi.detector", "src.midi.mapper",
    "src.audio.engine", "src.utils.config_manager", "src.utils.instruments",
    # criação / exportação / importação
    "src.creator.chart_model", "src.creator.chart_importer", "src.creator.midi_generator",
    "src.creator.auto_charter", "src.creator.lyric_processor", "src.creator.difficulty",
    "src.creator.tempo_map", "src.creator.passthrough", "src.creator.rbn_specs",
    "src.creator.mogg_generator", "src.creator.mogg_crypt", "src.creator.mogg_import",
    "src.creator.rb_mogg_multitrack", "src.creator.audio_resample",
    "src.creator.png_ps3", "src.creator.png_xbox", "src.creator.edat", "src.creator.ps3_pkg",
    "src.creator.xbox_stfs", "src.creator.clonehero_exporter", "src.creator.rb3_dta_exporter",
    "src.creator.rb2_exporter", "src.creator.ps3_pkg_exporter", "src.creator.xbox360_exporter",
    "src.creator.ps4_exporter", "src.creator.pack_compiler",
    "src.creator.validation", "src.creator.validation.dta_parser",
    "src.creator.validation.dta_rules", "src.creator.validation.midi_rules",
    "src.creator.validation.mogg_rules", "src.creator.validation.profiles",
    "src.creator.validation.report", "src.creator.validation.targets",
    # bibliotecas externas
    "Crypto.Cipher.AES", "Crypto.Hash.CMAC", "soundfile", "numpy", "mido", "rtmidi",
    "pygame", "customtkinter", "tkinterdnd2", "PIL.Image",
]

BUNDLED_FILES = ["presets", "assets/icon.ico", "assets/tutorial", "TUTORIAL_VISUAL.md"]


def run_selftest() -> int:
    lines = []
    failures = 0
    for name in MODULES:
        try:
            importlib.import_module(name)
            lines.append(f"OK    import {name}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            lines.append(f"FALHA import {name}: {e!r}")

    try:
        from src.utils.config_manager import get_asset_path, get_writable_config_path
        for rel in BUNDLED_FILES:
            path = get_asset_path(rel)
            if os.path.exists(path):
                lines.append(f"OK    arquivo {rel}")
            else:
                failures += 1
                lines.append(f"FALHA arquivo {rel} não encontrado ({path})")
        lines.append(f"INFO  config.json gravado em {get_writable_config_path()}")
    except Exception as e:  # noqa: BLE001
        failures += 1
        lines.append(f"FALHA arquivos: {e!r}")

    try:
        import numpy as np
        import soundfile as sf
        buf = io.BytesIO()
        tone = (0.2 * np.sin(np.arange(4410) * 2 * np.pi * 440 / 44100)).astype("float32")
        sf.write(buf, np.stack([tone, tone], axis=1), 44100, format="OGG", subtype="VORBIS")
        if buf.tell() <= 0:
            raise RuntimeError("OGG vazio")
        lines.append(f"OK    Vorbis (libsndfile {sf.__libsndfile_version__})")
    except Exception as e:  # noqa: BLE001
        failures += 1
        lines.append(f"FALHA Vorbis: {e!r}")

    try:
        from Crypto.Cipher import AES
        AES.new(b"\0" * 16, AES.MODE_ECB).encrypt(b"\0" * 16)
        lines.append("OK    AES (pycryptodome)")
    except Exception as e:  # noqa: BLE001
        failures += 1
        lines.append(f"FALHA AES: {e!r}")

    lines.append("OK" if failures == 0 else f"FALHOU ({failures} problema(s))")
    report = "\n".join(lines)
    try:
        print(report)
    except Exception:
        pass
    try:
        with open(os.path.join(tempfile.gettempdir(), "midguitar_selftest.txt"), "w", encoding="utf-8") as f:
            f.write(report + "\n")
    except Exception:
        traceback.print_exc()
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(run_selftest())
