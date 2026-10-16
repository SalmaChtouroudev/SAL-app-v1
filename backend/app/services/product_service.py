from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CompanyORM
from app.schemas.product import (
    PLAN_FEATURES,
    PLAN_PRICING,
    BillingCycle,
    FeatureFlag,
    PlanDetailsResponse,
    PlanFeatureResponse,
    PlanType,
    PlanUsageResponse,
    SubscriptionCreate,
    SubscriptionResponse,
    UpgradeRequest,
    FeatureUsageResponse,
)


class ProductService:
    """Service for managing product tiers and feature access."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_subscription(self, company_id: str) -> Optional[SubscriptionResponse]:
        """Get current subscription for a company."""
        result = await self.session.execute(
            select(CompanyORM).where(CompanyORM.id == company_id)
        )
        company = result.scalar_one_or_none()
        
        if not company:
            return None
        
        plan_type = PlanType(company.plan)
        return self._build_subscription_response(company_id, plan_type)

    def _build_subscription_response(
        self, company_id: str, plan_type: PlanType
    ) -> SubscriptionResponse:
        """Build subscription response from plan type."""
        features = self._get_plan_features(plan_type)
        
        # Default to monthly billing
        billing_cycle = BillingCycle.MONTHLY
        monthly_price = PLAN_PRICING[plan_type][BillingCycle.MONTHLY]
        yearly_price = PLAN_PRICING[plan_type][BillingCycle.YEARLY]
        
        # Calculate period (default to current month)
        now = datetime.utcnow()
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if plan_type == PlanType.FREE:
            period_end = period_start + timedelta(days=30)
        else:
            period_end = (period_start + timedelta(days=31)).replace(day=1)
        
        return SubscriptionResponse(
            company_id=company_id,
            plan_type=plan_type,
            billing_cycle=billing_cycle,
            monthly_price=monthly_price,
            yearly_price=yearly_price,
            current_period_start=period_start,
            current_period_end=period_end,
            status="active",
            features=features,
        )

    def _get_plan_features(self, plan_type: PlanType) -> list[PlanFeatureResponse]:
        """Get features for a plan type."""
        features_config = PLAN_FEATURES[plan_type]
        features = []
        
        for feature_flag, limit in features_config.items():
            enabled = limit != 0
            has_access = enabled
            
            # For unlimited features (-1), set limit to None
            actual_limit = None if limit == -1 else limit
            
            features.append(
                PlanFeatureResponse(
                    feature=feature_flag,
                    enabled=has_access,
                    limit=actual_limit,
                )
            )
        
        return features

    async def get_plan_details(self, plan_type: PlanType) -> PlanDetailsResponse:
        """Get detailed plan information."""
        features = self._get_plan_features(plan_type)
        monthly_price = PLAN_PRICING[plan_type][BillingCycle.MONTHLY]
        yearly_price = PLAN_PRICING[plan_type][BillingCycle.YEARLY]
        
        return PlanDetailsResponse(
            plan_type=plan_type,
            billing_cycle=BillingCycle.MONTHLY,
            price=monthly_price,
            features=features,
        )

    async def upgrade_plan(
        self, company_id: str, upgrade_request: UpgradeRequest
    ) -> SubscriptionResponse:
        """Upgrade company to a new plan."""
        result = await self.session.execute(
            select(CompanyORM).where(CompanyORM.id == company_id)
        )
        company = result.scalar_one_or_none()
        
        if not company:
            raise ValueError(f"Company {company_id} not found")
        
        # Update company plan
        company.plan = upgrade_request.new_plan_type.value
        await self.session.commit()
        
        return self._build_subscription_response(
            company_id, upgrade_request.new_plan_type
        )

    async def get_usage(
        self, company_id: str, feature_usage: dict[FeatureFlag, int]
    ) -> PlanUsageResponse:
        """Get feature usage for a company."""
        result = await self.session.execute(
            select(CompanyORM).where(CompanyORM.id == company_id)
        )
        company = result.scalar_one_or_none()
        
        if not company:
            raise ValueError(f"Company {company_id} not found")
        
        plan_type = PlanType(company.plan)
        features_config = PLAN_FEATURES[plan_type]
        
        usage_details = []
        for feature_flag, used in feature_usage.items():
            limit = features_config.get(feature_flag, 0)
            
            # Determine access
            if limit == -1:  # Unlimited
                has_access = True
                remaining = -1
            elif limit == 0:
                has_access = False
                remaining = 0
            else:
                has_access = used <= limit
                remaining = max(0, limit - used)
            
            usage_details.append(
                FeatureUsageResponse(
                    feature=feature_flag,
                    used=used,
                    limit=limit if limit > 0 else 0,
                    remaining=remaining,
                    has_access=has_access,
                )
            )
        
        now = datetime.utcnow()
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        period_end = (period_start + timedelta(days=31)).replace(day=1)
        
        return PlanUsageResponse(
            company_id=company_id,
            plan_type=plan_type,
            feature_usage=usage_details,
            period_start=period_start,
            period_end=period_end,
        )

    async def create_subscription(
        self, company_id: str, subscription: SubscriptionCreate
    ) -> SubscriptionResponse:
        """Create a new subscription for a company."""
        result = await self.session.execute(
            select(CompanyORM).where(CompanyORM.id == company_id)
        )
        company = result.scalar_one_or_none()
        
        if not company:
            raise ValueError(f"Company {company_id} not found")
        
        # Update company plan
        company.plan = subscription.plan_type.value
        await self.session.commit()
        
        return self._build_subscription_response(company_id, subscription.plan_type)