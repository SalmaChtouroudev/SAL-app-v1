from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.core.security import hash_password
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
from app.services.on_ing_profile import apply_company_profile_overrides


def utc_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class DemoPlatformRepository(PlatformRepository):
    def __init__(self) -> None:
        self._companies = [
            CompanyRead(
                id="ent-sal-001",
                name="SAL Holding Tunisia",
                sector="Business Services",
                plan="Enterprise",
                health="healthy",
                country="Tunisia",
                currency="TND",
                monthlyTarget=245000,
                headquarters="Tunis",
                lastSyncAt=utc_iso(),
            ),
            CompanyRead(
                id="ent-sal-010",
                name="ON INGENIERIE",
                sector="Bureau d’étude technique / Ingénierie bâtiment",
                plan="Growth",
                health="healthy",
                country="Tunisie",
                currency="EUR",
                monthlyTarget=285000,
                headquarters="Tunis",
                lastSyncAt=utc_iso(),
                shortName="ON ING",
                profileCode="ON_ING",
                mainMarket="France",
                subtitle="Business Intelligence pour bureau d’études techniques",
                technicalPoles=[
                    "ELEC",
                    "CVC",
                    "Fluides",
                    "Plomberie",
                    "Sécurité incendie",
                    "BIM",
                ],
                navigationLabels=[
                    "Vue Direction",
                    "Chiffre d’affaires",
                    "Affaires / Projets",
                    "Rentabilité",
                    "Clients",
                    "Prévisionnel",
                    "Comptabilité",
                    "Qualité des données",
                    "Alertes & Recommandations",
                ],
            ),
            CompanyRead(
                id="ent-sal-022",
                name="Demo SME Distribution",
                sector="Wholesale distribution",
                plan="Growth",
                health="healthy",
                country="Belgium",
                currency="EUR",
                monthlyTarget=120000,
                headquarters="Brussels",
                lastSyncAt=utc_iso(),
            ),
        ]
        self._users = [
            RepositoryUser(
                user_id="sal-admin-001",
                enterprise_id="ent-sal-001",
                email="admin@sal.local",
                full_name="Nadia Ben Salem",
                role_type="SAL_ADMIN",
                title="Platform Director",
                password_hash=hash_password("Admin123!"),
                accessible_company_ids=["ent-sal-001", "ent-sal-010", "ent-sal-022"],
                permissions=[
                    "dashboard:view",
                    "import:create",
                    "decision:view",
                    "audit:view",
                    "report:export",
                    "users:manage",
                    "companies:manage",
                    "kpi:manage",
                ],
                primary_company_id="ent-sal-001",
                created_at="2023-01-15T09:30:00.000Z",
            ),
            RepositoryUser(
                user_id="ent-admin-010",
                enterprise_id="ent-sal-022",
                email="entadmin@sal.local",
                full_name="Demo Operations Manager",
                role_type="ENT_ADMIN",
                title="Operations Lead",
                password_hash=hash_password("Admin123!"),
                accessible_company_ids=["ent-sal-022"],
                permissions=[
                    "dashboard:view",
                    "import:create",
                    "decision:view",
                    "audit:view",
                    "report:export",
                    "users:manage",
                    "kpi:manage",
                ],
                primary_company_id="ent-sal-022",
                created_at="2023-04-02T10:10:00.000Z",
            ),
            RepositoryUser(
                user_id="pme-user-101",
                enterprise_id="ent-sal-022",
                email="user@sal.local",
                full_name="Demo Executive Viewer",
                role_type="PME_USER",
                title="Executive Viewer",
                password_hash=hash_password("User123!"),
                accessible_company_ids=["ent-sal-022"],
                permissions=["dashboard:view", "decision:view", "audit:view", "report:export"],
                primary_company_id="ent-sal-022",
                created_at="2023-08-20T07:50:00.000Z",
            ),
        ]
        self._trend_by_company = {
            "ent-sal-010": [
                DashboardTrendPoint(bucket="2025-10", totalRevenue=122120, totalExpenses=85500, netMargin=36620),
                DashboardTrendPoint(bucket="2025-11", totalRevenue=115884, totalExpenses=86400, netMargin=29484),
                DashboardTrendPoint(bucket="2025-12", totalRevenue=109648, totalExpenses=87300, netMargin=22348),
                DashboardTrendPoint(bucket="2026-01", totalRevenue=103412, totalExpenses=88200, netMargin=15212),
                DashboardTrendPoint(bucket="2026-02", totalRevenue=97176, totalExpenses=89100, netMargin=8076),
                DashboardTrendPoint(bucket="2026-03", totalRevenue=90940, totalExpenses=90000, netMargin=940),
            ],
            "ent-sal-001": [
                DashboardTrendPoint(bucket="2025-10", totalRevenue=144000, totalExpenses=79200, netMargin=64800),
                DashboardTrendPoint(bucket="2025-11", totalRevenue=151000, totalExpenses=80800, netMargin=70200),
                DashboardTrendPoint(bucket="2025-12", totalRevenue=156000, totalExpenses=81250, netMargin=74750),
                DashboardTrendPoint(bucket="2026-01", totalRevenue=161000, totalExpenses=82500, netMargin=78500),
                DashboardTrendPoint(bucket="2026-02", totalRevenue=165000, totalExpenses=83600, netMargin=81400),
                DashboardTrendPoint(bucket="2026-03", totalRevenue=169000, totalExpenses=84200, netMargin=84800),
            ],
            "ent-sal-022": [
                DashboardTrendPoint(bucket="2025-10", totalRevenue=83500, totalExpenses=65500, netMargin=18000),
                DashboardTrendPoint(bucket="2025-11", totalRevenue=81200, totalExpenses=64800, netMargin=16400),
                DashboardTrendPoint(bucket="2025-12", totalRevenue=80600, totalExpenses=65100, netMargin=15500),
                DashboardTrendPoint(bucket="2026-01", totalRevenue=79800, totalExpenses=65900, netMargin=13900),
                DashboardTrendPoint(bucket="2026-02", totalRevenue=78300, totalExpenses=66100, netMargin=12200),
                DashboardTrendPoint(bucket="2026-03", totalRevenue=77600, totalExpenses=66600, netMargin=11000),
            ],
        }
        self._kpi_definitions = [
            KpiDefinitionRead(
                id="kpi-revenue-ent-001",
                companyId="ent-sal-001",
                name="Revenue",
                category="Finance",
                formula="SUM(REVENUE)",
                threshold=100000,
                unit="currency",
                direction="up",
                description="Tracks total recognized revenue across uploaded sources.",
                sourceKey="revenue",
                createdAt=utc_iso(),
                updatedAt=utc_iso(),
            ),
            KpiDefinitionRead(
                id="kpi-growth-ent-001",
                companyId="ent-sal-001",
                name="Growth",
                category="Sales",
                formula="(Current Revenue - Previous Revenue) / Previous Revenue",
                threshold=8,
                unit="percent",
                direction="up",
                description="Monthly growth versus previous period.",
                sourceKey="growth",
                createdAt=utc_iso(),
                updatedAt=utc_iso(),
            ),
            KpiDefinitionRead(
                id="kpi-charges-ent-010",
                companyId="ent-sal-010",
                name="Charges",
                category="Finance",
                formula="SUM(EXPENSE)",
                threshold=65000,
                unit="currency",
                direction="down",
                description="Operating charges tracked from imports.",
                sourceKey="charges",
                createdAt=utc_iso(),
                updatedAt=utc_iso(),
            ),
            KpiDefinitionRead(
                id="kpi-margin-ent-010",
                companyId="ent-sal-010",
                name="Margin",
                category="Finance",
                formula="(Revenue - Charges) / Revenue",
                threshold=18,
                unit="percent",
                direction="up",
                description="Net margin threshold used by alerts and recommendations.",
                sourceKey="margin",
                createdAt=utc_iso(),
                updatedAt=utc_iso(),
            ),
            DecisionRuleRead(
                id="rule-on-ing-client-dependency",
                companyId="ent-sal-010",
                name="Dépendance client élevée",
                priority=92,
                severity="warning",
                logic="AND",
                actionType="alert",
                enabled=True,
                titleEn="High client dependency",
                titleFr="Dépendance client élevée",
                explanationTemplateEn="The leading client concentration is above the expected threshold.",
                explanationTemplateFr="La concentration du chiffre d’affaires sur un client dépasse le seuil attendu.",
                recommendationTemplateEn="Diversify the client portfolio and reduce commercial dependency.",
                recommendationTemplateFr="Diversifiez le portefeuille clients et réduisez la dépendance commerciale.",
                conditions=[
                    DecisionRuleConditionRead(
                        id="cond-on-ing-client-concentration",
                        kpiCode="chargeRatio",
                        operator="GT",
                        threshold=40,
                    )
                ],
                createdAt=utc_iso(),
                updatedAt=utc_iso(),
            ),
            DecisionRuleRead(
                id="rule-on-ing-forecast-delay",
                companyId="ent-sal-010",
                name="Retard par rapport au prévisionnel",
                priority=90,
                severity="warning",
                logic="AND",
                actionType="alert",
                enabled=True,
                titleEn="Forecast delay versus plan",
                titleFr="Retard par rapport au prévisionnel",
                explanationTemplateEn="Forecast achievement remains below the expected level.",
                explanationTemplateFr="Le niveau d’atteinte du prévisionnel reste inférieur à l’objectif attendu.",
                recommendationTemplateEn="Review active projects, accelerate billing, and reinforce commercial follow-up.",
                recommendationTemplateFr="Analysez les affaires en cours, accélérez la facturation et renforcez les relances commerciales.",
                conditions=[
                    DecisionRuleConditionRead(
                        id="cond-on-ing-forecast-achievement",
                        kpiCode="margin",
                        operator="LT",
                        threshold=80,
                    )
                ],
                createdAt=utc_iso(),
                updatedAt=utc_iso(),
            ),
            DecisionRuleRead(
                id="rule-on-ing-low-margin-projects",
                companyId="ent-sal-010",
                name="Projets à faible marge",
                priority=88,
                severity="warning",
                logic="AND",
                actionType="alert",
                enabled=True,
                titleEn="Low margin projects",
                titleFr="Projets à faible marge",
                explanationTemplateEn="Several active projects are showing weak margin levels.",
                explanationTemplateFr="Plusieurs affaires actives présentent une marge insuffisante.",
                recommendationTemplateEn="Control purchases, worked time, and pricing on low-margin projects.",
                recommendationTemplateFr="Contrôlez les achats, le temps passé et la tarification des projets à faible marge.",
                conditions=[
                    DecisionRuleConditionRead(
                        id="cond-on-ing-low-margin-projects",
                        kpiCode="margin",
                        operator="LT",
                        threshold=25,
                    )
                ],
                createdAt=utc_iso(),
                updatedAt=utc_iso(),
            ),
            DecisionRuleRead(
                id="rule-on-ing-missing-resource",
                companyId="ent-sal-010",
                name="Ressource projet manquante",
                priority=85,
                severity="warning",
                logic="AND",
                actionType="alert",
                enabled=True,
                titleEn="Missing project resource",
                titleFr="Ressource projet manquante",
                explanationTemplateEn="Some active projects are not assigned to a named resource.",
                explanationTemplateFr="Certaines affaires actives ne sont pas affectées à une ressource identifiée.",
                recommendationTemplateEn="Assign a resource or mission owner to unassigned projects.",
                recommendationTemplateFr="Affectez une ressource ou un responsable mission aux affaires non affectées.",
                conditions=[
                    DecisionRuleConditionRead(
                        id="cond-on-ing-missing-resource",
                        kpiCode="growth",
                        operator="LT",
                        threshold=5,
                    )
                ],
                createdAt=utc_iso(),
                updatedAt=utc_iso(),
            ),
            DecisionRuleRead(
                id="rule-on-ing-remaining-to-invoice",
                companyId="ent-sal-010",
                name="Reste à facturer",
                priority=82,
                severity="info",
                logic="AND",
                actionType="alert",
                enabled=True,
                titleEn="Remaining revenue to invoice",
                titleFr="Reste à facturer",
                explanationTemplateEn="The remaining amount to invoice stays material on the current portfolio.",
                explanationTemplateFr="Le reste à facturer demeure significatif sur le portefeuille en cours.",
                recommendationTemplateEn="Review project progress and schedule the remaining billing.",
                recommendationTemplateFr="Vérifiez l’avancement des projets et planifiez la facturation restante.",
                conditions=[
                    DecisionRuleConditionRead(
                        id="cond-on-ing-remaining-to-invoice",
                        kpiCode="revenue",
                        operator="GT",
                        threshold=1,
                    )
                ],
                createdAt=utc_iso(),
                updatedAt=utc_iso(),
            ),
            DecisionRuleRead(
                id="rule-on-ing-data-quality",
                companyId="ent-sal-010",
                name="Qualité des données",
                priority=80,
                severity="warning",
                logic="AND",
                actionType="alert",
                enabled=True,
                titleEn="Data quality issue",
                titleFr="Qualité des données",
                explanationTemplateEn="The imported data still contains quality gaps that limit decision confidence.",
                explanationTemplateFr="Les données importées présentent encore des écarts de qualité qui limitent la fiabilité du pilotage.",
                recommendationTemplateEn="Clean missing fields across resources, poles, margins, dates, and billing data.",
                recommendationTemplateFr="Nettoyez les champs manquants sur les ressources, pôles, marges, dates et données de facturation.",
                conditions=[
                    DecisionRuleConditionRead(
                        id="cond-on-ing-data-quality",
                        kpiCode="growth",
                        operator="LT",
                        threshold=90,
                    )
                ],
                createdAt=utc_iso(),
                updatedAt=utc_iso(),
            ),
            DecisionRuleRead(
                id="rule-on-ing-accounting-control",
                companyId="ent-sal-010",
                name="Contrôle comptable",
                priority=95,
                severity="critical",
                logic="AND",
                actionType="alert",
                enabled=True,
                titleEn="Accounting control",
                titleFr="Contrôle comptable",
                explanationTemplateEn="Accounting consistency checks require immediate attention.",
                explanationTemplateFr="Les contrôles de cohérence comptable nécessitent une revue immédiate.",
                recommendationTemplateEn="Review accounting entries, vouchers, and debit/credit balances.",
                recommendationTemplateFr="Vérifiez les écritures comptables, les pièces justificatives et l’équilibre débit/crédit.",
                conditions=[
                    DecisionRuleConditionRead(
                        id="cond-on-ing-accounting-control",
                        kpiCode="chargeRatio",
                        operator="GT",
                        threshold=0,
                    )
                ],
                createdAt=utc_iso(),
                updatedAt=utc_iso(),
            ),
        ]
        self._report_breakdowns = {
            "ent-sal-010": {
                "products": [
                    ReportBreakdownItem(name="Eco Blender", revenue=28540),
                    ReportBreakdownItem(name="Thermo Kettle", revenue=21890),
                    ReportBreakdownItem(name="Smart Mixer", revenue=19640),
                ],
                "clients": [
                    ReportBreakdownItem(name="Carrefour Sfax", revenue=36420),
                    ReportBreakdownItem(name="Monoprix Centre", revenue=22880),
                    ReportBreakdownItem(name="MG Retail", revenue=18710),
                ],
            },
            "ent-sal-001": {
                "products": [
                    ReportBreakdownItem(name="Consulting Retainers", revenue=84200),
                    ReportBreakdownItem(name="Analytics Projects", revenue=46300),
                    ReportBreakdownItem(name="Training Services", revenue=31800),
                ],
                "clients": [
                    ReportBreakdownItem(name="North Africa Holding", revenue=90500),
                    ReportBreakdownItem(name="Tunisia Trade Group", revenue=44400),
                    ReportBreakdownItem(name="ScaleUp Labs", revenue=27400),
                ],
            },
            "ent-sal-022": {
                "products": [
                    ReportBreakdownItem(name="Cold Chain Packs", revenue=20400),
                    ReportBreakdownItem(name="Retail Displays", revenue=18750),
                    ReportBreakdownItem(name="POS Accessories", revenue=16340),
                ],
                "clients": [
                    ReportBreakdownItem(name="Phoenix Stores", revenue=28120),
                    ReportBreakdownItem(name="West Med Supply", revenue=20460),
                    ReportBreakdownItem(name="Delta Market", revenue=17310),
                ],
            },
        }
        self._rules = [
            DecisionRuleRead(
                id="rule-margin-growth-watch",
                companyId=None,
                name="Margin and growth watch",
                priority=95,
                severity="warning",
                logic="AND",
                actionType="both",
                enabled=True,
                titleEn="Margin pressure and revenue slowdown",
                titleFr="Pression sur la marge et ralentissement du chiffre d’affaires",
                explanationTemplateEn="Margin is {margin}, {marginDirection} by {marginVariation}, while revenue is {revenueDirection} by {revenueVariation}. This signals profitability pressure and weaker sales momentum.",
                explanationTemplateFr="La marge est de {margin}, en {marginDirection} de {marginVariation}, tandis que le chiffre d’affaires est en {revenueDirection} de {revenueVariation}. Cela signale une pression sur la rentabilité et un ralentissement commercial.",
                recommendationTemplateEn="Reduce controllable costs, review pricing, and focus sales efforts on profitable products and clients.",
                recommendationTemplateFr="Réduisez les coûts maîtrisables, revoyez le pricing et concentrez les efforts commerciaux sur les produits et clients rentables.",
                conditions=[
                    DecisionRuleConditionRead(
                        id="cond-margin-low", kpiCode="margin", operator="LT", threshold=20
                    ),
                    DecisionRuleConditionRead(
                        id="cond-growth-negative", kpiCode="growth", operator="LT", threshold=0
                    ),
                ],
                createdAt=utc_iso(),
                updatedAt=utc_iso(),
            ),
            DecisionRuleRead(
                id="rule-charge-ratio",
                companyId=None,
                name="Charges safe band",
                priority=88,
                severity="critical",
                logic="AND",
                actionType="alert",
                enabled=True,
                titleEn="Charges exceed safe operating band",
                titleFr="Les charges dépassent la zone d’exploitation sécurisée",
                explanationTemplateEn="Charges represent {chargeRatio} of revenue, {chargeRatioDirection} by {chargeRatioVariation}, which exceeds the acceptable operating band.",
                explanationTemplateFr="Les charges représentent {chargeRatio} du chiffre d’affaires, en {chargeRatioDirection} de {chargeRatioVariation}, ce qui dépasse la bande d’exploitation acceptable.",
                recommendationTemplateEn="Audit suppliers, review recurring expenses, and delay low-priority spending until the ratio stabilizes.",
                recommendationTemplateFr="Auditez les fournisseurs, revoyez les dépenses récurrentes et reportez les dépenses non prioritaires jusqu’à stabilisation du ratio.",
                conditions=[
                    DecisionRuleConditionRead(
                        id="cond-charge-high",
                        kpiCode="chargeRatio",
                        operator="GT",
                        threshold=70,
                    )
                ],
                createdAt=utc_iso(),
                updatedAt=utc_iso(),
            ),
        ]
        self._alerts = [
            AlertRead(
                id="ent-sal-010-rule-margin-growth-watch",
                companyId="ent-sal-010",
                ruleId="rule-margin-growth-watch",
                source="Margin and growth watch",
                ruleName="Margin and growth watch",
                title="Margin pressure and revenue slowdown",
                message="Margin remains below the target band while revenue momentum keeps softening.",
                explainabilityText="This alert is triggered because margin is below 20% based on rule 'Margin and growth watch'.",
                recommendation="Reduce controllable costs, review pricing, and focus commercial effort on higher-margin products.",
                severity="warning",
                isActive=True,
                createdAt=utc_iso(),
                triggerCount=2,
                firstTriggeredAt="2026-03-12T08:30:00.000Z",
                lastTriggeredAt="2026-03-26T07:45:00.000Z",
                resolvedAt=None,
                resolvedByUserId=None,
                triggeredBy=AlertTrigger(
                    kpiCode="margin",
                    kpiLabel="Margin",
                    actualValue=19.7,
                    actualValueLabel="19.7%",
                    threshold=20,
                    thresholdLabel="20.0%",
                    operator="LT",
                    operatorLabel="below",
                    statement="Margin is below 20.0% (current 19.7%).",
                ),
                matchedConditions=[
                    AlertTrigger(
                        kpiCode="margin",
                        kpiLabel="Margin",
                        actualValue=19.7,
                        actualValueLabel="19.7%",
                        threshold=20,
                        thresholdLabel="20.0%",
                        operator="LT",
                        operatorLabel="below",
                        statement="Margin is below 20.0% (current 19.7%).",
                    )
                ],
            ),
            AlertRead(
                id="ent-sal-010-rule-charge-ratio",
                companyId="ent-sal-010",
                ruleId="rule-charge-ratio",
                source="Charges safe band",
                ruleName="Charges safe band",
                title="Charges exceed safe operating band",
                message="Charges absorb an unsustainably high share of revenue in the latest periods.",
                explainabilityText="This alert is triggered because charge ratio is above 70.0% based on rule 'Charges safe band'.",
                recommendation="Audit suppliers, review recurring expenses, and delay non-priority spending.",
                severity="critical",
                isActive=True,
                createdAt=utc_iso(),
                triggerCount=3,
                firstTriggeredAt="2026-03-08T11:00:00.000Z",
                lastTriggeredAt="2026-03-26T07:50:00.000Z",
                resolvedAt=None,
                resolvedByUserId=None,
                triggeredBy=AlertTrigger(
                    kpiCode="chargeRatio",
                    kpiLabel="Charge ratio",
                    actualValue=80.3,
                    actualValueLabel="80.3%",
                    threshold=70,
                    thresholdLabel="70.0%",
                    operator="GT",
                    operatorLabel="above",
                    statement="Charge ratio is above 70.0% (current 80.3%).",
                ),
                matchedConditions=[
                    AlertTrigger(
                        kpiCode="chargeRatio",
                        kpiLabel="Charge ratio",
                        actualValue=80.3,
                        actualValueLabel="80.3%",
                        threshold=70,
                        thresholdLabel="70.0%",
                        operator="GT",
                        operatorLabel="above",
                        statement="Charge ratio is above 70.0% (current 80.3%).",
                    )
                ],
            ),
        ]
        self._alert_history = [
            AlertHistoryRead(
                id=f"ah-{alert.id}",
                alertId=alert.id,
                companyId=alert.companyId,
                ruleId=alert.ruleId,
                ruleName=alert.ruleName,
                eventType="TRIGGERED",
                severity=alert.severity,
                title=alert.title,
                message=alert.message,
                recommendation=alert.recommendation,
                alertStatus="ACTIVE",
                occurredAt=alert.createdAt,
                actedByUserId=None,
                actedByUserName=None,
                eventSource="RULE_ENGINE",
                evaluationWindow="rolling-6-months",
                contextBucket=(alert.lastTriggeredAt or alert.createdAt)[:7],
                lifecycleNote="Rule engine evaluated persisted KPI signals and generated this alert.",
                triggeredBy=alert.triggeredBy,
                matchedConditions=alert.matchedConditions,
            )
            for alert in self._alerts
        ]
        self._audit_logs = [
            AuditLogRead(
                id="audit-dashboard-open",
                enterpriseId="ent-sal-010",
                userId="pme-user-101",
                actionType="DASHBOARD_VIEW",
                status="SUCCESS",
                description="Executive dashboard opened.",
                occurredAt=utc_iso(),
            ),
            AuditLogRead(
                id="audit-import-confirmed",
                enterpriseId="ent-sal-010",
                userId="ent-admin-010",
                actionType="IMPORT_CONFIRMED",
                status="SUCCESS",
                description="Monthly import processed and KPI aggregates refreshed.",
                occurredAt=utc_iso(),
            ),
        ]
        self._import_batches: list[ImportBatchRead] = []
        self._report_exports: list[ReportExportRead] = []

    def get_user_by_email(self, email: str) -> RepositoryUser | None:
        normalized_email = email.strip().lower()
        return next((user for user in self._users if user.email == normalized_email), None)

    def get_user_by_id(self, user_id: str) -> RepositoryUser | None:
        return next((user for user in self._users if user.user_id == user_id), None)

    def list_auth_users(self) -> list[RepositoryUser]:
        return list(self._users)

    def update_user_last_login(self, user_id: str) -> None:
        for index, user in enumerate(self._users):
            if user.user_id != user_id:
                continue

            self._users[index] = RepositoryUser(
                **{
                    **user.__dict__,
                    "last_login_at": utc_iso(),
                }
            )
            return

    def update_current_user_profile(
        self, user_id: str, payload: CurrentUserProfileUpdate
    ) -> RepositoryUser | None:
        for index, user in enumerate(self._users):
            if user.user_id != user_id:
                continue

            updated_user = RepositoryUser(
                **{
                    **user.__dict__,
                    "full_name": payload.fullName.strip(),
                    "avatar_url": payload.avatarUrl,
                }
            )
            self._users[index] = updated_user
            return updated_user
        return None

    def update_user_password(self, user_id: str, password_hash: str) -> bool:
        for index, user in enumerate(self._users):
            if user.user_id != user_id:
                continue

            self._users[index] = RepositoryUser(
                **{
                    **user.__dict__,
                    "password_hash": password_hash,
                }
            )
            return True
        return False

    def list_users(self) -> list[UserRead]:
        return [self._to_user_read(user) for user in self._users]

    def create_user(self, payload: UserUpsert) -> UserRead:
        repository_user = RepositoryUser(
            user_id=f"usr-{uuid4().hex[:10]}",
            enterprise_id=payload.primaryCompanyId,
            email=payload.email.strip().lower(),
            full_name=payload.fullName,
            role_type=payload.roleType,
            title=payload.title,
            password_hash=hash_password("ChangeMe123!"),
            accessible_company_ids=self._company_ids_for_role(
                payload.roleType, payload.primaryCompanyId
            ),
            permissions=[],
            primary_company_id=payload.primaryCompanyId,
            status=payload.status,
        )
        self._users.append(repository_user)
        return self._to_user_read(repository_user)

    def update_user(self, user_id: str, payload: UserUpsert) -> UserRead | None:
        for index, user in enumerate(self._users):
            if user.user_id != user_id:
                continue

            updated_user = RepositoryUser(
                user_id=user.user_id,
                enterprise_id=payload.primaryCompanyId,
                email=payload.email.strip().lower(),
                full_name=payload.fullName,
                role_type=payload.roleType,
                title=payload.title,
                password_hash=user.password_hash,
                accessible_company_ids=self._company_ids_for_role(
                    payload.roleType, payload.primaryCompanyId
                ),
                permissions=user.permissions,
                primary_company_id=payload.primaryCompanyId,
                status=payload.status,
                last_login_at=user.last_login_at,
            )
            self._users[index] = updated_user
            return self._to_user_read(updated_user)
        return None

    def delete_user(self, user_id: str) -> bool:
        initial_count = len(self._users)
        self._users = [user for user in self._users if user.user_id != user_id]
        return len(self._users) != initial_count

    def list_companies(self) -> list[CompanyRead]:
        return [CompanyRead(**apply_company_profile_overrides(company.model_dump())) for company in self._companies]

    def get_company(self, company_id: str) -> CompanyRead | None:
        company = next((company for company in self._companies if company.id == company_id), None)
        if company is None:
            return None
        return CompanyRead(**apply_company_profile_overrides(company.model_dump()))

    def list_kpi_definitions(self, company_id: str) -> list[KpiDefinitionRead]:
        return [
            definition
            for definition in self._kpi_definitions
            if isinstance(definition, KpiDefinitionRead) and definition.companyId == company_id
        ]

    def create_kpi_definition(self, payload: KpiDefinitionUpsert) -> KpiDefinitionRead:
        definition = KpiDefinitionRead(
            id=f"kpi-{uuid4().hex[:10]}",
            createdAt=utc_iso(),
            updatedAt=utc_iso(),
            **payload.model_dump(),
        )
        self._kpi_definitions.insert(0, definition)
        return definition

    def update_kpi_definition(
        self, kpi_id: str, payload: KpiDefinitionUpsert
    ) -> KpiDefinitionRead | None:
        for index, definition in enumerate(self._kpi_definitions):
            if not isinstance(definition, KpiDefinitionRead):
                continue
            if definition.id != kpi_id:
                continue

            updated_definition = definition.model_copy(
                update={
                    **payload.model_dump(),
                    "updatedAt": utc_iso(),
                }
            )
            self._kpi_definitions[index] = updated_definition
            return updated_definition
        return None

    def delete_kpi_definition(self, kpi_id: str, company_id: str) -> bool:
        initial_count = len(self._kpi_definitions)
        self._kpi_definitions = [
            definition
            for definition in self._kpi_definitions
            if not (
                isinstance(definition, KpiDefinitionRead)
                and definition.id == kpi_id
                and definition.companyId == company_id
            )
        ]
        return len(self._kpi_definitions) != initial_count

    def get_dashboard_trend(self, company_id: str) -> list[DashboardTrendPoint]:
        return list(self._trend_by_company.get(company_id, []))

    def list_top_products(self, company_id: str, limit: int = 3) -> list[ReportBreakdownItem]:
        return list(self._report_breakdowns.get(company_id, {}).get("products", []))[:limit]

    def list_top_clients(self, company_id: str, limit: int = 3) -> list[ReportBreakdownItem]:
        return list(self._report_breakdowns.get(company_id, {}).get("clients", []))[:limit]

    def list_rules(self, company_id: str | None = None) -> list[DecisionRuleRead]:
        seeded_rules = [
            definition
            for definition in self._kpi_definitions
            if isinstance(definition, DecisionRuleRead)
        ]
        return [
            rule
            for rule in [*seeded_rules, *self._rules]
            if rule.companyId is None or company_id is None or rule.companyId == company_id
        ]

    def create_rule(self, payload: DecisionRuleCreate) -> DecisionRuleRead:
        new_rule = DecisionRuleRead(
            id=f"rule-{uuid4().hex[:10]}",
            createdAt=utc_iso(),
            updatedAt=utc_iso(),
            **payload.model_dump(),
        )
        self._rules.append(new_rule)
        return new_rule

    def update_rule(self, rule_id: str, payload: DecisionRuleCreate) -> DecisionRuleRead | None:
        for index, rule in enumerate(self._rules):
            if rule.id != rule_id:
                continue

            updated_rule = rule.model_copy(
                update={
                    **payload.model_dump(),
                    "updatedAt": utc_iso(),
                }
            )
            self._rules[index] = updated_rule
            return updated_rule
        return None

    def delete_rule(self, rule_id: str) -> bool:
        initial_count = len(self._rules)
        self._rules = [rule for rule in self._rules if rule.id != rule_id]
        return len(self._rules) != initial_count

    def list_alerts(self, company_id: str | None = None) -> list[AlertRead]:
        if company_id is None:
            return list(self._alerts)
        return [alert for alert in self._alerts if alert.companyId == company_id]

    def resolve_alert(self, alert_id: str, resolved_by_user_id: str | None = None) -> bool:
        for index, alert in enumerate(self._alerts):
            if alert.id != alert_id:
                continue

            resolved_at = utc_iso()
            self._alerts[index] = alert.model_copy(
                update={
                    "isActive": False,
                    "resolvedAt": resolved_at,
                    "resolvedByUserId": resolved_by_user_id,
                }
            )
            self._alert_history.insert(
                0,
                AlertHistoryRead(
                    id=f"ah-{uuid4().hex[:12]}",
                    alertId=alert.id,
                    companyId=alert.companyId,
                    ruleId=alert.ruleId,
                    ruleName=alert.ruleName,
                    eventType="RESOLVED",
                    severity=alert.severity,
                    title=alert.title,
                    message=alert.message,
                    recommendation=alert.recommendation,
                    alertStatus="RESOLVED",
                    occurredAt=utc_iso(),
                    actedByUserId=resolved_by_user_id,
                    actedByUserName=self.get_user_by_id(resolved_by_user_id).full_name
                    if resolved_by_user_id and self.get_user_by_id(resolved_by_user_id)
                    else None,
                    eventSource="USER_ACTION",
                    evaluationWindow="rolling-6-months",
                    contextBucket=(alert.lastTriggeredAt or alert.createdAt)[:7],
                    lifecycleNote="Alert resolved manually from the alerts workspace.",
                    triggeredBy=alert.triggeredBy,
                    matchedConditions=alert.matchedConditions,
                ),
            )
            return True
        return False

    def list_alert_history(
        self, company_id: str, alert_id: str | None = None
    ) -> list[AlertHistoryRead]:
        history = [entry for entry in self._alert_history if entry.companyId == company_id]
        if alert_id:
            history = [entry for entry in history if entry.alertId == alert_id]
        return history

    def list_audit_logs(self, company_id: str | None = None) -> list[AuditLogRead]:
        if company_id is None:
            return list(self._audit_logs)
        return [entry for entry in self._audit_logs if entry.enterpriseId == company_id]

    def create_audit_log(self, payload: AuditLogCreate) -> AuditLogRead:
        entry = AuditLogRead(
            id=f"audit-{uuid4().hex[:12]}",
            enterpriseId=payload.enterpriseId,
            userId=payload.userId,
            actionType=payload.actionType,
            status=payload.status,
            description=payload.description,
            occurredAt=utc_iso(),
        )
        self._audit_logs.insert(0, entry)
        return entry

    def record_import_batch(
        self,
        payload: ProcessImportRequest,
        persisted_rows: int,
        normalized_rows: list[dict[str, object]],
        trend_points: list[DashboardTrendPoint],
        status: str,
    ) -> ImportBatchRead:
        batch = ImportBatchRead(
            id=f"imp-{uuid4().hex[:12]}",
            companyId=payload.company_id,
            uploadedBy=payload.user_id,
            fileName=payload.file_name,
            aggregationLevel=payload.aggregation_level,
            persistedRows=persisted_rows,
            status=status,
            createdAt=utc_iso(),
        )
        self._import_batches.insert(0, batch)
        if trend_points:
            self._trend_by_company[payload.company_id] = trend_points
        self.create_audit_log(
            AuditLogCreate(
                enterpriseId=payload.company_id,
                userId=payload.user_id,
                actionType="IMPORT_CONFIRMED",
                description=f"Import {payload.file_name} persisted with {persisted_rows} normalized rows.",
            )
        )
        return batch

    def list_import_batches(self, company_id: str) -> list[ImportBatchRead]:
        return [batch for batch in self._import_batches if batch.companyId == company_id]

    def record_report_export(
        self,
        company_id: str,
        requested_by: str,
        format_name: str,
        file_name: str,
        status: str,
    ) -> ReportExportRead:
        export = ReportExportRead(
            id=f"rep-{uuid4().hex[:12]}",
            companyId=company_id,
            requestedBy=requested_by,
            format="pdf" if format_name == "pdf" else "excel",
            fileName=file_name,
            status=status,
            generatedAt=utc_iso(),
        )
        self._report_exports.insert(0, export)
        return export

    def list_report_exports(self, company_id: str) -> list[ReportExportRead]:
        return [export for export in self._report_exports if export.companyId == company_id]

    def get_report_export(self, export_id: str) -> ReportExportRead | None:
        return next((export for export in self._report_exports if export.id == export_id), None)

    def _company_ids_for_role(self, role_type: str, primary_company_id: str) -> list[str]:
        if role_type == "SAL_ADMIN":
            return [company.id for company in self._companies]
        return [primary_company_id]

    def _to_user_read(self, user: RepositoryUser) -> UserRead:
        return UserRead(
            id=user.user_id,
            fullName=user.full_name,
            email=user.email,
            title=user.title,
            roleType=user.role_type,
            primaryCompanyId=user.primary_company_id,
            companyIds=user.accessible_company_ids,
            status=user.status,
            lastLoginAt=user.last_login_at,
        )
