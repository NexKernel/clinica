"""Catálogos iniciales del policlínico.

Se cargan una sola vez, al crear la base de datos, para que el sistema quede
operativo desde el primer día. El personal administrador puede editarlos,
desactivarlos o ampliarlos desde el módulo de configuración.
"""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.catalog import MedicalService, ServiceKind, Specialty

# (nombre, descripción, duración por defecto en minutos)
SPECIALTIES: tuple[tuple[str, str, int], ...] = (
    ("Medicina General", "Consulta médica ambulatoria", 20),
    ("Obstetricia", "Control prenatal y salud de la mujer", 30),
    ("Odontología", "Atención dental y profilaxis", 30),
    ("Pediatría", "Atención de niñas y niños", 20),
    ("Optometría", "Evaluación visual y medidas ópticas", 30),
    ("Laboratorio", "Toma de muestras y análisis clínicos", 15),
    ("Rayos X", "Estudios radiológicos", 20),
    ("Enfermería / Tópico", "Triaje, curaciones e inyectables", 15),
)

# (código, nombre, tipo, especialidad, precio, duración)
SERVICES: tuple[tuple[str, str, ServiceKind, str | None, str, int], ...] = (
    ("CON-GEN", "Consulta de medicina general", ServiceKind.CONSULTA, "Medicina General", "35.00", 20),
    ("CON-OBS", "Consulta obstétrica", ServiceKind.CONSULTA, "Obstetricia", "40.00", 30),
    ("CON-ODO", "Consulta odontológica", ServiceKind.CONSULTA, "Odontología", "40.00", 30),
    ("CON-PED", "Consulta pediátrica", ServiceKind.CONSULTA, "Pediatría", "40.00", 20),
    ("CON-OPT", "Evaluación optométrica", ServiceKind.CONSULTA, "Optometría", "30.00", 30),
    ("LAB-HEM", "Hemograma completo", ServiceKind.LABORATORIO, "Laboratorio", "25.00", 15),
    ("LAB-GLU", "Glucosa en ayunas", ServiceKind.LABORATORIO, "Laboratorio", "15.00", 15),
    ("RX-TOR", "Radiografía de tórax", ServiceKind.IMAGENES, "Rayos X", "60.00", 20),
    ("TOP-INY", "Aplicación de inyectable", ServiceKind.PROCEDIMIENTO, "Enfermería / Tópico", "10.00", 15),
    ("TOP-CUR", "Curación simple", ServiceKind.PROCEDIMIENTO, "Enfermería / Tópico", "20.00", 15),
)


def seed_catalog(db: Session) -> None:
    """Crea especialidades y tarifario base si aún no existen."""
    if db.execute(select(func.count(Specialty.id))).scalar_one() > 0:
        return

    specialties = {
        name: Specialty(name=name, description=description, default_duration_minutes=duration)
        for name, description, duration in SPECIALTIES
    }
    db.add_all(specialties.values())
    db.flush()

    db.add_all(
        MedicalService(
            code=code,
            name=name,
            kind=kind.value,
            specialty_id=specialties[specialty].id if specialty else None,
            price=Decimal(price),
            duration_minutes=duration,
        )
        for code, name, kind, specialty, price, duration in SERVICES
    )
    db.commit()
