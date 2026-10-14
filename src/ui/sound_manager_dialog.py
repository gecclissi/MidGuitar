"""
Janela de Gerenciamento e Importação de Sons (.WAV, .MP3, .OGG) e SoundFonts.
Permite ao usuário carregar arquivos de áudio reais para qualquer peça de bateria
ou botão de guitarra, testar com 1 clique e configurar integração com SoundFonts/DAWs.
"""

import os
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from src.audio.engine import AudioEngine

class SoundManagerDialog(ctk.CTkToplevel):
    def __init__(self, master, audio_engine: AudioEngine, current_samples: dict, on_save_callback=None):
        super().__init__(master)

        self.title("🎵 Gerenciador de Sons & Amostras (.WAV / .MP3 / SoundFonts)")
        self.geometry("780x620")
        self.minsize(720, 560)
        self.resizable(True, True)

        self.audio = audio_engine
        self.samples = current_samples.copy() if current_samples else {}
        self.on_save_callback = on_save_callback

        # Mantém foco modal
        self.transient(master)
        self.after(100, self.lift)
        self.after(150, self.focus_force)

        self._build_ui()

    def _build_ui(self):
        # Header explicativo
        header = ctk.CTkFrame(self, fg_color="#0F172A", height=70, corner_radius=0)
        header.pack(fill="x", side="top")

        h_title = ctk.CTkLabel(
            header, text="🎵 Importar Outros Sons & Amostras de Áudio",
            font=ctk.CTkFont(size=18, weight="bold"), text_color="#38BDF8"
        )
        h_title.pack(anchor="w", padx=20, pady=(12, 2))

        h_desc = ctk.CTkLabel(
            header,
            text="Carregue arquivos reais (.wav, .mp3, .ogg) para bateria e guitarra, ou aprenda a plugar SoundFonts (.sf2) e DAWs.",
            font=ctk.CTkFont(size=12), text_color="#94A3B8"
        )
        h_desc.pack(anchor="w", padx=20, pady=(0, 10))

        # Abas de Configuração
        tabview = ctk.CTkTabview(self, fg_color="#1E293B", segmented_button_fg_color="#334155")
        tabview.pack(fill="both", expand=True, padx=16, pady=12)

        tab_drums = tabview.add("🥁 Bateria (.WAV / .MP3)")
        tab_guitar = tabview.add("🎸 Guitarra 5 Botões (.WAV / .MP3)")
        tab_soundfonts = tabview.add("🎹 SoundFonts (.sf2) & DAWs")

        self._build_drums_tab(tab_drums)
        self._build_guitar_tab(tab_guitar)
        self._build_soundfonts_tab(tab_soundfonts)

        # Rodapé com botões de Ação
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
    # ABA: BATERIA
    # -------------------------------------------------------------
    def _build_drums_tab(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=4, pady=4)

        info_box = ctk.CTkFrame(scroll, fg_color="#0F172A", corner_radius=8)
        info_box.pack(fill="x", padx=4, pady=(2, 10))
        ctk.CTkLabel(
            info_box,
            text="💡 Dica: Você pode colocar qualquer gravação real de bumbo, caixa, prato ou efeitos sonoros (.wav / .mp3)!\nAo bater no pad ou clicar na tela, o som importado tocará imediatamente.",
            font=ctk.CTkFont(size=12), text_color="#E2E8F0", justify="left"
        ).pack(padx=14, pady=8, anchor="w")

        drum_slots = [
            ("kick", "🔴 Bumbo (Kick)", "#9333EA"),
            ("snare", "🔴 Caixa (Snare)", "#EF4444"),
            ("hihat", "🟡 Chimbal (Hi-Hat)", "#FACC15"),
            ("tom1", "🔵 Tom 1 (High Tom)", "#3B82F6"),
            ("tom2", "🟢 Surdo (Floor Tom)", "#22C55E"),
            ("crash", "🟠 Prato de Ataque (Crash / Ride)", "#FB923C"),
        ]

        self.drum_status_labels = {}

        for key, name, color in drum_slots:
            card = ctk.CTkFrame(scroll, fg_color="#182234", corner_radius=8, border_width=1, border_color="#334155")
            card.pack(fill="x", padx=4, pady=4)

            # Lado Esquerdo: Nome do Pad
            title_lbl = ctk.CTkLabel(
                card, text=name, font=ctk.CTkFont(size=13, weight="bold"),
                text_color=color, width=190, anchor="w"
            )
            title_lbl.pack(side="left", padx=12, pady=10)

            # Centro: Status do arquivo atual
            current_path = self.samples.get(key, "")
            file_name = os.path.basename(current_path) if current_path and os.path.exists(current_path) else "Padrão (Sintetizador General MIDI)"
            status_text = f"📁 {file_name}" if current_path and os.path.exists(current_path) else "⚪ Som Padrão MIDI"
            status_color = "#34D399" if current_path and os.path.exists(current_path) else "#94A3B8"

            status_lbl = ctk.CTkLabel(
                card, text=status_text, font=ctk.CTkFont(size=11),
                text_color=status_color, anchor="w"
            )
            status_lbl.pack(side="left", fill="x", expand=True, padx=8)
            self.drum_status_labels[key] = status_lbl

            # Botão Importar Arquivo
            btn_choose = ctk.CTkButton(
                card, text="📁 Importar Áudio", width=120, height=28,
                fg_color="#3B82F6", hover_color="#2563EB", font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda k=key: self._choose_file_for_slot(k, self.drum_status_labels[k])
            )
            btn_choose.pack(side="left", padx=4, pady=8)

            # Botão Testar / Ouvir Som
            btn_test = ctk.CTkButton(
                card, text="🔊 Ouvir", width=75, height=28,
                fg_color="#059669", hover_color="#047857", font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda k=key: self._test_slot_audio(k)
            )
            btn_test.pack(side="left", padx=4, pady=8)

            # Botão Remover
            btn_clear = ctk.CTkButton(
                card, text="🗑️", width=36, height=28,
                fg_color="#DC2626", hover_color="#B91C1C",
                command=lambda k=key: self._clear_slot(k, self.drum_status_labels[k])
            )
            btn_clear.pack(side="left", padx=(4, 10), pady=8)

    # -------------------------------------------------------------
    # ABA: GUITARRA 5 BOTÕES
    # -------------------------------------------------------------
    def _build_guitar_tab(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=4, pady=4)

        info_box = ctk.CTkFrame(scroll, fg_color="#0F172A", corner_radius=8)
        info_box.pack(fill="x", padx=4, pady=(2, 10))
        ctk.CTkLabel(
            info_box,
            text="💡 Dica: Importe acordes reais gravados, riffs curtos ou sons sintetizados em .wav/.mp3 para cada botão da guitarra!",
            font=ctk.CTkFont(size=12), text_color="#E2E8F0", justify="left"
        ).pack(padx=14, pady=8, anchor="w")

        guitar_slots = [
            ("fret_green", "🟢 Botão Verde", "#22C55E"),
            ("fret_red", "🔴 Botão Vermelho", "#EF4444"),
            ("fret_yellow", "🟡 Botão Amarelo", "#EAB308"),
            ("fret_blue", "🔵 Botão Azul", "#3B82F6"),
            ("fret_orange", "🟠 Botão Laranja", "#F97316"),
        ]

        self.guitar_status_labels = {}

        for key, name, color in guitar_slots:
            card = ctk.CTkFrame(scroll, fg_color="#182234", corner_radius=8, border_width=1, border_color="#334155")
            card.pack(fill="x", padx=4, pady=4)

            title_lbl = ctk.CTkLabel(
                card, text=name, font=ctk.CTkFont(size=13, weight="bold"),
                text_color=color, width=170, anchor="w"
            )
            title_lbl.pack(side="left", padx=12, pady=10)

            current_path = self.samples.get(key, "")
            file_name = os.path.basename(current_path) if current_path and os.path.exists(current_path) else "Padrão (Acorde MIDI General MIDI)"
            status_text = f"📁 {file_name}" if current_path and os.path.exists(current_path) else "⚪ Som Padrão MIDI"
            status_color = "#34D399" if current_path and os.path.exists(current_path) else "#94A3B8"

            status_lbl = ctk.CTkLabel(
                card, text=status_text, font=ctk.CTkFont(size=11),
                text_color=status_color, anchor="w"
            )
            status_lbl.pack(side="left", fill="x", expand=True, padx=8)
            self.guitar_status_labels[key] = status_lbl

            btn_choose = ctk.CTkButton(
                card, text="📁 Importar Áudio", width=120, height=28,
                fg_color="#3B82F6", hover_color="#2563EB", font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda k=key: self._choose_file_for_slot(k, self.guitar_status_labels[k])
            )
            btn_choose.pack(side="left", padx=4, pady=8)

            btn_test = ctk.CTkButton(
                card, text="🔊 Ouvir", width=75, height=28,
                fg_color="#059669", hover_color="#047857", font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda k=key: self._test_slot_audio(k)
            )
            btn_test.pack(side="left", padx=4, pady=8)

            btn_clear = ctk.CTkButton(
                card, text="🗑️", width=36, height=28,
                fg_color="#DC2626", hover_color="#B91C1C",
                command=lambda k=key: self._clear_slot(k, self.guitar_status_labels[k])
            )
            btn_clear.pack(side="left", padx=(4, 10), pady=8)

    # -------------------------------------------------------------
    # ABA: SOUNDFONTS (.sf2) & DAWs
    # -------------------------------------------------------------
    def _build_soundfonts_tab(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=6, pady=6)

        title = ctk.CTkLabel(
            scroll, text="🎹 Como usar SoundFonts (.sf2) e VSTs Profissionais no Windows",
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#38BDF8"
        )
        title.pack(anchor="w", pady=(4, 10))

        content_1 = (
            "Se você quer usar bancos de instrumentos inteiros em formato SoundFont (.sf2 / .sf3) com realismo total:\n\n"
            "1️⃣ MÉTODO DIRETO COM SOUNDFONTS (VirtualMIDISynth):\n"
            "• Baixe e instale o software gratuito 'VirtualMIDISynth' (de Claudio Nicora).\n"
            "• Nele você pode carregar qualquer SoundFont gigante da internet (ex: FluidR3_GM, GeneralUser GS, Arachno, SGM-V2.01).\n"
            "• O VirtualMIDISynth cria uma saída de áudio MIDI no Windows.\n"
            "• No MidGuitar, basta escolher 'VirtualMIDISynth' na caixa de 'Saída de Áudio'. Pronto! Todos os seus instrumentos tocarão o SoundFont sem delay!"
        )
        box1 = ctk.CTkFrame(scroll, fg_color="#182234", corner_radius=8)
        box1.pack(fill="x", pady=6)
        ctk.CTkLabel(box1, text=content_1, font=ctk.CTkFont(size=12), text_color="#E2E8F0", justify="left").pack(padx=16, pady=12, anchor="w")

        content_2 = (
            "2️⃣ MÉTODO PARA DAWS E VSTs (Kontakt, Superior Drummer, Amplitube, Guitar Rig, FL Studio):\n"
            "• Instale o 'loopMIDI' (cria cabos virtuais de MIDI).\n"
            "• No MidGuitar, escolha a porta de saída como 'loopMIDI Port'.\n"
            "• No seu DAW (Reaper, FL Studio, Ableton, Cubase), configure a entrada MIDI como 'loopMIDI Port'.\n"
            "• Abra o seu plugin favorito (Superior Drummer para bateria, Amplitube para guitarra, Kontakt para pianos).\n"
            "• Você terá a qualidade de áudio de estúdio mais avançada do mundo tocando com sua guitarra ou bateria de videogame!"
        )
        box2 = ctk.CTkFrame(scroll, fg_color="#182234", corner_radius=8)
        box2.pack(fill="x", pady=6)
        ctk.CTkLabel(box2, text=content_2, font=ctk.CTkFont(size=12), text_color="#E2E8F0", justify="left").pack(padx=16, pady=12, anchor="w")

    # -------------------------------------------------------------
    # OPERAÇÕES DE ARQUIVOS E TESTE
    # -------------------------------------------------------------
    def _choose_file_for_slot(self, slot_key: str, status_lbl: ctk.CTkLabel):
        """Abre janela para selecionar arquivo de áudio."""
        file_path = filedialog.askopenfilename(
            title="Escolha um arquivo de áudio para este botão/pad",
            filetypes=[
                ("Arquivos de Áudio (*.wav;*.mp3;*.ogg)", "*.wav;*.mp3;*.ogg"),
                ("WAV Files (*.wav)", "*.wav"),
                ("MP3 Files (*.mp3)", "*.mp3"),
                ("OGG Files (*.ogg)", "*.ogg"),
                ("Todos os Arquivos (*.*)", "*.*")
            ]
        )
        if file_path and os.path.exists(file_path):
            success = self.audio.load_sample(slot_key, file_path)
            if success:
                self.samples[slot_key] = file_path
                file_name = os.path.basename(file_path)
                status_lbl.configure(text=f"📁 {file_name}", text_color="#34D399")
                # Toca imediatamente para dar feedback sonoro ao usuário
                self.audio.play_sample(slot_key, velocity=120)

    def _test_slot_audio(self, slot_key: str):
        """Toca o som do slot: sample se configurado, ou MIDI padrão se não."""
        if slot_key in self.samples and os.path.exists(self.samples[slot_key]):
            self.audio.play_sample(slot_key, velocity=120)
        else:
            # Toca nota MIDI representativa padrão
            if slot_key == "kick":
                self.audio.play_note(36, velocity=120, channel=9)
            elif slot_key == "snare":
                self.audio.play_note(38, velocity=120, channel=9)
            elif slot_key == "hihat":
                self.audio.play_note(42, velocity=120, channel=9)
            elif slot_key == "tom1":
                self.audio.play_note(48, velocity=120, channel=9)
            elif slot_key == "tom2":
                self.audio.play_note(41, velocity=120, channel=9)
            elif slot_key == "crash":
                self.audio.play_note(49, velocity=120, channel=9)
            elif slot_key == "fret_green":
                self.audio.play_chord([40, 47, 52], velocity=115)
            elif slot_key == "fret_red":
                self.audio.play_chord([45, 52, 57], velocity=115)
            elif slot_key == "fret_yellow":
                self.audio.play_chord([50, 57, 62], velocity=115)
            elif slot_key == "fret_blue":
                self.audio.play_chord([55, 62, 67], velocity=115)
            elif slot_key == "fret_orange":
                self.audio.play_chord([59, 66, 71], velocity=115)

    def _clear_slot(self, slot_key: str, status_lbl: ctk.CTkLabel):
        """Restaura o slot para o som MIDI padrão."""
        if slot_key in self.samples:
            del self.samples[slot_key]
        self.audio.remove_sample(slot_key)
        status_lbl.configure(text="⚪ Som Padrão MIDI", text_color="#94A3B8")

    def _save_and_close(self):
        """Salva as configurações de samples e fecha a janela."""
        if self.on_save_callback:
            self.on_save_callback(self.samples)
        self.destroy()
