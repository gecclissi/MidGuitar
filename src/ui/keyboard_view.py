"""
Visualizador de Teclado MIDI (25 Teclas).
Compatível com o Rock Band 3 Wireless Keyboard / Keytar.
"""

import customtkinter as ctk
from src.utils.instruments import midi_note_to_name

class KeyboardView(ctk.CTkFrame):
    def __init__(self, master, start_note: int = 48, num_keys: int = 25, **kwargs):
        super().__init__(master, **kwargs)
        self.start_note = start_note # C3 = 48 padrão RB3
        self.num_keys = num_keys
        self.active_keys = set()
        self.touch_strip_val = 0.5
        self._init_ui()

    def _init_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(6, 2))

        title = ctk.CTkLabel(header, text="🎹 Teclado Rock Band 3 (25 Teclas / Canal 1)", font=ctk.CTkFont(size=13, weight="bold"), text_color="#A855F7")
        title.pack(side="left")

        self.chord_lbl = ctk.CTkLabel(header, text="Teclas ativas: Nenhuma", font=ctk.CTkFont(size=12), text_color="#94A3B8")
        self.chord_lbl.pack(side="right")

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=10, pady=(4, 10))

        # Painel lateral esquerdo: Touch Strip (Modulation / Pitch Bend)
        touch_frame = ctk.CTkFrame(content, fg_color="#1E293B", width=90, corner_radius=8)
        touch_frame.pack(side="left", fill="y", padx=(0, 8), pady=2)

        ctk.CTkLabel(touch_frame, text="Touch Strip", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(6, 2))
        self.touch_bar = ctk.CTkProgressBar(touch_frame, orientation="vertical", width=22, height=140, progress_color="#A855F7")
        self.touch_bar.set(0.5)
        self.touch_bar.pack(expand=True, pady=(4, 8))

        # Canvas para desenhar as 25 teclas (brancas e pretas)
        keys_frame = ctk.CTkFrame(content, fg_color="#0F172A", corner_radius=8, border_width=2, border_color="#334155")
        keys_frame.pack(side="right", fill="both", expand=True)

        self.canvas = ctk.CTkCanvas(keys_frame, bg="#0F172A", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=6, pady=6)
        self.canvas.bind("<Configure>", self._draw_keyboard)

    def _draw_keyboard(self, event=None):
        self.canvas.delete("all")
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        if width < 100 or height < 50:
            return

        # 25 teclas: C3 a C5 contém 15 teclas brancas e 10 teclas pretas
        # Identifica quais notas são brancas e pretas
        white_notes = []
        black_notes = []

        for n in range(self.start_note, self.start_note + self.num_keys):
            semitone = n % 12
            if semitone in (1, 3, 6, 8, 10): # C#, D#, F#, G#, A#
                black_notes.append(n)
            else:
                white_notes.append(n)

        white_w = width / len(white_notes)
        white_h = height - 10
        black_w = white_w * 0.65
        black_h = white_h * 0.62

        # 1. Desenha teclas brancas
        white_x_positions = {}
        for idx, note in enumerate(white_notes):
            x1 = idx * white_w
            x2 = x1 + white_w
            white_x_positions[note] = x1

            is_active = note in self.active_keys
            fill_color = "#A855F7" if is_active else "#F8FAFC"
            self.canvas.create_rectangle(x1 + 1, 4, x2 - 1, white_h, fill=fill_color, outline="#64748B", width=1)

            # Rótulo na base da tecla
            label_col = "#FFFFFF" if is_active else "#64748B"
            self.canvas.create_text((x1 + x2) / 2, white_h - 10, text=midi_note_to_name(note), fill=label_col, font=("Arial", 8))

        # 2. Desenha teclas pretas
        # A posição das pretas fica entre duas brancas adjacentes
        for note in black_notes:
            prev_white = note - 1
            if prev_white in white_x_positions:
                center_x = white_x_positions[prev_white] + white_w
                x1 = center_x - (black_w / 2)
                x2 = center_x + (black_w / 2)

                is_active = note in self.active_keys
                fill_color = "#C084FC" if is_active else "#1E293B"
                self.canvas.create_rectangle(x1, 4, x2, black_h, fill=fill_color, outline="#020617", width=1)

                # Rótulo na tecla preta
                if is_active:
                    self.canvas.create_text((x1 + x2) / 2, black_h - 12, text=midi_note_to_name(note), fill="#FFFFFF", font=("Arial", 7, "bold"))

    def set_key_state(self, note: int, is_active: bool):
        if is_active:
            self.active_keys.add(note)
        else:
            self.active_keys.discard(note)
        self._draw_keyboard()

        if self.active_keys:
            names = [midi_note_to_name(n) for n in sorted(self.active_keys)]
            self.chord_lbl.configure(text=f"Teclas ativas: {' + '.join(names)}")
        else:
            self.chord_lbl.configure(text="Teclas ativas: Nenhuma")

    def set_touch_strip(self, normalized_val: float):
        """Atualiza a fita touch ribbon (0.0 a 1.0)."""
        val = max(0.0, min(1.0, normalized_val))
        self.touch_bar.set(val)
