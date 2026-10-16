from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_current_session,
    get_profile_service,
    get_repository,
    require_company_access,
    require_roles,
)
from app.repositories.platform_repository import PlatformRepository
from app.schemas.auth import AuthSessionResponse
from app.schemas.common import ApiMessage
from app.schemas.platform import (
    CurrentUserPasswordUpdate,
    CurrentUserProfileRead,
    CurrentUserProfileUpdate,
    UserRead,
    UserUpsert,
)
from app.services.profile_service import ProfileService


router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=CurrentUserProfileRead)
def get_current_user_profile(
    session: AuthSessionResponse = Depends(get_current_session),
    profile_service: ProfileService = Depends(get_profile_service),
) -> CurrentUserProfileRead:
    try:
        return profile_service.get_profile(session.userId)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("/me", response_model=CurrentUserProfileRead)
def update_current_user_profile(
    payload: CurrentUserProfileUpdate,
    session: AuthSessionResponse = Depends(get_current_session),
    profile_service: ProfileService = Depends(get_profile_service),
) -> CurrentUserProfileRead:
    try:
        return profile_service.update_profile(session.userId, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("/me/password", response_model=ApiMessage)
def update_current_user_password(
    payload: CurrentUserPasswordUpdate,
    session: AuthSessionResponse = Depends(get_current_session),
    profile_service: ProfileService = Depends(get_profile_service),
) -> ApiMessage:
    try:
        return profile_service.change_password(session.userId, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=list[UserRead])
def list_users(
    session: AuthSessionResponse = Depends(get_current_session),
    repository: PlatformRepository = Depends(get_repository),
) -> list[UserRead]:
    require_roles(session, {"SAL_ADMIN", "ENT_ADMIN"})
    if session.roleType == "SAL_ADMIN":
        return repository.list_users()

    return [
        user
        for user in repository.list_users()
        if session.enterpriseId in user.companyIds or user.primaryCompanyId == session.enterpriseId
    ]


@router.post("", response_model=UserRead)
def create_user(
    payload: UserUpsert,
    session: AuthSessionResponse = Depends(get_current_session),
    repository: PlatformRepository = Depends(get_repository),
) -> UserRead:
    require_roles(session, {"SAL_ADMIN", "ENT_ADMIN"})
    if repository.get_user_by_email(payload.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists.")

    if session.roleType != "SAL_ADMIN":
        if payload.roleType == "SAL_ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only SAL administrators can create SAL admin accounts.",
            )
        payload = payload.model_copy(update={"primaryCompanyId": session.enterpriseId})

    require_company_access(session, payload.primaryCompanyId)
    return repository.create_user(payload)


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: str,
    payload: UserUpsert,
    session: AuthSessionResponse = Depends(get_current_session),
    repository: PlatformRepository = Depends(get_repository),
) -> UserRead:
    require_roles(session, {"SAL_ADMIN", "ENT_ADMIN"})
    existing_user = next((user for user in repository.list_users() if user.id == user_id), None)
    if existing_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if session.roleType != "SAL_ADMIN":
        if existing_user.roleType == "SAL_ADMIN" or existing_user.primaryCompanyId != session.enterpriseId:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot modify this user.",
            )
        if payload.roleType == "SAL_ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only SAL administrators can assign SAL admin role.",
            )
        payload = payload.model_copy(update={"primaryCompanyId": session.enterpriseId})

    duplicate_user = repository.get_user_by_email(payload.email)
    if duplicate_user and duplicate_user.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists.")

    require_company_access(session, payload.primaryCompanyId)
    updated_user = repository.update_user(user_id, payload)
    if updated_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return updated_user


@router.delete("/{user_id}", response_model=ApiMessage)
def delete_user(
    user_id: str,
    session: AuthSessionResponse = Depends(get_current_session),
    repository: PlatformRepository = Depends(get_repository),
) -> ApiMessage:
    require_roles(session, {"SAL_ADMIN", "ENT_ADMIN"})
    if user_id == session.userId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete the currently authenticated account.",
        )

    existing_user = next((user for user in repository.list_users() if user.id == user_id), None)
    if existing_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if session.roleType != "SAL_ADMIN":
        if existing_user.roleType == "SAL_ADMIN" or existing_user.primaryCompanyId != session.enterpriseId:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot delete this user.",
            )

    repository.delete_user(user_id)
    return ApiMessage(status="DELETED", message=f"User {user_id} deleted.")
