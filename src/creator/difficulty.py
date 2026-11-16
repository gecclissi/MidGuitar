"""Cálculo automático do ranking de dificuldade (0 a 6) por instrumento."""

from typing import List, Optional

# Limites de densidade (notas por segundo, só dificuldade Expert, instantes distintos)
# para cada nível. Abaixo do primeiro limite o nível é 1; acima do último, 6.
#   < 0.6/s -> 1 | < 1.3/s -> 2 | < 2.2/s -> 3 | < 3.5/s -> 4 | < 5.0/s -> 5 | >= 5.0/s -> 6
DENSITY_THRESHOLDS = (0.6, 1.3, 2.2, 3.5, 5.0)

# Vocais são medidos em notas por segundo de música (frases cantadas são mais esparsas)
VOCAL_DENSITY_THRESHOLDS = (0.4, 0.8, 1.3, 1.9, 2.6)


def _expert_times(notes) -> List[int]:
    """Instantes distintos (ms) das notas Expert; acordes contam como um só ataque.
    Frases de overdrive/solo não são notas tocáveis e não contam."""
    times = set()
    for n in notes:
        if getattr(n, "difficulty", "Expert") == "Expert" and getattr(n, "lane", None) not in ("overdrive", "solo"):
            times.add(int(n.time_ms))
    return sorted(times)


def _tier(density: float, thresholds) -> int:
    tier = 1
    for limit in thresholds:
        if density >= limit:
            tier += 1
    return tier


def calculate_tier(notes, duration_ms: Optional[int] = None, vocal: bool = False) -> int:
    """Nível 0-6 de uma trilha pela densidade de notas Expert; 0 se não houver notas.

    A densidade usa o trecho ativo (primeira a última nota, no mínimo 30 s) quando
    duration_ms não é informado, para que silêncio no começo ou no fim não "dilua" a música.
    """
    times = _expert_times(notes) if not vocal else sorted({int(n.time_ms) for n in notes})
    if not times:
        return 0
    span_ms = max(30000, times[-1] - times[0]) if not duration_ms else max(30000, int(duration_ms))
    density = len(times) / (span_ms / 1000.0)
    return _tier(density, VOCAL_DENSITY_THRESHOLDS if vocal else DENSITY_THRESHOLDS)


def calculate_rankings(song) -> None:
    """Preenche diff_* e diff_band da música a partir da densidade de notas por instrumento."""
    dur = song.get_effective_duration_ms() if hasattr(song, "get_effective_duration_ms") else None
    song.diff_guitar = calculate_tier(song.guitar_notes, dur)
    song.diff_bass = calculate_tier(song.bass_notes, dur)
    song.diff_drums = calculate_tier(song.drum_notes, dur)
    song.diff_keys = calculate_tier(song.keys_notes, dur)
    song.diff_pro_guitar = calculate_tier(song.pro_guitar_notes, dur)
    song.diff_pro_bass = calculate_tier(song.pro_bass_notes, dur)
    song.diff_pro_keys = calculate_tier(song.pro_keys_notes, dur)
    song.diff_vocals = calculate_tier(song.vocal_notes, dur, vocal=True)
    active = [t for t in (song.diff_guitar, song.diff_bass, song.diff_drums,
                          song.diff_keys, song.diff_vocals) if t > 0]
    song.diff_band = int(round(sum(active) / len(active))) if active else 0
