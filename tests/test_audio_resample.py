"""Reamostragem limitada em banda (48000 -> 44100 para o .mogg do RB3)."""
import numpy as np
import pytest

from src.creator.audio_resample import read_audio, resample, resampled_length


def _sine(freq, rate, seconds=1.0, amp=0.5):
    t = np.arange(int(rate * seconds)) / float(rate)
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _peak(y, rate):
    w = np.hanning(len(y))
    spec = np.abs(np.fft.rfft(y * w))
    freqs = np.fft.rfftfreq(len(y), 1.0 / rate)
    return freqs[spec.argmax()], spec


@pytest.mark.parametrize("src,dst", [(48000, 44100), (22050, 44100), (32000, 44100), (44100, 48000)])
def test_sine_frequency_and_amplitude_preserved(src, dst):
    x = _sine(1000.0, src, 2.0)
    y = resample(x, src, dst)
    assert len(y) == resampled_length(len(x), src, dst)
    f, _ = _peak(y, dst)
    assert abs(f - 1000.0) < 1.0
    mid = y[len(y) // 4: 3 * len(y) // 4]
    assert abs(np.abs(mid).max() - 0.5) < 0.01
    # Comparação direta com o seno ideal na nova taxa
    ideal = _sine(1000.0, dst, 2.0)[:len(y)]
    assert np.abs(mid - ideal[len(y) // 4: 3 * len(y) // 4]).max() < 0.01


def test_no_aliasing_from_content_above_new_nyquist():
    # 23 kHz existe em 48 kHz mas não cabe em 44,1 kHz: tem de sumir, não dobrar para 21,1 kHz
    x = _sine(23000.0, 48000, 2.0)
    y = resample(x, 48000, 44100)
    mid = y[len(y) // 4: 3 * len(y) // 4]
    assert np.sqrt(np.mean(mid ** 2)) < 0.5 * 1e-3  # < -60 dB


def test_passband_tone_near_top_kept():
    x = _sine(18000.0, 48000, 1.0)
    y = resample(x, 48000, 44100)
    f, _ = _peak(y, 44100)
    assert abs(f - 18000.0) < 2.0
    mid = y[len(y) // 4: 3 * len(y) // 4]
    assert np.abs(mid).max() > 0.45


def test_multichannel_and_identity():
    x = np.stack([_sine(440, 48000), _sine(880, 48000)], 1)
    y = resample(x, 48000, 44100)
    assert y.shape == (44100, 2)
    assert abs(_peak(y[:, 1], 44100)[0] - 880) < 2
    assert resample(x, 44100, 44100).shape == x.shape


def test_read_audio_resamples_file(tmp_path):
    import soundfile as sf
    p = tmp_path / "a.wav"
    sf.write(str(p), _sine(500, 48000, 1.0), 48000)
    y = read_audio(str(p), 44100, channels=2)
    assert y.shape == (44100, 2)
    assert abs(_peak(y[:, 0], 44100)[0] - 500) < 2


def test_mogg_is_always_44100(tmp_path):
    import soundfile as sf
    from src.creator.mogg_generator import create_unencrypted_mogg, extract_ogg_from_mogg
    src = tmp_path / "a.wav"
    sf.write(str(src), _sine(500, 48000, 1.0), 48000)
    mogg = tmp_path / "a.mogg"
    assert create_unencrypted_mogg(str(src), str(mogg))
    ogg = extract_ogg_from_mogg(str(mogg), str(tmp_path / "out.ogg"))
    info = sf.info(ogg)
    assert info.samplerate == 44100 and info.channels == 2
    assert abs(info.frames - 44100) < 2048


def test_mogg_keeps_multichannel_vorbis_44100(tmp_path):
    import soundfile as sf
    from src.creator.mogg_generator import create_unencrypted_mogg, extract_ogg_from_mogg
    src = tmp_path / "multi.ogg"
    data = np.stack([_sine(300 + 100 * c, 44100, 0.5) for c in range(6)], 1)
    sf.write(str(src), data, 44100, format="OGG", subtype="VORBIS")
    mogg = tmp_path / "m.mogg"
    assert create_unencrypted_mogg(str(src), str(mogg))
    info = sf.info(extract_ogg_from_mogg(str(mogg), str(tmp_path / "o.ogg")))
    assert info.channels == 6 and info.samplerate == 44100
