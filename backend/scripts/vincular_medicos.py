"""Da de alta como profesional a los médicos que ya tenían usuario.

El alta automática de la ficha corrige a los usuarios que se crean o editan de
ahora en adelante, pero no a los que ya estaban: siguen sin figurar en la
agenda. Este script los pone al día una vez.

Es idempotente y no toca a nadie más: solo mira usuarios con perfil Médico que
no tengan ficha vinculada. Si encuentra una ficha suelta con el mismo nombre la
vincula, y si no, la crea.

    # dentro del contenedor del backend
    python scripts/vincular_medicos.py --simular   # muestra qué haría
    python scripts/vincular_medicos.py             # aplica los cambios
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal  # noqa: E402
from app.models import Practitioner, RoleCode, User  # noqa: E402
from app.repositories.practitioner_repository import PractitionerRepository  # noqa: E402


def main(simular: bool) -> int:
    with SessionLocal() as db:
        practitioners = PractitionerRepository(db)
        medicos = [
            user
            for user in db.query(User).filter(User.is_system.is_(False)).all()
            if user.role == RoleCode.MEDICO.value
        ]

        pendientes = [user for user in medicos if practitioners.get_by_user(user.id) is None]
        print(f"Médicos con usuario: {len(medicos)}. Sin ficha de profesional: {len(pendientes)}.")

        for user in pendientes:
            existente = practitioners.find_unlinked_by_name(user.full_name)
            accion = "vincular ficha existente" if existente else "crear ficha"
            print(f"  [{user.username}] {user.full_name}: {accion}")
            if simular:
                continue

            practitioner = existente or Practitioner(full_name=user.full_name, email=user.email)
            practitioner.user_id = user.id
            practitioner.is_active = user.is_active
            practitioners.save(practitioner)

        if simular and pendientes:
            print("\nSimulación: no se guardó nada. Repita sin --simular para aplicarlo.")
        elif pendientes:
            print(f"\nListo: {len(pendientes)} profesional(es) al día.")
        else:
            print("No hay nada que hacer.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--simular", action="store_true", help="muestra los cambios sin guardarlos"
    )
    raise SystemExit(main(parser.parse_args().simular))
