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

    if hasattr(song, "get_effective_duration_ms"):
        total_duration_ms = max(total_duration_ms or 0, song.get_effective_duration_ms())

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
"""
    # Chaves importadas que o MidGuitar não gera (preview_end_time, pro_drums, diff_*_real...)
    from src.creator.chart_importer import INI_MANAGED_KEYS
    extra = {k: v for k, v in (getattr(song, "ini_extra", None) or {}).items()
             if k not in INI_MANAGED_KEYS and "\n" not in str(v)}
    extra.setdefault("icon", "midguitar")
    extra.setdefault("loading_phrase", "Criado e gravado com MidGuitar Universal Studio!")
    ini_content += "".join(f"{k} = {v}\n" for k, v in extra.items())
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

    # 4. Copia a arte do álbum ou gera uma estilizada (512x512) para nunca ficar sem capa
    dest_art = os.path.join(target_dir, "album.png")
    if song.album_art_path and os.path.exists(song.album_art_path):
        try:
            from PIL import Image
            im = Image.open(song.album_art_path).convert("RGBA")
            im = im.resize((512, 512), Image.Resampling.LANCZOS)
            im.save(dest_art, "PNG")
        except Exception as e:
            print(f"[CloneHeroExporter] Erro ao salvar arte do álbum: {e}")
            _create_default_album_art(dest_art, song.title, song.artist)
    else:
        _create_default_album_art(dest_art, song.title, song.artist)

    return target_dir


def _create_default_album_art(path: str, title: str, artist: str):
    """Cria uma capa padrão bonita 512x512 caso o usuário não tenha selecionado uma imagem."""
    try:
        from PIL import Image, ImageDraw
        im = Image.new("RGBA", (512, 512), color=(15, 23, 42, 255))
        draw = ImageDraw.Draw(im)
        # Borda e disco central estilizado
        draw.rectangle([(8, 8), (503, 503)], outline=(56, 189, 248), width=3)
        draw.rectangle([(16, 16), (495, 495)], outline=(30, 41, 59), width=2)
        # Círculo de vinil
        draw.ellipse([(106, 106), (406, 406)], fill=(24, 32, 47), outline=(51, 65, 85), width=2)
        draw.ellipse([(206, 206), (306, 306)], fill=(30, 41, 59), outline=(56, 189, 248), width=2)
        draw.ellipse([(246, 246), (266, 266)], fill=(15, 23, 42))

        # Textos informativos
        draw.text((40, 40), "CUSTOM TRACK", fill=(56, 189, 248))
        draw.text((40, 420), title[:28], fill=(255, 255, 255))
        draw.text((40, 450), artist[:32], fill=(148, 163, 184))
        draw.text((40, 480), "⚡ MidGuitar Studio", fill=(16, 185, 129))
        im.save(path, "PNG")
    except Exception as e:
        print(f"[CloneHeroExporter] Erro ao criar capa padrão: {e}")
