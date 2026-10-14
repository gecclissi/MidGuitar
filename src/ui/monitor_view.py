"""
Monitor visual de eventos MIDI em tempo real.
Exibe timestamp, tipo do evento (Note On, Note Off, CC, Whammy) e detalhes.
"""

import customtkinter as ctk

class MonitorView(ctk.CTkFrame):
    def __init__(self, master, max_lines: int = 150, **kwargs):
        super().__init__(master, **kwargs)
        self.max_lines = max_lines
        self.is_paused = False
        self.line_count = 0
        self._init_ui()

    def _init_ui(self):
        # Header do monitor
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(6, 4))

        title = ctk.CTkLabel(header_frame, text="Monitor de Eventos MIDI", font=ctk.CTkFont(size=13, weight="bold"))
        title.pack(side="left")

        # Botão Limpar
        self.btn_clear = ctk.CTkButton(
            header_frame, text="Limpar", width=60, height=24, font=ctk.CTkFont(size=11),
            fg_color="#374151", hover_color="#4B5563", command=self.clear_log
        )
        self.btn_clear.pack(side="right", padx=2)

        # Botão Pausar
        self.btn_pause = ctk.CTkButton(
            header_frame, text="Pausar", width=60, height=24, font=ctk.CTkFont(size=11),
            fg_color="#374151", hover_color="#4B5563", command=self.toggle_pause
        )
        self.btn_pause.pack(side="right", padx=2)

        # Caixa de texto do console
        self.textbox = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color="#E2E8F0",
            fg_color="#0F172A",
            corner_radius=8,
            wrap="none"
        )
        self.textbox.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self.textbox.configure(state="disabled")

    def log(self, timestamp: str, event_type: str, details: str):
        """Adiciona uma nova linha formatada ao monitor."""
        if self.is_paused:
            return

        self.textbox.configure(state="normal")
        line = f"[{timestamp}] {event_type:<10} | {details}\n"
        self.textbox.insert("end", line)
        self.line_count += 1

        # Limita o número de linhas para economizar memória
        if self.line_count > self.max_lines:
            self.textbox.delete("1.0", "2.0")
            self.line_count -= 1

        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def clear_log(self):
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.line_count = 0
        self.textbox.configure(state="disabled")

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        self.btn_pause.configure(
            text="Retomar" if self.is_paused else "Pausar",
            fg_color="#DC2626" if self.is_paused else "#374151"
        )
