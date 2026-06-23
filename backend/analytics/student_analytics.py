"""pandas-based analytics over a student's applications.

`rows` are plain dicts (status, eligibility_status, opportunity_type,
required_skills, deadline) so this works whether data comes from SQLAlchemy
objects or a Celery context.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from typing import Iterable


def compute_dashboard(rows: list[dict]) -> dict:
    import pandas as pd

    if not rows:
        return {
            "stats": {"eligible": 0, "applied": 0, "offers": 0, "total": 0, "success_rate": 0.0},
            "status_counts": {},
            "skill_demand": [],
            "upcoming_deadlines": [],
        }

    df = pd.DataFrame(rows)

    applied_states = {"Applied", "Assessment Scheduled", "Interview Scheduled", "Offer Received"}
    applied = int(df["status"].isin(applied_states).sum()) if "status" in df else 0
    offers = int((df.get("status") == "Offer Received").sum()) if "status" in df else 0
    eligible = int((df.get("eligibility_status") == "Eligible").sum()) if "eligibility_status" in df else 0
    success_rate = round((offers / applied * 100), 1) if applied else 0.0

    status_counts = (
        df["status"].value_counts().to_dict() if "status" in df else {}
    )

    return {
        "stats": {
            "eligible": eligible,
            "applied": applied,
            "offers": offers,
            "total": len(df),
            "success_rate": success_rate,
        },
        "status_counts": {k: int(v) for k, v in status_counts.items()},
        "skill_demand": skill_demand(rows),
        "upcoming_deadlines": upcoming_deadlines(rows),
    }


def skill_demand(rows: Iterable[dict], top: int = 10) -> list[dict]:
    counter: Counter = Counter()
    for r in rows:
        for skill in r.get("required_skills") or []:
            if skill:
                counter[str(skill).strip().lower()] += 1
    return [{"skill": k, "count": v} for k, v in counter.most_common(top)]


def skill_gap_demand(rows: Iterable[dict], student_skills: list[str], top: int = 10) -> list[dict]:
    """Most-demanded skills the student does NOT yet have."""
    have = {s.lower() for s in (student_skills or [])}
    counter: Counter = Counter()
    for r in rows:
        for skill in r.get("required_skills") or []:
            s = str(skill).strip().lower()
            if s and s not in have:
                counter[s] += 1
    return [{"skill": k, "count": v} for k, v in counter.most_common(top)]


def upcoming_deadlines(rows: Iterable[dict], top: int = 5) -> list[dict]:
    today = date.today()
    items = []
    for r in rows:
        dl = r.get("deadline")
        if isinstance(dl, str):
            try:
                dl = datetime.fromisoformat(dl).date()
            except ValueError:
                dl = None
        if isinstance(dl, datetime):
            dl = dl.date()
        if isinstance(dl, date) and dl >= today:
            items.append(
                {
                    "company_name": r.get("company_name"),
                    "role": r.get("role"),
                    "deadline": dl.isoformat(),
                    "days_left": (dl - today).days,
                }
            )
    items.sort(key=lambda x: x["days_left"])
    return items[:top]
