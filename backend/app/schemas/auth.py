from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthSessionResponse(BaseModel):
    userId: str
    enterpriseId: str
    email: str
    fullName: str
    roleType: str
    token: str
    accessibleCompanyIds: list[str]
    permissions: list[str]
    issuedAt: int
    expiresAt: int
