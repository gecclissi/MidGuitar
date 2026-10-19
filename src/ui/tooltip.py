"""
Sistema Universal de Dicas Flutuantes (Tooltips).
Exibe dicas imediatas ao passar o mouse sobre qualquer botão ou controle,
sem sobreposição ou duplicação de janelas.
"""

import tkinter as tk

_CURRENT_ACTIVE_TOOLTIP = None

class ToolTip:
    def __init__(self, widget, text: str, delay_ms: int = 250):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.tip_window = None
        self._show_after_id = None
        self._hide_after_id = None
        self._is_inside = False

        # Registra eventos no widget principal e em seus componentes internos
        targets = [self.widget]
        for attr in ("_canvas", "_entry", "_label", "_textbox", "_text_label"):
            if hasattr(widget, attr):
                inner = getattr(widget, attr)
                if inner and inner not in targets:
                    targets.append(inner)

        for target in targets:
            try:
                target.bind("<Enter>", self._on_enter, add="+")
                target.bind("<Leave>", self._on_leave, add="+")
                target.bind("<ButtonPress>", self._on_click, add="+")
            except Exception:
                pass

    def _on_enter(self, event=None):
        self._is_inside = True
        # Cancela qualquer fechamento pendente
        if self._hide_after_id:
            try:
                self.widget.after_cancel(self._hide_after_id)
            except Exception:
                pass
            self._hide_after_id = None

        if not self.tip_window and not self._show_after_id:
            try:
                self._show_after_id = self.widget.after(self.delay_ms, self._show_tip)
            except Exception:
                pass

    def _on_leave(self, event=None):
        self._is_inside = False
        if self._show_after_id:
            try:
                self.widget.after_cancel(self._show_after_id)
            except Exception:
                pass
            self._show_after_id = None

        # Dá um pequeno delay de 60ms para checar se o mouse não foi para um componente interno
        if self._hide_after_id:
            try:
                self.widget.after_cancel(self._hide_after_id)
            except Exception:
                pass
        try:
            self._hide_after_id = self.widget.after(60, self._check_and_hide)
        except Exception:
            self._hide_tip()

    def _on_click(self, event=None):
        self._hide_tip()

    def _check_and_hide(self):
        self._hide_after_id = None
        if not self._is_inside:
            self._hide_tip()

    def _show_tip(self):
        global _CURRENT_ACTIVE_TOOLTIP
        self._show_after_id = None
        if not self._is_inside or not self.text:
            return

        # Fecha qualquer outro tooltip atualmente aberto na aplicação
        if _CURRENT_ACTIVE_TOOLTIP and _CURRENT_ACTIVE_TOOLTIP is not self:
            _CURRENT_ACTIVE_TOOLTIP._hide_tip()

        if self.tip_window:
            return

        try:
            # Posição logo abaixo do mouse ou do widget
            x = self.widget.winfo_rootx() + 15
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6

            screen_w = self.widget.winfo_screenwidth()
            est_width = len(self.text) * 8 + 30
            if x + est_width > screen_w:
                x = max(10, screen_w - est_width)

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
            _CURRENT_ACTIVE_TOOLTIP = self
        except Exception:
            pass

    def _hide_tip(self):
        global _CURRENT_ACTIVE_TOOLTIP
        if self._show_after_id:
            try:
                self.widget.after_cancel(self._show_after_id)
            except Exception:
                pass
            self._show_after_id = None

        if self.tip_window:
            try:
                self.tip_window.destroy()
            except Exception:
                pass
            self.tip_window = None

        if _CURRENT_ACTIVE_TOOLTIP is self:
            _CURRENT_ACTIVE_TOOLTIP = None


def set_tooltip(widget, text: str):
    """Adiciona ou atualiza a dica flutuante de um widget sem duplicar instâncias."""
    if not widget or not text:
        return
    # Se já existir um tooltip associado a este widget, apenas atualiza o texto
    if hasattr(widget, "_midguitar_tooltip") and widget._midguitar_tooltip:
        widget._midguitar_tooltip.text = text
        return
    tt = ToolTip(widget, text)
    widget._midguitar_tooltip = tt
