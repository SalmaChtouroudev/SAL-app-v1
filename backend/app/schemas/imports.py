from typing import Any, Literal

from pydantic import BaseModel


ImportDetectedType = Literal["date", "number", "category", "text", "unknown"]
ImportAggregationLevel = Literal["day", "month", "year"]


class ImportMapping(BaseModel):
    date: str
    amount: str | None = None
    kind: str | None = None
    revenue: str | None = None
    cost: str | None = None
    category: str | None = None
    product: str | None = None
    client: str | None = None
    description: str | None = None


class AnalyzeImportResponse(BaseModel):
    file_name: str
    columns: list[str]
    rows: list[dict[str, Any]]
    preview_rows: list[dict[str, Any]]
    detected_types: dict[str, ImportDetectedType]
    suggestions: dict[str, str | None]
    row_count: int


class ValidationMessage(BaseModel):
    level: Literal["error", "warning"]
    message: str
    field: str | None = None


class ValidateImportRequest(BaseModel):
    mapping: ImportMapping
    rows: list[dict[str, Any]]
    file_name: str | None = None
    company_id: str | None = None


class ValidateImportResponse(BaseModel):
    valid: bool
    messages: list[ValidationMessage]
    normalized_preview: list[dict[str, Any]]


class ProcessImportRequest(BaseModel):
    company_id: str
    user_id: str
    file_name: str
    mapping: ImportMapping
    rows: list[dict[str, Any]]
    aggregation_level: ImportAggregationLevel
    mapping_profile_name: str | None = None


class ProcessImportResponse(BaseModel):
    import_batch_id: str
    persisted_rows: int
    aggregation_level: ImportAggregationLevel
    status: str
