"""Áudio do Rock Band (RB3/PS3/Xbox/PS4): um único .mogg multicanal a partir dos stems.

Os canais seguem a ordem que o Magma C3 usa nas referências reais
(bateria, baixo, guitarra, vocais, teclado, acompanhamento) e o layout devolvido
alimenta o songs.dta (`tracks`, `tracks_count`, `pans`, `vols`, `cores`), de modo
que o DTA declara exatamente os canais que existem no .mogg.

Regras:
- todo stem vira estéreo (mono é duplicado) e é reamostrado para 44100 Hz;
- stems do mesmo instrumento são somados (drums_1..4 -> um par estéreo, mix drums0);
- stem de instrumento sem notas no chart, "song", "rhythm" e nomes desconhecidos vão
  para o acompanhamento (backing), que nunca é silenciado no jogo; "crowd" é ignorado;
- sem stems (ou um só): mix estéreo de 2 canais, como antes.
"""
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from src.creator.audio_resample import RB_SAMPLE_RATE, read_audio

# Ordem dos canais e do tracks_count (Magma C3): bateria, baixo, guitarra, vocais, teclado + backing
INSTRUMENT_ORDER = ("drum", "bass", "guitar", "vocals", "keys")
BACKING = "backing"

_STEM_KIND = {
    "drums": "drum", "drum": "drum", "drums_1": "drum", "drums_2": "drum",
    "drums_3": "drum", "drums_4": "drum", "kick": "drum", "snare": "drum", "kit": "drum",
    "bass": "bass", "guitar": "guitar",
    "vocals": "vocals", "vocal": "vocals", "vocals_1": "vocals", "vocals_2": "vocals",
    "keys": "keys",
    "crowd": "crowd",
}


def classify_stem(path: str) -> str:
    """Instrumento do stem pelo nome do arquivo (padrão Clone Hero); resto é backing."""
    base = os.path.splitext(os.path.basename(path))[0].strip().lower()
    return _STEM_KIND.get(base, BACKING)


def _has_harmonies(song) -> bool:
    for t in getattr(song, "passthrough_tracks", None) or []:
        if (t.get("name") or "").strip().upper().startswith("HARM") and any(
                e[1].get("type") == "note_on" for e in t.get("events", [])):
            return True
    return False


def charted_instruments(song) -> Dict[str, bool]:
    """Quais instrumentos do Rock Band têm notas (5 lanes ou Pro)."""
    return {
        "drum": bool(song.drum_notes),
        "bass": bool(song.bass_notes or getattr(song, "pro_bass_notes", None)),
        "guitar": bool(song.guitar_notes or getattr(song, "pro_guitar_notes", None)),
        "vocals": bool(song.vocal_notes) or _has_harmonies(song),
        "keys": bool(song.keys_notes or getattr(song, "pro_keys_notes", None)),
    }


@dataclass
class AudioLayout:
    """Canais do .mogg e como o songs.dta os declara."""
    channels: int = 2
    tracks: Dict[str, List[int]] = field(default_factory=dict)   # instrumento -> canais
    backing: List[int] = field(default_factory=list)
    pans: List[float] = field(default_factory=list)
    vols: List[float] = field(default_factory=list)
    drum_mix: int = 0
    multitrack: bool = False

    @property
    def cores(self) -> List[int]:
        return [-1] * self.channels

    @property
    def tracks_count(self) -> List[int]:
        if not self.multitrack:
            return []
        return [len(self.tracks.get(i, [])) for i in INSTRUMENT_ORDER] + [len(self.backing)]


def single_mix_layout(charted: Optional[Dict[str, bool]] = None) -> AudioLayout:
    """Mix estéreo único: os instrumentos com notas apontam para os 2 canais (como antes)."""
    charted = charted if charted is not None else {i: True for i in INSTRUMENT_ORDER}
    order = ("guitar", "bass", "drum", "keys", "vocals")
    tracks = {i: [0, 1] for i in order if charted.get(i)}
    return AudioLayout(channels=2, tracks=tracks, backing=[] if tracks else [0, 1],
                       pans=[-1.0, 1.0], vols=[-1.5, -1.5])


def plan_groups(stems: List[str], charted: Dict[str, bool]) -> Dict[str, List[str]]:
    """Agrupa os stems por destino (instrumento ou backing), na ordem dos canais."""
    groups: Dict[str, List[str]] = {}
    for p in stems:
        kind = classify_stem(p)
        if kind == "crowd":
            continue
        if kind != BACKING and not charted.get(kind):
            kind = BACKING
        groups.setdefault(kind, []).append(p)
    order = list(INSTRUMENT_ORDER) + [BACKING]
    return {k: groups[k] for k in order if k in groups}


def layout_for_groups(groups: Dict[str, List[str]]) -> AudioLayout:
    lay = AudioLayout(multitrack=True)
    ch = 0
    for kind in groups:
        pair = [ch, ch + 1]
        if kind == BACKING:
            lay.backing = pair
        else:
            lay.tracks[kind] = pair
        ch += 2
    lay.channels = ch
    lay.pans = [-1.0, 1.0] * (ch // 2)
    lay.vols = [0.0] * ch
    return lay


def _existing(paths) -> List[str]:
    out = []
    for p in paths or []:
        if p and os.path.isfile(p) and os.path.abspath(p) not in [os.path.abspath(q) for q in out]:
            out.append(p)
    return out


def _mixdown(paths: List[str], dest_ogg: str) -> bool:
    from src.creator.mogg_generator import write_vorbis
    total = None
    for p in paths:
        data = read_audio(p, RB_SAMPLE_RATE, channels=2)
        if total is None:
            total = data
        else:
            if len(data) > len(total):
                data, total = total, data
            total[:len(data)] += data
    if total is None:
        return False
    write_vorbis(dest_ogg, total, RB_SAMPLE_RATE)
    return True


def _write_multitrack_ogg(groups: Dict[str, List[str]], dest_ogg: str, work_dir: str) -> int:
    """Grava o Ogg Vorbis multicanal (2 canais por grupo). Devolve o número de canais."""
    from src.creator.mogg_generator import write_vorbis
    channels = 2 * len(groups)
    decoded = []
    for gi, (_kind, paths) in enumerate(groups.items()):
        for p in paths:
            data = read_audio(p, RB_SAMPLE_RATE, channels=2)
            raw = os.path.join(work_dir, "stem_%d.f32" % len(decoded))
            data.astype(np.float32).tofile(raw)
            decoded.append((gi, raw, len(data)))
            del data
    frames = max(n for _g, _r, n in decoded)
    # Soma dos grupos num arquivo mapeado em disco (não cabe tudo na RAM em músicas longas)
    mix_path = os.path.join(work_dir, "mix.f32")
    mix = np.memmap(mix_path, dtype=np.float32, mode="w+", shape=(frames, channels))
    for gi, raw, n in decoded:
        data = np.fromfile(raw, dtype=np.float32).reshape(n, 2)
        mix[:n, 2 * gi:2 * gi + 2] += data
        del data
        os.remove(raw)
    mix.flush()
    write_vorbis(dest_ogg, mix, RB_SAMPLE_RATE)
    del mix
    return channels


def build_rb_mogg(song, dest_mogg: str, audio_source_path: str = None, multitrack: bool = True,
                  charted: Optional[Dict[str, bool]] = None) -> Optional[AudioLayout]:
    """Gera `dest_mogg` (0x0A, Vorbis 44100 Hz) e devolve o layout de canais.

    Com 2+ stems e multitrack=True: .mogg multicanal; senão, mix estéreo (os stems
    são somados quando não há mix). None se não houver áudio."""
    from src.creator.mogg_generator import create_unencrypted_mogg
    charted = charted if charted is not None else charted_instruments(song)
    stems = _existing(getattr(song, "audio_stems", None))
    mix = audio_source_path or getattr(song, "audio_path", None)
    mix = mix if mix and os.path.isfile(mix) else None
    mix_in_stems = mix is not None and os.path.abspath(mix) in [os.path.abspath(p) for p in stems]
    work = tempfile.mkdtemp(prefix="midguitar_mogg_")
    try:
        from src.creator.mogg_generator import convert_audio_to_ogg, is_mogg_file
        ogg = os.path.join(work, "audio.ogg")
        if len(stems) > 1 and multitrack:
            # Mix completo separado dos stems (ex.: song.ogg do Clone Hero) = acompanhamento
            sources = stems + ([mix] if mix is not None and not mix_in_stems and not is_mogg_file(mix) else [])
            groups = plan_groups(sources, charted)
            if not groups:
                return None
            _write_multitrack_ogg(groups, ogg, work)
            layout = layout_for_groups(groups)
        else:
            layout = single_mix_layout(charted)
            if mix is not None and not mix_in_stems:
                if is_mogg_file(mix):
                    return layout if create_unencrypted_mogg(mix, dest_mogg) else None
                if not convert_audio_to_ogg(mix, ogg, target_rate=RB_SAMPLE_RATE):
                    return None
            elif stems:
                if not _mixdown(stems, ogg):
                    return None
            else:
                return None
        if not create_unencrypted_mogg(ogg, dest_mogg):
            return None
        return layout
    except Exception as e:
        print("[RBMogg] Erro ao gerar .mogg: %s" % e)
        return None
    finally:
        shutil.rmtree(work, ignore_errors=True)
