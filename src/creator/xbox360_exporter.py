"""
Exportador de Músicas para Xbox 360 (Rock Band 3 / RGH / JTAG / Horizon / Xenia).
Gera a estrutura de arquivos e diretórios oficial do Xbox 360:
- songs/songs.dta
- songs/{shortname}/{shortname}.mid
- songs/{shortname}/{shortname}.ogg
- Content/0000000000000000/45410914/00000002/{shortname}/ (estrutura de pendrive formatado em FATX / Horizon)
- COMO_INSTALAR_NO_XBOX360.txt (manual detalhado para console destravado e emulador Xenia)
"""

import os
import shutil
from src.creator.chart_model import ChartSong
from src.creator.rb3_dta_exporter import generate_songs_dta_content
from src.creator.midi_generator import generate_rbn_midi, save_midi

XBOX360_RB3_TITLE_ID = "45410914" # Title ID oficial do Rock Band 3 no Xbox 360

def export_xbox360_structure(song: ChartSong, output_base_dir: str, total_duration_ms: int = 180000) -> str:
    """
    Exporta a música no padrão oficial do Xbox 360 (Rock Band 3).
    Gera tanto a pasta solta para Aurora/Freestyle/Xenia quanto a estrutura Content/ para pendrive.
    """
    clean_shortname = "".join(c for c in f"{song.artist}_{song.title}" if c.isalnum()).lower()[:24] or "custom_song"
    folder_name = f"XBOX360_RB3_{clean_shortname}"
    root_dir = os.path.join(output_base_dir, folder_name)

    # 1. Pasta solta (Estrutura songs/)
    songs_dir = os.path.join(root_dir, "songs")
    track_dir = os.path.join(songs_dir, clean_shortname)
    os.makedirs(track_dir, exist_ok=True)

    # 2. Estrutura Content para pendrive FATX / Horizon / Aurora
    content_dir = os.path.join(root_dir, "Content", "0000000000000000", XBOX360_RB3_TITLE_ID, "00000002", clean_shortname)
    os.makedirs(content_dir, exist_ok=True)

    # 3. Gera songs.dta
    dta_content = generate_songs_dta_content(song, clean_shortname)
    dta_path = os.path.join(songs_dir, "songs.dta")
    with open(dta_path, "w", encoding="utf-8") as f:
        f.write(dta_content)

    # Copia dta também para dentro da estrutura content
    with open(os.path.join(content_dir, "songs.dta"), "w", encoding="utf-8") as f:
        f.write(dta_content)

    # 4. Gera arquivo MIDI ({shortname}.mid)
    mid = generate_rbn_midi(song, total_duration_ms=total_duration_ms)
    mid_path = os.path.join(track_dir, f"{clean_shortname}.mid")
    save_midi(mid, mid_path)
    shutil.copy2(mid_path, os.path.join(content_dir, f"{clean_shortname}.mid"))

    # 5. Copia áudios
    if song.audio_stems:
        for stem_p in song.audio_stems:
            if os.path.exists(stem_p):
                fname = os.path.basename(stem_p)
                dest1 = os.path.join(track_dir, fname)
                dest2 = os.path.join(content_dir, fname)
                shutil.copy2(stem_p, dest1)
                shutil.copy2(stem_p, dest2)
    elif song.audio_path and os.path.exists(song.audio_path):
        ext = os.path.splitext(song.audio_path)[1].lower()
        dest_audio1 = os.path.join(track_dir, f"{clean_shortname}{ext}")
        dest_audio2 = os.path.join(content_dir, f"{clean_shortname}{ext}")
        shutil.copy2(song.audio_path, dest_audio1)
        shutil.copy2(song.audio_path, dest_audio2)

    # 6. Manual passo a passo para o usuário
    readme_path = os.path.join(root_dir, "COMO_INSTALAR_NO_XBOX360.txt")
    readme_content = f"""========================================================================
MIDGUITAR - GUIA DE INSTALAÇÃO NO XBOX 360 (ROCK BAND 3)
Música: {song.title} - {song.artist}
Title ID do Rock Band 3: {XBOX360_RB3_TITLE_ID}
========================================================================

Você tem 3 formas de jogar esta música no Xbox 360:

------------------------------------------------------------------------
OPÇÃO 1: XBOX 360 DESTRAVADO (RGH / JTAG com Aurora ou Freestyle)
------------------------------------------------------------------------
1. Copie a pasta 'Content' gerada aqui diretamente para a raiz do seu
   disco rígido interno (Hdd1:\\) ou para o seu HD externo / Pendrive USB.
   Caminho final no console:
   Hdd1:\\Content\\0000000000000000\\45410914\\00000002\\{clean_shortname}\\

2. Alternativamente, se você usa a pasta solta de músicas do RB3:
   Copie a pasta 'songs' para dentro da pasta do jogo Rock Band 3 no seu HD.

3. Inicie o Rock Band 3. O jogo atualizará a biblioteca e a música aparecerá
   imediatamente no menu de seleção!

------------------------------------------------------------------------
OPÇÃO 2: PENDRIVE FORMATADO NO XBOX 360 (HORIZON / FATXPLORER)
------------------------------------------------------------------------
1. Formate um pendrive USB no próprio Xbox 360 (Configurações do Sistema ->
   Armazenamento -> Formatar para o Xbox).
2. Conecte o pendrive no PC e abra o programa 'Horizon' ou 'FATXplorer'.
3. Injete a pasta '{clean_shortname}' dentro de:
   Title ID 45410914 -> Rock Band 3 -> Saved Games / DLC.
4. Conecte o pendrive no Xbox 360 e divirta-se!

------------------------------------------------------------------------
OPÇÃO 3: EMULADOR XENIA NO COMPUTADOR (PC)
------------------------------------------------------------------------
1. Abra a pasta do seu emulador Xenia.
2. Navegue até:
   xenia\\content\\45410914\\00000002\\
3. Cole a pasta '{clean_shortname}' lá dentro.
4. Abra o Rock Band 3 no Xenia e a música estará pronta para tocar!
========================================================================
"""
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

    return root_dir
