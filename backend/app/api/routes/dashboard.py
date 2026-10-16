from fastapi import APIRouter, Depends

from app.api.dependencies import (
    get_client_demo_analytics_service,
    get_current_session,
    get_dashboard_service,
    require_company_access,
)
from app.schemas.auth import AuthSessionResponse
from app.schemas.client_demo import ClientDemoDashboardOverview
from app.schemas.platform import DashboardOverviewResponse, DashboardSummaryResponse, DashboardTrendPoint
from app.services.client_demo_analytics import ClientDemoAnalyticsService
from app.services.dashboard_service import DashboardService


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


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


@router.get("/overview", response_model=DashboardOverviewResponse)
def get_overview(
    company_id: str,
    session: AuthSessionResponse = Depends(get_current_session),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
) -> DashboardOverviewResponse:
    require_company_access(session, company_id)
    return dashboard_service.get_overview(company_id)


@router.get("/client-demo", response_model=ClientDemoDashboardOverview)
def get_client_demo_overview(
    company_id: str,
    session: AuthSessionResponse = Depends(get_current_session),
    analytics_service: ClientDemoAnalyticsService = Depends(get_client_demo_analytics_service),
) -> ClientDemoDashboardOverview:
    require_company_access(session, company_id)
    return analytics_service.get_overview(company_id)
