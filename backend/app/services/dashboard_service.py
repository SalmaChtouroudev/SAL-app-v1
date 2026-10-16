from __future__ import annotations

from datetime import datetime, timezone

from app.repositories.demo_repository import DemoPlatformRepository
from app.repositories.platform_repository import PlatformRepository
from app.schemas.platform import (
    DashboardOverviewResponse,
    DashboardStoryHighlight,
    DashboardSummaryResponse,
    DashboardTrendPoint,
)


class DashboardService:
    def __init__(self, repository: PlatformRepository) -> None:
        self.repository = repository

    def get_summary(self, company_id: str) -> DashboardSummaryResponse:
        trend = self.repository.get_dashboard_trend(company_id)
        total_revenue = round(sum(point.totalRevenue for point in trend), 2)
        total_expenses = round(sum(point.totalExpenses for point in trend), 2)
        net_margin = round(total_revenue - total_expenses, 2)
        previous_revenue = trend[-2].totalRevenue if len(trend) > 1 else 0
        latest_revenue = trend[-1].totalRevenue if trend else 0
        revenue_growth = (
            round(((latest_revenue - previous_revenue) / previous_revenue) * 100, 2)
            if previous_revenue
            else 0.0
        )
        charge_ratio = round((total_expenses / total_revenue) * 100, 2) if total_revenue else 0.0
        return DashboardSummaryResponse(
            totalRevenue=total_revenue,
            totalExpenses=total_expenses,
            netMargin=net_margin,
            revenueGrowth=revenue_growth,
            chargeRatio=charge_ratio,
            computedAt=datetime.now(tz=timezone.utc).isoformat(),
        )

    def get_trend(self, company_id: str) -> list[DashboardTrendPoint]:
        return self.repository.get_dashboard_trend(company_id)

    def get_overview(self, company_id: str) -> DashboardOverviewResponse:
        summary = self.get_summary(company_id)
        return DashboardOverviewResponse(
            companyId=company_id,
            summary=summary,
            trend=self.get_trend(company_id),
            storyHighlights=self.build_story_highlights(summary),
            recommendation=self.build_recommendation(summary),
            sourceMode="demo" if isinstance(self.repository, DemoPlatformRepository) else "database-ready",
        )

    def build_story_highlights(
        self, summary: DashboardSummaryResponse
    ) -> list[DashboardStoryHighlight]:
        growth_title = (
            "Revenue momentum is accelerating"
            if summary.revenueGrowth >= 7
            else "Revenue momentum is stable"
            if summary.revenueGrowth >= 2
            else "Revenue momentum is slowing"
        )
        growth_tone = (
            "success" if summary.revenueGrowth >= 7 else "warning" if summary.revenueGrowth >= 2 else "danger"
        )
        margin_title = (
            "Margin remains inside the target band"
            if summary.netMargin > 0 and summary.chargeRatio < 60
            else "Margin remains under surveillance"
            if summary.netMargin > 0
            else "Margin is now critically compressed"
        )
        margin_tone = "success" if summary.netMargin > 0 and summary.chargeRatio < 60 else "warning" if summary.netMargin > 0 else "danger"
        charge_title = (
            "Cost discipline is under control"
            if summary.chargeRatio <= 55
            else "Charge ratio needs attention"
            if summary.chargeRatio <= 70
            else "Charge ratio is above the safe operating band"
        )
        charge_tone = "success" if summary.chargeRatio <= 55 else "warning" if summary.chargeRatio <= 70 else "danger"

        return [
            DashboardStoryHighlight(
                id="revenue-momentum",
                title=growth_title,
                description=f"Latest visible growth is {summary.revenueGrowth:.1f}% with pressure on the current sales cycle.",
                tone=growth_tone,
            ),
            DashboardStoryHighlight(
                id="profitability",
                title=margin_title,
                description=f"Net margin stands at {summary.netMargin:,.0f} TND across the visible scope.",
                tone=margin_tone,
            ),
            DashboardStoryHighlight(
                id="cost-discipline",
                title=charge_title,
                description=f"Charges consume {summary.chargeRatio:.1f}% of revenue, which justifies active recommendations.",
                tone=charge_tone,
            ),
        ]

    def build_recommendation(self, summary: DashboardSummaryResponse) -> str:
        if summary.netMargin <= 0:
            return "Restore profitability immediately by reducing controllable costs and pausing low-yield spending."
        if summary.chargeRatio > 70:
            return "Reduce controllable costs, review supplier contracts, and prioritize higher-margin revenue streams."
        if summary.revenueGrowth < 2:
            return "Rebuild commercial momentum with focused campaigns on active products and top clients."
        return "The company is stable. Continue monitoring and keep the current operating discipline."
