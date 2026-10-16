from __future__ import annotations

from app.core.config import Settings
from app.core.security import create_access_token, decode_access_token, verify_password
from app.repositories.platform_repository import PlatformRepository
from app.schemas.auth import AuthSessionResponse, LoginRequest
from app.schemas.platform import AuditLogCreate


class AuthService:
    def __init__(self, repository: PlatformRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings

    def authenticate(self, payload: LoginRequest) -> AuthSessionResponse:
        user = self.repository.get_user_by_email(payload.email)
        if user is None or not verify_password(payload.password, user.password_hash):
            raise ValueError("Invalid email or password.")
        if user.status.lower() != "active":
            raise ValueError("This user account is not active.")

        self.repository.update_user_last_login(user.user_id)
        token, issued_at, expires_at = create_access_token(
            subject=user.user_id,
            settings=self.settings,
            claims={
                "enterpriseId": user.enterprise_id,
                "email": user.email,
                "fullName": user.full_name,
                "roleType": user.role_type,
                "accessibleCompanyIds": user.accessible_company_ids,
                "permissions": user.permissions,
            },
        )
        self.repository.create_audit_log(
            AuditLogCreate(
                enterpriseId=user.enterprise_id,
                userId=user.user_id,
                actionType="LOGIN",
                status="SUCCESS",
                description=f"User {user.full_name} authenticated successfully.",
            )
        )
        return AuthSessionResponse(
            userId=user.user_id,
            enterpriseId=user.enterprise_id,
            email=user.email,
            fullName=user.full_name,
            roleType=user.role_type,
            token=token,
            accessibleCompanyIds=list(user.accessible_company_ids),
            permissions=list(user.permissions),
            issuedAt=issued_at,
            expiresAt=expires_at,
        )

    def get_session_from_token(self, token: str) -> AuthSessionResponse:
        payload = decode_access_token(token, self.settings)
        user_id = str(payload.get("sub", ""))
        user = self.repository.get_user_by_id(user_id)
        if user is None:
            raise ValueError("Unknown session user.")

        return AuthSessionResponse(
            userId=user.user_id,
            enterpriseId=user.enterprise_id,
            email=user.email,
            fullName=user.full_name,
            roleType=user.role_type,
            token=token,
            accessibleCompanyIds=list(user.accessible_company_ids),
            permissions=list(user.permissions),
            issuedAt=int(payload.get("iat", 0)) * 1000,
            expiresAt=int(payload.get("exp", 0)) * 1000,
        )
