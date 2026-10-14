"""
Script automatizado de compilação do executável (.exe) do MidGuitar usando PyInstaller.
Inclui presets, icones, configurações e pacotes do CustomTkinter e Pygame.
"""

import os
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
        print("\n" + "=" * 60)
        print("COMPILAÇÃO CONCLUÍDA COM SUCESSO!")
        print("O executável está pronto em: dist/MidGuitar/MidGuitar.exe")
        print("=" * 60)
    else:
        print(f"\nErro durante a compilação. Código de retorno: {res.returncode}")

if __name__ == "__main__":
    build()
