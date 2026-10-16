"""
Janela e Gerenciador de Letras e Sincronização Vocal para o Estúdio Criador.
Permite colar letras da internet, carregar arquivos .txt ou .lrc (com timestamps),
dividir automaticamente em sílabas padrão Rock Band Network e sincronizar com a música.
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from typing import Callable, Optional

from src.creator.chart_model import ChartSong
from src.creator.lyric_processor import align_lyrics_to_song, parse_lrc_content, syllabify_text_lines
from src.ui.tooltip import set_tooltip

class LyricsManagerDialog(ctk.CTkToplevel):
    def __init__(self, master, song: ChartSong, on_applied_callback: Optional[Callable] = None):
        super().__init__(master)
        self.song = song
        self.on_applied = on_applied_callback

        self.title("🎤 Sincronizador de Letra & Vocais (Rock Band 3 / Clone Hero)")
        self.geometry("680x620")
        self.minsize(580, 520)
        self.resizable(True, True)

        self.transient(master)
        self.after(100, self.lift)
        self.after(150, self.focus_force)

        self._build_ui()

    def _build_ui(self):
        # 1. Header Superior
        header = ctk.CTkFrame(self, fg_color="#0F172A", height=65, corner_radius=0)
        header.pack(fill="x")

        ctk.CTkLabel(
            header,
            text="🎤 Sincronizador de Letras & Faixa Vocal",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#EC4899"
        ).pack(anchor="w", padx=16, pady=(10, 2))

        ctk.CTkLabel(
            header,
            text="Cole a letra da música ou carregue um arquivo .txt / .lrc. O sistema dividirá as palavras em sílabas e alinhará com o ritmo!",
            font=ctk.CTkFont(size=11),
            text_color="#94A3B8"
        ).pack(anchor="w", padx=16, pady=(0, 8))

        main_box = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=8)
        main_box.pack(fill="both", expand=True, padx=12, pady=10)

        # Barra de Ações Rápidas de Arquivo
        file_bar = ctk.CTkFrame(main_box, fg_color="transparent")
        file_bar.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(file_bar, text="Letra da Canção (Texto ou LRC com minutagem):", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left")

        btn_load = ctk.CTkButton(
            file_bar, text="📁 Carregar Arquivo (.txt / .lrc)...", width=190, height=28,
            fg_color="#0284C7", hover_color="#0369A1", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_load_file
        )
        btn_load.pack(side="right", padx=2)
        set_tooltip(btn_load, "Carrega um arquivo de texto comum (.txt) ou arquivo de letra com tempos (.lrc)")

        btn_clear = ctk.CTkButton(
            file_bar, text="🗑️ Limpar", width=80, height=28,
            fg_color="#475569", hover_color="#334155", font=ctk.CTkFont(size=11),
            command=self._on_clear
        )
        btn_clear.pack(side="right", padx=4)

        # Caixa de Texto da Letra
        self.txt_lyrics = ctk.CTkTextbox(main_box, font=ctk.CTkFont(family="Consolas", size=12), corner_radius=6)
        self.txt_lyrics.pack(fill="both", expand=True, padx=12, pady=6)

        # Se já houver letra na música, preenche
        if self.song.lyrics_raw:
            self.txt_lyrics.insert("1.0", self.song.lyrics_raw)
        elif self.song.vocal_notes:
            # Reconstrói a letra a partir das notas vocais existentes
            extracted = []
            cur_line = []
            for vn in self.song.vocal_notes:
                cur_line.append(vn.lyric)
                if vn.is_phrase_end:
                    extracted.append(" ".join(cur_line))
                    cur_line = []
            if cur_line:
                extracted.append(" ".join(cur_line))
            self.txt_lyrics.insert("1.0", "\n".join(extracted))

        # Barra de Configuração de Sincronia
        sync_cfg = ctk.CTkFrame(main_box, fg_color="#0F172A", corner_radius=6)
        sync_cfg.pack(fill="x", padx=12, pady=6)

        sc_row = ctk.CTkFrame(sync_cfg, fg_color="transparent")
        sc_row.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(sc_row, text="Atraso Inicial (Intro Instrumental):", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(0, 4))
        self.delay_entry = ctk.CTkEntry(sc_row, width=80)
        self.delay_entry.insert(0, "4000")
        self.delay_entry.pack(side="left", padx=4)
        ctk.CTkLabel(sc_row, text="ms", font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 10))
        set_tooltip(self.delay_entry, "Tempo em milissegundos antes da primeira frase começar (ignorado se o arquivo for .LRC)")

        self.status_lbl = ctk.CTkLabel(
            sc_row,
            text=f"Notas vocais mapeadas: {len(self.song.vocal_notes)}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#38BDF8"
        )
        self.status_lbl.pack(side="right", padx=6)

        # Botão Principal de Sincronização
        btn_apply = ctk.CTkButton(
            self, text="✨ SINCRONIZAR E APLICAR LETRA AOS VOCAIS!", height=40,
            fg_color="#EC4899", hover_color="#DB2777", font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_apply_lyrics
        )
        btn_apply.pack(fill="x", padx=14, pady=(4, 12))
        set_tooltip(btn_apply, "Divide o texto em sílabas fonéticas oficiais e sincroniza com a linha do tempo do Rock Band 3 e Clone Hero!")

    def _on_load_file(self):
        f = filedialog.askopenfilename(
            title="Selecione o arquivo de letra",
            filetypes=[("Arquivos de Letra", "*.txt *.lrc"), ("Todos os Arquivos", "*.*")]
        )
        if f:
            try:
                with open(f, "r", encoding="utf-8-sig", errors="ignore") as fp:
                    content = fp.read()
                self.txt_lyrics.delete("1.0", "end")
                self.txt_lyrics.insert("1.0", content)
                self.song.lyrics_raw = content
                self.status_lbl.configure(text=f"Arquivo carregado: {os.path.basename(f)}", text_color="#10B981")
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível ler o arquivo: {e}")

    def _on_clear(self):
        self.txt_lyrics.delete("1.0", "end")
        self.status_lbl.configure(text="Texto limpo.", text_color="#94A3B8")

    def _on_apply_lyrics(self):
        content = self.txt_lyrics.get("1.0", "end").strip()
        if not content:
            messagebox.showwarning("Aviso", "Digite ou cole a letra da música antes de sincronizar!")
            return

        try:
            delay_ms = int(self.delay_entry.get().strip())
        except Exception:
            delay_ms = 4000

        # Executa alinhador
        total_syls = align_lyrics_to_song(self.song, content, start_delay_ms=delay_ms)

        self.status_lbl.configure(
            text=f"🎉 {total_syls} sílabas sincronizadas!",
            text_color="#10B981"
        )

        if self.on_applied:
            self.on_applied()

        messagebox.showinfo(
            "Letra Sincronizada com Sucesso!",
            f"🎉 {total_syls} sílabas divididas e sincronizadas com sucesso!\n\n"
            f"• Divisão silábica oficial Rock Band aplicada (com hífens terminadores).\n"
            f"• Frases vocais (Nota 105) e Overdrives (Nota 106) demarcados.\n"
            f"• Você pode visualizar as sílabas escritas na trilha '🎤 Vocais' da linha do tempo!"
        )
        self.destroy()
