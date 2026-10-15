"""
Mapeador Avançado de Teclas e Sons (Individual e em Lote).
Permite configurar um som/barulho específico para cada tecla/pad/botão,
ou selecionar várias teclas ("de monte") e aplicar instrumentos, sons de bateria
ou importar uma pasta inteira de arquivos de áudio (.wav / .mp3) em lote!
"""

import os
import json
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from src.utils.instruments import GM_INSTRUMENTS, GM_DRUM_SOUNDS, midi_note_to_name
from src.audio.engine import AudioEngine

# 25 Teclas do Rock Band 3 Wireless Keyboard (C3 a C5 / Notas 48 a 72)
KEYBOARD_NOTES = list(range(48, 73))

class BatchKeyMapperDialog(ctk.CTkToplevel):
    def __init__(self, master, audio_engine: AudioEngine, current_map: dict, on_save_callback=None):
        super().__init__(master)

        self.title("🎹 Mapeador Avançado de Teclas & Sons (Individual e em Lote)")
        self.geometry("880x700")
        self.minsize(820, 600)
        self.resizable(True, True)

        self.audio = audio_engine
        self.key_map = current_map.copy() if current_map else {}
        self.on_save_callback = on_save_callback

        # Controle de seleção das teclas
        self.key_check_vars = {} # note_int -> ctk.BooleanVar
        self.key_widgets = {}    # note_int -> {card, badge, test_btn}

        # Foco da janela
        self.transient(master)
        self.after(100, self.lift)
        self.after(150, self.focus_force)

        self._build_ui()

    def _build_ui(self):
        # -------------------------------------------------------------
        # 1. HEADER
        # -------------------------------------------------------------
        header = ctk.CTkFrame(self, fg_color="#0F172A", height=75, corner_radius=0)
        header.pack(fill="x", side="top")

        h_title = ctk.CTkLabel(
            header, text="🎹 Mapeador de Sons por Tecla (Individual & Em Lote)",
            font=ctk.CTkFont(size=18, weight="bold"), text_color="#38BDF8"
        )
        h_title.pack(anchor="w", padx=20, pady=(12, 2))

        h_desc = ctk.CTkLabel(
            header,
            text="Personalize cada tecla com um barulho diferente ou selecione várias para configurar de uma só vez!",
            font=ctk.CTkFont(size=12), text_color="#94A3B8"
        )
        h_desc.pack(anchor="w", padx=20, pady=(0, 10))

        # -------------------------------------------------------------
        # 2. PAINEL DE AÇÃO EM LOTE ("CONFIGURAR DE MONTE")
        # -------------------------------------------------------------
        batch_card = ctk.CTkFrame(self, fg_color="#182234", corner_radius=10, border_width=1, border_color="#334155")
        batch_card.pack(fill="x", padx=16, pady=(10, 6))

        # Título da seção de lote
        batch_title_row = ctk.CTkFrame(batch_card, fg_color="transparent")
        batch_title_row.pack(fill="x", padx=12, pady=(8, 4))

        ctk.CTkLabel(
            batch_title_row, text="⚡ CONFIGURAR DE MONTE (SELEÇÃO EM LOTE):",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#F59E0B"
        ).pack(side="left")

        self.selected_count_lbl = ctk.CTkLabel(
            batch_title_row, text="0 teclas selecionadas",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#38BDF8"
        )
        self.selected_count_lbl.pack(side="right")

        # Linha 1 de Seleção Rápida de Teclas
        sel_row = ctk.CTkFrame(batch_card, fg_color="transparent")
        sel_row.pack(fill="x", padx=12, pady=(2, 6))

        ctk.CTkLabel(sel_row, text="Marcar:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(0, 4))

        btn_sel_all = ctk.CTkButton(
            sel_row, text="☑️ Todas (25)", width=90, height=26,
            fg_color="#334155", hover_color="#475569", font=ctk.CTkFont(size=11),
            command=self._select_all_keys
        )
        btn_sel_all.pack(side="left", padx=2)

        btn_desel = ctk.CTkButton(
            sel_row, text="⬜ Nenhuma", width=85, height=26,
            fg_color="#334155", hover_color="#475569", font=ctk.CTkFont(size=11),
            command=self._deselect_all_keys
        )
        btn_desel.pack(side="left", padx=2)

        btn_white = ctk.CTkButton(
            sel_row, text="⚪ Brancas", width=80, height=26,
            fg_color="#334155", hover_color="#475569", font=ctk.CTkFont(size=11),
            command=self._select_white_keys
        )
        btn_white.pack(side="left", padx=2)

        btn_black = ctk.CTkButton(
            sel_row, text="⚫ Pretas", width=75, height=26,
            fg_color="#334155", hover_color="#475569", font=ctk.CTkFont(size=11),
            command=self._select_black_keys
        )
        btn_black.pack(side="left", padx=2)

        btn_oct1 = ctk.CTkButton(
            sel_row, text="1️⃣ Oitava C3-B3", width=105, height=26,
            fg_color="#334155", hover_color="#475569", font=ctk.CTkFont(size=11),
            command=self._select_octave_1
        )
        btn_oct1.pack(side="left", padx=2)

        btn_oct2 = ctk.CTkButton(
            sel_row, text="2️⃣ Oitava C4-C5", width=105, height=26,
            fg_color="#334155", hover_color="#475569", font=ctk.CTkFont(size=11),
            command=self._select_octave_2
        )
        btn_oct2.pack(side="left", padx=2)

        # Linha 2: Ações de Aplicação de Sons
        act_row1 = ctk.CTkFrame(batch_card, fg_color="transparent")
        act_row1.pack(fill="x", padx=12, pady=(4, 4))

        ctk.CTkLabel(act_row1, text="Instrumento GM:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(0, 4))
        self.batch_inst_options = [f"{num:03d} - {name}" for num, name, cat in GM_INSTRUMENTS]
        self.batch_inst_combo = ctk.CTkComboBox(act_row1, width=220, values=self.batch_inst_options)
        self.batch_inst_combo.pack(side="left", padx=2)
        self.batch_inst_combo.set(self.batch_inst_options[0])

        btn_apply_inst = ctk.CTkButton(
            act_row1, text="⚡ Aplicar às Selecionadas", width=160, height=28,
            fg_color="#3B82F6", hover_color="#2563EB", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._apply_instrument_to_selected
        )
        btn_apply_inst.pack(side="left", padx=6)

        ctk.CTkLabel(act_row1, text="Percussão/Bateria:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(10, 4))
        self.batch_drum_options = [f"{note:02d} - {name}" for note, name in GM_DRUM_SOUNDS]
        self.batch_drum_combo = ctk.CTkComboBox(act_row1, width=170, values=self.batch_drum_options)
        self.batch_drum_combo.pack(side="left", padx=2)
        self.batch_drum_combo.set(self.batch_drum_options[0])

        btn_apply_drum = ctk.CTkButton(
            act_row1, text="⚡ Aplicar Percussão", width=140, height=28,
            fg_color="#F59E0B", hover_color="#D97706", text_color="#0F172A", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._apply_drum_to_selected
        )
        btn_apply_drum.pack(side="left", padx=4)

        # Linha 3: Arquivos de Áudio e Pasta em Lote
        act_row2 = ctk.CTkFrame(batch_card, fg_color="transparent")
        act_row2.pack(fill="x", padx=12, pady=(4, 10))

        # Botão Super Especial: Carregar Pasta Inteira em Lote
        btn_batch_folder = ctk.CTkButton(
            act_row2, text="📂 Importar Pasta de Sons (.WAV / .MP3) em Lote", width=290, height=28,
            fg_color="#8B5CF6", hover_color="#7C3AED", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._batch_import_folder
        )
        btn_batch_folder.pack(side="left", padx=(0, 6))

        # Botão Aplicar 1 Som a Todas
        btn_single_sample = ctk.CTkButton(
            act_row2, text="📁 Aplicar 1 Áudio às Selecionadas", width=220, height=28,
            fg_color="#10B981", hover_color="#059669", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._batch_import_single_file
        )
        btn_single_sample.pack(side="left", padx=4)

        # Botão Limpar Selecionadas
        btn_clear_sel = ctk.CTkButton(
            act_row2, text="🗑️ Restaurar Padrão", width=140, height=28,
            fg_color="#DC2626", hover_color="#B91C1C", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._clear_selected_keys
        )
        btn_clear_sel.pack(side="right", padx=2)

        # -------------------------------------------------------------
        # 3. LISTA ROLÁVEL DE TODAS AS 25 TECLAS
        # -------------------------------------------------------------
        list_container = ctk.CTkFrame(self, fg_color="transparent")
        list_container.pack(fill="both", expand=True, padx=16, pady=4)

        ctk.CTkLabel(
            list_container, text="📋 LISTA DE TECLAS DO TECLADO (Clique no botão '🔊 Ouvir' para validar o som de cada uma):",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="#94A3B8"
        ).pack(anchor="w", pady=(0, 4))

        self.scroll = ctk.CTkScrollableFrame(list_container, fg_color="#0F172A", corner_radius=8)
        self.scroll.pack(fill="both", expand=True)

        self._render_key_list()

        # -------------------------------------------------------------
        # 4. RODAPÉ
        # -------------------------------------------------------------
        footer = ctk.CTkFrame(self, fg_color="#0F172A", height=50)
        footer.pack(fill="x", side="bottom")

        btn_cancel = ctk.CTkButton(
            footer, text="Fechar", width=100, height=32,
            fg_color="#475569", hover_color="#64748B",
            command=self.destroy
        )
        btn_cancel.pack(side="right", padx=16, pady=10)

        btn_save = ctk.CTkButton(
            footer, text="💾 Salvar Alterações", width=160, height=32,
            fg_color="#10B981", hover_color="#059669", font=ctk.CTkFont(weight="bold"),
            command=self._save_and_close
        )
        btn_save.pack(side="right", padx=6, pady=10)

    # -------------------------------------------------------------
    # RENDERIZAÇÃO DA LISTA DE TECLAS
    # -------------------------------------------------------------
    def _render_key_list(self):
        # Limpa widgets existentes
        for w in self.scroll.winfo_children():
            w.destroy()

        self.key_widgets.clear()

        for note in KEYBOARD_NOTES:
            semitone = note % 12
            is_black = semitone in (1, 3, 6, 8, 10)
            note_name = midi_note_to_name(note)

            card_bg = "#111C2E" if not is_black else "#1A2234"
            card = ctk.CTkFrame(self.scroll, fg_color=card_bg, corner_radius=6, height=40)
            card.pack(fill="x", padx=4, pady=2)

            # Checkbox
            var = self.key_check_vars.get(note)
            if var is None:
                var = ctk.BooleanVar(value=False)
                self.key_check_vars[note] = var

            chk = ctk.CTkCheckBox(
                card, text="", variable=var, width=20,
                command=self._update_selected_count
            )
            chk.pack(side="left", padx=(8, 4), pady=6)

            # Ícone e Nome da Tecla
            key_icon = "🎹" if not is_black else "⬛"
            key_text = f"{key_icon} {note_name:<4} (Nota {note:02d})"
            lbl_key = ctk.CTkLabel(
                card, text=key_text, font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#F8FAFC" if not is_black else "#94A3B8", width=120, anchor="w"
            )
            lbl_key.pack(side="left", padx=4)

            # Badge do Som Atual
            rule = self.key_map.get(str(note))
            badge_text, badge_color = self._format_rule_badge(rule)

            lbl_badge = ctk.CTkLabel(
                card, text=badge_text, font=ctk.CTkFont(size=11),
                text_color=badge_color, anchor="w"
            )
            lbl_badge.pack(side="left", fill="x", expand=True, padx=8)

            # Botão Testar / Ouvir Som
            btn_test = ctk.CTkButton(
                card, text="🔊 Ouvir", width=75, height=26,
                fg_color="#059669", hover_color="#047857", font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda n=note: self._test_key_sound(n)
            )
            btn_test.pack(side="left", padx=4, pady=4)

            # Botão Escolher Arquivo Individual
            btn_edit_sample = ctk.CTkButton(
                card, text="📁 Som .WAV", width=95, height=26,
                fg_color="#3B82F6", hover_color="#2563EB", font=ctk.CTkFont(size=11),
                command=lambda n=note: self._pick_sample_for_single_key(n)
            )
            btn_edit_sample.pack(side="left", padx=4, pady=4)

            # Botão Limpar
            btn_clear = ctk.CTkButton(
                card, text="🗑️", width=34, height=26,
                fg_color="#475569", hover_color="#DC2626",
                command=lambda n=note: self._clear_single_key(n)
            )
            btn_clear.pack(side="left", padx=(2, 8), pady=4)

            self.key_widgets[note] = {
                "card": card,
                "badge": lbl_badge
            }

        self._update_selected_count()

    def _format_rule_badge(self, rule: dict | None) -> tuple[str, str]:
        if not rule:
            return ("⚪ Som Padrão (Instrumento Global)", "#94A3B8")

        rule_type = rule.get("type")
        if rule_type == "sample":
            path = rule.get("path", "")
            fname = os.path.basename(path) if path else "Arquivo desconhecido"
            return (f"📁 Áudio Customizado: {fname}", "#34D399")
        elif rule_type == "instrument":
            inst_id = rule.get("id", 0)
            name = "Instrumento"
            for num, n, cat in GM_INSTRUMENTS:
                if num == inst_id:
                    name = n
                    break
            return (f"🎺 Timbre GM: {inst_id:03d} - {name}", "#38BDF8")
        elif rule_type == "drum":
            drum_note = rule.get("drum_note", 36)
            name = "Bateria"
            for n, dname in GM_DRUM_SOUNDS:
                if n == drum_note:
                    name = dname
                    break
            return (f"🥁 Percussão: {name} (Nota {drum_note})", "#FACC15")

        return ("⚪ Som Padrão", "#94A3B8")

    def _update_key_badge(self, note: int):
        if note in self.key_widgets:
            rule = self.key_map.get(str(note))
            text, color = self._format_rule_badge(rule)
            self.key_widgets[note]["badge"].configure(text=text, text_color=color)

    # -------------------------------------------------------------
    # SELEÇÃO EM LOTE
    # -------------------------------------------------------------
    def _select_all_keys(self):
        for var in self.key_check_vars.values():
            var.set(True)
        self._update_selected_count()

    def _deselect_all_keys(self):
        for var in self.key_check_vars.values():
            var.set(False)
        self._update_selected_count()

    def _select_white_keys(self):
        for note in KEYBOARD_NOTES:
            semitone = note % 12
            is_black = semitone in (1, 3, 6, 8, 10)
            self.key_check_vars[note].set(not is_black)
        self._update_selected_count()

    def _select_black_keys(self):
        for note in KEYBOARD_NOTES:
            semitone = note % 12
            is_black = semitone in (1, 3, 6, 8, 10)
            self.key_check_vars[note].set(is_black)
        self._update_selected_count()

    def _select_octave_1(self):
        # C3 (48) até B3 (59)
        for note in KEYBOARD_NOTES:
            self.key_check_vars[note].set(48 <= note <= 59)
        self._update_selected_count()

    def _select_octave_2(self):
        # C4 (60) até C5 (72)
        for note in KEYBOARD_NOTES:
            self.key_check_vars[note].set(60 <= note <= 72)
        self._update_selected_count()

    def _get_selected_notes(self) -> list[int]:
        return [note for note in KEYBOARD_NOTES if self.key_check_vars.get(note, ctk.BooleanVar(value=False)).get()]

    def _update_selected_count(self):
        count = len(self._get_selected_notes())
        self.selected_count_lbl.configure(text=f"{count} teclas selecionadas")

    # -------------------------------------------------------------
    # AÇÕES EM LOTE
    # -------------------------------------------------------------
    def _apply_instrument_to_selected(self):
        selected = self._get_selected_notes()
        if not selected:
            return

        choice = self.batch_inst_combo.get()
        inst_id = int(choice.split(" - ")[0])

        for note in selected:
            self.key_map[str(note)] = {
                "type": "instrument",
                "id": inst_id
            }
            self.audio.set_key_rule(note, self.key_map[str(note)])
            self._update_key_badge(note)

        # Testa na primeira nota para dar feedback sonoro
        self._test_key_sound(selected[0])

    def _apply_drum_to_selected(self):
        selected = self._get_selected_notes()
        if not selected:
            return

        choice = self.batch_drum_combo.get()
        drum_note = int(choice.split(" - ")[0])

        for note in selected:
            self.key_map[str(note)] = {
                "type": "drum",
                "drum_note": drum_note
            }
            self.audio.set_key_rule(note, self.key_map[str(note)])
            self._update_key_badge(note)

        self._test_key_sound(selected[0])

    def _batch_import_single_file(self):
        selected = self._get_selected_notes()
        if not selected:
            return

        file_path = filedialog.askopenfilename(
            title="Escolha um arquivo de áudio para aplicar a todas as teclas selecionadas",
            filetypes=[
                ("Arquivos de Áudio (*.wav;*.mp3;*.ogg)", "*.wav;*.mp3;*.ogg"),
                ("Todos os Arquivos (*.*)", "*.*")
            ]
        )
        if not file_path or not os.path.exists(file_path):
            return

        for note in selected:
            rule = {"type": "sample", "path": file_path}
            self.key_map[str(note)] = rule
            self.audio.set_key_rule(note, rule)
            self._update_key_badge(note)

        self._test_key_sound(selected[0])

    def _batch_import_folder(self):
        """
        MÁGICA: O usuário escolhe uma pasta com vários arquivos de áudio.
        O sistema distribui os arquivos automaticamente pelas teclas selecionadas em ordem!
        """
        selected = self._get_selected_notes()
        if not selected:
            # Se nenhuma selecionada, seleciona todas
            self._select_all_keys()
            selected = self._get_selected_notes()

        folder_path = filedialog.askdirectory(
            title="Selecione uma pasta com arquivos .WAV ou .MP3 para distribuir nas teclas"
        )
        if not folder_path or not os.path.exists(folder_path):
            return

        # Lista arquivos de áudio em ordem alfabética
        valid_exts = (".wav", ".mp3", ".ogg")
        files = [
            os.path.join(folder_path, f) for f in sorted(os.listdir(folder_path))
            if f.lower().endswith(valid_exts)
        ]

        if not files:
            return

        # Atribui sequencialmente
        for idx, note in enumerate(selected):
            if idx < len(files):
                file_path = files[idx]
                rule = {"type": "sample", "path": file_path}
                self.key_map[str(note)] = rule
                self.audio.set_key_rule(note, rule)
                self._update_key_badge(note)

        # Testa o primeiro arquivo
        self._test_key_sound(selected[0])

    def _clear_selected_keys(self):
        selected = self._get_selected_notes()
        for note in selected:
            key_str = str(note)
            if key_str in self.key_map:
                del self.key_map[key_str]
            self.audio.remove_key_rule(note)
            self._update_key_badge(note)

    # -------------------------------------------------------------
    # AÇÕES INDIVIDUAIS
    # -------------------------------------------------------------
    def _pick_sample_for_single_key(self, note: int):
        file_path = filedialog.askopenfilename(
            title=f"Escolha um arquivo de áudio para a tecla {midi_note_to_name(note)} (Nota {note})",
            filetypes=[
                ("Arquivos de Áudio (*.wav;*.mp3;*.ogg)", "*.wav;*.mp3;*.ogg"),
                ("Todos os Arquivos (*.*)", "*.*")
            ]
        )
        if file_path and os.path.exists(file_path):
            rule = {"type": "sample", "path": file_path}
            self.key_map[str(note)] = rule
            self.audio.set_key_rule(note, rule)
            self._update_key_badge(note)
            self._test_key_sound(note)

    def _clear_single_key(self, note: int):
        key_str = str(note)
        if key_str in self.key_map:
            del self.key_map[key_str]
        self.audio.remove_key_rule(note)
        self._update_key_badge(note)

    def _test_key_sound(self, note: int):
        """Toca o som exato configurado para aquela tecla."""
        self.audio.play_note(note, velocity=120, channel=0)
        self.after(350, lambda: self.audio.stop_note(note, channel=0))

    def _save_and_close(self):
        """Salva as configurações de mapeamento de teclas e fecha."""
        if self.on_save_callback:
            self.on_save_callback(self.key_map)
        self.destroy()
