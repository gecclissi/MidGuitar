"""
Leitor assíncrono de eventos MIDI e de Gamepad/Joystick Universal.
Suporta:
- Rock Band 3 Mustang Pro Guitar & Squier Stratocaster (6 cordas, canais 1 a 6)
- Rock Band 3 Wireless Keyboard (25 teclas, fita touch ribbon)
- Band Hero / Guitar Hero / Rock Band Drums (Baterias eletrônicas, Canal 10)
- Rock Band / Guitar Hero 5-Button Guitars (MIDI Pro Adapter ou Gamepad USB)
"""

import threading
import time
import rtmidi
import pygame
from src.midi.mapper import GuitarMapper
from src.midi.instrument_types import InstrumentMode, DRUM_MAP, PRO_GUITAR_STRINGS

DEFAULT_RB_MIDI_NOTES = {
    60: "green",    # C4
    62: "red",      # D4
    64: "yellow",   # E4
    65: "blue",     # F4
    67: "orange",   # G4
    # Outras variações comuns de adaptadores Mad Catz:
    48: "green",
    50: "red",
    52: "yellow",
    53: "blue",
    55: "orange",
}

class MIDIReader:
    def __init__(
        self,
        mapper: GuitarMapper,
        on_event_callback=None,
        on_audio_play=None,
        on_audio_stop=None,
        on_whammy=None,
        on_pro_guitar_event=None,
        on_keyboard_event=None,
        on_drum_event=None,
        on_mode_detected=None
    ):
        self.mapper = mapper
        self.on_event_callback = on_event_callback      # func(timestamp, event_type, details)
        self.on_audio_play = on_audio_play              # func(notes, velocity, channel)
        self.on_audio_stop = on_audio_stop              # func(notes, channel)
        self.on_whammy = on_whammy                      # func(value: float)
        self.on_pro_guitar_event = on_pro_guitar_event  # func(string_num, fret, is_active, velocity)
        self.on_keyboard_event = on_keyboard_event      # func(note, is_active, velocity)
        self.on_drum_event = on_drum_event              # func(note, velocity)
        self.on_mode_detected = on_mode_detected        # func(mode: InstrumentMode)

        self.mode = InstrumentMode.AUTO
        self.midi_in = None
        self.current_port_name = None
        self.is_running = False

        # Thread de Gamepad/Joystick
        self.joystick_thread = None
        self.joystick_stop_flag = threading.Event()

    def set_mode(self, mode: InstrumentMode):
        self.mode = mode

    def connect_midi(self, port_index: int, port_name: str) -> bool:
        """Conecta a uma porta MIDI de entrada."""
        self.disconnect_midi()
        try:
            self.midi_in = rtmidi.MidiIn()
            self.midi_in.open_port(port_index)
            self.midi_in.set_callback(self._midi_callback)
            self.current_port_name = port_name
            self.is_running = True
            self._log_event("CONEXÃO", f"Porta MIDI conectada: {port_name}")
            return True
        except Exception as e:
            self._log_event("ERRO", f"Falha ao conectar na porta MIDI {port_name}: {e}")
            self.disconnect_midi()
            return False

    def disconnect_midi(self):
        """Desconecta a porta MIDI atual."""
        if self.midi_in:
            try:
                self.midi_in.close_port()
                del self.midi_in
            except Exception:
                pass
            self.midi_in = None
            self.current_port_name = None
            self.is_running = False
            self._log_event("DESCONEXÃO", "Porta MIDI desconectada")

    def _midi_callback(self, message, data=None):
        """Callback invocado pelo rtmidi ao receber qualquer mensagem física."""
        midi_msg, delta_time = message
        if not midi_msg:
            return

        status = midi_msg[0] & 0xF0
        channel = (midi_msg[0] & 0x0F) + 1  # 1 a 16
        data1 = midi_msg[1] if len(midi_msg) > 1 else 0
        data2 = midi_msg[2] if len(midi_msg) > 2 else 0

        # =========================================================================
        # 1. DETECÇÃO E PROCESSAMENTO DE BATERIA (CANAL 10)
        # =========================================================================
        if channel == 10:
            if self.mode == InstrumentMode.AUTO and self.on_mode_detected:
                self.on_mode_detected(InstrumentMode.DRUMS)

            if status == 0x90 and data2 > 0:
                note = data1
                velocity = data2
                drum_name = DRUM_MAP.get(note, ("Pad Desconhecido", "drum", ""))[0]
                self._log_event("DRUM HIT", f"Ch 10 | {drum_name} (Nota {note}) | Vel: {velocity}")
                
                if self.on_drum_event:
                    self.on_drum_event(note, velocity)
                
                # Toca no canal de percussão GM (Canal 9 em 0-index)
                if self.on_audio_play:
                    self.on_audio_play([note], velocity, channel=9)
            return

        # =========================================================================
        # 2. NOTE ON (Qualquer canal diferente de 10)
        # =========================================================================
        if status == 0x90 and data2 > 0:
            note = data1
            velocity = data2
            hex_msg = f"{midi_msg[0]:02X} {data1:02X} {data2:02X}"

            # A) MODO GUITARRA PRO (Canais 1 a 6 dedicados por corda - Squier / Mustang)
            if (self.mode == InstrumentMode.PRO_GUITAR) or (self.mode == InstrumentMode.AUTO and 1 <= channel <= 6 and channel in PRO_GUITAR_STRINGS):
                # Canal 1 = 1ª Corda (High E), ..., Canal 6 = 6ª Corda (Low E)
                string_num = channel
                open_note = PRO_GUITAR_STRINGS[string_num]["open_note"]
                fret = note - open_note
                str_name = PRO_GUITAR_STRINGS[string_num]["name"]

                self._log_event("PRO GUITAR", f"Ch {channel} ({str_name}) | Traste {fret} | Vel: {velocity}")

                if self.on_pro_guitar_event:
                    self.on_pro_guitar_event(string_num, fret, True, velocity)
                
                if self.mode == InstrumentMode.AUTO and self.on_mode_detected:
                    self.on_mode_detected(InstrumentMode.PRO_GUITAR)

                # Toca nota real polifônica
                if self.on_audio_play:
                    self.on_audio_play([note], velocity, channel=0)
                return

            # B) MODO GUITARRA CLÁSSICA 5 BOTÕES (Se configurado ou se nota for clássica RB)
            if self.mode == InstrumentMode.CLASSIC_GUITAR or (self.mode == InstrumentMode.AUTO and note in DEFAULT_RB_MIDI_NOTES):
                fret_name = DEFAULT_RB_MIDI_NOTES.get(note)
                if fret_name:
                    stop_notes, play_notes = self.mapper.handle_fret_change(fret_name, True)
                    self._dispatch_notes(stop_notes, play_notes, velocity)
                    self._log_event("NOTE ON", f"Ch {channel} | Casa {fret_name.upper()} | Vel: {velocity}")
                    return
                elif note in (69, 71, 72): # Strum
                    stop_notes, play_notes = self.mapper.handle_strum(is_down=True, is_pressed=True)
                    self._dispatch_notes(stop_notes, play_notes, velocity)
                    self._log_event("STRUM", f"Ch {channel} | Palheta | Vel: {velocity}")
                    return

            # C) MODO TECLADO (25 teclas C3=48 a C5=72 ou qualquer teclado MIDI)
            self._log_event("NOTE ON", f"Ch {channel} | Nota: {note} | Vel: {velocity} [{hex_msg}]")
            
            if self.on_keyboard_event:
                self.on_keyboard_event(note, True, velocity)
            
            if self.mode == InstrumentMode.AUTO and (48 <= note <= 72) and self.on_mode_detected:
                self.on_mode_detected(InstrumentMode.KEYBOARD)

            if self.on_audio_play:
                self.on_audio_play([note], velocity, channel=0)

        # =========================================================================
        # 3. NOTE OFF (ou Note On com velocity 0)
        # =========================================================================
        elif status == 0x80 or (status == 0x90 and data2 == 0):
            note = data1
            hex_msg = f"{midi_msg[0]:02X} {data1:02X} {data2:02X}"

            # Guitarra Pro
            if (self.mode == InstrumentMode.PRO_GUITAR) or (self.mode == InstrumentMode.AUTO and 1 <= channel <= 6 and channel in PRO_GUITAR_STRINGS):
                string_num = channel
                open_note = PRO_GUITAR_STRINGS[string_num]["open_note"]
                fret = note - open_note
                if self.on_pro_guitar_event:
                    self.on_pro_guitar_event(string_num, fret, False, 0)
                if self.on_audio_stop:
                    self.on_audio_stop([note], channel=0)
                return

            # Guitarra 5 Botões
            if self.mode == InstrumentMode.CLASSIC_GUITAR or (self.mode == InstrumentMode.AUTO and note in DEFAULT_RB_MIDI_NOTES):
                fret_name = DEFAULT_RB_MIDI_NOTES.get(note)
                if fret_name:
                    stop_notes, play_notes = self.mapper.handle_fret_change(fret_name, False)
                    self._dispatch_notes(stop_notes, play_notes)
                    return
                elif note in (69, 71, 72):
                    stop_notes, play_notes = self.mapper.handle_strum(is_down=True, is_pressed=False)
                    self._dispatch_notes(stop_notes, play_notes)
                    return

            # Teclado / Geral
            self._log_event("NOTE OFF", f"Ch {channel} | Nota: {note} [{hex_msg}]")
            if self.on_keyboard_event:
                self.on_keyboard_event(note, False, 0)
            if self.on_audio_stop:
                self.on_audio_stop([note], channel=0)

        # =========================================================================
        # 4. CONTROL CHANGE (CC)
        # =========================================================================
        elif status == 0xB0:
            cc_num = data1
            cc_val = data2
            self._log_event("CC", f"Ch {channel} | CC #{cc_num} = {cc_val}")
            
            # Alavanca de Whammy ou Fita Touch Ribbon do Teclado (CC 1 = Modulation)
            if cc_num in (1, 11, 14, 16):
                normalized = (cc_val - 64) / 64.0  # -1.0 a +1.0
                if self.on_whammy:
                    self.on_whammy(normalized)

        # =========================================================================
        # 5. PITCH BEND
        # =========================================================================
        elif status == 0xE0:
            raw_val = data1 + (data2 << 7)  # 0 a 16383, centro 8192
            normalized = (raw_val - 8192) / 8192.0
            self._log_event("PITCH BEND", f"Valor: {raw_val} ({normalized:+.2f})")
            if self.on_whammy:
                self.on_whammy(normalized)

    def _dispatch_notes(self, stop_notes: list[int], play_notes: list[int], velocity: int = 100, channel: int = 0):
        if stop_notes and self.on_audio_stop:
            self.on_audio_stop(stop_notes, channel)
        if play_notes and self.on_audio_play:
            self.on_audio_play(play_notes, velocity, channel)

    def _log_event(self, event_type: str, details: str):
        if self.on_event_callback:
            timestamp = time.strftime("%H:%M:%S")
            self.on_event_callback(timestamp, event_type, details)

    # -------------------------------------------------------------
    # Suporte a Gamepad / Joystick USB direto (Guitar Hero / Rock Band)
    # -------------------------------------------------------------
    def start_gamepad_listener(self, joystick_index: int = 0):
        """Inicia monitoramento em background de joystick/gamepad USB."""
        self.stop_gamepad_listener()
        self.joystick_stop_flag.clear()

        def _loop():
            try:
                if not pygame.get_init():
                    pygame.init()
                if not pygame.joystick.get_init():
                    pygame.joystick.init()
                
                if pygame.joystick.get_count() <= joystick_index:
                    return
                
                js = pygame.joystick.Joystick(joystick_index)
                js.init()
                self._log_event("GAMEPAD", f"Dispositivo USB conectado: {js.get_name()}")

                prev_buttons = [0] * js.get_numbuttons()
                prev_hat = (0, 0)

                while not self.joystick_stop_flag.is_set():
                    pygame.event.pump()
                    
                    # 1. Botões das casas (A, B, Y, X, LB)
                    btn_map = {
                        0: "green",
                        1: "red",
                        2: "yellow",
                        3: "blue",
                        4: "orange"
                    }
                    for b_idx, fret_name in btn_map.items():
                        if b_idx < len(prev_buttons):
                            val = js.get_button(b_idx)
                            if val != prev_buttons[b_idx]:
                                prev_buttons[b_idx] = val
                                stop_notes, play_notes = self.mapper.handle_fret_change(fret_name, bool(val))
                                self._dispatch_notes(stop_notes, play_notes, 100)
                                self._log_event("FRET", f"Casa {fret_name.upper()}: {'PRESSIONADA' if val else 'SOLTA'}")

                    # 2. D-Pad / Hat (Palheta Strum Up/Down)
                    if js.get_numhats() > 0:
                        hat = js.get_hat(0)
                        if hat != prev_hat:
                            if hat[1] == 1 and prev_hat[1] != 1:
                                stop_notes, play_notes = self.mapper.handle_strum(is_down=False, is_pressed=True)
                                self._dispatch_notes(stop_notes, play_notes, 110)
                                self._log_event("STRUM", "Palhetada para CIMA")
                            elif hat[1] == -1 and prev_hat[1] != -1:
                                stop_notes, play_notes = self.mapper.handle_strum(is_down=True, is_pressed=True)
                                self._dispatch_notes(stop_notes, play_notes, 110)
                                self._log_event("STRUM", "Palhetada para BAIXO")
                            elif hat[1] == 0:
                                self.mapper.handle_strum(is_down=True, is_pressed=False)
                            prev_hat = hat

                    # 3. Eixos (Alavanca de Whammy)
                    if js.get_numaxes() > 2:
                        axis_val = js.get_axis(2)
                        if abs(axis_val) > 0.05 and self.on_whammy:
                            self.on_whammy(axis_val)

                    time.sleep(0.005)
            except Exception as e:
                self._log_event("ERRO GAMEPAD", str(e))

        self.joystick_thread = threading.Thread(target=_loop, daemon=True)
        self.joystick_thread.start()

    def stop_gamepad_listener(self):
        self.joystick_stop_flag.set()
        if self.joystick_thread and self.joystick_thread.is_alive():
            self.joystick_thread.join(timeout=0.5)
        self.joystick_thread = None
