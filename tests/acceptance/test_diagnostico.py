"""Testes de aceitação do diagnóstico de 2026-11-16.

Comportamento que funciona hoje: testes normais.
Comportamento quebrado hoje: xfail(strict=True) com o motivo. Quando um bug for
corrigido, o xfail passa a "XPASS" e o pytest acusa falha: remova o xfail.
Detalhes em docs/superpowers/specs/2026-11-16-diagnostico-funcionalidades.md.
"""
import collections
import copy
import glob
import json
import os
import struct

import mido
import numpy as np
import pytest
import soundfile as sf

from src.creator.chart_model import ChartSong, NoteEvent
from src.creator.chart_importer import import_song_from_folder
from src.creator.midi_generator import generate_rbn_midi
from src.creator.rbn_specs import DRUM_NOTES, FRET_NOTES
from tests.acceptance.conftest import (FIVESOS, GORILLAZ, JOE, PAVLO, PKG_FILE, XBOX_CON,
                                       need, ps3_song_dir)

DIFF_RANGES = {"Expert": (96, 100), "Hard": (84, 88), "Medium": (72, 76), "Easy": (60, 64)}


def _track(mid, name):
    for t in mid.tracks:
        if any(m.type == "track_name" and m.name == name for m in t):
            return t
    return None


def _ons(track, notes=None):
    return [m for m in track if m.type == "note_on" and m.velocity > 0 and (notes is None or m.note in notes)]


def _src_count(mid, name, lo, hi):
    return len(_ons(_track(mid, name), set(range(lo, hi + 1))))


def _wav(path, seconds=3.0, sr=44100):
    t = np.arange(int(sr * seconds)) / sr
    x = (0.3 * np.sin(2 * np.pi * 220 * t)).astype("float32")
    sf.write(path, np.stack([x, x], axis=1), sr)
    return path


def _drum_song():
    s = ChartSong(title="Bateria", artist="Diag")
    for lane, t in [("kick", 0), ("snare", 500), ("yellow", 1000), ("blue", 1500), ("green", 2000)]:
        s.add_note("drum", NoteEvent(time_ms=t, lane=lane, difficulty="Expert"))
    return s


# ---------------------------------------------------------------------------
# Importação Clone Hero (.mid) — funciona
# ---------------------------------------------------------------------------
@need(JOE)
def test_ch_import_counts_match_source(joe_song):
    src = mido.MidiFile(os.path.join(JOE, "notes.mid"))
    for track, attr in [("PART GUITAR", "guitar"), ("PART DRUMS", "drum"), ("PART KEYS", "keys")]:
        got = collections.Counter(n.difficulty for n in getattr(joe_song, f"{attr}_notes"))
        for diff, (lo, hi) in DIFF_RANGES.items():
            assert got[diff] == _src_count(src, track, lo, hi), (track, diff)
    assert len(joe_song.tempo_map.tempos) == 154
    assert len(joe_song.vocal_notes) == 409
    assert len(joe_song.events) == 14


@need(JOE)
def test_ch_export_roundtrip_keeps_counts_and_validates(joe_song, tmp_path):
    from src.creator.clonehero_exporter import export_clone_hero_song
    from src.creator.validation import validate_export
    song = copy.deepcopy(joe_song)
    song.audio_stems = []
    song.audio_path = None
    folder = export_clone_hero_song(song, str(tmp_path))
    assert not [i for i in validate_export(folder, "clonehero") if i.level == "error" and i.code != "CH_NO_AUDIO"]
    back = import_song_from_folder(folder)
    for attr in ["guitar", "bass", "drum", "keys", "pro_guitar", "pro_bass", "pro_keys"]:
        assert len(getattr(back, f"{attr}_notes")) == len(getattr(joe_song, f"{attr}_notes")), attr
    assert len(back.vocal_notes) == len(joe_song.vocal_notes)


# ---------------------------------------------------------------------------
# Perdas na ida e volta Clone Hero — quebrado
# ---------------------------------------------------------------------------
def _ch_export_mid(song, tmp_path):
    from src.creator.clonehero_exporter import export_clone_hero_song
    song = copy.deepcopy(song)
    song.audio_stems, song.audio_path = [], None
    folder = export_clone_hero_song(song, str(tmp_path))
    return mido.MidiFile(os.path.join(folder, "notes.mid")), folder


@need(JOE)
def test_ch_roundtrip_keeps_vocal_phrases(joe_song, tmp_path):
    out, _ = _ch_export_mid(joe_song, tmp_path)
    assert len(_ons(_track(out, "PART VOCALS"), {105})) == 35


@need(JOE)
def test_ch_roundtrip_keeps_overdrive(joe_song, tmp_path):
    out, _ = _ch_export_mid(joe_song, tmp_path)
    assert len(_ons(_track(out, "PART GUITAR"), {116})) == 15


@need(JOE)
def test_ch_roundtrip_keeps_tom_markers(joe_song, tmp_path):
    out, _ = _ch_export_mid(joe_song, tmp_path)
    assert len(_ons(_track(out, "PART DRUMS"), {110, 111, 112})) == 15


@need(JOE)
def test_ch_import_reads_preview_and_pro_ranks(joe_song):
    assert joe_song.preview_start_ms == 72497
    assert joe_song.diff_pro_guitar == 5 and joe_song.diff_vocals == 1


# ---------------------------------------------------------------------------
# notes.chart (sintético; não há .chart real nas referências)
# ---------------------------------------------------------------------------
CHART = """[Song]
{
  Name = "Chart Test"
  Artist = "Diag"
  Resolution = 192
}
[SyncTrack]
{
  0 = TS 4
  0 = B 120000
  768 = B 150000
}
[Events]
{
  0 = E "section Intro"
}
[ExpertSingle]
{
  0 = N 0 0
  192 = N 1 96
}
[ExpertDrums]
{
  0 = N 0 0
  192 = N 1 0
  384 = N 2 0
}
"""


def _chart_song(tmp_path):
    folder = tmp_path / "chart"
    folder.mkdir()
    (folder / "notes.chart").write_text(CHART, encoding="utf-8")
    return import_song_from_folder(str(folder))


def test_chart_import_notes_and_tempo(tmp_path):
    s = _chart_song(tmp_path)
    exp = sorted((n.time_ms, n.lane) for n in s.guitar_notes if n.difficulty == "Expert")
    assert exp == [(0, "green"), (500, "red")]
    assert [t.us_per_beat for t in s.tempo_map.tempos] == [500000, 400000]


def test_chart_import_reads_artist(tmp_path):
    assert _chart_song(tmp_path).artist == "Diag"


def test_chart_import_reads_events(tmp_path):
    assert _chart_song(tmp_path).events


def test_chart_drums_export_kick_and_snare(tmp_path):
    mid = generate_rbn_midi(_chart_song(tmp_path))
    notes = {m.note for m in _ons(_track(mid, "PART DRUMS"))}
    assert {DRUM_NOTES["Expert"]["kick"], DRUM_NOTES["Expert"]["snare"]} <= notes


# ---------------------------------------------------------------------------
# Bateria do auto-charter / editor — quebrado
# ---------------------------------------------------------------------------
def test_drum_kick_snare_lanes_are_exported():
    from src.creator.auto_charter import auto_generate_chart
    s = ChartSong()
    auto_generate_chart(s, selected_instruments=["drum"])
    assert {n.lane for n in s.drum_notes} - {"overdrive"} <= set(DRUM_NOTES["Expert"])
    mid = generate_rbn_midi(s)
    notes = {m.note for m in _ons(_track(mid, "PART DRUMS"))}
    assert {96, 97} <= notes


def test_drum_kick_snare_named_lanes_are_exported():
    s = ChartSong()
    s.add_note("drum", NoteEvent(time_ms=0, lane="kick"))
    s.add_note("drum", NoteEvent(time_ms=500, lane="snare"))
    notes = {m.note for m in _ons(_track(generate_rbn_midi(s), "PART DRUMS"))}
    assert {96, 97} <= notes


def test_auto_chart_all_modes_generate_four_difficulties(tmp_path):
    from src.creator.auto_charter import auto_generate_chart
    audio = _wav(str(tmp_path / "a.wav"), seconds=20)
    for inst in ["guitar", "bass", "drum", "keys", "pro_guitar", "pro_bass", "pro_keys"]:
        s = ChartSong()
        s.audio_path = audio
        auto_generate_chart(s, selected_instruments=[inst])
        diffs = {n.difficulty for n in getattr(s, f"{inst}_notes")}
        assert diffs == {"Expert", "Hard", "Medium", "Easy"}, inst
        others = [t for t in ["guitar", "bass", "drum", "keys", "pro_guitar", "pro_bass", "pro_keys"] if t != inst]
        assert not any(getattr(s, f"{t}_notes") for t in others), inst


def test_no_lyrics_means_no_vocals():
    from src.creator.auto_charter import auto_generate_chart
    from src.creator.rb3_dta_exporter import generate_songs_dta_content
    s = ChartSong()
    auto_generate_chart(s, selected_instruments=["guitar", "vocals"])
    assert not s.vocal_notes
    assert "(vocal_parts 0)" in generate_songs_dta_content(s, "x")


# ---------------------------------------------------------------------------
# Letras
# ---------------------------------------------------------------------------
def test_lyrics_txt_lrc_srt():
    from src.creator.lyric_processor import align_lyrics_to_song
    lrc = "[00:05.00]Salut les amoureux\n[00:09.50]Les vacances\n"
    srt = "1\n00:00:05,000 --> 00:00:08,000\nSalut les amoureux\n"
    for text, first_ms in [("Salut les amoureux\nLes vacances\n", 4000), (lrc, 5000), (srt, 5000)]:
        s = ChartSong()
        assert align_lyrics_to_song(s, text) > 0
        assert s.vocal_notes[0].time_ms == first_ms
        assert not any("-->" in v.lyric or ":" in v.lyric for v in s.vocal_notes)


# ---------------------------------------------------------------------------
# Projeto (to_dict / from_dict)
# ---------------------------------------------------------------------------
def test_project_roundtrip_keeps_vocals():
    from src.creator.lyric_processor import align_lyrics_to_song
    s = ChartSong()
    align_lyrics_to_song(s, "Salut les amoureux\n")
    back = ChartSong.from_dict(json.loads(json.dumps(s.to_dict())))
    assert len(back.vocal_notes) == len(s.vocal_notes) and back.lyrics_raw == s.lyrics_raw


def test_project_roundtrip_keeps_instrument_notes():
    s = _drum_song()
    s.add_note("guitar", NoteEvent(time_ms=10, lane="green", difficulty="Hard"))
    back = ChartSong.from_dict(json.loads(json.dumps(s.to_dict())))
    assert [n.__dict__ for n in back.drum_notes] == [n.__dict__ for n in s.drum_notes]
    assert [n.__dict__ for n in back.guitar_notes] == [n.__dict__ for n in s.guitar_notes]


# ---------------------------------------------------------------------------
# Áudio / .mogg
# ---------------------------------------------------------------------------
def test_unencrypted_mogg_roundtrip(tmp_path):
    from src.creator.mogg_generator import create_unencrypted_mogg, extract_ogg_from_mogg, is_mogg_file
    wav = _wav(str(tmp_path / "a.wav"))
    mogg = str(tmp_path / "a.mogg")
    assert create_unencrypted_mogg(wav, mogg) and is_mogg_file(mogg)
    ogg = extract_ogg_from_mogg(mogg, str(tmp_path / "back.ogg"))
    assert abs(sf.info(ogg).duration - 3.0) < 0.05


@need(GORILLAZ)
def test_encrypted_mogg_is_not_extracted_as_garbage(copy_ref):
    from src.creator.mogg_generator import extract_ogg_from_mogg
    song_dir = ps3_song_dir(copy_ref(GORILLAZ))
    mogg = glob.glob(os.path.join(song_dir, "*.mogg"))[0]
    out = mogg + ".ogg"
    assert extract_ogg_from_mogg(mogg, out) == mogg
    assert not os.path.exists(out)


@need(JOE)
def test_opus_becomes_vorbis_inside_mogg(copy_ref, tmp_path):
    from src.creator.mogg_generator import create_unencrypted_mogg
    opus = copy_ref(os.path.join(JOE, "bass.opus"))
    mogg = str(tmp_path / "bass.mogg")
    assert create_unencrypted_mogg(opus, mogg)
    with open(mogg, "rb") as f:
        off = struct.unpack("<II", f.read(8))[1]
        f.seek(off)
        assert b"vorbis" in f.read(128)


def test_bpm_detection_click_128(tmp_path):
    from src.creator.mogg_generator import analyze_audio_file
    sr, bpm = 44100, 128
    x = np.zeros(sr * 30, dtype="float32")
    for k in range(int(30 * bpm / 60)):
        i = int(k * 60 / bpm * sr)
        x[i:i + 2000] += np.hanning(2000).astype("float32")
    p = str(tmp_path / "click.wav")
    sf.write(p, x, sr)
    assert abs(analyze_audio_file(p)["bpm"] - bpm) <= 1


# ---------------------------------------------------------------------------
# Importação de consoles — quebrado
# ---------------------------------------------------------------------------
@need(GORILLAZ)
@pytest.mark.xfail(strict=True, reason="importador não lê .mid.edat (NPD): pasta PS3 extraída carrega 0 notas")
def test_ps3_extracted_folder_imports_notes(copy_ref):
    song = import_song_from_folder(ps3_song_dir(copy_ref(GORILLAZ)))
    assert song.guitar_notes or song.drum_notes or song.bass_notes


@need(FIVESOS)
@pytest.mark.xfail(strict=True, reason="importador lê songs.dta com regex de 1 linha; DTA real (C3/Onyx) tem chaves entre aspas e quebras de linha")
def test_ps3_songs_dta_metadata_is_read(copy_ref):
    song = import_song_from_folder(ps3_song_dir(copy_ref(FIVESOS)))
    assert song.title == "Ghost of You"


@need(GORILLAZ)
@pytest.mark.xfail(strict=True, reason=".mogg criptografado: importador aponta audio_path para um *_extracted.ogg que não existe")
def test_ps3_import_audio_path_exists(copy_ref):
    song = import_song_from_folder(ps3_song_dir(copy_ref(GORILLAZ)))
    assert song.audio_path is None or os.path.exists(song.audio_path)


@need(XBOX_CON)
@pytest.mark.xfail(strict=True, reason="não há leitor de pacote CON/STFS do Xbox 360")
def test_xbox_con_import(copy_ref):
    song = import_song_from_folder(copy_ref(XBOX_CON))
    assert song.guitar_notes


@need(PKG_FILE)
@pytest.mark.xfail(strict=True, reason="não há leitor de .pkg do PS3")
def test_ps3_pkg_file_import(copy_ref):
    song = import_song_from_folder(copy_ref(PKG_FILE))
    assert song.guitar_notes


@need(PAVLO)
@pytest.mark.xfail(strict=True, reason="GHWT:DE (.pak.xen/.fsb.xen) não é suportado: só o título é lido")
def test_ghwtde_import(copy_ref):
    song = import_song_from_folder(copy_ref(PAVLO))
    assert song.guitar_notes and song.audio_path


# ---------------------------------------------------------------------------
# Exportação para consoles
# ---------------------------------------------------------------------------
def _small_song(tmp_path):
    s = ChartSong(title="Exemplo", artist="Diag")
    for i in range(40):
        s.add_note("guitar", NoteEvent(time_ms=2000 + i * 500, lane="green"))
        s.add_note("drum", NoteEvent(time_ms=2000 + i * 500, lane="kick"))
    s.audio_path = _wav(str(tmp_path / "audio.wav"), seconds=25)
    return s


@pytest.mark.xfail(strict=True, reason="PS3: .mid solto (sem .mid.edat); .mid.edat fica para o passo 3B")
def test_ps3_export_passes_validator(tmp_path):
    from src.creator.ps3_pkg_exporter import export_ps3_pkg_structure
    from src.creator.validation import validate_export
    folder = export_ps3_pkg_structure(_small_song(tmp_path), str(tmp_path / "out"))
    assert not [i for i in validate_export(folder, "rb3_ps3") if i.level == "error"]


@pytest.mark.xfail(strict=True, reason="Xbox 360: gera pasta solta, sem pacote CON/LIVE")
def test_xbox360_export_passes_validator(tmp_path):
    from src.creator.xbox360_exporter import export_xbox360_structure
    from src.creator.validation import validate_export
    folder = export_xbox360_structure(_small_song(tmp_path), str(tmp_path / "out"))
    assert not [i for i in validate_export(folder, "xbox360") if i.level == "error"]


@pytest.mark.xfail(strict=True, reason="PS4: não gera .songdta_ps4/.rbmid_ps4/.moggsong")
def test_ps4_export_passes_validator(tmp_path):
    from src.creator.ps4_exporter import export_ps4_structure
    from src.creator.validation import validate_export
    folder = export_ps4_structure(_small_song(tmp_path), str(tmp_path / "out"))
    assert not [i for i in validate_export(folder, "ps4") if i.level == "error"]


def test_clonehero_export_from_scratch_validates(tmp_path):
    from src.creator.clonehero_exporter import export_clone_hero_song
    from src.creator.validation import validate_export
    folder = export_clone_hero_song(_small_song(tmp_path), str(tmp_path / "out"))
    assert not [i for i in validate_export(folder, "clonehero") if i.level == "error"]


def test_rb3_dta_drum_solo_format():
    from src.creator.rb3_dta_exporter import generate_songs_dta_content
    assert "kick.cue" in generate_songs_dta_content(_drum_song(), "x")


@need(JOE)
def test_rb3_multistem_mogg_channels_match_dta(joe_song, tmp_path):
    from src.creator.rb3_dta_exporter import export_rb3_song_package
    from src.creator.validation import validate_export
    song = copy.deepcopy(joe_song)
    wav = _wav(str(tmp_path / "s.wav"))
    song.audio_path, song.audio_stems = wav, [wav, wav]
    folder = export_rb3_song_package(song, str(tmp_path / "out"))
    assert "DTA_MOGG_CHANNELS" not in {i.code for i in validate_export(folder, "rb3_ps3")}


# ---------------------------------------------------------------------------
# Pacotes
# ---------------------------------------------------------------------------
def test_pack_compilers_two_songs(tmp_path):
    from src.creator.pack_compiler import compile_clone_hero_pack, compile_ps3_song_pack
    from src.creator.validation import parse_dta
    a = _small_song(tmp_path)
    b = copy.deepcopy(a)
    b.title = "Outra"
    ch = compile_clone_hero_pack([a, b], "Pack CH", str(tmp_path / "ch"))
    assert len(os.listdir(ch)) == 2
    ps3 = compile_ps3_song_pack([a, b], "Pack PS3", str(tmp_path / "ps3"))
    dtas = glob.glob(os.path.join(ps3, "USRDIR", "*", "songs", "songs.dta"))
    assert len(dtas) == 1
    dta = open(dtas[0], encoding="utf-8").read()
    assert len(parse_dta(dta)) == 2


# ---------------------------------------------------------------------------
# MIDI ao vivo (mensagens sintéticas, sem hardware)
# ---------------------------------------------------------------------------
def _reader():
    from src.midi.mapper import GuitarMapper
    from src.midi.reader import MIDIReader
    from src.utils.config_manager import load_preset
    got = collections.defaultdict(list)
    r = MIDIReader(GuitarMapper(load_preset("rock_power_chords")),
                   on_pro_guitar_event=lambda *a: got["pg"].append(a),
                   on_keyboard_event=lambda *a: got["kb"].append(a),
                   on_drum_event=lambda *a: got["dr"].append(a),
                   on_classic_fret_event=lambda *a: got["cf"].append(a),
                   on_strum_event=lambda *a: got["st"].append(a))
    return r, got


def test_midi_drums_channel_10():
    r, got = _reader()
    r._midi_callback(([0x99, 36, 100], 0.0))
    assert got["dr"] == [(36, 100)]


@pytest.mark.xfail(strict=True, reason="modo AUTO: teclado no canal 1 vira Pro Guitar com casa negativa")
def test_midi_auto_keyboard_on_channel_1():
    r, got = _reader()
    r._midi_callback(([0x90, 60, 90], 0.0))
    assert got["kb"] and not got["pg"]


@pytest.mark.xfail(strict=True, reason="modo AUTO: palhetada (notas 69/71/72) nunca é reconhecida; vira tecla de teclado")
def test_midi_auto_strum_note():
    r, got = _reader()
    r._midi_callback(([0x96, 71, 100], 0.0))
    assert got["st"]
