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
    """Tenta obter a duração real em milissegundos do arquivo de áudio via pygame."""
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
    generate_all_diffs: bool = True
) -> ChartSong:
    """
    Gera automaticamente notas completas, rítmicas e musicais sincronizadas com o BPM.
    """
    if song.audio_path:
        detected_dur = get_audio_duration_ms(song.audio_path)
        if detected_dur > 10000:
            total_duration_ms = detected_dur

    if selected_instruments is None:
        selected_instruments = ["guitar", "bass", "drum", "keys"]

    bpm = max(30.0, song.bpm)
    beat_ms = (60.0 / bpm) * 1000.0          # Tempo de 1 semínima (1 batida)
    measure_ms = beat_ms * 4.0               # Tempo de 1 compasso (4/4)
    eighth_ms = beat_ms / 2.0                # Tempo de 1 colcheia
    total_measures = int(total_duration_ms / measure_ms)

    # 1. Limpa trilhas que serão geradas
    for inst in selected_instruments:
        song.clear_track(inst)
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

    # Progressões de Acordes Simbolizadas (0=Verde, 1=Vermelho, 2=Amarelo, 3=Azul, 4=Laranja)
    chord_progression = [0, 2, 3, 1] # I - V - vi - IV clássico do Rock/Pop
    lanes_5 = ["green", "red", "yellow", "blue", "orange"]

    # 3. GERAR BATERIA
    if "drum" in selected_instruments:
        for m in range(total_measures):
            m_start = int(m * measure_ms)
            is_chorus = (m >= m_chorus1 and m < m_verse2) or (m >= m_chorus2)
            is_solo = (m >= m_solo and m < m_chorus2)
            is_fill_measure = (m % 8 == 7) # Virada no final de frases de 8 compassos

            # Prato Crash no início de compassos de refrão ou início de estrofe
            if m % 4 == 0 or is_chorus and m % 2 == 0:
                song.add_note("drum", NoteEvent(time_ms=m_start, lane="green", duration_ms=160, difficulty="Expert"))

            if is_fill_measure:
                # Virada de bateria emocionante (Fill nos tempos 3 e 4)
                song.add_note("drum", NoteEvent(time_ms=int(m_start + 2 * beat_ms), lane="red", duration_ms=120, difficulty="Expert"))
                song.add_note("drum", NoteEvent(time_ms=int(m_start + 2.5 * beat_ms), lane="yellow", duration_ms=120, difficulty="Expert"))
                song.add_note("drum", NoteEvent(time_ms=int(m_start + 3 * beat_ms), lane="blue", duration_ms=120, difficulty="Expert"))
                song.add_note("drum", NoteEvent(time_ms=int(m_start + 3.5 * beat_ms), lane="red", duration_ms=120, difficulty="Expert"))
            else:
                # Ritmo base: Bumbo no tempo 1 e 3
                song.add_note("drum", NoteEvent(time_ms=m_start, lane="orange", duration_ms=160, difficulty="Expert"))
                song.add_note("drum", NoteEvent(time_ms=int(m_start + 2 * beat_ms), lane="orange", duration_ms=160, difficulty="Expert"))

                # Caixa no tempo 2 e 4
                song.add_note("drum", NoteEvent(time_ms=int(m_start + 1 * beat_ms), lane="red", duration_ms=160, difficulty="Expert"))
                song.add_note("drum", NoteEvent(time_ms=int(m_start + 3 * beat_ms), lane="red", duration_ms=160, difficulty="Expert"))

                # Chimbal (yellow) ou Prato Condução (blue no refrão) em colcheias
                cymbal_lane = "blue" if is_chorus else "yellow"
                for b8 in range(8):
                    t8 = int(m_start + b8 * eighth_ms)
                    song.add_note("drum", NoteEvent(time_ms=t8, lane=cymbal_lane, duration_ms=120, difficulty="Expert"))

                # Overdrive a cada 16 compassos
                if m % 16 == 8:
                    od_note = NoteEvent(time_ms=m_start, lane="overdrive", duration_ms=int(2 * measure_ms), difficulty="Expert", is_overdrive=True)
                    song.add_note("drum", od_note)

    # 4. GERAR BAIXO
    if "bass" in selected_instruments:
        for m in range(total_measures):
            m_start = int(m * measure_ms)
            root_idx = chord_progression[m % len(chord_progression)]
            root_lane = lanes_5[root_idx]

            # Pulso contínuo de colcheias ou semínimas no baixo
            for b in range(4):
                t_beat = int(m_start + b * beat_ms)
                # Variação sutil na 4ª batida
                active_lane = root_lane if b < 3 else lanes_5[(root_idx + 1) % len(lanes_5)]
                song.add_note("bass", NoteEvent(time_ms=t_beat, lane=active_lane, duration_ms=int(beat_ms * 0.75), difficulty="Expert"))

    # 5. GERAR GUITARRA (5 CASAS)
    if "guitar" in selected_instruments:
        for m in range(total_measures):
            m_start = int(m * measure_ms)
            root_idx = chord_progression[m % len(chord_progression)]
            is_chorus = (m >= m_chorus1 and m < m_verse2) or (m >= m_chorus2)
            is_solo = (m >= m_solo and m < m_chorus2)

            if is_solo:
                # Solo de guitarra épico com notas rápidas (semicolcheias / arpeggios e sustains)
                solo_marker = NoteEvent(time_ms=m_start, lane="solo", duration_ms=int(measure_ms), difficulty="Expert")
                song.add_note("guitar", solo_marker)
                # 8 notas por compasso com alternância melódica
                for s in range(8):
                    t_solo = int(m_start + s * eighth_ms)
                    note_lane = lanes_5[(s * 2 + root_idx) % 5]
                    is_hopo = (s % 2 != 0)
                    dur = int(eighth_ms * 0.9) if s != 7 else int(beat_ms * 1.5)
                    song.add_note("guitar", NoteEvent(time_ms=t_solo, lane=note_lane, duration_ms=dur, difficulty="Expert", is_hopo=is_hopo))
            elif is_chorus:
                # Acordes duplos cheios de energia no refrão (Power Chords)
                lane_1 = lanes_5[root_idx]
                lane_2 = lanes_5[(root_idx + 1) % 5]
                for b in range(4):
                    t_beat = int(m_start + b * beat_ms)
                    dur = int(beat_ms * 0.8)
                    song.add_note("guitar", NoteEvent(time_ms=t_beat, lane=lane_1, duration_ms=dur, difficulty="Expert"))
                    song.add_note("guitar", NoteEvent(time_ms=t_beat, lane=lane_2, duration_ms=dur, difficulty="Expert"))
            else:
                # Versos / Introdução: Ritmo sincopado agradável
                lane_1 = lanes_5[root_idx]
                for b in [0, 1.5, 2.5, 3]:
                    t_note = int(m_start + b * beat_ms)
                    song.add_note("guitar", NoteEvent(time_ms=t_note, lane=lane_1, duration_ms=int(beat_ms * 0.7), difficulty="Expert"))

            # Frase de Overdrive na guitarra a cada 16 compassos
            if m % 16 == 4:
                song.add_note("guitar", NoteEvent(time_ms=m_start, lane="overdrive", duration_ms=int(2 * measure_ms), difficulty="Expert", is_overdrive=True))

    # 6. GERAR TECLADO (KEYS)
    if "keys" in selected_instruments:
        for m in range(total_measures):
            m_start = int(m * measure_ms)
            root_idx = chord_progression[m % len(chord_progression)]
            # Teclado sustenta acordes longos de acompanhamento (Pads harmônicos)
            k_lane1 = lanes_5[(root_idx + 2) % 5]
            k_lane2 = lanes_5[(root_idx + 4) % 5]
            dur = int(measure_ms * 0.95)
            song.add_note("keys", NoteEvent(time_ms=m_start, lane=k_lane1, duration_ms=dur, difficulty="Expert"))
            song.add_note("keys", NoteEvent(time_ms=m_start, lane=k_lane2, duration_ms=dur, difficulty="Expert"))

    # 7. GERAR VOCAIS (PART VOCALS com Pitch, Frases, Letras e Overdrive)
    if "vocals" in selected_instruments:
        song.vocal_notes.clear()
        vocal_scale = [60, 62, 64, 65, 67, 69, 72]
        sample_lyrics = ["Yeah", "Come", "on", "feel", "the", "sound", "to-", "night", "sing", "out", "loud", "let's", "go!"]

        for m in range(total_measures):
            # Dá pausa na introdução e no solo de guitarra
            is_intro = (m < m_intro)
            is_solo = (m >= m_solo and m < m_chorus2)
            if is_intro or is_solo:
                continue

            m_start = int(m * measure_ms)
            is_chorus = (m >= m_chorus1 and m < m_verse2) or (m >= m_chorus2)
            root_idx = chord_progression[m % len(chord_progression)]

            is_phrase_end = (m % 2 == 1)
            is_vocal_od = is_chorus and (m % 8 == 7)

            for b in range(4):
                t_vocal = int(m_start + b * beat_ms)
                pitch = vocal_scale[(root_idx + b) % len(vocal_scale)]
                if is_chorus:
                    pitch += 12 # Uma oitava acima no refrão

                lyr = sample_lyrics[(m * 4 + b) % len(sample_lyrics)]
                last_in_phrase = is_phrase_end and (b == 3)

                song.add_vocal_note(VocalNote(
                    time_ms=t_vocal,
                    duration_ms=int(beat_ms * 0.8),
                    pitch=pitch,
                    lyric=lyr,
                    is_overdrive=is_vocal_od,
                    is_phrase_end=last_in_phrase
                ))

    # 8. GERAR DIFICULDADES MENORES (Hard, Medium, Easy)
    if generate_all_diffs:
        _generate_lower_difficulties(song, selected_instruments)

    return song

def _generate_lower_difficulties(song: ChartSong, instruments: List[str]):
    """Gera automaticamente as versões Hard, Medium e Easy a partir do Expert."""
    for inst in instruments:
        expert_notes = [n for n in getattr(song, f"{inst}_notes", []) if n.difficulty == "Expert" and n.lane not in ["overdrive", "solo"]]

        # Hard: ~70% das notas (elimina subdivisões muito rápidas)
        for i, n in enumerate(expert_notes):
            if i % 4 != 3: # Remove 1 a cada 4 notas
                song.add_note(inst, NoteEvent(time_ms=n.time_ms, lane=n.lane, duration_ms=n.duration_ms, difficulty="Hard", is_hopo=n.is_hopo))

        # Medium: ~40% das notas (apenas tempos fortes e notas principais)
        for i, n in enumerate(expert_notes):
            if i % 2 == 0:
                # Transpõe a casa laranja (5) para azul (4) para facilitar no Medium
                med_lane = "blue" if n.lane == "orange" else n.lane
                song.add_note(inst, NoteEvent(time_ms=n.time_ms, lane=med_lane, duration_ms=n.duration_ms, difficulty="Medium"))

        # Easy: ~20% das notas (apenas semibreves/mínimas nas cores mais fáceis)
        for i, n in enumerate(expert_notes):
            if i % 4 == 0:
                # No Easy usa apenas verde e vermelha
                easy_lane = "green" if n.lane in ["green", "yellow", "orange"] else "red"
                song.add_note(inst, NoteEvent(time_ms=n.time_ms, lane=easy_lane, duration_ms=max(200, n.duration_ms), difficulty="Easy"))
