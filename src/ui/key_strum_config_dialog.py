"""
Janela de Configuração de Teclas e Palheta do Teclado para o Estúdio Criador.
Permite definir livremente quais teclas do teclado do computador controlam:
- Casa 1 (Verde)
- Casa 2 (Vermelha)
- Casa 3 (Amarela)
- Casa 4 (Azul)
- Casa 5 (Laranja)
- Palheta (Strum Bar) - ex: Espaço, Enter, Setas
- Modo de Palhetada: Livre (Tocou já toca) ou Obrigatória (Casa + Palheta)
"""

import tkinter as tk
import customtkinter as ctk
from typing import Callable, Dict

DEFAULT_KEYS = {
    "green": "a",
    "red": "s",
    "yellow": "j",
    "blue": "k",
    "orange": "l",
    "strum": "space",
    "strum_mode": "free", # "free" ou "strum"
    "vocal_test": "v"
}

KEY_NAMES_FRIENDLY = {
    "space": "Espaço (Space)",
    "return": "Enter",
    "backspace": "Backspace",
    "tab": "Tab",
    "shift_l": "Shift Esquerdo",
    "shift_r": "Shift Direito",
    "control_l": "Ctrl",
    "alt_l": "Alt",
    "up": "Seta Cima",
    "down": "Seta Baixo",
    "left": "Seta Esquerda",
    "right": "Seta Direita",
}

class KeyStrumConfigDialog(ctk.CTkToplevel):
    def __init__(self, master, current_map: Dict[str, str], on_save_callback: Callable[[Dict[str, str]], None]):
        super().__init__(master)
        self.title("⌨️ Configuração de Teclas do Teclado & Palheta")
        self.geometry("540x520")
        self.minsize(500, 480)
        self.resizable(False, False)

        self.key_map = dict(DEFAULT_KEYS)
        if current_map:
            self.key_map.update(current_map)

        self.on_save = on_save_callback
        self.listening_action = None

        self.transient(master)
        self.after(100, self.lift)
        self.after(150, self.focus_force)

        self.bind("<KeyPress>", self._on_key_press_capture)

        self._build_ui()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="#0F172A", height=60, corner_radius=0)
        header.pack(fill="x")

        ctk.CTkLabel(
            header,
            text="⌨️ Mapeamento de Teclas do Computador",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#38BDF8"
        ).pack(anchor="w", padx=16, pady=(10, 2))

        ctk.CTkLabel(
            header,
            text="Personalize quais teclas você quer usar para tocar as notas e a palheta no teclado.",
            font=ctk.CTkFont(size=11),
            text_color="#94A3B8"
        ).pack(anchor="w", padx=16, pady=(0, 8))

        # Painel Central de Teclas
        center_frame = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=8)
        center_frame.pack(fill="both", expand=True, padx=14, pady=10)

        self.btn_widgets = {}

        rows = [
            ("green", "🟩 Casa 1 (Verde):", "#22C55E"),
            ("red", "🟥 Casa 2 (Vermelha):", "#EF4444"),
            ("yellow", "🟨 Casa 3 (Amarela):", "#EAB308"),
            ("blue", "🟦 Casa 4 (Azul):", "#3B82F6"),
            ("orange", "🟧 Casa 5 (Laranja):", "#F97316"),
            ("strum", "⚡ Tecla da Palheta (Strum):", "#A855F7"),
            ("vocal_test", "🎤 Tecla Teste Vocal:", "#EC4899"),
        ]

        for idx, (action_key, label_text, color) in enumerate(rows):
            r_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
            r_frame.pack(fill="x", padx=14, pady=4)

            lbl = ctk.CTkLabel(
                r_frame, text=label_text, width=200, anchor="w",
                font=ctk.CTkFont(size=12, weight="bold"), text_color=color
            )
            lbl.pack(side="left")

            current_k = self.key_map.get(action_key, "")
            display_name = KEY_NAMES_FRIENDLY.get(current_k.lower(), current_k.upper())

            btn = ctk.CTkButton(
                r_frame, text=f"[ {display_name} ]", width=140, height=28,
                fg_color="#334155", hover_color="#475569", font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda act=action_key: self._start_capture(act)
            )
            btn.pack(side="right")
            self.btn_widgets[action_key] = btn

        # Seletor de Modo de Palheta
        mode_box = ctk.CTkFrame(self, fg_color="#0F172A", corner_radius=8)
        mode_box.pack(fill="x", padx=14, pady=(0, 10))

        ctk.CTkLabel(
            mode_box, text="Estilo de Palhetada:",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="#E2E8F0"
        ).pack(anchor="w", padx=12, pady=(6, 2))

        self.mode_var = ctk.StringVar(value=self.key_map.get("strum_mode", "free"))

        r1 = ctk.CTkRadioButton(
            mode_box, text="Palheta Livre (Ao apertar a casa já toca o som na hora - Fácil)",
            variable=self.mode_var, value="free", font=ctk.CTkFont(size=11)
        )
        r1.pack(anchor="w", padx=14, pady=2)

        r2 = ctk.CTkRadioButton(
            mode_box, text="Palheta Obrigatória (Estilo Guitar Hero: segure a casa e aperte a Palheta)",
            variable=self.mode_var, value="strum", font=ctk.CTkFont(size=11)
        )
        r2.pack(anchor="w", padx=14, pady=(2, 8))

        # Status de Captura
        self.status_lbl = ctk.CTkLabel(
            self, text="Clique em qualquer botão acima para mudar sua tecla.",
            font=ctk.CTkFont(size=10), text_color="#94A3B8"
        )
        self.status_lbl.pack(pady=2)

        # Barra Inferior
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=14, pady=(0, 10))

        btn_default = ctk.CTkButton(
            bottom, text="Restaurar Padrão", width=140, height=32,
            fg_color="#334155", command=self._reset_defaults
        )
        btn_default.pack(side="left")

        btn_save = ctk.CTkButton(
            bottom, text="💾 Salvar Teclas", width=160, height=32,
            fg_color="#10B981", hover_color="#059669", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._save_and_close
        )
        btn_save.pack(side="right")

    def _start_capture(self, action_key):
        self.listening_action = action_key
        btn = self.btn_widgets.get(action_key)
        if btn:
            btn.configure(text="[ Aperte tecla... ]", fg_color="#F59E0B")
        self.status_lbl.configure(text=f"Pressione qualquer tecla no seu teclado para definir...", text_color="#F59E0B")

    def _on_key_press_capture(self, event):
        if not self.listening_action:
            return

        key_symbol = event.keysym.lower()
        self.key_map[self.listening_action] = key_symbol

        btn = self.btn_widgets.get(self.listening_action)
        if btn:
            display_name = KEY_NAMES_FRIENDLY.get(key_symbol, key_symbol.upper())
            btn.configure(text=f"[ {display_name} ]", fg_color="#334155")

        self.status_lbl.configure(text=f"Tecla '{key_symbol.upper()}' atribuída com sucesso!", text_color="#10B981")
        self.listening_action = None

    def _reset_defaults(self):
        self.key_map = dict(DEFAULT_KEYS)
        self.mode_var.set("free")
        for act, btn in self.btn_widgets.items():
            k = self.key_map.get(act, "")
            display_name = KEY_NAMES_FRIENDLY.get(k.lower(), k.upper())
            btn.configure(text=f"[ {display_name} ]", fg_color="#334155")
        self.status_lbl.configure(text="Teclas restauradas para o padrão (A, S, J, K, L e Espaço).", text_color="#94A3B8")

    def _save_and_close(self):
        self.key_map["strum_mode"] = self.mode_var.get()
        if self.on_save:
            self.on_save(self.key_map)
        self.destroy()
