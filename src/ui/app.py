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
        self.geometry("1060x720")
        self.minsize(920, 620)

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

        # Inicializa o motor de áudio
        self.audio = AudioEngine(
            midi_out_port_name=self.config.get("midi_out_port"),
            instrument_id=self.config.get("instrument_id", 29),
            volume=self.config.get("volume", 85)
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
        # -------------------------------------------------------------
        # 1. HEADER
        # -------------------------------------------------------------
        header = ctk.CTkFrame(self, fg_color="#0F172A", height=60, corner_radius=0)
        header.pack(fill="x", side="top")

        # Título
        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left", padx=18, pady=10)

        title_label = ctk.CTkLabel(
            title_box, text="🎸 MidGuitar Studio", font=ctk.CTkFont(size=20, weight="bold"), text_color="#38BDF8"
        )
        title_label.pack(side="left")

        subtitle = ctk.CTkLabel(
            title_box, text="Universal MIDI Studio (Guitarras Pro/6 Cordas • Teclados • Baterias • 5 Botões)",
            font=ctk.CTkFont(size=12), text_color="#94A3B8"
        )
        subtitle.pack(side="left", padx=(10, 0), pady=(3, 0))

        # Badge de Status de Conexão
        self.status_badge = ctk.CTkLabel(
            header, text="○ Desconectado", font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#EF4444", fg_color="#1E293B", corner_radius=12, padx=12, pady=4
        )
        self.status_badge.pack(side="right", padx=18, pady=12)

        # -------------------------------------------------------------
        # 2. BARRA DE CONEXÃO E DISPOSITIVOS
        # -------------------------------------------------------------
        conn_bar = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=8)
        conn_bar.pack(fill="x", padx=16, pady=(8, 4))

        # Entrada (MIDI In / Gamepad)
        ctk.CTkLabel(conn_bar, text="Entrada MIDI/USB:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(12, 4), pady=8)
        self.input_combo = ctk.CTkComboBox(conn_bar, width=250, values=["Nenhum dispositivo"])
        self.input_combo.pack(side="left", padx=4, pady=8)

        # Botão Atualizar
        btn_refresh = ctk.CTkButton(
            conn_bar, text="🔄 Atualizar", width=85, height=28,
            fg_color="#334155", hover_color="#475569", command=self.refresh_devices
        )
        btn_refresh.pack(side="left", padx=4, pady=8)

        # Botão Conectar / Desconectar
        self.btn_connect = ctk.CTkButton(
            conn_bar, text="Conectar", width=100, height=28,
            fg_color="#10B981", hover_color="#059669", font=ctk.CTkFont(weight="bold"),
            command=self.toggle_connection
        )
        self.btn_connect.pack(side="left", padx=8, pady=8)

        # Saída (Sintetizador ou DAW)
        ctk.CTkLabel(conn_bar, text="Saída de Áudio:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(18, 4), pady=8)
        self.output_combo = ctk.CTkComboBox(
            conn_bar, width=240, values=["Synth Nativo Windows (GS Wavetable)"],
            command=self._on_output_selected
        )
        self.output_combo.pack(side="left", padx=4, pady=8)

        # -------------------------------------------------------------
        # 3. SELETOR DE INSTRUMENTO / MODO UNIVERSAL
        # -------------------------------------------------------------
        mode_bar = ctk.CTkFrame(self, fg_color="transparent")
        mode_bar.pack(fill="x", padx=16, pady=(4, 6))

        ctk.CTkLabel(mode_bar, text="Instrumento Ativo:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(4, 8))

        self.mode_selector = ctk.CTkSegmentedButton(
            mode_bar,
            values=[
                "⚡ Auto (Detectar)",
                "🎸 Guitarra Pro (6 Cordas)",
                "🎮 Guitarra 5 Botões",
                "🎹 Teclado (25 Teclas)",
                "🥁 Bateria (Canal 10)"
            ],
            command=self._on_mode_button_clicked
        )
        self.mode_selector.pack(side="left", fill="x", expand=True)
        self.mode_selector.set("⚡ Auto (Detectar)")

        # -------------------------------------------------------------
        # 4. ÁREA PRINCIPAL (INSTRUMENTO VISUAL + MONITOR)
        # -------------------------------------------------------------
        main_split = ctk.CTkFrame(self, fg_color="transparent")
        main_split.pack(fill="both", expand=True, padx=16, pady=4)

        # Container esquerdo: onde os instrumentos visuais alternam
        self.instrument_container = ctk.CTkFrame(main_split, fg_color="#1E293B", corner_radius=10)
        self.instrument_container.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # Cria as 4 visões de instrumentos com suporte completo a clique para ouvir
        self.pro_fretboard = ProFretboardView(
            self.instrument_container, fg_color="transparent",
            on_fret_click=self._on_pro_fretboard_clicked
        )
        self.classic_fretboard = FretboardView(
            self.instrument_container, fg_color="transparent",
            on_fret_click=self._on_classic_fret_clicked,
            on_open_mapping=self.open_mapping_editor
        )
        self.keyboard_view = KeyboardView(
            self.instrument_container, fg_color="transparent",
            on_key_click=self._on_keyboard_key_clicked
        )
        self.drum_view = DrumView(
            self.instrument_container, fg_color="transparent",
            on_pad_click=self._on_drum_pad_clicked,
            on_open_mapping=self.open_mapping_editor
        )

        # Exibe inicialmente a Guitarra Pro
        self.active_visual_view = self.pro_fretboard
        self.pro_fretboard.pack(fill="both", expand=True, padx=6, pady=6)

        # Direita: Monitor MIDI
        self.monitor = MonitorView(main_split, fg_color="#1E293B", corner_radius=10, width=320)
        self.monitor.pack(side="right", fill="both", padx=(8, 0))

        # -------------------------------------------------------------
        # 5. PAINEL DE CONTROLE DE ÁUDIO & PRESETS
        # -------------------------------------------------------------
        bottom_panel = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=10)
        bottom_panel.pack(fill="x", padx=16, pady=(6, 12))

        # Linha 1: Preset, Botão de Mapeamento e Instrumento GM
        row1 = ctk.CTkFrame(bottom_panel, fg_color="transparent")
        row1.pack(fill="x", padx=12, pady=(8, 4))

        ctk.CTkLabel(row1, text="Preset:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(4, 6))
        preset_names = [name for _, name in self.preset_list] or ["Padrão"]
        self.preset_combo = ctk.CTkComboBox(
            row1, width=190, values=preset_names, command=self._on_preset_selected
        )
        self.preset_combo.pack(side="left", padx=4)

        for pid, pname in self.preset_list:
            if pid == self.current_preset_id:
                self.preset_combo.set(pname)
                break

        # Botão dedicado para abrir o Editor de Mapeamentos
        btn_open_map = ctk.CTkButton(
            row1, text="🎛️ Editar Mapeamentos", width=160, height=28,
            fg_color="#3B82F6", hover_color="#2563EB", font=ctk.CTkFont(weight="bold"),
            command=self.open_mapping_editor
        )
        btn_open_map.pack(side="left", padx=8)

        ctk.CTkLabel(row1, text="Timbre GM:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(12, 6))
        instrument_options = [f"{num:03d} - {name} ({cat})" for num, name, cat in GM_INSTRUMENTS]
        self.instrument_combo = ctk.CTkComboBox(
            row1, width=240, values=instrument_options, command=self._on_instrument_selected
        )
        self.instrument_combo.pack(side="left", padx=4)
        
        curr_inst = self.config.get("instrument_id", 29)
        for opt in instrument_options:
            if opt.startswith(f"{curr_inst:03d}"):
                self.instrument_combo.set(opt)
                break

        # Botão Pânico
        btn_panic = ctk.CTkButton(
            row1, text="⏹️ Parar Notas (Panic)", width=140, height=28,
            fg_color="#DC2626", hover_color="#B91C1C", font=ctk.CTkFont(weight="bold"),
            command=self.panic_stop
        )
        btn_panic.pack(side="right", padx=6)

        # Linha 2: Oitava e Volume
        row2 = ctk.CTkFrame(bottom_panel, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=(4, 8))

        ctk.CTkLabel(row2, text="Oitava:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(4, 6))
        self.octave_seg = ctk.CTkSegmentedButton(
            row2, values=["-2", "-1", "0", "+1", "+2"], command=self._on_octave_changed
        )
        self.octave_seg.pack(side="left", padx=4)
        self.octave_seg.set(str(self.config.get("octave_shift", 0)))

        ctk.CTkLabel(row2, text="Volume:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(24, 6))
        self.volume_slider = ctk.CTkSlider(
            row2, from_=0, to=100, number_of_steps=100, width=180,
            command=self._on_volume_changed
        )
        self.volume_slider.set(self.config.get("volume", 85))
        self.volume_slider.pack(side="left", padx=4)

        self.volume_label = ctk.CTkLabel(row2, text=f"{int(self.volume_slider.get())}%", width=40)
        self.volume_label.pack(side="left", padx=2)

    # -------------------------------------------------------------
    # CLIQUE DIRETO NAS NOTAS (PREVIEW & TESTE DE ÁUDIO)
    # -------------------------------------------------------------
    def _on_classic_fret_clicked(self, fret_name: str):
        """Disparado quando o usuário clica em uma das 5 casas da guitarra."""
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
        self.monitor.log(time.strftime("%H:%M:%S"), "TESTE", f"Clique Pad {pad_id.upper()} ➔ Nota {note} (Canal 10)")
        self.audio.play_note(note, velocity=120, channel=9)
        self.after(200, lambda: self.audio.stop_note(note, channel=9))

    def _on_keyboard_key_clicked(self, note: int):
        """Disparado quando o usuário clica em uma tecla do teclado."""
        note_name = midi_note_to_name(note)
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
            self.status_badge.configure(text=f"● Conectado: {device_name[:20]}", text_color="#22C55E")
            self.btn_connect.configure(text="Desconectar", fg_color="#DC2626", hover_color="#B91C1C")
        else:
            self.status_badge.configure(text="○ Desconectado", text_color="#EF4444")
            self.btn_connect.configure(text="Conectar", fg_color="#10B981", hover_color="#059669")

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
