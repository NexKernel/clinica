from fastapi import APIRouter

from app.api.v1.appointments.routes import router as appointments_router
from app.api.v1.audit.routes import router as audit_router
from app.api.v1.auth.routes import router as auth_router
from app.api.v1.catalog.routes import router as catalog_router
from app.api.v1.dashboard.routes import router as dashboard_router
from app.api.v1.documents.routes import router as documents_router
from app.api.v1.encounters.routes import router as encounters_router
from app.api.v1.inventory.routes import router as inventory_router
from app.api.v1.notifications.routes import router as notifications_router
from app.api.v1.patients.routes import router as patients_router
from app.api.v1.practitioners.routes import router as practitioners_router
from app.api.v1.purchases.routes import router as purchases_router
from app.api.v1.reminders.routes import router as reminders_router
from app.api.v1.roles.routes import router as roles_router
from app.api.v1.sales.routes import router as sales_router
from app.api.v1.settings.routes import router as settings_router
from app.api.v1.studies.routes import router as studies_router
from app.api.v1.users.management import router as users_admin_router
from app.api.v1.users.routes import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(roles_router)
api_router.include_router(settings_router)
api_router.include_router(audit_router)
# Las rutas propias (/users/me) se registran antes que /users/{user_id}.
api_router.include_router(users_router)
api_router.include_router(users_admin_router)

# Módulos clínicos y de operación
api_router.include_router(dashboard_router)
api_router.include_router(notifications_router)
api_router.include_router(catalog_router)
api_router.include_router(patients_router)
api_router.include_router(practitioners_router)
api_router.include_router(appointments_router)
api_router.include_router(encounters_router)
api_router.include_router(studies_router)
api_router.include_router(documents_router)
api_router.include_router(reminders_router)
api_router.include_router(inventory_router)
api_router.include_router(purchases_router)
api_router.include_router(sales_router)
