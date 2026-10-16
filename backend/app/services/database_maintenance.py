from __future__ import annotations

from collections import OrderedDict

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import (
    AlertHistoryORM,
    AlertORM,
    AuditLogORM,
    DecisionRuleORM,
    ImportBatchORM,
    ImportMappingProfileORM,
    ImportedRowORM,
    KpiDefinitionORM,
    KpiSnapshotORM,
    ReportExportORM,
)


BUSINESS_TABLE_ORDER = (
    ("alert_history", AlertHistoryORM),
    ("alerts", AlertORM),
    ("report_exports", ReportExportORM),
    ("audit_logs", AuditLogORM),
    ("kpi_snapshots", KpiSnapshotORM),
    ("kpi_definitions", KpiDefinitionORM),
    ("import_mapping_profiles", ImportMappingProfileORM),
    ("import_rows", ImportedRowORM),
    ("import_batches", ImportBatchORM),
    ("decision_rules", DecisionRuleORM),
)


def collect_business_table_counts(
    db: Session,
    company_id: str | None = None,
) -> OrderedDict[str, int]:
    counts: OrderedDict[str, int] = OrderedDict()
    for label, model in BUSINESS_TABLE_ORDER:
        statement = select(func.count()).select_from(model)
        if company_id and hasattr(model, "company_id"):
            statement = statement.where(model.company_id == company_id)
        counts[label] = int(db.scalar(statement) or 0)
    return counts


def clear_business_data(
    db: Session,
    company_id: str | None = None,
) -> OrderedDict[str, int]:
    deleted_counts = collect_business_table_counts(db, company_id)

    for _, model in BUSINESS_TABLE_ORDER:
        statement = delete(model)
        if company_id and hasattr(model, "company_id"):
            statement = statement.where(model.company_id == company_id)
        db.execute(statement)

    return deleted_counts
