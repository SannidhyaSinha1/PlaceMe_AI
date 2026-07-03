"""Eligibility engine: hard rule checks first, then an XGBoost probability.

Returns {status, reasons, score} where status is one of
'Eligible' / 'Potentially Eligible' / 'Not Eligible'. A hard-rule failure
short-circuits to 'Not Eligible'; otherwise the XGBoost probability decides.
"""

from __future__ import annotations

from ml_models import eligibility_model


def _to_float(v) -> float | None:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _parse_student(student: dict) -> dict:
    return {
        "cgpa": _to_float(student.get("cgpa")),
        "tenth": _to_float(student.get("tenth_pct")),
        "twelfth": _to_float(student.get("twelfth_pct")),
        "year": student.get("current_year"),
        "branch": (student.get("branch") or "").strip(),
        "skills": {s.lower() for s in student.get("skills", []) if isinstance(s, str)},
        "backlogs": student.get("active_backlogs", 0) or 0,
    }


def _hard_rule_reasons(s: dict, criteria: dict) -> list[str]:
    reasons: list[str] = []
    min_cgpa = _to_float(criteria.get("min_cgpa"))
    min_tenth = _to_float(criteria.get("min_tenth"))
    min_twelfth = _to_float(criteria.get("min_twelfth"))
    allowed_branches = criteria.get("allowed_branches") or []
    allowed_years = criteria.get("allowed_years") or []
    no_backlogs = criteria.get("no_backlogs_required")

    if min_cgpa is not None and s["cgpa"] is not None and s["cgpa"] < min_cgpa:
        reasons.append(f"CGPA {s['cgpa']} < required {min_cgpa}")
    if allowed_branches and s["branch"] and not _branch_match(s["branch"], allowed_branches):
        reasons.append(f"Branch '{s['branch']}' not in eligible list {allowed_branches}")
    if allowed_years and s["year"] is not None and s["year"] not in allowed_years:
        reasons.append(f"Year {s['year']} not in eligible years {allowed_years}")
    if min_tenth is not None and s["tenth"] is not None and s["tenth"] < min_tenth:
        reasons.append(f"10th {s['tenth']}% < required {min_tenth}%")
    if min_twelfth is not None and s["twelfth"] is not None and s["twelfth"] < min_twelfth:
        reasons.append(f"12th {s['twelfth']}% < required {min_twelfth}%")
    if no_backlogs and s["backlogs"] > 0:
        reasons.append(f"{s['backlogs']} active backlog(s); none allowed")
    return reasons


def _features(s: dict, criteria: dict) -> list[float]:
    required_skills = criteria.get("required_skills") or []
    skill_match = len(s["skills"] & {sk.lower() for sk in required_skills})
    return [
        (s["cgpa"] or 0) - (_to_float(criteria.get("min_cgpa")) or 0),
        skill_match,
        s["year"] or 2,
        s["tenth"] or 70.0,
        s["twelfth"] or 70.0,
    ]


def _verdict_from_prob(prob: float) -> dict:
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


def check_eligibility(student: dict, criteria: dict) -> dict:
    return check_eligibility_batch(student, [criteria])[0]


def check_eligibility_batch(student: dict, criteria_list: list[dict]) -> list[dict]:
    """Verdicts for one student against many criteria (one model call total).

    Hard-rule failures short-circuit per criteria; the survivors are scored in
    a single vectorized XGBoost call instead of one call per opportunity.
    """
    s = _parse_student(student or {})
    results: list[dict | None] = [None] * len(criteria_list)
    pending_idx: list[int] = []
    pending_features: list[list[float]] = []

    for i, criteria in enumerate(criteria_list):
        criteria = criteria or {}
        reasons = _hard_rule_reasons(s, criteria)
        if reasons:
            results[i] = {"status": "Not Eligible", "reasons": reasons, "score": 0.0}
        else:
            pending_idx.append(i)
            pending_features.append(_features(s, criteria))

    for i, prob in zip(
        pending_idx, eligibility_model.predict_proba_batch(pending_features), strict=True
    ):
        results[i] = _verdict_from_prob(prob)
    return results


def _branch_match(branch: str, allowed: list[str]) -> bool:
    b = branch.lower()
    return any(a.lower() in b or b in a.lower() for a in allowed)
