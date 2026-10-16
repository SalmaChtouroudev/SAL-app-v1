from pydantic import BaseModel


class ApiMessage(BaseModel):
    status: str
    message: str


class ApiErrorResponse(BaseModel):
    status: str = "error"
    error: str
    detail: str


class HealthResponse(BaseModel):
    status: str
    appName: str
    environment: str
    mode: str


class ReadinessCheck(BaseModel):
    name: str
    status: str
    detail: str


class ReadinessResponse(BaseModel):
    status: str
    appName: str
    environment: str
    mode: str
    checks: list[ReadinessCheck]
