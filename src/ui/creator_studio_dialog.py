"""
Estúdio Criador e Conversor de Músicas para Rock Band 3, Guitar Hero e Clone Hero.
Substitui 100% o fluxo fragmentado de REAPER, Magma v2, C3 CON Tools e Onyx:
- Conversor em 1 clique de músicas do Chorus Encore e RhythmVerse
- Editor Visual de Linha do Tempo (Mini-REAPER) com colocação manual de notas
- Gravação ao vivo tocando na guitarra/baixo/bateria real
- Upload de capa do álbum com preview em tempo real (ICON0.PNG e album.png)
- Gerador de pacotes completos para PS3 / RPCS3 (PARAM.SFO + ICON0 + BAT auto)
- Guia passo a passo completo e ilustrado para leigos
"""

import os
import time
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import pygame
from PIL import Image

from src.creator.chart_model import ChartSong, NoteEvent
from src.creator.chart_importer import import_song_from_folder
from src.creator.clonehero_exporter import export_clone_hero_song
from src.creator.rb3_dta_exporter import export_rb3_song_package
from src.creator.ps3_pkg_exporter import export_ps3_pkg_structure
from src.creator.auto_charter import auto_generate_chart
from src.creator.pack_compiler import scan_folder_for_songs, compile_ps3_song_pack, compile_clone_hero_pack
from src.ui.mini_reaper_canvas import MiniReaperCanvas
from src.ui.tooltip import set_tooltip
from src.ui.key_strum_config_dialog import KeyStrumConfigDialog, DEFAULT_KEYS, KEY_NAMES_FRIENDLY
from src.ui.lyrics_manager_dialog import LyricsManagerDialog
from src.utils.config_manager import save_config

class CreatorStudioDialog(ctk.CTkToplevel):
    def __init__(self, master, audio_engine=None):
        super().__init__(master)

        self.title("🎵 MidGuitar Universal Studio - Criador e Conversor (RB3 / PS3 / Clone Hero)")
        self.geometry("1040x720")
        self.minsize(920, 600)
        self.resizable(True, True)

        self.audio = audio_engine
        self.song = ChartSong()
        self.is_recording = False
        self.is_playing = False
        self.playback_start_time = 0.0
        self.tap_times = []
        self.preview_image_ctk = None
        self.batch_songs = []
        self.batch_art_path = None

        # Configuração de Teclas do Teclado e Modo de Palheta
        self.key_controls = dict(DEFAULT_KEYS)
        if hasattr(self.master, "config") and "creator_keyboard_map" in self.master.config:
            self.key_controls.update(self.master.config["creator_keyboard_map"])

        self.held_frets = set()
        self.vocal_pitch_counter = 0

        # Bindings do Teclado para Tocar e Palhetar
        self.bind("<KeyPress>", self._on_window_key_press)
        self.bind("<KeyRelease>", self._on_window_key_release)

        # Modal focus
        self.transient(master)
        self.after(100, self.lift)
        self.after(150, self.focus_force)

        self._build_ui()
        self._update_target_game_desc("🎸 Rock Band 3 (Emulador RPCS3 no PC)")
        self._start_playback_poll()

    def _build_ui(self):
        # 1. Header Superior
        header = ctk.CTkFrame(self, fg_color="#0F172A", height=65, corner_radius=0)
        header.pack(fill="x", side="top")

        h_title = ctk.CTkLabel(
            header,
            text="🎵 MidGuitar Universal Studio (Rock Band 3, PS3 PKG & Clone Hero)",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color="#38BDF8"
        )
        h_title.pack(anchor="w", padx=18, pady=(8, 2))

        h_desc = ctk.CTkLabel(
            header,
            text="Crie notas à mão no Editor Visual, grave ao vivo tocando seu instrumento, junte várias músicas em Mega Pacotes e exporte para PS3/RPCS3 sem Magma ou Onyx!",
            font=ctk.CTkFont(size=11),
            text_color="#94A3B8"
        )
        h_desc.pack(anchor="w", padx=18, pady=(0, 8))

        # 2. Abas do Estúdio
        self.tabview = ctk.CTkTabview(
            self,
            fg_color="#1E293B",
            segmented_button_fg_color="#0F172A",
            segmented_button_selected_color="#0284C7",
            segmented_button_selected_hover_color="#0369A1"
        )
        self.tabview.pack(fill="both", expand=True, padx=12, pady=6)

        tab_converter = self.tabview.add("⚡ Conversor 1 Clique (Individual)")
        tab_batch = self.tabview.add("📦 Compilador de Pacotes (Multi-Músicas PS3/CH)")
        tab_timeline = self.tabview.add("🎛️ Editor Visual de Notas (Mini-REAPER)")
        tab_metadata = self.tabview.add("🖼️ Metadados, Capa & Exportação")
        tab_guide = self.tabview.add("📖 Guia Passo a Passo (Para Leigos)")

        self._build_converter_tab(tab_converter)
        self._build_batch_tab(tab_batch)
        self._build_timeline_tab(tab_timeline)
        self._build_metadata_tab(tab_metadata)
        self._build_guide_tab(tab_guide)

    # -------------------------------------------------------------------------
    # ABA 1: CONVERSOR EM 1 CLIQUE
    # -------------------------------------------------------------------------
    def _build_converter_tab(self, tab):
        top_box = ctk.CTkFrame(tab, fg_color="#0F172A", corner_radius=8)
        top_box.pack(fill="x", padx=10, pady=8)

        lbl = ctk.CTkLabel(
            top_box,
            text="📁 Selecione a pasta de qualquer música baixada (Chorus Encore, RhythmVerse, Google Drive ou Clone Hero):",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#E2E8F0"
        )
        lbl.pack(anchor="w", padx=12, pady=(10, 4))

        sel_row = ctk.CTkFrame(top_box, fg_color="transparent")
        sel_row.pack(fill="x", padx=12, pady=(2, 10))

        self.folder_entry = ctk.CTkEntry(
            sel_row,
            placeholder_text="Clique em 'Buscar Pasta...' e escolha a pasta da música..."
        )
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        set_tooltip(self.folder_entry, "Caminho da pasta que contém o arquivo de áudio e as notas (notes.mid / song.ini)")

        btn_browse = ctk.CTkButton(
            sel_row, text="Buscar Pasta...", width=130, height=30,
            command=self._on_browse_import_folder
        )
        btn_browse.pack(side="right")
        set_tooltip(btn_browse, "Abre a janela para selecionar a pasta da música no seu computador")

        # Detalhes da música importada
        self.info_box = ctk.CTkFrame(tab, fg_color="#0F172A", corner_radius=8)
        self.info_box.pack(fill="both", expand=True, padx=10, pady=4)

        self.info_label = ctk.CTkLabel(
            self.info_box,
            text="Nenhuma música carregada no momento.\n\nClique no botão 'Buscar Pasta...' acima para carregar qualquer música de Clone Hero/Chorus\ne convertê-la imediatamente para Rock Band 3 e PS3 PKG!",
            font=ctk.CTkFont(size=12),
            text_color="#94A3B8",
            justify="center"
        )
        self.info_label.pack(expand=True, pady=20)

        # Seletor de Jogo de Destino
        target_box = ctk.CTkFrame(tab, fg_color="#0F172A", corner_radius=8)
        target_box.pack(fill="x", padx=10, pady=(6, 8))

        sel_game_row = ctk.CTkFrame(target_box, fg_color="transparent")
        sel_game_row.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(
            sel_game_row,
            text="🎯 Escolha o Jogo de Destino:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#38BDF8"
        ).pack(side="left", padx=(0, 8))

        self.target_game_combo = ctk.CTkComboBox(
            sel_game_row, width=320, height=32,
            values=[
                "🎸 Rock Band 3 (Emulador RPCS3 no PC)",
                "🎮 Clone Hero / YARG (PC)",
                "📦 PlayStation 3 Console (CFW / HEN / PKG)",
                "🟢 Xbox 360 (Rock Band 3 / 2 - RGH / CON)"
            ],
            command=self._on_target_game_changed
        )
        self.target_game_combo.set("🎸 Rock Band 3 (Emulador RPCS3 no PC)")
        self.target_game_combo.pack(side="left", padx=4)
        set_tooltip(self.target_game_combo, "Selecione para qual jogo ou videogame você deseja exportar")

        self.btn_export_selected = ctk.CTkButton(
            sel_game_row, text="⚡ EXPORTAR AGORA", width=220, height=34,
            fg_color="#10B981", hover_color="#059669", font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: self._on_export_to_selected_game(sync_metadata=False)
        )
        self.btn_export_selected.pack(side="right", padx=4)
        set_tooltip(self.btn_export_selected, "Exporta automaticamente os arquivos no formato do jogo selecionado")

        # Descrição dinâmica do formato do jogo
        self.target_desc_label = ctk.CTkLabel(
            target_box,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#94A3B8",
            justify="left"
        )
        self.target_desc_label.pack(anchor="w", padx=14, pady=(2, 10))

        # Atalhos rápidos diretos
        quick_row = ctk.CTkFrame(tab, fg_color="transparent")
        quick_row.pack(fill="x", padx=10, pady=(0, 4))

        ctk.CTkLabel(quick_row, text="Atalhos Rápidos:", font=ctk.CTkFont(size=10, weight="bold"), text_color="#64748B").pack(side="left", padx=(4, 8))

        btn_convert_rb3 = ctk.CTkButton(
            quick_row, text="🚀 RB3 (RPCS3 / Console)", width=170, height=28,
            fg_color="#334155", hover_color="#475569", font=ctk.CTkFont(size=10),
            command=self._on_convert_to_rb3
        )
        btn_convert_rb3.pack(side="left", padx=3)
        set_tooltip(btn_convert_rb3, "Gera pasta com songs.dta e arquivo MIDI compatível com Rock Band 3")

        btn_convert_ps3 = ctk.CTkButton(
            quick_row, text="📦 Pacote PS3 (PKG/SFO)", width=170, height=28,
            fg_color="#334155", hover_color="#475569", font=ctk.CTkFont(size=10),
            command=self._on_export_ps3_pkg
        )
        btn_convert_ps3.pack(side="left", padx=3)
        set_tooltip(btn_convert_ps3, "Gera pacote completo com PARAM.SFO, ICON0.PNG e instalador automático do RPCS3")

        btn_convert_ch = ctk.CTkButton(
            quick_row, text="🎮 Clone Hero / YARG", width=160, height=28,
            fg_color="#334155", hover_color="#475569", font=ctk.CTkFont(size=10),
            command=self._on_convert_to_clone_hero
        )
        btn_convert_ch.pack(side="left", padx=3)
        set_tooltip(btn_convert_ch, "Gera pasta pronta com song.ini, notes.mid e album.png para o Clone Hero")

    def _on_browse_import_folder(self):
        folder = filedialog.askdirectory(title="Selecione a pasta da música do Clone Hero / Rock Band")
        if not folder:
            return
        self.folder_entry.delete(0, "end")
        self.folder_entry.insert(0, folder)

        self.song = import_song_from_folder(folder)
        g_count = len(self.song.guitar_notes)
        b_count = len(self.song.bass_notes)
        d_count = len(self.song.drum_notes)
        k_count = len(self.song.keys_notes)
        v_count = len(self.song.vocal_notes)

        # Atualiza tela do timeline e formulários
        self.timeline.song = self.song
        self.timeline.redraw()
        self._sync_song_to_fields()

        stems_info = f" ({len(self.song.audio_stems)} faixas isoladas/stems)" if len(self.song.audio_stems) > 1 else ""
        info_text = (
            f"🎵 Título: {self.song.title}\n"
            f"👤 Artista: {self.song.artist}  |  Álbum: {self.song.album} ({self.song.year})\n"
            f"⚡ BPM: {self.song.bpm}  |  Gênero: {self.song.genre}  |  Charter: {self.song.charter}\n"
            f"🔊 Áudio detectado: {'Sim (' + os.path.basename(self.song.audio_path) + ')' + stems_info if self.song.audio_path else 'Não encontrado'}\n"
            f"🖼️ Imagem da Capa: {'Encontrada' if self.song.album_art_path else 'Não informada'}\n"
            f"--------------------------------------------------\n"
            f"🎸 Guitarra: {g_count} notas mapeadas\n"
            f"🎸 Baixo: {b_count} notas mapeadas\n"
            f"🥁 Bateria: {d_count} notas mapeadas\n"
            f"🎹 Teclado: {k_count} notas mapeadas\n"
            f"🎤 Vocais & Letra: {v_count} notas/sílabas mapeadas\n"
            f"✨ Seções/Eventos: {len(self.song.events)} marcadores\n"
        )
        self.info_label.configure(text=info_text, justify="left", font=ctk.CTkFont(family="Consolas", size=12), text_color="#F8FAFC")
        if self.song.album_art_path:
            self._load_art_preview(self.song.album_art_path)

    # -------------------------------------------------------------------------
    # ABA 2: COMPILADOR DE PACOTES EM LOTE (MEGA PACKS PS3 / CH)
    # -------------------------------------------------------------------------
    def _build_batch_tab(self, tab):
        top_box = ctk.CTkFrame(tab, fg_color="#0F172A", corner_radius=8)
        top_box.pack(fill="x", padx=10, pady=(6, 4))

        ctk.CTkLabel(
            top_box,
            text="📦 Compilador de Mega Pacotes (Junte 10, 50 ou 100 músicas em um único pacote consolidado):",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#38BDF8"
        ).pack(anchor="w", padx=12, pady=(8, 2))

        ctk.CTkLabel(
            top_box,
            text="Selecione uma pasta com várias músicas (do Chorus Encore, C3 ou criadas aqui) para compilar tudo em um único songs.dta unificado!",
            font=ctk.CTkFont(size=11),
            text_color="#94A3B8"
        ).pack(anchor="w", padx=12, pady=(0, 6))

        btn_row = ctk.CTkFrame(top_box, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(2, 8))

        btn_scan = ctk.CTkButton(
            btn_row, text="📁 Escanear Pasta com Músicas...", width=230, height=32,
            fg_color="#0284C7", hover_color="#0369A1", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_browse_batch_folder
        )
        btn_scan.pack(side="left", padx=(0, 6))
        set_tooltip(btn_scan, "Procura automaticamente todas as músicas dentro da pasta escolhida")

        btn_add_current = ctk.CTkButton(
            btn_row, text="➕ Incluir Música Atual do Editor", width=220, height=32,
            fg_color="#334155", hover_color="#475569", font=ctk.CTkFont(size=11),
            command=self._on_add_current_song_to_batch
        )
        btn_add_current.pack(side="left", padx=4)
        set_tooltip(btn_add_current, "Adiciona a música que você acabou de criar no editor para este pacote")

        btn_clear_batch = ctk.CTkButton(
            btn_row, text="🗑️ Limpar Lista", width=120, height=32,
            fg_color="#475569", hover_color="#334155", font=ctk.CTkFont(size=11),
            command=self._on_clear_batch_songs
        )
        btn_clear_batch.pack(side="right", padx=2)

        # Lista de Músicas
        list_frame = ctk.CTkFrame(tab, fg_color="#0F172A", corner_radius=8)
        list_frame.pack(fill="both", expand=True, padx=10, pady=4)

        header_list = ctk.CTkFrame(list_frame, fg_color="transparent")
        header_list.pack(fill="x", padx=12, pady=(8, 2))

        self.batch_count_lbl = ctk.CTkLabel(
            header_list,
            text="Músicas selecionadas para o pacote: 0",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#F8FAFC"
        )
        self.batch_count_lbl.pack(side="left")

        self.batch_scroll = ctk.CTkScrollableFrame(list_frame, fg_color="#1E293B", corner_radius=6)
        self.batch_scroll.pack(fill="both", expand=True, padx=10, pady=(4, 8))

        self.batch_empty_lbl = ctk.CTkLabel(
            self.batch_scroll,
            text="Nenhuma música na lista ainda.\nClique em 'Escanear Pasta com Músicas...' acima ou adicione a música atual!",
            font=ctk.CTkFont(size=11),
            text_color="#64748B"
        )
        self.batch_empty_lbl.pack(pady=30)

        # Opções de Compilação
        compile_box = ctk.CTkFrame(tab, fg_color="#0F172A", corner_radius=8)
        compile_box.pack(fill="x", padx=10, pady=(4, 8))

        c_row1 = ctk.CTkFrame(compile_box, fg_color="transparent")
        c_row1.pack(fill="x", padx=12, pady=(8, 4))

        ctk.CTkLabel(c_row1, text="Nome do Pacote:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(0, 6))
        self.batch_name_entry = ctk.CTkEntry(c_row1, width=280)
        self.batch_name_entry.insert(0, "Mega Pack Rock Band 3")
        self.batch_name_entry.pack(side="left", padx=4)

        ctk.CTkLabel(c_row1, text="Destino:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(10, 6))
        self.batch_target_combo = ctk.CTkComboBox(
            c_row1, width=280,
            values=[
                "🎸 Rock Band 3 (RPCS3 - dev_hdd0 USRDIR)",
                "📦 PlayStation 3 Console (Mega Pacote PKG)",
                "🎮 Clone Hero (Pasta Coletiva Songs)"
            ]
        )
        self.batch_target_combo.set("🎸 Rock Band 3 (RPCS3 - dev_hdd0 USRDIR)")
        self.batch_target_combo.pack(side="left", padx=4)

        btn_art = ctk.CTkButton(
            c_row1, text="🖼️ Capa do Pacote...", width=140, fg_color="#334155",
            command=self._on_browse_batch_art
        )
        btn_art.pack(side="right", padx=2)

        c_row2 = ctk.CTkFrame(compile_box, fg_color="transparent")
        c_row2.pack(fill="x", padx=12, pady=(4, 8))

        btn_compile = ctk.CTkButton(
            c_row2, text="📦 COMPILAR E GERAR MEGA PACOTE AGORA!", width=360, height=36,
            fg_color="#10B981", hover_color="#059669", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_compile_batch_pack
        )
        btn_compile.pack(side="left", padx=2)
        set_tooltip(btn_compile, "Une todas as músicas em um único songs.dta consolidado e gera o instalador automático!")

        self.batch_art_lbl = ctk.CTkLabel(c_row2, text="Capa: Ícone estilizado padrão", font=ctk.CTkFont(size=10), text_color="#64748B")
        self.batch_art_lbl.pack(side="right", padx=6)

    def _on_browse_batch_folder(self):
        f = filedialog.askdirectory(title="Selecione a pasta onde estão as músicas")
        if not f:
            return
        found = scan_folder_for_songs(f)
        if not found:
            messagebox.showwarning("Aviso", "Nenhuma pasta de música válida (com song.ini ou .mid) foi encontrada.")
            return

        added_count = 0
        for _, song in found:
            self.batch_songs.append(song)
            added_count += 1
        self._refresh_batch_list_ui()
        messagebox.showinfo("Sucesso!", f"{added_count} músicas foram adicionadas ao compilador de pacotes!")

    def _on_add_current_song_to_batch(self):
        if not self.song.title or self.song.title == "Nova Música":
            messagebox.showwarning("Aviso", "A música atual ainda não tem título ou notas geradas.")
            return
        self.batch_songs.append(self.song)
        self._refresh_batch_list_ui()

    def _on_clear_batch_songs(self):
        self.batch_songs.clear()
        self._refresh_batch_list_ui()

    def _on_browse_batch_art(self):
        f = filedialog.askopenfilename(title="Capa do Pacote", filetypes=[("Imagens", "*.png *.jpg *.jpeg")])
        if f:
            self.batch_art_path = f
            self.batch_art_lbl.configure(text=f"Capa: {os.path.basename(f)}", text_color="#38BDF8")

    def _refresh_batch_list_ui(self):
        for widget in self.batch_scroll.winfo_children():
            widget.destroy()

        count = len(self.batch_songs)
        self.batch_count_lbl.configure(text=f"Músicas selecionadas para o pacote: {count}")

        if count == 0:
            lbl = ctk.CTkLabel(
                self.batch_scroll,
                text="Nenhuma música na lista ainda.\nClique em 'Escanear Pasta com Músicas...' acima para carregar dezenas de faixas!",
                font=ctk.CTkFont(size=11), text_color="#64748B"
            )
            lbl.pack(pady=30)
            return

        for idx, s in enumerate(self.batch_songs):
            item_frame = ctk.CTkFrame(self.batch_scroll, fg_color="#0F172A", corner_radius=6)
            item_frame.pack(fill="x", padx=6, pady=3)

            t_text = f"#{idx+1}  🎵 {s.title}  -  {s.artist} ({s.album})  |  BPM: {s.bpm}"
            ctk.CTkLabel(item_frame, text=t_text, font=ctk.CTkFont(size=11, weight="bold"), text_color="#F8FAFC").pack(side="left", padx=10, pady=6)

            badge_text = []
            if s.guitar_notes: badge_text.append("🎸")
            if s.bass_notes: badge_text.append("🎸B")
            if s.drum_notes: badge_text.append("🥁")
            if s.keys_notes: badge_text.append("🎹")
            if s.vocal_notes: badge_text.append("🎤")

            ctk.CTkLabel(item_frame, text=" ".join(badge_text), font=ctk.CTkFont(size=11), text_color="#38BDF8").pack(side="right", padx=10, pady=6)

    def _on_compile_batch_pack(self):
        if not self.batch_songs:
            messagebox.showwarning("Aviso", "Adicione ao menos uma música à lista antes de compilar!")
            return

        out_dir = filedialog.askdirectory(title="Escolha onde salvar o Mega Pacote")
        if not out_dir:
            return

        pack_name = self.batch_name_entry.get().strip() or "MegaPack_RB3"
        choice = self.batch_target_combo.get()

        if "Clone Hero" in choice:
            res_dir = compile_clone_hero_pack(self.batch_songs, pack_name, out_dir)
            messagebox.showinfo("Sucesso Clone Hero!", f"Mega Pacote Clone Hero gerado com sucesso em:\n{res_dir}\n\nCole na sua pasta Songs!")
        else:
            res_dir = compile_ps3_song_pack(self.batch_songs, pack_name, out_dir, self.batch_art_path)
            messagebox.showinfo(
                "Mega Pacote PS3 / RPCS3 Pronto!",
                f"🎉 Mega Pacote criado com sucesso contendo {len(self.batch_songs)} músicas!\n\n"
                f"Pasta gerada: {res_dir}\n\n"
                f"• Todas as músicas foram unificadas em um único songs.dta consolidado!\n"
                f"• Para instalar no RPCS3: Dê dois cliques em 'INSTALAR_PACOTE_NO_RPCS3.bat' dentro da pasta!"
            )

    # -------------------------------------------------------------------------
    # ABA 3: EDITOR VISUAL DE NOTAS (MINI-REAPER) & GRAVAÇÃO
    # -------------------------------------------------------------------------
    def _build_timeline_tab(self, tab):
        # Barra superior com seletores de Instrumento, Dificuldade, Zoom e Grid
        bar = ctk.CTkFrame(tab, fg_color="#0F172A", corner_radius=8)
        bar.pack(fill="x", padx=10, pady=(6, 4))

        # Instrumento
        ctk.CTkLabel(bar, text="Instrumento:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(10, 4), pady=6)
        self.track_combo = ctk.CTkComboBox(
            bar, width=175,
            values=["🎸 Guitarra (5 Casas)", "🎸 Baixo", "🥁 Bateria", "🎹 Teclado", "🎤 Vocais"],
            command=self._on_track_changed
        )
        self.track_combo.set("🎸 Guitarra (5 Casas)")
        self.track_combo.pack(side="left", padx=4, pady=6)
        set_tooltip(self.track_combo, "Escolha qual instrumento você quer editar ou gravar")

        # Dificuldade
        ctk.CTkLabel(bar, text="Dificuldade:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(10, 4), pady=6)
        self.diff_combo = ctk.CTkComboBox(
            bar, width=110,
            values=["Expert", "Hard", "Medium", "Easy"],
            command=self._on_diff_changed
        )
        self.diff_combo.set("Expert")
        self.diff_combo.pack(side="left", padx=4, pady=6)
        set_tooltip(self.diff_combo, "Selecione a dificuldade da trilha atual (Expert, Hard, Medium, Easy)")

        # Grid de Encaixe (Snap)
        ctk.CTkLabel(bar, text="Encaixe na Grade:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(10, 4), pady=6)
        self.snap_combo = ctk.CTkComboBox(
            bar, width=130,
            values=["1/4 (Padrão)", "1/8 (Rápido)", "1/16 (Solos)", "1/2 (Lento)"],
            command=self._on_snap_changed
        )
        self.snap_combo.set("1/4 (Padrão)")
        self.snap_combo.pack(side="left", padx=4, pady=6)
        set_tooltip(self.snap_combo, "Define o alinhamento rítmico automático das notas na batida da música")

        # Zoom
        btn_zoom_out = ctk.CTkButton(bar, text="🔍-", width=36, height=28, fg_color="#334155", command=lambda: self._adjust_zoom(-20))
        btn_zoom_out.pack(side="right", padx=6, pady=6)
        set_tooltip(btn_zoom_out, "Diminuir zoom (ver mais tempo na tela)")

        btn_zoom_in = ctk.CTkButton(bar, text="🔍+", width=36, height=28, fg_color="#334155", command=lambda: self._adjust_zoom(+20))
        btn_zoom_in.pack(side="right", padx=2, pady=6)
        set_tooltip(btn_zoom_in, "Aumentar zoom (ver notas em detalhes para solos rápidos)")

        # Barra Inteligente de Auto-Chart (Geração Automática de Notas)
        auto_bar = ctk.CTkFrame(tab, fg_color="#1E1B4B", corner_radius=8, border_width=1, border_color="#6366F1")
        auto_bar.pack(fill="x", padx=10, pady=(2, 4))

        ab_row = ctk.CTkFrame(auto_bar, fg_color="transparent")
        ab_row.pack(fill="x", padx=10, pady=4)

        ctk.CTkLabel(
            ab_row, text="✨ Auto-Chart Automático:",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="#A5B4FC"
        ).pack(side="left", padx=(0, 6))

        self.chk_gen_guitar = ctk.CTkCheckBox(ab_row, text="🎸 Guitarra", font=ctk.CTkFont(size=11), width=85)
        self.chk_gen_guitar.select()
        self.chk_gen_guitar.pack(side="left", padx=2)

        self.chk_gen_bass = ctk.CTkCheckBox(ab_row, text="🎸 Baixo", font=ctk.CTkFont(size=11), width=75)
        self.chk_gen_bass.select()
        self.chk_gen_bass.pack(side="left", padx=2)

        self.chk_gen_drums = ctk.CTkCheckBox(ab_row, text="🥁 Bateria", font=ctk.CTkFont(size=11), width=85)
        self.chk_gen_drums.select()
        self.chk_gen_drums.pack(side="left", padx=2)

        self.chk_gen_keys = ctk.CTkCheckBox(ab_row, text="🎹 Teclado", font=ctk.CTkFont(size=11), width=85)
        self.chk_gen_keys.select()
        self.chk_gen_keys.pack(side="left", padx=2)

        self.chk_gen_vocals = ctk.CTkCheckBox(ab_row, text="🎤 Vocais", font=ctk.CTkFont(size=11), width=85)
        self.chk_gen_vocals.select()
        self.chk_gen_vocals.pack(side="left", padx=2)

        self.intensity_combo = ctk.CTkComboBox(
            ab_row, width=130, height=28,
            values=["⚡ Rock Enérgico", "🔥 Metal / Solos", "🎵 Pop Suave"]
        )
        self.intensity_combo.set("⚡ Rock Enérgico")
        self.intensity_combo.pack(side="left", padx=4)

        btn_run_auto = ctk.CTkButton(
            ab_row, text="✨ GERAR NOTAS!", width=150, height=28,
            fg_color="#8B5CF6", hover_color="#7C3AED", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_auto_generate_clicked
        )
        btn_run_auto.pack(side="right", padx=2)
        set_tooltip(btn_run_auto, "Cria todas as notas musicais, acordes, solos e bateria sincronizados com o BPM em 1 clique!")

        btn_lyrics = ctk.CTkButton(
            ab_row, text="🎤 Letra da Música (.txt/.lrc)...", width=190, height=28,
            fg_color="#EC4899", hover_color="#DB2777", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._open_lyrics_dialog
        )
        btn_lyrics.pack(side="right", padx=3)
        set_tooltip(btn_lyrics, "Cole a letra da música ou carregue arquivo .txt/.lrc para dividir em sílabas e sincronizar com a voz!")

        # Barra Interativa de Toque & Teste (Teclado PC / Instrumentos Plugados / Palheta)
        test_bar = ctk.CTkFrame(tab, fg_color="#0F172A", corner_radius=8, border_width=1, border_color="#334155")
        test_bar.pack(fill="x", padx=10, pady=(2, 4))

        tb_row = ctk.CTkFrame(test_bar, fg_color="transparent")
        tb_row.pack(fill="x", padx=10, pady=4)

        ctk.CTkLabel(
            tb_row, text="🎮 Toque & Teste:",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="#38BDF8"
        ).pack(side="left", padx=(0, 6))

        # Botões das Casas
        self.fret_buttons = {}
        fret_defs = [
            ("green", "🟩 Casa 1", "#15803D", "#22C55E"),
            ("red", "🟥 Casa 2", "#B91C1C", "#EF4444"),
            ("yellow", "🟨 Casa 3", "#A16207", "#EAB308"),
            ("blue", "🟦 Casa 4", "#1D4ED8", "#3B82F6"),
            ("orange", "🟧 Casa 5", "#C2410C", "#F97316"),
        ]

        for lane, label_base, bg_norm, bg_glow in fret_defs:
            k = self.key_controls.get(lane, "")
            display_k = KEY_NAMES_FRIENDLY.get(k.lower(), k.upper())
            btn = ctk.CTkButton(
                tb_row,
                text=f"{label_base} ({display_k})",
                width=96, height=30,
                fg_color=bg_norm, hover_color=bg_glow,
                font=ctk.CTkFont(size=10, weight="bold"),
                command=lambda l=lane: self._on_fret_button_clicked(l)
            )
            btn.pack(side="left", padx=2)
            self.fret_buttons[lane] = {
                "widget": btn,
                "label_base": label_base,
                "bg_norm": bg_norm,
                "bg_glow": bg_glow
            }

        # Botão da Palheta (Strum Bar)
        strum_k = self.key_controls.get("strum", "space")
        strum_display = KEY_NAMES_FRIENDLY.get(strum_k.lower(), strum_k.upper())
        self.btn_strum = ctk.CTkButton(
            tb_row,
            text=f"⚡ Palheta ({strum_display})",
            width=120, height=30,
            fg_color="#6B21A8", hover_color="#A855F7",
            font=ctk.CTkFont(size=10, weight="bold"),
            command=self._on_strum_button_clicked
        )
        self.btn_strum.pack(side="left", padx=3)
        set_tooltip(self.btn_strum, "Dispara a palhetada das notas seguradas ou corda solta")

        # Botão de Teste Vocal
        vocal_k = self.key_controls.get("vocal_test", "v")
        vocal_display = KEY_NAMES_FRIENDLY.get(vocal_k.lower(), vocal_k.upper())
        self.btn_vocal_test = ctk.CTkButton(
            tb_row,
            text=f"🎤 Vocal ({vocal_display})",
            width=96, height=30,
            fg_color="#9D174D", hover_color="#EC4899",
            font=ctk.CTkFont(size=10, weight="bold"),
            command=self._on_vocal_test_clicked
        )
        self.btn_vocal_test.pack(side="left", padx=2)
        set_tooltip(self.btn_vocal_test, "Toca notas melódicas para testar afinação vocal e frases de canto")

        # Configurar Teclas
        btn_cfg_keys = ctk.CTkButton(
            tb_row,
            text="⌨️ Teclas & Palheta...",
            width=135, height=30,
            fg_color="#334155", hover_color="#475569",
            font=ctk.CTkFont(size=10, weight="bold"),
            command=self._open_key_config_dialog
        )
        btn_cfg_keys.pack(side="right", padx=2)
        set_tooltip(btn_cfg_keys, "Escolha livremente quais teclas do seu teclado tocam as casas, a palheta (espaço) e o vocal!")

        # Indicador / Botão Rápido de Modo de Palheta
        self.btn_mode_toggle = ctk.CTkButton(
            tb_row,
            text=self._get_strum_mode_text(),
            width=140, height=30,
            fg_color="#1E293B", hover_color="#334155",
            font=ctk.CTkFont(size=10),
            command=self._toggle_strum_mode
        )
        self.btn_mode_toggle.pack(side="right", padx=3)
        set_tooltip(self.btn_mode_toggle, "Clique para alternar entre Palheta Livre (apertou tocou) ou Obrigatória (segure a casa e aperte Palheta/Espaço)")

        # Canvas Interativo (Mini-REAPER)
        canvas_box = ctk.CTkFrame(tab, fg_color="#0B0F17", corner_radius=6)
        canvas_box.pack(fill="both", expand=True, padx=10, pady=4)

        self.timeline = MiniReaperCanvas(canvas_box, self.song, on_change_callback=self._update_note_counter)
        self.timeline.pack(fill="both", expand=True)

        # Instruções rápidas do mouse
        inst_row = ctk.CTkFrame(tab, fg_color="transparent")
        inst_row.pack(fill="x", padx=10, pady=2)

        inst_lbl = ctk.CTkLabel(
            inst_row,
            text="💡 Como mexer: Clique Esquerdo = Coloca/Remove Nota | Clique Direito = Deleta Nota | Clique na régua superior = Move o cursor vermelho",
            font=ctk.CTkFont(size=10),
            text_color="#94A3B8"
        )
        inst_lbl.pack(side="left", padx=4)

        self.note_count_lbl = ctk.CTkLabel(
            inst_row,
            text="Notas na Trilha: 0",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#38BDF8"
        )
        self.note_count_lbl.pack(side="right", padx=4)

        # Controles de Gravação ao Vivo e Áudio
        ctrl_box = ctk.CTkFrame(tab, fg_color="#0F172A", corner_radius=8)
        ctrl_box.pack(fill="x", padx=10, pady=(4, 6))

        # Linha 1: Áudio e BPM
        row1 = ctk.CTkFrame(ctrl_box, fg_color="transparent")
        row1.pack(fill="x", padx=8, pady=4)

        ctk.CTkLabel(row1, text="🎵 Áudio de Fundo:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(0, 4))
        self.audio_entry = ctk.CTkEntry(row1, placeholder_text="Selecione um arquivo de música (.mp3 / .wav / .ogg)...")
        self.audio_entry.pack(side="left", fill="x", expand=True, padx=4)
        set_tooltip(self.audio_entry, "Arquivo de música que vai tocar enquanto você edita ou grava")

        btn_browse_audio = ctk.CTkButton(row1, text="Carregar Áudio...", width=120, command=self._on_browse_audio)
        btn_browse_audio.pack(side="left", padx=3)
        set_tooltip(btn_browse_audio, "Abre o explorador para escolher a música (.mp3 / .wav / .ogg)")

        btn_browse_stems = ctk.CTkButton(row1, text="🎚️ Stems...", width=95, fg_color="#334155", hover_color="#475569", command=self._on_browse_stems)
        btn_browse_stems.pack(side="left", padx=2)
        set_tooltip(btn_browse_stems, "Carrega pasta com faixas isoladas (guitar.ogg, bass.ogg, drums.ogg, vocals.ogg)")

        ctk.CTkLabel(row1, text="BPM:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(10, 4))
        self.bpm_entry = ctk.CTkEntry(row1, width=65)
        self.bpm_entry.insert(0, "120.0")
        self.bpm_entry.pack(side="left", padx=4)
        set_tooltip(self.bpm_entry, "Batidas por minuto (andamento da música). Define a precisão da régua")

        btn_tap = ctk.CTkButton(row1, text="🥁 Tap BPM", width=85, fg_color="#334155", command=self._on_tap_bpm)
        btn_tap.pack(side="left", padx=4)
        set_tooltip(btn_tap, "Clique repetidamente no ritmo da música para calcular o BPM automático!")

        # Linha 2: Ações de Playback e Gravação
        row2 = ctk.CTkFrame(ctrl_box, fg_color="transparent")
        row2.pack(fill="x", padx=8, pady=(2, 6))

        self.btn_play_toggle = ctk.CTkButton(
            row2, text="▶️ Tocar Música", width=140, height=34,
            fg_color="#3B82F6", hover_color="#2563EB", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._toggle_playback
        )
        self.btn_play_toggle.pack(side="left", padx=4)
        set_tooltip(self.btn_play_toggle, "Inicia ou pausa a música para você acompanhar as notas no cursor")

        self.btn_rec_toggle = ctk.CTkButton(
            row2, text="🔴 INICIAR GRAVAÇÃO AO VIVO", width=240, height=34,
            fg_color="#DC2626", hover_color="#B91C1C", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._toggle_recording
        )
        self.btn_rec_toggle.pack(side="left", padx=4)
        set_tooltip(self.btn_rec_toggle, "Grava ao vivo! Cada nota tocada na guitarra/bateria física ou teclado será colocada automaticamente na linha do tempo!")

        # Duração de Sustain Padrão
        ctk.CTkLabel(row2, text="Duração do Sustain:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(14, 4))
        self.sustain_combo = ctk.CTkComboBox(
            row2, width=120,
            values=["Toque (180ms)", "Curto (500ms)", "Longo (1.0s)", "Solos (2.0s)"],
            command=self._on_sustain_changed
        )
        self.sustain_combo.set("Toque (180ms)")
        self.sustain_combo.pack(side="left", padx=4)
        set_tooltip(self.sustain_combo, "Escolha o comprimento da cauda da nota (para notas sustentadas/seguradas)")

        btn_clear = ctk.CTkButton(
            row2, text="🗑️ Limpar Trilha Atual", width=160, height=34,
            fg_color="#475569", hover_color="#334155", font=ctk.CTkFont(size=11),
            command=self._clear_current_track_notes
        )
        btn_clear.pack(side="right", padx=4)
        set_tooltip(btn_clear, "Apaga todas as notas da trilha do instrumento selecionado")

    def _on_track_changed(self, choice):
        track_key = "guitar"
        if "Baixo" in choice:
            track_key = "bass"
        elif "Bateria" in choice:
            track_key = "drum"
        elif "Teclado" in choice:
            track_key = "keys"
        elif "Vocais" in choice:
            track_key = "vocals"
        self.timeline.set_track(track_key)
        self._update_note_counter()

    def _on_diff_changed(self, choice):
        self.timeline.set_difficulty(choice)
        self._update_note_counter()

    def _on_snap_changed(self, choice):
        if "1/8" in choice:
            self.timeline.snap_grid_division = 8
        elif "1/16" in choice:
            self.timeline.snap_grid_division = 16
        elif "1/2" in choice:
            self.timeline.snap_grid_division = 2
        else:
            self.timeline.snap_grid_division = 4

    def _on_sustain_changed(self, choice):
        if "500ms" in choice:
            self.timeline.set_sustain(500)
        elif "1.0s" in choice:
            self.timeline.set_sustain(1000)
        elif "2.0s" in choice:
            self.timeline.set_sustain(2000)
        else:
            self.timeline.set_sustain(180)

    def _adjust_zoom(self, delta):
        new_zoom = self.timeline.pixels_per_second + delta
        self.timeline.set_zoom(new_zoom)

    def _update_note_counter(self):
        if self.timeline.current_track == "vocals":
            count = len(self.song.vocal_notes)
        else:
            notes = self.timeline._get_notes()
            count = sum(1 for n in notes if n.difficulty == self.timeline.current_difficulty or n.lane in ["overdrive", "solo"])
        self.note_count_lbl.configure(text=f"Notas na Trilha: {count}")

    # -------------------------------------------------------------------------
    # ABA 3: METADADOS, CAPA & EXPORTAÇÃO
    # -------------------------------------------------------------------------
    def _build_metadata_tab(self, tab):
        main_box = ctk.CTkFrame(tab, fg_color="transparent")
        main_box.pack(fill="both", expand=True, padx=10, pady=8)

        # Coluna da Esquerda: Formulário de Metadados
        left_col = ctk.CTkFrame(main_box, fg_color="#0F172A", corner_radius=8)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 6))

        title_lbl = ctk.CTkLabel(left_col, text="📝 Informações da Música", font=ctk.CTkFont(size=13, weight="bold"), text_color="#38BDF8")
        title_lbl.pack(anchor="w", padx=14, pady=(10, 4))

        fields_frame = ctk.CTkFrame(left_col, fg_color="transparent")
        fields_frame.pack(fill="both", expand=True, padx=14, pady=4)

        row = 0
        def add_meta_field(label_text, default_val, tip=""):
            nonlocal row
            lbl = ctk.CTkLabel(fields_frame, text=label_text, font=ctk.CTkFont(size=11, weight="bold"))
            lbl.grid(row=row, column=0, padx=6, pady=4, sticky="w")
            entry = ctk.CTkEntry(fields_frame, width=280)
            entry.insert(0, str(default_val))
            entry.grid(row=row, column=1, padx=6, pady=4, sticky="w")
            if tip:
                set_tooltip(entry, tip)
            row += 1
            return entry

        self.f_title = add_meta_field("Título da Música:", self.song.title, "Nome da faixa que aparece no jogo")
        self.f_artist = add_meta_field("Artista / Banda:", self.song.artist, "Nome do artista ou banda")
        self.f_album = add_meta_field("Nome do Álbum:", self.song.album, "Álbum ao qual pertence a música")
        self.f_year = add_meta_field("Ano de Lançamento:", self.song.year, "Ano em 4 dígitos (ex: 2026)")
        self.f_genre = add_meta_field("Gênero Musical:", self.song.genre, "Ex: Rock, Metal, Pop, Classic Rock")
        self.f_charter = add_meta_field("Autor do Chart:", self.song.charter, "Seu nome ou apelido como criador do chart")
        self.f_preview = add_meta_field("Início da Prévia (ms):", self.song.preview_start_ms, "Tempo em milissegundos para tocar a amostra no menu (ex: 30000 = 30 seg)")

        # Botão de Letra & Vocais no formulário
        btn_lyrics_meta = ctk.CTkButton(
            left_col, text="🎤 Gerenciar Letra da Música (.txt / .lrc)...", width=280, height=32,
            fg_color="#EC4899", hover_color="#DB2777", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._open_lyrics_dialog
        )
        btn_lyrics_meta.pack(padx=14, pady=(8, 12), anchor="w")
        set_tooltip(btn_lyrics_meta, "Cole ou importe a letra da música para sincronizar automaticamente com a faixa vocal!")

        # Coluna da Direita: Capa do Álbum e Pré-visualização
        right_col = ctk.CTkFrame(main_box, fg_color="#0F172A", corner_radius=8, width=320)
        right_col.pack(side="right", fill="both", padx=(6, 0))

        art_title = ctk.CTkLabel(right_col, text="🖼️ Capa do Álbum", font=ctk.CTkFont(size=13, weight="bold"), text_color="#38BDF8")
        art_title.pack(anchor="w", padx=14, pady=(10, 4))

        # Caixa do Thumbnail
        self.art_preview_frame = ctk.CTkFrame(right_col, fg_color="#1E293B", width=220, height=200, corner_radius=8)
        self.art_preview_frame.pack(padx=14, pady=8)
        self.art_preview_frame.pack_propagate(False)

        self.art_img_label = ctk.CTkLabel(
            self.art_preview_frame,
            text="Sem Imagem\nCarregada",
            font=ctk.CTkFont(size=11),
            text_color="#94A3B8"
        )
        self.art_img_label.pack(expand=True)

        self.art_path_lbl = ctk.CTkLabel(
            right_col, text="Nenhum arquivo selecionado",
            font=ctk.CTkFont(size=10), text_color="#64748B", wraplength=280
        )
        self.art_path_lbl.pack(padx=14, pady=2)

        btn_browse_art = ctk.CTkButton(
            right_col, text="🖼️ Carregar Capa (.PNG / .JPG)", width=220, height=32,
            fg_color="#0284C7", hover_color="#0369A1", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_browse_album_art
        )
        btn_browse_art.pack(padx=14, pady=(8, 14))
        set_tooltip(btn_browse_art, "Carrega a arte do álbum que será exibida no menu do jogo e na tela do PS3/RPCS3")

        # Seletor de Jogo de Destino (Aba 3)
        target_box_3 = ctk.CTkFrame(tab, fg_color="#0F172A", corner_radius=8)
        target_box_3.pack(fill="x", padx=10, pady=(6, 8))

        sel_game_row_3 = ctk.CTkFrame(target_box_3, fg_color="transparent")
        sel_game_row_3.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(
            sel_game_row_3,
            text="🎯 Escolha o Jogo de Destino:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#38BDF8"
        ).pack(side="left", padx=(0, 8))

        self.target_game_combo_tab3 = ctk.CTkComboBox(
            sel_game_row_3, width=320, height=32,
            values=[
                "🎸 Rock Band 3 (Emulador RPCS3 no PC)",
                "🎮 Clone Hero / YARG (PC)",
                "📦 PlayStation 3 Console (CFW / HEN / PKG)",
                "🟢 Xbox 360 (Rock Band 3 / 2 - RGH / CON)"
            ],
            command=self._on_target_game_changed
        )
        self.target_game_combo_tab3.set("🎸 Rock Band 3 (Emulador RPCS3 no PC)")
        self.target_game_combo_tab3.pack(side="left", padx=4)
        set_tooltip(self.target_game_combo_tab3, "Selecione o formato para o qual a música será compilada")

        self.btn_export_selected_tab3 = ctk.CTkButton(
            sel_game_row_3, text="⚡ SALVAR E EXPORTAR PARA O JOGO", width=280, height=36,
            fg_color="#10B981", hover_color="#059669", font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: self._on_export_to_selected_game(sync_metadata=True)
        )
        self.btn_export_selected_tab3.pack(side="right", padx=4)
        set_tooltip(self.btn_export_selected_tab3, "Salva as informações da música e compila para o jogo selecionado")

        self.target_desc_label_tab3 = ctk.CTkLabel(
            target_box_3,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#94A3B8",
            justify="left"
        )
        self.target_desc_label_tab3.pack(anchor="w", padx=14, pady=(2, 10))

        # Atalhos rápidos inferiores
        quick_row_3 = ctk.CTkFrame(tab, fg_color="transparent")
        quick_row_3.pack(fill="x", padx=10, pady=(0, 4))

        ctk.CTkLabel(quick_row_3, text="Atalhos Rápidos:", font=ctk.CTkFont(size=10, weight="bold"), text_color="#64748B").pack(side="left", padx=(4, 8))

        btn_save_rb3 = ctk.CTkButton(
            quick_row_3, text="🚀 RB3 (RPCS3 / Console)", width=170, height=28,
            fg_color="#334155", hover_color="#475569", font=ctk.CTkFont(size=10),
            command=self._save_from_editor_rb3
        )
        btn_save_rb3.pack(side="left", padx=3)

        btn_save_ps3 = ctk.CTkButton(
            quick_row_3, text="📦 Pacote PS3 (PKG/SFO)", width=170, height=28,
            fg_color="#334155", hover_color="#475569", font=ctk.CTkFont(size=10),
            command=self._save_from_editor_ps3
        )
        btn_save_ps3.pack(side="left", padx=3)

        btn_save_ch = ctk.CTkButton(
            quick_row_3, text="🎮 Clone Hero / YARG", width=160, height=28,
            fg_color="#334155", hover_color="#475569", font=ctk.CTkFont(size=10),
            command=self._save_from_editor_ch
        )
        btn_save_ch.pack(side="left", padx=3)

    def _on_browse_album_art(self):
        f = filedialog.askopenfilename(
            title="Selecione a Imagem da Capa do Álbum",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.bmp *.webp")]
        )
        if f:
            self.song.album_art_path = f
            self._load_art_preview(f)

    def _load_art_preview(self, img_path):
        try:
            im = Image.open(img_path)
            # Redimensiona mantendo proporção para 180x180
            im.thumbnail((180, 180), Image.Resampling.LANCZOS)
            self.preview_image_ctk = ctk.CTkImage(light_image=im, dark_image=im, size=im.size)
            self.art_img_label.configure(image=self.preview_image_ctk, text="")
            self.art_path_lbl.configure(text=os.path.basename(img_path))
        except Exception as e:
            messagebox.showerror("Erro na Imagem", f"Não foi possível abrir a imagem: {e}")

    # -------------------------------------------------------------------------
    # ABA 4: GUIA PASSO A PASSO (PARA LEIGOS)
    # -------------------------------------------------------------------------
    def _build_guide_tab(self, tab):
        scroll_frame = ctk.CTkScrollableFrame(tab, fg_color="#0F172A", corner_radius=8)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=8)

        guide_title = ctk.CTkLabel(
            scroll_frame,
            text="📖 Guia Completo: Criando e Convertendo Músicas Sem Complicação!",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#38BDF8"
        )
        guide_title.pack(anchor="w", padx=16, pady=(12, 6))

        intro_text = (
            "Com o MidGuitar Universal Studio, você não precisa mais instalar ou configurar softwares difíceis como\n"
            "o REAPER, Magma v2, C3 Custom Tools ou Onyx. Tudo o que você precisa já está integrado aqui de forma visual e simples!\n"
        )
        ctk.CTkLabel(scroll_frame, text=intro_text, font=ctk.CTkFont(size=11), text_color="#E2E8F0", justify="left").pack(anchor="w", padx=16, pady=2)

        def _open_visual_tutorial():
            tut_path = os.path.abspath("TUTORIAL_VISUAL.md")
            if os.path.exists(tut_path):
                try:
                    os.startfile(tut_path)
                except Exception:
                    pass

        btn_tut = ctk.CTkButton(
            scroll_frame,
            text="🖼️ Abrir Tutorial Visual Ilustrado (Tela por Tela com Imagens)",
            command=_open_visual_tutorial,
            fg_color="#0284C7",
            hover_color="#0369A1",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        btn_tut.pack(anchor="w", padx=16, pady=(6, 10))

        def add_step(num, title, body_text):
            step_box = ctk.CTkFrame(scroll_frame, fg_color="#1E293B", corner_radius=6)
            step_box.pack(fill="x", padx=14, pady=6)
            t_lbl = ctk.CTkLabel(step_box, text=f"{num}. {title}", font=ctk.CTkFont(size=12, weight="bold"), text_color="#FACC15")
            t_lbl.pack(anchor="w", padx=12, pady=(8, 2))
            b_lbl = ctk.CTkLabel(step_box, text=body_text, font=ctk.CTkFont(size=11), text_color="#CBD5E1", justify="left")
            b_lbl.pack(anchor="w", padx=12, pady=(0, 8))

        add_step(
            "1", "Como Converter Músicas Baixadas da Internet (Chorus Encore / RhythmVerse)",
            "• Baixe qualquer música nos sites de costume (ex: Chorus Encore ou Google Drive).\n"
            "• Na aba '⚡ Conversor 1 Clique', clique em 'Buscar Pasta...' e aponte para a pasta da música descompactada.\n"
            "• Clique em '🚀 Converter para Rock Band 3' ou '📦 Gerar Pacote PS3 / RPCS3'. Pronto! Ele cria os arquivos oficiais na hora."
        )

        add_step(
            "2", "Como Criar uma Música Colocando Notas à Mão (Estilo REAPER Visual)",
            "• Vá na aba '🎛️ Editor Visual de Notas'.\n"
            "• Clique em 'Carregar Áudio...' e escolha seu MP3 ou WAV favorito.\n"
            "• Clique na régua colorida para colocar notas: Verde (Casa 1), Vermelha (Casa 2), Amarela (Casa 3), Azul (Casa 4) e Laranja (Casa 5).\n"
            "• Para apagar uma nota: basta clicar com o botão direito do mouse em cima dela.\n"
            "• Se quiser notas longas (que você segura), ajuste o seletor 'Duração do Sustain'."
        )

        add_step(
            "3", "Como Gravar Tocando ao Vivo na sua Guitarra ou Bateria Real",
            "• Conecte sua guitarra USB, guitarra MIDI, teclado ou bateria eletrônica no computador.\n"
            "• Carregue a música e clique no botão vermelho '🔴 INICIAR GRAVAÇÃO AO VIVO'.\n"
            "• A música vai começar a tocar: toque no ritmo certo no seu instrumento real!\n"
            "• Cada palhetada ou batida no pad é gravada na linha do tempo em tempo real como se estivesse no REAPER!"
        )

        add_step(
            "4", "Como Colocar a Imagem da Capa do Álbum",
            "• Acesse a aba '🖼️ Metadados, Capa & Exportação'.\n"
            "• Clique no botão '🖼️ Carregar Capa (.PNG / .JPG)' e escolha uma foto ou capa da música.\n"
            "• A imagem é redimensionada automaticamente para os tamanhos corretos do PS3 (ICON0.PNG) e Clone Hero (album.png)!"
        )

        add_step(
            "5", "Como Jogar no Emulador RPCS3 (PC)",
            "• Após clicar em '📦 Gerar Pacote PS3 / RPCS3', abra a pasta gerada.\n"
            "• Dê dois cliques no arquivo 'INSTALAR_NO_RPCS3_AUTOMATICO.bat' que nós criamos dentro dela!\n"
            "• Ele detecta seu emulador e copia as músicas em 1 segundo. Quando você abrir o Rock Band 3 no RPCS3, ela já vai estar lá!"
        )

        add_step(
            "6", "Como Jogar no PlayStation 3 Real (Videogame com HEN ou CFW)",
            "• Copie a pasta gerada para um pendrive FAT32 ou envie por FTP (FileZilla).\n"
            "• Cole a pasta 'USRDIR/songs' no diretório do jogo no PS3: /dev_hdd0/game/BLUS30463/USRDIR/songs/.\n"
            "• Inicie o Rock Band 3 no console e divirta-se!"
        )

        add_step(
            "7", "Como Jogar no Clone Hero ou YARG (PC)",
            "• Clique no botão '🎮 Exportar Clone Hero / YARG'.\n"
            "• Selecione sua pasta de músicas (geralmente Documentos/Clone Hero/Songs).\n"
            "• No jogo, vá em Settings -> General -> Scan Songs e a música estará pronta com capa e todas as dificuldades!"
        )

        add_step(
            "8", "Como Testar e Tocar Junto com a Música (Teclado do PC, Instrumentos Reais & Vocal)",
            "• Na aba '🎛️ Editor Visual de Notas', clique em '▶️ Tocar Música' para ouvir e ver a linha do tempo correr!\n"
            "• Você pode tocar junto usando o teclado do computador: A (Verde), S (Vermelho), J (Amarelo), K (Azul), L (Laranja), Espaço (Palheta) e V (Vocal)!\n"
            "• Clique em '⌨️ Teclas & Palheta...' para personalizar qualquer tecla do teclado e escolher entre:\n"
            "   - Palheta Livre: ao apertar a tecla da casa já toca o som direto.\n"
            "   - Palheta Obrigatória (Estilo Guitar Hero): segure a casa e aperte a tecla da palheta (ex: Espaço ou Enter)!\n"
            "• Se plugar uma guitarra Rock Band, Gamepad USB, bateria eletrônica ou teclado MIDI no PC, o estúdio detecta na hora e pisca as casas ao vivo!\n"
            "• A tecla Vocal (V) emite sons melódicos de teste vocal para checar a harmonia da canção e gravar faixas de canto!"
        )

        add_step(
            "9", "Como Colocar e Sincronizar a Letra da Música (Vocais & Stems)",
            "• Clique no botão rosa '🎤 Letra da Música (.txt/.lrc)...' no topo da linha do tempo ou na aba Metadados.\n"
            "• Cole a letra da música diretamente de qualquer site de letras (ou clique em 'Carregar Arquivo .txt / .lrc').\n"
            "• Clique em '✨ SINCRONIZAR E APLICAR LETRA AOS VOCAIS':\n"
            "   - O sistema divide as palavras automaticamente em sílabas fonéticas oficiais do Rock Band (com hífens terminadores).\n"
            "   - Se você usou um arquivo .lrc, cada frase é posicionada exatamente no tempo em que é cantada!\n"
            "   - As palavras/sílabas aparecem escritas diretamente na linha do tempo quando você seleciona a trilha '🎤 Vocais'!\n"
            "• Se tiver faixas isoladas (stems como guitar.ogg, bass.ogg, drums.ogg, vocals.ogg), clique em '🎚️ Stems...' para o mixer multitrack oficial!"
        )

    # -------------------------------------------------------------------------
    # SINCRONIZAÇÃO E CONTROLES
    # -------------------------------------------------------------------------
    def _sync_fields_to_song(self):
        self.song.title = self.f_title.get()
        self.song.artist = self.f_artist.get()
        self.song.album = self.f_album.get()
        self.song.genre = self.f_genre.get()
        self.song.charter = self.f_charter.get()
        try:
            self.song.year = int(self.f_year.get())
        except Exception:
            pass
        try:
            self.song.preview_start_ms = int(self.f_preview.get())
        except Exception:
            pass

    def _sync_song_to_fields(self):
        self.f_title.delete(0, "end")
        self.f_title.insert(0, self.song.title)

        self.f_artist.delete(0, "end")
        self.f_artist.insert(0, self.song.artist)

        self.f_album.delete(0, "end")
        self.f_album.insert(0, self.song.album)

        self.f_year.delete(0, "end")
        self.f_year.insert(0, str(self.song.year))

        self.f_genre.delete(0, "end")
        self.f_genre.insert(0, self.song.genre)

        self.f_charter.delete(0, "end")
        self.f_charter.insert(0, self.song.charter)

        self.f_preview.delete(0, "end")
        self.f_preview.insert(0, str(self.song.preview_start_ms))

        self.bpm_entry.delete(0, "end")
        self.bpm_entry.insert(0, str(self.song.bpm))

        if self.song.audio_path:
            self.audio_entry.delete(0, "end")
            self.audio_entry.insert(0, self.song.audio_path)

    def _on_browse_audio(self):
        f = filedialog.askopenfilename(filetypes=[("Arquivos de Áudio", "*.mp3 *.wav *.ogg")])
        if f:
            self.audio_entry.delete(0, "end")
            self.audio_entry.insert(0, f)
            self.song.audio_path = f

    def _on_browse_stems(self):
        f = filedialog.askdirectory(title="Selecione a pasta com as faixas separadas (stems)")
        if not f:
            return
        stems = []
        for file in os.listdir(f):
            if file.lower().endswith((".ogg", ".mp3", ".wav", ".flac")):
                stems.append(os.path.join(f, file))
        if stems:
            self.song.audio_stems = stems
            main_track = stems[0]
            for s in stems:
                s_name = os.path.basename(s).lower()
                if "song" in s_name or "backing" in s_name or "audio" in s_name:
                    main_track = s
                    break
            self.song.audio_path = main_track
            self.audio_entry.delete(0, "end")
            self.audio_entry.insert(0, main_track)
            messagebox.showinfo("Stems Carregados!", f"🎉 {len(stems)} faixas isoladas carregadas com sucesso para o mixer do Rock Band 3 e Clone Hero!")
        else:
            messagebox.showwarning("Aviso", "Nenhum arquivo de áudio (.ogg, .mp3, .wav) foi encontrado na pasta.")

    def _open_lyrics_dialog(self):
        LyricsManagerDialog(
            self,
            self.song,
            on_applied_callback=self._on_lyrics_applied
        )

    def _on_lyrics_applied(self):
        self.timeline.redraw()
        self._update_note_counter()

    def _on_tap_bpm(self):
        now = time.time()
        self.tap_times.append(now)
        if len(self.tap_times) > 8:
            self.tap_times.pop(0)
        if len(self.tap_times) >= 3:
            diffs = [self.tap_times[i] - self.tap_times[i - 1] for i in range(1, len(self.tap_times))]
            avg_diff = sum(diffs) / len(diffs)
            if avg_diff > 0:
                calculated_bpm = round(60.0 / avg_diff, 1)
                self.bpm_entry.delete(0, "end")
                self.bpm_entry.insert(0, str(calculated_bpm))
                self.song.bpm = calculated_bpm
                self.timeline.redraw()

    def _toggle_playback(self):
        if self.is_playing:
            pygame.mixer.music.stop()
            self.is_playing = False
            self.btn_play_toggle.configure(text="▶️ Tocar Música", fg_color="#3B82F6")
        else:
            path = self.audio_entry.get().strip()
            if path and os.path.exists(path):
                try:
                    pygame.mixer.music.load(path)
                    # Começa no tempo atual do playhead se houver
                    start_sec = self.timeline.current_playhead_ms / 1000.0
                    pygame.mixer.music.play(start=start_sec)
                    self.is_playing = True
                    self.playback_start_time = time.time() - start_sec
                    self.btn_play_toggle.configure(text="⏹️ Parar Reprodução", fg_color="#DC2626")
                except Exception as e:
                    messagebox.showerror("Erro", f"Erro ao reproduzir áudio: {e}")
            else:
                messagebox.showwarning("Aviso", "Selecione um arquivo de áudio válido primeiro!")

    def _toggle_recording(self):
        if self.is_recording:
            self.is_recording = False
            if self.is_playing:
                self._toggle_playback()
            self.btn_rec_toggle.configure(text="🔴 INICIAR GRAVAÇÃO AO VIVO", fg_color="#DC2626")
            messagebox.showinfo("Gravação Finalizada", "Notas gravadas com sucesso na trilha!\nVocê pode conferir na tela ou exportar.")
        else:
            path = self.audio_entry.get().strip()
            if not path or not os.path.exists(path):
                messagebox.showwarning("Aviso", "Carregue um arquivo de áudio para acompanhar o ritmo da gravação!")
                return
            try:
                self.song.bpm = float(self.bpm_entry.get())
            except Exception:
                self.song.bpm = 120.0

            self.is_recording = True
            self.btn_rec_toggle.configure(text="⏹️ PARAR GRAVAÇÃO", fg_color="#10B981")
            if not self.is_playing:
                self._toggle_playback()

    def record_incoming_note(self, lane: str):
        """Disparado pelo teclado do PC ou instrumento físico ao apertar uma casa ou pad."""
        if not self.is_recording or not self.is_playing:
            return
        elapsed_ms = int((time.time() - self.playback_start_time) * 1000)
        sel_track = self.track_combo.get()

        if "Vocais" in sel_track or lane == "vocal":
            from src.creator.chart_model import VocalNote
            vocal_pitches = [60, 62, 64, 67, 69, 72]
            pitch = vocal_pitches[self.vocal_pitch_counter % len(vocal_pitches)]
            self.vocal_pitch_counter += 1
            v_note = VocalNote(time_ms=elapsed_ms, pitch=pitch, duration_ms=self.timeline.default_sustain_ms, lyric="La", is_phrase_marker=False)
            self.song.vocal_notes.append(v_note)
            self.timeline.redraw()
            self._update_note_counter()
            return

        track_key = "guitar"
        if "Baixo" in sel_track:
            track_key = "bass"
        elif "Bateria" in sel_track:
            track_key = "drum"
        elif "Teclado" in sel_track:
            track_key = "keys"

        target_lane = lane
        if lane == "open":
            target_lane = "orange" if track_key == "drum" else "green"

        note = NoteEvent(time_ms=elapsed_ms, lane=target_lane, duration_ms=self.timeline.default_sustain_ms, difficulty=self.timeline.current_difficulty)
        self.song.add_note(track_key, note)
        self.timeline.redraw()
        self._update_note_counter()

    def _clear_current_track_notes(self):
        sel_track = self.track_combo.get()
        if "Vocais" in sel_track:
            self.song.vocal_notes.clear()
            self.timeline.redraw()
            self._update_note_counter()
            messagebox.showinfo("Limpo", f"Notas da trilha {sel_track} foram limpas.")
            return

        track_key = "guitar"
        if "Baixo" in sel_track:
            track_key = "bass"
        elif "Bateria" in sel_track:
            track_key = "drum"
        elif "Teclado" in sel_track:
            track_key = "keys"
        self.song.clear_track(track_key)
        self.timeline.redraw()
        self._update_note_counter()
        messagebox.showinfo("Limpo", f"Notas da trilha {sel_track} foram limpas.")

    # -------------------------------------------------------------------------
    # TESTE & TOQUE INTERATIVO (TECLADO / INSTRUMENTO FÍSICO / VOCAL)
    # -------------------------------------------------------------------------
    def _get_strum_mode_text(self) -> str:
        mode = self.key_controls.get("strum_mode", "free")
        if mode == "strum":
            strum_k = self.key_controls.get("strum", "space")
            kname = KEY_NAMES_FRIENDLY.get(strum_k.lower(), strum_k.upper())
            return f"Modo: Palheta [{kname}]"
        return "Modo: Palheta Livre"

    def _toggle_strum_mode(self):
        cur = self.key_controls.get("strum_mode", "free")
        new_mode = "strum" if cur == "free" else "free"
        self.key_controls["strum_mode"] = new_mode
        self.btn_mode_toggle.configure(text=self._get_strum_mode_text())
        self._persist_key_controls()

    def _open_key_config_dialog(self):
        KeyStrumConfigDialog(
            self,
            current_map=self.key_controls,
            on_save_callback=self._on_key_config_saved
        )

    def _on_key_config_saved(self, new_map: dict):
        self.key_controls.update(new_map)
        self._persist_key_controls()
        self._refresh_key_buttons_labels()

    def _persist_key_controls(self):
        if hasattr(self.master, "config"):
            self.master.config["creator_keyboard_map"] = self.key_controls
            try:
                save_config(self.master.config)
            except Exception:
                pass

    def _refresh_key_buttons_labels(self):
        for lane, data in self.fret_buttons.items():
            k = self.key_controls.get(lane, "")
            display_k = KEY_NAMES_FRIENDLY.get(k.lower(), k.upper())
            data["widget"].configure(text=f"{data['label_base']} ({display_k})")

        strum_k = self.key_controls.get("strum", "space")
        strum_display = KEY_NAMES_FRIENDLY.get(strum_k.lower(), strum_k.upper())
        self.btn_strum.configure(text=f"⚡ Palheta ({strum_display})")

        vocal_k = self.key_controls.get("vocal_test", "v")
        vocal_display = KEY_NAMES_FRIENDLY.get(vocal_k.lower(), vocal_k.upper())
        self.btn_vocal_test.configure(text=f"🎤 Vocal ({vocal_display})")

        self.btn_mode_toggle.configure(text=self._get_strum_mode_text())

    def _is_text_entry_focused(self) -> bool:
        try:
            focused = self.focus_get()
            if not focused:
                return False
            f_class = str(type(focused)).lower()
            if "entry" in f_class or "combobox" in f_class or "text" in f_class:
                return True
        except Exception:
            pass
        return False

    def _on_window_key_press(self, event):
        if self._is_text_entry_focused():
            return

        key_sym = event.keysym.lower()
        strum_mode = self.key_controls.get("strum_mode", "free")

        # Verifica se corresponde a alguma das 5 casas
        for lane in ["green", "red", "yellow", "blue", "orange"]:
            if key_sym == self.key_controls.get(lane, "").lower():
                self.held_frets.add(lane)
                self._highlight_fret_button(lane, True)
                if strum_mode == "free":
                    self._play_fret_audio(lane)
                    if self.is_recording and self.is_playing:
                        self.record_incoming_note(lane)
                return

        # Verifica se corresponde à Palheta (Strum)
        if key_sym == self.key_controls.get("strum", "space").lower():
            self._flash_strum_button()
            if strum_mode == "strum":
                if self.held_frets:
                    for lane in list(self.held_frets):
                        self._play_fret_audio(lane)
                        if self.is_recording and self.is_playing:
                            self.record_incoming_note(lane)
                else:
                    self._play_open_audio()
                    if self.is_recording and self.is_playing:
                        self.record_incoming_note("open")
            else:
                if self.held_frets:
                    for lane in list(self.held_frets):
                        self._play_fret_audio(lane)
                else:
                    self._play_open_audio()
            return

        # Verifica se corresponde ao Vocal Test
        if key_sym == self.key_controls.get("vocal_test", "v").lower():
            self._trigger_vocal_test()
            return

    def _on_window_key_release(self, event):
        if self._is_text_entry_focused():
            return

        key_sym = event.keysym.lower()
        strum_mode = self.key_controls.get("strum_mode", "free")

        for lane in ["green", "red", "yellow", "blue", "orange"]:
            if key_sym == self.key_controls.get(lane, "").lower():
                self.held_frets.discard(lane)
                self._highlight_fret_button(lane, False)
                if strum_mode == "free":
                    self._stop_fret_audio(lane)
                return

    def _highlight_fret_button(self, lane: str, is_on: bool):
        fret_info = self.fret_buttons.get(lane)
        if not fret_info:
            return
        btn = fret_info["widget"]
        if is_on:
            btn.configure(fg_color=fret_info["bg_glow"])
        else:
            btn.configure(fg_color=fret_info["bg_norm"])

    def _flash_strum_button(self):
        self.btn_strum.configure(fg_color="#D8B4FE")
        self.after(150, lambda: self.btn_strum.configure(fg_color="#6B21A8"))

    def _flash_vocal_button(self):
        self.btn_vocal_test.configure(fg_color="#F472B6")
        self.after(150, lambda: self.btn_vocal_test.configure(fg_color="#9D174D"))

    def _on_fret_button_clicked(self, lane: str):
        self._highlight_fret_button(lane, True)
        self._play_fret_audio(lane)
        if self.is_recording and self.is_playing:
            self.record_incoming_note(lane)
        self.after(180, lambda: self._highlight_fret_button(lane, False))

    def _on_strum_button_clicked(self):
        self._flash_strum_button()
        if self.held_frets:
            for f in list(self.held_frets):
                self._play_fret_audio(f)
                if self.is_recording and self.is_playing:
                    self.record_incoming_note(f)
        else:
            self._play_open_audio()
            if self.is_recording and self.is_playing:
                self.record_incoming_note("open")

    def _on_vocal_test_clicked(self):
        self._trigger_vocal_test()

    def _play_fret_audio(self, lane: str):
        if not self.audio:
            return
        track = self.track_combo.get()
        if "Bateria" in track:
            drum_map = {"green": 49, "red": 38, "yellow": 42, "blue": 47, "orange": 36, "open": 36}
            note = drum_map.get(lane, 38)
            self.audio.play_note(note, velocity=115, channel=9)
            self.after(200, lambda n=note: self.audio.stop_note(n, channel=9))
            return

        notes = [52]
        if hasattr(self.master, "preset_data") and "frets" in self.master.preset_data:
            notes = self.master.preset_data["frets"].get(lane, {}).get("notes", [52])
        else:
            defaults = {"green": [52], "red": [55], "yellow": [57], "blue": [59], "orange": [62], "open": [40]}
            notes = defaults.get(lane, [52])

        self.audio.play_chord(notes, velocity=115)
        self.after(450, lambda: self.audio.stop_chord(notes))

    def _play_open_audio(self):
        if not self.audio:
            return
        track = self.track_combo.get()
        if "Bateria" in track:
            self.audio.play_note(36, velocity=120, channel=9)
            self.after(200, lambda: self.audio.stop_note(36, channel=9))
        else:
            self.audio.play_chord([40], velocity=115)
            self.after(400, lambda: self.audio.stop_chord([40]))

    def _stop_fret_audio(self, lane: str):
        if not self.audio:
            return
        if hasattr(self.master, "preset_data") and "frets" in self.master.preset_data:
            notes = self.master.preset_data["frets"].get(lane, {}).get("notes", [52])
            self.audio.stop_chord(notes)

    def _trigger_vocal_test(self):
        vocal_pitches = [60, 62, 64, 67, 69, 72]
        pitch = vocal_pitches[self.vocal_pitch_counter % len(vocal_pitches)]
        self.vocal_pitch_counter += 1

        self._flash_vocal_button()
        if self.audio:
            self.audio.play_note(pitch, velocity=110, channel=0)
            self.after(350, lambda p=pitch: self.audio.stop_note(p, channel=0))

        if self.is_recording and self.is_playing:
            elapsed_ms = int((time.time() - self.playback_start_time) * 1000)
            from src.creator.chart_model import VocalNote
            v_note = VocalNote(time_ms=elapsed_ms, pitch=pitch, duration_ms=self.timeline.default_sustain_ms, lyric="La", is_phrase_marker=False)
            self.song.vocal_notes.append(v_note)
            self.timeline.redraw()
            self._update_note_counter()

    def handle_live_instrument_note(self, lane_or_id: str, is_active: bool = True, is_strum: bool = False):
        """Recebe eventos de instrumentos físicos plugados (Guitarra, Bateria, Teclado USB/MIDI)."""
        lane_clean = lane_or_id.lower()
        if "green" in lane_clean or "casa 1" in lane_clean:
            lane = "green"
        elif "red" in lane_clean or "casa 2" in lane_clean or "38" in lane_clean or "snare" in lane_clean:
            lane = "red"
        elif "yellow" in lane_clean or "casa 3" in lane_clean or "42" in lane_clean or "hihat" in lane_clean:
            lane = "yellow"
        elif "blue" in lane_clean or "casa 4" in lane_clean or "47" in lane_clean or "tom" in lane_clean:
            lane = "blue"
        elif "orange" in lane_clean or "casa 5" in lane_clean or "49" in lane_clean or "crash" in lane_clean or "36" in lane_clean:
            lane = "orange"
        elif "strum" in lane_clean or is_strum:
            lane = "strum"
        elif "vocal" in lane_clean:
            lane = "vocal"
        else:
            lane = "green"

        if lane == "strum":
            self._flash_strum_button()
            if self.is_recording and self.is_playing:
                if self.held_frets:
                    for f in list(self.held_frets):
                        self.record_incoming_note(f)
                else:
                    self.record_incoming_note("open")
        elif lane == "vocal":
            self._trigger_vocal_test()
        else:
            if is_active:
                self.held_frets.add(lane)
                self._highlight_fret_button(lane, True)
                strum_mode = self.key_controls.get("strum_mode", "free")
                if strum_mode == "free" and self.is_recording and self.is_playing:
                    self.record_incoming_note(lane)
            else:
                self.held_frets.discard(lane)
                self._highlight_fret_button(lane, False)

    def _start_playback_poll(self):
        """Atualiza a posição do playhead vermelho no Canvas enquanto a música toca."""
        if self.is_playing:
            elapsed_ms = int((time.time() - self.playback_start_time) * 1000)
            self.timeline.set_playhead_time(elapsed_ms)
        self.after(50, self._start_playback_poll)

    # -------------------------------------------------------------------------
    # EXPORTAÇÕES FINAIS
    # -------------------------------------------------------------------------
    def _on_convert_to_rb3(self):
        if not self.song.title:
            messagebox.showwarning("Aviso", "Carregue ou digite o nome da música primeiro!")
            return
        out_dir = filedialog.askdirectory(title="Escolha onde salvar o pacote do Rock Band 3")
        if not out_dir:
            return
        pkg_dir = export_rb3_song_package(self.song, out_dir)
        messagebox.showinfo("Sucesso!", f"Pacote Rock Band 3 gerado com sucesso em:\n{pkg_dir}\n\nVocê já pode copiar para o RPCS3 ou Xbox 360!")

    def _on_export_ps3_pkg(self):
        if not self.song.title:
            messagebox.showwarning("Aviso", "Carregue ou digite o nome da música primeiro!")
            return
        out_dir = filedialog.askdirectory(title="Escolha onde salvar o pacote PS3 / RPCS3")
        if not out_dir:
            return
        pkg_dir = export_ps3_pkg_structure(self.song, out_dir)
        messagebox.showinfo(
            "Sucesso PS3 / RPCS3!",
            f"Estrutura PS3 / RPCS3 gerada com sucesso em:\n{pkg_dir}\n\n"
            f"• Para instalar no RPCS3: Execute o arquivo 'INSTALAR_NO_RPCS3_AUTOMATICO.bat' dentro da pasta!\n"
            f"• Para PS3 Real: Copie a pasta USRDIR para /dev_hdd0/game/BLUS30463/USRDIR/"
        )

    def _on_convert_to_clone_hero(self):
        if not self.song.title:
            messagebox.showwarning("Aviso", "Carregue ou digite o nome da música primeiro!")
            return
        out_dir = filedialog.askdirectory(title="Escolha a pasta de destino (ex: Clone Hero/Songs)")
        if not out_dir:
            return
        pkg_dir = export_clone_hero_song(self.song, out_dir)
        messagebox.showinfo("Sucesso Clone Hero!", f"Pasta Clone Hero gerada com sucesso em:\n{pkg_dir}\n\nAbra o jogo e faça um Scan Songs!")

    def _save_from_editor_rb3(self):
        self._sync_fields_to_song()
        self._on_convert_to_rb3()

    def _save_from_editor_ps3(self):
        self._sync_fields_to_song()
        self._on_export_ps3_pkg()

    def _save_from_editor_ch(self):
        self._sync_fields_to_song()
        self._on_convert_to_clone_hero()

    def _on_target_game_changed(self, choice):
        """Sincroniza os seletores de jogo entre as abas e atualiza a explicação na tela."""
        if hasattr(self, "target_game_combo"):
            self.target_game_combo.set(choice)
        if hasattr(self, "target_game_combo_tab3"):
            self.target_game_combo_tab3.set(choice)
        self._update_target_game_desc(choice)

    def _update_target_game_desc(self, choice):
        """Atualiza o texto descritivo do jogo de destino para que o usuário saiba exatamente o que será criado."""
        if "Clone Hero" in choice:
            desc = "🎮 Clone Hero / YARG: Gera pasta com 'song.ini', 'notes.mid', 'album.png' e áudio. Basta colar na pasta 'Songs' do jogo!"
        elif "RPCS3" in choice:
            desc = "🎸 Rock Band 3 (RPCS3): Gera pasta com 'songs.dta', MIDI RBN e o script 'INSTALAR_NO_RPCS3_AUTOMATICO.bat' para instalar com 2 cliques!"
        elif "PlayStation 3" in choice:
            desc = "📦 PS3 Real (CFW / HEN): Gera pacote DLC com 'PARAM.SFO' (BLUS30463), 'ICON0.PNG' e 'USRDIR/songs/' para pendrive ou FTP!"
        elif "Xbox 360" in choice:
            desc = "🟢 Xbox 360: Gera 'songs/songs.dta' e trilha MIDI RBN compatível com RGH/JTAG ou para compilar em CON com C3 Tools / Le Fluffie."
        else:
            desc = ""

        if hasattr(self, "target_desc_label"):
            self.target_desc_label.configure(text=desc)
        if hasattr(self, "target_desc_label_tab3"):
            self.target_desc_label_tab3.configure(text=desc)

    def _on_export_to_selected_game(self, sync_metadata: bool = False):
        """Identifica qual jogo está selecionado no menu e executa a exportação correta imediatamente!"""
        if sync_metadata:
            self._sync_fields_to_song()

        choice = self.target_game_combo.get() if hasattr(self, "target_game_combo") else ""
        if "Clone Hero" in choice:
            self._on_convert_to_clone_hero()
        elif "PlayStation 3" in choice or "RPCS3" in choice:
            self._on_export_ps3_pkg()
        elif "Xbox 360" in choice:
            self._on_convert_to_rb3()
        else:
            self._on_convert_to_rb3()

    def _on_auto_generate_clicked(self):
        """Gera automaticamente notas completas para todos os instrumentos selecionados."""
        selected = []
        if self.chk_gen_guitar.get():
            selected.append("guitar")
        if self.chk_gen_bass.get():
            selected.append("bass")
        if self.chk_gen_drums.get():
            selected.append("drum")
        if self.chk_gen_keys.get():
            selected.append("keys")
        if self.chk_gen_vocals.get():
            selected.append("vocals")

        if not selected:
            messagebox.showwarning("Aviso", "Selecione ao menos um instrumento para gerar as notas!")
            return

        try:
            self.song.bpm = float(self.bpm_entry.get())
        except Exception:
            self.song.bpm = 120.0

        intensity = self.intensity_combo.get()
        auto_generate_chart(self.song, selected_instruments=selected, intensity=intensity, generate_all_diffs=True)
        self.timeline.redraw()
        self._update_note_counter()

        inst_names = []
        if "guitar" in selected: inst_names.append("Guitarra")
        if "bass" in selected: inst_names.append("Baixo")
        if "drum" in selected: inst_names.append("Bateria")
        if "keys" in selected: inst_names.append("Teclado")
        if "vocals" in selected: inst_names.append("Vocais (Letras & Melodias)")

        messagebox.showinfo(
            "Auto-Chart Concluído!",
            f"✨ Notas geradas automaticamente com sucesso!\n\n"
            f"• Instrumentos: {', '.join(inst_names)}\n"
            f"• Estilo: {intensity}  |  BPM: {self.song.bpm}\n"
            f"• Dificuldades: Expert, Hard, Medium e Easy incluídas!\n\n"
            f"Você já pode ouvir a música com ▶️ Tocar Música, ajustar qualquer nota com o mouse ou ir direto para a aba de Exportação!"
        )
