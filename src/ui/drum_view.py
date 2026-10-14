"""
Visualizador de Bateria Eletrônica MIDI (Pads e Pratos).
Compatível com Band Hero, Guitar Hero World Tour/5 e Rock Band Drums (Canal 10).
"""

import customtkinter as ctk
import time
from src.midi.instrument_types import DRUM_MAP

DRUM_PADS_CONFIG = [
    {"id": "kick", "name": "BUMBO (Kick)", "note": "36 (Pedal)", "color": "#9333EA", "active_color": "#C084FC"},
    {"id": "snare", "name": "CAIXA (Snare)", "note": "38 (Vermelho)", "color": "#991B1B", "active_color": "#EF4444"},
    {"id": "hihat", "name": "CHIMBAL (Hi-Hat)", "note": "42/46 (Amarelo)", "color": "#854D0E", "active_color": "#FACC15"},
    {"id": "tom1", "name": "TOM 1 / RIDE", "note": "48/51 (Azul)", "color": "#1E40AF", "active_color": "#3B82F6"},
    {"id": "tom2", "name": "SURDO / CRASH", "note": "41/49 (Verde)", "color": "#166534", "active_color": "#22C55E"},
    {"id": "crash", "name": "PRATO (Crash 2)", "note": "55 (Laranja)", "color": "#9A3412", "active_color": "#FB923C"},
]

class DrumView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.pad_frames = {}
        self.pad_buttons = {}
        self.pad_labels = {}
        self.hit_counts = {p["id"]: 0 for p in DRUM_PADS_CONFIG}
        self._init_ui()

    def _init_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(6, 2))

        title = ctk.CTkLabel(header, text="🥁 Bateria Rock Band / Band Hero (Canal 10)", font=ctk.CTkFont(size=13, weight="bold"), text_color="#F59E0B")
        title.pack(side="left")

        self.last_hit_lbl = ctk.CTkLabel(header, text="Último toque: Nenhum", font=ctk.CTkFont(size=12), text_color="#94A3B8")
        self.last_hit_lbl.pack(side="right")

        # Container dos pads de bateria organizados em grade
        grid_container = ctk.CTkFrame(self, fg_color="transparent")
        grid_container.pack(fill="both", expand=True, padx=10, pady=(4, 10))

        # Configura grid 2x3
        for col in range(3):
            grid_container.columnconfigure(col, weight=1)
        for row in range(2):
            grid_container.rowconfigure(row, weight=1)

        for idx, cfg in enumerate(DRUM_PADS_CONFIG):
            row = idx // 3
            col = idx % 3

            pad_frame = ctk.CTkFrame(grid_container, fg_color="#1E293B", corner_radius=10, border_width=2, border_color="#334155")
            pad_frame.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")

            btn = ctk.CTkButton(
                pad_frame,
                text=cfg["name"],
                fg_color=cfg["color"],
                hover_color=cfg["active_color"],
                font=ctk.CTkFont(size=13, weight="bold"),
                height=48,
                corner_radius=8
            )
            btn.pack(fill="x", padx=8, pady=(8, 2))

            lbl = ctk.CTkLabel(pad_frame, text=f"MIDI {cfg['note']} | Toques: 0", font=ctk.CTkFont(size=11), text_color="#94A3B8")
            lbl.pack(pady=(2, 6))

            self.pad_buttons[cfg["id"]] = (btn, cfg["color"], cfg["active_color"])
            self.pad_labels[cfg["id"]] = lbl

    def trigger_pad_by_note(self, note: int, velocity: int):
        """Dispara animação visual do pad correspondente à nota MIDI tocada."""
        pad_id = None
        pad_name = "Desconhecido"

        if note in DRUM_MAP:
            name, p_id, _ = DRUM_MAP[note]
            pad_id = p_id
            pad_name = name
        elif note in (35, 36):
            pad_id = "kick"
            pad_name = "Bumbo (Kick)"
        elif note in (38, 40):
            pad_id = "snare"
            pad_name = "Caixa (Snare)"
        elif note in (42, 44, 46):
            pad_id = "hihat"
            pad_name = "Chimbal (Hi-Hat)"
        elif note in (45, 47, 48):
            pad_id = "tom1"
            pad_name = "Tom 1"
        elif note in (41, 43):
            pad_id = "tom2"
            pad_name = "Surdo (Floor Tom)"
        elif note in (49, 51, 53, 55):
            pad_id = "crash"
            pad_name = "Prato (Crash/Ride)"

        if pad_id and pad_id in self.pad_buttons:
            btn, normal_col, active_col = self.pad_buttons[pad_id]
            self.hit_counts[pad_id] += 1
            btn.configure(fg_color=active_col)
            self.pad_labels[pad_id].configure(text=f"Vel: {velocity} | Toques: {self.hit_counts[pad_id]}")
            self.last_hit_lbl.configure(text=f"Último toque: {pad_name} (Vel {velocity})")

            # Retorna à cor normal após 120ms
            self.after(120, lambda b=btn, c=normal_col: b.configure(fg_color=c))
