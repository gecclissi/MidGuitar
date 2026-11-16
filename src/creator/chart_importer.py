"""
Importador e Conversor de Músicas (Charts).
Lê pastas e arquivos de músicas do Clone Hero, Phase Shift, FoFiX, Chorus Encore e C3,
carregando metadados (song.ini), trilhas MIDI (notes.mid) e arquivos de áudio.
Permite converter qualquer música baixada para Rock Band 3 ou Clone Hero em 1 clique!
"""

import os
import configparser
import mido
from mido import MidiFile
from src.creator.chart_model import ChartSong, NoteEvent, TextEvent
from src.creator.rbn_specs import FRET_NOTES, DRUM_NOTES, TICKS_PER_BEAT
from src.creator.tempo_map import TempoMap, TempoChange, TimeSigChange

# song.ini: ranking de dificuldade -> atributo do ChartSong
INI_DIFF_KEYS = {
    "diff_guitar": "diff_guitar", "diff_bass": "diff_bass", "diff_drums": "diff_drums",
    "diff_keys": "diff_keys", "diff_vocals": "diff_vocals", "diff_band": "diff_band",
    "diff_guitar_real": "diff_pro_guitar", "diff_bass_real": "diff_pro_bass",
    "diff_keys_real": "diff_pro_keys",
}
# Chaves que o MidGuitar gera a partir do modelo (o valor do modelo vence na exportação)
INI_MANAGED_KEYS = {"name", "artist", "album", "genre", "year", "charter", "song_length",
                    "preview_start_time"} | set(INI_DIFF_KEYS)


def parse_song_ini(ini_path: str) -> dict:
    """Lê os metadados do song.ini."""
    config = configparser.ConfigParser(interpolation=None)
    metadata = {}
    try:
        config.read(ini_path, encoding="utf-8-sig")
        section = "song" if config.has_section("song") else config.sections()[0] if config.sections() else None
        if section:
            for k, v in config.items(section):
                metadata[k.lower()] = v
    except Exception as e:
        print(f"[ChartImporter] Erro ao ler song.ini: {e}")
    return metadata

class UnsupportedFormatError(Exception):
    """A pasta é de um formato que o MidGuitar ainda não sabe importar (mensagem em português)."""


GHWTDE_MESSAGE = ("Formato GHWT:DE ainda não suportado: os mods do Guitar Hero World Tour: "
                  "Definitive Edition (.pak.xen / .fsb.xen, song.ini com [ModInfo]/[SongInfo]) "
                  "usam outro formato e não podem ser importados. Use uma música do Clone Hero / "
                  "YARG (notes.mid ou notes.chart) ou do Rock Band.")


def is_ghwtde_folder(folder_path: str) -> bool:
    """Pasta de mod do GHWT:DE: arquivos .pak.xen/.fsb.xen, ou song.ini sem [song] que
    tem [ModInfo]/[SongInfo] (e nenhum notes.mid/notes.chart de Clone Hero)."""
    try:
        if not os.path.isdir(folder_path):
            return False
        names = {n.lower() for n in os.listdir(folder_path)}
        if "notes.mid" in names or "notes.chart" in names:
            return False
        for _root, _dirs, files in os.walk(folder_path):
            if any(f.lower().endswith((".pak.xen", ".fsb.xen")) for f in files):
                return True
        if "song.ini" in names:
            cp = configparser.ConfigParser(interpolation=None, strict=False)
            cp.read(os.path.join(folder_path, [n for n in os.listdir(folder_path)
                                               if n.lower() == "song.ini"][0]), encoding="utf-8-sig")
            sections = {x.lower() for x in cp.sections()}
            return "song" not in sections and bool(sections & {"modinfo", "songinfo"})
    except Exception:
        pass
    return False


def import_song_from_folder(folder_path: str) -> ChartSong:
    """
    Importa uma pasta completa de música contendo notes.mid, song.ini e áudio.

    Também aceita um .pkg do PS3, um pacote CON/LIVE do Xbox 360 (qualquer nome, pelo
    magic), a raiz de um pacote PS3 ou Xbox extraído, a pasta songs/ de um pacote Rock Band
    e arquivos soltos (.mid, .mid.edat, .chart): nesses casos a pasta da primeira música é
    localizada automaticamente.
    """
    if os.path.isfile(folder_path):
        if folder_path.lower().endswith(".pkg"):
            return import_song_from_pkg(folder_path)
        from src.creator.xbox_stfs import is_stfs_file
        if is_stfs_file(folder_path):
            return import_song_from_con(folder_path)
        folder_path = os.path.dirname(os.path.abspath(folder_path))
    if is_ghwtde_folder(folder_path):
        raise UnsupportedFormatError(GHWTDE_MESSAGE)
    warnings = []
    # sem barra final: o songs.dta é procurado na pasta pai
    folder_path = _resolve_song_dir(os.path.normpath(folder_path), warnings)
    song = ChartSong()
    song.import_warnings.extend(warnings)
    dta_layout = {}   # canais do .mogg declarados no songs.dta (tracks, pans, vols)

    # 1. Busca song.ini
    ini_file = os.path.join(folder_path, "song.ini")
    if os.path.exists(ini_file):
        meta = parse_song_ini(ini_file)
        song.title = meta.get("name", song.title)
        song.artist = meta.get("artist", song.artist)
        song.album = meta.get("album", song.album)
        song.genre = meta.get("genre", song.genre)
        song.charter = meta.get("charter", song.charter)
        try:
            song.year = int(meta.get("year", song.year))
        except Exception:
            pass
        for key, attr in INI_DIFF_KEYS.items():
            try:
                setattr(song, attr, max(0, int(meta.get(key, getattr(song, attr)))))
            except Exception:
                pass
        try:
            song.preview_start_ms = max(0, int(float(meta.get("preview_start_time", song.preview_start_ms))))
        except Exception:
            pass
        # Chaves que o modelo não usa (preview_end_time, pro_drums, diff_*_real...) voltam na exportação
        song.ini_extra = {k: v for k, v in meta.items() if k not in INI_MANAGED_KEYS}
    else:
        # 1.1 songs.dta de Rock Band 2 / 3 (formato real: multi-linha, chaves entre aspas)
        for dta_p in [os.path.join(folder_path, "songs.dta"),
                      os.path.join(os.path.dirname(folder_path), "songs.dta")]:
            if os.path.exists(dta_p):
                try:
                    dta_layout = _apply_songs_dta(song, dta_p, os.path.basename(folder_path)) or {}
                    break
                except Exception as e:
                    print(f"[ChartImporter] Erro ao ler songs.dta {dta_p}: {e}")

    # 1.2 Busca imagem de capa (album.png, cover.png, ICON0.PNG)
    for f in os.listdir(folder_path):
        f_lower = f.lower()
        if f_lower in ["album.png", "album.jpg", "album.jpeg", "cover.png", "cover.jpg", "icon0.png"]:
            song.album_art_path = os.path.join(folder_path, f)
            break
    if not song.album_art_path:
        song.album_art_path = _decode_rb_album_art(folder_path) or song.album_art_path

    # 2. Busca arquivos de áudio (Stems individuais, mixagem geral ou .mogg oficial do RB3)
    for f in os.listdir(folder_path):
        f_lower = f.lower()
        full_p = os.path.join(folder_path, f)
        if f_lower.endswith(".mogg"):
            _import_mogg_audio(song, full_p, folder_path, dta_layout)
            continue
        elif f_lower.endswith((".ogg", ".mp3", ".wav", ".flac", ".opus")):
            song.audio_stems.append(full_p)
            stem_base = os.path.splitext(f_lower)[0]
            if stem_base in ["song", "guitar", "audio"] and not song.audio_path:
                song.audio_path = full_p

    if not song.audio_path and song.audio_stems:
        song.audio_path = song.audio_stems[0]

    # 3. Busca arquivos de letra (.txt / .lrc / .srt)
    for f in os.listdir(folder_path):
        f_lower = f.lower()
        if f_lower in ["lyrics.txt", "song.lrc", "lyrics.lrc", "letra.txt", "words.txt", "lyrics.srt", "song.srt"] or f_lower.endswith((".lrc", ".srt")):
            try:
                with open(os.path.join(folder_path, f), "r", encoding="utf-8-sig", errors="ignore") as lf:
                    song.lyrics_raw = lf.read()
                    break
            except Exception:
                pass

    # 4. Busca e analisa notes.mid ou notes.chart
    mid_file = os.path.join(folder_path, "notes.mid")
    if not os.path.exists(mid_file):
        for f in os.listdir(folder_path):
            if f.lower().endswith(".mid"):
                mid_file = os.path.join(folder_path, f)
                break

    chart_file = os.path.join(folder_path, "notes.chart")
    if not os.path.exists(chart_file):
        for f in os.listdir(folder_path):
            if f.lower().endswith(".chart"):
                chart_file = os.path.join(folder_path, f)
                break

    edat_file = None
    if not os.path.exists(mid_file):
        for f in sorted(os.listdir(folder_path)):
            if f.lower().endswith(".mid.edat"):
                edat_file = os.path.join(folder_path, f)
                break

    if os.path.exists(mid_file):
        try:
            mid = MidiFile(mid_file)
            _parse_midi_into_song(mid, song)
        except Exception as e:
            print(f"[ChartImporter] Erro ao analisar MIDI {mid_file}: {e}")
    elif edat_file:
        # .mid.edat do PS3: decifra em memória (klicensee verificada pelos hashes do NPD)
        try:
            import io
            from src.creator.edat import read_rock_band_mid_edat
            mid = MidiFile(file=io.BytesIO(read_rock_band_mid_edat(edat_file)))
            _parse_midi_into_song(mid, song)
        except Exception as e:
            song.import_warnings.append(
                f"Não foi possível decifrar '{os.path.basename(edat_file)}': {e}")
            print(f"[ChartImporter] Erro ao decifrar {edat_file}: {e}")
    elif os.path.exists(chart_file):
        try:
            _parse_chart_file_into_song(chart_file, song)
        except Exception as e:
            print(f"[ChartImporter] Erro ao analisar CHART {chart_file}: {e}")

    # Se carregou lyrics_raw mas não tinha vocal_notes, aplica alinhamento automático
    if song.lyrics_raw and not song.vocal_notes:
        from src.creator.lyric_processor import align_lyrics_to_song
        align_lyrics_to_song(song, song.lyrics_raw)

    # Garante que todas as 4 dificuldades existam para qualquer instrumento carregado
    from src.creator.auto_charter import recalculate_track_difficulties
    for inst_key in ["guitar", "bass", "drum", "keys"]:
        notes_list = getattr(song, f"{inst_key}_notes", [])
        if notes_list and not any(n.difficulty in ["Hard", "Medium", "Easy"] for n in notes_list):
            recalculate_track_difficulties(song, [inst_key])

    return song


_CHART_FILE_EXTS = (".mid", ".mid.edat", ".chart")

# rank do songs.dta -> atributo de dificuldade (0-6) do ChartSong
_DTA_RANK_ATTRS = {
    "drum": "diff_drums", "guitar": "diff_guitar", "bass": "diff_bass",
    "vocals": "diff_vocals", "keys": "diff_keys", "real_guitar": "diff_pro_guitar",
    "real_bass": "diff_pro_bass", "real_keys": "diff_pro_keys", "band": "diff_band",
}


def _has_chart_files(folder: str) -> bool:
    try:
        names = os.listdir(folder)
    except OSError:
        return False
    return any(n.lower() in ("song.ini", "notes.mid", "notes.chart") or n.lower().endswith(_CHART_FILE_EXTS)
               for n in names if os.path.isfile(os.path.join(folder, n)))


def find_rb_song_dirs(root: str) -> list:
    """Pastas songs/<s>/ com .mid ou .mid.edat abaixo de `root` (pacote RB / PS3)."""
    found = []
    for dirpath, dirnames, files in os.walk(root):
        dirnames.sort()
        if "songs.dta" not in (f.lower() for f in files):
            continue
        for name in sorted(os.listdir(dirpath)):
            sub = os.path.join(dirpath, name)
            if os.path.isdir(sub) and any(f.lower().endswith((".mid", ".mid.edat"))
                                          for f in os.listdir(sub)):
                found.append(sub)
    return found


def _resolve_song_dir(folder: str, warnings: list) -> str:
    """Aponta para a pasta da música quando `folder` é a raiz de um pacote ou songs/."""
    if not os.path.isdir(folder) or _has_chart_files(folder):
        return folder
    dirs = find_rb_song_dirs(folder)
    if not dirs:
        return folder
    if len(dirs) > 1:
        warnings.append(f"O pacote tem {len(dirs)} músicas; só a primeira "
                        f"('{os.path.basename(dirs[0])}') foi importada.")
    return dirs[0]


def _import_mogg_audio(song: ChartSong, mogg_path: str, folder_path: str, dta_layout: dict):
    """Descriptografa o .mogg (se preciso) para o cache: mix em audio_path, stems por
    instrumento e o Ogg multicanal em song.source_mogg. Versão sem suporte: sem áudio + aviso."""
    from src.creator.mogg_crypt import MoggCryptError, mogg_version
    from src.creator.mogg_import import mogg_cache_dir, prepare_mogg_audio
    name = os.path.basename(mogg_path)
    if song.audio_path:
        return
    try:
        audio = prepare_mogg_audio(mogg_path, mogg_cache_dir(), dta_layout)
    except MoggCryptError as e:
        version = mogg_version(mogg_path)
        song.import_warnings.append(
            f"O áudio '{name}' está criptografado (versão {version}) e não pôde ser importado ({e}). "
            "A música foi carregada sem áudio: escolha um MP3/OGG/WAV antes de exportar.")
        return
    except Exception as e:
        song.import_warnings.append(f"Não foi possível ler o áudio '{name}': {e}")
        print(f"[ChartImporter] Erro ao importar {mogg_path}: {e}")
        return
    song.audio_path = audio["mix"]
    song.audio_stems.extend(p for p in audio["stems"] if p not in song.audio_stems)
    song.source_mogg = dict(audio)


def import_song_from_pkg(pkg_path: str) -> ChartSong:
    """Importa a (primeira) música de um .pkg de debug do PS3 (customs do Rock Band).
    O pacote é extraído numa pasta temporária; o .mid.edat é decifrado em memória."""
    from src.creator.mogg_generator import extraction_cache_dir
    from src.creator.ps3_pkg import extract_pkg
    from src.creator.mogg_import import file_cache_key
    # Tamanho + data do .pkg na pasta: um .pkg trocado no mesmo caminho não reaproveita o cache
    cache = os.path.join(extraction_cache_dir(os.path.abspath(pkg_path)),
                         "pkg_" + file_cache_key(pkg_path))
    # .milo_ps3 (animações) não é usado na importação
    done = os.path.join(cache, ".extraido")
    if not os.path.isfile(done):
        extract_pkg(pkg_path, cache, want=lambda name: not name.lower().endswith(".milo_ps3"))
        with open(done, "w", encoding="utf-8") as f:
            f.write(pkg_path)
    return import_song_from_folder(cache)


def import_song_from_con(con_path: str) -> ChartSong:
    """Importa a (primeira) música de um pacote CON/LIVE do Xbox 360 (STFS).
    O pacote é extraído numa pasta temporária (sem os .milo_xbox)."""
    from src.creator.mogg_generator import extraction_cache_dir
    from src.creator.mogg_import import file_cache_key
    from src.creator.xbox_stfs import StfsPackage
    cache = os.path.join(extraction_cache_dir(os.path.abspath(con_path)),
                         "con_" + file_cache_key(con_path))
    done = os.path.join(cache, ".extraido")
    if not os.path.isfile(done):
        StfsPackage(con_path).extract(cache, want=lambda name: not name.lower().endswith(".milo_xbox"))
        with open(done, "w", encoding="utf-8") as f:
            f.write(con_path)
    return import_song_from_folder(cache)


def _decode_rb_album_art(song_dir: str) -> str:
    """Capa gen/<s>_keep.png_xbox / .png_ps3 convertida para PNG no cache temporário
    (nunca grava na pasta do usuário)."""
    from src.creator.mogg_generator import extraction_cache_dir
    from src.creator.mogg_import import file_cache_key
    gen = os.path.join(song_dir, "gen")
    if not os.path.isdir(gen):
        return ""
    for name in sorted(os.listdir(gen)):
        low = name.lower()
        if not low.endswith(("_keep.png_xbox", "_keep.png_ps3")):
            continue
        src = os.path.join(gen, name)
        try:
            dest = os.path.join(extraction_cache_dir(gen),
                                "%s_%s.png" % (name, file_cache_key(src)))
            if not os.path.isfile(dest):
                from PIL import Image
                with open(src, "rb") as f:
                    data = f.read()
                if low.endswith("_xbox"):
                    from src.creator.png_xbox import decode_png_xbox
                    img = decode_png_xbox(data)
                else:
                    from src.creator.png_ps3 import decode_png_ps3
                    img = decode_png_ps3(data)
                Image.fromarray(img).convert("RGB").save(dest)
            return dest
        except Exception as e:
            print(f"[ChartImporter] Capa {name} ilegível: {e}")
    return ""


def _dta_fields(entry: list, key: str):
    for item in entry:
        if isinstance(item, list) and item and item[0] == key:
            return item[1:]
    return None


def _dta_first(entry: list, key: str):
    v = _dta_fields(entry, key)
    return v[0] if v else None


def _read_dta_text(path: str) -> str:
    """songs.dta em UTF-8 ou latin1, conforme `(encoding ...)` (padrão do RB3: latin1)."""
    import re
    with open(path, "rb") as f:
        raw = f.read()
    m = re.search(rb"\(\s*'?encoding'?\s+'?(\w+)'?\s*\)", raw)
    enc = m.group(1).decode("ascii").lower() if m else "latin1"
    if enc in ("utf8", "utf-8"):
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            pass
    return raw.decode("latin-1")


def _apply_songs_dta(song: ChartSong, dta_path: str, song_dir_name: str):
    """Lê título, artista, álbum, ano, gênero, ranks, preview e song_id do songs.dta."""
    from src.creator.validation.dta_parser import parse_dta
    from src.creator.rb3_dta_exporter import RANK_TIERS
    entries = [e for e in parse_dta(_read_dta_text(dta_path)) if isinstance(e, list) and e]
    if not entries:
        return
    entry = entries[0]
    for e in entries:
        song_f = _dta_fields(e, "song") or []
        name = next((x[1] for x in song_f
                     if isinstance(x, list) and len(x) > 1 and x[0] == "name"), None)
        parts = [p for p in str(name or "").replace("\\", "/").split("/") if p]
        if (len(parts) >= 2 and parts[-2] == song_dir_name) or str(e[0]) == song_dir_name:
            entry = e
            break

    def text(key, default):
        v = _dta_first(entry, key)
        return str(v).replace("\\q", '"') if v is not None and str(v).strip() else default

    song.title = text("name", song.title)
    song.artist = text("artist", song.artist)
    song.album = text("album_name", song.album)
    song.charter = text("author", song.charter)
    genre = _dta_first(entry, "genre")
    if genre:
        song.genre = str(genre).replace("_", " ").title()
    year = _dta_first(entry, "year_released")
    if isinstance(year, int):
        song.year = year
    sid = _dta_first(entry, "song_id")
    if isinstance(sid, int):
        song.dta_song_id = sid
    preview = _dta_fields(entry, "preview")
    if preview and isinstance(preview[0], int):
        song.preview_start_ms = max(0, preview[0])
    length = _dta_first(entry, "song_length")
    if isinstance(length, int) and length > 0:
        song.duration_ms = length
    gender = _dta_first(entry, "vocal_gender")
    if gender:
        song.ini_extra["vocal_gender"] = str(gender)
    for item in _dta_fields(entry, "rank") or []:
        if not (isinstance(item, list) and len(item) > 1 and isinstance(item[1], int)):
            continue
        inst, value = str(item[0]), item[1]
        attr = _DTA_RANK_ATTRS.get(inst)
        if attr and value > 0 and inst in RANK_TIERS:
            setattr(song, attr, sum(1 for th in RANK_TIERS[inst] if value >= th))
    from src.creator.mogg_import import layout_from_dta_song
    return layout_from_dta_song(_dta_fields(entry, "song"))


def _parse_chart_file_into_song(chart_path: str, song: ChartSong):
    """Analisa arquivos notes.chart do Clone Hero / Moonscraper / Feedback.

    Lê metadados de [Song] (quando não há song.ini), mapa de tempo, [Events]
    (seções), notas, star power (S 2 -> overdrive), forçadas (N 5), tap (N 6)
    e open (N 7). Bateria usa as lanes de rbn_specs.DRUM_NOTES.
    """
    import re
    from src.creator import passthrough as pt
    with open(chart_path, "r", encoding="utf-8-sig", errors="ignore") as f:
        text = f.read()

    defaults = ChartSong()
    resolution = 192
    current_section = ""
    tempo_changes = []   # TempoChange em ticks do .chart
    sig_changes = []     # TimeSigChange em ticks do .chart
    pending_notes = []   # (inst, diff, lane, tick, sustain_ticks), convertidos no fim
    flags = {}           # (inst, diff, tick) -> {"forced", "tap"}
    star_power = []      # (inst, tick, length)
    chart_events = []    # (tick, texto)

    section_map = {
        "EXPERTSINGLE": ("guitar", "Expert"),
        "HARDSINGLE": ("guitar", "Hard"),
        "MEDIUMSINGLE": ("guitar", "Medium"),
        "EASYSINGLE": ("guitar", "Easy"),
        "EXPERTDOUBLEBASS": ("bass", "Expert"),
        "HARDDOUBLEBASS": ("bass", "Hard"),
        "MEDIUMDOUBLEBASS": ("bass", "Medium"),
        "EASYDOUBLEBASS": ("bass", "Easy"),
        "EXPERTDRUMS": ("drum", "Expert"),
        "HARDDRUMS": ("drum", "Hard"),
        "MEDIUMDRUMS": ("drum", "Medium"),
        "EASYDRUMS": ("drum", "Easy"),
        "EXPERTKEYBOARD": ("keys", "Expert"),
        "HARDKEYBOARD": ("keys", "Hard"),
        "MEDIUMKEYBOARD": ("keys", "Medium"),
        "EASYKEYBOARD": ("keys", "Easy"),
    }
    fret_idx_to_lane = {0: "green", 1: "red", 2: "yellow", 3: "blue", 4: "orange", 7: "open"}
    # Bateria .chart: 0 bumbo, 1 vermelho, 2 amarelo, 3 azul, 4 verde (4 lanes) /
    # laranja (5 lanes), 5 verde (5 lanes), 32 pedal duplo
    drum_idx_to_lane = {0: "kick", 1: "snare", 2: "yellow", 3: "blue", 4: "green", 5: "green", 32: "double_kick"}

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line in ["{", "}"]:
            continue
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1].strip().upper()
            continue

        if current_section == "SONG":
            if "=" in line:
                k, v = [p.strip().strip('"').strip() for p in line.split("=", 1)]
                kl = k.lower()
                # Valores do .chart só preenchem o que o song.ini não definiu
                if kl == "name" and song.title == defaults.title:
                    song.title = v
                elif kl == "artist" and song.artist == defaults.artist:
                    song.artist = v
                elif kl == "album" and song.album == defaults.album:
                    song.album = v
                elif kl == "genre" and song.genre == defaults.genre:
                    song.genre = v
                elif kl == "charter" and song.charter == defaults.charter:
                    song.charter = v
                elif kl == "year" and song.year == defaults.year:
                    m = re.search(r"\d{4}", v)
                    if m:
                        song.year = int(m.group(0))
                elif kl == "resolution":
                    try:
                        resolution = max(1, int(v))
                    except Exception:
                        pass
        elif current_section == "SYNCTRACK":
            # Ex: 0 = B 120000  /  0 = TS 4  /  1536 = TS 6 3
            m = re.match(r'(\d+)\s*=\s*B\s+(\d+)', line)
            if m and int(m.group(2)) > 0:
                bpm_milli = int(m.group(2))
                us = int(round(60_000_000 / (bpm_milli / 1000.0)))
                tempo_changes.append(TempoChange(int(m.group(1)), us))
                continue
            m = re.match(r'(\d+)\s*=\s*TS\s+(\d+)(?:\s+(\d+))?', line)
            if m:
                den_exp = int(m.group(3)) if m.group(3) is not None else 2
                sig_changes.append(TimeSigChange(int(m.group(1)), int(m.group(2)), 2 ** den_exp))
        elif current_section == "EVENTS":
            # Ex: 768 = E "section Verse 1"  (letras e frases vocais não são seções)
            m = re.match(r'(\d+)\s*=\s*E\s+(.*)$', line)
            if m:
                ev = m.group(2).strip().strip('"').strip()
                if ev and not ev.lower().startswith(("lyric", "phrase_start", "phrase_end")):
                    chart_events.append((int(m.group(1)), ev if ev.startswith("[") else "[%s]" % ev))
        elif current_section in section_map:
            inst, diff = section_map[current_section]
            # Ex: 768 = N 0 0  /  768 = S 2 384
            m = re.match(r'(\d+)\s*=\s*([NS])\s+(\d+)\s+(\d+)', line)
            if not m:
                continue
            tick, kind, idx, length = int(m.group(1)), m.group(2), int(m.group(3)), int(m.group(4))
            if kind == "S":
                if idx == 2:
                    star_power.append((inst, tick, length))
                continue
            lane_map = drum_idx_to_lane if inst == "drum" else fret_idx_to_lane
            if idx in lane_map:
                pending_notes.append((inst, diff, lane_map[idx], tick, length))
            elif inst != "drum" and idx in (5, 6):
                flags.setdefault((inst, diff, tick), set()).add("forced" if idx == 5 else "tap")

    # Monta o mapa de tempo com o arquivo inteiro lido (as seções de notas podem vir antes do SyncTrack)
    tm = TempoMap(resolution, tempo_changes, sig_changes)
    track_names = {"guitar": "PART GUITAR", "bass": "PART BASS", "drum": "PART DRUMS", "keys": "PART KEYS"}

    def extras_for(inst):
        return song.track_extras.setdefault(track_names[inst], pt.new_extras())

    def span_ms(tick, length):
        start_ms = int(round(tm.tick_to_ms(tick)))
        return start_ms, max(0, int(round(tm.tick_to_ms(tick + length))) - start_ms)

    open_insts = set()
    for inst, diff, lane, tick, sustain_ticks in pending_notes:
        if lane == "open":
            # Open (N 7): nota abaixo do verde, com [ENHANCED_OPENS] na trilha
            pitch = FRET_NOTES[diff]["green"] - 1
            pt.add_extra_note(extras_for(inst), tm, tick, tick + max(1, sustain_ticks), pitch, 100, 0)
            open_insts.add(inst)
            continue
        start_ms, dur_ms = span_ms(tick, sustain_ticks)
        song.add_note(inst, NoteEvent(time_ms=start_ms, lane=lane, duration_ms=max(120, dur_ms), difficulty=diff))
    for inst in sorted(open_insts):
        pt.add_extra_event(extras_for(inst), tm, 0, mido.MetaMessage("text", text="[ENHANCED_OPENS]"))

    # Forçadas (N 5 inverte o HOPO natural) e tap (N 6, marcador 104)
    hopo_threshold = resolution * 65 / 192
    groups = {}
    for inst, diff, lane, tick, sustain_ticks in pending_notes:
        groups.setdefault((inst, diff), {}).setdefault(tick, []).append((lane, sustain_ticks))
    taps_done = set()
    for (inst, diff), by_tick in groups.items():
        prev_tick, prev_lanes = None, set()
        for tick in sorted(by_tick):
            lanes = {lane for lane, _s in by_tick[tick]}
            length = max(1, max(s for _l, s in by_tick[tick]))
            natural = (prev_tick is not None and len(lanes) == 1 and tick - prev_tick <= hopo_threshold
                       and not lanes <= prev_lanes)
            f = flags.get((inst, diff, tick), set())
            if "forced" in f:
                marker = FRET_NOTES[diff]["force_strum" if natural else "force_hopo"]
                pt.add_extra_note(extras_for(inst), tm, tick, tick + length, marker, 100, 0)
            if "tap" in f and (inst, tick) not in taps_done:
                taps_done.add((inst, tick))
                pt.add_extra_note(extras_for(inst), tm, tick, tick + length, 104, 100, 0)
            prev_tick, prev_lanes = tick, lanes

    # Star power (S 2) -> frase de overdrive (uma por trilha, mesmo repetida em cada dificuldade)
    for inst, tick, length in sorted(set(star_power)):
        start_ms, dur_ms = span_ms(tick, length)
        song.add_note(inst, NoteEvent(time_ms=start_ms, lane="overdrive", duration_ms=dur_ms,
                                      difficulty="Expert", is_overdrive=True))

    for tick, ev in chart_events:
        song.events.append(TextEvent(time_ms=int(round(tm.tick_to_ms(tick))), text=ev))

    song.tempo_map = tm.rescaled(TICKS_PER_BEAT)
    song.bpm = round(song.tempo_map.initial_bpm(), 2)


# Trilhas de 5 lanes editáveis -> atributo do ChartSong
_FIVE_LANE_TRACKS = {"PART GUITAR": "guitar", "PART BASS": "bass", "PART KEYS": "keys"}
_PRO_KEYS_TRACKS = {"PART REAL_KEYS_X": "Expert", "PART REAL_KEYS_H": "Hard",
                    "PART REAL_KEYS_M": "Medium", "PART REAL_KEYS_E": "Easy"}
# Marcadores de HOPO/palhetada forçados não são notas tocáveis: vão para o passthrough
_FORCED_LANES = ("force_hopo", "force_strum")


def _inverse_map(note_map: dict) -> dict:
    inv = {}
    for diff, lanes in note_map.items():
        for lane, pitch in lanes.items():
            if lane not in _FORCED_LANES:
                inv[pitch] = (lane, diff)
    return inv


def _ms_span(tm: TempoMap, start: int, end: int):
    """(início, duração) em ms inteiros; início + duração = fim arredondado (sem piso)."""
    s = int(round(tm.tick_to_ms(start)))
    return s, max(0, int(round(tm.tick_to_ms(end))) - s)


def _parse_midi_into_song(mid: MidiFile, song: ChartSong):
    """Extrai notas, mapa de tempo, eventos e o passthrough das trilhas do MIDI.

    Trilhas editáveis (PART GUITAR/BASS/DRUMS/KEYS/VOCALS/REAL_*) viram notas do
    modelo; o que o modelo não representa (marcadores, textos, canais, sysex) fica
    em song.track_extras. Trilhas que o MidGuitar não edita ficam inteiras em
    song.passthrough_tracks. Assim importar e exportar não perde nada.
    """
    from src.creator import passthrough as pt
    from src.creator.chart_model import ProGuitarNote, ProKeysNote, VocalNote
    from src.creator.rbn_specs import PRO_GUITAR_STRING_BASE, VOCAL_PITCH_MIN, VOCAL_PITCH_MAX, VOCAL_PHRASE_MARKER

    # Primeira passada: coleta tempos e fórmulas de compasso de TODAS as trilhas
    tempo_changes = []
    sig_changes = []
    for track in mid.tracks:
        abs_tick = 0
        for msg in track:
            abs_tick += msg.time
            if msg.type == 'set_tempo':
                tempo_changes.append(TempoChange(abs_tick, msg.tempo))
            elif msg.type == 'time_signature':
                sig_changes.append(TimeSigChange(abs_tick, msg.numerator, msg.denominator))
    src_tm = TempoMap(mid.ticks_per_beat, tempo_changes, sig_changes)
    song.tempo_map = src_tm.rescaled(TICKS_PER_BEAT)
    song.bpm = round(song.tempo_map.initial_bpm(), 2)
    tm = src_tm  # conversões tick -> ms usam a resolução do arquivo de origem

    inv_fret_notes = _inverse_map(FRET_NOTES)
    inv_drum_notes = _inverse_map(DRUM_NOTES)
    song.passthrough_tracks = []
    song.track_extras = {}

    for idx, track in enumerate(mid.tracks):
        name, notes, others, raw = pt.read_track(track, tm)
        upper = (name or "").strip().upper()

        # Trilha de tempo (1ª trilha do tipo 1, sem notas): o mapa já foi lido
        if idx == 0 and mid.type == 1 and not notes and upper not in pt.EDITABLE_TRACKS and upper != "EVENTS":
            song.tempo_track_name = name
            continue

        if upper == "EVENTS":
            for tick, msg in others:
                if msg.type == 'text':
                    song.events.append(TextEvent(time_ms=int(round(tm.tick_to_ms(tick))), text=msg.text))
            continue

        # Nomes EXATOS: customs reais trazem trilhas extras (PART GUITAR GHL,
        # PART ELITE_DRUMS, PART REAL_GUITAR_22, PART KEYS_ANIM_RH, HARM1...)
        # que não podem ser misturadas nas trilhas editadas pelo MidGuitar.
        if upper not in pt.EDITABLE_TRACKS:
            song.passthrough_tracks.append(pt.raw_track_from_midi(name, raw, tm))
            continue

        extras = pt.new_extras()
        lyrics_at = {}
        for tick, msg in others:
            if upper == "PART VOCALS" and msg.type == 'lyrics':
                lyrics_at.setdefault(tick, []).append(msg)
            else:
                pt.add_extra_event(extras, tm, tick, msg)

        phrase_ends = []
        sung = []
        for start, end, pitch, vel, ch in sorted(notes):
            t_ms, d_ms = _ms_span(tm, start, end)
            consumed = False
            if upper in _FIVE_LANE_TRACKS or upper == "PART DRUMS":
                inv = inv_drum_notes if upper == "PART DRUMS" else inv_fret_notes
                if ch == 0 and pitch in inv:
                    lane, diff = inv[pitch]
                    attr = "drum" if upper == "PART DRUMS" else _FIVE_LANE_TRACKS[upper]
                    getattr(song, f"{attr}_notes").append(NoteEvent(
                        time_ms=t_ms, lane=lane, duration_ms=d_ms, difficulty=diff, velocity=vel))
                    consumed = True
            elif upper == "PART VOCALS":
                if ch == 0 and VOCAL_PITCH_MIN <= pitch <= VOCAL_PITCH_MAX:
                    pending = lyrics_at.get(start)
                    lyric = pending.pop(0).text if pending else ""
                    note = VocalNote(time_ms=t_ms, duration_ms=d_ms, pitch=pitch, lyric=lyric, velocity=vel)
                    song.vocal_notes.append(note)
                    sung.append((start, note))
                    consumed = True
                elif pitch == VOCAL_PHRASE_MARKER:
                    phrase_ends.append(end)
            elif upper in ("PART REAL_GUITAR", "PART REAL_BASS"):
                if vel >= 100:
                    for diff, base_p in PRO_GUITAR_STRING_BASE.items():
                        if base_p <= pitch <= base_p + 5:
                            target = song.pro_bass_notes if upper == "PART REAL_BASS" else song.pro_guitar_notes
                            target.append(ProGuitarNote(
                                time_ms=t_ms, string_idx=pitch - base_p, fret=vel - 100,
                                duration_ms=d_ms, difficulty=diff, channel=ch))
                            consumed = True
                            break
            elif upper in _PRO_KEYS_TRACKS:
                if ch == 0 and 48 <= pitch <= 72:
                    song.pro_keys_notes.append(ProKeysNote(
                        time_ms=t_ms, pitch=pitch, duration_ms=d_ms,
                        difficulty=_PRO_KEYS_TRACKS[upper], velocity=vel))
                    consumed = True
            if not consumed:
                pt.add_extra_note(extras, tm, start, end, pitch, vel, ch)

        # Letras sem nota cantada no mesmo tick também são repassadas
        for tick, msgs in lyrics_at.items():
            for msg in msgs:
                pt.add_extra_event(extras, tm, tick, msg)
        # Fim de frase (nota 105): a última nota cantada que começa dentro da frase
        for p_end in phrase_ends:
            inside = [n for s, n in sung if s < p_end]
            if inside:
                inside[-1].is_phrase_end = True

        # Registrado mesmo vazio: marca a trilha como importada (o gerador não inventa âncoras)
        song.track_extras[upper] = extras

    # Ordena todas as trilhas por tempo
    song.guitar_notes.sort(key=lambda n: n.time_ms)
    song.bass_notes.sort(key=lambda n: n.time_ms)
    song.drum_notes.sort(key=lambda n: n.time_ms)
    song.keys_notes.sort(key=lambda n: n.time_ms)
    song.pro_guitar_notes.sort(key=lambda n: n.time_ms)
    song.pro_bass_notes.sort(key=lambda n: n.time_ms)
    song.pro_keys_notes.sort(key=lambda n: n.time_ms)
    song.vocal_notes.sort(key=lambda n: n.time_ms)
