"""Validação por destino: combina regras de MIDI/DTA/MOGG com o layout de pastas
que cada JOGO exige (não o que os exportadores atuais geram)."""
import codecs
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
        names = {n.lower(): n for n in os.listdir(folder)}
        if "notes.mid" in names or "notes.chart" in names:
            return "clonehero"
        # song.ini sozinho só é Clone Hero com a seção [song]: mods do GHWT:DE
        # também usam song.ini, mas com [ModInfo]/[SongInfo]
        if "song.ini" in names:
            with open(os.path.join(folder, names["song.ini"]), "rb") as f:
                if _parse_song_ini(_decode_ini(f.read())) is not False:
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
            issues = _validate_xbox(folder, profile)
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


def _decode_ini(raw: bytes) -> str:
    if raw.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8-sig", errors="replace")


def _parse_song_ini(text: str):
    """Campos da seção [song] (chaves em minúsculas), ou False se não há a seção.

    Tolerante como o Clone Hero: ignora linhas inválidas e comentários."""
    cp = configparser.ConfigParser(interpolation=None, strict=False, allow_no_value=True)
    cp.optionxform = str.lower
    try:
        cp.read_string(text)
        section = next((s for s in cp.sections() if s.lower() == "song"), None)
        if section is None:
            return False
        return {k: (v or "") for k, v in cp.items(section)}
    except configparser.Error:
        pass
    fields: dict = {}
    in_song = found = False
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            in_song = line[1:-1].strip().lower() == "song"
            found = found or in_song
        elif in_song and "=" in line and not line.startswith(("//", ";", "#")):
            k, _, v = line.partition("=")
            fields.setdefault(k.strip().lower(), v.strip())
    return fields if found else False


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
        try:
            with open(os.path.join(folder, ini), "rb") as f:
                raw = f.read()
            fields = _parse_song_ini(_decode_ini(raw))
        except Exception as e:
            issues.append(Issue("error", "CH_INI_MISSING",
                                "song.ini ilegível: %s" % e, ini))
            fields = None
        if fields is not None:
            if fields is False:
                issues.append(Issue("error", "CH_INI_MISSING",
                                    "song.ini sem a seção [song]", ini))
            else:
                for key in ("name", "artist"):
                    if not fields.get(key, "").strip():
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


def _validate_ps3_like(folder: str, profile, platform: str = "ps3") -> List[Issue]:
    dtas = _find_songs_dtas(folder) if os.path.isdir(folder) else []
    if not dtas:
        return [Issue("error", "LAYOUT_MISSING_SONG_DIR",
                      "Não foi encontrado songs/songs.dta abaixo da pasta")]
    issues: List[Issue] = []
    for dta in dtas:
        issues.extend(_guard(_validate_one_songs_dir, folder, dta, profile, platform))
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


def _validate_one_songs_dir(folder: str, dta: str, profile, platform: str = "ps3") -> List[Issue]:
    songs_dir = os.path.dirname(dta)
    entries = dta_song_entries(dta)
    midi_tracks: Dict[str, Set[str]] = {}
    mogg_channels: Dict[str, Optional[int]] = {}
    issues: List[Issue] = []

    for entry in entries:
        issues.extend(_guard(_validate_song_files, folder, songs_dir, entry, profile,
                             midi_tracks, mogg_channels, platform))

    for i in _guard(validate_dta, dta, profile, midi_tracks, mogg_channels):
        issues.append(Issue(i.level, i.code, i.message, _rel_loc(folder, dta, i.location)))
    return issues


def _song_paths(songs_dir: str, entry: list):
    """(base, pasta) do `song/name` ("songs/<dir>/<base>"); cai no nome da entrada."""
    key = str(entry[0])
    for item in entry:
        if isinstance(item, list) and item and item[0] == "song":
            for sub in item[1:]:
                if (isinstance(sub, list) and len(sub) > 1 and sub[0] == "name"
                        and isinstance(sub[1], str) and sub[1].strip()):
                    parts = [p for p in sub[1].replace("\\", "/").split("/") if p]
                    if len(parts) >= 2:
                        parent = os.path.dirname(songs_dir)
                        return parts[-1], os.path.join(parent, *parts[:-1])
    return key, os.path.join(songs_dir, key)


def _validate_edat(folder, edat, s, profile, key, midi_tracks, check_midi=True) -> List[Issue]:
    """Confere o .mid.edat: magic NPD, hashes com a klicensee da pasta em USRDIR e,
    decifrado, as mesmas regras do MIDI solto."""
    import shutil
    import tempfile
    from src.creator.edat import EdatError, read_rock_band_mid_edat
    loc = _rel(folder, edat)
    try:
        with open(edat, "rb") as f:
            if f.read(4) != b"NPD\x00":
                return [Issue("error", "PS3_BAD_EDAT", "O .mid.edat não começa com NPD", loc)]
    except OSError as e:
        return [Issue("error", "PS3_BAD_EDAT", "Não foi possível ler o .mid.edat: %s" % e, loc)]
    try:
        midi_bytes = read_rock_band_mid_edat(edat, installed=True)
    except EdatError as e:
        return [Issue("error", "PS3_BAD_EDAT",
                      "O .mid.edat não abre com a chave desta pasta: %s" % e, loc)]
    except Exception as e:
        return [Issue("error", "PS3_BAD_EDAT", "Não foi possível decifrar o .mid.edat: %s" % e, loc)]
    issues: List[Issue] = []
    if not getattr(profile, "edat_verified", True):
        issues.append(Issue("warning", "PS3_EDAT_UNVERIFIED",
                            "O .mid.edat de %s segue a fórmula do Onyx, mas não foi conferido "
                            "com um pacote real" % profile.label, loc))
    if not check_midi:
        return issues
    tmp = tempfile.mkdtemp(prefix="mg_edat_")
    try:
        mid = os.path.join(tmp, s + ".mid")
        with open(mid, "wb") as f:
            f.write(midi_bytes)
        for i in _guard(validate_midi, mid, profile):
            iloc = i.location
            if iloc == s + ".mid" or iloc.startswith(s + ".mid "):
                iloc = loc + iloc[len(s + ".mid"):]
            issues.append(Issue(i.level, i.code, i.message, iloc))
        tracks = midi_track_names(mid)
        if tracks:
            midi_tracks[key] = tracks
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return issues


def _validate_song_files(folder, songs_dir, entry, profile, midi_tracks, mogg_channels,
                         platform: str = "ps3"):
    key = str(entry[0])
    s, sdir = _song_paths(songs_dir, entry)
    issues: List[Issue] = []
    if not os.path.isdir(sdir):
        return [Issue("error", "LAYOUT_MISSING_SONG_DIR",
                      "Faltando a pasta %s/" % _rel(folder, sdir), _rel(folder, sdir))]
    edat = os.path.join(sdir, s + ".mid.edat")
    mid = os.path.join(sdir, s + ".mid")
    if platform == "xbox":
        if os.path.isfile(edat):
            issues.append(Issue("error", "XBOX_UNEXPECTED_EDAT",
                                "%s.mid.edat é do PS3: o Xbox 360 usa o .mid sem cifra" % s,
                                _rel(folder, edat)))
        if not os.path.isfile(mid):
            issues.append(Issue("error", "LAYOUT_MISSING_CHART",
                                "Faltando %s.mid" % s, _rel(folder, mid)))
    elif os.path.isfile(edat):
        issues.extend(_validate_edat(folder, edat, s, profile, key, midi_tracks,
                                     check_midi=not os.path.isfile(mid)))
    else:
        issues.append(Issue("error", "PS3_MISSING_EDAT",
                            "Faltando %s.mid.edat" % s, _rel(folder, edat)))
    if os.path.isfile(mid):
        if platform != "xbox" and not os.path.isfile(edat):
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
            midi_tracks[key] = tracks

    mogg = os.path.join(sdir, s + ".mogg")
    if not os.path.isfile(mogg):
        issues.append(Issue("error", "LAYOUT_MISSING_MOGG",
                            "Faltando %s.mogg" % s, _rel(folder, mogg)))
    else:
        info = read_mogg_info(mogg)
        mogg_channels[key] = info.channels if info else None
        for i in _guard(validate_mogg, mogg):
            issues.append(Issue(i.level, i.code, i.message, _rel(folder, mogg)))

    gen = os.path.join(sdir, "gen")
    prefix = "XBOX" if platform == "xbox" else "PS3"
    milo = os.path.join(gen, "%s.milo_%s" % (s, platform))
    if not os.path.isfile(milo):
        issues.append(Issue("warning", prefix + "_MISSING_MILO",
                            "Faltando gen/%s" % os.path.basename(milo), _rel(folder, milo)))
    art = os.path.join(gen, "%s_keep.png_%s" % (s, platform))
    if not _album_art_disabled(entry) and not os.path.isfile(art):
        issues.append(Issue("warning", prefix + "_MISSING_ART",
                            "Faltando gen/%s" % os.path.basename(art), _rel(folder, art)))
    return issues


def _validate_xbox(folder: str, profile) -> List[Issue]:
    """Abre cada pacote CON/LIVE com o leitor STFS (hashes, assinatura, metadados) e
    valida o songs.dta/.mid/.mogg de dentro com as mesmas regras do PS3."""
    if os.path.isfile(folder) and _is_con_package(folder):
        cons = [folder]
        base = os.path.dirname(folder)
    else:
        cons = sorted(_find_con_packages(folder)) if os.path.isdir(folder) else []
        base = folder
    if not cons:
        return [Issue("error", "XBOX_NO_CON_PACKAGE", _XBOX_MSG)]
    issues: List[Issue] = []
    for con in cons:
        issues.extend(_guard(_validate_con, base, con, profile))
    return issues


def _validate_con(folder: str, con: str, profile) -> List[Issue]:
    import shutil
    import tempfile
    from src.creator.xbox_stfs import RB2_TITLE_ID, RB3_TITLE_ID, StfsError, StfsPackage
    loc = _rel(folder, con)
    try:
        pkg = StfsPackage(con)
    except (StfsError, OSError) as e:
        return [Issue("error", "XBOX_BAD_CON", "Pacote CON ilegível: %s" % e, loc)]
    issues: List[Issue] = []
    for problem in pkg.verify():
        issues.append(Issue("error", "XBOX_BAD_CON", problem, loc))
    if pkg.title_id not in (RB3_TITLE_ID, RB2_TITLE_ID):
        issues.append(Issue("error", "XBOX_WRONG_TITLE",
                            "Title id %08X não é do Rock Band 3 (45410914)" % pkg.title_id, loc))
    if pkg.magic != "CON":
        issues.append(Issue("warning", "XBOX_LIVE_PACKAGE",
                            "Pacote %s: a assinatura da Microsoft não pode ser conferida aqui"
                            % pkg.magic, loc))
    elif not pkg.signed_with_known_kv():
        issues.append(Issue("warning", "XBOX_UNKNOWN_SIGNER",
                            "CON assinada com um certificado diferente do KV do Onyx/C3", loc))
    tmp = tempfile.mkdtemp(prefix="mg_con_")
    try:
        pkg.extract(tmp, want=lambda name: not name.lower().endswith(".milo_xbox"))
        # .milo_xbox não é validado: só marca que existe (arquivo vazio)
        for e in pkg.files():
            if e.path.lower().endswith(".milo_xbox"):
                dest = os.path.join(tmp, *e.path.split("/"))
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                open(dest, "wb").close()
        inner = _validate_ps3_like(tmp, profile, platform="xbox")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for i in inner:
        where = i.location
        issues.append(Issue(i.level, i.code, i.message,
                            "%s:%s" % (loc, where) if where else loc))
    return issues


def _validate_ps4(folder: str) -> List[Issue]:
    songdtas = [p for p in _walk_files(folder)
                if p.lower().endswith(".songdta_ps4")] if os.path.isdir(folder) else []
    if not songdtas:
        return [Issue("error", "PS4_NO_SONGDTA", "PS4 / Rock Band 4 é experimental e não verificado: o RB4 exige "
                      "arquivos binários (.songdta_ps4, .rbmid_ps4, .moggsong, .png_ps4) que o "
                      "MidGuitar ainda não gera. Esta pasta tem só a estrutura de arquivos "
                      "e ainda não toca no Rock Band 4")]
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
