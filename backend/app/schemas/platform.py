from typing import Literal

from pydantic import BaseModel


class CompanyRead(BaseModel):
    id: str
    name: str
    sector: str
    plan: str
    health: str
    country: str
    currency: str
    monthlyTarget: int
    headquarters: str
    lastSyncAt: str
    shortName: str | None = None
    profileCode: str | None = None
    mainMarket: str | None = None
    subtitle: str | None = None
    technicalPoles: list[str] = []
    navigationLabels: list[str] = []


class KpiDefinitionUpsert(BaseModel):
    companyId: str
    name: str
    category: Literal["Finance", "Sales", "Operations"]
    formula: str
    threshold: float
    unit: Literal["currency", "percent", "ratio"]
    direction: Literal["up", "down"]
    description: str
    sourceKey: Literal["revenue", "growth", "charges", "margin"]


class KpiDefinitionRead(KpiDefinitionUpsert):
    id: str
    createdAt: str
    updatedAt: str


class UserRead(BaseModel):
    id: str
    fullName: str
    email: str
    title: str
    roleType: str
    primaryCompanyId: str
    companyIds: list[str]
    status: str
    lastLoginAt: str | None


class UserActivitySummaryRead(BaseModel):
    totalImports: int
    lastImportDate: str | None
    totalReportsGenerated: int
    lastActivity: str | None


class CurrentUserProfileRead(BaseModel):
    userId: str
    enterpriseId: str
    email: str
    fullName: str
    title: str
    roleType: str
    status: str
    companyName: str
    accountCreatedDate: str
    lastLoginAt: str | None
    avatarUrl: str | None
    activitySummary: UserActivitySummaryRead


class CurrentUserProfileUpdate(BaseModel):
    fullName: str
    avatarUrl: str | None = None


class CurrentUserPasswordUpdate(BaseModel):
    currentPassword: str
    newPassword: str


class UserUpsert(BaseModel):
    fullName: str
    email: str
    title: str
    roleType: Literal["SAL_ADMIN", "ENT_ADMIN", "PME_USER"]
    primaryCompanyId: str
    status: Literal["active", "pending", "suspended"]


class DashboardSummaryResponse(BaseModel):
    totalRevenue: float
    totalExpenses: float
    netMargin: float
    revenueGrowth: float
    chargeRatio: float
    computedAt: str


class DashboardTrendPoint(BaseModel):
    bucket: str
    totalRevenue: float
    totalExpenses: float
    netMargin: float


class DashboardStoryHighlight(BaseModel):
    id: str
    title: str
    description: str
    tone: Literal["success", "warning", "danger", "info"]


class DashboardOverviewResponse(BaseModel):
    companyId: str
    summary: DashboardSummaryResponse
    trend: list[DashboardTrendPoint]
    storyHighlights: list[DashboardStoryHighlight]
    recommendation: str
    sourceMode: Literal["demo", "database-ready"]


class AlertTrigger(BaseModel):
    kpiCode: str
    kpiLabel: str
    actualValue: float
    actualValueLabel: str
    threshold: float
    thresholdLabel: str
    operator: str
    operatorLabel: str
    statement: str


class AlertRead(BaseModel):
    id: str
    companyId: str
    ruleId: str | None = None
    source: str
    ruleName: str
    title: str
    message: str
    explainabilityText: str
    recommendation: str
    severity: Literal["critical", "warning", "info"]
    isActive: bool
    createdAt: str
    triggerCount: int = 1
    firstTriggeredAt: str | None = None
    lastTriggeredAt: str | None = None
    resolvedAt: str | None = None
    resolvedByUserId: str | None = None
    triggeredBy: AlertTrigger | None = None
    matchedConditions: list[AlertTrigger] = []


class AlertHistoryRead(BaseModel):
    id: str
    alertId: str
    companyId: str
    ruleId: str | None
    ruleName: str
    eventType: Literal["TRIGGERED", "RESOLVED"]
    severity: Literal["critical", "warning", "info"]
    title: str
    message: str
    recommendation: str
    alertStatus: Literal["ACTIVE", "RESOLVED"]
    occurredAt: str
    actedByUserId: str | None = None
    actedByUserName: str | None = None
    eventSource: Literal["RULE_ENGINE", "USER_ACTION", "SYSTEM"] = "SYSTEM"
    evaluationWindow: str | None = None
    contextBucket: str | None = None
    lifecycleNote: str | None = None
    triggeredBy: AlertTrigger | None = None
    matchedConditions: list[AlertTrigger] = []


class DecisionRuleConditionRead(BaseModel):
    id: str
    kpiCode: str
    operator: str
    threshold: float


class DecisionRuleCreate(BaseModel):
    companyId: str | None = None
    name: str
    priority: int = 50
    severity: Literal["critical", "warning", "info"]
    logic: Literal["AND", "OR"]
    actionType: Literal["alert", "recommendation", "both"]
    enabled: bool = True
    titleEn: str = ""
    titleFr: str = ""
    explanationTemplateEn: str = ""
    explanationTemplateFr: str = ""
    recommendationTemplateEn: str = ""
    recommendationTemplateFr: str = ""
    conditions: list[DecisionRuleConditionRead]


class DecisionRuleRead(DecisionRuleCreate):
    id: str
    createdAt: str
    updatedAt: str


class AuditLogRead(BaseModel):
    id: str
    enterpriseId: str
    userId: str
    actionType: str
    status: Literal["SUCCESS", "INFO", "ERROR"]
    description: str
    occurredAt: str


class AuditLogCreate(BaseModel):
    enterpriseId: str
    userId: str
    actionType: str
    status: Literal["SUCCESS", "INFO", "ERROR"] = "SUCCESS"
    description: str


class ReportExportRequest(BaseModel):
    companyId: str
    requestedBy: str
    format: Literal["pdf", "excel"]


class ReportExportResponse(BaseModel):
    id: str
    status: str
    fileName: str
    message: str
    generatedAt: str
    downloadPath: str | None = None


class ImportBatchRead(BaseModel):
    id: str
    companyId: str
    uploadedBy: str
    fileName: str
    aggregationLevel: str
    persistedRows: int
    status: str
    createdAt: str


class ReportExportRead(BaseModel):
    id: str
    companyId: str
    requestedBy: str
    format: Literal["pdf", "excel"]
    fileName: str
    status: str
    generatedAt: str
    downloadPath: str | None = None


class ReportBreakdownItem(BaseModel):
    name: str
    revenue: float


class ReportAlertDigestRead(BaseModel):
    alertId: str
    ruleId: str | None = None
    ruleName: str
    severity: Literal["critical", "warning", "info"]
    title: str
    recommendation: str
    status: Literal["ACTIVE", "RESOLVED"]
    createdAt: str


class ReportPreviewRead(BaseModel):
    companyName: str
    generatedAt: str
    totalRevenue: float
    totalExpenses: float
    netMargin: float
    growthPercent: float
    chargeRatio: float
    activeAlerts: int
    criticalAlerts: int
    priorityRecommendation: str
    alertsDigest: list[ReportAlertDigestRead]
    topProducts: list[ReportBreakdownItem]
    topClients: list[ReportBreakdownItem]
