from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PlanType(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class BillingCycle(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


# === Feature Flags ===
class FeatureFlag(str, Enum):
    # Import features
    IMPORT_UNLIMITED_ROWS = "import_unlimited_rows"
    IMPORT_API = "import_api"
    IMPORT_SCHEDULED = "import_scheduled"
    
    # Analytics features
    ADVANCED_ANALYTICS = "advanced_analytics"
    AI_RECOMMENDATIONS = "ai_recommendations"
    CUSTOM_KPIS = "custom_kpis"
    
    # Reporting features
    EXPORT_PDF = "export_pdf"
    EXPORT_EXCEL = "export_excel"
    SCHEDULED_REPORTS = "scheduled_reports"
    
    # Collaboration
    TEAM_MEMBERS = "team_members"
    ROLE_MANAGEMENT = "role_management"
    AUDIT_LOG = "audit_log"
    
    # Integration
    API_ACCESS = "api_access"
    WEBHOOKS = "webhooks"
    SSO = "sso"


# === Plan Features Configuration ===
PLAN_FEATURES: dict[PlanType, dict[FeatureFlag, int]] = {
    PlanType.FREE: {
        FeatureFlag.IMPORT_UNLIMITED_ROWS: 0,  # 100 rows limit
        FeatureFlag.IMPORT_API: 0,
        FeatureFlag.IMPORT_SCHEDULED: 0,
        FeatureFlag.ADVANCED_ANALYTICS: 0,
        FeatureFlag.AI_RECOMMENDATIONS: 0,
        FeatureFlag.CUSTOM_KPIS: 0,
        FeatureFlag.EXPORT_PDF: 1,
        FeatureFlag.EXPORT_EXCEL: 0,
        FeatureFlag.SCHEDULED_REPORTS: 0,
        FeatureFlag.TEAM_MEMBERS: 1,  # 1 user
        FeatureFlag.ROLE_MANAGEMENT: 0,
        FeatureFlag.AUDIT_LOG: 0,
        FeatureFlag.API_ACCESS: 0,
        FeatureFlag.WEBHOOKS: 0,
        FeatureFlag.SSO: 0,
    },
    PlanType.STARTER: {
        FeatureFlag.IMPORT_UNLIMITED_ROWS: 0,  # 5000 rows
        FeatureFlag.IMPORT_API: 0,
        FeatureFlag.IMPORT_SCHEDULED: 0,
        FeatureFlag.ADVANCED_ANALYTICS: 1,
        FeatureFlag.AI_RECOMMENDATIONS: 0,
        FeatureFlag.CUSTOM_KPIS: 0,
        FeatureFlag.EXPORT_PDF: 1,
        FeatureFlag.EXPORT_EXCEL: 1,
        FeatureFlag.SCHEDULED_REPORTS: 0,
        FeatureFlag.TEAM_MEMBERS: 3,  # 3 users
        FeatureFlag.ROLE_MANAGEMENT: 1,
        FeatureFlag.AUDIT_LOG: 1,
        FeatureFlag.API_ACCESS: 0,
        FeatureFlag.WEBHOOKS: 0,
        FeatureFlag.SSO: 0,
    },
    PlanType.PROFESSIONAL: {
        FeatureFlag.IMPORT_UNLIMITED_ROWS: 1,
        FeatureFlag.IMPORT_API: 1,
        FeatureFlag.IMPORT_SCHEDULED: 1,
        FeatureFlag.ADVANCED_ANALYTICS: 1,
        FeatureFlag.AI_RECOMMENDATIONS: 1,
        FeatureFlag.CUSTOM_KPIS: 1,
        FeatureFlag.EXPORT_PDF: 1,
        FeatureFlag.EXPORT_EXCEL: 1,
        FeatureFlag.SCHEDULED_REPORTS: 1,
        FeatureFlag.TEAM_MEMBERS: 10,  # 10 users
        FeatureFlag.ROLE_MANAGEMENT: 1,
        FeatureFlag.AUDIT_LOG: 1,
        FeatureFlag.API_ACCESS: 1,
        FeatureFlag.WEBHOOKS: 1,
        FeatureFlag.SSO: 0,
    },
    PlanType.ENTERPRISE: {
        FeatureFlag.IMPORT_UNLIMITED_ROWS: 1,
        FeatureFlag.IMPORT_API: 1,
        FeatureFlag.IMPORT_SCHEDULED: 1,
        FeatureFlag.ADVANCED_ANALYTICS: 1,
        FeatureFlag.AI_RECOMMENDATIONS: 1,
        FeatureFlag.CUSTOM_KPIS: 1,
        FeatureFlag.EXPORT_PDF: 1,
        FeatureFlag.EXPORT_EXCEL: 1,
        FeatureFlag.SCHEDULED_REPORTS: 1,
        FeatureFlag.TEAM_MEMBERS: -1,  # unlimited
        FeatureFlag.ROLE_MANAGEMENT: 1,
        FeatureFlag.AUDIT_LOG: 1,
        FeatureFlag.API_ACCESS: 1,
        FeatureFlag.WEBHOOKS: 1,
        FeatureFlag.SSO: 1,
    },
}


# === Pricing Configuration ===
PLAN_PRICING: dict[PlanType, dict[BillingCycle, float]] = {
    PlanType.FREE: {
        BillingCycle.MONTHLY: 0.0,
        BillingCycle.YEARLY: 0.0,
    },
    PlanType.STARTER: {
        BillingCycle.MONTHLY: 99.0,
        BillingCycle.YEARLY: 990.0,
    },
    PlanType.PROFESSIONAL: {
        BillingCycle.MONTHLY: 299.0,
        BillingCycle.YEARLY: 2990.0,
    },
    PlanType.ENTERPRISE: {
        BillingCycle.MONTHLY: 0.0,  # Custom pricing
        BillingCycle.YEARLY: 0.0,
    },
}


# === Schemas ===

class PlanFeatureResponse(BaseModel):
    feature: FeatureFlag
    enabled: bool
    limit: int | None = None  # -1 means unlimited


class PlanDetailsResponse(BaseModel):
    plan_type: PlanType
    billing_cycle: BillingCycle
    price: float
    features: list[PlanFeatureResponse]


class SubscriptionCreate(BaseModel):
    plan_type: PlanType = Field(default=PlanType.FREE)
    billing_cycle: BillingCycle = Field(default=BillingCycle.MONTHLY)


class SubscriptionResponse(BaseModel):
    company_id: str
    plan_type: PlanType
    billing_cycle: BillingCycle
    monthly_price: float
    yearly_price: float
    current_period_start: datetime
    current_period_end: datetime
    status: str  # active, cancelled, past_due
    features: list[PlanFeatureResponse]


class UpgradeRequest(BaseModel):
    new_plan_type: PlanType
    billing_cycle: BillingCycle = Field(default=BillingCycle.MONTHLY)


class FeatureUsageResponse(BaseModel):
    feature: FeatureFlag
    used: int
    limit: int
    remaining: int
    has_access: bool


class PlanUsageResponse(BaseModel):
    company_id: str
    plan_type: PlanType
    feature_usage: list[FeatureUsageResponse]
    period_start: datetime
    period_end: datetime