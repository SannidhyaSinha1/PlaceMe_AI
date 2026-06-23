"""AI endpoints: resume optimizer, cover letter, company research, recommend, extract."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_agents import (
    career_recommender,
    company_researcher,
    cover_letter_gen,
    latex_tailor,
    resume_optimizer,
    resume_tailor,
)
from fastapi_app.core.database import get_db, mongo_collection
from fastapi_app.core.security import get_current_user, require_complete_profile
from fastapi_app.models.schemas import (
    CareerAdviceOut,
    CoverLetterOut,
    ExtractIn,
    ExtractOut,
    LatexTailorOut,
    ResearchOut,
    ResumeAnalysisOut,
    TailoredResumeOut,
)
from fastapi_app.models.sql_models import Application, Opportunity, StudentProfile, User
from fastapi_app.services import pipeline

router = APIRouter(prefix="/ai", tags=["ai"])


async def _load(db: AsyncSession, user: User, opp_id: int):
    opp = await db.get(Opportunity, opp_id)
    if opp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Opportunity not found")
    profile = (
        await db.execute(select(StudentProfile).where(StudentProfile.user_id == user.id))
    ).scalar_one_or_none()
    if profile is None or not profile.resume_parsed:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Upload and parse your resume first"
        )
    return opp, profile


def _job_description(opp: Opportunity) -> str:
    parts = [opp.role or "", opp.description or "", " ".join(opp.required_skills or [])]
    return " ".join(p for p in parts if p)


def _slug(text: str | None) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")[:40]


@router.post("/extract", response_model=ExtractOut)
async def extract(payload: ExtractIn, _: User = Depends(get_current_user)):
    """Run the extractor + classifier on arbitrary email text (demo/manual use)."""
    return ExtractOut(**pipeline.extract_and_classify(payload.subject, payload.body))


@router.post("/resume/{opp_id}", response_model=ResumeAnalysisOut)
async def optimize_resume(
    opp_id: int, user: User = Depends(require_complete_profile), db: AsyncSession = Depends(get_db)
):
    opp, profile = await _load(db, user, opp_id)
    analysis = resume_optimizer.analyze_resume(
        profile.resume_parsed, _job_description(opp), opp.required_skills or []
    )
    await _store_ai_content(user.id, opp_id, "resume_analysis", analysis)
    return ResumeAnalysisOut(**analysis)


@router.post("/resume/{opp_id}/tailor", response_model=TailoredResumeOut)
async def tailor_resume(
    opp_id: int, user: User = Depends(require_complete_profile), db: AsyncSession = Depends(get_db)
):
    """Highlight the student's original resume for this role (layout preserved)."""
    opp, profile = await _load(db, user, opp_id)
    result = await resume_tailor.generate_and_store(
        user.id,
        {**opp.as_dict(), "id": opp.id},
        profile.resume_url,
        profile.resume_parsed,
        opp.required_skills or [],
        _job_description(opp),
    )
    await _store_ai_content(user.id, opp_id, "tailored_resume", result)
    return TailoredResumeOut(**result)


@router.post("/resume/{opp_id}/tailor-latex", response_model=LatexTailorOut)
async def tailor_resume_latex(
    opp_id: int, user: User = Depends(require_complete_profile), db: AsyncSession = Depends(get_db)
):
    """Edit the student's LaTeX résumé source for this role (bold/add/remove), keeping
    the exact template, and return the tailored .tex."""
    opp = await db.get(Opportunity, opp_id)
    if opp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Opportunity not found")
    profile = (
        await db.execute(select(StudentProfile).where(StudentProfile.user_id == user.id))
    ).scalar_one_or_none()
    if profile is None or not (profile.resume_latex or "").strip():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Add your résumé's LaTeX source in your Profile to tailor it.",
        )

    result = latex_tailor.tailor_latex(
        profile.resume_latex,
        {**opp.as_dict(), "id": opp.id},
        opp.required_skills or [],
        _job_description(opp),
    )
    company = _slug(opp.company_name) or "role"
    result["filename"] = f"resume_{company}.tex"
    await _store_ai_content(user.id, opp_id, "tailored_latex", {"changes": result["changes"]})
    return LatexTailorOut(**result)


@router.post("/cover-letter/{opp_id}", response_model=CoverLetterOut)
async def cover_letter(
    opp_id: int, user: User = Depends(require_complete_profile), db: AsyncSession = Depends(get_db)
):
    opp, profile = await _load(db, user, opp_id)

    # Reuse a cached company summary if research already exists.
    summary = ""
    reports = mongo_collection("company_reports")
    if reports is not None and opp.company_name:
        cached = await reports.find_one({"company_name": opp.company_name})
        if cached:
            summary = cached.get("overview", "")

    result = await cover_letter_gen.generate_and_store(
        user.id, {**opp.as_dict(), "id": opp.id}, profile.resume_parsed, summary
    )

    # Persist URL onto the application if one exists.
    app = (
        await db.execute(
            select(Application).where(
                Application.user_id == user.id, Application.opportunity_id == opp_id
            )
        )
    ).scalar_one_or_none()
    if app and result.get("pdf_url"):
        app.cover_letter_url = result["pdf_url"]
        await db.commit()

    await _store_ai_content(user.id, opp_id, "cover_letter", result)
    return CoverLetterOut(**result)


@router.get("/research/{opp_id}", response_model=ResearchOut)
async def research(
    opp_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    opp = await db.get(Opportunity, opp_id)
    if opp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Opportunity not found")
    if not opp.company_name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Opportunity has no company")
    report = await company_researcher.research_company(opp.company_name, opp_id)
    return ResearchOut(**{k: report.get(k) for k in ResearchOut.model_fields if k in report})


@router.get("/recommend", response_model=CareerAdviceOut)
async def recommend(user: User = Depends(require_complete_profile), db: AsyncSession = Depends(get_db)):
    profile = (
        await db.execute(select(StudentProfile).where(StudentProfile.user_id == user.id))
    ).scalar_one_or_none()
    apps = (
        await db.execute(
            select(Application).where(Application.user_id == user.id)
        )
    ).scalars().all()

    from analytics import student_analytics

    history = [
        {
            "status": a.status,
            "eligibility_status": a.eligibility_status,
            "company_name": a.opportunity.company_name if a.opportunity else None,
            "opportunity_type": a.opportunity.opportunity_type if a.opportunity else None,
            "required_skills": a.opportunity.required_skills if a.opportunity else [],
        }
        for a in apps
    ]
    demand = student_analytics.skill_demand(history)
    advice = career_recommender.recommend(
        profile.as_dict() if profile else {}, history, demand
    )
    return CareerAdviceOut(**advice)


async def _store_ai_content(user_id: int, opp_id: int, content_type: str, data: dict):
    col = mongo_collection("ai_content")
    if col is None:
        return
    doc = {
        "user_id": user_id,
        "opportunity_id": opp_id,
        "type": content_type,
        "content": data,
        "ats_score": data.get("ats_score"),
        "skill_gaps": data.get("skill_gaps"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await col.update_one(
            {"user_id": user_id, "opportunity_id": opp_id, "type": content_type},
            {"$set": doc},
            upsert=True,
        )
    except Exception:  # noqa: BLE001 - analytics persistence is best-effort
        pass
