"""
Exportador de Pacotes PS3 / RPCS3 para Rock Band 3.
Gera a estrutura completa de DLC para PS3 e Emulador RPCS3:
- BLUS30463_00-CUSTOM/
  - PARAM.SFO (arquivo de metadados binário oficial do PS3)
  - ICON0.PNG (capa do álbum formatada para a XMB do PS3 e RPCS3)
  - USRDIR/
    - songs/
      - songs.dta
      - {shortname}/{shortname}.mid
  - package.conf (configuração para ferramentas de empacotamento PKG)
  - INSTALAR_NO_RPCS3.bat (script automático de 1 clique para instalar no emulador)
  - COMO_INSTALAR_NO_PS3.txt (passo a passo para console real e emulador)
"""

import os
import struct
import shutil
import hashlib
from PIL import Image
from src.creator.chart_model import ChartSong
from src.creator.rb3_dta_exporter import generate_songs_dta_content
from src.creator.midi_generator import generate_rbn_midi, save_midi

def generate_param_sfo(title: str, content_id: str, title_id: str = "BLUS30463") -> bytes:
    """
    Gera um arquivo binário PARAM.SFO compatível com PS3 e RPCS3.
    """
    entries = [
        ("CATEGORY", "DG", 0x0204),
        ("CONTENT_ID", content_id, 0x0204),
        ("TITLE", title[:127], 0x0204),
        ("TITLE_ID", title_id, 0x0204),
        ("VERSION", "01.00", 0x0204),
    ]
    # SFO Header: magic (\x00PSF), version 1.1, key_table_offset, data_table_offset, entries_count
    num_entries = len(entries)
    entry_table_size = num_entries * 16
    header_size = 20
    
    # Monta a key table
    key_table = bytearray()
    key_offsets = []
    for k, _, _ in entries:
        key_offsets.append(len(key_table))
        key_table.extend(k.encode('utf-8') + b'\x00')
    
    # Alinhamento da key table
    key_table_offset = header_size + entry_table_size
    data_table_offset = key_table_offset + len(key_table)
    # Alinha a 4 bytes
    if data_table_offset % 4 != 0:
        padding = 4 - (data_table_offset % 4)
        key_table.extend(b'\x00' * padding)
        data_table_offset += padding

    # Monta a data table
    data_table = bytearray()
    entry_records = []
    for i, (k, val, fmt) in enumerate(entries):
        val_bytes = val.encode('utf-8') + b'\x00'
        data_len = len(val_bytes)
        max_len = ((data_len + 3) // 4) * 4
        # Pad data
        val_bytes = val_bytes.ljust(max_len, b'\x00')
        data_offset = len(data_table)
        data_table.extend(val_bytes)
        entry_records.append((key_offsets[i], fmt, data_len, max_len, data_offset))

    # Cria header
    header = struct.pack(
        "<4sIIII",
        b"\x00PSF",
        0x00000101,
        key_table_offset,
        data_table_offset,
        num_entries
    )

    # Cria tabela de entradas
    entries_bytes = bytearray()
    for k_off, fmt, d_len, m_len, d_off in entry_records:
        entries_bytes.extend(struct.pack("<HHIII", k_off, fmt, d_len, m_len, d_off))

    return header + entries_bytes + bytes(key_table) + bytes(data_table)


def export_ps3_pkg_structure(song: ChartSong, output_base_dir: str, audio_source_path: str = None, total_duration_ms: int = 180000) -> str:
    """
    Gera a pasta completa no padrão PS3 / RPCS3 pronta para empacotar ou copiar diretamente.
    """
    clean_shortname = "".join(c for c in f"{song.artist}_{song.title}" if c.isalnum()).lower()[:24] or "custom_song"
    hash_id = hashlib.md5(clean_shortname.encode()).hexdigest().upper()[:8]
    content_id = f"UP0006-BLUS30463_00-MG{hash_id}00001"
    
    pkg_folder_name = f"PS3_RPCS3_{clean_shortname}"
    root_dir = os.path.join(output_base_dir, pkg_folder_name)
    usrdir = os.path.join(root_dir, "USRDIR")
    songs_dir = os.path.join(usrdir, "songs")
    track_dir = os.path.join(songs_dir, clean_shortname)
    os.makedirs(track_dir, exist_ok=True)

    # 1. Gera PARAM.SFO
    sfo_path = os.path.join(root_dir, "PARAM.SFO")
    sfo_bytes = generate_param_sfo(f"RB3: {song.title} - {song.artist}", content_id)
    with open(sfo_path, "wb") as f:
        f.write(sfo_bytes)

    # 2. Gera ICON0.PNG (320x176 - proporção clássica do PS3)
    icon_path = os.path.join(root_dir, "ICON0.PNG")
    if song.album_art_path and os.path.exists(song.album_art_path):
        try:
            im = Image.open(song.album_art_path).convert("RGBA")
            im = im.resize((320, 176), Image.Resampling.LANCZOS)
            im.save(icon_path, "PNG")
        except Exception as e:
            print(f"[PS3Exporter] Erro ao redimensionar capa: {e}")
            _create_default_icon(icon_path, song.title, song.artist)
    else:
        _create_default_icon(icon_path, song.title, song.artist)

    # 3. Gera songs.dta
    dta_content = generate_songs_dta_content(song, clean_shortname)
    dta_path = os.path.join(songs_dir, "songs.dta")
    with open(dta_path, "w", encoding="utf-8") as f:
        f.write(dta_content)

    # 4. Gera {shortname}.mid
    mid = generate_rbn_midi(song, total_duration_ms=total_duration_ms)
    mid_path = os.path.join(track_dir, f"{clean_shortname}.mid")
    save_midi(mid, mid_path)

    # 4.1 Gera o container oficial .mogg (0x0A) e copia os arquivos de áudio para a pasta da música no PS3
    from src.creator.mogg_generator import create_unencrypted_mogg
    primary_audio = audio_source_path or song.audio_path or (song.audio_stems[0] if song.audio_stems else None)
    if primary_audio and os.path.exists(primary_audio):
        mogg_dest = os.path.join(track_dir, f"{clean_shortname}.mogg")
        create_unencrypted_mogg(primary_audio, mogg_dest)

    if song.audio_stems:
        for stem_p in song.audio_stems:
            if os.path.exists(stem_p):
                fname = os.path.basename(stem_p)
                dest_p = os.path.join(track_dir, fname)
                try:
                    shutil.copy2(stem_p, dest_p)
                except Exception as e:
                    print(f"[PS3Exporter] Erro ao copiar stem {fname}: {e}")
    elif song.audio_path and os.path.exists(song.audio_path):
        ext = os.path.splitext(song.audio_path)[1].lower()
        dest_audio = os.path.join(track_dir, f"{clean_shortname}{ext}")
        try:
            shutil.copy2(song.audio_path, dest_audio)
        except Exception as e:
            print(f"[PS3Exporter] Erro ao copiar áudio: {e}")

    # 5. Gera package.conf (para ferramentas que compilam PKG como make_package_npdrm)
    conf_path = os.path.join(root_dir, "package.conf")
    conf_content = f"""Content-ID = {content_id}
k_licensee = 0x00000000000000000000000000000000
DRMType = Free
ContentType = GameExec
PackageVersion = 01.00
"""
    with open(conf_path, "w", encoding="utf-8") as f:
        f.write(conf_content)

    # 6. Gera script de instalação em 1 clique para o RPCS3
    bat_path = os.path.join(root_dir, "INSTALAR_NO_RPCS3_AUTOMATICO.bat")
    bat_content = f"""@echo off
chcp 65001 > nul
echo ============================================================
echo   MidGuitar - Instalador de Músicas no RPCS3 (Rock Band 3)
echo ============================================================
echo.
echo Procurando a pasta do RPCS3 nas pastas usuais...
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
  echo Não encontrou o RPCS3 automaticamente.
  echo Por favor, digite ou cole o caminho da pasta dev_hdd0\\game\\BLUS30463\\USRDIR do seu RPCS3:
  set /p RPCS3_FOUND="Caminho: "
)

if exist "%RPCS3_FOUND%" (
  echo Copiando músicas para: %RPCS3_FOUND%\\songs
  xcopy /E /I /Y "USRDIR\\songs" "%RPCS3_FOUND%\\songs"
  echo.
  echo [SUCESSO!] Música {song.title} instalada com sucesso no RPCS3!
  echo Abra o Rock Band 3 e aproveite!
) else (
  echo Pasta não encontrada. Verifique se o jogo Rock Band 3 (BLUS30463) está instalado no emulador.
)
pause
"""
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)

    # 7. Instruções detalhadas
    info_path = os.path.join(root_dir, "COMO_USAR_NO_PS3_E_RPCS3.txt")
    info_content = f"""======================================================================
  MidGuitar Universal Studio - Pacote Rock Band 3 (PS3 & RPCS3)
  Música: {song.title}
  Artista: {song.artist}
  Content-ID: {content_id}
======================================================================

OPÇÃO 1: INSTALAR NO EMULADOR RPCS3 (MUITO FÁCIL)
----------------------------------------------------------------------
1. Você pode simplesmente dar dois cliques no arquivo:
   'INSTALAR_NO_RPCS3_AUTOMATICO.bat' que criamos nesta pasta!
OU
2. Copie manualmente a pasta 'USRDIR\\songs' desta pasta para:
   [Sua Pasta RPCS3]\\dev_hdd0\\game\\BLUS30463\\USRDIR\\songs\\

Ao abrir o Rock Band 3 no emulador, a música aparecerá imediatamente na lista!


OPÇÃO 2: INSTALAR NO CONSOLE PLAYSTATION 3 REAL (CFW / HEN)
----------------------------------------------------------------------
Método A (Mais Rápido por FTP ou Pendrive / multiMAN):
1. Conecte no seu PS3 via FTP (FileZilla) ou use o Gerenciador de Arquivos do multiMAN.
2. Copie os arquivos de 'USRDIR/songs/' para:
   /dev_hdd0/game/BLUS30463/USRDIR/songs/

Método B (Gerar arquivo .PKG direto):
1. Use qualquer empacotador comum de PKG (como 'make_package_npdrm' ou 'TrueAncestor PKG Repacker').
2. Esta pasta já possui o 'PARAM.SFO', 'ICON0.PNG' e 'package.conf' 100% configurados!
3. O instalador gera o arquivo .pkg para instalar pelo menu 'Package Manager' da XMB.

======================================================================
Gerado com amor pelo MidGuitar Universal Studio!
======================================================================
"""
    with open(info_path, "w", encoding="utf-8") as f:
        f.write(info_content)

    return root_dir


def _create_default_icon(path: str, title: str, artist: str):
    """Cria um ícone padrão bonito caso não haja imagem de capa."""
    try:
        from PIL import ImageDraw, ImageFont
        im = Image.new("RGBA", (320, 176), color=(24, 28, 36, 255))
        draw = ImageDraw.Draw(im)
        # Borda decorativa
        draw.rectangle([(2, 2), (317, 173)], outline=(0, 200, 255), width=2)
        draw.rectangle([(6, 6), (313, 169)], outline=(30, 40, 55), width=1)
        # Texto
        draw.text((20, 35), "ROCK BAND 3 CUSTOM", fill=(0, 220, 255))
        draw.text((20, 65), title[:25], fill=(255, 255, 255))
        draw.text((20, 95), artist[:28], fill=(180, 180, 180))
        draw.text((20, 135), "⚡ MidGuitar Universal Studio", fill=(100, 255, 100))
        im.save(path, "PNG")
    except Exception:
        pass
