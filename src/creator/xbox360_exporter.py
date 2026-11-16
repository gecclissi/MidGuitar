"""
Exportador de Músicas para Xbox 360 (Rock Band 3 / RGH / JTAG / Horizon / Xenia).
Gera a estrutura de arquivos e diretórios oficial do Xbox 360:
- songs/songs.dta
- songs/{shortname}/{shortname}.mid
- songs/{shortname}/{shortname}.mogg (multicanal, 44100 Hz)
- Content/0000000000000000/45410914/00000002/{shortname}/ (estrutura de pendrive formatado em FATX / Horizon)
- COMO_INSTALAR_NO_XBOX360.txt (manual detalhado para console destravado e emulador Xenia)
"""

import os
import shutil
from src.creator.chart_model import ChartSong
from src.creator.rb3_dta_exporter import song_shortname, write_rb3_song_files, write_songs_dta

XBOX360_RB3_TITLE_ID = "45410914" # Title ID oficial do Rock Band 3 no Xbox 360

def export_xbox360_structure(song: ChartSong, output_base_dir: str, total_duration_ms: int = 180000) -> str:
    """
    Exporta a música no padrão oficial do Xbox 360 (Rock Band 3).
    Gera tanto a pasta solta para Aurora/Freestyle/Xenia quanto a estrutura Content/ para pendrive.
    """
    clean_shortname = song_shortname(song)
    folder_name = f"XBOX360_RB3_{clean_shortname}"
    root_dir = os.path.join(output_base_dir, folder_name)

    # 1. Pasta solta (Estrutura songs/)
    songs_dir = os.path.join(root_dir, "songs")
    track_dir = os.path.join(songs_dir, clean_shortname)
    os.makedirs(track_dir, exist_ok=True)

    # 2. Estrutura Content para pendrive FATX / Horizon / Aurora
    content_dir = os.path.join(root_dir, "Content", "0000000000000000", XBOX360_RB3_TITLE_ID, "00000002", clean_shortname)
    os.makedirs(content_dir, exist_ok=True)

    # 3. MIDI (só trilhas do Rock Band), .mogg multicanal e songs.dta coerente com ele
    dta_content, _layout = write_rb3_song_files(song, songs_dir, clean_shortname,
                                                total_duration_ms=total_duration_ms, with_art=False)
    write_songs_dta(os.path.join(songs_dir, "songs.dta"), [dta_content])

    # 4. Cópia para a estrutura Content (pendrive / Horizon)
    write_songs_dta(os.path.join(content_dir, "songs.dta"), [dta_content])
    for ext in (".mid", ".mogg"):
        src = os.path.join(track_dir, f"{clean_shortname}{ext}")
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(content_dir, f"{clean_shortname}{ext}"))

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
