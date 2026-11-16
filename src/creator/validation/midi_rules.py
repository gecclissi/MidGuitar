"""Regras de validação do MIDI exportado, por perfil de destino.

Funções puras: devolvem List[Issue] e nunca lançam exceção.
"""
import os
from collections import Counter
from typing import Dict, List, Set, Tuple

import mido

from src.creator.rbn_specs import (
    DRUM_NOTES, FRET_NOTES, PRO_GUITAR_STRING_BASE, TICKS_PER_BEAT,
    VOCAL_OVERDRIVE, VOCAL_PHRASE_MARKER, VOCAL_PITCH_MAX, VOCAL_PITCH_MIN,
)
from src.creator.validation.issues import Issue
from src.creator.validation.profiles import TargetProfile

_RANGE_TRACKS = {"PART GUITAR", "PART BASS", "PART KEYS", "PART DRUMS"}
_VOCAL_TRACKS = {"PART VOCALS", "HARM1", "HARM2", "HARM3"}
# trilhas Pro de cordas -> velocidade máxima permitida (17 casas / 22 casas)
_PRO_STRING_TRACKS = {"PART REAL_GUITAR": 117, "PART REAL_GUITAR_22": 122,
                      "PART REAL_BASS": 117, "PART REAL_BASS_22": 122}
_MARKERS = ("[music_start]", "[music_end]", "[end]")

_ACCEPTED_NOTES: Set[int] = set()
for _d in (FRET_NOTES, DRUM_NOTES):
    for _lanes in _d.values():
        _ACCEPTED_NOTES.update(_lanes.values())
_ACCEPTED_NOTES.update([95, 103, 116, 127])
_ACCEPTED_NOTES.update(range(105, 113))
_ACCEPTED_NOTES.update(range(120, 125))
_ACCEPTED_NOTES.update(range(12, 16))   # animação
_ACCEPTED_NOTES.update([104, 126])      # tap e faixa de tremolo/trill/roll
_EXTRA_ACCEPTED = {
    "PART DRUMS": set(range(24, 52)),    # animação / hi-hat aberto
    # animação da mão do braço + notas abertas [ENHANCED_OPENS] do Clone Hero (59/71/83/95)
    "PART GUITAR": set(range(40, 60)) | {71, 83},
    "PART BASS": set(range(40, 60)) | {71, 83},
}


def _track_name(track) -> str:
    for m in track:
        if m.type == "track_name":
            return m.name
    return ""


def _is_note_on(m) -> bool:
    return m.type == "note_on" and m.velocity > 0


def _is_note_off(m) -> bool:
    return m.type == "note_off" or (m.type == "note_on" and m.velocity == 0)


def midi_track_names(path: str) -> Set[str]:
    """Nomes das trilhas do MIDI; conjunto vazio se o arquivo for ilegível."""
    try:
        mid = mido.MidiFile(path)
        return {n for n in (_track_name(t) for t in mid.tracks) if n}
    except Exception:
        return set()


class _Collector:
    """Acumula Issues; avisos repetidos viram 1 Issue por (código, trilha)."""

    def __init__(self, fname: str):
        self.fname = fname
        self.issues: list = []
        self._groups: Dict[Tuple[str, str], list] = {}

    def loc(self, track: str = "", tick=None) -> str:
        parts = [self.fname]
        if track:
            parts.append(track)
        if tick is not None:
            parts.append("tick %d" % tick)
        return " › ".join(parts)

    def add(self, level, code, message, track="", tick=None):
        self.issues.append(Issue(level, code, message, self.loc(track, tick)))

    def group(self, level, code, track, tick, singular, plural):
        """Registra uma ocorrência; a localização é a da primeira."""
        key = (code, track)
        if key not in self._groups:
            self.issues.append(None)  # reserva a posição
            self._groups[key] = [level, tick, 0, singular, plural, len(self.issues) - 1]
        self._groups[key][2] += 1

    def flush(self) -> List[Issue]:
        for (code, track), (level, tick, n, sing, plur, idx) in self._groups.items():
            msg = sing if n == 1 else plur.replace("{n}", str(n))
            self.issues[idx] = Issue(level, code, "%s (trilha %s)" % (msg, track),
                                     self.loc(track, tick))
        return [i for i in self.issues if i is not None]


def validate_midi(path: str, profile: TargetProfile) -> List[Issue]:
    """Valida o MIDI contra o perfil. Nunca lança exceção."""
    try:
        return _validate(path, profile)
    except Exception as e:  # rede de segurança: o validador não pode derrubar a exportação
        return [Issue("error", "MIDI_UNREADABLE",
                      "Não foi possível analisar o arquivo MIDI: %s" % e,
                      os.path.basename(str(path)))]


def _validate(path: str, profile: TargetProfile) -> List[Issue]:
    fname = os.path.basename(path)
    c = _Collector(fname)
    try:
        mid = mido.MidiFile(path)
    except Exception as e:
        return [Issue("error", "MIDI_UNREADABLE",
                      "Não foi possível abrir o arquivo MIDI: %s" % e, fname)]

    if mid.type != 1:
        c.add("error", "MIDI_NOT_TYPE1",
              "O MIDI precisa ser do tipo 1 (várias trilhas); este é do tipo %d" % mid.type)
    if mid.ticks_per_beat != TICKS_PER_BEAT:
        c.add("warning", "MIDI_TPB_NOT_480",
              "Resolução de %d ticks por tempo; o Rock Band espera %d"
              % (mid.ticks_per_beat, TICKS_PER_BEAT))

    if not any(m.type == "set_tempo" for t in mid.tracks for m in t):
        c.add("error", "MIDI_NO_TEMPO", "O MIDI não tem nenhuma marcação de andamento (BPM)")

    # nomes de trilhas (a trilha 0 é a de andamento e fica fora desta checagem)
    named = [(_track_name(t), t) for idx, t in enumerate(mid.tracks) if idx > 0]
    named = [(n, t) for n, t in named if n]
    counts = Counter(n for n, _ in named)
    for n, k in counts.items():
        if k > 1:
            c.add("error", "MIDI_DUPLICATE_TRACK",
                  "A trilha %s aparece %d vezes" % (n, k), n)
        if n in profile.forbid_tracks:
            c.add("error", "MIDI_FORBIDDEN_TRACK",
                  "A trilha %s não é aceita em %s" % (n, profile.label), n)
        elif n not in profile.allowed_tracks:
            c.add("warning", "MIDI_UNKNOWN_TRACK", "Trilha desconhecida: %s" % n, n)

    by_name = {}
    for n, t in named:
        by_name.setdefault(n, t)

    level_req = "error" if profile.require_beat else "warning"
    if "EVENTS" not in by_name:
        c.add(level_req, "MIDI_NO_EVENTS", "Faltando a trilha EVENTS (obrigatória no Rock Band)")
    if "BEAT" not in by_name:
        c.add(level_req, "MIDI_NO_BEAT", "Faltando a trilha BEAT (obrigatória no Rock Band)")

    markers: Dict[str, int] = {}
    if "EVENTS" in by_name:
        tick = 0
        for m in by_name["EVENTS"]:
            tick += m.time
            if m.type in ("text", "marker", "lyrics"):
                markers.setdefault(m.text.strip(), tick)
        missing = [mk for mk in _MARKERS if mk not in markers]
        if missing:
            c.add("error" if profile.require_end_markers else "warning",
                  "MIDI_MISSING_MARKER",
                  "Faltando marcadores em EVENTS: %s" % ", ".join(missing), "EVENTS")

    last_off = 0   # último note_off de qualquer PART
    last_on = 0    # última nota tocável
    for n, t in named:
        _scan_track(c, n, t)
        if n.startswith("PART") or n in _VOCAL_TRACKS:
            tick = 0
            for m in t:
                tick += m.time
                if _is_note_off(m):
                    last_off = max(last_off, tick)
                if _is_note_on(m):
                    last_on = max(last_on, tick)

    if "[end]" in markers and markers["[end]"] < last_off:
        c.add("error", "MIDI_END_BEFORE_NOTES",
              "O marcador [end] vem antes do fim das notas", "EVENTS", markers["[end]"])

    if "BEAT" in by_name:
        tick, beat_last = 0, None
        for m in by_name["BEAT"]:
            tick += m.time
            if _is_note_on(m):
                beat_last = tick
        if beat_last is not None and last_on - beat_last > 4 * mid.ticks_per_beat:
            c.add("warning", "MIDI_BEAT_SHORT",
                  "A trilha BEAT termina antes das últimas notas tocáveis", "BEAT", beat_last)

    return c.flush()


def _scan_track(c: _Collector, name: str, track) -> None:
    """Percorre uma trilha uma vez acumulando o tick absoluto."""
    tick = 0
    events = []
    for m in track:
        tick += m.time
        if _is_note_on(m) or _is_note_off(m):
            events.append((tick, m))
    # no mesmo tick, os note_off vêm antes dos note_on (ordem estável)
    events.sort(key=lambda e: (e[0], 0 if _is_note_off(e[1]) else 1))

    check_range = name in _RANGE_TRACKS
    pro_max = _PRO_STRING_TRACKS.get(name)
    active: Dict[int, int] = {}
    for tk, m in events:
        if _is_note_on(m):
            if m.note in active and active[m.note] == tk:
                # mesma nota repetida no mesmo tick: customs reais fazem isso e os jogos aceitam
                c.group("warning", "MIDI_DUPLICATE_NOTE", name, tk,
                        "Nota repetida no mesmo tick (altura %d)" % m.note,
                        "{n} notas repetidas no mesmo tick")
            elif m.note in active:
                c.group("error", "MIDI_OVERLAPPING_NOTE", name, tk,
                        "Nota sobreposta (altura %d já ativa)" % m.note,
                        "{n} notas sobrepostas (altura já ativa)")
            active[m.note] = tk
            if check_range and m.note not in _ACCEPTED_NOTES and (
                    m.note not in _EXTRA_ACCEPTED.get(name, ())) and not (
                    name == "PART KEYS" and 0 <= m.note <= 12):
                c.group("warning", "MIDI_NOTE_OUT_OF_RANGE", name, tk,
                        "1 nota fora da faixa (altura %d)" % m.note,
                        "{n} notas fora da faixa")
            if pro_max is not None and any(
                    b <= m.note <= b + 5 for b in PRO_GUITAR_STRING_BASE.values()):
                if not (100 <= m.velocity <= pro_max):
                    c.group("error", "MIDI_PRO_FRET_VELOCITY", name, tk,
                            "1 nota de corda com velocidade %d (permitido 100-%d)"
                            % (m.velocity, pro_max),
                            "{n} notas de corda com velocidade fora de 100-%d" % pro_max)
        else:
            active.pop(m.note, None)
    for pitch, tk in active.items():
        c.group("error", "MIDI_UNTERMINATED_NOTE", name, tk,
                "1 nota sem fim (altura %d)" % pitch, "{n} notas sem fim")

    if name in _VOCAL_TRACKS:
        spans, open_at, notes = [], {}, []
        for tk, m in events:
            if m.note in (VOCAL_PHRASE_MARKER, VOCAL_OVERDRIVE):
                if _is_note_on(m):
                    open_at[m.note] = tk
                elif m.note in open_at:
                    spans.append((open_at.pop(m.note), tk))
            elif VOCAL_PITCH_MIN <= m.note <= VOCAL_PITCH_MAX and _is_note_on(m):
                notes.append(tk)
        for tk in notes:
            if not any(a <= tk <= b for a, b in spans):
                c.group("warning", "MIDI_VOCAL_NOTE_OUTSIDE_PHRASE", name, tk,
                        "1 nota vocal fora de uma frase",
                        "{n} notas vocais fora de uma frase")
