"""
Gerador de Arquivos songs.dta para Rock Band 3 (Padrão Harmonix / Magma C3).
Gera metadados, canais de áudio, panning, volumes, ranks de dificuldade
e estrutura de pastas prontas para Rock Band 3 (PS3/RPCS3, Xbox 360 e PS4).

Este módulo é o único lugar que monta o songs.dta do RB3: os exportadores de
PS3, Xbox 360, PS4 e o compilador de pacotes usam generate_songs_dta_content e
write_rb3_song_files daqui. O formato segue as referências reais (Magma C3):
`tracks_count`, `drum_solo (seqs ...)`, `song_length`, `game_origin ugc_plus`...
"""

import hashlib
import os
from typing import List, Optional, Tuple

from src.creator.chart_model import ChartSong
from src.creator.midi_generator import generate_rbn_midi, save_midi
from src.creator.rb_mogg_multitrack import (INSTRUMENT_ORDER, AudioLayout, build_rb_mogg,
                                            charted_instruments, single_mix_layout)

RB3_PS3_TITLE_ID = "BLUS30463"

# Limites dos tiers de dificuldade do Rock Band 3 (valores do Magma C3; batem com os
# ranks das referências reais). Índice 0 = 1 ponto ... índice 5 = devil.
RANK_TIERS = {
    "drum": (124, 151, 178, 242, 345, 448),
    "guitar": (139, 176, 221, 267, 333, 409),
    "bass": (135, 181, 228, 293, 364, 436),
    "vocals": (132, 175, 218, 279, 353, 427),
    "keys": (153, 211, 269, 327, 385, 443),
    "real_guitar": (150, 208, 267, 325, 384, 442),
    "real_bass": (150, 208, 267, 325, 384, 442),
    "real_keys": (153, 211, 269, 327, 385, 443),
    "band": (163, 215, 243, 267, 292, 345),
}

# Faixa de song_id para músicas customizadas: positivo em 32 bits com sinal e acima
# dos IDs oficiais (as referências C3 usam valores na casa de 1,7-2,1 bilhões)
_SONG_ID_BASE = 1000000000
_SONG_ID_SPAN = 2147483647 - _SONG_ID_BASE


def rank_value(instrument: str, tier: int, has_notes: bool) -> int:
    """Ranking 0-6 do MidGuitar (0 = sem pontos, 6 = devil) -> valor do DTA. 0 sem notas."""
    if not has_notes:
        return 0
    tier = int(tier) if tier is not None else 0
    if tier <= 0:
        return 1
    return RANK_TIERS[instrument][min(tier, 6) - 1]


def _ascii_alnum(text: str) -> str:
    """Só letras/dígitos ASCII (acentos viram a letra base): nomes de arquivo e pasta do
    console e content id do PS3 não aceitam outros caracteres."""
    import unicodedata
    plain = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in plain if c.isascii() and c.isalnum())


def song_shortname(song: ChartSong, limit: int = 24, default: str = "custom_song") -> str:
    return _ascii_alnum(f"{song.artist}_{song.title}").lower()[:limit] or default


def stable_song_id(song: ChartSong, salt: str = "") -> int:
    """song_id estável e único por artista+título+charter (hash SHA-1 de 31 bits)."""
    key = "|".join([salt, (song.artist or "").strip().lower(), (song.title or "").strip().lower(),
                    (song.charter or "").strip().lower()])
    h = int(hashlib.sha1(key.encode("utf-8")).hexdigest()[:12], 16)
    return _SONG_ID_BASE + h % _SONG_ID_SPAN


def ps3_folder_name(shortname: str, song_id: int, limit: int = 27) -> str:
    """Pasta única em USRDIR/ (como o Magma C3: prefixo + id + nome, até 27 caracteres)."""
    name = "MG%d%s" % (song_id % 100000000, _ascii_alnum(shortname).upper())
    return name[:limit]


def _q(text) -> str:
    """Texto entre aspas do DTA: aspas viram \\q (escape da Harmonix)."""
    return str(text if text is not None else "").replace('"', "\\q").replace("\n", " ")


def _ini(song: ChartSong, key: str, default=None):
    v = (getattr(song, "ini_extra", None) or {}).get(key)
    return default if v is None or str(v).strip() == "" else str(v).strip()


def _int_or(value, default: int) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _harmony_parts(song: ChartSong) -> int:
    """Quantas trilhas HARM1-3 com notas vieram no passthrough (0 se nenhuma)."""
    parts = 0
    for t in getattr(song, "passthrough_tracks", None) or []:
        name = (t.get("name") or "").strip().upper()
        if name in ("HARM1", "HARM2", "HARM3") and any(
                e[1].get("type") == "note_on" for e in t.get("events", [])):
            parts = max(parts, int(name[-1]))
    return parts


def vocal_parts_count(song: ChartSong) -> int:
    harm = _harmony_parts(song)
    if harm >= 2:
        return harm
    return 1 if (song.vocal_notes or harm) else 0


def _tuning(song: ChartSong, key: str, strings: int) -> str:
    raw = _ini(song, key, "")
    vals = [_int_or(v, 0) for v in raw.replace(",", " ").split()]
    if len(vals) != strings:
        vals = [0] * strings
    return "(%s)" % " ".join(str(v) for v in vals)


# Gêneros que o Rock Band 3 reconhece (símbolos do DTA); o resto vira "other"
RB3_GENRES = frozenset((
    "alternative", "blues", "classical", "classicrock", "country", "emo", "fusion", "glam",
    "grunge", "hiphoprap", "indierock", "inspirational", "jazz", "jrock", "latin", "metal",
    "new_wave", "novelty", "numetal", "other", "popdanceelectronic", "poprock", "prog",
    "punk", "rbsoulfunk", "reggaeska", "rock", "southernrock", "world", "urban",
))
_GENRE_ALIASES = {"pop": "poprock", "poprock": "poprock", "hiphop": "hiphoprap", "rap": "hiphoprap",
                  "indie": "indierock", "newwave": "new_wave", "electronic": "popdanceelectronic",
                  "dance": "popdanceelectronic", "rb": "rbsoulfunk", "soul": "rbsoulfunk",
                  "funk": "rbsoulfunk", "reggae": "reggaeska", "ska": "reggaeska",
                  "progressive": "prog", "progrock": "prog", "southern": "southernrock"}


def rb3_genre(genre: str) -> str:
    """Gênero livre (song.ini / UI) -> símbolo de gênero do RB3."""
    key = "".join(c for c in (genre or "").lower() if c.isalnum() or c == "_")
    if key in RB3_GENRES:
        return key
    return _GENRE_ALIASES.get(key.replace("_", ""), "other")


def _vocal_gender(song: ChartSong) -> str:
    v = (_ini(song, "vocal_gender", "male") or "male").lower()
    return "female" if v in ("female", "f", "2") else "male"


def audio_length_ms(song: ChartSong) -> Optional[int]:
    """Duração do áudio (maior entre mix e stems), ou None se não der para ler."""
    best = None
    paths = list(getattr(song, "audio_stems", None) or []) + [song.audio_path]
    for p in paths:
        if not p or not os.path.isfile(p):
            continue
        try:
            import soundfile as sf
            info = sf.info(p)
            ms = int(round(info.frames * 1000.0 / info.samplerate))
            best = ms if best is None else max(best, ms)
        except Exception:
            continue
    return best


def _format_tracks(layout: AudioLayout, charted: dict) -> str:
    items = []
    for inst in INSTRUMENT_ORDER:
        chans = layout.tracks.get(inst)
        if chans and (charted.get(inst) or not layout.multitrack):
            items.append("(%s (%s))" % (inst, " ".join(str(c) for c in chans)))
    return "(%s)" % "\n          ".join(items)


def _floats(vals) -> str:
    return "(%s)" % " ".join("%.1f" % v for v in vals)


def generate_songs_dta_content(song: ChartSong, shortname: str, song_id: int = None,
                               layout: Optional[AudioLayout] = None,
                               song_length_ms: Optional[int] = None,
                               album_art: Optional[bool] = None,
                               rb2: bool = False) -> str:
    """Gera o texto de definição songs.dta conforme a sintaxe oficial Harmonix.

    layout: canais reais do .mogg (rb_mogg_multitrack); sem ele, mix estéreo de 2 canais.
    O texto é para gravar em UTF-8 (a entrada declara `encoding utf8`).
    rb2=True: modo Rock Band 2 (só campos que o RB2 conhece; ver _generate_rb2_dta)."""
    if rb2:
        return _generate_rb2_dta(song, shortname, song_id, album_art)
    if song_id is None:
        song_id = stable_song_id(song)
    charted = charted_instruments(song)
    if layout is None:
        layout = single_mix_layout(charted)

    has_vocals = charted["vocals"]
    has_guitar = bool(song.guitar_notes)
    has_bass = bool(song.bass_notes)
    has_drums = bool(song.drum_notes)
    has_keys = bool(song.keys_notes)
    has_pro_guitar = bool(getattr(song, "pro_guitar_notes", None))
    has_pro_bass = bool(getattr(song, "pro_bass_notes", None))
    has_pro_keys = bool(getattr(song, "pro_keys_notes", None))

    if song_length_ms is None:
        song_length_ms = audio_length_ms(song) or song.get_effective_duration_ms()
    if album_art is None:
        album_art = bool(song.album_art_path and os.path.exists(song.album_art_path))

    preview_start = max(0, int(song.preview_start_ms or 0))
    hopo = _int_or(_ini(song, "hopo_frequency"), 170)
    rating = _int_or(_ini(song, "rating"), 2)
    rating = rating if 1 <= rating <= 4 else 2
    track_number = max(1, _int_or(_ini(song, "album_track"), 1))

    tracks_count = ""
    if layout.multitrack:
        tracks_count = "\n      (tracks_count (%s))" % " ".join(str(n) for n in layout.tracks_count)

    tuning = ""
    if has_pro_guitar:
        tuning += "\n   (real_guitar_tuning %s)" % _tuning(song, "real_guitar_tuning", 6)
    if has_pro_bass:
        tuning += "\n   (real_bass_tuning %s)" % _tuning(song, "real_bass_tuning", 4)

    band = any([has_drums, has_guitar, has_bass, has_keys, has_vocals])
    return f"""({shortname}
   (name "{_q(song.title)}")
   (artist "{_q(song.artist)}")
   (master TRUE)
   (song_id {song_id})
   (song
      (name "songs/{shortname}/{shortname}"){tracks_count}
      (tracks
         {_format_tracks(layout, charted)}
      )
      (vocal_parts {vocal_parts_count(song)})
      (pans {_floats(layout.pans)})
      (vols {_floats(layout.vols)})
      (cores ({" ".join(str(c) for c in layout.cores)}))
      (drum_solo
         (seqs (kick.cue snare.cue tom1.cue tom2.cue crash.cue))
      )
      (drum_freestyle
         (seqs (kick.cue snare.cue hat.cue ride.cue crash.cue))
      )
      (mute_volume -96)
      (mute_volume_vocals -12)
      (hopo_threshold {hopo})
   )
   (bank "sfx/tambourine_bank.milo")
   (drum_bank sfx/kit01_bank.milo)
   (anim_tempo kTempoMedium)
   (song_scroll_speed 2300)
   (preview {preview_start} {preview_start + 30000})
   (song_length {int(song_length_ms)})
   (rank
      (drum {rank_value("drum", song.diff_drums, has_drums)})
      (guitar {rank_value("guitar", song.diff_guitar, has_guitar)})
      (bass {rank_value("bass", song.diff_bass, has_bass)})
      (vocals {rank_value("vocals", song.diff_vocals, has_vocals)})
      (keys {rank_value("keys", song.diff_keys, has_keys)})
      (real_guitar {rank_value("real_guitar", getattr(song, 'diff_pro_guitar', 3), has_pro_guitar)})
      (real_bass {rank_value("real_bass", getattr(song, 'diff_pro_bass', 2), has_pro_bass)})
      (real_keys {rank_value("real_keys", getattr(song, 'diff_pro_keys', 3), has_pro_keys)})
      (band {rank_value("band", song.diff_band, band)})
   )
   (genre {rb3_genre(song.genre)})
   (vocal_gender {_vocal_gender(song)})
   (version 30)
   (format 10)
   (album_art {1 if album_art else "FALSE"})
   (year_released {_int_or(song.year, 2026)})
   (rating {rating})
   (tuning_offset_cents 0)
   (guide_pitch_volume -3.0)
   (game_origin ugc_plus)
   (encoding utf8)
   (album_name "{_q(song.album)}")
   (album_track_number {track_number}){tuning}
   (author "{_q(song.charter)}")
)
"""


def rb2_decade(year) -> str:
    """Ano -> símbolo de década do DTA (the60s ... the10s); o RB2 não conhece décadas
    fora dessa faixa, então anos extremos são limitados a ela."""
    y = _int_or(year, 2010)
    if y >= 2010:
        return "the10s"
    if y >= 2000:
        return "the00s"
    return "the%ds" % max(60, min(90, (y // 10) * 10 % 100))


def latin1_safe(text: str) -> str:
    """Troca o que o latin-1 (codificação do DTA do RB2) não representa pela letra base
    (ou '?'), em vez de perder o caractere sem aviso."""
    import unicodedata
    out = []
    for ch in text:
        try:
            ch.encode("latin-1")
            out.append(ch)
        except UnicodeEncodeError:
            base = unicodedata.normalize("NFKD", ch)
            base = "".join(c for c in base if c.isascii())
            out.append(base or "?")
    return "".join(out)


def _generate_rb2_dta(song: ChartSong, shortname: str, song_id: Optional[int],
                      album_art: Optional[bool]) -> str:
    """songs.dta do Rock Band 2: format 4, game_origin rb2, sem teclado nem real_*,
    sem `encoding` (o jogo lê latin-1) e mix estéreo único de 2 canais."""
    if song_id is None:
        song_id = stable_song_id(song, salt="rb2")
    has_vocals = bool(song.vocal_notes)
    has_guitar = bool(song.guitar_notes)
    has_bass = bool(song.bass_notes)
    has_drums = bool(song.drum_notes)
    if album_art is None:
        album_art = True
    preview_start = max(0, int(song.preview_start_ms or 0))
    rating = _int_or(_ini(song, "rating"), 2)
    rating = rating if 1 <= rating <= 4 else 2
    track_number = max(1, _int_or(_ini(song, "album_track"), 1))
    gender = ""
    if has_vocals and _ini(song, "vocal_gender"):
        gender = "\n   (vocal_gender %s)" % _vocal_gender(song)
    band = any([has_drums, has_guitar, has_bass, has_vocals])
    return f"""({shortname}
   (name "{_q(song.title)}")
   (artist "{_q(song.artist)}")
   (master TRUE)
   (context 2000)
   (song
      (name "songs/{shortname}/{shortname}")
      (tracks
         ((guitar (0 1))
          (bass (0 1))
          (drum (0 1))
          (vocals (0 1))
         )
      )
      (vocal_parts {1 if has_vocals else 0})
      (pans (-1.0 1.0))
      (vols (-1.5 -1.5))
      (cores (-1 -1))
      (drum_solo
         (seqs (kick.cue snare.cue tom1.cue tom2.cue crash.cue))
      )
      (drum_freestyle
         (seqs (kick.cue snare.cue hat.cue ride.cue crash.cue))
      )
      (midi_file "songs/{shortname}/{shortname}.mid")
   )
   (song_scroll_speed 2300)
   (bank "sfx/tambourine_bank.milo")
   (anim_tempo kTempoMedium)
   (preview {preview_start} {preview_start + 30000})
   (rank
      (drum {rank_value("drum", song.diff_drums, has_drums)})
      (guitar {rank_value("guitar", song.diff_guitar, has_guitar)})
      (bass {rank_value("bass", song.diff_bass, has_bass)})
      (vocals {rank_value("vocals", song.diff_vocals, has_vocals)})
      (band {rank_value("band", song.diff_band, band)})
   )
   (genre {rb3_genre(song.genre)})
   (decade {rb2_decade(song.year)}){gender}
   (format 4)
   (version 1)
   (fake FALSE)
   (downloaded TRUE)
   (game_origin rb2)
   (song_id {song_id})
   (rating {rating})
   (short_version 0)
   (album_art {"TRUE" if album_art else "FALSE"})
   (year_released {_int_or(song.year, 2010)})
   (album_name "{_q(song.album)}")
   (album_track_number {track_number})
   (base_points 500000)
)
"""


def write_rb3_song_files(song: ChartSong, songs_dir: str, shortname: str,
                         song_id: int = None, audio_source_path: str = None,
                         total_duration_ms: int = 180000, with_art: bool = True,
                         multitrack: bool = True,
                         edat_folder: Optional[str] = None,
                         art_format: str = "ps3") -> Tuple[str, Optional[AudioLayout]]:
    """Grava songs/<s>/<s>.mid, <s>.mogg e gen/<s>_keep.png_<art_format> ("ps3" ou "xbox")
    dentro de `songs_dir`.

    Com `edat_folder` (a pasta em USRDIR/), grava <s>.mid.edat cifrado para o PS3 no
    lugar do .mid solto (klicensee e content id derivados dessa pasta).

    Devolve (bloco do songs.dta, layout do .mogg ou None se não houver áudio).
    O songs.dta em si é gravado por quem chama (um bloco por música do pacote)."""
    track_dir = os.path.join(songs_dir, shortname)
    os.makedirs(track_dir, exist_ok=True)

    # 1. Áudio: .mogg 0x0A Vorbis 44100 Hz, multicanal quando há stems
    layout = build_rb_mogg(song, os.path.join(track_dir, f"{shortname}.mogg"),
                           audio_source_path=audio_source_path, multitrack=multitrack)

    # 2. MIDI só com trilhas do Rock Band e mix de bateria coerente com o .mogg
    drum_mix = layout.drum_mix if layout is not None else 0
    mid = generate_rbn_midi(song, total_duration_ms=total_duration_ms,
                            rock_band_only=True, drum_mix=drum_mix if song.drum_notes else None)
    if edat_folder:
        import io
        from src.creator.edat import write_rock_band_mid_edat
        buf = io.BytesIO()
        mid.save(file=buf)
        write_rock_band_mid_edat(buf.getvalue(), os.path.join(track_dir, f"{shortname}.mid.edat"),
                                 edat_folder)
    else:
        save_midi(mid, os.path.join(track_dir, f"{shortname}.mid"))

    # 3. Capa do álbum (gen/<s>_keep.png_ps3 / .png_xbox), da capa da música ou a padrão
    has_art = None   # sem capa (PS4): album_art segue a existência da capa
    if with_art:
        art = os.path.join(track_dir, "gen", f"{shortname}_keep.png_{art_format}")
        if art_format == "xbox":
            has_art = write_album_art_xbox(song, art)
        else:
            has_art = write_album_art_ps3(song, art)

    length = audio_length_ms(song) or song.get_effective_duration_ms()
    dta = generate_songs_dta_content(song, shortname, song_id=song_id, layout=layout,
                                     song_length_ms=length, album_art=has_art)
    return dta, layout


def write_album_art_ps3(song: ChartSong, dest_path: str) -> bool:
    """Gera a capa png_ps3 a partir de song.album_art_path (ou da capa padrão)."""
    from src.creator.png_ps3 import write_png_ps3
    return _write_album_art(song, dest_path, write_png_ps3)


def write_album_art_xbox(song: ChartSong, dest_path: str) -> bool:
    """Gera a capa png_xbox a partir de song.album_art_path (ou da capa padrão)."""
    from src.creator.png_xbox import write_png_xbox
    return _write_album_art(song, dest_path, write_png_xbox)


def _write_album_art(song: ChartSong, dest_path: str, writer) -> bool:
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    src = song.album_art_path if song.album_art_path and os.path.exists(song.album_art_path) else None
    if src is None:
        import tempfile
        from src.creator.clonehero_exporter import _create_default_album_art
        fd, tmp = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        try:
            _create_default_album_art(tmp, song.title, song.artist)
            return writer(tmp, dest_path)
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass
    return writer(src, dest_path)


def write_songs_dta(path: str, blocks: List[str]):
    """Grava o songs.dta em UTF-8 (LF), coerente com `(encoding utf8)`."""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(blocks))


def export_rb3_song_package(song: ChartSong, output_base_dir: str, audio_source_path: str = None, total_duration_ms: int = 180000) -> str:
    """
    Exporta a estrutura completa de arquivos para Rock Band 3 (layout dos pacotes PS3 reais):
    USRDIR/<pasta única>/songs/songs.dta
    USRDIR/<pasta única>/songs/{shortname}/{shortname}.mid.edat (cifrado para a pasta única)
    USRDIR/<pasta única>/songs/{shortname}/{shortname}.mogg (0x0A, multicanal com stems)
    USRDIR/<pasta única>/songs/{shortname}/gen/{shortname}_keep.png_ps3
    Retorna o diretório base criado.
    """
    clean_shortname = song_shortname(song)
    song_id = stable_song_id(song)
    folder = ps3_folder_name(clean_shortname, song_id)

    rb3_root = os.path.join(output_base_dir, f"RB3_{clean_shortname}")
    songs_dir = os.path.join(rb3_root, "USRDIR", folder, "songs")
    os.makedirs(songs_dir, exist_ok=True)

    dta_content, _layout = write_rb3_song_files(song, songs_dir, clean_shortname, song_id=song_id,
                                                audio_source_path=audio_source_path,
                                                total_duration_ms=total_duration_ms,
                                                edat_folder=folder)
    write_songs_dta(os.path.join(songs_dir, "songs.dta"), [dta_content])

    readme_path = os.path.join(rb3_root, "COMO_JOGAR_NO_RB3.txt")
    readme_content = f"""============================================================
MidGuitar Studio - Pacote Rock Band 3 Pronto!
Música: {song.title} - {song.artist}
============================================================

Estrutura gerada (igual à dos pacotes PS3 reais):
- USRDIR/{folder}/songs/songs.dta (Definições Harmonix)
- USRDIR/{folder}/songs/{clean_shortname}/{clean_shortname}.mid.edat (Trilhas RBN cifradas para o PS3)
- USRDIR/{folder}/songs/{clean_shortname}/{clean_shortname}.mogg (Áudio Harmonix 0x0A, 44100 Hz)
- USRDIR/{folder}/songs/{clean_shortname}/gen/{clean_shortname}_keep.png_ps3 (Capa)

Como jogar no RPCS3 (Emulador de PS3):
1. Copie a pasta 'USRDIR/{folder}' inteira para dentro da pasta do jogo no RPCS3:
   dev_hdd0/game/{RB3_PS3_TITLE_ID}/USRDIR/
   (cada música fica na própria pasta e não sobrescreve as outras)
2. Inicie o Rock Band 3 e a música aparecerá na biblioteca.

Observação: o .mid.edat é cifrado com a chave da pasta '{folder}'; não renomeie a pasta.
============================================================
"""
    with open(readme_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(readme_content)

    return rb3_root
