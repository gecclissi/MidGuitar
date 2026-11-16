"""
Exportador EXPERIMENTAL e NÃO VERIFICADO para PlayStation 4 (Rock Band 4).
O RB4 usa formatos binários (.rbmid_ps4, .songdta_ps4, .moggsong, .png_ps4) que o
MidGuitar não gera (não há referência de PS4 para conferir): o resultado é só uma
estrutura de arquivos no estilo RB3 e AINDA NÃO TOCA no Rock Band 4. Estrutura gerada:
- songs/songs.dta
- songs/{shortname}/{shortname}.mid
- songs/{shortname}/{shortname}.mogg (multicanal, 44100 Hz)
- COMO_INSTALAR_NO_PS4.txt (guia passo a passo para consoles com GoldHEN / PS4 HEN)
"""

import os
import shutil
from src.creator.chart_model import ChartSong
from src.creator.rb3_dta_exporter import song_shortname, write_rb3_song_files, write_songs_dta

PS4_RB4_TITLE_ID = "CUSA02084" # Rock Band 4 US
PS4_RB4_RIVALS_ID = "CUSA02901" # Rock Band 4 Rivals

def export_ps4_structure(song: ChartSong, output_base_dir: str, total_duration_ms: int = 180000) -> str:
    """
    Exporta a música no padrão do PlayStation 4 para Rock Band 4 e YARG.
    """
    clean_shortname = song_shortname(song)
    folder_name = f"PS4_RB4_{clean_shortname}"
    root_dir = os.path.join(output_base_dir, folder_name)

    # 1. Diretórios do pacote PS4
    sce_dir = os.path.join(root_dir, "sce_sys")
    songs_dir = os.path.join(root_dir, "songs")
    track_dir = os.path.join(songs_dir, clean_shortname)
    os.makedirs(sce_dir, exist_ok=True)
    os.makedirs(track_dir, exist_ok=True)

    # 2. MIDI (só trilhas do Rock Band), .mogg multicanal e songs.dta coerente com ele
    dta_content, _layout = write_rb3_song_files(song, songs_dir, clean_shortname,
                                                total_duration_ms=total_duration_ms, with_art=False)
    write_songs_dta(os.path.join(songs_dir, "songs.dta"), [dta_content])

    # 5. Gera arquivo de configuração GPAC / orbis-pub-cmd
    gpac_content = f"""<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<project version="1">
  <volume>
    <volume_type>pkg_ps4_app</volume_type>
    <package_id>UP0006-{PS4_RB4_TITLE_ID}_00-MG{clean_shortname.upper()[:16]}</package_id>
    <title_id>{PS4_RB4_TITLE_ID}</title_id>
    <content_id>UP0006-{PS4_RB4_TITLE_ID}_00-MG{clean_shortname.upper()[:16]}</content_id>
    <passcode>00000000000000000000000000000000</passcode>
  </volume>
</project>
"""
    with open(os.path.join(root_dir, "project.gp4"), "w", encoding="utf-8") as f:
        f.write(gpac_content)

    # 6. Manual detalhado de instalação
    readme_path = os.path.join(root_dir, "COMO_INSTALAR_NO_PS4.txt")
    readme_content = f"""========================================================================
MIDGUITAR - PLAYSTATION 4 / ROCK BAND 4 (EXPERIMENTAL, NÃO VERIFICADO)
Música: {song.title} - {song.artist}
========================================================================

ATENÇÃO: esta pasta AINDA NÃO TOCA no Rock Band 4.

O Rock Band 4 usa arquivos binários próprios (.rbmid_ps4, .songdta_ps4,
.moggsong e .png_ps4) que o MidGuitar ainda não gera, e não existe uma
referência de PS4 para conferir o formato. O que há aqui é só a estrutura de
arquivos no estilo do Rock Band 3 (songs.dta, .mid, .mogg) e um project.gp4
de exemplo, que servem de ponto de partida para ferramentas de terceiros.

Para jogar esta música hoje, use as exportações já verificadas:
Rock Band 3 (PS3/RPCS3), Xbox 360 (pacote CON) ou Clone Hero / YARG.
========================================================================
"""
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

    return root_dir
