"""Resume optimizer: ATS score (deterministic) + LLM skill-gap suggestions.

The ATS score uses the exact formula from implementation-rule #8:
    round((len(matched_keywords) / len(jd_keywords)) * 100)
where matched = intersection of resume tokens and JD keyword tokens. The LLM
only adds qualitative suggestions/summary; the number is never left to the LLM.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from pydantic import BaseModel, Field

from ai_agents import llm_client

logger = logging.getLogger(__name__)

_STOPWORDS = {
    "the", "and", "for", "with", "you", "your", "are", "our", "will", "have",
    "this", "that", "from", "who", "all", "any", "can", "has", "was", "were",
    "a", "an", "in", "on", "of", "to", "is", "as", "at", "be", "or", "by",
    "we", "us", "it", "its", "their", "they", "them", "should", "must", "able",
    "experience", "work", "team", "role", "skills", "knowledge", "strong",
    "good", "excellent", "ability", "candidate", "looking", "join", "year",
    "years", "plus", "etc", "using", "build", "design", "develop", "company",
}

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z+#.]{1,}")


def _tokens(text: str) -> set[str]:
    return {
        t.lower()
        for t in _TOKEN_RE.findall(text or "")
        if len(t) > 2 and t.lower() not in _STOPWORDS
    }


def _jd_keywords(job_description: str, required_skills: list[str]) -> set[str]:
    kws = _tokens(job_description)
    for s in required_skills or []:
        kws.update(_tokens(s))
    return kws


def _resume_text(resume: dict) -> str:
    """Flatten the parsed-resume JSON into a single searchable blob."""
    parts: list[str] = []
    for value in (resume or {}).values():
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            parts.extend(str(v) for v in value)
        elif isinstance(value, dict):
            parts.extend(str(v) for v in value.values())
    return " ".join(parts)


class ResumeAnalysis(BaseModel):
    suggestions: list[str] = Field(default_factory=list)
    tailored_summary: Optional[str] = None


def analyze_resume(resume: dict, job_description: str, required_skills: list[str]) -> dict:
    """Return ATS score, matched/missing keywords, skill gaps, suggestions."""
    jd_kws = _jd_keywords(job_description, required_skills)
    resume_tokens = _tokens(_resume_text(resume))
    resume_skills = {s.lower() for s in (resume or {}).get("skills", []) if isinstance(s, str)}
    resume_tokens |= resume_skills

    matched = sorted(jd_kws & resume_tokens)
    missing = sorted(jd_kws - resume_tokens)
    ats_score = round((len(matched) / len(jd_kws)) * 100) if jd_kws else 0

    # Skill gaps: required skills the resume does not mention.
    skill_gaps = [
        s for s in (required_skills or [])
        if not any(tok in resume_tokens for tok in _tokens(s))
    ]

    suggestions, summary = _llm_suggestions(resume, job_description, missing, skill_gaps)

    return {
        "ats_score": ats_score,
        "matched_keywords": matched[:40],
        "missing_keywords": missing[:40],
        "skill_gaps": skill_gaps,
        "suggestions": suggestions,
        "tailored_summary": summary,
    }


def _llm_suggestions(resume, jd, missing, gaps) -> tuple[list[str], Optional[str]]:
    if not llm_client.llm_available():
        fallback = [
            f"Add the missing keyword '{kw}' if you have relevant experience."
            for kw in missing[:5]
        ]
        if gaps:
            fallback.append("Consider upskilling in: " + ", ".join(gaps[:5]))
        return fallback or ["Resume already covers the main JD keywords."], None

    try:
        from langchain.output_parsers import PydanticOutputParser
        from langchain.prompts import PromptTemplate

        parser = PydanticOutputParser(pydantic_object=ResumeAnalysis)

        def build(llm):
            prompt = PromptTemplate(
                template=(
                    "You are an ATS resume coach. Given the parsed resume, the job "
                    "description, and the missing keywords, write up to 6 concrete "
                    "improvement suggestions and a 2-sentence tailored professional "
                    "summary. Return ONLY JSON.\n\n"
                    "RESUME: {resume}\nJOB DESCRIPTION: {jd}\nMISSING KEYWORDS: {missing}\n"
                    "SKILL GAPS: {gaps}\n\n{format_instructions}"
                ),
                input_variables=["resume", "jd", "missing", "gaps"],
                partial_variables={"format_instructions": parser.get_format_instructions()},
            )
            return prompt | llm | parser

        result: ResumeAnalysis = llm_client.invoke_with_fallback(
            None,
            {
                "resume": str(resume)[:3000],
                "jd": (jd or "")[:3000],
                "missing": ", ".join(missing[:25]),
                "gaps": ", ".join(gaps),
                "_build": build,
            },
        )
        return result.suggestions, result.tailored_summary
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM resume suggestions failed: %s", exc)
        return [f"Add experience demonstrating: {kw}" for kw in missing[:5]], None
