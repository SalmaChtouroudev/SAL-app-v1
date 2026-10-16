from __future__ import annotations

from datetime import datetime, timezone
import json
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import AlertHistoryORM, AlertORM, CompanyORM, DecisionRuleORM
from app.schemas.platform import AlertTrigger
from app.services.client_demo_analytics import MetricSignal, build_metric_signals, load_company_import_frame
from app.services.client_demo_catalog import get_client_demo_rule_templates


class ClientDemoRuleEngineService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def sync_company(self, company_id: str) -> None:
        self.ensure_company_rules(company_id)

        company = self.db.scalar(select(CompanyORM).where(CompanyORM.id == company_id))
        currency = company.currency if company else "TND"
        frame = load_company_import_frame(self.db, company_id)
        signals = build_metric_signals(frame, currency)
        now = datetime.now(tz=timezone.utc)

        self.db.execute(delete(AlertHistoryORM).where(AlertHistoryORM.company_id == company_id))
        self.db.execute(delete(AlertORM).where(AlertORM.company_id == company_id))

        rules = self.db.scalars(
            select(DecisionRuleORM)
            .where(DecisionRuleORM.company_id == company_id, DecisionRuleORM.enabled.is_(True))
            .order_by(DecisionRuleORM.priority.desc(), DecisionRuleORM.name.asc())
        ).all()

        for rule in rules:
            matched_conditions = self._match_rule_conditions(rule.payload, rule.logic, signals)
            if not matched_conditions:
                continue

            message = self._build_message(rule.title_fr or rule.name, matched_conditions)
            recommendation = rule.recommendation_template_fr or rule.recommendation_template_en or rule.name
            alert_id = f"alt-{uuid4().hex[:12]}"

            self.db.add(
                AlertORM(
                    id=alert_id,
                    company_id=company_id,
                    rule_id=rule.id,
                    source=rule.name,
                    rule_name=rule.name,
                    title=rule.title_fr or rule.title_en or rule.name,
                    message=message,
                    severity=rule.severity,
                    is_active=True,
                    explainability_text=message,
                    recommendation=recommendation,
                    triggered_payload=json.dumps(matched_conditions[0].model_dump()),
                    matched_conditions_payload=json.dumps(
                        [condition.model_dump() for condition in matched_conditions]
                    ),
                    trigger_count=1,
                    first_triggered_at=now,
                    last_triggered_at=now,
                    created_at=now,
                )
            )
            self.db.add(
                AlertHistoryORM(
                    id=f"ah-{uuid4().hex[:12]}",
                    alert_id=alert_id,
                    company_id=company_id,
                    rule_id=rule.id,
                    rule_name=rule.name,
                    event_type="TRIGGERED",
                    severity=rule.severity,
                    title=rule.title_fr or rule.title_en or rule.name,
                    message=message,
                    recommendation=recommendation,
                    alert_status="ACTIVE",
                    event_source="RULE_ENGINE",
                    evaluation_window="client-demo-refresh",
                    context_bucket=now.strftime("%Y-%m"),
                    lifecycle_note="Client demo rule engine evaluated the latest imported data.",
                    triggered_payload=json.dumps(matched_conditions[0].model_dump()),
                    matched_conditions_payload=json.dumps(
                        [condition.model_dump() for condition in matched_conditions]
                    ),
                    occurred_at=now,
                )
            )

    def ensure_company_rules(self, company_id: str) -> None:
        existing = {
            rule.id: rule
            for rule in self.db.scalars(
                select(DecisionRuleORM).where(DecisionRuleORM.company_id == company_id)
            ).all()
        }
        now = datetime.now(tz=timezone.utc)

        for template in get_client_demo_rule_templates(company_id):
            payload = json.dumps(list(template.conditions))
            if template.id in existing:
                rule = existing[template.id]
                rule.name = template.name
                rule.priority = self._priority_for_severity(template.severity)
                rule.severity = template.severity
                rule.logic = template.logic
                rule.action_type = template.action_type
                rule.title_en = template.title_en
                rule.title_fr = template.title_fr
                rule.recommendation_template_en = template.recommendation_en
                rule.recommendation_template_fr = template.recommendation_fr
                rule.explanation_template_en = template.title_en
                rule.explanation_template_fr = template.title_fr
                rule.payload = payload
                rule.enabled = True
                rule.updated_at = now
                self.db.add(rule)
                continue

            self.db.add(
                DecisionRuleORM(
                    id=template.id,
                    company_id=company_id,
                    name=template.name,
                    priority=self._priority_for_severity(template.severity),
                    severity=template.severity,
                    logic=template.logic,
                    action_type=template.action_type,
                    title_en=template.title_en,
                    title_fr=template.title_fr,
                    explanation_template_en=template.title_en,
                    explanation_template_fr=template.title_fr,
                    recommendation_template_en=template.recommendation_en,
                    recommendation_template_fr=template.recommendation_fr,
                    payload=payload,
                    enabled=True,
                    created_at=now,
                    updated_at=now,
                )
            )

        self.db.flush()

    def _match_rule_conditions(
        self,
        payload: str,
        logic: str,
        signals: dict[str, MetricSignal],
    ) -> list[AlertTrigger]:
        raw_conditions = json.loads(payload)
        matches: list[AlertTrigger] = []
        condition_results: list[bool] = []

        for condition in raw_conditions:
            signal = signals.get(str(condition.get("kpiCode")))
            if signal is None:
                condition_results.append(False)
                continue

            threshold = float(condition.get("threshold") or 0)
            operator = str(condition.get("operator") or "GT").upper()
            matched = self._compare(signal.value, operator, threshold)
            condition_results.append(matched)
            if matched:
                matches.append(
                    AlertTrigger(
                        kpiCode=signal.code,
                        kpiLabel=signal.label,
                        actualValue=signal.value,
                        actualValueLabel=signal.display_value,
                        threshold=threshold,
                        thresholdLabel=self._format_threshold(threshold, signal.unit),
                        operator=operator,
                        operatorLabel=self._operator_label(operator),
                        statement=(
                            f"{signal.label} est {self._operator_label(operator)} "
                            f"{self._format_threshold(threshold, signal.unit)} "
                            f"(actuel {signal.display_value})."
                        ),
                    )
                )

        if logic.upper() == "OR":
            return matches if any(condition_results) else []
        return matches if condition_results and all(condition_results) else []

    def _compare(self, actual: float, operator: str, threshold: float) -> bool:
        if operator == "GT":
            return actual > threshold
        if operator == "GTE":
            return actual >= threshold
        if operator == "LT":
            return actual < threshold
        if operator == "LTE":
            return actual <= threshold
        if operator == "EQ":
            return actual == threshold
        if operator == "NE":
            return actual != threshold
        return False

    def _format_threshold(self, threshold: float, unit: str) -> str:
        if unit == "currency":
            return f"{threshold:,.0f}"
        if unit == "percent":
            return f"{threshold:.1f}%"
        return f"{threshold:,.0f}"

    def _operator_label(self, operator: str) -> str:
        return {
            "GT": "au-dessus de",
            "GTE": "au moins",
            "LT": "en dessous de",
            "LTE": "au plus",
            "EQ": "égal à",
            "NE": "différent de",
        }.get(operator, operator)

    def _build_message(self, title: str, conditions: list[AlertTrigger]) -> str:
        joined_conditions = " ; ".join(condition.statement for condition in conditions)
        return f"{title}. {joined_conditions}"

    def _priority_for_severity(self, severity: str) -> int:
        if severity == "critical":
            return 95
        if severity == "warning":
            return 80
        return 60
