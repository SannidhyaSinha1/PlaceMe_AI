"""Career recommendation engine: profile + skills + history → guidance.

LangChain + Groq with PydanticOutputParser (rule #7). Degrades to heuristic
recommendations derived from the most in-demand skills across opportunities.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from ai_agents import llm_client

logger = logging.getLogger(__name__)


class CareerAdvice(BaseModel):
    summary: str = Field("", description="2-3 sentence personalized assessment")
    target_companies: list[str] = Field(default_factory=list)
    skills_to_learn: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    project_ideas: list[str] = Field(default_factory=list)
    hackathons: list[str] = Field(default_factory=list)


def recommend(profile: dict, history: list[dict], skill_demand: list[dict]) -> dict:
    if llm_client.llm_available():
        try:
            from langchain.output_parsers import PydanticOutputParser
            from langchain.prompts import PromptTemplate

            parser = PydanticOutputParser(pydantic_object=CareerAdvice)

            def build(llm):
                prompt = PromptTemplate(
                    template=(
                        "You are a career counselor for engineering students. Based on "
                        "the student's profile, their application history, and current "
                        "market skill demand, recommend: target companies, skills to "
                        "learn, certifications, project ideas, and hackathons to join. "
                        "Be specific and realistic. Return ONLY JSON.\n\n"
                        "PROFILE: {profile}\nHISTORY: {history}\nSKILL DEMAND: {demand}\n\n"
                        "{format_instructions}"
                    ),
                    input_variables=["profile", "history", "demand"],
                    partial_variables={"format_instructions": parser.get_format_instructions()},
                )
                return prompt | llm | parser

            advice: CareerAdvice = llm_client.invoke_with_fallback(
                None,
                {
                    "profile": str(profile)[:2000],
                    "history": str(history)[:2000],
                    "demand": str(skill_demand)[:1000],
                    "_build": build,
                },
            )
            return advice.model_dump()
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM career advice failed: %s", exc)

    return _heuristic(profile, skill_demand)


def _heuristic(profile: dict, skill_demand: list[dict]) -> dict:
    have = {s.lower() for s in (profile or {}).get("skills", [])}
    demanded = [d["skill"] for d in skill_demand if d.get("skill")]
    to_learn = [s for s in demanded if s.lower() not in have][:6]
    return CareerAdvice(
        summary=(
            "Keep applying consistently and close the highlighted skill gaps to "
            "strengthen your eligibility for top roles."
        ),
        skills_to_learn=to_learn,
        certifications=["AWS Cloud Practitioner", "Google Data Analytics"],
        project_ideas=[
            "Build a full-stack app showcasing your top skill",
            "Contribute to an open-source project in your domain",
        ],
        hackathons=["Smart India Hackathon", "MLH member events"],
    ).model_dump()
