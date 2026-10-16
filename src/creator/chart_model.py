"""
Modelo de Dados para Criação e Edição de Músicas (Charts).
Representa a música completa com metadados, trilhas de instrumentos,
eventos de tempo, seções e notas musicais.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import json

@dataclass
class NoteEvent:
    time_ms: int             # Tempo de início em milissegundos
    lane: str                # "green", "red", "yellow", "blue", "orange" (ou "kick", "snare", etc.)
    duration_ms: int = 150   # Duração (para notas longas / sustains)
    difficulty: str = "Expert" # "Easy", "Medium", "Hard", "Expert"
    is_hopo: bool = False
    is_overdrive: bool = False

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
    audio_path: Optional[str] = None
    audio_stems: List[str] = field(default_factory=list)
    album_art_path: Optional[str] = None
    
    # Dificuldades de 0 a 7 (-1 se não tiver)
    diff_guitar: int = 3
    diff_bass: int = 2
    diff_drums: int = 3
    diff_keys: int = 2
    diff_vocals: int = 3
    diff_band: int = 3

    # Trilhas de notas
    guitar_notes: List[NoteEvent] = field(default_factory=list)
    bass_notes: List[NoteEvent] = field(default_factory=list)
    drum_notes: List[NoteEvent] = field(default_factory=list)
    keys_notes: List[NoteEvent] = field(default_factory=list)
    vocal_notes: List[VocalNote] = field(default_factory=list)
    events: List[TextEvent] = field(default_factory=list)

    def add_vocal_note(self, note: VocalNote):
        self.vocal_notes.append(note)
        self.vocal_notes.sort(key=lambda n: n.time_ms)

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

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "year": self.year,
            "genre": self.genre,
            "charter": self.charter,
            "bpm": self.bpm,
            "time_signature": list(self.time_signature),
            "preview_start_ms": self.preview_start_ms,
            "audio_path": self.audio_path,
            "album_art_path": self.album_art_path,
            "diff_guitar": self.diff_guitar,
            "diff_bass": self.diff_bass,
            "diff_drums": self.diff_drums,
            "diff_keys": self.diff_keys,
            "diff_band": self.diff_band,
            "guitar_notes": [n.__dict__ for n in self.guitar_notes],
            "bass_notes": [n.__dict__ for n in self.bass_notes],
            "drum_notes": [n.__dict__ for n in self.drum_notes],
            "keys_notes": [n.__dict__ for n in self.keys_notes],
            "events": [e.__dict__ for e in self.events],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChartSong":
        song = cls(
            title=data.get("title", "Nova Música"),
            artist=data.get("artist", "Artista"),
            album=data.get("album", "Álbum"),
            year=data.get("year", 2026),
            genre=data.get("genre", "Rock"),
            charter=data.get("charter", "MidGuitar Studio"),
            bpm=float(data.get("bpm", 120.0)),
            time_signature=tuple(data.get("time_signature", [4, 4])),
            preview_start_ms=data.get("preview_start_ms", 30000),
            audio_path=data.get("audio_path"),
            album_art_path=data.get("album_art_path"),
            diff_guitar=data.get("diff_guitar", 3),
            diff_bass=data.get("diff_bass", 2),
            diff_drums=data.get("diff_drums", 3),
            diff_keys=data.get("diff_keys", 2),
            diff_band=data.get("diff_band", 3),
        )
        song.guitar_notes = [NoteEvent(**n) for n in data.get("guitar_notes", [])]
        song.bass_notes = [NoteEvent(**n) for n in data.get("bass_notes", [])]
        song.drum_notes = [NoteEvent(**n) for n in data.get("drum_notes", [])]
        song.keys_notes = [NoteEvent(**n) for n in data.get("keys_notes", [])]
        song.events = [TextEvent(**e) for e in data.get("events", [])]
        return song
