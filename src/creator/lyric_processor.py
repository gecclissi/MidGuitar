"""
Processador e Sincronizador Inteligente de Letras Vocais para Rock Band e Clone Hero.
Permite importar letras de arquivos .txt ou .lrc (com timestamps), dividir palavras em sílabas
no padrão oficial RBN (com hífens terminadores 'syl-') e sincronizar perfeitamente com a trilha vocal.
"""

import re
from typing import List, Tuple, Optional
from src.creator.chart_model import ChartSong, VocalNote

def parse_lrc_content(lrc_text: str) -> List[Tuple[int, str]]:
    """
    Analisa texto no formato LRC com tags de tempo [mm:ss.xx] ou [mm:ss:xxx].
    Retorna lista ordenada de tuplas (tempo_ms, linha_de_letra).
    """
    entries = []
    # Padrão para pegar timestamps como [01:23.45] ou [01:23:450]
    pattern = re.compile(r'\[(\d{1,2}):(\d{2})(?:[.:](\d{2,3}))?\](.*)')

    for line in lrc_text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = pattern.match(line)
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            millis_str = match.group(3) or "0"
            if len(millis_str) == 2:
                millis = int(millis_str) * 10
            else:
                millis = int(millis_str[:3])
            
            time_ms = (minutes * 60 + seconds) * 1000 + millis
            text = match.group(4).strip()
            # Remove tags de metadados como [ar:artista]
            if text and not re.match(r'^(ti|ar|al|by|offset):', text, re.IGNORECASE):
                entries.append((time_ms, text))

    entries.sort(key=lambda x: x[0])
    return entries

def syllabify_word(word: str) -> List[str]:
    """
    Divide uma palavra em sílabas aplicando regras fonéticas de Português e Inglês,
    e formata no padrão Rock Band Network:
    - Sílabas intermediárias terminam com hífen '-' (ex: 'can-', 'tar')
    - A última sílaba não tem hífen.
    """
    clean_word = word.strip()
    if not clean_word:
        return []
    
    # Se a palavra for muito curta (1 ou 2 letras), não divide
    if len(clean_word) <= 3:
        return [clean_word]

    # Regex heurística de divisão silábica para línguas latinas / inglês
    # Identifica núcleos vocálicos e quebras consonantais
    vowels = "aeiouáéíóúâêîôûãõàyAEIOUÁÉÍÓÚÂÊÎÔÛÃÕÀY"
    
    # Regra simples mas muito eficaz: divide após encontros vogal-consoante-vogal
    syllables = []
    current_syl = ""
    
    i = 0
    w_len = len(clean_word)
    while i < w_len:
        current_syl += clean_word[i]
        
        # Se achou uma vogal
        if clean_word[i] in vowels:
            # Olha para frente
            if i + 2 < w_len:
                next_c = clean_word[i+1]
                next_next = clean_word[i+2]
                
                # Vogal + Consoante + Vogal -> Quebra antes da consoante (ex: ca-sa, to-mar)
                if next_c not in vowels and next_next in vowels:
                    syllables.append(current_syl)
                    current_syl = ""
                # Vogal + Consoante + Consoante + Vogal (ex: can-tar, por-ta)
                elif next_c not in vowels and next_next not in vowels and (i + 3 < w_len and clean_word[i+3] in vowels):
                    # Não quebra dígrafos como ch, lh, nh, tr, br, cl
                    digraphs = ["ch", "lh", "nh", "qu", "gu", "tr", "br", "cl", "cr", "pl", "pr", "fl", "fr", "gr", "dr"]
                    pair = (next_c + next_next).lower()
                    if pair not in digraphs:
                        current_syl += next_c
                        syllables.append(current_syl)
                        current_syl = ""
                        i += 1
        i += 1

    if current_syl:
        syllables.append(current_syl)

    if not syllables:
        return [clean_word]

    # Formata no padrão Rock Band: sílabas anteriores terminam com '-'
    formatted = []
    for idx, s in enumerate(syllables):
        if idx < len(syllables) - 1:
            formatted.append(s + "-")
        else:
            formatted.append(s)

    return formatted

def syllabify_text_lines(text: str) -> List[List[str]]:
    """
    Divide um texto com vários versos em linhas de sílabas.
    Cada linha representa uma frase lírica.
    """
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        words = line.split()
        line_syllables = []
        for w in words:
            line_syllables.extend(syllabify_word(w))
        if line_syllables:
            lines.append(line_syllables)
    return lines

def align_lyrics_to_song(
    song: ChartSong,
    lyrics_text: str,
    start_delay_ms: int = 4000,
    measures_per_phrase: int = 2
) -> int:
    """
    Sincroniza a letra com a música.
    1. Se for LRC com timestamps, usa os tempos marcados para cada frase!
    2. Se for texto simples:
       - Se já houver notas vocais na música, aloca as sílabas ordenadamente nelas.
       - Se não houver notas, cria automaticamente notas vocais melódicas distribuídas
         no ritmo do BPM e compassos da canção.
    Retorna o número de sílabas/notas vocais aplicadas.
    """
    song.lyrics_raw = lyrics_text
    lrc_entries = parse_lrc_content(lyrics_text)

    # Caso A: Letra com timestamps LRC
    if lrc_entries:
        song.vocal_notes.clear()
        vocal_pitches = [60, 62, 64, 65, 67, 69, 72]
        p_idx = 0

        for line_idx, (t_start, line_text) in enumerate(lrc_entries):
            words = line_text.split()
            syls = []
            for w in words:
                syls.extend(syllabify_word(w))

            if not syls:
                continue

            # Calcula tempo disponível até a próxima frase (ou 3.5 segundos padrão)
            if line_idx + 1 < len(lrc_entries):
                dur_total = min(4000, lrc_entries[line_idx + 1][0] - t_start - 200)
            else:
                dur_total = 3500

            step_ms = max(200, int(dur_total / len(syls)))
            note_dur = int(step_ms * 0.8)

            for s_idx, s in enumerate(syls):
                cur_time = t_start + s_idx * step_ms
                pitch = vocal_pitches[p_idx % len(vocal_pitches)]
                p_idx += 1
                is_phrase_end = (s_idx == len(syls) - 1)
                is_od = (line_idx % 4 == 3) and is_phrase_end

                song.add_vocal_note(VocalNote(
                    time_ms=cur_time,
                    duration_ms=note_dur,
                    pitch=pitch,
                    lyric=s,
                    is_overdrive=is_od,
                    is_phrase_end=is_phrase_end
                ))

        return len(song.vocal_notes)

    # Caso B: Texto simples
    phrase_lines = syllabify_text_lines(lyrics_text)
    if not phrase_lines:
        return 0

    all_syls = []
    phrase_end_indices = set()
    cum_count = 0
    for pline in phrase_lines:
        all_syls.extend(pline)
        cum_count += len(pline)
        phrase_end_indices.add(cum_count - 1)

    # B.1: Já existem notas vocais na música (ex: gravadas ao vivo no teclado ou geradas)
    if song.vocal_notes:
        total_applied = min(len(all_syls), len(song.vocal_notes))
        for i in range(total_applied):
            song.vocal_notes[i].lyric = all_syls[i]
            if i in phrase_end_indices:
                song.vocal_notes[i].is_phrase_end = True
        return total_applied

    # B.2: Não há notas vocais ainda -> Gera automaticamente no tempo do BPM
    song.vocal_notes.clear()
    bpm = max(40.0, song.bpm)
    beat_ms = (60.0 / bpm) * 1000.0
    measure_ms = beat_ms * 4.0

    cur_time = start_delay_ms
    vocal_pitches = [60, 62, 64, 65, 67, 69, 72]
    syl_idx = 0

    for pline in phrase_lines:
        phrase_notes_count = len(pline)
        # Distribui cada sílaba em tempos fortes de semínima ou colcheia
        for p_i, syl in enumerate(pline):
            pitch = vocal_pitches[(syl_idx + p_i) % len(vocal_pitches)]
            is_end = (p_i == phrase_notes_count - 1)
            is_od = (syl_idx % 16 >= 14) and is_end

            song.add_vocal_note(VocalNote(
                time_ms=int(cur_time),
                duration_ms=int(beat_ms * 0.8),
                pitch=pitch,
                lyric=syl,
                is_overdrive=is_od,
                is_phrase_end=is_end
            ))
            # Avança 1 beat ou meio beat por sílaba
            cur_time += beat_ms

        # Pausa para respirar entre frases (1 compasso)
        cur_time += measure_ms
        syl_idx += phrase_notes_count

    return len(song.vocal_notes)
