"""
Gerador Inteligente Automático de Notas (Auto-Charter).
Gera automaticamente todas as trilhas e notas musicais sincronizadas ao BPM:
- 🎸 Guitarra (5 botões com acordes, solos e HOPOs)
- 🎸 Baixo (grooves de fundamental e pulso rítmico)
- 🥁 Bateria (bumbo, caixa, chimbal, pratos, viradas e fills)
- 🎹 Teclado (Keys com pads harmônicos e arpejos)
- 🎸 Pro Guitar (6 cordas / digitação real)
- 🎹 Pro Keys (teclas reais de piano)
- 🌟 Marcadores de Seções (intro, verso, refrão, solo) e Overdrive!
Gera automaticamente para todas as dificuldades (Expert, Hard, Medium, Easy).
"""

import math
from typing import List, Tuple
from src.creator.chart_model import ChartSong, NoteEvent, TextEvent, VocalNote

def get_audio_duration_ms(audio_path: str) -> int:
    """Tenta obter a duração real em milissegundos do arquivo de áudio."""
    try:
        from src.creator.mogg_generator import analyze_audio_file
        info = analyze_audio_file(audio_path)
        if info.get("duration_ms", 0) > 5000:
            return int(info["duration_ms"])
    except Exception:
        pass
    try:
        import pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        snd = pygame.mixer.Sound(audio_path)
        dur_sec = snd.get_length()
        if dur_sec > 5.0:
            return int(dur_sec * 1000)
    except Exception:
        pass
    return 180000 # 3 minutos padrão

def auto_generate_chart(
    song: ChartSong,
    total_duration_ms: int = 180000,
    selected_instruments: List[str] = None,
    intensity: str = "Rock",
    generate_all_diffs: bool = True,
    clear_existing: bool = True
) -> ChartSong:
    """
    Gera automaticamente notas completas, rítmicas e musicais sincronizadas com o BPM e energia do áudio.
    Se clear_existing for False, preserva as trilhas que já possuem notas!
    REGRA DE OURO DO MICROFONE: Se a música NÃO possuir letra (lyrics_raw vazio), NÃO gera vocais falsos!
    """
    first_sound_ms = 2000
    last_sound_ms = total_duration_ms - 2000
    energy_windows = []

    if song.audio_path:
        try:
            from src.creator.mogg_generator import analyze_audio_file
            info = analyze_audio_file(song.audio_path)
            if info.get("duration_ms", 0) > 5000:
                total_duration_ms = int(info["duration_ms"])
                first_sound_ms = max(500, int(info.get("first_sound_ms", 2000)))
                last_sound_ms = min(total_duration_ms - 500, int(info.get("last_sound_ms", total_duration_ms - 2000)))
                energy_windows = info.get("energy_windows", [])
                # Se o BPM ainda estava no padrão (120.0), usa o BPM real detectado do áudio!
                if abs(song.bpm - 120.0) < 0.1 and info.get("bpm"):
                    song.bpm = float(info["bpm"])
        except Exception:
            detected_dur = get_audio_duration_ms(song.audio_path)
            if detected_dur > 10000:
                total_duration_ms = detected_dur
                last_sound_ms = total_duration_ms - 2000

    if selected_instruments is None:
        selected_instruments = ["guitar", "bass", "drum", "keys"]

    # Validação estrita do Microfone: Sem letra = Sem microfone!
    has_real_lyrics = bool(song.lyrics_raw and song.lyrics_raw.strip())
    if "vocals" in selected_instruments and not has_real_lyrics:
        selected_instruments = [inst for inst in selected_instruments if inst != "vocals"]
        if clear_existing:
            song.vocal_notes.clear()

    bpm = max(30.0, song.bpm)
    beat_ms = (60.0 / bpm) * 1000.0          # Tempo de 1 semínima (1 batida)
    measure_ms = beat_ms * 4.0               # Tempo de 1 compasso (4/4)
    eighth_ms = beat_ms / 2.0                # Tempo de 1 colcheia
    total_measures = max(4, int(total_duration_ms / measure_ms))

    def _is_silent_at(t_ms: int) -> bool:
        if t_ms < first_sound_ms or t_ms > last_sound_ms:
            return True
        if energy_windows:
            idx = min(len(energy_windows) - 1, max(0, int(t_ms // 500)))
            if energy_windows[idx] < 0.04:
                return True
        return False

    # 1. Limpa trilhas que serão geradas (apenas se clear_existing for True)
    for inst in selected_instruments:
        if clear_existing:
            song.clear_track(inst)
    if clear_existing or not song.events:
        song.events.clear()
        # 2. Gera Seções Musicais (EVENTS)
        song.events.append(TextEvent(time_ms=0, text="[music_start]"))
        m_intro = min(4, total_measures // 8)
        m_verse1 = m_intro + min(8, total_measures // 5)
        m_chorus1 = m_verse1 + min(8, total_measures // 5)
        m_verse2 = m_chorus1 + min(8, total_measures // 5)
        m_solo = m_verse2 + min(6, total_measures // 6)
        m_chorus2 = m_solo + min(8, total_measures // 5)

        song.events.append(TextEvent(time_ms=int(m_intro * measure_ms), text="[section intro]"))
        song.events.append(TextEvent(time_ms=int(m_verse1 * measure_ms), text="[section verse1]"))
        song.events.append(TextEvent(time_ms=int(m_chorus1 * measure_ms), text="[section chorus1]"))
        song.events.append(TextEvent(time_ms=int(m_verse2 * measure_ms), text="[section verse2]"))
        song.events.append(TextEvent(time_ms=int(m_solo * measure_ms), text="[section solo]"))
        song.events.append(TextEvent(time_ms=int(m_chorus2 * measure_ms), text="[section chorus2]"))
        song.events.append(TextEvent(time_ms=max(0, total_duration_ms - 4000), text="[section outro]"))
    else:
        m_intro = min(4, total_measures // 8)
        m_verse1 = m_intro + min(8, total_measures // 5)
        m_chorus1 = m_verse1 + min(8, total_measures // 5)
        m_verse2 = m_chorus1 + min(8, total_measures // 5)
        m_solo = m_verse2 + min(6, total_measures // 6)
        m_chorus2 = m_solo + min(8, total_measures // 5)

    # Progressões de Acordes Simbolizadas (0=Verde, 1=Vermelho, 2=Amarelo, 3=Azul, 4=Laranja)
    chord_progression = [0, 2, 3, 1] # I - V - vi - IV clássico do Rock/Pop
    lanes_5 = ["green", "red", "yellow", "blue", "orange"]

    # 3. GERAR BATERIA
    if "drum" in selected_instruments and (clear_existing or not song.drum_notes):
        song.clear_track("drum")
        for m in range(total_measures):
            m_start = int(m * measure_ms)
            if _is_silent_at(m_start):
                continue
            is_chorus = (m >= m_chorus1 and m < m_verse2) or (m >= m_chorus2)
            is_solo = (m >= m_solo and m < m_chorus2)
            is_fill_measure = (m % 8 == 7)

            if m % 4 == 0 or is_chorus and m % 2 == 0:
                song.add_note("drum", NoteEvent(time_ms=m_start, lane="green", duration_ms=160, difficulty="Expert"))

            if is_fill_measure:
                song.add_note("drum", NoteEvent(time_ms=int(m_start + 2 * beat_ms), lane="red", duration_ms=120, difficulty="Expert"))
                song.add_note("drum", NoteEvent(time_ms=int(m_start + 2.5 * beat_ms), lane="yellow", duration_ms=120, difficulty="Expert"))
                song.add_note("drum", NoteEvent(time_ms=int(m_start + 3 * beat_ms), lane="blue", duration_ms=120, difficulty="Expert"))
                song.add_note("drum", NoteEvent(time_ms=int(m_start + 3.5 * beat_ms), lane="red", duration_ms=120, difficulty="Expert"))
            else:
                song.add_note("drum", NoteEvent(time_ms=m_start, lane="orange", duration_ms=160, difficulty="Expert"))
                song.add_note("drum", NoteEvent(time_ms=int(m_start + 2 * beat_ms), lane="orange", duration_ms=160, difficulty="Expert"))

                song.add_note("drum", NoteEvent(time_ms=int(m_start + 1 * beat_ms), lane="red", duration_ms=160, difficulty="Expert"))
                song.add_note("drum", NoteEvent(time_ms=int(m_start + 3 * beat_ms), lane="red", duration_ms=160, difficulty="Expert"))

                cymbal_lane = "blue" if is_chorus else "yellow"
                for b8 in range(8):
                    t8 = int(m_start + b8 * eighth_ms)
                    if not _is_silent_at(t8):
                        song.add_note("drum", NoteEvent(time_ms=t8, lane=cymbal_lane, duration_ms=120, difficulty="Expert"))

                if m % 16 == 8:
                    od_note = NoteEvent(time_ms=m_start, lane="overdrive", duration_ms=int(2 * measure_ms), difficulty="Expert", is_overdrive=True)
                    song.add_note("drum", od_note)

    # 4. GERAR BAIXO
    if "bass" in selected_instruments and (clear_existing or not song.bass_notes):
        song.clear_track("bass")
        for m in range(total_measures):
            m_start = int(m * measure_ms)
            if _is_silent_at(m_start):
                continue
            root_idx = chord_progression[m % len(chord_progression)]
            root_lane = lanes_5[root_idx]

            for b in range(4):
                t_beat = int(m_start + b * beat_ms)
                if _is_silent_at(t_beat):
                    continue
                active_lane = root_lane if b < 3 else lanes_5[(root_idx + 1) % len(lanes_5)]
                song.add_note("bass", NoteEvent(time_ms=t_beat, lane=active_lane, duration_ms=int(beat_ms * 0.75), difficulty="Expert"))

    # 5. GERAR GUITARRA (5 CASAS)
    if "guitar" in selected_instruments and (clear_existing or not song.guitar_notes):
        song.clear_track("guitar")
        for m in range(total_measures):
            m_start = int(m * measure_ms)
            if _is_silent_at(m_start):
                continue
            root_idx = chord_progression[m % len(chord_progression)]
            is_chorus = (m >= m_chorus1 and m < m_verse2) or (m >= m_chorus2)
            is_solo = (m >= m_solo and m < m_chorus2)

            if is_solo:
                solo_marker = NoteEvent(time_ms=m_start, lane="solo", duration_ms=int(measure_ms), difficulty="Expert")
                song.add_note("guitar", solo_marker)
                for s in range(8):
                    t_solo = int(m_start + s * eighth_ms)
                    if _is_silent_at(t_solo):
                        continue
                    note_lane = lanes_5[(s * 2 + root_idx) % 5]
                    is_hopo = (s % 2 != 0)
                    dur = int(eighth_ms * 0.9) if s != 7 else int(beat_ms * 1.5)
                    song.add_note("guitar", NoteEvent(time_ms=t_solo, lane=note_lane, duration_ms=dur, difficulty="Expert", is_hopo=is_hopo))
            elif is_chorus:
                lane_1 = lanes_5[root_idx]
                lane_2 = lanes_5[(root_idx + 1) % 5]
                for b in range(4):
                    t_beat = int(m_start + b * beat_ms)
                    if _is_silent_at(t_beat):
                        continue
                    dur = int(beat_ms * 0.8)
                    song.add_note("guitar", NoteEvent(time_ms=t_beat, lane=lane_1, duration_ms=dur, difficulty="Expert"))
                    song.add_note("guitar", NoteEvent(time_ms=t_beat, lane=lane_2, duration_ms=dur, difficulty="Expert"))
            else:
                lane_1 = lanes_5[root_idx]
                for b in [0, 1.5, 2.5, 3]:
                    t_note = int(m_start + b * beat_ms)
                    if _is_silent_at(t_note):
                        continue
                    song.add_note("guitar", NoteEvent(time_ms=t_note, lane=lane_1, duration_ms=int(beat_ms * 0.7), difficulty="Expert"))

            if m % 16 == 4:
                song.add_note("guitar", NoteEvent(time_ms=m_start, lane="overdrive", duration_ms=int(2 * measure_ms), difficulty="Expert", is_overdrive=True))

    # 6. GERAR TECLADO (KEYS)
    if "keys" in selected_instruments and (clear_existing or not song.keys_notes):
        song.clear_track("keys")
        for m in range(total_measures):
            m_start = int(m * measure_ms)
            if _is_silent_at(m_start):
                continue
            root_idx = chord_progression[m % len(chord_progression)]
            k_lane1 = lanes_5[(root_idx + 2) % 5]
            k_lane2 = lanes_5[(root_idx + 4) % 5]
            dur = int(measure_ms * 0.95)
            song.add_note("keys", NoteEvent(time_ms=m_start, lane=k_lane1, duration_ms=dur, difficulty="Expert"))
            song.add_note("keys", NoteEvent(time_ms=m_start, lane=k_lane2, duration_ms=dur, difficulty="Expert"))

    # 7. GERAR VOCAIS (PART VOCALS) - SOMENTE SE HOUVER LETRA/LEGENDA REAL!
    if "vocals" in selected_instruments and has_real_lyrics and (clear_existing or not song.vocal_notes):
        from src.creator.lyric_processor import align_lyrics_to_song
        align_lyrics_to_song(song, song.lyrics_raw, start_delay_ms=max(3000, first_sound_ms + int(measure_ms)))

    # 8. GERAR DIFICULDADES MENORES (Hard, Medium, Easy)
    if generate_all_diffs:
        _generate_lower_difficulties(song, selected_instruments)

    return song


def _generate_lower_difficulties(song: ChartSong, instruments: List[str]):
    """
    Gera as versões Hard, Medium e Easy a partir do Expert conforme os padrões canônicos
    oficiais de Rock Band e Guitar Hero:
    - Hard: Todas as 5 pistas (Verde, Vermelha, Amarela, Azul, Laranja). Mantém acordes duplos.
            Reduz ritmos de 16 avos (solos muito rápidos) para colcheias (8 avos).
    - Medium: 4 pistas principais (Verde, Vermelha, Amarela, Azul). Quase NENHUMA Laranja
              (notas laranjas são transpostas para azul). Apenas acordes simples nos tempos fortes.
    - Easy: 3 pistas principais (Verde, Vermelha, Amarela). Quase NENHUM azul (apenas Verde, Vermelho, Amarelo).
            ESTRITAMENTE NOTAS INDIVIDUAIS (sem nenhum acorde). Ritmo lento e espaçado (mínimo 350ms).
    """
    lanes_order = ["green", "red", "yellow", "blue", "orange"]

    for inst in instruments:
        if inst == "vocals":
            continue

        track_notes = getattr(song, f"{inst}_notes", [])
        # Mantém apenas as notas Expert (e marcadores especiais de solo/overdrive)
        filtered = [n for n in track_notes if n.difficulty == "Expert" or n.lane in ["overdrive", "solo"]]
        setattr(song, f"{inst}_notes", filtered)

        expert_notes = [n for n in filtered if n.difficulty == "Expert" and n.lane not in ["overdrive", "solo"]]
        if not expert_notes:
            continue

        # Agrupa notas por tempo (para preservar acordes do Expert)
        notes_by_time = {}
        for n in expert_notes:
            notes_by_time.setdefault(n.time_ms, []).append(n)

        sorted_times = sorted(notes_by_time.keys())

        # -------------------------------------------------------------
        # 1. HARD (~75% das notas, 5 cores: G, R, Y, B, O, acordes duplos)
        # -------------------------------------------------------------
        last_hard_time = -1000
        for i, t in enumerate(sorted_times):
            simul_notes = notes_by_time[t]
            # No Hard: elimina apenas subdivisões de 16 avos coladas (< 120ms)
            if t - last_hard_time < 120 and (i % 2 != 0):
                continue
            last_hard_time = t

            sorted_simul = sorted(simul_notes, key=lambda x: lanes_order.index(x.lane) if x.lane in lanes_order else 99)
            chosen = sorted_simul[:2] if len(sorted_simul) > 2 else sorted_simul

            for n in chosen:
                song.add_note(inst, NoteEvent(
                    time_ms=n.time_ms,
                    lane=n.lane,
                    duration_ms=n.duration_ms,
                    difficulty="Hard",
                    is_hopo=n.is_hopo
                ))

        # -------------------------------------------------------------
        # 2. MEDIUM (~45% das notas, 4 cores: G, R, Y, B. Sem Laranja!)
        # -------------------------------------------------------------
        last_med_time = -1000
        for i, t in enumerate(sorted_times):
            if t - last_med_time < 180 or (i % 2 != 0 and (t - last_med_time < 280)):
                continue
            last_med_time = t

            simul_notes = notes_by_time[t]
            first_note = simul_notes[0]
            # Transpõe laranja para azul no Medium
            m_lane = "blue" if first_note.lane == "orange" else first_note.lane
            song.add_note(inst, NoteEvent(
                time_ms=first_note.time_ms,
                lane=m_lane,
                duration_ms=first_note.duration_ms,
                difficulty="Medium"
            ))

            # Acorde duplo simples apenas em tempos fortes
            if len(simul_notes) > 1 and i % 4 == 0:
                sec_lane = "blue" if simul_notes[1].lane == "orange" else simul_notes[1].lane
                if sec_lane != m_lane:
                    song.add_note(inst, NoteEvent(
                        time_ms=simul_notes[1].time_ms,
                        lane=sec_lane,
                        duration_ms=simul_notes[1].duration_ms,
                        difficulty="Medium"
                    ))

        # -------------------------------------------------------------
        # 3. EASY (~20% das notas, 3 cores: G, R, Y. NUNCA ACORDES!)
        # -------------------------------------------------------------
        last_easy_time = -1000
        for i, t in enumerate(sorted_times):
            if t - last_easy_time < 380:
                continue
            if i % 3 != 0:
                continue
            last_easy_time = t

            simul_notes = notes_by_time[t]
            primary_note = simul_notes[0]

            # No Easy: apenas Verde, Vermelho e Amarelo! Quase nenhum azul, zero laranja!
            if primary_note.lane == "orange":
                easy_lane = "yellow"
            elif primary_note.lane == "blue":
                easy_lane = "yellow" if i % 2 == 0 else "red"
            else:
                easy_lane = primary_note.lane

            song.add_note(inst, NoteEvent(
                time_ms=primary_note.time_ms,
                lane=easy_lane,
                duration_ms=max(260, primary_note.duration_ms),
                difficulty="Easy"
            ))


def recalculate_track_difficulties(song: ChartSong, instruments: List[str] = None):
    """
    Recalcula as dificuldades Hard, Medium e Easy para os instrumentos selecionados
    mantendo intactas as notas do Expert.
    """
    if instruments is None:
        instruments = ["guitar", "bass", "drum", "keys"]
    _generate_lower_difficulties(song, instruments)


def generate_missing_instruments_only(
    song: ChartSong,
    instruments: List[str] = None,
    intensity: str = "Rock",
    generate_all_diffs: bool = True
) -> List[str]:
    """
    Gera APENAS os instrumentos que estão vazios (sem notas), preservando 100%
    das trilhas já criadas por fãs ou pelo usuário.
    Retorna a lista dos instrumentos que foram gerados.
    """
    if instruments is None:
        instruments = ["guitar", "bass", "drum", "keys", "vocals"]

    missing = []
    has_real_lyrics = bool(song.lyrics_raw and song.lyrics_raw.strip())
    for inst in instruments:
        if inst == "vocals":
            if not song.vocal_notes and has_real_lyrics:
                missing.append("vocals")
        else:
            if not getattr(song, f"{inst}_notes", []):
                missing.append(inst)

    if missing:
        auto_generate_chart(
            song,
            selected_instruments=missing,
            intensity=intensity,
            generate_all_diffs=generate_all_diffs,
            clear_existing=False
        )

    # Para qualquer trilha existente que só tenha Expert, recalcula Hard/Medium/Easy
    if generate_all_diffs:
        for inst in ["guitar", "bass", "drum", "keys"]:
            notes = getattr(song, f"{inst}_notes", [])
            has_lower = any(n.difficulty in ["Hard", "Medium", "Easy"] for n in notes)
            if notes and not has_lower:
                _generate_lower_difficulties(song, [inst])

    return missing

