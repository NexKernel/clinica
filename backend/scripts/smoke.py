"""Prueba de humo: levanta la aplicación entera y recorre el camino crítico.

Se corre antes de subir un cambio. En unos segundos dice si la app arranca, si
el sembrado dejó la base utilizable y si el login sigue funcionando; es lo que
separa un push de un 502 delante del cliente.

Trabaja sobre una sqlite temporal que borra al terminar, así que no toca ningún
dato real ni necesita Postgres levantado. El tramo de `migrations.py` que es SQL
exclusivo de Postgres queda registrado como fallo y no se tiene en cuenta.

    cd backend
    python scripts/smoke.py          # silencioso salvo que algo falle

Devuelve 0 si todo pasa y 1 si no, para poder encadenarlo en un hook o en CI.
Necesita httpx (requirements-dev.txt); no es dependencia de la imagen.
"""

import logging
import os
import sys
import tempfile
from pathlib import Path

ADMIN_PASSWORD = "smoke-admin-1"


def _prepare_environment(database_path: Path) -> None:
    """Define el entorno antes de importar la app: Settings se cachea al importarse."""
    os.environ["DATABASE_URL"] = f"sqlite:///{database_path.as_posix()}"
    os.environ["FIRST_ADMIN_USERNAME"] = "admin"
    os.environ["FIRST_ADMIN_EMAIL"] = "admin@estabridis.pe"
    os.environ["FIRST_ADMIN_PASSWORD"] = ADMIN_PASSWORD
    os.environ["SECRET_KEY"] = "clave-solo-para-la-prueba-de-humo"


def _check(results: list[tuple[str, bool, str]], label: str, ok: bool, detail: str = "") -> None:
    results.append((label, ok, detail))


def _check_seeded(results: list[tuple[str, bool, str]]) -> None:
    """Confirma que el sembrado dejó datos, no solo que no explotó."""
    from app.db.session import SessionLocal
    from app.models import DocumentTemplate, MedicalService, Specialty

    with SessionLocal() as db:
        for label, model in (
            ("especialidades", Specialty),
            ("servicios del tarifario", MedicalService),
            ("plantillas de documentos", DocumentTemplate),
        ):
            total = db.query(model).count()
            _check(results, f"sembrado: {label}", total > 0, "la tabla quedó vacía")


def run() -> int:
    results: list[tuple[str, bool, str]] = []

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as workdir:
        _prepare_environment(Path(workdir) / "smoke.db")

        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from fastapi.testclient import TestClient

        from app.main import app

        # El lifespan corre init_db() de verdad: crear tablas, migrar y sembrar.
        with TestClient(app) as client:
            response = client.get("/health")
            _check(results, "health responde 200", response.status_code == 200)

            response = client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": ADMIN_PASSWORD},
            )
            ok = response.status_code == 200
            _check(results, "login de la cuenta de soporte", ok, response.text[:160])
            if not ok:
                return _report(results)

            headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

            response = client.get("/api/v1/users/me", headers=headers)
            _check(results, "perfil propio", response.status_code == 200, response.text[:160])

            response = client.get("/api/v1/users", headers=headers)
            ok = response.status_code == 200
            detail = response.text[:160]
            _check(results, "listado de usuarios", ok, detail)
            if ok:
                usuarios = [item["username"] for item in response.json()["items"]]
                _check(
                    results,
                    "la cuenta de soporte no se lista",
                    "admin" not in usuarios,
                    f"devolvió {usuarios}",
                )

            response = client.get("/api/v1/settings/public")
            _check(
                results,
                "configuración pública",
                response.status_code == 200,
                response.text[:160],
            )

            # El sembrado ya no aborta el arranque cuando un paso falla, así que
            # hay que mirar el resultado: una base vacía no se nota desde fuera.
            _check_seeded(results)

        # Suelta el fichero sqlite antes de borrar el directorio (Windows lo bloquea).
        from app.db.session import engine

        engine.dispose()

    return _report(results)


def _report(results: list[tuple[str, bool, str]]) -> int:
    fallos = [item for item in results if not item[1]]
    for label, ok, detail in results:
        if not ok:
            print(f"  FALLA  {label}" + (f" -> {detail}" if detail else ""))
    if fallos:
        print(f"\nPrueba de humo: {len(fallos)} de {len(results)} comprobaciones fallaron.")
        return 1
    print(f"Prueba de humo: {len(results)} comprobaciones, todo correcto.")
    return 0


if __name__ == "__main__":
    # El sembrado registra el tramo de Postgres como fallo; aquí solo estorba.
    logging.disable(logging.CRITICAL)
    raise SystemExit(run())
