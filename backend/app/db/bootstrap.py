from __future__ import annotations

from datetime import datetime
import json
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.base import Base
from app.db.models import (
    AlertORM,
    AlertHistoryORM,
    AuditLogORM,
    CompanyORM,
    DecisionRuleORM,
    KpiDefinitionORM,
    KpiSnapshotORM,
    UserORM,
)
from app.db.session import SessionLocal, engine
from app.repositories.demo_repository import DemoPlatformRepository


def initialize_database(
    settings: Settings,
    *,
    db_engine: Engine | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> None:
    if settings.use_demo_data:
        return

    active_engine = db_engine or engine
    active_session_factory = session_factory or (
        SessionLocal
        if db_engine is None
        else sessionmaker(
            bind=active_engine,
            autocommit=False,
            autoflush=False,
            class_=Session,
        )
    )
    Base.metadata.create_all(bind=active_engine)

    # SQLite local demo mode uses metadata-based initialization for a fresh portable DB file.
    # PostgreSQL keeps the incremental schema patch path for existing local databases.
    if not settings.is_sqlite_database:
        ensure_import_enrichment_schema(active_engine)

    if not settings.bootstrap_sample_data:
        return

    with active_session_factory() as db:
        has_companies = db.scalar(select(CompanyORM.id).limit(1))
        if has_companies:
            return

        demo_repository = DemoPlatformRepository()

        for company in demo_repository.list_companies():
            db.add(
                CompanyORM(
                    id=company.id,
                    name=company.name,
                    sector=company.sector,
                    plan=company.plan,
                    country=company.country,
                    currency=company.currency,
                    monthly_target=company.monthlyTarget,
                    headquarters=company.headquarters,
                    health=company.health,
                )
            )

        db.flush()

        for user in demo_repository.list_auth_users():
            db.add(
                UserORM(
                    id=user.user_id,
                    company_id=user.enterprise_id,
                    full_name=user.full_name,
                    email=user.email,
                    password_hash=user.password_hash,
                    role_type=user.role_type,
                    title=user.title,
                    avatar_url=user.avatar_url,
                    status=user.status,
                    is_active=user.status.lower() == "active",
                )
            )

        db.flush()

        for company in demo_repository.list_companies():
            for definition in demo_repository.list_kpi_definitions(company.id):
                db.add(
                    KpiDefinitionORM(
                        id=definition.id,
                        company_id=definition.companyId,
                        name=definition.name,
                        category=definition.category,
                        formula=definition.formula,
                        threshold=float(definition.threshold),
                        unit=definition.unit,
                        direction=definition.direction,
                        description=definition.description,
                        source_key=definition.sourceKey,
                    )
                )

        db.flush()

        for company in demo_repository.list_companies():
            for point in demo_repository.get_dashboard_trend(company.id):
                db.add(
                    KpiSnapshotORM(
                        id=f"kpi-{uuid4().hex[:12]}",
                        company_id=company.id,
                        bucket=point.bucket,
                        aggregation_level="month",
                        total_revenue=int(round(point.totalRevenue)),
                        total_expenses=int(round(point.totalExpenses)),
                        net_margin=int(round(point.netMargin)),
                    )
                )

        db.flush()

        for rule in demo_repository.list_rules():
            db.add(
                DecisionRuleORM(
                    id=rule.id,
                    company_id=rule.companyId,
                    name=rule.name,
                    priority=rule.priority,
                    severity=rule.severity,
                    logic=rule.logic,
                    action_type=rule.actionType,
                    title_en=rule.titleEn,
                    title_fr=rule.titleFr,
                    explanation_template_en=rule.explanationTemplateEn,
                    explanation_template_fr=rule.explanationTemplateFr,
                    recommendation_template_en=rule.recommendationTemplateEn,
                    recommendation_template_fr=rule.recommendationTemplateFr,
                    payload=json.dumps([condition.model_dump() for condition in rule.conditions]),
                    enabled=rule.enabled,
                )
            )

        db.flush()

        for alert in demo_repository.list_alerts():
            db.add(
                AlertORM(
                    id=alert.id,
                    company_id=alert.companyId,
                    rule_id=alert.ruleId,
                    source=alert.source,
                    rule_name=alert.ruleName,
                    title=alert.title,
                    message=alert.message,
                    severity=alert.severity,
                    is_active=alert.isActive,
                    explainability_text=alert.explainabilityText,
                    recommendation=alert.recommendation,
                    trigger_count=alert.triggerCount,
                    first_triggered_at=(
                        datetime.fromisoformat(alert.firstTriggeredAt.replace("Z", "+00:00"))
                        if alert.firstTriggeredAt
                        else None
                    ),
                    last_triggered_at=(
                        datetime.fromisoformat(alert.lastTriggeredAt.replace("Z", "+00:00"))
                        if alert.lastTriggeredAt
                        else None
                    ),
                    resolved_at=(
                        datetime.fromisoformat(alert.resolvedAt.replace("Z", "+00:00"))
                        if alert.resolvedAt
                        else None
                    ),
                    resolved_by_user_id=alert.resolvedByUserId,
                    triggered_payload=(
                        json.dumps(alert.triggeredBy.model_dump()) if alert.triggeredBy else None
                    ),
                    matched_conditions_payload=json.dumps(
                        [condition.model_dump() for condition in alert.matchedConditions]
                    ),
                )
            )

        # Flush parent alerts before seeding history rows that reference them.
        db.flush()

        for company in demo_repository.list_companies():
            for entry in demo_repository.list_alert_history(company.id):
                db.add(
                    AlertHistoryORM(
                        id=entry.id,
                        alert_id=entry.alertId,
                        company_id=entry.companyId,
                        rule_id=entry.ruleId,
                        rule_name=entry.ruleName,
                        event_type=entry.eventType,
                        severity=entry.severity,
                        title=entry.title,
                        message=entry.message,
                        recommendation=entry.recommendation,
                        alert_status=entry.alertStatus,
                        acted_by_user_id=entry.actedByUserId,
                        event_source=entry.eventSource,
                        evaluation_window=entry.evaluationWindow,
                        context_bucket=entry.contextBucket,
                        lifecycle_note=entry.lifecycleNote,
                        triggered_payload=(
                            json.dumps(entry.triggeredBy.model_dump()) if entry.triggeredBy else None
                        ),
                        matched_conditions_payload=json.dumps(
                            [condition.model_dump() for condition in entry.matchedConditions]
                        ),
                        occurred_at=datetime.fromisoformat(entry.occurredAt.replace("Z", "+00:00")),
                    )
                )

        for entry in demo_repository.list_audit_logs():
            db.add(
                AuditLogORM(
                    id=entry.id,
                    company_id=entry.enterpriseId,
                    user_id=entry.userId,
                    action_type=entry.actionType,
                    status=entry.status,
                    description=entry.description,
                )
            )

        db.commit()


def ensure_import_enrichment_schema(db_engine: Engine = engine) -> None:
    statements = [
        "ALTER TABLE import_batches ADD COLUMN IF NOT EXISTS source_type VARCHAR(32) NOT NULL DEFAULT 'generic'",
        "ALTER TABLE import_rows ADD COLUMN IF NOT EXISTS source_type VARCHAR(32) NOT NULL DEFAULT 'generic'",
        "ALTER TABLE import_rows ADD COLUMN IF NOT EXISTS project_code VARCHAR(128)",
        "ALTER TABLE import_rows ADD COLUMN IF NOT EXISTS project_name VARCHAR(255)",
        "ALTER TABLE import_rows ADD COLUMN IF NOT EXISTS responsible VARCHAR(255)",
        "ALTER TABLE import_rows ADD COLUMN IF NOT EXISTS business_pole VARCHAR(255)",
        "ALTER TABLE import_rows ADD COLUMN IF NOT EXISTS status VARCHAR(64)",
        "ALTER TABLE import_rows ADD COLUMN IF NOT EXISTS start_date TIMESTAMP WITH TIME ZONE",
        "ALTER TABLE import_rows ADD COLUMN IF NOT EXISTS end_date TIMESTAMP WITH TIME ZONE",
        "ALTER TABLE import_rows ADD COLUMN IF NOT EXISTS forecast_revenue_amount INTEGER",
        "ALTER TABLE import_rows ADD COLUMN IF NOT EXISTS purchase_amount INTEGER",
        "ALTER TABLE import_rows ADD COLUMN IF NOT EXISTS margin_amount INTEGER",
        "ALTER TABLE import_rows ADD COLUMN IF NOT EXISTS margin_rate DOUBLE PRECISION",
        "ALTER TABLE import_rows ADD COLUMN IF NOT EXISTS debit_amount INTEGER",
        "ALTER TABLE import_rows ADD COLUMN IF NOT EXISTS credit_amount INTEGER",
        "ALTER TABLE import_rows ADD COLUMN IF NOT EXISTS invoice_amount INTEGER",
        "ALTER TABLE import_rows ADD COLUMN IF NOT EXISTS invoice_number VARCHAR(128)",
        "ALTER TABLE import_rows ADD COLUMN IF NOT EXISTS currency VARCHAR(16)",
        "ALTER TABLE import_rows ADD COLUMN IF NOT EXISTS account_code VARCHAR(128)",
        "ALTER TABLE import_rows ADD COLUMN IF NOT EXISTS subaccount VARCHAR(128)",
        "ALTER TABLE import_rows ADD COLUMN IF NOT EXISTS original_project_reference VARCHAR(255)",
        "ALTER TABLE import_rows ADD COLUMN IF NOT EXISTS normalized_project_reference VARCHAR(255)",
        "ALTER TABLE import_rows ADD COLUMN IF NOT EXISTS original_client_name VARCHAR(255)",
        "ALTER TABLE import_rows ADD COLUMN IF NOT EXISTS normalized_client_name VARCHAR(255)",
        "ALTER TABLE import_rows ADD COLUMN IF NOT EXISTS client_group VARCHAR(255)",
        "ALTER TABLE import_rows ADD COLUMN IF NOT EXISTS resource_name VARCHAR(255)",
        "ALTER TABLE import_rows ADD COLUMN IF NOT EXISTS original_business_pole VARCHAR(255)",
        "ALTER TABLE import_rows ADD COLUMN IF NOT EXISTS normalized_business_pole VARCHAR(255)",
        "ALTER TABLE import_rows ADD COLUMN IF NOT EXISTS remaining_to_invoice_amount INTEGER",
        "CREATE INDEX IF NOT EXISTS ix_import_rows_company_source ON import_rows (company_id, source_type)",
        "CREATE INDEX IF NOT EXISTS ix_import_rows_company_project ON import_rows (company_id, project_code)",
    ]

    with db_engine.begin() as connection:
        for statement in statements:
            connection.exec_driver_sql(statement)
