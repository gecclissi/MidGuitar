"""Mapa de tempo e compasso: conversão entre milissegundos e ticks MIDI."""
from bisect import bisect_right
from dataclasses import dataclass
from typing import List, Optional

from src.creator.rbn_specs import TICKS_PER_BEAT

DEFAULT_US_PER_BEAT = 500000  # 120 BPM


@dataclass
class TempoChange:
    tick: int
    us_per_beat: int


@dataclass
class TimeSigChange:
    tick: int
    numerator: int
    denominator: int


def _dedupe_by_tick(items):
    """Ordena por tick (estável) e mantém a última entrada de cada tick."""
    by_tick = {}
    for item in sorted(items, key=lambda x: x.tick):
        by_tick[item.tick] = item
    return [by_tick[t] for t in sorted(by_tick)]


class TempoMap:
    def __init__(self, ticks_per_beat: int = TICKS_PER_BEAT,
                 tempos: Optional[List[TempoChange]] = None,
                 time_sigs: Optional[List[TimeSigChange]] = None):
        self.ticks_per_beat = ticks_per_beat
        valid = [t for t in (tempos or []) if t.us_per_beat > 0]
        self.tempos = _dedupe_by_tick(valid)
        if not self.tempos or self.tempos[0].tick != 0:
            self.tempos.insert(0, TempoChange(0, DEFAULT_US_PER_BEAT))
        self.time_sigs = _dedupe_by_tick(list(time_sigs or []))
        if not self.time_sigs or self.time_sigs[0].tick != 0:
            self.time_sigs.insert(0, TimeSigChange(0, 4, 4))
        self._rebuild()

    def _rebuild(self):
        self._ticks = [t.tick for t in self.tempos]
        self._ms_at = []
        ms = 0.0
        for i, t in enumerate(self.tempos):
            if i > 0:
                prev = self.tempos[i - 1]
                ms += (t.tick - prev.tick) * prev.us_per_beat / self.ticks_per_beat / 1000.0
            self._ms_at.append(ms)

    @classmethod
    def constant(cls, bpm: float, numerator: int = 4, denominator: int = 4) -> "TempoMap":
        return cls(TICKS_PER_BEAT,
                   [TempoChange(0, round(60_000_000 / bpm))],
                   [TimeSigChange(0, numerator, denominator)])

    def tick_to_ms(self, tick: int) -> float:
        i = max(bisect_right(self._ticks, tick) - 1, 0)
        t = self.tempos[i]
        return self._ms_at[i] + (tick - t.tick) * t.us_per_beat / self.ticks_per_beat / 1000.0

    def ms_to_tick(self, ms: float) -> int:
        i = max(bisect_right(self._ms_at, ms) - 1, 0)
        t = self.tempos[i]
        return int(round(t.tick + (ms - self._ms_at[i]) * 1000.0 * self.ticks_per_beat / t.us_per_beat))

    def initial_bpm(self) -> float:
        return 60_000_000 / self.tempos[0].us_per_beat

    def rescaled(self, ticks_per_beat: int) -> "TempoMap":
        """Novo mapa com outra resolução, preservando os tempos em ms."""
        f = ticks_per_beat / self.ticks_per_beat
        return TempoMap(
            ticks_per_beat,
            [TempoChange(int(round(t.tick * f)), t.us_per_beat) for t in self.tempos],
            [TimeSigChange(int(round(s.tick * f)), s.numerator, s.denominator) for s in self.time_sigs],
        )

    def to_dict(self) -> dict:
        return {
            "ticks_per_beat": self.ticks_per_beat,
            "tempos": [[t.tick, t.us_per_beat] for t in self.tempos],
            "time_sigs": [[s.tick, s.numerator, s.denominator] for s in self.time_sigs],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TempoMap":
        return cls(
            int(d.get("ticks_per_beat", TICKS_PER_BEAT)),
            [TempoChange(int(a), int(b)) for a, b in d.get("tempos", [])],
            [TimeSigChange(int(a), int(b), int(c)) for a, b, c in d.get("time_sigs", [])],
        )
