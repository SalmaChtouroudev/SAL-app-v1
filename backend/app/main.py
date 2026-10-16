from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path
import tempfile

from sqlalchemy import text

from app.api.router import api_router
from app.core.config import get_settings
from app.db.bootstrap import initialize_database
from app.db.session import engine
from app.schemas.common import ApiErrorResponse, HealthResponse, ReadinessCheck, ReadinessResponse


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Integration-ready FastAPI backend for SAL - Business Decision Engine.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.on_event("startup")
def on_startup() -> None:
    initialize_database(settings)
    Path(settings.report_storage_dir).mkdir(parents=True, exist_ok=True)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    payload = ApiErrorResponse(error="http_error", detail=str(exc.detail))
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    payload = ApiErrorResponse(
        error="internal_server_error",
        detail=str(exc) if settings.debug else "An unexpected server error occurred.",
    )
    return JSONResponse(status_code=500, content=payload.model_dump())


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        appName=settings.app_name,
        environment=settings.app_env,
        mode="demo" if settings.use_demo_data else "database-ready",
    )


@app.get("/health/ready", response_model=ReadinessResponse, tags=["health"])
def health_ready() -> ReadinessResponse:
    checks: list[ReadinessCheck] = []

    storage_dir = Path(settings.report_storage_dir)
    try:
        storage_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=storage_dir, delete=True) as temp_file:
            temp_file.write(b"sal-ready")
            temp_file.flush()
        checks.append(
            ReadinessCheck(
                name="report_storage",
                status="ok",
                detail=f"Writable report storage at '{storage_dir}'.",
            )
        )
    except Exception as exc:
        checks.append(
            ReadinessCheck(
                name="report_storage",
                status="error",
                detail=f"Report storage is not writable: {exc}",
            )
        )

    if settings.use_demo_data:
        checks.append(
            ReadinessCheck(
                name="database",
                status="skipped",
                detail="Demo mode enabled; database connectivity check skipped.",
            )
        )
    else:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            checks.append(
                ReadinessCheck(
                    name="database",
                    status="ok",
                    detail="Database connection verified successfully.",
                )
            )
        except Exception as exc:
            checks.append(
                ReadinessCheck(
                    name="database",
                    status="error",
                    detail=f"Database connection failed: {exc}",
                )
            )

    overall_status = "ready" if all(check.status in {"ok", "skipped"} for check in checks) else "degraded"
    return ReadinessResponse(
        status=overall_status,
        appName=settings.app_name,
        environment=settings.app_env,
        mode="demo" if settings.use_demo_data else "database-ready",
        checks=checks,
    )
