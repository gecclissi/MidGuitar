"""Instaladores .bat: textos vindos do usuário (título, artista, nome do pacote) não podem virar comandos."""
import os
import re

from src.creator.chart_model import ChartSong, NoteEvent

EVIL = 'Rock & Roll %PATH% ^x | calc < in > out (a) !b! "q"\r\ndel /q *'
SPECIALS = set('&%^|<>()!"')


def _song(title=EVIL, artist="A & B | C"):
    s = ChartSong(title=title, artist=artist, charter="Eu")
    for i in range(8):
        s.add_note("guitar", NoteEvent(time_ms=1000 + i * 400, lane="green"))
    return s


def _echo_label_lines(bat_text):
    """Linhas de eco do cabeçalho (entre as réguas de '=')."""
    lines = bat_text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("echo ====="))
    end = next(i for i, l in enumerate(lines) if i > start and l.startswith("echo ====="))
    return lines[start + 1:end]


def _assert_inert(bat_text):
    header = _echo_label_lines(bat_text)
    # Cabeçalho tem exatamente as duas linhas fixas, nenhuma linha extra injetada
    assert len(header) == 2
    for line in header:
        assert line.startswith("echo ")
        assert not (set(line[5:]) & SPECIALS), line
    # A quebra de linha do título não cria uma linha de comando própria
    assert not any(l.strip().lower().startswith("del ") for l in bat_text.splitlines())


def test_rpcs3_install_bat_label_is_inert():
    from src.creator.ps3_pkg_exporter import rpcs3_install_bat
    bat = rpcs3_install_bat("ABC123", "BLUS30463", EVIL)
    _assert_inert(bat)
    assert "Rock" in bat and "Roll" in bat  # o texto continua legível


def test_bat_rejects_unsafe_folder_or_title_id():
    import pytest
    from src.creator.ps3_pkg_exporter import rpcs3_install_bat
    with pytest.raises(ValueError):
        rpcs3_install_bat("ABC&calc", "BLUS30463", "x")
    with pytest.raises(ValueError):
        rpcs3_install_bat("ABC", "BLUS3046%", "x")


def test_all_exporters_write_inert_bats(tmp_path):
    from src.creator.pack_compiler import compile_ps3_song_pack
    from src.creator.ps3_pkg_exporter import export_ps3_pkg_structure
    from src.creator.rb2_exporter import export_rb2_song_package
    roots = [
        export_ps3_pkg_structure(_song(), str(tmp_path / "ps3")),
        export_rb2_song_package(_song(), str(tmp_path / "rb2")),
        compile_ps3_song_pack([_song(), _song("Outra")], 'Pack & "x" | %y%', str(tmp_path / "pk")),
    ]
    found = 0
    for root in roots:
        for name in os.listdir(root):
            if name.lower().endswith((".bat", ".cmd")):
                with open(os.path.join(root, name), encoding="utf-8") as f:
                    _assert_inert(f.read())
                found += 1
    assert found == 3


def test_no_other_bat_writers_in_src():
    """O único gerador de script de lote em src/ é rpcs3_install_bat (que higieniza o texto)."""
    root = os.path.join(os.path.dirname(__file__), "..", "src")
    writers = []
    for dp, _, files in os.walk(root):
        for fn in files:
            if fn.endswith(".py"):
                with open(os.path.join(dp, fn), encoding="utf-8") as f:
                    if re.search(r"@echo off", f.read(), re.I):
                        writers.append(fn)
    assert writers == ["ps3_pkg_exporter.py"]
