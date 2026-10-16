from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.repositories.demo_repository import DemoPlatformRepository
from app.repositories.platform_repository import PlatformRepository
from app.repositories.sqlalchemy_repository import SqlAlchemyPlatformRepository
from app.services.auth_service import AuthService
from app.services.client_demo_analytics import ClientDemoAnalyticsService
from app.services.dashboard_service import DashboardService
from app.services.import_pipeline import ImportPipelineService
from app.services.profile_service import ProfileService
from app.services.report_service import ReportService


bearer_scheme = HTTPBearer(auto_error=False)
repository = DemoPlatformRepository()


def get_repository(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> PlatformRepository:
    if settings.use_demo_data:
        return repository
    return SqlAlchemyPlatformRepository(db)


def get_auth_service(
    settings: Settings = Depends(get_settings),
    platform_repository: PlatformRepository = Depends(get_repository),
) -> AuthService:
    return AuthService(platform_repository, settings)


def get_dashboard_service(
    platform_repository: PlatformRepository = Depends(get_repository),
) -> DashboardService:
    return DashboardService(platform_repository)


def get_client_demo_analytics_service(
    db: Session = Depends(get_db),
) -> ClientDemoAnalyticsService:
    return ClientDemoAnalyticsService(db)


def get_import_pipeline_service() -> ImportPipelineService:
    return ImportPipelineService()


def get_report_service(
    settings: Settings = Depends(get_settings),
    platform_repository: PlatformRepository = Depends(get_repository),
) -> ReportService:
    return ReportService(platform_repository, settings)


def get_profile_service(
    platform_repository: PlatformRepository = Depends(get_repository),
) -> ProfileService:
    return ProfileService(platform_repository)


def get_current_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )

    try:
        return auth_service.get_session_from_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


def require_company_access(session, company_id: str) -> None:
    if company_id not in session.accessibleCompanyIds:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access to company '{company_id}' is not allowed for this session.",
        )


def require_roles(session, allowed_roles: set[str]) -> None:
    if session.roleType not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{session.roleType}' is not allowed for this operation.",
        )
