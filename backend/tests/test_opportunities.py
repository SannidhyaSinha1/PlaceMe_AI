"""Opportunities list: filters, search, sort, eligibility enrichment, caps."""

import pytest


@pytest.fixture
async def seeded(client, admin):
    """Three opportunities with distinct types/criteria."""
    specs = [
        {"company_name": "Alpha Analytics", "role": "Data Intern",
         "opportunity_type": "Internship",
         "eligibility_criteria": {"min_cgpa": 7.0, "required_skills": ["python"]}},
        {"company_name": "Beta Bank", "role": "Quant",
         "opportunity_type": "Full-Time Placement",
         "eligibility_criteria": {"min_cgpa": 9.9}},
        {"company_name": "Gamma Games", "role": "Hack Night",
         "opportunity_type": "Hackathon", "eligibility_criteria": {}},
    ]
    ids = []
    for s in specs:
        r = await client.post("/opportunities", json=s, headers=admin["headers"])
        assert r.status_code == 201, r.text
        ids.append(r.json()["id"])
    return ids


async def test_list_enriches_eligibility(client, student, seeded):
    r = await client.get("/opportunities?limit=200", headers=student["headers"])
    assert r.status_code == 200
    by_company = {o["company_name"]: o for o in r.json()}
    # 8.5 CGPA student: eligible for Alpha, hard-blocked by Beta's 9.9 bar.
    assert by_company["Alpha Analytics"]["eligibility"]["status"] == "Eligible"
    assert by_company["Beta Bank"]["eligibility"]["status"] == "Not Eligible"


async def test_type_filter_and_search(client, student, seeded):
    r = await client.get(
        "/opportunities", params={"type": "Hackathon"}, headers=student["headers"]
    )
    assert {o["opportunity_type"] for o in r.json()} <= {"Hackathon"}

    r = await client.get(
        "/opportunities", params={"search": "beta"}, headers=student["headers"]
    )
    names = [o["company_name"] for o in r.json()]
    assert "Beta Bank" in names and "Alpha Analytics" not in names


async def test_eligible_only_filter(client, student, seeded):
    r = await client.get(
        "/opportunities?eligible_only=true&limit=200", headers=student["headers"]
    )
    assert all(
        o["eligibility"]["status"] in ("Eligible", "Potentially Eligible")
        for o in r.json()
    )


async def test_missing_profile_row_gets_unknown(client, seeded):
    """Registration auto-creates an (empty) profile row, so fresh users get
    computed verdicts; only a truly missing row yields 'Unknown'."""
    r = await client.post(
        "/auth/register", json={"email": "noprof@test.co", "password": "test-password-123"}
    )
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # Fresh user (empty profile row): still gets a computed verdict per row.
    r = await client.get("/opportunities?limit=200", headers=headers)
    assert r.status_code == 200
    valid = {"Eligible", "Potentially Eligible", "Not Eligible", "Unknown"}
    assert all(o["eligibility"]["status"] in valid for o in r.json())

    # Remove the profile row entirely → every verdict becomes 'Unknown'.
    from sqlalchemy import delete, select

    from fastapi_app.core.database import SessionLocal
    from fastapi_app.models.sql_models import StudentProfile, User

    async with SessionLocal() as session:
        uid = (
            await session.execute(select(User.id).where(User.email == "noprof@test.co"))
        ).scalar_one()
        await session.execute(delete(StudentProfile).where(StudentProfile.user_id == uid))
        await session.commit()

    r = await client.get("/opportunities?limit=200", headers=headers)
    assert r.status_code == 200
    assert all(o["eligibility"]["status"] == "Unknown" for o in r.json())


async def test_query_validation_caps(client, student):
    assert (
        await client.get(
            "/opportunities", params={"search": "x" * 300}, headers=student["headers"]
        )
    ).status_code == 422
    assert (
        await client.get(
            "/opportunities", params={"limit": 500}, headers=student["headers"]
        )
    ).status_code == 422
    assert (
        await client.get(
            "/opportunities", params={"offset": -1}, headers=student["headers"]
        )
    ).status_code == 422


async def test_non_admin_cannot_create(client, student):
    r = await client.post(
        "/opportunities", json={"company_name": "Nope"}, headers=student["headers"]
    )
    assert r.status_code == 403
