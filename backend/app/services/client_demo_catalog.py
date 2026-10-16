from __future__ import annotations

from dataclasses import dataclass

from app.services.on_ing_profile import is_on_ing_company


EXPECTED_CLIENT_SOURCES: dict[str, str] = {
    "ca_projects": "CA Projets",
    "affair_tracking": "Toutes Affaires",
    "pnl": "Reporting PnL",
    "accounting": "Export Comptable",
}


@dataclass(frozen=True)
class ClientDemoRuleTemplate:
    id: str
    section_id: str
    name: str
    severity: str
    logic: str
    action_type: str
    title_en: str
    title_fr: str
    recommendation_en: str
    recommendation_fr: str
    conditions: tuple[dict[str, object], ...]


DEFAULT_CLIENT_DEMO_RULE_TEMPLATES: tuple[ClientDemoRuleTemplate, ...] = (
    ClientDemoRuleTemplate(
        id="rule-client-finance-ca-forecast-gap-negative",
        section_id="reporting-pnl",
        name="Monthly revenue below forecast",
        severity="warning",
        logic="AND",
        action_type="alert",
        title_en="Revenue target not achieved",
        title_fr="Objectif CA non atteint",
        recommendation_en="Review the monthly delivery plan and secure short-cycle revenue opportunities.",
        recommendation_fr="Revoyez le plan de production mensuel et sécurisez des opportunités de CA à cycle court.",
        conditions=(
            {
                "id": "cond-finance-actual-vs-forecast",
                "kpiCode": "latest_month_revenue_delta_vs_forecast",
                "operator": "LT",
                "threshold": 0,
            },
        ),
    ),
    ClientDemoRuleTemplate(
        id="rule-client-finance-negative-growth",
        section_id="reporting-pnl",
        name="Negative monthly growth",
        severity="warning",
        logic="AND",
        action_type="alert",
        title_en="Business slowdown detected",
        title_fr="Baisse d'activité",
        recommendation_en="Investigate the commercial pipeline and protect the strongest recurring revenue streams.",
        recommendation_fr="Analysez le pipe commercial et protégez les flux récurrents les plus solides.",
        conditions=(
            {
                "id": "cond-finance-negative-growth",
                "kpiCode": "latest_month_growth_pct",
                "operator": "LT",
                "threshold": 0,
            },
        ),
    ),
    ClientDemoRuleTemplate(
        id="rule-client-finance-yoy-delay",
        section_id="dashboard-general",
        name="Cumulative revenue lags previous year",
        severity="warning",
        logic="AND",
        action_type="alert",
        title_en="Lagging behind the previous year",
        title_fr="Retard par rapport à l'année précédente",
        recommendation_en="Compare the current portfolio against last year and accelerate delayed revenue recognition.",
        recommendation_fr="Comparez le portefeuille actuel à l'année précédente et accélérez la reconnaissance du CA en retard.",
        conditions=(
            {
                "id": "cond-finance-cumulative-yoy",
                "kpiCode": "cumulative_revenue_yoy_growth_pct",
                "operator": "LT",
                "threshold": 0,
            },
        ),
    ),
    ClientDemoRuleTemplate(
        id="rule-client-finance-forecast-gap-20",
        section_id="reporting-pnl",
        name="Forecast gap above 20 percent",
        severity="critical",
        logic="AND",
        action_type="alert",
        title_en="Large gap between forecast and actual",
        title_fr="Écart important entre prévisionnel et réalisé",
        recommendation_en="Reforecast the monthly plan and isolate the projects driving the variance.",
        recommendation_fr="Révisez le prévisionnel mensuel et isolez les projets à l'origine de l'écart.",
        conditions=(
            {
                "id": "cond-finance-forecast-gap-20",
                "kpiCode": "forecast_gap_pct",
                "operator": "GT",
                "threshold": 20,
            },
        ),
    ),
    ClientDemoRuleTemplate(
        id="rule-client-project-overdue",
        section_id="suivi-affaires",
        name="Overdue projects",
        severity="critical",
        logic="AND",
        action_type="alert",
        title_en="Project overdue",
        title_fr="Projet en retard",
        recommendation_en="Escalate delayed projects and review delivery blockers with the responsible managers.",
        recommendation_fr="Escaladez les projets en retard et passez en revue les blocages avec les responsables.",
        conditions=(
            {
                "id": "cond-project-overdue",
                "kpiCode": "overdue_projects_count",
                "operator": "GT",
                "threshold": 0,
            },
        ),
    ),
    ClientDemoRuleTemplate(
        id="rule-client-project-low-margin",
        section_id="suivi-affaires",
        name="Low margin projects",
        severity="warning",
        logic="AND",
        action_type="alert",
        title_en="Low margin detected",
        title_fr="Marge faible",
        recommendation_en="Review pricing and purchasing assumptions on the affected projects.",
        recommendation_fr="Revoyez le pricing et les hypothèses d'achats sur les projets concernés.",
        conditions=(
            {
                "id": "cond-project-low-margin",
                "kpiCode": "low_margin_project_count",
                "operator": "GT",
                "threshold": 0,
            },
        ),
    ),
    ClientDemoRuleTemplate(
        id="rule-client-project-loss-risk",
        section_id="suivi-affaires",
        name="Purchases exceed revenue",
        severity="critical",
        logic="AND",
        action_type="alert",
        title_en="Risk of loss detected",
        title_fr="Risque de perte",
        recommendation_en="Check project cost allocations immediately and freeze additional purchases until reviewed.",
        recommendation_fr="Contrôlez immédiatement les affectations de coûts et geler les achats supplémentaires jusqu'à revue.",
        conditions=(
            {
                "id": "cond-project-loss-risk",
                "kpiCode": "loss_risk_project_count",
                "operator": "GT",
                "threshold": 0,
            },
        ),
    ),
    ClientDemoRuleTemplate(
        id="rule-client-project-missing-owner",
        section_id="suivi-affaires",
        name="Projects without responsible",
        severity="warning",
        logic="AND",
        action_type="alert",
        title_en="Responsible manager missing",
        title_fr="Responsable manquant",
        recommendation_en="Assign a named owner to every active project before the next review cycle.",
        recommendation_fr="Affectez un responsable nominatif à chaque projet actif avant le prochain cycle de revue.",
        conditions=(
            {
                "id": "cond-project-missing-owner",
                "kpiCode": "missing_responsible_count",
                "operator": "GT",
                "threshold": 0,
            },
        ),
    ),
    ClientDemoRuleTemplate(
        id="rule-client-project-missing-end-date",
        section_id="suivi-affaires",
        name="Projects without end date",
        severity="warning",
        logic="AND",
        action_type="alert",
        title_en="Project end date missing",
        title_fr="Date de fin manquante",
        recommendation_en="Complete the project planning data to improve schedule visibility.",
        recommendation_fr="Complétez les dates de fin projet pour améliorer la visibilité planning.",
        conditions=(
            {
                "id": "cond-project-missing-end-date",
                "kpiCode": "missing_end_date_count",
                "operator": "GT",
                "threshold": 0,
            },
        ),
    ),
    ClientDemoRuleTemplate(
        id="rule-client-project-client-concentration",
        section_id="dashboard-general",
        name="Client concentration risk",
        severity="warning",
        logic="AND",
        action_type="alert",
        title_en="High customer dependency",
        title_fr="Dépendance client importante",
        recommendation_en="Diversify the commercial pipeline and protect the margin of the leading account.",
        recommendation_fr="Diversifiez le pipe commercial et protégez la marge du principal client.",
        conditions=(
            {
                "id": "cond-project-client-concentration",
                "kpiCode": "client_concentration_pct",
                "operator": "GT",
                "threshold": 45,
            },
        ),
    ),
    ClientDemoRuleTemplate(
        id="rule-client-accounting-unbalanced",
        section_id="controle-comptable",
        name="Accounting imbalance",
        severity="critical",
        logic="AND",
        action_type="alert",
        title_en="Accounting imbalance",
        title_fr="Déséquilibre comptable",
        recommendation_en="Investigate the journal entries that break debit and credit balance before the demo.",
        recommendation_fr="Vérifiez les écritures qui rompent l'équilibre débit/crédit avant la démonstration.",
        conditions=(
            {
                "id": "cond-accounting-unbalanced",
                "kpiCode": "debit_credit_difference",
                "operator": "GT",
                "threshold": 0,
            },
        ),
    ),
    ClientDemoRuleTemplate(
        id="rule-client-accounting-missing-subaccount",
        section_id="controle-comptable",
        name="Missing client subaccount",
        severity="warning",
        logic="AND",
        action_type="alert",
        title_en="Client or subaccount missing",
        title_fr="Client ou sous-compte manquant",
        recommendation_en="Complete client and subaccount references on the affected invoices.",
        recommendation_fr="Complétez les références client et sous-compte sur les factures concernées.",
        conditions=(
            {
                "id": "cond-accounting-missing-subaccount",
                "kpiCode": "missing_subaccount_count",
                "operator": "GT",
                "threshold": 0,
            },
        ),
    ),
    ClientDemoRuleTemplate(
        id="rule-client-accounting-invalid-amount",
        section_id="controle-comptable",
        name="Invalid invoice amount",
        severity="warning",
        logic="AND",
        action_type="alert",
        title_en="Abnormal amount detected",
        title_fr="Montant anormal",
        recommendation_en="Review invoice lines with missing or zero amounts.",
        recommendation_fr="Contrôlez les lignes de facture dont le montant est vide ou nul.",
        conditions=(
            {
                "id": "cond-accounting-invalid-amount",
                "kpiCode": "invalid_invoice_amount_count",
                "operator": "GT",
                "threshold": 0,
            },
        ),
    ),
    ClientDemoRuleTemplate(
        id="rule-client-accounting-foreign-currency",
        section_id="controle-comptable",
        name="Foreign currency entries",
        severity="info",
        logic="AND",
        action_type="alert",
        title_en="Currency to review",
        title_fr="Devise à vérifier",
        recommendation_en="Validate exchange handling for the entries recorded in a foreign currency.",
        recommendation_fr="Validez le traitement de change pour les écritures saisies dans une devise étrangère.",
        conditions=(
            {
                "id": "cond-accounting-foreign-currency",
                "kpiCode": "foreign_currency_entries_count",
                "operator": "GT",
                "threshold": 0,
            },
        ),
    ),
)

ON_ING_RULE_TEMPLATES: tuple[ClientDemoRuleTemplate, ...] = (
    ClientDemoRuleTemplate(
        id="rule-on-ing-client-dependency",
        section_id="clients",
        name="Dépendance client élevée",
        severity="warning",
        logic="AND",
        action_type="alert",
        title_en="High client dependency",
        title_fr="Dépendance client élevée",
        recommendation_en="Diversify the client portfolio and reduce commercial dependency.",
        recommendation_fr="Diversifier le portefeuille clients et réduire la dépendance commerciale.",
        conditions=(
            {
                "id": "cond-on-ing-client-concentration",
                "kpiCode": "client_concentration_pct",
                "operator": "GT",
                "threshold": 40,
            },
        ),
    ),
    ClientDemoRuleTemplate(
        id="rule-on-ing-forecast-delay",
        section_id="previsionnel",
        name="Retard par rapport au prévisionnel",
        severity="warning",
        logic="AND",
        action_type="alert",
        title_en="Forecast delay versus plan",
        title_fr="Retard par rapport au prévisionnel",
        recommendation_en="Review active projects, accelerate billing, and reinforce commercial follow-up.",
        recommendation_fr="Analyser les affaires en cours, accélérer la facturation et renforcer les relances commerciales.",
        conditions=(
            {
                "id": "cond-on-ing-forecast-achievement",
                "kpiCode": "forecast_achievement_pct",
                "operator": "LT",
                "threshold": 80,
            },
        ),
    ),
    ClientDemoRuleTemplate(
        id="rule-on-ing-low-margin-projects",
        section_id="rentabilite",
        name="Projets à faible marge",
        severity="warning",
        logic="AND",
        action_type="alert",
        title_en="Low margin projects",
        title_fr="Projets à faible marge",
        recommendation_en="Control purchases, worked time, and pricing on low-margin projects.",
        recommendation_fr="Contrôler les achats, le temps passé et la tarification des projets à faible marge.",
        conditions=(
            {
                "id": "cond-on-ing-low-margin-projects",
                "kpiCode": "low_margin_project_count",
                "operator": "GT",
                "threshold": 0,
            },
        ),
    ),
    ClientDemoRuleTemplate(
        id="rule-on-ing-missing-resource",
        section_id="affaires-projets",
        name="Ressource projet manquante",
        severity="warning",
        logic="AND",
        action_type="alert",
        title_en="Missing project resource",
        title_fr="Ressource projet manquante",
        recommendation_en="Assign a resource or mission owner to unassigned projects.",
        recommendation_fr="Affecter une ressource ou un responsable mission aux affaires non affectées.",
        conditions=(
            {
                "id": "cond-on-ing-missing-resource",
                "kpiCode": "missing_resource_count",
                "operator": "GT",
                "threshold": 0,
            },
        ),
    ),
    ClientDemoRuleTemplate(
        id="rule-on-ing-remaining-to-invoice",
        section_id="previsionnel",
        name="Reste à facturer",
        severity="info",
        logic="AND",
        action_type="alert",
        title_en="Remaining revenue to invoice",
        title_fr="Reste à facturer",
        recommendation_en="Review project progress and schedule the remaining billing.",
        recommendation_fr="Vérifier l’avancement des projets et planifier la facturation restante.",
        conditions=(
            {
                "id": "cond-on-ing-remaining-to-invoice",
                "kpiCode": "remaining_to_invoice_amount",
                "operator": "GT",
                "threshold": 0,
            },
        ),
    ),
    ClientDemoRuleTemplate(
        id="rule-on-ing-accounting-imbalance",
        section_id="comptabilite",
        name="Contrôle comptable",
        severity="critical",
        logic="AND",
        action_type="alert",
        title_en="Accounting control",
        title_fr="Contrôle comptable",
        recommendation_en="Review accounting entries, vouchers, and debit/credit amounts.",
        recommendation_fr="Vérifier les écritures comptables, les pièces et les montants débit/crédit.",
        conditions=(
            {
                "id": "cond-on-ing-accounting-imbalance",
                "kpiCode": "debit_credit_difference",
                "operator": "GT",
                "threshold": 0,
            },
        ),
    ),
    ClientDemoRuleTemplate(
        id="rule-on-ing-missing-subaccount",
        section_id="comptabilite",
        name="Contrôle comptable",
        severity="warning",
        logic="AND",
        action_type="alert",
        title_en="Accounting control",
        title_fr="Contrôle comptable",
        recommendation_en="Complete the missing subaccounts to secure accounting analysis.",
        recommendation_fr="Compléter les sous-comptes pour fiabiliser l’analyse comptable.",
        conditions=(
            {
                "id": "cond-on-ing-missing-subaccount",
                "kpiCode": "missing_subaccount_count",
                "operator": "GT",
                "threshold": 0,
            },
        ),
    ),
    ClientDemoRuleTemplate(
        id="rule-on-ing-data-quality",
        section_id="qualite-donnees",
        name="Qualité des données",
        severity="warning",
        logic="AND",
        action_type="alert",
        title_en="Data quality issue",
        title_fr="Qualité des données",
        recommendation_en="Clean missing fields across resources, poles, margins, dates, and billing data.",
        recommendation_fr="Nettoyer les champs manquants: ressource, pôle, marge, dates, facturation.",
        conditions=(
            {
                "id": "cond-on-ing-data-quality",
                "kpiCode": "data_quality_score",
                "operator": "LT",
                "threshold": 90,
            },
        ),
    ),
)


def get_client_demo_rule_templates(company_id: str | None = None) -> tuple[ClientDemoRuleTemplate, ...]:
    return ON_ING_RULE_TEMPLATES if is_on_ing_company(company_id) else DEFAULT_CLIENT_DEMO_RULE_TEMPLATES


def find_rule_section(rule_id: str | None) -> str | None:
    if not rule_id:
        return None

    for template in (*DEFAULT_CLIENT_DEMO_RULE_TEMPLATES, *ON_ING_RULE_TEMPLATES):
        if template.id == rule_id:
            return template.section_id
    return None
