from __future__ import annotations

from typing import Any


ON_ING_COMPANY_ID = "ent-sal-010"
ON_ING_PROFILE_CODE = "ON_ING"
ON_ING_TECHNICAL_POLES: tuple[str, ...] = (
    "ELEC",
    "CVC",
    "Fluides",
    "Plomberie",
    "Sécurité incendie",
    "BIM",
)
ON_ING_NAV_LABELS: tuple[str, ...] = (
    "Vue Direction",
    "Chiffre d’affaires",
    "Affaires / Projets",
    "Rentabilité",
    "Clients",
    "Prévisionnel",
    "Comptabilité",
    "Qualité des données",
    "Alertes & Recommandations",
)


def is_on_ing_company(company_id: str | None) -> bool:
    return (company_id or "").strip() == ON_ING_COMPANY_ID


def get_on_ing_company_profile() -> dict[str, Any]:
    return {
        "profileCode": ON_ING_PROFILE_CODE,
        "companyName": "ON INGENIERIE",
        "shortName": "ON ING",
        "subtitle": "Pilotage intelligent pour bureau d’études techniques",
        "sector": "Bureau d’études techniques / Ingénierie du bâtiment",
        "country": "Tunisie",
        "mainMarket": "France",
        "currency": "EUR",
        "headquarters": "Tunis",
        "monthlyTarget": 285000,
        "health": "healthy",
        "technicalPoles": list(ON_ING_TECHNICAL_POLES),
        "navigationLabels": list(ON_ING_NAV_LABELS),
    }


def apply_company_profile_overrides(base_payload: dict[str, Any]) -> dict[str, Any]:
    if not is_on_ing_company(str(base_payload.get("id") or "")):
        return base_payload

    profile = get_on_ing_company_profile()
    return {
        **base_payload,
        "name": profile["companyName"],
        "sector": profile["sector"],
        "health": profile["health"],
        "country": profile["country"],
        "currency": profile["currency"],
        "monthlyTarget": profile["monthlyTarget"],
        "headquarters": profile["headquarters"],
        "shortName": profile["shortName"],
        "profileCode": profile["profileCode"],
        "mainMarket": profile["mainMarket"],
        "subtitle": profile["subtitle"],
        "technicalPoles": profile["technicalPoles"],
        "navigationLabels": profile["navigationLabels"],
    }


def resolve_company_currency(company_id: str | None, fallback: str | None = None) -> str:
    if is_on_ing_company(company_id):
        return "EUR"
    return (fallback or "EUR").strip() or "EUR"
