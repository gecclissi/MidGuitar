"""
Modelo de Dados para Criação e Edição de Músicas (Charts).
Representa a música completa com metadados, trilhas de instrumentos,
eventos de tempo, seções e notas musicais.
"""

from dataclasses import dataclass, field, fields
from typing import Any, List, Dict, Optional
import json
import os

from src.creator.tempo_map import TempoMap

@dataclass
class NoteEvent:
    time_ms: int             # Tempo de início em milissegundos
    lane: str                # Guitarra/baixo/teclado: "green", "red", "yellow", "blue", "orange"
                             # Bateria: "kick", "snare", "yellow", "blue", "green" (rbn_specs.DRUM_NOTES)
    duration_ms: int = 150   # Duração (para notas longas / sustains)
    difficulty: str = "Expert" # "Easy", "Medium", "Hard", "Expert"
    is_hopo: bool = False
    is_overdrive: bool = False
    velocity: int = 100      # Velocity MIDI (acento/ghost da bateria, 96 em customs reais)

@dataclass
class TextEvent:
    time_ms: int
    text: str                # ex: "[section intro]", "[section solo]"

@dataclass
class VocalNote:
    time_ms: int
    duration_ms: int = 250
    pitch: int = 60            # Altura tonal MIDI (ex: 60 = C4)
    lyric: str = "la"          # Sílaba / palavra cantada
    is_talkie: bool = False    # Frase falada / rap
    is_overdrive: bool = False # Frase de Overdrive (Nota 106)
    is_phrase_end: bool = False # Fim da frase vocal (Nota 105)
    velocity: int = 100

@dataclass
class ProGuitarNote:
    time_ms: int
    string_idx: int = 0          # 0 (Corda 6 Mi grave) a 5 (Corda 1 Mi agudo)
    fret: int = 0                # Casa 0 a 17
    duration_ms: int = 200
    difficulty: str = "Expert"   # "Easy", "Medium", "Hard", "Expert"
    is_overdrive: bool = False
    channel: int = 0             # Canal MIDI (tipo de nota: normal, abafada, harmônico...)

@dataclass
class ProKeysNote:
    time_ms: int
    pitch: int = 60              # Tecla real do teclado (48 = C3 até 72 = C5)
    duration_ms: int = 250
    difficulty: str = "Expert"   # "Easy", "Medium", "Hard", "Expert"
    is_overdrive: bool = False
    velocity: int = 100

# Nomes antigos das lanes de bateria (projetos salvos antes da unificação)
LEGACY_DRUM_LANES = {"orange": "kick", "red": "snare"}


def _build(cls, data: dict):
    """Cria o dataclass ignorando chaves desconhecidas (projetos de outras versões)."""
    names = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in names})


@dataclass
class ChartSong:
    title: str = "Nova Música"
    artist: str = "Artista"
    album: str = "Álbum"
    year: int = 2026
    genre: str = "Rock"
    charter: str = "MidGuitar Studio"
    bpm: float = 120.0
    time_signature: tuple = (4, 4)
    preview_start_ms: int = 30000
    duration_ms: int = 180000
    audio_path: Optional[str] = None
    audio_stems: List[str] = field(default_factory=list)
    audio_offset_ms: int = 0
    lyrics_raw: str = ""
    album_art_path: Optional[str] = None
    
    # Dificuldades de 0 a 7 (-1 se não tiver)
    diff_guitar: int = 3
    diff_bass: int = 2
    diff_drums: int = 3
    diff_keys: int = 2
    diff_vocals: int = 3
    diff_pro_guitar: int = 3
    diff_pro_bass: int = 2
    diff_pro_keys: int = 3
    diff_band: int = 3

    # Trilhas de notas
    guitar_notes: List[NoteEvent] = field(default_factory=list)
    bass_notes: List[NoteEvent] = field(default_factory=list)
    drum_notes: List[NoteEvent] = field(default_factory=list)
    keys_notes: List[NoteEvent] = field(default_factory=list)
    vocal_notes: List[VocalNote] = field(default_factory=list)
    pro_guitar_notes: List[ProGuitarNote] = field(default_factory=list)
    pro_bass_notes: List[ProGuitarNote] = field(default_factory=list)
    pro_keys_notes: List[ProKeysNote] = field(default_factory=list)
    events: List[TextEvent] = field(default_factory=list)
    # Mapa de tempo importado de um MIDI (None = tempo constante definido por bpm)
    tempo_map: Optional[TempoMap] = None
    # Dados importados que o modelo não edita, regravados sem perdas (ver passthrough.py)
    passthrough_tracks: List[Dict[str, Any]] = field(default_factory=list)
    track_extras: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    tempo_track_name: Optional[str] = None
    # Chaves do song.ini importado que o MidGuitar não usa (regravadas na exportação)
    ini_extra: Dict[str, str] = field(default_factory=dict)
    # song_id lido do songs.dta de um pacote Rock Band importado (None se não houver)
    dta_song_id: Optional[int] = None
    # Avisos da importação para a interface mostrar (ex.: .mogg criptografado sem áudio)
    import_warnings: List[str] = field(default_factory=list)
    # Áudio multicanal de um .mogg importado (mogg_import.prepare_mogg_audio): Ogg original,
    # mix, stems e layout de canais do songs.dta. A exportação Rock Band reaproveita os canais
    # enquanto o áudio e os stems da música forem os mesmos da importação.
    source_mogg: Dict[str, Any] = field(default_factory=dict)

    def get_tempo_map(self) -> TempoMap:
        """Devolve o mapa de tempo efetivo da música.

        O mapa importado só vale enquanto o BPM inicial dele coincide com
        self.bpm. A UI atribui song.bpm diretamente em vários lugares; se o
        usuário muda o BPM, o mapa importado é descartado e usamos tempo
        constante, sem precisar alterar a UI.
        """
        if self.tempo_map is not None and round(self.tempo_map.initial_bpm(), 2) == round(self.bpm, 2):
            return self.tempo_map
        return TempoMap.constant(self.bpm, *self.time_signature)

    def get_effective_duration_ms(self) -> int:
        """Retorna a duração total real garantindo que cubra todas as notas e o áudio."""
        max_ms = max(10000, int(self.duration_ms or 180000))
        for lst in [
            self.guitar_notes, self.bass_notes, self.drum_notes, self.keys_notes,
            self.vocal_notes, self.pro_guitar_notes, self.pro_bass_notes, self.pro_keys_notes
        ]:
            for n in lst:
                end_t = n.time_ms + getattr(n, "duration_ms", 200) + 2000
                if end_t > max_ms:
                    max_ms = end_t
        return max_ms

    def add_vocal_note(self, note: VocalNote):
        self.vocal_notes.append(note)
        self.vocal_notes.sort(key=lambda n: n.time_ms)

    def add_pro_guitar_note(self, note: ProGuitarNote, is_bass: bool = False):
        target = self.pro_bass_notes if is_bass else self.pro_guitar_notes
        target.append(note)
        target.sort(key=lambda n: n.time_ms)

    def add_pro_keys_note(self, note: ProKeysNote):
        self.pro_keys_notes.append(note)
        self.pro_keys_notes.sort(key=lambda n: n.time_ms)

    def add_note(self, track: str, note_event: NoteEvent):
        """Adiciona uma nota à trilha especificada mantendo ordenado por tempo."""
        target_list = getattr(self, f"{track}_notes", None)
        if target_list is not None:
            target_list.append(note_event)
            target_list.sort(key=lambda n: n.time_ms)

    def remove_note_near(self, track: str, time_ms: int, lane: str, tolerance_ms: int = 80) -> bool:
        """Remove nota próxima ao tempo e lane especificados."""
        target_list = getattr(self, f"{track}_notes", None)
        if target_list is None:
            return False
        for i, n in enumerate(target_list):
            if n.lane == lane and abs(n.time_ms - time_ms) <= tolerance_ms:
                target_list.pop(i)
                return True
        return False

    def clear_track(self, track: str):
        """Limpa todas as notas de uma trilha."""
        target_list = getattr(self, f"{track}_notes", None)
        if target_list is not None:
            target_list.clear()

    def get_track_notes(self, track: str) -> List[NoteEvent]:
        return getattr(self, f"{track}_notes", [])

    # Campos simples salvos no projeto (.mgproj)
    _SCALAR_FIELDS = (
        "title", "artist", "album", "year", "genre", "charter", "bpm",
        "preview_start_ms", "duration_ms", "audio_path", "audio_offset_ms",
        "lyrics_raw", "album_art_path",
        "diff_guitar", "diff_bass", "diff_drums", "diff_keys", "diff_vocals",
        "diff_pro_guitar", "diff_pro_bass", "diff_pro_keys", "diff_band",
        "tempo_track_name", "dta_song_id",
    )
    _NOTE_LISTS = (
        ("guitar_notes", NoteEvent), ("bass_notes", NoteEvent), ("drum_notes", NoteEvent),
        ("keys_notes", NoteEvent), ("vocal_notes", VocalNote),
        ("pro_guitar_notes", ProGuitarNote), ("pro_bass_notes", ProGuitarNote),
        ("pro_keys_notes", ProKeysNote), ("events", TextEvent),
    )

    def to_dict(self) -> dict:
        data = {k: getattr(self, k) for k in self._SCALAR_FIELDS}
        data["time_signature"] = list(self.time_signature)
        data["audio_stems"] = list(self.audio_stems)
        for attr, _cls in self._NOTE_LISTS:
            data[attr] = [dict(n.__dict__) for n in getattr(self, attr)]
        data["passthrough_tracks"] = self.passthrough_tracks
        data["track_extras"] = self.track_extras
        data["ini_extra"] = dict(self.ini_extra)
        if self.source_mogg:
            data["source_mogg"] = dict(self.source_mogg)
        if self.tempo_map is not None:
            data["tempo_map"] = self.tempo_map.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "ChartSong":
        song = cls()
        for k in cls._SCALAR_FIELDS:
            if k in data:
                setattr(song, k, data[k])
        song.bpm = float(song.bpm)
        song.time_signature = tuple(data.get("time_signature", [4, 4]))
        song.audio_stems = list(data.get("audio_stems", []))
        for attr, item_cls in cls._NOTE_LISTS:
            setattr(song, attr, [_build(item_cls, n) for n in data.get(attr, [])])
        for n in song.drum_notes:
            n.lane = LEGACY_DRUM_LANES.get(n.lane, n.lane)
        song.passthrough_tracks = list(data.get("passthrough_tracks", []))
        song.track_extras = dict(data.get("track_extras", {}))
        song.ini_extra = dict(data.get("ini_extra", {}))
        song.source_mogg = dict(data.get("source_mogg") or {})
        tm = data.get("tempo_map")
        song.tempo_map = TempoMap.from_dict(tm) if tm else None
        return song


PROJECT_FORMAT = "midguitar-project"
PROJECT_VERSION = 1
PROJECT_EXTENSION = ".mgproj"


def save_project(song: ChartSong, path: str):
    """Salva o projeto (.mgproj, JSON) com tudo que o ChartSong guarda."""
    data = {"format": PROJECT_FORMAT, "version": PROJECT_VERSION, "song": song.to_dict()}
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)


def load_project(path: str) -> ChartSong:
    """Abre um projeto .mgproj; ValueError se o arquivo não for um projeto do MidGuitar."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or data.get("format") != PROJECT_FORMAT or not isinstance(data.get("song"), dict):
        raise ValueError("O arquivo não é um projeto do MidGuitar (.mgproj).")
    return ChartSong.from_dict(data["song"])
