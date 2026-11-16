"""
Compilador de Pacotes de Músicas em Lote (Batch Song Pack Compiler).
Permite selecionar uma pasta com dezenas de músicas (ou várias músicas criadas no app)
e compilar tudo junto em um único pacote consolidado:
- Mescla todas as músicas em um único 'songs.dta' unificado oficial do Rock Band 3
- Organiza a pasta USRDIR/<pasta do pacote>/songs/{musica}/ para cada faixa com seus respectivos MIDIs e áudios
- Gera um único PARAM.SFO e ICON0.PNG para o Mega Pacote do PS3
- Gera instalador automático de 1 clique para o RPCS3
- Permite também empacotar pastas coletivas para o Clone Hero
"""

import os
import hashlib
from typing import List, Tuple

from src.creator.chart_model import ChartSong
from src.creator.chart_importer import import_song_from_folder
from src.creator.rb3_dta_exporter import (RB3_PS3_TITLE_ID, _ascii_alnum, song_shortname,
                                          stable_song_id, write_rb3_song_files, write_songs_dta)
from src.creator.edat import rb3_content_id
from src.creator.ps3_pkg_exporter import (build_ps3_package, generate_param_sfo, package_conf,
                                          save_icon0, write_install_bat)

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
    Layout dos pacotes reais: USRDIR/<pasta única do pacote>/songs/songs.dta (uma entrada
    por música) + songs/<s>/<s>.mid.edat / .mogg / gen/<s>_keep.png_ps3, e um .pkg de debug.
    """
    clean_pack_name = "".join(c for c in pack_name if c.isalnum() or c in " _-").strip() or "MegaPack_RB3"
    pack_id_str = hashlib.md5(clean_pack_name.encode()).hexdigest().upper()[:8]
    folder = ("MGPK" + pack_id_str + _ascii_alnum(clean_pack_name).upper())[:27]
    content_id = rb3_content_id(folder)

    pack_root = os.path.join(output_base_dir, f"PS3_PACK_{clean_pack_name}")
    songs_dir = os.path.join(pack_root, "USRDIR", folder, "songs")
    os.makedirs(songs_dir, exist_ok=True)

    # 1. PARAM.SFO e ICON0.PNG do pacote
    sfo_bytes = generate_param_sfo(f"RB3 Pack: {pack_name[:20]} ({len(songs)} Músicas)", content_id)
    with open(os.path.join(pack_root, "PARAM.SFO"), "wb") as f:
        f.write(sfo_bytes)
    save_icon0(os.path.join(pack_root, "ICON0.PNG"), pack_art_path, pack_name, f"{len(songs)} Músicas")

    # 2. Uma pasta por música e um bloco do songs.dta para cada uma
    dta_blocks = []
    used_shortnames = set()
    used_ids = set()
    for idx, song in enumerate(songs):
        raw_shortname = song_shortname(song, limit=20, default=f"song_{idx+1}")
        shortname = raw_shortname
        counter = 1
        while shortname in used_shortnames:
            shortname = f"{raw_shortname}_{counter}"
            counter += 1
        used_shortnames.add(shortname)

        # song_id estável por música (artista+título+charter); colisão dentro do pacote
        # (mesma música duas vezes) usa o shortname como sal
        song_id = stable_song_id(song)
        salt = 0
        while song_id in used_ids:
            salt += 1
            song_id = stable_song_id(song, salt="%s#%d" % (shortname, salt))
        used_ids.add(song_id)

        dta_block, layout = write_rb3_song_files(song, songs_dir, shortname, song_id=song_id,
                                                 edat_folder=folder)
        if layout is None:
            print(f"[PackCompiler] Aviso: '{song.title}' não tem áudio; o pacote sai sem {shortname}.mogg")
        dta_blocks.append(dta_block)

    # Salva o arquivo songs.dta unificado com todas as músicas juntas
    write_songs_dta(os.path.join(songs_dir, "songs.dta"), dta_blocks)
    build_ps3_package(pack_root, folder, _ascii_alnum(clean_pack_name) or "pacote")

    # 3. package.conf para compiladores PKG
    with open(os.path.join(pack_root, "package.conf"), "w", encoding="utf-8", newline="\n") as f:
        f.write(package_conf(content_id))

    # 4. Instalador automático no RPCS3 (copia a pasta do pacote, não sobrescreve outras)
    write_install_bat(os.path.join(pack_root, "INSTALAR_PACOTE_NO_RPCS3.bat"), folder,
                      RB3_PS3_TITLE_ID, f"Pacote: {pack_name} ({len(songs)} Músicas)")

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
