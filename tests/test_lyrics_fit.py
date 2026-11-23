"""Letra em texto simples (sem tempos) sempre cabe dentro da duração do áudio.

Bug visto no RB3 (RPCS3): "Salut les amoureux (Auto)" tinha 4:05 de áudio, mas a letra, com uma
sílaba por batida a 80 BPM, ia até 7:01 e o jogo mostrava a música com 7:04.
"""
from src.creator.chart_model import ChartSong
from src.creator.lyric_processor import align_lyrics_to_song
from src.creator.tempo_map import TempoChange, TempoMap, TimeSigChange

LONG_LYRICS = "\n".join("la le li lo lu la le li" for _ in range(40))  # 320 sílabas


def _last_end(song):
    return max(v.time_ms + v.duration_ms for v in song.vocal_notes)


def test_letra_longa_cabe_no_fim_informado():
    s = ChartSong(bpm=80.0)
    n = align_lyrics_to_song(s, LONG_LYRICS, start_delay_ms=3000, end_ms=100000)
    assert n == 320
    assert _last_end(s) <= 100000
    assert s.vocal_notes[0].time_ms == 3000
    times = [v.time_ms for v in s.vocal_notes]
    assert times == sorted(times) and len(set(times)) == len(times)


def test_letra_longa_cabe_com_mapa_de_tempo():
    s = ChartSong(bpm=120.0)
    s.tempo_map = TempoMap(480, [TempoChange(0, 500000), TempoChange(3840, 750000)],
                           [TimeSigChange(0, 4, 4)])
    align_lyrics_to_song(s, LONG_LYRICS, start_delay_ms=3000, end_ms=90000)
    assert len(s.vocal_notes) == 320 and _last_end(s) <= 90000


def test_sem_audio_usa_duracao_da_musica_quando_tem_audio():
    s = ChartSong(bpm=80.0, duration_ms=120000)
    s.audio_path = "musica.mp3"
    align_lyrics_to_song(s, LONG_LYRICS, start_delay_ms=3000)
    assert _last_end(s) <= 120000


def test_letra_curta_mantem_uma_silaba_por_batida():
    s = ChartSong(bpm=120.0)
    align_lyrics_to_song(s, "um dois tres\n", start_delay_ms=4000, end_ms=200000)
    assert [v.time_ms for v in s.vocal_notes] == [4000, 4500, 5000]
