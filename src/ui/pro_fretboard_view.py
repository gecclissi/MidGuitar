"""
Visualizador de Braço de Guitarra Pro (6 Cordas, 17/22 trastes).
Permite clicar em qualquer corda e traste para ouvir e validar o som!
"""

import customtkinter as ctk
from src.midi.instrument_types import PRO_GUITAR_STRINGS
from src.utils.instruments import midi_note_to_name

class ProFretboardView(ctk.CTkFrame):
    def __init__(self, master, on_fret_click=None, num_frets: int = 17, **kwargs):
        super().__init__(master, **kwargs)
        self.on_fret_click = on_fret_click # func(string_num, fret, note)
        self.num_frets = num_frets
        self.string_states = {s: {"fret": -1, "velocity": 0, "active": False} for s in range(1, 7)}
        self._init_ui()

    def _init_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(6, 2))

        title = ctk.CTkLabel(
            header, text="🎸 Guitarra Pro (Clique em qualquer traste/corda para Ouvir)",
            font=ctk.CTkFont(size=13, weight="bold"), text_color="#38BDF8"
        )
        title.pack(side="left")

        self.last_chord_lbl = ctk.CTkLabel(header, text="Notas ativas: Nenhuma", font=ctk.CTkFont(size=12), text_color="#94A3B8")
        self.last_chord_lbl.pack(side="right")

        neck_frame = ctk.CTkFrame(self, fg_color="#0F172A", corner_radius=8, border_width=2, border_color="#334155")
        neck_frame.pack(fill="both", expand=True, padx=10, pady=(4, 10))

        self.canvas = ctk.CTkCanvas(neck_frame, bg="#0F172A", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=8, pady=8)
        self.canvas.bind("<Configure>", self._draw_fretboard)
        self.canvas.bind("<Button-1>", self._on_canvas_click)

    def _on_canvas_click(self, event):
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        margin_left = 60
        margin_right = 20
        margin_top = 20
        margin_bottom = 25

        usable_w = width - margin_left - margin_right
        usable_h = height - margin_top - margin_bottom

        if usable_w <= 0 or usable_h <= 0:
            return

        fret_spacing = usable_w / (self.num_frets + 1)
        string_spacing = usable_h / 5

        # Identifica a corda clicada (1 a 6)
        y = event.y
        closest_string = 1
        min_dist = 999999
        for s in range(1, 7):
            sy = margin_top + ((s - 1) * string_spacing)
            dist = abs(y - sy)
            if dist < min_dist:
                min_dist = dist
                closest_string = s

        # Identifica o traste clicado (0 = corda solta, 1 a num_frets)
        x = event.x
        if x < margin_left:
            clicked_fret = 0
        else:
            clicked_fret = int((x - margin_left) / fret_spacing) + 1
            clicked_fret = max(0, min(self.num_frets, clicked_fret))

        # Calcula a nota
        open_note = PRO_GUITAR_STRINGS[closest_string]["open_note"]
        note = open_note + clicked_fret

        # Ativa visualmente
        self.set_string_fret(closest_string, clicked_fret, True, velocity=105)
        self.after(250, lambda s=closest_string: self.set_string_fret(s, -1, False, 0))

        if self.on_fret_click:
            self.on_fret_click(closest_string, clicked_fret, note)

    def _draw_fretboard(self, event=None):
        self.canvas.delete("all")
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        if width < 100 or height < 60:
            return

        margin_left = 60
        margin_right = 20
        margin_top = 20
        margin_bottom = 25

        usable_w = width - margin_left - margin_right
        usable_h = height - margin_top - margin_bottom

        fret_spacing = usable_w / (self.num_frets + 1)
        string_spacing = usable_h / 5

        # Pestana
        self.canvas.create_rectangle(
            margin_left - 6, margin_top - 4, margin_left, margin_top + usable_h + 4,
            fill="#CBD5E1", outline=""
        )

        # Trastes
        for f in range(1, self.num_frets + 2):
            x = margin_left + (f * fret_spacing)
            self.canvas.create_line(x, margin_top - 2, x, margin_top + usable_h + 2, fill="#475569", width=2)
            if f <= self.num_frets:
                self.canvas.create_text(
                    x - (fret_spacing / 2), height - 10,
                    text=str(f), fill="#64748B", font=("Arial", 9)
                )

        # Marcadores de casas
        inlay_frets = [3, 5, 7, 9, 12, 15, 17]
        for f in inlay_frets:
            if f <= self.num_frets:
                x = margin_left + (f * fret_spacing) - (fret_spacing / 2)
                y = margin_top + (usable_h / 2)
                if f == 12:
                    self.canvas.create_oval(x - 3, y - 18, x + 3, y - 12, fill="#334155", outline="")
                    self.canvas.create_oval(x - 3, y + 12, x + 3, y + 18, fill="#334155", outline="")
                else:
                    self.canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill="#334155", outline="")

        # 6 cordas
        string_thicknesses = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
        string_names = ["1ª E", "2ª B", "3ª G", "4ª D", "5ª A", "6ª E"]

        for idx, (th, name) in enumerate(zip(string_thicknesses, string_names)):
            string_num = idx + 1
            y = margin_top + (idx * string_spacing)

            is_active = self.string_states[string_num]["active"]
            lbl_color = "#38BDF8" if is_active else "#94A3B8"
            self.canvas.create_text(
                margin_left - 24, y,
                text=name, fill=lbl_color, font=("Arial", 10, "bold" if is_active else "normal")
            )

            str_color = "#38BDF8" if is_active else "#94A3B8"
            self.canvas.create_line(
                margin_left, y, width - margin_right, y,
                fill=str_color, width=th + (2 if is_active else 0)
            )

            if is_active:
                fret = self.string_states[string_num]["fret"]
                if fret == 0:
                    dot_x = margin_left - 12
                else:
                    dot_x = margin_left + (fret * fret_spacing) - (fret_spacing / 2)

                self.canvas.create_oval(dot_x - 10, y - 10, dot_x + 10, y + 10, fill="#22C55E", outline="#FFFFFF", width=2)
                
                open_note = PRO_GUITAR_STRINGS[string_num]["open_note"]
                actual_note = open_note + max(0, fret)
                note_name = midi_note_to_name(actual_note)
                self.canvas.create_text(dot_x, y, text=note_name, fill="#0F172A", font=("Arial", 8, "bold"))

    def set_string_fret(self, string_num: int, fret: int, is_active: bool, velocity: int = 100):
        if string_num in self.string_states:
            self.string_states[string_num]["fret"] = fret
            self.string_states[string_num]["active"] = is_active
            self.string_states[string_num]["velocity"] = velocity
            self._draw_fretboard()

            active_notes = []
            for s, st in self.string_states.items():
                if st["active"]:
                    open_n = PRO_GUITAR_STRINGS[s]["open_note"]
                    note = open_n + max(0, st["fret"])
                    active_notes.append(midi_note_to_name(note))
            
            if active_notes:
                self.last_chord_lbl.configure(text=f"Notas ativas: {' + '.join(active_notes)}")
            else:
                self.last_chord_lbl.configure(text="Notas ativas: Nenhuma")
