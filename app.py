"""
APP.PY - Entry point para producción (Render / Railway / cualquier PaaS con gunicorn)
======================================================================================

Este archivo es un wrapper finito sobre el dashboard que:
  1. Importa la app de Dash desde `dashboard/dashboard_fci.py`
  2. Expone `server` (el WSGI Flask interno) para que gunicorn lo tome
  3. Si se corre directo (python app.py), lanza en modo producción
     leyendo el PORT de variables de entorno

En prod (Render/Railway) se corre con:
    gunicorn app:server --workers 2 --timeout 120

En dev local seguí usando:
    python dashboard/dashboard_fci.py
"""

import os
import sys
from pathlib import Path

# Permite importar el paquete dashboard/ como módulo
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "dashboard"))

# Importa la app Dash ya configurada (carga datos al bootear)
from dashboard.dashboard_fci import app  # noqa: E402

# Flask WSGI instance que gunicorn necesita
server = app.server

# Algunas buenas prácticas de prod
app.enable_dev_tools(debug=False)


if __name__ == "__main__":
    # Modo "standalone" de prod (sin gunicorn) — útil para probar local con vars de env
    port = int(os.environ.get("PORT", 8050))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"🚀 Dashboard prod en http://{host}:{port}")
    app.run(debug=False, host=host, port=port)
