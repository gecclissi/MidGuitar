"""
Script automatizado de compilação do executável (.exe) do MidGuitar usando PyInstaller.
Inclui presets, ícones, tutorial ilustrado, configurações e as bibliotecas de interface,
MIDI, áudio (soundfile/libsndfile, pygame) e criptografia (pycryptodome).

Uso:  venv\\Scripts\\python build_exe.py
Saída: dist\\MidGuitar\\MidGuitar.exe (confira com: dist\\MidGuitar\\MidGuitar.exe --selftest)

Observação: o config.json do usuário NÃO fica ao lado do .exe; o app grava em
%APPDATA%\\MidGuitar\\config.json (e migra um config.json antigo do lado do .exe).
"""

import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def build() -> int:
    os.chdir(ROOT)  # caminhos relativos abaixo valem a partir da raiz do projeto
    print("=" * 60)
    print("Iniciando compilação do MidGuitar para Executável Windows (.exe)...")
    print("=" * 60)

    sep = os.pathsep  # ';' no Windows
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",                       # Gera em pasta distribuível rápida e estável
        "--windowed",                     # Sem console preto de terminal (janela limpa)
        "--name=MidGuitar",
        "--icon=assets/icon.ico",
        "--paths=.",                      # acha o pacote src sem depender do diretório atual
        f"--add-data=presets{sep}presets",
        f"--add-data=assets{sep}assets",  # inclui assets/tutorial (imagens do tutorial)
        f"--add-data=TUTORIAL_VISUAL.md{sep}.",
        f"--add-data=LICENSE{sep}.",  # GPL v3: a licença acompanha o programa
        f"--add-data=CREDITS.md{sep}.",
        f"--add-data=config.json{sep}.",  # só o padrão (somente leitura)
        "--collect-submodules=src",
        "--collect-all=customtkinter",
        "--collect-all=rtmidi",
        "--collect-all=pygame",
        "--collect-all=PIL",
        "--collect-all=soundfile",        # inclui a libsndfile (Vorbis do .ogg/.mogg)
        "--collect-all=tkinterdnd2",      # arrastar e soltar
        "--collect-all=Crypto",           # pycryptodome (AES/CMAC do .mid.edat e do .mogg)
        "--collect-all=mido",
        "src/main.py",
    ]

    print("Executando:", " ".join(cmd))
    res = subprocess.run(cmd)
    if res.returncode != 0:
        print(f"\nErro durante a compilação. Código de retorno: {res.returncode}")
        return res.returncode

    dist_dir = os.path.join("dist", "MidGuitar")
    # Copia presets, assets e o tutorial para a raiz de dist/MidGuitar para o usuário ver e editar
    try:
        for folder in ("presets", "assets"):
            target = os.path.join(dist_dir, folder)
            if os.path.exists(target):
                shutil.rmtree(target)
            shutil.copytree(folder, target)
        shutil.copy2("TUTORIAL_VISUAL.md", os.path.join(dist_dir, "TUTORIAL_VISUAL.md"))
        stale = os.path.join(dist_dir, "config.json")
        if os.path.exists(stale):
            os.remove(stale)  # o config do usuário fica em %APPDATA%\MidGuitar
        print("[Build] Presets, assets e TUTORIAL_VISUAL.md copiados para dist/MidGuitar/")
    except Exception as e:
        print(f"[Build] Aviso ao copiar dados para a raiz de dist: {e}")

    print("\n" + "=" * 60)
    print("COMPILAÇÃO CONCLUÍDA COM SUCESSO!")
    print("O executável está pronto em: dist/MidGuitar/MidGuitar.exe")
    print("Autoteste: dist\\MidGuitar\\MidGuitar.exe --selftest  (relatório em %TEMP%\\midguitar_selftest.txt)")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(build())
