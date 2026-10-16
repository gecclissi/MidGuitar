"""
Exportador de Músicas para PlayStation 4 (Rock Band 4 / PS4 HEN / YARG / FPKG).
Gera a estrutura oficial para custom songs no PlayStation 4:
- sce_sys/param.sfo (metadados do PS4 com CUSA02084 / CUSA02901)
- songs/songs.dta
- songs/{shortname}/{shortname}.mid
- songs/{shortname}/{shortname}.ogg
- COMO_INSTALAR_NO_PS4.txt (guia passo a passo para consoles com GoldHEN / PS4 HEN)
"""

import os
import shutil
from src.creator.chart_model import ChartSong
from src.creator.rb3_dta_exporter import generate_songs_dta_content
from src.creator.midi_generator import generate_rbn_midi, save_midi

PS4_RB4_TITLE_ID = "CUSA02084" # Rock Band 4 US
PS4_RB4_RIVALS_ID = "CUSA02901" # Rock Band 4 Rivals

def export_ps4_structure(song: ChartSong, output_base_dir: str, total_duration_ms: int = 180000) -> str:
    """
    Exporta a música no padrão do PlayStation 4 para Rock Band 4 e YARG.
    """
    clean_shortname = "".join(c for c in f"{song.artist}_{song.title}" if c.isalnum()).lower()[:24] or "custom_song"
    folder_name = f"PS4_RB4_{clean_shortname}"
    root_dir = os.path.join(output_base_dir, folder_name)

    # 1. Diretórios do pacote PS4
    sce_dir = os.path.join(root_dir, "sce_sys")
    songs_dir = os.path.join(root_dir, "songs")
    track_dir = os.path.join(songs_dir, clean_shortname)
    os.makedirs(sce_dir, exist_ok=True)
    os.makedirs(track_dir, exist_ok=True)

    # 2. Gera songs.dta
    dta_content = generate_songs_dta_content(song, clean_shortname)
    dta_path = os.path.join(songs_dir, "songs.dta")
    with open(dta_path, "w", encoding="utf-8") as f:
        f.write(dta_content)

    # 3. Gera MIDI compatível
    mid = generate_rbn_midi(song, total_duration_ms=total_duration_ms)
    mid_path = os.path.join(track_dir, f"{clean_shortname}.mid")
    save_midi(mid, mid_path)

    # 4. Gera o container .mogg e copia áudios
    from src.creator.mogg_generator import create_unencrypted_mogg
    primary_audio = song.audio_path or (song.audio_stems[0] if song.audio_stems else None)
    if primary_audio and os.path.exists(primary_audio):
        mogg_dest = os.path.join(track_dir, f"{clean_shortname}.mogg")
        create_unencrypted_mogg(primary_audio, mogg_dest)

    if song.audio_stems:
        for stem_p in song.audio_stems:
            if os.path.exists(stem_p):
                fname = os.path.basename(stem_p)
                dest = os.path.join(track_dir, fname)
                shutil.copy2(stem_p, dest)
    elif song.audio_path and os.path.exists(song.audio_path):
        ext = os.path.splitext(song.audio_path)[1].lower()
        dest_audio = os.path.join(track_dir, f"{clean_shortname}{ext}")
        shutil.copy2(song.audio_path, dest_audio)

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
MIDGUITAR - GUIA DE INSTALAÇÃO NO PLAYSTATION 4 (ROCK BAND 4 / YARG)
Música: {song.title} - {song.artist}
Title ID: {PS4_RB4_TITLE_ID} / {PS4_RB4_RIVALS_ID}
========================================================================

COMO USAR NO SEU PLAYSTATION 4 (CONSOLES COM HEN / GOLDHEN):

MÉTODO 1: VIA GESTOR DE ARQUIVOS (FTP / PS4-EXPLORER)
1. Conecte-se ao PS4 via FTP (FileZilla) ou abra o aplicativo PS4-Explorer
   no próprio videogame.
2. Navegue até a pasta de DLCs do Rock Band 4 instalada no seu console:
   /user/appmeta/{PS4_RB4_TITLE_ID}/
   ou
   /data/songs/
3. Copie a pasta '{clean_shortname}' com os arquivos gerados (MIDI, DTA e Áudio).
4. Inicie o Rock Band 4 e aproveite suas novas músicas!

MÉTODO 2: COMPILANDO EM PACOTE FPKG (ORBIS-PUB-GEN)
1. Se você compila DLCs em formato .pkg instalável para o PS4:
2. Abra a ferramenta 'orbis-pub-gen' no computador.
3. Carregue o arquivo 'project.gp4' gerado nesta pasta.
4. Clique em 'Build' para gerar o arquivo .pkg final.
5. Copie o .pkg para um pendrive em exFAT/FAT32 e instale pelo 'GoldHEN Package Installer'.
========================================================================
"""
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

    return root_dir
