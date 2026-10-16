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
from src.ui.mini_reaper_canvas import MiniReaperCanvas
from src.ui.tooltip import set_tooltip

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

        # Modal focus
        self.transient(master)
        self.after(100, self.lift)
        self.after(150, self.focus_force)

        self._build_ui()
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
            text="Crie notas à mão no Editor Visual, grave ao vivo tocando seu instrumento, coloque capa de álbum e exporte para PS3/RPCS3 sem precisar de REAPER, Magma ou Onyx!",
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

        tab_converter = self.tabview.add("⚡ Conversor 1 Clique (Chorus ➔ RB3/PS3)")
        tab_timeline = self.tabview.add("🎛️ Editor Visual de Notas (Mini-REAPER)")
        tab_metadata = self.tabview.add("🖼️ Metadados, Capa & Exportação")
        tab_guide = self.tabview.add("📖 Guia Passo a Passo (Para Leigos)")

        self._build_converter_tab(tab_converter)
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

        # Barra de Ações Rápidas de Conversão
        act_box = ctk.CTkFrame(tab, fg_color="transparent")
        act_box.pack(fill="x", padx=10, pady=8)

        btn_convert_rb3 = ctk.CTkButton(
            act_box, text="🚀 Converter para Rock Band 3 (Console & RPCS3)", width=280, height=38,
            fg_color="#10B981", hover_color="#059669", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_convert_to_rb3
        )
        btn_convert_rb3.pack(side="left", padx=4)
        set_tooltip(btn_convert_rb3, "Gera a pasta com songs.dta e arquivo MIDI compatível com Rock Band 3")

        btn_convert_ps3 = ctk.CTkButton(
            act_box, text="📦 Gerar Pacote PS3 / RPCS3 (PKG + SFO + ICON0)", width=290, height=38,
            fg_color="#0284C7", hover_color="#0369A1", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_export_ps3_pkg
        )
        btn_convert_ps3.pack(side="left", padx=4)
        set_tooltip(btn_convert_ps3, "Gera estrutura completa com PARAM.SFO, ICON0.PNG e script automático de instalação no RPCS3!")

        btn_convert_ch = ctk.CTkButton(
            act_box, text="🎮 Exportar para Clone Hero / YARG", width=240, height=38,
            fg_color="#3B82F6", hover_color="#2563EB", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_convert_to_clone_hero
        )
        btn_convert_ch.pack(side="left", padx=4)
        set_tooltip(btn_convert_ch, "Gera pasta pronta com song.ini, notes.mid e album.png para colar na pasta Songs do Clone Hero")

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

        # Atualiza tela do timeline e formulários
        self.timeline.song = self.song
        self.timeline.redraw()
        self._sync_song_to_fields()

        info_text = (
            f"🎵 Título: {self.song.title}\n"
            f"👤 Artista: {self.song.artist}  |  Álbum: {self.song.album} ({self.song.year})\n"
            f"⚡ BPM: {self.song.bpm}  |  Gênero: {self.song.genre}  |  Charter: {self.song.charter}\n"
            f"🔊 Áudio detectado: {'Sim (' + os.path.basename(self.song.audio_path) + ')' if self.song.audio_path else 'Não encontrado'}\n"
            f"🖼️ Imagem da Capa: {'Encontrada' if self.song.album_art_path else 'Não informada'}\n"
            f"--------------------------------------------------\n"
            f"🎸 Guitarra: {g_count} notas mapeadas\n"
            f"🎸 Baixo: {b_count} notas mapeadas\n"
            f"🥁 Bateria: {d_count} notas mapeadas\n"
            f"🎹 Teclado: {k_count} notas mapeadas\n"
            f"✨ Seções/Eventos: {len(self.song.events)} marcadores\n"
        )
        self.info_label.configure(text=info_text, justify="left", font=ctk.CTkFont(family="Consolas", size=12), text_color="#F8FAFC")
        if self.song.album_art_path:
            self._load_art_preview(self.song.album_art_path)

    # -------------------------------------------------------------------------
    # ABA 2: EDITOR VISUAL DE NOTAS (MINI-REAPER) & GRAVAÇÃO
    # -------------------------------------------------------------------------
    def _build_timeline_tab(self, tab):
        # Barra superior com seletores de Instrumento, Dificuldade, Zoom e Grid
        bar = ctk.CTkFrame(tab, fg_color="#0F172A", corner_radius=8)
        bar.pack(fill="x", padx=10, pady=(6, 4))

        # Instrumento
        ctk.CTkLabel(bar, text="Instrumento:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(10, 4), pady=6)
        self.track_combo = ctk.CTkComboBox(
            bar, width=175,
            values=["🎸 Guitarra (5 Casas)", "🎸 Baixo", "🥁 Bateria", "🎹 Teclado"],
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
        btn_browse_audio.pack(side="left", padx=4)
        set_tooltip(btn_browse_audio, "Abre o explorador para escolher a música")

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

        # Barra Inferior com Todos os Botões de Exportação
        export_box = ctk.CTkFrame(tab, fg_color="transparent")
        export_box.pack(fill="x", padx=10, pady=8)

        btn_save_rb3 = ctk.CTkButton(
            export_box, text="🚀 Exportar Rock Band 3 (Console & RPCS3)", width=270, height=40,
            fg_color="#10B981", hover_color="#059669", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._save_from_editor_rb3
        )
        btn_save_rb3.pack(side="left", padx=4)
        set_tooltip(btn_save_rb3, "Gera o songs.dta oficial e o arquivo MIDI pronto para carregar no Rock Band 3")

        btn_save_ps3 = ctk.CTkButton(
            export_box, text="📦 Gerar Pacote PS3 / RPCS3 (PKG + SFO)", width=280, height=40,
            fg_color="#0284C7", hover_color="#0369A1", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._save_from_editor_ps3
        )
        btn_save_ps3.pack(side="left", padx=4)
        set_tooltip(btn_save_ps3, "Gera o pacote completo com PARAM.SFO, ICON0.PNG e instalador automático de 1 clique para o RPCS3!")

        btn_save_ch = ctk.CTkButton(
            export_box, text="🎮 Exportar Clone Hero / YARG", width=250, height=40,
            fg_color="#3B82F6", hover_color="#2563EB", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._save_from_editor_ch
        )
        btn_save_ch.pack(side="left", padx=4)
        set_tooltip(btn_save_ch, "Gera a pasta completa com song.ini, notes.mid, áudio e album.png")

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
        """Disparado pelo app principal ao apertar uma casa ou pad."""
        if not self.is_recording or not self.is_playing:
            return
        elapsed_ms = int((time.time() - self.playback_start_time) * 1000)
        sel_track = self.track_combo.get()

        track_key = "guitar"
        if "Baixo" in sel_track:
            track_key = "bass"
        elif "Bateria" in sel_track:
            track_key = "drum"
        elif "Teclado" in sel_track:
            track_key = "keys"

        note = NoteEvent(time_ms=elapsed_ms, lane=lane, duration_ms=self.timeline.default_sustain_ms, difficulty=self.timeline.current_difficulty)
        self.song.add_note(track_key, note)
        self.timeline.redraw()
        self._update_note_counter()

    def _clear_current_track_notes(self):
        sel_track = self.track_combo.get()
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
