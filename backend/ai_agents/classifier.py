"""Opportunity-type classifier.

Primary: HuggingFace zero-shot `facebook/bart-large-mnli` (local, free).
If top confidence < 0.7, fall back to the Groq LLM. If neither is available,
fall back to keyword heuristics. The model is loaded lazily and cached so the
API boots without torch/transformers installed.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from ai_agents import llm_client

logger = logging.getLogger(__name__)

LABELS = [
    "Internship",
    "Full-Time Placement",
    "Hackathon",
    "Competition",
    "Workshop",
    "Scholarship",
    "Other",
]

CONFIDENCE_THRESHOLD = 0.7


@lru_cache(maxsize=1)
def _zero_shot_pipeline():
    try:
        from transformers import pipeline

        logger.info("Loading facebook/bart-large-mnli zero-shot classifier…")
        return pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
    except Exception as exc:  # pragma: no cover - heavy optional dep
        logger.warning("Zero-shot classifier unavailable: %s", exc)
        return None


def classify(subject: str, body: str) -> dict:
    """Return {label, confidence, method}."""
    text = f"{subject}\n{body}".strip()[:2000]
    if not text:
        return {"label": "Other", "confidence": 0.0, "method": "empty"}

    clf = _zero_shot_pipeline()
    if clf is not None:
        try:
            out = clf(text, candidate_labels=LABELS, multi_label=False)
            label, score = out["labels"][0], float(out["scores"][0])
            if score >= CONFIDENCE_THRESHOLD:
                return {"label": label, "confidence": round(score, 3), "method": "zero-shot"}
            logger.info("Zero-shot low confidence %.2f → LLM fallback", score)
            llm_label = _llm_classify(text)
            if llm_label:
                return {"label": llm_label, "confidence": round(score, 3), "method": "groq-fallback"}
            return {"label": label, "confidence": round(score, 3), "method": "zero-shot-lowconf"}
        except Exception as exc:  # noqa: BLE001
            logger.warning("Zero-shot inference failed: %s", exc)

    llm_label = _llm_classify(text)
    if llm_label:
        return {"label": llm_label, "confidence": 0.0, "method": "groq"}
    return _keyword_classify(text)


def _llm_classify(text: str) -> str | None:
    if not llm_client.llm_available():
        return None
    try:
        from langchain.prompts import PromptTemplate
        from langchain.schema.output_parser import StrOutputParser

        def build(llm):
            prompt = PromptTemplate.from_template(
                "Classify this placement email into exactly one label from "
                f"{LABELS}. Reply with ONLY the label.\n\n{{text}}"
            )
            return prompt | llm | StrOutputParser()

        raw = llm_client.invoke_with_fallback(None, {"text": text, "_build": build})
        raw = (raw or "").strip()
        for label in LABELS:
            if label.lower() in raw.lower():
                return label
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM classification failed: %s", exc)
    return None


def _keyword_classify(text: str) -> dict:
    low = text.lower()
    table = {
        "Internship": ["intern", "internship"],
        "Hackathon": ["hackathon", "codefest"],
        "Competition": ["competition", "contest", "challenge"],
        "Workshop": ["workshop", "webinar", "bootcamp"],
        "Scholarship": ["scholarship", "fellowship"],
        "Full-Time Placement": ["full-time", "placement", "campus drive", "fte"],
    }
    for label, kws in table.items():
        if any(k in low for k in kws):
            return {"label": label, "confidence": 0.5, "method": "keyword"}
    return {"label": "Other", "confidence": 0.3, "method": "keyword"}
