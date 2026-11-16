"""song.ini: importação e exportação preservam as chaves que o MidGuitar não usa."""
import configparser
import json
import os

from src.creator.chart_importer import import_song_from_folder
from src.creator.chart_model import ChartSong, NoteEvent
from src.creator.clonehero_exporter import export_clone_hero_song

INI = """[song]
name = Musica INI
artist = Banda INI
album = Disco
year = 1972
genre = Country
charter = The Guy
icon = customs
loading_phrase = Frase original
delay = 0
pro_drums = True
diff_guitar = 4
diff_drums = 3
diff_drums_real = 3
diff_guitar_real = 5
diff_bass_real = 1
diff_keys_real = 2
diff_vocals = 1
diff_vocals_harm = 2
preview_start_time = 72497
preview_end_time = 102497
song_length = 241658
"""


def _folder(tmp_path):
    folder = tmp_path / "ini_song"
    folder.mkdir()
    (folder / "song.ini").write_text(INI, encoding="utf-8")
    return str(folder)


def _read_ini(folder):
    cp = configparser.ConfigParser(interpolation=None)
    cp.read(os.path.join(folder, "song.ini"), encoding="utf-8")
    return dict(cp.items("song"))


def test_ini_import_reads_managed_keys(tmp_path):
    s = import_song_from_folder(_folder(tmp_path))
    assert s.preview_start_ms == 72497
    assert (s.diff_pro_guitar, s.diff_pro_bass, s.diff_pro_keys, s.diff_vocals) == (5, 1, 2, 1)
    assert s.ini_extra["pro_drums"] == "True"
    assert s.ini_extra["preview_end_time"] == "102497"
    assert "name" not in s.ini_extra and "diff_guitar" not in s.ini_extra


def test_ini_export_keeps_unknown_keys(tmp_path):
    s = import_song_from_folder(_folder(tmp_path))
    s.add_note("guitar", NoteEvent(time_ms=1000, lane="green"))
    s.title = "Novo Titulo"
    out = export_clone_hero_song(s, str(tmp_path / "out"))
    ini = _read_ini(out)
    assert ini["name"] == "Novo Titulo"                 # valor do MidGuitar vence
    assert ini["preview_start_time"] == "72497"
    for key, val in [("preview_end_time", "102497"), ("pro_drums", "True"), ("diff_drums_real", "3"),
                     ("diff_vocals_harm", "2"), ("delay", "0"), ("icon", "customs"),
                     ("loading_phrase", "Frase original")]:
        assert ini[key] == val, key


def test_ini_extra_survives_project_json(tmp_path):
    s = import_song_from_folder(_folder(tmp_path))
    back = ChartSong.from_dict(json.loads(json.dumps(s.to_dict())))
    assert back.ini_extra == s.ini_extra and back.preview_start_ms == 72497


def test_new_song_ini_has_default_icon(tmp_path):
    s = ChartSong(title="Nova", artist="Banda")
    s.add_note("guitar", NoteEvent(time_ms=1000, lane="green"))
    ini = _read_ini(export_clone_hero_song(s, str(tmp_path / "out")))
    assert ini["icon"] == "midguitar"
