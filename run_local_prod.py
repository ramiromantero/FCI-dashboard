"""
RUN_LOCAL_PROD.PY — Correr el dashboard en modo prod DESDE Windows
====================================================================
Workaround para los 2 problemas tipicos:
  1. Gunicorn no soporta Windows (usa fork/syscalls POSIX)
  2. Politicas corporativas tipo EY bloquean .exe nuevos de pip

Este script usa waitress (WSGI server puro Python) directo por import,
sin invocar ejecutables, asi que pasa la policy de Windows App Control.

Uso:
    conda activate dash-panel
    pip install waitress  # si no esta ya
    python run_local_prod.py

Equivalente a lo que corre en Render (pero con waitress en vez de gunicorn).
"""

import os
from waitress import serve

from app import server

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"🚀 Dashboard prod en http://{host}:{port} (waitress)")
    serve(server, host=host, port=port, threads=8)
