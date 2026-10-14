"""
Lista de instrumentos padrão General MIDI (GM1) divididos por categoria.
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
    # Synth Pad (88-95)
    (88, "Pad 1 (new age)", "Synth Pad"),
    (89, "Pad 2 (warm)", "Synth Pad"),
    (90, "Pad 3 (polysynth)", "Synth Pad"),
    (91, "Pad 4 (choir)", "Synth Pad"),
    (92, "Pad 5 (bowed)", "Synth Pad"),
    (93, "Pad 6 (metallic)", "Synth Pad"),
    (94, "Pad 7 (halo)", "Synth Pad"),
    (95, "Pad 8 (sweep)", "Synth Pad"),
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

# Mapa rápido id -> nome
INSTRUMENT_NAMES = {num: name for num, name, _ in GM_INSTRUMENTS}

# Nota musical (0-127) para nome (ex: 60 -> C4)
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

def midi_note_to_name(note_number: int) -> str:
    """Converte número de nota MIDI (0-127) em formato legível (ex: 60 -> C4)."""
    if not (0 <= note_number <= 127):
        return str(note_number)
    octave = (note_number // 12) - 1
    name = NOTE_NAMES[note_number % 12]
    return f"{name}{octave}"
