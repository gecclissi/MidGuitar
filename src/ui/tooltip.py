"""
Sistema Universal de Dicas Flutuantes (Tooltips).
Exibe dicas imediatas ao passar o mouse sobre qualquer botão ou controle.
"""

import tkinter as tk

class ToolTip:
    def __init__(self, widget, text: str, delay_ms: int = 250):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.tip_window = None
        self._after_id = None

        # Vincula eventos no widget
        try:
            self.widget.bind("<Enter>", self._on_enter, add="+")
            self.widget.bind("<Leave>", self._on_leave, add="+")
            self.widget.bind("<ButtonPress>", self._on_leave, add="+")
        except Exception:
            pass

    def _on_enter(self, event=None):
        self._cancel()
        try:
            self._after_id = self.widget.after(self.delay_ms, self._show_tip)
        except Exception:
            pass

    def _on_leave(self, event=None):
        self._cancel()
        self._hide_tip()

    def _cancel(self):
        if self._after_id:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _show_tip(self):
        if self.tip_window or not self.text:
            return
        try:
            # Posição logo abaixo do mouse ou do widget
            x = self.widget.winfo_rootx() + 15
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6

            self.tip_window = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.attributes("-topmost", True)
            tw.wm_geometry(f"+{x}+{y}")

            # Container com borda elegante e cor contrastante
            frame = tk.Frame(tw, background="#38BDF8", padx=1, pady=1)
            frame.pack()

            label = tk.Label(
                frame,
                text=self.text,
                justify="left",
                background="#0F172A",
                foreground="#F8FAFC",
                font=("Segoe UI", 9, "bold"),
                padx=8,
                pady=4
            )
            label.pack()
        except Exception:
            pass

    def _hide_tip(self):
        if self.tip_window:
            try:
                self.tip_window.destroy()
            except Exception:
                pass
            self.tip_window = None

def set_tooltip(widget, text: str):
    """Adiciona dica flutuante ao passar o mouse sobre o widget (suporta CustomTkinter)."""
    if not widget or not text:
        return
    ToolTip(widget, text)
    # Suporte a widgets CustomTkinter que usam componentes internos
    for attr in ("_canvas", "_entry", "_label", "_textbox"):
        if hasattr(widget, attr):
            inner = getattr(widget, attr)
            if inner:
                ToolTip(inner, text)
