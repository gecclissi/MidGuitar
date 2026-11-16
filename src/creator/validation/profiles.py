"""Perfis de destino (Clone Hero, RB3, RB2, ...) usados pelo validador."""
from dataclasses import dataclass
from typing import Dict, FrozenSet

_REAL_TRACKS = [
    "PART REAL_GUITAR", "PART REAL_GUITAR_22", "PART REAL_BASS", "PART REAL_BASS_22",
    "PART REAL_KEYS_X", "PART REAL_KEYS_H", "PART REAL_KEYS_M", "PART REAL_KEYS_E",
    "PART REAL_KEYS_ANIM_LH", "PART REAL_KEYS_ANIM_RH",
]

KNOWN_TRACKS: FrozenSet[str] = frozenset([
    "BEAT", "EVENTS", "VENUE",
    "PART GUITAR", "PART GUITAR COOP", "PART RHYTHM", "PART BASS", "PART DRUMS",
    "PART KEYS", "PART VOCALS", "HARM1", "HARM2", "HARM3",
    "PART KEYS_ANIM_LH", "PART KEYS_ANIM_RH",
] + _REAL_TRACKS)


# Trilhas que só o Clone Hero / YARG usam (GH Live, Elite Drums, Pro Drums do Phase Shift)
CLONEHERO_EXTRA_TRACKS: FrozenSet[str] = frozenset([
    "PART GUITAR GHL", "PART BASS GHL", "PART ELITE_DRUMS", "PART REAL_DRUMS_PS",
])


@dataclass(frozen=True)
class TargetProfile:
    name: str
    label: str
    verified_in_game: bool
    allowed_tracks: FrozenSet[str]
    require_beat: bool
    require_end_markers: bool
    forbid_tracks: FrozenSet[str] = frozenset()
    # .mid.edat conferido contra pacotes reais (RB2: só a fórmula do Onyx, sem referência)
    edat_verified: bool = True


_RB2_FORBIDDEN = frozenset(["PART KEYS"] + _REAL_TRACKS)

PROFILES: Dict[str, TargetProfile] = {
    "clonehero": TargetProfile("clonehero", "Clone Hero", True,
                               KNOWN_TRACKS | CLONEHERO_EXTRA_TRACKS, False, False),
    "rb3_ps3": TargetProfile("rb3_ps3", "Rock Band 3 (PS3/RPCS3)", True, KNOWN_TRACKS, True, True),
    # .mid.edat do RB2 não verificado: nenhuma referência de RB2 disponível
    "rb2": TargetProfile("rb2", "Rock Band 2", False, KNOWN_TRACKS - _RB2_FORBIDDEN, True, True,
                         _RB2_FORBIDDEN, edat_verified=False),
    "xbox360": TargetProfile("xbox360", "Rock Band 3 (Xbox 360)", False, KNOWN_TRACKS, True, True),
    "ps4": TargetProfile("ps4", "Rock Band 4 (PS4)", True, KNOWN_TRACKS, True, True),
}
