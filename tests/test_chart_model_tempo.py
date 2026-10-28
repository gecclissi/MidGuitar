import pytest

from src.creator.chart_model import ChartSong
from src.creator.tempo_map import TempoChange, TempoMap


def test_default_song_uses_constant_map_from_bpm():
    s = ChartSong(bpm=150.0)
    assert s.get_tempo_map().initial_bpm() == pytest.approx(150.0)
    assert len(s.get_tempo_map().tempos) == 1


def test_imported_map_is_used_while_bpm_matches():
    tm = TempoMap(480, [TempoChange(0, 500000), TempoChange(960, 1000000)])
    s = ChartSong(bpm=120.0, tempo_map=tm)
    assert s.get_tempo_map() is tm


def test_changing_bpm_discards_imported_map():
    tm = TempoMap(480, [TempoChange(0, 500000), TempoChange(960, 1000000)])
    s = ChartSong(bpm=120.0, tempo_map=tm)
    s.bpm = 140.0
    assert len(s.get_tempo_map().tempos) == 1
    assert s.get_tempo_map().initial_bpm() == pytest.approx(140.0, abs=0.01)


def test_to_dict_from_dict_keeps_tempo_map():
    tm = TempoMap(480, [TempoChange(0, 500000), TempoChange(960, 1000000)])
    s2 = ChartSong.from_dict(ChartSong(bpm=120.0, tempo_map=tm).to_dict())
    assert s2.tempo_map is not None and s2.tempo_map.tempos == tm.tempos


def test_old_project_dict_without_tempo_map_loads():
    d = ChartSong(bpm=133.0).to_dict()
    d.pop("tempo_map", None)
    s = ChartSong.from_dict(d)
    assert s.tempo_map is None and s.get_tempo_map().initial_bpm() == pytest.approx(133.0)
