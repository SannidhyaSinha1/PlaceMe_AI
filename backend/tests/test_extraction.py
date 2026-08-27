"""With no LLM keys the extractor must fall back to heuristics, never crash."""

from ai_agents import llm_client
from fastapi_app.services import pipeline


def test_llm_is_off_in_tests():
    assert llm_client.llm_available() is False


def test_extract_pulls_company_details_from_email():
    data = pipeline.extract(
        "Internship at Acme Corp",
        "Acme Corp is hiring interns.\nRole: Backend Intern\nStipend: 20k/month\n"
        "Deadline: 2026-08-01. Min CGPA 7.5 required. Skills: python, sql.\n"
        "No active backlogs allowed.",
    )
    assert data["opportunity_type"] == "Internship"
    assert data["company_name"] and "Acme" in data["company_name"]
    assert data["deadline"] == "2026-08-01"
    assert data["min_cgpa"] == 7.5
    assert "python" in data["required_skills"]
    assert data["no_backlogs_required"] is True


def test_extract_never_returns_empty_company():
    data = pipeline.extract("XYZ Systems drive", "short body")
    assert data["company_name"]  # subject fallback guarantees a value


def test_signature_lines_do_not_become_the_company():
    data = pipeline.extract(
        "Hackathon registration open",
        "Join our codefest.\n\nWarm regards,\nRanking Committee\n",
    )
    assert data["opportunity_type"] == "Hackathon"
    assert "Ranking Committee" not in (data["company_name"] or "")


def test_invoke_with_fallback_raises_when_unconfigured():
    import pytest

    with pytest.raises(llm_client.LLMUnavailable):
        llm_client.invoke_with_fallback(None, {})
