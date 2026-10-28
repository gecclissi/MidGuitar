"""Parser mínimo de s-expressions do formato DTA do Rock Band."""
import re
from typing import Any, List, Union


class DtaSyntaxError(ValueError):
    """Erro de sintaxe no DTA; `line` é a linha (base 1) do problema."""

    def __init__(self, msg: str, line: int):
        super().__init__("%s (linha %d)" % (msg, line))
        self.msg = msg
        self.line = line


_OPEN = {"(": ")", "{": "}"}
_CLOSE = {")": "(", "}": "{"}
_DELIMS = set("(){};\"'") | set(" \t\r\n")


_INT_RE = re.compile(r"^[+-]?\d+$")
_FLOAT_RE = re.compile(r"^[+-]?(\d+\.\d*|\.\d+|\d+)([eE][+-]?\d+)?$")


def _atom(tok: str) -> Union[int, float, str]:
    """Número só se bater com regex estrita (sem inf, nan nem '_')."""
    if _INT_RE.match(tok):
        return int(tok)
    if _FLOAT_RE.match(tok) and ("." in tok or "e" in tok or "E" in tok):
        return float(tok)
    return tok


def _tokenize(text: str):
    """Gera (tipo, valor, linha); tipo em open/close/str/atom."""
    i, n, line = 0, len(text), 1
    while i < n:
        ch = text[i]
        if ch == "\n":
            line += 1
            i += 1
        elif ch in " \t\r":
            i += 1
        elif ch == ";":
            while i < n and text[i] != "\n":
                i += 1
        elif ch in _OPEN:
            yield ("open", ch, line, ch)
            i += 1
        elif ch in _CLOSE:
            yield ("close", ch, line, ch)
            i += 1
        elif ch in "\"'":
            start_line, j = line, i + 1
            while j < n and text[j] != ch:
                if text[j] == "\n":
                    line += 1
                j += 1
            if j >= n:
                raise DtaSyntaxError("Texto entre aspas não foi fechado", start_line)
            body = text[i + 1:j]
            yield ("str" if ch == '"' else "atom", body, start_line, body)
            i = j + 1
        else:
            j = i
            while j < n and text[j] not in _DELIMS:
                j += 1
            yield ("atom", _atom(text[i:j]), line, text[i:j])
            i = j


def parse_dta(text: str) -> List[Any]:
    """Converte o texto DTA em uma lista de s-expressions.

    Listas e `{ }` viram `list`; strings entre aspas viram `str`; símbolos e
    números viram `str`/`int`/`float`. Lança DtaSyntaxError se desbalanceado.
    """
    root: List[Any] = []
    stack = []  # (lista pai, delimitador de abertura, linha de abertura)
    cur = root
    for kind, val, line, raw in _tokenize(text):
        if kind == "open":
            new: List[Any] = []
            cur.append(new)
            stack.append((cur, val, line))
            cur = new
        elif kind == "close":
            if not stack:
                raise DtaSyntaxError("'%s' sem abertura correspondente" % val, line)
            parent, opener, _ = stack.pop()
            if opener != _CLOSE[val]:
                raise DtaSyntaxError("'%s' não fecha '%s'" % (val, opener), line)
            cur = parent
        else:
            # nome da entrada de topo fica com o texto bruto (ex.: shortname "007")
            if len(stack) == 1 and not cur and kind == "atom" and str(val) != raw:
                val = raw
            cur.append(val)
    if stack:
        _, opener, line = stack[-1]
        raise DtaSyntaxError("'%s' aberto e nunca fechado" % opener, line)
    return root
