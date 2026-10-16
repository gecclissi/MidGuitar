"""
Exportador para Clone Hero / YARG / Phase Shift.
Gera uma pasta pronta para colar na pasta 'Songs' do jogo contendo:
- notes.mid (MIDI com as trilhas RBN)
- song.ini (Metadados e pontuações de dificuldade)
- song.ogg ou song.mp3 (Áudio da música)
"""

import os
import shutil
from src.creator.chart_model import ChartSong
from src.creator.midi_generator import generate_rbn_midi, save_midi

def export_clone_hero_song(song: ChartSong, output_base_dir: str, audio_source_path: str = None, total_duration_ms: int = 180000) -> str:
    """
    Exporta a música para formato nativo do Clone Hero / YARG.
    Retorna o caminho da pasta criada.
    """
    clean_artist = "".join(c for c in song.artist if c.isalnum() or c in " _-").strip() or "Artista"
    clean_title = "".join(c for c in song.title if c.isalnum() or c in " _-").strip() or "Musica"
    folder_name = f"{clean_artist} - {clean_title}"
    target_dir = os.path.join(output_base_dir, folder_name)
    os.makedirs(target_dir, exist_ok=True)

    # 1. Gera e salva o notes.mid
    mid = generate_rbn_midi(song, total_duration_ms=total_duration_ms)
    midi_path = os.path.join(target_dir, "notes.mid")
    save_midi(mid, midi_path)

    # 2. Gera e salva o song.ini (com -1 para instrumentos inexistentes conforme padrão Clone Hero / YARG)
    d_guitar = song.diff_guitar if song.guitar_notes else -1
    d_bass = song.diff_bass if song.bass_notes else -1
    d_drums = song.diff_drums if song.drum_notes else -1
    d_keys = song.diff_keys if song.keys_notes else -1
    d_vocals = song.diff_vocals if song.vocal_notes else -1
    d_pro_guitar = getattr(song, "diff_pro_guitar", 3) if getattr(song, "pro_guitar_notes", None) else -1
    d_pro_bass = getattr(song, "diff_pro_bass", 2) if getattr(song, "pro_bass_notes", None) else -1
    d_pro_keys = getattr(song, "diff_pro_keys", 3) if getattr(song, "pro_keys_notes", None) else -1

    ini_content = f"""[song]
name = {song.title}
artist = {song.artist}
album = {song.album}
genre = {song.genre}
year = {song.year}
charter = {song.charter}
song_length = {total_duration_ms}
diff_band = {song.diff_band}
diff_guitar = {d_guitar}
diff_bass = {d_bass}
diff_drums = {d_drums}
diff_keys = {d_keys}
diff_vocals = {d_vocals}
diff_guitar_real = {d_pro_guitar}
diff_bass_real = {d_pro_bass}
diff_keys_real = {d_pro_keys}
preview_start_time = {song.preview_start_ms}
icon = midguitar
loading_phrase = Criado e gravado com MidGuitar Universal Studio!
"""
    ini_path = os.path.join(target_dir, "song.ini")
    with open(ini_path, "w", encoding="utf-8") as f:
        f.write(ini_content)

    # 3. Copia e converte arquivos de áudio (gera song.ogg oficial para máxima compatibilidade no Clone Hero / YARG)
    from src.creator.mogg_generator import convert_audio_to_ogg
    audio_path = audio_source_path or song.audio_path
    if audio_path and os.path.exists(audio_path):
        ogg_dest = os.path.join(target_dir, "song.ogg")
        if not convert_audio_to_ogg(audio_path, ogg_dest):
            ext = os.path.splitext(audio_path)[1].lower()
            try:
                shutil.copy2(audio_path, os.path.join(target_dir, f"song{ext}"))
            except Exception as e:
                print(f"[CloneHeroExporter] Erro ao copiar áudio: {e}")

    if song.audio_stems:
        for stem_p in song.audio_stems:
            if os.path.exists(stem_p):
                fname = os.path.basename(stem_p)
                dest_p = os.path.join(target_dir, fname)
                try:
                    shutil.copy2(stem_p, dest_p)
                except Exception as e:
                    print(f"[CloneHeroExporter] Erro ao copiar stem {fname}: {e}")

    # 4. Copia a arte do álbum se existir
    if song.album_art_path and os.path.exists(song.album_art_path):
        try:
            from PIL import Image
            dest_art = os.path.join(target_dir, "album.png")
            im = Image.open(song.album_art_path).convert("RGBA")
            im.save(dest_art, "PNG")
        except Exception as e:
            print(f"[CloneHeroExporter] Erro ao salvar arte do álbum: {e}")

    return target_dir
