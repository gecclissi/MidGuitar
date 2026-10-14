"""
Widget visual de Guitarra e Braço (Fretboard) para o MidGuitar.
Renderiza os 5 botões de casas (Verde, Vermelho, Amarelo, Azul, Laranja),
a palheta (Strum Bar) e a alavanca (Whammy Bar) em tempo real.
"""

import customtkinter as ctk

FRET_COLORS = {
    "green": {"idle": "#166534", "active": "#22C55E", "text": "Verde"},
    "red": {"idle": "#991B1B", "active": "#EF4444", "text": "Vermelho"},
    "yellow": {"idle": "#854D0E", "active": "#FACC15", "text": "Amarelo"},
    "blue": {"idle": "#1E40AF", "active": "#3B82F6", "text": "Azul"},
    "orange": {"idle": "#9A3412", "active": "#FB923C", "text": "Laranja"},
}

class FretboardView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.fret_buttons = {}
        self.fret_labels = {}
        self._init_ui()

    def _init_ui(self):
        # Título da seção
        title = ctk.CTkLabel(self, text="Braço da Guitarra (Fretboard)", font=ctk.CTkFont(size=14, weight="bold"))
        title.pack(pady=(8, 4))

        # Container dos 5 trastes
        frets_container = ctk.CTkFrame(self, fg_color="transparent")
        frets_container.pack(fill="x", padx=12, pady=6)

        for fret_key, color_info in FRET_COLORS.items():
            fret_frame = ctk.CTkFrame(frets_container, fg_color="transparent")
            fret_frame.pack(side="left", expand=True, fill="both", padx=4)

            # Botão visual
            btn = ctk.CTkButton(
                fret_frame,
                text=color_info["text"],
                fg_color=color_info["idle"],
                hover_color=color_info["active"],
                font=ctk.CTkFont(size=13, weight="bold"),
                height=52,
                corner_radius=10,
                border_width=2,
                border_color="#374151"
            )
            btn.pack(fill="x")
            self.fret_buttons[fret_key] = btn

            # Label de nota/acorde mapeado abaixo do botão
            note_lbl = ctk.CTkLabel(fret_frame, text="--", font=ctk.CTkFont(size=11), text_color="#9CA3AF")
            note_lbl.pack(pady=(2, 0))
            self.fret_labels[fret_key] = note_lbl

        # Separador visual
        sep = ctk.CTkFrame(self, height=2, fg_color="#374151")
        sep.pack(fill="x", padx=12, pady=10)

        # Seção de Palheta (Strum) e Alavanca (Whammy)
        controls_container = ctk.CTkFrame(self, fg_color="transparent")
        controls_container.pack(fill="x", padx=12, pady=(0, 10))

        # Strum Bar
        strum_frame = ctk.CTkFrame(controls_container, fg_color="#1E293B", corner_radius=8, width=160)
        strum_frame.pack(side="left", expand=True, fill="both", padx=4, pady=2)

        ctk.CTkLabel(strum_frame, text="Palheta (Strum)", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(4, 2))
        
        strum_btns_frame = ctk.CTkFrame(strum_frame, fg_color="transparent")
        strum_btns_frame.pack(pady=4)

        self.strum_up_indicator = ctk.CTkButton(
            strum_btns_frame, text="▲ Cima", width=70, height=28, fg_color="#334155", state="disabled"
        )
        self.strum_up_indicator.pack(side="left", padx=3)

        self.strum_down_indicator = ctk.CTkButton(
            strum_btns_frame, text="▼ Baixo", width=70, height=28, fg_color="#334155", state="disabled"
        )
        self.strum_down_indicator.pack(side="left", padx=3)

        # Whammy Bar
        whammy_frame = ctk.CTkFrame(controls_container, fg_color="#1E293B", corner_radius=8)
        whammy_frame.pack(side="right", expand=True, fill="both", padx=4, pady=2)

        ctk.CTkLabel(whammy_frame, text="Alavanca (Whammy Bar)", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(4, 2))
        self.whammy_progress = ctk.CTkProgressBar(whammy_frame, height=14, corner_radius=6, progress_color="#6366F1")
        self.whammy_progress.set(0.5) # Centro = 0
        self.whammy_progress.pack(fill="x", padx=14, pady=(6, 8))

    def set_fret_state(self, fret: str, is_active: bool):
        """Acende ou apaga visualmente o botão da casa."""
        if fret in self.fret_buttons:
            color = FRET_COLORS[fret]["active"] if is_active else FRET_COLORS[fret]["idle"]
            border = "#FFFFFF" if is_active else "#374151"
            self.fret_buttons[fret].configure(fg_color=color, border_color=border)

    def set_fret_label(self, fret: str, text: str):
        """Atualiza o texto da nota/acorde mapeado."""
        if fret in self.fret_labels:
            self.fret_labels[fret].configure(text=text)

    def set_strum_state(self, is_down: bool, is_active: bool):
        """Destaca o indicador de palheta para cima ou para baixo."""
        indicator = self.strum_down_indicator if is_down else self.strum_up_indicator
        color = "#38BDF8" if is_active else "#334155"
        indicator.configure(fg_color=color)

    def set_whammy_value(self, normalized_val: float):
        """Atualiza a barra de progresso da alavanca (-1.0 a +1.0 mapeado para 0.0 a 1.0)."""
        clamped = max(-1.0, min(1.0, normalized_val))
        ui_val = (clamped + 1.0) / 2.0
        self.whammy_progress.set(ui_val)

    def update_fret_labels_from_preset(self, preset: dict):
        """Atualiza todas as legendas das casas a partir do preset atual."""
        frets = preset.get("frets", {})
        for fret in FRET_COLORS:
            if fret in frets:
                name = frets[fret].get("name", "")
                self.set_fret_label(fret, name)
            else:
                self.set_fret_label(fret, "--")
