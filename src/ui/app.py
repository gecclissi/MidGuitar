"""
Janela Principal da aplicação MidGuitar em CustomTkinter.
Estúdio Universal para:
- Guitarra Pro Rock Band 3 (Mustang Pro / Squier Stratocaster - 6 cordas)
- Guitarra Rock Band / Guitar Hero (5 botões + palheta + alavanca)
- Teclado Rock Band 3 Wireless Keyboard (25 teclas + touch ribbon)
- Baterias Band Hero / Guitar Hero / Rock Band Drums (Canal 10)
"""

import customtkinter as ctk
import tkinter as tk
import time
import os
import json
from src.ui.fretboard_view import FretboardView
from src.ui.pro_fretboard_view import ProFretboardView
from src.ui.keyboard_view import KeyboardView
from src.ui.drum_view import DrumView
from src.ui.monitor_view import MonitorView
from src.ui.mapping_dialog import MappingDialog
from src.ui.sound_manager_dialog import SoundManagerDialog
from src.ui.batch_key_mapper_dialog import BatchKeyMapperDialog
from src.ui.sound_browser_dialog import SoundBrowserDialog
from src.midi.detector import (
    get_midi_input_ports, get_midi_output_ports, get_gamepad_devices,
    find_rockband_midi_input, find_default_midi_output
)
from src.midi.instrument_types import InstrumentMode
from src.midi.mapper import GuitarMapper
from src.midi.reader import MIDIReader
from src.audio.engine import AudioEngine
from src.utils.config_manager import (
    load_config, save_config, list_presets, load_preset, get_asset_path, get_presets_dirs
)
from src.utils.instruments import GM_INSTRUMENTS, INSTRUMENT_NAMES, midi_note_to_name

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class MidGuitarApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("MidGuitar - Universal Rock Band & MIDI Studio")
        self.geometry("1100x740")
        self.minsize(860, 560)

        # Configura ícone da janela
        try:
            icon_file = get_asset_path("assets/icon.ico")
            if icon_file:
                self.iconbitmap(icon_file)
        except Exception:
            pass

        # Carrega configurações e presets
        self.config = load_config()
        self.preset_list = list_presets()
        self.current_preset_id = self.config.get("current_preset", "rock_power_chords")
        self.preset_data = load_preset(self.current_preset_id)

        # Modo de instrumento inicial
        self.current_instrument_mode = InstrumentMode.AUTO

        # Inicializa o mapeador
        self.mapper = GuitarMapper(
            preset=self.preset_data,
            octave_shift=self.config.get("octave_shift", 0)
        )

        # Inicializa o motor de áudio com as amostras e regras de teclas salvas
        self.audio = AudioEngine(
            midi_out_port_name=self.config.get("midi_out_port"),
            instrument_id=self.config.get("instrument_id", 29),
            volume=self.config.get("volume", 85),
            initial_samples=self.config.get("custom_samples", {}),
            key_sound_map=self.config.get("key_sound_map", {})
        )

        # Inicializa o leitor MIDI universal
        self.reader = MIDIReader(
            mapper=self.mapper,
            on_event_callback=self._on_midi_event,
            on_audio_play=self._on_audio_play,
            on_audio_stop=self._on_audio_stop,
            on_whammy=self._on_whammy,
            on_pro_guitar_event=self._on_pro_guitar_event,
            on_keyboard_event=self._on_keyboard_event,
            on_drum_event=self._on_drum_event,
            on_mode_detected=self._on_mode_detected
        )

        # Constrói a interface
        self._build_ui()

        # Atualiza a lista de dispositivos
        self.refresh_devices()

        # Conexão automática se habilitada
        if self.config.get("auto_connect", True):
            self.auto_connect()

        # Intercepta fechamento da janela
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        from src.ui.tooltip import set_tooltip

        # -------------------------------------------------------------
        # 1. HEADER LIMPO E ELEGANTE
        # -------------------------------------------------------------
        header = ctk.CTkFrame(self, fg_color="#0F172A", height=50, corner_radius=0)
        header.pack(fill="x", side="top")

        # Título
        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left", padx=16, pady=8)

        title_label = ctk.CTkLabel(
            title_box, text="🎸 MidGuitar", font=ctk.CTkFont(size=18, weight="bold"), text_color="#38BDF8"
        )
        title_label.pack(side="left")
        set_tooltip(title_label, "MidGuitar Studio - Plugue seus instrumentos ou toque clicando na tela!")

        # Badge de Status Centralizado
        self.status_badge = ctk.CTkLabel(
            header, text="🟡 Modo Clique para Tocar", font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#F59E0B", fg_color="#1E293B", corner_radius=12, padx=14, pady=4
        )
        self.status_badge.pack(side="left", padx=20, pady=10)
        set_tooltip(self.status_badge, "Indica se seu instrumento físico está conectado ou se você está no modo virtual (mouse)")

        # Controles Rápidos no Header (Direita): Panic e Volume
        hdr_right = ctk.CTkFrame(header, fg_color="transparent")
        hdr_right.pack(side="right", padx=14, pady=8)

        # Botão Pânico
        btn_panic = ctk.CTkButton(
            hdr_right, text="⏹️ Parar Sons", width=105, height=26,
            fg_color="#DC2626", hover_color="#B91C1C", font=ctk.CTkFont(size=11, weight="bold"),
            command=self.panic_stop
        )
        btn_panic.pack(side="right", padx=(8, 0))
        set_tooltip(btn_panic, "Para imediatamente todas as notas que estiverem soando no momento")

        self.volume_label = ctk.CTkLabel(hdr_right, text=f"{self.config.get('volume', 85)}%", width=35, font=ctk.CTkFont(size=11, weight="bold"))
        self.volume_label.pack(side="right", padx=2)

        self.volume_slider = ctk.CTkSlider(
            hdr_right, from_=0, to=100, number_of_steps=100, width=110, height=16,
            command=self._on_volume_changed
        )
        self.volume_slider.set(self.config.get("volume", 85))
        self.volume_slider.pack(side="right", padx=4)
        set_tooltip(self.volume_slider, "Volume geral de saída de áudio (0 a 100%)")

        ctk.CTkLabel(hdr_right, text="🔊", font=ctk.CTkFont(size=12)).pack(side="right")

        # -------------------------------------------------------------
        # 2. BARRA DE CONEXÃO E SELEÇÃO DE INSTRUMENTO (RESPONSIVA)
        # -------------------------------------------------------------
        toolbar = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=8)
        toolbar.pack(fill="x", padx=14, pady=(6, 4))

        # Linha 1 do Toolbar: Conexões USB/MIDI e Monitor
        tb_top = ctk.CTkFrame(toolbar, fg_color="transparent")
        tb_top.pack(fill="x", padx=8, pady=(4, 2))

        ctk.CTkLabel(tb_top, text="🔌 Entrada:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(4, 4))
        self.input_combo = ctk.CTkComboBox(tb_top, width=190, height=26, values=["Nenhum dispositivo"])
        self.input_combo.pack(side="left", padx=2)
        set_tooltip(self.input_combo, "Escolha sua guitarra, bateria ou teclado USB/MIDI conectado")

        btn_refresh = ctk.CTkButton(
            tb_top, text="🔄", width=32, height=26,
            fg_color="#334155", hover_color="#475569", font=ctk.CTkFont(weight="bold"),
            command=self.refresh_devices
        )
        btn_refresh.pack(side="left", padx=2)
        set_tooltip(btn_refresh, "Detectar novamente instrumentos conectados ao PC")

        self.btn_connect = ctk.CTkButton(
            tb_top, text="Conectar", width=75, height=26,
            fg_color="#10B981", hover_color="#059669", font=ctk.CTkFont(size=11, weight="bold"),
            command=self.toggle_connection
        )
        self.btn_connect.pack(side="left", padx=(2, 10))
        set_tooltip(self.btn_connect, "Conecta ou desconecta o instrumento selecionado")

        ctk.CTkLabel(tb_top, text="🔊 Saída:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(4, 4))
        self.output_combo = ctk.CTkComboBox(
            tb_top, width=175, height=26, values=["Synth Nativo Windows (GS Wavetable)"],
            command=self._on_output_selected
        )
        self.output_combo.pack(side="left", padx=2)
        set_tooltip(self.output_combo, "Sintetizador nativo do Windows ou cabo virtual para seu DAW")

        # Botão para Ocultar/Exibir o Monitor (Garante espaço total para a tela)
        self.btn_toggle_monitor = ctk.CTkButton(
            tb_top, text="📡 Monitor [ON]", width=95, height=26,
            fg_color="#0EA5E9", hover_color="#0284C7", font=ctk.CTkFont(size=11, weight="bold"),
            command=self.toggle_monitor
        )
        self.btn_toggle_monitor.pack(side="right", padx=4)
        set_tooltip(self.btn_toggle_monitor, "Ocultar ou exibir o monitor MIDI lateral para dar mais espaço ao instrumento")

        # Linha 2 do Toolbar: Modos de Instrumento
        tb_bottom = ctk.CTkFrame(toolbar, fg_color="transparent")
        tb_bottom.pack(fill="x", padx=8, pady=(2, 4))

        ctk.CTkLabel(tb_bottom, text="🎮 Instrumento:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94A3B8").pack(side="left", padx=(4, 6))
        self.mode_selector = ctk.CTkSegmentedButton(
            tb_bottom,
            values=[
                "🎸 5 Botões",
                "🎸 Pro (6 Cordas)",
                "🥁 Bateria",
                "🎹 Teclado",
                "⚡ Auto"
            ],
            command=self._on_mode_button_clicked
        )
        self.mode_selector.pack(side="left", padx=2)
        self.mode_selector.set("🎸 5 Botões")
        set_tooltip(self.mode_selector, "Alterne qual instrumento você quer visualizar e tocar na tela")

        # -------------------------------------------------------------
        # 3. PALCO CENTRAL (O INSTRUMENTO EM DESTAQUE)
        # -------------------------------------------------------------
        main_split = ctk.CTkFrame(self, fg_color="transparent")
        main_split.pack(fill="both", expand=True, padx=14, pady=4)

        # Container esquerdo do instrumento
        self.instrument_container = ctk.CTkFrame(main_split, fg_color="#1E293B", corner_radius=10)
        self.instrument_container.pack(side="left", fill="both", expand=True, padx=(0, 6))

        # Cria as 4 visões com suporte completo aos novos seletores e banco de sons
        self.classic_fretboard = FretboardView(
            self.instrument_container, fg_color="transparent",
            on_fret_click=self._on_classic_fret_clicked,
            on_open_mapping=self.open_mapping_editor,
            on_open_sound_manager=self.open_sound_manager,
            on_quick_preset=self._on_quick_fret_preset_selected,
            on_instrument_change=self._on_quick_instrument_selected,
            on_open_sound_browser=self.open_sound_browser
        )
        self.pro_fretboard = ProFretboardView(
            self.instrument_container, fg_color="transparent",
            on_fret_click=self._on_pro_fretboard_clicked
        )
        self.keyboard_view = KeyboardView(
            self.instrument_container, fg_color="transparent",
            on_key_click=self._on_keyboard_key_clicked,
            on_open_key_mapper=self.open_batch_key_mapper
        )
        self.drum_view = DrumView(
            self.instrument_container, fg_color="transparent",
            on_pad_click=self._on_drum_pad_clicked,
            on_open_mapping=self.open_mapping_editor,
            on_open_sound_manager=self.open_sound_manager
        )

        # Exibe inicialmente a Guitarra Clássica de 5 botões (a mais intuitiva para começar)
        self.active_visual_view = self.classic_fretboard
        self.classic_fretboard.pack(fill="both", expand=True, padx=6, pady=6)
        self.classic_fretboard.update_fret_labels_from_preset(self.preset_data)

        # Monitor de Eventos MIDI (Direita) - Largura compacta de 240px
        self.monitor = MonitorView(main_split, fg_color="#1E293B", corner_radius=10, width=240)
        self.monitor.pack(side="right", fill="both", padx=(6, 0))

        # -------------------------------------------------------------
        # 4. BARRA INFERIOR (COMPACTA E RESPONSIVA)
        # -------------------------------------------------------------
        bottom_bar = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=8)
        bottom_bar.pack(fill="x", padx=14, pady=(4, 8))

        # Oitava
        ctk.CTkLabel(bottom_bar, text="Oitava:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(10, 4), pady=6)
        self.octave_seg = ctk.CTkSegmentedButton(
            bottom_bar, values=["-2", "-1", "0", "+1", "+2"], width=130, command=self._on_octave_changed
        )
        self.octave_seg.pack(side="left", padx=2, pady=6)
        self.octave_seg.set(str(self.config.get("octave_shift", 0)))
        set_tooltip(self.octave_seg, "Altera a afinação de todas as notas em oitavas (mais grave ou mais aguda)")

        # Botão Explorador de Sons Espaciais (Em destaque!)
        btn_sound_browser = ctk.CTkButton(
            bottom_bar, text="🌌 Sons Espaciais & Banco (128)", width=190, height=28,
            fg_color="#0284C7", hover_color="#0369A1", font=ctk.CTkFont(size=11, weight="bold"),
            command=self.open_sound_browser
        )
        btn_sound_browser.pack(side="left", padx=(12, 4), pady=6)
        set_tooltip(btn_sound_browser, "Abre o Explorador com todos os 128 instrumentos MIDI, efeitos sci-fi, espaciais, pads e sintetizadores!")

        # Botões de Ações Rápidas (Direita)
        btn_batch_keys = ctk.CTkButton(
            bottom_bar, text="⚡ Sons por Tecla", width=125, height=28,
            fg_color="#6366F1", hover_color="#4F46E5", font=ctk.CTkFont(size=11, weight="bold"),
            command=self.open_batch_key_mapper
        )
        btn_batch_keys.pack(side="right", padx=(4, 10), pady=6)
        set_tooltip(btn_batch_keys, "Defina o som de cada tecla individualmente ou configure em lote!")

        btn_sound_mgr = ctk.CTkButton(
            bottom_bar, text="📁 Áudios (.WAV)", width=120, height=28,
            fg_color="#8B5CF6", hover_color="#7C3AED", font=ctk.CTkFont(size=11, weight="bold"),
            command=self.open_sound_manager
        )
        btn_sound_mgr.pack(side="right", padx=4, pady=6)
        set_tooltip(btn_sound_mgr, "Importe arquivos de áudio reais (.wav / .mp3) para qualquer botão ou prato")

        btn_open_map = ctk.CTkButton(
            bottom_bar, text="🎛️ Mapear Casas", width=115, height=28,
            fg_color="#3B82F6", hover_color="#2563EB", font=ctk.CTkFont(size=11, weight="bold"),
            command=self.open_mapping_editor
        )
        btn_open_map.pack(side="right", padx=4, pady=6)
        set_tooltip(btn_open_map, "Editor avançado para escolher notas e acordes individualmente")

    # -------------------------------------------------------------
    # CLIQUE DIRETO NAS NOTAS (PREVIEW & TESTE DE ÁUDIO)
    # -------------------------------------------------------------
    def _on_classic_fret_clicked(self, fret_name: str):
        """Disparado quando o usuário clica em uma das 5 casas da guitarra."""
        # Se houver arquivo customizado (.wav/.mp3) importado para este botão
        sample_key = f"fret_{fret_name}"
        if self.audio.get_sample_path(sample_key):
            self.monitor.log(time.strftime("%H:%M:%S"), "SAMPLE", f"Clique Botão {fret_name.upper()} ➔ Áudio Customizado (.wav/.mp3)")
            self.audio.play_sample(sample_key, velocity=120)
            return

        frets = self.preset_data.get("frets", {})
        fret_cfg = frets.get(fret_name, {})
        base_notes = fret_cfg.get("notes", [52])
        shift = self.mapper.octave_shift * 12
        notes = [max(0, min(127, n + shift)) for n in base_notes]
        note_names = [midi_note_to_name(n) for n in notes]

        self.monitor.log(time.strftime("%H:%M:%S"), "TESTE", f"Clique Casa {fret_name.upper()} ➔ {' + '.join(note_names)} ({notes})")
        self.audio.play_chord(notes, velocity=115)
        self.after(450, lambda: self.audio.stop_chord(notes))

    def _on_drum_pad_clicked(self, pad_id: str, note: int):
        """Disparado quando o usuário clica em um dos pads de bateria."""
        if self.audio.get_sample_path(pad_id):
            self.monitor.log(time.strftime("%H:%M:%S"), "SAMPLE", f"Clique Pad {pad_id.upper()} ➔ Áudio Customizado (.wav/.mp3)")
            self.audio.play_sample(pad_id, velocity=120)
            # Envia também MIDI para portas externas se houver DAW conectada
            if self.audio.rtmidi_out and self.audio.rtmidi_out.is_port_open():
                try:
                    self.audio.rtmidi_out.send_message([0x99, note, 120])
                except Exception:
                    pass
            return

        self.monitor.log(time.strftime("%H:%M:%S"), "TESTE", f"Clique Pad {pad_id.upper()} ➔ Nota {note} (Canal 10)")
        self.audio.play_note(note, velocity=120, channel=9)
        self.after(200, lambda: self.audio.stop_note(note, channel=9))

    def _on_keyboard_key_clicked(self, note: int):
        """Disparado quando o usuário clica em uma tecla do teclado."""
        note_name = midi_note_to_name(note)
        rule = self.audio.get_key_rule(note)
        if rule and isinstance(rule, dict):
            rtype = rule.get("type")
            if rtype == "sample":
                fname = os.path.basename(rule.get("path", ""))
                self.monitor.log(time.strftime("%H:%M:%S"), "SAMPLE", f"Tecla {note_name} ➔ Áudio Customizado: {fname}")
            elif rtype == "instrument":
                self.monitor.log(time.strftime("%H:%M:%S"), "TIMBRE", f"Tecla {note_name} ➔ Timbre GM {rule.get('id')}")
            elif rtype == "drum":
                self.monitor.log(time.strftime("%H:%M:%S"), "DRUM", f"Tecla {note_name} ➔ Percussão GM {rule.get('drum_note')}")
        else:
            self.monitor.log(time.strftime("%H:%M:%S"), "TESTE", f"Clique Tecla {note_name} (Nota {note})")

        self.audio.play_note(note, velocity=110, channel=0)
        self.after(400, lambda: self.audio.stop_note(note, channel=0))

    def _on_pro_fretboard_clicked(self, string_num: int, fret: int, note: int):
        """Disparado quando o usuário clica em uma corda/traste da Guitarra Pro."""
        note_name = midi_note_to_name(note)
        self.monitor.log(time.strftime("%H:%M:%S"), "TESTE", f"Clique Corda {string_num} Casa {fret} ➔ {note_name} (Nota {note})")
        self.audio.play_note(note, velocity=110, channel=0)
        self.after(400, lambda: self.audio.stop_note(note, channel=0))

    # -------------------------------------------------------------
    # EXPLORADOR DE SONS ESPACIAIS E GERAIS (128 SONS GM)
    # -------------------------------------------------------------
    def open_sound_browser(self):
        """Abre o Explorador de Sons com todos os 128 instrumentos e efeitos espaciais/sci-fi."""
        SoundBrowserDialog(
            self,
            current_instrument_id=self.config.get("instrument_id", 29),
            on_select_instrument=self._on_browser_instrument_selected,
            audio_engine=self.audio
        )

    def _on_browser_instrument_selected(self, inst_id: int):
        self._on_quick_instrument_selected(inst_id)
        self.classic_fretboard.set_selected_instrument(inst_id)

    def toggle_monitor(self):
        """Oculta ou exibe o monitor MIDI lateral para dar espaço ao instrumento."""
        if self.monitor.winfo_ismapped():
            self.monitor.pack_forget()
            self.btn_toggle_monitor.configure(text="📡 Monitor [OFF]", fg_color="#334155")
        else:
            self.monitor.pack(side="right", fill="both", padx=(6, 0))
            self.btn_toggle_monitor.configure(text="📡 Monitor [ON]", fg_color="#0EA5E9")

    # -------------------------------------------------------------
    # MAPEADOR DE TECLAS & SONS EM LOTE
    # -------------------------------------------------------------
    def open_batch_key_mapper(self):
        """Abre o mapeador avançado de teclas e sons individuais/em lote."""
        BatchKeyMapperDialog(
            self,
            audio_engine=self.audio,
            current_map=self.config.get("key_sound_map", {}),
            on_save_callback=self._on_key_sound_map_updated
        )

    def _on_key_sound_map_updated(self, updated_map: dict):
        """Salva as regras de sons por tecla e atualiza o motor de áudio."""
        self.config["key_sound_map"] = updated_map
        save_config(self.config)
        self.audio.set_key_sound_map(updated_map)
        self.monitor.log(time.strftime("%H:%M:%S"), "SISTEMA", f"Mapeamento de teclas atualizado: {len(updated_map)} regras ativas")

    # -------------------------------------------------------------
    # GERENCIAMENTO DE SONS CUSTOMIZADOS (.WAV / .MP3)
    # -------------------------------------------------------------
    def open_sound_manager(self):
        """Abre a janela de importação e gerenciamento de arquivos de áudio customizados."""
        SoundManagerDialog(
            self,
            audio_engine=self.audio,
            current_samples=self.config.get("custom_samples", {}),
            on_save_callback=self._on_samples_updated
        )

    def _on_samples_updated(self, updated_samples: dict):
        """Salva as amostras customizadas e aplica ao motor de áudio."""
        self.config["custom_samples"] = updated_samples
        save_config(self.config)
        self.monitor.log(time.strftime("%H:%M:%S"), "SISTEMA", f"Amostras salvas: {len(updated_samples)} arquivos de áudio vinculados")

    # -------------------------------------------------------------
    # EDITOR DE MAPEAMENTOS INTERATIVO
    # -------------------------------------------------------------
    def open_mapping_editor(self):
        """Abre a janela de edição de mapeamentos."""
        MappingDialog(
            self,
            current_preset=self.preset_data,
            audio_engine=self.audio,
            on_save_callback=self._on_preset_updated
        )

    def _on_preset_updated(self, updated_preset: dict):
        """Aplica e salva as novas notas e configurações definidas no editor."""
        self.preset_data = updated_preset
        self.mapper.set_preset(updated_preset)
        self.classic_fretboard.update_fret_labels_from_preset(updated_preset)

        # Atualiza notas de bateria no drum_view
        drum_mapping = updated_preset.get("drum_mapping", {})
        for pad_id, note in drum_mapping.items():
            self.drum_view.set_pad_mapping(pad_id, note)

        # Salva o arquivo de preset no disco
        preset_dir = get_presets_dirs()[0]
        filepath = os.path.join(preset_dir, f"{self.current_preset_id}.json")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(updated_preset, f, indent=2, ensure_ascii=False)
            self.monitor.log(time.strftime("%H:%M:%S"), "SALVO", f"Preset '{self.current_preset_id}' atualizado com sucesso no disco!")
        except Exception as e:
            self.monitor.log(time.strftime("%H:%M:%S"), "ERRO", f"Erro ao salvar preset: {e}")

    # -------------------------------------------------------------
    # GERENCIAMENTO DE MODO DO INSTRUMENTO
    # -------------------------------------------------------------
    def _switch_visual_view(self, new_view):
        if self.active_visual_view != new_view:
            if self.active_visual_view:
                self.active_visual_view.pack_forget()
            self.active_visual_view = new_view
            self.active_visual_view.pack(fill="both", expand=True, padx=6, pady=6)

    def _on_mode_button_clicked(self, selected_mode_str: str):
        if "Auto" in selected_mode_str:
            self.current_instrument_mode = InstrumentMode.AUTO
            self.reader.set_mode(InstrumentMode.AUTO)
        elif "Guitarra Pro" in selected_mode_str:
            self.current_instrument_mode = InstrumentMode.PRO_GUITAR
            self.reader.set_mode(InstrumentMode.PRO_GUITAR)
            self._switch_visual_view(self.pro_fretboard)
        elif "5 Botões" in selected_mode_str:
            self.current_instrument_mode = InstrumentMode.CLASSIC_GUITAR
            self.reader.set_mode(InstrumentMode.CLASSIC_GUITAR)
            self._switch_visual_view(self.classic_fretboard)
        elif "Teclado" in selected_mode_str:
            self.current_instrument_mode = InstrumentMode.KEYBOARD
            self.reader.set_mode(InstrumentMode.KEYBOARD)
            self._switch_visual_view(self.keyboard_view)
        elif "Bateria" in selected_mode_str:
            self.current_instrument_mode = InstrumentMode.DRUMS
            self.reader.set_mode(InstrumentMode.DRUMS)
            self._switch_visual_view(self.drum_view)

    def _on_mode_detected(self, detected_mode: InstrumentMode):
        self.after(0, self._apply_detected_mode, detected_mode)

    def _apply_detected_mode(self, detected_mode: InstrumentMode):
        if self.current_instrument_mode != InstrumentMode.AUTO:
            return

        if detected_mode == InstrumentMode.DRUMS:
            self._switch_visual_view(self.drum_view)
        elif detected_mode == InstrumentMode.KEYBOARD:
            self._switch_visual_view(self.keyboard_view)
        elif detected_mode == InstrumentMode.PRO_GUITAR:
            self._switch_visual_view(self.pro_fretboard)
        elif detected_mode == InstrumentMode.CLASSIC_GUITAR:
            self._switch_visual_view(self.classic_fretboard)

    # -------------------------------------------------------------
    # GERENCIAMENTO DE CONEXÃO & DISPOSITIVOS
    # -------------------------------------------------------------
    def refresh_devices(self):
        midi_in_ports = get_midi_input_ports()
        gamepads = get_gamepad_devices()

        input_options = []
        for p in midi_in_ports:
            input_options.append(f"[MIDI] {p}")
        for idx, gname in gamepads:
            input_options.append(f"[USB] {gname} (#{idx})")

        if not input_options:
            input_options = ["Nenhum dispositivo encontrado"]

        self.input_combo.configure(values=input_options)
        
        auto_rb = find_rockband_midi_input()
        if auto_rb:
            target_str = f"[MIDI] {auto_rb[1]}"
            if target_str in input_options:
                self.input_combo.set(target_str)
        elif input_options:
            self.input_combo.set(input_options[0])

        midi_out_ports = get_midi_output_ports()
        output_options = ["Synth Nativo Windows (GS Wavetable)"]
        for p in midi_out_ports:
            output_options.append(f"[MIDI OUT] {p}")
        self.output_combo.configure(values=output_options)

    def auto_connect(self):
        auto_rb = find_rockband_midi_input()
        if auto_rb:
            port_idx, port_name = auto_rb
            self._connect_midi(port_idx, port_name)

    def toggle_connection(self):
        if self.reader.is_running:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        selected = self.input_combo.get()
        if not selected or "Nenhum dispositivo" in selected:
            self.monitor.log(time.strftime("%H:%M:%S"), "AVISO", "Nenhum dispositivo selecionado para conectar.")
            return

        if selected.startswith("[MIDI]"):
            port_name = selected[7:]
            midi_in_ports = get_midi_input_ports()
            for idx, p in enumerate(midi_in_ports):
                if p == port_name:
                    self._connect_midi(idx, port_name)
                    return
        elif selected.startswith("[USB]"):
            try:
                idx_str = selected.split("(#")[-1].replace(")", "")
                idx = int(idx_str)
                self.reader.start_gamepad_listener(idx)
                self._update_connection_status(True, selected)
            except Exception as e:
                self.monitor.log(time.strftime("%H:%M:%S"), "ERRO", f"Falha ao iniciar controle USB: {e}")

    def _connect_midi(self, port_idx: int, port_name: str):
        success = self.reader.connect_midi(port_idx, port_name)
        if success:
            self._update_connection_status(True, port_name)
        else:
            self._update_connection_status(False)

    def disconnect(self):
        self.reader.disconnect_midi()
        self.reader.stop_gamepad_listener()
        self.panic_stop()
        self._update_connection_status(False)

    def _update_connection_status(self, is_connected: bool, device_name: str = ""):
        if is_connected:
            self.status_badge.configure(text=f"🟢 Conectado: {device_name[:22]}", text_color="#22C55E")
            self.btn_connect.configure(text="Desconectar", fg_color="#DC2626", hover_color="#B91C1C")
        else:
            self.status_badge.configure(text="🟡 Modo Virtual (Clique para Testar)", text_color="#F59E0B")
            self.btn_connect.configure(text="🔌 Conectar", fg_color="#10B981", hover_color="#059669")

    # -------------------------------------------------------------
    # CALLBACKS DE EVENTOS MIDI E ÁUDIO
    # -------------------------------------------------------------
    def _on_midi_event(self, timestamp: str, event_type: str, details: str):
        self.after(0, self.monitor.log, timestamp, event_type, details)

    def _on_pro_guitar_event(self, string_num: int, fret: int, is_active: bool, velocity: int):
        self.after(0, self.pro_fretboard.set_string_fret, string_num, fret, is_active, velocity)

    def _on_keyboard_event(self, note: int, is_active: bool, velocity: int):
        self.after(0, self.keyboard_view.set_key_state, note, is_active)

    def _on_drum_event(self, note: int, velocity: int):
        self.after(0, self.drum_view.trigger_pad_by_note, note, velocity)

    def _on_audio_play(self, notes: list[int], velocity: int, channel: int = 0):
        for n in notes:
            self.audio.play_note(n, velocity, channel)

    def _on_audio_stop(self, notes: list[int], channel: int = 0):
        for n in notes:
            self.audio.stop_note(n, channel)

    def _on_whammy(self, value: float):
        self.audio.pitch_bend(value)
        self.after(0, self.classic_fretboard.set_whammy_value, value)
        self.after(0, self.keyboard_view.set_touch_strip, (value + 1.0) / 2.0)

    # -------------------------------------------------------------
    # CONTROLES DO USUÁRIO
    # -------------------------------------------------------------
    def _on_quick_instrument_selected(self, inst_id: int):
        """Muda o som de todas as casas/notas instantaneamente."""
        self.audio.set_instrument(inst_id)
        self.config["instrument_id"] = inst_id
        # Toca uma nota de teste rápida para o usuário ouvir o novo som imediatamente!
        self.audio.play_note(52, velocity=115, channel=0)
        self.after(350, lambda: self.audio.stop_note(52, channel=0))
        self.monitor.log(time.strftime("%H:%M:%S"), "SOM", f"Som de todas as notas alterado para instrumento GM {inst_id}")

    def _on_quick_fret_preset_selected(self, preset_name: str, preset_data: dict):
        """Muda os acordes/notas de todas as 5 casas de uma vez só."""
        self.preset_data["frets"] = preset_data
        self.mapper.set_preset(self.preset_data)
        self.classic_fretboard.update_fret_labels_from_preset(self.preset_data)
        # Toca o primeiro acorde para dar feedback imediato
        first_notes = preset_data.get("green", {}).get("notes", [52])
        self.audio.play_chord(first_notes, velocity=115)
        self.after(450, lambda: self.audio.stop_chord(first_notes))
        self.monitor.log(time.strftime("%H:%M:%S"), "ESTILO", f"Todas as 5 casas configuradas para: {preset_name}")

    def _on_preset_selected(self, preset_name: str):
        for pid, pname in self.preset_list:
            if pname == preset_name:
                self.current_preset_id = pid
                self.preset_data = load_preset(pid)
                self.mapper.set_preset(self.preset_data)
                self.classic_fretboard.update_fret_labels_from_preset(self.preset_data)
                
                # Atualiza notas de bateria
                drum_mapping = self.preset_data.get("drum_mapping", {})
                for pad_id, note in drum_mapping.items():
                    self.drum_view.set_pad_mapping(pad_id, note)

                if "instrument_id" in self.preset_data:
                    inst_id = self.preset_data["instrument_id"]
                    self.audio.set_instrument(inst_id)
                    for opt in self.instrument_combo.cget("values"):
                        if opt.startswith(f"{inst_id:03d}"):
                            self.instrument_combo.set(opt)
                            break
                break

    def _on_instrument_selected(self, selection_str: str):
        try:
            inst_id = int(selection_str.split(" - ")[0])
            self.audio.set_instrument(inst_id)
            self.config["instrument_id"] = inst_id
        except Exception:
            pass

    def _on_output_selected(self, selection_str: str):
        if selection_str.startswith("[MIDI OUT]"):
            port_name = selection_str[11:]
            self.audio.set_midi_output_port(port_name)
        else:
            self.audio.set_midi_output_port(None)

    def _on_octave_changed(self, value_str: str):
        try:
            octave = int(value_str)
            self.mapper.set_octave_shift(octave)
            self.config["octave_shift"] = octave
        except Exception:
            pass

    def _on_volume_changed(self, value: float):
        vol = int(value)
        self.volume_label.configure(text=f"{vol}%")
        self.audio.set_volume(vol)
        self.config["volume"] = vol

    def panic_stop(self):
        self.audio.stop_all_notes()
        self.mapper.stop_all_active_notes()
        self.monitor.log(time.strftime("%H:%M:%S"), "PANIC", "Todas as notas foram interrompidas.")

    def _on_close(self):
        self.disconnect()
        self.audio.close()
        self.config["current_preset"] = self.current_preset_id
        save_config(self.config)
        self.destroy()

if __name__ == "__main__":
    app = MidGuitarApp()
    app.mainloop()
