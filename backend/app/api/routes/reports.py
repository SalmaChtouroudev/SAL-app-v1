from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.api.dependencies import get_current_session, get_report_service, require_company_access
from app.repositories.platform_repository import PlatformRepository
from app.api.dependencies import get_repository
from app.schemas.auth import AuthSessionResponse
from app.schemas.platform import (
    AuditLogCreate,
    ReportExportRead,
    ReportExportRequest,
    ReportExportResponse,
    ReportPreviewRead,
)
from app.services.report_service import ReportService


router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/preview", response_model=ReportPreviewRead)
def preview_report(
    company_id: str,
    session: AuthSessionResponse = Depends(get_current_session),
    report_service: ReportService = Depends(get_report_service),
) -> ReportPreviewRead:
    require_company_access(session, company_id)
    try:
        return report_service.preview(company_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/history", response_model=list[ReportExportRead])
def list_export_history(
    company_id: str,
    session: AuthSessionResponse = Depends(get_current_session),
    report_service: ReportService = Depends(get_report_service),
) -> list[ReportExportRead]:
    require_company_access(session, company_id)
    return report_service.list_export_history(company_id)


@router.post("/pdf", response_model=ReportExportResponse)
def export_pdf(
    payload: ReportExportRequest,
    session: AuthSessionResponse = Depends(get_current_session),
    report_service: ReportService = Depends(get_report_service),
) -> ReportExportResponse:
    require_company_access(session, payload.companyId)
    try:
        return report_service.export(
            payload.model_copy(update={"format": "pdf", "requestedBy": session.userId})
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/excel", response_model=ReportExportResponse)
def export_excel(
    payload: ReportExportRequest,
    session: AuthSessionResponse = Depends(get_current_session),
    report_service: ReportService = Depends(get_report_service),
) -> ReportExportResponse:
    require_company_access(session, payload.companyId)
    try:
        return report_service.export(
            payload.model_copy(update={"format": "excel", "requestedBy": session.userId})
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{export_id}/download")
def download_report(
    export_id: str,
    session: AuthSessionResponse = Depends(get_current_session),
    report_service: ReportService = Depends(get_report_service),
    repository: PlatformRepository = Depends(get_repository),
) -> FileResponse:
    export = report_service.get_export(export_id)
    if export is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report export not found.")

    require_company_access(session, export.companyId)
    file_path = report_service.resolve_output_path(export)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generated report file not found.")

    media_type = (
        "application/pdf"
        if export.format == "pdf"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    repository.create_audit_log(
        AuditLogCreate(
            enterpriseId=export.companyId,
            userId=session.userId,
            actionType="REPORT_DOWNLOADED",
            status="SUCCESS",
            description=f"{export.format.upper()} report downloaded: {export.fileName}.",
        )
    )
    return FileResponse(path=file_path, media_type=media_type, filename=export.fileName)
