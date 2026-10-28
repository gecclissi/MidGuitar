"""Testes do parser e das regras de songs.dta."""
import pytest

from src.creator.chart_model import ChartSong, NoteEvent
from src.creator.rb3_dta_exporter import generate_songs_dta_content
from src.creator.validation import (DtaSyntaxError, PROFILES, parse_dta, validate_dta)

RB3 = PROFILES["rb3_ps3"]


def _good_dta(pans="(-1.0 1.0)", vols="(-1.5 -1.5)", cores="(-1 -1)", vocal="1",
              rank="(guitar 100) (vocals 0)", name="ta", tracks="((guitar (0 1)))"):
    return ('(%s (name "T") (artist "A") (song_id 1) (game_origin rb3_dlc)\n'
            ' (song (name "songs/ta/ta") (tracks %s) (vocal_parts %s)\n'
            '  (pans %s) (vols %s) (cores %s))\n (rank %s))\n'
            % (name, tracks, vocal, pans, vols, cores, rank))


def _write(tmp_path, text, name="songs.dta"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def _codes(issues):
    return [i.code for i in issues]


def test_parse_pack_with_two_songs_comments_and_parens_in_strings():
    text = '; pack\n(song_a (name "Song (Live)") (artist "X"))\n(song_b (name "B") (artist "Y"))\n'
    tree = parse_dta(text)
    assert [e[0] for e in tree] == ["song_a", "song_b"]
    assert tree[0][1] == ["name", "Song (Live)"]


def test_parse_numbers_braces_and_quoted_symbol():
    tree = parse_dta("(a 1 -2.5 {b c} 'sym')")
    assert tree == [["a", 1, -2.5, ["b", "c"], "sym"]]


def test_unbalanced_reports_line():
    with pytest.raises(DtaSyntaxError) as e:
        parse_dta('(a\n(b "x")\n')
    assert e.value.line == 1
    assert isinstance(e.value, ValueError)


def test_extra_close_reports_line():
    with pytest.raises(DtaSyntaxError) as e:
        parse_dta("(a)\n)\n")
    assert e.value.line == 2


def test_midguitar_generated_dta_passes(tmp_path):
    s = ChartSong(title="T", artist="A")
    s.guitar_notes = [NoteEvent(1000, "green")]
    p = _write(tmp_path, generate_songs_dta_content(s, "ta"))
    errs = [i for i in validate_dta(p, RB3, {"ta": {"PART GUITAR"}}) if i.level == "error"]
    assert errs == []


def test_good_minimal_dta_has_no_issues(tmp_path):
    p = _write(tmp_path, _good_dta())
    assert validate_dta(p, RB3, {"ta": {"PART GUITAR", "PART VOCALS"}}, {"ta": 2}) == []


def test_unreadable_and_syntax(tmp_path):
    assert _codes(validate_dta(str(tmp_path / "no.dta"), RB3)) == ["DTA_UNREADABLE"]
    p = _write(tmp_path, "(a\n(b")
    issues = validate_dta(p, RB3)
    assert _codes(issues) == ["DTA_SYNTAX"]
    assert "linha" in issues[0].location


def test_latin1_fallback(tmp_path):
    p = tmp_path / "songs.dta"
    p.write_bytes(_good_dta().replace('"T"', '"Caf\xe9"').encode("latin-1"))
    assert validate_dta(str(p), RB3) == []


def test_missing_fields_each_song_in_pack(tmp_path):
    p = _write(tmp_path, "(a (name \"x\"))\n(b (artist \"y\"))\n")
    issues = validate_dta(p, RB3)
    assert set(_codes(issues)) == {"DTA_MISSING_FIELD"}
    assert any("› a" in i.location for i in issues) and any("› b" in i.location for i in issues)
    msgs = " ".join(i.message for i in issues)
    for k in ("artist", "rank", "song_id", "game_origin", "vocal_parts", "'song'"):
        assert k in msgs


def test_vocal_parts_at_top_level_is_accepted(tmp_path):
    text = _good_dta().replace("(vocal_parts 1)", "").replace("(rank", "(vocal_parts 1) (rank")
    assert validate_dta(_write(tmp_path, text), RB3) == []


def test_channel_mismatch(tmp_path):
    p = _write(tmp_path, _good_dta(pans="(-1.0 1.0)", vols="(-1.5 -1.5 0.0)"))
    assert _codes(validate_dta(p, RB3)) == ["DTA_CHANNEL_MISMATCH"]


def test_track_index_out_of_range(tmp_path):
    p = _write(tmp_path, _good_dta(tracks="((guitar (0 2)))"))
    assert _codes(validate_dta(p, RB3)) == ["DTA_CHANNEL_MISMATCH"]


def test_mogg_channels_mismatch(tmp_path):
    p = _write(tmp_path, _good_dta())
    issues = validate_dta(p, RB3, None, {"ta": 8})
    assert _codes(issues) == ["DTA_MOGG_CHANNELS"] and issues[0].level == "error"


def test_rank_without_track_warns(tmp_path):
    p = _write(tmp_path, _good_dta(vocal="0", rank="(guitar 100) (bass 0) (band 200)"))
    issues = validate_dta(p, RB3, {"ta": set()})
    assert [(i.code, i.level) for i in issues] == [("DTA_RANK_WITHOUT_TRACK", "warning")]
    assert validate_dta(p, RB3, {"ta": {"PART GUITAR"}}) == []


def test_vocal_parts_without_vocals(tmp_path):
    p = _write(tmp_path, _good_dta(vocal="1"))
    assert _codes(validate_dta(p, RB3, {"ta": {"PART GUITAR"}})) == ["DTA_VOCAL_PARTS"]
    p2 = _write(tmp_path, _good_dta(vocal="0"), "b.dta")
    assert _codes(validate_dta(p2, RB3, {"ta": {"PART GUITAR", "PART VOCALS"}})) == ["DTA_VOCAL_PARTS"]
