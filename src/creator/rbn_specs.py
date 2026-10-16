"""
Especificações Oficiais do Rock Band Network (RBN) e C3 Universe para MIDI.
Mapeamento de notas para Guitarra (5 botões), Baixo, Bateria, Teclado,
Pro Keys, Pro Guitar (6 cordas), Pista de Compasso (BEAT) e Eventos (EVENTS).
"""

# -------------------------------------------------------------------------
# CONSTANTES DE TEMPO
# -------------------------------------------------------------------------
TICKS_PER_BEAT = 480     # Padrão Harmonix Rock Band Network / C3

# -------------------------------------------------------------------------
# PISTA DE COMPASSO (BEAT)
# -------------------------------------------------------------------------
BEAT_BAR_DOWNBEAT = 12   # Primeiro tempo do compasso (forte)
BEAT_OFFBEAT = 13        # Demais tempos do compasso (fraco)

# -------------------------------------------------------------------------
# PISTA DE EVENTOS (EVENTS)
# Exemplos de textos: [music_start], [section intro], [section verse1],
# [section chorus1], [section solo], [music_end], [end]
# -------------------------------------------------------------------------

# -------------------------------------------------------------------------
# GUITARRA & BAIXO TRADICIONAIS (5 BOTÕES) - PART GUITAR / PART BASS
# -------------------------------------------------------------------------
FRET_NOTES = {
    "Expert": {
        "green": 96,
        "red": 97,
        "yellow": 98,
        "blue": 99,
        "orange": 100,
        "force_hopo": 101,
        "force_strum": 102,
    },
    "Hard": {
        "green": 84,
        "red": 85,
        "yellow": 86,
        "blue": 87,
        "orange": 88,
        "force_hopo": 89,
        "force_strum": 90,
    },
    "Medium": {
        "green": 72,
        "red": 73,
        "yellow": 74,
        "blue": 75,
        "orange": 76,
        "force_hopo": 77,
        "force_strum": 78,
    },
    "Easy": {
        "green": 60,
        "red": 61,
        "yellow": 62,
        "blue": 63,
        "orange": 64,
        "force_hopo": 65,
        "force_strum": 66,
    }
}

GUITAR_SOLO_MARKER = 103     # Marcador de Solo de Guitarra
GUITAR_OVERDRIVE = 116       # Frase de Overdrive / Star Power

# -------------------------------------------------------------------------
# BATERIA (PART DRUMS)
# -------------------------------------------------------------------------
DRUM_NOTES = {
    "Expert": {
        "kick": 96,          # Bumbo (Pedal Laranja)
        "snare": 97,         # Caixa (Pad Vermelho)
        "yellow": 98,        # Chimbal / Tom Amarelo
        "blue": 99,          # Tom / Condução Azul
        "green": 100,        # Surdo / Prato Verde
        "double_kick": 95,   # Pedal duplo (2x Bass Drum)
    },
    "Hard": {
        "kick": 84,
        "snare": 85,
        "yellow": 86,
        "blue": 87,
        "green": 88,
    },
    "Medium": {
        "kick": 72,
        "snare": 73,
        "yellow": 74,
        "blue": 75,
        "green": 76,
    },
    "Easy": {
        "kick": 60,
        "snare": 61,
        "yellow": 62,
        "blue": 63,
        "green": 64,
    }
}

# Marcadores Pro Drums (Pratos vs Tons)
DRUM_CYMBAL_MARKERS = {
    "yellow_cymbal": 110,   # Marca o tom amarelo como Prato Chimbal
    "blue_cymbal": 111,     # Marca o tom azul como Prato Condução/Ride
    "green_cymbal": 112,    # Marca o tom verde como Prato Ataque/Crash
}

DRUM_SOLO_MARKER = 103
DRUM_OVERDRIVE = 116
DRUM_FILLS = [120, 121, 122, 123, 124] # Ativação de Roll / Fill para ativar Overdrive

# -------------------------------------------------------------------------
# TECLADO TRADICIONAL & PRO KEYS (PART KEYS / PART REAL_KEYS_X)
# -------------------------------------------------------------------------
KEYS_5LANE = FRET_NOTES     # Teclado 5 botões usa as mesmas notas da guitarra
KEYS_OVERDRIVE = 116
KEYS_SOLO_MARKER = 103

# Pro Keys (25 teclas reais): C3 (48) até C5 (72)
PRO_KEYS_MIN_NOTE = 48
PRO_KEYS_MAX_NOTE = 72

# -------------------------------------------------------------------------
# GUITARRA PRO / BAIXO PRO (PART REAL_GUITAR / PART REAL_BASS)
# -------------------------------------------------------------------------
# 6 cordas: Corda 6 Mi grave (string_idx=0) até Corda 1 Mi agudo (string_idx=5)
# No MIDI RBN2: pitch = base_diff + string_idx, velocity = 100 + fret (0 a 17)
PRO_GUITAR_STRING_BASE = {
    "Expert": 96,
    "Hard": 72,
    "Medium": 48,
    "Easy": 24,
}
PRO_GUITAR_OVERDRIVE = 116
PRO_GUITAR_SOLO = 103

# -------------------------------------------------------------------------
# VOCAIS & HARMONIAS (PART VOCALS / HARM1 / HARM2 / HARM3)
# Mecânicas especiais da Harmonix: Altura tonal (Pitch), Letras (Lyrics),
# Frases de Pontuação (Note 105), Overdrive (Note 106) e Pandeiro (Note 116).
# -------------------------------------------------------------------------
VOCAL_PITCH_MIN = 36          # C2 (Dó 2)
VOCAL_PITCH_MAX = 84          # C6 (Dó 6)
VOCAL_PHRASE_MARKER = 105     # Marca o início e fim da frase vocal para rolagem e pontuação
VOCAL_OVERDRIVE = 106         # Frase de Overdrive (Energia) dos vocais
VOCAL_PERCUSSION = 116        # Batida no microfone / Pandeiro durante partes instrumentais
VOCAL_TALKIE = 96             # Nota falada / rap (sem altura tonal obrigatória)
