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

from src.ui.app import MidGuitarApp

def main():
    print("Iniciando MidGuitar...")
    app = MidGuitarApp()
    app.mainloop()

if __name__ == "__main__":
    main()
