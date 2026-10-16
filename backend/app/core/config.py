from __future__ import annotations

import json
from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SAL Backend API"
    app_env: str = "development"
    debug: bool = False
    use_demo_data: bool = True
    bootstrap_sample_data: bool = True
    database_url: str = "postgresql+psycopg://sal:sal@localhost:5432/sal"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 480
    max_upload_bytes: int = 5 * 1024 * 1024
    report_storage_dir: str = "storage/reports"
    allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:4200",
            "http://127.0.0.1:4200",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
        ]
    )

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_prefix="SAL_",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def is_sqlite_database(self) -> bool:
        return self.database_url.strip().lower().startswith("sqlite")

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            normalized = value.strip()
            if normalized.startswith("["):
                try:
                    decoded = json.loads(normalized)
                except json.JSONDecodeError:
                    decoded = None
                if isinstance(decoded, list):
                    return [str(origin).strip() for origin in decoded if str(origin).strip()]
            return [origin.strip() for origin in normalized.split(",") if origin.strip()]
        return value

    @field_validator("access_token_minutes")
    @classmethod
    def validate_access_token_minutes(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("SAL_ACCESS_TOKEN_MINUTES must be greater than 0.")
        return value

    @field_validator("max_upload_bytes")
    @classmethod
    def validate_max_upload_bytes(cls, value: int) -> int:
        if value < 1024 * 1024:
            raise ValueError("SAL_MAX_UPLOAD_BYTES must be at least 1 MB.")
        return value

    @field_validator("report_storage_dir")
    @classmethod
    def validate_report_storage_dir(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("SAL_REPORT_STORAGE_DIR cannot be empty.")
        return normalized

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, value: str, info) -> str:
        app_env = str(info.data.get("app_env", "development")).lower()
        use_demo_data = bool(info.data.get("use_demo_data", True))
        normalized = value.strip()
        if not normalized:
            raise ValueError("SAL_JWT_SECRET cannot be empty.")

        insecure_default = normalized == "change-me" or len(normalized) < 24
        if insecure_default and (app_env == "production" or not use_demo_data):
            raise ValueError(
                "SAL_JWT_SECRET must be replaced with a strong secret outside demo mode."
            )

        return normalized


@lru_cache
def get_settings() -> Settings:
    return Settings()
