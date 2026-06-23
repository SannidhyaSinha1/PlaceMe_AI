"""Resume tailor — format-preserving.

Instead of rewriting the résumé (which would discard the candidate's original
layout, e.g. Jake's template), this takes the candidate's *own* uploaded PDF and
**highlights the keywords most relevant to a specific role** directly on it. The
file, fonts, and layout are untouched — only a translucent highlight layer is
merged on top. Missing keywords are returned as suggestions for the candidate to
add in their own source.
"""

from __future__ import annotations

import io
import logging
import os
import re
from typing import Optional

from ai_agents import resume_optimizer

logger = logging.getLogger(__name__)

_HIGHLIGHT_RGB = (1, 0.86, 0.18)  # warm yellow
_HIGHLIGHT_ALPHA = 0.38
_MAX_HIGHLIGHTS = 18


def read_stored_pdf(url: Optional[str]) -> Optional[bytes]:
    """Fetch the original résumé PDF bytes from its stored URL (local or remote)."""
    if not url:
        return None
    if url.startswith("/files/"):
        from fastapi_app.core.config import get_settings

        settings = get_settings()
        base = os.path.realpath(settings.uploads_dir)
        target = os.path.realpath(os.path.join(settings.uploads_dir, url[len("/files/"):]))
        if not (target == base or target.startswith(base + os.sep)):
            return None
        try:
            with open(target, "rb") as fh:
                return fh.read()
        except OSError:
            return None
    if url.startswith("http"):
        try:
            import requests

            resp = requests.get(url, timeout=10)
            return resp.content if resp.ok else None
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not download résumé PDF: %s", exc)
            return None
    return None


def _norm(token: str) -> str:
    return token.strip(" .,():;|/–-").lower()


def highlight_pdf(original: bytes, keywords: list[str]) -> Optional[bytes]:
    """Return the original PDF with `keywords` highlighted in place (layout intact)."""
    import pdfplumber
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas

    targets = {_norm(k) for k in keywords if _norm(k)}
    if not targets:
        return original

    overlay_buf = io.BytesIO()
    c = canvas.Canvas(overlay_buf)
    try:
        with pdfplumber.open(io.BytesIO(original)) as pdf:
            for page in pdf.pages:
                w, h = float(page.width), float(page.height)
                c.setPageSize((w, h))
                c.setFillColorRGB(*_HIGHLIGHT_RGB)
                c.setFillAlpha(_HIGHLIGHT_ALPHA)
                for word in page.extract_words(use_text_flow=True):
                    if _norm(word["text"]) in targets:
                        x0 = float(word["x0"]) - 1
                        x1 = float(word["x1"]) + 1
                        top, bottom = float(word["top"]), float(word["bottom"])
                        c.rect(x0, h - bottom - 1, x1 - x0, (bottom - top) + 2, fill=1, stroke=0)
                c.showPage()
        c.save()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Highlighting failed: %s", exc)
        return original

    overlay_buf.seek(0)
    try:
        base = PdfReader(io.BytesIO(original))
        overlay = PdfReader(overlay_buf)
        writer = PdfWriter()
        for i, page in enumerate(base.pages):
            if i < len(overlay.pages):
                page.merge_page(overlay.pages[i])
            writer.add_page(page)
        out = io.BytesIO()
        writer.write(out)
        return out.getvalue()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Merging highlight layer failed: %s", exc)
        return original


def _pick_highlights(matched: list[str], required_skills: list[str], resume: dict) -> list[str]:
    """Keywords to highlight: required-skill matches first, then other JD matches."""
    resume_tokens = {_norm(t) for t in _flatten(resume)}
    req_present = [s for s in (required_skills or []) if _norm(s) in resume_tokens]
    ordered = list(dict.fromkeys([*(s.lower() for s in req_present), *matched]))
    # keep single, alphabetic-ish tokens (highlighting works word-by-word)
    ordered = [k for k in ordered if len(k) > 1 and " " not in k]
    return ordered[:_MAX_HIGHLIGHTS]


def _flatten(resume: dict) -> list[str]:
    out: list[str] = []
    for v in (resume or {}).values():
        if isinstance(v, str):
            out.extend(re.findall(r"[A-Za-z+#.]{2,}", v))
        elif isinstance(v, list):
            out.extend(str(x) for x in v)
        elif isinstance(v, dict):
            for x in v.values():
                out.extend(re.findall(r"[A-Za-z+#.]{2,}", str(x)))
    return out


async def generate_and_store(
    user_id: int,
    opportunity: dict,
    resume_url: Optional[str],
    resume_parsed: dict,
    required_skills: list[str],
    job_description: str,
) -> dict:
    """Highlight the original résumé for this role → upload → return download + tips."""
    from fastapi_app.services.cloudinary_service import upload_tailored_resume

    analysis = resume_optimizer.analyze_resume(resume_parsed or {}, job_description, required_skills)
    highlights = _pick_highlights(analysis["matched_keywords"], required_skills, resume_parsed or {})

    original = read_stored_pdf(resume_url)
    pdf_url = None
    note = ""
    if original:
        highlighted = highlight_pdf(original, highlights)
        opp_id = opportunity.get("id", 0)
        pdf_url = upload_tailored_resume(highlighted, user_id, opp_id)
        note = (
            f"Your original résumé — layout untouched — with {len(highlights)} role-relevant "
            "keyword(s) highlighted. Add the suggested keywords in your own source to raise the match."
        )
    else:
        note = (
            "Couldn't read your original résumé file to highlight it. The suggestions below "
            "show what to add — apply them in your own résumé and re-upload."
        )

    # Suggestions: missing JD keywords + skill gaps + any LLM tips.
    suggestions: list[str] = []
    for kw in analysis["missing_keywords"][:8]:
        suggestions.append(f"Add “{kw}” if you have relevant experience.")
    if analysis["skill_gaps"]:
        suggestions.append("Skills the role wants that aren't on your résumé: "
                           + ", ".join(analysis["skill_gaps"][:8]))
    for tip in (analysis.get("suggestions") or [])[:4]:
        if tip not in suggestions:
            suggestions.append(tip)

    return {
        "pdf_url": pdf_url,
        "highlighted": highlights,
        "suggestions": suggestions[:10],
        "ats_score": analysis["ats_score"],
        "note": note,
    }
