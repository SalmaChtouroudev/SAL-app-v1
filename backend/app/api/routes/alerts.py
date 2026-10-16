from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_session, get_repository, require_company_access
from app.repositories.platform_repository import PlatformRepository
from app.schemas.auth import AuthSessionResponse
from app.schemas.common import ApiMessage
from app.schemas.platform import AuditLogCreate
from app.schemas.platform import AlertHistoryRead, AlertRead


router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertRead])
def list_alerts(
    company_id: str | None = None,
    session: AuthSessionResponse = Depends(get_current_session),
    repository: PlatformRepository = Depends(get_repository),
) -> list[AlertRead]:
    scoped_company_id = company_id or session.enterpriseId
    require_company_access(session, scoped_company_id)
    return repository.list_alerts(scoped_company_id)


@router.get("/history", response_model=list[AlertHistoryRead])
def list_alert_history(
    company_id: str,
    alert_id: str | None = None,
    session: AuthSessionResponse = Depends(get_current_session),
    repository: PlatformRepository = Depends(get_repository),
) -> list[AlertHistoryRead]:
    require_company_access(session, company_id)
    return repository.list_alert_history(company_id, alert_id)


@router.post("/{alert_id}/resolve", response_model=ApiMessage)
def resolve_alert(
    alert_id: str,
    session: AuthSessionResponse = Depends(get_current_session),
    repository: PlatformRepository = Depends(get_repository),
) -> ApiMessage:
    accessible_alert = next(
        (
            alert
            for company_id in session.accessibleCompanyIds
            for alert in repository.list_alerts(company_id)
            if alert.id == alert_id
        ),
        None,
    )
    if accessible_alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")

    repository.resolve_alert(alert_id, resolved_by_user_id=session.userId)
    repository.create_audit_log(
        AuditLogCreate(
            enterpriseId=accessible_alert.companyId,
            userId=session.userId,
            actionType="ALERT_RESOLVED",
            status="SUCCESS",
            description=f"Alert {alert_id} resolved from the alerts center.",
        )
    )
    return ApiMessage(status="ACKNOWLEDGED", message=f"Alert {alert_id} marked as resolved.")
