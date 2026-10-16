from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session
from app.schemas.product import (
    PlanDetailsResponse,
    PlanType,
    SubscriptionResponse,
    UpgradeRequest,
    PlanUsageResponse,
    FeatureFlag,
)
from app.services.product_service import ProductService
from app.services.feature_gate_service import FeatureGateService


router = APIRouter(prefix="/products", tags=["products"])


@router.get("/plans", response_model=list[PlanDetailsResponse])
async def get_available_plans():
    """
    Get all available plans with their features and pricing.
    """
    product_service = ProductService(session=None)
    
    plans = []
    for plan_type in PlanType:
        plan_details = await product_service.get_plan_details(plan_type)
        plans.append(plan_details)
    
    return plans


@router.get("/plans/{plan_type}", response_model=PlanDetailsResponse)
async def get_plan_details(plan_type: PlanType):
    """
    Get detailed information about a specific plan.
    """
    product_service = ProductService(session=None)
    return await product_service.get_plan_details(plan_type)


@router.get("/subscription/{company_id}", response_model=SubscriptionResponse)
async def get_subscription(
    company_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get current subscription for a company.
    """
    product_service = ProductService(session=session)
    subscription = await product_service.get_subscription(company_id)
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription not found for company {company_id}"
        )
    
    return subscription


@router.post("/subscription/{company_id}/upgrade", response_model=SubscriptionResponse)
async def upgrade_subscription(
    company_id: str,
    upgrade_request: UpgradeRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Upgrade company to a new plan.
    """
    product_service = ProductService(session=session)
    
    try:
        return await product_service.upgrade_plan(company_id, upgrade_request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/usage/{company_id}", response_model=PlanUsageResponse)
async def get_usage(
    company_id: str,
    feature_usage: str,  # Format: "import_rows:5000,users:3"
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get feature usage for a company.
    
    Query parameter format: "feature_name:value,feature_name:value"
    Example: "import_rows:5000,users:3"
    """
    # Parse feature usage from query string
    usage_dict = {}
    if feature_usage:
        for item in feature_usage.split(","):
            if ":" in item:
                key, value = item.split(":")
                try:
                    usage_dict[FeatureFlag(key)] = int(value)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid value for feature {key}"
                    )
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Unknown feature {key}"
                    )
    
    product_service = ProductService(session=session)
    
    try:
        return await product_service.get_usage(company_id, usage_dict)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# === Feature Gate Endpoints ===

@router.get("/features/check/{company_id}")
async def check_feature_access(
    company_id: str,
    feature: FeatureFlag,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Check if a specific feature is available for a company.
    """
    from app.db.models import CompanyORM
    from sqlalchemy import select
    
    result = await session.execute(
        select(CompanyORM).where(CompanyORM.id == company_id)
    )
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found"
        )
    
    feature_gate = FeatureGateService(session=session)
    has_access = feature_gate.check_feature(PlanType(company.plan), feature)
    
    return {
        "company_id": company_id,
        "feature": feature.value,
        "has_access": has_access,
        "plan": company.plan
    }


@router.get("/features/limits/{company_id}")
async def get_feature_limits(
    company_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get all feature limits for a company.
    """
    from app.db.models import CompanyORM
    from sqlalchemy import select
    
    result = await session.execute(
        select(CompanyORM).where(CompanyORM.id == company_id)
    )
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found"
        )
    
    feature_gate = FeatureGateService(session=session)
    plan_type = PlanType(company.plan)
    
    limits = {}
    for feature_flag in FeatureFlag:
        limits[feature_flag.value] = {
            "limit": feature_gate.get_feature_limit(plan_type, feature_flag),
            "has_access": feature_gate.check_feature(plan_type, feature_flag)
        }
    
    return {
        "company_id": company_id,
        "plan": company.plan,
        "features": limits
    }