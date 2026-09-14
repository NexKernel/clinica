"""Ajustes de esquema sobre bases de datos ya creadas.

`Base.metadata.create_all` crea las tablas que faltan, pero no modifica las que
ya existen. Cuando un módulo gana una columna nueva después de una puesta en
producción, hay que añadirla explícitamente: esta lista lo hace al arrancar, de
forma idempotente, para que una instalación en marcha se actualice sola.

Es un puente deliberadamente simple. Si el esquema empieza a cambiar de formas
que no se resuelven agregando columnas opcionales (renombrados, cambios de tipo,
migración de datos), corresponde incorporar Alembic.
"""

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.models.patient import new_public_id

logger = logging.getLogger(__name__)

# (tabla, columna, definición SQL). Solo columnas opcionales: al agregarse, las
# filas existentes quedan en NULL sin romper la información ya registrada.
ADDED_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("products", "lot", "VARCHAR(40)"),
    ("products", "expiry_date", "DATE"),
    ("clinic_settings", "category", "VARCHAR(10)"),
    ("clinic_settings", "document_footer", "VARCHAR(255)"),
)


def apply_schema_updates(engine: Engine) -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    for table, column, definition in ADDED_COLUMNS:
        if table not in tables:
            continue  # la tabla se acaba de crear con la columna incluida
        existing = {info["name"] for info in inspector.get_columns(table)}
        if column in existing:
            continue

        with engine.begin() as connection:
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))
        logger.info("Columna agregada: %s.%s", table, column)

    _add_patient_public_id(engine, tables)


def _add_patient_public_id(engine: Engine, tables: set[str]) -> None:
    """Da identificador opaco a los pacientes registrados antes del cambio.

    No cabe en ADDED_COLUMNS porque la columna es obligatoria y única: hay que
    crearla libre, sortear un valor por fila y recién entonces exigirla.
    """
    if "patients" not in tables:
        return  # tabla recién creada, ya trae la columna

    inspector = inspect(engine)
    if "public_id" not in {info["name"] for info in inspector.get_columns("patients")}:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE patients ADD COLUMN public_id VARCHAR(32)"))
        logger.info("Columna agregada: patients.public_id")

    with engine.begin() as connection:
        pending = connection.execute(
            text("SELECT id FROM patients WHERE public_id IS NULL")
        ).scalars().all()
        for patient_id in pending:
            connection.execute(
                text("UPDATE patients SET public_id = :value WHERE id = :id"),
                {"value": new_public_id(), "id": patient_id},
            )
        if pending:
            logger.info("public_id asignado a %d paciente(s)", len(pending))

        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_patients_public_id "
                "ON patients (public_id)"
            )
        )
        connection.execute(text("ALTER TABLE patients ALTER COLUMN public_id SET NOT NULL"))
