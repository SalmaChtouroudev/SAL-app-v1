from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_session, get_repository, require_company_access
from app.repositories.platform_repository import PlatformRepository
from app.schemas.auth import AuthSessionResponse
from app.schemas.platform import CompanyRead


router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("", response_model=list[CompanyRead])
def list_companies(
    session: AuthSessionResponse = Depends(get_current_session),
    repository: PlatformRepository = Depends(get_repository),
) -> list[CompanyRead]:
    return [
        company
        for company in repository.list_companies()
        if company.id in session.accessibleCompanyIds
    ]


@router.get("/{company_id}", response_model=CompanyRead)
def get_company(
    company_id: str,
    session: AuthSessionResponse = Depends(get_current_session),
    repository: PlatformRepository = Depends(get_repository),
) -> CompanyRead:
    require_company_access(session, company_id)
    company = repository.get_company(company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")
    return company
