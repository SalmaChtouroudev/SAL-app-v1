from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_session, get_repository, require_company_access, require_roles
from app.repositories.platform_repository import PlatformRepository
from app.schemas.auth import AuthSessionResponse
from app.schemas.common import ApiMessage
from app.schemas.platform import DecisionRuleCreate, DecisionRuleRead


router = APIRouter(prefix="/api/decision-rules", tags=["decision-rules"])


@router.get("", response_model=list[DecisionRuleRead])
def list_rules(
    company_id: str | None = None,
    session: AuthSessionResponse = Depends(get_current_session),
    repository: PlatformRepository = Depends(get_repository),
) -> list[DecisionRuleRead]:
    scoped_company_id = company_id or session.enterpriseId
    require_company_access(session, scoped_company_id)
    return repository.list_rules(scoped_company_id)


@router.post("", response_model=DecisionRuleRead)
def create_rule(
    payload: DecisionRuleCreate,
    session: AuthSessionResponse = Depends(get_current_session),
    repository: PlatformRepository = Depends(get_repository),
) -> DecisionRuleRead:
    require_roles(session, {"SAL_ADMIN", "ENT_ADMIN"})
    if payload.companyId is None and session.roleType != "SAL_ADMIN":
        payload = payload.model_copy(update={"companyId": session.enterpriseId})

    if payload.companyId is not None:
        require_company_access(session, payload.companyId)

    return repository.create_rule(payload)


@router.put("/{rule_id}", response_model=DecisionRuleRead)
def update_rule(
    rule_id: str,
    payload: DecisionRuleCreate,
    session: AuthSessionResponse = Depends(get_current_session),
    repository: PlatformRepository = Depends(get_repository),
) -> DecisionRuleRead:
    require_roles(session, {"SAL_ADMIN", "ENT_ADMIN"})
    existing_rule = next(
        (
            rule
            for company_id in session.accessibleCompanyIds
            for rule in repository.list_rules(company_id)
            if rule.id == rule_id
        ),
        None,
    )
    if existing_rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found.")

    if existing_rule.companyId is None and session.roleType != "SAL_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SAL administrators can modify global rules.",
        )

    if payload.companyId is None and session.roleType != "SAL_ADMIN":
        payload = payload.model_copy(update={"companyId": session.enterpriseId})

    if payload.companyId is not None:
        require_company_access(session, payload.companyId)

    updated_rule = repository.update_rule(rule_id, payload)
    if updated_rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found.")
    return updated_rule


@router.delete("/{rule_id}", response_model=ApiMessage)
def delete_rule(
    rule_id: str,
    session: AuthSessionResponse = Depends(get_current_session),
    repository: PlatformRepository = Depends(get_repository),
) -> ApiMessage:
    require_roles(session, {"SAL_ADMIN", "ENT_ADMIN"})
    existing_rule = next(
        (
            rule
            for company_id in session.accessibleCompanyIds
            for rule in repository.list_rules(company_id)
            if rule.id == rule_id
        ),
        None,
    )
    if existing_rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found.")

    if existing_rule.companyId is None and session.roleType != "SAL_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SAL administrators can delete global rules.",
        )

    repository.delete_rule(rule_id)
    return ApiMessage(status="DELETED", message=f"Decision rule {rule_id} deleted.")
