"""Cover letter generator: Groq → text → ReportLab PDF → Cloudinary URL."""

from __future__ import annotations

import asyncio
import io
import logging
from datetime import date

from ai_agents import llm_client

logger = logging.getLogger(__name__)


def generate_cover_letter_text(
    resume: dict, opportunity: dict, company_summary: str = ""
) -> str:
    name = (resume or {}).get("name") or "Candidate"
    company = opportunity.get("company_name") or "the company"
    role = opportunity.get("role") or opportunity.get("opportunity_type") or "the role"

    if llm_client.llm_available():
        try:
            from langchain.prompts import PromptTemplate
            from langchain.schema.output_parser import StrOutputParser

            def build(llm):
                prompt = PromptTemplate.from_template(
                    "Write a professional, specific cover letter (3 short paragraphs, "
                    "no placeholders) for {name} applying to {role} at {company}. "
                    "Draw on the resume and company research. Do not invent facts.\n\n"
                    "RESUME: {resume}\nCOMPANY RESEARCH: {research}\n"
                    "JOB: {job}\n\nReturn only the letter body."
                )
                return prompt | llm | StrOutputParser()

            text = llm_client.invoke_with_fallback(
                None,
                {
                    "name": name,
                    "role": role,
                    "company": company,
                    "resume": str(resume)[:2500],
                    "research": (company_summary or "")[:1500],
                    "job": str(opportunity)[:1500],
                    "_build": build,
                },
            )
            if text and text.strip():
                return text.strip()
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM cover letter failed: %s", exc)

    return _template_letter(name, role, company, resume)


def _template_letter(name: str, role: str, company: str, resume: dict) -> str:
    skills = ", ".join((resume or {}).get("skills", [])[:6]) or "my technical skills"
    return (
        f"Dear Hiring Team at {company},\n\n"
        f"I am writing to express my strong interest in the {role} position at "
        f"{company}. As a motivated student with a background spanning {skills}, "
        f"I am confident I can contribute meaningfully to your team.\n\n"
        f"Through my coursework and projects I have built practical experience that "
        f"aligns well with this role. I am eager to bring my problem-solving ability "
        f"and enthusiasm for learning to {company}.\n\n"
        f"Thank you for considering my application. I would welcome the opportunity "
        f"to discuss how I can add value to your team.\n\n"
        f"Sincerely,\n{name}"
    )


def text_to_pdf_bytes(text: str, title: str = "Cover Letter") -> bytes:
    """Render the letter to a clean A4 PDF using ReportLab."""
    from reportlab.lib.enums import TA_JUSTIFY
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=inch, rightMargin=inch, topMargin=inch, bottomMargin=inch,
    )
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "Body", parent=styles["Normal"], fontSize=11, leading=16, alignment=TA_JUSTIFY
    )
    story = [Paragraph(date.today().strftime("%B %d, %Y"), styles["Normal"]), Spacer(1, 18)]
    for para in text.split("\n\n"):
        para = para.strip().replace("\n", "<br/>")
        if para:
            story.append(Paragraph(para, body))
            story.append(Spacer(1, 12))
    doc.build(story)
    return buf.getvalue()


async def generate_and_store(
    user_id: int, opportunity: dict, resume: dict, company_summary: str = ""
) -> dict:
    """Full path: text → PDF → upload → return {text, pdf_url}."""
    from fastapi_app.services.cloudinary_service import upload_cover_letter

    # LLM call, ReportLab rendering and the upload are all blocking — keep
    # them in worker threads so the event loop stays responsive.
    text = await asyncio.to_thread(
        generate_cover_letter_text, resume, opportunity, company_summary
    )
    pdf_bytes = await asyncio.to_thread(text_to_pdf_bytes, text)
    opp_id = opportunity.get("id", 0)
    url = await asyncio.to_thread(upload_cover_letter, pdf_bytes, user_id, opp_id)
    return {"text": text, "pdf_url": url}
