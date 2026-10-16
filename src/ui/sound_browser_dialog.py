"""
Janela de Exploração e Seleção Completa de Sons MIDI (128 Instrumentos GM1).
Destaque especial para Sons Espaciais, Efeitos Sci-Fi, Sintetizadores Futuristas e FX.
Permite buscar por nome, filtrar por categoria, testar o som na hora e aplicar a tudo em 1 clique.
"""

import customtkinter as ctk
from src.utils.instruments import (
    GM_INSTRUMENTS, GM_CATEGORIES, INSTRUMENT_PORTUGUESE_NAMES
)
from src.ui.tooltip import set_tooltip

class SoundBrowserDialog(ctk.CTkToplevel):
    def __init__(self, master, current_instrument_id: int = 29, on_select_instrument=None, audio_engine=None):
        super().__init__(master)

        self.title("🌌 Explorador de Sons & Efeitos Espaciais (Banco Completo - 128 Sons)")
        self.geometry("820x620")
        self.minsize(700, 480)
        self.resizable(True, True)

        self.selected_id = current_instrument_id
        self.on_select_instrument = on_select_instrument
        self.audio = audio_engine
        self.current_category = "🌌 Sons Espaciais e Sci-Fi"

        # Mantém foco modal
        self.transient(master)
        self.after(100, self.lift)
        self.after(150, self.focus_force)

        self._build_ui()
        self._populate_list()

    def _build_ui(self):
        # 1. Header estilizado
        header = ctk.CTkFrame(self, fg_color="#0B132B", height=60, corner_radius=0)
        header.pack(fill="x", side="top")

        title_lbl = ctk.CTkLabel(
            header,
            text="🌌 Explorador de Sons & Efeitos Especiais (128 Instrumentos)",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#38BDF8"
        )
        title_lbl.pack(anchor="w", padx=16, pady=(10, 2))

        subtitle_lbl = ctk.CTkLabel(
            header,
            text="Ouça os sons sci-fi, espaciais, pads atmosféricos, sintetizadores e guitarras. Clique em 'Usar Som' para tocar!",
            font=ctk.CTkFont(size=11),
            text_color="#94A3B8"
        )
        subtitle_lbl.pack(anchor="w", padx=16, pady=(0, 8))

        # 2. Barra de Filtro e Busca
        filter_bar = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=8)
        filter_bar.pack(fill="x", padx=14, pady=(8, 4))

        # Busca por texto
        ctk.CTkLabel(filter_bar, text="🔍 Buscar:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(10, 4), pady=6)
        self.search_entry = ctk.CTkEntry(filter_bar, width=170, height=28, placeholder_text="Ex: espacial, laser, chuva...")
        self.search_entry.pack(side="left", padx=4, pady=6)
        self.search_entry.bind("<KeyRelease>", lambda e: self._populate_list())
        set_tooltip(self.search_entry, "Digite para filtrar instantaneamente os 128 sons")

        # Categoria
        ctk.CTkLabel(filter_bar, text="📁 Categoria:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(12, 4), pady=6)
        cat_options = ["⭐ Todos os 128 Sons"] + list(GM_CATEGORIES.keys())
        self.category_combo = ctk.CTkComboBox(
            filter_bar, width=230, height=28, values=cat_options, command=self._on_category_changed
        )
        self.category_combo.pack(side="left", padx=4, pady=6)
        self.category_combo.set(self.current_category)
        set_tooltip(self.category_combo, "Filtre por tipo de som (Espaciais, Sintetizadores, Efeitos, Guitarras, etc.)")

        # Botão Pânico de Prévia
        btn_stop = ctk.CTkButton(
            filter_bar, text="⏹️ Parar Som", width=95, height=28,
            fg_color="#DC2626", hover_color="#B91C1C", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._stop_preview
        )
        btn_stop.pack(side="right", padx=(4, 10), pady=6)
        set_tooltip(btn_stop, "Interrompe qualquer prévia de áudio tocando agora")

        # 3. Lista Rolável de Instrumentos
        self.list_container = ctk.CTkScrollableFrame(self, fg_color="#0F172A", corner_radius=8)
        self.list_container.pack(fill="both", expand=True, padx=14, pady=4)

        # 4. Rodapé
        footer = ctk.CTkFrame(self, fg_color="#1E293B", height=45, corner_radius=8)
        footer.pack(fill="x", padx=14, pady=(4, 10))

        self.selected_label = ctk.CTkLabel(
            footer,
            text=f"Som Atual: #{self.selected_id:03d} - {INSTRUMENT_PORTUGUESE_NAMES.get(self.selected_id, 'Instrumento')}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#FACC15"
        )
        self.selected_label.pack(side="left", padx=14, pady=8)

        btn_close = ctk.CTkButton(
            footer, text="Concluído", width=100, height=28,
            fg_color="#334155", hover_color="#475569", font=ctk.CTkFont(size=11, weight="bold"),
            command=self.destroy
        )
        btn_close.pack(side="right", padx=10, pady=8)

    def _on_category_changed(self, choice: str):
        self.current_category = choice
        self._populate_list()

    def _populate_list(self):
        # Limpa itens anteriores
        for child in self.list_container.winfo_children():
            child.destroy()

        search_query = self.search_entry.get().strip().lower()

        # Determina quais IDs de instrumentos exibir
        if self.current_category == "⭐ Todos os 128 Sons":
            allowed_ids = set(range(128))
        else:
            allowed_ids = set(GM_CATEGORIES.get(self.current_category, range(128)))

        # Filtra os instrumentos
        displayed_items = []
        for num, eng_name, cat in GM_INSTRUMENTS:
            if num not in allowed_ids:
                continue
            pt_name = INSTRUMENT_PORTUGUESE_NAMES.get(num, eng_name)
            searchable_text = f"{num} {eng_name} {pt_name} {cat}".lower()
            if search_query and (search_query not in searchable_text):
                continue
            displayed_items.append((num, pt_name, eng_name, cat))

        if not displayed_items:
            empty_lbl = ctk.CTkLabel(
                self.list_container,
                text="Nenhum som encontrado para esta busca.",
                font=ctk.CTkFont(size=13),
                text_color="#64748B"
            )
            empty_lbl.pack(pady=40)
            return

        # Renderiza os cartões de som
        for num, pt_name, eng_name, cat in displayed_items:
            is_active = (num == self.selected_id)
            card_bg = "#1E293B" if not is_active else "#1E3A5F"
            border_color = "#38BDF8" if is_active else "#334155"

            card = ctk.CTkFrame(
                self.list_container,
                fg_color=card_bg,
                corner_radius=6,
                border_width=2 if is_active else 1,
                border_color=border_color
            )
            card.pack(fill="x", padx=4, pady=3)

            # Informações do som
            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=8, pady=4)

            title_row = ctk.CTkFrame(info_frame, fg_color="transparent")
            title_row.pack(anchor="w", fill="x")

            id_badge = ctk.CTkLabel(
                title_row,
                text=f"#{num:03d}",
                font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
                fg_color="#334155",
                corner_radius=4,
                padx=6,
                pady=1
            )
            id_badge.pack(side="left", padx=(0, 6))

            name_lbl = ctk.CTkLabel(
                title_row,
                text=pt_name,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#F8FAFC"
            )
            name_lbl.pack(side="left")

            sub_lbl = ctk.CTkLabel(
                info_frame,
                text=f"GM: {eng_name} | {cat}",
                font=ctk.CTkFont(size=10),
                text_color="#94A3B8"
            )
            sub_lbl.pack(anchor="w", pady=(1, 0))

            # Ações à direita
            btn_box = ctk.CTkFrame(card, fg_color="transparent")
            btn_box.pack(side="right", padx=6, pady=4)

            # Botão Testar / Ouvir
            btn_test = ctk.CTkButton(
                btn_box,
                text="🔊 Ouvir",
                width=75,
                height=26,
                fg_color="#3B82F6",
                hover_color="#2563EB",
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda n=num: self._preview_sound(n)
            )
            btn_test.pack(side="left", padx=3)
            set_tooltip(btn_test, "Ouvir uma prévia musical deste som agora mesmo")

            # Botão Usar este Som em Tudo
            btn_use = ctk.CTkButton(
                btn_box,
                text="✅ Usar Som",
                width=90,
                height=26,
                fg_color="#10B981" if not is_active else "#059669",
                hover_color="#059669",
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda n=num, name=pt_name: self._apply_instrument(n, name)
            )
            btn_use.pack(side="left", padx=3)
            set_tooltip(btn_use, "Aplica este som a todas as casas da guitarra, teclado e sintetizador")

    def _preview_sound(self, inst_id: int):
        """Toca um arpeggio de teste do instrumento."""
        if not self.audio:
            return
        self.audio.set_instrument(inst_id)
        # Toca notas espaçadas de demonstração
        self.audio.play_note(60, 110)
        self.after(140, lambda: self.audio.play_note(64, 110))
        self.after(280, lambda: self.audio.play_note(67, 110))
        self.after(420, lambda: self.audio.play_note(72, 110))
        self.after(900, self._stop_preview)

    def _stop_preview(self):
        if self.audio:
            self.audio.stop_all_notes()

    def _apply_instrument(self, inst_id: int, inst_name: str):
        self.selected_id = inst_id
        self.selected_label.configure(text=f"Som Atual: #{inst_id:03d} - {inst_name}")
        if self.audio:
            self.audio.set_instrument(inst_id)
        if self.on_select_instrument:
            self.on_select_instrument(inst_id)
        self._populate_list()
