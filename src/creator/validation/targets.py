"""Validação por destino: combina regras de MIDI/DTA/MOGG com o layout de pastas
que cada JOGO exige (não o que os exportadores atuais geram)."""
import configparser
import os
from typing import Dict, List, Optional, Set

from src.creator.validation.dta_rules import dta_song_entries, validate_dta
from src.creator.validation.issues import Issue
from src.creator.validation.midi_rules import midi_track_names, validate_midi
from src.creator.validation.mogg_rules import read_mogg_info, validate_mogg
from src.creator.validation.profiles import PROFILES

_CH_AUDIO_BASES = {"song", "guitar", "bass", "rhythm", "drums", "drums_1", "drums_2",
                   "drums_3", "drums_4", "vocals", "vocals_1", "vocals_2", "keys", "crowd"}
_CH_AUDIO_EXTS = {".ogg", ".opus", ".mp3", ".wav"}
_XBOX_MSG = ("o Xbox 360 exige um pacote CON/LIVE; pastas soltas só funcionam em "
             "Xenia/Aurora com plugins")


def _rel(folder: str, path: str) -> str:
    try:
        return os.path.relpath(path, folder).replace("\\", "/")
    except ValueError:
        return path


def _walk_files(folder: str):
    for root, _dirs, files in os.walk(folder):
        for f in files:
            yield os.path.join(root, f)


def _find_songs_dtas(folder: str) -> List[str]:
    """Todo `songs/songs.dta` (pai chamado `songs`) abaixo de `folder`."""
    found = []
    for root, _dirs, files in os.walk(folder):
        if os.path.basename(root).lower() == "songs" and "songs.dta" in files:
            found.append(os.path.join(root, "songs.dta"))
    return sorted(found)


def _is_con_package(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            return f.read(4) in (b"CON ", b"LIVE")
    except OSError:
        return False


def _find_con_packages(folder: str) -> List[str]:
    return [p for p in _walk_files(folder) if _is_con_package(p)]


def detect_target(folder: str) -> Optional[str]:
    """Adivinha o destino pela estrutura da pasta (rb2 nunca é detectado)."""
    try:
        if not os.path.isdir(folder):
            return None
        names = set(os.listdir(folder))
        if "song.ini" in names or "notes.mid" in names or "notes.chart" in names:
            return "clonehero"
        if _find_songs_dtas(folder):
            return "rb3_ps3"
        if any(p.lower().endswith(".songdta_ps4") for p in _walk_files(folder)):
            return "ps4"
        if _find_con_packages(folder):
            return "xbox360"
    except Exception:
        pass
    return None


def validate_export(folder: str, target: str) -> List[Issue]:
    """Valida a pasta exportada para o destino. Nunca lança exceção."""
    profile = PROFILES.get(target)
    if profile is None:
        return [Issue("error", "TARGET_UNKNOWN",
                      "Destino desconhecido: %s (válidos: %s)"
                      % (target, ", ".join(sorted(PROFILES))))]
    try:
        if target == "clonehero":
            issues = _validate_clonehero(folder, profile)
        elif target in ("rb3_ps3", "rb2"):
            issues = _validate_ps3_like(folder, profile)
        elif target == "xbox360":
            issues = _validate_xbox(folder)
        else:
            issues = _validate_ps4(folder)
        if not profile.verified_in_game:
            issues.append(Issue("warning", "PROFILE_UNVERIFIED",
                                "Perfil %s ainda não foi confirmado em jogo real" % profile.label))
        return issues
    except Exception as e:
        return [Issue("error", "VALIDATOR_CRASH", "Falha interna no validador: %s" % e)]


def _guard(fn, *args) -> List[Issue]:
    """Roda uma sub-validação sem deixar que uma falha esconda as demais."""
    try:
        return fn(*args)
    except Exception as e:
        return [Issue("error", "VALIDATOR_CRASH", "Falha interna no validador: %s" % e)]


def _validate_clonehero(folder: str, profile) -> List[Issue]:
    issues: List[Issue] = []
    if not os.path.isdir(folder):
        return [Issue("error", "LAYOUT_MISSING_CHART",
                      "Pasta inexistente ou sem notes.mid/notes.chart", folder)]
    names = os.listdir(folder)
    lower = {n.lower(): n for n in names}
    mid = lower.get("notes.mid")
    if not mid and "notes.chart" not in lower:
        issues.append(Issue("error", "LAYOUT_MISSING_CHART",
                            "Faltando notes.mid ou notes.chart na pasta da música"))

    ini = lower.get("song.ini")
    if not ini:
        issues.append(Issue("error", "CH_INI_MISSING", "Faltando song.ini", "song.ini"))
    else:
        cp = configparser.ConfigParser(interpolation=None, strict=False)
        cp.optionxform = str.lower
        try:
            with open(os.path.join(folder, ini), "rb") as f:
                text = f.read().decode("utf-8-sig", errors="replace")
            cp.read_string(text)
        except Exception as e:
            issues.append(Issue("error", "CH_INI_MISSING",
                                "song.ini ilegível: %s" % e, ini))
            cp = None
        if cp is not None:
            section = next((s for s in cp.sections() if s.lower() == "song"), None)
            if section is None:
                issues.append(Issue("error", "CH_INI_MISSING",
                                    "song.ini sem a seção [song]", ini))
            else:
                for key in ("name", "artist"):
                    if not cp.get(section, key, fallback="").strip():
                        issues.append(Issue("warning", "CH_INI_FIELD",
                                            "song.ini sem a chave '%s'" % key, ini))

    has_audio = any(os.path.splitext(n)[0].lower() in _CH_AUDIO_BASES
                    and os.path.splitext(n)[1].lower() in _CH_AUDIO_EXTS for n in names)
    if not has_audio:
        issues.append(Issue("error", "CH_NO_AUDIO",
                            "Nenhum áudio (song, guitar, drums... em .ogg/.opus/.mp3/.wav)"))
    if mid:
        issues.extend(_guard(validate_midi, os.path.join(folder, mid), profile))
    return issues


def _validate_ps3_like(folder: str, profile) -> List[Issue]:
    dtas = _find_songs_dtas(folder) if os.path.isdir(folder) else []
    if not dtas:
        return [Issue("error", "LAYOUT_MISSING_SONG_DIR",
                      "Não foi encontrado songs/songs.dta abaixo da pasta")]
    issues: List[Issue] = []
    for dta in dtas:
        issues.extend(_guard(_validate_one_songs_dir, folder, dta, profile))
    return issues


def _album_art_disabled(entry: list) -> bool:
    for item in entry:
        if isinstance(item, list) and item and item[0] == "album_art":
            return len(item) > 1 and str(item[1]).upper() == "FALSE"
    return False


def _rel_loc(folder: str, dta: str, location: str) -> str:
    """Troca o nome do arquivo (início da localização) pelo caminho relativo."""
    base = os.path.basename(dta)
    if location == base or location.startswith(base + " "):
        return _rel(folder, dta) + location[len(base):]
    return location


def _validate_one_songs_dir(folder: str, dta: str, profile) -> List[Issue]:
    songs_dir = os.path.dirname(dta)
    entries = dta_song_entries(dta)
    midi_tracks: Dict[str, Set[str]] = {}
    mogg_channels: Dict[str, Optional[int]] = {}
    issues: List[Issue] = []

    for entry in entries:
        issues.extend(_guard(_validate_song_files, folder, songs_dir, entry, profile,
                             midi_tracks, mogg_channels))

    for i in _guard(validate_dta, dta, profile, midi_tracks, mogg_channels):
        issues.append(Issue(i.level, i.code, i.message, _rel_loc(folder, dta, i.location)))
    return issues


def _validate_song_files(folder, songs_dir, entry, profile, midi_tracks, mogg_channels):
    s = str(entry[0])
    sdir = os.path.join(songs_dir, s)
    issues: List[Issue] = []
    if not os.path.isdir(sdir):
        return [Issue("error", "LAYOUT_MISSING_SONG_DIR",
                      "Faltando a pasta songs/%s/" % s, _rel(folder, sdir))]
    edat = os.path.join(sdir, s + ".mid.edat")
    mid = os.path.join(sdir, s + ".mid")
    if os.path.isfile(edat):
        try:
            with open(edat, "rb") as f:
                if f.read(4) != b"NPD\x00":
                    issues.append(Issue("error", "PS3_BAD_EDAT",
                                        "O .mid.edat não começa com NPD", _rel(folder, edat)))
        except OSError as e:
            issues.append(Issue("error", "PS3_BAD_EDAT",
                                "Não foi possível ler o .mid.edat: %s" % e, _rel(folder, edat)))
    else:
        issues.append(Issue("error", "PS3_MISSING_EDAT",
                            "Faltando %s.mid.edat" % s, _rel(folder, edat)))
    if os.path.isfile(mid):
        if not os.path.isfile(edat):
            issues.append(Issue("error", "PS3_PLAIN_MID",
                                "Só há %s.mid solto: o PS3 exige .mid.edat" % s,
                                _rel(folder, mid)))
        for i in _guard(validate_midi, mid, profile):
            loc = i.location
            if loc == s + ".mid" or loc.startswith(s + ".mid "):
                loc = _rel(folder, mid) + loc[len(s + ".mid"):]
            issues.append(Issue(i.level, i.code, i.message, loc))
        tracks = midi_track_names(mid)
        if tracks:
            midi_tracks[s] = tracks

    mogg = os.path.join(sdir, s + ".mogg")
    if not os.path.isfile(mogg):
        issues.append(Issue("error", "LAYOUT_MISSING_MOGG",
                            "Faltando %s.mogg" % s, _rel(folder, mogg)))
    else:
        info = read_mogg_info(mogg)
        mogg_channels[s] = info.channels if info else None
        for i in _guard(validate_mogg, mogg):
            issues.append(Issue(i.level, i.code, i.message, _rel(folder, mogg)))

    gen = os.path.join(sdir, "gen")
    milo = os.path.join(gen, s + ".milo_ps3")
    if not os.path.isfile(milo):
        issues.append(Issue("warning", "PS3_MISSING_MILO",
                            "Faltando gen/%s.milo_ps3" % s, _rel(folder, milo)))
    art = os.path.join(gen, s + "_keep.png_ps3")
    if not _album_art_disabled(entry) and not os.path.isfile(art):
        issues.append(Issue("warning", "PS3_MISSING_ART",
                            "Faltando gen/%s_keep.png_ps3" % s, _rel(folder, art)))
    return issues


def _validate_xbox(folder: str) -> List[Issue]:
    if os.path.isdir(folder) and _find_con_packages(folder):
        return []
    return [Issue("error", "XBOX_NO_CON_PACKAGE", _XBOX_MSG)]


def _validate_ps4(folder: str) -> List[Issue]:
    songdtas = [p for p in _walk_files(folder)
                if p.lower().endswith(".songdta_ps4")] if os.path.isdir(folder) else []
    if not songdtas:
        return [Issue("error", "PS4_NO_SONGDTA", "Nenhum arquivo *.songdta_ps4 encontrado")]
    issues: List[Issue] = []
    for p in sorted(songdtas):
        issues.extend(_guard(_validate_ps4_song, folder, p))
    return issues


def _validate_ps4_song(folder: str, songdta: str) -> List[Issue]:
    d = os.path.dirname(songdta)
    s = os.path.basename(songdta)[:-len(".songdta_ps4")]
    issues: List[Issue] = []
    for ext, level, code in ((".rbmid_ps4", "error", "PS4_MISSING_RBMID"),
                             (".mogg", "error", "LAYOUT_MISSING_MOGG"),
                             (".moggsong", "error", "PS4_MISSING_MOGGSONG"),
                             (".png_ps4", "warning", "PS4_MISSING_ART")):
        path = os.path.join(d, s + ext)
        if not os.path.isfile(path):
            issues.append(Issue(level, code, "Faltando %s%s" % (s, ext), _rel(folder, path)))
    mogg = os.path.join(d, s + ".mogg")
    if os.path.isfile(mogg):
        for i in _guard(validate_mogg, mogg):
            issues.append(Issue(i.level, i.code, i.message, _rel(folder, mogg)))
    return issues
