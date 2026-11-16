def test_imports_core_modules():
    import src.creator.chart_model, src.creator.midi_generator, src.creator.chart_importer  # noqa


def test_selftest_passes_from_source(monkeypatch, tmp_path):
    """`MidGuitar.exe --selftest` importa tudo, confere os arquivos do build e codifica Vorbis."""
    import pytest
    pytest.importorskip("customtkinter", reason="UI indisponível neste ambiente")
    monkeypatch.setenv("TEMP", str(tmp_path))
    monkeypatch.setenv("TMP", str(tmp_path))
    import tempfile
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    from src.selftest import run_selftest
    assert run_selftest() == 0
    report = (tmp_path / "midguitar_selftest.txt").read_text(encoding="utf-8")
    assert report.strip().splitlines()[-1] == "OK"
