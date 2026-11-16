"""songs.dta do Rock Band 2: modo RB2 do gerador compartilhado."""
import glob
import os

from src.creator.chart_model import ChartSong, NoteEvent
from src.creator.rb2_exporter import export_rb2_song_package, generate_rb2_songs_dta_content
from src.creator.validation import validate_export
from src.creator.validation.dta_parser import parse_dta


def _song(year="1975", title='Salut "les" amoureux é'):
    s = ChartSong(title=title, artist="Joe", year=year)
    for i in range(30):
        s.add_note("guitar", NoteEvent(time_ms=2000 + i * 500, lane="green"))
    return s


def test_rb2_dta_fields():
    text = generate_rb2_songs_dta_content(_song(), "x")
    assert "(decade the70s)" in text and "(game_origin rb2)" in text
    assert r"\q" in text and 'les"' not in text
    assert "(vocal_gender" not in text           # sem vocal e sem valor no ini
    for banned in ("real_guitar", "(keys", "tracks_count", "encoding", "song_length"):
        assert banned not in text
    parse_dta(text)


def test_rb2_decade_follows_year():
    assert "(decade the10s)" in generate_rb2_songs_dta_content(_song("2019"), "x")
    assert "(decade the00s)" in generate_rb2_songs_dta_content(_song("2003"), "x")
    assert "(decade the80s)" in generate_rb2_songs_dta_content(_song("1984"), "x")


def test_rb2_export_is_latin1_and_validates(tmp_path):
    root = export_rb2_song_package(_song(), str(tmp_path))
    dta = glob.glob(os.path.join(root, "USRDIR", "*", "songs", "songs.dta"))[0]
    raw = open(dta, "rb").read()
    assert b"\xe9" in raw                        # é em latin-1, não UTF-8
    issues = validate_export(root, "rb2")
    assert not [i for i in issues if i.level == "error" and i.code != "LAYOUT_MISSING_MOGG"], issues
