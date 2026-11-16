"""Editar uma dificuldade não pode apagar nota de outra."""
import types

from src.creator.chart_model import ChartSong, NoteEvent


def _song():
    s = ChartSong()
    s.add_note("guitar", NoteEvent(time_ms=1000, lane="green", difficulty="Expert"))
    s.add_note("guitar", NoteEvent(time_ms=1000, lane="green", difficulty="Easy"))
    return s


def test_remove_note_near_respects_difficulty():
    s = _song()
    assert s.remove_note_near("guitar", 1000, "green", difficulty="Easy")
    assert [n.difficulty for n in s.guitar_notes] == ["Expert"]
    assert not s.remove_note_near("guitar", 1000, "green", difficulty="Easy")


def test_remove_note_near_without_difficulty_keeps_old_behavior():
    s = _song()
    assert s.remove_note_near("guitar", 1000, "green")
    assert len(s.guitar_notes) == 1


def test_canvas_filter_uses_current_difficulty():
    from src.ui.mini_reaper_canvas import MiniReaperCanvas
    fake = types.SimpleNamespace(current_difficulty="Easy")
    check = MiniReaperCanvas._is_in_current_difficulty
    assert check(fake, NoteEvent(time_ms=0, lane="green", difficulty="Easy"))
    assert not check(fake, NoteEvent(time_ms=0, lane="green", difficulty="Expert"))
    assert check(fake, NoteEvent(time_ms=0, lane="overdrive", difficulty="Expert"))
