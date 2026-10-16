from __future__ import annotations

from app.core.security import hash_password
from app.repositories.platform_repository import RepositoryUser
from app.schemas.platform import CompanyRead, DecisionRuleConditionRead, DecisionRuleRead, KpiDefinitionRead


PLASTIC_SFAX_COMPANY_ID = "ent-plastic-sfax-001"


def get_plastic_sfax_company() -> CompanyRead:
    return CompanyRead(
        id=PLASTIC_SFAX_COMPANY_ID,
        name="Plastic Sfax",
        sector="Transformation plastique / extrusion / impression / packaging B2B",
        plan="Growth",
        health="healthy",
        country="Tunisia",
        currency="TND",
        monthlyTarget=420000,
        headquarters="Sfax",
        lastSyncAt="2026-05-10T00:00:00.000Z",
    )


def get_plastic_sfax_users() -> list[RepositoryUser]:
    return [
        RepositoryUser(
            user_id="sal-admin-001",
            enterprise_id=PLASTIC_SFAX_COMPANY_ID,
            email="admin@sal.local",
            full_name="Administrateur SAL",
            role_type="SAL_ADMIN",
            title="Administration plateforme",
            password_hash=hash_password("Admin123!"),
            accessible_company_ids=[PLASTIC_SFAX_COMPANY_ID],
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
            primary_company_id=PLASTIC_SFAX_COMPANY_ID,
            status="active",
            created_at="2026-05-10T00:00:00.000Z",
        ),
        RepositoryUser(
            user_id="plastic-admin-001",
            enterprise_id=PLASTIC_SFAX_COMPANY_ID,
            email="entadmin@sal.local",
            full_name="Administration Plastic Sfax",
            role_type="ENT_ADMIN",
            title="Administration operationnelle",
            password_hash=hash_password("Admin123!"),
            accessible_company_ids=[PLASTIC_SFAX_COMPANY_ID],
            permissions=[
                "dashboard:view",
                "import:create",
                "decision:view",
                "audit:view",
                "report:export",
                "users:manage",
                "kpi:manage",
            ],
            primary_company_id=PLASTIC_SFAX_COMPANY_ID,
            status="active",
            created_at="2026-05-10T00:00:00.000Z",
        ),
        RepositoryUser(
            user_id="plastic-direction-001",
            enterprise_id=PLASTIC_SFAX_COMPANY_ID,
            email="user@sal.local",
            full_name="Direction Plastic Sfax",
            role_type="PME_USER",
            title="Direction generale",
            password_hash=hash_password("User123!"),
            accessible_company_ids=[PLASTIC_SFAX_COMPANY_ID],
            permissions=["dashboard:view", "decision:view", "audit:view", "report:export"],
            primary_company_id=PLASTIC_SFAX_COMPANY_ID,
            status="active",
            created_at="2026-05-10T00:00:00.000Z",
        ),
    ]


def get_plastic_sfax_kpi_definitions() -> list[KpiDefinitionRead]:
    company_id = PLASTIC_SFAX_COMPANY_ID
    return [
        KpiDefinitionRead(
            id="kpi-plastic-revenue",
            companyId=company_id,
            name="Chiffre d'affaires total",
            category="Commercial",
            formula="SUM(revenue_amount)",
            threshold=350000,
            unit="currency",
            direction="up",
            description="Suit le chiffre d'affaires consolide des commandes et facturations importees.",
            sourceKey="total_revenue",
            createdAt="2026-05-10T00:00:00.000Z",
            updatedAt="2026-05-10T00:00:00.000Z",
        ),
        KpiDefinitionRead(
            id="kpi-plastic-margin-rate",
            companyId=company_id,
            name="Taux de marge",
            category="Rentabilite",
            formula="(revenue_amount - cost_amount) / revenue_amount",
            threshold=18,
            unit="percent",
            direction="up",
            description="Mesure la rentabilite globale sur la periode visible.",
            sourceKey="margin_rate_pct",
            createdAt="2026-05-10T00:00:00.000Z",
            updatedAt="2026-05-10T00:00:00.000Z",
        ),
        KpiDefinitionRead(
            id="kpi-plastic-delivery-otd",
            companyId=company_id,
            name="Taux de livraison a temps",
            category="Delais",
            formula="on_time_deliveries / total_deliveries",
            threshold=92,
            unit="percent",
            direction="up",
            description="Mesure la capacite a respecter les delais clients.",
            sourceKey="on_time_delivery_rate_pct",
            createdAt="2026-05-10T00:00:00.000Z",
            updatedAt="2026-05-10T00:00:00.000Z",
        ),
        KpiDefinitionRead(
            id="kpi-plastic-material-cost",
            companyId=company_id,
            name="Cout matiere premiere",
            category="Matiere",
            formula="SUM(purchase_amount)",
            threshold=210000,
            unit="currency",
            direction="down",
            description="Suit le cout matiere importe depuis les achats, consommations ou couts.",
            sourceKey="raw_material_cost_amount",
            createdAt="2026-05-10T00:00:00.000Z",
            updatedAt="2026-05-10T00:00:00.000Z",
        ),
        KpiDefinitionRead(
            id="kpi-plastic-complaints",
            companyId=company_id,
            name="Taux de reclamation",
            category="Qualite",
            formula="complaints / orders",
            threshold=3,
            unit="percent",
            direction="down",
            description="Surveille les non-conformites et reclamations clients.",
            sourceKey="complaint_rate_pct",
            createdAt="2026-05-10T00:00:00.000Z",
            updatedAt="2026-05-10T00:00:00.000Z",
        ),
    ]


def get_plastic_sfax_rules() -> list[DecisionRuleRead]:
    company_id = PLASTIC_SFAX_COMPANY_ID
    base_time = "2026-05-10T00:00:00.000Z"
    return [
        DecisionRuleRead(
            id="rule-plastic-late-orders",
            companyId=company_id,
            name="Commandes en retard",
            priority=95,
            severity="critical",
            logic="AND",
            actionType="alert",
            enabled=True,
            titleEn="Late orders detected",
            titleFr="Commandes en retard detectees",
            explanationTemplateEn="One or more customer orders are now beyond the planned delivery date.",
            explanationTemplateFr="Une ou plusieurs commandes clients depassent la date de livraison prevue.",
            recommendationTemplateEn="Prioritize delayed orders, align production planning, and inform key customers.",
            recommendationTemplateFr="Priorisez les commandes en retard, alignez le planning de production et informez les clients cles.",
            conditions=[
                DecisionRuleConditionRead(
                    id="cond-plastic-late-orders",
                    kpiCode="late_order_count",
                    operator="GT",
                    threshold=0,
                )
            ],
            createdAt=base_time,
            updatedAt=base_time,
        ),
        DecisionRuleRead(
            id="rule-plastic-low-margin",
            companyId=company_id,
            name="Marge sous seuil",
            priority=92,
            severity="warning",
            logic="AND",
            actionType="alert",
            enabled=True,
            titleEn="Margin below target",
            titleFr="Marge sous le seuil cible",
            explanationTemplateEn="The overall margin rate is below the acceptable target for Plastic Sfax.",
            explanationTemplateFr="Le taux de marge global est inferieur au seuil cible pour Plastic Sfax.",
            recommendationTemplateEn="Review pricing, material cost, and low-profit orders before the next cycle.",
            recommendationTemplateFr="Revoyez le pricing, le cout matiere et les commandes peu rentables avant le prochain cycle.",
            conditions=[
                DecisionRuleConditionRead(
                    id="cond-plastic-low-margin",
                    kpiCode="margin_rate_pct",
                    operator="LT",
                    threshold=18,
                )
            ],
            createdAt=base_time,
            updatedAt=base_time,
        ),
        DecisionRuleRead(
            id="rule-plastic-inactive-clients",
            companyId=company_id,
            name="Clients inactifs",
            priority=80,
            severity="warning",
            logic="AND",
            actionType="recommendation",
            enabled=True,
            titleEn="Inactive clients detected",
            titleFr="Clients inactifs detectes",
            explanationTemplateEn="Some customers have not placed recent orders and require commercial follow-up.",
            explanationTemplateFr="Certains clients n'ont pas commande recemment et demandent une relance commerciale.",
            recommendationTemplateEn="Launch a targeted reactivation campaign on inactive accounts.",
            recommendationTemplateFr="Lancez une campagne de reactivation ciblee sur les comptes inactifs.",
            conditions=[
                DecisionRuleConditionRead(
                    id="cond-plastic-inactive-clients",
                    kpiCode="inactive_client_count",
                    operator="GT",
                    threshold=0,
                )
            ],
            createdAt=base_time,
            updatedAt=base_time,
        ),
        DecisionRuleRead(
            id="rule-plastic-material-cost",
            companyId=company_id,
            name="Hausse cout matiere",
            priority=88,
            severity="warning",
            logic="AND",
            actionType="alert",
            enabled=True,
            titleEn="Material cost pressure",
            titleFr="Pression sur le cout matiere",
            explanationTemplateEn="Raw material cost exceeds the expected control threshold.",
            explanationTemplateFr="Le cout matiere depasse le seuil de controle attendu.",
            recommendationTemplateEn="Review suppliers, purchasing contracts, and pricing updates.",
            recommendationTemplateFr="Revoyez les fournisseurs, les contrats d'achat et les mises a jour tarifaires.",
            conditions=[
                DecisionRuleConditionRead(
                    id="cond-plastic-material-cost",
                    kpiCode="raw_material_cost_amount",
                    operator="GT",
                    threshold=210000,
                )
            ],
            createdAt=base_time,
            updatedAt=base_time,
        ),
        DecisionRuleRead(
            id="rule-plastic-complaints",
            companyId=company_id,
            name="Taux de reclamation eleve",
            priority=90,
            severity="critical",
            logic="AND",
            actionType="alert",
            enabled=True,
            titleEn="Complaint rate is high",
            titleFr="Taux de reclamation eleve",
            explanationTemplateEn="Customer complaints are above the accepted operating threshold.",
            explanationTemplateFr="Les reclamations clients sont au-dessus du seuil d'exploitation accepte.",
            recommendationTemplateEn="Escalate quality review, root-cause analysis, and corrective action tracking.",
            recommendationTemplateFr="Escaladez la revue qualite, l'analyse des causes racines et le suivi des actions correctives.",
            conditions=[
                DecisionRuleConditionRead(
                    id="cond-plastic-complaints",
                    kpiCode="complaint_rate_pct",
                    operator="GT",
                    threshold=3,
                )
            ],
            createdAt=base_time,
            updatedAt=base_time,
        ),
        DecisionRuleRead(
            id="rule-plastic-top-client",
            companyId=company_id,
            name="Client strategique",
            priority=70,
            severity="info",
            logic="AND",
            actionType="recommendation",
            enabled=True,
            titleEn="Strategic client concentration",
            titleFr="Concentration client strategique",
            explanationTemplateEn="A major client contributes a large share of turnover and should be protected.",
            explanationTemplateFr="Un client majeur contribue fortement au chiffre d'affaires et doit etre securise.",
            recommendationTemplateEn="Prepare an account retention and upsell plan for the dominant client.",
            recommendationTemplateFr="Preparez un plan de fidelisation et de developpement pour le client dominant.",
            conditions=[
                DecisionRuleConditionRead(
                    id="cond-plastic-top-client",
                    kpiCode="top_client_share_pct",
                    operator="GT",
                    threshold=35,
                )
            ],
            createdAt=base_time,
            updatedAt=base_time,
        ),
    ]
