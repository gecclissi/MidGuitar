"""
Exportador Oficial para Rock Band 2 (PS3 / RPCS3 BLUS30147, Xbox 360 45410869 e Rock Band 2 Deluxe).
Gera a estrutura de arquivos e diretórios com especificações nativas da engine do Rock Band 2:
- songs.dta (format 4, version 1, game_origin rb2, sem blocos de teclado para não travar o RB2)
- {shortname}.mid (MIDI RBN compatível com RB2)
- {shortname}.mogg (Container de áudio multicanal Harmonix 0x0A)
- PARAM.SFO e ICON0.PNG para PlayStation 3 / RPCS3 (Title ID: BLUS30147)
- Content/0000000000000000/45410869/00000002/ para Xbox 360 (Title ID: 45410869)
- INSTALAR_NO_RB2_RPCS3.bat (Instalador automático de 1 clique para RPCS3)
"""

import os
import shutil
import hashlib
from PIL import Image
from src.creator.chart_model import ChartSong
from src.creator.midi_generator import generate_rbn_midi, save_midi
from src.creator.ps3_pkg_exporter import generate_param_sfo, _create_default_icon
from src.creator.mogg_generator import create_unencrypted_mogg

RB2_PS3_TITLE_ID = "BLUS30147"      # Title ID oficial do Rock Band 2 no PS3
RB2_XBOX360_TITLE_ID = "45410869"   # Title ID oficial do Rock Band 2 no Xbox 360


def generate_rb2_songs_dta_content(song: ChartSong, shortname: str, song_id: int = None) -> str:
    """
    Gera o arquivo songs.dta estritamente no padrão da engine do Rock Band 2:
    - (format 4) e (version 1)
    - (game_origin rb2)
    - Sem referências a 'keys' em (tracks ...) para total compatibilidade com RB2 original e RB2 Deluxe.
    """
    if song_id is None:
        hash_val = int(hashlib.md5(f"rb2_{song.artist}_{song.title}".encode()).hexdigest()[:6], 16)
        song_id = 1005000 + (hash_val % 900000)

    def rank_to_dta(val: int, has_notes: bool) -> int:
        if not has_notes:
            return 0
        return max(50, min(500, val * 60 + 50))

    has_vocals = len(song.vocal_notes) > 0
    has_guitar = len(song.guitar_notes) > 0
    has_bass = len(song.bass_notes) > 0
    has_drums = len(song.drum_notes) > 0
    vocal_parts_count = 1 if has_vocals else 0

    tracks_dta = """((guitar (0 1))
          (bass (0 1))
          (drum (0 1))
          (vocals (0 1))
         )"""
    pans_dta = "(-1.0 1.0)"
    vols_dta = "(-1.5 -1.5)"
    cores_dta = "(-1 -1)"

    dta = f"""({shortname}
   (name "{song.title}")
   (artist "{song.artist}")
   (master TRUE)
   (context 2000)
   (song
      (name "songs/{shortname}/{shortname}")
      (tracks
         {tracks_dta}
      )
      (vocal_parts {vocal_parts_count})
      (pans {pans_dta})
      (vols {vols_dta})
      (cores {cores_dta})
      (drum_solo
         (seqs (kick.cue snare.cue tom1.cue tom2.cue crash.cue))
      )
      (drum_freestyle
         (seqs (kick.cue snare.cue hat.cue ride.cue crash.cue))
      )
      (midi_file "songs/{shortname}/{shortname}.mid")
   )
   (song_scroll_speed 2300)
   (bank "sfx/tambourine_bank.milo")
   (anim_tempo kTempoMedium)
   (preview {song.preview_start_ms} {song.preview_start_ms + 30000})
   (rank
      (drum {rank_to_dta(song.diff_drums, has_drums)})
      (guitar {rank_to_dta(song.diff_guitar, has_guitar)})
      (bass {rank_to_dta(song.diff_bass, has_bass)})
      (vocals {rank_to_dta(song.diff_vocals, has_vocals)})
      (band {rank_to_dta(song.diff_band, any([has_drums, has_guitar, has_bass, has_vocals]))})
   )
   (genre "{song.genre.lower()}")
   (decade the10s)
   (vocal_gender male)
   (format 4)
   (version 1)
   (fake FALSE)
   (downloaded TRUE)
   (game_origin rb2)
   (song_id {song_id})
   (rating 2)
   (short_version 0)
   (album_art TRUE)
   (year_released {song.year})
   (album_name "{song.album}")
   (album_track_number 1)
   (base_points 500000)
)
"""
    return dta


def export_rb2_song_package(song: ChartSong, output_base_dir: str, audio_source_path: str = None, total_duration_ms: int = 180000) -> str:
    """
    Exporta um pacote híbrido completo para Rock Band 2 (PS3 BLUS30147, RPCS3, Xbox 360 45410869 e RB2 Deluxe).
    """
    clean_shortname = "".join(c for c in f"{song.artist}_{song.title}" if c.isalnum()).lower()[:24] or "custom_rb2"
    hash_id = hashlib.md5(clean_shortname.encode()).hexdigest().upper()[:8]
    content_id = f"UP0006-{RB2_PS3_TITLE_ID}_00-MG{hash_id}00001"

    root_dir = os.path.join(output_base_dir, f"RB2_{clean_shortname}")
    usrdir = os.path.join(root_dir, "USRDIR")
    songs_dir = os.path.join(usrdir, "songs")
    track_dir = os.path.join(songs_dir, clean_shortname)
    os.makedirs(track_dir, exist_ok=True)

    # Estrutura Xbox 360 para Rock Band 2 (Title ID 45410869)
    x360_content_dir = os.path.join(root_dir, "Xbox360_Content", "0000000000000000", RB2_XBOX360_TITLE_ID, "00000002", clean_shortname)
    os.makedirs(x360_content_dir, exist_ok=True)

    # 1. PARAM.SFO oficial para PS3 Rock Band 2 (BLUS30147)
    sfo_path = os.path.join(root_dir, "PARAM.SFO")
    sfo_bytes = generate_param_sfo(f"RB2: {song.title} - {song.artist}", content_id, title_id=RB2_PS3_TITLE_ID)
    with open(sfo_path, "wb") as f:
        f.write(sfo_bytes)

    # 2. ICON0.PNG
    icon_path = os.path.join(root_dir, "ICON0.PNG")
    if song.album_art_path and os.path.exists(song.album_art_path):
        try:
            im = Image.open(song.album_art_path).convert("RGBA")
            im = im.resize((320, 176), Image.Resampling.LANCZOS)
            im.save(icon_path, "PNG")
        except Exception:
            _create_default_icon(icon_path, song.title, song.artist)
    else:
        _create_default_icon(icon_path, song.title, song.artist)

    # 3. Gera songs.dta específico do Rock Band 2 (format 4, version 1)
    dta_content = generate_rb2_songs_dta_content(song, clean_shortname)
    dta_path = os.path.join(songs_dir, "songs.dta")
    with open(dta_path, "w", encoding="utf-8") as f:
        f.write(dta_content)
    with open(os.path.join(x360_content_dir, "songs.dta"), "w", encoding="utf-8") as f:
        f.write(dta_content)

    # 4. Gera {shortname}.mid (com todas as 4 dificuldades)
    mid = generate_rbn_midi(song, total_duration_ms=total_duration_ms)
    mid_path = os.path.join(track_dir, f"{clean_shortname}.mid")
    save_midi(mid, mid_path)
    shutil.copy2(mid_path, os.path.join(x360_content_dir, f"{clean_shortname}.mid"))

    # 5. Gera {shortname}.mogg (Container oficial Harmonix 0x0A)
    primary_audio = audio_source_path or song.audio_path or (song.audio_stems[0] if song.audio_stems else None)
    if primary_audio and os.path.exists(primary_audio):
        mogg_dest = os.path.join(track_dir, f"{clean_shortname}.mogg")
        if create_unencrypted_mogg(primary_audio, mogg_dest):
            shutil.copy2(mogg_dest, os.path.join(x360_content_dir, f"{clean_shortname}.mogg"))

    # 6. Script automático de 1 clique para instalar no Rock Band 2 (RPCS3)
    bat_path = os.path.join(root_dir, "INSTALAR_NO_RB2_RPCS3.bat")
    bat_content = f"""@echo off
chcp 65001 > nul
echo ============================================================
echo   MidGuitar - Instalador Automático Rock Band 2 (RPCS3)
echo   Música: {song.title} - {song.artist}
echo ============================================================
echo.
set "RPCS3_RB2="
for %%D in (
  "%USERPROFILE%\\Desktop\\rpcs3"
  "%USERPROFILE%\\Downloads\\rpcs3"
  "C:\\rpcs3"
  "D:\\rpcs3"
  "E:\\rpcs3"
  "%APPDATA%\\rpcs3"
) do (
  if exist "%%~D\\dev_hdd0\\game\\{RB2_PS3_TITLE_ID}\\USRDIR" (
    set "RPCS3_RB2=%%~D\\dev_hdd0\\game\\{RB2_PS3_TITLE_ID}\\USRDIR"
  )
)

if not defined RPCS3_RB2 (
  echo Digite ou cole o caminho da pasta dev_hdd0\\game\\{RB2_PS3_TITLE_ID}\\USRDIR do seu RPCS3:
  set /p RPCS3_RB2="Caminho: "
)

if exist "%RPCS3_RB2%" (
  echo Copiando música para Rock Band 2: %RPCS3_RB2%\\songs
  xcopy /E /I /Y "USRDIR\\songs" "%RPCS3_RB2%\\songs"
  echo.
  echo [SUCESSO!] Música instalada no Rock Band 2 (BLUS30147)!
) else (
  echo Pasta não encontrada. Verifique se o Rock Band 2 ({RB2_PS3_TITLE_ID}) está instalado no RPCS3.
)
pause
"""
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)

    # 7. Guia passo a passo
    readme_path = os.path.join(root_dir, "COMO_INSTALAR_NO_ROCK_BAND_2.txt")
    readme_content = f"""========================================================================
  MidGuitar Universal Studio - Pacote Oficial ROCK BAND 2
  Música: {song.title} - {song.artist}
  PS3 Title ID: {RB2_PS3_TITLE_ID}  |  Xbox 360 Title ID: {RB2_XBOX360_TITLE_ID}
========================================================================

1. COMO JOGAR NO EMULADOR RPCS3 (PC - ROCK BAND 2 / RB2 DELUXE):
   - Dê dois cliques em 'INSTALAR_NO_RB2_RPCS3.bat' nesta pasta!
   - Ou copie a pasta 'USRDIR/songs' para:
     dev_hdd0/game/{RB2_PS3_TITLE_ID}/USRDIR/songs/

2. COMO JOGAR NO PLAYSTATION 3 REAL (HEN / CFW):
   - Envie a pasta 'USRDIR/songs' via FTP ou multiMAN para:
     /dev_hdd0/game/{RB2_PS3_TITLE_ID}/USRDIR/songs/

3. COMO JOGAR NO XBOX 360 (RGH / JTAG / XENIA):
   - Copie o conteúdo da pasta 'Xbox360_Content' para:
     Hdd1:\\Content\\0000000000000000\\{RB2_XBOX360_TITLE_ID}\\00000002\\
========================================================================
"""
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

    return root_dir
