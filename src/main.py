"""
Ponto de entrada principal do MidGuitar.
Inicia a aplicação visual completa.
"""

import os
import sys

# Garante que a raiz do projeto esteja no sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def main():
    if "--selftest" in sys.argv:
        # Confere módulos, bibliotecas e arquivos do build sem abrir janela
        from src.selftest import run_selftest
        sys.exit(run_selftest())

    from src.ui.app import MidGuitarApp
    print("Iniciando MidGuitar...")
    app = MidGuitarApp()
    app.mainloop()

if __name__ == "__main__":
    main()
