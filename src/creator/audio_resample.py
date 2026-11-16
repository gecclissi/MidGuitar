"""Reamostragem de áudio limitada em banda (só numpy; o scipy não está disponível).

O Rock Band 3 espera 44100 Hz no .mogg. Stems Opus vêm em 48000 Hz, então todo
áudio que vai para um .mogg passa por aqui. Método: reamostragem por FFT
(interpolação sinc ideal), com zeros de guarda contra o efeito circular e uma
rampa cosseno no topo da banda para reduzir o "ringing" do corte.
"""
from math import gcd

import numpy as np

RB_SAMPLE_RATE = 44100
# Zeros de guarda no fim do sinal: o núcleo sinc decai como 1/x, então o fim
# "vazando" para o começo (FFT é circular) fica bem abaixo do ruído do Vorbis.
_GUARD = 16384
# Fração do topo da nova banda atenuada por rampa cosseno (só ao reduzir a taxa)
_TAPER = 0.025


def _is_smooth(n: int) -> bool:
    for p in (2, 3, 5):
        while n % p == 0:
            n //= p
    return n == 1


def _next_smooth(n: int) -> int:
    n = max(1, n)
    while not _is_smooth(n):
        n += 1
    return n


def resampled_length(n: int, src_rate: int, dst_rate: int) -> int:
    return int(round(n * float(dst_rate) / float(src_rate)))


def _resample_1d(x: np.ndarray, up: int, down: int, k: int, out_len: int, taper: np.ndarray) -> np.ndarray:
    n_in = k * down
    n_out = k * up
    spec = np.fft.rfft(x.astype(np.float64), n=n_in)
    out_bins = n_out // 2 + 1
    new = np.zeros(out_bins, np.complex128)
    m = min(out_bins, len(spec))
    new[:m] = spec[:m]
    if taper is not None:
        new[out_bins - len(taper):] *= taper
    if n_out < n_in and n_out % 2 == 0:
        # Bin de Nyquist do sinal reduzido: só a parte real é representável
        new[-1] = new[-1].real
    y = np.fft.irfft(new, n=n_out) * (float(n_out) / float(n_in))
    return y[:out_len].astype(np.float32)


def resample(x: np.ndarray, src_rate: int, dst_rate: int = RB_SAMPLE_RATE) -> np.ndarray:
    """Reamostra `x` ((n,) ou (n, canais)) de src_rate para dst_rate. Devolve float32."""
    x = np.asarray(x)
    src_rate, dst_rate = int(src_rate), int(dst_rate)
    if src_rate <= 0 or dst_rate <= 0:
        raise ValueError("taxa de amostragem inválida")
    if src_rate == dst_rate or len(x) == 0:
        return x.astype(np.float32)
    g = gcd(src_rate, dst_rate)
    up, down = dst_rate // g, src_rate // g
    n = len(x)
    out_len = resampled_length(n, src_rate, dst_rate)
    k = _next_smooth(-(-(n + _GUARD) // down))
    out_bins = (k * up) // 2 + 1
    taper = None
    if dst_rate < src_rate:
        width = max(2, int(out_bins * _TAPER))
        taper = 0.5 * (1.0 + np.cos(np.linspace(0.0, np.pi, width)))
    if x.ndim == 1:
        return _resample_1d(x, up, down, k, out_len, taper)
    out = np.empty((out_len, x.shape[1]), np.float32)
    for c in range(x.shape[1]):
        out[:, c] = _resample_1d(x[:, c], up, down, k, out_len, taper)
    return out


def read_audio(path: str, target_rate: int = RB_SAMPLE_RATE, channels: int = None) -> np.ndarray:
    """Lê um arquivo de áudio (wav/ogg/opus/mp3/flac) como float32 (frames, canais) em target_rate.

    channels=2 força estéreo (mono duplicado; mais de 2 canais: os 2 primeiros)."""
    import soundfile as sf
    data, rate = sf.read(path, dtype="float32", always_2d=True)
    if channels == 2:
        if data.shape[1] == 1:
            data = np.repeat(data, 2, axis=1)
        elif data.shape[1] > 2:
            data = data[:, :2]
    if rate != target_rate:
        data = resample(data, rate, target_rate)
    return data
