"""Student analytics: JSON dashboard + base64 PNG charts."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analytics import chart_generator, student_analytics
from fastapi_app.core.database import get_db
from fastapi_app.core.security import get_current_user
from fastapi_app.models.schemas import AnalyticsChartsOut, AnalyticsDashboardOut
from fastapi_app.models.sql_models import Application, StudentProfile, User

router = APIRouter(prefix="/analytics", tags=["analytics"])


async def _rows(db: AsyncSession, user_id: int) -> list[dict]:
    apps = (
        await db.execute(select(Application).where(Application.user_id == user_id))
    ).scalars().all()
    rows = []
    for a in apps:
        opp = a.opportunity
        rows.append(
            {
                "status": a.status,
                "eligibility_status": a.eligibility_status,
                "company_name": opp.company_name if opp else None,
                "role": opp.role if opp else None,
                "opportunity_type": opp.opportunity_type if opp else None,
                "required_skills": (opp.required_skills if opp else []) or [],
                "deadline": opp.deadline.isoformat() if opp and opp.deadline else None,
            }
        )
    return rows


@router.get("/dashboard", response_model=AnalyticsDashboardOut)
async def dashboard(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await _rows(db, user.id)
    return AnalyticsDashboardOut(**student_analytics.compute_dashboard(rows))


@router.get("/charts", response_model=AnalyticsChartsOut)
async def charts(
    theme: str = "light",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await _rows(db, user.id)
    dash = student_analytics.compute_dashboard(rows)

    profile = (
        await db.execute(select(StudentProfile).where(StudentProfile.user_id == user.id))
    ).scalar_one_or_none()
    gap_demand = student_analytics.skill_gap_demand(
        rows, profile.skills if profile else []
    )

    dark = theme.lower() == "dark"
    return AnalyticsChartsOut(
        status_pie=chart_generator.status_pie_chart(dash["status_counts"], dark=dark),
        skill_gap_bar=chart_generator.skill_gap_bar_chart(gap_demand, dark=dark),
    )
