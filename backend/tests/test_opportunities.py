"""Opportunities listing: filters, search, sort, query caps."""

import pytest
from sqlalchemy import delete

from fastapi_app.core.database import SessionLocal
from fastapi_app.models.sql_models import Opportunity


@pytest.fixture
async def seeded():
    """Three parsed opportunities with distinct types."""
    specs = [
        {"company_name": "Alpha Analytics", "role": "Data Intern",
         "opportunity_type": "Internship", "required_skills": ["python"]},
        {"company_name": "Beta Bank", "role": "Quant",
         "opportunity_type": "Full-Time Placement", "required_skills": []},
        {"company_name": "Gamma Games", "role": "Hack Night",
         "opportunity_type": "Hackathon", "required_skills": []},
    ]
    async with SessionLocal() as session:
        rows = [Opportunity(source_email_id=f"seed-{i}", **s) for i, s in enumerate(specs)]
        session.add_all(rows)
        await session.commit()
        ids = [r.id for r in rows]
    yield ids
    async with SessionLocal() as session:
        await session.execute(delete(Opportunity).where(Opportunity.id.in_(ids)))
        await session.commit()


async def test_list_returns_parsed_details(client, student, seeded):
    r = await client.get("/opportunities?limit=200", headers=student["headers"])
    assert r.status_code == 200
    by_company = {o["company_name"]: o for o in r.json()}
    assert by_company["Alpha Analytics"]["role"] == "Data Intern"
    assert by_company["Alpha Analytics"]["required_skills"] == ["python"]
    # Parsed from an email → a deep link back to that message.
    assert by_company["Alpha Analytics"]["email_link"].startswith("https://mail.google.com/")


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


async def test_get_one_and_404(client, student, seeded):
    r = await client.get(f"/opportunities/{seeded[0]}", headers=student["headers"])
    assert r.status_code == 200
    assert r.json()["company_name"] == "Alpha Analytics"

    r = await client.get("/opportunities/99999", headers=student["headers"])
    assert r.status_code == 404


async def test_email_requires_gmail_connection(client, student, seeded):
    r = await client.get(f"/opportunities/{seeded[0]}/email", headers=student["headers"])
    assert r.status_code == 400


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
