"""Testes do importador: cada trilha do jogo é lida só pelo nome exato.

Customs reais (Clone Hero / YARG / RB3) trazem trilhas extras como
PART GUITAR GHL, PART ELITE_DRUMS, PART REAL_GUITAR_22 e PART KEYS_ANIM_RH.
Elas não podem ser misturadas nas trilhas que o MidGuitar edita.
"""
from mido import MidiFile, Message, MetaMessage

from src.creator.chart_model import ChartSong
from src.creator.chart_importer import _parse_midi_into_song
from tests.test_importer_tempo import _abs_track


def _note(start, note, vel=100, dur=120):
    return [(start, Message('note_on', note=note, velocity=vel)),
            (start + dur, Message('note_off', note=note, velocity=0))]


def _import(tmp_path, tracks):
    mid = MidiFile(ticks_per_beat=480)
    mid.tracks.append(_abs_track([(0, MetaMessage('set_tempo', tempo=500000))]))
    for name, events in tracks:
        mid.tracks.append(_abs_track(events, name=name))
    path = tmp_path / "notes.mid"
    mid.save(str(path))
    song = ChartSong()
    _parse_midi_into_song(MidiFile(str(path)), song)
    return song


def test_extra_tracks_are_not_merged(tmp_path):
    song = _import(tmp_path, [
        ("PART GUITAR", _note(480, 96)),
        ("PART GUITAR GHL", _note(960, 96) + _note(1440, 97)),
        ("PART BASS", _note(480, 97)),
        ("PART BASS GHL", _note(960, 97)),
        ("PART DRUMS", _note(480, 96)),
        ("PART ELITE_DRUMS", _note(960, 96)),
        ("PART KEYS", _note(480, 98)),
        ("PART KEYS_ANIM_RH", _note(960, 98)),
    ])
    assert [n.time_ms for n in song.guitar_notes if n.difficulty == "Expert"] == [500]
    assert [n.time_ms for n in song.bass_notes if n.difficulty == "Expert"] == [500]
    assert [n.time_ms for n in song.drum_notes if n.difficulty == "Expert"] == [500]
    assert [n.time_ms for n in song.keys_notes if n.difficulty == "Expert"] == [500]


def test_real_guitar_22_is_not_added_to_pro_guitar(tmp_path):
    song = _import(tmp_path, [
        ("PART REAL_GUITAR", _note(480, 96, vel=103)),
        ("PART REAL_GUITAR_22", _note(480, 96, vel=103)),
        ("PART REAL_BASS_22", _note(480, 96, vel=101)),
    ])
    assert len(song.pro_guitar_notes) == 1
    assert song.pro_bass_notes == []


def test_only_events_track_text_becomes_song_event(tmp_path):
    song = _import(tmp_path, [
        ("EVENTS", [(480, MetaMessage('text', text="[section intro]"))]),
        ("VENUE", [(480, MetaMessage('text', text="[lighting (verse)]"))]),
        ("PART GUITAR", [(0, MetaMessage('text', text="[idle]"))] + _note(480, 96)),
    ])
    assert [e.text for e in song.events] == ["[section intro]"]


def test_harmony_tracks_are_not_vocals(tmp_path):
    song = _import(tmp_path, [
        ("PART VOCALS", _note(480, 60)),
        ("HARM1", _note(960, 62)),
    ])
    assert [n.pitch for n in song.vocal_notes] == [60]
