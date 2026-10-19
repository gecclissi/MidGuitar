"""
Visualizador de Braço de Guitarra Pro (6 Cordas) e Baixo Pro (4 Cordas).
Permite tocar notas individuais ou Acordes Pro (Pro Chords) completos!
"""

import customtkinter as ctk
from src.midi.instrument_types import PRO_GUITAR_STRINGS
from src.utils.instruments import midi_note_to_name
from src.ui.tooltip import set_tooltip

# Definições de Acordes Pro para Guitarra (Corda: Traste, -1 = silenciada)
GUITAR_PRO_CHORDS = {
    "C": ("C (Dó)", {1: 0, 2: 1, 3: 0, 4: 2, 5: 3, 6: -1}),
    "D": ("D (Ré)", {1: 2, 2: 3, 3: 2, 4: 0, 5: -1, 6: -1}),
    "E": ("E (Mi)", {1: 0, 2: 0, 3: 1, 4: 2, 5: 2, 6: 0}),
    "G": ("G (Sol)", {1: 3, 2: 0, 3: 0, 4: 0, 5: 2, 6: 3}),
    "A": ("A (Lá)", {1: 0, 2: 2, 3: 2, 4: 2, 5: 0, 6: -1}),
    "Em": ("Em (Mi m)", {1: 0, 2: 0, 3: 0, 4: 2, 5: 2, 6: 0}),
    "Am": ("Am (Lá m)", {1: 0, 2: 1, 3: 2, 4: 2, 5: 0, 6: -1}),
    "Dm": ("Dm (Ré m)", {1: 1, 2: 3, 3: 2, 4: 0, 5: -1, 6: -1}),
    "E5": ("E5 (Power)", {6: 0, 5: 2, 4: 2, 3: -1, 2: -1, 1: -1}),
    "A5": ("A5 (Power)", {5: 0, 4: 2, 3: 2, 6: -1, 2: -1, 1: -1}),
    "D5": ("D5 (Power)", {4: 0, 3: 2, 2: 3, 6: -1, 5: -1, 1: -1}),
    "G5": ("G5 (Power)", {6: 3, 5: 5, 4: 5, 3: -1, 2: -1, 1: -1}),
}

# Afinações do Baixo Pro (4 Cordas)
PRO_BASS_STRINGS = {
    1: {"name": "1ª G", "open_note": 43}, # G2
    2: {"name": "2ª D", "open_note": 38}, # D2
    3: {"name": "3ª A", "open_note": 33}, # A1
    4: {"name": "4ª E", "open_note": 28}, # E1
}


class ProFretboardView(ctk.CTkFrame):
    def __init__(self, master, on_fret_click=None, num_frets: int = 17, **kwargs):
        super().__init__(master, **kwargs)
        self.on_fret_click = on_fret_click # func(string_num, fret, note)
        self.num_frets = num_frets
        self.string_count = 6 # 6 = Guitarra, 4 = Baixo Pro
        self.string_states = {s: {"fret": -1, "velocity": 0, "active": False} for s in range(1, 7)}
        self._init_ui()

    def _init_ui(self):
        # 1. Header com Título, Seletor 6C/4C e Nome do Acorde
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(6, 2))

        title = ctk.CTkLabel(
            header, text="🎸 Guitarra Pro & Baixo Pro (6 e 4 Cordas)",
            font=ctk.CTkFont(size=13, weight="bold"), text_color="#38BDF8"
        )
        title.pack(side="left")

        self.type_selector = ctk.CTkSegmentedButton(
            header,
            values=["🎸 6 Cordas (Guitarra)", "🎸 4 Cordas (Baixo Pro)"],
            command=self._on_type_changed,
            height=26
        )
        self.type_selector.set("🎸 6 Cordas (Guitarra)")
        self.type_selector.pack(side="left", padx=12)
        set_tooltip(self.type_selector, "Alterne entre Guitarra Pro (6 cordas) e Baixo Pro (4 cordas)")

        self.last_chord_lbl = ctk.CTkLabel(header, text="Notas ativas: Nenhuma", font=ctk.CTkFont(size=12, weight="bold"), text_color="#10B981")
        self.last_chord_lbl.pack(side="right")

        # 2. Barra de Acordes Pro Rápidos (Pro Chords)
        chord_bar = ctk.CTkFrame(self, fg_color="#0F172A", corner_radius=6)
        chord_bar.pack(fill="x", padx=10, pady=(2, 4))

        ctk.CTkLabel(chord_bar, text="🎵 Acordes Pro (Pro Chords):", font=ctk.CTkFont(size=11, weight="bold"), text_color="#FACC15").pack(side="left", padx=(8, 6), pady=4)

        for c_key, (c_label, frets_map) in GUITAR_PRO_CHORDS.items():
            btn = ctk.CTkButton(
                chord_bar, text=c_key, width=42, height=24,
                fg_color="#1E293B", hover_color="#334155", font=ctk.CTkFont(size=10, weight="bold"),
                command=lambda k=c_key, lbl=c_label, m=frets_map: self._play_pro_chord(lbl, m)
            )
            btn.pack(side="left", padx=2, pady=4)
            set_tooltip(btn, f"Tocar acorde {c_label} em todas as cordas")

        # 3. Braço da Guitarra / Baixo (Canvas)
        neck_frame = ctk.CTkFrame(self, fg_color="#0F172A", corner_radius=8, border_width=2, border_color="#334155")
        neck_frame.pack(fill="both", expand=True, padx=10, pady=(2, 8))

        self.canvas = ctk.CTkCanvas(neck_frame, bg="#0F172A", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=8, pady=8)
        self.canvas.bind("<Configure>", self._draw_fretboard)
        self.canvas.bind("<Button-1>", self._on_canvas_click)

    def _on_type_changed(self, choice):
        if "4 Cordas" in choice or "Baixo" in choice:
            self.string_count = 4
        else:
            self.string_count = 6
        self.string_states = {s: {"fret": -1, "velocity": 0, "active": False} for s in range(1, self.string_count + 1)}
        self._draw_fretboard()

    def _play_pro_chord(self, chord_name: str, frets_map: dict):
        """Ativa simultaneamente todas as cordas e trastes que formam o acorde Pro."""
        # Limpa anteriores
        for s in range(1, 7):
            self.string_states[s] = {"fret": -1, "velocity": 0, "active": False}

        active_names = []
        for s, f in frets_map.items():
            if s > self.string_count or f < 0:
                continue
            strings_dict = PRO_BASS_STRINGS if self.string_count == 4 else PRO_GUITAR_STRINGS
            open_n = strings_dict[s]["open_note"]
            actual_note = open_n + f
            self.string_states[s] = {"fret": f, "velocity": 110, "active": True}
            active_names.append(midi_note_to_name(actual_note))

            if self.on_fret_click:
                self.on_fret_click(s, f, actual_note)

        self._draw_fretboard()
        self.last_chord_lbl.configure(text=f"Acorde: {chord_name} ({', '.join(active_names)})")
        # Mantém aceso por 500ms e apaga
        self.after(500, self._clear_all_strings)

    def _clear_all_strings(self):
        for s in range(1, self.string_count + 1):
            self.string_states[s]["active"] = False
            self.string_states[s]["fret"] = -1
        self._draw_fretboard()

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
        string_spacing = usable_h / max(1, self.string_count - 1)

        # Identifica a corda clicada (1 a string_count)
        y = event.y
        closest_string = 1
        min_dist = 999999
        for s in range(1, self.string_count + 1):
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
        strings_dict = PRO_BASS_STRINGS if self.string_count == 4 else PRO_GUITAR_STRINGS
        open_note = strings_dict[closest_string]["open_note"]
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
        string_spacing = usable_h / max(1, self.string_count - 1)

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

        # Marcadores de casas (3, 5, 7, 9, 12, 15, 17)
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

        # Configuração das Cordas (6 Cordas Guitarra vs 4 Cordas Baixo)
        if self.string_count == 4:
            string_thicknesses = [2.5, 3.5, 4.5, 6.0]
            string_names = ["1ª G", "2ª D", "3ª A", "4ª E"]
            strings_dict = PRO_BASS_STRINGS
        else:
            string_thicknesses = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
            string_names = ["1ª E", "2ª B", "3ª G", "4ª D", "5ª A", "6ª E"]
            strings_dict = PRO_GUITAR_STRINGS

        for idx, (th, name) in enumerate(zip(string_thicknesses, string_names)):
            string_num = idx + 1
            y = margin_top + (idx * string_spacing)

            is_active = self.string_states.get(string_num, {}).get("active", False)
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
                
                open_note = strings_dict[string_num]["open_note"]
                actual_note = open_note + max(0, fret)
                note_name = midi_note_to_name(actual_note)
                self.canvas.create_text(dot_x, y, text=note_name, fill="#0F172A", font=("Arial", 8, "bold"))

    def set_string_fret(self, string_num: int, fret: int, is_active: bool, velocity: int = 100):
        if string_num in self.string_states:
            self.string_states[string_num]["fret"] = fret
            self.string_states[string_num]["active"] = is_active
            self.string_states[string_num]["velocity"] = velocity
            self._draw_fretboard()

            strings_dict = PRO_BASS_STRINGS if self.string_count == 4 else PRO_GUITAR_STRINGS
            active_notes = []
            for s, st in self.string_states.items():
                if st["active"] and s in strings_dict:
                    open_n = strings_dict[s]["open_note"]
                    note = open_n + max(0, st["fret"])
                    active_notes.append(midi_note_to_name(note))
            
            if active_notes:
                self.last_chord_lbl.configure(text=f"Notas: {' + '.join(active_notes)}")
            else:
                self.last_chord_lbl.configure(text="Notas ativas: Nenhuma")
