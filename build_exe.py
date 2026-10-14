"""
Script automatizado de compilação do executável (.exe) do MidGuitar usando PyInstaller.
Inclui presets, ícones, configurações e pacotes do CustomTkinter e Pygame.
"""

import os
import shutil
import subprocess
import sys

def build():
    print("=" * 60)
    print("Iniciando compilação do MidGuitar para Executável Windows (.exe)...")
    print("=" * 60)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",                       # Gera em pasta distribuível rápida e estável
        "--windowed",                     # Sem console preto de terminal (janela limpa)
        "--name=MidGuitar",
        "--icon=assets/icon.ico",
        "--add-data=presets;presets",
        "--add-data=assets;assets",
        "--add-data=config.json;.",
        "--collect-all=customtkinter",
        "--collect-all=rtmidi",
        "--collect-all=pygame",
        "src/main.py"
    ]

    print("Executando:", " ".join(cmd))
    res = subprocess.run(cmd)
    if res.returncode == 0:
        dist_dir = os.path.join("dist", "MidGuitar")
        
        # Copia pastas para a raiz de dist/MidGuitar para que o usuário possa ver e editar presets
        try:
            target_presets = os.path.join(dist_dir, "presets")
            if os.path.exists(target_presets):
                shutil.rmtree(target_presets)
            shutil.copytree("presets", target_presets)

            target_assets = os.path.join(dist_dir, "assets")
            if os.path.exists(target_assets):
                shutil.rmtree(target_assets)
            shutil.copytree("assets", target_assets)

            shutil.copy2("config.json", os.path.join(dist_dir, "config.json"))
            print("[Build] Presets, assets e config.json copiados para dist/MidGuitar/")
        except Exception as e:
            print(f"[Build] Aviso ao copiar dados para a raiz de dist: {e}")

        print("\n" + "=" * 60)
        print("COMPILAÇÃO CONCLUÍDA COM SUCESSO!")
        print("O executável está pronto em: dist/MidGuitar/MidGuitar.exe")
        print("=" * 60)
    else:
        print(f"\nErro durante a compilação. Código de retorno: {res.returncode}")

if __name__ == "__main__":
    build()
