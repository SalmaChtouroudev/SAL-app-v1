from fastapi import APIRouter

from app.api.routes.alerts import router as alerts_router
from app.api.routes.audit import router as audit_router
from app.api.routes.auth import router as auth_router
from app.api.routes.companies import router as companies_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.imports import router as imports_router
from app.api.routes.kpis import router as kpis_router
from app.api.routes.reports import router as reports_router
from app.api.routes.rules import router as rules_router
from app.api.routes.users import router as users_router


api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(companies_router)
api_router.include_router(imports_router)
api_router.include_router(kpis_router)
api_router.include_router(dashboard_router)
api_router.include_router(alerts_router)
api_router.include_router(reports_router)
api_router.include_router(rules_router)
api_router.include_router(audit_router)
