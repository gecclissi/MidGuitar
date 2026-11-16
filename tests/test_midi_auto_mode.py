"""Roteamento das notas MIDI no modo AUTO e nos modos fixos (mensagens sintéticas)."""
import collections

from src.midi.instrument_types import InstrumentMode
from src.midi.mapper import GuitarMapper
from src.midi.reader import MIDIReader
from src.utils.config_manager import load_preset


def _reader(mode=InstrumentMode.AUTO):
    got = collections.defaultdict(list)
    r = MIDIReader(GuitarMapper(load_preset("rock_power_chords")),
                   on_pro_guitar_event=lambda *a: got["pg"].append(a),
                   on_keyboard_event=lambda *a: got["kb"].append(a),
                   on_drum_event=lambda *a: got["dr"].append(a),
                   on_classic_fret_event=lambda *a: got["cf"].append(a),
                   on_strum_event=lambda *a: got["st"].append(a),
                   on_mode_detected=lambda m: got["mode"].append(m),
                   on_audio_play=lambda notes, vel, channel=0: got["play"].append(list(notes)))
    r.set_mode(mode)
    return r, got


def _on(r, ch, note, vel=100):
    r._midi_callback(([0x90 | (ch - 1), note, vel], 0.0))


def _off(r, ch, note):
    r._midi_callback(([0x80 | (ch - 1), note, 0], 0.0))


def test_pro_guitar_strings_2_to_6():
    r, got = _reader()
    _on(r, 6, 43)  # Mi grave, casa 3
    _on(r, 2, 59)  # Si solta
    assert got["pg"] == [(6, 3, True, 100), (2, 0, True, 100)]
    assert not got["kb"]
    assert got["mode"][-1] == InstrumentMode.PRO_GUITAR


def test_pro_guitar_channel_1_valid_fret():
    r, got = _reader()
    _on(r, 1, 67)
    assert got["pg"] == [(1, 3, True, 100)]


def test_keyboard_channel_1_low_note_then_sticks():
    r, got = _reader()
    _on(r, 1, 48)   # C3: não existe casa negativa -> teclado
    _on(r, 1, 67)   # depois de reconhecer o teclado, continua teclado
    _off(r, 1, 67)
    assert not got["pg"]
    assert [a[:2] for a in got["kb"]] == [(48, True), (67, True), (67, False)]
    assert got["mode"][-1] == InstrumentMode.KEYBOARD


def test_pro_guitar_on_other_string_switches_back_from_keyboard():
    r, got = _reader()
    _on(r, 1, 50)   # teclado
    _on(r, 5, 47)   # corda Lá casa 2: só a Pro Guitar usa o canal 5
    _on(r, 1, 66)   # agora casa 2 da corda Mi agudo
    assert got["pg"] == [(5, 2, True, 100), (1, 2, True, 100)]


def test_classic_guitar_frets_and_strum_via_adapter():
    r, got = _reader()
    _on(r, 7, 60)   # verde
    _on(r, 7, 71)   # palhetada
    assert got["cf"] == [("green", True)]
    assert got["st"] == [(True,)]
    assert got["play"]  # palhetada toca o acorde do preset
    _off(r, 7, 71)
    _off(r, 7, 60)
    assert got["cf"][-1] == ("green", False)
    assert not got["kb"]


def test_generic_keyboard_on_other_channel():
    r, got = _reader()
    _on(r, 2, 30)   # fora da Pro Guitar -> teclado
    _on(r, 8, 61)   # nota que não é casa nem palhetada -> teclado
    _on(r, 8, 60)   # teclado já reconhecido: não vira casa verde
    assert not got["cf"] and not got["pg"]
    assert [a[0] for a in got["kb"]] == [30, 61, 60]


def test_fixed_pro_guitar_mode_out_of_range_does_not_crash():
    r, got = _reader(InstrumentMode.PRO_GUITAR)
    _on(r, 9, 60)   # canal sem corda
    _on(r, 1, 50)   # casa negativa
    assert not got["pg"]
    assert len(got["kb"]) == 2
    assert not got["mode"]  # modo fixo não anuncia troca


def test_drums_channel_10_in_auto():
    r, got = _reader()
    _on(r, 10, 38)
    assert got["dr"] == [(38, 100)]
    assert got["mode"] == [InstrumentMode.DRUMS]
