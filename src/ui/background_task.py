"""
Execução de trabalhos pesados (exportação, importação de pacote, compilação de pacote)
fora da thread da interface, com uma janelinha de progresso.

A thread de trabalho NUNCA toca no Tk: ela só calcula o resultado. A thread da interface
consulta o resultado com `after()` e chama `on_success(resultado)` ou `on_error(exceção)`.

Nos testes (sem janela) use `run_sync`, que faz tudo na hora, na mesma thread.
"""

import queue
import threading
import traceback

POLL_MS = 100


def run_sync(owner, text, work, on_success, on_error):
    """Executa na hora, na thread atual (testes e objetos que não são janelas Tk)."""
    try:
        result = work()
    except Exception as exc:  # noqa: BLE001 - o erro sempre chega ao usuário por on_error
        traceback.print_exc()
        on_error(exc)
        return
    on_success(result)


def _set_buttons_state(widget, state, changed):
    """Desliga (ou religa) os botões da janela; `changed` guarda os que foram desligados."""
    try:
        children = widget.winfo_children()
    except Exception:
        return
    for child in children:
        cls = type(child).__name__
        if cls in ("CTkButton", "Button"):
            try:
                if state == "disabled":
                    if str(child.cget("state")) != "disabled":
                        child.configure(state="disabled")
                        changed.append(child)
                else:
                    child.configure(state="normal")
            except Exception:
                pass
        _set_buttons_state(child, state, changed)


class _ProgressWindow:
    """Janela modal pequena: barra indeterminada + texto."""

    def __init__(self, owner, text):
        import customtkinter as ctk
        self.win = ctk.CTkToplevel(owner)
        self.win.title("MidGuitar")
        self.win.geometry("380x120")
        self.win.resizable(False, False)
        self.win.transient(owner)
        # Fechar no X não interrompe o trabalho; só ignora o clique
        self.win.protocol("WM_DELETE_WINDOW", lambda: None)
        ctk.CTkLabel(self.win, text=text, font=ctk.CTkFont(size=13, weight="bold"),
                     wraplength=340).pack(pady=(18, 8), padx=16)
        self.bar = ctk.CTkProgressBar(self.win, mode="indeterminate", width=320)
        self.bar.pack(pady=(0, 16), padx=16)
        self.bar.start()
        try:
            self.win.after(50, self._grab)
        except Exception:
            pass

    def _grab(self):
        try:
            self.win.lift()
            self.win.grab_set()
        except Exception:
            pass

    def close(self):
        try:
            self.bar.stop()
            self.win.grab_release()
        except Exception:
            pass
        try:
            self.win.destroy()
        except Exception:
            pass


def run_with_progress(owner, text, work, on_success, on_error):
    """Roda `work()` numa thread e mostra o progresso até terminar."""
    if getattr(owner, "_background_busy", False):
        on_error(RuntimeError("Já existe uma operação em andamento. Aguarde ela terminar."))
        return
    owner._background_busy = True

    disabled = []
    _set_buttons_state(owner, "disabled", disabled)
    try:
        progress = _ProgressWindow(owner, text)
    except Exception:
        traceback.print_exc()
        progress = None

    results = queue.Queue()

    def _worker():
        try:
            results.put((True, work()))
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            results.put((False, exc))

    def _finish(ok, value):
        if progress is not None:
            progress.close()
        for btn in disabled:
            try:
                btn.configure(state="normal")
            except Exception:
                pass
        owner._background_busy = False
        try:
            if ok:
                on_success(value)
            else:
                on_error(value)
        except Exception as exc:  # erro ao mostrar o resultado também chega ao usuário
            traceback.print_exc()
            _report_unexpected(exc)

    def _poll():
        try:
            ok, value = results.get_nowait()
        except queue.Empty:
            owner.after(POLL_MS, _poll)
            return
        _finish(ok, value)

    threading.Thread(target=_worker, name="midguitar-task", daemon=True).start()
    owner.after(POLL_MS, _poll)


def _report_unexpected(exc):
    try:
        from tkinter import messagebox
        messagebox.showerror("Erro", f"Erro inesperado:\n{exc}")
    except Exception:
        pass
