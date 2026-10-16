from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.schemas.platform import AlertRead


DashboardTableValue = str | int | float | None


class ClientDemoMetricCard(BaseModel):
    code: str
    label: str
    value: float
    displayValue: str
    unit: str
    tone: Literal["success", "warning", "danger", "info"] = "info"
    helperText: str | None = None


class ClientDemoChartPoint(BaseModel):
    label: str
    value: float


class ClientDemoChartSeries(BaseModel):
    key: str
    label: str
    points: list[ClientDemoChartPoint]


class ClientDemoChart(BaseModel):
    id: str
    title: str
    kind: Literal["line", "bar", "donut"]
    series: list[ClientDemoChartSeries]


class ClientDemoTableColumn(BaseModel):
    key: str
    label: str


class ClientDemoTable(BaseModel):
    id: str
    title: str
    columns: list[ClientDemoTableColumn]
    rows: list[dict[str, DashboardTableValue]]


class ClientDemoSection(BaseModel):
    id: str
    title: str
    cards: list[ClientDemoMetricCard]
    charts: list[ClientDemoChart]
    tables: list[ClientDemoTable]
    alerts: list[AlertRead]


class ClientDemoDashboardOverview(BaseModel):
    companyId: str
    generatedAt: str
    availableSources: list[str]
    missingSources: list[str]
    sections: list[ClientDemoSection]
    activeAlerts: list[AlertRead]
