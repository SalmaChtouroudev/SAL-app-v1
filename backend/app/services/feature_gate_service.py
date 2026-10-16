from typing import Optional
from functools import wraps
from fastapi import HTTPException, status

from app.schemas.product import (
    PLAN_FEATURES,
    FeatureFlag,
    PlanType,
)


class FeatureGateService:
    """Service for checking feature access based on plan."""

    def __init__(self, session=None):
        self.session = session

    def check_feature(self, plan_type: PlanType, feature: FeatureFlag) -> bool:
        """
        Check if a feature is available for a given plan.
        
        Args:
            plan_type: The plan type to check
            feature: The feature flag to check
            
        Returns:
            True if feature is available, False otherwise
        """
        if plan_type not in PLAN_FEATURES:
            return False
        
        limit = PLAN_FEATURES[plan_type].get(feature, 0)
        return limit != 0

    def get_feature_limit(self, plan_type: PlanType, feature: FeatureFlag) -> int:
        """
        Get the limit for a feature in a given plan.
        
        Args:
            plan_type: The plan type
            feature: The feature flag
            
        Returns:
            -1 for unlimited, 0 for disabled, >0 for limited access
        """
        if plan_type not in PLAN_FEATURES:
            return 0
        
        return PLAN_FEATURES[plan_type].get(feature, 0)

    def check_import_limit(self, plan_type: PlanType, row_count: int) -> tuple[bool, str]:
        """
        Check if import row count is within limits.
        
        Returns:
            Tuple of (allowed, message)
        """
        limit = self.get_feature_limit(plan_type, FeatureFlag.IMPORT_UNLIMITED_ROWS)
        
        if limit == -1:  # Unlimited
            return True, "Import allowed (unlimited)"
        elif limit == 0:
            # Check basic limit (100 rows for free)
            if row_count <= 100:
                return True, f"Import allowed ({row_count}/100 rows)"
            return False, f"Import limit exceeded. Upgrade to Starter for 5000 rows/month"
        else:
            if row_count <= limit:
                return True, f"Import allowed ({row_count}/{limit} rows)"
            return False, f"Import limit exceeded ({row_count}/{limit} rows)"

    def check_user_limit(self, plan_type: PlanType, current_users: int) -> tuple[bool, str]:
        """
        Check if user count is within plan limits.
        
        Returns:
            Tuple of (allowed, message)
        """
        limit = self.get_feature_limit(plan_type, FeatureFlag.TEAM_MEMBERS)
        
        if limit == -1:  # Unlimited
            return True, "Users allowed (unlimited)"
        elif current_users >= limit:
            return False, f"User limit reached ({current_users}/{limit}). Upgrade to add more users"
        return True, f"User slot available ({current_users}/{limit})"

    def check_api_access(self, plan_type: PlanType) -> bool:
        """Check if API access is available."""
        return self.check_feature(plan_type, FeatureFlag.API_ACCESS)

    def check_ai_recommendations(self, plan_type: PlanType) -> bool:
        """Check if AI recommendations are available."""
        return self.check_feature(plan_type, FeatureFlag.AI_RECOMMENDATIONS)

    def check_export_pdf(self, plan_type: PlanType) -> bool:
        """Check if PDF export is available."""
        return self.check_feature(plan_type, FeatureFlag.EXPORT_PDF)

    def check_export_excel(self, plan_type: PlanType) -> bool:
        """Check if Excel export is available."""
        return self.check_feature(plan_type, FeatureFlag.EXPORT_EXCEL)

    def check_scheduled_reports(self, plan_type: PlanType) -> bool:
        """Check if scheduled reports are available."""
        return self.check_feature(plan_type, FeatureFlag.SCHEDULED_REPORTS)

    def check_sso(self, plan_type: PlanType) -> bool:
        """Check if SSO is available."""
        return self.check_feature(plan_type, FeatureFlag.SSO)


# === Decorators for FastAPI ===

def require_feature(feature: FeatureFlag):
    """
    Decorator to protect endpoints based on feature access.
    
    Usage:
        @require_feature(FeatureFlag.API_ACCESS)
        async def my_endpoint():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get plan_type from kwargs or context
            plan_type = kwargs.get('plan_type')
            if not plan_type:
                # Try to get from company_id
                company_id = kwargs.get('company_id')
                if company_id and hasattr(wrapper, 'session'):
                    # This would need to be resolved at runtime
                    pass
            
            # This is a simplified version - in production you'd
            # inject the service and check the feature
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def check_feature_or_403(feature: FeatureFlag):
    """
    Decorator that raises 403 if feature is not available.
    
    Usage:
        @check_feature_or_403(FeatureFlag.EXPORT_PDF)
        async def export_report():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # This would be resolved with proper dependency injection
            # For now, return a placeholder that shows the pattern
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature '{feature.value}' not available in your plan. Upgrade to access."
            )
        return wrapper
    return decorator


# === Helper Functions ===

def get_available_features(plan_type: PlanType) -> list[str]:
    """Get list of available feature names for a plan."""
    if plan_type not in PLAN_FEATURES:
        return []
    
    features = []
    for feature, limit in PLAN_FEATURES[plan_type].items():
        if limit != 0:
            features.append(feature.value)
    
    return features


def get_upgrade_recommendation(current_plan: PlanType) -> Optional[PlanType]:
    """Get recommended upgrade plan based on current plan."""
    upgrades = {
        PlanType.FREE: PlanType.STARTER,
        PlanType.STARTER: PlanType.PROFESSIONAL,
        PlanType.PROFESSIONAL: PlanType.ENTERPRISE,
        PlanType.ENTERPRISE: None,
    }
    return upgrades.get(current_plan)