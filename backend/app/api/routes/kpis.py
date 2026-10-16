from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_current_session,
    get_dashboard_service,
    get_repository,
    require_company_access,
    require_roles,
)
from app.repositories.platform_repository import PlatformRepository
from app.schemas.auth import AuthSessionResponse
from app.schemas.platform import (
    DashboardSummaryResponse,
    DashboardTrendPoint,
    KpiDefinitionRead,
    KpiDefinitionUpsert,
)
from app.services.dashboard_service import DashboardService


router = APIRouter(prefix="/api/kpis", tags=["kpis"])


@router.get("/definitions", response_model=list[KpiDefinitionRead])
def list_definitions(
    company_id: str,
    session: AuthSessionResponse = Depends(get_current_session),
    repository: PlatformRepository = Depends(get_repository),
) -> list[KpiDefinitionRead]:
    require_company_access(session, company_id)
    return repository.list_kpi_definitions(company_id)


@router.post("/definitions", response_model=KpiDefinitionRead, status_code=status.HTTP_201_CREATED)
def create_definition(
    payload: KpiDefinitionUpsert,
    session: AuthSessionResponse = Depends(get_current_session),
    repository: PlatformRepository = Depends(get_repository),
) -> KpiDefinitionRead:
    require_roles(session, {"SAL_ADMIN", "ENT_ADMIN"})
    require_company_access(session, payload.companyId)
    return repository.create_kpi_definition(payload)


@router.put("/definitions/{kpi_id}", response_model=KpiDefinitionRead)
def update_definition(
    kpi_id: str,
    payload: KpiDefinitionUpsert,
    session: AuthSessionResponse = Depends(get_current_session),
    repository: PlatformRepository = Depends(get_repository),
) -> KpiDefinitionRead:
    require_roles(session, {"SAL_ADMIN", "ENT_ADMIN"})
    require_company_access(session, payload.companyId)
    updated_definition = repository.update_kpi_definition(kpi_id, payload)
    if updated_definition is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KPI definition not found.")
    return updated_definition


@router.delete("/definitions/{kpi_id}", response_model=dict[str, str])
def delete_definition(
    kpi_id: str,
    company_id: str,
    session: AuthSessionResponse = Depends(get_current_session),
    repository: PlatformRepository = Depends(get_repository),
) -> dict[str, str]:
    require_roles(session, {"SAL_ADMIN", "ENT_ADMIN"})
    require_company_access(session, company_id)
    if not repository.delete_kpi_definition(kpi_id, company_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KPI definition not found.")
    return {"status": "DELETED"}


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_summary(
    company_id: str,
    session: AuthSessionResponse = Depends(get_current_session),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
) -> DashboardSummaryResponse:
    require_company_access(session, company_id)
    return dashboard_service.get_summary(company_id)


@router.get("/trend", response_model=list[DashboardTrendPoint])
def get_trend(
    company_id: str,
    session: AuthSessionResponse = Depends(get_current_session),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
) -> list[DashboardTrendPoint]:
    require_company_access(session, company_id)
    return dashboard_service.get_trend(company_id)
