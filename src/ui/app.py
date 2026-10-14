"""
Janela Principal da aplicação MidGuitar em CustomTkinter.
Unifica detecção de hardware, mapeamento, motor de áudio e interface visual.
"""

import customtkinter as ctk
import tkinter as tk
import time
from src.ui.fretboard_view import FretboardView
from src.ui.monitor_view import MonitorView
from src.midi.detector import (
    get_midi_input_ports, get_midi_output_ports, get_gamepad_devices,
    find_rockband_midi_input, find_default_midi_output
)
from src.midi.mapper import GuitarMapper
from src.midi.reader import MIDIReader
from src.audio.engine import AudioEngine
from src.utils.config_manager import load_config, save_config, list_presets, load_preset
from src.utils.instruments import GM_INSTRUMENTS, INSTRUMENT_NAMES

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class MidGuitarApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("MidGuitar - Rock Band MIDI Controller & Studio")
        self.geometry("980x680")
        self.minsize(860, 580)

        # Carrega configurações e presets
        self.config = load_config()
        self.preset_list = list_presets()
        self.current_preset_id = self.config.get("current_preset", "rock_power_chords")
        self.preset_data = load_preset(self.current_preset_id)

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

        # Inicializa o leitor MIDI
        self.reader = MIDIReader(
            mapper=self.mapper,
            on_event_callback=self._on_midi_event,
            on_audio_play=self._on_audio_play,
            on_audio_stop=self._on_audio_stop,
            on_whammy=self._on_whammy
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
            title_box, text="🎸 MidGuitar", font=ctk.CTkFont(size=20, weight="bold"), text_color="#38BDF8"
        )
        title_label.pack(side="left")

        subtitle = ctk.CTkLabel(
            title_box, text="Rock Band 3 & MIDI Controller Studio",
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
        conn_bar.pack(fill="x", padx=16, pady=10)

        # Entrada (MIDI In / Gamepad)
        ctk.CTkLabel(conn_bar, text="Entrada:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(12, 4), pady=10)
        self.input_combo = ctk.CTkComboBox(conn_bar, width=240, values=["Nenhum dispositivo"])
        self.input_combo.pack(side="left", padx=4, pady=10)

        # Botão Atualizar
        btn_refresh = ctk.CTkButton(
            conn_bar, text="🔄 Atualizar", width=85, height=28,
            fg_color="#334155", hover_color="#475569", command=self.refresh_devices
        )
        btn_refresh.pack(side="left", padx=4, pady=10)

        # Botão Conectar / Desconectar
        self.btn_connect = ctk.CTkButton(
            conn_bar, text="Conectar", width=100, height=28,
            fg_color="#10B981", hover_color="#059669", font=ctk.CTkFont(weight="bold"),
            command=self.toggle_connection
        )
        self.btn_connect.pack(side="left", padx=8, pady=10)

        # Saída (Sintetizador ou DAW)
        ctk.CTkLabel(conn_bar, text="Saída de Áudio:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(18, 4), pady=10)
        self.output_combo = ctk.CTkComboBox(
            conn_bar, width=230, values=["Synth Nativo Windows (GS Wavetable)"],
            command=self._on_output_selected
        )
        self.output_combo.pack(side="left", padx=4, pady=10)

        # -------------------------------------------------------------
        # 3. ÁREA PRINCIPAL (FRETBOARD + MONITOR)
        # -------------------------------------------------------------
        main_split = ctk.CTkFrame(self, fg_color="transparent")
        main_split.pack(fill="both", expand=True, padx=16, pady=4)

        # Esquerda: Braço da Guitarra (Fretboard)
        self.fretboard = FretboardView(main_split, fg_color="#1E293B", corner_radius=10)
        self.fretboard.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.fretboard.update_fret_labels_from_preset(self.preset_data)

        # Direita: Monitor MIDI
        self.monitor = MonitorView(main_split, fg_color="#1E293B", corner_radius=10)
        self.monitor.pack(side="right", fill="both", expand=True, padx=(8, 0))

        # -------------------------------------------------------------
        # 4. PAINEL DE CONTROLE DE ÁUDIO & PRESETS
        # -------------------------------------------------------------
        bottom_panel = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=10)
        bottom_panel.pack(fill="x", padx=16, pady=(8, 14))

        # Linha 1: Preset e Instrumento
        row1 = ctk.CTkFrame(bottom_panel, fg_color="transparent")
        row1.pack(fill="x", padx=12, pady=(10, 6))

        # Preset
        ctk.CTkLabel(row1, text="Preset:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(4, 6))
        preset_names = [name for _, name in self.preset_list] or ["Padrão"]
        self.preset_combo = ctk.CTkComboBox(
            row1, width=200, values=preset_names, command=self._on_preset_selected
        )
        self.preset_combo.pack(side="left", padx=4)

        # Seleciona o nome do preset atual no combo
        for pid, pname in self.preset_list:
            if pid == self.current_preset_id:
                self.preset_combo.set(pname)
                break

        # Instrumento GM
        ctk.CTkLabel(row1, text="Instrumento:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(16, 6))
        instrument_options = [f"{num:03d} - {name} ({cat})" for num, name, cat in GM_INSTRUMENTS]
        self.instrument_combo = ctk.CTkComboBox(
            row1, width=260, values=instrument_options, command=self._on_instrument_selected
        )
        self.instrument_combo.pack(side="left", padx=4)
        
        # Seleciona instrumento padrão
        curr_inst = self.config.get("instrument_id", 29)
        for opt in instrument_options:
            if opt.startswith(f"{curr_inst:03d}"):
                self.instrument_combo.set(opt)
                break

        # Botão Pânico (Parar Todas as Notas)
        btn_panic = ctk.CTkButton(
            row1, text="⏹️ Parar Notas (Panic)", width=140, height=28,
            fg_color="#DC2626", hover_color="#B91C1C", font=ctk.CTkFont(weight="bold"),
            command=self.panic_stop
        )
        btn_panic.pack(side="right", padx=6)

        # Linha 2: Oitava e Volume
        row2 = ctk.CTkFrame(bottom_panel, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=(4, 10))

        # Deslocamento de Oitava
        ctk.CTkLabel(row2, text="Oitava:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(4, 6))
        self.octave_seg = ctk.CTkSegmentedButton(
            row2, values=["-2", "-1", "0", "+1", "+2"], command=self._on_octave_changed
        )
        self.octave_seg.pack(side="left", padx=4)
        self.octave_seg.set(str(self.config.get("octave_shift", 0)))

        # Volume
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
    # GERENCIAMENTO DE CONEXÃO & DISPOSITIVOS
    # -------------------------------------------------------------
    def refresh_devices(self):
        """Varre portas MIDI e Gamepads e atualiza as caixas de seleção."""
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
        
        # Sugere dispositivo Rock Band detectado se nada estiver selecionado
        auto_rb = find_rockband_midi_input()
        if auto_rb:
            target_str = f"[MIDI] {auto_rb[1]}"
            if target_str in input_options:
                self.input_combo.set(target_str)
        elif input_options:
            self.input_combo.set(input_options[0])

        # Portas de saída
        midi_out_ports = get_midi_output_ports()
        output_options = ["Synth Nativo Windows (GS Wavetable)"]
        for p in midi_out_ports:
            output_options.append(f"[MIDI OUT] {p}")
        self.output_combo.configure(values=output_options)

    def auto_connect(self):
        """Conecta automaticamente ao melhor dispositivo encontrado."""
        auto_rb = find_rockband_midi_input()
        if auto_rb:
            port_idx, port_name = auto_rb
            self._connect_midi(port_idx, port_name)

    def toggle_connection(self):
        """Alterna o estado de conexão do botão."""
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
            # Controle USB direto
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
        """Recebe log de evento e atualiza o monitor e a guitarra visual na thread principal."""
        self.after(0, self._process_ui_event, timestamp, event_type, details)

    def _process_ui_event(self, timestamp: str, event_type: str, details: str):
        self.monitor.log(timestamp, event_type, details)

        # Atualiza botões do fretboard
        state = self.mapper.state
        self.fretboard.set_fret_state("green", state.green)
        self.fretboard.set_fret_state("red", state.red)
        self.fretboard.set_fret_state("yellow", state.yellow)
        self.fretboard.set_fret_state("blue", state.blue)
        self.fretboard.set_fret_state("orange", state.orange)
        self.fretboard.set_strum_state(is_down=True, is_active=state.strum_down)
        self.fretboard.set_strum_state(is_down=False, is_active=state.strum_up)

    def _on_audio_play(self, notes: list[int], velocity: int):
        self.audio.play_chord(notes, velocity)

    def _on_audio_stop(self, notes: list[int]):
        self.audio.stop_chord(notes)

    def _on_whammy(self, value: float):
        self.audio.pitch_bend(value)
        self.after(0, self.fretboard.set_whammy_value, value)

    # -------------------------------------------------------------
    # CONTROLES DO USUÁRIO (PRESETS, INSTRUMENTOS, VOLUME)
    # -------------------------------------------------------------
    def _on_preset_selected(self, preset_name: str):
        for pid, pname in self.preset_list:
            if pname == preset_name:
                self.current_preset_id = pid
                self.preset_data = load_preset(pid)
                self.mapper.set_preset(self.preset_data)
                self.fretboard.update_fret_labels_from_preset(self.preset_data)
                
                # Se o preset definir um instrumento recomendado, aplica
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
        """Para imediatamente todas as notas e limpa a guitarra."""
        self.audio.stop_all_notes()
        self.mapper.stop_all_active_notes()
        for fret in ("green", "red", "yellow", "blue", "orange"):
            self.fretboard.set_fret_state(fret, False)
        self.fretboard.set_strum_state(is_down=True, is_active=False)
        self.fretboard.set_strum_state(is_down=False, is_active=False)
        self.monitor.log(time.strftime("%H:%M:%S"), "PANIC", "Todas as notas foram interrompidas.")

    def _on_close(self):
        """Salva configurações e fecha recursos."""
        self.disconnect()
        self.audio.close()
        self.config["current_preset"] = self.current_preset_id
        save_config(self.config)
        self.destroy()

if __name__ == "__main__":
    app = MidGuitarApp()
    app.mainloop()
