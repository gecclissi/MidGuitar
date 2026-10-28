"""Regras de validação do songs.dta (uma entrada por música do pacote).

Funções puras: devolvem List[Issue] e nunca lançam exceção.
"""
import os
from typing import Any, Dict, List, Optional, Set

from src.creator.validation.dta_parser import DtaSyntaxError, parse_dta
from src.creator.validation.issues import Issue
from src.creator.validation.profiles import TargetProfile

_RANK_TRACKS = {
    "guitar": "PART GUITAR", "bass": "PART BASS", "drum": "PART DRUMS",
    "keys": "PART KEYS", "vocals": "PART VOCALS",
    "real_guitar": "PART REAL_GUITAR", "real_bass": "PART REAL_BASS",
    "real_keys": "PART REAL_KEYS_X",
}


def _field(entry: list, key: str) -> Optional[list]:
    """Primeira sublista de `entry` cujo primeiro item é `key`."""
    for item in entry:
        if isinstance(item, list) and item and item[0] == key:
            return item
    return None


def _flat_ints(value: Any) -> List[int]:
    if isinstance(value, bool):
        return []
    if isinstance(value, int):
        return [value]
    if isinstance(value, list):
        out: List[int] = []
        for v in value:
            out.extend(_flat_ints(v))
        return out
    return []


def _num(field: Optional[list]) -> Optional[float]:
    if field and len(field) > 1 and isinstance(field[1], (int, float)):
        return field[1]
    return None


def _values(field: list) -> list:
    """Valores numéricos de `(chave v1 v2 ...)` ou `(chave (v1 v2 ...))`."""
    vals = field[1:]
    if len(vals) == 1 and isinstance(vals[0], list):
        vals = vals[0]
    return [v for v in vals if isinstance(v, (int, float))]


def validate_dta(path: str, profile: TargetProfile,
                 midi_tracks_by_song: Optional[Dict[str, Set[str]]] = None,
                 mogg_channels_by_song: Optional[Dict[str, Optional[int]]] = None) -> List[Issue]:
    """Valida cada entrada do songs.dta. Nunca lança exceção."""
    try:
        return _validate(path, midi_tracks_by_song, mogg_channels_by_song)
    except Exception as e:  # rede de segurança
        return [Issue("error", "DTA_UNREADABLE",
                      "Não foi possível analisar o songs.dta: %s" % e,
                      os.path.basename(str(path)))]


def _read_text(path: str) -> str:
    with open(path, "rb") as f:
        raw = f.read()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def _validate(path, midi_tracks_by_song, mogg_channels_by_song) -> List[Issue]:
    fname = os.path.basename(path)
    try:
        text = _read_text(path)
    except OSError as e:
        return [Issue("error", "DTA_UNREADABLE",
                      "Não foi possível abrir o songs.dta: %s" % e, fname)]
    try:
        tree = parse_dta(text)
    except DtaSyntaxError as e:
        return [Issue("error", "DTA_SYNTAX", "Erro de sintaxe no songs.dta: %s" % e,
                      "%s › linha %d" % (fname, e.line))]

    issues: List[Issue] = []
    after_directive = False
    for entry in tree:
        if isinstance(entry, str) and entry.startswith("#"):
            after_directive = True   # #define/#include/#merge: a próxima lista não é música
            continue
        if isinstance(entry, list) and after_directive:
            after_directive = False
            continue
        if (isinstance(entry, list) and entry and isinstance(entry[0], str)
                and not entry[0].startswith(("#", "$"))):
            issues.extend(_validate_entry(fname, entry, midi_tracks_by_song,
                                          mogg_channels_by_song))
    return issues


def _validate_entry(fname, entry, midi_tracks_by_song, mogg_channels_by_song) -> List[Issue]:
    short = str(entry[0])
    loc = "%s › %s" % (fname, short)
    out: List[Issue] = []

    def add(level, code, msg, sub=""):
        out.append(Issue(level, code, msg, loc + (" › " + sub if sub else "")))

    for key in ("name", "artist", "rank", "song_id", "game_origin"):
        if _field(entry, key) is None:
            add("error", "DTA_MISSING_FIELD", "Faltando o campo '%s' na música %s" % (key, short))

    song = _field(entry, "song")
    pans = vols = cores = tracks = vocal_f = None
    if song is None:
        add("error", "DTA_MISSING_FIELD", "Faltando o bloco 'song' na música %s" % short)
    else:
        for key in ("name", "tracks", "pans", "vols", "cores"):
            if _field(song, key) is None:
                add("error", "DTA_MISSING_FIELD",
                    "Faltando o campo '%s' dentro de 'song' na música %s" % (key, short), "song")
        pans, vols, cores = (_field(song, k) for k in ("pans", "vols", "cores"))
        tracks = _field(song, "tracks")
        vocal_f = _field(song, "vocal_parts")
    if vocal_f is None:
        vocal_f = _field(entry, "vocal_parts")
    if vocal_f is None:
        add("error", "DTA_MISSING_FIELD", "Faltando o campo 'vocal_parts' na música %s" % short)

    if pans is not None and vols is not None and cores is not None:
        counts = [len(_values(f)) for f in (pans, vols, cores)]
        if len(set(counts)) > 1:
            add("error", "DTA_CHANNEL_MISMATCH",
                "pans, vols e cores têm contagens diferentes (%d, %d, %d)" % tuple(counts), "song")
        elif tracks is not None:
            bad = [i for i in _flat_ints(tracks[1:]) if i >= counts[0]]
            if bad:
                add("error", "DTA_CHANNEL_MISMATCH",
                    "tracks usa o canal %d, mas há só %d canais em pans/vols/cores"
                    % (max(bad), counts[0]), "song")
    if (pans is not None and mogg_channels_by_song
            and mogg_channels_by_song.get(short) is not None):
        n_pans, n_mogg = len(_values(pans)), mogg_channels_by_song[short]
        if n_pans != n_mogg:
            add("error", "DTA_MOGG_CHANNELS",
                "pans tem %d canais, mas o .mogg tem %d" % (n_pans, n_mogg), "song")

    midi_tracks = (midi_tracks_by_song or {}).get(short)
    if midi_tracks is not None:
        rank = _field(entry, "rank")
        if rank is not None:
            for inst, track in _RANK_TRACKS.items():
                val = _num(_field(rank, inst))
                if val is not None and val > 0 and track not in midi_tracks:
                    add("warning", "DTA_RANK_WITHOUT_TRACK",
                        "rank de '%s' é %s, mas o MIDI não tem a trilha %s"
                        % (inst, val, track), "rank")
        vp = _num(vocal_f)
        if vp is not None:
            if vp > 0 and "PART VOCALS" not in midi_tracks:
                add("error", "DTA_VOCAL_PARTS",
                    "vocal_parts é %s, mas o MIDI não tem PART VOCALS" % vp)
            elif vp == 0 and "PART VOCALS" in midi_tracks:
                add("warning", "DTA_VOCAL_PARTS",
                    "O MIDI tem PART VOCALS, mas vocal_parts é 0")
    return out
