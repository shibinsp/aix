"""Admin API routes aggregation."""
from fastapi import APIRouter

from app.api.routes.admin.dashboard import router as dashboard_router
from app.api.routes.admin.users import router as users_router
from app.api.routes.admin.settings import router as settings_router
from app.api.routes.admin.audit import router as audit_router
from app.api.routes.admin.monitoring import router as monitoring_router

router = APIRouter(prefix="/admin", tags=["admin"])

router.include_router(dashboard_router)
router.include_router(users_router)
router.include_router(settings_router)
router.include_router(audit_router)
router.include_router(monitoring_router)
