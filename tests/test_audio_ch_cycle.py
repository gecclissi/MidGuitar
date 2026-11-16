"""Passo 2B: áudio (Opus/Vorbis, BPM), stems do Clone Hero e ranking 0-6."""
import glob
import os

import numpy as np
import pytest
import soundfile as sf

from src.creator.chart_model import ChartSong, NoteEvent
from tests.acceptance.conftest import JOE, copy_ref, need  # noqa: F401 (fixture)


def _codec(path):
    with open(path, "rb") as f:
        head = f.read(256)
    if b"OpusHead" in head:
        return "opus"
    if b"\x01vorbis" in head:
        return "vorbis"
    return "?"


def _click_wav(path, bpm, seconds=30, sr=44100):
    x = np.zeros(sr * seconds, dtype="float32")
    for k in range(int(seconds * bpm / 60)):
        i = int(k * 60 / bpm * sr)
        x[i:i + 2000] += np.hanning(2000).astype("float32")
    sf.write(path, x, sr)
    return path


# ---------------------------------------------------------------- Opus -> Vorbis
@need(JOE)
def test_convert_opus_to_vorbis(copy_ref, tmp_path):
    from src.creator.mogg_generator import convert_audio_to_ogg
    opus = copy_ref(os.path.join(JOE, "bass.opus"))
    out = str(tmp_path / "bass.ogg")
    assert convert_audio_to_ogg(opus, out)
    assert _codec(out) == "vorbis"
    assert sf.info(out).duration > 200


def test_vorbis_ogg_is_still_copied(tmp_path):
    from src.creator.mogg_generator import convert_audio_to_ogg
    src = str(tmp_path / "a.ogg")
    sf.write(src, np.zeros(44100, dtype="float32"), 44100, format="OGG", subtype="VORBIS")
    out = str(tmp_path / "b.ogg")
    assert convert_audio_to_ogg(src, out)
    assert open(src, "rb").read() == open(out, "rb").read()


@need(JOE)
def test_analyze_opus(copy_ref):
    from src.creator.mogg_generator import analyze_audio_file
    r = analyze_audio_file(copy_ref(os.path.join(JOE, "bass.opus")))
    assert 240000 < r["duration_ms"] < 250000


# ---------------------------------------------------------------- BPM
@pytest.mark.parametrize("bpm", [90, 128, 150])
def test_bpm_click_tracks(tmp_path, bpm):
    from src.creator.mogg_generator import analyze_audio_file
    p = _click_wav(str(tmp_path / "click.wav"), bpm)
    assert abs(analyze_audio_file(p)["bpm"] - bpm) <= 1


# ---------------------------------------------------------------- ranking
def _song_with_density(notes_per_sec, seconds=120):
    n = int(notes_per_sec * seconds)
    notes = [NoteEvent(time_ms=int(i * 1000 / notes_per_sec), lane="green") for i in range(n)]
    return ChartSong(guitar_notes=notes, duration_ms=seconds * 1000)


def test_ranking_sparse_low_dense_high():
    from src.creator.difficulty import calculate_rankings
    sparse, dense = _song_with_density(0.4), _song_with_density(8)
    calculate_rankings(sparse)
    calculate_rankings(dense)
    assert sparse.diff_guitar <= 1
    assert dense.diff_guitar >= 5
    assert sparse.diff_bass == 0 and sparse.diff_vocals == 0


def test_ranking_ignores_lower_difficulties():
    from src.creator.difficulty import calculate_rankings
    song = _song_with_density(1.0)
    extra = [NoteEvent(time_ms=n.time_ms + 1, lane="red", difficulty=d)
             for n in song.guitar_notes for d in ("Easy", "Medium", "Hard")]
    song.guitar_notes += extra
    calculate_rankings(song)
    base = song.diff_guitar
    assert base <= 3


def test_auto_charter_ranking_not_constant():
    from src.creator.difficulty import calculate_rankings
    tiers = set()
    for d in (0.3, 2, 6, 12):
        s = _song_with_density(d)
        calculate_rankings(s)
        tiers.add(s.diff_guitar)
    assert len(tiers) >= 3


# ---------------------------------------------------------------- Clone Hero stems
def _silence(path, fmt="OGG", subtype="VORBIS"):
    sf.write(path, np.zeros(4410, dtype="float32"), 44100, format=fmt, subtype=subtype)


def test_ch_with_stems_has_no_song_ogg(tmp_path):
    from src.creator.clonehero_exporter import export_clone_hero_song
    src = tmp_path / "src"
    src.mkdir()
    stems = []
    for name in ("guitar", "bass", "Drums Kit", "vocals"):
        p = str(src / (name + ".ogg"))
        _silence(p)
        stems.append(p)
    song = ChartSong(audio_path=stems[0], audio_stems=stems)
    folder = export_clone_hero_song(song, str(tmp_path / "out"))
    files = set(os.listdir(folder))
    assert "song.ogg" not in files
    assert {"guitar.ogg", "bass.ogg", "drums.ogg", "vocals.ogg"} <= files
    assert "Drums Kit.ogg" not in files


def test_ch_without_stems_keeps_song_ogg(tmp_path):
    from src.creator.clonehero_exporter import export_clone_hero_song
    p = str(tmp_path / "mix.wav")
    sf.write(p, np.zeros(4410, dtype="float32"), 44100)
    folder = export_clone_hero_song(ChartSong(audio_path=p), str(tmp_path / "out"))
    assert os.path.exists(os.path.join(folder, "song.ogg"))


def test_ch_keeps_separate_full_mix_as_song(tmp_path):
    from src.creator.clonehero_exporter import export_clone_hero_song
    g = str(tmp_path / "guitar.ogg")
    mix = str(tmp_path / "mix.ogg")
    _silence(g)
    _silence(mix)
    song = ChartSong(audio_path=mix, audio_stems=[g])
    folder = export_clone_hero_song(song, str(tmp_path / "out"))
    assert os.path.exists(os.path.join(folder, "song.ogg"))
    assert os.path.exists(os.path.join(folder, "guitar.ogg"))


@need(JOE)
def test_ch_joe_roundtrip_opus_stems_kept(copy_ref, tmp_path):
    from src.creator.chart_importer import import_song_from_folder
    from src.creator.clonehero_exporter import export_clone_hero_song
    folder = copy_ref(JOE)
    song = import_song_from_folder(folder)
    # o importador não pode gravar arquivos ao lado da pasta de origem
    assert not glob.glob(os.path.join(folder, "*_extracted.ogg"))
    out = export_clone_hero_song(song, str(tmp_path / "out"))
    files = set(os.listdir(out))
    assert "song.ogg" not in files
    assert {"guitar.opus", "bass.opus", "drums_1.opus", "keys.opus", "vocals.opus"} <= files


def test_importer_mogg_extraction_not_in_source_folder(tmp_path):
    from src.creator.chart_importer import import_song_from_folder
    from src.creator.mogg_generator import create_unencrypted_mogg
    folder = tmp_path / "song"
    folder.mkdir()
    _silence(str(folder / "a.ogg"))
    assert create_unencrypted_mogg(str(folder / "a.ogg"), str(folder / "song.mogg"))
    os.remove(str(folder / "a.ogg"))
    import_song_from_folder(str(folder))
    assert not glob.glob(str(folder / "*_extracted.ogg"))
