"""
Componente de Linha do Tempo e Editor Visual de Notas (Mini-REAPER).
Permite visualizar, adicionar manualmente (clicando), deletar e editar notas
para Guitarra (5 botões), Baixo, Bateria e Teclado, com grid musical (BPM).
"""

import tkinter as tk
from typing import Callable, List, Optional
from src.creator.chart_model import ChartSong, NoteEvent

LANE_COLORS = {
    "green": "#22C55E",
    "red": "#EF4444",
    "yellow": "#FACC15",
    "blue": "#38BDF8",
    "orange": "#FB923C",
    "overdrive": "#A855F7",
    "solo": "#F59E0B"
}

LANE_NAMES_GUITAR = [
    ("green", "Verde (Casa 1)"),
    ("red", "Vermelha (Casa 2)"),
    ("yellow", "Amarela (Casa 3)"),
    ("blue", "Azul (Casa 4)"),
    ("orange", "Laranja (Casa 5)"),
    ("overdrive", "⭐ Overdrive"),
    ("solo", "⚡ Solo"),
]

LANE_NAMES_DRUMS = [
    ("orange", "Bumbo (Pedal Laranja)"),
    ("red", "Caixa (Pad Vermelho)"),
    ("yellow", "Chimbal (Amarelo)"),
    ("blue", "Tom / Condução (Azul)"),
    ("green", "Prato Ataque (Verde)"),
    ("overdrive", "⭐ Overdrive"),
    ("solo", "⚡ Preenchimento (Fill)"),
]

class MiniReaperCanvas(tk.Frame):
    def __init__(self, master, song: ChartSong, on_change_callback: Optional[Callable] = None, **kwargs):
        super().__init__(master, bg="#0B0F17", **kwargs)
        self.song = song
        self.on_change = on_change_callback

        self.current_track = "guitar"
        self.current_difficulty = "Expert"
        self.pixels_per_second = 80.0  # Zoom inicial
        self.lane_height = 28
        self.header_height = 24
        self.current_playhead_ms = 0
        self.snap_grid_division = 4    # 4 = 1/4 de tempo (semínima)
        self.default_sustain_ms = 180  # Duração padrão ao clicar

        self._build_widgets()

    def _build_widgets(self):
        # Frame do topo do canvas com régua e canvas com scrollbar horizontal
        self.canvas_frame = tk.Frame(self, bg="#0B0F17")
        self.canvas_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(
            self.canvas_frame,
            bg="#0B0F17",
            highlightthickness=0,
            cursor="crosshair"
        )
        self.h_scroll = tk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=self.h_scroll.set)

        self.h_scroll.pack(fill="x", side="bottom")
        self.canvas.pack(fill="both", expand=True, side="top")

        # Eventos do mouse no Canvas
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Button-3>", self._on_canvas_right_click)
        self.canvas.bind("<Configure>", lambda e: self.redraw())

        # Suporte a rolagem horizontal com rodinha do mouse (Shift + Wheel ou Wheel)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)

    def set_track(self, track_key: str):
        self.current_track = track_key
        self.redraw()

    def set_difficulty(self, diff: str):
        self.current_difficulty = diff
        self.redraw()

    def set_zoom(self, px_per_sec: float):
        self.pixels_per_second = max(20.0, min(400.0, px_per_sec))
        self.redraw()

    def set_sustain(self, ms: int):
        self.default_sustain_ms = max(50, ms)

    def set_playhead_time(self, ms: int):
        self.current_playhead_ms = ms
        self._update_playhead_only()

    def get_lanes(self):
        if self.current_track == "drum":
            return LANE_NAMES_DRUMS
        return LANE_NAMES_GUITAR

    def _get_notes(self) -> List[NoteEvent]:
        if self.current_track == "guitar":
            return self.song.guitar_notes
        elif self.current_track == "bass":
            return self.song.bass_notes
        elif self.current_track == "drum":
            return self.song.drum_notes
        elif self.current_track == "keys":
            return self.song.keys_notes
        return []

    def redraw(self):
        self.canvas.delete("all")
        lanes = self.get_lanes()
        total_lanes = len(lanes)
        total_height = self.header_height + total_lanes * self.lane_height

        # Duração total em segundos (mínimo 180s ou última nota + 10s)
        notes = self._get_notes()
        max_ms = 180000
        for n in notes:
            if n.time_ms + n.duration_ms > max_ms:
                max_ms = n.time_ms + n.duration_ms + 10000

        total_width = int((max_ms / 1000.0) * self.pixels_per_second) + 200
        self.canvas.configure(scrollregion=(0, 0, total_width, total_height))

        # 1. Desenha réguas e faixas das casas
        for i, (lane_key, lane_label) in enumerate(lanes):
            y_top = self.header_height + i * self.lane_height
            y_bot = y_top + self.lane_height
            bg_color = "#141B26" if i % 2 == 0 else "#0F141D"
            self.canvas.create_rectangle(0, y_top, total_width, y_bot, fill=bg_color, outline="#1E293B", width=1)

            # Rótulo da pista à esquerda (fixo visualmente via tag)
            self.canvas.create_text(
                12, y_top + self.lane_height / 2,
                text=lane_label,
                anchor="w",
                fill=LANE_COLORS.get(lane_key, "#94A3B8"),
                font=("Segoe UI", 9, "bold")
            )

        # 2. Grid musical baseado no BPM (Compassos e Tempos)
        bpm = max(20.0, self.song.bpm)
        beat_interval_sec = 60.0 / bpm
        measure_interval_sec = beat_interval_sec * 4.0

        current_t = 0.0
        measure_count = 1
        while current_t * 1000.0 <= max_ms:
            x = int(current_t * self.pixels_per_second)
            # Linha de compasso (mais grossa)
            self.canvas.create_line(x, self.header_height, x, total_height, fill="#334155", width=2)
            # Número do compasso no topo
            self.canvas.create_text(x + 4, self.header_height / 2, text=f"M{measure_count}", fill="#64748B", font=("Segoe UI", 8), anchor="w")

            # Linhas de tempos menores (subdivisões de batidas)
            for b in range(1, 4):
                bx = int((current_t + b * beat_interval_sec) * self.pixels_per_second)
                self.canvas.create_line(bx, self.header_height, bx, total_height, fill="#1E293B", width=1, dash=(2, 2))

            current_t += measure_interval_sec
            measure_count += 1

        # 3. Desenha as notas mapeadas
        for note in notes:
            if note.difficulty != self.current_difficulty and note.lane not in ["overdrive", "solo"]:
                continue

            # Acha o índice da pista
            lane_idx = -1
            for idx, (l_key, _) in enumerate(lanes):
                if l_key == note.lane:
                    lane_idx = idx
                    break
            if lane_idx == -1:
                continue

            y_top = self.header_height + lane_idx * self.lane_height + 3
            y_bot = y_top + self.lane_height - 6

            x_start = int((note.time_ms / 1000.0) * self.pixels_per_second)
            dur_px = max(10, int((note.duration_ms / 1000.0) * self.pixels_per_second))
            x_end = x_start + dur_px

            color = LANE_COLORS.get(note.lane, "#38BDF8")

            # Se for nota com sustain longo, desenha cauda estilosa
            if note.duration_ms > 200:
                y_mid = (y_top + y_bot) / 2
                self.canvas.create_line(x_start + 10, y_mid, x_end, y_mid, fill=color, width=4)
                self.canvas.create_line(x_end, y_top + 4, x_end, y_bot - 4, fill=color, width=2)

            # Cabeça da nota (botão colorido)
            tag_id = f"note_{id(note)}"
            self.canvas.create_rectangle(
                x_start, y_top, x_start + min(16, dur_px), y_bot,
                fill=color,
                outline="#FFFFFF" if note.lane in ["overdrive", "solo"] else "#0F172A",
                width=1,
                tags=("chart_note", tag_id)
            )

        # 4. Linha vermelha do Playhead (posição atual)
        self._draw_playhead(total_height)

    def _draw_playhead(self, total_height):
        self.canvas.delete("playhead")
        px = int((self.current_playhead_ms / 1000.0) * self.pixels_per_second)
        self.canvas.create_line(px, 0, px, total_height, fill="#EF4444", width=2, tags="playhead")
        self.canvas.create_polygon(
            px - 6, 0, px + 6, 0, px, 10,
            fill="#EF4444", tags="playhead"
        )

    def _update_playhead_only(self):
        lanes = self.get_lanes()
        total_height = self.header_height + len(lanes) * self.lane_height
        self._draw_playhead(total_height)

    def _on_canvas_click(self, event):
        """Clique esquerdo: insere nota na posição clicada."""
        # Coordenada absoluta no Canvas levando em conta a rolagem
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        if y < self.header_height:
            # Clicou na régua de tempo -> move o cursor do playhead!
            t_sec = x / self.pixels_per_second
            self.set_playhead_time(int(t_sec * 1000))
            return

        lanes = self.get_lanes()
        lane_idx = int((y - self.header_height) // self.lane_height)
        if 0 <= lane_idx < len(lanes):
            lane_key = lanes[lane_idx][0]
            # Calcula tempo em ms com snap ao beat
            time_sec = x / self.pixels_per_second
            bpm = max(20.0, self.song.bpm)
            beat_sec = 60.0 / bpm
            snap_step = beat_sec / self.snap_grid_division
            # Ajusta ao passo da grade mais próximo
            snapped_sec = round(time_sec / snap_step) * snap_step
            time_ms = max(0, int(snapped_sec * 1000))

            # Verifica se já existe uma nota muito perto nessa mesma pista para evitar duplicatas
            notes = self._get_notes()
            for n in list(notes):
                if n.lane == lane_key and abs(n.time_ms - time_ms) < 40:
                    # Se clicou exatamente em cima, remove (toggle rápido)
                    notes.remove(n)
                    self.redraw()
                    if self.on_change:
                        self.on_change()
                    return

            new_note = NoteEvent(
                time_ms=time_ms,
                lane=lane_key,
                duration_ms=self.default_sustain_ms,
                difficulty=self.current_difficulty
            )
            self.song.add_note(self.current_track, new_note)
            self.redraw()
            if self.on_change:
                self.on_change()

    def _on_canvas_right_click(self, event):
        """Clique direito: deleta a nota sob o cursor."""
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        lanes = self.get_lanes()
        lane_idx = int((y - self.header_height) // self.lane_height)
        if 0 <= lane_idx < len(lanes):
            lane_key = lanes[lane_idx][0]
            click_ms = (x / self.pixels_per_second) * 1000.0

            notes = self._get_notes()
            to_remove = None
            for n in notes:
                if n.lane == lane_key:
                    # Verifica se o clique está dentro do corpo ou cauda da nota
                    if n.time_ms - 50 <= click_ms <= n.time_ms + max(160, n.duration_ms) + 50:
                        to_remove = n
                        break
            if to_remove:
                notes.remove(to_remove)
                self.redraw()
                if self.on_change:
                    self.on_change()

    def _on_mousewheel(self, event):
        """Rolagem horizontal com a rodinha."""
        delta = -1 if event.delta < 0 else 1
        self.canvas.xview_scroll(delta * 2, "units")
