"""Shortname (nome interno da música no DTA/pastas): curto, ASCII e único por artista+título.

Bug visto no RB3 (RPCS3): "Salut les amoureux" e "Salut les amoureux (Auto)" viravam o mesmo
shortname depois do corte em 24 caracteres, e o jogo mostrava só uma das duas músicas.
"""
from src.creator.chart_model import ChartSong
from src.creator.rb3_dta_exporter import song_shortname


def _song(artist, title):
    return ChartSong(title=title, artist=artist)


def test_nomes_curtos_nao_mudam():
    assert song_shortname(_song("Gorillaz", "Andromeda")) == "gorillazandromeda"


def test_titulos_longos_diferentes_nao_colidem():
    a = song_shortname(_song("Joe Dassin", "Salut les amoureux"))
    b = song_shortname(_song("Joe Dassin", "Salut les amoureux (Auto)"))
    assert a != b
    assert len(a) <= 24 and len(b) <= 24
    assert a.isalnum() and b.isalnum() and a == a.lower()


def test_shortname_e_estavel():
    s = _song("Joe Dassin", "Salut les amoureux (Auto)")
    assert song_shortname(s) == song_shortname(_song("Joe Dassin", "Salut les amoureux (Auto)"))


def test_respeita_limite_menor():
    a = song_shortname(_song("Joe Dassin", "Salut les amoureux"), limit=20)
    b = song_shortname(_song("Joe Dassin", "Salut les amoureux (Auto)"), limit=20)
    assert a != b and len(a) <= 20 and len(b) <= 20


def test_vazio_usa_padrao():
    assert song_shortname(_song("", ""), default="custom_song") == "custom_song"
