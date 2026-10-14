"""
Motor de mapeamento de sinais de guitarra para notas MIDI, acordes e efeitos.
Suporta:
- Rock Band 5-button (Verde, Vermelho, Amarelo, Azul, Laranja + Palheta + Alavanca + Overdrive)
- Rock Band Pro Guitar (Mustang / Squier) notas diretas
- Modo Acordes (Power Chords) e Modo Solo (Notas individuais)
"""

from dataclasses import dataclass, field
import time

@dataclass
class GuitarState:
    green: bool = False
    red: bool = False
    yellow: bool = False
    blue: bool = False
    orange: bool = False
    strum_up: bool = False
    strum_down: bool = False
    whammy_value: float = 0.0      # 0.0 a 1.0 (ou -1.0 a +1.0)
    overdrive: bool = False
    active_sounding_notes: set[int] = field(default_factory=set)
    last_action: str = "Pronto"

class GuitarMapper:
    def __init__(self, preset: dict, octave_shift: int = 0):
        self.preset = preset
        self.octave_shift = octave_shift
        self.state = GuitarState()
        self.last_strum_time = 0.0

    def set_preset(self, preset: dict):
        self.preset = preset

    def set_octave_shift(self, shift: int):
        self.octave_shift = shift

    def get_highest_priority_fret(self) -> str | None:
        """Em guitarras clássicas de Rock Band, a casa mais à direita (mais alta) prevalece."""
        if self.state.orange:
            return "orange"
        if self.state.blue:
            return "blue"
        if self.state.yellow:
            return "yellow"
        if self.state.red:
            return "red"
        if self.state.green:
            return "green"
        return None

    def get_notes_for_current_frets(self) -> list[int]:
        """Calcula a lista de notas MIDI baseado nas casas pressionadas e no preset."""
        frets_config = self.preset.get("frets", {})
        fret = self.get_highest_priority_fret()

        if fret and fret in frets_config:
            base_notes = frets_config[fret].get("notes", [])
        else:
            base_notes = frets_config.get("open_strum", {}).get("notes", [40])

        # Aplica deslocamento de oitava (12 semitons por oitava)
        shift_semitones = self.octave_shift * 12
        final_notes = [max(0, min(127, n + shift_semitones)) for n in base_notes]
        return final_notes

    def handle_fret_change(self, fret: str, is_pressed: bool) -> tuple[list[int], list[int]]:
        """
        Atualiza o estado de uma casa.
        Retorna: (notas_para_desligar, notas_para_tocar)
        """
        setattr(self.state, fret, is_pressed)
        trigger_mode = self.preset.get("trigger_mode", "strum_required")

        notes_to_stop = []
        notes_to_play = []

        if trigger_mode == "instant_or_strum" or trigger_mode == "passthrough":
            if is_pressed:
                # Tapping instantâneo
                notes_to_play = self.get_notes_for_current_frets()
                notes_to_stop = list(self.state.active_sounding_notes)
                self.state.active_sounding_notes = set(notes_to_play)
                self.state.last_action = f"Fret {fret.upper()} (Tap)"
            else:
                # Se soltou a casa e não tem outra casa pressionada
                if not any([self.state.green, self.state.red, self.state.yellow, self.state.blue, self.state.orange]):
                    notes_to_stop = list(self.state.active_sounding_notes)
                    self.state.active_sounding_notes.clear()

        return notes_to_stop, notes_to_play

    def handle_strum(self, is_down: bool, is_pressed: bool) -> tuple[list[int], list[int]]:
        """
        Atualiza a palheta (strum up/down).
        Retorna: (notas_para_desligar, notas_para_tocar)
        """
        if is_down:
            self.state.strum_down = is_pressed
        else:
            self.state.strum_up = is_pressed

        notes_to_stop = []
        notes_to_play = []

        if is_pressed:
            direction = "Baixo" if is_down else "Cima"
            self.state.last_action = f"Palhetada para {direction}"
            self.last_strum_time = time.time()

            # Desliga notas que estavam soando antes para palhetar novo ataque limpo
            notes_to_stop = list(self.state.active_sounding_notes)
            notes_to_play = self.get_notes_for_current_frets()
            self.state.active_sounding_notes = set(notes_to_play)
        else:
            # Soltou a palheta
            pass

        return notes_to_stop, notes_to_play

    def stop_all_active_notes(self) -> list[int]:
        """Para todas as notas atualmente soando."""
        notes = list(self.state.active_sounding_notes)
        self.state.active_sounding_notes.clear()
        return notes
