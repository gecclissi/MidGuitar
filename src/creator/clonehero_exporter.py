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

    # 2. Gera e salva o song.ini
    ini_content = f"""[song]
name = {song.title}
artist = {song.artist}
album = {song.album}
genre = {song.genre}
year = {song.year}
charter = {song.charter}
song_length = {total_duration_ms}
diff_band = {song.diff_band}
diff_guitar = {song.diff_guitar}
diff_bass = {song.diff_bass}
diff_drums = {song.diff_drums}
diff_keys = {song.diff_keys}
preview_start_time = {song.preview_start_ms}
icon = midguitar
loading_phrase = Criado e gravado com MidGuitar Universal Studio!
"""
    ini_path = os.path.join(target_dir, "song.ini")
    with open(ini_path, "w", encoding="utf-8") as f:
        f.write(ini_content)

    # 3. Copia o arquivo de áudio
    audio_path = audio_source_path or song.audio_path
    if audio_path and os.path.exists(audio_path):
        ext = os.path.splitext(audio_path)[1].lower()
        dest_filename = f"song{ext}"
        dest_audio = os.path.join(target_dir, dest_filename)
        try:
            shutil.copy2(audio_path, dest_audio)
        except Exception as e:
            print(f"[CloneHeroExporter] Erro ao copiar áudio: {e}")

    return target_dir
