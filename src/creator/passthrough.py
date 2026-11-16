"""Repasse sem perdas ("passthrough") de dados MIDI que o modelo não edita.

Na importação de um notes.mid, tudo que o ChartSong não representa como nota
editável é guardado cru, em milissegundos absolutos, e regravado sem mudança
pelo gerador MIDI (convertido pelo mapa de tempo da música):

- trilhas inteiras que o MidGuitar não edita (HARM1-3, VENUE, PART GUITAR GHL,
  PART ELITE_DRUMS, PART REAL_GUITAR_22, PART KEYS_ANIM_*, BEAT...):
  ``song.passthrough_tracks = [{"name": str|None, "events": [[ms, msg], ...]}]``
- marcadores dentro das trilhas editáveis (overdrive 116, solo 103, frases
  vocais 105/106, marcadores de tom 110-112, fills 120-124, HOPO forçado,
  canais e marcadores do Pro Guitar, textos como [ENHANCED_OPENS]...):
  ``song.track_extras = {"PART DRUMS": {"notes": [[on_ms, off_ms, pitch, vel, ch]],
  "events": [[ms, msg]]}}``

``msg`` é o dicionário de uma mensagem mido (sem ``time``), serializável em JSON.
"""
from typing import Dict, List, Optional, Tuple

import mido
from mido import Message, MetaMessage

# Trilhas editáveis pelo MidGuitar (nome exato no MIDI)
EDITABLE_TRACKS = (
    "PART GUITAR", "PART BASS", "PART DRUMS", "PART KEYS", "PART VOCALS",
    "PART REAL_GUITAR", "PART REAL_BASS",
    "PART REAL_KEYS_X", "PART REAL_KEYS_H", "PART REAL_KEYS_M", "PART REAL_KEYS_E",
)

# Trilhas que o Rock Band 2 não conhece (omitidas quando include_rb3_tracks=False)
_RB3_ONLY_PREFIXES = ("PART REAL_", "PART KEYS", "HARM")
_RB3_ONLY_MARKERS = ("GHL", "ELITE")

# Precisão (casas decimais) dos tempos guardados em ms
_MS_DECIMALS = 3


# Trilhas que o Rock Band 3 lê (RB3/PS3/Xbox/PS4); o resto (GHL, ELITE_DRUMS,
# REAL_DRUMS_PS, RHYTHM, COOP, DRUMS_2X...) é só do Clone Hero/YARG e fica de fora
ROCK_BAND_TRACKS = frozenset(EDITABLE_TRACKS) | {
    "PART REAL_GUITAR_22", "PART REAL_BASS_22", "PART KEYS_ANIM_RH", "PART KEYS_ANIM_LH",
    "HARM1", "HARM2", "HARM3", "BEAT", "EVENTS", "VENUE",
}


def is_rock_band_track(name: Optional[str]) -> bool:
    """True para trilhas que o Rock Band 3 conhece (nome exato, sem diferenciar caixa)."""
    return (name or "").strip().upper() in ROCK_BAND_TRACKS


def is_rb3_only_track(name: Optional[str]) -> bool:
    """True para trilhas exclusivas do RB3 (ou de outros jogos) que o RB2 não lê."""
    up = (name or "").strip().upper()
    if up.startswith(_RB3_ONLY_PREFIXES):
        return True
    return any(m in up for m in _RB3_ONLY_MARKERS)


def msg_to_dict(msg) -> dict:
    """Mensagem mido -> dicionário JSON (sem o delta ``time``)."""
    d = msg.dict()
    d.pop("time", None)
    if msg.is_meta:
        d["meta"] = True
    for k, v in list(d.items()):
        if isinstance(v, (tuple, bytes, bytearray)) or type(v).__name__ == "SysexData":
            d[k] = list(v)
    return d


def dict_to_msg(d: dict, time: int = 0):
    """Dicionário de msg_to_dict -> mensagem mido com o delta ``time``."""
    d = dict(d)
    is_meta = d.pop("meta", False)
    typ = d.pop("type")
    if "data" in d and isinstance(d["data"], list):
        d["data"] = tuple(d["data"])
    if not is_meta:
        return Message(typ, time=time, **d)
    if typ == "unknown_meta":
        return mido.UnknownMetaMessage(d.get("type_byte", 0x7F), d.get("data", ()), time=time)
    return MetaMessage(typ, time=time, **d)


def ms(value: float) -> float:
    return round(float(value), _MS_DECIMALS)


def read_track(track, tm) -> Tuple[Optional[str], list, list, list]:
    """Lê uma trilha em ticks absolutos.

    Retorna (nome, notas, outros, crus):
      notas  = [(início, fim, altura, velocity, canal)] pareadas (FIFO por canal/altura)
      outros = [(tick, msg)] mensagens que não são nota nem nome/fim de trilha
      crus   = [(tick, msg)] todas as mensagens, exceto nome e fim de trilha
    note_on sem note_off (ou o contrário) ficam em ``outros`` como mensagens soltas.
    """
    name = None
    tick = 0
    active: Dict[tuple, list] = {}
    notes, others, raw = [], [], []
    for msg in track:
        tick += msg.time
        if msg.type == "track_name" and name is None:
            name = msg.name
            continue
        if msg.type == "end_of_track":
            continue
        raw.append((tick, msg))
        if msg.type == "note_on" and msg.velocity > 0:
            active.setdefault((msg.channel, msg.note), []).append((tick, msg))
        elif msg.type in ("note_on", "note_off"):
            pending = active.get((msg.channel, msg.note))
            if pending:
                start, on = pending.pop(0)
                notes.append((start, tick, msg.note, on.velocity, msg.channel))
            else:
                others.append((tick, msg))
        else:
            others.append((tick, msg))
    for pending in active.values():
        others.extend(pending)
    others.sort(key=lambda x: x[0])
    return name, notes, others, raw


def raw_track_from_midi(name: Optional[str], raw: list, tm) -> dict:
    """Trilha inteira crua: eventos em ms absolutos, na ordem original."""
    return {"name": name, "events": [[ms(tm.tick_to_ms(t)), msg_to_dict(m)] for t, m in raw]}


def new_extras() -> dict:
    return {"notes": [], "events": []}


def add_extra_note(extras: dict, tm, start: int, end: int, pitch: int, vel: int, ch: int):
    extras["notes"].append([ms(tm.tick_to_ms(start)), ms(tm.tick_to_ms(end)), int(pitch), int(vel), int(ch)])


def add_extra_event(extras: dict, tm, tick: int, msg):
    extras["events"].append([ms(tm.tick_to_ms(tick)), msg_to_dict(msg)])


def extra_pitches(extras: Optional[dict]) -> set:
    return {int(n[2]) for n in (extras or {}).get("notes", [])}


def extra_notes_ticks(extras: Optional[dict], tm) -> list:
    """Notas repassadas em ticks: [(início, fim, altura, velocity, canal)]."""
    out = []
    for on_ms, off_ms, pitch, vel, ch in (extras or {}).get("notes", []):
        s = max(0, tm.ms_to_tick(on_ms))
        e = max(s, tm.ms_to_tick(off_ms))
        out.append((s, e, int(pitch), int(vel), int(ch)))
    return out


def extra_events_ticks(extras: Optional[dict], tm) -> list:
    """Mensagens repassadas em ticks: [(tick, msg)]."""
    return [(max(0, tm.ms_to_tick(t)), dict_to_msg(d)) for t, d in (extras or {}).get("events", [])]


def emit_raw_track(track, events: List[list], tm):
    """Grava eventos crus (ms absolutos) numa trilha, mantendo a ordem original."""
    last = 0
    for t, d in events:
        tick = max(last, max(0, tm.ms_to_tick(t)))
        track.append(dict_to_msg(d, time=tick - last))
        last = tick
