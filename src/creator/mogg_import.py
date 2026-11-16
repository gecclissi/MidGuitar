"""Áudio de um .mogg importado (pacote Rock Band / PS3), criptografado ou não.

O .mogg é descriptografado (mogg_crypt) para um Ogg Vorbis multicanal num cache
temporário. A partir dele, usando o layout de canais do songs.dta (tracks, pans, vols):
- mix estéreo (song.audio_path) para o editor e o playtest;
- stems estéreo por instrumento com nomes do Clone Hero (drums, bass, guitar,
  vocals, keys, song = acompanhamento, crowd);
- o Ogg multicanal original fica em song.source_mogg para a exportação Rock Band
  reaproveitar os canais sem regravar (PS3 -> PS3 mantém os stems).

O cache (uma pasta só, em %TEMP%/midguitar_cache/mogg) usa nome + tamanho + data de
modificação do .mogg e o layout no nome dos arquivos: trocar o arquivo de origem gera
arquivos novos em vez de reaproveitar um cache velho, e a mesma música importada de
outro lugar (cópia, .pkg de novo) reaproveita o trabalho.
"""
import json
import math
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

import numpy as np

from src.creator.rb_mogg_multitrack import INSTRUMENT_ORDER, AudioLayout

# Nome do stem (padrão Clone Hero) por instrumento do songs.dta
STEM_NAMES = {"drum": "drums", "bass": "bass", "guitar": "guitar", "vocals": "vocals",
              "keys": "keys", "backing": "song", "crowd": "crowd"}

# Canais de bateria -> número do [mix <dif> drumsN] (layouts do Rock Band)
_DRUM_MIX_BY_CHANNELS = {2: 0, 3: 4, 4: 1, 5: 2, 6: 3}


def mogg_cache_dir() -> str:
    """Pasta de cache dos áudios extraídos de .mogg."""
    import tempfile
    path = os.path.join(tempfile.gettempdir(), "midguitar_cache", "mogg")
    os.makedirs(path, exist_ok=True)
    return path


def file_cache_key(path: str) -> str:
    """Chave de cache de um arquivo: tamanho + data de modificação."""
    st = os.stat(path)
    return "%d_%d" % (st.st_size, int(st.st_mtime))


def _ints(value) -> List[int]:
    if isinstance(value, int):
        return [value]
    if isinstance(value, list):
        return [v for v in value if isinstance(v, int)]
    return []


def _floats(value) -> List[float]:
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, list):
        return [float(v) for v in value if isinstance(v, (int, float))]
    return []


def layout_from_dta_song(song_fields: list) -> Dict:
    """Layout de canais do bloco (song ...) de uma entrada do songs.dta."""
    out = {"tracks": {}, "pans": [], "vols": [], "crowd": []}
    for item in song_fields or []:
        if not (isinstance(item, list) and item):
            continue
        key = item[0]
        rest = item[1] if len(item) > 1 else None
        if key == "tracks" and isinstance(rest, list):
            for tr in rest:
                if isinstance(tr, list) and len(tr) > 1 and tr[0] in INSTRUMENT_ORDER:
                    chans = _ints(tr[1])
                    if chans:
                        out["tracks"][tr[0]] = chans
        elif key == "pans":
            out["pans"] = _floats(rest)
        elif key == "vols":
            out["vols"] = _floats(rest)
        elif key == "crowd_channels":
            out["crowd"] = _ints(item[1:] if len(item) > 2 else rest)
    return out


def _groups(channels: int, layout: Optional[Dict]) -> Dict[str, List[int]]:
    """Canais por grupo (instrumentos, backing, crowd), só os que existem no áudio."""
    if not layout or not layout.get("tracks"):
        return {}
    used = set()
    groups = {}
    for inst in INSTRUMENT_ORDER:
        chans = [c for c in layout["tracks"].get(inst, []) if 0 <= c < channels and c not in used]
        if chans:
            groups[inst] = chans
            used.update(chans)
    crowd = [c for c in layout.get("crowd", []) if 0 <= c < channels and c not in used]
    used.update(crowd)
    backing = [c for c in range(channels) if c not in used]
    if backing:
        groups["backing"] = backing
    if crowd:
        groups["crowd"] = crowd
    return groups


def _pan_vol(channels: int, layout: Optional[Dict]):
    pans = list((layout or {}).get("pans") or [])
    vols = list((layout or {}).get("vols") or [])
    if len(pans) != channels:
        # Sem layout: canais em pares estéreo (L, R); canal sobrando no centro
        pans = [-1.0 if c % 2 == 0 else 1.0 for c in range(channels)]
        if channels % 2 == 1:
            pans[-1] = 0.0
    if len(vols) != channels:
        vols = [0.0] * channels
    return pans, vols


def _render_stereo(data: np.ndarray, chans: List[int], pans, vols) -> np.ndarray:
    """Soma os canais num par estéreo com pan de potência constante e volume em dB."""
    out = np.zeros((data.shape[0], 2), dtype=np.float32)
    for c in chans:
        gain = 10.0 ** (vols[c] / 20.0)
        angle = (max(-1.0, min(1.0, pans[c])) + 1.0) * math.pi / 4.0
        out[:, 0] += data[:, c] * np.float32(gain * math.cos(angle))
        out[:, 1] += data[:, c] * np.float32(gain * math.sin(angle))
    return out


def audio_layout_from_source(source: Dict, charted: Dict[str, bool]) -> AudioLayout:
    """AudioLayout (songs.dta da exportação) com os canais originais do .mogg importado."""
    channels = int(source["channels"])
    pans, vols = _pan_vol(channels, source)
    tracks = {}
    for inst in INSTRUMENT_ORDER:
        chans = [c for c in source.get("tracks", {}).get(inst, []) if 0 <= c < channels]
        if chans and charted.get(inst):
            tracks[inst] = chans
    used = {c for chans in tracks.values() for c in chans}
    # Canais de instrumento sem notas, acompanhamento e plateia tocam sempre
    backing = [c for c in range(channels) if c not in used]
    drum_mix = _DRUM_MIX_BY_CHANNELS.get(len(tracks.get("drum", [])), 0)
    return AudioLayout(channels=channels, tracks=tracks, backing=backing,
                       pans=pans, vols=vols, drum_mix=drum_mix, multitrack=True)


def prepare_mogg_audio(mogg_path: str, cache_dir: str, layout: Optional[Dict] = None) -> Dict:
    """Descriptografa `mogg_path` e grava ogg multicanal, mix estéreo e stems em `cache_dir`.

    Devolve {"ogg", "mix", "stems", "channels", "tracks", "pans", "vols", "crowd"}.
    Levanta mogg_crypt.MoggCryptError se a versão não for suportada."""
    import soundfile as sf
    from src.creator.mogg_crypt import decrypt_mogg
    from src.creator.mogg_generator import write_vorbis

    import hashlib
    layout_key = hashlib.md5(json.dumps(layout or {}, sort_keys=True).encode("utf-8")).hexdigest()[:8]
    base = "%s_%s_%s" % (os.path.splitext(os.path.basename(mogg_path))[0],
                         file_cache_key(mogg_path), layout_key)
    manifest_path = os.path.join(cache_dir, base + ".json")
    if os.path.isfile(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if all(os.path.isfile(p) for p in [cached["ogg"], cached["mix"]] + cached["stems"]):
                return cached
        except (OSError, ValueError, KeyError):
            pass

    os.makedirs(cache_dir, exist_ok=True)
    ogg_path = os.path.join(cache_dir, base + ".ogg")
    tmp = ogg_path + ".tmp"
    decrypt_mogg(mogg_path, ogg_out_path=tmp)
    os.replace(tmp, ogg_path)

    data, rate = sf.read(ogg_path, dtype="float32", always_2d=True)
    channels = data.shape[1]
    pans, vols = _pan_vol(channels, layout)
    groups = _groups(channels, layout)

    jobs = {}   # caminho -> áudio estéreo
    mix_groups = [g for g in groups if g != "crowd"] or None
    if mix_groups:
        mix = sum(_render_stereo(data, groups[g], pans, vols) for g in mix_groups)
    else:
        mix = _render_stereo(data, list(range(channels)), pans, vols)
    peak = float(np.max(np.abs(mix))) if len(mix) else 0.0
    scale = np.float32(0.98 / peak) if peak > 0.98 else np.float32(1.0)
    mix_path = os.path.join(cache_dir, base + "_mix.ogg")
    jobs[mix_path] = mix * scale

    stems = []
    if groups:
        stem_dir = os.path.join(cache_dir, base + "_stems")
        os.makedirs(stem_dir, exist_ok=True)
        for g, chans in groups.items():
            audio = _render_stereo(data, chans, pans, vols) * scale
            if g != "backing" and float(np.max(np.abs(audio))) < 1e-4:
                continue   # canal mudo (ex.: teclado vazio): não vira stem
            path = os.path.join(stem_dir, STEM_NAMES[g] + ".ogg")
            jobs[path] = audio
            stems.append(path)
        if "backing" not in groups:
            # Sem acompanhamento: song.ogg mudo, para o Clone Hero não somar o mix aos stems
            path = os.path.join(stem_dir, "song.ogg")
            jobs[path] = np.zeros((len(data), 2), dtype=np.float32)
            stems.append(path)
    del data

    def encode(item):
        path, audio = item
        part = path + ".tmp.ogg"
        write_vorbis(part, audio, rate)
        os.replace(part, path)

    with ThreadPoolExecutor(max_workers=min(4, len(jobs))) as pool:
        list(pool.map(encode, jobs.items()))

    result = {"ogg": ogg_path, "mix": mix_path, "stems": stems, "channels": channels,
              "tracks": {k: v for k, v in (layout or {}).get("tracks", {}).items()},
              "pans": pans, "vols": vols, "crowd": list((layout or {}).get("crowd", []))}
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(result, f)
    return result
