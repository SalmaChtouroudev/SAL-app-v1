from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_session, get_repository, require_company_access
from app.repositories.platform_repository import PlatformRepository
from app.schemas.auth import AuthSessionResponse
from app.schemas.platform import AuditLogCreate, AuditLogRead


router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogRead])
def list_audit_logs(
    company_id: str | None = None,
    session: AuthSessionResponse = Depends(get_current_session),
    repository: PlatformRepository = Depends(get_repository),
) -> list[AuditLogRead]:
    scoped_company_id = company_id or session.enterpriseId
    require_company_access(session, scoped_company_id)
    return repository.list_audit_logs(scoped_company_id)


@router.post("", response_model=AuditLogRead)
def create_audit_log(
    payload: AuditLogCreate,
    session: AuthSessionResponse = Depends(get_current_session),
    repository: PlatformRepository = Depends(get_repository),
) -> AuditLogRead:
    require_company_access(session, payload.enterpriseId)
    safe_payload = payload.model_copy(update={"userId": session.userId})
    return repository.create_audit_log(safe_payload)
