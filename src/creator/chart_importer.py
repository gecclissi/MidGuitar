"""
Importador e Conversor de Músicas (Charts).
Lê pastas e arquivos de músicas do Clone Hero, Phase Shift, FoFiX, Chorus Encore e C3,
carregando metadados (song.ini), trilhas MIDI (notes.mid) e arquivos de áudio.
Permite converter qualquer música baixada para Rock Band 3 ou Clone Hero em 1 clique!
"""

import os
import configparser
import mido
from mido import MidiFile
from src.creator.chart_model import ChartSong, NoteEvent, TextEvent
from src.creator.rbn_specs import FRET_NOTES, DRUM_NOTES, TICKS_PER_BEAT

def parse_song_ini(ini_path: str) -> dict:
    """Lê os metadados do song.ini."""
    config = configparser.ConfigParser(interpolation=None)
    metadata = {}
    try:
        config.read(ini_path, encoding="utf-8-sig")
        section = "song" if config.has_section("song") else config.sections()[0] if config.sections() else None
        if section:
            for k, v in config.items(section):
                metadata[k.lower()] = v
    except Exception as e:
        print(f"[ChartImporter] Erro ao ler song.ini: {e}")
    return metadata

def import_song_from_folder(folder_path: str) -> ChartSong:
    """
    Importa uma pasta completa de música contendo notes.mid, song.ini e áudio.
    """
    song = ChartSong()

    # 1. Busca song.ini
    ini_file = os.path.join(folder_path, "song.ini")
    if os.path.exists(ini_file):
        meta = parse_song_ini(ini_file)
        song.title = meta.get("name", song.title)
        song.artist = meta.get("artist", song.artist)
        song.album = meta.get("album", song.album)
        song.genre = meta.get("genre", song.genre)
        song.charter = meta.get("charter", song.charter)
        try:
            song.year = int(meta.get("year", song.year))
        except Exception:
            pass
        try:
            song.diff_guitar = int(meta.get("diff_guitar", song.diff_guitar))
            song.diff_bass = int(meta.get("diff_bass", song.diff_bass))
            song.diff_drums = int(meta.get("diff_drums", song.diff_drums))
            song.diff_keys = int(meta.get("diff_keys", song.diff_keys))
            song.diff_band = int(meta.get("diff_band", song.diff_band))
        except Exception:
            pass

    # 2. Busca arquivos de áudio (Stems individuais ou mixagem geral)
    for f in os.listdir(folder_path):
        f_lower = f.lower()
        if f_lower.endswith((".ogg", ".mp3", ".wav", ".flac", ".opus")):
            full_p = os.path.join(folder_path, f)
            song.audio_stems.append(full_p)
            stem_base = os.path.splitext(f_lower)[0]
            if stem_base in ["song", "guitar", "audio"] and not song.audio_path:
                song.audio_path = full_p

    if not song.audio_path and song.audio_stems:
        song.audio_path = song.audio_stems[0]

    # 3. Busca e analisa notes.mid
    mid_file = os.path.join(folder_path, "notes.mid")
    if not os.path.exists(mid_file):
        for f in os.listdir(folder_path):
            if f.lower().endswith(".mid"):
                mid_file = os.path.join(folder_path, f)
                break

    if os.path.exists(mid_file):
        try:
            mid = MidiFile(mid_file)
            _parse_midi_into_song(mid, song)
        except Exception as e:
            print(f"[ChartImporter] Erro ao analisar MIDI {mid_file}: {e}")

    return song

def _parse_midi_into_song(mid: MidiFile, song: ChartSong):
    """Extrai notas e BPM das trilhas do MIDI."""
    # Descobre o BPM
    bpm = 120.0
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'set_tempo':
                bpm = mido.tempo2bpm(msg.tempo)
                break
    song.bpm = round(bpm, 2)

    # Inverte os mapas de notas (número MIDI -> lane)
    inv_fret_notes = {}
    for diff, lanes in FRET_NOTES.items():
        for lane, pitch in lanes.items():
            inv_fret_notes[pitch] = (lane, diff)

    inv_drum_notes = {}
    for diff, lanes in DRUM_NOTES.items():
        for lane, pitch in lanes.items():
            inv_drum_notes[pitch] = (lane, diff)

    # Processa cada trilha
    for track in mid.tracks:
        track_name = ""
        current_tick = 0
        active_notes = {} # pitch -> start_tick

        for msg in track:
            current_tick += msg.time
            if msg.type == 'track_name':
                track_name = msg.name.strip().upper()
            elif msg.type == 'text':
                ms = int((current_tick / mid.ticks_per_beat) * (60.0 / song.bpm) * 1000.0)
                song.events.append(TextEvent(time_ms=ms, text=msg.text))
            elif msg.type == 'note_on' and msg.velocity > 0:
                active_notes[msg.note] = current_tick
            elif (msg.type == 'note_off') or (msg.type == 'note_on' and msg.velocity == 0):
                if msg.note in active_notes:
                    start_tick = active_notes.pop(msg.note)
                    start_ms = int((start_tick / mid.ticks_per_beat) * (60.0 / song.bpm) * 1000.0)
                    duration_ms = max(100, int(((current_tick - start_tick) / mid.ticks_per_beat) * (60.0 / song.bpm) * 1000.0))

                    if "GUITAR" in track_name:
                        if msg.note in inv_fret_notes:
                            lane, diff = inv_fret_notes[msg.note]
                            song.guitar_notes.append(NoteEvent(time_ms=start_ms, lane=lane, duration_ms=duration_ms, difficulty=diff))
                    elif "BASS" in track_name:
                        if msg.note in inv_fret_notes:
                            lane, diff = inv_fret_notes[msg.note]
                            song.bass_notes.append(NoteEvent(time_ms=start_ms, lane=lane, duration_ms=duration_ms, difficulty=diff))
                    elif "DRUM" in track_name:
                        if msg.note in inv_drum_notes:
                            lane, diff = inv_drum_notes[msg.note]
                            song.drum_notes.append(NoteEvent(time_ms=start_ms, lane=lane, duration_ms=duration_ms, difficulty=diff))
                    elif "KEYS" in track_name:
                        if msg.note in inv_fret_notes:
                            lane, diff = inv_fret_notes[msg.note]
                            song.keys_notes.append(NoteEvent(time_ms=start_ms, lane=lane, duration_ms=duration_ms, difficulty=diff))

    # Ordena todas as trilhas por tempo
    song.guitar_notes.sort(key=lambda n: n.time_ms)
    song.bass_notes.sort(key=lambda n: n.time_ms)
    song.drum_notes.sort(key=lambda n: n.time_ms)
    song.keys_notes.sort(key=lambda n: n.time_ms)
