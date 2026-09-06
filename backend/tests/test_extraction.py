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


# ── Gmail sender filter ───────────────────────────────────────────────────
def test_placement_query_single_and_multi_sender(monkeypatch):
    """One sender is a plain from:; several become an OR group."""
    from fastapi_app.services import gmail_service as gs

    def q(value):
        monkeypatch.setattr(gs.settings, "placement_email_sender", value)
        monkeypatch.setattr(gs.settings, "placement_email_since", "180d")
        return gs._placement_query()

    assert q("helpdesk.cdc@vit.ac.in") == "from:helpdesk.cdc@vit.ac.in newer_than:180d"
    # Multi-word names are phrase-quoted so Gmail does not split them.
    assert q("No Reply CDC Info") == 'from:"No Reply CDC Info" newer_than:180d'
    # Mailing-list mail needs both the display name and the real address.
    assert q("No Reply CDC Info, noreply.cdcinfo@vit.ac.in") == (
        'from:("No Reply CDC Info" OR noreply.cdcinfo@vit.ac.in) newer_than:180d'
    )
