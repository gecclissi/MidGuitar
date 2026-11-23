"""Detecção de BPM sem cair na metade/dobro do andamento.

Bug visto no RB3 (RPCS3): "Salut les amoureux" (~161 BPM, acento forte a cada 2 tempos) era
detectada como 80 BPM, e o chart automático saía no dobro da duração das batidas.
"""
import numpy as np
import pytest
import soundfile as sf

from src.creator.mogg_generator import analyze_audio_file

SR = 44100


def _hit(x, i, amp, freq, sr=SR, length=3000):
    t = np.arange(min(length, len(x) - i)) / sr
    x[i:i + len(t)] += (amp * np.sin(2 * np.pi * freq * t) * np.exp(-t * 40)).astype("float32")


def _accented_beat(path, bpm, seconds=40):
    """Bumbo forte nos tempos 1 e 3, caixa fraca nos tempos 2 e 4 (padrão de rock/pop)."""
    x = np.zeros(SR * seconds, dtype="float32")
    for k in range(int(seconds * bpm / 60)):
        i = int(k * 60 / bpm * SR)
        if k % 2 == 0:
            _hit(x, i, 1.0, 60)
        else:
            _hit(x, i, 0.3, 1800)
    sf.write(path, x, SR)
    return path


@pytest.mark.parametrize("bpm", [100, 140, 160, 170])
def test_acento_a_cada_dois_tempos_nao_vira_metade(tmp_path, bpm):
    p = _accented_beat(str(tmp_path / "beat.wav"), bpm)
    assert abs(analyze_audio_file(p)["bpm"] - bpm) <= 1


def test_andamento_lento_e_dobrado_para_faixa_dos_charts(tmp_path):
    p = _accented_beat(str(tmp_path / "beat.wav"), 70)
    assert abs(analyze_audio_file(p)["bpm"] - 140) <= 1
