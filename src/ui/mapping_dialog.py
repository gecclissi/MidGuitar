"""
Janela Interativa de Edição e Validação de Mapeamentos (Casas, Acordes e Bateria).
Permite alterar as notas/sons de cada controle e testar com áudio em tempo real!
"""

import customtkinter as ctk
import os
import json
from src.utils.instruments import (
    NOTE_NAMES, CHORD_INTERVALS, GM_DRUM_SOUNDS, GM_DRUM_NAMES,
    name_to_midi_note, build_chord_notes, midi_note_to_name
)
from src.utils.config_manager import get_presets_dirs, save_config

class MappingDialog(ctk.CTkToplevel):
    def __init__(self, master, current_preset: dict, audio_engine, on_save_callback=None, **kwargs):
        super().__init__(master, **kwargs)

        self.title("Editor de Mapeamento de Sons e Casas")
        self.geometry("640x560")
        self.minsize(580, 500)
        self.resizable(False, False)

        self.audio = audio_engine
        self.preset = json.loads(json.dumps(current_preset)) # cópia profunda
        self.on_save_callback = on_save_callback

        # Mantém no topo
        self.attributes("-topmost", True)
        self.after(100, lambda: self.focus_force())

        self._build_ui()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="#0F172A", height=50, corner_radius=0)
        header.pack(fill="x")

        title = ctk.CTkLabel(
            header, text="🎛️ Personalizador de Sons e Acordes",
            font=ctk.CTkFont(size=16, weight="bold"), text_color="#38BDF8"
        )
        title.pack(side="left", padx=16, pady=12)

        # Tabs: Guitarra vs Bateria
        self.tabview = ctk.CTkTabview(self, fg_color="#1E293B", corner_radius=8)
        self.tabview.pack(fill="both", expand=True, padx=16, pady=10)

        self.tab_guitar = self.tabview.add("🎸 Casas da Guitarra (5 Botões)")
        self.tab_drums = self.tabview.add("🥁 Pads da Bateria")

        self._build_guitar_tab()
        self._build_drums_tab()

        # Rodapé: Salvar
        footer = ctk.CTkFrame(self, fg_color="#0F172A", height=60, corner_radius=0)
        footer.pack(fill="x", side="bottom")

        btn_save = ctk.CTkButton(
            footer, text="💾 Salvar Alterações", width=140, height=32,
            fg_color="#10B981", hover_color="#059669", font=ctk.CTkFont(weight="bold"),
            command=self._save_changes
        )
        btn_save.pack(side="right", padx=16, pady=12)

        btn_cancel = ctk.CTkButton(
            footer, text="Cancelar", width=90, height=32,
            fg_color="#475569", hover_color="#334155",
            command=self.destroy
        )
        btn_cancel.pack(side="right", padx=6, pady=12)

    # -------------------------------------------------------------
    # TAB GUITARRA
    # -------------------------------------------------------------
    def _build_guitar_tab(self):
        tab = self.tab_guitar

        # Seletor de Casa
        row1 = ctk.CTkFrame(tab, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(row1, text="Escolha a Casa / Controle:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=4)
        self.fret_select = ctk.CTkComboBox(
            row1, width=220,
            values=["green (Verde)", "red (Vermelho)", "yellow (Amarelo)", "blue (Azul)", "orange (Laranja)", "open_strum (Palhetada Aberta)"],
            command=self._on_fret_selection_changed
        )
        self.fret_select.pack(side="left", padx=8)

        # Parâmetros de Acorde
        box_chord = ctk.CTkFrame(tab, fg_color="#0F172A", corner_radius=8)
        box_chord.pack(fill="x", padx=10, pady=8)

        # Nota Fundamental (Tônica) e Oitava
        r_note = ctk.CTkFrame(box_chord, fg_color="transparent")
        r_note.pack(fill="x", padx=12, pady=10)

        ctk.CTkLabel(r_note, text="Nota Fundamental:").pack(side="left", padx=4)
        self.root_note_combo = ctk.CTkComboBox(r_note, width=80, values=NOTE_NAMES, command=self._update_guitar_preview)
        self.root_note_combo.pack(side="left", padx=6)
        self.root_note_combo.set("E")

        ctk.CTkLabel(r_note, text="Oitava:").pack(side="left", padx=(12, 4))
        self.octave_combo = ctk.CTkComboBox(r_note, width=70, values=["1", "2", "3", "4", "5", "6"], command=self._update_guitar_preview)
        self.octave_combo.pack(side="left", padx=6)
        self.octave_combo.set("3")

        # Tipo de Acorde
        r_type = ctk.CTkFrame(box_chord, fg_color="transparent")
        r_type.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkLabel(r_type, text="Tipo de Acorde:").pack(side="left", padx=4)
        chord_names = list(CHORD_INTERVALS.keys())
        self.chord_type_combo = ctk.CTkComboBox(r_type, width=220, values=chord_names, command=self._update_guitar_preview)
        self.chord_type_combo.pack(side="left", padx=6)
        self.chord_type_combo.set("Power Chord (5ª)")

        # Preview e Teste de Som
        p_frame = ctk.CTkFrame(tab, fg_color="#1E293B", corner_radius=8, border_width=1, border_color="#334155")
        p_frame.pack(fill="x", padx=10, pady=10)

        self.guitar_preview_lbl = ctk.CTkLabel(
            p_frame, text="Notas resultantes: --", font=ctk.CTkFont(size=13, weight="bold"), text_color="#38BDF8"
        )
        self.guitar_preview_lbl.pack(pady=(10, 6))

        btn_test_guitar = ctk.CTkButton(
            p_frame, text="🔊 Ouvir / Testar Som", width=180, height=34,
            fg_color="#3B82F6", hover_color="#2563EB", font=ctk.CTkFont(weight="bold"),
            command=self._test_guitar_sound
        )
        btn_test_guitar.pack(pady=(4, 10))

        btn_apply_fret = ctk.CTkButton(
            tab, text="✔ Aplicar a Esta Casa", width=160, height=30,
            fg_color="#334155", hover_color="#475569", command=self._apply_to_fret
        )
        btn_apply_fret.pack(pady=4)

        self._on_fret_selection_changed(self.fret_select.get())

    def _on_fret_selection_changed(self, selection: str):
        fret_key = selection.split(" ")[0]
        frets = self.preset.get("frets", {})
        fret_cfg = frets.get(fret_key, {})

        notes = fret_cfg.get("notes", [52])
        if notes:
            root_midi = notes[0]
            name = NOTE_NAMES[root_midi % 12]
            octave = (root_midi // 12) - 1
            self.root_note_combo.set(name)
            self.octave_combo.set(str(max(1, min(6, octave))))

        self._update_guitar_preview()

    def _update_guitar_preview(self, *args):
        root = self.root_note_combo.get()
        octave = int(self.octave_combo.get())
        ctype = self.chord_type_combo.get()

        root_midi = name_to_midi_note(root, octave)
        chord_notes = build_chord_notes(root_midi, ctype)
        names = [midi_note_to_name(n) for n in chord_notes]

        self.current_guitar_notes = chord_notes
        self.guitar_preview_lbl.configure(text=f"Notas resultantes: {' + '.join(names)} ({chord_notes})")

    def _test_guitar_sound(self):
        if hasattr(self, 'current_guitar_notes') and self.current_guitar_notes:
            self.audio.play_chord(self.current_guitar_notes, velocity=115)
            self.after(500, lambda: self.audio.stop_chord(self.current_guitar_notes))

    def _apply_to_fret(self):
        fret_key = self.fret_select.get().split(" ")[0]
        if "frets" not in self.preset:
            self.preset["frets"] = {}
        
        root = self.root_note_combo.get()
        ctype = self.chord_type_combo.get()
        display_name = f"{root} ({ctype})"

        self.preset["frets"][fret_key] = {
            "name": display_name,
            "notes": self.current_guitar_notes
        }
        self.guitar_preview_lbl.configure(text=f"✔ Salvo para {fret_key.upper()}: {display_name}")

    # -------------------------------------------------------------
    # TAB BATERIA
    # -------------------------------------------------------------
    def _build_drums_tab(self):
        tab = self.tab_drums

        row1 = ctk.CTkFrame(tab, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(row1, text="Escolha o Pad de Bateria:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=4)
        self.pad_select = ctk.CTkComboBox(
            row1, width=220,
            values=["kick (Bumbo)", "snare (Caixa)", "hihat (Chimbal)", "tom1 (Tom 1)", "tom2 (Surdo)", "crash (Prato)"],
            command=self._on_pad_selection_changed
        )
        self.pad_select.pack(side="left", padx=8)

        # Escolha do som de percussão
        box_drum = ctk.CTkFrame(tab, fg_color="#0F172A", corner_radius=8)
        box_drum.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(box_drum, text="Som de Percussão General MIDI (Canal 10):", font=ctk.CTkFont(weight="bold")).pack(padx=12, pady=(10, 4), anchor="w")
        drum_sound_options = [f"{note} - {name}" for note, name in GM_DRUM_SOUNDS]
        self.drum_sound_combo = ctk.CTkComboBox(
            box_drum, width=380, values=drum_sound_options, command=self._on_drum_sound_selected
        )
        self.drum_sound_combo.pack(padx=12, pady=(0, 12), fill="x")

        # Preview e Teste
        p_frame = ctk.CTkFrame(tab, fg_color="#1E293B", corner_radius=8, border_width=1, border_color="#334155")
        p_frame.pack(fill="x", padx=10, pady=10)

        self.drum_preview_lbl = ctk.CTkLabel(
            p_frame, text="Som selecionado: Bumbo 1 (Nota 36)", font=ctk.CTkFont(size=13, weight="bold"), text_color="#F59E0B"
        )
        self.drum_preview_lbl.pack(pady=(10, 6))

        btn_test_drum = ctk.CTkButton(
            p_frame, text="🔊 Ouvir / Testar Som de Bateria", width=220, height=34,
            fg_color="#F59E0B", hover_color="#D97706", text_color="#0F172A", font=ctk.CTkFont(weight="bold"),
            command=self._test_drum_sound
        )
        btn_test_drum.pack(pady=(4, 10))

        btn_apply_pad = ctk.CTkButton(
            tab, text="✔ Aplicar a Este Pad", width=160, height=30,
            fg_color="#334155", hover_color="#475569", command=self._apply_to_pad
        )
        btn_apply_pad.pack(pady=4)

        self.current_drum_note = 36
        self._on_pad_selection_changed(self.pad_select.get())

    def _on_pad_selection_changed(self, selection: str):
        pad_id = selection.split(" ")[0]
        drum_mapping = self.preset.get("drum_mapping", {
            "kick": 36, "snare": 38, "hihat": 42, "tom1": 48, "tom2": 41, "crash": 49
        })
        note = drum_mapping.get(pad_id, 36)
        self.current_drum_note = note

        # Encontra no combo
        for opt in self.drum_sound_combo.cget("values"):
            if opt.startswith(f"{note} -"):
                self.drum_sound_combo.set(opt)
                break
        self.drum_preview_lbl.configure(text=f"Som selecionado: Nota {note} ({GM_DRUM_NAMES.get(note, '')})")

    def _on_drum_sound_selected(self, selection: str):
        try:
            note = int(selection.split(" - ")[0])
            self.current_drum_note = note
            self.drum_preview_lbl.configure(text=f"Som selecionado: Nota {note} ({GM_DRUM_NAMES.get(note, '')})")
        except Exception:
            pass

    def _test_drum_sound(self):
        # Canal 9 em zero-index = Canal 10 MIDI
        self.audio.play_note(self.current_drum_note, velocity=120, channel=9)
        self.after(200, lambda: self.audio.stop_note(self.current_drum_note, channel=9))

    def _apply_to_pad(self):
        pad_id = self.pad_select.get().split(" ")[0]
        if "drum_mapping" not in self.preset:
            self.preset["drum_mapping"] = {}
        self.preset["drum_mapping"][pad_id] = self.current_drum_note
        self.drum_preview_lbl.configure(text=f"✔ Salvo para Pad {pad_id.upper()}: Nota {self.current_drum_note}")

    # -------------------------------------------------------------
    # SALVAR
    # -------------------------------------------------------------
    def _save_changes(self):
        if self.on_save_callback:
            self.on_save_callback(self.preset)
        self.destroy()
