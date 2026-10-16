from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas.imports import ProcessImportRequest
from app.schemas.platform import (
    AlertRead,
    AlertHistoryRead,
    AuditLogCreate,
    AuditLogRead,
    CompanyRead,
    CurrentUserProfileUpdate,
    DashboardTrendPoint,
    DecisionRuleCreate,
    DecisionRuleRead,
    ImportBatchRead,
    KpiDefinitionRead,
    KpiDefinitionUpsert,
    ReportBreakdownItem,
    ReportExportRead,
    UserUpsert,
    UserRead,
)


@dataclass(frozen=True)
class RepositoryUser:
    user_id: str
    enterprise_id: str
    email: str
    full_name: str
    role_type: str
    title: str
    password_hash: str
    accessible_company_ids: list[str]
    permissions: list[str]
    primary_company_id: str
    status: str = "active"
    last_login_at: str | None = None
    avatar_url: str | None = None
    created_at: str | None = None


class PlatformRepository(Protocol):
    def get_user_by_email(self, email: str) -> RepositoryUser | None: ...

    def get_user_by_id(self, user_id: str) -> RepositoryUser | None: ...

    def update_user_last_login(self, user_id: str) -> None: ...

    def update_current_user_profile(
        self, user_id: str, payload: CurrentUserProfileUpdate
    ) -> RepositoryUser | None: ...

    def update_user_password(self, user_id: str, password_hash: str) -> bool: ...

    def list_users(self) -> list[UserRead]: ...

    def create_user(self, payload: UserUpsert) -> UserRead: ...

    def update_user(self, user_id: str, payload: UserUpsert) -> UserRead | None: ...

    def delete_user(self, user_id: str) -> bool: ...

    def list_companies(self) -> list[CompanyRead]: ...

    def get_company(self, company_id: str) -> CompanyRead | None: ...

    def list_kpi_definitions(self, company_id: str) -> list[KpiDefinitionRead]: ...

    def create_kpi_definition(self, payload: KpiDefinitionUpsert) -> KpiDefinitionRead: ...

    def update_kpi_definition(
        self, kpi_id: str, payload: KpiDefinitionUpsert
    ) -> KpiDefinitionRead | None: ...

    def delete_kpi_definition(self, kpi_id: str, company_id: str) -> bool: ...

    def get_dashboard_trend(self, company_id: str) -> list[DashboardTrendPoint]: ...

    def list_top_products(self, company_id: str, limit: int = 3) -> list[ReportBreakdownItem]: ...

    def list_top_clients(self, company_id: str, limit: int = 3) -> list[ReportBreakdownItem]: ...

    def list_rules(self, company_id: str | None = None) -> list[DecisionRuleRead]: ...

    def create_rule(self, payload: DecisionRuleCreate) -> DecisionRuleRead: ...

    def update_rule(self, rule_id: str, payload: DecisionRuleCreate) -> DecisionRuleRead | None: ...

    def delete_rule(self, rule_id: str) -> bool: ...

    def list_alerts(self, company_id: str | None = None) -> list[AlertRead]: ...

    def resolve_alert(self, alert_id: str, resolved_by_user_id: str | None = None) -> bool: ...

    def list_alert_history(
        self, company_id: str, alert_id: str | None = None
    ) -> list[AlertHistoryRead]: ...

    def list_audit_logs(self, company_id: str | None = None) -> list[AuditLogRead]: ...

    def create_audit_log(self, payload: AuditLogCreate) -> AuditLogRead: ...

    def record_import_batch(
        self,
        payload: ProcessImportRequest,
        persisted_rows: int,
        normalized_rows: list[dict[str, object]],
        trend_points: list[DashboardTrendPoint],
        status: str,
    ) -> ImportBatchRead: ...

    def list_import_batches(self, company_id: str) -> list[ImportBatchRead]: ...

    def record_report_export(
        self,
        company_id: str,
        requested_by: str,
        format_name: str,
        file_name: str,
        status: str,
    ) -> ReportExportRead: ...

    def list_report_exports(self, company_id: str) -> list[ReportExportRead]: ...

    def get_report_export(self, export_id: str) -> ReportExportRead | None: ...
