"""
Visualizador de Bateria Eletrônica MIDI (Pads e Pratos).
Permite clicar em qualquer pad para tocar/testar o som instantaneamente!
"""

import customtkinter as ctk
import time
from src.midi.instrument_types import DRUM_MAP

# Mapeamento padrão dos 6 pads para notas MIDI
DEFAULT_PAD_NOTES = {
    "kick": 36,   # Bumbo
    "snare": 38,  # Caixa
    "hihat": 42,  # Chimbal
    "tom1": 48,   # Tom 1
    "tom2": 41,   # Surdo (Floor Tom)
    "crash": 49,  # Prato (Crash)
}

DRUM_PADS_CONFIG = [
    {"id": "kick", "name": "BUMBO (Kick)", "default_note": 36, "color": "#9333EA", "active_color": "#C084FC"},
    {"id": "snare", "name": "CAIXA (Snare)", "default_note": 38, "color": "#991B1B", "active_color": "#EF4444"},
    {"id": "hihat", "name": "CHIMBAL (Hi-Hat)", "default_note": 42, "color": "#854D0E", "active_color": "#FACC15"},
    {"id": "tom1", "name": "TOM 1 / RIDE", "default_note": 48, "color": "#1E40AF", "active_color": "#3B82F6"},
    {"id": "tom2", "name": "SURDO / CRASH", "default_note": 41, "color": "#166534", "active_color": "#22C55E"},
    {"id": "crash", "name": "PRATO (Crash 2)", "default_note": 55, "color": "#9A3412", "active_color": "#FB923C"},
]

class DrumView(ctk.CTkFrame):
    def __init__(self, master, on_pad_click=None, on_open_mapping=None, on_open_sound_manager=None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_pad_click = on_pad_click                # func(pad_id, note)
        self.on_open_mapping = on_open_mapping          # func()
        self.on_open_sound_manager = on_open_sound_manager # func()
        self.pad_buttons = {}
        self.pad_labels = {}
        self.pad_notes = DEFAULT_PAD_NOTES.copy()
        self.hit_counts = {p["id"]: 0 for p in DRUM_PADS_CONFIG}
        self._init_ui()

    def _init_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(6, 2))

        title = ctk.CTkLabel(
            header, text="🥁 Bateria (Clique em qualquer pad para Ouvir)",
            font=ctk.CTkFont(size=13, weight="bold"), text_color="#F59E0B"
        )
        title.pack(side="left")

        from src.ui.tooltip import set_tooltip

        if self.on_open_sound_manager:
            btn_sound = ctk.CTkButton(
                header, text="📁 Áudios", width=100, height=26,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#8B5CF6", hover_color="#7C3AED",
                command=self.on_open_sound_manager
            )
            btn_sound.pack(side="right", padx=(4, 0))
            set_tooltip(btn_sound, "Importe gravações reais (.wav / .mp3) para os pratos e tambores")

        if self.on_open_mapping:
            btn_edit = ctk.CTkButton(
                header, text="🎛️ Mapear", width=95, height=26,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#F59E0B", hover_color="#D97706", text_color="#0F172A",
                command=self.on_open_mapping
            )
            btn_edit.pack(side="right", padx=(4, 0))
            set_tooltip(btn_edit, "Altere a nota e peça de cada pad da bateria")

        self.last_hit_lbl = ctk.CTkLabel(self, text="Último toque: Nenhum", font=ctk.CTkFont(size=11), text_color="#94A3B8")
        self.last_hit_lbl.pack(pady=(0, 2))

        # Container dos pads de bateria organizados em grade
        grid_container = ctk.CTkFrame(self, fg_color="transparent")
        grid_container.pack(fill="both", expand=True, padx=10, pady=(2, 8))

        for col in range(3):
            grid_container.columnconfigure(col, weight=1)
        for row in range(2):
            grid_container.rowconfigure(row, weight=1)

        for idx, cfg in enumerate(DRUM_PADS_CONFIG):
            row = idx // 3
            col = idx % 3
            pad_id = cfg["id"]

            pad_frame = ctk.CTkFrame(grid_container, fg_color="#1E293B", corner_radius=10, border_width=2, border_color="#334155")
            pad_frame.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")

            btn = ctk.CTkButton(
                pad_frame,
                text=cfg["name"],
                fg_color=cfg["color"],
                hover_color=cfg["active_color"],
                font=ctk.CTkFont(size=13, weight="bold"),
                height=48,
                corner_radius=8,
                command=lambda pid=pad_id: self._on_pad_clicked(pid)
            )
            btn.pack(fill="x", padx=8, pady=(8, 2))

            set_tooltip(btn, f"{cfg['name']}\n• Clique com o mouse para tocar a batida!\n• Dispara o som no Canal 10 da bateria.")

            lbl = ctk.CTkLabel(pad_frame, text=f"Nota {self.pad_notes[pad_id]} | Toques: 0", font=ctk.CTkFont(size=11), text_color="#94A3B8")
            lbl.pack(pady=(2, 6))

            self.pad_buttons[pad_id] = (btn, cfg["color"], cfg["active_color"])
            self.pad_labels[pad_id] = lbl

    def _on_pad_clicked(self, pad_id: str):
        note = self.pad_notes.get(pad_id, 36)
        self.trigger_pad_by_note(note, velocity=115)
        if self.on_pad_click:
            self.on_pad_click(pad_id, note)

    def set_pad_mapping(self, pad_id: str, note: int):
        """Atualiza a nota MIDI atribuída a um pad."""
        self.pad_notes[pad_id] = note
        if pad_id in self.pad_labels:
            self.pad_labels[pad_id].configure(text=f"Nota {note} | Toques: {self.hit_counts[pad_id]}")

    def trigger_pad_by_note(self, note: int, velocity: int):
        """Dispara animação visual do pad correspondente à nota MIDI tocada."""
        pad_id = None
        pad_name = "Percussão"

        # Verifica se corresponde à nota mapeada de algum pad
        for p_id, mapped_note in self.pad_notes.items():
            if mapped_note == note:
                pad_id = p_id
                break

        if not pad_id:
            # Fallback para notas padrão
            if note in (35, 36):
                pad_id = "kick"
                pad_name = "Bumbo"
            elif note in (38, 40):
                pad_id = "snare"
                pad_name = "Caixa"
            elif note in (42, 44, 46):
                pad_id = "hihat"
                pad_name = "Chimbal"
            elif note in (45, 47, 48):
                pad_id = "tom1"
                pad_name = "Tom 1"
            elif note in (41, 43):
                pad_id = "tom2"
                pad_name = "Surdo"
            elif note in (49, 51, 53, 55):
                pad_id = "crash"
                pad_name = "Prato"

        if pad_id and pad_id in self.pad_buttons:
            btn, normal_col, active_col = self.pad_buttons[pad_id]
            self.hit_counts[pad_id] += 1
            btn.configure(fg_color=active_col)
            self.pad_labels[pad_id].configure(text=f"Nota {self.pad_notes[pad_id]} | Toques: {self.hit_counts[pad_id]}")
            self.last_hit_lbl.configure(text=f"Último toque: {pad_id.upper()} (Nota {note} | Vel {velocity})")
            self.after(120, lambda b=btn, c=normal_col: b.configure(fg_color=c))
