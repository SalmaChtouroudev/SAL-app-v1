from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
import unicodedata

import pandas as pd

from app.schemas.imports import ImportMapping


MONTH_TOKENS: dict[str, int] = {
    "jan": 1,
    "january": 1,
    "janvier": 1,
    "fev": 2,
    "fevr": 2,
    "feb": 2,
    "february": 2,
    "fevrier": 2,
    "fvrier": 2,
    "mar": 3,
    "march": 3,
    "mars": 3,
    "apr": 4,
    "april": 4,
    "avr": 4,
    "avril": 4,
    "may": 5,
    "mai": 5,
    "jun": 6,
    "june": 6,
    "juin": 6,
    "jul": 7,
    "july": 7,
    "juil": 7,
    "juillet": 7,
    "aug": 8,
    "august": 8,
    "aout": 8,
    "ao": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "septembre": 9,
    "oct": 10,
    "october": 10,
    "octobre": 10,
    "nov": 11,
    "november": 11,
    "novembre": 11,
    "dec": 12,
    "december": 12,
    "decembre": 12,
    "dcembre": 12,
}


ALIASES: dict[str, tuple[str, ...]] = {
    "date": ("date", "dateoperation", "datepiece", "dateecriture", "periode"),
    "month": ("mois", "month", "period", "periode"),
    "year": ("annee", "year", "exercice"),
    "project_code": (
        "codeaffaire",
        "numaffaire",
        "numeroaffaire",
        "codeprojet",
        "refprojet",
        "reference",
        "referenceaffaire",
        "refaffaire",
    ),
    "project_name": ("affaire", "projet", "libelleaffaire", "mission", "nomprojet"),
    "client": ("client", "customer", "tiers", "compteclient"),
    "responsible": ("responsable", "responsablemission", "chefeprojet", "chefdeprojet", "manager"),
    "resource": ("ressource", "resource", "intervenant", "ingenieur", "consultant", "affectation"),
    "business_pole": ("pole", "businessunit", "service", "departement", "department"),
    "status": ("statut", "status", "etat"),
    "start_date": ("datedebut", "startdate", "debut"),
    "end_date": ("datefin", "enddate", "fin", "echeance"),
    "revenue": ("ca", "chiffredaffaires", "revenue", "sales", "carealise", "realise", "realized"),
    "forecast_revenue": ("caprevisionnel", "caprevisionnel", "previsionnel", "forecast", "budget", "cabuget", "caprev"),
    "remaining_to_invoice": (
        "resteafacturer",
        "restefacturation",
        "remainingtoinvoice",
        "totalapresperiode",
        "caapresperiode",
        "encoursafacturer",
    ),
    "purchase": ("achat", "achats", "purchase", "purchases", "cost", "cout", "charges", "chargedirecte"),
    "margin": ("marge", "margin", "resultat"),
    "margin_rate": ("tauxmarge", "margerate", "margepct", "margepourcentage"),
    "debit": ("debit",),
    "credit": ("credit",),
    "amount": ("montant", "amount", "valeur", "total"),
    "kind": ("nature", "type", "kind", "sens"),
    "invoice_number": ("facture", "numerofacture", "invoice", "piece"),
    "currency": ("devise", "currency"),
    "account_code": ("compte", "account", "generalaccount"),
    "subaccount": ("souscompte", "subaccount", "compteauxiliaire"),
    "label": ("libelle", "label", "description", "designation", "intitule", "indicateur", "indicator", "poste"),
    "category": ("categorie", "category", "segment"),
    "product": ("produit", "product", "offre", "service"),
}

AUTO_TEMPLATE_FILE_NAMES = frozenset(
    {
        "toutesaffairesxlsx",
        "toutesaffairescsv",
        "caprojets2025xlsx",
        "caprojets2025csv",
        "caprojets2026xlsx",
        "caprojets2026csv",
        "reportingpnl2025xlsx",
        "reportingpnl2025csv",
        "reportingpnl2026xlsx",
        "reportingpnl2026csv",
        "exportcomptablexlsx",
        "exportcomptablecsv",
    }
)
EMPTY_VALUE_TOKENS = frozenset({"", "-", "--", "n/a", "na", "null", "none", "nan"})


@dataclass(frozen=True)
class MonthMeasureColumn:
    column_name: str
    month: int
    measure: str


class ClientDemoImportNormalizer:
    def detect_source_type(self, file_name: str) -> str:
        normalized_file_name = normalize_token(file_name)
        if normalized_file_name in {"caprojets2025xlsx", "caprojets2026xlsx"}:
            return "ca_projects"
        if normalized_file_name == "toutesaffairesxlsx":
            return "affair_tracking"
        if normalized_file_name in {"reportingpnl2025xlsx", "reportingpnl2026xlsx"}:
            return "pnl"
        if normalized_file_name == "exportcomptablexlsx":
            return "accounting"
        if "caprojets" in normalized_file_name:
            return "ca_projects"
        if "toutesaffaires" in normalized_file_name:
            return "affair_tracking"
        if "reportingpnl" in normalized_file_name or normalized_file_name.startswith("pnl"):
            return "pnl"
        if "exportcomptable" in normalized_file_name or "comptable" in normalized_file_name:
            return "accounting"
        return "generic"

    def normalize_rows(
        self,
        company_id: str,
        file_name: str,
        rows: list[dict[str, object]],
        mapping: ImportMapping,
    ) -> list[dict[str, object]] | None:
        dataframe = pd.DataFrame(rows)
        if dataframe.empty:
            return []

        source_type = self.detect_source_type(file_name)
        if source_type == "ca_projects":
            return self._normalize_ca_projects(company_id, file_name, dataframe)
        if source_type == "affair_tracking":
            return self._normalize_affairs(company_id, file_name, dataframe)
        if source_type == "pnl":
            return self._normalize_pnl(company_id, file_name, dataframe)
        if source_type == "accounting":
            return self._normalize_accounting(company_id, file_name, dataframe)
        return None

    def _normalize_ca_projects(
        self, company_id: str, file_name: str, dataframe: pd.DataFrame
    ) -> list[dict[str, object]]:
        year = extract_year(file_name)
        month_measures = self._detect_month_measure_columns(dataframe.columns, default_measure="revenue")
        normalized: list[dict[str, object]] = []
        if month_measures:
            for _, row in dataframe.iterrows():
                base = self._base_project_payload(row, file_name, "ca_projects")
                month_payloads: dict[int, dict[str, object]] = {}
                for month_measure in month_measures:
                    value = to_number(row.get(month_measure.column_name))
                    if value is None:
                        continue
                    bucket = month_payloads.setdefault(
                        month_measure.month,
                        {
                            "date": build_period_date(year, month_measure.month),
                            "revenue": 0.0,
                            "cost": 0.0,
                            "purchase_amount": None,
                            "margin_amount": None,
                        },
                    )
                    if month_measure.measure == "revenue":
                        bucket["revenue"] = value
                    elif month_measure.measure == "purchase":
                        bucket["cost"] = value
                        bucket["purchase_amount"] = value
                    elif month_measure.measure == "margin":
                        bucket["margin_amount"] = value

                for month_payload in month_payloads.values():
                    normalized.append(self._complete_finance_payload(base | month_payload))
            return normalized

        revenue_column = find_column(dataframe.columns, "revenue")
        forecast_column = find_column(dataframe.columns, "forecast_revenue")
        remaining_to_invoice_column = find_column(dataframe.columns, "remaining_to_invoice")
        purchase_column = find_column(dataframe.columns, "purchase")
        margin_column = find_column(dataframe.columns, "margin")
        margin_rate_column = find_column(dataframe.columns, "margin_rate")
        date_column = find_column(dataframe.columns, "date")
        month_column = find_column(dataframe.columns, "month")
        year_column = find_column(dataframe.columns, "year")

        for _, row in dataframe.iterrows():
            revenue = to_number(row.get(revenue_column))
            purchase = to_number(row.get(purchase_column))
            margin = to_number(row.get(margin_column))
            margin_rate = to_number(row.get(margin_rate_column))
            date_value = self._resolve_row_date(
                row,
                date_column=date_column,
                month_column=month_column,
                year_column=year_column,
                fallback_year=year,
            )
            payload = self._base_project_payload(row, file_name, "ca_projects") | {
                "date": date_value,
                "revenue": revenue or 0.0,
                "forecast_revenue_amount": to_number(row.get(forecast_column)),
                "remaining_to_invoice_amount": to_number(row.get(remaining_to_invoice_column)),
                "cost": purchase or 0.0,
                "purchase_amount": purchase,
                "margin_amount": margin,
                "margin_rate": margin_rate,
            }
            normalized.append(self._complete_finance_payload(payload))
        return normalized

    def _normalize_affairs(
        self, company_id: str, file_name: str, dataframe: pd.DataFrame
    ) -> list[dict[str, object]]:
        year = extract_year(file_name)
        revenue_column = find_column(dataframe.columns, "revenue")
        forecast_column = find_column(dataframe.columns, "forecast_revenue")
        remaining_to_invoice_column = find_column(dataframe.columns, "remaining_to_invoice")
        purchase_column = find_column(dataframe.columns, "purchase")
        margin_column = find_column(dataframe.columns, "margin")
        margin_rate_column = find_column(dataframe.columns, "margin_rate")
        date_column = find_column(dataframe.columns, "date")
        month_column = find_column(dataframe.columns, "month")
        year_column = find_column(dataframe.columns, "year")
        normalized: list[dict[str, object]] = []

        for _, row in dataframe.iterrows():
            payload = self._base_project_payload(row, file_name, "affair_tracking") | {
                "date": self._resolve_row_date(
                    row,
                    date_column=date_column,
                    month_column=month_column,
                    year_column=year_column,
                    fallback_year=year,
                ),
                "revenue": to_number(row.get(revenue_column)) or 0.0,
                "forecast_revenue_amount": to_number(row.get(forecast_column)),
                "remaining_to_invoice_amount": to_number(row.get(remaining_to_invoice_column)),
                "cost": to_number(row.get(purchase_column)) or 0.0,
                "purchase_amount": to_number(row.get(purchase_column)),
                "margin_amount": to_number(row.get(margin_column)),
                "margin_rate": to_number(row.get(margin_rate_column)),
            }
            normalized.append(self._complete_finance_payload(payload))
        return normalized

    def _normalize_pnl(
        self, company_id: str, file_name: str, dataframe: pd.DataFrame
    ) -> list[dict[str, object]]:
        year = extract_year(file_name)
        normalized: list[dict[str, object]] = []
        label_column = find_column(dataframe.columns, "label")
        month_measures = self._detect_month_measure_columns(dataframe.columns, default_measure="revenue")

        if label_column and month_measures:
            measures_by_month: dict[int, dict[str, float]] = {}
            for _, row in dataframe.iterrows():
                detected_measure = self._resolve_pnl_row_measure(str(row.get(label_column) or ""))
                if detected_measure is None:
                    continue
                for month_measure in month_measures:
                    value = to_number(row.get(month_measure.column_name))
                    if value is None:
                        continue
                    bucket = measures_by_month.setdefault(month_measure.month, {})
                    bucket[detected_measure] = value

            for month, values in sorted(measures_by_month.items()):
                payload = {
                    "date": build_period_date(year, month),
                    "revenue": values.get("revenue", 0.0),
                    "forecast_revenue_amount": values.get("forecast"),
                    "margin_amount": values.get("margin"),
                    "cost": values.get("cost", 0.0),
                    "purchase_amount": values.get("cost"),
                    "source_type": "pnl",
                    "description": file_name,
                }
                normalized.append(self._complete_finance_payload(payload))
            return normalized

        revenue_column = find_column(dataframe.columns, "revenue")
        forecast_column = find_column(dataframe.columns, "forecast_revenue")
        margin_column = find_column(dataframe.columns, "margin")
        purchase_column = find_column(dataframe.columns, "purchase")
        date_column = find_column(dataframe.columns, "date")
        month_column = find_column(dataframe.columns, "month")
        year_column = find_column(dataframe.columns, "year")

        for _, row in dataframe.iterrows():
            payload = {
                "date": self._resolve_row_date(
                    row,
                    date_column=date_column,
                    month_column=month_column,
                    year_column=year_column,
                    fallback_year=year,
                ),
                "revenue": to_number(row.get(revenue_column)) or 0.0,
                "forecast_revenue_amount": to_number(row.get(forecast_column)),
                "margin_amount": to_number(row.get(margin_column)),
                "cost": to_number(row.get(purchase_column)) or 0.0,
                "purchase_amount": to_number(row.get(purchase_column)),
                "source_type": "pnl",
                "description": clean_optional(row.get(label_column)) or file_name,
            }
            normalized.append(self._complete_finance_payload(payload))
        return normalized

    def _normalize_accounting(
        self, company_id: str, file_name: str, dataframe: pd.DataFrame
    ) -> list[dict[str, object]]:
        year = extract_year(file_name)
        date_column = find_column(dataframe.columns, "date")
        month_column = find_column(dataframe.columns, "month")
        year_column = find_column(dataframe.columns, "year")
        debit_column = find_column(dataframe.columns, "debit")
        credit_column = find_column(dataframe.columns, "credit")
        amount_column = find_column(dataframe.columns, "amount")
        kind_column = find_column(dataframe.columns, "kind")
        invoice_column = find_column(dataframe.columns, "invoice_number")
        currency_column = find_column(dataframe.columns, "currency")
        account_column = find_column(dataframe.columns, "account_code")
        subaccount_column = find_column(dataframe.columns, "subaccount")
        client_column = find_column(dataframe.columns, "client")
        label_column = find_column(dataframe.columns, "label")

        normalized: list[dict[str, object]] = []
        for _, row in dataframe.iterrows():
            debit = to_number(row.get(debit_column))
            credit = to_number(row.get(credit_column))
            if debit is None and credit is None and amount_column and kind_column:
                amount = to_number(row.get(amount_column))
                kind = normalize_token(str(row.get(kind_column) or ""))
                if amount is not None:
                    if kind.startswith("d"):
                        debit = amount
                        credit = 0.0
                    elif kind.startswith("c"):
                        credit = amount
                        debit = 0.0

            amount = max(debit or 0.0, credit or 0.0)
            normalized.append(
                {
                    "date": self._resolve_row_date(
                        row,
                        date_column=date_column,
                        month_column=month_column,
                        year_column=year_column,
                        fallback_year=year,
                    ),
                    "revenue": 0.0,
                    "cost": 0.0,
                    "source_type": "accounting",
                    "client": clean_optional(row.get(client_column)),
                    "description": clean_optional(row.get(label_column)) or file_name,
                    "invoice_number": clean_optional(row.get(invoice_column)),
                    "currency": clean_optional(row.get(currency_column)),
                    "account_code": clean_optional(row.get(account_column)),
                    "subaccount": clean_optional(row.get(subaccount_column)),
                    "debit_amount": debit,
                    "credit_amount": credit,
                    "invoice_amount": amount,
                }
            )
        return normalized

    def _base_project_payload(
        self, row: pd.Series, file_name: str, source_type: str
    ) -> dict[str, object]:
        raw_project_code = clean_optional(row.get(find_column(row.index, "project_code")))
        raw_client_name = clean_optional(row.get(find_column(row.index, "client")))
        raw_business_pole = clean_optional(row.get(find_column(row.index, "business_pole")))
        raw_responsible_name = clean_optional(row.get(find_column(row.index, "responsible")))
        raw_resource_name = clean_optional(row.get(find_column(row.index, "resource")))
        normalized_project_reference = normalize_project_reference(
            raw_project_code or clean_optional(row.get(find_column(row.index, "project_name")))
        )
        normalized_client_name = normalize_client_name(raw_client_name)
        normalized_business_pole = normalize_technical_pole(raw_business_pole)

        return {
            "source_type": source_type,
            "project_code": raw_project_code,
            "project_name": clean_optional(row.get(find_column(row.index, "project_name"))),
            "original_project_reference": raw_project_code,
            "normalized_project_reference": normalized_project_reference,
            "client": normalized_client_name or raw_client_name,
            "original_client_name": raw_client_name,
            "normalized_client_name": normalized_client_name,
            "client_group": resolve_client_group(normalized_client_name or raw_client_name),
            "responsible": normalize_person_name(raw_responsible_name),
            "resource_name": normalize_person_name(raw_resource_name),
            "business_pole": normalized_business_pole or raw_business_pole,
            "original_business_pole": raw_business_pole,
            "normalized_business_pole": normalized_business_pole,
            "status": clean_optional(row.get(find_column(row.index, "status"))),
            "start_date": parse_optional_date(row.get(find_column(row.index, "start_date"))),
            "end_date": parse_optional_date(row.get(find_column(row.index, "end_date"))),
            "category": clean_optional(row.get(find_column(row.index, "category"))),
            "product": clean_optional(row.get(find_column(row.index, "product"))),
            "description": clean_optional(row.get(find_column(row.index, "label"))) or file_name,
        }

    def _complete_finance_payload(self, payload: dict[str, object]) -> dict[str, object]:
        revenue = float(payload.get("revenue") or 0.0)
        cost = float(payload.get("cost") or 0.0)
        purchase = to_number(payload.get("purchase_amount"))
        margin = to_number(payload.get("margin_amount"))
        margin_rate = to_number(payload.get("margin_rate"))
        remaining_to_invoice = to_number(payload.get("remaining_to_invoice_amount"))
        forecast_revenue = to_number(payload.get("forecast_revenue_amount"))

        effective_purchase = purchase if purchase is not None else cost
        if margin is None:
            margin = revenue - effective_purchase
        if margin_rate is None and revenue:
            margin_rate = margin / revenue * 100
        if remaining_to_invoice is None and forecast_revenue is not None:
            remaining_to_invoice = max(forecast_revenue - revenue, 0.0)

        return {
            **payload,
            "cost": effective_purchase,
            "purchase_amount": effective_purchase,
            "margin_amount": margin,
            "margin_rate": margin_rate,
            "remaining_to_invoice_amount": remaining_to_invoice,
        }

    def _resolve_row_date(
        self,
        row: pd.Series,
        *,
        date_column: str | None,
        month_column: str | None,
        year_column: str | None,
        fallback_year: int,
    ) -> str:
        explicit_date = parse_optional_date(row.get(date_column))
        if explicit_date:
            return explicit_date

        month_value = resolve_month(row.get(month_column))
        year_value = resolve_year_value(row.get(year_column), fallback_year)
        return build_period_date(year_value, month_value or 12)

    def _resolve_pnl_row_measure(self, label: str) -> str | None:
        normalized = normalize_token(label)
        if not normalized:
            return None
        if "forecast" in normalized or "budget" in normalized or "prevision" in normalized:
            return "forecast"
        if "marge" in normalized or "margin" in normalized:
            return "margin"
        if "charge" in normalized or "cost" in normalized or "achat" in normalized:
            return "cost"
        if "ca" in normalized or "revenue" in normalized or "realis" in normalized:
            return "revenue"
        return None

    def _detect_month_measure_columns(
        self, columns: pd.Index, default_measure: str
    ) -> list[MonthMeasureColumn]:
        detected: list[MonthMeasureColumn] = []
        for raw_column in columns:
            normalized = normalize_token(str(raw_column))
            month = detect_month_from_token(normalized)
            if month is None:
                continue

            measure = default_measure
            if any(alias in normalized for alias in ALIASES["purchase"]):
                measure = "purchase"
            elif any(alias in normalized for alias in ALIASES["margin"]):
                measure = "margin"
            elif any(alias in normalized for alias in ALIASES["forecast_revenue"]):
                measure = "forecast"
            detected.append(
                MonthMeasureColumn(column_name=str(raw_column), month=month, measure=measure)
            )
        return detected


def find_column(columns: pd.Index | list[object], alias_key: str) -> str | None:
    alias_candidates = ALIASES.get(alias_key, ())
    normalized_lookup = {str(column): normalize_token(str(column)) for column in columns}

    for raw_column, normalized in normalized_lookup.items():
        if normalized in alias_candidates:
            return raw_column

    for raw_column, normalized in normalized_lookup.items():
        if any(alias in normalized for alias in alias_candidates):
            return raw_column
    return None


def is_client_demo_template_file(file_name: str | None) -> bool:
    if not file_name:
        return False
    normalized = normalize_token(file_name)
    return normalized in AUTO_TEMPLATE_FILE_NAMES


def normalize_token(value: str) -> str:
    lowered = value.strip().lower()
    ascii_value = "".join(
        character
        for character in unicodedata.normalize("NFKD", lowered)
        if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", "", ascii_value)


def detect_month_from_token(token: str) -> int | None:
    for label, month in MONTH_TOKENS.items():
        if label in token:
            return month
    return None


def extract_year(file_name: str) -> int:
    match = re.search(r"(20\d{2})", file_name)
    if match:
        return int(match.group(1))
    return datetime.now().year


def resolve_year_value(value: object, fallback_year: int) -> int:
    if value is None or value == "":
        return fallback_year
    if isinstance(value, (int, float)):
        numeric = int(value)
        return numeric if 1900 <= numeric <= 2200 else fallback_year
    match = re.search(r"(20\d{2})", str(value))
    return int(match.group(1)) if match else fallback_year


def resolve_month(value: object) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        numeric = int(value)
        return numeric if 1 <= numeric <= 12 else None
    return detect_month_from_token(normalize_token(str(value)))


def build_period_date(year: int, month: int) -> str:
    return datetime(year, month, 1).date().isoformat()


def parse_optional_date(value: object) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        numeric_value = float(value)
        if pd.isna(numeric_value):
            return None
        if 1 <= numeric_value <= 60000:
            parsed = pd.to_datetime(numeric_value, unit="D", origin="1899-12-30", errors="coerce")
            if pd.notna(parsed):
                return parsed.date().isoformat()
    parsed = pd.to_datetime(value, errors="coerce", dayfirst=True)
    if pd.isna(parsed):
        return None
    return parsed.date().isoformat()


def to_number(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        numeric_value = float(value)
        return None if pd.isna(numeric_value) else numeric_value
    normalized = str(value).strip()
    if normalize_token(normalized) in EMPTY_VALUE_TOKENS:
        return None
    normalized = normalized.replace("\u00a0", "").replace(" ", "")
    normalized = re.sub(r"[€$£]|tnd|eur|usd", "", normalized, flags=re.IGNORECASE)
    normalized = normalized.replace("%", "")
    if normalized.startswith("(") and normalized.endswith(")"):
        normalized = f"-{normalized[1:-1]}"
    if normalized.endswith("-"):
        normalized = f"-{normalized[:-1]}"
    if normalized.count(",") > 1 and "." not in normalized:
        normalized = normalized.replace(",", "")
    elif normalized.count(".") > 1 and "," not in normalized:
        normalized = normalized.replace(".", "")
    elif "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    else:
        normalized = normalized.replace(",", ".")

    try:
        return float(normalized)
    except ValueError:
        return None


def clean_optional(value: object) -> str | None:
    if value is None:
        return None
    if pd.isna(value):
        return None
    normalized = str(value).strip()
    return None if normalize_token(normalized) in EMPTY_VALUE_TOKENS else normalized or None


def normalize_project_reference(value: str | None) -> str | None:
    if not value:
        return None
    normalized = normalize_token(value)
    return normalized.upper() or None


def normalize_client_name(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = " ".join(str(value).strip().split())
    normalized = normalize_token(cleaned)
    if not normalized:
        return None
    replacements = {
        "societe": "",
        "ste": "",
        "sarl": "",
        "sa": "",
        "sas": "",
    }
    simplified = normalized
    for token, replacement in replacements.items():
        simplified = simplified.replace(token, replacement)
    simplified = simplified.strip()
    return simplified.upper() or normalized.upper()


def resolve_client_group(value: str | None) -> str | None:
    if not value:
        return None
    normalized = normalize_client_name(value)
    return normalized or clean_optional(value)


def normalize_technical_pole(value: str | None) -> str | None:
    token = normalize_token(value or "")
    if not token:
        return None
    if "elec" in token:
        return "ELEC"
    if "cvc" in token or "clim" in token:
        return "CVC"
    if "fluide" in token:
        return "Fluides"
    if "plomb" in token:
        return "Plomberie"
    if "incendie" in token or "securite" in token:
        return "Sécurité incendie"
    if "bim" in token:
        return "BIM"
    return clean_optional(value)


def normalize_person_name(value: str | None) -> str | None:
    if not value:
        return None
    normalized = " ".join(str(value).strip().split())
    return normalized or None
