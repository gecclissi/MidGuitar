"""
Gerador de Arquivos MIDI no Padrão Rock Band Network (RBN / C3) e Clone Hero.
Converte objetos ChartSong em arquivos .mid com trilhas separadas:
PART GUITAR, PART BASS, PART DRUMS, PART KEYS, BEAT e EVENTS.

Todas as conversões ms <-> tick passam pelo mapa de tempo da música
(várias mudanças de tempo e de compasso), para o chart ficar em sincronia.
"""

from collections import defaultdict

from mido import MidiFile, MidiTrack, Message, MetaMessage
from src.creator.chart_model import ChartSong
from src.creator.tempo_map import TempoMap
from src.creator.rbn_specs import (
    TICKS_PER_BEAT,
    FRET_NOTES, DRUM_NOTES, BEAT_BAR_DOWNBEAT, BEAT_OFFBEAT,
    GUITAR_OVERDRIVE, DRUM_OVERDRIVE, KEYS_OVERDRIVE,
    VOCAL_PHRASE_MARKER, VOCAL_OVERDRIVE, VOCAL_TALKIE
)

MIN_NOTE_TICKS = 120        # Duração mínima de uma nota de instrumento
MIN_VOCAL_TICKS = 80        # Duração mínima de uma nota vocal
BEAT_NOTE_TICKS = 60        # Duração das notas da trilha BEAT
STRIPPED_MARKERS = ("[music_start]", "[music_end]", "[end]")


def ms_to_ticks(ms: int, bpm: float) -> int:
    """Converte milissegundos em ticks MIDI baseado no BPM (tempo constante, truncado)."""
    us_per_beat = TempoMap.constant(bpm).tempos[0].us_per_beat
    return int(ms * 1000.0 * TICKS_PER_BEAT / us_per_beat)


def ticks_to_ms(ticks: int, bpm: float) -> int:
    """Converte ticks MIDI em milissegundos (tempo constante, truncado)."""
    return int(TempoMap.constant(bpm).tick_to_ms(ticks))


def _song_tempo_map(song: ChartSong) -> TempoMap:
    """Mapa de tempo da música na resolução de saída (TICKS_PER_BEAT)."""
    tm = song.get_tempo_map()
    if tm.ticks_per_beat != TICKS_PER_BEAT:
        tm = tm.rescaled(TICKS_PER_BEAT)
    return tm


def _note_ticks(tm: TempoMap, time_ms: float, duration_ms: float, min_ticks: int):
    """(início, fim) em ticks de uma nota, com duração mínima."""
    start = max(0, tm.ms_to_tick(time_ms))  # tempo negativo vira 0 (deltas nunca negativos)
    end = max(start + min_ticks, tm.ms_to_tick(time_ms + duration_ms))
    return start, end


def generate_rbn_midi(song: ChartSong, total_duration_ms: int = None, include_rb3_tracks: bool = True) -> MidiFile:
    """
    Gera um MidiFile (Type 1) 100% compatível com Rock Band 3, Rock Band 2, Clone Hero e YARG.
    Se include_rb3_tracks=False (modo Rock Band 2 / Band Hero), omite trilhas exclusivas do RB3
    (PART KEYS, PART REAL_GUITAR, PART REAL_BASS, PART REAL_KEYS_X/H/M/E) para evitar incompatibilidades.
    """
    effective_dur = song.get_effective_duration_ms() if hasattr(song, "get_effective_duration_ms") else 180000
    if total_duration_ms is None or total_duration_ms == 180000:
        total_duration_ms = effective_dur
    else:
        total_duration_ms = max(total_duration_ms, effective_dur)

    tm = _song_tempo_map(song)
    total_ticks = tm.ms_to_tick(total_duration_ms)
    mid = MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)

    # -------------------------------------------------------------
    # PISTA 0: TEMPO & ASSINATURA DE TEMPO (mapa completo)
    # -------------------------------------------------------------
    tempo_track = MidiTrack()
    mid.tracks.append(tempo_track)
    meta = [(s.tick, 0, MetaMessage('time_signature', numerator=s.numerator, denominator=s.denominator,
                                    clocks_per_click=24, notated_32nd_notes_per_beat=8))
            for s in tm.time_sigs]
    meta += [(t.tick, 1, MetaMessage('set_tempo', tempo=t.us_per_beat)) for t in tm.tempos]
    _append_meta(tempo_track, meta)
    tempo_track.append(MetaMessage('end_of_track', time=0))

    # -------------------------------------------------------------
    # PISTA 1: BEAT (12 no primeiro tempo do compasso, 13 nos demais)
    # -------------------------------------------------------------
    beat_grid = _beat_grid(tm, total_ticks)
    beat_track = MidiTrack()
    mid.tracks.append(beat_track)
    beat_track.append(MetaMessage('track_name', name='BEAT', time=0))
    beat_notes = []
    for i, (tick, is_downbeat) in enumerate(beat_grid):
        next_tick = beat_grid[i + 1][0] if i + 1 < len(beat_grid) else tick + BEAT_NOTE_TICKS
        end = tick + max(1, min(BEAT_NOTE_TICKS, next_tick - tick))
        beat_notes.append((tick, end, BEAT_BAR_DOWNBEAT if is_downbeat else BEAT_OFFBEAT, 100))
    _emit_track(beat_track, beat_notes)
    beat_track.append(MetaMessage('end_of_track', time=0))

    # -------------------------------------------------------------
    # PISTA 2: EVENTS (preenchida depois das notas, para achar [music_end])
    # -------------------------------------------------------------
    events_track = MidiTrack()
    mid.tracks.append(events_track)

    # Garante que todas as 4 dificuldades (Expert, Hard, Medium, Easy) existam nas trilhas
    from src.creator.auto_charter import recalculate_track_difficulties
    for inst_key in ["guitar", "bass", "drum", "keys"]:
        notes_list = getattr(song, f"{inst_key}_notes", [])
        if notes_list:
            has_lower = any(n.difficulty in ["Hard", "Medium", "Easy"] for n in notes_list)
            if not has_lower:
                recalculate_track_difficulties(song, [inst_key])

    last_note_tick = None

    def add_track(name, build, *args):
        nonlocal last_note_tick
        track = MidiTrack()
        mid.tracks.append(track)
        track.append(MetaMessage('track_name', name=name, time=0))
        last = build(track, *args)
        track.append(MetaMessage('end_of_track', time=0))
        if last is not None:
            last_note_tick = last if last_note_tick is None else max(last_note_tick, last)

    # PISTAS 3..6: instrumentos de 5 lanes / bateria
    if song.guitar_notes:
        add_track('PART GUITAR', _build_instrument_track, song.guitar_notes, FRET_NOTES, GUITAR_OVERDRIVE, tm)
    if song.bass_notes:
        add_track('PART BASS', _build_instrument_track, song.bass_notes, FRET_NOTES, GUITAR_OVERDRIVE, tm)
    if song.drum_notes:
        add_track('PART DRUMS', _build_instrument_track, song.drum_notes, DRUM_NOTES, DRUM_OVERDRIVE, tm)
    if include_rb3_tracks and song.keys_notes:
        add_track('PART KEYS', _build_instrument_track, song.keys_notes, FRET_NOTES, KEYS_OVERDRIVE, tm)

    # PISTA 7: PART VOCALS (Melodias, Letras e Frases)
    if song.vocal_notes:
        add_track('PART VOCALS', _build_vocal_track, song.vocal_notes, tm)

    # PISTAS 8/9: PART REAL_GUITAR / PART REAL_BASS (Exclusivo RB3)
    if include_rb3_tracks and getattr(song, "pro_guitar_notes", None):
        add_track('PART REAL_GUITAR', _build_pro_guitar_track, song.pro_guitar_notes, tm)
    if include_rb3_tracks and getattr(song, "pro_bass_notes", None):
        add_track('PART REAL_BASS', _build_pro_guitar_track, song.pro_bass_notes, tm)

    # PISTAS 10..13: PART REAL_KEYS_X / H / M / E (Pro Keys 25 Teclas Reais - Exclusivo RB3)
    if include_rb3_tracks and getattr(song, "pro_keys_notes", None):
        for diff_name, suffix in [("Expert", "X"), ("Hard", "H"), ("Medium", "M"), ("Easy", "E")]:
            diff_pk_notes = [n for n in song.pro_keys_notes if n.difficulty == diff_name]
            if not diff_pk_notes:
                diff_pk_notes = [n for n in song.pro_keys_notes if n.difficulty == "Expert"]
            if diff_pk_notes:
                add_track(f'PART REAL_KEYS_{suffix}', _build_pro_keys_track, diff_pk_notes, tm)

    _build_events_track(events_track, song, tm, beat_grid, total_duration_ms, total_ticks, last_note_tick)
    return mid


def _beat_grid(tm: TempoMap, total_ticks: int) -> list:
    """Batidas (tick, é_primeiro_tempo) até total_ticks, seguindo os compassos do mapa.

    Cada batida dura ticks_per_beat * 4 / denominador; cada mudança de compasso
    começa um compasso novo.
    """
    grid = []
    sigs = tm.time_sigs
    for i, sig in enumerate(sigs):
        seg_end = min(sigs[i + 1].tick if i + 1 < len(sigs) else total_ticks, total_ticks)
        beat_len = tm.ticks_per_beat * 4 / sig.denominator
        num = max(1, sig.numerator)
        k = 0
        tick = sig.tick
        while tick < seg_end:
            grid.append((tick, k % num == 0))
            k += 1
            tick = sig.tick + int(round(k * beat_len))
    return grid


def _build_events_track(track: MidiTrack, song: ChartSong, tm: TempoMap, beat_grid: list,
                        total_duration_ms: int, total_ticks: int, last_note_tick):
    """Seções e marcadores: um único [music_start], [music_end] e [end], nessa ordem."""
    track.append(MetaMessage('track_name', name='EVENTS', time=0))
    texts = []  # (tick, ordem, texto)
    if song.events:
        for ev in song.events:
            if ev.text.strip() in STRIPPED_MARKERS:
                continue
            texts.append((max(0, tm.ms_to_tick(ev.time_ms)), 1, ev.text))
    else:
        # Seções canônicas de treino padrão Rock Band, no início dos compassos do mapa
        downbeats = [t for t, is_down in beat_grid if is_down]
        canonical_sections = [
            (0, "[section intro]"), (4, "[section verse_1]"), (12, "[section chorus_1]"),
            (20, "[section verse_2]"), (28, "[section chorus_2]"), (36, "[section solo]"),
            (44, "[section outro]"),
        ]
        for measure, s_text in canonical_sections:
            if measure < len(downbeats) and downbeats[measure] < total_ticks:
                texts.append((downbeats[measure], 1, s_text))

    if last_note_tick is None:
        music_end_tick = tm.ms_to_tick(max(0, total_duration_ms - 1000))
    else:
        music_end_tick = last_note_tick
    end_tick = max(total_ticks, music_end_tick + 1)
    if texts:
        # Eventos do usuário depois do fim previsto: [end] sempre vem por último
        end_tick = max(end_tick, max(t for t, _o, _x in texts) + 1)

    texts.append((0, 0, "[music_start]"))
    texts.append((music_end_tick, 2, "[music_end]"))
    texts.append((end_tick, 3, "[end]"))
    _append_meta(track, [(t, order, MetaMessage('text', text=txt)) for t, order, txt in texts])
    track.append(MetaMessage('end_of_track', time=0))


def _append_meta(track: MidiTrack, items: list):
    """Insere (tick, ordem, MetaMessage) ordenados, convertendo para delta-times."""
    last_tick = 0
    for tick, _order, msg in sorted(items, key=lambda x: (x[0], x[1])):
        msg.time = tick - last_tick
        track.append(msg)
        last_tick = tick


def _merge_intervals(intervals: list) -> list:
    """Une intervalos (início, fim) que se sobrepõem ou se tocam em frases contínuas."""
    merged = []
    for s, e in sorted(iv for iv in intervals if iv[1] > iv[0]):
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged]


def _resolve_overlaps(notes: list) -> list:
    """Remove sobreposições por altura.

    notes: (início, fim, altura, velocity, é_marcador). Duplicatas no mesmo
    tick e altura são descartadas (fica a mais longa); se o fim de uma nota
    passa do próximo note_on da mesma altura, é recortado para esse tick
    (o recorte vence a duração mínima). Notas de duração zero não saem.
    """
    by_pitch = defaultdict(list)
    for s, e, p, v, mk in notes:
        by_pitch[p].append((s, e, v, mk))
    out = []
    for p, items in by_pitch.items():
        items.sort(key=lambda x: (x[0], -x[1]))
        uniq = []
        for item in items:
            if uniq and uniq[-1][0] == item[0]:
                continue
            uniq.append(item)
        for i, (s, e, v, mk) in enumerate(uniq):
            if i + 1 < len(uniq):
                e = min(e, uniq[i + 1][0])
            if e > s:
                out.append((s, e, p, v, mk))
    return out


def _emit_track(track: MidiTrack, notes: list, markers: dict = None, lyrics: list = None):
    """Grava notas, frases marcadoras e letras na trilha, sem notas sobrepostas.

    notes: (início, fim, altura, velocity) tocáveis; markers: {altura: [(início, fim)]},
    unidos em frases contínuas e gravados uma vez cada; lyrics: [(tick, texto)].
    Retorna o tick do fim da última nota tocável (ou None).
    """
    all_notes = [(s, e, p, v, False) for s, e, p, v in notes]
    for pitch, intervals in (markers or {}).items():
        all_notes += [(s, e, pitch, 100, True) for s, e in _merge_intervals(intervals)]
    resolved = _resolve_overlaps(all_notes)

    # Ordem no mesmo tick: note_off, letra, note_on
    events = []
    for s, e, p, v, _mk in resolved:
        events.append((s, 2, Message('note_on', note=p, velocity=v)))
        events.append((e, 0, Message('note_off', note=p, velocity=0)))
    for tick, text in (lyrics or []):
        events.append((tick, 1, MetaMessage('lyrics', text=text)))
    events.sort(key=lambda x: (x[0], x[1]))
    last_tick = 0
    for tick, _order, msg in events:
        msg.time = tick - last_tick
        track.append(msg)
        last_tick = tick

    ends = [e for _s, e, _p, _v, mk in resolved if not mk]
    return max(ends) if ends else None


def _build_vocal_track(track: MidiTrack, notes: list, tm: TempoMap):
    """
    Constrói a trilha PART VOCALS conforme a especificação oficial Rock Band:
    - Alturas tonais reais (36 a 84)
    - Letras cantadas sincronizadas (MetaMessage lyrics)
    - Frases vocais (Nota 105)
    - Frases de Overdrive (Nota 106)
    """
    sung, lyrics = [], []
    markers = {VOCAL_PHRASE_MARKER: [], VOCAL_OVERDRIVE: []}

    # Agrupa notas em frases para demarcar com a nota 105
    phrase_start_tick = None
    phrase_end_tick = None
    is_od_phrase = False

    def close_phrase(od: bool):
        markers[VOCAL_PHRASE_MARKER].append((phrase_start_tick, phrase_end_tick))
        if od:
            markers[VOCAL_OVERDRIVE].append((phrase_start_tick, phrase_end_tick))

    for n in notes:
        s_tick, e_tick = _note_ticks(tm, n.time_ms, n.duration_ms, MIN_VOCAL_TICKS)

        if phrase_start_tick is None:
            phrase_start_tick = max(0, s_tick - 40)
            is_od_phrase = n.is_overdrive

        pitch = VOCAL_TALKIE if n.is_talkie else n.pitch
        if n.lyric:
            lyrics.append((s_tick, n.lyric))
        sung.append((s_tick, e_tick, pitch, 100))
        phrase_end_tick = e_tick + 40

        if n.is_phrase_end:
            close_phrase(is_od_phrase or n.is_overdrive)
            phrase_start_tick = None
            phrase_end_tick = None
            is_od_phrase = False

    # Fecha frase restante se houver
    if phrase_start_tick is not None and phrase_end_tick is not None:
        close_phrase(is_od_phrase)

    return _emit_track(track, sung, markers, lyrics)


def _build_instrument_track(track: MidiTrack, notes: list, note_map: dict, overdrive_note: int, tm: TempoMap):
    """Converte lista de NoteEvent em note_on/note_off, com frases de Overdrive unidas.

    NoteEvent com lane "overdrive" (Star Power do auto_charter) vira uma frase
    de overdrive cobrindo time_ms .. time_ms + duration_ms.
    """
    playable, od = [], []
    for n in notes:
        if n.lane == "overdrive":
            od.append(_note_ticks(tm, n.time_ms, n.duration_ms, 1))
            continue
        diff_map = note_map.get(n.difficulty, note_map.get("Expert", {}))
        pitch = diff_map.get(n.lane)
        if pitch is None:
            continue
        start, end = _note_ticks(tm, n.time_ms, n.duration_ms, MIN_NOTE_TICKS)
        playable.append((start, end, pitch, 100))
        if n.is_overdrive:
            od.append((start, end))
    return _emit_track(track, playable, {overdrive_note: od})


def _build_pro_guitar_track(track: MidiTrack, notes: list, tm: TempoMap):
    """
    Constrói a trilha PART REAL_GUITAR / PART REAL_BASS conforme a especificação RBN2:
    - Pitch = Base da Dificuldade (Easy=24, Medium=48, Hard=72, Expert=96) + índice da corda (0 a 5)
    - Velocity = 100 + número da casa/traste (0 a 17, logo velocity 100 a 117)
    """
    from src.creator.rbn_specs import PRO_GUITAR_STRING_BASE, PRO_GUITAR_OVERDRIVE
    playable, od = [], []
    for n in notes:
        base_pitch = PRO_GUITAR_STRING_BASE.get(n.difficulty, 96)
        pitch = base_pitch + max(0, min(5, int(n.string_idx)))
        vel = 100 + max(0, min(17, int(n.fret)))
        start, end = _note_ticks(tm, n.time_ms, n.duration_ms, MIN_NOTE_TICKS)
        playable.append((start, end, pitch, vel))
        if getattr(n, "is_overdrive", False):
            od.append((start, end))
    return _emit_track(track, playable, {PRO_GUITAR_OVERDRIVE: od})


def _build_pro_keys_track(track: MidiTrack, notes: list, tm: TempoMap):
    """
    Constrói as trilhas PART REAL_KEYS_X / H / M / E (Teclado Real de 25 Teclas C3=48 a C5=72).
    Inclui também a nota âncora de Range Shift (Nota 0 = C3..C5) no início da trilha.
    """
    playable = [(0, 120, 0, 100)]
    od = []
    for n in notes:
        pitch = max(48, min(72, int(n.pitch)))
        start, end = _note_ticks(tm, n.time_ms, n.duration_ms, MIN_NOTE_TICKS)
        playable.append((start, end, pitch, 100))
        if getattr(n, "is_overdrive", False):
            od.append((start, end))
    return _emit_track(track, playable, {KEYS_OVERDRIVE: od})


def save_midi(mid: MidiFile, filepath: str):
    """Salva o arquivo MIDI no caminho especificado."""
    mid.save(filepath)
