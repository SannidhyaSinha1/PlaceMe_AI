"""LaTeX résumé tailor — edits the candidate's own .tex source for a role.

Because LaTeX is plain text, the AI can genuinely edit it in place: bold the
role-relevant keywords (``\\textbf{...}``), add/remove keywords, and rephrase
bullets — all while keeping the exact template (e.g. Jake's Resume), preamble,
and custom commands intact and compilable. Returns the full edited .tex.
"""

from __future__ import annotations

import logging

from ai_agents import llm_client

logger = logging.getLogger(__name__)

_MAX_LATEX_CHARS = 14000

_PROMPT = r"""You are an expert technical resume editor working directly on LaTeX source.
Edit the .tex below to tailor the resume for the target role.

HARD RULES:
- Keep ALL LaTeX preamble, \usepackage lines, custom command definitions, and the
  overall document structure EXACTLY as they are. Do not change the template/format.
- The output MUST still compile with the same packages.
- Tailoring you SHOULD do, inside the existing structure:
  * Wrap the most role-relevant skills/technologies/keywords in \textbf{{...}}
    (only terms that already appear, or that the candidate truthfully has).
  * Add role-relevant keywords to the skills section where the candidate
    plausibly has them. Be conservative.
  * Reorder bullet points / items so the most relevant come first.
  * Rephrase bullets to be concise and impact-oriented and to include the job's
    keywords WHERE the candidate genuinely did that work.
  * Remove or de-emphasize clearly irrelevant lines.
- NEVER invent employers, degrees, dates, numbers, or experiences.

OUTPUT FORMAT — output EXACTLY this, and nothing else (no markdown fences):
===CHANGES===
- <one short note per line, 3 to 7 lines, on what you tailored>
===LATEX===
<the complete edited .tex, ready to compile>

TARGET ROLE: {role} at {company}
JOB DESCRIPTION: {jd}
REQUIRED SKILLS: {required}

LATEX SOURCE:
{latex}"""


def _build_chain(llm):
    from langchain.prompts import PromptTemplate
    from langchain.schema.output_parser import StrOutputParser

    prompt = PromptTemplate.from_template(_PROMPT)
    return prompt | llm | StrOutputParser()


def _parse(raw: str, original: str) -> tuple[str, list[str]]:
    """Split the model output into (latex, changes); fall back to original."""
    if not raw or "===LATEX===" not in raw:
        return original, []
    head, _, latex = raw.partition("===LATEX===")
    latex = latex.strip()
    # Strip accidental markdown fences.
    if latex.startswith("```"):
        latex = latex.split("\n", 1)[-1]
    if latex.endswith("```"):
        latex = latex.rsplit("```", 1)[0]
    latex = latex.strip()

    changes: list[str] = []
    _, _, changes_block = head.partition("===CHANGES===")
    for line in changes_block.splitlines():
        line = line.strip().lstrip("-*•").strip()
        if line:
            changes.append(line)

    # Sanity: a real LaTeX doc must keep \begin{document}. If the model mangled
    # it, don't ship a broken file.
    if "\\begin{document}" in original and "\\begin{document}" not in latex:
        return original, []
    return (latex or original), changes


def tailor_latex(
    latex_source: str,
    opportunity: dict,
    required_skills: list[str],
    job_description: str,
) -> dict:
    """Return {latex, changes, used_llm} — the role-tailored LaTeX source."""
    original = latex_source or ""
    if not original.strip():
        return {"latex": original, "changes": [], "used_llm": False}

    if not llm_client.llm_available():
        return {
            "latex": original,
            "changes": ["AI is unavailable right now — your LaTeX was returned unchanged."],
            "used_llm": False,
        }

    try:
        payload = {
            "role": opportunity.get("role") or opportunity.get("opportunity_type") or "the role",
            "company": opportunity.get("company_name") or "the company",
            "jd": (job_description or "")[:2500],
            "required": ", ".join(required_skills or []) or "—",
            "latex": original[:_MAX_LATEX_CHARS],
            "_build": _build_chain,
        }
        raw = llm_client.invoke_with_fallback(None, payload)
        latex, changes = _parse(raw, original)
        return {
            "latex": latex,
            "changes": changes or ["Tailored for the role (details not itemised)."],
            "used_llm": latex != original,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("LaTeX tailoring failed: %s", exc)
        return {
            "latex": original,
            "changes": ["Tailoring failed (likely rate-limited) — original LaTeX returned. Try again shortly."],
            "used_llm": False,
        }
