"""Ciclo Clone Hero: importar notes.mid -> gerar MIDI sem perder dados (passthrough)."""
import collections
import copy
import json
import os

import mido
import pytest
from mido import Message, MetaMessage, MidiFile, MidiTrack

from src.creator.chart_importer import import_song_from_folder
from src.creator.chart_model import ChartSong
from src.creator.midi_generator import generate_rbn_midi
from tests.acceptance.conftest import JOE, joe_song, need  # noqa: F401 (fixture)

TOL = 1  # ticks


def _signature(track):
    """(nome, notas, textos) de uma trilha; notas = [(início, fim, altura, vel, canal)]."""
    name, tick = None, 0
    active = collections.defaultdict(list)
    notes, texts = [], []
    for m in track:
        tick += m.time
        if m.type == "track_name":
            name = name or m.name
        elif m.type == "note_on" and m.velocity > 0:
            active[(m.channel, m.note)].append((tick, m.velocity))
        elif m.type in ("note_on", "note_off"):
            if active[(m.channel, m.note)]:
                s, v = active[(m.channel, m.note)].pop(0)
                notes.append((s, tick, m.note, v, m.channel))
        elif m.type in ("text", "lyrics"):
            texts.append((tick, m.type, m.text))
        elif m.type == "sysex":
            texts.append((tick, "sysex", tuple(m.data)))
    return name, notes, texts


def _tracks_by_name(mid):
    out = {}
    for t in mid.tracks:
        name, notes, texts = _signature(t)
        out[name] = (notes, texts)
    return out


def _assert_same(src_mid, out_mid, skip=()):
    src, out = _tracks_by_name(src_mid), _tracks_by_name(out_mid)
    assert set(src) == set(out)
    for name, (s_notes, s_texts) in src.items():
        if name in skip:
            continue
        o_notes, o_texts = out[name]
        groups_s, groups_o = collections.defaultdict(list), collections.defaultdict(list)
        for s, e, p, v, c in s_notes:
            groups_s[(p, v, c)].append((s, e))
        for s, e, p, v, c in o_notes:
            groups_o[(p, v, c)].append((s, e))
        assert set(groups_s) == set(groups_o), (name, set(groups_s) ^ set(groups_o))
        for key, items in groups_s.items():
            a, b = sorted(items), sorted(groups_o[key])
            assert len(a) == len(b), (name, key, len(a), len(b))
            for (s1, e1), (s2, e2) in zip(a, b):
                assert abs(s1 - s2) <= TOL and abs(e1 - e2) <= TOL, (name, key, (s1, e1), (s2, e2))
        ts, to = collections.defaultdict(list), collections.defaultdict(list)
        for t, kind, x in s_texts:
            ts[(kind, x)].append(t)
        for t, kind, x in o_texts:
            to[(kind, x)].append(t)
        assert set(ts) == set(to), (name, set(ts) ^ set(to))
        for key, ticks in ts.items():
            a, b = sorted(ticks), sorted(to[key])
            assert len(a) == len(b) and all(abs(x - y) <= TOL for x, y in zip(a, b)), (name, key)


# ---------------------------------------------------------------------------
# MIDI sintético com tudo que um custom real costuma ter
# ---------------------------------------------------------------------------
def _put(track, items):
    """items: (tick, msg) -> delta-times."""
    last = 0
    for tick, msg in sorted(items, key=lambda x: x[0]):
        track.append(msg.copy(time=tick - last))
        last = tick
    track.append(MetaMessage("end_of_track", time=0))


def _note(items, start, end, pitch, vel=96, ch=0):
    items.append((start, Message("note_on", note=pitch, velocity=vel, channel=ch)))
    items.append((end, Message("note_off", note=pitch, velocity=0, channel=ch)))


def _synthetic_mid(path):
    mid = MidiFile(type=1, ticks_per_beat=480)

    def track(name, items):
        t = MidiTrack()
        t.append(MetaMessage("track_name", name=name, time=0))
        mid.tracks.append(t)
        _put(t, items)

    tempo = MidiTrack()
    tempo.append(MetaMessage("track_name", name="notes", time=0))
    _put(tempo, [(0, MetaMessage("time_signature", numerator=4, denominator=4)),
                 (0, MetaMessage("set_tempo", tempo=500000)),
                 (3840, MetaMessage("set_tempo", tempo=400000))])
    mid.tracks.append(tempo)

    g = [(480, MetaMessage("text", text="[ENHANCED_OPENS]"))]
    _note(g, 960, 1000, 96)            # verde Expert curto (40 ticks)
    _note(g, 1440, 2400, 97)           # vermelha com sustain
    _note(g, 1440, 1460, 101)          # HOPO forçado
    _note(g, 960, 4000, 116, vel=100)  # overdrive
    _note(g, 960, 4000, 103, vel=100)  # solo
    _note(g, 2880, 2900, 95)           # open (ENHANCED_OPENS)
    _note(g, 960, 1000, 84, vel=100)   # Hard
    g.append((1440, Message("sysex", data=(0x50, 0x53, 0, 0, 3, 1, 1))))
    track("PART GUITAR", g)

    d = [(480, MetaMessage("text", text="[ENABLE_CHART_DYNAMICS]"))]
    _note(d, 960, 970, 96)             # bumbo
    _note(d, 960, 970, 98, vel=127)    # amarelo com acento
    _note(d, 1200, 1210, 97, vel=1)    # caixa ghost
    _note(d, 960, 970, 84)             # bumbo Hard
    _note(d, 960, 1300, 110, vel=100)  # marcador de tom amarelo
    _note(d, 3000, 3600, 120, vel=100)  # fill
    track("PART DRUMS", d)

    v = [(480, MetaMessage("text", text="[idle]"))]
    _note(v, 900, 2000, 105, vel=100)
    _note(v, 960, 1100, 60, vel=100)
    v.append((960, MetaMessage("lyrics", text="Sa-")))
    _note(v, 1200, 1400, 62, vel=100)
    v.append((1200, MetaMessage("lyrics", text="lut")))
    _note(v, 2400, 3500, 105, vel=100)
    _note(v, 2500, 2700, 64, vel=100)
    v.append((2500, MetaMessage("lyrics", text="les")))
    _note(v, 3000, 3100, 96, vel=100)  # percussão
    track("PART VOCALS", v)

    pg = []
    _note(pg, 960, 1200, 96, vel=103, ch=0)    # corda 0 casa 3
    _note(pg, 960, 1200, 97, vel=105, ch=13)   # corda 1 casa 5, canal 13 (abafada)
    _note(pg, 960, 1200, 108, vel=103)         # posição da mão
    _note(pg, 960, 1200, 4, vel=96)            # nome do acorde
    _note(pg, 1440, 1600, 102, vel=96)         # HOPO forçado do Pro Guitar
    track("PART REAL_GUITAR", pg)

    pk = []
    _note(pk, 0, 480, 9, vel=100)              # range shift
    _note(pk, 960, 1100, 60, vel=96)
    track("PART REAL_KEYS_X", pk)
    for suffix, pitch in (("H", 59), ("M", 57), ("E", 55)):
        pk = []
        _note(pk, 960, 1100, pitch, vel=96)
        track("PART REAL_KEYS_" + suffix, pk)

    h = []
    _note(h, 960, 1100, 61, vel=96)
    h.append((960, MetaMessage("lyrics", text="la")))
    _note(h, 900, 2000, 105, vel=100)
    track("HARM1", h)

    track("VENUE", [(960, MetaMessage("text", text="[coop_all_far]"))] +
          [(1920, MetaMessage("text", text="[lighting (chorus)]"))])

    ghl = []
    _note(ghl, 960, 1200, 94, vel=100)
    track("PART GUITAR GHL", ghl)

    beat = []
    for i in range(8):
        _note(beat, i * 480, i * 480 + 120, 12 if i % 4 == 0 else 13)
    track("BEAT", beat)

    track("EVENTS", [(480, MetaMessage("text", text="[music_start]")),
                     (960, MetaMessage("text", text="[section intro]")),
                     (4200, MetaMessage("text", text="[music_end]")),
                     (4400, MetaMessage("text", text="[end]"))])
    mid.save(path)
    return mid


@pytest.fixture
def synthetic(tmp_path):
    folder = tmp_path / "synthetic"
    folder.mkdir()
    src = _synthetic_mid(str(folder / "notes.mid"))
    return src, import_song_from_folder(str(folder))


def test_synthetic_roundtrip_is_lossless(synthetic, tmp_path):
    src, song = synthetic
    out_path = str(tmp_path / "out.mid")
    generate_rbn_midi(song).save(out_path)
    _assert_same(MidiFile(str(tmp_path / "synthetic" / "notes.mid")), MidiFile(out_path))


def test_synthetic_roundtrip_survives_project_json(synthetic, tmp_path):
    _src, song = synthetic
    back = ChartSong.from_dict(json.loads(json.dumps(song.to_dict())))
    out_path = str(tmp_path / "out.mid")
    generate_rbn_midi(back).save(out_path)
    _assert_same(MidiFile(str(tmp_path / "synthetic" / "notes.mid")), MidiFile(out_path))


def test_markers_are_not_model_notes(synthetic):
    _src, song = synthetic
    # Overdrive (116) e solo (103) viram lanes do editor; o resto dos marcadores não
    assert {n.lane for n in song.guitar_notes} <= {"green", "red", "yellow", "blue", "orange", "open",
                                                   "overdrive", "solo"}
    assert {n.lane for n in song.drum_notes} == {"kick", "yellow", "snare"}
    assert len(song.vocal_notes) == 3
    assert [v.is_phrase_end for v in song.vocal_notes] == [False, True, True]
    assert [v.lyric for v in song.vocal_notes] == ["Sa-", "lut", "les"]
    pg = sorted(song.pro_guitar_notes, key=lambda n: n.string_idx)
    assert [(n.string_idx, n.fret, n.channel) for n in pg] == [(0, 3, 0), (1, 5, 13)]


def test_generated_overdrive_does_not_duplicate_passthrough(synthetic):
    _src, song = synthetic
    for n in song.guitar_notes:
        n.is_overdrive = True
    _name, notes, _texts = _signature(next(t for t in generate_rbn_midi(song).tracks
                                           if _signature(t)[0] == "PART GUITAR"))
    assert len([n for n in notes if n[2] == 116]) == 1


def test_rb2_skips_rb3_only_passthrough_tracks(synthetic):
    _src, song = synthetic
    names = {_signature(t)[0] for t in generate_rbn_midi(song, include_rb3_tracks=False).tracks}
    assert "VENUE" in names and "PART GUITAR" in names
    assert not {"HARM1", "PART GUITAR GHL", "PART REAL_GUITAR", "PART REAL_KEYS_X"} & names


def test_beat_is_regenerated_when_bpm_changes(synthetic):
    _src, song = synthetic
    song.bpm = 90.0  # descarta o mapa importado
    beat = next(t for t in generate_rbn_midi(song).tracks if _signature(t)[0] == "BEAT")
    starts = sorted(n[0] for n in _signature(beat)[1])
    assert starts[:3] == [0, 480, 960]
    assert len(starts) > 8


# ---------------------------------------------------------------------------
# Custom real (Joe Dassin, 24 trilhas)
# ---------------------------------------------------------------------------
@need(JOE)
def test_joe_dassin_import_export_is_lossless(joe_song, tmp_path):
    song = copy.deepcopy(joe_song)
    out_path = str(tmp_path / "notes.mid")
    generate_rbn_midi(song).save(out_path)
    _assert_same(MidiFile(os.path.join(JOE, "notes.mid")), MidiFile(out_path))


def test_open_notes_become_lane_and_export_per_target(tmp_path):
    """[ENHANCED_OPENS]: 95/83/71/59 viram a lane "open"; o Clone Hero regrava no mesmo
    pitch (sem duplicar) e o Rock Band converte em verde."""
    from src.creator.chart_importer import import_song_from_folder
    from src.creator.midi_generator import generate_rbn_midi
    mid = MidiFile(ticks_per_beat=480, type=1)
    t = MidiTrack()
    t.append(MetaMessage("track_name", name="PART BASS", time=0))
    t.append(MetaMessage("text", text="[ENHANCED_OPENS]", time=0))
    for tick, pitch in ((480, 95), (1000, 83), (1500, 96), (2000, 71), (2500, 59)):
        t.append(Message("note_on", note=pitch, velocity=100, time=tick - sum(
            m.time for m in t)))
        t.append(Message("note_off", note=pitch, velocity=0, time=20))
    mid.tracks.append(t)
    folder = tmp_path / "s"
    folder.mkdir()
    mid.save(str(folder / "notes.mid"))
    (folder / "song.ini").write_text("[song]\nname=a\nartist=b\n", encoding="utf-8")
    song = import_song_from_folder(str(folder))
    lanes = sorted((n.difficulty, n.lane) for n in song.bass_notes)
    assert lanes == [("Easy", "open"), ("Expert", "green"), ("Expert", "open"),
                     ("Hard", "open"), ("Medium", "open")]

    def pitches(m):
        tr = next(x for x in m.tracks if x.name == "PART BASS")
        return sorted(x.note for x in tr if x.type == "note_on" and x.velocity > 0), tr

    ch, tr = pitches(generate_rbn_midi(song))
    assert ch == [59, 71, 83, 95, 96]
    assert any(m.type == "text" and m.text == "[ENHANCED_OPENS]" for m in tr)
    rb, tr = pitches(generate_rbn_midi(song, rock_band_only=True))
    assert rb == [60, 72, 84, 96, 96]
    assert not any(m.type == "text" and m.text == "[ENHANCED_OPENS]" for m in tr)
