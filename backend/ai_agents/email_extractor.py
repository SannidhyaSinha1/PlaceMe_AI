"""Email → structured OpportunityExtract via LangChain + Groq + PydanticOutputParser.

Per implementation-rule #7 we never hand-parse LLM text: the chain is
`prompt | llm | PydanticOutputParser`. When no LLM is configured we fall back
to a lightweight regex/keyword extractor so the pipeline still produces useful
rows offline.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from ai_agents import llm_client

logger = logging.getLogger(__name__)

OPPORTUNITY_TYPE_VALUES = (
    "Internship, Full-Time Placement, Hackathon, Competition, "
    "Workshop, Scholarship, Other"
)


class OpportunityExtract(BaseModel):
    company_name: Optional[str] = Field(None, description="Hiring company / organiser")
    role: Optional[str] = Field(None, description="Job title or role")
    opportunity_type: str = Field(
        "Other", description=f"One of: {OPPORTUNITY_TYPE_VALUES}"
    )
    deadline: Optional[str] = Field(None, description="Application deadline YYYY-MM-DD")
    salary_stipend: Optional[str] = Field(None, description="Salary or stipend text")
    job_location: Optional[str] = None
    required_skills: List[str] = Field(default_factory=list)
    min_cgpa: Optional[float] = None
    allowed_branches: Optional[List[str]] = None
    allowed_years: Optional[List[int]] = None
    min_tenth: Optional[float] = None
    min_twelfth: Optional[float] = None
    no_backlogs_required: Optional[bool] = None
    summary: Optional[str] = Field(None, description="One-line summary")

    @field_validator("required_skills", mode="before")
    @classmethod
    def _coerce_skills(cls, v):
        """LLMs often return null / a comma string for an absent skills list."""
        if v is None:
            return []
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v


_PROMPT_TEMPLATE = """You are a placement-cell assistant. Extract ALL opportunity
details from the email below. Return ONLY valid JSON. Use null for anything not
stated; never invent values. Dates must be YYYY-MM-DD.

Subject: {subject}
Body:
{body}

{format_instructions}"""


def _build_chain(llm):
    from langchain.output_parsers import PydanticOutputParser
    from langchain.prompts import PromptTemplate

    parser = PydanticOutputParser(pydantic_object=OpportunityExtract)
    prompt = PromptTemplate(
        template=_PROMPT_TEMPLATE,
        input_variables=["subject", "body"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    return prompt | llm | parser


def extract_from_email(
    subject: str, body: str, *, allow_heuristic: bool = True
) -> OpportunityExtract:
    """Return structured fields; LLM when available, regex heuristics otherwise.

    Set ``allow_heuristic=False`` (used by the re-extraction backfill) to raise
    ``LLMUnavailable`` instead of silently degrading, so callers don't overwrite
    good rows with low-quality heuristic output when the LLM is merely
    rate-limited.
    """
    if llm_client.llm_available():
        try:
            payload = {
                "subject": subject or "",
                "body": (body or "")[:8000],
                "_build": _build_chain,
            }
            return llm_client.invoke_with_fallback(None, payload)
        except Exception as exc:  # noqa: BLE001 - fall through to heuristics
            if not allow_heuristic:
                raise
            logger.warning("LLM extraction failed (%s); using heuristics", exc)
    elif not allow_heuristic:
        raise llm_client.LLMUnavailable("No LLM configured")
    return _heuristic_extract(subject or "", body or "")


# ── Offline heuristic fallback ────────────────────────────────────────────
_TYPE_KEYWORDS = {
    "Internship": ["intern", "internship", "summer training"],
    "Full-Time Placement": ["full-time", "full time", "placement", "campus drive", "fte"],
    "Hackathon": ["hackathon", "hack ", "codefest"],
    "Competition": ["competition", "contest", "challenge", "coding round"],
    "Workshop": ["workshop", "webinar", "bootcamp", "session"],
    "Scholarship": ["scholarship", "fellowship", "grant"],
}

_SKILL_VOCAB = [
    "python", "java", "c++", "javascript", "typescript", "react", "node", "sql",
    "machine learning", "deep learning", "nlp", "data science", "aws", "docker",
    "kubernetes", "django", "flask", "fastapi", "spring", "go", "rust", "html",
    "css", "tensorflow", "pytorch", "pandas", "numpy", "excel", "tableau",
]

_DATE_PATTERNS = [
    (r"(\d{4})-(\d{2})-(\d{2})", "%Y-%m-%d"),
    (r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", "%d/%m/%Y"),
    (r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})", "%d %B %Y"),
    (r"([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})", "%B %d %Y"),
]

# Lines at/after which the meaningful email content has ended — signatures and
# quoted replies, where stray capitalised tokens (e.g. "World University
# Rankings by Subject 2026") used to be mis-read as the company name.
_SIGNATURE_MARKERS = re.compile(
    r"(?im)^[ \t>*]*(?:--\s*$|warm regards|best regards|kind regards|regards[,.]?\s*$"
    r"|thanks (?:&|and) regards|thanks[,.]?\s*$|sincerely|director\s*\("
    r"|on .{0,80}\bwrote:|-{2,}\s*forwarded message|from:\s|sent from "
    r"|world university rankings|unsubscribe)"
)

# Tokens that are never a company name on their own.
_COMPANY_STOPWORDS = {
    "subject", "world", "university", "rankings", "ranking", "the", "a", "an",
    "registration", "batch", "hackathon", "competition", "internship", "placement",
    "workshop", "scholarship", "drive", "update", "reminder", "regarding",
    "invitation", "webinar", "important", "attention", "fwd", "re", "kind",
    "dear", "team", "notice", "announcement",
}


def _strip_signature_and_quotes(body: str) -> str:
    """Keep only the meaningful top of an email, dropping signatures / quoted replies."""
    if not body:
        return ""
    m = _SIGNATURE_MARKERS.search(body)
    return body[: m.start()] if m else body


def _company_from_subject(subject: str) -> Optional[str]:
    """Leading capitalised proper-noun run of the subject, minus Re:/Fwd: and junk."""
    s = re.sub(r"(?i)^\s*(?:re|fwd|fw)\s*:\s*", "", subject or "").strip()
    picked: list[str] = []
    for w in re.findall(r"[A-Za-z0-9&.\-]+", s):
        if re.match(r"[A-Z][A-Za-z0-9&.\-]*$", w) and w.lower() not in _COMPANY_STOPWORDS:
            picked.append(w)
        elif picked:
            break
    return " ".join(picked[:4]) or None


def _extract_company(subject: str, text: str) -> Optional[str]:
    """Company from a '<lead-in> <Proper Noun>' phrase, else the subject's name run.

    'by'/'from' are deliberately omitted as lead-ins — they matched signature
    lines like '...Rankings by Subject 2026'.
    """
    # [ \t] (not \s) so the match never spills across a line break.
    m = re.search(
        r"\b(?:at|with|join|hiring for)[ \t]+"
        r"([A-Z][A-Za-z0-9&.\-]+(?:[ \t]+[A-Z][A-Za-z0-9&.\-]+){0,2})",
        text,
    )
    if m:
        cand = re.sub(r"\s+", " ", m.group(1)).strip(" .,-")
        if cand and cand.split()[0].lower() not in _COMPANY_STOPWORDS:
            return cand
    return _company_from_subject(subject)


def _heuristic_extract(subject: str, body: str) -> OpportunityExtract:
    # Read only the meaningful top of the email so signatures/footers can't
    # pollute company/role/skill detection.
    intro = _strip_signature_and_quotes(body)
    text = f"{subject}\n{intro}"
    low = text.lower()

    opp_type = "Other"
    for label, kws in _TYPE_KEYWORDS.items():
        if any(k in low for k in kws):
            opp_type = label
            break

    company = _extract_company(subject, text)

    role = None
    m = re.search(r"\b(?:role|position|hiring for|opening for)[:\- ]+([A-Za-z][A-Za-z0-9/ ]{2,49})", low)
    if m:
        role = m.group(1).strip().title()

    deadline = _find_date(text)
    min_cgpa = _find_float(low, [r"cgpa[^0-9]{0,12}(\d{1,2}(?:\.\d{1,2})?)",
                                 r"(\d{1,2}(?:\.\d{1,2})?)\s*(?:\+\s*)?cgpa"])
    min_tenth = _find_float(low, [r"10th[^0-9]{0,12}(\d{1,3}(?:\.\d{1,2})?)",
                                  r"tenth[^0-9]{0,12}(\d{1,3}(?:\.\d{1,2})?)"])
    min_twelfth = _find_float(low, [r"12th[^0-9]{0,12}(\d{1,3}(?:\.\d{1,2})?)",
                                    r"twelfth[^0-9]{0,12}(\d{1,3}(?:\.\d{1,2})?)"])

    skills = [s for s in _SKILL_VOCAB if re.search(rf"\b{re.escape(s)}\b", low)]
    no_backlog = bool(re.search(r"no\s+(?:active\s+)?backlog", low))

    salary = None
    m = re.search(r"(?:stipend|salary|ctc|package)[:\- ]*([₹$]?\s?[\d.,]+\s?(?:lpa|k|per month|/month|lakhs?)?)", low)
    if m:
        salary = m.group(1).strip()

    return OpportunityExtract(
        company_name=company,
        role=role,
        opportunity_type=opp_type,
        deadline=deadline,
        salary_stipend=salary,
        required_skills=skills,
        min_cgpa=min_cgpa,
        min_tenth=min_tenth,
        min_twelfth=min_twelfth,
        no_backlogs_required=no_backlog or None,
        summary=(subject or body[:80]).strip()[:120],
    )


def _find_date(text: str) -> Optional[str]:
    for pattern, fmt in _DATE_PATTERNS:
        m = re.search(pattern, text)
        if not m:
            continue
        try:
            parsed = datetime.strptime(" ".join(m.groups()), fmt.replace("/", " ").replace("-", " "))
            return parsed.date().isoformat()
        except (ValueError, TypeError):
            continue
    return None


def _find_float(text: str, patterns: list[str]) -> Optional[float]:
    for p in patterns:
        m = re.search(p, text)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                continue
    return None
