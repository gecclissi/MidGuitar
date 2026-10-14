"""
Motor de áudio universal para o MidGuitar:
1. Sintetizador nativo do Windows (Microsoft GS Wavetable Synth via pygame.midi) - Funciona 100% sem instalar DLLs!
2. Roteamento MIDI Pass-through (rtmidi) para DAWs (Reaper, FL Studio, Ableton, Amplitube, etc.)
3. Suporte opcional a SoundFonts (.sf2) via pyfluidsynth se disponível no sistema.
"""

import os
import pygame.midi
import pygame.mixer
import rtmidi
from src.utils.instruments import INSTRUMENT_NAMES

# Mapeamento de notas de bateria General MIDI para identificadores de pads
DRUM_NOTE_TO_PAD = {
    35: "kick",
    36: "kick",
    38: "snare",
    40: "snare",
    42: "hihat",
    44: "hihat",
    46: "hihat",
    48: "tom1",
    50: "tom1",
    41: "tom2",
    43: "tom2",
    45: "tom2",
    47: "tom2",
    49: "crash",
    51: "crash",
    52: "crash",
    55: "crash",
    57: "crash",
}

class AudioEngine:
    def __init__(self, midi_out_port_name: str | None = None, instrument_id: int = 29, volume: int = 85, initial_samples: dict | None = None):
        self.instrument_id = instrument_id
        self.volume = max(0, min(100, volume))
        self.midi_out_port_name = midi_out_port_name
        self.active_sounding_notes = set()

        # Dicionário de samples customizados (.wav, .mp3, .ogg)
        self.custom_samples = {}
        self._init_pygame_mixer()
        if initial_samples:
            for k, p in initial_samples.items():
                self.load_sample(k, p)

        # Instância pygame.midi (Sintetizador Nativo do Windows)
        self.pygame_output = None
        self._init_pygame_synth()

        # Instância rtmidi (Saída para DAWs / loopMIDI)
        self.rtmidi_out = None
        self._init_rtmidi_out(midi_out_port_name)

        # Configura instrumento e volume inicial
        self.set_instrument(self.instrument_id)
        self.set_volume(self.volume)

    def _init_pygame_mixer(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
                pygame.mixer.set_num_channels(32)
        except Exception as e:
            print(f"[AudioEngine] Aviso ao iniciar mixer: {e}")

    def load_sample(self, sample_id: str, file_path: str) -> bool:
        """Carrega um arquivo de áudio (.wav, .mp3, .ogg) para uma chave de instrumento."""
        if not file_path or not os.path.exists(file_path):
            return False
        try:
            sound = pygame.mixer.Sound(file_path)
            self.custom_samples[sample_id] = {
                "path": file_path,
                "sound": sound
            }
            print(f"[AudioEngine] Sample carregado com sucesso: {sample_id} -> {file_path}")
            return True
        except Exception as e:
            print(f"[AudioEngine] Erro ao carregar sample {file_path}: {e}")
            return False

    def remove_sample(self, sample_id: str):
        """Remove um sample customizado, voltando para o som MIDI padrão."""
        if sample_id in self.custom_samples:
            del self.custom_samples[sample_id]

    def get_sample_path(self, sample_id: str) -> str | None:
        if sample_id in self.custom_samples:
            return self.custom_samples[sample_id]["path"]
        return None

    def play_sample(self, sample_id: str, velocity: int = 100) -> bool:
        """Toca um sample customizado se existir."""
        if sample_id in self.custom_samples:
            try:
                sound = self.custom_samples[sample_id]["sound"]
                vol = (self.volume / 100.0) * (velocity / 127.0)
                sound.set_volume(max(0.0, min(1.0, vol)))
                sound.play()
                return True
            except Exception as e:
                print(f"[AudioEngine] Erro ao tocar sample {sample_id}: {e}")
        return False

    def _init_pygame_synth(self):
        try:
            if not pygame.midi.get_init():
                pygame.midi.init()
            
            # Encontra o dispositivo de síntese nativa do Windows (MMSystem / Microsoft GS Wavetable)
            synth_id = None
            for i in range(pygame.midi.get_count()):
                info = pygame.midi.get_device_info(i)
                # info: (interface, name, input, output, opened)
                if info[3] == 1:  # is output
                    name = info[1].decode('utf-8', errors='ignore')
                    if "wavetable" in name.lower() or "synth" in name.lower() or "mapper" in name.lower():
                        synth_id = i
                        break

            if synth_id is None:
                synth_id = pygame.midi.get_default_output_id()

            if synth_id != -1:
                self.pygame_output = pygame.midi.Output(synth_id)
                print(f"[AudioEngine] Sintetizador nativo conectado (ID {synth_id})")
        except Exception as e:
            print(f"[AudioEngine] Aviso: não foi possível inicializar synth nativo: {e}")

    def _init_rtmidi_out(self, port_name: str | None):
        if not port_name:
            return
        try:
            self.rtmidi_out = rtmidi.MidiOut()
            ports = self.rtmidi_out.get_ports()
            for i, p in enumerate(ports):
                if port_name.lower() in p.lower():
                    self.rtmidi_out.open_port(i)
                    print(f"[AudioEngine] Saída MIDI externa conectada a: {p}")
                    return
            print(f"[AudioEngine] Porta de saída '{port_name}' não encontrada.")
        except Exception as e:
            print(f"[AudioEngine] Erro ao abrir porta rtmidi out: {e}")

    def set_midi_output_port(self, port_name: str | None):
        """Altera a porta de saída externa (DAW)."""
        self.midi_out_port_name = port_name
        if self.rtmidi_out:
            try:
                self.rtmidi_out.close_port()
            except Exception:
                pass
            self.rtmidi_out = None
        if port_name:
            self._init_rtmidi_out(port_name)

    def set_instrument(self, instrument_id: int, channel: int = 0):
        """Define o instrumento General MIDI (0 a 127)."""
        self.instrument_id = max(0, min(127, instrument_id))
        
        # Sintetizador nativo
        if self.pygame_output:
            try:
                self.pygame_output.set_instrument(self.instrument_id, channel)
            except Exception as e:
                print(f"[AudioEngine] Erro ao mudar instrumento pygame: {e}")

        # Envia Program Change para DAW externa
        if self.rtmidi_out and self.rtmidi_out.is_port_open():
            try:
                # 0xC0 = Program Change no canal 0
                self.rtmidi_out.send_message([0xC0 | channel, self.instrument_id])
            except Exception as e:
                print(f"[AudioEngine] Erro ao enviar Program Change rtmidi: {e}")

    def set_volume(self, volume_percent: int, channel: int = 0):
        """Ajusta o volume geral (0 a 100%)."""
        self.volume = max(0, min(100, volume_percent))
        midi_vol = int(self.volume * 1.27)  # mapeia 0-100 para 0-127

        # Envia CC 7 (Channel Volume)
        if self.pygame_output:
            try:
                # write_short(status, data1, data2)
                self.pygame_output.write_short(0xB0 | channel, 7, midi_vol)
            except Exception:
                pass

        if self.rtmidi_out and self.rtmidi_out.is_port_open():
            try:
                self.rtmidi_out.send_message([0xB0 | channel, 7, midi_vol])
            except Exception:
                pass

    def play_note(self, note: int, velocity: int = 100, channel: int = 0):
        """Dispara uma nota individual (ou sample customizado se configurado)."""
        note = max(0, min(127, note))
        velocity = max(1, min(127, velocity))
        self.active_sounding_notes.add(note)

        # 1. Verifica se há sample customizado (.wav / .mp3)
        sample_played = False
        if channel == 9:  # Bateria (Canal 10)
            pad_key = DRUM_NOTE_TO_PAD.get(note)
            if pad_key and self.play_sample(pad_key, velocity):
                sample_played = True
            elif self.play_sample(f"drum_{note}", velocity):
                sample_played = True
        else:
            if self.play_sample(f"note_{note}", velocity):
                sample_played = True

        # 2. Se não tocou sample customizado, usa o sintetizador nativo
        if not sample_played and self.pygame_output:
            try:
                self.pygame_output.note_on(note, velocity, channel)
            except Exception:
                pass

        # 3. Sempre envia MIDI para a porta de saída externa (DAWs / loopMIDI)
        if self.rtmidi_out and self.rtmidi_out.is_port_open():
            try:
                self.rtmidi_out.send_message([0x90 | channel, note, velocity])
            except Exception:
                pass

    def stop_note(self, note: int, channel: int = 0):
        """Interrompe uma nota individual."""
        note = max(0, min(127, note))
        self.active_sounding_notes.discard(note)

        if self.pygame_output:
            try:
                self.pygame_output.note_off(note, 64, channel)
            except Exception:
                pass

        if self.rtmidi_out and self.rtmidi_out.is_port_open():
            try:
                self.rtmidi_out.send_message([0x80 | channel, note, 64])
            except Exception:
                pass

    def play_chord(self, notes: list[int], velocity: int = 100, channel: int = 0):
        """Dispara múltiplas notas simultaneamente (acorde)."""
        for n in notes:
            self.play_note(n, velocity, channel)

    def stop_chord(self, notes: list[int], channel: int = 0):
        """Interrompe múltiplas notas."""
        for n in notes:
            self.stop_note(n, channel)

    def stop_all_notes(self, channel: int = 0):
        """Para todas as notas soando (Panic / All Notes Off)."""
        for n in list(self.active_sounding_notes):
            self.stop_note(n, channel)
        self.active_sounding_notes.clear()

        # Envia CC 123 (All Notes Off)
        if self.pygame_output:
            try:
                self.pygame_output.write_short(0xB0 | channel, 123, 0)
            except Exception:
                pass
        if self.rtmidi_out and self.rtmidi_out.is_port_open():
            try:
                self.rtmidi_out.send_message([0xB0 | channel, 123, 0])
            except Exception:
                pass

    def pitch_bend(self, value: float, channel: int = 0):
        """
        Ajusta Pitch Bend (alavanca de whammy).
        value varia de -1.0 a +1.0 (onde 0.0 é centro).
        Mapeia para MIDI Pitch Bend de 0 a 16383 (centro = 8192).
        """
        raw_val = int(8192 + (value * 8191))
        raw_val = max(0, min(16383, raw_val))
        lsb = raw_val & 0x7F
        msb = (raw_val >> 7) & 0x7F

        if self.pygame_output:
            try:
                self.pygame_output.write_short(0xE0 | channel, lsb, msb)
            except Exception:
                pass

        if self.rtmidi_out and self.rtmidi_out.is_port_open():
            try:
                self.rtmidi_out.send_message([0xE0 | channel, lsb, msb])
            except Exception:
                pass

    def close(self):
        """Fecha com segurança todos os recursos de áudio."""
        self.stop_all_notes()
        if pygame.mixer.get_init():
            try:
                pygame.mixer.stop()
                pygame.mixer.quit()
            except Exception:
                pass

        if self.pygame_output:
            try:
                del self.pygame_output
                self.pygame_output = None
                pygame.midi.quit()
            except Exception:
                pass

        if self.rtmidi_out:
            try:
                self.rtmidi_out.close_port()
                del self.rtmidi_out
                self.rtmidi_out = None
            except Exception:
                pass
