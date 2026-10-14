"""
Definições dos tipos de instrumentos MIDI do ecossistema Rock Band / Guitar Hero / Band Hero.
"""

from enum import Enum

class InstrumentMode(Enum):
    AUTO = "auto"                     # Detecção automática baseada no tráfego MIDI
    PRO_GUITAR = "pro_guitar"         # Squier Stratocaster / Mustang Pro Guitar (6 cordas, canais 1 a 6)
    CLASSIC_GUITAR = "classic_guitar" # Guitarra 5 botões (Rock Band / Guitar Hero via MIDI Pro Adapter)
    KEYBOARD = "keyboard"             # Rock Band 3 Wireless Keyboard (25 teclas, fita touch ribbon)
    DRUMS = "drums"                   # Band Hero / Guitar Hero / Rock Band Pro Drums (Canal 10)

# Mapeamento padrão de notas de bateria General MIDI (Canal 10)
DRUM_MAP = {
    35: ("Acoustic Bass Drum", "kick", "#9333EA"),
    36: ("Bass Drum 1 (Pedal)", "kick", "#9333EA"),
    38: ("Acoustic Snare (Vermelho)", "snare", "#EF4444"),
    40: ("Electric Snare", "snare", "#EF4444"),
    42: ("Closed Hi-Hat (Amarelo)", "hihat", "#FACC15"),
    46: ("Open Hi-Hat (Amarelo)", "hihat", "#FACC15"),
    44: ("Pedal Hi-Hat", "hihat", "#FACC15"),
    48: ("Hi-Mid Tom (Amarelo/Azul)", "tom1", "#3B82F6"),
    45: ("Low Tom (Azul)", "tom2", "#3B82F6"),
    47: ("Low-Mid Tom", "tom2", "#3B82F6"),
    41: ("Low Floor Tom (Verde)", "tom3", "#22C55E"),
    43: ("High Floor Tom (Verde)", "tom3", "#22C55E"),
    49: ("Crash Cymbal 1 (Verde/Laranja)", "crash", "#FB923C"),
    51: ("Ride Cymbal 1 (Azul)", "ride", "#38BDF8"),
    53: ("Ride Bell", "ride", "#38BDF8"),
    55: ("Splash Cymbal (Laranja)", "crash", "#FB923C"),
}

# Afinação padrão das 6 cordas da Guitarra Pro (Canais 1 a 6)
PRO_GUITAR_STRINGS = {
    6: {"name": "6ª Corda (Mi Grave / Low E)", "open_note": 40, "base_name": "E2"},
    5: {"name": "5ª Corda (Lá / A)", "open_note": 45, "base_name": "A2"},
    4: {"name": "4ª Corda (Ré / D)", "open_note": 50, "base_name": "D3"},
    3: {"name": "3ª Corda (Sol / G)", "open_note": 55, "base_name": "G3"},
    2: {"name": "2ª Corda (Si / B)", "open_note": 59, "base_name": "B3"},
    1: {"name": "1ª Corda (Mi Agudo / High E)", "open_note": 64, "base_name": "E4"},
}
