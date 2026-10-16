"""
Widget visual de Guitarra e Braço (Fretboard) para o MidGuitar.
Permite trocar o som de todas as casas de uma vez, selecionar estilos de acordes
rápidos e clicar nos botões para ouvir/testar as notas imediatamente.
"""

import customtkinter as ctk
from src.ui.tooltip import set_tooltip
from src.utils.instruments import POPULAR_INSTRUMENTS, QUICK_FRET_PRESETS

FRET_COLORS = {
    "green": {"idle": "#166534", "active": "#22C55E", "text": "Verde", "num": "1"},
    "red": {"idle": "#991B1B", "active": "#EF4444", "text": "Vermelho", "num": "2"},
    "yellow": {"idle": "#854D0E", "active": "#FACC15", "text": "Amarelo", "num": "3"},
    "blue": {"idle": "#1E40AF", "active": "#3B82F6", "text": "Azul", "num": "4"},
    "orange": {"idle": "#9A3412", "active": "#FB923C", "text": "Laranja", "num": "5"},
}

class FretboardView(ctk.CTkFrame):
    def __init__(self, master, on_fret_click=None, on_open_mapping=None, on_open_sound_manager=None, on_quick_preset=None, on_instrument_change=None, on_open_sound_browser=None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_fret_click = on_fret_click
        self.on_open_mapping = on_open_mapping
        self.on_open_sound_manager = on_open_sound_manager
        self.on_quick_preset = on_quick_preset
        self.on_instrument_change = on_instrument_change
        self.on_open_sound_browser = on_open_sound_browser

        self.fret_buttons = {}
        self.fret_labels = {}
        self._init_ui()

    def _init_ui(self):
        # -------------------------------------------------------------
        # BARRA DE AÇÃO DIRETA (MUDAR TUDO DE UMA VEZ & SONS ESPACIAIS)
        # -------------------------------------------------------------
        action_bar = ctk.CTkFrame(self, fg_color="#182234", corner_radius=8)
        action_bar.pack(fill="x", padx=8, pady=(4, 6))

        # Linha 1: Som Geral e Estilo de Acordes
        row1 = ctk.CTkFrame(action_bar, fg_color="transparent")
        row1.pack(fill="x", padx=6, pady=(4, 2))

        ctk.CTkLabel(row1, text="🎵 Som:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#38BDF8").pack(side="left", padx=(4, 4))
        
        self.inst_options = [f"{num:03d} - {name}" for num, name in POPULAR_INSTRUMENTS]
        self.inst_combo = ctk.CTkComboBox(
            row1, width=220, height=26, values=self.inst_options,
            command=self._on_instrument_selected
        )
        self.inst_combo.pack(side="left", padx=2)
        self.inst_combo.set(self.inst_options[0])
        set_tooltip(self.inst_combo, "Muda o som de TODAS as casas de uma vez só!\nEscolha Guitarra, Sons Espaciais, Violão, Baixo, etc.")

        # Botão para abrir o Explorador dos 128 Sons (Espaciais, Sci-Fi, Efeitos)
        if self.on_open_sound_browser:
            btn_browser = ctk.CTkButton(
                row1, text="🌌 Explorar 128 Sons...", width=145, height=26,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#0284C7", hover_color="#0369A1", command=self.on_open_sound_browser
            )
            btn_browser.pack(side="left", padx=(6, 4))
            set_tooltip(btn_browser, "Abre a lista com todos os 128 sons MIDI, efeitos sci-fi, espaciais, pads e sintetizadores!")

        ctk.CTkLabel(row1, text="⚡ Estilo:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#F59E0B").pack(side="left", padx=(10, 4))
        
        self.preset_options = list(QUICK_FRET_PRESETS.keys())
        self.preset_combo = ctk.CTkComboBox(
            row1, width=210, height=26, values=self.preset_options,
            command=self._on_quick_preset_selected
        )
        self.preset_combo.pack(side="left", padx=2)
        self.preset_combo.set(self.preset_options[0])
        set_tooltip(self.preset_combo, "Muda as notas e acordes de todas as 5 casas de uma vez!\n(Rock Power Chords, Viagem Espacial, Synthwave, Acordes, Metal)")

        # Linha 2: Ações de Customização (Espaçada e Responsiva)
        row2 = ctk.CTkFrame(action_bar, fg_color="transparent")
        row2.pack(fill="x", padx=6, pady=(2, 4))

        if self.on_open_mapping:
            btn_map = ctk.CTkButton(
                row2, text="🎛️ Editar Mapeamento Individual", width=190, height=24,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#334155", hover_color="#475569", command=self.on_open_mapping
            )
            btn_map.pack(side="left", padx=(4, 4))
            set_tooltip(btn_map, "Abre a tela detalhada para escolher nota por nota se desejar")

        if self.on_open_sound_manager:
            btn_sound = ctk.CTkButton(
                row2, text="📁 Importar Áudios (.WAV / .MP3)", width=180, height=24,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#8B5CF6", hover_color="#7C3AED", command=self.on_open_sound_manager
            )
            btn_sound.pack(side="left", padx=4)
            set_tooltip(btn_sound, "Importe arquivos de áudio reais (.wav / .mp3) do seu computador")

        # -------------------------------------------------------------
        # OS 5 BOTÕES / CASAS DA GUITARRA (CLIQUE DIRETO)
        # -------------------------------------------------------------
        frets_container = ctk.CTkFrame(self, fg_color="transparent")
        frets_container.pack(fill="x", padx=8, pady=4)

        for fret_key, color_info in FRET_COLORS.items():
            fret_frame = ctk.CTkFrame(frets_container, fg_color="transparent")
            fret_frame.pack(side="left", expand=True, fill="both", padx=4)

            # Botão clicável para ouvir a nota
            btn = ctk.CTkButton(
                fret_frame,
                text=color_info["text"],
                fg_color=color_info["idle"],
                hover_color=color_info["active"],
                font=ctk.CTkFont(size=14, weight="bold"),
                height=56,
                corner_radius=10,
                border_width=2,
                border_color="#374151",
                command=lambda fk=fret_key: self._on_btn_clicked(fk)
            )
            btn.pack(fill="x")
            self.fret_buttons[fret_key] = btn

            # Dica flutuante explicativa em cada botão
            set_tooltip(
                btn,
                f"Casa {color_info['text']} (Botão {color_info['num']})\n"
                "• Clique com o mouse para ouvir o som na hora!\n"
                "• Ou aperte o botão correspondente no seu controle/guitarra."
            )

            # Label de nota/acorde mapeado abaixo do botão
            note_lbl = ctk.CTkLabel(fret_frame, text="--", font=ctk.CTkFont(size=11, weight="bold"), text_color="#E2E8F0")
            note_lbl.pack(pady=(2, 0))
            self.fret_labels[fret_key] = note_lbl
            set_tooltip(note_lbl, "Acorde ou nota atual disparada por este botão")

        # -------------------------------------------------------------
        # SEÇÃO DE PALHETA E ALAVANCA
        # -------------------------------------------------------------
        controls_container = ctk.CTkFrame(self, fg_color="transparent")
        controls_container.pack(fill="x", padx=8, pady=(4, 6))

        # Strum Bar
        strum_frame = ctk.CTkFrame(controls_container, fg_color="#1E293B", corner_radius=8, width=160)
        strum_frame.pack(side="left", expand=True, fill="both", padx=4, pady=2)

        lbl_strum = ctk.CTkLabel(strum_frame, text="Palheta (Strum)", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94A3B8")
        lbl_strum.pack(pady=(4, 2))
        set_tooltip(strum_frame, "Mostra a palhetada para cima ou para baixo do controle de guitarra")
        
        strum_btns_frame = ctk.CTkFrame(strum_frame, fg_color="transparent")
        strum_btns_frame.pack(pady=4)

        self.strum_up_indicator = ctk.CTkButton(
            strum_btns_frame, text="▲ Cima", width=70, height=26, fg_color="#334155", state="disabled"
        )
        self.strum_up_indicator.pack(side="left", padx=3)

        self.strum_down_indicator = ctk.CTkButton(
            strum_btns_frame, text="▼ Baixo", width=70, height=26, fg_color="#334155", state="disabled"
        )
        self.strum_down_indicator.pack(side="left", padx=3)

        # Whammy Bar
        whammy_frame = ctk.CTkFrame(controls_container, fg_color="#1E293B", corner_radius=8)
        whammy_frame.pack(side="right", expand=True, fill="both", padx=4, pady=2)

        lbl_whammy = ctk.CTkLabel(whammy_frame, text="Alavanca (Whammy)", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94A3B8")
        lbl_whammy.pack(pady=(4, 2))
        set_tooltip(whammy_frame, "Mostra a alavanca de whammy da guitarra (Pitch Bend que altera o tom)")

        self.whammy_bar = ctk.CTkProgressBar(whammy_frame, height=12, progress_color="#38BDF8")
        self.whammy_bar.pack(fill="x", padx=14, pady=(6, 8))
        self.whammy_bar.set(0)

    def _on_btn_clicked(self, fret_name: str):
        """Ativa visualmente o botão e dispara callback de áudio."""
        self.set_fret_state(fret_name, True)
        self.after(200, lambda: self.set_fret_state(fret_name, False))
        if self.on_fret_click:
            self.on_fret_click(fret_name)

    def _on_instrument_selected(self, choice_str: str):
        """Disparado quando o usuário escolhe um instrumento direto na guitarra."""
        try:
            inst_id = int(choice_str.split(" - ")[0])
            if self.on_instrument_change:
                self.on_instrument_change(inst_id)
        except Exception:
            pass

    def _on_quick_preset_selected(self, preset_name: str):
        """Aplica o preset rápido de acordes para todas as 5 casas de uma vez."""
        if preset_name in QUICK_FRET_PRESETS:
            preset_data = QUICK_FRET_PRESETS[preset_name]
            for fret_key, info in preset_data.items():
                if fret_key in self.fret_labels:
                    self.fret_labels[fret_key].configure(text=info.get("label", "--"))
            if self.on_quick_preset:
                self.on_quick_preset(preset_name, preset_data)

    def set_fret_state(self, fret_name: str, is_active: bool):
        if fret_name in self.fret_buttons:
            color = FRET_COLORS[fret_name]["active"] if is_active else FRET_COLORS[fret_name]["idle"]
            self.fret_buttons[fret_name].configure(fg_color=color)

    def set_strum_state(self, up_active: bool, down_active: bool):
        self.strum_up_indicator.configure(fg_color="#38BDF8" if up_active else "#334155")
        self.strum_down_indicator.configure(fg_color="#38BDF8" if down_active else "#334155")

    def set_whammy_value(self, value: float):
        norm = max(0.0, min(1.0, value))
        self.whammy_bar.set(norm)

    def update_fret_labels_from_preset(self, preset: dict):
        frets = preset.get("frets", {})
        for fret_key, info in frets.items():
            if fret_key in self.fret_labels:
                label_text = info.get("label", "")
                if not label_text and "notes" in info:
                    label_text = str(info["notes"])
                self.fret_labels[fret_key].configure(text=label_text)

    def set_selected_instrument(self, inst_id: int):
        """Atualiza a seleção do combobox de instrumentos se disponível."""
        target_prefix = f"{inst_id:03d} -"
        for opt in self.inst_options:
            if opt.startswith(target_prefix):
                self.inst_combo.set(opt)
                return
        # Se for um dos 128 que não está na lista curta de populares, adiciona temporariamente
        from src.utils.instruments import INSTRUMENT_PORTUGUESE_NAMES, INSTRUMENT_NAMES
        name = INSTRUMENT_PORTUGUESE_NAMES.get(inst_id, INSTRUMENT_NAMES.get(inst_id, f"Instrumento {inst_id}"))
        new_opt = f"{inst_id:03d} - {name}"
        if new_opt not in self.inst_options:
            self.inst_options.insert(0, new_opt)
            self.inst_combo.configure(values=self.inst_options)
        self.inst_combo.set(new_opt)
