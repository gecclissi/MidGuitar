"""
Lista de instrumentos padrão General MIDI (GM1) divididos por categoria,
sons de bateria GM (Canal 10) e utilitários de notas e acordes.
"""

GM_INSTRUMENTS = [
    # Piano (0-7)
    (0, "Acoustic Grand Piano", "Piano"),
    (1, "Bright Acoustic Piano", "Piano"),
    (2, "Electric Grand Piano", "Piano"),
    (3, "Honky-tonk Piano", "Piano"),
    (4, "Electric Piano 1 (Rhodes)", "Piano"),
    (5, "Electric Piano 2 (Chorused)", "Piano"),
    (6, "Harpsichord", "Piano"),
    (7, "Clavinet", "Piano"),
    # Chromatic Percussion (8-15)
    (8, "Celesta", "Chromatic"),
    (9, "Glockenspiel", "Chromatic"),
    (10, "Music Box", "Chromatic"),
    (11, "Vibraphone", "Chromatic"),
    (12, "Marimba", "Chromatic"),
    (13, "Xylophone", "Chromatic"),
    (14, "Tubular Bells", "Chromatic"),
    (15, "Dulcimer", "Chromatic"),
    # Organ (16-23)
    (16, "Drawbar Organ", "Organ"),
    (17, "Percussive Organ", "Organ"),
    (18, "Rock Organ", "Organ"),
    (19, "Church Organ", "Organ"),
    (20, "Reed Organ", "Organ"),
    (21, "Accordion", "Organ"),
    (22, "Harmonica", "Organ"),
    (23, "Tango Accordion", "Organ"),
    # Guitar (24-31) - Prioritários para este app!
    (24, "Acoustic Guitar (nylon)", "Guitar"),
    (25, "Acoustic Guitar (steel)", "Guitar"),
    (26, "Electric Guitar (jazz)", "Guitar"),
    (27, "Electric Guitar (clean)", "Guitar"),
    (28, "Electric Guitar (muted)", "Guitar"),
    (29, "Overdriven Guitar", "Guitar"),
    (30, "Distortion Guitar", "Guitar"),
    (31, "Guitar Harmonics", "Guitar"),
    # Bass (32-39)
    (32, "Acoustic Bass", "Bass"),
    (33, "Electric Bass (finger)", "Bass"),
    (34, "Electric Bass (pick)", "Bass"),
    (35, "Fretless Bass", "Bass"),
    (36, "Slap Bass 1", "Bass"),
    (37, "Slap Bass 2", "Bass"),
    (38, "Synth Bass 1", "Bass"),
    (39, "Synth Bass 2", "Bass"),
    # Strings (40-47)
    (40, "Violin", "Strings"),
    (41, "Viola", "Strings"),
    (42, "Cello", "Strings"),
    (43, "Contrabass", "Strings"),
    (44, "Tremolo Strings", "Strings"),
    (45, "Pizzicato Strings", "Strings"),
    (46, "Orchestral Harp", "Strings"),
    (47, "Timpani", "Strings"),
    # Ensemble (48-55)
    (48, "String Ensemble 1", "Ensemble"),
    (49, "String Ensemble 2", "Ensemble"),
    (50, "SynthStrings 1", "Ensemble"),
    (51, "SynthStrings 2", "Ensemble"),
    (52, "Choir Aahs", "Ensemble"),
    (53, "Voice Oohs", "Ensemble"),
    (54, "Synth Voice", "Ensemble"),
    (55, "Orchestra Hit", "Ensemble"),
    # Brass (56-63)
    (56, "Trumpet", "Brass"),
    (57, "Trombone", "Brass"),
    (58, "Tuba", "Brass"),
    (59, "Muted Trumpet", "Brass"),
    (60, "French Horn", "Brass"),
    (61, "Brass Section", "Brass"),
    (62, "SynthBrass 1", "Brass"),
    (63, "SynthBrass 2", "Brass"),
    # Reed (64-71)
    (64, "Soprano Sax", "Reed"),
    (65, "Alto Sax", "Reed"),
    (66, "Tenor Sax", "Reed"),
    (67, "Baritone Sax", "Reed"),
    (68, "Oboe", "Reed"),
    (69, "English Horn", "Reed"),
    (70, "Bassoon", "Reed"),
    (71, "Clarinet", "Reed"),
    # Pipe (72-79)
    (72, "Piccolo", "Pipe"),
    (73, "Flute", "Pipe"),
    (74, "Recorder", "Pipe"),
    (75, "Pan Flute", "Pipe"),
    (76, "Blown Bottle", "Pipe"),
    (77, "Shakuhachi", "Pipe"),
    (78, "Whistle", "Pipe"),
    (79, "Ocarina", "Pipe"),
    # Synth Lead (80-87)
    (80, "Lead 1 (square)", "Synth Lead"),
    (81, "Lead 2 (sawtooth)", "Synth Lead"),
    (82, "Lead 3 (calliope)", "Synth Lead"),
    (83, "Lead 4 (chiff)", "Synth Lead"),
    (84, "Lead 5 (charang)", "Synth Lead"),
    (85, "Lead 6 (voice)", "Synth Lead"),
    (86, "Lead 7 (fifths)", "Synth Lead"),
    (87, "Lead 8 (bass + lead)", "Synth Lead"),
    # Synth Pad (88-95) - Sons Espaciais e Atmosféricos
    (88, "Pad 1 (new age)", "Synth Pad"),
    (89, "Pad 2 (warm)", "Synth Pad"),
    (90, "Pad 3 (polysynth)", "Synth Pad"),
    (91, "Pad 4 (choir)", "Synth Pad"),
    (92, "Pad 5 (bowed)", "Synth Pad"),
    (93, "Pad 6 (metallic)", "Synth Pad"),
    (94, "Pad 7 (halo)", "Synth Pad"),
    (95, "Pad 8 (sweep)", "Synth Pad"),
    # Synth Effects (96-103) - Sons Espaciais, Sci-Fi e Efeitos Futuristas
    (96, "FX 1 (rain)", "Synth Effects"),
    (97, "FX 2 (soundtrack)", "Synth Effects"),
    (98, "FX 3 (crystal)", "Synth Effects"),
    (99, "FX 4 (atmosphere)", "Synth Effects"),
    (100, "FX 5 (brightness)", "Synth Effects"),
    (101, "FX 6 (goblins)", "Synth Effects"),
    (102, "FX 7 (echoes)", "Synth Effects"),
    (103, "FX 8 (sci-fi)", "Synth Effects"),
    # Ethnic (104-111)
    (104, "Sitar", "Ethnic"),
    (105, "Banjo", "Ethnic"),
    (106, "Shamisen", "Ethnic"),
    (107, "Koto", "Ethnic"),
    (108, "Kalimba", "Ethnic"),
    (109, "Bag pipe", "Ethnic"),
    (110, "Fiddle", "Ethnic"),
    (111, "Shanai", "Ethnic"),
    # Percussive (112-119)
    (112, "Tinkle Bell", "Percussive"),
    (113, "Agogo", "Percussive"),
    (114, "Steel Drums", "Percussive"),
    (115, "Woodblock", "Percussive"),
    (116, "Taiko Drum", "Percussive"),
    (117, "Melodic Tom", "Percussive"),
    (118, "Synth Drum", "Percussive"),
    (119, "Reverse Cymbal", "Percussive"),
    # Sound Effects (120-127)
    (120, "Guitar Fret Noise", "SFX"),
    (121, "Breath Noise", "SFX"),
    (122, "Seashore", "SFX"),
    (123, "Bird Tweet", "SFX"),
    (124, "Telephone Ring", "SFX"),
    (125, "Helicopter", "SFX"),
    (126, "Applause", "SFX"),
    (127, "Gunshot", "SFX"),
]

# Categorias organizadas com ícones para o Explorador de Sons
GM_CATEGORIES = {
    "🌌 Sons Espaciais e Sci-Fi": [103, 97, 99, 98, 101, 102, 96, 100],
    "🛸 Sintetizadores e Pads": [88, 89, 90, 91, 92, 93, 94, 95, 80, 81, 82, 83, 84, 85, 86, 87],
    "💥 Efeitos Especiais & FX": [119, 118, 112, 120, 121, 122, 123, 124, 125, 126, 127],
    "🎸 Guitarras e Baixos": [24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39],
    "🎹 Pianos e Teclados": [0, 1, 2, 3, 4, 5, 6, 7, 16, 17, 18, 19, 20, 21, 22, 23],
    "🎻 Orquestra e Metais": [40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79],
    "🌍 Étnicos e Percussão": [104, 105, 106, 107, 108, 109, 110, 111, 113, 114, 115, 116, 117],
}

# Nomes descritivos e amigáveis em Português para cada um dos 128 instrumentos
INSTRUMENT_PORTUGUESE_NAMES = {
    # Espaciais e Sci-Fi (96-103)
    103: "🌌 Efeito Sci-Fi (Laser / Nave Espacial)",
    97:  "🛸 Trilha Espacial (Soundtrack Cósmico)",
    99:  "🔮 Atmosfera Alienígena (Deep Space)",
    98:  "💎 Cristais Cósmicos (Crystal Synth)",
    101: "👽 Goblins & Criaturas Alienígenas",
    102: "🪐 Ecos do Espaço (Cosmic Echoes)",
    96:  "🌧️ Chuva Espacial (Rain FX)",
    100: "✨ Brilho Estelar (Brightness FX)",
    # Pads Espaciais (88-95)
    88:  "🌌 Pad New Age (Fantasia Cósmica)",
    89:  "🛸 Pad Quente (Warm Synth)",
    90:  "⚡ Polysynth (Sintetizador Retrô 80s)",
    91:  "👼 Pad Celestial (Coro Sintético)",
    92:  "🎻 Pad Bowed (Vidro Espacial)",
    93:  "⚡ Pad Metálico (Metallic Pad)",
    94:  "😇 Pad Halo (Angelical)",
    95:  "🌪️ Pad Sweep (Vento Cósmico)",
    # Leads (80-87)
    80:  "👾 Synth 8-Bit Arcade (Chiptune)",
    81:  "⚡ Synth Solo Sawtooth (Dente de Serra)",
    82:  "🎶 Synth Calíope",
    83:  "💨 Synth Chiff",
    84:  "🎸 Synth Charang",
    85:  "🗣️ Voz Sintética Solo",
    86:  "🎹 Synth em Quintas",
    87:  "🔊 Baixo + Synth Solo",
    # Efeitos & Percussivos (112-127)
    119: "🔄 Prato Invertido (Reverse Cymbal)",
    118: "🥁 Bateria Sintética Espacial",
    112: "🔔 Sino Mágico (Tinkle Bell)",
    127: "💥 Tiro / Explosão (Gunshot)",
    125: "🚁 Helicóptero",
    126: "👏 Aplausos da Plateia",
    122: "🌊 Ondas do Mar (Seashore)",
    123: "🐦 Canto de Pássaros",
    124: "☎️ Telefone Antigo Tocando",
    120: "🎸 Chiado de Traste",
    121: "💨 Respiração",
    # Guitarras e Baixos
    24:  "🎸 Violão de Nylon Clássico",
    25:  "🎸 Violão Acústico de Aço",
    26:  "🎸 Guitarra Jazz",
    27:  "🎸 Guitarra Limpa (Clean)",
    28:  "🎸 Guitarra Muted (Abafada)",
    29:  "🎸 Guitarra Rock (Distorção / Overdrive)",
    30:  "🎸 Guitarra Metal Pesada (Distortion)",
    31:  "🎸 Harmônicos de Guitarra",
    32:  "🎸 Baixo Acústico",
    33:  "🎸 Baixo Elétrico (Dedo)",
    34:  "🎸 Baixo Elétrico (Palheta)",
    35:  "🎸 Baixo Fretless",
    36:  "🎸 Baixo Slap 1",
    37:  "🎸 Baixo Slap 2",
    38:  "🎸 Baixo Sintetizador 1",
    39:  "🎸 Baixo Sintetizador 2",
    # Pianos e Teclados
    0:   "🎹 Piano de Cauda Acústico",
    1:   "🎹 Piano Acústico Brilhante",
    2:   "🎹 Piano Elétrico de Cauda",
    3:   "🎹 Piano Honky-Tonk (Saloon)",
    4:   "🎹 Piano Elétrico 1 (Rhodes)",
    5:   "🎹 Piano Elétrico 2 (Chorused)",
    6:   "🎹 Cravo (Harpsichord)",
    7:   "🎹 Clavinete",
    16:  "🎹 Órgão Drawbar",
    17:  "🎹 Órgão Percussivo",
    18:  "🎹 Órgão de Rock",
    19:  "🎹 Órgão de Igreja",
    20:  "🎹 Órgão Reed",
    21:  "🪗 Acordeom",
    22:  "🎶 Gaita (Harmônica)",
    23:  "🪗 Bandoneon de Tango",
    # Cordas e Orquestra
    40:  "🎻 Violino",
    41:  "🎻 Viola",
    42:  "🎻 Violoncelo",
    43:  "🎻 Contrabaixo Orquestral",
    44:  "🎻 Cordas Trêmulas",
    45:  "🎻 Cordas Pizzicato",
    46:  "🎻 Harpa Orquestral",
    47:  "🥁 Tímpanos",
    48:  "🎻 Orquestra de Cordas 1",
    49:  "🎻 Orquestra de Cordas 2",
    50:  "🎻 Cordas Sintéticas 1",
    51:  "🎻 Cordas Sintéticas 2",
    52:  "🗣️ Coro de Vozes (Aahs)",
    53:  "🗣️ Coro de Vozes (Oohs)",
    54:  "🗣️ Vozes Sintéticas",
    55:  "💥 Orchestra Hit",
    # Metais e Sopros
    56:  "🎺 Trompete",
    57:  "🎺 Trombone",
    58:  "🎺 Tuba",
    59:  "🎺 Trompete com Surdina",
    60:  "🎺 Trompa Francesa",
    61:  "🎺 Metais / Brass Section",
    62:  "🎺 Synth Brass 1",
    63:  "🎺 Synth Brass 2",
    64:  "🎷 Sax Soprano",
    65:  "🎷 Sax Alto",
    66:  "🎷 Sax Tenor",
    67:  "🎷 Sax Barítono",
    68:  "🎶 Oboé",
    69:  "🎶 Cornetim Inglês",
    70:  "🎶 Fagote",
    71:  "🎶 Clarinete",
    72:  "🎶 Flautim (Piccolo)",
    73:  "🎶 Flauta",
    74:  "🎶 Flauta Doce",
    75:  "🎶 Flauta de Pã",
    76:  "🎶 Garrafa Soprada",
    77:  "🎶 Shakuhachi Japonês",
    78:  "🎶 Assobio",
    79:  "🎶 Ocarina",
    # Étnicos
    104: "🪕 Sitar Indiano",
    105: "🪕 Banjo",
    106: "🪕 Shamisen Japonês",
    107: "🪕 Koto Japonês",
    108: "🎶 Kalimba Africana",
    109: "🎶 Gaita de Foles Escocesa",
    110: "🎻 Fiddle Country",
    111: "🎶 Shanai Oriental",
    113: "🔔 Agogô",
    114: "🥁 Steel Drums Caribenho",
    115: "🪵 Bloco de Madeira",
    116: "🥁 Tambor Taiko Japonês",
    117: "🥁 Tom Melódico",
}

# Mapa rápido id -> nome
INSTRUMENT_NAMES = {num: name for num, name, _ in GM_INSTRUMENTS}

# Sons de Percussão Padrão General MIDI (Canal 10)
GM_DRUM_SOUNDS = [
    (35, "Acoustic Bass Drum (Bumbo Acústico)"),
    (36, "Bass Drum 1 (Bumbo Pedal)"),
    (37, "Side Stick (Aro da Caixa)"),
    (38, "Acoustic Snare (Caixa Acústica)"),
    (39, "Hand Clap (Palmas)"),
    (40, "Electric Snare (Caixa Elétrica)"),
    (41, "Low Floor Tom (Surdo Baixo)"),
    (42, "Closed Hi-Hat (Chimbal Fechado)"),
    (43, "High Floor Tom (Surdo Alto)"),
    (44, "Pedal Hi-Hat (Chimbal Pedal)"),
    (45, "Low Tom (Tom Baixo)"),
    (46, "Open Hi-Hat (Chimbal Aberto)"),
    (47, "Low-Mid Tom (Tom Médio-Grave)"),
    (48, "Hi-Mid Tom (Tom Médio-Agudo)"),
    (49, "Crash Cymbal 1 (Prato de Ataque 1)"),
    (50, "High Tom (Tom Agudo)"),
    (51, "Ride Cymbal 1 (Prato de Condução 1)"),
    (52, "Chinese Cymbal (Prato Chinês)"),
    (53, "Ride Bell (Cúpula do Ride)"),
    (54, "Tambourine (Pandeiro)"),
    (55, "Splash Cymbal (Prato Splash)"),
    (56, "Cowbell (Caneca/Sino)"),
    (57, "Crash Cymbal 2 (Prato de Ataque 2)"),
    (58, "Vibraslap"),
    (59, "Ride Cymbal 2 (Prato de Condução 2)"),
]

GM_DRUM_NAMES = {note: name for note, name in GM_DRUM_SOUNDS}

# Nota musical (0-127) para nome (ex: 60 -> C4)
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Intervalos de acordes em semitons a partir da tônica
CHORD_INTERVALS = {
    "Nota Única (Solo)": [0],
    "Power Chord (5ª)": [0, 7, 12],
    "Acorde Maior": [0, 4, 7],
    "Acorde Menor": [0, 3, 7],
    "Sétima Dominante (7)": [0, 4, 7, 10],
    "Menor com 7ª (m7)": [0, 3, 7, 10],
    "Maior com 7ª Maior (maj7)": [0, 4, 7, 11],
    "Sus4": [0, 5, 7],
    "Oitava Dupla": [0, 12],
}

def midi_note_to_name(note_number: int) -> str:
    """Converte número de nota MIDI (0-127) em formato legível (ex: 60 -> C4)."""
    if not (0 <= note_number <= 127):
        return str(note_number)
    octave = (note_number // 12) - 1
    name = NOTE_NAMES[note_number % 12]
    return f"{name}{octave}"

def name_to_midi_note(name: str, octave: int) -> int:
    """Calcula o número MIDI a partir do nome da nota e oitava (ex: 'E', 3 -> 52)."""
    if name in NOTE_NAMES:
        idx = NOTE_NAMES.index(name)
        return (octave + 1) * 12 + idx
    return 60

def build_chord_notes(root_note: int, chord_type: str) -> list[int]:
    """Gera lista de notas MIDI para o acorde especificado."""
    intervals = CHORD_INTERVALS.get(chord_type, [0])
    return [max(0, min(127, root_note + i)) for i in intervals]

# Instrumentos mais populares e sons especiais organizados
POPULAR_INSTRUMENTS = [
    # Guitarras & Baixos
    (29, "🎸 Guitarra Rock (Distorção / Overdrive)"),
    (30, "🎸 Guitarra Metal Pesada (Distortion)"),
    (27, "🎸 Guitarra Limpa (Clean)"),
    (25, "🎸 Violão Acústico de Aço"),
    (24, "🎸 Violão de Nylon Clássico"),
    (28, "🎸 Guitarra Muted (Abafada)"),
    (33, "🎸 Baixo Elétrico (Dedo)"),
    (36, "🎸 Baixo Slap"),
    (38, "🎸 Baixo Sintetizador"),
    # Sons Espaciais, Sci-Fi e Efeitos Futuristas
    (103, "🌌 Som Espacial Sci-Fi (Laser / Nave)"),
    (97,  "🛸 Trilha Espacial (Soundtrack Cósmico)"),
    (99,  "🔮 Atmosfera Alienígena (Deep Space)"),
    (98,  "💎 Cristais Cósmicos (Crystal Synth)"),
    (101, "👽 Goblins & Criaturas Alienígenas"),
    (102, "🪐 Ecos do Espaço (Cosmic Echoes)"),
    (96,  "🌧️ Chuva Espacial (Rain FX)"),
    (88,  "🌌 Pad New Age (Fantasia Cósmica)"),
    (89,  "🛸 Pad Quente (Warm Synth)"),
    (90,  "⚡ Polysynth (Sintetizador Retrô 80s)"),
    (95,  "🌪️ Pad Sweep (Vento Cósmico)"),
    (80,  "👾 Synth 8-Bit Arcade (Chiptune)"),
    # Pianos e Teclados
    (0,   "🎹 Piano de Cauda"),
    (4,   "🎹 Piano Elétrico (Rhodes)"),
    (18,  "🎹 Órgão de Rock"),
    (81,  "🎹 Sintetizador Solo (Lead)"),
    # Orquestra e Metais
    (48,  "🎻 Orquestra / Cordas (Strings)"),
    (61,  "🎺 Metais / Brass Section"),
    (65,  "🎷 Saxofone"),
    (56,  "🎺 Trompete"),
    (73,  "🎶 Flauta"),
    # Efeitos Especiais & FX
    (119, "🔄 Prato Invertido (Reverse Cymbal)"),
    (118, "🥁 Bateria Sintética Espacial"),
    (112, "🔔 Sino Mágico (Tinkle Bell)"),
    (127, "💥 Efeito: Tiro / Explosão"),
    (125, "🚁 Efeito: Helicóptero"),
    (126, "👏 Efeito: Aplausos da Plateia"),
    (122, "🌊 Efeito: Ondas do Mar"),
    (123, "🐦 Efeito: Pássaros"),
]

# Estilos e Afinações Rápidas para MUDAR TODAS AS CASAS DE UMA VEZ
QUICK_FRET_PRESETS = {
    "⚡ Rock Power Chords (Clássico)": {
        "green": {"notes": [40, 47, 52], "label": "E5 (Mi)"},
        "red": {"notes": [45, 52, 57], "label": "A5 (Lá)"},
        "yellow": {"notes": [50, 57, 62], "label": "D5 (Ré)"},
        "blue": {"notes": [55, 62, 67], "label": "G5 (Sol)"},
        "orange": {"notes": [59, 66, 71], "label": "B5 (Si)"},
        "open_strum": {"notes": [40, 47], "label": "E5 Solto"}
    },
    "🌌 Viagem Espacial (Sci-Fi Cósmico)": {
        "green": {"notes": [48, 55, 62, 67], "label": "Cmaj9 (Nebulosa)"},
        "red": {"notes": [53, 60, 67, 72], "label": "Fmaj9 (Supernova)"},
        "yellow": {"notes": [45, 52, 59, 64], "label": "Am9 (Buraco Negro)"},
        "blue": {"notes": [50, 57, 64, 69], "label": "Dm9 (Órbita)"},
        "orange": {"notes": [47, 54, 61, 66], "label": "Bdim (Interestelar)"},
        "open_strum": {"notes": [36, 48, 60], "label": "Eco Cósmico"}
    },
    "🛸 Trilha Sonora Sci-Fi (Atmosfera)": {
        "green": {"notes": [36, 43, 48, 55], "label": "C-Sus2 (Vazio)"},
        "red": {"notes": [41, 48, 53, 60], "label": "F-Sus2 (Aurora)"},
        "yellow": {"notes": [43, 50, 55, 62], "label": "G-Sus4 (Solar)"},
        "blue": {"notes": [38, 45, 50, 57], "label": "D-Sus2 (Pulsar)"},
        "orange": {"notes": [40, 47, 52, 59], "label": "E-Min (Galáxia)"},
        "open_strum": {"notes": [36, 48], "label": "Drone Cósmico"}
    },
    "⚡ Synthwave Anos 80 (Retrô)": {
        "green": {"notes": [45, 52, 57], "label": "Am (Neon)"},
        "red": {"notes": [41, 48, 53], "label": "F (Cyberpunk)"},
        "yellow": {"notes": [48, 55, 60], "label": "C (Outrun)"},
        "blue": {"notes": [43, 50, 55], "label": "G (Grid)"},
        "orange": {"notes": [38, 45, 50], "label": "Dm (Nightcall)"},
        "open_strum": {"notes": [45, 57], "label": "Bassline"}
    },
    "⚡ Acordes Maiores (Pop / Balada)": {
        "green": {"notes": [48, 52, 55], "label": "C (Dó)"},
        "red": {"notes": [55, 59, 62], "label": "G (Sol)"},
        "yellow": {"notes": [50, 54, 57], "label": "D (Ré)"},
        "blue": {"notes": [45, 49, 52], "label": "A (Lá)"},
        "orange": {"notes": [40, 44, 47], "label": "E (Mi)"},
        "open_strum": {"notes": [48, 55], "label": "C Solto"}
    },
    "⚡ Acordes Menores (Emocional)": {
        "green": {"notes": [45, 48, 52], "label": "Am (Lá Menor)"},
        "red": {"notes": [40, 43, 47], "label": "Em (Mi Menor)"},
        "yellow": {"notes": [50, 53, 57], "label": "Dm (Ré Menor)"},
        "blue": {"notes": [47, 50, 54], "label": "Bm (Si Menor)"},
        "orange": {"notes": [41, 44, 48], "label": "Fm (Fá Menor)"},
        "open_strum": {"notes": [45, 52], "label": "Am Solto"}
    },
    "⚡ Escala Pentatônica (Solos Rock)": {
        "green": {"notes": [40], "label": "Mi (E2)"},
        "red": {"notes": [43], "label": "Sol (G2)"},
        "yellow": {"notes": [45], "label": "Lá (A2)"},
        "blue": {"notes": [47], "label": "Si (B2)"},
        "orange": {"notes": [50], "label": "Ré (D3)"},
        "open_strum": {"notes": [40], "label": "E Solto"}
    },
    "⚡ Metal Pesado (Drop D)": {
        "green": {"notes": [38, 45, 50], "label": "D5 (Drop D)"},
        "red": {"notes": [41, 48, 53], "label": "F5 (Fá)"},
        "yellow": {"notes": [43, 50, 55], "label": "G5 (Sol)"},
        "blue": {"notes": [44, 51, 56], "label": "Ab5 (Sol#)"},
        "orange": {"notes": [45, 52, 57], "label": "A5 (Lá)"},
        "open_strum": {"notes": [38, 45], "label": "D5 Solto"}
    },
    "⚡ Blues / Sertanejo com 7ª": {
        "green": {"notes": [40, 44, 47, 50], "label": "E7 (Mi 7ª)"},
        "red": {"notes": [45, 49, 52, 55], "label": "A7 (Lá 7ª)"},
        "yellow": {"notes": [47, 51, 54, 57], "label": "B7 (Si 7ª)"},
        "blue": {"notes": [50, 54, 57, 60], "label": "D7 (Ré 7ª)"},
        "orange": {"notes": [55, 59, 62, 65], "label": "G7 (Sol 7ª)"},
        "open_strum": {"notes": [40, 47], "label": "E7 Solto"}
    }
}
