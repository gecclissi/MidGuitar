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
from src.creator.tempo_map import TempoMap, TempoChange, TimeSigChange

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
            song.diff_guitar = max(0, int(meta.get("diff_guitar", song.diff_guitar)))
            song.diff_bass = max(0, int(meta.get("diff_bass", song.diff_bass)))
            song.diff_drums = max(0, int(meta.get("diff_drums", song.diff_drums)))
            song.diff_keys = max(0, int(meta.get("diff_keys", song.diff_keys)))
            song.diff_band = max(0, int(meta.get("diff_band", song.diff_band)))
        except Exception:
            pass
    else:
        # 1.1 Busca songs.dta caso seja uma pasta de Rock Band 2 / 3
        dta_candidates = [os.path.join(folder_path, "songs.dta"), os.path.join(os.path.dirname(folder_path), "songs.dta")]
        for dta_p in dta_candidates:
            if os.path.exists(dta_p):
                try:
                    import re
                    with open(dta_p, "r", encoding="utf-8", errors="ignore") as df:
                        dta_txt = df.read()
                    m_name = re.search(r'\(name\s+"([^"]+)"\)', dta_txt)
                    m_art = re.search(r'\(artist\s+"([^"]+)"\)', dta_txt)
                    m_alb = re.search(r'\(album_name\s+"([^"]+)"\)', dta_txt)
                    m_yr = re.search(r'\(year_released\s+(\d+)\)', dta_txt)
                    if m_name: song.title = m_name.group(1)
                    if m_art: song.artist = m_art.group(1)
                    if m_alb: song.album = m_alb.group(1)
                    if m_yr: song.year = int(m_yr.group(1))
                    break
                except Exception:
                    pass

    # 1.2 Busca imagem de capa (album.png, cover.png, ICON0.PNG)
    for f in os.listdir(folder_path):
        f_lower = f.lower()
        if f_lower in ["album.png", "album.jpg", "album.jpeg", "cover.png", "cover.jpg", "icon0.png"]:
            song.album_art_path = os.path.join(folder_path, f)
            break

    # 2. Busca arquivos de áudio (Stems individuais, mixagem geral ou .mogg oficial do RB3)
    for f in os.listdir(folder_path):
        f_lower = f.lower()
        full_p = os.path.join(folder_path, f)
        if f_lower.endswith(".mogg"):
            from src.creator.mogg_generator import extract_ogg_from_mogg
            extracted_ogg = os.path.join(folder_path, f"{os.path.splitext(f)[0]}_extracted.ogg")
            if extract_ogg_from_mogg(full_p, extracted_ogg):
                song.audio_stems.append(extracted_ogg)
                if not song.audio_path:
                    song.audio_path = extracted_ogg
        elif f_lower.endswith((".ogg", ".mp3", ".wav", ".flac", ".opus")):
            song.audio_stems.append(full_p)
            stem_base = os.path.splitext(f_lower)[0]
            if stem_base in ["song", "guitar", "audio"] and not song.audio_path:
                song.audio_path = full_p

    if not song.audio_path and song.audio_stems:
        song.audio_path = song.audio_stems[0]

    # 3. Busca arquivos de letra (.txt / .lrc / .srt)
    for f in os.listdir(folder_path):
        f_lower = f.lower()
        if f_lower in ["lyrics.txt", "song.lrc", "lyrics.lrc", "letra.txt", "words.txt", "lyrics.srt", "song.srt"] or f_lower.endswith((".lrc", ".srt")):
            try:
                with open(os.path.join(folder_path, f), "r", encoding="utf-8-sig", errors="ignore") as lf:
                    song.lyrics_raw = lf.read()
                    break
            except Exception:
                pass

    # 4. Busca e analisa notes.mid ou notes.chart
    mid_file = os.path.join(folder_path, "notes.mid")
    if not os.path.exists(mid_file):
        for f in os.listdir(folder_path):
            if f.lower().endswith(".mid"):
                mid_file = os.path.join(folder_path, f)
                break

    chart_file = os.path.join(folder_path, "notes.chart")
    if not os.path.exists(chart_file):
        for f in os.listdir(folder_path):
            if f.lower().endswith(".chart"):
                chart_file = os.path.join(folder_path, f)
                break

    if os.path.exists(mid_file):
        try:
            mid = MidiFile(mid_file)
            _parse_midi_into_song(mid, song)
        except Exception as e:
            print(f"[ChartImporter] Erro ao analisar MIDI {mid_file}: {e}")
    elif os.path.exists(chart_file):
        try:
            _parse_chart_file_into_song(chart_file, song)
        except Exception as e:
            print(f"[ChartImporter] Erro ao analisar CHART {chart_file}: {e}")

    # Se carregou lyrics_raw mas não tinha vocal_notes, aplica alinhamento automático
    if song.lyrics_raw and not song.vocal_notes:
        from src.creator.lyric_processor import align_lyrics_to_song
        align_lyrics_to_song(song, song.lyrics_raw)

    # Garante que todas as 4 dificuldades existam para qualquer instrumento carregado
    from src.creator.auto_charter import recalculate_track_difficulties
    for inst_key in ["guitar", "bass", "drum", "keys"]:
        notes_list = getattr(song, f"{inst_key}_notes", [])
        if notes_list and not any(n.difficulty in ["Hard", "Medium", "Easy"] for n in notes_list):
            recalculate_track_difficulties(song, [inst_key])

    return song


def _parse_chart_file_into_song(chart_path: str, song: ChartSong):
    """Analisa arquivos notes.chart do Clone Hero / Moonscraper / Feedback."""
    import re
    with open(chart_path, "r", encoding="utf-8-sig", errors="ignore") as f:
        text = f.read()

    resolution = 192
    current_section = ""
    tempo_changes = []   # TempoChange em ticks do .chart
    sig_changes = []     # TimeSigChange em ticks do .chart
    pending_notes = []   # (inst, diff, lane, tick, sustain_ticks), convertidos no fim

    section_map = {
        "EXPERTSINGLE": ("guitar", "Expert"),
        "HARDSINGLE": ("guitar", "Hard"),
        "MEDIUMSINGLE": ("guitar", "Medium"),
        "EASYSINGLE": ("guitar", "Easy"),
        "EXPERTDOUBLEBASS": ("bass", "Expert"),
        "HARDDOUBLEBASS": ("bass", "Hard"),
        "MEDIUMDOUBLEBASS": ("bass", "Medium"),
        "EASYDOUBLEBASS": ("bass", "Easy"),
        "EXPERTDRUMS": ("drum", "Expert"),
        "HARDDRUMS": ("drum", "Hard"),
        "MEDIUMDRUMS": ("drum", "Medium"),
        "EASYDRUMS": ("drum", "Easy"),
        "EXPERTKEYBOARD": ("keys", "Expert"),
        "HARDKEYBOARD": ("keys", "Hard"),
        "MEDIUMKEYBOARD": ("keys", "Medium"),
        "EASYKEYBOARD": ("keys", "Easy"),
    }
    fret_idx_to_lane = {0: "green", 1: "red", 2: "yellow", 3: "blue", 4: "orange"}
    drum_idx_to_lane = {0: "orange", 1: "red", 2: "yellow", 3: "blue", 4: "green"}

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line in ["{", "}"]:
            continue
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1].strip().upper()
            continue

        if current_section == "SONG":
            if "=" in line:
                k, v = [p.strip().strip('"') for p in line.split("=", 1)]
                kl = k.lower()
                if kl == "name" and song.title == "Nova Música":
                    song.title = v
                elif kl == "artist" and song.artist == "Artista Desconhecido":
                    song.artist = v
                elif kl == "resolution":
                    try:
                        resolution = max(1, int(v))
                    except Exception:
                        pass
        elif current_section == "SYNCTRACK":
            # Ex: 0 = B 120000  /  0 = TS 4  /  1536 = TS 6 3
            m = re.match(r'(\d+)\s*=\s*B\s+(\d+)', line)
            if m and int(m.group(2)) > 0:
                bpm_milli = int(m.group(2))
                us = int(round(60_000_000 / (bpm_milli / 1000.0)))
                tempo_changes.append(TempoChange(int(m.group(1)), us))
                continue
            m = re.match(r'(\d+)\s*=\s*TS\s+(\d+)(?:\s+(\d+))?', line)
            if m:
                den_exp = int(m.group(3)) if m.group(3) is not None else 2
                sig_changes.append(TimeSigChange(int(m.group(1)), int(m.group(2)), 2 ** den_exp))
        elif current_section in section_map:
            inst, diff = section_map[current_section]
            # Ex: 768 = N 0 0
            m = re.match(r'(\d+)\s*=\s*N\s+(\d+)\s+(\d+)', line)
            if m:
                tick = int(m.group(1))
                n_idx = int(m.group(2))
                sustain_ticks = int(m.group(3))
                lane_map = drum_idx_to_lane if inst == "drum" else fret_idx_to_lane
                if n_idx in lane_map:
                    pending_notes.append((inst, diff, lane_map[n_idx], tick, sustain_ticks))

    # Monta o mapa de tempo com o arquivo inteiro lido (as seções de notas podem vir antes do SyncTrack)
    tm = TempoMap(resolution, tempo_changes, sig_changes)
    for inst, diff, lane, tick, sustain_ticks in pending_notes:
        start_ms = int(round(tm.tick_to_ms(tick)))
        dur_ms = max(120, int(round(tm.tick_to_ms(tick + sustain_ticks) - tm.tick_to_ms(tick))))
        song.add_note(inst, NoteEvent(time_ms=start_ms, lane=lane, duration_ms=dur_ms, difficulty=diff))
    song.tempo_map = tm.rescaled(TICKS_PER_BEAT)
    song.bpm = round(song.tempo_map.initial_bpm(), 2)


# Trilhas de 5 lanes editáveis -> atributo do ChartSong
_FIVE_LANE_TRACKS = {"PART GUITAR": "guitar", "PART BASS": "bass", "PART KEYS": "keys"}
_PRO_KEYS_TRACKS = {"PART REAL_KEYS_X": "Expert", "PART REAL_KEYS_H": "Hard",
                    "PART REAL_KEYS_M": "Medium", "PART REAL_KEYS_E": "Easy"}
# Marcadores de HOPO/palhetada forçados não são notas tocáveis: vão para o passthrough
_FORCED_LANES = ("force_hopo", "force_strum")


def _inverse_map(note_map: dict) -> dict:
    inv = {}
    for diff, lanes in note_map.items():
        for lane, pitch in lanes.items():
            if lane not in _FORCED_LANES:
                inv[pitch] = (lane, diff)
    return inv


def _ms_span(tm: TempoMap, start: int, end: int):
    """(início, duração) em ms inteiros; início + duração = fim arredondado (sem piso)."""
    s = int(round(tm.tick_to_ms(start)))
    return s, max(0, int(round(tm.tick_to_ms(end))) - s)


def _parse_midi_into_song(mid: MidiFile, song: ChartSong):
    """Extrai notas, mapa de tempo, eventos e o passthrough das trilhas do MIDI.

    Trilhas editáveis (PART GUITAR/BASS/DRUMS/KEYS/VOCALS/REAL_*) viram notas do
    modelo; o que o modelo não representa (marcadores, textos, canais, sysex) fica
    em song.track_extras. Trilhas que o MidGuitar não edita ficam inteiras em
    song.passthrough_tracks. Assim importar e exportar não perde nada.
    """
    from src.creator import passthrough as pt
    from src.creator.chart_model import ProGuitarNote, ProKeysNote, VocalNote
    from src.creator.rbn_specs import PRO_GUITAR_STRING_BASE, VOCAL_PITCH_MIN, VOCAL_PITCH_MAX, VOCAL_PHRASE_MARKER

    # Primeira passada: coleta tempos e fórmulas de compasso de TODAS as trilhas
    tempo_changes = []
    sig_changes = []
    for track in mid.tracks:
        abs_tick = 0
        for msg in track:
            abs_tick += msg.time
            if msg.type == 'set_tempo':
                tempo_changes.append(TempoChange(abs_tick, msg.tempo))
            elif msg.type == 'time_signature':
                sig_changes.append(TimeSigChange(abs_tick, msg.numerator, msg.denominator))
    src_tm = TempoMap(mid.ticks_per_beat, tempo_changes, sig_changes)
    song.tempo_map = src_tm.rescaled(TICKS_PER_BEAT)
    song.bpm = round(song.tempo_map.initial_bpm(), 2)
    tm = src_tm  # conversões tick -> ms usam a resolução do arquivo de origem

    inv_fret_notes = _inverse_map(FRET_NOTES)
    inv_drum_notes = _inverse_map(DRUM_NOTES)
    song.passthrough_tracks = []
    song.track_extras = {}

    for idx, track in enumerate(mid.tracks):
        name, notes, others, raw = pt.read_track(track, tm)
        upper = (name or "").strip().upper()

        # Trilha de tempo (1ª trilha do tipo 1, sem notas): o mapa já foi lido
        if idx == 0 and mid.type == 1 and not notes and upper not in pt.EDITABLE_TRACKS and upper != "EVENTS":
            song.tempo_track_name = name
            continue

        if upper == "EVENTS":
            for tick, msg in others:
                if msg.type == 'text':
                    song.events.append(TextEvent(time_ms=int(round(tm.tick_to_ms(tick))), text=msg.text))
            continue

        # Nomes EXATOS: customs reais trazem trilhas extras (PART GUITAR GHL,
        # PART ELITE_DRUMS, PART REAL_GUITAR_22, PART KEYS_ANIM_RH, HARM1...)
        # que não podem ser misturadas nas trilhas editadas pelo MidGuitar.
        if upper not in pt.EDITABLE_TRACKS:
            song.passthrough_tracks.append(pt.raw_track_from_midi(name, raw, tm))
            continue

        extras = pt.new_extras()
        lyrics_at = {}
        for tick, msg in others:
            if upper == "PART VOCALS" and msg.type == 'lyrics':
                lyrics_at.setdefault(tick, []).append(msg)
            else:
                pt.add_extra_event(extras, tm, tick, msg)

        phrase_ends = []
        sung = []
        for start, end, pitch, vel, ch in sorted(notes):
            t_ms, d_ms = _ms_span(tm, start, end)
            consumed = False
            if upper in _FIVE_LANE_TRACKS or upper == "PART DRUMS":
                inv = inv_drum_notes if upper == "PART DRUMS" else inv_fret_notes
                if ch == 0 and pitch in inv:
                    lane, diff = inv[pitch]
                    attr = "drum" if upper == "PART DRUMS" else _FIVE_LANE_TRACKS[upper]
                    getattr(song, f"{attr}_notes").append(NoteEvent(
                        time_ms=t_ms, lane=lane, duration_ms=d_ms, difficulty=diff, velocity=vel))
                    consumed = True
            elif upper == "PART VOCALS":
                if ch == 0 and VOCAL_PITCH_MIN <= pitch <= VOCAL_PITCH_MAX:
                    pending = lyrics_at.get(start)
                    lyric = pending.pop(0).text if pending else ""
                    note = VocalNote(time_ms=t_ms, duration_ms=d_ms, pitch=pitch, lyric=lyric, velocity=vel)
                    song.vocal_notes.append(note)
                    sung.append((start, note))
                    consumed = True
                elif pitch == VOCAL_PHRASE_MARKER:
                    phrase_ends.append(end)
            elif upper in ("PART REAL_GUITAR", "PART REAL_BASS"):
                if vel >= 100:
                    for diff, base_p in PRO_GUITAR_STRING_BASE.items():
                        if base_p <= pitch <= base_p + 5:
                            target = song.pro_bass_notes if upper == "PART REAL_BASS" else song.pro_guitar_notes
                            target.append(ProGuitarNote(
                                time_ms=t_ms, string_idx=pitch - base_p, fret=vel - 100,
                                duration_ms=d_ms, difficulty=diff, channel=ch))
                            consumed = True
                            break
            elif upper in _PRO_KEYS_TRACKS:
                if ch == 0 and 48 <= pitch <= 72:
                    song.pro_keys_notes.append(ProKeysNote(
                        time_ms=t_ms, pitch=pitch, duration_ms=d_ms,
                        difficulty=_PRO_KEYS_TRACKS[upper], velocity=vel))
                    consumed = True
            if not consumed:
                pt.add_extra_note(extras, tm, start, end, pitch, vel, ch)

        # Letras sem nota cantada no mesmo tick também são repassadas
        for tick, msgs in lyrics_at.items():
            for msg in msgs:
                pt.add_extra_event(extras, tm, tick, msg)
        # Fim de frase (nota 105): a última nota cantada que começa dentro da frase
        for p_end in phrase_ends:
            inside = [n for s, n in sung if s < p_end]
            if inside:
                inside[-1].is_phrase_end = True

        # Registrado mesmo vazio: marca a trilha como importada (o gerador não inventa âncoras)
        song.track_extras[upper] = extras

    # Ordena todas as trilhas por tempo
    song.guitar_notes.sort(key=lambda n: n.time_ms)
    song.bass_notes.sort(key=lambda n: n.time_ms)
    song.drum_notes.sort(key=lambda n: n.time_ms)
    song.keys_notes.sort(key=lambda n: n.time_ms)
    song.pro_guitar_notes.sort(key=lambda n: n.time_ms)
    song.pro_bass_notes.sort(key=lambda n: n.time_ms)
    song.pro_keys_notes.sort(key=lambda n: n.time_ms)
    song.vocal_notes.sort(key=lambda n: n.time_ms)
