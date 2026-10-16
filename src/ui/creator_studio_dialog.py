"""
Estúdio Criador e Conversor de Músicas para Rock Band 3, Guitar Hero e Clone Hero.
Substitui completamente o fluxo fragmentado de REAPER, Magma v2, C3 CON Tools e Onyx:
- Converte músicas do Chorus Encore e RhythmVerse em 1 clique
- Grava notas ao vivo enquanto você toca no seu instrumento real com a música
- Exporta pacotes prontos para Rock Band 3 (songs.dta + mid) e Clone Hero (song.ini + notes.mid)
"""

import os
import time
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import pygame

from src.creator.chart_model import ChartSong, NoteEvent
from src.creator.chart_importer import import_song_from_folder
from src.creator.clonehero_exporter import export_clone_hero_song
from src.creator.rb3_dta_exporter import export_rb3_song_package
from src.ui.tooltip import set_tooltip

class CreatorStudioDialog(ctk.CTkToplevel):
    def __init__(self, master, audio_engine=None):
        super().__init__(master)

        self.title("🎵 Estúdio Criador de Músicas (Rock Band 3, Guitar Hero & Clone Hero)")
        self.geometry("960x680")
        self.minsize(860, 560)
        self.resizable(True, True)

        self.audio = audio_engine
        self.song = ChartSong()
        self.is_recording = False
        self.is_playing = False
        self.playback_start_time = 0.0
        self.tap_times = []

        # Mantém foco modal
        self.transient(master)
        self.after(100, self.lift)
        self.after(150, self.focus_force)

        self._build_ui()

    def _build_ui(self):
        # 1. Header do Estúdio
        header = ctk.CTkFrame(self, fg_color="#0F172A", height=60, corner_radius=0)
        header.pack(fill="x", side="top")

        h_title = ctk.CTkLabel(
            header,
            text="🎵 MidGuitar Song Creator (Rock Band 3 & Clone Hero)",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color="#38BDF8"
        )
        h_title.pack(anchor="w", padx=16, pady=(8, 2))

        h_desc = ctk.CTkLabel(
            header,
            text="Crie músicas, grave ao vivo com sua guitarra/bateria real e converta charts sem precisar do REAPER, Magma ou Onyx!",
            font=ctk.CTkFont(size=11),
            text_color="#94A3B8"
        )
        h_desc.pack(anchor="w", padx=16, pady=(0, 6))

        # 2. Abas Principais
        self.tabview = ctk.CTkTabview(self, fg_color="#1E293B", segmented_button_fg_color="#334155")
        self.tabview.pack(fill="both", expand=True, padx=14, pady=8)

        tab_converter = self.tabview.add("⚡ Conversor em 1 Clique (Chorus / CH ➔ RB3)")
        tab_recorder = self.tabview.add("🔴 Gravação ao Vivo (Toque no Instrumento)")
        tab_editor = self.tabview.add("🎛️ Metadados & Exportação Final")

        self._build_converter_tab(tab_converter)
        self._build_recorder_tab(tab_recorder)
        self._build_editor_tab(tab_editor)

    # -------------------------------------------------------------------------
    # ABA 1: CONVERSOR EM 1 CLIQUE
    # -------------------------------------------------------------------------
    def _build_converter_tab(self, tab):
        top_box = ctk.CTkFrame(tab, fg_color="#0F172A", corner_radius=8)
        top_box.pack(fill="x", padx=10, pady=8)

        lbl = ctk.CTkLabel(
            top_box,
            text="📁 Selecione a pasta de qualquer música baixada do Chorus Encore, RhythmVerse, C3 ou Clone Hero:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#E2E8F0"
        )
        lbl.pack(anchor="w", padx=12, pady=(10, 4))

        sel_row = ctk.CTkFrame(top_box, fg_color="transparent")
        sel_row.pack(fill="x", padx=12, pady=(2, 10))

        self.folder_entry = ctk.CTkEntry(sel_row, placeholder_text="Caminho da pasta da música (com notes.mid e song.ini)...")
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_browse = ctk.CTkButton(
            sel_row, text="Buscar Pasta...", width=120, height=28,
            command=self._on_browse_import_folder
        )
        btn_browse.pack(side="right")
        set_tooltip(btn_browse, "Localize uma pasta de música no seu computador")

        # Detalhes da música importada
        self.info_box = ctk.CTkFrame(tab, fg_color="#0F172A", corner_radius=8)
        self.info_box.pack(fill="both", expand=True, padx=10, pady=4)

        self.info_label = ctk.CTkLabel(
            self.info_box,
            text="Nenhuma música carregada no momento.\nSelecione uma pasta acima para ver os detalhes e converter!",
            font=ctk.CTkFont(size=12),
            text_color="#94A3B8",
            justify="center"
        )
        self.info_label.pack(expand=True, pady=20)

        # Botões de Conversão e Exportação Direta
        act_box = ctk.CTkFrame(tab, fg_color="transparent")
        act_box.pack(fill="x", padx=10, pady=8)

        btn_convert_rb3 = ctk.CTkButton(
            act_box, text="🚀 Converter para Rock Band 3 (Console & RPCS3)", width=280, height=36,
            fg_color="#10B981", hover_color="#059669", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_convert_to_rb3
        )
        btn_convert_rb3.pack(side="left", padx=4)
        set_tooltip(btn_convert_rb3, "Gera a estrutura completa de arquivos do Rock Band 3 com songs.dta e MIDI pronta para jogar!")

        btn_convert_ch = ctk.CTkButton(
            act_box, text="🎮 Exportar para Clone Hero / YARG", width=240, height=36,
            fg_color="#3B82F6", hover_color="#2563EB", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_convert_to_clone_hero
        )
        btn_convert_ch.pack(side="left", padx=4)
        set_tooltip(btn_convert_ch, "Gera pasta pronta com song.ini e notes.mid para colar na pasta Songs do Clone Hero")

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

        info_text = (
            f"🎵 Título: {self.song.title}\n"
            f"👤 Artista: {self.song.artist}  |  Álbum: {self.song.album} ({self.song.year})\n"
            f"⚡ BPM: {self.song.bpm}  |  Gênero: {self.song.genre}  |  Charter: {self.song.charter}\n"
            f"🔊 Áudio detectado: {'Sim' if self.song.audio_path else 'Não encontrado'}\n"
            f"--------------------------------------------------\n"
            f"🎸 Guitarra: {g_count} notas mapeadas\n"
            f"🎸 Baixo: {b_count} notas mapeadas\n"
            f"🥁 Bateria: {d_count} notas mapeadas\n"
            f"🎹 Teclado: {k_count} notas mapeadas\n"
            f"✨ Seções/Eventos: {len(self.song.events)} marcadores\n"
        )
        self.info_label.configure(text=info_text, justify="left", font=ctk.CTkFont(family="Consolas", size=12), text_color="#F8FAFC")

    def _on_convert_to_rb3(self):
        if not self.song.title:
            messagebox.showwarning("Aviso", "Carregue ou crie uma música primeiro!")
            return
        out_dir = filedialog.askdirectory(title="Escolha onde salvar o pacote do Rock Band 3")
        if not out_dir:
            return
        pkg_dir = export_rb3_song_package(self.song, out_dir)
        messagebox.showinfo("Sucesso!", f"Pacote Rock Band 3 gerado com sucesso em:\n{pkg_dir}\n\nVocê já pode copiar para o RPCS3 ou Xbox 360!")

    def _on_convert_to_clone_hero(self):
        if not self.song.title:
            messagebox.showwarning("Aviso", "Carregue ou crie uma música primeiro!")
            return
        out_dir = filedialog.askdirectory(title="Escolha a pasta de destino (ou sua pasta Clone Hero/Songs)")
        if not out_dir:
            return
        pkg_dir = export_clone_hero_song(self.song, out_dir)
        messagebox.showinfo("Sucesso!", f"Pasta Clone Hero gerada com sucesso em:\n{pkg_dir}")

    # -------------------------------------------------------------------------
    # ABA 2: GRAVAÇÃO AO VIVO
    # -------------------------------------------------------------------------
    def _build_recorder_tab(self, tab):
        ctrl_box = ctk.CTkFrame(tab, fg_color="#0F172A", corner_radius=8)
        ctrl_box.pack(fill="x", padx=10, pady=8)

        # Seleção de áudio
        audio_row = ctk.CTkFrame(ctrl_box, fg_color="transparent")
        audio_row.pack(fill="x", padx=10, pady=(10, 4))

        ctk.CTkLabel(audio_row, text="🎵 Arquivo de Áudio (.MP3/.WAV):", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(0, 6))
        self.audio_entry = ctk.CTkEntry(audio_row, placeholder_text="Selecione o arquivo de áudio da música...")
        self.audio_entry.pack(side="left", fill="x", expand=True, padx=4)

        btn_audio = ctk.CTkButton(audio_row, text="Carregar Áudio...", width=130, command=self._on_browse_audio)
        btn_audio.pack(side="right")

        # Configurações de BPM e Instrumento
        cfg_row = ctk.CTkFrame(ctrl_box, fg_color="transparent")
        cfg_row.pack(fill="x", padx=10, pady=(4, 10))

        ctk.CTkLabel(cfg_row, text="BPM:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(0, 4))
        self.bpm_entry = ctk.CTkEntry(cfg_row, width=70)
        self.bpm_entry.insert(0, "120.0")
        self.bpm_entry.pack(side="left", padx=4)

        btn_tap = ctk.CTkButton(cfg_row, text="🥁 Tap BPM", width=90, fg_color="#334155", command=self._on_tap_bpm)
        btn_tap.pack(side="left", padx=4)
        set_tooltip(btn_tap, "Clique repetidamente no ritmo da música para calcular o BPM automático!")

        ctk.CTkLabel(cfg_row, text="Pista a Gravar:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(14, 4))
        self.rec_track_combo = ctk.CTkComboBox(
            cfg_row, width=170, values=["🎸 Guitarra (5 Casas)", "🎸 Baixo", "🥁 Bateria", "🎹 Teclado"]
        )
        self.rec_track_combo.pack(side="left", padx=4)
        self.rec_track_combo.set("🎸 Guitarra (5 Casas)")

        # Painel Central de Gravação
        rec_center = ctk.CTkFrame(tab, fg_color="#0F172A", corner_radius=8)
        rec_center.pack(fill="both", expand=True, padx=10, pady=4)

        self.rec_status_lbl = ctk.CTkLabel(
            rec_center,
            text="🔴 GRAVAÇÃO AO VIVO\n\nConecte sua guitarra, bateria ou teclado USB/MIDI,\nclique em 'INICIAR GRAVAÇÃO AO VIVO' e toque junto com a música!\nO app captura seu ritmo e cria as notas automaticamente.",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#38BDF8",
            justify="center"
        )
        self.rec_status_lbl.pack(expand=True, pady=20)

        # Botões de Controle de Reprodução/Gravação
        bottom_ctrls = ctk.CTkFrame(tab, fg_color="transparent")
        bottom_ctrls.pack(fill="x", padx=10, pady=8)

        self.btn_rec_toggle = ctk.CTkButton(
            bottom_ctrls, text="🔴 INICIAR GRAVAÇÃO AO VIVO", width=250, height=36,
            fg_color="#DC2626", hover_color="#B91C1C", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._toggle_recording
        )
        self.btn_rec_toggle.pack(side="left", padx=4)

        self.btn_play_toggle = ctk.CTkButton(
            bottom_ctrls, text="▶️ Ouvir Música", width=140, height=36,
            fg_color="#3B82F6", hover_color="#2563EB", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._toggle_playback
        )
        self.btn_play_toggle.pack(side="left", padx=4)

        btn_clear = ctk.CTkButton(
            bottom_ctrls, text="🗑️ Limpar Notas da Pista", width=170, height=36,
            fg_color="#475569", hover_color="#334155", font=ctk.CTkFont(size=11),
            command=self._clear_current_track_notes
        )
        btn_clear.pack(side="right", padx=4)

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

    def _toggle_playback(self):
        if self.is_playing:
            pygame.mixer.music.stop()
            self.is_playing = False
            self.btn_play_toggle.configure(text="▶️ Ouvir Música", fg_color="#3B82F6")
        else:
            path = self.audio_entry.get().strip()
            if path and os.path.exists(path):
                try:
                    pygame.mixer.music.load(path)
                    pygame.mixer.music.play()
                    self.is_playing = True
                    self.playback_start_time = time.time()
                    self.btn_play_toggle.configure(text="⏹️ Parar Reprodução", fg_color="#DC2626")
                except Exception as e:
                    messagebox.showerror("Erro", f"Erro ao tocar áudio: {e}")
            else:
                messagebox.showwarning("Aviso", "Selecione um arquivo de áudio válido primeiro!")

    def _toggle_recording(self):
        if self.is_recording:
            # Para gravação
            self.is_recording = False
            if self.is_playing:
                self._toggle_playback()
            self.btn_rec_toggle.configure(text="🔴 INICIAR GRAVAÇÃO AO VIVO", fg_color="#DC2626")
            self.rec_status_lbl.configure(
                text=f"✅ Gravação Concluída!\n\nNotas salvas na trilha.\nAcesse a aba 'Metadados & Exportação' para gerar o arquivo do Rock Band ou Clone Hero!",
                text_color="#10B981"
            )
        else:
            # Inicia gravação
            path = self.audio_entry.get().strip()
            if not path or not os.path.exists(path):
                messagebox.showwarning("Aviso", "Carregue um arquivo de áudio para acompanhar o ritmo!")
                return

            try:
                self.song.bpm = float(self.bpm_entry.get())
            except Exception:
                self.song.bpm = 120.0

            self.is_recording = True
            self.btn_rec_toggle.configure(text="⏹️ PARAR GRAVAÇÃO", fg_color="#10B981")
            self.rec_status_lbl.configure(
                text="🔴 GRAVANDO AO VIVO!\n\nToque no seu instrumento agora!\nCada nota tocada está sendo mapeada na linha do tempo.",
                text_color="#EF4444"
            )
            if not self.is_playing:
                self._toggle_playback()

    def record_incoming_note(self, lane: str):
        """Chamado pelo app principal quando o usuário aperta uma casa da guitarra ou pad enquanto grava."""
        if not self.is_recording or not self.is_playing:
            return
        elapsed_ms = int((time.time() - self.playback_start_time) * 1000)
        sel_track = self.rec_track_combo.get()

        track_key = "guitar"
        if "Baixo" in sel_track:
            track_key = "bass"
        elif "Bateria" in sel_track:
            track_key = "drum"
        elif "Teclado" in sel_track:
            track_key = "keys"

        note = NoteEvent(time_ms=elapsed_ms, lane=lane, duration_ms=160, difficulty="Expert")
        self.song.add_note(track_key, note)

    def _clear_current_track_notes(self):
        sel_track = self.rec_track_combo.get()
        track_key = "guitar"
        if "Baixo" in sel_track:
            track_key = "bass"
        elif "Bateria" in sel_track:
            track_key = "drum"
        elif "Teclado" in sel_track:
            track_key = "keys"
        self.song.clear_track(track_key)
        messagebox.showinfo("Limpo", f"Notas da trilha {sel_track} foram limpas.")

    # -------------------------------------------------------------------------
    # ABA 3: METADADOS & EXPORTAÇÃO
    # -------------------------------------------------------------------------
    def _build_editor_tab(self, tab):
        form_frame = ctk.CTkFrame(tab, fg_color="#0F172A", corner_radius=8)
        form_frame.pack(fill="both", expand=True, padx=10, pady=8)

        # Grid de campos
        row = 0
        def add_field(label_text, default_val):
            nonlocal row
            ctk.CTkLabel(form_frame, text=label_text, font=ctk.CTkFont(size=11, weight="bold")).grid(row=row, column=0, padx=14, pady=6, sticky="w")
            entry = ctk.CTkEntry(form_frame, width=320)
            entry.insert(0, str(default_val))
            entry.grid(row=row, column=1, padx=14, pady=6, sticky="w")
            row += 1
            return entry

        self.f_title = add_field("Título da Música:", self.song.title)
        self.f_artist = add_field("Artista / Banda:", self.song.artist)
        self.f_album = add_field("Nome do Álbum:", self.song.album)
        self.f_year = add_field("Ano de Lançamento:", self.song.year)
        self.f_genre = add_field("Gênero Musical:", self.song.genre)
        self.f_charter = add_field("Autor do Chart (Charter):", self.song.charter)

        # Botões finais de exportação
        export_box = ctk.CTkFrame(tab, fg_color="transparent")
        export_box.pack(fill="x", padx=10, pady=8)

        btn_save_rb3 = ctk.CTkButton(
            export_box, text="💾 Salvar Pacote Rock Band 3 (songs.dta + mid)", width=300, height=38,
            fg_color="#10B981", hover_color="#059669", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._save_from_editor_rb3
        )
        btn_save_rb3.pack(side="left", padx=4)

        btn_save_ch = ctk.CTkButton(
            export_box, text="🎮 Salvar Pasta Clone Hero / YARG", width=260, height=38,
            fg_color="#3B82F6", hover_color="#2563EB", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._save_from_editor_ch
        )
        btn_save_ch.pack(side="left", padx=4)

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

    def _save_from_editor_rb3(self):
        self._sync_fields_to_song()
        self._on_convert_to_rb3()

    def _save_from_editor_ch(self):
        self._sync_fields_to_song()
        self._on_convert_to_clone_hero()
