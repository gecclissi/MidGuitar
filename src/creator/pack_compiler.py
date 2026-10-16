"""
Compilador de Pacotes de Músicas em Lote (Batch Song Pack Compiler).
Permite selecionar uma pasta com dezenas de músicas (ou várias músicas criadas no app)
e compilar tudo junto em um único pacote consolidado:
- Mescla todas as músicas em um único 'songs.dta' unificado oficial do Rock Band 3
- Organiza a pasta USRDIR/songs/{musica}/ para cada faixa com seus respectivos MIDIs e áudios
- Gera um único PARAM.SFO e ICON0.PNG para o Mega Pacote do PS3
- Gera instalador automático de 1 clique para o RPCS3
- Permite também empacotar pastas coletivas para o Clone Hero
"""

import os
import shutil
import hashlib
from typing import List, Tuple
from PIL import Image

from src.creator.chart_model import ChartSong
from src.creator.chart_importer import import_song_from_folder
from src.creator.rb3_dta_exporter import generate_songs_dta_content
from src.creator.midi_generator import generate_rbn_midi, save_midi
from src.creator.ps3_pkg_exporter import generate_param_sfo, _create_default_icon

def scan_folder_for_songs(root_dir: str) -> List[Tuple[str, ChartSong]]:
    """
    Varre um diretório em busca de todas as músicas (pastas com song.ini ou .mid).
    Retorna lista de tuplas: (caminho_da_pasta, objeto_ChartSong)
    """
    found_songs = []
    if not os.path.exists(root_dir):
        return found_songs

    # Verifica se a própria pasta raiz é uma música
    if os.path.exists(os.path.join(root_dir, "song.ini")) or any(f.lower().endswith((".mid", ".chart")) for f in os.listdir(root_dir) if os.path.isfile(os.path.join(root_dir, f))):
        s = import_song_from_folder(root_dir)
        if s.title and s.title != "Nova Música":
            found_songs.append((root_dir, s))
            return found_songs

    # Varre subpastas
    for entry in os.scandir(root_dir):
        if entry.is_dir():
            sub = entry.path
            has_ini = os.path.exists(os.path.join(sub, "song.ini"))
            has_mid = any(f.lower().endswith((".mid", ".chart")) for f in os.listdir(sub) if os.path.isfile(os.path.join(sub, f)))
            if has_ini or has_mid:
                try:
                    song = import_song_from_folder(sub)
                    found_songs.append((sub, song))
                except Exception as e:
                    print(f"[PackCompiler] Erro ao ler pasta {sub}: {e}")

    return found_songs

def compile_ps3_song_pack(
    songs: List[ChartSong],
    pack_name: str,
    output_base_dir: str,
    pack_art_path: str = None
) -> str:
    """
    Compila múltiplas músicas em um único pacote consolidado para PS3 e RPCS3.
    """
    clean_pack_name = "".join(c for c in pack_name if c.isalnum() or c in " _-").strip() or "MegaPack_RB3"
    pack_id_str = hashlib.md5(clean_pack_name.encode()).hexdigest().upper()[:8]
    content_id = f"UP0006-BLUS30463_00-PK{pack_id_str}0001"

    pack_root = os.path.join(output_base_dir, f"PS3_PACK_{clean_pack_name}")
    usrdir = os.path.join(pack_root, "USRDIR")
    songs_dir = os.path.join(usrdir, "songs")
    os.makedirs(songs_dir, exist_ok=True)

    # 1. PARAM.SFO do Mega Pacote
    sfo_path = os.path.join(pack_root, "PARAM.SFO")
    sfo_bytes = generate_param_sfo(f"RB3 Pack: {pack_name[:20]} ({len(songs)} Músicas)", content_id)
    with open(sfo_path, "wb") as f:
        f.write(sfo_bytes)

    # 2. ICON0.PNG do Pacote
    icon_path = os.path.join(pack_root, "ICON0.PNG")
    if pack_art_path and os.path.exists(pack_art_path):
        try:
            im = Image.open(pack_art_path).convert("RGBA")
            im = im.resize((320, 176), Image.Resampling.LANCZOS)
            im.save(icon_path, "PNG")
        except Exception:
            _create_default_icon(icon_path, pack_name, f"{len(songs)} Músicas")
    else:
        _create_default_icon(icon_path, pack_name, f"{len(songs)} Músicas")

    # 3. Mescla todos os blocos do songs.dta
    dta_blocks = []
    used_shortnames = set()
    from src.creator.mogg_generator import create_unencrypted_mogg

    for idx, song in enumerate(songs):
        raw_shortname = "".join(c for c in f"{song.artist}_{song.title}" if c.isalnum()).lower()[:20] or f"song_{idx+1}"
        shortname = raw_shortname
        counter = 1
        while shortname in used_shortnames:
            shortname = f"{raw_shortname}_{counter}"
            counter += 1
        used_shortnames.add(shortname)

        song_id = 1010000000 + (idx * 100) + (int(hashlib.md5(shortname.encode()).hexdigest()[:6], 16) % 90)
        dta_block = generate_songs_dta_content(song, shortname, song_id=song_id)
        dta_blocks.append(dta_block)

        # Pasta da música individual dentro de songs/
        track_dir = os.path.join(songs_dir, shortname)
        os.makedirs(track_dir, exist_ok=True)

        # Arquivo MIDI da música
        mid = generate_rbn_midi(song)
        mid_path = os.path.join(track_dir, f"{shortname}.mid")
        save_midi(mid, mid_path)

        # Gera o arquivo oficial .mogg (0x0A) e copia áudios (stems ou mix)
        primary_audio = song.audio_path or (song.audio_stems[0] if song.audio_stems else None)
        if primary_audio and os.path.exists(primary_audio):
            create_unencrypted_mogg(primary_audio, os.path.join(track_dir, f"{shortname}.mogg"))

        if song.audio_stems:
            for s_path in song.audio_stems:
                if os.path.exists(s_path):
                    try:
                        shutil.copy2(s_path, os.path.join(track_dir, os.path.basename(s_path)))
                    except Exception:
                        pass
        elif song.audio_path and os.path.exists(song.audio_path):
            ext = os.path.splitext(song.audio_path)[1].lower()
            try:
                shutil.copy2(song.audio_path, os.path.join(track_dir, f"{shortname}{ext}"))
            except Exception:
                pass

    # Salva o arquivo songs.dta unificado com todas as músicas juntas!
    unified_dta_path = os.path.join(songs_dir, "songs.dta")
    with open(unified_dta_path, "w", encoding="utf-8") as f:
        f.write("\n".join(dta_blocks))

    # 4. package.conf para compiladores PKG
    conf_path = os.path.join(pack_root, "package.conf")
    conf_content = f"""Content-ID = {content_id}
k_licensee = 0x00000000000000000000000000000000
DRMType = Free
ContentType = GameExec
PackageVersion = 01.00
"""
    with open(conf_path, "w", encoding="utf-8") as f:
        f.write(conf_content)

    # 5. Script Automático de Instalação no RPCS3 de 1 Clique
    bat_path = os.path.join(pack_root, "INSTALAR_PACOTE_NO_RPCS3.bat")
    bat_content = f"""@echo off
chcp 65001 > nul
echo ============================================================
echo   MidGuitar - Instalador de MEGA PACOTE no RPCS3
echo   Pacote: {pack_name} ({len(songs)} Músicas)
echo ============================================================
echo.
echo Procurando a pasta do emulador RPCS3...
set "RPCS3_FOUND="

for %%D in (
  "%USERPROFILE%\\Desktop\\rpcs3"
  "%USERPROFILE%\\Downloads\\rpcs3"
  "C:\\rpcs3"
  "D:\\rpcs3"
  "E:\\rpcs3"
  "%APPDATA%\\rpcs3"
) do (
  if exist "%%~D\\dev_hdd0\\game\\BLUS30463\\USRDIR" (
    set "RPCS3_FOUND=%%~D\\dev_hdd0\\game\\BLUS30463\\USRDIR"
  )
)

if not defined RPCS3_FOUND (
  echo Digite ou cole o caminho da pasta dev_hdd0\\game\\BLUS30463\\USRDIR do seu RPCS3:
  set /p RPCS3_FOUND="Caminho: "
)

if exist "%RPCS3_FOUND%" (
  echo Copiando todas as {len(songs)} músicas do pacote para: %RPCS3_FOUND%\\songs
  xcopy /E /I /Y "USRDIR\\songs" "%RPCS3_FOUND%\\songs"
  echo.
  echo [SUCESSO TOTAL!] O Mega Pacote com {len(songs)} músicas foi instalado com sucesso!
  echo Abra o Rock Band 3 e todas as músicas estarão disponíveis na sua biblioteca!
) else (
  echo Pasta do emulador não encontrada.
)
pause
"""
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)

    return pack_root

def compile_clone_hero_pack(
    songs: List[ChartSong],
    pack_name: str,
    output_base_dir: str
) -> str:
    """
    Compila todas as músicas em uma pasta única para colar na pasta Songs do Clone Hero.
    """
    clean_pack_name = "".join(c for c in pack_name if c.isalnum() or c in " _-").strip() or "MegaPack_CH"
    pack_root = os.path.join(output_base_dir, clean_pack_name)
    os.makedirs(pack_root, exist_ok=True)

    from src.creator.clonehero_exporter import export_clone_hero_song
    for s in songs:
        export_clone_hero_song(s, pack_root)

    return pack_root
