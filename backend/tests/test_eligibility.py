"""Eligibility engine: hard rules, scoring bands, and batch/single parity."""

from fastapi_app.services.eligibility_engine import (
    check_eligibility,
    check_eligibility_batch,
)

STRONG = {
    "cgpa": 9.0, "tenth_pct": 92, "twelfth_pct": 90, "current_year": 3,
    "branch": "CSE", "skills": ["python", "sql", "react"], "active_backlogs": 0,
}


def test_hard_rule_cgpa():
    out = check_eligibility({**STRONG, "cgpa": 6.0}, {"min_cgpa": 7.0})
    assert out["status"] == "Not Eligible"
    assert out["score"] == 0.0
    assert any("CGPA" in r for r in out["reasons"])


def test_hard_rule_branch_and_year_and_backlogs():
    out = check_eligibility(
        {**STRONG, "branch": "Mechanical", "current_year": 1, "active_backlogs": 2},
        {"allowed_branches": ["CSE", "IT"], "allowed_years": [3, 4],
         "no_backlogs_required": True},
    )
    assert out["status"] == "Not Eligible"
    assert len(out["reasons"]) == 3


def test_branch_match_is_fuzzy():
    out = check_eligibility(
        {**STRONG, "branch": "Computer Science (CSE)"}, {"allowed_branches": ["CSE"]}
    )
    assert out["status"] != "Not Eligible" or "Branch" not in " ".join(out["reasons"])


def test_strong_profile_eligible():
    out = check_eligibility(STRONG, {"min_cgpa": 7.0, "required_skills": ["python", "sql"]})
    assert out["status"] == "Eligible"
    assert out["score"] >= 0.75


def test_missing_criteria_fields_are_ignored():
    out = check_eligibility(STRONG, {})
    assert out["status"] in ("Eligible", "Potentially Eligible", "Not Eligible")
    assert out["score"] is not None


def test_batch_matches_single():
    criteria_list = [
        {}, {"min_cgpa": 9.5}, {"allowed_branches": ["EEE"]},
        {"required_skills": ["python", "go", "rust"]},
        {"min_tenth": 95, "min_twelfth": 95}, {"no_backlogs_required": True},
    ]
    batch = check_eligibility_batch(STRONG, criteria_list)
    singles = [check_eligibility(STRONG, c) for c in criteria_list]
    assert batch == singles


def test_batch_empty():
    assert check_eligibility_batch(STRONG, []) == []
