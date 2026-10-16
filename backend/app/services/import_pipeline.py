from __future__ import annotations

from io import BytesIO
from uuid import uuid4

import numpy as np
import pandas as pd
from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype

from app.services.client_demo_import import ClientDemoImportNormalizer, is_client_demo_template_file
from app.schemas.imports import (
    AnalyzeImportResponse,
    ImportMapping,
    ProcessImportRequest,
    ProcessImportResponse,
    ValidateImportResponse,
    ValidationMessage,
)
from app.schemas.platform import DashboardTrendPoint


class ImportPipelineService:
    def __init__(self) -> None:
        self.client_demo_normalizer = ClientDemoImportNormalizer()

    def analyze_file(self, file_name: str, content: bytes) -> AnalyzeImportResponse:
        if not content:
            raise ValueError("Uploaded file is empty.")

        dataframe = self._read_dataframe(file_name, content)
        if dataframe.empty or len(dataframe.columns) == 0:
            raise ValueError("Uploaded file does not contain analyzable business data.")

        dataframe = dataframe.replace({np.nan: None})
        return AnalyzeImportResponse(
            file_name=file_name,
            columns=[str(column) for column in dataframe.columns.tolist()],
            rows=self._to_records(dataframe),
            preview_rows=self._to_records(dataframe.head(5)),
            detected_types=self._detect_types(dataframe),
            suggestions=self._build_suggestions(dataframe.columns.tolist()),
            row_count=int(len(dataframe.index)),
        )

    def validate_rows(
        self,
        rows: list[dict[str, object]],
        mapping: ImportMapping,
        file_name: str | None = None,
        company_id: str | None = None,
    ) -> ValidateImportResponse:
        dataframe = pd.DataFrame(rows)
        messages: list[ValidationMessage] = []
        normalized_frame: pd.DataFrame

        use_client_demo_profile = is_client_demo_template_file(file_name)
        if use_client_demo_profile:
            normalized_rows = self.client_demo_normalizer.normalize_rows(
                company_id or "validation-company",
                file_name or "",
                rows,
                mapping,
            )
            normalized_frame = pd.DataFrame(normalized_rows or [])
            if normalized_frame.empty:
                messages.append(
                    ValidationMessage(
                        level="error",
                        message="The ON ING template was recognized but no normalized rows were produced.",
                        field="mapping",
                    )
                )
        else:
            if not mapping.date:
                messages.append(
                    ValidationMessage(level="error", message="A date column is required.", field="date")
                )

            has_split_amount_mapping = bool(mapping.amount and mapping.kind)
            has_direct_value_mapping = bool(mapping.revenue or mapping.cost)
            if not has_split_amount_mapping and not has_direct_value_mapping:
                messages.append(
                    ValidationMessage(
                        level="error",
                        message="Map either amount+kind or at least one revenue/cost column.",
                        field="amount",
                    )
                )

            missing_columns = [
                column
                for column in [
                    mapping.date,
                    mapping.amount,
                    mapping.kind,
                    mapping.revenue,
                    mapping.cost,
                    mapping.category,
                    mapping.product,
                    mapping.client,
                    mapping.description,
                ]
                if column and column not in dataframe.columns
            ]
            for column in missing_columns:
                messages.append(
                    ValidationMessage(
                        level="error",
                        message=f"Mapped column '{column}' was not found in the uploaded rows.",
                        field=column,
                    )
                )

            if (
                mapping.amount
                and mapping.kind
                and mapping.amount in dataframe.columns
                and mapping.kind in dataframe.columns
            ):
                kind_series = dataframe[mapping.kind].fillna("").astype(str).str.strip().str.upper()
                invalid_kind_rows = int(
                    (
                        ~kind_series.isin(
                            [
                                "REVENUE",
                                "INCOME",
                                "R",
                                "REVENU",
                                "EXPENSE",
                                "COST",
                                "CHARGE",
                                "E",
                                "DEPENSE",
                            ]
                        )
                        & (kind_series != "")
                    ).sum()
                )
                if invalid_kind_rows > 0:
                    messages.append(
                        ValidationMessage(
                            level="warning",
                            message=f"{invalid_kind_rows} rows contain values in '{mapping.kind}' that are not recognized as revenue or expense.",
                            field=mapping.kind,
                        )
                    )

            normalized_frame = self._normalize_rows(dataframe, mapping)
        if normalized_frame.empty:
            messages.append(
                ValidationMessage(
                    level="error",
                    message="No normalized rows were produced from the current mapping.",
                    field="mapping",
                )
            )

        if "date" in normalized_frame.columns:
            invalid_dates = int(normalized_frame["date"].isna().sum())
            if invalid_dates > 0:
                messages.append(
                    ValidationMessage(
                        level="warning",
                        message=f"{invalid_dates} rows contain invalid or missing dates after normalization.",
                        field="date",
                    )
                )
        elif "business_date" in normalized_frame.columns:
            invalid_dates = int(pd.to_datetime(normalized_frame["business_date"], errors="coerce").isna().sum())
            if invalid_dates > 0:
                messages.append(
                    ValidationMessage(
                        level="warning",
                        message=f"{invalid_dates} rows contain invalid or missing dates after normalization.",
                        field="business_date",
                    )
                )

        for amount_field in ("revenue", "cost"):
            if amount_field in normalized_frame.columns:
                missing_amounts = int(normalized_frame[amount_field].isna().sum())
                if missing_amounts > 0:
                    messages.append(
                        ValidationMessage(
                            level="warning",
                            message=f"{missing_amounts} rows contain invalid values in '{amount_field}'.",
                            field=amount_field,
                        )
                    )

                negative_amounts = int((normalized_frame[amount_field].fillna(0) < 0).sum())
                if negative_amounts > 0:
                    messages.append(
                        ValidationMessage(
                            level="warning",
                            message=f"{negative_amounts} rows contain negative values in '{amount_field}'.",
                            field=amount_field,
                        )
                    )

        normalized_preview = normalized_frame.head(5)
        return ValidateImportResponse(
            valid=not any(message.level == "error" for message in messages),
            messages=messages,
            normalized_preview=self._to_records(normalized_preview),
        )

    def process_import(self, payload: ProcessImportRequest) -> ProcessImportResponse:
        normalized = pd.DataFrame(self.normalize_import_rows(payload))
        return ProcessImportResponse(
            import_batch_id=f"imp-{uuid4().hex[:12]}",
            persisted_rows=int(len(normalized.index)),
            aggregation_level=payload.aggregation_level,
            status="PROCESSED",
        )

    def normalize_import_rows(self, payload: ProcessImportRequest) -> list[dict[str, object]]:
        normalized_client_rows = self.client_demo_normalizer.normalize_rows(
            payload.company_id,
            payload.file_name,
            payload.rows,
            payload.mapping,
        )
        if normalized_client_rows is not None:
            return normalized_client_rows

        dataframe = pd.DataFrame(payload.rows)
        normalized = self._normalize_rows(dataframe, payload.mapping)
        return self._to_records(normalized)

    def build_trend_points(
        self,
        normalized_rows: list[dict[str, object]],
        aggregation_level: str,
    ) -> list[DashboardTrendPoint]:
        if not normalized_rows:
            return []

        dataframe = pd.DataFrame(normalized_rows)
        if dataframe.empty or "date" not in dataframe.columns:
            return []

        working_frame = dataframe.copy()
        working_frame["date"] = pd.to_datetime(working_frame["date"], errors="coerce")
        working_frame = working_frame.dropna(subset=["date"])
        if working_frame.empty:
            return []

        if "revenue" in working_frame.columns:
            working_frame["revenue"] = pd.to_numeric(
                working_frame["revenue"], errors="coerce"
            ).fillna(0)
        else:
            working_frame["revenue"] = 0

        if "cost" in working_frame.columns:
            working_frame["cost"] = pd.to_numeric(working_frame["cost"], errors="coerce").fillna(0)
        else:
            working_frame["cost"] = 0

        if aggregation_level == "day":
            working_frame["bucket"] = working_frame["date"].dt.strftime("%Y-%m-%d")
        elif aggregation_level == "year":
            working_frame["bucket"] = working_frame["date"].dt.strftime("%Y")
        else:
            working_frame["bucket"] = working_frame["date"].dt.strftime("%Y-%m")

        grouped = (
            working_frame.groupby("bucket", as_index=False)[["revenue", "cost"]].sum().sort_values("bucket")
        )
        return [
            DashboardTrendPoint(
                bucket=str(row["bucket"]),
                totalRevenue=float(round(row["revenue"], 2)),
                totalExpenses=float(round(row["cost"], 2)),
                netMargin=float(round(row["revenue"] - row["cost"], 2)),
            )
            for _, row in grouped.iterrows()
        ]

    def _read_dataframe(self, file_name: str, content: bytes) -> pd.DataFrame:
        extension = file_name.lower().rsplit(".", maxsplit=1)[-1]
        buffer = BytesIO(content)
        if extension == "csv":
            return pd.read_csv(buffer)
        if extension in {"xlsx", "xls"}:
            return pd.read_excel(buffer)
        raise ValueError("Only CSV and Excel files are supported.")

    def _detect_types(self, dataframe: pd.DataFrame) -> dict[str, str]:
        detected: dict[str, str] = {}
        for column in dataframe.columns:
            series = dataframe[column]
            missing_rate = float(np.mean(series.isna().to_numpy()))
            if missing_rate > 0.85:
                detected[str(column)] = "unknown"
            elif is_datetime64_any_dtype(series):
                detected[str(column)] = "date"
            elif is_numeric_dtype(series):
                detected[str(column)] = "number"
            elif series.nunique(dropna=True) <= 12:
                detected[str(column)] = "category"
            else:
                detected[str(column)] = "text"
        return detected

    def _build_suggestions(self, columns: list[object]) -> dict[str, str | None]:
        suggestions: dict[str, str | None] = {}
        for raw_column in columns:
            column = str(raw_column).strip().lower()
            if "date" in column:
                suggestions[str(raw_column)] = "date"
            elif column in {"amount", "montant", "value", "total"}:
                suggestions[str(raw_column)] = "amount"
            elif column in {"type", "kind", "nature"}:
                suggestions[str(raw_column)] = "kind"
            elif column in {"revenue", "sales"}:
                suggestions[str(raw_column)] = "revenue"
            elif column in {"cost", "expense", "charges"}:
                suggestions[str(raw_column)] = "cost"
            elif "category" in column or "categorie" in column:
                suggestions[str(raw_column)] = "category"
            elif "product" in column:
                suggestions[str(raw_column)] = "product"
            elif "client" in column or "customer" in column:
                suggestions[str(raw_column)] = "client"
            elif "description" in column or "label" in column:
                suggestions[str(raw_column)] = "description"
            else:
                suggestions[str(raw_column)] = None
        return suggestions

    def _normalize_rows(self, dataframe: pd.DataFrame, mapping: ImportMapping) -> pd.DataFrame:
        normalized = pd.DataFrame()
        if mapping.date and mapping.date in dataframe:
            parsed_dates = pd.to_datetime(dataframe[mapping.date], errors="coerce")
            normalized["date"] = parsed_dates.map(
                lambda value: value.date().isoformat() if pd.notnull(value) else None
            )
        if mapping.amount and mapping.amount in dataframe and mapping.kind and mapping.kind in dataframe:
            amount_series = pd.to_numeric(dataframe[mapping.amount], errors="coerce")
            kind_series = dataframe[mapping.kind].fillna("").astype(str).str.strip().str.upper()
            normalized["revenue"] = amount_series.where(
                kind_series.isin(["REVENUE", "INCOME", "R", "REVENU"]),
                other=0,
            )
            normalized["cost"] = amount_series.where(
                kind_series.isin(["EXPENSE", "COST", "CHARGE", "E", "DEPENSE"]),
                other=0,
            )
        else:
            if mapping.revenue and mapping.revenue in dataframe:
                normalized["revenue"] = pd.to_numeric(dataframe[mapping.revenue], errors="coerce")
            if mapping.cost and mapping.cost in dataframe:
                normalized["cost"] = pd.to_numeric(dataframe[mapping.cost], errors="coerce")
        if mapping.category and mapping.category in dataframe:
            normalized["category"] = self._normalize_text_series(dataframe[mapping.category])
        if mapping.product and mapping.product in dataframe:
            normalized["product"] = self._normalize_text_series(dataframe[mapping.product])
        if mapping.client and mapping.client in dataframe:
            normalized["client"] = self._normalize_text_series(dataframe[mapping.client])
        if mapping.description and mapping.description in dataframe:
            normalized["description"] = self._normalize_text_series(dataframe[mapping.description])
        return normalized.replace({np.nan: None})

    def _to_records(self, dataframe: pd.DataFrame) -> list[dict[str, object]]:
        safe_frame = dataframe.copy()
        for column in safe_frame.columns:
            safe_frame[column] = safe_frame[column].where(pd.notnull(safe_frame[column]), None)
        return safe_frame.to_dict(orient="records")

    def _normalize_text_series(self, series: pd.Series) -> pd.Series:
        normalized = series.fillna("").astype(str).map(lambda value: value.strip())
        return normalized.replace("", None)
