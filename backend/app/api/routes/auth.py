from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_auth_service, get_current_session
from app.schemas.auth import AuthSessionResponse, LoginRequest
from app.services.auth_service import AuthService


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=AuthSessionResponse)
def login(payload: LoginRequest, auth_service: AuthService = Depends(get_auth_service)) -> AuthSessionResponse:
    try:
        return auth_service.authenticate(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.get("/session", response_model=AuthSessionResponse)
def current_session(session: AuthSessionResponse = Depends(get_current_session)) -> AuthSessionResponse:
    return session
