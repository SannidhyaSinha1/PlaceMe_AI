"""With no LLM keys the pipeline must fall back to heuristics, never crash."""

from ai_agents import classifier, llm_client
from fastapi_app.services import pipeline


def test_llm_is_off_in_tests():
    assert llm_client.llm_available() is False


def test_extract_and_classify_heuristic():
    data = pipeline.extract_and_classify(
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
    assert data["classification"]["method"] == "keyword"


def test_extract_never_returns_empty_company():
    data = pipeline.extract_and_classify("XYZ Systems drive", "short body")
    assert data["company_name"]  # subject fallback guarantees a value


def test_classifier_keyword_fallback():
    out = classifier.classify("Hackathon registration open", "join our codefest")
    assert out["label"] == "Hackathon"
    assert out["method"] == "keyword"


def test_classifier_empty_text():
    out = classifier.classify("", "")
    assert out["label"] == "Other"


async def test_ai_extract_endpoint_heuristic(client, student):
    r = await client.post(
        "/ai/extract",
        json={"subject": "Workshop on Docker", "body": "A hands-on docker workshop."},
        headers=student["headers"],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["opportunity_type"] == "Workshop"


def test_invoke_with_fallback_raises_when_unconfigured():
    import pytest

    with pytest.raises(llm_client.LLMUnavailable):
        llm_client.invoke_with_fallback(None, {})
