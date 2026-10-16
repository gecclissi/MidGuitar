"""
Gerador de Arquivos MIDI no Padrão Rock Band Network (RBN / C3) e Clone Hero.
Converte objetos ChartSong em arquivos .mid com trilhas separadas:
PART GUITAR, PART BASS, PART DRUMS, PART KEYS, BEAT e EVENTS.
"""

import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage, bpm2tempo
from src.creator.chart_model import ChartSong, NoteEvent, VocalNote
from src.creator.rbn_specs import (
    FRET_NOTES, DRUM_NOTES, BEAT_BAR_DOWNBEAT, BEAT_OFFBEAT,
    GUITAR_OVERDRIVE, DRUM_OVERDRIVE, KEYS_OVERDRIVE,
    VOCAL_PHRASE_MARKER, VOCAL_OVERDRIVE, VOCAL_PERCUSSION, VOCAL_TALKIE
)

TICKS_PER_BEAT = 480

def ms_to_ticks(ms: int, bpm: float) -> int:
    """Converte milissegundos em ticks MIDI baseado no BPM."""
    beats = (ms / 1000.0) * (bpm / 60.0)
    return int(beats * TICKS_PER_BEAT)

def ticks_to_ms(ticks: int, bpm: float) -> int:
    """Converte ticks MIDI em milissegundos."""
    beats = ticks / TICKS_PER_BEAT
    return int((beats * 60.0 / bpm) * 1000.0)

def generate_rbn_midi(song: ChartSong, total_duration_ms: int = 180000) -> MidiFile:
    """
    Gera um MidiFile (Type 1) 100% compatível com Rock Band 3, Clone Hero e YARG.
    """
    mid = MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)

    # -------------------------------------------------------------
    # PISTA 0: TEMPO & ASSINATURA DE TEMPO
    # -------------------------------------------------------------
    tempo_track = MidiTrack()
    mid.tracks.append(tempo_track)

    num, den = song.time_signature
    tempo_track.append(MetaMessage('time_signature', numerator=num, denominator=den, clocks_per_click=24, notated_32nd_notes_per_beat=8, time=0))
    tempo_track.append(MetaMessage('set_tempo', tempo=bpm2tempo(song.bpm), time=0))
    tempo_track.append(MetaMessage('end_of_track', time=0))

    # -------------------------------------------------------------
    # PISTA 1: BEAT (Compassos fortes e fracos)
    # -------------------------------------------------------------
    beat_track = MidiTrack()
    mid.tracks.append(beat_track)
    beat_track.append(MetaMessage('track_name', name='BEAT', time=0))

    # Gera batidas a cada semínima (1 beat = TICKS_PER_BEAT)
    total_ticks = ms_to_ticks(total_duration_ms, song.bpm)
    current_tick = 0
    beat_counter = 0

    beat_events = []
    while current_tick < total_ticks:
        pitch = BEAT_BAR_DOWNBEAT if (beat_counter % num == 0) else BEAT_OFFBEAT
        beat_events.append((current_tick, "note_on", pitch, 100))
        beat_events.append((current_tick + 60, "note_off", pitch, 0))
        current_tick += TICKS_PER_BEAT
        beat_counter += 1

    _append_timed_events_to_track(beat_track, beat_events)
    beat_track.append(MetaMessage('end_of_track', time=0))

    # -------------------------------------------------------------
    # PISTA 2: EVENTS (Seções e Marcadores)
    # -------------------------------------------------------------
    events_track = MidiTrack()
    mid.tracks.append(events_track)
    events_track.append(MetaMessage('track_name', name='EVENTS', time=0))

    raw_events = [(0, "[music_start]")]
    if song.events:
        for ev in song.events:
            raw_events.append((ev.time_ms, ev.text))
    else:
        # Gera seções canônicas de treino padrão Rock Band
        bpm = max(40.0, song.bpm)
        measure_ms = (60.0 / bpm) * 4000.0
        canonical_sections = [
            (0, "[section intro]"),
            (int(4 * measure_ms), "[section verse_1]"),
            (int(12 * measure_ms), "[section chorus_1]"),
            (int(20 * measure_ms), "[section verse_2]"),
            (int(28 * measure_ms), "[section chorus_2]"),
            (int(36 * measure_ms), "[section solo]"),
            (int(44 * measure_ms), "[section outro]"),
        ]
        for t_sec, s_text in canonical_sections:
            if t_sec < total_duration_ms:
                raw_events.append((t_sec, s_text))

    raw_events.append((total_duration_ms, "[end]"))
    raw_events.sort(key=lambda x: x[0])

    last_tick = 0
    for ms, text in raw_events:
        target_tick = ms_to_ticks(ms, song.bpm)
        delta = max(0, target_tick - last_tick)
        events_track.append(MetaMessage('text', text=text, time=delta))
        last_tick = target_tick
    events_track.append(MetaMessage('end_of_track', time=0))

    # Garante que todas as 4 dificuldades (Expert, Hard, Medium, Easy) existam nas trilhas
    from src.creator.auto_charter import recalculate_track_difficulties
    for inst_key in ["guitar", "bass", "drum", "keys"]:
        notes_list = getattr(song, f"{inst_key}_notes", [])
        if notes_list:
            has_lower = any(n.difficulty in ["Hard", "Medium", "Easy"] for n in notes_list)
            if not has_lower:
                recalculate_track_difficulties(song, [inst_key])

    # -------------------------------------------------------------
    # PISTA 3: PART GUITAR
    # -------------------------------------------------------------
    if song.guitar_notes:
        guitar_track = MidiTrack()
        mid.tracks.append(guitar_track)
        guitar_track.append(MetaMessage('track_name', name='PART GUITAR', time=0))
        _build_instrument_track(guitar_track, song.guitar_notes, FRET_NOTES, GUITAR_OVERDRIVE, song.bpm)
        guitar_track.append(MetaMessage('end_of_track', time=0))

    # -------------------------------------------------------------
    # PISTA 4: PART BASS
    # -------------------------------------------------------------
    if song.bass_notes:
        bass_track = MidiTrack()
        mid.tracks.append(bass_track)
        bass_track.append(MetaMessage('track_name', name='PART BASS', time=0))
        _build_instrument_track(bass_track, song.bass_notes, FRET_NOTES, GUITAR_OVERDRIVE, song.bpm)
        bass_track.append(MetaMessage('end_of_track', time=0))

    # -------------------------------------------------------------
    # PISTA 5: PART DRUMS
    # -------------------------------------------------------------
    if song.drum_notes:
        drum_track = MidiTrack()
        mid.tracks.append(drum_track)
        drum_track.append(MetaMessage('track_name', name='PART DRUMS', time=0))
        _build_instrument_track(drum_track, song.drum_notes, DRUM_NOTES, DRUM_OVERDRIVE, song.bpm)
        drum_track.append(MetaMessage('end_of_track', time=0))

    # -------------------------------------------------------------
    # PISTA 6: PART KEYS
    # -------------------------------------------------------------
    if song.keys_notes:
        keys_track = MidiTrack()
        mid.tracks.append(keys_track)
        keys_track.append(MetaMessage('track_name', name='PART KEYS', time=0))
        _build_instrument_track(keys_track, song.keys_notes, FRET_NOTES, KEYS_OVERDRIVE, song.bpm)
        keys_track.append(MetaMessage('end_of_track', time=0))

    # -------------------------------------------------------------
    # PISTA 7: PART VOCALS (Melodias, Letras e Frases)
    # -------------------------------------------------------------
    if song.vocal_notes:
        vocal_track = MidiTrack()
        mid.tracks.append(vocal_track)
        vocal_track.append(MetaMessage('track_name', name='PART VOCALS', time=0))
        _build_vocal_track(vocal_track, song.vocal_notes, song.bpm)
        vocal_track.append(MetaMessage('end_of_track', time=0))

    return mid

def _build_vocal_track(track: MidiTrack, notes: list, bpm: float):
    """
    Constrói a trilha PART VOCALS conforme a especificação oficial Rock Band:
    - Alturas tonais reais (36 a 84)
    - Letras cantadas sincronizadas (MetaMessage lyrics)
    - Frases vocais (Nota 105)
    - Frases de Overdrive (Nota 106)
    - Pandeiro / Percussão (Nota 116)
    """
    events = []
    
    # Agrupa notas em frases para demarcar com a nota 105
    phrase_start_tick = None
    phrase_end_tick = None
    is_od_phrase = False

    for n in notes:
        s_tick = ms_to_ticks(n.time_ms, bpm)
        dur_ticks = max(80, ms_to_ticks(n.duration_ms, bpm))
        e_tick = s_tick + dur_ticks

        if phrase_start_tick is None:
            phrase_start_tick = max(0, s_tick - 40)
            is_od_phrase = n.is_overdrive

        pitch = VOCAL_TALKIE if n.is_talkie else n.pitch

        # Letra/sílaba anexada no tempo exato
        if n.lyric:
            events.append((s_tick, "lyric", n.lyric, 0))

        # Nota cantada
        events.append((s_tick, "note_on", pitch, 100))
        events.append((e_tick, "note_off", pitch, 0))

        phrase_end_tick = e_tick + 40

        # Se for fim de frase (ou última nota)
        if n.is_phrase_end:
            # Nota 105 demarca a frase vocal completa
            events.append((phrase_start_tick, "note_on", VOCAL_PHRASE_MARKER, 100))
            events.append((phrase_end_tick, "note_off", VOCAL_PHRASE_MARKER, 0))

            # Se a frase tem Overdrive (Nota 106)
            if is_od_phrase or n.is_overdrive:
                events.append((phrase_start_tick, "note_on", VOCAL_OVERDRIVE, 100))
                events.append((phrase_end_tick, "note_off", VOCAL_OVERDRIVE, 0))

            phrase_start_tick = None
            phrase_end_tick = None
            is_od_phrase = False

    # Fecha frase restante se houver
    if phrase_start_tick is not None and phrase_end_tick is not None:
        events.append((phrase_start_tick, "note_on", VOCAL_PHRASE_MARKER, 100))
        events.append((phrase_end_tick, "note_off", VOCAL_PHRASE_MARKER, 0))
        if is_od_phrase:
            events.append((phrase_start_tick, "note_on", VOCAL_OVERDRIVE, 100))
            events.append((phrase_end_tick, "note_off", VOCAL_OVERDRIVE, 0))

    # Ordena e insere na track
    events.sort(key=lambda x: (x[0], 0 if x[1] == "note_off" else 1))
    last_tick = 0
    for tick, ev_type, val, vel in events:
        delta = max(0, tick - last_tick)
        if ev_type == "lyric":
            track.append(MetaMessage("lyrics", text=val, time=delta))
        else:
            track.append(Message(ev_type, note=val, velocity=vel, time=delta))
        last_tick = tick

def _build_instrument_track(track: MidiTrack, notes: list[NoteEvent], note_map: dict, overdrive_note: int, bpm: float):
    """Converte lista de NoteEvent em mensagens note_on e note_off com deltas corretos."""
    timed_events = []
    for n in notes:
        diff_map = note_map.get(n.difficulty, note_map.get("Expert", {}))
        pitch = diff_map.get(n.lane)
        if pitch is not None:
            start_tick = ms_to_ticks(n.time_ms, bpm)
            duration_ticks = max(120, ms_to_ticks(n.duration_ms, bpm))
            end_tick = start_tick + duration_ticks

            timed_events.append((start_tick, "note_on", pitch, 100))
            timed_events.append((end_tick, "note_off", pitch, 0))

            # Se for overdrive
            if n.is_overdrive:
                timed_events.append((start_tick, "note_on", overdrive_note, 100))
                timed_events.append((end_tick, "note_off", overdrive_note, 0))

    _append_timed_events_to_track(track, timed_events)

def _append_timed_events_to_track(track: MidiTrack, timed_events: list):
    """Ordena eventos por tick absoluto e insere na track com delta-times."""
    timed_events.sort(key=lambda x: (x[0], 0 if x[1] == "note_off" else 1))
    last_tick = 0
    for tick, ev_type, pitch, vel in timed_events:
        delta = max(0, tick - last_tick)
        track.append(Message(ev_type, note=pitch, velocity=vel, time=delta))
        last_tick = tick

def save_midi(mid: MidiFile, filepath: str):
    """Salva o arquivo MIDI no caminho especificado."""
    mid.save(filepath)
