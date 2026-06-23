"""Eligibility engine: hard rule checks first, then an XGBoost probability.

Returns {status, reasons, score} where status is one of
'Eligible' / 'Potentially Eligible' / 'Not Eligible'. A hard-rule failure
short-circuits to 'Not Eligible'; otherwise the XGBoost probability decides.
"""

from __future__ import annotations

from typing import Optional

from ml_models import eligibility_model


def _to_float(v) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def check_eligibility(student: dict, criteria: dict) -> dict:
    reasons: list[str] = []
    criteria = criteria or {}
    student = student or {}

    cgpa = _to_float(student.get("cgpa"))
    tenth = _to_float(student.get("tenth_pct"))
    twelfth = _to_float(student.get("twelfth_pct"))
    year = student.get("current_year")
    branch = (student.get("branch") or "").strip()
    skills = {s.lower() for s in student.get("skills", []) if isinstance(s, str)}
    backlogs = student.get("active_backlogs", 0) or 0

    min_cgpa = _to_float(criteria.get("min_cgpa"))
    min_tenth = _to_float(criteria.get("min_tenth"))
    min_twelfth = _to_float(criteria.get("min_twelfth"))
    allowed_branches = criteria.get("allowed_branches") or []
    allowed_years = criteria.get("allowed_years") or []
    required_skills = criteria.get("required_skills") or []
    no_backlogs = criteria.get("no_backlogs_required")

    # ── Hard rule checks ──────────────────────────────────────────────
    if min_cgpa is not None and cgpa is not None and cgpa < min_cgpa:
        reasons.append(f"CGPA {cgpa} < required {min_cgpa}")
    if allowed_branches and branch and not _branch_match(branch, allowed_branches):
        reasons.append(f"Branch '{branch}' not in eligible list {allowed_branches}")
    if allowed_years and year is not None and year not in allowed_years:
        reasons.append(f"Year {year} not in eligible years {allowed_years}")
    if min_tenth is not None and tenth is not None and tenth < min_tenth:
        reasons.append(f"10th {tenth}% < required {min_tenth}%")
    if min_twelfth is not None and twelfth is not None and twelfth < min_twelfth:
        reasons.append(f"12th {twelfth}% < required {min_twelfth}%")
    if no_backlogs and backlogs > 0:
        reasons.append(f"{backlogs} active backlog(s); none allowed")

    if reasons:
        return {"status": "Not Eligible", "reasons": reasons, "score": 0.0}

    # ── Probabilistic score for grey-area cases ───────────────────────
    skill_match = len(skills & {s.lower() for s in required_skills})
    features = [
        (cgpa or 0) - (min_cgpa or 0),
        skill_match,
        year or 2,
        tenth or 70.0,
        twelfth or 70.0,
    ]
    prob = eligibility_model.predict_proba(features)

    if prob >= 0.75:
        return {"status": "Eligible", "reasons": ["Meets all criteria"], "score": round(prob, 3)}
    if prob >= 0.40:
        return {
            "status": "Potentially Eligible",
            "reasons": ["Borderline match — verify with the placement cell"],
            "score": round(prob, 3),
        }
    return {
        "status": "Not Eligible",
        "reasons": ["Low eligibility probability for this profile"],
        "score": round(prob, 3),
    }


def _branch_match(branch: str, allowed: list[str]) -> bool:
    b = branch.lower()
    return any(a.lower() in b or b in a.lower() for a in allowed)
