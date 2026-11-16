"""Testes contra customs reais de referência (pasta MIDGUITAR_REFS, fora do Git).

Cada subpasta de MIDGUITAR_REFS é um custom que funciona no jogo. Veja REFERENCIAS.md.
"""
import os
import shutil

import pytest

from src.creator.chart_importer import import_song_from_folder
from src.creator.midi_generator import generate_rbn_midi, save_midi
from src.creator.validation import detect_target, validate_export

TRACKS = ["guitar", "bass", "drum", "keys", "pro_guitar", "pro_bass", "pro_keys", "vocal"]
DIFFS = ["Expert", "Hard", "Medium", "Easy"]
TOLERANCE_MS = 2


_INVALID_ROOT = "<MIDGUITAR_REFS-invalida>"


@pytest.fixture(autouse=True)
def _fail_on_invalid_refs(request):
    """MIDGUITAR_REFS definida mas inexistente é erro de configuração, não motivo para pular."""
    if "ref_folder" in request.fixturenames and request.getfixturevalue("ref_folder") == _INVALID_ROOT:
        pytest.fail("MIDGUITAR_REFS aponta para algo que não é uma pasta existente: %r"
                    % os.environ.get("MIDGUITAR_REFS"))


def pytest_generate_tests(metafunc):
    if "ref_folder" not in metafunc.fixturenames:
        return
    root = os.environ.get("MIDGUITAR_REFS")
    folders = []
    if root and not os.path.isdir(root):
        metafunc.parametrize("ref_folder", [_INVALID_ROOT], ids=["refs-invalida"])
        return
    if root and os.path.isdir(root):
        folders = sorted(
            (os.path.join(root, n) for n in os.listdir(root)
             if os.path.isdir(os.path.join(root, n))),
            key=lambda p: os.path.basename(p).lower())
    if folders:
        metafunc.parametrize("ref_folder", folders,
                             ids=[os.path.basename(p) for p in folders])
    else:
        skip = pytest.mark.skip(
            reason="MIDGUITAR_REFS não definida ou sem subpastas (veja tests/REFERENCIAS.md)")
        metafunc.parametrize("ref_folder", [pytest.param(None, marks=skip)], ids=["sem-refs"])


def _times(song, track, diff):
    """Lista ordenada de time_ms de uma trilha/dificuldade (vocal não tem dificuldade)."""
    if track == "vocal":
        if diff != "Expert":
            return []
        return sorted(n.time_ms for n in song.vocal_notes)
    return sorted(n.time_ms for n in getattr(song, f"{track}_notes", []) if n.difficulty == diff)


def _snapshot(song):
    """Copia as listas de tempos agora: a geração pode acrescentar dificuldades à música."""
    return {(t, d): _times(song, t, d) for t in TRACKS for d in DIFFS}


def _has_any_notes(snapshot):
    return any(snapshot.values())


def _rb3_song_folders(ref):
    """Pastas songs/<dir>/ (abaixo de um songs.dta) com .mid ou .mid.edat."""
    found = []
    for dirpath, _dirs, files in os.walk(ref):
        if "songs.dta" not in (f.lower() for f in files):
            continue
        for name in sorted(os.listdir(dirpath)):
            sub = os.path.join(dirpath, name)
            if os.path.isdir(sub) and any(f.lower().endswith((".mid", ".mid.edat"))
                                          for f in os.listdir(sub)):
                found.append(sub)
    return found


def _has_rb3_layout(ref):
    return any("songs.dta" in (f.lower() for f in files) for _d, _s, files in os.walk(ref))


@pytest.mark.refs
def test_reference_passes_validator(ref_folder):
    target = detect_target(str(ref_folder))
    assert target is not None, "não reconheci o formato desta pasta"
    errors = [i for i in validate_export(str(ref_folder), target) if i.level == "error"]
    assert errors == [], (
        "custom que funciona no jogo foi acusado — a REGRA está errada:\n"
        + "\n".join(f"{i.code}: {i.message}" for i in errors))


@pytest.mark.refs
def test_reference_roundtrip_keeps_note_times(ref_folder, tmp_path):
    if _has_rb3_layout(ref_folder):
        song_folders = _rb3_song_folders(ref_folder)
    else:
        song_folders = [ref_folder]
    if not song_folders:
        pytest.skip("MIDI ilegível pelo importador (ex.: só .mid.edat)")

    problems = []
    checked = 0
    for idx, folder in enumerate(song_folders):
        original = import_song_from_folder(str(folder))
        before = _snapshot(original)
        if not _has_any_notes(before):
            continue
        label = os.path.basename(folder)

        out_dir = tmp_path / str(idx)
        out_dir.mkdir()
        save_midi(generate_rbn_midi(original), str(out_dir / "notes.mid"))
        for candidate in (folder, ref_folder):
            ini = os.path.join(candidate, "song.ini")
            if os.path.isfile(ini):
                shutil.copy(ini, out_dir / "song.ini")
                break
        again = import_song_from_folder(str(out_dir))
        after = _snapshot(again)

        for (track, diff), a in before.items():
            if not a:
                continue  # a geração acrescenta dificuldades que o original não tinha
            checked += 1
            b = after[(track, diff)]
            if len(a) != len(b):
                problems.append(f"{label} {track}/{diff}: {len(a)} -> {len(b)} notas")
            elif any(abs(x - y) > TOLERANCE_MS for x, y in zip(a, b)):
                problems.append(f"{label} {track}/{diff}: dessincronizou")

    if not checked:
        pytest.skip("MIDI ilegível pelo importador (ex.: só .mid.edat)")
    assert problems == [], "\n".join(problems)
