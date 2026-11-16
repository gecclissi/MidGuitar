"""
Exportador de Pacotes PS3 / RPCS3 para Rock Band 3.
Gera a estrutura de DLC no mesmo layout dos pacotes PS3 reais (Magma C3):
- PS3_RPCS3_<shortname>/
  - <shortname>.pkg (pacote de debug instalável no RPCS3 e no PS3 com HEN/CFW)
  - PARAM.SFO (mesmos campos das referências: CATEGORY GD, PARENTAL_LEVEL,
    PS3_SYSTEM_VER, TITLE, TITLE_ID BLUS30463, VERSION)
  - ICON0.PNG (320x176 RGB)
  - USRDIR/<pasta única>/songs/songs.dta
  - USRDIR/<pasta única>/songs/{shortname}/{shortname}.mid.edat / .mogg / gen/{shortname}_keep.png_ps3
  - package.conf (configuração para ferramentas de empacotamento PKG)
  - INSTALAR_NO_RPCS3_AUTOMATICO.bat (copia USRDIR/<pasta> para dev_hdd0/game/BLUS30463/USRDIR/)
  - COMO_USAR_NO_PS3_E_RPCS3.txt

Cada música (ou pacote) usa a sua própria pasta em USRDIR/, então instalar uma
segunda música não sobrescreve o songs.dta da primeira.
"""

import os
import struct
from PIL import Image
from src.creator.chart_model import ChartSong
from src.creator.edat import rb3_content_id
from src.creator.ps3_pkg import build_pkg
from src.creator.rb3_dta_exporter import (RB3_PS3_TITLE_ID, ps3_folder_name, song_shortname,
                                          stable_song_id, write_rb3_song_files, write_songs_dta)

# Campos do PARAM.SFO como nos pacotes reais (iguais nas duas referências)
SFO_CATEGORY = "GD"            # Game Data (dados extras do jogo)
SFO_PARENTAL_LEVEL = 5
SFO_PS3_SYSTEM_VER = "03.3000"
SFO_VERSION = "01.00"
SFO_TITLE_MAX = 128


def _sfo_utf8(value: str, max_len: int) -> bytes:
    """Texto UTF-8 terminado em zero, cortado sem quebrar caracteres multibyte."""
    raw = (value or "").encode("utf-8")[:max_len - 1]
    while raw:
        try:
            raw.decode("utf-8")
            break
        except UnicodeDecodeError:
            raw = raw[:-1]
    return raw + b"\x00"


def generate_param_sfo(title: str, content_id: str = None, title_id: str = RB3_PS3_TITLE_ID) -> bytes:
    """
    Gera um PARAM.SFO de dados de jogo (GD) igual ao dos pacotes PS3 reais do Rock Band.
    Com title="Rock Band 3" o resultado é idêntico byte a byte às referências.
    content_id é aceito por compatibilidade, mas não vai no SFO (os pacotes reais não
    o têm; ele é usado no package.conf / .pkg).
    """
    # (chave, formato, bytes, tamanho máximo); 0x0204 = texto UTF-8, 0x0404 = inteiro
    entries = [
        ("CATEGORY", 0x0204, _sfo_utf8(SFO_CATEGORY, 4), 4),
        ("PARENTAL_LEVEL", 0x0404, struct.pack("<I", SFO_PARENTAL_LEVEL), 4),
        ("PS3_SYSTEM_VER", 0x0204, _sfo_utf8(SFO_PS3_SYSTEM_VER, 8), 8),
        ("TITLE", 0x0204, _sfo_utf8(title, SFO_TITLE_MAX), SFO_TITLE_MAX),
        ("TITLE_ID", 0x0204, _sfo_utf8(title_id, 16), 16),
        ("VERSION", 0x0204, _sfo_utf8(SFO_VERSION, 8), 8),
    ]
    header_size = 20
    key_table = bytearray()
    key_offsets = []
    for key, _fmt, _data, _max in entries:
        key_offsets.append(len(key_table))
        key_table.extend(key.encode("ascii") + b"\x00")
    key_table_offset = header_size + 16 * len(entries)
    while (key_table_offset + len(key_table)) % 4:
        key_table.append(0)
    data_table_offset = key_table_offset + len(key_table)

    data_table = bytearray()
    records = bytearray()
    for (_key, fmt, data, max_len), k_off in zip(entries, key_offsets):
        records.extend(struct.pack("<HHIII", k_off, fmt, len(data), max_len, len(data_table)))
        data_table.extend(data.ljust(max_len, b"\x00"))

    header = struct.pack("<4sIIII", b"\x00PSF", 0x00000101, key_table_offset,
                         data_table_offset, len(entries))
    return header + bytes(records) + bytes(key_table) + bytes(data_table)


def save_icon0(path: str, art_path: str = None, title: str = "", subtitle: str = ""):
    """ICON0.PNG 320x176 RGB (como nas referências), da capa ou do ícone padrão."""
    if art_path and os.path.exists(art_path):
        try:
            im = Image.open(art_path).convert("RGB")
            im = im.resize((320, 176), Image.Resampling.LANCZOS)
            im.save(path, "PNG")
            return
        except Exception as e:
            print(f"[PS3Exporter] Erro ao redimensionar capa: {e}")
    _create_default_icon(path, title, subtitle)


def rpcs3_install_bat(folder: str, title_id: str, label: str) -> str:
    """Script .bat que copia USRDIR\\<pasta> para dev_hdd0\\game\\<title_id>\\USRDIR\\<pasta>."""
    return rf"""@echo off
chcp 65001 > nul
echo ============================================================
echo   MidGuitar - Instalador no RPCS3 ({title_id})
echo   {label}
echo ============================================================
echo.
echo Procurando a pasta do RPCS3 nas pastas usuais...
set "RPCS3_FOUND="

for %%D in (
  "%USERPROFILE%\Desktop\rpcs3"
  "%USERPROFILE%\Downloads\rpcs3"
  "C:\rpcs3"
  "D:\rpcs3"
  "E:\rpcs3"
  "%APPDATA%\rpcs3"
) do (
  if exist "%%~D\dev_hdd0\game\{title_id}\USRDIR" (
    set "RPCS3_FOUND=%%~D\dev_hdd0\game\{title_id}\USRDIR"
  )
)

if not defined RPCS3_FOUND (
  echo Não encontrou o RPCS3 automaticamente.
  echo Digite ou cole o caminho da pasta dev_hdd0\game\{title_id}\USRDIR do seu RPCS3:
  set /p RPCS3_FOUND="Caminho: "
)

if exist "%RPCS3_FOUND%" (
  echo Copiando para: %RPCS3_FOUND%\{folder}
  xcopy /E /I /Y "%~dp0USRDIR\{folder}" "%RPCS3_FOUND%\{folder}"
  echo.
  echo [SUCESSO!] Instalado em %RPCS3_FOUND%\{folder}
  echo Abra o jogo e aproveite!
) else (
  echo Pasta não encontrada. Verifique se o jogo ({title_id}) está instalado no emulador.
)
pause
"""


def write_install_bat(path: str, folder: str, title_id: str, label: str):
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(rpcs3_install_bat(folder, title_id, label))


# Itens da raiz que vão para o .pkg (o resto é só para quem copia a pasta à mão)
PKG_ROOT_ITEMS = ["ICON0.PNG", "PARAM.SFO", "USRDIR"]


def build_ps3_package(root_dir: str, folder: str, pkg_name: str) -> str:
    """Gera <root_dir>/<pkg_name>.pkg com PARAM.SFO, ICON0.PNG e USRDIR/<folder>."""
    pkg_path = os.path.join(root_dir, pkg_name + ".pkg")
    build_pkg(root_dir, pkg_path, rb3_content_id(folder), include=PKG_ROOT_ITEMS)
    return pkg_path


def package_conf(content_id: str) -> str:
    return f"""Content-ID = {content_id}
k_licensee = 0x00000000000000000000000000000000
DRMType = Free
ContentType = GameData
PackageVersion = 01.00
"""


def export_ps3_pkg_structure(song: ChartSong, output_base_dir: str, audio_source_path: str = None, total_duration_ms: int = 180000) -> str:
    """
    Gera a pasta completa no padrão PS3 / RPCS3 pronta para empacotar ou copiar diretamente.
    """
    clean_shortname = song_shortname(song)
    song_id = stable_song_id(song)
    folder = ps3_folder_name(clean_shortname, song_id)
    # Como nas referências: o content id do .pkg e do .mid.edat é o prefixo do RB3 + a pasta
    content_id = rb3_content_id(folder)

    root_dir = os.path.join(output_base_dir, f"PS3_RPCS3_{clean_shortname}")
    songs_dir = os.path.join(root_dir, "USRDIR", folder, "songs")
    os.makedirs(songs_dir, exist_ok=True)

    # 1. PARAM.SFO e ICON0.PNG
    with open(os.path.join(root_dir, "PARAM.SFO"), "wb") as f:
        f.write(generate_param_sfo(f"RB3: {song.title} - {song.artist}", content_id))
    save_icon0(os.path.join(root_dir, "ICON0.PNG"), song.album_art_path, song.title, song.artist)

    # 2. Música: .mid.edat, .mogg (multicanal), capa png_ps3 e songs.dta
    dta_content, _layout = write_rb3_song_files(song, songs_dir, clean_shortname, song_id=song_id,
                                                audio_source_path=audio_source_path,
                                                total_duration_ms=total_duration_ms,
                                                edat_folder=folder)
    write_songs_dta(os.path.join(songs_dir, "songs.dta"), [dta_content])

    # 2.1 Pacote .pkg pronto para instalar
    pkg_path = build_ps3_package(root_dir, folder, clean_shortname)

    # 3. package.conf (ferramentas que compilam PKG, como make_package_npdrm)
    with open(os.path.join(root_dir, "package.conf"), "w", encoding="utf-8", newline="\n") as f:
        f.write(package_conf(content_id))

    # 4. Instalador de 1 clique para o RPCS3
    write_install_bat(os.path.join(root_dir, "INSTALAR_NO_RPCS3_AUTOMATICO.bat"), folder,
                      RB3_PS3_TITLE_ID, f"Música: {song.title} - {song.artist}")

    # 5. Instruções detalhadas
    info_path = os.path.join(root_dir, "COMO_USAR_NO_PS3_E_RPCS3.txt")
    info_content = f"""======================================================================
  MidGuitar Universal Studio - Pacote Rock Band 3 (PS3 & RPCS3)
  Música: {song.title}
  Artista: {song.artist}
  Content-ID: {content_id}
======================================================================

OPÇÃO 1: INSTALAR O .PKG (MAIS FÁCIL)
----------------------------------------------------------------------
- RPCS3: menu File > Install Packages/Raps/Edats e escolha
  '{os.path.basename(pkg_path)}'.
- PS3 com HEN/CFW: copie '{os.path.basename(pkg_path)}' para a raiz de um pendrive
  (FAT32) e instale pelo Package Manager > Install Package Files.

OPÇÃO 2: COPIAR A PASTA À MÃO
----------------------------------------------------------------------
- RPCS3: dê dois cliques em 'INSTALAR_NO_RPCS3_AUTOMATICO.bat' ou copie a pasta
  'USRDIR/{folder}' para:
  [Sua Pasta RPCS3]/dev_hdd0/game/{RB3_PS3_TITLE_ID}/USRDIR/{folder}/
- PS3 (CFW / HEN): via FTP ou multiMAN, copie 'USRDIR/{folder}' para:
  /dev_hdd0/game/{RB3_PS3_TITLE_ID}/USRDIR/{folder}/

Cada música fica na própria pasta: instalar outra não apaga esta.
Não renomeie a pasta '{folder}': o .mid.edat é cifrado com uma chave
derivada desse nome e deixa de abrir se ela mudar.

Observação: o arquivo gen/{clean_shortname}.milo_ps3 (animações de palco)
ainda não é gerado; o jogo usa as animações padrão.
======================================================================
"""
    with open(info_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(info_content)

    return root_dir


def _create_default_icon(path: str, title: str, artist: str):
    """Cria um ícone padrão (320x176 RGB) caso não haja imagem de capa."""
    try:
        from PIL import ImageDraw
        im = Image.new("RGB", (320, 176), color=(24, 28, 36))
        draw = ImageDraw.Draw(im)
        # Borda decorativa
        draw.rectangle([(2, 2), (317, 173)], outline=(0, 200, 255), width=2)
        draw.rectangle([(6, 6), (313, 169)], outline=(30, 40, 55), width=1)
        # Texto
        draw.text((20, 35), "ROCK BAND 3 CUSTOM", fill=(0, 220, 255))
        draw.text((20, 65), (title or "")[:25], fill=(255, 255, 255))
        draw.text((20, 95), (artist or "")[:28], fill=(180, 180, 180))
        draw.text((20, 135), "MidGuitar Universal Studio", fill=(100, 255, 100))
        im.save(path, "PNG")
    except Exception:
        pass
