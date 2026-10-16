from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CompanyORM(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[str] = mapped_column(String(120), nullable=False)
    plan: Mapped[str] = mapped_column(String(64), nullable=False)
    country: Mapped[str] = mapped_column(String(120), nullable=False)
    currency: Mapped[str] = mapped_column(String(16), nullable=False, default="TND")
    monthly_target: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    headquarters: Mapped[str] = mapped_column(String(120), nullable=False)
    health: Mapped[str] = mapped_column(String(32), nullable=False, default="healthy")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ImportBatchORM(Base):
    __tablename__ = "import_batches"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False)
    uploaded_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="generic")
    aggregation_level: Mapped[str] = mapped_column(String(16), nullable=False)
    persisted_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ImportedRowORM(Base):
    __tablename__ = "import_rows"
    __table_args__ = (
        Index("ix_import_rows_company_date", "company_id", "business_date"),
        Index("ix_import_rows_batch", "import_batch_id"),
        Index("ix_import_rows_company_source", "company_id", "source_type"),
        Index("ix_import_rows_company_project", "company_id", "project_code"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    import_batch_id: Mapped[str] = mapped_column(ForeignKey("import_batches.id"), nullable=False)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False)
    business_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revenue_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="generic")
    project_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    project_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_project_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    normalized_project_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    product: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    normalized_client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_group: Mapped[str | None] = mapped_column(String(255), nullable=True)
    responsible: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resource_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    business_pole: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_business_pole: Mapped[str | None] = mapped_column(String(255), nullable=True)
    normalized_business_pole: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    forecast_revenue_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    remaining_to_invoice_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    purchase_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    margin_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    margin_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    debit_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    credit_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    invoice_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    invoice_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(16), nullable=True)
    account_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    subaccount: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ImportMappingProfileORM(Base):
    __tablename__ = "import_mapping_profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    import_batch_id: Mapped[str] = mapped_column(ForeignKey("import_batches.id"), nullable=False)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False)
    mapping_profile_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class KpiDefinitionORM(Base):
    __tablename__ = "kpi_definitions"
    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_kpi_definition_company_name"),
        Index("ix_kpi_definitions_company", "company_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    formula: Mapped[str] = mapped_column(Text, nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_key: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class KpiSnapshotORM(Base):
    __tablename__ = "kpi_snapshots"
    __table_args__ = (UniqueConstraint("company_id", "bucket", name="uq_kpi_snapshot_company_bucket"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False)
    bucket: Mapped[str] = mapped_column(String(32), nullable=False)
    aggregation_level: Mapped[str] = mapped_column(String(16), nullable=False, default="month")
    total_revenue: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_expenses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    net_margin: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_import_batch_id: Mapped[str | None] = mapped_column(
        ForeignKey("import_batches.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class DecisionRuleORM(Base):
    __tablename__ = "decision_rules"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    logic: Mapped[str] = mapped_column(String(8), nullable=False)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    title_fr: Mapped[str] = mapped_column(Text, nullable=False, default="")
    explanation_template_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    explanation_template_fr: Mapped[str] = mapped_column(Text, nullable=False, default="")
    recommendation_template_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    recommendation_template_fr: Mapped[str] = mapped_column(Text, nullable=False, default="")
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class AlertORM(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False)
    rule_id: Mapped[str | None] = mapped_column(ForeignKey("decision_rules.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(255), nullable=False, default="System")
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False, default="System rule")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    explainability_text: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    triggered_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    matched_conditions_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    first_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class AlertHistoryORM(Base):
    __tablename__ = "alert_history"
    __table_args__ = (
        Index("ix_alert_history_company_occurred", "company_id", "occurred_at"),
        Index("ix_alert_history_alert", "alert_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    alert_id: Mapped[str] = mapped_column(ForeignKey("alerts.id"), nullable=False)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False)
    rule_id: Mapped[str | None] = mapped_column(ForeignKey("decision_rules.id"), nullable=True)
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False, default="System rule")
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    recommendation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    alert_status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    acted_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    event_source: Mapped[str] = mapped_column(String(32), nullable=False, default="SYSTEM")
    evaluation_window: Mapped[str | None] = mapped_column(String(64), nullable=True)
    context_bucket: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lifecycle_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    matched_conditions_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class AuditLogORM(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ReportExportORM(Base):
    __tablename__ = "report_exports"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False)
    requested_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    format: Mapped[str] = mapped_column(String(16), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="QUEUED")
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
