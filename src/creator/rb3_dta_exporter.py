"""
Gerador de Arquivos songs.dta para Rock Band 3 (Padrão Harmonix).
Gera metadados, canais de áudio, panning, volumes, ranks de dificuldade
e estrutura de pastas prontas para Rock Band 3 (Console Xbox 360, PS3 RPCS3 e Wii).
"""

import os
import hashlib
from src.creator.chart_model import ChartSong
from src.creator.midi_generator import generate_rbn_midi, save_midi

def generate_songs_dta_content(song: ChartSong, shortname: str, song_id: int = None) -> str:
    """Gera o texto de definição songs.dta conforme a sintaxe oficial Harmonix."""
    if song_id is None:
        # Gera ID numérico estável baseado no nome e artista
        hash_val = int(hashlib.md5(f"{song.artist}_{song.title}".encode()).hexdigest()[:7], 16)
        song_id = 1010000000 + (hash_val % 9000000)

    # Converte rank 0-7 para pontuação Harmonix (0 a 500)
    def rank_to_dta(val: int) -> int:
        return max(0, min(500, val * 60 + 50))

    has_multistem = len(song.audio_stems) > 1
    if has_multistem:
        tracks_dta = """((guitar (0 1))
          (bass 2)
          (drum (3 4))
          (keys (5 6))
          (vocals 7)
         )"""
        pans_dta = "(-1.0 1.0 0.0 -1.0 1.0 -1.0 1.0 0.0)"
        vols_dta = "(-1.0 -1.0 -1.5 -1.0 -1.0 -1.5 -1.5 -1.0)"
        cores_dta = "(-1 -1 -1 -1 -1 -1 -1 -1)"
    else:
        # Padrão oficial Harmonix para faixas estéreo gerais (2 canais)
        tracks_dta = """((guitar (0 1))
          (bass (0 1))
          (drum (0 1))
          (keys (0 1))
          (vocals (0 1))
         )"""
        pans_dta = "(-1.0 1.0)"
        vols_dta = "(-1.5 -1.5)"
        cores_dta = "(-1 -1)"

    dta = f"""({shortname}
   (name "{song.title}")
   (artist "{song.artist}")
   (master TRUE)
   (song_id {song_id})
   (song
      (name "songs/{shortname}/{shortname}")
      (tracks
         {tracks_dta}
      )
      (vocal_parts 1)
      (pans {pans_dta})
      (vols {vols_dta})
      (cores {cores_dta})
      (drum_solo (seq 96 97 98 99 100))
      (drum_freestyle (seq 120 121 122 123 124))
   )
   (bank "sfx/tambourine_bank.milo")
   (anim_tempo kTempoMedium)
   (song_scroll_speed 2300)
   (preview {song.preview_start_ms} {song.preview_start_ms + 30000})
   (album_name "{song.album}")
   (album_track_number 1)
   (year_released {song.year})
   (format 10)
   (version 30)
   (game_origin rb3_dlc)
   (rating 2)
   (genre "{song.genre.lower()}")
   (rank
      (drum {rank_to_dta(song.diff_drums)})
      (guitar {rank_to_dta(song.diff_guitar)})
      (bass {rank_to_dta(song.diff_bass)})
      (keys {rank_to_dta(song.diff_keys)})
      (vocals {rank_to_dta(song.diff_vocals)})
      (real_guitar 0)
      (real_bass 0)
      (real_keys 0)
      (band {rank_to_dta(song.diff_band)})
   )
)
"""
    return dta

def export_rb3_song_package(song: ChartSong, output_base_dir: str, audio_source_path: str = None, total_duration_ms: int = 180000) -> str:
    """
    Exporta a estrutura completa de arquivos para Rock Band 3:
    songs/{shortname}/{shortname}.mid
    songs/songs.dta
    Retorna o diretório base criado.
    """
    clean_shortname = "".join(c for c in f"{song.artist}_{song.title}" if c.isalnum()).lower()[:24] or "custom_song"
    
    rb3_root = os.path.join(output_base_dir, f"RB3_{clean_shortname}")
    songs_dir = os.path.join(rb3_root, "songs")
    song_track_dir = os.path.join(songs_dir, clean_shortname)
    os.makedirs(song_track_dir, exist_ok=True)

    # 1. Gera o arquivo songs.dta
    dta_content = generate_songs_dta_content(song, clean_shortname)
    dta_path = os.path.join(songs_dir, "songs.dta")
    with open(dta_path, "w", encoding="utf-8") as f:
        f.write(dta_content)

    # 2. Gera o arquivo .mid compatível com RB3
    mid = generate_rbn_midi(song, total_duration_ms=total_duration_ms)
    mid_path = os.path.join(song_track_dir, f"{clean_shortname}.mid")
    save_midi(mid, mid_path)

    # 2.1 Copia áudio para dentro da pasta da música
    import shutil
    if song.audio_stems:
        for stem_p in song.audio_stems:
            if os.path.exists(stem_p):
                fname = os.path.basename(stem_p)
                dest_p = os.path.join(song_track_dir, fname)
                try:
                    shutil.copy2(stem_p, dest_p)
                except Exception as e:
                    print(f"[RB3Exporter] Erro ao copiar stem {fname}: {e}")
    elif song.audio_path and os.path.exists(song.audio_path):
        ext = os.path.splitext(song.audio_path)[1].lower()
        dest_audio = os.path.join(song_track_dir, f"{clean_shortname}{ext}")
        try:
            shutil.copy2(song.audio_path, dest_audio)
        except Exception as e:
            print(f"[RB3Exporter] Erro ao copiar áudio: {e}")

    # 3. Informações de áudio e guia de carregamento
    readme_path = os.path.join(rb3_root, "COMO_JOGAR_NO_RB3.txt")
    readme_content = f"""============================================================
MidGuitar Studio - Pacote Rock Band 3 Pronto!
Música: {song.title} - {song.artist}
============================================================

Estrutura gerada:
- songs/songs.dta (Definições Harmonix)
- songs/{clean_shortname}/{clean_shortname}.mid (Trilhas RBN com todas as notas)

Como jogar no RPCS3 (Emulador de PS3):
1. Basta copiar a pasta 'songs' gerada aqui para dentro da pasta do jogo no RPCS3:
   dev_hdd0/game/BLUS30463/USRDIR/
2. Inicie o Rock Band 3 e a música aparecerá na biblioteca automaticamente!

Como jogar no Xbox 360:
1. Esta pasta pode ser copiada diretamente para jogos com mod RGH/JTAG ou empacotada em CON.
============================================================
"""
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

    return rb3_root
