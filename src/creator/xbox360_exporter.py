"""
Exportador de Músicas para Xbox 360 (Rock Band 3 / RGH / JTAG / Xenia).

Gera um pacote CON (STFS) no mesmo formato dos customs feitos pelo Onyx e pelo C3 CON
Tools (conferido byte a byte com uma CON real do Onyx):
- XBOX360_RB3_<shortname>/
  - <shortname>_rb3con: pacote CON assinado com o KV do Onyx/C3 (title id 45410914,
    tipo "Saved Game", nome "Artista - Título", miniatura 64x64 da capa), contendo:
      songs/songs.dta (o mesmo songs.dta do PS3)
      songs/<s>/<s>.mid (MIDI sem cifra)
      songs/<s>/<s>.mogg (0x0A sem cifra, multicanal com stems, ou o original importado)
      songs/<s>/gen/<s>_keep.png_xbox (capa DXT1)
    (sem .milo_xbox: o jogo usa as animações automáticas)
  - COMO_INSTALAR_NO_XBOX360.txt

Não verificado em console/Xenia (o dono não tem como testar): a assinatura é a mesma
das CONs de referência, que funcionam em consoles destravados (RGH/JTAG) e no Xenia.
"""

import io
import os
import shutil
import tempfile

from src.creator.chart_model import ChartSong
from src.creator.rb3_dta_exporter import song_shortname, write_rb3_song_files, write_songs_dta
from src.creator.xbox_stfs import RB3_TITLE_ID, build_con

XBOX360_RB3_TITLE_ID = "45410914"  # Title ID oficial do Rock Band 3 no Xbox 360
# Pasta dos pacotes CON ("Saved Game" = 00000001) do RB3 no HD do Xbox / no Xenia
XBOX360_CON_CONTENT_DIR = "Content/0000000000000000/45410914/00000001"
CON_SUFFIX = "_rb3con"
_THUMB_SIZE = 64


def con_display_name(song: ChartSong) -> str:
    artist = (song.artist or "").strip()
    title = (song.title or "").strip() or "Música"
    return "%s - %s" % (artist, title) if artist else title


def con_thumbnail(song: ChartSong) -> bytes:
    """Miniatura PNG 64x64 (RGB) do pacote, da capa da música ou da capa padrão."""
    from PIL import Image
    src = song.album_art_path if song.album_art_path and os.path.exists(song.album_art_path) else None
    tmp = None
    try:
        if src is None:
            from src.creator.clonehero_exporter import _create_default_album_art
            fd, tmp = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            _create_default_album_art(tmp, song.title, song.artist)
            src = tmp
        with Image.open(src) as im:
            thumb = im.convert("RGB").resize((_THUMB_SIZE, _THUMB_SIZE), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        thumb.save(buf, "PNG", optimize=True)
        return buf.getvalue()
    except Exception as e:
        print("[Xbox360Exporter] Miniatura não gerada: %s" % e)
        return b""
    finally:
        if tmp:
            try:
                os.remove(tmp)
            except OSError:
                pass


def build_xbox_song_tree(song: ChartSong, stage_dir: str, shortname: str,
                         total_duration_ms: int = 180000) -> str:
    """Grava songs/ (songs.dta, .mid, .mogg, gen/_keep.png_xbox) em `stage_dir`."""
    songs_dir = os.path.join(stage_dir, "songs")
    os.makedirs(songs_dir, exist_ok=True)
    dta_content, _layout = write_rb3_song_files(song, songs_dir, shortname,
                                                total_duration_ms=total_duration_ms,
                                                with_art=True, art_format="xbox")
    write_songs_dta(os.path.join(songs_dir, "songs.dta"), [dta_content])
    return songs_dir


def export_xbox360_structure(song: ChartSong, output_base_dir: str, total_duration_ms: int = 180000) -> str:
    """
    Exporta a música como pacote CON do Rock Band 3 para Xbox 360.
    Devolve a pasta XBOX360_RB3_<shortname> com o arquivo <shortname>_rb3con.
    """
    clean_shortname = song_shortname(song)
    folder_name = f"XBOX360_RB3_{clean_shortname}"
    root_dir = os.path.join(output_base_dir, folder_name)
    os.makedirs(root_dir, exist_ok=True)
    con_name = clean_shortname + CON_SUFFIX
    con_path = os.path.join(root_dir, con_name)

    stage = tempfile.mkdtemp(prefix="mg_xbox_")
    try:
        build_xbox_song_tree(song, stage, clean_shortname, total_duration_ms)
        build_con(stage, con_path, con_display_name(song),
                  "Criado com o MidGuitar", title_id=RB3_TITLE_ID, title_name="Rock Band 3",
                  thumbnail=con_thumbnail(song))
    finally:
        shutil.rmtree(stage, ignore_errors=True)

    content_win = XBOX360_CON_CONTENT_DIR.replace("/", "\\")
    readme_path = os.path.join(root_dir, "COMO_INSTALAR_NO_XBOX360.txt")
    readme_content = f"""========================================================================
MIDGUITAR - GUIA DE INSTALAÇÃO NO XBOX 360 (ROCK BAND 3)
Música: {song.title} - {song.artist}
Pacote: {con_name} (CON, Title ID do Rock Band 3: {XBOX360_RB3_TITLE_ID})
========================================================================

O arquivo '{con_name}' é um pacote CON igual aos customs do Onyx / C3 CON
Tools. Ele precisa de um Xbox 360 destravado (RGH/JTAG) ou do emulador Xenia.
O Rock Band 3 precisa estar atualizado (Title Update 5) para ler customs.

------------------------------------------------------------------------
OPÇÃO 1: XBOX 360 DESTRAVADO (RGH / JTAG)
------------------------------------------------------------------------
1. Copie '{con_name}' para:
   Hdd1:\\{content_win}\\
   (pelo FTP do Aurora/FreeStyle ou por um pendrive com o Horizon/FATXplorer).
2. Inicie o Rock Band 3: a música aparece na lista.

------------------------------------------------------------------------
OPÇÃO 2: PENDRIVE FORMATADO NO XBOX 360 (HORIZON / FATXPLORER)
------------------------------------------------------------------------
1. Formate um pendrive no Xbox 360 (Configurações > Armazenamento).
2. No PC, abra o Horizon ou o FATXplorer e injete o arquivo '{con_name}'
   (o programa coloca o pacote na pasta {content_win}).
3. Conecte o pendrive no console destravado e abra o Rock Band 3.

------------------------------------------------------------------------
OPÇÃO 3: EMULADOR XENIA NO COMPUTADOR (PC)
------------------------------------------------------------------------
1. No Xenia Canary, use File > Install Content e escolha '{con_name}'.
2. Abra o Rock Band 3 no Xenia.

Observação: o pacote ainda não foi testado em console nem no Xenia pelo
MidGuitar; o formato e a assinatura são os mesmos das CONs do Onyx.
========================================================================
"""
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

    return root_dir
