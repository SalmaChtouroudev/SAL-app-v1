from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
import unicodedata

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AlertORM, CompanyORM, DecisionRuleORM, ImportedRowORM
from app.schemas.client_demo import (
    ClientDemoChart,
    ClientDemoChartPoint,
    ClientDemoChartSeries,
    ClientDemoDashboardOverview,
    ClientDemoMetricCard,
    ClientDemoSection,
    ClientDemoTable,
    ClientDemoTableColumn,
)
from app.schemas.platform import AlertRead, AlertTrigger
from app.services.client_demo_catalog import EXPECTED_CLIENT_SOURCES, find_rule_section
from app.services.on_ing_profile import is_on_ing_company


IMPORT_FRAME_COLUMNS = [
    "source_type",
    "business_date",
    "revenue_amount",
    "cost_amount",
    "project_code",
    "project_name",
    "original_project_reference",
    "normalized_project_reference",
    "category",
    "product",
    "client",
    "original_client_name",
    "normalized_client_name",
    "client_group",
    "responsible",
    "resource_name",
    "business_pole",
    "original_business_pole",
    "normalized_business_pole",
    "status",
    "start_date",
    "end_date",
    "forecast_revenue_amount",
    "remaining_to_invoice_amount",
    "purchase_amount",
    "margin_amount",
    "margin_rate",
    "debit_amount",
    "credit_amount",
    "invoice_amount",
    "invoice_number",
    "currency",
    "account_code",
    "subaccount",
    "description",
]


ON_ING_REPORT_FALLBACK = {
    "ca_projects_2025": 117083.00,
    "ca_projects_2026": 50601.75,
    "pnl_2025": 133283.00,
    "pnl_2026": 32583.00,
    "projects_2025": 89,
    "projects_2026": 53,
    "affairs_detected": 123,
    "clients_detected": 14,
    "pieces_detected": 389,
    "missing_subaccounts": 389,
    "debit_credit_gap": 0.0,
    "monthly_target": 15000.0,
    "months_transmitted_2026": 4,
    "quality_score": 71.0,
    "yearly_revenue_projects": [
        {"label": "2025", "value": 117083.00},
        {"label": "2026", "value": 50601.75},
    ],
    "yearly_revenue_pnl": [
        {"label": "2025", "value": 133283.00},
        {"label": "2026", "value": 32583.00},
    ],
    "cumulative_revenue": [
        {"label": "2025", "value": 117083.00},
        {"label": "2026", "value": 167684.75},
    ],
    "yearly_gap": [
        {"label": "2025", "value": 16200.00},
        {"label": "2026", "value": -18018.75},
    ],
    "yearly_mix_table": [
        {"label": "2025", "projects": 117083.00, "pnl": 133283.00, "gap": 16200.00},
        {"label": "2026", "projects": 50601.75, "pnl": 32583.00, "gap": -18018.75},
    ],
    "projects_by_year": [
        {"label": "2025", "value": 89},
        {"label": "2026", "value": 53},
    ],
    "portfolio_counts": [
        {"label": "Affaires detectees", "value": 123},
        {"label": "Clients detectes", "value": 14},
    ],
    "portfolio_overview": [
        {"label": "Projets 2025", "value": 89},
        {"label": "Projets 2026", "value": 53},
        {"label": "Affaires", "value": 123},
        {"label": "Clients", "value": 14},
    ],
    "focus_topics": [
        {"label": "CA", "value": 3},
        {"label": "Clients", "value": 2},
        {"label": "Comptable", "value": 2},
        {"label": "Qualite", "value": 2},
    ],
    "dashboard_axes": [
        {"label": "Vue direction", "value": 1},
        {"label": "Chiffre d'affaires", "value": 1},
        {"label": "Affaires / Projets", "value": 1},
        {"label": "Rentabilite", "value": 1},
        {"label": "Clients", "value": 1},
        {"label": "Previsionnel", "value": 1},
        {"label": "Comptabilite", "value": 1},
        {"label": "Qualite", "value": 1},
    ],
    "profitability_gap": [
        {"label": "2025", "value": 16200.00},
        {"label": "2026", "value": -18018.75},
    ],
    "projection_curve": [
        {"label": "T1 2026", "value": 12650.44},
        {"label": "T2 2026", "value": 25300.88},
        {"label": "T3 2026", "value": 37951.31},
        {"label": "T4 2026", "value": 50601.75},
        {"label": "Projection annuelle", "value": 151805.25},
    ],
    "annual_target_curve": [
        {"label": "T1 2026", "value": 45000.00},
        {"label": "T2 2026", "value": 90000.00},
        {"label": "T3 2026", "value": 135000.00},
        {"label": "T4 2026", "value": 180000.00},
        {"label": "Projection annuelle", "value": 180000.00},
    ],
    "client_risk_signals": [
        {"label": "Dependance client elevee", "value": 3},
        {"label": "Ecart PnL / CAProjets", "value": 2},
        {"label": "Qualite donnees projet", "value": 2},
        {"label": "Marge sous surveillance", "value": 1},
    ],
    "crm_positioning": [
        {"label": "Clients dans CRM", "value": 14},
        {"label": "Affaires dans CRM", "value": 123},
        {"label": "Priorites sales", "value": 5},
    ],
    "client_risk_rows": [
        {"theme": "Dependance client elevee", "status": "A surveiller", "impact": "Risque de concentration du portefeuille"},
        {"theme": "Ecart PnL / CA Projets", "status": "A confirmer", "impact": "Verifier l'alignement reporting / production"},
        {"theme": "Qualite donnees projet", "status": "Action requise", "impact": "Completer les champs projet et client"},
    ],
    "next_steps": [
        {"label": "Charger les sources Excel", "value": 5},
        {"label": "Normaliser references", "value": 4},
        {"label": "Fiabiliser CRM", "value": 3},
        {"label": "Industrialiser reporting", "value": 4},
    ],
    "next_step_rows": [
        {"step": "Charger CA Projets, Toutes Affaires, PnL et comptabilite", "why": "Activer toutes les courbes natives", "priority": "Haute"},
        {"step": "Aligner references affaires / clients", "why": "Eviter les ecarts et doublons", "priority": "Haute"},
        {"step": "Relier la vue CRM au cockpit SAL", "why": "Suivre le pipe commercial de bout en bout", "priority": "Moyenne"},
    ],
    "accounting_controls": [
        {"label": "Pieces detectees", "value": 389},
        {"label": "Sous-comptes manquants", "value": 389},
        {"label": "Ecart debit-credit", "value": 0.0},
    ],
    "accounting_quality": [
        {"label": "Equilibre OK", "value": 1},
        {"label": "Sous-comptes a completer", "value": 389},
    ],
    "accounting_rows": [
        {"metric": "Pieces detectees", "value": 389, "comment": "Base export comptable du rapport"},
        {"metric": "Sous-comptes manquants", "value": 389, "comment": "Enrichissement comptable necessaire"},
        {"metric": "Ecart debit-credit", "value": 0.0, "comment": "Controle d'equilibre passe"},
    ],
    "data_quality_breakdown": [
        {"label": "Sources documentees", "value": 4},
        {"label": "Sous-comptes manquants", "value": 389},
        {"label": "Alertes qualite", "value": 3},
    ],
    "source_coverage": [
        {"label": "CA Projets", "value": 100},
        {"label": "Toutes Affaires", "value": 100},
        {"label": "Reporting PnL", "value": 100},
        {"label": "Export Comptable", "value": 100},
    ],
    "quality_rows": [
        {"theme": "CA Projets", "status": "Disponible dans le rapport", "action": "Charger les fichiers sources pour detail complet"},
        {"theme": "Toutes Affaires", "status": "Disponible dans le rapport", "action": "Aligner les references CRM / affaires"},
        {"theme": "Reporting PnL", "status": "Disponible dans le rapport", "action": "Rapprocher avec CA projets"},
        {"theme": "Export Comptable", "status": "Sous-comptes manquants detectes", "action": "Completer les sous-comptes"},
    ],
    "alert_severity": [
        {"label": "Priorite haute", "value": 2},
        {"label": "Priorite moyenne", "value": 2},
        {"label": "Surveillance", "value": 1},
    ],
    "alert_signal_usage": [
        {"label": "Dependance client", "value": 3},
        {"label": "Ecart PnL / CA", "value": 2},
        {"label": "Qualite donnees", "value": 2},
        {"label": "Controle comptable", "value": 1},
    ],
    "alert_rows": [
        {"theme": "Dependance client elevee", "priority": "Haute", "recommendation": "Suivre la concentration du chiffre d'affaires par client"},
        {"theme": "Ecart PnL / CAProjets", "priority": "Haute", "recommendation": "Verifier le mapping entre sources revenue et PnL"},
        {"theme": "Qualite donnees projet", "priority": "Moyenne", "recommendation": "Completer les references projet et client"},
        {"theme": "Marge sous surveillance", "priority": "Moyenne", "recommendation": "Suivre les affaires a faible rentabilite"},
        {"theme": "Controle comptable", "priority": "Surveillance", "recommendation": "Completer les sous-comptes manquants"},
    ],
}


@dataclass(frozen=True)
class MetricSignal:
    code: str
    label: str
    value: float
    unit: str
    display_value: str
    raw_value: str | float | int | None = None


def load_company_import_frame(db: Session, company_id: str) -> pd.DataFrame:
    rows = db.scalars(
        select(ImportedRowORM)
        .where(ImportedRowORM.company_id == company_id)
        .order_by(ImportedRowORM.business_date.asc(), ImportedRowORM.created_at.asc())
    ).all()
    if not rows:
        return pd.DataFrame(columns=IMPORT_FRAME_COLUMNS)

    records = [
        {
            "source_type": row.source_type,
            "business_date": row.business_date,
            "revenue_amount": row.revenue_amount,
            "cost_amount": row.cost_amount,
            "project_code": row.project_code,
            "project_name": row.project_name,
            "original_project_reference": row.original_project_reference,
            "normalized_project_reference": row.normalized_project_reference,
            "category": row.category,
            "product": row.product,
            "client": row.client,
            "original_client_name": row.original_client_name,
            "normalized_client_name": row.normalized_client_name,
            "client_group": row.client_group,
            "responsible": row.responsible,
            "resource_name": row.resource_name,
            "business_pole": row.business_pole,
            "original_business_pole": row.original_business_pole,
            "normalized_business_pole": row.normalized_business_pole,
            "status": row.status,
            "start_date": row.start_date,
            "end_date": row.end_date,
            "forecast_revenue_amount": row.forecast_revenue_amount,
            "remaining_to_invoice_amount": row.remaining_to_invoice_amount,
            "purchase_amount": row.purchase_amount,
            "margin_amount": row.margin_amount,
            "margin_rate": row.margin_rate,
            "debit_amount": row.debit_amount,
            "credit_amount": row.credit_amount,
            "invoice_amount": row.invoice_amount,
            "invoice_number": row.invoice_number,
            "currency": row.currency,
            "account_code": row.account_code,
            "subaccount": row.subaccount,
            "description": row.description,
        }
        for row in rows
    ]
    return prepare_import_frame(pd.DataFrame.from_records(records, columns=IMPORT_FRAME_COLUMNS))


def build_metric_signals(frame: pd.DataFrame, currency: str) -> dict[str, MetricSignal]:
    prepared = prepare_import_frame(frame)
    revenue_frame = select_preferred_revenue_frame(prepared)
    project_frame = select_project_snapshot_frame(prepared)
    pnl_frame = prepared[prepared["source_type"] == "pnl"].copy()
    accounting_frame = prepared[prepared["source_type"] == "accounting"].copy()

    revenue_by_month = aggregate_by_period(revenue_frame, "revenue_amount", "month")
    pnl_actual_by_month = aggregate_by_period(
        pnl_frame if not pnl_frame.empty else revenue_frame,
        "revenue_amount",
        "month",
    )
    pnl_forecast_by_month = aggregate_by_period(pnl_frame, "forecast_revenue_amount", "month")
    margin_by_month = aggregate_by_period(
        pnl_frame if not pnl_frame.empty else revenue_frame,
        "margin_effective",
        "month",
    )

    latest_revenue = float(revenue_by_month["value"].iloc[-1]) if not revenue_by_month.empty else 0.0
    previous_revenue = (
        float(revenue_by_month["value"].iloc[-2]) if len(revenue_by_month.index) > 1 else 0.0
    )
    latest_margin = float(margin_by_month["value"].iloc[-1]) if not margin_by_month.empty else 0.0
    latest_forecast = (
        float(pnl_forecast_by_month["value"].iloc[-1]) if not pnl_forecast_by_month.empty else 0.0
    )
    available_dates = pd.to_datetime(
        prepared.get("business_date", pd.Series(dtype="object")),
        errors="coerce",
        utc=True,
    )
    revenue_years = sorted({int(year) for year in available_dates.dropna().dt.year.tolist()})
    current_year = revenue_years[-1] if revenue_years else datetime.now(tz=timezone.utc).year
    previous_year = revenue_years[-2] if len(revenue_years) > 1 else current_year - 1

    ca_total = float(revenue_frame["revenue_amount"].fillna(0).sum())
    ca_monthly = latest_revenue
    ca_cumulative = sum_year(revenue_frame, current_year, "revenue_amount")
    forecast_revenue = float(
        (
            pnl_frame["forecast_revenue_amount"]
            if not pnl_frame.empty
            else prepared["forecast_revenue_amount"]
        ).fillna(0).sum()
    )
    forecast_achievement = ca_total / forecast_revenue * 100 if forecast_revenue else 0.0
    forecast_gap = abs(ca_total - forecast_revenue) / forecast_revenue * 100 if forecast_revenue else 0.0
    growth = percent_change(latest_revenue, previous_revenue)
    previous_year_revenue = sum_year(revenue_frame, previous_year, "revenue_amount")
    yoy_growth = percent_change(ca_cumulative, previous_year_revenue)

    total_revenue = ca_total
    total_margin = float(revenue_frame["margin_effective"].fillna(0).sum())
    margin_rate = total_margin / total_revenue * 100 if total_revenue else 0.0
    rex = latest_margin
    cumulative_rex = float(margin_by_month["value"].sum()) if not margin_by_month.empty else total_margin

    total_projects = count_distinct_non_empty(project_frame, "project_key")
    active_projects = int(project_frame["is_in_progress"].sum())
    low_margin_projects = int(
        (
            project_frame["margin_rate_effective"].fillna(0) < 30
        ).sum()
    )
    loss_risk_projects = int(
        (
            project_frame["purchase_effective"].fillna(0)
            > project_frame["revenue_amount"].fillna(0)
        ).sum()
    )
    missing_responsible = int(project_frame["responsible"].eq("").sum())
    missing_resource = int(project_frame["resource_name"].fillna("").eq("").sum())
    missing_end_date = int(project_frame["end_date"].isna().sum())
    overdue_projects = int(project_frame["is_overdue"].sum())
    remaining_invoice_series = pd.to_numeric(
        project_frame["remaining_to_invoice_amount"], errors="coerce"
    ).fillna(0.0)
    remaining_to_invoice_amount = float(remaining_invoice_series.clip(lower=0).sum())
    projects_with_remaining_invoice = int((remaining_invoice_series > 0).sum())
    average_ca_per_project = total_revenue / total_projects if total_projects else 0.0
    billing_rate = (
        total_revenue / (total_revenue + remaining_to_invoice_amount) * 100
        if (total_revenue + remaining_to_invoice_amount)
        else 0.0
    )

    active_clients_count = count_distinct_non_empty(revenue_frame, "client")
    client_revenue = aggregate_group_sum(revenue_frame, "client", "revenue_amount")
    client_totals = aggregate_group_totals(
        revenue_frame,
        "client",
        ["revenue_amount", "margin_effective", "remaining_to_invoice_amount"],
    )
    if not client_totals.empty and total_revenue:
        client_totals["share_pct"] = client_totals["revenue_amount"] / total_revenue * 100
    else:
        client_totals["share_pct"] = pd.Series(dtype="float64")
    if not client_totals.empty:
        client_totals["margin_rate_pct"] = client_totals.apply(
            lambda row: row["margin_effective"] / row["revenue_amount"] * 100
            if row["revenue_amount"]
            else 0.0,
            axis=1,
        )
    else:
        client_totals["margin_rate_pct"] = pd.Series(dtype="float64")
    top_client_name = str(client_revenue["label"].iloc[0]) if not client_revenue.empty else ""
    top_client_revenue = float(client_revenue["value"].iloc[0]) if not client_revenue.empty else 0.0
    risky_clients_count = int(
        (
            (client_totals["share_pct"].fillna(0) > 25)
            | (client_totals["margin_rate_pct"].fillna(0) < 15)
        ).sum()
    )

    total_debit = float(accounting_frame["debit_amount"].fillna(0).sum())
    total_credit = float(accounting_frame["credit_amount"].fillna(0).sum())
    accounting_entries_count = int(len(accounting_frame.index))
    duplicate_piece_count = count_duplicate_non_empty_values(accounting_frame["invoice_number"])
    missing_subaccount = int(accounting_frame["subaccount"].fillna("").eq("").sum())
    invalid_invoice_amount = int(
        (
            accounting_frame["invoice_effective_amount"].fillna(0) <= 0
        ).sum()
    )

    base_currency = detect_primary_currency(accounting_frame, currency)
    foreign_currency_entries = int(
        (
            accounting_frame["currency"].ne("")
            & accounting_frame["currency"].ne(base_currency)
        ).sum()
    )

    client_concentration = (
        top_client_revenue / total_revenue * 100
        if total_revenue and top_client_revenue
        else 0.0
    )

    missing_pole_count = int(project_frame["original_business_pole"].fillna("").eq("").sum())
    missing_margin_rate_count = int(project_frame["margin_rate"].isna().sum())
    duplicate_project_reference_count = count_duplicate_non_empty_values(
        project_frame["normalized_project_reference"]
    )
    missing_facturation_count = int(project_frame["remaining_to_invoice_amount"].isna().sum())
    quality_issue_total = (
        missing_resource
        + missing_pole_count
        + missing_margin_rate_count
        + duplicate_project_reference_count
        + missing_end_date
        + missing_facturation_count
    )
    quality_scope = max(total_projects * 6, 1)
    data_quality_score = max(0.0, round(100 - (quality_issue_total / quality_scope) * 100, 1))

    signals = [
        MetricSignal(
            code="ca_total",
            label="Chiffre d'affaires réalisé",
            value=ca_total,
            unit="currency",
            display_value=format_currency(ca_total, currency),
        ),
        MetricSignal(
            code="ca_monthly",
            label="CA du dernier mois",
            value=ca_monthly,
            unit="currency",
            display_value=format_currency(ca_monthly, currency),
        ),
        MetricSignal(
            code="ca_cumulative",
            label=f"CA cumulé {current_year}",
            value=ca_cumulative,
            unit="currency",
            display_value=format_currency(ca_cumulative, currency),
        ),
        MetricSignal(
            code="forecast_revenue",
            label="CA prévisionnel",
            value=forecast_revenue,
            unit="currency",
            display_value=format_currency(forecast_revenue, currency),
        ),
        MetricSignal(
            code="latest_month_revenue_delta_vs_forecast",
            label="Écart CA réalisé vs prévisionnel",
            value=float(pnl_actual_by_month["value"].iloc[-1]) - latest_forecast
            if not pnl_actual_by_month.empty
            else latest_revenue - latest_forecast,
            unit="currency",
            display_value=format_currency(
                (
                    float(pnl_actual_by_month["value"].iloc[-1]) - latest_forecast
                    if not pnl_actual_by_month.empty
                    else latest_revenue - latest_forecast
                ),
                currency,
            ),
        ),
        MetricSignal(
            code="forecast_gap_pct",
            label="Écart prévisionnel",
            value=forecast_gap,
            unit="percent",
            display_value=format_percent(forecast_gap),
        ),
        MetricSignal(
            code="forecast_achievement_pct",
            label="Taux d'atteinte prévisionnel",
            value=forecast_achievement,
            unit="percent",
            display_value=format_percent(forecast_achievement),
        ),
        MetricSignal(
            code="latest_month_growth_pct",
            label="Croissance mensuelle",
            value=growth,
            unit="percent",
            display_value=format_percent(growth),
        ),
        MetricSignal(
            code="cumulative_revenue_yoy_growth_pct",
            label=f"Croissance cumulée {current_year} vs {previous_year}",
            value=yoy_growth,
            unit="percent",
            display_value=format_percent(yoy_growth),
        ),
        MetricSignal(
            code="total_margin",
            label="Marge globale",
            value=total_margin,
            unit="currency",
            display_value=format_currency(total_margin, currency),
        ),
        MetricSignal(
            code="margin_rate_pct",
            label="Taux de marge",
            value=margin_rate,
            unit="percent",
            display_value=format_percent(margin_rate),
        ),
        MetricSignal(
            code="rex",
            label="REX mensuel",
            value=rex,
            unit="currency",
            display_value=format_currency(rex, currency),
        ),
        MetricSignal(
            code="cumulative_rex",
            label="REX cumulé",
            value=cumulative_rex,
            unit="currency",
            display_value=format_currency(cumulative_rex, currency),
        ),
        MetricSignal(
            code="total_projects_count",
            label="Nombre total de projets",
            value=float(total_projects),
            unit="count",
            display_value=format_number(total_projects),
        ),
        MetricSignal(
            code="active_projects_count",
            label="Projets actifs",
            value=float(active_projects),
            unit="count",
            display_value=format_number(active_projects),
        ),
        MetricSignal(
            code="overdue_projects_count",
            label="Projets en retard",
            value=float(overdue_projects),
            unit="count",
            display_value=format_number(overdue_projects),
        ),
        MetricSignal(
            code="low_margin_project_count",
            label="Projets à faible marge",
            value=float(low_margin_projects),
            unit="count",
            display_value=format_number(low_margin_projects),
        ),
        MetricSignal(
            code="loss_risk_project_count",
            label="Projets à risque de perte",
            value=float(loss_risk_projects),
            unit="count",
            display_value=format_number(loss_risk_projects),
        ),
        MetricSignal(
            code="missing_responsible_count",
            label="Projets sans responsable",
            value=float(missing_responsible),
            unit="count",
            display_value=format_number(missing_responsible),
        ),
        MetricSignal(
            code="missing_resource_count",
            label="Projets sans ressource",
            value=float(missing_resource),
            unit="count",
            display_value=format_number(missing_resource),
        ),
        MetricSignal(
            code="missing_end_date_count",
            label="Projets sans date de fin",
            value=float(missing_end_date),
            unit="count",
            display_value=format_number(missing_end_date),
        ),
        MetricSignal(
            code="remaining_to_invoice_amount",
            label="Reste à facturer",
            value=remaining_to_invoice_amount,
            unit="currency",
            display_value=format_currency(remaining_to_invoice_amount, currency),
        ),
        MetricSignal(
            code="projects_with_remaining_invoice_count",
            label="Projets avec reste à facturer",
            value=float(projects_with_remaining_invoice),
            unit="count",
            display_value=format_number(projects_with_remaining_invoice),
        ),
        MetricSignal(
            code="average_ca_per_project",
            label="CA moyen par projet",
            value=average_ca_per_project,
            unit="currency",
            display_value=format_currency(average_ca_per_project, currency),
        ),
        MetricSignal(
            code="billing_rate_pct",
            label="Taux de facturation",
            value=billing_rate,
            unit="percent",
            display_value=format_percent(billing_rate),
        ),
        MetricSignal(
            code="active_clients_count",
            label="Clients actifs",
            value=float(active_clients_count),
            unit="count",
            display_value=format_number(active_clients_count),
        ),
        MetricSignal(
            code="top_client_name",
            label="Principal client",
            value=0.0,
            unit="text",
            display_value=top_client_name or "n/a",
            raw_value=top_client_name or None,
        ),
        MetricSignal(
            code="top_client_revenue",
            label="CA du principal client",
            value=top_client_revenue,
            unit="currency",
            display_value=format_currency(top_client_revenue, currency),
        ),
        MetricSignal(
            code="client_concentration_pct",
            label="Dépendance au premier client",
            value=client_concentration,
            unit="percent",
            display_value=format_percent(client_concentration),
        ),
        MetricSignal(
            code="risky_clients_count",
            label="Clients à surveiller",
            value=float(risky_clients_count),
            unit="count",
            display_value=format_number(risky_clients_count),
        ),
        MetricSignal(
            code="total_debit",
            label="Total débit",
            value=total_debit,
            unit="currency",
            display_value=format_currency(total_debit, currency),
        ),
        MetricSignal(
            code="total_credit",
            label="Total crédit",
            value=total_credit,
            unit="currency",
            display_value=format_currency(total_credit, currency),
        ),
        MetricSignal(
            code="debit_credit_difference",
            label="Écart débit / crédit",
            value=abs(total_debit - total_credit),
            unit="currency",
            display_value=format_currency(abs(total_debit - total_credit), currency),
        ),
        MetricSignal(
            code="accounting_entries_count",
            label="Écritures comptables",
            value=float(accounting_entries_count),
            unit="count",
            display_value=format_number(accounting_entries_count),
        ),
        MetricSignal(
            code="duplicate_piece_count",
            label="Pièces dupliquées",
            value=float(duplicate_piece_count),
            unit="count",
            display_value=format_number(duplicate_piece_count),
        ),
        MetricSignal(
            code="missing_subaccount_count",
            label="Écritures sans sous-compte",
            value=float(missing_subaccount),
            unit="count",
            display_value=format_number(missing_subaccount),
        ),
        MetricSignal(
            code="invalid_invoice_amount_count",
            label="Montants anormaux",
            value=float(invalid_invoice_amount),
            unit="count",
            display_value=format_number(invalid_invoice_amount),
        ),
        MetricSignal(
            code="foreign_currency_entries_count",
            label="Écritures en devise à vérifier",
            value=float(foreign_currency_entries),
            unit="count",
            display_value=format_number(foreign_currency_entries),
        ),
        MetricSignal(
            code="missing_pole_count",
            label="Pôles non renseignés",
            value=float(missing_pole_count),
            unit="count",
            display_value=format_number(missing_pole_count),
        ),
        MetricSignal(
            code="missing_margin_rate_count",
            label="Taux de marge manquants",
            value=float(missing_margin_rate_count),
            unit="count",
            display_value=format_number(missing_margin_rate_count),
        ),
        MetricSignal(
            code="duplicate_project_reference_count",
            label="Références projet dupliquées",
            value=float(duplicate_project_reference_count),
            unit="count",
            display_value=format_number(duplicate_project_reference_count),
        ),
        MetricSignal(
            code="missing_facturation_count",
            label="Lignes sans donnée de facturation",
            value=float(missing_facturation_count),
            unit="count",
            display_value=format_number(missing_facturation_count),
        ),
        MetricSignal(
            code="data_quality_score",
            label="Score qualité des données",
            value=data_quality_score,
            unit="percent",
            display_value=format_percent(data_quality_score),
        ),
    ]
    return {signal.code: signal for signal in signals}


class ClientDemoAnalyticsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_overview(self, company_id: str) -> ClientDemoDashboardOverview:
        company = self.db.scalar(select(CompanyORM).where(CompanyORM.id == company_id))
        currency = company.currency if company else "TND"
        frame = load_company_import_frame(self.db, company_id)
        available_sources = sorted(
            {
                EXPECTED_CLIENT_SOURCES.get(source_type, source_type)
                for source_type in frame.get("source_type", pd.Series(dtype="object")).tolist()
                if source_type in EXPECTED_CLIENT_SOURCES
            }
        )
        missing_sources = [
            label for source_type, label in EXPECTED_CLIENT_SOURCES.items() if label not in available_sources
        ]
        alerts = self._list_alerts(company_id)
        alerts_by_section = self._group_alerts_by_section(alerts)
        sections = self._build_sections(company_id, frame, currency, alerts_by_section)

        return ClientDemoDashboardOverview(
            companyId=company_id,
            generatedAt=datetime.now(tz=timezone.utc).isoformat(),
            availableSources=available_sources,
            missingSources=missing_sources,
            sections=sections,
            activeAlerts=alerts,
        )

    def _build_sections(
        self,
        company_id: str,
        frame: pd.DataFrame,
        currency: str,
        alerts_by_section: dict[str, list[AlertRead]],
    ) -> list[ClientDemoSection]:
        prepared = prepare_import_frame(frame)
        revenue_frame = select_preferred_revenue_frame(prepared)
        project_frame = select_project_snapshot_frame(prepared)
        pnl_frame = prepared[prepared["source_type"] == "pnl"].copy()
        accounting_frame = prepared[prepared["source_type"] == "accounting"].copy()
        signals = build_metric_signals(prepared, currency)

        if is_on_ing_company(company_id):
            if self._should_use_on_ing_report_fallback(
                revenue_frame,
                project_frame,
                pnl_frame,
                accounting_frame,
            ):
                return self._build_on_ing_report_fallback_sections(
                    currency,
                    alerts_by_section,
                    company_id,
                )
            return self._build_on_ing_sections(
                revenue_frame,
                project_frame,
                pnl_frame,
                accounting_frame,
                currency,
                alerts_by_section,
                signals,
                company_id,
            )

        return [
            self._build_general_section(
                revenue_frame,
                project_frame,
                currency,
                alerts_by_section.get("dashboard-general", []),
            ),
            self._build_ca_section(
                revenue_frame,
                currency,
                alerts_by_section.get("analyse-ca-projets", []),
            ),
            self._build_affairs_section(
                project_frame,
                currency,
                alerts_by_section.get("suivi-affaires", []),
            ),
            self._build_pnl_section(
                pnl_frame,
                revenue_frame,
                currency,
                alerts_by_section.get("reporting-pnl", []),
            ),
            self._build_accounting_section(
                accounting_frame,
                currency,
                alerts_by_section.get("controle-comptable", []),
            ),
            self._build_alert_section(
                alerts_by_section.get("alertes-regles", []),
                company_id=company_id,
                signals=signals,
            ),
        ]

    def _should_use_on_ing_report_fallback(
        self,
        revenue_frame: pd.DataFrame,
        project_frame: pd.DataFrame,
        pnl_frame: pd.DataFrame,
        accounting_frame: pd.DataFrame,
    ) -> bool:
        return (
            revenue_frame.empty
            and project_frame.empty
            and pnl_frame.empty
            and accounting_frame.empty
        )

    def _build_on_ing_report_fallback_sections(
        self,
        currency: str,
        alerts_by_section: dict[str, list[AlertRead]],
        company_id: str,
    ) -> list[ClientDemoSection]:
        report = ON_ING_REPORT_FALLBACK

        direction_cards = [
            metric_card("on-ing-report-ca-2025", "CA projets 2025", report["ca_projects_2025"], "currency", currency),
            metric_card("on-ing-report-ca-2026", "CA projets 2026 transmis", report["ca_projects_2026"], "currency", currency),
            metric_card("on-ing-report-pnl-2025", "CA Reporting PnL 2025", report["pnl_2025"], "currency", currency),
            metric_card("on-ing-report-pnl-2026", "CA Reporting PnL 2026 transmis", report["pnl_2026"], "currency", currency),
            metric_card("on-ing-report-affairs", "Affaires detectees", report["affairs_detected"], "count", currency),
            metric_card("on-ing-report-clients", "Clients detectes", report["clients_detected"], "count", currency),
            metric_card(
                "on-ing-report-ecart-pnl",
                "Ecart PnL 2025 vs CA projets 2025",
                percent_change(report["pnl_2025"], report["ca_projects_2025"]),
                "percent",
                currency,
                tone=resolve_percent_tone(percent_change(report["pnl_2025"], report["ca_projects_2025"])),
            ),
        ]

        direction_charts = [
            bar_chart(
                "on-ing-report-direction-ca-comparison",
                "Comparatif CA projets vs Reporting PnL",
                [
                    chart_series("projects", "CA projets", report_frame(report["yearly_revenue_projects"])),
                    chart_series("pnl", "Reporting PnL", report_frame(report["yearly_revenue_pnl"])),
                ],
            ),
            bar_chart(
                "on-ing-report-direction-project-flow",
                "Volume affaires et clients detectes",
                [chart_series("portfolio", "Portefeuille", report_frame(report["portfolio_overview"]))],
            ),
            donut_chart(
                "on-ing-report-direction-alerts",
                "Themes de pilotage a surveiller",
                [chart_series("topics", "Themes", report_frame(report["focus_topics"]))],
            ),
        ]

        direction_tables = [
            table_from_frame(
                "on-ing-report-direction-sources",
                "Sources analysees dans le rapport",
                pd.DataFrame(
                    [
                        {"source": "CA Projets", "coverage": "2025-2026", "status": "Analyse report disponible"},
                        {"source": "Toutes Affaires", "coverage": "Portefeuille commercial", "status": "Synthese report disponible"},
                        {"source": "Reporting PnL", "coverage": "2025-2026", "status": "Analyse report disponible"},
                        {"source": "Export Comptable", "coverage": "Controle comptable", "status": "Analyse report disponible"},
                    ]
                ),
                [("source", "Source"), ("coverage", "Perimetre"), ("status", "Etat")],
            )
        ]

        revenue_cards = [
            metric_card("on-ing-report-revenue-2025", "CA projets 2025", report["ca_projects_2025"], "currency", currency),
            metric_card("on-ing-report-revenue-2026", "CA projets 2026", report["ca_projects_2026"], "currency", currency),
            metric_card(
                "on-ing-report-revenue-growth",
                "Variation CA projets 2026 vs 2025",
                percent_change(report["ca_projects_2026"], report["ca_projects_2025"]),
                "percent",
                currency,
                tone=resolve_percent_tone(percent_change(report["ca_projects_2026"], report["ca_projects_2025"])),
            ),
            metric_card(
                "on-ing-report-revenue-cumulative",
                "CA projets cumule",
                report["ca_projects_2025"] + report["ca_projects_2026"],
                "currency",
                currency,
            ),
            metric_card(
                "on-ing-report-pnl-gap",
                "Ecart absolu PnL / CA projets 2026",
                abs(report["pnl_2026"] - report["ca_projects_2026"]),
                "currency",
                currency,
            ),
        ]

        revenue_charts = [
            line_chart(
                "on-ing-report-revenue-evolution",
                "Evolution du chiffre d'affaires",
                [chart_series("projects", "CA projets", report_frame(report["yearly_revenue_projects"]))],
            ),
            bar_chart(
                "on-ing-report-revenue-cumulative",
                "Chiffre d'affaires cumule",
                [chart_series("cumulative", "CA cumule", report_frame(report["cumulative_revenue"]))],
            ),
            bar_chart(
                "on-ing-report-revenue-pnl-gap",
                "Ecart entre CA projets et Reporting PnL",
                [chart_series("gap", "Ecart", report_frame(report["yearly_gap"]))],
            ),
        ]

        revenue_tables = [
            table_from_frame(
                "on-ing-report-revenue-table",
                "Synthese chiffre d'affaires",
                pd.DataFrame(
                    [
                        {
                            "year": row["label"],
                            "ca_projects": row["projects"],
                            "reporting_pnl": row["pnl"],
                            "gap": row["gap"],
                        }
                        for row in report["yearly_mix_table"]
                    ]
                ),
                [("year", "Annee"), ("ca_projects", "CA projets"), ("reporting_pnl", "Reporting PnL"), ("gap", "Ecart")],
            )
        ]

        projects_cards = [
            metric_card("on-ing-report-projects-2025", "Projets analyses 2025", report["projects_2025"], "count", currency),
            metric_card("on-ing-report-projects-2026", "Projets analyses 2026", report["projects_2026"], "count", currency),
            metric_card("on-ing-report-affairs-detected", "Affaires detectees", report["affairs_detected"], "count", currency),
            metric_card(
                "on-ing-report-projects-delta",
                "Variation volume projets 2026 vs 2025",
                percent_change(report["projects_2026"], report["projects_2025"]),
                "percent",
                currency,
                tone=resolve_percent_tone(percent_change(report["projects_2026"], report["projects_2025"])),
            ),
            metric_card(
                "on-ing-report-clients-per-affair",
                "Ratio clients / affaires",
                round(report["clients_detected"] / report["affairs_detected"] * 100, 2),
                "percent",
                currency,
            ),
            metric_card(
                "on-ing-report-ca-per-project",
                "CA moyen par projet 2025-2026",
                round(
                    (report["ca_projects_2025"] + report["ca_projects_2026"])
                    / max(report["projects_2025"] + report["projects_2026"], 1),
                    2,
                ),
                "currency",
                currency,
            ),
        ]

        projects_charts = [
            bar_chart(
                "on-ing-report-projects-volume",
                "Projets analyses par annee",
                [chart_series("projects", "Projets", report_frame(report["projects_by_year"]))],
            ),
            bar_chart(
                "on-ing-report-projects-portfolio",
                "Affaires detectees vs clients detectes",
                [chart_series("portfolio", "Volume", report_frame(report["portfolio_counts"]))],
            ),
            donut_chart(
                "on-ing-report-projects-focus",
                "Axes du dossier client ON ING",
                [chart_series("axes", "Axes", report_frame(report["dashboard_axes"]))],
            ),
        ]

        projects_tables = [
            table_from_frame(
                "on-ing-report-projects-table",
                "Points cles affaires / projets",
                pd.DataFrame(
                    [
                        {"metric": "Projets analyses en 2025", "value": report["projects_2025"], "comment": "Base rapport client"},
                        {"metric": "Projets analyses en 2026", "value": report["projects_2026"], "comment": "Base rapport client"},
                        {"metric": "Affaires detectees", "value": report["affairs_detected"], "comment": "Toutes Affaires"},
                        {"metric": "Clients detectes", "value": report["clients_detected"], "comment": "Portefeuille client"},
                    ]
                ),
                [("metric", "Indicateur"), ("value", "Valeur"), ("comment", "Lecture")],
            )
        ]

        profitability_cards = [
            metric_card(
                "on-ing-report-margin-gap-2025",
                "Ecart PnL - CA projets 2025",
                report["pnl_2025"] - report["ca_projects_2025"],
                "currency",
                currency,
                tone="warning",
            ),
            metric_card(
                "on-ing-report-margin-gap-2026",
                "Ecart PnL - CA projets 2026",
                report["pnl_2026"] - report["ca_projects_2026"],
                "currency",
                currency,
                tone="danger" if report["pnl_2026"] < report["ca_projects_2026"] else "success",
            ),
            metric_card(
                "on-ing-report-pnl-coverage",
                "Couverture PnL 2026 / 2025",
                percent_change(report["pnl_2026"], report["pnl_2025"]),
                "percent",
                currency,
                tone=resolve_percent_tone(percent_change(report["pnl_2026"], report["pnl_2025"])),
            ),
            metric_card(
                "on-ing-report-project-value",
                "CA moyen par affaire detectee",
                round((report["ca_projects_2025"] + report["ca_projects_2026"]) / max(report["affairs_detected"], 1), 2),
                "currency",
                currency,
            ),
            metric_card("on-ing-report-monthly-target", "Objectif mensuel rappelle", report["monthly_target"], "currency", currency),
            metric_card(
                "on-ing-report-yearly-run-rate",
                "Run rate 2026 annualise",
                round(report["ca_projects_2026"] * 12 / max(report["months_transmitted_2026"], 1), 2),
                "currency",
                currency,
            ),
        ]

        profitability_charts = [
            bar_chart(
                "on-ing-report-profitability-gap",
                "Rentabilite et marge",
                [chart_series("gap", "Ecart PnL - CA projets", report_frame(report["profitability_gap"]))],
            ),
            line_chart(
                "on-ing-report-profitability-run-rate",
                "Projection simple du CA 2026",
                [chart_series("projection", "Projection", report_frame(report["projection_curve"]))],
            ),
        ]

        profitability_tables = [
            table_from_frame(
                "on-ing-report-profitability-table",
                "Lecture rentabilite",
                pd.DataFrame(
                    [
                        {"year": "2025", "ca_projects": report["ca_projects_2025"], "reporting_pnl": report["pnl_2025"], "observation": "PnL au-dessus du CA projets"},
                        {"year": "2026", "ca_projects": report["ca_projects_2026"], "reporting_pnl": report["pnl_2026"], "observation": "PnL transmis sous le CA projets"},
                    ]
                ),
                [("year", "Annee"), ("ca_projects", "CA projets"), ("reporting_pnl", "Reporting PnL"), ("observation", "Observation")],
            )
        ]

        clients_cards = [
            metric_card("on-ing-report-client-count", "Clients detectes", report["clients_detected"], "count", currency),
            metric_card(
                "on-ing-report-client-density",
                "Affaires par client",
                round(report["affairs_detected"] / max(report["clients_detected"], 1), 2),
                "count",
                currency,
            ),
            metric_card("on-ing-report-top-risk-clients", "Themes risque client suivis", len(report["client_risk_signals"]), "count", currency),
            metric_card("on-ing-report-focus-commercial", "Alertes commerciales", 2, "count", currency),
        ]

        clients_charts = [
            donut_chart(
                "on-ing-report-clients-risk",
                "Analyse clients et risque commercial",
                [chart_series("risks", "Risque", report_frame(report["client_risk_signals"]))],
            ),
            bar_chart(
                "on-ing-report-clients-portfolio",
                "Positionnement par rapport au CRM",
                [chart_series("crm", "Positionnement", report_frame(report["crm_positioning"]))],
            ),
        ]

        clients_tables = [
            table_from_frame(
                "on-ing-report-clients-table",
                "Memo risque client",
                pd.DataFrame(report["client_risk_rows"]),
                [("theme", "Theme"), ("status", "Statut"), ("impact", "Impact")],
            )
        ]

        forecast_cards = [
            metric_card("on-ing-report-target", "Objectif mensuel", report["monthly_target"], "currency", currency),
            metric_card(
                "on-ing-report-2026-run-rate",
                "CA 2026 annualise",
                round(report["ca_projects_2026"] * 12 / max(report["months_transmitted_2026"], 1), 2),
                "currency",
                currency,
            ),
            metric_card(
                "on-ing-report-target-gap",
                "Ecart a l'objectif annuel",
                round(report["monthly_target"] * 12 - (report["ca_projects_2026"] * 12 / max(report["months_transmitted_2026"], 1)), 2),
                "currency",
                currency,
                tone="warning",
            ),
            metric_card("on-ing-report-next-step", "Prochaine etape proposee", 1, "count", currency, helper="Industrialiser les imports sources ON ING"),
            metric_card("on-ing-report-sources-ready", "Sources requises a charger", 4, "count", currency),
        ]

        forecast_charts = [
            line_chart(
                "on-ing-report-forecast-target",
                "Projection vs objectif",
                [
                    chart_series("projection", "Projection 2026", report_frame(report["projection_curve"])),
                    chart_series("target", "Objectif annuel", report_frame(report["annual_target_curve"])),
                ],
            ),
            bar_chart(
                "on-ing-report-forecast-action-plan",
                "Proposition de prochaine etape",
                [chart_series("actions", "Priorite", report_frame(report["next_steps"]))],
            ),
        ]

        forecast_tables = [
            table_from_frame(
                "on-ing-report-forecast-table",
                "Plan de passage a l'echelle",
                pd.DataFrame(report["next_step_rows"]),
                [("step", "Etape"), ("why", "Pourquoi"), ("priority", "Priorite")],
            )
        ]

        accounting_cards = [
            metric_card("on-ing-report-accounting-pieces", "Pieces detectees", report["pieces_detected"], "count", currency),
            metric_card("on-ing-report-accounting-subaccounts", "Sous-comptes manquants", report["missing_subaccounts"], "count", currency, tone="danger"),
            metric_card("on-ing-report-accounting-gap", "Ecart debit-credit", report["debit_credit_gap"], "currency", currency, tone="success"),
            metric_card(
                "on-ing-report-accounting-coverage",
                "Taux sous-comptes manquants",
                round(report["missing_subaccounts"] / max(report["pieces_detected"], 1) * 100, 2),
                "percent",
                currency,
                tone="danger",
            ),
            metric_card("on-ing-report-accounting-controls", "Controles comptables suivis", 3, "count", currency),
            metric_card("on-ing-report-accounting-ready", "Statut controle", 1, "count", currency, helper="Equilibre debit-credit verifie"),
        ]

        accounting_charts = [
            bar_chart(
                "on-ing-report-accounting-control",
                "Controle comptable",
                [chart_series("control", "Controle", report_frame(report["accounting_controls"]))],
            ),
            donut_chart(
                "on-ing-report-accounting-anomalies",
                "Qualite des donnees comptables",
                [chart_series("quality", "Qualite", report_frame(report["accounting_quality"]))],
            ),
        ]

        accounting_tables = [
            table_from_frame(
                "on-ing-report-accounting-table",
                "Lecture comptable",
                pd.DataFrame(report["accounting_rows"]),
                [("metric", "Indicateur"), ("value", "Valeur"), ("comment", "Commentaire")],
            )
        ]

        quality_cards = [
            metric_card("on-ing-report-quality-score", "Indice qualite deduit", report["quality_score"], "percent", currency, tone=resolve_margin_tone(report["quality_score"])),
            metric_card("on-ing-report-quality-missing-subaccounts", "Sous-comptes a completer", report["missing_subaccounts"], "count", currency, tone="danger"),
            metric_card("on-ing-report-quality-data-sources", "Familles de sources analysees", 4, "count", currency),
            metric_card("on-ing-report-quality-top-alerts", "Alertes donnees majeures", 3, "count", currency),
            metric_card("on-ing-report-quality-balance", "Equilibre comptable", report["debit_credit_gap"], "currency", currency, tone="success"),
        ]

        quality_charts = [
            donut_chart(
                "on-ing-report-quality-breakdown",
                "Qualite des donnees",
                [chart_series("quality", "Etat", report_frame(report["data_quality_breakdown"]))],
            ),
            bar_chart(
                "on-ing-report-quality-sources",
                "Couverture des sources ON ING",
                [chart_series("sources", "Couverture", report_frame(report["source_coverage"]))],
            ),
        ]

        quality_tables = [
            table_from_frame(
                "on-ing-report-quality-table",
                "Memo qualite",
                pd.DataFrame(report["quality_rows"]),
                [("theme", "Theme"), ("status", "Statut"), ("action", "Action")],
            )
        ]

        alert_cards = [
            metric_card("on-ing-report-alert-count", "Alertes rapport", len(report["alert_rows"]), "count", currency),
            metric_card("on-ing-report-alert-critical", "Alertes prioritaires", 2, "count", currency, tone="danger"),
            metric_card("on-ing-report-alert-data", "Alertes qualite donnees", 2, "count", currency, tone="warning"),
            metric_card("on-ing-report-alert-finance", "Alertes finance", 1, "count", currency, tone="warning"),
            metric_card("on-ing-report-alert-next", "Actions recommandees", len(report["next_step_rows"]), "count", currency),
        ]

        alert_charts = [
            donut_chart(
                "on-ing-report-alert-severity",
                "Alertes et recommandations SAL",
                [chart_series("severity", "Severite", report_frame(report["alert_severity"]))],
            ),
            bar_chart(
                "on-ing-report-alert-themes",
                "Signaux utilises par les regles",
                [chart_series("signals", "Signaux", report_frame(report["alert_signal_usage"]))],
            ),
        ]

        alert_tables = [
            table_from_frame(
                "on-ing-report-alert-table",
                "Recommandations memorisees",
                pd.DataFrame(report["alert_rows"]),
                [("theme", "Theme"), ("priority", "Priorite"), ("recommendation", "Recommendation")],
            )
        ]

        return [
            self._finalize_client_section(
                ClientDemoSection(
                    id="vue-direction",
                    title="Vue Direction",
                    cards=direction_cards,
                    charts=direction_charts,
                    tables=direction_tables,
                    alerts=alerts_by_section.get("vue-direction", []),
                )
            ),
            self._finalize_client_section(
                ClientDemoSection(
                    id="chiffre-affaires",
                    title="Chiffre d'affaires",
                    cards=revenue_cards,
                    charts=revenue_charts,
                    tables=revenue_tables,
                    alerts=alerts_by_section.get("chiffre-affaires", []),
                )
            ),
            self._finalize_client_section(
                ClientDemoSection(
                    id="affaires-projets",
                    title="Affaires / Projets",
                    cards=projects_cards,
                    charts=projects_charts,
                    tables=projects_tables,
                    alerts=alerts_by_section.get("affaires-projets", []),
                )
            ),
            self._finalize_client_section(
                ClientDemoSection(
                    id="rentabilite",
                    title="Rentabilite",
                    cards=profitability_cards,
                    charts=profitability_charts,
                    tables=profitability_tables,
                    alerts=alerts_by_section.get("rentabilite", []),
                )
            ),
            self._finalize_client_section(
                ClientDemoSection(
                    id="clients",
                    title="Clients & Risque Commercial",
                    cards=clients_cards,
                    charts=clients_charts,
                    tables=clients_tables,
                    alerts=alerts_by_section.get("clients", []),
                )
            ),
            self._finalize_client_section(
                ClientDemoSection(
                    id="previsionnel",
                    title="Previsionnel",
                    cards=forecast_cards,
                    charts=forecast_charts,
                    tables=forecast_tables,
                    alerts=alerts_by_section.get("previsionnel", []),
                )
            ),
            self._finalize_client_section(
                ClientDemoSection(
                    id="comptabilite",
                    title="Comptabilite",
                    cards=accounting_cards,
                    charts=accounting_charts,
                    tables=accounting_tables,
                    alerts=alerts_by_section.get("comptabilite", []),
                )
            ),
            self._finalize_client_section(
                ClientDemoSection(
                    id="qualite-donnees",
                    title="Qualite des donnees",
                    cards=quality_cards,
                    charts=quality_charts,
                    tables=quality_tables,
                    alerts=alerts_by_section.get("qualite-donnees", []),
                )
            ),
            self._finalize_client_section(
                ClientDemoSection(
                    id="alertes-regles",
                    title="Alertes & Recommandations",
                    cards=alert_cards,
                    charts=alert_charts,
                    tables=alert_tables,
                    alerts=alerts_by_section.get("alertes-regles", []),
                )
            ),
        ]

    def _build_on_ing_sections(
        self,
        revenue_frame: pd.DataFrame,
        project_frame: pd.DataFrame,
        pnl_frame: pd.DataFrame,
        accounting_frame: pd.DataFrame,
        currency: str,
        alerts_by_section: dict[str, list[AlertRead]],
        signals: dict[str, MetricSignal],
        company_id: str,
    ) -> list[ClientDemoSection]:
        return [
            self._finalize_client_section(
                self._build_on_ing_direction_section(
                    revenue_frame,
                    project_frame,
                    pnl_frame,
                    currency,
                    signals,
                    alerts_by_section.get("vue-direction", []),
                )
            ),
            self._finalize_client_section(
                self._build_on_ing_revenue_section(
                    revenue_frame,
                    currency,
                    signals,
                    alerts_by_section.get("chiffre-affaires", []),
                )
            ),
            self._finalize_client_section(
                self._build_on_ing_projects_section(
                    project_frame,
                    currency,
                    signals,
                    alerts_by_section.get("affaires-projets", []),
                )
            ),
            self._finalize_client_section(
                self._build_on_ing_profitability_section(
                    project_frame,
                    pnl_frame,
                    revenue_frame,
                    currency,
                    signals,
                    alerts_by_section.get("rentabilite", []),
                )
            ),
            self._finalize_client_section(
                self._build_on_ing_clients_section(
                    revenue_frame,
                    currency,
                    signals,
                    alerts_by_section.get("clients", []),
                )
            ),
            self._finalize_client_section(
                self._build_on_ing_forecast_section(
                    pnl_frame,
                    revenue_frame,
                    project_frame,
                    currency,
                    signals,
                    alerts_by_section.get("previsionnel", []),
                )
            ),
            self._finalize_client_section(
                self._build_on_ing_accounting_section(
                    accounting_frame,
                    currency,
                    signals,
                    alerts_by_section.get("comptabilite", []),
                )
            ),
            self._finalize_client_section(
                self._build_on_ing_data_quality_section(
                    project_frame,
                    currency,
                    signals,
                    alerts_by_section.get("qualite-donnees", []),
                )
            ),
            self._finalize_client_section(
                self._build_alert_section(
                    alerts_by_section.get("alertes-regles", []),
                    company_id=company_id,
                    signals=signals,
                )
            ),
        ]

    def _build_on_ing_direction_section(
        self,
        revenue_frame: pd.DataFrame,
        project_frame: pd.DataFrame,
        pnl_frame: pd.DataFrame,
        currency: str,
        signals: dict[str, MetricSignal],
        alerts: list[AlertRead],
    ) -> ClientDemoSection:
        monthly_revenue = aggregate_by_period(revenue_frame, "revenue_amount", "month")
        monthly_forecast = aggregate_by_period(
            pnl_frame if not pnl_frame.empty else revenue_frame,
            "forecast_revenue_amount",
            "month",
        )
        top_clients = aggregate_group_totals(
            revenue_frame,
            "client",
            ["revenue_amount", "margin_effective"],
        ).head(8)
        if not top_clients.empty:
            total_revenue = float(top_clients["revenue_amount"].sum())
            top_clients["share_pct"] = top_clients["revenue_amount"].apply(
                lambda value: round(value / total_revenue * 100, 2) if total_revenue else 0.0
            )
        else:
            top_clients["share_pct"] = pd.Series(dtype="float64")
        projects_by_pole = aggregate_group_count(project_frame, "business_pole").head(8)

        cards = [
            signal_card(signals["ca_total"], tone="info"),
            signal_card(signals["ca_monthly"], tone="info"),
            signal_card(signals["margin_rate_pct"], tone=resolve_margin_tone(signals["margin_rate_pct"].value)),
            signal_card(
                signals["forecast_achievement_pct"],
                tone="success" if signals["forecast_achievement_pct"].value >= 100 else "warning",
            ),
            signal_card(signals["total_projects_count"], tone="info"),
            signal_card(signals["active_clients_count"], tone="info"),
            signal_card(
                signals["data_quality_score"],
                tone="success" if signals["data_quality_score"].value >= 90 else "warning",
            ),
        ]

        charts = [
            line_chart(
                "on-ing-direction-revenue-vs-forecast",
                "CA réalisé vs prévisionnel",
                [
                    chart_series("revenue", "Réalisé", monthly_revenue),
                    chart_series("forecast", "Prévisionnel", monthly_forecast),
                ],
            ),
            donut_chart(
                "on-ing-direction-projects-by-pole",
                "Portefeuille par pôle technique",
                [chart_series("projects", "Affaires", projects_by_pole)],
            ),
            bar_chart(
                "on-ing-direction-top-clients",
                "Principaux clients",
                [
                    chart_series(
                        "clients",
                        "CA",
                        top_clients.rename(columns={"client": "label", "revenue_amount": "value"})[
                            ["label", "value"]
                        ],
                    )
                ],
            ),
        ]

        tables = [
            table_from_frame(
                "on-ing-direction-client-summary",
                "Synthèse clients",
                top_clients.rename(columns={"client": "label", "revenue_amount": "revenue"})[
                    ["label", "revenue", "share_pct"]
                ],
                [("label", "Client"), ("revenue", "CA"), ("share_pct", "Part CA %")],
            ),
            table_from_frame(
                "on-ing-direction-pole-summary",
                "Répartition des affaires par pôle",
                projects_by_pole,
                [("label", "Pôle"), ("value", "Affaires")],
            ),
        ]

        return ClientDemoSection(
            id="vue-direction",
            title="Vue Direction",
            cards=cards,
            charts=charts,
            tables=tables,
            alerts=alerts,
        )

    def _build_on_ing_revenue_section(
        self,
        revenue_frame: pd.DataFrame,
        currency: str,
        signals: dict[str, MetricSignal],
        alerts: list[AlertRead],
    ) -> ClientDemoSection:
        monthly_revenue = aggregate_by_period(revenue_frame, "revenue_amount", "month")
        yearly_revenue = aggregate_by_period(revenue_frame, "revenue_amount", "year")
        top_projects = aggregate_group_sum(revenue_frame, "project_display", "revenue_amount").head(10)
        top_clients = aggregate_group_sum(revenue_frame, "client", "revenue_amount").head(10)
        top_responsibles = aggregate_group_sum(revenue_frame, "responsible", "revenue_amount").head(10)

        cards = [
            signal_card(signals["ca_total"], tone="info"),
            signal_card(signals["ca_monthly"], tone="info"),
            signal_card(
                signals["latest_month_growth_pct"],
                tone=resolve_percent_tone(signals["latest_month_growth_pct"].value),
            ),
            signal_card(
                signals["cumulative_revenue_yoy_growth_pct"],
                tone=resolve_percent_tone(signals["cumulative_revenue_yoy_growth_pct"].value),
            ),
            signal_card(signals["average_ca_per_project"], tone="info"),
        ]

        charts = [
            line_chart(
                "on-ing-revenue-monthly",
                "Évolution mensuelle du chiffre d’affaires",
                [chart_series("revenue", "CA", monthly_revenue)],
            ),
            bar_chart(
                "on-ing-revenue-yearly",
                "Chiffre d’affaires par année",
                [chart_series("revenue-year", "CA annuel", yearly_revenue)],
            ),
            bar_chart(
                "on-ing-revenue-top-clients",
                "Top clients par chiffre d’affaires",
                [chart_series("top-clients", "CA", top_clients.head(8))],
            ),
        ]

        tables = [
            table_from_frame(
                "on-ing-revenue-projects",
                "Top affaires par chiffre d’affaires",
                top_projects,
                [("label", "Affaire"), ("value", "CA")],
            ),
            table_from_frame(
                "on-ing-revenue-clients",
                "Top clients",
                top_clients,
                [("label", "Client"), ("value", "CA")],
            ),
            table_from_frame(
                "on-ing-revenue-responsibles",
                "CA par responsable mission",
                top_responsibles,
                [("label", "Responsable"), ("value", "CA")],
            ),
        ]

        return ClientDemoSection(
            id="chiffre-affaires",
            title="Chiffre d’affaires",
            cards=cards,
            charts=charts,
            tables=tables,
            alerts=alerts,
        )

    def _build_on_ing_projects_section(
        self,
        project_frame: pd.DataFrame,
        currency: str,
        signals: dict[str, MetricSignal],
        alerts: list[AlertRead],
    ) -> ClientDemoSection:
        projects_by_status = aggregate_group_count(project_frame, "status_display").head(8)
        projects_by_pole = aggregate_group_count(project_frame, "business_pole").head(8)
        missing_resource_rows = project_frame[project_frame["resource_name"].fillna("").eq("")].copy()
        missing_responsible_rows = project_frame[project_frame["responsible"].fillna("").eq("")].copy()
        remaining_invoice_rows = (
            project_frame[project_frame["remaining_to_invoice_amount"].fillna(0) > 0]
            .sort_values("remaining_to_invoice_amount", ascending=False)
            .head(10)
            .copy()
        )

        cards = [
            signal_card(signals["total_projects_count"], tone="info"),
            signal_card(signals["active_projects_count"], tone="info"),
            signal_card(
                signals["missing_responsible_count"],
                tone="warning" if signals["missing_responsible_count"].value > 0 else "success",
            ),
            signal_card(
                signals["missing_resource_count"],
                tone="warning" if signals["missing_resource_count"].value > 0 else "success",
            ),
            signal_card(
                signals["missing_end_date_count"],
                tone="warning" if signals["missing_end_date_count"].value > 0 else "success",
            ),
            signal_card(signals["projects_with_remaining_invoice_count"], tone="warning"),
        ]

        charts = [
            donut_chart(
                "on-ing-projects-status",
                "Affaires par statut",
                [chart_series("status", "Affaires", projects_by_status)],
            ),
            bar_chart(
                "on-ing-projects-poles",
                "Affaires par pôle technique",
                [chart_series("pole", "Affaires", projects_by_pole)],
            ),
            bar_chart(
                "on-ing-projects-backlog",
                "Reste à facturer par affaire",
                [
                    chart_series(
                        "remaining-invoice",
                        "Reste à facturer",
                        remaining_invoice_rows.rename(
                            columns={
                                "project_display": "label",
                                "remaining_to_invoice_amount": "value",
                            }
                        )[["label", "value"]],
                    )
                ],
            ),
        ]

        tables = [
            project_detail_table(
                "on-ing-projects-missing-resource",
                "Affaires sans ressource affectée",
                missing_resource_rows.head(10),
            ),
            project_detail_table(
                "on-ing-projects-missing-owner",
                "Affaires sans responsable mission",
                missing_responsible_rows.head(10),
            ),
            table_from_frame(
                "on-ing-projects-remaining-invoice",
                "Affaires avec reste à facturer",
                remaining_invoice_rows.rename(
                    columns={
                        "project_display": "project",
                        "client": "client",
                        "remaining_to_invoice_amount": "remaining",
                    }
                )[["project", "client", "remaining"]],
                [("project", "Affaire"), ("client", "Client"), ("remaining", "Reste à facturer")],
            ),
        ]

        return ClientDemoSection(
            id="affaires-projets",
            title="Affaires / Projets",
            cards=cards,
            charts=charts,
            tables=tables,
            alerts=alerts,
        )

    def _build_on_ing_profitability_section(
        self,
        project_frame: pd.DataFrame,
        pnl_frame: pd.DataFrame,
        revenue_frame: pd.DataFrame,
        currency: str,
        signals: dict[str, MetricSignal],
        alerts: list[AlertRead],
    ) -> ClientDemoSection:
        working_revenue = pnl_frame if not pnl_frame.empty else revenue_frame
        margin_by_month = aggregate_by_period(working_revenue, "margin_effective", "month")
        margin_by_pole = aggregate_group_totals(
            project_frame,
            "business_pole",
            ["revenue_amount", "margin_effective"],
        ).head(8)
        if not margin_by_pole.empty:
            margin_by_pole["margin_rate_pct"] = margin_by_pole.apply(
                lambda row: round(row["margin_effective"] / row["revenue_amount"] * 100, 2)
                if row["revenue_amount"]
                else 0.0,
                axis=1,
            )
        else:
            margin_by_pole["margin_rate_pct"] = pd.Series(dtype="float64")
        low_margin_rows = (
            project_frame.sort_values("margin_rate_effective", ascending=True)
            .head(10)
            .copy()
        )

        cards = [
            signal_card(signals["total_margin"], tone="info"),
            signal_card(
                signals["margin_rate_pct"],
                tone=resolve_margin_tone(signals["margin_rate_pct"].value),
            ),
            signal_card(
                signals["low_margin_project_count"],
                tone="warning" if signals["low_margin_project_count"].value > 0 else "success",
            ),
            signal_card(signals["rex"], tone="info"),
            signal_card(signals["cumulative_rex"], tone="info"),
            signal_card(
                signals["billing_rate_pct"],
                tone="success" if signals["billing_rate_pct"].value >= 85 else "warning",
            ),
        ]

        charts = [
            line_chart(
                "on-ing-profitability-margin-monthly",
                "Marge mensuelle",
                [chart_series("margin", "Marge", margin_by_month)],
            ),
            bar_chart(
                "on-ing-profitability-by-pole",
                "Taux de marge par pôle",
                [
                    chart_series(
                        "margin-rate-pole",
                        "Taux de marge",
                        margin_by_pole.rename(
                            columns={"business_pole": "label", "margin_rate_pct": "value"}
                        )[["label", "value"]],
                    )
                ],
            ),
            bar_chart(
                "on-ing-profitability-low-projects",
                "Affaires à faible marge",
                [
                    chart_series(
                        "low-margin-projects",
                        "Taux de marge",
                        low_margin_rows.rename(
                            columns={"project_display": "label", "margin_rate_effective": "value"}
                        )[["label", "value"]],
                    )
                ],
            ),
        ]

        tables = [
            project_detail_table(
                "on-ing-profitability-detail",
                "Affaires à surveiller sur la marge",
                low_margin_rows,
            ),
            table_from_frame(
                "on-ing-profitability-pole-table",
                "Rentabilité par pôle",
                margin_by_pole.rename(
                    columns={
                        "business_pole": "pole",
                        "revenue_amount": "revenue",
                        "margin_effective": "margin",
                    }
                )[["pole", "revenue", "margin", "margin_rate_pct"]],
                [("pole", "Pôle"), ("revenue", "CA"), ("margin", "Marge"), ("margin_rate_pct", "Taux marge %")],
            ),
        ]

        return ClientDemoSection(
            id="rentabilite",
            title="Rentabilité",
            cards=cards,
            charts=charts,
            tables=tables,
            alerts=alerts,
        )

    def _build_on_ing_clients_section(
        self,
        revenue_frame: pd.DataFrame,
        currency: str,
        signals: dict[str, MetricSignal],
        alerts: list[AlertRead],
    ) -> ClientDemoSection:
        client_totals = aggregate_group_totals(
            revenue_frame,
            "client",
            ["revenue_amount", "margin_effective", "remaining_to_invoice_amount"],
        ).head(12)
        total_revenue = float(client_totals["revenue_amount"].sum()) if not client_totals.empty else 0.0
        if not client_totals.empty:
            client_totals["share_pct"] = client_totals["revenue_amount"].apply(
                lambda value: round(value / total_revenue * 100, 2) if total_revenue else 0.0
            )
            client_totals["margin_rate_pct"] = client_totals.apply(
                lambda row: round(row["margin_effective"] / row["revenue_amount"] * 100, 2)
                if row["revenue_amount"]
                else 0.0,
                axis=1,
            )
        else:
            client_totals["share_pct"] = pd.Series(dtype="float64")
            client_totals["margin_rate_pct"] = pd.Series(dtype="float64")
        risky_clients = client_totals[
            (client_totals["share_pct"].fillna(0) > 25)
            | (client_totals["margin_rate_pct"].fillna(0) < 15)
        ].copy()

        cards = [
            signal_card(signals["active_clients_count"], tone="info"),
            signal_card(
                signals["top_client_revenue"],
                tone="info",
                helper=signals["top_client_name"].display_value,
            ),
            signal_card(
                signals["client_concentration_pct"],
                tone="warning" if signals["client_concentration_pct"].value > 40 else "success",
            ),
            signal_card(
                signals["risky_clients_count"],
                tone="warning" if signals["risky_clients_count"].value > 0 else "success",
            ),
        ]

        charts = [
            bar_chart(
                "on-ing-clients-top",
                "Top clients par chiffre d’affaires",
                [
                    chart_series(
                        "client-revenue",
                        "CA",
                        client_totals.rename(columns={"client": "label", "revenue_amount": "value"})[
                            ["label", "value"]
                        ].head(8),
                    )
                ],
            ),
            donut_chart(
                "on-ing-clients-share",
                "Part de chiffre d’affaires par client",
                [
                    chart_series(
                        "client-share",
                        "Part CA %",
                        client_totals.rename(columns={"client": "label", "share_pct": "value"})[
                            ["label", "value"]
                        ].head(8),
                    )
                ],
            ),
        ]

        tables = [
            table_from_frame(
                "on-ing-clients-table",
                "Portefeuille clients",
                client_totals.rename(
                    columns={
                        "client": "client",
                        "revenue_amount": "revenue",
                        "margin_effective": "margin",
                    }
                )[["client", "revenue", "share_pct", "margin_rate_pct", "remaining_to_invoice_amount"]],
                [
                    ("client", "Client"),
                    ("revenue", "CA"),
                    ("share_pct", "Part CA %"),
                    ("margin_rate_pct", "Taux marge %"),
                    ("remaining_to_invoice_amount", "Reste à facturer"),
                ],
            ),
            table_from_frame(
                "on-ing-clients-risky-table",
                "Clients à surveiller",
                risky_clients.rename(
                    columns={
                        "client": "client",
                        "revenue_amount": "revenue",
                    }
                )[["client", "revenue", "share_pct", "margin_rate_pct"]],
                [
                    ("client", "Client"),
                    ("revenue", "CA"),
                    ("share_pct", "Part CA %"),
                    ("margin_rate_pct", "Taux marge %"),
                ],
            ),
        ]

        return ClientDemoSection(
            id="clients",
            title="Clients & Risque Commercial",
            cards=cards,
            charts=charts,
            tables=tables,
            alerts=alerts,
        )

    def _build_on_ing_forecast_section(
        self,
        pnl_frame: pd.DataFrame,
        revenue_frame: pd.DataFrame,
        project_frame: pd.DataFrame,
        currency: str,
        signals: dict[str, MetricSignal],
        alerts: list[AlertRead],
    ) -> ClientDemoSection:
        monthly_realized = aggregate_by_period(
            pnl_frame if not pnl_frame.empty else revenue_frame,
            "revenue_amount",
            "month",
        )
        monthly_forecast = aggregate_by_period(
            pnl_frame if not pnl_frame.empty else project_frame,
            "forecast_revenue_amount",
            "month",
        )
        remaining_invoice_rows = (
            project_frame[project_frame["remaining_to_invoice_amount"].fillna(0) > 0]
            .sort_values("remaining_to_invoice_amount", ascending=False)
            .head(10)
            .copy()
        )
        monthly_comparison = monthly_realized.merge(
            monthly_forecast,
            on="label",
            how="outer",
            suffixes=("_realized", "_forecast"),
        ).fillna(0)
        monthly_comparison["gap"] = (
            monthly_comparison["value_realized"] - monthly_comparison["value_forecast"]
        )

        cards = [
            signal_card(signals["forecast_revenue"], tone="info"),
            signal_card(
                signals["forecast_achievement_pct"],
                tone="success" if signals["forecast_achievement_pct"].value >= 100 else "warning",
            ),
            signal_card(
                signals["forecast_gap_pct"],
                tone="warning" if signals["forecast_gap_pct"].value > 20 else "success",
            ),
            signal_card(
                signals["remaining_to_invoice_amount"],
                tone="warning" if signals["remaining_to_invoice_amount"].value > 0 else "success",
            ),
            signal_card(
                signals["billing_rate_pct"],
                tone="success" if signals["billing_rate_pct"].value >= 85 else "warning",
            ),
        ]

        charts = [
            line_chart(
                "on-ing-forecast-actual-vs-forecast",
                "Réalisé vs prévisionnel",
                [
                    chart_series("realized", "Réalisé", monthly_realized),
                    chart_series("forecast", "Prévisionnel", monthly_forecast),
                ],
            ),
            bar_chart(
                "on-ing-forecast-gap",
                "Écart mensuel",
                [
                    chart_series(
                        "gap",
                        "Écart",
                        monthly_comparison.rename(columns={"label": "label", "gap": "value"})[
                            ["label", "value"]
                        ],
                    )
                ],
            ),
            bar_chart(
                "on-ing-forecast-backlog",
                "Reste à facturer par affaire",
                [
                    chart_series(
                        "remaining",
                        "Reste à facturer",
                        remaining_invoice_rows.rename(
                            columns={
                                "project_display": "label",
                                "remaining_to_invoice_amount": "value",
                            }
                        )[["label", "value"]],
                    )
                ],
            ),
        ]

        tables = [
            table_from_frame(
                "on-ing-forecast-monthly-table",
                "Suivi mensuel prévisionnel",
                monthly_comparison.rename(
                    columns={
                        "value_realized": "realized",
                        "value_forecast": "forecast",
                    }
                )[["label", "realized", "forecast", "gap"]],
                [("label", "Mois"), ("realized", "Réalisé"), ("forecast", "Prévisionnel"), ("gap", "Écart")],
            ),
            table_from_frame(
                "on-ing-forecast-projects-table",
                "Affaires avec facturation restante",
                remaining_invoice_rows.rename(
                    columns={
                        "project_display": "project",
                        "client": "client",
                        "remaining_to_invoice_amount": "remaining",
                    }
                )[["project", "client", "remaining"]],
                [("project", "Affaire"), ("client", "Client"), ("remaining", "Reste à facturer")],
            ),
        ]

        return ClientDemoSection(
            id="previsionnel",
            title="Prévisionnel",
            cards=cards,
            charts=charts,
            tables=tables,
            alerts=alerts,
        )

    def _build_on_ing_accounting_section(
        self,
        accounting_frame: pd.DataFrame,
        currency: str,
        signals: dict[str, MetricSignal],
        alerts: list[AlertRead],
    ) -> ClientDemoSection:
        billed_monthly = aggregate_by_period(accounting_frame, "invoice_effective_amount", "month")
        by_currency = aggregate_group_sum(accounting_frame, "currency_display", "invoice_effective_amount")
        by_subaccount = aggregate_group_sum(accounting_frame, "subaccount_display", "invoice_effective_amount")
        duplicate_piece_rows = (
            accounting_frame[
                accounting_frame["invoice_number"].fillna("").ne("")
                & accounting_frame["invoice_number"].duplicated(keep=False)
            ]
            .sort_values(["invoice_number", "business_date"])
            .head(10)
            .copy()
        )
        missing_subaccount_rows = accounting_frame[
            accounting_frame["subaccount"].fillna("").eq("")
        ].copy()
        invalid_amount_rows = accounting_frame[
            accounting_frame["invoice_effective_amount"].fillna(0) <= 0
        ].copy()

        cards = [
            signal_card(signals["total_debit"], tone="info"),
            signal_card(signals["total_credit"], tone="info"),
            signal_card(
                signals["debit_credit_difference"],
                tone="danger" if signals["debit_credit_difference"].value > 0 else "success",
            ),
            signal_card(signals["accounting_entries_count"], tone="info"),
            signal_card(
                signals["duplicate_piece_count"],
                tone="warning" if signals["duplicate_piece_count"].value > 0 else "success",
            ),
            signal_card(
                signals["missing_subaccount_count"],
                tone="warning" if signals["missing_subaccount_count"].value > 0 else "success",
            ),
            signal_card(
                signals["invalid_invoice_amount_count"],
                tone="warning" if signals["invalid_invoice_amount_count"].value > 0 else "success",
            ),
            signal_card(
                signals["foreign_currency_entries_count"],
                tone="info" if signals["foreign_currency_entries_count"].value > 0 else "success",
            ),
        ]

        charts = [
            line_chart(
                "on-ing-accounting-billed-monthly",
                "Facturation comptable par mois",
                [chart_series("billed", "Montant", billed_monthly)],
            ),
            donut_chart(
                "on-ing-accounting-currency",
                "Répartition par devise",
                [chart_series("currency", "Montant", by_currency.head(8))],
            ),
            bar_chart(
                "on-ing-accounting-subaccount",
                "Montant par sous-compte",
                [chart_series("subaccount", "Montant", by_subaccount.head(10))],
            ),
        ]

        tables = [
            accounting_issue_table(
                "on-ing-accounting-duplicates",
                "Pièces comptables dupliquées",
                duplicate_piece_rows,
            ),
            accounting_issue_table(
                "on-ing-accounting-missing-subaccount",
                "Écritures sans sous-compte",
                missing_subaccount_rows.head(10),
            ),
            accounting_issue_table(
                "on-ing-accounting-invalid-amounts",
                "Écritures avec montant invalide",
                invalid_amount_rows.head(10),
            ),
        ]

        return ClientDemoSection(
            id="comptabilite",
            title="Comptabilité",
            cards=cards,
            charts=charts,
            tables=tables,
            alerts=alerts,
        )

    def _build_on_ing_data_quality_section(
        self,
        project_frame: pd.DataFrame,
        currency: str,
        signals: dict[str, MetricSignal],
        alerts: list[AlertRead],
    ) -> ClientDemoSection:
        duplicate_reference_rows = (
            project_frame[
                project_frame["normalized_project_reference"].fillna("").ne("")
                & project_frame["normalized_project_reference"].duplicated(keep=False)
            ]
            .sort_values("normalized_project_reference")
            .head(10)
            .copy()
        )
        missing_quality_rows = project_frame[
            project_frame["resource_name"].fillna("").eq("")
            | project_frame["original_business_pole"].fillna("").eq("")
            | project_frame["margin_rate"].isna()
            | project_frame["end_date"].isna()
            | project_frame["remaining_to_invoice_amount"].isna()
        ].copy()
        quality_breakdown = pd.DataFrame(
            [
                {"label": "Ressource manquante", "value": signals["missing_resource_count"].value},
                {"label": "Pôle manquant", "value": signals["missing_pole_count"].value},
                {"label": "Marge manquante", "value": signals["missing_margin_rate_count"].value},
                {"label": "Date fin manquante", "value": signals["missing_end_date_count"].value},
                {"label": "Facturation manquante", "value": signals["missing_facturation_count"].value},
                {
                    "label": "Référence dupliquée",
                    "value": signals["duplicate_project_reference_count"].value,
                },
            ]
        )

        cards = [
            signal_card(
                signals["data_quality_score"],
                tone="success" if signals["data_quality_score"].value >= 90 else "warning",
            ),
            signal_card(
                signals["missing_pole_count"],
                tone="warning" if signals["missing_pole_count"].value > 0 else "success",
            ),
            signal_card(
                signals["missing_margin_rate_count"],
                tone="warning" if signals["missing_margin_rate_count"].value > 0 else "success",
            ),
            signal_card(
                signals["duplicate_project_reference_count"],
                tone="warning" if signals["duplicate_project_reference_count"].value > 0 else "success",
            ),
            signal_card(
                signals["missing_facturation_count"],
                tone="warning" if signals["missing_facturation_count"].value > 0 else "success",
            ),
        ]

        charts = [
            donut_chart(
                "on-ing-quality-breakdown",
                "Répartition des anomalies",
                [chart_series("quality", "Anomalies", quality_breakdown)],
            ),
            bar_chart(
                "on-ing-quality-pole",
                "Affaires par pôle normalisé",
                [chart_series("pole", "Affaires", aggregate_group_count(project_frame, "business_pole").head(8))],
            ),
        ]

        tables = [
            table_from_frame(
                "on-ing-quality-duplicates",
                "Références affaire dupliquées",
                duplicate_reference_rows.rename(
                    columns={
                        "project_display": "project",
                        "client": "client",
                        "normalized_project_reference": "reference",
                    }
                )[["reference", "project", "client"]],
                [("reference", "Référence"), ("project", "Affaire"), ("client", "Client")],
            ),
            project_detail_table(
                "on-ing-quality-missing-fields",
                "Affaires avec données à compléter",
                missing_quality_rows.head(10),
            ),
        ]

        return ClientDemoSection(
            id="qualite-donnees",
            title="Qualité des données",
            cards=cards,
            charts=charts,
            tables=tables,
            alerts=alerts,
        )

    def _build_general_section(
        self,
        revenue_frame: pd.DataFrame,
        project_frame: pd.DataFrame,
        currency: str,
        alerts: list[AlertRead],
    ) -> ClientDemoSection:
        total_revenue = float(revenue_frame["revenue_amount"].fillna(0).sum())
        revenue_2025 = sum_year(revenue_frame, 2025, "revenue_amount")
        revenue_2026 = sum_year(revenue_frame, 2026, "revenue_amount")
        cumulative = total_revenue
        growth = percent_change(revenue_2026, revenue_2025)
        total_margin = float(revenue_frame["margin_effective"].fillna(0).sum())
        average_margin_rate = safe_average(revenue_frame["margin_rate_effective"])
        total_projects = count_distinct_non_empty(project_frame, "project_key")

        cards = [
            metric_card("total-revenue", "Chiffre d'affaires total", total_revenue, "currency", currency),
            metric_card("revenue-2025", "CA 2025", revenue_2025, "currency", currency),
            metric_card("revenue-2026", "CA 2026", revenue_2026, "currency", currency),
            metric_card("cumulative-revenue", "CA cumulé", cumulative, "currency", currency),
            metric_card(
                "revenue-growth",
                "Croissance 2025 vs 2026",
                growth,
                "percent",
                currency,
                tone=resolve_percent_tone(growth),
            ),
            metric_card("total-margin", "Marge totale", total_margin, "currency", currency),
            metric_card(
                "avg-margin-rate",
                "Taux de marge moyen",
                average_margin_rate,
                "percent",
                currency,
                tone=resolve_margin_tone(average_margin_rate),
            ),
            metric_card("total-projects", "Nombre total de projets / affaires", total_projects, "count", currency),
        ]

        charts = [
            line_chart(
                "general-revenue-monthly",
                "Chiffre d'affaires par mois",
                [
                    chart_series(
                        "revenue",
                        "CA",
                        aggregate_by_period(revenue_frame, "revenue_amount", "month"),
                    )
                ],
            ),
            bar_chart(
                "general-revenue-yearly",
                "Chiffre d'affaires par année",
                [
                    chart_series(
                        "revenue",
                        "CA annuel",
                        aggregate_by_period(revenue_frame, "revenue_amount", "year"),
                    )
                ],
            ),
            donut_chart(
                "general-projects-by-pole",
                "Nombre de projets par pôle",
                [
                    chart_series(
                        "projects-by-pole",
                        "Projets",
                        aggregate_group_count(project_frame, "business_pole"),
                    )
                ],
            ),
        ]

        tables = [
            table_from_frame(
                "general-projects-by-client",
                "Nombre de projets par client",
                aggregate_group_count(project_frame, "client").head(10),
                [("label", "Client"), ("value", "Projets")],
            ),
            table_from_frame(
                "general-projects-by-responsible",
                "Nombre de projets par responsable",
                aggregate_group_count(project_frame, "responsible").head(10),
                [("label", "Responsable"), ("value", "Projets")],
            ),
            table_from_frame(
                "general-projects-by-pole-table",
                "Nombre de projets par pôle",
                aggregate_group_count(project_frame, "business_pole").head(10),
                [("label", "Pôle"), ("value", "Projets")],
            ),
        ]

        return ClientDemoSection(
            id="dashboard-general",
            title="Dashboard Général",
            cards=cards,
            charts=charts,
            tables=tables,
            alerts=alerts,
        )

    def _build_ca_section(
        self,
        revenue_frame: pd.DataFrame,
        currency: str,
        alerts: list[AlertRead],
    ) -> ClientDemoSection:
        top_projects = aggregate_group_sum(revenue_frame, "project_display", "revenue_amount").head(10)
        top_clients = aggregate_group_sum(revenue_frame, "client", "revenue_amount").head(10)
        top_responsibles = aggregate_group_sum(revenue_frame, "responsible", "revenue_amount").head(10)
        top_poles = aggregate_group_sum(revenue_frame, "business_pole", "revenue_amount").head(10)
        revenue_2025 = sum_year(revenue_frame, 2025, "revenue_amount")
        revenue_2026 = sum_year(revenue_frame, 2026, "revenue_amount")
        cards = [
            metric_card(
                "ca-projects-total",
                "CA total projets",
                float(revenue_frame["revenue_amount"].fillna(0).sum()),
                "currency",
                currency,
            ),
            metric_card("ca-projects-2025", "CA 2025", revenue_2025, "currency", currency),
            metric_card("ca-projects-2026", "CA 2026", revenue_2026, "currency", currency),
            metric_card(
                "ca-projects-growth",
                "Comparaison CA 2025 vs 2026",
                percent_change(revenue_2026, revenue_2025),
                "percent",
                currency,
                tone=resolve_percent_tone(percent_change(revenue_2026, revenue_2025)),
            ),
            metric_card(
                "top-project-ca",
                "Meilleur projet par CA",
                float(top_projects["value"].iloc[0]) if not top_projects.empty else 0.0,
                "currency",
                currency,
                helper=top_projects["label"].iloc[0] if not top_projects.empty else None,
            ),
            metric_card(
                "top-client-ca",
                "Meilleur client par CA",
                float(top_clients["value"].iloc[0]) if not top_clients.empty else 0.0,
                "currency",
                currency,
                helper=top_clients["label"].iloc[0] if not top_clients.empty else None,
            ),
        ]

        charts = [
            line_chart(
                "ca-projects-monthly",
                "Évolution du CA dans le temps",
                [chart_series("revenue", "CA", aggregate_by_period(revenue_frame, "revenue_amount", "month"))],
            ),
            bar_chart(
                "ca-projects-top-clients",
                "Classement des meilleurs clients par CA",
                [chart_series("clients", "CA", top_clients.head(8))],
            ),
            bar_chart(
                "ca-projects-by-pole",
                "CA par pôle",
                [chart_series("poles", "CA", top_poles.head(8))],
            ),
        ]

        tables = [
            table_from_frame(
                "ca-projects-top-projects",
                "Classement des meilleurs projets par CA",
                top_projects,
                [("label", "Projet"), ("value", "CA")],
            ),
            table_from_frame(
                "ca-projects-top-clients-table",
                "Classement des meilleurs clients par CA",
                top_clients,
                [("label", "Client"), ("value", "CA")],
            ),
            table_from_frame(
                "ca-projects-top-responsibles",
                "CA par responsable mission",
                top_responsibles,
                [("label", "Responsable"), ("value", "CA")],
            ),
        ]

        return ClientDemoSection(
            id="analyse-ca-projets",
            title="Analyse CA Projets",
            cards=cards,
            charts=charts,
            tables=tables,
            alerts=alerts,
        )

    def _build_affairs_section(
        self,
        project_frame: pd.DataFrame,
        currency: str,
        alerts: list[AlertRead],
    ) -> ClientDemoSection:
        strong_margin = int((project_frame["margin_rate_effective"].fillna(0) >= 30).sum())
        low_margin = int((project_frame["margin_rate_effective"].fillna(0) < 30).sum())
        upcoming = project_frame[project_frame["is_ending_soon"]].copy()
        overdue = project_frame[project_frame["is_overdue"]].copy()

        cards = [
            metric_card(
                "affairs-in-progress",
                "Nombre d'affaires en cours",
                int(project_frame["is_in_progress"].sum()),
                "count",
                currency,
            ),
            metric_card(
                "affairs-completed",
                "Nombre d'affaires terminées",
                int(project_frame["is_completed"].sum()),
                "count",
                currency,
            ),
            metric_card(
                "affairs-average-duration",
                "Durée moyenne des projets",
                safe_average(project_frame["duration_days"]),
                "days",
                currency,
            ),
            metric_card(
                "affairs-near-end",
                "Projets avec date de fin proche",
                len(upcoming.index),
                "count",
                currency,
            ),
            metric_card(
                "affairs-overdue",
                "Projets en retard",
                len(overdue.index),
                "count",
                currency,
                tone="danger" if len(overdue.index) > 0 else "success",
            ),
            metric_card(
                "affairs-strong-margin",
                "Projets à forte marge",
                strong_margin,
                "count",
                currency,
            ),
            metric_card(
                "affairs-low-margin",
                "Projets à faible marge",
                low_margin,
                "count",
                currency,
                tone="warning" if low_margin > 0 else "success",
            ),
        ]

        charts = [
            donut_chart(
                "affairs-by-status",
                "Nombre d'affaires par statut",
                [chart_series("status", "Affaires", aggregate_group_count(project_frame, "status_display"))],
            ),
            bar_chart(
                "affairs-by-responsible",
                "Répartition des affaires par responsable",
                [chart_series("responsible", "Affaires", aggregate_group_count(project_frame, "responsible").head(10))],
            ),
            bar_chart(
                "affairs-by-pole",
                "Répartition des affaires par pôle",
                [chart_series("pole", "Affaires", aggregate_group_count(project_frame, "business_pole").head(10))],
            ),
        ]

        upcoming_or_overdue = (
            pd.concat([upcoming, overdue], ignore_index=True)
            .drop_duplicates(subset=["project_key"], keep="first")
            .sort_values(["is_overdue", "end_date"], ascending=[False, True])
            .head(10)
        )

        tables = [
            project_detail_table(
                "affairs-deadlines",
                "Projets avec date de fin proche ou dépassée",
                upcoming_or_overdue,
            ),
            table_from_frame(
                "affairs-by-client-table",
                "Répartition des affaires par client",
                aggregate_group_count(project_frame, "client").head(10),
                [("label", "Client"), ("value", "Affaires")],
            ),
            table_from_frame(
                "affairs-by-pole-table",
                "Répartition des affaires par pôle",
                aggregate_group_count(project_frame, "business_pole").head(10),
                [("label", "Pôle"), ("value", "Affaires")],
            ),
        ]

        return ClientDemoSection(
            id="suivi-affaires",
            title="Suivi des Affaires",
            cards=cards,
            charts=charts,
            tables=tables,
            alerts=alerts,
        )

    def _build_pnl_section(
        self,
        pnl_frame: pd.DataFrame,
        revenue_frame: pd.DataFrame,
        currency: str,
        alerts: list[AlertRead],
    ) -> ClientDemoSection:
        monthly_realized = aggregate_by_period(
            pnl_frame if not pnl_frame.empty else revenue_frame, "revenue_amount", "month"
        )
        monthly_forecast = aggregate_by_period(pnl_frame, "forecast_revenue_amount", "month")
        monthly_margin = aggregate_by_period(
            pnl_frame if not pnl_frame.empty else revenue_frame, "margin_effective", "month"
        )
        latest_realized = float(monthly_realized["value"].iloc[-1]) if not monthly_realized.empty else 0.0
        latest_forecast = float(monthly_forecast["value"].iloc[-1]) if not monthly_forecast.empty else 0.0
        latest_gap = latest_realized - latest_forecast
        realization_rate = latest_realized / latest_forecast * 100 if latest_forecast else 0.0
        annual_realized = aggregate_by_period(
            pnl_frame if not pnl_frame.empty else revenue_frame, "revenue_amount", "year"
        )
        cards = [
            metric_card("pnl-realized", "CA mensuel réalisé", latest_realized, "currency", currency),
            metric_card("pnl-forecast", "CA mensuel prévisionnel", latest_forecast, "currency", currency),
            metric_card(
                "pnl-gap",
                "Écart réalisé / prévisionnel",
                latest_gap,
                "currency",
                currency,
                tone="danger" if latest_gap < 0 else "success",
            ),
            metric_card(
                "pnl-realization-rate",
                "Taux de réalisation du prévisionnel",
                realization_rate,
                "percent",
                currency,
                tone=resolve_percent_tone(realization_rate - 100),
            ),
            metric_card(
                "pnl-margin-cumulative",
                "Marge cumulée",
                float(monthly_margin["value"].sum()) if not monthly_margin.empty else 0.0,
                "currency",
                currency,
            ),
            metric_card(
                "pnl-monthly-growth",
                "Croissance mensuelle",
                percent_change(latest_realized, float(monthly_realized["value"].iloc[-2]))
                if len(monthly_realized.index) > 1
                else 0.0,
                "percent",
                currency,
            ),
            metric_card(
                "pnl-annual-growth",
                "Croissance annuelle",
                percent_change(
                    float(annual_realized["value"].iloc[-1]) if not annual_realized.empty else 0.0,
                    float(annual_realized["value"].iloc[-2]) if len(annual_realized.index) > 1 else 0.0,
                ),
                "percent",
                currency,
            ),
        ]

        comparison = monthly_realized.merge(
            monthly_forecast, on="label", how="outer", suffixes=("_realized", "_forecast")
        ).fillna(0)
        comparison["gap"] = comparison["value_realized"] - comparison["value_forecast"]
        comparison["realization_rate"] = comparison.apply(
            lambda row: row["value_realized"] / row["value_forecast"] * 100
            if row["value_forecast"]
            else 0,
            axis=1,
        )
        comparison["margin"] = comparison["label"].map(
            {
                row["label"]: row["value"]
                for _, row in monthly_margin.iterrows()
            }
        ).fillna(0)

        charts = [
            line_chart(
                "pnl-realized-vs-forecast",
                "CA mensuel réalisé vs prévisionnel",
                [
                    chart_series("realized", "Réalisé", monthly_realized),
                    chart_series("forecast", "Prévisionnel", monthly_forecast),
                ],
            ),
            line_chart(
                "pnl-monthly-margin",
                "Marge mensuelle",
                [chart_series("margin", "Marge", monthly_margin)],
            ),
            bar_chart(
                "pnl-annual-comparison",
                "Comparaison PnL 2025 vs 2026",
                [chart_series("annual", "CA annuel", annual_realized)],
            ),
        ]

        best_months = comparison.sort_values("value_realized", ascending=False).head(5)
        worst_months = comparison.sort_values("value_realized", ascending=True).head(5)
        tables = [
            table_from_frame(
                "pnl-monthly-detail",
                "Détail mensuel PnL",
                comparison[["label", "value_realized", "value_forecast", "gap", "realization_rate", "margin"]],
                [
                    ("label", "Mois"),
                    ("value_realized", "Réalisé"),
                    ("value_forecast", "Prévisionnel"),
                    ("gap", "Écart"),
                    ("realization_rate", "Taux réalisation"),
                    ("margin", "Marge"),
                ],
            ),
            table_from_frame(
                "pnl-best-months",
                "Mois les plus performants",
                best_months[["label", "value_realized"]].rename(columns={"value_realized": "value"}),
                [("label", "Mois"), ("value", "CA réalisé")],
            ),
            table_from_frame(
                "pnl-worst-months",
                "Mois les moins performants",
                worst_months[["label", "value_realized"]].rename(columns={"value_realized": "value"}),
                [("label", "Mois"), ("value", "CA réalisé")],
            ),
        ]

        return ClientDemoSection(
            id="reporting-pnl",
            title="Reporting PnL",
            cards=cards,
            charts=charts,
            tables=tables,
            alerts=alerts,
        )

    def _build_accounting_section(
        self,
        accounting_frame: pd.DataFrame,
        currency: str,
        alerts: list[AlertRead],
    ) -> ClientDemoSection:
        total_debit = float(accounting_frame["debit_amount"].fillna(0).sum())
        total_credit = float(accounting_frame["credit_amount"].fillna(0).sum())
        balance = total_debit - total_credit
        invoice_count = count_distinct_non_empty(accounting_frame, "invoice_key")
        billed_monthly = aggregate_by_period(accounting_frame, "invoice_effective_amount", "month")
        by_subaccount = aggregate_group_sum(accounting_frame, "subaccount_display", "invoice_effective_amount")
        by_currency = aggregate_group_sum(accounting_frame, "currency_display", "invoice_effective_amount")
        invalid_amount_rows = accounting_frame[
            accounting_frame["invoice_effective_amount"].fillna(0) <= 0
        ].copy()
        incomplete_rows = accounting_frame[
            accounting_frame["subaccount"].eq("") | accounting_frame["client"].eq("")
        ].copy()

        cards = [
            metric_card("accounting-debit", "Total débit", total_debit, "currency", currency),
            metric_card("accounting-credit", "Total crédit", total_credit, "currency", currency),
            metric_card(
                "accounting-balance",
                "Solde comptable",
                balance,
                "currency",
                currency,
                tone="danger" if abs(balance) > 0.01 else "success",
            ),
            metric_card("accounting-invoices", "Nombre de factures", invoice_count, "count", currency),
            metric_card(
                "accounting-monthly-billed",
                "Montant facturé par mois",
                float(billed_monthly["value"].iloc[-1]) if not billed_monthly.empty else 0.0,
                "currency",
                currency,
            ),
            metric_card(
                "accounting-foreign-currency",
                "Factures par devise",
                count_distinct_non_empty(accounting_frame, "currency_display"),
                "count",
                currency,
            ),
            metric_card(
                "accounting-incomplete-entries",
                "Écritures incomplètes",
                len(incomplete_rows.index),
                "count",
                currency,
                tone="warning" if len(incomplete_rows.index) > 0 else "success",
            ),
            metric_card(
                "accounting-zero-amounts",
                "Montants vides ou nuls",
                len(invalid_amount_rows.index),
                "count",
                currency,
                tone="warning" if len(invalid_amount_rows.index) > 0 else "success",
            ),
        ]

        charts = [
            line_chart(
                "accounting-billed-monthly",
                "Montant facturé par mois",
                [chart_series("billed", "Facturé", billed_monthly)],
            ),
            donut_chart(
                "accounting-by-currency",
                "Factures par devise",
                [chart_series("currency", "Montant", by_currency.head(8))],
            ),
            bar_chart(
                "accounting-by-subaccount",
                "Montant par client ou sous-compte",
                [chart_series("subaccount", "Montant", by_subaccount.head(10))],
            ),
        ]

        tables = [
            table_from_frame(
                "accounting-by-subaccount-table",
                "Montant par client ou sous-compte",
                by_subaccount.head(10),
                [("label", "Client / sous-compte"), ("value", "Montant")],
            ),
            accounting_issue_table(
                "accounting-incomplete-table",
                "Détection des écritures incomplètes",
                incomplete_rows.head(10),
            ),
            accounting_issue_table(
                "accounting-invalid-amounts-table",
                "Détection des montants vides ou égaux à zéro",
                invalid_amount_rows.head(10),
            ),
        ]

        return ClientDemoSection(
            id="controle-comptable",
            title="Contrôle Comptable",
            cards=cards,
            charts=charts,
            tables=tables,
            alerts=alerts,
        )

    def _build_alert_section(
        self,
        alerts: list[AlertRead],
        company_id: str | None,
        signals: dict[str, MetricSignal],
    ) -> ClientDemoSection:
        all_alerts = self._list_alerts(company_id) if company_id else alerts
        active_alerts = [alert for alert in all_alerts if alert.isActive]
        rules = self.db.scalars(
            select(DecisionRuleORM)
            .where(DecisionRuleORM.company_id == company_id)
            .order_by(DecisionRuleORM.priority.desc(), DecisionRuleORM.name.asc())
        ).all() if company_id else []

        severity_counts = {
            "critical": sum(1 for alert in active_alerts if alert.severity == "critical"),
            "warning": sum(1 for alert in active_alerts if alert.severity == "warning"),
            "info": sum(1 for alert in active_alerts if alert.severity == "info"),
        }

        cards = [
            metric_card("alerts-total", "Alertes actives", len(active_alerts), "count", "TND"),
            metric_card("alerts-critical", "Alertes critiques", severity_counts["critical"], "count", "TND"),
            metric_card("alerts-warning", "Alertes warning", severity_counts["warning"], "count", "TND"),
            metric_card("alerts-info", "Alertes info", severity_counts["info"], "count", "TND"),
            metric_card("rules-total", "Règles actives", len(rules), "count", "TND"),
        ]

        charts = [
            donut_chart(
                "alerts-by-severity",
                "Répartition des alertes par sévérité",
                [
                    chart_series(
                        "severity",
                        "Alertes",
                        pd.DataFrame(
                            [
                                {"label": "Critique", "value": severity_counts["critical"]},
                                {"label": "Warning", "value": severity_counts["warning"]},
                                {"label": "Info", "value": severity_counts["info"]},
                            ]
                        ),
                    )
                ],
            ),
            bar_chart(
                "alerts-key-signals",
                "Signaux utilisés par les règles",
                [
                    chart_series(
                        "signals",
                        "Valeur",
                        pd.DataFrame(
                            [
                                {"label": signal.label, "value": signal.value}
                                for signal in list(signals.values())[:6]
                            ]
                        ),
                    )
                ],
            ),
        ]

        alert_rows = pd.DataFrame(
            [
                {
                    "severity": alert.severity,
                    "title": alert.title,
                    "recommendation": alert.recommendation,
                    "rule": alert.ruleName,
                }
                for alert in active_alerts
            ]
        )
        rule_rows = pd.DataFrame(
            [
                {
                    "name": rule.name,
                    "severity": rule.severity,
                    "enabled": "Oui" if rule.enabled else "Non",
                    "section": find_rule_section(rule.id) or "alertes-regles",
                }
                for rule in rules
            ]
        )

        tables = [
            table_from_frame(
                "alerts-active-table",
                "Alertes générées automatiquement",
                alert_rows,
                [
                    ("severity", "Sévérité"),
                    ("title", "Alerte"),
                    ("rule", "Règle"),
                    ("recommendation", "Recommandation"),
                ],
            ),
            table_from_frame(
                "alerts-rules-table",
                "Catalogue des règles",
                rule_rows,
                [
                    ("name", "Règle"),
                    ("severity", "Sévérité"),
                    ("section", "Section"),
                    ("enabled", "Active"),
                ],
            ),
        ]

        return ClientDemoSection(
            id="alertes-regles",
            title="Alertes & Recommandations" if is_on_ing_company(company_id) else "Alertes & Règles",
            cards=cards,
            charts=charts,
            tables=tables,
            alerts=active_alerts,
        )

    def _finalize_client_section(self, section: ClientDemoSection) -> ClientDemoSection:
        charts = [chart for chart in section.charts if any(series.points for series in chart.series)]
        tables = [
            table
            for table in section.tables
            if table.columns and any(any(value not in (None, "", "n/a") for value in row.values()) for row in table.rows)
        ]

        if not tables:
            fallback_rows = [
                {
                    "metric": card.label,
                    "value": card.displayValue,
                    "comment": card.helperText or section.title,
                }
                for card in section.cards[:6]
                if str(card.displayValue).strip() not in {"", "n/a", "None"}
            ]
            if fallback_rows:
                tables = [
                    ClientDemoTable(
                        id=f"{section.id}-summary",
                        title=f"Synthèse {section.title}",
                        columns=[
                            ClientDemoTableColumn(key="metric", label="Indicateur"),
                            ClientDemoTableColumn(key="value", label="Valeur"),
                            ClientDemoTableColumn(key="comment", label="Lecture"),
                        ],
                        rows=fallback_rows,
                    )
                ]

        return section.model_copy(update={"charts": charts, "tables": tables})

    def _group_alerts_by_section(self, alerts: list[AlertRead]) -> dict[str, list[AlertRead]]:
        grouped: dict[str, list[AlertRead]] = {"alertes-regles": list(alerts)}
        for alert in alerts:
            section_id = find_rule_section(alert.ruleId) or "alertes-regles"
            grouped.setdefault(section_id, []).append(alert)
        return grouped

    def _list_alerts(self, company_id: str | None) -> list[AlertRead]:
        if not company_id:
            return []

        alerts = self.db.scalars(
            select(AlertORM)
            .where(AlertORM.company_id == company_id)
            .order_by(AlertORM.is_active.desc(), AlertORM.created_at.desc())
        ).all()
        return [self._to_alert_read(alert) for alert in alerts]

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
            createdAt=alert.created_at.isoformat(),
            triggerCount=alert.trigger_count,
            firstTriggeredAt=alert.first_triggered_at.isoformat() if alert.first_triggered_at else None,
            lastTriggeredAt=alert.last_triggered_at.isoformat() if alert.last_triggered_at else None,
            resolvedAt=alert.resolved_at.isoformat() if alert.resolved_at else None,
            resolvedByUserId=alert.resolved_by_user_id,
            triggeredBy=AlertTrigger(**raw_trigger) if raw_trigger else None,
            matchedConditions=[AlertTrigger(**condition) for condition in raw_conditions],
        )


def prepare_import_frame(frame: pd.DataFrame) -> pd.DataFrame:
    prepared = frame.copy()
    if prepared.empty:
        for column in IMPORT_FRAME_COLUMNS:
            if column not in prepared.columns:
                prepared[column] = pd.Series(dtype="object")
        prepared["purchase_effective"] = pd.Series(dtype="float64")
        prepared["margin_effective"] = pd.Series(dtype="float64")
        prepared["margin_rate_effective"] = pd.Series(dtype="float64")
        prepared["invoice_effective_amount"] = pd.Series(dtype="float64")
        prepared["project_display"] = pd.Series(dtype="object")
        prepared["project_key"] = pd.Series(dtype="object")
        prepared["status_display"] = pd.Series(dtype="object")
        prepared["status_normalized"] = pd.Series(dtype="object")
        prepared["subaccount_display"] = pd.Series(dtype="object")
        prepared["currency_display"] = pd.Series(dtype="object")
        prepared["invoice_key"] = pd.Series(dtype="object")
        prepared["is_completed"] = pd.Series(dtype="bool")
        prepared["is_in_progress"] = pd.Series(dtype="bool")
        prepared["is_overdue"] = pd.Series(dtype="bool")
        prepared["is_ending_soon"] = pd.Series(dtype="bool")
        prepared["duration_days"] = pd.Series(dtype="float64")
        prepared["year_label"] = pd.Series(dtype="object")
        prepared["month_label"] = pd.Series(dtype="object")
        return prepared

    for column in IMPORT_FRAME_COLUMNS:
        if column not in prepared.columns:
            prepared[column] = None

    prepared["source_type"] = prepared["source_type"].fillna("generic").astype(str).str.strip()
    for column in ["business_date", "start_date", "end_date"]:
        prepared[column] = pd.to_datetime(prepared[column], errors="coerce", utc=True)

    required_numeric = ["revenue_amount", "cost_amount"]
    optional_numeric = [
        "forecast_revenue_amount",
        "purchase_amount",
        "margin_amount",
        "margin_rate",
        "debit_amount",
        "credit_amount",
        "invoice_amount",
    ]
    for column in required_numeric:
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce").fillna(0.0)
    for column in optional_numeric:
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce")

    for column in [
        "project_code",
        "project_name",
        "original_project_reference",
        "normalized_project_reference",
        "category",
        "product",
        "client",
        "original_client_name",
        "normalized_client_name",
        "client_group",
        "responsible",
        "resource_name",
        "business_pole",
        "original_business_pole",
        "normalized_business_pole",
        "status",
        "invoice_number",
        "currency",
        "account_code",
        "subaccount",
        "description",
    ]:
        prepared[column] = prepared[column].fillna("").astype(str).map(clean_text)

    prepared["purchase_effective"] = prepared["purchase_amount"].where(
        prepared["purchase_amount"].notna(), prepared["cost_amount"]
    ).fillna(0.0)
    prepared["margin_effective"] = prepared["margin_amount"].where(
        prepared["margin_amount"].notna(),
        prepared["revenue_amount"] - prepared["purchase_effective"],
    )
    prepared["margin_rate_effective"] = prepared["margin_rate"].where(
        prepared["margin_rate"].notna(),
        prepared.apply(
            lambda row: row["margin_effective"] / row["revenue_amount"] * 100
            if row["revenue_amount"]
            else 0.0,
            axis=1,
        ),
    ).fillna(0.0)
    prepared["invoice_effective_amount"] = prepared["invoice_amount"].where(
        prepared["invoice_amount"].notna(),
        prepared[["debit_amount", "credit_amount"]].fillna(0.0).max(axis=1),
    ).fillna(0.0)
    prepared["project_display"] = prepared.apply(
        lambda row: first_non_empty(
            row["project_name"],
            row["project_code"],
            row["description"],
            row["client"],
            "Projet non libellé",
        ),
        axis=1,
    )
    prepared["project_key"] = prepared.apply(
        lambda row: first_non_empty(
            row["normalized_project_reference"],
            row["original_project_reference"],
            row["project_code"],
            row["project_name"],
            row["invoice_number"],
            row["description"],
            row["client"],
            "unknown-project",
        ),
        axis=1,
    )
    prepared["status_display"] = prepared["status"].replace("", "Non renseigné")
    prepared["status_normalized"] = prepared["status_display"].map(normalize_label)
    prepared["business_pole"] = prepared["business_pole"].replace("", "Non renseigné")
    prepared["responsible"] = prepared["responsible"].replace("", "")
    prepared["resource_name"] = prepared["resource_name"].replace("", "")
    prepared["client"] = prepared["client"].replace("", "")
    prepared["subaccount_display"] = prepared["subaccount"].where(
        prepared["subaccount"].ne(""),
        prepared["client"].where(prepared["client"].ne(""), "Non renseigné"),
    )
    prepared["currency_display"] = prepared["currency"].replace("", "Devise principale")
    prepared["invoice_key"] = prepared.apply(
        lambda row: first_non_empty(
            row["invoice_number"],
            row["account_code"],
            row["subaccount"],
            row["description"],
        ),
        axis=1,
    )

    now_utc = pd.Timestamp(datetime.now(tz=timezone.utc))
    completed_statuses = {
        "complete",
        "completed",
        "done",
        "finished",
        "close",
        "closed",
        "termine",
        "terminee",
        "terminer",
        "terminee",
        "cloture",
        "cloturee",
    }
    in_progress_statuses = {
        "active",
        "open",
        "ongoing",
        "inprogress",
        "encours",
        "en cours",
    }
    prepared["is_completed"] = prepared["status_normalized"].isin(completed_statuses)
    prepared["is_in_progress"] = prepared["status_normalized"].isin(in_progress_statuses) | (
        prepared["status_normalized"].eq("") & ~prepared["is_completed"]
    )
    prepared["is_overdue"] = (
        prepared["end_date"].notna()
        & (prepared["end_date"] < now_utc)
        & ~prepared["is_completed"]
    )
    prepared["is_ending_soon"] = (
        prepared["end_date"].notna()
        & (prepared["end_date"] >= now_utc)
        & (prepared["end_date"] <= now_utc + pd.Timedelta(days=30))
        & ~prepared["is_completed"]
    )
    prepared["duration_days"] = (
        prepared["end_date"] - prepared["start_date"]
    ).dt.days.where(prepared["start_date"].notna() & prepared["end_date"].notna())
    prepared["year_label"] = prepared["business_date"].dt.strftime("%Y")
    prepared["month_label"] = prepared["business_date"].dt.strftime("%Y-%m")
    return prepared


def select_preferred_revenue_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    for source_type in ["ca_projects", "pnl", "affair_tracking"]:
        scoped = frame[
            (frame["source_type"] == source_type) & (frame["revenue_amount"].fillna(0) > 0)
        ].copy()
        if not scoped.empty:
            return scoped
    return frame[frame["revenue_amount"].fillna(0) > 0].copy()


def select_project_snapshot_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    project_sources = frame[
        frame["source_type"].isin(["affair_tracking", "ca_projects"])
        & frame["project_key"].ne("unknown-project")
    ].copy()
    if project_sources.empty:
        return project_sources
    return (
        project_sources.sort_values("business_date")
        .drop_duplicates(subset=["project_key"], keep="last")
        .reset_index(drop=True)
    )


def aggregate_by_period(frame: pd.DataFrame, value_column: str, period: str) -> pd.DataFrame:
    if frame.empty or value_column not in frame.columns:
        return pd.DataFrame(columns=["label", "value"])
    working = frame[["business_date", value_column]].copy()
    working = working.dropna(subset=["business_date"])
    if working.empty:
        return pd.DataFrame(columns=["label", "value"])
    working["value"] = pd.to_numeric(working[value_column], errors="coerce").fillna(0.0)
    working["label"] = working["business_date"].dt.strftime("%Y" if period == "year" else "%Y-%m")
    return (
        working.groupby("label", as_index=False)["value"]
        .sum()
        .sort_values("label")
        .reset_index(drop=True)
    )


def aggregate_group_sum(frame: pd.DataFrame, group_column: str, value_column: str) -> pd.DataFrame:
    if frame.empty or group_column not in frame.columns or value_column not in frame.columns:
        return pd.DataFrame(columns=["label", "value"])
    working = frame[[group_column, value_column]].copy()
    working[group_column] = working[group_column].fillna("").astype(str).map(clean_text)
    working = working[working[group_column] != ""]
    if working.empty:
        return pd.DataFrame(columns=["label", "value"])
    working["value"] = pd.to_numeric(working[value_column], errors="coerce").fillna(0.0)
    result = (
        working.groupby(group_column, as_index=False)["value"]
        .sum()
        .rename(columns={group_column: "label"})
        .sort_values("value", ascending=False)
        .reset_index(drop=True)
    )
    return result


def aggregate_group_count(frame: pd.DataFrame, group_column: str) -> pd.DataFrame:
    if frame.empty or group_column not in frame.columns:
        return pd.DataFrame(columns=["label", "value"])
    working = frame[[group_column]].copy()
    working[group_column] = working[group_column].fillna("").astype(str).map(clean_text)
    working = working[working[group_column] != ""]
    if working.empty:
        return pd.DataFrame(columns=["label", "value"])
    return (
        working.groupby(group_column, as_index=False)
        .size()
        .rename(columns={group_column: "label", "size": "value"})
        .sort_values("value", ascending=False)
        .reset_index(drop=True)
    )


def aggregate_group_totals(
    frame: pd.DataFrame,
    group_column: str,
    value_columns: list[str],
) -> pd.DataFrame:
    if frame.empty or group_column not in frame.columns:
        return pd.DataFrame(columns=[group_column, *value_columns])

    available_value_columns = [column for column in value_columns if column in frame.columns]
    if not available_value_columns:
        return pd.DataFrame(columns=[group_column, *value_columns])

    working = frame[[group_column, *available_value_columns]].copy()
    working[group_column] = working[group_column].fillna("").astype(str).map(clean_text)
    working = working[working[group_column] != ""]
    if working.empty:
        return pd.DataFrame(columns=[group_column, *value_columns])

    for column in available_value_columns:
        working[column] = pd.to_numeric(working[column], errors="coerce").fillna(0.0)

    grouped = (
        working.groupby(group_column, as_index=False)[available_value_columns]
        .sum()
        .sort_values(available_value_columns[0], ascending=False)
        .reset_index(drop=True)
    )
    for column in value_columns:
        if column not in grouped.columns:
            grouped[column] = 0.0
    return grouped[[group_column, *value_columns]]


def count_duplicate_non_empty_values(series: pd.Series) -> int:
    if series.empty:
        return 0
    cleaned = series.fillna("").astype(str).map(clean_text)
    cleaned = cleaned[cleaned != ""]
    return int(cleaned.duplicated().sum())


def project_detail_table(table_id: str, title: str, frame: pd.DataFrame) -> ClientDemoTable:
    if frame.empty:
        return ClientDemoTable(id=table_id, title=title, columns=[], rows=[])

    rows = []
    for _, row in frame.iterrows():
        rows.append(
            {
                "project": row["project_display"],
                "client": row["client"] or "n/a",
                "responsible": row["responsible"] or "n/a",
                "pole": row["business_pole"] or "n/a",
                "status": row["status_display"],
                "endDate": row["end_date"].strftime("%Y-%m-%d") if pd.notnull(row["end_date"]) else "n/a",
                "marginRate": round(float(row["margin_rate_effective"]), 2),
            }
        )

    return ClientDemoTable(
        id=table_id,
        title=title,
        columns=[
            ClientDemoTableColumn(key="project", label="Projet"),
            ClientDemoTableColumn(key="client", label="Client"),
            ClientDemoTableColumn(key="responsible", label="Responsable"),
            ClientDemoTableColumn(key="pole", label="Pôle"),
            ClientDemoTableColumn(key="status", label="Statut"),
            ClientDemoTableColumn(key="endDate", label="Date de fin"),
            ClientDemoTableColumn(key="marginRate", label="Taux marge"),
        ],
        rows=rows,
    )


def accounting_issue_table(table_id: str, title: str, frame: pd.DataFrame) -> ClientDemoTable:
    if frame.empty:
        return ClientDemoTable(id=table_id, title=title, columns=[], rows=[])

    rows = []
    for _, row in frame.iterrows():
        rows.append(
            {
                "date": row["business_date"].strftime("%Y-%m-%d") if pd.notnull(row["business_date"]) else "n/a",
                "invoice": row["invoice_number"] or "n/a",
                "client": row["client"] or "n/a",
                "subaccount": row["subaccount"] or "n/a",
                "currency": row["currency"] or "n/a",
                "amount": round(float(row["invoice_effective_amount"]), 2),
            }
        )

    return ClientDemoTable(
        id=table_id,
        title=title,
        columns=[
            ClientDemoTableColumn(key="date", label="Date"),
            ClientDemoTableColumn(key="invoice", label="Facture"),
            ClientDemoTableColumn(key="client", label="Client"),
            ClientDemoTableColumn(key="subaccount", label="Sous-compte"),
            ClientDemoTableColumn(key="currency", label="Devise"),
            ClientDemoTableColumn(key="amount", label="Montant"),
        ],
        rows=rows,
    )


def table_from_frame(
    table_id: str,
    title: str,
    frame: pd.DataFrame,
    columns: list[tuple[str, str]],
) -> ClientDemoTable:
    if frame.empty:
        return ClientDemoTable(id=table_id, title=title, columns=[], rows=[])

    rows = []
    for _, row in frame.iterrows():
        rows.append({key: serialize_table_value(row.get(key)) for key, _ in columns})
    return ClientDemoTable(
        id=table_id,
        title=title,
        columns=[ClientDemoTableColumn(key=key, label=label) for key, label in columns],
        rows=rows,
    )


def serialize_table_value(value: object) -> str | int | float | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        return round(value, 2) if isinstance(value, float) else value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def chart_series(key: str, label: str, frame: pd.DataFrame) -> ClientDemoChartSeries:
    if frame.empty:
        return ClientDemoChartSeries(key=key, label=label, points=[])

    safe_frame = frame.copy()
    safe_frame["value"] = pd.to_numeric(safe_frame["value"], errors="coerce")
    safe_frame = safe_frame[safe_frame["value"].notna()]

    return ClientDemoChartSeries(
        key=key,
        label=label,
        points=[
            ClientDemoChartPoint(label=str(row["label"]), value=float(row["value"]))
            for _, row in safe_frame.iterrows()
        ],
    )


def report_frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame.from_records(rows, columns=["label", "value"])


def line_chart(chart_id: str, title: str, series: list[ClientDemoChartSeries]) -> ClientDemoChart:
    return ClientDemoChart(id=chart_id, title=title, kind="line", series=series)


def bar_chart(chart_id: str, title: str, series: list[ClientDemoChartSeries]) -> ClientDemoChart:
    return ClientDemoChart(id=chart_id, title=title, kind="bar", series=series)


def donut_chart(chart_id: str, title: str, series: list[ClientDemoChartSeries]) -> ClientDemoChart:
    return ClientDemoChart(id=chart_id, title=title, kind="donut", series=series)


def metric_card(
    code: str,
    label: str,
    value: float | int,
    unit: str,
    currency: str,
    tone: str = "info",
    helper: str | None = None,
) -> ClientDemoMetricCard:
    numeric_value = safe_numeric_value(value)
    if unit == "currency":
        display_value = format_currency(numeric_value, currency)
    elif unit == "percent":
        display_value = format_percent(numeric_value)
    elif unit == "days":
        display_value = f"{numeric_value:,.0f} j"
    else:
        display_value = format_number(numeric_value)

    return ClientDemoMetricCard(
        code=code,
        label=label,
        value=numeric_value,
        displayValue=display_value,
        unit=unit,
        tone=tone,  # type: ignore[arg-type]
        helperText=helper,
    )


def signal_card(
    signal: MetricSignal,
    tone: str = "info",
    helper: str | None = None,
) -> ClientDemoMetricCard:
    numeric_value = safe_numeric_value(signal.value)
    return ClientDemoMetricCard(
        code=signal.code,
        label=signal.label,
        value=numeric_value,
        displayValue=signal.display_value if str(signal.display_value).strip() else format_number(numeric_value),
        unit=signal.unit,
        tone=tone,  # type: ignore[arg-type]
        helperText=helper,
    )


def safe_numeric_value(value: object) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0

    if math.isnan(numeric) or math.isinf(numeric):
        return 0.0
    return numeric


def safe_average(series: pd.Series) -> float:
    if series.empty:
        return 0.0
    valid = pd.to_numeric(series, errors="coerce").dropna()
    return round(float(valid.mean()), 2) if not valid.empty else 0.0


def percent_change(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return round(((current - previous) / previous) * 100, 2)


def sum_year(frame: pd.DataFrame, year: int, value_column: str) -> float:
    if frame.empty:
        return 0.0
    return round(
        float(
            frame.loc[frame["business_date"].dt.year == year, value_column]
            .fillna(0)
            .sum()
        ),
        2,
    )


def resolve_percent_tone(value: float) -> str:
    if value < 0:
        return "danger"
    if value < 5:
        return "warning"
    return "success"


def resolve_margin_tone(value: float) -> str:
    if value < 15:
        return "danger"
    if value < 30:
        return "warning"
    return "success"


def format_currency(value: float, currency: str) -> str:
    return f"{value:,.0f} {currency}"


def format_percent(value: float) -> str:
    return f"{value:.1f}%"


def format_number(value: float | int) -> str:
    return f"{float(value):,.0f}"


def count_distinct_non_empty(frame: pd.DataFrame, column: str) -> int:
    if frame.empty or column not in frame.columns:
        return 0
    values = frame[column].fillna("").astype(str).map(clean_text)
    values = values[values != ""]
    return int(values.nunique())


def detect_primary_currency(frame: pd.DataFrame, fallback: str) -> str:
    if frame.empty or "currency" not in frame.columns:
        return fallback
    non_empty = frame["currency"].fillna("").astype(str).map(clean_text)
    non_empty = non_empty[non_empty != ""]
    if non_empty.empty:
        return fallback
    return str(non_empty.mode().iloc[0])


def clean_text(value: str | None) -> str:
    if value is None:
        return ""
    normalized = str(value).strip()
    return normalized


def normalize_label(value: str | None) -> str:
    cleaned = clean_text(value).lower()
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", cleaned)
        if not unicodedata.combining(character)
    )


def first_non_empty(*values: object) -> str:
    for value in values:
        if value is None:
            continue
        normalized = clean_text(str(value))
        if normalized:
            return normalized
    return ""
