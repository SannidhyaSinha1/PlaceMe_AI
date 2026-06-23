"""Resume PDF → structured JSON using pdfplumber + regex section heuristics."""

from __future__ import annotations

import io
import logging
import re

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s-]?)?\b\d{10}\b")
_LINK_RE = re.compile(r"(https?://[^\s]+|linkedin\.com/[^\s]+|github\.com/[^\s]+)", re.I)

_SECTION_HEADS = {
    "education": ["education", "academic"],
    "experience": ["experience", "employment", "work history", "internship"],
    "projects": ["projects", "project work"],
    "skills": ["skills", "technical skills", "technologies", "core competencies"],
    "certifications": ["certifications", "certificates", "courses"],
    "achievements": ["achievements", "awards", "honors"],
}

_SKILL_VOCAB = [
    "python", "java", "c++", "c", "javascript", "typescript", "react", "angular",
    "vue", "node", "express", "django", "flask", "fastapi", "spring", "sql",
    "postgresql", "mysql", "mongodb", "redis", "aws", "gcp", "azure", "docker",
    "kubernetes", "git", "linux", "machine learning", "deep learning", "nlp",
    "tensorflow", "pytorch", "pandas", "numpy", "scikit-learn", "tableau",
    "power bi", "excel", "html", "css", "tailwind", "go", "rust", "kotlin",
    "swift", "php", "ruby", "graphql", "rest", "kafka", "spark", "hadoop",
]


def extract_text(file_bytes: bytes) -> str:
    try:
        import pdfplumber

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            return "\n".join((page.extract_text() or "") for page in pdf.pages)
    except Exception as exc:  # noqa: BLE001
        logger.warning("pdfplumber extraction failed: %s", exc)
        return ""


def parse_resume(file_bytes: bytes) -> dict:
    text = extract_text(file_bytes)
    if not text.strip():
        return {"raw_text": "", "skills": [], "sections": {}}

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    email = _first(_EMAIL_RE, text)
    phone = _first(_PHONE_RE, text)
    links = _LINK_RE.findall(text)
    name = _guess_name(lines, email)

    sections = _split_sections(lines)
    skills = _extract_skills(text, sections.get("skills", ""))

    return {
        "name": name,
        "email": email,
        "phone": phone,
        "links": list(dict.fromkeys(links))[:5],
        "skills": skills,
        "sections": sections,
        "raw_text": text[:20000],
    }


def _first(pattern: re.Pattern, text: str):
    m = pattern.search(text)
    return m.group(0) if m else None


def _guess_name(lines: list[str], email: str | None) -> str | None:
    for ln in lines[:4]:
        if email and email in ln:
            continue
        words = ln.split()
        if 1 < len(words) <= 4 and all(w[:1].isupper() for w in words if w[:1].isalpha()):
            if not _EMAIL_RE.search(ln) and not _PHONE_RE.search(ln):
                return ln
    return lines[0] if lines else None


def _split_sections(lines: list[str]) -> dict:
    sections: dict[str, list[str]] = {}
    current = "header"
    sections[current] = []
    for ln in lines:
        low = ln.lower().strip(" :")
        matched = next(
            (key for key, heads in _SECTION_HEADS.items()
             if any(low == h or low.startswith(h) for h in heads) and len(ln) < 40),
            None,
        )
        if matched:
            current = matched
            sections.setdefault(current, [])
        else:
            sections.setdefault(current, []).append(ln)
    return {k: "\n".join(v).strip() for k, v in sections.items() if v}


def _extract_skills(full_text: str, skills_section: str) -> list[str]:
    haystack = (skills_section or full_text).lower()
    found = [s for s in _SKILL_VOCAB if re.search(rf"(?<![a-z]){re.escape(s)}(?![a-z])", haystack)]
    # Also pull comma/bullet separated tokens from a dedicated skills section.
    if skills_section:
        for tok in re.split(r"[,•|\n;]", skills_section):
            tok = tok.strip()
            if 1 < len(tok) <= 25 and tok.lower() not in found and tok[0].isalnum():
                found.append(tok.lower())
    return list(dict.fromkeys(found))[:40]
