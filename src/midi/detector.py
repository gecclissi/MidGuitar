"""
Detector inteligente de dispositivos de entrada e saída:
- Portas MIDI In (MIDI Pro Adapter, interfaces USB-MIDI, etc.)
- Portas MIDI Out (Microsoft GS Wavetable Synth, loopMIDI, interfaces)
- Dispositivos Gamepad/Joystick (guitarras Rock Band / Guitar Hero USB diretas)
"""

import rtmidi
import pygame

ROCKBAND_KEYWORDS = [
    "midi pro adapter",
    "rock band",
    "harmonix",
    "mad catz",
    "pro adapter",
    "guitar",
    "mustang",
    "squier"
]

def get_midi_input_ports() -> list[str]:
    """Retorna a lista de nomes das portas MIDI de entrada disponíveis."""
    try:
        midi_in = rtmidi.MidiIn()
        ports = midi_in.get_ports()
        del midi_in
        return ports
    except Exception as e:
        print(f"[Detector] Erro ao listar portas MIDI IN: {e}")
        return []

def get_midi_output_ports() -> list[str]:
    """Retorna a lista de nomes das portas MIDI de saída disponíveis."""
    try:
        midi_out = rtmidi.MidiOut()
        ports = midi_out.get_ports()
        del midi_out
        return ports
    except Exception as e:
        print(f"[Detector] Erro ao listar portas MIDI OUT: {e}")
        return []

def get_gamepad_devices() -> list[tuple[int, str]]:
    """Retorna a lista de controles USB / Joysticks detectados pelo Windows."""
    try:
        if not pygame.get_init():
            pygame.init()
        if not pygame.joystick.get_init():
            pygame.joystick.init()
        
        count = pygame.joystick.get_count()
        devices = []
        for i in range(count):
            try:
                js = pygame.joystick.Joystick(i)
                devices.append((i, js.get_name()))
            except Exception:
                pass
        return devices
    except Exception as e:
        print(f"[Detector] Erro ao listar gamepads: {e}")
        return []

def find_rockband_midi_input() -> tuple[int, str] | None:
    """
    Busca automaticamente uma porta MIDI In correspondente ao Rock Band / MIDI Pro Adapter.
    Retorna (indice_da_porta, nome_da_porta) ou None.
    """
    ports = get_midi_input_ports()
    # 1. Procura específica por palavras-chave de Rock Band
    for i, port in enumerate(ports):
        port_lower = port.lower()
        if any(keyword in port_lower for keyword in ROCKBAND_KEYWORDS):
            return (i, port)
    
    # 2. Se houver apenas 1 porta USB MIDI genérica, assume como provável
    for i, port in enumerate(ports):
        port_lower = port.lower()
        if "usb" in port_lower or "midi" in port_lower:
            return (i, port)

    # 3. Se houver qualquer porta de entrada disponível, retorna a primeira como fallback
    if ports:
        return (0, ports[0])
        
    return None

def find_default_midi_output() -> tuple[int, str] | None:
    """
    Busca a porta de saída padrão (prioriza Microsoft GS Wavetable Synth ou loopMIDI).
    """
    ports = get_midi_output_ports()
    for i, port in enumerate(ports):
        if "wavetable" in port.lower() or "synth" in port.lower():
            return (i, port)
    for i, port in enumerate(ports):
        if "loopmidi" in port.lower() or "virtual" in port.lower():
            return (i, port)
    if ports:
        return (0, ports[0])
    return None
