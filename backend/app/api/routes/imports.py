from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.dependencies import (
    get_current_session,
    get_import_pipeline_service,
    get_repository,
    require_company_access,
    require_roles,
)
from app.core.config import Settings, get_settings
from app.repositories.platform_repository import PlatformRepository
from app.schemas.auth import AuthSessionResponse
from app.schemas.imports import (
    AnalyzeImportResponse,
    ProcessImportRequest,
    ProcessImportResponse,
    ValidateImportRequest,
    ValidateImportResponse,
)
from app.schemas.platform import ImportBatchRead
from app.services.import_pipeline import ImportPipelineService


router = APIRouter(prefix="/api/imports", tags=["imports"])


@router.get("/history", response_model=list[ImportBatchRead])
def list_import_history(
    company_id: str,
    session: AuthSessionResponse = Depends(get_current_session),
    repository: PlatformRepository = Depends(get_repository),
) -> list[ImportBatchRead]:
    require_company_access(session, company_id)
    return repository.list_import_batches(company_id)


@router.post("/analyze", response_model=AnalyzeImportResponse)
async def analyze_import(
    file: UploadFile = File(...),
    session: AuthSessionResponse = Depends(get_current_session),
    settings: Settings = Depends(get_settings),
    import_pipeline_service: ImportPipelineService = Depends(get_import_pipeline_service),
) -> AnalyzeImportResponse:
    require_roles(session, {"SAL_ADMIN", "ENT_ADMIN"})
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing file name.")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Uploaded file exceeds the {settings.max_upload_bytes} byte limit.",
        )

    try:
        return import_pipeline_service.analyze_file(file.filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/validate", response_model=ValidateImportResponse)
def validate_import(
    payload: ValidateImportRequest,
    session: AuthSessionResponse = Depends(get_current_session),
    import_pipeline_service: ImportPipelineService = Depends(get_import_pipeline_service),
) -> ValidateImportResponse:
    require_roles(session, {"SAL_ADMIN", "ENT_ADMIN"})
    return import_pipeline_service.validate_rows(
        payload.rows,
        payload.mapping,
        file_name=payload.file_name,
        company_id=payload.company_id,
    )


@router.post("/process", response_model=ProcessImportResponse)
def process_import(
    payload: ProcessImportRequest,
    session: AuthSessionResponse = Depends(get_current_session),
    import_pipeline_service: ImportPipelineService = Depends(get_import_pipeline_service),
    repository: PlatformRepository = Depends(get_repository),
) -> ProcessImportResponse:
    require_roles(session, {"SAL_ADMIN", "ENT_ADMIN"})
    require_company_access(session, payload.company_id)
    safe_payload = payload.model_copy(update={"user_id": session.userId})
    normalized_rows = import_pipeline_service.normalize_import_rows(safe_payload)
    trend_points = import_pipeline_service.build_trend_points(
        normalized_rows, safe_payload.aggregation_level
    )
    import_batch = repository.record_import_batch(
        payload=safe_payload,
        persisted_rows=len(normalized_rows),
        normalized_rows=normalized_rows,
        trend_points=trend_points,
        status="COMPLETED",
    )
    return ProcessImportResponse(
        import_batch_id=import_batch.id,
        persisted_rows=import_batch.persistedRows,
        aggregation_level=safe_payload.aggregation_level,
        status=import_batch.status,
    )
