#!/bin/sh
set -e

# Espera a Postgres antes de arrancar: en el primer deploy la app y la base
# levantan a la vez y create_all() fallaría en silencio (main.py atrapa el error
# para no impedir el arranque, así que un fallo aquí pasaría desapercibido).
# El host/puerto salen de DATABASE_URL si está definida, no se asume el host `db`.
python - <<'PY'
import os
import sys
import time
from urllib.parse import urlparse

url = os.getenv("DATABASE_URL")
if url:
    parsed = urlparse(url)
    host, port = parsed.hostname, parsed.port or 5432
else:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5432"))

if not host:
    print("[entrypoint] Sin host de base de datos; se continúa sin esperar.")
    sys.exit(0)

import socket

deadline = time.time() + 120
while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=3):
            print(f"[entrypoint] Base de datos disponible en {host}:{port}")
            sys.exit(0)
    except OSError:
        print(f"[entrypoint] Esperando a {host}:{port}...", flush=True)
        time.sleep(2)

print(f"[entrypoint] La base de datos {host}:{port} no respondió en 120s", file=sys.stderr)
sys.exit(1)
PY

exec "$@"
