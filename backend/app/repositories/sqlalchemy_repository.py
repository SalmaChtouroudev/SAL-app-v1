from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import (
    AlertORM,
    AlertHistoryORM,
    AuditLogORM,
    CompanyORM,
    DecisionRuleORM,
    ImportBatchORM,
    ImportMappingProfileORM,
    ImportedRowORM,
    KpiDefinitionORM,
    KpiSnapshotORM,
    ReportExportORM,
    UserORM,
)
from app.repositories.platform_repository import PlatformRepository, RepositoryUser
from app.schemas.imports import ProcessImportRequest
from app.schemas.platform import (
    AlertRead,
    AlertTrigger,
    AlertHistoryRead,
    AuditLogCreate,
    AuditLogRead,
    CompanyRead,
    CurrentUserProfileUpdate,
    DashboardTrendPoint,
    DecisionRuleConditionRead,
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
from app.services.client_demo_rules import ClientDemoRuleEngineService
from app.services.on_ing_profile import apply_company_profile_overrides


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def utc_iso(value: datetime | None = None) -> str:
    target = value or utc_now()
    return target.isoformat()


def role_permissions(role_type: str) -> list[str]:
    if role_type == "SAL_ADMIN":
        return [
            "dashboard:view",
            "import:create",
            "decision:view",
            "audit:view",
            "report:export",
            "users:manage",
            "companies:manage",
            "kpi:manage",
        ]
    if role_type == "ENT_ADMIN":
        return [
            "dashboard:view",
            "import:create",
            "decision:view",
            "audit:view",
            "report:export",
            "users:manage",
            "kpi:manage",
        ]
    return ["dashboard:view", "decision:view", "audit:view", "report:export"]


class SqlAlchemyPlatformRepository(PlatformRepository):
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user_by_email(self, email: str) -> RepositoryUser | None:
        normalized_email = email.strip().lower()
        user = self.db.scalar(select(UserORM).where(UserORM.email == normalized_email))
        return self._to_repository_user(user)

    def get_user_by_id(self, user_id: str) -> RepositoryUser | None:
        user = self.db.scalar(select(UserORM).where(UserORM.id == user_id))
        return self._to_repository_user(user)

    def update_user_last_login(self, user_id: str) -> None:
        user = self.db.scalar(select(UserORM).where(UserORM.id == user_id))
        if user is None:
            return

        user.last_login_at = utc_now()
        self.db.add(user)
        self.db.commit()

    def update_current_user_profile(
        self, user_id: str, payload: CurrentUserProfileUpdate
    ) -> RepositoryUser | None:
        user = self.db.scalar(select(UserORM).where(UserORM.id == user_id))
        if user is None:
            return None

        user.full_name = payload.fullName.strip()
        user.avatar_url = payload.avatarUrl
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return self._to_repository_user(user)

    def update_user_password(self, user_id: str, password_hash: str) -> bool:
        user = self.db.scalar(select(UserORM).where(UserORM.id == user_id))
        if user is None:
            return False

        user.password_hash = password_hash
        self.db.add(user)
        self.db.commit()
        return True

    def list_users(self) -> list[UserRead]:
        users = self.db.scalars(select(UserORM).order_by(UserORM.full_name.asc())).all()
        company_ids = list(self.db.scalars(select(CompanyORM.id)).all())
        return [
            UserRead(
                id=user.id,
                fullName=user.full_name,
                email=user.email,
                title=user.title,
                roleType=user.role_type,
                primaryCompanyId=user.company_id,
                companyIds=company_ids if user.role_type == "SAL_ADMIN" else [user.company_id],
                status=user.status,
                lastLoginAt=utc_iso(user.last_login_at) if user.last_login_at else None,
            )
            for user in users
        ]

    def create_user(self, payload: UserUpsert) -> UserRead:
        user = UserORM(
            id=f"usr-{uuid4().hex[:10]}",
            company_id=payload.primaryCompanyId,
            full_name=payload.fullName,
            email=payload.email.strip().lower(),
            password_hash=hash_password("ChangeMe123!"),
            role_type=payload.roleType,
            title=payload.title,
            status=payload.status,
            is_active=payload.status == "active",
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return self._to_user_read_model(user)

    def update_user(self, user_id: str, payload: UserUpsert) -> UserRead | None:
        user = self.db.scalar(select(UserORM).where(UserORM.id == user_id))
        if user is None:
            return None

        user.company_id = payload.primaryCompanyId
        user.full_name = payload.fullName
        user.email = payload.email.strip().lower()
        user.role_type = payload.roleType
        user.title = payload.title
        user.status = payload.status
        user.is_active = payload.status == "active"
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return self._to_user_read_model(user)

    def delete_user(self, user_id: str) -> bool:
        user = self.db.scalar(select(UserORM).where(UserORM.id == user_id))
        if user is None:
            return False

        self.db.delete(user)
        self.db.commit()
        return True

    def list_companies(self) -> list[CompanyRead]:
        companies = self.db.scalars(select(CompanyORM).order_by(CompanyORM.name.asc())).all()
        return [self._to_company_read(company) for company in companies]

    def get_company(self, company_id: str) -> CompanyRead | None:
        company = self.db.scalar(select(CompanyORM).where(CompanyORM.id == company_id))
        if company is None:
            return None
        return self._to_company_read(company)

    def list_kpi_definitions(self, company_id: str) -> list[KpiDefinitionRead]:
        definitions = self.db.scalars(
            select(KpiDefinitionORM)
            .where(KpiDefinitionORM.company_id == company_id)
            .order_by(KpiDefinitionORM.name.asc())
        ).all()
        return [self._to_kpi_definition_read(definition) for definition in definitions]

    def create_kpi_definition(self, payload: KpiDefinitionUpsert) -> KpiDefinitionRead:
        now = utc_now()
        definition = KpiDefinitionORM(
            id=f"kpi-{uuid4().hex[:10]}",
            company_id=payload.companyId,
            name=payload.name,
            category=payload.category,
            formula=payload.formula,
            threshold=float(payload.threshold),
            unit=payload.unit,
            direction=payload.direction,
            description=payload.description,
            source_key=payload.sourceKey,
            created_at=now,
            updated_at=now,
        )
        self.db.add(definition)
        self.db.commit()
        self.db.refresh(definition)
        return self._to_kpi_definition_read(definition)

    def update_kpi_definition(
        self, kpi_id: str, payload: KpiDefinitionUpsert
    ) -> KpiDefinitionRead | None:
        definition = self.db.scalar(select(KpiDefinitionORM).where(KpiDefinitionORM.id == kpi_id))
        if definition is None:
            return None

        definition.company_id = payload.companyId
        definition.name = payload.name
        definition.category = payload.category
        definition.formula = payload.formula
        definition.threshold = float(payload.threshold)
        definition.unit = payload.unit
        definition.direction = payload.direction
        definition.description = payload.description
        definition.source_key = payload.sourceKey
        definition.updated_at = utc_now()
        self.db.add(definition)
        self.db.commit()
        self.db.refresh(definition)
        return self._to_kpi_definition_read(definition)

    def delete_kpi_definition(self, kpi_id: str, company_id: str) -> bool:
        definition = self.db.scalar(
            select(KpiDefinitionORM).where(
                KpiDefinitionORM.id == kpi_id,
                KpiDefinitionORM.company_id == company_id,
            )
        )
        if definition is None:
            return False

        self.db.delete(definition)
        self.db.commit()
        return True

    def get_dashboard_trend(self, company_id: str) -> list[DashboardTrendPoint]:
        snapshots = self.db.scalars(
            select(KpiSnapshotORM)
            .where(KpiSnapshotORM.company_id == company_id)
            .order_by(KpiSnapshotORM.bucket.asc())
        ).all()
        return [
            DashboardTrendPoint(
                bucket=snapshot.bucket,
                totalRevenue=float(snapshot.total_revenue),
                totalExpenses=float(snapshot.total_expenses),
                netMargin=float(snapshot.net_margin),
            )
            for snapshot in snapshots
        ]

    def list_top_products(self, company_id: str, limit: int = 3) -> list[ReportBreakdownItem]:
        statement = (
            select(ImportedRowORM.product, func.sum(ImportedRowORM.revenue_amount))
            .where(
                ImportedRowORM.company_id == company_id,
                ImportedRowORM.product.is_not(None),
                ImportedRowORM.revenue_amount > 0,
            )
            .group_by(ImportedRowORM.product)
            .order_by(func.sum(ImportedRowORM.revenue_amount).desc())
            .limit(limit)
        )
        rows = self.db.execute(statement).all()
        return [
            ReportBreakdownItem(name=str(name), revenue=float(revenue or 0))
            for name, revenue in rows
            if name
        ]

    def list_top_clients(self, company_id: str, limit: int = 3) -> list[ReportBreakdownItem]:
        statement = (
            select(ImportedRowORM.client, func.sum(ImportedRowORM.revenue_amount))
            .where(
                ImportedRowORM.company_id == company_id,
                ImportedRowORM.client.is_not(None),
                ImportedRowORM.revenue_amount > 0,
            )
            .group_by(ImportedRowORM.client)
            .order_by(func.sum(ImportedRowORM.revenue_amount).desc())
            .limit(limit)
        )
        rows = self.db.execute(statement).all()
        return [
            ReportBreakdownItem(name=str(name), revenue=float(revenue or 0))
            for name, revenue in rows
            if name
        ]

    def list_rules(self, company_id: str | None = None) -> list[DecisionRuleRead]:
        statement = select(DecisionRuleORM)
        if company_id:
            statement = statement.where(
                (DecisionRuleORM.company_id.is_(None)) | (DecisionRuleORM.company_id == company_id)
            )

        rules = self.db.scalars(
            statement.order_by(
                DecisionRuleORM.enabled.desc(),
                DecisionRuleORM.priority.desc(),
                DecisionRuleORM.name.asc(),
            )
        ).all()
        return [self._to_rule_read(rule) for rule in rules]

    def create_rule(self, payload: DecisionRuleCreate) -> DecisionRuleRead:
        now = utc_now()
        rule = DecisionRuleORM(
            id=f"rule-{uuid4().hex[:10]}",
            company_id=payload.companyId,
            name=payload.name,
            priority=payload.priority,
            severity=payload.severity,
            logic=payload.logic,
            action_type=payload.actionType,
            title_en=payload.titleEn,
            title_fr=payload.titleFr,
            explanation_template_en=payload.explanationTemplateEn,
            explanation_template_fr=payload.explanationTemplateFr,
            recommendation_template_en=payload.recommendationTemplateEn,
            recommendation_template_fr=payload.recommendationTemplateFr,
            payload=json.dumps([condition.model_dump() for condition in payload.conditions]),
            enabled=payload.enabled,
            created_at=now,
            updated_at=now,
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return self._to_rule_read(rule)

    def update_rule(self, rule_id: str, payload: DecisionRuleCreate) -> DecisionRuleRead | None:
        rule = self.db.scalar(select(DecisionRuleORM).where(DecisionRuleORM.id == rule_id))
        if rule is None:
            return None

        rule.company_id = payload.companyId
        rule.name = payload.name
        rule.priority = payload.priority
        rule.severity = payload.severity
        rule.logic = payload.logic
        rule.action_type = payload.actionType
        rule.title_en = payload.titleEn
        rule.title_fr = payload.titleFr
        rule.explanation_template_en = payload.explanationTemplateEn
        rule.explanation_template_fr = payload.explanationTemplateFr
        rule.recommendation_template_en = payload.recommendationTemplateEn
        rule.recommendation_template_fr = payload.recommendationTemplateFr
        rule.payload = json.dumps([condition.model_dump() for condition in payload.conditions])
        rule.enabled = payload.enabled
        rule.updated_at = utc_now()
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return self._to_rule_read(rule)

    def delete_rule(self, rule_id: str) -> bool:
        rule = self.db.scalar(select(DecisionRuleORM).where(DecisionRuleORM.id == rule_id))
        if rule is None:
            return False

        self.db.delete(rule)
        self.db.commit()
        return True

    def list_alerts(self, company_id: str | None = None) -> list[AlertRead]:
        statement = select(AlertORM)
        if company_id:
            statement = statement.where(AlertORM.company_id == company_id)

        alerts = self.db.scalars(
            statement.order_by(AlertORM.is_active.desc(), AlertORM.created_at.desc())
        ).all()
        return [self._to_alert_read(alert) for alert in alerts]

    def resolve_alert(self, alert_id: str, resolved_by_user_id: str | None = None) -> bool:
        alert = self.db.scalar(select(AlertORM).where(AlertORM.id == alert_id))
        if alert is None:
            return False

        alert.is_active = False
        alert.resolved_at = utc_now()
        alert.resolved_by_user_id = resolved_by_user_id
        self.db.add(alert)
        self.db.add(
            AlertHistoryORM(
                id=f"ah-{uuid4().hex[:12]}",
                alert_id=alert.id,
                company_id=alert.company_id,
                rule_id=alert.rule_id,
                rule_name=alert.rule_name,
                event_type="RESOLVED",
                severity=alert.severity,
                title=alert.title,
                message=alert.message,
                recommendation=alert.recommendation,
                alert_status="RESOLVED",
                acted_by_user_id=resolved_by_user_id,
                event_source="USER_ACTION",
                evaluation_window="rolling-6-months",
                context_bucket=(
                    alert.last_triggered_at.strftime("%Y-%m")
                    if alert.last_triggered_at
                    else alert.created_at.strftime("%Y-%m")
                ),
                lifecycle_note="Alert resolved manually from the alerts workspace.",
                triggered_payload=alert.triggered_payload,
                matched_conditions_payload=alert.matched_conditions_payload,
                occurred_at=utc_now(),
            )
        )
        self.db.commit()
        return True

    def list_alert_history(
        self, company_id: str, alert_id: str | None = None
    ) -> list[AlertHistoryRead]:
        statement = select(AlertHistoryORM).where(AlertHistoryORM.company_id == company_id)
        if alert_id:
            statement = statement.where(AlertHistoryORM.alert_id == alert_id)

        entries = self.db.scalars(
            statement.order_by(AlertHistoryORM.occurred_at.desc())
        ).all()
        history = [self._to_alert_history_read(entry) for entry in entries]
        existing_alert_ids = {entry.alertId for entry in history}

        alert_statement = select(AlertORM).where(AlertORM.company_id == company_id)
        if alert_id:
            alert_statement = alert_statement.where(AlertORM.id == alert_id)

        alerts = self.db.scalars(alert_statement).all()
        for alert in alerts:
            if alert.id in existing_alert_ids:
                continue

            history.append(
                AlertHistoryRead(
                    id=f"synthetic-{alert.id}",
                    alertId=alert.id,
                    companyId=alert.company_id,
                    ruleId=alert.rule_id,
                    ruleName=alert.rule_name,
                    eventType="TRIGGERED",
                    severity=alert.severity,
                    title=alert.title,
                    message=alert.message,
                    recommendation=alert.recommendation,
                    alertStatus="ACTIVE",
                    occurredAt=utc_iso(alert.created_at),
                    actedByUserId=None,
                    actedByUserName=None,
                    eventSource="RULE_ENGINE",
                    evaluationWindow="rolling-6-months",
                    contextBucket=(
                        alert.last_triggered_at.strftime("%Y-%m")
                        if alert.last_triggered_at
                        else alert.created_at.strftime("%Y-%m")
                    ),
                    lifecycleNote="Rule engine evaluated persisted KPI signals and generated this alert.",
                    triggeredBy=self._parse_alert_trigger(alert.triggered_payload),
                    matchedConditions=self._parse_alert_condition_list(
                        alert.matched_conditions_payload
                    ),
                )
            )

        return sorted(history, key=lambda entry: entry.occurredAt, reverse=True)

    def list_audit_logs(self, company_id: str | None = None) -> list[AuditLogRead]:
        statement = select(AuditLogORM)
        if company_id:
            statement = statement.where(AuditLogORM.company_id == company_id)

        entries = self.db.scalars(
            statement.order_by(AuditLogORM.occurred_at.desc())
        ).all()
        return [self._to_audit_log_read(entry) for entry in entries]

    def create_audit_log(self, payload: AuditLogCreate) -> AuditLogRead:
        entry = AuditLogORM(
            id=f"audit-{uuid4().hex[:12]}",
            company_id=payload.enterpriseId,
            user_id=payload.userId,
            action_type=payload.actionType,
            status=payload.status,
            description=payload.description,
            occurred_at=utc_now(),
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return self._to_audit_log_read(entry)

    def record_import_batch(
        self,
        payload: ProcessImportRequest,
        persisted_rows: int,
        normalized_rows: list[dict[str, object]],
        trend_points: list[DashboardTrendPoint],
        status: str,
    ) -> ImportBatchRead:
        now = utc_now()
        batch_id = f"imp-{uuid4().hex[:12]}"
        source_type = self._resolve_batch_source_type(normalized_rows)
        batch = ImportBatchORM(
            id=batch_id,
            company_id=payload.company_id,
            uploaded_by=payload.user_id,
            file_name=payload.file_name,
            source_type=source_type,
            aggregation_level=payload.aggregation_level,
            persisted_rows=persisted_rows,
            status=status,
            created_at=now,
        )
        self.db.add(batch)
        self.db.add(
            ImportMappingProfileORM(
                id=f"map-{uuid4().hex[:12]}",
                import_batch_id=batch_id,
                company_id=payload.company_id,
                mapping_profile_name=payload.mapping_profile_name,
                payload=json.dumps(
                    {
                        "mapping": payload.mapping.model_dump(),
                        "normalizedPreview": normalized_rows[:10],
                    }
                ),
                created_at=now,
            )
        )

        for row in normalized_rows:
            business_date = row.get("date")
            if not isinstance(business_date, str):
                continue

            parsed_date = datetime.fromisoformat(business_date.replace("Z", "+00:00"))
            self.db.add(
                ImportedRowORM(
                    id=f"row-{uuid4().hex[:12]}",
                    import_batch_id=batch_id,
                    company_id=payload.company_id,
                    business_date=parsed_date,
                    revenue_amount=int(round(float(row.get("revenue") or 0))),
                    cost_amount=int(round(float(row.get("cost") or 0))),
                    source_type=str(row.get("source_type") or source_type),
                    project_code=self._clean_optional_text(row.get("project_code")),
                    project_name=self._clean_optional_text(row.get("project_name")),
                    original_project_reference=self._clean_optional_text(
                        row.get("original_project_reference")
                    ),
                    normalized_project_reference=self._clean_optional_text(
                        row.get("normalized_project_reference")
                    ),
                    category=self._clean_optional_text(row.get("category")),
                    product=self._clean_optional_text(row.get("product")),
                    client=self._clean_optional_text(row.get("client")),
                    original_client_name=self._clean_optional_text(row.get("original_client_name")),
                    normalized_client_name=self._clean_optional_text(
                        row.get("normalized_client_name")
                    ),
                    client_group=self._clean_optional_text(row.get("client_group")),
                    responsible=self._clean_optional_text(row.get("responsible")),
                    resource_name=self._clean_optional_text(row.get("resource_name")),
                    business_pole=self._clean_optional_text(row.get("business_pole")),
                    original_business_pole=self._clean_optional_text(
                        row.get("original_business_pole")
                    ),
                    normalized_business_pole=self._clean_optional_text(
                        row.get("normalized_business_pole")
                    ),
                    status=self._clean_optional_text(row.get("status")),
                    start_date=self._parse_optional_iso_date(row.get("start_date")),
                    end_date=self._parse_optional_iso_date(row.get("end_date")),
                    forecast_revenue_amount=self._round_optional_number(
                        row.get("forecast_revenue_amount")
                    ),
                    remaining_to_invoice_amount=self._round_optional_number(
                        row.get("remaining_to_invoice_amount")
                    ),
                    purchase_amount=self._round_optional_number(row.get("purchase_amount")),
                    margin_amount=self._round_optional_number(row.get("margin_amount")),
                    margin_rate=self._float_optional_number(row.get("margin_rate")),
                    debit_amount=self._round_optional_number(row.get("debit_amount")),
                    credit_amount=self._round_optional_number(row.get("credit_amount")),
                    invoice_amount=self._round_optional_number(row.get("invoice_amount")),
                    invoice_number=self._clean_optional_text(row.get("invoice_number")),
                    currency=self._clean_optional_text(row.get("currency")),
                    account_code=self._clean_optional_text(row.get("account_code")),
                    subaccount=self._clean_optional_text(row.get("subaccount")),
                    description=self._clean_optional_text(row.get("description")),
                    created_at=now,
                )
            )

        self.db.flush()
        recomputed_trend = self._build_trend_from_imported_rows(
            payload.company_id, payload.aggregation_level
        )
        self.db.execute(
            delete(KpiSnapshotORM).where(KpiSnapshotORM.company_id == payload.company_id)
        )
        for point in recomputed_trend:
            self.db.add(
                KpiSnapshotORM(
                    id=f"kpi-{uuid4().hex[:12]}",
                    company_id=payload.company_id,
                    bucket=point.bucket,
                    aggregation_level=payload.aggregation_level,
                    total_revenue=int(round(point.totalRevenue)),
                    total_expenses=int(round(point.totalExpenses)),
                    net_margin=int(round(point.netMargin)),
                    source_import_batch_id=batch_id,
                    created_at=now,
                )
            )

        self.db.add(
            AuditLogORM(
                id=f"audit-{uuid4().hex[:12]}",
                company_id=payload.company_id,
                user_id=payload.user_id,
                action_type="IMPORT_CONFIRMED",
                status="SUCCESS",
                description=f"Import {payload.file_name} persisted with {persisted_rows} normalized rows.",
                occurred_at=now,
            )
        )

        ClientDemoRuleEngineService(self.db).sync_company(payload.company_id)
        self.db.commit()
        return ImportBatchRead(
            id=batch.id,
            companyId=batch.company_id,
            uploadedBy=batch.uploaded_by,
            fileName=batch.file_name,
            aggregationLevel=batch.aggregation_level,
            persistedRows=batch.persisted_rows,
            status=batch.status,
            createdAt=utc_iso(batch.created_at),
        )

    def list_import_batches(self, company_id: str) -> list[ImportBatchRead]:
        batches = self.db.scalars(
            select(ImportBatchORM)
            .where(ImportBatchORM.company_id == company_id)
            .order_by(ImportBatchORM.created_at.desc())
        ).all()
        return [
            ImportBatchRead(
                id=batch.id,
                companyId=batch.company_id,
                uploadedBy=batch.uploaded_by,
                fileName=batch.file_name,
                aggregationLevel=batch.aggregation_level,
                persistedRows=batch.persisted_rows,
                status=batch.status,
                createdAt=utc_iso(batch.created_at),
            )
            for batch in batches
        ]

    def record_report_export(
        self,
        company_id: str,
        requested_by: str,
        format_name: str,
        file_name: str,
        status: str,
    ) -> ReportExportRead:
        export = ReportExportORM(
            id=f"rep-{uuid4().hex[:12]}",
            company_id=company_id,
            requested_by=requested_by,
            format=format_name,
            file_name=file_name,
            status=status,
            generated_at=utc_now(),
        )
        self.db.add(export)
        self.db.commit()
        self.db.refresh(export)
        return ReportExportRead(
            id=export.id,
            companyId=export.company_id,
            requestedBy=export.requested_by,
            format="pdf" if export.format == "pdf" else "excel",
            fileName=export.file_name,
            status=export.status,
            generatedAt=utc_iso(export.generated_at),
        )

    def list_report_exports(self, company_id: str) -> list[ReportExportRead]:
        exports = self.db.scalars(
            select(ReportExportORM)
            .where(ReportExportORM.company_id == company_id)
            .order_by(ReportExportORM.generated_at.desc())
        ).all()
        return [
            ReportExportRead(
                id=export.id,
                companyId=export.company_id,
                requestedBy=export.requested_by,
                format="pdf" if export.format == "pdf" else "excel",
                fileName=export.file_name,
                status=export.status,
                generatedAt=utc_iso(export.generated_at),
            )
            for export in exports
        ]

    def get_report_export(self, export_id: str) -> ReportExportRead | None:
        export = self.db.scalar(select(ReportExportORM).where(ReportExportORM.id == export_id))
        if export is None:
            return None
        return ReportExportRead(
            id=export.id,
            companyId=export.company_id,
            requestedBy=export.requested_by,
            format="pdf" if export.format == "pdf" else "excel",
            fileName=export.file_name,
            status=export.status,
            generatedAt=utc_iso(export.generated_at),
        )

    def _to_repository_user(self, user: UserORM | None) -> RepositoryUser | None:
        if user is None:
            return None

        accessible_company_ids = (
            list(self.db.scalars(select(CompanyORM.id)).all())
            if user.role_type == "SAL_ADMIN"
            else [user.company_id]
        )
        return RepositoryUser(
            user_id=user.id,
            enterprise_id=user.company_id,
            email=user.email,
            full_name=user.full_name,
            role_type=user.role_type,
            title=user.title,
            password_hash=user.password_hash,
            accessible_company_ids=accessible_company_ids,
            permissions=role_permissions(user.role_type),
            primary_company_id=user.company_id,
            status=user.status if user.is_active else "inactive",
            last_login_at=utc_iso(user.last_login_at) if user.last_login_at else None,
            avatar_url=user.avatar_url,
            created_at=utc_iso(user.created_at),
        )

    def _to_user_read_model(self, user: UserORM) -> UserRead:
        company_ids = (
            list(self.db.scalars(select(CompanyORM.id)).all())
            if user.role_type == "SAL_ADMIN"
            else [user.company_id]
        )
        return UserRead(
            id=user.id,
            fullName=user.full_name,
            email=user.email,
            title=user.title,
            roleType=user.role_type,
            primaryCompanyId=user.company_id,
            companyIds=company_ids,
            status=user.status,
            lastLoginAt=utc_iso(user.last_login_at) if user.last_login_at else None,
        )

    def _to_company_read(self, company: CompanyORM) -> CompanyRead:
        payload = apply_company_profile_overrides(
            {
                "id": company.id,
                "name": company.name,
                "sector": company.sector,
                "plan": company.plan,
                "health": company.health,
                "country": company.country,
                "currency": company.currency,
                "monthlyTarget": company.monthly_target,
                "headquarters": company.headquarters,
                "lastSyncAt": utc_iso(company.created_at),
            }
        )
        return CompanyRead(**payload)

    def _to_kpi_definition_read(self, definition: KpiDefinitionORM) -> KpiDefinitionRead:
        return KpiDefinitionRead(
            id=definition.id,
            companyId=definition.company_id,
            name=definition.name,
            category=definition.category,
            formula=definition.formula,
            threshold=float(definition.threshold),
            unit=definition.unit,
            direction=definition.direction,
            description=definition.description,
            sourceKey=definition.source_key,
            createdAt=utc_iso(definition.created_at),
            updatedAt=utc_iso(definition.updated_at),
        )

    def _to_rule_read(self, rule: DecisionRuleORM) -> DecisionRuleRead:
        raw_conditions = json.loads(rule.payload)
        return DecisionRuleRead(
            id=rule.id,
            companyId=rule.company_id,
            name=rule.name,
            priority=rule.priority,
            severity=rule.severity,
            logic=rule.logic,
            actionType=rule.action_type,
            enabled=rule.enabled,
            titleEn=rule.title_en,
            titleFr=rule.title_fr,
            explanationTemplateEn=rule.explanation_template_en,
            explanationTemplateFr=rule.explanation_template_fr,
            recommendationTemplateEn=rule.recommendation_template_en,
            recommendationTemplateFr=rule.recommendation_template_fr,
            conditions=[DecisionRuleConditionRead(**condition) for condition in raw_conditions],
            createdAt=utc_iso(rule.created_at),
            updatedAt=utc_iso(rule.updated_at),
        )

    def _to_alert_read(self, alert: AlertORM) -> AlertRead:
        raw_trigger = json.loads(alert.triggered_payload) if alert.triggered_payload else None
        raw_conditions = (
            json.loads(alert.matched_conditions_payload) if alert.matched_conditions_payload else []
        )
        return AlertRead(
            id=alert.id,
            companyId=alert.company_id,
            ruleId=alert.rule_id,
            source=alert.source,
            ruleName=alert.rule_name,
            title=alert.title,
            message=alert.message,
            explainabilityText=alert.explainability_text,
            recommendation=alert.recommendation,
            severity=alert.severity,
            isActive=alert.is_active,
            createdAt=utc_iso(alert.created_at),
            triggerCount=alert.trigger_count,
            firstTriggeredAt=utc_iso(alert.first_triggered_at) if alert.first_triggered_at else None,
            lastTriggeredAt=utc_iso(alert.last_triggered_at) if alert.last_triggered_at else None,
            resolvedAt=utc_iso(alert.resolved_at) if alert.resolved_at else None,
            resolvedByUserId=alert.resolved_by_user_id,
            triggeredBy=AlertTrigger(**raw_trigger) if raw_trigger else None,
            matchedConditions=[AlertTrigger(**condition) for condition in raw_conditions],
        )

    def _to_audit_log_read(self, entry: AuditLogORM) -> AuditLogRead:
        return AuditLogRead(
            id=entry.id,
            enterpriseId=entry.company_id,
            userId=entry.user_id,
            actionType=entry.action_type,
            status=entry.status,
            description=entry.description,
            occurredAt=utc_iso(entry.occurred_at),
        )

    def _to_alert_history_read(self, entry: AlertHistoryORM) -> AlertHistoryRead:
        raw_trigger = json.loads(entry.triggered_payload) if entry.triggered_payload else None
        raw_conditions = (
            json.loads(entry.matched_conditions_payload) if entry.matched_conditions_payload else []
        )
        acted_by_user = (
            self.get_user_by_id(entry.acted_by_user_id) if entry.acted_by_user_id else None
        )
        return AlertHistoryRead(
            id=entry.id,
            alertId=entry.alert_id,
            companyId=entry.company_id,
            ruleId=entry.rule_id,
            ruleName=entry.rule_name,
            eventType=entry.event_type,
            severity=entry.severity,
            title=entry.title,
            message=entry.message,
            recommendation=entry.recommendation,
            alertStatus=entry.alert_status,
            occurredAt=utc_iso(entry.occurred_at),
            actedByUserId=entry.acted_by_user_id,
            actedByUserName=acted_by_user.full_name if acted_by_user else None,
            eventSource=entry.event_source,
            evaluationWindow=entry.evaluation_window,
            contextBucket=entry.context_bucket,
            lifecycleNote=entry.lifecycle_note,
            triggeredBy=AlertTrigger(**raw_trigger) if raw_trigger else None,
            matchedConditions=[AlertTrigger(**condition) for condition in raw_conditions],
        )

    def _build_trend_from_imported_rows(
        self, company_id: str, aggregation_level: str
    ) -> list[DashboardTrendPoint]:
        rows = self.db.scalars(
            select(ImportedRowORM)
            .where(ImportedRowORM.company_id == company_id)
            .order_by(ImportedRowORM.business_date.asc())
        ).all()
        preferred_source = self.db.scalar(
            select(ImportBatchORM.source_type)
            .where(ImportBatchORM.company_id == company_id)
            .order_by(ImportBatchORM.created_at.desc())
            .limit(1)
        )
        if preferred_source is None:
            preferred_source = self._resolve_preferred_trend_source(list(rows))
        grouped: dict[str, dict[str, float]] = {}

        for row in rows:
            if preferred_source is not None and row.source_type != preferred_source:
                continue

            if aggregation_level == "day":
                bucket = row.business_date.strftime("%Y-%m-%d")
            elif aggregation_level == "year":
                bucket = row.business_date.strftime("%Y")
            else:
                bucket = row.business_date.strftime("%Y-%m")

            current = grouped.setdefault(bucket, {"revenue": 0.0, "cost": 0.0})
            current["revenue"] += float(row.revenue_amount)
            current["cost"] += float(row.cost_amount)

        return [
            DashboardTrendPoint(
                bucket=bucket,
                totalRevenue=round(values["revenue"], 2),
                totalExpenses=round(values["cost"], 2),
                netMargin=round(values["revenue"] - values["cost"], 2),
            )
            for bucket, values in sorted(grouped.items(), key=lambda item: item[0])
        ]

    def _clean_optional_text(self, value: object) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        if normalized.lower() == "nan":
            return None
        return normalized or None

    def _parse_optional_iso_date(self, value: object) -> datetime | None:
        normalized = self._clean_optional_text(value)
        if normalized is None:
            return None
        return datetime.fromisoformat(normalized.replace("Z", "+00:00"))

    def _round_optional_number(self, value: object) -> int | None:
        parsed = self._float_optional_number(value)
        if parsed is None:
            return None
        return int(round(parsed))

    def _float_optional_number(self, value: object) -> float | None:
        normalized = self._clean_optional_text(value)
        if normalized is None:
            return None
        try:
            return float(normalized)
        except ValueError:
            return None

    def _resolve_batch_source_type(self, normalized_rows: list[dict[str, object]]) -> str:
        for row in normalized_rows:
            source_type = row.get("source_type")
            if isinstance(source_type, str) and source_type.strip():
                return source_type.strip()
        return "generic"

    def _resolve_preferred_trend_source(self, rows: list[ImportedRowORM]) -> str | None:
        available_sources = {row.source_type for row in rows}
        for source_type in ("ca_projects", "pnl", "affair_tracking"):
            if source_type in available_sources:
                return source_type
        return None
